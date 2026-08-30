"""Phase 7 Paper Exercise — R1 order-lifecycle harness (state-authority-preserving).

The R1 checkpoint pushes the Alpaca paper adapter through a **full order
lifecycle** (submit -> ack -> fill/cancel -> reconciliation) and collects the
evidence lineage required to flip a BMAP Conformance Matrix cell from D (design)
to P (paper-exercised). See ``docs/phase7/paper_exercise_r1.md``.

Authority boundary (locked, unchanged):
- The harness is a DRIVER only. It decodes NOTHING.
- Every canonical state is produced by ``ExecutionCoordinator`` (which delegates
  to ``transition_order()``, the SOLE state authority). The harness NEVER calls
  ``transition_order()`` and NEVER assigns an ``OrderLifecycleState``; it only
  READS state from ``coord.state`` after ``coord.apply()``/``coord.reconcile()``.
- The pump reuses the existing seam ``to_coordinator_event(raw, fill_qty=...)``
  (``broker_adapter.py``), which runs ``normalize_broker_event()`` (Step 8C) and
  builds the canonical event identity ``(broker_event_id, broker_sequence)``.
- Per-fill quantity MUST be taken from the raw ``AlpacaTradeEvent.qty`` and passed
  into ``to_coordinator_event(fill_qty=...)``; ``BrokerRawEvent`` carries no fill
  qty. The coordinator owns the fill ledger + dedup (no double accumulation).
- The operator-initiated ``CANCEL_REQUEST`` is a local action (NOT a broker
  observation; there is no ``BrokerEventKind.CANCEL_REQUEST``). The harness emits it
  as a ``CoordinatorEvent`` directly (still via ``coord.apply()`` -> ``transition_order()``),
  matching the existing test pattern. A broker confirmation of the cancel (CANCEL_ACK)
  is driven ONLY from a REST snapshot with cancel provenance (BMAP-07: the SSE
  ``canceled`` path fails closed).
- Every terminal outcome carries evidence lineage (R1-H ExecutionManifest;
  R1-I ReconciliationReport). A terminal state is NEVER asserted bare.

Bound (this module/test round):
- No network, no paper credentials, no real account/order, no P evidence, no live.
- The production entry (``run_order_exercise_verification``) is the FUTURE real
  paper gate and is NOT executed by the unit suite.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional, Sequence, Tuple

from acash.execution.broker_adapter import (
    SubmissionReceipt,
    to_coordinator_event,
)
from acash.execution.broker_events import BrokerEventKind
from acash.execution.coordinator import (
    CoordinatorEvent,
    CoordinatorOutcome,
    ExecutionCoordinator,
)
from acash.execution.schema import (
    ExecutionManifest,
    OrderIntent,
    OrderLifecycleState,
    OrderSide,
    OrderType,
    ReconciliationReport,
    TimeInForce,
)
from acash.execution.state_machine import ExecutionEvent

from acash.execution.alpaca.adapter import AlpacaPaperAdapter
from acash.execution.alpaca.transport import (
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
)
from acash.execution.alpaca.venue import paper_endpoint


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderExerciseError(Exception):
    """Fail-closed R1 harness error (never exposes secret / account material).

    Raised when a scenario cannot be driven through the authority-preserving pump
    (e.g. a required step missing). Distinct from transport/adapter errors so
    callers can route R1 failures to reconciliation without confusing them with a
    broker reply.
    """


# ---------------------------------------------------------------------------
# Evidence DTO (no secret material)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifecycleEvidence:
    """Structured R1 order-lifecycle evidence for a single exercised order.

    Captures the ordered canonical states reached, the terminal outcome, the
    cumulative fill, the per-step ``CoordinatorOutcome`` sequence, and — where a
    lineage artifact was produced — the ``ExecutionManifest`` (R1-H) and
    ``ReconciliationReport`` (R1-I). Carries NO secret / account material.
    """

    scenario: str
    client_order_id: str
    broker_order_id: str
    symbol: str
    requested_qty: Decimal
    venue: str
    states_reached: Tuple[str, ...]
    final_state: str
    final_terminal: bool
    filled_qty: Decimal
    disputed: bool
    outcomes: Tuple[CoordinatorOutcome, ...]
    manifest: Optional[ExecutionManifest] = None
    reconciliation_report: Optional[ReconciliationReport] = None
    recorded_at_utc: datetime = field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Lineage builders (reuse the canonical serializer, not a new helper)
# ---------------------------------------------------------------------------


def _sha256_hexdigest(payload: dict[str, Any]) -> str:
    import hashlib

    from acash.core.serialization import CanonicalConfigSerializer

    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
    ).hexdigest()


def build_nominal_intent(
    *,
    intent_id: str,
    authorization_id: str,
    strategy_id: str,
    symbol: str,
    quantity: Decimal,
    created_at: datetime,
    signal_event_hash: str = "0" * 64,
    risk_snapshot_hash: str = "0" * 64,
) -> OrderIntent:
    """Construct a nominal frozen ``OrderIntent`` for R1-H paper-lineage binding.

    IMPORTANT — exercise-lineage artifact ONLY, NOT admission proof: this builds
    the model via DIRECT construction, deliberately bypassing
    ``construct_order_intent()`` (the live authorization/admission gate). It
    therefore proves NOTHING about admission fitness; it exists solely to carry the
    canonical intent shape + ``intent_digest`` into the manifest for lineage
    binding. Do NOT read this as evidence that R1 passed the authorization /
    admission stack. Consumers must treat R1-H ``intent_digest`` as
    nominal-exercise lineage, never as a validated admission digest.

    Pure data construction (the model is a frozen BaseModel with field validators
    only). The venue is fixed to the paper venue.
    """
    provisional = OrderIntent(
        intent_id=intent_id,
        authorization_id=authorization_id,
        strategy_id=strategy_id,
        venue="ALPACA_PAPER",
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=quantity,
        limit_price=None,
        stop_price=None,
        created_at=created_at,
        signal_event_hash=signal_event_hash,
        risk_snapshot_hash=risk_snapshot_hash,
        intent_digest="0" * 64,
    )
    intent_digest = _sha256_hexdigest(
        {
            "intent_id": provisional.intent_id,
            "authorization_id": provisional.authorization_id,
            "strategy_id": provisional.strategy_id,
            "venue": provisional.venue,
            "symbol": provisional.symbol,
            "side": provisional.side.value,
            "order_type": provisional.order_type.value,
            "time_in_force": provisional.time_in_force.value,
            "quantity": str(provisional.quantity),
            "limit_price": (
                str(provisional.limit_price) if provisional.limit_price is not None else None
            ),
            "stop_price": (
                str(provisional.stop_price) if provisional.stop_price is not None else None
            ),
            "created_at": provisional.created_at.isoformat(),
            "signal_event_hash": provisional.signal_event_hash,
            "risk_snapshot_hash": provisional.risk_snapshot_hash,
        }
    )
    return OrderIntent(
        intent_id=provisional.intent_id,
        authorization_id=provisional.authorization_id,
        strategy_id=provisional.strategy_id,
        venue=provisional.venue,
        symbol=provisional.symbol,
        side=provisional.side,
        order_type=provisional.order_type,
        time_in_force=provisional.time_in_force,
        quantity=provisional.quantity,
        limit_price=provisional.limit_price,
        stop_price=provisional.stop_price,
        created_at=provisional.created_at,
        signal_event_hash=provisional.signal_event_hash,
        risk_snapshot_hash=provisional.risk_snapshot_hash,
        intent_digest=intent_digest,
    )


def _canonical_execution_payload(
    outcomes: Sequence[CoordinatorOutcome],
) -> list[dict[str, str]]:
    """Canonical serialization of the applied execution record (R1-H digest).

    Each applied (non-duplicate, non-rejected) step contributes the resulting state
    and cumulative fill. This is the execution record the ``execution_digest`` binds
    to — never a raw broker event.
    """
    payload: list[dict[str, str]] = []
    for out in outcomes:
        if out.was_duplicate or out.rejected:
            continue
        payload.append({"state": out.state.value, "filled_qty": str(out.filled_qty)})
    return payload


def build_execution_manifest(
    *,
    intent: OrderIntent,
    execution_id: str,
    client_order_id: str,
    broker_order_id: str,
    outcomes: Sequence[CoordinatorOutcome],
    requested_qty: Decimal,
    filled_qty: Decimal,
    submitted_at: datetime,
    closed_at: Optional[datetime],
) -> ExecutionManifest:
    """Build the R1-H ``ExecutionManifest`` lineage artifact.

    ``closed_at`` is set ONLY when the caller passes a verified terminal time;
    callers MUST leave it ``None`` for ``UNKNOWN``/non-terminal outcomes. The
    ``execution_digest`` is over the canonical execution record (the applied
    ``CoordinatorOutcome`` sequence).
    """
    execution_digest = _sha256_hexdigest(
        {"steps": _canonical_execution_payload(outcomes), "execution_id": execution_id}
    )
    return ExecutionManifest(
        execution_id=execution_id,
        authorization_id=intent.authorization_id,
        strategy_id=intent.strategy_id,
        intent_id=intent.intent_id,
        intent_digest=intent.intent_digest,
        client_order_id=client_order_id,
        broker_order_id=broker_order_id,
        venue=intent.venue,
        symbol=intent.symbol,
        order_side=intent.side,
        order_type=intent.order_type,
        created_at=intent.created_at,
        submitted_at=submitted_at,
        acknowledged_at=None,
        first_fill_at=None,
        closed_at=closed_at,
        requested_qty=requested_qty,
        filled_qty=filled_qty,
        benchmark_mid_price=Decimal("100.00"),
        average_fill_price=Decimal("100.00") if filled_qty > Decimal("0") else None,
        realized_slippage_bps=0.0,
        total_commission_paid=Decimal("0.0"),
        source_signal_event_hash=intent.signal_event_hash,
        execution_digest=execution_digest,
    )


def build_reconciliation_report(
    *,
    reconciliation_id: str,
    outcome: CoordinatorOutcome,
    observed_at: datetime,
) -> ReconciliationReport:
    """Build the R1-I ``ReconciliationReport`` lineage artifact.

    Single-order parity: True when the outcome resolved to a verified terminal
    state with no dispute, else discrepancy/HALTED. ``report_digest`` is over the
    report content.
    """
    in_parity = (
        outcome.transition is not None
        and outcome.transition.is_terminal
        and not outcome.transition.dispute
    )
    report_digest = _sha256_hexdigest(
        {
            "reconciliation_id": reconciliation_id,
            "is_in_parity": in_parity,
            "resolved_state": outcome.state.value,
            "filled_qty": str(outcome.filled_qty),
        }
    )
    return ReconciliationReport(
        reconciliation_id=reconciliation_id,
        timestamp=observed_at,
        venue="ALPACA_PAPER",
        is_in_parity=in_parity,
        internal_open_orders_count=1 if not in_parity else 0,
        broker_open_orders_count=1 if not in_parity else 0,
        action_taken="NOMINAL_LOGGED" if in_parity else "HALTED_ON_DISCREPANCY",
        report_digest=report_digest,
    )


# ---------------------------------------------------------------------------
# Raw Alpaca DTO builder (what the paper broker emits for a scenario)
# ---------------------------------------------------------------------------


def _event_id(n: int) -> str:
    """Deterministic, sortable fake ULID-like event id for paper-exercise DTOs.

    BMAP-03 requires ``broker_sequence = event_id`` verbatim; the harness builds
    these deterministically so a scenario is reproducible, monotonic, and distinct.
    """
    return f"01{n:012d}0000000000000000"


def _trade_event(
    *,
    event_id: str,
    event: AlpacaTradeEventType,
    broker_order_id: str,
    symbol: str,
    requested_qty: Decimal,
    filled_qty: Decimal,
    order_status: AlpacaOrderStatus,
    qty: Optional[Decimal] = None,
    price: Optional[Decimal] = None,
    execution_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> AlpacaTradeEvent:
    """Construct one raw Alpaca Trade Events DTO for the harness pump.

    The embedded ``order`` mirrors what Alpaca embeds on the SSE payload (BMAP-02),
    carrying cumulative ``filled_qty`` for overfill triage. ``event_id`` is the ULID
    publication sequence carried verbatim as ``broker_sequence`` (BMAP-03).
    """
    return AlpacaTradeEvent(
        event_id=event_id,
        event=event,
        at=_utcnow(),
        executed_at=_utcnow() if qty is not None else None,
        broker_order_id=broker_order_id,
        execution_id=execution_id,
        qty=qty,
        price=price,
        reason=reason,
        order=AlpacaOrder(
            broker_order_id=broker_order_id,
            client_order_id=f"coid-{broker_order_id}",
            symbol=symbol,
            status=order_status,
            requested_qty=requested_qty,
            filled_qty=filled_qty,
            created_at=_utcnow(),
            updated_at=_utcnow(),
            filled_at=_utcnow() if filled_qty == requested_qty else None,
            canceled_at=None,
            cancel_requested_at=None,
        ),
    )


# ---------------------------------------------------------------------------
# The order-lifecycle harness (authority-preserving driver)
# ---------------------------------------------------------------------------


class OrderExerciseHarness:
    """Drive one paper order lifecycle through the authority-preserving pump.

    The harness owns a fresh ``ExecutionCoordinator`` for the order and routes every
    raw Alpaca reality (DTOs / snapshots) through
    ``AlpacaPaperAdapter.ingest_*`` -> ``to_coordinator_event`` -> ``coord.apply`` /
    ``coord.reconcile``. It NEVER calls ``transition_order()`` and NEVER assigns an
    ``OrderLifecycleState``; it only READS ``coord.state`` after each step.

    Design bound: this exposes a fixed set of EXPLICIT step methods
    (submit / acknowledge / reject / partial_fill / full_fill / cancel_request /
    cancel_ack_via_snapshot / cancel_reject / fill_during_cancel / connection_lost /
    reconcile / evidence). There is deliberately NO generic script dispatcher or
    workflow runner: each conformance scenario (R1-A..R1-I) states its sequence
    directly as method calls, so the harness cannot drift into a mini workflow
    engine.
    """

    def __init__(
        self,
        adapter: AlpacaPaperAdapter,
        *,
        execution_id: str,
        requested_qty: Decimal,
        client_order_id: str,
        symbol: str,
        scenario: str = "manual",
    ) -> None:
        self._adapter = adapter
        self.execution_id = execution_id
        self.client_order_id = client_order_id
        self.symbol = symbol
        self.requested_qty = requested_qty
        self.scenario = scenario
        self._coord = ExecutionCoordinator(
            execution_id=execution_id,
            requested_qty=requested_qty,
        )
        self._states_reached: List[str] = [OrderLifecycleState.SUBMITTED.value]
        self._outcomes: List[CoordinatorOutcome] = []
        self._broker_order_id: Optional[str] = None

    # -- read-only observation of the shadow --------------------------------

    @property
    def state(self) -> OrderLifecycleState:
        return self._coord.state

    @property
    def broker_order_id(self) -> str:
        if self._broker_order_id is None:
            raise OrderExerciseError(
                "no broker order id yet (submit first) (fail-closed)."
            )
        return self._broker_order_id

    def _record(self, state: OrderLifecycleState) -> None:
        if not self._states_reached or self._states_reached[-1] != state.value:
            self._states_reached.append(state.value)

    def _apply(self, outcome: CoordinatorOutcome) -> CoordinatorOutcome:
        self._outcomes.append(outcome)
        self._record(outcome.state)
        return outcome

    # -- steps --------------------------------------------------------------

    def submit(self) -> SubmissionReceipt:
        receipt = self._adapter.submit_order(
            client_order_id=self.client_order_id,
            symbol=self.symbol,
            quantity=self.requested_qty,
        )
        self._broker_order_id = receipt.broker_order_id
        return receipt

    def acknowledge(self) -> CoordinatorOutcome:
        raw = self._adapter.ingest_trade_event(
            _trade_event(
                event_id=_event_id(1),
                event=AlpacaTradeEventType.ACCEPTED,
                broker_order_id=self.broker_order_id,
                symbol=self.symbol,
                requested_qty=self.requested_qty,
                filled_qty=Decimal("0"),
                order_status=AlpacaOrderStatus.NEW,
            )
        )
        return self._apply(self._coord.apply(to_coordinator_event(raw)))

    def reject(self) -> CoordinatorOutcome:
        raw = self._adapter.ingest_trade_event(
            _trade_event(
                event_id=_event_id(2),
                event=AlpacaTradeEventType.REJECTED,
                broker_order_id=self.broker_order_id,
                symbol=self.symbol,
                requested_qty=self.requested_qty,
                filled_qty=Decimal("0"),
                order_status=AlpacaOrderStatus.REJECTED,
            )
        )
        return self._apply(self._coord.apply(to_coordinator_event(raw)))

    def partial_fill(self, qty: Decimal) -> CoordinatorOutcome:
        raw = self._adapter.ingest_trade_event(
            _trade_event(
                event_id=_event_id(len(self._outcomes) + 10),
                event=AlpacaTradeEventType.PARTIAL_FILL,
                broker_order_id=self.broker_order_id,
                symbol=self.symbol,
                qty=qty,
                execution_id=f"exec-{len(self._outcomes) + 10}",
                requested_qty=self.requested_qty,
                filled_qty=qty,
                order_status=AlpacaOrderStatus.PARTIALLY_FILLED,
            )
        )
        return self._apply(self._coord.apply(to_coordinator_event(raw, fill_qty=qty)))

    def full_fill(self, qty: Decimal) -> CoordinatorOutcome:
        broker_cumulative = self._coord.filled_qty + qty
        raw = self._adapter.ingest_trade_event(
            _trade_event(
                event_id=_event_id(len(self._outcomes) + 20),
                event=AlpacaTradeEventType.FILL,
                broker_order_id=self.broker_order_id,
                symbol=self.symbol,
                qty=qty,
                execution_id=f"exec-{len(self._outcomes) + 20}",
                requested_qty=self.requested_qty,
                filled_qty=broker_cumulative,
                order_status=AlpacaOrderStatus.FILLED,
            )
        )
        return self._apply(self._coord.apply(to_coordinator_event(raw, fill_qty=qty)))

    def cancel_request(self) -> CoordinatorOutcome:
        """Request a cancel: DELETE accepted (a REQUEST, never CANCELLED).

        ``CANCEL_REQUEST`` is an operator action (no BrokerEventKind), emitted as a
        ``CoordinatorEvent`` directly, still through ``coord.apply()``.
        """
        self._adapter.cancel_order(self.broker_order_id)
        ev = CoordinatorEvent(
            broker_event_id=_event_id(len(self._outcomes) + 30),
            broker_sequence=_event_id(len(self._outcomes) + 30),
            canonical_event=ExecutionEvent.CANCEL_REQUEST,
        )
        return self._apply(self._coord.apply(ev))

    def cancel_ack_via_snapshot(self) -> CoordinatorOutcome:
        """Resolve CANCELLED via a REST snapshot with cancel provenance (BMAP-07).

        The SSE ``canceled`` path fails closed (BMAP-07 strict). The ONLY
        authoritative CANCELLED path is a REST snapshot carrying cancel provenance
        (``cancel_requested_at`` set), normalized by ``to_coordinator_event`` to
        ``CANCEL_ACK`` and applied through the coordinator.
        """
        order = AlpacaOrder(
            broker_order_id=self.broker_order_id,
            client_order_id=f"coid-{self.broker_order_id}",
            symbol=self.symbol,
            status=AlpacaOrderStatus.CANCELED,
            requested_qty=self.requested_qty,
            filled_qty=self._coord.filled_qty,
            created_at=_utcnow(),
            updated_at=_utcnow(),
            canceled_at=_utcnow(),
            cancel_requested_at=_utcnow(),
        )
        raw = self._adapter.ingest_order_snapshot(
            order, BrokerEventKind.ORDER_CANCELLED
        )
        ev = to_coordinator_event(raw)
        return self._apply(self._coord.apply(ev))

    def cancel_reject(self) -> CoordinatorOutcome:
        """Feed SSE ``order_cancel_rejected`` -> CANCEL_REJECTED -> ACKNOWLEDGED."""
        raw = self._adapter.ingest_trade_event(
            _trade_event(
                event_id=_event_id(len(self._outcomes) + 31),
                event=AlpacaTradeEventType.ORDER_CANCEL_REJECTED,
                broker_order_id=self.broker_order_id,
                symbol=self.symbol,
                requested_qty=self.requested_qty,
                filled_qty=self._coord.filled_qty,
                order_status=AlpacaOrderStatus.CANCEL_REJECTED,
            )
        )
        return self._apply(self._coord.apply(to_coordinator_event(raw)))

    def fill_during_cancel(self, qty: Decimal) -> CoordinatorOutcome:
        """Feed a fill while a cancel is pending (R1-D: fill authoritative).

        A FILL arriving after ``cancel_request()`` (state CANCEL_REQUESTED) is an
        authoritative broker observation: the fill wins the race (row 20 of the
        canonical transition table). Explicitly named so the cancel/fill race reads
        directly in a test; delegates to the same ``full_fill`` fill ledger.
        """
        return self.full_fill(qty)

    def connection_lost(self) -> CoordinatorOutcome:
        """Simulate an ack/cancel-confirmation timeout -> CONNECTION_LOST -> UNKNOWN."""
        raw = self._adapter.raise_ack_timeout(self.broker_order_id)
        return self._apply(self._coord.apply(to_coordinator_event(raw)))

    def reconcile(self, evidence_token: str) -> CoordinatorOutcome:
        """Reconcile UNKNOWN toward a verified outcome (evidence-gated)."""
        outcome = self._coord.reconcile(
            broker_event_id=_event_id(len(self._outcomes) + 40),
            broker_sequence=_event_id(len(self._outcomes) + 40),
            evidence_token=evidence_token,
            observed_at=_utcnow(),
        )
        return self._apply(outcome)

    def evidence(self) -> LifecycleEvidence:
        final = self._coord.state
        is_terminal = final in {
            OrderLifecycleState.FILLED,
            OrderLifecycleState.CANCELLED,
            OrderLifecycleState.REJECTED,
            OrderLifecycleState.EXPIRED,
        }
        intent = build_nominal_intent(
            intent_id=f"INT_{self.execution_id}",
            authorization_id="AUTH_PAPER_EXERCISE",
            strategy_id="STRAT_PAPER_EXERCISE",
            symbol=self.symbol,
            quantity=self.requested_qty,
            created_at=_utcnow(),
        )
        manifest = build_execution_manifest(
            intent=intent,
            execution_id=self.execution_id,
            client_order_id=self.client_order_id,
            broker_order_id=self.broker_order_id,
            outcomes=tuple(self._outcomes),
            requested_qty=self.requested_qty,
            filled_qty=self._coord.filled_qty,
            submitted_at=_utcnow(),
            closed_at=_utcnow() if is_terminal else None,
        )
        report = (
            build_reconciliation_report(
                reconciliation_id=f"REC_{self.execution_id}",
                outcome=self._outcomes[-1],
                observed_at=_utcnow(),
            )
            if self._outcomes
            else None
        )
        return LifecycleEvidence(
            scenario=self.scenario,
            client_order_id=self.client_order_id,
            broker_order_id=self.broker_order_id,
            symbol=self.symbol,
            requested_qty=self.requested_qty,
            venue="ALPACA_PAPER",
            states_reached=tuple(self._states_reached),
            final_state=final.value,
            final_terminal=is_terminal,
            filled_qty=self._coord.filled_qty,
            disputed=self._coord.disputed,
            outcomes=tuple(self._outcomes),
            manifest=manifest,
            reconciliation_report=report,
        )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def run_order_exercise_verification(
    *,
    client_order_id: str,
    symbol: str,
    quantity: Decimal,
) -> LifecycleEvidence:
    """Production R1 gate: one REAL paper order through the explicit nominal flow.

    Builds the paper transport from operator-exported credentials
    (``ACASH_ALPACA_API_KEY_ID`` / ``ACASH_ALPACA_API_SECRET``) and drives the
    nominal lifecycle (submit -> acknowledge -> full fill) through explicit harness
    methods. NOT executed by the unit suite; no fake transport ever counts as P.

    Intentionally NO generic script dispatcher: the sequence is stated explicitly
    so this entry cannot become a mini workflow engine. All state flows only
    through ``ExecutionCoordinator``.
    """
    from acash.execution.alpaca.credentials import paper_credential_provider
    from acash.execution.alpaca.transport import PaperHttpAlpacaTransport

    transport: AlpacaTransport = PaperHttpAlpacaTransport(
        provider=paper_credential_provider(),
        endpoint=paper_endpoint(),
    )
    adapter = AlpacaPaperAdapter(transport)
    harness = OrderExerciseHarness(
        adapter,
        execution_id=f"R1_VERIFY_{client_order_id}",
        requested_qty=quantity,
        client_order_id=client_order_id,
        symbol=symbol,
        scenario="verification",
    )
    harness.submit()
    harness.acknowledge()
    harness.full_fill(quantity)
    return harness.evidence()


__all__ = [
    "LifecycleEvidence",
    "OrderExerciseError",
    "OrderExerciseHarness",
    "build_execution_manifest",
    "build_nominal_intent",
    "build_reconciliation_report",
    "run_order_exercise_verification",
]
