"""Statistical Validation Gate Orchestrator (Phase 6).

Implements the master validation gate enforcing:
1. Deflated Sharpe Ratio & MinTRL significance with Search Trial Ledger coupling.
2. Combinatorial Purged Cross-Validation PBO bounds.
3. Parameter sensitivity curvature and non-fragility.
4. Friction decay monotonicity.
5. Sealed blind Out-of-Sample (OOS) performance retention (Strict Fail-Closed).
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Dict, List, Optional, Sequence, Union
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.validation.cpcv import CombinatorialPurgedCrossValidation
from acash.validation.deflated_sharpe import DeflatedSharpeEngine
from acash.validation.multiple_testing import MultipleTestingEngine
from acash.validation.overfitting import OverfittingEngine
from acash.validation.schema import (
    DSRResult,
    MultipleTestingResult,
    OverfittingReport,
    SearchTrialLedger,
    ValidationConfig,
    ValidationGateVerdict,
    ValidationReport,
)


def _compute_series_sha256(series: Optional[Sequence[Union[Decimal, float]]]) -> str:
    """Compute deterministic SHA-256 hash of a numerical sequence."""
    if not series:
        return "NONE"
    raw_str = ",".join(f"{float(v):.8f}" for v in series)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]


class StatisticalValidationGate:
    """Master orchestrator for Phase 6 Statistical Validation & Overfitting Controls."""

    def __init__(self, config: Optional[ValidationConfig] = None) -> None:
        self.config = config or ValidationConfig()
        self.cpcv_engine = CombinatorialPurgedCrossValidation(self.config)

    def evaluate_strategy(
        self,
        strategy_id: str,
        hypothesis_id: str,
        in_sample_returns: Sequence[Union[Decimal, float]],
        out_of_sample_returns: Optional[Sequence[Union[Decimal, float]]] = None,
        effective_trials_k: int = 1,
        variance_of_trials: float = 1.0,
        trial_ledger: Optional[SearchTrialLedger] = None,
        all_trials_p_values: Optional[Sequence[Union[Decimal, float]]] = None,
        is_cpcv_sharpe_matrix: Optional[np.ndarray] = None,
        oos_cpcv_sharpe_matrix: Optional[np.ndarray] = None,
        param_grid: Optional[Sequence[float]] = None,
        sharpe_profile: Optional[Sequence[float]] = None,
        base_net_return_bps: float = 10.0,
        fixed_created_timestamp_utc: Optional[str] = None,
    ) -> ValidationReport:
        """Run complete statistical validation battery and emit definitive verdict.

        Fails closed: Any missing OOS returns or failed threshold strictly results in REJECT.
        """
        n_is = len(in_sample_returns)
        if n_is < 4:
            raise DataContractError(f"Insufficient in-sample return observations: {n_is} < 4")

        # Couple with SearchTrialLedger if provided
        if trial_ledger is not None:
            effective_trials_k = trial_ledger.total_trials
            variance_of_trials = trial_ledger.empirical_sharpe_variance
            p_vals_candidate = trial_ledger.p_values
        else:
            p_vals_candidate = None

        # 1. Deflated Sharpe Ratio & MinTRL
        dsr_result = DeflatedSharpeEngine.evaluate_dsr(
            returns=in_sample_returns,
            effective_trials_k=effective_trials_k,
            variance_of_trials=variance_of_trials,
            confidence_level_alpha=float(self.config.confidence_level_alpha),
            trial_ledger=trial_ledger,
        )

        # 2. Multiple Testing FWER & Haircut Sharpe
        p_vals = all_trials_p_values or p_vals_candidate or [float(dsr_result.dsr_p_value)]
        mult_result = MultipleTestingEngine.evaluate_multiple_testing(
            p_values=p_vals,
            estimated_sharpe=float(dsr_result.estimated_sharpe),
            sample_size_t=n_is,
            confidence_level_alpha=float(self.config.confidence_level_alpha),
        )

        # 3. Overfitting & Parameter Fragility
        if is_cpcv_sharpe_matrix is not None and oos_cpcv_sharpe_matrix is not None:
            is_mat = is_cpcv_sharpe_matrix
            oos_mat = oos_cpcv_sharpe_matrix
        else:
            # Baseline single-run matrix
            is_mat = np.array([[float(dsr_result.estimated_sharpe), 0.0]])
            oos_mat = np.array([[float(dsr_result.estimated_sharpe), 0.0]])

        grid = param_grid or [0.75, 1.0, 1.25]
        profile = sharpe_profile or [float(dsr_result.estimated_sharpe)] * len(grid)

        overfit_report = OverfittingEngine.evaluate_overfitting_battery(
            is_sharpe_matrix=is_mat,
            oos_sharpe_matrix=oos_mat,
            param_grid=grid,
            sharpe_profile=profile,
            base_net_return_bps=base_net_return_bps,
            max_acceptable_pbo=float(self.config.max_acceptable_pbo),
        )

        # 4. Out-of-Sample Performance Evaluation (Fail-Closed)
        oos_sr: Optional[Decimal] = None
        retention_pct: Optional[Decimal] = None
        has_valid_oos = (out_of_sample_returns is not None) and (len(out_of_sample_returns) >= 4)

        if has_valid_oos and out_of_sample_returns is not None:
            mean_oos, std_oos, _, _ = DeflatedSharpeEngine.calculate_higher_moments(out_of_sample_returns)
            raw_oos_sr = mean_oos / std_oos if std_oos > 0 else 0.0
            oos_sr = to_decimal18(Decimal(f"{raw_oos_sr:.12f}")) or Decimal("0.0")

            if dsr_result.estimated_sharpe > Decimal("0.0"):
                ret_val = (oos_sr / dsr_result.estimated_sharpe) * Decimal("100.0")
                retention_pct = to_decimal18(ret_val)

        # 5. Fail-Closed Gating Decision Logic
        verdict = ValidationGateVerdict.PASS_TRADEABLE_ALPHA
        is_tradeable = True

        if not has_valid_oos:
            # Hard Gate: Missing or insufficient OOS data strictly fails closed!
            verdict = ValidationGateVerdict.REJECT_MISSING_OOS_DATA
            is_tradeable = False
        elif not dsr_result.is_statistically_significant:
            verdict = ValidationGateVerdict.REJECT_OVERFIT_DSR
            is_tradeable = False
        elif not dsr_result.has_sufficient_track_record:
            verdict = ValidationGateVerdict.REJECT_INSUFFICIENT_TRL
            is_tradeable = False
        elif not overfit_report.is_pbo_acceptable:
            verdict = ValidationGateVerdict.REJECT_HIGH_PBO
            is_tradeable = False
        elif not overfit_report.is_parameter_stable:
            verdict = ValidationGateVerdict.REJECT_PARAMETER_FRAGILE
            is_tradeable = False
        elif not overfit_report.friction_monotonicity_passed:
            verdict = ValidationGateVerdict.REJECT_FRICTION_COLLAPSE
            is_tradeable = False
        elif retention_pct is not None and retention_pct < self.config.min_oos_sharpe_retention_pct:
            verdict = ValidationGateVerdict.REJECT_OOS_DEGRADATION
            is_tradeable = False

        # Deterministic Content-Derived Validation Report ID (timestamp excluded from hash)
        is_hash = _compute_series_sha256(in_sample_returns)
        oos_hash = _compute_series_sha256(out_of_sample_returns)
        val_content = f"{strategy_id}:{hypothesis_id}:{is_hash}:{oos_hash}:{effective_trials_k}:{verdict.value}"
        val_hash = hashlib.sha256(val_content.encode("utf-8")).hexdigest()[:16]
        val_id = f"VAL_{strategy_id}_{val_hash}"

        now_utc = fixed_created_timestamp_utc or datetime.now(timezone.utc).isoformat()

        return ValidationReport(
            validation_id=val_id,
            strategy_id=strategy_id,
            hypothesis_id=hypothesis_id,
            verdict=verdict,
            is_tradeable_alpha=is_tradeable,
            dsr_result=dsr_result,
            multiple_testing_result=mult_result,
            overfitting_report=overfit_report,
            in_sample_sharpe=dsr_result.estimated_sharpe,
            out_of_sample_sharpe=oos_sr,
            oos_retention_pct=retention_pct,
            created_timestamp_utc=now_utc,
        )
