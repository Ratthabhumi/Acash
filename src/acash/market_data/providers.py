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

MarketData.app Free adapter (``MARKETDATA_APP_FREE``) follows the documented array contract
(``s``, ``symbol``, ``last``, ``updated``), authenticates with ``Authorization: Bearer`` and keeps a
persisted 100-credit/day counter whose window opens at 09:30 America/New_York. The documented
contract is verified; a real response has not been observed (``MARKETDATA_LIVE_RESPONSE_VERIFIED``
is False), and the adapter is only constructed for a provider that ODR-004 reports READY.

Frankfurter ECB FX adapter (``FRANKFURTER_ECB_FX``) uses
``GET https://api.frankfurter.dev/v2/rate/USD/THB?providers=ECB`` and parses the documented V2
scalar ``{date, base, quote, rate}`` object, optionally with a ``date`` query for as-of alignment.
The documented contract is verified; a real response has not been observed
(``FRANKFURTER_LIVE_RESPONSE_VERIFIED`` is False).
"""

from __future__ import annotations

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
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
# Documented-contract verification (official docs / OpenAPI) and observed-live verification are separate
# states; neither one implies account entitlement, display rights or derived-use rights.
MARKETDATA_CONTRACT_VERIFIED = True
MARKETDATA_LIVE_RESPONSE_VERIFIED = False
FRANKFURTER_CONTRACT_VERIFIED = True
FRANKFURTER_LIVE_RESPONSE_VERIFIED = False
# MarketData.app Free Forever: 100 credits per day, window opening at 09:30 America/New_York.
MARKETDATA_CREDIT_LIMIT = 100
MARKETDATA_CREDIT_RESET = time(9, 30)
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
    "MASSIVE_BASIC": Endpoint("api.massive.com",
                              re.compile(r"^/v2/aggs/ticker/[A-Z][A-Z0-9]{0,9}(\.[A-Z])?"
                                         r"/(prev|range/1/day/\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2})$"),
                              frozenset({"adjusted"}), frozenset({"Authorization"})),
    "MARKETDATA_APP_FREE": Endpoint("api.marketdata.app",
                                    re.compile(r"^/v1/stocks/quotes/$"),
                                    frozenset({"symbols"}), frozenset({"Authorization"}), {}),
    "FRANKFURTER_ECB_FX": Endpoint("api.frankfurter.dev",
                                   re.compile(r"^/v2/rate/[A-Z]{3}/[A-Z]{3}$"),
                                   frozenset({"providers", "date"}), frozenset(),
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


def _unix_millis(provider_id: str, value: Any) -> datetime:
    """Whole Unix milliseconds (the aggregate-bar contract) to an aware UTC timestamp."""
    try:
        stamp = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} timestamp.") from None
    if not stamp.is_finite() or stamp <= 0 or stamp != stamp.to_integral_value():
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} timestamp.")
    try:
        return datetime.fromtimestamp(int(stamp) // 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} timestamp.") from None


def _unix_seconds(provider_id: str, value: Any) -> datetime:
    """Whole Unix seconds (as the documented quote contract supplies) to an aware UTC timestamp."""
    try:
        stamp = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} timestamp.") from None
    if not stamp.is_finite() or stamp <= 0 or stamp != stamp.to_integral_value():
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} timestamp.")
    try:
        return datetime.fromtimestamp(int(stamp), tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {provider_id} timestamp.") from None


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

    Documented contract (``MARKETDATA_CONTRACT_VERIFIED``): the response carries a status ``s`` plus
    index-aligned ``symbol``, ``last`` and ``updated`` arrays; ``updated`` is Unix seconds. ``last`` is
    a delayed last trade, never an official completed-session close, so it is labelled
    ``HISTORICAL_DELAYED_LAST``. Only ``s == "ok"`` is usable and ``no_data`` is an empty result.

    The token travels only in ``Authorization: Bearer`` (never in a query string). Credits are one per
    requested symbol, reserved before the request against a persisted counter whose window opens at
    09:30 America/New_York. A real response has not been observed
    (``MARKETDATA_LIVE_RESPONSE_VERIFIED`` is False) and the provider stays not-READY until the Owner
    attests the exchange-level rights in ODR-004 ``scope_providers``.
    """

    credential: Credential        # (token, "") — sent only in the Authorization header
    transport: Transport
    allow: Limiter
    clock: Callable[[], datetime]
    provider_id: str = "MARKETDATA_APP_FREE"
    ledger_path: Optional[Path] = None
    daily_credit_limit: int = MARKETDATA_CREDIT_LIMIT
    _used: int = field(default=0, repr=False)
    _window: Optional[date] = field(default=None, repr=False)
    _lock: Any = field(default_factory=threading.Lock, repr=False)

    @staticmethod
    def credit_window(moment: datetime) -> date:
        """The 09:30 America/New_York window containing ``moment``; DST follows the New York clock."""
        local = moment.astimezone(NEW_YORK)
        return local.date() if local.time() >= MARKETDATA_CREDIT_RESET else local.date() - timedelta(days=1)

    def _load(self, window: date) -> None:
        if self.ledger_path is None:
            if self._window != window:
                self._window, self._used = window, 0
            return
        if self.ledger_path.is_file():
            try:
                doc = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raise DataContractError(f"CREDIT_LEDGER_INVALID: {self.provider_id}.") from None
            used = doc.get("used") if isinstance(doc, dict) else None
            if not isinstance(used, int) or isinstance(used, bool) or used < 0:
                raise DataContractError(f"CREDIT_LEDGER_INVALID: {self.provider_id}.")
            if doc.get("window") == window.isoformat():
                self._window, self._used = window, min(used, self.daily_credit_limit)
                return
        self._window, self._used = window, 0

    def _persist(self) -> None:
        if self.ledger_path is None:
            return
        payload = json.dumps({"provider_id": self.provider_id, "window": str(self._window),
                              "used": self._used}, sort_keys=True)
        temporary = self.ledger_path.with_suffix(".tmp")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, self.ledger_path)

    def _reserve(self, symbols: int) -> None:
        """Reserve credits before the request so a failure can never over-spend the free allowance.

        The lock serialises refreshes inside this process; the persisted counter survives restarts.
        """
        with self._lock:
            window = self.credit_window(self.clock())
            self._load(window)
            if self._used + symbols > self.daily_credit_limit:
                raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id} daily credit budget exhausted.")
            self._used += symbols
            self._persist()

    def credits_used(self) -> int:
        """Credits reserved in the current window (for the Dashboard status, never a price)."""
        with self._lock:
            self._load(self.credit_window(self.clock()))
            return self._used

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.provider_id, ("HISTORICAL_DELAYED_LAST",), "UNKNOWN",
                                    True, True, True, None)

    def latest_prices(self, security_ids: Sequence[str], as_of: date) -> Sequence[PriceObservation]:
        if not MARKETDATA_CONTRACT_VERIFIED:
            raise DataContractError(f"PROVIDER_CONTRACT_UNVERIFIED: {self.provider_id}.")
        symbols = sorted({s for s in security_ids if SYMBOL.match(s)})
        if not symbols:
            return []
        if not self.allow():
            raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id}.")
        self._reserve(len(symbols))
        # The credential layout is (username, secret); SETUP-MARKET-DATA stores the token in the
        # secret half, so read that first and fall back to the username half for older entries.
        token = self.credential[1] or self.credential[0]
        url = build_url(self.provider_id, "/v1/stocks/quotes/", {"symbols": ",".join(symbols)})
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        request = HttpRequest(self.provider_id, url, headers)
        assert_allowed(request)
        status, body = self.transport(request)
        if status not in (200, 203):
            raise _status_error(self.provider_id, status)
        doc = _json_body(self.provider_id, body)
        if not isinstance(doc, dict):
            raise self._invalid("envelope")
        state = doc.get("s")
        if state == "no_data":
            return []
        if state != "ok":
            raise self._invalid("status")
        names, prices, stamps = doc.get("symbol"), doc.get("last"), doc.get("updated")
        if not (isinstance(names, list) and isinstance(prices, list) and isinstance(stamps, list)):
            raise self._invalid("arrays")
        if not names or not len(names) == len(prices) == len(stamps):
            raise self._invalid("array lengths")
        if any(not isinstance(n, str) or not SYMBOL.match(n) for n in names):
            raise self._invalid("symbol")
        if len(set(names)) != len(names) or set(names) - set(symbols):
            raise self._invalid("symbol set")
        now = self.clock()
        out: List[PriceObservation] = []
        for symbol, price, stamp in zip(names, prices, stamps):
            value = _positive(self.provider_id, price)
            observed = _unix_seconds(self.provider_id, stamp)
            if observed > now + timedelta(seconds=1):
                raise self._invalid("future timestamp")
            out.append(PriceObservation(
                security_id=symbol, provider_id=self.provider_id, provider_symbol=symbol, currency="USD",
                price=value, price_type="HISTORICAL_DELAYED_LAST",
                market_date=observed.astimezone(NEW_YORK).date(), retrieved_at=now, coverage="UNKNOWN",
                market_timestamp=observed))
        return out

    def _invalid(self, what: str) -> DataContractError:
        return DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} {what}.")


@dataclass
class FrankfurterECBFxProvider:
    """ECB reference USD/THB via ``GET https://api.frankfurter.dev/v2/rate/USD/THB?providers=ECB``.

    Documented V2 single-pair contract (``FRANKFURTER_CONTRACT_VERIFIED``): a scalar
    ``{date, base, quote, rate}`` object, not a nested ``rates`` map. Keyless, no published hard
    quota, ECB as the only accepted provider filter. Rates are reference rates: **not executable**,
    and a real response has not been observed (``FRANKFURTER_LIVE_RESPONSE_VERIFIED`` is False).
    """

    transport: Transport
    allow: Limiter
    clock: Callable[[], datetime]
    provider_id: str = "FRANKFURTER_ECB_FX"

    # No credential is required; the provider still needs ODR-004 scope and attested data-use rights.
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.provider_id, (), "REFERENCE_FX_NOT_EXECUTABLE",
                                    False, False, False, None)

    def _invalid(self, what: str) -> DataContractError:
        return DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} {what}.")

    def _fetch(self, base: str, quote: str, as_of: Optional[date]) -> Sequence[FXObservation]:
        if not FRANKFURTER_CONTRACT_VERIFIED:
            raise DataContractError(f"PROVIDER_CONTRACT_UNVERIFIED: {self.provider_id}.")
        if not re.match(r"^[A-Z]{3}$", base) or not re.match(r"^[A-Z]{3}$", quote) or base == quote:
            raise self._invalid("currency pair")
        if not self.allow():
            raise DataContractError(f"PROVIDER_RATE_LIMITED: {self.provider_id}.")
        query = {"providers": "ECB"} if as_of is None else {"providers": "ECB", "date": as_of.isoformat()}
        url = build_url(self.provider_id, f"/v2/rate/{base}/{quote}", query)
        status, body = self.transport(HttpRequest(self.provider_id, url, {}))
        if status != 200:
            raise _status_error(self.provider_id, status)
        doc = _json_body(self.provider_id, body)
        if not isinstance(doc, dict):
            raise self._invalid("envelope")
        try:
            obs_date = date.fromisoformat(str(doc["date"]))
            if str(doc["base"]).upper() != base or str(doc["quote"]).upper() != quote:
                raise self._invalid("currency pair mismatch")
            rate = _positive(self.provider_id, doc["rate"])
        except (KeyError, TypeError, ValueError):
            raise self._invalid("fields") from None
        retrieved = self.clock()
        if obs_date > retrieved.astimezone(NEW_YORK).date():
            raise self._invalid("future date")
        back = Decimal(f"{Decimal(1) / rate:.10g}")
        return [
            FXObservation(base, quote, rate, obs_date, "REFERENCE_FX", self.provider_id, retrieved),
            FXObservation(quote, base, back, obs_date, "REFERENCE_FX", self.provider_id, retrieved),
        ]

    def reference_rate(self, base: str = "USD", quote: str = "THB") -> Sequence[FXObservation]:
        """Latest ECB reference rate for ``base``/``quote`` in both directions."""
        return self._fetch(base, quote, None)

    def reference_rates(self, end: date, lookback_days: int = 7) -> Sequence[FXObservation]:
        """``FXProvider`` protocol view: ask for ``end`` and accept only ``[end-lookback_days, end]``.

        No look-ahead: the request carries the valuation date, and a rate the source dates after it
        or outside the window is refused rather than substituted (an empty sequence becomes
        ``FX_UNAVAILABLE_FOR_MARKET_DATE``).
        """
        observations = self._fetch("USD", "THB", end)
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

    def historical_daily(self, symbols: Sequence[str], start: date, end: date) -> List[Dict[str, Any]]:
        """Daily OHLCV aggregates for a bounded range (one request per symbol, 5/min budget).

        Split-adjusted prices are explicitly *not* dividend-adjusted total returns; the caller must
        treat this as a price-return series. A missing session is reported by absence, never filled.
        Pagination beyond the documented window is refused rather than silently truncated.
        """
        if start > end:
            raise DataContractError("MASSIVE_RANGE_INVALID: start must be on or before end.")
        bars: List[Dict[str, Any]] = []
        self.skipped = []
        for symbol in [s for s in symbols if SYMBOL.match(s)]:
            if not self.allow():
                self.skipped.append(symbol)
                continue
            url = build_url(self.provider_id,
                            f"/v2/aggs/ticker/{quote(symbol)}/range/1/day/{start.isoformat()}/{end.isoformat()}",
                            {"adjusted": "false"})
            status, body = self.transport(HttpRequest(self.provider_id, url,
                                                      {"Authorization": f"Bearer {self.credential[1]}"}))
            if status != 200:
                raise _status_error(self.provider_id, status)
            doc = _json_body(self.provider_id, body)
            if not isinstance(doc, dict) or not isinstance(doc.get("results"), list):
                raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} bars envelope.")
            if doc.get("next_url"):
                raise DataContractError("PROVIDER_PAGINATION_UNSUPPORTED: MASSIVE_BASIC.")
            for row in doc["results"]:
                if not isinstance(row, dict):
                    raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} bar.")
                try:
                    opened = _unix_millis(self.provider_id, row.get("t"))
                except DataContractError:
                    raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} bar timestamp.") from None
                session = opened.astimezone(NEW_YORK).date()
                if session < start or session > end:
                    raise DataContractError(f"PROVIDER_RESPONSE_INVALID: {self.provider_id} bar out of range.")
                bars.append({"symbol": symbol, "session_date": session, "open": str(_positive(self.provider_id, row.get("o"))),
                             "high": str(_positive(self.provider_id, row.get("h"))),
                             "low": str(_positive(self.provider_id, row.get("l"))),
                             "close": str(_positive(self.provider_id, row.get("c"))),
                             "volume": str(row.get("v")), "adjusted": False,
                             "provider": self.provider_id, "retrieved_at": self.clock().isoformat()})
        return bars

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
