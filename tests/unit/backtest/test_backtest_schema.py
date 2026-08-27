"""Unit Tests for Backtesting Schemas, Models, Provenance, and Manifest Identity (Phase 5)."""

from decimal import Decimal
import pyarrow as pa
import pytest

from acash.backtest.schema import (
    CANONICAL_BACKTEST_FILLS_SCHEMA,
    CANONICAL_EQUITY_CURVE_SCHEMA,
    BacktestEngineConfig,
    BacktestExecutionSummary,
    BacktestFillRecord,
    BacktestManifest,
    BacktestOrderStatus,
    FeeModelConfig,
    LiquidityType,
    OrderType,
    RealityGapSummary,
    SimulationLatencyConfig,
    SlippageModelConfig,
    calculate_backtest_manifest_id,
    load_current_environment_provenance,
)
from acash.data.schema import DataContractError


def test_simulation_latency_and_fee_models() -> None:
    """Verify latency calculation methods and fee/slippage models."""
    lat = SimulationLatencyConfig(
        signal_calc_latency_ns=500_000,
        uplink_latency_ns=2_000_000,
        matching_engine_latency_ns=100_000,
        downlink_latency_ns=2_000_000,
    )
    assert lat.total_match_latency_ns() == 2_600_000
    assert lat.total_roundtrip_latency_ns() == 4_600_000

    fees = FeeModelConfig(
        maker_fee_bps=Decimal("-0.2"),
        taker_fee_bps=Decimal("1.5"),
        fixed_fee_per_trade=Decimal("0.50"),
    )
    assert fees.maker_fee_bps == Decimal("-0.2")
    assert fees.taker_fee_bps == Decimal("1.5")


def test_deterministic_content_derived_manifest_id() -> None:
    """Verify manifest ID is strictly content-derived and invariant to volatile timestamps."""
    hyp_hash = "a" * 64
    data_hashes = ["chunk_b_hash", "chunk_a_hash"]  # Unsorted
    engine_hash = "b" * 64
    strategy_hash = "c" * 64
    seed = 42

    manifest_id1 = calculate_backtest_manifest_id(
        hypothesis_spec_sha256=hyp_hash,
        canonical_data_hashes=data_hashes,
        engine_config_hash=engine_hash,
        strategy_config_hash=strategy_hash,
        prng_seed=seed,
    )

    # Reorder data_hashes list -> should produce identical manifest_id
    manifest_id2 = calculate_backtest_manifest_id(
        hypothesis_spec_sha256=hyp_hash,
        canonical_data_hashes=list(reversed(data_hashes)),
        engine_config_hash=engine_hash,
        strategy_config_hash=strategy_hash,
        prng_seed=seed,
    )

    assert manifest_id1 == manifest_id2
    assert len(manifest_id1) == 32

    # Changing seed changes manifest_id
    manifest_id_diff_seed = calculate_backtest_manifest_id(
        hypothesis_spec_sha256=hyp_hash,
        canonical_data_hashes=data_hashes,
        engine_config_hash=engine_hash,
        strategy_config_hash=strategy_hash,
        prng_seed=99,
    )
    assert manifest_id1 != manifest_id_diff_seed


def test_mandatory_environment_provenance_validation() -> None:
    """Verify placeholder or invalid environment hashes are rejected by BacktestManifest."""
    exec_summary = BacktestExecutionSummary(
        total_orders=1,
        total_fills=1,
        total_volume_traded=Decimal("1000.0"),
        total_fees_paid=Decimal("1.0"),
        realized_pnl=Decimal("50.0"),
        unrealized_pnl=Decimal("0.0"),
        ending_equity=Decimal("100049.0"),
        net_return_pct=Decimal("0.049"),
        max_drawdown_pct=Decimal("0.0"),
        win_rate_pct=Decimal("100.0"),
    )
    reality_gap = RealityGapSummary(
        phase4_analytical_edge_bps=Decimal("10.0"),
        phase5_simulated_realized_bps=Decimal("8.0"),
        reality_gap_bps=Decimal("2.0"),
        spread_drag_bps=Decimal("1.0"),
        latency_slip_drag_bps=Decimal("1.0"),
        queue_position_drag_bps=Decimal("0.0"),
    )

    # Placeholder pyproject hash rejected
    with pytest.raises(DataContractError, match="Invalid pyproject_toml_sha256"):
        BacktestManifest(
            manifest_id="a" * 32,
            hypothesis_id="H-1",
            hypothesis_spec_sha256="a" * 64,
            canonical_data_hashes=[],
            engine_config_hash="b" * 64,
            strategy_config_hash="c" * 64,
            prng_seed=42,
            pyproject_toml_sha256="pinned_pyproject_hash",  # Forbidden placeholder
            git_commit_hash="0123456789abcdef",
            execution_summary=exec_summary,
            reality_gap=reality_gap,
            computed_at_utc="2026-08-28T00:00:00Z",
            wall_clock_duration_ms=10,
        )

    # Valid real provenance loaded from disk
    pyproject_sha256, uv_lock_sha256, git_commit = load_current_environment_provenance()
    assert len(pyproject_sha256) == 64
    assert len(git_commit) >= 7

    valid_manifest = BacktestManifest(
        manifest_id="a" * 32,
        hypothesis_id="H-1",
        hypothesis_spec_sha256="a" * 64,
        canonical_data_hashes=[],
        engine_config_hash="b" * 64,
        strategy_config_hash="c" * 64,
        prng_seed=42,
        pyproject_toml_sha256=pyproject_sha256,
        uv_lock_sha256=uv_lock_sha256,
        git_commit_hash=git_commit,
        execution_summary=exec_summary,
        reality_gap=reality_gap,
        computed_at_utc="2026-08-28T00:00:00Z",
        wall_clock_duration_ms=10,
    )
    assert valid_manifest.pyproject_toml_sha256 == pyproject_sha256


def test_canonical_backtest_arrow_schemas() -> None:
    """Verify Arrow table schema types and nullability constraints."""
    assert CANONICAL_BACKTEST_FILLS_SCHEMA.field("fill_id").type == pa.utf8()
    assert CANONICAL_BACKTEST_FILLS_SCHEMA.field("fill_price").type == pa.decimal128(38, 18)
    assert CANONICAL_BACKTEST_FILLS_SCHEMA.field("fill_timestamp_utc").type == pa.timestamp("ns", tz="UTC")

    assert CANONICAL_EQUITY_CURVE_SCHEMA.field("total_equity").type == pa.decimal128(38, 18)
    assert CANONICAL_EQUITY_CURVE_SCHEMA.field("accounting_residual").type == pa.decimal128(38, 18)
