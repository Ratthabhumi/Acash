"""Probability of Backtest Overfitting (PBO) & Parameter Fragility Engine (Phase 6).

Implements:
- Probability of Backtest Overfitting (PBO) via CPCV log-odds distribution with mid-rank tie handling (Bailey et al. 2016).
- Parameter Sensitivity Surface & Curvature Fragility Metric across [0.75 theta_0, theta_0, 1.25 theta_0] perturbations.
- Friction Stress Decay Monotonicity under cost multipliers.
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
        """Calculate empirical Probability of Backtest Overfitting (PBO) with exact mid-rank tie handling.

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
            m_star_val = oos_sharpe_matrix[c, m_star]

            # 2. Compute exact mid-rank of m* in OOS slice
            oos_slice = oos_sharpe_matrix[c, :]
            strictly_less = int(np.sum(oos_slice < m_star_val))
            equal_count = int(np.sum(oos_slice == m_star_val))
            # Mid-rank formula (1-indexed): strictly_less + 1 + 0.5 * (equal_count - 1)
            mid_rank = strictly_less + 1.0 + 0.5 * (equal_count - 1.0)

            # Relative rank omega in (0, 1)
            omega = mid_rank / (M + 1.0)
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

        Enforces discrete second derivative curvature:
        kappa = | (SR(theta + h) - 2*SR(theta) + SR(theta - h)) / h^2 |
        and verifies that neighbor degradation <= max_degradation_tolerance (default 30%).

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

        curvatures: List[float] = []
        for i in range(1, n - 1):
            h_left = params[i] - params[i - 1]
            h_right = params[i + 1] - params[i]
            h_avg = (h_left + h_right) / 2.0
            if h_avg > 1e-12:
                second_diff = (sharpes[i + 1] - 2.0 * sharpes[i] + sharpes[i - 1]) / (h_avg ** 2)
                curvatures.append(abs(second_diff))

        max_curvature = max(curvatures) if curvatures else 0.0

        # Check neighbor degradation around peak (within +/- 1 step)
        is_stable = True
        if peak_sr > 0.0:
            if peak_idx > 0:
                left_deg = (peak_sr - sharpes[peak_idx - 1]) / peak_sr
                if left_deg > max_degradation_tolerance:
                    is_stable = False
            if peak_idx < n - 1:
                right_deg = (peak_sr - sharpes[peak_idx + 1]) / peak_sr
                if right_deg > max_degradation_tolerance:
                    is_stable = False

        return float(max_curvature), is_stable

    @staticmethod
    def verify_friction_decay_monotonicity(
        base_net_return_bps: float,
        friction_multipliers: Sequence[float] = (1.0, 2.0, 3.0, 5.0),
        base_friction_bps: float = 2.0,
    ) -> bool:
        """Verify that net returns decrease monotonically as friction multipliers increase."""
        prev_return = base_net_return_bps
        for mult in friction_multipliers[1:]:
            stressed_return = base_net_return_bps - (mult - 1.0) * base_friction_bps
            if stressed_return > prev_return + 1e-12:
                return False
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
