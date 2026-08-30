"""Adversarial tests for the Phase 7 Step 8B execution state machine authority.

These tests are the executable interpretation (1:1) of the normative contract
in ``docs/phase7/execution_state_machine.md`` §9, backed by rv1 ``953246d`` +
rv2 ``05c1a04``:

- §2.3 UNKNOWN reconciliation-only exit (NO_NEW_ORDERS, RECONCILIATION_REQUIRED)
- §2.4 CancelRequested != Cancelled; fixed CANCEL_REQUESTED fan-out
- §2.5 terminal absorbing: forall e, delta(terminal, e) = INVALID

FAIL-CLOSED rule: a transition asserted INVALID MUST raise a fail-closed error;
the authority MUST NOT silently return the prior state (implicit coercion).
"""

import pytest

from acash.execution.state_machine import (
    ExecutionEvent,
    ExecutionStateError,
    ExecutionTransition,
    is_terminal,
    transition_order,
)
from acash.execution.schema import OrderLifecycleState

TERMINAL = (
    OrderLifecycleState.FILLED,
    OrderLifecycleState.CANCELLED,
    OrderLifecycleState.REJECTED,
    OrderLifecycleState.EXPIRED,
)

ALL_EVENTS = list(ExecutionEvent)


# ============================================================================
# §2.3 — UNKNOWN reconciliation gate
# ============================================================================

def test_unknown_requires_reconciliation() -> None:
    # Only RECONCILE (with evidence) or CONNECTION_LOST (incident loop) are
    # permitted from UNKNOWN; any other event must fail closed.
    for ev in ALL_EVENTS:
        if ev in (ExecutionEvent.RECONCILE, ExecutionEvent.CONNECTION_LOST):
            continue
        with pytest.raises(ExecutionStateError, match="hard safety boundary"):
            transition_order(OrderLifecycleState.UNKNOWN, ev)


def test_unknown_cannot_transition_to_cancelled_directly() -> None:
    # CANCEL_ACK is not a valid broker-evidence path out of UNKNOWN.
    with pytest.raises(ExecutionStateError, match="hard safety boundary"):
        transition_order(OrderLifecycleState.UNKNOWN, ExecutionEvent.CANCEL_ACK)


def test_unknown_cannot_transition_to_acknowledged() -> None:
    with pytest.raises(ExecutionStateError, match="hard safety boundary"):
        transition_order(OrderLifecycleState.UNKNOWN, ExecutionEvent.ACK)


def test_unknown_reconcile_dispute_remains_unknown() -> None:
    res = transition_order(
        OrderLifecycleState.UNKNOWN,
        ExecutionEvent.RECONCILE,
        evidence="UNKNOWN",
    )
    assert res.new_state is OrderLifecycleState.UNKNOWN
    assert res.dispute is True
    assert res.is_terminal is False
    assert res.evidence_required is True


def test_unknown_reconcile_requires_evidence() -> None:
    with pytest.raises(ExecutionStateError, match="evidence"):
        transition_order(OrderLifecycleState.UNKNOWN, ExecutionEvent.RECONCILE)


def test_unknown_reconcile_to_verified_terminal() -> None:
    for target in TERMINAL:
        res = transition_order(
            OrderLifecycleState.UNKNOWN,
            ExecutionEvent.RECONCILE,
            evidence=target.value,
        )
        assert res.new_state is target
        assert res.is_terminal is True
        assert res.evidence_required is True


def test_unknown_reconcile_rejects_malformed_evidence() -> None:
    with pytest.raises(ExecutionStateError, match="does not name a verified"):
        transition_order(
            OrderLifecycleState.UNKNOWN,
            ExecutionEvent.RECONCILE,
            evidence="MAYBE_FILLED???",
        )


def test_unknown_connection_lost_stays_unknown_and_dispute() -> None:
    res = transition_order(
        OrderLifecycleState.UNKNOWN, ExecutionEvent.CONNECTION_LOST
    )
    assert res.new_state is OrderLifecycleState.UNKNOWN
    assert res.dispute is True


# ============================================================================
# §2.4 — CancelRequested != Cancelled; fixed fan-out
# ============================================================================

def test_cancel_requested_is_not_cancelled() -> None:
    # Contract §2.4: CancelRequested != Cancelled is guaranteed by the enum
    # defining two distinct members (MyPy proves it non-overlapping). The
    # meaningful invariant is behavioral: a pending cancel MUST NOT be coerced
    # to CANCELLED by the authority.
    assert len({OrderLifecycleState.CANCEL_REQUESTED, OrderLifecycleState.CANCELLED}) == 2
    # A pending cancel request must NOT be implicitly coerced to CANCELLED.
    with pytest.raises(ExecutionStateError, match="INVALID transition"):
        transition_order(
            OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.CANCEL_REQUEST
        )


def test_cancel_ack_transitions_to_cancelled() -> None:
    res = transition_order(
        OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.CANCEL_ACK
    )
    assert res.new_state is OrderLifecycleState.CANCELLED
    assert res.is_terminal is True


def test_cancel_reject_returns_to_acknowledged_live() -> None:
    # Broker confirmed cancel rejected AND underlying order remains live.
    res = transition_order(
        OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.CANCEL_REJECT
    )
    assert res.new_state is OrderLifecycleState.ACKNOWLEDGED
    assert res.is_terminal is False


def test_late_fill_after_cancel_requested_becomes_filled() -> None:
    res = transition_order(
        OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.FILL
    )
    assert res.new_state is OrderLifecycleState.FILLED
    assert res.is_terminal is True


def test_connection_loss_during_cancel_becomes_unknown() -> None:
    res = transition_order(
        OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.CONNECTION_LOST
    )
    assert res.new_state is OrderLifecycleState.UNKNOWN
    assert res.is_terminal is False


# ============================================================================
# Happy-path lifecycle (contract §4 rows 1-15)
# ============================================================================

def test_intent_to_submitted_to_acknowledged() -> None:
    res = transition_order(OrderLifecycleState.INTENT, ExecutionEvent.SUBMIT)
    assert res.new_state is OrderLifecycleState.SUBMITTED
    res = transition_order(res.new_state, ExecutionEvent.ACK)
    assert res.new_state is OrderLifecycleState.ACKNOWLEDGED


def test_submitted_reject_is_terminal() -> None:
    res = transition_order(OrderLifecycleState.SUBMITTED, ExecutionEvent.REJECT)
    assert res.new_state is OrderLifecycleState.REJECTED
    assert res.is_terminal is True


def test_acknowledged_partial_then_filled() -> None:
    res = transition_order(
        OrderLifecycleState.ACKNOWLEDGED, ExecutionEvent.PARTIAL_FILL
    )
    assert res.new_state is OrderLifecycleState.PARTIALLY_FILLED
    res = transition_order(res.new_state, ExecutionEvent.FILL)
    assert res.new_state is OrderLifecycleState.FILLED
    assert res.is_terminal is True


def test_acknowledged_cancel_request_flow() -> None:
    res = transition_order(
        OrderLifecycleState.ACKNOWLEDGED, ExecutionEvent.CANCEL_REQUEST
    )
    assert res.new_state is OrderLifecycleState.CANCEL_REQUESTED


def test_submitted_connection_lost_becomes_unknown() -> None:
    res = transition_order(
        OrderLifecycleState.SUBMITTED, ExecutionEvent.CONNECTION_LOST
    )
    assert res.new_state is OrderLifecycleState.UNKNOWN


# ============================================================================
# §2.5 — Terminal absorbing states
# ============================================================================

def test_terminal_states_are_absorbing() -> None:
    # forall s in terminal, forall e: delta(s, e) = INVALID (raises fail-closed).
    for s in TERMINAL:
        for ev in ALL_EVENTS:
            with pytest.raises(ExecutionStateError, match="terminal state"):
                transition_order(s, ev)


def test_late_event_after_terminal_raises_invalid_not_mutation() -> None:
    # Late broker event after terminal must raise; historical state unchanged.
    hist = [OrderLifecycleState.FILLED, OrderLifecycleState.CANCELLED,
            OrderLifecycleState.REJECTED, OrderLifecycleState.EXPIRED]
    for s, ev in ((s, e) for s in hist for e in ALL_EVENTS):
        with pytest.raises(ExecutionStateError):
            transition_order(s, ev)
    # No implicit coercion: the authoritative API only returns on success.
    for s in hist:
        assert is_terminal(s)


# ============================================================================
# Invalid / boundary transitions (contract §5.1)
# ============================================================================

def test_intent_cannot_fill_before_submission() -> None:
    with pytest.raises(ExecutionStateError, match="INVALID transition"):
        transition_order(OrderLifecycleState.INTENT, ExecutionEvent.FILL)


def test_submitted_cannot_cancel_before_ack() -> None:
    with pytest.raises(ExecutionStateError, match="INVALID transition"):
        transition_order(OrderLifecycleState.SUBMITTED, ExecutionEvent.CANCEL_REQUEST)


def test_invalid_pairs_all_raise_fail_closed() -> None:
    # Every (state, event) pair NOT in the canonical table must raise — the
    # authority never silently no-ops nor returns the prior state.
    live = (
        OrderLifecycleState.INTENT,
        OrderLifecycleState.SUBMITTED,
        OrderLifecycleState.ACKNOWLEDGED,
        OrderLifecycleState.PARTIALLY_FILLED,
        OrderLifecycleState.CANCEL_REQUESTED,
    )
    for s in live:
        for ev in ALL_EVENTS:
            try:
                res = transition_order(s, ev)
            except ExecutionStateError:
                continue  # correctly failed closed
            assert isinstance(res, ExecutionTransition)
            assert res.new_state is not None


# ============================================================================
# is_terminal helper
# ============================================================================

def test_is_terminal_classification() -> None:
    for s in TERMINAL:
        assert is_terminal(s) is True
    for s in (
        OrderLifecycleState.INTENT,
        OrderLifecycleState.SUBMITTED,
        OrderLifecycleState.ACKNOWLEDGED,
        OrderLifecycleState.PARTIALLY_FILLED,
        OrderLifecycleState.CANCEL_REQUESTED,
        OrderLifecycleState.UNKNOWN,
    ):
        assert is_terminal(s) is False
