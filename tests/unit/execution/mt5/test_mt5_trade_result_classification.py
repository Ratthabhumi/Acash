"""Unit tests for Phase 12 MT5 trade result observation classification."""

from decimal import Decimal
import pytest

from acash.execution.broker_events import BrokerEventKind
from acash.execution.mt5.exceptions import MT5RetcodeError
from acash.execution.mt5.mapping import classify_trade_result_observation
from acash.execution.mt5.schemas import MT5TradeResult


def test_retcode_10009_done_requires_authoritative_confirmation() -> None:
    """Verify that retcode 10009 (DONE) alone NEVER emits FILLED without confirmed deal."""
    # Case A: retcode 10009 with deal == 0
    res_no_deal = MT5TradeResult(retcode=10009, deal=0, order=123)
    event_no_deal = classify_trade_result_observation(res_no_deal, authoritative_deal_confirmed=False)
    assert event_no_deal == BrokerEventKind.ACK

    # Case B: retcode 10009 with deal > 0 but authoritative confirmation False
    res_unconfirmed = MT5TradeResult(retcode=10009, deal=999, order=123)
    event_unconfirmed = classify_trade_result_observation(res_unconfirmed, authoritative_deal_confirmed=False)
    assert event_unconfirmed == BrokerEventKind.ACK

    # Case C: retcode 10009 with deal > 0 AND authoritative confirmation True
    res_confirmed = MT5TradeResult(retcode=10009, deal=999, order=123)
    event_confirmed = classify_trade_result_observation(res_confirmed, authoritative_deal_confirmed=True)
    assert event_confirmed == BrokerEventKind.FILLED


def test_retcode_observations_placed_partial_cancel() -> None:
    """Verify classification of PLACED (10008), DONE_PARTIAL (10010), and CANCEL (10007)."""
    # 10008 PLACED -> ACK
    res_placed = MT5TradeResult(retcode=10008, order=456)
    assert classify_trade_result_observation(res_placed) == BrokerEventKind.ACK

    # 10010 DONE_PARTIAL -> PARTIAL_FILL
    res_partial = MT5TradeResult(retcode=10010, deal=789, order=456, volume=Decimal("0.5"))
    assert classify_trade_result_observation(res_partial) == BrokerEventKind.PARTIAL_FILL

    # 10007 CANCEL -> ORDER_CANCELLED
    res_cancel = MT5TradeResult(retcode=10007, order=456)
    assert classify_trade_result_observation(res_cancel) == BrokerEventKind.ORDER_CANCELLED


def test_retcode_rejections_and_requote() -> None:
    """Verify classification of requotes and official MQL5 rejection retcodes."""
    # 10004 REQUOTE -> REJECT
    res_requote = MT5TradeResult(retcode=10004)
    assert classify_trade_result_observation(res_requote) == BrokerEventKind.REJECT

    # 10006 REJECT -> REJECT
    res_reject = MT5TradeResult(retcode=10006)
    assert classify_trade_result_observation(res_reject) == BrokerEventKind.REJECT

    # 10035 INVALID_ORDER -> REJECT
    res_invalid_order = MT5TradeResult(retcode=10035)
    assert classify_trade_result_observation(res_invalid_order) == BrokerEventKind.REJECT

    # 10036 POSITION_CLOSED -> REJECT
    res_pos_closed = MT5TradeResult(retcode=10036)
    assert classify_trade_result_observation(res_pos_closed) == BrokerEventKind.REJECT

    # 10046 HEDGE_PROHIBITED -> REJECT
    res_hedge = MT5TradeResult(retcode=10046)
    assert classify_trade_result_observation(res_hedge) == BrokerEventKind.REJECT


def test_unknown_retcode_fails_closed() -> None:
    """Verify unrecognized retcode integers fail closed with MT5RetcodeError."""
    # 99999 unknown code
    res_unknown = MT5TradeResult(retcode=99999)
    with pytest.raises(MT5RetcodeError, match="Unrecognized or unsupported MT5 retcode: 99999"):
        classify_trade_result_observation(res_unknown)

    # 10005 gap code
    res_gap = MT5TradeResult(retcode=10005)
    with pytest.raises(MT5RetcodeError, match="Unrecognized or unsupported MT5 retcode: 10005"):
        classify_trade_result_observation(res_gap)
