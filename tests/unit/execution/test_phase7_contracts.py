"""Adversarial and Invariant Unit Tests for Phase 7 Operational Contracts.

Tests systematically attack assumptions across:
- Happy Path
- Boundary Conditions
- Malformed / Tampered Inputs
- Cryptographic Signature & Revocation Enforcements
- State Machine & No Auto-Reboot Reactivation Invariants
- Dynamic Risk Staleness Fail-Closed Enforcements
- Kill Switch Trigger-to-Action Matrix
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from typing import Any, Dict, Optional, Sequence, Tuple
import pytest


from acash.core.domain.exceptions import DomainValidationError
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.admission import (
    PreLiveRiskAdmissionError,
    construct_order_intent,
    evaluate_kill_switch_triggers,
    issue_live_authorization,
    verify_validation_certificate,
)
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
    ReconciliationReport,
    RiskState,
    RiskStatus,
    TimeInForce,
    ValidationCertificate,
)
from acash.validation.schema import ValidationGateVerdict


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_digests() -> Tuple[str, str, str]:
    d1 = hashlib.sha256(b"decision_payload").hexdigest()
    d2 = hashlib.sha256(b"evidence_payload").hexdigest()
    d3 = hashlib.sha256(b"full_report_payload").hexdigest()
    return d1, d2, d3


@pytest.fixture
def trusted_keys() -> Dict[str, str]:
    return {
        "KEY_RESEARCH_GOV_V1": "super_secret_gov_key_123",
        "KEY_RISK_OFFICER_V1": "super_secret_risk_key_456",
    }


@pytest.fixture
def valid_certificate(sample_digests: Tuple[str, str, str], trusted_keys: Dict[str, str]) -> ValidationCertificate:
    d1, d2, d3 = sample_digests
    now = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    expires = now + timedelta(days=90)
    
    cert_dict = {
        "certificate_id": "CERT_TEST_ALPHA_001",
        "validation_id": "VAL_REPORT_001",
        "strategy_id": "STAT_ARB_VOL_01",
        "hypothesis_id": "HYP_VOL_PREMIUM_01",
        "verdict": ValidationGateVerdict.PASS_TRADEABLE_ALPHA.value,
        "decision_digest": d1,
        "evidence_digest": d2,
        "source_report_hash": d3,
        "issuer_id": "ACASH_RESEARCH_AUTHORITY_V1",
        "issuer_public_key_id": "KEY_RESEARCH_GOV_V1",
        "signature_algorithm": "ED25519_SHA512",
        "methodology_version": "v1.0.0",
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
    }
    payload_bytes = CanonicalConfigSerializer.to_canonical_json(cert_dict).encode("utf-8")
    sig = hashlib.sha256(payload_bytes + trusted_keys["KEY_RESEARCH_GOV_V1"].encode("utf-8")).hexdigest()
    
    return ValidationCertificate(
        certificate_id="CERT_TEST_ALPHA_001",
        validation_id="VAL_REPORT_001",
        strategy_id="STAT_ARB_VOL_01",
        hypothesis_id="HYP_VOL_PREMIUM_01",
        verdict=ValidationGateVerdict.PASS_TRADEABLE_ALPHA,
        decision_digest=d1,
        evidence_digest=d2,
        source_report_hash=d3,
        issuer_id="ACASH_RESEARCH_AUTHORITY_V1",
        issuer_public_key_id="KEY_RESEARCH_GOV_V1",
        signature_algorithm="ED25519_SHA512",
        certificate_signature=sig,
        methodology_version="v1.0.0",
        created_at=now,
        expires_at=expires,
    )


@pytest.fixture
def valid_authorization(valid_certificate: ValidationCertificate, trusted_keys: Dict[str, str]) -> LiveAuthorization:
    now = datetime(2026, 8, 30, 12, 5, 0, tzinfo=timezone.utc)
    expires = now + timedelta(days=30)
    return issue_live_authorization(
        certificate=valid_certificate,
        authorization_id="AUTH_LIVE_001",
        max_notional=Decimal("100000.00"),
        max_position_size=Decimal("25000.00"),
        max_order_rate_per_minute=60,
        max_daily_loss_notional=Decimal("2500.00"),
        max_drawdown_pct=Decimal("5.0"),
        allowed_venues=["BINANCE_FUTURES", "INTERACTIVE_BROKERS"],
        allowed_symbols=["BTC/USDT", "ETH/USDT"],
        risk_policy_version="POL_PRE_LIVE_V1",
        approver_id="RISK_OFFICER_01",
        approver_public_key_id="KEY_RISK_OFFICER_V1",
        approver_secret_key=trusted_keys["KEY_RISK_OFFICER_V1"],
        authorized_at=now,
        expires_at=expires,
        trusted_public_keys=trusted_keys,
    )


@pytest.fixture
def nominal_risk_state() -> RiskState:
    now = datetime(2026, 8, 30, 12, 10, 0, tzinfo=timezone.utc)
    return RiskState(
        timestamp=now,
        authorization_id="AUTH_LIVE_001",
        strategy_id="STAT_ARB_VOL_01",
        total_equity=Decimal("100000.00"),
        realized_pnl_today=Decimal("500.00"),
        unrealized_pnl=Decimal("200.00"),
        current_drawdown_pct=Decimal("0.5"),
        gross_exposure_notional=Decimal("20000.00"),
        net_exposure_notional=Decimal("5000.00"),
        concentration_ratio=Decimal("0.20"),
        parametric_var_95=Decimal("1500.00"),
        historical_cvar_95=Decimal("2200.00"),
        confidence_level=0.95,
        estimation_window_bars=252,
        risk_model_version="PARAMETRIC_GAUSSIAN_HURDLE_V1",
        data_timestamp=now,
        data_age_ms=120,
        calculation_status=CalculationStatus.NOMINAL,
        is_market_data_stale=False,
        is_broker_connected=True,
        is_clock_skew_detected=False,
        risk_status=RiskStatus.NORMAL,
    )


# ============================================================================
# 1. VALIDATION CERTIFICATE TESTS
# ============================================================================

def test_validation_certificate_happy_path(valid_certificate: ValidationCertificate, trusted_keys: Dict[str, str]) -> None:
    verify_validation_certificate(
        certificate=valid_certificate,
        trusted_public_keys=trusted_keys,
        current_utc=datetime(2026, 8, 30, 12, 1, 0, tzinfo=timezone.utc),
    )


def test_validation_certificate_rejects_non_pass_verdict(valid_certificate: ValidationCertificate) -> None:
    with pytest.raises(DomainValidationError, match="requires verdict PASS_TRADEABLE_ALPHA"):
        ValidationCertificate(
            **{**valid_certificate.model_dump(), "verdict": ValidationGateVerdict.REJECT_OVERFIT_DSR}
        )


def test_validation_certificate_rejects_tampered_signature(valid_certificate: ValidationCertificate, trusted_keys: Dict[str, str]) -> None:
    tampered_cert = ValidationCertificate(
        **{**valid_certificate.model_dump(), "certificate_signature": "a" * 64}
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="digital signature mismatch"):
        verify_validation_certificate(tampered_cert, trusted_public_keys=trusted_keys)


def test_validation_certificate_rejects_expired(valid_certificate: ValidationCertificate, trusted_keys: Dict[str, str]) -> None:
    past_expiration = datetime(2026, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(PreLiveRiskAdmissionError, match="has expired"):
        verify_validation_certificate(
            certificate=valid_certificate,
            trusted_public_keys=trusted_keys,
            current_utc=past_expiration,
        )


def test_validation_certificate_rejects_revoked(valid_certificate: ValidationCertificate, trusted_keys: Dict[str, str]) -> None:
    rev_event = CertificateRevocationEvent(
        revocation_id="REV_001",
        certificate_id=valid_certificate.certificate_id,
        strategy_id=valid_certificate.strategy_id,
        revoked_at=datetime(2026, 8, 30, 12, 2, 0, tzinfo=timezone.utc),
        reason="Data leak discovered in training split",
        actor="RISK_COMMITTEE_CHAIR",
        actor_public_key_id="KEY_RISK_OFFICER_V1",
        revocation_signature="b" * 64,
        revocation_digest=hashlib.sha256(b"rev_canonical").hexdigest(),
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="was revoked"):
        verify_validation_certificate(
            certificate=valid_certificate,
            revocation_events=[rev_event],
            trusted_public_keys=trusted_keys,
        )


# ============================================================================
# 2. LIVE AUTHORIZATION TESTS
# ============================================================================

def test_live_authorization_happy_path(valid_authorization: LiveAuthorization) -> None:
    assert valid_authorization.status == AuthorizationStatus.ACTIVE
    assert valid_authorization.max_notional == Decimal("100000.00")
    assert valid_authorization.max_position_size == Decimal("25000.00")
    assert "BINANCE_FUTURES" in valid_authorization.allowed_venues
    assert "BTC/USDT" in valid_authorization.allowed_symbols


def test_live_authorization_rejects_position_size_exceeding_notional(valid_certificate: ValidationCertificate, trusted_keys: Dict[str, str]) -> None:
    now = datetime(2026, 8, 30, 12, 5, 0, tzinfo=timezone.utc)
    with pytest.raises(PreLiveRiskAdmissionError, match="cannot exceed total max_notional"):
        issue_live_authorization(
            certificate=valid_certificate,
            authorization_id="AUTH_BAD_01",
            max_notional=Decimal("50000.00"),
            max_position_size=Decimal("60000.00"),  # Exceeds notional
            max_order_rate_per_minute=60,
            max_daily_loss_notional=Decimal("1000.00"),
            max_drawdown_pct=Decimal("5.0"),
            allowed_venues=["BINANCE_FUTURES"],
            allowed_symbols=["BTC/USDT"],
            risk_policy_version="POL_PRE_LIVE_V1",
            approver_id="RISK_OFFICER_01",
            approver_public_key_id="KEY_RISK_OFFICER_V1",
            approver_secret_key=trusted_keys["KEY_RISK_OFFICER_V1"],
            authorized_at=now,
            expires_at=now + timedelta(days=30),
            trusted_public_keys=trusted_keys,
        )


def test_live_authorization_rejects_negative_or_nan_limits() -> None:
    with pytest.raises(DomainValidationError, match="must be strictly positive"):
        LiveAuthorization(
            authorization_id="AUTH_TEST",
            certificate_id="CERT_TEST",
            strategy_id="STRAT_TEST",
            status=AuthorizationStatus.ACTIVE,
            authorized_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            max_notional=Decimal("-100.0"),  # Negative
            max_position_size=Decimal("10.0"),
            max_order_rate_per_minute=10,
            max_daily_loss_notional=Decimal("10.0"),
            max_drawdown_pct=Decimal("5.0"),
            allowed_venues=("BINANCE",),
            allowed_symbols=("BTC/USDT",),
            risk_policy_version="v1",
            approver_id="app",
            approver_public_key_id="key",
            authorization_signature="sig",
            authorization_digest="a" * 64,
        )


# ============================================================================
# 3. ORDER INTENT ADMISSION TESTS
# ============================================================================

def test_construct_order_intent_happy_path(valid_authorization: LiveAuthorization, nominal_risk_state: RiskState) -> None:
    signal_hash = hashlib.sha256(b"signal_event_123").hexdigest()
    intent = construct_order_intent(
        authorization=valid_authorization,
        intent_id="INTENT_001",
        venue="BINANCE_FUTURES",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("1.50"),
        current_risk=nominal_risk_state,
        signal_event_hash=signal_hash,
        created_at=datetime(2026, 8, 30, 12, 11, 0, tzinfo=timezone.utc),
        limit_price=Decimal("64000.00"),
    )
    assert intent.intent_id == "INTENT_001"
    assert intent.quantity == Decimal("1.50")
    assert len(intent.intent_digest) == 64


def test_order_intent_rejects_when_authorization_suspended(valid_authorization: LiveAuthorization, nominal_risk_state: RiskState) -> None:
    suspended_auth = LiveAuthorization(
        **{**valid_authorization.model_dump(), "status": AuthorizationStatus.SUSPENDED}
    )
    signal_hash = hashlib.sha256(b"signal").hexdigest()
    with pytest.raises(PreLiveRiskAdmissionError, match="is AuthorizationStatus.SUSPENDED, must be ACTIVE"):
        construct_order_intent(
            authorization=suspended_auth,
            intent_id="INTENT_BAD_01",
            venue="BINANCE_FUTURES",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            current_risk=nominal_risk_state,
            signal_event_hash=signal_hash,
            created_at=datetime.now(timezone.utc),
        )


def test_order_intent_rejects_unwhitelisted_venue_or_symbol(valid_authorization: LiveAuthorization, nominal_risk_state: RiskState) -> None:
    signal_hash = hashlib.sha256(b"signal").hexdigest()
    # Unallowed venue
    with pytest.raises(PreLiveRiskAdmissionError, match="Venue 'UNAPPROVED_EXCHANGE' is not permitted"):
        construct_order_intent(
            authorization=valid_authorization,
            intent_id="INTENT_BAD_02",
            venue="UNAPPROVED_EXCHANGE",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            current_risk=nominal_risk_state,
            signal_event_hash=signal_hash,
            created_at=datetime.now(timezone.utc),
        )
    # Unallowed symbol
    with pytest.raises(PreLiveRiskAdmissionError, match="Symbol 'SHIB/USDT' is not permitted"):
        construct_order_intent(
            authorization=valid_authorization,
            intent_id="INTENT_BAD_03",
            venue="BINANCE_FUTURES",
            symbol="SHIB/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            current_risk=nominal_risk_state,
            signal_event_hash=signal_hash,
            created_at=datetime.now(timezone.utc),
        )


def test_order_intent_fail_closed_on_stale_or_unknown_risk_state(valid_authorization: LiveAuthorization, nominal_risk_state: RiskState) -> None:
    signal_hash = hashlib.sha256(b"signal").hexdigest()
    stale_risk = RiskState(
        **{**nominal_risk_state.model_dump(), "calculation_status": CalculationStatus.STALE, "data_age_ms": 3500}
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="Risk calculation is not NOMINAL"):
        construct_order_intent(
            authorization=valid_authorization,
            intent_id="INTENT_BAD_04",
            venue="BINANCE_FUTURES",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            current_risk=stale_risk,
            signal_event_hash=signal_hash,
            created_at=datetime.now(timezone.utc),
        )


# ============================================================================
# 4. KILL SWITCH TRIGGER MATRIX TESTS
# ============================================================================

def test_kill_switch_triggers_on_broker_disconnect(valid_authorization: LiveAuthorization, nominal_risk_state: RiskState) -> None:
    disconnected_risk = RiskState(
        **{**nominal_risk_state.model_dump(), "is_broker_connected": False}
    )
    event = evaluate_kill_switch_triggers(valid_authorization, disconnected_risk)
    assert event is not None
    assert event.trigger_type == KillSwitchTriggerType.BROKER_DISCONNECTED
    assert event.primary_action == KillSwitchAction.HALT_NEW_ORDERS
    assert event.position_action == KillSwitchAction.FREEZE_AND_RECONCILE


def test_kill_switch_triggers_on_stale_market_data_with_hold_positions(valid_authorization: LiveAuthorization, nominal_risk_state: RiskState) -> None:
    stale_risk = RiskState(
        **{**nominal_risk_state.model_dump(), "is_market_data_stale": True, "data_age_ms": 2500}
    )
    event = evaluate_kill_switch_triggers(valid_authorization, stale_risk)
    assert event is not None
    assert event.trigger_type == KillSwitchTriggerType.STALE_MARKET_DATA
    assert event.primary_action == KillSwitchAction.CANCEL_WORKING_ORDERS
    # Invariant: Never blindly market-flatten on stale data; freeze and hold
    assert event.position_action == KillSwitchAction.FREEZE_AND_RECONCILE


def test_kill_switch_triggers_on_daily_loss_breach(valid_authorization: LiveAuthorization, nominal_risk_state: RiskState) -> None:
    loss_risk = RiskState(
        **{**nominal_risk_state.model_dump(), "realized_pnl_today": Decimal("-3000.00")}  # Limit is 2500
    )
    event = evaluate_kill_switch_triggers(valid_authorization, loss_risk)
    assert event is not None
    assert event.trigger_type == KillSwitchTriggerType.MAX_DAILY_LOSS
    assert event.position_action == KillSwitchAction.CONTROLLED_DERISK


def test_kill_switch_triggers_on_max_drawdown_breach(valid_authorization: LiveAuthorization, nominal_risk_state: RiskState) -> None:
    dd_risk = RiskState(
        **{**nominal_risk_state.model_dump(), "current_drawdown_pct": Decimal("6.2")}  # Limit is 5.0%
    )
    event = evaluate_kill_switch_triggers(valid_authorization, dd_risk)
    assert event is not None
    assert event.trigger_type == KillSwitchTriggerType.MAX_DRAWDOWN
    assert event.position_action == KillSwitchAction.EMERGENCY_FLATTEN


# ============================================================================
# 5. RECONCILIATION REPORT TESTS
# ============================================================================

def test_reconciliation_report_happy_path() -> None:
    report = ReconciliationReport(
        reconciliation_id="REC_001",
        timestamp=datetime.now(timezone.utc),
        venue="BINANCE_FUTURES",
        is_in_parity=True,
        internal_open_orders_count=3,
        broker_open_orders_count=3,
        position_discrepancies=(),
        order_discrepancies=(),
        cash_discrepancy_amount=Decimal("0.0"),
        action_taken="NOMINAL_LOGGED",
        report_digest=hashlib.sha256(b"rec_nominal").hexdigest(),
    )
    assert report.is_in_parity is True
    assert report.cash_discrepancy_amount == Decimal("0.0")
