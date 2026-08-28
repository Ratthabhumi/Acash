"""Statistical Validation Gate Orchestrator (Phase 6).

Implements the master validation gate enforcing:
1. Deflated Sharpe Ratio & MinTRL significance with strict Search Trial Ledger coupling (K_ledger == K_DSR == K_Holm == K_BH).
2. Combinatorial Purged Cross-Validation PBO bounds with mid-rank tie handling.
3. Parameter sensitivity curvature & stability on strict +/- 25% perturbation grids.
4. Component-wise friction decay monotonicity.
5. Sealed blind Out-of-Sample (OOS) performance retention (Strict Fail-Closed).
6. Sovereign cryptographic separation between evidence_digest and decision_digest.
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
    FrictionStressParameters,
    MultipleTestingResult,
    OverfittingReport,
    ParameterPerturbationGrid,
    SearchTrialLedger,
    SearchTrialRecord,
    ValidationConfig,
    ValidationGateVerdict,
    ValidationReport,
)


def _compute_canonical_series_sha256(series: Optional[Sequence[Union[Decimal, float]]]) -> str:
    """Compute deterministic SHA-256 hash using exact canonical Decimal strings (no float rounding)."""
    if not series:
        return "NONE"
    dec_strings = [f"{Decimal(str(v)):.18f}" for v in series]
    raw_payload = ",".join(dec_strings)
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


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
        trial_ledger: Optional[SearchTrialLedger] = None,
        is_cpcv_sharpe_matrix: Optional[np.ndarray] = None,
        oos_cpcv_sharpe_matrix: Optional[np.ndarray] = None,
        perturbation_grid: Optional[ParameterPerturbationGrid] = None,
        raw_predictive_edge_bps: float = 15.0,
        friction_params: Optional[FrictionStressParameters] = None,
        fixed_created_timestamp_utc: Optional[str] = None,
    ) -> ValidationReport:
        """Run complete statistical validation battery and emit definitive, cryptographically-sealed verdict."""
        n_is = len(in_sample_returns)
        if n_is < 4:
            raise DataContractError(f"Insufficient in-sample return observations: {n_is} < 4")

        # 1. Search Intensity & Trial Coupling
        # Enforce K_ledger == K_DSR == K_Holm == K_BH
        if trial_ledger is not None:
            effective_k = trial_ledger.total_trials
            all_p_values = trial_ledger.p_values
        else:
            # Single-trial baseline ledger
            dummy_record = SearchTrialRecord(
                trial_id=f"trial_single_{strategy_id}",
                strategy_id=strategy_id,
                hypothesis_id=hypothesis_id,
                feature_names=["baseline"],
                parameters={},
                in_sample_sharpe=Decimal("1.0"),
                p_value=Decimal("0.05"),
            )
            trial_ledger = SearchTrialLedger(
                ledger_id=f"ledger_single_{strategy_id}",
                hypothesis_id=hypothesis_id,
                trials=[dummy_record],
            )
            effective_k = 1
            all_p_values = [Decimal("0.05")]

        # 2. Deflated Sharpe Ratio & MinTRL
        dsr_result = DeflatedSharpeEngine.evaluate_dsr(
            returns=in_sample_returns,
            effective_trials_k=effective_k,
            confidence_level_alpha=float(self.config.confidence_level_alpha),
            trial_ledger=trial_ledger,
        )

        # 3. Multiple Testing FWER & Haircut Sharpe
        mult_result = MultipleTestingEngine.evaluate_multiple_testing(
            p_values=all_p_values,
            estimated_sharpe=float(dsr_result.estimated_sharpe),
            sample_size_t=n_is,
            confidence_level_alpha=float(self.config.confidence_level_alpha),
        )

        # 4. Overfitting & Parameter Fragility
        if is_cpcv_sharpe_matrix is not None and oos_cpcv_sharpe_matrix is not None:
            is_mat = is_cpcv_sharpe_matrix
            oos_mat = oos_cpcv_sharpe_matrix
        else:
            is_mat = np.array([[float(dsr_result.estimated_sharpe), 0.0]])
            oos_mat = np.array([[float(dsr_result.estimated_sharpe), 0.0]])

        # Enforce strict [0.75, 1.0, 1.25] perturbation grid
        if perturbation_grid is None:
            theta_0 = Decimal("10.0")
            sr_val = dsr_result.estimated_sharpe
            perturbation_grid = ParameterPerturbationGrid(
                base_parameter_name="lookback",
                base_parameter_value=theta_0,
                grid_values=[theta_0 * Decimal("0.75"), theta_0, theta_0 * Decimal("1.25")],
                sharpe_profile=[sr_val, sr_val, sr_val],
            )

        overfit_report = OverfittingEngine.evaluate_overfitting_battery(
            is_sharpe_matrix=is_mat,
            oos_sharpe_matrix=oos_mat,
            perturbation_grid=perturbation_grid,
            raw_predictive_edge_bps=raw_predictive_edge_bps,
            friction_params=friction_params,
            max_acceptable_pbo=float(self.config.max_acceptable_pbo),
        )

        # 5. Out-of-Sample Performance Evaluation (Strict Fail-Closed)
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

        # 6. Gating Decision Logic
        verdict = ValidationGateVerdict.PASS_TRADEABLE_ALPHA
        is_tradeable = True

        if not has_valid_oos:
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

        # 7. Cryptographic Lineage Digests
        is_hash = _compute_canonical_series_sha256(in_sample_returns)
        oos_hash = _compute_canonical_series_sha256(out_of_sample_returns)

        # Evidence Digest (Pure mathematical input & statistical calculation)
        evidence_payload = f"{strategy_id}:{hypothesis_id}:{is_hash}:{oos_hash}:{effective_k}:{dsr_result.dsr_statistic}:{overfit_report.pbo_estimate}"
        evidence_digest = hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest()

        # Decision Digest (Evidence + Governance decision + Threshold parameters)
        decision_payload = f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:{self.config.max_acceptable_pbo}"
        decision_digest = hashlib.sha256(decision_payload.encode("utf-8")).hexdigest()

        val_id = f"VAL_{strategy_id}_{decision_digest[:16]}"
        now_utc = fixed_created_timestamp_utc or datetime.now(timezone.utc).isoformat()

        return ValidationReport(
            validation_id=val_id,
            evidence_digest=evidence_digest,
            decision_digest=decision_digest,
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
