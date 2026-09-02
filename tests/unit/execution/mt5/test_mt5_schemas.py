"""Unit tests for Phase 12 MT5 domain schemas, DTOs, and lineage validation."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.execution.mt5.enums import (
    MT5DealType,
    MT5FillingMode,
    MT5OrderState,
    MT5OrderTime,
    MT5OrderType,
    MT5PositionType,
    MT5TradeAction,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import MT5SymbolSpecError, MT5ValidationError
from acash.execution.mt5.schemas import (
    BrokerSymbolSpec,
    MT5AccountReality,
    MT5DealReality,
    MT5ExecutionLineage,
    MT5OrderReality,
    MT5PositionReality,
    MT5TradeRequest,
    MT5TradeResult,
)


def test_broker_symbol_spec_immutable_and_valid() -> None:
    """Verify BrokerSymbolSpec instantiation, immutability, and deterministic digest."""
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

    spec = BrokerSymbolSpec(
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

    assert spec.canonical_symbol == "EURUSD"
    assert spec.spec_digest == digest

    # Immutability check
    with pytest.raises(Exception):
        setattr(spec, "digits", 6)


def test_broker_symbol_spec_positive_bounds_enforced() -> None:
    """Verify BrokerSymbolSpec fails closed on non-positive volume or tick size."""
    digest = "a" * 64
    with pytest.raises(MT5SymbolSpecError, match="contract_size must be strictly positive"):
        BrokerSymbolSpec(
            canonical_symbol="EURUSD",
            broker_symbol="EURUSD.pro",
            contract_size=Decimal("0"),
            volume_min=Decimal("0.01"),
            volume_max=Decimal("100.00"),
            volume_step=Decimal("0.01"),
            digits=5,
            point_size=Decimal("0.00001"),
            tick_size=Decimal("0.00001"),
            trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
            spec_digest=digest,
            margin_currency="EUR",
            profit_currency="USD",
        )

    with pytest.raises(MT5SymbolSpecError, match="volume_max .* cannot be less than volume_min"):
        BrokerSymbolSpec(
            canonical_symbol="EURUSD",
            broker_symbol="EURUSD.pro",
            contract_size=Decimal("100000"),
            volume_min=Decimal("10.00"),
            volume_max=Decimal("1.00"),
            volume_step=Decimal("0.01"),
            digits=5,
            point_size=Decimal("0.00001"),
            tick_size=Decimal("0.00001"),
            trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
            spec_digest=digest,
            margin_currency="EUR",
            profit_currency="USD",
        )


def test_mt5_trade_request_strict_validation() -> None:
    """Verify MT5TradeRequest field contracts, defaults, and extra-field rejection."""
    req = MT5TradeRequest(
        action=MT5TradeAction.TRADE_ACTION_DEAL,
        magic=1001,
        symbol="EURUSD",
        volume=Decimal("1.5"),
        type=MT5OrderType.BUY,
        type_filling=MT5FillingMode.ORDER_FILLING_FOK,
    )
    assert req.action == MT5TradeAction.TRADE_ACTION_DEAL
    assert req.magic == 1001
    assert req.price == Decimal("0.0")
    assert req.type_time == MT5OrderTime.ORDER_TIME_GTC
    assert req.comment == ""

    # Extra fields forbidden
    with pytest.raises(Exception):
        MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=Decimal("1.0"),
            type=MT5OrderType.BUY,
            type_filling=MT5FillingMode.ORDER_FILLING_FOK,
            unauthorized_field="malicious",  # type: ignore[call-arg]
        )


def test_mt5_trade_result_observation_dto() -> None:
    """Verify MT5TradeResult observation DTO validation and defaults."""
    res = MT5TradeResult(
        retcode=10009,
        deal=987654,
        order=123456,
        volume=Decimal("1.5"),
        price=Decimal("1.08500"),
    )
    assert res.retcode == 10009
    assert res.deal == 987654
    assert res.order == 123456
    assert res.volume == Decimal("1.5")


def test_mt5_execution_lineage_9_tuple() -> None:
    """Verify MT5ExecutionLineage immutable 9-tuple and nullability validations."""
    lineage = MT5ExecutionLineage(
        broker_id="IC_MARKETS",
        account_id="MT5_DEMO_01",
        terminal_instance_id="TERMINAL_01",
        strategy_id="MOM_ALPHA_01",
        cycle_id="CYC_20260902_001",
        intent_id="INTENT_1001",
        mt5_order_ticket=123456,
        mt5_deal_ticket=(555111, 555112),
        position_id=777888,
    )
    assert lineage.broker_id == "IC_MARKETS"
    assert lineage.mt5_deal_ticket == (555111, 555112)

    # Empty string validation
    with pytest.raises(Exception):
        MT5ExecutionLineage(
            broker_id="",
            account_id="MT5_DEMO_01",
            terminal_instance_id="TERMINAL_01",
            strategy_id="MOM_ALPHA_01",
            cycle_id="CYC_20260902_001",
            intent_id="INTENT_1001",
        )
