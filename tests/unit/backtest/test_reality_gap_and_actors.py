"""Unit Tests for Reality Gap Attribution Engine and Baseline Strategy Actors (Phase 5)."""

from decimal import Decimal
import pytest

from acash.backtest.adapter import BacktestEventType, BacktestMarketEvent
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.schema import BacktestEngineConfig, RealityGapSummary
from acash.backtest.strategies.imbalance_actor import MicrostructureImbalanceActor
from acash.backtest.strategies.vwap_actor import VwapMeanReversionActor
from acash.backtest.telemetry import RealityGapAttributionEngine


def test_reality_gap_attribution_decomposition() -> None:
    """Verify reality gap arithmetic and drag decomposition reporting."""
    summary = RealityGapAttributionEngine.calculate_attribution(
        phase4_analytical_edge_bps=Decimal("15.0"),
        phase5_simulated_realized_bps=Decimal("11.5"),
        spread_drag_bps=Decimal("2.0"),
        slippage_drag_bps=Decimal("1.0"),
        latency_drag_bps=Decimal("0.5"),
        maker_adverse_selection_drag_bps=Decimal("0.0"),
    )

    assert summary.reality_gap_bps == Decimal("3.5")
    report = RealityGapAttributionEngine.generate_reality_gap_report(summary)

    assert report["phase4_analytical_edge_bps"] == 15.0
    assert report["phase5_simulated_realized_bps"] == 11.5
    assert report["reality_gap_bps"] == 3.5
    assert report["verdict"] == "FEASIBLE"


def test_microstructure_imbalance_actor_order_triggers() -> None:
    """Verify OBI actor triggers buy when imbalance >= threshold and sell when <= -threshold."""
    config = BacktestEngineConfig(engine_id="BKT-OBI-TEST", symbol="ES.FUT")
    runner = EventBacktestRunner(config=config)
    runner.last_price = Decimal("5000.00")

    actor = MicrostructureImbalanceActor(
        symbol="ES.FUT",
        threshold_long=Decimal("0.30"),
        threshold_short=Decimal("-0.30"),
        trade_size=Decimal("1.0"),
    )

    # 1. Bullish imbalance -> Triggers BUY
    order_id1 = actor.generate_signal_and_order(Decimal("0.45"), runner)
    assert order_id1 is not None
    assert runner.ledger.positions["ES.FUT"].quantity == Decimal("1.0")

    # 2. Reversal Bearish imbalance -> Triggers SELL to close Long and open Short
    order_id2 = actor.generate_signal_and_order(Decimal("-0.50"), runner)
    assert order_id2 is not None
    assert runner.ledger.positions["ES.FUT"].quantity == Decimal("-1.0")


def test_vwap_mean_reversion_actor_order_triggers() -> None:
    """Verify VWAP mean reversion actor buys when oversold and sells when overbought."""
    config = BacktestEngineConfig(engine_id="BKT-VWAP-TEST", symbol="ES.FUT")
    runner = EventBacktestRunner(config=config)

    actor = VwapMeanReversionActor(
        symbol="ES.FUT",
        deviation_threshold_bps=Decimal("20.0"),
        trade_size=Decimal("1.0"),
    )

    # Bar with Price = 5020, VWAP = 5000 -> Diff = +40 bps >= +20 bps -> Triggers SELL
    ev_overbought = BacktestMarketEvent(
        event_type=BacktestEventType.BAR,
        symbol="ES.FUT",
        event_timestamp_ns=1000,
        source_order_key="k1",
        message_rank=1,
        stream_id="BARS",
        row_sub_index=0,
        payload={"close": Decimal("5020.00"), "vwap": Decimal("5000.00")},
    )

    runner.current_time_ns = 1000
    runner.last_price = Decimal("5020.00")
    actor.on_bar(ev_overbought, runner)

    assert runner.ledger.positions["ES.FUT"].quantity == Decimal("-1.0")
