"""Unit tests for Phase 12 MT5 enumeration models and MQL5 retcodes."""

import pytest

from acash.execution.mt5.enums import (
    MT5DealEntry,
    MT5DealType,
    MT5ExecutionPolicy,
    MT5FillingMode,
    MT5OrderState,
    MT5OrderTime,
    MT5OrderType,
    MT5PositionType,
    MT5Retcode,
    MT5TradeAction,
    MT5TradeExecutionMode,
)


def test_mt5_order_type_vocabulary() -> None:
    """Verify MT5OrderType contains all 9 canonical MQL5 values including CLOSE_BY."""
    expected = {
        "BUY",
        "SELL",
        "BUY_LIMIT",
        "SELL_LIMIT",
        "BUY_STOP",
        "SELL_STOP",
        "BUY_STOP_LIMIT",
        "SELL_STOP_LIMIT",
        "CLOSE_BY",
    }
    actual = {e.value for e in MT5OrderType}
    assert actual == expected
    assert len(MT5OrderType) == 9


def test_mt5_filling_mode_vocabulary() -> None:
    """Verify MT5FillingMode contains the 4 canonical MQL5 filling modes."""
    expected = {
        "ORDER_FILLING_FOK",
        "ORDER_FILLING_IOC",
        "ORDER_FILLING_RETURN",
        "ORDER_FILLING_BOC",
    }
    actual = {e.value for e in MT5FillingMode}
    assert actual == expected
    assert len(MT5FillingMode) == 4


def test_mt5_execution_policy_vocabulary() -> None:
    """Verify MT5ExecutionPolicy contains ACASH intent execution policies."""
    expected = {"DEFAULT", "TAKER_SWEEP", "PASSIVE_MAKER"}
    actual = {e.value for e in MT5ExecutionPolicy}
    assert actual == expected


def test_mt5_trade_action_vocabulary() -> None:
    """Verify MT5TradeAction contains all 6 MQL5 trade actions."""
    expected = {
        "TRADE_ACTION_DEAL",
        "TRADE_ACTION_PENDING",
        "TRADE_ACTION_SLTP",
        "TRADE_ACTION_MODIFY",
        "TRADE_ACTION_REMOVE",
        "TRADE_ACTION_CLOSE_BY",
    }
    actual = {e.value for e in MT5TradeAction}
    assert actual == expected
    assert len(MT5TradeAction) == 6


def test_mt5_retcodes_exact_mql5_mapping() -> None:
    """Verify exact numerical integer mappings for all supported MQL5 trade server retcodes."""
    expected_retcodes = {
        MT5Retcode.TRADE_RETCODE_REQUOTE: 10004,
        MT5Retcode.TRADE_RETCODE_REJECT: 10006,
        MT5Retcode.TRADE_RETCODE_CANCEL: 10007,
        MT5Retcode.TRADE_RETCODE_PLACED: 10008,
        MT5Retcode.TRADE_RETCODE_DONE: 10009,
        MT5Retcode.TRADE_RETCODE_DONE_PARTIAL: 10010,
        MT5Retcode.TRADE_RETCODE_ERROR: 10011,
        MT5Retcode.TRADE_RETCODE_TIMEOUT: 10012,
        MT5Retcode.TRADE_RETCODE_INVALID: 10013,
        MT5Retcode.TRADE_RETCODE_INVALID_VOLUME: 10014,
        MT5Retcode.TRADE_RETCODE_INVALID_PRICE: 10015,
        MT5Retcode.TRADE_RETCODE_INVALID_STOPS: 10016,
        MT5Retcode.TRADE_RETCODE_TRADE_DISABLED: 10017,
        MT5Retcode.TRADE_RETCODE_MARKET_CLOSED: 10018,
        MT5Retcode.TRADE_RETCODE_NO_MONEY: 10019,
        MT5Retcode.TRADE_RETCODE_PRICE_CHANGED: 10020,
        MT5Retcode.TRADE_RETCODE_PRICE_OFF: 10021,
        MT5Retcode.TRADE_RETCODE_INVALID_EXPIRATION: 10022,
        MT5Retcode.TRADE_RETCODE_ORDER_CHANGED: 10023,
        MT5Retcode.TRADE_RETCODE_TOO_MANY_REQUESTS: 10024,
        MT5Retcode.TRADE_RETCODE_NO_CHANGES: 10025,
        MT5Retcode.TRADE_RETCODE_SERVER_DISABLES_AT: 10026,
        MT5Retcode.TRADE_RETCODE_CLIENT_DISABLES_AT: 10027,
        MT5Retcode.TRADE_RETCODE_LOCKED: 10028,
        MT5Retcode.TRADE_RETCODE_FROZEN: 10029,
        MT5Retcode.TRADE_RETCODE_INVALID_FILL: 10030,
        MT5Retcode.TRADE_RETCODE_CONNECTION: 10031,
        MT5Retcode.TRADE_RETCODE_ONLY_REAL: 10032,
        MT5Retcode.TRADE_RETCODE_LIMIT_ORDERS: 10033,
        MT5Retcode.TRADE_RETCODE_LIMIT_VOLUME: 10034,
        MT5Retcode.TRADE_RETCODE_INVALID_ORDER: 10035,
        MT5Retcode.TRADE_RETCODE_POSITION_CLOSED: 10036,
        MT5Retcode.TRADE_RETCODE_INVALID_CLOSE_VOLUME: 10038,
        MT5Retcode.TRADE_RETCODE_CLOSE_ORDER_EXIST: 10039,
        MT5Retcode.TRADE_RETCODE_LIMIT_POSITIONS: 10040,
        MT5Retcode.TRADE_RETCODE_REJECT_CANCEL: 10041,
        MT5Retcode.TRADE_RETCODE_LONG_ONLY: 10042,
        MT5Retcode.TRADE_RETCODE_SHORT_ONLY: 10043,
        MT5Retcode.TRADE_RETCODE_CLOSE_ONLY: 10044,
        MT5Retcode.TRADE_RETCODE_FIFO_CLOSE: 10045,
        MT5Retcode.TRADE_RETCODE_HEDGE_PROHIBITED: 10046,
    }

    for enum_member, expected_int in expected_retcodes.items():
        assert enum_member.value == expected_int

    assert len(MT5Retcode) == 41

    # Assert gaps exist as per official MQL5 technical specification
    all_values = {e.value for e in MT5Retcode}
    assert 10005 not in all_values
    assert 10037 not in all_values
