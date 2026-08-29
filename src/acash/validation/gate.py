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
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np


from acash.backtest.schema import BacktestManifest
from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.research.schema import HypothesisSpecification
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
    SharpeSpace,
    ValidationConfig,
    ValidationGateVerdict,
    ValidationReport,
)


def _verify_finite_numeric(v: Any, context: str = "value") -> Decimal:
    """Strict exception-safe finite check validating Decimal and numeric inputs directly."""
    if isinstance(v, Decimal):
        if not v.is_finite():
            raise DataContractError(f"Non-finite Decimal {context} '{v}' (NaN or Inf) encountered.")
        try:
            fv = float(v)
            if not math.isfinite(fv):
                raise DataContractError(
                    f"Decimal {context} '{v}' exceeds float64 representable magnitude boundary."
                )
        except (OverflowError, ValueError) as e:
            raise DataContractError(
                f"Decimal {context} '{v}' exceeds float64 representable magnitude boundary."
            ) from e
        return v
    if isinstance(v, (int, np.integer)):
        return Decimal(str(int(v)))
    if isinstance(v, (float, np.floating)):
        fv = float(v)
        if not math.isfinite(fv):
            raise DataContractError(f"Non-finite float {context} '{v}' (NaN or Inf) encountered.")
        try:
            dec = Decimal(str(fv))
            if not dec.is_finite():
                raise DataContractError(f"Non-finite converted Decimal {context} '{v}' encountered.")
            return dec
        except (InvalidOperation, OverflowError) as e:
            raise DataContractError(f"Invalid numeric {context} '{v}' failed Decimal conversion.") from e
    try:
        dec = Decimal(str(v))
        if not dec.is_finite():
            raise DataContractError(f"Non-finite string/numeric {context} '{v}' encountered.")
        try:
            fv = float(dec)
            if not math.isfinite(fv):
                raise DataContractError(
                    f"Numeric {context} '{v}' exceeds float64 representable magnitude boundary."
                )
        except (OverflowError, ValueError) as e:
            raise DataContractError(
                f"Numeric {context} '{v}' exceeds float64 representable magnitude boundary."
            ) from e
        return dec
    except (InvalidOperation, OverflowError) as e:
        raise DataContractError(f"Invalid numeric representation for {context} '{v}'.") from e


def _compute_canonical_series_sha256(series: Optional[Union[Sequence[Union[Decimal, float]], np.ndarray]]) -> str:
    """Compute deterministic SHA-256 hash using 18-decimal canonical quantization (fixed-point at 10^-18)."""
    if series is None or len(series) == 0:
        return "NONE"

    dec_strings: List[str] = []
    for idx, v in enumerate(series):
        dec = _verify_finite_numeric(v, context=f"return observation at index {idx}")
        dec_strings.append(f"{dec:.18f}")

    raw_payload = ",".join(dec_strings)
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


def _compute_ledger_sha256(ledger: Optional[SearchTrialLedger]) -> str:
    """Compute deterministic SHA-256 hash of SearchTrialLedger records including full candidate lineage."""
    if ledger is None:
        return "NONE"
    return ledger.compute_ledger_digest()


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
        hypothesis_spec: HypothesisSpecification,
        in_sample_returns: Sequence[Union[Decimal, float]],
        trial_matrix_column_trial_ids: Sequence[str],
        manifest_store: Dict[str, BacktestManifest],
        out_of_sample_returns: Optional[Sequence[Union[Decimal, float]]] = None,
        trial_ledger: Optional[SearchTrialLedger] = None,
        trial_return_matrix: Optional[np.ndarray] = None,
        perturbation_grid: Optional[ParameterPerturbationGrid] = None,
        embargo_bars: Optional[int] = None,
        raw_predictive_edge_bps: float = 15.0,
        friction_params: Optional[FrictionStressParameters] = None,
        fixed_created_timestamp_utc: Optional[str] = None,
    ) -> ValidationReport:
        """Run complete statistical validation battery and emit definitive, cryptographically-sealed verdict."""

        # Strict Finite Numerical Data Contract Guards (with true Decimal is_finite validation)
        for idx, r in enumerate(in_sample_returns):
            _verify_finite_numeric(r, context=f"in_sample_returns[{idx}]")
        if out_of_sample_returns is not None:
            for idx, r in enumerate(out_of_sample_returns):
                _verify_finite_numeric(r, context=f"out_of_sample_returns[{idx}]")
        if trial_return_matrix is not None:
            if not np.all(np.isfinite(trial_return_matrix)):
                raise DataContractError("trial_return_matrix contains non-finite values (NaN or Inf).")

        # 0. Mandatory Pre-Registered Hypothesis Specification Sovereign Binding
        if hypothesis_spec is None:
            raise DataContractError("Mandatory hypothesis_spec is required for sovereign statistical validation.")
        if hypothesis_spec.hypothesis_id != hypothesis_id:
            raise DataContractError(
                f"hypothesis_spec hypothesis_id '{hypothesis_spec.hypothesis_id}' does not match evaluate_strategy hypothesis_id '{hypothesis_id}'."
            )
        label_horizon = hypothesis_spec.primary_horizon
        if label_horizon < 1:
            raise DataContractError(f"hypothesis_spec.primary_horizon must be >= 1, got {label_horizon}")
        hyp_spec_hash = hashlib.sha256(hypothesis_spec.to_canonical_json().encode("utf-8")).hexdigest()

        # 1. Search Intensity & Trial Coupling (Strict Pre-Flight Fail-Closed on missing ledger)
        if trial_ledger is None:
            is_hash = _compute_canonical_series_sha256(in_sample_returns)
            oos_hash = _compute_canonical_series_sha256(out_of_sample_returns)
            ev_payload = f"{strategy_id}:{hypothesis_id}:{hyp_spec_hash}:{is_hash}:{oos_hash}:MISSING_TRIAL_LEDGER"
            evidence_digest = hashlib.sha256(ev_payload.encode("utf-8")).hexdigest()

            verdict = ValidationGateVerdict.REJECT_MISSING_TRIAL_LEDGER
            decision_payload = (
                f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
                f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}:{self.config.sharpe_consistency_tolerance}"
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
            ev_payload = f"{strategy_id}:{hypothesis_id}:{hyp_spec_hash}:{is_hash}:MISSING_OOS:{ledger_hash}"
            evidence_digest = hashlib.sha256(ev_payload.encode("utf-8")).hexdigest()
            verdict = ValidationGateVerdict.REJECT_MISSING_OOS_DATA
            decision_payload = (
                f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
                f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}:{self.config.sharpe_consistency_tolerance}"
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
            ev_payload = f"{strategy_id}:{hypothesis_id}:{hyp_spec_hash}:{is_hash}:{oos_hash}:{ledger_hash}:MISSING_PERTURBATION_GRID"
            evidence_digest = hashlib.sha256(ev_payload.encode("utf-8")).hexdigest()
            verdict = ValidationGateVerdict.REJECT_MISSING_PERTURBATION_GRID
            decision_payload = (
                f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
                f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}:{self.config.sharpe_consistency_tolerance}"
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
            ev_payload = f"{strategy_id}:{hypothesis_id}:{hyp_spec_hash}:{is_hash}:{oos_hash}:{ledger_hash}:{grid_hash}:MISSING_CPCV_EVIDENCE"
            evidence_digest = hashlib.sha256(ev_payload.encode("utf-8")).hexdigest()
            verdict = ValidationGateVerdict.REJECT_MISSING_CPCV_EVIDENCE
            decision_payload = (
                f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
                f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}:{self.config.sharpe_consistency_tolerance}"
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

        # 5. In-Sample Observation Sufficiency & Horizon Check
        n_is = len(in_sample_returns)
        if n_is < 4:
            raise DataContractError(f"Insufficient in-sample return observations: {n_is} < 4")

        # Invariant Check: SearchTrialLedger must be in SEALED state with non-null matching digest
        if not trial_ledger.is_sealed:
            raise DataContractError(
                f"SearchTrialLedger '{trial_ledger.ledger_id}' must be in SEALED state before validation. "
                f"Unsealed or open ledgers are strictly prohibited."
            )
        if trial_ledger.ledger_digest is None:
            raise DataContractError(
                f"SearchTrialLedger '{trial_ledger.ledger_id}' is marked is_sealed=True but ledger_digest is None."
            )
        expected_ledger_digest = trial_ledger.compute_ledger_digest()
        if trial_ledger.ledger_digest != expected_ledger_digest:
            raise DataContractError(
                f"SearchTrialLedger '{trial_ledger.ledger_id}' ledger_digest mismatch: "
                f"stored '{trial_ledger.ledger_digest}' != computed '{expected_ledger_digest}'."
            )

        if manifest_store is None or not isinstance(manifest_store, dict):
            raise DataContractError("Mandatory manifest_store dictionary repository is required for sovereign validation.")

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

        # Invariant Check: Primary candidate strategy returns (column 0) must strictly match in_sample_returns via SHA-256
        is_hash = _compute_canonical_series_sha256(in_sample_returns)
        col0_hash = _compute_canonical_series_sha256(trial_return_matrix[:, 0])
        if col0_hash != is_hash:
            raise DataContractError(
                f"trial_return_matrix column 0 return series SHA-256 ({col0_hash}) does not match in_sample_returns SHA-256 ({is_hash}). "
                f"Both DSR and CPCV must evaluate the identical underlying return series."
            )

        # Invariant Check: Mandatory Ordered candidate column trial IDs binding
        if len(trial_matrix_column_trial_ids) != effective_k:
            raise DataContractError(
                f"trial_matrix_column_trial_ids length ({len(trial_matrix_column_trial_ids)}) does not match ledger trial count ({effective_k})."
            )
        expected_ids = [t.trial_id for t in trial_ledger.trials]
        if list(trial_matrix_column_trial_ids) != expected_ids:
            raise DataContractError(
                f"trial_matrix_column_trial_ids {list(trial_matrix_column_trial_ids)} does not match ordered ledger trial_ids {expected_ids}."
            )
        if trial_matrix_column_trial_ids[0] != trial_ledger.trials[0].trial_id:
            raise DataContractError("trial_matrix_column_trial_ids[0] must match the primary evaluated trial record.")

        # Invariant Check: Candidate Return Series, Config & Execution Cryptographic Lineage Verification
        matrix_evidence_elements: List[str] = []
        for m in range(effective_k):
            col_m_hash = _compute_canonical_series_sha256(trial_return_matrix[:, m])
            trial_rec = trial_ledger.trials[m]

            # 1. Candidate Return Series Lineage (Hard Invariant: No None escape hatch!)
            if trial_rec.in_sample_return_series_sha256 != col_m_hash:
                raise DataContractError(
                    f"Trial '{trial_rec.trial_id}' registered in_sample_return_series_sha256 ({trial_rec.in_sample_return_series_sha256}) "
                    f"does not match actual matrix column {m} return series SHA-256 ({col_m_hash})."
                )

            # 2. Candidate Configuration Lineage (Deterministic canonical JSON hash of features & params)
            expected_cfg_hash = SearchTrialRecord.compute_config_sha256(trial_rec.feature_names, trial_rec.parameters)
            if trial_rec.config_sha256 != expected_cfg_hash:
                raise DataContractError(
                    f"Trial '{trial_rec.trial_id}' registered config_sha256 ({trial_rec.config_sha256}) "
                    f"does not match computed parameter/feature configuration SHA-256 ({expected_cfg_hash})."
                )

            # 3. Methodological Sharpe Consistency: Verify recorded ledger Sharpe matches empirical Sharpe of column m
            # within methodological tolerance bound self.config.sharpe_consistency_tolerance
            mean_m = float(np.mean(trial_return_matrix[:, m]))
            std_m = float(np.std(trial_return_matrix[:, m], ddof=1)) if n_is > 1 else 1.0
            sr_m_period = (mean_m / std_m) if std_m > 1e-12 else 0.0
            if trial_ledger.sharpe_space == SharpeSpace.ANNUAL:
                ann_mult = math.sqrt(float(self.config.periods_per_year)) if float(self.config.periods_per_year) > 0 else 1.0
                computed_sr_m = sr_m_period * ann_mult
            else:
                computed_sr_m = sr_m_period

            epsilon_sr = float(self.config.sharpe_consistency_tolerance)
            diff_sr = abs(float(trial_rec.in_sample_sharpe) - computed_sr_m)
            if diff_sr > epsilon_sr:
                raise DataContractError(
                    f"Trial '{trial_rec.trial_id}' registered in_sample_sharpe ({trial_rec.in_sample_sharpe}) "
                    f"exceeds methodological tolerance bound (|SR_ledger - SR_computed| = {diff_sr:.6f} > {epsilon_sr}) "
                    f"against empirical Sharpe ({computed_sr_m:.6f})."
                )

            # 4. Methodological p-value Mathematical and Cryptographic Derivation Verification
            t_stat_m = sr_m_period * math.sqrt(n_is)
            computed_p_m = math.erfc(abs(t_stat_m) / math.sqrt(2.0))
            diff_p = abs(float(trial_rec.p_value) - computed_p_m)
            if diff_p > epsilon_sr:
                raise DataContractError(
                    f"Trial '{trial_rec.trial_id}' registered p_value ({trial_rec.p_value}) "
                    f"exceeds methodological tolerance bound (|p_ledger - p_computed| = {diff_p:.6f} > {epsilon_sr}) "
                    f"against empirical return series two-sided p-value ({computed_p_m:.6f})."
                )

            if trial_rec.p_value_input_hash:
                expected_p_hash = SearchTrialRecord.compute_p_value_input_hash(
                    return_series_sha256=col_m_hash,
                    config_sha256=trial_rec.config_sha256,
                    p_value=trial_rec.p_value,
                    p_value_method=trial_rec.p_value_method,
                )
                if trial_rec.p_value_input_hash != expected_p_hash:
                    raise DataContractError(
                        f"Trial '{trial_rec.trial_id}' p_value_input_hash mismatch: stored '{trial_rec.p_value_input_hash}' != computed '{expected_p_hash}'."
                    )

            # 5. Candidate Execution Lineage (Mandatory BacktestManifest Repository Verification - No Duck Typing!)
            if trial_rec.execution_manifest_id not in manifest_store:
                raise DataContractError(
                    f"Trial '{trial_rec.trial_id}' execution manifest '{trial_rec.execution_manifest_id}' missing from manifest_store repository."
                )
            manifest = manifest_store[trial_rec.execution_manifest_id]
            if not isinstance(manifest, BacktestManifest):
                raise DataContractError(
                    f"Candidate trial '{trial_rec.trial_id}' manifest '{trial_rec.execution_manifest_id}' "
                    f"must be an instance of BacktestManifest, got {type(manifest).__name__}."
                )
            if manifest.manifest_id != trial_rec.execution_manifest_id:
                raise DataContractError(
                    f"Trial '{trial_rec.trial_id}' manifest ID mismatch: expected '{trial_rec.execution_manifest_id}', got '{manifest.manifest_id}'."
                )
            if manifest.hypothesis_id != trial_rec.hypothesis_id:
                raise DataContractError(
                    f"Trial '{trial_rec.trial_id}' manifest hypothesis_id '{manifest.hypothesis_id}' does not match trial hypothesis_id '{trial_rec.hypothesis_id}'."
                )
            if manifest.strategy_config_hash != trial_rec.config_sha256:
                raise DataContractError(
                    f"Trial '{trial_rec.trial_id}' manifest strategy_config_hash '{manifest.strategy_config_hash}' does not match trial config_sha256 '{trial_rec.config_sha256}'."
                )

            # Strict Unconditional Manifest Output Integrity Check
            if manifest.execution_summary is None:
                raise DataContractError(
                    f"Candidate trial '{trial_rec.trial_id}' manifest '{manifest.manifest_id}' has no execution_summary."
                )
            manifest_sr = manifest.execution_summary.sharpe_ratio
            if manifest_sr is None:
                raise DataContractError(
                    f"Candidate trial '{trial_rec.trial_id}' manifest '{manifest.manifest_id}' execution_summary has no sharpe_ratio."
                )
            if abs(float(trial_rec.in_sample_sharpe) - float(manifest_sr)) > epsilon_sr:
                raise DataContractError(
                    f"Candidate trial '{trial_rec.trial_id}' ledger Sharpe ({trial_rec.in_sample_sharpe}) "
                    f"deviates from manifest execution summary Sharpe ({manifest_sr})."
                )

            # Full Cryptographic Binding: Bind candidate return series, config, manifest ID, and manifest artifact hash
            manifest_out_hash = manifest.compute_sha256()
            evidence_item = f"{trial_rec.trial_id}:{trial_rec.config_sha256}:{col_m_hash}:{trial_rec.p_value_input_hash}:{trial_rec.execution_manifest_id}:{manifest_out_hash}"
            matrix_evidence_elements.append(evidence_item)

        matrix_evidence_payload = ";".join(matrix_evidence_elements)
        matrix_evidence_hash = hashlib.sha256(matrix_evidence_payload.encode("utf-8")).hexdigest()

        # 6. Deflated Sharpe Ratio & MinTRL (Authoritative K from ledger with Unified Frequency Scale)
        dsr_result = DeflatedSharpeEngine.evaluate_dsr(
            returns=in_sample_returns,
            effective_trials_k=effective_k,
            confidence_level_alpha=float(self.config.confidence_level_alpha),
            periods_per_year=float(self.config.periods_per_year),
            trial_ledger=trial_ledger,
        )

        # 7. Multiple Testing FWER & Haircut Sharpe (Authoritative K from ledger)
        # Note: Index 0 is the pre-registered primary candidate (bound to in_sample_returns)
        mult_result = MultipleTestingEngine.evaluate_multiple_testing(
            p_values=trial_ledger.p_values,
            estimated_sharpe=float(dsr_result.estimated_sharpe),
            sample_size_t=n_is,
            effective_trials_k=effective_k,
            confidence_level_alpha=float(self.config.confidence_level_alpha),
            primary_candidate_index=0,
            sharpe_space=dsr_result.sharpe_space,
            periods_per_year=float(self.config.periods_per_year),
        )



        # 8. Sovereign CPCV / CSCV Execution with Real Label Horizon & Embargo Buffers
        for pt in perturbation_grid.points:
            if pt.manifest_id not in manifest_store:
                raise DataContractError(
                    f"Perturbation point manifest '{pt.manifest_id}' missing from manifest_store repository."
                )
            man = manifest_store[pt.manifest_id]
            if not isinstance(man, BacktestManifest):
                raise DataContractError(
                    f"Perturbation point '{pt.manifest_id}' manifest must be an instance of BacktestManifest, got {type(man).__name__}."
                )
            pt.validate_manifest_binding(man)

        is_mat, oos_mat = self.cpcv_engine.evaluate_cscv_sharpe_matrices(
            trial_return_matrix,
            label_horizon=label_horizon,
            embargo_bars=embargo_bars,
            periods_per_year=float(self.config.periods_per_year),
        )

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
        raw_oos_sr = (mean_oos / std_oos if std_oos > 0 else 0.0) * math.sqrt(float(self.config.periods_per_year))
        oos_sr = to_decimal18(Decimal(f"{raw_oos_sr:.12f}")) or Decimal("0.0")

        retention_pct: Optional[Decimal] = None
        if dsr_result.estimated_sharpe > Decimal("0.0"):
            ret_val = (oos_sr / dsr_result.estimated_sharpe) * Decimal("100.0")
            retention_pct = to_decimal18(ret_val)


        # 8. Master Verdict Determination
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

        # 11. Cryptographic Lineage Digests (DAG: Evidence -> Decision -> ValidationID)
        oos_hash = _compute_canonical_series_sha256(out_of_sample_returns)
        ledger_hash = _compute_ledger_sha256(trial_ledger)
        grid_hash = _compute_grid_sha256(perturbation_grid)
        effective_embargo = embargo_bars if embargo_bars is not None else self.config.embargo_bars

        # Evidence Digest (Pure mathematical input, research horizon, candidate matrix digest & statistical calculations)
        evidence_payload = (
            f"{strategy_id}:{hypothesis_id}:{hyp_spec_hash}:{is_hash}:{oos_hash}:{ledger_hash}:{grid_hash}:"
            f"{matrix_evidence_hash}:{effective_k}:{label_horizon}:{effective_embargo}:{dsr_result.dsr_statistic}:{overfit_report.pbo_estimate}"
        )
        evidence_digest = hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest()

        # Decision Digest (Evidence + Governance decision + Threshold parameters + Sharpe tolerance)
        decision_payload = (
            f"{evidence_digest}:{verdict.value}:{self.config.min_dsr_probability}:"
            f"{self.config.max_acceptable_pbo}:{self.config.min_oos_sharpe_retention_pct}:{self.config.sharpe_consistency_tolerance}"
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
