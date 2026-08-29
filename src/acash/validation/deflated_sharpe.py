"""Deflated Sharpe Ratio (DSR) & Minimum Track Record Length (MinTRL) Engine (Phase 6).

Mathematical implementation based on:
- Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality." Journal of Portfolio Management, 40(5), 94–107.
- López de Prado, M. (2018). "Advances in Financial Machine Learning." John Wiley & Sons, Chapter 14.
- Mertens, E. (2002). "Comments on Alternative Measure of Risk."
- Opdyke, J. D. (2007). "Comparing Sharpe Ratios: So Where are the p-values?" Journal of Asset Management, 8(5), 308–336.

Strictly enforces:
- Moment estimation: Fisher-Pearson sample skewness g_1 and Pearson standardized fourth moment kurtosis g_2 >= 1.0 (normal = 3.0).
- Scale alignment: SR0 and sample Sharpe evaluated in identical frequency space (per-period) before annualization.
- Explicit SelectionCorrectionMode:
  * SINGLE_TRIAL: When K = 1, V = 0, SR0 = 0. Non-normal asymptotic test against hurdle without selection penalty.
  * MULTIPLE_TRIAL: When K >= 2, SR0 derived via EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1 using empirical trial variance V.
- Asymptotic Deflated Sharpe Ratio (DSR) non-normal test statistic and p-value.
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


class DeflatedSharpeEngine:
    """Calculates non-normal Deflated Sharpe Ratio, expected maximum null Sharpe, and MinTRL.

    MATHEMATICAL PRIMITIVE NOTICE:
    This engine is a low-level mathematical calculator. Direct primitive invocation
    does NOT constitute a Gate 6 validation decision. Sovereign governance authority
    resides exclusively in StatisticalValidationGate.
    """

    @staticmethod
    def calculate_higher_moments(returns: Sequence[Union[Decimal, float]]) -> Tuple[float, float, float, float]:
        """Compute sample mean, standard deviation, Fisher-Pearson skewness g_1, and Pearson kurtosis g_2.

        Formulation:
        - Mean: bar(X) = (1/n) sum X_i
        - Sample Variance: s^2 = (1/(n-1)) sum (X_i - bar(X))^2
        - Fisher-Pearson Skewness: g_1 = (n / ((n-1)(n-2))) * sum( ((X_i - bar(X)) / s)^3 )
        - Pearson Kurtosis: g_2 = (1/n) * sum( ((X_i - bar(X)) / s)^4 ) (normal distribution = 3.0, lower bound = 1.0)

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
        std = math.sqrt(max(1e-18, variance))

        if std <= 1e-12:
            return mean, 0.0, 0.0, 3.0

        # Fisher-Pearson adjusted sample skewness g_1
        norm_diff = diff / std
        m3_term = float(np.sum(norm_diff ** 3))
        skewness = (n / ((n - 1) * (n - 2))) * m3_term

        # Pearson standardized fourth moment kurtosis g_2 (bounded below by 1.0)
        m4_term = float(np.sum(norm_diff ** 4))
        kurtosis = max(1.0, (1.0 / n) * m4_term)

        return mean, std, float(skewness), float(kurtosis)

    @staticmethod
    def compute_expected_max_sharpe_sr0(
        effective_trials_k: int,
        variance_of_trials: float = 0.0,
    ) -> float:
        """Compute expected maximum Sharpe ratio under the null hypothesis (SR0) across K trials.

        Reference:
        Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection
        Bias, Backtest Overfitting, and Non-Normality." Journal of Portfolio Management, 40(5), 94–107.

        Estimator: EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1 (Extreme Value Theory Gumbel Approximation)
        SR0 = sqrt(V) * [ (1 - gamma_E) * Z^{-1}(1 - 1/K) + gamma_E * Z^{-1}(1 - 1/(K * e)) ]
        where:
        - gamma_E is the Euler-Mascheroni constant (~0.57721566)
        - V is the empirical sample variance of the trial distribution in the evaluated frequency space.
        - K is the total declared search trial count (SearchTrialLedger trials).

        SEARCH SPACE CENSUS & DEPENDENCE CONTRACT:
        K represents the authoritative upper bound on declared selection opportunities across the entire
        research session. Because explored strategies in quantitative research may exhibit mutual correlation,
        the effective number of statistically independent trials satisfies K_eff <= K. Using the exhaustive
        search trial count K provides a rigorous, conservative upper bound on multiple-testing selection bias.
        """
        K = max(1, effective_trials_k)
        if K <= 1 or variance_of_trials <= 1e-12:
            return 0.0

        gamma_e = EULER_MASCHERONI_CONSTANT
        p1 = 1.0 - (1.0 / K)
        p2 = 1.0 - (1.0 / (K * math.e))

        z1 = _standard_normal_ppf(max(1e-12, min(1.0 - 1e-12, p1)))
        z2 = _standard_normal_ppf(max(1e-12, min(1.0 - 1e-12, p2)))

        sr0 = math.sqrt(variance_of_trials) * ((1.0 - gamma_e) * z1 + gamma_e * z2)
        return float(sr0)

    @classmethod
    def evaluate_dsr(
        cls,
        returns: Sequence[Union[Decimal, float]],
        effective_trials_k: int = 1,
        variance_of_trials: float = 0.0,
        benchmark_sharpe: float = 0.0,
        confidence_level_alpha: float = 0.05,
        periods_per_year: float = 252.0,
        trial_ledger: Optional[SearchTrialLedger] = None,
    ) -> DSRResult:
        """Evaluate complete Deflated Sharpe Ratio and Minimum Track Record Length.

        FREQUENCY-SPACE INFERENCE INVARIANCE CONTRACT:
        All statistical hypothesis testing (z-statistic, DSR probability, MinTRL) is evaluated strictly
        in raw per-period return space (T observations, SR_period, SR0_period).
        Skewness g_1 and Kurtosis g_2 are dimensionless invariants of the discrete return series.
        Computing the non-normal asymptotic variance factor in per-period space guarantees that higher-moment
        interaction terms (g_1 * SR, (g_2 - 1)/4 * SR^2) remain scale-invariant without introducing
        spurious multi-period cross-product scaling artifacts.
        For financial readability, the resulting Sharpe ratios are also presented in annualized form via
        SR_annual = SR_period * sqrt(periods_per_year), with inference_space=PERIOD and sharpe_space=ANNUAL.
        """

        annual_mult = math.sqrt(periods_per_year) if periods_per_year > 0 else 1.0

        if trial_ledger is not None:
            effective_trials_k = trial_ledger.total_trials
            if effective_trials_k >= 2:
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

        mode = SelectionCorrectionMode.SINGLE_TRIAL if effective_trials_k <= 1 else SelectionCorrectionMode.MULTIPLE_TRIAL

        n = len(returns)
        mean, std, skew, kurt = cls.calculate_higher_moments(returns)

        # 1. Estimated sample Sharpe ratio (per-period and annualized)
        sr_hat_period = mean / std if std > 0 else 0.0
        sr_hat_annual = sr_hat_period * annual_mult

        # 2. Expected maximum Sharpe under null (per-period and annualized)
        sr0_period = cls.compute_expected_max_sharpe_sr0(effective_trials_k, variance_of_trials)
        sr0_annual = sr0_period * annual_mult

        # 3. Non-normal asymptotic variance factor:
        # sigma_SR = sqrt( (1 - g_1 * SR + (g_2 - 1)/4 * SR^2) / (T - 1) )
        denominator_term = 1.0 - (skew * sr_hat_period) + (((kurt - 1.0) / 4.0) * (sr_hat_period ** 2))
        denominator_term = max(1e-12, denominator_term)

        # 4. Asymptotic standardized test statistic z
        z_stat = (sr_hat_period - sr0_period) * math.sqrt(n - 1) / math.sqrt(denominator_term)
        dsr_prob = _standard_normal_cdf(z_stat)

        # 5. Minimum Track Record Length (MinTRL)
        z_alpha = _standard_normal_ppf(1.0 - confidence_level_alpha)
        if (sr_hat_period - sr0_period) > 1e-12:
            min_trl_bars = int(math.ceil(1.0 + denominator_term * ((z_alpha / (sr_hat_period - sr0_period)) ** 2)))
        else:
            min_trl_bars = int(1e9)  # Infinitely long track record needed if return is at or below null

        is_significant = dsr_prob >= (1.0 - confidence_level_alpha)
        has_sufficient_trl = n >= min_trl_bars

        return DSRResult(
            estimated_sharpe=to_decimal18(Decimal(f"{sr_hat_annual:.12f}")) or Decimal("0.0"),
            benchmark_sharpe=to_decimal18(Decimal(f"{benchmark_sharpe:.12f}")) or Decimal("0.0"),
            expected_max_sharpe_sr0=to_decimal18(Decimal(f"{sr0_annual:.12f}")) or Decimal("0.0"),
            sample_skewness=to_decimal18(Decimal(f"{skew:.12f}")) or Decimal("0.0"),
            sample_kurtosis=to_decimal18(Decimal(f"{kurt:.12f}")) or Decimal("3.0"),
            effective_trials_k=effective_trials_k,
            declared_trials_k=effective_trials_k,
            effective_independent_trials_k=effective_trials_k,
            independence_assumption="CONSERVATIVE_SEARCH_OPPORTUNITIES_UPPER_BOUND",
            selection_correction_mode=mode,
            sr0_estimator="EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1",
            variance_estimator="EMPIRICAL_SAMPLE_VARIANCE_DDOF1",
            sharpe_space=SharpeSpace.ANNUAL,
            inference_space=SharpeSpace.PERIOD,
            trial_variance_used=to_decimal18(Decimal(f"{variance_of_trials:.12f}")) or Decimal("0.0"),
            sample_size_t=n,
            dsr_statistic=to_decimal18(Decimal(f"{z_stat:.12f}")) or Decimal("0.0"),
            dsr_p_value=to_decimal18(Decimal(f"{dsr_prob:.12f}")) or Decimal("0.0"),
            min_track_record_length_bars=min_trl_bars,
            is_statistically_significant=is_significant,
            has_sufficient_track_record=has_sufficient_trl,
        )


