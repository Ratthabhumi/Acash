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
    """Verify all 4 segments are contiguous from 2007-05-01 through 2024-04-30 without gaps."""
    assert len(FINRA_TAF_SCHEDULE) == 4
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
        # Check start date (if within authorized scope)
        if seg.effective_start >= date(2007, 5, 1):
            found = get_sec31_segment(seg.effective_start)
            assert found == seg
        # Check end date (if within authorized scope)
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


def test_buy_side_regulatory_fees_are_strictly_zero() -> None:
    """Buy side orders incur zero SEC and zero FINRA TAF fee."""
    d = date(2020, 6, 1)
    assert compute_sec31_fee(d, Decimal("100000.00"), is_sell=False) == Decimal("0.00")
    assert compute_finra_taf(d, Decimal("1000"), is_sell=False) == Decimal("0.00")
    assert compute_finra_taf(d, 500, is_sell=False) == Decimal("0.00")


def test_sec31_calculation_and_rounding() -> None:
    """Verify Section 31 calculations for known rates."""
    # Segment 20 (2023-02-27 to 2024-05-21): $8.00 per $1,000,000 (rate 0.000008)
    d = date(2024, 3, 1)
    principal = Decimal("100000.00")  # $100k -> fee = $0.80
    assert compute_sec31_fee(d, principal) == Decimal("0.80")

    # Minimum cent floor on tiny positive principal
    tiny_principal = Decimal("10.00")  # 10 * 0.000008 = 0.00008 -> min $0.01
    assert compute_sec31_fee(d, tiny_principal) == Decimal("0.01")

    # Zero principal -> zero fee
    assert compute_sec31_fee(d, Decimal("0.00")) == Decimal("0.00")


def test_finra_taf_calculation_and_cap() -> None:
    """Verify FINRA TAF rate, rounding ceiling, and per-trade cap."""
    # Segment 4 (2012-07-01 to 2024-12-31): $0.000119/share, max $5.95
    d = date(2024, 3, 1)

    # 100 shares -> 100 * 0.000119 = 0.0119 -> ceil -> $0.02
    assert compute_finra_taf(d, 100) == Decimal("0.02")

    # 1 share -> 1 * 0.000119 = 0.000119 -> ceil -> $0.01
    assert compute_finra_taf(d, 1) == Decimal("0.01")

    # 50,000 shares -> 50,000 * 0.000119 = $5.95 -> exact cap
    assert compute_finra_taf(d, 50000) == Decimal("5.95")

    # 100,000 shares -> would be $11.90 -> capped at $5.95
    assert compute_finra_taf(d, 100000) == Decimal("5.95")

    # Segment 1 (2004-11-01 to 2011-06-30): $0.000075/share, max $3.75
    d_early = date(2009, 1, 15)
    assert compute_finra_taf(d_early, 100000) == Decimal("3.75")


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

    # Invalid type
    with pytest.raises(DataContractError, match="INVALID_TYPE"):
        compute_sec31_fee(date(2020, 1, 15), 100.50)  # type: ignore[arg-type]
