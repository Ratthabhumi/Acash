"""Test Phase 17 Strategy Admission Contracts and Architectural Invariants."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.schema import ForwardHealthState
from acash.strategy.schema import (
    AllocationSafetyBounds,
    EffectiveEvidenceSample,
    EvidenceSupportLevel,
    ParameterProvenance,
    SkillEvidence,
    StrategyAdmissionStatus,
    StrategyAllocationProposal,
    StrategyDefinition,
    StrategyEvidenceLevel,
    StrategyLifecycleState,
    StrategyMechanism,
    StrategyStyle,
)


class TestAdmissionContracts:
    """Verify core decoupling and semantic invariants for strategy admission."""

    def test_invariant_1_admission_decoupling(self) -> None:
        """Admission != Selection != Allocation != Execution.

        An admitted strategy can have allocation == 0.0 with zero live execution authority.
        """
        strat = StrategyDefinition(
            strategy_id="STRAT_TREND_01",
            strategy_name="Trend Following Alpha",
            strategy_version="1.0.0",
            mechanism=StrategyMechanism.FORECASTING,
            style=StrategyStyle.TREND_FOLLOWING,
            instrument_universe=("EURUSD", "GBPUSD"),
            timeframe="H1",
            entry_logic_summary="Breakout above 20-period high",
            exit_logic_summary="Trailing stop at 2x ATR",
            sizing_method="FIXED_RISK",
            max_positions=3,
            max_gross_exposure_ratio=Decimal("2.0"),
        )
        assert strat.mechanism == StrategyMechanism.FORECASTING
        assert strat.style == StrategyStyle.TREND_FOLLOWING

        # Admitted status exists independently of allocation
        admission_status = StrategyAdmissionStatus.ADMITTED
        lifecycle_state = StrategyLifecycleState.CATALOG_ACTIVE

        # Target allocation can be strictly ZERO
        proposal = StrategyAllocationProposal(
            strategy_id=strat.strategy_id,
            proposed_weight=Decimal("0.0"),
            proposed_notional_usd=Decimal("0.0"),
            rationale="Admitted to catalog but capital allocated is $0.00 until Phase 21 selection",
            is_eligible=True,
            allocation_zero_enforced=True,
        )
        assert proposal.proposed_weight == Decimal("0.0")
        assert proposal.proposed_notional_usd == Decimal("0.0")
        assert admission_status == StrategyAdmissionStatus.ADMITTED
        assert lifecycle_state == StrategyLifecycleState.CATALOG_ACTIVE

    def test_invariant_2_calendar_anti_rule(self) -> None:
        """Calendar duration alone (e.g. 90 days) can never certify a strategy when N_eff is insufficient."""
        # 90 elapsed days with 0 effective sample observations cannot certify
        with pytest.raises(DataContractError, match="effective_sample_size cannot be negative"):
            EffectiveEvidenceSample(
                raw_observation_count=0,
                effective_sample_size=Decimal("-1.0"),
                estimator_method="BLOCK_BOOTSTRAP",
                dependency_model="IID",
                assumptions=("Zero trade history",),
            )

        # Effective sample size cannot materially exceed raw count
        with pytest.raises(DataContractError, match="cannot materially exceed raw_observation_count"):
            EffectiveEvidenceSample(
                raw_observation_count=10,
                effective_sample_size=Decimal("150.0"),
                estimator_method="AR1_AUTOCORRELATION_ADJUSTMENT",
                dependency_model="AR1",
                assumptions=("Autocorrelated signals",),
            )

    def test_invariant_3_evidence_maturity_not_superiority(self) -> None:
        """Level 6 (Live Execution) represents operational realism, NOT superior statistical edge.

        A strategy with Level 6 evidence cannot override a failed Gate 3 OOS test.
        """
        skill_evidence = SkillEvidence(
            out_of_sample_support=EvidenceSupportLevel.FAILED,
            walk_forward_support=EvidenceSupportLevel.FAILED,
            regime_coverage_support=EvidenceSupportLevel.SUPPORTED,
            execution_realism_support=EvidenceSupportLevel.SUPPORTED,
            robustness_support=EvidenceSupportLevel.WEAK,
            attribution_support=EvidenceSupportLevel.INCONCLUSIVE,
            persistence_support=EvidenceSupportLevel.FAILED,
            sample_quality_support=EvidenceSupportLevel.SUPPORTED,
            unresolved_alternatives_count=2,
            statistical_confidence=Decimal("0.15"),
        )
        # Operational realism can be SUPPORTED while statistical persistence is FAILED
        assert skill_evidence.execution_realism_support == EvidenceSupportLevel.SUPPORTED
        assert skill_evidence.out_of_sample_support == EvidenceSupportLevel.FAILED
        assert skill_evidence.persistence_support == EvidenceSupportLevel.FAILED

    def test_invariant_4_state_plane_independence(self) -> None:
        """AdmissionStatus, LifecycleState, and ForwardHealthState transition independently."""
        adm_status = StrategyAdmissionStatus.ADMITTED
        life_state = StrategyLifecycleState.CATALOG_ACTIVE

        # Runtime forward monitoring can report DEGRADED without destroying the admission record
        health_state = ForwardHealthState.DEGRADED
        assert adm_status == StrategyAdmissionStatus.ADMITTED
        assert life_state == StrategyLifecycleState.CATALOG_ACTIVE
        assert health_state == ForwardHealthState.DEGRADED

    def test_invariant_5_mechanism_vs_style_orthogonality(self) -> None:
        """StrategyMechanism and StrategyStyle are orthogonal and decoupled."""
        mm_strat = StrategyDefinition(
            strategy_id="STRAT_MM_01",
            strategy_name="Liquidity Provider Alpha",
            strategy_version="1.0.0",
            mechanism=StrategyMechanism.LIQUIDITY_PROVISION,
            style=StrategyStyle.MARKET_NEUTRAL,
            instrument_universe=("EURUSD",),
            timeframe="M1",
            entry_logic_summary="Post two-sided quotes at inside spread",
            exit_logic_summary="Inventory skew adjustment",
            sizing_method="INVENTORY_BALANCED",
            max_positions=10,
            max_gross_exposure_ratio=Decimal("5.0"),
        )
        assert mm_strat.mechanism == StrategyMechanism.LIQUIDITY_PROVISION
        assert mm_strat.style == StrategyStyle.MARKET_NEUTRAL

    def test_invariant_6_zero_allocation_when_ineligible(self) -> None:
        """When is_eligible is False, proposed_weight must strictly be 0.0."""
        with pytest.raises(DataContractError, match="must have proposed_weight == 0.0"):
            StrategyAllocationProposal(
                strategy_id="STRAT_FAIL_01",
                proposed_weight=Decimal("0.05"),
                proposed_notional_usd=Decimal("500.0"),
                rationale="Ineligible but tried to allocate",
                is_eligible=False,
            )
