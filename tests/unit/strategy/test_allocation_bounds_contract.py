"""Test Phase 17 Capital Allocation Safety Bounds and Protocol Contracts."""

from decimal import Decimal
from typing import Sequence
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.strategy.schema import (
    AllocationSafetyBounds,
    IAllocationPolicy,
    PerformanceAttributionAssessment,
    StrategyAllocationProposal,
    StrategyDefinition,
    StrategyMechanism,
    StrategyRegimeObservation,
    StrategyStyle,
)


class MockPhase21Solver:
    """Mock implementation of future Phase 21 allocation solver satisfying IAllocationPolicy."""

    def propose_allocation(
        self,
        strategy: StrategyDefinition,
        candidate_evaluations: Sequence[StrategyRegimeObservation],
        safety_bounds: AllocationSafetyBounds,
        attribution: PerformanceAttributionAssessment,
    ) -> StrategyAllocationProposal:
        # If attribution confidence is zero or unverified, force allocation = 0.0
        if attribution.attribution_confidence == Decimal("0.0"):
            return StrategyAllocationProposal(
                strategy_id=strategy.strategy_id,
                proposed_weight=Decimal("0.0"),
                proposed_notional_usd=Decimal("0.0"),
                rationale="Attribution confidence is zero; fail-closed zero allocation enforced.",
                is_eligible=False,
                allocation_zero_enforced=True,
            )
        # Otherwise propose bounded allocation
        bounded_weight = min(Decimal("0.05"), safety_bounds.max_risk_budget_pct)
        bounded_notional = min(Decimal("500.0"), safety_bounds.max_notional_usd)
        return StrategyAllocationProposal(
            strategy_id=strategy.strategy_id,
            proposed_weight=bounded_weight,
            proposed_notional_usd=bounded_notional,
            rationale="Feasible bounded proposal",
            is_eligible=True,
        )


class TestAllocationBoundsContract:
    """Verify allocation safety bounds and zero allocation invariants."""

    def test_invariant_19_zero_allocation_always_valid(self) -> None:
        """Allocation of exactly 0.0 is always valid and default."""
        proposal = StrategyAllocationProposal(
            strategy_id="STRAT_CANDIDATE_01",
            proposed_weight=Decimal("0.0"),
            proposed_notional_usd=Decimal("0.0"),
            rationale="Default zero capital allocation",
            is_eligible=True,
        )
        assert proposal.proposed_weight == Decimal("0.0")
        assert proposal.proposed_notional_usd == Decimal("0.0")

    def test_invariant_20_strict_risk_ceilings(self) -> None:
        """Negative bounds raise DataContractError fail-closed."""
        with pytest.raises(DataContractError, match="cannot be negative"):
            AllocationSafetyBounds(
                max_notional_usd=Decimal("-100.0"),
                max_risk_budget_pct=Decimal("0.10"),
                max_gross_exposure_ratio=Decimal("2.0"),
            )

        with pytest.raises(DataContractError, match="cannot be negative"):
            AllocationSafetyBounds(
                max_notional_usd=Decimal("1000.0"),
                max_risk_budget_pct=Decimal("-0.05"),
                max_gross_exposure_ratio=Decimal("2.0"),
            )

    def test_invariant_21_unresolved_attribution_halts_allocation(self) -> None:
        """Strategy with zero attribution confidence fails closed to allocation == 0.0."""
        solver: IAllocationPolicy = MockPhase21Solver()
        strat = StrategyDefinition(
            strategy_id="STRAT_TEST_01",
            strategy_name="Unverified EA",
            strategy_version="1.0.0",
            mechanism=StrategyMechanism.FORECASTING,
            style=StrategyStyle.GRID_PROGRESSION,
            instrument_universe=("EURUSD",),
            timeframe="M15",
            entry_logic_summary="Grid entry",
            exit_logic_summary="Basket take profit",
            sizing_method="LINEAR",
            max_positions=5,
            max_gross_exposure_ratio=Decimal("3.0"),
        )
        bounds = AllocationSafetyBounds(
            max_notional_usd=Decimal("1000.0"),
            max_risk_budget_pct=Decimal("0.10"),
            max_gross_exposure_ratio=Decimal("2.0"),
        )
        unresolved_attr = PerformanceAttributionAssessment(
            gross_return=Decimal("0.20"),
            net_return=Decimal("0.15"),
            attribution_confidence=Decimal("0.0"),  # Zero confidence
        )
        proposal = solver.propose_allocation(strat, (), bounds, unresolved_attr)
        assert proposal.is_eligible is False
        assert proposal.proposed_weight == Decimal("0.0")
        assert proposal.proposed_notional_usd == Decimal("0.0")
        assert proposal.allocation_zero_enforced is True

    def test_invariant_22_protocol_feasibility(self) -> None:
        """IAllocationPolicy protocol correctly types mock solvers without error."""
        solver: IAllocationPolicy = MockPhase21Solver()
        strat = StrategyDefinition(
            strategy_id="STRAT_TEST_02",
            strategy_name="Verified Momentum",
            strategy_version="1.0.0",
            mechanism=StrategyMechanism.FORECASTING,
            style=StrategyStyle.MOMENTUM,
            instrument_universe=("EURUSD",),
            timeframe="H1",
            entry_logic_summary="20-day breakout",
            exit_logic_summary="ATR trailing stop",
            sizing_method="VOLATILITY_SCALED",
            max_positions=2,
            max_gross_exposure_ratio=Decimal("1.5"),
        )
        bounds = AllocationSafetyBounds(
            max_notional_usd=Decimal("1000.0"),
            max_risk_budget_pct=Decimal("0.10"),
            max_gross_exposure_ratio=Decimal("2.0"),
        )
        valid_attr = PerformanceAttributionAssessment(
            gross_return=Decimal("0.25"),
            net_return=Decimal("0.20"),
            attribution_confidence=Decimal("0.85"),
        )
        proposal = solver.propose_allocation(strat, (), bounds, valid_attr)
        assert proposal.is_eligible is True
        assert proposal.proposed_weight == Decimal("0.05")
        assert proposal.proposed_notional_usd == Decimal("500.0")
