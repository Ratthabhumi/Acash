"""HYP_011 dedicated Alpaca SIP daily-bars qualification client.

Separate module so HYP_003/HYP_009/HYP_010 codepaths are untouched. Tiny-probe
scope only: exactly 2016-01-04..2016-01-07, symbols ACWI/AGG/SPY, 1Day SIP,
adjustments split/raw. Every actual HTTP execution is counted via listener.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional, Sequence, Set, Tuple

import httpx
import time
from pydantic import ValidationError

from acash.core.domain.exceptions import DataContractError, DomainError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.daily_models import DailyBar
from acash.data.qualification.manifest import compute_page_sha256
from acash.data.qualification.models import (
    MarketDataFeed,
    PriceAdjustment,
    SipPageMetadata,
)
from acash.data.qualification.client import SipContractViolationError
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    AlpacaCredentialProvider,
    AlpacaCredentials,
    EnvAlpacaCredentialProvider,
)


HYP011_SYMBOLS: FrozenSet[str] = frozenset({"ACWI", "AGG", "SPY"})
HYP011_TIMEFRAME: str = "1Day"
HYP011_FEED: MarketDataFeed = MarketDataFeed.SIP
HYP011_ALLOWED_ADJUSTMENTS: FrozenSet[PriceAdjustment] = frozenset(
    {PriceAdjustment.SPLIT, PriceAdjustment.RAW}
)
HYP011_PROBE_START: date = date(2016, 1, 4)
HYP011_PROBE_END: date = date(2016, 1, 7)
HYP011_HISTORICAL_START: date = date(2016, 1, 1)
HYP011_HISTORICAL_END: date = date(2024, 12, 31)
HYP011_EXPECTED_PROBE_SESSIONS = (
    date(2016, 1, 4),
    date(2016, 1, 5),
    date(2016, 1, 6),
    date(2016, 1, 7),
)


@dataclass(frozen=True)
class Hyp011HistoricalResult:
    bars: List[DailyBar]
    pages_raw_bytes: List[bytes]
    pages_metadata: List[SipPageMetadata]
    http_status_code: int
    symbol: str
    adjustment: str

_REQUIRED_BAR_KEYS = ("t", "o", "h", "l", "c", "v")


@dataclass(frozen=True)
class Hyp011RetrievalResult:
    bars: List[DailyBar]
    pages_raw_bytes: List[bytes]
    pages_metadata: List[SipPageMetadata]
    http_status_code: int
    response_headers: Dict[str, str]
    feed_requested: str
    feed_response_provenance: str
    symbol: str
    adjustment: str


class Hyp011PreNetworkGuard:
    """Pre-network guard: allowlisted symbols and the exact tiny-probe window."""

    def validate_request(
        self,
        symbol: str,
        start_utc: datetime,
        end_utc: datetime,
        feed: MarketDataFeed,
        adjustment: PriceAdjustment,
        timeframe: str,
    ) -> None:
        sym = symbol.strip().upper()
        if sym not in HYP011_SYMBOLS:
            raise SipContractViolationError(
                f"HYP_011 allowlist violation: symbol '{symbol}' not in ACWI/AGG/SPY."
            )
        if timeframe != HYP011_TIMEFRAME:
            raise SipContractViolationError(
                f"HYP_011 requires timeframe='1Day', got '{timeframe}'."
            )
        if feed != MarketDataFeed.SIP:
            raise SipContractViolationError(
                f"HYP_011 requires feed='sip', got '{feed}'."
            )
        if adjustment not in HYP011_ALLOWED_ADJUSTMENTS:
            raise SipContractViolationError(
                f"HYP_011 requires adjustment in {{'split','raw'}}, got '{adjustment}'."
            )
        if start_utc.tzinfo is None or end_utc.tzinfo is None:
            raise DataContractError("HYP_011 window datetimes must be timezone-aware UTC.")
        start_date = start_utc.astimezone(timezone.utc).date()
        end_date = end_utc.astimezone(timezone.utc).date()
        if start_date != HYP011_PROBE_START or end_date != HYP011_PROBE_END:
            raise SipContractViolationError(
                f"HYP_011 tiny-probe window must be exactly "
                f"{HYP011_PROBE_START}..{HYP011_PROBE_END}, got {start_date}..{end_date}."
            )


class HYP011AlpacaClient:
    """Tiny-probe-only Alpaca SIP daily client for HYP_011 qualification."""

    def __init__(
        self,
        credential_provider: Optional[AlpacaCredentialProvider] = None,
        guard: Optional[Hyp011PreNetworkGuard] = None,
        calendar: Optional[NyseCa1Calendar] = None,
        base_url: str = "https://data.alpaca.markets",
        transport: Optional[httpx.BaseTransport] = None,
        max_retries_429: int = 3,
        retry_delay_seconds: float = 1.0,
        http_attempt_listener: Optional[Callable[[], None]] = None,
    ) -> None:
        self._credentials_provider = credential_provider or EnvAlpacaCredentialProvider()
        self._guard = guard or Hyp011PreNetworkGuard()
        self._calendar = calendar or NyseCa1Calendar()
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._max_retries_429 = max_retries_429
        self._retry_delay_seconds = retry_delay_seconds
        self._http_attempt_listener = http_attempt_listener

    def _get_auth_headers(self) -> Dict[str, str]:
        creds: AlpacaCredentials = self._credentials_provider.load()
        if not creds.resolved or not creds.api_key_id:
            raise AlpacaCredentialError(
                "Alpaca API credentials are not resolved; refusing request (fail-closed)."
            )
        return {
            "APCA-API-KEY-ID": creds.api_key_id,
            "APCA-API-SECRET-KEY": creds.api_secret_ref,
            "Accept": "application/json",
        }

    def fetch_tiny_probe(
        self,
        symbol: str,
        start_utc: datetime,
        end_utc: datetime,
        feed: MarketDataFeed = MarketDataFeed.SIP,
        adjustment: PriceAdjustment = PriceAdjustment.RAW,
        timeframe: str = "1Day",
    ) -> Hyp011RetrievalResult:
        """Fetch the exact tiny probe window; guard rejects anything else pre-network."""
        self._guard.validate_request(symbol, start_utc, end_utc, feed, adjustment, timeframe)
        bars, pages_raw, pages_meta, status, headers = self._fetch_pages(
            symbol.strip().upper(), start_utc, end_utc, feed, adjustment, timeframe,
            max_pages=5,
            window=(HYP011_PROBE_START, HYP011_PROBE_END),
        )
        return Hyp011RetrievalResult(
            bars=bars,
            pages_raw_bytes=pages_raw,
            pages_metadata=pages_meta,
            http_status_code=status,
            response_headers=headers,
            feed_requested=feed.value,
            feed_response_provenance="alpaca-sip",
            symbol=symbol.strip().upper(),
            adjustment=adjustment.value,
        )

    def fetch_historical_window(
        self,
        symbol: str,
        start_utc: datetime,
        end_utc: datetime,
        feed: MarketDataFeed = MarketDataFeed.SIP,
        adjustment: PriceAdjustment = PriceAdjustment.RAW,
        timeframe: str = "1Day",
    ) -> Hyp011HistoricalResult:
        """Fetch the full frozen historical window (fail closed outside scope)."""
        sym = symbol.strip().upper()
        if sym not in HYP011_SYMBOLS:
            raise SipContractViolationError(
                f"HYP_011 allowlist violation: symbol '{symbol}' not in ACWI/AGG/SPY."
            )
        if timeframe != HYP011_TIMEFRAME:
            raise SipContractViolationError(
                f"HYP_011 requires timeframe='1Day', got '{timeframe}'."
            )
        if feed != MarketDataFeed.SIP:
            raise SipContractViolationError(f"HYP_011 requires feed='sip', got '{feed}'.")
        if adjustment not in HYP011_ALLOWED_ADJUSTMENTS:
            raise SipContractViolationError(
                f"HYP_011 requires adjustment in {{'split','raw'}}, got '{adjustment}'."
            )
        if start_utc.tzinfo is None or end_utc.tzinfo is None:
            raise DataContractError("HYP_011 window datetimes must be timezone-aware UTC.")
        start_date = start_utc.astimezone(timezone.utc).date()
        end_date = end_utc.astimezone(timezone.utc).date()
        if start_date < HYP011_HISTORICAL_START or end_date > HYP011_HISTORICAL_END:
            raise SipContractViolationError(
                f"HYP_011 historical window [{start_date}, {end_date}] outside "
                f"[{HYP011_HISTORICAL_START}, {HYP011_HISTORICAL_END}]."
            )
        if start_date > end_date:
            raise DataContractError("HYP_011 historical window start exceeds end.")
        bars, pages_raw, pages_meta, status, _ = self._fetch_pages(
            sym, start_utc, end_utc, feed, adjustment, timeframe,
            max_pages=50,
            window=(HYP011_HISTORICAL_START, HYP011_HISTORICAL_END),
        )
        return Hyp011HistoricalResult(
            bars=bars,
            pages_raw_bytes=pages_raw,
            pages_metadata=pages_meta,
            http_status_code=status,
            symbol=sym,
            adjustment=adjustment.value,
        )

    def fetch_single_session(
        self,
        symbol: str,
        session: date,
        feed: MarketDataFeed = MarketDataFeed.SIP,
        adjustment: PriceAdjustment = PriceAdjustment.RAW,
        timeframe: str = "1Day",
    ) -> Hyp011HistoricalResult:
        """Fetch exactly one eligible trading session (prospective observations).

        Bounds are the single session day (00:00:00Z..23:59:59.999999Z).
        Activation/next-expected rules live in the runner, not here.
        """
        from datetime import datetime as _datetime

        sym = symbol.strip().upper()
        if sym not in HYP011_SYMBOLS:
            raise SipContractViolationError(
                f"HYP_011 allowlist violation: symbol '{symbol}' not in ACWI/AGG/SPY."
            )
        if timeframe != HYP011_TIMEFRAME:
            raise SipContractViolationError(
                f"HYP_011 requires timeframe='1Day', got '{timeframe}'."
            )
        if feed != MarketDataFeed.SIP:
            raise SipContractViolationError(f"HYP_011 requires feed='sip', got '{feed}'.")
        if adjustment not in HYP011_ALLOWED_ADJUSTMENTS:
            raise SipContractViolationError(
                f"HYP_011 requires adjustment in {{'split','raw'}}, got '{adjustment}'."
            )
        if not self._calendar.is_trading_session(session):
            raise SipContractViolationError(f"HYP_011 not a trading session: {session}.")
        start_utc = _datetime(session.year, session.month, session.day, tzinfo=timezone.utc)
        end_utc = _datetime(
            session.year, session.month, session.day, 23, 59, 59, 999999,
            tzinfo=timezone.utc,
        )
        bars, pages_raw, pages_meta, status, _ = self._fetch_pages(
            sym, start_utc, end_utc, feed, adjustment, timeframe,
            max_pages=5,
            window=(session, session),
        )
        if len(bars) != 1 or bars[0].timestamp_utc.date() != session:
            raise SipContractViolationError(
                f"HYP_011 single-session fetch must return exactly {session}."
            )
        return Hyp011HistoricalResult(
            bars=bars,
            pages_raw_bytes=pages_raw,
            pages_metadata=pages_meta,
            http_status_code=status,
            symbol=sym,
            adjustment=adjustment.value,
        )

    def _fetch_pages(
        self,
        sym: str,
        start_utc: datetime,
        end_utc: datetime,
        feed: MarketDataFeed,
        adjustment: PriceAdjustment,
        timeframe: str,
        max_pages: int,
        window: Tuple[date, date],
    ) -> Tuple[List[DailyBar], List[bytes], List[SipPageMetadata], int, Dict[str, str]]:
        headers = self._get_auth_headers()
        start_str = start_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"{self._base_url}/v2/stocks/{sym}/bars"
        params: Dict[str, Any] = {
            "timeframe": timeframe,
            "feed": feed.value,
            "adjustment": adjustment.value,
            "start": start_str,
            "end": end_str,
            "limit": 10000,
            "sort": "asc",
        }
        pages_raw_bytes: List[bytes] = []
        pages_metadata: List[SipPageMetadata] = []
        all_bars: List[DailyBar] = []
        page_index = 0
        next_page_token: Optional[str] = None
        last_status_code = 0
        last_headers: Dict[str, str] = {}
        with httpx.Client(transport=self._transport) as client:
            while True:
                page_index += 1
                if page_index > max_pages:
                    raise DataContractError("HYP_011 page budget exceeded.")
                page_params = dict(params)
                if next_page_token:
                    page_params["page_token"] = next_page_token
                retries = 0
                while True:
                    if self._http_attempt_listener is not None:
                        self._http_attempt_listener()
                    try:
                        response = client.get(url, headers=headers, params=page_params, timeout=30.0)
                    except httpx.RequestError as e:
                        raise DataContractError(f"HTTP request to Alpaca failed: {e}") from e
                    if response.status_code == 429:
                        retries += 1
                        if retries > self._max_retries_429:
                            raise DataContractError("Alpaca 429 retry budget exhausted.")
                        time.sleep(self._retry_delay_seconds * (2 ** (retries - 1)))
                        continue
                    break
                last_status_code = response.status_code
                last_headers = dict(response.headers)
                if response.status_code == 401:
                    raise AlpacaCredentialError("Alpaca authentication failed (HTTP 401).")
                if response.status_code == 403:
                    raise DataContractError("Alpaca access forbidden (HTTP 403). SIP denied.")
                if response.status_code != 200:
                    raise DataContractError(
                        f"Alpaca query failed with HTTP status {response.status_code}."
                    )
                raw_bytes = response.content
                pages_raw_bytes.append(raw_bytes)
                try:
                    payload = response.json()
                except Exception as e:
                    raise DataContractError(f"Failed to parse Alpaca JSON: {e}") from e
                raw_bars = payload.get("bars") or []
                if isinstance(raw_bars, dict):
                    raw_bars = raw_bars.get(sym, [])
                if not isinstance(raw_bars, list):
                    raise SipContractViolationError("HYP_011 'bars' payload must be a list.")
                parsed = self._parse_bars(raw_bars, window)
                all_bars.extend(parsed)
                token = payload.get("next_page_token")
                pages_metadata.append(
                    SipPageMetadata(
                        page_index=page_index,
                        bar_count=len(parsed),
                        raw_sha256=compute_page_sha256(raw_bytes),
                        byte_length=len(raw_bytes),
                        relative_artifact_path=f"page-{page_index:04d}.raw.json",
                        page_token=next_page_token,
                        next_page_token=token,
                    )
                )
                if not token:
                    break
                next_page_token = token
        return (
            all_bars,
            pages_raw_bytes,
            pages_metadata,
            last_status_code,
            last_headers,
        )

    def _parse_bars(
        self, raw_bars: Sequence[Any], window: Tuple[date, date]
    ) -> List[DailyBar]:
        window_start, window_end = window
        result: List[DailyBar] = []
        seen: Set[date] = set()
        for item in raw_bars:
            if not isinstance(item, Mapping):
                raise SipContractViolationError("HYP_011 bar row must be a mapping.")
            for key in _REQUIRED_BAR_KEYS:
                if item.get(key) is None:
                    raise SipContractViolationError(f"HYP_011 bar missing field '{key}'.")
            t_str = str(item["t"])
            if t_str.endswith("Z"):
                t_str = t_str[:-1] + "+00:00"
            try:
                t_utc = datetime.fromisoformat(t_str).astimezone(timezone.utc)
            except (ValueError, TypeError) as e:
                raise SipContractViolationError(f"HYP_011 malformed timestamp: {e}.") from e
            session_date = t_utc.date()
            if session_date < window_start or session_date > window_end:
                raise SipContractViolationError(
                    f"HYP_011 provider spill: {session_date} outside [{window_start}, {window_end}]."
                )
            if session_date in seen:
                raise SipContractViolationError(f"HYP_011 duplicate session: {session_date}.")
            if session_date.weekday() >= 5:
                raise SipContractViolationError(f"HYP_011 weekend row: {session_date}.")
            if self._calendar.is_holiday(session_date):
                raise SipContractViolationError(f"HYP_011 holiday row: {session_date}.")
            try:
                bar = DailyBar(
                    timestamp_utc=t_utc,
                    open=Decimal(str(item["o"])),
                    high=Decimal(str(item["h"])),
                    low=Decimal(str(item["l"])),
                    close=Decimal(str(item["c"])),
                    volume=Decimal(str(item["v"])),
                )
            except (InvalidOperation, ValueError, TypeError, ValidationError, DomainError) as e:
                raise SipContractViolationError(f"HYP_011 bar validation failed: {e}.") from e
            seen.add(session_date)
            result.append(bar)
        return result


def assert_probe_sessions(bars: Sequence[DailyBar], symbol: str) -> List[date]:
    """Require exactly the 4 expected probe sessions, aligned and valid."""
    sessions = sorted({bar.timestamp_utc.date() for bar in bars})
    if sessions != list(HYP011_EXPECTED_PROBE_SESSIONS):
        raise SipContractViolationError(
            f"HYP_011 {symbol} probe sessions {sessions} != expected "
            f"{list(HYP011_EXPECTED_PROBE_SESSIONS)}."
        )
    if len(bars) != 4:
        raise SipContractViolationError(f"HYP_011 {symbol} expected 4 rows, got {len(bars)}.")
    return sessions
