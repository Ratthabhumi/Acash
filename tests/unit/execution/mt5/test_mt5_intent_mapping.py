"""Unit tests for OrderIntent to MT5TradeRequest mapping and Close-By fail-closed guard."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.execution.mt5.enums import (
    MT5ExecutionPolicy,
    MT5FillingMode,
    MT5OrderTime,
    MT5OrderType,
    MT5TradeAction,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import MT5ValidationError
from acash.execution.mt5.mapping import map_order_intent_to_trade_request
from acash.execution.mt5.schemas import BrokerSymbolSpec
from acash.execution.schema import OrderIntent, OrderSide, OrderType, TimeInForce


@pytest.fixture
def mock_symbol_spec() -> BrokerSymbolSpec:
    digest = BrokerSymbolSpec.compute_spec_digest(
        canonical_symbol="EURUSD",
        broker_symbol="EURUSD.pro",
        contract_size=Decimal("100000"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100.00"),
        volume_step=Decimal("0.01"),
        digits=5,
        point_size=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=0,
        margin_currency="EUR",
        profit_currency="USD",
    )
    return BrokerSymbolSpec(
        canonical_symbol="EURUSD",
        broker_symbol="EURUSD.pro",
        contract_size=Decimal("100000"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100.00"),
        volume_step=Decimal("0.01"),
        digits=5,
        point_size=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=0,
        margin_currency="EUR",
        profit_currency="USD",
        spec_digest=digest,
    )


def test_map_market_order_intent_preserves_values(mock_symbol_spec: BrokerSymbolSpec) -> None:
    """Verify market OrderIntent maps to TRADE_ACTION_DEAL and preserves volume exactly."""
    intent = OrderIntent(
        intent_id="INTENT_101",
        authorization_id="AUTH_999",
        strategy_id="MOM_01",
        venue="MT5",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.GTC,
        quantity=Decimal("1.25"),
        created_at=datetime.now(timezone.utc),
        signal_event_hash="0" * 64,
        risk_snapshot_hash="1" * 64,
        intent_digest="2" * 64,
    )

    req = map_order_intent_to_trade_request(
        intent=intent,
        symbol_spec=mock_symbol_spec,
        magic=777,
        comment="MOM_ALPHA_SIGNAL",
    )

    assert req.action == MT5TradeAction.TRADE_ACTION_DEAL
    assert req.type == MT5OrderType.BUY
    assert req.volume == Decimal("1.25")
    assert req.price == Decimal("0.0")
    assert req.magic == 777
    assert req.symbol == "EURUSD.pro"
    assert req.comment == "MOM_ALPHA_SIGNAL"
    assert req.type_filling == MT5FillingMode.ORDER_FILLING_FOK


def test_map_limit_order_intent_preserves_values(mock_symbol_spec: BrokerSymbolSpec) -> None:
    """Verify limit OrderIntent maps to TRADE_ACTION_PENDING and preserves price/volume."""
    intent = OrderIntent(
        intent_id="INTENT_102",
        authorization_id="AUTH_999",
        strategy_id="MOM_01",
        venue="MT5",
        symbol="EURUSD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=Decimal("0.50"),
        limit_price=Decimal("1.09550"),
        created_at=datetime.now(timezone.utc),
        signal_event_hash="0" * 64,
        risk_snapshot_hash="1" * 64,
        intent_digest="2" * 64,
    )

    req = map_order_intent_to_trade_request(
        intent=intent,
        symbol_spec=mock_symbol_spec,
        magic=777,
    )

    assert req.action == MT5TradeAction.TRADE_ACTION_PENDING
    assert req.type == MT5OrderType.SELL_LIMIT
    assert req.volume == Decimal("0.50")
    assert req.price == Decimal("1.09550")
    assert req.stoplimit is None


def test_close_by_fails_closed_in_slice_1(mock_symbol_spec: BrokerSymbolSpec) -> None:
    """Verify Close-By operations (position_by) fail closed with MT5ValidationError in Slice 1."""
    intent = OrderIntent(
        intent_id="INTENT_103",
        authorization_id="AUTH_999",
        strategy_id="MOM_01",
        venue="MT5",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.GTC,
        quantity=Decimal("1.00"),
        created_at=datetime.now(timezone.utc),
        signal_event_hash="0" * 64,
        risk_snapshot_hash="1" * 64,
        intent_digest="2" * 64,
    )

    with pytest.raises(MT5ValidationError, match="Close-By execution .* is intentionally deferred in Slice 1"):
        map_order_intent_to_trade_request(
            intent=intent,
            symbol_spec=mock_symbol_spec,
            position=111,
            position_by=222,  # Close-By deferred
        )
