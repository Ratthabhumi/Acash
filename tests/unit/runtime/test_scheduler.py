"""Unit and adversarial tests for Phase 10 Operational Clock & Cadence Scheduler (Slice 2).

Tests:
- Operational regime determination across session timeline (weekday vs weekend).
- Pulse due detection strictly aligned with REBALANCE_PULSE window.
- Cycle start and complete lifecycle.
- Overlapping cycle prevention (CYCLE_LOCKED_BUSY).
- Duplicate cycle detection and idempotency enforcement.
- Clock rollback and temporal inversion fail-closed defense.
- Sequence counter monotonicity.
- Zero broker execution authority on OperationalScheduler.
"""

from datetime import datetime, timedelta, timezone
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.runtime.scheduler import OperationalScheduler
from acash.runtime.schema import (
    CycleIdentity,
    CycleOutcome,
    RuntimePolicyConfig,
    RuntimeRegime,
)


# ============================================================================
# 1. REGIME DETERMINATION TESTS
# ============================================================================


def test_scheduler_determines_regimes_weekday() -> None:
    scheduler = OperationalScheduler()

    # Wednesday 2026-09-02
    pre_mkt = datetime(2026, 9, 2, 8, 0, 0, tzinfo=timezone.utc)
    mkt_open = datetime(2026, 9, 2, 13, 45, 0, tzinfo=timezone.utc)
    rebalance = datetime(2026, 9, 2, 14, 2, 0, tzinfo=timezone.utc)
    post_mkt = datetime(2026, 9, 2, 20, 15, 0, tzinfo=timezone.utc)
    maint = datetime(2026, 9, 2, 22, 0, 0, tzinfo=timezone.utc)

    assert scheduler.determine_regime(pre_mkt) == RuntimeRegime.PRE_MARKET
    assert scheduler.determine_regime(mkt_open) == RuntimeRegime.MARKET_OPEN
    assert scheduler.determine_regime(rebalance) == RuntimeRegime.REBALANCE_PULSE
    assert scheduler.determine_regime(post_mkt) == RuntimeRegime.POST_MARKET_CLOSE
    assert scheduler.determine_regime(maint) == RuntimeRegime.MAINTENANCE


def test_scheduler_determines_regime_weekend_maintenance() -> None:
    scheduler = OperationalScheduler()

    # Saturday 2026-09-05
    sat = datetime(2026, 9, 5, 14, 2, 0, tzinfo=timezone.utc)
    assert scheduler.determine_regime(sat) == RuntimeRegime.MAINTENANCE

    # Sunday 2026-09-06
    sun = datetime(2026, 9, 6, 8, 0, 0, tzinfo=timezone.utc)
    assert scheduler.determine_regime(sun) == RuntimeRegime.MAINTENANCE


def test_scheduler_is_pulse_due() -> None:
    scheduler = OperationalScheduler()

    rebalance_time = datetime(2026, 9, 2, 14, 1, 0, tzinfo=timezone.utc)
    non_rebalance_time = datetime(2026, 9, 2, 13, 45, 0, tzinfo=timezone.utc)

    assert scheduler.is_pulse_due(rebalance_time) is True
    assert scheduler.is_pulse_due(non_rebalance_time) is False


# ============================================================================
# 2. CYCLE LIFECYCLE & CONCURRENCY TESTS
# ============================================================================


def test_scheduler_cycle_start_and_complete_lifecycle() -> None:
    scheduler = OperationalScheduler(initial_sequence=10)
    assert scheduler.current_sequence == 10
    assert scheduler.is_cycle_active is False

    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    cid = scheduler.start_cycle("CYCLE_001", as_of, wall_clock)
    assert scheduler.is_cycle_active is True
    assert scheduler.active_cycle == cid
    assert cid.sequence_number == 10

    # Complete cycle
    complete_wall = datetime(2026, 9, 2, 14, 0, 5, tzinfo=timezone.utc)
    scheduler.complete_cycle("CYCLE_001", CycleOutcome.SUCCESS, complete_wall)

    assert scheduler.is_cycle_active is False
    assert scheduler.active_cycle is None
    assert scheduler.current_sequence == 11
    assert scheduler.is_duplicate_cycle(cid) is True


def test_scheduler_prevents_overlapping_cycles_busy() -> None:
    scheduler = OperationalScheduler()

    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    scheduler.start_cycle("CYCLE_001", as_of, wall_clock)

    # Attempt to start a second cycle while CYCLE_001 is running
    with pytest.raises(DataContractError, match="CYCLE_LOCKED_BUSY"):
        scheduler.start_cycle("CYCLE_002", as_of, wall_clock)


def test_scheduler_rejects_replaying_completed_cycle() -> None:
    scheduler = OperationalScheduler()

    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    scheduler.start_cycle("CYCLE_001", as_of, wall_clock)
    scheduler.complete_cycle("CYCLE_001", CycleOutcome.SUCCESS, wall_clock + timedelta(seconds=2))

    # Attempt to start the exact same cycle again -> Idempotent rejection
    with pytest.raises(DataContractError, match="IDEMPOTENT_DUPLICATE_CYCLE"):
        scheduler.start_cycle("CYCLE_001", as_of, wall_clock + timedelta(seconds=3))


def test_scheduler_complete_cycle_validates_mismatch_or_no_cycle() -> None:
    scheduler = OperationalScheduler()
    wall = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(DataContractError, match="No active cycle to complete"):
        scheduler.complete_cycle("CYCLE_NONE", CycleOutcome.SUCCESS, wall)

    scheduler.start_cycle("CYCLE_001", wall, wall)
    with pytest.raises(DataContractError, match="Cycle mismatch on complete"):
        scheduler.complete_cycle("CYCLE_WRONG", CycleOutcome.SUCCESS, wall)


# ============================================================================
# 3. CLOCK ANOMALY & FAIL-CLOSED DEFENSE TESTS
# ============================================================================


def test_scheduler_rejects_temporal_inversion() -> None:
    scheduler = OperationalScheduler()
    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock_inverted = datetime(2026, 9, 2, 13, 59, 59, tzinfo=timezone.utc)

    with pytest.raises(DataContractError, match="Temporal Inversion"):
        scheduler.start_cycle("CYCLE_001", as_of, wall_clock_inverted)


def test_scheduler_rejects_wall_clock_rollback() -> None:
    policy = RuntimePolicyConfig(max_clock_drift_ms=500)
    scheduler = OperationalScheduler(policy_config=policy)

    as_of1 = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall1 = datetime(2026, 9, 2, 14, 0, 10, tzinfo=timezone.utc)
    scheduler.start_cycle("CYCLE_001", as_of1, wall1)
    scheduler.complete_cycle("CYCLE_001", CycleOutcome.SUCCESS, wall1)

    # Rollback wall_clock by 2 seconds (wall_rollback 14:00:08 < wall1 14:00:10 - 500ms, but >= as_of2 14:00:05)
    as_of2 = datetime(2026, 9, 2, 14, 0, 5, tzinfo=timezone.utc)
    wall_rollback = datetime(2026, 9, 2, 14, 0, 8, tzinfo=timezone.utc)

    with pytest.raises(DataContractError, match="Clock Rollback Detected"):
        scheduler.start_cycle("CYCLE_002", as_of2, wall_rollback)


def test_scheduler_rejects_non_monotonic_as_of() -> None:
    scheduler = OperationalScheduler()

    as_of1 = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall1 = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)
    scheduler.start_cycle("CYCLE_001", as_of1, wall1)
    scheduler.complete_cycle("CYCLE_001", CycleOutcome.SUCCESS, wall1)

    # Inverted as_of
    as_of_inverted = datetime(2026, 9, 2, 13, 50, 0, tzinfo=timezone.utc)
    wall2 = datetime(2026, 9, 2, 14, 0, 5, tzinfo=timezone.utc)

    with pytest.raises(DataContractError, match="Monotonic As-Of Violation"):
        scheduler.start_cycle("CYCLE_002", as_of_inverted, wall2)


# ============================================================================
# 4. AUTHORITY BOUNDARY TESTS
# ============================================================================


def test_scheduler_zero_broker_execution_authority() -> None:
    forbidden = [
        "submit_order",
        "execute_order",
        "cancel_order",
        "send_wire",
        "get_broker_client",
        "evaluate_risk",
        "optimize_portfolio",
    ]
    for m in forbidden:
        assert not hasattr(OperationalScheduler, m)
