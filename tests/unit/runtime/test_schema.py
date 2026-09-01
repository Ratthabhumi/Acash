"""Unit and adversarial tests for Phase 10 Operational Domain Contracts & Configuration (Slice 1).

Tests:
- RuntimeRegime, RuntimeHealthStatus, CycleOutcome enums.
- RuntimeHealthStatus != KillSwitchState domain separation.
- Dual-Clock discipline: as_of_utc vs wall_clock_utc, rejection of naive/inverted timestamps.
- CycleIdentity deterministic hashing, immutability, and uniqueness.
- RuntimePolicyConfig validation, positive bounds, and canonical digest.
- OperationalCycleEvent envelope, SHA-256 digest validation, and hash chaining.
- Authority boundary verification: Zero execution or broker wire methods.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.risk.risk_schema import KillSwitchState
from acash.runtime.schema import (
    CycleIdentity,
    CycleOutcome,
    OperationalCycleEvent,
    RuntimeHealthStatus,
    RuntimePolicyConfig,
    RuntimeRegime,
    _ensure_utc,
    _validate_sha256,
)


# ============================================================================
# 1. ENUM & STATE MACHINE SEPARATION TESTS
# ============================================================================


def test_runtime_regime_enum_values() -> None:
    assert RuntimeRegime.PRE_MARKET.value == "PRE_MARKET"
    assert RuntimeRegime.MARKET_OPEN.value == "MARKET_OPEN"
    assert RuntimeRegime.REBALANCE_PULSE.value == "REBALANCE_PULSE"
    assert RuntimeRegime.POST_MARKET_CLOSE.value == "POST_MARKET_CLOSE"
    assert RuntimeRegime.MAINTENANCE.value == "MAINTENANCE"


def test_runtime_health_status_distinct_from_kill_switch_state() -> None:
    """Invariant: RuntimeHealthStatus is strictly decoupled from Phase 9 KillSwitchState."""
    assert RuntimeHealthStatus.RUNTIME_HEALTHY.value == "RUNTIME_HEALTHY"
    assert RuntimeHealthStatus.RUNTIME_DEGRADED.value == "RUNTIME_DEGRADED"
    assert RuntimeHealthStatus.RUNTIME_PAUSED.value == "RUNTIME_PAUSED"
    assert RuntimeHealthStatus.RUNTIME_HALTED.value == "RUNTIME_HALTED"

    # RuntimeHealthStatus is not KillSwitchState
    assert not issubclass(RuntimeHealthStatus, KillSwitchState)
    assert not issubclass(KillSwitchState, RuntimeHealthStatus)


def test_cycle_outcome_enum_values() -> None:
    assert CycleOutcome.SUCCESS.value == "SUCCESS"
    assert CycleOutcome.RISK_REJECTED.value == "RISK_REJECTED"
    assert CycleOutcome.DATA_STALE.value == "DATA_STALE"
    assert CycleOutcome.DISPATCH_FAILED.value == "DISPATCH_FAILED"
    assert CycleOutcome.INTERRUPTED_CRASH.value == "INTERRUPTED_CRASH"
    assert CycleOutcome.IDEMPOTENT_SKIPPED.value == "IDEMPOTENT_SKIPPED"


# ============================================================================
# 2. DUAL-CLOCK DISCIPLINE & TIME VALIDATION TESTS
# ============================================================================


def test_ensure_utc_accepts_timezone_aware_datetime() -> None:
    dt = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    verified = _ensure_utc(dt)
    assert verified.tzinfo == timezone.utc
    assert verified == dt


def test_ensure_utc_rejects_naive_datetime() -> None:
    naive_dt = datetime(2026, 9, 2, 14, 0, 0)  # No tzinfo
    with pytest.raises(DataContractError, match="must be timezone-aware UTC"):
        _ensure_utc(naive_dt)


def test_ensure_utc_parses_iso_string() -> None:
    iso_str = "2026-09-02T14:00:00+00:00"
    verified = _ensure_utc(iso_str)
    assert verified.tzinfo == timezone.utc
    assert verified.year == 2026


# ============================================================================
# 3. CYCLE IDENTITY & DETERMINISTIC HASHING TESTS
# ============================================================================


def test_cycle_identity_deterministic_digest() -> None:
    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    cid1 = CycleIdentity(
        cycle_id="CYCLE_REBALANCE_001",
        as_of_utc=as_of,
        regime=RuntimeRegime.REBALANCE_PULSE,
        sequence_number=1,
    )
    cid2 = CycleIdentity(
        cycle_id="CYCLE_REBALANCE_001",
        as_of_utc=as_of,
        regime=RuntimeRegime.REBALANCE_PULSE,
        sequence_number=1,
    )

    assert len(cid1.cycle_digest) == 64
    assert cid1.cycle_digest == cid2.cycle_digest


def test_cycle_identity_distinct_for_different_as_of() -> None:
    cid1 = CycleIdentity(
        cycle_id="CYCLE_REBALANCE_001",
        as_of_utc=datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc),
        regime=RuntimeRegime.REBALANCE_PULSE,
        sequence_number=1,
    )
    cid2 = CycleIdentity(
        cycle_id="CYCLE_REBALANCE_001",
        as_of_utc=datetime(2026, 9, 2, 14, 1, 0, tzinfo=timezone.utc),  # 1 minute later
        regime=RuntimeRegime.REBALANCE_PULSE,
        sequence_number=1,
    )

    assert cid1.cycle_digest != cid2.cycle_digest


def test_cycle_identity_rejects_empty_id_or_negative_seq() -> None:
    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(DataContractError, match="cycle_id must be a non-empty string"):
        CycleIdentity(
            cycle_id="",
            as_of_utc=as_of,
            regime=RuntimeRegime.REBALANCE_PULSE,
        )

    with pytest.raises(DataContractError, match="sequence_number must be non-negative"):
        CycleIdentity(
            cycle_id="CYCLE_001",
            as_of_utc=as_of,
            regime=RuntimeRegime.REBALANCE_PULSE,
            sequence_number=-1,
        )


def test_cycle_identity_immutability() -> None:
    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    cid = CycleIdentity(
        cycle_id="CYCLE_001",
        as_of_utc=as_of,
        regime=RuntimeRegime.REBALANCE_PULSE,
    )
    with pytest.raises(Exception):  # Frozen instance assignment
        setattr(cid, "cycle_id", "NEW_ID")


# ============================================================================
# 4. RUNTIME POLICY CONFIGURATION TESTS
# ============================================================================


def test_runtime_policy_config_defaults_and_digest() -> None:
    policy = RuntimePolicyConfig()
    assert policy.policy_version == "v1.0.0"
    assert policy.heartbeat_interval_seconds == 5
    assert policy.max_market_data_age_ms == 1500
    assert policy.max_clock_drift_ms == 500
    assert len(policy.policy_digest) == 64


def test_runtime_policy_config_rejects_invalid_bounds() -> None:
    with pytest.raises(DataContractError, match="Numeric runtime policy parameters violate required positive bounds"):
        RuntimePolicyConfig(heartbeat_interval_seconds=0)

    with pytest.raises(DataContractError, match="Numeric runtime policy parameters violate required positive bounds"):
        RuntimePolicyConfig(max_market_data_age_ms=50)  # Min is 100ms


def test_runtime_policy_config_immutability_and_extra_forbid() -> None:
    policy = RuntimePolicyConfig()
    with pytest.raises(Exception):
        setattr(policy, "policy_version", "v2.0.0")

    with pytest.raises(Exception):
        RuntimePolicyConfig(extra_param=123)  # type: ignore[call-arg]


# ============================================================================
# 5. OPERATIONAL EVENT ENVELOPE TESTS
# ============================================================================


def test_operational_cycle_event_valid_happy_path() -> None:
    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    cid = CycleIdentity(
        cycle_id="CYCLE_001",
        as_of_utc=as_of,
        regime=RuntimeRegime.REBALANCE_PULSE,
        sequence_number=1,
    )

    valid_hash = hashlib.sha256(b"state").hexdigest()
    event = OperationalCycleEvent(
        cycle_identity=cid,
        wall_clock_utc=wall_clock,
        runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
        portfolio_state_digest=valid_hash,
        account_state_digest=valid_hash,
        allocation_decision_digest=valid_hash,
        risk_report_digest=valid_hash,
        cycle_outcome=CycleOutcome.SUCCESS,
        previous_event_digest="0" * 64,
    )

    assert event.cycle_identity == cid
    assert event.runtime_health == RuntimeHealthStatus.RUNTIME_HEALTHY
    assert event.cycle_outcome == CycleOutcome.SUCCESS
    assert len(event.event_digest) == 64


def test_operational_cycle_event_rejects_temporal_inversion() -> None:
    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock_inverted = datetime(2026, 9, 2, 13, 59, 59, tzinfo=timezone.utc)  # Before as_of!

    cid = CycleIdentity(
        cycle_id="CYCLE_001",
        as_of_utc=as_of,
        regime=RuntimeRegime.REBALANCE_PULSE,
        sequence_number=1,
    )

    with pytest.raises(DataContractError, match="Temporal Inversion"):
        OperationalCycleEvent(
            cycle_identity=cid,
            wall_clock_utc=wall_clock_inverted,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            cycle_outcome=CycleOutcome.SUCCESS,
        )


def test_operational_cycle_event_rejects_malformed_digests() -> None:
    as_of = datetime(2026, 9, 2, 14, 0, 0, tzinfo=timezone.utc)
    wall_clock = datetime(2026, 9, 2, 14, 0, 1, tzinfo=timezone.utc)

    cid = CycleIdentity(
        cycle_id="CYCLE_001",
        as_of_utc=as_of,
        regime=RuntimeRegime.REBALANCE_PULSE,
    )

    with pytest.raises(DataContractError, match="Invalid previous_event_digest"):
        OperationalCycleEvent(
            cycle_identity=cid,
            wall_clock_utc=wall_clock,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            cycle_outcome=CycleOutcome.SUCCESS,
            previous_event_digest="not_a_sha256",
        )


# ============================================================================
# 6. AUTHORITY BOUNDARY TESTS
# ============================================================================


def test_schema_zero_broker_execution_authority() -> None:
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
        assert not hasattr(CycleIdentity, m)
        assert not hasattr(RuntimePolicyConfig, m)
        assert not hasattr(OperationalCycleEvent, m)
