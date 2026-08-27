"""Unit tests for in-memory mock adapters and deterministic execution."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.enums import BarTimeframe, OrderSide, OrderStatus, OrderType
from acash.core.domain.execution import Order
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.data.mock import MockMarketDataProvider
from acash.execution.mock import MockExecutionEngine


def test_mock_execution_engine_workflow(sample_order: Order, sample_time: datetime) -> None:
    engine = MockExecutionEngine(default_fee_rate=Decimal("0.001"))

    # 1. Submit Order
    submitted = engine.submit_order(sample_order)
    assert submitted.status == OrderStatus.SUBMITTED
    assert engine.get_order_status(sample_order.order_id) == OrderStatus.SUBMITTED

    # 2. Execute Fill
    filled_order, fill = engine.execute_fill(
        order_id=sample_order.order_id,
        fill_price=Decimal("50010.00"),
        timestamp_utc=sample_time,
    )
    assert filled_order.status == OrderStatus.FILLED
    assert engine.get_order_status(sample_order.order_id) == OrderStatus.FILLED
    assert fill.fill_price == Decimal("50010.00")
    assert fill.fill_quantity == Decimal("0.5")
    # Slippage = |50010 - 50000| = 10.00 price units
    assert fill.slippage == Decimal("10.00")
    # Fee = 50010 * 0.5 * 0.001 = 25.005
    assert fill.fee == Decimal("25.0050")


def test_mock_execution_cancellation(sample_order: Order) -> None:
    engine = MockExecutionEngine()
    engine.submit_order(sample_order)

    # Cancel order
    cancelled = engine.cancel_order(sample_order.order_id)
    assert cancelled is True
    assert engine.get_order_status(sample_order.order_id) == OrderStatus.CANCELLED

    # Cannot cancel already cancelled
    assert engine.cancel_order(sample_order.order_id) is False


def test_mock_market_data_provider(sample_bar: Bar, sample_snapshot: MarketDataSnapshot, sample_time: datetime) -> None:
    provider = MockMarketDataProvider()

    # Add synthetic bars
    provider.add_bars("BTC-USD", [sample_bar])

    bars = provider.get_historical_bars(
        symbol="BTC-USD",
        timeframe=BarTimeframe.M1,
        start_utc=sample_time,
        end_utc=sample_time,
    )
    assert len(bars) == 1
    assert bars[0].symbol == "BTC-USD"

    # Set and retrieve snapshot
    provider.set_snapshot(sample_snapshot)
    latest = provider.get_latest_snapshot("BTC-USD")
    assert latest.last_price == Decimal("50200.00")

    # Missing symbol raises KeyError
    with pytest.raises(KeyError):
        provider.get_latest_snapshot("ETH-USD")
