"""Deterministic Unit Tests for CA-1 NYSE Trading Calendar Engine.

Covers:
1. Regular session: 2026-09-15 -> 390 minutes [09:30, 16:00) ET.
2. Holiday: 2026-09-07 (Labor Day) -> non-trading session.
3. Early Close: Exact CA-1 pinned dates (e.g. 2024-07-03, 2026-11-27, 2026-12-24) -> 13:00 ET close, 210 minutes.
4. DST Transitions: Standard Time (EST = UTC-5) vs Daylight Time (EDT = UTC-4) ZoneInfo conversion.
5. Minute Boundaries: first bar = 09:30 ET, regular last bar = 15:59 ET, early close last bar = 12:59 ET.
6. Out of Range: Year < 2013 and Year > 2026 fail closed with CalendarAuthorityOutOfRangeError.
7. Integration with HistoricalBarValidator: completeness checks authorized under CA-1.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest

from acash.data.calendar.nyse_ca1 import (
    CalendarAuthorityOutOfRangeError,
    NonTradingDayError,
    NyseCa1Calendar,
    SessionType,
)
from acash.data.qualification.models import (
    HistoricalSipBar,
    QualityRuleCode,
    QualitySeverity,
)
from acash.data.qualification.validator import HistoricalBarValidator

NY_TZ = ZoneInfo("America/New_York")


@pytest.fixture
def calendar() -> NyseCa1Calendar:
    return NyseCa1Calendar()


# =============================================================================
# 1. Regular Session Tests
# =============================================================================

def test_regular_session_2026_09_15(calendar: NyseCa1Calendar) -> None:
    """Verify 2026-09-15 is an official regular session with 390 expected minutes."""
    d = date(2026, 9, 15)
    assert calendar.is_trading_session(d) is True
    assert calendar.is_holiday(d) is False
    assert calendar.is_early_close(d) is False

    session = calendar.get_session(d)
    assert session.session_date == d
    assert session.timezone_name == "America/New_York"
    assert session.session_type == SessionType.REGULAR
    assert session.open_local == time(9, 30, 0)
    assert session.close_local == time(16, 0, 0)
    assert session.expected_minute_count == 390

    # 2026-09-15 is EDT (UTC-4)
    # 09:30:00 EDT == 13:30:00 UTC
    # 16:00:00 EDT == 20:00:00 UTC
    assert session.open_utc == datetime(2026, 9, 15, 13, 30, 0, tzinfo=timezone.utc)
    assert session.close_utc == datetime(2026, 9, 15, 20, 0, 0, tzinfo=timezone.utc)

    # Minute grid
    grid = session.expected_minute_grid()
    assert len(grid) == 390
    assert grid[0] == datetime(2026, 9, 15, 13, 30, 0, tzinfo=timezone.utc)
    assert grid[-1] == datetime(2026, 9, 15, 19, 59, 0, tzinfo=timezone.utc)


# =============================================================================
# 2. Holiday Tests
# =============================================================================

def test_holiday_2026_09_07_labor_day(calendar: NyseCa1Calendar) -> None:
    """Verify 2026-09-07 (Labor Day) is recognized as a market holiday with no session."""
    d = date(2026, 9, 7)
    assert calendar.is_trading_session(d) is False
    assert calendar.is_holiday(d) is True
    assert calendar.get_holiday_reason(d) == "Labor Day"

    # get_session must fail closed
    with pytest.raises(NonTradingDayError, match="official NYSE holiday: Labor Day"):
        calendar.get_session(d)

    # get_session_or_none returns None
    assert calendar.get_session_or_none(d) is None
    assert calendar.get_verified_schedule(d) is None


def test_special_closure_2018_12_05_bush_mourning(calendar: NyseCa1Calendar) -> None:
    """Verify 2018-12-05 National Day of Mourning for President Bush is recorded."""
    d = date(2018, 12, 5)
    assert calendar.is_trading_session(d) is False
    assert calendar.is_holiday(d) is True
    assert "George H.W. Bush" in str(calendar.get_holiday_reason(d))


def test_special_closure_2025_01_09_carter_mourning(calendar: NyseCa1Calendar) -> None:
    """Verify 2025-01-09 National Day of Mourning for President Carter is recorded.

    The NYSE was fully closed on 2025-01-09 (unscheduled full market closure). This
    regression guards against the M2 census counting the closure day as a regular session.
    """
    d = date(2025, 1, 9)
    assert calendar.is_trading_session(d) is False
    assert calendar.is_holiday(d) is True
    assert "Jimmy Carter" in str(calendar.get_holiday_reason(d))

    # get_session must fail closed
    with pytest.raises(NonTradingDayError, match="official NYSE holiday"):
        calendar.get_session(d)

    # get_session_or_none returns None
    assert calendar.get_session_or_none(d) is None
    assert calendar.get_verified_schedule(d) is None


# =============================================================================
# 3. Early Close Tests
# =============================================================================

@pytest.mark.parametrize(
    "early_date,expected_year,description",
    [
        (date(2024, 7, 3), 2024, "Day before Independence Day 2024"),
        (date(2026, 11, 27), 2026, "Day after Thanksgiving 2026"),
        (date(2026, 12, 24), 2026, "Christmas Eve 2026"),
        (date(2023, 7, 3), 2023, "Day before Independence Day 2023"),
    ],
)
def test_early_close_dates(
    calendar: NyseCa1Calendar,
    early_date: date,
    expected_year: int,
    description: str,
) -> None:
    """Verify exact pinned CA-1 early close dates close at 13:00 ET with 210 minutes."""
    assert calendar.is_trading_session(early_date) is True
    assert calendar.is_early_close(early_date) is True
    assert calendar.is_holiday(early_date) is False

    session = calendar.get_session(early_date)
    assert session.session_type == SessionType.EARLY_CLOSE
    assert session.open_local == time(9, 30, 0)
    assert session.close_local == time(13, 0, 0)
    assert session.expected_minute_count == 210

    grid = session.expected_minute_grid()
    assert len(grid) == 210
    # First bar 09:30 ET
    ny_first = grid[0].astimezone(NY_TZ)
    assert ny_first.time() == time(9, 30, 0)
    # Last bar 12:59 ET
    ny_last = grid[-1].astimezone(NY_TZ)
    assert ny_last.time() == time(12, 59, 0)


# =============================================================================
# 4. DST Transition Tests (ZoneInfo-Driven)
# =============================================================================

def test_dst_standard_vs_daylight_utc_conversion(calendar: NyseCa1Calendar) -> None:
    """Verify standard time (EST = UTC-5) vs daylight time (EDT = UTC-4) conversions."""
    # Standard time: 2026-01-15 (Thursday)
    std_date = date(2026, 1, 15)
    std_session = calendar.get_session(std_date)
    # 09:30 EST == 14:30 UTC
    # 16:00 EST == 21:00 UTC
    assert std_session.open_utc == datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
    assert std_session.close_utc == datetime(2026, 1, 15, 21, 0, 0, tzinfo=timezone.utc)

    # Daylight time: 2026-06-15 (Monday)
    dst_date = date(2026, 6, 15)
    dst_session = calendar.get_session(dst_date)
    # 09:30 EDT == 13:30 UTC
    # 16:00 EDT == 20:00 UTC
    assert dst_session.open_utc == datetime(2026, 6, 15, 13, 30, 0, tzinfo=timezone.utc)
    assert dst_session.close_utc == datetime(2026, 6, 15, 20, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# 5. Boundary Minute Alignment Tests
# =============================================================================

def test_boundary_minute_grid_alignment(calendar: NyseCa1Calendar) -> None:
    """Verify first minute = 09:30 ET, regular last = 15:59 ET, early-close last = 12:59 ET."""
    reg_session = calendar.get_session(date(2026, 9, 15))
    reg_grid = reg_session.expected_minute_grid()
    assert reg_grid[0].astimezone(NY_TZ).strftime("%H:%M:%S") == "09:30:00"
    assert reg_grid[-1].astimezone(NY_TZ).strftime("%H:%M:%S") == "15:59:00"

    early_session = calendar.get_session(date(2026, 11, 27))
    early_grid = early_session.expected_minute_grid()
    assert early_grid[0].astimezone(NY_TZ).strftime("%H:%M:%S") == "09:30:00"
    assert early_grid[-1].astimezone(NY_TZ).strftime("%H:%M:%S") == "12:59:00"


# =============================================================================
# 6. Out-of-Range and Non-Trading Day Strict Fail-Closed Tests
# =============================================================================

def test_out_of_range_years_fail_closed(calendar: NyseCa1Calendar) -> None:
    """Verify years outside ratified coverage [2013, 2026] raise CalendarAuthorityOutOfRangeError."""
    # Historical pre-coverage: 2012
    with pytest.raises(CalendarAuthorityOutOfRangeError, match="outside ratified CA-1"):
        calendar.is_trading_session(date(2012, 12, 31))

    with pytest.raises(CalendarAuthorityOutOfRangeError, match="outside ratified CA-1"):
        calendar.get_session(date(2012, 12, 31))

    # Future post-coverage: 2027
    with pytest.raises(CalendarAuthorityOutOfRangeError, match="outside ratified CA-1"):
        calendar.is_trading_session(date(2027, 1, 4))

    with pytest.raises(CalendarAuthorityOutOfRangeError, match="outside ratified CA-1"):
        calendar.get_session(date(2027, 1, 4))


def test_weekend_days_fail_closed(calendar: NyseCa1Calendar) -> None:
    """Verify Saturday and Sunday return False for trading session and fail closed on get_session."""
    saturday = date(2026, 9, 12)
    sunday = date(2026, 9, 13)

    assert calendar.is_trading_session(saturday) is False
    assert calendar.is_trading_session(sunday) is False

    with pytest.raises(NonTradingDayError, match="weekend"):
        calendar.get_session(saturday)

    with pytest.raises(NonTradingDayError, match="weekend"):
        calendar.get_session(sunday)


# =============================================================================
# 7. CA-1 Artifact Metadata Authority Tests
# =============================================================================

def test_authority_metadata_provenance(calendar: NyseCa1Calendar) -> None:
    """Verify all 14 coverage years (2013-2026) have complete pinned artifact provenance."""
    for yr in range(2013, 2027):
        meta = calendar.authority_metadata(date(yr, 6, 1))
        assert meta.source_year == yr
        assert len(meta.sha256) == 64
        assert meta.authority == "NYSE Official (CA-1)"
        assert len(meta.artifact_identity) > 0
        assert meta.official_url.startswith("http")


# =============================================================================
# 8. Integration with HistoricalBarValidator Tests
# =============================================================================

def test_validator_with_ca1_calendar_completeness_pass() -> None:
    """A CA-1 covered date (2026-09-15) with 390 bars passes completeness without unverified warning."""
    cal = NyseCa1Calendar()
    validator = HistoricalBarValidator(calendar=cal)
    session = cal.get_session(date(2026, 9, 15))
    grid = session.expected_minute_grid()

    # Generate 390 valid bars
    bars = [
        HistoricalSipBar(
            timestamp_utc=ts,
            open=Decimal("560.00"),
            high=Decimal("561.00"),
            low=Decimal("559.50"),
            close=Decimal("560.50"),
            volume=Decimal("1000"),
        )
        for ts in grid
    ]

    findings = validator.validate_bars(bars)
    # Zero blocking errors
    assert validator.has_blocking_errors(findings) is False
    # CALENDAR_AUTHORITY_UNVERIFIED must NOT be emitted because CA-1 authorized the schedule
    assert not any(f.rule == QualityRuleCode.CALENDAR_AUTHORITY_UNVERIFIED for f in findings)
    # Zero missing bars
    assert not any(f.rule == QualityRuleCode.MISSING_BAR for f in findings)


def test_validator_with_ca1_calendar_detects_missing_bars() -> None:
    """A CA-1 covered date with missing minutes detects exact MISSING_BAR count."""
    cal = NyseCa1Calendar()
    validator = HistoricalBarValidator(calendar=cal)
    session = cal.get_session(date(2026, 9, 15))
    grid = session.expected_minute_grid()

    # Drop 5 bars (keep 385 out of 390)
    bars = [
        HistoricalSipBar(
            timestamp_utc=ts,
            open=Decimal("560.00"),
            high=Decimal("561.00"),
            low=Decimal("559.50"),
            close=Decimal("560.50"),
            volume=Decimal("1000"),
        )
        for i, ts in enumerate(grid)
        if i not in (10, 11, 12, 50, 100)
    ]

    findings = validator.validate_bars(bars)
    missing_findings = [f for f in findings if f.rule == QualityRuleCode.MISSING_BAR]
    assert len(missing_findings) == 1
    assert missing_findings[0].severity == QualitySeverity.WARNING
    assert missing_findings[0].details["missing_count"] == 5
    assert missing_findings[0].details["expected_count"] == 390
    assert missing_findings[0].details["observed_count"] == 385


def test_validator_with_ca1_calendar_early_close_completeness() -> None:
    """A CA-1 covered early close date (2026-11-27) with 210 bars passes completeness."""
    cal = NyseCa1Calendar()
    validator = HistoricalBarValidator(calendar=cal)
    session = cal.get_session(date(2026, 11, 27))
    grid = session.expected_minute_grid()
    assert len(grid) == 210

    bars = [
        HistoricalSipBar(
            timestamp_utc=ts,
            open=Decimal("570.00"),
            high=Decimal("571.00"),
            low=Decimal("569.50"),
            close=Decimal("570.50"),
            volume=Decimal("500"),
        )
        for ts in grid
    ]

    findings = validator.validate_bars(bars)
    assert validator.has_blocking_errors(findings) is False
    assert not any(f.rule == QualityRuleCode.CALENDAR_AUTHORITY_UNVERIFIED for f in findings)
    assert not any(f.rule == QualityRuleCode.MISSING_BAR for f in findings)


def test_validator_out_of_range_retains_authority_unverified() -> None:
    """An out-of-range date (2012-10-01) retains fail-closed CALENDAR_AUTHORITY_UNVERIFIED."""
    cal = NyseCa1Calendar()
    validator = HistoricalBarValidator(calendar=cal)

    bars = [
        HistoricalSipBar(
            timestamp_utc=datetime(2012, 10, 1, 13, 30 + i, 0, tzinfo=timezone.utc),
            open=Decimal("140.00"),
            high=Decimal("141.00"),
            low=Decimal("139.50"),
            close=Decimal("140.50"),
            volume=Decimal("100"),
        )
        for i in range(5)
    ]

    findings = validator.validate_bars(bars)
    cal_unverified = [f for f in findings if f.rule == QualityRuleCode.CALENDAR_AUTHORITY_UNVERIFIED]
    assert len(cal_unverified) == 1
    assert cal_unverified[0].severity == QualitySeverity.INFO
    # No false missing bars
    assert not any(f.rule == QualityRuleCode.MISSING_BAR for f in findings)
