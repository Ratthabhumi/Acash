"""Unit tests for Phase 11 ForwardHealthStateMachine and asymmetric hysteresis.

Verifies:
1. Transition to INSUFFICIENT_EVIDENCE when observation count < min_observations.
2. Transition to HEALTHY upon reaching observation threshold with sound metrics.
3. Degradation anti-whipsaw hysteresis: requires N_degrade consecutive degraded periods.
4. Recovery asymmetric hysteresis: requires M_recover consecutive healthy periods AND cooldown expiration.
5. Immediate catastrophic STRUCTURAL_BREAK on inception HWM drawdown threshold breach.
6. Absorbing nature of STRUCTURAL_BREAK (market movement alone cannot auto-recover).
7. Infrastructure separation: MONITORING_BLOCKED on telemetry failure (not performance degradation).
8. Evidence generation: produces valid StrategyForwardDriftEvidence with Tier 1 digest and strictly ZERO is_tournament_eligible.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.monitoring.schema import (
    ForwardGovernanceRecommendation,
    ForwardHealthPolicy,
    ForwardHealthState,
    ForwardWindowMetrics,
    StrategyForwardDriftEvidence,
)
from acash.monitoring.state_machine import ForwardHealthStateMachine

VALID_DOSSIER_DIGEST = "d" * 64


def _create_sample_metrics(
    observation_count: int = 60,
    sharpe: Decimal = Decimal("1.50"),
    window_max_dd: Decimal = Decimal("0.05"),
    inception_max_dd: Decimal = Decimal("0.08"),
) -> ForwardWindowMetrics:
    return ForwardWindowMetrics(
        window_size=60,
        observation_count=observation_count,
        mean_realized_return_annualized=Decimal("0.18"),
        realized_volatility_annualized=Decimal("0.12"),
        realized_sharpe_ratio=sharpe,
        max_drawdown=window_max_dd,
        inception_max_drawdown=inception_max_dd,
        hit_rate=Decimal("0.55"),
        tracking_error_annualized=None,
        t_stat_decay=Decimal("2.10"),
        expected_vs_realized_divergence_bps=None,
        information_coefficient=None,
        ic_decay_slope=None,
    )


# ============================================================================
# 1. INSUFFICIENT EVIDENCE & HEALTHY TRANSITIONS
# ============================================================================

def test_state_machine_insufficient_evidence() -> None:
    """When observation count < min_observations (default 30), state is INSUFFICIENT_EVIDENCE."""
    policy = ForwardHealthPolicy()
    sm = ForwardHealthStateMachine(policy)

    metrics = _create_sample_metrics(observation_count=20)
    result = sm.evaluate_step(
        current_state=ForwardHealthState.INSUFFICIENT_EVIDENCE,
        metrics=metrics,
    )

    assert result.state == ForwardHealthState.INSUFFICIENT_EVIDENCE
    assert result.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED
    assert result.consecutive_degraded_periods == 0
    assert result.consecutive_recovery_periods == 0


def test_state_machine_transition_to_healthy() -> None:
    """When observation count reaches 30 with Sharpe >= 0.50, state transitions to HEALTHY."""
    policy = ForwardHealthPolicy()
    sm = ForwardHealthStateMachine(policy)

    metrics = _create_sample_metrics(observation_count=30, sharpe=Decimal("1.20"))
    result = sm.evaluate_step(
        current_state=ForwardHealthState.INSUFFICIENT_EVIDENCE,
        metrics=metrics,
    )

    assert result.state == ForwardHealthState.HEALTHY
    assert result.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED


# ============================================================================
# 2. DEGRADATION HYSTERESIS (N_degrade = 3)
# ============================================================================

def test_state_machine_degradation_anti_whipsaw_persistence() -> None:
    """Degradation requires N_degrade (3) consecutive degraded periods before leaving HEALTHY."""
    policy = ForwardHealthPolicy(degradation_persistence_n=3, recovery_persistence_m=10)
    sm = ForwardHealthStateMachine(policy)

    # Sub-par Sharpe ratio below policy.min_acceptable_sharpe (0.50)
    bad_metrics = _create_sample_metrics(observation_count=60, sharpe=Decimal("0.20"))

    # Period 1: First degraded period (N=1 < 3) -> remains HEALTHY
    res1 = sm.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=bad_metrics,
        consecutive_degraded_periods=0,
    )
    assert res1.state == ForwardHealthState.HEALTHY
    assert res1.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED
    assert res1.consecutive_degraded_periods == 1

    # Period 2: Second degraded period (N=2 < 3) -> remains HEALTHY
    res2 = sm.evaluate_step(
        current_state=res1.state,
        metrics=bad_metrics,
        consecutive_degraded_periods=res1.consecutive_degraded_periods,
    )
    assert res2.state == ForwardHealthState.HEALTHY
    assert res2.consecutive_degraded_periods == 2

    # Period 3: Third degraded period (N=3 == N_degrade) -> transitions to DEGRADED
    res3 = sm.evaluate_step(
        current_state=res2.state,
        metrics=bad_metrics,
        consecutive_degraded_periods=res2.consecutive_degraded_periods,
    )
    assert res3.state == ForwardHealthState.DEGRADED
    assert res3.recommendation == ForwardGovernanceRecommendation.DEGRADED_PROBATION
    assert res3.consecutive_degraded_periods == 3
    assert res3.recovery_cooldown_remaining == policy.recovery_cooldown_periods


# ============================================================================
# 3. RECOVERY ASYMMETRIC HYSTERESIS (M_recover = 10, T_cooldown = 5)
# ============================================================================

def test_state_machine_recovery_asymmetric_persistence_and_cooldown() -> None:
    """Recovery from DEGRADED requires M_recover (10) consecutive healthy periods AND cooldown == 0."""
    policy = ForwardHealthPolicy(
        degradation_persistence_n=3,
        recovery_persistence_m=10,
        recovery_cooldown_periods=5,
    )
    sm = ForwardHealthStateMachine(policy)
    good_metrics = _create_sample_metrics(observation_count=60, sharpe=Decimal("1.80"))

    # Start in DEGRADED with cooldown = 5
    curr_state = ForwardHealthState.DEGRADED
    recovery_count = 0
    cooldown = 5

    # Simulate 9 healthy periods (M=9 < 10)
    for _ in range(9):
        res = sm.evaluate_step(
            current_state=curr_state,
            metrics=good_metrics,
            consecutive_degraded_periods=0,
            consecutive_recovery_periods=recovery_count,
            recovery_cooldown_remaining=cooldown,
        )
        assert res.state == ForwardHealthState.DEGRADED
        assert res.recommendation == ForwardGovernanceRecommendation.DEGRADED_PROBATION
        recovery_count = res.consecutive_recovery_periods
        cooldown = res.recovery_cooldown_remaining

    assert recovery_count == 9
    assert cooldown == 0  # Cooldown decremented 5 -> 0 over 5 periods

    # 10th healthy period (M=10 == M_recover, cooldown == 0) -> Full recovery to HEALTHY
    res_final = sm.evaluate_step(
        current_state=ForwardHealthState.DEGRADED,
        metrics=good_metrics,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=recovery_count,
        recovery_cooldown_remaining=cooldown,
    )
    assert res_final.state == ForwardHealthState.HEALTHY
    assert res_final.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED
    assert res_final.consecutive_recovery_periods == 0


def test_state_machine_recovery_relapse_resets_counter() -> None:
    """A single degraded period during recovery resets recovery count to 0 and refreshes cooldown."""
    policy = ForwardHealthPolicy(degradation_persistence_n=3, recovery_persistence_m=10, recovery_cooldown_periods=5)
    sm = ForwardHealthStateMachine(policy)

    bad_metrics = _create_sample_metrics(observation_count=60, sharpe=Decimal("0.10"))

    # Currently in DEGRADED with 5 recovery periods accumulated
    res = sm.evaluate_step(
        current_state=ForwardHealthState.DEGRADED,
        metrics=bad_metrics,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=5,
        recovery_cooldown_remaining=1,
    )

    assert res.state == ForwardHealthState.DEGRADED
    assert res.consecutive_recovery_periods == 0
    assert res.consecutive_degraded_periods == 1
    assert res.recovery_cooldown_remaining == policy.recovery_cooldown_periods


# ============================================================================
# 4. CATASTROPHIC STRUCTURAL BREAK & ABSORBING STATE
# ============================================================================

def test_state_machine_immediate_catastrophic_structural_break() -> None:
    """Inception HWM drawdown >= critical_drawdown_limit (0.20) triggers STRUCTURAL_BREAK immediately."""
    policy = ForwardHealthPolicy(critical_drawdown_limit=Decimal("0.20"))
    sm = ForwardHealthStateMachine(policy)

    # Strategy is currently HEALTHY, but suffered a 22% inception drawdown
    catastrophic_metrics = _create_sample_metrics(
        observation_count=60,
        sharpe=Decimal("1.20"),
        inception_max_dd=Decimal("0.22"),
    )

    res = sm.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=catastrophic_metrics,
        consecutive_degraded_periods=0,
    )

    # Bypasses N_degrade lag immediately
    assert res.state == ForwardHealthState.STRUCTURAL_BREAK
    assert res.recommendation == ForwardGovernanceRecommendation.RECOMMEND_EXCLUSION
    assert "CRITICAL_DRAWDOWN_BREACH" in res.drift_flags


def test_state_machine_structural_break_is_absorbing() -> None:
    """Once in STRUCTURAL_BREAK, subsequent healthy performance cannot auto-recover the strategy."""
    policy = ForwardHealthPolicy(critical_drawdown_limit=Decimal("0.20"))
    sm = ForwardHealthStateMachine(policy)

    healthy_metrics = _create_sample_metrics(
        observation_count=60,
        sharpe=Decimal("2.50"),
        inception_max_dd=Decimal("0.15"),  # Drawdown appears recovered
    )

    res = sm.evaluate_step(
        current_state=ForwardHealthState.STRUCTURAL_BREAK,
        metrics=healthy_metrics,
    )

    assert res.state == ForwardHealthState.STRUCTURAL_BREAK
    assert res.recommendation == ForwardGovernanceRecommendation.RECOMMEND_EXCLUSION
    assert "ABSORBING_STRUCTURAL_BREAK" in res.drift_flags


# ============================================================================
# 5. INFRASTRUCTURE / TELEMETRY SEPARATION (MONITORING_BLOCKED)
# ============================================================================

def test_state_machine_telemetry_failure_triggers_monitoring_blocked() -> None:
    """Telemetry failure (is_telemetry_valid=False) triggers MONITORING_BLOCKED, not performance degradation."""
    policy = ForwardHealthPolicy()
    sm = ForwardHealthStateMachine(policy)

    metrics = _create_sample_metrics()
    res = sm.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics,
        is_telemetry_valid=False,
    )

    assert res.state == ForwardHealthState.MONITORING_BLOCKED
    assert res.recommendation == ForwardGovernanceRecommendation.MONITORING_BLOCKED_FLAG
    assert "TELEMETRY_CORRUPTED" in res.drift_flags


# ============================================================================
# 6. EVIDENCE GENERATION & AUTHORITY ISOLATION
# ============================================================================

def test_generate_evidence_dto_clean_lineage_and_no_authority_creep() -> None:
    """Verify generate_evidence produces valid StrategyForwardDriftEvidence with zero authority creep."""
    policy = ForwardHealthPolicy()
    sm = ForwardHealthStateMachine(policy)
    metrics = _create_sample_metrics(observation_count=60, sharpe=Decimal("1.50"))

    t0 = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)

    evidence = sm.generate_evidence(
        strategy_id="STRAT_MOMENTUM_01",
        dossier_digest=VALID_DOSSIER_DIGEST,
        as_of_utc=t0,
        wall_clock_utc=t0,
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics,
    )

    assert isinstance(evidence, StrategyForwardDriftEvidence)
    assert evidence.health_state == ForwardHealthState.HEALTHY
    assert evidence.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED
    assert len(evidence.evidence_digest) == 64
    # Authority isolation: strictly no tournament eligibility on evidence
    assert not hasattr(evidence, "is_tournament_eligible")
