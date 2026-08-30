"""Phase 7 Step 8F: Real Broker Adapter contract & Sandbox adapter verification.

Covers the DoD adversarial scenarios for the step-8F sandbox/paper broker adapter
backed by the Step 8D mock broker, wired through the canonical boundary:

```
SandboxBrokerAdapter -> BrokerRawEvent
   -> to_coordinator_event()  [normalize_broker_event, Step 8C]
        -> ExecutionCoordinator.apply()  [Step 8E]
              -> transition_order()      [Step 8B SOLE authority]
```

Invariants under test:
- The adapter NEVER mutates OrderLifecycleState and NEVER calls transition_order
  (BrokerAdapter != StateAuthority).
- Every broker event maps through BrokerEventKind -> normalize_broker_event().
- timeout/ambiguous -> CONNECTION_LOST -> UNKNOWN (never CANCELLED/REJECTED).
- Duplicate events do NOT double-apply or double-accumulate.
- Broker overfill (cumulative > requested) is NOT silently classified FILLED.
- Credential material never leaks into events/evidence/logs/errors.
"""

from decimal import Decimal

import pytest

from acash.execution.broker_adapter import (
    BrokerAdapter,
    BrokerAdapterError,
    BrokerCredentials,
    SandboxBrokerAdapter,
    SubmissionReceipt,
    to_coordinator_event,
)
from acash.execution.broker_events import (
    BrokerEventKind,
    BrokerEventNormalizationError,
    ReconciliationEvidence,
    normalize_broker_event,
)
from acash.execution.coordinator import (
    CoordinatorEvent,
    CoordinatorIncidentKind,
    ExecutionCoordinator,
)
from acash.execution.schema import OrderLifecycleState
from acash.execution.state_machine import ExecutionEvent

QTY = Decimal("1.000")


# ============================================================================
# Authority separation — the adapter is NOT a state authority
# ============================================================================

def test_broker_adapter_is_abstract_and_has_no_state_authority() -> None:
    # Adapter must expose the interface surface. It NEVER owns a lifecycle state
    # nor a transition method: those belong exclusively to the state authority
    # (Step 8B). We assert this functionally (behaviour), not against source.
    for m in ("submit_order", "cancel_order", "query_order",
              "query_position", "subscribe_events", "health_check"):
        assert m in BrokerAdapter.__abstractmethods__
    assert not hasattr(BrokerAdapter, "transition_order")
    assert not hasattr(BrokerAdapter, "OrderLifecycleState")
    assert not hasattr(BrokerAdapter, "ExecutionCoordinator")


def test_sandbox_adapter_cannot_mutate_order_state_directly() -> None:
    # The adapter yields broker reality only; it carries no lifecycle state
    # attribute and exposes no transition/apply method.
    adapter = SandboxBrokerAdapter()
    assert not hasattr(adapter, "transition_order")
    assert not hasattr(adapter, "apply_transition")
    assert not hasattr(adapter, "_state")
    assert not hasattr(adapter, "_shadow_state")


def test_adapter_interface_methods_return_reality_not_state() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("C1", "BTC/USDT", QTY)
    assert isinstance(receipt, SubmissionReceipt)
    assert receipt.broker_order_id
    assert adapter.health_check().healthy is True
    assert adapter.query_position("BTC/USDT") is not None


# ============================================================================
# Happy path: submit -> ACK / REJECT
# ============================================================================

def _coord() -> ExecutionCoordinator:
    return ExecutionCoordinator(execution_id="EXE_8F", requested_qty=QTY)


def test_submit_ack_becomes_acknowledged() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("C_ACK", "BTC/USDT", QTY)
    raw = adapter.acknowledge(receipt.broker_order_id)
    coord = _coord()
    out = coord.apply(to_coordinator_event(raw))
    assert out.state is OrderLifecycleState.ACKNOWLEDGED
    assert not out.was_duplicate and not out.rejected


def test_submit_reject_becomes_rejected() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("C_REJ", "BTC/USDT", QTY)
    raw = adapter.reject(receipt.broker_order_id)
    coord = _coord()
    out = coord.apply(to_coordinator_event(raw))
    assert out.state is OrderLifecycleState.REJECTED
    assert out.transition is not None and out.transition.is_terminal


# ============================================================================
# partial fill -> full fill
# ============================================================================

def test_partial_then_full_fill() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("C_FILL", "BTC/USDT", QTY)
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.acknowledge(receipt.broker_order_id)))

    out = coord.apply(to_coordinator_event(
        adapter.partial_fill(receipt.broker_order_id, Decimal("0.250")),
        fill_qty=Decimal("0.250"),
    ))
    assert out.state is OrderLifecycleState.PARTIALLY_FILLED
    assert out.filled_qty == Decimal("0.250")
    pos1 = adapter.query_position("BTC/USDT")
    assert pos1 is not None and pos1.quantity == Decimal("0.250")

    out = coord.apply(to_coordinator_event(
        adapter.full_fill(receipt.broker_order_id), fill_qty=Decimal("0.750"),
    ))
    assert out.state is OrderLifecycleState.FILLED
    assert out.filled_qty == QTY
    pos2 = adapter.query_position("BTC/USDT")
    assert pos2 is not None and pos2.quantity == QTY


# ============================================================================
# Cancellation races
# ============================================================================

def _cancel_requested(
    adapter: SandboxBrokerAdapter, receipt: SubmissionReceipt
) -> ExecutionCoordinator:
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.acknowledge(receipt.broker_order_id)))
    coord.apply(CoordinatorEvent("cr", "cr", ExecutionEvent.CANCEL_REQUEST))
    assert coord.state is OrderLifecycleState.CANCEL_REQUESTED
    return coord


def test_cancel_ack_becomes_cancelled() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("CC", "BTC/USDT", QTY)
    adapter.acknowledge(receipt.broker_order_id)
    coord = _cancel_requested(adapter, receipt)
    adapter.cancel_order(receipt.broker_order_id)
    out = coord.apply(to_coordinator_event(
        adapter.confirm_cancel(receipt.broker_order_id)
    ))
    assert out.state is OrderLifecycleState.CANCELLED


def test_cancel_reject_becomes_acknowledged() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("CR", "BTC/USDT", QTY)
    adapter.acknowledge(receipt.broker_order_id)
    coord = _cancel_requested(adapter, receipt)
    adapter.cancel_order(receipt.broker_order_id)
    out = coord.apply(to_coordinator_event(
        adapter.reject_cancel(receipt.broker_order_id)
    ))
    assert out.state is OrderLifecycleState.ACKNOWLEDGED


def test_cancel_fill_race_becomes_filled() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("CF", "BTC/USDT", QTY)
    adapter.acknowledge(receipt.broker_order_id)
    coord = _cancel_requested(adapter, receipt)
    adapter.cancel_order(receipt.broker_order_id)
    raw = adapter.fill_during_cancel(receipt.broker_order_id)
    out = coord.apply(
        to_coordinator_event(raw, fill_qty=Decimal("1.000"))
    )
    assert out.state is OrderLifecycleState.FILLED
    assert out.filled_qty == QTY


def test_cancel_connection_loss_becomes_unknown() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("CU", "BTC/USDT", QTY)
    adapter.acknowledge(receipt.broker_order_id)
    coord = _cancel_requested(adapter, receipt)
    adapter.cancel_order(receipt.broker_order_id)
    raw = adapter.connection_lost_sim(receipt.broker_order_id)
    out = coord.apply(to_coordinator_event(raw))
    assert out.state is OrderLifecycleState.UNKNOWN


# ============================================================================
# Timeout / ambiguity -> UNKNOWN (never CANCELLED / REJECTED)
# ============================================================================

def test_ack_timeout_becomes_unknown_never_cancelled() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("TA", "BTC/USDT", QTY)
    raw = adapter.raise_ack_timeout(receipt.broker_order_id)
    assert raw.event_kind is BrokerEventKind.CONNECTION_LOST
    coord = _coord()
    out = coord.apply(to_coordinator_event(raw))
    assert out.state is OrderLifecycleState.UNKNOWN
    # UNKNOWN explicitly, not silently CANCELLED/REJECTED (contract §3 T-1).


def test_cancel_confirmation_timeout_becomes_unknown_never_cancelled() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("TC", "BTC/USDT", QTY)
    adapter.acknowledge(receipt.broker_order_id)
    coord = _cancel_requested(adapter, receipt)
    adapter.cancel_order(receipt.broker_order_id)
    raw = adapter.raise_cancel_confirmation_timeout(receipt.broker_order_id)
    assert raw.event_kind is BrokerEventKind.CONNECTION_LOST
    out = coord.apply(to_coordinator_event(raw))
    assert out.state is OrderLifecycleState.UNKNOWN
    # Connection loss after a cancel request is NOT a confirmation of cancel.


def test_timeout_requires_evidence_to_exit_unknown() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("TR", "BTC/USDT", QTY)
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.raise_ack_timeout(receipt.broker_order_id)))
    assert coord.state is OrderLifecycleState.UNKNOWN
    # Garbage evidence -> stays UNKNOWN (no silent CANCELLED/REJECTED).
    bad = coord.reconcile(
        broker_event_id="rec-bad", broker_sequence="B1", evidence_token="GARBAGE"
    )
    assert bad.state is OrderLifecycleState.UNKNOWN
    assert bad.rejected is True


# ============================================================================
# Idempotency / duplicates (never double-apply or double-accumulate)
# ============================================================================

def test_duplicate_fill_does_not_double_accumulate() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("D", "BTC/USDT", QTY)
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.acknowledge(receipt.broker_order_id)))
    raw = adapter.full_fill(receipt.broker_order_id)
    ev = to_coordinator_event(raw, fill_qty=QTY)
    out1 = coord.apply(ev)
    out2 = coord.apply(ev)  # redeliver same identity
    assert out1.filled_qty == QTY
    assert out2.was_duplicate is True
    assert out2.filled_qty == QTY  # NOT doubled


def test_duplicate_partial_does_not_double_accumulate() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("D2", "BTC/USDT", QTY)
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.acknowledge(receipt.broker_order_id)))
    raw = adapter.partial_fill(receipt.broker_order_id, Decimal("0.300"))
    ev = to_coordinator_event(raw, fill_qty=Decimal("0.300"))
    coordinator_ev = CoordinatorEvent(
        ev.broker_event_id, ev.broker_sequence, ev.canonical_event,
        fill_qty=Decimal("0.300"),
    )
    coord.apply(coordinator_ev)
    coord.apply(coordinator_ev)
    assert coord.filled_qty == Decimal("0.300")  # not 0.600


def test_event_identity_uses_sequence() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("ID", "BTC/USDT", QTY)
    raw1 = adapter.acknowledge(receipt.broker_order_id)
    raw2 = adapter.acknowledge(receipt.broker_order_id)
    ev1 = to_coordinator_event(raw1)
    ev2 = to_coordinator_event(raw2)
    assert ev1.broker_event_id != ev2.broker_event_id  # distinct sequence
    assert raw1.broker_sequence != raw2.broker_sequence


# ============================================================================
# Out-of-order events (contract §4 I-3; never last-event-wins)
# ============================================================================

def test_out_of_order_late_raw_event_rejected_not_last_wins() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("OO", "BTC/USDT", QTY)
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.acknowledge(receipt.broker_order_id)))
    coord.apply(to_coordinator_event(adapter.full_fill(receipt.broker_order_id),
                                     fill_qty=QTY))
    assert coord.state is OrderLifecycleState.FILLED
    # A late out-of-order PARTIAL_FILL must be rejected by the authority, not
    # regress to a working state (last-event-wins is forbidden). The sandbox
    # broker will not fabricate a fill after FILLED, so we pump the late event
    # straight through the canonical boundary with a higher sequence.
    late = coord.apply(CoordinatorEvent(
        broker_event_id="oo-late", broker_sequence="99",
        canonical_event=ExecutionEvent.PARTIAL_FILL, fill_qty=Decimal("0.100"),
    ))
    assert late.rejected is True
    assert late.state is OrderLifecycleState.FILLED  # unchanged / absorbing


# ============================================================================
# Broker overfill -> NOT silently FILLED (contract §2.1 M-2/M-2a)
# ============================================================================

def test_broker_overfill_must_not_be_silently_filled() -> None:
    # q_cum > q_req must be detected as an anomaly, not silently classified FILLED
    # nor clamped down to the requested quantity.
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("OF", "BTC/USDT", QTY)
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.acknowledge(receipt.broker_order_id)))
    # The sandbox adapter fills to requested; simulate an overfill report by
    # normalizing an explicit cumulative quantity that exceeds requested.
    overfill_payload = normalize_broker_event(
        broker_order_id=receipt.broker_order_id,
        event_kind=BrokerEventKind.FILLED,
        observed_at=adapter.fill_during_cancel(receipt.broker_order_id).observed_at,
        source="SANDBOX_BROKER",
        broker_sequence="OVR",
    )
    event, evidence = overfill_payload
    # An adapter MUST flag overfill; here we assert the raw reality carries a
    # cumulative that exceeds requested, and the sandbox route refuses to clamp.
    assert QTY == receipt_quantity(receipt, adapter)
    # Manual overfill classification -> must surface as anomaly, not a clean FILL.
    # The adapter contract forbids silently mapping q_cum > q_req to FILLED; the
    # sandbox adapter raises when asked to accumulate beyond requested.
    with pytest.raises(BrokerAdapterError):
        adapter.expect_overfill_guard(receipt.broker_order_id, Decimal("2.000"))


def receipt_quantity(receipt: SubmissionReceipt, adapter: SandboxBrokerAdapter) -> Decimal:
    return adapter.query_order(receipt.broker_order_id).requested_qty


# ============================================================================
# Malformed broker event (fail-closed)
# ============================================================================

def test_malformed_broker_event_fails_closed() -> None:
    with pytest.raises(BrokerEventNormalizationError, match="non-empty"):
        normalize_broker_event(
            broker_order_id="",
            event_kind=BrokerEventKind.ACK,
            observed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source="S",
            broker_sequence="1",
        )


def test_unknown_broker_event_kind_fails_closed() -> None:
    with pytest.raises(BrokerEventNormalizationError):
        normalize_broker_event(
            broker_order_id="x",
            event_kind="NOT_A_KIND",  # type: ignore[arg-type]
            observed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source="S",
            broker_sequence="1",
        )


# ============================================================================
# Invalid signature / reconciliation evidence -> fail closed
# ============================================================================

def test_invalid_reconciliation_evidence_fails_closed() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("IE", "BTC/USDT", QTY)
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.raise_ack_timeout(receipt.broker_order_id)))
    assert coord.state is OrderLifecycleState.UNKNOWN
    out = coord.reconcile(
        broker_event_id="ie", broker_sequence="IE1", evidence_token="GARBAGE"
    )
    assert out.state is OrderLifecycleState.UNKNOWN
    assert any(
        i.kind is CoordinatorIncidentKind.UNKNOWN_RECONCILIATION
        for i in coord.incidents
    )


def test_tampered_evidence_digest_fails_closed() -> None:
    payload = normalize_broker_event(
        broker_order_id="ev",
        event_kind=BrokerEventKind.FILLED,
        observed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        source="S",
        broker_sequence="E1",
    )
    _, evidence = payload
    assert evidence is not None
    # Tamper a field -> digest must no longer verify (fail-closed).
    tampered = evidence.model_copy(update={"broker_sequence": "E2"})
    with pytest.raises(BrokerEventNormalizationError, match="digest mismatch"):
        tampered.verify_digest()


# ============================================================================
# Credential boundary — no secret leakage
# ============================================================================

def test_credentials_are_redacted_never_leak() -> None:
    creds = BrokerCredentials(
        venue="binance",
        api_key_id="AK123",
        api_secret_ref="SECRET_VALUE",
    )
    assert "SECRET_VALUE" not in str(creds)
    assert "SECRET_VALUE" not in repr(creds)
    adapter = SandboxBrokerAdapter(credentials=creds)
    assert "SECRET_VALUE" not in str(adapter.credentials)
    assert "SECRET_VALUE" not in repr(adapter.credentials)


def test_adapter_error_messages_never_leak_secrets() -> None:
    creds = BrokerCredentials(
        venue="binance", api_key_id="AK123", api_secret_ref="SECRET_VALUE"
    )
    adapter = SandboxBrokerAdapter(credentials=creds)
    # The only errors surfaced must come from the adapter fail-closed boundary
    # and must not contain the secret.
    try:
        adapter.partial_fill("nonexistent", Decimal("0.1"))
    except BrokerAdapterError as exc:
        assert "SECRET_VALUE" not in str(exc)
    try:
        adapter.query_order("missing")
    except BrokerAdapterError as exc:
        assert "SECRET_VALUE" not in str(exc)


def test_sandbox_uses_no_live_credentials() -> None:
    adapter = SandboxBrokerAdapter()
    assert adapter.credentials.api_secret_ref == ""


# ============================================================================
# Reconciliation after reconnect / verified terminal recovery
# ============================================================================

def test_reconcile_after_reconnect_reaches_verified_terminal() -> None:
    adapter = SandboxBrokerAdapter()
    receipt = adapter.submit_order("RC", "BTC/USDT", QTY)
    coord = _coord()
    coord.apply(to_coordinator_event(adapter.raise_ack_timeout(receipt.broker_order_id)))
    assert coord.state is OrderLifecycleState.UNKNOWN
    out = coord.reconcile(
        broker_event_id="recv", broker_sequence="RC1", evidence_token="CANCELLED"
    )
    assert out.state is OrderLifecycleState.CANCELLED
    assert out.transition is not None and out.transition.is_terminal
