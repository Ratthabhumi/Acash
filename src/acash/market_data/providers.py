"""HTTP market-data adapters: Alpaca latest trade (IEX feed), Massive previous close, BOT reference FX.

Every URL is rebuilt from a fixed per-provider allowlist (scheme, host, path pattern, query keys,
value charset) and checked again by the transport, which refuses redirects and proxies. Requests
carry public symbols, dates and the provider's credential header only; nothing from the owner's
portfolio leaves the machine. Responses are parsed strictly with ``Decimal`` and any schema
deviation raises ``DataContractError``. Adapters are only constructed for providers that
``market_authority.provider_status`` reports READY; this module never logs URLs, headers or bodies.

The BOT host, path, header and field names follow the ChatGPT research brief and are not yet
verified against a live response (``BOT_SPEC_VERIFIED`` is False).
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
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
BOT_SPEC_VERIFIED = False
_QUERY_VALUE = re.compile(r"^[A-Za-z0-9.,\-]{1,800}$")
_RFC3339 = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


@dataclass(frozen=True)
class Endpoint:
    host: str
    path: Pattern[str]
    query_keys: FrozenSet[str]
    headers: FrozenSet[str]


ENDPOINTS: Dict[str, Endpoint] = {
    "ALPACA_BASIC": Endpoint("data.alpaca.markets", re.compile(r"^/v2/stocks/trades/latest$"),
                             frozenset({"symbols", "feed"}), frozenset({"APCA-API-KEY-ID", "APCA-API-SECRET-KEY"})),
    "MASSIVE_BASIC": Endpoint("api.massive.com", re.compile(r"^/v2/aggs/ticker/[A-Z][A-Z0-9]{0,9}(\.[A-Z])?/prev$"),
                              frozenset({"adjusted"}), frozenset({"Authorization"})),
    "BOT_REFERENCE_FX": Endpoint("gateway.api.bot.or.th", re.compile(r"^/Stat-ReferenceRate/v2/DAILY_REF_RATE/$"),
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
    if any(not _QUERY_VALUE.match(v) for _, v in pairs):
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
        url = build_url(self.provider_id, "/Stat-ReferenceRate/v2/DAILY_REF_RATE/",
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
