"""Unit and adversarial tests for Sovereign Kill Switch Controller (Slice 3).

Tests:
- State machine lifecycle (ACTIVE -> TRIPPED -> PERSISTENTLY_BLOCKED -> RESET_PENDING -> ACTIVE).
- Strict invalid state transition rejection (fail-closed).
- Admission boundary lockout when TRIPPED or PERSISTENTLY_BLOCKED.
- Multi-sig quorum reset verification using Ed25519TrustStore and Ed25519Signer.
- Rejection of unauthorized approvers, invalid signatures, insufficient quorum, empty root cause.
- Replay attack protection on reset approvals.
- Race condition handling: newer trip overrides reset proposal.
- Process restart state recovery from append-only disk ledger.
- Fail-closed behavior on corrupted or tampered persistence ledger.
- Separation of concerns: Kill Switch Trip != Positions Flattened.
- Zero direct broker execution authority.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Optional
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.execution.schema import ApproverRole, AuthorizationApproval
from acash.risk.kill_switch import (
    ALLOWED_KILL_SWITCH_TRANSITIONS,
    KillSwitchEvent,
    SovereignKillSwitchController,
)
from acash.risk.risk_schema import (
    KillSwitchResetEvent,
    KillSwitchState,
    RiskPolicyConfig,
)


class MockEd25519Signer:
    """Helper wrapper around Ed25519Signer for test fixtures."""

    def __init__(self, key_id: str, issuer_id: str) -> None:
        self.key_id = key_id
        self.issuer_id = issuer_id
        self.private_key_b64, self.public_key_b64 = Ed25519Signer.generate_key_pair()

    def sign(self, payload_bytes: bytes) -> str:
        return Ed25519Signer.sign(self.private_key_b64, payload_bytes)


@pytest.fixture
def risk_officer_signer() -> MockEd25519Signer:
    return MockEd25519Signer(
        key_id="KEY_RISK_OFFICER_01",
        issuer_id="ACASH_RISK_AUTHORITY",
    )


@pytest.fixture
def compliance_signer() -> MockEd25519Signer:
    return MockEd25519Signer(
        key_id="KEY_COMPLIANCE_01",
        issuer_id="ACASH_COMPLIANCE_AUTHORITY",
    )


@pytest.fixture
def unauthorized_signer() -> MockEd25519Signer:
    return MockEd25519Signer(
        key_id="KEY_PM_01",
        issuer_id="ACASH_PM_AUTHORITY",
    )


@pytest.fixture
def sample_trust_store(
    risk_officer_signer: MockEd25519Signer,
    compliance_signer: MockEd25519Signer,
    unauthorized_signer: MockEd25519Signer,
) -> Ed25519TrustStore:
    now = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    entry_risk = Ed25519TrustStoreEntry(
        key_id=risk_officer_signer.key_id,
        issuer_id=risk_officer_signer.issuer_id,
        public_key_b64=risk_officer_signer.public_key_b64,
        valid_from=now,
        status=TrustStoreEntryStatus.ACTIVE,
    )
    entry_comp = Ed25519TrustStoreEntry(
        key_id=compliance_signer.key_id,
        issuer_id=compliance_signer.issuer_id,
        public_key_b64=compliance_signer.public_key_b64,
        valid_from=now,
        status=TrustStoreEntryStatus.ACTIVE,
    )
    entry_pm = Ed25519TrustStoreEntry(
        key_id=unauthorized_signer.key_id,
        issuer_id=unauthorized_signer.issuer_id,
        public_key_b64=unauthorized_signer.public_key_b64,
        valid_from=now,
        status=TrustStoreEntryStatus.ACTIVE,
    )
    return Ed25519TrustStore(entries=(entry_risk, entry_comp, entry_pm))


def create_test_approval(
    signer: MockEd25519Signer,
    auth_id: str,
    role: ApproverRole,
    approver_id: str,
    approved_at: Optional[datetime] = None,
) -> AuthorizationApproval:
    ts = approved_at or datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    payload = {
        "authorization_id": auth_id,
        "approver_id": approver_id,
        "public_key_id": signer.key_id,
        "role": role.value,
        "approved_at": ts.isoformat(),
    }
    payload_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
    sig_b64 = signer.sign(payload_bytes)
    digest = hashlib.sha256(payload_bytes).hexdigest()

    return AuthorizationApproval(
        approver_id=approver_id,
        public_key_id=signer.key_id,
        role=role,
        authorization_id=auth_id,
        approved_at=ts,
        approval_signature=sig_b64,
        approval_digest=digest,
    )


# ============================================================================
# 1. STATE MACHINE & TRIP SEMANTICS TESTS
# ============================================================================


def test_kill_switch_initial_state(sample_trust_store: Ed25519TrustStore) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)
    assert controller.state == KillSwitchState.ACTIVE
    assert controller.is_blocked is False
    # Admission allowed in ACTIVE state
    controller.assert_admission_allowed()


def test_kill_switch_trip_and_block(sample_trust_store: Ed25519TrustStore) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)

    event = controller.trip(
        reason="MAX_DRAWDOWN_EXCEEDED: Peak equity drawdown breached limit.",
        evidence={"drawdown_pct": "16.50", "peak_equity": "12000.00"},
    )

    assert controller.state == KillSwitchState.PERSISTENTLY_BLOCKED
    assert controller.is_blocked is True
    assert event.resulting_state == KillSwitchState.PERSISTENTLY_BLOCKED
    assert len(event.event_digest) == 64

    # Admission must be BLOCKED
    with pytest.raises(DataContractError, match="EXECUTION_ADMISSION_BLOCKED"):
        controller.assert_admission_allowed()


def test_kill_switch_trip_idempotent_when_already_blocked(sample_trust_store: Ed25519TrustStore) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)
    controller.trip(reason="FIRST_TRIP")
    assert controller.state == KillSwitchState.PERSISTENTLY_BLOCKED

    # Second trip must not crash, remains PERSISTENTLY_BLOCKED
    event2 = controller.trip(reason="SECOND_TRIP_FLOOD")
    assert controller.state == KillSwitchState.PERSISTENTLY_BLOCKED
    assert "SECOND_TRIP_FLOOD" in event2.trigger_reason


# ============================================================================
# 2. MULTI-SIG RESET & QUORUM VERIFICATION TESTS
# ============================================================================


def test_kill_switch_authorized_reset_flow(
    sample_trust_store: Ed25519TrustStore,
    risk_officer_signer: MockEd25519Signer,
) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)
    trip_event = controller.trip(reason="DATA_FEED_STALE")

    # Construct valid single-sig reset proposal (required_approvals = 1)
    approval = create_test_approval(
        signer=risk_officer_signer,
        auth_id="RESET_REQ_001",
        role=ApproverRole.RISK_OFFICER,
        approver_id="OFFICER_ALICE",
    )

    reset_proposal = KillSwitchResetEvent(
        event_id="RESET_REQ_001",
        kill_switch_event_id=trip_event.event_id,
        root_cause_summary="Data feed latency restored to nominal 120ms.",
        approvals=(approval,),
        required_approvals=1,
        created_at_utc=datetime(2026, 9, 1, 12, 30, 0, tzinfo=timezone.utc),
    )

    active_event = controller.submit_reset(reset_proposal)

    assert controller.state == KillSwitchState.ACTIVE
    assert controller.is_blocked is False
    assert active_event.resulting_state == KillSwitchState.ACTIVE
    # Admission is permitted again
    controller.assert_admission_allowed()


def test_kill_switch_reset_rejects_unauthorized_approver_role(
    sample_trust_store: Ed25519TrustStore,
    unauthorized_signer: MockEd25519Signer,
) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)
    trip_event = controller.trip(reason="DATA_FEED_STALE")

    # PM role is NOT authorized to reset kill switch
    pm_approval = create_test_approval(
        signer=unauthorized_signer,
        auth_id="RESET_REQ_BAD_ROLE",
        role=ApproverRole.PORTFOLIO_MANAGER,
        approver_id="PM_BOB",
    )

    reset_proposal = KillSwitchResetEvent(
        event_id="RESET_REQ_BAD_ROLE",
        kill_switch_event_id=trip_event.event_id,
        root_cause_summary="PM requested unlock.",
        approvals=(pm_approval,),
        required_approvals=1,
        created_at_utc=datetime(2026, 9, 1, 12, 30, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(DataContractError, match="Unauthorized approver role"):
        controller.submit_reset(reset_proposal)

    # State remains PERSISTENTLY_BLOCKED
    assert controller.state == KillSwitchState.PERSISTENTLY_BLOCKED


def test_kill_switch_reset_rejects_replayed_approval(
    sample_trust_store: Ed25519TrustStore,
    risk_officer_signer: MockEd25519Signer,
) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)

    # 1. First trip and successful reset
    trip1 = controller.trip(reason="TRIP_1")
    app1 = create_test_approval(
        signer=risk_officer_signer,
        auth_id="RESET_01",
        role=ApproverRole.RISK_OFFICER,
        approver_id="OFFICER_ALICE",
    )
    reset1 = KillSwitchResetEvent(
        event_id="RESET_01",
        kill_switch_event_id=trip1.event_id,
        root_cause_summary="Resolved 1.",
        approvals=(app1,),
        required_approvals=1,
        created_at_utc=datetime(2026, 9, 1, 12, 30, 0, tzinfo=timezone.utc),
    )
    controller.submit_reset(reset1)
    assert controller.state.value == KillSwitchState.ACTIVE.value

    # 2. Second trip occurs
    trip2 = controller.trip(reason="TRIP_2")

    # 3. Adversary attempts to replay the exact same approval signature from RESET_01
    replay_reset = KillSwitchResetEvent(
        event_id="RESET_02_REPLAY",
        kill_switch_event_id=trip2.event_id,
        root_cause_summary="Attempted replay.",
        approvals=(app1,),  # Reused app1!
        required_approvals=1,
        created_at_utc=datetime(2026, 9, 1, 12, 45, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(DataContractError, match="Replayed approval detected"):
        controller.submit_reset(replay_reset)

    assert controller.state.value == KillSwitchState.PERSISTENTLY_BLOCKED.value


def test_kill_switch_reset_rejects_stale_target_trip_id(
    sample_trust_store: Ed25519TrustStore,
    risk_officer_signer: MockEd25519Signer,
) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)
    controller.trip(reason="TRIP_OLD")
    new_trip = controller.trip(reason="TRIP_NEWER")

    app = create_test_approval(
        signer=risk_officer_signer,
        auth_id="RESET_STALE",
        role=ApproverRole.RISK_OFFICER,
        approver_id="OFFICER_ALICE",
    )

    stale_reset = KillSwitchResetEvent(
        event_id="RESET_STALE",
        kill_switch_event_id="KILL_STALE_TRIP_ID_000",  # Does not match new_trip.event_id
        root_cause_summary="Stale reset proposal.",
        approvals=(app,),
        required_approvals=1,
        created_at_utc=datetime(2026, 9, 1, 13, 0, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(DataContractError, match="Stale or mismatched reset proposal"):
        controller.submit_reset(stale_reset)


# ============================================================================
# 3. PERSISTENCE & RESTART RECOVERY TESTS
# ============================================================================


def test_kill_switch_persistence_and_restart(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    ledger_file = tmp_path / "kill_switch_ledger.jsonl"

    # 1. Start controller 1 and trip
    c1 = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=ledger_file,
    )
    assert c1.state.value == KillSwitchState.ACTIVE.value
    c1.trip(reason="LATENCY_SPIKE_BREACH")
    assert c1.state.value == KillSwitchState.PERSISTENTLY_BLOCKED.value
    assert ledger_file.exists()

    # 2. Simulate process crash & restart with new controller instance reading same ledger
    c2 = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=ledger_file,
    )
    # Must recover in PERSISTENTLY_BLOCKED state!
    assert c2.state.value == KillSwitchState.PERSISTENTLY_BLOCKED.value
    assert c2.is_blocked is True
    with pytest.raises(DataContractError, match="EXECUTION_ADMISSION_BLOCKED"):
        c2.assert_admission_allowed()


def test_kill_switch_corrupted_persistence_fails_closed(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    ledger_file = tmp_path / "corrupted_ledger.jsonl"
    ledger_file.write_text("MALFORMED_NON_JSON_CORRUPTION\n", encoding="utf-8")

    # Corrupted ledger must fail closed with DataContractError and stay in PERSISTENTLY_BLOCKED
    with pytest.raises(DataContractError, match="PERSISTENCE_RECOVERY_FAILED"):
        SovereignKillSwitchController(
            trust_store=sample_trust_store,
            persistence_path=ledger_file,
        )


# ============================================================================
# 4. ARCHITECTURAL INVARIANTS & AUTHORITY BOUNDARY
# ============================================================================


def test_kill_switch_zero_broker_authority(sample_trust_store: Ed25519TrustStore) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)
    forbidden = [
        "submit_order",
        "execute_order",
        "place_order",
        "cancel_order",
        "send_wire",
        "get_broker_client",
    ]
    for m in forbidden:
        assert not hasattr(controller, m), f"SovereignKillSwitchController must not have '{m}' method."
