"""Phase 11 Forward Health State Machine & Anti-Whipsaw Hysteresis.

Deterministic forward strategy health classification implementing the 6-stage decoupled authority funnel:
Metric -> Detection -> Evidence -> Recommendation -> Governance Decision -> Eligibility Consequence

Strict Sovereign Boundaries:
- Zero broker interaction.
- Zero Phase 8 portfolio mutation or friction writes.
- Zero direct tournament eligibility mutation (strictly forbidden from setting is_tournament_eligible).
- Emits advisory evidence (StrategyForwardDriftEvidence) to consuming Phase 10 Stage 2 Census.
- Infrastructure/telemetry state (MONITORING_BLOCKED) is strictly separated from performance degradation.
- Catastrophic structural break triggers immediately using lifetime inception HWM drawdown.
- Anti-whipsaw asymmetric hysteresis: M_recover > N_degrade + T_cooldown.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence, Tuple
import uuid

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.schema import (
    ForwardGovernanceRecommendation,
    ForwardHealthPolicy,
    ForwardHealthState,
    ForwardWindowMetrics,
    StrategyForwardDriftEvidence,
)


@dataclass(frozen=True)
class StateTransitionResult:
    """Immutable result of a single forward health state transition step."""

    state: ForwardHealthState
    recommendation: ForwardGovernanceRecommendation
    consecutive_degraded_periods: int
    consecutive_recovery_periods: int
    recovery_cooldown_remaining: int
    drift_flags: Tuple[str, ...]


class ForwardHealthStateMachine:
    """Deterministic finite state machine governing forward strategy health."""

    def __init__(self, policy: ForwardHealthPolicy) -> None:
        self.policy = policy

    def evaluate_step(
        self,
        current_state: ForwardHealthState,
        metrics: ForwardWindowMetrics,
        consecutive_degraded_periods: int = 0,
        consecutive_recovery_periods: int = 0,
        recovery_cooldown_remaining: int = 0,
        is_telemetry_valid: bool = True,
        baseline_sharpe: Optional[Decimal] = None,
    ) -> StateTransitionResult:
        """Evaluate next health state and advisory recommendation.

        Deterministic Transition Precedence:
        1. Telemetry Failure: If is_telemetry_valid == False, transition immediately to MONITORING_BLOCKED.
        2. Catastrophic Structural Break: If inception_max_drawdown >= critical_drawdown_limit, transition
           immediately to STRUCTURAL_BREAK (takes precedence over observation count when telemetry is valid).
        3. Absorbing Break: If already in STRUCTURAL_BREAK, state is absorbing and cannot auto-recover.
        4. Re-entry from Blocked: If current_state == MONITORING_BLOCKED and telemetry is restored, transition
           to INSUFFICIENT_EVIDENCE to rebuild clean evidence without synthesizing missing data.
        5. Insufficient Evidence: If observation_count < min_observations, state is INSUFFICIENT_EVIDENCE.
        6. Asymmetric Anti-Whipsaw Hysteresis:
           - HEALTHY -> DEGRADED requires N_degrade consecutive degraded periods.
           - DEGRADED -> HEALTHY requires M_recover consecutive healthy periods AND recovery_cooldown_remaining == 0.
        """
        # Priority 1: Telemetry Failure (Infrastructure state, NOT performance degradation)
        if not is_telemetry_valid:
            return StateTransitionResult(
                state=ForwardHealthState.MONITORING_BLOCKED,
                recommendation=ForwardGovernanceRecommendation.MONITORING_BLOCKED_FLAG,
                consecutive_degraded_periods=consecutive_degraded_periods,
                consecutive_recovery_periods=0,
                recovery_cooldown_remaining=recovery_cooldown_remaining,
                drift_flags=("TELEMETRY_CORRUPTED",),
            )

        # Priority 2: Catastrophic Structural Break (Inception HWM Drawdown Threshold Breach)
        # Precedence Invariant: Catastrophic structural break takes precedence over insufficient observation
        # count when telemetry is valid, ensuring catastrophic loss is never obscured by low bar count.
        if metrics.inception_max_drawdown >= self.policy.critical_drawdown_limit:
            return StateTransitionResult(
                state=ForwardHealthState.STRUCTURAL_BREAK,
                recommendation=ForwardGovernanceRecommendation.RECOMMEND_EXCLUSION,
                consecutive_degraded_periods=consecutive_degraded_periods + 1,
                consecutive_recovery_periods=0,
                recovery_cooldown_remaining=0,
                drift_flags=("CRITICAL_DRAWDOWN_BREACH",),
            )

        # Priority 3: Absorbing Structural Break (Cannot auto-recover via market movement)
        if current_state == ForwardHealthState.STRUCTURAL_BREAK:
            return StateTransitionResult(
                state=ForwardHealthState.STRUCTURAL_BREAK,
                recommendation=ForwardGovernanceRecommendation.RECOMMEND_EXCLUSION,
                consecutive_degraded_periods=consecutive_degraded_periods,
                consecutive_recovery_periods=0,
                recovery_cooldown_remaining=0,
                drift_flags=("ABSORBING_STRUCTURAL_BREAK",),
            )

        # Priority 4: Re-entry from MONITORING_BLOCKED
        # Fail-closed semantics: When telemetry is restored after being blocked, state transitions to
        # INSUFFICIENT_EVIDENCE to rebuild clean evidence. It does not assume prior state validity and
        # never synthesizes missing observations across the outage gap.
        if current_state == ForwardHealthState.MONITORING_BLOCKED:
            return StateTransitionResult(
                state=ForwardHealthState.INSUFFICIENT_EVIDENCE,
                recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
                consecutive_degraded_periods=0,
                consecutive_recovery_periods=0,
                recovery_cooldown_remaining=0,
                drift_flags=("TELEMETRY_RESTORED_RESET_TO_INSUFFICIENT_EVIDENCE",),
            )

        # Priority 5: Insufficient Evidence
        if metrics.observation_count < self.policy.min_observations:
            return StateTransitionResult(
                state=ForwardHealthState.INSUFFICIENT_EVIDENCE,
                recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
                consecutive_degraded_periods=0,
                consecutive_recovery_periods=0,
                recovery_cooldown_remaining=0,
                drift_flags=(),
            )

        # Determine whether current window metrics exhibit performance degradation
        is_period_degraded, detected_flags = self._detect_period_degradation(
            metrics=metrics,
            baseline_sharpe=baseline_sharpe,
        )

        # Rule 5: State Transitions under Asymmetric Anti-Whipsaw Hysteresis
        if current_state == ForwardHealthState.DEGRADED:
            if is_period_degraded:
                # Still degraded: reset recovery counters and refresh cooldown
                return StateTransitionResult(
                    state=ForwardHealthState.DEGRADED,
                    recommendation=ForwardGovernanceRecommendation.DEGRADED_PROBATION,
                    consecutive_degraded_periods=consecutive_degraded_periods + 1,
                    consecutive_recovery_periods=0,
                    recovery_cooldown_remaining=self.policy.recovery_cooldown_periods,
                    drift_flags=detected_flags,
                )
            else:
                # Period is healthy: increment recovery counter and decrement cooldown
                new_recovery_count = consecutive_recovery_periods + 1
                new_cooldown = max(0, recovery_cooldown_remaining - 1)

                if (
                    new_recovery_count >= self.policy.recovery_persistence_m
                    and new_cooldown == 0
                ):
                    # Full recovery criteria met under asymmetric hysteresis
                    return StateTransitionResult(
                        state=ForwardHealthState.HEALTHY,
                        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
                        consecutive_degraded_periods=0,
                        consecutive_recovery_periods=0,
                        recovery_cooldown_remaining=0,
                        drift_flags=("RECOVERY_CONFIRMED",),
                    )
                else:
                    # Pending recovery persistence or cooldown
                    return StateTransitionResult(
                        state=ForwardHealthState.DEGRADED,
                        recommendation=ForwardGovernanceRecommendation.DEGRADED_PROBATION,
                        consecutive_degraded_periods=0,
                        consecutive_recovery_periods=new_recovery_count,
                        recovery_cooldown_remaining=new_cooldown,
                        drift_flags=("RECOVERY_PENDING_PERSISTENCE",),
                    )

        else:
            # Current state is HEALTHY, INSUFFICIENT_EVIDENCE, or recovered MONITORING_BLOCKED
            if is_period_degraded:
                new_degraded_count = consecutive_degraded_periods + 1
                if new_degraded_count >= self.policy.degradation_persistence_n:
                    # Degradation persistence threshold reached -> transition to DEGRADED
                    return StateTransitionResult(
                        state=ForwardHealthState.DEGRADED,
                        recommendation=ForwardGovernanceRecommendation.DEGRADED_PROBATION,
                        consecutive_degraded_periods=new_degraded_count,
                        consecutive_recovery_periods=0,
                        recovery_cooldown_remaining=self.policy.recovery_cooldown_periods,
                        drift_flags=detected_flags,
                    )
                else:
                    # Degradation observed but pending persistence threshold
                    return StateTransitionResult(
                        state=ForwardHealthState.HEALTHY,
                        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
                        consecutive_degraded_periods=new_degraded_count,
                        consecutive_recovery_periods=0,
                        recovery_cooldown_remaining=0,
                        drift_flags=("DEGRADATION_PENDING_PERSISTENCE",) + detected_flags,
                    )
            else:
                # Healthy period
                return StateTransitionResult(
                    state=ForwardHealthState.HEALTHY,
                    recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
                    consecutive_degraded_periods=0,
                    consecutive_recovery_periods=0,
                    recovery_cooldown_remaining=0,
                    drift_flags=(),
                )

    def generate_evidence(
        self,
        strategy_id: str,
        dossier_digest: str,
        as_of_utc: datetime,
        wall_clock_utc: datetime,
        current_state: ForwardHealthState,
        metrics: ForwardWindowMetrics,
        consecutive_degraded_periods: int = 0,
        consecutive_recovery_periods: int = 0,
        recovery_cooldown_remaining: int = 0,
        is_telemetry_valid: bool = True,
        baseline_sharpe: Optional[Decimal] = None,
        evidence_id: Optional[str] = None,
    ) -> StrategyForwardDriftEvidence:
        """Evaluate state transition and construct canonical StrategyForwardDriftEvidence DTO."""
        step_result = self.evaluate_step(
            current_state=current_state,
            metrics=metrics,
            consecutive_degraded_periods=consecutive_degraded_periods,
            consecutive_recovery_periods=consecutive_recovery_periods,
            recovery_cooldown_remaining=recovery_cooldown_remaining,
            is_telemetry_valid=is_telemetry_valid,
            baseline_sharpe=baseline_sharpe,
        )

        eid = evidence_id if evidence_id is not None else f"EVID_{strategy_id}_{uuid.uuid4().hex[:12]}"

        return StrategyForwardDriftEvidence(
            evidence_id=eid,
            strategy_id=strategy_id,
            dossier_digest=dossier_digest,
            as_of_utc=as_of_utc,
            wall_clock_utc=wall_clock_utc,
            health_state=step_result.state,
            recommendation=step_result.recommendation,
            metrics=metrics,
            policy_digest=self.policy.policy_digest,
            consecutive_degraded_periods=step_result.consecutive_degraded_periods,
            consecutive_recovery_periods=step_result.consecutive_recovery_periods,
            drift_flags=step_result.drift_flags,
        )

    def _detect_period_degradation(
        self,
        metrics: ForwardWindowMetrics,
        baseline_sharpe: Optional[Decimal],
    ) -> Tuple[bool, Tuple[str, ...]]:
        """Detect whether window metrics breach degradation thresholds."""
        flags: list[str] = []

        # 1. Absolute Sharpe Floor Breach
        if metrics.realized_sharpe_ratio < self.policy.min_acceptable_sharpe:
            flags.append("SHARPE_BELOW_MINIMUM")

        # 2. Relative Sharpe Decay Breach
        if baseline_sharpe is not None and baseline_sharpe > Decimal("0.0"):
            decay_pct = (baseline_sharpe - metrics.realized_sharpe_ratio) / baseline_sharpe
            if decay_pct > self.policy.max_sharpe_decay_pct:
                flags.append("SHARPE_EXCESSIVE_DECAY")

        is_degraded = len(flags) > 0
        return is_degraded, tuple(flags)
