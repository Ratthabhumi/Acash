"""Phase 7 Step 8C: Broker Event Normalization.

Implements the pure, deterministic mapping from broker-specific raw events to
canonical ``ExecutionEvent`` values plus typed ``ReconciliationEvidence``:

$$\boxed{ \text{Broker Raw Event} \rightarrow \text{Canonical Execution Event} }$$

Architecture contract (from Step 8B + Step 8C authority split):

```
Broker
  ↓ Raw Event
Normalizer          <- THIS module: maps to canonical event + evidence
  ↓ Canonical Event + Evidence
transition_order()  <- ONLY state authority (state_machine.py)
  ↓ New State
```

The normalizer:
- NEVER computes or returns an order state. It returns a canonical
  ``ExecutionEvent`` and (where available) a typed ``ReconciliationEvidence``.
  State transition remains exclusively the responsibility of
  ``transition_order()``.
- Is a pure, stateless function of its inputs (no I/O, no clock).
- Fails closed on any broker event it cannot normalize (unknown kind, ambiguous
  cancellation without a caller cancel hint, malformed evidence fields).

``ReconciliationEvidence`` is the typed, structured, self-authenticating
evidence model. It is the foundation for upgrading ``transition_order()``'s
free-form ``evidence`` string to structured, verifiable evidence (contract §2.3).
It stabilizes the broker_order_id / observed_status / observed_at / source /
broker_sequence lineage and carries a canonical ``evidence_digest`` (SHA-256).
"""

from datetime import datetime
from enum import Enum
import hashlib
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from acash.core.domain.exceptions import DomainValidationError
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.state_machine import ExecutionEvent, ExecutionStateError


class BrokerEventNormalizationError(DomainValidationError):
    """Raised when a broker raw event cannot be normalized (fail-closed)."""


class BrokerEventKind(str, Enum):
    """Canonical vocabulary of broker-reported raw event kinds.

    These are the normalized names a broker adapter SHALL map its vendor-specific
    payloads onto BEFORE calling the normalizer. This keeps the normalizer
    broker-agnostic and deterministic.
    """

    ACK = "ACK"
    REJECT = "REJECT"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCEL_REJECTED = "CANCEL_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    EXPIRED = "EXPIRED"
    CONNECTION_LOST = "CONNECTION_LOST"


# BrokerEventKind -> canonical ExecutionEvent for the deterministic (non-cancel)
# subset. ORDER_CANCELLED is intentionally excluded: it is ambiguous and is
# resolved only via the caller cancel hint (see normalize_broker_event).
_DIRECT_EVENT_MAP: dict[BrokerEventKind, ExecutionEvent] = {
    BrokerEventKind.ACK: ExecutionEvent.ACK,
    BrokerEventKind.REJECT: ExecutionEvent.REJECT,
    BrokerEventKind.PARTIAL_FILL: ExecutionEvent.PARTIAL_FILL,
    BrokerEventKind.FILLED: ExecutionEvent.FILL,
    BrokerEventKind.CANCEL_REJECTED: ExecutionEvent.CANCEL_REJECT,
    BrokerEventKind.EXPIRED: ExecutionEvent.EXPIRY,
    BrokerEventKind.CONNECTION_LOST: ExecutionEvent.CONNECTION_LOST,
}


class ReconciliationEvidence(BaseModel):
    """Typed, self-authenticating broker evidence for a normalized event.

    Field lineage (structured > free-form string, contract §2.3):
        broker_order_id: authoritative broker-side order identifier.
        observed_status: status the broker reported (canonical BrokerEventKind).
        observed_at: UTC timestamp at which the broker reported the status.
        source: originating venue/adapter name (e.g. 'binance_futures').
        broker_sequence: broker-provided sequence / execution report id.
        evidence_digest: SHA-256 over the canonical serialization of the above
            fields, binding the evidence to its content (tamper-evident).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker_order_id: str = Field(description="Authoritative broker order identifier.")
    observed_status: BrokerEventKind = Field(description="Broker-reported status.")
    observed_at: datetime = Field(description="UTC timestamp of the broker report.")
    source: str = Field(description="Originating venue/adapter name.")
    broker_sequence: str = Field(description="Broker sequence / execution report id.")
    evidence_refs: Tuple[str, ...] = Field(default_factory=tuple, description="Canonical references to underlying execution deals or events.")

    evidence_digest: str = Field(description="SHA-256 of canonical evidence payload.")

    @field_validator("broker_order_id", "source", "broker_sequence")
    @classmethod
    def validate_non_empty(cls, v: str, info: "object") -> str:
        field_name = getattr(info, "field_name", "field") or "field"
        if not v or not v.strip():
            raise BrokerEventNormalizationError(
                f"{field_name} must be a non-empty string."
            )
        return v.strip()

    def compute_canonical_payload_bytes(self) -> bytes:
        """Canonical serialization of the evidence content (digest inputs)."""
        return _evidence_payload_bytes(
            broker_order_id=self.broker_order_id,
            observed_status=self.observed_status,
            observed_at=self.observed_at,
            source=self.source,
            broker_sequence=self.broker_sequence,
            evidence_refs=self.evidence_refs,
        )

    def verify_digest(self) -> None:
        """Re-compute and assert the evidence_digest matches the content.

        Raises BrokerEventNormalizationError on tamper/mismatch (fail-closed).
        """
        expected = hashlib.sha256(self.compute_canonical_payload_bytes()).hexdigest()
        if self.evidence_digest != expected:
            raise BrokerEventNormalizationError(
                f"ReconciliationEvidence digest mismatch for broker_order_id "
                f"'{self.broker_order_id}'. Tamper-evident integrity check failed."
            )

    def to_evidence_string(self) -> str:
        """Encode this evidence as the verified-outcome token for `transition_order()`.

        Bridges the structured evidence model to the current Step 8B free-form
        ``evidence`` interface (e.g. 'FILLED'). This is an explicit, documented
        bridge and does NOT weaken the structured source of truth.
        """
        token = self.observed_status.value
        if token in ("FILLED", "ORDER_CANCELLED", "REJECT", "REJECTED", "EXPIRED"):
            # Map broker kind back to a reconciliation-verifiable terminal token.
            mapping = {
                "FILLED": "FILLED",
                "ORDER_CANCELLED": "CANCELLED",
                "REJECT": "REJECTED",
                "REJECTED": "REJECTED",
                "EXPIRED": "EXPIRED",
            }
            return mapping[token]
        raise BrokerEventNormalizationError(
            f"observed_status '{token}' is not a reconciliation-verifiable "
            "terminal outcome; cannot build an evidence string."
        )


def normalize_broker_event(
    *,
    broker_order_id: str,
    event_kind: BrokerEventKind,
    observed_at: datetime,
    source: str,
    broker_sequence: str,
    cancel_was_requested: bool = False,
    evidence_refs: Tuple[str, ...] = (),
) -> Tuple[ExecutionEvent, Optional[ReconciliationEvidence]]:
    """Normalize a broker raw event into (canonical ExecutionEvent, evidence).

    Pure and stateless. Does NOT compute or return the new order state — that is
    exclusively ``transition_order()``'s responsibility.

    Args:
        broker_order_id: authoritative broker order identifier.
        event_kind: canonical broker-reported event kind.
        observed_at: UTC timestamp of the broker report.
        source: originating venue/adapter name.
        broker_sequence: broker sequence / execution report id.
        cancel_was_requested: caller hint (from the broker client, NOT derived
            from internal order state) stating whether a cancel request is in
            flight. REQUIRED to disambiguate an ``ORDER_CANCELLED`` report into
            ``CANCEL_ACK``.

    Returns:
        ``(canonical ExecutionEvent, ReconciliationEvidence | None)``.
        Evidence is produced for statuses that are reconciliation-verifiable
        terminal outcomes (fill/cancel/reject/expiry).

    Raises:
        BrokerEventNormalizationError: fail-closed on unknown kind, ambiguous
        cancellation without the caller hint, or malformed inputs.
    """
    # Fail-closed input validation: these are always required, independent of
    # whether a terminal evidence object is produced.
    for label, val in (
        ("broker_order_id", broker_order_id),
        ("source", source),
        ("broker_sequence", broker_sequence),
    ):
        if not isinstance(val, str) or not val.strip():
            raise BrokerEventNormalizationError(
                f"{label} must be a non-empty string; got {val!r}."
            )
    if not isinstance(event_kind, BrokerEventKind):
        raise BrokerEventNormalizationError(
            f"event_kind must be a BrokerEventKind; got {event_kind!r}. "
            "Fail-closed: cannot normalize."
        )

    # Ambiguous cancellation: only resolved through the caller hint, never by
    # guessing an order state.
    canonical_event: ExecutionEvent
    if event_kind is BrokerEventKind.ORDER_CANCELLED:
        if not cancel_was_requested:
            raise BrokerEventNormalizationError(
                "Broker reported ORDER_CANCELLED but no cancel was requested "
                "(cancel_was_requested=False). This is an unexpected/ambiguous "
                "cancellation and MUST be routed to reconciliation — the "
                "normalizer does not guess an order state. Fail-closed."
            )
        canonical_event = ExecutionEvent.CANCEL_ACK
    else:
        direct_event = _DIRECT_EVENT_MAP.get(event_kind)
        if direct_event is None:
            raise BrokerEventNormalizationError(
                f"Unknown/unsupported broker event kind '{event_kind.value}'. "
                "Fail-closed: cannot normalize."
            )
        canonical_event = direct_event

    evidence = _build_evidence(
        broker_order_id=broker_order_id,
        event_kind=event_kind,
        observed_at=observed_at,
        source=source,
        broker_sequence=broker_sequence,
        evidence_refs=evidence_refs,
    )

    return canonical_event, evidence


def _canonical_evidence_payload(
    *,
    broker_order_id: str,
    observed_status: BrokerEventKind,
    observed_at: datetime,
    source: str,
    broker_sequence: str,
    evidence_refs: Tuple[str, ...] = (),
) -> Dict[str, Any]:
    """Canonical dict of evidence content (shared, deterministic)."""
    return {
        "broker_order_id": broker_order_id,
        "observed_status": observed_status.value,
        "observed_at": observed_at.isoformat(),
        "source": source,
        "broker_sequence": broker_sequence,
        "evidence_refs": list(evidence_refs),
    }


def _evidence_payload_bytes(
    *,
    broker_order_id: str,
    observed_status: BrokerEventKind,
    observed_at: datetime,
    source: str,
    broker_sequence: str,
    evidence_refs: Tuple[str, ...] = (),
) -> bytes:
    payload = _canonical_evidence_payload(
        broker_order_id=broker_order_id,
        observed_status=observed_status,
        observed_at=observed_at,
        source=source,
        broker_sequence=broker_sequence,
        evidence_refs=evidence_refs,
    )
    return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")


def _build_evidence(
    *,
    broker_order_id: str,
    event_kind: BrokerEventKind,
    observed_at: datetime,
    source: str,
    broker_sequence: str,
    evidence_refs: Tuple[str, ...] = (),
) -> Optional[ReconciliationEvidence]:
    """Build typed ReconciliationEvidence for reconciliation-verifiable outcomes.

    Returns None for events that are not themselves terminal reconciliation
    outcomes (ACK, PARTIAL_FILL, CANCEL_REJECTED, CONNECTION_LOST).
    """
    verifiable = {
        BrokerEventKind.FILLED,
        BrokerEventKind.REJECT,
        BrokerEventKind.ORDER_CANCELLED,
        BrokerEventKind.EXPIRED,
    }
    if event_kind not in verifiable:
        return None

    content_digest = hashlib.sha256(
        _evidence_payload_bytes(
            broker_order_id=broker_order_id,
            observed_status=event_kind,
            observed_at=observed_at,
            source=source,
            broker_sequence=broker_sequence,
            evidence_refs=evidence_refs,
        )
    ).hexdigest()

    return ReconciliationEvidence(
        broker_order_id=broker_order_id,
        observed_status=event_kind,
        observed_at=observed_at,
        source=source,
        broker_sequence=broker_sequence,
        evidence_refs=evidence_refs,
        evidence_digest=content_digest,
    )
