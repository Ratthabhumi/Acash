"""Unit & Adversarial Tests for Phase 8.5 Economic Qualification & Rebate Isolation (Slice 2).

Covers:
- Standard economic qualification pass (Net Alpha >= Hurdle).
- Strict zero-rebate isolation: Positive rebate cannot rescue a negative net alpha strategy.
- Boundary condition: Net Alpha exactly equal to Hurdle Rate is eligible (inclusive >=).
- Sub-hurdle rejection: Net Alpha < Hurdle transitions to REJECTED_HURDLE_COLLAPSE.
- Monotonicity: Increasing friction costs strictly monotonically decreases viability.
- Monotonicity: Increasing rebates has strictly ZERO impact on qualification decisions.
- Lifecycle transition enforcement and fail-closed state validation.
- Immutability, extra="forbid", and Decimal precision determinism.
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from acash.core.domain.exceptions import DataContractError
from acash.research.alpha_schema import (
    AlphaEconomicDecomposition,
    AlphaLifecycleState,
)
from acash.research.qualification import (
    EconomicQualificationConfig,
    EconomicQualificationDecision,
    create_economic_decomposition,
    evaluate_economic_qualification,
)


# ---------------------------------------------------------------------------
# 1. Standard Economic Qualification & Viability Tests
# ---------------------------------------------------------------------------


def test_standard_economic_qualification_pass() -> None:
    """Verify that a strategy clearing the hurdle on net alpha is qualified."""
    decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("100.0"),
        realized_spread_slippage_bps=Decimal("15.0"),
        broker_commissions_bps=Decimal("5.0"),
        broker_rebate_income_bps=Decimal("30.0"),
    )
    assert decomp.net_trading_alpha_bps == Decimal("80.0")
    assert decomp.total_realized_economic_bps == Decimal("110.0")

    decision = evaluate_economic_qualification(
        decomposition=decomp,
        hurdle_rate_bps=Decimal("50.0"),
        current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
    )

    assert decision.is_viable is True
    assert decision.lifecycle_verdict == AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED
    assert decision.excess_alpha_over_hurdle_bps == Decimal("30.0")
    assert decision.rejection_reason is None


def test_positive_rebate_cannot_rescue_negative_net_alpha() -> None:
    """Critical Invariant: Positive rebate cannot qualify a negative net-alpha strategy."""
    decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("10.0"),
        realized_spread_slippage_bps=Decimal("15.0"),
        broker_commissions_bps=Decimal("5.0"),
        broker_rebate_income_bps=Decimal("100.0"),  # Massive rebate subsidy!
    )
    # Net alpha is negative (-10.0 bps), while total economic return is +90.0 bps
    assert decomp.net_trading_alpha_bps == Decimal("-10.0")
    assert decomp.total_realized_economic_bps == Decimal("90.0")

    decision = evaluate_economic_qualification(
        decomposition=decomp,
        hurdle_rate_bps=Decimal("5.0"),
        current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
    )

    # Invariant: Must fail and emit REJECTED_HURDLE_COLLAPSE
    assert decision.is_viable is False
    assert decision.lifecycle_verdict == AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE
    assert decision.excess_alpha_over_hurdle_bps == Decimal("-15.0")
    assert decision.rejection_reason is not None
    assert "failed hurdle rate" in decision.rejection_reason


def test_net_alpha_exactly_at_hurdle_boundary() -> None:
    """Verify that Net Alpha exactly equal to hurdle passes (inclusive >=)."""
    decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("20.0"),
        realized_spread_slippage_bps=Decimal("10.0"),
        broker_commissions_bps=Decimal("5.0"),
        broker_rebate_income_bps=Decimal("0.0"),
    )
    assert decomp.net_trading_alpha_bps == Decimal("5.0")

    # Hurdle = 5.0 bps -> exactly equal
    decision = evaluate_economic_qualification(
        decomposition=decomp,
        hurdle_rate_bps=Decimal("5.0"),
        current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
    )

    assert decision.is_viable is True
    assert decision.lifecycle_verdict == AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED
    assert decision.excess_alpha_over_hurdle_bps == Decimal("0.0")


def test_net_alpha_slightly_below_hurdle_fails() -> None:
    """Verify that Net Alpha strictly below hurdle fails (strict boundary)."""
    decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("19.99"),
        realized_spread_slippage_bps=Decimal("10.00"),
        broker_commissions_bps=Decimal("5.00"),
        broker_rebate_income_bps=Decimal("50.00"),
    )
    assert decomp.net_trading_alpha_bps == Decimal("4.99")

    # Hurdle = 5.00 bps -> 4.99 < 5.00
    decision = evaluate_economic_qualification(
        decomposition=decomp,
        hurdle_rate_bps=Decimal("5.00"),
        current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
    )

    assert decision.is_viable is False
    assert decision.lifecycle_verdict == AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE
    assert decision.excess_alpha_over_hurdle_bps == Decimal("-0.01")


# ---------------------------------------------------------------------------
# 2. Monotonicity & Sensitivity Tests
# ---------------------------------------------------------------------------


def test_monotonicity_of_increasing_friction_costs() -> None:
    """Verify that increasing friction costs monotonically decreases excess alpha and never improves viability."""
    hurdle = Decimal("10.0")
    gross = Decimal("25.0")
    spread_levels = [Decimal("1.0"), Decimal("5.0"), Decimal("10.0"), Decimal("15.0"), Decimal("20.0")]
    previous_excess = Decimal("1000.0")

    for spread in spread_levels:
        decomp = create_economic_decomposition(
            gross_trading_pnl_bps=gross,
            realized_spread_slippage_bps=spread,
            broker_commissions_bps=Decimal("2.0"),
            broker_rebate_income_bps=Decimal("0.0"),
        )
        decision = evaluate_economic_qualification(
            decomposition=decomp,
            hurdle_rate_bps=hurdle,
            current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
        )

        # Monotonicity check: excess alpha strictly decreases
        assert decision.excess_alpha_over_hurdle_bps < previous_excess
        previous_excess = decision.excess_alpha_over_hurdle_bps

        # Correct state assignment
        if decomp.net_trading_alpha_bps >= hurdle:
            assert decision.is_viable is True
            assert decision.lifecycle_verdict == AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED
        else:
            assert decision.is_viable is False
            assert decision.lifecycle_verdict == AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE


def test_rebate_invariance_monotonicity() -> None:
    """Verify that varying rebates across several orders of magnitude has ZERO impact on qualification."""
    hurdle = Decimal("5.0")
    # Failing strategy: Gross 5 - Costs 7 = Net -2
    gross = Decimal("5.0")
    costs = Decimal("7.0")
    rebate_levels = [
        Decimal("0.0"),
        Decimal("1.0"),
        Decimal("10.0"),
        Decimal("100.0"),
        Decimal("1000.0"),
        Decimal("10000.0"),
    ]

    for rebate in rebate_levels:
        decomp = create_economic_decomposition(
            gross_trading_pnl_bps=gross,
            realized_spread_slippage_bps=costs,
            broker_commissions_bps=Decimal("0.0"),
            broker_rebate_income_bps=rebate,
        )
        decision = evaluate_economic_qualification(
            decomposition=decomp,
            hurdle_rate_bps=hurdle,
            current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
        )

        # Invariant: Must remain exactly non-viable with identical excess alpha
        assert decision.is_viable is False
        assert decision.lifecycle_verdict == AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE
        assert decision.excess_alpha_over_hurdle_bps == Decimal("-7.0")


# ---------------------------------------------------------------------------
# 3. State Machine & Lifecycle Transition Enforcement Tests
# ---------------------------------------------------------------------------


def test_illegal_lifecycle_transition_raises_data_contract_error() -> None:
    """Verify that evaluating qualification from an invalid current state raises DataContractError."""
    decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("20.0"),
        realized_spread_slippage_bps=Decimal("2.0"),
        broker_commissions_bps=Decimal("1.0"),
    )
    # Attempting to jump from HYPOTHESIS directly to ECONOMIC_EDGE_QUALIFIED
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        evaluate_economic_qualification(
            decomposition=decomp,
            hurdle_rate_bps=Decimal("5.0"),
            current_state=AlphaLifecycleState.HYPOTHESIS,
        )

    # Attempting transition from a terminal state (RETIRED_STRUCTURAL_BREAK)
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        evaluate_economic_qualification(
            decomposition=decomp,
            hurdle_rate_bps=Decimal("5.0"),
            current_state=AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK,
        )


# ---------------------------------------------------------------------------
# 4. Immutability & Model Integrity Tests
# ---------------------------------------------------------------------------


def test_economic_qualification_decision_immutability_and_extra_forbid() -> None:
    """Verify that EconomicQualificationDecision is strictly frozen and forbids extra fields."""
    decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("20.0"),
        realized_spread_slippage_bps=Decimal("2.0"),
        broker_commissions_bps=Decimal("1.0"),
    )
    decision = evaluate_economic_qualification(
        decomposition=decomp,
        hurdle_rate_bps=Decimal("5.0"),
        current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
    )

    # Mutation attempt raises ValidationError
    with pytest.raises(ValidationError, match="Instance is frozen"):
        decision.is_viable = False

    # Extra field attempt raises ValidationError
    with pytest.raises(ValidationError, match="extra_forbidden"):
        EconomicQualificationDecision(
            is_viable=decision.is_viable,
            lifecycle_verdict=decision.lifecycle_verdict,
            economic_decomposition=decision.economic_decomposition,
            hurdle_rate_bps=decision.hurdle_rate_bps,
            excess_alpha_over_hurdle_bps=decision.excess_alpha_over_hurdle_bps,
            unauthorized_grant="malicious_capital",  # type: ignore[call-arg]
        )
