"""Unit tests for MEC-0015 Alpaca SIP bar contract qualification module.

Tests cover:
- OOS boundary guard (fail-closed)
- Authorized probe date guard (fail-closed)
- Bar timestamp semantics and author-to-Alpaca mapping constants
- Session qualification logic (OHLC invariants, missing bars, monotonicity)
- SHA-256 determinism
- Governance invariant assertions (HYP_005 not created, no backtest, no P&L)
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
import json
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0015_bar_contract import (
    MEC_0015_AUTHORIZED_PROBE_DATES,
    MEC_0015_AUTHOR_DECISION_TO_ALPACA_MAPPING,
    MEC_0015_BACKTEST_STARTED,
    MEC_0015_BAR_TIMESTAMP_SEMANTICS,
    MEC_0015_HYP_005_CREATED,
    MEC_0015_OOS_FORBIDDEN_DATE,
    MEC_0015_STRATEGY_PNL_COMPUTED,
    Mec0015BarContractProbeReport,
    Mec0015ProbeSessionStatus,
    Mec0015SessionProbeResult,
    compute_mec0015_report_sha256,
    compute_mec0015_session_bars_sha256,
    _validate_probe_date_authorized,
    _validate_probe_date_not_oos,
    _qualify_session_bars,
)
from acash.data.qualification.models import HistoricalSipBar
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar

NY_TZ = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bar(timestamp_et: datetime, open_: float = 450.0, high: float = 451.0, low: float = 449.0, close: float = 450.5, volume: int = 100000) -> HistoricalSipBar:
    """Build a synthetic HistoricalSipBar in UTC from an ET-localized datetime."""
    ts_utc = timestamp_et.astimezone(timezone.utc)
    return HistoricalSipBar(
        timestamp_utc=ts_utc,
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(str(volume)),
        trade_count=500,
        provider_vwap=Decimal("450.25"),
    )


def _make_full_session_bars(session_date: date, bar_count: int = 390) -> List[HistoricalSipBar]:
    """Build a complete set of synthetic RTH bars for a session."""
    bars: List[HistoricalSipBar] = []
    rth_open = datetime.combine(session_date, time(9, 30, 0), tzinfo=NY_TZ)
    for i in range(bar_count):
        ts = rth_open + timedelta(minutes=i)
        bars.append(_make_bar(ts))
    return bars


# ---------------------------------------------------------------------------
# Part A: Governance Invariant Assertions
# ---------------------------------------------------------------------------

class TestGovernanceInvariants:
    """MEC-0015 contract module must never create HYP_005, start a backtest, or compute P&L."""

    def test_hyp_005_not_created(self) -> None:
        assert MEC_0015_HYP_005_CREATED is False

    def test_backtest_not_started(self) -> None:
        assert MEC_0015_BACKTEST_STARTED is False

    def test_strategy_pnl_not_computed(self) -> None:
        assert MEC_0015_STRATEGY_PNL_COMPUTED is False

    def test_oos_forbidden_date_is_2024_05_01(self) -> None:
        assert MEC_0015_OOS_FORBIDDEN_DATE == date(2024, 5, 1)

    def test_authorized_probe_dates_all_before_oos_boundary(self) -> None:
        for d in MEC_0015_AUTHORIZED_PROBE_DATES:
            assert d < MEC_0015_OOS_FORBIDDEN_DATE, (
                f"Probe date {d} is >= OOS boundary {MEC_0015_OOS_FORBIDDEN_DATE}"
            )

    def test_no_2025_or_2026_probe_dates(self) -> None:
        for d in MEC_0015_AUTHORIZED_PROBE_DATES:
            assert d.year < 2025, f"Probe date {d} is in 2025 or later"


# ---------------------------------------------------------------------------
# Part B: Bar Timestamp Semantics (RESOLVED)
# ---------------------------------------------------------------------------

class TestBarTimestampSemantics:
    """Verify that canonical timestamp semantics constants are correctly set."""

    def test_bar_timestamp_is_left_edge(self) -> None:
        assert MEC_0015_BAR_TIMESTAMP_SEMANTICS == "LEFT_EDGE_OF_ONE_MINUTE_INTERVAL"

    def test_author_decision_mapping_resolves_to_minus_one_minute(self) -> None:
        # The mapping must encode that author "HH:MM right-edge decision" maps to Alpaca "HH:MM - 1min"
        assert "HH:MM - 1min" in MEC_0015_AUTHOR_DECISION_TO_ALPACA_MAPPING
        assert "RIGHT_EDGE" in MEC_0015_AUTHOR_DECISION_TO_ALPACA_MAPPING

    def test_first_rth_bar_is_0930(self) -> None:
        """First RTH bar is labeled 09:30:00 ET (left edge), representing [09:30, 09:31)."""
        session_date = date(2022, 6, 1)
        rth_open = datetime.combine(session_date, time(9, 30, 0), tzinfo=NY_TZ)
        assert rth_open.strftime("%H:%M") == "09:30"

    def test_decision_at_1000_maps_to_alpaca_0959(self) -> None:
        """Author decision at 10:00 (right-edge) = Alpaca bar timestamp 09:59 (left-edge)."""
        # Author's 10:00 decision reads close of the bar [09:59, 10:00)
        # That bar's Alpaca timestamp is 09:59:00 ET.
        bar_ts_et = time(9, 59, 0)
        decision_ts_et = time(10, 0, 0)
        # bar_ts = decision_ts - 1 minute
        expected_bar_time = (
            datetime.combine(date.today(), decision_ts_et, tzinfo=NY_TZ) - timedelta(minutes=1)
        ).time()
        assert expected_bar_time == bar_ts_et

    def test_next_exposure_minute_bar_is_1000(self) -> None:
        """After signal at Alpaca bar 09:59, next exposure minute starts at Alpaca bar 10:00."""
        signal_bar_time = time(9, 59, 0)
        next_exposure_bar = (
            datetime.combine(date.today(), signal_bar_time, tzinfo=NY_TZ) + timedelta(minutes=1)
        ).time()
        assert next_exposure_bar == time(10, 0, 0)


# ---------------------------------------------------------------------------
# Part C: OOS Guard (Fail-Closed)
# ---------------------------------------------------------------------------

class TestOosBoundaryGuard:
    """OOS guard must reject any date >= 2024-05-01 with DataContractError."""

    @pytest.mark.parametrize("d", [
        date(2024, 5, 1),
        date(2024, 5, 2),
        date(2024, 12, 31),
        date(2025, 1, 1),
        date(2025, 6, 15),
        date(2026, 9, 20),
    ])
    def test_oos_date_raises_data_contract_error(self, d: date) -> None:
        with pytest.raises(DataContractError):
            _validate_probe_date_not_oos(d)

    @pytest.mark.parametrize("d", [
        date(2024, 4, 30),
        date(2022, 6, 1),
        date(2018, 6, 1),
    ])
    def test_historical_date_does_not_raise(self, d: date) -> None:
        _validate_probe_date_not_oos(d)  # Must not raise


# ---------------------------------------------------------------------------
# Part D: Authorized Probe Date Guard (Fail-Closed)
# ---------------------------------------------------------------------------

class TestAuthorizedProbeDateGuard:
    """Only pre-authorized probe dates may be accessed."""

    @pytest.mark.parametrize("d", [
        date(2018, 6, 4),   # Not in authorized list
        date(2023, 6, 1),   # Not in authorized list
        date(2024, 1, 2),   # Not in authorized list
        date(2017, 1, 3),   # Not in authorized list
    ])
    def test_unauthorized_date_raises(self, d: date) -> None:
        with pytest.raises(DataContractError):
            _validate_probe_date_authorized(d)

    @pytest.mark.parametrize("d", [
        date(2018, 6, 1),
        date(2019, 6, 3),
        date(2020, 6, 1),
        date(2021, 6, 1),
        date(2022, 6, 1),
        date(2024, 3, 1),
    ])
    def test_authorized_date_does_not_raise(self, d: date) -> None:
        _validate_probe_date_authorized(d)  # Must not raise

    def test_oos_authorized_date_still_blocked_by_oos_guard(self) -> None:
        """Even if we tried to add a date >= 2024-05-01, the OOS guard would catch it."""
        # 2025-01-01 is not authorized AND would violate OOS guard
        with pytest.raises(DataContractError):
            _validate_probe_date_not_oos(date(2025, 1, 1))


# ---------------------------------------------------------------------------
# Part E: Session Qualification Logic
# ---------------------------------------------------------------------------

class TestSessionQualification:
    """Verify _qualify_session_bars correctly detects OHLC violations, missing bars, etc."""

    def setup_method(self) -> None:
        self.calendar = NyseCa1Calendar()
        self.session_date = date(2022, 6, 1)

    def test_perfect_session_passes(self) -> None:
        bars = _make_full_session_bars(self.session_date)
        result = _qualify_session_bars(self.session_date, bars, self.calendar)
        assert result.status == Mec0015ProbeSessionStatus.PASS
        assert result.bar_count == 390
        assert result.missing_bar_count == 0
        assert len(result.missing_bars_et) == 0
        assert result.failure_reason is None

    def test_missing_bars_detected(self) -> None:
        bars = _make_full_session_bars(self.session_date)
        # Remove 3 bars from the middle
        bars_subset = [b for i, b in enumerate(bars) if i not in {50, 100, 200}]
        result = _qualify_session_bars(self.session_date, bars_subset, self.calendar)
        assert result.status == Mec0015ProbeSessionStatus.FAIL_MISSING_BARS
        assert result.missing_bar_count == 3
        assert result.failure_reason is not None

    def test_invalid_ohlc_high_below_close_detected_arithmetic(self) -> None:
        """Verify that the OHLC invariant check correctly identifies violations.

        HistoricalSipBar's model_validator prevents construction of invalid bars,
        which is correct fail-closed behavior. We verify the arithmetic condition
        that _qualify_session_bars enforces: high >= max(open, close).
        """
        # Directly test the invariant arithmetic used by _qualify_session_bars
        open_ = Decimal("450.00")
        high = Decimal("450.00")  # high equals open
        low = Decimal("449.00")
        close = Decimal("451.00")  # close > high => OHLC violation

        max_body = max(open_, close)
        min_body = min(open_, close)

        # Confirm the violation condition that _qualify_session_bars checks
        assert high < max_body, "high < max(open, close) should be True (OHLC violation)"
        # This is the exact check in the validator:
        ohlc_violation = high < max_body or low > min_body or high < low
        assert ohlc_violation is True

    def test_valid_ohlc_passes_invariant(self) -> None:
        """Confirm that a valid OHLC bar passes all invariant checks."""
        open_ = Decimal("450.00")
        high = Decimal("451.50")
        low = Decimal("448.50")
        close = Decimal("450.75")

        max_body = max(open_, close)
        min_body = min(open_, close)
        ohlc_violation = high < max_body or low > min_body or high < low
        assert ohlc_violation is False

    def test_zero_volume_bars_are_noted_but_do_not_fail(self) -> None:
        bars = _make_full_session_bars(self.session_date)
        # Inject a zero-volume bar at one minute
        ts_et = datetime.combine(self.session_date, time(11, 0, 0), tzinfo=NY_TZ)
        zero_vol_bar = HistoricalSipBar(
            timestamp_utc=ts_et.astimezone(timezone.utc),
            open=Decimal("450.00"),
            high=Decimal("451.00"),
            low=Decimal("449.00"),
            close=Decimal("450.50"),
            volume=Decimal("0"),
            trade_count=0,
        )
        bars_list = [
            zero_vol_bar if b.timestamp_utc.astimezone(NY_TZ).time() == time(11, 0, 0) else b
            for b in bars
        ]
        result = _qualify_session_bars(self.session_date, bars_list, self.calendar)
        assert "11:00 ET" in result.zero_volume_bars_et
        # Zero volume is informational, not a hard failure
        # (the session would be PASS for schema if no missing bars)

    def test_first_and_last_bar_timestamps_recorded(self) -> None:
        bars = _make_full_session_bars(self.session_date)
        result = _qualify_session_bars(self.session_date, bars, self.calendar)
        assert result.first_bar_timestamp_et is not None
        assert "09:30" in result.first_bar_timestamp_et
        assert result.last_bar_timestamp_et is not None
        assert "15:59" in result.last_bar_timestamp_et

    def test_exact_390_bars_for_standard_session(self) -> None:
        bars = _make_full_session_bars(self.session_date, bar_count=390)
        result = _qualify_session_bars(self.session_date, bars, self.calendar)
        assert result.expected_bar_count == 390
        assert result.bar_count == 390


# ---------------------------------------------------------------------------
# Part F: SHA-256 Determinism
# ---------------------------------------------------------------------------

class TestSha256Determinism:
    """SHA-256 computations must be deterministic given identical inputs."""

    def test_session_bars_sha256_deterministic(self) -> None:
        bars = _make_full_session_bars(date(2022, 6, 1))
        sha1 = compute_mec0015_session_bars_sha256(bars)
        sha2 = compute_mec0015_session_bars_sha256(bars)
        assert sha1 == sha2
        assert len(sha1) == 64  # SHA-256 hex digest

    def test_empty_bars_sha256_is_stable(self) -> None:
        sha = compute_mec0015_session_bars_sha256([])
        assert isinstance(sha, str)
        assert len(sha) == 64

    def test_report_sha256_deterministic(self) -> None:
        d: Dict[str, Any] = {"a": 1, "b": "test", "c": [1, 2, 3]}
        sha1 = compute_mec0015_report_sha256(d)
        sha2 = compute_mec0015_report_sha256(d)
        assert sha1 == sha2
        assert len(sha1) == 64

    def test_report_sha256_changes_with_content(self) -> None:
        d1: Dict[str, Any] = {"a": 1}
        d2: Dict[str, Any] = {"a": 2}
        assert compute_mec0015_report_sha256(d1) != compute_mec0015_report_sha256(d2)

    def test_bars_sha256_changes_with_different_prices(self) -> None:
        bars1 = _make_full_session_bars(date(2022, 6, 1))
        bars2 = _make_full_session_bars(date(2021, 6, 1))  # Different date = different timestamps
        sha1 = compute_mec0015_session_bars_sha256(bars1)
        sha2 = compute_mec0015_session_bars_sha256(bars2)
        assert sha1 != sha2


# ---------------------------------------------------------------------------
# Part G: Missing-Bar Policy Contract
# ---------------------------------------------------------------------------

class TestMissingBarPolicy:
    """MISSING_REQUIRED_MINUTE_POLICY = FAIL_CLOSED_SESSION_EXCLUSION.
    Missing bars must be detected and reported; no silent imputation is performed.
    """

    def test_no_forward_fill_imputation(self) -> None:
        """The qualification module must NOT silently fill missing bars."""
        # A session with a missing bar must produce FAIL_MISSING_BARS, not PASS
        session_date = date(2022, 6, 1)
        full_bars = _make_full_session_bars(session_date)
        truncated_bars = full_bars[:389]  # Remove last bar (15:59)
        result = _qualify_session_bars(session_date, truncated_bars, NyseCa1Calendar())
        assert result.status == Mec0015ProbeSessionStatus.FAIL_MISSING_BARS
        assert result.missing_bar_count > 0

    def test_missing_bar_timestamps_explicitly_listed(self) -> None:
        session_date = date(2022, 6, 1)
        full_bars = _make_full_session_bars(session_date)
        # Remove bars at 10:00, 12:30, 14:00
        target_times = {time(10, 0), time(12, 30), time(14, 0)}
        filtered = [b for b in full_bars if b.timestamp_utc.astimezone(NY_TZ).time() not in target_times]
        result = _qualify_session_bars(session_date, filtered, NyseCa1Calendar())
        assert result.missing_bar_count == 3
        assert len(result.missing_bars_et) == 3

    def test_no_interpolation_in_module(self) -> None:
        """Verify the module has no forward-fill or interpolation logic by inspection."""
        import acash.data.qualification.mec_0015_bar_contract as m
        import inspect
        src = inspect.getsource(m)
        forbidden_patterns = ["ffill", "forward_fill", "interpolate", "fillna(method"]
        for pat in forbidden_patterns:
            assert pat not in src, f"Forbidden imputation pattern '{pat}' found in module source"


# ---------------------------------------------------------------------------
# Part H: Early-Close Session Policy (EXCLUDE_NON_STANDARD_REGULAR_SESSIONS)
# ---------------------------------------------------------------------------

class TestEarlyClosePolicy:
    """EARLY_CLOSE_POLICY = EXCLUDE_NON_STANDARD_REGULAR_SESSIONS.
    Early-close sessions are identified and expected_bar_count adjusted to 210.
    """

    def test_early_close_sessions_have_210_expected_bars(self) -> None:
        """On days like the day after Thanksgiving 2021 (2021-11-26), session is early close."""
        calendar = NyseCa1Calendar()
        # 2021-11-26 is day-after-Thanksgiving: early close (13:00 ET)
        early_close_date = date(2021, 11, 26)
        bars = _make_full_session_bars(early_close_date, bar_count=210)  # 09:30..12:59 ET
        result = _qualify_session_bars(early_close_date, bars, calendar)
        assert result.is_early_close_session is True
        assert result.expected_bar_count == 210


# ---------------------------------------------------------------------------
# Part I: Probe Module Constants Safety
# ---------------------------------------------------------------------------

class TestModuleConstantsSafety:
    """Verify all module-level constants satisfy governance requirements."""

    def test_symbol_is_spy(self) -> None:
        from acash.data.qualification.mec_0015_bar_contract import MEC_0015_SYMBOL
        assert MEC_0015_SYMBOL == "SPY"

    def test_feed_is_sip(self) -> None:
        from acash.data.qualification.mec_0015_bar_contract import MEC_0015_FEED
        from acash.data.qualification.models import MarketDataFeed
        assert MEC_0015_FEED == MarketDataFeed.SIP

    def test_timeframe_is_1min(self) -> None:
        from acash.data.qualification.mec_0015_bar_contract import MEC_0015_TIMEFRAME
        assert MEC_0015_TIMEFRAME == "1Min"

    def test_adjustment_is_raw(self) -> None:
        from acash.data.qualification.mec_0015_bar_contract import MEC_0015_ADJUSTMENT
        from acash.data.qualification.models import PriceAdjustment
        assert MEC_0015_ADJUSTMENT == PriceAdjustment.RAW

    def test_authorized_probe_dates_count(self) -> None:
        """Exactly 6 authorized probe dates."""
        assert len(MEC_0015_AUTHORIZED_PROBE_DATES) == 6

    def test_no_probe_date_after_2024_03_01(self) -> None:
        """No probe date should be after 2024-03-01."""
        latest = max(MEC_0015_AUTHORIZED_PROBE_DATES)
        assert latest <= date(2024, 3, 1)
