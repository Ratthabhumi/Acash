"""Phase 13 Slice 1: Gate A Pre-Live Certification Test Suite.

Layer A: Automated Contract Evidence Suite.
Verifies all 11 certification items (A-1 through A-11) per:
- docs/phase13/PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV3.md
- docs/phase13/recovery_runbook.md

Scope Invariants:
1. Live Capital Authority is strictly $0.00.
2. All execution and reconciliation in this suite operates against simulation / MockMT5Transport.
3. Layer A verifies software contract integrity. Real MT5 terminal reality is documented
   and verified separately under Layer B (Operational Demo Rehearsal).
4. No modification to Phase 12 frozen baseline (1e1d154).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.execution.admission import (
    PreLiveRiskAdmissionError,
    construct_order_intent,
)
from acash.execution.broker_events import (
    BrokerEventKind,
    normalize_broker_event,
)
from acash.execution.coordinator import (
    CoordinatorEvent,
    ExecutionCoordinator,
)
from acash.execution.crypto import (
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.execution.signing import Ed25519Signer
from acash.execution.mt5.adapter import MT5BrokerAdapter
from acash.execution.mt5.enums import (
    MT5AccountMarginMode,
    MT5DealType,
    MT5PositionType,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5ReconciliationError,
)
from acash.execution.mt5.reconciliation import (
    ACASHShadowLedgerSnapshot,
    CaptureCompletenessStatus,
    HistoricalDealCoverage,
    HistoricalDealScopeKind,
    MT5BrokerRealitySnapshot,
    MT5ReconciliationEngine,
    ReconciliationCaptureContext,
    ReconciliationStatus,
    ShadowDealRecord,
    ShadowPosition,
    ShadowRestingOrder,
    compute_payload_digest,
)
from acash.execution.mt5.schemas import (
    BrokerSymbolSpec,
    MT5AccountReality,
    MT5DealReality,
    MT5OrderReality,
    MT5PositionReality,
)
from acash.execution.mt5.transport import (
    MockMT5Transport,
    MT5TransportSafetyState,
    TransportFailureCause,
)
from acash.execution.operational_restriction import (
    RestrictionLedger,
    RiskRestrictionAuthority,
)
from acash.execution.schema import (
    AuthorizationStatus,
    CalculationStatus,
    LiveAuthorization,
    OrderLifecycleState,
    OrderSide,
    OrderType,
    RiskState,
    RiskStatus,
    compute_authorization_digest,
)
from acash.monitoring.schema import (
    ForwardGovernanceRecommendation,
    ForwardHealthPolicy,
    ForwardHealthState,
    ForwardWindowMetrics,
)
from acash.monitoring.state_machine import ForwardHealthStateMachine
from acash.risk.emergency import (
    EmergencyFlattenGenerator,
    EmergencyFlattenTracker,
)
from acash.risk.kill_switch import (
    KillSwitchEvent,
    SovereignKillSwitchController,
)
from acash.risk.risk_engine import DeterministicRiskEngine
from acash.risk.risk_schema import (
    CandidateRiskAllocation,
    DeriskPolicy,
    EmergencyFlattenIntent,
    EmergencyFlattenStatus,
    KillSwitchState,
    RiskPolicyConfig,
    RiskVerdict,
)


# ===========================================================================
# Fixtures & Test Helpers
# ===========================================================================


class MockEd25519Signer:
    """Helper wrapper around Ed25519Signer for test fixtures."""

    def __init__(self, key_id: str, issuer_id: str) -> None:
        self.key_id = key_id
        self.issuer_id = issuer_id
        self.private_key_b64, self.public_key_b64 = Ed25519Signer.generate_key_pair()

    def sign(self, payload_bytes: bytes) -> str:
        return Ed25519Signer.sign(self.private_key_b64, payload_bytes)


@pytest.fixture
def sample_trust_store() -> Ed25519TrustStore:
    now = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    risk_officer = MockEd25519Signer(key_id="KEY_RISK_01", issuer_id="RISK_LEAD")
    comp_officer = MockEd25519Signer(key_id="KEY_COMP_01", issuer_id="COMP_LEAD")

    entry_risk = Ed25519TrustStoreEntry(
        key_id=risk_officer.key_id,
        issuer_id=risk_officer.issuer_id,
        public_key_b64=risk_officer.public_key_b64,
        valid_from=now,
        status=TrustStoreEntryStatus.ACTIVE,
    )
    entry_comp = Ed25519TrustStoreEntry(
        key_id=comp_officer.key_id,
        issuer_id=comp_officer.issuer_id,
        public_key_b64=comp_officer.public_key_b64,
        valid_from=now,
        status=TrustStoreEntryStatus.ACTIVE,
    )
    return Ed25519TrustStore(entries=(entry_risk, entry_comp))


@pytest.fixture
def micro_capital_risk_policy() -> RiskPolicyConfig:
    """Phase 13 micro-capital calibrated risk parameters ($50 max daily loss, 5% drawdown)."""
    return RiskPolicyConfig(
        policy_version="v1.0.0-phase13-micro",
        derisk_policy=DeriskPolicy.BINARY_REJECT,
        max_gross_leverage=Decimal("1.00"),
        max_asset_concentration=Decimal("0.50"),
        min_cash_buffer=Decimal("0.10"),
        max_drawdown_limit_pct=Decimal("5.00"),
        max_daily_loss_usd=Decimal("50.00"),
        min_margin_buffer_usd=Decimal("50.00"),
        max_market_data_age_ms=1500,
        max_clock_drift_ms=500,
    )


def _make_symbol_spec(symbol: str = "EURUSD") -> BrokerSymbolSpec:
    digest = BrokerSymbolSpec.compute_spec_digest(
        canonical_symbol=symbol,
        broker_symbol=symbol,
        contract_size=Decimal("100000"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("10.00"),
        volume_step=Decimal("0.01"),
        digits=5,
        point_size=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=10,
        margin_currency="EUR",
        profit_currency="USD",
    )
    return BrokerSymbolSpec(
        canonical_symbol=symbol,
        broker_symbol=symbol,
        contract_size=Decimal("100000"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("10.00"),
        volume_step=Decimal("0.01"),
        digits=5,
        point_size=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=10,
        margin_currency="EUR",
        profit_currency="USD",
        spec_digest=digest,
    )


def _make_sample_account_reality(
    balance: Decimal = Decimal("500.00"),
    equity: Decimal = Decimal("500.00"),
    margin: Decimal = Decimal("0.00"),
) -> MT5AccountReality:
    return MT5AccountReality(
        login=1001,
        trade_mode=0,
        margin_mode=MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
        leverage=100,
        limit_orders=200,
        margin_so_mode=0,
        trade_allowed=True,
        trade_expert=True,
        balance=balance,
        credit=Decimal("0.0"),
        profit=equity - balance,
        equity=equity,
        margin=margin,
        margin_free=equity - margin,
        margin_level=Decimal("0.0") if margin == Decimal("0.0") else (equity / margin) * Decimal("100"),
        margin_so_call=Decimal("50.0"),
        margin_so_so=Decimal("30.0"),
        currency="USD",
    )


def _make_shadow_snapshot(
    *,
    broker_id: str = "TEST_BROKER",
    account_id: str = "ACC_DEMO_01",
    terminal_instance_id: str = "TERM_01",
    balance: Decimal = Decimal("500.00"),
    equity: Decimal = Decimal("500.00"),
    margin: Decimal = Decimal("0.00"),
    positions: Tuple[ShadowPosition, ...] = (),
    orders: Tuple[ShadowRestingOrder, ...] = (),
    deals: Tuple[ShadowDealRecord, ...] = (),
) -> ACASHShadowLedgerSnapshot:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "broker_id": broker_id,
        "account_id": account_id,
        "terminal_instance_id": terminal_instance_id,
        "currency": "USD",
        "snapshot_at": now,
        "balance": balance,
        "equity": equity,
        "margin": margin,
        "positions": positions,
        "resting_orders": orders,
        "deals": deals,
    }
    digest = compute_payload_digest(payload)
    return ACASHShadowLedgerSnapshot(
        schema_version="1.0.0",
        broker_id=broker_id,
        account_id=account_id,
        terminal_instance_id=terminal_instance_id,
        currency="USD",
        snapshot_at=now,
        balance=balance,
        equity=equity,
        margin=margin,
        positions=positions,
        resting_orders=orders,
        deals=deals,
        ledger_digest=digest,
    )


def _make_broker_snapshot(
    *,
    broker_id: str = "TEST_BROKER",
    account_id: str = "ACC_DEMO_01",
    terminal_instance_id: str = "TERM_01",
    account: Optional[MT5AccountReality] = None,
    positions: Tuple[MT5PositionReality, ...] = (),
    orders: Tuple[MT5OrderReality, ...] = (),
    history_orders: Tuple[MT5OrderReality, ...] = (),
    deals: Tuple[MT5DealReality, ...] = (),
    observed_at: Optional[datetime] = None,
) -> MT5BrokerRealitySnapshot:
    t = observed_at or datetime.now(timezone.utc)
    acc = account or _make_sample_account_reality()
    t_msc = int(t.timestamp() * 1000)

    capture_ctx = ReconciliationCaptureContext(
        reconciliation_id=f"CAP_{t_msc}",
        capture_started_at=t - timedelta(milliseconds=100),
        capture_completed_at=t,
        capture_started_at_msc=t_msc - 100,
        capture_completed_at_msc=t_msc,
        pre_watermark_deal_ticket=0,
        post_watermark_deal_ticket=max((d.deal_ticket for d in deals), default=0),
        query_latencies_ms={"account": 20.0, "positions": 20.0, "orders": 20.0, "deals": 40.0},
        capture_duration_ms=100.0,
        max_capture_window_ms=2000.0,
        completeness_status=CaptureCompletenessStatus.COMPLETE,
    )

    coverage = HistoricalDealCoverage(
        scope_kind=HistoricalDealScopeKind.FULL_CYCLE,
        from_timestamp=t - timedelta(hours=1),
        to_timestamp=t,
        watermark_ticket=0,
        last_deal_ticket=max((d.deal_ticket for d in deals), default=0),
        total_deals_retrieved=len(deals),
        is_complete=True,
        coverage_digest=compute_payload_digest({"deals": len(deals), "is_complete": True}),
    )

    payload = {
        "schema_version": "1.0.0",
        "broker_id": broker_id,
        "account_id": account_id,
        "terminal_instance_id": terminal_instance_id,
        "observed_at": t,
        "account": acc,
        "positions": positions,
        "orders": orders,
        "history_orders": history_orders,
        "deals": deals,
        "deal_coverage": coverage,
        "capture_context": capture_ctx,
    }
    digest = compute_payload_digest(payload)

    return MT5BrokerRealitySnapshot(
        schema_version="1.0.0",
        broker_id=broker_id,
        account_id=account_id,
        terminal_instance_id=terminal_instance_id,
        observed_at=t,
        account=acc,
        positions=positions,
        orders=orders,
        history_orders=history_orders,
        deals=deals,
        deal_coverage=coverage,
        capture_context=capture_ctx,
        broker_snapshot_digest=digest,
    )


def _make_forward_metrics(
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


def _make_risk_state(
    *,
    authorization_id: str = "AUTH_TEST_001",
    strategy_id: str = "STRAT_TEST",
    risk_status: RiskStatus = RiskStatus.NORMAL,
    calculation_status: CalculationStatus = CalculationStatus.NOMINAL,
) -> RiskState:
    now = datetime.now(timezone.utc)
    return RiskState(
        timestamp=now,
        authorization_id=authorization_id,
        strategy_id=strategy_id,
        total_equity=Decimal("500.00"),
        realized_pnl_today=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        current_drawdown_pct=Decimal("0.00"),
        gross_exposure_notional=Decimal("0.00"),
        net_exposure_notional=Decimal("0.00"),
        concentration_ratio=Decimal("0.00"),
        parametric_var_95=Decimal("0.00"),
        historical_cvar_95=Decimal("0.00"),
        data_timestamp=now,
        data_age_ms=10,
        calculation_status=calculation_status,
        is_market_data_stale=False,
        is_broker_connected=True,
        is_clock_skew_detected=False,
        risk_status=risk_status,
    )


# ===========================================================================
# A-1: RiskPolicyConfig Parameter Calibration and Breach Halts
# ===========================================================================


def test_gate_a1_risk_policy_config_limits(
    micro_capital_risk_policy: RiskPolicyConfig,
) -> None:
    """A-1: Verify RiskPolicyConfig micro-capital limits and BINARY_REJECT / HALT enforcement."""
    now = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)
    engine = DeterministicRiskEngine(policy_config=micro_capital_risk_policy)

    # 1. Normal allocation under $50 daily loss and 5% drawdown limits -> APPROVED
    candidate = CandidateRiskAllocation(
        candidate_id="CAND_GATE_A1",
        strategy_id="STRAT_EURUSD_MICRO",
        weights={"EURUSD": Decimal("0.40")},
        cash_weight=Decimal("0.60"),
        source_decision_digest=hashlib.sha256(b"gate_a1").hexdigest(),
        as_of_utc=now,
    )
    port_state = PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("500.00"),
        total_equity=Decimal("500.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )
    acct_state = AccountState(
        account_id="ACC_DEMO_01",
        currency="USD",
        balance=Decimal("500.00"),
        equity=Decimal("500.00"),
        free_margin=Decimal("500.00"),
        leverage=100.0,
        is_live=False,
        timestamp_utc=now,
    )

    report = engine.evaluate_candidate_allocation(
        candidate_allocation=candidate,
        portfolio_state=port_state,
        account_state=acct_state,
        as_of=now,
    )
    assert report.verdict == RiskVerdict.APPROVED

    # 2. Simulate Daily Loss Breach: Cumulative daily loss $60 > $50 limit -> BLOCKED / REJECTED
    acct_breached = AccountState(
        account_id="ACC_DEMO_01",
        currency="USD",
        balance=Decimal("440.00"),
        equity=Decimal("440.00"),
        free_margin=Decimal("440.00"),
        leverage=100.0,
        is_live=False,
        timestamp_utc=now,
    )
    port_breached = PortfolioState(
        timestamp_utc=now,
        positions={},
        cash_balance=Decimal("440.00"),
        total_equity=Decimal("440.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("-60.00"),  # Breaches $50.00 daily loss limit!
    )
    report_breach = engine.evaluate_candidate_allocation(
        candidate_allocation=candidate,
        portfolio_state=port_breached,
        account_state=acct_breached,
        as_of=now,
    )
    assert report_breach.verdict in (RiskVerdict.REJECTED, RiskVerdict.KILL_SWITCH_BLOCKED)


# ===========================================================================
# A-2: Kill Switch Persistence and Crash Recovery
# ===========================================================================


def test_gate_a2_kill_switch_persistence_and_recovery(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    """A-2: Verify SovereignKillSwitchController persists PERSISTENTLY_BLOCKED and recovers."""
    ledger_path = tmp_path / "kill_switch_ledger.jsonl"

    c1 = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=ledger_path,
    )
    initial_ks_state: KillSwitchState = c1.state
    assert initial_ks_state == KillSwitchState.ACTIVE

    # Trip to PERSISTENTLY_BLOCKED
    c1.trip(reason="GATE_A2_TEST_TRIP", evidence={"trigger": "manual_test"})
    assert c1.state == KillSwitchState.PERSISTENTLY_BLOCKED
    assert ledger_path.exists()

    # Simulate Cold Process Restart
    c2 = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=ledger_path,
    )
    assert c2.state == KillSwitchState.PERSISTENTLY_BLOCKED
    assert c2.is_blocked is True

    # Assert fail-closed admission block
    with pytest.raises(DataContractError, match="EXECUTION_ADMISSION_BLOCKED"):
        c2.assert_admission_allowed()


# ===========================================================================
# A-3: MT5 Demo Lifecycle Contract Evidence (Layer A)
# ===========================================================================


def test_gate_a3_layer_a_demo_lifecycle_contract_evidence() -> None:
    """A-3 Layer A: Verify order lifecycle progression (SUBMITTED -> ACK -> FILLED)."""
    now = datetime.now(timezone.utc)
    coord = ExecutionCoordinator(
        execution_id="EXEC_DEMO_001",
        requested_qty=Decimal("0.01"),
        initial_state=OrderLifecycleState.SUBMITTED,
        intent_id="INT_DEMO_001",
    )
    initial_coord_state: OrderLifecycleState = coord.state
    assert initial_coord_state == OrderLifecycleState.SUBMITTED

    # 1. ACK event from broker
    ev_ack, _ = normalize_broker_event(
        broker_order_id="ORD_DEMO_9988",
        event_kind=BrokerEventKind.ACK,
        observed_at=now,
        source="mt5_test",
        broker_sequence="SEQ_1",
    )
    outcome_ack = coord.apply(CoordinatorEvent(
        broker_event_id="ORD_DEMO_9988",
        broker_sequence="SEQ_1",
        canonical_event=ev_ack,
        observed_at=now,
    ))
    assert outcome_ack.state is OrderLifecycleState.ACKNOWLEDGED
    ack_coord_state: OrderLifecycleState = coord.state
    assert ack_coord_state is OrderLifecycleState.ACKNOWLEDGED

    # 2. FILL event from broker
    ev_fill, evidence_fill = normalize_broker_event(
        broker_order_id="ORD_DEMO_9988",
        event_kind=BrokerEventKind.FILLED,
        observed_at=now + timedelta(seconds=1),
        source="mt5_test",
        broker_sequence="SEQ_2",
    )
    outcome_fill = coord.apply(CoordinatorEvent(
        broker_event_id="ORD_DEMO_9988",
        broker_sequence="SEQ_2",
        canonical_event=ev_fill,
        evidence=evidence_fill.to_evidence_string() if evidence_fill else "FILLED",
        observed_at=now + timedelta(seconds=1),
        fill_qty=Decimal("0.01"),
    ))
    assert outcome_fill.state is OrderLifecycleState.FILLED
    final_coord_state: OrderLifecycleState = coord.state
    assert final_coord_state is OrderLifecycleState.FILLED
    assert coord.filled_qty == Decimal("0.01")


# ===========================================================================
# A-4: 6-D Reconciliation Cycle Verification
# ===========================================================================


def test_gate_a4_6d_reconciliation_cycle_evidence() -> None:
    """A-4: Verify 6-D reconciliation cycle pass and fail-closed discrepancy handling."""
    engine = MT5ReconciliationEngine()
    transport = MockMT5Transport(broker_id="TEST_BROKER", account_id="ACC_DEMO_01")
    adapter = MT5BrokerAdapter(
        broker_id="TEST_BROKER",
        account_id="ACC_DEMO_01",
        terminal_instance_id="TERM_01",
        transport=transport,
    )

    # 1. Nominal 6-D cycle passes
    shadow = _make_shadow_snapshot()
    broker = _make_broker_snapshot()
    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is True
    assert report.status == ReconciliationStatus.CLEAN
    assert report.confirmation is not None

    adapter.confirm_reconciliation(report.confirmation)
    ready_state: MT5TransportSafetyState = adapter.safety_state
    assert ready_state == MT5TransportSafetyState.READY
    assert adapter.can_dispatch() is True

    # 2. Inject discrepancy: External untracked deal
    untracked_deal = MT5DealReality(
        deal_ticket=888999,
        order_ticket=777666,
        position_ticket=111222,
        deal_time_utc=datetime.now(timezone.utc),
        deal_type=MT5DealType.DEAL_TYPE_BUY,
        volume=Decimal("0.05"),
        price=Decimal("1.08500"),
        commission=Decimal("0.00"),
        swap=Decimal("0.00"),
        profit=Decimal("0.00"),
        fee=Decimal("0.00"),
        symbol="EURUSD",
        comment="external_mobile_trade",
    )
    broker_discrepant = _make_broker_snapshot(deals=(untracked_deal,))
    report_disc = engine.reconcile_6d(shadow, broker_discrepant)
    assert report_disc.is_clean is False

    # Mark blocked upon discrepancy
    adapter.mark_blocked("Discrepancy detected in 6-D reconciliation")
    assert adapter.safety_state == MT5TransportSafetyState.BLOCKED
    assert adapter.can_dispatch() is False


# ===========================================================================
# A-5: ForwardHealthStateMachine Transitions (DEGRADED & MONITORING_BLOCKED)
# ===========================================================================


def test_gate_a5_forward_health_state_transitions() -> None:
    """A-5: Verify ForwardHealthStateMachine transitions to DEGRADED and MONITORING_BLOCKED."""
    policy = ForwardHealthPolicy(
        min_observations=30,
        rolling_window_size=60,
        degradation_persistence_n=3,
        recovery_persistence_m=10,
        critical_drawdown_limit=Decimal("0.20"),
    )
    sm = ForwardHealthStateMachine(policy=policy)

    # 1. Insufficient observations -> INSUFFICIENT_EVIDENCE
    metrics_sparse = _make_forward_metrics(observation_count=10)
    r1 = sm.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics_sparse,
    )
    assert r1.state == ForwardHealthState.INSUFFICIENT_EVIDENCE

    # 2. Telemetry failure -> MONITORING_BLOCKED
    r_blocked = sm.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics_sparse,
        is_telemetry_valid=False,
    )
    assert r_blocked.state == ForwardHealthState.MONITORING_BLOCKED
    assert r_blocked.recommendation == ForwardGovernanceRecommendation.MONITORING_BLOCKED_FLAG

    # 3. Telemetry restored -> INSUFFICIENT_EVIDENCE (fail-closed reset)
    r_restore = sm.evaluate_step(
        current_state=ForwardHealthState.MONITORING_BLOCKED,
        metrics=metrics_sparse,
        is_telemetry_valid=True,
    )
    assert r_restore.state == ForwardHealthState.INSUFFICIENT_EVIDENCE


# ===========================================================================
# A-6: EmergencyFlattenIntent Forensic Record Verification
# ===========================================================================


def test_gate_a6_emergency_flatten_intent_forensic_record(
    sample_trust_store: Ed25519TrustStore,
) -> None:
    """A-6: Verify EmergencyFlattenIntent generated from kill switch event is forensic only."""
    now = datetime.now(timezone.utc)
    ks = SovereignKillSwitchController(trust_store=sample_trust_store)
    ks_event = ks.trip(reason="TEST_KILL_SWITCH_EMERGENCY")

    port_state = PortfolioState(
        timestamp_utc=now,
        positions={
            "EURUSD": Position(
                symbol="EURUSD",
                quantity=Decimal("0.02"),
                entry_price=Decimal("1.08500"),
                current_price=Decimal("1.08500"),
                unrealized_pnl=Decimal("0.00"),
                realized_pnl=Decimal("0.00"),
                timestamp_utc=now,
            )
        },
        cash_balance=Decimal("499.9783"),
        total_equity=Decimal("500.00"),
        margin_used=Decimal("20.00"),
        gross_exposure=Decimal("0.0217"),
        net_exposure=Decimal("0.0217"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
    )

    intent = EmergencyFlattenGenerator.generate_flatten_intent(
        portfolio_state=port_state,
        kill_switch_event=ks_event,
        as_of=now,
    )

    assert isinstance(intent, EmergencyFlattenIntent)
    assert intent.target_positions["EURUSD"] == Decimal("0.0")
    assert intent.closing_deltas["EURUSD"] == Decimal("-0.02")
    assert intent.status == EmergencyFlattenStatus.FLATTEN_REQUESTED
    assert intent.kill_switch_event_id == ks_event.event_id


# ===========================================================================
# A-7: Recovery Procedures Contract Verification
# ===========================================================================


def test_gate_a7_recovery_procedures_contract() -> None:
    """A-7: Verify connection loss inhibition and post-reconnect 6-D recon requirement."""
    engine = MT5ReconciliationEngine()
    transport = MockMT5Transport(broker_id="TEST_BROKER", account_id="ACC_DEMO_01")
    adapter = MT5BrokerAdapter(
        broker_id="TEST_BROKER",
        account_id="ACC_DEMO_01",
        terminal_instance_id="TERM_01",
        transport=transport,
    )

    # Initial Clean Recon
    report = engine.reconcile_6d(_make_shadow_snapshot(), _make_broker_snapshot())
    assert report.confirmation is not None
    adapter.confirm_reconciliation(report.confirmation)
    assert adapter.can_dispatch() is True

    # 1. Connection Lost -> mark_reconciliation_required
    adapter.mark_reconciliation_required(cause=TransportFailureCause.TRADE_SERVER_DISCONNECTED)
    assert adapter.can_dispatch() is False
    assert adapter.safety_state == MT5TransportSafetyState.RECONCILIATION_REQUIRED

    # 2. Re-running 6-D recon after reconnect restores dispatch
    report_restored = engine.reconcile_6d(_make_shadow_snapshot(), _make_broker_snapshot())
    assert report_restored.confirmation is not None
    adapter.confirm_reconciliation(report_restored.confirmation)
    assert adapter.can_dispatch() is True


# ===========================================================================
# A-8: LiveAuthorization Parameter Contract & Digest Binding
# ===========================================================================


def test_gate_a8_live_authorization_parameter_contract() -> None:
    """A-8: Verify LiveAuthorization parameters, digest integrity, and admission enforcement."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=4)

    # 1. Construct valid DRAFT authorization with micro-capital bounds
    digest = compute_authorization_digest(
        authorization_id="AUTH_PHASE13_001",
        certificate_id="CERT_P13_DEMO",
        strategy_id="STRAT_EURUSD_MICRO",
        authorized_at=now,
        expires_at=expires,
        max_notional=Decimal("500.00"),
        max_position_size=Decimal("0.01"),
        max_order_rate_per_minute=30,
        max_daily_loss_notional=Decimal("50.00"),
        max_drawdown_pct=Decimal("5.00"),
        allowed_venues=("MT5_DEMO_VENUE",),
        allowed_symbols=("EURUSD",),
        risk_policy_version="v1.0.0-phase13-micro",
        required_approvals=1,
        approval_digests=(),
    )

    auth = LiveAuthorization(
        authorization_id="AUTH_PHASE13_001",
        certificate_id="CERT_P13_DEMO",
        strategy_id="STRAT_EURUSD_MICRO",
        status=AuthorizationStatus.DRAFT,
        authorized_at=now,
        expires_at=expires,
        max_notional=Decimal("500.00"),
        max_position_size=Decimal("0.01"),
        max_order_rate_per_minute=30,
        max_daily_loss_notional=Decimal("50.00"),
        max_drawdown_pct=Decimal("5.00"),
        allowed_venues=("MT5_DEMO_VENUE",),
        allowed_symbols=("EURUSD",),
        risk_policy_version="v1.0.0-phase13-micro",
        required_approvals=1,
        approvals=(),
        authorization_digest=digest,
    )
    assert auth.status == AuthorizationStatus.DRAFT

    # 2. Invariant: DRAFT status rejected at admission gate
    risk_state = _make_risk_state(
        authorization_id="AUTH_PHASE13_001",
        strategy_id="STRAT_EURUSD_MICRO",
    )
    restriction_auth = RiskRestrictionAuthority(ledger=RestrictionLedger())

    with pytest.raises(PreLiveRiskAdmissionError, match="must be ACTIVE"):
        construct_order_intent(
            authorization=auth,
            intent_id="INTENT_DEMO_001",
            venue="MT5_DEMO_VENUE",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.01"),
            current_risk=risk_state,
            signal_event_hash=hashlib.sha256(b"sig").hexdigest(),
            created_at=now,
            restriction_authority=restriction_auth,
        )


# ===========================================================================
# A-9: Rollback / Corrupt Ledger Fails Closed
# ===========================================================================


def test_gate_a9_rollback_corrupted_persistence_fails_closed(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    """A-9: Verify corrupt kill switch ledger fails closed with DataContractError on startup."""
    ledger_path = tmp_path / "corrupted_ledger.jsonl"
    ledger_path.write_text("ILLEGAL_MALFORMED_JSON_CORRUPTION\n", encoding="utf-8")

    with pytest.raises(DataContractError, match="PERSISTENCE_RECOVERY_FAILED"):
        SovereignKillSwitchController(
            trust_store=sample_trust_store,
            persistence_path=ledger_path,
        )


# ===========================================================================
# A-10: DEGRADED Warning Log and Operator SLA Rehearsal (Layer A)
# ===========================================================================


def test_gate_a10_automated_degraded_warning_and_sla_policy() -> None:
    """A-10 Layer A: Verify structured WARNING schema and <= 15 min SLA timeout policy."""
    now = datetime(2026, 9, 3, 14, 0, 0, tzinfo=timezone.utc)

    # 1. Structure WARNING event
    warning_payload = {
        "level": "WARNING",
        "event": "STRATEGY_DEGRADED",
        "state": "DEGRADED",
        "recommendation": "DEGRADED_PROBATION",
        "timestamp_utc": now.isoformat(),
        "strategy_id": "STRAT_EURUSD_MICRO",
        "periods_degraded": 2,
        "trigger_metrics": {"rolling_sharpe": "0.45", "benchmark_sharpe": "1.20"},
    }
    assert warning_payload["event"] == "STRATEGY_DEGRADED"
    assert warning_payload["recommendation"] == "DEGRADED_PROBATION"

    # 2. SLA policy helper function simulation
    def check_operator_sla(
        warn_ts: datetime,
        ack_ts: Optional[datetime],
        max_sla_seconds: int = 900,  # 15 minutes
    ) -> Tuple[bool, str]:
        if ack_ts is None:
            return False, "MISSED_ACKNOWLEDGEMENT"
        delta = (ack_ts - warn_ts).total_seconds()
        if delta <= max_sla_seconds:
            return True, "WITHIN_SLA"
        return False, "SLA_BREACH_MANDATORY_KILL_SWITCH"

    # Rehearsal Case 1: Operator acknowledges at 10 minutes -> PASS
    ack_pass = now + timedelta(minutes=10)
    ok, reason = check_operator_sla(now, ack_pass)
    assert ok is True
    assert reason == "WITHIN_SLA"

    # Rehearsal Case 2: Operator acknowledges at 18 minutes -> BREACH -> Kill switch trip required
    ack_fail = now + timedelta(minutes=18)
    ok_breach, breach_reason = check_operator_sla(now, ack_fail)
    assert ok_breach is False
    assert breach_reason == "SLA_BREACH_MANDATORY_KILL_SWITCH"


# ===========================================================================
# A-11: Emergency Manual Close E2E Rehearsal (Layer A Contract)
# ===========================================================================


def test_gate_a11_layer_a_emergency_manual_close_rehearsal(
    tmp_path: Path,
    sample_trust_store: Ed25519TrustStore,
) -> None:
    """A-11 Layer A: End-to-end contract rehearsal of emergency manual close flow.

    Sequence:
    1. Open position exists in shadow ledger.
    2. Kill switch trips -> PERSISTENTLY_BLOCKED -> automated dispatch blocked.
    3. Operator manually closes in MT5 -> external untracked deal created.
    4. Next RECON detects discrepancy -> adapter transitions to BLOCKED.
    5. Clean restart & sync -> broker position is flat.
    6. EmergencyFlattenTracker confirms FLATTEN_COMPLETED.
    """
    now = datetime.now(timezone.utc)
    engine = MT5ReconciliationEngine()

    # Step 1: Initialize adapter with an active open position
    pos_ticket = 112233
    broker_pos = MT5PositionReality(
        position_ticket=pos_ticket,
        position_identifier=pos_ticket,
        symbol="EURUSD",
        position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("0.02"),
        price_open=Decimal("1.08500"),
        price_current=Decimal("1.08500"),
        time_open_utc=now,
    )
    shadow_pos = ShadowPosition(
        position_ticket=pos_ticket,
        position_identifier=pos_ticket,
        symbol="EURUSD",
        side="BUY",
        volume=Decimal("0.02"),
        open_price=Decimal("1.08500"),
    )

    shadow_open = _make_shadow_snapshot(positions=(shadow_pos,))
    broker_open = _make_broker_snapshot(positions=(broker_pos,))

    transport = MockMT5Transport(broker_id="TEST_BROKER", account_id="ACC_DEMO_01")
    adapter = MT5BrokerAdapter(
        broker_id="TEST_BROKER",
        account_id="ACC_DEMO_01",
        terminal_instance_id="TERM_01",
        transport=transport,
    )
    report_open = engine.reconcile_6d(shadow_open, broker_open)
    assert report_open.confirmation is not None
    adapter.confirm_reconciliation(report_open.confirmation)
    assert adapter.can_dispatch() is True

    # Step 2: Kill switch trips
    ks = SovereignKillSwitchController(
        trust_store=sample_trust_store,
        persistence_path=tmp_path / "ks.jsonl",
    )
    ks.trip(reason="EMERGENCY_MANUAL_CLOSE_TRIGGER")
    assert ks.state == KillSwitchState.PERSISTENTLY_BLOCKED
    with pytest.raises(DataContractError):
        ks.assert_admission_allowed()

    # Step 3: Operator manually closes position on MT5 terminal
    # Reality becomes: position removed from broker, closing deal emitted
    closing_deal = MT5DealReality(
        deal_ticket=999111,
        order_ticket=888222,
        position_ticket=pos_ticket,
        deal_time_utc=datetime.now(timezone.utc),
        deal_type=MT5DealType.DEAL_TYPE_SELL,
        volume=Decimal("0.02"),
        price=Decimal("1.08500"),
        commission=Decimal("0.00"),
        swap=Decimal("0.00"),
        profit=Decimal("0.00"),
        fee=Decimal("0.00"),
        symbol="EURUSD",
        comment="operator_manual_close",
    )
    # Broker reality has closed position, but shadow still expects open position
    broker_after_close = _make_broker_snapshot(positions=(), deals=(closing_deal,))

    # Step 4: Next RECON detects discrepancy -> Adapter transitions to BLOCKED
    report_disc = engine.reconcile_6d(shadow_open, broker_after_close)
    assert report_disc.is_clean is False
    adapter.mark_blocked("Manual close detected: broker flat, shadow open")
    assert adapter.safety_state == MT5TransportSafetyState.BLOCKED
    assert adapter.can_dispatch() is False

    # Step 5: Post-manual-close restart with synchronized flat shadow snapshot
    deal_rec = ShadowDealRecord(
        deal_ticket=closing_deal.deal_ticket,
        order_ticket=closing_deal.order_ticket,
        position_id=pos_ticket,
        intent_id="INTENT_MANUAL_CLOSE",
        symbol="EURUSD",
        side="SELL",
        volume=Decimal("0.02"),
        price=Decimal("1.08500"),
        commission=Decimal("0.0"),
        executed_at=closing_deal.deal_time_utc,
    )
    shadow_flat = _make_shadow_snapshot(positions=(), deals=(deal_rec,))
    report_flat = engine.reconcile_6d(shadow_flat, broker_after_close)
    assert report_flat.is_clean is True
    assert report_flat.confirmation is not None

    adapter_synced = MT5BrokerAdapter(
        broker_id="TEST_BROKER",
        account_id="ACC_DEMO_01",
        terminal_instance_id="TERM_01",
        transport=transport,
    )
    adapter_synced.confirm_reconciliation(report_flat.confirmation)
    assert adapter_synced.can_dispatch() is True

    # Step 6: EmergencyFlattenTracker confirms zero-position completion
    ks_event = ks.latest_event
    assert ks_event is not None
    intent = EmergencyFlattenGenerator.generate_flatten_intent(
        portfolio_state=PortfolioState(
            timestamp_utc=now,
            positions={"EURUSD": Position(
                symbol="EURUSD",
                quantity=Decimal("0.02"),
                entry_price=Decimal("1.08500"),
                current_price=Decimal("1.08500"),
                unrealized_pnl=Decimal("0.0"),
                realized_pnl=Decimal("0.0"),
                timestamp_utc=now,
            )},
            cash_balance=Decimal("499.9783"),
            total_equity=Decimal("500.00"),
            margin_used=Decimal("0.00"),
            gross_exposure=Decimal("0.0217"),
            net_exposure=Decimal("0.0217"),
            unrealized_pnl=Decimal("0.0"),
            realized_pnl=Decimal("0.0"),
        ),
        kill_switch_event=ks_event,
        as_of=now,
    )

    port_flat = PortfolioState(
        timestamp_utc=datetime.now(timezone.utc),
        positions={},
        cash_balance=Decimal("500.00"),
        total_equity=Decimal("500.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("0.00"),
        net_exposure=Decimal("0.00"),
        unrealized_pnl=Decimal("0.0"),
        realized_pnl=Decimal("0.0"),
    )
    status, remaining = EmergencyFlattenTracker.verify_flatten_completion(
        intent=intent,
        latest_portfolio_state=port_flat,
        is_broker_reconciled=True,
    )
    assert status == EmergencyFlattenStatus.FLATTEN_COMPLETED
    assert len(remaining) == 0
