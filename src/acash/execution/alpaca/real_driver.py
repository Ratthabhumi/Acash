"""Phase 7 R1-REAL Broker-Observed Order Lifecycle Driver (Authority-Preserving).

Implements the R1-REAL Driver Contract (``docs/phase7/r1_real_driver_contract.md``).
Observes execution state exclusively from authoritative broker channels:
- Channel A (Primary): Real-time Trade Events SSE stream (``/v2/events/trades``).
- Channel B (Recovery / Reconciliation): Authoritative REST order snapshot polling (``/v2/orders/{id}``).

Authority & Provenance Boundaries (Non-negotiable):
1. ZERO synthetic event injections (no synthetic acknowledge / full_fill in runtime path).
2. ExecutionCoordinator is the SOLE state transition authority (delegating to transition_order()).
3. The driver is an observation pump only; it decodes nothing and assigns no states directly.
4. Timeout in non-terminal state transitions fail-closed to CONNECTION_LOST -> UNKNOWN.
5. Reconciliation is evidence-gated against authoritative broker snapshots.
6. REST aggregate evidence != SSE per-fill evidence (execution_id is None on REST-only path).
7. Economics provenance: average_fill_price is computed from observed SSE fills (VWAP) or
   extracted from broker.filled_avg_price; NEVER falls back to benchmark_mid_price or magic numbers.
8. BMAP-07 cancellation provenance: unexpected broker cancellations are routed to reconciliation
   without fabricating synthetic CANCEL_REQUEST events.
9. closed_at is derived strictly from authoritative broker terminal timestamps (filled_at /
   canceled_at / updated_at / terminal SSE event timestamp), NEVER from local _utcnow().
10. Exception boundaries: broad exception swallowing is forbidden; only expected transport
    retries / timeouts are caught during observation polling.
11. Identity Classification:
    - Broker Event Ordering: event.event_id (ULID from SSE).
    - Local Observation Sequence: LOCAL-FB-* (adapter fallback counter).
    - Local Reconciliation Identity: LOCAL-REC-EVT-* / LOCAL-REC-SEQ-* (never labeled as broker ordering).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import time
from typing import Any, List, Optional, Sequence, Tuple

from acash.execution.broker_adapter import (
    BrokerOrderReality,
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
    AlpacaTransportError,
    AlpacaTransportTimeoutError,
)
from acash.execution.alpaca.venue import paper_endpoint


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_hexdigest(payload: dict[str, Any]) -> str:
    import hashlib

    from acash.core.serialization import CanonicalConfigSerializer

    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
    ).hexdigest()


class R1RealDriverError(Exception):
    """Fail-closed error raised when broker observation invariants are violated."""


@dataclass(frozen=True)
class RealDriverEvidence:
    """Structured R1-REAL order-lifecycle evidence for a broker-observed execution.

    Carries NO secret / credential material.
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


class R1RealOrderExerciseDriver:
    """Production R1-REAL driver: observes real broker execution without synthetic pumps."""

    def __init__(
        self,
        adapter: AlpacaPaperAdapter,
        *,
        transport: Optional[AlpacaTransport] = None,
        execution_id_prefix: str = "R1_REAL",
    ) -> None:
        self._adapter = adapter
        self._transport = transport or adapter.transport
        self._execution_id_prefix = execution_id_prefix

    def submit_and_observe(
        self,
        *,
        client_order_id: str,
        symbol: str,
        quantity: Decimal,
        benchmark_mid_price: Decimal,
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.5,
    ) -> RealDriverEvidence:
        """Submit a single order and observe its real broker lifecycle fail-closed."""
        if quantity <= Decimal("0"):
            raise R1RealDriverError(f"quantity must be positive, got: {quantity}")
        if benchmark_mid_price is None or benchmark_mid_price <= Decimal("0"):
            raise R1RealDriverError(
                f"benchmark_mid_price must be a positive Decimal from pre-submission snapshot, got: {benchmark_mid_price}"
            )

        execution_id = f"{self._execution_id_prefix}_{client_order_id}"
        coord = ExecutionCoordinator(
            execution_id=execution_id,
            requested_qty=quantity,
        )
        states_reached: list[str] = [coord.state.value]
        outcomes: list[CoordinatorOutcome] = []
        sse_fills: list[Tuple[Decimal, Decimal]] = []  # (qty, price)
        sse_terminal_at: Optional[datetime] = None

        def _apply_outcome(outcome: CoordinatorOutcome) -> None:
            outcomes.append(outcome)
            if not states_reached or states_reached[-1] != outcome.state.value:
                states_reached.append(outcome.state.value)

        # 1. Connect Transport (paper-only assertion)
        self._transport.connect()

        # 2. Wire Submit (Real HTTP POST -> SubmissionReceipt)
        # Timing provenance: submitted_at_utc records local socket transit time
        submitted_at_utc = _utcnow()
        receipt = self._adapter.submit_order(
            client_order_id=client_order_id,
            symbol=symbol,
            quantity=quantity,
        )
        broker_order_id = receipt.broker_order_id
        if not broker_order_id:
            raise R1RealDriverError("submit response missing broker order id (fail-closed).")

        start_time = time.monotonic()
        observed_terminal = False

        # 3. Observation Loop (SSE primary cursor / REST polling recovery)
        while time.monotonic() - start_time < timeout_seconds:
            # Check terminal absorbing state
            if coord.state in {
                OrderLifecycleState.FILLED,
                OrderLifecycleState.CANCELLED,
                OrderLifecycleState.REJECTED,
                OrderLifecycleState.EXPIRED,
            }:
                observed_terminal = True
                break

            # Try reading Trade Events SSE stream
            try:
                stream = self._adapter.stream_trade_events()
                for trade_event in stream:
                    if trade_event.broker_order_id != broker_order_id:
                        continue
                    if trade_event.event in {AlpacaTradeEventType.FILL, AlpacaTradeEventType.PARTIAL_FILL}:
                        if trade_event.qty is not None and trade_event.price is not None:
                            sse_fills.append((trade_event.qty, trade_event.price))
                    raw_event = self._adapter.ingest_trade_event(trade_event)
                    coord_event = to_coordinator_event(raw_event, fill_qty=trade_event.qty)
                    outcome = coord.apply(coord_event)
                    _apply_outcome(outcome)
                    if outcome.transition and outcome.transition.is_terminal:
                        observed_terminal = True
                        sse_terminal_at = trade_event.executed_at or trade_event.at
                        break
            except (AlpacaTransportTimeoutError, AlpacaTransportError):
                # Expected stream disconnect / timeout -> fall back to REST polling
                pass

            if observed_terminal:
                break

            # Query authoritative REST snapshot for state progress / recovery
            try:
                broker_order = self._transport.query_order(broker_order_id)
                if broker_order.status in {AlpacaOrderStatus.NEW, AlpacaOrderStatus.ACCEPTED, AlpacaOrderStatus.PENDING_NEW}:
                    if coord.state == OrderLifecycleState.SUBMITTED:
                        raw_ack = self._adapter.ingest_order_snapshot(broker_order, BrokerEventKind.ACK)
                        _apply_outcome(coord.apply(to_coordinator_event(raw_ack)))
                elif broker_order.status == AlpacaOrderStatus.PARTIALLY_FILLED:
                    if coord.state == OrderLifecycleState.SUBMITTED:
                        raw_ack = self._adapter.ingest_order_snapshot(broker_order, BrokerEventKind.ACK)
                        _apply_outcome(coord.apply(to_coordinator_event(raw_ack)))
                    if broker_order.filled_qty > coord.filled_qty:
                        fill_increment = broker_order.filled_qty - coord.filled_qty
                        raw_pf = self._adapter.ingest_order_snapshot(broker_order, BrokerEventKind.PARTIAL_FILL)
                        _apply_outcome(coord.apply(to_coordinator_event(raw_pf, fill_qty=fill_increment)))
                elif broker_order.status == AlpacaOrderStatus.FILLED:
                    if coord.state == OrderLifecycleState.SUBMITTED:
                        raw_ack = self._adapter.ingest_order_snapshot(broker_order, BrokerEventKind.ACK)
                        _apply_outcome(coord.apply(to_coordinator_event(raw_ack)))
                    fill_increment = broker_order.filled_qty - coord.filled_qty
                    raw_fill = self._adapter.ingest_order_snapshot(broker_order, BrokerEventKind.FILLED)
                    _apply_outcome(coord.apply(to_coordinator_event(raw_fill, fill_qty=fill_increment)))
                    observed_terminal = True
                    break
                elif broker_order.status == AlpacaOrderStatus.CANCELED:
                    if coord.state == OrderLifecycleState.CANCEL_REQUESTED:
                        # User-initiated cancel in flight (BMAP-07 proven): normalizes to CANCEL_ACK
                        raw_cancel = self._adapter.ingest_order_snapshot(broker_order, BrokerEventKind.ORDER_CANCELLED)
                        _apply_outcome(coord.apply(to_coordinator_event(raw_cancel)))
                        observed_terminal = True
                        break
                    else:
                        # Unexpected broker cancellation without in-flight user cancel (BMAP-07):
                        # Drive to UNKNOWN via ambiguity if not already in UNKNOWN, then reconcile toward CANCELLED
                        # using verified broker snapshot evidence refs.
                        if coord.state not in {OrderLifecycleState.UNKNOWN, OrderLifecycleState.CANCEL_REQUESTED}:
                            raw_ambiguity = self._adapter.raise_ack_timeout(broker_order_id)
                            _apply_outcome(coord.apply(to_coordinator_event(raw_ambiguity)))
                        recon_outcome = coord.reconcile(
                            broker_event_id=f"LOCAL-REC-EVT-{broker_order_id}-cancel",
                            broker_sequence=f"LOCAL-REC-SEQ-{broker_order_id}",
                            evidence_token="CANCELLED",
                            order_id=broker_order_id,
                            observed_at=broker_order.canceled_at or broker_order.updated_at,
                            evidence_refs=(
                                f"broker_order_id:{broker_order.broker_order_id}",
                                f"broker_status:{broker_order.status.value}",
                                f"broker_canceled_at:{broker_order.canceled_at.isoformat() if broker_order.canceled_at else 'none'}",
                            ),
                        )
                        _apply_outcome(recon_outcome)
                        observed_terminal = True
                        break
                elif broker_order.status == AlpacaOrderStatus.REJECTED:
                    raw_rej = self._adapter.ingest_order_snapshot(broker_order, BrokerEventKind.REJECT)
                    _apply_outcome(coord.apply(to_coordinator_event(raw_rej)))
                    observed_terminal = True
                    break
                elif broker_order.status == AlpacaOrderStatus.EXPIRED:
                    raw_exp = self._adapter.ingest_order_snapshot(broker_order, BrokerEventKind.EXPIRED)
                    _apply_outcome(coord.apply(to_coordinator_event(raw_exp)))
                    observed_terminal = True
                    break
            except AlpacaTransportError:
                # Intermittent network error during polling -> continue loop until timeout
                pass

            time.sleep(poll_interval_seconds)

        # 4. Timeout Handling in Non-Terminal State -> Fail-Closed to UNKNOWN
        if not observed_terminal and coord.state not in {
            OrderLifecycleState.FILLED,
            OrderLifecycleState.CANCELLED,
            OrderLifecycleState.REJECTED,
            OrderLifecycleState.EXPIRED,
        }:
            raw_timeout = self._adapter.raise_ack_timeout(broker_order_id)
            _apply_outcome(coord.apply(to_coordinator_event(raw_timeout)))

            # Perform final post-timeout query for evidence-gated resolution
            try:
                broker_order = self._transport.query_order(broker_order_id)
                if broker_order.status == AlpacaOrderStatus.FILLED and broker_order.filled_qty == quantity:
                    _apply_outcome(
                        coord.reconcile(
                            broker_event_id=f"LOCAL-REC-EVT-{broker_order_id}-timeout-fill",
                            broker_sequence=f"LOCAL-REC-SEQ-{broker_order_id}",
                            evidence_token="FILLED",
                            order_id=broker_order_id,
                            observed_at=broker_order.filled_at or broker_order.updated_at,
                            evidence_refs=(
                                f"broker_order_id:{broker_order.broker_order_id}",
                                f"broker_status:{broker_order.status.value}",
                                f"broker_filled_qty:{broker_order.filled_qty}",
                            ),
                        )
                    )
                elif broker_order.status == AlpacaOrderStatus.CANCELED:
                    _apply_outcome(
                        coord.reconcile(
                            broker_event_id=f"LOCAL-REC-EVT-{broker_order_id}-timeout-cancel",
                            broker_sequence=f"LOCAL-REC-SEQ-{broker_order_id}",
                            evidence_token="CANCELLED",
                            order_id=broker_order_id,
                            observed_at=broker_order.canceled_at or broker_order.updated_at,
                            evidence_refs=(
                                f"broker_order_id:{broker_order.broker_order_id}",
                                f"broker_status:{broker_order.status.value}",
                                f"broker_canceled_at:{broker_order.canceled_at.isoformat() if broker_order.canceled_at else 'none'}",
                            ),
                        )
                    )
            except AlpacaTransportError:
                # Ambiguity remains UNKNOWN
                pass

        # 5. Final Authoritative REST Reconciliation & Parity Verification
        final_state = coord.state
        is_terminal = final_state in {
            OrderLifecycleState.FILLED,
            OrderLifecycleState.CANCELLED,
            OrderLifecycleState.REJECTED,
            OrderLifecycleState.EXPIRED,
        }

        # Query broker snapshot for reconciliation
        broker_snapshot: Optional[AlpacaOrder] = None
        try:
            broker_snapshot = self._transport.query_order(broker_order_id)
        except AlpacaTransportError:
            broker_snapshot = None

        in_parity = False
        if broker_snapshot is not None and is_terminal and not coord.disputed:
            if final_state == OrderLifecycleState.FILLED:
                in_parity = (
                    broker_snapshot.status == AlpacaOrderStatus.FILLED
                    and broker_snapshot.filled_qty == quantity
                    and coord.filled_qty == quantity
                )
            elif final_state == OrderLifecycleState.CANCELLED:
                in_parity = (
                    broker_snapshot.status == AlpacaOrderStatus.CANCELED
                    and broker_snapshot.filled_qty == coord.filled_qty
                )
            elif final_state == OrderLifecycleState.REJECTED:
                in_parity = broker_snapshot.status == AlpacaOrderStatus.REJECTED
            elif final_state == OrderLifecycleState.EXPIRED:
                in_parity = broker_snapshot.status == AlpacaOrderStatus.EXPIRED

        reconciliation_id = f"REC_{self._execution_id_prefix}_{client_order_id}"
        rec_payload = {
            "reconciliation_id": reconciliation_id,
            "is_in_parity": in_parity,
            "resolved_state": final_state.value,
            "filled_qty": str(coord.filled_qty),
        }
        report_digest = _sha256_hexdigest(rec_payload)
        reconciliation_report = ReconciliationReport(
            reconciliation_id=reconciliation_id,
            timestamp=_utcnow(),
            venue="ALPACA_PAPER",
            is_in_parity=in_parity,
            internal_open_orders_count=0 if is_terminal else 1,
            broker_open_orders_count=0 if (broker_snapshot and broker_snapshot.status in {AlpacaOrderStatus.FILLED, AlpacaOrderStatus.CANCELED, AlpacaOrderStatus.REJECTED, AlpacaOrderStatus.EXPIRED}) else 1,
            action_taken="NOMINAL_LOGGED" if in_parity else "HALTED_ON_DISCREPANCY",
            report_digest=report_digest,
        )

        # 6. Economic Attribution & Manifest Construction (Strict Provenance, Zero Fabrication)
        avg_fill_price: Optional[Decimal] = None
        if sse_fills:
            total_val = sum((q * p for q, p in sse_fills), Decimal("0"))
            total_qty = sum((q for q, _ in sse_fills), Decimal("0"))
            if total_qty > Decimal("0"):
                avg_fill_price = total_val / total_qty
        elif broker_snapshot is not None and broker_snapshot.filled_avg_price is not None:
            avg_fill_price = broker_snapshot.filled_avg_price
        else:
            avg_fill_price = None

        slippage_bps: Optional[float] = None
        if avg_fill_price is not None:
            slippage_bps = float(((avg_fill_price - benchmark_mid_price) / benchmark_mid_price) * Decimal("10000"))

        # Broker-observed terminal timestamp provenance
        closed_at_timestamp: Optional[datetime] = None
        if is_terminal:
            if final_state == OrderLifecycleState.FILLED:
                closed_at_timestamp = broker_snapshot.filled_at if (broker_snapshot and broker_snapshot.filled_at) else sse_terminal_at
            elif final_state == OrderLifecycleState.CANCELLED:
                closed_at_timestamp = broker_snapshot.canceled_at if (broker_snapshot and broker_snapshot.canceled_at) else sse_terminal_at
            elif final_state in {OrderLifecycleState.REJECTED, OrderLifecycleState.EXPIRED}:
                closed_at_timestamp = broker_snapshot.updated_at if (broker_snapshot and broker_snapshot.updated_at) else sse_terminal_at

        # Timing provenance: created_at represents local OrderIntent construction time
        intent_created_at = _utcnow()
        intent = OrderIntent(
            intent_id=f"INT_{self._execution_id_prefix}_{client_order_id}",
            authorization_id="AUTH_PAPER_EXERCISE",
            strategy_id="STRAT_PAPER_EXERCISE",
            venue="ALPACA_PAPER",
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=quantity,
            limit_price=None,
            stop_price=None,
            created_at=intent_created_at,
            signal_event_hash="0" * 64,
            risk_snapshot_hash="0" * 64,
            intent_digest=_sha256_hexdigest({
                "client_order_id": client_order_id,
                "symbol": symbol,
                "quantity": str(quantity),
            }),
        )

        steps_payload = []
        for out in outcomes:
            if not out.was_duplicate and not out.rejected:
                steps_payload.append({"state": out.state.value, "filled_qty": str(out.filled_qty)})

        execution_id = f"{self._execution_id_prefix}_{client_order_id}"
        manifest_digest = _sha256_hexdigest({
            "steps": steps_payload,
            "execution_id": execution_id,
        })

        manifest = ExecutionManifest(
            execution_id=execution_id,
            authorization_id=intent.authorization_id,
            strategy_id=intent.strategy_id,
            intent_id=intent.intent_id,
            intent_digest=intent.intent_digest,
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            venue=intent.venue,
            symbol=symbol,
            order_side=intent.side,
            order_type=intent.order_type,
            created_at=intent.created_at,
            submitted_at=submitted_at_utc,
            acknowledged_at=None,
            first_fill_at=broker_snapshot.filled_at if (broker_snapshot and broker_snapshot.filled_at) else None,
            closed_at=closed_at_timestamp,
            requested_qty=quantity,
            filled_qty=coord.filled_qty,
            benchmark_mid_price=benchmark_mid_price,
            average_fill_price=avg_fill_price,
            realized_slippage_bps=slippage_bps,
            # Canonical Schema Commission Semantics: In ExecutionManifest (schema.py line 644),
            # total_commission_paid is a non-optional Decimal with canonical default Decimal("0.0").
            # Alpaca standard US equity paper trading carries $0 commission; when broker provides
            # no per-trade fee item in the order snapshot, Decimal("0.0") represents the canonical
            # schema default for unavailable fee data, not a broker-reported fee execution event.
            total_commission_paid=Decimal("0.0"),
            source_signal_event_hash=intent.signal_event_hash,
            execution_digest=manifest_digest,
        )

        return RealDriverEvidence(
            scenario="real_broker_observation",
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            symbol=symbol,
            requested_qty=quantity,
            venue="ALPACA_PAPER",
            states_reached=tuple(states_reached),
            final_state=final_state.value,
            final_terminal=is_terminal,
            filled_qty=coord.filled_qty,
            disputed=coord.disputed,
            outcomes=tuple(outcomes),
            manifest=manifest,
            reconciliation_report=reconciliation_report,
        )


__all__ = [
    "R1RealDriverError",
    "R1RealOrderExerciseDriver",
    "RealDriverEvidence",
]
