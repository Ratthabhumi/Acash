"""Phase 13 Slice 2: Gate B Mandatory Human Authorization Schemas & DTOs (Rev 20).

Establishes formal, immutable Pydantic schemas, cryptographic verification DTOs,
storage records, and quote contracts per docs/phase13/slice2_gate_b_plan.md.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import hashlib
from typing import Any, Dict, Optional, Protocol, Tuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import Ed25519TrustStore
from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    DataContractError,
    PreLiveRiskAdmissionError,
)


class LiveAuthorizationStatus(str, Enum):
    """Lifecycle status of a Gate B strategy authorization token."""

    DRAFT = "DRAFT"
    APPROVED_PENDING_GO = "APPROVED_PENDING_GO"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class DurableTransactionState(str, Enum):
    """Persisted on-disk transactional lifecycle states (B95)."""

    PREPARED = "PREPARED"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"
    QUARANTINED = "QUARANTINED"


class SystemSafetyMode(str, Enum):
    """System-wide operational safety mode (B95)."""

    NORMAL = "NORMAL"
    SUSPENDED = "SUSPENDED"
    QUARANTINE_LOCKED = "QUARANTINE_LOCKED"


class JournalState(str, Enum):
    """Operational WAL journal states (reconstructible metadata)."""

    PREPARED = "PREPARED"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"
    QUARANTINED = "QUARANTINED"


class LiveAuthorization(BaseModel):
    """Authoritative runtime strategy authorization artifact (B97).

    ACTIVE is reachable only through the authoritative activation transaction path.
    Under Rev 20, ACTIVE is impossible to reach without an atomic CAS commit binding
    the verified LiveAuthorization, the Ed25519-signed HumanGORecord, and the unbroken
    authoritative ledger head.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    authorization_id: str = Field(description="Deterministic strategy authorization ID.")
    status: LiveAuthorizationStatus = Field(default=LiveAuthorizationStatus.DRAFT)
    approved_authorization_digest: str = Field(
        description="Canonical SHA-256 of draft artifact when approved by machine quorum."
    )
    source_approved_digest: Optional[str] = Field(
        default=None,
        description="Cryptographic derivation link to human-approved draft digest (B79).",
    )
    activated_authorization_digest: Optional[str] = Field(
        default=None,
        description="SHA-256 of active artifact post-activation (B73, B77).",
    )
    active_go_record_digest: Optional[str] = Field(
        default=None,
        description="Bound HumanGORecord digest once active.",
    )
    activation_transaction_id: Optional[UUID] = Field(
        default=None,
        description="Storage transaction ID under which activation committed.",
    )
    activated_at: Optional[datetime] = Field(
        default=None,
        description="Strict UTC timestamp of activation (B97).",
    )
    strategy_id: str = Field(description="Bound strategy identity.")
    symbol: str = Field(description="Trading symbol.")
    account_id: str = Field(description="Target live broker account ID.")
    max_notional_usd: Decimal = Field(gt=Decimal("0"))
    max_drawdown_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("100"))
    max_slippage_points: int = Field(gt=0, description="Mandatory positive slippage allowance points.")
    max_quote_age_ms: int = Field(gt=0, description="Mandatory positive quote age SLA.")
    required_approvals: int = Field(gt=0)
    created_at: datetime = Field(description="UTC timestamp.")
    expires_at: datetime = Field(description="Mandatory UTC expiry.")

    @property
    def authorization_digest(self) -> str:
        """Alias for approved_authorization_digest preserving backward compatibility."""
        return self.approved_authorization_digest

    @field_validator("created_at", "expires_at", "activated_at")
    @classmethod
    def validate_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return None
        if v.tzinfo is None or v.utcoffset() != timedelta(0):
            raise DataContractError(f"Timestamp {v} must be UTC-aware with zero offset")
        return v

    def compute_approved_canonical_bytes(self) -> bytes:
        """Derive canonical bytes for approved draft state."""
        payload = {
            "authorization_id": self.authorization_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "account_id": self.account_id,
            "max_notional_usd": str(self.max_notional_usd),
            "max_drawdown_pct": str(self.max_drawdown_pct),
            "max_slippage_points": self.max_slippage_points,
            "max_quote_age_ms": self.max_quote_age_ms,
            "required_approvals": self.required_approvals,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")

    def compute_activated_canonical_bytes(self) -> bytes:
        """Derive canonical bytes for activated authorization state including activated_at (B97)."""
        if (
            self.activated_at is None
            or self.activation_transaction_id is None
            or self.active_go_record_digest is None
        ):
            raise DataContractError("INCOMPLETE_ACTIVATION_METADATA_FOR_DIGEST")
        payload = {
            "authorization_id": self.authorization_id,
            "status": self.status.value,
            "source_approved_digest": self.source_approved_digest,
            "active_go_record_digest": self.active_go_record_digest,
            "activation_transaction_id": str(self.activation_transaction_id),
            "activated_at": self.activated_at.isoformat(),
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "account_id": self.account_id,
            "max_notional_usd": str(self.max_notional_usd),
            "max_drawdown_pct": str(self.max_drawdown_pct),
            "max_slippage_points": self.max_slippage_points,
            "max_quote_age_ms": self.max_quote_age_ms,
            "required_approvals": self.required_approvals,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")


class HumanGORecord(BaseModel):
    """Cryptographically signed, non-repudiable human authorization record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    go_record_id: str = Field(description="Unique deterministic GO record identifier.")
    authorization_id: str = Field(description="LiveAuthorization ID being granted GO authority.")
    approved_authorization_digest: str = Field(
        description="SHA-256 of the exact LiveAuthorization artifact approved by human."
    )
    previous_record_digest: str = Field(
        description="Cryptographic link to previous authoritative ledger head."
    )
    record_timestamp_utc: datetime = Field(description="Strict UTC timestamp of human signature.")
    approver_public_key_id: str = Field(description="Ed25519 public key ID in trust store.")
    signature_ed25519: str = Field(description="Base64-encoded Ed25519 digital signature.")
    record_digest: str = Field(description="Authoritative SHA-256 digest of this complete record.")

    @field_validator("record_timestamp_utc")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() != timedelta(0):
            raise DataContractError(f"Timestamp {v} must be UTC-aware with zero offset")
        return v

    def compute_signed_payload_bytes(self) -> bytes:
        """Payload over which approver signature is computed."""
        payload = {
            "go_record_id": self.go_record_id,
            "authorization_id": self.authorization_id,
            "approved_authorization_digest": self.approved_authorization_digest,
            "previous_record_digest": self.previous_record_digest,
            "record_timestamp_utc": self.record_timestamp_utc.isoformat(),
            "approver_public_key_id": self.approver_public_key_id,
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")

    def compute_canonical_digest(self) -> str:
        """SHA-256 over complete record payload including signature."""
        payload = {
            "go_record_id": self.go_record_id,
            "authorization_id": self.authorization_id,
            "approved_authorization_digest": self.approved_authorization_digest,
            "previous_record_digest": self.previous_record_digest,
            "record_timestamp_utc": self.record_timestamp_utc.isoformat(),
            "approver_public_key_id": self.approver_public_key_id,
            "signature_ed25519": self.signature_ed25519,
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def verify_signature(self, trust_store: Ed25519TrustStore) -> None:
        """Verify Ed25519 signature against trust store."""
        payload_bytes = self.compute_signed_payload_bytes()
        try:
            trust_store.verify(
                key_id=self.approver_public_key_id,
                payload_bytes=payload_bytes,
                signature_b64=self.signature_ed25519,
                at_time=self.record_timestamp_utc,
            )
        except Exception as exc:
            raise CryptographicVerificationError(
                f"HUMAN_GO_SIGNATURE_VERIFICATION_FAILED: Key '{self.approver_public_key_id}': {exc}"
            ) from exc


class DurablePointerTransitionRecord(BaseModel):
    """Cryptographically authenticated durable record of pointer state transition (B88, B93)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pointer_version: int = Field(description="Monotonically increasing pointer version.")
    previous_tx_id: Optional[UUID] = Field(
        description="Previous active transaction ID (None for genesis)."
    )
    new_tx_id: UUID = Field(description="New transaction ID being published.")
    transition_timestamp_utc: datetime = Field(description="Strict UTC timestamp of transition.")
    commit_intent_digest: str = Field(
        description="SHA-256 of AuthoritativeCommitRecordBlock being published."
    )
    previous_pointer_digest: str = Field(
        description="SHA-256 of previous pointer state file for hash-chain continuity."
    )
    transition_record_digest: str = Field(
        description="Canonical SHA-256 digest over above fields (B93)."
    )
    engine_signature: str = Field(
        description="Ed25519 digital signature by storage engine trust anchor (B93)."
    )
    engine_key_id: str = Field(
        description="Storage engine signer key ID in trust store (B93)."
    )

    @field_validator("transition_timestamp_utc")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() != timedelta(0):
            raise DataContractError(f"Timestamp {v} must be UTC-aware with zero offset")
        return v

    def compute_canonical_digest(self) -> str:
        """Compute canonical digest over transition payload."""
        payload = {
            "pointer_version": self.pointer_version,
            "previous_tx_id": str(self.previous_tx_id) if self.previous_tx_id else None,
            "new_tx_id": str(self.new_tx_id),
            "transition_timestamp_utc": self.transition_timestamp_utc.isoformat(),
            "commit_intent_digest": self.commit_intent_digest,
            "previous_pointer_digest": self.previous_pointer_digest,
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def is_valid_transition(
        self,
        expected_tx_id: UUID,
        expected_prev_tx_id: Optional[UUID],
        expected_manifest_digest: str,
        trust_store: Ed25519TrustStore,
    ) -> bool:
        """Assert Invariant VALID_TRANSITION(tx) (B93)."""
        calculated_digest = self.compute_canonical_digest()
        if calculated_digest != self.transition_record_digest:
            return False

        if self.new_tx_id != expected_tx_id:
            return False

        if self.previous_tx_id != expected_prev_tx_id:
            return False

        if self.commit_intent_digest != expected_manifest_digest:
            return False

        try:
            trust_store.verify(
                key_id=self.engine_key_id,
                payload_bytes=self.transition_record_digest.encode("utf-8"),
                signature_b64=self.engine_signature,
                at_time=self.transition_timestamp_utc,
            )
            return True
        except Exception:
            return False


class AuthoritativeAbortRecordBlock(BaseModel):
    """Persistent, immutable cryptographic evidence block written upon rollback."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    activation_transaction_id: UUID = Field(description="Storage transaction ID being terminated.")
    pre_transaction_head_digest: str = Field(
        description="Durable ledger head digest prior to transaction start."
    )
    authorization_id: str = Field(description="LiveAuthorization ID being aborted.")
    approved_authorization_digest: str = Field(
        description="Human-approved draft digest bound to this abort."
    )
    expected_previous_state: DurableTransactionState = Field(
        description="State from which abort was initiated."
    )
    terminal_state: DurableTransactionState = Field(default=DurableTransactionState.ABORTED)
    abort_reason_code: str = Field(description="Canonical error or failure reason code.")
    abort_timestamp_utc: datetime = Field(description="Strict UTC timestamp of abort completion.")
    abort_record_digest: str = Field(description="Canonical SHA-256 of this abort block.")

    @field_validator("abort_timestamp_utc")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() != timedelta(0):
            raise DataContractError(f"Timestamp {v} must be UTC-aware with zero offset")
        return v

    def compute_digest(self) -> str:
        """SHA-256 over canonical JSON of abort block fields."""
        payload = {
            "activation_transaction_id": str(self.activation_transaction_id),
            "pre_transaction_head_digest": self.pre_transaction_head_digest,
            "authorization_id": self.authorization_id,
            "approved_authorization_digest": self.approved_authorization_digest,
            "expected_previous_state": self.expected_previous_state.value,
            "terminal_state": self.terminal_state.value,
            "abort_reason_code": self.abort_reason_code,
            "abort_timestamp_utc": self.abort_timestamp_utc.isoformat(),
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def is_valid(self) -> bool:
        """Assert integrity and terminal aborted state."""
        if self.terminal_state != DurableTransactionState.ABORTED:
            return False
        return self.compute_digest() == self.abort_record_digest


class AuthoritativeCommitRecordBlock(BaseModel):
    """Disambiguated manifest capturing all entity hashes and commit proof (B77, B79)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    activation_transaction_id: UUID = Field(
        description="Storage transaction ID under which mutation occurred."
    )
    commit_timestamp_utc: datetime = Field(description="Strict UTC timestamp of commit.")
    ledger_record_digest: str = Field(description="SHA-256 of appended HumanGORecord.")
    advanced_head_digest: str = Field(description="SHA-256 of advanced ledger head.")
    approved_authorization_digest: str = Field(
        description="Canonical digest of approved draft authorization."
    )
    activated_authorization_digest: str = Field(
        description="Canonical digest of active authorization artifact."
    )
    mutation_manifest_digest: str = Field(
        description="Authoritative SHA-256 over all entity hashes in commit."
    )

    @field_validator("commit_timestamp_utc")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() != timedelta(0):
            raise DataContractError(f"Timestamp {v} must be UTC-aware with zero offset")
        return v

    def compute_manifest_digest(self) -> str:
        """SHA-256 over canonical JSON of manifest fields."""
        payload = {
            "activation_transaction_id": str(self.activation_transaction_id),
            "commit_timestamp_utc": self.commit_timestamp_utc.isoformat(),
            "ledger_record_digest": self.ledger_record_digest,
            "advanced_head_digest": self.advanced_head_digest,
            "approved_authorization_digest": self.approved_authorization_digest,
            "activated_authorization_digest": self.activated_authorization_digest,
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def verify_manifest_integrity(self) -> bool:
        """Assert internal manifest consistency."""
        return self.compute_manifest_digest() == self.mutation_manifest_digest


class MT5QuoteSnapshot(BaseModel):
    """Authoritative market price observation bound to transaction window."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(description="Normalized symbol (e.g. EURUSD).")
    bid: Decimal = Field(gt=Decimal("0"), description="Live broker bid price.")
    ask: Decimal = Field(gt=Decimal("0"), description="Live broker ask price.")
    point_size: Decimal = Field(gt=Decimal("0"), description="Symbol tick/point dimension.")
    contract_size: Decimal = Field(gt=Decimal("0"), description="Units per standard lot.")
    timestamp_utc: datetime = Field(description="Strict UTC timestamp of quote observation.")

    @field_validator("timestamp_utc")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() != timedelta(0):
            raise DataContractError(f"Timestamp {v} must be UTC-aware with zero offset")
        return v

    def assert_valid_and_fresh(self, *, max_quote_age_ms: int) -> None:
        """Validate spread non-inversion, non-negative age, and freshness SLA."""
        if max_quote_age_ms is None or max_quote_age_ms <= 0:
            raise PreLiveRiskAdmissionError(
                "MANDATORY_PARAMETER_MISSING: max_quote_age_ms must be positive int"
            )

        now_utc = datetime.now(timezone.utc)
        age_ms = (now_utc - self.timestamp_utc).total_seconds() * 1000.0
        if age_ms < 0:
            raise PreLiveRiskAdmissionError(
                f"FUTURE_TIMESTAMP_ANOMALY: Quote timestamp {self.timestamp_utc} is in the future "
                f"relative to local clock {now_utc} (age: {age_ms:.1f}ms)"
            )
        if age_ms > max_quote_age_ms:
            raise PreLiveRiskAdmissionError(
                f"STALE_QUOTE: Quote age {age_ms:.1f}ms exceeds maximum allowed {max_quote_age_ms}ms"
            )

        if self.ask < self.bid:
            raise PreLiveRiskAdmissionError(
                f"INVALID_QUOTE: Inverted market spread bid={self.bid} > ask={self.ask}"
            )


class AuthoritativeLedgerProtocol(Protocol):
    """Protocol defining the interface of an authoritative ledger for GO records."""

    @property
    def current_head_digest(self) -> str: ...


def verify_human_go_record_integrity(
    record: HumanGORecord,
    trust_store: Ed25519TrustStore,
    ledger: AuthoritativeLedgerProtocol,
) -> None:
    """Non-repudiable cryptographic integrity assertion for HumanGORecord."""
    # 1. Self-digest integrity
    calculated_digest = record.compute_canonical_digest()
    if calculated_digest != record.record_digest:
        raise CryptographicVerificationError(
            f"GO_RECORD_DIGEST_CORRUPTED: Calculated {calculated_digest} != Recorded {record.record_digest}"
        )

    # 2. Cryptographic signature check
    record.verify_signature(trust_store)

    # 3. Head continuity check
    if record.previous_record_digest != ledger.current_head_digest:
        raise CryptographicVerificationError(
            f"GO_LEDGER_CONTINUITY_BROKEN: Record points to {record.previous_record_digest}, "
            f"but authoritative ledger head is {ledger.current_head_digest}"
        )


def assert_activation_preconditions(
    auth: LiveAuthorization,
    go_record: HumanGORecord,
    trust_store: Ed25519TrustStore,
) -> None:
    """Validate activation preconditions prior to entering atomic CAS commit."""
    # 1. Verify approval status
    if auth.status != LiveAuthorizationStatus.APPROVED_PENDING_GO:
        raise PreLiveRiskAdmissionError(
            f"INVALID_AUTHORIZATION_STATUS: Expected APPROVED_PENDING_GO, got {auth.status}"
        )

    # 2. Verify timestamp expiration
    now_utc = datetime.now(timezone.utc)
    if auth.expires_at <= now_utc:
        raise PreLiveRiskAdmissionError(
            f"AUTHORIZATION_EXPIRED: Expiry {auth.expires_at} <= current time {now_utc}"
        )

    # 3. Verify approver key validity at signing time
    entry = trust_store.resolve(go_record.approver_public_key_id, at_time=go_record.record_timestamp_utc)
    if entry is None:
        raise CryptographicVerificationError("APPROVER_KEY_NOT_RESOLVED")


def calculate_worst_case_notional(
    quantity: Decimal,
    quote: MT5QuoteSnapshot,
    slippage_points: int,
) -> Decimal:
    """Calculate worst-case executable notional exposure including slippage."""
    slippage_distance = Decimal(str(slippage_points)) * quote.point_size
    worst_case_price = quote.ask + slippage_distance
    return quantity * quote.contract_size * worst_case_price
