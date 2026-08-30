"""Unit tests for HAC Newey-West variance, robust p-value inference, and DGP benchmark invariants."""

from decimal import Decimal
import math
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.benchmarks.dgp_experiments import (
    compute_wilson_confidence_interval,
    run_correlated_search_experiment,
    run_null_dgp_experiment,
    run_serial_dependence_experiment,
)
from acash.validation.deflated_sharpe import compute_hac_newey_west_variance, compute_hac_p_value
from acash.validation.schema import SearchTrialRecord


def test_wilson_confidence_interval_exactness() -> None:
    """Verify Wilson score confidence interval computation on zero and non-zero counts."""
    p0, l0, u0 = compute_wilson_confidence_interval(0, 100)
    assert p0 == 0.0
    assert l0 == 0.0
    assert 0.035 < u0 < 0.038  # ~3.7% rule of three bound

    p50, l50, u50 = compute_wilson_confidence_interval(50, 100)
    assert p50 == 0.5
    assert 0.40 < l50 < 0.41
    assert 0.59 < u50 < 0.60


def test_compute_hac_newey_west_variance_iid_vs_autocorrelated() -> None:
    """Verify that Newey-West HAC variance scales up under positive serial autocorrelation."""
    np.random.seed(42)
    T = 1000
    white_noise = np.random.normal(0.0, 1.0, T)
    var_iid = compute_hac_newey_west_variance(white_noise)
    assert 0.85 < var_iid < 1.15

    # AR(1) with phi = 0.50 -> theoretical long-run variance = sigma^2 / (1 - phi)^2 = 1.0 / 0.25 = 4.0
    ar_returns = np.zeros(T)
    for t in range(1, T):
        ar_returns[t] = 0.50 * ar_returns[t - 1] + white_noise[t]

    sample_var = float(np.var(ar_returns, ddof=1))  # ~ 1 / (1 - 0.25) = 1.33
    hac_var = compute_hac_newey_west_variance(ar_returns, max_lags=15)
    assert hac_var > sample_var * 2.0  # HAC variance properly captures positive persistence


def test_compute_hac_p_value_rejections() -> None:
    """Verify that compute_hac_p_value strictly fails closed on non-finite, small sample, and zero variance."""
    with pytest.raises(DataContractError, match="non-finite values"):
        compute_hac_p_value(np.array([1.0, np.nan, 2.0]))

    with pytest.raises(DataContractError, match="non-finite values"):
        compute_hac_p_value(np.array([1.0, np.inf, 2.0]))

    with pytest.raises(DataContractError, match="Cannot compute HAC p-value for sample size n=1 < 2"):
        compute_hac_p_value([0.01])

    with pytest.raises(DataContractError, match="Zero or near-zero variance"):
        compute_hac_p_value([0.01, 0.01, 0.01, 0.01])

    with pytest.raises(DataContractError, match="Invalid max_lags"):
        compute_hac_newey_west_variance([0.01, 0.02, 0.03], max_lags=-1)

    with pytest.raises(DataContractError, match="Invalid max_lags"):
        compute_hac_newey_west_variance([0.01, 0.02, 0.03], max_lags=5)


def test_canonical_p_value_fails_closed_on_zero_variance() -> None:
    """Verify that SearchTrialRecord.compute_canonical_p_value strictly fails closed on zero variance and n < 2."""
    with pytest.raises(DataContractError, match="Cannot compute canonical p-value for sample size n=1 < 2"):
        SearchTrialRecord.compute_canonical_p_value([0.01])

    with pytest.raises(DataContractError, match="Zero or near-zero sample variance"):
        SearchTrialRecord.compute_canonical_p_value([0.01, 0.01, 0.01, 0.01])



def test_search_trial_record_hac_p_value_derivation() -> None:
    """Verify that SearchTrialRecord correctly derives and validates HAC Newey-West p-values."""
    np.random.seed(42)
    returns = list(np.random.normal(0.002, 0.01, 100))
    expected_hac_p = compute_hac_p_value(returns)

    rec = SearchTrialRecord.create(
        trial_id="trial_hac_01",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["mom"],
        parameters={"window": 20},
        in_sample_sharpe=Decimal("1.500000"),
        p_value_method="HAC_NEWEY_WEST_ZERO_SHARPE_TEST_V1",
        execution_manifest_id="MAN_01",
        in_sample_returns=returns,
    )
    assert rec.p_value_method == "HAC_NEWEY_WEST_ZERO_SHARPE_TEST_V1"
    assert rec.p_value == expected_hac_p


def test_dgp_experiment_a_null_rejection_invariant() -> None:
    """Invariant test: Experiment A under small fast seed confirms 0% false positives on pure noise."""
    res = run_null_dgp_experiment(num_simulations=10, T=300, M=6, random_seed=999)
    assert res["pass_count"] == 0
    assert res["observed_false_positive_rate"] == 0.0
    assert res["wilson_95_ci"][1] < 0.35
