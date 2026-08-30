"""Phase 7 Step 8D: Mock Broker — broker-side reality simulator.

The Mock Broker simulates the *exchange side* of order lifecycle. It is fully
separable from the internal shadow state machine:

- It owns ONLY broker-side order state (``MockBrokerStatus``), reflecting what
  the exchange believes about an order.
- It emits ``BrokerRawEvent`` observations (the raw events that a real broker
  adapter would surface).
- It has NO authority over order transitions and NO reference to
  ``transition_order()``. State transitions remain exclusively the
  responsibility of the state machine authority (Step 8B).

The end-to-end wiring lives in the harness/tests:

```
Order State (shadow)
   ↓ cancel request
Mock Broker (broker-side reality)
   ↓ raw event
normalize_broker_event()  ->  ExecutionEvent + evidence
   ↓
transition_order()        ->  (ONLY state authority)
   ↓
New State
```

The ``cancel_was_requested`` flag on each raw event is derived from BROKER-SIDE
knowledge (whether the mock broker itself received a cancel request), never from
the internal shadow state. This is a deliberate design choice to satisfy the
Step 8C caveat: the normalizer is not the source of that truth.

The mock broker supports replaying the adversarial cancellation races:
Cancel->CancelAck, Cancel->Fill, Cancel->ConnectionLost, Cancel->CancelReject.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from acash.execution.broker_events import BrokerEventKind


class MockBrokerStatus(str, Enum):
    """Broker-side order status (exchange reality), NOT the shadow lifecycle."""

    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    DISCONNECTED = "DISCONNECTED"


@dataclass(frozen=True)
class BrokerRawEvent:
    """A raw broker-side observation surfaced for normalization.

    This is what a real broker adapter would emit. It is intentionally
    vendor-agnostic: the adapter maps its payload onto this canonical shape.
    """

    broker_order_id: str
    event_kind: BrokerEventKind
    observed_at: datetime
    source: str
    broker_sequence: str
    cancel_was_requested: bool = False


@dataclass
class MockBrokerOrder:
    """Broker-side record of a placed order (mock exchange reality)."""

    broker_order_id: str
    client_order_id: str
    requested_qty: Decimal
    symbol: str
    status: MockBrokerStatus = MockBrokerStatus.NEW
    filled_qty: Decimal = Decimal("0")
    cancel_was_requested: bool = False
    sequence_counter: int = 0
    events: List["BrokerRawEvent"] = field(default_factory=list)

    def next_sequence(self) -> int:
        self.sequence_counter += 1
        return self.sequence_counter


class MockBroker:
    """Deterministic in-memory broker-side reality simulator.

    Each method mutates the broker-side order record and appends a
    ``BrokerRawEvent`` observation to the order's event log. The shadow state
    machine is never touched here.
    """

    def __init__(self, source: str = "MOCK_BROKER") -> None:
        self._source = source
        self._orders: Dict[str, MockBrokerOrder] = {}
        self._counter = 0

    # -- mgmt ---------------------------------------------------------------

    def _new_id(self, client_order_id: str) -> str:
        self._counter += 1
        return f"BROKER_{self._counter}_{client_order_id}"

    def has_order(self, broker_order_id: str) -> bool:
        return broker_order_id in self._orders

    def get_order(self, broker_order_id: str) -> Optional[MockBrokerOrder]:
        return self._orders.get(broker_order_id)

    # -- order placement ----------------------------------------------------

    def place_order(self, client_order_id: str, symbol: str, quantity: Decimal) -> MockBrokerOrder:
        """Register a new order in broker-side state (NEW); no event yet."""
        broker_order_id = self._new_id(client_order_id)
        order = MockBrokerOrder(
            broker_order_id=broker_order_id,
            client_order_id=client_order_id,
            requested_qty=quantity,
            symbol=symbol,
        )
        self._orders[broker_order_id] = order
        return order

    # -- broker-side behaviors ---------------------------------------------

    def acknowledge(self, broker_order_id: str) -> BrokerRawEvent:
        """Broker acknowledges a working order (NEW/ACKNOWLEDGED)."""
        order = self._require(broker_order_id)
        if order.status not in (MockBrokerStatus.NEW, MockBrokerStatus.ACKNOWLEDGED):
            raise ValueError(f"mock broker: cannot ACK order in {order.status.value}")
        order.status = MockBrokerStatus.ACKNOWLEDGED
        ev = self._raw(order, event_kind=BrokerEventKind.ACK)
        order.events.append(ev)
        return ev

    def apply_partial_fill(self, broker_order_id: str, qty: Decimal) -> BrokerRawEvent:
        """Broker reports a partial fill (residual still working)."""
        order = self._require(broker_order_id)
        if order.status is MockBrokerStatus.FILLED:
            raise ValueError("mock broker: order already FILLED")
        order.status = MockBrokerStatus.PARTIALLY_FILLED
        order.filled_qty += qty
        ev = self._raw(order, event_kind=BrokerEventKind.PARTIAL_FILL)
        order.events.append(ev)
        return ev

    def apply_full_fill(self, broker_order_id: str) -> BrokerRawEvent:
        """Broker reports a complete fill (authoritative, terminal)."""
        order = self._require(broker_order_id)
        order.status = MockBrokerStatus.FILLED
        order.filled_qty = order.requested_qty
        ev = self._raw(order, event_kind=BrokerEventKind.FILLED)
        order.events.append(ev)
        return ev

    def reject(self, broker_order_id: str) -> BrokerRawEvent:
        """Broker rejects the order (authoritative, terminal)."""
        order = self._require(broker_order_id)
        order.status = MockBrokerStatus.REJECTED
        ev = self._raw(order, event_kind=BrokerEventKind.REJECT)
        order.events.append(ev)
        return ev

    def expire(self, broker_order_id: str) -> BrokerRawEvent:
        """Broker reports expiry (authoritative, terminal)."""
        order = self._require(broker_order_id)
        order.status = MockBrokerStatus.EXPIRED
        ev = self._raw(order, event_kind=BrokerEventKind.EXPIRED)
        order.events.append(ev)
        return ev

    # -- cancellation races -------------------------------------------------

    def request_cancel(self, broker_order_id: str) -> None:
        """Broker-side receipt of a cancel request (sets its own flag)."""
        order = self._require(broker_order_id)
        order.cancel_was_requested = True

    def confirm_cancel(self, broker_order_id: str) -> BrokerRawEvent:
        """Race 1: broker confirms cancellation -> CANCELLED (CANCEL_ACK)."""
        order = self._require(broker_order_id)
        if not order.cancel_was_requested:
            raise ValueError("mock broker: no pending cancel to confirm")
        order.status = MockBrokerStatus.CANCELLED
        ev = self._raw(order, event_kind=BrokerEventKind.ORDER_CANCELLED)
        order.events.append(ev)
        return ev

    def fill_during_cancel(self, broker_order_id: str) -> BrokerRawEvent:
        """Race 2: broker fills the order that had a pending cancel -> FILLED."""
        order = self._require(broker_order_id)
        order.status = MockBrokerStatus.FILLED
        order.filled_qty = order.requested_qty
        ev = self._raw(order, event_kind=BrokerEventKind.FILLED)
        order.events.append(ev)
        return ev

    def connection_lost(self, broker_order_id: str) -> BrokerRawEvent:
        """Race 3: connectivity lost while cancel pending -> CONNECTION_LOST."""
        order = self._require(broker_order_id)
        order.status = MockBrokerStatus.DISCONNECTED
        ev = self._raw(order, event_kind=BrokerEventKind.CONNECTION_LOST)
        order.events.append(ev)
        return ev

    def reject_cancel(self, broker_order_id: str) -> BrokerRawEvent:
        """Race 4: broker rejects the cancel, order remains live -> CANCEL_REJECT."""
        order = self._require(broker_order_id)
        if not order.cancel_was_requested:
            raise ValueError("mock broker: no pending cancel to reject")
        order.status = MockBrokerStatus.ACKNOWLEDGED
        order.cancel_was_requested = False
        ev = self._raw(order, event_kind=BrokerEventKind.CANCEL_REJECTED)
        order.events.append(ev)
        return ev

    # -- helpers ------------------------------------------------------------

    def _require(self, broker_order_id: str) -> MockBrokerOrder:
        order = self._orders.get(broker_order_id)
        if order is None:
            raise KeyError(f"mock broker: unknown order '{broker_order_id}'")
        return order

    def _raw(
        self,
        order: MockBrokerOrder,
        *,
        event_kind: BrokerEventKind,
    ) -> BrokerRawEvent:
        return BrokerRawEvent(
            broker_order_id=order.broker_order_id,
            event_kind=event_kind,
            observed_at=datetime.now(timezone.utc),
            source=self._source,
            broker_sequence=f"SEQ_{order.next_sequence()}",
            cancel_was_requested=order.cancel_was_requested,
        )
