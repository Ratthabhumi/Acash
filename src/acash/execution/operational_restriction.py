"""Phase 7 Operational Boundary implementation: the Risk/Restriction Authority.

Implements the frozen Operational Boundary Contract (`.omc/phase7_operational
_boundary_contract.md`, approved). This module is the **Risk / Restriction
Authority** — the explicit OWNER of the OperationalRestriction lifecycle.

Enforced separation (locked):
    Order State != Evidence State != Operational Restriction != Live Authorization

    Coordinator                          (detect + request only, NEVER lifecycle owner)
    Risk/Restriction Authority           (THIS module: OPEN / ENFORCE / CLEAR)
    transition_order()                   (sole order-state authority)

Canonical data authority (architecture):
    Canonical Restriction Ledger  <- single source of truth, owned by composition root
        ^ (required, injected)
    RiskRestrictionAuthority      <- lifecycle/query facade ONLY
        | gate_for_intent()
        v
    Admission enforcement
        v
    OrderIntent

Provenance contract (frozen, operational):
- The authority MUST be bound to a ``RestrictionLedger``; it never silently owns a
  private empty store and never constructs a ledger internally. ``gate_for_intent()``
  reads exclusively from the bound ledger. This closes the *default-empty / omitted
  snapshot* fail-open: there is no code path where a caller "forgets" to supply a
  store, and no store is fabricated implicitly.
- WHAT THE CONSTRUCTOR DOES NOT PROVE: a caller can still create
  ``RiskRestrictionAuthority(RestrictionLedger())`` with a freshly-created empty
  ledger. That is an *honest empty* (no restrictions exist in that ledger) but it is
  NOT the production store. Canonical provenance — that the admission path reads the
  same ledger the application owns and seeds — is therefore NOT proven by the
  constructor alone. It is an application-composition invariant (see below).
- DEPLOYMENT / COMPOSITION INVARIANT (governance, not provable by code here):
  there is currently NO production composition root in the codebase, and NO
  production call site constructs ``RiskRestrictionAuthority`` or
  ``RestrictionLedger``. Production MUST wire a single application-owned
  ``Canonical RestrictionLedger`` at the composition root, bind exactly one
  ``RiskRestrictionAuthority`` to it, and inject that authority into
  ``construct_order_intent``. No production path may construct an isolated
  authority/ledger. Unit tests MAY create isolated ledgers; they must not be
  substituted into the production admission path.

Rules enforced here (from contract §3, §4, §5):
- The coordinator MUST NOT OPEN/CLEAR a restriction or decide risk policy. It
  only emits an ``OperationalRestrictionRequest`` (with evidence lineage).
- Clearing a restriction requires BOTH verified evidence AND an authorized
  recovery decision (``RestrictionClearPolicy``). Verified evidence alone does
  NOT clear (no auto-clear from broker/evidence parity).
- ``Clear Restriction != Reauthorize Live Trading``. Clearing here never flips
  a ``SUSPENDED``/``REVOKED`` authorization to ``ACTIVE``; that is a separate
  authorization reactivation lifecycle (existing reactivation quorum), handled
  by the admission/authorization layer, not this module.
- N-of-M quorum is NOT required for a transient restriction clear (the clear
  policy is an authorized decision; quorum is only for authorization
  reactivation).
- An OPEN restriction blocks new order admission (enforced by the admission
  gate in ``admission.construct_order_intent``).

Boundary: this module is a restriction authority, NOT a full risk engine. It does
not do VaR / CVaR / kill-switch / position sizing / market regime. Those stay in
the existing RiskState / KillSwitch controls. ``RestrictionAuthority != RiskEngine``.

This module is pure (no I/O, no clock). All timestamps are supplied by callers.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple

from acash.core.domain.exceptions import DomainValidationError


class RestrictionScope(str, Enum):
    """The operational scope a restriction applies to."""

    STRATEGY = "STRATEGY"
    AUTHORIZATION = "AUTHORIZATION"
    EXECUTION = "EXECUTION"


class RestrictionReason(str, Enum):
    """Canonical reason for an operational restriction."""

    RECONCILIATION_CONFLICT = "RECONCILIATION_CONFLICT"
    ORDER_STATE_UNKNOWN = "ORDER_STATE_UNKNOWN"
    STALE_RISK = "STALE_RISK"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"


class OperationalRestrictionStatus(str, Enum):
    """Lifecycle of an operational restriction."""

    OPEN = "OPEN"
    CLEARED = "CLEARED"


class OperationalRestrictionError(DomainValidationError):
    """Fail-closed error from the restriction authority."""


@dataclass(frozen=True)
class OperationalRestrictionRequest:
    """What the coordinator emits to request a restriction (NO status mutation).

    This is the only thing a non-authority component may produce. It carries the
    full evidence lineage so the risk authority (and any later auditor) can
    answer "why was this order/strategy blocked, and what did the broker say".
    """

    request_id: str
    scope: RestrictionScope
    reason: RestrictionReason
    strategy_id: Optional[str] = None
    authorization_id: Optional[str] = None
    execution_id: Optional[str] = None
    order_id: Optional[str] = None
    evidence_refs: Tuple[str, ...] = ()          # ReconciliationEvidence digests
    shadow_state: Optional[str] = None            # order state at detection
    broker_observed_state: Optional[str] = None   # evidence-observed broker state
    source: str = "EXECUTION_COORDINATOR"
    observed_at: Optional[datetime] = None
    created_by: str = "coordinator"
    detail: str = ""


@dataclass(frozen=True)
class OperationalRestriction:
    """First-class, lineage-carrying operational restriction (proposal §5).

    ``status`` is lifecycle-owned by the Risk/Restriction Authority. Non-authority
    code MUST treat it as read-only and NEVER construct it with a non-OPEN status
    or mutate its lifecycle.
    """

    restriction_id: str
    scope: RestrictionScope
    reason: RestrictionReason
    strategy_id: Optional[str] = None
    authorization_id: Optional[str] = None
    execution_id: Optional[str] = None
    order_id: Optional[str] = None
    evidence_refs: Tuple[str, ...] = ()
    shadow_state: Optional[str] = None
    broker_observed_state: Optional[str] = None
    source: str = "EXECUTION_COORDINATOR"
    observed_at: Optional[datetime] = None
    created_by: str = "coordinator"
    status: OperationalRestrictionStatus = OperationalRestrictionStatus.OPEN
    # Clear lineage (populated only by the authority on CLEARED)
    cleared_by: Optional[str] = None
    cleared_at: Optional[datetime] = None
    cleared_evidence_refs: Tuple[str, ...] = ()
    clear_decision_note: str = ""


@dataclass(frozen=True)
class RestrictionClearDecision:
    """The authorized decision to clear (or not) a restriction."""

    authorized: bool
    actor_id: Optional[str] = None
    decision_note: str = ""


class RestrictionClearPolicy:
    """Policy hook that yields the AUTHORIZED recovery decision.

    Implementers evaluate whether, given verified evidence, the system/actor is
    permitted to re-open. This is the safeguard against "broker says OK -> auto
    clear". It is NOT a quorum gate for transient clears; it is an authorization
    decision. Reauthorizing a suspended live authorization remains the job of the
    authorization reactivation lifecycle (quorum), NOT this policy.

    `is_evidence_verified` and `decide` are SEPARATE gates. Evidence verification
    alone can NEVER clear; the authorized decision is mandatory.
    """

    def is_evidence_verified(self, restriction: OperationalRestriction) -> bool:
        """Return True when the conflict's reconciliation evidence is verified.

        Fail-closed default is True because verification is done upstream; the
        authorization gate remains the required second condition. Implementers
        MAY tighten this. Evidence verification alone never clears.
        """
        return True

    def decide(
        self,
        *,
        restriction: OperationalRestriction,
        evidence_refs: Tuple[str, ...],
        actor_id: str,
    ) -> RestrictionClearDecision:
        """Return the authorized clear decision.

        Default (fail-closed): NOT authorized. Production MUST provide a concrete
        policy; absence fails closed and never auto-approves.
        """
        return RestrictionClearDecision(
            authorized=False,
            actor_id=actor_id,
            decision_note="fail-closed: no policy supplied",
        )


class RestrictionLedger:
    """Canonical, single-owner store of ``OperationalRestriction`` records.

    This is the **data authority** for operational restrictions. It is created
    and owned by the application composition root (not by order-issuing callers).
    ``RiskRestrictionAuthority`` is bound to exactly one ledger and reads/writes
    exclusively through it, so the admission gate always consults the same
    canonical source that production populates.
    """

    def __init__(self) -> None:
        self._restrictions: dict[str, OperationalRestriction] = {}

    def record(self, restriction: OperationalRestriction) -> None:
        """Record (create/replace by id) a restriction in the canonical ledger."""
        self._restrictions[restriction.restriction_id] = restriction

    def get(self, restriction_id: str) -> Optional[OperationalRestriction]:
        return self._restrictions.get(restriction_id)

    def all(self) -> Tuple[OperationalRestriction, ...]:
        return tuple(self._restrictions.values())


class RiskRestrictionAuthority:
    """Owner of the OperationalRestriction lifecycle (OPEN / CLEAR).

    This authority is bound to a canonical ``RestrictionLedger`` (REQUIRED, no
    default empty store). It is the ONLY component permitted to set ``status`` on
    a restriction. It enforces:
    - OPEN:  accepts a request (produced by the coordinator) and emits an OPEN
             restriction into the canonical ledger.
    - CLEAR: requires evidence verified AND an authorized decision; never
             auto-clears on evidence alone; never reactivates an authorization.
    - QUERY: ``gate_for_intent`` reads ONLY from the bound ledger, so a caller
             cannot fabricate an empty authority to bypass admission.

    The authority is NOT a risk engine: it does no VaR/kill-switch/sizing/market
    regime. Those remain in the existing RiskState/KillSwitch controls.
    """

    def __init__(
        self,
        ledger: RestrictionLedger,
        clear_policy: Optional[RestrictionClearPolicy] = None,
    ) -> None:
        self._ledger = ledger
        self._counter = 0
        self._clear_policy = clear_policy or RestrictionClearPolicy()

    @property
    def ledger(self) -> RestrictionLedger:
        """The canonical ledger this authority is bound to (read-only handle)."""
        return self._ledger

    # -- state access (read from canonical ledger only) ---------------------

    def get(self, restriction_id: str) -> Optional[OperationalRestriction]:
        return self._ledger.get(restriction_id)

    def all(self) -> Tuple[OperationalRestriction, ...]:
        return self._ledger.all()

    def open_for_scope(
        self, scope: RestrictionScope, scope_id: str
    ) -> Tuple[OperationalRestriction, ...]:
        """Return OPEN restrictions matching ``scope`` for target ``scope_id``.

        Matching semantics by scope:
        - EXECUTION:      ``execution_id == scope_id``
        - AUTHORIZATION:  ``authorization_id == scope_id``
        - STRATEGY:       ``strategy_id == scope_id``
        """
        out = []
        for r in self._ledger.all():
            if r.status is not OperationalRestrictionStatus.OPEN:
                continue
            if r.scope is RestrictionScope.EXECUTION and r.execution_id == scope_id:
                out.append(r)
            elif r.scope is RestrictionScope.AUTHORIZATION and r.authorization_id == scope_id:
                out.append(r)
            elif r.scope is RestrictionScope.STRATEGY and r.strategy_id == scope_id:
                out.append(r)
        return tuple(out)

    def has_open(self, scope: RestrictionScope, scope_id: str) -> bool:
        return bool(self.open_for_scope(scope, scope_id))

    def gate_for_intent(
        self, *, strategy_id: str, authorization_id: str
    ) -> RestrictionAdmissionGate:
        """Return the authoritative OPEN-restriction snapshot for an order intent.

        Enforces the formal ``Applies`` predicate and includes only OPEN
        restrictions. ``CLEARED``/non-OPEN restrictions have no effect.

            Applies(r, strategy_id, authorization_id) =
                (r.scope = STRATEGY      and r.strategy_id      = strategy_id)      or
                (r.scope = AUTHORIZATION and r.authorization_id = authorization_id)

        Reads exclusively from the canonical ledger. This is the ONLY admission
        gate the admission layer may rely on.
        """
        matched = []
        for r in self._ledger.all():
            if r.status is not OperationalRestrictionStatus.OPEN:
                continue
            if r.scope is RestrictionScope.STRATEGY and r.strategy_id == strategy_id:
                matched.append(r)
            elif (
                r.scope is RestrictionScope.AUTHORIZATION
                and r.authorization_id == authorization_id
            ):
                matched.append(r)
        return RestrictionAdmissionGate(tuple(matched))

    # -- OPEN (authority-only) ----------------------------------------------

    def open_restriction(
        self, request: OperationalRestrictionRequest
    ) -> OperationalRestriction:
        """OPEN a restriction from a coordinator/risk request (authority-only)."""
        if not request.request_id or not request.request_id.strip():
            raise OperationalRestrictionError("request_id must be non-empty")
        self._counter += 1
        restriction_id = f"IR_{request.request_id}_{self._counter}"
        restriction = OperationalRestriction(
            restriction_id=restriction_id,
            scope=request.scope,
            reason=request.reason,
            strategy_id=request.strategy_id,
            authorization_id=request.authorization_id,
            execution_id=request.execution_id,
            order_id=request.order_id,
            evidence_refs=request.evidence_refs,
            shadow_state=request.shadow_state,
            broker_observed_state=request.broker_observed_state,
            source=request.source,
            observed_at=request.observed_at,
            created_by=request.created_by,
            status=OperationalRestrictionStatus.OPEN,
        )
        self._ledger.record(restriction)
        return restriction

    # -- CLEAR (authority-only) ---------------------------------------------

    def clear_restriction(
        self,
        *,
        restriction_id: str,
        actor_id: str,
        evidence_refs: Tuple[str, ...] = (),
        cleared_at: Optional[datetime] = None,
    ) -> OperationalRestriction:
        """CLEAR an OPEN restriction, requiring evidence verified + authorized decision.

        Fail-closed: does NOT clear if (a) evidence is not verified, or (b) the
        clear policy does not authorize. Never auto-clears on evidence alone.
        Returns the CLEARED restriction; raises on failure to clear.
        """
        restriction = self._ledger.get(restriction_id)
        if restriction is None:
            raise OperationalRestrictionError(
                f"Unknown restriction_id '{restriction_id}'."
            )
        if restriction.status is not OperationalRestrictionStatus.OPEN:
            raise OperationalRestrictionError(
                f"Restriction {restriction_id} is already {restriction.status.value}; "
                "only OPEN restrictions can be cleared."
            )

        if not self._clear_policy.is_evidence_verified(restriction):
            raise OperationalRestrictionError(
                f"Cannot clear {restriction_id}: reconciliation evidence is not "
                "verified. Fail-closed: no evidence, no clear."
            )

        decision = self._clear_policy.decide(
            restriction=restriction,
            evidence_refs=evidence_refs,
            actor_id=actor_id,
        )
        if not decision.authorized:
            raise OperationalRestrictionError(
                f"Cannot clear {restriction_id}: recovery is NOT authorized by "
                f"policy for actor '{actor_id}'. Verified evidence alone does not "
                "clear; an authorized recovery decision is required. "
                f"({decision.decision_note})"
            )

        cleared = replace(
            restriction,
            status=OperationalRestrictionStatus.CLEARED,
            cleared_by=decision.actor_id,
            cleared_at=cleared_at,
            cleared_evidence_refs=evidence_refs,
            clear_decision_note=decision.decision_note,
        )
        self._ledger.record(cleared)
        return cleared


@dataclass(frozen=True)
class RestrictionAdmissionGate:
    """Authority-derived, deterministic snapshot of OPEN restrictions for an intent.

    This is an **internal projection** produced only by ``RiskRestrictionAuthority``;
    it is NOT a public input to ``construct_order_intent`` (a caller-fabricated
    empty gate could bypass admission). Construction of a gate is restricted to
    the authority so it can never diverge from the canonical ledger.
    """

    restrictions: Tuple[OperationalRestriction, ...] = ()

    def is_blocked(self) -> bool:
        return bool(self.restrictions)

    def block_reason(self) -> Optional[str]:
        if not self.restrictions:
            return None
        ids = ", ".join(r.restriction_id for r in self.restrictions)
        return f"{len(self.restrictions)} OPEN operational restriction(s): {ids}"
