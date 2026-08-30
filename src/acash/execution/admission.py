"""Phase 7: Pre-Live Risk Admission & Verification Engine.

Enforces fail-closed cryptographic verification and operational invariants for:
1. ValidationCertificate verification (Authenticity, Integrity, Expiration, Revocation)
2. LiveAuthorization issuance, multi-sig quorum, and state transitions
3. OrderIntent admission against active operational constraints
4. KillSwitch evaluation and Trigger-to-Action dispatch
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Optional, Sequence, Tuple

from acash.core.domain.exceptions import DomainValidationError
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import Ed25519TrustStore
from acash.execution.operational_restriction import RiskRestrictionAuthority
from acash.execution.schema import (
    AuthorizationApproval,
    AuthorizationReactivationApproval,
    AuthorizationReactivationEvent,
    AuthorizationStatus,
    CalculationStatus,
    CertificateRevocationEvent,
    KillSwitchAction,
    KillSwitchEvent,
    KillSwitchTriggerType,
    LiveAuthorization,
    OrderIntent,
    OrderSide,
    OrderType,
    RiskState,
    RiskStatus,
    TimeInForce,
    ValidationCertificate,
    compute_authorization_digest,
)
from acash.validation.schema import ValidationGateVerdict


class PreLiveRiskAdmissionError(DomainValidationError):
    """Raised when pre-live risk admission or certificate verification fails closed."""


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _verify_trust_store_signature(
    trust_store: Ed25519TrustStore,
    key_id: str,
    payload_bytes: bytes,
    signature_b64: str,
    signed_at: datetime,
) -> None:
    """Expose cryptographic trust failures at the pre-live admission boundary."""
    try:
        trust_store.verify(key_id, payload_bytes, signature_b64, at_time=signed_at)
    except DomainValidationError as exc:
        raise PreLiveRiskAdmissionError(str(exc)) from exc


def _validate_authorization_params(
    certificate: ValidationCertificate,
    max_notional: Decimal,
    max_position_size: Decimal,
    authorized_at: datetime,
    expires_at: datetime,
) -> None:
    if max_position_size > max_notional:
        raise PreLiveRiskAdmissionError(
            f"max_position_size ({max_position_size}) cannot exceed total max_notional ({max_notional})."
        )
    if _ensure_utc(authorized_at) >= _ensure_utc(expires_at):
        raise PreLiveRiskAdmissionError(
            f"authorized_at ({authorized_at.isoformat()}) must be strictly before "
            f"expires_at ({expires_at.isoformat()})."
        )
    if certificate.strategy_id.strip() == "":
        raise PreLiveRiskAdmissionError("ValidationCertificate strategy_id must be non-empty.")


def _verify_revocation_event(
    revocation: CertificateRevocationEvent,
    certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    current_utc: datetime,
) -> None:
    if revocation.certificate_id != certificate.certificate_id:
        return

    if revocation.strategy_id != certificate.strategy_id:
        raise PreLiveRiskAdmissionError(
            f"Revocation {revocation.revocation_id} strategy_id '{revocation.strategy_id}' "
            f"does not match certificate strategy_id '{certificate.strategy_id}'."
        )

    now_utc = _ensure_utc(current_utc)
    revoked_at_utc = _ensure_utc(revocation.revoked_at)
    if revoked_at_utc > now_utc:
        raise PreLiveRiskAdmissionError(
            f"Revocation {revocation.revocation_id} has future revoked_at "
            f"{revocation.revoked_at.isoformat()}."
        )

    expected_digest = hashlib.sha256(revocation.compute_canonical_payload_bytes()).hexdigest()
    if revocation.revocation_digest != expected_digest:
        raise PreLiveRiskAdmissionError(
            f"Revocation {revocation.revocation_id} digest mismatch."
        )

    _verify_trust_store_signature(
        trust_store,
        revocation.actor_public_key_id,
        revocation.compute_canonical_payload_bytes(),
        revocation.revocation_signature,
        revocation.revoked_at,
    )

    raise PreLiveRiskAdmissionError(
        f"Certificate {certificate.certificate_id} was revoked on "
        f"{revocation.revoked_at.isoformat()} by {revocation.actor}. Reason: {revocation.reason}"
    )


def verify_validation_certificate(
    certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    revocation_events: Sequence[CertificateRevocationEvent] = (),
    current_utc: Optional[datetime] = None,
) -> None:
    """Verify cryptographic integrity, issuer authenticity, expiration, and revocation status."""
    if certificate.verdict != ValidationGateVerdict.PASS_TRADEABLE_ALPHA:
        raise PreLiveRiskAdmissionError(
            f"Certificate {certificate.certificate_id} rejected: verdict is {certificate.verdict}, "
            "must be PASS_TRADEABLE_ALPHA."
        )

    now = _ensure_utc(current_utc or datetime.now(timezone.utc))

    if certificate.expires_at is not None:
        cert_exp = _ensure_utc(certificate.expires_at)
        if now > cert_exp:
            raise PreLiveRiskAdmissionError(
                f"Certificate {certificate.certificate_id} has expired at "
                f"{certificate.expires_at.isoformat()} (current time: {now.isoformat()})."
            )

    for revocation in revocation_events:
        _verify_revocation_event(revocation, certificate, trust_store, now)

    if certificate.signature_algorithm != "Ed25519":
        raise PreLiveRiskAdmissionError(
            f"Certificate {certificate.certificate_id} uses unsupported signature algorithm "
            f"'{certificate.signature_algorithm}'; only Ed25519 is accepted."
        )

    try:
        entry = trust_store.resolve(
            certificate.issuer_public_key_id, at_time=certificate.created_at
        )
    except DomainValidationError as exc:
        raise PreLiveRiskAdmissionError(str(exc)) from exc
    if entry.issuer_id != certificate.issuer_id:
        raise PreLiveRiskAdmissionError(
            f"Certificate issuer_id '{certificate.issuer_id}' does not match TrustStore entry "
            f"issuer_id '{entry.issuer_id}' for key '{certificate.issuer_public_key_id}'."
        )

    _verify_trust_store_signature(
        trust_store,
        certificate.issuer_public_key_id,
        certificate.compute_canonical_payload_bytes(),
        certificate.certificate_signature,
        certificate.created_at,
    )


def _verify_authorization_approval(
    approval: AuthorizationApproval,
    authorization_id: str,
    trust_store: Ed25519TrustStore,
) -> None:
    if approval.authorization_id != authorization_id:
        raise PreLiveRiskAdmissionError(
            f"Approval from '{approval.approver_id}' is bound to authorization_id "
            f"'{approval.authorization_id}', expected '{authorization_id}'."
        )

    expected_digest = hashlib.sha256(approval.compute_canonical_payload_bytes()).hexdigest()
    if approval.approval_digest != expected_digest:
        raise PreLiveRiskAdmissionError(
            f"Approval digest mismatch for approver '{approval.approver_id}'."
        )

    _verify_trust_store_signature(
        trust_store,
        approval.public_key_id,
        approval.compute_canonical_payload_bytes(),
        approval.approval_signature,
        approval.approved_at,
    )


def _verify_reactivation_approval(
    approval: AuthorizationReactivationApproval,
    reactivation_id: str,
    authorization_id: str,
    trust_store: Ed25519TrustStore,
) -> None:
    if approval.reactivation_id != reactivation_id:
        raise PreLiveRiskAdmissionError(
            f"Reactivation approval from '{approval.approver_id}' is bound to reactivation_id "
            f"'{approval.reactivation_id}', expected '{reactivation_id}'."
        )
    if approval.authorization_id != authorization_id:
        raise PreLiveRiskAdmissionError(
            f"Reactivation approval from '{approval.approver_id}' is bound to authorization_id "
            f"'{approval.authorization_id}', expected '{authorization_id}'."
        )

    expected_digest = hashlib.sha256(approval.compute_canonical_payload_bytes()).hexdigest()
    if approval.approval_digest != expected_digest:
        raise PreLiveRiskAdmissionError(
            f"Reactivation approval digest mismatch for approver '{approval.approver_id}'."
        )

    _verify_trust_store_signature(
        trust_store,
        approval.public_key_id,
        approval.compute_canonical_payload_bytes(),
        approval.approval_signature,
        approval.approved_at,
    )


def _collect_verified_approvals(
    authorization_id: str,
    approvals: Sequence[AuthorizationApproval],
    trust_store: Ed25519TrustStore,
) -> Tuple[AuthorizationApproval, ...]:
    verified: list[AuthorizationApproval] = []
    seen_approvers: set[str] = set()
    seen_keys: set[str] = set()

    for approval in approvals:
        if approval.approver_id in seen_approvers:
            raise PreLiveRiskAdmissionError(
                f"Duplicate approver_id '{approval.approver_id}' in approval set."
            )
        if approval.public_key_id in seen_keys:
            raise PreLiveRiskAdmissionError(
                f"Duplicate public_key_id '{approval.public_key_id}' in approval set."
            )
        _verify_authorization_approval(approval, authorization_id, trust_store)
        seen_approvers.add(approval.approver_id)
        seen_keys.add(approval.public_key_id)
        verified.append(approval)

    return tuple(verified)


def _build_live_authorization(
    *,
    certificate: ValidationCertificate,
    authorization_id: str,
    status: AuthorizationStatus,
    authorized_at: datetime,
    expires_at: datetime,
    max_notional: Decimal,
    max_position_size: Decimal,
    max_order_rate_per_minute: int,
    max_daily_loss_notional: Decimal,
    max_drawdown_pct: Decimal,
    allowed_venues: Sequence[str],
    allowed_symbols: Sequence[str],
    risk_policy_version: str,
    required_approvals: int,
    approvals: Sequence[AuthorizationApproval],
) -> LiveAuthorization:
    approval_digests = tuple(sorted(a.approval_digest for a in approvals))
    auth_digest = compute_authorization_digest(
        authorization_id=authorization_id,
        certificate_id=certificate.certificate_id,
        strategy_id=certificate.strategy_id,
        authorized_at=authorized_at,
        expires_at=expires_at,
        max_notional=max_notional,
        max_position_size=max_position_size,
        max_order_rate_per_minute=max_order_rate_per_minute,
        max_daily_loss_notional=max_daily_loss_notional,
        max_drawdown_pct=max_drawdown_pct,
        allowed_venues=tuple(allowed_venues),
        allowed_symbols=tuple(allowed_symbols),
        risk_policy_version=risk_policy_version,
        required_approvals=required_approvals,
        approval_digests=approval_digests,
    )

    return LiveAuthorization(
        authorization_id=authorization_id,
        certificate_id=certificate.certificate_id,
        strategy_id=certificate.strategy_id,
        status=status,
        authorized_at=authorized_at,
        expires_at=expires_at,
        max_notional=max_notional,
        max_position_size=max_position_size,
        max_order_rate_per_minute=max_order_rate_per_minute,
        max_daily_loss_notional=max_daily_loss_notional,
        max_drawdown_pct=max_drawdown_pct,
        allowed_venues=tuple(allowed_venues),
        allowed_symbols=tuple(allowed_symbols),
        risk_policy_version=risk_policy_version,
        required_approvals=required_approvals,
        approvals=tuple(approvals),
        authorization_digest=auth_digest,
    )


def create_draft_authorization(
    certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    authorization_id: str,
    max_notional: Decimal,
    max_position_size: Decimal,
    max_order_rate_per_minute: int,
    max_daily_loss_notional: Decimal,
    max_drawdown_pct: Decimal,
    allowed_venues: Sequence[str],
    allowed_symbols: Sequence[str],
    risk_policy_version: str,
    required_approvals: int,
    authorized_at: datetime,
    expires_at: datetime,
    revocation_events: Sequence[CertificateRevocationEvent] = (),
) -> LiveAuthorization:
    """Create a DRAFT LiveAuthorization after certificate verification."""
    verify_validation_certificate(
        certificate=certificate,
        trust_store=trust_store,
        revocation_events=revocation_events,
        current_utc=authorized_at,
    )
    _validate_authorization_params(
        certificate, max_notional, max_position_size, authorized_at, expires_at
    )
    if required_approvals < 1:
        raise PreLiveRiskAdmissionError("required_approvals must be >= 1.")

    return _build_live_authorization(
        certificate=certificate,
        authorization_id=authorization_id,
        status=AuthorizationStatus.DRAFT,
        authorized_at=authorized_at,
        expires_at=expires_at,
        max_notional=max_notional,
        max_position_size=max_position_size,
        max_order_rate_per_minute=max_order_rate_per_minute,
        max_daily_loss_notional=max_daily_loss_notional,
        max_drawdown_pct=max_drawdown_pct,
        allowed_venues=allowed_venues,
        allowed_symbols=allowed_symbols,
        risk_policy_version=risk_policy_version,
        required_approvals=required_approvals,
        approvals=(),
    )


def issue_live_authorization(
    certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    authorization_id: str,
    approvals: Sequence[AuthorizationApproval],
    required_approvals: int,
    max_notional: Decimal,
    max_position_size: Decimal,
    max_order_rate_per_minute: int,
    max_daily_loss_notional: Decimal,
    max_drawdown_pct: Decimal,
    allowed_venues: Sequence[str],
    allowed_symbols: Sequence[str],
    risk_policy_version: str,
    authorized_at: datetime,
    expires_at: datetime,
    revocation_events: Sequence[CertificateRevocationEvent] = (),
) -> LiveAuthorization:
    """Issue a LiveAuthorization after certificate verification and approval quorum check."""
    verify_validation_certificate(
        certificate=certificate,
        trust_store=trust_store,
        revocation_events=revocation_events,
        current_utc=authorized_at,
    )
    _validate_authorization_params(
        certificate, max_notional, max_position_size, authorized_at, expires_at
    )
    if required_approvals < 1:
        raise PreLiveRiskAdmissionError("required_approvals must be >= 1.")

    verified_approvals = _collect_verified_approvals(authorization_id, approvals, trust_store)
    if len(verified_approvals) > required_approvals:
        raise PreLiveRiskAdmissionError(
            f"Approval count {len(verified_approvals)} exceeds required_approvals {required_approvals}."
        )

    status = (
        AuthorizationStatus.ACTIVE
        if len(verified_approvals) >= required_approvals
        else AuthorizationStatus.PENDING_APPROVAL
    )

    return _build_live_authorization(
        certificate=certificate,
        authorization_id=authorization_id,
        status=status,
        authorized_at=authorized_at,
        expires_at=expires_at,
        max_notional=max_notional,
        max_position_size=max_position_size,
        max_order_rate_per_minute=max_order_rate_per_minute,
        max_daily_loss_notional=max_daily_loss_notional,
        max_drawdown_pct=max_drawdown_pct,
        allowed_venues=allowed_venues,
        allowed_symbols=allowed_symbols,
        risk_policy_version=risk_policy_version,
        required_approvals=required_approvals,
        approvals=verified_approvals,
    )


def submit_for_approval(auth: LiveAuthorization) -> LiveAuthorization:
    """Transition DRAFT -> PENDING_APPROVAL."""
    if auth.status != AuthorizationStatus.DRAFT:
        raise PreLiveRiskAdmissionError(
            f"submit_for_approval requires DRAFT status, got {auth.status}."
        )
    return auth.model_copy(update={"status": AuthorizationStatus.PENDING_APPROVAL})


def apply_approval(
    auth: LiveAuthorization,
    approval: AuthorizationApproval,
    trust_store: Ed25519TrustStore,
) -> LiveAuthorization:
    """Append a verified approval; transition to ACTIVE when quorum is reached."""
    if auth.status != AuthorizationStatus.PENDING_APPROVAL:
        raise PreLiveRiskAdmissionError(
            f"apply_approval requires PENDING_APPROVAL status, got {auth.status}."
        )

    for existing in auth.approvals:
        if existing.approver_id == approval.approver_id:
            raise PreLiveRiskAdmissionError(
                f"Duplicate approver_id '{approval.approver_id}'."
            )
        if existing.public_key_id == approval.public_key_id:
            raise PreLiveRiskAdmissionError(
                f"Duplicate public_key_id '{approval.public_key_id}'."
            )

    _verify_authorization_approval(approval, auth.authorization_id, trust_store)
    new_approvals = auth.approvals + (approval,)

    if len(new_approvals) > auth.required_approvals:
        raise PreLiveRiskAdmissionError(
            f"Approval count {len(new_approvals)} exceeds required_approvals {auth.required_approvals}."
        )

    new_status = (
        AuthorizationStatus.ACTIVE
        if len(new_approvals) >= auth.required_approvals
        else AuthorizationStatus.PENDING_APPROVAL
    )

    approval_digests = tuple(sorted(a.approval_digest for a in new_approvals))
    new_digest = compute_authorization_digest(
        authorization_id=auth.authorization_id,
        certificate_id=auth.certificate_id,
        strategy_id=auth.strategy_id,
        authorized_at=auth.authorized_at,
        expires_at=auth.expires_at,
        max_notional=auth.max_notional,
        max_position_size=auth.max_position_size,
        max_order_rate_per_minute=auth.max_order_rate_per_minute,
        max_daily_loss_notional=auth.max_daily_loss_notional,
        max_drawdown_pct=auth.max_drawdown_pct,
        allowed_venues=auth.allowed_venues,
        allowed_symbols=auth.allowed_symbols,
        risk_policy_version=auth.risk_policy_version,
        required_approvals=auth.required_approvals,
        approval_digests=approval_digests,
    )

    return auth.model_copy(
        update={
            "status": new_status,
            "approvals": new_approvals,
            "authorization_digest": new_digest,
        }
    )


def suspend_authorization(
    auth: LiveAuthorization,
    reason: str,
    actor_id: str,
) -> LiveAuthorization:
    """Transition ACTIVE -> SUSPENDED."""
    if auth.status != AuthorizationStatus.ACTIVE:
        raise PreLiveRiskAdmissionError(
            f"suspend_authorization requires ACTIVE status, got {auth.status}."
        )
    if not reason.strip():
        raise PreLiveRiskAdmissionError("Suspension reason must be non-empty.")
    if not actor_id.strip():
        raise PreLiveRiskAdmissionError("Suspension actor_id must be non-empty.")
    return auth.model_copy(update={"status": AuthorizationStatus.SUSPENDED})


def reactivate_authorization(
    auth: LiveAuthorization,
    event: AuthorizationReactivationEvent,
    trust_store: Ed25519TrustStore,
) -> LiveAuthorization:
    """Transition SUSPENDED -> ACTIVE after same-quorum reactivation verification."""
    if auth.status != AuthorizationStatus.SUSPENDED:
        raise PreLiveRiskAdmissionError(
            f"reactivate_authorization requires SUSPENDED status, got {auth.status}."
        )

    if event.authorization_id != auth.authorization_id:
        raise PreLiveRiskAdmissionError(
            f"Reactivation event authorization_id '{event.authorization_id}' "
            f"does not match '{auth.authorization_id}'."
        )
    if event.strategy_id != auth.strategy_id:
        raise PreLiveRiskAdmissionError(
            f"Reactivation event strategy_id '{event.strategy_id}' "
            f"does not match '{auth.strategy_id}'."
        )
    if event.required_approvals != auth.required_approvals:
        raise PreLiveRiskAdmissionError(
            f"Reactivation required_approvals ({event.required_approvals}) must equal "
            f"authorization required_approvals ({auth.required_approvals})."
        )
    if not event.root_cause_summary.strip():
        raise PreLiveRiskAdmissionError("Reactivation root_cause_summary must be non-empty.")

    expected_reactivation_digest = hashlib.sha256(
        event.compute_canonical_payload_bytes()
    ).hexdigest()
    if event.reactivation_digest != expected_reactivation_digest:
        raise PreLiveRiskAdmissionError("Reactivation event digest mismatch.")

    seen_approvers: set[str] = set()
    seen_keys: set[str] = set()
    verified_count = 0
    for approval in event.approvals:
        if approval.approver_id in seen_approvers:
            raise PreLiveRiskAdmissionError(
                f"Duplicate reactivation approver_id '{approval.approver_id}'."
            )
        if approval.public_key_id in seen_keys:
            raise PreLiveRiskAdmissionError(
                f"Duplicate reactivation public_key_id '{approval.public_key_id}'."
            )
        _verify_reactivation_approval(
            approval, event.reactivation_id, auth.authorization_id, trust_store
        )
        seen_approvers.add(approval.approver_id)
        seen_keys.add(approval.public_key_id)
        verified_count += 1

    if verified_count < auth.required_approvals:
        raise PreLiveRiskAdmissionError(
            f"Reactivation quorum not met: {verified_count} verified approvals, "
            f"required {auth.required_approvals}."
        )

    return auth.model_copy(update={"status": AuthorizationStatus.ACTIVE})


def revoke_authorization(
    auth: LiveAuthorization,
    reason: str,
    actor_id: str,
) -> LiveAuthorization:
    """Transition to REVOKED from non-terminal operational states."""
    if auth.status in (AuthorizationStatus.REVOKED, AuthorizationStatus.EXPIRED):
        raise PreLiveRiskAdmissionError(
            f"revoke_authorization cannot transition from terminal status {auth.status}."
        )
    if not reason.strip():
        raise PreLiveRiskAdmissionError("Revocation reason must be non-empty.")
    if not actor_id.strip():
        raise PreLiveRiskAdmissionError("Revocation actor_id must be non-empty.")
    return auth.model_copy(update={"status": AuthorizationStatus.REVOKED})


def expire_authorization(
    auth: LiveAuthorization,
    current_utc: datetime,
) -> LiveAuthorization:
    """Transition ACTIVE -> EXPIRED when current time exceeds expires_at."""
    if auth.status != AuthorizationStatus.ACTIVE:
        raise PreLiveRiskAdmissionError(
            f"expire_authorization requires ACTIVE status, got {auth.status}."
        )
    now = _ensure_utc(current_utc)
    expires = _ensure_utc(auth.expires_at)
    if now <= expires:
        raise PreLiveRiskAdmissionError(
            f"Authorization {auth.authorization_id} has not expired "
            f"(expires_at={auth.expires_at.isoformat()}, current={now.isoformat()})."
        )
    return auth.model_copy(update={"status": AuthorizationStatus.EXPIRED})


# ============================================================================
# ORDER INTENT ADMISSION
# ============================================================================

def construct_order_intent(
    authorization: LiveAuthorization,
    intent_id: str,
    venue: str,
    symbol: str,
    side: OrderSide,
    order_type: OrderType,
    quantity: Decimal,
    current_risk: RiskState,
    signal_event_hash: str,
    created_at: datetime,
    restriction_authority: RiskRestrictionAuthority,
    limit_price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: TimeInForce = TimeInForce.GTC,
) -> OrderIntent:
    """Validate operational limits and emit an immutable OrderIntent.

    ``restriction_authority`` is REQUIRED. The admission gate PULLS the
    authoritative OPEN-restriction snapshot from it for this intent's scope
    (strategy + authorization) and ENFORCES it. This is deliberately
    non-optional: a caller cannot "forget" to supply restrictions and thereby
    bypass the restriction boundary (no fail-open). Admission only ENFORCES; it
    never opens/clears a restriction or mutates restriction lifecycle.
    """
    if authorization.status != AuthorizationStatus.ACTIVE:
        raise PreLiveRiskAdmissionError(
            f"Cannot create OrderIntent: LiveAuthorization {authorization.authorization_id} "
            f"is {authorization.status}, must be ACTIVE."
        )

    gate = restriction_authority.gate_for_intent(
        strategy_id=authorization.strategy_id,
        authorization_id=authorization.authorization_id,
    )
    block_reason = gate.block_reason()
    if block_reason is not None:
        raise PreLiveRiskAdmissionError(
            f"Cannot create OrderIntent: {block_reason}"
        )

    now_tz = _ensure_utc(created_at)
    auth_exp_tz = _ensure_utc(authorization.expires_at)
    if now_tz > auth_exp_tz:
        raise PreLiveRiskAdmissionError(
            f"LiveAuthorization {authorization.authorization_id} expired at "
            f"{authorization.expires_at.isoformat()}."
        )

    if venue not in authorization.allowed_venues:
        raise PreLiveRiskAdmissionError(
            f"Venue '{venue}' is not permitted by LiveAuthorization "
            f"{authorization.authorization_id}. Allowed: {authorization.allowed_venues}"
        )
    if symbol not in authorization.allowed_symbols:
        raise PreLiveRiskAdmissionError(
            f"Symbol '{symbol}' is not permitted by LiveAuthorization "
            f"{authorization.authorization_id}. Allowed: {authorization.allowed_symbols}"
        )

    if quantity > authorization.max_position_size:
        raise PreLiveRiskAdmissionError(
            f"Order quantity {quantity} exceeds authorized max_position_size "
            f"({authorization.max_position_size})."
        )

    if current_risk.calculation_status != CalculationStatus.NOMINAL:
        raise PreLiveRiskAdmissionError(
            f"Risk calculation is not NOMINAL (status: {current_risk.calculation_status}, "
            f"data_age: {current_risk.data_age_ms}ms). Orders halted fail-closed."
        )
    if current_risk.risk_status != RiskStatus.NORMAL:
        raise PreLiveRiskAdmissionError(
            f"Operational risk state is {current_risk.risk_status}. New orders blocked."
        )

    risk_snapshot_bytes = CanonicalConfigSerializer.to_canonical_json({
        "timestamp": current_risk.timestamp.isoformat(),
        "total_equity": str(current_risk.total_equity),
        "gross_exposure_notional": str(current_risk.gross_exposure_notional),
        "current_drawdown_pct": str(current_risk.current_drawdown_pct),
        "calculation_status": current_risk.calculation_status.value,
    }).encode("utf-8")
    risk_snapshot_hash = hashlib.sha256(risk_snapshot_bytes).hexdigest()

    canonical_intent_payload = {
        "intent_id": intent_id,
        "authorization_id": authorization.authorization_id,
        "strategy_id": authorization.strategy_id,
        "venue": venue,
        "symbol": symbol,
        "side": side.value,
        "order_type": order_type.value,
        "time_in_force": time_in_force.value,
        "quantity": str(quantity),
        "limit_price": str(limit_price) if limit_price is not None else None,
        "stop_price": str(stop_price) if stop_price is not None else None,
        "created_at": created_at.isoformat(),
        "signal_event_hash": signal_event_hash,
        "risk_snapshot_hash": risk_snapshot_hash,
    }
    intent_digest = hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(canonical_intent_payload).encode("utf-8")
    ).hexdigest()

    return OrderIntent(
        intent_id=intent_id,
        authorization_id=authorization.authorization_id,
        strategy_id=authorization.strategy_id,
        venue=venue,
        symbol=symbol,
        side=side,
        order_type=order_type,
        time_in_force=time_in_force,
        quantity=quantity,
        limit_price=limit_price,
        stop_price=stop_price,
        created_at=created_at,
        signal_event_hash=signal_event_hash,
        risk_snapshot_hash=risk_snapshot_hash,
        intent_digest=intent_digest,
    )


# ============================================================================
# KILL SWITCH TRIGGER EVALUATION
# ============================================================================

def evaluate_kill_switch_triggers(
    authorization: LiveAuthorization,
    risk_state: RiskState,
    staleness_threshold_ms: int = 1500,
    clock_skew_threshold_ms: int = 500,
    triggered_at: Optional[datetime] = None,
) -> Optional[KillSwitchEvent]:
    """Evaluate real-time risk state against authorization bounds and trigger fail-closed KillSwitchEvent."""
    event_time = triggered_at or datetime.now(timezone.utc)
    trigger_type: Optional[KillSwitchTriggerType] = None
    metric_str = ""
    threshold_str = ""
    primary_action = KillSwitchAction.HALT_NEW_ORDERS
    pos_action = KillSwitchAction.FREEZE_AND_RECONCILE

    if not risk_state.is_broker_connected:
        trigger_type = KillSwitchTriggerType.BROKER_DISCONNECTED
        metric_str = "broker_connected=False"
        threshold_str = "broker_connected=True"
        primary_action = KillSwitchAction.HALT_NEW_ORDERS
        pos_action = KillSwitchAction.FREEZE_AND_RECONCILE

    elif risk_state.is_market_data_stale or risk_state.data_age_ms > staleness_threshold_ms:
        trigger_type = KillSwitchTriggerType.STALE_MARKET_DATA
        metric_str = f"data_age_ms={risk_state.data_age_ms}"
        threshold_str = f"max_allowed={staleness_threshold_ms}ms"
        primary_action = KillSwitchAction.CANCEL_WORKING_ORDERS
        pos_action = KillSwitchAction.FREEZE_AND_RECONCILE

    elif risk_state.is_clock_skew_detected:
        trigger_type = KillSwitchTriggerType.CLOCK_SKEW_DETECTED
        metric_str = "clock_skew_detected=True"
        threshold_str = f"max_drift={clock_skew_threshold_ms}ms"
        primary_action = KillSwitchAction.CANCEL_WORKING_ORDERS
        pos_action = KillSwitchAction.FREEZE_AND_RECONCILE

    elif risk_state.realized_pnl_today < -authorization.max_daily_loss_notional:
        trigger_type = KillSwitchTriggerType.MAX_DAILY_LOSS
        metric_str = f"realized_loss={abs(risk_state.realized_pnl_today)}"
        threshold_str = f"max_daily_loss={authorization.max_daily_loss_notional}"
        primary_action = KillSwitchAction.CANCEL_WORKING_ORDERS
        pos_action = KillSwitchAction.CONTROLLED_DERISK

    elif risk_state.current_drawdown_pct >= authorization.max_drawdown_pct:
        trigger_type = KillSwitchTriggerType.MAX_DRAWDOWN
        metric_str = f"drawdown_pct={risk_state.current_drawdown_pct}%"
        threshold_str = f"max_drawdown_pct={authorization.max_drawdown_pct}%"
        primary_action = KillSwitchAction.CANCEL_WORKING_ORDERS
        pos_action = KillSwitchAction.EMERGENCY_FLATTEN

    if trigger_type is None:
        return None

    event_id = f"KILL_{trigger_type.value}_{int(event_time.timestamp() * 1000)}"

    canonical_payload = {
        "event_id": event_id,
        "triggered_at": event_time.isoformat(),
        "trigger_type": trigger_type.value,
        "severity": "CRITICAL",
        "observed_metric_value": metric_str,
        "threshold_limit_value": threshold_str,
        "affected_strategies": [authorization.strategy_id],
        "primary_action": primary_action.value,
        "position_action": pos_action.value,
        "actor": "SYSTEM_AUTOMATED_RISK_GATE",
    }
    event_digest = hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(canonical_payload).encode("utf-8")
    ).hexdigest()

    return KillSwitchEvent(
        event_id=event_id,
        triggered_at=event_time,
        trigger_type=trigger_type,
        severity="CRITICAL",
        observed_metric_value=metric_str,
        threshold_limit_value=threshold_str,
        affected_strategies=(authorization.strategy_id,),
        primary_action=primary_action,
        position_action=pos_action,
        actor="SYSTEM_AUTOMATED_RISK_GATE",
        event_digest=event_digest,
    )
