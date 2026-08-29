"""Golden numerical reference test suite comparing ACASH implementations against independent mathematical derivations.

References:
1. Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality."
   Journal of Portfolio Management, 40(5), 94–107.
2. Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2016). "The Probability of Backtest Overfitting."
   Journal of Computational Finance, 20(4), 39–69.
3. Harvey, C. R., Liu, Y., & Zhu, H. (2016). "... and the Cross-Section of Expected Returns."
   Review of Financial Studies, 29(1), 5–68.
"""

import math
import numpy as np
import pytest
from scipy.stats import norm  # type: ignore[import-untyped]

from acash.validation.cpcv import CombinatorialPurgedCrossValidation
from acash.validation.deflated_sharpe import DeflatedSharpeEngine
from acash.validation.multiple_testing import MultipleTestingEngine
from acash.validation.overfitting import OverfittingEngine
from acash.validation.schema import ValidationConfig


def test_golden_reference_higher_moments_and_dsr_analytical_precision() -> None:
    """Compare ACASH higher moments and DSR calculations against independent analytical reference derivations."""
    # Deterministic test return sequence of length T = 10
    returns = [0.010, -0.020, 0.015, 0.030, -0.010, 0.005, 0.025, -0.015, 0.020, 0.005]
    T = len(returns)

    # 1. Independent Analytical Higher Moments
    r_arr = np.array(returns, dtype=np.float64)
    ref_mean = float(np.mean(r_arr))
    # Sample standard deviation (ddof=1)
    ref_std = float(np.std(r_arr, ddof=1))

    # Analytical Fisher-Pearson sample skewness G_1 (bias=False):
    # G_1 = (n / ((n - 1) * (n - 2))) * sum( ((x_i - mean) / std)^3 )
    norm_diff = (r_arr - ref_mean) / ref_std
    ref_skew = (T / ((T - 1) * (T - 2))) * float(np.sum(norm_diff ** 3))

    # Analytical Pearson fourth moment kurtosis:
    # g_2 = (1 / n) * sum( ((x_i - mean) / std)^4 )
    ref_kurt = float(np.mean(norm_diff ** 4))

    # ACASH Higher Moments
    acash_mean, acash_std, acash_skew, acash_kurt = DeflatedSharpeEngine.calculate_higher_moments(returns)

    assert math.isclose(acash_mean, ref_mean, abs_tol=1e-12)
    assert math.isclose(acash_std, ref_std, abs_tol=1e-12)
    assert math.isclose(acash_skew, ref_skew, abs_tol=1e-12)
    assert math.isclose(acash_kurt, ref_kurt, abs_tol=1e-12)


    # 2. Independent Analytical SR0 Derivation (Bailey & López de Prado 2014 EVT Gumbel Approximation)
    K = 100
    V_period = 0.0004  # Variance in period space
    euler_mascheroni = 0.57721566490153286060651209

    p1 = 1.0 - (1.0 / K)
    p2 = 1.0 - (1.0 / (K * math.e))
    z1 = float(norm.ppf(p1))
    z2 = float(norm.ppf(p2))

    ref_sr0_period = math.sqrt(V_period) * ((1.0 - euler_mascheroni) * z1 + euler_mascheroni * z2)

    acash_sr0_period = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(
        effective_trials_k=K,
        variance_of_trials=V_period,
    )
    assert math.isclose(acash_sr0_period, ref_sr0_period, abs_tol=1e-10)

    # 3. Independent Analytical DSR Test Statistic & p-Value
    sr_hat_period = ref_mean / ref_std
    denominator_term = 1.0 - (ref_skew * sr_hat_period) + (((ref_kurt - 1.0) / 4.0) * (sr_hat_period ** 2))
    ref_z_stat = (sr_hat_period - ref_sr0_period) * math.sqrt(T - 1) / math.sqrt(denominator_term)
    ref_dsr_prob = float(norm.cdf(ref_z_stat))

    # Analytical MinTRL at alpha = 0.05
    z_alpha = float(norm.ppf(0.95))
    if (sr_hat_period - ref_sr0_period) > 1e-12:
        ref_min_trl = int(math.ceil(1.0 + denominator_term * ((z_alpha / (sr_hat_period - ref_sr0_period)) ** 2)))
    else:
        ref_min_trl = int(1e9)

    # ACASH Full DSR Evaluation
    dsr_result = DeflatedSharpeEngine.evaluate_dsr(
        returns=returns,
        effective_trials_k=K,
        variance_of_trials=V_period,
        confidence_level_alpha=0.05,
        periods_per_year=252.0,
    )

    assert math.isclose(float(dsr_result.dsr_statistic), ref_z_stat, abs_tol=1e-6)
    assert math.isclose(float(dsr_result.dsr_p_value), ref_dsr_prob, abs_tol=1e-6)
    assert dsr_result.min_track_record_length_bars == ref_min_trl
    assert dsr_result.declared_trials_k == K
    assert dsr_result.effective_independent_trials_k == K
    assert dsr_result.independence_assumption == "CONSERVATIVE_SEARCH_OPPORTUNITIES_UPPER_BOUND"


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


def test_golden_reference_haircut_sharpe_analytical_derivation() -> None:
    """Verify ACASH Multiple-Testing Haircut Sharpe against analytical Harvey-Liu-Zhu Bonferroni derivation."""
    # Scenario: estimated_sharpe = 0.30, sample_size_t = 100, effective_trials_k = 10
    SR = 0.30
    T = 100
    K = 10

    # 1. Raw t-statistic
    t_raw = SR * math.sqrt(T)  # 3.0

    # 2. Two-sided raw p-value
    p_raw = math.erfc(t_raw / math.sqrt(2.0))  # ~0.002699796063

    # 3. Bonferroni adjusted p-value
    p_adj = min(1.0, p_raw * float(K))  # ~0.02699796063

    # 4. Adjusted t-statistic
    prob = 1.0 - (p_adj / 2.0)
    t_adj = float(norm.ppf(prob))  # ~2.21183359

    # 5. Non-linear Haircut Sharpe
    ref_haircut_sr = max(0.0, t_adj / math.sqrt(T))  # ~0.221183359

    acash_haircut = MultipleTestingEngine.calculate_haircut_sharpe(
        estimated_sharpe=SR,
        effective_trials_k=K,
        sample_size_t=T,
    )

    assert math.isclose(float(acash_haircut), ref_haircut_sr, abs_tol=1e-6)
