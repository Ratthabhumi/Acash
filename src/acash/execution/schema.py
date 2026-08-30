"""Phase 7: Live Execution, Pre-Live Risk Admission & Operational Governance Schemas.

Establishes strict data contracts, state machines, and cryptographic lineage for:
1. ValidationCertificate & CertificateRevocationEvent (Read-only Phase 6 Ingestion)
2. AuthorizationApproval & LiveAuthorization (Multi-sig Capital Allocation Token)
3. AuthorizationReactivationApproval & AuthorizationReactivationEvent (Quorum Recovery)
4. OrderIntent & OrderLifecycleState (First-Class Pre-Submission Binding)
5. ExecutionManifest (Immutable Execution Audit Trail)
6. RiskState & CalculationStatus (Dynamic Real-Time Risk & Staleness Halt)
7. KillSwitchEvent & KillSwitchTriggerType (First-Class Safety Action Engine)
8. ReconciliationReport (6-Dimensional Shadow vs. Broker Parity Check)

Contract Invariants:
- ACTIVE LiveAuthorization MUST only be emitted by the issuance/transition service.
  Schema accepts any status for serialization; the service layer is the sole authority.
- Reactivation quorum MUST equal issuance quorum (required_approvals is invariant).
- authorization_digest covers canonical params + sorted approval_digests.
- approval_signature is Ed25519 over canonical payload bound to authorization_id.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
import hashlib
import re
from typing import Any, Dict, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from acash.core.domain.exceptions import DomainValidationError
from acash.core.domain.types import ensure_finite_decimal
from acash.core.serialization import CanonicalConfigSerializer
from acash.validation.schema import ValidationGateVerdict


SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _validate_sha256(v: str, field_name: str) -> str:
    if not isinstance(v, str) or not SHA256_HEX_PATTERN.match(v):
        raise DomainValidationError(
            f"{field_name} must be a valid 64-character lowercase hex SHA-256 string, got: {v!r}"
        )
    return v


# ============================================================================
# 1. VALIDATION CERTIFICATE & REVOCATION EVENT
# ============================================================================

class ValidationCertificate(BaseModel):
    """Immutable certificate ingested from Phase 6 Statistical Validation Gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    certificate_id: str = Field(description="Unique deterministic certificate identifier.")
    validation_id: str = Field(description="Phase 6 validation report identifier.")
    strategy_id: str = Field(description="Target strategy identifier.")
    hypothesis_id: str = Field(description="Registered hypothesis specification identifier.")
    verdict: ValidationGateVerdict = Field(description="Must be PASS_TRADEABLE_ALPHA.")

    # Cryptographic Lineage Digests
    decision_digest: str = Field(description="Phase 6 decision digest.")
    evidence_digest: str = Field(description="Phase 6 evidence digest.")
    source_report_hash: str = Field(description="SHA-256 hash of the complete Phase 6 JSON report.")

    # Issuer Trust Root & Digital Signature
    issuer_id: str = Field(description="Authorized issuing authority identifier.")
    issuer_public_key_id: str = Field(description="Key ID of the issuing authority (must be in TrustStore).")
    signature_algorithm: Literal["Ed25519"] = Field(
        default="Ed25519",
        description="Cryptographic signature algorithm. Ed25519 uses SHA-512 internally (RFC 8032).",
    )
    certificate_signature: str = Field(
        description="Base64-encoded Ed25519 signature over canonical certificate payload."
    )

    methodology_version: str = Field(description="Phase 6 governance methodology version.")
    created_at: datetime = Field(description="UTC timestamp when certificate was issued.")
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration timestamp. None = no expiry. Mandatory expiry is enforced at LiveAuthorization.",
    )

    @field_validator(
        "certificate_id", "validation_id", "strategy_id", "hypothesis_id",
        "issuer_id", "issuer_public_key_id", "certificate_signature", "methodology_version",
    )
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("decision_digest", "evidence_digest", "source_report_hash")
    @classmethod
    def validate_digests(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "digest")

    @field_validator("verdict")
    @classmethod
    def validate_verdict_pass(cls, v: ValidationGateVerdict) -> ValidationGateVerdict:
        if v != ValidationGateVerdict.PASS_TRADEABLE_ALPHA:
            raise DomainValidationError(
                f"ValidationCertificate requires verdict PASS_TRADEABLE_ALPHA, got: {v}"
            )
        return v

    def compute_canonical_payload_bytes(self) -> bytes:
        """Derive canonical bytes for Ed25519 signature verification."""
        payload = {
            "certificate_id": self.certificate_id,
            "validation_id": self.validation_id,
            "strategy_id": self.strategy_id,
            "hypothesis_id": self.hypothesis_id,
            "verdict": self.verdict.value,
            "decision_digest": self.decision_digest,
            "evidence_digest": self.evidence_digest,
            "source_report_hash": self.source_report_hash,
            "issuer_id": self.issuer_id,
            "issuer_public_key_id": self.issuer_public_key_id,
            "signature_algorithm": self.signature_algorithm,
            "methodology_version": self.methodology_version,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")


class CertificateRevocationEvent(BaseModel):
    """Immutable forensic event declaring a ValidationCertificate revoked."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revocation_id: str = Field(description="Unique deterministic revocation event ID.")
    certificate_id: str = Field(description="Target ValidationCertificate ID being revoked.")
    strategy_id: str = Field(
        description="Target strategy identifier. Must match certificate.strategy_id."
    )
    revoked_at: datetime = Field(description="UTC timestamp of revocation.")

    reason: str = Field(description="Forensic reason for revocation.")
    actor: str = Field(description="Entity issuing revocation.")
    actor_public_key_id: str = Field(
        description="Public key ID of the revoking authority (must be in TrustStore)."
    )
    revocation_signature: str = Field(
        description="Base64-encoded Ed25519 signature over canonical revocation payload."
    )
    revocation_digest: str = Field(description="SHA-256 hash of canonical revocation record.")

    @field_validator(
        "revocation_id", "certificate_id", "strategy_id", "reason",
        "actor", "actor_public_key_id", "revocation_signature",
    )
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("revocation_digest")
    @classmethod
    def validate_digests(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "digest")

    def compute_canonical_payload_bytes(self) -> bytes:
        """Derive canonical bytes for Ed25519 signature verification."""
        payload = {
            "revocation_id": self.revocation_id,
            "certificate_id": self.certificate_id,
            "strategy_id": self.strategy_id,
            "revoked_at": self.revoked_at.isoformat(),
            "reason": self.reason,
            "actor": self.actor,
            "actor_public_key_id": self.actor_public_key_id,
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")


# ============================================================================
# 2. LIVE AUTHORIZATION — MULTI-SIG APPROVAL & LIFECYCLE STATE MACHINE
# ============================================================================

class AuthorizationStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ApproverRole(str, Enum):
    """Role of the approving authority in the authorization quorum."""

    RISK_OFFICER = "RISK_OFFICER"
    PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"


class AuthorizationApproval(BaseModel):
    """Signed approval record explicitly bound to a single LiveAuthorization.

    The approval_signature is an Ed25519 signature over compute_canonical_payload_bytes().
    Binding to authorization_id prevents replay across different authorizations.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    approver_id: str = Field(description="Authorized approver identifier.")
    public_key_id: str = Field(description="Key ID in TrustStore used to sign this approval.")
    role: ApproverRole = Field(description="Approver's role in the quorum.")
    authorization_id: str = Field(
        description="LiveAuthorization ID this approval is bound to (replay protection)."
    )
    approved_at: datetime = Field(description="UTC timestamp of approval.")
    approval_signature: str = Field(
        description="Base64-encoded Ed25519 signature over canonical approval payload."
    )
    approval_digest: str = Field(
        description="SHA-256 of canonical approval payload (fast content addressing)."
    )

    @field_validator("approver_id", "public_key_id", "authorization_id", "approval_signature")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("approval_digest")
    @classmethod
    def validate_digest(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "approval_digest")

    def compute_canonical_payload_bytes(self) -> bytes:
        """Canonical bytes for Ed25519 signing/verification."""
        payload = {
            "authorization_id": self.authorization_id,
            "approver_id": self.approver_id,
            "public_key_id": self.public_key_id,
            "role": self.role.value,
            "approved_at": self.approved_at.isoformat(),
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")


class LiveAuthorization(BaseModel):
    """Authoritative token granting capital allocation and operational boundaries.

    INVARIANT: ACTIVE status MUST only be emitted by the issuance/transition service.
    The schema permits any status for deserialization; application code MUST NOT
    construct ACTIVE LiveAuthorization objects directly.

    Multi-sig contract:
        |verified approvals| >= required_approvals  →  ACTIVE
        The authorization_digest covers canonical params + sorted approval_digests,
        creating an unbreakable link between the issued parameters and the approval set.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    authorization_id: str = Field(description="Unique deterministic authorization identifier.")
    certificate_id: str = Field(description="Linked ValidationCertificate identifier.")
    strategy_id: str = Field(description="Target strategy identifier.")
    status: AuthorizationStatus = Field(
        default=AuthorizationStatus.DRAFT, description="Current lifecycle state."
    )

    authorized_at: datetime = Field(description="UTC timestamp when authorization was granted.")
    expires_at: datetime = Field(description="Mandatory expiration timestamp.")

    # Operational Capital & Sizing Limits
    max_notional: Decimal = Field(description="Maximum total notional exposure.")
    max_position_size: Decimal = Field(description="Maximum units for any single position.")
    max_order_rate_per_minute: int = Field(gt=0, description="Throttle: max order submissions per minute.")

    # Loss & Drawdown Halts
    max_daily_loss_notional: Decimal = Field(description="Max cumulative daily loss before automatic halt.")
    max_drawdown_pct: Decimal = Field(description="Max peak-to-trough drawdown percentage before halt.")

    # Environmental Access
    allowed_venues: Tuple[str, ...] = Field(min_length=1, description="Whitelisted broker/exchange venues.")
    allowed_symbols: Tuple[str, ...] = Field(min_length=1, description="Whitelisted tradeable symbols.")
    risk_policy_version: str = Field(description="Active pre-live risk policy version.")

    # Multi-Sig Approval Quorum
    required_approvals: int = Field(ge=1, description="Minimum valid approvals required for ACTIVE state.")
    approvals: Tuple[AuthorizationApproval, ...] = Field(
        default=(), description="Signed approval records collected so far."
    )

    # Canonical Integrity Digest
    authorization_digest: str = Field(
        description=(
            "SHA-256 of canonical authorization params + required_approvals + "
            "sorted approval_digests. Recomputed on ACTIVE transition."
        )
    )

    @field_validator(
        "authorization_id", "certificate_id", "strategy_id", "risk_policy_version",
    )
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("max_notional", "max_position_size", "max_daily_loss_notional")
    @classmethod
    def validate_positive_money_bounds(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if v <= Decimal("0"):
            raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("max_drawdown_pct")
    @classmethod
    def validate_drawdown_pct(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="max_drawdown_pct")
        if v <= Decimal("0") or v > Decimal("100"):
            raise DomainValidationError(f"max_drawdown_pct must be in (0, 100], got: {v}")
        return v

    @field_validator("authorization_digest")
    @classmethod
    def validate_digests(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "digest")

    @field_validator("allowed_venues", "allowed_symbols")
    @classmethod
    def validate_string_tuples(cls, v: Tuple[str, ...], info: ValidationInfo) -> Tuple[str, ...]:
        field_name = info.field_name or "field"
        if not v:
            raise DomainValidationError(f"{field_name} cannot be empty.")
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise DomainValidationError(f"Items in {field_name} must be non-empty strings.")
        return tuple(sorted(set(item.strip() for item in v)))


def compute_authorization_digest(
    authorization_id: str,
    certificate_id: str,
    strategy_id: str,
    authorized_at: datetime,
    expires_at: datetime,
    max_notional: Decimal,
    max_position_size: Decimal,
    max_order_rate_per_minute: int,
    max_daily_loss_notional: Decimal,
    max_drawdown_pct: Decimal,
    allowed_venues: Tuple[str, ...],
    allowed_symbols: Tuple[str, ...],
    risk_policy_version: str,
    required_approvals: int,
    approval_digests: Tuple[str, ...],
) -> str:
    """Compute the canonical SHA-256 authorization_digest.

    Covers all operational parameters + required_approvals + sorted approval_digests.
    This is the single authoritative computation point for authorization_digest.
    """
    canonical: Dict[str, Any] = {
        "authorization_id": authorization_id,
        "certificate_id": certificate_id,
        "strategy_id": strategy_id,
        "authorized_at": authorized_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "max_notional": str(max_notional),
        "max_position_size": str(max_position_size),
        "max_order_rate_per_minute": max_order_rate_per_minute,
        "max_daily_loss_notional": str(max_daily_loss_notional),
        "max_drawdown_pct": str(max_drawdown_pct),
        "allowed_venues": sorted(allowed_venues),
        "allowed_symbols": sorted(allowed_symbols),
        "risk_policy_version": risk_policy_version,
        "required_approvals": required_approvals,
        "approval_digests": sorted(approval_digests),
    }
    return hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(canonical).encode("utf-8")
    ).hexdigest()


# ============================================================================
# 3. AUTHORIZATION REACTIVATION EVENT — SAME QUORUM AS ISSUANCE
# ============================================================================

class AuthorizationReactivationApproval(BaseModel):
    """Signed approval record bound to a specific AuthorizationReactivationEvent.

    Mirrors AuthorizationApproval but is explicitly bound to reactivation_id
    to prevent replay across reactivation events.

    Reactivation quorum MUST equal issuance quorum (required_approvals invariant).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    approver_id: str = Field(description="Authorized approver identifier.")
    public_key_id: str = Field(description="Key ID in TrustStore used to sign this approval.")
    role: ApproverRole = Field(description="Approver's role in the quorum.")
    reactivation_id: str = Field(description="AuthorizationReactivationEvent ID (replay protection).")
    authorization_id: str = Field(description="LiveAuthorization ID being reactivated.")
    approved_at: datetime = Field(description="UTC timestamp of approval.")
    approval_signature: str = Field(
        description="Base64-encoded Ed25519 signature over canonical reactivation approval payload."
    )
    approval_digest: str = Field(description="SHA-256 of canonical payload.")

    @field_validator(
        "approver_id", "public_key_id", "reactivation_id", "authorization_id", "approval_signature",
    )
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("approval_digest")
    @classmethod
    def validate_digest(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "approval_digest")

    def compute_canonical_payload_bytes(self) -> bytes:
        """Canonical bytes for Ed25519 signing/verification."""
        payload = {
            "reactivation_id": self.reactivation_id,
            "authorization_id": self.authorization_id,
            "approver_id": self.approver_id,
            "public_key_id": self.public_key_id,
            "role": self.role.value,
            "approved_at": self.approved_at.isoformat(),
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")


class AuthorizationReactivationEvent(BaseModel):
    """Immutable forensic event authorizing reactivation of a SUSPENDED authorization.

    INVARIANT: len(verified approvals) >= required_approvals.
    required_approvals MUST equal the original LiveAuthorization.required_approvals.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    reactivation_id: str = Field(description="Unique deterministic reactivation event ID.")
    authorization_id: str = Field(description="Target LiveAuthorization ID being reactivated.")
    strategy_id: str = Field(description="Target strategy identifier.")
    reactivated_at: datetime = Field(description="UTC timestamp of reactivation.")

    root_cause_summary: str = Field(
        description="Audited root cause summary of previous suspension. Required for reactivation."
    )

    # Multi-Sig Approval Quorum (same N as issuance)
    required_approvals: int = Field(
        ge=1,
        description="Must equal original LiveAuthorization.required_approvals.",
    )
    approvals: Tuple[AuthorizationReactivationApproval, ...] = Field(
        description="Signed reactivation approval records."
    )

    reactivation_digest: str = Field(
        description="SHA-256 of canonical reactivation event (params + sorted approval_digests)."
    )

    @field_validator("reactivation_id", "authorization_id", "strategy_id", "root_cause_summary")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("reactivation_digest")
    @classmethod
    def validate_digests(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "digest")

    def compute_canonical_payload_bytes(self) -> bytes:
        """Canonical bytes for reactivation_digest computation."""
        payload = {
            "reactivation_id": self.reactivation_id,
            "authorization_id": self.authorization_id,
            "strategy_id": self.strategy_id,
            "reactivated_at": self.reactivated_at.isoformat(),
            "root_cause_summary": self.root_cause_summary,
            "required_approvals": self.required_approvals,
            "approval_digests": sorted(a.approval_digest for a in self.approvals),
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")


# ============================================================================
# 4. ORDER INTENT & LIFECYCLE
# ============================================================================

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    DAY = "DAY"


class OrderLifecycleState(str, Enum):
    """Order state machine.

    CANCEL_REQUESTED → BrokerConfirmation → CANCELLED
    CANCEL_REQUESTED → ConnectionLost     → UNKNOWN
    UNKNOWN must trigger reconciliation before any further action.
    """

    INTENT = "INTENT"
    SUBMITTED = "SUBMITTED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class OrderIntent(BaseModel):
    """Immutable intent to place an order, emitted before broker transmission."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: str = Field(description="Unique deterministic order intent ID.")
    authorization_id: str = Field(description="Active LiveAuthorization ID.")
    strategy_id: str = Field(description="Originating strategy identifier.")

    venue: str = Field(description="Target broker/exchange venue.")
    symbol: str = Field(description="Tradeable asset symbol.")
    side: OrderSide = Field(description="'BUY' or 'SELL'.")
    order_type: OrderType = Field(description="'LIMIT', 'MARKET', 'STOP_LIMIT'.")
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC, description="Time-in-force condition.")

    quantity: Decimal = Field(description="Requested order volume.")
    limit_price: Optional[Decimal] = Field(default=None, description="Limit price for non-market orders.")
    stop_price: Optional[Decimal] = Field(default=None, description="Stop trigger price if applicable.")

    created_at: datetime = Field(description="UTC timestamp of intent creation.")

    # Cryptographic Provenance Bindings
    signal_event_hash: str = Field(description="SHA-256 hash of triggering market signal event.")
    risk_snapshot_hash: str = Field(description="SHA-256 hash of RiskState at pre-submission check.")
    intent_digest: str = Field(description="SHA-256 hash of canonical order intent payload.")

    @field_validator("intent_id", "authorization_id", "strategy_id", "venue", "symbol")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="quantity")
        if v <= Decimal("0"):
            raise DomainValidationError(f"OrderIntent quantity must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("limit_price", "stop_price")
    @classmethod
    def validate_optional_prices(cls, v: Optional[Decimal], info: ValidationInfo) -> Optional[Decimal]:
        field_name = info.field_name or "price"
        if v is not None:
            ensure_finite_decimal(v, field_name=field_name)
            if v <= Decimal("0"):
                raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("signal_event_hash", "risk_snapshot_hash", "intent_digest")
    @classmethod
    def validate_digests(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "digest")


# ============================================================================
# 5. EXECUTION MANIFEST
# ============================================================================

class ExecutionManifest(BaseModel):
    """Immutable forensic audit record of a single live order execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: str = Field(description="Unique deterministic execution identifier.")
    authorization_id: str = Field(description="Linked LiveAuthorization identifier.")
    strategy_id: str = Field(description="Target strategy identifier.")
    intent_id: str = Field(description="Linked OrderIntent identifier.")
    intent_digest: str = Field(description="SHA-256 hash of originating OrderIntent.")

    client_order_id: str = Field(description="Client order identifier.")
    broker_order_id: Optional[str] = Field(default=None, description="Assigned broker order ID.")

    venue: str = Field(description="Target exchange or broker venue.")
    symbol: str = Field(description="Tradeable asset symbol.")
    order_side: OrderSide = Field(description="'BUY' or 'SELL'.")
    order_type: OrderType = Field(description="'LIMIT', 'MARKET', 'STOP_LIMIT'.")

    # Timing & Latency Attribution
    created_at: datetime = Field(description="Timestamp when OrderIntent was constructed.")
    submitted_at: datetime = Field(description="Timestamp when order packet left socket.")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Timestamp of broker acknowledgment.")
    first_fill_at: Optional[datetime] = Field(default=None, description="Timestamp of first fill packet.")
    closed_at: Optional[datetime] = Field(default=None, description="Timestamp when order reached terminal state.")

    network_latency_ms: Optional[float] = Field(default=None, description="Wire transit latency (ack - submit).")
    exchange_queue_latency_ms: Optional[float] = Field(default=None, description="Queue latency on exchange.")

    # Fill Economics & Slippage Attribution
    requested_qty: Decimal = Field(description="Requested volume from OrderIntent.")
    filled_qty: Decimal = Field(description="Cumulative filled volume.")
    benchmark_mid_price: Decimal = Field(description="Mid price at moment of OrderIntent creation.")
    average_fill_price: Optional[Decimal] = Field(default=None, description="Volume-weighted average fill price.")
    realized_slippage_bps: Optional[float] = Field(default=None, description="Realized execution drag vs. benchmark.")
    total_commission_paid: Decimal = Field(default=Decimal("0.0"), description="Total exchange/broker fees.")

    # Lineage Hashes
    source_signal_event_hash: str = Field(description="SHA-256 hash of triggering market event.")
    execution_digest: str = Field(description="SHA-256 hash of canonical execution record.")

    @field_validator("execution_id", "authorization_id", "strategy_id", "intent_id", "client_order_id", "venue", "symbol")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("requested_qty", "benchmark_mid_price")
    @classmethod
    def validate_strictly_positive(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if v <= Decimal("0"):
            raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("filled_qty", "total_commission_paid")
    @classmethod
    def validate_non_negative_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if v < Decimal("0"):
            raise DomainValidationError(f"{field_name} cannot be negative, got: {v}")
        return v

    @field_validator("average_fill_price")
    @classmethod
    def validate_optional_avg_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            ensure_finite_decimal(v, field_name="average_fill_price")
            if v <= Decimal("0"):
                raise DomainValidationError(f"average_fill_price must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("intent_digest", "source_signal_event_hash", "execution_digest")
    @classmethod
    def validate_digests(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "digest")


# ============================================================================
# 6. DYNAMIC RISK STATE & STALENESS INVARIANT
# ============================================================================

class CalculationStatus(str, Enum):
    NOMINAL = "NOMINAL"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class RiskStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    RESTRICTED = "RESTRICTED"
    HALTED = "HALTED"


class RiskState(BaseModel):
    """Dynamic, real-time snapshot of live risk and portfolio health."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(description="UTC timestamp of risk snapshot.")
    authorization_id: str = Field(description="Associated LiveAuthorization ID.")
    strategy_id: str = Field(description="Target strategy identifier.")

    # Financial Balances & PnL
    total_equity: Decimal = Field(description="Current mark-to-market equity.")
    realized_pnl_today: Decimal = Field(description="Realized PnL since daily reset.")
    unrealized_pnl: Decimal = Field(description="Floating unrealized PnL.")
    current_drawdown_pct: Decimal = Field(description="Peak-to-trough drawdown percentage.")

    # Exposure & Sizing
    gross_exposure_notional: Decimal = Field(description="Total gross notional exposure.")
    net_exposure_notional: Decimal = Field(description="Net directional notional exposure.")
    concentration_ratio: Decimal = Field(description="Largest position notional / total equity.")

    # Quantitative Risk Estimates & Epistemic Metadata
    parametric_var_95: Decimal = Field(description="1-day 95% Value at Risk (Modelled estimate).")
    historical_cvar_95: Decimal = Field(description="1-day 95% Conditional Value at Risk (Modelled estimate).")
    confidence_level: float = Field(default=0.95, description="Statistical confidence level.")
    estimation_window_bars: int = Field(default=252, description="Lookback bar horizon for covariance/VaR.")
    risk_model_version: str = Field(default="PARAMETRIC_GAUSSIAN_HURDLE_V1", description="Active risk model version.")

    # Data Freshness & Environmental Telemetry
    data_timestamp: datetime = Field(description="Timestamp of newest tick used in calculation.")
    data_age_ms: int = Field(ge=0, description="Age of newest input tick in milliseconds.")
    calculation_status: CalculationStatus = Field(description="Integrity status of risk calculation.")

    is_market_data_stale: bool = Field(description="True if data_age_ms exceeds staleness threshold.")
    is_broker_connected: bool = Field(description="True if gateway WebSocket/FIX session is active.")
    is_clock_skew_detected: bool = Field(description="True if local vs. gateway timestamp exceeds threshold.")

    risk_status: RiskStatus = Field(description="Active operational risk status.")
    active_kill_switch_event_id: Optional[str] = Field(default=None, description="Linked KillSwitchEvent if HALTED.")

    @field_validator("authorization_id", "strategy_id", "risk_model_version")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator(
        "total_equity", "realized_pnl_today", "unrealized_pnl",
        "gross_exposure_notional", "net_exposure_notional",
        "parametric_var_95", "historical_cvar_95",
    )
    @classmethod
    def validate_finite_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        return ensure_finite_decimal(v, field_name=info.field_name or "field")

    @field_validator("current_drawdown_pct")
    @classmethod
    def validate_drawdown_bounds(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="current_drawdown_pct")
        if v < Decimal("0") or v > Decimal("100"):
            raise DomainValidationError(f"current_drawdown_pct must be in [0, 100], got: {v}")
        return v

    @field_validator("concentration_ratio")
    @classmethod
    def validate_concentration_ratio(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="concentration_ratio")
        if v < Decimal("0") or v > Decimal("1"):
            raise DomainValidationError(f"concentration_ratio must be in [0, 1], got: {v}")
        return v


# ============================================================================
# 7. KILL SWITCH ENGINE & EVENT SCHEMAS
# ============================================================================

class KillSwitchAction(str, Enum):
    HALT_NEW_ORDERS = "HALT_NEW_ORDERS"
    CANCEL_WORKING_ORDERS = "CANCEL_WORKING_ORDERS"
    CONTROLLED_DERISK = "CONTROLLED_DERISK"
    EMERGENCY_FLATTEN = "EMERGENCY_FLATTEN"
    FREEZE_AND_RECONCILE = "FREEZE_AND_RECONCILE"


class KillSwitchTriggerType(str, Enum):
    STALE_MARKET_DATA = "STALE_MARKET_DATA"
    MAX_DAILY_LOSS = "MAX_DAILY_LOSS"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"
    RECONCILIATION_FAILURE = "RECONCILIATION_FAILURE"
    CLOCK_SKEW_DETECTED = "CLOCK_SKEW_DETECTED"
    MARKET_CLOSED = "MARKET_CLOSED"
    MANUAL_HALT = "MANUAL_HALT"


class KillSwitchEvent(BaseModel):
    """Immutable forensic event emitted upon automated or manual emergency halt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(description="Unique deterministic kill switch event ID.")
    triggered_at: datetime = Field(description="UTC timestamp of emergency halt.")
    trigger_type: KillSwitchTriggerType = Field(description="Cause of emergency halt.")
    severity: str = Field(description="'CRITICAL' or 'FATAL'.")

    observed_metric_value: str = Field(description="Observed metric at time of halt.")
    threshold_limit_value: str = Field(description="Configured limit threshold breached.")

    affected_strategies: Tuple[str, ...] = Field(min_length=1, description="Strategy IDs halted.")
    primary_action: KillSwitchAction = Field(description="Primary immediate safety action.")
    position_action: KillSwitchAction = Field(description="Prescribed action on open positions.")
    actor: str = Field(description="Entity triggering halt.")

    event_digest: str = Field(description="SHA-256 hash of canonical kill event.")

    @field_validator("event_id", "severity", "observed_metric_value", "threshold_limit_value", "actor")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("affected_strategies")
    @classmethod
    def validate_affected_strategies(cls, v: Tuple[str, ...]) -> Tuple[str, ...]:
        if not v:
            raise DomainValidationError("affected_strategies cannot be empty.")
        for s in v:
            if not isinstance(s, str) or not s.strip():
                raise DomainValidationError("Strategy IDs in affected_strategies must be non-empty strings.")
        return tuple(sorted(set(s.strip() for s in v)))

    @field_validator("event_digest")
    @classmethod
    def validate_digests(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "digest")


# ============================================================================
# 8. RECONCILIATION REPORT SCHEMA
# ============================================================================

class ReconciliationReport(BaseModel):
    """Forensic report of state reconciliation between internal shadow ledger and broker."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reconciliation_id: str = Field(description="Unique reconciliation event identifier.")
    timestamp: datetime = Field(description="UTC timestamp of reconciliation check.")
    venue: str = Field(description="Target exchange or broker venue.")
    is_in_parity: bool = Field(description="True if all 6 parity checks passed without discrepancy.")

    # Parity Metrics
    internal_open_orders_count: int = Field(ge=0, description="Active order count in shadow ledger.")
    broker_open_orders_count: int = Field(ge=0, description="Working order count on broker exchange.")

    position_discrepancies: Tuple[Dict[str, Any], ...] = Field(default=(), description="Mismatched positions.")
    order_discrepancies: Tuple[Dict[str, Any], ...] = Field(default=(), description="Mismatched orders.")
    cash_discrepancy_amount: Decimal = Field(default=Decimal("0.0"), description="Discrepancy in account equity.")

    action_taken: str = Field(description="'NOMINAL_LOGGED' or 'HALTED_ON_DISCREPANCY'.")
    report_digest: str = Field(description="SHA-256 hash of reconciliation state.")

    @field_validator("reconciliation_id", "venue", "action_taken")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("cash_discrepancy_amount")
    @classmethod
    def validate_finite_decimals(cls, v: Decimal) -> Decimal:
        return ensure_finite_decimal(v, field_name="cash_discrepancy_amount")

    @field_validator("report_digest")
    @classmethod
    def validate_digests(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "digest")
