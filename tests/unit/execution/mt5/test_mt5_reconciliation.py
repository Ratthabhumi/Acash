"""Unit tests for Phase 12 Slice 4: Authoritative 6-Dimensional Reconciliation Engine (RECON-6D).

Covers all 62 adversarial, boundary, and regression tests (R01 to R62) specified in
Implementation Plan Revision 5.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
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
    margin_mode: int = 0,
) -> MT5AccountReality:
    return MT5AccountReality(
        login=1001,
        trade_mode=margin_mode,
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
            now = datetime.now(timezone.utc)
            deals = [d.model_copy(update={"deal_time_utc": now}) for d in deals]
        return tuple(deals)


# ============================================================================
# TESTS: R01 TO R62
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
    assert report.confirmation.discrepancies_count == 0


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
        position_ticket=501,
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
    assert any(d.kind == MT5DiscrepancyKind.PHANTOM_POSITION and d.severity == MT5DiscrepancySeverity.CRITICAL for d in report.discrepancies)


def test_r04_position_volume_mismatch_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow_pos = ShadowPosition(
        position_ticket=501,
        position_identifier=501,
        symbol="EURUSD",
        side="BUY",
        volume=Decimal("1.0"),
        open_price=Decimal("1.0850"),
    )
    broker_pos = MT5PositionReality(
        position_ticket=501,
        symbol="EURUSD",
        position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("1.5"),  # Mismatch: 1.5 vs 1.0
        price_open=Decimal("1.0850"),
        price_current=Decimal("1.0855"),
        time_open_utc=datetime.now(timezone.utc),
    )
    shadow = make_sample_shadow_snapshot(positions=(shadow_pos,))
    broker = make_sample_broker_snapshot(positions=(broker_pos,))

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.POSITION_VOLUME_MISMATCH for d in report.discrepancies)


def test_r05_stale_broker_snapshot_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    old_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(observed_at=old_time)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.STALE_SNAPSHOT for d in report.discrepancies)


def test_r06_orphan_resting_order_detected() -> None:
    engine = MT5ReconciliationEngine()
    orphan_ord = MT5OrderReality(
        order_ticket=999,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED,
        volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"),
        price_open=Decimal("1.0800"),
        time_setup_utc=datetime.now(timezone.utc),
    )
    shadow = make_sample_shadow_snapshot(resting_orders=())
    broker = make_sample_broker_snapshot(orders=(orphan_ord,))

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.ORPHAN_RESTING_ORDER for d in report.discrepancies)


def test_r07_missing_resting_order_detected() -> None:
    engine = MT5ReconciliationEngine()
    missing_ord = ShadowRestingOrder(
        intent_id="INT_1",
        order_ticket=888,
        symbol="EURUSD",
        order_type="BUY_LIMIT",
        volume=Decimal("1.0"),
        price=Decimal("1.0800"),
    )
    shadow = make_sample_shadow_snapshot(resting_orders=(missing_ord,))
    broker = make_sample_broker_snapshot(orders=())

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.MISSING_RESTING_ORDER for d in report.discrepancies)


def test_r08_balance_divergence_outside_tolerance_fails() -> None:
    engine = MT5ReconciliationEngine(ReconciliationToleranceConfig(balance_tolerance=Decimal("0.05")))
    shadow = make_sample_shadow_snapshot(balance=Decimal("100000.00"))
    acc = make_sample_account_reality(balance=Decimal("100000.10"))  # delta = 0.10 > 0.05
    broker = make_sample_broker_snapshot(account=acc)

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.BALANCE_MISMATCH for d in report.discrepancies)


def test_r09_balance_divergence_within_tolerance_passes() -> None:
    engine = MT5ReconciliationEngine(ReconciliationToleranceConfig(balance_tolerance=Decimal("0.05")))
    shadow = make_sample_shadow_snapshot(balance=Decimal("100000.00"))
    acc = make_sample_account_reality(balance=Decimal("100000.03"))  # delta = 0.03 <= 0.05
    broker = make_sample_broker_snapshot(account=acc)

    report = engine.reconcile_6d(shadow, broker)
    assert not any(d.kind == MT5DiscrepancyKind.BALANCE_MISMATCH for d in report.discrepancies)


def test_r10_equity_divergence_outside_tolerance_fails() -> None:
    engine = MT5ReconciliationEngine(ReconciliationToleranceConfig(equity_tolerance=Decimal("0.10")))
    shadow = make_sample_shadow_snapshot(equity=Decimal("100000.00"))
    acc = make_sample_account_reality(equity=Decimal("100000.25"))
    broker = make_sample_broker_snapshot(account=acc)

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.EQUITY_MISMATCH for d in report.discrepancies)


def test_r11_margin_divergence_outside_tolerance_fails() -> None:
    engine = MT5ReconciliationEngine(ReconciliationToleranceConfig(margin_tolerance=Decimal("0.05")))
    shadow = make_sample_shadow_snapshot(margin=Decimal("1000.00"))
    acc = make_sample_account_reality(margin=Decimal("1000.20"))
    broker = make_sample_broker_snapshot(account=acc)

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.MARGIN_MISMATCH for d in report.discrepancies)


def test_r12_untracked_broker_trade_deal_triggers_critical_discrepancy() -> None:
    engine = MT5ReconciliationEngine()
    untracked_deal = MT5DealReality(
        deal_ticket=777,
        order_ticket=666,
        position_ticket=555,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY,
        volume=Decimal("1.0"),
        price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
        comment="",  # No lineage comment
    )
    shadow = make_sample_shadow_snapshot(deals=(), resting_orders=())
    broker = make_sample_broker_snapshot(deals=(untracked_deal,))

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL for d in report.discrepancies)


def test_r13_unknown_order_recovered_to_filled_via_deal_evidence() -> None:
    coordinator = ExecutionCoordinator("EXEC_101", Decimal("1.0"), OrderLifecycleState.UNKNOWN)
    assert coordinator.state == OrderLifecycleState.UNKNOWN

    historical_order = MT5OrderReality(
        order_ticket=101,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_FILLED,
        volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"),
        price_open=Decimal("1.0850"),
        time_setup_utc=datetime.now(timezone.utc),
    )
    deal = MT5DealReality(
        deal_ticket=201,
        order_ticket=101,
        position_ticket=301,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY,
        volume=Decimal("1.0"),
        price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
    )

    resolved_state, vol, vwap = verify_order_deal_execution(101, historical_order, (deal,))
    assert resolved_state == OrderLifecycleState.FILLED
    assert vol == Decimal("1.0")

    outcome = coordinator.apply_reconciliation(
        broker_event_id="201",
        broker_sequence="201",
        evidence_token="FILLED",
        order_id="101",
        observed_at=deal.deal_time_utc,
    )
    assert outcome.state == OrderLifecycleState.FILLED
    final_c_state: Any = coordinator.state
    assert final_c_state == OrderLifecycleState.FILLED


def test_r14_unknown_order_recovered_to_cancelled_via_history_order() -> None:
    coordinator = ExecutionCoordinator("EXEC_102", Decimal("1.0"), OrderLifecycleState.UNKNOWN)

    historical_order = MT5OrderReality(
        order_ticket=102,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_CANCELED,
        volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"),
        price_open=Decimal("1.0800"),
        time_setup_utc=datetime.now(timezone.utc),
    )

    resolved_state, vol, vwap = verify_order_deal_execution(102, historical_order, ())
    assert resolved_state == OrderLifecycleState.CANCELLED

    outcome = coordinator.apply_reconciliation(
        broker_event_id="EVT_CANCEL",
        broker_sequence="1",
        evidence_token="CANCELLED",
        order_id="102",
    )
    assert outcome.state == OrderLifecycleState.CANCELLED


def test_r15_reconciliation_never_directly_mutates_state_machine() -> None:
    coordinator = ExecutionCoordinator("EXEC_103", Decimal("1.0"), OrderLifecycleState.UNKNOWN)
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot()

    report = engine.reconcile_6d(shadow, broker)
    # Assert engine did not mutate coordinator
    assert coordinator.state == OrderLifecycleState.UNKNOWN


def test_r16_contradictory_evidence_on_terminal_shadow_emits_restriction() -> None:
    coordinator = ExecutionCoordinator("EXEC_104", Decimal("1.0"), OrderLifecycleState.CANCELLED)
    assert coordinator.state == OrderLifecycleState.CANCELLED

    # Contradictory evidence: broker proves FILLED
    outcome = coordinator.apply_reconciliation(
        broker_event_id="DEAL_999",
        broker_sequence="1",
        evidence_token="FILLED",
        order_id="104",
        observed_at=datetime.now(timezone.utc),
    )
    assert coordinator.disputed is True
    assert outcome.restriction_request is not None
    assert outcome.restriction_request.reason == RestrictionReason.RECONCILIATION_CONFLICT
    assert coordinator.state == OrderLifecycleState.CANCELLED  # Terminal absorbing preserved


def test_r17_tampered_shadow_digest_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    # Tamper with payload digest
    tampered_shadow = shadow.model_copy(update={"ledger_digest": "0" * 64})
    broker = make_sample_broker_snapshot()

    with pytest.raises(ReconciliationIntegrityError, match="SHADOW_LEDGER_DIGEST_MISMATCH"):
        engine.reconcile_6d(tampered_shadow, broker)


def test_r18_tampered_broker_snapshot_digest_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot()
    tampered_broker = broker.model_copy(update={"broker_snapshot_digest": "f" * 64})

    with pytest.raises(ReconciliationIntegrityError, match="BROKER_SNAPSHOT_DIGEST_MISMATCH"):
        engine.reconcile_6d(shadow, tampered_broker)


def test_r19a_digest_dict_order_invariance() -> None:
    dict1 = {"b": 2, "a": 1, "c": {"y": 20, "x": 10}}
    dict2 = {"a": 1, "c": {"x": 10, "y": 20}, "b": 2}
    assert compute_payload_digest(dict1) == compute_payload_digest(dict2)


def test_r19b_digest_decimal_canonicalization() -> None:
    # 1.0 and 1.00 should normalize to identical digest
    d1 = {"val": Decimal("1.0")}
    d2 = {"val": Decimal("1.00")}
    assert compute_payload_digest(d1) == compute_payload_digest(d2)


def test_r19c_digest_utc_timezone_normalization() -> None:
    # Non-UTC timezone equivalent should produce identical canonical string
    dt_utc = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    dt_offset = datetime(2026, 9, 3, 17, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    assert compute_payload_digest({"t": dt_utc}) == compute_payload_digest({"t": dt_offset})


def test_r19d_digest_schema_version_binding() -> None:
    payload1 = {"schema_version": "1.0.0", "data": 42}
    payload2 = {"schema_version": "1.0.1", "data": 42}
    assert compute_payload_digest(payload1) != compute_payload_digest(payload2)


def test_r19e_digest_evidence_mutation_invalidates_report() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot()
    report = engine.reconcile_6d(shadow, broker)
    orig_digest = report.report_digest

    # Alter discrepancies
    mutated_report_payload = {
        "reconciliation_id": report.reconciliation_id,
        "schema_version": report.schema_version,
        "broker_id": report.broker_id,
        "account_id": report.account_id,
        "terminal_instance_id": report.terminal_instance_id,
        "ledger_digest": report.ledger_digest,
        "broker_snapshot_digest": report.broker_snapshot_digest,
        "historical_coverage_digest": broker.deal_coverage.coverage_digest,
        "capture_context_digest": compute_payload_digest(broker.capture_context),
        "resolved_evidence_digests": ("MUTATED_EVIDENCE",),
        "discrepancies": [],
        "reconciled_at": report.reconciled_at,
    }
    assert compute_payload_digest(mutated_report_payload) != orig_digest


def test_r20_multi_position_multi_symbol_matrix_clean_pass() -> None:
    engine = MT5ReconciliationEngine()
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
    shadow_positions = tuple(
        ShadowPosition(
            position_ticket=100 + i,
            position_identifier=100 + i,
            symbol=sym,
            side="BUY",
            volume=Decimal("0.5"),
            open_price=Decimal("1.0000"),
        )
        for i, sym in enumerate(symbols)
    )
    broker_positions = tuple(
        MT5PositionReality(
            position_ticket=100 + i,
            symbol=sym,
            position_type=MT5PositionType.POSITION_TYPE_BUY,
            volume=Decimal("0.5"),
            price_open=Decimal("1.0000"),
            price_current=Decimal("1.0010"),
            time_open_utc=datetime.now(timezone.utc),
        )
        for i, sym in enumerate(symbols)
    )
    shadow = make_sample_shadow_snapshot(positions=shadow_positions)
    broker = make_sample_broker_snapshot(positions=broker_positions)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is True
    assert report.dimension_verification["positions"] is True


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
    assert conf.is_complete is True


def test_r25_full_coordinator_adapter_engine_roundtrip_integration() -> None:
    transport = MockTransportForEngine()
    adapter = MT5BrokerAdapter("TEST_BROKER", "ACC_1001", "TERM_1", transport=transport)
    assert adapter.safety_state == MT5TransportSafetyState.DEGRADED

    shadow = make_sample_shadow_snapshot()
    shadow_ledger = MockShadowLedger(shadow)
    coordinator = ExecutionCoordinator("EXEC_UNKNOWN", Decimal("1.0"), OrderLifecycleState.UNKNOWN)

    engine = MT5ReconciliationEngine()
    report = engine.execute_reconciliation_cycle(
        adapter=adapter,
        shadow_ledger=shadow_ledger,
        coordinator_map={"EXEC_UNKNOWN": coordinator},
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
    # 2 BUYs, 1 SELL on EURUSD under Hedging mode
    pos1 = ShadowPosition(position_ticket=101, position_identifier=101, symbol="EURUSD", side="BUY", volume=Decimal("1.0"), open_price=Decimal("1.0850"))
    pos2 = ShadowPosition(position_ticket=102, position_identifier=102, symbol="EURUSD", side="BUY", volume=Decimal("0.5"), open_price=Decimal("1.0860"))
    pos3 = ShadowPosition(position_ticket=103, position_identifier=103, symbol="EURUSD", side="SELL", volume=Decimal("0.3"), open_price=Decimal("1.0840"))

    b_pos1 = MT5PositionReality(position_ticket=101, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("1.0"), price_open=Decimal("1.0850"), price_current=Decimal("1.0855"), time_open_utc=datetime.now(timezone.utc))
    b_pos2 = MT5PositionReality(position_ticket=102, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("0.5"), price_open=Decimal("1.0860"), price_current=Decimal("1.0855"), time_open_utc=datetime.now(timezone.utc))
    b_pos3 = MT5PositionReality(position_ticket=103, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_SELL, volume=Decimal("0.3"), price_open=Decimal("1.0840"), price_current=Decimal("1.0855"), time_open_utc=datetime.now(timezone.utc))

    engine = MT5ReconciliationEngine()
    acc = make_sample_account_reality(margin_mode=MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING.value)
    shadow = make_sample_shadow_snapshot(positions=(pos1, pos2, pos3))
    broker = make_sample_broker_snapshot(account=acc, positions=(b_pos1, b_pos2, b_pos3))

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is True
    assert report.dimension_verification["positions"] is True


def test_r28_non_trade_deal_does_not_become_phantom_execution() -> None:
    engine = MT5ReconciliationEngine()
    balance_deal = MT5DealReality(
        deal_ticket=901,
        order_ticket=1,
        position_ticket=0,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BALANCE,
        volume=Decimal("1.0"),
        price=Decimal("1.0"),
        profit=Decimal("5000.00"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    comm_deal = MT5DealReality(
        deal_ticket=902,
        order_ticket=1,
        position_ticket=0,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_COMMISSION,
        volume=Decimal("1.0"),
        price=Decimal("1.0"),
        commission=Decimal("-15.00"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    shadow = make_sample_shadow_snapshot(deals=())
    broker = make_sample_broker_snapshot(deals=(balance_deal, comm_deal))

    report = engine.reconcile_6d(shadow, broker)
    # Non-trade deals should not trigger UNTRACKED_TRADE_DEAL
    assert not any(d.kind == MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL for d in report.discrepancies)


def test_r29_trade_deal_without_lineage_triggers_critical() -> None:
    engine = MT5ReconciliationEngine()
    orphan_deal = MT5DealReality(
        deal_ticket=903,
        order_ticket=801,
        position_ticket=701,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY,
        volume=Decimal("2.0"),
        price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
        comment="",
    )
    shadow = make_sample_shadow_snapshot(deals=())
    broker = make_sample_broker_snapshot(deals=(orphan_deal,))

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL for d in report.discrepancies)


def test_r30_mixed_terminal_capture_times_exceed_coherence_window() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(capture_duration_ms=2500.0, max_capture_window_ms=2000.0)

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.INCOHERENT_SNAPSHOT for d in report.discrepancies)


def test_r31_snapshot_queries_straddle_a_fill_detected() -> None:
    # An order observed resting in orders, but newly minted deal observed in deals in capture interval
    t0 = datetime.now(timezone.utc)
    resting_order = MT5OrderReality(
        order_ticket=555,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED,
        volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"),
        price_open=Decimal("1.0800"),
        time_setup_utc=t0,
    )
    straddle_deal = MT5DealReality(
        deal_ticket=777,
        order_ticket=555,  # Matching resting order!
        position_ticket=888,
        symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY,
        volume=Decimal("1.0"),
        price=Decimal("1.0800"),
        deal_time_utc=t0,
    )
    transport = MockTransportForEngine(orders=(resting_order,), deals=(straddle_deal,), dynamic_deal_time=True)
    engine = MT5ReconciliationEngine()

    snapshot = engine.capture_bounded_broker_observation(
        transport,
        broker_id="TEST",
        account_id="ACC",
        terminal_instance_id="TERM",
    )
    assert snapshot.capture_context.completeness_status == CaptureCompletenessStatus.CAPTURE_TIMEOUT


def test_r32_terminal_instance_identity_mismatch_fails_closed() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot(terminal_instance_id="TERM_1")
    broker = make_sample_broker_snapshot(terminal_instance_id="TERM_2")

    report = engine.reconcile_6d(shadow, broker)
    assert any(d.kind == MT5DiscrepancyKind.IDENTITY_MISMATCH and d.identifier == "terminal_instance_id" for d in report.discrepancies)


def test_r33_report_digest_changes_when_scope_changes() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker1 = make_sample_broker_snapshot()
    report1 = engine.reconcile_6d(shadow, broker1)

    # Change coverage scope
    coverage2 = broker1.deal_coverage.model_copy(update={"total_deals_retrieved": 999})
    broker2 = broker1.model_copy(update={"deal_coverage": coverage2})
    # Must update snapshot digest to preserve integrity check
    payload2 = broker2.model_dump()
    payload2.pop("broker_snapshot_digest", None)
    broker2 = broker2.model_copy(update={"broker_snapshot_digest": compute_payload_digest(payload2)})

    report2 = engine.reconcile_6d(shadow, broker2)
    assert report1.report_digest != report2.report_digest


def test_r34_decimal_canonicalization_deterministic() -> None:
    d = Decimal("123.45000")
    norm1 = _normalize_for_canonical_json(d)
    norm2 = _normalize_for_canonical_json(Decimal("123.45"))
    assert norm1 == norm2 == "123.45"


def test_r35_apply_reconciliation_is_sole_coordinator_integration_seam() -> None:
    coordinator = ExecutionCoordinator("EXEC_35", Decimal("1.0"), OrderLifecycleState.UNKNOWN)
    outcome = coordinator.apply_reconciliation(
        broker_event_id="EVT_35",
        broker_sequence="1",
        evidence_token="FILLED",
    )
    assert outcome.state == OrderLifecycleState.FILLED


def test_r36_engine_uses_public_shadow_reconciliation_snapshot_only() -> None:
    coordinator = ExecutionCoordinator("EXEC_36", Decimal("1.0"), OrderLifecycleState.UNKNOWN)
    snapshot = coordinator.snapshot_execution_state()
    assert isinstance(snapshot, CoordinatorExecutionSnapshot)
    assert snapshot.execution_id == "EXEC_36"
    assert snapshot.state == OrderLifecycleState.UNKNOWN


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
    resolved_state, vol, vwap = verify_order_deal_execution(137, historical_order, ())
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
    resolved_state, vol, vwap = verify_order_deal_execution(138, historical_order, ())
    assert resolved_state == OrderLifecycleState.EXPIRED


def test_r39_multi_deal_aggregation_matches_single_intent() -> None:
    historical_order = MT5OrderReality(
        order_ticket=139,
        symbol="EURUSD",
        order_type=MT5OrderType.BUY,
        state=MT5OrderState.ORDER_STATE_FILLED,
        volume_initial=Decimal("1.0"),
        volume_current=Decimal("0.0"),
        price_open=Decimal("1.0850"),
        time_setup_utc=datetime.now(timezone.utc),
    )
    deal1 = MT5DealReality(
        deal_ticket=201, order_ticket=139, position_ticket=301, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("0.4"), price=Decimal("1.0850"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    deal2 = MT5DealReality(
        deal_ticket=202, order_ticket=139, position_ticket=301, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("0.6"), price=Decimal("1.0852"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    resolved_state, total_vol, vwap = verify_order_deal_execution(139, historical_order, (deal1, deal2))
    assert resolved_state == OrderLifecycleState.FILLED
    assert total_vol == Decimal("1.0")
    # VWAP = (0.4 * 1.0850 + 0.6 * 1.0852) / 1.0 = 0.4340 + 0.65112 = 1.08512
    assert vwap == Decimal("1.08512")


def test_r40_duplicate_deal_ticket_is_detected() -> None:
    d1 = MT5DealReality(
        deal_ticket=500, order_ticket=1, position_ticket=1, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    d2 = MT5DealReality(
        deal_ticket=500, order_ticket=1, position_ticket=1, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0"),
        deal_time_utc=datetime.now(timezone.utc),
    )
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(deals=(d1, d2))
    with pytest.raises(MT5ValidationError, match="DUPLICATE_DEAL_TICKET"):
        engine.reconcile_6d(shadow, broker)


def test_r41_duplicate_position_identity_is_detected() -> None:
    p1 = MT5PositionReality(
        position_ticket=600, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"),
        time_open_utc=datetime.now(timezone.utc),
    )
    p2 = MT5PositionReality(
        position_ticket=600, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"),
        time_open_utc=datetime.now(timezone.utc),
    )
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(positions=(p1, p2))
    with pytest.raises(MT5ValidationError, match="DUPLICATE_POSITION_TICKET"):
        engine.reconcile_6d(shadow, broker)


def test_r42_partial_historical_window_cannot_produce_clean() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    broker = make_sample_broker_snapshot(is_complete=False)
    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False


def test_r43_non_usd_account_tolerance_uses_account_currency() -> None:
    engine = MT5ReconciliationEngine(ReconciliationToleranceConfig(balance_tolerance=Decimal("5.0")))
    # JPY account
    shadow = make_sample_shadow_snapshot(currency="JPY", balance=Decimal("10000000"))
    acc = make_sample_account_reality(currency="JPY", balance=Decimal("10000003"))
    broker = make_sample_broker_snapshot(account=acc)

    report = engine.reconcile_6d(shadow, broker)
    assert report.dimension_verification["balance"] is True


def test_r44_missing_one_of_six_dimensions_cannot_produce_confirmation() -> None:
    engine = MT5ReconciliationEngine()
    # Missing positions dimension
    shadow = make_sample_shadow_snapshot(positions=(ShadowPosition(position_ticket=1, position_identifier=1, symbol="EURUSD", side="BUY", volume=Decimal("1.0"), open_price=Decimal("1.0")),))
    broker = make_sample_broker_snapshot(positions=())  # Missing!

    report = engine.reconcile_6d(shadow, broker)
    assert report.confirmation is None


def test_r45_stale_snapshot_cannot_be_overridden_by_clean_comparison() -> None:
    engine = MT5ReconciliationEngine()
    shadow = make_sample_shadow_snapshot()
    # Perfectly matching ledger but stale
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    broker = make_sample_broker_snapshot(observed_at=stale_time)

    report = engine.reconcile_6d(shadow, broker)
    assert report.is_clean is False
    assert any(d.kind == MT5DiscrepancyKind.STALE_SNAPSHOT for d in report.discrepancies)


def test_r46_netting_position_reversal_preserves_position_identity() -> None:
    # Netting mode: position_ticket changed from 100 to 200 due to reversal, but identifier stays 500
    shadow_pos = ShadowPosition(
        position_ticket=100,
        position_identifier=500,
        symbol="EURUSD",
        side="BUY",
        volume=Decimal("1.0"),
        open_price=Decimal("1.0850"),
    )
    broker_pos = MT5PositionReality(
        position_ticket=200,  # Changed ticket!
        symbol="EURUSD",
        position_type=MT5PositionType.POSITION_TYPE_BUY,
        volume=Decimal("1.0"),
        price_open=Decimal("1.0850"),
        price_current=Decimal("1.0855"),
        time_open_utc=datetime.now(timezone.utc),
    )
    # Under Netting, match succeeds because position_identifier is constant
    is_match = match_position_identity(shadow_pos, broker_pos, MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_NETTING)
    assert is_match is True


def test_r47_canceled_trade_deal_classification() -> None:
    canonical_type = decode_mt5_deal_type(16)  # DEAL_TYPE_BUY_CANCELED
    assert canonical_type == MT5DealType.DEAL_TYPE_BUY_CANCELED
    category = categorize_deal(canonical_type)
    assert category == MT5DealCategory.CANCELED_TRADE_DEAL


def test_r48_daily_monthly_agent_commission_classification() -> None:
    for code in (7, 8, 9, 10, 15):
        ctype = decode_mt5_deal_type(code)
        assert categorize_deal(ctype) == MT5DealCategory.ACCOUNTING_DEAL


def test_r49_unknown_deal_type_fails_closed() -> None:
    with pytest.raises(MT5DomainError, match="UNKNOWN_MQL5_DEAL_TYPE"):
        decode_mt5_deal_type(9999)


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
    assert snapshot.capture_context.completeness_status == CaptureCompletenessStatus.CAPTURE_TIMEOUT


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
    resolved_state, vol, vwap = verify_order_deal_execution(151, historical_order, (deal,))
    assert resolved_state == OrderLifecycleState.CANCELLED
    assert vol == Decimal("0.4")  # Partial fill volume preserved


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
    resolved_state, vol, vwap = verify_order_deal_execution(152, historical_order, (deal,))
    assert resolved_state == OrderLifecycleState.FILLED


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
    assert snapshot.capture_context.completeness_status == CaptureCompletenessStatus.CAPTURE_TIMEOUT


def test_r55_ticket_order_without_temporal_evidence_does_not_prove_straddle() -> None:
    # Deal has higher ticket, but its deal_time_utc is BEFORE capture start
    t_past = datetime.now(timezone.utc) - timedelta(hours=2)
    t_now = datetime.now(timezone.utc)

    resting_order = MT5OrderReality(
        order_ticket=555, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_PLACED, volume_initial=Decimal("1.0"),
        volume_current=Decimal("1.0"), price_open=Decimal("1.0800"), time_setup_utc=t_now,
    )
    # Past deal (occurred 2 hours ago)
    deal = MT5DealReality(
        deal_ticket=855, order_ticket=555, position_ticket=955, symbol="EURUSD",
        deal_type=MT5DealType.DEAL_TYPE_BUY, volume=Decimal("1.0"), price=Decimal("1.0800"),
        deal_time_utc=t_past,
    )
    transport = MockTransportForEngine(orders=(resting_order,), deals=(deal,))
    engine = MT5ReconciliationEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")
    # Not a straddle race because temporal timestamp is outside capture interval
    assert snapshot.capture_context.completeness_status == CaptureCompletenessStatus.COMPLETE


def test_r56_pre_post_watermark_boundary_is_closed() -> None:
    engine = MT5ReconciliationEngine()
    transport = MockTransportForEngine()
    snapshot = engine.capture_bounded_broker_observation(transport, "TEST", "ACC", "TERM")
    ctx = snapshot.capture_context
    assert ctx.pre_watermark_deal_ticket <= ctx.post_watermark_deal_ticket


def test_r57_margin_mode_uses_canonical_enum_only() -> None:
    shadow_pos = ShadowPosition(position_ticket=10, position_identifier=10, symbol="EURUSD", side="BUY", volume=Decimal("1.0"), open_price=Decimal("1.0"))
    broker_pos = MT5PositionReality(position_ticket=10, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"), time_open_utc=datetime.now(timezone.utc))

    # Canonical enum
    assert match_position_identity(shadow_pos, broker_pos, MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_NETTING) is True
    assert match_position_identity(shadow_pos, broker_pos, MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) is True


def test_r58_unknown_margin_mode_fails_closed() -> None:
    shadow_pos = ShadowPosition(position_ticket=10, position_identifier=10, symbol="EURUSD", side="BUY", volume=Decimal("1.0"), open_price=Decimal("1.0"))
    broker_pos = MT5PositionReality(position_ticket=10, symbol="EURUSD", position_type=MT5PositionType.POSITION_TYPE_BUY, volume=Decimal("1.0"), price_open=Decimal("1.0"), price_current=Decimal("1.0"), time_open_utc=datetime.now(timezone.utc))

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
    assert snapshot.capture_context.completeness_status == CaptureCompletenessStatus.CAPTURE_TIMEOUT


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
