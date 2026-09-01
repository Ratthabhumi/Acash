"""Unit and adversarial tests for Emergency Flattening Generator & Tracker (Slice 4).

Tests:
- Deterministic EmergencyFlattenIntent generation from PortfolioState.
- Single and multiple position liquidation targeting 0.0 with correct closing deltas (-quantity).
- Zero open positions produces empty deltas (no redundant liquidation intents).
- Invariant: EmergencyFlattenIntent Generated != Orders Submitted != Positions Flattened.
- Partial fill handling: remains FLATTEN_REQUESTED until 100% exposure is eliminated.
- Unreconciled / disconnected broker state prevents FLATTEN_COMPLETED declaration.
- Authoritative reconciliation with 0 gross exposure transitions to FLATTEN_COMPLETED.
- Residual flatten intent generation for remaining partial fill exposure.
- Strict rejection of non-blocked kill switch events.
- Zero direct broker execution authority in Phase 9.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import PortfolioState
from acash.core.domain.position import Position
from acash.risk.emergency import (
    EmergencyFlattenGenerator,
    EmergencyFlattenTracker,
)
from acash.risk.kill_switch import KillSwitchEvent
from acash.risk.risk_schema import (
    EmergencyFlattenIntent,
    EmergencyFlattenStatus,
    KillSwitchState,
)


@pytest.fixture
def valid_kill_switch_trip_event() -> KillSwitchEvent:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    policy_hash = hashlib.sha256(b"policy").hexdigest()
    return KillSwitchEvent(
        event_id="KILL_TRIP_001",
        previous_state=KillSwitchState.ACTIVE,
        resulting_state=KillSwitchState.PERSISTENTLY_BLOCKED,
        trigger_reason="MAX_DRAWDOWN_BREACHED",
        trigger_evidence={"drawdown_pct": "16.50"},
        policy_version="v1.0.0",
        policy_digest=policy_hash,
        previous_event_digest="0" * 64,
        timestamp_utc=now,
    )


@pytest.fixture
def sample_portfolio_with_positions() -> PortfolioState:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    pos_aapl = Position(
        symbol="AAPL",
        quantity=Decimal("100"),
        entry_price=Decimal("150.00"),
        current_price=Decimal("150.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    pos_msft = Position(
        symbol="MSFT",
        quantity=Decimal("50"),
        entry_price=Decimal("300.00"),
        current_price=Decimal("300.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    return PortfolioState(
        timestamp_utc=now,
        positions={"AAPL": pos_aapl, "MSFT": pos_msft},
        cash_balance=Decimal("10000.00"),
        total_equity=Decimal("40000.00"),
        margin_used=Decimal("30000.00"),
        gross_exposure=Decimal("30000.00"),
        net_exposure=Decimal("30000.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )


# ============================================================================
# 1. INTENT GENERATION & DELTA TESTS
# ============================================================================


def test_emergency_flatten_generator_single_and_multiple_positions(
    sample_portfolio_with_positions: PortfolioState,
    valid_kill_switch_trip_event: KillSwitchEvent,
) -> None:
    intent = EmergencyFlattenGenerator.generate_flatten_intent(
        portfolio_state=sample_portfolio_with_positions,
        kill_switch_event=valid_kill_switch_trip_event,
    )

    assert intent.status == EmergencyFlattenStatus.FLATTEN_REQUESTED
    assert intent.kill_switch_event_id == valid_kill_switch_trip_event.event_id

    # AAPL was +100 -> target 0.0, delta -100
    assert intent.target_positions["AAPL"] == Decimal("0.0")
    assert intent.closing_deltas["AAPL"] == Decimal("-100.0")

    # MSFT was +50 -> target 0.0, delta -50
    assert intent.target_positions["MSFT"] == Decimal("0.0")
    assert intent.closing_deltas["MSFT"] == Decimal("-50.0")

    assert len(intent.intent_digest) == 64


def test_emergency_flatten_generator_zero_positions(
    valid_kill_switch_trip_event: KillSwitchEvent,
) -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    empty_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("10000.00"),
        total_equity=Decimal("10000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    intent = EmergencyFlattenGenerator.generate_flatten_intent(
        portfolio_state=empty_portfolio,
        kill_switch_event=valid_kill_switch_trip_event,
    )

    # Invariant: No open positions -> empty deltas (no useless order generation)
    assert len(intent.target_positions) == 0
    assert len(intent.closing_deltas) == 0
    assert intent.status == EmergencyFlattenStatus.FLATTEN_REQUESTED


def test_emergency_flatten_generator_rejects_non_blocked_kill_switch() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    policy_hash = hashlib.sha256(b"policy").hexdigest()
    # Active event cannot trigger emergency flattening!
    active_event = KillSwitchEvent(
        event_id="KILL_ACTIVE_001",
        previous_state=KillSwitchState.RESET_PENDING,
        resulting_state=KillSwitchState.ACTIVE,
        trigger_reason="RESET_COMPLETED",
        policy_version="v1.0.0",
        policy_digest=policy_hash,
        timestamp_utc=now,
    )

    empty_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("10000.00"),
        total_equity=Decimal("10000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    with pytest.raises(DataContractError, match="Cannot generate emergency flatten intent"):
        EmergencyFlattenGenerator.generate_flatten_intent(
            portfolio_state=empty_portfolio,
            kill_switch_event=active_event,
        )


# ============================================================================
# 2. LIFECYCLE & RECONCILIATION VERIFICATION TESTS
# ============================================================================


def test_emergency_flatten_tracker_partial_fill_remains_requested(
    sample_portfolio_with_positions: PortfolioState,
    valid_kill_switch_trip_event: KillSwitchEvent,
) -> None:
    intent = EmergencyFlattenGenerator.generate_flatten_intent(
        portfolio_state=sample_portfolio_with_positions,
        kill_switch_event=valid_kill_switch_trip_event,
    )

    now = datetime(2026, 9, 1, 12, 5, 0, tzinfo=timezone.utc)
    # Partial fill scenario: AAPL was +100, now +40 (60 shares closed)
    pos_aapl_partial = Position(
        symbol="AAPL",
        quantity=Decimal("40"),
        entry_price=Decimal("150.00"),
        current_price=Decimal("150.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    partial_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={"AAPL": pos_aapl_partial},
        cash_balance=Decimal("19000.00"),
        total_equity=Decimal("25000.00"),
        margin_used=Decimal("6000.00"),
        gross_exposure=Decimal("6000.00"),
        net_exposure=Decimal("6000.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    status, remaining = EmergencyFlattenTracker.verify_flatten_completion(
        intent=intent,
        latest_portfolio_state=partial_portfolio,
        is_broker_reconciled=True,
    )

    # Invariant: Partial fill remains FLATTEN_REQUESTED (NOT completed)
    assert status == EmergencyFlattenStatus.FLATTEN_REQUESTED
    assert remaining["AAPL"] == Decimal("40")


def test_emergency_flatten_tracker_unreconciled_broker_prevents_completion(
    valid_kill_switch_trip_event: KillSwitchEvent,
) -> None:
    now = datetime(2026, 9, 1, 12, 5, 0, tzinfo=timezone.utc)
    zero_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("40000.00"),
        total_equity=Decimal("40000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    intent = EmergencyFlattenIntent(
        intent_id="FLATTEN_001",
        kill_switch_event_id=valid_kill_switch_trip_event.event_id,
        target_positions={"AAPL": Decimal("0.0")},
        closing_deltas={"AAPL": Decimal("-100.0")},
        issued_at_utc=now,
    )

    # Even if local positions is empty, if broker is UNRECONCILED / DISCONNECTED -> NOT COMPLETED
    status, _ = EmergencyFlattenTracker.verify_flatten_completion(
        intent=intent,
        latest_portfolio_state=zero_portfolio,
        is_broker_reconciled=False,  # Unreconciled!
    )

    assert status == EmergencyFlattenStatus.FLATTEN_REQUESTED


def test_emergency_flatten_tracker_full_liquidation_completed(
    valid_kill_switch_trip_event: KillSwitchEvent,
) -> None:
    now = datetime(2026, 9, 1, 12, 5, 0, tzinfo=timezone.utc)
    zero_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("40000.00"),
        total_equity=Decimal("40000.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    intent = EmergencyFlattenIntent(
        intent_id="FLATTEN_001",
        kill_switch_event_id=valid_kill_switch_trip_event.event_id,
        target_positions={"AAPL": Decimal("0.0")},
        closing_deltas={"AAPL": Decimal("-100.0")},
        issued_at_utc=now,
    )

    status, remaining = EmergencyFlattenTracker.verify_flatten_completion(
        intent=intent,
        latest_portfolio_state=zero_portfolio,
        is_broker_reconciled=True,
    )

    # 100% Liquidated and reconciled -> FLATTEN_COMPLETED
    assert status == EmergencyFlattenStatus.FLATTEN_COMPLETED
    assert len(remaining) == 0


def test_emergency_flatten_tracker_generate_residual_intent(
    sample_portfolio_with_positions: PortfolioState,
    valid_kill_switch_trip_event: KillSwitchEvent,
) -> None:
    parent_intent = EmergencyFlattenGenerator.generate_flatten_intent(
        portfolio_state=sample_portfolio_with_positions,
        kill_switch_event=valid_kill_switch_trip_event,
    )

    now = datetime(2026, 9, 1, 12, 5, 0, tzinfo=timezone.utc)
    pos_aapl_residual = Position(
        symbol="AAPL",
        quantity=Decimal("30"),
        entry_price=Decimal("150.00"),
        current_price=Decimal("150.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=now,
    )
    residual_portfolio = PortfolioState(
        timestamp_utc=now,
        positions={"AAPL": pos_aapl_residual},
        cash_balance=Decimal("20000.00"),
        total_equity=Decimal("24500.00"),
        margin_used=Decimal("4500.00"),
        gross_exposure=Decimal("4500.00"),
        net_exposure=Decimal("4500.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    residual_intent = EmergencyFlattenTracker.generate_residual_intent(
        parent_intent=parent_intent,
        latest_portfolio_state=residual_portfolio,
    )

    assert residual_intent is not None
    assert residual_intent.target_positions["AAPL"] == Decimal("0.0")
    assert residual_intent.closing_deltas["AAPL"] == Decimal("-30.0")


# ============================================================================
# 3. AUTHORITY BOUNDARY TESTS
# ============================================================================


def test_emergency_flatten_zero_broker_authority() -> None:
    """Phase 9 generator & tracker must NOT have direct broker wire authority."""
    forbidden = [
        "submit_order",
        "execute_order",
        "send_wire",
        "cancel_order",
        "get_broker_client",
    ]
    for m in forbidden:
        assert not hasattr(EmergencyFlattenGenerator, m)
        assert not hasattr(EmergencyFlattenTracker, m)
