"""Unit and integration tests for Phase 12 Slice 3: MT5 Transport & Broker Adapter (CONN-MT5)."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.execution.broker_events import BrokerEventKind
from acash.execution.mt5.adapter import MT5BrokerAdapter, MT5BrokerObservation
from acash.execution.mt5.enums import (
    MT5ExecutionPolicy,
    MT5OrderType,
    MT5Retcode,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5ValidationError,
)
from acash.execution.mt5.schemas import BrokerSymbolSpec
from acash.execution.mt5.transport import (
    MockMT5Transport,
    MT5ReconciliationConfirmation,
    MT5TransportSafetyState,
    TransportFailureCause,
)
from acash.execution.schema import OrderIntent, OrderSide, OrderType, TimeInForce
from acash.execution.state_machine import ExecutionEvent
from typing import Any, Dict


@pytest.fixture
def mock_transport() -> MockMT5Transport:
    return MockMT5Transport(broker_id="IC_MARKETS", account_id="ACC_1001")


@pytest.fixture
def symbol_spec() -> BrokerSymbolSpec:
    digest = BrokerSymbolSpec.compute_spec_digest(
        canonical_symbol="EURUSD",
        broker_symbol="EURUSD.pro",
        contract_size=Decimal("100000"),
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
        broker_symbol="EURUSD.pro",
        contract_size=Decimal("100000"),
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


@pytest.fixture
def adapter(mock_transport: MockMT5Transport, symbol_spec: BrokerSymbolSpec) -> MT5BrokerAdapter:
    mock_transport.register_symbol_spec(symbol_spec)
    return MT5BrokerAdapter(
        broker_id="IC_MARKETS",
        account_id="ACC_1001",
        terminal_instance_id="TERMINAL_01",
        transport=mock_transport,
    )


@pytest.fixture
def sample_intent() -> OrderIntent:
    return OrderIntent(
        intent_id="INTENT_1001",
        authorization_id="AUTH_999",
        strategy_id="MOM_01",
        venue="MT5",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.GTC,
        quantity=Decimal("100000"),  # 100,000 units = 1.00 lot
        created_at=datetime.now(timezone.utc),
        signal_event_hash="0" * 64,
        risk_snapshot_hash="1" * 64,
        intent_digest="2" * 64,
    )


def make_valid_confirmation(adapter: MT5BrokerAdapter) -> MT5ReconciliationConfirmation:
    return MT5ReconciliationConfirmation(
        reconciliation_id="REC_20260902_001",
        broker_id=adapter.broker_id,
        account_id=adapter.account_id,
        verified_at=datetime.now(timezone.utc),
        orders_verified=True,
        deals_verified=True,
        positions_verified=True,
        account_verified=True,
        is_complete=True,
        discrepancies_count=0,
    )


# --- T1: Terminal IPC Unreachable ---
def test_t1_terminal_ipc_unreachable(adapter: MT5BrokerAdapter, mock_transport: MockMT5Transport) -> None:
    mock_transport.set_terminal_healthy(False)
    report = adapter.check_health()
    assert report.is_connected is False
    assert report.is_healthy is False
    assert report.failure_cause == TransportFailureCause.TERMINAL_IPC_UNAVAILABLE
    assert report.safety_state == MT5TransportSafetyState.DEGRADED


# --- T2: Trade Server Disconnected ---
def test_t2_trade_server_disconnected(adapter: MT5BrokerAdapter, mock_transport: MockMT5Transport) -> None:
    mock_transport.set_connected(False)
    report = adapter.check_health()
    assert report.is_connected is False
    assert report.is_healthy is False
    assert report.failure_cause == TransportFailureCause.TRADE_SERVER_DISCONNECTED
    assert report.safety_state == MT5TransportSafetyState.DEGRADED


# --- T3: Trading Permissions Disabled ---
def test_t3_trading_permissions_disabled(adapter: MT5BrokerAdapter, mock_transport: MockMT5Transport) -> None:
    mock_transport.set_trading_permissions(trade_allowed=False, trade_expert=True)
    report = adapter.check_health()
    assert report.is_connected is True
    assert report.is_healthy is True
    assert report.is_trade_allowed is False
    assert report.failure_cause == TransportFailureCause.TRADING_PERMISSION_DISABLED
    assert report.safety_state == MT5TransportSafetyState.DEGRADED


# --- T4: order_send Timeout Uncertainty ---
def test_t4_order_send_timeout_uncertainty(
    adapter: MT5BrokerAdapter,
    mock_transport: MockMT5Transport,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    # First unblock adapter
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    assert adapter.can_dispatch() is True

    # Inject timeout
    mock_transport.set_timeout_on_order_send(True)
    obs = adapter.submit_order(sample_intent, symbol_spec)

    assert obs.event_kind == BrokerEventKind.CONNECTION_LOST
    assert obs.requires_reconciliation is True
    assert obs.execution_event == ExecutionEvent.CONNECTION_LOST
    assert adapter.safety_state == MT5TransportSafetyState.RECONCILIATION_REQUIRED
    assert adapter.is_reconciled is False
    assert adapter.can_dispatch() is False


# --- T5: Subsequent Dispatch Blocked ---
def test_t5_submit_order_blocked_when_cannot_dispatch(
    adapter: MT5BrokerAdapter,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    # Fresh adapter is in DEGRADED and is_reconciled=False
    assert adapter.can_dispatch() is False
    with pytest.raises(MT5DomainError, match="DISPATCH_BLOCKED"):
        adapter.submit_order(sample_intent, symbol_spec)


# --- T6: Reconciliation Confirmation Unblocks Dispatch ---
def test_t6_confirm_reconciliation_unblocks_dispatch(
    adapter: MT5BrokerAdapter,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    assert adapter.safety_state == MT5TransportSafetyState.READY
    assert adapter.is_reconciled is True
    assert adapter.can_dispatch() is True

    # Order can now be submitted
    obs = adapter.submit_order(sample_intent, symbol_spec)
    assert obs.event_kind in (BrokerEventKind.ACK, BrokerEventKind.FILLED)
    assert obs.execution_event in (ExecutionEvent.ACK, ExecutionEvent.FILL)


# --- T7: Retcode 10031 Emits Connection Lost Not Rejected ---
def test_t7_retcode_10031_emits_connection_lost_not_rejected(
    adapter: MT5BrokerAdapter,
    mock_transport: MockMT5Transport,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    mock_transport.set_injected_retcode(MT5Retcode.TRADE_RETCODE_CONNECTION.value)

    obs = adapter.submit_order(sample_intent, symbol_spec)
    assert obs.event_kind == BrokerEventKind.CONNECTION_LOST
    assert obs.requires_reconciliation is True
    assert obs.execution_event == ExecutionEvent.CONNECTION_LOST
    assert adapter.safety_state == MT5TransportSafetyState.RECONCILIATION_REQUIRED
    assert adapter.is_reconciled is False


# --- T8: Lineage Envelope Correlation ---
def test_t8_lineage_envelope_preservation(
    adapter: MT5BrokerAdapter,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    obs = adapter.submit_order(sample_intent, symbol_spec)
    assert obs.lineage.broker_id == adapter.broker_id
    assert obs.lineage.account_id == adapter.account_id
    assert obs.lineage.strategy_id == sample_intent.strategy_id
    assert obs.lineage.intent_id == sample_intent.intent_id


# --- T9: State Authority Isolation Invariant ---
def test_t9_state_authority_isolation(
    adapter: MT5BrokerAdapter,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    obs = adapter.submit_order(sample_intent, symbol_spec)
    # The adapter returns a raw observation and does NOT execute any state transitions
    assert isinstance(obs, MT5BrokerObservation)
    assert hasattr(adapter, "submit_order")
    assert not hasattr(adapter, "transition_order")


# --- T10: 4-Dimensional Reconciliation Queries ---
def test_t10_four_dimensional_reconciliation_queries(
    adapter: MT5BrokerAdapter,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    adapter.submit_order(sample_intent, symbol_spec)

    orders = adapter.fetch_open_orders()
    hist_orders = adapter.fetch_history_orders()
    deals = adapter.fetch_history_deals()
    positions = adapter.fetch_open_positions()
    acc = adapter.fetch_account_state()

    assert isinstance(orders, tuple)
    assert isinstance(hist_orders, tuple)
    assert isinstance(deals, tuple)
    assert isinstance(positions, tuple)
    assert acc is not None
    assert acc.balance == Decimal("100000.00")


# --- T11: Incomplete or Unverified Confirmation Fails Closed ---
def test_t11_incomplete_or_unverified_reconciliation_fails_closed(adapter: MT5BrokerAdapter) -> None:
    # Incomplete confirmation
    incomplete = MT5ReconciliationConfirmation(
        reconciliation_id="REC_INC",
        broker_id=adapter.broker_id,
        account_id=adapter.account_id,
        verified_at=datetime.now(timezone.utc),
        orders_verified=True,
        deals_verified=True,
        positions_verified=False,  # Unverified dimension!
        account_verified=True,
        is_complete=False,
    )
    with pytest.raises(MT5ValidationError, match="INCOMPLETE_RECONCILIATION_EVIDENCE"):
        adapter.confirm_reconciliation(incomplete)

    assert adapter.is_reconciled is False
    assert adapter.can_dispatch() is False


# --- T12: account.trade_allowed == False Blocks Dispatch ---
def test_t12_account_trade_allowed_false_blocks_dispatch(
    adapter: MT5BrokerAdapter,
    mock_transport: MockMT5Transport,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    assert adapter.can_dispatch() is True

    # Account trade permission revoked
    mock_transport.set_trading_permissions(trade_allowed=False, trade_expert=True)
    report = adapter.check_health()
    assert report.is_trade_allowed is False
    assert adapter.safety_state == MT5TransportSafetyState.DEGRADED
    assert adapter.can_dispatch() is False

    with pytest.raises(MT5DomainError, match="DISPATCH_BLOCKED"):
        adapter.submit_order(sample_intent, symbol_spec)


# --- T13: terminal.trade_expert == False Blocks Dispatch ---
def test_t13_terminal_trade_expert_false_blocks_dispatch(
    adapter: MT5BrokerAdapter,
    mock_transport: MockMT5Transport,
    symbol_spec: BrokerSymbolSpec,
    sample_intent: OrderIntent,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    mock_transport.set_trading_permissions(trade_allowed=True, trade_expert=False)
    report = adapter.check_health()
    assert report.is_trade_allowed is False
    assert adapter.safety_state == MT5TransportSafetyState.DEGRADED
    assert adapter.can_dispatch() is False


# --- T14: Fresh Adapter Baseline ---
def test_t14_fresh_adapter_baseline(adapter: MT5BrokerAdapter) -> None:
    assert adapter.safety_state == MT5TransportSafetyState.DEGRADED
    assert adapter.is_reconciled is False
    assert adapter.can_dispatch() is False


# --- T15: Transient Permission Loss & Restoration ---
def test_t15_transient_permission_loss_and_restoration(
    adapter: MT5BrokerAdapter,
    mock_transport: MockMT5Transport,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    assert adapter.safety_state == MT5TransportSafetyState.READY
    assert adapter.is_reconciled is True

    # Permission loss
    mock_transport.set_trading_permissions(trade_allowed=False, trade_expert=True)
    report_deg = adapter.check_health()
    assert report_deg.safety_state == MT5TransportSafetyState.DEGRADED
    assert adapter.is_reconciled is True  # Invariant: reconciliation preserved

    # Permission restored
    mock_transport.set_trading_permissions(trade_allowed=True, trade_expert=True)
    report_ready = adapter.check_health()
    assert report_ready.safety_state == MT5TransportSafetyState.READY
    assert adapter.can_dispatch() is True


# --- T16: Health Restoration Cannot Bypass Reconciliation ---
def test_t16_health_restoration_cannot_bypass_reconciliation(
    adapter: MT5BrokerAdapter,
    mock_transport: MockMT5Transport,
) -> None:
    adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    adapter.mark_reconciliation_required(TransportFailureCause.ORDER_SEND_TIMEOUT_UNCERTAIN)
    assert adapter.safety_state == MT5TransportSafetyState.RECONCILIATION_REQUIRED
    assert adapter.is_reconciled is False

    # Check health when healthy
    report = adapter.check_health()
    assert report.is_connected is True
    assert report.is_healthy is True
    assert report.safety_state == MT5TransportSafetyState.RECONCILIATION_REQUIRED
    assert adapter.can_dispatch() is False


# --- T17: Absorbing BLOCKED State & Truthful Health Reporting ---
def test_t17_blocked_state_absorbing_and_truthful_health(
    adapter: MT5BrokerAdapter,
    mock_transport: MockMT5Transport,
) -> None:
    adapter.mark_blocked("Administrative Emergency Stop")
    assert adapter.safety_state == MT5TransportSafetyState.BLOCKED

    # Truthful health report under BLOCKED state
    report = adapter.check_health()
    assert report.is_connected is True
    assert report.is_healthy is True
    assert report.is_trade_allowed is True
    assert report.safety_state == MT5TransportSafetyState.BLOCKED

    # Transport error cannot unblock BLOCKED
    adapter.mark_reconciliation_required(TransportFailureCause.ORDER_SEND_TIMEOUT_UNCERTAIN)
    assert adapter.safety_state == MT5TransportSafetyState.BLOCKED

    # confirm_reconciliation cannot unblock BLOCKED
    with pytest.raises(MT5ValidationError, match="CANNOT_RECONCILE_BLOCKED_ADAPTER"):
        adapter.confirm_reconciliation(make_valid_confirmation(adapter))
    assert adapter.safety_state == MT5TransportSafetyState.BLOCKED


# --- T18: unblock_emergency Source Guard ---
def test_t18_unblock_emergency_source_guard(adapter: MT5BrokerAdapter) -> None:
    # Cannot call unblock_emergency from DEGRADED state
    assert adapter.safety_state == MT5TransportSafetyState.DEGRADED
    with pytest.raises(MT5ValidationError, match="EMERGENCY_UNBLOCK_REQUIRES_BLOCKED_STATE"):
        adapter.unblock_emergency("ADMIN_TOKEN_123")

    # Mark blocked
    adapter.mark_blocked("Manual Kill")
    report = adapter.check_health()
    assert report.safety_state == MT5TransportSafetyState.BLOCKED

    # Empty token fails closed
    with pytest.raises(MT5ValidationError, match="OVERRIDE_TOKEN_REQUIRED"):
        adapter.unblock_emergency("")

    # Valid token transitions to RECONCILIATION_REQUIRED
    adapter.unblock_emergency("ADMIN_TOKEN_123")
    report_recon = adapter.check_health()
    assert report_recon.safety_state == MT5TransportSafetyState.RECONCILIATION_REQUIRED
    assert adapter.is_reconciled is False
    assert adapter.can_dispatch() is False


# --- NativeMT5Transport Translation & Error Handling Tests ---

class DummyNamedTuple:
    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_native_transport_import_error_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from acash.execution.mt5.transport import NativeMT5Transport

    def fake_import(name: str) -> object:
        raise ImportError("No module named MetaTrader5")

    monkeypatch.setattr("importlib.import_module", fake_import)

    transport = NativeMT5Transport()
    with pytest.raises(MT5DomainError, match="MetaTrader5 package is not available"):
        transport.is_connected()


def test_native_transport_translation(monkeypatch: pytest.MonkeyPatch) -> None:
    from acash.execution.mt5.transport import NativeMT5Transport, MT5TransportCommand

    mock_terminal = DummyNamedTuple(
        connected=True,
        trade_allowed=True,
        trade_expert=True,
        community_account=False,
        community_connection=False,
    )
    mock_account = DummyNamedTuple(
        login=999999,
        trade_mode=2,
        leverage=500,
        limit_orders=500,
        margin_so_mode=0,
        trade_allowed=True,
        trade_expert=True,
        balance=50000.0,
        credit=0.0,
        profit=123.45,
        equity=50123.45,
        margin=1000.0,
        margin_free=49123.45,
        margin_level=5012.3,
        margin_so_call=50.0,
        margin_so_so=30.0,
        margin_initial=0.0,
        margin_maintenance=0.0,
        currency="USD",
    )
    mock_symbol = DummyNamedTuple(
        name="EURUSD.raw",
        trade_contract_size=100000.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        digits=5,
        point=0.00001,
        trade_tick_size=0.00001,
        trade_execution_mode=2,
        filling_mode=7,  # FOK (1) + IOC (2) + BOC (4)
        trade_stops_level=15,
        currency_margin="EUR",
        currency_profit="USD",
    )
    mock_order_res = DummyNamedTuple(
        retcode=10009,
        deal=88888,
        order=77777,
        volume=1.0,
        price=1.08550,
        bid=1.08548,
        ask=1.08550,
        comment="Deal executed",
        request_id=10,
        retcode_external=0,
    )

    class MockNativeMT5Module:
        @staticmethod
        def terminal_info() -> object:
            return mock_terminal

        @staticmethod
        def account_info() -> object:
            return mock_account

        @staticmethod
        def symbol_info(symbol: str) -> object:
            return mock_symbol

        @staticmethod
        def order_send(req: Dict[str, Any]) -> object:
            return mock_order_res

    monkeypatch.setattr("importlib.import_module", lambda name: MockNativeMT5Module)

    transport = NativeMT5Transport()
    assert transport.is_connected() is True

    term_info = transport.terminal_info()
    assert term_info is not None
    assert term_info["connected"] is True
    assert term_info["trade_allowed"] is True

    acc_info = transport.account_info()
    assert acc_info is not None
    assert acc_info.login == 999999
    assert acc_info.balance == Decimal("50000.0")
    assert acc_info.equity == Decimal("50123.45")

    sym_spec = transport.symbol_info("EURUSD")
    assert sym_spec is not None
    assert sym_spec.broker_symbol == "EURUSD.raw"
    assert "SYMBOL_FILLING_FOK" in sym_spec.allowed_filling_flags
    assert "SYMBOL_FILLING_IOC" in sym_spec.allowed_filling_flags
    assert "SYMBOL_FILLING_BOC" in sym_spec.allowed_filling_flags

    # Test order_send mapping
    from acash.execution.mt5.schemas import MT5TradeRequest, MT5ExecutionLineage
    from acash.execution.mt5.enums import MT5TradeAction, MT5FillingMode

    req = MT5TradeRequest(
        action=MT5TradeAction.TRADE_ACTION_DEAL,
        symbol="EURUSD",
        volume=Decimal("1.00"),
        price=Decimal("1.08550"),
        type=MT5OrderType.BUY,
        type_filling=MT5FillingMode.ORDER_FILLING_FOK,
    )
    lineage = MT5ExecutionLineage(
        broker_id="MOCK_BROKER",
        account_id="ACC_999",
        terminal_instance_id="TERM_1",
        strategy_id="STRAT_1",
        cycle_id="CYC_1",
        intent_id="INT_1",
    )
    cmd = MT5TransportCommand(request=req, lineage=lineage)
    obs = transport.order_send(cmd)

    assert obs.result.retcode == 10009
    assert obs.result.deal == 88888
    assert obs.result.order == 77777
    assert obs.result.volume == Decimal("1.0")
    assert obs.result.price == Decimal("1.08550")

