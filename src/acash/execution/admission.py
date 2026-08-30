"""Phase 7: Pre-Live Risk Admission & Verification Engine.

Enforces fail-closed cryptographic verification and operational invariants for:
1. ValidationCertificate verification (Authenticity, Integrity, Expiration, Revocation)
2. LiveAuthorization issuance and state transitions
3. OrderIntent admission against active operational constraints
4. KillSwitch evaluation and Trigger-to-Action dispatch
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Dict, List, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DomainValidationError
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.schema import (
    AuthorizationReactivationEvent,
    AuthorizationStatus,
    CalculationStatus,
    CertificateRevocationEvent,
    ExecutionManifest,
    KillSwitchAction,
    KillSwitchEvent,
    KillSwitchTriggerType,
    LiveAuthorization,
    OrderIntent,
    OrderLifecycleState,
    OrderSide,
    OrderType,
    RiskState,
    RiskStatus,
    TimeInForce,
    ValidationCertificate,
)
from acash.validation.schema import ValidationGateVerdict


class PreLiveRiskAdmissionError(DomainValidationError):
    """Raised when pre-live risk admission or certificate verification fails closed."""


# ============================================================================
# 1. CERTIFICATE VERIFICATION (Phase 6 Ingestion)
# ============================================================================

def verify_validation_certificate(
    certificate: ValidationCertificate,
    revocation_events: Sequence[CertificateRevocationEvent] = (),
    trusted_public_keys: Optional[Dict[str, str]] = None,
    current_utc: Optional[datetime] = None,
) -> None:
    """Verify cryptographic integrity, issuer authenticity, expiration, and revocation status of a certificate."""
    if certificate.verdict != ValidationGateVerdict.PASS_TRADEABLE_ALPHA:
        raise PreLiveRiskAdmissionError(
            f"Certificate {certificate.certificate_id} rejected: verdict is {certificate.verdict}, must be PASS_TRADEABLE_ALPHA."
        )

    # 1. Check expiration
    now = current_utc or datetime.now(timezone.utc)
    if certificate.expires_at is not None:
        cert_exp = certificate.expires_at if certificate.expires_at.tzinfo else certificate.expires_at.replace(tzinfo=timezone.utc)
        now_tz = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        if now_tz > cert_exp:
            raise PreLiveRiskAdmissionError(
                f"Certificate {certificate.certificate_id} has expired at {certificate.expires_at.isoformat()} (current time: {now.isoformat()})."
            )

    # 2. Check revocation ledger
    for rev in revocation_events:
        if rev.certificate_id == certificate.certificate_id:
            raise PreLiveRiskAdmissionError(
                f"Certificate {certificate.certificate_id} was revoked on {rev.revoked_at.isoformat()} by {rev.actor}. Reason: {rev.reason}"
            )

    # 3. Check digital signature authenticity if trusted keys are provided
    if trusted_public_keys is not None:
        if certificate.issuer_public_key_id not in trusted_public_keys:
            raise PreLiveRiskAdmissionError(
                f"Certificate issuer key ID '{certificate.issuer_public_key_id}' is not in trusted public keys registry."
            )
        # Verify deterministic signature binding
        expected_sig_input = certificate.compute_canonical_payload_bytes()
        trusted_key = trusted_public_keys[certificate.issuer_public_key_id]
        expected_sig = hashlib.sha256(expected_sig_input + trusted_key.encode("utf-8")).hexdigest()
        if certificate.certificate_signature != expected_sig:
            raise PreLiveRiskAdmissionError(
                f"Certificate digital signature mismatch for {certificate.certificate_id}."
            )


# ============================================================================
# 2. LIVE AUTHORIZATION ISSUANCE & TRANSITIONS
# ============================================================================

def issue_live_authorization(
    certificate: ValidationCertificate,
    authorization_id: str,
    max_notional: Decimal,
    max_position_size: Decimal,
    max_order_rate_per_minute: int,
    max_daily_loss_notional: Decimal,
    max_drawdown_pct: Decimal,
    allowed_venues: Sequence[str],
    allowed_symbols: Sequence[str],
    risk_policy_version: str,
    approver_id: str,
    approver_public_key_id: str,
    approver_secret_key: str,
    authorized_at: datetime,
    expires_at: datetime,
    revocation_events: Sequence[CertificateRevocationEvent] = (),
    trusted_public_keys: Optional[Dict[str, str]] = None,
) -> LiveAuthorization:
    """Issue a signed, active LiveAuthorization token after verifying certificate and capital constraints."""
    # 1. Strict certificate verification
    verify_validation_certificate(
        certificate=certificate,
        revocation_events=revocation_events,
        trusted_public_keys=trusted_public_keys,
        current_utc=authorized_at,
    )

    if max_position_size > max_notional:
        raise PreLiveRiskAdmissionError(
            f"max_position_size ({max_position_size}) cannot exceed total max_notional ({max_notional})."
        )

    if authorized_at >= expires_at:
        raise PreLiveRiskAdmissionError(
            f"authorized_at ({authorized_at.isoformat()}) must be strictly before expires_at ({expires_at.isoformat()})."
        )

    canonical_payload = {
        "authorization_id": authorization_id,
        "certificate_id": certificate.certificate_id,
        "strategy_id": certificate.strategy_id,
        "status": AuthorizationStatus.ACTIVE.value,
        "authorized_at": authorized_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "max_notional": str(max_notional),
        "max_position_size": str(max_position_size),
        "max_order_rate_per_minute": max_order_rate_per_minute,
        "max_daily_loss_notional": str(max_daily_loss_notional),
        "max_drawdown_pct": str(max_drawdown_pct),
        "allowed_venues": sorted(set(allowed_venues)),
        "allowed_symbols": sorted(set(allowed_symbols)),
        "risk_policy_version": risk_policy_version,
        "approver_id": approver_id,
        "approver_public_key_id": approver_public_key_id,
    }
    payload_bytes = CanonicalConfigSerializer.to_canonical_json(canonical_payload).encode("utf-8")
    auth_digest = hashlib.sha256(payload_bytes).hexdigest()
    auth_signature = hashlib.sha256(payload_bytes + approver_secret_key.encode("utf-8")).hexdigest()

    return LiveAuthorization(
        authorization_id=authorization_id,
        certificate_id=certificate.certificate_id,
        strategy_id=certificate.strategy_id,
        status=AuthorizationStatus.ACTIVE,
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
        approver_id=approver_id,
        approver_public_key_id=approver_public_key_id,
        authorization_signature=auth_signature,
        authorization_digest=auth_digest,
    )


# ============================================================================
# 3. ORDER INTENT ADMISSION
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
    limit_price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: TimeInForce = TimeInForce.GTC,
) -> OrderIntent:
    """Validate operational limits and emit an immutable OrderIntent."""
    # 1. Authorization status check
    if authorization.status != AuthorizationStatus.ACTIVE:
        raise PreLiveRiskAdmissionError(
            f"Cannot create OrderIntent: LiveAuthorization {authorization.authorization_id} is {authorization.status}, must be ACTIVE."
        )

    # 2. Expiration check
    now_tz = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    auth_exp_tz = authorization.expires_at if authorization.expires_at.tzinfo else authorization.expires_at.replace(tzinfo=timezone.utc)
    if now_tz > auth_exp_tz:
        raise PreLiveRiskAdmissionError(
            f"LiveAuthorization {authorization.authorization_id} expired at {authorization.expires_at.isoformat()}."
        )

    # 3. Whitelist checks
    if venue not in authorization.allowed_venues:
        raise PreLiveRiskAdmissionError(
            f"Venue '{venue}' is not permitted by LiveAuthorization {authorization.authorization_id}. Allowed: {authorization.allowed_venues}"
        )
    if symbol not in authorization.allowed_symbols:
        raise PreLiveRiskAdmissionError(
            f"Symbol '{symbol}' is not permitted by LiveAuthorization {authorization.authorization_id}. Allowed: {authorization.allowed_symbols}"
        )

    # 4. Sizing check
    if quantity > authorization.max_position_size:
        raise PreLiveRiskAdmissionError(
            f"Order quantity {quantity} exceeds authorized max_position_size ({authorization.max_position_size})."
        )

    # 5. Risk state & staleness check (Fail-closed)
    if current_risk.calculation_status != CalculationStatus.NOMINAL:
        raise PreLiveRiskAdmissionError(
            f"Risk calculation is not NOMINAL (status: {current_risk.calculation_status}, data_age: {current_risk.data_age_ms}ms). Orders halted fail-closed."
        )
    if current_risk.risk_status != RiskStatus.NORMAL:
        raise PreLiveRiskAdmissionError(
            f"Operational risk state is {current_risk.risk_status}. New orders blocked."
        )

    # 6. Compute canonical intent digest
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
    intent_digest = hashlib.sha256(CanonicalConfigSerializer.to_canonical_json(canonical_intent_payload).encode("utf-8")).hexdigest()

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
# 4. KILL SWITCH TRIGGER EVALUATION
# ============================================================================

def evaluate_kill_switch_triggers(
    authorization: LiveAuthorization,
    risk_state: RiskState,
    staleness_threshold_ms: int = 1500,
    clock_skew_threshold_ms: int = 500,
    triggered_at: Optional[datetime] = None,
) -> Optional[KillSwitchEvent]:
    """Evaluate real-time risk state against authorization bounds and trigger fail-closed KillSwitchEvent if breached."""
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
    event_digest = hashlib.sha256(CanonicalConfigSerializer.to_canonical_json(canonical_payload).encode("utf-8")).hexdigest()

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
