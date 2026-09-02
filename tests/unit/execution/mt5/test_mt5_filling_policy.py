"""Unit tests for Phase 12 MT5 filling policy matrix and BOC validation."""

import pytest

from acash.execution.mt5.enums import (
    MT5ExecutionPolicy,
    MT5FillingMode,
    MT5OrderType,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import MT5FillingModeError
from acash.execution.mt5.mapping import select_mt5_filling_mode


def test_market_execution_filling_selection() -> None:
    """Verify market execution selects FOK or IOC and rejects RETURN/BOC."""
    # FOK available
    mode = select_mt5_filling_mode(
        execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        order_type=MT5OrderType.BUY,
        execution_policy=MT5ExecutionPolicy.DEFAULT,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
    )
    assert mode == MT5FillingMode.ORDER_FILLING_FOK

    # TAKER_SWEEP prefers IOC
    mode_taker = select_mt5_filling_mode(
        execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        order_type=MT5OrderType.SELL,
        execution_policy=MT5ExecutionPolicy.TAKER_SWEEP,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
    )
    assert mode_taker == MT5FillingMode.ORDER_FILLING_IOC


def test_market_execution_forbids_return_and_boc() -> None:
    """Verify market execution fails closed if symbol only provides RETURN or unsupported flags."""
    with pytest.raises(MT5FillingModeError, match="Symbol does not support SYMBOL_FILLING_FOK or SYMBOL_FILLING_IOC"):
        select_mt5_filling_mode(
            execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
            order_type=MT5OrderType.BUY,
            execution_policy=MT5ExecutionPolicy.DEFAULT,
            allowed_filling_flags=(),
        )

    # Market orders with PASSIVE_MAKER are strictly forbidden
    with pytest.raises(MT5FillingModeError, match="PASSIVE_MAKER policy cannot be applied to market orders"):
        select_mt5_filling_mode(
            execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
            order_type=MT5OrderType.BUY,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            allowed_filling_flags=("SYMBOL_FILLING_FOK",),
        )


def test_pending_orders_default_to_return() -> None:
    """Verify pending orders default to ORDER_FILLING_RETURN."""
    mode = select_mt5_filling_mode(
        execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE,
        order_type=MT5OrderType.BUY_LIMIT,
        execution_policy=MT5ExecutionPolicy.DEFAULT,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
    )
    assert mode == MT5FillingMode.ORDER_FILLING_RETURN


def test_boc_passive_maker_matrix() -> None:
    """Verify BOC requires PASSIVE_MAKER, Limit/Stop-Limit type, Exchange mode, and BOC flag."""
    # Valid BOC path
    mode = select_mt5_filling_mode(
        execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE,
        order_type=MT5OrderType.BUY_LIMIT,
        execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
        allowed_filling_flags=("SYMBOL_FILLING_BOC", "SYMBOL_FILLING_FOK"),
    )
    assert mode == MT5FillingMode.ORDER_FILLING_BOC

    # Invalid: BOC with non-Exchange execution mode
    with pytest.raises(MT5FillingModeError, match="PASSIVE_MAKER BOC filling requires Exchange execution mode"):
        select_mt5_filling_mode(
            execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_INSTANT,
            order_type=MT5OrderType.BUY_LIMIT,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            allowed_filling_flags=("SYMBOL_FILLING_BOC",),
        )

    # Invalid: BOC with market order (BUY)
    with pytest.raises(MT5FillingModeError, match="PASSIVE_MAKER policy cannot be applied to market orders"):
        select_mt5_filling_mode(
            execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE,
            order_type=MT5OrderType.BUY,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            allowed_filling_flags=("SYMBOL_FILLING_BOC",),
        )

    # Invalid: BOC without SYMBOL_FILLING_BOC flag
    with pytest.raises(MT5FillingModeError, match="Symbol does not support SYMBOL_FILLING_BOC capability"):
        select_mt5_filling_mode(
            execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE,
            order_type=MT5OrderType.BUY_LIMIT,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            allowed_filling_flags=("SYMBOL_FILLING_FOK",),
        )
