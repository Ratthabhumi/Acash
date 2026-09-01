"""Phase 10: Runtime Supervisor & 5-Stage Orchestrator (Slice 4).

Strictly enforces:
1. Five-Way Sovereign Separation:
   Research (8.5) != Allocation (8) != Supervisor (10) != Risk (9) != Execution (7) != Broker.
2. Zero Direct Execution Authority:
   Supervisor orchestrates lifecycle; it has zero broker socket/wire access.
3. Fail-Closed Stage Progression:
   Stage 1 (Data) -> Stage 2 (Strategy) -> Stage 3 (Tournament) -> Stage 4 (Risk) -> Stage 5 (Admission).
   Failure at any stage terminates cycle immediately; no later stage executes.
4. Sovereign Risk Veto & Kill Switch Respect:
   Risk REJECTED or Kill Switch BLOCKED unconditionally blocks execution admission.
5. Runtime Health != Kill Switch:
   Maintains independent RuntimeHealthStatus without modifying Phase 8.5 historical dossiers.
6. Evidence Sealing via OperationalLedger:
   Every cycle outcome is immutably recorded to disk ledger with SHA-256 hash chaining.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import logging
from typing import Callable, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.signal import TargetAllocation
from acash.core.domain.types import freeze_mapping
from acash.core.serialization import CanonicalConfigSerializer
from acash.portfolio.schema import AllocationDecision
from acash.research.alpha_schema import AlphaLifecycleState, AlphaQualificationDossier
from acash.risk.bridge import RiskStateBridge
from acash.risk.kill_switch import SovereignKillSwitchController
from acash.risk.risk_engine import DeterministicRiskEngine
from acash.risk.risk_schema import (
    CandidateRiskAllocation,
    KillSwitchState,
    RiskEvaluationReport,
    RiskVerdict,
)
from acash.runtime.ledger import OperationalLedger
from acash.runtime.scheduler import OperationalScheduler
from acash.runtime.schema import (
    CycleIdentity,
    CycleOutcome,
    OperationalCycleEvent,
    RuntimeHealthStatus,
    RuntimePolicyConfig,
    RuntimeRegime,
    _ensure_utc,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CycleExecutionSummary:
    """Immutable summary of an executed operational cycle."""

    cycle_identity: CycleIdentity
    wall_clock_utc: datetime
    outcome: CycleOutcome
    runtime_health: RuntimeHealthStatus
    active_dossier_digests: Tuple[str, ...] = ()
    allocation_decision: Optional[AllocationDecision] = None
    risk_report: Optional[RiskEvaluationReport] = None
    admitted_for_execution: bool = False
    error_message: Optional[str] = None
    event_digest: str = ""


class RuntimeSupervisor:
    """Authoritative 5-stage runtime pipeline supervisor and operational orchestrator."""

    def __init__(
        self,
        scheduler: OperationalScheduler,
        ledger: OperationalLedger,
        risk_engine: DeterministicRiskEngine,
        kill_switch: SovereignKillSwitchController,
        policy_config: Optional[RuntimePolicyConfig] = None,
        initial_health: RuntimeHealthStatus = RuntimeHealthStatus.RUNTIME_HEALTHY,
    ) -> None:
        self.scheduler: OperationalScheduler = scheduler
        self.ledger: OperationalLedger = ledger
        self.risk_engine: DeterministicRiskEngine = risk_engine
        self.kill_switch: SovereignKillSwitchController = kill_switch
        self.policy: RuntimePolicyConfig = policy_config or scheduler.policy
        self._health_status: RuntimeHealthStatus = initial_health

    @property
    def health_status(self) -> RuntimeHealthStatus:
        """Return current operational health status."""
        return self._health_status

    def set_health_status(self, new_status: RuntimeHealthStatus, reason: str = "") -> None:
        """Update runtime health status with auditable logging."""
        if not isinstance(new_status, RuntimeHealthStatus):
            raise DataContractError(f"Invalid health status: {new_status}")
        logger.info(f"Runtime health transitioned: {self._health_status} -> {new_status}. Reason: {reason}")
        self._health_status = new_status

    def execute_rebalance_cycle(
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
        """Execute the full 5-stage operational rebalance cycle.

        Stage 1: Telemetry & Ingestion Check (data freshness)
        Stage 2: Strategy Census (discover active RESEARCH_QUALIFIED dossiers)
        Stage 3: Phase 8 Allocation Tournament
        Stage 4: Phase 9 Sovereign Risk Evaluation
        Stage 5: Phase 7 Execution Admission Verification
        """
        as_of = _ensure_utc(as_of_utc, "as_of_utc")
        wall_clock = _ensure_utc(wall_clock_utc, "wall_clock_utc")

        # Health Lockout: Paused or Halted supervisor cannot execute cycles
        if self._health_status in (RuntimeHealthStatus.RUNTIME_PAUSED, RuntimeHealthStatus.RUNTIME_HALTED):
            raise DataContractError(
                f"EXECUTION_BLOCKED_HEALTH: Cannot execute cycle while in health state '{self._health_status.value}'."
            )

        # Start cycle in scheduler (enforces concurrency and idempotency locks)
        cycle_identity = self.scheduler.start_cycle(
            cycle_id=cycle_id,
            as_of_utc=as_of,
            wall_clock_utc=wall_clock,
            regime=RuntimeRegime.REBALANCE_PULSE,
        )

        dossier_digests: Tuple[str, ...] = ()
        alloc_decision: Optional[AllocationDecision] = None
        risk_report: Optional[RiskEvaluationReport] = None
        admitted = False
        outcome = CycleOutcome.SUCCESS
        err_msg: Optional[str] = None

        try:
            # ----------------------------------------------------------------
            # STAGE 1: Telemetry & Ingestion Freshness Check
            # ----------------------------------------------------------------
            if data_age_ms > self.policy.max_market_data_age_ms:
                outcome = CycleOutcome.DATA_STALE
                err_msg = f"Data age {data_age_ms}ms exceeds max tolerance {self.policy.max_market_data_age_ms}ms."
                self._record_and_complete(cycle_identity, wall_clock, outcome, err_msg)
                return CycleExecutionSummary(
                    cycle_identity=cycle_identity,
                    wall_clock_utc=wall_clock,
                    outcome=outcome,
                    runtime_health=self._health_status,
                    error_message=err_msg,
                    event_digest=self.ledger.last_event_digest,
                )

            # ----------------------------------------------------------------
            # STAGE 2: Strategy Census (Filter for RESEARCH_QUALIFIED)
            # ----------------------------------------------------------------
            active_dossiers = [
                d for d in qualified_dossiers
                if d.lifecycle_state == AlphaLifecycleState.RESEARCH_QUALIFIED
            ]
            dossier_digests = tuple(sorted(d.dossier_digest for d in active_dossiers))

            if not active_dossiers:
                # Governed 100% cash fallback if no qualified alpha active
                logger.warning(f"Cycle {cycle_id}: Zero active RESEARCH_QUALIFIED strategies found. Falling back to 100% cash.")

            # ----------------------------------------------------------------
            # STAGE 3: Phase 8 Allocation Tournament
            # ----------------------------------------------------------------
            try:
                alloc_decision = tournament_runner_fn(active_dossiers, portfolio_state, as_of)
            except Exception as e:
                outcome = CycleOutcome.DISPATCH_FAILED
                err_msg = f"Tournament execution failed: {e}"
                self._record_and_complete(cycle_identity, wall_clock, outcome, err_msg, dossier_digests)
                return CycleExecutionSummary(
                    cycle_identity=cycle_identity,
                    wall_clock_utc=wall_clock,
                    outcome=outcome,
                    runtime_health=self._health_status,
                    active_dossier_digests=dossier_digests,
                    error_message=err_msg,
                    event_digest=self.ledger.last_event_digest,
                )

            # ----------------------------------------------------------------
            # STAGE 4: Phase 9 Sovereign Risk Evaluation & Kill Switch Check
            # ----------------------------------------------------------------
            # Kill switch check
            if self.kill_switch.is_blocked:
                outcome = CycleOutcome.RISK_REJECTED
                err_msg = f"Sovereign Kill Switch is BLOCKED: {self.kill_switch.state.value}."
                self._record_and_complete(
                    cycle_identity, wall_clock, outcome, err_msg, dossier_digests,
                    alloc_decision_digest=alloc_decision.decision_digest,
                )
                return CycleExecutionSummary(
                    cycle_identity=cycle_identity,
                    wall_clock_utc=wall_clock,
                    outcome=outcome,
                    runtime_health=self._health_status,
                    active_dossier_digests=dossier_digests,
                    allocation_decision=alloc_decision,
                    error_message=err_msg,
                    event_digest=self.ledger.last_event_digest,
                )

            # Convert AllocationDecision -> CandidateRiskAllocation
            candidate_risk_alloc = CandidateRiskAllocation(
                candidate_id=alloc_decision.selected_candidate_id,
                strategy_id=alloc_decision.allocator_name,
                weights=alloc_decision.authorized_weights,
                cash_weight=alloc_decision.cash_weight,
                source_decision_digest=alloc_decision.decision_digest,
                as_of_utc=as_of,
            )

            risk_report = self.risk_engine.evaluate_candidate_allocation(
                candidate_allocation=candidate_risk_alloc,
                portfolio_state=portfolio_state,
                account_state=account_state,
                as_of=as_of,
            )

            if risk_report.verdict in (RiskVerdict.REJECTED, RiskVerdict.KILL_SWITCH_BLOCKED):
                outcome = CycleOutcome.RISK_REJECTED
                err_msg = f"Risk Engine Veto: {risk_report.verdict.value}. Reason: {risk_report.rejection_reason}"
                self._record_and_complete(
                    cycle_identity, wall_clock, outcome, err_msg, dossier_digests,
                    alloc_decision_digest=alloc_decision.decision_digest,
                    risk_report_digest=risk_report.report_digest,
                )
                return CycleExecutionSummary(
                    cycle_identity=cycle_identity,
                    wall_clock_utc=wall_clock,
                    outcome=outcome,
                    runtime_health=self._health_status,
                    active_dossier_digests=dossier_digests,
                    allocation_decision=alloc_decision,
                    risk_report=risk_report,
                    admitted_for_execution=False,
                    error_message=err_msg,
                    event_digest=self.ledger.last_event_digest,
                )

            # ----------------------------------------------------------------
            # STAGE 5: Phase 7 Execution Admission Verification
            # ----------------------------------------------------------------
            if admission_hook_fn is not None:
                try:
                    admission_passed = admission_hook_fn(risk_report, portfolio_state)
                    if not admission_passed:
                        outcome = CycleOutcome.DISPATCH_FAILED
                        err_msg = "Phase 7 execution admission hook returned False."
                        self._record_and_complete(
                            cycle_identity, wall_clock, outcome, err_msg, dossier_digests,
                            alloc_decision_digest=alloc_decision.decision_digest,
                            risk_report_digest=risk_report.report_digest,
                        )
                        return CycleExecutionSummary(
                            cycle_identity=cycle_identity,
                            wall_clock_utc=wall_clock,
                            outcome=outcome,
                            runtime_health=self._health_status,
                            active_dossier_digests=dossier_digests,
                            allocation_decision=alloc_decision,
                            risk_report=risk_report,
                            admitted_for_execution=False,
                            error_message=err_msg,
                            event_digest=self.ledger.last_event_digest,
                        )
                except Exception as e:
                    outcome = CycleOutcome.DISPATCH_FAILED
                    err_msg = f"Phase 7 admission check raised exception: {e}"
                    self._record_and_complete(
                        cycle_identity, wall_clock, outcome, err_msg, dossier_digests,
                        alloc_decision_digest=alloc_decision.decision_digest,
                        risk_report_digest=risk_report.report_digest,
                    )
                    return CycleExecutionSummary(
                        cycle_identity=cycle_identity,
                        wall_clock_utc=wall_clock,
                        outcome=outcome,
                        runtime_health=self._health_status,
                        active_dossier_digests=dossier_digests,
                        allocation_decision=alloc_decision,
                        risk_report=risk_report,
                        admitted_for_execution=False,
                        error_message=err_msg,
                        event_digest=self.ledger.last_event_digest,
                    )

            admitted = True
            outcome = CycleOutcome.SUCCESS

            # Record final successful cycle in ledger & complete in scheduler
            port_snapshot = RiskStateBridge.portfolio_state_to_risk_snapshot(
                portfolio_state=portfolio_state,
                account_state=account_state,
            )
            port_digest = port_snapshot.snapshot_digest
            acc_payload = {
                "account_id": account_state.account_id,
                "currency": account_state.currency,
                "balance": str(account_state.balance),
                "equity": str(account_state.equity),
                "free_margin": str(account_state.free_margin),
                "timestamp_utc": account_state.timestamp_utc.isoformat(),
            }
            acc_digest = hashlib.sha256(CanonicalConfigSerializer.to_canonical_json(acc_payload).encode("utf-8")).hexdigest()

            self._record_and_complete(
                cycle_identity, wall_clock, outcome, None, dossier_digests,
                portfolio_digest=port_digest,
                account_digest=acc_digest,
                alloc_decision_digest=alloc_decision.decision_digest,
                risk_report_digest=risk_report.report_digest,
            )

            return CycleExecutionSummary(
                cycle_identity=cycle_identity,
                wall_clock_utc=wall_clock,
                outcome=outcome,
                runtime_health=self._health_status,
                active_dossier_digests=dossier_digests,
                allocation_decision=alloc_decision,
                risk_report=risk_report,
                admitted_for_execution=admitted,
                event_digest=self.ledger.last_event_digest,
            )

        except Exception as unhandled_exc:
            # Catch-all fail closed: record interrupted crash and complete scheduler
            outcome = CycleOutcome.INTERRUPTED_CRASH
            err_msg = f"Unhandled pipeline crash: {unhandled_exc}"
            try:
                self._record_and_complete(cycle_identity, wall_clock, outcome, err_msg, dossier_digests)
            except Exception:
                pass  # Avoid masking original exception

            return CycleExecutionSummary(
                cycle_identity=cycle_identity,
                wall_clock_utc=wall_clock,
                outcome=outcome,
                runtime_health=self._health_status,
                active_dossier_digests=dossier_digests,
                error_message=err_msg,
                event_digest=self.ledger.last_event_digest,
            )

    def _record_and_complete(
        self,
        cycle_identity: CycleIdentity,
        wall_clock_utc: datetime,
        outcome: CycleOutcome,
        error_message: Optional[str] = None,
        active_dossier_digests: Tuple[str, ...] = (),
        portfolio_digest: str = "",
        account_digest: str = "",
        alloc_decision_digest: str = "",
        risk_report_digest: str = "",
        execution_manifest_digests: Tuple[str, ...] = (),
    ) -> None:
        """Commit operational event to ledger and release scheduler cycle lock."""
        event = OperationalCycleEvent(
            cycle_identity=cycle_identity,
            wall_clock_utc=wall_clock_utc,
            runtime_health=self._health_status,
            active_dossier_digests=active_dossier_digests,
            portfolio_state_digest=portfolio_digest,
            account_state_digest=account_digest,
            allocation_decision_digest=alloc_decision_digest,
            risk_report_digest=risk_report_digest,
            execution_manifest_digests=execution_manifest_digests,
            kill_switch_state_val=self.kill_switch.state.value,
            cycle_outcome=outcome,
            error_message=error_message,
            previous_event_digest=self.ledger.last_event_digest,
        )
        self.ledger.append_event(event)
        self.scheduler.complete_cycle(cycle_identity.cycle_id, outcome, wall_clock_utc)
