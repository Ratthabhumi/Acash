"""Phase 7 Step 8B: Pure Order Execution State Machine Authority.

Implements the authoritative transition contract defined in
``docs/phase7/execution_state_machine.md`` (rv1 ``953246d`` + rv2 ``05c1a04``).

This module is a PURE state-transition authority:
- It accepts (current state, normalized event, optional reconciliation evidence)
  and returns an ``ExecutionTransition`` result.
- It performs NO network I/O, NO broker calls, NO datetime.now() sampling.
  Connectivity events (``CONNECTION_LOST``) are ALREADY normalized by the caller
  before reaching this authority.

Normative invariants enforced (from contract §2):
- §2.3 UNKNOWN: no new orders / reconciliation required; exit only via RECONCILE
  with evidence; NO UNKNOWN -> ACKNOWLEDGED; NO evidence-free CANCELLED/FILLED.
- §2.4 CancelRequested != Cancelled; fixed CANCEL_REQUESTED fan-out.
- §2.5 Terminal absorbing: s in {FILLED,CANCELLED,REJECTED,EXPIRED} =>
  forall e, delta(s,e) = INVALID (fail-closed raise).
- Any (state, event) pair outside the table is INVALID and raises
  ExecutionStateError. It never silently no-ops / coerces.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from acash.core.domain.exceptions import DomainValidationError
from acash.execution.schema import OrderLifecycleState


class ExecutionStateError(DomainValidationError):
    """Raised when an order state transition is invalid or fail-closed violated.

    Fail-closed: an invalid (state, event) pair MUST raise; it MUST NOT silently
    return the prior state (that would be an implicit coercion).
    """


class ExecutionEvent(str, Enum):
    """Canonical normalized events accepted by the transition authority.

    Aligned to contract §3. CONNECTION_LOST is a pseudo-event supplied by
    connectivity monitoring; RECONCILE carries reconciliation evidence.
    """

    SUBMIT = "SUBMIT"
    ACK = "ACK"
    REJECT = "REJECT"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILL = "FILL"
    CANCEL_REQUEST = "CANCEL_REQUEST"
    CANCEL_ACK = "CANCEL_ACK"
    CANCEL_REJECT = "CANCEL_REJECT"
    EXPIRY = "EXPIRY"
    CONNECTION_LOST = "CONNECTION_LOST"
    RECONCILE = "RECONCILE"


# ----------------------------------------------------------------------------
# Single canonical transition table (contract §4)
# ----------------------------------------------------------------------------

_TERMINAL_STATES = frozenset(
    {
        OrderLifecycleState.FILLED,
        OrderLifecycleState.CANCELLED,
        OrderLifecycleState.REJECTED,
        OrderLifecycleState.EXPIRED,
    }
)

# (source, event) -> target state. Single authoritative data-driven definition.
_TRANSITIONS: dict[tuple[OrderLifecycleState, ExecutionEvent], OrderLifecycleState] = {
    # INTENT
    (OrderLifecycleState.INTENT, ExecutionEvent.SUBMIT): OrderLifecycleState.SUBMITTED,
    # SUBMITTED
    (OrderLifecycleState.SUBMITTED, ExecutionEvent.ACK): OrderLifecycleState.ACKNOWLEDGED,
    (OrderLifecycleState.SUBMITTED, ExecutionEvent.REJECT): OrderLifecycleState.REJECTED,
    (OrderLifecycleState.SUBMITTED, ExecutionEvent.CONNECTION_LOST): OrderLifecycleState.UNKNOWN,
    # ACKNOWLEDGED
    (OrderLifecycleState.ACKNOWLEDGED, ExecutionEvent.PARTIAL_FILL): OrderLifecycleState.PARTIALLY_FILLED,
    (OrderLifecycleState.ACKNOWLEDGED, ExecutionEvent.FILL): OrderLifecycleState.FILLED,
    (OrderLifecycleState.ACKNOWLEDGED, ExecutionEvent.CANCEL_REQUEST): OrderLifecycleState.CANCEL_REQUESTED,
    (OrderLifecycleState.ACKNOWLEDGED, ExecutionEvent.REJECT): OrderLifecycleState.REJECTED,
    (OrderLifecycleState.ACKNOWLEDGED, ExecutionEvent.EXPIRY): OrderLifecycleState.EXPIRED,
    (OrderLifecycleState.ACKNOWLEDGED, ExecutionEvent.CONNECTION_LOST): OrderLifecycleState.UNKNOWN,
    # PARTIALLY_FILLED
    (OrderLifecycleState.PARTIALLY_FILLED, ExecutionEvent.PARTIAL_FILL): OrderLifecycleState.PARTIALLY_FILLED,
    (OrderLifecycleState.PARTIALLY_FILLED, ExecutionEvent.FILL): OrderLifecycleState.FILLED,
    (OrderLifecycleState.PARTIALLY_FILLED, ExecutionEvent.CANCEL_REQUEST): OrderLifecycleState.CANCEL_REQUESTED,
    (OrderLifecycleState.PARTIALLY_FILLED, ExecutionEvent.EXPIRY): OrderLifecycleState.EXPIRED,
    (OrderLifecycleState.PARTIALLY_FILLED, ExecutionEvent.CONNECTION_LOST): OrderLifecycleState.UNKNOWN,
    # CANCEL_REQUESTED (contract §2.4 fixed fan-out + row 20)
    (OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.CANCEL_ACK): OrderLifecycleState.CANCELLED,
    (OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.CANCEL_REJECT): OrderLifecycleState.ACKNOWLEDGED,
    (OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.FILL): OrderLifecycleState.FILLED,
    (OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.CONNECTION_LOST): OrderLifecycleState.UNKNOWN,
    (OrderLifecycleState.CANCEL_REQUESTED, ExecutionEvent.RECONCILE): OrderLifecycleState.UNKNOWN,
    # UNKNOWN (contract §2.3 — evidence-gated, reconciliation-only exit)
    (OrderLifecycleState.UNKNOWN, ExecutionEvent.RECONCILE): OrderLifecycleState.UNKNOWN,  # sentinel; targets resolved below
    (OrderLifecycleState.UNKNOWN, ExecutionEvent.CONNECTION_LOST): OrderLifecycleState.UNKNOWN,
}


@dataclass(frozen=True)
class ExecutionTransition:
    """Immutable result of a state transition.

    Attributes:
        new_state: The resulting state after applying the event.
        is_terminal: True when new_state is an absorbing terminal state.
        dispute: True when the transition is a reconciliation dispute /
            connection-lost loop (stays UNKNOWN) that SHALL raise an incident.
        evidence_required: True when the caller MUST supply reconciliation
            evidence (`RECONCILE` recovery); this transition would otherwise
            fail closed.
    """

    new_state: OrderLifecycleState
    is_terminal: bool
    dispute: bool = False
    evidence_required: bool = False


def _verify_evidence(evidence: Optional[str]) -> None:
    """Fail-closed check: reconciliation evidence MUST be non-empty."""
    if evidence is None or not evidence.strip():
        raise ExecutionStateError(
            "UNKNOWN -> terminal requires reconciliation evidence; none provided. "
            "Fail-closed: no evidence, no transition."
        )


def is_terminal(state: OrderLifecycleState) -> bool:
    """Return True if `state` is an absorbing terminal state (§2.5)."""
    return state in _TERMINAL_STATES


def transition_order(
    state: OrderLifecycleState,
    event: ExecutionEvent,
    *,
    evidence: Optional[str] = None,
) -> ExecutionTransition:
    """Apply `event` to `state` and return the resulting ``ExecutionTransition``.

    Pure function — no I/O, no clock. Raises ``ExecutionStateError`` (fail-closed)
    for any (state, event) pair not in the canonical table (§4), including any
    event delivered to a terminal state (absorbing, §2.5) and any evidence-free
    ``UNKNOWN`` reconciliation recovery (§2.3).

    Args:
        state: current ``OrderLifecycleState``.
        event: normalized ``ExecutionEvent``.
        evidence: non-empty reconciliation evidence STRING. REQUIRED to leave
            ``UNKNOWN`` toward a terminal state; ignored otherwise.

    Returns:
        ``ExecutionTransition`` describing the resulting state and flags.
    """
    if state in _TERMINAL_STATES:
        raise ExecutionStateError(
            f"Order is in terminal state {state.value}; absorbing (§2.5). "
            f"Event {event.value} is INVALID: forall e, delta(terminal, e) = INVALID. "
            "Late events MUST be routed to reconciliation/incident, not the state machine."
        )

    # UNKNOWN reconciliation recovery (contract §2.3) — the only exit from UNKNOWN.
    if state is OrderLifecycleState.UNKNOWN:
        if event is ExecutionEvent.RECONCILE:
            if evidence is None or not evidence.strip():
                raise ExecutionStateError(
                    "UNKNOWN requires reconciliation evidence to exit (§2.3). "
                    "No evidence -> no transition; order MUST remain UNKNOWN."
                )
            # Evidence is required; the TARGET terminal state must be encoded
            # in the evidence (single authoritative resolution). We require the
            # caller to select the verified outcome explicitly.
            reconcile_target = _resolve_reconcile_target(evidence)
            if reconcile_target is OrderLifecycleState.UNKNOWN:
                return ExecutionTransition(
                    new_state=OrderLifecycleState.UNKNOWN,
                    is_terminal=False,
                    dispute=True,
                    evidence_required=True,
                )
            return ExecutionTransition(
                new_state=reconcile_target,
                is_terminal=True,
                evidence_required=True,
            )
        if event is ExecutionEvent.CONNECTION_LOST:
            return ExecutionTransition(
                new_state=OrderLifecycleState.UNKNOWN,
                is_terminal=False,
                dispute=True,
            )
        raise ExecutionStateError(
            f"UNKNOWN is a hard safety boundary (§2.3). Event {event.value} is "
            f"INVALID from UNKNOWN; only RECONCILE (with evidence) or "
            "CONNECTION_LOST (incident) are permitted."
        )

    target = _TRANSITIONS.get((state, event))
    if target is None:
        raise ExecutionStateError(
            f"INVALID transition: ({state.value}, {event.value}) is not in the "
            f"canonical table (§4). Fail-closed: no silent no-op or coercion."
        )

    return ExecutionTransition(
        new_state=target,
        is_terminal=target in _TERMINAL_STATES,
    )

def _resolve_reconcile_target(evidence: str) -> OrderLifecycleState:
    """Resolve the evidence-gated verified outcome for an UNKNOWN reconciliation.

    The reconciliation engine MUST emit evidence that names the authoritative
    broker outcome. Accepted evidence targets are the terminal states and the
    dispute (UNKNOWN). Unknown/malformed evidence fails closed.
    """
    token = evidence.strip().upper()
    mapping = {
        "FILLED": OrderLifecycleState.FILLED,
        "CANCELLED": OrderLifecycleState.CANCELLED,
        "REJECTED": OrderLifecycleState.REJECTED,
        "EXPIRED": OrderLifecycleState.EXPIRED,
        "UNKNOWN": OrderLifecycleState.UNKNOWN,
    }
    target = mapping.get(token)
    if target is None:
        raise ExecutionStateError(
            f"Reconciliation evidence '{evidence}' does not name a verified "
            "authoritative outcome. Fail-closed: no transition. Valid evidence "
            "tokens: FILLED, CANCELLED, REJECTED, EXPIRED, UNKNOWN."
        )
    return target
