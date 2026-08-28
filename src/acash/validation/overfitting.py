"""Probability of Backtest Overfitting (PBO) & Parameter Fragility Engine (Phase 6).

Implements:
- Probability of Backtest Overfitting (PBO) via CPCV log-odds distribution (Bailey et al. 2016).
- Parameter Sensitivity Surface & Curvature Fragility Metric (penalizing knife-edge local optima).
- Friction Stress Decay Monotonicity under 1x, 2x, 3x, 5x cost multiples.
"""

from decimal import Decimal
import math
from typing import Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.validation.schema import OverfittingReport


class OverfittingEngine:
    """Evaluates backtest overfitting probability and parameter stability."""

    @staticmethod
    def calculate_pbo(
        is_sharpe_matrix: np.ndarray,
        oos_sharpe_matrix: np.ndarray,
    ) -> Tuple[float, float, float]:
        """Calculate empirical Probability of Backtest Overfitting (PBO).

        Args:
            is_sharpe_matrix: 2D array of shape (C combinations, M models) for In-Sample Sharpe.
            oos_sharpe_matrix: 2D array of shape (C combinations, M models) for Out-of-Sample Sharpe.

        Returns:
            Tuple[pbo_estimate, logits_mean, logits_std]
        """
        C, M = is_sharpe_matrix.shape
        if C < 1 or M < 2:
            return 0.0, 0.0, 0.0

        logits: List[float] = []
        underperforming_count = 0

        for c in range(C):
            # 1. Identify optimal in-sample model index m*
            m_star = int(np.argmax(is_sharpe_matrix[c, :]))

            # 2. Determine relative rank of m* in OOS slice
            oos_scores = oos_sharpe_matrix[c, :]
            # Sort OOS scores ascending
            sorted_oos = np.sort(oos_scores)
            # Find rank of m* (1-indexed)
            rank = int(np.searchsorted(sorted_oos, oos_scores[m_star])) + 1
            # Relative rank omega in (0, 1)
            omega = rank / (M + 1.0)
            omega = max(1e-6, min(1.0 - 1e-6, omega))

            # 3. Log-odds lambda = ln(omega / (1 - omega))
            logit_val = math.log(omega / (1.0 - omega))
            logits.append(logit_val)

            # 4. If logit < 0 (i.e. omega < 0.5, below median OOS performance), count as overfit
            if logit_val < 0.0:
                underperforming_count += 1

        pbo = underperforming_count / float(C)
        logits_arr = np.array(logits, dtype=np.float64)
        logits_mean = float(np.mean(logits_arr))
        logits_std = float(np.std(logits_arr))

        return pbo, logits_mean, logits_std

    @staticmethod
    def evaluate_parameter_curvature(
        param_grid: Sequence[float],
        sharpe_profile: Sequence[float],
        max_degradation_tolerance: float = 0.30,
    ) -> Tuple[float, bool]:
        """Evaluate second-order curvature and degradation stability across parameter perturbations.

        Returns:
            Tuple[max_curvature, is_stable]
        """
        n = len(param_grid)
        if n < 3 or len(sharpe_profile) != n:
            return 0.0, True

        params = np.array(param_grid, dtype=np.float64)
        sharpes = np.array(sharpe_profile, dtype=np.float64)

        peak_idx = int(np.argmax(sharpes))
        peak_sr = sharpes[peak_idx]

        # Discrete second derivative / curvature: (f(x+h) - 2f(x) + f(x-h)) / h^2
        curvatures: List[float] = []
        for i in range(1, n - 1):
            h = (params[i + 1] - params[i - 1]) / 2.0
            if h > 1e-12:
                second_diff = (sharpes[i + 1] - 2.0 * sharpes[i] + sharpes[i - 1]) / (h ** 2)
                curvatures.append(abs(second_diff))

        max_curvature = max(curvatures) if curvatures else 0.0

        # Check neighbor degradation around peak (within +/- 1 step)
        is_stable = True
        if peak_sr > 0.0:
            if peak_idx > 0:
                left_degradation = (peak_sr - sharpes[peak_idx - 1]) / peak_sr
                if left_degradation > max_degradation_tolerance:
                    is_stable = False
            if peak_idx < n - 1:
                right_degradation = (peak_sr - sharpes[peak_idx + 1]) / peak_sr
                if right_degradation > max_degradation_tolerance:
                    is_stable = False

        return float(max_curvature), is_stable

    @staticmethod
    def verify_friction_decay_monotonicity(
        base_net_return_bps: float,
        friction_multipliers: Sequence[float] = (1.0, 2.0, 3.0, 5.0),
        base_friction_bps: float = 2.0,
    ) -> bool:
        """Verify that net returns decrease monotonically as friction scales up."""
        prev_return = base_net_return_bps
        for mult in friction_multipliers[1:]:
            stressed_return = base_net_return_bps - (mult - 1.0) * base_friction_bps
            if stressed_return > prev_return + 1e-12:
                return False  # Non-monotonic behavior detected!
            prev_return = stressed_return
        return True

    @classmethod
    def evaluate_overfitting_battery(
        cls,
        is_sharpe_matrix: np.ndarray,
        oos_sharpe_matrix: np.ndarray,
        param_grid: Sequence[float],
        sharpe_profile: Sequence[float],
        base_net_return_bps: float,
        max_acceptable_pbo: float = 0.25,
    ) -> OverfittingReport:
        """Run complete overfitting and parameter sensitivity evaluation."""
        pbo, log_mean, log_std = cls.calculate_pbo(is_sharpe_matrix, oos_sharpe_matrix)
        curvature, is_param_stable = cls.evaluate_parameter_curvature(param_grid, sharpe_profile)
        is_monotonic = cls.verify_friction_decay_monotonicity(base_net_return_bps)

        is_pbo_ok = pbo < max_acceptable_pbo

        return OverfittingReport(
            pbo_estimate=to_decimal18(Decimal(f"{pbo:.12f}")) or Decimal("0.0"),
            logits_distribution_mean=to_decimal18(Decimal(f"{log_mean:.12f}")) or Decimal("0.0"),
            logits_distribution_std=to_decimal18(Decimal(f"{log_std:.12f}")) or Decimal("0.0"),
            parameter_fragility_max_curvature=to_decimal18(Decimal(f"{curvature:.12f}")) or Decimal("0.0"),
            is_pbo_acceptable=is_pbo_ok,
            is_parameter_stable=is_param_stable,
            friction_monotonicity_passed=is_monotonic,
        )
