"""Phase 5 Production Research & Evidence Orchestration (Phase 14, frozen D6 contract).

Ratified scope (see ``docs/phase14/phase14_d5_d6_ratification_record.md`` and
``docs/phase14/phase5_production_orchestration_readiness.md``):

- Executes a FROZEN, pre-registered census of strategy trials in declared order against the
  canonical in-sample (TRAIN + VAL, inclusive, embargo-buffered) event segment, using a fresh
  ``EventBacktestRunner`` per trial so every trial is an independent execution.
- Never invents evidence, never shrinks K, never substitutes a "successful count". FAILED and
  INVALID trials REMAIN census members with NO evidence (D6 Option A). A mixed census is sealed
  truthfully and Phase 6 is BLOCKED (no complete statistical evidence exists).
- On an all-successful census, assembles Phase 6 gate evidence through the canonical
  ``assemble_phase_six_evidence`` Evidence Bridge (single authority on return-record construction),
  seals the ledger via ``SearchTrialCensusSealAuthority.seal_census(expected_k=
  planned_trial_count)`` (the SOLE sanctioned sealer), runs the canonical 3-point parameter
  perturbation grid (exact 0.75/1.0/1.25 * theta geometry, distinct executions), builds the
  separate held-out OOS evidence via ``build_oos_backtest_evidence`` (D5: fresh runner, PIT
  fail-closed, no-reuse invariant), and invokes the ``StatisticalValidationGate``.
- Reports a structured, immutable ``PhaseFiveOrchestrationReport``.

Explicitly NOT authorized here: HYP_003 inception, R1 admission, ResearchReInceptionGate,
AlphaQualificationGate, live/paper trading, broker/capital interaction, or any ``ledger.seal()``
invocation outside ``SearchTrialCensusSealAuthority``. Gate exceptions PROPAGATE (never swallowed).
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import hashlib
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field

from acash.backtest.adapter import BacktestMarketEvent, extract_nanoseconds_from_scalar
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.equity_returns import derive_canonical_equity_returns
from acash.backtest.schema import BacktestEngineConfig, BacktestManifest
from acash.core.domain.exceptions import DataContractError
from acash.research.census_seal_authority import SearchTrialCensusSealAuthority
from acash.research.evidence_bridge import (
    MANIFEST_SHARPE_CONSISTENCY_TOLERANCE,
    BacktestRunEvidence,
    assemble_phase_six_evidence,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.oos_provenance import (
    OosEvidenceRecord,
    PitLineageAttestation,
    build_oos_backtest_evidence,
    resolve_partition_ranges,
)
from acash.research.schema import HypothesisSpecification, SplitPolicy
from acash.validation.deflated_sharpe import calculate_annualized_sharpe
from acash.validation.gate import StatisticalValidationGate
from acash.validation.schema import (
    ParameterPerturbationGrid,
    ParameterPerturbationPoint,
    SearchTrialLedger,
    SearchTrialRecord,
    SearchTrialStatus,
    SharpeSpace,
    ValidationConfig,
    ValidationReport,
)

# Actor contract: a factory taking the RESOLVED parameter mapping for the run and returning a
# strategy actor instance exposing ``on_bar(event, runner)`` / ``on_trade(event, runner)``.
ActorFactory = Callable[[Mapping[str, Any]], Any]


class CensusState(str, Enum):
    """D6 census outcome for an orchestrated pre-registered search census."""

    SEALED_COMPLETE = "SEALED_COMPLETE"
    SEALED_MIXED = "SEALED_MIXED"


@dataclass(frozen=True)
class TrialSpec:
    """Frozen pre-registered trial identity (D6 census membership)."""

    trial_id: str
    feature_names: Sequence[str]
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class PerturbationSpec:
    """Frozen parameter perturbation spec bound to the primary trial config identity."""

    base_parameter_name: str
    base_parameter_value: Decimal


@dataclass(frozen=True)
class FrozenResearchPlan:
    """Immutable pre-registration mesh consumed by the Phase 5 production orchestrator.

    Every input is frozen BEFORE census execution (frozen-decision contract): the ordered trial
    census, the hypothesis identity, the execution/engine config, the canonical dataset (rows +
    events + PIT attestation), the partition policy, the annualization authority, the gate policy,
    and the optional perturbation spec.
    """

    plan_id: str
    strategy_id: str
    hypothesis_id: str
    hypothesis_spec: HypothesisSpecification
    trials: Tuple[TrialSpec, ...]
    engine_config: BacktestEngineConfig
    canonical_data_hashes: Tuple[str, ...]
    pyproject_toml_sha256: str
    git_commit_hash: str
    periods_per_year: Decimal
    split_policy: SplitPolicy
    validation_config: ValidationConfig
    rows_table: pa.Table
    events: Tuple[BacktestMarketEvent, ...]
    pit_attestation: PitLineageAttestation
    dataset_id: str
    dataset_version: str
    perturbation_spec: Optional[PerturbationSpec] = None


class PhaseFiveOrchestrationReport(BaseModel):
    """Immutable structured audit certificate for a Phase 5 orchestration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    strategy_id: str
    hypothesis_id: str
    planned_trial_count: int
    actual_trial_count: int
    ordered_trial_ids: Tuple[str, ...]
    successful_count: int
    failed_count: int
    invalid_count: int
    census_state: CensusState
    ledger_id: str
    ledger_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    sealed_by_owner: str
    perturbation_runs_executed: int
    perturbation_grid: Optional[ParameterPerturbationGrid] = None
    oos_record: Optional[OosEvidenceRecord] = None
    oos_return_series_sha256: Optional[str] = None
    phase_six_invoked: bool
    phase_six_report: Optional[ValidationReport] = None
    manifest_store: Optional[Mapping[str, BacktestManifest]] = None
    blocked_reason: Optional[str] = None
    sealed_ledger: Optional[SearchTrialLedger] = None


@dataclass(frozen=True)
class _TrialExecutionResult:
    """Internal outcome of a single census trial execution (never exposed)."""

    trial_id: str
    feature_names: Sequence[str]
    parameters: Mapping[str, Any]
    status: SearchTrialStatus
    evidence: Optional[BacktestRunEvidence]
    failure_reason: Optional[str]
    config_sha256: str


def _deterministic_failure_reason(exc: BaseException) -> str:
    """Derive a deterministic non-empty failure reason from an execution exception."""
    category = type(exc).__name__
    raw = str(exc).strip()
    detail = (raw.splitlines()[0] if raw else category)[:200]
    if detail and detail != category:
        return f"{category}: {detail}"
    return category


class PhaseFiveResearchOrchestrator:
    """Production orchestrator executing a frozen Phase 5 census through Phase 6 evidence.

    The single point of production orchestration in this repository. It composes existing
    canonical authorities (D3 returns, D7 Sharpe, D4 annualization, Evidence Bridge, seal
    authority, D5 OOS, Phase 6 gate) and enforces the D6 statistical-semantics contract:
    census K is frozen, FAILED/INVALID trials keep their census membership with NO evidence, and
    Phase 6 is only reachable with a fully executed census.
    """

    LEDGER_ID_PREFIX = "CENSUS"

    def orchestrate(
        self,
        plan: FrozenResearchPlan,
        actor_factory: ActorFactory,
        oos_actor_factory: ActorFactory,
    ) -> PhaseFiveOrchestrationReport:
        """Execute the frozen plan and emit the structured Phase 5 orchestration report."""
        self._validate_plan(plan)
        self._probe_actor_factories(plan, actor_factory, oos_actor_factory)
        hypothesis_spec_sha256 = calculate_hypothesis_spec_sha256(plan.hypothesis_spec)
        is_events = self._resolve_is_events(plan)

        results = tuple(
            self._execute_census_trial(trial, plan, actor_factory, is_events, hypothesis_spec_sha256)
            for trial in plan.trials
        )
        successful = [r for r in results if r.status == SearchTrialStatus.EXECUTED_SUCCESSFULLY]
        all_success = len(successful) == len(plan.trials)

        # 1. Census ledger assembly (single authority on return-record construction).
        if all_success:
            runs: list[BacktestRunEvidence] = []
            for r in results:
                if r.evidence is None:
                    raise DataContractError(
                        f"Successful trial '{r.trial_id}' carries no evidence in census assembly."
                    )
                runs.append(r.evidence)
            assembly = assemble_phase_six_evidence(runs, plan.periods_per_year)
            self._assert_success_lineage(results, assembly.trial_records)
            ledger_records = assembly.trial_records
        else:
            ledger_records = self._build_mixed_ledger_records(results, plan, plan.periods_per_year)

        # 2. Census sealing through the SOLE sanctioned authority (never a bare ledger.seal()).
        ledger = SearchTrialLedger(
            ledger_id=f"{self.LEDGER_ID_PREFIX}_{plan.strategy_id}_{plan.hypothesis_id}",
            strategy_id=plan.strategy_id,
            hypothesis_id=plan.hypothesis_id,
            sharpe_space=SharpeSpace.ANNUAL,
            trials=tuple(ledger_records),
        )
        sealed = SearchTrialCensusSealAuthority.seal_census(
            ledger, expected_k=len(plan.trials)
        )
        if sealed.ledger_digest is None:
            raise DataContractError(
                f"Sealed census '{sealed.ledger_id}' carries no ledger_digest after authoritative sealing."
            )
        if not sealed.sealed_by_owner:
            raise DataContractError(
                f"Sealed census '{sealed.ledger_id}' carries no sealed_by_owner after authoritative sealing."
            )

        failed_count = sum(1 for r in results if r.status == SearchTrialStatus.FAILED)
        invalid_count = sum(1 for r in results if r.status == SearchTrialStatus.INVALID)

        if not all_success:
            blocked = (
                f"MIXED CENSUS FAILED CLOSED (D6): {failed_count} FAILED + {invalid_count} INVALID "
                f"of {len(plan.trials)} frozen trials. K={len(plan.trials)} never shrinks and no "
                f"complete statistical evidence exists; Phase 6, perturbation, and OOS are NOT invoked."
            )
            return PhaseFiveOrchestrationReport(
                plan_id=plan.plan_id,
                strategy_id=plan.strategy_id,
                hypothesis_id=plan.hypothesis_id,
                planned_trial_count=len(plan.trials),
                actual_trial_count=len(plan.trials),
                ordered_trial_ids=tuple(t.trial_id for t in plan.trials),
                successful_count=len(successful),
                failed_count=failed_count,
                invalid_count=invalid_count,
                census_state=CensusState.SEALED_MIXED,
                ledger_id=ledger.ledger_id,
                ledger_digest=sealed.ledger_digest,
                sealed_by_owner=sealed.sealed_by_owner,
                perturbation_runs_executed=0,
                phase_six_invoked=False,
                blocked_reason=blocked,
                sealed_ledger=sealed,
            )

        # 3. Parameter perturbation (all-success only): exact 0.75/1.0/1.25 * theta geometry.
        manifest_store: Dict[str, BacktestManifest] = dict(assembly.manifest_store)
        perturbation_grid: Optional[ParameterPerturbationGrid] = None
        perturbation_runs_executed = 0
        if plan.perturbation_spec is not None:
            perturbation_grid, perturb_manifests = self._run_perturbation(
                plan, actor_factory, is_events, hypothesis_spec_sha256
            )
            perturbation_runs_executed = len(perturbation_grid.points)
            for point in perturbation_grid.points:
                manifest_store[point.manifest_id] = perturb_manifests[point.run_id]

        # 4. Separate held-out OOS evidence (D5): fresh runner, PIT fail-closed, no-reuse bound.
        oos_record, _oos_manifest, _oos_fills, _oos_equity, oos_returns = build_oos_backtest_evidence(
            rows_table=plan.rows_table,
            source_kind=plan.pit_attestation.source_kind,
            events=plan.events,
            strategy_id=plan.strategy_id,
            hypothesis_id=plan.hypothesis_id,
            split_policy=plan.split_policy,
            engine_config=plan.engine_config,
            strategy_actor=oos_actor_factory(dict(plan.trials[0].parameters)),
            periods_per_year=plan.periods_per_year,
            hypothesis_spec_sha256=hypothesis_spec_sha256,
            strategy_config_hash=assembly.trial_records[0].config_sha256,
            pyproject_toml_sha256=plan.pyproject_toml_sha256,
            git_commit_hash=plan.git_commit_hash,
            in_sample_returns=assembly.primary_in_sample_returns,
            pit_attestation=plan.pit_attestation,
            dataset_id=plan.dataset_id,
            dataset_version=plan.dataset_version,
        )

        # 5. Phase 6 gate: sealed ledger, matrix aligned to ordered census trial_ids, perturbation
        #    and trial manifests bound, OOS from the independent run. Gate errors PROPAGATE.
        gate = StatisticalValidationGate(plan.validation_config)
        phase_six_report = gate.evaluate_strategy(
            strategy_id=plan.strategy_id,
            hypothesis_id=plan.hypothesis_id,
            hypothesis_spec=plan.hypothesis_spec,
            in_sample_returns=assembly.primary_in_sample_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=sealed,
            trial_return_matrix=assembly.trial_return_matrix,
            trial_matrix_column_trial_ids=assembly.trial_matrix_column_trial_ids,
            perturbation_grid=perturbation_grid,
            manifest_store=manifest_store,
            embargo_bars=plan.split_policy.embargo_bars,
            raw_predictive_edge_bps=15.0,
            friction_params=None,
        )

        return PhaseFiveOrchestrationReport(
            plan_id=plan.plan_id,
            strategy_id=plan.strategy_id,
            hypothesis_id=plan.hypothesis_id,
            planned_trial_count=len(plan.trials),
            actual_trial_count=len(plan.trials),
            ordered_trial_ids=tuple(t.trial_id for t in plan.trials),
            successful_count=len(successful),
            failed_count=0,
            invalid_count=0,
            census_state=CensusState.SEALED_COMPLETE,
            ledger_id=ledger.ledger_id,
            ledger_digest=sealed.ledger_digest,
            sealed_by_owner=sealed.sealed_by_owner,
            perturbation_runs_executed=perturbation_runs_executed,
            perturbation_grid=perturbation_grid,
            oos_record=oos_record,
            oos_return_series_sha256=oos_record.oos_return_series_sha256,
            phase_six_invoked=True,
            phase_six_report=phase_six_report,
            manifest_store=manifest_store,
            sealed_ledger=sealed,
        )

    # ------------------------------------------------------------------
    # Preflight
    # ------------------------------------------------------------------

    def _validate_plan(self, plan: FrozenResearchPlan) -> None:
        if not plan.trials:
            raise DataContractError(
                "Cannot orchestrate an empty pre-registered census: at least one trial is required."
            )
        trial_ids = [t.trial_id for t in plan.trials]
        if len(set(trial_ids)) != len(trial_ids):
            raise DataContractError(
                f"Plan '{plan.plan_id}' contains duplicate trial_ids; the census must be unique: {trial_ids}."
            )
        if plan.hypothesis_spec.hypothesis_id != plan.hypothesis_id:
            raise DataContractError(
                f"Plan '{plan.plan_id}' hypothesis_spec.hypothesis_id '{plan.hypothesis_spec.hypothesis_id}' "
                f"does not match the declared hypothesis_id '{plan.hypothesis_id}'."
            )
        if plan.periods_per_year != plan.validation_config.periods_per_year:
            raise DataContractError(
                f"Annualization authority contradiction for plan '{plan.plan_id}': "
                f"periods_per_year={plan.periods_per_year} != validation_config.periods_per_year="
                f"{plan.validation_config.periods_per_year}; the D4 annualization authority must be single."
            )
        pct_sum = plan.split_policy.train_pct + plan.split_policy.val_pct + plan.split_policy.oos_pct
        if pct_sum != Decimal("1.0"):
            raise DataContractError(
                f"SplitPolicy fractions for plan '{plan.plan_id}' sum to {pct_sum} != 1.0; "
                f"the frozen partition must allocate 100% of the dataset."
            )
        if tuple(plan.pit_attestation.canonical_data_hashes) != plan.canonical_data_hashes:
            raise DataContractError(
                f"Plan '{plan.plan_id}' PitLineageAttestation canonical_data_hashes do not match the "
                f"declared canonical_data_hashes; census and OOS must bind to identical data lineage."
            )
        if (
            plan.dataset_id != plan.pit_attestation.dataset_id
            or plan.dataset_version != plan.pit_attestation.dataset_version
        ):
            raise DataContractError(
                f"Plan '{plan.plan_id}' dataset identity (v{plan.dataset_version}) does not match the "
                f"PitLineageAttestation dataset identity (v{plan.pit_attestation.dataset_version})."
            )
        if plan.rows_table is None or plan.rows_table.num_rows < 2 or not plan.events:
            raise DataContractError(
                f"Plan '{plan.plan_id}' requires a canonical bars table with >= 2 rows and a "
                f"non-empty canonical event stream."
            )
        if plan.perturbation_spec is not None:
            base = plan.perturbation_spec
            primary = plan.trials[0]
            if base.base_parameter_name not in primary.parameters:
                raise DataContractError(
                    f"PerturbationSpec base parameter '{base.base_parameter_name}' is not present in "
                    f"the primary trial '{primary.trial_id}' parameters; the perturbation must be bound "
                    f"to the primary candidate config identity."
                )
            primary_value = primary.parameters[base.base_parameter_name]
            if not isinstance(primary_value, Decimal) or primary_value <= Decimal("0.0"):
                raise DataContractError(
                    f"PerturbationSpec requires the primary parameter '{base.base_parameter_name}' to "
                    f"be a positive Decimal base theta_0; got {primary_value!r}."
                )
            if base.base_parameter_value != primary_value:
                raise DataContractError(
                    f"PerturbationSpec base_parameter_value {base.base_parameter_value} must exactly "
                    f"equal the primary trial theta_0 {primary_value}; single config identity required."
                )

    def _probe_actor_factories(
        self,
        plan: FrozenResearchPlan,
        actor_factory: ActorFactory,
        oos_actor_factory: ActorFactory,
    ) -> None:
        primary_params = dict(plan.trials[0].parameters)
        probe_a = actor_factory(primary_params)
        if not callable(getattr(probe_a, "on_bar", None)):
            raise DataContractError(
                "actor_factory must return a strategy actor exposing on_bar(event, runner)."
            )
        probe_b = actor_factory(primary_params)
        if probe_b is probe_a:
            raise DataContractError(
                "actor_factory must return a NEW actor instance per call; returning a shared "
                "mutable instance violates the fresh-runner/fresh-state isolation contract."
            )
        oos_probe = oos_actor_factory(primary_params)
        if not callable(getattr(oos_probe, "on_bar", None)):
            raise DataContractError(
                "oos_actor_factory must return a strategy actor exposing on_bar(event, runner)."
            )

    # ------------------------------------------------------------------
    # In-sample segment slicing (mirrors the canonical OOS slicer semantics)
    # ------------------------------------------------------------------

    def _resolve_is_events(self, plan: FrozenResearchPlan) -> Tuple[BacktestMarketEvent, ...]:
        num_bars = plan.rows_table.num_rows
        for ev in plan.events:
            idx_val = ev.payload.get("bar_index")
            if idx_val is not None:
                idx = int(idx_val)
                if not (0 <= idx < num_bars):
                    raise DataContractError(
                        f"Event '{ev.source_order_key}' carries bar_index {idx} outside the canonical "
                        f"range [0, {num_bars - 1}]; index identity inconsistent with the dataset."
                    )

        parts = resolve_partition_ranges(num_bars, plan.split_policy)
        train_start, train_end = parts["TRAIN"]
        val_start, val_end = parts["VAL"]
        ts_col = plan.rows_table.column("timestamp_utc")
        window_start_ns = extract_nanoseconds_from_scalar(ts_col[train_start], ts_col.type)
        window_end_ns = extract_nanoseconds_from_scalar(ts_col[val_end], ts_col.type)

        segment: list[BacktestMarketEvent] = []
        for ev in plan.events:
            idx_val = ev.payload.get("bar_index")
            if idx_val is not None:
                idx = int(idx_val)
                if (train_start <= idx <= train_end) or (val_start <= idx <= val_end):
                    if not (window_start_ns <= ev.event_timestamp_ns <= window_end_ns):
                        raise DataContractError(
                            f"Event '{ev.source_order_key}' claims IS bar_index {idx} but its timestamp "
                            f"({ev.event_timestamp_ns} ns) falls outside the inclusive IS window "
                            f"({window_start_ns}, {window_end_ns}); index/timestamp identity "
                            f"contradiction fails closed."
                        )
                    segment.append(ev)
            else:
                if window_start_ns <= ev.event_timestamp_ns <= window_end_ns:
                    segment.append(ev)

        if not segment:
            raise DataContractError(
                f"In-sample segment for plan '{plan.plan_id}' is empty; no census events to execute."
            )
        return tuple(segment)

    # ------------------------------------------------------------------
    # Census trial execution
    # ------------------------------------------------------------------

    def _classify_invalid_spec(self, trial: TrialSpec) -> Optional[str]:
        if not trial.feature_names:
            return "empty feature_names (a pre-registered trial must declare features)"
        if not trial.parameters:
            return "empty parameters (a pre-registered trial must declare parameters)"
        return None

    def _execute_census_trial(
        self,
        trial: TrialSpec,
        plan: FrozenResearchPlan,
        actor_factory: ActorFactory,
        is_events: Sequence[BacktestMarketEvent],
        hypothesis_spec_sha256: str,
    ) -> _TrialExecutionResult:
        invalid_reason = self._classify_invalid_spec(trial)
        if invalid_reason is not None:
            config_sha256 = SearchTrialRecord.compute_config_sha256(trial.feature_names, trial.parameters)
            return _TrialExecutionResult(
                trial_id=trial.trial_id,
                feature_names=trial.feature_names,
                parameters=trial.parameters,
                status=SearchTrialStatus.INVALID,
                evidence=None,
                failure_reason=f"INVALID trial specification: {invalid_reason}",
                config_sha256=config_sha256,
            )

        config_sha256 = SearchTrialRecord.compute_config_sha256(trial.feature_names, trial.parameters)
        try:
            actor = actor_factory(dict(trial.parameters))
            runner = EventBacktestRunner(config=plan.engine_config, strategy_actor=actor)
            manifest, fills_table, equity_table = runner.run_backtest(
                events=list(is_events),
                hypothesis_id=plan.hypothesis_id,
                hypothesis_spec_sha256=hypothesis_spec_sha256,
                strategy_config_hash=config_sha256,
                pyproject_toml_sha256=plan.pyproject_toml_sha256,
                git_commit_hash=plan.git_commit_hash,
                periods_per_year=plan.periods_per_year,
                canonical_data_hashes=list(plan.canonical_data_hashes),
            )
            evidence = BacktestRunEvidence(
                trial_id=trial.trial_id,
                strategy_id=plan.strategy_id,
                hypothesis_id=plan.hypothesis_id,
                feature_names=trial.feature_names,
                parameters=dict(trial.parameters),
                manifest=manifest,
                fills_table=fills_table,
                equity_table=equity_table,
            )
            return _TrialExecutionResult(
                trial_id=trial.trial_id,
                feature_names=trial.feature_names,
                parameters=trial.parameters,
                status=SearchTrialStatus.EXECUTED_SUCCESSFULLY,
                evidence=evidence,
                failure_reason=None,
                config_sha256=config_sha256,
            )
        except Exception as exc:
            return _TrialExecutionResult(
                trial_id=trial.trial_id,
                feature_names=trial.feature_names,
                parameters=trial.parameters,
                status=SearchTrialStatus.FAILED,
                evidence=None,
                failure_reason=_deterministic_failure_reason(exc),
                config_sha256=config_sha256,
            )

    # ------------------------------------------------------------------
    # Ledger record assembly
    # ------------------------------------------------------------------

    def _assert_success_lineage(
        self,
        results: Sequence[_TrialExecutionResult],
        records: Sequence[SearchTrialRecord],
    ) -> None:
        for result, record in zip(results, records):
            evidence = result.evidence
            if evidence is None:
                raise DataContractError(
                    f"Success-lineage guard expects evidence for trial '{result.trial_id}'."
                )
            if record.config_sha256 != evidence.manifest.strategy_config_hash:
                raise DataContractError(
                    f"Trial '{result.trial_id}' record config_sha256 '{record.config_sha256}' does not "
                    f"match its manifest strategy_config_hash "
                    f"'{evidence.manifest.strategy_config_hash}'; config identity lineage violated."
                )
            if record.execution_manifest_id != evidence.manifest.manifest_id:
                raise DataContractError(
                    f"Trial '{result.trial_id}' record execution_manifest_id '"
                    f"{record.execution_manifest_id}' does not match its manifest id "
                    f"'{evidence.manifest.manifest_id}'."
                )

    def _build_mixed_ledger_records(
        self,
        results: Sequence[_TrialExecutionResult],
        plan: FrozenResearchPlan,
        periods_per_year: Decimal,
    ) -> Tuple[SearchTrialRecord, ...]:
        records: list[SearchTrialRecord] = []
        for r in results:
            if r.status == SearchTrialStatus.EXECUTED_SUCCESSFULLY:
                evidence = r.evidence
                if evidence is None:
                    raise DataContractError(
                        f"Successful trial '{r.trial_id}' carries no evidence in mixed census build."
                    )
                returns = derive_canonical_equity_returns(evidence.equity_table)
                sharpe = calculate_annualized_sharpe(returns, periods_per_year)
                manifest_sr = evidence.manifest.execution_summary.sharpe_ratio
                if manifest_sr is None:
                    raise DataContractError(
                        f"Trial '{r.trial_id}' manifest '{evidence.manifest.manifest_id}' has no "
                        f"execution_summary.sharpe_ratio; truthful Phase 5 emission required before "
                        f"evidence assembly."
                    )
                if abs(manifest_sr - sharpe) > MANIFEST_SHARPE_CONSISTENCY_TOLERANCE:
                    raise DataContractError(
                        f"Trial '{r.trial_id}' manifest execution summary Sharpe ({manifest_sr}) "
                        f"deviates from canonical Sharpe ({sharpe}) beyond tolerance "
                        f"({MANIFEST_SHARPE_CONSISTENCY_TOLERANCE})."
                    )
                records.append(
                    SearchTrialRecord.create(
                        trial_id=evidence.trial_id,
                        strategy_id=evidence.strategy_id,
                        hypothesis_id=evidence.hypothesis_id,
                        feature_names=evidence.feature_names,
                        parameters=evidence.parameters,
                        in_sample_sharpe=sharpe,
                        execution_manifest_id=evidence.manifest.manifest_id,
                        in_sample_returns=returns,
                        config_sha256=r.config_sha256,
                    )
                )
            else:
                status = (
                    SearchTrialStatus.FAILED
                    if r.status == SearchTrialStatus.FAILED
                    else SearchTrialStatus.INVALID
                )
                if not r.failure_reason:
                    raise DataContractError(
                        f"Non-successful trial '{r.trial_id}' carries no failure_reason; cannot build "
                        f"a truthful census record."
                    )
                reason = r.failure_reason
                records.append(
                    SearchTrialRecord.create_declared(
                        trial_id=r.trial_id,
                        strategy_id=plan.strategy_id,
                        hypothesis_id=plan.hypothesis_id,
                        feature_names=r.feature_names,
                        parameters=r.parameters,
                        trial_status=status,
                        failure_reason=reason,
                        config_sha256=r.config_sha256,
                    )
                )
        return tuple(records)

    # ------------------------------------------------------------------
    # Parameter perturbation (all-success census only)
    # ------------------------------------------------------------------

    def _run_perturbation(
        self,
        plan: FrozenResearchPlan,
        actor_factory: ActorFactory,
        is_events: Sequence[BacktestMarketEvent],
        hypothesis_spec_sha256: str,
    ) -> Tuple[ParameterPerturbationGrid, Dict[str, BacktestManifest]]:
        base = plan.perturbation_spec
        if base is None:
            raise DataContractError("Perturbation not configured for this plan.")
        primary = plan.trials[0]
        theta = base.base_parameter_value
        values = (theta * Decimal("0.75"), theta, theta * Decimal("1.25"))

        points: list[ParameterPerturbationPoint] = []
        by_run: Dict[str, BacktestManifest] = {}
        for n, value in enumerate(values):
            parameters = dict(primary.parameters)
            parameters[base.base_parameter_name] = value
            config_sha256 = SearchTrialRecord.compute_config_sha256(primary.feature_names, parameters)
            run_id = f"{plan.plan_id}-PERT{n + 1}"

            actor = actor_factory(parameters)
            runner = EventBacktestRunner(config=plan.engine_config, strategy_actor=actor)
            manifest, _fills, equity = runner.run_backtest(
                events=list(is_events),
                hypothesis_id=plan.hypothesis_id,
                hypothesis_spec_sha256=hypothesis_spec_sha256,
                strategy_config_hash=config_sha256,
                pyproject_toml_sha256=plan.pyproject_toml_sha256,
                git_commit_hash=plan.git_commit_hash,
                periods_per_year=plan.periods_per_year,
                canonical_data_hashes=list(plan.canonical_data_hashes),
            )
            returns = derive_canonical_equity_returns(equity)
            actual_sharpe = calculate_annualized_sharpe(returns, plan.periods_per_year)
            manifest_sr = manifest.execution_summary.sharpe_ratio
            if manifest_sr is None:
                raise DataContractError(
                    f"Perturbation run '{run_id}' manifest '{manifest.manifest_id}' has no "
                    f"execution_summary.sharpe_ratio."
                )
            if Decimal(str(manifest_sr)) != actual_sharpe:
                raise DataContractError(
                    f"Perturbation run '{run_id}' manifest Sharpe ({manifest_sr}) must equal the "
                    f"canonical Sharpe ({actual_sharpe}) exactly for a perturbation execution point."
                )
            output_artifact_hash = manifest.compute_sha256()
            input_artifact_hash = hashlib.sha256(
                f"{hypothesis_spec_sha256}:{config_sha256}".encode("utf-8")
            ).hexdigest()
            point = ParameterPerturbationPoint(
                parameter_value=value,
                run_id=run_id,
                manifest_id=manifest.manifest_id,
                input_artifact_hash=input_artifact_hash,
                output_artifact_hash=output_artifact_hash,
                actual_sharpe=actual_sharpe,
            )
            points.append(point)
            by_run[run_id] = manifest

        if len(points) != 3:
            raise DataContractError(
                "Perturbation grid must contain exactly three execution points "
                f"(0.75x, 1.0x, 1.25x of theta_0); observed {len(points)}."
            )
        grid = ParameterPerturbationGrid(
            base_parameter_name=base.base_parameter_name,
            base_parameter_value=theta,
            points=(points[0], points[1], points[2]),
        )
        return grid, by_run