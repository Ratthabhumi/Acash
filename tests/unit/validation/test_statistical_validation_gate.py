"""Unit tests for the Statistical Validation Gate master orchestrator."""

from decimal import Decimal
import hashlib
import json
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.gate import StatisticalValidationGate
from acash.validation.schema import (
    ParameterPerturbationGrid,
    ParameterPerturbationPoint,
    SearchTrialLedger,
    SearchTrialRecord,
    SelectionCorrectionMode,
    ValidationConfig,
    ValidationGateVerdict,
)


def _make_valid_perturbation_grid(
    base_val: Decimal = Decimal("10.0"),
    sr: Decimal = Decimal("1.5"),
    strat_id: str = "STRAT_01",
) -> ParameterPerturbationGrid:
    """Helper to construct a valid 3-point perturbation grid with distinct execution runs and manifests."""
    base_hash = hashlib.sha256(f"{strat_id}:test_grid:{base_val}".encode("utf-8")).hexdigest()
    points = [
        ParameterPerturbationPoint(
            parameter_value=base_val * Decimal("0.75"),
            run_id=f"run_{strat_id}_left_p75",
            manifest_id=f"MANIFEST_{strat_id}_LEFT",
            input_artifact_hash=hashlib.sha256(f"{base_hash}:left:in".encode("utf-8")).hexdigest(),
            output_artifact_hash=hashlib.sha256(f"{base_hash}:left:out".encode("utf-8")).hexdigest(),
            actual_sharpe=sr,
        ),
        ParameterPerturbationPoint(
            parameter_value=base_val,
            run_id=f"run_{strat_id}_base_100",
            manifest_id=f"MANIFEST_{strat_id}_BASE",
            input_artifact_hash=hashlib.sha256(f"{base_hash}:base:in".encode("utf-8")).hexdigest(),
            output_artifact_hash=hashlib.sha256(f"{base_hash}:base:out".encode("utf-8")).hexdigest(),
            actual_sharpe=sr,
        ),
        ParameterPerturbationPoint(
            parameter_value=base_val * Decimal("1.25"),
            run_id=f"run_{strat_id}_right_p125",
            manifest_id=f"MANIFEST_{strat_id}_RIGHT",
            input_artifact_hash=hashlib.sha256(f"{base_hash}:right:in".encode("utf-8")).hexdigest(),
            output_artifact_hash=hashlib.sha256(f"{base_hash}:right:out".encode("utf-8")).hexdigest(),
            actual_sharpe=sr,
        ),
    ]
    return ParameterPerturbationGrid(
        base_parameter_name="lookback",
        base_parameter_value=base_val,
        points=points,
    )


def test_statistical_validation_gate_pass_tradeable_alpha() -> None:
    """Verify that a genuine robust strategy passing all gates receives PASS_TRADEABLE_ALPHA."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    # Strong persistent positive returns
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_MOM_001",
            hypothesis_id="HYP_TSMOM_001",
            feature_names=["mom"],
            parameters={"period": 10 + i},
            in_sample_sharpe=Decimal(f"{1.2 + i * 0.05:.4f}"),
            p_value=Decimal("0.001"),
        )
        for i in range(5)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_MOM_001",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_MOM_001")
    trial_matrix = np.zeros((1000, 5), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    for m in range(1, 5):
        trial_matrix[:, m] = np.random.normal(0.0020 - m * 0.0005, 0.0040, 1000)

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        perturbation_grid=grid,
    )




    assert report.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA
    assert report.is_tradeable_alpha is True
    assert report.dsr_result is not None
    assert report.dsr_result.effective_trials_k == 5
    assert report.dsr_result.selection_correction_mode == SelectionCorrectionMode.MULTIPLE_TRIAL
    assert report.dsr_result.sr0_estimator == "EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1"
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

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=None,
    )

    assert report.verdict == ValidationGateVerdict.REJECT_MISSING_TRIAL_LEDGER
    assert report.is_tradeable_alpha is False
    # Strict zero-evaluation & zero-synthetic evidence invariant:
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

    trial = SearchTrialRecord(
        trial_id="trial_1",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        feature_names=["mom"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        trials=[trial],
    )

    # 1. None OOS returns
    report_none = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
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
        in_sample_returns=is_returns,
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

    trial = SearchTrialRecord(
        trial_id="trial_1",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        feature_names=["mom"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_001",
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        trials=[trial],
    )

    report = gate.evaluate_strategy(
        strategy_id="STRAT_MOM_001",
        hypothesis_id="HYP_TSMOM_001",
        in_sample_returns=is_returns,
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
    record_1 = SearchTrialRecord(
        trial_id="duplicate_id",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.0"),
        p_value=Decimal("0.05"),
    )
    record_2 = SearchTrialRecord(
        trial_id="duplicate_id",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f2"],
        parameters={},
        in_sample_sharpe=Decimal("1.2"),
        p_value=Decimal("0.03"),
    )

    with pytest.raises(DataContractError, match="duplicate trial_ids"):
        SearchTrialLedger(
            ledger_id="LEDGER_01",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            trials=[record_1, record_2],
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

    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.01"),
        )
        for i in range(2)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_01",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01")
    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    report_1 = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        perturbation_grid=grid,
        fixed_created_timestamp_utc="2026-08-28T10:00:00Z",
    )

    report_2 = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
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

    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.01"),
        )
        for i in range(2)
    ]
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_01",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01")
    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    report = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
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
    from acash.backtest.schema import (
        BacktestExecutionSummary,
        BacktestManifest,
        FeeModelConfig,
        RealityGapSummary,
        SimulationLatencyConfig,
        SlippageModelConfig,
    )

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

    # 6. Standalone strategy_config_hash alone strictly rejected (must be composite SHA256(hyp:strat))
    point_standalone_strat = ParameterPerturbationPoint(
        parameter_value=Decimal("7.5"),
        run_id="run_p75",
        manifest_id="MANIFEST_MOM_P75_TEST",
        input_artifact_hash=strat_hash,
        output_artifact_hash=manifest_output_hash,
        actual_sharpe=Decimal("1.650000000000000000"),
    )
    with pytest.raises(DataContractError, match="Input artifact hash mismatch"):
        point_standalone_strat.validate_manifest_binding(manifest)

    # 7. Standalone hypothesis_spec_sha256 alone strictly rejected
    point_standalone_hyp = ParameterPerturbationPoint(
        parameter_value=Decimal("7.5"),
        run_id="run_p75",
        manifest_id="MANIFEST_MOM_P75_TEST",
        input_artifact_hash=hyp_hash,
        output_artifact_hash=manifest_output_hash,
        actual_sharpe=Decimal("1.650000000000000000"),
    )
    with pytest.raises(DataContractError, match="Input artifact hash mismatch"):
        point_standalone_hyp.validate_manifest_binding(manifest)


def test_statistical_validation_gate_fail_closed_precedes_sample_size_check() -> None:
    """Verify that missing governance prerequisites fail closed through verdict before in-sample size validation."""
    gate = StatisticalValidationGate()

    # in_sample has only 2 bars (< 4 minimum)
    short_is = [0.01, 0.02]

    # 1. Missing ledger with short IS -> REJECT_MISSING_TRIAL_LEDGER (not DataContractError)
    rep_ledger = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=short_is,
        out_of_sample_returns=[0.01, 0.02, 0.03, 0.04],
        trial_ledger=None,
    )
    assert rep_ledger.verdict == ValidationGateVerdict.REJECT_MISSING_TRIAL_LEDGER

    # 2. Missing OOS with short IS -> REJECT_MISSING_OOS_DATA
    trial = SearchTrialRecord(
        trial_id="t1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.01"),
    )
    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=[trial],
    )

    rep_oos = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=short_is,
        out_of_sample_returns=None,
        trial_ledger=ledger,
    )
    assert rep_oos.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA

    # 3. Missing Perturbation Grid with short IS -> REJECT_MISSING_PERTURBATION_GRID
    rep_grid = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=short_is,
        out_of_sample_returns=[0.01, 0.02, 0.03, 0.04],
        trial_ledger=ledger,
        perturbation_grid=None,
    )
    assert rep_grid.verdict == ValidationGateVerdict.REJECT_MISSING_PERTURBATION_GRID


def test_statistical_validation_gate_verifies_manifest_store_repository() -> None:
    """Verify that StatisticalValidationGate strictly verifies all 3 perturbation points against manifest_store."""
    from acash.backtest.schema import (
        BacktestExecutionSummary,
        BacktestManifest,
        RealityGapSummary,
    )

    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 500))

    trial = SearchTrialRecord(
        trial_id="trial_1",
        strategy_id="STRAT_STORE_01",
        hypothesis_id="HYP_01",
        feature_names=["f1"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.001"),
    )
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_01",
        strategy_id="STRAT_STORE_01",
        hypothesis_id="HYP_01",
        trials=[
            SearchTrialRecord(
                trial_id=f"trial_{i}",
                strategy_id="STRAT_STORE_01",
                hypothesis_id="HYP_01",
                feature_names=["f1"],
                parameters={"p": i},
                in_sample_sharpe=Decimal("1.5"),
                p_value=Decimal("0.001"),
            )
            for i in range(2)
        ],
    )

    hyp_hash = "1" * 64
    eng_hash = "2" * 64
    strat_hash = "3" * 64
    pyp_hash = "4" * 64
    git_hash = "5" * 40
    data_hash = "6" * 64
    expected_in = hashlib.sha256(f"{hyp_hash}:{strat_hash}".encode("utf-8")).hexdigest()

    manifest_store = {}
    points = []
    base_val = Decimal("10.0")
    multipliers = [("left", Decimal("0.75")), ("base", Decimal("1.0")), ("right", Decimal("1.25"))]

    for label, mult in multipliers:
        p_val = base_val * mult
        man_id = f"MANIFEST_RUN_{label.upper()}"
        sr = Decimal("1.500000000000000000")

        exec_summary = BacktestExecutionSummary(
            total_orders=10,
            total_fills=10,
            total_volume_traded=Decimal("10000.0"),
            total_fees_paid=Decimal("10.0"),
            realized_pnl=Decimal("1000.0"),
            unrealized_pnl=Decimal("0.0"),
            ending_equity=Decimal("101000.0"),
            net_return_pct=Decimal("1.0"),
            sharpe_ratio=sr,
            max_drawdown_pct=Decimal("0.5"),
            win_rate_pct=Decimal("60.0"),
        )
        reality_gap = RealityGapSummary(
            phase4_analytical_edge_bps=Decimal("10.0"),
            phase5_simulated_realized_bps=Decimal("8.0"),
            reality_gap_bps=Decimal("2.0"),
        )
        manifest = BacktestManifest(
            manifest_id=man_id,
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
            wall_clock_duration_ms=1000,
        )
        manifest_store[man_id] = manifest

        pt = ParameterPerturbationPoint(
            parameter_value=p_val,
            run_id=f"run_{label}",
            manifest_id=man_id,
            input_artifact_hash=expected_in,
            output_artifact_hash=manifest.compute_sha256(),
            actual_sharpe=sr,
        )
        points.append(pt)

    grid = ParameterPerturbationGrid(
        base_parameter_name="lookback",
        base_parameter_value=base_val,
        points=points,
    )

    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    # 1. Successful verification against manifest_store
    report = gate.evaluate_strategy(
        strategy_id="STRAT_STORE_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
        perturbation_grid=grid,
        manifest_store=manifest_store,
    )
    assert report.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA

    # 2. Rejection when a manifest is missing from manifest_store
    incomplete_store = {k: v for k, v in manifest_store.items() if k != "MANIFEST_RUN_RIGHT"}
    with pytest.raises(DataContractError, match="missing from manifest_store repository"):
        gate.evaluate_strategy(
            strategy_id="STRAT_STORE_01",
            hypothesis_id="HYP_01",
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

    trial = SearchTrialRecord(
        trial_id="t1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        feature_names=["f"],
        parameters={},
        in_sample_sharpe=Decimal("1.5"),
        p_value=Decimal("0.001"),
    )
    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=[trial],
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01")

    # Omitting CPCV evidence
    rep = gate.evaluate_strategy(
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
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

    # Insignificant trials: p-value = 0.50
    trials = [
        SearchTrialRecord(
            trial_id=f"t_{i}",
            strategy_id="STRAT_FWER",
            hypothesis_id="HYP_01",
            feature_names=["f"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.50"),  # High p-value -> FWER fails!
        )
        for i in range(3)
    ]
    ledger = SearchTrialLedger(
        ledger_id="L_FWER",
        strategy_id="STRAT_FWER",
        hypothesis_id="HYP_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_FWER")
    trial_matrix = np.zeros((500, 3), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0010, 0.0040, 500)
    trial_matrix[:, 2] = np.random.normal(0.0005, 0.0040, 500)

    rep = gate.evaluate_strategy(
        strategy_id="STRAT_FWER",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
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

    trials = [
        SearchTrialRecord(
            trial_id=f"t_{i}",
            strategy_id="STRAT_HC",
            hypothesis_id="HYP_01",
            feature_names=["f"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.001"),
        )
        for i in range(2)
    ]
    ledger = SearchTrialLedger(
        ledger_id="L_HC",
        strategy_id="STRAT_HC",
        hypothesis_id="HYP_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_HC")
    trial_matrix = np.zeros((500, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 500)

    rep = gate.evaluate_strategy(
        strategy_id="STRAT_HC",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
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

    trials = [
        SearchTrialRecord(
            trial_id=f"t_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.001"),
        )
        for i in range(3)  # K = 3
    ]
    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01")
    # M = 2 != K = 3
    mismatched_matrix = np.zeros((500, 2), dtype=np.float64)
    mismatched_matrix[:, 0] = np.array([float(x) for x in is_returns])

    with pytest.raises(DataContractError, match="candidate count M .* does not match SearchTrialLedger K"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=mismatched_matrix,
            trial_matrix_column_trial_ids=["t_0", "t_1", "t_2"],
            perturbation_grid=grid,
        )


def test_statistical_validation_gate_rejects_is_returns_matrix_column_0_mismatch() -> None:
    """Verify that Gate strictly rejects when trial_return_matrix column 0 != in_sample_returns."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0015, 0.0040, 500))
    oos_returns = list(np.random.normal(0.0012, 0.0040, 200))

    trials = [
        SearchTrialRecord(
            trial_id=f"t_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.001"),
        )
        for i in range(2)
    ]
    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01")
    # Column 0 has different random returns
    divergent_matrix = np.random.normal(0.0050, 0.0040, (500, 2))

    with pytest.raises(DataContractError, match="column 0 .* does not match in_sample_returns"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=divergent_matrix,
            trial_matrix_column_trial_ids=[t.trial_id for t in ledger.trials],
            perturbation_grid=grid,
        )



def test_statistical_validation_gate_binds_real_label_horizon_and_embargo() -> None:
    """Verify that Gate strictly evaluates CPCV with custom research label_horizon H and embargo_bars E."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 500))

    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_HORIZON",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.001"),
        )
        for i in range(2)
    ]
    ledger = SearchTrialLedger(
        ledger_id="L_HORIZON",
        strategy_id="STRAT_HORIZON",
        hypothesis_id="HYP_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_HORIZON")
    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    # 1. Standard evaluate with H=20, E=10
    rep_h20 = gate.evaluate_strategy(
        strategy_id="STRAT_HORIZON",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=["trial_0", "trial_1"],
        perturbation_grid=grid,
        label_horizon=20,
        embargo_bars=10,
        fixed_created_timestamp_utc="2026-08-28T10:00:00Z",
    )
    assert rep_h20.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA

    # 2. Evaluate with H=1, E=5
    rep_h1 = gate.evaluate_strategy(
        strategy_id="STRAT_HORIZON",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=["trial_0", "trial_1"],
        perturbation_grid=grid,
        label_horizon=1,
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

    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            feature_names=["f"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.001"),
        )
        for i in range(2)
    ]
    ledger = SearchTrialLedger(
        ledger_id="L1",
        strategy_id="STRAT_01",
        hypothesis_id="HYP_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_01")
    trial_matrix = np.zeros((500, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns])

    # Passing inverted column trial IDs ["trial_1", "trial_0"]
    with pytest.raises(DataContractError, match="does not match ordered ledger trial_ids"):
        gate.evaluate_strategy(
            strategy_id="STRAT_01",
            hypothesis_id="HYP_01",
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            trial_matrix_column_trial_ids=["trial_1", "trial_0"],
            perturbation_grid=grid,
        )


def test_overfitting_engine_is_tie_symmetric_policy() -> None:
    """Verify that OverfittingEngine.calculate_pbo evaluates tied in-sample winners symmetrically without argmax bias."""
    from acash.validation.overfitting import OverfittingEngine

    # 1 split, 3 candidate models where model 0 and model 1 have identical IS Sharpe
    is_mat = np.array([[2.0, 2.0, 1.0]], dtype=np.float64)
    # Model 0 is top OOS (rank 3), model 1 is bottom OOS (rank 1), model 2 is mid (rank 2)
    # Ranks for M=3:
    # Model 0 midrank = 3.0 -> omega = 3.0 / 4.0 = 0.75
    # Model 1 midrank = 1.0 -> omega = 1.0 / 4.0 = 0.25
    # Symmetric average omega for tied {0, 1} = (0.75 + 0.25)/2 = 0.50 -> lambda = ln(0.5/0.5) = 0.0 -> PBO = 0.0 (not overfit)
    oos_mat = np.array([[3.0, 1.0, 2.0]], dtype=np.float64)

    pbo, logit_mean, logit_std = OverfittingEngine.calculate_pbo(is_mat, oos_mat)
    assert pbo == 0.0
    assert abs(logit_mean) < 1e-6


def test_statistical_validation_gate_binds_hypothesis_specification_horizon() -> None:
    """Verify that Gate strictly validates label_horizon against pre-registered HypothesisSpecification.primary_horizon."""
    from acash.research.schema import ExpectedDirection, HypothesisSpecification, InvalidationCriteria

    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 500))

    trials = [
        SearchTrialRecord(
            trial_id=f"trial_{i}",
            strategy_id="STRAT_SPEC",
            hypothesis_id="HYP_SPEC_01",
            feature_names=["f1"],
            parameters={"p": i},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.001"),
        )
        for i in range(2)
    ]
    ledger = SearchTrialLedger(
        ledger_id="L_SPEC",
        strategy_id="STRAT_SPEC",
        hypothesis_id="HYP_SPEC_01",
        trials=trials,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_SPEC")
    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    spec = HypothesisSpecification(
        hypothesis_id="HYP_SPEC_01",
        hypothesis_version="v1.0.0",
        economic_rationale="Momentum autocorrelation in microstructure footprint",
        target_symbol="BTCUSDT",
        feature_dependencies=["order_flow_imbalance"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[5, 10, 20],
        primary_horizon=20,  # Formal registered horizon is 20 bars
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-08-28T00:00:00Z",
        author="ResearchTeam",
    )

    # 1. Successful validation when label_horizon strictly matches spec.primary_horizon (20)
    rep = gate.evaluate_strategy(
        strategy_id="STRAT_SPEC",
        hypothesis_id="HYP_SPEC_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=["trial_0", "trial_1"],
        perturbation_grid=grid,
        hypothesis_spec=spec,
        label_horizon=20,
    )
    assert rep.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA

    # 2. Strict rejection when caller attempts to supply mismatched label_horizon (e.g. 1 != 20)
    with pytest.raises(DataContractError, match="does not match hypothesis_spec.primary_horizon"):
        gate.evaluate_strategy(
            strategy_id="STRAT_SPEC",
            hypothesis_id="HYP_SPEC_01",
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            trial_matrix_column_trial_ids=["trial_0", "trial_1"],
            perturbation_grid=grid,
            hypothesis_spec=spec,
            label_horizon=1,  # Attempting unauthorized horizon shortcut
        )


def test_statistical_validation_gate_verifies_candidate_return_series_sha256() -> None:
    """Verify that Gate strictly checks cryptographic return series SHA-256 for all ledger trials."""
    gate = StatisticalValidationGate()

    np.random.seed(42)
    is_returns = list(np.random.normal(0.0020, 0.0040, 1000))
    oos_returns = list(np.random.normal(0.0015, 0.0040, 500))

    trial_matrix = np.zeros((1000, 2), dtype=np.float64)
    trial_matrix[:, 0] = np.array([float(x) for x in is_returns], dtype=np.float64)
    trial_matrix[:, 1] = np.random.normal(0.0005, 0.0040, 1000)

    # Compute exact hashes for the two columns
    from acash.validation.gate import _compute_canonical_series_sha256
    hash_col0 = _compute_canonical_series_sha256(trial_matrix[:, 0])
    hash_col1 = _compute_canonical_series_sha256(trial_matrix[:, 1])

    trials_valid = [
        SearchTrialRecord(
            trial_id="trial_0",
            strategy_id="STRAT_SHA",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"p": 0},
            in_sample_sharpe=Decimal("1.5"),
            p_value=Decimal("0.001"),
            in_sample_return_series_sha256=hash_col0,
        ),
        SearchTrialRecord(
            trial_id="trial_1",
            strategy_id="STRAT_SHA",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"p": 1},
            in_sample_sharpe=Decimal("0.5"),
            p_value=Decimal("0.050"),
            in_sample_return_series_sha256=hash_col1,
        ),
    ]
    ledger_valid = SearchTrialLedger(
        ledger_id="L_SHA",
        strategy_id="STRAT_SHA",
        hypothesis_id="HYP_01",
        trials=trials_valid,
    )
    grid = _make_valid_perturbation_grid(strat_id="STRAT_SHA")

    # 1. Successful evaluation when ledger registered hashes match matrix columns exactly
    rep = gate.evaluate_strategy(
        strategy_id="STRAT_SHA",
        hypothesis_id="HYP_01",
        in_sample_returns=is_returns,
        out_of_sample_returns=oos_returns,
        trial_ledger=ledger_valid,
        trial_return_matrix=trial_matrix,
        trial_matrix_column_trial_ids=["trial_0", "trial_1"],
        perturbation_grid=grid,
    )
    assert rep.verdict == ValidationGateVerdict.PASS_TRADEABLE_ALPHA

    # 2. Rejection when a trial's return series hash is tampered/mismatched
    trials_tampered = [
        trials_valid[0],
        SearchTrialRecord(
            trial_id="trial_1",
            strategy_id="STRAT_SHA",
            hypothesis_id="HYP_01",
            feature_names=["f1"],
            parameters={"p": 1},
            in_sample_sharpe=Decimal("0.5"),
            p_value=Decimal("0.050"),
            in_sample_return_series_sha256="deadbeef" * 8,  # Tampered hash
        ),
    ]
    ledger_tampered = SearchTrialLedger(
        ledger_id="L_SHA",
        strategy_id="STRAT_SHA",
        hypothesis_id="HYP_01",
        trials=trials_tampered,
    )
    with pytest.raises(DataContractError, match="in_sample_return_series_sha256 .* does not match"):
        gate.evaluate_strategy(
            strategy_id="STRAT_SHA",
            hypothesis_id="HYP_01",
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger_tampered,
            trial_return_matrix=trial_matrix,
            trial_matrix_column_trial_ids=["trial_0", "trial_1"],
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







