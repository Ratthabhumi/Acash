"""MEC-0015 Alpaca SIP 1-Minute Bar Contract Qualification.

This module qualifies the Alpaca SIP historical 1-minute OHLCV bar feed for use
in MEC-0015 (Noise-Area Intraday Momentum Strategy). It performs infrastructure
qualification probes ONLY.

STRICT INVARIANTS (from ACASH AGENTS.md and Phase 15 authorization):
1. Temporal Boundary: Only deliberately publication-exposed historical sessions:
   - 2018-06-01, 2019-06-03, 2020-06-01, 2021-06-01, 2022-06-01, 2024-03-01.
   - Any date >= 2024-05-01 triggers immediate fail-closed DataContractError.
   - Any date >= 2025-01-01 triggers immediate fail-closed DataContractError.
2. Provider: Alpaca Historical Bars (/v2/stocks/SPY/bars, feed=sip, timeframe=1Min,
   adjustment=raw).
3. Zero Strategy Execution: No signal computation, no P&L, no Sharpe, no return
   calculation, no backtest. Qualification probes verify data structure ONLY.
4. Zero OOS Access: No market data >= 2024-05-01.
5. HYP_005: NOT CREATED in this module. ResearchReInceptionGate: NOT INVOKED.
6. Fail Closed: DataContractError raised for any contract or governance violation.
7. Secret Non-Leakage: API credentials are never logged or serialized.

Bar Timestamp Semantics (RESOLVED - Alpaca left-edge labeling):
  Alpaca minute bar timestamp = LEFT EDGE of the 1-minute interval.
  Example: timestamp 09:30:00 ET represents trades [09:30:00, 09:31:00).
  Therefore bar 09:30:00 ET = BAR_0930 = first RTH minute.

Author Strategy Time-to-Alpaca Timestamp Mapping (RESOLVED):
  Author "10:00 decision" is based on bar close (right edge) at 10:00 ET.
  This corresponds to bar [09:59:00, 10:00:00), i.e. Alpaca timestamp 09:59:00 ET.
  AUTHOR_DECISION_TIME_TO_ALPACA_BAR_TIMESTAMP:
    Author decision at HH:MM (right-edge) => Alpaca bar timestamp HH:MM - 1min.
  Example: decision at 10:00 ET => Alpaca bar timestamp 09:59:00 ET.
  Next exposure minute begins at Alpaca bar timestamp 10:00:00 ET (bar [10:00, 10:01)).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar, SessionType
from acash.data.qualification.client import (
    AlpacaHistoricalSipClient,
    SipRetrievalResult,
)
from acash.data.qualification.guard import FifteenMinuteAccessGuard
from acash.data.qualification.models import (
    HistoricalSipBar,
    MarketDataFeed,
    PriceAdjustment,
)
from acash.data.qualification.session import RthSessionBounds, VerifiedSessionSchedule

NY_TZ = ZoneInfo("America/New_York")

# ---------------------------------------------------------------------------
# Contract Constants
# ---------------------------------------------------------------------------

MEC_0015_SYMBOL: str = "SPY"
MEC_0015_FEED: MarketDataFeed = MarketDataFeed.SIP
MEC_0015_TIMEFRAME: str = "1Min"
MEC_0015_ADJUSTMENT: PriceAdjustment = PriceAdjustment.RAW

# Authorized probe dates: deliberately publication-exposed historical sessions only
# Per authorization: do NOT access any date >= 2024-05-01, no 2025/2026
MEC_0015_AUTHORIZED_PROBE_DATES: Tuple[date, ...] = (
    date(2018, 6, 1),
    date(2019, 6, 3),
    date(2020, 6, 1),
    date(2021, 6, 1),
    date(2022, 6, 1),
    date(2024, 3, 1),
)

# Absolute OOS and temporal boundary guards
MEC_0015_OOS_FORBIDDEN_DATE: date = date(2024, 5, 1)  # strict: no access >= this date
MEC_0015_FUTURE_FORBIDDEN_DATE: date = date(2025, 1, 1)  # no 2025 or 2026 data

# Governance scope markers
MEC_0015_HYP_005_CREATED: bool = False
MEC_0015_BACKTEST_STARTED: bool = False
MEC_0015_STRATEGY_PNL_COMPUTED: bool = False

# Contractual governance: bar timestamp semantics
MEC_0015_BAR_TIMESTAMP_SEMANTICS: str = "LEFT_EDGE_OF_ONE_MINUTE_INTERVAL"
# Mapping: author decision at HH:MM (right-edge concept) -> Alpaca bar timestamp HH:MM - 1min
MEC_0015_AUTHOR_DECISION_TO_ALPACA_MAPPING: str = (
    "AUTHOR_DECISION_AT_HH:MM_RIGHT_EDGE_EQUALS_ALPACA_TIMESTAMP_(HH:MM - 1min)"
)

# Expected standard regular session bar count
STANDARD_RTH_BAR_COUNT: int = 390  # 09:30:00 through 15:59:00 ET (390 bars, each [t, t+1min))


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------

class Mec0015ProbeSessionStatus(str, Enum):
    """Per-session qualification probe result."""
    PASS = "PASS"
    FAIL_MISSING_BARS = "FAIL_MISSING_BARS"
    FAIL_NON_MONOTONIC = "FAIL_NON_MONOTONIC"
    FAIL_DUPLICATE_TIMESTAMP = "FAIL_DUPLICATE_TIMESTAMP"
    FAIL_INVALID_OHLC = "FAIL_INVALID_OHLC"
    FAIL_INVALID_PRICE = "FAIL_INVALID_PRICE"
    FAIL_NEGATIVE_VOLUME = "FAIL_NEGATIVE_VOLUME"
    FAIL_SCHEMA_VIOLATION = "FAIL_SCHEMA_VIOLATION"
    FAIL_OOS_BOUNDARY = "FAIL_OOS_BOUNDARY"
    FAIL_NETWORK = "FAIL_NETWORK"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class Mec0015BarSchemaCheck:
    """Result of a single OHLCV schema invariant check on one bar."""
    timestamp_et: str
    passed: bool
    violation: Optional[str] = None


@dataclass(frozen=True)
class Mec0015SessionProbeResult:
    """Complete per-session probe result for MEC-0015 bar contract qualification."""
    session_date: str
    status: Mec0015ProbeSessionStatus
    bar_count: int
    expected_bar_count: int
    missing_bar_count: int
    missing_bars_et: List[str]
    first_bar_timestamp_et: Optional[str]
    last_bar_timestamp_et: Optional[str]
    first_bar_open: Optional[str]
    zero_volume_bars_et: List[str]
    schema_violations: List[str]
    is_early_close_session: bool
    canonical_bars_sha256: str
    failure_reason: Optional[str]


@dataclass(frozen=True)
class Mec0015BarContractProbeReport:
    """Aggregated report for the full MEC-0015 bar contract probe."""
    generated_utc: str
    canonical_git_commit: str
    symbol: str
    feed: str
    timeframe: str
    adjustment: str
    bar_timestamp_semantics: str
    author_decision_to_alpaca_mapping: str
    hyp_005_created: bool
    backtest_started: bool
    strategy_pnl_computed: bool
    oos_forbidden_date: str
    probe_sessions: List[Mec0015SessionProbeResult]
    overall_status: str
    total_bars_retrieved: int
    total_missing_bars: int
    manifest_sha256: str


# ---------------------------------------------------------------------------
# OOS guard
# ---------------------------------------------------------------------------

def _validate_probe_date_not_oos(session_date: date) -> None:
    """Fail-closed guard: raise DataContractError if session_date >= OOS boundary."""
    if session_date >= MEC_0015_OOS_FORBIDDEN_DATE:
        raise DataContractError(
            f"MEC-0015 probe date {session_date.isoformat()} violates OOS boundary. "
            f"No access permitted on or after {MEC_0015_OOS_FORBIDDEN_DATE.isoformat()}. "
            f"Fail-closed."
        )
    if session_date >= MEC_0015_FUTURE_FORBIDDEN_DATE:
        raise DataContractError(
            f"MEC-0015 probe date {session_date.isoformat()} is in the prohibited 2025+ future window. "
            f"Fail-closed."
        )


def _validate_probe_date_authorized(session_date: date) -> None:
    """Fail-closed guard: raise DataContractError if date not in authorized probe set."""
    if session_date not in MEC_0015_AUTHORIZED_PROBE_DATES:
        raise DataContractError(
            f"MEC-0015 probe date {session_date.isoformat()} is NOT in the authorized probe set. "
            f"Only {[d.isoformat() for d in MEC_0015_AUTHORIZED_PROBE_DATES]} are authorized. "
            f"Fail-closed."
        )


# ---------------------------------------------------------------------------
# Canonical SHA-256 for MEC-0015 bars
# ---------------------------------------------------------------------------

def compute_mec0015_session_bars_sha256(bars: Sequence[HistoricalSipBar]) -> str:
    """Compute deterministic SHA-256 over normalized bar representations for MEC-0015."""
    hasher = hashlib.sha256()
    for b in bars:
        vwap_str = str(b.provider_vwap) if b.provider_vwap is not None else "NONE"
        tc_str = str(b.trade_count) if b.trade_count is not None else "NONE"
        record_line = (
            f"{b.timestamp_utc.isoformat()}|{b.open}|{b.high}|{b.low}|{b.close}|"
            f"{b.volume}|{tc_str}|{vwap_str}\n"
        )
        hasher.update(record_line.encode("utf-8"))
    return hasher.hexdigest()


def compute_mec0015_report_sha256(report_dict: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 over a serialized probe report dictionary."""
    canonical = json.dumps(report_dict, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Per-session probe
# ---------------------------------------------------------------------------

def _qualify_session_bars(
    session_date: date,
    bars: Sequence[HistoricalSipBar],
    calendar: NyseCa1Calendar,
) -> Mec0015SessionProbeResult:
    """Run all data quality checks on the bars retrieved for one session."""
    # Determine session type and expected bar count
    try:
        session_info = calendar.get_session(session_date)
        is_early_close = (session_info.session_type == SessionType.EARLY_CLOSE)
        expected_count = 210 if is_early_close else STANDARD_RTH_BAR_COUNT
    except Exception:
        is_early_close = False
        expected_count = STANDARD_RTH_BAR_COUNT

    session_status = Mec0015ProbeSessionStatus.PASS
    schema_violations: List[str] = []
    missing_bars_et: List[str] = []
    zero_volume_bars_et: List[str] = []
    failure_reason: Optional[str] = None

    # Build expected timestamp set for completeness check
    rth_open = datetime.combine(session_date, time(9, 30, 0), tzinfo=NY_TZ)
    rth_close_ts = rth_open + timedelta(minutes=expected_count)

    expected_utc_set: set[datetime] = set()
    curr = rth_open.astimezone(timezone.utc)
    close_utc = rth_close_ts.astimezone(timezone.utc)
    while curr < close_utc:
        expected_utc_set.add(curr)
        curr += timedelta(minutes=1)

    # Gather bar timestamps
    rth_bars: List[HistoricalSipBar] = []
    for b in bars:
        ny_ts = b.timestamp_utc.astimezone(NY_TZ)
        bar_time = ny_ts.time()
        if time(9, 30, 0) <= bar_time < time(16, 0, 0):
            rth_bars.append(b)

    observed_utc = {b.timestamp_utc for b in rth_bars}

    # Missing bars
    for expected_ts in sorted(expected_utc_set):
        if expected_ts not in observed_utc:
            et_label = expected_ts.astimezone(NY_TZ).strftime("%H:%M ET")
            missing_bars_et.append(et_label)
    if missing_bars_et:
        session_status = Mec0015ProbeSessionStatus.FAIL_MISSING_BARS
        failure_reason = f"{len(missing_bars_et)} required minute bars absent"

    # Monotonicity and duplicate
    seen_ts: set[datetime] = set()
    prev_ts: Optional[datetime] = None
    for b in rth_bars:
        t = b.timestamp_utc
        if t in seen_ts:
            session_status = Mec0015ProbeSessionStatus.FAIL_DUPLICATE_TIMESTAMP
            schema_violations.append(f"Duplicate timestamp: {t.astimezone(NY_TZ).strftime('%H:%M ET')}")
            failure_reason = failure_reason or "Duplicate timestamp"
        seen_ts.add(t)
        if prev_ts is not None and t < prev_ts:
            session_status = Mec0015ProbeSessionStatus.FAIL_NON_MONOTONIC
            schema_violations.append(
                f"Non-monotonic: {t.astimezone(NY_TZ).strftime('%H:%M ET')} after {prev_ts.astimezone(NY_TZ).strftime('%H:%M ET')}"
            )
            failure_reason = failure_reason or "Non-monotonic timestamps"
        prev_ts = t

    # OHLC invariants
    for b in rth_bars:
        et_ts = b.timestamp_utc.astimezone(NY_TZ).strftime("%H:%M ET")
        # Prices must be positive
        if b.open <= 0 or b.high <= 0 or b.low <= 0 or b.close <= 0:
            schema_violations.append(f"Non-positive price at {et_ts}")
            if session_status == Mec0015ProbeSessionStatus.PASS:
                session_status = Mec0015ProbeSessionStatus.FAIL_INVALID_PRICE
                failure_reason = "Non-positive price detected"
        # high >= max(open, close)
        max_body = max(b.open, b.close)
        min_body = min(b.open, b.close)
        if b.high < max_body or b.low > min_body or b.high < b.low:
            schema_violations.append(f"OHLC bound violation at {et_ts}")
            if session_status == Mec0015ProbeSessionStatus.PASS:
                session_status = Mec0015ProbeSessionStatus.FAIL_INVALID_OHLC
                failure_reason = "OHLC bounds violated"
        # Volume non-negative
        if b.volume < 0:
            schema_violations.append(f"Negative volume at {et_ts}")
            if session_status == Mec0015ProbeSessionStatus.PASS:
                session_status = Mec0015ProbeSessionStatus.FAIL_NEGATIVE_VOLUME
                failure_reason = "Negative volume detected"
        # Zero-volume bars (informational)
        if b.volume == 0:
            zero_volume_bars_et.append(et_ts)

    # First/last bar timestamps in ET
    first_et = rth_bars[0].timestamp_utc.astimezone(NY_TZ).strftime("%H:%M:%S ET") if rth_bars else None
    last_et = rth_bars[-1].timestamp_utc.astimezone(NY_TZ).strftime("%H:%M:%S ET") if rth_bars else None
    first_open = str(rth_bars[0].open) if rth_bars else None

    bars_sha = compute_mec0015_session_bars_sha256(rth_bars)

    return Mec0015SessionProbeResult(
        session_date=session_date.isoformat(),
        status=session_status,
        bar_count=len(rth_bars),
        expected_bar_count=expected_count,
        missing_bar_count=len(missing_bars_et),
        missing_bars_et=missing_bars_et,
        first_bar_timestamp_et=first_et,
        last_bar_timestamp_et=last_et,
        first_bar_open=first_open,
        zero_volume_bars_et=zero_volume_bars_et,
        schema_violations=schema_violations,
        is_early_close_session=is_early_close,
        canonical_bars_sha256=bars_sha,
        failure_reason=failure_reason,
    )


# ---------------------------------------------------------------------------
# Main probe orchestrator
# ---------------------------------------------------------------------------

class Mec0015BarContractProbe:
    """Infrastructure qualification probe for MEC-0015 Alpaca SIP 1-minute bars.

    Governance scope:
    - HYP_005 is NOT created.
    - No strategy signals, P&L, or return computations.
    - Only authorized probe dates accessed.
    - OOS guard is fail-closed.
    """

    def __init__(
        self,
        client: Optional[AlpacaHistoricalSipClient] = None,
        calendar: Optional[NyseCa1Calendar] = None,
        guard: Optional[FifteenMinuteAccessGuard] = None,
    ) -> None:
        self._guard = guard or FifteenMinuteAccessGuard()
        self._client = client or AlpacaHistoricalSipClient(guard=self._guard)
        self._calendar = calendar or NyseCa1Calendar()

    def run_probe(
        self,
        probe_dates: Optional[Sequence[date]] = None,
    ) -> Mec0015BarContractProbeReport:
        """Run bar contract infrastructure probe for MEC-0015.

        Args:
            probe_dates: Optional override of probe dates. If None, uses all authorized
                         probe dates. Only dates in MEC_0015_AUTHORIZED_PROBE_DATES allowed.

        Returns:
            Mec0015BarContractProbeReport with per-session qualification results.
        """
        import subprocess
        from datetime import datetime as _dt

        dates_to_probe = list(probe_dates) if probe_dates else list(MEC_0015_AUTHORIZED_PROBE_DATES)

        # Pre-validate all dates fail-closed before any network access
        for d in dates_to_probe:
            _validate_probe_date_not_oos(d)
            _validate_probe_date_authorized(d)

        generated_utc = _dt.now(timezone.utc).isoformat()
        try:
            git_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            git_sha = "UNKNOWN"

        session_results: List[Mec0015SessionProbeResult] = []
        total_bars = 0
        total_missing = 0

        for probe_date in sorted(dates_to_probe):
            result = self._probe_single_session(probe_date)
            session_results.append(result)
            total_bars += result.bar_count
            total_missing += result.missing_bar_count

        # Compute overall status
        all_pass = all(r.status == Mec0015ProbeSessionStatus.PASS for r in session_results)
        overall_status = "PASS" if all_pass else "PARTIAL_FAIL"

        # Compute manifest SHA-256
        report_dict: Dict[str, Any] = {
            "generated_utc": generated_utc,
            "canonical_git_commit": git_sha,
            "symbol": MEC_0015_SYMBOL,
            "feed": MEC_0015_FEED.value,
            "timeframe": MEC_0015_TIMEFRAME,
            "adjustment": MEC_0015_ADJUSTMENT.value,
            "bar_timestamp_semantics": MEC_0015_BAR_TIMESTAMP_SEMANTICS,
            "author_decision_to_alpaca_mapping": MEC_0015_AUTHOR_DECISION_TO_ALPACA_MAPPING,
            "hyp_005_created": MEC_0015_HYP_005_CREATED,
            "backtest_started": MEC_0015_BACKTEST_STARTED,
            "strategy_pnl_computed": MEC_0015_STRATEGY_PNL_COMPUTED,
            "oos_forbidden_date": MEC_0015_OOS_FORBIDDEN_DATE.isoformat(),
            "overall_status": overall_status,
            "total_bars_retrieved": total_bars,
            "total_missing_bars": total_missing,
            "sessions": [
                {
                    "date": r.session_date,
                    "status": r.status.value,
                    "bar_count": r.bar_count,
                    "expected": r.expected_bar_count,
                    "missing": r.missing_bar_count,
                    "sha256": r.canonical_bars_sha256,
                }
                for r in session_results
            ],
        }
        manifest_sha256 = compute_mec0015_report_sha256(report_dict)

        return Mec0015BarContractProbeReport(
            generated_utc=generated_utc,
            canonical_git_commit=git_sha,
            symbol=MEC_0015_SYMBOL,
            feed=MEC_0015_FEED.value,
            timeframe=MEC_0015_TIMEFRAME,
            adjustment=MEC_0015_ADJUSTMENT.value,
            bar_timestamp_semantics=MEC_0015_BAR_TIMESTAMP_SEMANTICS,
            author_decision_to_alpaca_mapping=MEC_0015_AUTHOR_DECISION_TO_ALPACA_MAPPING,
            hyp_005_created=MEC_0015_HYP_005_CREATED,
            backtest_started=MEC_0015_BACKTEST_STARTED,
            strategy_pnl_computed=MEC_0015_STRATEGY_PNL_COMPUTED,
            oos_forbidden_date=MEC_0015_OOS_FORBIDDEN_DATE.isoformat(),
            probe_sessions=session_results,
            overall_status=overall_status,
            total_bars_retrieved=total_bars,
            total_missing_bars=total_missing,
            manifest_sha256=manifest_sha256,
        )

    def _probe_single_session(self, session_date: date) -> Mec0015SessionProbeResult:
        """Probe a single session; return result with fail-closed error handling."""
        # Double-check OOS guard before any network call
        _validate_probe_date_not_oos(session_date)

        try:
            start_utc, end_utc = RthSessionBounds.get_rth_query_interval(session_date)
            retrieval: SipRetrievalResult = self._client.fetch_historical_bars(
                symbol=MEC_0015_SYMBOL,
                start_utc=start_utc,
                end_utc=end_utc,
                feed=MEC_0015_FEED,
                adjustment=MEC_0015_ADJUSTMENT,
                timeframe=MEC_0015_TIMEFRAME,
            )
            return _qualify_session_bars(session_date, retrieval.bars, self._calendar)
        except DataContractError:
            raise
        except Exception as e:
            return Mec0015SessionProbeResult(
                session_date=session_date.isoformat(),
                status=Mec0015ProbeSessionStatus.FAIL_NETWORK,
                bar_count=0,
                expected_bar_count=STANDARD_RTH_BAR_COUNT,
                missing_bar_count=STANDARD_RTH_BAR_COUNT,
                missing_bars_et=[],
                first_bar_timestamp_et=None,
                last_bar_timestamp_et=None,
                first_bar_open=None,
                zero_volume_bars_et=[],
                schema_violations=[f"Network/client error: {e}"],
                is_early_close_session=False,
                canonical_bars_sha256="ERROR",
                failure_reason=f"Network or client error: {type(e).__name__}: {e}",
            )
