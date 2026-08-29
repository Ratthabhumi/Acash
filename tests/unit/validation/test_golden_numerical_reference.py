"""Golden numerical reference test suite comparing ACASH implementations against independent mathematical derivations.

References:
1. Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality."
   Journal of Portfolio Management, 40(5), 94–107.
2. Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2016). "The Probability of Backtest Overfitting."
   Journal of Computational Finance, 20(4), 39–69.
3. Harvey, C. R., Liu, Y., & Zhu, H. (2016). "... and the Cross-Section of Expected Returns."
   Review of Financial Studies, 29(1), 5–68.
"""

from decimal import Decimal
import math
import numpy as np
import pytest
from scipy.stats import norm  # type: ignore[import-untyped]

from acash.core.domain.exceptions import DataContractError
from acash.validation.cpcv import CombinatorialPurgedCrossValidation
from acash.validation.deflated_sharpe import DeflatedSharpeEngine
from acash.validation.multiple_testing import MultipleTestingEngine
from acash.validation.overfitting import OverfittingEngine
from acash.validation.schema import SharpeSpace, ValidationConfig


# ======================================================================================
# INDEPENDENT MATHEMATICAL REFERENCE DERIVATIONS (Zero ACASH Internal Dependencies)
# ======================================================================================

def _independent_higher_moments(returns: list[float]) -> tuple[float, float, float, float]:
    """Compute sample mean, standard deviation (ddof=1), Fisher-Pearson G_1, and Pearson g_2."""
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((x - mean) ** 2 for x in returns) / (n - 1)
    std = math.sqrt(variance)

    # Standardized deviations
    z = [(x - mean) / std for x in returns]
    # Unbiased Fisher-Pearson sample skewness G_1
    skew = (n / ((n - 1) * (n - 2))) * sum(zi ** 3 for zi in z)
    # Pearson standardized fourth moment kurtosis g_2
    kurt = sum(zi ** 4 for zi in z) / n
    return mean, std, skew, kurt


def _independent_evt_gumbel_sr0(k_trials: int, variance: float) -> float:
    """Compute expected max Sharpe SR_0 via independent EVT Gumbel closed form."""
    if k_trials <= 1 or variance <= 1e-12:
        return 0.0
    gamma_e = 0.57721566490153286060651209
    p1 = 1.0 - (1.0 / k_trials)
    p2 = 1.0 - (1.0 / (k_trials * math.e))
    z1 = float(norm.ppf(p1))
    z2 = float(norm.ppf(p2))
    return float(math.sqrt(variance) * ((1.0 - gamma_e) * z1 + gamma_e * z2))


def _independent_dsr_z_stat(
    mean: float,
    std: float,
    skew: float,
    kurt: float,
    sr0_period: float,
    t_obs: int,
) -> float:
    """Compute asymptotic DSR z-statistic in period space."""
    sr_hat = mean / std
    d_term = 1.0 - (skew * sr_hat) + (((kurt - 1.0) / 4.0) * (sr_hat ** 2))
    return float((sr_hat - sr0_period) * math.sqrt(t_obs - 1) / math.sqrt(d_term))


def _independent_min_trl(
    mean: float,
    std: float,
    skew: float,
    kurt: float,
    sr0_period: float,
    alpha: float,
) -> int:
    """Compute Minimum Track Record Length (MinTRL) in bars."""
    sr_hat = mean / std
    if (sr_hat - sr0_period) <= 1e-12:
        return int(1e9)
    d_term = 1.0 - (skew * sr_hat) + (((kurt - 1.0) / 4.0) * (sr_hat ** 2))
    z_alpha = float(norm.ppf(1.0 - alpha))
    return int(math.ceil(1.0 + d_term * ((z_alpha / (sr_hat - sr0_period)) ** 2)))


def _independent_bonferroni_haircut_sharpe(sr: float, k_trials: int, t_obs: int, raw_p: float | None = None) -> float:
    """Compute Bonferroni Haircut Sharpe Ratio via closed-form inverse normal mapping."""
    if k_trials <= 1 or sr <= 1e-12:
        return sr
    t_raw = sr * math.sqrt(t_obs)
    p_raw = raw_p if raw_p is not None else float(math.erfc(t_raw / math.sqrt(2.0)))
    p_adj = min(1.0, p_raw * k_trials)
    if p_adj >= 1.0 - 1e-15:
        return 0.0
    t_adj = float(norm.ppf(1.0 - (p_adj / 2.0)))
    return float(max(0.0, t_adj / math.sqrt(t_obs)))


# ======================================================================================
# GOLDEN TESTS
# ======================================================================================

def test_golden_reference_higher_moments_and_dsr_analytical_precision() -> None:
    """Compare ACASH higher moments and DSR calculations against independent closed-form reference implementations."""
    # Deterministic test return sequence of length T = 10
    returns = [0.010, -0.020, 0.015, 0.030, -0.010, 0.005, 0.025, -0.015, 0.020, 0.005]
    T = len(returns)
    K = 100
    V_period = 0.0004
    P = 252.0
    alpha = 0.05

    # 1. Independent Reference Calculations
    ref_mean, ref_std, ref_skew, ref_kurt = _independent_higher_moments(returns)
    ref_sr_period = ref_mean / ref_std
    ref_sr_annual = ref_sr_period * math.sqrt(P)
    ref_sr0_period = _independent_evt_gumbel_sr0(K, V_period)
    ref_sr0_annual = ref_sr0_period * math.sqrt(P)
    ref_z = _independent_dsr_z_stat(ref_mean, ref_std, ref_skew, ref_kurt, ref_sr0_period, T)
    ref_prob = float(norm.cdf(ref_z))
    ref_trl = _independent_min_trl(ref_mean, ref_std, ref_skew, ref_kurt, ref_sr0_period, alpha)

    # 2. ACASH Evaluation
    acash_mean, acash_std, acash_skew, acash_kurt = DeflatedSharpeEngine.calculate_higher_moments(returns)
    acash_sr0_period = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=K, variance_of_trials=V_period)
    dsr_result = DeflatedSharpeEngine.evaluate_dsr(
        returns=returns,
        effective_trials_k=K,
        variance_of_trials=V_period,
        confidence_level_alpha=alpha,
        periods_per_year=P,
    )

    # 3. Exact Precision Assertions
    assert math.isclose(acash_mean, ref_mean, abs_tol=1e-12)
    assert math.isclose(acash_std, ref_std, abs_tol=1e-12)
    assert math.isclose(acash_skew, ref_skew, abs_tol=1e-12)
    assert math.isclose(acash_kurt, ref_kurt, abs_tol=1e-12)
    assert math.isclose(acash_sr0_period, ref_sr0_period, abs_tol=1e-10)

    # Full DSRResult verification
    assert math.isclose(float(dsr_result.estimated_sharpe), ref_sr_annual, abs_tol=1e-6)
    assert math.isclose(float(dsr_result.expected_max_sharpe_sr0), ref_sr0_annual, abs_tol=1e-6)
    assert math.isclose(float(dsr_result.dsr_statistic), ref_z, abs_tol=1e-6)
    assert math.isclose(float(dsr_result.dsr_p_value), ref_prob, abs_tol=1e-6)
    assert dsr_result.min_track_record_length_bars == ref_trl
    assert dsr_result.sample_size_t == T
    assert math.isclose(float(dsr_result.trial_variance_used), V_period, abs_tol=1e-12)
    assert dsr_result.sharpe_space == SharpeSpace.ANNUAL
    assert dsr_result.inference_space == SharpeSpace.PERIOD

    # Independence Semantics Assertions (Strict Contract)
    assert dsr_result.declared_trials_k == K
    assert dsr_result.effective_independent_trials_k is None  # Must remain None unless explicitly estimated!
    assert dsr_result.independence_assumption == "CONSERVATIVE_DECLARED_SEARCH_OPPORTUNITIES_UPPER_BOUND"


def test_golden_reference_zero_variance_and_threshold_guards() -> None:
    """Verify that constant returns raise DataContractError and V <= 1e-12 collapses SR0 to 0.0."""
    # 1. Constant return series -> standard deviation = 0 -> mathematically undefined
    constant_returns = [0.01, 0.01, 0.01, 0.01, 0.01]
    with pytest.raises(DataContractError, match="zero or near-zero variance"):
        DeflatedSharpeEngine.calculate_higher_moments(constant_returns)

    # 2. Trial variance V <= 1e-12 numerical policy
    sr0_tiny_v = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=100, variance_of_trials=1e-13)
    assert sr0_tiny_v == 0.0

    sr0_k1 = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(effective_trials_k=1, variance_of_trials=0.04)
    assert sr0_k1 == 0.0


def test_golden_reference_cscv_pbo_exact_toy_case() -> None:
    """Verify CSCV combinatorial structure and exact PBO against hand-calculated reference.

    Toy Case:
    N = 6 blocks, k = 3 test blocks (balanced half/half split).
    C = (6 choose 3) = 20 splits.
    phi = (3 / 6) * 20 = 10 pseudo-OOS paths.
    Total testing slices = C * k = 20 * 3 = 60.
    Total slices across paths = phi * N = 10 * 6 = 60.
    """
    N = 6
    k = 3
    T = 60
    config = ValidationConfig(num_groups_n=N, num_test_groups_k=k)
    cpcv = CombinatorialPurgedCrossValidation(config)

    partitions = cpcv.generate_partitions(sample_size=T, label_horizon=1, enforce_cscv_balanced=True)
    assert len(partitions) == 20  # C = 20

    # Verify each group g in {0, ..., 5} appears in exactly (5 choose 2) = 10 splits
    group_appearance_counts = {g: 0 for g in range(N)}
    for p in partitions:
        assert len(p.test_group_indices) == 3
        for g in p.test_group_indices:
            group_appearance_counts[g] += 1

    for g in range(N):
        assert group_appearance_counts[g] == 10  # phi = 10

    # Path reconstruction
    paths = cpcv.reconstruct_pseudo_oos_paths(partitions, sample_size=T)
    assert len(paths) == 10  # phi = 10

    # Verify each path covers exactly [0, T) = [0, 60) without overlap or gaps
    expected_full_series = list(range(T))
    for path in paths:
        assert len(path) == T
        assert [sample_idx for _, sample_idx in path] == expected_full_series

    # 2. Hand-Calculated PBO Evaluation over known (C=4, M=3) Sharpe Matrix
    # Setup exact IS and OOS matrices for 4 splits and 3 candidate models:
    # Split 0: IS=[1.0, 0.5, 0.2] (winner m*=0), OOS=[0.1, 0.8, 0.9] -> OOS[m*]=0.1 (Rank 1/3, omega=1/4=0.25, logit=ln(0.25/0.75)=-1.098612, Overfit)
    # Split 1: IS=[0.2, 1.0, 0.5] (winner m*=1), OOS=[0.1, 0.5, 0.9] -> OOS[m*]=0.5 (Rank 2/3, omega=2/4=0.50, logit=ln(0.5/0.5)=0.0, Not Overfit)
    # Split 2: IS=[0.1, 0.2, 1.0] (winner m*=2), OOS=[0.1, 0.5, 0.9] -> OOS[m*]=0.9 (Rank 3/3, omega=3/4=0.75, logit=ln(0.75/0.25)=+1.098612, Not Overfit)
    # Split 3: IS=[1.0, 0.2, 0.1] (winner m*=0), OOS=[0.1, 0.5, 0.9] -> OOS[m*]=0.1 (Rank 1/3, omega=1/4=0.25, logit=ln(0.25/0.75)=-1.098612, Overfit)
    is_mat = np.array([
        [1.0, 0.5, 0.2],
        [0.2, 1.0, 0.5],
        [0.1, 0.2, 1.0],
        [1.0, 0.2, 0.1],
    ], dtype=np.float64)

    oos_mat = np.array([
        [0.1, 0.8, 0.9],
        [0.1, 0.5, 0.9],
        [0.1, 0.5, 0.9],
        [0.1, 0.5, 0.9],
    ], dtype=np.float64)

    # Reference Hand-Calculations:
    # Overfit splits = {0, 3} -> count = 2 out of C=4 -> PBO = 2 / 4 = 0.50
    # Logits: [-1.09861228867, 0.0, 1.09861228867, -1.09861228867]
    ref_logits = np.array([-math.log(3.0), 0.0, math.log(3.0), -math.log(3.0)], dtype=np.float64)
    ref_logits_mean = float(np.mean(ref_logits))
    ref_logits_std = float(np.std(ref_logits, ddof=0))  # population std (ddof=0)
    ref_pbo = 2.0 / 4.0  # 0.50

    acash_pbo, acash_logits_mean, acash_logits_std = OverfittingEngine.calculate_pbo(is_mat, oos_mat)

    assert math.isclose(acash_pbo, ref_pbo, abs_tol=1e-12)
    assert math.isclose(acash_logits_mean, ref_logits_mean, abs_tol=1e-6)
    assert math.isclose(acash_logits_std, ref_logits_std, abs_tol=1e-6)


def test_golden_reference_bonferroni_haircut_sharpe() -> None:
    """Verify ACASH Multiple-Testing Bonferroni Haircut Sharpe against independent derivation."""
    # Scenario: estimated_sharpe = 0.30, sample_size_t = 100, effective_trials_k = 10
    SR = 0.30
    T = 100
    K = 10

    ref_haircut = _independent_bonferroni_haircut_sharpe(SR, K, T)

    acash_haircut_primary = MultipleTestingEngine.calculate_bonferroni_haircut_sharpe(
        estimated_sharpe=SR,
        effective_trials_k=K,
        sample_size_t=T,
    )
    acash_haircut_alias = MultipleTestingEngine.calculate_haircut_sharpe(
        estimated_sharpe=SR,
        effective_trials_k=K,
        sample_size_t=T,
    )

    assert math.isclose(float(acash_haircut_primary), ref_haircut, abs_tol=1e-6)
    assert math.isclose(float(acash_haircut_alias), ref_haircut, abs_tol=1e-6)

