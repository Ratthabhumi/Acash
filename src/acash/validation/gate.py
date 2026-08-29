"""Statistical Validation Gate Orchestrator (Phase 6).

Implements the master validation gate enforcing:
1. Deflated Sharpe Ratio & MinTRL significance with strict Search Trial Ledger coupling:
   K_ledger == |unique trial_id| == |p_values| == K_DSR == K_Holm == K_BH == K_Haircut.
2. Combinatorial Purged Cross-Validation PBO bounds with mid-rank tie handling.
3. Parameter sensitivity curvature & stability on strict +/- 25% perturbation grids with cryptographic lineage proof.
4. Component-wise analytical friction decay monotonicity.
5. Sealed blind Out-of-Sample (OOS) performance retention (Strict Fail-Closed).
6. Sovereign cryptographic DAG: evidence_digest (pure evidence) -> decision_digest (evidence + governance) -> validation_id.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Union

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
    ParameterPerturbationPoint,
    SearchTrialLedger,
    SearchTrialRecord,
    SelectionCorrectionMode,
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


def _compute_ledger_sha256(ledger: Optional[SearchTrialLedger]) -> str:
    """Compute deterministic SHA-256 hash of SearchTrialLedger records."""
    if ledger is None:
        return "NONE"
    items = [
        f"{t.trial_id}:{t.strategy_id}:{t.hypothesis_id}:{Decimal(str(t.in_sample_sharpe)):.18f}:{Decimal(str(t.p_value)):.18f}"
        for t in ledger.trials
    ]
    raw_payload = f"{ledger.ledger_id}:{ledger.strategy_id}:{ledger.hypothesis_id}:" + ";".join(items)
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


def _compute_grid_sha256(grid: Optional[ParameterPerturbationGrid]) -> str:
    """Compute deterministic SHA-256 hash of ParameterPerturbationGrid execution points."""
    if grid is None:
        return "NONE"
    items = [
        f"{p.parameter_value}:{p.run_id}:{p.manifest_id}:{p.input_artifact_hash}:{p.output_artifact_hash}:{Decimal(str(p.actual_sharpe)):.18f}"
        for p in grid.points
    ]
    raw_payload = f"{grid.base_parameter_name}:{grid.base_parameter_value}:" + ";".join(items)
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


class StatisticalValidationGate:
    """Master orchestrator for Phase 6 Statistical Validation & Overfitting Controls.

    SOVEREIGN GOVERNANCE AUTHORITY:
    This class is the SOLE sovereign governance authority for Gate 6 validation decisions.
    Standalone engines (DeflatedSharpeEngine, MultipleTestingEngine, OverfittingEngine) are
    low-level mathematical primitives; their standalone invocation does NOT constitute a Gate 6 validation decision.
    """

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
        trial_return_matrix: Optional[np.ndarray] = None,
        perturbation_grid: Optional[ParameterPerturbationGrid] = None,
        manifest_store: Optional[Dict[str, Any]] = None,
        raw_predictive_edge_bps: float = 15.0,
        friction_params: Optional[FrictionStressParameters] = None,
        fixed_created_timestamp_utc: Optional[str] = None,
    ) -> ValidationReport:
        """Run complete statistical validation battery and emit definitive, cryptographically-sealed verdict."""

        # 1. Search Intensity & Trial Coupling (Strict Pre-Flight Fail-Closed on missing ledger)
        if trial_ledger is None:
            is_hash = _compute_canonical_series_sha256(in_sample_returns)
            oos_hash = _compute_canonical_series_sha256(out_of_sample_returns)
            ev_payload = f"{strategy_id}:{hypothesis_id}:{is_hash}:{oos_hash}:MISSING_TRIAL_LEDGER"
            evidence_digest = hashlib.sha256(ev_payload.encode("utf-8")).hexdigest()

            verdict = ValidationGateVerdict.REJECT_MISSING_TRIAL_LEDGER
            decision_payload = (
                f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
                f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}"
            )
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
                is_tradeable_alpha=False,
                dsr_result=None,
                multiple_testing_result=None,
                overfitting_report=None,
                in_sample_sharpe=None,
                out_of_sample_sharpe=None,
                oos_retention_pct=None,
                created_timestamp_utc=now_utc,
            )

        # 2. Out-of-Sample Requirement (Strict Fail-Closed before evaluation)
        if out_of_sample_returns is None or len(out_of_sample_returns) < 4:
            is_hash = _compute_canonical_series_sha256(in_sample_returns)
            ledger_hash = _compute_ledger_sha256(trial_ledger)
            ev_payload = f"{strategy_id}:{hypothesis_id}:{is_hash}:MISSING_OOS:{ledger_hash}"
            evidence_digest = hashlib.sha256(ev_payload.encode("utf-8")).hexdigest()
            verdict = ValidationGateVerdict.REJECT_MISSING_OOS_DATA
            decision_payload = (
                f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
                f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}"
            )
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
                is_tradeable_alpha=False,
                dsr_result=None,
                multiple_testing_result=None,
                overfitting_report=None,
                in_sample_sharpe=None,
                out_of_sample_sharpe=None,
                oos_retention_pct=None,
                created_timestamp_utc=now_utc,
            )

        # 3. Parameter Perturbation Lineage Requirement (Strict Fail-Closed on missing grid)
        if perturbation_grid is None:
            is_hash = _compute_canonical_series_sha256(in_sample_returns)
            oos_hash = _compute_canonical_series_sha256(out_of_sample_returns)
            ledger_hash = _compute_ledger_sha256(trial_ledger)
            ev_payload = f"{strategy_id}:{hypothesis_id}:{is_hash}:{oos_hash}:{ledger_hash}:MISSING_PERTURBATION_GRID"
            evidence_digest = hashlib.sha256(ev_payload.encode("utf-8")).hexdigest()
            verdict = ValidationGateVerdict.REJECT_MISSING_PERTURBATION_GRID
            decision_payload = (
                f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
                f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}"
            )
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
                is_tradeable_alpha=False,
                dsr_result=None,
                multiple_testing_result=None,
                overfitting_report=None,
                in_sample_sharpe=None,
                out_of_sample_sharpe=None,
                oos_retention_pct=None,
                created_timestamp_utc=now_utc,
            )

        # 4. Mandatory CPCV / CSCV Empirical Evidence Requirement (Strict Fail-Closed without surrogate fallback)
        if trial_return_matrix is None:
            is_hash = _compute_canonical_series_sha256(in_sample_returns)
            oos_hash = _compute_canonical_series_sha256(out_of_sample_returns)
            ledger_hash = _compute_ledger_sha256(trial_ledger)
            grid_hash = _compute_grid_sha256(perturbation_grid)
            ev_payload = f"{strategy_id}:{hypothesis_id}:{is_hash}:{oos_hash}:{ledger_hash}:{grid_hash}:MISSING_CPCV_EVIDENCE"
            evidence_digest = hashlib.sha256(ev_payload.encode("utf-8")).hexdigest()
            verdict = ValidationGateVerdict.REJECT_MISSING_CPCV_EVIDENCE
            decision_payload = (
                f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
                f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}"
            )
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
                is_tradeable_alpha=False,
                dsr_result=None,
                multiple_testing_result=None,
                overfitting_report=None,
                in_sample_sharpe=None,
                out_of_sample_sharpe=None,
                oos_retention_pct=None,
                created_timestamp_utc=now_utc,
            )

        # 5. In-Sample Observation Sufficiency Check (Evaluated after all prerequisites are verified)
        n_is = len(in_sample_returns)
        if n_is < 4:
            raise DataContractError(f"Insufficient in-sample return observations: {n_is} < 4")

        # Enforce strict Authoritative Ledger Invariants:
        # K_ledger == |unique trial_id| == |p-values| == K_DSR == K_Holm == K_BH == K_Haircut == M_CPCV
        effective_k = trial_ledger.total_trials

        if effective_k < 1:
            raise DataContractError(f"SearchTrialLedger must contain at least 1 trial, got {effective_k}")
        if len(trial_ledger.trials) != effective_k:
            raise DataContractError(f"Ledger trials length mismatch: {len(trial_ledger.trials)} != {effective_k}")
        if len(trial_ledger.p_values) != effective_k:
            raise DataContractError(f"Ledger p_values length mismatch: {len(trial_ledger.p_values)} != {effective_k}")
        unique_ids = {t.trial_id for t in trial_ledger.trials}
        if len(unique_ids) != effective_k:
            raise DataContractError(f"Ledger contains duplicate trial_ids: {len(unique_ids)} unique != {effective_k} total")

        # Invariant Check: trial_return_matrix candidate universe coupling (M == K_ledger)
        if trial_return_matrix.ndim != 2:
            raise DataContractError(
                f"trial_return_matrix must be 2D array of shape (T, M), got ndim={trial_return_matrix.ndim}"
            )
        t_matrix, m_matrix = trial_return_matrix.shape
        if m_matrix != effective_k:
            raise DataContractError(
                f"trial_return_matrix candidate count M ({m_matrix}) does not match SearchTrialLedger K ({effective_k}). "
                f"PBO search universe must strictly equal the authoritative trial ledger universe."
            )
        if t_matrix != n_is:
            raise DataContractError(
                f"trial_return_matrix observation count T ({t_matrix}) does not match in_sample_returns length ({n_is})."
            )

        # Invariant Check: Primary candidate strategy returns (column 0) must strictly match in_sample_returns
        is_floats = np.array([float(x) for x in in_sample_returns], dtype=np.float64)
        if not np.allclose(trial_return_matrix[:, 0], is_floats, atol=1e-7, rtol=1e-5):
            raise DataContractError(
                "trial_return_matrix column 0 (primary candidate strategy) does not match in_sample_returns observations. "
                "Both DSR and CPCV must evaluate identical underlying return series."
            )

        all_p_values = trial_ledger.p_values

        # 6. Deflated Sharpe Ratio & MinTRL (Authoritative K from ledger)
        dsr_result = DeflatedSharpeEngine.evaluate_dsr(
            returns=in_sample_returns,
            effective_trials_k=effective_k,
            confidence_level_alpha=float(self.config.confidence_level_alpha),
            trial_ledger=trial_ledger,
        )

        # 7. Multiple Testing FWER & Haircut Sharpe (Authoritative K from ledger)
        mult_result = MultipleTestingEngine.evaluate_multiple_testing(
            p_values=all_p_values,
            estimated_sharpe=float(dsr_result.estimated_sharpe),
            sample_size_t=n_is,
            effective_trials_k=effective_k,
            confidence_level_alpha=float(self.config.confidence_level_alpha),
        )

        # 8. Sovereign CPCV / CSCV Execution & Overfitting Battery
        if manifest_store is not None:
            for pt in perturbation_grid.points:
                if pt.manifest_id not in manifest_store:
                    raise DataContractError(
                        f"Perturbation point manifest '{pt.manifest_id}' missing from manifest_store repository."
                    )
                pt.validate_manifest_binding(manifest_store[pt.manifest_id])

        is_mat, oos_mat = self.cpcv_engine.evaluate_cscv_sharpe_matrices(trial_return_matrix)

        overfit_report = OverfittingEngine.evaluate_overfitting_battery(
            is_sharpe_matrix=is_mat,
            oos_sharpe_matrix=oos_mat,
            perturbation_grid=perturbation_grid,
            raw_predictive_edge_bps=raw_predictive_edge_bps,
            friction_params=friction_params,
            max_acceptable_pbo=float(self.config.max_acceptable_pbo),
        )


        # 9. Out-of-Sample Performance Evaluation
        mean_oos, std_oos, _, _ = DeflatedSharpeEngine.calculate_higher_moments(out_of_sample_returns)
        raw_oos_sr = mean_oos / std_oos if std_oos > 0 else 0.0
        oos_sr = to_decimal18(Decimal(f"{raw_oos_sr:.12f}")) or Decimal("0.0")

        retention_pct: Optional[Decimal] = None
        if dsr_result.estimated_sharpe > Decimal("0.0"):
            ret_val = (oos_sr / dsr_result.estimated_sharpe) * Decimal("100.0")
            retention_pct = to_decimal18(ret_val)

        # 10. Gating Decision Logic (Sequential Sovereign Arbiter)
        verdict = ValidationGateVerdict.PASS_TRADEABLE_ALPHA
        is_tradeable = True

        if not dsr_result.is_statistically_significant:
            verdict = ValidationGateVerdict.REJECT_OVERFIT_DSR
            is_tradeable = False
        elif not dsr_result.has_sufficient_track_record:
            verdict = ValidationGateVerdict.REJECT_INSUFFICIENT_TRL
            is_tradeable = False
        elif self.config.enforce_fwer_significance and not mult_result.is_fwer_significant:
            verdict = ValidationGateVerdict.REJECT_MULTIPLE_TESTING_FWER
            is_tradeable = False
        elif mult_result.haircut_sharpe_ratio < self.config.min_haircut_sharpe:
            verdict = ValidationGateVerdict.REJECT_HAIRCUT_SHARPE
            is_tradeable = False
        elif not overfit_report.is_pbo_acceptable:
            verdict = ValidationGateVerdict.REJECT_HIGH_PBO
            is_tradeable = False
        elif not overfit_report.is_parameter_stable:
            verdict = ValidationGateVerdict.REJECT_PARAMETER_FRAGILE
            is_tradeable = False
        elif not overfit_report.analytical_friction_monotonicity_passed:
            verdict = ValidationGateVerdict.REJECT_FRICTION_COLLAPSE
            is_tradeable = False
        elif retention_pct is not None and retention_pct < self.config.min_oos_sharpe_retention_pct:
            verdict = ValidationGateVerdict.REJECT_OOS_DEGRADATION
            is_tradeable = False



        # 7. Cryptographic Lineage Digests (DAG: Evidence -> Decision -> ValidationID)
        is_hash = _compute_canonical_series_sha256(in_sample_returns)
        oos_hash = _compute_canonical_series_sha256(out_of_sample_returns)
        ledger_hash = _compute_ledger_sha256(trial_ledger)
        grid_hash = _compute_grid_sha256(perturbation_grid)

        # Evidence Digest (Pure mathematical input & statistical calculation - NO governance decision)
        evidence_payload = (
            f"{strategy_id}:{hypothesis_id}:{is_hash}:{oos_hash}:{ledger_hash}:{grid_hash}:"
            f"{effective_k}:{dsr_result.dsr_statistic}:{overfit_report.pbo_estimate}"
        )
        evidence_digest = hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest()

        # Decision Digest (Evidence + Governance decision + Threshold parameters)
        decision_payload = (
            f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
            f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}"
        )
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
