"""Step 8E adversarial verification tests for the ExecutionCoordinator.

Covers the full end-to-end authority-separated chain and the DoD invariants:

- Full cancel race E2E traces (single test per race, traced from ACKNOWLEDGED).
- Duplicate events + event-identity idempotency (no double fill accumulation).
- Out-of-order events resolved by contract/sequence, not last-event-wins.
- UNKNOWN + reconnect + reconciliation (verified -> terminal; insufficient ->
  UNKNOWN + incident).
- Late-event rejection BY the state authority (never silently dropped).
- Reconciliation conflicts -> incident + restricted (no self-selection).
- No state mutation outside transition_order().
"""

from decimal import Decimal

from acash.execution.broker_events import BrokerEventKind, normalize_broker_event
from acash.execution.coordinator import (
    CoordinatorEvent,
    CoordinatorIncidentKind,
    ExecutionCoordinator,
)
from acash.execution.mock_broker import BrokerRawEvent, MockBroker, MockBrokerOrder
from acash.execution.schema import OrderLifecycleState
from acash.execution.state_machine import ExecutionEvent


EXE_ID = "EXE_TEST_1"
QTY = Decimal("1.000")


def _broker_acknowledged() -> tuple[MockBroker, MockBrokerOrder]:
    """Mock broker with a single placed, working (ACKNOWLEDGED) order."""
    broker = MockBroker()
    order = broker.place_order("C_X11", "BTC/USDT", QTY)
    broker.acknowledge(order.broker_order_id)
    assert order.status.value == "ACKNOWLEDGED"
    return broker, order


def _coordinator() -> ExecutionCoordinator:
    return ExecutionCoordinator(execution_id=EXE_ID, requested_qty=QTY)


def _to_event(raw: BrokerRawEvent) -> CoordinatorEvent:
    """Normalizer seam: raw broker event -> canonical CoordinatorEvent."""
    event, _ = normalize_broker_event(
        broker_order_id=raw.broker_order_id,
        event_kind=raw.event_kind,
        observed_at=raw.observed_at,
        source=raw.source,
        broker_sequence=raw.broker_sequence,
        cancel_was_requested=raw.cancel_was_requested,
    )
    return CoordinatorEvent(
        broker_event_id=f"{raw.broker_order_id}:{raw.broker_sequence}",
        broker_sequence=raw.broker_sequence,
        canonical_event=event,
    )


def _raw_partial(seq: str, fill: Decimal, event_id: str = "pf") -> CoordinatorEvent:
    return CoordinatorEvent(
        broker_event_id=event_id, broker_sequence=seq,
        canonical_event=ExecutionEvent.PARTIAL_FILL, fill_qty=fill,
    )


def _raw_fill(seq: str, fill: Decimal, event_id: str = "fl") -> CoordinatorEvent:
    return CoordinatorEvent(
        broker_event_id=event_id, broker_sequence=seq,
        canonical_event=ExecutionEvent.FILL, fill_qty=fill,
    )


def _drive_acknowledged(coord: ExecutionCoordinator) -> None:
    """Move shadow to ACKNOWLEDGED through the coordinator (SUB -> ACK)."""
    coord.apply(CoordinatorEvent("sub", "1", ExecutionEvent.ACK))


def _drive_cancel_requested(coord: ExecutionCoordinator) -> None:
    _drive_acknowledged(coord)
    coord.apply(CoordinatorEvent("cr", "2", ExecutionEvent.CANCEL_REQUEST))


# ============================================================================
# 1. Full cancel race E2E — single test each, traced from ACKNOWLEDGED
# ============================================================================

def test_e2e_race_cancel_ack() -> None:
    broker, order = _broker_acknowledged()
    coord = _coordinator()
    _drive_acknowledged(coord)
    s1: OrderLifecycleState = coord.state
    assert s1 == OrderLifecycleState.ACKNOWLEDGED
    coord.apply(CoordinatorEvent("cr", "2", ExecutionEvent.CANCEL_REQUEST))
    s2: OrderLifecycleState = coord.state
    assert s2 == OrderLifecycleState.CANCEL_REQUESTED
    broker.request_cancel(order.broker_order_id)
    out = coord.apply(_to_event(broker.confirm_cancel(order.broker_order_id)))
    assert out.state == OrderLifecycleState.CANCELLED
    assert not out.rejected and not out.was_duplicate


def test_e2e_race_cancel_reject() -> None:
    broker, order = _broker_acknowledged()
    coord = _coordinator()
    _drive_cancel_requested(coord)
    broker.request_cancel(order.broker_order_id)
    out = coord.apply(_to_event(broker.reject_cancel(order.broker_order_id)))
    assert out.state == OrderLifecycleState.ACKNOWLEDGED


def test_e2e_race_cancel_fill() -> None:
    broker, order = _broker_acknowledged()
    coord = _coordinator()
    _drive_cancel_requested(coord)
    broker.request_cancel(order.broker_order_id)
    fill_ev = _to_event(broker.fill_during_cancel(order.broker_order_id))
    fill_ev = CoordinatorEvent(
        fill_ev.broker_event_id, fill_ev.broker_sequence, fill_ev.canonical_event,
        evidence=None, fill_qty=QTY,
    )
    out = coord.apply(fill_ev)
    assert out.state == OrderLifecycleState.FILLED
    assert out.filled_qty == QTY


def test_e2e_race_cancel_connection_lost() -> None:
    broker, order = _broker_acknowledged()
    coord = _coordinator()
    _drive_cancel_requested(coord)
    broker.request_cancel(order.broker_order_id)
    out = coord.apply(_to_event(broker.connection_lost(order.broker_order_id)))
    assert out.state == OrderLifecycleState.UNKNOWN


# ============================================================================
# 2. Duplicate events + event-identity idempotency
# ============================================================================

def test_duplicate_ack_is_idempotent() -> None:
    coord = _coordinator()
    ev = CoordinatorEvent("ack", "1", ExecutionEvent.ACK)
    out1 = coord.apply(ev)
    out2 = coord.apply(ev)
    assert out1.state == OrderLifecycleState.ACKNOWLEDGED
    assert out2.was_duplicate is True
    assert out2.state == out1.state


def test_duplicate_ack_via_mock_is_idempotent() -> None:
    broker, order = _broker_acknowledged()
    coord = _coordinator()
    raw = broker.acknowledge(order.broker_order_id)  # same identity both deliveries
    _drive_acknowledged(coord)
    # redeliver the exact same raw event identity twice
    out1 = coord.apply(_to_event(raw))
    out2 = coord.apply(_to_event(raw))
    assert out2.was_duplicate is True
    assert out2.state == out1.state


def test_duplicate_partial_fill_does_not_double_accumulate() -> None:
    coord = _coordinator()
    _drive_acknowledged(coord)
    ev = _raw_partial("1", Decimal("0.400"), event_id="pf-1")
    out1 = coord.apply(ev)
    out2 = coord.apply(ev)
    assert out1.filled_qty == Decimal("0.400")
    assert out2.was_duplicate is True
    assert out2.filled_qty == Decimal("0.400")  # NOT 0.800


def test_distinct_fills_accumulate_only_once_each() -> None:
    # Two different event identities (two partial fills) -> both counted; a replay
    # of either identity must NOT be recounted.
    coord = _coordinator()
    _drive_acknowledged(coord)
    pf1 = _raw_partial("10", Decimal("0.250"), event_id="pf-1")
    pf2 = _raw_partial("11", Decimal("0.250"), event_id="pf-2")
    coord.apply(pf1)
    coord.apply(pf2)
    assert coord.filled_qty == Decimal("0.500")
    coord.apply(pf1)  # replay pf-1
    assert coord.filled_qty == Decimal("0.500")  # not 0.750
    assert coord.state == OrderLifecycleState.PARTIALLY_FILLED


def test_duplicate_cancel_ack_is_idempotent() -> None:
    coord = _coordinator()
    _drive_cancel_requested(coord)
    ev = CoordinatorEvent("ca", "3", ExecutionEvent.CANCEL_ACK)
    out1 = coord.apply(ev)
    out2 = coord.apply(ev)
    assert out1.state == OrderLifecycleState.CANCELLED
    assert out2.was_duplicate is True
    assert out2.state == OrderLifecycleState.CANCELLED


# ============================================================================
# 3. Out-of-order events resolved by contract, not last-event-wins
# ============================================================================

def test_out_of_order_fill_then_partial_rejected() -> None:
    # FILL reaches terminal; a later PARTIAL_FILL is a late event rejected by the
    # state authority (never last-event-wins back to a working state).
    coord = _coordinator()
    _drive_acknowledged(coord)
    coord.apply(_raw_fill("1", QTY))
    assert coord.state == OrderLifecycleState.FILLED
    late = coord.apply(_raw_partial("2", Decimal("0.100")))
    assert late.rejected is True
    assert late.state == OrderLifecycleState.FILLED  # unchanged


def test_out_of_order_cancel_ack_then_fill_rejected() -> None:
    coord = _coordinator()
    _drive_cancel_requested(coord)
    coord.apply(CoordinatorEvent("ca", "3", ExecutionEvent.CANCEL_ACK))  # -> CANCELLED
    late = coord.apply(_raw_fill("4", Decimal("0.100")))
    assert late.rejected is True
    assert late.state == OrderLifecycleState.CANCELLED


# ============================================================================
# 4. UNKNOWN + reconnect + reconciliation
# ============================================================================

def test_unknown_reconnect_reconcile_verified_to_terminal() -> None:
    coord = _coordinator()
    _drive_cancel_requested(coord)
    coord.apply(CoordinatorEvent("lost", "3", ExecutionEvent.CONNECTION_LOST))
    assert coord.state == OrderLifecycleState.UNKNOWN
    out = coord.reconcile(
        broker_event_id="rec-1", broker_sequence="R1", evidence_token="CANCELLED"
    )
    assert out.state == OrderLifecycleState.CANCELLED
    assert out.transition is not None and out.transition.is_terminal


def test_unknown_reconcile_insufficient_evidence_stays_unknown_incident() -> None:
    coord = _coordinator()
    coord.shadow_state = OrderLifecycleState.UNKNOWN
    out = coord.reconcile(
        broker_event_id="bad-1", broker_sequence="B1", evidence_token="GARBAGE"
    )
    assert out.state == OrderLifecycleState.UNKNOWN
    assert out.rejected is True
    assert any(
        i.kind is CoordinatorIncidentKind.UNKNOWN_RECONCILIATION
        for i in coord.incidents
    )


# ============================================================================
# 5. Late events rejected by the state authority (never dropped)
# ============================================================================

def test_late_fill_after_cancelled_rejected() -> None:
    coord = _coordinator()
    _drive_cancel_requested(coord)
    coord.apply(CoordinatorEvent("ca", "3", ExecutionEvent.CANCEL_ACK))  # -> CANCELLED
    out = coord.apply(_raw_fill("4", Decimal("1.0")))
    assert out.rejected is True
    assert out.state == OrderLifecycleState.CANCELLED
    assert any(i.kind is CoordinatorIncidentKind.LATE_EVENT for i in coord.incidents)


# ============================================================================
# 6. Reconciliation conflict -> incident + restricted (no self-selection)
# ============================================================================

def test_reconciliation_conflict_shadow_cancelled_broker_filled() -> None:
    coord = _coordinator()
    _drive_cancel_requested(coord)
    coord.apply(CoordinatorEvent("ca", "3", ExecutionEvent.CANCEL_ACK))  # -> CANCELLED
    assert not coord.disputed
    out = coord.reconcile(
        broker_event_id="conf", broker_sequence="C1", evidence_token="FILLED"
    )
    assert out.state == OrderLifecycleState.CANCELLED  # no regression of terminal
    assert coord.disputed is True  # restricted path
    assert any(
        i.kind is CoordinatorIncidentKind.RECONCILIATION_CONFLICT
        for i in coord.incidents
    )


def test_reconcile_matching_terminal_evidence_no_conflict() -> None:
    coord = _coordinator()
    _drive_cancel_requested(coord)
    coord.apply(CoordinatorEvent("ca", "3", ExecutionEvent.CANCEL_ACK))  # -> CANCELLED
    out = coord.reconcile(
        broker_event_id="conf2", broker_sequence="C2", evidence_token="CANCELLED"
    )
    assert coord.disputed is False
    assert out.state == OrderLifecycleState.CANCELLED
    assert not any(
        i.kind is CoordinatorIncidentKind.RECONCILIATION_CONFLICT
        for i in coord.incidents
    )


# ============================================================================
# 7. No state mutation outside transition_order() / fail-closed
# ============================================================================

def test_invalid_transition_is_rejected_not_fabricated() -> None:
    coord = _coordinator()
    _drive_cancel_requested(coord)
    # REJECT is NOT valid from CANCEL_REQUESTED (not in the canonical table) ->
    # the authority raises; coordinator must not fabricate a state, it surfaces
    # rejection.
    bad = coord.apply(CoordinatorEvent("y", "2", ExecutionEvent.REJECT))
    assert bad.rejected is True
    assert bad.state == OrderLifecycleState.CANCEL_REQUESTED
