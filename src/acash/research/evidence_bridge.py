"""Evidence Bridge: deterministic assembly of Phase 6 evidence inputs from Phase 5 outputs (Phase 14, D8-B).

Ratified D8-B scope (see ``docs/phase14/phase14_evidence_bridge_ratification_D1_D9.md``):

- Minimal capability to assemble truthful Phase 6 evidence inputs from already-produced Phase 5 outputs.
- Uses the canonical equity-derived return series (D2-A/D3) and the single canonical Sharpe authority
  (D7) with the frozen ``ValidationConfig.periods_per_year`` annualization authority (D4).
- Preserves identity / hash / lineage invariants: manifest ``hypothesis_id`` must match the trial's
  declared hypothesis, the manifest ``execution_summary.sharpe_ratio`` must be consistent with the
  canonical Sharpe, and every ``SearchTrialRecord`` is cryptographically bound via the existing
  ``SearchTrialRecord.create`` hash/p-value lineage.

Explicitly NOT authorized in this slice: OOS orchestration, production end-to-end orchestrator,
Phase 8.5 integration, ``AlphaEconomicDecomposition`` producer, ``SearchTrialLedger`` production
orchestration/sealing, CPCV execution, perturbation-run orchestration, live/paper trading, HYP_003,
or R1. This module assembles evidence only; it never seals a census and never invokes a gate.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence, Tuple

import numpy as np
import pyarrow as pa

from acash.backtest.equity_returns import derive_canonical_equity_returns
from acash.backtest.schema import BacktestManifest
from acash.core.domain.exceptions import DataContractError
from acash.validation.deflated_sharpe import calculate_annualized_sharpe
from acash.validation.schema import SearchTrialRecord

MANIFEST_SHARPE_CONSISTENCY_TOLERANCE = Decimal("0.001")


@dataclass(frozen=True)
class BacktestRunEvidence:
    """Canonical Phase 5 output artifact of a single trial execution."""

    trial_id: str
    strategy_id: str
    hypothesis_id: str
    feature_names: Sequence[str]
    parameters: Mapping[str, Any]
    manifest: BacktestManifest
    fills_table: pa.Table
    equity_table: pa.Table


@dataclass(frozen=True)
class PhaseSixEvidenceAssembly:
    """Deterministic, cryptographically-bound assembly of Phase 6 gate evidence inputs.

    Attributes:
        primary_in_sample_returns: Canonical equity-derived returns of the primary (first) trial.
        trial_return_matrix: ``(n_is, K)`` float64 matrix, column ``m`` = canonical returns of trial ``m``.
        trial_matrix_column_trial_ids: Ordered trial ids aligned to the matrix columns.
        manifest_store: ``manifest_id -> BacktestManifest`` repository for gate lineage verification.
        trial_records: Materialized ``SearchTrialRecord`` bindings (no ledger sealing performed here).
        canonical_sharpe_by_trial: Canonical annualized Sharpe per trial id.
    """

    primary_in_sample_returns: Tuple[Decimal, ...]
    trial_return_matrix: np.ndarray
    trial_matrix_column_trial_ids: Tuple[str, ...]
    manifest_store: Mapping[str, BacktestManifest]
    trial_records: Tuple[SearchTrialRecord, ...]
    canonical_sharpe_by_trial: Mapping[str, Decimal]


def assemble_phase_six_evidence(
    runs: Sequence[BacktestRunEvidence],
    periods_per_year: Decimal,
) -> PhaseSixEvidenceAssembly:
    """Assemble truthful Phase 6 evidence inputs from already-produced Phase 5 outputs.

    Args:
        runs: Ordered trial executions (first element is the primary candidate).
        periods_per_year: Frozen annualization authority supplied from ``ValidationConfig`` (D4).

    Returns:
        ``PhaseSixEvidenceAssembly`` with cryptographically bound records, matrix, and manifest store.

    Raises:
        DataContractError: On missing/duplicate trials, empty inputs, lineage mismatches, Sharpe
            emission inconsistency, unequal return-series lengths, non-finite/invalid inputs, or
            insufficient observations (strict fail-closed contract).
    """
    if not runs:
        raise DataContractError("Cannot assemble Phase 6 evidence: no trial runs supplied.")

    trial_ids = [r.trial_id for r in runs]
    if len(set(trial_ids)) != len(trial_ids):
        raise DataContractError(
            f"Cannot assemble Phase 6 evidence: duplicate trial_id(s) detected ({trial_ids})."
        )

    records: list[SearchTrialRecord] = []
    manifest_store: dict[str, BacktestManifest] = {}
    sharpe_by_trial: dict[str, Decimal] = {}
    return_series_by_trial: dict[str, Tuple[Decimal, ...]] = {}

    for run in runs:
        # 1. Lineage: manifest hypothesis identity must match the trial's declared hypothesis.
        if run.manifest.hypothesis_id != run.hypothesis_id:
            raise DataContractError(
                f"Trial '{run.trial_id}' manifest hypothesis_id '{run.manifest.hypothesis_id}' "
                f"does not match declared trial hypothesis_id '{run.hypothesis_id}'."
            )

        if run.manifest.manifest_id in manifest_store:
            raise DataContractError(
                f"Cannot assemble Phase 6 evidence: duplicate manifest_id '{run.manifest.manifest_id}' "
                f"detected for trials '{manifest_store[run.manifest.manifest_id].hypothesis_id}' and '{run.hypothesis_id}'."
            )

        # 2. Canonical equity-derived return series (D2-A / D3) and canonical Sharpe (D7 / D4).
        returns = derive_canonical_equity_returns(run.equity_table)
        sharpe = calculate_annualized_sharpe(returns, periods_per_year)

        # 3. Phase 5 emission consistency: the manifest must carry a non-None execution summary
        #    Sharpe that agrees with the canonical Sharpe authority within the gate's methodological
        #    tolerance (epsilon_sr = 0.001), proving bridge and emission use one math.
        manifest_sr = run.manifest.execution_summary.sharpe_ratio
        if manifest_sr is None:
            raise DataContractError(
                f"Trial '{run.trial_id}' manifest '{run.manifest.manifest_id}' execution_summary has no "
                f"sharpe_ratio; truthful Phase 5 Sharpe emission is required before evidence assembly."
            )
        if abs(manifest_sr - sharpe) > MANIFEST_SHARPE_CONSISTENCY_TOLERANCE:
            raise DataContractError(
                f"Trial '{run.trial_id}' manifest execution summary Sharpe ({manifest_sr}) "
                f"deviates from canonical Sharpe ({sharpe}) beyond tolerance "
                f"({MANIFEST_SHARPE_CONSISTENCY_TOLERANCE})."
            )

        # 4. Cryptographic SearchTrialRecord materialization (p-value + return-series + config hashes).
        record = SearchTrialRecord.create(
            trial_id=run.trial_id,
            strategy_id=run.strategy_id,
            hypothesis_id=run.hypothesis_id,
            feature_names=run.feature_names,
            parameters=run.parameters,
            in_sample_sharpe=sharpe,
            execution_manifest_id=run.manifest.manifest_id,
            in_sample_returns=returns,
        )

        records.append(record)
        manifest_store[run.manifest.manifest_id] = run.manifest
        sharpe_by_trial[run.trial_id] = sharpe
        return_series_by_trial[run.trial_id] = tuple(returns)

    # 5. Strict equal-length matrix contract: every column MUST share the same observation count
    #    (no silent truncation, interpolation, or padding — Phase 6 requires equal n_is).
    expected_n = len(return_series_by_trial[trial_ids[0]])
    for tid in trial_ids:
        observed_n = len(return_series_by_trial[tid])
        if observed_n != expected_n:
            raise DataContractError(
                f"Cannot assemble Phase 6 evidence: trial '{tid}' return series length {observed_n} "
                f"does not match primary trial length {expected_n}; equal observation counts are required."
            )

    matrix = np.asarray(
        [[float(r) for r in return_series_by_trial[tid]] for tid in trial_ids],
        dtype=np.float64,
    ).T
    if matrix.shape != (expected_n, len(trial_ids)):
        raise DataContractError(
            f"Cannot assemble Phase 6 evidence: unexpected trial matrix shape "
            f"{matrix.shape} (expected ({expected_n}, {len(trial_ids)}))."
        )

    return PhaseSixEvidenceAssembly(
        primary_in_sample_returns=return_series_by_trial[trial_ids[0]],
        trial_return_matrix=matrix,
        trial_matrix_column_trial_ids=tuple(trial_ids),
        manifest_store=manifest_store,
        trial_records=tuple(records),
        canonical_sharpe_by_trial=sharpe_by_trial,
    )