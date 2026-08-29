"""Unit tests for the Statistical Validation Gate master orchestrator."""

from decimal import Decimal
import hashlib
import json
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.gate import StatisticalValidationGate
from acash.validation.schema import (
    ParameterPerturbationGrid,
    ParameterPerturbationPoint,
    SearchTrialLedger,
    SearchTrialRecord,
    SelectionCorrectionMode,
    ValidationConfig,
    ValidationGateVerdict,
)


def _make_valid_perturbation_grid(
    base_val: Decimal = Decimal("10.0"),
    sr: Decimal = Decimal("1.5"),
    strat_id: str = "STRAT_01",
) -> ParameterPerturbationGrid:
    """Helper to construct a valid 3-point perturbation grid with distinct execution runs."""
    base_hash = hashlib.sha256(f"{strat_id}:test_grid:{base_val}".encode("utf-8")).hexdigest()
    points = [
        ParameterPerturbationPoint(
            parameter_value=base_val * Decimal("0.75"),
            run_id=f"run_{strat_id}_left_p75",
            input_artifact_hash=hashlib.sha256(f"{base_hash}:left:in".encode("utf-8")).hexdigest(),
            output_artifact_hash=hashlib.sha256(f"{base_hash}:left:out".encode("utf-8")).hexdigest(),
            actual_sharpe=sr,
        ),
        ParameterPerturbationPoint(
            parameter_value=base_val,
            run_id=f"run_{strat_id}_base_100",
            input_artifact_hash=hashlib.sha256(f"{base_hash}:base:in".encode("utf-8")).hexdigest(),
            output_artifact_hash=hashlib.sha256(f"{base_hash}:base:out".encode("utf-8")).hexdigest(),
            actual_sharpe=sr,
        ),
        ParameterPerturbationPoint(
            parameter_value=base_val * Decimal("1.25"),
            run_id=f"run_{strat_id}_right_p125",
            input_artifact_hash=hashlib.sha256(f"{base_hash}:right:in".encode("utf-8")).hexdigest(),
            output_artifact_hash=hashlib.sha256(f"{base_hash}:right:out".encode("utf-8")).hexdigest(),
            actual_sharpe=sr,
        ),
    ]
    return ParameterPerturbationGrid(
        base_parameter_name="lookback",
        base_parameter_value=base_val,
        points=points,
    )


def test_statistical_validation_gate_pass_tradeable_alpha() -> None:
    """Verify that a genuine robust strategy passing all gates receives PASS_TRADEABLE_ALPHA."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    # Strong persistent positive returns
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_MOM_001",
            hypothesis_id="HYP_TSMOM_001",
            feature_names=["mom"],
            parameters={"period": 10 + i},
            in_sample_sharpe=Decimal(f"{1.2 + i * 0.05:.4f}"),
            p_value=Decimal("0.001"),
        )
        for i in range(5)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_MOM_001",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_MOM_001")

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        perturbation_grid=grid,
    )

    assert report.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA
    assert report.is_tradeable_alpha is True
    assert report.dsr_result.effective_trials_k == 5
    assert report.dsr_result.selection_correction_mode == SelectionCorrectionMode.MULTIPLE_TRIAL
    assert report.dsr_result.sr0_estimator == "EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1"
    assert len(report.multiple_testing_result.raw_p_values) == 5  # Strictly coupled K
    assert report.dsr_result.is_statistically_significant is True
    assert report.overfitting_report.is_pbo_acceptable is True
    assert report.overfitting_report.analytical_friction_monotonicity_passed is True
    assert report.oos_retention_pct is not None
    assert report.oos_retention_pct > Decimal("50.0")


def test_statistical_validation_gate_fail_closed_on_missing_ledger() -> None:
    """Verify that omitting trial_ledger strictly fails closed with REJECT_MISSING_TRIAL_LEDGER."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=None,
    )

    assert report.verdict == ValidationGateVerdict.REJECT_MISSING_TRIAL_LEDGER
    assert report.is_tradeable_alpha is False


def test_statistical_validation_gate_fail_closed_on_missing_oos() -> None:
    """Verify that missing or insufficient OOS returns strictly fail closed with REJECT_MISSING_OOS_DATA."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))

    trial = SearchTrialRecord(
        trial_id="trial_1",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        feature_names=["mom"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        trials=[trial],
    )

    # 1. None OOS returns
    report_none = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=None,
        trial_ledger=ledger,
    )
    assert report_none.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA
    assert report_none.is_tradeable_alpha is False

    # 2. Too short OOS returns (< 4 bars)
    report_short = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=[0.01, 0.02],
        trial_ledger=ledger,
    )
    assert report_short.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA
    assert report_short.is_tradeable_alpha is False


def test_ledger_duplicate_trial_id_rejection() -> None:
    """Verify that SearchTrialLedger strictly rejects duplicate trial IDs."""
    record_1 = SearchTrialRecord(
        trial_id="duplicate_id",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
    )
    record_2 = SearchTrialRecord(
        trial_id="duplicate_id",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f2"],
        parameters={},
        in_sample_sharpe=Decimal("1.2"),
        p_value=Decimal("0.03"),
    )

    with pytest.raises(DataContractError, match="duplicate trial_ids"):
        SearchTrialLedger(
            ledger_id="LEDGER_01",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            trials=[record_1, record_2],
        )


def test_parameter_perturbation_grid_duplicate_run_id_rejection() -> None:
    """Verify that ParameterPerturbationGrid strictly rejects non-distinct run_ids."""
    theta = Decimal("10.0")
    dummy_hash = "a" * 32

    points_dup = [
        ParameterPerturbationPoint(
            parameter_value=Decimal("7.5"),
            run_id="same_run_id",
            input_artifact_hash=dummy_hash,
            output_artifact_hash=dummy_hash,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("10.0"),
            run_id="same_run_id",
            input_artifact_hash=dummy_hash,
            output_artifact_hash=dummy_hash,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("12.5"),
            run_id="different_run_id",
            input_artifact_hash=dummy_hash,
            output_artifact_hash=dummy_hash,
            actual_sharpe=Decimal("1.5"),
        ),
    ]

    with pytest.raises(DataContractError, match="3 distinct execution run_ids"):
        ParameterPerturbationGrid(
            base_parameter_name="lookback",
            base_parameter_value=theta,
            points=points_dup,
        )


def test_deterministic_validation_report_id_and_digests() -> None:
    """Verify that identical strategy evaluation inputs produce bitwise-identical digests and validation_id."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    trial = SearchTrialRecord(
        trial_id="trial_single",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_01",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=[trial],
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01")

    report_1 = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        perturbation_grid=grid,
        fixed_created_timestamp_utc="2026-08-28T10:00:00Z",
    )

    report_2 = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        perturbation_grid=grid,
        fixed_created_timestamp_utc="2026-08-28T12:00:00Z",  # Different runtime timestamp
    )

    # validation_id, evidence_digest, and decision_digest MUST be 100% identical
    assert report_1.evidence_digest == report_2.evidence_digest
    assert report_1.decision_digest == report_2.decision_digest
    assert report_1.validation_id == report_2.validation_id


def test_canonical_json_serialization_separation() -> None:
    """Verify clean separation between to_canonical_evidence_json() and to_canonical_report_json()."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    trial = SearchTrialRecord(
        trial_id="trial_single",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_01",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=[trial],
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01")

    report = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        perturbation_grid=grid,
    )

    # 1. Canonical Evidence JSON (pure mathematical facts)
    ev_json = report.to_canonical_evidence_json()
    ev_data = json.loads(ev_json)
    assert "evidence_digest" in ev_data
    assert "decision_digest" not in ev_data  # No governance verdict/decision in evidence!
    assert "verdict" not in ev_data
    assert "created_timestamp_utc" not in ev_data

    # 2. Canonical Report JSON (sealed governance record)
    rep_json = report.to_canonical_report_json()
    rep_data = json.loads(rep_json)
    assert "decision_digest" in rep_data
    assert "evidence_digest" in rep_data
    assert "verdict" in rep_data
    assert "created_timestamp_utc" not in rep_data
