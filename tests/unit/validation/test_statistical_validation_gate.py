"""Unit tests for the Statistical Validation Gate master orchestrator."""

from decimal import Decimal
import json
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.gate import StatisticalValidationGate
from acash.validation.schema import (
    ParameterPerturbationGrid,
    SearchTrialLedger,
    SearchTrialRecord,
    ValidationConfig,
    ValidationGateVerdict,
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
    ledger = SearchTrialLedger(ledger_id="LEDGER_MOM_001", hypothesis_id="HYP_TSMOM_001", trials=trials)

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
    )

    assert report.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA
    assert report.is_tradeable_alpha is True
    assert report.dsr_result.effective_trials_k == 5
    assert len(report.multiple_testing_result.raw_p_values) == 5  # Strictly coupled K
    assert report.dsr_result.is_statistically_significant is True
    assert report.overfitting_report.is_pbo_acceptable is True
    assert report.oos_retention_pct is not None
    assert report.oos_retention_pct > Decimal("50.0")


def test_statistical_validation_gate_fail_closed_on_missing_oos() -> None:
    """Verify that missing or insufficient OOS returns strictly fail closed with REJECT_MISSING_OOS_DATA."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))

    # 1. None OOS returns
    report_none = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=None,
    )
    assert report_none.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA
    assert report_none.is_tradeable_alpha is False

    # 2. Too short OOS returns (< 4 bars)
    report_short = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=[0.01, 0.02],
    )
    assert report_short.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA
    assert report_short.is_tradeable_alpha is False


def test_deterministic_validation_report_id_and_digests() -> None:
    """Verify that identical strategy evaluation inputs produce bitwise-identical digests and validation_id."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    report_1 = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        fixed_created_timestamp_utc="2026-08-28T10:00:00Z",
    )

    report_2 = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        fixed_created_timestamp_utc="2026-08-28T12:00:00Z",  # Different runtime timestamp
    )

    # validation_id, evidence_digest, and decision_digest MUST be 100% identical
    assert report_1.evidence_digest == report_2.evidence_digest
    assert report_1.decision_digest == report_2.decision_digest
    assert report_1.validation_id == report_2.validation_id


def test_parameter_perturbation_grid_geometry_validation() -> None:
    """Verify that ParameterPerturbationGrid rejects non-conforming grids that violate +/- 25% invariants."""
    theta = Decimal("10.0")

    # Valid grid
    valid_grid = ParameterPerturbationGrid(
        base_parameter_name="lookback",
        base_parameter_value=theta,
        grid_values=[Decimal("7.5"), Decimal("10.0"), Decimal("12.5")],
        sharpe_profile=[Decimal("1.5"), Decimal("2.0"), Decimal("1.8")],
    )
    assert len(valid_grid.grid_values) == 3

    # Invalid left point (e.g. 5.0 instead of 7.5)
    with pytest.raises(DataContractError, match="Grid left point 5.0 does not equal 0.75"):
        ParameterPerturbationGrid(
            base_parameter_name="lookback",
            base_parameter_value=theta,
            grid_values=[Decimal("5.0"), Decimal("10.0"), Decimal("12.5")],
            sharpe_profile=[Decimal("1.5"), Decimal("2.0"), Decimal("1.8")],
        )


def test_canonical_json_serialization_completeness() -> None:
    """Verify that to_canonical_json() contains all fields without non-deterministic runtime timestamps."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    report = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
    )

    c_json = report.to_canonical_json()
    data = json.loads(c_json)

    assert "evidence_digest" in data
    assert "decision_digest" in data
    assert "created_timestamp_utc" not in data  # Non-canonical runtime timestamp excluded!
    assert "logits_distribution_mean" in data["overfitting_report"]
    assert "logits_distribution_std" in data["overfitting_report"]
    assert "trial_variance_used" in data["dsr_result"]
