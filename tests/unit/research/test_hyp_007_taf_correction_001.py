"""HYP_007 M2 TAF correction 001: frozen defect preserved, canonical 2025 parity, bound."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from acash.execution.regulatory_fees import compute_finra_taf, get_finra_taf_segment
from acash.research.step_r4_hyp_007 import M2_FINRA_TAF_SCHEDULE, compute_m2_finra_taf

PER_TRADE_OVERCHARGE_BOUND = Decimal("1.50")
SHARE_GRID = (1, 99, 100, 101, 1000, 6024, 6025, 10_000, 50_000, 50_205, 50_206, 60_000, 1_000_000)
DAYS_2025 = (date(2025, 1, 1), date(2025, 1, 2), date(2025, 7, 1), date(2025, 12, 31))


def test_frozen_m2_schedule_is_preserved_unmodified() -> None:
    row = M2_FINRA_TAF_SCHEDULE[1]
    assert (row.effective_start, row.rate_per_share, row.max_fee_per_trade) == (
        date(2025, 1, 1), Decimal("0.000195"), Decimal("9.79"),
    )


def test_canonical_engine_2025_matches_sec_release_34_101696() -> None:
    for day in DAYS_2025:
        segment = get_finra_taf_segment(day)
        assert (segment.rate_per_share, segment.max_fee_per_trade) == (Decimal("0.000166"), Decimal("8.30"))
    assert compute_finra_taf(date(2024, 12, 31), 50_000) == compute_finra_taf(date(2025, 1, 2), 50_000)


def test_m2_overcharge_in_2025_is_nonnegative_and_bounded_per_sell() -> None:
    for day in DAYS_2025:
        for shares in SHARE_GRID:
            delta = compute_m2_finra_taf(shares, day) - compute_finra_taf(day, shares)
            assert Decimal("0") <= delta <= PER_TRADE_OVERCHARGE_BOUND, (day, shares, delta)
    assert compute_m2_finra_taf(60_000, date(2025, 7, 1)) - compute_finra_taf(date(2025, 7, 1), 60_000) == Decimal("1.49")
