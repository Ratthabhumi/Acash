"""Phase 10: Continuous Paper Trading Daemon & Operational Harness (Slice 5).

Strictly enforces:
1. Long-Running Continuous Lifecycle:
   Manages controlled START -> WAIT -> PULSE -> SUPERVISOR -> LEDGER -> STOP lifecycle.
2. Zero Direct Execution / Broker Authority:
   The daemon is an operational harness orchestrator; it has zero direct broker wire/API access.
   Enforces paper-only bounds unless downstream Phase 7 independently authorizes.
3. Dual-Clock Discipline:
   Preserves strict separation of as_of_utc (logical evaluation time) and wall_clock_utc (NTP system time).
4. Graceful Shutdown & Fail-Closed Safety:
   Handles clean stop requests between cycles; halts immediately on fatal integrity or ledger errors.
5. Sovereign Kill Switch & Runtime Health Awareness:
   Observes Phase 9 KillSwitchState and Phase 10 RuntimeHealthStatus; blocks cycle dispatch on trip/halt.
6. Idempotency & Concurrency:
   Relies on OperationalScheduler and OperationalLedger for duplicate rejection and busy lockouts.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import logging
import time
from typing import Any, Callable, Iterator, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.portfolio.schema import AllocationDecision
from acash.research.alpha_schema import AlphaQualificationDossier
from acash.risk.kill_switch import SovereignKillSwitchController
from acash.risk.risk_engine import DeterministicRiskEngine
from acash.risk.risk_schema import RiskEvaluationReport
from acash.runtime.ledger import OperationalLedger
from acash.runtime.scheduler import OperationalScheduler
from acash.runtime.schema import (
    CycleOutcome,
    RuntimeHealthStatus,
    RuntimePolicyConfig,
    RuntimeRegime,
    _ensure_utc,
)
from acash.runtime.supervisor import CycleExecutionSummary, RuntimeSupervisor

logger = logging.getLogger(__name__)


class DaemonLifecycleState(str, Enum):
    """Operational lifecycle state of the continuous paper daemon."""

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    HALTED_FATAL = "HALTED_FATAL"


@dataclass(frozen=True)
class DaemonStatusReport:
    """Immutable status snapshot of the paper daemon."""

    lifecycle_state: DaemonLifecycleState
    runtime_health: RuntimeHealthStatus
    is_kill_switch_blocked: bool
    last_cycle_id: Optional[str]
    last_cycle_outcome: Optional[CycleOutcome]
    total_cycles_executed: int
    last_pulse_wall_clock_utc: Optional[datetime]
    ledger_event_count: int
    last_event_digest: str


class ContinuousPaperDaemon:
    """Authoritative long-running continuous paper trading daemon and harness."""

    def __init__(
        self,
        supervisor: RuntimeSupervisor,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self.supervisor: RuntimeSupervisor = supervisor
        self.scheduler: OperationalScheduler = supervisor.scheduler
        self.ledger: OperationalLedger = supervisor.ledger
        self.risk_engine: DeterministicRiskEngine = supervisor.risk_engine
        self.kill_switch: SovereignKillSwitchController = supervisor.kill_switch
        self.policy: RuntimePolicyConfig = supervisor.policy

        self.poll_interval_seconds: float = poll_interval_seconds
        self._lifecycle_state: DaemonLifecycleState = DaemonLifecycleState.UNINITIALIZED
        self._stop_requested: bool = False
        self._total_cycles_executed: int = 0
        self._last_cycle_id: Optional[str] = None
        self._last_cycle_outcome: Optional[CycleOutcome] = None
        self._last_pulse_wall_clock_utc: Optional[datetime] = None

    @property
    def lifecycle_state(self) -> DaemonLifecycleState:
        """Return current daemon lifecycle state."""
        return self._lifecycle_state

    @property
    def is_running(self) -> bool:
        """Return True if daemon is actively running."""
        return self._lifecycle_state == DaemonLifecycleState.RUNNING

    def start(self) -> None:
        """Start and initialize the continuous paper daemon."""
        if self._lifecycle_state == DaemonLifecycleState.RUNNING:
            logger.warning("ContinuousPaperDaemon is already running.")
            return

        self._lifecycle_state = DaemonLifecycleState.INITIALIZING
        logger.info("Initializing ContinuousPaperDaemon...")

        # Verify integrity of underlying ledger
        try:
            self.ledger.verify_ledger_integrity()
        except Exception as e:
            self._lifecycle_state = DaemonLifecycleState.HALTED_FATAL
            raise DataContractError(f"DAEMON_STARTUP_FAILED: Corrupted ledger integrity: {e}") from e

        # Fail closed on halted runtime health
        if self.supervisor.health_status == RuntimeHealthStatus.RUNTIME_HALTED:
            self._lifecycle_state = DaemonLifecycleState.HALTED_FATAL
            raise DataContractError("DAEMON_STARTUP_BLOCKED: Runtime health is RUNTIME_HALTED.")

        self._stop_requested = False
        self._lifecycle_state = DaemonLifecycleState.RUNNING
        logger.info("ContinuousPaperDaemon started successfully.")

    def stop(self) -> None:
        """Request graceful shutdown of the daemon."""
        if self._lifecycle_state in (DaemonLifecycleState.STOPPED, DaemonLifecycleState.UNINITIALIZED):
            return

        logger.info("Requesting graceful shutdown of ContinuousPaperDaemon...")
        self._stop_requested = True
        self._lifecycle_state = DaemonLifecycleState.STOPPING
        # Finalize stop
        self._lifecycle_state = DaemonLifecycleState.STOPPED
        logger.info("ContinuousPaperDaemon stopped.")

    def step_pulse(
        self,
        cycle_id: str,
        as_of_utc: datetime,
        wall_clock_utc: datetime,
        portfolio_state: PortfolioState,
        account_state: AccountState,
        qualified_dossiers: Sequence[AlphaQualificationDossier],
        tournament_runner_fn: Callable[[Sequence[AlphaQualificationDossier], PortfolioState, datetime], AllocationDecision],
        data_age_ms: int = 0,
        admission_hook_fn: Optional[Callable[[RiskEvaluationReport, PortfolioState], bool]] = None,
    ) -> CycleExecutionSummary:
        """Execute a single discrete rebalance pulse cycle through the supervisor."""
        if self._lifecycle_state not in (DaemonLifecycleState.RUNNING, DaemonLifecycleState.INITIALIZING):
            raise DataContractError(
                f"DAEMON_NOT_RUNNING: Cannot execute pulse when daemon is in state '{self._lifecycle_state.value}'."
            )

        as_of = _ensure_utc(as_of_utc, "as_of_utc")
        wall_clock = _ensure_utc(wall_clock_utc, "wall_clock_utc")

        # Execute cycle via authoritative supervisor
        summary = self.supervisor.execute_rebalance_cycle(
            cycle_id=cycle_id,
            as_of_utc=as_of,
            wall_clock_utc=wall_clock,
            portfolio_state=portfolio_state,
            account_state=account_state,
            qualified_dossiers=qualified_dossiers,
            tournament_runner_fn=tournament_runner_fn,
            data_age_ms=data_age_ms,
            admission_hook_fn=admission_hook_fn,
        )

        self._total_cycles_executed += 1
        self._last_cycle_id = cycle_id
        self._last_cycle_outcome = summary.outcome
        self._last_pulse_wall_clock_utc = wall_clock

        return summary

    def run_harness(
        self,
        pulse_feed: Iterator[Tuple[str, datetime, datetime, PortfolioState, AccountState, Sequence[AlphaQualificationDossier], Callable[..., AllocationDecision], int, Optional[Callable[..., bool]]]],
    ) -> int:
        """Run continuous harness loop consuming a pulse iterator until feed exhausts or stop requested."""
        if not self.is_running:
            self.start()

        pulses_executed = 0
        for pulse_args in pulse_feed:
            if self._stop_requested:
                logger.info("Daemon stop requested. Terminating harness loop.")
                break

            self.step_pulse(*pulse_args)
            pulses_executed += 1

        if self._stop_requested:
            self.stop()

        return pulses_executed

    def get_status_report(self) -> DaemonStatusReport:
        """Get an immutable status report of the running daemon."""
        return DaemonStatusReport(
            lifecycle_state=self._lifecycle_state,
            runtime_health=self.supervisor.health_status,
            is_kill_switch_blocked=self.kill_switch.is_blocked,
            last_cycle_id=self._last_cycle_id,
            last_cycle_outcome=self._last_cycle_outcome,
            total_cycles_executed=self._total_cycles_executed,
            last_pulse_wall_clock_utc=self._last_pulse_wall_clock_utc,
            ledger_event_count=self.ledger.event_count,
            last_event_digest=self.ledger.last_event_digest,
        )
