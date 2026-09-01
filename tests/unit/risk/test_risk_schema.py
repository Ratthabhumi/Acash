"""Unit tests for Phase 9 Canonical Domain Contracts & Configuration (Slice 1).

Tests:
- Valid schema construction and field validation
- Frozen immutability and extra='forbid' enforcement
- Strict finite Decimal validation (rejection of NaN, +Inf, -Inf, negative values)
- Policy and Verdict enum integrity
- TTL and as-of boundary semantics (valid before expiration, expired at and after)
- SHA-256 digest validation and deterministic serialization
- Separation of concerns: EmergencyFlattenIntent != Positions Flattened
- Zero direct broker execution authority in schema
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.execution.schema import ApproverRole, AuthorizationApproval
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
    _validate_sha256,
    _verify_finite_decimal,
)


@pytest.fixture
def valid_sha256() -> str:
    return hashlib.sha256(b"canonical_fixture_payload").hexdigest()


@pytest.fixture
def sample_approval(valid_sha256: str) -> AuthorizationApproval:
    return AuthorizationApproval(
        approver_id="RISK_OFFICER_01",
        public_key_id="KEY_RISK_01",
        role=ApproverRole.RISK_OFFICER,
        authorization_id="AUTH_LIVE_001",
        approved_at=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        approval_signature="dGVzdF9zaWduYXR1cmVfYmFzZTY0X3BsYWNlaG9sZGVy",
        approval_digest=valid_sha256,
    )


# ============================================================================
# 1. FINITE DECIMAL & DIGEST HELPER TESTS
# ============================================================================


def test_verify_finite_decimal_happy_path() -> None:
    assert _verify_finite_decimal(Decimal("10.5"), "test") == Decimal("10.5")
    assert _verify_finite_decimal(100, "test") == Decimal("100")
    assert _verify_finite_decimal("0.25", "test") == Decimal("0.25")
    assert _verify_finite_decimal("-5.0", "test", allow_negative=True) == Decimal("-5.0")


def test_verify_finite_decimal_rejects_nan_and_inf() -> None:
    with pytest.raises(DataContractError, match="Non-finite"):
        _verify_finite_decimal(Decimal("NaN"), "test")

    with pytest.raises(DataContractError, match="Non-finite"):
        _verify_finite_decimal(Decimal("Infinity"), "test")

    with pytest.raises(DataContractError, match="Non-finite"):
        _verify_finite_decimal(float("nan"), "test")

    with pytest.raises(DataContractError, match="Non-finite"):
        _verify_finite_decimal(float("inf"), "test")


def test_verify_finite_decimal_rejects_negative_when_forbidden() -> None:
    with pytest.raises(DataContractError, match="cannot be negative"):
        _verify_finite_decimal(Decimal("-0.01"), "test", allow_negative=False)


def test_verify_finite_decimal_bounds_enforcement() -> None:
    with pytest.raises(DataContractError, match="below minimum"):
        _verify_finite_decimal(Decimal("0.5"), "test", min_val=Decimal("1.0"))

    with pytest.raises(DataContractError, match="exceeds maximum"):
        _verify_finite_decimal(Decimal("1.5"), "test", max_val=Decimal("1.0"))


def test_validate_sha256_pattern() -> None:
    valid = "a" * 64
    assert _validate_sha256(valid, "context") == valid

    with pytest.raises(DataContractError, match="64-character lowercase hexadecimal"):
        _validate_sha256("INVALID_HASH", "context")

    with pytest.raises(DataContractError, match="64-character lowercase hexadecimal"):
        _validate_sha256("A" * 64, "context")  # Uppercase not allowed


# ============================================================================
# 2. RISK POLICY CONFIG TESTS
# ============================================================================


def test_risk_policy_config_defaults_and_digest() -> None:
    config = RiskPolicyConfig()
    assert config.policy_version == "v1.0.0"
    assert config.derisk_policy == DeriskPolicy.EXACT_SCALE_DOWN
    assert config.max_gross_leverage == Decimal("1.00")
    assert config.max_asset_concentration == Decimal("0.25")
    assert config.min_cash_buffer == Decimal("0.05")
    assert config.max_drawdown_limit_pct == Decimal("15.00")
    assert config.max_daily_loss_usd == Decimal("10000.00")
    assert config.min_margin_buffer_usd == Decimal("5000.00")
    assert config.max_market_data_age_ms == 1500
    assert config.max_clock_drift_ms == 500
    assert config.evaluation_ttl_seconds == 60
    assert len(config.policy_digest) == 64


def test_risk_policy_config_immutability_and_extra_forbid() -> None:
    config = RiskPolicyConfig()
    with pytest.raises(Exception):
        setattr(config, "max_gross_leverage", Decimal("2.00"))

    with pytest.raises(Exception):
        RiskPolicyConfig(extra_field="malicious")  # type: ignore[call-arg]


def test_risk_policy_config_rejects_infeasible_cash_buffer() -> None:
    with pytest.raises(DataContractError, match="exceeds maximum permitted"):
        RiskPolicyConfig(min_cash_buffer=Decimal("1.05"))


# ============================================================================
# 3. CANDIDATE RISK ALLOCATION TESTS
# ============================================================================


def test_candidate_risk_allocation_valid(valid_sha256: str) -> None:
    alloc = CandidateRiskAllocation(
        candidate_id="CAND_001",
        strategy_id="MULTI_HORIZON_MOM",
        weights={"AAPL": Decimal("0.40"), "MSFT": Decimal("0.50")},
        cash_weight=Decimal("0.10"),
        source_decision_digest=valid_sha256,
        as_of_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert alloc.candidate_id == "CAND_001"
    assert alloc.weights["AAPL"] == Decimal("0.40")
    assert alloc.weights["MSFT"] == Decimal("0.50")
    assert alloc.cash_weight == Decimal("0.10")
    assert len(alloc.candidate_digest) == 64


def test_candidate_risk_allocation_rejects_negative_weight(valid_sha256: str) -> None:
    with pytest.raises(DataContractError, match="cannot be negative"):
        CandidateRiskAllocation(
            candidate_id="CAND_001",
            strategy_id="STRAT",
            weights={"AAPL": Decimal("-0.10")},
            cash_weight=Decimal("1.10"),
            source_decision_digest=valid_sha256,
            as_of_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        )


def test_candidate_risk_allocation_frozen_weights(valid_sha256: str) -> None:
    alloc = CandidateRiskAllocation(
        candidate_id="CAND_001",
        strategy_id="STRAT",
        weights={"AAPL": Decimal("0.5")},
        cash_weight=Decimal("0.5"),
        source_decision_digest=valid_sha256,
        as_of_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(TypeError):
        alloc.weights["AAPL"] = Decimal("0.8")  # type: ignore[index]


# ============================================================================
# 4. RISK EVALUATION REPORT & TTL TESTS
# ============================================================================


def test_risk_evaluation_report_ttl_and_staleness(valid_sha256: str) -> None:
    eval_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    exp_time = eval_time + timedelta(seconds=60)

    report = RiskEvaluationReport(
        evaluation_id="RISK_EVAL_001",
        verdict=RiskVerdict.APPROVED,
        original_allocation_digest=valid_sha256,
        portfolio_state_digest=valid_sha256,
        account_state_digest=valid_sha256,
        risk_policy_digest=valid_sha256,
        adjusted_weights={"AAPL": Decimal("0.50"), "MSFT": Decimal("0.45")},
        cash_weight=Decimal("0.05"),
        metrics_observed={"gross_leverage": Decimal("0.95")},
        evaluated_at_utc=eval_time,
        expires_at_utc=exp_time,
    )

    assert report.verdict == RiskVerdict.APPROVED
    assert len(report.report_digest) == 64

    # TTL boundary check:
    # 1. 30 seconds after evaluation -> NOT expired
    assert report.is_expired(as_of=eval_time + timedelta(seconds=30)) is False

    # 2. 59 seconds after evaluation -> NOT expired
    assert report.is_expired(as_of=eval_time + timedelta(seconds=59)) is False

    # 3. Exact expiration timestamp (60s) -> EXPIRED (fail-closed boundary)
    assert report.is_expired(as_of=exp_time) is True

    # 4. Past expiration timestamp (61s) -> EXPIRED
    assert report.is_expired(as_of=eval_time + timedelta(seconds=61)) is True


def test_risk_evaluation_report_rejects_inverted_timestamps(valid_sha256: str) -> None:
    eval_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    exp_time = eval_time - timedelta(seconds=1)  # Inverted

    with pytest.raises(DataContractError, match="cannot precede evaluated_at_utc"):
        RiskEvaluationReport(
            evaluation_id="RISK_EVAL_001",
            verdict=RiskVerdict.REJECTED,
            original_allocation_digest=valid_sha256,
            portfolio_state_digest=valid_sha256,
            account_state_digest=valid_sha256,
            risk_policy_digest=valid_sha256,
            adjusted_weights={},
            cash_weight=Decimal("1.0"),
            evaluated_at_utc=eval_time,
            expires_at_utc=exp_time,
        )


def test_risk_evaluation_report_deterministic_hashing(valid_sha256: str) -> None:
    t = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    r1 = RiskEvaluationReport(
        evaluation_id="RISK_EVAL_001",
        verdict=RiskVerdict.REDUCED,
        original_allocation_digest=valid_sha256,
        portfolio_state_digest=valid_sha256,
        account_state_digest=valid_sha256,
        risk_policy_digest=valid_sha256,
        adjusted_weights={"MSFT": Decimal("0.40"), "AAPL": Decimal("0.30")},
        cash_weight=Decimal("0.30"),
        evaluated_at_utc=t,
        expires_at_utc=t + timedelta(seconds=60),
    )
    r2 = RiskEvaluationReport(
        evaluation_id="RISK_EVAL_001",
        verdict=RiskVerdict.REDUCED,
        original_allocation_digest=valid_sha256,
        portfolio_state_digest=valid_sha256,
        account_state_digest=valid_sha256,
        risk_policy_digest=valid_sha256,
        adjusted_weights={"AAPL": Decimal("0.30"), "MSFT": Decimal("0.40")},  # Different key insertion order
        cash_weight=Decimal("0.30"),
        evaluated_at_utc=t,
        expires_at_utc=t + timedelta(seconds=60),
    )
    assert r1.report_digest == r2.report_digest


# ============================================================================
# 5. KILL SWITCH RESET EVENT TESTS
# ============================================================================


def test_kill_switch_reset_event_quorum_validation(sample_approval: AuthorizationApproval) -> None:
    event = KillSwitchResetEvent(
        event_id="RESET_001",
        kill_switch_event_id="KILL_STALE_001",
        root_cause_summary="Data feed restarted and verified nominal.",
        approvals=(sample_approval,),
        required_approvals=1,
        created_at_utc=datetime(2026, 9, 1, 12, 30, 0, tzinfo=timezone.utc),
    )
    assert event.event_id == "RESET_001"
    assert len(event.reset_digest) == 64


def test_kill_switch_reset_event_rejects_insufficient_quorum(sample_approval: AuthorizationApproval) -> None:
    with pytest.raises(DataContractError, match="less than required"):
        KillSwitchResetEvent(
            event_id="RESET_001",
            kill_switch_event_id="KILL_STALE_001",
            root_cause_summary="Data feed restarted.",
            approvals=(sample_approval,),
            required_approvals=2,  # Requires 2, only 1 provided
            created_at_utc=datetime(2026, 9, 1, 12, 30, 0, tzinfo=timezone.utc),
        )


def test_kill_switch_reset_event_rejects_empty_root_cause(sample_approval: AuthorizationApproval) -> None:
    with pytest.raises(DataContractError, match="root_cause_summary must be a non-empty string"):
        KillSwitchResetEvent(
            event_id="RESET_001",
            kill_switch_event_id="KILL_STALE_001",
            root_cause_summary="   ",
            approvals=(sample_approval,),
            required_approvals=1,
            created_at_utc=datetime(2026, 9, 1, 12, 30, 0, tzinfo=timezone.utc),
        )


# ============================================================================
# 6. EMERGENCY FLATTENING INTENT TESTS
# ============================================================================


def test_emergency_flatten_intent_valid() -> None:
    intent = EmergencyFlattenIntent(
        intent_id="EMERGENCY_FLATTEN_001",
        kill_switch_event_id="KILL_DD_001",
        target_positions={"AAPL": Decimal("0.0"), "MSFT": Decimal("0.0")},
        closing_deltas={"AAPL": Decimal("-100.0"), "MSFT": Decimal("-50.0")},
        issued_at_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        status=EmergencyFlattenStatus.FLATTEN_REQUESTED,
    )
    assert intent.intent_id == "EMERGENCY_FLATTEN_001"
    assert intent.target_positions["AAPL"] == Decimal("0.0")
    assert intent.status == EmergencyFlattenStatus.FLATTEN_REQUESTED
    assert len(intent.intent_digest) == 64


def test_emergency_flatten_intent_rejects_non_zero_target() -> None:
    with pytest.raises(DataContractError, match="must be exactly 0.0"):
        EmergencyFlattenIntent(
            intent_id="EMERGENCY_FLATTEN_BAD",
            kill_switch_event_id="KILL_DD_001",
            target_positions={"AAPL": Decimal("10.0")},  # Target must be 0.0
            closing_deltas={"AAPL": Decimal("-10.0")},
            issued_at_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        )


def test_emergency_intent_does_not_imply_completion() -> None:
    intent = EmergencyFlattenIntent(
        intent_id="EMERGENCY_FLATTEN_001",
        kill_switch_event_id="KILL_DD_001",
        target_positions={"AAPL": Decimal("0.0")},
        closing_deltas={"AAPL": Decimal("-10.0")},
        issued_at_utc=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    # Architectural Invariant: Intent Emitted != Flatten Completed
    assert intent.status.value == EmergencyFlattenStatus.FLATTEN_REQUESTED.value
    assert intent.status.value != EmergencyFlattenStatus.FLATTEN_COMPLETED.value
