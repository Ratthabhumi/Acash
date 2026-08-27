"""Unit tests for pure state transitions, signed position math, spot cash flows, and zero PnL double-counting."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.enums import OrderSide
from acash.core.domain.execution import Fill
from acash.core.domain.portfolio import PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.transitions import (
    apply_fill_to_portfolio,
    apply_fill_to_position,
    update_portfolio_market_prices,
)


def test_position_eight_transition_scenarios(sample_time: datetime) -> None:
    # 1. Long Open / Increase
    fill_buy_1 = Fill(
        fill_id="f1", order_id="o1", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("100.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos = apply_fill_to_position(None, fill_buy_1)
    assert pos.quantity == Decimal("1.0")
    assert pos.entry_price == Decimal("100.00")
    assert pos.realized_pnl == Decimal("0.00")

    # Long Increase: Buy 1 @ 200 -> Total 2 @ avg 150
    fill_buy_2 = Fill(
        fill_id="f2", order_id="o2", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("200.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos = apply_fill_to_position(pos, fill_buy_2)
    assert pos.quantity == Decimal("2.0")
    assert pos.entry_price == Decimal("150.00")
    assert pos.realized_pnl == Decimal("0.00")

    # 2. Long Reduce: Sell 1 @ 180 -> Remaining 1 @ entry 150, Realized PnL = 1 * (180 - 150) = +30
    fill_sell_reduce = Fill(
        fill_id="f3", order_id="o3", symbol="BTC-USD", side=OrderSide.SELL,
        fill_price=Decimal("180.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos = apply_fill_to_position(pos, fill_sell_reduce)
    assert pos.quantity == Decimal("1.0")
    assert pos.entry_price == Decimal("150.00")
    assert pos.realized_pnl == Decimal("30.00")

    # 3. Long Close: Sell 1 @ 190 -> Remaining 0, Realized PnL = 30 + 1 * (190 - 150) = +70
    fill_sell_close = Fill(
        fill_id="f4", order_id="o4", symbol="BTC-USD", side=OrderSide.SELL,
        fill_price=Decimal("190.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos = apply_fill_to_position(pos, fill_sell_close)
    assert pos.quantity == Decimal("0.0")
    assert pos.entry_price == Decimal("0.0")
    assert pos.realized_pnl == Decimal("70.00")

    # 4. Long -> Short Reversal: Buy 1 @ 100 then Sell 3 @ 110
    # Closed 1 @ 110 (+10 realized PnL), Residual -2 @ 110
    fill_open_long = Fill(
        fill_id="f5", order_id="o5", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("100.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos_long = apply_fill_to_position(None, fill_open_long)
    fill_reverse_short = Fill(
        fill_id="f6", order_id="o6", symbol="BTC-USD", side=OrderSide.SELL,
        fill_price=Decimal("110.00"), fill_quantity=Decimal("3.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos_rev_short = apply_fill_to_position(pos_long, fill_reverse_short)
    assert pos_rev_short.quantity == Decimal("-2.0")
    assert pos_rev_short.entry_price == Decimal("110.00")
    assert pos_rev_short.realized_pnl == Decimal("10.00")

    # 5. Short Increase: Sell 2 @ 100 -> Total -4 @ avg 105
    fill_short_inc = Fill(
        fill_id="f7", order_id="o7", symbol="BTC-USD", side=OrderSide.SELL,
        fill_price=Decimal("100.00"), fill_quantity=Decimal("2.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos_short = apply_fill_to_position(pos_rev_short, fill_short_inc)
    assert pos_short.quantity == Decimal("-4.0")
    assert pos_short.entry_price == Decimal("105.00")
    assert pos_short.realized_pnl == Decimal("10.00")

    # 6. Short Reduce: Buy 2 @ 95 -> Remaining -2 @ entry 105, Realized PnL = 10 + 2 * (105 - 95) = +30
    fill_short_red = Fill(
        fill_id="f8", order_id="o8", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("95.00"), fill_quantity=Decimal("2.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos_short = apply_fill_to_position(pos_short, fill_short_red)
    assert pos_short.quantity == Decimal("-2.0")
    assert pos_short.entry_price == Decimal("105.00")
    assert pos_short.realized_pnl == Decimal("30.00")

    # 7. Short Close: Buy 2 @ 90 -> Remaining 0, Realized PnL = 30 + 2 * (105 - 90) = +60
    fill_short_close = Fill(
        fill_id="f9", order_id="o9", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("90.00"), fill_quantity=Decimal("2.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos_short = apply_fill_to_position(pos_short, fill_short_close)
    assert pos_short.quantity == Decimal("0.0")
    assert pos_short.entry_price == Decimal("0.0")
    assert pos_short.realized_pnl == Decimal("60.00")

    # 8. Short -> Long Reversal: Short 1 @ 100 then Buy 3 @ 90
    # Closed 1 @ 90 (+10 realized PnL), Residual +2 @ 90
    fill_open_short = Fill(
        fill_id="f10", order_id="o10", symbol="BTC-USD", side=OrderSide.SELL,
        fill_price=Decimal("100.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos_s = apply_fill_to_position(None, fill_open_short)
    fill_reverse_long = Fill(
        fill_id="f11", order_id="o11", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("90.00"), fill_quantity=Decimal("3.0"),
        fee=Decimal("0"), slippage=Decimal("0"), correlation_id="c1", timestamp_utc=sample_time
    )
    pos_rev_long = apply_fill_to_position(pos_s, fill_reverse_long)
    assert pos_rev_long.quantity == Decimal("2.0")
    assert pos_rev_long.entry_price == Decimal("90.00")
    assert pos_rev_long.realized_pnl == Decimal("10.00")


def test_spot_portfolio_cash_flows_and_zero_pnl_double_counting(sample_time: datetime) -> None:
    # Initial empty portfolio with $1000 cash
    p0 = PortfolioState(
        timestamp_utc=sample_time,
        positions={},
        cash_balance=Decimal("1000.00"),
        total_equity=Decimal("1000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    # 1. Buy 1 @ 100 (Fee = 0)
    fill_buy = Fill(
        fill_id="fb1", order_id="ob1", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("100.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0.00"), slippage=Decimal("0.00"), correlation_id="c1", timestamp_utc=sample_time
    )
    p1 = apply_fill_to_portfolio(p0, fill_buy)
    assert p1.cash_balance == Decimal("900.00")
    assert p1.positions["BTC-USD"].quantity == Decimal("1.0")
    assert p1.positions["BTC-USD"].market_value == Decimal("100.00")
    assert p1.total_equity == Decimal("1000.00")  # 900 + 100
    assert p1.realized_pnl == Decimal("0.00")

    # 2. Sell 1 @ 110 (Fee = 0)
    fill_sell = Fill(
        fill_id="fs1", order_id="os1", symbol="BTC-USD", side=OrderSide.SELL,
        fill_price=Decimal("110.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0.00"), slippage=Decimal("0.00"), correlation_id="c1", timestamp_utc=sample_time
    )
    p2 = apply_fill_to_portfolio(p1, fill_sell)
    assert p2.cash_balance == Decimal("1010.00")  # 900 + 110
    assert p2.positions["BTC-USD"].quantity == Decimal("0.0")
    assert p2.positions["BTC-USD"].market_value == Decimal("0.00")
    assert p2.total_equity == Decimal("1010.00")  # 1010 + 0 (NOT 1020!)
    assert p2.realized_pnl == Decimal("10.00")    # reporting only


def test_spot_portfolio_short_cash_flows(sample_time: datetime) -> None:
    p0 = PortfolioState(
        timestamp_utc=sample_time,
        positions={},
        cash_balance=Decimal("1000.00"),
        total_equity=Decimal("1000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    # Sell 1 @ 100 -> cash +100 = 1100, position = -1 @ 100, market_value = -100
    fill_short = Fill(
        fill_id="fs1", order_id="os1", symbol="BTC-USD", side=OrderSide.SELL,
        fill_price=Decimal("100.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0.00"), slippage=Decimal("0.00"), correlation_id="c1", timestamp_utc=sample_time
    )
    p1 = apply_fill_to_portfolio(p0, fill_short)
    assert p1.cash_balance == Decimal("1100.00")
    assert p1.positions["BTC-USD"].quantity == Decimal("-1.0")
    assert p1.positions["BTC-USD"].market_value == Decimal("-100.00")
    assert p1.total_equity == Decimal("1000.00")  # 1100 + (-100) = 1000
    assert p1.gross_exposure == Decimal("100.00")
    assert p1.net_exposure == Decimal("-100.00")

    # Buy to close 1 @ 90 -> cash -90 = 1010, position = 0, equity = 1010
    fill_cover = Fill(
        fill_id="fc1", order_id="oc1", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("90.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("0.00"), slippage=Decimal("0.00"), correlation_id="c1", timestamp_utc=sample_time
    )
    p2 = apply_fill_to_portfolio(p1, fill_cover)
    assert p2.cash_balance == Decimal("1010.00")
    assert p2.positions["BTC-USD"].quantity == Decimal("0.0")
    assert p2.total_equity == Decimal("1010.00")
    assert p2.realized_pnl == Decimal("10.00")


def test_market_price_updates_and_equity_conservation(sample_time: datetime) -> None:
    p0 = PortfolioState(
        timestamp_utc=sample_time,
        positions={},
        cash_balance=Decimal("1000.00"),
        total_equity=Decimal("1000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    # Buy 2 @ 100 (cash = 800, pos = 2 * 100 = 200, equity = 1000)
    fill = Fill(
        fill_id="fb1", order_id="ob1", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("100.00"), fill_quantity=Decimal("2.0"),
        fee=Decimal("0.00"), slippage=Decimal("0.00"), correlation_id="c1", timestamp_utc=sample_time
    )
    p1 = apply_fill_to_portfolio(p0, fill)

    # Price appreciates to 120
    p2 = update_portfolio_market_prices(p1, {"BTC-USD": Decimal("120.00")}, timestamp=sample_time)
    assert p2.cash_balance == Decimal("800.00")
    assert p2.positions["BTC-USD"].current_price == Decimal("120.00")
    assert p2.positions["BTC-USD"].market_value == Decimal("240.00")
    assert p2.positions["BTC-USD"].unrealized_pnl == Decimal("40.00")
    assert p2.total_equity == Decimal("1040.00")  # 800 + 240
    assert p2.gross_exposure == Decimal("240.00")

    # Price depreciates to 80
    p3 = update_portfolio_market_prices(p2, {"BTC-USD": Decimal("80.00")}, timestamp=sample_time)
    assert p3.cash_balance == Decimal("800.00")
    assert p3.positions["BTC-USD"].current_price == Decimal("80.00")
    assert p3.positions["BTC-USD"].market_value == Decimal("160.00")
    assert p3.positions["BTC-USD"].unrealized_pnl == Decimal("-40.00")
    assert p3.total_equity == Decimal("960.00")  # 800 + 160


def test_fill_fee_deduction(sample_time: datetime) -> None:
    p0 = PortfolioState(
        timestamp_utc=sample_time,
        positions={},
        cash_balance=Decimal("1000.00"),
        total_equity=Decimal("1000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    # Buy 1 @ 100 with $5 fee -> cash = 1000 - 100 - 5 = 895, pos = 100, equity = 995
    fill = Fill(
        fill_id="fb1", order_id="ob1", symbol="BTC-USD", side=OrderSide.BUY,
        fill_price=Decimal("100.00"), fill_quantity=Decimal("1.0"),
        fee=Decimal("5.00"), slippage=Decimal("0.00"), correlation_id="c1", timestamp_utc=sample_time
    )
    p1 = apply_fill_to_portfolio(p0, fill)
    assert p1.cash_balance == Decimal("895.00")
    assert p1.total_equity == Decimal("995.00")
