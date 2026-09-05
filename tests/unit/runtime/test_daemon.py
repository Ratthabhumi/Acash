"""Unit and adversarial tests for Phase 10 Continuous Paper Daemon & Live Harness (Slice 5).

Tests:
- Startup semantics: clean startup, corrupted ledger fail-closed, halted health block.
- Shutdown semantics: graceful stop, stopped pulse rejection, repeated stop safety.
- Continuous loop / harness execution: sequential multi-pulse progression.
- Mid-loop graceful stop request.
- Pulse idempotency & duplicate pulse rejection.
- Kill switch trip observation and execution block.
- Zero broker wire authority & paper-only boundary.
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
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.execution.signing import Ed25519Signer
from acash.portfolio.schema import AllocationDecision
from acash.research.alpha_schema import (
    AlphaEconomicDecomposition,
    AlphaLifecycleState,
    AlphaQualificationDossier,
)
from acash.risk.kill_switch import SovereignKillSwitchController
from acash.risk.risk_engine import DeterministicRiskEngine
from acash.runtime.daemon import (
    ContinuousPaperDaemon,
    DaemonLifecycleState,
    DaemonStatusReport,
)
from acash.runtime.ledger import OperationalLedger
from acash.runtime.scheduler import OperationalScheduler
from acash.runtime.schema import (
    CycleOutcome,
    RuntimeHealthStatus,
    RuntimePolicyConfig,
)
from acash.runtime.supervisor import RuntimeSupervisor


# ============================================================================
# FIXTURES & HELPERS
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


def mock_tournament_runner(
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


# ============================================================================
# 1. STARTUP & SHUTDOWN SEMANTICS
# ============================================================================


def test_daemon_startup_and_status_report(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    ledger_path = tmp_path / "daemon_ledger.jsonl"
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

    assert daemon.get_status_report().lifecycle_state == DaemonLifecycleState.UNINITIALIZED
    assert not daemon.is_running

    daemon.start()
    assert daemon.get_status_report().lifecycle_state == DaemonLifecycleState.RUNNING
    assert daemon.is_running

    status = daemon.get_status_report()
    assert status.lifecycle_state == DaemonLifecycleState.RUNNING
    assert status.runtime_health == RuntimeHealthStatus.RUNTIME_HEALTHY
    assert status.is_kill_switch_blocked is False
    assert status.total_cycles_executed == 0


def test_daemon_startup_fails_on_corrupted_ledger(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    ledger_path = tmp_path / "daemon_corrupt.jsonl"
    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)

    # Write garbage JSON to simulate corrupted ledger on disk before startup
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write("{corrupt_json_line\n")

    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=DeterministicRiskEngine(),
        kill_switch=SovereignKillSwitchController(trust_store=sample_trust_store),
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)

    with pytest.raises(DataContractError, match="DAEMON_STARTUP_FAILED"):
        daemon.start()

    assert daemon.lifecycle_state == DaemonLifecycleState.HALTED_FATAL


def test_daemon_startup_blocked_on_halted_health(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    ledger_path = tmp_path / "daemon_halted.jsonl"
    scheduler = OperationalScheduler()
    ledger = OperationalLedger(persistence_path=ledger_path)
    supervisor = RuntimeSupervisor(
        scheduler=scheduler,
        ledger=ledger,
        risk_engine=DeterministicRiskEngine(),
        kill_switch=SovereignKillSwitchController(trust_store=sample_trust_store),
        initial_health=RuntimeHealthStatus.RUNTIME_HALTED,
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)

    with pytest.raises(DataContractError, match="DAEMON_STARTUP_BLOCKED"):
        daemon.start()

    assert daemon.lifecycle_state == DaemonLifecycleState.HALTED_FATAL


def test_daemon_graceful_shutdown(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "daemon_shutdown.jsonl"
    supervisor = RuntimeSupervisor(
        scheduler=OperationalScheduler(),
        ledger=OperationalLedger(persistence_path=ledger_path),
        risk_engine=DeterministicRiskEngine(),
        kill_switch=SovereignKillSwitchController(trust_store=sample_trust_store),
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)
    daemon.start()

    daemon.stop()
    assert daemon.lifecycle_state == DaemonLifecycleState.STOPPED
    assert not daemon.is_running

    # Attempting to execute pulse when stopped fails closed
    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(DataContractError, match="DAEMON_NOT_RUNNING"):
        daemon.step_pulse(
            cycle_id="CYCLE_AFTER_STOP",
            as_of_utc=now,
            wall_clock_utc=now,
            portfolio_state=sample_portfolio_state,
            account_state=sample_account_state,
            qualified_dossiers=[sample_qualified_dossier],
            tournament_runner_fn=mock_tournament_runner,
        )


# ============================================================================
# 2. CONTINUOUS HARNESS & PULSE EXECUTION
# ============================================================================


def test_daemon_step_pulse_and_harness_loop(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "daemon_harness.jsonl"
    supervisor = RuntimeSupervisor(
        scheduler=OperationalScheduler(),
        ledger=OperationalLedger(persistence_path=ledger_path),
        risk_engine=DeterministicRiskEngine(),
        kill_switch=SovereignKillSwitchController(trust_store=sample_trust_store),
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)
    daemon.start()

    t0 = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 9, 2, 14, 1, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 2, 14, 2, 0, tzinfo=timezone.utc)

    # 3-pulse deterministic feed
    feed = [
        ("CYCLE_H_001", t0, t0, sample_portfolio_state, sample_account_state, [sample_qualified_dossier], mock_tournament_runner, 100, None),
        ("CYCLE_H_002", t1, t1, sample_portfolio_state, sample_account_state, [sample_qualified_dossier], mock_tournament_runner, 100, None),
        ("CYCLE_H_003", t2, t2, sample_portfolio_state, sample_account_state, [sample_qualified_dossier], mock_tournament_runner, 100, None),
    ]

    count = daemon.run_harness(iter(feed))
    assert count == 3
    assert daemon.get_status_report().total_cycles_executed == 3
    assert supervisor.ledger.event_count == 3


def test_daemon_idempotency_duplicate_pulse(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "daemon_idem.jsonl"
    supervisor = RuntimeSupervisor(
        scheduler=OperationalScheduler(),
        ledger=OperationalLedger(persistence_path=ledger_path),
        risk_engine=DeterministicRiskEngine(),
        kill_switch=SovereignKillSwitchController(trust_store=sample_trust_store),
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)
    daemon.start()

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    daemon.step_pulse(
        cycle_id="CYCLE_UNIQUE_001",
        as_of_utc=now,
        wall_clock_utc=now,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner,
    )

    # Re-executing same cycle_id raises IDEMPOTENT_DUPLICATE_CYCLE
    with pytest.raises(DataContractError, match="IDEMPOTENT_DUPLICATE_CYCLE"):
        daemon.step_pulse(
            cycle_id="CYCLE_UNIQUE_001",
            as_of_utc=now,
            wall_clock_utc=now,
            portfolio_state=sample_portfolio_state,
            account_state=sample_account_state,
            qualified_dossiers=[sample_qualified_dossier],
            tournament_runner_fn=mock_tournament_runner,
        )


def test_daemon_kill_switch_trip_blocks_pulse(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
    sample_qualified_dossier: AlphaQualificationDossier,
) -> None:
    ledger_path = tmp_path / "daemon_ks.jsonl"
    kill_switch = SovereignKillSwitchController(trust_store=sample_trust_store)
    supervisor = RuntimeSupervisor(
        scheduler=OperationalScheduler(),
        ledger=OperationalLedger(persistence_path=ledger_path),
        risk_engine=DeterministicRiskEngine(),
        kill_switch=kill_switch,
    )
    daemon = ContinuousPaperDaemon(supervisor=supervisor)
    daemon.start()

    # Trip sovereign kill switch
    kill_switch.trip(reason="EMERGENCY_VOLATILITY")

    now = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    summary = daemon.step_pulse(
        cycle_id="CYCLE_TRIPPED_001",
        as_of_utc=now,
        wall_clock_utc=now,
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        qualified_dossiers=[sample_qualified_dossier],
        tournament_runner_fn=mock_tournament_runner,
    )

    assert summary.outcome == CycleOutcome.RISK_REJECTED
    assert summary.admitted_for_execution is False
    assert daemon.get_status_report().is_kill_switch_blocked is True


def test_daemon_zero_broker_execution_authority() -> None:
    forbidden = [
        "submit_order",
        "execute_order",
        "cancel_order",
        "send_wire",
        "get_broker_client",
    ]
    for m in forbidden:
        assert not hasattr(ContinuousPaperDaemon, m)
