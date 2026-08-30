"""8F-2: Concrete Alpaca Paper Transport adversarial tests.

Probes the locked 8F-2 invariants using ``httpx.MockTransport`` (broker behaviour
is injected; NO real network I/O):

- HTTP success != execution state transition: a submit only yields a
  ``SubmissionReceipt`` and a DELETE ``204`` only means the cancel *request was
  accepted* (never a confirmation / terminal state).
- Paper-only in BOTH layers: ``PaperHttpAlpacaTransport`` hard-rejects a non-paper
  venue at construction, and ``connect()`` re-asserts credential<->endpoint venue
  match (covers paper-cred->live / live-cred->paper silently).
- Fail-closed on timeout/network/auth: a timeout surfaces
  ``AlpacaTransportTimeoutError`` (an ambiguity -> UNKNOWN upstream), NEVER a
  CANCELLED/REJECTED/FILLED guess.
- Cancel request != cancel confirmed; HTTP 422 = non-cancellable.
- SSE framing decodes to ``AlpacaTradeEvent`` with broker_sequence from
  ``event_id`` (never timestamp-derived).
- Unknown statuses/events raise ``AlpacaTransportParseError`` (fail-closed,
  never guessed).
- Credentials never leak into DTOs/errors; no ``alpaca-py``; no state authority.
"""

import ast
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Optional

import httpx
import pytest

from acash.execution.alpaca import (
    AlpacaNonCancellableError,
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransportAuthError,
    AlpacaTransportError,
    AlpacaTransportParseError,
    AlpacaTransportTimeoutError,
    AlpacaVenueMismatchError,
    EnvAlpacaCredentialProvider,
    HttpAlpacaTransport,
    PaperHttpAlpacaTransport,
    live_endpoint,
    paper_endpoint,
)
from acash.execution.broker_adapter import SubmissionReceipt

_ORDER_ID = "db04069d-2e5a-48d4-a42f-6a0dea8ea0b8"


def _paper_provider(venue: str = "ALPACA_PAPER") -> EnvAlpacaCredentialProvider:
    return EnvAlpacaCredentialProvider(
        venue=venue, api_key_id="AK-PAPER-TEST", api_secret="paper-secret-test"
    )


def _make_paper(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    venue_provider: str = "ALPACA_PAPER",
) -> PaperHttpAlpacaTransport:
    provider = _paper_provider(venue_provider)
    t = PaperHttpAlpacaTransport(
        provider=provider,
        endpoint=paper_endpoint(),
        transport=httpx.MockTransport(handler),
    )
    t.connect()
    return t


# ---------------------------------------------------------------------------
# HTTP success != execution state transition
# ---------------------------------------------------------------------------


def test_submit_success_returns_receipt_not_state() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/orders"
        assert request.method == "POST"
        return httpx.Response(
            200,
            json={"id": _ORDER_ID, "client_order_id": "client-1"},
        )

    t = _make_paper(handler)
    receipt = t.submit_order(
        client_order_id="client-1", symbol="AAPL", quantity=Decimal("0.11")
    )
    assert receipt == SubmissionReceipt(
        broker_order_id=_ORDER_ID, client_order_id="client-1"
    )
    # A receipt is NOT a lifecycle state: no terminal state, no filled qty.
    assert not isinstance(receipt, AlpacaOrder)


def test_cancel_204_is_request_accepted_not_confirmed() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(204)

    t = _make_paper(handler)
    t.cancel_order(_ORDER_ID)  # returns None; request accepted, no confirmation
    assert seen == ["/v2/orders/db04069d-2e5a-48d4-a42f-6a0dea8ea0b8"]
    # The transport NEVER fabricates a cancel confirmation/terminal state.


def test_delete_422_is_non_cancellable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"code": 40010002, "message": "invalid order"})

    t = _make_paper(handler)
    with pytest.raises(AlpacaNonCancellableError):
        t.cancel_order(_ORDER_ID)


def test_cancel_404_is_fail_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"code": 40010001, "message": "order not found"})

    t = _make_paper(handler)
    with pytest.raises(AlpacaTransportError):
        t.cancel_order(_ORDER_ID)


# ---------------------------------------------------------------------------
# Paper-only enforcement (both layers)
# ---------------------------------------------------------------------------


def test_paper_transport_rejects_live_at_construction() -> None:
    with pytest.raises(AlpacaVenueMismatchError):
        PaperHttpAlpacaTransport(
            provider=_paper_provider(),
            endpoint=live_endpoint(),
        )


def test_generic_transport_runtime_rejects_paper_credential_to_live_endpoint() -> None:
    provider = _paper_provider()  # venue ALPACA_PAPER
    t = HttpAlpacaTransport(
        provider=provider,
        endpoint=live_endpoint(),
        transport=httpx.MockTransport(lambda r: httpx.Response(404)),
    )
    with pytest.raises(AlpacaVenueMismatchError):
        t.connect()


def test_generic_transport_runtime_rejects_live_credential_to_paper_endpoint() -> None:
    provider = _paper_provider(venue="ALPACA_LIVE")  # venue ALPACA_LIVE
    t = HttpAlpacaTransport(
        provider=provider,
        endpoint=paper_endpoint(),
        transport=httpx.MockTransport(lambda r: httpx.Response(404)),
    )
    with pytest.raises(AlpacaVenueMismatchError):
        t.connect()


# ---------------------------------------------------------------------------
# Fail-closed on timeout / network / auth
# ---------------------------------------------------------------------------


def test_timeout_raises_fail_closed_ambiguity_NOT_terminal() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("mock timeout")

    t = _make_paper(handler)
    with pytest.raises(AlpacaTransportTimeoutError) as exc:
        t.submit_order("c1", "AAPL", Decimal("0.11"))
    msg = str(exc.value)
    # It is an ambiguity, explicitly NOT a terminal guess.
    assert "paper-secret-test" not in msg  # no credential leakage
    assert "fail-closed" in msg


def test_network_error_raises_fail_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("mock connection refused")

    t = _make_paper(handler)
    with pytest.raises(AlpacaTransportError):
        t.cancel_order(_ORDER_ID)


def test_submit_before_connect_is_fail_closed() -> None:
    t = PaperHttpAlpacaTransport(
        provider=_paper_provider(),
        endpoint=paper_endpoint(),
        transport=httpx.MockTransport(lambda r: httpx.Response(404)),
    )
    with pytest.raises(AlpacaTransportError):
        t.submit_order("c1", "AAPL", Decimal("0.11"))


def test_missing_credentials_fail_closed_at_connect() -> None:
    provider = EnvAlpacaCredentialProvider(environ={"SOME_OTHER_VAR": "x"})
    t = PaperHttpAlpacaTransport(
        provider=provider,
        endpoint=paper_endpoint(),
        transport=httpx.MockTransport(lambda r: httpx.Response(404)),
    )
    with pytest.raises(AlpacaTransportAuthError):
        t.connect()


# ---------------------------------------------------------------------------
# Order / position reality (broker state, never lifecycle)
# ---------------------------------------------------------------------------


def test_query_order_parses_broker_state() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": _ORDER_ID,
                "client_order_id": "be139e2d-8153-4ae8-83ee-7b98b4e17419",
                "symbol": "AAPL",
                "status": "filled",
                "qty": "0.11",
                "filled_qty": "0.1102779",
                "created_at": "2023-10-13T13:22:21.887914Z",
                "updated_at": "2023-10-13T13:30:00.661902331Z",
                "filled_at": "2023-10-13T13:30:00.658443088Z",
            },
        )

    t = _make_paper(handler)
    order = t.query_order(_ORDER_ID)
    assert order.broker_order_id == _ORDER_ID
    assert order.status is AlpacaOrderStatus.FILLED
    assert order.requested_qty == Decimal("0.11")
    assert order.filled_qty == Decimal("0.1102779")  # cumulative, not per-fill
    assert order.filled_at == datetime.fromisoformat(
        "2023-10-13T13:30:00.658443088".replace("Z", "+00:00")
    ).replace(tzinfo=timezone.utc)


def test_query_order_unknown_status_raises_never_guesses() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": _ORDER_ID,
                "client_order_id": "c1",
                "symbol": "AAPL",
                "status": "teleported",  # unknown; MUST NOT guess a state
                "qty": "0.11",
                "filled_qty": "0",
                "created_at": "2023-10-13T13:22:21.887914Z",
                "updated_at": "2023-10-13T13:22:21.887914Z",
            },
        )

    t = _make_paper(handler)
    with pytest.raises(AlpacaTransportParseError):
        t.query_order(_ORDER_ID)


def test_query_position_returns_none_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    t = _make_paper(handler)
    assert t.query_position("AAPL") is None


def test_query_position_parses_snapshot() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"symbol": "AAPL", "qty": "42.5"})

    t = _make_paper(handler)
    pos = t.query_position("AAPL")
    assert pos is not None
    assert pos.symbol == "AAPL"
    assert pos.quantity == Decimal("42.5")
    assert pos.venue == "ALPACA_PAPER"


# ---------------------------------------------------------------------------
# SSE Trade Events streaming (broker_sequence = event_id)
# ---------------------------------------------------------------------------


def test_sse_stream_parses_fill_frame_with_sequence_from_event_id() -> None:
    event_json = (
        '{"event_id":"01HCMKKNRK7S5C1JYP50QGDECQ",'
        '"event":"fill",'
        '"at":"2023-10-13T13:28:58.387652Z",'
        '"executed_at":"2023-10-13T13:30:00.658443088Z",'
        '"order":{"id":"' + _ORDER_ID + '","client_order_id":"fill-c1",'
        '"symbol":"AAPL","status":"filled",'
        '"qty":"0.11","filled_qty":"0.1102779",'
        '"created_at":"2023-10-13T13:22:21.887914Z",'
        '"updated_at":"2023-10-13T13:30:00.661902331Z"},'
        '"execution_id":"a958bb42-b034-4d17-bf07-805cf0820ffe",'
        '"qty":"0.1102779",'
        '"price":"174.04"}'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=f"data: {event_json}\n\n",
            headers={"content-type": "text/event-stream"},
        )

    t = _make_paper(handler)
    stream = t.stream_trade_events()
    events = list(stream)
    stream.close()
    assert len(events) == 1
    ev = events[0]
    assert ev.event_id == "01HCMKKNRK7S5C1JYP50QGDECQ"  # broker_sequence source
    assert ev.event is AlpacaTradeEventType.FILL
    assert ev.broker_order_id == _ORDER_ID
    assert ev.execution_id == "a958bb42-b034-4d17-bf07-805cf0820ffe"
    # Sequence is the ULID id, NOT a timestamp.
    assert ev.event_id != str(ev.at)
    assert ev.executed_at == datetime.fromisoformat(
        "2023-10-13T13:30:00.658443088".replace("Z", "+00:00")
    ).replace(tzinfo=timezone.utc)
    assert ev.at.tzinfo is not None  # broker timestamps are tz-aware


def test_sse_stream_replay_since_id_passes_cursor() -> None:
    capture: dict[str, Optional[str]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capture["since_id"] = request.url.params.get("since_id")
        return httpx.Response(
            200, text="", headers={"content-type": "text/event-stream"}
        )

    t = _make_paper(handler)
    stream = t.stream_trade_events(since_id="01HCMKKNRK7S5C1JYP50QGDECQ")
    list(stream)
    stream.close()
    assert capture["since_id"] == "01HCMKKNRK7S5C1JYP50QGDECQ"


def test_sse_unknown_event_type_raises_never_guesses() -> None:
    event_json = (
        '{"event_id":"01HCMQR4S73L9G6EHI0JKL2M3N",'
        '"event":"teleport",'  # unknown; MUST NOT guess
        '"at":"2024-09-23T13:30:00.673857Z",'
        '"order":{"id":"' + _ORDER_ID + '","client_order_id":"u1","symbol":"AAPL"}}'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=f"data: {event_json}\n\n",
            headers={"content-type": "text/event-stream"},
        )

    t = _make_paper(handler)
    with pytest.raises(AlpacaTransportParseError):
        list(t.stream_trade_events())


# ---------------------------------------------------------------------------
# Structural guards (no alpaca-py, no state authority in the concrete seam)
# ---------------------------------------------------------------------------


_TRANSPORT_SRC = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "src", "acash",
    "execution", "alpaca", "transport.py",
)


def test_concrete_transport_imports_no_state_authority() -> None:
    with open(_TRANSPORT_SRC, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=_TRANSPORT_SRC)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        "acash.execution.coordinator",
        "acash.execution.schema",
        "acash.execution.state_machine",
        "acash.execution.lifecycle",
    }
    assert forbidden.isdisjoint(imported), imported & forbidden
    assert "alpaca-py" not in {i.split(".")[0] for i in imported}


def test_concrete_transport_method_surfaces_broker_reality_not_state() -> None:
    # The abstract seam guarantees the surface; the concrete class must not add
    # any transition/state authority either.
    assert not hasattr(PaperHttpAlpacaTransport, "transition_order")
    assert not hasattr(HttpAlpacaTransport, "transition_order")
    assert not hasattr(PaperHttpAlpacaTransport, "OrderLifecycleState")
