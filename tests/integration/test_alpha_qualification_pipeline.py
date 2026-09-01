"""End-to-End Multi-Phase Integration Pipeline Tests (Slice 5).

Verifies the canonical integration seam:
Phase 4 (Hypothesis Specification & Manifest Lineage)
  -> Phase 6 (SearchTrialLedger & Statistical Validation Gate)
    -> Phase 8.5 (Economic Qualification, Zero-Rebate Isolation & Falsification Engine)
      -> AlphaQualificationGate & Dossier Sealing (RESEARCH_QUALIFIED)
        -> Phase 8 (Candidate Universe Input - Capital Authority strictly $0.00)

Strict Invariants Verified:
1. Research (8.5) != Allocation (8) != Risk (9) != Execution (7).
2. Capital authority strictly remains Decimal("0.00") across all Phase 8.5 artifacts.
3. No dependency loop: Phase 8.5 qualification does NOT require a downstream Phase 8 AllocationDecision.
4. Full cryptographic lineage DAG: Hypothesis -> TrialLedger -> ValidationReport -> GovernancePolicy -> Dossier.
5. Fail-closed on statistical rejection, economic hurdle failure, falsification triggers, and tampering.
"""

from decimal import Decimal
from typing import Tuple
import pytest
from pydantic import ValidationError

from acash.core.domain.exceptions import DataContractError
from acash.research.alpha_schema import (
    AlphaEconomicDecomposition,
    AlphaFalsificationTrigger,
    AlphaLifecycleState,
    FalsificationComparisonOperator,
    validate_lifecycle_transition,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.qualification import (
    AlphaQualificationGate,
    EconomicQualificationConfig,
    build_falsification_triggers_from_invalidation_criteria,
    create_economic_decomposition,
    evaluate_falsification_battery,
)
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
)
from acash.validation.schema import (
    SearchTrialLedger,
    SearchTrialRecord,
    ValidationGateVerdict,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Shared Multi-Phase Factories
# ---------------------------------------------------------------------------


@pytest.fixture
def canonical_hypothesis() -> HypothesisSpecification:
    """Canonical Phase 4 Pre-Registered Hypothesis Specification."""
    return HypothesisSpecification(
        hypothesis_id="HYP_SPY_VWAP_MR_001",
        hypothesis_version="v1.0",
        economic_rationale="Intraday mean reversion to session VWAP driven by liquidity provision.",
        target_symbol="SPY",
        feature_dependencies=["vwap_distance_bps", "volume_imbalance"],
        parameter_config_json='{"lookback_bars": 30, "entry_z": 2.0}',
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1, 5],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.025"),
            min_hac_t_stat=Decimal("2.00"),
            max_feature_autocorrelation=Decimal("0.98"),
            min_cost_adjusted_spread_ratio=Decimal("1.50"),
        ),
        registered_at_utc="2026-09-01T09:00:00Z",
        author="quant_researcher_01",
    )


@pytest.fixture
def canonical_sealed_trial_ledger(canonical_hypothesis: HypothesisSpecification) -> SearchTrialLedger:
    """Canonical Phase 6 Sealed SearchTrialLedger containing exhaustive search census."""
    trial_1 = SearchTrialRecord.create(
        trial_id="TRIAL_SPY_VWAP_001",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_id=canonical_hypothesis.hypothesis_id,
        feature_names=("vwap_distance_bps", "volume_imbalance"),
        parameters={"lookback_bars": 30, "entry_z": 2.0},
        in_sample_sharpe=Decimal("2.10"),
        execution_manifest_id="MAN_SEARCH_001",
        in_sample_returns=(Decimal("0.005"), Decimal("0.003"), Decimal("-0.001"), Decimal("0.008")),
    )
    trial_2 = SearchTrialRecord.create(
        trial_id="TRIAL_SPY_VWAP_002",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_id=canonical_hypothesis.hypothesis_id,
        feature_names=("vwap_distance_bps", "volume_imbalance"),
        parameters={"lookback_bars": 45, "entry_z": 2.5},
        in_sample_sharpe=Decimal("1.75"),
        execution_manifest_id="MAN_SEARCH_002",
        in_sample_returns=(Decimal("0.002"), Decimal("-0.002"), Decimal("0.004"), Decimal("0.006")),
    )
    unsealed_ledger = SearchTrialLedger(
        ledger_id="LEDGER_SPY_VWAP_001",
        hypothesis_id=canonical_hypothesis.hypothesis_id,
        strategy_id="STRAT_SPY_VWAP_V1",
        trials=(trial_1, trial_2),
        is_sealed=False,
    )
    return unsealed_ledger.seal(sealed_at_utc="2026-09-01T09:30:00Z")


@pytest.fixture
def canonical_passing_validation_report(
    canonical_hypothesis: HypothesisSpecification,
) -> ValidationReport:
    """Canonical Phase 6 ValidationReport with PASS_TRADEABLE_ALPHA verdict."""
    return ValidationReport(
        validation_id="VAL_REPORT_SPY_VWAP_001",
        evidence_digest="a" * 64,
        decision_digest="b" * 64,
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_id=canonical_hypothesis.hypothesis_id,
        verdict=ValidationGateVerdict.PASS_TRADEABLE_ALPHA,
        is_tradeable_alpha=True,
        in_sample_sharpe=Decimal("2.10"),
        out_of_sample_sharpe=Decimal("1.68"),
        oos_retention_pct=Decimal("80.00"),
        created_timestamp_utc="2026-09-01T10:00:00Z",
    )


# ---------------------------------------------------------------------------
# 1. Happy Path End-to-End Multi-Phase Qualification
# ---------------------------------------------------------------------------


def test_end_to_end_alpha_qualification_happy_path(
    canonical_hypothesis: HypothesisSpecification,
    canonical_sealed_trial_ledger: SearchTrialLedger,
    canonical_passing_validation_report: ValidationReport,
) -> None:
    """Scenario 1: Full lifecycle progression from Phase 4 through Phase 8.5 to RESEARCH_QUALIFIED."""
    # Step 1: Pre-register Phase 4 Invalidation Triggers
    falsification_triggers = build_falsification_triggers_from_invalidation_criteria(
        canonical_hypothesis.invalidation_criteria
    )
    assert len(falsification_triggers) == 4

    # Step 2: Evaluate Falsification Battery against empirical observations
    observed_metrics = {
        "rank_ic": Decimal("0.038"),           # > 0.025 (PASS)
        "hac_t_stat": Decimal("3.15"),          # > 2.00 (PASS)
        "autocorrelation_lag1": Decimal("0.65"),# < 0.98 (PASS)
        "spread_ratio": Decimal("2.40"),        # > 1.50 (PASS)
    }
    evaluated_triggers = evaluate_falsification_battery(falsification_triggers, observed_metrics)
    assert all(t.is_triggered is False for t in evaluated_triggers)

    # Step 3: Phase 8.5 Economic Decomposition (Rebate isolated)
    economic_decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("35.0"),
        realized_spread_slippage_bps=Decimal("4.0"),
        broker_commissions_bps=Decimal("1.0"),
        broker_rebate_income_bps=Decimal("10.0"),
    )
    assert economic_decomp.net_trading_alpha_bps == Decimal("30.0")
    assert economic_decomp.total_realized_economic_bps == Decimal("40.0")

    # Step 4: AlphaQualificationGate Master Orchestration
    gate = AlphaQualificationGate(
        config=EconomicQualificationConfig(hurdle_rate_bps=Decimal("5.0")),
        governance_policy_version="v1.3",
    )

    result = gate.qualify_alpha(
        alpha_id="ALPHA_SPY_VWAP_V1",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_spec=canonical_hypothesis,
        trial_ledger=canonical_sealed_trial_ledger,
        validation_report=canonical_passing_validation_report,
        economic_decomposition=economic_decomp,
        falsification_triggers=evaluated_triggers,
        current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
        fixed_created_timestamp_utc="2026-09-01T12:00:00Z",
    )

    # Invariant Verification: Successful qualification
    assert result.is_qualified is True
    assert result.lifecycle_state == AlphaLifecycleState.RESEARCH_QUALIFIED
    assert result.rejection_reason is None
    assert result.dossier is not None

    dossier = result.dossier
    assert dossier.is_research_qualified is True
    assert dossier.capital_authority_usd == Decimal("0.00")
    assert len(dossier.dossier_digest) == 64
    assert len(dossier.hypothesis_digest) == 64
    assert len(dossier.trial_ledger_digest) == 64
    assert len(dossier.validation_report_digest) == 64
    assert len(dossier.governance_policy_digest) == 64


# ---------------------------------------------------------------------------
# 2. Rejection Scenarios: Statistical, Economic, and Falsification
# ---------------------------------------------------------------------------


def test_end_to_end_statistical_rejection(
    canonical_hypothesis: HypothesisSpecification,
    canonical_sealed_trial_ledger: SearchTrialLedger,
) -> None:
    """Scenario 2: Statistical Gate failure produces REJECTED_STATISTICAL_GATE with no dossier."""
    failed_report = ValidationReport(
        validation_id="VAL_REPORT_FAIL",
        evidence_digest="a" * 64,
        decision_digest="b" * 64,
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_id=canonical_hypothesis.hypothesis_id,
        verdict=ValidationGateVerdict.REJECT_OVERFIT_DSR,
        is_tradeable_alpha=False,
        created_timestamp_utc="2026-09-01T10:00:00Z",
    )
    economic_decomp = create_economic_decomposition(gross_trading_pnl_bps=Decimal("35.0"))

    gate = AlphaQualificationGate()
    result = gate.qualify_alpha(
        alpha_id="ALPHA_FAILED_STAT",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_spec=canonical_hypothesis,
        trial_ledger=canonical_sealed_trial_ledger,
        validation_report=failed_report,
        economic_decomposition=economic_decomp,
    )

    assert result.is_qualified is False
    assert result.lifecycle_state == AlphaLifecycleState.REJECTED_STATISTICAL_GATE
    assert result.dossier is None
    assert "failed Phase 6 statistical validation gate" in (result.rejection_reason or "")


def test_end_to_end_economic_hurdle_rejection_with_rebate_subsidy(
    canonical_hypothesis: HypothesisSpecification,
    canonical_sealed_trial_ledger: SearchTrialLedger,
    canonical_passing_validation_report: ValidationReport,
) -> None:
    """Scenario 3: Bleeding strategy subsidized by massive rebates is REJECTED_HURDLE_COLLAPSE."""
    bleeding_decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("8.0"),
        realized_spread_slippage_bps=Decimal("12.0"),
        broker_commissions_bps=Decimal("2.0"),
        broker_rebate_income_bps=Decimal("150.0"),  # Gross 8 - Costs 14 = Net -6 bps!
    )
    assert bleeding_decomp.net_trading_alpha_bps == Decimal("-6.0")
    assert bleeding_decomp.total_realized_economic_bps == Decimal("144.0")

    gate = AlphaQualificationGate(config=EconomicQualificationConfig(hurdle_rate_bps=Decimal("5.0")))
    result = gate.qualify_alpha(
        alpha_id="ALPHA_REBATE_BLEED",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_spec=canonical_hypothesis,
        trial_ledger=canonical_sealed_trial_ledger,
        validation_report=canonical_passing_validation_report,
        economic_decomposition=bleeding_decomp,
    )

    assert result.is_qualified is False
    assert result.lifecycle_state == AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE
    assert result.dossier is None
    assert "failed hurdle rate" in (result.rejection_reason or "")


def test_end_to_end_falsification_trigger_degradation(
    canonical_hypothesis: HypothesisSpecification,
    canonical_sealed_trial_ledger: SearchTrialLedger,
    canonical_passing_validation_report: ValidationReport,
) -> None:
    """Scenario 4: Tripped falsification trigger degrades candidate to DEGRADED_FORWARD_TEST."""
    triggers = build_falsification_triggers_from_invalidation_criteria(
        canonical_hypothesis.invalidation_criteria
    )
    # Autocorrelation exceeds maximum allowable threshold (0.99 > 0.98)
    observed_metrics = {
        "rank_ic": Decimal("0.038"),
        "hac_t_stat": Decimal("3.15"),
        "autocorrelation_lag1": Decimal("0.99"),  # TRIPPED!
        "spread_ratio": Decimal("2.40"),
    }
    evaluated_triggers = evaluate_falsification_battery(triggers, observed_metrics)

    economic_decomp = create_economic_decomposition(gross_trading_pnl_bps=Decimal("35.0"))
    gate = AlphaQualificationGate()
    result = gate.qualify_alpha(
        alpha_id="ALPHA_DEGRADED",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_spec=canonical_hypothesis,
        trial_ledger=canonical_sealed_trial_ledger,
        validation_report=canonical_passing_validation_report,
        economic_decomposition=economic_decomp,
        falsification_triggers=evaluated_triggers,
    )

    assert result.is_qualified is False
    assert result.lifecycle_state == AlphaLifecycleState.DEGRADED_FORWARD_TEST
    assert result.dossier is None
    assert "Falsification triggers tripped" in (result.rejection_reason or "")


# ---------------------------------------------------------------------------
# 3. Lineage Tampering & Fail-Closed Integrity
# ---------------------------------------------------------------------------


def test_end_to_end_evidence_tampering_detection(
    canonical_hypothesis: HypothesisSpecification,
    canonical_sealed_trial_ledger: SearchTrialLedger,
    canonical_passing_validation_report: ValidationReport,
) -> None:
    """Scenario 5: Modifying an upstream artifact (e.g. strategy ID mismatch) fails closed."""
    mismatched_report = ValidationReport(
        validation_id="VAL_TAMPERED",
        evidence_digest="a" * 64,
        decision_digest="b" * 64,
        strategy_id="DIFFERENT_STRATEGY_ID",  # Tampered strategy ID!
        hypothesis_id=canonical_hypothesis.hypothesis_id,
        verdict=ValidationGateVerdict.PASS_TRADEABLE_ALPHA,
        is_tradeable_alpha=True,
        created_timestamp_utc="2026-09-01T10:00:00Z",
    )
    economic_decomp = create_economic_decomposition(gross_trading_pnl_bps=Decimal("35.0"))

    gate = AlphaQualificationGate()
    with pytest.raises(DataContractError, match="Lineage mismatch"):
        gate.qualify_alpha(
            alpha_id="ALPHA_TAMPERED",
            strategy_id="STRAT_SPY_VWAP_V1",
            hypothesis_spec=canonical_hypothesis,
            trial_ledger=canonical_sealed_trial_ledger,
            validation_report=mismatched_report,
            economic_decomposition=economic_decomp,
        )


def test_end_to_end_lifecycle_state_machine_violations() -> None:
    """Scenario 6: Illegal transitions across the pipeline raise DataContractError."""
    # Skipping transitions: HYPOTHESIS directly to ECONOMIC_EDGE_QUALIFIED
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        validate_lifecycle_transition(
            AlphaLifecycleState.HYPOTHESIS,
            AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED,
        )

    # Retrospective transitions: RESEARCH_QUALIFIED back to CANDIDATE
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        validate_lifecycle_transition(
            AlphaLifecycleState.RESEARCH_QUALIFIED,
            AlphaLifecycleState.CANDIDATE,
        )

    # Outbound transition from terminal state
    with pytest.raises(DataContractError, match="Illegal Alpha lifecycle transition"):
        validate_lifecycle_transition(
            AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK,
            AlphaLifecycleState.RESEARCH_SEARCH,
        )


# ---------------------------------------------------------------------------
# 4. Phase 8 Candidate Universe Handoff & Boundary Invariants
# ---------------------------------------------------------------------------


def test_phase_8_candidate_handoff_and_zero_capital_authority(
    canonical_hypothesis: HypothesisSpecification,
    canonical_sealed_trial_ledger: SearchTrialLedger,
    canonical_passing_validation_report: ValidationReport,
) -> None:
    """Scenario 7: Qualified Alpha enters Phase 8 universe with ZERO capital authority and NO execution authority."""
    economic_decomp = create_economic_decomposition(gross_trading_pnl_bps=Decimal("30.0"))
    gate = AlphaQualificationGate()

    result = gate.qualify_alpha(
        alpha_id="ALPHA_SPY_001",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_spec=canonical_hypothesis,
        trial_ledger=canonical_sealed_trial_ledger,
        validation_report=canonical_passing_validation_report,
        economic_decomposition=economic_decomp,
        fixed_created_timestamp_utc="2026-09-01T12:00:00Z",
    )
    assert result.is_qualified is True
    assert result.dossier is not None

    dossier = result.dossier

    # Invariant 1: Capital authority is exactly $0.00
    assert dossier.capital_authority_usd == Decimal("0.00")

    # Invariant 2: Candidate universe representation payload
    candidate_universe_entry = {
        "alpha_id": dossier.alpha_id,
        "strategy_id": dossier.strategy_id,
        "dossier_digest": dossier.dossier_digest,
        "lifecycle_state": dossier.lifecycle_state.value,
        "is_research_qualified": dossier.is_research_qualified,
        "net_trading_alpha_bps": str(dossier.economic_decomposition.net_trading_alpha_bps),
        "capital_authority_usd": str(dossier.capital_authority_usd),
    }

    assert candidate_universe_entry["lifecycle_state"] == "RESEARCH_QUALIFIED"
    assert candidate_universe_entry["capital_authority_usd"] == "0.00"

    # Invariant 3: Modifying capital authority raises ValidationError
    with pytest.raises(ValidationError, match="Instance is frozen"):
        setattr(dossier, "capital_authority_usd", Decimal("10000.00"))


# ---------------------------------------------------------------------------
# 5. Deterministic Repeated Execution
# ---------------------------------------------------------------------------


def test_end_to_end_deterministic_pipeline_repeatability(
    canonical_hypothesis: HypothesisSpecification,
    canonical_sealed_trial_ledger: SearchTrialLedger,
    canonical_passing_validation_report: ValidationReport,
) -> None:
    """Scenario 8: Running the entire pipeline twice from same canonical inputs yields identical DAG digests."""
    falsification_triggers = build_falsification_triggers_from_invalidation_criteria(
        canonical_hypothesis.invalidation_criteria
    )
    observed_metrics = {
        "rank_ic": Decimal("0.038"),
        "hac_t_stat": Decimal("3.15"),
        "autocorrelation_lag1": Decimal("0.65"),
        "spread_ratio": Decimal("2.40"),
    }
    evaluated_triggers = evaluate_falsification_battery(falsification_triggers, observed_metrics)
    economic_decomp = create_economic_decomposition(gross_trading_pnl_bps=Decimal("35.0"))

    gate = AlphaQualificationGate(governance_policy_version="v1.3")

    run_1 = gate.qualify_alpha(
        alpha_id="ALPHA_DETERMINISTIC",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_spec=canonical_hypothesis,
        trial_ledger=canonical_sealed_trial_ledger,
        validation_report=canonical_passing_validation_report,
        economic_decomposition=economic_decomp,
        falsification_triggers=evaluated_triggers,
        fixed_created_timestamp_utc="2026-09-01T12:00:00Z",
    )

    run_2 = gate.qualify_alpha(
        alpha_id="ALPHA_DETERMINISTIC",
        strategy_id="STRAT_SPY_VWAP_V1",
        hypothesis_spec=canonical_hypothesis,
        trial_ledger=canonical_sealed_trial_ledger,
        validation_report=canonical_passing_validation_report,
        economic_decomposition=economic_decomp,
        falsification_triggers=evaluated_triggers,
        fixed_created_timestamp_utc="2026-09-01T12:00:00Z",
    )

    assert run_1.dossier is not None and run_2.dossier is not None
    assert run_1.dossier.dossier_digest == run_2.dossier.dossier_digest
    assert run_1.dossier.hypothesis_digest == run_2.dossier.hypothesis_digest
    assert run_1.dossier.trial_ledger_digest == run_2.dossier.trial_ledger_digest
    assert run_1.dossier.validation_report_digest == run_2.dossier.validation_report_digest
    assert run_1.dossier.governance_policy_digest == run_2.dossier.governance_policy_digest
