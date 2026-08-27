"""Order Book Imbalance (OBI) Baseline Strategy Actor for Backtesting Substrate (Phase 5).

Translates Phase 4 Microstructure Imbalance signals into simulated order actions.
"""

from decimal import Decimal
from typing import Any, Optional

from acash.backtest.adapter import BacktestMarketEvent
from acash.backtest.schema import OrderType


class MicrostructureImbalanceActor:
    """Strategy actor trading on order book imbalance signals."""

    def __init__(
        self,
        symbol: str,
        threshold_long: Decimal = Decimal("0.30"),
        threshold_short: Decimal = Decimal("-0.30"),
        trade_size: Decimal = Decimal("1.0"),
    ) -> None:
        self.symbol = symbol
        self.threshold_long = threshold_long
        self.threshold_short = threshold_short
        self.trade_size = trade_size
        self.order_counter: int = 0

    def on_bar(self, event: BacktestMarketEvent, runner: Any) -> None:
        """Process bar event."""
        # Optional bar logic

    def on_trade(self, event: BacktestMarketEvent, runner: Any) -> None:
        """Process trade event."""
        # Optional trade logic

    def generate_signal_and_order(self, obi_value: Decimal, runner: Any) -> Optional[str]:
        """Evaluate OBI feature value and submit orders to backtest runner."""
        pos = runner.ledger.positions.get(self.symbol)
        current_qty = pos.quantity if pos else Decimal("0.0")

        if obi_value >= self.threshold_long and current_qty <= Decimal("0.0"):
            self.order_counter += 1
            order_id = f"ORD-OBI-{self.order_counter:06d}"
            target_buy_qty = self.trade_size if current_qty == Decimal("0.0") else self.trade_size + abs(current_qty)
            runner.submit_order(
                order_id=order_id,
                symbol=self.symbol,
                order_type=OrderType.MARKET,
                side="BUY",
                quantity=target_buy_qty,
            )
            return order_id

        elif obi_value <= self.threshold_short and current_qty >= Decimal("0.0"):
            self.order_counter += 1
            order_id = f"ORD-OBI-{self.order_counter:06d}"
            target_sell_qty = self.trade_size if current_qty == Decimal("0.0") else self.trade_size + current_qty
            runner.submit_order(
                order_id=order_id,
                symbol=self.symbol,
                order_type=OrderType.MARKET,
                side="SELL",
                quantity=target_sell_qty,
            )
            return order_id

        return None
