"""Unit tests for the Statistical Validation Gate master orchestrator."""

from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pytest

from acash.backtest.schema import BacktestExecutionSummary, BacktestManifest, RealityGapSummary
from acash.core.domain.exceptions import DataContractError
from acash.research.schema import ExpectedDirection, HypothesisSpecification, InvalidationCriteria
from acash.validation.deflated_sharpe import DeflatedSharpeEngine
from acash.validation.gate import StatisticalValidationGate, _compute_canonical_series_sha256
from acash.core.serialization import CanonicalConfigSerializer, deep_freeze_value
from acash.validation.schema import (
    ParameterPerturbationGrid,
    ParameterPerturbationPoint,
    SearchTrialLedger,
    SearchTrialRecord,
    SelectionCorrectionMode,
    SharpeSpace,
    ValidationConfig,
    ValidationGateVerdict,
)





def _make_mock_manifest(
    manifest_id: str,
    hypothesis_id: str = "HYP_01",
    strategy_config_hash: Optional[str] = None,
    sharpe: Decimal = Decimal("1.5"),
) -> BacktestManifest:
    """Helper creating a cryptographically valid BacktestManifest."""
    hyp_hash = "1" * 64
    eng_hash = "2" * 64
    strat_hash = strategy_config_hash or ("3" * 64)
    pyp_hash = "4" * 64
    git_hash = "5" * 40
    data_hash = "6" * 64

    exec_summary = BacktestExecutionSummary(
        total_orders=10,
        total_fills=10,
        total_volume_traded=Decimal("10000.0"),
        total_fees_paid=Decimal("10.0"),
        realized_pnl=Decimal("1000.0"),
        unrealized_pnl=Decimal("0.0"),
        ending_equity=Decimal("101000.0"),
        net_return_pct=Decimal("1.0"),
        sharpe_ratio=sharpe,
        max_drawdown_pct=Decimal("0.5"),
        win_rate_pct=Decimal("60.0"),
    )
    reality_gap = RealityGapSummary(
        phase4_analytical_edge_bps=Decimal("10.0"),
        phase5_simulated_realized_bps=Decimal("8.0"),
        reality_gap_bps=Decimal("2.0"),
    )
    return BacktestManifest(
        manifest_id=manifest_id,
        hypothesis_id=hypothesis_id,
        hypothesis_spec_sha256=hyp_hash,
        canonical_data_hashes=[data_hash],
        engine_config_hash=eng_hash,
        strategy_config_hash=strat_hash,
        prng_seed=42,
        pyproject_toml_sha256=pyp_hash,
        git_commit_hash=git_hash,
        execution_summary=exec_summary,
        reality_gap=reality_gap,
        computed_at_utc="2026-08-28T10:00:00Z",
        wall_clock_duration_ms=1000,
    )


def _make_valid_perturbation_grid(
    base_val: Decimal = Decimal("10.0"),
    sr: Decimal = Decimal("1.5"),
    strat_id: str = "STRAT_01",
    manifest_store: Optional[Dict[str, Any]] = None,
) -> ParameterPerturbationGrid:
    """Helper to construct a valid 3-point perturbation grid with distinct execution runs and manifests."""
    hyp_hash = "1" * 64
    strat_hash = "3" * 64
    expected_in = hashlib.sha256(f"{hyp_hash}:{strat_hash}".encode("utf-8")).hexdigest()

    points = []
    multipliers = [("left", Decimal("0.75")), ("base", Decimal("1.0")), ("right", Decimal("1.25"))]
    for label, mult in multipliers:
        p_val = base_val * mult
        man_id = f"MANIFEST_{strat_id}_{label.upper()}"
        man = _make_mock_manifest(manifest_id=man_id, sharpe=sr)
        if manifest_store is not None:
            manifest_store[man_id] = man
        pt = ParameterPerturbationPoint(
            parameter_value=p_val,
            run_id=f"run_{strat_id}_{label}",
            manifest_id=man_id,
            input_artifact_hash=expected_in,
            output_artifact_hash=man.compute_sha256(),
            actual_sharpe=sr,
        )
        points.append(pt)

    return ParameterPerturbationGrid(
        base_parameter_name="lookback",
        base_parameter_value=base_val,
        points=points,
    )


def _make_valid_hypothesis_spec(
    hypothesis_id: str = "HYP_01",
    primary_horizon: int = 1,
    target_symbol: str = "BTCUSDT",
) -> HypothesisSpecification:
    """Helper to construct a valid formal pre-registered hypothesis specification."""
    return HypothesisSpecification(
        hypothesis_id=hypothesis_id,
        hypothesis_version="v1.0.0",
        economic_rationale="Microstructure order flow imbalance predictive edge",
        target_symbol=target_symbol,
        feature_dependencies=["mom"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[primary_horizon],
        primary_horizon=primary_horizon,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-08-28T00:00:00Z",
        author="ResearchTeam",
    )


def _make_valid_trial_ledger(
    trial_return_matrix: np.ndarray,
    strategy_id: str = "STRAT_01",
    hypothesis_id: str = "HYP_01",
    ledger_id: str = "LEDGER_01",
    p_value: Decimal = Decimal("0.001"),
    is_sealed: bool = True,
    manifest_store: Optional[Dict[str, Any]] = None,
) -> SearchTrialLedger:
    """Helper to construct a sealed SearchTrialLedger bound to trial_return_matrix and populate manifest_store."""
    t_len, k_trials = trial_return_matrix.shape
    trials: List[SearchTrialRecord] = []
    for m in range(k_trials):
        col_m = trial_return_matrix[:, m]
        mean_m = float(np.mean(col_m))
        std_m = float(np.std(col_m, ddof=1)) if len(col_m) > 1 else 1.0
        sr_m_period = (mean_m / std_m) if std_m > 0 else 0.0
        features = ["mom"]
        params = {"period": 10 + m}
        cfg_hash = SearchTrialRecord.compute_config_sha256(features, params)
        man_id = f"MANIFEST_TRIAL_{strategy_id}_{m}"
        trial = SearchTrialRecord.create(
            trial_id=f"trial_{m}",
            strategy_id=strategy_id,
            hypothesis_id=hypothesis_id,
            feature_names=features,
            parameters=params,
            in_sample_sharpe=Decimal(f"{sr_m_period:.6f}"),
            p_value=p_value,
            execution_manifest_id=man_id,
            in_sample_returns=list(col_m),
        )
        trials.append(trial)
        if manifest_store is not None:
            manifest_store[man_id] = _make_mock_manifest(
                manifest_id=man_id,
                hypothesis_id=hypothesis_id,
                strategy_config_hash=cfg_hash,
                sharpe=Decimal(f"{sr_m_period:.6f}"),
            )
    ledger = SearchTrialLedger(
        ledger_id=ledger_id,
        strategy_id=strategy_id,
        hypothesis_id=hypothesis_id,
        trials=tuple(trials),
        sharpe_space=SharpeSpace.PERIOD,
        is_sealed=False,
    )
    if is_sealed:
        return ledger.seal(sealed_at_utc="2026-08-28T00:00:00Z")
    return ledger


def test_statistical_validation_gate_pass_tradeable_alpha() -> None:
    """Verify that a genuine robust strategy passing all gates receives PASS_TRADEABLE_ALPHA."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    # Strong persistent positive returns
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_TSMOM_001", primary_horizon=1)
    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_MOM_001", manifest_store=manifest_store)
    trial_matrix = np.zeros((1000, 5), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    for m in range(1, 5):
        trial_matrix[:, m] = np.random.normal(0.0020 - m * 0.0005, 0.0040, 1000)

    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        ledger_id="LEDGER_MOM_001",
        manifest_store=manifest_store,
    )

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
    )

    assert report.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA
    assert report.is_tradeable_alpha is True
    assert report.dsr_result is not None
    assert report.dsr_result.effective_trials_k == 5
    assert report.dsr_result.selection_correction_mode == SelectionCorrectionMode.MULTIPLE_TRIAL
    assert report.dsr_result.sr0_estimator == "EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1"
    assert report.dsr_result.sharpe_space == SharpeSpace.ANNUAL
    assert report.dsr_result.inference_space == SharpeSpace.PERIOD

    assert report.multiple_testing_result is not None
    assert len(report.multiple_testing_result.raw_p_values) == 5  # Strictly coupled K
    assert report.dsr_result.is_statistically_significant is True
    assert report.overfitting_report is not None
    assert report.overfitting_report.is_pbo_acceptable is True
    assert report.overfitting_report.analytical_friction_monotonicity_passed is True
    assert report.oos_retention_pct is not None
    assert report.oos_retention_pct > Decimal("50.0")


def test_statistical_validation_gate_fail_closed_on_missing_ledger() -> None:
    """Verify that omitting trial_ledger strictly fails closed with REJECT_MISSING_TRIAL_LEDGER and ZERO statistical evaluation."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_TSMOM_001")

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=[],
        manifest_store={},
        out_of_sample_returns=oos_returns,
        trial_ledger=None,
    )

    assert report.verdict == ValidationGateVerdict.REJECT_MISSING_TRIAL_LEDGER
    assert report.is_tradeable_alpha is False
    assert report.in_sample_sharpe is None
    assert report.dsr_result is None
    assert report.multiple_testing_result is None
    assert report.overfitting_report is None
    assert report.out_of_sample_sharpe is None
    assert report.oos_retention_pct is None

    # Canonical serialization must succeed cleanly without fabricated objects
    ev_json = report.to_canonical_evidence_json()
    assert "MISSING_TRIAL_LEDGER" in report.evidence_digest or len(report.evidence_digest) == 64
    assert json.loads(ev_json)["dsr_result"] is None
    assert json.loads(ev_json)["in_sample_sharpe"] is None


def test_statistical_validation_gate_fail_closed_on_missing_oos() -> None:
    """Verify that missing or insufficient OOS returns strictly fail closed with REJECT_MISSING_OOS_DATA and zero evaluation."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_TSMOM_001")

    trial = SearchTrialRecord.create(
        trial_id="trial_1",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        feature_names=["mom"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
        execution_manifest_id="MANIFEST_01",
        in_sample_returns=is_returns,
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        trials=(trial,),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    # 1. None OOS returns
    report_none = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=["trial_1"],
        manifest_store={},
        out_of_sample_returns=None,
        trial_ledger=ledger,
    )
    assert report_none.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA
    assert report_none.is_tradeable_alpha is False
    assert report_none.in_sample_sharpe is None
    assert report_none.dsr_result is None
    assert report_none.multiple_testing_result is None
    assert report_none.overfitting_report is None
    assert report_none.out_of_sample_sharpe is None
    assert report_none.oos_retention_pct is None

    # 2. Too short OOS returns (< 4 bars)
    report_short = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=["trial_1"],
        manifest_store={},
        out_of_sample_returns=[0.01, 0.02],
        trial_ledger=ledger,
    )
    assert report_short.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA
    assert report_short.is_tradeable_alpha is False
    assert report_short.in_sample_sharpe is None
    assert report_short.out_of_sample_sharpe is None


def test_statistical_validation_gate_fail_closed_on_missing_perturbation_grid() -> None:
    """Verify that omitting perturbation_grid strictly fails closed with REJECT_MISSING_PERTURBATION_GRID and zero synthetic grid."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_TSMOM_001")

    trial = SearchTrialRecord.create(
        trial_id="trial_1",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        feature_names=["mom"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
        execution_manifest_id="MANIFEST_01",
        in_sample_returns=is_returns,
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        trials=(trial,),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=["trial_1"],
        manifest_store={},
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        perturbation_grid=None,  # Missing perturbation grid
    )

    assert report.verdict == ValidationGateVerdict.REJECT_MISSING_PERTURBATION_GRID
    assert report.is_tradeable_alpha is False
    assert report.in_sample_sharpe is None
    assert report.dsr_result is None
    assert report.multiple_testing_result is None
    assert report.overfitting_report is None
    assert report.out_of_sample_sharpe is None
    assert report.oos_retention_pct is None

    # Canonical serialization verification
    ev_json = report.to_canonical_evidence_json()
    assert json.loads(ev_json)["in_sample_sharpe"] is None
    assert json.loads(ev_json)["overfitting_report"] is None


def test_ledger_duplicate_trial_id_rejection() -> None:
    """Verify that SearchTrialLedger strictly rejects duplicate trial IDs."""
    h = "a" * 64
    cfg_h = "b" * 64
    record_1 = SearchTrialRecord(
        trial_id="duplicate_id",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
        in_sample_return_series_sha256=h,
        config_sha256=cfg_h,
        execution_manifest_id="MAN_01",
    )
    record_2 = SearchTrialRecord(
        trial_id="duplicate_id",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f2"],
        parameters={},
        in_sample_sharpe=Decimal("1.2"),
        p_value=Decimal("0.03"),
        in_sample_return_series_sha256=h,
        config_sha256=cfg_h,
        execution_manifest_id="MAN_02",
    )

    with pytest.raises(DataContractError, match="duplicate trial_ids"):
        SearchTrialLedger(
            ledger_id="LEDGER_01",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            trials=(record_1, record_2),
        )


def test_parameter_perturbation_grid_distinct_lineage_and_exact_geometry() -> None:
    """Verify that ParameterPerturbationGrid enforces distinct runs, manifests, hashes, and exact geometry."""
    theta = Decimal("10.0")
    h1 = "a" * 64
    h2 = "b" * 64
    h3 = "c" * 64

    # 1. Duplicate run_ids rejected
    points_dup_run = [
        ParameterPerturbationPoint(
            parameter_value=Decimal("7.5"),
            run_id="same_run",
            manifest_id="MANIFEST_01",
            input_artifact_hash=h1,
            output_artifact_hash=h1,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("10.0"),
            run_id="same_run",
            manifest_id="MANIFEST_02",
            input_artifact_hash=h2,
            output_artifact_hash=h2,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("12.5"),
            run_id="diff_run",
            manifest_id="MANIFEST_03",
            input_artifact_hash=h3,
            output_artifact_hash=h3,
            actual_sharpe=Decimal("1.5"),
        ),
    ]
    with pytest.raises(DataContractError, match="3 distinct execution run_ids"):
        ParameterPerturbationGrid(base_parameter_name="lookback", base_parameter_value=theta, points=points_dup_run)

    # 2. Duplicate manifest_ids rejected
    points_dup_man = [
        ParameterPerturbationPoint(
            parameter_value=Decimal("7.5"),
            run_id="run_1",
            manifest_id="MANIFEST_SAME",
            input_artifact_hash=h1,
            output_artifact_hash=h1,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("10.0"),
            run_id="run_2",
            manifest_id="MANIFEST_SAME",
            input_artifact_hash=h2,
            output_artifact_hash=h2,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("12.5"),
            run_id="run_3",
            manifest_id="MANIFEST_03",
            input_artifact_hash=h3,
            output_artifact_hash=h3,
            actual_sharpe=Decimal("1.5"),
        ),
    ]
    with pytest.raises(DataContractError, match="3 distinct manifest_ids"):
        ParameterPerturbationGrid(base_parameter_name="lookback", base_parameter_value=theta, points=points_dup_man)

    # 3. Non-exact geometry rejected (e.g. 0.750001 != 0.75)
    points_inexact = [
        ParameterPerturbationPoint(
            parameter_value=Decimal("7.500001"),
            run_id="run_1",
            manifest_id="MANIFEST_01",
            input_artifact_hash=h1,
            output_artifact_hash=h1,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("10.0"),
            run_id="run_2",
            manifest_id="MANIFEST_02",
            input_artifact_hash=h2,
            output_artifact_hash=h2,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("12.5"),
            run_id="run_3",
            manifest_id="MANIFEST_03",
            input_artifact_hash=h3,
            output_artifact_hash=h3,
            actual_sharpe=Decimal("1.5"),
        ),
    ]
    with pytest.raises(DataContractError, match="does not exactly equal 0.75"):
        ParameterPerturbationGrid(base_parameter_name="lookback", base_parameter_value=theta, points=points_inexact)

    # 4. Out-of-order points rejected
    points_unordered = [
        ParameterPerturbationPoint(
            parameter_value=Decimal("10.0"),  # Mid in pos 0
            run_id="run_1",
            manifest_id="MANIFEST_01",
            input_artifact_hash=h1,
            output_artifact_hash=h1,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("7.5"),
            run_id="run_2",
            manifest_id="MANIFEST_02",
            input_artifact_hash=h2,
            output_artifact_hash=h2,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("12.5"),
            run_id="run_3",
            manifest_id="MANIFEST_03",
            input_artifact_hash=h3,
            output_artifact_hash=h3,
            actual_sharpe=Decimal("1.5"),
        ),
    ]
    with pytest.raises(DataContractError, match="does not exactly equal 0.75"):
        ParameterPerturbationGrid(base_parameter_name="lookback", base_parameter_value=theta, points=points_unordered)


def test_deterministic_validation_report_id_and_digests() -> None:
    """Verify that identical strategy evaluation inputs produce bitwise-identical digests and validation_id."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)
    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        manifest_store=manifest_store,
    )

    report_1 = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
        fixed_created_timestamp_utc="2026-08-28T10:00:00Z",
    )

    report_2 = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
        fixed_created_timestamp_utc="2026-08-28T12:00:00Z",  # Different runtime timestamp
    )

    # validation_id, evidence_digest, and decision_digest MUST be 100% identical
    assert report_1.evidence_digest == report_2.evidence_digest
    assert report_1.decision_digest == report_2.decision_digest
    assert report_1.validation_id == report_2.validation_id


def test_canonical_json_serialization_separation() -> None:
    """Verify clean separation between to_canonical_evidence_json() and to_canonical_report_json()."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)
    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        manifest_store=manifest_store,
    )

    report = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
    )

    # 1. Canonical Evidence JSON (pure mathematical facts)
    ev_json = report.to_canonical_evidence_json()
    ev_data = json.loads(ev_json)
    assert "evidence_digest" in ev_data
    assert "decision_digest" not in ev_data  # No governance verdict/decision in evidence!
    assert "verdict" not in ev_data
    assert "created_timestamp_utc" not in ev_data

    # 2. Canonical Report JSON (sealed governance record)
    rep_json = report.to_canonical_report_json()
    rep_data = json.loads(rep_json)
    assert "decision_digest" in rep_data
    assert "evidence_digest" in rep_data
    assert "verdict" in rep_data
    assert "created_timestamp_utc" not in rep_data


def test_parameter_perturbation_point_manifest_binding_invariants() -> None:
    """Verify 4-way manifest binding invariants: manifest_id, execution_sharpe, input hash, output hash."""
    hyp_hash = "1" * 64
    eng_hash = "2" * 64
    strat_hash = "3" * 64
    pyp_hash = "4" * 64
    git_hash = "5" * 40
    data_hash = "6" * 64
    expected_in_hash = hashlib.sha256(f"{hyp_hash}:{strat_hash}".encode("utf-8")).hexdigest()

    exec_summary = BacktestExecutionSummary(
        total_orders=10,
        total_fills=10,
        total_volume_traded=Decimal("100000.0"),
        total_fees_paid=Decimal("20.0"),
        realized_pnl=Decimal("1500.0"),
        unrealized_pnl=Decimal("0.0"),
        ending_equity=Decimal("101480.0"),
        net_return_pct=Decimal("1.48"),
        sharpe_ratio=Decimal("1.650000000000000000"),
        sortino_ratio=Decimal("2.1"),
        max_drawdown_pct=Decimal("0.5"),
        win_rate_pct=Decimal("60.0"),
        profit_factor=Decimal("1.8"),
    )

    reality_gap = RealityGapSummary(
        phase4_analytical_edge_bps=Decimal("10.0"),
        phase5_simulated_realized_bps=Decimal("8.0"),
        reality_gap_bps=Decimal("2.0"),
    )

    manifest = BacktestManifest(
        manifest_id="MANIFEST_MOM_P75_TEST",
        hypothesis_id="HYP_01",
        hypothesis_spec_sha256=hyp_hash,
        canonical_data_hashes=[data_hash],
        engine_config_hash=eng_hash,
        strategy_config_hash=strat_hash,
        prng_seed=42,
        pyproject_toml_sha256=pyp_hash,
        git_commit_hash=git_hash,
        execution_summary=exec_summary,
        reality_gap=reality_gap,
        computed_at_utc="2026-08-28T10:00:00Z",
        wall_clock_duration_ms=1200,
    )

    manifest_output_hash = hashlib.sha256(manifest.to_canonical_json().encode("utf-8")).hexdigest()

    # 1. Perfectly matched point
    point_valid = ParameterPerturbationPoint(
        parameter_value=Decimal("7.5"),
        run_id="run_p75",
        manifest_id="MANIFEST_MOM_P75_TEST",
        input_artifact_hash=expected_in_hash,
        output_artifact_hash=manifest_output_hash,
        actual_sharpe=Decimal("1.650000000000000000"),
    )
    assert point_valid.validate_manifest_binding(manifest) is True

    # 2. Manifest ID mismatch
    point_bad_id = ParameterPerturbationPoint(
        parameter_value=Decimal("7.5"),
        run_id="run_p75",
        manifest_id="MANIFEST_DIFFERENT_ID",
        input_artifact_hash=expected_in_hash,
        output_artifact_hash=manifest_output_hash,
        actual_sharpe=Decimal("1.650000000000000000"),
    )
    with pytest.raises(DataContractError, match="Manifest ID mismatch"):
        point_bad_id.validate_manifest_binding(manifest)

    # 3. Sharpe ratio mismatch
    point_bad_sr = ParameterPerturbationPoint(
        parameter_value=Decimal("7.5"),
        run_id="run_p75",
        manifest_id="MANIFEST_MOM_P75_TEST",
        input_artifact_hash=expected_in_hash,
        output_artifact_hash=manifest_output_hash,
        actual_sharpe=Decimal("1.800000000000000000"),
    )
    with pytest.raises(DataContractError, match="Sharpe ratio mismatch"):
        point_bad_sr.validate_manifest_binding(manifest)

    # 4. Output artifact hash mismatch
    point_bad_out = ParameterPerturbationPoint(
        parameter_value=Decimal("7.5"),
        run_id="run_p75",
        manifest_id="MANIFEST_MOM_P75_TEST",
        input_artifact_hash=expected_in_hash,
        output_artifact_hash="f" * 64,
        actual_sharpe=Decimal("1.650000000000000000"),
    )
    with pytest.raises(DataContractError, match="Output artifact hash mismatch"):
        point_bad_out.validate_manifest_binding(manifest)

    # 5. Input artifact hash mismatch (random hash)
    point_bad_in = ParameterPerturbationPoint(
        parameter_value=Decimal("7.5"),
        run_id="run_p75",
        manifest_id="MANIFEST_MOM_P75_TEST",
        input_artifact_hash="e" * 64,
        output_artifact_hash=manifest_output_hash,
        actual_sharpe=Decimal("1.650000000000000000"),
    )
    with pytest.raises(DataContractError, match="Input artifact hash mismatch"):
        point_bad_in.validate_manifest_binding(manifest)


def test_statistical_validation_gate_fail_closed_precedes_sample_size_check() -> None:
    """Verify that missing governance prerequisites fail closed through verdict before in-sample size validation."""
    gate = StatisticalValidationGate()

    # in_sample has only 2 bars (< 4 minimum)
    short_is = [0.01, 0.02]
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    # 1. Missing ledger with short IS -> REJECT_MISSING_TRIAL_LEDGER (not DataContractError)
    rep_ledger = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=short_is,
        trial_matrix_column_trial_ids=[],
        manifest_store={},
        out_of_sample_returns=[0.01, 0.02, 0.03, 0.04],
        trial_ledger=None,
    )
    assert rep_ledger.verdict == ValidationGateVerdict.REJECT_MISSING_TRIAL_LEDGER

    # 2. Missing OOS with short IS -> REJECT_MISSING_OOS_DATA
    trial = SearchTrialRecord.create(
        trial_id="t1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
        execution_manifest_id="MANIFEST_01",
        in_sample_returns=short_is,
    )
    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=(trial,),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    rep_oos = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=short_is,
        trial_matrix_column_trial_ids=["t1"],
        manifest_store={},
        out_of_sample_returns=None,
        trial_ledger=ledger,
    )
    assert rep_oos.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA

    # 3. Missing Perturbation Grid with short IS -> REJECT_MISSING_PERTURBATION_GRID
    rep_grid = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=short_is,
        trial_matrix_column_trial_ids=["t1"],
        manifest_store={},
        out_of_sample_returns=[0.01, 0.02, 0.03, 0.04],
        trial_ledger=ledger,
        perturbation_grid=None,
    )
    assert rep_grid.verdict == ValidationGateVerdict.REJECT_MISSING_PERTURBATION_GRID


def test_statistical_validation_gate_verifies_manifest_store_repository() -> None:
    """Verify that StatisticalValidationGate strictly verifies all candidate trials and perturbation points against manifest_store."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_STORE_01", manifest_store=manifest_store)
    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_STORE_01",
        hypothesis_id="HYP_01",
        manifest_store=manifest_store,
    )

    # 1. Successful verification against manifest_store
    report = gate.evaluate_strategy(
        strategy_id="STRAT_STORE_01",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        perturbation_grid=grid,
        manifest_store=manifest_store,
    )
    assert report.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA

    # 2. Rejection when a perturbation manifest is missing from manifest_store
    incomplete_store = {k: v for k, v in manifest_store.items() if k != "MANIFEST_STRAT_STORE_01_RIGHT"}
    with pytest.raises(DataContractError, match="missing from manifest_store repository"):
        gate.evaluate_strategy(
            strategy_id="STRAT_STORE_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
            perturbation_grid=grid,
            manifest_store=incomplete_store,
        )


def test_statistical_validation_gate_fail_closed_on_missing_cpcv_evidence() -> None:
    """Verify that omitting trial_return_matrix strictly fails closed with REJECT_MISSING_CPCV_EVIDENCE."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial = SearchTrialRecord.create(
        trial_id="t1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.001"),
        execution_manifest_id="MANIFEST_01",
        in_sample_returns=is_returns,
    )
    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=(trial,),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")
    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)

    # Omitting CPCV evidence
    rep = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=["t1"],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        perturbation_grid=grid,
        trial_return_matrix=None,
    )
    assert rep.verdict == ValidationGateVerdict.REJECT_MISSING_CPCV_EVIDENCE
    assert rep.is_tradeable_alpha is False
    assert rep.overfitting_report is None


def test_statistical_validation_gate_multiple_testing_fwer_gating() -> None:
    """Verify that failing Holm-Bonferroni FWER test triggers REJECT_MULTIPLE_TESTING_FWER."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 3), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0010, 0.0040, 500)
    trial_matrix[:, 2] = np.random.normal(0.0005, 0.0040, 500)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_FWER", manifest_store=manifest_store)

    # Insignificant trials: p-value = 0.50 -> FWER fails!
    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_FWER",
        hypothesis_id="HYP_01",
        ledger_id="L_FWER",
        p_value=Decimal("0.50"),
        manifest_store=manifest_store,
    )

    rep = gate.evaluate_strategy(
        strategy_id="STRAT_FWER",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
    )
    assert rep.verdict == ValidationGateVerdict.REJECT_MULTIPLE_TESTING_FWER
    assert rep.is_tradeable_alpha is False


def test_statistical_validation_gate_haircut_sharpe_gating() -> None:
    """Verify that Haircut Sharpe falling below min_haircut_sharpe threshold triggers REJECT_HAIRCUT_SHARPE."""
    # Configure high minimum haircut Sharpe requirement
    cfg = ValidationConfig(min_haircut_sharpe=Decimal("2.50"))
    gate = StatisticalValidationGate(config=cfg)

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 500)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_HC", manifest_store=manifest_store)
    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_HC",
        hypothesis_id="HYP_01",
        ledger_id="L_HC",
        p_value=Decimal("0.001"),
        manifest_store=manifest_store,
    )

    rep = gate.evaluate_strategy(
        strategy_id="STRAT_HC",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
    )
    assert rep.verdict == ValidationGateVerdict.REJECT_HAIRCUT_SHARPE
    assert rep.is_tradeable_alpha is False


def test_statistical_validation_gate_rejects_m_k_ledger_mismatch() -> None:
    """Verify that Gate strictly rejects when trial_return_matrix M != ledger K."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    # Ledger has K = 3 trials
    manifest_store: Dict[str, Any] = {}
    trials = [
        SearchTrialRecord.create(
            trial_id=f"t_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.001"),
            execution_manifest_id=f"MAN_{i}",
            in_sample_returns=is_returns,
        )
        for i in range(3)
    ]
    for t in trials:
        manifest_store[t.execution_manifest_id] = _make_mock_manifest(
            manifest_id=t.execution_manifest_id,
            hypothesis_id="HYP_01",
            strategy_config_hash=t.config_sha256,
        )

    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=tuple(trials),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)
    # M = 2 != K = 3
    mismatched_matrix = np.zeros((500, 2), dtype=np.float64)
    mismatched_matrix[:, 0] = np.array([float(x) for x in is_returns])

    with pytest.raises(DataContractError, match="candidate count M .* does not match SearchTrialLedger K"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["t_0", "t_1", "t_2"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=mismatched_matrix,
            perturbation_grid=grid,
        )


def test_statistical_validation_gate_rejects_is_returns_matrix_column_0_mismatch() -> None:
    """Verify that Gate strictly rejects when trial_return_matrix column 0 != in_sample_returns."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns])
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 500)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)
    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        manifest_store=manifest_store,
    )

    # Column 0 has different random returns
    divergent_matrix = np.random.normal(0.0050, 0.0040, (500, 2))

    with pytest.raises(DataContractError, match="column 0 .* does not match in_sample_returns"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=divergent_matrix,
            perturbation_grid=grid,
        )


def test_statistical_validation_gate_binds_real_label_horizon_and_embargo() -> None:
    """Verify that Gate strictly evaluates CPCV with custom research label_horizon H and embargo_bars E."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 500))

    spec_h20 = _make_valid_hypothesis_spec(hypothesis_id="HYP_01", primary_horizon=20)
    spec_h1 = _make_valid_hypothesis_spec(hypothesis_id="HYP_01", primary_horizon=1)

    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_HORIZON", manifest_store=manifest_store)
    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_HORIZON",
        hypothesis_id="HYP_01",
        manifest_store=manifest_store,
    )

    # 1. Standard evaluate with H=20, E=10
    rep_h20 = gate.evaluate_strategy(
        strategy_id="STRAT_HORIZON",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec_h20,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=["trial_0", "trial_1"],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
        embargo_bars=10,
        fixed_created_timestamp_utc="2026-08-28T10:00:00Z",
    )
    assert rep_h20.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA

    # 2. Evaluate with H=1, E=5
    rep_h1 = gate.evaluate_strategy(
        strategy_id="STRAT_HORIZON",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec_h1,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=["trial_0", "trial_1"],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
        embargo_bars=5,
        fixed_created_timestamp_utc="2026-08-28T10:00:00Z",
    )
    # The evidence digest MUST differ because label horizon and embargo are bound into evidence
    assert rep_h20.evidence_digest != rep_h1.evidence_digest


def test_statistical_validation_gate_rejects_trial_matrix_column_trial_ids_mismatch() -> None:
    """Verify that Gate strictly rejects when trial_matrix_column_trial_ids order does not match ledger."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns])
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 500)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)
    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        manifest_store=manifest_store,
    )

    # Passing inverted column trial IDs ["trial_1", "trial_0"]
    with pytest.raises(DataContractError, match="does not match ordered ledger trial_ids"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["trial_1", "trial_0"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            perturbation_grid=grid,
        )


def test_overfitting_engine_is_tie_symmetric_policy() -> None:
    """Verify that OverfittingEngine.calculate_pbo evaluates tied in-sample winners symmetrically without argmax bias."""
    from acash.validation.overfitting import OverfittingEngine

    # 1 split, 3 candidate models where model 0 and model 1 have identical IS Sharpe
    is_mat = np.array([[2.0, 2.0, 1.0]], dtype=np.float64)
    oos_mat = np.array([[3.0, 1.0, 2.0]], dtype=np.float64)

    pbo, logit_mean, logit_std = OverfittingEngine.calculate_pbo(is_mat, oos_mat)
    assert pbo == 0.0
    assert abs(logit_mean) < 1e-6


def test_statistical_validation_gate_binds_hypothesis_specification_horizon() -> None:
    """Verify that Gate strictly validates label_horizon against pre-registered HypothesisSpecification.primary_horizon."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 500))

    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_SPEC_01", primary_horizon=20)
    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_SPEC", manifest_store=manifest_store)
    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_SPEC",
        hypothesis_id="HYP_SPEC_01",
        manifest_store=manifest_store,
    )

    # 1. Successful validation when label_horizon strictly matches spec.primary_horizon (20)
    rep = gate.evaluate_strategy(
        strategy_id="STRAT_SPEC",
        hypothesis_id="HYP_SPEC_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=["trial_0", "trial_1"],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
    )
    assert rep.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA


def test_statistical_validation_gate_verifies_candidate_return_series_sha256() -> None:
    """Verify that Gate strictly checks cryptographic return series SHA-256 for all ledger trials."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 500))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_SHA", manifest_store=manifest_store)
    ledger_valid = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_SHA",
        hypothesis_id="HYP_01",
        manifest_store=manifest_store,
    )

    # 1. Successful evaluation when ledger registered hashes match matrix columns exactly
    rep = gate.evaluate_strategy(
        strategy_id="STRAT_SHA",
        hypothesis_id="HYP_01",
        hypothesis_spec=spec,
        in_sample_returns=is_returns,
        trial_matrix_column_trial_ids=["trial_0", "trial_1"],
        manifest_store=manifest_store,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger_valid,
        trial_return_matrix=trial_matrix,
        perturbation_grid=grid,
    )
    assert rep.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA

    # 2. Rejection when a trial's return series hash is tampered/mismatched
    trials_tampered = [
        ledger_valid.trials[0],
        SearchTrialRecord(
            trial_id="trial_1",
            strategy_id="STRAT_SHA",
            hypothesis_id="HYP_01",
            feature_names=["mom"],
            parameters={"period": 11},
            in_sample_sharpe=Decimal("0.5"),
            p_value=Decimal("0.050"),
            in_sample_return_series_sha256="deadbeef" * 8,  # Tampered hash
            config_sha256=ledger_valid.trials[1].config_sha256,
            execution_manifest_id=ledger_valid.trials[1].execution_manifest_id,
        ),
    ]
    ledger_tampered = SearchTrialLedger(
        ledger_id="L_SHA_TAMPERED",
        strategy_id="STRAT_SHA",
        hypothesis_id="HYP_01",
        trials=tuple(trials_tampered),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    with pytest.raises(DataContractError, match="in_sample_return_series_sha256 .* does not match"):
        gate.evaluate_strategy(
            strategy_id="STRAT_SHA",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["trial_0", "trial_1"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger_tampered,
            trial_return_matrix=trial_matrix,
            perturbation_grid=grid,
        )


def test_overfitting_engine_rejects_malformed_or_non_finite_matrices() -> None:
    """Verify that OverfittingEngine.calculate_pbo strictly rejects NaN, Inf, and shape mismatches."""
    from acash.validation.overfitting import OverfittingEngine

    # 1. NaN in matrix
    is_nan = np.array([[1.0, np.nan], [2.0, 1.5]], dtype=np.float64)
    oos_valid = np.array([[1.0, 1.2], [2.0, 1.5]], dtype=np.float64)
    with pytest.raises(DataContractError, match="contain non-finite values"):
        OverfittingEngine.calculate_pbo(is_nan, oos_valid)

    # 2. Infinite in matrix
    is_inf = np.array([[1.0, np.inf], [2.0, 1.5]], dtype=np.float64)
    with pytest.raises(DataContractError, match="contain non-finite values"):
        OverfittingEngine.calculate_pbo(is_inf, oos_valid)

    # 3. Shape mismatch
    oos_mismatch = np.array([[1.0, 1.2, 0.5]], dtype=np.float64)
    is_valid = np.array([[1.0, 1.2], [2.0, 1.5]], dtype=np.float64)
    with pytest.raises(DataContractError, match="matrix shape mismatch"):
        OverfittingEngine.calculate_pbo(is_valid, oos_mismatch)

    # 4. M < 2 models
    is_m1 = np.array([[1.0], [2.0]], dtype=np.float64)
    oos_m1 = np.array([[1.0], [2.0]], dtype=np.float64)
    with pytest.raises(DataContractError, match="must contain at least M >= 2"):
        OverfittingEngine.calculate_pbo(is_m1, oos_m1)


def test_statistical_validation_gate_rejects_missing_or_mismatched_hypothesis_spec() -> None:
    """Verify that Gate strictly rejects missing or mismatched hypothesis_spec."""
    gate = StatisticalValidationGate()

    is_returns = [0.01, 0.02, 0.03, 0.04]
    spec_wrong_id = _make_valid_hypothesis_spec(hypothesis_id="HYP_OTHER")

    # Mismatched hypothesis_id between spec and evaluate_strategy
    with pytest.raises(DataContractError, match="does not match evaluate_strategy hypothesis_id"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec_wrong_id,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=[],
            manifest_store={},
        )


def test_statistical_validation_gate_rejects_unsealed_trial_ledger() -> None:
    """Verify that Gate strictly rejects SearchTrialLedger where is_sealed=False."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 500)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)

    # Unsealed ledger (is_sealed=False)
    unsealed_ledger = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        is_sealed=False,
        manifest_store=manifest_store,
    )

    with pytest.raises(DataContractError, match="must be in SEALED state before validation"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["trial_0", "trial_1"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=unsealed_ledger,
            trial_return_matrix=trial_matrix,
            perturbation_grid=grid,
        )


def test_statistical_validation_gate_rejects_tampered_candidate_config_sha256() -> None:
    """Verify that Gate strictly rejects when trial config_sha256 does not match canonical parameters hash."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 500)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)
    ledger_valid = _make_valid_trial_ledger(
        trial_return_matrix=trial_matrix,
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        manifest_store=manifest_store,
    )

    trials_tampered = [
        ledger_valid.trials[0],
        SearchTrialRecord(
            trial_id="trial_1",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["mom"],
            parameters={"period": 11},
            in_sample_sharpe=Decimal("0.5"),
            p_value=Decimal("0.050"),
            in_sample_return_series_sha256=ledger_valid.trials[1].in_sample_return_series_sha256,
            config_sha256="deadbeef" * 8,  # Tampered config hash
            execution_manifest_id=ledger_valid.trials[1].execution_manifest_id,
        ),
    ]
    ledger_tampered = SearchTrialLedger(
        ledger_id="L_CFG_TAMPERED",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=tuple(trials_tampered),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    with pytest.raises(DataContractError, match="registered config_sha256 .* does not match"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["trial_0", "trial_1"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger_tampered,
            trial_return_matrix=trial_matrix,
            perturbation_grid=grid,
        )


def test_statistical_validation_gate_rejects_missing_candidate_execution_manifest() -> None:
    """Verify that Gate strictly rejects when trial execution_manifest_id is not in manifest_store."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 500)

    # Trial with execution_manifest_id that does not exist in store
    sr_0 = float(np.mean(trial_matrix[:, 0])) / float(np.std(trial_matrix[:, 0], ddof=1))
    sr_1 = float(np.mean(trial_matrix[:, 1])) / float(np.std(trial_matrix[:, 1], ddof=1))
    trials = [
        SearchTrialRecord.create(
            trial_id="trial_0",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["mom"],
            parameters={"period": 10},
            in_sample_sharpe=Decimal(f"{sr_0:.6f}"),
            p_value=Decimal("0.001"),
            execution_manifest_id="MANIFEST_NON_EXISTENT",
            in_sample_returns=list(trial_matrix[:, 0]),
        ),
        SearchTrialRecord.create(
            trial_id="trial_1",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["mom"],
            parameters={"period": 11},
            in_sample_sharpe=Decimal(f"{sr_1:.6f}"),
            p_value=Decimal("0.001"),
            execution_manifest_id="MANIFEST_TRIAL_1",
            in_sample_returns=list(trial_matrix[:, 1]),
        ),
    ]
    ledger = SearchTrialLedger(
        ledger_id="L_MAN",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=tuple(trials),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)
    manifest_store["MANIFEST_TRIAL_1"] = _make_mock_manifest("MANIFEST_TRIAL_1", sharpe=Decimal(f"{sr_1:.6f}"))

    with pytest.raises(DataContractError, match="execution manifest 'MANIFEST_NON_EXISTENT' missing"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["trial_0", "trial_1"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            perturbation_grid=grid,
        )


def test_search_trial_record_rejects_missing_returns_and_hash() -> None:
    """Verify that SearchTrialRecord strictly fails-closed when neither in_sample_returns nor hash is supplied (zero synthetic fallback)."""
    with pytest.raises(DataContractError, match="in_sample_return_series_sha256 requires actual in_sample_returns"):
        SearchTrialRecord.model_validate({
            "trial_id": "trial_missing",
            "strategy_id": "STRAT_01",
            "hypothesis_id": "HYP_01",
            "feature_names": ["f1"],
            "parameters": {},
            "in_sample_sharpe": Decimal("1.5"),
            "p_value": Decimal("0.01"),
            "execution_manifest_id": "MANIFEST_01",
            # Omitting both in_sample_returns and in_sample_return_series_sha256
        })

    with pytest.raises(DataContractError, match="Must provide either in_sample_returns or in_sample_return_series_sha256"):
        SearchTrialRecord.create(
            trial_id="trial_missing_create",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.01"),
            execution_manifest_id="MANIFEST_01",
            in_sample_returns=None,
            in_sample_return_series_sha256=None,
        )



def test_search_trial_ledger_sealing_lifecycle() -> None:
    """Verify SearchTrialLedger OPEN -> SEAL -> SEALED lifecycle and tamper detection."""
    h = "a" * 64
    cfg_h = "b" * 64
    record = SearchTrialRecord(
        trial_id="t1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
        in_sample_return_series_sha256=h,
        config_sha256=cfg_h,
        execution_manifest_id="MAN_01",
    )

    # 1. Unsealed initial state
    ledger_open = SearchTrialLedger(
        ledger_id="LEDGER_SEAL_TEST",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=(record,),
    )
    assert ledger_open.is_sealed is False
    assert ledger_open.ledger_digest is None

    # 2. Sealing transition
    ledger_sealed = ledger_open.seal(sealed_at_utc="2026-08-28T12:00:00Z")
    assert ledger_sealed.is_sealed is True
    assert ledger_sealed.sealed_at_utc == "2026-08-28T12:00:00Z"
    assert ledger_sealed.ledger_digest is not None
    assert len(ledger_sealed.ledger_digest) == 64

    # 3. Tampering with digest triggers DataContractError
    with pytest.raises(DataContractError, match="ledger_digest mismatch"):
        SearchTrialLedger(
            ledger_id="LEDGER_SEAL_TEST",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            trials=(record,),
            is_sealed=True,
            sealed_at_utc="2026-08-28T12:00:00Z",
            ledger_digest="deadbeef" * 8,  # Invalid digest
        )


def test_statistical_validation_gate_rejects_manifest_mismatch() -> None:
    """Verify that Gate rejects when manifest hypothesis or strategy_config_hash does not match candidate trial."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 1), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_MISMATCH", manifest_store=manifest_store)

    sr_0 = float(np.mean(trial_matrix[:, 0])) / float(np.std(trial_matrix[:, 0], ddof=1))
    trial = SearchTrialRecord.create(
        trial_id="trial_0",
        strategy_id="STRAT_MISMATCH",
        hypothesis_id="HYP_01",
        feature_names=["mom"],
        parameters={"period": 10},
        in_sample_sharpe=Decimal(f"{sr_0:.6f}"),
        p_value=Decimal("0.001"),
        execution_manifest_id="MANIFEST_MISMATCH_HYP",
        in_sample_returns=list(trial_matrix[:, 0]),
    )
    ledger = SearchTrialLedger(
        ledger_id="L_MISMATCH",
        strategy_id="STRAT_MISMATCH",
        hypothesis_id="HYP_01",
        trials=(trial,),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    # Manifest with mismatched hypothesis_id
    manifest_store["MANIFEST_MISMATCH_HYP"] = _make_mock_manifest(
        manifest_id="MANIFEST_MISMATCH_HYP",
        hypothesis_id="HYP_DIFFERENT",
        strategy_config_hash=trial.config_sha256,
    )

    with pytest.raises(DataContractError, match="manifest hypothesis_id .* does not match trial hypothesis_id"):
        gate.evaluate_strategy(
            strategy_id="STRAT_MISMATCH",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["trial_0"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            perturbation_grid=grid,
        )


def test_sha256_strict_lowercase_64hex_pattern_rejections() -> None:
    """Verify that SearchTrialRecord, SearchTrialLedger, and ParameterPerturbationPoint strictly reject uppercase, non-hex, 63, and 65-char hashes."""
    from pydantic import ValidationError

    valid_hex = "a" * 64
    invalid_cases = [
        "A" * 64,  # Uppercase hex
        "z" * 64,  # Non-hex characters
        "a" * 63,  # 63 chars (short)
        "a" * 65,  # 65 chars (long)
        "1234567890abcdef" * 4 + "G",  # Non-hex char
    ]

    for bad_hash in invalid_cases:
        # 1. SearchTrialRecord in_sample_return_series_sha256
        with pytest.raises((ValidationError, DataContractError)):
            SearchTrialRecord(
                trial_id="t1",
                strategy_id="S1",
                hypothesis_id="H1",
                feature_names=["f"],
                parameters={},
                in_sample_sharpe=Decimal("1.0"),
                p_value=Decimal("0.05"),
                in_sample_return_series_sha256=bad_hash,
                config_sha256=valid_hex,
                execution_manifest_id="MAN_01",
            )

        # 2. SearchTrialRecord config_sha256
        with pytest.raises((ValidationError, DataContractError)):
            SearchTrialRecord(
                trial_id="t1",
                strategy_id="S1",
                hypothesis_id="H1",
                feature_names=["f"],
                parameters={},
                in_sample_sharpe=Decimal("1.0"),
                p_value=Decimal("0.05"),
                in_sample_return_series_sha256=valid_hex,
                config_sha256=bad_hash,
                execution_manifest_id="MAN_01",
            )

        # 3. ParameterPerturbationPoint output_artifact_hash
        with pytest.raises((ValidationError, DataContractError)):
            ParameterPerturbationPoint(
                parameter_value=Decimal("7.5"),
                run_id="run_1",
                manifest_id="MANIFEST_01",
                input_artifact_hash=valid_hex,
                output_artifact_hash=bad_hash,
                actual_sharpe=Decimal("1.5"),
            )


def test_statistical_validation_gate_rejects_fake_duck_typed_manifest() -> None:
    """Verify that Gate strictly rejects non-BacktestManifest objects in manifest_store (zero duck typing)."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 1), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_DUCK", manifest_store=manifest_store)

    sr_0 = float(np.mean(trial_matrix[:, 0])) / float(np.std(trial_matrix[:, 0], ddof=1))
    trial = SearchTrialRecord.create(
        trial_id="trial_0",
        strategy_id="STRAT_DUCK",
        hypothesis_id="HYP_01",
        feature_names=["mom"],
        parameters={"period": 10},
        in_sample_sharpe=Decimal(f"{sr_0:.6f}"),
        p_value=Decimal("0.001"),
        execution_manifest_id="MANIFEST_TRIAL_DUCK",
        in_sample_returns=list(trial_matrix[:, 0]),
    )
    ledger = SearchTrialLedger(
        ledger_id="L_DUCK",
        strategy_id="STRAT_DUCK",
        hypothesis_id="HYP_01",
        trials=(trial,),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    # Pass arbitrary non-BacktestManifest object in manifest_store
    manifest_store["MANIFEST_TRIAL_DUCK"] = object()

    with pytest.raises(DataContractError, match="must be an instance of BacktestManifest"):
        gate.evaluate_strategy(
            strategy_id="STRAT_DUCK",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["trial_0"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            perturbation_grid=grid,
        )


def test_search_trial_ledger_rejects_sealed_without_digest() -> None:
    """Verify that SearchTrialLedger strictly rejects is_sealed=True when ledger_digest is None."""
    valid_hex = "a" * 64
    record = SearchTrialRecord(
        trial_id="t1",
        strategy_id="S1",
        hypothesis_id="H1",
        feature_names=["f"],
        parameters={},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
        in_sample_return_series_sha256=valid_hex,
        config_sha256=valid_hex,
        execution_manifest_id="MAN_01",
    )

    with pytest.raises(DataContractError, match="marked is_sealed=True but ledger_digest is None"):
        SearchTrialLedger(
            ledger_id="LEDGER_NO_DIGEST",
            strategy_id="S1",
            hypothesis_id="H1",
            trials=(record,),
            is_sealed=True,
            ledger_digest=None,  # SEALED + NO DIGEST escape hatch strictly blocked!
        )


def test_search_trial_ledger_tuple_deep_immutability() -> None:
    """Verify that SearchTrialLedger.trials is an immutable Tuple preventing in-place mutations."""
    valid_hex = "a" * 64
    record = SearchTrialRecord(
        trial_id="t1",
        strategy_id="S1",
        hypothesis_id="H1",
        feature_names=["f"],
        parameters={},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
        in_sample_return_series_sha256=valid_hex,
        config_sha256=valid_hex,
        execution_manifest_id="MAN_01",
    )

    ledger = SearchTrialLedger(
        ledger_id="LEDGER_IMMUTABLE",
        strategy_id="S1",
        hypothesis_id="H1",
        trials=(record,),
    )
    assert isinstance(ledger.trials, tuple)
    assert not hasattr(ledger.trials, "append")


def test_statistical_inputs_reject_nan_and_inf() -> None:
    """Verify that Gate, DSR engine, and canonical hashers reject NaN and +/- Inf."""
    gate = StatisticalValidationGate()
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")
    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01", manifest_store=manifest_store)

    # 1. _compute_canonical_series_sha256 rejects NaN and Inf
    with pytest.raises(DataContractError, match="Non-finite .* encountered"):
        _compute_canonical_series_sha256([0.01, float("nan"), 0.02])

    with pytest.raises(DataContractError, match="Non-finite .* encountered"):
        _compute_canonical_series_sha256([0.01, float("inf"), 0.02])

    with pytest.raises(DataContractError, match="Non-finite .* encountered"):
        _compute_canonical_series_sha256([0.01, float("-inf"), 0.02])

    # 2. DeflatedSharpeEngine.calculate_higher_moments rejects NaN and Inf
    with pytest.raises(DataContractError, match="Non-finite .* encountered in return series"):
        DeflatedSharpeEngine.calculate_higher_moments([0.01, float("nan"), 0.02, 0.03])


    # 3. Gate rejects non-finite in_sample_returns
    with pytest.raises(DataContractError, match="in_sample_returns"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=[0.01, float("nan"), 0.02, 0.03],
            trial_matrix_column_trial_ids=["t1"],
            manifest_store=manifest_store,
        )

    # 4. Gate rejects non-finite out_of_sample_returns
    clean_is = [0.01, 0.02, 0.03, 0.04, 0.05]
    with pytest.raises(DataContractError, match="out_of_sample_returns"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=clean_is,
            trial_matrix_column_trial_ids=["t1"],
            manifest_store=manifest_store,
            out_of_sample_returns=[0.01, float("inf"), 0.02, 0.03],
        )

    # 5. Gate rejects non-finite trial_return_matrix
    mat_nan = np.array([[0.01], [np.nan], [0.03], [0.04]])
    h = "a" * 64
    trial = SearchTrialRecord(
        trial_id="t1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f"],
        parameters={},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
        in_sample_return_series_sha256=h,
        config_sha256=h,
        execution_manifest_id="MAN_01",
    )
    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=(trial,),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    with pytest.raises(DataContractError, match="trial_return_matrix contains non-finite values"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=[0.01, 0.02, 0.03, 0.04],
            trial_matrix_column_trial_ids=["t1"],
            manifest_store=manifest_store,
            out_of_sample_returns=[0.01, 0.02, 0.03, 0.04],
            trial_ledger=ledger,
            perturbation_grid=grid,
            trial_return_matrix=mat_nan,
        )


def test_sharpe_space_closed_enum_rejection() -> None:
    """Verify that SearchTrialLedger strictly rejects arbitrary string values for sharpe_space."""
    h = "a" * 64
    record = SearchTrialRecord(
        trial_id="t1",
        strategy_id="S1",
        hypothesis_id="H1",
        feature_names=["f"],
        parameters={},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
        in_sample_return_series_sha256=h,
        config_sha256=h,
        execution_manifest_id="MAN_01",
    )

    # Rejection of arbitrary strings (no silent fallback to PERIOD)
    with pytest.raises(DataContractError, match="Invalid sharpe_space 'BANANA'"):
        SearchTrialLedger(
            ledger_id="L1",
            strategy_id="S1",
            hypothesis_id="H1",
            trials=(record,),
            sharpe_space="BANANA",  # type: ignore[arg-type]
        )

    with pytest.raises(DataContractError, match="Invalid sharpe_space 'YEAR'"):
        SearchTrialLedger(
            ledger_id="L1",
            strategy_id="S1",
            hypothesis_id="H1",
            trials=(record,),
            sharpe_space="YEAR",  # type: ignore[arg-type]
        )

    # Valid enum specifications
    ledger_period = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="S1",
        hypothesis_id="H1",
        trials=(record,),
        sharpe_space=SharpeSpace.PERIOD,
    )
    assert ledger_period.sharpe_space == SharpeSpace.PERIOD

    ledger_annual = SearchTrialLedger(
        ledger_id="L2",
        strategy_id="S1",
        hypothesis_id="H1",
        trials=(record,),
        sharpe_space=SharpeSpace.ANNUAL,
    )
    assert ledger_annual.sharpe_space == SharpeSpace.ANNUAL


def test_search_trial_record_feature_names_tuple_immutability() -> None:
    """Verify that SearchTrialRecord feature_names is stored as an immutable tuple."""
    h = "a" * 64
    record = SearchTrialRecord(
        trial_id="t1",
        strategy_id="S1",
        hypothesis_id="H1",
        feature_names=["mom", "vol", "alpha"],  # Passed as list
        parameters={"lookback": 20},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
        in_sample_return_series_sha256=h,
        config_sha256=h,
        execution_manifest_id="MAN_01",
    )
    assert isinstance(record.feature_names, tuple)
    assert record.feature_names == ("alpha", "mom", "vol")  # Sorted canonical order


def test_statistical_validation_gate_rejects_divergent_ledger_sharpe() -> None:
    """Verify that Gate strictly rejects when registered trial in_sample_sharpe deviates from actual return series Sharpe."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 200))
    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_01")

    trial_matrix = np.zeros((500, 1), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)

    manifest_store: Dict[str, Any] = {}
    grid = _make_valid_perturbation_grid(strat_id="STRAT_DIVERGE", manifest_store=manifest_store)

    # Registered Sharpe = 5.0, but actual return series Sharpe ~ 0.38
    trial = SearchTrialRecord.create(
        trial_id="trial_0",
        strategy_id="STRAT_DIVERGE",
        hypothesis_id="HYP_01",
        feature_names=["mom"],
        parameters={"period": 10},
        in_sample_sharpe=Decimal("5.000000"),  # Fabricated divergent Sharpe!
        p_value=Decimal("0.001"),
        execution_manifest_id="MANIFEST_TRIAL_DIVERGE",
        in_sample_returns=list(trial_matrix[:, 0]),
    )
    ledger = SearchTrialLedger(
        ledger_id="L_DIVERGE",
        strategy_id="STRAT_DIVERGE",
        hypothesis_id="HYP_01",
        trials=(trial,),
        sharpe_space=SharpeSpace.PERIOD,
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z")

    manifest_store["MANIFEST_TRIAL_DIVERGE"] = _make_mock_manifest(
        manifest_id="MANIFEST_TRIAL_DIVERGE",
        hypothesis_id="HYP_01",
        strategy_config_hash=trial.config_sha256,
        sharpe=Decimal("5.000000"),
    )

    with pytest.raises(DataContractError, match="exceeds methodological tolerance bound"):
        gate.evaluate_strategy(
            strategy_id="STRAT_DIVERGE",
            hypothesis_id="HYP_01",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            trial_matrix_column_trial_ids=["trial_0"],
            manifest_store=manifest_store,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            perturbation_grid=grid,
        )


def test_canonical_config_serializer_type_preservation_and_differentiation() -> None:
    """Verify that CanonicalConfigSerializer strictly differentiates primitive types and rejects non-finite values."""
    # 1. bool vs int differentiation: True != 1
    h_bool = CanonicalConfigSerializer.compute_sha256({"flag": True})
    h_int = CanonicalConfigSerializer.compute_sha256({"flag": 1})
    assert h_bool != h_int

    # 2. Decimal vs float differentiation: Decimal("1.0") != 1.0
    h_dec = CanonicalConfigSerializer.compute_sha256({"val": Decimal("1.0")})
    h_float = CanonicalConfigSerializer.compute_sha256({"val": 1.0})
    assert h_dec != h_float

    # 3. str vs bytes differentiation: "abc" != b"abc"
    h_str = CanonicalConfigSerializer.compute_sha256({"data": "abc"})
    h_bytes = CanonicalConfigSerializer.compute_sha256({"data": b"abc"})
    assert h_str != h_bytes

    # 4. Non-finite float rejection
    with pytest.raises(DataContractError, match="Non-finite float value"):
        CanonicalConfigSerializer.to_canonical_json({"val": float("nan")})

    with pytest.raises(DataContractError, match="Non-finite float value"):
        CanonicalConfigSerializer.to_canonical_json({"val": float("inf")})

    # 5. Non-finite Decimal rejection
    with pytest.raises(DataContractError, match="Non-finite Decimal value"):
        CanonicalConfigSerializer.to_canonical_json({"val": Decimal("NaN")})


def test_search_trial_record_deep_immutable_parameters() -> None:
    """Verify that SearchTrialRecord recursively freezes parameters and prevents runtime mutation."""
    h = "a" * 64
    raw_params = {
        "lookback": 20,
        "nested": {"threshold": 1.5, "tags": ["a", "b"]},
    }
    record = SearchTrialRecord.create(
        trial_id="t_freeze",
        strategy_id="S1",
        hypothesis_id="H1",
        feature_names=["f1"],
        parameters=raw_params,
        in_sample_sharpe=Decimal("1.2"),
        p_value=Decimal("0.02"),
        execution_manifest_id="MAN_01",
        in_sample_returns=[0.01, 0.02, 0.03, 0.04],
    )

    # 1. Top-level parameter mutation raises TypeError
    with pytest.raises(TypeError):
        record.parameters["lookback"] = 999  # type: ignore[index]

    with pytest.raises(TypeError):
        record.parameters["new_key"] = "hacked"  # type: ignore[index]

    # 2. Nested dictionary mutation raises TypeError
    with pytest.raises(TypeError):
        nested_dict = record.parameters["nested"]
        nested_dict["threshold"] = 99.9


    # 3. Nested list converted to tuple -> raises AttributeError on append
    nested_tags = record.parameters["nested"]["tags"]
    assert isinstance(nested_tags, tuple)
    assert not hasattr(nested_tags, "append")


def test_decimal_is_finite_guards_on_extreme_values() -> None:
    """Verify that Decimal is_finite guards properly validate extreme Decimal values and reject float64 overflow."""
    # 100-digit decimal is within float64 range (< 1.79e308)
    large_dec = Decimal("1" * 100 + ".5")
    assert large_dec.is_finite() is True

    from acash.validation.gate import _verify_finite_numeric
    checked = _verify_finite_numeric(large_dec, context="test_large")
    assert checked == large_dec

    # 400-digit decimal exceeds float64 range (> 1.79e308) -> raises DataContractError
    overflow_dec = Decimal("1" * 400 + ".5")
    assert overflow_dec.is_finite() is True  # Finite in Decimal
    with pytest.raises(DataContractError, match="exceeds float64 representable magnitude boundary"):
        _verify_finite_numeric(overflow_dec, context="overflow_test")

    with pytest.raises(DataContractError, match="exceeds float64 representable magnitude boundary"):
        DeflatedSharpeEngine.calculate_higher_moments([0.01, 0.02, 0.03, overflow_dec])

    # Non-finite Decimals fail closed
    with pytest.raises(DataContractError, match="Non-finite Decimal"):
        _verify_finite_numeric(Decimal("NaN"), context="nan_test")

    with pytest.raises(DataContractError, match="Non-finite Decimal"):
        _verify_finite_numeric(Decimal("Infinity"), context="inf_test")

    with pytest.raises(DataContractError, match="Non-finite Decimal"):
        _verify_finite_numeric(Decimal("-Infinity"), context="neg_inf_test")


def test_governance_sharpe_consistency_tolerance_binding() -> None:
    """Verify that sharpe_consistency_tolerance is configurable and bound into the decision digest."""
    # Custom config with tighter tolerance 1e-4
    config_tight = ValidationConfig(sharpe_consistency_tolerance=Decimal("0.0001"))
    config_loose = ValidationConfig(sharpe_consistency_tolerance=Decimal("0.01"))

    assert config_tight.sharpe_consistency_tolerance == Decimal("0.0001")
    assert config_loose.sharpe_consistency_tolerance == Decimal("0.01")

    # Verify decision digest differs when sharpe_consistency_tolerance changes
    gate_tight = StatisticalValidationGate(config=config_tight)
    gate_loose = StatisticalValidationGate(config=config_loose)

    spec = _make_valid_hypothesis_spec(hypothesis_id="HYP_GOV")
    report_tight = gate_tight.evaluate_strategy(
        strategy_id="STRAT_GOV",
        hypothesis_id="HYP_GOV",
        hypothesis_spec=spec,
        in_sample_returns=[0.01, 0.02, 0.03, 0.04],
        trial_matrix_column_trial_ids=["t1"],
        manifest_store={},
    )
    report_loose = gate_loose.evaluate_strategy(
        strategy_id="STRAT_GOV",
        hypothesis_id="HYP_GOV",
        hypothesis_spec=spec,
        in_sample_returns=[0.01, 0.02, 0.03, 0.04],
        trial_matrix_column_trial_ids=["t1"],
        manifest_store={},
    )
    # Different governance tolerance -> different decision digest & validation ID
    assert report_tight.decision_digest != report_loose.decision_digest
    assert report_tight.validation_id != report_loose.validation_id




