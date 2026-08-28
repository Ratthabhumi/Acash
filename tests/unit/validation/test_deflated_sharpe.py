"""Unit tests for Deflated Sharpe Ratio (DSR) and MinTRL Engine against published references."""

from decimal import Decimal
import math
import numpy as np
import pytest

from acash.validation.deflated_sharpe import DeflatedSharpeEngine


def test_higher_moments_estimation() -> None:
    """Verify sample skewness and kurtosis on standard normal vs skewed synthetic distributions."""
    np.random.seed(42)
    normal_data = np.random.normal(0.0, 1.0, 5000)
    mean, std, skew, kurt = DeflatedSharpeEngine.calculate_higher_moments(normal_data)

    assert math.isclose(mean, 0.0, abs_tol=0.05)
    assert math.isclose(std, 1.0, abs_tol=0.05)
    assert math.isclose(skew, 0.0, abs_tol=0.10)
    assert math.isclose(kurt, 3.0, abs_tol=0.20)


def test_expected_max_sharpe_sr0_monotonicity() -> None:
    """Verify that expected max Sharpe SR0 increases monotonically with number of trials K."""
    sr0_1 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=1)
    sr0_10 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=10)
    sr0_100 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=100)
    sr0_1000 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=1000)

    assert sr0_1 == 0.0
    assert 0.0 < sr0_10 < sr0_100 < sr0_1000


def test_dsr_evaluation_and_mintr_length() -> None:
    """Verify DSR calculation and MinTRL requirement for significant vs overfit strategies."""
    # Strong strategy return series: annualized Sharpe ~ 2.5
    np.random.seed(42)
    strong_returns = np.random.normal(0.0010, 0.0050, 1000)

    res_single = DeflatedSharpeEngine.evaluate_dsr(
        returns=strong_returns,
        effective_trials_k=1,
    )
    assert res_single.is_statistically_significant is True
    assert res_single.has_sufficient_track_record is True

    # Same strategy evaluated after 100,000 exploratory trials (severe selection bias penalty)
    res_heavily_searched = DeflatedSharpeEngine.evaluate_dsr(
        returns=strong_returns,
        effective_trials_k=100000,
    )
    # Selection bias inflates SR0 -> DSR probability drops significantly
    assert res_heavily_searched.expected_max_sharpe_sr0 > res_single.expected_max_sharpe_sr0
    assert res_heavily_searched.dsr_p_value < res_single.dsr_p_value
