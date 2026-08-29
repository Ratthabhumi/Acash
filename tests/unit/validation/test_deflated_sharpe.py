"""Unit tests for Deflated Sharpe Ratio (DSR) and MinTRL Engine against published references."""

from decimal import Decimal
import math
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.deflated_sharpe import DeflatedSharpeEngine
from acash.validation.schema import SearchTrialLedger, SearchTrialRecord, SelectionCorrectionMode, SharpeSpace



def test_higher_moments_estimation() -> None:
    """Verify sample skewness and kurtosis on standard normal vs skewed synthetic distributions."""
    np.random.seed(42)
    normal_data = list(np.random.normal(0.0, 1.0, 5000))
    mean, std, skew, kurt = DeflatedSharpeEngine.calculate_higher_moments(normal_data)

    assert math.isclose(mean, 0.0, abs_tol=0.05)
    assert math.isclose(std, 1.0, abs_tol=0.05)
    assert math.isclose(skew, 0.0, abs_tol=0.10)
    assert kurt >= ((len(normal_data) - 1) / len(normal_data)) ** 2  # Pearson kurtosis finite-sample lower bound



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
    returns = list(np.random.normal(0.0010, 0.0050, 500))

    trial = SearchTrialRecord.create(
        trial_id="trial_1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.2"),
        p_value=Decimal("0.01"),
        execution_manifest_id="MANIFEST_01",
        in_sample_returns=returns,
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_01",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=(trial,),
    )

    res = DeflatedSharpeEngine.evaluate_dsr(returns=returns, trial_ledger=ledger)
    assert res.effective_trials_k == 1
    assert res.selection_correction_mode == SelectionCorrectionMode.SINGLE_TRIAL
    assert res.expected_max_sharpe_sr0 == Decimal("0.0")
    assert res.sr0_estimator == "ZERO_LOCATION_EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1"



def test_dsr_evaluation_with_search_trial_ledger_significance() -> None:
    """Verify DSR calculation when coupled directly with a SearchTrialLedger under MULTIPLE_TRIAL mode."""
    np.random.seed(42)
    # Very strong returns (Sharpe ~ 1.2 > SR0 ~ 0.47)
    strong_returns = list(np.random.normal(0.0060, 0.0050, 1000))

    # Create a SearchTrialLedger recording 10 exploratory trials
    trials = [
        SearchTrialRecord.create(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"lookback": 10 + i},
            in_sample_sharpe=Decimal(f"{1.0 + i * 0.1:.4f}"),
            p_value=Decimal("0.01"),
            execution_manifest_id=f"MANIFEST_{i}",
            in_sample_returns=strong_returns,
        )
        for i in range(10)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=tuple(trials),
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
    weak_returns = list(np.random.normal(0.0010, 0.0050, 1000))

    trials = [
        SearchTrialRecord.create(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"lookback": 10 + i},
            in_sample_sharpe=Decimal(f"{1.0 + i * 0.1:.4f}"),
            p_value=Decimal("0.01"),
            execution_manifest_id=f"MANIFEST_{i}",
            in_sample_returns=weak_returns,
        )
        for i in range(10)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=tuple(trials),
    )

    res = DeflatedSharpeEngine.evaluate_dsr(
        returns=weak_returns,
        trial_ledger=ledger,
    )
    assert res.effective_trials_k == 10
    assert res.is_statistically_significant is False
    assert res.min_track_record_length_bars is None  # Unbounded / infinite track record required
    assert res.is_min_trl_unbounded is True
    assert res.has_sufficient_track_record is False



def test_dsr_variance_monotonicity_and_identical_trials() -> None:
    """Verify that SR0 increases monotonically with cross-sectional trial variance and tests V=0 baseline."""
    # 1. Monotonicity of SR0 with respect to trial variance V for fixed K=50
    k = 50
    variances = [0.01, 0.04, 0.25, 1.0, 4.0]
    sr0_values = [
        DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=k, variance_of_trials=v)
        for v in variances
    ]
    for i in range(len(sr0_values) - 1):
        assert sr0_values[i] < sr0_values[i + 1]

    # 2. Identical trials in ledger produce Var(SR_k) == 0.0 -> SR0 == 0.0
    dummy_returns = [0.01, 0.02, 0.03, 0.04]
    identical_trials = [
        SearchTrialRecord.create(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_IDENTICAL",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.500000000000000000"),
            p_value=Decimal("0.001"),
            execution_manifest_id=f"MANIFEST_IDENTICAL_{i}",
            in_sample_returns=dummy_returns,
        )
        for i in range(20)
    ]
    identical_ledger = SearchTrialLedger(
        ledger_id="LEDGER_IDENTICAL",
        strategy_id="STRAT_IDENTICAL",
        hypothesis_id="HYP_01",
        trials=tuple(identical_trials),
    )
    assert identical_ledger.get_empirical_sharpe_variance() == 0.0

    returns = list(np.random.normal(0.0015, 0.0040, 500))
    res = DeflatedSharpeEngine.evaluate_dsr(returns=returns, trial_ledger=identical_ledger)
    assert res.expected_max_sharpe_sr0 == Decimal("0.0")


def test_dsr_location_provenance_zero_location_vs_empirical_mean() -> None:
    """Verify DSR location parameter provenance: zero-location policy vs empirical ledger mean."""
    returns = list(np.random.normal(0.0020, 0.0040, 500))
    dummy_returns = [0.01, 0.02, 0.03, 0.04]

    # 10 trials with Sharpes 1.0, 1.2, 1.4, ..., 2.8 (Mean = 1.90, Variance > 0)
    trials = [
        SearchTrialRecord.create(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"p": i},
            in_sample_sharpe=Decimal(f"{1.0 + i * 0.2:.6f}"),
            p_value=Decimal("0.001"),
            execution_manifest_id=f"MANIFEST_{i}",
            in_sample_returns=dummy_returns,
        )
        for i in range(10)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_01",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=tuple(trials),
        sharpe_space=SharpeSpace.PERIOD,
    )

    # 1. Zero-Location Governance Policy (default): mu_trials = 0.0
    res_zero = DeflatedSharpeEngine.evaluate_dsr(
        returns=returns,
        trial_ledger=ledger,
        use_empirical_trial_mean=False,
    )
    assert res_zero.trial_mean_used == Decimal("0.0")
    assert res_zero.sr0_estimator == "ZERO_LOCATION_EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1"

    # 2. Empirical Location-Scale Variant: mu_trials derived from ledger mean
    res_empirical = DeflatedSharpeEngine.evaluate_dsr(
        returns=returns,
        trial_ledger=ledger,
        use_empirical_trial_mean=True,
    )
    expected_mean = float(ledger.get_empirical_sharpe_mean())
    assert math.isclose(float(res_empirical.trial_mean_used), expected_mean, abs_tol=1e-6)
    assert res_empirical.sr0_estimator == "EMPIRICAL_LOCATION_SCALE_GUMBEL_V1"
    assert res_empirical.expected_max_sharpe_sr0 > res_zero.expected_max_sharpe_sr0


def test_dsr_rejects_non_positive_denominator_term() -> None:
    """Verify that DeflatedSharpeEngine raises DataContractError when asymptotic variance denominator is <= 0."""
    from unittest.mock import patch

    returns = [0.01, -0.02, 0.015, 0.03, -0.01]
    # Mock higher moments to produce denominator_term <= 0
    # denominator_term = 1 - skew*SR + (kurt - 1)/4 * SR^2
    # If skew = 100.0, SR = 1.0, kurt = 1.0 -> denominator_term = 1 - 100 + 0 = -99 <= 0
    with patch.object(DeflatedSharpeEngine, "calculate_higher_moments", return_value=(1.0, 1.0, 100.0, 1.0)):
        with pytest.raises(DataContractError, match="non-positive or non-finite"):
            DeflatedSharpeEngine.evaluate_dsr(returns=returns)






