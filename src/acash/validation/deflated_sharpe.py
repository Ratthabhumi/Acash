"""Deflated Sharpe Ratio (DSR) & Minimum Track Record Length (MinTRL) Engine (Phase 6).

Mathematical implementation based on:
- Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality." Journal of Portfolio Management, 40(5), 94–107.
- López de Prado, M. (2018). "Advances in Financial Machine Learning." John Wiley & Sons, Chapter 14.

Strictly enforces:
- Unbiased higher-moment estimation (Sample Skewness gamma_3, Excess Kurtosis gamma_4).
- Expected maximum Sharpe under null hypothesis (SR0) via Extreme Value Theory (EVT) with Euler-Mascheroni constant.
- Asymptotic Deflated Sharpe Ratio (DSR) non-normal test statistic and p-value.
- Minimum Track Record Length (MinTRL) required sample size calculation.
"""

from decimal import Decimal
import math
from typing import Optional, Sequence, Tuple, Union
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.validation.schema import DSRResult


EULER_MASCHERONI_CONSTANT = 0.57721566490153286060


def _standard_normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function Phi(x)."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _standard_normal_ppf(p: float) -> float:
    """Inverse standard normal cumulative distribution function Z^{-1}(p) via Winitzki/rational approximation."""
    if p <= 0.0 or p >= 1.0:
        raise ValueError(f"Probability p must be in (0, 1), got {p}")

    # Accurate approximation for inverse normal CDF
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

    q = p - 0.5
    if abs(q) <= 0.42:
        r = q * q
        num = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        den = (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        return num / den

    r = p if q < 0.0 else 1.0 - p
    r = math.log(-math.log(r))
    num = ((((c[0] * r + c[1]) * r + c[2]) * r + c[3]) * r + c[4]) * r + c[5]
    den = (((d[0] * r + d[1]) * r + d[2]) * r + d[3]) * r + 1.0
    return -num / den if q < 0.0 else num / den


class DeflatedSharpeEngine:
    """Calculates non-normal Deflated Sharpe Ratio, expected maximum null Sharpe, and MinTRL."""

    @staticmethod
    def calculate_higher_moments(returns: Sequence[Union[Decimal, float]]) -> Tuple[float, float, float, float]:
        """Compute sample mean, standard deviation, skewness (gamma_3), and Pearson kurtosis (gamma_4).

        Returns:
            Tuple[mean, std, skewness, kurtosis] where normal distribution has kurtosis = 3.0.
        """
        arr = np.array([float(r) for r in returns], dtype=np.float64)
        n = len(arr)
        if n < 4:
            raise DataContractError(f"Minimum 4 return observations required for higher moment estimation, got {n}")

        mean = float(np.mean(arr))
        diff = arr - mean
        variance = float(np.sum(diff ** 2) / (n - 1))
        std = math.sqrt(max(1e-18, variance))

        # Sample skewness (Fisher-Pearson standardized third moment)
        m3 = float(np.sum(diff ** 3) / n)
        skewness = m3 / (std ** 3) if std > 0 else 0.0

        # Sample kurtosis (Pearson fourth moment)
        m4 = float(np.sum(diff ** 4) / n)
        kurtosis = m4 / (std ** 4) if std > 0 else 3.0

        return mean, std, skewness, kurtosis

    @staticmethod
    def compute_expected_max_sharpe_sr0(
        effective_trials_k: int,
        variance_of_trials: float = 1.0,
    ) -> float:
        """Compute expected maximum Sharpe ratio under the null hypothesis (SR0) across K independent/correlated trials.

        Formula (Bailey & López de Prado 2014):
        SR0 = sqrt(V) * [ (1 - gamma_E) * Z^{-1}(1 - 1/K) + gamma_E * Z^{-1}(1 - 1/(K * e)) ]
        """
        K = max(1, effective_trials_k)
        if K == 1:
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
        benchmark_sharpe: float = 0.0,
        confidence_level_alpha: float = 0.05,
        annualization_factor: float = 1.0,
        variance_of_trials: float = 1.0,
    ) -> DSRResult:
        """Evaluate complete Deflated Sharpe Ratio and Minimum Track Record Length.

        Args:
            returns: Sequence of periodic strategy returns.
            effective_trials_k: Total number of parameter variations/hypotheses explored.
            benchmark_sharpe: Baseline Sharpe threshold (default 0.0).
            confidence_level_alpha: Significance level (default 0.05).
            annualization_factor: Factor to annualize Sharpe (e.g. sqrt(252) for daily).
            variance_of_trials: Variance of Sharpe ratios across all exploratory trials.
        """
        n = len(returns)
        mean, std, skew, kurt = cls.calculate_higher_moments(returns)

        # Estimated sample Sharpe ratio (per-period)
        sr_hat_period = mean / std if std > 0 else 0.0
        sr_hat_annual = sr_hat_period * annualization_factor

        # Expected maximum Sharpe under null (per-period)
        sr0_annual = cls.compute_expected_max_sharpe_sr0(effective_trials_k, variance_of_trials)
        sr0_period = sr0_annual / annualization_factor if annualization_factor > 0 else sr0_annual

        # Non-normal asymptotic variance factor:
        # sigma_SR = sqrt( (1 - gamma_3 * SR + (gamma_4 - 1)/4 * SR^2) / (T - 1) )
        denominator_term = 1.0 - (skew * sr_hat_period) + (((kurt - 1.0) / 4.0) * (sr_hat_period ** 2))
        denominator_term = max(1e-12, denominator_term)

        # Asymptotic standardized test statistic z
        z_stat = (sr_hat_period - sr0_period) * math.sqrt(n - 1) / math.sqrt(denominator_term)
        dsr_prob = _standard_normal_cdf(z_stat)

        # Minimum Track Record Length (MinTRL)
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
            sample_size_t=n,
            dsr_statistic=to_decimal18(Decimal(f"{z_stat:.12f}")) or Decimal("0.0"),
            dsr_p_value=to_decimal18(Decimal(f"{dsr_prob:.12f}")) or Decimal("0.0"),
            min_track_record_length_bars=min_trl_bars,
            is_statistically_significant=is_significant,
            has_sufficient_track_record=has_sufficient_trl,
        )
