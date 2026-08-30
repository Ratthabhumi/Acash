"""Deflated Sharpe Ratio (DSR) & Minimum Track Record Length (MinTRL) Engine (Phase 6).

Mathematical implementation based on:
- Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality." Journal of Portfolio Management, 40(5), 94–107.
- López de Prado, M. (2018). "Advances in Financial Machine Learning." John Wiley & Sons, Chapter 14.
- Mertens, E. (2002). "Comments on Alternative Measure of Risk."
- Opdyke, J. D. (2007). "Comparing Sharpe Ratios: So Where are the p-values?" Journal of Asset Management, 8(5), 308–336.

Strictly enforces:
- Moment estimation: Fisher-Pearson sample skewness g_1 and Pearson standardized fourth moment kurtosis g_2 >= ((n-1)/n)^2 (normal distribution = 3.0).
- Scale alignment: SR0 and sample Sharpe evaluated in identical frequency space (per-period) before annualization.
- Location-Scale Estimator Form: SR0 = mu_trials + sqrt(V_trials) * f(K).
  * ZERO_LOCATION variant (default): mu_trials = 0.0 under standard ACASH null governance policy.
  * EMPIRICAL_LOCATION_SCALE variant: mu_trials derived from trial ledger or explicit input.
- SelectionCorrectionMode:
  * SINGLE_TRIAL: When K = 1, V = 0, SR0 = mu_trials. Non-normal asymptotic test against hurdle without selection penalty.
  * MULTIPLE_TRIAL: When K >= 2, SR0 derived via Gumbel EVT formula using empirical trial variance V and declared search count K.
- Asymptotic Deflated Sharpe Ratio (DSR) non-normal test statistic and p-value with strict denominator > 0 fail-closed validation.
- Minimum Track Record Length (MinTRL) required sample size calculation.
"""


from decimal import Decimal
import math
from typing import Any, List, Optional, Sequence, Tuple, Union
import numpy as np
from scipy import stats  # type: ignore[import-untyped]

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.validation.schema import DSRResult, SearchTrialLedger, SelectionCorrectionMode, SharpeSpace


EULER_MASCHERONI_CONSTANT = 0.57721566490153286060


def _standard_normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function Phi(x)."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _standard_normal_ppf(p: float) -> float:
    """Inverse standard normal CDF using Acklam's rational approximation algorithm."""
    if p <= 0.0 or p >= 1.0:
        raise ValueError(f"Probability p must be in (0, 1), got {p}")

    a = [
        -3.969683028665376e+01,
        2.209460984245205e+02,
        -2.759285104469687e+02,
        1.383577518672690e+02,
        -3.066479806614716e+01,
        2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01,
        1.615858368580409e+02,
        -1.556989798598866e+02,
        6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e+00,
        -2.549732539343734e+00,
        4.374664141464968e+00,
        2.938163982698783e+00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e+00,
        3.754408661907416e+00,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        # Lower tail
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    elif p <= p_high:
        # Central region
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    else:
        # Upper tail
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


def _to_dec(val: Union[int, float, Decimal, str], default: str = "0.0") -> Decimal:
    """Safe, explicit Decimal conversion that avoids ambiguous 'or Decimal(...)' fallback idiom."""
    dec_val = to_decimal18(Decimal(f"{val:.12f}") if isinstance(val, (float, int)) else Decimal(str(val)))
    return dec_val if dec_val is not None else Decimal(default)


def compute_hac_newey_west_variance(
    returns: Union[Sequence[Union[float, Decimal]], np.ndarray],
    max_lags: Optional[int] = None,
) -> float:
    """Compute Newey-West (1987) Heteroskedasticity and Autocorrelation Consistent (HAC) long-run variance.

    Mathematical formulation:
    gamma_0 = (1/T) * sum_{t=1}^T (r_t - mu)^2
    gamma_l = (1/T) * sum_{t=l+1}^T (r_t - mu)(r_{t-l} - mu)
    sigma_LR^2 = gamma_0 + 2 * sum_{l=1}^L w_l * gamma_l
    where w_l = 1 - l / (L + 1) (Bartlett kernel).

    Lag truncation bandwidth L defaults to Newey-West (1994) plug-in rule:
    L = floor(4 * (T / 100)^(2/9)).

    FAIL-CLOSED GOVERNANCE SPECIFICATION:
    - Requires sample size T >= 2.
    - Requires valid max_lags in [0, T - 1].
    - Strictly fails closed with DataContractError on non-finite observations, zero sample variance, or non-positive long-run variance.
    - Never applies silent artificial numerical floors or silent fallback constants.
    """
    if isinstance(returns, np.ndarray):
        arr = returns.astype(np.float64)
    else:
        arr = np.array([float(x) for x in returns], dtype=np.float64)

    n = len(arr)
    if n < 2:
        raise DataContractError(f"Cannot compute HAC long-run variance for sample size n={n} < 2.")

    if not np.all(np.isfinite(arr)):
        raise DataContractError("Returns series contains non-finite values (NaN or Inf).")

    if max_lags is not None:
        if not isinstance(max_lags, int) or max_lags < 0 or max_lags >= n:
            raise DataContractError(
                f"Invalid max_lags={max_lags} for sample size n={n}. "
                f"Must be a non-negative integer satisfying 0 <= max_lags < {n}."
            )
        lags = max_lags
    else:
        lags = max(1, int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0)))))

    mu = float(np.mean(arr))
    demeaned = arr - mu
    gamma_0 = float(np.dot(demeaned, demeaned) / n)

    if gamma_0 <= 1e-12 or not math.isfinite(gamma_0):
        raise DataContractError(
            f"Zero or near-zero variance (gamma_0={gamma_0:.6e} <= 1e-12) detected in return series; "
            f"HAC long-run variance is undefined."
        )

    if lags == 0:
        return gamma_0

    lr_var = gamma_0
    for l in range(1, lags + 1):
        weight = 1.0 - (l / (lags + 1.0))
        gamma_l = float(np.dot(demeaned[l:], demeaned[:-l]) / n)
        lr_var += 2.0 * weight * gamma_l

    if lr_var <= 1e-12 or not math.isfinite(lr_var):
        raise DataContractError(
            f"Non-positive or near-zero HAC long-run variance (sigma_LR^2={lr_var:.6e} <= 1e-12) detected; "
            f"HAC inference fails closed."
        )

    return lr_var


def compute_hac_p_value(
    returns: Union[Sequence[Union[float, Decimal]], np.ndarray],
    max_lags: Optional[int] = None,
) -> Decimal:
    """Compute two-sided hypothesis test p-value against H_0: mu = 0 using Newey-West HAC standard error.

    t_HAC = mean(r) / sqrt(sigma_LR^2 / T)
    p_HAC = 2 * (1 - Phi(|t_HAC|)) = erfc(|t_HAC| / sqrt(2))

    FAIL-CLOSED GOVERNANCE SPECIFICATION:
    - Strictly fails closed with DataContractError on non-finite observations, zero variance, or undefined SE.
    - Never fabricates p=1.0 on invalid mathematical states.
    """
    if isinstance(returns, np.ndarray):
        arr = returns.astype(np.float64)
    else:
        arr = np.array([float(x) for x in returns], dtype=np.float64)

    n = len(arr)
    if n < 2:
        raise DataContractError(f"Cannot compute HAC p-value for sample size n={n} < 2.")

    mu = float(np.mean(arr))
    lr_var = compute_hac_newey_west_variance(arr, max_lags=max_lags)
    se_hac = math.sqrt(lr_var / n)
    if se_hac <= 1e-12 or not math.isfinite(se_hac):
        raise DataContractError(
            f"Zero or near-zero HAC standard error (se_hac={se_hac:.6e} <= 1e-12) detected; p-value is undefined."
        )

    t_hac = mu / se_hac
    p_val = math.erfc(abs(t_hac) / math.sqrt(2.0))
    dec = to_decimal18(Decimal(f"{p_val:.12f}"))
    if dec is None:
        raise DataContractError(f"Failed to serialize HAC p-value ({p_val}) to 18-decimal precision.")
    return dec





class DeflatedSharpeEngine:

    """Calculates non-normal Deflated Sharpe Ratio, expected maximum null Sharpe, and MinTRL.

    MATHEMATICAL PRIMITIVE NOTICE:
    This engine is a low-level mathematical calculator. Direct primitive invocation
    does NOT constitute a Gate 6 validation decision. Sovereign governance authority
    resides exclusively in StatisticalValidationGate.
    """

    TRIAL_VARIANCE_MIN_THRESHOLD: float = 1e-12
    """Explicit numerical threshold below which trial variance is deemed zero (SR_0 = 0.0)."""

    @staticmethod
    def calculate_higher_moments(returns: Sequence[Union[Decimal, float]]) -> Tuple[float, float, float, float]:
        """Compute sample mean, standard deviation, Fisher-Pearson skewness g_1, and Pearson kurtosis g_2.

        Formulation:
        - Mean: bar(X) = (1/n) sum X_i
        - Fisher-Pearson Skewness: G_1 = (n / ((n-1)(n-2))) * sum( ((X_i - bar(X)) / s)^3 )
        - Pearson Kurtosis: g_2 = (1/n) * sum( ((X_i - bar(X)) / s)^4 ) (normal distribution = 3.0, finite-sample lower bound = ((n - 1) / n)^2)


        Returns:
            Tuple[mean, std, skewness_g1, kurtosis_g2]
        """
        float_values: List[float] = []
        for idx, r in enumerate(returns):
            if isinstance(r, Decimal):
                if not r.is_finite():
                    raise DataContractError(f"Non-finite Decimal value '{r}' (NaN or Inf) encountered in return series.")
                try:
                    rf = float(r)
                    if not math.isfinite(rf):
                        raise DataContractError(
                            f"Decimal observation '{r}' at index {idx} exceeds float64 representable magnitude boundary."
                        )
                except (OverflowError, ValueError) as e:
                    raise DataContractError(
                        f"Decimal observation '{r}' at index {idx} exceeds float64 representable magnitude boundary."
                    ) from e
            else:
                rf = float(r)
                if not math.isfinite(rf):
                    raise DataContractError(f"Non-finite value '{r}' (NaN or Inf) encountered in return series.")
            float_values.append(rf)

        arr = np.array(float_values, dtype=np.float64)

        n = len(arr)
        if n < 4:
            raise DataContractError(f"Minimum 4 return observations required for moment estimation, got {n}")

        mean = float(np.mean(arr))
        diff = arr - mean
        variance = float(np.sum(diff ** 2) / (n - 1))
        std = math.sqrt(max(0.0, variance))

        if std <= 1e-12:
            raise DataContractError(
                f"Sample return series has zero or near-zero variance (std={std:.2e} <= 1e-12); "
                f"higher statistical moments and Sharpe ratio are mathematically undefined for constant returns."
            )


        # Fisher-Pearson adjusted sample skewness G_1
        norm_diff = diff / std
        m3_term = float(np.sum(norm_diff ** 3))
        skewness = (n / ((n - 1) * (n - 2))) * m3_term

        # Pearson standardized fourth moment kurtosis g_2:
        # g_2 = (1 / n) * sum( ((x_i - mean) / std)^4 )
        # Note: Bounded below by ((n - 1) / n)^2 for finite samples with ddof=1 sample standard deviation.
        m4_term = float(np.sum(norm_diff ** 4))
        kurtosis = (1.0 / n) * m4_term

        return mean, std, float(skewness), float(kurtosis)


    @classmethod
    def compute_expected_max_sharpe_sr0(
        cls,
        dsr_trials_k: Optional[int] = None,
        variance_of_trials: float = 0.0,
        mean_of_trials: float = 0.0,
        effective_trials_k: Optional[int] = None,
    ) -> float:
        """Compute expected maximum Sharpe ratio under the null hypothesis (SR0) across K trials.

        Reference:
        Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection
        Bias, Backtest Overfitting, and Non-Normality." Journal of Portfolio Management, 40(5), 94–107, Eq. (10).

        Estimator: Extreme Value Theory (EVT) Gumbel Location-Scale Approximation:
        SR_0 = mu_trials + sqrt(V_trials) * [ (1 - gamma_E) * Z^{-1}(1 - 1/K) + gamma_E * Z^{-1}(1 - 1/(K * e)) ]
        where:
        - mu_trials is the expected/null mean of the trial distribution (defaults to 0.0 under ACASH zero-location policy).
        - gamma_E is the Euler-Mascheroni constant (~0.57721566)
        - V_trials is the empirical sample variance of the trial distribution in the evaluated frequency space.
        - K is the total declared search trial count (SearchTrialLedger trials).

        METHODOLOGICAL & CONDITIONAL PROPERTIES:
        - Conditional Monotonicity in K: For a FIXED trial variance estimate V > 0, SR_0 is monotonically increasing in K.
          Across distinct trial universes where both (K, V) vary jointly, SR_0 is determined jointly by location and dispersion.
        - Zero-Location Policy: By default, ACASH enforces mu_trials = 0.0 (testing against a zero-alpha null benchmark).
        - Numerical Boundary: If V <= TRIAL_VARIANCE_MIN_THRESHOLD (1e-12) or K <= 1, the EVT dispersion penalty is 0.0,
          yielding SR_0 = mu_trials (0.0 under default zero-location policy).
        """
        if dsr_trials_k is not None and effective_trials_k is not None and dsr_trials_k != effective_trials_k:
            raise DataContractError(
                f"Contradictory DSR trial counts: dsr_trials_k={dsr_trials_k} != effective_trials_k={effective_trials_k}."
            )
        K = dsr_trials_k if dsr_trials_k is not None else (effective_trials_k if effective_trials_k is not None else 1)
        if K < 1:
            raise DataContractError(f"dsr_trials_k must be >= 1, got {K}")
        if K <= 1 or variance_of_trials <= cls.TRIAL_VARIANCE_MIN_THRESHOLD:
            return float(mean_of_trials)

        gamma_e = EULER_MASCHERONI_CONSTANT
        p1 = 1.0 - (1.0 / K)
        p2 = 1.0 - (1.0 / (K * math.e))

        if p1 <= 0.0 or p1 >= 1.0:
            raise DataContractError(f"p1 probability {p1} out of bounds (0, 1) for K={K}")
        if p2 <= 0.0 or p2 >= 1.0:
            raise DataContractError(f"p2 probability {p2} out of bounds (0, 1) for K={K}")

        z1 = _standard_normal_ppf(p1)
        z2 = _standard_normal_ppf(p2)

        dispersion_term = math.sqrt(variance_of_trials) * ((1.0 - gamma_e) * z1 + gamma_e * z2)
        sr0 = float(mean_of_trials) + dispersion_term
        return float(sr0)

    @classmethod
    def evaluate_dsr(
        cls,
        returns: Sequence[Union[Decimal, float]],
        dsr_trials_k: Optional[int] = None,
        variance_of_trials: float = 0.0,
        mean_of_trials: float = 0.0,
        benchmark_sharpe: float = 0.0,
        confidence_level_alpha: float = 0.05,
        periods_per_year: float = 252.0,
        trial_ledger: Optional[SearchTrialLedger] = None,
        declared_trials_k: Optional[int] = None,
        effective_independent_trials_k: Optional[int] = None,
        use_empirical_trial_mean: bool = False,
        effective_trials_k: Optional[int] = None,
    ) -> DSRResult:
        """Evaluate complete Deflated Sharpe Ratio and Minimum Track Record Length.

        METHODOLOGICAL SPECIFICATION & TERMINOLOGY (ACASH DSR Governance Variant):
        - Canonical DSR (Bailey & López de Prado, 2014) defines K as the effective number of independent
          trials (or estimates K_eff <= K from cross-trial correlation).
        - In the ACASH sovereign governance framework, under a fixed trial-variance estimate V, increasing
          declared search opportunities K_declared from the authoritative SearchTrialLedger monotonically
          increases the EVT selection hurdle SR_0:
            SR_0(K_declared, V) >= SR_0(K_effective_independent, V)  [for fixed V]
          Across different trial universes where (K, V, mu) vary jointly, SR_0 is determined jointly by location
          and dispersion.
        - Location Parameter Provenance:
          * If use_empirical_trial_mean=False (ACASH zero-location policy): mu_trials = 0.0 strictly.
          * If use_empirical_trial_mean=True: mu_trials is derived directly from trial_ledger.get_empirical_sharpe_mean().
        - DSR Probability: Phi(z_DSR) computes the probability that the true strategy Sharpe exceeds the
          expected maximum Sharpe under selection bias and non-normal (skewness g_1, kurtosis g_2) returns.
          This is a non-normal, selection-corrected composite probability, strictly distinct from single-test
          asymptotic normal p-values stored in SearchTrialRecord.

        FREQUENCY-SPACE INFERENCE INVARIANCE CONTRACT:
        All statistical hypothesis testing (z-statistic, DSR probability, MinTRL) is evaluated strictly
        in raw per-period return space (T observations, SR_period, SR0_period).
        Skewness G_1 and Kurtosis g_2 are dimensionless invariants of the discrete return series.
        Computing the non-normal asymptotic variance factor in per-period space guarantees that higher-moment
        interaction terms (G_1 * SR, (g_2 - 1)/4 * SR^2) remain scale-invariant without introducing
        spurious multi-period cross-product scaling artifacts.

        ANNUALIZATION & SERIAL INDEPENDENCE NOTE:
        Sharpe ratio annualization via sqrt(periods_per_year) is a standard scale identity under i.i.d. assumptions.
        It does NOT correct for serial autocorrelation or overlapping forward label horizons.
        Reported values include inference_space=PERIOD and sharpe_space=ANNUAL.
        """
        if dsr_trials_k is not None and effective_trials_k is not None and dsr_trials_k != effective_trials_k:
            raise DataContractError(
                f"Contradictory DSR trial counts: dsr_trials_k={dsr_trials_k} != effective_trials_k={effective_trials_k}."
            )
        resolved_k = dsr_trials_k if dsr_trials_k is not None else (effective_trials_k if effective_trials_k is not None else 1)


        annual_mult = math.sqrt(periods_per_year) if periods_per_year > 0 else 1.0

        if trial_ledger is not None:
            declared_k = trial_ledger.total_trials
            k_for_dsr = declared_k
            if use_empirical_trial_mean:
                raw_mean = trial_ledger.get_empirical_sharpe_mean()
                if trial_ledger.sharpe_space == SharpeSpace.ANNUAL:
                    if periods_per_year <= 0:
                        raise DataContractError(f"Invalid periods_per_year {periods_per_year} for ANNUAL SharpeSpace scaling.")
                    mean_of_trials = raw_mean / annual_mult
                elif trial_ledger.sharpe_space == SharpeSpace.PERIOD:
                    mean_of_trials = raw_mean
                else:
                    raise DataContractError(f"Unsupported SharpeSpace '{trial_ledger.sharpe_space}' in trial_ledger.")
            else:
                mean_of_trials = 0.0  # ACASH Zero-Location Sovereign Policy (strictly enforced)

            if declared_k >= 2:
                raw_var = trial_ledger.get_empirical_sharpe_variance()
                if trial_ledger.sharpe_space == SharpeSpace.ANNUAL:
                    if periods_per_year <= 0:
                        raise DataContractError(f"Invalid periods_per_year {periods_per_year} for ANNUAL SharpeSpace scaling.")
                    variance_of_trials = raw_var / periods_per_year
                elif trial_ledger.sharpe_space == SharpeSpace.PERIOD:
                    variance_of_trials = raw_var
                else:
                    raise DataContractError(f"Unsupported SharpeSpace '{trial_ledger.sharpe_space}' in trial_ledger.")
            else:
                variance_of_trials = 0.0
        else:
            declared_k = declared_trials_k if declared_trials_k is not None else resolved_k
            k_for_dsr = declared_k

        mode = SelectionCorrectionMode.SINGLE_TRIAL if k_for_dsr <= 1 else SelectionCorrectionMode.MULTIPLE_TRIAL

        n = len(returns)
        mean, std, skew, kurt = cls.calculate_higher_moments(returns)

        # 1. Estimated sample Sharpe ratio (per-period and annualized)
        sr_hat_period = mean / std if std > 0 else 0.0
        sr_hat_annual = sr_hat_period * annual_mult

        # 2. Expected maximum Sharpe under null (per-period and annualized)
        sr0_period = cls.compute_expected_max_sharpe_sr0(
            dsr_trials_k=k_for_dsr,
            variance_of_trials=variance_of_trials,
            mean_of_trials=mean_of_trials,
        )
        sr0_annual = sr0_period * annual_mult


        # 3. Non-normal asymptotic variance factor:
        # sigma_SR = sqrt( (1 - g_1 * SR + (g_2 - 1)/4 * SR^2) / (T - 1) )
        denominator_term = 1.0 - (skew * sr_hat_period) + (((kurt - 1.0) / 4.0) * (sr_hat_period ** 2))
        if not math.isfinite(denominator_term) or denominator_term <= 0.0:
            raise DataContractError(
                f"DSR non-normal asymptotic variance factor is non-positive or non-finite "
                f"(denominator_term = {denominator_term:.6e} <= 0). Strategy return series higher moments "
                f"(skew={skew:.4f}, kurt={kurt:.4f}, SR={sr_hat_period:.4f}) violate asymptotic regularity conditions."
            )

        # 4. Asymptotic standardized test statistic z
        z_stat = (sr_hat_period - sr0_period) * math.sqrt(n - 1) / math.sqrt(denominator_term)
        dsr_prob = _standard_normal_cdf(z_stat)

        # 5. Minimum Track Record Length (MinTRL)
        z_alpha = _standard_normal_ppf(1.0 - confidence_level_alpha)
        min_trl_bars: Optional[int] = None
        if (sr_hat_period - sr0_period) > 1e-12:
            computed_trl = int(math.ceil(1.0 + denominator_term * ((z_alpha / (sr_hat_period - sr0_period)) ** 2)))
            min_trl_bars = computed_trl
            is_unbounded = False
            has_sufficient_trl = n >= computed_trl
        else:
            min_trl_bars = None  # Mathematically infinite / unbounded track record needed
            is_unbounded = True
            has_sufficient_trl = False


        is_significant = dsr_prob >= (1.0 - confidence_level_alpha)

        estimator_name = (
            "ZERO_LOCATION_EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1"
            if abs(mean_of_trials) <= 1e-12
            else "EMPIRICAL_LOCATION_SCALE_GUMBEL_V1"
        )

        dsr_dec = _to_dec(dsr_prob, default="0.0")

        return DSRResult(
            estimated_sharpe=_to_dec(sr_hat_annual, default="0.0"),
            benchmark_sharpe=_to_dec(benchmark_sharpe, default="0.0"),
            expected_max_sharpe_sr0=_to_dec(sr0_annual, default="0.0"),
            sample_skewness=_to_dec(skew, default="0.0"),
            sample_kurtosis=_to_dec(kurt, default="3.0"),
            dsr_trials_k=declared_k,
            effective_trials_k=declared_k,
            declared_trials_k=declared_k,
            effective_independent_trials_k=effective_independent_trials_k,
            independence_assumption="FIXED_VARIANCE_DECLARED_SEARCH_OPPORTUNITIES_UPPER_BOUND",
            selection_correction_mode=mode,
            sr0_estimator=estimator_name,
            variance_estimator="EMPIRICAL_SAMPLE_VARIANCE_DDOF1",
            sharpe_space=SharpeSpace.ANNUAL,
            inference_space=SharpeSpace.PERIOD,
            trial_mean_used=_to_dec(mean_of_trials, default="0.0"),
            trial_variance_used=_to_dec(variance_of_trials, default="0.0"),
            sample_size_t=n,
            dsr_statistic=_to_dec(z_stat, default="0.0"),
            dsr_probability=dsr_dec,
            dsr_p_value=dsr_dec,
            min_track_record_length_bars=min_trl_bars,
            is_min_trl_unbounded=is_unbounded,
            is_statistically_significant=is_significant,
            has_sufficient_track_record=has_sufficient_trl,
        )






