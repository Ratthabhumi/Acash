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


def _to_dec(val: Union[int, float, Decimal, str], default: str = "0.0") -> Decimal:
    """Safe, explicit Decimal conversion that avoids ambiguous 'or Decimal(...)' fallback idiom."""
    dec_val = to_decimal18(Decimal(f"{val:.12f}") if isinstance(val, (float, int)) else Decimal(str(val)))
    return dec_val if dec_val is not None else Decimal(default)



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

        Reference:
        Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2016).
        "The Probability of Backtest Overfitting." Journal of Computational Finance, 20(4), 39–69.

        Mathematical Formulation & Relative Rank Convention:
        1. For each combination split c in {1, ..., C}:
           - Identify optimal in-sample model: m* = argmax_{m=1..M} IS_Sharpe[c, m]
           - Determine exact mid-rank of m* in OOS slice:
             mid_rank = sum(I(OOS < OOS[m*])) + 1.0 + 0.5 * (sum(I(OOS == OOS[m*])) - 1.0)
           - Relative rank convention:
             omega = mid_rank / (M + 1.0)
             Rationale: Using (M + 1) maps rank in {1, ..., M} strictly into (0, 1), guaranteeing
             finite log-odds logits while ensuring that the exact median mid_rank = (M + 1)/2 yields
             omega = 0.5 and log-odds lambda = ln(0.5 / 0.5) = 0.0.
           - Log-odds: lambda = ln(omega / (1.0 - omega))
           - Count overfit if lambda < 0.0 (i.e. omega < 0.5, strictly below median OOS performance).
        2. PBO is the empirical proportion of CSCV splits where the IS-optimal model underperforms median OOS:
           PBO = (1 / C) * sum_{c=1}^C I(lambda_c < 0.0)
           where C is the total number of CSCV splits (C = (N choose N/2) in balanced CSCV).

        Args:
            is_sharpe_matrix: 2D array of shape (C combinations, M models) for In-Sample Sharpe.
            oos_sharpe_matrix: 2D array of shape (C combinations, M models) for Out-of-Sample Sharpe.

        Returns:
            Tuple[pbo_estimate, logits_distribution_mean, logits_distribution_std]
            where logits_distribution_std is the population standard deviation (ddof=0) over the C splits.
        """
        if not isinstance(is_sharpe_matrix, np.ndarray) or not isinstance(oos_sharpe_matrix, np.ndarray):
            raise DataContractError("CSCV Sharpe matrices must be numpy.ndarray instances.")
        if is_sharpe_matrix.ndim != 2 or oos_sharpe_matrix.ndim != 2:
            raise DataContractError(
                f"CSCV Sharpe matrices must be 2-dimensional. Got shapes {is_sharpe_matrix.shape} and {oos_sharpe_matrix.shape}."
            )
        if is_sharpe_matrix.shape != oos_sharpe_matrix.shape:
            raise DataContractError(
                f"CSCV In-Sample and Out-of-Sample Sharpe matrix shape mismatch: {is_sharpe_matrix.shape} != {oos_sharpe_matrix.shape}."
            )

        C, M = is_sharpe_matrix.shape
        if C < 1:
            raise DataContractError(f"CSCV matrix must contain at least C >= 1 split, got C={C}.")
        if M < 2:
            raise DataContractError(f"CSCV matrix must contain at least M >= 2 candidate models, got M={M}.")

        if not np.all(np.isfinite(is_sharpe_matrix)) or not np.all(np.isfinite(oos_sharpe_matrix)):
            raise DataContractError("CSCV Sharpe matrices contain non-finite values (NaN, +inf, or -inf).")

        logits: List[float] = []
        underperforming_count = 0

        for c in range(C):
            is_slice = is_sharpe_matrix[c, :]
            # ACASH Canonicalized Ranking Quantization Policy:
            # Quantize Sharpes to 10 decimal places (1e-10 equivalence class) to ensure deterministic tie
            # resolution across floating-point platforms. Note: this is an explicit governance ranking
            # policy rather than exact IEEE float equality.
            quantized_is = np.round(is_slice, decimals=10)
            max_is_val = float(np.max(quantized_is))

            # 1. Identify all optimal in-sample model indices m* achieving max IS Sharpe (Symmetric IS-Tie Policy)
            tied_indices = np.where(quantized_is == max_is_val)[0]

            # 2. Compute exact mid-rank of all tied winners in OOS slice and compute average relative rank
            oos_slice = oos_sharpe_matrix[c, :]
            quantized_oos = np.round(oos_slice, decimals=10)
            omega_list: List[float] = []
            for m_star in tied_indices:
                m_star_val = quantized_oos[m_star]
                strictly_less = int(np.sum(quantized_oos < m_star_val))
                equal_count = int(np.sum(quantized_oos == m_star_val))
                mid_rank = strictly_less + 1.0 + 0.5 * (equal_count - 1.0)
                omega_m = mid_rank / (M + 1.0)
                omega_list.append(omega_m)

            omega = float(np.mean(omega_list))
            if not (0.0 < omega < 1.0) or not math.isfinite(omega):
                raise DataContractError(
                    f"PBO relative rank omega={omega} violates mathematical invariant 0 < omega < 1 on CSCV split {c}."
                )

            # 3. Log-odds lambda = ln(omega / (1 - omega))
            logit_val = math.log(omega / (1.0 - omega))
            logits.append(logit_val)


            # 4. If logit < 0 (i.e. omega < 0.5, strictly below median OOS performance), count as overfit
            if logit_val < 0.0:
                underperforming_count += 1

        pbo = underperforming_count / float(C)
        logits_arr = np.array(logits, dtype=np.float64)
        logits_mean = float(np.mean(logits_arr))
        # Population standard deviation over enumerated CSCV partition splits (ddof=0)
        logits_std = float(np.std(logits_arr, ddof=0))

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
        """Verify analytical friction stress decay monotonicity under an explicit super-linear cost-scaling model.

        Cost-Scaling Model:
        R_stressed(m) = R_raw - m * (Spread + Fee) - (m^1.5) * (Slippage + Latency + Adverse Selection)
        where:
        - m is a stress multiplier evaluating sensitivity to friction expansion (Phase 4/5 reality gap).
        - Exponent alpha = 1.5 is a structural stress assumption penalizing non-linear market impact.
        Note: This is an analytical sensitivity stress test evaluating cost scaling, not an empirical market impact measurement.
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
            pbo_estimate=_to_dec(pbo, default="0.0"),
            logits_distribution_mean=_to_dec(log_mean, default="0.0"),
            logits_distribution_std=_to_dec(log_std, default="0.0"),
            parameter_fragility_max_curvature=_to_dec(curvature, default="0.0"),
            is_pbo_acceptable=is_pbo_ok,
            is_parameter_stable=is_param_stable,
            analytical_friction_monotonicity_passed=is_monotonic,
        )

