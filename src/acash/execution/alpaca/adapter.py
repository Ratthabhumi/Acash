"""Phase 7 Step 8F: 8F-3 ``AlpacaPaperAdapter`` (concrete Alpaca broker adapter).

Translates Alpaca paper reality (raw ``AlpacaOrder`` / ``AlpacaTradeEvent`` DTOs
from the 8F-2 ``AlpacaTransport``) onto the canonical ``BrokerRawEvent``
vocabulary, exposing the ``BrokerAdapter`` interface to the engine pump.

Authority separation (locked, contract §1 N-1/N-3, BMAP §1): this adapter is a
*command sink + observation source* ONLY. It NEVER:

- returns or mutates an ``OrderLifecycleState``,
- calls ``transition_order()`` or ``ExecutionCoordinator``,
- performs canonical normalization itself (Step 8C ``normalize_broker_event()``
  is the sole normalizer authority).

The adapter emits ``BrokerRawEvent`` observations (canonical identity + reality
fields) which the engine pump feeds to ``normalize_broker_event()`` then to
``ExecutionCoordinator`` -> ``transition_order()`` (Step 8B sole authority).

Five no-shortcut rules (locked, user): POST ACK != FILLED; DELETE 204 !=
CANCELLED; timeout -> UNKNOWN (never a terminal guess); canceled-without-valid-
provenance fail-closed; ``event_id`` -> ``broker_sequence`` verbatim (BMAP-03).

The mapping (BMAP-01):
- ``accepted``/``new``/``pending_new``           -> ACK
- ``partial_fill``                               -> PARTIAL_FILL (overfill triaged)
- ``fill``                                       -> FILLED (overfill triaged)
- ``rejected``                                   -> REJECT
- ``expired``                                    -> EXPIRED
- ``order_cancel_rejected``                      -> CANCEL_REJECTED
- ``canceled``                                   -> ALWAYS fail-closed raise
                                                   (BMAP-07 strictest, E-verified)
- non-terminal in-flight set + incidents (done_for_day, held, stopped,
  suspended, calculated, pending_cancel, pending_replace, replaced,
  order_replace_rejected, trade_bust, trade_correct) -> fail-closed raise
  (BMAP-01: in-flight MUST NOT be terminal; never guessed).

BMAP-07 strictest policy (E-verified, user-locked): the adapter NEVER emits
``ORDER_CANCELLED`` from the live SSE ``canceled`` path. Current Alpaca docs
(TradeUpdateEventV2 ``reason``) provide NO documented positive "user cancel"
discriminator, and ``cancel_requested_at`` proves only that a cancel was
*requested*, not that the resulting ``canceled`` was user-initiated vs
Alpaca-side (``CORPORATE_ACTION``) or upstream-venue free-form. Therefore
``canceled`` ALWAYS raises ``AlpacaAdapterMappingError``; ``CANCELLED`` is
resolved only by the reconciliation layer via REST snapshot evidence
(``ingest_order_snapshot(..., ORDER_CANCELLED)`` with ``cancel_was_requested``).

Fail-closed (user-approved): overfill, unexpected cancellation, non-terminal
in-flight events, and every SSE ``canceled`` RAISE ``AlpacaAdapterMappingError``
(a subclass of ``BrokerAdapterError``). The engine pump catches this and routes
to reconciliation/incident. The adapter never fabricates a terminal canonical
state.

Credential boundary (BMAP-10 / C-1..C-5): this adapter holds no secrets itself;
it delegates all authed I/O to its ``AlpacaTransport``. It never writes
credential material into events, evidence, logs, or error messages.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from acash.execution.alpaca.transport import (
    AlpacaEventStream,
    AlpacaOrder,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
    AlpacaTransportError,
)
from acash.execution.broker_adapter import (
    AdapterHealth,
    BrokerAdapter,
    BrokerAdapterError,
    BrokerOrderReality,
    BrokerPosition,
    SubmissionReceipt,
)
from acash.execution.broker_events import BrokerEventKind
from acash.execution.mock_broker import BrokerRawEvent

_SOURCE = "ALPACA"

# Alpaca trade-event types that are genuinely actionable canonical transitions.
_ACK_TYPES = frozenset(
    {
        AlpacaTradeEventType.ACCEPTED,
        AlpacaTradeEventType.NEW,
        AlpacaTradeEventType.PENDING_NEW,
    }
)

# Alpaca statuses that are non-terminal in-flight / incident-only and MUST NOT be
# guessed into a terminal canonical state (BMAP-01).
_IN_FLIGHT_NON_TERMINAL = frozenset(
    {
        AlpacaTradeEventType.DONE_FOR_DAY,
        AlpacaTradeEventType.HELD,
        AlpacaTradeEventType.STOPPED,
        AlpacaTradeEventType.SUSPENDED,
        AlpacaTradeEventType.CALCULATED,
        AlpacaTradeEventType.PENDING_CANCEL,
        AlpacaTradeEventType.PENDING_REPLACE,
        AlpacaTradeEventType.REPLACED,
        AlpacaTradeEventType.ORDER_REPLACE_REJECTED,
        AlpacaTradeEventType.TRADE_BUST,
        AlpacaTradeEventType.TRADE_CORRECT,
    }
)

# Canonical kinds a REST snapshot may assert during reconciliation (BMAP-02/11).
_SNAPSHOT_KINDS = frozenset(
    {
        BrokerEventKind.FILLED,
        BrokerEventKind.REJECT,
        BrokerEventKind.ORDER_CANCELLED,
        BrokerEventKind.EXPIRED,
        BrokerEventKind.PARTIAL_FILL,
        BrokerEventKind.ACK,
    }
)

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AlpacaAdapterMappingError(BrokerAdapterError):
    """Fail-closed mapping error: raw Alpaca reality cannot be faithfully mapped
    onto a canonical ``BrokerRawEvent`` without guessing a terminal state.

    Thrown for:
    - overfill (cumulative ``filled_qty > requested_qty``) — BMAP-06;
    - unexpected cancellation without user-cancel provenance — BMAP-07;
    - non-terminal in-flight / incident-only Alpaca event types — BMAP-01.

    The engine pump catches this and routes to reconciliation/incident. It never
    fabricates a terminal canonical state. Messages carry NO credential material.
    """


class AlpacaPaperAdapter(BrokerAdapter):
    """Concrete paper adapter over an ``AlpacaTransport`` (8F-2).

    Wraps the abstract transport (tests inject a fake transport or the concrete
    ``PaperHttpAlpacaTransport``). Authority-free: no lifecycle state, no
    ``transition_order()``, no normalizer. The venue is guaranteed paper-only at
    the transport layer; this adapter never connects a live venue.
    """

    def __init__(self, transport: AlpacaTransport) -> None:
        self._transport = transport
        # Per-order observation log (broker reality) drained by subscribe_events.
        self._observations: dict[str, list[BrokerRawEvent]] = {}
        # BMAP-04 REST-snapshot fallback: strictly-increasing LOCAL receipt
        # counter, explicitly a fallback (never a genuine Alpaca sequence).
        self._snapshot_counter = 0

    @property
    def transport(self) -> AlpacaTransport:
        return self._transport

    # -- commands ------------------------------------------------------------

    def submit_order(
        self,
        client_order_id: str,
        symbol: str,
        quantity: Decimal,
    ) -> SubmissionReceipt:
        if quantity <= Decimal("0"):
            raise BrokerAdapterError(
                f"submit_order: quantity must be positive for {symbol}."
            )
        receipt = self._transport.submit_order(
            client_order_id=client_order_id,
            symbol=symbol,
            quantity=quantity,
        )
        # HTTP success yields only a SubmissionReceipt, never FILLED (no-shortcut).
        if receipt is None:
            raise BrokerAdapterError(
                f"submit_order: transport returned no receipt for {symbol}."
            )
        return receipt

    def cancel_order(self, broker_order_id: str) -> None:
        # DELETE 204 acceptance is a cancel REQUEST, never CANCELLED (no-shortcut).
        # The broker-side cancel confirmation arrives as a later event.
        self._transport.cancel_order(broker_order_id)

    # -- queries -------------------------------------------------------------

    def query_order(self, broker_order_id: str) -> BrokerOrderReality:
        return self._transport.query_order(broker_order_id)

    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        return self._transport.query_position(symbol)

    def health_check(self) -> AdapterHealth:
        try:
            healthy = self._transport.connected()
        except AlpacaTransportError:
            return AdapterHealth(healthy=False, detail="alpaca transport error")
        return AdapterHealth(healthy=healthy)

    def subscribe_events(self, broker_order_id: str) -> Sequence[BrokerRawEvent]:
        if broker_order_id is None or not broker_order_id.strip():
            raise BrokerAdapterError(
                "subscribe_events: broker_order_id is empty (fail-closed)."
            )
        return tuple(self._observations.get(broker_order_id, ()))

    # -- timeout / ambiguity (contract §3 T-1/T-2) ---------------------------

    def raise_ack_timeout(self, broker_order_id: str) -> BrokerRawEvent:
        """Emit ``CONNECTION_LOST`` on an ACK/REJECT timeout (contract §3 T-1).

        The order is NOT declared cancelled/rejected/filled anywhere here; it is
        reported as disconnected reality so the engine drives it to UNKNOWN.
        """
        raw = BrokerRawEvent(
            broker_order_id=broker_order_id,
            event_kind=BrokerEventKind.CONNECTION_LOST,
            observed_at=_utc_now(),
            source=_SOURCE,
            broker_sequence=self._next_fallback_sequence(broker_order_id),
        )
        self._record(raw)
        return raw

    def raise_cancel_confirmation_timeout(self, broker_order_id: str) -> BrokerRawEvent:
        """Emit ``CONNECTION_LOST`` after a cancel-confirmation timeout (T-2).

        A pending-cancel timeout never proves CANCELLED; it is reported as
        disconnected reality so the engine drives the order to UNKNOWN.
        """
        return self.raise_ack_timeout(broker_order_id)

    # -- live SSE observation source (BMAP-04/08/09) -------------------------

    def stream_trade_events(
        self, since_id: Optional[str] = None
    ) -> AlpacaEventStream:
        """Open the Trade Events SSE cursor/replay (reconnect resumable via cursor)."""
        return self._transport.stream_trade_events(since_id=since_id)

    def ingest_trade_event(self, event: AlpacaTradeEvent) -> BrokerRawEvent:
        """Map one raw Alpaca Trade Events SSE payload -> canonical BrokerRawEvent.

        This is the adapter's primary observation mapper (BMAP-01..09). It is
        authority-free: it returns a canonical observation only; the engine pump
        normalizes and transitions.
        """
        if event is None:
            raise AlpacaAdapterMappingError(
                "ingest_trade_event: event is None (fail-closed)."
            )
        raw = self._map_trade_event(event)
        self._record(raw)
        return raw

    def ingest_order_snapshot(
        self, order: AlpacaOrder, kind: BrokerEventKind
    ) -> BrokerRawEvent:
        """Map a REST order snapshot to a canonical observation (reconciliation).

        ``kind`` MUST be a reconciliation-verifiable canonical kind (BMAP-02), so
        the caller cannot fabricate an arbitrary transition. Reconciliation
        snapshots use the strictly-increasing local receipt counter as
        ``broker_sequence`` (BMAP-04 fallback; live SSE uses verbatim ``event_id``).
        """
        if order is None:
            raise AlpacaAdapterMappingError(
                "ingest_order_snapshot: order is None (fail-closed)."
            )
        raw = self._order_to_raw(order, kind)
        self._record(raw)
        return raw

    # -- mapping internals ---------------------------------------------------

    def _map_trade_event(self, event: AlpacaTradeEvent) -> BrokerRawEvent:
        if not event.broker_order_id or not event.broker_order_id.strip():
            raise AlpacaAdapterMappingError(
                "ingest_trade_event: broker_order_id is empty (fail-closed)."
            )
        if event.event is None:
            raise AlpacaAdapterMappingError(
                "ingest_trade_event: event type is None (fail-closed)."
            )

        etype = event.event

        if etype in _ACK_TYPES:
            raw = BrokerRawEvent(
                broker_order_id=event.broker_order_id,
                event_kind=BrokerEventKind.ACK,
                observed_at=self._observation_time(event),
                source=_SOURCE,
                broker_sequence=self._event_sequence(event),
                cancel_was_requested=self._cancel_requested(event),
            )
        elif etype is AlpacaTradeEventType.REJECTED:
            raw = self._direct(event, BrokerEventKind.REJECT)
        elif etype is AlpacaTradeEventType.EXPIRED:
            raw = self._direct(event, BrokerEventKind.EXPIRED)
        elif etype is AlpacaTradeEventType.ORDER_CANCEL_REJECTED:
            raw = self._direct(event, BrokerEventKind.CANCEL_REJECTED)
        elif etype is AlpacaTradeEventType.PARTIAL_FILL:
            self._assert_no_overfill(event)
            raw = self._direct(event, BrokerEventKind.PARTIAL_FILL)
        elif etype is AlpacaTradeEventType.FILL:
            self._assert_no_overfill(event)
            raw = self._direct(event, BrokerEventKind.FILLED)
        elif etype is AlpacaTradeEventType.CANCELED:
            raw = self._map_canceled(event)
        elif etype in _IN_FLIGHT_NON_TERMINAL:
            # BMAP-01: in-flight statuses MUST NOT be terminal; never guess.
            raise AlpacaAdapterMappingError(
                f"ingest_trade_event: Alpaca event type '{etype.value}' is a "
                "non-terminal in-flight status and cannot be mapped onto a "
                "terminal canonical BrokerEventKind without guessing state "
                "(BMAP-01). Fail-closed; route to reconciliation."
            )
        else:
            raise AlpacaAdapterMappingError(
                f"ingest_trade_event: unknown Alpaca event type "
                f"'{getattr(etype, 'value', etype)!r}' (fail-closed, never guessed)."
            )
        return raw

    def _direct(self, event: AlpacaTradeEvent, kind: BrokerEventKind) -> BrokerRawEvent:
        return BrokerRawEvent(
            broker_order_id=event.broker_order_id,
            event_kind=kind,
            observed_at=self._observation_time(event),
            source=_SOURCE,
            broker_sequence=self._event_sequence(event),
            cancel_was_requested=self._cancel_requested(event),
        )

    def _map_canceled(self, event: AlpacaTradeEvent) -> BrokerRawEvent:
        # BMAP-07 strictest policy (E-verified, user-locked): the SSE 'canceled'
        # path can NEVER be proven user-cancel against current Alpaca docs. There
        # is no documented positive 'user cancel' reason code; `cancel_requested_at`
        # proves only a cancel was REQUESTED, not that the resulting `canceled` was
        # user-initiated vs Alpaca-side (CORPORATE_ACTION) or upstream-venue
        # free-form reason. Even with `cancel_requested_at` set, reason does not
        # disambiguate. Therefore ALWAYS fail-closed; never emit ORDER_CANCELLED.
        # CANCELLED is resolved only via REST reconciliation snapshot evidence.
        raise AlpacaAdapterMappingError(
            f"ingest_trade_event: Alpaca reported 'canceled' for "
            f"{event.broker_order_id}. Current Alpaca docs provide no verified "
            "user-cancel discriminator (reason=None is NOT documented as a routine "
            "user cancel; reason may be CORPORATE_ACTION or upstream-venue "
            "free-form). Unexpected/ambiguous cancellation cannot be guessed; "
            "BMAP-07 strict fail-closed. Route to reconciliation; resolve CANCELLED "
            "via REST snapshot evidence only."
        )

    def _order_to_raw(
        self, order: AlpacaOrder, kind: BrokerEventKind
    ) -> BrokerRawEvent:
        # Authority: canonical kinds are fixed by Step 8C/8E; the adapter adapts
        # TO them, never invents one (BMAP-02).
        if kind not in _SNAPSHOT_KINDS:
            raise AlpacaAdapterMappingError(
                f"ingest_order_snapshot: canonical kind '{kind.value}' is not a "
                "reconciliation-verifiable snapshot kind (fail-closed)."
            )
        observed_at = self._order_updated(order)
        return BrokerRawEvent(
            broker_order_id=order.broker_order_id,
            event_kind=kind,
            observed_at=observed_at,
            source=_SOURCE,
            broker_sequence=self._next_fallback_sequence(order.broker_order_id),
            cancel_was_requested=order.cancel_requested_at is not None,
        )

    # -- helpers ------------------------------------------------------------

    def _assert_no_overfill(self, event: AlpacaTradeEvent) -> None:
        order = event.order
        if order is None:
            # No cumulative reference supplied -> cannot verify overfill; fail-closed.
            raise AlpacaAdapterMappingError(
                f"ingest_trade_event: fill-family event for "
                f"{event.broker_order_id} carries no embedded cumulative order; "
                "cannot verify filled_qty <= requested_qty (BMAP-06). Fail-closed."
            )
        if order.filled_qty > order.requested_qty:
            raise AlpacaAdapterMappingError(
                f"ingest_trade_event: overfill for {event.broker_order_id} "
                f"(filled_qty={order.filled_qty} > requested_qty="
                f"{order.requested_qty}). Overfill is an anomaly, not a silent "
                "FILLED/clamp (BMAP-06). Fail-closed; route to reconciliation."
            )
        if event.qty is not None and event.qty > order.requested_qty:
            # per-fill qty exceeding the total requested is also an anomaly.
            raise AlpacaAdapterMappingError(
                f"ingest_trade_event: per-fill qty {event.qty} exceeds requested "
                f"qty {order.requested_qty} for {event.broker_order_id} "
                "(BMAP-06, fail-closed)."
            )

    def _cancel_requested(self, event: AlpacaTradeEvent) -> bool:
        if event.order is not None and event.order.cancel_requested_at is not None:
            return True
        return False

    def _observation_time(self, event: AlpacaTradeEvent) -> datetime:
        # BMAP-09: timestamp framing. Fill-family events key on executed_at /
        # business at; never blanket/event-dependent timestamp.
        if event.executed_at is not None:
            return event.executed_at
        if event.at is not None:
            return event.at
        raise AlpacaAdapterMappingError(
            f"ingest_trade_event: no event time (at/executed_at) for "
            f"{event.broker_order_id} (BMAP-09, fail-closed)."
        )

    def _event_sequence(self, event: AlpacaTradeEvent) -> str:
        # BMAP-03: broker_sequence = event_id (v2 ULID) verbatim; NEVER derived
        # from a timestamp/wall-clock. Deterministic, lexicographically sortable.
        if not event.event_id or not event.event_id.strip():
            raise AlpacaAdapterMappingError(
                f"ingest_trade_event: missing event_id for "
                f"{event.broker_order_id} (BMAP-03, fail-closed)."
            )
        return event.event_id

    def _order_updated(self, order: AlpacaOrder) -> datetime:
        # Snapshots time-keyed on updated_at (BMAP-09).
        if order.updated_at is not None:
            return order.updated_at
        raise AlpacaAdapterMappingError(
            f"ingest_order_snapshot: no updated_at for "
            f"{order.broker_order_id} (fail-closed)."
        )

    def _next_fallback_sequence(self, broker_order_id: str) -> str:
        # BMAP-04: the REST snapshot path uses a strictly-increasing LOCAL receipt
        # counter, explicitly a fallback -- never a genuine Alpaca sequence.
        self._snapshot_counter += 1
        return f"LOCAL-FB-{self._snapshot_counter:06d}-{broker_order_id}"

    def _record(self, raw: BrokerRawEvent) -> None:
        self._observations.setdefault(raw.broker_order_id, []).append(raw)


__all__ = ["AlpacaAdapterMappingError", "AlpacaPaperAdapter"]
