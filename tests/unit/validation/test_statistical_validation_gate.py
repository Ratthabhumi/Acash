"""Unit tests for the Statistical Validation Gate master orchestrator."""

from decimal import Decimal
import numpy as np
import pytest

from acash.validation.gate import StatisticalValidationGate
from acash.validation.schema import ValidationConfig, ValidationGateVerdict


def test_statistical_validation_gate_pass_tradeable_alpha() -> None:
    """Verify that a genuine robust strategy passing all gates receives PASS_TRADEABLE_ALPHA."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    # Strong persistent positive returns
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        effective_trials_k=5,
    )

    assert report.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA
    assert report.is_tradeable_alpha is True
    assert report.dsr_result.is_statistically_significant is True
    assert report.overfitting_report.is_pbo_acceptable is True
    assert report.oos_retention_pct is not None
    assert report.oos_retention_pct > Decimal("50.0")


def test_statistical_validation_gate_reject_overfit_dsr() -> None:
    """Verify that a noisy strategy with low Sharpe / high trial count is rejected with REJECT_OVERFIT_DSR."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    # Weak/zero edge returns
    noisy_returns = list(np.random.normal(0.0001, 0.0050, 1000))

    report = gate.evaluate_strategy(
        strategy_id="STRAT_NOISY_001",
        hypothesis_id="HYP_NOISE_001",
        in_sample_returns=noisy_returns,
        effective_trials_k=1000,  # High selection penalty
    )

    assert report.verdict == ValidationGateVerdict.REJECT_OVERFIT_DSR
    assert report.is_tradeable_alpha is False


def test_statistical_validation_gate_reject_oos_degradation() -> None:
    """Verify that a strategy with high in-sample performance but collapsing OOS is rejected with REJECT_OOS_DEGRADATION."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0030, 1000))  # High IS Sharpe ~ 10
    oos_returns = list(np.random.normal(-0.0005, 0.0050, 500))  # Negative OOS return

    report = gate.evaluate_strategy(
        strategy_id="STRAT_OVERFIT_001",
        hypothesis_id="HYP_OVERFIT_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        effective_trials_k=1,
    )

    assert report.verdict == ValidationGateVerdict.REJECT_OOS_DEGRADATION
    assert report.is_tradeable_alpha is False
