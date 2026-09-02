"""Phase 11 Time-Series Econometric Estimator Engine.

Pure deterministic econometric estimators operating strictly in Decimal space:
- Annualized arithmetic return
- Annualized sample volatility
- Annualized Sharpe ratio (strict fail-closed on zero variance)
- Peak-to-trough rolling window max drawdown
- Forward-monitoring inception high-water mark max drawdown
- Hit rate (% positive return periods)
- Annualized tracking error
- Student's t-statistic of excess returns
- Expected vs realized divergence (basis points)
- Option B: Information coefficient and IC decay slope are explicitly deferred (None).

Strict Fail-Closed Contracts:
- Zero float casting (strictly Decimal arithmetic).
- Zero silent artificial floors or magic constants (max(1e-12, val) is strictly forbidden).
- Zero state machine transitions or governance authority (pure math calculation layer).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.schema import ForwardObservation, ForwardWindowMetrics

DEFAULT_ANNUALIZATION_FACTOR = Decimal("252")
BPS_SCALER = Decimal("10000.0")


class ForwardMetricsCalculator:
    """Pure deterministic econometric estimator engine for forward strategy tracking."""

    def __init__(
        self,
        annualization_factor: Decimal = DEFAULT_ANNUALIZATION_FACTOR,
        risk_free_rate_annualized: Decimal = Decimal("0.0"),
    ) -> None:
        if annualization_factor <= Decimal("0.0"):
            raise DataContractError(
                f"annualization_factor must be strictly positive, got {annualization_factor}."
            )
        self.annualization_factor = annualization_factor
        self.risk_free_rate_annualized = risk_free_rate_annualized
        self._sqrt_annualization = annualization_factor.sqrt()

    def calculate_window_metrics(
        self,
        observations: Sequence[ForwardObservation],
        window_size: Optional[int] = None,
        inception_observations: Optional[Sequence[ForwardObservation]] = None,
    ) -> ForwardWindowMetrics:
        """Calculate forward rolling econometric metrics over observation window in Decimal space.

        Args:
            observations: Sequence of discrete forward observations (at least 2 required).
            window_size: Nominal window capacity. If None, defaults to len(observations).
            inception_observations: Full history since forward inception to evaluate
                                    inception HWM drawdown. If None, uses observations.

        Returns:
            ForwardWindowMetrics with all 8 deterministic time-series estimators.

        Raises:
            DataContractError: On empty sequences, N < 2, zero variance, or telemetry integrity failure.
        """
        if not observations:
            raise DataContractError("Cannot calculate metrics on empty observation sequence.")

        effective_window_size = window_size if window_size is not None else len(observations)
        if effective_window_size <= 0:
            raise DataContractError(
                f"window_size must be strictly positive, got {effective_window_size}."
            )

        # Take rolling window slice (last effective_window_size observations)
        window_obs = observations[-effective_window_size:]
        n = len(window_obs)
        if n < 2:
            raise DataContractError(
                f"At least 2 valid observations required for sample variance/volatility calculation, got {n}."
            )

        # 1. Telemetry Integrity Check
        for obs in window_obs:
            if not obs.is_telemetry_valid:
                raise DataContractError(
                    f"TELEMETRY_INVALID: Observation {obs.observation_id} (seq {obs.observation_sequence}) "
                    f"has is_telemetry_valid=False. Metric calculation must fail closed."
                )

        n_dec = Decimal(str(n))
        n_minus_one_dec = Decimal(str(n - 1))

        # 2. Annualized Arithmetic Return
        returns = [obs.realized_return for obs in window_obs]
        sum_return = sum(returns, Decimal("0.0"))
        mean_daily_return = sum_return / n_dec
        mean_realized_return_annualized = mean_daily_return * self.annualization_factor

        # 3. Annualized Sample Volatility
        sum_squared_deviations = sum(
            ((r - mean_daily_return) ** 2 for r in returns),
            Decimal("0.0"),
        )
        sample_variance = sum_squared_deviations / n_minus_one_dec

        # Strict fail-closed on zero sample variance (Principle 3 of AGENTS.md)
        if sample_variance <= Decimal("0.0"):
            raise DataContractError(
                f"Zero sample variance detected across {n} observations (variance={sample_variance}). "
                f"Sharpe ratio and volatility-based metrics are mathematically undefined."
            )

        daily_volatility = sample_variance.sqrt()
        realized_volatility_annualized = daily_volatility * self._sqrt_annualization

        # 4. Annualized Sharpe Ratio
        rf_annualized = self.risk_free_rate_annualized
        realized_sharpe_ratio = (mean_realized_return_annualized - rf_annualized) / realized_volatility_annualized

        # 5. Peak-to-Trough Rolling Max Drawdown
        max_drawdown = self._compute_max_drawdown(returns)

        # 6. Inception High-Water Mark Max Drawdown
        all_inception_obs = inception_observations if inception_observations is not None else observations
        inception_returns = [obs.realized_return for obs in all_inception_obs]
        inception_max_drawdown = self._compute_max_drawdown(inception_returns)

        # 7. Hit Rate (% of positive return periods)
        positive_count = sum((1 for r in returns if r > Decimal("0.0")), 0)
        hit_rate = Decimal(str(positive_count)) / n_dec

        # 8. Tracking Error & Expected vs Realized Divergence
        expected_returns = [obs.expected_return for obs in window_obs]
        has_expected = all(e is not None for e in expected_returns)
        has_none_expected = all(e is None for e in expected_returns)

        if has_expected:
            diffs = [
                r - exp  # exp is not None here
                for r, exp in zip(returns, expected_returns)
                if exp is not None
            ]
            sum_diff = sum(diffs, Decimal("0.0"))
            mean_diff = sum_diff / n_dec
            sum_sq_diff = sum(((d - mean_diff) ** 2 for d in diffs), Decimal("0.0"))
            tracking_variance = sum_sq_diff / n_minus_one_dec
            daily_tracking_error = tracking_variance.sqrt()
            tracking_error_annualized = daily_tracking_error * self._sqrt_annualization

            exp_vals = [e for e in expected_returns if e is not None]
            mean_exp = sum(exp_vals, Decimal("0.0")) / n_dec
            expected_vs_realized_divergence_bps = (mean_daily_return - mean_exp) * BPS_SCALER
        elif has_none_expected:
            tracking_error_annualized = Decimal("0.0")
            expected_vs_realized_divergence_bps = Decimal("0.0")
        else:
            raise DataContractError(
                "Inconsistent expected_return telemetry: expected_return must be uniformly present "
                "or uniformly None across all window observations."
            )

        # 9. Student's t-statistic of Excess Return
        daily_rf = rf_annualized / self.annualization_factor
        mean_excess_daily = mean_daily_return - daily_rf
        standard_error_daily = daily_volatility / n_dec.sqrt()
        t_stat_decay = mean_excess_daily / standard_error_daily

        return ForwardWindowMetrics(
            window_size=effective_window_size,
            observation_count=n,
            mean_realized_return_annualized=mean_realized_return_annualized,
            realized_volatility_annualized=realized_volatility_annualized,
            realized_sharpe_ratio=realized_sharpe_ratio,
            max_drawdown=max_drawdown,
            inception_max_drawdown=inception_max_drawdown,
            hit_rate=hit_rate,
            tracking_error_annualized=tracking_error_annualized,
            t_stat_decay=t_stat_decay,
            expected_vs_realized_divergence_bps=expected_vs_realized_divergence_bps,
            information_coefficient=None,  # Option B explicitly deferred
            ic_decay_slope=None,           # Option B explicitly deferred
        )

    @staticmethod
    def _compute_max_drawdown(returns: Sequence[Decimal]) -> Decimal:
        """Compute maximum peak-to-trough percentage drawdown from a return series."""
        if not returns:
            return Decimal("0.0")

        equity = Decimal("1.0")
        peak = Decimal("1.0")
        max_dd = Decimal("0.0")

        for r in returns:
            equity = equity * (Decimal("1.0") + r)
            if equity <= Decimal("0.0"):
                # Complete capital loss
                return Decimal("1.0")
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd

        return max_dd


def calculate_forward_window_metrics(
    observations: Sequence[ForwardObservation],
    window_size: Optional[int] = None,
    inception_observations: Optional[Sequence[ForwardObservation]] = None,
    annualization_factor: Decimal = DEFAULT_ANNUALIZATION_FACTOR,
    risk_free_rate_annualized: Decimal = Decimal("0.0"),
) -> ForwardWindowMetrics:
    """Convenience function calculating forward window metrics using ForwardMetricsCalculator."""
    calculator = ForwardMetricsCalculator(
        annualization_factor=annualization_factor,
        risk_free_rate_annualized=risk_free_rate_annualized,
    )
    return calculator.calculate_window_metrics(
        observations=observations,
        window_size=window_size,
        inception_observations=inception_observations,
    )
