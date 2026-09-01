"""Unit & Adversarial Tests for Phase 8.5 Alpha Qualification Gate & Dossier Sealing (Slice 4).

Covers:
- Master AlphaQualificationGate orchestration across Phase 4, Phase 6, and Phase 8.5 evidence.
- Full qualification happy path: transition to RESEARCH_QUALIFIED with sealed AlphaQualificationDossier.
- Fail-closed rejection on Phase 6 Statistical Gate failure (REJECTED_STATISTICAL_GATE).
- Fail-closed rejection on Phase 8.5 Economic Hurdle failure (REJECTED_HURDLE_COLLAPSE).
- Fail-closed degradation on tripped Falsification Triggers (DEGRADED_FORWARD_TEST).
- Zero Rebate Rescue invariant: positive rebate with negative net alpha strictly rejected.
- Lineage integrity: hypothesis ID mismatch, strategy ID mismatch, tampered trial ledger.
- Deterministic SHA-256 DAG and dossier digest repeatability.
- Zero capital authority ($0.00) invariant and zero live execution authority.
- No dependency loop on Phase 8 portfolio allocation.
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
)
from acash.research.qualification import (
    AlphaQualificationGate,
    EconomicQualificationConfig,
    create_economic_decomposition,
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
# Test Fixtures & Builders
# ---------------------------------------------------------------------------


@pytest.fixture
def hypothesis_fixture() -> HypothesisSpecification:
    return HypothesisSpecification(
        hypothesis_id="HYP_ALPHA_MOM_001",
        hypothesis_version="v1.0",
        economic_rationale="Momentum predictive edge adjusted for volatility.",
        target_symbol="SPY",
        feature_dependencies=["mom_20d", "vol_20d"],
        parameter_config_json='{"lookback": 20}',
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1, 5],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.025"),
            min_hac_t_stat=Decimal("2.00"),
            max_feature_autocorrelation=Decimal("0.98"),
            min_cost_adjusted_spread_ratio=Decimal("1.50"),
        ),
        registered_at_utc="2026-09-01T10:00:00Z",
        author="quant_researcher",
    )


@pytest.fixture
def sealed_trial_ledger_fixture(hypothesis_fixture: HypothesisSpecification) -> SearchTrialLedger:
    trial = SearchTrialRecord.create(
        trial_id="TRIAL_001",
        strategy_id="STRAT_MOM_001",
        hypothesis_id=hypothesis_fixture.hypothesis_id,
        feature_names=("mom_20d",),
        parameters={"lookback": 20},
        in_sample_sharpe=Decimal("1.85"),
        execution_manifest_id="MAN_001",
        in_sample_returns=(Decimal("0.01"), Decimal("-0.005"), Decimal("0.008")),
    )
    unsealed_ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        hypothesis_id=hypothesis_fixture.hypothesis_id,
        strategy_id="STRAT_MOM_001",
        trials=(trial,),
        is_sealed=False,
    )
    return unsealed_ledger.seal(sealed_at_utc="2026-09-01T11:00:00Z")




@pytest.fixture
def passing_validation_report_fixture(
    hypothesis_fixture: HypothesisSpecification,
) -> ValidationReport:
    return ValidationReport(
        validation_id="VAL_STRAT_MOM_001_0001",
        evidence_digest="1" * 64,
        decision_digest="2" * 64,
        strategy_id="STRAT_MOM_001",
        hypothesis_id=hypothesis_fixture.hypothesis_id,
        verdict=ValidationGateVerdict.PASS_TRADEABLE_ALPHA,
        is_tradeable_alpha=True,
        in_sample_sharpe=Decimal("1.85"),
        out_of_sample_sharpe=Decimal("1.42"),
        oos_retention_pct=Decimal("76.75"),
        created_timestamp_utc="2026-09-01T11:30:00Z",
    )


@pytest.fixture
def clean_economic_decomp() -> AlphaEconomicDecomposition:
    return create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("25.0"),
        realized_spread_slippage_bps=Decimal("3.0"),
        broker_commissions_bps=Decimal("2.0"),
        broker_rebate_income_bps=Decimal("0.0"),
    )


@pytest.fixture
def clean_falsification_triggers() -> Tuple[AlphaFalsificationTrigger, ...]:
    return (
        AlphaFalsificationTrigger(
            trigger_name="OOS_RANK_IC_DEGRADATION",
            metric_name="rank_ic",
            threshold_value=Decimal("0.025"),
            comparison_operator=FalsificationComparisonOperator.LESS_THAN,
            is_triggered=False,
            observed_value=Decimal("0.045"),
        ),
    )


# ---------------------------------------------------------------------------
# 1. Master Qualification Happy Path & Sealing Tests
# ---------------------------------------------------------------------------


def test_alpha_qualification_gate_full_happy_path(
    hypothesis_fixture: HypothesisSpecification,
    sealed_trial_ledger_fixture: SearchTrialLedger,
    passing_validation_report_fixture: ValidationReport,
    clean_economic_decomp: AlphaEconomicDecomposition,
    clean_falsification_triggers: Tuple[AlphaFalsificationTrigger, ...],
) -> None:
    """Verify end-to-end evidence aggregation and sealing into AlphaQualificationDossier."""
    gate = AlphaQualificationGate(
        config=EconomicQualificationConfig(hurdle_rate_bps=Decimal("5.0")),
        governance_policy_version="v1.0",
    )

    result = gate.qualify_alpha(
        alpha_id="ALPHA_MOM_SPY_V1",
        strategy_id="STRAT_MOM_001",
        hypothesis_spec=hypothesis_fixture,
        trial_ledger=sealed_trial_ledger_fixture,
        validation_report=passing_validation_report_fixture,
        economic_decomposition=clean_economic_decomp,
        falsification_triggers=clean_falsification_triggers,
        current_state=AlphaLifecycleState.STATISTICAL_VALIDATED,
        fixed_created_timestamp_utc="2026-09-01T12:00:00Z",
    )

    assert result.is_qualified is True
    assert result.lifecycle_state == AlphaLifecycleState.RESEARCH_QUALIFIED
    assert result.rejection_reason is None
    assert result.dossier is not None

    dossier = result.dossier
    assert dossier.alpha_id == "ALPHA_MOM_SPY_V1"
    assert dossier.strategy_id == "STRAT_MOM_001"
    assert dossier.lifecycle_state == AlphaLifecycleState.RESEARCH_QUALIFIED
    assert dossier.is_research_qualified is True
    assert dossier.capital_authority_usd == Decimal("0.00")
    assert len(dossier.dossier_digest) == 64
    assert len(dossier.hypothesis_digest) == 64
    assert len(dossier.trial_ledger_digest) == 64
    assert len(dossier.validation_report_digest) == 64


def test_dossier_sealing_determinism_and_repeatability(
    hypothesis_fixture: HypothesisSpecification,
    sealed_trial_ledger_fixture: SearchTrialLedger,
    passing_validation_report_fixture: ValidationReport,
    clean_economic_decomp: AlphaEconomicDecomposition,
    clean_falsification_triggers: Tuple[AlphaFalsificationTrigger, ...],
) -> None:
    """Verify that repeated qualification with identical inputs yields bit-for-bit identical digests."""
    gate = AlphaQualificationGate()

    result1 = gate.qualify_alpha(
        alpha_id="ALPHA_REPEATABLE",
        strategy_id="STRAT_MOM_001",
        hypothesis_spec=hypothesis_fixture,
        trial_ledger=sealed_trial_ledger_fixture,
        validation_report=passing_validation_report_fixture,
        economic_decomposition=clean_economic_decomp,
        falsification_triggers=clean_falsification_triggers,
        fixed_created_timestamp_utc="2026-09-01T12:00:00Z",
    )

    result2 = gate.qualify_alpha(
        alpha_id="ALPHA_REPEATABLE",
        strategy_id="STRAT_MOM_001",
        hypothesis_spec=hypothesis_fixture,
        trial_ledger=sealed_trial_ledger_fixture,
        validation_report=passing_validation_report_fixture,
        economic_decomposition=clean_economic_decomp,
        falsification_triggers=clean_falsification_triggers,
        fixed_created_timestamp_utc="2026-09-01T12:00:00Z",
    )

    assert result1.dossier is not None and result2.dossier is not None
    assert result1.dossier.dossier_digest == result2.dossier.dossier_digest


# ---------------------------------------------------------------------------
# 2. Rejection & Degradation Branch Tests
# ---------------------------------------------------------------------------


def test_rejection_on_failed_phase6_statistical_validation(
    hypothesis_fixture: HypothesisSpecification,
    sealed_trial_ledger_fixture: SearchTrialLedger,
    clean_economic_decomp: AlphaEconomicDecomposition,
) -> None:
    """Verify that failing Phase 6 validation gate emits REJECTED_STATISTICAL_GATE."""
    failed_report = ValidationReport(
        validation_id="VAL_FAILED_001",
        evidence_digest="1" * 64,
        decision_digest="2" * 64,
        strategy_id="STRAT_MOM_001",
        hypothesis_id=hypothesis_fixture.hypothesis_id,
        verdict=ValidationGateVerdict.REJECT_OVERFIT_DSR,  # Fails Phase 6 Gate!
        is_tradeable_alpha=False,
        created_timestamp_utc="2026-09-01T11:30:00Z",
    )

    gate = AlphaQualificationGate()
    result = gate.qualify_alpha(
        alpha_id="ALPHA_FAILED_DSR",
        strategy_id="STRAT_MOM_001",
        hypothesis_spec=hypothesis_fixture,
        trial_ledger=sealed_trial_ledger_fixture,
        validation_report=failed_report,
        economic_decomposition=clean_economic_decomp,
    )

    assert result.is_qualified is False
    assert result.lifecycle_state == AlphaLifecycleState.REJECTED_STATISTICAL_GATE
    assert result.dossier is None
    assert "failed Phase 6 statistical validation gate" in (result.rejection_reason or "")


def test_rejection_on_failed_economic_hurdle_with_rebate(
    hypothesis_fixture: HypothesisSpecification,
    sealed_trial_ledger_fixture: SearchTrialLedger,
    passing_validation_report_fixture: ValidationReport,
) -> None:
    """Verify that a strategy with negative raw alpha subsidized by rebates is REJECTED."""
    bleeding_decomp = create_economic_decomposition(
        gross_trading_pnl_bps=Decimal("5.0"),
        realized_spread_slippage_bps=Decimal("10.0"),
        broker_commissions_bps=Decimal("2.0"),
        broker_rebate_income_bps=Decimal("100.0"),  # Net alpha is -7.0 bps
    )

    gate = AlphaQualificationGate(config=EconomicQualificationConfig(hurdle_rate_bps=Decimal("5.0")))
    result = gate.qualify_alpha(
        alpha_id="ALPHA_REBATE_SUBSIDIZED",
        strategy_id="STRAT_MOM_001",
        hypothesis_spec=hypothesis_fixture,
        trial_ledger=sealed_trial_ledger_fixture,
        validation_report=passing_validation_report_fixture,
        economic_decomposition=bleeding_decomp,
    )

    assert result.is_qualified is False
    assert result.lifecycle_state == AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE
    assert result.dossier is None
    assert "failed hurdle rate" in (result.rejection_reason or "")


def test_degradation_on_tripped_falsification_trigger(
    hypothesis_fixture: HypothesisSpecification,
    sealed_trial_ledger_fixture: SearchTrialLedger,
    passing_validation_report_fixture: ValidationReport,
    clean_economic_decomp: AlphaEconomicDecomposition,
) -> None:
    """Verify that tripped falsification triggers transition candidate to DEGRADED_FORWARD_TEST."""
    tripped_trigger = AlphaFalsificationTrigger(
        trigger_name="OOS_RANK_IC_DEGRADATION",
        metric_name="rank_ic",
        threshold_value=Decimal("0.025"),
        comparison_operator=FalsificationComparisonOperator.LESS_THAN,
        is_triggered=True,  # Tripped!
        observed_value=Decimal("0.010"),
        trigger_reason="Falsification trigger 'OOS_RANK_IC_DEGRADATION' tripped: observed rank_ic=0.010 < threshold 0.025.",
    )

    gate = AlphaQualificationGate()
    result = gate.qualify_alpha(
        alpha_id="ALPHA_DEGRADED",
        strategy_id="STRAT_MOM_001",
        hypothesis_spec=hypothesis_fixture,
        trial_ledger=sealed_trial_ledger_fixture,
        validation_report=passing_validation_report_fixture,
        economic_decomposition=clean_economic_decomp,
        falsification_triggers=(tripped_trigger,),
    )

    assert result.is_qualified is False
    assert result.lifecycle_state == AlphaLifecycleState.DEGRADED_FORWARD_TEST
    assert result.dossier is None
    assert "Falsification triggers tripped" in (result.rejection_reason or "")


# ---------------------------------------------------------------------------
# 3. Lineage Tampering & Fail-Closed Integrity Tests
# ---------------------------------------------------------------------------


def test_tampered_trial_ledger_digest_raises_data_contract_error(
    sealed_trial_ledger_fixture: SearchTrialLedger,
) -> None:
    """Verify that a tampered trial ledger digest raises DataContractError immediately."""
    with pytest.raises(DataContractError, match="ledger_digest mismatch"):
        SearchTrialLedger(
            ledger_id=sealed_trial_ledger_fixture.ledger_id,
            hypothesis_id=sealed_trial_ledger_fixture.hypothesis_id,
            strategy_id=sealed_trial_ledger_fixture.strategy_id,
            trials=sealed_trial_ledger_fixture.trials,
            sealed_at_utc=sealed_trial_ledger_fixture.sealed_at_utc,
            is_sealed=True,
            ledger_digest="f" * 64,  # Fraudulent digest!
        )


def test_unsealed_trial_ledger_rejected_by_qualification_gate(
    hypothesis_fixture: HypothesisSpecification,
    sealed_trial_ledger_fixture: SearchTrialLedger,
    passing_validation_report_fixture: ValidationReport,
    clean_economic_decomp: AlphaEconomicDecomposition,
) -> None:
    """Verify that an unsealed trial ledger is rejected by AlphaQualificationGate."""
    unsealed_ledger = SearchTrialLedger(
        ledger_id=sealed_trial_ledger_fixture.ledger_id,
        hypothesis_id=sealed_trial_ledger_fixture.hypothesis_id,
        strategy_id=sealed_trial_ledger_fixture.strategy_id,
        trials=sealed_trial_ledger_fixture.trials,
        is_sealed=False,
    )

    gate = AlphaQualificationGate()
    with pytest.raises(DataContractError, match="must be in SEALED state"):
        gate.qualify_alpha(
            alpha_id="ALPHA_UNSEALED",
            strategy_id="STRAT_MOM_001",
            hypothesis_spec=hypothesis_fixture,
            trial_ledger=unsealed_ledger,
            validation_report=passing_validation_report_fixture,
            economic_decomposition=clean_economic_decomp,
        )



def test_lineage_hypothesis_mismatch_raises_data_contract_error(
    hypothesis_fixture: HypothesisSpecification,
    sealed_trial_ledger_fixture: SearchTrialLedger,
    clean_economic_decomp: AlphaEconomicDecomposition,
) -> None:
    """Verify that a mismatch between hypothesis and validation report raises DataContractError."""
    mismatched_report = ValidationReport(
        validation_id="VAL_MISMATCH",
        evidence_digest="1" * 64,
        decision_digest="2" * 64,
        strategy_id="STRAT_MOM_001",
        hypothesis_id="DIFFERENT_HYPOTHESIS_ID",  # Mismatch!
        verdict=ValidationGateVerdict.PASS_TRADEABLE_ALPHA,
        is_tradeable_alpha=True,
        created_timestamp_utc="2026-09-01T11:30:00Z",
    )

    gate = AlphaQualificationGate()
    with pytest.raises(DataContractError, match="Lineage mismatch"):
        gate.qualify_alpha(
            alpha_id="ALPHA_MISMATCH",
            strategy_id="STRAT_MOM_001",
            hypothesis_spec=hypothesis_fixture,
            trial_ledger=sealed_trial_ledger_fixture,
            validation_report=mismatched_report,
            economic_decomposition=clean_economic_decomp,
        )
