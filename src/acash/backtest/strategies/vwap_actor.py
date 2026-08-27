"""Session VWAP Mean Reversion Strategy Actor for Backtesting Substrate (Phase 5).

Trades mean reversion when price deviates significantly from session volume-weighted average price.
"""

from decimal import Decimal
from typing import Any, Optional

from acash.backtest.adapter import BacktestMarketEvent
from acash.backtest.schema import OrderType


class VwapMeanReversionActor:
    """Strategy actor trading mean reversion relative to session VWAP."""

    def __init__(
        self,
        symbol: str,
        deviation_threshold_bps: Decimal = Decimal("15.0"),
        trade_size: Decimal = Decimal("1.0"),
    ) -> None:
        self.symbol = symbol
        self.deviation_threshold_bps = deviation_threshold_bps
        self.trade_size = trade_size
        self.order_counter: int = 0

    def on_bar(self, event: BacktestMarketEvent, runner: Any) -> None:
        """Evaluate bar close price against session VWAP if provided in payload."""
        price = event.payload.get("close")
        vwap = event.payload.get("vwap")
        if price is None or vwap is None or vwap == Decimal("0.0"):
            return

        diff_bps = ((price - vwap) / vwap) * Decimal("10000.0")

        pos = runner.ledger.positions.get(self.symbol)
        current_qty = pos.quantity if pos else Decimal("0.0")

        # Overbought relative to VWAP -> Sell/Short
        if diff_bps >= self.deviation_threshold_bps and current_qty >= Decimal("0.0"):
            self.order_counter += 1
            order_id = f"ORD-VWAP-{self.order_counter:06d}"
            target_sell_qty = self.trade_size if current_qty == Decimal("0.0") else self.trade_size + current_qty
            runner.submit_order(
                order_id=order_id,
                symbol=self.symbol,
                order_type=OrderType.MARKET,
                side="SELL",
                quantity=target_sell_qty,
            )

        # Oversold relative to VWAP -> Buy/Long
        elif diff_bps <= -self.deviation_threshold_bps and current_qty <= Decimal("0.0"):
            self.order_counter += 1
            order_id = f"ORD-VWAP-{self.order_counter:06d}"
            target_buy_qty = self.trade_size if current_qty == Decimal("0.0") else self.trade_size + abs(current_qty)
            runner.submit_order(
                order_id=order_id,
                symbol=self.symbol,
                order_type=OrderType.MARKET,
                side="BUY",
                quantity=target_buy_qty,
            )

    def on_trade(self, event: BacktestMarketEvent, runner: Any) -> None:
        """Optional trade event handling."""
