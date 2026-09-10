"""Adversarial tests for the Evidence Bridge Phase 6 evidence assembly (Phase 14, D8-B).

Attack the ratified D8-B scope: deterministic, cryptographically-bound assembly of Phase 5
outputs into Phase 6 evidence inputs. Every lineage / identity / hash / consistency invariant
must fail closed. Assembly must NOT seal a ledger, invoke a gate, or run OOS/CPCV.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pyarrow as pa
import pytest

from acash.backtest.adapter import CanonicalDataAdapter
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.equity_returns import derive_canonical_equity_returns
from acash.backtest.schema import (
    BacktestEngineConfig,
    BacktestExecutionSummary,
    BacktestManifest,
    CANONICAL_EQUITY_CURVE_SCHEMA,
    RealityGapSummary,
)
from acash.backtest.strategies.imbalance_actor import MicrostructureImbalanceActor
from acash.core.domain.exceptions import DataContractError
from acash.research.evidence_bridge import (
    BacktestRunEvidence,
    PhaseSixEvidenceAssembly,
    assemble_phase_six_evidence,
)
from acash.validation.deflated_sharpe import calculate_annualized_sharpe
from acash.validation.gate import _compute_canonical_series_sha256

_PPY = Decimal("252.0")
_TS_BASE_NS = 1_768_833_000_000_000_000
_T60_NS = 60_000_000_000
_MINUTE = timedelta(minutes=1)


def _make_manifest(
    hypothesis_id: str, manifest_id: str, sharpe: Decimal | None, engine_config_hash: str | None = None
) -> BacktestManifest:
    h = engine_config_hash or ("a" * 64)
    summary = BacktestExecutionSummary(
        total_orders=1,
        total_fills=1,
        total_volume_traded=Decimal("1.0"),
        total_fees_paid=Decimal("0.0"),
        realized_pnl=Decimal("0.0"),
        unrealized_pnl=Decimal("100.0"),
        ending_equity=Decimal("100100.0"),
        net_return_pct=Decimal("0.1"),
        sharpe_ratio=sharpe,
        max_drawdown_pct=Decimal("0.0"),
        win_rate_pct=Decimal("100.0"),
    )
    return BacktestManifest(
        manifest_id=manifest_id,
        hypothesis_id=hypothesis_id,
        hypothesis_spec_sha256="b" * 64,
        canonical_data_hashes=["c" * 64],
        engine_config_hash=h,
        strategy_config_hash="d" * 64,
        prng_seed=42,
        pyproject_toml_sha256="e" * 64,
        git_commit_hash="a" * 40,
        execution_summary=summary,
        reality_gap=RealityGapSummary(
            phase4_analytical_edge_bps=Decimal("0.0"),
            phase5_simulated_realized_bps=Decimal("0.0"),
            reality_gap_bps=Decimal("0.0"),
        ),
        computed_at_utc="2026-01-01T00:00:00+00:00",
        wall_clock_duration_ms=0,
    )


def _equity_table(equities: list[Decimal]) -> pa.Table:
    n = len(equities)
    return pa.Table.from_pydict(
        {
            "timestamp_utc": [_TS_BASE_NS + (i * _T60_NS) for i in range(n)],
            "cash_balance": [Decimal("0.0")] * n,
            "realized_pnl": [Decimal("0.0")] * n,
            "unrealized_pnl": [Decimal("0.0")] * n,
            "total_equity": equities,
            "margin_utilized": [Decimal("0.0")] * n,
            "accounting_residual": [Decimal("0.0")] * n,
        },
        schema=CANONICAL_EQUITY_CURVE_SCHEMA,
    )


def _synthetic_run(
    trial_id: str,
    hypothesis_id: str,
    equities: list[Decimal],
    manifest_id: str,
) -> BacktestRunEvidence:
    table = _equity_table(equities)
    returns = derive_canonical_equity_returns(table)
    sharpe = calculate_annualized_sharpe(returns, _PPY)
    manifest = _make_manifest(hypothesis_id, manifest_id, sharpe)
    return BacktestRunEvidence(
        trial_id=trial_id,
        strategy_id=f"STRAT_{trial_id}",
        hypothesis_id=hypothesis_id,
        feature_names=("feature_1", "feature_2"),
        parameters={"param_alpha": Decimal("0.5")},
        manifest=manifest,
        fills_table=pa.Table.from_pydict({}),  # placebo table; identity checks focus on manifest/equity
        equity_table=table,
    )


class TestAssemblyHappyPath:
    def test_materializes_cryptographically_bound_records(self) -> None:
        run = _synthetic_run(
            trial_id="TR-1",
            hypothesis_id="HYP_BRIDGE_0001",
            equities=[Decimal("100000"), Decimal("101000"), Decimal("99000"), Decimal("102000")],
            manifest_id="M" * 32,
        )
        assembly = assemble_phase_six_evidence([run], _PPY)

        assert isinstance(assembly, PhaseSixEvidenceAssembly)
        assert assembly.trial_matrix_column_trial_ids == ("TR-1",)
        assert assembly.primary_in_sample_returns == tuple(derive_canonical_equity_returns(run.equity_table))
        assert assembly.trial_return_matrix.shape[1] == 1
        assert assembly.trial_return_matrix.shape[0] == len(assembly.primary_in_sample_returns)
        assert assembly.trial_return_matrix[:, 0].tolist() == [float(r) for r in assembly.primary_in_sample_returns]

        records = assembly.trial_records
        assert len(records) == 1
        record = records[0]
        assert record.trial_id == "TR-1"
        assert record.hypothesis_id == "HYP_BRIDGE_0001"
        assert record.execution_manifest_id == run.manifest.manifest_id
        expected_returns = tuple(derive_canonical_equity_returns(run.equity_table))
        assert record.in_sample_return_series_sha256 == _compute_canonical_series_sha256(expected_returns)
        assert record.in_sample_sharpe == calculate_annualized_sharpe(expected_returns, _PPY)
        assert assembly.canonical_sharpe_by_trial["TR-1"] == record.in_sample_sharpe
        assert assembly.manifest_store[run.manifest.manifest_id] is run.manifest

    def test_multi_trial_matrix_column_alignment_and_equal_length_contract(self) -> None:
        run_a = _synthetic_run(
            "TR-A", "HYP_BRIDGE_0002",
            [Decimal("100000"), Decimal("101000"), Decimal("99000"), Decimal("102000")],
            "M" * 32 + "A",
        )
        run_b = _synthetic_run(
            "TR-B", "HYP_BRIDGE_0002",
            [Decimal("100000"), Decimal("100500"), Decimal("101000"), Decimal("99000")],
            "M" * 32 + "B",
        )
        assembly = assemble_phase_six_evidence([run_a, run_b], _PPY)

        assert assembly.trial_return_matrix.shape == (3, 2)
        assert assembly.trial_matrix_column_trial_ids == ("TR-A", "TR-B")
        assert assembly.trial_records[0].trial_id == "TR-A"
        assert assembly.trial_records[1].trial_id == "TR-B"
        assert set(assembly.manifest_store.keys()) == {run_a.manifest.manifest_id, run_b.manifest.manifest_id}
        # Highest-nonzero principal component of the matrix must equal the primary trial column:
        assert assembly.primary_in_sample_returns == tuple(derive_canonical_equity_returns(run_a.equity_table))


class TestAssemblyFailClosed:
    def test_empty_runs_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="no trial runs"):
            assemble_phase_six_evidence([], _PPY)

    def test_duplicate_trial_ids_fails_closed(self) -> None:
        run_a = _synthetic_run(
            "TR-DUP", "HYP_BRIDGE_0003",
            [Decimal("100000"), Decimal("101000"), Decimal("99000")],
            "X" * 32 + "1",
        )
        run_b = _synthetic_run(
            "TR-DUP", "HYP_BRIDGE_0003",
            [Decimal("100000"), Decimal("101000"), Decimal("99000")],
            "X" * 32 + "2",
        )
        with pytest.raises(DataContractError, match="duplicate trial_id"):
            assemble_phase_six_evidence([run_a, run_b], _PPY)

    def test_duplicate_manifest_id_fails_closed(self) -> None:
        run_a = _synthetic_run(
            "TR-1", "HYP_BRIDGE_0004",
            [Decimal("100000"), Decimal("101000"), Decimal("99000")],
            "Y" * 32,
        )
        run_b = _synthetic_run(
            "TR-2", "HYP_BRIDGE_0004",
            [Decimal("100000"), Decimal("101000"), Decimal("99000")],
            "Y" * 32,
        )
        with pytest.raises(DataContractError, match="duplicate manifest_id"):
            assemble_phase_six_evidence([run_a, run_b], _PPY)

    def test_hypothesis_identity_mismatch_fails_closed(self) -> None:
        run = _synthetic_run(
            "TR-1", "HYP_BRIDGE_0005",
            [Decimal("100000"), Decimal("101000"), Decimal("99000")],
            "Z" * 32,
        )
        # Corrupt manifest identity to disagree with the declared trial hypothesis.
        corrupted = BacktestRunEvidence(
            trial_id=run.trial_id,
            strategy_id=run.strategy_id,
            hypothesis_id=run.hypothesis_id,
            feature_names=run.feature_names,
            parameters=run.parameters,
            manifest=_make_manifest(
                hypothesis_id="HYP_CONTRADICTION", manifest_id=run.manifest.manifest_id,
                sharpe=run.manifest.execution_summary.sharpe_ratio,
            ),
            fills_table=run.fills_table,
            equity_table=run.equity_table,
        )
        with pytest.raises(DataContractError, match="does not match declared trial hypothesis_id"):
            assemble_phase_six_evidence([corrupted], _PPY)

    def test_manifest_sharpe_none_fails_closed(self) -> None:
        run = _synthetic_run(
            "TR-1", "HYP_BRIDGE_0006",
            [Decimal("100000"), Decimal("101000"), Decimal("99000")],
            "M" * 32,
        )
        silent = BacktestRunEvidence(
            trial_id=run.trial_id,
            strategy_id=run.strategy_id,
            hypothesis_id=run.hypothesis_id,
            feature_names=run.feature_names,
            parameters=run.parameters,
            manifest=_make_manifest("HYP_BRIDGE_0006", run.manifest.manifest_id, None),
            fills_table=run.fills_table,
            equity_table=run.equity_table,
        )
        with pytest.raises(DataContractError, match="no sharpe_ratio"):
            assemble_phase_six_evidence([silent], _PPY)

    def test_manifest_sharpe_inconsistent_fails_closed(self) -> None:
        run = _synthetic_run(
            "TR-1", "HYP_BRIDGE_0007",
            [Decimal("100000"), Decimal("101000"), Decimal("99000")],
            "M" * 32,
        )
        manifest_sr = run.manifest.execution_summary.sharpe_ratio
        assert manifest_sr is not None
        drift = manifest_sr + Decimal("0.1")  # beyond 0.001 tolerance
        lying = BacktestRunEvidence(
            trial_id=run.trial_id,
            strategy_id=run.strategy_id,
            hypothesis_id=run.hypothesis_id,
            feature_names=run.feature_names,
            parameters=run.parameters,
            manifest=_make_manifest("HYP_BRIDGE_0007", run.manifest.manifest_id, drift),
            fills_table=run.fills_table,
            equity_table=run.equity_table,
        )
        with pytest.raises(DataContractError, match="deviates from canonical Sharpe"):
            assemble_phase_six_evidence([lying], _PPY)

    def test_unequal_return_series_lengths_fails_closed(self) -> None:
        run_a = _synthetic_run(
            "TR-A", "HYP_BRIDGE_0008",
            [Decimal("100000"), Decimal("101000"), Decimal("99000"), Decimal("102000")],
            "N" * 32 + "A",
        )
        run_b = _synthetic_run(
            "TR-B", "HYP_BRIDGE_0008",
            [Decimal("100000"), Decimal("100500"), Decimal("99000")],
            "N" * 32 + "B",
        )
        with pytest.raises(DataContractError, match="length"):
            assemble_phase_six_evidence([run_a, run_b], _PPY)


class TestEngineToBridge:
    """Full chain: Phase 5 engine emits canonical Sharpe -> Evidence Bridge assembles it truthfully."""

    def test_assemble_evidence_from_real_phase5_run(self) -> None:
        bars_table = pa.Table.from_pydict(
            {
                "timestamp_utc": [
                    datetime(2026, 1, 19, 9, 30, 0, tzinfo=timezone.utc) + _MINUTE * i for i in range(5)
                ],
                "open": [Decimal("5000.00"), Decimal("5002.00"), Decimal("5004.00"), Decimal("5008.00"), Decimal("5010.00")],
                "high": [Decimal("5005.00"), Decimal("5010.00"), Decimal("5010.00"), Decimal("5012.00"), Decimal("5010.00")],
                "low": [Decimal("4995.00"), Decimal("5000.00"), Decimal("5002.00"), Decimal("5006.00"), Decimal("5002.00")],
                "close": [Decimal("5002.00"), Decimal("5004.00"), Decimal("5008.00"), Decimal("5010.00"), Decimal("5006.00")],
                "volume": [Decimal("100.0")] * 5,
            }
        )
        events = CanonicalDataAdapter.from_bars_table(bars_table, symbol="ES.FUT")

        class BuyHoldingActor:
            def __init__(self, symbol: str) -> None:
                self._actor = MicrostructureImbalanceActor(symbol=symbol)

            def on_bar(self, event: Any, runner: Any) -> None:
                if event.payload["bar_index"] == 2:
                    self._actor.generate_signal_and_order(Decimal("0.40"), runner)

            def on_trade(self, event: Any, runner: Any) -> None:
                pass

        runner = EventBacktestRunner(
            config=BacktestEngineConfig(engine_id="BKT-BRIDGE-TEST", symbol="ES.FUT"),
            strategy_actor=BuyHoldingActor(symbol="ES.FUT"),
        )
        manifest, fills_tbl, equity_tbl = runner.run_backtest(
            events=events,
            hypothesis_id="HYP_BRIDGE_0009",
            hypothesis_spec_sha256="a" * 64,
            strategy_config_hash="b" * 64,
            pyproject_toml_sha256="c" * 64,
            git_commit_hash="a" * 40,
            periods_per_year=_PPY,
            canonical_data_hashes=["d" * 64],
        )

        assert manifest.execution_summary.sharpe_ratio is not None
        run = BacktestRunEvidence(
            trial_id="TR-ENGINE-1",
            strategy_id="MICROSTRUCTURE_IMBALANCE_V1",
            hypothesis_id="HYP_BRIDGE_0009",
            feature_names=("order_flow_imbalance",),
            parameters={"flow_fraction": Decimal("0.40")},
            manifest=manifest,
            fills_table=fills_tbl,
            equity_table=equity_tbl,
        )
        assembly = assemble_phase_six_evidence([run], _PPY)

        returns = derive_canonical_equity_returns(equity_tbl)
        assert assembly.primary_in_sample_returns == tuple(returns)
        assert assembly.trial_return_matrix.shape == (len(returns), 1)
        record = assembly.trial_records[0]
        assert record.execution_manifest_id == manifest.manifest_id
        assert record.in_sample_return_series_sha256 == _compute_canonical_series_sha256(returns)
        assert record.in_sample_sharpe == manifest.execution_summary.sharpe_ratio
        assert assembly.manifest_store[manifest.manifest_id] is manifest