"""Effective-date extension of the regulatory fee schedules through 2025-12-31."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.execution.regulatory_fees import (
    FINRA_TAF_SCHEDULE,
    MEC_0015_REGULATORY_SCHEDULE_END,
    REGULATORY_SCHEDULE_END,
    REGULATORY_SCHEDULE_START,
    SEC_SECTION_31_SCHEDULE,
    compute_finra_taf,
    compute_sec31_fee,
)

PRINCIPAL = Decimal("100000.00")


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


@pytest.mark.parametrize(
    "schedule",
    [SEC_SECTION_31_SCHEDULE, FINRA_TAF_SCHEDULE],
    ids=["sec31", "finra_taf"],
)
def test_every_supported_day_matches_exactly_one_segment(schedule: object) -> None:
    segments = list(schedule)  # type: ignore[call-overload]
    for day in _days(REGULATORY_SCHEDULE_START, REGULATORY_SCHEDULE_END):
        matches = [s for s in segments if s.effective_start <= day <= s.effective_end]
        assert len(matches) == 1, day


def test_mec_0015_replication_window_constant_is_unchanged() -> None:
    assert MEC_0015_REGULATORY_SCHEDULE_END == date(2024, 4, 30)
    assert REGULATORY_SCHEDULE_END == date(2025, 12, 31)


@pytest.mark.parametrize(
    ("trade_date", "expected"),
    [
        (date(2024, 4, 30), Decimal("0.80")),
        (date(2024, 5, 1), Decimal("0.80")),
        (date(2024, 5, 21), Decimal("0.80")),
        (date(2024, 5, 22), Decimal("2.78")),
        (date(2025, 5, 13), Decimal("2.78")),
        (date(2025, 5, 14), Decimal("0.00")),
        (date(2025, 12, 31), Decimal("0.00")),
    ],
)
def test_sec31_transition_boundaries(trade_date: date, expected: Decimal) -> None:
    assert compute_sec31_fee(trade_date, PRINCIPAL) == expected


def test_sec31_rounding_and_zero_rate() -> None:
    assert compute_sec31_fee(date(2024, 5, 22), Decimal("1000.00")) == Decimal("0.03")
    assert compute_sec31_fee(date(2025, 6, 2), Decimal("9999999.99")) == Decimal("0.00")
    assert compute_sec31_fee(date(2024, 5, 22), PRINCIPAL, is_sell=False) == Decimal("0.00")


@pytest.mark.parametrize(
    ("shares", "expected"),
    [
        (0, Decimal("0.00")),
        (1, Decimal("0.01")),
        (Decimal("0.5"), Decimal("0.01")),
        (100, Decimal("0.02")),
        (50_000, Decimal("8.30")),
        (60_000, Decimal("8.30")),
    ],
)
def test_finra_taf_2025_rate_cap_and_rounding(shares: int | Decimal, expected: Decimal) -> None:
    assert compute_finra_taf(date(2025, 7, 1), shares) == expected


def test_finra_taf_2024_2025_parity_and_buy_exempt() -> None:
    for shares in (1, 100, 12_345, 60_000):
        assert compute_finra_taf(date(2024, 12, 31), shares) == compute_finra_taf(
            date(2025, 1, 1), shares
        )
    assert compute_finra_taf(date(2025, 1, 1), 100, is_sell=False) == Decimal("0.00")


def test_dates_beyond_coverage_fail_closed() -> None:
    with pytest.raises(DataContractError, match="DATE_OUTSIDE_SCHEDULE"):
        compute_sec31_fee(date(2026, 1, 1), PRINCIPAL)
    with pytest.raises(DataContractError, match="DATE_OUTSIDE_SCHEDULE"):
        compute_finra_taf(date(2026, 1, 1), 100)
