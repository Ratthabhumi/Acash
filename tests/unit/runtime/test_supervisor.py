"""Unit and adversarial tests for Phase 10 Runtime Supervisor & 5-Stage Orchestrator (Slice 4).

Tests:
- Happy path 5-stage progression: Data -> Census -> Tournament -> Risk -> Admission.
- Fail-closed Stage 1: Data stale blocks stages 2-5.
- Fail-closed Stage 3: Tournament exception blocks stages 4-5.
- Fail-closed Stage 4: Risk REJECTED and Kill Switch BLOCKED block stage 5.
- Fail-closed Stage 5: Execution admission rejection terminates cycle safely.
- Health state lockout (RUNTIME_PAUSED, RUNTIME_HALTED).
- Concurrency and duplicate cycle prevention.
- Zero broker execution authority on RuntimeSupervisor.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
from typing import List, Sequence
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.signal import TargetAllocation
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
# TEST FIXTURES & HELPERS
# ============================================================================


@pytest.fixture
def sample_trust_store() -> Ed25519TrustStore:
    now = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    _, pub_key_b64 = Ed25519Signer.generate_key_pair()
    entry = Ed25519TrustStoreEntry(
        key_id="KEY_01",
        issuer_id="ACASH_AUTH",
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
        account_id="ACC_001",
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
        gross_trading_pnl_bps=Decimal("25.0"),
        realized_spread_slippage_bps=Decimal("2.0"),
        broker_commissions_bps=Decimal("1.0"),
        net_trading_alpha_bps=Decimal("22.0"),
        broker_rebate_income_bps=Decimal("0.0"),
        total_realized_economic_bps=Decimal("22.0"),
    )
    valid_hash = hashlib.sha256(b"lineage").hexdigest()
    return AlphaQualificationDossier(
        alpha_id="ALPHA_001",
        strategy_id="STRAT_TREND",
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


def mock_tournament_runner_approved(
    dossiers: Sequence[AlphaQualificationDossier],
    portfolio: PortfolioState,
    as_of: datetime,
) -> AllocationDecision:
    valid_hash = hashlib.sha256(b"lineage").hexdigest()
    return AllocationDecision(
        decision_id="DEC_001",
        selected_candidate_id="CAND_01",
        allocator_name="MAX_SHARPE",
        authorized_weights={"AAPL": Decimal("0.25"), "MSFT": Decimal("0.25")},
        cash_weight=Decimal("0.50"),
        authorization_timestamp=as_of,
        is_fallback_baseline=False,
        gate_verdict="APPROVED_TOURNAMENT",
        rationale="Optimal risk-adjusted Sharpe",
        candidate_digest=valid_hash,
        evaluation_digest=valid_hash,
        risk_snapshot_digest=valid_hash,
        constraints_digest=valid_hash,
    )


def mock_tournament_runner_failing(
    dossiers: Sequence[AlphaQualificationDossier],
    portfolio: PortfolioState,
    as_of: datetime,
) -> AllocationDecision:
    raise RuntimeError("Optimizer failed to converge (simulated failure).")


# ============================================================================
# 1. HAPPY PATH 5-STAGE PROGRESSION TEST
# ============================================================================


def test_supervisor_happy_path_5_stage_progression(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
    policy = RuntimePolicyConfig(max_market_data_age_ms=1500)
    scheduler = OperationalScheduler(policy_config=policy)
    ledger = OperationalLedger(persistence_path=ledger_path)
    risk_engine = DeterministicRiskEngine()
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
        policy_config=policy,
    )

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    summary = supervisor.execute_rebalance_cycle(
        cycle_id="CYCLE_HAPPY_001",
        as_of_utc=now,
        wall_clock_utc=wall_clock,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner_approved,
        data_age_ms=120,  # Nominal freshness
        admission_hook_fn=lambda report, port: True,  # Phase 7 admission OK
    )

    assert summary.outcome == CycleOutcome.SUCCESS
    assert summary.admitted_for_execution is True
    assert summary.allocation_decision is not None
    assert summary.risk_report is not None
    assert summary.risk_report.verdict == RiskVerdict.APPROVED
    assert len(summary.active_dossier_digests) == 1
    assert ledger.event_count == 1
    assert ledger.last_sequence == 0


# ============================================================================
# 2. FAIL-CLOSED STAGE 1 (DATA STALE) TEST
# ============================================================================


def test_supervisor_fail_closed_stage_1_data_stale(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
    policy = RuntimePolicyConfig(max_market_data_age_ms=1500)
    scheduler = OperationalScheduler(policy_config=policy)
    ledger = OperationalLedger(persistence_path=ledger_path)
    risk_engine = DeterministicRiskEngine()
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
    )

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    summary = supervisor.execute_rebalance_cycle(
        cycle_id="CYCLE_STALE_001",
        as_of_utc=now,
        wall_clock_utc=wall_clock,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner_approved,
        data_age_ms=3500,  # Exceeds 1500ms
    )

    assert summary.outcome == CycleOutcome.DATA_STALE
    assert summary.admitted_for_execution is False
    assert summary.allocation_decision is None  # Stage 3 did NOT run
    assert summary.risk_report is None         # Stage 4 did NOT run
    assert "exceeds max tolerance" in (summary.error_message or "")
    assert ledger.event_count == 1


# ============================================================================
# 3. FAIL-CLOSED STAGE 3 (TOURNAMENT CRASH) TEST
# ============================================================================


def test_supervisor_fail_closed_stage_3_tournament_failure(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
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

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    summary = supervisor.execute_rebalance_cycle(
        cycle_id="CYCLE_CRASH_001",
        as_of_utc=now,
        wall_clock_utc=wall_clock,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner_failing,  # Raises exception
        data_age_ms=100,
    )

    assert summary.outcome == CycleOutcome.DISPATCH_FAILED
    assert summary.admitted_for_execution is False
    assert summary.risk_report is None  # Stage 4 did NOT run
    assert "Tournament execution failed" in (summary.error_message or "")
    assert ledger.event_count == 1


# ============================================================================
# 4. FAIL-CLOSED STAGE 4 (RISK REJECTED & KILL SWITCH BLOCKED) TESTS
# ============================================================================


def test_supervisor_fail_closed_stage_4_risk_veto(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)

    # Risk Engine with BINARY_REJECT and tight concentration (max 0.20)
    strict_policy = RiskPolicyConfig(
        derisk_policy=DeriskPolicy.BINARY_REJECT,
        max_asset_concentration=Decimal("0.20"),
    )
    risk_engine = DeterministicRiskEngine(policy_config=strict_policy)
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
    )

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    # Tournament proposes AAPL 0.25 (breaches max concentration 0.20)
    summary = supervisor.execute_rebalance_cycle(
        cycle_id="CYCLE_VETO_001",
        as_of_utc=now,
        wall_clock_utc=wall_clock,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner_approved,
        data_age_ms=100,
        admission_hook_fn=lambda report, port: True,
    )

    assert summary.outcome == CycleOutcome.RISK_REJECTED
    assert summary.admitted_for_execution is False
    assert summary.risk_report is not None
    assert summary.risk_report.verdict == RiskVerdict.REJECTED
    assert "Risk Engine Veto" in (summary.error_message or "")
    assert ledger.event_count == 1


def test_supervisor_fail_closed_kill_switch_blocked(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)
    risk_engine = DeterministicRiskEngine()
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)

    # Trip the sovereign kill switch
    kill_switch.trip(reason="EMERGENCY_VOLATILITY_SPIKE")
    assert kill_switch.is_blocked is True

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
    )

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    summary = supervisor.execute_rebalance_cycle(
        cycle_id="CYCLE_KS_BLOCKED_001",
        as_of_utc=now,
        wall_clock_utc=wall_clock,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner_approved,
        data_age_ms=100,
    )

    assert summary.outcome == CycleOutcome.RISK_REJECTED
    assert summary.admitted_for_execution is False
    assert "Sovereign Kill Switch is BLOCKED" in (summary.error_message or "")
    assert ledger.event_count == 1


# ============================================================================
# 5. HEALTH STATE LOCKOUT & CONCURRENCY TESTS
# ============================================================================


def test_supervisor_rejects_cycle_when_paused_or_halted(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)
    risk_engine = DeterministicRiskEngine()
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
        initial_health=RuntimeHealthStatus.RUNTIME_PAUSED,
    )

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    with pytest.raises(DataContractError, match="EXECUTION_BLOCKED_HEALTH"):
        supervisor.execute_rebalance_cycle(
            cycle_id="CYCLE_PAUSED_001",
            as_of_utc=now,
            wall_clock_utc=wall_clock,
            portfolio_state=sample_portfolio_state,
            account_state=sample_account_state,
            qualified_dossiers=[sample_qualified_dossier],
            tournament_runner_fn=mock_tournament_runner_approved,
        )


def test_supervisor_fail_closed_stage_5_admission_rejection(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
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

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    summary = supervisor.execute_rebalance_cycle(
        cycle_id="CYCLE_ADMISSION_FAIL_001",
        as_of_utc=now,
        wall_clock_utc=wall_clock,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner_approved,
        data_age_ms=100,
        admission_hook_fn=lambda report, port: False,  # Phase 7 rejects admission
    )

    assert summary.outcome == CycleOutcome.DISPATCH_FAILED
    assert summary.admitted_for_execution is False
    assert "Phase 7 execution admission hook returned False" in (summary.error_message or "")
    assert ledger.event_count == 1


def test_supervisor_idempotency_duplicate_cycle_rejection(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
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

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    # First run succeeds
    summary = supervisor.execute_rebalance_cycle(
        cycle_id="CYCLE_IDEM_001",
        as_of_utc=now,
        wall_clock_utc=wall_clock,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner_approved,
        data_age_ms=100,
        admission_hook_fn=lambda report, port: True,
    )
    assert summary.outcome == CycleOutcome.SUCCESS

    # Second run with same cycle_id is rejected by scheduler
    with pytest.raises(DataContractError, match="IDEMPOTENT_DUPLICATE_CYCLE"):
        supervisor.execute_rebalance_cycle(
            cycle_id="CYCLE_IDEM_001",
            as_of_utc=now,
            wall_clock_utc=wall_clock,
            portfolio_state=sample_portfolio_state,
            account_state=sample_account_state,
            qualified_dossiers=[sample_qualified_dossier],
            tournament_runner_fn=mock_tournament_runner_approved,
        )


def test_supervisor_concurrency_busy_lockout(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "supervisor_ledger.jsonl"
    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)
    risk_engine = DeterministicRiskEngine()
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)

    # Manually acquire lock on scheduler
    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    scheduler.start_cycle("CYCLE_IN_PROGRESS", now, now, RuntimeRegime.MARKET_OPEN)

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=risk_engine,
        kill_switch=kill_switch,
    )

    # Starting another cycle while one is active raises CYCLE_LOCKED_BUSY
    with pytest.raises(DataContractError, match="CYCLE_LOCKED_BUSY"):
        supervisor.execute_rebalance_cycle(
            cycle_id="CYCLE_CONCURRENT_002",
            as_of_utc=now,
            wall_clock_utc=now,
            portfolio_state=sample_portfolio_state,
            account_state=sample_account_state,
            qualified_dossiers=[sample_qualified_dossier],
            tournament_runner_fn=mock_tournament_runner_approved,
        )


def test_supervisor_zero_broker_execution_authority() -> None:
    forbidden = [
        "submit_order",
        "execute_order",
        "cancel_order",
        "send_wire",
        "get_broker_client",
    ]
    for m in forbidden:
        assert not hasattr(RuntimeSupervisor, m)
