"""Unit tests for MEC-0015 regulatory fee models (SEC Section 31 & FINRA TAF)."""

from datetime import date
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.execution.regulatory_fees import (
    SEC_SECTION_31_SCHEDULE,
    FINRA_TAF_SCHEDULE,
    compute_sec31_fee,
    compute_finra_taf,
    get_sec31_segment,
    get_finra_taf_segment,
)


def test_sec31_schedule_completeness_and_continuity() -> None:
    """Verify all 20 segments are contiguous from 2007-05-01 through 2024-04-30 without gaps."""
    assert len(SEC_SECTION_31_SCHEDULE) == 20
    assert SEC_SECTION_31_SCHEDULE[0].effective_start <= date(2007, 5, 1)
    assert SEC_SECTION_31_SCHEDULE[-1].effective_end >= date(2024, 4, 30)

    for i in range(len(SEC_SECTION_31_SCHEDULE) - 1):
        seg = SEC_SECTION_31_SCHEDULE[i]
        next_seg = SEC_SECTION_31_SCHEDULE[i + 1]
        assert seg.effective_end < next_seg.effective_start
        assert (next_seg.effective_start - seg.effective_end).days == 1, (
            f"Gap between segment {i} ({seg.effective_end}) and {i+1} ({next_seg.effective_start})"
        )


def test_finra_taf_schedule_completeness_and_continuity() -> None:
    """Verify all 7 segments are contiguous from 2007-05-01 through 2024-04-30 without gaps."""
    assert len(FINRA_TAF_SCHEDULE) == 7
    assert FINRA_TAF_SCHEDULE[0].effective_start <= date(2007, 5, 1)
    assert FINRA_TAF_SCHEDULE[-1].effective_end >= date(2024, 4, 30)

    for i in range(len(FINRA_TAF_SCHEDULE) - 1):
        seg = FINRA_TAF_SCHEDULE[i]
        next_seg = FINRA_TAF_SCHEDULE[i + 1]
        assert seg.effective_end < next_seg.effective_start
        assert (next_seg.effective_start - seg.effective_end).days == 1, (
            f"Gap between segment {i} ({seg.effective_end}) and {i+1} ({next_seg.effective_start})"
        )


def test_sec31_boundary_dates() -> None:
    """Test lookup across every SEC segment boundary start and end date."""
    for seg in SEC_SECTION_31_SCHEDULE:
        if seg.effective_start >= date(2007, 5, 1):
            found = get_sec31_segment(seg.effective_start)
            assert found == seg
        if seg.effective_end <= date(2024, 4, 30):
            found = get_sec31_segment(seg.effective_end)
            assert found == seg


def test_finra_taf_boundary_dates() -> None:
    """Test lookup across every FINRA segment boundary start and end date."""
    for seg in FINRA_TAF_SCHEDULE:
        if seg.effective_start >= date(2007, 5, 1):
            found = get_finra_taf_segment(seg.effective_start)
            assert found == seg
        if seg.effective_end <= date(2024, 4, 30):
            found = get_finra_taf_segment(seg.effective_end)
            assert found == seg


def test_finra_taf_staged_transition_boundaries_2021_2024() -> None:
    """Explicitly verify SR-FINRA-2020-032 phased implementation boundaries across 2021-2024."""
    # 2021-12-31 (Segment 4): rate 0.000119, cap 5.95
    seg_2021_end = get_finra_taf_segment(date(2021, 12, 31))
    assert seg_2021_end.rate_per_share == Decimal("0.000119")
    assert seg_2021_end.max_fee_per_trade == Decimal("5.95")

    # 2022-01-01 (Segment 5, Phase 1 start): rate 0.000130, cap 6.49
    seg_2022_start = get_finra_taf_segment(date(2022, 1, 1))
    assert seg_2022_start.rate_per_share == Decimal("0.000130")
    assert seg_2022_start.max_fee_per_trade == Decimal("6.49")

    # 2022-12-31 (Segment 5, Phase 1 end): rate 0.000130, cap 6.49
    seg_2022_end = get_finra_taf_segment(date(2022, 12, 31))
    assert seg_2022_end.rate_per_share == Decimal("0.000130")
    assert seg_2022_end.max_fee_per_trade == Decimal("6.49")

    # 2023-01-01 (Segment 6, Phase 2 start): rate 0.000145, cap 7.27
    seg_2023_start = get_finra_taf_segment(date(2023, 1, 1))
    assert seg_2023_start.rate_per_share == Decimal("0.000145")
    assert seg_2023_start.max_fee_per_trade == Decimal("7.27")

    # 2023-12-31 (Segment 6, Phase 2 end): rate 0.000145, cap 7.27
    seg_2023_end = get_finra_taf_segment(date(2023, 12, 31))
    assert seg_2023_end.rate_per_share == Decimal("0.000145")
    assert seg_2023_end.max_fee_per_trade == Decimal("7.27")

    # 2024-01-01 (Segment 7, Phase 3 Full Implementation start): rate 0.000166, cap 8.30
    seg_2024_start = get_finra_taf_segment(date(2024, 1, 1))
    assert seg_2024_start.rate_per_share == Decimal("0.000166")
    assert seg_2024_start.max_fee_per_trade == Decimal("8.30")

    # 2024-04-30 (M1 end date, within Segment 7): rate 0.000166, cap 8.30
    seg_2024_m1_end = get_finra_taf_segment(date(2024, 4, 30))
    assert seg_2024_m1_end.rate_per_share == Decimal("0.000166")
    assert seg_2024_m1_end.max_fee_per_trade == Decimal("8.30")


def test_finra_taf_cap_behavior_across_all_tiers() -> None:
    """Verify rate application and per-trade fee cap behavior across tiers."""
    # Segment 1 (2004-2011): rate 0.000075, cap 3.75
    d1 = date(2008, 6, 1)
    assert compute_finra_taf(d1, 100) == Decimal("0.01")  # 100 * 0.000075 = 0.0075 -> ceil $0.01
    assert compute_finra_taf(d1, 50000) == Decimal("3.75")  # 50,000 * 0.000075 = 3.75 (exact cap)
    assert compute_finra_taf(d1, 100000) == Decimal("3.75")  # capped

    # Segment 4 (2012-2021): rate 0.000119, cap 5.95
    d4 = date(2020, 6, 1)
    assert compute_finra_taf(d4, 100) == Decimal("0.02")  # 100 * 0.000119 = 0.0119 -> ceil $0.02
    assert compute_finra_taf(d4, 50000) == Decimal("5.95")  # exact cap
    assert compute_finra_taf(d4, 100000) == Decimal("5.95")  # capped

    # Segment 5 (2022): rate 0.000130, cap 6.49
    d5 = date(2022, 6, 1)
    assert compute_finra_taf(d5, 100) == Decimal("0.02")  # 100 * 0.000130 = 0.0130 -> ceil $0.02
    assert compute_finra_taf(d5, 49923) == Decimal("6.49")  # 49923 * 0.000130 = 6.48999 -> ceil $6.49
    assert compute_finra_taf(d5, 60000) == Decimal("6.49")  # 60,000 * 0.000130 = 7.80 -> capped at 6.49

    # Segment 6 (2023): rate 0.000145, cap 7.27
    d6 = date(2023, 6, 1)
    assert compute_finra_taf(d6, 100) == Decimal("0.02")  # 100 * 0.000145 = 0.0145 -> ceil $0.02
    assert compute_finra_taf(d6, 50137) == Decimal("7.27")  # 50137 * 0.000145 = 7.269865 -> ceil $7.27
    assert compute_finra_taf(d6, 60000) == Decimal("7.27")  # 60,000 * 0.000145 = 8.70 -> capped at 7.27

    # Segment 7 (2024): rate 0.000166, cap 8.30
    d7 = date(2024, 3, 1)
    assert compute_finra_taf(d7, 1) == Decimal("0.01")  # 1 * 0.000166 = 0.000166 -> ceil $0.01
    assert compute_finra_taf(d7, 100) == Decimal("0.02")  # 100 * 0.000166 = 0.0166 -> ceil $0.02
    assert compute_finra_taf(d7, 50000) == Decimal("8.30")  # 50,000 * 0.000166 = 8.30 (exact cap)
    assert compute_finra_taf(d7, 100000) == Decimal("8.30")  # 100,000 * 0.000166 = 16.60 -> capped at 8.30


def test_buy_side_regulatory_fees_are_strictly_zero() -> None:
    """Buy side orders incur zero SEC and zero FINRA TAF fee."""
    d = date(2020, 6, 1)
    assert compute_sec31_fee(d, Decimal("100000.00"), is_sell=False) == Decimal("0.00")
    assert compute_finra_taf(d, Decimal("1000"), is_sell=False) == Decimal("0.00")
    assert compute_finra_taf(d, 500, is_sell=False) == Decimal("0.00")


def test_sec31_calculation_and_rounding() -> None:
    """Verify Section 31 calculations and conservative ROUND_CEILING_TO_CENT operationalization.

    Proves:
    A. exact-cent raw fee remains exact.
    B. fractional fee below one cent (0.00008 -> 0.01).
    C. fractional fee (0.011 -> 0.02).
    D. value where HALF_UP differs from CEILING (0.014 -> 0.02, NOT 0.01).
    E. zero principal -> 0.00.
    F. buy side -> 0.00.
    """
    # Segment 20 (2023-02-27 to 2024-05-21): $8.00 per $1,000,000 (rate 0.000008)
    d = date(2024, 3, 1)

    # A. Exact-cent raw fee remains exact
    # $100,000 * 0.000008 = $0.800000 -> $0.80
    assert compute_sec31_fee(d, Decimal("100000.00")) == Decimal("0.80")
    # $125,000 * 0.000008 = $1.000000 -> $1.00
    assert compute_sec31_fee(d, Decimal("125000.00")) == Decimal("1.00")

    # B. Fractional fee below one cent
    # $10.00 * 0.000008 = $0.000080 -> ceil to cent -> $0.01
    assert compute_sec31_fee(d, Decimal("10.00")) == Decimal("0.01")
    # $1.00 * 0.000008 = $0.000008 -> ceil to cent -> $0.01
    assert compute_sec31_fee(d, Decimal("1.00")) == Decimal("0.01")

    # C. Fractional fee
    # $1,375.00 * 0.000008 = $0.011000 -> ceil to cent -> $0.02
    assert compute_sec31_fee(d, Decimal("1375.00")) == Decimal("0.02")

    # D. Value where HALF_UP would differ from CEILING
    # $1,750.00 * 0.000008 = $0.014000
    # Under ROUND_HALF_UP: 0.014 -> 0.01
    # Under ROUND_CEILING: 0.014 -> 0.02 (conservative broker pass-through)
    raw_014 = Decimal("1750.00") * Decimal("0.000008")
    assert raw_014 == Decimal("0.014000")
    assert compute_sec31_fee(d, Decimal("1750.00")) == Decimal("0.02")

    # E. Zero principal
    assert compute_sec31_fee(d, Decimal("0.00")) == Decimal("0.00")

    # F. Buy side
    assert compute_sec31_fee(d, Decimal("1750.00"), is_sell=False) == Decimal("0.00")
    assert compute_sec31_fee(d, Decimal("100000.00"), is_sell=False) == Decimal("0.00")


def test_fail_closed_outside_scope_and_malformed() -> None:
    """Verify strict fail-closed contract outside [2007-05-01, 2024-04-30] and invalid inputs."""
    too_early = date(2007, 4, 30)
    too_late = date(2024, 5, 1)

    with pytest.raises(DataContractError, match="DATE_OUTSIDE_SCHEDULE"):
        compute_sec31_fee(too_early, Decimal("1000.00"))

    with pytest.raises(DataContractError, match="DATE_OUTSIDE_SCHEDULE"):
        compute_sec31_fee(too_late, Decimal("1000.00"))

    with pytest.raises(DataContractError, match="DATE_OUTSIDE_SCHEDULE"):
        compute_finra_taf(too_early, 100)

    with pytest.raises(DataContractError, match="DATE_OUTSIDE_SCHEDULE"):
        compute_finra_taf(too_late, 100)

    # Negative inputs
    with pytest.raises(DataContractError, match="NEGATIVE_PRINCIPAL"):
        compute_sec31_fee(date(2020, 1, 15), Decimal("-100.00"))

    with pytest.raises(DataContractError, match="NEGATIVE_SHARES"):
        compute_finra_taf(date(2020, 1, 15), -10)
