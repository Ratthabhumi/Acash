"""Alpaca paper transport abstraction (Phase 7 Step 8F follow-on).

This module defines the **transport seam** for a future Alpaca paper adapter. It
is the analog of ``MockBroker`` inside the existing ``SandboxBrokerAdapter``
pattern: an injectable, deterministic, authority-free source of Alpaca broker
reality that a future ``AlpacaPaperAdapter`` (an implementation of
``BrokerAdapter``) will delegate to.

Scope of THIS checkpoint (interface + paper transport abstraction only):
- No concrete Alpaca SDK / HTTP wiring.
- No network I/O.
- No credentials in this module (they are supplied by
  ``AlpacaCredentialProvider`` and held only by the transport).
- No ``OrderLifecycleState`` mutation, no ``transition_order`` reference, no
  normalization here. The transport only *carries* raw Alpaca payloads; the
  adapter maps them onto canonical ``BrokerRawEvent`` and the engine pump runs
  ``normalize_broker_event()`` (Step 8C) — authority stays with Step 8B (N-1).

Field names below follow the **E-verified** Alpaca BMAP
(``docs/phase7/alpaca_bmap.md`` rv ``47a8bc9``, BMAP-02/03/06) and the frozen
broker adapter contract (``docs/phase7/broker_adapter_contract.md`` rv
``6fd4a78``):

- ``broker_order_id``  <- ``order.id`` (UUID)
- ``broker_sequence``  <- ``event_id`` (ULID, v2) — verbatim, NOT derived from a
                          timestamp (§3/§9)
- ``execution_id``     <- fill/partial fill event identity / dedup key
- ``at`` / ``executed_at`` <- business/execution timestamps (NOT the sequence)
- per-fill ``qty`` + ``order.filled_qty`` (cumulative) -> overfill guard is the
                          adapter's/coordinator's concern, not the transport
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Iterator, Optional, Sequence

from acash.execution.broker_adapter import (
    BrokerPosition,
    SubmissionReceipt,
)
from acash.execution.alpaca.credentials import AlpacaCredentialProvider


class AlpacaOrderStatus(str, Enum):
    """Alpaca ``order.status`` values relevant to the paper lifecycle.

    Only the subset the ACASH pipeline consumes is enumerated here. Unmapped /
    unknown values MUST be treated as non-terminal in-flight statuses by the
    adapter, never guessed into a terminal canonical state (BMAP §1, M-4).
    """

    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"
    PENDING_NEW = "pending_new"
    ACCEPTED = "accepted"
    HELD = "held"
    PENDING_CANCEL = "pending_cancel"
    CANCEL_REJECTED = "cancel_rejected"
    PENDING_REPLACE = "pending_replace"
    SUSPENDED = "suspended"
    DONE_FOR_DAY = "done_for_day"
    STOPPED = "stopped"
    CALCULATED = "calculated"


class AlpacaTradeEventType(str, Enum):
    """Alpaca Trade Events SSE ``event`` values (E-verified vocabulary).

    Mirrors the documented Trade Events SSE v2 lifecycle list. The adapter maps
    these onto canonical ``BrokerEventKind`` (BMAP §1); this transport never does
    that mapping.
    """

    ACCEPTED = "accepted"
    NEW = "new"
    PENDING_NEW = "pending_new"
    FILL = "fill"
    PARTIAL_FILL = "partial_fill"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    REJECTED = "rejected"
    DONE_FOR_DAY = "done_for_day"
    HELD = "held"
    STOPPED = "stopped"
    SUSPENDED = "suspended"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    CALCULATED = "calculated"
    ORDER_REPLACE_REJECTED = "order_replace_rejected"
    ORDER_CANCEL_REJECTED = "order_cancel_rejected"
    TRADE_BUST = "trade_bust"
    TRADE_CORRECT = "trade_correct"


class AlpacaCancelReason(str, Enum):
    """``reason`` codes documented on ``canceled`` / ``order_cancel_rejected``.

    BMAP §7: ``canceled`` is NOT proof of a user cancel. ``CORPORATE_ACTION``
    indicates an Alpaca-side cancel (not a user cancel) and ``TOO_LATE_TO_CANCEL``
    indicates the cancel request arrived after a terminal state. Free-form strings
    may also appear; consumers key on ``event`` first and use ``reason`` only as a
    secondary hint (BMAP-01/07).
    """

    CORPORATE_ACTION = "CORPORATE_ACTION"
    TOO_LATE_TO_CANCEL = "TOO_LATE_TO_CANCEL"
    TRADE_BUST = "TRADE_BUST"


@dataclass(frozen=True)
class AlpacaOrder:
    """Alpaca ``Order`` object projection (REST / embedded in trade events).

    Only fields the ACASH pipeline needs (BMAP-02 Layer A/B/C). ``qty`` and
    ``filled_qty`` are kept as strings-turned-Decimals to mirror Alpaca's decimal
    strings without losing precision; ``filled_qty`` is the **cumulative** fill
    quantity used for overfill triage (BMAP-06).
    """

    broker_order_id: str  # order.id (UUID)
    client_order_id: str
    symbol: str
    status: AlpacaOrderStatus
    requested_qty: Decimal
    filled_qty: Decimal  # cumulative, NOT per-fill
    created_at: datetime
    updated_at: datetime
    filled_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    cancel_requested_at: Optional[datetime] = None


@dataclass(frozen=True)
class AlpacaTradeEvent:
    """Alpaca Trade Events SSE ``event`` payload projection (BMAP-02).

    ``event_id`` is the ULID publication sequence -> becomes ``broker_sequence``
    verbatim (BMAP-03). ``at``/``executed_at`` are business/execution timestamps,
    NOT the sequence. ``execution_id`` is the fill dedup identity. ``qty`` is the
    per-fill quantity (negative on ``trade_bust``). ``reason`` is an optional
    machine code on ``canceled``/``order_cancel_rejected``/``trade_bust``.
    """

    event_id: str  # ULID (v2) -> broker_sequence
    event: AlpacaTradeEventType
    at: datetime  # business event time
    executed_at: Optional[datetime]  # execution time where applicable
    broker_order_id: str
    execution_id: Optional[str] = None
    qty: Optional[Decimal] = None  # per-fill; negative on trade_bust
    price: Optional[Decimal] = None
    previous_execution_id: Optional[str] = None
    reason: Optional[str] = None
    order: Optional[AlpacaOrder] = None


@dataclass(frozen=True)
class AlpacaEndpoint:
    """Paper vs live base endpoint resolved from the provider (BMAP-10).

    Distinct domains and key sets for paper vs live. The transport binds to the
    paper endpoint only for the sandbox/paper phase. No secrets live here.
    """

    base_url: str
    is_paper: bool


class AlpacaTransport(ABC):
    """Abstract Alpaca network/API seam (paper transport).

    Authority-free by design: it emits raw Alpaca shapes/ads only (orders, trade
    events, positions, errors) and NEVER computes or returns an
    ``OrderLifecycleState``, NEVER calls ``transition_order``, and NEVER performs
    canonical normalization (N-1/N-3). The future adapter maps these onto
    ``BrokerRawEvent`` for the engine pump.

    The transport holds no secrets itself; it receives the current
    ``AlpacaCredentials`` and the credential provider at construction and calls
    ``provider.load()`` again on reconnect for live rotation (C-5).
    """

    def __init__(
        self,
        provider: AlpacaCredentialProvider,
        endpoint: AlpacaEndpoint,
    ) -> None:
        self._provider = provider
        self._endpoint = endpoint

    @property
    def endpoint(self) -> AlpacaEndpoint:
        return self._endpoint

    @abstractmethod
    def connect(self) -> None:
        """Establish the authenticated session; fails closed (C-4) on failure."""

    @abstractmethod
    def submit_order(
        self,
        client_order_id: str,
        symbol: str,
        quantity: Decimal,
    ) -> SubmissionReceipt:
        """Place an order; returns the broker-assigned receipt (NOT state)."""

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> None:
        """Request cancellation (a REQUEST, NOT a confirmation)."""

    @abstractmethod
    def query_order(self, broker_order_id: str) -> AlpacaOrder:
        """Return broker-side order reality (broker state, not lifecycle)."""

    @abstractmethod
    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        """Return broker-side position snapshot for a symbol."""

    @abstractmethod
    def stream_trade_events(
        self,
        since_id: Optional[str] = None,
    ) -> "AlpacaEventStream":
        """Open a Trade Events SSE cursor/replay from ``since_id`` (ULID).

        May re-deliver events (BMAP-04/08); the engine deduplicates. This returns
        a stream handle, not a resolution of canonical state.
        """

    @abstractmethod
    def connected(self) -> bool:
        """Whether the transport session is currently up (health)."""

    @abstractmethod
    def rotate_credentials(self) -> None:
        """Re-load credentials from the provider and re-validate (C-5)."""


class AlpacaEventStream(ABC):
    """Handle to an open Trade Events SSE stream (replay + live push)."""

    @abstractmethod
    def __iter__(self) -> Iterator[AlpacaTradeEvent]:
        """Iterate raw ``AlpacaTradeEvent`` payloads as they arrive."""

    @abstractmethod
    def close(self) -> None:
        """Gracefully close the stream."""
