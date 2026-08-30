"""Phase 7 Step 8F: Broker Adapter contract & Sandbox (paper) implementation.

Implements the broker-adapter interface layer defined in
``docs/phase7/broker_adapter_contract.md`` (rv ``6fd4a78``):

- **BrokerAdapter** (abstract): the SDK/API abstraction every real broker adapter
  SHALL implement. It is a *command sink + observation source*: it translates
  broker reality onto the canonical ``BrokerRawEvent`` vocabulary. It NEVER
  computes, returns, or mutates an ``OrderLifecycleState`` and NEVER calls
  ``transition_order()`` (state authority is exclusive to Step 8B).
- **SandboxBrokerAdapter** (paper/sandbox): a deterministic in-memory adapter for
  the sandbox/paper phase. It wraps ``MockBroker`` (Step 8D broker-side reality)
  and surfaces canonical ``BrokerRawEvent`` observations through the interface.

Authority-separation invariant (contract §1):

$$\boxed{ BrokerAdapter \neq StateAuthority }$$

```
BrokerAdapter.submit/cancel/query/health
   -> BrokerRawEvent observations (broker reality only)
        -> (engine pump) normalize_broker_event()   [Step 8C]
              -> ExecutionCoordinator.apply/reconcile [Step 8E]
                    -> transition_order()             [Step 8B SOLE authority]
```

This module contains NO network I/O, NO real credentials, and NO state
transitions. Sandbox round-1: no live credentials, no live order submission.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple, TypeVar

from acash.core.domain.exceptions import DomainValidationError
from acash.execution.broker_events import (
    BrokerEventKind,
    ReconciliationEvidence,
    normalize_broker_event,
)
from acash.execution.coordinator import CoordinatorEvent
from acash.execution.mock_broker import (
    BrokerRawEvent,
    MockBroker,
    MockBrokerOrder,
)

_T = TypeVar("_T")


class BrokerAdapterError(DomainValidationError):
    """Fail-closed error surfaced by a broker adapter.

    Adapter error messages MUST NOT contain credential material (API keys,
    secrets, tokens). Any adapter that exposes a secret in an error message is
    in violation of the credential boundary (contract §6 C-1/C-2).
    """


@dataclass(frozen=True)
class BrokerCredentials:
    """Redacted credential handle for a broker venue.

    Deliberately colorable/redacted: the value is held ONLY by the adapter and is
    NEVER serialized into canonical events, evidence, incidents, manifests, logs,
    or error messages. ``str``/``repr`` always emit ``********``.

    Round-1 sandbox uses no real credentials; this type exists to define the
    credential boundary and to guarantee redaction semantics under test.
    """

    venue: str
    api_key_id: str = ""
    api_secret_ref: str = ""

    def __str__(self) -> str:
        return "********"

    def __repr__(self) -> str:
        return "BrokerCredentials(venue=********, redacted=True)"


@dataclass(frozen=True)
class SubmissionReceipt:
    """Adapter-side receipt of a submitted order (broker reality, NOT state).

    ``broker_order_id`` is the authoritative broker-side identifier assigned at
    submission. ``client_order_id`` echoes the engine's client id. No lifecycle
    state is represented here.
    """

    broker_order_id: str
    client_order_id: str


@dataclass(frozen=True)
class BrokerPosition:
    """Adapter-side position snapshot (broker reality, NOT ACASH shadow state)."""

    symbol: str
    quantity: Decimal
    venue: str


@dataclass(frozen=True)
class AdapterHealth:
    """Connectivity health reported by an adapter (bool + optional detail)."""

    healthy: bool
    detail: str = ""


class BrokerAdapter(ABC):
    """Abstract broker adapter interface (the Step 8F SDK/API abstraction).

    A real broker adapter implements these methods to translate its vendor
    payloads onto the canonical ``BrokerRawEvent`` vocabulary. An adapter:

    - MUST NOT return or set any ``OrderLifecycleState``.
    - MUST NOT call ``transition_order()`` or ``ExecutionCoordinator``.
    - MUST yield all broker observations as ``BrokerRawEvent`` (Step 8D shape),
      which the engine pump feeds to ``normalize_broker_event()``.
    - MUST NOT leak credentials into events, evidence, logs, or error messages.

    Messages surfaced to the engine are ``BrokerRawEvent`` objects carrying
    ``broker_order_id``, ``event_kind``, ``observed_at``, ``source``,
    ``broker_sequence``, ``cancel_was_requested`` — the canonical identity +
    reality fields (contract §7).
    """

    @abstractmethod
    def submit_order(
        self,
        client_order_id: str,
        symbol: str,
        quantity: Decimal,
    ) -> SubmissionReceipt:
        """Submit an order to the broker (sandbox/paper). Returns a receipt."""

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> None:
        """Request cancellation (broker-side: a cancel REQUEST, not a confirmation).

        This NEVER asserts the order is cancelled; the broker-side cancel
        confirmation arrives as a later ``BrokerRawEvent`` (contract §3 T-2:
        ``CancelRequested != Cancelled``).
        """

    @abstractmethod
    def query_order(self, broker_order_id: str) -> MockBrokerOrder:
        """Return broker-side order reality (broker state, not lifecycle state)."""

    @abstractmethod
    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        """Return broker-side position snapshot for a symbol."""

    @abstractmethod
    def subscribe_events(
        self,
        broker_order_id: str,
    ) -> Sequence[BrokerRawEvent]:
        """Return the broker-side event log for an order (drain snapshots).

        The engine pump converts each ``BrokerRawEvent`` to a canonical
        ``CoordinatorEvent`` via ``to_coordinator_event``, then applies it.
        """

    @abstractmethod
    def health_check(self) -> AdapterHealth:
        """Report adapter/connectivity health."""

    # -- timeout / ambiguity (contract §3) ----------------------------------

    @abstractmethod
    def raise_ack_timeout(self, broker_order_id: str) -> BrokerRawEvent:
        """Simulate an ACK/REJECT timeout -> canonical ``CONNECTION_LOST`` observation.

        Implements contract §3 T-1: on an acknowledgment timeout the adapter MUST
        emit ``CONNECTION_LOST`` (which drives the order to ``UNKNOWN``), NEVER a
        speculative ``CANCEL_ACK``/``FILL``/``REJECT``. The adapter itself does not
        set any state; it merely reports the timeout as broker reality.
        """


class SandboxBrokerAdapter(BrokerAdapter):
    """Deterministic paper/sandbox broker adapter over ``MockBroker`` (Step 8D).

    Round-1 sandbox: wraps ``MockBroker`` as broker-side reality and exposes the
    Step 8F interface. No live credentials, no network I/O, no state authority.

    The adapter only:
    - issues commands to ``MockBroker`` (submit/cancel),
    - queries broker-side reality (order/position/health),
    - surfaces broker observations as canonical ``BrokerRawEvent``.

    The engine pump (caller), NOT this adapter, performs normalization and
    transition (authority separation). This adapter never imports or references
    ``transition_order`` / ``ExecutionCoordinator`` / ``OrderLifecycleState``.
    """

    def __init__(
        self,
        source: str = "SANDBOX_BROKER",
        credentials: Optional[BrokerCredentials] = None,
    ) -> None:
        self._broker = MockBroker(source=source)
        self._source = source
        self._credentials = credentials or BrokerCredentials(venue=source)
        self._positions: dict[str, BrokerPosition] = {}

    @property
    def credentials(self) -> BrokerCredentials:
        """Redacted credential handle used for the boundary test (never leaks)."""
        return self._credentials

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
        order = self._guarded(
            self._broker.place_order, client_order_id, symbol, quantity
        )
        self._positions[symbol] = BrokerPosition(
            symbol=symbol, quantity=Decimal("0"), venue=self._source
        )
        return SubmissionReceipt(
            broker_order_id=order.broker_order_id,
            client_order_id=client_order_id,
        )

    def cancel_order(self, broker_order_id: str) -> None:
        # Broker-side cancel REQUEST only; confirmation arrives as a later event.
        self._guarded(self._broker.request_cancel, broker_order_id)

    # -- queries -------------------------------------------------------------

    def query_order(self, broker_order_id: str) -> MockBrokerOrder:
        order = self._broker.get_order(broker_order_id)
        if order is None:
            raise BrokerAdapterError(
                f"query_order: unknown broker_order_id '{broker_order_id}'."
            )
        return order

    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        return self._positions.get(symbol)

    def health_check(self) -> AdapterHealth:
        return AdapterHealth(healthy=True, detail="sandbox healthy")

    def subscribe_events(
        self, broker_order_id: str
    ) -> Sequence[BrokerRawEvent]:
        order = self._guarded(self._broker.get_order, broker_order_id)
        if order is None:
            raise BrokerAdapterError(
                f"subscribe_events: unknown broker_order_id '{broker_order_id}'."
            )
        return tuple(order.events)

    # -- timeout / ambiguity (contract §3 T-1/T-2) --------------------------

    def raise_ack_timeout(self, broker_order_id: str) -> BrokerRawEvent:
        """Simulate an ACK timeout -> canonical CONNECTION_LOST observation.

        The order is NOT marked cancelled/rejected anywhere here; it is reported
        as disconnected reality so the engine drives it to UNKNOWN (contract §3).
        """
        return self._guarded(self._broker.connection_lost, broker_order_id)

    def raise_cancel_confirmation_timeout(
        self, broker_order_id: str
    ) -> BrokerRawEvent:
        """Simulate a pending-cancel confirmation timeout (contract §3 T-2).

        Yields a ``CONNECTION_LOST`` observation after a cancel was requested;
        the adapter MUST NOT report the order as CANCELLED merely because a
        cancel was requested.
        """
        return self._guarded(self._broker.connection_lost, broker_order_id)

    # -- driver helpers used by sandbox scenarios ---------------------------

    def acknowledge(self, broker_order_id: str) -> BrokerRawEvent:
        return self._guarded(self._broker.acknowledge, broker_order_id)

    def reject(self, broker_order_id: str) -> BrokerRawEvent:
        return self._guarded(self._broker.reject, broker_order_id)

    def partial_fill(
        self, broker_order_id: str, qty: Decimal
    ) -> BrokerRawEvent:
        raw = self._guarded(
            self._broker.apply_partial_fill, broker_order_id, qty
        )
        self._update_position(broker_order_id)
        return raw

    def full_fill(self, broker_order_id: str) -> BrokerRawEvent:
        raw = self._guarded(self._broker.apply_full_fill, broker_order_id)
        self._update_position(broker_order_id)
        return raw

    def confirm_cancel(self, broker_order_id: str) -> BrokerRawEvent:
        return self._guarded(self._broker.confirm_cancel, broker_order_id)

    def reject_cancel(self, broker_order_id: str) -> BrokerRawEvent:
        return self._guarded(self._broker.reject_cancel, broker_order_id)

    def fill_during_cancel(self, broker_order_id: str) -> BrokerRawEvent:
        raw = self._guarded(self._broker.fill_during_cancel, broker_order_id)
        self._update_position(broker_order_id)
        return raw

    def expire(self, broker_order_id: str) -> BrokerRawEvent:
        return self._guarded(self._broker.expire, broker_order_id)

    def connection_lost_sim(self, broker_order_id: str) -> BrokerRawEvent:
        """Surface a connectivity-loss observation (contract §3 T-2)."""
        return self._guarded(self._broker.connection_lost, broker_order_id)

    def expect_overfill_guard(
        self, broker_order_id: str, cumulative_qty: Decimal
    ) -> None:
        """Fail-closed overfill guard (contract §2.1 M-2/M-2a).

        If an adapter observes ``cumulative_qty > requested`` it MUST NOT
        silently classify it as ``FILLED`` nor clamp it down; it MUST surface a
        protocol anomaly via ``BrokerAdapterError`` so the pump routes it to
        reconciliation/incident.
        """
        order = self.query_order(broker_order_id)
        if cumulative_qty > order.requested_qty:
            raise BrokerAdapterError(
                f"Broker overfill detected: cumulative {cumulative_qty} > "
                f"requested {order.requested_qty} for {broker_order_id}. "
                "Protocol anomaly; MUST NOT be silently classified FILLED. "
                "Route to reconciliation/incident."
            )

    # -- helpers -------------------------------------------------------------

    def _update_position(self, broker_order_id: str) -> None:
        order = self.query_order(broker_order_id)
        self._positions[order.symbol] = BrokerPosition(
            symbol=order.symbol,
            quantity=order.filled_qty,
            venue=self._source,
        )

    def _guarded(
        self, fn: Callable[..., _T], *args: object
    ) -> _T:
        """Fail-closed wrapper around broker reality.

        Any broker-layer error is surfaced as a secret-free ``BrokerAdapterError``
        so the pump never sees raw internal exceptions and never leaks credentials
        (contract §5 A-2).
        """
        try:
            return fn(*args)
        except BrokerAdapterError:
            raise
        except (KeyError, ValueError) as exc:
            raise BrokerAdapterError(f"adapter: {type(exc).__name__}: {exc}") from exc


def to_coordinator_event(
    raw: BrokerRawEvent,
    *,
    fill_qty: Optional[Decimal] = None,
) -> CoordinatorEvent:
    """Engine-pump seam: canonical ``BrokerRawEvent`` -> ``CoordinatorEvent``.

    This performs the Step 8C normalization (via ``normalize_broker_event``) and
    builds the canonical event identity ``(broker_event_id, broker_sequence)``
    that the coordinator uses for idempotency (contract §4 I-1).

    The adapter participates only by supplying the raw observation; the pump does
    normalization, keeping the adapter authority-free.
    """
    event, _evidence = normalize_broker_event(
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
        fill_qty=fill_qty,
    )
