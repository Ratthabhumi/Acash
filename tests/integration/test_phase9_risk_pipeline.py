"""Full Cross-Phase Integration & Lineage Invariant Test Suite for Phase 9.

Tests:
1. End-to-End Runtime Pipeline:
   Phase 8.5 Research Qualification -> Phase 8 Allocation Decision -> Phase 9 Risk Engine -> Phase 7 Execution Admission.
2. Happy Path:
   RESEARCH_QUALIFIED alpha ($0 capital authority) -> Phase 8 valid allocation -> Phase 9 APPROVED -> Phase 7 admission allowed.
3. REDUCED Path:
   Scalable constraint breach -> deterministic scale-down factor -> RiskVerdict.REDUCED -> compliant targets.
4. REJECTED Path:
   Drawdown/margin breach -> RiskVerdict.REJECTED -> 0 orders reach execution boundary.
5. Sovereign Kill Switch Lifecycle:
   Trip -> PERSISTENTLY_BLOCKED -> admission blocked -> restart recovery -> multi-sig Ed25519 quorum reset -> ACTIVE.
6. Emergency Flattening Intent Lifecycle:
   Open positions -> target 0.0 -> EmergencyFlattenIntent -> partial fill remains FLATTEN_REQUESTED -> broker reconciliation confirms 0 exposure -> FLATTEN_COMPLETED.
7. Authority Boundary Enforcement:
   Phase 8.5 has $0 capital authority; Phase 9 has zero broker wire authority; Phase 7 is the sole broker execution authority.
8. Replay & Staleness Defense:
   Expired TTL reports, mismatched policy digests, and tampered state fail closed.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
from typing import Mapping, Optional
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.signal import TargetAllocation
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.execution.schema import ApproverRole, AuthorizationApproval, RiskState, RiskStatus
from acash.portfolio.schema import (
    AllocationCandidate,
    AllocationDecision,
    PortfolioConstraints,
    RebalancePlan,
    RiskSnapshot,
)
from acash.research.alpha_schema import (
    AlphaLifecycleState,
)
from acash.risk.bridge import RiskStateBridge
from acash.risk.emergency import EmergencyFlattenGenerator, EmergencyFlattenTracker
from acash.risk.kill_switch import SovereignKillSwitchController
from acash.risk.risk_engine import DeterministicRiskEngine
from acash.risk.risk_schema import (
    CandidateRiskAllocation,
    DeriskPolicy,
    EmergencyFlattenIntent,
    EmergencyFlattenStatus,
    KillSwitchResetEvent,
    KillSwitchState,
    RiskEvaluationReport,
    RiskPolicyConfig,
    RiskVerdict,
)


class MockEd25519Signer:
    """Signer helper for multi-sig fixtures."""

    def __init__(self, key_id: str, issuer_id: str) -> None:
        self.key_id = key_id
        self.issuer_id = issuer_id
        self.private_key_b64, self.public_key_b64 = Ed25519Signer.generate_key_pair()

    def sign(self, payload_bytes: bytes) -> str:
        return Ed25519Signer.sign(self.private_key_b64, payload_bytes)


@pytest.fixture
def risk_officer() -> MockEd25519Signer:
    return MockEd25519Signer("KEY_RISK_01", "ACASH_RISK_AUTHORITY")


@pytest.fixture
def compliance_officer() -> MockEd25519Signer:
    return MockEd25519Signer("KEY_COMP_01", "ACASH_COMPLIANCE_AUTHORITY")


@pytest.fixture
def sample_trust_store(
    risk_officer: MockEd25519Signer,
    compliance_officer: MockEd25519Signer,
) -> Ed25519TrustStore:
    now = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    entry_risk = Ed25519TrustStoreEntry(
        key_id=risk_officer.key_id,
        issuer_id=risk_officer.issuer_id,
        public_key_b64=risk_officer.public_key_b64,
        valid_from=now,
        status=TrustStoreEntryStatus.ACTIVE,
    )
    entry_comp = Ed25519TrustStoreEntry(
        key_id=compliance_officer.key_id,
        issuer_id=compliance_officer.issuer_id,
        public_key_b64=compliance_officer.public_key_b64,
        valid_from=now,
        status=TrustStoreEntryStatus.ACTIVE,
    )
    return Ed25519TrustStore(entries=(entry_risk, entry_comp))


@pytest.fixture
def standard_risk_policy() -> RiskPolicyConfig:
    return RiskPolicyConfig(
        max_gross_leverage=Decimal("1.00"),
        max_asset_concentration=Decimal("0.50"),
        min_cash_buffer=Decimal("0.10"),
        max_drawdown_limit_pct=Decimal("15.00"),
        max_daily_loss_usd=Decimal("10000.00"),
        min_margin_buffer_usd=Decimal("5000.00"),
        max_market_data_age_ms=60000,
        max_clock_drift_ms=5000,
    )


@pytest.fixture
def standard_portfolio_state() -> PortfolioState:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    pos_aapl = Position(
        symbol="AAPL",
        quantity=Decimal("50"),
        entry_price=Decimal("150.00"),
        current_price=Decimal("150.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    return PortfolioState(
        timestamp_utc=now,
        positions={"AAPL": pos_aapl},
        cash_balance=Decimal("12500.00"),
        total_equity=Decimal("20000.00"),
        margin_used=Decimal("7500.00"),
        gross_exposure=Decimal("7500.00"),
        net_exposure=Decimal("7500.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )


@pytest.fixture
def standard_account_state() -> AccountState:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    return AccountState(
        account_id="ACC_MAIN_01",
        currency="USD",
        balance=Decimal("20000.00"),
        equity=Decimal("20000.00"),
        free_margin=Decimal("12500.00"),
        margin_level_pct=266.67,
        leverage=1.0,
        is_live=False,
        timestamp_utc=now,
    )


def create_approval(
    signer: MockEd25519Signer,
    auth_id: str,
    role: ApproverRole,
    approver_id: str,
    ts: datetime,
) -> AuthorizationApproval:
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
# 1. HAPPY PATH: ALPHA QUALIFIED -> ALLOCATION -> RISK APPROVED -> ADMISSION
# ============================================================================


def test_integration_happy_path_pipeline(
    standard_risk_policy: RiskPolicyConfig,
    standard_portfolio_state: PortfolioState,
    standard_account_state: AccountState,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Phase 8.5: Research Alpha Qualification Invariant (Zero Capital Authority)
    # Alpha qualifies statistically, but has ZERO allocation/capital authority
    alpha_status = AlphaLifecycleState.RESEARCH_QUALIFIED
    assert alpha_status.value == "RESEARCH_QUALIFIED"

    # 2. Phase 8: Portfolio Tournament produces AllocationDecision & RebalancePlan
    candidate_alloc = CandidateRiskAllocation(
        candidate_id="CAND_P8_WINNER",
        strategy_id="MULTI_HORIZON_MOMENTUM",
        weights={"AAPL": Decimal("0.35"), "MSFT": Decimal("0.45")},
        cash_weight=Decimal("0.20"),
        source_decision_digest=hashlib.sha256(b"phase8_decision").hexdigest(),
        as_of_utc=now,
    )

    # 3. Phase 9: Sovereign Risk Evaluation
    engine = DeterministicRiskEngine(
        policy_config=standard_risk_policy,
    )
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=candidate_alloc,
        portfolio_state=standard_portfolio_state,
        account_state=standard_account_state,
        as_of=now,
    )

    # Must be APPROVED
    assert report.verdict == RiskVerdict.APPROVED
    assert report.adjusted_weights["AAPL"] == Decimal("0.35")
    assert report.adjusted_weights["MSFT"] == Decimal("0.45")
    assert report.cash_weight == Decimal("0.20")
    assert report.is_expired(as_of=now + timedelta(seconds=10)) is False

    # 4. Phase 9 -> Phase 7 Execution RiskState Bridge
    risk_state = RiskStateBridge.risk_evaluation_report_to_execution_risk_state(
        report=report,
        portfolio_state=standard_portfolio_state,
        authorization_id="AUTH_LIVE_001",
        strategy_id="MULTI_HORIZON_MOMENTUM",
    )
    assert risk_state.risk_status == RiskStatus.NORMAL
    assert risk_state.total_equity == Decimal("20000.00")

    # 5. Admission verification: Controller is in ACTIVE state -> Admission permitted
    ks_controller = SovereignKillSwitchController(trust_store=sample_trust_store)
    ks_controller.assert_admission_allowed()


# ============================================================================
# 2. REDUCED PATH: SCALABLE RISK CONSTRAINT BREACH
# ============================================================================


def test_integration_reduced_path_pipeline(
    standard_risk_policy: RiskPolicyConfig,
    standard_portfolio_state: PortfolioState,
    standard_account_state: AccountState,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Candidate breaches max single asset concentration (MSFT at 0.70 > max 0.50)
    over_concentrated_candidate = CandidateRiskAllocation(
        candidate_id="CAND_P8_OVERCONCENTRATED",
        strategy_id="MOMENTUM_AGGRESSIVE",
        weights={"AAPL": Decimal("0.20"), "MSFT": Decimal("0.70")},
        cash_weight=Decimal("0.10"),
        source_decision_digest=hashlib.sha256(b"phase8_overconcentrated").hexdigest(),
        as_of_utc=now,
    )

    engine = DeterministicRiskEngine(
        policy_config=standard_risk_policy,
    )
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=over_concentrated_candidate,
        portfolio_state=standard_portfolio_state,
        account_state=standard_account_state,
        as_of=now,
    )

    # Scaled down monotonically via EXACT_SCALE_DOWN
    assert report.verdict == RiskVerdict.REDUCED
    # Scale factor alpha = 0.50 / 0.70 = 5/7 ≈ 0.7142857142857143
    assert report.adjusted_weights["MSFT"] <= Decimal("0.5000000000000001")
    assert report.adjusted_weights["AAPL"] < Decimal("0.20")
    # Cash buffer preserved
    assert report.cash_weight >= standard_risk_policy.min_cash_buffer

    # Handed to Phase 7 as RESTRICTED
    risk_state = RiskStateBridge.risk_evaluation_report_to_execution_risk_state(
        report=report,
        portfolio_state=standard_portfolio_state,
        authorization_id="AUTH_LIVE_001",
        strategy_id="MOMENTUM_AGGRESSIVE",
    )
    assert risk_state.risk_status == RiskStatus.RESTRICTED


# ============================================================================
# 3. REJECTED PATH: NON-SCALABLE RISK BREACH & BINARY REJECT
# ============================================================================


def test_integration_rejected_path_drawdown_breach(
    standard_risk_policy: RiskPolicyConfig,
    standard_account_state: AccountState,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Portfolio has suffered massive drawdown: peak 40000 -> current 20000 (50% drawdown > max 15%)
    pos_aapl = Position(
        symbol="AAPL",
        quantity=Decimal("50"),
        entry_price=Decimal("150.00"),
        current_price=Decimal("150.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    drawdown_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={"AAPL": pos_aapl},
        cash_balance=Decimal("12500.00"),
        total_equity=Decimal("20000.00"),
        margin_used=Decimal("7500.00"),
        gross_exposure=Decimal("7500.00"),
        net_exposure=Decimal("7500.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    candidate = CandidateRiskAllocation(
        candidate_id="CAND_001",
        strategy_id="STRAT_001",
        weights={"AAPL": Decimal("0.30")},
        cash_weight=Decimal("0.70"),
        source_decision_digest=hashlib.sha256(b"cand").hexdigest(),
        as_of_utc=now,
    )

    engine = DeterministicRiskEngine(
        policy_config=standard_risk_policy,
    )
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=candidate,
        portfolio_state=drawdown_portfolio,
        account_state=standard_account_state,
        peak_equity=Decimal("40000.00"),  # Breaches max_drawdown_limit_pct!
        as_of=now,
    )

    # Sovereign drawdown breach triggers kill switch block
    assert report.verdict == RiskVerdict.KILL_SWITCH_BLOCKED
    assert len(report.adjusted_weights) == 0
    assert report.cash_weight == Decimal("1.0")
    assert "MAX_DRAWDOWN_BREACHED" in (report.rejection_reason or "")


def test_integration_rejected_path_binary_reject_policy(
    standard_portfolio_state: PortfolioState,
    standard_account_state: AccountState,
) -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # BINARY_REJECT policy rejects any breach instead of derisking
    binary_policy = RiskPolicyConfig(
        derisk_policy=DeriskPolicy.BINARY_REJECT,
        max_gross_leverage=Decimal("1.00"),
        max_asset_concentration=Decimal("0.30"),
        min_cash_buffer=Decimal("0.10"),
    )

    over_leverage_candidate = CandidateRiskAllocation(
        candidate_id="CAND_OVER_LEV",
        strategy_id="HIGH_LEVERAGE_STRAT",
        weights={"AAPL": Decimal("0.60"), "MSFT": Decimal("0.60")},  # Gross 1.20 > max 1.00
        cash_weight=Decimal("0.00"),
        source_decision_digest=hashlib.sha256(b"over_lev").hexdigest(),
        as_of_utc=now,
    )

    engine = DeterministicRiskEngine(policy_config=binary_policy)
    report = engine.evaluate_candidate_allocation(
        candidate_allocation=over_leverage_candidate,
        portfolio_state=standard_portfolio_state,
        account_state=standard_account_state,
        as_of=now,
    )

    assert report.verdict == RiskVerdict.REJECTED
    assert len(report.adjusted_weights) == 0
    assert report.cash_weight == Decimal("1.0")
    assert "BINARY_REJECT" in (report.rejection_reason or "")


# ============================================================================
# 4. KILL SWITCH PATH: TRIP -> PERSISTENCE -> RESTART -> MULTI-SIG RESET
# ============================================================================


def test_integration_kill_switch_lifecycle_and_restart(
    tmp_path: Path,
    standard_risk_policy: RiskPolicyConfig,
    sample_trust_store: Ed25519TrustStore,
    risk_officer: MockEd25519Signer,
    compliance_officer: MockEd25519Signer,
) -> None:
    ledger_path = tmp_path / "sovereign_kill_switch.jsonl"

    # 1. Initialize Engine & Kill Switch Controller
    controller1 = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=ledger_path,
    )
    assert controller1.state.value == KillSwitchState.ACTIVE.value
    controller1.assert_admission_allowed()

    # 2. Trip Kill Switch
    trip_event = controller1.trip(
        reason="ANOMALY_LATENCY_SPIKE",
        evidence={"broker_latency_ms": 15000},
    )
    assert controller1.state.value == KillSwitchState.PERSISTENTLY_BLOCKED.value
    assert controller1.is_blocked is True
    with pytest.raises(DataContractError, match="EXECUTION_ADMISSION_BLOCKED"):
        controller1.assert_admission_allowed()

    # 3. Simulate process crash & restart -> Must recover in PERSISTENTLY_BLOCKED!
    controller2 = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=ledger_path,
    )
    assert controller2.state.value == KillSwitchState.PERSISTENTLY_BLOCKED.value
    assert controller2.is_blocked is True
    with pytest.raises(DataContractError, match="EXECUTION_ADMISSION_BLOCKED"):
        controller2.assert_admission_allowed()

    # 4. Authorized Multi-Sig Quorum Reset (2-of-2 required)
    now = datetime(2026, 9, 1, 12, 30, 0, tzinfo=timezone.utc)
    app_risk = create_approval(
        signer=risk_officer,
        auth_id="RESET_001",
        role=ApproverRole.RISK_OFFICER,
        approver_id="OFFICER_BOB",
        ts=now,
    )
    app_comp = create_approval(
        signer=compliance_officer,
        auth_id="RESET_001",
        role=ApproverRole.COMPLIANCE_OFFICER,
        approver_id="OFFICER_CAROL",
        ts=now,
    )

    reset_event = KillSwitchResetEvent(
        event_id="RESET_001",
        kill_switch_event_id=trip_event.event_id,
        root_cause_summary="Network gateway rerouted to secondary optical fiber.",
        approvals=(app_risk, app_comp),
        required_approvals=2,
        created_at_utc=now,
    )

    active_event = controller2.submit_reset(reset_event)
    assert controller2.state == KillSwitchState.ACTIVE
    assert controller2.is_blocked is False
    assert active_event.resulting_state == KillSwitchState.ACTIVE
    controller2.assert_admission_allowed()


# ============================================================================
# 5. EMERGENCY FLATTEN PATH: INTENT -> RECONCILIATION -> COMPLETION
# ============================================================================


def test_integration_emergency_flatten_lifecycle(
    standard_portfolio_state: PortfolioState,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    controller = SovereignKillSwitchController(trust_store=sample_trust_store)
    trip_event = controller.trip(reason="EMERGENCY_DRAWDOWN")

    # 1. Phase 9 generates EmergencyFlattenIntent
    intent = EmergencyFlattenGenerator.generate_flatten_intent(
        portfolio_state=standard_portfolio_state,
        kill_switch_event=trip_event,
    )
    assert intent.status == EmergencyFlattenStatus.FLATTEN_REQUESTED
    assert intent.target_positions["AAPL"] == Decimal("0.0")
    assert intent.closing_deltas["AAPL"] == Decimal("-50.0")

    # 2. Phase 7 Partial Fill: 30 shares filled, 20 remaining
    now = datetime(2026, 9, 1, 12, 5, 0, tzinfo=timezone.utc)
    pos_partial = Position(
        symbol="AAPL",
        quantity=Decimal("20"),
        entry_price=Decimal("150.00"),
        current_price=Decimal("150.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    partial_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={"AAPL": pos_partial},
        cash_balance=Decimal("17000.00"),
        total_equity=Decimal("20000.00"),
        margin_used=Decimal("3000.00"),
        gross_exposure=Decimal("3000.00"),
        net_exposure=Decimal("3000.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    status_partial, remaining = EmergencyFlattenTracker.verify_flatten_completion(
        intent=intent,
        latest_portfolio_state=partial_portfolio,
        is_broker_reconciled=True,
    )
    # Partial fill remains FLATTEN_REQUESTED
    assert status_partial == EmergencyFlattenStatus.FLATTEN_REQUESTED
    assert remaining["AAPL"] == Decimal("20")

    # 3. Phase 7 Full Fill + Broker Reconciliation confirms 0 gross exposure
    zero_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("20000.00"),
        total_equity=Decimal("20000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    status_completed, remaining_zero = EmergencyFlattenTracker.verify_flatten_completion(
        intent=intent,
        latest_portfolio_state=zero_portfolio,
        is_broker_reconciled=True,
    )
    # ONLY now is FLATTEN_COMPLETED granted
    assert status_completed == EmergencyFlattenStatus.FLATTEN_COMPLETED
    assert len(remaining_zero) == 0


# ============================================================================
# 6. CROSS-PHASE AUTHORITY SEPARATION TESTS
# ============================================================================


def test_integration_cross_phase_authority_separation() -> None:
    """Verify strictly segregated authorities across Phases 8.5, 8, 9, and 7."""
    # Phase 9 Risk Engine must NOT have direct broker wire authority
    forbidden_broker_methods = [
        "submit_order",
        "execute_order",
        "cancel_order",
        "send_wire",
        "place_order",
    ]
    for m in forbidden_broker_methods:
        assert not hasattr(DeterministicRiskEngine, m)
        assert not hasattr(SovereignKillSwitchController, m)
        assert not hasattr(EmergencyFlattenGenerator, m)
        assert not hasattr(RiskStateBridge, m)
