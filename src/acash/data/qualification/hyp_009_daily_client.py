# src/acash/data/qualification/hyp_009_daily_client.py
"""HYP 009-specific Alpaca client for daily SIP bars.

Frozen HYP_009 provider contract (CORE-001 / HYP_009 R1 + pre-R2 clarification):

- symbol = SPY
- timeframe = 1Day
- feed = SIP
- allowed adjustments = SPLIT, RAW
  (signal prices adjustment=split; execution/valuation adjustment=raw)
- authorized request window: 2016-01-01 <= start_date <= end_date <= 2020-12-31

Pre-network enforcement (BEFORE any HTTP execution):

- symbol != SPY -> rejected
- timeframe != 1Day -> rejected
- feed != SIP -> rejected
- unsupported adjustment -> rejected
- start < 2016-01-01, end > 2020-12-31, or start > end -> rejected

This module deliberately does NOT use FifteenMinuteAccessGuard: the 15-minute
recency / 390-minute-session / 15:59-final-minute / early-close-exclusion
semantics belong to the intraday 1Min path. Daily history uses the dedicated
Hyp009PreNetworkGuard date-boundary authority below.

Response validation fails closed (no silent trimming of provider spill):

- row before requested start / after requested end -> rejected
- duplicate session -> rejected
- weekend row / full-holiday row -> rejected
- legitimate early-close session -> accepted (CA-1 authority)
- null/malformed values, non-finite numerics, non-positive OHLC,
  invalid OHLC geometry, negative volume -> rejected

No changes are made to the existing AlpacaHistoricalSipClient - this
implementation lives in a separate module so that HYP_003 codepaths are
completely untouched.
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


HYP009_SYMBOL: str = "SPY"
HYP009_TIMEFRAME: str = "1Day"
HYP009_FEED: MarketDataFeed = MarketDataFeed.SIP
HYP009_ALLOWED_ADJUSTMENTS: FrozenSet[PriceAdjustment] = frozenset(
    {PriceAdjustment.SPLIT, PriceAdjustment.RAW}
)
HYP009_MIN_DATE: date = date(2016, 1, 1)
HYP009_MAX_DATE: date = date(2020, 12, 31)

_REQUIRED_BAR_KEYS: Tuple[str, ...] = ("t", "o", "h", "l", "c", "v")


def inclusive_date_window_to_utc_bounds(
    start_date: date, end_date: date
) -> Tuple[datetime, datetime]:
    """Convert an inclusive calendar-date window into provider timestamp bounds.

    Maps the inclusive start date to UTC start-of-day (00:00:00Z) and the
    inclusive end date to UTC end-of-day (23:59:59.999999Z), so daily bars
    timestamped after 00:00Z for the end session (e.g. Alpaca 1Day bars near
    04:00:00Z) remain inside the provider query. The SCIENTIFIC session-date
    window is unchanged, and response spill validation is NOT loosened: any
    returned session date outside [start_date, end_date] is still rejected.

    This helper is a pure converter; the frozen authorized-window contract
    (2016-01-01..2020-12-31) is still enforced by Hyp009PreNetworkGuard at
    fetch time.
    """
    if start_date > end_date:
        raise SipContractViolationError(
            f"Inclusive date window start ({start_date}) must not exceed "
            f"end ({end_date})."
        )
    start_utc = datetime(
        start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc
    )
    end_utc = datetime(
        end_date.year,
        end_date.month,
        end_date.day,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )
    return start_utc, end_utc


class Hyp009PreNetworkGuard:
    """Dedicated HYP_009 pre-network temporal guard (date-boundary authority).

    Enforces the frozen authorized window 2016-01-01..2020-12-31 at date
    granularity. This guard carries NO 15-minute recency semantics, NO
    390-minute-session requirement, NO 15:59 final-minute requirement, and NO
    early-close exclusion. It is the sole date-boundary authority for the
    HYP_009 daily path.
    """

    def __init__(
        self,
        min_date: date = HYP009_MIN_DATE,
        max_date: date = HYP009_MAX_DATE,
    ) -> None:
        if min_date > max_date:
            raise DataContractError(
                f"Hyp009PreNetworkGuard min_date ({min_date}) must not exceed "
                f"max_date ({max_date})."
            )
        self.min_date = min_date
        self.max_date = max_date

    def validate_window(self, start_utc: datetime, end_utc: datetime) -> Tuple[date, date]:
        """Validate the requested window BEFORE any network execution.

        Returns the normalized (start_date, end_date) pair on success.

        Raises:
            DataContractError: naive (timezone-unaware) datetimes.
            SipContractViolationError: any authorized-window violation.
        """
        if start_utc.tzinfo is None or end_utc.tzinfo is None:
            raise DataContractError(
                "HYP_009 window datetimes must be timezone-aware UTC."
            )
        start_date = start_utc.astimezone(timezone.utc).date()
        end_date = end_utc.astimezone(timezone.utc).date()
        if start_date > end_date:
            raise SipContractViolationError(
                f"HYP_009 window start_date ({start_date}) must not exceed "
                f"end_date ({end_date})."
            )
        if start_date < self.min_date:
            raise SipContractViolationError(
                f"HYP_009 window start_date ({start_date}) precedes the authorized "
                f"lower bound ({self.min_date})."
            )
        if end_date > self.max_date:
            raise SipContractViolationError(
                f"HYP_009 window end_date ({end_date}) exceeds the authorized "
                f"upper bound ({self.max_date})."
            )
        return start_date, end_date


@dataclass(frozen=True)
class Hyp009RetrievalResult:
    """Result of a completed paginated HYP_009 daily bars retrieval."""

    bars: List[DailyBar]
    pages_raw_bytes: List[bytes]
    pages_metadata: List[SipPageMetadata]
    http_status_code: int
    response_headers: Dict[str, str]
    feed_requested: str
    feed_response_provenance: str
    asof: Optional[str] = None


def assert_split_raw_alignment(
    split_bars: Sequence[DailyBar],
    raw_bars: Sequence[DailyBar],
) -> List[date]:
    """Require split/raw session-date sets to be exactly equal (fail closed).

    Per the frozen pre-R2 accounting clarification, split history is qualified
    only against the same authorized window as raw valuation data. Any date
    mismatch (split-only or raw-only sessions) is a contract violation: no
    interpolation, no filling, no silent dropping of unmatched dates.

    Returns the sorted aligned session dates on success.
    """
    split_dates = {bar.timestamp_utc.date() for bar in split_bars}
    raw_dates = {bar.timestamp_utc.date() for bar in raw_bars}
    if split_dates != raw_dates:
        raise SipContractViolationError(
            "HYP_009 split/raw session-date sets differ: "
            f"split_only={sorted(split_dates - raw_dates)}, "
            f"raw_only={sorted(raw_dates - split_dates)}."
        )
    return sorted(split_dates)


class HYP009AlpacaClient:
    """Client for fetching **daily** SIP bars via Alpaca under the HYP_009 contract."""

    def __init__(
        self,
        credential_provider: Optional[AlpacaCredentialProvider] = None,
        guard: Optional[Hyp009PreNetworkGuard] = None,
        calendar: Optional[NyseCa1Calendar] = None,
        base_url: str = "https://data.alpaca.markets",
        transport: Optional[httpx.BaseTransport] = None,
        max_pages: int = 50,
        max_retries_429: int = 3,
        retry_delay_seconds: float = 1.0,
        http_attempt_listener: Optional[Callable[[], None]] = None,
    ) -> None:
        self._credentials_provider = credential_provider or EnvAlpacaCredentialProvider()
        self._guard = guard or Hyp009PreNetworkGuard()
        self._calendar = calendar or NyseCa1Calendar()
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._max_pages = max_pages
        self._max_retries_429 = max_retries_429
        self._retry_delay_seconds = retry_delay_seconds
        # Auditable hook invoked once per ACTUAL provider HTTP execution
        # (first attempts, 429 retries, and pagination pages each count).
        # Carries no credentials and performs no logging itself.
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

    def fetch_historical_bars(
        self,
        symbol: str,
        start_utc: datetime,
        end_utc: datetime,
        feed: MarketDataFeed = MarketDataFeed.SIP,
        adjustment: PriceAdjustment = PriceAdjustment.RAW,
        timeframe: str = "1Day",
        limit: int = 10000,
        asof: Optional[str] = None,
    ) -> Hyp009RetrievalResult:
        """Fetch daily SIP bars with strict HYP_009 contract enforcement.

        Every precondition below is checked BEFORE any HTTP execution; a
        forbidden request performs zero network calls.
        """
        sym = symbol.strip().upper()
        if not sym:
            raise DataContractError("Symbol must be a non-empty string.")
        if sym != HYP009_SYMBOL:
            raise SipContractViolationError(
                f"HYP_009 client requires symbol='{HYP009_SYMBOL}', got '{sym}'."
            )
        if feed != MarketDataFeed.SIP:
            raise SipContractViolationError(
                f"HYP_009 client requires feed='sip', got '{feed}'."
            )
        if adjustment not in HYP009_ALLOWED_ADJUSTMENTS:
            raise SipContractViolationError(
                f"HYP_009 client requires adjustment in "
                f"{{'split', 'raw'}}, got '{adjustment}'."
            )
        if timeframe != HYP009_TIMEFRAME:
            raise SipContractViolationError(
                f"HYP_009 client requires timeframe='{HYP009_TIMEFRAME}', got '{timeframe}'."
            )

        start_date, end_date = self._guard.validate_window(start_utc, end_utc)

        start_str = start_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        url = f"{self._base_url}/v2/stocks/{sym}/bars"
        headers = self._get_auth_headers()

        pages_raw_bytes: List[bytes] = []
        pages_metadata: List[SipPageMetadata] = []
        all_bars: List[DailyBar] = []
        seen_dates: Set[date] = set()
        next_page_token: Optional[str] = None
        page_index = 0
        last_status_code = 0
        last_headers: Dict[str, str] = {}

        with httpx.Client(transport=self._transport) as client:
            while True:
                page_index += 1
                if page_index > self._max_pages:
                    raise DataContractError(
                        f"Pagination exceeded maximum allowed pages ({self._max_pages}); aborting."
                    )

                params: Dict[str, Any] = {
                    "timeframe": timeframe,
                    "feed": feed.value,
                    "adjustment": adjustment.value,
                    "start": start_str,
                    "end": end_str,
                    "limit": limit,
                    "sort": "asc",
                }
                if asof:
                    params["asof"] = asof.strip()
                if next_page_token:
                    params["page_token"] = next_page_token

                response = self._execute_request_with_retry(client, url, headers, params)
                last_status_code = response.status_code
                last_headers = dict(response.headers)

                if response.status_code == 401:
                    raise AlpacaCredentialError("Alpaca authentication failed (HTTP 401).")
                if response.status_code == 403:
                    raise DataContractError("Alpaca access forbidden (HTTP 403). SIP feed denied.")
                if response.status_code != 200:
                    raise DataContractError(
                        f"Alpaca historical data query failed with HTTP status {response.status_code}."
                    )

                raw_bytes = response.content
                page_sha256 = compute_page_sha256(raw_bytes)
                pages_raw_bytes.append(raw_bytes)

                try:
                    payload = response.json()
                except Exception as e:
                    raise DataContractError(f"Failed to parse Alpaca response as JSON: {e}") from e

                raw_bars = payload.get("bars") or []
                if isinstance(raw_bars, dict):
                    raw_bars = raw_bars.get(sym, [])
                if not isinstance(raw_bars, list):
                    raise SipContractViolationError(
                        "HYP_009 response 'bars' payload must be a list (or a symbol-keyed mapping)."
                    )

                parsed_page = self._parse_daily_bars(
                    raw_bars, start_date, end_date, seen_dates
                )
                all_bars.extend(parsed_page)

                token = payload.get("next_page_token")
                pages_metadata.append(
                    SipPageMetadata(
                        page_index=page_index,
                        bar_count=len(parsed_page),
                        raw_sha256=page_sha256,
                        byte_length=len(raw_bytes),
                        relative_artifact_path=f"page-{page_index:04d}.raw.json",
                        page_token=next_page_token,
                        next_page_token=token,
                    )
                )

                if not token or token == next_page_token:
                    break
                next_page_token = str(token)

        feed_provenance = "UNVERIFIED"
        for k, v in last_headers.items():
            if "feed" in k.lower() and "sip" in v.lower():
                feed_provenance = "FEED_CONFIRMED_IN_HEADER"
                break

        return Hyp009RetrievalResult(
            bars=all_bars,
            pages_raw_bytes=pages_raw_bytes,
            pages_metadata=pages_metadata,
            http_status_code=last_status_code,
            response_headers=last_headers,
            feed_requested=feed.value,
            feed_response_provenance=feed_provenance,
            asof=asof,
        )

    def _execute_request_with_retry(
        self, client: httpx.Client, url: str, headers: Dict[str, str], params: Dict[str, Any]
    ) -> httpx.Response:
        retries = 0
        while True:
            try:
                if self._http_attempt_listener is not None:
                    self._http_attempt_listener()
                resp = client.get(url, headers=headers, params=params, timeout=30.0)
                if resp.status_code == 429:
                    retries += 1
                    if retries > self._max_retries_429:
                        raise DataContractError(
                            f"Alpaca rate limit exceeded (HTTP 429). Retry budget ({self._max_retries_429}) exhausted."
                        )
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else self._retry_delay_seconds * (2 ** (retries - 1))
                    time.sleep(delay)
                    continue
                return resp
            except httpx.RequestError as e:
                raise DataContractError(f"HTTP request to Alpaca failed: {e}") from e

    def _parse_daily_bars(
        self,
        raw_bars: Sequence[Any],
        window_start: date,
        window_end: date,
        seen_dates: Set[date],
    ) -> List[DailyBar]:
        """Parse and validate one response page (fail closed, no silent trimming)."""
        result: List[DailyBar] = []
        for item in raw_bars:
            if not isinstance(item, Mapping):
                raise SipContractViolationError(
                    "HYP_009 daily bar row must be a mapping object."
                )
            for key in _REQUIRED_BAR_KEYS:
                if item.get(key) is None:
                    raise SipContractViolationError(
                        f"HYP_009 daily bar row has null/missing field '{key}': {item}."
                    )

            t_raw = item["t"]
            try:
                t_str = str(t_raw)
                if t_str.endswith("Z"):
                    t_str = t_str[:-1] + "+00:00"
                t_utc = datetime.fromisoformat(t_str).astimezone(timezone.utc)
            except (ValueError, TypeError) as e:
                raise SipContractViolationError(
                    f"HYP_009 daily bar has malformed timestamp: {t_raw!r}."
                ) from e
            if t_utc.tzinfo is None:
                raise SipContractViolationError(
                    f"HYP_009 daily bar timestamp must be timezone-aware: {t_raw!r}."
                )
            session_date = t_utc.date()

            if session_date < window_start:
                raise SipContractViolationError(
                    f"HYP_009 provider spill: session {session_date} precedes "
                    f"requested start {window_start}."
                )
            if session_date > window_end:
                raise SipContractViolationError(
                    f"HYP_009 provider spill: session {session_date} exceeds "
                    f"requested end {window_end}."
                )
            if session_date in seen_dates:
                raise SipContractViolationError(
                    f"HYP_009 duplicate session in provider response: {session_date}."
                )

            if session_date.weekday() >= 5:
                raise SipContractViolationError(
                    f"HYP_009 weekend row in provider response: {session_date}."
                )
            if self._calendar.is_holiday(session_date):
                reason = self._calendar.get_holiday_reason(session_date)
                raise SipContractViolationError(
                    f"HYP_009 full-holiday row in provider response: {session_date} ({reason})."
                )

            try:
                open_val = Decimal(str(item["o"]))
                high_val = Decimal(str(item["h"]))
                low_val = Decimal(str(item["l"]))
                close_val = Decimal(str(item["c"]))
                volume_val = Decimal(str(item["v"]))
            except (InvalidOperation, ValueError, TypeError) as e:
                raise SipContractViolationError(
                    f"HYP_009 daily bar has malformed numeric values: {item}."
                ) from e

            try:
                bar = DailyBar(
                    timestamp_utc=t_utc,
                    open=open_val,
                    high=high_val,
                    low=low_val,
                    close=close_val,
                    volume=volume_val,
                )
            except (ValidationError, DomainError) as e:
                # Normalize every model-validation failure (pydantic-wrapped or
                # raw domain errors) into the single HYP_009 contract exception.
                raise SipContractViolationError(
                    f"HYP_009 daily bar failed OHLCV validation: {e}."
                ) from e

            seen_dates.add(session_date)
            result.append(bar)
        return result
