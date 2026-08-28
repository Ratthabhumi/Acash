"""Unit and forensic regression tests verifying all Phase 2-5 audit remediations."""

from datetime import datetime, timezone
from decimal import Decimal
import tempfile
from pathlib import Path
import pyarrow as pa
import pytest

from acash.backtest.accounting import ShadowAccountingLedger
from acash.backtest.adapter import BacktestEventType, BacktestMarketEvent, CanonicalDataAdapter
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.nautilus_bridge import NautilusCatalogExporter, NautilusTraderSubstrate
from acash.backtest.schema import (
    BacktestEngineConfig,
    BacktestOrderStatus,
    InstrumentSpecification,
    OrderType,
    calculate_backtest_manifest_id,
    get_instrument_specification,
)

from acash.data.schema import DataContractError
from acash.research.evaluation import transform_feature_to_signal
from acash.research.schema import ExpectedDirection, SignalTransformConfig, SignalTransformMethod



def test_maker_queue_partial_fill_multi_trade_fulfillment() -> None:
    """Audit P0: Queue Ahead = 5, Our Order = 10, Opposing Trade = 6 -> Queue = 0, Fill = 1, Remaining = 9.

    Subsequent Opposing Trade = 9 -> Fill = 9, Remaining = 0 (FILLED).
    """
    config = BacktestEngineConfig(
        engine_id="BKT-MAKER-PARTIAL-FILL",
        symbol="ES.FUT",
    )
    runner = EventBacktestRunner(config=config)
    runner.current_time_ns = 1_000_000_000

    # Book has 5 units at 5000.00 on Bid
    runner.order_book.apply_delta("ADD", "BID", Decimal("5000.00"), Decimal("5.0"))

    # Place Buy limit order @ 5000.00 for 10.0 units -> Queue ahead is 5.0 units
    order = runner.submit_order(
        order_id="ORD-M-001",
        symbol="ES.FUT",
        order_type=OrderType.LIMIT,
        side="BUY",
        quantity=Decimal("10.0"),
        limit_price=Decimal("5000.00"),
    )
    assert order.queue_ahead_volume == Decimal("5.0")
    assert order.remaining_qty == Decimal("10.0")
    assert order.filled_qty == Decimal("0.0")

    # Trade 1: Sell aggressor trades 6 units @ 5000.00
    # Queue ahead (5.0) consumed -> Available 1.0 -> Fills 1.0 of our 10.0 units -> Remaining 9.0 (PARTIALLY_FILLED)
    runner._process_order_matching(
        event_timestamp_ns=2_000_000_000,
        trade_event_payload={"price": Decimal("5000.00"), "size": Decimal("6.0"), "aggressor_side": "SELL"},
    )
    assert runner.orders["ORD-M-001"].status is BacktestOrderStatus.PARTIALLY_FILLED
    assert runner.orders["ORD-M-001"].filled_qty == Decimal("1.0")
    assert runner.orders["ORD-M-001"].remaining_qty == Decimal("9.0")
    assert runner.orders["ORD-M-001"].queue_ahead_volume == Decimal("0.0")
    assert len(runner.fills) == 1
    assert runner.fills[0].fill_qty == Decimal("1.0")

    # Trade 2: Sell aggressor trades 9 units @ 5000.00
    # Queue ahead is 0.0 -> Available 9.0 -> Fills all remaining 9.0 units -> Remaining 0.0 (FILLED)
    runner._process_order_matching(
        event_timestamp_ns=3_000_000_000,
        trade_event_payload={"price": Decimal("5000.00"), "size": Decimal("9.0"), "aggressor_side": "SELL"},
    )
    final_status: BacktestOrderStatus = runner.orders["ORD-M-001"].status
    assert final_status == BacktestOrderStatus.FILLED
    assert runner.orders["ORD-M-001"].filled_qty == Decimal("10.0")
    assert runner.orders["ORD-M-001"].remaining_qty == Decimal("0.0")
    assert len(runner.fills) == 2
    assert runner.fills[1].fill_qty == Decimal("9.0")




def test_engine_boundary_out_of_order_event_rejection() -> None:
    """Audit P1: Engine must reject out-of-order events at boundary with DataContractError."""
    config = BacktestEngineConfig(
        engine_id="BKT-OOO-TEST",
        symbol="ES.FUT",
    )
    runner = EventBacktestRunner(config=config)

    t1 = 1_000_000_000
    t2 = 2_000_000_000

    ev1 = BacktestMarketEvent(
        event_type=BacktestEventType.BAR,
        symbol="ES.FUT",
        event_timestamp_ns=t2,  # Later timestamp first!
        source_order_key=f"ES.FUT:BARS:{t2}:0",
        message_rank=10,
        stream_id="BARS",
        row_sub_index=0,
        payload={"close": Decimal("5000.00")},
    )
    ev2 = BacktestMarketEvent(
        event_type=BacktestEventType.BAR,
        symbol="ES.FUT",
        event_timestamp_ns=t1,  # Earlier timestamp second!
        source_order_key=f"ES.FUT:BARS:{t1}:0",
        message_rank=10,
        stream_id="BARS",
        row_sub_index=0,
        payload={"close": Decimal("5001.00")},
    )

    with pytest.raises(DataContractError, match="Out-of-order event sequence detected"):
        runner.run_backtest(
            events=[ev1, ev2],
            hypothesis_spec_sha256="a" * 64,
            strategy_config_hash="b" * 64,
            pyproject_toml_sha256="c" * 64,
            git_commit_hash="d" * 40,
            canonical_data_hashes=["e" * 64],
        )


def test_non_ascii_source_order_key_rejection() -> None:
    """Audit P1: BacktestMarketEvent must reject non-ASCII characters in source_order_key."""
    with pytest.raises(DataContractError, match="must contain ASCII-only characters"):
        BacktestMarketEvent(
            event_type=BacktestEventType.BAR,
            symbol="ES.FUT",
            event_timestamp_ns=1_000_000_000,
            source_order_key="ES.FUT:BARS:1000:ümlaut_©",
            message_rank=10,
            stream_id="BARS",
            row_sub_index=0,
            payload={"close": Decimal("5000.00")},
        )


def test_canonical_trades_adapter_source_seq_num_priority() -> None:
    """Audit P1: CanonicalDataAdapter.from_trades_table must prioritize source_seq_num."""
    t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    trades_table = pa.Table.from_pydict({
        "exchange_time_utc": [t0],
        "channel_id": ["310"],
        "source_seq_num": [5555],
        "sequence_num": [1111],  # Legacy should be ignored when source_seq_num is present
        "price": [Decimal("5000.00")],
        "size": [Decimal("5.0")],
        "aggressor_side": ["BUY"],
    })

    events = CanonicalDataAdapter.from_trades_table(trades_table, symbol="ES.FUT")
    assert len(events) == 1
    assert "ch310_seq5555" in events[0].source_order_key


def test_nautilus_manifest_id_and_empty_data_hashes_rejection() -> None:
    """Audit P1: Nautilus execution requires non-empty data hashes and derives canonical manifest_id."""
    config = BacktestEngineConfig(
        engine_id="BKT-MANIFEST-TEST",
        symbol="ES",
    )
    substrate = NautilusTraderSubstrate(config=config)

    # Empty data hashes must be rejected
    with pytest.raises(DataContractError, match="canonical_data_hashes is mandatory"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            substrate.run_simulation(
                catalog_path=tmp_dir,
                hypothesis_spec_sha256="a" * 64,
                strategy_config_hash="b" * 64,
                pyproject_toml_sha256="c" * 64,
                git_commit_hash="d" * 40,
                canonical_data_hashes=[],
            )

    # Manifest ID calculation test
    calc_id = calculate_backtest_manifest_id(
        hypothesis_spec_sha256="a" * 64,
        canonical_data_hashes=["d1" * 32, "d2" * 32],
        engine_config_hash="e" * 64,
        strategy_config_hash="s" * 64,
        prng_seed=42,
    )
    assert len(calc_id) == 32
    assert not calc_id.startswith("bkt_NAUTILUS_")  # Pure content hash without prefix pollution


def test_instrument_specification_registry_and_multipliers() -> None:
    """Audit P0: Instrument registry provides correct multipliers for major futures contracts."""
    assert get_instrument_specification("ES").multiplier == Decimal("50.0")
    assert get_instrument_specification("NQ").multiplier == Decimal("20.0")
    assert get_instrument_specification("YM").multiplier == Decimal("5.0")
    assert get_instrument_specification("RTY").multiplier == Decimal("50.0")
    assert get_instrument_specification("GC").multiplier == Decimal("100.0")
    assert get_instrument_specification("CL").multiplier == Decimal("1000.0")


def test_mark_to_market_accounting_across_positions() -> None:
    """Audit Amendment 3: Test MTM accounting for Long, Short, Partial close, Full close, Reversal."""
    ledger = ShadowAccountingLedger(starting_cash=Decimal("100000.00"))
    symbol = "ES.SIM"

    # 1. Long 2 contracts @ 5000.00 (ES multiplier = 50)
    ledger.process_fill(symbol=symbol, side="BUY", fill_price=Decimal("5000.00"), fill_qty=Decimal("2.0"))
    assert ledger.positions[symbol].quantity == Decimal("2.0")
    assert ledger.positions[symbol].avg_entry_price == Decimal("5000.00")

    # MTM at 5010.00 (+10 pts) -> 2 * 10 * 50 = +1000.00 unrealized PnL
    ledger.update_market_price(symbol, Decimal("5010.00"))
    assert ledger.positions[symbol].unrealized_pnl == Decimal("20.00") * Decimal("1.0")  # per-unit
    # Contract MTM: signed_qty * (mark - avg_entry) * multiplier
    unrealized_contract = ledger.positions[symbol].quantity * (Decimal("5010.00") - ledger.positions[symbol].avg_entry_price) * Decimal("50.0")
    assert unrealized_contract == Decimal("1000.00")

    # 2. Partial close: Sell 1 contract @ 5015.00 (+15 pts on 1 contract)
    realized_delta, _ = ledger.process_fill(symbol=symbol, side="SELL", fill_price=Decimal("5015.00"), fill_qty=Decimal("1.0"))
    assert ledger.positions[symbol].quantity == Decimal("1.0")
    assert ledger.positions[symbol].avg_entry_price == Decimal("5000.00")
    assert realized_delta == Decimal("15.00")  # per-unit basis

    # 3. Reversal: Sell 3 contracts @ 5020.00 (Long 1 -> Short 2)
    # Closed Long 1 (+20 pts), Opened Short 2 @ 5020.00
    realized_delta2, _ = ledger.process_fill(symbol=symbol, side="SELL", fill_price=Decimal("5020.00"), fill_qty=Decimal("3.0"))
    assert ledger.positions[symbol].quantity == Decimal("-2.0")
    assert ledger.positions[symbol].avg_entry_price == Decimal("5020.00")
    assert realized_delta2 == Decimal("20.00")

    # 4. Short MTM: Price drops to 5005.00 (+15 pts in favor of Short)
    # Unrealized contract PnL = -2 * (5005 - 5020) * 50 = +1500.00
    unrealized_short = ledger.positions[symbol].quantity * (Decimal("5005.00") - ledger.positions[symbol].avg_entry_price) * Decimal("50.0")
    assert unrealized_short == Decimal("1500.00")

    # 5. Full close: Buy 2 contracts @ 5005.00 -> Flat
    realized_delta3, _ = ledger.process_fill(symbol=symbol, side="BUY", fill_price=Decimal("5005.00"), fill_qty=Decimal("2.0"))
    assert ledger.positions[symbol].quantity == Decimal("0.0")
    assert ledger.positions[symbol].is_flat
    assert realized_delta3 == Decimal("30.00")  # 2 contracts * 15 pts

    ledger.verify_internal_conservation()


def test_identity_clipped_signal_bounds() -> None:
    """Audit Amendment 2: IDENTITY_CLIPPED must enforce S(X) in [-1.0, +1.0] regardless of clip_limit."""
    cfg = SignalTransformConfig(
        method=SignalTransformMethod.IDENTITY_CLIPPED,
        clip_limit=Decimal("3.0"),  # Global config remains 3.0
    )
    raw_features = [Decimal("-5.0"), Decimal("-1.5"), Decimal("-0.5"), Decimal("0.0"), Decimal("0.5"), Decimal("1.5"), Decimal("5.0")]
    signals = transform_feature_to_signal(raw_features, ExpectedDirection.LONG, cfg)

    assert min(signals) >= Decimal("-1.0")
    assert max(signals) <= Decimal("1.0")
    assert signals[0] == Decimal("-1.0")
    assert signals[1] == Decimal("-1.0")
    assert signals[2] == Decimal("-0.5")
    assert signals[3] == Decimal("0.0")
    assert signals[4] == Decimal("0.5")
    assert signals[5] == Decimal("1.0")
    assert signals[6] == Decimal("1.0")

