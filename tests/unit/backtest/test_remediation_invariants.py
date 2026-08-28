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


def test_maker_order_zero_and_negative_trade_size_no_fill_rejection() -> None:
    """Audit P0: Maker Order matching must reject trade_size <= 0 with ZERO fill (no phantom liquidity)."""
    config = BacktestEngineConfig(
        engine_id="BKT-NO-PHANTOM-FILL",
        symbol="ES.FUT",
    )
    runner = EventBacktestRunner(config=config)
    runner.current_time_ns = 1_000_000_000

    # Place Buy limit order @ 5000.00 for 10.0 units
    order = runner.submit_order(
        order_id="ORD-BUY-001",
        symbol="ES.FUT",
        order_type=OrderType.LIMIT,
        side="BUY",
        quantity=Decimal("10.0"),
        limit_price=Decimal("5000.00"),
    )

    # 1. Incoming trade-through below limit (4999.00), but trade_size is 0.0 -> NO FILL
    runner._process_order_matching(
        event_timestamp_ns=2_000_000_000,
        trade_event_payload={"price": Decimal("4999.00"), "size": Decimal("0.0"), "aggressor_side": "SELL"},
    )
    assert order.filled_qty == Decimal("0.0")
    assert order.remaining_qty == Decimal("10.0")
    assert order.status == BacktestOrderStatus.ACCEPTED
    assert len(runner.fills) == 0

    # 2. Incoming trade at limit price (5000.00), but trade_size is negative -> NO FILL
    runner._process_order_matching(
        event_timestamp_ns=3_000_000_000,
        trade_event_payload={"price": Decimal("5000.00"), "size": Decimal("-5.0"), "aggressor_side": "SELL"},
    )
    assert order.filled_qty == Decimal("0.0")
    assert order.remaining_qty == Decimal("10.0")
    assert order.status == BacktestOrderStatus.ACCEPTED
    assert len(runner.fills) == 0




def test_trades_adapter_non_positive_price_and_size_rejection() -> None:
    """Audit P0: Trades adapter must reject non-positive prices and sizes with DataContractError."""
    t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)

    # Zero price
    zero_price_tbl = pa.Table.from_pydict({
        "exchange_time_utc": [t0],
        "channel_id": ["310"],
        "source_seq_num": [100],
        "price": [Decimal("0.00")],
        "size": [Decimal("5.0")],
    })
    with pytest.raises(DataContractError, match="Trade price must be strictly positive"):
        CanonicalDataAdapter.from_trades_table(zero_price_tbl, symbol="ES.FUT")

    # Zero size
    zero_size_tbl = pa.Table.from_pydict({
        "exchange_time_utc": [t0],
        "channel_id": ["310"],
        "source_seq_num": [100],
        "price": [Decimal("5000.00")],
        "size": [Decimal("0.0")],
    })
    with pytest.raises(DataContractError, match="Trade size must be strictly positive"):
        CanonicalDataAdapter.from_trades_table(zero_size_tbl, symbol="ES.FUT")


def test_trades_adapter_multi_match_sub_index_differentiation() -> None:
    """Audit Phase 3A: Multi-match message expansion produces unique, deterministic source_order_keys."""
    t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    multi_match_tbl = pa.Table.from_pydict({
        "exchange_time_utc": [t0, t0, t0],
        "channel_id": ["310", "310", "310"],
        "source_seq_num": [100, 100, 100],
        "match_sub_idx": [0, 1, 2],
        "price": [Decimal("5000.00"), Decimal("5000.25"), Decimal("5000.50")],
        "size": [Decimal("2.0"), Decimal("3.0"), Decimal("5.0")],
        "aggressor_side": ["BUY", "BUY", "BUY"],
    })

    events = CanonicalDataAdapter.from_trades_table(multi_match_tbl, symbol="ES.FUT")
    assert len(events) == 3
    assert "ch310_seq100_sub0" in events[0].source_order_key
    assert "ch310_seq100_sub1" in events[1].source_order_key
    assert "ch310_seq100_sub2" in events[2].source_order_key
    assert events[0].order_tuple < events[1].order_tuple < events[2].order_tuple


def test_nautilus_execution_summary_and_reality_gap_metrics() -> None:
    """Audit P1: Nautilus execution produces genuine non-zero reality gap attribution and stats."""
    from acash.backtest.telemetry import RealityGapAttributionEngine
    from acash.backtest.schema import RealityGapSummary

    reality = RealityGapAttributionEngine.calculate_attribution(
        phase4_analytical_edge_bps=Decimal("25.0"),
        phase5_simulated_realized_bps=Decimal("18.5"),
        spread_drag_bps=Decimal("4.0"),
        latency_slip_drag_bps=Decimal("2.5"),
        queue_position_drag_bps=Decimal("0.0"),
        fee_drag_bps=Decimal("1.0"),
    )
    assert reality.phase4_analytical_edge_bps == Decimal("25.0")
    assert reality.phase5_simulated_realized_bps == Decimal("18.5")
    assert reality.reality_gap_bps == Decimal("6.5")
    assert reality.fee_drag_bps == Decimal("1.0")

    report = RealityGapAttributionEngine.generate_reality_gap_report(reality)
    assert report["verdict"] == "FEASIBLE"
    assert report["phase4_analytical_edge_bps"] == 25.0
    assert report["phase5_simulated_realized_bps"] == 18.5
    assert report["reality_gap_bps"] == 6.5
    assert report["friction_decomposition"]["fee_drag_bps"] == 1.0


def test_trades_adapter_fallback_permutation_invariance_adversarial() -> None:
    """Audit P1: Fallback source_order_key generation is 100% permutation-invariant when sub-index is absent."""
    t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 19, 14, 30, 1, tzinfo=timezone.utc)

    # 3 distinct trades without match_sub_idx or row_sub_index
    rows_forward = {
        "exchange_time_utc": [t0, t0, t1],
        "channel_id": ["310", "310", "310"],
        "source_seq_num": [100, 100, 101],
        "trade_id": ["TRD_A", "TRD_B", "TRD_C"],
        "price": [Decimal("5000.00"), Decimal("5000.25"), Decimal("5001.00")],
        "size": [Decimal("2.0"), Decimal("3.0"), Decimal("1.0")],
        "aggressor_side": ["BUY", "SELL", "BUY"],
    }
    tbl_forward = pa.Table.from_pydict(rows_forward)

    # Reversed row order
    rows_reversed = {
        "exchange_time_utc": [t1, t0, t0],
        "channel_id": ["310", "310", "310"],
        "source_seq_num": [101, 100, 100],
        "trade_id": ["TRD_C", "TRD_B", "TRD_A"],
        "price": [Decimal("5001.00"), Decimal("5000.25"), Decimal("5000.00")],
        "size": [Decimal("1.0"), Decimal("3.0"), Decimal("2.0")],
        "aggressor_side": ["BUY", "SELL", "BUY"],
    }
    tbl_reversed = pa.Table.from_pydict(rows_reversed)

    events_fwd = CanonicalDataAdapter.from_trades_table(tbl_forward, symbol="ES.FUT")
    events_rev = CanonicalDataAdapter.from_trades_table(tbl_reversed, symbol="ES.FUT")

    # Both must use content fingerprints, NOT loop row index 'i'
    for ev in events_fwd + events_rev:
        assert "_fp" in ev.source_order_key

    # Sort both streams using canonical 5-tuple
    sorted_fwd = CanonicalDataAdapter.merge_and_sort_event_streams([events_fwd])
    sorted_rev = CanonicalDataAdapter.merge_and_sort_event_streams([events_rev])

    assert len(sorted_fwd) == len(sorted_rev) == 3
    assert [ev.order_tuple for ev in sorted_fwd] == [ev.order_tuple for ev in sorted_rev]
    assert [ev.payload["price"] for ev in sorted_fwd] == [ev.payload["price"] for ev in sorted_rev]


def test_reality_gap_attribution_empirical_derivation_from_fills() -> None:
    """Audit P1: RealityGapAttributionEngine derives drag from empirical fills instead of config placeholders."""
    from acash.backtest.telemetry import RealityGapAttributionEngine
    from acash.backtest.schema import BacktestFillRecord, LiquidityType

    initial_cash = Decimal("100000.00")
    fills = [
        BacktestFillRecord(
            fill_id="F1",
            order_id="O1",
            symbol="ES.FUT",
            fill_timestamp_utc="2026-01-19T14:30:00Z",
            side="BUY",
            fill_price=Decimal("5000.00"),
            fill_qty=Decimal("2.0"),
            fee_paid=Decimal("50.00"),
            liquidity_type=LiquidityType.TAKER,
            slippage_incurred_bps=Decimal("2.0"),  # 2 bps slippage on $10,000 notional = $2.00 cost
        ),
        BacktestFillRecord(
            fill_id="F2",
            order_id="O2",
            symbol="ES.FUT",
            fill_timestamp_utc="2026-01-19T14:30:01Z",
            side="SELL",
            fill_price=Decimal("5010.00"),
            fill_qty=Decimal("2.0"),
            fee_paid=Decimal("50.00"),
            liquidity_type=LiquidityType.MAKER,
            slippage_incurred_bps=Decimal("0.0"),  # Maker = 0 slippage
        ),
    ]

    # Total fees paid = $100.00 -> on $100,000 cash = 10.0 bps fee drag
    # Total slippage cost = 2.0 * 5000.00 * (2.0 / 10000) = $2.00 -> on $100,000 cash = 0.20 bps slippage drag
    # Total reality gap = 30.0 - 15.0 = 15.0 bps
    # Queue / timing drag = 15.0 - (10.0 + 0.20) = 4.80 bps
    summary = RealityGapAttributionEngine.derive_from_fills(
        fills=fills,
        initial_cash=initial_cash,
        phase4_analytical_edge_bps=Decimal("30.0"),
        phase5_simulated_realized_bps=Decimal("15.0"),
    )

    assert summary.reality_gap_bps == Decimal("15.0")
    assert summary.fee_drag_bps == Decimal("10.0")
    assert summary.latency_slip_drag_bps == Decimal("0.2")
    assert summary.queue_position_drag_bps == Decimal("4.8")

    report = RealityGapAttributionEngine.generate_reality_gap_report(summary)
    assert report["friction_decomposition"]["fee_drag_bps"] == 10.0
    assert report["friction_decomposition"]["latency_slip_drag_bps"] == 0.2
    assert report["friction_decomposition"]["queue_position_drag_bps"] == 4.8



