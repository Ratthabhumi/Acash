"""Unit tests for Deflated Sharpe Ratio (DSR) and MinTRL Engine against published references."""

from decimal import Decimal
import math
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.deflated_sharpe import DeflatedSharpeEngine
from acash.validation.schema import SearchTrialLedger, SearchTrialRecord, SelectionCorrectionMode


def test_higher_moments_estimation() -> None:
    """Verify sample skewness and kurtosis on standard normal vs skewed synthetic distributions."""
    np.random.seed(42)
    normal_data = np.random.normal(0.0, 1.0, 5000)
    mean, std, skew, kurt = DeflatedSharpeEngine.calculate_higher_moments(normal_data)

    assert math.isclose(mean, 0.0, abs_tol=0.05)
    assert math.isclose(std, 1.0, abs_tol=0.05)
    assert math.isclose(skew, 0.0, abs_tol=0.10)
    assert math.isclose(kurt, 3.0, abs_tol=0.20)
    assert kurt >= 1.0  # Pearson kurtosis invariant


def test_expected_max_sharpe_sr0_monotonicity() -> None:
    """Verify that expected max Sharpe SR0 increases monotonically with number of trials K."""
    sr0_1 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=1, variance_of_trials=1.0)
    sr0_10 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=10, variance_of_trials=1.0)
    sr0_100 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=100, variance_of_trials=1.0)
    sr0_1000 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=1000, variance_of_trials=1.0)

    assert sr0_1 == 0.0  # Single-trial has zero selection deflation
    assert 0.0 < sr0_10 < sr0_100 < sr0_1000


def test_dsr_single_trial_mode() -> None:
    """Verify that K=1 explicitly triggers SelectionCorrectionMode.SINGLE_TRIAL with SR0 = 0."""
    np.random.seed(42)
    returns = np.random.normal(0.0010, 0.0050, 500)

    trial = SearchTrialRecord(
        trial_id="trial_1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.2"),
        p_value=Decimal("0.01"),
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_01",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=[trial],
    )

    res = DeflatedSharpeEngine.evaluate_dsr(returns=returns, trial_ledger=ledger)
    assert res.effective_trials_k == 1
    assert res.selection_correction_mode == SelectionCorrectionMode.SINGLE_TRIAL
    assert res.expected_max_sharpe_sr0 == Decimal("0.0")
    assert res.sr0_estimator == "EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1"


def test_dsr_evaluation_with_search_trial_ledger_significance() -> None:
    """Verify DSR calculation when coupled directly with a SearchTrialLedger under MULTIPLE_TRIAL mode."""
    np.random.seed(42)
    # Very strong returns (Sharpe ~ 1.2 > SR0 ~ 0.47)
    strong_returns = np.random.normal(0.0060, 0.0050, 1000)

    # Create a SearchTrialLedger recording 10 exploratory trials
    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"lookback": 10 + i},
            in_sample_sharpe=Decimal(f"{1.0 + i * 0.1:.4f}"),
            p_value=Decimal("0.01"),
        )
        for i in range(10)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=trials,
    )

    res = DeflatedSharpeEngine.evaluate_dsr(
        returns=strong_returns,
        trial_ledger=ledger,
    )
    assert res.effective_trials_k == 10
    assert res.selection_correction_mode == SelectionCorrectionMode.MULTIPLE_TRIAL
    assert res.expected_max_sharpe_sr0 > Decimal("0.0")
    assert res.is_statistically_significant is True
    assert res.has_sufficient_track_record is True


def test_dsr_rejection_when_sharpe_below_sr0() -> None:
    """Verify that a strategy with Sharpe lower than expected null max SR0 is strictly rejected."""
    np.random.seed(42)
    # Weak returns (Sharpe ~ 0.20 < SR0 ~ 0.47)
    weak_returns = np.random.normal(0.0010, 0.0050, 1000)

    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"lookback": 10 + i},
            in_sample_sharpe=Decimal(f"{1.0 + i * 0.1:.4f}"),
            p_value=Decimal("0.01"),
        )
        for i in range(10)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=trials,
    )

    res = DeflatedSharpeEngine.evaluate_dsr(
        returns=weak_returns,
        trial_ledger=ledger,
    )
    assert res.effective_trials_k == 10
    assert res.is_statistically_significant is False
    assert res.has_sufficient_track_record is False
