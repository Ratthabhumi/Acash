"""Statistical Evaluation, HAC Inference, and 3-Tier Friction Engine (Phase 4).

Strictly enforces:
- Primary Inference: OLS slope beta_H under Heteroskedasticity and Autocorrelation Consistent (HAC) covariance.
- Configurable HAC Bandwidth: Baseline (H-1), Fixed Lag, Newey-West Plug-in, and Andrews AR(1).
- Non-parametric Association: Pearson IC, Spearman Rank IC (tie-aware), and Autocorrelation.
- 3-Tier Friction Waterfall: Raw Predictive Edge -> Spread+Fee Net -> Slippage+Latency Economic Edge.
- Robustness Matrix: Multi-bandwidth stability verification.
"""

from decimal import Decimal
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from acash.data.features.engine import to_decimal18
from acash.data.schema import DataContractError
from acash.research.schema import (
    CostModelConfig,
    EvaluationResult,
    HacBandwidthMethod,
    HacInferencePolicy,
    HypothesisSpecification,
    RobustnessCheckRecord,
)


def _normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def calculate_spearman_rank_ic(
    x: Sequence[Decimal],
    y: Sequence[Decimal],
) -> Optional[Decimal]:
    """Calculate Spearman Rank Correlation Coefficient with fractional rank tie-handling."""
    if len(x) != len(y) or len(x) < 2:
        return None

    x_float = [float(v) for v in x]
    y_float = [float(v) for v in y]

    def get_ranks(arr: List[float]) -> np.ndarray:
        temp = np.argsort(arr)
        ranks = np.empty_like(temp, dtype=float)
        ranks[temp] = np.arange(len(arr))
        # Handle ties
        vals, inverse, counts = np.unique(arr, return_inverse=True, return_counts=True)
        tie_ranks = np.zeros_like(vals, dtype=float)
        for i, val in enumerate(vals):
            indices = np.where(inverse == i)[0]
            tie_ranks[i] = np.mean(ranks[indices])
        return tie_ranks[inverse]

    x_ranks = get_ranks(x_float)
    y_ranks = get_ranks(y_float)

    std_x = np.std(x_ranks)
    std_y = np.std(y_ranks)

    if std_x == 0 or std_y == 0:
        return None

    corr = float(np.corrcoef(x_ranks, y_ranks)[0, 1])
    return to_decimal18(Decimal(f"{corr:.18f}"))


def calculate_pearson_ic(
    x: Sequence[Decimal],
    y: Sequence[Decimal],
) -> Optional[Decimal]:
    """Calculate Pearson Linear Correlation Coefficient."""
    if len(x) != len(y) or len(x) < 2:
        return None

    x_float = np.array([float(v) for v in x])
    y_float = np.array([float(v) for v in y])

    std_x = np.std(x_float)
    std_y = np.std(y_float)

    if std_x == 0 or std_y == 0:
        return None

    corr = float(np.corrcoef(x_float, y_float)[0, 1])
    return to_decimal18(Decimal(f"{corr:.18f}"))


def calculate_autocorrelation(
    x: Sequence[Decimal],
    lag: int = 1,
) -> Optional[Decimal]:
    """Calculate sample autocorrelation at specified lag."""
    if len(x) <= lag + 1:
        return None

    x_float = np.array([float(v) for v in x])
    s1 = x_float[:-lag]
    s2 = x_float[lag:]

    if np.std(s1) == 0 or np.std(s2) == 0:
        return None

    corr = float(np.corrcoef(s1, s2)[0, 1])
    return to_decimal18(Decimal(f"{corr:.18f}"))


def determine_hac_bandwidth(
    method: HacBandwidthMethod,
    sample_size: int,
    horizon: int,
    fixed_lag: Optional[int] = None,
    residuals: Optional[np.ndarray] = None,
) -> int:
    """Determine HAC kernel lag truncation bandwidth L."""
    if method == HacBandwidthMethod.FIXED_HORIZON_MINUS_ONE:
        return max(0, horizon - 1)
    elif method == HacBandwidthMethod.FIXED_LAG:
        return max(0, fixed_lag if fixed_lag is not None else horizon - 1)
    elif method == HacBandwidthMethod.NEWEY_WEST_PLUGIN:
        # Standard Newey-West (1994) rule-of-thumb plug-in: floor(4 * (T / 100)^(2/9))
        return max(0, int(math.floor(4.0 * ((sample_size / 100.0) ** (2.0 / 9.0)))))
    elif method == HacBandwidthMethod.ANDREWS_AR1_PLUGIN:
        if residuals is not None and len(residuals) > 2:
            r1 = residuals[:-1]
            r2 = residuals[1:]
            if np.std(r1) > 0 and np.std(r2) > 0:
                rho = float(np.corrcoef(r1, r2)[0, 1])
                rho = max(-0.99, min(0.99, rho))
                alpha = (4.0 * (rho ** 2)) / ((1.0 - (rho ** 2)) ** 2)
                return max(0, int(math.floor(1.1447 * ((alpha * sample_size) ** (1.0 / 3.0)))))
        return max(0, horizon - 1)
    return max(0, horizon - 1)


def compute_ols_beta_and_hac(
    x: Sequence[Decimal],
    y: Sequence[Decimal],
    lag_bandwidth: int,
) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    """Compute OLS slope beta, HAC standard error, HAC t-stat, and asymptotic p-value using Bartlett kernel.

    Model: Y_t = alpha + beta * X_t + eps_t
    Score: u_t = (X_t - mean(X)) * eps_t
    """
    n = len(x)
    if n < 3:
        raise DataContractError(f"Insufficient sample size for regression: {n} < 3")

    x_arr = np.array([float(v) for v in x])
    y_arr = np.array([float(v) for v in y])

    x_mean = np.mean(x_arr)
    y_mean = np.mean(y_arr)

    x_dm = x_arr - x_mean
    y_dm = y_arr - y_mean

    denom = np.sum(x_dm ** 2)
    if denom <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0"), Decimal("1.0")

    beta_hat = np.sum(x_dm * y_dm) / denom
    alpha_hat = y_mean - beta_hat * x_mean

    # Residuals and moment conditions
    residuals = y_arr - (alpha_hat + beta_hat * x_arr)
    scores = x_dm * residuals

    # HAC Covariance via Bartlett Kernel: w(l, L) = 1 - l / (L + 1)
    L = min(lag_bandwidth, n - 1)
    gamma_0 = np.sum(scores ** 2) / n
    omega_hat = gamma_0

    for l in range(1, L + 1):
        weight = 1.0 - (l / (L + 1.0))
        gamma_l = np.sum(scores[l:] * scores[:-l]) / n
        omega_hat += 2.0 * weight * gamma_l

    # Asymptotic variance of beta: Var(beta) = (1/N) * Omega / (Var(X))^2
    var_x = denom / n
    var_beta = (omega_hat / n) / (var_x ** 2)
    se_beta = math.sqrt(max(1e-18, var_beta))

    t_stat = beta_hat / se_beta if se_beta > 0 else 0.0
    p_val = 2.0 * (1.0 - _normal_cdf(abs(t_stat)))

    return (
        to_decimal18(Decimal(f"{beta_hat:.12f}")) or Decimal("0"),
        to_decimal18(Decimal(f"{se_beta:.12f}")) or Decimal("0"),
        to_decimal18(Decimal(f"{t_stat:.12f}")) or Decimal("0"),
        to_decimal18(Decimal(f"{p_val:.12f}")) or Decimal("1.0"),
    )



def calculate_3tier_friction_waterfall(
    fwd_returns: Sequence[Decimal],
    signals: Sequence[Decimal],
    cost_config: Optional[CostModelConfig] = None,
) -> Tuple[Decimal, Decimal, Decimal]:
    """Calculate 3-Tier Friction Waterfall in basis points (bps).

    Tier 1 (Raw Predictive Edge): E[R * Signal] * 10000
    Tier 2 (Spread & Fee Net): Tier 1 - (Quoted Spread + Roundtrip Broker Fees)
    Tier 3 (Economic Edge): Tier 2 - Fixed Slippage Proxy
    """
    cfg = cost_config or CostModelConfig()
    if not fwd_returns or not signals or len(fwd_returns) != len(signals):
        return Decimal("0"), Decimal("0"), Decimal("0")

    # Raw expected product return
    n = len(fwd_returns)
    raw_returns = [float(fwd_returns[i]) * float(signals[i]) for i in range(n)]
    tier1_raw_bps = Decimal(str(np.mean(raw_returns) * 10000.0))

    # Tier 2: Deduct Quoted Spread + Roundtrip Fees
    tier2_cost_bps = cfg.quoted_spread_bps + cfg.roundtrip_broker_fee_bps
    tier2_net_bps = tier1_raw_bps - tier2_cost_bps

    # Tier 3: Deduct Fixed Slippage Proxy
    tier3_economic_bps = tier2_net_bps - cfg.fixed_slippage_bps

    return (
        to_decimal18(tier1_raw_bps) or Decimal("0"),
        to_decimal18(tier2_net_bps) or Decimal("0"),
        to_decimal18(tier3_economic_bps) or Decimal("0"),
    )


def evaluate_hypothesis_relationship(
    features: Sequence[Decimal],
    forward_returns: Sequence[Decimal],
    horizon: int,
    hypothesis: HypothesisSpecification,
    hac_policy: Optional[HacInferencePolicy] = None,
    cost_config: Optional[CostModelConfig] = None,
    purged_count: int = 0,
) -> EvaluationResult:
    """Evaluate full statistical inference, IC metrics, 3-tier friction, and robustness matrix."""
    policy = hac_policy or HacInferencePolicy()
    cost_cfg = cost_config or CostModelConfig()
    n = len(features)

    if n < 3:
        raise DataContractError(f"Minimum 3 valid observations required for evaluation, got {n}")

    # Compute exact OLS model residuals e_t = y_t - (alpha_hat + beta_hat * x_t) for HAC plug-in bandwidth
    x_arr = np.array([float(v) for v in features])
    y_arr = np.array([float(v) for v in forward_returns])
    x_dm = x_arr - np.mean(x_arr)
    y_dm = y_arr - np.mean(y_arr)
    denom = float(np.sum(x_dm ** 2))
    beta_hat = float(np.sum(x_dm * y_dm) / denom) if denom > 0 else 0.0
    alpha_hat = float(np.mean(y_arr) - beta_hat * np.mean(x_arr))
    ols_residuals = y_arr - (alpha_hat + beta_hat * x_arr)

    primary_lag = determine_hac_bandwidth(
        policy.bandwidth_method,
        sample_size=n,
        horizon=horizon,
        fixed_lag=policy.fixed_lag_value,
        residuals=ols_residuals,
    )


    # Primary OLS Slope Beta & HAC Inference
    beta, hac_se, hac_t_stat, p_val = compute_ols_beta_and_hac(features, forward_returns, primary_lag)

    # Association Statistics
    p_ic = calculate_pearson_ic(features, forward_returns)
    r_ic = calculate_spearman_rank_ic(features, forward_returns)
    autocorr = calculate_autocorrelation(features, lag=1)

    # Convert directional signals
    dir_mult = Decimal("1.0") if hypothesis.expected_direction == "LONG" else Decimal("-1.0")
    signals = [f * dir_mult for f in features]
    t1_bps, t2_bps, t3_bps = calculate_3tier_friction_waterfall(forward_returns, signals, cost_cfg)

    # Robustness Check Matrix across Lags
    robustness_records: List[RobustnessCheckRecord] = []
    if policy.run_bandwidth_robustness_check:
        for r_lag in policy.robustness_lags:
            b_r, se_r, t_r, p_r = compute_ols_beta_and_hac(features, forward_returns, r_lag)
            robustness_records.append(
                RobustnessCheckRecord(
                    lag=r_lag,
                    beta=b_r,
                    hac_se=se_r,
                    hac_t_stat=t_r,
                    asymptotic_p_value=p_r,
                )
            )

    # Falsification Checks against InvalidationCriteria
    crit = hypothesis.invalidation_criteria
    is_falsified = False
    if r_ic is None or abs(r_ic) < crit.min_in_sample_rank_ic:
        is_falsified = True
    if abs(hac_t_stat) < crit.min_hac_t_stat:
        is_falsified = True
    if autocorr is not None and abs(autocorr) > crit.max_feature_autocorrelation:
        is_falsified = True


    is_sig = abs(hac_t_stat) >= Decimal("2.00") and p_val <= Decimal("0.05")

    return EvaluationResult(
        horizon=horizon,
        valid_observations_count=n,
        purged_observations_count=purged_count,
        beta=beta,
        hac_se=hac_se,
        hac_t_stat=hac_t_stat,
        asymptotic_p_value=p_val,
        selected_hac_lag=primary_lag,
        pearson_ic=p_ic,
        spearman_rank_ic=r_ic,
        feature_autocorrelation_lag1=autocorr,
        tier1_raw_edge_bps=t1_bps,
        tier2_net_edge_bps=t2_bps,
        tier3_economic_edge_bps=t3_bps,
        robustness_matrix=robustness_records,
        is_statistically_significant=is_sig,
        is_falsified=is_falsified,
    )
