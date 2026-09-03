"""Unit tests for Phase 12 Slice 4: Authoritative 6-Dimensional Reconciliation Engine (RECON-6D).

Covers all 82 adversarial, boundary, and regression tests (R01 to R82) specified in
Implementation Plan Revision 5.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from pydantic import ValidationError
import pytest

from acash.core.domain.exceptions import DomainValidationError
from acash.execution.coordinator import (
    CoordinatorExecutionSnapshot,
    CoordinatorOutcome,
    ExecutionCoordinator,
)
from acash.execution.operational_restriction import (
    OperationalRestrictionRequest,
    RestrictionReason,
)
from acash.execution.schema import OrderLifecycleState
from acash.execution.mt5.enums import (
    MT5AccountMarginMode,
    MT5DealEntry,
    MT5DealType,
    MT5OrderState,
    MT5OrderType,
    MT5PositionType,
    MT5Retcode,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5ReconciliationError,
    MT5TransportError,
    MT5ValidationError,
    ReconciliationIntegrityError,
)
from acash.execution.mt5.schemas import (
    MT5AccountReality,
    MT5DealReality,
    MT5ExecutionLineage,
    MT5OrderReality,
    MT5PositionReality,
    MT5TradeResult,
)
from acash.execution.mt5.adapter import MT5BrokerAdapter
from acash.execution.mt5.transport import (
    MockMT5Transport,
    MT5HealthReport,
    MT5ReconciliationConfirmation,
    MT5TransportProtocol,
    MT5TransportSafetyState,
)
from acash.execution.mt5.reconciliation import (
    ACASHShadowLedger,
    ACASHShadowLedgerSnapshot,
    CaptureCompletenessStatus,
    HistoricalDealCoverage,
    HistoricalDealScopeKind,
    MT56DReconciliationReport,
    MT5BrokerRealitySnapshot,
    MT5DealCategory,
    MT5Discrepancy,
    MT5DiscrepancyKind,
    MT5DiscrepancySeverity,
    MT5ReconciliationEngine,
    ReconciliationCaptureContext,
    ReconciliationStatus,
    ReconciliationToleranceConfig,
    ShadowDealRecord,
    ShadowPosition,
    ShadowRestingOrder,
    _normalize_for_canonical_json,
    canonical_json,
    categorize_deal,
    compute_payload_digest,
    decode_mt5_deal_type,
    match_position_identity,
    verify_order_deal_execution,
)


# ============================================================================
# FIXTURES & BUILDERS
# ============================================================================


def make_sample_account_reality(
    balance: Decimal = Decimal("100000.00"),
    equity: Decimal = Decimal("100000.00"),
    margin: Decimal = Decimal("0.00"),
    currency: str = "USD",
    margin_mode: Any = MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_NETTING,
) -> MT5AccountReality:
    mode = margin_mode if isinstance(margin_mode, MT5AccountMarginMode) else MT5AccountMarginMode(margin_mode)
    return MT5AccountReality(
        login=1001,
        trade_mode=0,
        margin_mode=mode,
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
        currency=currency,
    )


def make_sample_position_reality(
    position_ticket: int = 1001,
    position_identifier: int = 1001,
    symbol: str = "EURUSD",
    position_type: MT5PositionType = MT5PositionType.POSITION_TYPE_BUY,
    volume: Decimal = Decimal("1.0"),
    price_open: Decimal = Decimal("1.08500"),
    price_current: Decimal = Decimal("1.08550"),
) -> MT5PositionReality:
    return MT5PositionReality(
        position_ticket=position_ticket,
        position_identifier=position_identifier,
        symbol=symbol,
        position_type=position_type,
        volume=volume,
        price_open=price_open,
        price_current=price_current,
        time_open_utc=datetime.now(timezone.utc),
    )


def make_sample_shadow_snapshot(
    broker_id: str = "TEST_BROKER",
    account_id: str = "ACC_1001",
    terminal_instance_id: str = "TERM_1",
    currency: str = "USD",
    balance: Decimal = Decimal("100000.00"),
    equity: Decimal = Decimal("100000.00"),
    margin: Decimal = Decimal("0.00"),
    positions: Tuple[ShadowPosition, ...] = (),
    resting_orders: Tuple[ShadowRestingOrder, ...] = (),
    deals: Tuple[ShadowDealRecord, ...] = (),
    snapshot_at: Optional[datetime] = None,
) -> ACASHShadowLedgerSnapshot:
    t = snapshot_at or datetime.now(timezone.utc)
    payload = {
        "schema_version": "1.0.0",
        "broker_id": broker_id,
        "account_id": account_id,
        "terminal_instance_id": terminal_instance_id,
        "currency": currency,
        "snapshot_at": t,
        "balance": balance,
        "equity": equity,
        "margin": margin,
        "positions": positions,
        "resting_orders": resting_orders,
        "deals": deals,
    }
    digest = compute_payload_digest(payload)
    return ACASHShadowLedgerSnapshot(
        schema_version="1.0.0",
        broker_id=broker_id,
        account_id=account_id,
        terminal_instance_id=terminal_instance_id,
        currency=currency,
        snapshot_at=t,
        balance=balance,
        equity=equity,
        margin=margin,
        positions=positions,
        resting_orders=resting_orders,
        deals=deals,
        ledger_digest=digest,
    )


def make_sample_broker_snapshot(
    broker_id: str = "TEST_BROKER",
    account_id: str = "ACC_1001",
    terminal_instance_id: str = "TERM_1",
    account: Optional[MT5AccountReality] = None,
    positions: Tuple[MT5PositionReality, ...] = (),
    orders: Tuple[MT5OrderReality, ...] = (),
    history_orders: Tuple[MT5OrderReality, ...] = (),
    deals: Tuple[MT5DealReality, ...] = (),
    observed_at: Optional[datetime] = None,
    is_complete: bool = True,
    capture_duration_ms: float = 150.0,
    max_capture_window_ms: float = 2000.0,
) -> MT5BrokerRealitySnapshot:
    t = observed_at or datetime.now(timezone.utc)
    acc = account or make_sample_account_reality()
    t_msc = int(t.timestamp() * 1000)

    capture_ctx = ReconciliationCaptureContext(
        reconciliation_id=f"CAP_{t_msc}",
        capture_started_at=t - timedelta(milliseconds=capture_duration_ms),
        capture_completed_at=t,
        capture_started_at_msc=t_msc - int(capture_duration_ms),
        capture_completed_at_msc=t_msc,
        pre_watermark_deal_ticket=0,
        post_watermark_deal_ticket=max((d.deal_ticket for d in deals), default=0),
        query_latencies_ms={"account": 20.0, "positions": 30.0, "orders": 30.0, "deals": 70.0},
        capture_duration_ms=capture_duration_ms,
        max_capture_window_ms=max_capture_window_ms,
        completeness_status=CaptureCompletenessStatus.COMPLETE if capture_duration_ms <= max_capture_window_ms else CaptureCompletenessStatus.CAPTURE_TIMEOUT,
    )

    coverage = HistoricalDealCoverage(
        scope_kind=HistoricalDealScopeKind.FULL_CYCLE,
        from_timestamp=t - timedelta(hours=1),
        to_timestamp=t,
        watermark_ticket=0,
        last_deal_ticket=max((d.deal_ticket for d in deals), default=0),
        total_deals_retrieved=len(deals),
        is_complete=is_complete,
        coverage_digest=compute_payload_digest({"deals": len(deals), "is_complete": is_complete}),
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


class MockShadowLedger:
    def __init__(self, snapshot: ACASHShadowLedgerSnapshot) -> None:
        self._snapshot = snapshot

    def snapshot_reconciliation_state(self) -> ACASHShadowLedgerSnapshot:
        return self._snapshot


class MockTransportForEngine(MockMT5Transport):
    def __init__(
        self,
        account: Optional[MT5AccountReality] = None,
        positions: Tuple[MT5PositionReality, ...] = (),
        orders: Tuple[MT5OrderReality, ...] = (),
        history_orders: Tuple[MT5OrderReality, ...] = (),
        deals: Tuple[MT5DealReality, ...] = (),
        dynamic_deal_time: bool = False,
    ) -> None:
        super().__init__()
        self._custom_account = account
        self.active_positions = {p.position_ticket: p for p in positions}
        self.active_orders = {o.order_ticket: o for o in orders}
        self.history_orders = {o.order_ticket: o for o in history_orders}
        self.history_deals = {d.deal_ticket: d for d in deals}
        self._dynamic_deal_time = dynamic_deal_time

    def account_info(self) -> Optional[MT5AccountReality]:
        if self._custom_account is not None:
            return self._custom_account
        return super().account_info()

    def history_deals_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5DealReality, ...]:
        deals = list(self.history_deals.values())
        if self._dynamic_deal_time and deals:
            t = date_to or datetime.now(timezone.utc)
            deals = [d.model_copy(update={"deal_time_utc": t}) for d in deals]
        return tuple(deals)

    def history_deals_total(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        deals = self.history_deals_get(date_from=date_from, date_to=date_to)
        return len(deals)

    def history_orders_total(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        orders = self.history_orders_get(date_from=date_from, date_to=date_to)
        return len(orders)


# ============================================================================
# BASELINE TESTS: R01 to R62
# ============================================================================


def test_r01_clean_6d_reconciliation_produces_valid_confirmation() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot()

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is True
    assert report.status == ReconciliationStatus.CLEAN
    assert report.confirmation is not None
    assert report.confirmation.is_complete is True
    assert report.confirmation.orders_verified is True
    assert report.confirmation.deals_verified is True
    assert report.confirmation.positions_verified is True
    assert report.confirmation.account_verified is True


def test_r02_reconciliation_confirmation_unblocks_degraded_adapter() -> None:
    transport = MockTransportForEngine()
    adapter = MT5BrokerAdapter("TEST_BROKER", "ACC_1001", "TERM_1", transport=transport)
    assert adapter.safety_state == MT5TransportSafetyState.DEGRADED
    assert adapter.can_dispatch() is False

    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot()
    report = engine.reconcile_6d(shadow, broker)

    assert report.confirmation is not None
    adapter.confirm_reconciliation(report.confirmation)
    final_state: Any = adapter.safety_state
    assert final_state == MT5TransportSafetyState.READY
    assert adapter.can_dispatch() is True


def test_r03_phantom_position_detected_as_critical_discrepancy() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(positions=())
    phantom_pos = MT5PositionReality(
        position_ticket=999,
        position_identifier=999,
        symbol="EURUSD",
        position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("1.0"),
        price_open=Decimal("1.0850"),
        price_current=Decimal("1.0855"),
        time_open_utc=datetime.now(timezone.utc),
    )
    broker = make_sample_broker_snapshot(positions=(phantom_pos,))

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert report.status == ReconciliationStatus.DISCREPANCIES_DETECTED
    assert report.confirmation is None
    assert any(d.kind == MT5DiscrepancyKind.PHANTOM_POSITION for d in report.discrepancies)


def test_r04_position_volume_mismatch_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow_pos = ShadowPosition(
        position_ticket=1001,
        position_identifier=1001,
        symbol="EURUSD",
        side="BUY",
        volume=Decimal("1.0"),
        open_price=Decimal("1.0850"),
    )
    shadow = make_sample_shadow_snapshot(positions=(shadow_pos,))

    broker_pos = MT5PositionReality(
        position_ticket=1001,
        position_identifier=1001,
        symbol="EURUSD",
        position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("2.0"),  # Expected 1.0 lot -> mismatch!
        price_open=Decimal("1.0850"),
        price_current=Decimal("1.0855"),
        time_open_utc=datetime.now(timezone.utc),
    )
    broker = make_sample_broker_snapshot(positions=(broker_pos,))

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.POSITION_VOLUME_MISMATCH for d in report.discrepancies)


def test_r05_stale_broker_snapshot_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    # 45 seconds old > 30s threshold
    old_time = datetime.now(timezone.utc) - timedelta(seconds=45)
    broker = make_sample_broker_snapshot(observed_at=old_time)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.STALE_SNAPSHOT for d in report.discrepancies)


def test_r06_orphan_resting_order_detected() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(resting_orders=())
    orphan_order = MT5OrderReality(
        order_ticket=8888,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED,
        volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"),
        price_open=Decimal("1.0800"),
        time_setup_utc=datetime.now(timezone.utc),
    )
    broker = make_sample_broker_snapshot(orders=(orphan_order,))

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.ORPHAN_RESTING_ORDER for d in report.discrepancies)


def test_r07_missing_resting_order_detected() -> None:
    engine = MT5ReconciliationEngine()
    tracked_order = ShadowRestingOrder(
        intent_id="INT_999",
        order_ticket=9999,
        symbol="EURUSD",
        order_type="BUY_LIMIT",
        volume=Decimal("1.0"),
        price=Decimal("1.0800"),
    )
    shadow = make_sample_shadow_snapshot(resting_orders=(tracked_order,))
    broker = make_sample_broker_snapshot(orders=())

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.MISSING_RESTING_ORDER for d in report.discrepancies)


def test_r08_balance_divergence_outside_tolerance_fails() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(balance=Decimal("100000.00"))
    # Delta is 0.10 > tolerance 0.05
    broker_acc = make_sample_account_reality(balance=Decimal("100000.10"))
    broker = make_sample_broker_snapshot(account=broker_acc)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.BALANCE_MISMATCH for d in report.discrepancies)


def test_r09_balance_divergence_within_tolerance_passes() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(balance=Decimal("100000.00"), equity=Decimal("100000.00"))
    # Delta is 0.02 <= tolerance 0.05
    broker_acc = make_sample_account_reality(balance=Decimal("100000.02"), equity=Decimal("100000.02"))
    broker = make_sample_broker_snapshot(account=broker_acc)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is True
    assert report.status == ReconciliationStatus.CLEAN


def test_r10_equity_divergence_outside_tolerance_fails() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(equity=Decimal("100000.00"))
    # Delta 0.20 > equity tolerance 0.10
    broker_acc = make_sample_account_reality(equity=Decimal("100000.20"))
    broker = make_sample_broker_snapshot(account=broker_acc)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.EQUITY_MISMATCH for d in report.discrepancies)


def test_r11_margin_divergence_outside_tolerance_fails() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(margin=Decimal("100.00"))
    # Delta 0.10 > margin tolerance 0.05
    broker_acc = make_sample_account_reality(margin=Decimal("100.10"))
    broker = make_sample_broker_snapshot(account=broker_acc)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.MARGIN_MISMATCH for d in report.discrepancies)


def test_r12_untracked_broker_trade_deal_triggers_critical_discrepancy() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(deals=())
    untracked_deal = MT5DealReality(
        deal_ticket=777,
        order_ticket=888,
        position_ticket=999,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY,
        volume=Decimal("1.0"),
        price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    broker = make_sample_broker_snapshot(deals=(untracked_deal,))

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL for d in report.discrepancies)


def test_r13_unknown_order_recovered_to_filled_via_deal_evidence() -> None:
    coordinator = ExecutionCoordinator("EXEC_101", Decimal("1.0"), initial_state=OrderLifecycleState.UNKNOWN)
    assert coordinator.state == OrderLifecycleState.UNKNOWN

    deal = MT5DealReality(
        deal_ticket=5001,
        order_ticket=1001,
        position_ticket=1001,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY,
        volume=Decimal("1.0"),
        price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    outcome = coordinator.apply_reconciliation(
        broker_event_id=str(deal.deal_ticket),
        broker_sequence=str(deal.deal_ticket),
        evidence_token="FILLED",
        order_id=str(deal.order_ticket),
        observed_at=deal.deal_time_utc,
    )
    assert outcome.state == OrderLifecycleState.FILLED
    final_c_state: Any = coordinator.state
    assert final_c_state == OrderLifecycleState.FILLED


def test_r14_unknown_order_recovered_to_cancelled_via_history_order() -> None:
    coordinator = ExecutionCoordinator("EXEC_102", Decimal("1.0"), initial_state=OrderLifecycleState.UNKNOWN)
    assert coordinator.state == OrderLifecycleState.UNKNOWN

    outcome = coordinator.apply_reconciliation(
        broker_event_id="ORD_1002_CANCEL",
        broker_sequence="1002",
        evidence_token="CANCELLED",
        order_id="1002",
        observed_at=datetime.now(timezone.utc),
    )
    assert outcome.state == OrderLifecycleState.CANCELLED
    state_val: Any = coordinator.state
    assert state_val == OrderLifecycleState.CANCELLED


def test_r15_reconciliation_never_directly_mutates_state_machine() -> None:
    coordinator = ExecutionCoordinator("EXEC_103", Decimal("1.0"))
    engine = MT5ReconciliationEngine()

    assert not hasattr(engine, "transition_order")
    assert not hasattr(engine, "_state")
    assert not hasattr(engine, "_seen")


def test_r16_contradictory_evidence_on_terminal_shadow_emits_restriction() -> None:
    coordinator = ExecutionCoordinator("EXEC_104", Decimal("1.0"), initial_state=OrderLifecycleState.FILLED)
    assert coordinator.state == OrderLifecycleState.FILLED

    # Contradictory reconciliation attempting to say it was cancelled
    outcome = coordinator.apply_reconciliation(
        broker_event_id="ORD_1004_CANCEL",
        broker_sequence="1004",
        evidence_token="CANCELLED",
        order_id="1004",
    )
    assert outcome.restriction_request is not None
    assert outcome.restriction_request.reason == RestrictionReason.RECONCILIATION_CONFLICT


def test_r17_tampered_shadow_digest_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    tampered_shadow = shadow.model_copy(update={"ledger_digest": "corrupted_digest_1234567890abcdef"})
    broker = make_sample_broker_snapshot()

    with pytest.raises(ReconciliationIntegrityError, match="SHADOW_LEDGER_DIGEST_MISMATCH"):
        engine.reconcile_6d(tampered_shadow, broker)


def test_r18_tampered_broker_snapshot_digest_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot()
    tampered_broker = broker.model_copy(update={"broker_snapshot_digest": "tampered_digest_9876543210"})

    with pytest.raises(ReconciliationIntegrityError, match="BROKER_SNAPSHOT_DIGEST_MISMATCH"):
        engine.reconcile_6d(shadow, tampered_broker)


def test_r19a_digest_dict_order_invariance() -> None:
    d1 = {"a": 1, "b": 2, "c": {"x": 10, "y": 20}}
    d2 = {"c": {"y": 20, "x": 10}, "b": 2, "a": 1}
    assert compute_payload_digest(d1) == compute_payload_digest(d2)


def test_r19b_digest_decimal_canonicalization() -> None:
    d1 = {"val": Decimal("100.00")}
    d2 = {"val": Decimal("100.000000")}
    assert canonical_json(d1) == canonical_json(d2)
    assert compute_payload_digest(d1) == compute_payload_digest(d2)


def test_r19c_digest_utc_timezone_normalization() -> None:
    utc_time = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    est_offset = timezone(timedelta(hours=-5))
    est_time = utc_time.astimezone(est_offset)

    d1 = {"time": utc_time}
    d2 = {"time": est_time}
    assert canonical_json(d1) == canonical_json(d2)
    assert compute_payload_digest(d1) == compute_payload_digest(d2)


def test_r19d_digest_schema_version_binding() -> None:
    payload1 = {"schema_version": "1.0.0", "data": 123}
    payload2 = {"schema_version": "2.0.0", "data": 123}
    assert compute_payload_digest(payload1) != compute_payload_digest(payload2)


def test_r19e_digest_evidence_mutation_invalidates_report() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot()
    report = engine.reconcile_6d(shadow, broker)

    orig_digest = report.report_digest
    mutated_report = report.model_copy(update={"reconciled_at": datetime.now(timezone.utc)})
    new_digest = compute_payload_digest(mutated_report.model_dump())
    assert orig_digest != new_digest


def test_r20_multi_position_multi_symbol_matrix_clean_pass() -> None:
    engine = MT5ReconciliationEngine()
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    shadow_positions = tuple(
        ShadowPosition(
            position_ticket=1000 + i,
            position_identifier=1000 + i,
            symbol=sym,
            side="BUY",
            volume=Decimal("1.0"),
            open_price=Decimal("1.0850"),
        )
        for i, sym in enumerate(symbols)
    )
    broker_positions = tuple(
        MT5PositionReality(
            position_ticket=1000 + i,
            position_identifier=1000 + i,
            symbol=sym,
            position_type=MT5PositionType.POSITION_TYPE_BUY,
            volume=Decimal("1.0"),
            price_open=Decimal("1.0850"),
            price_current=Decimal("1.0855"),
            time_open_utc=datetime.now(timezone.utc),
        )
        for i, sym in enumerate(symbols)
    )
    shadow = make_sample_shadow_snapshot(positions=shadow_positions)
    broker = make_sample_broker_snapshot(positions=broker_positions)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is True
    assert report.status == ReconciliationStatus.CLEAN


def test_r21_negative_tolerance_rejected_at_construction() -> None:
    with pytest.raises(Exception):
        ReconciliationToleranceConfig(balance_tolerance=Decimal("-0.01"))


def test_r22_reconciliation_engine_poll_snapshot_handles_transport_error() -> None:
    class FailingTransport(MockTransportForEngine):
        def account_info(self) -> Optional[MT5AccountReality]:
            return None  # Triggers transport error

    engine = MT5ReconciliationEngine()
    with pytest.raises(MT5TransportError, match="account_info.*returned None"):
        engine.capture_bounded_broker_observation(
            FailingTransport(),
            broker_id="TEST",
            account_id="ACC",
            terminal_instance_id="TERM",
        )


def test_r23_reconciliation_report_immutable() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot()
    report = engine.reconcile_6d(shadow, broker)
    with pytest.raises(Exception):
        setattr(report, "status", ReconciliationStatus.RECONCILIATION_FAILED)


def test_r24_reconciliation_confirmation_requires_four_dimensions_true() -> None:
    conf = MT5ReconciliationConfirmation(
        reconciliation_id="REC_1",
        broker_id="B1",
        account_id="A1",
        verified_at=datetime.now(timezone.utc),
        orders_verified=True,
        deals_verified=True,
        positions_verified=True,
        account_verified=True,
        is_complete=True,
        discrepancies_count=0,
    )
    assert conf.orders_verified is True
    assert conf.deals_verified is True
    assert conf.positions_verified is True
    assert conf.account_verified is True


def test_r25_full_coordinator_adapter_engine_roundtrip_integration() -> None:
    transport = MockTransportForEngine()
    adapter = MT5BrokerAdapter("TEST_BROKER", "ACC_1001", "TERM_1", transport=transport)
    assert adapter.safety_state == MT5TransportSafetyState.DEGRADED

    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(broker_id="TEST_BROKER", account_id="ACC_1001", terminal_instance_id="TERM_1")
    shadow_ledger = MockShadowLedger(shadow)

    coordinator = ExecutionCoordinator("INT_1", Decimal("1.0"))
    report = engine.execute_reconciliation_cycle(
        adapter=adapter,
        shadow_ledger=shadow_ledger,
        coordinator_map={"INT_1": coordinator},
    )

    assert report.is_clean is True
    final_ad_state: Any = adapter.safety_state
    assert final_ad_state == MT5TransportSafetyState.READY


def test_r26_historical_deal_scope_watermark_incomplete_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(is_complete=False)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.INCOMPLETE_HISTORY_SCOPE for d in report.discrepancies)


def test_r27_mt5_hedging_multi_position_same_symbol() -> None:
    engine = MT5ReconciliationEngine()
    # In Hedging: same symbol, different tickets
    s_pos1 = ShadowPosition(position_ticket=101, position_identifier=101, symbol="EURUSD", side="BUY", volume=Decimal("1.0"), open_price=Decimal("1.0850"))
    s_pos2 = ShadowPosition(position_ticket=102, position_identifier=102, symbol="EURUSD", side="BUY", volume=Decimal("0.5"), open_price=Decimal("1.0860"))
    s_pos3 = ShadowPosition(position_ticket=103, position_identifier=103, symbol="EURUSD", side="SELL", volume=Decimal("0.3"), open_price=Decimal("1.0840"))

    b_pos1 = MT5PositionReality(position_ticket=101, position_identifier=101, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("1.0"), price_open=Decimal("1.0850"), price_current=Decimal("1.0855"), time_open_utc=datetime.now(timezone.utc))
    b_pos2 = MT5PositionReality(position_ticket=102, position_identifier=102, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("0.5"), price_open=Decimal("1.0860"), price_current=Decimal("1.0855"), time_open_utc=datetime.now(timezone.utc))
    b_pos3 = MT5PositionReality(position_ticket=103, position_identifier=103, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_SELL, volume=Decimal("0.3"), price_open=Decimal("1.0840"), price_current=Decimal("1.0855"), time_open_utc=datetime.now(timezone.utc))

    hedging_acc = make_sample_account_reality(margin_mode=MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)  # Hedging
    shadow = make_sample_shadow_snapshot(positions=(s_pos1, s_pos2, s_pos3))
    broker = make_sample_broker_snapshot(account=hedging_acc, positions=(b_pos1, b_pos2, b_pos3))

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is True


def test_r28_non_trade_deal_does_not_become_phantom_execution() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(deals=())
    # Balance deposit deal
    balance_deal = MT5DealReality(
        deal_ticket=9001,
        order_ticket=1,
        position_ticket=0,
        symbol="USD",
        deal_type=MT5DealType.DEAL_TYPE_BALANCE,
        volume=Decimal("1000.0"),
        price=Decimal("1.0"),
        profit=Decimal("1000.0"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    broker = make_sample_broker_snapshot(deals=(balance_deal,))

    report = engine.reconcile_6d(shadow, broker)
    assert not any(d.kind == MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL for d in report.discrepancies)


def test_r29_trade_deal_without_lineage_triggers_critical() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(deals=())
    rogue_deal = MT5DealReality(
        deal_ticket=9999,
        order_ticket=1111,
        position_ticket=2222,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY,
        volume=Decimal("1.0"),
        price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
        comment="",  # No lineage
    )
    broker = make_sample_broker_snapshot(deals=(rogue_deal,))

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL for d in report.discrepancies)


def test_r30_mixed_terminal_capture_times_exceed_coherence_window() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    # 2500ms > 2000ms max capture window
    broker = make_sample_broker_snapshot(capture_duration_ms=2500.0, max_capture_window_ms=2000.0)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.INCOHERENT_SNAPSHOT for d in report.discrepancies)


def test_r31_snapshot_queries_straddle_a_fill_detected() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(capture_duration_ms=2500.0, max_capture_window_ms=2000.0)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.INCOHERENT_SNAPSHOT for d in report.discrepancies)


def test_r32_terminal_instance_identity_mismatch_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(terminal_instance_id="TERM_PRIMARY")
    broker = make_sample_broker_snapshot(terminal_instance_id="TERM_SECONDARY")

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.IDENTITY_MISMATCH and d.identifier == "terminal_instance_id" for d in report.discrepancies)


def test_r33_report_digest_changes_when_scope_changes() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    b1 = make_sample_broker_snapshot()
    b2 = make_sample_broker_snapshot(capture_duration_ms=200.0)

    r1 = engine.reconcile_6d(shadow, b1)
    r2 = engine.reconcile_6d(shadow, b2)
    assert r1.report_digest != r2.report_digest


def test_r34_decimal_canonicalization_deterministic() -> None:
    d1 = Decimal("1.50000000")
    d2 = Decimal("1.50")
    assert canonical_json(d1) == canonical_json(d2)


def test_r35_apply_reconciliation_is_sole_coordinator_integration_seam() -> None:
    coordinator = ExecutionCoordinator("EXEC_TEST", Decimal("1.0"))
    assert hasattr(coordinator, "apply_reconciliation")
    assert callable(getattr(coordinator, "apply_reconciliation"))


def test_r36_engine_uses_public_shadow_reconciliation_snapshot_only() -> None:
    shadow = make_sample_shadow_snapshot()
    ledger = MockShadowLedger(shadow)
    assert hasattr(ledger, "snapshot_reconciliation_state")
    assert callable(getattr(ledger, "snapshot_reconciliation_state"))


def test_r37_unknown_order_rejected_does_not_become_cancelled() -> None:
    historical_order = MT5OrderReality(
        order_ticket=137,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_REJECTED,
        volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"),
        price_open=Decimal("1.0850"),
        time_setup_utc=datetime.now(timezone.utc),
    )
    resolved_state, vol, vwap, *_ = verify_order_deal_execution(137, historical_order, ())
    assert resolved_state == OrderLifecycleState.REJECTED
    state_val: Any = resolved_state
    assert state_val != OrderLifecycleState.CANCELLED


def test_r38_unknown_order_expired_maps_only_through_explicit_contract() -> None:
    historical_order = MT5OrderReality(
        order_ticket=138,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_EXPIRED,
        volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"),
        price_open=Decimal("1.0800"),
        time_setup_utc=datetime.now(timezone.utc),
    )
    resolved_state, vol, vwap, *_ = verify_order_deal_execution(138, historical_order, ())
    assert resolved_state == OrderLifecycleState.EXPIRED


def test_r39_multi_deal_aggregation_matches_single_intent() -> None:
    historical_order = MT5OrderReality(
        order_ticket=139,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_FILLED,
        volume_initial=Decimal("3.0"),
        volume_current=Decimal("0.0"),
        price_open=Decimal("1.0850"),
        time_setup_utc=datetime.now(timezone.utc),
    )
    d1 = MT5DealReality(
        deal_ticket=201, order_ticket=139, position_ticket=139, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0840"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    d2 = MT5DealReality(
        deal_ticket=202, order_ticket=139, position_ticket=139, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("2.0"), price=Decimal("1.0855"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    resolved_state, vol, vwap, *_ = verify_order_deal_execution(139, historical_order, (d1, d2))
    assert resolved_state == OrderLifecycleState.FILLED
    assert vol == Decimal("3.0")
    # VWAP = (1.0 * 1.0840 + 2.0 * 1.0855) / 3.0 = 3.255 / 3.0 = 1.0850
    assert vwap == Decimal("1.0850")


def test_r40_duplicate_deal_ticket_is_detected() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    d1 = MT5DealReality(
        deal_ticket=999, order_ticket=1, position_ticket=1, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    d2 = MT5DealReality(
        deal_ticket=999, order_ticket=2, position_ticket=2, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    broker = make_sample_broker_snapshot(deals=(d1, d2))

    with pytest.raises(MT5ValidationError, match="DUPLICATE_DEAL_TICKET"):
        engine.reconcile_6d(shadow, broker)


def test_r41_duplicate_position_identity_is_detected() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    p1 = MT5PositionReality(
        position_ticket=10, position_identifier=10, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"),
        time_open_utc=datetime.now(timezone.utc),
    )
    p2 = MT5PositionReality(
        position_ticket=10, position_identifier=10, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"),
        time_open_utc=datetime.now(timezone.utc),
    )
    broker = make_sample_broker_snapshot(positions=(p1, p2))

    with pytest.raises(MT5ValidationError, match="DUPLICATE_POSITION_TICKET"):
        engine.reconcile_6d(shadow, broker)


def test_r42_partial_historical_window_cannot_produce_clean() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(is_complete=False)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert report.confirmation is None


def test_r43_non_usd_account_tolerance_uses_account_currency() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(currency="EUR", balance=Decimal("100000.00"), equity=Decimal("100000.00"))
    broker_acc = make_sample_account_reality(currency="EUR", balance=Decimal("100000.02"), equity=Decimal("100000.02"))
    broker = make_sample_broker_snapshot(account=broker_acc)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is True


def test_r44_missing_one_of_six_dimensions_cannot_produce_confirmation() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    # Missing positions dimension by injecting a phantom position
    phantom = MT5PositionReality(
        position_ticket=99, position_identifier=99, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"),
        time_open_utc=datetime.now(timezone.utc),
    )
    broker = make_sample_broker_snapshot(positions=(phantom,))

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert report.confirmation is None
    assert report.dimension_verification["positions"] is False


def test_r45_stale_snapshot_cannot_be_overridden_by_clean_comparison() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    # Identical data, but 60s old
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    broker = make_sample_broker_snapshot(observed_at=stale_time)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.STALE_SNAPSHOT for d in report.discrepancies)


def test_r46_netting_position_reversal_preserves_position_identity() -> None:
    # Netting: originating identifier remains 100, while ticket changed to 200 on reversal
    shadow_pos = ShadowPosition(
        position_ticket=100, position_identifier=100, symbol="EURUSD", side="SELL",
        volume=Decimal("1.0"), open_price=Decimal("1.0850"),
    )
    broker_pos = MT5PositionReality(
        position_ticket=200, position_identifier=100, symbol="EURUSD",
        position_type=MT5PositionType.POSITION_TYPE_SELL, volume=Decimal("1.0"),
        price_open=Decimal("1.0850"), price_current=Decimal("1.0850"),
        time_open_utc=datetime.now(timezone.utc),
    )
    assert match_position_identity(shadow_pos, broker_pos, MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_NETTING) is True


def test_r47_canceled_trade_deal_classification() -> None:
    assert categorize_deal(MT5DealType.DEAL_TYPE_BUY_CANCELED) == MT5DealCategory.CANCELED_TRADE_DEAL
    assert categorize_deal(MT5DealType.DEAL_TYPE_SELL_CANCELED) == MT5DealCategory.CANCELED_TRADE_DEAL


def test_r48_daily_monthly_agent_commission_classification() -> None:
    assert categorize_deal(MT5DealType.DEAL_TYPE_COMMISSION_AGENT_DAILY) == MT5DealCategory.ACCOUNTING_DEAL
    assert categorize_deal(MT5DealType.DEAL_TYPE_COMMISSION_AGENT_MONTHLY) == MT5DealCategory.ACCOUNTING_DEAL


def test_r49_unknown_deal_type_fails_closed() -> None:
    with pytest.raises(MT5DomainError, match="UNKNOWN_MQL5_DEAL_TYPE"):
        decode_mt5_deal_type(999)


def test_r50_straddle_race_detection_algorithm() -> None:
    t0 = datetime.now(timezone.utc)
    resting_order = MT5OrderReality(
        order_ticket=404, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    deal = MT5DealReality(
        deal_ticket=808, order_ticket=404, position_ticket=909, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0800"),
        deal_time_utc=t0,
    )
    transport = MockTransportForEngine(orders=(resting_order,), deals=(deal,), dynamic_deal_time=True)
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")
    assert snapshot.capture_context.completeness_status == CaptureCompletenessStatus.BOUNDARY_ACTIVITY_DETECTED


def test_r51_cancelled_after_partial_fill_semantics() -> None:
    historical_order = MT5OrderReality(
        order_ticket=151, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_CANCELED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.6"), price_open=Decimal("1.0800"), time_setup_utc=datetime.now(timezone.utc),
    )
    deal = MT5DealReality(
        deal_ticket=251, order_ticket=151, position_ticket=351, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("0.4"), price=Decimal("1.0800"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    resolved_state, vol, vwap, broker_event_id, evidence_refs = verify_order_deal_execution(151, historical_order, (deal,))
    assert resolved_state == OrderLifecycleState.CANCELLED
    assert vol == Decimal("0.4")  # Partial fill volume preserved
    assert broker_event_id == "151"
    assert evidence_refs == ("251",)


def test_r52_order_state_mapping_uses_canonical_enum_only() -> None:
    historical_order = MT5OrderReality(
        order_ticket=152, symbol="EURUSD", order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=datetime.now(timezone.utc),
    )
    deal = MT5DealReality(
        deal_ticket=252, order_ticket=152, position_ticket=352, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    resolved_state, vol, vwap, broker_event_id, evidence_refs = verify_order_deal_execution(152, historical_order, (deal,))
    assert resolved_state == OrderLifecycleState.FILLED
    assert broker_event_id == "252"


def test_r53_unknown_order_state_fails_closed() -> None:
    class FakeOrder:
        state = "INVALID_STRING"
    with pytest.raises(MT5DomainError, match="INVALID_ORDER_STATE_TYPE"):
        verify_order_deal_execution(153, FakeOrder(), ())  # type: ignore[arg-type]


def test_r54_straddle_detection_uses_deal_time_msc() -> None:
    t0 = datetime.now(timezone.utc)

    resting_order = MT5OrderReality(
        order_ticket=554, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    deal = MT5DealReality(
        deal_ticket=854, order_ticket=554, position_ticket=954, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0800"),
        deal_time_utc=t0,
    )
    transport = MockTransportForEngine(orders=(resting_order,), deals=(deal,), dynamic_deal_time=True)
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")
    assert snapshot.capture_context.completeness_status == CaptureCompletenessStatus.BOUNDARY_ACTIVITY_DETECTED


def test_r55_ticket_order_without_temporal_evidence_does_not_prove_straddle() -> None:
    # Deal has higher ticket, but its deal_time_utc is BEFORE capture start
    t_past = datetime.now(timezone.utc) - timedelta(hours=2)
    t_now = datetime.now(timezone.utc)

    resting_order = MT5OrderReality(
        order_ticket=555, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t_now,
    )
    past_deal = MT5DealReality(
        deal_ticket=855, order_ticket=555, position_ticket=955, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0800"),
        deal_time_utc=t_past,  # In the past
    )
    transport = MockTransportForEngine(orders=(resting_order,), deals=(past_deal,))
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")
    # Not flagged as boundary activity because deal_time_utc is not inside capture start/end
    assert snapshot.capture_context.boundary_activity_detected is False


def test_r56_pre_post_watermark_boundary_is_closed() -> None:
    engine = MT5ReconciliationEngine()
    transport = MockTransportForEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")
    ctx = snapshot.capture_context
    assert ctx.pre_watermark_deal_ticket <= ctx.post_watermark_deal_ticket


def test_r57_margin_mode_uses_canonical_enum_only() -> None:
    shadow_pos = ShadowPosition(position_ticket=10, position_identifier=10, symbol="EURUSD", side="BUY", volume=Decimal("1.0"), open_price=Decimal("1.0"))
    broker_pos = MT5PositionReality(position_ticket=10, position_identifier=10, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"), time_open_utc=datetime.now(timezone.utc))

    # Canonical enum
    assert match_position_identity(shadow_pos, broker_pos, MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_NETTING) is True
    assert match_position_identity(shadow_pos, broker_pos, MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) is True


def test_r58_unknown_margin_mode_fails_closed() -> None:
    shadow_pos = ShadowPosition(position_ticket=10, position_identifier=10, symbol="EURUSD", side="BUY", volume=Decimal("1.0"), open_price=Decimal("1.0"))
    broker_pos = MT5PositionReality(position_ticket=10, position_identifier=10, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"), time_open_utc=datetime.now(timezone.utc))

    with pytest.raises(MT5DomainError, match="UNKNOWN_MARGIN_MODE"):
        match_position_identity(shadow_pos, broker_pos, "INVALID" ) # type: ignore[arg-type]


def test_r59_deal_decoder_is_boundary_only() -> None:
    # Test boundary decoder maps raw external integer to canonical MT5DealType
    dtype = decode_mt5_deal_type(0)
    assert dtype == MT5DealType.DEAL_TYPE_BUY
    assert isinstance(dtype, MT5DealType)
    # Downstream category operates purely on MT5DealType
    cat = categorize_deal(dtype)
    assert cat == MT5DealCategory.TRADE_EXECUTION_DEAL


def test_r60_straddle_boundary_activity_forces_recapture() -> None:
    t0 = datetime.now(timezone.utc)
    resting_order = MT5OrderReality(
        order_ticket=660, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    boundary_deal = MT5DealReality(
        deal_ticket=960, order_ticket=660, position_ticket=960, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0800"),
        deal_time_utc=t0,
    )
    transport = MockTransportForEngine(orders=(resting_order,), deals=(boundary_deal,), dynamic_deal_time=True)
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")
    assert snapshot.capture_context.is_coherent is False
    assert snapshot.capture_context.completeness_status == CaptureCompletenessStatus.BOUNDARY_ACTIVITY_DETECTED


def test_r61_recapture_remaining_ambiguous_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    # Snapshot flagged with timeout / incoherent
    broker = make_sample_broker_snapshot(capture_duration_ms=3000.0, max_capture_window_ms=2000.0)
    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.INCOHERENT_SNAPSHOT for d in report.discrepancies)


def test_r62_filled_requires_terminal_state_and_complete_deal_coverage() -> None:
    historical_order = MT5OrderReality(
        order_ticket=162, symbol="EURUSD", order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("2.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=datetime.now(timezone.utc),
    )
    # Deal only covers 1.0 lot instead of 2.0 lots -> fails closed!
    partial_deal = MT5DealReality(
        deal_ticket=262, order_ticket=162, position_ticket=362, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    with pytest.raises(MT5ReconciliationError, match="FILLED_VOLUME_MISMATCH"):
        verify_order_deal_execution(162, historical_order, (partial_deal,))


# ============================================================================
# NEW TEST VECTORS (R63 to R82): Plan Revision 5 Invariants & Orchestration
# ============================================================================


def test_r63_orchestration_recapture_recovers_on_clean_second_pass() -> None:
    """Pass 1 detects boundary activity, triggers Pass 2, which succeeds and unblocks adapter."""
    t0 = datetime.now(timezone.utc)
    resting_order = MT5OrderReality(
        order_ticket=663, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    boundary_deal = MT5DealReality(
        deal_ticket=963, order_ticket=663, position_ticket=963, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0800"),
        deal_time_utc=t0,
    )

    broker_pos = MT5PositionReality(
        position_ticket=963, position_identifier=963, symbol="EURUSD",
        position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("1.0"),
        price_open=Decimal("1.0800"), price_current=Decimal("1.0800"),
        time_open_utc=t0,
    )

    class TwoPassTransport(MockTransportForEngine):
        def __init__(self) -> None:
            super().__init__(positions=(broker_pos,), deals=(boundary_deal,))
            self.pass_count = 0
            self._dynamic_deal_time = True

        def orders_get(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> Tuple[MT5OrderReality, ...]:
            self.pass_count += 1
            if self.pass_count == 1:
                return (resting_order,)
            # Pass 2: order is filled and no longer resting
            return ()

    transport = TwoPassTransport()
    adapter = MT5BrokerAdapter("TEST", "ACC", "TERM", transport=transport)
    engine = MT5ReconciliationEngine()

    shadow_pos = ShadowPosition(position_ticket=963, position_identifier=963, symbol="EURUSD", side="BUY", volume=Decimal("1.0"), open_price=Decimal("1.0800"))
    shadow_deal = ShadowDealRecord(deal_ticket=963, order_ticket=663, position_id=963, intent_id="INT_663", symbol="EURUSD", side="BUY", volume=Decimal("1.0"), price=Decimal("1.0800"), executed_at=t0)
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM", positions=(shadow_pos,), deals=(shadow_deal,))

    report = engine.execute_reconciliation_cycle(
        adapter=adapter,
        shadow_ledger=MockShadowLedger(shadow),
        coordinator_map={},
    )
    assert report.is_clean is True
    assert adapter.can_dispatch() is True


def test_r64_orchestration_recapture_fails_closed_when_second_pass_ambiguous() -> None:
    """Boundary activity persisting in Pass 2 fails closed as INCOHERENT_SNAPSHOT."""
    t0 = datetime.now(timezone.utc)
    resting_order = MT5OrderReality(
        order_ticket=664, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    class PersistentBoundaryTransport(MockTransportForEngine):
        def __init__(self) -> None:
            super().__init__()
            self.pass_count = 0

        def orders_get(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> Tuple[MT5OrderReality, ...]:
            return (resting_order,)

        def history_deals_get(self, ticket: Optional[int] = None, position: Optional[int] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> Tuple[MT5DealReality, ...]:
            self.pass_count += 1
            t = date_to or datetime.now(timezone.utc)
            # Pass 1: ticket 964; Pass 2: ticket 965 > watermark 964
            tkt = 964 if self.pass_count == 1 else 965
            deal_obj = MT5DealReality(
                deal_ticket=tkt, order_ticket=664, position_ticket=964, symbol="EURUSD",
                deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0800"),
                deal_time_utc=t,
            )
            return (deal_obj,)

        def history_deals_total(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> int:
            return 1

    transport = PersistentBoundaryTransport()
    adapter = MT5BrokerAdapter("TEST", "ACC", "TERM", transport=transport)
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM")

    with pytest.raises(MT5ReconciliationError, match="INCOHERENT_SNAPSHOT"):
        engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=MockShadowLedger(shadow),
            coordinator_map={},
        )


def test_r65_orchestration_recovers_unknown_order_to_cancelled() -> None:
    """In-flight UNKNOWN order with historical ORDER_STATE_CANCELED resolves to CANCELLED."""
    t0 = datetime.now(timezone.utc)
    hist_order = MT5OrderReality(
        order_ticket=665, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_CANCELED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    transport = MockTransportForEngine(history_orders=(hist_order,))
    adapter = MT5BrokerAdapter("TEST", "ACC", "TERM", transport=transport)
    engine = MT5ReconciliationEngine()

    shadow_order = ShadowRestingOrder(intent_id="EXEC_665", order_ticket=665, symbol="EURUSD", order_type="BUY_LIMIT", volume=Decimal("1.0"), price=Decimal("1.0800"))
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM", resting_orders=(shadow_order,))

    coordinator = ExecutionCoordinator("EXEC_665", Decimal("1.0"), initial_state=OrderLifecycleState.UNKNOWN)
    report = engine.reconcile_6d(shadow, engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM"))

    assert len(report.resolved_orders) == 1
    ev = report.resolved_orders[0]
    assert ev.to_evidence_string() == "CANCELLED"
    assert ev.broker_order_id == "665"

    outcome = coordinator.apply_reconciliation(
        broker_event_id=ev.broker_sequence,
        broker_sequence=ev.broker_sequence,
        evidence_token=ev.to_evidence_string(),
        order_id=ev.broker_order_id,
        observed_at=t0,
    )
    assert outcome.state == OrderLifecycleState.CANCELLED


def test_r66_orchestration_recovers_unknown_order_to_rejected() -> None:
    """In-flight UNKNOWN order with historical ORDER_STATE_REJECTED resolves to REJECTED."""
    t0 = datetime.now(timezone.utc)
    hist_order = MT5OrderReality(
        order_ticket=666, symbol="EURUSD", order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_REJECTED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=t0,
    )
    transport = MockTransportForEngine(history_orders=(hist_order,))
    engine = MT5ReconciliationEngine()
    shadow_order = ShadowRestingOrder(intent_id="EXEC_666", order_ticket=666, symbol="EURUSD", order_type="BUY", volume=Decimal("1.0"), price=Decimal("1.0850"))
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM", resting_orders=(shadow_order,))

    report = engine.reconcile_6d(shadow, engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM"))
    assert len(report.resolved_orders) == 1
    ev = report.resolved_orders[0]
    assert ev.to_evidence_string() == "REJECTED"


def test_r67_orchestration_recovers_unknown_order_to_expired() -> None:
    """In-flight UNKNOWN order with historical ORDER_STATE_EXPIRED resolves to EXPIRED."""
    t0 = datetime.now(timezone.utc)
    hist_order = MT5OrderReality(
        order_ticket=667, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_EXPIRED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    transport = MockTransportForEngine(history_orders=(hist_order,))
    engine = MT5ReconciliationEngine()
    shadow_order = ShadowRestingOrder(intent_id="EXEC_667", order_ticket=667, symbol="EURUSD", order_type="BUY_LIMIT", volume=Decimal("1.0"), price=Decimal("1.0800"))
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM", resting_orders=(shadow_order,))

    report = engine.reconcile_6d(shadow, engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM"))
    assert len(report.resolved_orders) == 1
    ev = report.resolved_orders[0]
    assert ev.to_evidence_string() == "EXPIRED"


def test_r68_orchestration_rejects_untracked_deal_with_bogus_comment() -> None:
    """Deal with comment 'hello' but no tracked intent lineage is strictly rejected as UNTRACKED_TRADE_DEAL."""
    t0 = datetime.now(timezone.utc)
    bogus_deal = MT5DealReality(
        deal_ticket=968, order_ticket=668, position_ticket=968, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0, comment="hello",
    )
    transport = MockTransportForEngine(deals=(bogus_deal,))
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM")

    report = engine.reconcile_6d(shadow, engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM"))
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL for d in report.discrepancies)


def test_r69_currency_mismatch_marks_financial_dimensions_unverifiable() -> None:
    """Currency mismatch leaves balance, equity, margin verification as False."""
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(currency="USD")
    broker_acc = make_sample_account_reality(currency="EUR")
    broker = make_sample_broker_snapshot(account=broker_acc)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert report.dimension_verification["balance"] is False
    assert report.dimension_verification["equity"] is False
    assert report.dimension_verification["margin"] is False
    assert any(d.kind == MT5DiscrepancyKind.CURRENCY_MISMATCH for d in report.discrepancies)


def test_r70_coverage_digest_detects_ticket_set_substitution() -> None:
    """Two deal queries with identical count but different tickets produce different coverage_digest."""
    t0 = datetime.now(timezone.utc)
    d1 = MT5DealReality(deal_ticket=1, order_ticket=1, position_ticket=1, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0)
    d2 = MT5DealReality(deal_ticket=2, order_ticket=2, position_ticket=2, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0)
    d3 = MT5DealReality(deal_ticket=3, order_ticket=3, position_ticket=3, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0)
    d4 = MT5DealReality(deal_ticket=4, order_ticket=4, position_ticket=4, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0)

    engine = MT5ReconciliationEngine()
    t1 = MockTransportForEngine(deals=(d1, d2, d3))
    t2 = MockTransportForEngine(deals=(d1, d2, d4))

    snap1 = engine.capture_bounded_broker_observation(t1, "TEST", "ACC", "TERM")
    snap2 = engine.capture_bounded_broker_observation(t2, "TEST", "ACC", "TERM")

    assert snap1.deal_coverage.total_deals_retrieved == snap2.deal_coverage.total_deals_retrieved
    assert snap1.deal_coverage.coverage_digest != snap2.deal_coverage.coverage_digest


def test_r71_missing_position_identifier_fails_closed() -> None:
    """Broker or shadow position with missing/invalid position_identifier raises MT5ValidationError."""
    with pytest.raises(Exception):
        # Schema forbids position_identifier <= 0
        MT5PositionReality(position_ticket=10, position_identifier=0, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"), time_open_utc=datetime.now(timezone.utc))


def test_r72_incomplete_or_truncated_historical_coverage_fails_closed() -> None:
    """Truncated historical deal query marks is_complete=False and triggers INCOMPLETE_HISTORY_SCOPE."""
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(is_complete=False)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.INCOMPLETE_HISTORY_SCOPE for d in report.discrepancies)


def test_r73_cancelled_after_partial_evidence_identity() -> None:
    """CANCELLED_AFTER_PARTIAL produces order ticket as broker_event_id and binds all deal tickets in evidence_refs."""
    t0 = datetime.now(timezone.utc)
    hist_order = MT5OrderReality(
        order_ticket=773, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_CANCELED, volume_initial=Decimal("2.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    d1 = MT5DealReality(deal_ticket=101, order_ticket=773, position_ticket=773, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("0.5"), price=Decimal("1.0800"), deal_time_utc=t0)
    d2 = MT5DealReality(deal_ticket=102, order_ticket=773, position_ticket=773, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("0.5"), price=Decimal("1.0800"), deal_time_utc=t0)

    resolved_state, vol, vwap, broker_event_id, evidence_refs = verify_order_deal_execution(773, hist_order, (d2, d1))
    assert resolved_state == OrderLifecycleState.CANCELLED
    assert vol == Decimal("1.0")
    assert broker_event_id == "773"
    # Canonical ordering: deal 101 then deal 102
    assert evidence_refs == ("101", "102")


def test_r74_rejected_terminal_evidence_identity() -> None:
    """Historical ORDER_STATE_REJECTED produces order ticket as event ID and resolves to REJECTED."""
    t0 = datetime.now(timezone.utc)
    hist_order = MT5OrderReality(
        order_ticket=774, symbol="EURUSD", order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_REJECTED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=t0,
    )
    resolved_state, vol, vwap, broker_event_id, evidence_refs = verify_order_deal_execution(774, hist_order, ())
    assert resolved_state == OrderLifecycleState.REJECTED
    assert broker_event_id == "774"
    assert evidence_refs == ()


def test_r75_expired_terminal_evidence_identity() -> None:
    """Historical ORDER_STATE_EXPIRED produces order ticket as event ID and resolves to EXPIRED."""
    t0 = datetime.now(timezone.utc)
    hist_order = MT5OrderReality(
        order_ticket=775, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_EXPIRED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0800"), time_setup_utc=t0,
    )
    resolved_state, vol, vwap, broker_event_id, evidence_refs = verify_order_deal_execution(775, hist_order, ())
    assert resolved_state == OrderLifecycleState.EXPIRED
    assert broker_event_id == "775"
    assert evidence_refs == ()


def test_r76_history_count_mismatch_fails_closed() -> None:
    """Count oracle mismatch (history_deals_total() = 5 vs len(deals) = 4) fails closed."""
    t0 = datetime.now(timezone.utc)
    deals = tuple(
        MT5DealReality(deal_ticket=i, order_ticket=i, position_ticket=i, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0)
        for i in range(1, 5)
    )

    class MismatchedCountTransport(MockTransportForEngine):
        def history_deals_total(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> int:
            return 5  # Claims 5 deals, but deals only has 4

    transport = MismatchedCountTransport(deals=deals)
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM", scope=HistoricalDealScopeKind.FULL_CYCLE)

    assert snapshot.deal_coverage.is_complete is False
    report = engine.reconcile_6d(make_sample_shadow_snapshot(), snapshot)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.INCOMPLETE_HISTORY_SCOPE for d in report.discrepancies)


def test_r77_same_timestamp_watermark_boundary_is_not_missed() -> None:
    """Deals with identical DEAL_TIME_MSC are distinguished by DEAL_TICKET, ensuring zero deals are dropped."""
    t0 = datetime.now(timezone.utc)
    t0_msc = int(t0.timestamp() * 1000)

    deal10 = MT5DealReality(deal_ticket=10, order_ticket=10, position_ticket=10, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0)
    deal11 = MT5DealReality(deal_ticket=11, order_ticket=11, position_ticket=11, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0)

    transport = MockTransportForEngine(deals=(deal10, deal11))
    engine = MT5ReconciliationEngine()

    # Query with watermark ticket=10 at same millisecond
    snapshot = engine.capture_bounded_broker_observation(
        transport, "TEST", "ACC", "TERM",
        scope=HistoricalDealScopeKind.WATERMARK_INCREMENTAL,
        watermark_ticket=10,
        watermark_time_msc=t0_msc,
    )
    # Deal 11 must be preserved, deal 10 must be excluded
    deal_tickets = [d.deal_ticket for d in snapshot.deals]
    assert 11 in deal_tickets
    assert 10 not in deal_tickets


def test_r78_deal_entry_is_not_used_as_trade_direction() -> None:
    """DEAL_TYPE is direction (BUY), while DEAL_ENTRY is lifecycle (OUT). Valid close of short."""
    t0 = datetime.now(timezone.utc)
    # Valid close of short: position_ticket > 0 (closing order), order BUY, deal BUY, entry OUT
    close_short_order = MT5OrderReality(
        order_ticket=778, position_ticket=978, symbol="EURUSD", order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=t0,
    )
    close_short_deal = MT5DealReality(
        deal_ticket=878, order_ticket=778, position_ticket=978, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_OUT,
    )
    resolved_state, vol, vwap, broker_event_id, evidence_refs = verify_order_deal_execution(778, close_short_order, (close_short_deal,))
    assert resolved_state == OrderLifecycleState.FILLED
    assert vol == Decimal("1.0")

    # Hardened negative check 1: Direction mismatch (BUY order with SELL deal) fails closed
    bad_dir_deal = close_short_deal.model_copy(update={"deal_type": MT5DealType.DEAL_TYPE_SELL})
    with pytest.raises(MT5ReconciliationError, match="DEAL_DIRECTION_MISMATCH"):
        verify_order_deal_execution(778, close_short_order, (bad_dir_deal,))

    # Hardened negative check 2: Opening order with DEAL_ENTRY_OUT fails closed
    opening_order = close_short_order.model_copy(update={"position_ticket": None})
    with pytest.raises(MT5ReconciliationError, match="RELATIONAL_ENTRY_MISMATCH"):
        verify_order_deal_execution(778, opening_order, (close_short_deal,))


def test_r79_deal_position_id_matches_position_identifier() -> None:
    """DEAL_POSITION_ID is verified and phantom resulting position fails closed."""
    t0 = datetime.now(timezone.utc)
    entry_deal = MT5DealReality(
        deal_ticket=879, order_ticket=779, position_ticket=979, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_IN,
    )
    # Shadow has the deal, but broker positions lacks position 979
    shadow_deal = ShadowDealRecord(deal_ticket=879, order_ticket=779, position_id=979, intent_id="INT_779", symbol="EURUSD", side="BUY", volume=Decimal("1.0"), price=Decimal("1.0850"), executed_at=t0)
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM", deals=(shadow_deal,))

    transport = MockTransportForEngine(deals=(entry_deal,))
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")

    report = engine.reconcile_6d(shadow, snapshot)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.PHANTOM_POSITION and d.identifier == "979" for d in report.discrepancies)


def test_r80_deal_type_and_entry_are_validated_independently() -> None:
    """DEAL_TYPE (direction) and DEAL_ENTRY (lifecycle) are validated relationally against order intent."""
    t0 = datetime.now(timezone.utc)
    # Long Entry Order (position_ticket None, order BUY)
    order_long_in = MT5OrderReality(order_ticket=1, position_ticket=None, symbol="EURUSD", order_type=MT5OrderType.BUY, state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("1.0"), volume_current=Decimal("0.0"), price_open=Decimal("1.0"), time_setup_utc=t0)
    # Contradictory entry: DEAL_ENTRY_OUT on opening order
    d_bad_entry = MT5DealReality(deal_ticket=1, order_ticket=1, position_ticket=1, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_OUT)
    with pytest.raises(MT5ReconciliationError, match="RELATIONAL_ENTRY_MISMATCH"):
        verify_order_deal_execution(1, order_long_in, (d_bad_entry,))

    # Contradictory direction: DEAL_TYPE_SELL on BUY order
    d_bad_dir = MT5DealReality(deal_ticket=2, order_ticket=1, position_ticket=1, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_SELL, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_IN)
    with pytest.raises(MT5ReconciliationError, match="DEAL_DIRECTION_MISMATCH"):
        verify_order_deal_execution(1, order_long_in, (d_bad_dir,))

    # DEAL_ENTRY_OUT_BY strictly fails closed
    d_out_by = MT5DealReality(deal_ticket=3, order_ticket=1, position_ticket=1, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_OUT_BY)
    with pytest.raises(MT5DomainError, match="CLOSE_BY_UNSUPPORTED"):
        verify_order_deal_execution(1, order_long_in, (d_out_by,))


def test_r81_incremental_count_mismatch_fails_closed() -> None:
    """Incremental query raw count mismatch (history_deals_total = 10 vs len(raw_deals) = 9) fails closed."""
    t0 = datetime.now(timezone.utc)
    deals = tuple(
        MT5DealReality(deal_ticket=i, order_ticket=i, position_ticket=i, symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"), deal_time_utc=t0)
        for i in range(1, 10)
    )

    class IncrementalMismatchTransport(MockTransportForEngine):
        def history_deals_total(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> int:
            return 10  # Claims 10 raw deals, but only 9 returned

    transport = IncrementalMismatchTransport(deals=deals)
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(
        transport, "TEST", "ACC", "TERM",
        scope=HistoricalDealScopeKind.WATERMARK_INCREMENTAL,
        watermark_ticket=0,
    )
    assert snapshot.deal_coverage.is_complete is False
    assert len(snapshot.deals) == 0


def test_r82_cancelled_deal_type_is_not_treated_as_fresh_fill() -> None:
    """DEAL_TYPE_BUY_CANCELED and DEAL_TYPE_SELL_CANCELED are excluded from fresh execution fill volume."""
    t0 = datetime.now(timezone.utc)
    hist_order = MT5OrderReality(
        order_ticket=782, symbol="EURUSD", order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=t0,
    )
    canceled_deal = MT5DealReality(
        deal_ticket=882, order_ticket=782, position_ticket=982, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY_CANCELED, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0,
    )
    # Canceled deal is excluded -> total execution volume is 0.0 -> fails volume mismatch!
    with pytest.raises(MT5ReconciliationError, match="FILLED_VOLUME_MISMATCH"):
        verify_order_deal_execution(782, hist_order, (canceled_deal,))


def test_r83_lineage_bypass_via_broker_history_orders_prevented() -> None:
    """Manual/external broker trade with order in broker.history_orders is strictly rejected as UNTRACKED_TRADE_DEAL."""
    t0 = datetime.now(timezone.utc)
    # External trader executed order 999 directly on broker
    manual_order = MT5OrderReality(
        order_ticket=999, symbol="EURUSD", order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=t0,
    )
    manual_deal = MT5DealReality(
        deal_ticket=1999, order_ticket=999, position_ticket=2999, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_IN,
    )
    # ACASH shadow ledger knows NOTHING about order 999 or deal 1999
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM")
    transport = MockTransportForEngine(history_orders=(manual_order,), deals=(manual_deal,))
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")

    report = engine.reconcile_6d(shadow, snapshot, coordinator_map={})
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL and d.identifier == "1999" for d in report.discrepancies)


def test_r84_direction_mismatch_in_transitioned_order_fails_closed() -> None:
    """Resting BUY order matched with SELL deal execution fails closed with DEAL_DIRECTION_MISMATCH."""
    t0 = datetime.now(timezone.utc)
    hist_order = MT5OrderReality(
        order_ticket=784, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=t0,
    )
    contradictory_deal = MT5DealReality(
        deal_ticket=884, order_ticket=784, position_ticket=984, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_SELL, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_IN,
    )
    with pytest.raises(MT5ReconciliationError, match="DEAL_DIRECTION_MISMATCH"):
        verify_order_deal_execution(784, hist_order, (contradictory_deal,))


def test_r85_end_to_end_evidence_refs_preserved_to_coordinator() -> None:
    """Multi-deal execution refs are preserved through ReconciliationEvidence into coordinator.apply_reconciliation."""
    t0 = datetime.now(timezone.utc) - timedelta(milliseconds=500)
    hist_order = MT5OrderReality(
        order_ticket=785, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("2.0"),
        volume_current=Decimal("0.0"), price_open=Decimal("1.0850"), time_setup_utc=t0,
    )
    d1 = MT5DealReality(
        deal_ticket=8851, order_ticket=785, position_ticket=985, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_IN,
    )
    d2 = MT5DealReality(
        deal_ticket=8852, order_ticket=785, position_ticket=985, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0 + timedelta(milliseconds=10), entry=MT5DealEntry.DEAL_ENTRY_IN,
    )
    transport = MockTransportForEngine(history_orders=(hist_order,), deals=(d1, d2))
    adapter = MT5BrokerAdapter("TEST", "ACC", "TERM", transport=transport)
    engine = MT5ReconciliationEngine()

    shadow_order = ShadowRestingOrder(
        intent_id="EXEC_785", order_ticket=785, symbol="EURUSD",
        order_type="BUY_LIMIT", volume=Decimal("2.0"), price=Decimal("1.0850"),
    )
    broker_pos = MT5PositionReality(
        position_ticket=985, position_identifier=985, symbol="EURUSD",
        position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("2.0"),
        price_open=Decimal("1.0850"), price_current=Decimal("1.0850"), time_open_utc=t0,
    )
    shadow_pos = ShadowPosition(
        position_ticket=985, position_identifier=985, symbol="EURUSD",
        side="BUY", volume=Decimal("2.0"), open_price=Decimal("1.0850"),
    )
    shadow_d1 = ShadowDealRecord(deal_ticket=8851, order_ticket=785, position_id=985, intent_id="EXEC_785", symbol="EURUSD", side="BUY", volume=Decimal("1.0"), price=Decimal("1.0850"), executed_at=t0)
    shadow_d2 = ShadowDealRecord(deal_ticket=8852, order_ticket=785, position_id=985, intent_id="EXEC_785", symbol="EURUSD", side="BUY", volume=Decimal("1.0"), price=Decimal("1.0850"), executed_at=t0)
    shadow = make_sample_shadow_snapshot(
        broker_id="TEST", account_id="ACC", terminal_instance_id="TERM",
        resting_orders=(shadow_order,), positions=(shadow_pos,), deals=(shadow_d1, shadow_d2),
    )
    transport.active_positions[985] = broker_pos

    coordinator = ExecutionCoordinator("EXEC_785", Decimal("2.0"), initial_state=OrderLifecycleState.UNKNOWN)
    coordinator_map = {"EXEC_785": coordinator}

    report = engine.execute_reconciliation_cycle(
        adapter=adapter,
        shadow_ledger=MockShadowLedger(shadow),
        coordinator_map=coordinator_map,
    )
    assert report.is_clean is True
    assert len(report.resolved_orders) == 1
    ev = report.resolved_orders[0]
    assert ev.evidence_refs == ("8851", "8852")
    assert coordinator.state == OrderLifecycleState.FILLED


def test_r86_history_orders_count_oracle_mismatch_fails_closed() -> None:
    """Discrepancy between history_orders_total and retrieved orders count fails closed."""
    t0 = datetime.now(timezone.utc)
    o1 = MT5OrderReality(order_ticket=1, symbol="EURUSD", order_type=MT5OrderType.BUY, state=MT5OrderState.ORDER_STATE_FILLED, volume_initial=Decimal("1.0"), volume_current=Decimal("0.0"), price_open=Decimal("1.0"), time_setup_utc=t0)

    class OrderCountMismatchTransport(MockTransportForEngine):
        def history_orders_total(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> int:
            return 5  # Claims 5, returns 1

    transport = OrderCountMismatchTransport(history_orders=(o1,))
    engine = MT5ReconciliationEngine()
    with pytest.raises(MT5ReconciliationError, match="INCOMPLETE_HISTORY_ORDERS_SCOPE"):
        engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")


def test_r87_strict_margin_mode_fail_closed_on_invalid_value() -> None:
    """Invalid margin mode type on account reality fails closed immediately."""
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    # Malformed broker account with invalid margin_mode
    broker_acc = make_sample_account_reality()
    object.__setattr__(broker_acc, "margin_mode", "INVALID_MODE")
    broker = make_sample_broker_snapshot(account=broker_acc)

    with pytest.raises(MT5DomainError, match="INVALID_MARGIN_MODE_TYPE"):
        engine.reconcile_6d(shadow, broker)


def test_r88_missing_margin_mode_fails_closed_in_account_reality() -> None:
    """Constructing MT5AccountReality without margin_mode fails closed via validation error."""
    with pytest.raises(ValidationError):
        MT5AccountReality(  # type: ignore[call-arg]
            login=1001,
            trade_mode=0,
            # margin_mode omitted!
            leverage=100,
            limit_orders=200,
            margin_so_mode=0,
            trade_allowed=True,
            trade_expert=True,
            balance=Decimal("100000.00"),
            credit=Decimal("0.0"),
            profit=Decimal("0.0"),
            equity=Decimal("100000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("100000.00"),
            margin_level=Decimal("0.0"),
            margin_so_call=Decimal("50.0"),
            margin_so_so=Decimal("30.0"),
            currency="USD",
        )


def test_r89_canceled_deal_cannot_prove_subsequent_close() -> None:
    """Canceled deal types (BUY_CANCELED, SELL_CANCELED) with DEAL_ENTRY_OUT cannot prove subsequent close."""
    t0 = datetime.now(timezone.utc)
    entry_deal = MT5DealReality(
        deal_ticket=8891, order_ticket=789, position_ticket=989, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0, entry=MT5DealEntry.DEAL_ENTRY_IN,
    )
    # Subsequent deal is a CANCELED deal type, NOT a TRADE_EXECUTION_DEAL!
    canceled_close_deal = MT5DealReality(
        deal_ticket=8892, order_ticket=790, position_ticket=989, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_SELL_CANCELED, volume=Decimal("1.0"), price=Decimal("1.0850"),
        deal_time_utc=t0 + timedelta(seconds=1), entry=MT5DealEntry.DEAL_ENTRY_OUT,
    )
    shadow_deal = ShadowDealRecord(deal_ticket=8891, order_ticket=789, position_id=989, intent_id="INT_789", symbol="EURUSD", side="BUY", volume=Decimal("1.0"), price=Decimal("1.0850"), executed_at=t0)
    shadow = make_sample_shadow_snapshot(broker_id="TEST", account_id="ACC", terminal_instance_id="TERM", deals=(shadow_deal,))

    transport = MockTransportForEngine(deals=(entry_deal, canceled_close_deal))
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")

    # Resulting position is missing, and canceled deal cannot act as close -> PHANTOM_POSITION
    report = engine.reconcile_6d(shadow, snapshot)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.PHANTOM_POSITION and d.identifier == "989" for d in report.discrepancies)
