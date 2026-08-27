"""Pure state transition functions for Positions and PortfolioState."""

from datetime import datetime
from decimal import Decimal
from typing import Mapping, Optional

from acash.core.domain.enums import OrderSide
from acash.core.domain.execution import Fill
from acash.core.domain.portfolio import PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.types import ensure_finite_decimal


def apply_fill_to_position(current_position: Optional[Position], fill: Fill) -> Position:
    """Pure state transition function applying a trade Fill to a Position.
    
    Implements 8 signed quantity transition scenarios:
    1. Long Increase
    2. Long Reduce
    3. Long Close
    4. Long -> Short Reversal
    5. Short Increase
    6. Short Reduce
    7. Short Close
    8. Short -> Long Reversal
    """
    symbol = fill.symbol
    fill_qty = fill.fill_quantity
    fill_price = fill.fill_price
    timestamp = fill.timestamp_utc

    if current_position is None or current_position.is_flat:
        old_realized = current_position.realized_pnl if current_position is not None else Decimal("0")
        if fill.side == OrderSide.BUY:
            return Position(
                symbol=symbol,
                quantity=fill_qty,
                entry_price=fill_price,
                current_price=fill_price,
                unrealized_pnl=Decimal("0"),
                realized_pnl=old_realized,
                timestamp_utc=timestamp,
            )
        else:
            return Position(
                symbol=symbol,
                quantity=-fill_qty,
                entry_price=fill_price,
                current_price=fill_price,
                unrealized_pnl=Decimal("0"),
                realized_pnl=old_realized,
                timestamp_utc=timestamp,
            )

    old_qty = current_position.quantity
    old_entry = current_position.entry_price
    old_realized = current_position.realized_pnl

    if current_position.is_long:
        if fill.side == OrderSide.BUY:
            # 1. Long Increase
            new_qty = old_qty + fill_qty
            new_entry = ((old_qty * old_entry) + (fill_qty * fill_price)) / new_qty
            unrealized = new_qty * (fill_price - new_entry)
            return Position(
                symbol=symbol,
                quantity=new_qty,
                entry_price=new_entry,
                current_price=fill_price,
                unrealized_pnl=unrealized,
                realized_pnl=old_realized,
                timestamp_utc=timestamp,
            )
        else:
            # fill.side == OrderSide.SELL
            if fill_qty < old_qty:
                # 2. Long Reduce
                new_qty = old_qty - fill_qty
                realized_delta = fill_qty * (fill_price - old_entry)
                new_realized = old_realized + realized_delta
                unrealized = new_qty * (fill_price - old_entry)
                return Position(
                    symbol=symbol,
                    quantity=new_qty,
                    entry_price=old_entry,
                    current_price=fill_price,
                    unrealized_pnl=unrealized,
                    realized_pnl=new_realized,
                    timestamp_utc=timestamp,
                )
            elif fill_qty == old_qty:
                # 3. Long Close
                realized_delta = fill_qty * (fill_price - old_entry)
                new_realized = old_realized + realized_delta
                return Position(
                    symbol=symbol,
                    quantity=Decimal("0"),
                    entry_price=Decimal("0"),
                    current_price=fill_price,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=new_realized,
                    timestamp_utc=timestamp,
                )
            else:
                # 4. Long -> Short Reversal (fill_qty > old_qty)
                closed_qty = old_qty
                residual_qty = fill_qty - old_qty
                realized_delta = closed_qty * (fill_price - old_entry)
                new_realized = old_realized + realized_delta
                return Position(
                    symbol=symbol,
                    quantity=-residual_qty,
                    entry_price=fill_price,
                    current_price=fill_price,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=new_realized,
                    timestamp_utc=timestamp,
                )
    else:
        # current_position.is_short (old_qty < 0)
        abs_old_qty = abs(old_qty)
        if fill.side == OrderSide.SELL:
            # 5. Short Increase
            new_abs_qty = abs_old_qty + fill_qty
            new_qty = -new_abs_qty
            new_entry = ((abs_old_qty * old_entry) + (fill_qty * fill_price)) / new_abs_qty
            unrealized = new_qty * (fill_price - new_entry)
            return Position(
                symbol=symbol,
                quantity=new_qty,
                entry_price=new_entry,
                current_price=fill_price,
                unrealized_pnl=unrealized,
                realized_pnl=old_realized,
                timestamp_utc=timestamp,
            )
        else:
            # fill.side == OrderSide.BUY
            if fill_qty < abs_old_qty:
                # 6. Short Reduce
                new_abs_qty = abs_old_qty - fill_qty
                new_qty = -new_abs_qty
                realized_delta = fill_qty * (old_entry - fill_price)
                new_realized = old_realized + realized_delta
                unrealized = new_qty * (fill_price - old_entry)
                return Position(
                    symbol=symbol,
                    quantity=new_qty,
                    entry_price=old_entry,
                    current_price=fill_price,
                    unrealized_pnl=unrealized,
                    realized_pnl=new_realized,
                    timestamp_utc=timestamp,
                )
            elif fill_qty == abs_old_qty:
                # 7. Short Close
                realized_delta = fill_qty * (old_entry - fill_price)
                new_realized = old_realized + realized_delta
                return Position(
                    symbol=symbol,
                    quantity=Decimal("0"),
                    entry_price=Decimal("0"),
                    current_price=fill_price,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=new_realized,
                    timestamp_utc=timestamp,
                )
            else:
                # 8. Short -> Long Reversal (fill_qty > abs_old_qty)
                closed_qty = abs_old_qty
                residual_qty = fill_qty - abs_old_qty
                realized_delta = closed_qty * (old_entry - fill_price)
                new_realized = old_realized + realized_delta
                return Position(
                    symbol=symbol,
                    quantity=residual_qty,
                    entry_price=fill_price,
                    current_price=fill_price,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=new_realized,
                    timestamp_utc=timestamp,
                )


def apply_fill_to_portfolio(portfolio: PortfolioState, fill: Fill) -> PortfolioState:
    """Pure state transition function applying a trade Fill to a PortfolioState.
    
    Cash Flow Invariants (Spot-like model):
    - BUY: cash decreases by (fill_price * fill_qty) + fee
    - SELL: cash increases by (fill_price * fill_qty) - fee
    - Realized PnL is naturally embedded in cash balance through these cash flows and is NOT added again.
    """
    # 1. Calculate trade cash flow
    trade_value = fill.fill_price * fill.fill_quantity
    if fill.side == OrderSide.BUY:
        cash_delta = -trade_value - fill.fee
    else:
        cash_delta = trade_value - fill.fee

    new_cash_balance = portfolio.cash_balance + cash_delta

    # 2. Update Position
    current_pos = portfolio.positions.get(fill.symbol)
    new_pos = apply_fill_to_position(current_pos, fill)

    # 3. Construct updated positions map
    new_positions = dict(portfolio.positions)
    new_positions[fill.symbol] = new_pos

    # 4. Recalculate portfolio metrics
    calc_market_val_sum = Decimal("0")
    calc_gross_exposure = Decimal("0")
    calc_unrealized_pnl = Decimal("0")
    calc_realized_pnl = Decimal("0")

    for pos in new_positions.values():
        mv = pos.market_value
        calc_market_val_sum += mv
        calc_gross_exposure += abs(mv)
        calc_unrealized_pnl += pos.unrealized_pnl
        calc_realized_pnl += pos.realized_pnl

    new_total_equity = new_cash_balance + calc_market_val_sum

    return PortfolioState(
        timestamp_utc=fill.timestamp_utc,
        positions=new_positions,
        cash_balance=new_cash_balance,
        total_equity=new_total_equity,
        margin_used=portfolio.margin_used,
        gross_exposure=calc_gross_exposure,
        net_exposure=calc_market_val_sum,
        unrealized_pnl=calc_unrealized_pnl,
        realized_pnl=calc_realized_pnl,
    )


def update_portfolio_market_prices(
    portfolio: PortfolioState,
    prices: Mapping[str, Decimal],
    timestamp: datetime
) -> PortfolioState:
    """Pure state transition updating current prices across active positions and recalculating portfolio valuation."""
    new_positions: dict[str, Position] = {}
    calc_market_val_sum = Decimal("0")
    calc_gross_exposure = Decimal("0")
    calc_unrealized_pnl = Decimal("0")
    calc_realized_pnl = Decimal("0")

    for symbol, pos in portfolio.positions.items():
        if symbol in prices and not pos.is_flat:
            new_price = ensure_finite_decimal(prices[symbol], field_name=f"prices[{symbol}]")
            unrealized = pos.quantity * (new_price - pos.entry_price)
            updated_pos = Position(
                symbol=pos.symbol,
                quantity=pos.quantity,
                entry_price=pos.entry_price,
                current_price=new_price,
                unrealized_pnl=unrealized,
                realized_pnl=pos.realized_pnl,
                timestamp_utc=timestamp,
            )
        else:
            updated_pos = pos

        new_positions[symbol] = updated_pos
        mv = updated_pos.market_value
        calc_market_val_sum += mv
        calc_gross_exposure += abs(mv)
        calc_unrealized_pnl += updated_pos.unrealized_pnl
        calc_realized_pnl += updated_pos.realized_pnl

    new_total_equity = portfolio.cash_balance + calc_market_val_sum

    return PortfolioState(
        timestamp_utc=timestamp,
        positions=new_positions,
        cash_balance=portfolio.cash_balance,
        total_equity=new_total_equity,
        margin_used=portfolio.margin_used,
        gross_exposure=calc_gross_exposure,
        net_exposure=calc_market_val_sum,
        unrealized_pnl=calc_unrealized_pnl,
        realized_pnl=calc_realized_pnl,
    )
