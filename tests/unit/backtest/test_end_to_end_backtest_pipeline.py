"""Comprehensive End-to-End Integration Tests for Backtesting Pipeline (Phase 5).

Verifies the entire execution chain:
Canonical Data -> Data Adapter -> Event-Driven Engine -> Shadow Accounting -> Reality Gap Attribution -> Backtest Manifest
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import pyarrow as pa
import pytest


from acash.backtest.adapter import CanonicalDataAdapter
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.schema import (
    BacktestEngineConfig,
    FeeModelConfig,
    OrderType,
    SimulationLatencyConfig,
    SlippageModelConfig,
    load_current_environment_provenance,
)
from acash.backtest.strategies.imbalance_actor import MicrostructureImbalanceActor



def _generate_synthetic_market_history() -> pa.Table:
    """Generate synthetic 60-bar OHLCV market history."""
    timestamps = []
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    base_ts = datetime(2026, 1, 19, 9, 30, 0, tzinfo=timezone.utc)
    current_price = Decimal("5000.00")

    for i in range(60):
        ts = datetime.fromtimestamp(base_ts.timestamp() + (i * 60), tz=timezone.utc)
        timestamps.append(ts)

        # Oscillating trend
        drift = Decimal("1.50") if (i // 10) % 2 == 0 else Decimal("-1.50")
        o = current_price
        c = current_price + drift
        h = max(o, c) + Decimal("1.00")
        l = min(o, c) - Decimal("1.00")
        v = Decimal("100.0") + Decimal(str(i % 10 * 10))

        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        volumes.append(v)

        current_price = c

    return pa.Table.from_pydict(
        {
            "timestamp_utc": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


class EndToEndActor:
    """Actor evaluating simulated signals and placing market orders."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.actor = MicrostructureImbalanceActor(symbol=symbol)

    def on_bar(self, event: Any, runner: Any) -> None:
        idx = event.payload["bar_index"]
        # Generate synthetic OBI signal from price trend
        if idx % 10 == 2:
            self.actor.generate_signal_and_order(Decimal("0.40"), runner)
        elif idx % 10 == 7:
            self.actor.generate_signal_and_order(Decimal("-0.40"), runner)

    def on_trade(self, event: Any, runner: Any) -> None:
        pass



def test_end_to_end_backtest_pipeline_execution() -> None:
    """Verify complete end-to-end execution, manifest emission, and conservation invariant."""
    bars_table = _generate_synthetic_market_history()
    events = CanonicalDataAdapter.from_bars_table(bars_table, symbol="ES.FUT")

    config = BacktestEngineConfig(
        engine_id="BKT-E2E-TEST",
        symbol="ES.FUT",
        initial_cash=Decimal("200000.00"),
        latency_config=SimulationLatencyConfig(
            signal_calc_latency_ns=50_000_000,
            uplink_latency_ns=100_000_000,
        ),
        fee_config=FeeModelConfig(
            maker_fee_bps=Decimal("-0.1"),
            taker_fee_bps=Decimal("1.2"),
            fixed_fee_per_trade=Decimal("0.25"),
        ),
        slippage_config=SlippageModelConfig(
            fixed_slippage_bps=Decimal("0.5"),
        ),
        prng_seed=12345,
    )

    actor = EndToEndActor(symbol="ES.FUT")
    runner = EventBacktestRunner(config=config, strategy_actor=actor)

    pyproject_sha256, uv_lock_sha256, git_commit = load_current_environment_provenance()

    manifest, fills_tbl, equity_tbl = runner.run_backtest(
        events=events,
        hypothesis_spec_sha256="a" * 64,
        strategy_config_hash="b" * 64,
        pyproject_toml_sha256=pyproject_sha256,
        uv_lock_sha256=uv_lock_sha256,
        git_commit_hash=git_commit,
        phase4_analytical_edge_bps=Decimal("25.0"),
    )


    # 1. Manifest Identity Verification
    assert len(manifest.manifest_id) == 32
    assert manifest.prng_seed == 12345
    assert manifest.execution_summary.total_fills > 0
    assert manifest.reality_gap.phase4_analytical_edge_bps == Decimal("25.0")

    # 2. Table Integrity
    assert fills_tbl.num_rows == manifest.execution_summary.total_fills
    assert equity_tbl.num_rows == 60

    # 3. Strict Double-Entry Conservation Verification
    final_eq = runner.ledger.calculate_balance_sheet_equity()
    assert final_eq == manifest.execution_summary.ending_equity
    runner.ledger.verify_internal_conservation()
