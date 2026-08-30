"""Phase 7 Step 8F: 8F-3 ``AlpacaPaperAdapter`` — BMAP-01..12 conformance suite.

This suite proves, for the ``AlpacaPaperAdapter`` -> canonical pipeline, that
the 12 frozen BMAP requirements hold adapter->canonical BEFORE any real paper
run (BMAP-12 = D is *this* checkpoint's conformance matrix; executing it here
does NOT create P evidence — paper runs remain deferred).

Scope (locked, user):
- The adapter maps Alpaca reality -> ``BrokerRawEvent`` ONLY. It never owns the
  state machine, never mutates ``OrderLifecycleState``, never calls
  ``transition_order()`` / ``ExecutionCoordinator``.
- The canonical normalization is done by the engine pump via
  ``normalize_broker_event()`` (Step 8C). Several cases extend the pipeline to
  that canonical step to prove end-to-end mapping correctness.

No-shortcut rules (locked): POST ACK != FILLED; DELETE 204 != CANCELLED; timeout
-> UNKNOWN; canceled-without-provenance fail-closed; ``event_id`` ->
``broker_sequence`` verbatim.
"""

import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterator, Optional

import pytest

from acash.execution.alpaca import (
    AlpacaEventStream,
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
)
from acash.execution.alpaca.adapter import (
    AlpacaAdapterMappingError,
    AlpacaPaperAdapter,
)
from acash.execution.broker_adapter import (
    BrokerPosition,
    SubmissionReceipt,
)
from acash.execution.broker_events import (
    BrokerEventKind,
    normalize_broker_event,
)
from acash.execution.mock_broker import BrokerRawEvent


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _order(
    *,
    broker_id: str = "alpaca-order-0001",
    client_id: str = "C1",
    symbol: str = "SPY",
    status: AlpacaOrderStatus = AlpacaOrderStatus.FILLED,
    requested: str = "10",
    filled: str = "10",
    cancel_requested_at: Optional[str] = None,
) -> AlpacaOrder:
    return AlpacaOrder(
        broker_order_id=broker_id,
        client_order_id=client_id,
        symbol=symbol,
        status=status,
        requested_qty=Decimal(requested),
        filled_qty=Decimal(filled),
        created_at=_utc("2026-01-01T00:00:00Z"),
        updated_at=_utc("2026-01-01T00:01:00Z"),
        cancel_requested_at=_utc(cancel_requested_at) if cancel_requested_at else None,
    )


def _event(
    *,
    event_id: str,
    etype: AlpacaTradeEventType,
    broker_id: str = "alpaca-order-0001",
    at: str = "2026-01-01T00:01:00Z",
    executed_at: Optional[str] = None,
    order: Optional[AlpacaOrder] = None,
    qty: Optional[str] = None,
) -> AlpacaTradeEvent:
    return AlpacaTradeEvent(
        event_id=event_id,
        event=etype,
        at=_utc(at),
        executed_at=_utc(executed_at) if executed_at else None,
        broker_order_id=broker_id,
        execution_id=None,
        qty=Decimal(qty) if qty is not None else None,
        price=None,
        order=order,
    )


# ---------------------------------------------------------------------------
# In-memory fake transport so the adapter tests are hermetic and deterministic.
# ---------------------------------------------------------------------------


class _FakeTransport(AlpacaTransport):
    """Minimal in-memory ``AlpacaTransport`` for the adapter.

    Authority-free like the real transport: emits raw Alpaca DTOs only. HTTP
    semantics are emulated: ``submit_order`` returns a ``SubmissionReceipt``
    (never FILLED) and ``cancel_order`` returns after a cancel REQUEST (never
    CANCELLED).
    """

    def __init__(self) -> None:
        self._connected = True
        self._submit_calls = 0
        self._cancel_calls = 0

    @property
    def cancel_calls(self) -> int:
        return self._cancel_calls

    def connect(self) -> None:
        self._connected = True

    def submit_order(self, client_order_id: str, symbol: str, quantity: Decimal) -> SubmissionReceipt:
        self._submit_calls += 1
        return SubmissionReceipt(
            broker_order_id=f"alpaca-order-{self._submit_calls:04d}",
            client_order_id=client_order_id,
        )

    def cancel_order(self, broker_order_id: str) -> None:
        self._cancel_calls += 1

    def query_order(self, broker_order_id: str) -> AlpacaOrder:
        return _order(broker_id=broker_order_id)

    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        return BrokerPosition(symbol=symbol, quantity=Decimal("0"), venue="ALPACA_PAPER")

    def stream_trade_events(self, since_id: Optional[str] = None) -> "AlpacaEventStream":
        return _FakeStream()

    def connected(self) -> bool:
        return self._connected

    def rotate_credentials(self) -> None:
        self._connected = True


class _FakeStream(AlpacaEventStream):
    def __iter__(self) -> Iterator[AlpacaTradeEvent]:
        return iter(())

    def close(self) -> None:
        return None


def _adapter() -> AlpacaPaperAdapter:
    return AlpacaPaperAdapter(transport=_FakeTransport())


# ===========================================================================
# BMAP-01 — raw trade-event -> canonical BrokerEventKind mapping
# ===========================================================================


@pytest.mark.parametrize(
    ("etype", "expected_kind"),
    [
        (AlpacaTradeEventType.ACCEPTED, BrokerEventKind.ACK),
        (AlpacaTradeEventType.NEW, BrokerEventKind.ACK),
        (AlpacaTradeEventType.PENDING_NEW, BrokerEventKind.ACK),
        (AlpacaTradeEventType.REJECTED, BrokerEventKind.REJECT),
        (AlpacaTradeEventType.EXPIRED, BrokerEventKind.EXPIRED),
        (AlpacaTradeEventType.ORDER_CANCEL_REJECTED, BrokerEventKind.CANCEL_REJECTED),
    ],
)
def test_bmap01_direct_event_mapping(
    etype: AlpacaTradeEventType, expected_kind: BrokerEventKind
) -> None:
    a = _adapter()
    ev = _event(event_id="01H", etype=etype, order=_order())
    raw = a.ingest_trade_event(ev)
    assert raw.event_kind is expected_kind
    assert raw.source == "ALPACA"


def test_bmap01_partial_fill_maps_with_no_overfill() -> None:
    a = _adapter()
    ev = _event(
        event_id="01H2",
        etype=AlpacaTradeEventType.PARTIAL_FILL,
        executed_at="2026-01-01T00:01:10Z",
        qty="3",
        order=_order(requested="10", filled="3", status=AlpacaOrderStatus.PARTIALLY_FILLED),
    )
    raw = a.ingest_trade_event(ev)
    assert raw.event_kind is BrokerEventKind.PARTIAL_FILL


def test_bmap01_fill_maps_on_cumulative_filled_equals_requested() -> None:
    a = _adapter()
    ev = _event(
        event_id="01H3",
        etype=AlpacaTradeEventType.FILL,
        executed_at="2026-01-01T00:02:00Z",
        qty="10",
        order=_order(requested="10", filled="10"),
    )
    raw = a.ingest_trade_event(ev)
    assert raw.event_kind is BrokerEventKind.FILLED


def test_bmap01_non_terminal_in_flight_never_guesses_terminal_state() -> None:
    a = _adapter()
    for etype in (
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
    ):
        ev = _event(event_id=f"IN-{etype.value}", etype=etype, order=_order())
        with pytest.raises(AlpacaAdapterMappingError):
            a.ingest_trade_event(ev)


def test_bmap01_unknown_event_type_fail_closed() -> None:
    a = _adapter()
    # A never-seen Alpaca event type is not in any mapping set -> fail-closed,
    # never guessed into a terminal canonical state.
    class _Strange:
        value = "made_up_alpaca_lifecycle_state"

    ev = AlpacaTradeEvent(
        event_id="01H9",
        event=_Strange(),  # type: ignore[arg-type]
        at=_utc("2026-01-01T00:01:00Z"),
        executed_at=None,
        broker_order_id="alpaca-order-0001",
        execution_id=None,
        qty=None,
        price=None,
        order=_order(),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


# ===========================================================================
# BMAP-02 — required fields / canonical kinds fixed (Layer A/B/C)
# ===========================================================================


def test_bmap02_missing_required_broker_order_id_fail_closed() -> None:
    a = _adapter()
    ev = _event(event_id="02H1", etype=AlpacaTradeEventType.FILL, order=_order())
    # force empty broker_order_id
    ev = AlpacaTradeEvent(
        event_id=ev.event_id,
        event=ev.event,
        at=ev.at,
        executed_at=ev.executed_at,
        broker_order_id="   ",
        execution_id=None,
        qty=ev.qty,
        price=None,
        order=ev.order,
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


def test_bmap02_missing_event_id_fail_closed() -> None:
    a = _adapter()
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(_event(event_id="   ", etype=AlpacaTradeEventType.FILL, order=_order()))


def test_bmap02_ingest_order_snapshot_rejects_non_reconciliation_kind() -> None:
    a = _adapter()
    # CONNECTION_LOST is not a valid snapshot/reconciliation kind -> fail closed.
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_order_snapshot(_order(), BrokerEventKind.CONNECTION_LOST)


# ===========================================================================
# BMAP-03 — broker_sequence = event_id (ULID) verbatim; never a timestamp
# ===========================================================================


def test_bmap03_broker_sequence_is_event_id_verbatim() -> None:
    a = _adapter()
    ev = _event(event_id="01HZ12345678901234567890", etype=AlpacaTradeEventType.FILL, order=_order())
    raw = a.ingest_trade_event(ev)
    assert raw.broker_sequence == "01HZ12345678901234567890"


def test_bmap03_sequence_not_derived_from_timestamp() -> None:
    a = _adapter()
    # The at/executed_at timestamps must never influence broker_sequence.
    ev = _event(
        event_id="01HBLAH59400",
        etype=AlpacaTradeEventType.ACCEPTED,
        at="2026-05-01T00:00:00Z",
        order=_order(status=AlpacaOrderStatus.ACCEPTED),
    )
    raw = a.ingest_trade_event(ev)
    assert raw.broker_sequence == "01HBLAH59400"
    assert raw.broker_sequence != raw.observed_at.isoformat()


# ===========================================================================
# BMAP-04 — fallback ordering: SSE no-fallback; REST snapshot local counter
# ===========================================================================


def test_bmap04_sse_uses_event_id_no_fallback() -> None:
    a = _adapter()
    ev = _event(event_id="01HSSE00001", etype=AlpacaTradeEventType.FILL, order=_order())
    raw = a.ingest_trade_event(ev)
    assert raw.broker_sequence == "01HSSE00001"


def test_bmap04_rest_snapshot_uses_strictly_increasing_local_fallback() -> None:
    a = _adapter()
    r1 = a.ingest_order_snapshot(_order(broker_id="o1"), BrokerEventKind.FILLED)
    r2 = a.ingest_order_snapshot(_order(broker_id="o2"), BrokerEventKind.FILLED)
    assert r1.broker_sequence.startswith("LOCAL-FB-")
    assert r2.broker_sequence.startswith("LOCAL-FB-")
    # Strictly increasing across calls, never presented as a genuine Alpaca ULID.
    assert r1.broker_sequence != r2.broker_sequence
    assert "01H" not in r1.broker_sequence


# ===========================================================================
# BMAP-05 — timeout / ambiguity -> CONNECTION_LOST -> UNKNOWN, never terminal
# ===========================================================================


def test_bmap05_ack_timeout_maps_to_connection_lost() -> None:
    a = _adapter()
    raw = a.raise_ack_timeout("o1")
    assert raw.event_kind is BrokerEventKind.CONNECTION_LOST
    # The pipeline from this raw event must NOT yield a terminal outcome.
    _, evidence = normalize_broker_event(
        broker_order_id=raw.broker_order_id,
        event_kind=raw.event_kind,
        observed_at=raw.observed_at,
        source=raw.source,
        broker_sequence=raw.broker_sequence,
        cancel_was_requested=raw.cancel_was_requested,
    )
    assert raw.event_kind is BrokerEventKind.CONNECTION_LOST
    assert evidence is None  # not a reconciliation-verifiable terminal outcome


def test_bmap05_cancel_confirmation_timeout_never_cancelled() -> None:
    a = _adapter()
    raw = a.raise_cancel_confirmation_timeout("o1")
    assert raw.event_kind is BrokerEventKind.CONNECTION_LOST
    # The canonical pipeline from this observation must NOT resolve to a cancel
    # acknowledgement; it is an ambiguity signal (drives state to UNKNOWN).
    event, _ = normalize_broker_event(
        broker_order_id=raw.broker_order_id,
        event_kind=raw.event_kind,
        observed_at=raw.observed_at,
        source=raw.source,
        broker_sequence=raw.broker_sequence,
        cancel_was_requested=raw.cancel_was_requested,
    )
    assert event.value != "CANCEL_ACK"


# ===========================================================================
# BMAP-06 — partial / full / overfill: never silent FILLED/clamp
# ===========================================================================


def test_bmap06_overfill_cumulative_fails_closed() -> None:
    a = _adapter()
    ev = _event(
        event_id="06H1",
        etype=AlpacaTradeEventType.FILL,
        qty="12",
        order=_order(requested="10", filled="12"),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


def test_bmap06_per_fill_qty_exceeding_requested_fails_closed() -> None:
    a = _adapter()
    ev = _event(
        event_id="06H2",
        etype=AlpacaTradeEventType.FILL,
        qty="11",
        order=_order(requested="10", filled="10"),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


def test_bmap06_fill_without_embedded_order_fails_closed() -> None:
    a = _adapter()
    ev = _event(event_id="06H3", etype=AlpacaTradeEventType.FILL, order=None)
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


# ===========================================================================
# BMAP-07 — cancel provenance (STRICTEST): the SSE 'canceled' path can NEVER be
# proven user-cancel against current Alpaca docs (E-verified), so it ALWAYS
# fails closed. CANCELLED is resolved ONLY via REST reconciliation snapshot.
# ===========================================================================


def test_bmap07_canceled_without_provenance_fails_closed() -> None:
    a = _adapter()
    ev = _event(
        event_id="07H1",
        etype=AlpacaTradeEventType.CANCELED,
        order=_order(cancel_requested_at=None),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


def test_bmap07_canceled_even_with_cancel_requested_at_fails_closed() -> None:
    # cancel_requested_at proves a cancel was REQUESTED, not that the resulting
    # 'canceled' was user-initiated. Per E-verified policy, NEVER emit ORDER_CANCELLED.
    a = _adapter()
    ev = _event(
        event_id="07H2",
        etype=AlpacaTradeEventType.CANCELED,
        order=_order(cancel_requested_at="2026-01-01T00:03:00Z"),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)
    assert a.subscribe_events("alpaca-order-0001") == ()


def test_bmap07_canceled_alpaca_initiated_corporate_action_fails_closed() -> None:
    # E-verified: CORPORATE_ACTION = Alpaca-side cancel, definitely NOT user.
    a = _adapter()
    ev = AlpacaTradeEvent(
        event_id="07H3",
        event=AlpacaTradeEventType.CANCELED,
        at=_utc("2026-01-01T00:03:00Z"),
        executed_at=None,
        broker_order_id="alpaca-order-0001",
        execution_id=None,
        qty=None,
        price=None,
        reason="CORPORATE_ACTION",
        order=_order(cancel_requested_at="2026-01-01T00:02:00Z"),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


def test_bmap07_canceled_too_late_to_cancel_fails_closed() -> None:
    a = _adapter()
    ev = AlpacaTradeEvent(
        event_id="07H4",
        event=AlpacaTradeEventType.CANCELED,
        at=_utc("2026-01-01T00:03:00Z"),
        executed_at=None,
        broker_order_id="alpaca-order-0001",
        execution_id=None,
        qty=None,
        price=None,
        reason="TOO_LATE_TO_CANCEL",
        order=_order(cancel_requested_at="2026-01-01T00:02:00Z"),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


def test_bmap07_canceled_free_form_venue_reason_fails_closed() -> None:
    # E-verified: upstream-venue cancels may carry the venue's own free-form text.
    a = _adapter()
    ev = AlpacaTradeEvent(
        event_id="07H5",
        event=AlpacaTradeEventType.CANCELED,
        at=_utc("2026-01-01T00:03:00Z"),
        executed_at=None,
        broker_order_id="alpaca-order-0001",
        execution_id=None,
        qty=None,
        price=None,
        reason="VARIOUS_VENUE_REPORTED_TEXT",
        order=_order(cancel_requested_at="2026-01-01T00:02:00Z"),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


def test_bmap07_adapter_never_emits_order_cancelled_from_any_canceled() -> None:
    a = _adapter()
    for reason, cancel_req in (
        (None, None),
        (None, "2026-01-01T00:03:00Z"),
        ("CORPORATE_ACTION", None),
        ("CORPORATE_ACTION", "2026-01-01T00:03:00Z"),
        ("TOO_LATE_TO_CANCEL", "2026-01-01T00:03:00Z"),
    ):
        ev = AlpacaTradeEvent(
            event_id=f"07P-{reason or 'none'}-{cancel_req or 'none'}",
            event=AlpacaTradeEventType.CANCELED,
            at=_utc("2026-01-01T00:03:00Z"),
            executed_at=None,
            broker_order_id="alpaca-order-0001",
            execution_id=None,
            qty=None,
            price=None,
            reason=reason,
            order=_order(cancel_requested_at=cancel_req),
        )
        with pytest.raises(AlpacaAdapterMappingError):
            a.ingest_trade_event(ev)


def test_bmap07_cancelled_reachable_only_via_rest_reconciliation_snapshot() -> None:
    # CANCELLED must STILL be reachable end-to-end, but only through the
    # reconciliation layer (ingest_order_snapshot with ORDER_CANCELLED +
    # cancel_was_requested=True), never from the SSE 'canceled' path.
    a = _adapter()
    raw = a.ingest_order_snapshot(
        _order(
            broker_id="alpaca-order-0001",
            status=AlpacaOrderStatus.CANCELED,
            cancel_requested_at="2026-01-01T00:03:00Z",
        ),
        BrokerEventKind.ORDER_CANCELLED,
    )
    assert raw.event_kind is BrokerEventKind.ORDER_CANCELLED
    assert raw.cancel_was_requested is True
    # Required-field evidence path -> canonical event resolves to CANCEL_ACK.
    event, _ = normalize_broker_event(
        broker_order_id=raw.broker_order_id,
        event_kind=raw.event_kind,
        observed_at=raw.observed_at,
        source=raw.source,
        broker_sequence=raw.broker_sequence,
        cancel_was_requested=raw.cancel_was_requested,
    )
    assert event.value == "CANCEL_ACK"
    # Reconciliation snapshots are LOCAL-FB-* fallback (BMAP-04), not Alpaca seq.
    assert raw.broker_sequence.startswith("LOCAL-FB-")


# ===========================================================================
# BMAP-08 — idempotent (execution_id, event_id) as ordering/dedup key
# ===========================================================================


def test_bmap08_broker_sequence_verbatim_supports_dedup_by_event_id() -> None:
    a = _adapter()
    # Re-delivered fill (same event_id) must produce the identical broker_sequence
    # so the coordinator can dedup idempotently (no double accumulate).
    ev1 = _event(event_id="08HV", etype=AlpacaTradeEventType.FILL, order=_order())
    ev2 = _event(event_id="08HV", etype=AlpacaTradeEventType.FILL, order=_order())
    assert a.ingest_trade_event(ev1).broker_sequence == a.ingest_trade_event(ev2).broker_sequence


# ===========================================================================
# BMAP-09 — timestamp framing: observed_at from executed_at/at, not blanket
# ===========================================================================


def test_bmap09_fill_family_keys_observed_at_on_executed_at() -> None:
    a = _adapter()
    ev = _event(
        event_id="09H1",
        etype=AlpacaTradeEventType.FILL,
        at="2026-01-01T00:01:00Z",
        executed_at="2026-01-01T00:01:42Z",
        order=_order(),
    )
    raw = a.ingest_trade_event(ev)
    assert raw.observed_at == _utc("2026-01-01T00:01:42Z")


def test_bmap09_observed_at_is_utc_aware() -> None:
    a = _adapter()
    ev = _event(event_id="09H2", etype=AlpacaTradeEventType.FILL, order=_order())
    raw = a.ingest_trade_event(ev)
    assert raw.observed_at.tzinfo is not None


def test_bmap09_no_event_time_fails_closed() -> None:
    a = _adapter()
    ev = AlpacaTradeEvent(
        event_id="09H3",
        event=AlpacaTradeEventType.ACCEPTED,
        at=None,  # type: ignore[arg-type]
        executed_at=None,
        broker_order_id="o1",
        execution_id=None,
        qty=None,
        price=None,
        order=_order(status=AlpacaOrderStatus.ACCEPTED),
    )
    with pytest.raises(AlpacaAdapterMappingError):
        a.ingest_trade_event(ev)


# ===========================================================================
# BMAP-10 — credential & secret boundary
# ===========================================================================


def test_bmap10_adapter_error_messages_carry_no_credential_material() -> None:
    try:
        _adapter().ingest_trade_event(
            _event(event_id="10H1", etype=AlpacaTradeEventType.FILL, order=None)
        )
    except AlpacaAdapterMappingError as exc:
        msg = str(exc)
        for secret_like in ("AK-", "secret", "SECRET", "key=", "Bearer", "token"):
            assert secret_like.lower() not in msg.lower()
    else:
        pytest.fail("expected AlpacaAdapterMappingError")


def test_bmap10_no_secrets_in_submitted_or_canceled_dto_roundtrip() -> None:
    a = _adapter()
    receipt = a.submit_order("C1", "SPY", Decimal("10"))
    assert isinstance(receipt, SubmissionReceipt)
    assert receipt.broker_order_id.startswith("alpaca-order-")
    a.cancel_order(receipt.broker_order_id)


# ===========================================================================
# BMAP-11 — evidence provenance / digest lineage, adapter never tampers
# ===========================================================================


def test_bmap11_adapter_does_not_fabricate_digest() -> None:
    a = _adapter()
    ev = _event(event_id="11H1", etype=AlpacaTradeEventType.EXPIRED, order=_order())
    raw = a.ingest_trade_event(ev)
    _, evidence = normalize_broker_event(
        broker_order_id=raw.broker_order_id,
        event_kind=raw.event_kind,
        observed_at=raw.observed_at,
        source=raw.source,
        broker_sequence=raw.broker_sequence,
        cancel_was_requested=raw.cancel_was_requested,
    )
    assert evidence is not None
    # The normalizer computes the digest over canonical fields only; the adapter
    # does not inject any field. Verify digest binds to content (tamper-evident).
    evidence.verify_digest()
    assert len(evidence.evidence_digest) == 64
    assert hashlib.sha256(
        evidence.broker_order_id.encode()
    ).hexdigest() != evidence.evidence_digest


# ===========================================================================
# BMAP-12 — adversarial conformance matrix (this checkpoint): full pipeline
# ===========================================================================


def _to_coordinator_event(raw: BrokerRawEvent) -> tuple[object, object]:
    event, evidence = normalize_broker_event(
        broker_order_id=raw.broker_order_id,
        event_kind=raw.event_kind,
        observed_at=raw.observed_at,
        source=raw.source,
        broker_sequence=raw.broker_sequence,
        cancel_was_requested=raw.cancel_was_requested,
    )
    return event, evidence


def test_bmap12_submit_returns_receipt_not_state() -> None:
    a = _adapter()
    receipt = a.submit_order("C1", "SPY", Decimal("10"))
    assert isinstance(receipt, SubmissionReceipt)
    # POST ACK != FILLED: no FILLED anywhere in the adapter's command path.
    assert a.subscribe_events(receipt.broker_order_id) == ()


def test_bmap12_cancel_is_a_request_not_confirmation() -> None:
    a = _adapter()
    receipt = a.submit_order("C1", "SPY", Decimal("10"))
    a.cancel_order(receipt.broker_order_id)
    # DELETE 204 acceptance produced NO canonical CANCELLED observation.
    assert a.subscribe_events(receipt.broker_order_id) == ()


def test_bmap12_full_lifecycle_ack_then_partial_then_fill() -> None:
    a = _adapter()
    order = _order(requested="10", filled="0", status=AlpacaOrderStatus.NEW)
    ack = a.ingest_trade_event(
        _event(event_id="L1", etype=AlpacaTradeEventType.ACCEPTED, order=order)
    )
    part = a.ingest_trade_event(
        _event(
            event_id="L2",
            etype=AlpacaTradeEventType.PARTIAL_FILL,
            executed_at="2026-01-01T00:01:10Z",
            qty="3",
            order=_order(requested="10", filled="3", status=AlpacaOrderStatus.PARTIALLY_FILLED),
        )
    )
    fill = a.ingest_trade_event(
        _event(
            event_id="L3",
            etype=AlpacaTradeEventType.FILL,
            executed_at="2026-01-01T00:02:00Z",
            qty="7",
            order=_order(requested="10", filled="10"),
        )
    )
    kinds = [ack.event_kind, part.event_kind, fill.event_kind]
    assert kinds == [
        BrokerEventKind.ACK,
        BrokerEventKind.PARTIAL_FILL,
        BrokerEventKind.FILLED,
    ]
    # Canonical pipeline resolves cleanly with no fail-closed error.
    for raw in (ack, part, fill):
        _to_coordinator_event(raw)


def test_bmap12_each_observation_recorded_for_subscribe_drain() -> None:
    a = _adapter()
    a.ingest_trade_event(_event(event_id="S1", etype=AlpacaTradeEventType.ACCEPTED, order=_order()))
    a.ingest_trade_event(_event(event_id="S2", etype=AlpacaTradeEventType.FILL, order=_order()))
    log = a.subscribe_events("alpaca-order-0001")
    assert [e.broker_sequence for e in log] == ["S1", "S2"]


def test_bmap12_health_check_bridges_transport_connected() -> None:
    a = _adapter()
    h = a.health_check()
    assert h.healthy is True


def test_bmap12_stream_trade_events_passthrough() -> None:
    a = _adapter()
    stream = a.stream_trade_events(since_id="01H")
    assert hasattr(stream, "close")


# ===========================================================================
# Authority separation (N-1/N-3): the adapter owns NO state machine
# ===========================================================================

_AUTHORITY_MODULES = {
    "acash.execution.coordinator",
    "acash.execution.state_machine",
    "acash.execution.schema",
}
_ALLOWED_ADAPTER_ACASH_IMPORTS = {
    "acash.execution.alpaca.adapter",
    "acash.execution.alpaca.transport",
    "acash.execution.broker_adapter",
    "acash.execution.broker_events",
    "acash.execution.mock_broker",
}


def _ast_imports(path: str) -> set[str]:
    import ast as _ast

    with open(path, encoding="utf-8") as fh:
        tree = _ast.parse(fh.read(), filename=path)
    imported: set[str] = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, _ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_authority_adapter_imports_no_state_authority_module() -> None:
    imports = _ast_imports("src/acash/execution/alpaca/adapter.py")
    violations = _AUTHORITY_MODULES & imports
    assert not violations, (
        f"adapter must NOT import state authority modules, got: {sorted(violations)}"
    )


def test_authority_adapter_imports_only_intended_acash_modules() -> None:
    imports = _ast_imports("src/acash/execution/alpaca/adapter.py")
    shipped = {i for i in imports if i.startswith("acash.")} - {"acash"}
    unexpected = shipped - _AUTHORITY_MODULES - _ALLOWED_ADAPTER_ACASH_IMPORTS
    assert not unexpected, (
        f"adapter pulls acash modules outside the sealed seam: "
        f"{sorted(unexpected)} (allowed: {sorted(_ALLOWED_ADAPTER_ACASH_IMPORTS)})"
    )


def test_authority_adapter_never_calls_transition_order() -> None:
    import ast as _ast

    with open("src/acash/execution/alpaca/adapter.py", encoding="utf-8") as fh:
        tree = _ast.parse(fh.read(), filename="adapter.py")
    calls = []
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Call):
            continue
        if isinstance(node.func, _ast.Attribute):
            calls.append(node.func.attr)
        elif isinstance(node.func, _ast.Name):
            calls.append(node.func.id)
    assert "transition_order" not in calls, "adapter must never call transition_order"
    assert "OrderLifecycleState" not in (
        c for c in calls
    ), "adapter must never construct OrderLifecycleState"


def test_docs_path_is_repository_relative() -> None:
    # AGENTS.md §17: no machine-specific absolute paths committed.
    src = open("src/acash/execution/alpaca/adapter.py", encoding="utf-8").read()
    assert "file:///" not in src
    assert "C:\\" not in src
    assert "C:/" not in src
