"""Unit Tests for Backtesting Schemas, Models, and Manifest Identity (Phase 5)."""

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
)


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


def test_canonical_backtest_arrow_schemas() -> None:
    """Verify Arrow table schema types and nullability constraints."""
    assert CANONICAL_BACKTEST_FILLS_SCHEMA.field("fill_id").type == pa.utf8()
    assert CANONICAL_BACKTEST_FILLS_SCHEMA.field("fill_price").type == pa.decimal128(38, 18)
    assert CANONICAL_BACKTEST_FILLS_SCHEMA.field("fill_timestamp_utc").type == pa.timestamp("ns", tz="UTC")

    assert CANONICAL_EQUITY_CURVE_SCHEMA.field("total_equity").type == pa.decimal128(38, 18)
    assert CANONICAL_EQUITY_CURVE_SCHEMA.field("accounting_residual").type == pa.decimal128(38, 18)
