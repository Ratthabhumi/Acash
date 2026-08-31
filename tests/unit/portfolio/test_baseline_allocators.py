"""Unit tests for Phase 8 Level 1 Baseline Allocators (Cash, 1/N, Inverse-Vol)."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.baselines import (
    CashAllocator,
    EqualWeightAllocator,
    InverseVolatilityAllocator,
)
from acash.portfolio.schema import AssetReturnPanel, PortfolioConstraints


def _sample_panel() -> AssetReturnPanel:
    t1 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    t4 = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)

    # Volatility of Asset A will be higher than Asset B
    returns = (
        (Decimal("0.02"), Decimal("0.01")),
        (Decimal("-0.02"), Decimal("0.01")),
        (Decimal("0.03"), Decimal("-0.01")),
        (Decimal("-0.03"), Decimal("-0.01")),
    )

    return AssetReturnPanel(
        universe_id="UNIV_TEST",
        timestamps=(t1, t2, t3, t4),
        symbols=("ASSET_A", "ASSET_B"),
        returns_matrix=returns,
        frequency="1D",
    )


def _default_constraints() -> PortfolioConstraints:
    return PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("1.0"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.10"),
    )


def test_cash_allocator() -> None:
    """Verify CashAllocator proposes 100% cash with 0 risky asset weights."""
    panel = _sample_panel()
    constraints = _default_constraints()
    allocator = CashAllocator()

    cand = allocator.compute_candidate(
        panel=panel,
        constraints=constraints,
        current_weights={"ASSET_A": Decimal("0.0"), "ASSET_B": Decimal("0.0")},
    )

    assert cand.allocator_name == "CASH"
    assert cand.asset_weights["ASSET_A"] == Decimal("0.0")
    assert cand.asset_weights["ASSET_B"] == Decimal("0.0")
    assert cand.cash_weight == Decimal("1.0")


def test_equal_weight_allocator() -> None:
    """Verify EqualWeightAllocator divides (1 - min_cash_buffer) equally across N assets."""
    panel = _sample_panel()
    constraints = _default_constraints()  # min_cash_buffer = 0.10
    allocator = EqualWeightAllocator()

    cand = allocator.compute_candidate(
        panel=panel,
        constraints=constraints,
        current_weights={"ASSET_A": Decimal("0.0"), "ASSET_B": Decimal("0.0")},
    )

    assert cand.allocator_name == "EQUAL_WEIGHT"
    # (1.0 - 0.10) / 2 = 0.45
    assert cand.asset_weights["ASSET_A"] == Decimal("0.45")
    assert cand.asset_weights["ASSET_B"] == Decimal("0.45")
    assert cand.cash_weight == Decimal("0.10")


def test_equal_weight_max_weight_residual_cash() -> None:
    """Verify EqualWeightAllocator caps weights at max_weight and leaves residual as unallocated cash."""
    panel = _sample_panel()  # N = 2
    # max_weight = 0.30 -> each gets 0.30, risky sum = 0.60, cash = 0.40
    constrained = PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("0.30"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )
    allocator = EqualWeightAllocator()
    cand = allocator.compute_candidate(
        panel=panel,
        constraints=constrained,
        current_weights={"ASSET_A": Decimal("0.0"), "ASSET_B": Decimal("0.0")},
    )

    assert cand.asset_weights["ASSET_A"] == Decimal("0.30")
    assert cand.asset_weights["ASSET_B"] == Decimal("0.30")
    assert cand.cash_weight == Decimal("0.40")


def test_inverse_volatility_allocator() -> None:
    """Verify InverseVolatilityAllocator allocates inversely to asset standard deviation."""
    panel = _sample_panel()
    constraints = _default_constraints()  # min_cash_buffer = 0.10
    allocator = InverseVolatilityAllocator()

    cand = allocator.compute_candidate(
        panel=panel,
        constraints=constraints,
        current_weights={"ASSET_A": Decimal("0.0"), "ASSET_B": Decimal("0.0")},
    )

    assert cand.allocator_name == "INVERSE_VOL"
    # ASSET_B has lower vol -> higher weight than ASSET_A
    assert cand.asset_weights["ASSET_B"] > cand.asset_weights["ASSET_A"]
    # Total sum of asset weights + cash weight must equal 1.0 exactly
    total_alloc = sum(cand.asset_weights.values()) + (cand.cash_weight or Decimal("0"))
    assert abs(total_alloc - Decimal("1.0")) < Decimal("1e-12")


def test_inverse_volatility_max_weight_residual_cash() -> None:
    """Verify InverseVolatilityAllocator caps highest-allocated asset at max_weight and retains residual cash."""
    panel = _sample_panel()
    # Impose a tight max_weight cap of 0.40
    constrained = PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("0.40"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )
    allocator = InverseVolatilityAllocator()
    cand = allocator.compute_candidate(
        panel=panel,
        constraints=constrained,
        current_weights={"ASSET_A": Decimal("0.0"), "ASSET_B": Decimal("0.0")},
    )

    assert cand.asset_weights["ASSET_B"] <= Decimal("0.40")
    assert cand.asset_weights["ASSET_A"] <= Decimal("0.40")
    total_alloc = sum(cand.asset_weights.values()) + (cand.cash_weight or Decimal("0"))
    assert abs(total_alloc - Decimal("1.0")) < Decimal("1e-12")


def test_inverse_volatility_zero_vol_fail_closed() -> None:
    """Verify InverseVolatilityAllocator fails closed on zero volatility (no magic floors)."""
    t1 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Constant zero returns -> vol = 0
    returns = (
        (Decimal("0.0"), Decimal("0.01")),
        (Decimal("0.0"), Decimal("0.02")),
    )
    panel = AssetReturnPanel(
        universe_id="UNIV_TEST",
        timestamps=(t1, t2),
        symbols=("ASSET_FLAT", "ASSET_NORM"),
        returns_matrix=returns,
        frequency="1D",
    )
    allocator = InverseVolatilityAllocator()
    with pytest.raises(DataContractError, match="Zero or invalid volatility detected"):
        allocator.compute_candidate(
            panel=panel,
            constraints=_default_constraints(),
            current_weights={"ASSET_FLAT": Decimal("0.0"), "ASSET_NORM": Decimal("0.0")},
        )
