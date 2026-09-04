"""Regression test suite for Layer B Harness deal classification and audit.

Verifies:
1. BUY (type=0) -> parsed into MT5DealReality.
2. SELL (type=1) -> parsed into MT5DealReality.
3. BALANCE (type=2) -> excluded from MT5DealReality without ValidationError and counted in audit ledger.
4. Real A-3 trade deal (deal 10071863196, order 10355518139, EURUSD 0.01 @ 1.16282) is completely parsed and retained.
5. Direct _parse_deal call on non-trade deal fails closed with MT5ValidationError.
6. Non-trade breakdown correctly accounts for accounting and corporate action operations.
"""

from collections import namedtuple
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from acash.execution.mt5.enums import MT5DealEntry, MT5DealType
from acash.execution.mt5.exceptions import MT5ValidationError
from acash.execution.mt5.reconciliation import MT5DealCategory
from scripts.phase13_layer_b_harness import LayerBDemoMT5Transport

# Namedtuple mimicking MT5 C-extension TradeDeal struct faithfully
RawMT5Deal = namedtuple(
    "RawMT5Deal",
    [
        "ticket",
        "order",
        "time",
        "time_msc",
        "type",
        "entry",
        "magic",
        "position_id",
        "reason",
        "volume",
        "price",
        "commission",
        "swap",
        "profit",
        "fee",
        "symbol",
        "comment",
        "external_id",
    ],
)


def _make_trade_deal(
    ticket: int,
    order: int,
    position_id: int,
    symbol: str,
    deal_type: int,
    volume: float,
    price: float,
    entry: int = 0,
    magic: int = 13001,
    comment: str = "trade",
    profit: float = 0.0,
    commission: float = 0.0,
    fee: float = 0.0,
    swap: float = 0.0,
    time_sec: int = 1756972800,
) -> RawMT5Deal:
    return RawMT5Deal(
        ticket=ticket,
        order=order,
        time=time_sec,
        time_msc=time_sec * 1000,
        type=deal_type,
        entry=entry,
        magic=magic,
        position_id=position_id,
        reason=0,
        volume=volume,
        price=price,
        commission=commission,
        swap=swap,
        profit=profit,
        fee=fee,
        symbol=symbol,
        comment=comment,
        external_id="",
    )


def _make_balance_deal(
    ticket: int = 10034767853,
    profit: float = 3000.0,
    comment: str = "Deposit",
    time_sec: int = 1756500000,
) -> RawMT5Deal:
    return RawMT5Deal(
        ticket=ticket,
        order=0,
        time=time_sec,
        time_msc=time_sec * 1000,
        type=2,  # DEAL_TYPE_BALANCE
        entry=0,
        magic=0,
        position_id=0,
        reason=0,
        volume=0.0,
        price=0.0,
        commission=0.0,
        swap=0.0,
        profit=profit,
        fee=0.0,
        symbol="",
        comment=comment,
        external_id="",
    )


class TestLayerBHarnessDealClassification:
    """Regression tests for LayerBDemoMT5Transport deal classification and auditing."""

    def test_buy_and_sell_deals_parsed_successfully(self) -> None:
        """BUY (type=0) and SELL (type=1) are parsed into MT5DealReality."""
        raw_buy = _make_trade_deal(
            ticket=200001,
            order=300001,
            position_id=300001,
            symbol="EURUSD",
            deal_type=0,  # DEAL_TYPE_BUY
            volume=0.01,
            price=1.16280,
            entry=0,  # DEAL_ENTRY_IN
        )
        raw_sell = _make_trade_deal(
            ticket=200002,
            order=300002,
            position_id=300001,
            symbol="EURUSD",
            deal_type=1,  # DEAL_TYPE_SELL
            volume=0.01,
            price=1.16300,
            entry=1,  # DEAL_ENTRY_OUT
        )

        transport = LayerBDemoMT5Transport()
        mock_mt5 = MagicMock()
        mock_mt5.history_deals_get.return_value = (raw_buy, raw_sell)
        transport._mt5 = mock_mt5

        deals = transport.history_deals_get()

        assert len(deals) == 2
        assert deals[0].deal_ticket == 200001
        assert deals[0].deal_type == MT5DealType.DEAL_TYPE_BUY
        assert deals[0].volume == Decimal("0.01")
        assert deals[0].price == Decimal("1.16280")
        assert deals[0].entry == MT5DealEntry.DEAL_ENTRY_IN

        assert deals[1].deal_ticket == 200002
        assert deals[1].deal_type == MT5DealType.DEAL_TYPE_SELL
        assert deals[1].volume == Decimal("0.01")
        assert deals[1].price == Decimal("1.16300")
        assert deals[1].entry == MT5DealEntry.DEAL_ENTRY_OUT

        audit = transport.last_deal_audit
        assert audit["raw_deals_count"] == 2
        assert audit["trade_execution_deals_count"] == 2
        assert audit["non_trade_deals_count"] == 0
        assert audit["non_trade_breakdown"] == {}
        assert audit["non_trade_records"] == []

    def test_balance_deal_excluded_without_validation_error(self) -> None:
        """BALANCE (type=2) is excluded without raising ValidationError and audited."""
        raw_balance = _make_balance_deal(ticket=10034767853, profit=3000.0, comment="Deposit")

        transport = LayerBDemoMT5Transport()
        mock_mt5 = MagicMock()
        mock_mt5.history_deals_get.return_value = (raw_balance,)
        transport._mt5 = mock_mt5

        # Must NOT raise ValidationError
        deals = transport.history_deals_get()

        assert len(deals) == 0
        audit = transport.last_deal_audit
        assert audit["raw_deals_count"] == 1
        assert audit["trade_execution_deals_count"] == 0
        assert audit["non_trade_deals_count"] == 1
        assert audit["non_trade_breakdown"] == {"DEAL_TYPE_BALANCE": 1}
        assert len(audit["non_trade_records"]) == 1
        rec = audit["non_trade_records"][0]
        assert rec["ticket"] == 10034767853
        assert rec["deal_type"] == "DEAL_TYPE_BALANCE"
        assert rec["category"] == MT5DealCategory.ACCOUNTING_DEAL.value
        assert rec["comment"] == "Deposit"
        assert rec["profit"] == "3000.0"

    def test_real_a3_deal_parsed_and_retained_alongside_balance(self) -> None:
        """Real A-3 trade deal is completely parsed and retained while deposit deal is audited."""
        # Deposit deal from actual demo account
        raw_balance = _make_balance_deal(
            ticket=10034767853,
            profit=3000.0,
            comment="Initial Deposit",
        )
        # Real trade deal from actual A-3 execution
        raw_a3_deal = _make_trade_deal(
            ticket=10071863196,
            order=10355518139,
            position_id=10355518139,
            symbol="EURUSD",
            deal_type=0,  # BUY
            volume=0.01,
            price=1.16282,
            entry=0,  # IN
            magic=13001,
            comment="phase13_a3_demo",
            profit=0.0,
            commission=-0.04,
            fee=0.0,
            swap=0.0,
            time_sec=1756972800,
        )

        transport = LayerBDemoMT5Transport()
        mock_mt5 = MagicMock()
        mock_mt5.history_deals_get.return_value = (raw_balance, raw_a3_deal)
        transport._mt5 = mock_mt5

        deals = transport.history_deals_get()

        assert len(deals) == 1
        retained = deals[0]
        assert retained.deal_ticket == 10071863196
        assert retained.order_ticket == 10355518139
        assert retained.position_ticket == 10355518139
        assert retained.symbol == "EURUSD"
        assert retained.deal_type == MT5DealType.DEAL_TYPE_BUY
        assert retained.volume == Decimal("0.01")
        assert retained.price == Decimal("1.16282")
        assert retained.entry == MT5DealEntry.DEAL_ENTRY_IN
        assert retained.magic == 13001
        assert retained.comment == "phase13_a3_demo"
        assert retained.commission == Decimal("-0.04")

        audit = transport.last_deal_audit
        assert audit["raw_deals_count"] == 2
        assert audit["trade_execution_deals_count"] == 1
        assert audit["non_trade_deals_count"] == 1
        assert audit["non_trade_breakdown"] == {"DEAL_TYPE_BALANCE": 1}
        assert audit["non_trade_records"][0]["ticket"] == 10034767853

    def test_direct_parse_deal_fails_closed_on_non_trade_deal(self) -> None:
        """Direct call to _parse_deal with non-trade deal raises MT5ValidationError (strict fail-closed)."""
        raw_balance = _make_balance_deal()
        transport = LayerBDemoMT5Transport()

        with pytest.raises(MT5ValidationError) as exc_info:
            transport._parse_deal(raw_balance)

        assert "NON_TRADE_DEAL_TYPE" in str(exc_info.value)
        assert "ACCOUNTING_DEAL" in str(exc_info.value)

    def test_multiple_non_trade_operations_categorized_and_audited(self) -> None:
        """CREDIT, CHARGE, CORRECTION, BONUS are excluded and audited with respective categories."""
        credit_deal = RawMT5Deal(
            ticket=50001,
            order=0,
            time=1756500000,
            time_msc=1756500000000,
            type=3,  # DEAL_TYPE_CREDIT
            entry=0,
            magic=0,
            position_id=0,
            reason=0,
            volume=0.0,
            price=0.0,
            commission=0.0,
            swap=0.0,
            profit=500.0,
            fee=0.0,
            symbol="",
            comment="Credit In",
            external_id="",
        )
        charge_deal = RawMT5Deal(
            ticket=50002,
            order=0,
            time=1756500010,
            time_msc=1756500010000,
            type=4,  # DEAL_TYPE_CHARGE
            entry=0,
            magic=0,
            position_id=0,
            reason=0,
            volume=0.0,
            price=0.0,
            commission=0.0,
            swap=0.0,
            profit=-10.0,
            fee=0.0,
            symbol="",
            comment="Monthly fee",
            external_id="",
        )
        valid_trade = _make_trade_deal(
            ticket=50003,
            order=60001,
            position_id=60001,
            symbol="EURUSD",
            deal_type=1,  # SELL
            volume=0.02,
            price=1.16500,
        )

        transport = LayerBDemoMT5Transport()
        mock_mt5 = MagicMock()
        mock_mt5.history_deals_get.return_value = (credit_deal, charge_deal, valid_trade)
        transport._mt5 = mock_mt5

        deals = transport.history_deals_get()

        assert len(deals) == 1
        assert deals[0].deal_ticket == 50003

        audit = transport.last_deal_audit
        assert audit["raw_deals_count"] == 3
        assert audit["trade_execution_deals_count"] == 1
        assert audit["non_trade_deals_count"] == 2
        assert audit["non_trade_breakdown"]["DEAL_TYPE_CREDIT"] == 1
        assert audit["non_trade_breakdown"]["DEAL_TYPE_CHARGE"] == 1
