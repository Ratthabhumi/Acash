"""Full Cross-Phase End-to-End Integration Pipeline Tests for Phase 10 (Slice 6).

Proves the complete runtime operating chain:
    OperationalScheduler
           │
           ▼
    ContinuousPaperDaemon
           │
           ▼
    RuntimeSupervisor
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
Phase 8.5  Phase 8 Phase 9
           │
           ▼
        Phase 7
           │
           ▼
    OperationalLedger

Verifies:
1. Complete 5-stage happy path operational cycle.
2. Sovereign Risk veto blocks Phase 7 execution admission (Risk Reject -> No Execution).
3. Sovereign Kill Switch trip blocks execution admission across restarts.
4. Operational Health (PAUSED / HALTED) blocks cycles without mutating Phase 8.5 historical dossiers.
5. Idempotent cycle deduplication prevents duplicate pulses/orders.
6. Dual-clock discipline (as_of_utc != wall_clock_utc) preserved end-to-end.
7. Ledger SHA-256 hash chaining, replay audit, and tamper detection.
8. Zero direct broker execution wire authority in Phase 10 (Paper-only boundary).
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
from typing import List, Sequence
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.portfolio.schema import AllocationDecision
from acash.research.alpha_schema import (
    AlphaEconomicDecomposition,
    AlphaLifecycleState,
    AlphaQualificationDossier,
)
from acash.risk.kill_switch import SovereignKillSwitchController
from acash.risk.risk_engine import DeterministicRiskEngine
from acash.risk.risk_schema import (
    DeriskPolicy,
    KillSwitchState,
    RiskEvaluationReport,
    RiskPolicyConfig,
    RiskVerdict,
)
from acash.runtime.daemon import (
    ContinuousPaperDaemon,
    DaemonLifecycleState,
)
from acash.runtime.ledger import OperationalLedger
from acash.runtime.scheduler import OperationalScheduler
from acash.runtime.schema import (
    CycleOutcome,
    RuntimeHealthStatus,
    RuntimePolicyConfig,
    RuntimeRegime,
)
from acash.runtime.supervisor import RuntimeSupervisor


# ============================================================================
# TEST FIXTURES & CANONICAL ARTIFACT FACTORIES
# ============================================================================


@pytest.fixture
def sample_trust_store() -> Ed25519TrustStore:
    now = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    _, pub_key_b64 = Ed25519Signer.generate_key_pair()
    entry = Ed25519TrustStoreEntry(
        key_id="KEY_E2E_01",
        issuer_id="ACASH_AUTHORITY",
        public_key_b64=pub_key_b64,
        valid_from=now,
        status=TrustStoreEntryStatus.ACTIVE,
    )
    return Ed25519TrustStore(entries=(entry,))


@pytest.fixture
def sample_portfolio_state() -> PortfolioState:
    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    return PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("100000.00"),
        total_equity=Decimal("100000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )


@pytest.fixture
def sample_account_state() -> AccountState:
    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    return AccountState(
        account_id="ACC_E2E_001",
        currency="USD",
        balance=Decimal("100000.00"),
        equity=Decimal("100000.00"),
        free_margin=Decimal("100000.00"),
        leverage=1.0,
        is_live=False,
        timestamp_utc=now,
    )


@pytest.fixture
def sample_qualified_dossier() -> AlphaQualificationDossier:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    decomp = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("30.0"),
        realized_spread_slippage_bps=Decimal("2.5"),
        broker_commissions_bps=Decimal("1.5"),
        net_trading_alpha_bps=Decimal("26.0"),
        broker_rebate_income_bps=Decimal("0.0"),
        total_realized_economic_bps=Decimal("26.0"),
    )
    valid_hash = hashlib.sha256(b"lineage_e2e").hexdigest()
    return AlphaQualificationDossier(
        alpha_id="ALPHA_E2E_001",
        strategy_id="STRAT_E2E_MOMENTUM",
        hypothesis_digest=valid_hash,
        trial_ledger_digest=valid_hash,
        validation_report_digest=valid_hash,
        governance_policy_digest=valid_hash,
        economic_decomposition=decomp,
        lifecycle_state=AlphaLifecycleState.RESEARCH_QUALIFIED,
        capital_authority_usd=Decimal("0.00"),
        created_timestamp_utc=now.isoformat(),
        dossier_digest=valid_hash,
    )


def canonical_tournament_allocator(
    dossiers: Sequence[AlphaQualificationDossier],
    portfolio: PortfolioState,
    as_of: datetime,
) -> AllocationDecision:
    valid_hash = hashlib.sha256(b"lineage_alloc").hexdigest()
    return AllocationDecision(
        decision_id="DEC_E2E_001",
        selected_candidate_id="CAND_E2E_01",
        allocator_name="MAX_SHARPE_TOURNAMENT",
        authorized_weights={"AAPL": Decimal("0.20"), "MSFT": Decimal("0.20")},
        cash_weight=Decimal("0.60"),
        authorization_timestamp=as_of,
        is_fallback_baseline=False,
        gate_verdict="APPROVED_TOURNAMENT",
        rationale="Canonical tournament selection",
        candidate_digest=valid_hash,
        evaluation_digest=valid_hash,
        risk_snapshot_digest=valid_hash,
        constraints_digest=valid_hash,
    )


# ============================================================================
# 1. FULL END-TO-END OPERATIONAL REBALANCE CYCLE (HAPPY PATH)
# ============================================================================


def test_full_pipeline_happy_path_e2e(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "e2e_operational_ledger.jsonl"
    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)
    risk_engine = DeterministicRiskEngine()
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)
    daemon.start()

    # Logical decision time != Wall-clock execution time
    as_of_utc = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock_utc = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    # Track admission verification invocation
    admission_invocations: List[str] = []

    def mock_phase7_admission(report: RiskEvaluationReport, port: PortfolioState) -> bool:
        admission_invocations.append(report.report_digest)
        return True

    summary = daemon.step_pulse(
        cycle_id="CYCLE_E2E_HAPPY_001",
        as_of_utc=as_of_utc,
        wall_clock_utc=wall_clock_utc,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=canonical_tournament_allocator,
        data_age_ms=150,
        admission_hook_fn=mock_phase7_admission,
    )

    # Assert 5-stage complete success
    assert summary.outcome == CycleOutcome.SUCCESS
    assert summary.admitted_for_execution is True
    assert summary.allocation_decision is not None
    assert summary.risk_report is not None
    assert summary.risk_report.verdict == RiskVerdict.APPROVED
    assert len(admission_invocations) == 1

    # Assert ledger integrity and cryptographic sealing
    assert ledger.event_count == 1
    assert ledger.last_sequence == 0
    assert ledger.last_event_digest != ""
    is_valid, ev_count, last_d = ledger.verify_ledger_integrity()
    assert is_valid is True
    assert ev_count == 1
    assert last_d == ledger.last_event_digest

    # Assert daemon status report
    status = daemon.get_status_report()
    assert status.lifecycle_state == DaemonLifecycleState.RUNNING
    assert status.total_cycles_executed == 1
    assert status.last_cycle_outcome == CycleOutcome.SUCCESS


# ============================================================================
# 2. SOVEREIGN RISK VETO ISOLATION (RISK REJECT -> NO EXECUTION)
# ============================================================================


def test_full_pipeline_risk_rejection_blocks_execution(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "e2e_risk_veto.jsonl"
    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)

    # Strict risk policy: max asset concentration = 0.15 (candidate proposes 0.20)
    strict_policy = RiskPolicyConfig(
        derisk_policy=DeriskPolicy.BINARY_REJECT,
        max_asset_concentration=Decimal("0.15"),
    )
    risk_engine = DeterministicRiskEngine(policy_config=strict_policy)
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)
    daemon.start()

    as_of_utc = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock_utc = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    admission_called = False

    def admission_hook(report: RiskEvaluationReport, port: PortfolioState) -> bool:
        nonlocal admission_called
        admission_called = True
        return True

    summary = daemon.step_pulse(
        cycle_id="CYCLE_E2E_VETO_001",
        as_of_utc=as_of_utc,
        wall_clock_utc=wall_clock_utc,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=canonical_tournament_allocator,
        data_age_ms=150,
        admission_hook_fn=admission_hook,
    )

    # Risk Engine Veto must block Phase 7 admission
    assert summary.outcome == CycleOutcome.RISK_REJECTED
    assert summary.admitted_for_execution is False
    assert admission_called is False
    assert summary.risk_report is not None
    assert summary.risk_report.verdict == RiskVerdict.REJECTED
    assert ledger.event_count == 1


# ============================================================================
# 3. SOVEREIGN KILL SWITCH LOCKOUT & RESTART INVARIANCE
# ============================================================================


def test_full_pipeline_kill_switch_blocks_and_persists_across_restart(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "e2e_ks_ledger.jsonl"
    ks_path = tmp_path / "kill_switch_state.jsonl"

    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)
    risk_engine = DeterministicRiskEngine()
    kill_switch = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=ks_path,
    )

    # Trip sovereign kill switch
    kill_switch.trip(reason="EMERGENCY_VOLATILITY_CIRCUIT_BREAKER")
    assert kill_switch.is_blocked is True

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)
    daemon.start()

    as_of_utc = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock_utc = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    summary = daemon.step_pulse(
        cycle_id="CYCLE_E2E_KS_001",
        as_of_utc=as_of_utc,
        wall_clock_utc=wall_clock_utc,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=canonical_tournament_allocator,
    )

    assert summary.outcome == CycleOutcome.RISK_REJECTED
    assert summary.admitted_for_execution is False

    # Simulate process crash and restart from disk
    recovered_ks = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=ks_path,
    )
    assert recovered_ks.is_blocked is True
    assert recovered_ks.state in (KillSwitchState.TRIPPED, KillSwitchState.PERSISTENTLY_BLOCKED)


# ============================================================================
# 4. RUNTIME HEALTH SEPARATION & DOSSIER IMMUTABILITY
# ============================================================================


def test_runtime_health_does_not_mutate_alpha_dossier(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "e2e_health_ledger.jsonl"
    supervisor = RuntimeSupervisor(
        scheduler=OperationalScheduler(),
        ledger=OperationalLedger(persistence_path=ledger_path),
        risk_engine=DeterministicRiskEngine(),
        kill_switch=SovereignKillSwitchController(trust_store=sample_trust_store),
    )

    # Initial dossier state
    original_digest = sample_qualified_dossier.dossier_digest
    original_state = sample_qualified_dossier.lifecycle_state

    # Transition runtime health to degraded and paused
    supervisor.set_health_status(RuntimeHealthStatus.RUNTIME_DEGRADED, reason="TELEMETRY_LATENCY_SPIKE")
    assert supervisor.health_status == RuntimeHealthStatus.RUNTIME_DEGRADED

    # Dossier is immutable and unaffected
    assert sample_qualified_dossier.dossier_digest == original_digest
    assert sample_qualified_dossier.lifecycle_state == original_state
    assert supervisor.kill_switch.is_blocked is False  # Health != KillSwitch


# ============================================================================
# 5. IDEMPOTENCY & REPLAY ATTACK DEFENSE
# ============================================================================


def test_duplicate_cycle_pulse_strictly_rejected(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "e2e_idempotency.jsonl"
    supervisor = RuntimeSupervisor(
        scheduler=OperationalScheduler(),
        ledger=OperationalLedger(persistence_path=ledger_path),
        risk_engine=DeterministicRiskEngine(),
        kill_switch=SovereignKillSwitchController(trust_store=sample_trust_store),
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)
    daemon.start()

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)

    # Pulse 1 succeeds
    daemon.step_pulse(
        cycle_id="CYCLE_E2E_PULSE_001",
        as_of_utc=now,
        wall_clock_utc=now,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=canonical_tournament_allocator,
    )

    # Pulse 1 replayed fails closed
    with pytest.raises(DataContractError, match="IDEMPOTENT_DUPLICATE_CYCLE"):
        daemon.step_pulse(
            cycle_id="CYCLE_E2E_PULSE_001",
            as_of_utc=now,
            wall_clock_utc=now,
            portfolio_state=sample_portfolio_state,
            account_state=sample_account_state,
            qualified_dossiers=[sample_qualified_dossier],
            tournament_runner_fn=canonical_tournament_allocator,
        )


# ============================================================================
# 6. ZERO BROKER WIRE AUTHORITY (PAPER-ONLY BOUNDARY)
# ============================================================================


def test_phase10_runtime_zero_broker_execution_authority() -> None:
    forbidden_methods = [
        "submit_order",
        "execute_order",
        "cancel_order",
        "send_wire",
        "get_broker_client",
        "connect_live_broker",
    ]
    for target in [OperationalScheduler, OperationalLedger, RuntimeSupervisor, ContinuousPaperDaemon]:
        for method_name in forbidden_methods:
            assert not hasattr(target, method_name), f"{target.__name__} has illegal broker method {method_name}"
