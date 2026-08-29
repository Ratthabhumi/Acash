"""Probability of Backtest Overfitting (PBO) & Parameter Fragility Engine (Phase 6).

Implements:
- Probability of Backtest Overfitting (PBO) via CPCV log-odds distribution with mid-rank tie handling (Bailey et al. 2016).
- Parameter Sensitivity Surface & Curvature Fragility Metric across [0.75 theta_0, 1.0 theta_0, 1.25 theta_0] perturbations.
- Component-wise analytical friction stress decay monotonicity (Phase 4/5 reality gap coupling).
"""

from decimal import Decimal
import math
from typing import Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.validation.schema import FrictionStressParameters, OverfittingReport, ParameterPerturbationGrid


class OverfittingEngine:
    """Evaluates backtest overfitting probability, parameter stability, and analytical friction stress.

    MATHEMATICAL PRIMITIVE NOTICE:
    This engine is a low-level mathematical calculator. Direct primitive invocation
    does NOT constitute a Gate 6 validation decision. Sovereign governance authority
    resides exclusively in StatisticalValidationGate.
    """


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
        perturbation_grid: ParameterPerturbationGrid,
        max_degradation_tolerance: float = 0.30,
    ) -> Tuple[float, bool]:
        """Evaluate second-order discrete curvature and degradation stability across +/- 25% perturbations.

        Grid is guaranteed to be [0.75 * theta_0, 1.0 * theta_0, 1.25 * theta_0].
        Curvature: kappa = | (SR(1.25*theta) - 2*SR(theta) + SR(0.75*theta)) / (0.25*theta)^2 |
        Neighbor Degradation: max( (SR(theta) - SR(0.75*theta))/SR(theta), (SR(theta) - SR(1.25*theta))/SR(theta) )

        Returns:
            Tuple[curvature, is_stable]
        """
        theta = float(perturbation_grid.base_parameter_value)
        h = 0.25 * theta

        sr_left = float(perturbation_grid.sharpe_profile[0])
        sr_mid = float(perturbation_grid.sharpe_profile[1])
        sr_right = float(perturbation_grid.sharpe_profile[2])

        second_diff = (sr_right - 2.0 * sr_mid + sr_left) / (h ** 2) if h > 1e-12 else 0.0
        curvature = abs(second_diff)

        is_stable = True
        if sr_mid > 0.0:
            left_deg = (sr_mid - sr_left) / sr_mid
            right_deg = (sr_mid - sr_right) / sr_mid
            max_deg = max(left_deg, right_deg)
            if max_deg > max_degradation_tolerance:
                is_stable = False

        return float(curvature), is_stable

    @staticmethod
    def verify_analytical_friction_decay_monotonicity(
        raw_predictive_edge_bps: float,
        friction_params: Optional[FrictionStressParameters] = None,
        multipliers: Sequence[float] = (1.0, 2.0, 3.0, 5.0),
    ) -> bool:
        """Verify component-wise analytical friction stress decay monotonicity using Phase 4/5 reality gap components.

        R_stressed(m) = R_raw - m * (Spread + Fee) - m^1.5 * (Slippage + Latency + Adverse Selection)
        """
        params = friction_params or FrictionStressParameters()
        linear_cost = float(params.spread_bps + params.fee_bps)
        impact_cost = float(params.slippage_bps + params.latency_drift_bps + params.maker_adverse_selection_bps)

        prev_net = raw_predictive_edge_bps
        for m in multipliers:
            stressed_net = raw_predictive_edge_bps - (m * linear_cost) - ((m ** 1.5) * impact_cost)
            if stressed_net > prev_net + 1e-12:
                return False  # Non-monotonic behavior detected
            prev_net = stressed_net

        return True

    @classmethod
    def evaluate_overfitting_battery(
        cls,
        is_sharpe_matrix: np.ndarray,
        oos_sharpe_matrix: np.ndarray,
        perturbation_grid: ParameterPerturbationGrid,
        raw_predictive_edge_bps: float = 15.0,
        friction_params: Optional[FrictionStressParameters] = None,
        max_acceptable_pbo: float = 0.25,
    ) -> OverfittingReport:
        """Run complete overfitting, parameter perturbation curvature, and analytical friction stress battery."""
        pbo, log_mean, log_std = cls.calculate_pbo(is_sharpe_matrix, oos_sharpe_matrix)
        curvature, is_param_stable = cls.evaluate_parameter_curvature(perturbation_grid)
        is_monotonic = cls.verify_analytical_friction_decay_monotonicity(raw_predictive_edge_bps, friction_params)

        is_pbo_ok = pbo < max_acceptable_pbo

        return OverfittingReport(
            pbo_estimate=to_decimal18(Decimal(f"{pbo:.12f}")) or Decimal("0.0"),
            logits_distribution_mean=to_decimal18(Decimal(f"{log_mean:.12f}")) or Decimal("0.0"),
            logits_distribution_std=to_decimal18(Decimal(f"{log_std:.12f}")) or Decimal("0.0"),
            parameter_fragility_max_curvature=to_decimal18(Decimal(f"{curvature:.12f}")) or Decimal("0.0"),
            is_pbo_acceptable=is_pbo_ok,
            is_parameter_stable=is_param_stable,
            analytical_friction_monotonicity_passed=is_monotonic,
        )
