"""Execution engine abstract interface contract."""

from abc import ABC, abstractmethod

from acash.core.domain.enums import OrderStatus
from acash.core.domain.execution import Order


class IExecutionEngine(ABC):
    """Abstract interface contract for order routing and execution adapters."""

    @abstractmethod
    def submit_order(self, order: Order) -> Order:
        """Submit executable order intent."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Attempt cancellation of an existing active order."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Retrieve current lifecycle status for an order."""
        pass
