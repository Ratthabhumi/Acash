"""Alpaca transport abstraction + concrete paper transport (Phase 7 Step 8F).

This module defines the **transport seam** (abstraction) and its **concrete
paper HTTP/SSE implementation** (8F-2). The transport is the analog of
``MockBroker`` inside the existing ``SandboxBrokerAdapter`` pattern: an
injectable, deterministic, authority-free source of Alpaca broker reality that a
future ``AlpacaPaperAdapter`` (an implementation of ``BrokerAdapter``) delegates
to.

Authority separation (unchanged, locked):
- No ``OrderLifecycleState`` mutation, no ``transition_order`` reference, no
  normalization here. The transport only *carries* raw Alpaca payloads; the
  adapter maps them onto canonical ``BrokerRawEvent`` and the engine pump runs
  ``normalize_broker_event()`` (Step 8C) — authority stays with Step 8B (N-1).

Concrete transport invariants (8F-2):
- HTTP success != execution state transition:
  $$\boxed{\text{HTTP success} \neq \text{execution state transition}}$$
  ``POST``-order success only yields a ``SubmissionReceipt`` (never FILLED); a
  ``DELETE`` ``204`` only means the cancel *request was accepted* (never CANCELLED).
  Terminal mapping is deferred to the adapter/engine (8F-3).
- Paper-only enforcement in BOTH layers:
  $$\boxed{\text{typed venue config, not free URL string}}$$
  the endpoint is a typed ``AlpacaEndpoint`` (venue.py) with a derived base URL,
  and the paper transport hard-rejects a non-paper venue at construction plus
  re-asserts at ``connect()`` (defense-in-depth).
- Fail-closed on timeout/network/auth: we raise ``AlpacaTransportError`` and NEVER
  fabricate a terminal canonical state (a timeout is an ambiguity -> drives to
  UNKNOWN upstream, never CANCELLED/REJECTED/FILLED).

Field names follow the E-verified Alpaca BMAP (rv ``47a8bc9``, BMAP-02/03/06/10):
- ``broker_order_id``  <- ``order.id`` (UUID)
- ``broker_sequence``  <- ``event_id`` (ULID v2), verbatim, NOT timestamp-derived
- ``execution_id``     <- fill/partial-fill identity / dedup key
- ``at`` / ``executed_at`` <- business/execution timestamps (NOT the sequence)
- per-fill ``qty`` + cumulative ``filled_qty`` (overfill guard lives upstream)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Iterator, List, Mapping, Optional, Sequence

import httpx

from acash.execution.broker_adapter import (
    BrokerAdapterError,
    BrokerPosition,
    SubmissionReceipt,
)
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    AlpacaCredentialProvider,
)
from acash.execution.alpaca.venue import AlpacaEndpoint, AlpacaVenue


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


class AlpacaTransport(ABC):
    """Abstract Alpaca network/API seam (typed paper/live venue).

    Authority-free by design: it emits raw Alpaca shapes/ads only (orders, trade
    events, positions, errors) and NEVER computes or returns an
    ``OrderLifecycleState``, NEVER calls ``transition_order``, and NEVER performs
    canonical normalization (N-1/N-3). The adapter maps these onto
    ``BrokerRawEvent`` for the engine pump.

    ``endpoint`` is a typed ``AlpacaEndpoint`` (venue.py) — a derived, non-free-form
    base URL — so the venue (paper vs live) is explicit at construction, never an
    arbitrary caller URL. HTTP success is NOT an execution state transition; a
    submit only yields a ``SubmissionReceipt`` and a cancel request only returns
    after acceptance (never a confirmation). The transport holds no secrets itself;
    it calls ``provider.load()`` at construction and again on reconnect for live
    rotation (C-5).
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


# ===========================================================================
# 8F-2: concrete HTTP/SSE paper transport
# ===========================================================================


class AlpacaTransportError(BrokerAdapterError):
    """Fail-closed transport error (network, auth, venue, reply, parse).

    A transport surfaced error NEVER implies a terminal canonical state. In
    particular a timeout surfaces ``AlpacaTransportTimeoutError`` which upstream
    maps to an ambiguity -> UNKNOWN, NOT CANCELLED/REJECTED/FILLED (contract §3,
    BMAP §1 M-4). Messages carry NO credential material (C-2).
    """


class AlpacaTransportTimeoutError(AlpacaTransportError):
    """A request timed out. Fail-closed ambiguity, never a terminal guess."""


class AlpacaTransportAuthError(AlpacaTransportError):
    """Credential material absent/failed at connect (fail-closed, C-4)."""


class AlpacaTransportParseError(AlpacaTransportError):
    """Broker reply could not be parsed into a verified DTO (never guessed)."""


class AlpacaNonCancellableError(AlpacaTransportError):
    """Broker refused the cancel request (e.g. HTTP 422, non-cancellable)."""


class AlpacaVenueMismatchError(AlpacaTransportError):
    """Credential venue and endpoint venue disagree (cross-venue guard)."""


# Trade Events SSE resource relative to the ``/v2`` base. Exact resource is
# confirmed during conformance (8F-3); 8F-2 keeps the seam + frame parsing. The
# cursor ``since_id``/``until_id`` are ULID cursors (BMAP-04/08).
_TRADES_EVENTS_STREAM_PATH = "/events/trades"


class HttpAlpacaTransport(AlpacaTransport):
    """Concrete Alpaca REST + Trade-Events-SSE transport over ``httpx``.

    Authority-free and fail-closed:

    - HTTP success != execution state transition: submit returns only a
      ``SubmissionReceipt``; a ``DELETE`` ``204`` returns without a confirmation.
      No method produces or implies a terminal canonical state.
    - Timeouts/network/auth raise ``AlpacaTransportError`` subclasses; a timeout is
      an ambiguity (-> UNKNOWN upstream), never CANCELLED/REJECTED/FILLED.
    - Credentials are used only for ``httpx`` Basic auth and are never logged or
      serialized into any DTO/event.

    ``transport`` is an injectable ``httpx`` transport (e.g. ``httpx.MockTransport``)
    so unit tests never touch the network. Defaults to real network I/O.
    """

    def __init__(
        self,
        provider: AlpacaCredentialProvider,
        endpoint: AlpacaEndpoint,
        *,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        super().__init__(provider, endpoint)
        self._timeout = timeout
        self._inject_transport = transport
        self._client: Optional[httpx.Client] = None

    # -- paper-only enforcement (level 2: runtime, defense-in-depth) ---------

    def _assert_venue_match(self) -> None:
        provider_venue = self._provider.venue()
        if provider_venue != self._endpoint.venue.value:
            raise AlpacaVenueMismatchError(
                f"Alpaca venue mismatch: credential provider venue "
                f"{provider_venue!r} != endpoint venue {self._endpoint.venue.value!r} "
                f"(forbids paper->live / live->paper silently)."
            )

    def _require_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            raise AlpacaTransportError("transport is not connected")
        return self._client

    # -- ABC implementation ---------------------------------------------------

    def connect(self) -> None:
        try:
            creds = self._provider.load()
        except AlpacaCredentialError as exc:
            raise AlpacaTransportAuthError(
                "Alpaca credentials absent/failed; refusing to connect (fail-closed, C-4)."
            ) from exc
        if not creds.resolved:
            raise AlpacaTransportAuthError(
                "Alpaca credentials absent/failed; refusing to connect (fail-closed, C-4)."
            )
        self._assert_venue_match()
        self._client = httpx.Client(
            base_url=self._endpoint.base_url,
            auth=(
                creds.api_key_id,
                creds.api_secret_ref,
            ),
            timeout=self._timeout,
            transport=self._inject_transport,
        )

    def rotate_credentials(self) -> None:
        """Re-load credentials and rebuild the session (C-5, no code change)."""
        self._client = None
        self.connect()

    def connected(self) -> bool:
        return self._client is not None and not self._client.is_closed

    def submit_order(
        self,
        client_order_id: str,
        symbol: str,
        quantity: Decimal,
    ) -> SubmissionReceipt:
        client = self._require_client()
        payload = {
            "client_order_id": client_order_id,
            "symbol": symbol,
            "qty": str(quantity),
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
        }
        resp = self._request(client, "POST", "/orders", json=payload)
        if resp.status_code >= 400:
            self._raise_http("submit", resp.status_code)
        body = resp.json()
        broker_order_id = body.get("id") if isinstance(body, dict) else None
        if not isinstance(broker_order_id, str) or not broker_order_id:
            raise AlpacaTransportParseError(
                "submit response missing broker order id (never fabricate a receipt)."
            )
        # HTTP success => broker accepted the order, NOT a state transition.
        return SubmissionReceipt(
            broker_order_id=broker_order_id,
            client_order_id=client_order_id,
        )

    def cancel_order(self, broker_order_id: str) -> None:
        client = self._require_client()
        resp = self._request(client, "DELETE", f"/orders/{broker_order_id}")
        if resp.status_code == 204:
            # Request accepted only; a confirmation arrives as a later broker event.
            return
        if resp.status_code == 422:
            raise AlpacaNonCancellableError(
                "broker refused cancel (HTTP 422): order is not cancellable."
            )
        if resp.status_code == 404:
            raise AlpacaTransportError("cancel: order not found (HTTP 404).")
        self._raise_http("cancel", resp.status_code)

    def query_order(self, broker_order_id: str) -> AlpacaOrder:
        client = self._require_client()
        resp = self._request(client, "GET", f"/orders/{broker_order_id}")
        if resp.status_code == 404:
            raise AlpacaTransportError("order not found (HTTP 404).")
        if resp.status_code >= 400:
            self._raise_http("query_order", resp.status_code)
        return _parse_order(resp.json())

    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        client = self._require_client()
        resp = self._request(client, "GET", f"/positions/{symbol}")
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            self._raise_http("query_position", resp.status_code)
        body = resp.json()
        if not isinstance(body, dict):
            raise AlpacaTransportParseError("position reply is not an object.")
        return BrokerPosition(
            symbol=symbol,
            quantity=_to_decimal(body.get("qty"), "position qty"),
            venue=self._endpoint.venue.value,
        )

    def stream_trade_events(
        self,
        since_id: Optional[str] = None,
    ) -> AlpacaEventStream:
        client = self._require_client()
        params: Dict[str, str] = {}
        if since_id is not None:
            params["since_id"] = since_id
        return _HttpAlpacaEventStream(
            client=client,
            path=_TRADES_EVENTS_STREAM_PATH,
            params=params,
            venue=self._endpoint.venue,
        )

    # -- HTTP plumbing (fail-closed) ------------------------------------------

    @staticmethod
    def _request(
        client: httpx.Client,
        method: str,
        path: str,
        *,
        json: Optional[Mapping[str, object]] = None,
    ) -> httpx.Response:
        try:
            if method == "POST":
                return client.post(path, json=json)
            if method == "DELETE":
                return client.delete(path)
            return client.get(path)
        except httpx.TimeoutException as exc:
            raise AlpacaTransportTimeoutError(
                f"{method} {path} timed out (fail-closed ambiguity, not a terminal state)."
            ) from exc
        except httpx.HTTPError as exc:
            raise AlpacaTransportError(
                f"{method} {path} network error (fail-closed)."
            ) from exc

    @staticmethod
    def _raise_http(operation: str, status_code: int) -> "None":
        raise AlpacaTransportError(
            f"{operation} rejected by broker: HTTP {status_code} (fail-closed)."
        )


class PaperHttpAlpacaTransport(HttpAlpacaTransport):
    """Paper-only concrete transport.

    Level 1 (constructor-time typed gate): a non-paper venue is a hard
    ``AlpacaVenueMismatchError`` regardless of anything else. Level 2 (runtime,
    inherited): ``connect()`` also asserts credential<->endpoint venue match.
    """

    def __init__(
        self,
        provider: AlpacaCredentialProvider,
        endpoint: AlpacaEndpoint,
        *,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        if not endpoint.is_paper:
            raise AlpacaVenueMismatchError(
                f"PaperAlpacaTransport refuses non-paper venue: {endpoint.venue.value}."
            )
        super().__init__(
            provider,
            endpoint,
            timeout=timeout,
            transport=transport,
        )


class _HttpAlpacaEventStream(AlpacaEventStream):
    """SSE-backed ``AlpacaEventStream`` over ``httpx``.

    Parses ``data`` frames from the Trade Events SSE stream and yields
    ``AlpacaTradeEvent`` DTOs. Re-delivery is possible (BMAP-04/08); dedup is the
    engine's job keyed on ``event_id`` (broker_sequence).
    """

    def __init__(
        self,
        client: httpx.Client,
        path: str,
        params: Dict[str, str],
        venue: AlpacaVenue,
    ) -> None:
        self._client = client
        self._path = path
        self._params = params
        self._venue = venue
        self._response: Optional[httpx.Response] = None

    def __iter__(self) -> Iterator[AlpacaTradeEvent]:
        with self._client.stream(
            "GET", self._path, params=self._params
        ) as resp:
            if resp.status_code >= 400:
                raise AlpacaTransportError(
                    f"event stream rejected: HTTP {resp.status_code}."
                )
            self._response = resp
            for line in resp.iter_lines():
                event = _parse_sse_line(line, self._venue)
                if event is not None:
                    yield event

    def close(self) -> None:
        if self._response is not None:
            self._response.close()


# -- DTO parsing (deterministic, fail-closed on unknown) -----------------------


def _to_decimal(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (TypeError, ValueError) as exc:
        raise AlpacaTransportParseError(
            f"cannot parse {field}: {value!r} (fail-closed)."
        ) from exc


def _to_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise AlpacaTransportParseError(f"{field} is not an ISO string.")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AlpacaTransportParseError(
            f"cannot parse {field}: {value!r} (fail-closed)."
        ) from exc


def _parse_order(body: object) -> AlpacaOrder:
    if not isinstance(body, dict):
        raise AlpacaTransportParseError("order reply is not an object.")
    raw_status = body.get("status")
    try:
        status = AlpacaOrderStatus(str(raw_status))
    except ValueError as exc:
        raise AlpacaTransportParseError(
            f"unknown order status {raw_status!r}; refusing to guess a state."
        ) from exc
    broker_order_id = body.get("id")
    client_order_id = body.get("client_order_id")
    symbol = body.get("symbol")
    if not isinstance(broker_order_id, str) or not broker_order_id:
        raise AlpacaTransportParseError("order reply missing broker order id.")
    if not isinstance(client_order_id, str) or not client_order_id:
        raise AlpacaTransportParseError("order reply missing client order id.")
    if not isinstance(symbol, str) or not symbol:
        raise AlpacaTransportParseError("order reply missing symbol.")
    return AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id=client_order_id,
        symbol=symbol,
        status=status,
        requested_qty=_to_decimal(body.get("qty"), "order qty"),
        filled_qty=_to_decimal(body.get("filled_qty", 0), "filled qty"),
        created_at=_to_datetime(body.get("created_at"), "created_at"),
        updated_at=_to_datetime(body.get("updated_at"), "updated_at"),
        filled_at=_optional_datetime(body.get("filled_at"), "filled_at"),
        canceled_at=_optional_datetime(body.get("canceled_at"), "canceled_at"),
        cancel_requested_at=_optional_datetime(
            body.get("cancel_requested_at"), "cancel_requested_at"
        ),
    )


def _optional_datetime(value: object, field: str) -> Optional[datetime]:
    if value is None or value == "":
        return None
    return _to_datetime(value, field)


def _parse_sse_line(line: str, _venue: AlpacaVenue) -> Optional[AlpacaTradeEvent]:
    text = line.strip()
    if not text.startswith("data:"):
        return None
    payload = text[len("data:"):].strip()
    if not payload:
        return None
    import json

    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AlpacaTransportParseError("malformed SSE data frame.") from exc
    return _parse_trade_event(obj)


def _parse_trade_event(obj: object) -> AlpacaTradeEvent:
    if not isinstance(obj, dict):
        raise AlpacaTransportParseError("trade event payload is not an object.")
    raw_event = obj.get("event")
    try:
        event_type = AlpacaTradeEventType(str(raw_event))
    except ValueError as exc:
        raise AlpacaTransportParseError(
            f"unknown trade event type {raw_event!r}; refusing to guess."
        ) from exc
    event_id = obj.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        raise AlpacaTransportParseError(
            "trade event missing event_id (broker_sequence source)."
        )
    order_obj = obj.get("order")
    broker_order_id: Optional[str] = None
    if isinstance(order_obj, dict):
        candidate = order_obj.get("id")
        if isinstance(candidate, str):
            broker_order_id = candidate
    # SSE frames may carry broker_order_id at top level on some paths.
    top_id = obj.get("broker_order_id")
    if broker_order_id is None and isinstance(top_id, str):
        broker_order_id = top_id
    if not broker_order_id:
        raise AlpacaTransportParseError("trade event missing broker order id.")

    return AlpacaTradeEvent(
        event_id=event_id,
        event=event_type,
        at=_to_datetime(obj.get("at"), "at"),
        executed_at=_optional_datetime(obj.get("executed_at"), "executed_at"),
        broker_order_id=broker_order_id,
        execution_id=_optional_str(obj.get("execution_id")),
        qty=_optional_decimal(obj.get("qty"), "qty"),
        price=_optional_decimal(obj.get("price"), "price"),
        previous_execution_id=_optional_str(obj.get("previous_execution_id")),
        reason=_optional_str(obj.get("reason")),
        order=_parse_order(order_obj) if isinstance(order_obj, dict) else None,
    )


def _optional_str(value: object) -> Optional[str]:
    return value if isinstance(value, str) else None


def _optional_decimal(value: object, field: str) -> Optional[Decimal]:
    if value is None:
        return None
    return _to_decimal(value, field)
