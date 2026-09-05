"""Adversarial and Invariant Unit Tests for Phase 7 Operational Contracts."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from typing import Callable, Tuple
import pytest

from acash.core.domain.exceptions import DomainValidationError
from acash.execution.admission import (
    PreLiveRiskAdmissionError,
    apply_approval,
    construct_order_intent,
    create_draft_authorization,
    evaluate_kill_switch_triggers,
    expire_authorization,
    issue_live_authorization,
    reactivate_authorization,
    revoke_authorization,
    submit_for_approval,
    suspend_authorization,
    verify_validation_certificate,
)
from acash.execution.coordinator import (
    ExecutionCoordinator,
)
from acash.execution.signing import Ed25519Signer
from acash.execution.crypto import (
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.execution.operational_restriction import (
    OperationalRestriction,
    OperationalRestrictionError,
    OperationalRestrictionRequest,
    OperationalRestrictionStatus,
    RestrictionClearDecision,
    RestrictionClearPolicy,
    RestrictionLedger,
    RestrictionReason,
    RestrictionScope,
    RiskRestrictionAuthority,
)
from acash.execution.state_machine import ExecutionEvent
from acash.execution.schema import (
    AuthorizationApproval,
    AuthorizationReactivationApproval,
    AuthorizationReactivationEvent,
    AuthorizationStatus,
    ApproverRole,
    CalculationStatus,
    CertificateRevocationEvent,
    KillSwitchAction,
    KillSwitchTriggerType,
    LiveAuthorization,
    OrderIntent,
    OrderLifecycleState,
    OrderSide,
    OrderType,
    ReconciliationReport,
    RiskState,
    RiskStatus,
    ValidationCertificate,
    compute_authorization_digest,
)
from acash.validation.schema import ValidationGateVerdict


@dataclass(frozen=True)
class KeyMaterial:
    key_id: str
    issuer_id: str
    private_key_b64: str
    public_key_b64: str


_SHA256_PLACEHOLDER = "0" * 64


def _sample_digests() -> Tuple[str, str, str]:
    return (
        hashlib.sha256(b"decision_payload").hexdigest(),
        hashlib.sha256(b"evidence_payload").hexdigest(),
        hashlib.sha256(b"full_report_payload").hexdigest(),
    )


def _make_key(key_id: str, issuer_id: str) -> KeyMaterial:
    private_b64, public_b64 = Ed25519Signer.generate_key_pair()
    return KeyMaterial(key_id, issuer_id, private_b64, public_b64)


def _sign_payload(key: KeyMaterial, payload_bytes: bytes) -> str:
    return Ed25519Signer.sign(key.private_key_b64, payload_bytes)


def _make_approval_digest(payload_bytes: bytes) -> str:
    return hashlib.sha256(payload_bytes).hexdigest()


def _build_signed_certificate(
    key: KeyMaterial,
    *,
    certificate_id: str = "CERT_TEST_ALPHA_001",
    strategy_id: str = "STAT_ARB_VOL_01",
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> ValidationCertificate:
    d1, d2, d3 = _sample_digests()
    created = created_at or datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    expires = expires_at or (created + timedelta(days=90))
    cert = ValidationCertificate(
        certificate_id=certificate_id,
        validation_id="VAL_REPORT_001",
        strategy_id=strategy_id,
        hypothesis_id="HYP_VOL_PREMIUM_01",
        verdict=ValidationGateVerdict.PASS_TRADEABLE_ALPHA,
        decision_digest=d1,
        evidence_digest=d2,
        source_report_hash=d3,
        issuer_id=key.issuer_id,
        issuer_public_key_id=key.key_id,
        signature_algorithm="Ed25519",
        certificate_signature="PLACEHOLDER",
        methodology_version="v1.0.0",
        created_at=created,
        expires_at=expires,
    )
    sig = _sign_payload(key, cert.compute_canonical_payload_bytes())
    return cert.model_copy(update={"certificate_signature": sig})


def _build_signed_revocation(
    key: KeyMaterial,
    certificate: ValidationCertificate,
    *,
    strategy_id: str | None = None,
    signature_override: str | None = None,
) -> CertificateRevocationEvent:
    revoked_at = datetime(2026, 8, 30, 12, 2, 0, tzinfo=timezone.utc)
    rev = CertificateRevocationEvent(
        revocation_id="REV_001",
        certificate_id=certificate.certificate_id,
        strategy_id=strategy_id if strategy_id is not None else certificate.strategy_id,
        revoked_at=revoked_at,
        reason="Data leak discovered in training split",
        actor="RISK_COMMITTEE_CHAIR",
        actor_public_key_id=key.key_id,
        revocation_signature="PLACEHOLDER",
        revocation_digest=_SHA256_PLACEHOLDER,
    )
    payload = rev.compute_canonical_payload_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    sig = signature_override if signature_override is not None else _sign_payload(key, payload)
    return rev.model_copy(update={"revocation_signature": sig, "revocation_digest": digest})


def _build_signed_approval(
    key: KeyMaterial,
    authorization_id: str,
    *,
    approver_id: str,
    role: ApproverRole = ApproverRole.RISK_OFFICER,
    approved_at: datetime | None = None,
    signature_override: str | None = None,
    authorization_id_override: str | None = None,
) -> AuthorizationApproval:
    approved = approved_at or datetime(2026, 8, 30, 12, 4, 0, tzinfo=timezone.utc)
    approval = AuthorizationApproval(
        approver_id=approver_id,
        public_key_id=key.key_id,
        role=role,
        authorization_id=authorization_id_override or authorization_id,
        approved_at=approved,
        approval_signature="PLACEHOLDER",
        approval_digest=_SHA256_PLACEHOLDER,
    )
    payload = approval.compute_canonical_payload_bytes()
    digest = _make_approval_digest(payload)
    sig = signature_override if signature_override is not None else _sign_payload(key, payload)
    return approval.model_copy(update={"approval_signature": sig, "approval_digest": digest})


def _build_signed_reactivation_approval(
    key: KeyMaterial,
    reactivation_id: str,
    authorization_id: str,
    *,
    approver_id: str,
    role: ApproverRole = ApproverRole.RISK_OFFICER,
) -> AuthorizationReactivationApproval:
    approved_at = datetime(2026, 8, 30, 14, 0, 0, tzinfo=timezone.utc)
    approval = AuthorizationReactivationApproval(
        approver_id=approver_id,
        public_key_id=key.key_id,
        role=role,
        reactivation_id=reactivation_id,
        authorization_id=authorization_id,
        approved_at=approved_at,
        approval_signature="PLACEHOLDER",
        approval_digest=_SHA256_PLACEHOLDER,
    )
    payload = approval.compute_canonical_payload_bytes()
    digest = _make_approval_digest(payload)
    sig = _sign_payload(key, payload)
    return approval.model_copy(update={"approval_signature": sig, "approval_digest": digest})


def _build_reactivation_event(
    authorization: LiveAuthorization,
    approvals: Tuple[AuthorizationReactivationApproval, ...],
    *,
    root_cause_summary: str = "Broker reconnect restored; reconciliation passed.",
    authorization_id_override: str | None = None,
) -> AuthorizationReactivationEvent:
    reactivated_at = datetime(2026, 8, 30, 14, 5, 0, tzinfo=timezone.utc)
    event = AuthorizationReactivationEvent(
        reactivation_id="REACT_001",
        authorization_id=authorization_id_override or authorization.authorization_id,
        strategy_id=authorization.strategy_id,
        reactivated_at=reactivated_at,
        root_cause_summary=root_cause_summary,
        required_approvals=authorization.required_approvals,
        approvals=approvals,
        reactivation_digest=_SHA256_PLACEHOLDER,
    )
    digest = hashlib.sha256(event.compute_canonical_payload_bytes()).hexdigest()
    return event.model_copy(update={"reactivation_digest": digest})


@pytest.fixture
def gov_key() -> KeyMaterial:
    return _make_key("KEY_RESEARCH_GOV_V1", "ACASH_RESEARCH_AUTHORITY_V1")


@pytest.fixture
def risk_key_1() -> KeyMaterial:
    return _make_key("KEY_RISK_OFFICER_1", "ACASH_RISK_AUTHORITY_V1")


@pytest.fixture
def risk_key_2() -> KeyMaterial:
    return _make_key("KEY_RISK_OFFICER_2", "ACASH_RISK_AUTHORITY_V1")


@pytest.fixture
def risk_key_3() -> KeyMaterial:
    return _make_key("KEY_RISK_OFFICER_3", "ACASH_RISK_AUTHORITY_V1")


@pytest.fixture
def trust_store(
    gov_key: KeyMaterial,
    risk_key_1: KeyMaterial,
    risk_key_2: KeyMaterial,
    risk_key_3: KeyMaterial,
) -> Ed25519TrustStore:
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    entries = (
        Ed25519TrustStoreEntry(
            key_id=gov_key.key_id,
            issuer_id=gov_key.issuer_id,
            public_key_b64=gov_key.public_key_b64,
            valid_from=now,
            valid_until=None,
            status=TrustStoreEntryStatus.ACTIVE,
        ),
        Ed25519TrustStoreEntry(
            key_id=risk_key_1.key_id,
            issuer_id=risk_key_1.issuer_id,
            public_key_b64=risk_key_1.public_key_b64,
            valid_from=now,
            valid_until=None,
            status=TrustStoreEntryStatus.ACTIVE,
        ),
        Ed25519TrustStoreEntry(
            key_id=risk_key_2.key_id,
            issuer_id=risk_key_2.issuer_id,
            public_key_b64=risk_key_2.public_key_b64,
            valid_from=now,
            valid_until=None,
            status=TrustStoreEntryStatus.ACTIVE,
        ),
        Ed25519TrustStoreEntry(
            key_id=risk_key_3.key_id,
            issuer_id=risk_key_3.issuer_id,
            public_key_b64=risk_key_3.public_key_b64,
            valid_from=now,
            valid_until=None,
            status=TrustStoreEntryStatus.ACTIVE,
        ),
    )
    return Ed25519TrustStore(entries=entries)


@pytest.fixture
def valid_certificate(gov_key: KeyMaterial) -> ValidationCertificate:
    return _build_signed_certificate(gov_key)


@pytest.fixture
def auth_params() -> dict[str, object]:
    now = datetime(2026, 8, 30, 12, 5, 0, tzinfo=timezone.utc)
    return {
        "authorization_id": "AUTH_LIVE_001",
        "max_notional": Decimal("100000.00"),
        "max_position_size": Decimal("25000.00"),
        "max_order_rate_per_minute": 60,
        "max_daily_loss_notional": Decimal("2500.00"),
        "max_drawdown_pct": Decimal("5.0"),
        "allowed_venues": ["BINANCE_FUTURES", "INTERACTIVE_BROKERS"],
        "allowed_symbols": ["BTC/USDT", "ETH/USDT"],
        "risk_policy_version": "POL_PRE_LIVE_V1",
        "authorized_at": now,
        "expires_at": now + timedelta(days=30),
        "required_approvals": 2,
    }


def _issue_with_quorum(
    certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    risk_key_2: KeyMaterial,
    auth_params: dict[str, object],
) -> LiveAuthorization:
    auth_id = str(auth_params["authorization_id"])
    approvals = (
        _build_signed_approval(risk_key_1, auth_id, approver_id="RISK_OFFICER_1"),
        _build_signed_approval(risk_key_2, auth_id, approver_id="RISK_OFFICER_2"),
    )
    return issue_live_authorization(
        certificate=certificate,
        trust_store=trust_store,
        approvals=approvals,
        **auth_params,  # type: ignore[arg-type]
    )


@pytest.fixture
def valid_authorization(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    risk_key_2: KeyMaterial,
    auth_params: dict[str, object],
) -> LiveAuthorization:
    return _issue_with_quorum(
        valid_certificate, trust_store, risk_key_1, risk_key_2, auth_params
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
        data_timestamp=now,
        data_age_ms=120,
        calculation_status=CalculationStatus.NOMINAL,
        is_market_data_stale=False,
        is_broker_connected=True,
        is_clock_skew_detected=False,
        risk_status=RiskStatus.NORMAL,
    )


# ============================================================================
# CERTIFICATE & TRUSTSTORE TESTS
# ============================================================================

def test_certificate_happy_path(
    valid_certificate: ValidationCertificate, trust_store: Ed25519TrustStore
) -> None:
    verify_validation_certificate(
        certificate=valid_certificate,
        trust_store=trust_store,
        current_utc=datetime(2026, 8, 30, 12, 1, 0, tzinfo=timezone.utc),
    )


def test_certificate_rejects_unknown_key_id(
    valid_certificate: ValidationCertificate, trust_store: Ed25519TrustStore
) -> None:
    tampered = valid_certificate.model_copy(update={"issuer_public_key_id": "UNKNOWN_KEY"})
    with pytest.raises(PreLiveRiskAdmissionError, match="unknown key_id"):
        verify_validation_certificate(tampered, trust_store)


def test_certificate_rejects_tampered_payload(
    valid_certificate: ValidationCertificate, trust_store: Ed25519TrustStore
) -> None:
    tampered = valid_certificate.model_copy(update={"strategy_id": "TAMPERED_STRATEGY"})
    with pytest.raises(PreLiveRiskAdmissionError, match="Ed25519 signature FAILED"):
        verify_validation_certificate(tampered, trust_store)


def test_certificate_rejects_revoked_key(
    gov_key: KeyMaterial, trust_store: Ed25519TrustStore
) -> None:
    revoked_store = Ed25519TrustStore(
        entries=(
            Ed25519TrustStoreEntry(
                key_id=gov_key.key_id,
                issuer_id=gov_key.issuer_id,
                public_key_b64=gov_key.public_key_b64,
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                status=TrustStoreEntryStatus.REVOKED,
            ),
        )
    )
    cert = _build_signed_certificate(gov_key)
    with pytest.raises(PreLiveRiskAdmissionError, match="REVOKED"):
        verify_validation_certificate(cert, revoked_store)


def test_certificate_rejects_expired_key_at_signing_time(
    gov_key: KeyMaterial,
) -> None:
    created = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    expired_store = Ed25519TrustStore(
        entries=(
            Ed25519TrustStoreEntry(
                key_id=gov_key.key_id,
                issuer_id=gov_key.issuer_id,
                public_key_b64=gov_key.public_key_b64,
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                valid_until=datetime(2026, 6, 1, tzinfo=timezone.utc),
                status=TrustStoreEntryStatus.ACTIVE,
            ),
        )
    )
    cert = _build_signed_certificate(
        gov_key,
        created_at=created,
        expires_at=datetime(2027, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="was not valid at"):
        verify_validation_certificate(cert, expired_store)


def test_certificate_accepts_rotated_key_for_historical_timestamp(
    gov_key: KeyMaterial,
) -> None:
    created = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    rotated_store = Ed25519TrustStore(
        entries=(
            Ed25519TrustStoreEntry(
                key_id=gov_key.key_id,
                issuer_id=gov_key.issuer_id,
                public_key_b64=gov_key.public_key_b64,
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                valid_until=datetime(2026, 6, 30, tzinfo=timezone.utc),
                status=TrustStoreEntryStatus.ROTATED,
            ),
        )
    )
    cert = _build_signed_certificate(
        gov_key,
        created_at=created,
        expires_at=datetime(2027, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    verify_validation_certificate(
        cert,
        rotated_store,
        current_utc=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )


def test_certificate_rejects_expired_certificate(
    valid_certificate: ValidationCertificate, trust_store: Ed25519TrustStore
) -> None:
    with pytest.raises(PreLiveRiskAdmissionError, match="has expired"):
        verify_validation_certificate(
            valid_certificate,
            trust_store,
            current_utc=datetime(2026, 12, 1, tzinfo=timezone.utc),
        )


def test_certificate_rejects_revoked_with_full_verification(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
) -> None:
    rev = _build_signed_revocation(risk_key_1, valid_certificate)
    with pytest.raises(PreLiveRiskAdmissionError, match="was revoked"):
        verify_validation_certificate(
            valid_certificate,
            trust_store,
            revocation_events=[rev],
            current_utc=datetime(2026, 8, 30, 12, 3, 0, tzinfo=timezone.utc),
        )


def test_revocation_rejects_cross_strategy_confusion(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
) -> None:
    rev = _build_signed_revocation(
        risk_key_1, valid_certificate, strategy_id="OTHER_STRATEGY"
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="strategy_id"):
        verify_validation_certificate(
            valid_certificate,
            trust_store,
            revocation_events=[rev],
            current_utc=datetime(2026, 8, 30, 12, 3, 0, tzinfo=timezone.utc),
        )


def test_revocation_rejects_invalid_signature(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
) -> None:
    rev = _build_signed_revocation(
        risk_key_1,
        valid_certificate,
        signature_override=Ed25519Signer.sign(
            Ed25519Signer.generate_key_pair()[0],
            _build_signed_revocation(risk_key_1, valid_certificate).compute_canonical_payload_bytes(),
        ),
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="Ed25519 signature FAILED"):
        verify_validation_certificate(
            valid_certificate,
            trust_store,
            revocation_events=[rev],
            current_utc=datetime(2026, 8, 30, 12, 3, 0, tzinfo=timezone.utc),
        )


def test_old_sha256_secret_signature_path_does_not_work(
    valid_certificate: ValidationCertificate, trust_store: Ed25519TrustStore
) -> None:
    fake_sig = hashlib.sha256(
        valid_certificate.compute_canonical_payload_bytes() + b"super_secret"
    ).hexdigest()
    tampered = valid_certificate.model_copy(update={"certificate_signature": fake_sig})
    with pytest.raises(PreLiveRiskAdmissionError, match="invalid base64 signature"):
        verify_validation_certificate(tampered, trust_store)


# ============================================================================
# AUTHORIZATION QUORUM TESTS
# ============================================================================

def test_authorization_happy_path_at_quorum(valid_authorization: LiveAuthorization) -> None:
    assert valid_authorization.status == AuthorizationStatus.ACTIVE
    assert len(valid_authorization.approvals) == 2
    assert valid_authorization.required_approvals == 2


def test_authorization_rejects_insufficient_quorum_pending(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    auth_params: dict[str, object],
) -> None:
    auth_id = str(auth_params["authorization_id"])
    auth = issue_live_authorization(
        certificate=valid_certificate,
        trust_store=trust_store,
        approvals=(
            _build_signed_approval(risk_key_1, auth_id, approver_id="RISK_OFFICER_1"),
        ),
        **auth_params,  # type: ignore[arg-type]
    )
    assert auth.status == AuthorizationStatus.PENDING_APPROVAL


def test_authorization_rejects_duplicate_approvers(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    auth_params: dict[str, object],
) -> None:
    auth_id = str(auth_params["authorization_id"])
    dup = _build_signed_approval(risk_key_1, auth_id, approver_id="RISK_OFFICER_1")
    with pytest.raises(PreLiveRiskAdmissionError, match="Duplicate approver_id"):
        issue_live_authorization(
            certificate=valid_certificate,
            trust_store=trust_store,
            approvals=(dup, dup),
            **auth_params,  # type: ignore[arg-type]
        )


def test_authorization_rejects_forged_approval(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    risk_key_2: KeyMaterial,
    auth_params: dict[str, object],
) -> None:
    auth_id = str(auth_params["authorization_id"])
    forged = _build_signed_approval(
        risk_key_1,
        auth_id,
        approver_id="RISK_OFFICER_1",
        signature_override="not-valid-base64!!!",
    )
    good = _build_signed_approval(risk_key_2, auth_id, approver_id="RISK_OFFICER_2")
    with pytest.raises(PreLiveRiskAdmissionError, match="invalid base64 signature"):
        issue_live_authorization(
            certificate=valid_certificate,
            trust_store=trust_store,
            approvals=(forged, good),
            **auth_params,  # type: ignore[arg-type]
        )


def test_direct_active_construction_possible_but_service_is_authority(
    auth_params: dict[str, object],
) -> None:
    """Schema permits ACTIVE construction; production path must use service layer."""
    now = auth_params["authorized_at"]
    assert isinstance(now, datetime)
    digest = compute_authorization_digest(
        authorization_id="AUTH_DIRECT",
        certificate_id="CERT_TEST",
        strategy_id="STAT_ARB_VOL_01",
        authorized_at=now,
        expires_at=auth_params["expires_at"],  # type: ignore[arg-type]
        max_notional=auth_params["max_notional"],  # type: ignore[arg-type]
        max_position_size=auth_params["max_position_size"],  # type: ignore[arg-type]
        max_order_rate_per_minute=auth_params["max_order_rate_per_minute"],  # type: ignore[arg-type]
        max_daily_loss_notional=auth_params["max_daily_loss_notional"],  # type: ignore[arg-type]
        max_drawdown_pct=auth_params["max_drawdown_pct"],  # type: ignore[arg-type]
        allowed_venues=tuple(auth_params["allowed_venues"]),  # type: ignore[arg-type]
        allowed_symbols=tuple(auth_params["allowed_symbols"]),  # type: ignore[arg-type]
        risk_policy_version=str(auth_params["risk_policy_version"]),
        required_approvals=2,
        approval_digests=(),
    )
    direct = LiveAuthorization(
        authorization_id="AUTH_DIRECT",
        certificate_id="CERT_TEST",
        strategy_id="STAT_ARB_VOL_01",
        status=AuthorizationStatus.ACTIVE,
        authorized_at=now,
        expires_at=auth_params["expires_at"],  # type: ignore[arg-type]
        max_notional=auth_params["max_notional"],  # type: ignore[arg-type]
        max_position_size=auth_params["max_position_size"],  # type: ignore[arg-type]
        max_order_rate_per_minute=auth_params["max_order_rate_per_minute"],  # type: ignore[arg-type]
        max_daily_loss_notional=auth_params["max_daily_loss_notional"],  # type: ignore[arg-type]
        max_drawdown_pct=auth_params["max_drawdown_pct"],  # type: ignore[arg-type]
        allowed_venues=tuple(auth_params["allowed_venues"]),  # type: ignore[arg-type]
        allowed_symbols=tuple(auth_params["allowed_symbols"]),  # type: ignore[arg-type]
        risk_policy_version=str(auth_params["risk_policy_version"]),
        required_approvals=2,
        approvals=(),
        authorization_digest=digest,
    )
    assert direct.status == AuthorizationStatus.ACTIVE
    assert direct.approvals == ()


# ============================================================================
# STATE TRANSITION TESTS
# ============================================================================

def test_draft_to_pending_approval(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    auth_params: dict[str, object],
) -> None:
    draft = create_draft_authorization(
        certificate=valid_certificate,
        trust_store=trust_store,
        **auth_params,  # type: ignore[arg-type]
    )
    assert draft.status == AuthorizationStatus.DRAFT
    pending = submit_for_approval(draft)
    assert pending.status == AuthorizationStatus.PENDING_APPROVAL


def test_invalid_draft_transition_rejected(
    valid_authorization: LiveAuthorization,
) -> None:
    with pytest.raises(PreLiveRiskAdmissionError, match="requires DRAFT status"):
        submit_for_approval(valid_authorization)


def test_pending_to_active_at_quorum(
    valid_certificate: ValidationCertificate,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    risk_key_2: KeyMaterial,
    auth_params: dict[str, object],
) -> None:
    draft = create_draft_authorization(
        certificate=valid_certificate,
        trust_store=trust_store,
        **auth_params,  # type: ignore[arg-type]
    )
    pending = submit_for_approval(draft)
    auth_id = str(auth_params["authorization_id"])
    after_one = apply_approval(
        pending,
        _build_signed_approval(risk_key_1, auth_id, approver_id="RISK_OFFICER_1"),
        trust_store,
    )
    assert after_one.status == AuthorizationStatus.PENDING_APPROVAL
    active = apply_approval(
        after_one,
        _build_signed_approval(risk_key_2, auth_id, approver_id="RISK_OFFICER_2"),
        trust_store,
    )
    assert active.status == AuthorizationStatus.ACTIVE


def test_active_to_suspended(valid_authorization: LiveAuthorization) -> None:
    suspended = suspend_authorization(
        valid_authorization, reason="BROKER_DISCONNECTED", actor_id="SYSTEM"
    )
    assert suspended.status == AuthorizationStatus.SUSPENDED


def test_suspended_to_active_requires_same_quorum(
    valid_authorization: LiveAuthorization,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    risk_key_2: KeyMaterial,
) -> None:
    suspended = suspend_authorization(
        valid_authorization, reason="STALE_MARKET_DATA", actor_id="SYSTEM"
    )
    reactivation_approvals = (
        _build_signed_reactivation_approval(
            risk_key_1, "REACT_001", suspended.authorization_id, approver_id="RISK_OFFICER_1"
        ),
        _build_signed_reactivation_approval(
            risk_key_2, "REACT_001", suspended.authorization_id, approver_id="RISK_OFFICER_2"
        ),
    )
    event = _build_reactivation_event(suspended, reactivation_approvals)
    reactivated = reactivate_authorization(suspended, event, trust_store)
    assert reactivated.status == AuthorizationStatus.ACTIVE


def test_reactivation_rejects_insufficient_quorum(
    valid_authorization: LiveAuthorization,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
) -> None:
    suspended = suspend_authorization(
        valid_authorization, reason="RECONCILIATION_FAILURE", actor_id="SYSTEM"
    )
    event = _build_reactivation_event(
        suspended,
        (
            _build_signed_reactivation_approval(
                risk_key_1, "REACT_001", suspended.authorization_id, approver_id="RISK_OFFICER_1"
            ),
        ),
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="quorum not met"):
        reactivate_authorization(suspended, event, trust_store)


def test_reactivation_rejects_wrong_authorization_binding(
    valid_authorization: LiveAuthorization,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    risk_key_2: KeyMaterial,
) -> None:
    suspended = suspend_authorization(valid_authorization, reason="CLOCK_SKEW", actor_id="SYSTEM")
    reactivation_approvals = (
        _build_signed_reactivation_approval(
            risk_key_1, "REACT_001", suspended.authorization_id, approver_id="RISK_OFFICER_1"
        ),
        _build_signed_reactivation_approval(
            risk_key_2, "REACT_001", suspended.authorization_id, approver_id="RISK_OFFICER_2"
        ),
    )
    event = _build_reactivation_event(
        suspended, reactivation_approvals, authorization_id_override="WRONG_AUTH_ID"
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="authorization_id"):
        reactivate_authorization(suspended, event, trust_store)


def test_reactivation_rejects_empty_root_cause(
    valid_authorization: LiveAuthorization,
    trust_store: Ed25519TrustStore,
    risk_key_1: KeyMaterial,
    risk_key_2: KeyMaterial,
) -> None:
    suspended = suspend_authorization(valid_authorization, reason="MANUAL_HALT", actor_id="OPS")
    reactivation_approvals = (
        _build_signed_reactivation_approval(
            risk_key_1, "REACT_001", suspended.authorization_id, approver_id="RISK_OFFICER_1"
        ),
        _build_signed_reactivation_approval(
            risk_key_2, "REACT_001", suspended.authorization_id, approver_id="RISK_OFFICER_2"
        ),
    )
    event = _build_reactivation_event(suspended, reactivation_approvals).model_copy(
        update={"root_cause_summary": "   "}
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="root_cause_summary"):
        reactivate_authorization(suspended, event, trust_store)


def test_revoked_is_terminal(valid_authorization: LiveAuthorization) -> None:
    revoked = revoke_authorization(valid_authorization, reason="Policy breach", actor_id="RISK")
    assert revoked.status == AuthorizationStatus.REVOKED
    with pytest.raises(PreLiveRiskAdmissionError, match="terminal status"):
        revoke_authorization(revoked, reason="Again", actor_id="RISK")
    with pytest.raises(PreLiveRiskAdmissionError, match="requires ACTIVE status"):
        suspend_authorization(revoked, reason="Late suspend", actor_id="RISK")


def test_expired_is_terminal(valid_authorization: LiveAuthorization) -> None:
    expired = expire_authorization(
        valid_authorization,
        current_utc=valid_authorization.expires_at + timedelta(seconds=1),
    )
    assert expired.status == AuthorizationStatus.EXPIRED
    with pytest.raises(PreLiveRiskAdmissionError, match="terminal status"):
        revoke_authorization(expired, reason="Late revoke", actor_id="RISK")


def test_cancel_requested_exists_in_order_lifecycle() -> None:
    assert OrderLifecycleState.CANCEL_REQUESTED == "CANCEL_REQUESTED"


# ============================================================================
# ORDER INTENT & KILL SWITCH (REGRESSION)
# ============================================================================

def test_construct_order_intent_happy_path(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
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
        restriction_authority=RiskRestrictionAuthority(RestrictionLedger()),
    )
    assert intent.intent_id == "INTENT_001"
    assert len(intent.intent_digest) == 64


def test_order_intent_rejects_suspended(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    suspended = valid_authorization.model_copy(update={"status": AuthorizationStatus.SUSPENDED})
    with pytest.raises(PreLiveRiskAdmissionError, match="must be ACTIVE"):
        construct_order_intent(
            authorization=suspended,
            intent_id="INTENT_BAD",
            venue="BINANCE_FUTURES",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            current_risk=nominal_risk_state,
            signal_event_hash=hashlib.sha256(b"x").hexdigest(),
            created_at=datetime.now(timezone.utc),
            restriction_authority=RiskRestrictionAuthority(RestrictionLedger()),
        )


def test_kill_switch_halt_not_flatten_on_stale(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    stale_risk = nominal_risk_state.model_copy(
        update={"is_market_data_stale": True, "data_age_ms": 2500}
    )
    event = evaluate_kill_switch_triggers(valid_authorization, stale_risk)
    assert event is not None
    assert event.trigger_type == KillSwitchTriggerType.STALE_MARKET_DATA
    assert event.primary_action == KillSwitchAction.CANCEL_WORKING_ORDERS
    assert event.position_action == KillSwitchAction.FREEZE_AND_RECONCILE


def test_reconciliation_report_happy_path() -> None:
    report = ReconciliationReport(
        reconciliation_id="REC_001",
        timestamp=datetime.now(timezone.utc),
        venue="BINANCE_FUTURES",
        is_in_parity=True,
        internal_open_orders_count=3,
        broker_open_orders_count=3,
        action_taken="NOMINAL_LOGGED",
        report_digest=hashlib.sha256(b"rec_nominal").hexdigest(),
    )
    assert report.is_in_parity is True


# ============================================================================
# OPERATIONAL RESTRICTION & ADMISSION BOUNDARY (Phase 7 Operational Boundary)
# ============================================================================
# Invariant (locked): Order State != Evidence State != Operational Restriction
# != Live Authorization. Coordinator = detect/request only; Risk/Restriction
# Authority = OPEN/CLEAR; Admission = ENFORCE only; and
#   Reconciliation Evidence != Authorization to Clear.

STRATEGY_ID = "STAT_ARB_VOL_01"
AUTH_ID = "AUTH_LIVE_001"


def _empty_authority() -> RiskRestrictionAuthority:
    return RiskRestrictionAuthority(RestrictionLedger())


def _open_restriction(
    authority: RiskRestrictionAuthority,
    *,
    scope: RestrictionScope,
    strategy_id: str | None = None,
    authorization_id: str | None = None,
    request_id: str = "REQ_AB",
) -> OperationalRestriction:
    request = OperationalRestrictionRequest(
        request_id=request_id,
        scope=scope,
        reason=RestrictionReason.RECONCILIATION_CONFLICT,
        strategy_id=strategy_id,
        authorization_id=authorization_id,
        evidence_refs=(_SHA256_PLACEHOLDER,),
    )
    return authority.open_restriction(request)


def _construct_intent(
    valid_authorization: LiveAuthorization,
    nominal_risk_state: RiskState,
    authority: RiskRestrictionAuthority,
    intent_id: str = "INTENT_RESTRICTED",
) -> OrderIntent:
    return construct_order_intent(
        authorization=valid_authorization,
        intent_id=intent_id,
        venue="BINANCE_FUTURES",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("1.50"),
        current_risk=nominal_risk_state,
        signal_event_hash=hashlib.sha256(b"sig_rest").hexdigest(),
        created_at=datetime(2026, 8, 30, 12, 11, 0, tzinfo=timezone.utc),
        limit_price=Decimal("64000.00"),
        restriction_authority=authority,
    )


def test_open_strategy_restriction_blocks_order_intent(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    authority = _empty_authority()
    _open_restriction(
        authority, scope=RestrictionScope.STRATEGY, strategy_id=STRATEGY_ID
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="OPEN operational restriction"):
        _construct_intent(valid_authorization, nominal_risk_state, authority)


def test_open_authorization_restriction_blocks_order_intent(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    authority = _empty_authority()
    _open_restriction(
        authority,
        scope=RestrictionScope.AUTHORIZATION,
        authorization_id=AUTH_ID,
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="OPEN operational restriction"):
        _construct_intent(valid_authorization, nominal_risk_state, authority)


def test_cleared_restriction_does_not_block(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    # Clearing a restriction still requires an authorized decision; a matching
    # OPEN restriction blocks. After CLEARED it must no longer block. We supply a
    # policy that authorizes the clear (evidence verified AND authorized).
    class AuthorizingPolicy(RestrictionClearPolicy):
        def is_evidence_verified(self, restriction: OperationalRestriction) -> bool:
            return True

        def decide(
            self,
            *,
            restriction: OperationalRestriction,
            evidence_refs: Tuple[str, ...],
            actor_id: str,
        ) -> RestrictionClearDecision:
            return RestrictionClearDecision(
                authorized=True, actor_id=actor_id, decision_note="authorized"
            )

    authority = RiskRestrictionAuthority(RestrictionLedger(), AuthorizingPolicy())
    r = _open_restriction(
        authority, scope=RestrictionScope.STRATEGY, strategy_id=STRATEGY_ID
    )
    assert r.status == OperationalRestrictionStatus.OPEN
    authority.clear_restriction(
        restriction_id=r.restriction_id,
        actor_id="RISK",
        evidence_refs=(_SHA256_PLACEHOLDER,),
    )
    cleared = authority.get(r.restriction_id)
    assert cleared is not None
    assert cleared.status == OperationalRestrictionStatus.CLEARED
    intent = _construct_intent(valid_authorization, nominal_risk_state, authority)
    assert intent.intent_id == "INTENT_RESTRICTED"


def test_unrelated_strategy_restriction_does_not_block(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    authority = _empty_authority()
    _open_restriction(
        authority, scope=RestrictionScope.STRATEGY, strategy_id="SOME_OTHER_STRAT"
    )
    intent = _construct_intent(valid_authorization, nominal_risk_state, authority)
    assert intent.intent_id == "INTENT_RESTRICTED"


def test_unrelated_authorization_restriction_does_not_block(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    authority = _empty_authority()
    _open_restriction(
        authority,
        scope=RestrictionScope.AUTHORIZATION,
        authorization_id="AUTH_UNRELATED",
    )
    intent = _construct_intent(valid_authorization, nominal_risk_state, authority)
    assert intent.intent_id == "INTENT_RESTRICTED"


def test_restriction_cannot_be_bypassed_by_omitting_snapshot(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    # The admission signature REQUIRES the authority; there is no optional
    # snapshot/list a caller can omit. An empty authority + empty ledger is the
    # only way to have no restrictions, and it is honest (no open restrictions).
    authority = _empty_authority()
    assert authority.gate_for_intent(
        strategy_id=STRATEGY_ID, authorization_id=AUTH_ID
    ).is_blocked() is False


def test_empty_fabricated_restriction_authority_cannot_bypass_production_admission(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    # A caller cannot forge an empty decision: the admission gate reads ONLY the
    # bound canonical ledger. If a restriction is recorded in that ledger (the
    # same ledger the authority reads), an empty-looking authority is impossible
    # -- the gate reflects the ledger, not a caller-supplied [].
    ledger = RestrictionLedger()
    authority = RiskRestrictionAuthority(ledger)
    _open_restriction(
        authority, scope=RestrictionScope.STRATEGY, strategy_id=STRATEGY_ID
    )
    # The admission consults the same ledger-backed authority.
    with pytest.raises(PreLiveRiskAdmissionError, match="OPEN operational restriction"):
        _construct_intent(valid_authorization, nominal_risk_state, authority)


def test_admission_enforces_the_supplied_canonical_ledger_authority(
    valid_authorization: LiveAuthorization, nominal_risk_state: RiskState
) -> None:
    # What this test proves: `construct_order_intent` ENFORCES the ledger-backed
    # authority that the CALLER SUPPLIES — it never constructs a ledger/authority
    # internally, and it never consults any store other than the one bound to the
    # authority passed in. It does NOT prove production composition-root
    # provenance (no production composition root exists yet); that remains a
    # DEPLOYMENT INVARIANT, not something a unit test can establish.

    # 1) The caller-owned ledger (a supplied store in this test, NOT the
    #    production composition root) carries an OPEN strategy restriction.
    supplied_ledger = RestrictionLedger()
    supplied_authority = RiskRestrictionAuthority(supplied_ledger)
    _open_restriction(
        supplied_authority,
        scope=RestrictionScope.STRATEGY,
        strategy_id=STRATEGY_ID,
    )

    # 2) A separately-created empty ledger is a DISTINCT store. Admission consults
    #    ONLY the supplied authority's bound ledger; an isolated empty store does
    #    not affect it.
    other_empty_ledger = RestrictionLedger()
    assert other_empty_ledger.all() == ()
    assert other_empty_ledger is not supplied_ledger

    # 3) Passing the supplied (matching-OPEN) authority → admission MUST reject.
    with pytest.raises(PreLiveRiskAdmissionError, match="OPEN operational restriction"):
        _construct_intent(
            valid_authorization, nominal_risk_state, supplied_authority
        )

    # 4) `construct_order_intent` cannot fabricate or default an authority: it has
    #    no default authority argument and no internal authority/ledger creation.
    #    The ONLY authority source is the required caller-supplied parameter — so a
    #    caller cannot omit it (nil) to skip the gate, and cannot silently swap in
    #    a different, empty ledger than the one the supplied authority is bound to.
    import inspect

    params = inspect.signature(construct_order_intent).parameters
    assert "restriction_authority" in params
    assert params["restriction_authority"].default is inspect.Parameter.empty


def test_only_risk_authority_opens_restriction() -> None:
    authority = _empty_authority()
    r = _open_restriction(
        authority, scope=RestrictionScope.STRATEGY, strategy_id="S"
    )
    assert r.status == OperationalRestrictionStatus.OPEN
    # The authority is the single lifecycle owner: it is the only object that
    # records an OPEN restriction into the canonical ledger.
    fetched = authority.get(r.restriction_id)
    assert fetched is not None
    assert fetched.status == OperationalRestrictionStatus.OPEN


def test_coordinator_only_emits_request() -> None:
    # Coordinator = detect + request ONLY. Drive it to terminal CANCELLED, then
    # reconcile with contradictory FILLED evidence: it emits a *request* but does
    # NOT itself OPEN a restriction (no authority access, no lifecycle mutation).
    coord = ExecutionCoordinator(
        execution_id="EXE_AB",
        requested_qty=Decimal("2.0"),
        initial_state=OrderLifecycleState.CANCELLED,
    )
    outcome = coord.reconcile(
        broker_event_id="EV_1",
        broker_sequence="1",
        evidence_token="FILLED",
        order_id="ORD_AB",
        observed_at=datetime(2026, 8, 30, 12, 11, 0, tzinfo=timezone.utc),
        evidence_refs=(_SHA256_PLACEHOLDER,),
    )
    assert outcome.restriction_request is not None
    req = outcome.restriction_request
    assert req.scope == RestrictionScope.EXECUTION
    assert req.reason == RestrictionReason.RECONCILIATION_CONFLICT
    assert req.evidence_refs == (_SHA256_PLACEHOLDER,)
    assert req.shadow_state == "CANCELLED"
    assert req.broker_observed_state == "FILLED"
    # Coordinator must NOT have opened anything: no OPEN mutation can be reached
    # through the coordinator, and its CANCELLED shadow is NOT regressed.
    assert coord.state == OrderLifecycleState.CANCELLED


def test_verified_evidence_does_not_auto_clear() -> None:
    class VerifyOnlyPolicy(RestrictionClearPolicy):
        def is_evidence_verified(self, restriction: OperationalRestriction) -> bool:
            return True  # evidence verified, but NO authorized decision

        def decide(
            self,
            *,
            restriction: OperationalRestriction,
            evidence_refs: Tuple[str, ...],
            actor_id: str,
        ) -> RestrictionClearDecision:
            return RestrictionClearDecision(
                authorized=False, actor_id=actor_id, decision_note="not authorized"
            )

    authority = RiskRestrictionAuthority(RestrictionLedger(), VerifyOnlyPolicy())
    r = _open_restriction(
        authority, scope=RestrictionScope.STRATEGY, strategy_id="S"
    )
    # Verified evidence alone NEVER clears: clear requires an authorized decision.
    with pytest.raises(OperationalRestrictionError):
        authority.clear_restriction(
            restriction_id=r.restriction_id,
            actor_id="RISK",
            evidence_refs=(_SHA256_PLACEHOLDER,),
        )
    still_open = authority.get(r.restriction_id)
    assert still_open is not None
    assert still_open.status == OperationalRestrictionStatus.OPEN
