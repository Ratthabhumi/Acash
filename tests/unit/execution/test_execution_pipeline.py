"""End-to-end pipeline + adversarial tests for Step 8D Mock Broker.

Verifies the full authority-separated pipeline:

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

The Mock Broker owns only broker-side state and NEVER calls transition_order().
All wiring is done by the harness helpers below, so the broker stays authority-free.

Also verifies the Step 8C caveat: cancel_was_requested is derived from broker-side
state, and the normalizer never guesses it.
"""

from decimal import Decimal

import pytest

from acash.execution.broker_events import normalize_broker_event
from acash.execution.mock_broker import (
    BrokerRawEvent,
    MockBroker,
    MockBrokerOrder,
    MockBrokerStatus,
)
from acash.execution.schema import OrderLifecycleState
from acash.execution.state_machine import (
    ExecutionStateError,
    transition_order,
)


def _apply_raw(shadow: OrderLifecycleState, raw: BrokerRawEvent) -> OrderLifecycleState:
    """Harness-owned wiring: raw event -> canonical event -> transition order."""
    event, _ = normalize_broker_event(
        broker_order_id=raw.broker_order_id,
        event_kind=raw.event_kind,
        observed_at=raw.observed_at,
        source=raw.source,
        broker_sequence=raw.broker_sequence,
        cancel_was_requested=raw.cancel_was_requested,
    )
    return transition_order(shadow, event).new_state


def _placed_ack(order_id: str = "C1") -> tuple[MockBroker, MockBrokerOrder]:
    """Place an order in the mock broker and return (broker, order) at ACK/working."""
    broker = MockBroker()
    order = broker.place_order(client_order_id=order_id, symbol="BTC/USDT", quantity=Decimal("1.0"))
    # Broker acknowledged as a working order (shadow would be SUBMITTED -> ACKNOWLEDGED).
    broker.acknowledge(order.broker_order_id)
    return broker, order


# ============================================================================
# Happy path pipeline
# ============================================================================

def test_pipeline_place_ack_acknowledged() -> None:
    broker, order = _placed_ack("P1")
    raw = order.events[-1]
    assert raw.event_kind.value == "ACK"
    assert _apply_raw(OrderLifecycleState.SUBMITTED, raw) is OrderLifecycleState.ACKNOWLEDGED


def test_pipeline_partial_then_fill() -> None:
    broker, order = _placed_ack("P2")
    raw = broker.apply_partial_fill(order.broker_order_id, Decimal("0.25"))
    state = _apply_raw(OrderLifecycleState.ACKNOWLEDGED, raw)
    assert state is OrderLifecycleState.PARTIALLY_FILLED

    raw = broker.apply_full_fill(order.broker_order_id)
    state = _apply_raw(state, raw)
    assert state is OrderLifecycleState.FILLED


def test_pipeline_reject() -> None:
    broker, order = _placed_ack("P3")
    raw = broker.reject(order.broker_order_id)
    state = _apply_raw(OrderLifecycleState.ACKNOWLEDGED, raw)
    assert state is OrderLifecycleState.REJECTED


# ============================================================================
# Cancellation races (shadow in CANCEL_REQUESTED, broker-side cancel requested)
# ============================================================================

def test_race_cancel_ack_becomes_cancelled() -> None:
    broker, order = _placed_ack("R1")
    broker.request_cancel(order.broker_order_id)  # broker-side cancel receipt
    raw = broker.confirm_cancel(order.broker_order_id)
    state = _apply_raw(OrderLifecycleState.CANCEL_REQUESTED, raw)
    assert state is OrderLifecycleState.CANCELLED


def test_race_cancel_fill_becomes_filled() -> None:
    broker, order = _placed_ack("R2")
    broker.request_cancel(order.broker_order_id)
    raw = broker.fill_during_cancel(order.broker_order_id)
    state = _apply_raw(OrderLifecycleState.CANCEL_REQUESTED, raw)
    assert state is OrderLifecycleState.FILLED


def test_race_cancel_connection_lost_becomes_unknown() -> None:
    broker, order = _placed_ack("R3")
    broker.request_cancel(order.broker_order_id)
    raw = broker.connection_lost(order.broker_order_id)
    state = _apply_raw(OrderLifecycleState.CANCEL_REQUESTED, raw)
    assert state is OrderLifecycleState.UNKNOWN


def test_race_cancel_reject_becomes_acknowledged() -> None:
    broker, order = _placed_ack("R4")
    broker.request_cancel(order.broker_order_id)
    raw = broker.reject_cancel(order.broker_order_id)
    state = _apply_raw(OrderLifecycleState.CANCEL_REQUESTED, raw)
    assert state is OrderLifecycleState.ACKNOWLEDGED


# ============================================================================
# Step 8C caveat: cancel_was_requested is broker-side, never guessed
# ============================================================================

def test_cancel_flag_comes_from_broker_not_shadow() -> None:
    # The raw event carries the broker-side cancel flag; it is not inferred from
    # the shadow state by the normalizer.
    broker, order = _placed_ack("C1")
    broker.request_cancel(order.broker_order_id)
    raw = broker.connection_lost(order.broker_order_id)
    assert raw.cancel_was_requested is True
    # The normalizer itself only knows what the raw event tells it.
    event, _ = normalize_broker_event(
        broker_order_id=raw.broker_order_id,
        event_kind=raw.event_kind,
        observed_at=raw.observed_at,
        source=raw.source,
        broker_sequence=raw.broker_sequence,
        cancel_was_requested=raw.cancel_was_requested,
    )
    assert event.value == "CONNECTION_LOST"


def test_mock_broker_has_no_state_authority() -> None:
    # The mock broker must not expose/Own transition_order semantics.
    from acash.execution import mock_broker as mb
    assert not hasattr(mb.MockBroker, "transition_order")
    assert not hasattr(mb.MockBroker, "apply_transition")


# ============================================================================
# UNKNOWN reconciliation (evidence gate)
# ============================================================================

def test_unknown_reconcile_without_evidence_fails_closed() -> None:
    from acash.execution.state_machine import ExecutionEvent
    with pytest.raises(ExecutionStateError, match="evidence"):
        transition_order(
            OrderLifecycleState.UNKNOWN,
            ExecutionEvent.RECONCILE,
            evidence=None,
        )


def test_unknown_reconcile_with_verified_evidence_reaches_terminal() -> None:
    from acash.execution.state_machine import ExecutionEvent
    for token in ("FILLED", "CANCELLED", "REJECTED", "EXPIRED"):
        # Move an order to UNKNOWN first (via connection loss during cancel).
        broker, order = _placed_ack(f"U_{token}")
        broker.request_cancel(order.broker_order_id)
        raw = broker.connection_lost(order.broker_order_id)
        state = _apply_raw(OrderLifecycleState.CANCEL_REQUESTED, raw)
        assert state is OrderLifecycleState.UNKNOWN
        # Reconciliation provides verified evidence -> leave UNKNOWN.
        res = transition_order(
            OrderLifecycleState.UNKNOWN, ExecutionEvent.RECONCILE, evidence=token
        )
        assert res.new_state.value == token
        assert res.is_terminal is True


# ============================================================================
# Terminal states are absorbing (adversarial)
# ============================================================================

def test_terminal_rejects_all_events() -> None:
    from acash.execution.state_machine import ExecutionEvent

    terminal_states = [
        OrderLifecycleState.FILLED,
        OrderLifecycleState.CANCELLED,
        OrderLifecycleState.REJECTED,
        OrderLifecycleState.EXPIRED,
    ]
    for s in terminal_states:
        for ev in ExecutionEvent:
            with pytest.raises(ExecutionStateError, match="terminal state"):
                transition_order(s, ev)


def test_specific_terminal_invalid_cases() -> None:
    from acash.execution.state_machine import ExecutionEvent

    cases = (
        (OrderLifecycleState.FILLED, ExecutionEvent.CANCEL_REQUEST, "FILLED + CANCEL_REQUEST"),
        (OrderLifecycleState.CANCELLED, ExecutionEvent.FILL, "CANCELLED + FILL"),
        (OrderLifecycleState.REJECTED, ExecutionEvent.ACK, "REJECTED + ACK"),
        (OrderLifecycleState.EXPIRED, ExecutionEvent.FILL, "EXPIRED + FILL"),
    )
    for state, ev, label in cases:
        with pytest.raises(ExecutionStateError, match="terminal state"):
            transition_order(state, ev)
