"""Adversarial tests for the Phase 5 production research orchestrator (Phase 14, frozen D6 contract).

Attack the ratified production seam: a FROZEN pre-registered census executes in declared order
against the canonical in-sample segment; the census is sealed ONLY through the sole sanctioned
authority with the frozen expected_k; FAILED/INVALID trials REMAIN census members with NO
evidence (D6 Option A) and a mixed census seals truthfully with Phase 6 BLOCKED; an all-success
census runs the exact 0.75/1.0/1.25 perturbation grid, a separate held-out OOS run, and the
StatisticalValidationGate. No fabrication, no K shrink, no ledger.seal() outside the authority,
no forbidden production/execution imports, and gate/OOS exceptions PROPAGATE.
"""

import ast
import inspect
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pyarrow as pa
import pytest

import acash.research.backtest_orchestrator as orch_mod
from acash.backtest.adapter import BacktestMarketEvent, CanonicalDataAdapter
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.equity_returns import derive_canonical_equity_returns
from acash.backtest.schema import BacktestEngineConfig, BacktestManifest, OrderType
from acash.core.domain.exceptions import DataContractError
from acash.research.backtest_orchestrator import (
    CensusState,
    FrozenResearchPlan,
    PerturbationSpec,
    PhaseFiveOrchestrationReport,
    PhaseFiveResearchOrchestrator,
    TrialSpec,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.oos_provenance import (
    PitLineageAttestation,
    PriceAdjustmentPolicy,
    resolve_partition_ranges,
)
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
    SplitPolicy,
)
from acash.validation.deflated_sharpe import calculate_annualized_sharpe
from acash.validation.gate import (
    StatisticalValidationGate,
    _compute_canonical_series_sha256,
)
from acash.validation.schema import (
    SEARCH_TRIAL_EVIDENCE_FIELDS,
    ParameterPerturbationGrid,
    SearchTrialLedger,
    SearchTrialRecord,
    SearchTrialStatus,
    SharpeSpace,
    ValidationConfig,
    ValidationGateVerdict,
    ValidationReport,
)

_NUM_BARS = 240
_PPY = Decimal("252.0")
_TS_BASE_NS = 1_768_833_000_000_000_000
_T60_NS = 60_000_000_000

_STRATEGY_ID = "STRAT_P5_ORCH"
_HYPOTHESIS_ID = "TEST-HYP-PHASE5-001"
_PLAN_ID = "PLAN_PHASE5_CENSUS_001"
_PYPROJECT_SHA = "e" * 64
_GIT_COMMIT = "1" * 40
_DATASET_ID = "DATASET_PHASE5_CENSUS"
_DATASET_VERSION = "v1"
_CANONICAL_HASHES = ("a" * 64,)

_POLICY = SplitPolicy(
    train_pct=Decimal("0.60"),
    val_pct=Decimal("0.20"),
    oos_pct=Decimal("0.20"),
    embargo_bars=1,
)
_ENGINE_CONFIG = BacktestEngineConfig(engine_id="BKT-PHASE5-ORCH", symbol="ES.FUT")

_QUANTITIES = [Decimal(str(q)) for q in range(2, 8)]  # 2.0 .. 7.0 aligned with _TRIAL_IDS 001..006
_TRIAL_IDS = [f"PHASE5-TRIAL-{i:03d}" for i in range(1, 7)]

_DEFAULT_PERTURBATION = PerturbationSpec(
    base_parameter_name="quantity", base_parameter_value=Decimal("2.0")
)
_MISSING = object()


# ---------------------------------------------------------------------------
# Synthetic data plumbing (deterministic, isolated from any production data)
# ---------------------------------------------------------------------------


def _bars_table(num_bars: int = _NUM_BARS, seed: int = 1234) -> pa.Table:
    rng = np.random.default_rng(seed=seed)
    steps = rng.normal(loc=0.00025, scale=0.0040, size=num_bars)
    log_close = 5000.0 + np.cumsum(steps)
    closes = [Decimal(f"{c:.2f}") for c in log_close]
    timestamps = [_TS_BASE_NS + (i * _T60_NS) for i in range(num_bars)]
    pydict: Dict[str, Any] = {
        "timestamp_utc": timestamps,
        "open": closes,
        "high": [c + Decimal("1.00") for c in closes],
        "low": [c - Decimal("1.00") for c in closes],
        "close": closes,
        "volume": [Decimal("100.0")] * num_bars,
        "knowledge_time_utc": timestamps,
    }
    return pa.Table.from_pydict(pydict)


def _events(num_bars: int = _NUM_BARS, seed: int = 1234) -> Tuple[BacktestMarketEvent, ...]:
    return tuple(CanonicalDataAdapter.from_bars_table(_bars_table(num_bars, seed), symbol="ES.FUT"))


def _attestation(**overrides: Any) -> PitLineageAttestation:
    base: Dict[str, Any] = {
        "dataset_id": _DATASET_ID,
        "dataset_version": _DATASET_VERSION,
        "source_kind": "BARS",
        "pit_verified": True,
        "pit_verification_provenance": (
            "Event-level timestamps from source-matched exchange feed with recorded "
            "knowledge_time_utc at each observation"
        ),
        "knowledge_time_utc_available": True,
        "price_adjustment_policy": PriceAdjustmentPolicy.NONE_APPLICABLE_RECORDED,
        "corporate_action_provenance": "",
        "canonical_data_hashes": _CANONICAL_HASHES,
    }
    base.update(overrides)
    return PitLineageAttestation(**base)


def _hypothesis_spec() -> HypothesisSpecification:
    return HypothesisSpecification(
        hypothesis_id=_HYPOTHESIS_ID,
        hypothesis_version="v1.0",
        economic_rationale="Phase 5 production orchestrator synthetic test census",
        target_symbol="ES.FUT",
        feature_dependencies=["qty_proxy"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-09-09T00:00:00Z",
        author="Phase14-Test",
    )


def _trial_specs() -> Tuple[TrialSpec, ...]:
    return tuple(
        TrialSpec(
            trial_id=tid,
            feature_names=["qty_proxy"],
            parameters={"quantity": qty},
        )
        for tid, qty in zip(_TRIAL_IDS, _QUANTITIES)
    )


def _plan(
    *,
    num_bars: int = _NUM_BARS,
    seed: Optional[int] = None,
    trials: Optional[Sequence[TrialSpec]] = None,
    perturbation_spec: Any = _MISSING,
    split_policy: Optional[SplitPolicy] = None,
    validation_config: Optional[ValidationConfig] = None,
    periods_per_year: Optional[Decimal] = None,
    **overrides: Any,
) -> FrozenResearchPlan:
    resolved_seed = seed if seed is not None else 1234 + num_bars
    bars = _bars_table(num_bars, resolved_seed)
    kwargs: Dict[str, Any] = {
        "plan_id": _PLAN_ID,
        "strategy_id": _STRATEGY_ID,
        "hypothesis_id": _HYPOTHESIS_ID,
        "hypothesis_spec": _hypothesis_spec(),
        "trials": tuple(trials if trials is not None else _trial_specs()),
        "engine_config": _ENGINE_CONFIG,
        "canonical_data_hashes": _CANONICAL_HASHES,
        "pyproject_toml_sha256": _PYPROJECT_SHA,
        "git_commit_hash": _GIT_COMMIT,
        "periods_per_year": periods_per_year if periods_per_year is not None else _PPY,
        "split_policy": split_policy if split_policy is not None else _POLICY,
        "validation_config": (
            validation_config
            if validation_config is not None
            else ValidationConfig(periods_per_year=_PPY)
        ),
        "rows_table": bars,
        "events": _events(num_bars, resolved_seed),
        "pit_attestation": _attestation(),
        "dataset_id": _DATASET_ID,
        "dataset_version": _DATASET_VERSION,
        "perturbation_spec": (
            _DEFAULT_PERTURBATION if perturbation_spec is _MISSING else perturbation_spec
        ),
    }
    kwargs.update(overrides)
    return FrozenResearchPlan(**kwargs)


# ---------------------------------------------------------------------------
# Strategy actors and factories (fresh instance per call)
# ---------------------------------------------------------------------------


class QtyHoldActor:
    """Buys a fixed quantity once at an IS bar index and holds to the end."""

    def __init__(self, parameters: Mapping[str, Any], bar_index: int = 1) -> None:
        self._qty = parameters["quantity"]
        self._bar_index = bar_index

    def on_bar(self, event: Any, runner: Any) -> None:
        if event.payload["bar_index"] == self._bar_index:
            runner.submit_order(
                order_id="ORD-P5-000001",
                symbol="ES.FUT",
                order_type=OrderType.MARKET,
                side="BUY",
                quantity=self._qty,
            )

    def on_trade(self, event: Any, runner: Any) -> None:
        pass


class OosHoldActor:
    """Buys a fixed quantity once on the first OOS event and holds to the end."""

    def __init__(self, parameters: Mapping[str, Any]) -> None:
        self._qty = parameters["quantity"]
        self._placed = False

    def on_bar(self, event: Any, runner: Any) -> None:
        if not self._placed:
            runner.submit_order(
                order_id="ORD-P5-OOS001",
                symbol="ES.FUT",
                order_type=OrderType.MARKET,
                side="BUY",
                quantity=self._qty,
            )
            self._placed = True

    def on_trade(self, event: Any, runner: Any) -> None:
        pass


def _clean_actor_factory(parameters: Mapping[str, Any]) -> Any:
    return QtyHoldActor(parameters)


def _failing_actor_factory(parameters: Mapping[str, Any]) -> Any:
    if parameters.get("quantity") == Decimal("4.0"):
        raise RuntimeError("injected quantity-4.0 census failure")
    return QtyHoldActor(parameters)


def _oos_actor_factory(parameters: Mapping[str, Any]) -> Any:
    return OosHoldActor(parameters)


def _orchestrate(
    plan: FrozenResearchPlan,
    actor_factory: Any = _clean_actor_factory,
    oos_actor_factory: Any = _oos_actor_factory,
) -> PhaseFiveOrchestrationReport:
    return PhaseFiveResearchOrchestrator().orchestrate(plan, actor_factory, oos_actor_factory)


# ---------------------------------------------------------------------------
# Plan construction & frozen-plan governance
# ---------------------------------------------------------------------------


class TestPlanGovernance:
    def test_empty_census_fails_closed(self) -> None:
        plan = _plan(trials=[])
        with pytest.raises(DataContractError, match="empty pre-registered census"):
            _orchestrate(plan)

    def test_duplicate_trial_ids_fail_closed(self) -> None:
        specs = (
            TrialSpec(trial_id="DUP", feature_names=["q"], parameters={"quantity": Decimal("2.0")}),
            TrialSpec(trial_id="DUP", feature_names=["q"], parameters={"quantity": Decimal("3.0")}),
        )
        with pytest.raises(DataContractError, match="duplicate trial_ids"):
            _orchestrate(_plan(trials=specs))

    def test_hypothesis_id_mismatch_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="hypothesis_spec.hypothesis_id"):
            _orchestrate(_plan(hypothesis_id="HYP_OTHER"))

    def test_ppy_contradiction_fails_closed(self) -> None:
        plan = _plan(periods_per_year=Decimal("200"))
        with pytest.raises(DataContractError, match="single"):
            _orchestrate(plan)

    def test_split_policy_not_100_pct_fails_closed(self) -> None:
        bad = SplitPolicy(
            train_pct=Decimal("0.60"),
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.19"),
            embargo_bars=1,
        )
        with pytest.raises(DataContractError, match="allocate 100%"):
            _orchestrate(_plan(split_policy=bad))

    def test_dataset_identity_mismatch_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="dataset identity"):
            _orchestrate(_plan(pit_attestation=_attestation(dataset_id="DATASET_OTHER")))

    def test_canonical_hash_mismatch_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="canonical_data_hashes"):
            _orchestrate(_plan(pit_attestation=_attestation(canonical_data_hashes=("b" * 64,))))

    def test_bars_table_too_small_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="canonical bars table"):
            _orchestrate(_plan(num_bars=1))

    def test_perturbation_base_parameter_absent_fails_closed(self) -> None:
        spec = PerturbationSpec(base_parameter_name="lookback", base_parameter_value=Decimal("2.0"))
        with pytest.raises(DataContractError, match="not present in"):
            _orchestrate(_plan(perturbation_spec=spec))

    def test_perturbation_theta_mismatch_fails_closed(self) -> None:
        spec = PerturbationSpec(base_parameter_name="quantity", base_parameter_value=Decimal("3.0"))
        with pytest.raises(DataContractError, match="must exactly equal"):
            _orchestrate(_plan(perturbation_spec=spec))

    def test_perturbation_nonpositive_theta_fails_closed(self) -> None:
        plan = _plan(
            trials=(TrialSpec(trial_id="T1", feature_names=["qty_proxy"], parameters={"quantity": Decimal("0.0")}),),
            perturbation_spec=PerturbationSpec(base_parameter_name="quantity", base_parameter_value=Decimal("0.0")),
        )
        with pytest.raises(DataContractError, match="positive Decimal base theta_0"):
            _orchestrate(plan)


class TestActorFactoryGuardrails:
    _SINGLETON = QtyHoldActor({"quantity": Decimal("2.0")})

    def test_shared_actor_instance_fails_closed(self) -> None:
        def shared_factory(parameters: Mapping[str, Any]) -> Any:
            return self._SINGLETON

        with pytest.raises(DataContractError, match="NEW actor instance"):
            _orchestrate(_plan(), actor_factory=shared_factory)

    def test_actor_without_on_bar_fails_closed(self) -> None:
        def bare_factory(parameters: Mapping[str, Any]) -> Any:
            return object()

        with pytest.raises(DataContractError, match="on_bar"):
            _orchestrate(_plan(), actor_factory=bare_factory)


# ---------------------------------------------------------------------------
# All-success census: full orchestration certificate
# ---------------------------------------------------------------------------


def _assert_valid_gate_report(report: PhaseFiveOrchestrationReport) -> None:
    assert isinstance(report.phase_six_report, ValidationReport)
    assert report.phase_six_report.validation_id.startswith("VAL_")
    assert len(report.phase_six_report.evidence_digest) == 64
    assert len(report.phase_six_report.decision_digest) == 64
    assert isinstance(report.phase_six_report.verdict, ValidationGateVerdict)
    assert isinstance(report.phase_six_report.is_tradeable_alpha, bool)


class TestAllSuccessCensus:
    def test_happy_path_full_certificate(self) -> None:
        report = _orchestrate(_plan())

        assert report.plan_id == _PLAN_ID
        assert report.planned_trial_count == 6
        assert report.actual_trial_count == 6
        assert report.successful_count == 6
        assert report.failed_count == 0
        assert report.invalid_count == 0
        assert report.census_state == CensusState.SEALED_COMPLETE
        assert report.ordered_trial_ids == tuple(_TRIAL_IDS)
        assert report.ledger_id == f"CENSUS_{_STRATEGY_ID}_{_HYPOTHESIS_ID}"
        assert report.sealed_by_owner == "ACASH_D6_CENSUS_AUTHORITY"
        assert len(report.ledger_digest) == 64
        assert report.perturbation_runs_executed == 3
        assert report.phase_six_invoked is True
        assert report.blocked_reason is None
        assert report.perturbation_grid is not None
        assert report.oos_record is not None
        assert report.sealed_ledger is not None

        # Sealed census royalty: EXECUTED_SUCCESSFULLY with full evidence in declared order.
        ledger = report.sealed_ledger
        assert ledger.is_sealed is True
        assert ledger.ledger_digest == ledger.compute_ledger_digest()
        assert [t.trial_id for t in ledger.trials] == _TRIAL_IDS
        assert all(
            t.trial_status == SearchTrialStatus.EXECUTED_SUCCESSFULLY for t in ledger.trials
        )

        _assert_valid_gate_report(report)

    def test_census_identity_and_config_single_authority(self) -> None:
        report = _orchestrate(_plan())
        ledger = report.sealed_ledger
        assert ledger is not None
        for tid, qty in zip(_TRIAL_IDS, _QUANTITIES):
            rec = next(t for t in ledger.trials if t.trial_id == tid)
            assert rec.strategy_id == _STRATEGY_ID
            assert rec.hypothesis_id == _HYPOTHESIS_ID
            expected_cfg = SearchTrialRecord.compute_config_sha256(["qty_proxy"], {"quantity": qty})
            assert rec.config_sha256 == expected_cfg
        assert len(ledger.p_values) == 6

    def test_repeat_invocation_is_deterministic(self) -> None:
        a = _orchestrate(_plan())
        b = _orchestrate(_plan())

        assert a.ledger_digest == b.ledger_digest
        assert a.ordered_trial_ids == b.ordered_trial_ids
        assert a.oos_record is not None and b.oos_record is not None
        assert a.oos_record.content_digest() == b.oos_record.content_digest()
        assert a.oos_return_series_sha256 == b.oos_return_series_sha256
        assert a.perturbation_grid is not None and b.perturbation_grid is not None
        assert (
            tuple(p.output_artifact_hash for p in a.perturbation_grid.points)
            == tuple(p.output_artifact_hash for p in b.perturbation_grid.points)
        )
        assert (
            tuple(p.input_artifact_hash for p in a.perturbation_grid.points)
            == tuple(p.input_artifact_hash for p in b.perturbation_grid.points)
        )
        assert a.phase_six_report is not None and b.phase_six_report is not None
        assert a.phase_six_report.evidence_digest == b.phase_six_report.evidence_digest
        assert a.phase_six_report.decision_digest == b.phase_six_report.decision_digest
        assert a.phase_six_report.verdict == b.phase_six_report.verdict

    def test_sealed_through_sole_authority_with_expected_k(self) -> None:
        report = _orchestrate(_plan())
        ledger = report.sealed_ledger
        assert ledger is not None
        assert ledger.total_trials == 6
        assert ledger.ledger_digest is not None
        assert ledger.ledger_digest == ledger.compute_ledger_digest()
        assert report.census_state == CensusState.SEALED_COMPLETE

    def test_perturbation_grid_geometry_and_distinct_execution(self) -> None:
        report = _orchestrate(_plan())
        grid = report.perturbation_grid
        assert grid is not None
        assert grid.base_parameter_name == "quantity"
        assert grid.base_parameter_value == Decimal("2.0")
        assert grid.grid_values == (Decimal("1.5"), Decimal("2.0"), Decimal("2.5"))
        points = grid.points
        assert len({p.run_id for p in points}) == 3
        assert len({p.manifest_id for p in points}) == 3
        assert len({p.output_artifact_hash for p in points}) == 3
        assert len({p.actual_sharpe for p in points}) == 3
        # Perturbation runs are NOT census members.
        for point in points:
            assert point.manifest_id not in report.ordered_trial_ids
        assert report.perturbation_runs_executed == 3
        # The mid point is the primary theta_0 and must reproduce the primary Sharpe.
        ledger = report.sealed_ledger
        assert ledger is not None
        primary = next(
            t for t in ledger.trials if t.trial_id == _TRIAL_IDS[0]
        )
        assert primary is not None
        assert points[1].actual_sharpe == primary.in_sample_sharpe

    def test_four_way_perturbation_manifest_binding(self) -> None:
        report = _orchestrate(_plan())
        grid = report.perturbation_grid
        store = report.manifest_store
        assert grid is not None and store is not None
        for point in grid.points:
            man = store[point.manifest_id]
            assert isinstance(man, BacktestManifest)
            assert point.validate_manifest_binding(man) is True

    def test_census_trial_manifests_bound_in_store(self) -> None:
        report = _orchestrate(_plan())
        ledger = report.sealed_ledger
        store = report.manifest_store
        assert ledger is not None and store is not None
        for rec in ledger.trials:
            assert rec.execution_manifest_id is not None
            man = store[rec.execution_manifest_id]
            assert isinstance(man, BacktestManifest)
            assert man.manifest_id == rec.execution_manifest_id
            assert man.hypothesis_id == _HYPOTHESIS_ID
            assert man.strategy_config_hash == rec.config_sha256

    def test_phase_six_report_emitted(self) -> None:
        report = _orchestrate(_plan())
        _assert_valid_gate_report(report)
        # The gate was reached only with a complete, sealed census.
        phase_six = report.phase_six_report
        assert phase_six is not None
        assert phase_six.in_sample_sharpe is not None
        assert phase_six.out_of_sample_sharpe is not None

    def test_oos_separate_heldout_no_is_reuse(self) -> None:
        report = _orchestrate(_plan())
        record = report.oos_record
        assert record is not None
        record.assert_is_oos_distinct()
        assert report.oos_return_series_sha256 == record.oos_return_series_sha256
        assert len(record.oos_manifest_id) >= 8
        assert record.oos_return_count >= 4
        # The OOS series must differ from the primary in-sample series (D5 no-reuse).
        ledger = report.sealed_ledger
        assert ledger is not None
        primary_is_hash = ledger.trials[0].in_sample_return_series_sha256
        assert report.oos_return_series_sha256 != primary_is_hash

    def test_canonical_return_sharpe_lineage_matches_independent_rerun(self) -> None:
        plan = _plan()
        report = _orchestrate(plan)
        is_events = PhaseFiveResearchOrchestrator()._resolve_is_events(plan)
        hyp_spec_hash = calculate_hypothesis_spec_sha256(plan.hypothesis_spec)
        ledger = report.sealed_ledger
        assert ledger is not None
        for tid, qty in zip(_TRIAL_IDS, _QUANTITIES):
            cfg_hash = SearchTrialRecord.compute_config_sha256(["qty_proxy"], {"quantity": qty})
            runner = EventBacktestRunner(config=_ENGINE_CONFIG, strategy_actor=QtyHoldActor({"quantity": qty}))
            manifest, _fills, equity = runner.run_backtest(
                events=list(is_events),
                hypothesis_id=_HYPOTHESIS_ID,
                hypothesis_spec_sha256=hyp_spec_hash,
                strategy_config_hash=cfg_hash,
                pyproject_toml_sha256=_PYPROJECT_SHA,
                git_commit_hash=_GIT_COMMIT,
                periods_per_year=_PPY,
                canonical_data_hashes=list(_CANONICAL_HASHES),
            )
            returns = derive_canonical_equity_returns(equity)
            rec = next(t for t in ledger.trials if t.trial_id == tid)
            assert _compute_canonical_series_sha256(returns) == rec.in_sample_return_series_sha256
            assert calculate_annualized_sharpe(returns, _PPY) == rec.in_sample_sharpe
            assert manifest.manifest_id == rec.execution_manifest_id
            assert manifest.execution_summary.sharpe_ratio == rec.in_sample_sharpe
            assert manifest.strategy_config_hash == rec.config_sha256
            assert cfg_hash == rec.config_sha256

    def test_is_slice_boundary_matches_partition_authority(self) -> None:
        plan = _plan()
        parts = resolve_partition_ranges(_NUM_BARS, _POLICY)
        is_events = PhaseFiveResearchOrchestrator()._resolve_is_events(plan)
        is_indices = {int(e.payload["bar_index"]) for e in is_events}
        expected = set(range(parts["TRAIN"][0], parts["TRAIN"][1] + 1)) | set(
            range(parts["VAL"][0], parts["VAL"][1] + 1)
        )
        assert is_indices == expected
        assert len(is_events) == len(expected) == 192


# ---------------------------------------------------------------------------
# Mixed census (D6 Option A): FAILED/INVALID remain with NO evidence, Phase 6 blocked
# ---------------------------------------------------------------------------


class TestMixedCensusD6OptionA:
    def test_failed_trial_remains_phase_six_blocked(self) -> None:
        report = _orchestrate(_plan(), actor_factory=_failing_actor_factory)

        assert report.census_state == CensusState.SEALED_MIXED
        assert report.successful_count == 5
        assert report.failed_count == 1
        assert report.invalid_count == 0
        assert report.actual_trial_count == 6
        assert report.planned_trial_count == 6
        assert report.phase_six_invoked is False
        assert report.phase_six_report is None
        assert report.perturbation_runs_executed == 0
        assert report.perturbation_grid is None
        assert report.oos_record is None
        assert report.blocked_reason is not None
        assert "MIXED CENSUS FAILED CLOSED" in report.blocked_reason
        assert report.blocked_reason.count("K=6") == 1

        ledger = report.sealed_ledger
        assert ledger is not None
        assert ledger.total_trials == 6
        assert [t.trial_id for t in ledger.trials] == _TRIAL_IDS
        failed = next(t for t in ledger.trials if t.trial_id == "PHASE5-TRIAL-003")
        assert failed.trial_status == SearchTrialStatus.FAILED
        assert failed.failure_reason is not None
        assert "RuntimeError" in failed.failure_reason
        assert failed.failure_reason.startswith("RuntimeError")
        for field in SEARCH_TRIAL_EVIDENCE_FIELDS:
            assert getattr(failed, field) is None
        assert failed.config_sha256 == SearchTrialRecord.compute_config_sha256(
            ["qty_proxy"], {"quantity": Decimal("4.0")}
        )

    def test_invalid_trial_remains_phase_six_blocked(self) -> None:
        # Exclude qty 4.0 so the failure-injection factory never trips in this census.
        valid = tuple(s for s in _trial_specs() if s.parameters["quantity"] != Decimal("4.0"))
        invalid = TrialSpec(
            trial_id="PHASE5-TRIAL-INVALID-001",
            feature_names=["qty_proxy"],
            parameters={},
        )
        plan = _plan(trials=valid + (invalid,))
        report = _orchestrate(plan, actor_factory=_failing_actor_factory)

        assert report.census_state == CensusState.SEALED_MIXED
        assert report.successful_count == 5
        assert report.invalid_count == 1
        assert report.phase_six_invoked is False
        assert report.blocked_reason is not None

        ledger = report.sealed_ledger
        assert ledger is not None
        assert ledger.total_trials == 6
        bad = ledger.trials[5]
        assert bad.trial_id == "PHASE5-TRIAL-INVALID-001"
        assert bad.trial_status == SearchTrialStatus.INVALID
        assert bad.failure_reason is not None
        assert "empty parameters" in bad.failure_reason
        for field in SEARCH_TRIAL_EVIDENCE_FIELDS:
            assert getattr(bad, field) is None

    def test_k_never_shrinks_and_success_count_never_substituted(self) -> None:
        report = _orchestrate(_plan(), actor_factory=_failing_actor_factory)
        ledger = report.sealed_ledger
        assert ledger is not None
        # K is the frozen planned count, NOT the successful count.
        assert ledger.total_trials == report.planned_trial_count == 6
        assert report.successful_count == 5
        assert ledger.ledger_digest == ledger.compute_ledger_digest()

    def test_gate_never_invoked_on_mixed_census(self, monkeypatch: Any) -> None:
        calls: List[int] = []

        def _spy(self: Any, *args: Any, **kwargs: Any) -> ValidationReport:
            calls.append(1)
            raise AssertionError("StatisticalValidationGate must not run on a mixed census")

        monkeypatch.setattr(StatisticalValidationGate, "evaluate_strategy", _spy)
        report = _orchestrate(_plan(), actor_factory=_failing_actor_factory)
        assert report.census_state == CensusState.SEALED_MIXED
        assert calls == []


# ---------------------------------------------------------------------------
# Fail-closed execution, error propagation, and boundary resilience
# ---------------------------------------------------------------------------


class TestFailClosedExecution:
    def test_insufficient_oos_observations_fails_closed(self) -> None:
        no_embargo = SplitPolicy(
            train_pct=Decimal("0.60"),
            val_pct=Decimal("0.20"),
            oos_pct=Decimal("0.20"),
            embargo_bars=0,
        )
        plan = _plan(num_bars=15, split_policy=no_embargo)
        with pytest.raises(DataContractError):
            _orchestrate(plan)

    def test_gate_exceptions_propagate(self, monkeypatch: Any) -> None:
        def _exploding_gate(self: Any, *args: Any, **kwargs: Any) -> ValidationReport:
            raise DataContractError("gate boom is a hard failure")

        monkeypatch.setattr(StatisticalValidationGate, "evaluate_strategy", _exploding_gate)
        with pytest.raises(DataContractError, match="gate boom is a hard failure"):
            _orchestrate(_plan())

    def test_oos_exceptions_propagate(self, monkeypatch: Any) -> None:
        def _exploding_oos(*args: Any, **kwargs: Any) -> Any:
            raise DataContractError("oos boom is a hard failure")

        monkeypatch.setattr(orch_mod, "build_oos_backtest_evidence", _exploding_oos)
        with pytest.raises(DataContractError, match="oos boom is a hard failure"):
            _orchestrate(_plan())

    def test_plan_without_perturbation_spec_yields_missing_grid_reject(self) -> None:
        report = _orchestrate(_plan(perturbation_spec=None))
        assert report.perturbation_runs_executed == 0
        assert report.perturbation_grid is None
        assert report.census_state == CensusState.SEALED_COMPLETE
        assert report.phase_six_invoked is True
        report_six = report.phase_six_report
        assert report_six is not None
        assert report_six.verdict == ValidationGateVerdict.REJECT_MISSING_PERTURBATION_GRID
        assert report_six.is_tradeable_alpha is False

    def test_prevents_k_shrink_on_mixed_census_seal(self) -> None:
        # The seal authority itself must still enforce expected_k == len(trials).
        from acash.research.census_seal_authority import SearchTrialCensusSealAuthority

        records = tuple(
            SearchTrialRecord.create_declared(
                trial_id=tid,
                strategy_id=_STRATEGY_ID,
                hypothesis_id=_HYPOTHESIS_ID,
                feature_names=["qty_proxy"],
                parameters={"quantity": qty},
                trial_status=SearchTrialStatus.FAILED,
                failure_reason="injected failure",
            )
            for tid, qty in zip(_TRIAL_IDS, _QUANTITIES)
        )
        ledger = SearchTrialLedger(
            ledger_id="CENSUS_K_ANCHOR_TEST",
            strategy_id=_STRATEGY_ID,
            hypothesis_id=_HYPOTHESIS_ID,
            sharpe_space=SharpeSpace.ANNUAL,
            trials=records,
        )
        with pytest.raises(DataContractError, match="planned_trial_count K=5"):
            SearchTrialCensusSealAuthority.seal_census(ledger, expected_k=5)


# ---------------------------------------------------------------------------
# Report schema & module invariants
# ---------------------------------------------------------------------------


class TestReportSchemaAndModuleInvariants:
    def _minimal_report(self) -> PhaseFiveOrchestrationReport:
        return PhaseFiveOrchestrationReport(
            plan_id="p",
            strategy_id="s",
            hypothesis_id="h",
            planned_trial_count=1,
            actual_trial_count=1,
            ordered_trial_ids=("t",),
            successful_count=1,
            failed_count=0,
            invalid_count=0,
            census_state=CensusState.SEALED_COMPLETE,
            ledger_id="l",
            ledger_digest="0" * 64,
            sealed_by_owner="o",
            perturbation_runs_executed=0,
            phase_six_invoked=False,
        )

    def test_report_extra_forbid(self) -> None:
        data = self._minimal_report().model_dump()
        data["mystery_field"] = 123
        with pytest.raises(Exception, match="Extra inputs are not permitted"):
            PhaseFiveOrchestrationReport(**data)

    def test_report_is_frozen(self) -> None:
        report = self._minimal_report()
        with pytest.raises(Exception):
            report.census_state = CensusState.SEALED_MIXED

    def test_no_forbidden_imports_in_orchestrator_module(self) -> None:
        src_path = inspect.getsourcefile(orch_mod)
        assert src_path is not None
        source = Path(src_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = (
            "acash.execution",
            "acash.portfolio",
            "acash.runtime",
            "acash.risk",
            "acash.broker",
            "acash.networking",
            "acash.reinception",
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                for banned in forbidden:
                    if module == banned or module.startswith(banned + "."):
                        raise AssertionError(f"forbidden import in orchestrator: {module}")
        dynamic = ("eval", "exec", "compile", "__import__", "importlib")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
                if name in dynamic:
                    raise AssertionError(f"forbidden dynamic execution primitive: {name}")

    def test_no_bare_ledger_seal_outside_authority(self) -> None:
        src_path = inspect.getsourcefile(orch_mod)
        assert src_path is not None
        source = Path(src_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert "seal_census" in source
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "seal":
                    raise AssertionError(
                        "orchestrator invokes a bare `.seal()` method; sealing must go through "
                        "SearchTrialCensusSealAuthority.seal_census"
                    )