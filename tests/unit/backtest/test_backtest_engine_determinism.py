"""Unit Tests for Backtesting Engine Determinism, Depth-Aware VWAP Execution, Queue Priority, and Latency (Phase 5)."""

from datetime import datetime, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.backtest.adapter import BacktestEventType, BacktestMarketEvent
from acash.backtest.engine import EventBacktestRunner, SimulatedOrderBook
from acash.backtest.schema import (
    BacktestEngineConfig,
    BacktestOrderStatus,
    FeeModelConfig,
    OrderType,
    SimulationLatencyConfig,
    SlippageModelConfig,
    load_current_environment_provenance,
)


def test_simulated_order_book_vwap_sweeps() -> None:
    """Verify L2 order book depth sweeps compute accurate VWAP and remaining quantity."""
    book = SimulatedOrderBook()

    # Add 3 ask levels: 5000 (qty 5), 5001 (qty 10), 5002 (qty 20)
    book.apply_delta("ADD", "ASK", Decimal("5000.00"), Decimal("5.0"))
    book.apply_delta("ADD", "ASK", Decimal("5001.00"), Decimal("10.0"))
    book.apply_delta("ADD", "ASK", Decimal("5002.00"), Decimal("20.0"))

    assert book.best_ask == Decimal("5000.00")
    assert book.total_ask_depth == Decimal("35.0")

    # 1. Sweep 12 units: 5 @ 5000 + 7 @ 5001 -> Cost = 25000 + 35007 = 60007. VWAP = 60007 / 12 = 5000.583333333333333333
    vwap, filled_qty, remaining = book.sweep_asks(Decimal("12.0"))
    assert filled_qty == Decimal("12.0")
    assert remaining == Decimal("0.0")
    expected_vwap = (Decimal("5.0") * Decimal("5000.00") + Decimal("7.0") * Decimal("5001.00")) / Decimal("12.0")
    assert vwap == expected_vwap


def test_maker_queue_priority_and_trade_through_matching() -> None:
    """Verify Maker limit orders respect queue volume ahead and execute on trade-through."""
    config = BacktestEngineConfig(
        engine_id="BKT-MAKER-QUEUE-TEST",
        symbol="ES.FUT",
    )
    runner = EventBacktestRunner(config=config)
    runner.current_time_ns = 1_000_000_000

    # Book has 10 units at 5000.00 on Bid
    runner.order_book.apply_delta("ADD", "BID", Decimal("5000.00"), Decimal("10.0"))

    # Place Buy limit order @ 5000.00 for 2.0 units -> Queue ahead is 10.0 units
    order = runner.submit_order(
        order_id="ORD-M-001",
        symbol="ES.FUT",
        order_type=OrderType.LIMIT,
        side="BUY",
        quantity=Decimal("2.0"),
        limit_price=Decimal("5000.00"),
    )
    assert order.queue_ahead_volume == Decimal("10.0")

    # Trade 1: Sell aggressor trades 6 units @ 5000.00 -> Queue ahead becomes 4.0 (Order not filled yet)
    runner._process_order_matching(
        event_timestamp_ns=2_000_000_000,
        trade_event_payload={"price": Decimal("5000.00"), "size": Decimal("6.0"), "aggressor_side": "SELL"},
    )
    status_t1 = runner.orders["ORD-M-001"].status
    assert status_t1 is BacktestOrderStatus.ACCEPTED
    assert runner.orders["ORD-M-001"].queue_ahead_volume == Decimal("4.0")

    # Trade 2: Sell aggressor trades 5 units @ 5000.00 -> Queue ahead becomes -1.0 -> Order is FILLED!
    runner._process_order_matching(
        event_timestamp_ns=3_000_000_000,
        trade_event_payload={"price": Decimal("5000.00"), "size": Decimal("5.0"), "aggressor_side": "SELL"},
    )
    status_t2 = runner.orders["ORD-M-001"].status
    assert status_t2 is BacktestOrderStatus.FILLED
    assert len(runner.fills) == 1



def _make_deterministic_event_stream() -> list[BacktestMarketEvent]:
    """Create a synthetic deterministic series of 10 minute bars."""
    events = []
    base_ts = int(datetime(2026, 1, 19, 9, 30, 0, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
    prices = [
        Decimal("5000.00"),
        Decimal("5002.00"),
        Decimal("5005.00"),
        Decimal("5003.00"),
        Decimal("5008.00"),
        Decimal("5010.00"),
        Decimal("5007.00"),
        Decimal("5012.00"),
        Decimal("5015.00"),
        Decimal("5020.00"),
    ]

    for i, p in enumerate(prices):
        ts = base_ts + (i * 60 * 1_000_000_000)
        ev = BacktestMarketEvent(
            event_type=BacktestEventType.BAR,
            symbol="ES.FUT",
            event_timestamp_ns=ts,
            source_order_key=f"ES.FUT:BARS:{ts}:{i:08d}",
            message_rank=10,
            stream_id="BARS",
            row_sub_index=0,
            payload={
                "open": p - Decimal("1.0"),
                "high": p + Decimal("2.0"),
                "low": p - Decimal("2.0"),
                "close": p,
                "volume": Decimal("100"),
                "bar_index": i,
            },
        )
        events.append(ev)
    return events


class SimpleMockActor:
    """Mock strategy actor buying at bar 1, selling at bar 5."""

    def on_bar(self, event: BacktestMarketEvent, runner: EventBacktestRunner) -> None:
        idx = event.payload["bar_index"]
        if idx == 1:
            runner.submit_order(
                order_id="ORD-001",
                symbol="ES.FUT",
                order_type=OrderType.MARKET,
                side="BUY",
                quantity=Decimal("2.0"),
            )
        elif idx == 5:
            runner.submit_order(
                order_id="ORD-002",
                symbol="ES.FUT",
                order_type=OrderType.MARKET,
                side="SELL",
                quantity=Decimal("2.0"),
            )

    def on_trade(self, event: BacktestMarketEvent, runner: EventBacktestRunner) -> None:
        pass


def test_bitwise_replay_invariance() -> None:
    """Verify re-running simulation with identical inputs produces bitwise-identical fills, equity, and manifest."""
    config = BacktestEngineConfig(
        engine_id="BKT-DETERMINISTIC-TEST",
        symbol="ES.FUT",
        initial_cash=Decimal("100000.00"),
        fee_config=FeeModelConfig(taker_fee_bps=Decimal("1.0")),
        slippage_config=SlippageModelConfig(fixed_slippage_bps=Decimal("0.5")),
        prng_seed=42,
    )

    hyp_hash = "h" * 64
    strategy_hash = "s" * 64
    pyproject_sha256, uv_lock_sha256, git_commit = load_current_environment_provenance()

    # Run 1
    events1 = _make_deterministic_event_stream()
    runner1 = EventBacktestRunner(config=config, strategy_actor=SimpleMockActor())
    manifest1, fills1, equity1 = runner1.run_backtest(
        events=events1,
        hypothesis_spec_sha256=hyp_hash,
        strategy_config_hash=strategy_hash,
        pyproject_toml_sha256=pyproject_sha256,
        uv_lock_sha256=uv_lock_sha256,
        git_commit_hash=git_commit,
    )

    # Run 2
    events2 = _make_deterministic_event_stream()
    runner2 = EventBacktestRunner(config=config, strategy_actor=SimpleMockActor())
    manifest2, fills2, equity2 = runner2.run_backtest(
        events=events2,
        hypothesis_spec_sha256=hyp_hash,
        strategy_config_hash=strategy_hash,
        pyproject_toml_sha256=pyproject_sha256,
        uv_lock_sha256=uv_lock_sha256,
        git_commit_hash=git_commit,
    )

    # 1. Exact Manifest ID Equivalence
    assert manifest1.manifest_id == manifest2.manifest_id
    assert manifest1.execution_summary == manifest2.execution_summary
    assert manifest1.reality_gap == manifest2.reality_gap

    # 2. Bitwise Equivalent Fills
    assert fills1.equals(fills2)
    assert fills1.num_rows == 2

    # 3. Bitwise Equivalent Equity Curves
    assert equity1.equals(equity2)
    assert equity1.num_rows == 10


def test_causal_latency_delay_matching() -> None:
    """Verify limit orders with latency do not execute before created_timestamp + latency delay."""
    latency = SimulationLatencyConfig(
        signal_calc_latency_ns=100_000_000,
        uplink_latency_ns=500_000_000,
        matching_engine_latency_ns=400_000_000,  # Total match latency = 1.0 second
    )
    config = BacktestEngineConfig(
        engine_id="BKT-LATENCY-TEST",
        symbol="ES.FUT",
        latency_config=latency,
    )

    runner = EventBacktestRunner(config=config)
    runner.current_time_ns = 1_000_000_000  # t = 1.0s
    runner.last_price = Decimal("5000.00")

    # Submit limit order at t=1.0s. Must match at earliest t=2.0s
    order = runner.submit_order(
        order_id="ORD-LIMIT-001",
        symbol="ES.FUT",
        order_type=OrderType.LIMIT,
        side="BUY",
        quantity=Decimal("1.0"),
        limit_price=Decimal("5005.00"),
    )
    status_at_submission = runner.orders["ORD-LIMIT-001"].status
    assert status_at_submission is BacktestOrderStatus.SUBMITTED

    # At t = 1.5s, matching runs -> Latency not satisfied (1.5s < 1.0s + 1.0s) -> Order remains active
    runner._process_order_matching(event_timestamp_ns=1_500_000_000)
    status_at_1_5s = runner.orders["ORD-LIMIT-001"].status
    assert status_at_1_5s is BacktestOrderStatus.SUBMITTED

    # At t = 2.0s, matching runs -> Latency satisfied -> Order is ACCEPTED and FILLED
    runner._process_order_matching(event_timestamp_ns=2_000_000_000)
    status_at_2_0s = runner.orders["ORD-LIMIT-001"].status
    assert status_at_2_0s is BacktestOrderStatus.FILLED
    assert len(runner.fills) == 1
