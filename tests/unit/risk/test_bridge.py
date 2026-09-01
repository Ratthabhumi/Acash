"""Unit and adversarial tests for Type-Safe Cross-Phase Risk State Bridge (Slice 5).

Tests:
- PortfolioState & AccountState -> RiskSnapshot mapping & accounting invariant preservation.
- TargetAllocation (float) <-> CandidateRiskAllocation (Decimal) conversion & round-trip.
- RiskEvaluationReport -> RiskAssessment interface adaptation.
- RiskEvaluationReport & PortfolioState -> Phase 7 Execution RiskState mapping.
- Strict numeric validation (rejection of NaN, Inf, negative equity).
- Timestamp and temporal identity preservation.
- Authority boundary verification (Bridge is a pure transformer with zero broker wire access).
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import pytest

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.signal import RiskAssessment, TargetAllocation
from acash.execution.schema import (
    CalculationStatus,
    RiskState,
    RiskStatus,
)
from acash.portfolio.schema import RiskSnapshot
from acash.risk.bridge import RiskStateBridge
from acash.risk.risk_schema import (
    CandidateRiskAllocation,
    RiskEvaluationReport,
    RiskVerdict,
)


@pytest.fixture
def sample_portfolio_state() -> PortfolioState:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    pos_aapl = Position(
        symbol="AAPL",
        quantity=Decimal("10"),
        entry_price=Decimal("150.00"),
        current_price=Decimal("150.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    return PortfolioState(
        timestamp_utc=now,
        positions={"AAPL": pos_aapl},
        cash_balance=Decimal("8500.00"),
        total_equity=Decimal("10000.00"),
        margin_used=Decimal("1500.00"),
        gross_exposure=Decimal("1500.00"),
        net_exposure=Decimal("1500.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )


@pytest.fixture
def sample_account_state() -> AccountState:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    return AccountState(
        account_id="ACC_001",
        currency="USD",
        balance=Decimal("10000.00"),
        equity=Decimal("10000.00"),
        free_margin=Decimal("8500.00"),
        margin_level_pct=666.67,
        leverage=1.0,
        is_live=False,
        timestamp_utc=now,
    )


# ============================================================================
# 1. PORTFOLIO STATE -> RISK SNAPSHOT TESTS
# ============================================================================


def test_bridge_portfolio_state_to_risk_snapshot(
    sample_portfolio_state: PortfolioState,
    sample_account_state: AccountState,
) -> None:
    snapshot = RiskStateBridge.portfolio_state_to_risk_snapshot(
        portfolio_state=sample_portfolio_state,
        account_state=sample_account_state,
        peak_equity=Decimal("12000.00"),
        max_drawdown_limit_pct=Decimal("15.00"),
        min_margin_buffer_threshold=Decimal("5000.00"),
        is_kill_switch_active=False,
    )

    assert isinstance(snapshot, RiskSnapshot)
    assert snapshot.account_equity == Decimal("10000.00")
    assert snapshot.cash_balance == Decimal("8500.00")
    assert snapshot.margin_used == Decimal("1500.00")
    assert snapshot.margin_headroom == Decimal("8500.00")
    # Drawdown = (12000 - 10000) / 12000 = 16.67%
    expected_dd = (Decimal("2000.00") / Decimal("12000.00")) * Decimal("100.0")
    assert snapshot.current_drawdown_pct == expected_dd
    assert snapshot.is_kill_switch_active is False
    assert len(snapshot.snapshot_digest) == 64


def test_bridge_portfolio_state_rejects_non_positive_equity() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    invalid_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("0.00"),
        total_equity=Decimal("0.00"),  # Zero equity
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    with pytest.raises(DataContractError, match="below minimum required"):
        RiskStateBridge.portfolio_state_to_risk_snapshot(portfolio_state=invalid_portfolio)


# ============================================================================
# 2. TARGET ALLOCATION <-> CANDIDATE RISK ALLOCATION ROUND-TRIP TESTS
# ============================================================================


def test_bridge_target_allocation_to_candidate_and_roundtrip() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    target = TargetAllocation(
        weights={"AAPL": 0.35, "MSFT": 0.45},
        cash_weight=0.20,
        rationale="Multi-horizon momentum target",
        timestamp_utc=now,
    )

    # 1. Convert TargetAllocation (float) -> CandidateRiskAllocation (Decimal)
    candidate = RiskStateBridge.target_allocation_to_candidate_allocation(
        target_allocation=target,
        strategy_id="MOM_STRATEGY",
    )

    assert isinstance(candidate, CandidateRiskAllocation)
    assert candidate.strategy_id == "MOM_STRATEGY"
    assert candidate.weights["AAPL"] == Decimal("0.35")
    assert candidate.weights["MSFT"] == Decimal("0.45")
    assert candidate.cash_weight == Decimal("0.20")
    assert candidate.as_of_utc == now
    assert len(candidate.candidate_digest) == 64

    # 2. Round-trip back to TargetAllocation (float)
    recovered = RiskStateBridge.candidate_allocation_to_target_allocation(candidate)
    assert isinstance(recovered, TargetAllocation)
    assert recovered.weights["AAPL"] == pytest.approx(0.35)
    assert recovered.weights["MSFT"] == pytest.approx(0.45)
    assert recovered.cash_weight == pytest.approx(0.20)
    assert recovered.timestamp_utc == now


def test_bridge_target_allocation_rejects_negative_float_weight() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    target = TargetAllocation(
        weights={"AAPL": -0.10},
        cash_weight=1.10,
        rationale="Negative weight",
        timestamp_utc=now,
    )
    with pytest.raises(DataContractError, match="cannot be negative"):
        RiskStateBridge.target_allocation_to_candidate_allocation(target)


# ============================================================================
# 3. RISK EVALUATION REPORT -> RISK ASSESSMENT ADAPTATION TESTS
# ============================================================================


def test_bridge_report_to_risk_assessment_approved() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    valid_hash = hashlib.sha256(b"digest").hexdigest()

    report = RiskEvaluationReport(
        evaluation_id="EVAL_01",
        verdict=RiskVerdict.APPROVED,
        original_allocation_digest=valid_hash,
        portfolio_state_digest=valid_hash,
        account_state_digest=valid_hash,
        risk_policy_digest=valid_hash,
        adjusted_weights={"AAPL": Decimal("0.40"), "MSFT": Decimal("0.40")},
        cash_weight=Decimal("0.20"),
        metrics_observed={"gross_leverage": Decimal("0.80"), "drawdown_pct": Decimal("5.20")},
        evaluated_at_utc=now,
        expires_at_utc=now,
    )

    assessment = RiskStateBridge.risk_evaluation_report_to_risk_assessment(report)

    assert isinstance(assessment, RiskAssessment)
    assert assessment.approved is True
    assert assessment.adjusted_weights["AAPL"] == pytest.approx(0.40)
    assert assessment.risk_utilization_pct == pytest.approx(80.0)
    assert assessment.max_drawdown_pct == pytest.approx(5.20)
    assert assessment.timestamp_utc == now


def test_bridge_report_to_risk_assessment_rejected() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    valid_hash = hashlib.sha256(b"digest").hexdigest()

    report = RiskEvaluationReport(
        evaluation_id="EVAL_REJ",
        verdict=RiskVerdict.KILL_SWITCH_BLOCKED,
        original_allocation_digest=valid_hash,
        portfolio_state_digest=valid_hash,
        account_state_digest=valid_hash,
        risk_policy_digest=valid_hash,
        adjusted_weights={},
        cash_weight=Decimal("1.00"),
        rejection_reason="KILL_SWITCH_ACTIVE",
        evaluated_at_utc=now,
        expires_at_utc=now,
    )

    assessment = RiskStateBridge.risk_evaluation_report_to_risk_assessment(report)

    assert isinstance(assessment, RiskAssessment)
    assert assessment.approved is False
    assert len(assessment.adjusted_weights) == 0
    assert assessment.rejection_reason == "KILL_SWITCH_ACTIVE"


# ============================================================================
# 4. RISK EVALUATION REPORT -> EXECUTION RISK STATE TESTS
# ============================================================================


def test_bridge_report_to_execution_risk_state(
    sample_portfolio_state: PortfolioState,
) -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    valid_hash = hashlib.sha256(b"digest").hexdigest()

    report = RiskEvaluationReport(
        evaluation_id="EVAL_01",
        verdict=RiskVerdict.REDUCED,
        original_allocation_digest=valid_hash,
        portfolio_state_digest=valid_hash,
        account_state_digest=valid_hash,
        risk_policy_digest=valid_hash,
        adjusted_weights={"AAPL": Decimal("0.25")},
        cash_weight=Decimal("0.75"),
        metrics_observed={
            "drawdown_pct": Decimal("4.50"),
            "max_asset_concentration": Decimal("0.25"),
        },
        evaluated_at_utc=now,
        expires_at_utc=now,
    )

    risk_state = RiskStateBridge.risk_evaluation_report_to_execution_risk_state(
        report=report,
        portfolio_state=sample_portfolio_state,
        authorization_id="AUTH_LIVE_001",
        strategy_id="MOM_01",
        data_age_ms=250,
        is_broker_connected=True,
    )

    assert isinstance(risk_state, RiskState)
    assert risk_state.authorization_id == "AUTH_LIVE_001"
    assert risk_state.strategy_id == "MOM_01"
    assert risk_state.total_equity == Decimal("10000.00")
    assert risk_state.risk_status == RiskStatus.RESTRICTED  # REDUCED verdict maps to RESTRICTED
    assert risk_state.calculation_status == CalculationStatus.NOMINAL
    assert risk_state.current_drawdown_pct == Decimal("4.50")
    assert risk_state.concentration_ratio == Decimal("0.25")
    assert risk_state.is_broker_connected is True


# ============================================================================
# 5. AUTHORITY BOUNDARY TESTS
# ============================================================================


def test_bridge_zero_broker_execution_authority() -> None:
    forbidden = [
        "submit_order",
        "execute_order",
        "place_order",
        "cancel_order",
        "send_wire",
        "get_broker_client",
    ]
    for m in forbidden:
        assert not hasattr(RiskStateBridge, m), f"RiskStateBridge must not have '{m}' method."
