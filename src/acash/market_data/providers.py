"""HTTP market-data adapters: Alpaca latest trade (IEX feed), Alpaca historical SIP bars,
MarketData.app Free delayed quotes, Frankfurter ECB reference FX, Massive previous close,
BOT reference FX.

Every URL is rebuilt from a fixed per-provider allowlist (scheme, host, path pattern, query keys,
value charset) and checked again by the transport, which refuses redirects and proxies. Requests
carry public symbols, dates and the provider's credential header only; nothing from the owner's
portfolio leaves the machine. Responses are parsed strictly with ``Decimal`` and any schema
deviation raises ``DataContractError``. Adapters are only constructed for providers that
``market_authority.provider_status`` reports READY; this module never logs URLs, headers or bodies.

The BOT host, path, header and field names follow the ChatGPT research brief and are not yet
verified against a live response (``BOT_SPEC_VERIFIED`` is False). The operation path
``/Stat-ReferenceRate/v2/DAILY_REF_RATE/get`` and the ``Authorization`` header follow the published
API catalogue; the query keys and response fields are still an unverified parser contract, so the
provider registry keeps BOT at CONTRACT_UNVERIFIED and it is never constructed for a real refresh.

MarketData.app Free adapter (``MARKETDATA_APP_FREE``) is registered but its live response schema
is not yet verified (``MARKETDATA_CONTRACT_VERIFIED = False``); synthetic tests use a mock
transport. The adapter will reach NOT_CONFIGURED until the contract and exchange-level rights are
established and the Owner adds the provider to ODR-004 ``scope_providers``.

Frankfurter ECB FX adapter (``FRANKFURTER_ECB_FX``) uses
``GET https://api.frankfurter.dev/v2/rate/USD/THB?providers=ECB``; the endpoint and envelope
structure are sourced from the published Frankfurter documentation. The response schema is treated
as unverified until a real response is observed and recorded (``FRANKFURTER_CONTRACT_VERIFIED``).
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional, Pattern, Sequence, Tuple
from urllib.parse import parse_qsl, quote, urlencode, urlsplit
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError
from acash.invest.market_authority import Credential
from acash.invest.market_refresh import NEW_YORK, SYMBOL
from acash.invest.market_valuation import FXObservation, PriceObservation, ProviderCapabilities

BANGKOK = ZoneInfo("Asia/Bangkok")
MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 10.0
ALPACA_BATCH = 100
ALPACA_SIP_DELAY = timedelta(minutes=15)
ALPACA_SIP_MARGIN = timedelta(minutes=2)
ALPACA_MAX_PAGES = 10
SESSION_CLOSE = time(16, 0)
BOT_SPEC_VERIFIED = False
MARKETDATA_CONTRACT_VERIFIED = False
FRANKFURTER_CONTRACT_VERIFIED = False
_QUERY_VALUE = re.compile(r"^[A-Za-z0-9.,:+/=_\-]{1,800}$")
_RFC3339 = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


@dataclass(frozen=True)
class Endpoint:
    host: str
    path: Pattern[str]
    query_keys: FrozenSet[str]
    headers: FrozenSet[str]
    fixed: Mapping[str, FrozenSet[str]] = field(default_factory=dict)


ENDPOINTS: Dict[str, Endpoint] = {
    "ALPACA_BASIC": Endpoint("data.alpaca.markets", re.compile(r"^/v2/stocks/trades/latest$"),
                             frozenset({"symbols", "feed"}), frozenset({"APCA-API-KEY-ID", "APCA-API-SECRET-KEY"}),
                             {"feed": frozenset({"iex"})}),
    "ALPACA_HISTORICAL": Endpoint("data.alpaca.markets", re.compile(r"^/v2/stocks/bars$"),
                                  frozenset({"symbols", "timeframe", "start", "end", "limit", "page_token", "feed",
                                             "adjustment"}),
                                  frozenset({"APCA-API-KEY-ID", "APCA-API-SECRET-KEY"}),
                                  {"feed": frozenset({"sip"}), "timeframe": frozenset({"1Min", "1Day"}),
                                   "adjustment": frozenset({"raw"})}),
    "MASSIVE_BASIC": Endpoint("api.massive.com", re.compile(r"^/v2/aggs/ticker/[A-Z][A-Z0-9]{0,9}(\.[A-Z])?/prev$"),
                              frozenset({"adjusted"}), frozenset({"Authorization"})),
    "MARKETDATA_APP_FREE": Endpoint("api.marketdata.app",
                                    re.compile(r"^/v1/stocks/quotes/$"),
                                    frozenset({"symbols", "token"}), frozenset(), {}),
    "FRANKFURTER_ECB_FX": Endpoint("api.frankfurter.dev",
                                   re.compile(r"^/v2/rate/[A-Z]{3}/[A-Z]{3}$"),
                                   frozenset({"providers"}), frozenset(),
                                   {"providers": frozenset({"ECB"})}),
        "BOT_REFERENCE_FX": Endpoint("gateway.api.bot.or.th", re.compile(r"^/Stat-ReferenceRate/v2/DAILY_REF_RATE/get$"),
                                 frozenset({"start_period", "end_period"}), frozenset({"Authorization"})),
}


@dataclass(frozen=True)
class HttpRequest:
    provider_id: str
    url: str
    headers: Mapping[str, str]


Transport = Callable[[HttpRequest], Tuple[int, bytes]]


def build_url(provider_id: str, path: str, query: Mapping[str, str]) -> str:
    url = f"https://{ENDPOINTS[provider_id].host}{path}?{urlencode(query, safe=',')}" if provider_id in ENDPOINTS else ""
    assert_allowed(HttpRequest(provider_id, url, {}))
    return url


def assert_allowed(request: HttpRequest) -> None:
    """Refuse anything outside the provider's fixed market-data endpoint."""
    endpoint = ENDPOINTS.get(request.provider_id)
    if endpoint is None:
        raise DataContractError("ENDPOINT_NOT_ALLOWED: unknown provider.")
    parts = urlsplit(request.url)
    if (parts.scheme != "https" or parts.hostname != endpoint.host or parts.port is not None
            or parts.username or parts.password or parts.fragment or parts.netloc != endpoint.host
            or not endpoint.path.match(parts.path)):
        raise DataContractError(f"ENDPOINT_NOT_ALLOWED: {request.provider_id}.")
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)) or not set(keys) <= endpoint.query_keys:
        raise DataContractError(f"ENDPOINT_QUERY_NOT_ALLOWED: {request.provider_id}.")
    if any(not _QUERY_VALUE.match(v) or (k in endpoint.fixed and v not in endpoint.fixed[k]) for k, v in pairs):
        raise DataContractError(f"EGRESS_VALUE_REFUSED: {request.provider_id}.")
    if not set(request.headers) <= endpoint.headers:
        raise DataContractError(f"ENDPOINT_HEADER_NOT_ALLOWED: {request.provider_id}.")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def urllib_transport(request: HttpRequest) -> Tuple[int, bytes]:
    """GET only, TLS verified, no proxy, no redirect, bounded body; errors carry no URL or header."""
    assert_allowed(request)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    req = urllib.request.Request(request.url, headers=dict(request.headers), method="GET")
    try:
        with opener.open(req, timeout=TIMEOUT_SECONDS) as response:
            return int(response.status), response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        return int(exc.code), b""
    except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError):
        raise DataContractError(f"PROVIDER_UNREACHABLE: {request.provider_id}.") from None


def _status_error(provider_id: str, status: int) -> DataContractError:
    if status in (401, 403):
        return DataContractError(f"PROVIDER_ACCESS_DENIED: {provider_id} HTTP {status}.")
    if status == 429:
        return DataContractError(f"PROVIDER_RATE_LIMITED: {provider_id}.")
    return DataContractError(f"PROVIDER_UNAVAILABLE: {provider_id} HTTP {status}.")


def _json_body(provider_id: str, body: bytes) -> Any:
    if len(body) > MAX_RESPONSE_BYTES:
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} response too large.")
    try:
        return json.loads(body.decode("utf-8"), parse_float=Decimal, parse_int=Decimal)
    except (UnicodeDecodeError, ValueError):
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} malformed JSON.") from None


def _positive(provider_id: str, value: Any) -> Decimal:
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value)) if isinstance(value, str) else None
    except InvalidOperation:
        number = None
    if number is None or not number.is_finite() or number <= 0:
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} price or rate.")
    return number


def _rfc3339(provider_id: str, text: Any) -> datetime:
    match = _RFC3339.match(text) if isinstance(text, str) else None
    if not match:
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} timestamp.")
    fraction = (match.group(2) or "")[:7]
    offset = "+00:00" if match.group(3) == "Z" else match.group(3)
    return datetime.fromisoformat(match.group(1) + fraction + offset)


Limiter = Callable[[], bool]


@dataclass
class AlpacaIEXMarketDataProvider:
    """``/v2/stocks/trades/latest?feed=iex``: last IEX trade, not a bid/ask, midpoint or consolidated
    last sale; timestamps are truncated to microseconds."""

    credential: Credential
    transport: Transport
    allow: Limiter
    clock: Callable[[], datetime]
    provider_id: str = "ALPACA_BASIC"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.provider_id, ("LAST_TRADE",), "IEX_ONLY", True, True, True, None)

    def latest_prices(self, security_ids: Sequence[str], as_of: date) -> Sequence[PriceObservation]:
        symbols = [s for s in security_ids if SYMBOL.match(s)]
        out: List[PriceObservation] = []
        headers = {"APCA-API-KEY-ID": self.credential[0], "APCA-API-SECRET-KEY": self.credential[1]}
        for start in range(0, len(symbols), ALPACA_BATCH):
            if not self.allow():
                if not out:
                    raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id}.")
                break
            batch = symbols[start:start + ALPACA_BATCH]
            url = build_url(self.provider_id, "/v2/stocks/trades/latest", {"symbols": ",".join(batch), "feed": "iex"})
            status, body = self.transport(HttpRequest(self.provider_id, url, headers))
            if status != 200:
                raise _status_error(self.provider_id, status)
            doc = _json_body(self.provider_id, body)
            trades = doc.get("trades") if isinstance(doc, dict) else None
            if not isinstance(trades, dict):
                raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} trades.")
            retrieved = self.clock()
            for symbol, trade in sorted(trades.items()):
                if not isinstance(trade, dict) or not isinstance(trade.get("x"), str):
                    raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} trade.")
                stamp = _rfc3339(self.provider_id, trade.get("t"))
                out.append(PriceObservation(
                    security_id=str(symbol), provider_id=self.provider_id, provider_symbol=str(symbol), currency="USD",
                    price=_positive(self.provider_id, trade.get("p")), price_type="LAST_TRADE",
                    market_date=stamp.astimezone(NEW_YORK).date(), retrieved_at=retrieved, coverage="IEX_ONLY",
                    market_timestamp=stamp))
        return out


def _z(stamp: datetime) -> str:
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AlpacaHistoricalSIPProvider:
    """``/v2/stocks/bars?feed=sip&adjustment=raw``: consolidated bars whose interval ended at least
    15 minutes (plus a 2-minute clock margin) before now, as the Basic plan allows without
    real-time SIP.

    The latest completed 1-minute bar of the past hour is an ``INTRADAY_BAR_CLOSE``; symbols without
    one fall back to the latest daily bar whose session has closed (16:00 New York, plus the same
    delay) as an ``EOD_CLOSE``. ``market_timestamp`` is the end of the bar interval, never the
    retrieval time. Bars are unadjusted: a split after the holdings date makes them incomparable
    with stored quantities. Pages beyond ``ALPACA_MAX_PAGES`` are refused rather than truncated.
    """

    credential: Credential
    transport: Transport
    allow: Limiter
    clock: Callable[[], datetime]
    provider_id: str = "ALPACA_HISTORICAL"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.provider_id, ("INTRADAY_BAR_CLOSE", "EOD_CLOSE"), "CONSOLIDATED", True, True, True, None)

    def _invalid(self, what: str) -> DataContractError:
        return DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} {what}.")

    def _bars(self, symbols: List[str], timeframe: str, start: datetime, end: datetime) -> Dict[str, List[Any]]:
        headers = {"APCA-API-KEY-ID": self.credential[0], "APCA-API-SECRET-KEY": self.credential[1]}
        out: Dict[str, List[Any]] = {}
        token: Optional[str] = None
        for _ in range(ALPACA_MAX_PAGES):
            if not self.allow():
                raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id}.")
            query = {"symbols": ",".join(symbols), "timeframe": timeframe, "start": _z(start), "end": _z(end),
                     "limit": "10000", "feed": "sip", "adjustment": "raw"}
            if token is not None:
                query["page_token"] = token
            status, body = self.transport(HttpRequest(self.provider_id, build_url(self.provider_id, "/v2/stocks/bars", query),
                                                      headers))
            if status != 200:
                raise _status_error(self.provider_id, status)
            doc = _json_body(self.provider_id, body)
            bars = doc.get("bars") if isinstance(doc, dict) else None
            if not isinstance(bars, dict):
                raise self._invalid("bars")
            for symbol, rows in bars.items():
                if symbol not in symbols or not isinstance(rows, list):
                    raise self._invalid("unrequested symbol")
                out.setdefault(symbol, []).extend(rows)
            token = doc.get("next_page_token")
            if token is None:
                return out
            if not isinstance(token, str) or not token:
                raise self._invalid("page token")
        raise self._invalid("excessive pagination")

    def _complete(self, rows: List[Any], daily: bool, start: datetime, limit: datetime) -> Optional[Tuple[datetime, Decimal]]:
        best: Optional[Tuple[datetime, Decimal]] = None
        seen = set()
        for raw in rows:
            if not isinstance(raw, dict):
                raise self._invalid("bar")
            opened = _rfc3339(self.provider_id, raw.get("t"))
            o, h, l, c = (_positive(self.provider_id, raw.get(k)) for k in ("o", "h", "l", "c"))
            if h < max(o, l, c) or l > min(o, h, c):
                raise self._invalid("bar range")
            if opened in seen or opened > limit or opened < start - timedelta(days=1):
                raise self._invalid("bar timestamp")
            seen.add(opened)
            closed = (datetime.combine(opened.astimezone(NEW_YORK).date(), SESSION_CLOSE, NEW_YORK) if daily
                      else opened + timedelta(minutes=1))
            if closed <= limit and (best is None or closed > best[0]):
                best = (closed, c)
        return best

    def latest_prices(self, security_ids: Sequence[str], as_of: date) -> Sequence[PriceObservation]:
        symbols = [s for s in security_ids if SYMBOL.match(s)]
        now = self.clock()
        limit = now - ALPACA_SIP_DELAY - ALPACA_SIP_MARGIN
        out: List[PriceObservation] = []
        for first in range(0, len(symbols), ALPACA_BATCH):
            batch = symbols[first:first + ALPACA_BATCH]
            for timeframe, span, price_type in (("1Min", timedelta(hours=1), "INTRADAY_BAR_CLOSE"),
                                                ("1Day", timedelta(days=10), "EOD_CLOSE")):
                wanted = [s for s in batch if not any(o.security_id == s for o in out)]
                if not wanted:
                    break
                start = limit - span
                bars = self._bars(wanted, timeframe, start, limit)
                for symbol in wanted:
                    best = self._complete(bars.get(symbol, []), timeframe == "1Day", start, limit)
                    if best is not None:
                        out.append(PriceObservation(
                            security_id=symbol, provider_id=self.provider_id, provider_symbol=symbol, currency="USD",
                            price=best[1], price_type=price_type, market_date=best[0].astimezone(NEW_YORK).date(),
                            retrieved_at=now, coverage="CONSOLIDATED", market_timestamp=best[0]))
        return out


@dataclass
class MarketDataAppFreeProvider:
    """MarketData.app Free Forever delayed quotes (``/v1/stocks/quotes/``).

    100 credits/day budget enforced.  Data is delayed ≥ 24 h.  The live response schema
    is **not yet verified** (``MARKETDATA_CONTRACT_VERIFIED = False``); the adapter raises
    ``DataContractError`` on any unexpected envelope shape.  Synthetic tests use a mock
    transport only.  The provider stays NOT_CONFIGURED until the Owner adds it to
    ODR-004 ``scope_providers`` with exchange-level rights attested.
    """

    credential: Credential        # (token, "") — token passed as query param, never in URL log
    transport: Transport
    allow: Limiter                # must gate on daily credit budget
    clock: Callable[[], datetime]
    provider_id: str = "MARKETDATA_APP_FREE"
    _daily_credits_used: int = field(default=0, repr=False)
    _credits_day: Optional[date] = field(default=None, repr=False)
    DAILY_CREDIT_LIMIT: int = field(default=100, init=False, repr=False)

    def _charge(self, symbols: int) -> None:
        """One credit per requested symbol against the published 100/day Free allowance.

        Credits are charged before the request, so a failed call never over-spends; the counter
        resets only when the UTC date changes.
        """
        today = self.clock().astimezone(timezone.utc).date()
        if self._credits_day != today:
            self._credits_day, self._daily_credits_used = today, 0
        if self._daily_credits_used + symbols > self.DAILY_CREDIT_LIMIT:
            raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id} daily credit budget exhausted.")
        self._daily_credits_used += symbols

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.provider_id, ("EOD_CLOSE",), "UNKNOWN",
                                    True, True, True, None)

    def latest_prices(self, security_ids: Sequence[str], as_of: date) -> Sequence[PriceObservation]:
        if not MARKETDATA_CONTRACT_VERIFIED:
            raise DataContractError(
                f"PROVIDER_CONTRACT_UNVERIFIED: {self.provider_id} response schema not confirmed "
                "against a live observation; add a verified schema before enabling live requests."
            )
        symbols = [s for s in security_ids if SYMBOL.match(s)]
        if not symbols:
            return []
        if not self.allow():
            raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id}.")
        self._charge(len(symbols))
        # The live request shape stays the unverified placeholder; only the security registration and
        # transport layers are active at this stage.
        token = self.credential[0]
        url = build_url(self.provider_id, "/v1/stocks/quotes/",
                        {"symbols": ",".join(symbols), "token": token})
        status, body = self.transport(HttpRequest(self.provider_id, url, {}))
        if status != 200:
            raise _status_error(self.provider_id, status)
        doc = _json_body(self.provider_id, body)
        # Minimal envelope guard — full field parsing requires verified schema
        if not isinstance(doc, dict):
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} envelope.")
        return []   # CONTRACT_UNVERIFIED guard above prevents reaching this line in practice


@dataclass
class FrankfurterECBFxProvider:
    """ECB reference USD/THB via ``GET https://api.frankfurter.dev/v2/rate/USD/THB?providers=ECB``.

    Keyless, no daily hard quota.  Rates are ECB reference rates: **not executable**.
    The response schema is sourced from published Frankfurter documentation and is treated
    as unverified until ``FRANKFURTER_CONTRACT_VERIFIED`` is set True after a real
    response is recorded.  Label: ``REFERENCE_FX_NOT_EXECUTABLE``.
    """

    transport: Transport
    allow: Limiter
    clock: Callable[[], datetime]
    provider_id: str = "FRANKFURTER_ECB_FX"

    # No credential needed — keyless API; credential tuple reserved for future auth
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.provider_id, (), "REFERENCE_FX_NOT_EXECUTABLE",
                                    False, False, False, None)

    def reference_rate(self, base: str = "USD", quote: str = "THB") -> Sequence[FXObservation]:
        """Fetch the latest ECB reference rate for ``base``/``quote``."""
        if not FRANKFURTER_CONTRACT_VERIFIED:
            raise DataContractError(
                f"PROVIDER_CONTRACT_UNVERIFIED: {self.provider_id} response schema not confirmed "
                "against a live observation; record a real response before enabling live requests."
            )
        if not re.match(r"^[A-Z]{3}$", base) or not re.match(r"^[A-Z]{3}$", quote):
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} currency pair.")
        if not self.allow():
            raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id}.")
        path = f"/v2/rate/{base}/{quote}"
        url = build_url(self.provider_id, path, {"providers": "ECB"})
        status, body = self.transport(HttpRequest(self.provider_id, url, {}))
        if status != 200:
            raise _status_error(self.provider_id, status)
        doc = _json_body(self.provider_id, body)
        # Envelope: {"base": "USD", "quote": "THB", "date": "2026-10-31", "rates": {"ECB": 34.12}}
        if not isinstance(doc, dict):
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} envelope.")
        try:
            obs_date = date.fromisoformat(str(doc["date"]))
            rates = doc["rates"]
            if not isinstance(rates, dict) or "ECB" not in rates:
                raise KeyError("ECB")
            rate = _positive(self.provider_id, rates["ECB"])
        except (KeyError, TypeError, ValueError):
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} fields.") from None
        retrieved = self.clock()
        if obs_date > retrieved.astimezone(timezone.utc).date():
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} future date.")
        back = Decimal(f"{Decimal(1) / rate:.10g}")
        return [
            FXObservation(base, quote, rate, obs_date, "REFERENCE_FX", self.provider_id, retrieved),
            FXObservation(quote, base, back, obs_date, "REFERENCE_FX", self.provider_id, retrieved),
        ]

    def reference_rates(self, end: date, lookback_days: int = 7) -> Sequence[FXObservation]:
        """``FXProvider`` protocol view: only observations inside ``[end-lookback_days, end]``.

        Frankfurter Free exposes the latest ECB reference rate; a stale rate outside the market
        window is not silently substituted (an empty sequence becomes ``FX_UNAVAILABLE_FOR_MARKET_DATE``).
        """
        observations = self.reference_rate("USD", "THB")
        start = end - timedelta(days=lookback_days)
        return [o for o in observations if start <= o.market_date <= end]


@dataclass
class MassiveEODMarketDataProvider:
    """``/v2/aggs/ticker/{T}/prev?adjusted=false``: previous eligible session close, unadjusted.
    One request per symbol under a five-per-minute budget; symbols beyond it stay unpriced.
    Closes are kept in memory only, keyed by the New York date they were retrieved on."""

    credential: Credential
    transport: Transport
    allow: Limiter
    clock: Callable[[], datetime]
    provider_id: str = "MASSIVE_BASIC"
    cache: Dict[str, PriceObservation] = field(default_factory=dict)
    skipped: List[str] = field(default_factory=list)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.provider_id, ("EOD_CLOSE",), "UNKNOWN", True, True, True, None)

    def latest_prices(self, security_ids: Sequence[str], as_of: date) -> Sequence[PriceObservation]:
        out: List[PriceObservation] = []
        self.skipped = []
        today = self.clock().astimezone(NEW_YORK).date()
        for symbol in [s for s in security_ids if SYMBOL.match(s)]:
            cached = self.cache.get(symbol)
            if cached is not None and cached.retrieved_at.astimezone(NEW_YORK).date() == today:
                out.append(cached)
                continue
            if not self.allow():
                self.skipped.append(symbol)
                continue
            url = build_url(self.provider_id, f"/v2/aggs/ticker/{quote(symbol)}/prev", {"adjusted": "false"})
            status, body = self.transport(HttpRequest(self.provider_id, url, {"Authorization": f"Bearer {self.credential[1]}"}))
            if status == 404:
                continue
            if status != 200:
                raise _status_error(self.provider_id, status)
            observation = self._parse(symbol, _json_body(self.provider_id, body))
            if observation is not None:
                self.cache[symbol] = observation
                out.append(observation)
        if not out and self.skipped:
            raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id}.")
        return out

    def _parse(self, symbol: str, doc: Any) -> Optional[PriceObservation]:
        if not isinstance(doc, dict) or doc.get("adjusted") is not False or doc.get("ticker") != symbol:
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} envelope.")
        results = doc.get("results")
        if not results:
            return None
        if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} results.")
        bar = results[0]
        stamp = bar.get("t")
        if bar.get("T", symbol) != symbol or not isinstance(stamp, Decimal) or stamp != stamp.to_integral_value() or stamp <= 0:
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} bar.")
        session = datetime.fromtimestamp(int(stamp) / 1000, tz=timezone.utc).astimezone(NEW_YORK).date()
        return PriceObservation(
            security_id=symbol, provider_id=self.provider_id, provider_symbol=symbol, currency="USD",
            price=_positive(self.provider_id, bar.get("c")), price_type="EOD_CLOSE", market_date=session,
            retrieved_at=self.clock(), coverage="UNKNOWN", adjustment_policy="UNADJUSTED")


@dataclass
class BOTReferenceFXProvider:
    """Bank of Thailand USD/THB reference rate (THB per USD) by period date. The reciprocal
    THB->USD rate is derived exactly and rounded to 10 significant digits for PPDS, which needs
    both directions. Reference rates are not executable conversion rates."""

    credential: Credential
    transport: Transport
    allow: Limiter
    clock: Callable[[], datetime]
    provider_id: str = "BOT_REFERENCE_FX"

    def reference_rates(self, end: date, lookback_days: int = 7) -> Sequence[FXObservation]:
        if not self.allow():
            raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id}.")
        start = end - timedelta(days=lookback_days)
        url = build_url(self.provider_id, "/Stat-ReferenceRate/v2/DAILY_REF_RATE/get",
                        {"start_period": start.isoformat(), "end_period": end.isoformat()})
        status, body = self.transport(HttpRequest(self.provider_id, url, {"Authorization": self.credential[1]}))
        if status != 200:
            raise _status_error(self.provider_id, status)
        doc = _json_body(self.provider_id, body)
        try:
            rows = doc["result"]["data"]["data_detail"]
        except (KeyError, TypeError):
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} envelope.") from None
        if not isinstance(rows, list):
            raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} rows.")
        retrieved, out, seen = self.clock(), [], set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("period"), str):
                raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} row.")
            try:
                period = date.fromisoformat(row["period"])
            except ValueError:
                raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} period.") from None
            if row.get("rate") in (None, ""):
                continue
            rate = _positive(self.provider_id, row.get("rate"))
            if period in seen or period > retrieved.astimezone(BANGKOK).date() or not start <= period <= end:
                raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} period range.")
            seen.add(period)
            back = Decimal(f"{Decimal(1) / rate:.10g}")
            out.append(FXObservation("USD", "THB", rate, period, "REFERENCE_FX", self.provider_id, retrieved))
            out.append(FXObservation("THB", "USD", back, period, "REFERENCE_FX", self.provider_id, retrieved))
        return out
