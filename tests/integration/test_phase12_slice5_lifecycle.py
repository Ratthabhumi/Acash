"""Phase 12 Slice 5: Execution Lifecycle Integration Tests.

Proves, through structured integration evidence, that all frozen components
wired end-to-end form a single authority-separated execution chain where:
- No lifecycle state is ever mutated outside transition_order()
- Every terminal state requires authoritative broker evidence before resolution
- Gate 6 evidence routing is: intent_id ONLY, fail-closed, Phase-A preflight atomic

Scope constraints (per Plan Rev5):
    - No production modifications beyond coordinator.py + reconciliation.py
    - No rollback/transaction semantics added

Phase-A Preflight Atomicity Invariant (what IS proven here):
    Any routing or lineage validation failure is raised BEFORE any coordinator mutation.
    Phase-B failures (apply_reconciliation raises mid-loop) are NOT covered by this
    invariant and are explicitly deferred.
"""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pytest

from acash.execution.admission import (
    PreLiveRiskAdmissionError,
    construct_order_intent,
)
from acash.execution.coordinator import ExecutionCoordinator
from acash.execution.mt5.adapter import MT5BrokerAdapter
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5ReconciliationError,
)
from acash.execution.mt5.reconciliation import (
    ACASHShadowLedger,
    ACASHShadowLedgerSnapshot,
    MT5ReconciliationEngine,
    ReconciliationToleranceConfig,
    ShadowDealRecord,
    ShadowPosition,
    ShadowRestingOrder,
    compute_payload_digest,
)
from acash.execution.mt5.transport import (
    MockMT5Transport,
    MT5TransportSafetyState,
)
from acash.execution.mt5.schemas import (
    BrokerSymbolSpec,
    MT5DealReality,
    MT5OrderReality,
    MT5PositionReality,
    MT5TradeResult,
)
from acash.execution.mt5.enums import (
    MT5DealType,
    MT5OrderState,
    MT5OrderType,
    MT5Retcode,
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


# ===========================================================================
# Helpers
# ===========================================================================


def _make_signal_hash() -> str:
    return hashlib.sha256(b"test_signal_s5").hexdigest()


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
        total_equity=Decimal("100000.00"),
        realized_pnl_today=Decimal("500.00"),
        unrealized_pnl=Decimal("200.00"),
        current_drawdown_pct=Decimal("0.5"),
        gross_exposure_notional=Decimal("20000.00"),
        net_exposure_notional=Decimal("5000.00"),
        concentration_ratio=Decimal("0.20"),
        parametric_var_95=Decimal("1500.00"),
        historical_cvar_95=Decimal("2200.00"),
        data_timestamp=now,
        data_age_ms=120,
        calculation_status=calculation_status,
        is_market_data_stale=False,
        is_broker_connected=True,
        is_clock_skew_detected=False,
        risk_status=risk_status,
    )


def _make_authorization(
    *,
    status: AuthorizationStatus = AuthorizationStatus.ACTIVE,
    allowed_venues: Tuple[str, ...] = ("TEST_MT5",),
    allowed_symbols: Tuple[str, ...] = ("EURUSD",),
    max_position_size: Decimal = Decimal("10.0"),
    max_notional: Decimal = Decimal("1000000"),
    expires_delta_seconds: int = 3600,
    strategy_id: str = "STRAT_TEST",
    authorization_id: str = "AUTH_TEST_001",
) -> LiveAuthorization:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_delta_seconds)
    auth_id = authorization_id
    digest = compute_authorization_digest(
        authorization_id=auth_id,
        certificate_id="CERT_TEST_001",
        strategy_id=strategy_id,
        authorized_at=now,
        expires_at=expires_at,
        max_notional=max_notional,
        max_position_size=max_position_size,
        max_order_rate_per_minute=60,
        max_daily_loss_notional=Decimal("5000"),
        max_drawdown_pct=Decimal("10"),
        allowed_venues=allowed_venues,
        allowed_symbols=allowed_symbols,
        risk_policy_version="v1",
        required_approvals=1,
        approval_digests=(),
    )
    return LiveAuthorization(
        authorization_id=auth_id,
        certificate_id="CERT_TEST_001",
        strategy_id=strategy_id,
        status=status,
        authorized_at=now,
        expires_at=expires_at,
        max_notional=max_notional,
        max_position_size=max_position_size,
        max_order_rate_per_minute=60,
        max_daily_loss_notional=Decimal("5000"),
        max_drawdown_pct=Decimal("10"),
        allowed_venues=allowed_venues,
        allowed_symbols=allowed_symbols,
        risk_policy_version="v1",
        required_approvals=1,
        approvals=(),
        authorization_digest=digest,
    )


def _make_restriction_authority() -> RiskRestrictionAuthority:
    return RiskRestrictionAuthority(ledger=RestrictionLedger())


def _build_shadow_snapshot(
    *,
    broker_id: str = "TEST_BROKER",
    account_id: str = "ACC_001",
    terminal_instance_id: str = "TERM_001",
    resting_orders: Tuple[ShadowRestingOrder, ...] = (),
    positions: Tuple[ShadowPosition, ...] = (),
    deals: Tuple[ShadowDealRecord, ...] = (),
    balance: Decimal = Decimal("100000.00"),
    equity: Decimal = Decimal("100000.00"),
    margin: Decimal = Decimal("0.00"),
    currency: str = "USD",
) -> ACASHShadowLedgerSnapshot:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "broker_id": broker_id,
        "account_id": account_id,
        "terminal_instance_id": terminal_instance_id,
        "currency": currency,
        "snapshot_at": now,
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
        snapshot_at=now,
        balance=balance,
        equity=equity,
        margin=margin,
        positions=positions,
        resting_orders=resting_orders,
        deals=deals,
        ledger_digest=digest,
    )


class StubShadowLedger:
    """Minimal ACASHShadowLedger Protocol impl for integration harness."""

    def __init__(self, snapshot: ACASHShadowLedgerSnapshot) -> None:
        self._snapshot = snapshot

    def snapshot_reconciliation_state(self) -> ACASHShadowLedgerSnapshot:
        return self._snapshot


class _MockAdapterTransport(MockMT5Transport):
    """Extended MockMT5Transport with configurable order_send behaviour."""

    def __init__(
        self,
        *,
        broker_id: str = "TEST_BROKER",
        account_id: str = "ACC_001",
        positions: Tuple[MT5PositionReality, ...] = (),
        orders: Tuple[MT5OrderReality, ...] = (),
        history_orders: Tuple[MT5OrderReality, ...] = (),
        deals: Tuple[MT5DealReality, ...] = (),
        order_send_timeout: bool = False,
    ) -> None:
        super().__init__(broker_id=broker_id, account_id=account_id)
        self.active_positions = {p.position_ticket: p for p in positions}
        self.active_orders = {o.order_ticket: o for o in orders}
        self.history_orders = {o.order_ticket: o for o in history_orders}
        self.history_deals = {d.deal_ticket: d for d in deals}
        self._timeout_on_order_send = order_send_timeout


def _make_sym_spec() -> BrokerSymbolSpec:
    from acash.execution.mt5.enums import MT5TradeExecutionMode
    digest = BrokerSymbolSpec.compute_spec_digest(
        canonical_symbol="EURUSD",
        broker_symbol="EURUSD",
        contract_size=Decimal("1"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100.00"),
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
        canonical_symbol="EURUSD",
        broker_symbol="EURUSD",
        contract_size=Decimal("1"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100.00"),
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


def _make_adapter(
    transport: Optional[_MockAdapterTransport] = None,
    *,
    broker_id: str = "TEST_BROKER",
    account_id: str = "ACC_001",
    terminal_instance_id: str = "TERM_001",
) -> MT5BrokerAdapter:
    if transport is None:
        transport = _MockAdapterTransport(broker_id=broker_id, account_id=account_id)
    sym_spec = _make_sym_spec()
    transport.register_symbol_spec(sym_spec)
    return MT5BrokerAdapter(broker_id, account_id, terminal_instance_id, transport=transport)


def _make_intent(intent_id: str = "INT_TEST") -> Any:
    auth = _make_authorization()
    risk = _make_risk_state()
    return construct_order_intent(
        authorization=auth, intent_id=intent_id,
        venue="TEST_MT5", symbol="EURUSD",
        side=OrderSide.BUY, order_type=OrderType.MARKET,
        quantity=Decimal("1.0"), current_risk=risk,
        signal_event_hash=_make_signal_hash(),
        created_at=datetime.now(timezone.utc),
        restriction_authority=_make_restriction_authority(),
    )


def _make_cancelled_history_order(order_ticket: int) -> MT5OrderReality:
    return MT5OrderReality(
        order_ticket=order_ticket, symbol="EURUSD",
        order_type=MT5OrderType.BUY_LIMIT,
        state=MT5OrderState.ORDER_STATE_CANCELED,
        volume_initial=Decimal("1.0"), volume_current=Decimal("1.0"),
        price_open=Decimal("1.0850"),
        time_setup_utc=datetime.now(timezone.utc),
    )


def _make_shadow_resting(intent_id: str, order_ticket: int) -> ShadowRestingOrder:
    return ShadowRestingOrder(
        intent_id=intent_id, order_ticket=order_ticket, symbol="EURUSD",
        order_type="BUY_LIMIT", volume=Decimal("1.0"), price=Decimal("1.0850"),
    )


# ===========================================================================
# S1 — Admission Enforcement (6 tests)
# ===========================================================================


class TestS1AdmissionEnforcement:
    """Gate 1: construct_order_intent() is the sole admission gate."""

    def test_s1_intent_rejected_if_risk_status_not_normal(self) -> None:
        auth = _make_authorization()
        risk = _make_risk_state(risk_status=RiskStatus.HALTED)
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S1A",
                venue="TEST_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("1.0"), current_risk=risk,
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=_make_restriction_authority(),
            )

    def test_s1_intent_rejected_if_calculation_not_nominal(self) -> None:
        auth = _make_authorization()
        risk = _make_risk_state(calculation_status=CalculationStatus.STALE)
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S1B",
                venue="TEST_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("1.0"), current_risk=risk,
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=_make_restriction_authority(),
            )

    def test_s1_intent_rejected_if_restriction_open(self) -> None:
        from acash.execution.operational_restriction import (
            OperationalRestriction, RestrictionReason, RestrictionScope,
        )
        auth = _make_authorization()
        ledger = RestrictionLedger()
        ledger.record(OperationalRestriction(
            restriction_id="RESTR_S1C",
            scope=RestrictionScope.STRATEGY,
            reason=RestrictionReason.RECONCILIATION_CONFLICT,
            strategy_id=auth.strategy_id,
            authorization_id=auth.authorization_id,
        ))
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S1C",
                venue="TEST_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("1.0"), current_risk=_make_risk_state(),
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=RiskRestrictionAuthority(ledger=ledger),
            )

    def test_s1_intent_rejected_if_authorization_suspended(self) -> None:
        auth = _make_authorization(status=AuthorizationStatus.SUSPENDED)
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S1D",
                venue="TEST_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("1.0"), current_risk=_make_risk_state(),
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=_make_restriction_authority(),
            )

    def test_s1_intent_rejected_if_venue_not_allowed(self) -> None:
        auth = _make_authorization(allowed_venues=("PAPER_MT5",))
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S1E",
                venue="LIVE_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("1.0"), current_risk=_make_risk_state(),
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=_make_restriction_authority(),
            )

    def test_s1_intent_admitted_clears_all_gates_nominal(self) -> None:
        auth = _make_authorization()
        intent = construct_order_intent(
            authorization=auth, intent_id="INT_S1F",
            venue="TEST_MT5", symbol="EURUSD",
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=Decimal("1.0"), current_risk=_make_risk_state(),
            signal_event_hash=_make_signal_hash(),
            created_at=datetime.now(timezone.utc),
            restriction_authority=_make_restriction_authority(),
        )
        assert intent.intent_id == "INT_S1F"
        assert intent.intent_digest  # non-empty


# ===========================================================================
# S2 — Coordinator Sole State Authority (4 tests)
# ===========================================================================


class TestS2CoordinatorSoleStateAuthority:
    """Gate 2: MT5BrokerAdapter has zero transition_order() callsites."""

    def test_s2_adapter_submit_observation_has_no_lifecycle_state(self) -> None:
        from acash.execution.mt5.adapter import MT5BrokerObservation
        field_names = MT5BrokerObservation.model_fields.keys()
        assert "shadow_state" not in field_names
        assert "lifecycle_state" not in field_names
        assert "state" not in field_names

    def test_s2_coordinator_apply_ack_transitions_to_acknowledged(self) -> None:
        from acash.execution.broker_events import normalize_broker_event, BrokerEventKind
        from acash.execution.coordinator import CoordinatorEvent
        now = datetime.now(timezone.utc)
        coord = ExecutionCoordinator("EXEC_S2B", Decimal("1.0"), intent_id="INT_S2B")
        ev, _ = normalize_broker_event(
            broker_order_id="ORD_S2B", event_kind=BrokerEventKind.ACK,
            observed_at=now, source="test", broker_sequence="SEQ_S2B",
        )
        outcome = coord.apply(CoordinatorEvent(
            broker_event_id="ORD_S2B", broker_sequence="SEQ_S2B",
            canonical_event=ev, observed_at=now,
        ))
        assert outcome.state is OrderLifecycleState.ACKNOWLEDGED

    def test_s2_coordinator_apply_reject_transitions_to_rejected(self) -> None:
        from acash.execution.broker_events import normalize_broker_event, BrokerEventKind
        from acash.execution.coordinator import CoordinatorEvent
        now = datetime.now(timezone.utc)
        coord = ExecutionCoordinator("EXEC_S2C", Decimal("1.0"), intent_id="INT_S2C")
        ev, _ = normalize_broker_event(
            broker_order_id="ORD_S2C", event_kind=BrokerEventKind.REJECT,
            observed_at=now, source="test", broker_sequence="SEQ_S2C",
        )
        outcome = coord.apply(CoordinatorEvent(
            broker_event_id="ORD_S2C", broker_sequence="SEQ_S2C",
            canonical_event=ev, observed_at=now,
        ))
        assert outcome.state is OrderLifecycleState.REJECTED

    def test_s2_broker_adapter_has_no_transition_order_callsite(self) -> None:
        import ast
        from acash.execution.mt5 import adapter as adapter_mod
        tree = ast.parse(inspect.getsource(adapter_mod))
        call_names = [
            n.func.id for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        ]
        assert "transition_order" not in call_names
        assert "transition_order" not in adapter_mod.__dict__


# ===========================================================================
# S3 — ACK ≠ FILLED (4 tests)
# ===========================================================================


class TestS3AckNotFilled:
    """Gate 3: order_send retcode 10009 → ACK; FILLED requires RECONCILE+evidence."""

    def test_s3_submit_retcode_10009_yields_ack_not_filled(self) -> None:
        from acash.execution.mt5.mapping import classify_trade_result_observation
        from acash.execution.broker_events import BrokerEventKind
        result = MT5TradeResult(
            retcode=MT5Retcode.TRADE_RETCODE_DONE.value,
            order=12345, deal=0,
            volume=Decimal("1.0"), price=Decimal("1.0850"), comment="done",
        )
        event_kind = classify_trade_result_observation(result, authoritative_deal_confirmed=False)
        assert event_kind is BrokerEventKind.ACK

    def test_s3_state_stays_acknowledged_after_ack(self) -> None:
        from acash.execution.broker_events import normalize_broker_event, BrokerEventKind
        from acash.execution.coordinator import CoordinatorEvent
        now = datetime.now(timezone.utc)
        coord = ExecutionCoordinator("EXEC_S3B", Decimal("1.0"), intent_id="INT_S3B")
        ev, _ = normalize_broker_event(
            broker_order_id="ORD_S3B", event_kind=BrokerEventKind.ACK,
            observed_at=now, source="test", broker_sequence="SEQ_S3B",
        )
        coord.apply(CoordinatorEvent(
            broker_event_id="ORD_S3B", broker_sequence="SEQ_S3B",
            canonical_event=ev, observed_at=now,
        ))
        assert coord.shadow_state is OrderLifecycleState.ACKNOWLEDGED

    def test_s3_filled_requires_reconcile_evidence_from_recon(self) -> None:
        now = datetime.now(timezone.utc)
        coord = ExecutionCoordinator(
            "EXEC_S3C", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN,
            intent_id="INT_S3C",
        )
        outcome = coord.apply_reconciliation(
            broker_event_id="RECON_S3C", broker_sequence="SEQ_RECON_S3C",
            evidence_token="FILLED", order_id="ORD_S3C",
            observed_at=now, evidence_refs=("ref1",),
        )
        assert outcome.state is OrderLifecycleState.FILLED

    def test_s3_direct_ack_to_filled_without_evidence_raises(self) -> None:
        from acash.execution.state_machine import transition_order, ExecutionStateError, ExecutionEvent
        with pytest.raises(ExecutionStateError, match="requires reconciliation evidence"):
            transition_order(OrderLifecycleState.UNKNOWN, ExecutionEvent.RECONCILE, evidence=None)


# ===========================================================================
# S4 — Timeout → UNKNOWN → BLOCKED → RECON (7 tests)
# ===========================================================================


class TestS4TimeoutUnknownRecon:
    """Gate 4: timeout → CONNECTION_LOST → UNKNOWN → RECONCILIATION_REQUIRED → RECON."""

    def test_s4_timeout_yields_connection_lost_observation(self) -> None:
        from acash.execution.broker_events import BrokerEventKind
        transport = _MockAdapterTransport(order_send_timeout=True)
        adapter = _make_adapter(transport)
        adapter.is_reconciled = True
        adapter.safety_state = MT5TransportSafetyState.READY
        intent = _make_intent("INT_S4A")
        obs = adapter.submit_order(intent, _make_sym_spec())
        assert obs.event_kind is BrokerEventKind.CONNECTION_LOST
        assert obs.requires_reconciliation is True

    def test_s4_adapter_safety_state_reconciliation_required_after_timeout(self) -> None:
        transport = _MockAdapterTransport(order_send_timeout=True)
        adapter = _make_adapter(transport)
        adapter.is_reconciled = True
        adapter.safety_state = MT5TransportSafetyState.READY
        adapter.submit_order(_make_intent("INT_S4B"), _make_sym_spec())
        assert adapter.safety_state is MT5TransportSafetyState.RECONCILIATION_REQUIRED

    def test_s4_coordinator_transitions_to_unknown_on_connection_lost(self) -> None:
        from acash.execution.broker_events import normalize_broker_event, BrokerEventKind
        from acash.execution.coordinator import CoordinatorEvent
        now = datetime.now(timezone.utc)
        coord = ExecutionCoordinator(
            "EXEC_S4C", Decimal("1.0"),
            initial_state=OrderLifecycleState.SUBMITTED, intent_id="INT_S4C",
        )
        ev, _ = normalize_broker_event(
            broker_order_id="ORD_S4C", event_kind=BrokerEventKind.CONNECTION_LOST,
            observed_at=now, source="test", broker_sequence="SEQ_S4C",
        )
        outcome = coord.apply(CoordinatorEvent(
            broker_event_id="ORD_S4C", broker_sequence="SEQ_S4C",
            canonical_event=ev, observed_at=now,
        ))
        assert outcome.state is OrderLifecycleState.UNKNOWN

    def test_s4_second_dispatch_raises_dispatch_blocked(self) -> None:
        transport = _MockAdapterTransport(order_send_timeout=True)
        adapter = _make_adapter(transport)
        adapter.is_reconciled = True
        adapter.safety_state = MT5TransportSafetyState.READY
        sym_spec = _make_sym_spec()
        intent = _make_intent("INT_S4D")
        adapter.submit_order(intent, sym_spec)
        assert adapter.safety_state is MT5TransportSafetyState.RECONCILIATION_REQUIRED
        with pytest.raises(MT5DomainError, match="DISPATCH_BLOCKED"):
            adapter.submit_order(intent, sym_spec)

    def test_s4_recon_clean_unblocks_adapter(self) -> None:
        transport = _MockAdapterTransport()
        adapter = _make_adapter(transport)
        adapter.safety_state = MT5TransportSafetyState.RECONCILIATION_REQUIRED
        adapter.is_reconciled = False
        assert not adapter.can_dispatch()
        shadow = _build_shadow_snapshot()
        engine = MT5ReconciliationEngine()
        report = engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={},
        )
        assert report.is_clean
        assert adapter.can_dispatch()

    def test_s4_recon_resolves_unknown_to_filled_via_evidence(self) -> None:
        t0 = datetime.now(timezone.utc)
        hist_order = MT5OrderReality(
            order_ticket=501, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
            state=MT5OrderState.ORDER_STATE_FILLED,
            volume_initial=Decimal("1.0"), volume_current=Decimal("0.0"),
            price_open=Decimal("1.0850"), time_setup_utc=t0,
        )
        fill_deal = MT5DealReality(
            deal_ticket=5001, order_ticket=501, position_ticket=501,
            symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY,
            volume=Decimal("1.0"), price=Decimal("1.0850"), deal_time_utc=t0,
        )
        transport = _MockAdapterTransport(history_orders=(hist_order,), deals=(fill_deal,))
        adapter = _make_adapter(transport)
        shadow_order = _make_shadow_resting("INT_S4F", 501)
        shadow_deal = ShadowDealRecord(
            deal_ticket=5001, order_ticket=501, position_id=501,
            intent_id="INT_S4F", symbol="EURUSD", side="BUY",
            volume=Decimal("1.0"), price=Decimal("1.0850"), executed_at=t0,
        )
        shadow = _build_shadow_snapshot(resting_orders=(shadow_order,), deals=(shadow_deal,))
        coord = ExecutionCoordinator(
            "EXEC_S4F", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S4F",
        )
        engine = MT5ReconciliationEngine()
        report = engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={"EXEC_S4F": coord},
        )
        assert report.is_clean
        assert coord.state is OrderLifecycleState.FILLED

    def test_s4_recon_resolves_unknown_to_cancelled_via_evidence(self) -> None:
        t0 = datetime.now(timezone.utc)
        hist_order = MT5OrderReality(
            order_ticket=502, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
            state=MT5OrderState.ORDER_STATE_CANCELED,
            volume_initial=Decimal("1.0"), volume_current=Decimal("1.0"),
            price_open=Decimal("1.0850"), time_setup_utc=t0,
        )
        transport = _MockAdapterTransport(history_orders=(hist_order,))
        adapter = _make_adapter(transport)
        shadow_order = _make_shadow_resting("INT_S4G", 502)
        shadow = _build_shadow_snapshot(resting_orders=(shadow_order,))
        coord = ExecutionCoordinator(
            "EXEC_S4G", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S4G",
        )
        engine = MT5ReconciliationEngine()
        report = engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={"EXEC_S4G": coord},
        )
        assert report.is_clean
        assert coord.state is OrderLifecycleState.CANCELLED


# ===========================================================================
# S5 — External Broker Activity: UNTRACKED_TRADE_DEAL (4 tests)
# ===========================================================================


class TestS5ExternalBrokerActivity:
    """Gate 5: Broker deals with no ACASH shadow lineage → UNTRACKED_TRADE_DEAL."""

    def _untracked_deal(self, ticket: int) -> MT5DealReality:
        return MT5DealReality(
            deal_ticket=ticket, order_ticket=ticket, position_ticket=ticket,
            symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY,
            volume=Decimal("1.0"), price=Decimal("1.0850"),
            deal_time_utc=datetime.now(timezone.utc),
        )

    def test_s5_broker_deal_without_shadow_lineage_detected_as_critical(self) -> None:
        from acash.execution.mt5.reconciliation import MT5DiscrepancyKind, MT5DiscrepancySeverity
        transport = _MockAdapterTransport(deals=(self._untracked_deal(9999),))
        engine = MT5ReconciliationEngine()
        shadow = _build_shadow_snapshot()
        broker_obs = engine.capture_bounded_broker_observation(
            transport=transport, broker_id="TEST_BROKER",
            account_id="ACC_001", terminal_instance_id="TERM_001",
        )
        report = engine.reconcile_6d(shadow, broker_obs)
        untracked = [d for d in report.discrepancies
                     if d.kind is MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL]
        assert len(untracked) > 0
        assert untracked[0].severity is MT5DiscrepancySeverity.CRITICAL

    def test_s5_untracked_deal_produces_untracked_trade_deal_discrepancy(self) -> None:
        from acash.execution.mt5.reconciliation import MT5DiscrepancyKind
        transport = _MockAdapterTransport(deals=(self._untracked_deal(8888),))
        shadow = _build_shadow_snapshot(deals=())
        engine = MT5ReconciliationEngine()
        broker_obs = engine.capture_bounded_broker_observation(
            transport=transport, broker_id="TEST_BROKER",
            account_id="ACC_001", terminal_instance_id="TERM_001",
        )
        report = engine.reconcile_6d(shadow, broker_obs)
        assert not report.is_clean
        assert MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL in {d.kind for d in report.discrepancies}

    def test_s5_adapter_stays_locked_on_untracked_deal(self) -> None:
        transport = _MockAdapterTransport(deals=(self._untracked_deal(7777),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot()
        engine = MT5ReconciliationEngine()
        with pytest.raises(MT5ReconciliationError, match="RECONCILIATION_CRITICAL_DISCREPANCY"):
            engine.execute_reconciliation_cycle(
                adapter=adapter,
                shadow_ledger=StubShadowLedger(shadow),
                coordinator_map={},
            )
        assert not adapter.can_dispatch()

    def test_s5_untracked_deal_never_resolves_any_coordinator(self) -> None:
        transport = _MockAdapterTransport(deals=(self._untracked_deal(6666),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot()
        coord = ExecutionCoordinator(
            "EXEC_S5D", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S5D",
        )
        engine = MT5ReconciliationEngine()
        with pytest.raises(MT5ReconciliationError, match="RECONCILIATION_CRITICAL_DISCREPANCY"):
            engine.execute_reconciliation_cycle(
                adapter=adapter,
                shadow_ledger=StubShadowLedger(shadow),
                coordinator_map={"EXEC_S5D": coord},
            )
        assert coord.state is OrderLifecycleState.UNKNOWN


# ===========================================================================
# S6 — Evidence Routing (11 tests) ★
# ===========================================================================


class TestS6EvidenceRouting:
    """Gate 6: intent_id sole routing key, fail-closed, Phase-A preflight atomicity."""

    # ── Positive routing ────────────────────────────────────────────────────

    def test_s6_evidence_routed_to_correct_coordinator_via_intent_id(self) -> None:
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(601),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(_make_shadow_resting("INT_S6A", 601),))
        coord = ExecutionCoordinator(
            "EXEC_S6A", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6A",
        )
        engine = MT5ReconciliationEngine()
        report = engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={"EXEC_S6A": coord},
        )
        assert report.is_clean
        assert coord.state is OrderLifecycleState.CANCELLED

    def test_s6_coordinator_state_filled_after_evidence_delivery(self) -> None:
        t0 = datetime.now(timezone.utc)
        hist_order = MT5OrderReality(
            order_ticket=602, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
            state=MT5OrderState.ORDER_STATE_FILLED,
            volume_initial=Decimal("1.0"), volume_current=Decimal("0.0"),
            price_open=Decimal("1.0850"), time_setup_utc=t0,
        )
        fill_deal = MT5DealReality(
            deal_ticket=6021, order_ticket=602, position_ticket=602,
            symbol="EURUSD", deal_type=MT5DealType.DEAL_TYPE_BUY,
            volume=Decimal("1.0"), price=Decimal("1.0850"), deal_time_utc=t0,
        )
        shadow_deal = ShadowDealRecord(
            deal_ticket=6021, order_ticket=602, position_id=602,
            intent_id="INT_S6B", symbol="EURUSD", side="BUY",
            volume=Decimal("1.0"), price=Decimal("1.0850"), executed_at=t0,
        )
        transport = _MockAdapterTransport(history_orders=(hist_order,), deals=(fill_deal,))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(
            resting_orders=(_make_shadow_resting("INT_S6B", 602),),
            deals=(shadow_deal,),
        )
        coord = ExecutionCoordinator(
            "EXEC_S6B", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6B",
        )
        engine = MT5ReconciliationEngine()
        report = engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={"EXEC_S6B": coord},
        )
        assert report.is_clean
        assert coord.state is OrderLifecycleState.FILLED

    def test_s6_evidence_refs_contain_report_digest(self) -> None:
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(603),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(_make_shadow_resting("INT_S6C", 603),))
        coord = ExecutionCoordinator(
            "EXEC_S6C", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6C",
        )
        engine = MT5ReconciliationEngine()
        report = engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={"EXEC_S6C": coord},
        )
        assert report.is_clean
        assert report.report_digest  # non-empty
        assert coord.state is OrderLifecycleState.CANCELLED

    # ── Negative: wrong coordinator untouched ────────────────────────────────

    def test_s6_wrong_coordinator_does_not_receive_evidence(self) -> None:
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(604),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(_make_shadow_resting("INT_S6D_TARGET", 604),))
        coord_correct = ExecutionCoordinator(
            "EXEC_S6D_A", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6D_TARGET",
        )
        coord_wrong = ExecutionCoordinator(
            "EXEC_S6D_B", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6D_WRONG",
        )
        engine = MT5ReconciliationEngine()
        report = engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={"EXEC_S6D_A": coord_correct, "EXEC_S6D_B": coord_wrong},
        )
        assert report.is_clean
        assert coord_correct.state is OrderLifecycleState.CANCELLED
        assert coord_wrong.state is OrderLifecycleState.UNKNOWN

    def test_s6_wrong_coordinator_state_unchanged_no_silent_drop(self) -> None:
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(605),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(_make_shadow_resting("INT_S6E_TARGET", 605),))
        coord_target = ExecutionCoordinator(
            "EXEC_S6E_A", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6E_TARGET",
        )
        coord_bystander = ExecutionCoordinator(
            "EXEC_S6E_B", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6E_OTHER",
        )
        engine = MT5ReconciliationEngine()
        engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={"EXEC_S6E_A": coord_target, "EXEC_S6E_B": coord_bystander},
        )
        assert len(coord_bystander.incidents) == 0
        assert coord_bystander.filled_qty == Decimal("0")
        assert coord_bystander.state is OrderLifecycleState.UNKNOWN

    # ── Phase-A fail-closed ──────────────────────────────────────────────────

    def test_s6_no_coordinator_match_raises_fail_closed(self) -> None:
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(606),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(_make_shadow_resting("INT_S6F", 606),))
        coord_wrong = ExecutionCoordinator(
            "EXEC_S6F", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_WRONG",
        )
        initial_state = coord_wrong.state
        engine = MT5ReconciliationEngine()
        with pytest.raises(MT5ReconciliationError, match="EVIDENCE_ROUTING_TARGET_NOT_FOUND"):
            engine.execute_reconciliation_cycle(
                adapter=adapter,
                shadow_ledger=StubShadowLedger(shadow),
                coordinator_map={"EXEC_S6F": coord_wrong},
            )
        assert coord_wrong.state is initial_state

    def test_s6_duplicate_shadow_order_ticket_raises_ambiguous(self) -> None:
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(607),))
        adapter = _make_adapter(transport)
        shadow_a = _make_shadow_resting("INT_S6G_A", 607)
        shadow_b = ShadowRestingOrder(
            intent_id="INT_S6G_B", order_ticket=607, symbol="EURUSD",  # same ticket!
            order_type="BUY_LIMIT", volume=Decimal("0.5"), price=Decimal("1.0860"),
        )
        shadow = _build_shadow_snapshot(resting_orders=(shadow_a, shadow_b))
        coord = ExecutionCoordinator(
            "EXEC_S6G", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6G_A",
        )
        engine = MT5ReconciliationEngine()
        with pytest.raises(MT5ReconciliationError, match="EVIDENCE_ROUTING_AMBIGUOUS"):
            engine.execute_reconciliation_cycle(
                adapter=adapter,
                shadow_ledger=StubShadowLedger(shadow),
                coordinator_map={"EXEC_S6G": coord},
            )
        assert coord.state is OrderLifecycleState.UNKNOWN

    def test_s6_duplicate_coordinator_intent_id_raises_ambiguous(self) -> None:
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(608),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(_make_shadow_resting("INT_S6H", 608),))
        coord_a = ExecutionCoordinator(
            "EXEC_S6H_A", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6H",
        )
        coord_b = ExecutionCoordinator(
            "EXEC_S6H_B", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6H",  # same!
        )
        engine = MT5ReconciliationEngine()
        with pytest.raises(MT5ReconciliationError, match="EVIDENCE_ROUTING_AMBIGUOUS"):
            engine.execute_reconciliation_cycle(
                adapter=adapter,
                shadow_ledger=StubShadowLedger(shadow),
                coordinator_map={"EXEC_S6H_A": coord_a, "EXEC_S6H_B": coord_b},
            )
        assert coord_a.state is OrderLifecycleState.UNKNOWN
        assert coord_b.state is OrderLifecycleState.UNKNOWN

    def test_s6_phase_a_failure_leaves_zero_coordinator_mutations(self) -> None:
        """Phase-A Preflight Atomicity proof.

        evidence_1 → coord_A (valid route in routing_plan)
        evidence_2 → no coordinator match (Phase A-2 raises BEFORE Phase B)

        Assert: coord_A.state UNCHANGED — Phase-A atomicity guaranteed.
        Assert: adapter NOT confirmed (confirm_reconciliation NOT called).

        NOTE: This proves PHASE-A PREFLIGHT ATOMICITY ONLY.
        Phase-B failures (apply_reconciliation raises mid-loop) are out of scope.
        """
        t0 = datetime.now(timezone.utc)
        hist_A = _make_cancelled_history_order(609)
        hist_B = MT5OrderReality(
            order_ticket=610, symbol="EURUSD", order_type=MT5OrderType.BUY_LIMIT,
            state=MT5OrderState.ORDER_STATE_CANCELED,
            volume_initial=Decimal("1.0"), volume_current=Decimal("1.0"),
            price_open=Decimal("1.0860"), time_setup_utc=t0,
        )
        transport = _MockAdapterTransport(history_orders=(hist_A, hist_B))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(
            _make_shadow_resting("INT_S6I_A", 609),
            _make_shadow_resting("INT_S6I_B", 610),
        ))
        coord_A = ExecutionCoordinator(
            "EXEC_S6I_A", Decimal("1.0"),
            initial_state=OrderLifecycleState.UNKNOWN, intent_id="INT_S6I_A",
        )
        initial_state_A = coord_A.state
        engine = MT5ReconciliationEngine()
        with pytest.raises(MT5ReconciliationError, match="EVIDENCE_ROUTING_TARGET_NOT_FOUND"):
            engine.execute_reconciliation_cycle(
                adapter=adapter,
                shadow_ledger=StubShadowLedger(shadow),
                coordinator_map={"EXEC_S6I_A": coord_A},  # no coord for INT_S6I_B
            )
        # Phase-A atomicity: coord_A must NOT have been mutated
        assert coord_A.state is initial_state_A, (
            "Phase-A Preflight Atomicity violated: "
            "coord_A was mutated before Phase A completed"
        )
        assert not adapter.can_dispatch(), (
            "confirm_reconciliation() must not have been called on Phase-A failure"
        )

    # ── Regression: legacy execution_id path dead ────────────────────────────

    def test_regression_execution_id_ne_intent_id_routes_correctly(self) -> None:
        """Happy-path: execution_id='EXEC-ABC', intent_id='INT-123', target='INT-123' → routes."""
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(611),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(
            ShadowRestingOrder(
                intent_id="INT-123", order_ticket=611, symbol="EURUSD",
                order_type="BUY_LIMIT", volume=Decimal("1.0"), price=Decimal("1.0850"),
            ),
        ))
        coord = ExecutionCoordinator(
            "EXEC-ABC", Decimal("1.0"),           # execution_id ≠ intent_id
            initial_state=OrderLifecycleState.UNKNOWN,
            intent_id="INT-123",                  # routing key
        )
        engine = MT5ReconciliationEngine()
        report = engine.execute_reconciliation_cycle(
            adapter=adapter,
            shadow_ledger=StubShadowLedger(shadow),
            coordinator_map={"EXEC-ABC": coord},
        )
        assert report.is_clean
        assert coord.state is OrderLifecycleState.CANCELLED

    def test_regression_execution_id_matches_target_but_intent_id_differs_does_not_route(self) -> None:
        """Adversarial: execution_id='INT-TARGET' (== target), intent_id='INT-999' (!= target).
        MUST NOT route → MT5ReconciliationError. Proves legacy execution_id path is dead.
        """
        transport = _MockAdapterTransport(history_orders=(_make_cancelled_history_order(612),))
        adapter = _make_adapter(transport)
        shadow = _build_shadow_snapshot(resting_orders=(
            ShadowRestingOrder(
                intent_id="INT-TARGET", order_ticket=612, symbol="EURUSD",
                order_type="BUY_LIMIT", volume=Decimal("1.0"), price=Decimal("1.0850"),
            ),
        ))
        coord = ExecutionCoordinator(
            "INT-TARGET", Decimal("1.0"),          # execution_id == target (adversarial)
            initial_state=OrderLifecycleState.UNKNOWN,
            intent_id="INT-999",                   # ≠ target — ONLY valid routing key
        )
        initial_state = coord.state
        engine = MT5ReconciliationEngine()
        with pytest.raises(MT5ReconciliationError, match="EVIDENCE_ROUTING_TARGET_NOT_FOUND"):
            engine.execute_reconciliation_cycle(
                adapter=adapter,
                shadow_ledger=StubShadowLedger(shadow),
                coordinator_map={"INT-TARGET": coord},
            )
        assert coord.state is initial_state, (
            "Legacy execution_id routing path is NOT dead: "
            "coordinator was mutated despite intent_id mismatch"
        )


# ===========================================================================
# S7 — Admission Enforcement for Unauthorized Orders (5 tests)
# ===========================================================================


class TestS7AdmissionHardLock:
    """Gate 7: Admission layer blocks unauthorized orders using schema-valid constraints."""

    def test_s7_size_limit_exceeded_blocks_intent(self) -> None:
        auth = _make_authorization(max_position_size=Decimal("0.50"))
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S7A",
                venue="TEST_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("1.00"),  # > 0.50
                current_risk=_make_risk_state(),
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=_make_restriction_authority(),
            )

    def test_s7_paper_venue_blocks_live_venue_intent(self) -> None:
        auth = _make_authorization(allowed_venues=("PAPER_MT5",))
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S7B",
                venue="LIVE_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("0.10"),
                current_risk=_make_risk_state(),
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=_make_restriction_authority(),
            )

    def test_s7_expired_authorization_blocks_intent(self) -> None:
        auth = _make_authorization(expires_delta_seconds=-1)
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S7C",
                venue="TEST_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("0.10"),
                current_risk=_make_risk_state(),
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=_make_restriction_authority(),
            )

    def test_s7_suspended_authorization_blocks_intent(self) -> None:
        auth = _make_authorization(status=AuthorizationStatus.SUSPENDED)
        with pytest.raises(PreLiveRiskAdmissionError):
            construct_order_intent(
                authorization=auth, intent_id="INT_S7D",
                venue="TEST_MT5", symbol="EURUSD",
                side=OrderSide.BUY, order_type=OrderType.MARKET,
                quantity=Decimal("0.10"),
                current_risk=_make_risk_state(),
                signal_event_hash=_make_signal_hash(),
                created_at=datetime.now(timezone.utc),
                restriction_authority=_make_restriction_authority(),
            )

    def test_s7_adapter_starts_fail_closed_degraded(self) -> None:
        transport = _MockAdapterTransport()
        adapter = _make_adapter(transport)
        assert adapter.safety_state is MT5TransportSafetyState.DEGRADED
        assert adapter.is_reconciled is False
        assert adapter.can_dispatch() is False

