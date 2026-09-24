"""HYP_010 dedicated Alpaca SIP daily-bars qualification client.

Separate module so HYP_003/HYP_009 codepaths are untouched. Tiny-probe scope
only: exactly 2017-01-03..2017-01-06, symbols SPY/VEU/AGG/BIL, 1Day SIP,
adjustments split/raw. Every actual HTTP execution is counted via listener.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional, Sequence, Set

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


HYP010_SYMBOLS: FrozenSet[str] = frozenset({"SPY", "VEU", "AGG", "BIL"})
HYP010_TIMEFRAME: str = "1Day"
HYP010_FEED: MarketDataFeed = MarketDataFeed.SIP
HYP010_ALLOWED_ADJUSTMENTS: FrozenSet[PriceAdjustment] = frozenset(
    {PriceAdjustment.SPLIT, PriceAdjustment.RAW}
)
HYP010_PROBE_START: date = date(2017, 1, 3)
HYP010_PROBE_END: date = date(2017, 1, 6)
HYP010_EXPECTED_PROBE_SESSIONS = (
    date(2017, 1, 3),
    date(2017, 1, 4),
    date(2017, 1, 5),
    date(2017, 1, 6),
)

_REQUIRED_BAR_KEYS = ("t", "o", "h", "l", "c", "v")


@dataclass(frozen=True)
class Hyp010RetrievalResult:
    bars: List[DailyBar]
    pages_raw_bytes: List[bytes]
    pages_metadata: List[SipPageMetadata]
    http_status_code: int
    response_headers: Dict[str, str]
    feed_requested: str
    feed_response_provenance: str
    symbol: str
    adjustment: str


class Hyp010PreNetworkGuard:
    """Pre-network guard: exact tiny-probe scope, allowlisted symbols only."""

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
        if sym not in HYP010_SYMBOLS:
            raise SipContractViolationError(
                f"HYP_010 allowlist violation: symbol '{symbol}' not in SPY/VEU/AGG/BIL."
            )
        if timeframe != HYP010_TIMEFRAME:
            raise SipContractViolationError(
                f"HYP_010 requires timeframe='1Day', got '{timeframe}'."
            )
        if feed != MarketDataFeed.SIP:
            raise SipContractViolationError(
                f"HYP_010 requires feed='sip', got '{feed}'."
            )
        if adjustment not in HYP010_ALLOWED_ADJUSTMENTS:
            raise SipContractViolationError(
                f"HYP_010 requires adjustment in {{'split','raw'}}, got '{adjustment}'."
            )
        if start_utc.tzinfo is None or end_utc.tzinfo is None:
            raise DataContractError("HYP_010 window datetimes must be timezone-aware UTC.")
        start_date = start_utc.astimezone(timezone.utc).date()
        end_date = end_utc.astimezone(timezone.utc).date()
        if start_date != HYP010_PROBE_START or end_date != HYP010_PROBE_END:
            raise SipContractViolationError(
                f"HYP_010 tiny-probe window must be exactly "
                f"{HYP010_PROBE_START}..{HYP010_PROBE_END}, got {start_date}..{end_date}."
            )


class HYP010AlpacaClient:
    """Tiny-probe-only Alpaca SIP daily client for HYP_010 qualification."""

    def __init__(
        self,
        credential_provider: Optional[AlpacaCredentialProvider] = None,
        guard: Optional[Hyp010PreNetworkGuard] = None,
        calendar: Optional[NyseCa1Calendar] = None,
        base_url: str = "https://data.alpaca.markets",
        transport: Optional[httpx.BaseTransport] = None,
        max_retries_429: int = 3,
        retry_delay_seconds: float = 1.0,
        http_attempt_listener: Optional[Callable[[], None]] = None,
    ) -> None:
        self._credentials_provider = credential_provider or EnvAlpacaCredentialProvider()
        self._guard = guard or Hyp010PreNetworkGuard()
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
    ) -> Hyp010RetrievalResult:
        """Fetch the exact tiny probe window; guard rejects anything else pre-network."""
        self._guard.validate_request(symbol, start_utc, end_utc, feed, adjustment, timeframe)
        sym = symbol.strip().upper()
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
        seen_dates: Set[date] = set()
        page_index = 0
        next_page_token: Optional[str] = None
        last_status_code = 0
        last_headers: Dict[str, str] = {}
        with httpx.Client(transport=self._transport) as client:
            while True:
                page_index += 1
                if page_index > 5:
                    raise DataContractError("HYP_010 tiny probe exceeded page budget.")
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
                    raise SipContractViolationError("HYP_010 'bars' payload must be a list.")
                parsed = self._parse_bars(raw_bars)
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
        return Hyp010RetrievalResult(
            bars=all_bars,
            pages_raw_bytes=pages_raw_bytes,
            pages_metadata=pages_metadata,
            http_status_code=last_status_code,
            response_headers=last_headers,
            feed_requested=feed.value,
            feed_response_provenance="alpaca-sip",
            symbol=sym,
            adjustment=adjustment.value,
        )

    def _parse_bars(self, raw_bars: Sequence[Any]) -> List[DailyBar]:
        result: List[DailyBar] = []
        seen: Set[date] = set()
        for item in raw_bars:
            if not isinstance(item, Mapping):
                raise SipContractViolationError("HYP_010 bar row must be a mapping.")
            for key in _REQUIRED_BAR_KEYS:
                if item.get(key) is None:
                    raise SipContractViolationError(f"HYP_010 bar missing field '{key}'.")
            t_str = str(item["t"])
            if t_str.endswith("Z"):
                t_str = t_str[:-1] + "+00:00"
            try:
                t_utc = datetime.fromisoformat(t_str).astimezone(timezone.utc)
            except (ValueError, TypeError) as e:
                raise SipContractViolationError(f"HYP_010 malformed timestamp: {e}.") from e
            session_date = t_utc.date()
            if session_date < HYP010_PROBE_START or session_date > HYP010_PROBE_END:
                raise SipContractViolationError(
                    f"HYP_010 provider spill: {session_date} outside probe window."
                )
            if session_date in seen:
                raise SipContractViolationError(f"HYP_010 duplicate session: {session_date}.")
            if session_date.weekday() >= 5:
                raise SipContractViolationError(f"HYP_010 weekend row: {session_date}.")
            if self._calendar.is_holiday(session_date):
                raise SipContractViolationError(f"HYP_010 holiday row: {session_date}.")
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
                raise SipContractViolationError(f"HYP_010 bar validation failed: {e}.") from e
            seen.add(session_date)
            result.append(bar)
        return result


def assert_probe_sessions(bars: Sequence[DailyBar], symbol: str) -> List[date]:
    """Require exactly the 4 expected probe sessions, aligned and valid."""
    sessions = sorted({bar.timestamp_utc.date() for bar in bars})
    if sessions != list(HYP010_EXPECTED_PROBE_SESSIONS):
        raise SipContractViolationError(
            f"HYP_010 {symbol} probe sessions {sessions} != expected "
            f"{list(HYP010_EXPECTED_PROBE_SESSIONS)}."
        )
    if len(bars) != 4:
        raise SipContractViolationError(f"HYP_010 {symbol} expected 4 rows, got {len(bars)}.")
    return sessions
