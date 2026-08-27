"""In-memory mock execution engine adapter for Phase 1 testing."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from acash.core.domain.enums import OrderStatus
from acash.core.domain.execution import Fill, Order
from acash.core.interfaces.execution import IExecutionEngine


class MockExecutionEngine(IExecutionEngine):
    """Deterministic in-memory order executor for unit testing."""

    def __init__(self, default_fee_rate: Decimal = Decimal("0.0001")) -> None:
        self._orders: dict[str, Order] = {}
        self._fills: dict[str, Fill] = {}
        self._default_fee_rate = default_fee_rate

    def submit_order(self, order: Order) -> Order:
        """Submit an order into in-memory storage with SUBMITTED status."""
        submitted_order = Order(
            order_id=order.order_id,
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price_limit=order.price_limit,
            status=OrderStatus.SUBMITTED,
            idempotency_key=order.idempotency_key,
            correlation_id=order.correlation_id,
            created_at_utc=order.created_at_utc,
        )
        self._orders[order.order_id] = submitted_order
        return submitted_order

    def execute_fill(
        self,
        order_id: str,
        fill_price: Decimal,
        timestamp_utc: Optional[datetime] = None,
        custom_fee: Optional[Decimal] = None
    ) -> tuple[Order, Fill]:
        """Execute a deterministic fill against a submitted order."""
        if order_id not in self._orders:
            raise KeyError(f"Order {order_id} not found in mock execution engine.")

        order = self._orders[order_id]
        if order.status not in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            raise ValueError(f"Cannot fill order in status: {order.status}")

        # Calculate slippage in price units (absolute difference)
        if order.price_limit is not None:
            slippage = abs(fill_price - order.price_limit)
        else:
            slippage = Decimal("0")

        # Calculate fee
        if custom_fee is not None:
            fee = custom_fee
        else:
            fee = fill_price * order.quantity * self._default_fee_rate

        fill_time = timestamp_utc if timestamp_utc is not None else order.created_at_utc

        fill = Fill(
            fill_id=f"fill_{uuid.uuid4().hex[:8]}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            fill_price=fill_price,
            fill_quantity=order.quantity,
            fee=fee,
            slippage=slippage,
            correlation_id=order.correlation_id,
            timestamp_utc=fill_time,
        )

        filled_order = Order(
            order_id=order.order_id,
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price_limit=order.price_limit,
            status=OrderStatus.FILLED,
            idempotency_key=order.idempotency_key,
            correlation_id=order.correlation_id,
            created_at_utc=order.created_at_utc,
        )

        self._orders[order_id] = filled_order
        self._fills[fill.fill_id] = fill

        return filled_order, fill

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order if pending or submitted."""
        if order_id not in self._orders:
            return False

        order = self._orders[order_id]
        if order.status in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            cancelled_order = Order(
                order_id=order.order_id,
                symbol=order.symbol,
                order_type=order.order_type,
                side=order.side,
                quantity=order.quantity,
                price_limit=order.price_limit,
                status=OrderStatus.CANCELLED,
                idempotency_key=order.idempotency_key,
                correlation_id=order.correlation_id,
                created_at_utc=order.created_at_utc,
            )
            self._orders[order_id] = cancelled_order
            return True
        return False

    def get_order_status(self, order_id: str) -> OrderStatus:
        """Get the current lifecycle status for an order."""
        if order_id not in self._orders:
            raise KeyError(f"Order {order_id} not found.")
        return self._orders[order_id].status
