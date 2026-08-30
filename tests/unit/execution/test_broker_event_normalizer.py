"""Adversarial tests for Step 8C broker event normalizer.

Verifies the Step 8C contract:

$$\boxed{ \text{Broker Raw Event} \rightarrow \text{Canonical Execution Event} }$$

and the authority split: the normalizer produces a canonical ``ExecutionEvent``
+ typed ``ReconciliationEvidence``; it NEVER computes an order state. State
transition is exclusively ``transition_order()``.

Also verifies the structured-evidence audit trail (tamper-evident digest) and
fail-closed handling of ambiguous cancellation.
"""

from datetime import datetime, timezone
import hashlib
from typing import Optional

import pytest

from acash.execution.broker_events import (
    BrokerEventKind,
    BrokerEventNormalizationError,
    ReconciliationEvidence,
    normalize_broker_event,
)
from acash.execution.state_machine import (
    ExecutionEvent,
    transition_order,
)
from acash.execution.schema import OrderLifecycleState


def _now() -> datetime:
    return datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)


def _norm(
    kind: BrokerEventKind,
    *,
    cancel_was_requested: bool = False,
    broker_id: str = "BROKER_ORDER_1",
    seq: str = "SEQ_1",
) -> tuple[ExecutionEvent, Optional[ReconciliationEvidence]]:
    return normalize_broker_event(
        broker_order_id=broker_id,
        event_kind=kind,
        observed_at=_now(),
        source="BINANCE_FUTURES",
        broker_sequence=seq,
        cancel_was_requested=cancel_was_requested,
    )


# ============================================================================
# Deterministic mapping
# ============================================================================

def test_ack_maps_to_ack_without_evidence() -> None:
    event, evidence = _norm(BrokerEventKind.ACK)
    assert event is ExecutionEvent.ACK
    assert evidence is None


def test_reject_maps_to_reject_event() -> None:
    event, evidence = _norm(BrokerEventKind.REJECT)
    assert event is ExecutionEvent.REJECT
    assert isinstance(evidence, ReconciliationEvidence)


def test_partial_fill_maps_without_evidence() -> None:
    event, evidence = _norm(BrokerEventKind.PARTIAL_FILL)
    assert event is ExecutionEvent.PARTIAL_FILL
    assert evidence is None


def test_filled_maps_to_fill_with_evidence() -> None:
    event, evidence = _norm(BrokerEventKind.FILLED)
    assert event is ExecutionEvent.FILL
    assert isinstance(evidence, ReconciliationEvidence)
    assert evidence.observed_status is BrokerEventKind.FILLED


def test_cancel_rejected_maps_without_evidence() -> None:
    event, evidence = _norm(BrokerEventKind.CANCEL_REJECTED)
    assert event is ExecutionEvent.CANCEL_REJECT
    assert evidence is None


def test_expired_maps_with_evidence() -> None:
    event, evidence = _norm(BrokerEventKind.EXPIRED)
    assert event is ExecutionEvent.EXPIRY
    assert isinstance(evidence, ReconciliationEvidence)


def test_connection_lost_maps_without_evidence() -> None:
    event, evidence = _norm(BrokerEventKind.CONNECTION_LOST)
    assert event is ExecutionEvent.CONNECTION_LOST
    assert evidence is None


# ============================================================================
# Ambiguous cancellation — fail closed, never decide state by guessing
# ============================================================================

def test_order_cancelled_without_hint_fails_closed() -> None:
    with pytest.raises(BrokerEventNormalizationError, match="cancel_was_requested"):
        _norm(BrokerEventKind.ORDER_CANCELLED)


def test_order_cancelled_with_hint_maps_to_cancel_ack() -> None:
    event, evidence = _norm(
        BrokerEventKind.ORDER_CANCELLED, cancel_was_requested=True
    )
    assert event is ExecutionEvent.CANCEL_ACK
    assert isinstance(evidence, ReconciliationEvidence)
    assert evidence.observed_status is BrokerEventKind.ORDER_CANCELLED


# ============================================================================
# Evidence digest integrity (tamper-evident)
# ============================================================================

def test_evidence_digest_verifies() -> None:
    _, evidence = _norm(BrokerEventKind.FILLED, broker_id="B_1", seq="S_9")
    assert evidence is not None
    evidence.verify_digest()  # no raise == digest matches content


def test_evidence_digest_rejects_tampered_content() -> None:
    _, evidence = _norm(BrokerEventKind.FILLED)
    assert evidence is not None
    tampered = evidence.model_copy(update={"broker_sequence": "SEQ_TAMPERED"})
    with pytest.raises(BrokerEventNormalizationError, match="digest mismatch"):
        tampered.verify_digest()


def test_evidence_digest_is_deterministic() -> None:
    _, e1 = _norm(BrokerEventKind.FILLED, broker_id="B", seq="S")
    _, e2 = _norm(BrokerEventKind.FILLED, broker_id="B", seq="S")
    assert e1 is not None and e2 is not None
    assert e1.evidence_digest == e2.evidence_digest
    assert e1.evidence_digest == hashlib.sha256(e1.compute_canonical_payload_bytes()).hexdigest()


# ============================================================================
# Fail-closed on unknown kind
# ============================================================================

def test_unknown_kind_fails_closed() -> None:
    with pytest.raises(BrokerEventNormalizationError, match="BrokerEventKind"):
        normalize_broker_event(
            broker_order_id="B",
            event_kind="NOT_A_REAL_KIND",  # type: ignore[arg-type]
            observed_at=_now(),
            source="X",
            broker_sequence="S",
        )


def test_empty_broker_order_id_fails_closed() -> None:
    with pytest.raises(Exception):
        normalize_broker_event(
            broker_order_id="   ",
            event_kind=BrokerEventKind.ACK,
            observed_at=_now(),
            source="X",
            broker_sequence="S",
        )


# ============================================================================
# Authority split: normalizer never decides state; transition_order is the
# only state authority
# ============================================================================

def test_normalizer_returns_event_not_state() -> None:
    # The normalizer's output is a canonical EVENT, not an OrderLifecycleState.
    event, _ = _norm(BrokerEventKind.FILLED)
    assert isinstance(event, ExecutionEvent)
    assert not isinstance(event, OrderLifecycleState)


def test_full_pipeline_normalizer_then_transition_authority() -> None:
    # Lifecycle: ACKNOWLEDGED + FILL (from normalizer) -> FILLED
    event, _ = _norm(BrokerEventKind.FILLED)
    res = transition_order(OrderLifecycleState.ACKNOWLEDGED, event)
    assert res.new_state is OrderLifecycleState.FILLED
    assert res.is_terminal is True


def test_reconcile_bridge_evidence_string_to_transition() -> None:
    # Normalizer evidence can drive the Step 8B reconciliation gate.
    _, evidence = _norm(BrokerEventKind.FILLED, broker_id="B_RECON", seq="9")
    assert evidence is not None
    token = evidence.to_evidence_string()
    assert token == "FILLED"
    res = transition_order(
        OrderLifecycleState.UNKNOWN,
        ExecutionEvent.RECONCILE,
        evidence=token,
    )
    assert res.new_state is OrderLifecycleState.FILLED
    assert res.is_terminal is True


def test_evidence_string_rejects_non_terminal_status() -> None:
    ev = ReconciliationEvidence(
        broker_order_id="B",
        observed_status=BrokerEventKind.ACK,
        observed_at=_now(),
        source="X",
        broker_sequence="S",
        evidence_digest="0" * 64,
    )
    with pytest.raises(BrokerEventNormalizationError, match="not a reconciliation"):
        ev.to_evidence_string()
