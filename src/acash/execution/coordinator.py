"""Phase 7 Step 8E: Execution Coordinator — the Shadow State & Reconciliation layer.

This module realizes the "Shadow State -> Reconciliation" block of the Step 8
architecture while keeping ``transition_order()`` as the SOLE state authority.

```
Broker Adapter
   ↓ raw
Event Normalizer (8C: normalize_broker_event)
   ↓ canonical event + evidence
transition_order()   (8B: SOLE AUTHORITY)
   ↓ new state
ExecutionCoordinator  <- THIS module: owns shadow state, dedup, fill ledger,
   ↓                    incident routing, reconciliation
Shadow State -> Reconciliation
```

The coordinator owns the *lifecycle that the state machine cannot* without
breaking its purity contract:
- **Event-identity idempotency**: the same (broker_event_id, broker_sequence)
  redelivered MUST NOT re-apply a transition nor double-accumulate fill qty.
  Deduplication lives HERE, never in ``transition_order()``.
- **Shadow state ownership**: the coordinator holds the current shadow
  ``OrderLifecycleState`` and ``filled_qty`` ledger.
- **Late-event routing**: an event delivered after the shadow reached a terminal
  state is rejected BY THE STATE AUTHORITY (``transition_order()`` raises its
  terminal-absorbing error), and the coordinator records a LATE_EVENT incident.
  Late events are never silently dropped/disappeared.
- **Reconciliation**: leaving UNKNOWN requires verified evidence; contradictory
  or insufficient evidence produces a conflict incident and an operationally
  restricted path, NOT self-selection of one side.
- **No state mutation outside transition_order()**: every shadow-state change is
  the direct return value of ``transition_order()``. The coordinator never
  assigns a state on its own judgement.

The coordinator contains no I/O and no clock; it is a pure orchestration seam.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

from acash.execution.schema import OrderLifecycleState
from acash.execution.state_machine import (
    ExecutionEvent,
    ExecutionStateError,
    ExecutionTransition,
    is_terminal,
    transition_order,
)


class CoordinatorIncidentKind(str, Enum):
    """Operational incident categories surfaced by the coordinator."""

    LATE_EVENT = "LATE_EVENT"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    RECONCILIATION_CONFLICT = "RECONCILIATION_CONFLICT"
    UNKNOWN_RECONCILIATION = "UNKNOWN_RECONCILIATION"


@dataclass(frozen=True)
class CoordinatorIncident:
    """Immutable forensic record of a detected operational anomaly."""

    incident_id: str
    kind: CoordinatorIncidentKind
    execution_id: str
    broker_event_id: Optional[str]
    broker_sequence: Optional[str]
    detail: str


@dataclass(frozen=True)
class CoordinatorEvent:
    """A canonical event submitted to the coordinator for application.

    ``canonical_event`` is the already-normalized ``ExecutionEvent`` (Step 8C
    output). Event identity is (broker_event_id, broker_sequence); the same pair
    is idempotent.
    """

    broker_event_id: str
    broker_sequence: str
    canonical_event: ExecutionEvent
    evidence: Optional[str] = None
    fill_qty: Optional[Decimal] = None


@dataclass(frozen=True)
class CoordinatorOutcome:
    """Result of applying an event via the coordinator."""

    state: OrderLifecycleState
    filled_qty: Decimal
    was_duplicate: bool
    rejected: bool
    transition: Optional[ExecutionTransition]
    incidents: Tuple[CoordinatorIncident, ...] = ()


class ExecutionCoordinator:
    """Shadow-state owner for a single order execution.

    Attributes:
        execution_id: tied to ``ExecutionManifest.execution_id``.
        requested_qty: requested volume from the originating ``OrderIntent``.
    """

    def __init__(
        self,
        execution_id: str,
        requested_qty: Decimal,
        initial_state: OrderLifecycleState = OrderLifecycleState.SUBMITTED,
    ) -> None:
        if not execution_id or not execution_id.strip():
            raise ValueError("execution_id must be non-empty")
        if requested_qty < Decimal("0"):
            raise ValueError("requested_qty cannot be negative")
        self.execution_id = execution_id
        self.requested_qty = requested_qty
        self.shadow_state: OrderLifecycleState = initial_state
        self.filled_qty: Decimal = Decimal("0")
        self._seen: set[Tuple[str, str]] = set()
        self._incidents: List[CoordinatorIncident] = []
        self._incident_counter = 0
        self._disputed: bool = False

    # -- public state -------------------------------------------------------

    @property
    def state(self) -> OrderLifecycleState:
        return self.shadow_state

    @property
    def disputed(self) -> bool:
        """True when a reconciliation conflict restricted this execution."""
        return self._disputed

    @property
    def incidents(self) -> Tuple[CoordinatorIncident, ...]:
        return tuple(self._incidents)

    # -- core application ---------------------------------------------------

    def apply(self, event: CoordinatorEvent) -> CoordinatorOutcome:
        """Apply a canonical broker event with event-identity idempotency.

        Every shadow-state change is delegated to ``transition_order()`` (the
        sole authority). Returns an outcome describing the effect — deduplicated,
        rejected-by-authority, or applied.
        """
        key = (event.broker_event_id, event.broker_sequence)
        if key in self._seen:
            incident = self._new_incident(
                CoordinatorIncidentKind.DUPLICATE_EVENT,
                event,
                f"Duplicate event identity ({key[0]}, {key[1]}) redelivered; "
                "no re-apply, no fill accumulation.",
            )
            return CoordinatorOutcome(
                state=self.shadow_state,
                filled_qty=self.filled_qty,
                was_duplicate=True,
                rejected=False,
                transition=None,
                incidents=(incident,),
            )
        self._seen.add(key)

        # Late-event routing: a terminal shadow only accepts nothing new; let the
        # state authority reject it (it raises terminal-absorbing). We surface the
        # rejection as an incident rather than silently dropping or crashing state.
        try:
            transition = transition_order(
                self.shadow_state,
                event.canonical_event,
                evidence=event.evidence,
            )
        except ExecutionStateError as exc:
            incident = self._new_incident(
                CoordinatorIncidentKind.LATE_EVENT,
                event,
                f"Rejected by state authority: {exc}",
            )
            return CoordinatorOutcome(
                state=self.shadow_state,
                filled_qty=self.filled_qty,
                was_duplicate=False,
                rejected=True,
                transition=None,
                incidents=(incident,),
            )

        self.shadow_state = transition.new_state

        # Fill quantity accumulation — only for an applied, non-duplicate fill.
        new_filled = self.filled_qty
        if event.canonical_event in (ExecutionEvent.PARTIAL_FILL, ExecutionEvent.FILL):
            if event.fill_qty is not None and event.fill_qty > Decimal("0"):
                new_filled = self.filled_qty + event.fill_qty
        self.filled_qty = new_filled

        return CoordinatorOutcome(
            state=self.shadow_state,
            filled_qty=self.filled_qty,
            was_duplicate=False,
            rejected=False,
            transition=transition,
        )

    # -- reconciliation -----------------------------------------------------

    def reconcile(
        self,
        *,
        broker_event_id: str,
        broker_sequence: str,
        evidence_token: str,
    ) -> CoordinatorOutcome:
        """Reconcile an UNKNOWN (or terminal-conflicted) order toward a verified outcome.

        Reconciliation never self-selects. The verified ``evidence_token`` names
        the authoritative broker outcome (FILLED / CANCELLED / REJECTED / EXPIRED
        / UNKNOWN). Contradictory or insufficient evidence produces a conflict
        incident and a restricted (disputed) path.

        If the shadow is already terminal and the evidence contradicts it, the
        coordinator must NOT regress the state machine (terminal-absorbing, §2.5);
        it records a RECONCILIATION_CONFLICT incident and marks the execution
        disputed so no further live action proceeds on it.
        """
        key = (broker_event_id, broker_sequence)
        if key in self._seen:
            incident = self._new_incident(
                CoordinatorIncidentKind.DUPLICATE_EVENT,
                CoordinatorEvent(
                    broker_event_id=broker_event_id,
                    broker_sequence=broker_sequence,
                    canonical_event=ExecutionEvent.RECONCILE,
                    evidence=evidence_token,
                ),
                "Duplicate reconcile event identity redelivered.",
            )
            return CoordinatorOutcome(
                state=self.shadow_state,
                filled_qty=self.filled_qty,
                was_duplicate=True,
                rejected=False,
                transition=None,
                incidents=(incident,),
            )
        self._seen.add(key)

        # Contradictory evidence against an already-terminal shadow: flag dispute.
        if is_terminal(self.shadow_state):
            terminal_token = self.shadow_state.value
            if evidence_token.strip().upper() != terminal_token:
                incident = self._new_incident(
                    CoordinatorIncidentKind.RECONCILIATION_CONFLICT,
                    CoordinatorEvent(
                        broker_event_id=broker_event_id,
                        broker_sequence=broker_sequence,
                        canonical_event=ExecutionEvent.RECONCILE,
                        evidence=evidence_token,
                    ),
                    f"Reconciliation conflict: shadow={terminal_token} but "
                    f"broker evidence={evidence_token}. No self-selection; "
                    "execution marked disputed/restricted.",
                )
                self._disputed = True
                return CoordinatorOutcome(
                    state=self.shadow_state,
                    filled_qty=self.filled_qty,
                    was_duplicate=False,
                    rejected=False,
                    transition=None,
                    incidents=(incident,),
                )
            # Matching terminal evidence: no transition needed, stays terminal.
            return CoordinatorOutcome(
                state=self.shadow_state,
                filled_qty=self.filled_qty,
                was_duplicate=False,
                rejected=False,
                transition=None,
            )

        # Shadow is UNKNOWN (or reconcilable): delegate to the authority.
        try:
            transition = transition_order(
                self.shadow_state,
                ExecutionEvent.RECONCILE,
                evidence=evidence_token,
            )
        except ExecutionStateError as exc:
            incident = self._new_incident(
                CoordinatorIncidentKind.UNKNOWN_RECONCILIATION,
                CoordinatorEvent(
                    broker_event_id=broker_event_id,
                    broker_sequence=broker_sequence,
                    canonical_event=ExecutionEvent.RECONCILE,
                    evidence=evidence_token,
                ),
                f"Insufficient/contradictory evidence; rejected by authority: {exc}",
            )
            self._disputed = True
            return CoordinatorOutcome(
                state=self.shadow_state,
                filled_qty=self.filled_qty,
                was_duplicate=False,
                rejected=True,
                transition=None,
                incidents=(incident,),
            )

        self.shadow_state = transition.new_state
        if transition.dispute:
            self._disputed = True
        return CoordinatorOutcome(
            state=self.shadow_state,
            filled_qty=self.filled_qty,
            was_duplicate=False,
            rejected=False,
            transition=transition,
        )

    # -- helpers ------------------------------------------------------------

    def _new_incident(
        self,
        kind: CoordinatorIncidentKind,
        event: CoordinatorEvent,
        detail: str,
    ) -> CoordinatorIncident:
        self._incident_counter += 1
        incident = CoordinatorIncident(
            incident_id=f"INC_{self.execution_id}_{self._incident_counter}",
            kind=kind,
            execution_id=self.execution_id,
            broker_event_id=event.broker_event_id,
            broker_sequence=event.broker_sequence,
            detail=detail,
        )
        self._incidents.append(incident)
        return incident
