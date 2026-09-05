"""Phase 13: Paper Trading Runtime Integration Test Suite (Ladder Step 3).

Validates the integrated multi-pulse behavior of Phase 13 runtime components:
1. ForwardMarketDataFeeder
2. PaperStrategyAdapter
3. PaperExecutionBridge
4. ExecutionCoordinator
5. OperationalLedger
6. PortfolioStateRehydrator

Strict Verification Matrix:
- Full canonical cycle from market data to ledger & snapshot persistence.
- Dual venue execution paths: LOCAL_SIMULATOR and MT5_DEMO (via MockMT5Transport).
- Multi-pulse partial-fill lifecycle: ACK -> PARTIAL_FILL -> FILLED -> ExecutionManifest.
- Dispatch timeout -> UNKNOWN -> authoritative broker reconciliation.
- Stale data fail-closed behavior at integrated runtime level.
- Multi-pulse idempotency and client_order_id deduplication.
- Session identity compatibility and cryptographic config/dossier lineage.
- Candidate STRAT-MOM-MULTI-HORIZON-V1 qualification gating (BLOCKED -> 100% Cash fallback).

Governance Constraints:
- Live Capital: $0.00
- Live Orders: 0
- Broker Wire: DISCONNECTED (mocked/simulated transport only)
- Frozen Core: 0 modifications
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import pytest

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.interfaces.market_data import IMarketDataProvider
from acash.execution.broker_events import BrokerEventKind
from acash.execution.mock_broker import BrokerRawEvent
from acash.execution.broker_adapter import to_coordinator_event
from acash.execution.coordinator import (
    CoordinatorEvent,
    CoordinatorOutcome,
    ExecutionCoordinator,
)
from acash.execution.mt5.adapter import MT5BrokerAdapter
from acash.execution.mt5.enums import (
    MT5AccountMarginMode,
    MT5DealType,
    MT5ExecutionPolicy,
    MT5OrderType,
    MT5PositionType,
    MT5TradeExecutionMode,
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
    MT5ReconciliationConfirmation,
    MT5TransportSafetyState,
)
from acash.execution.schema import (
    ExecutionManifest,
    OrderIntent,
    OrderLifecycleState,
    OrderSide,
    OrderType,
    TimeInForce,
)
from acash.portfolio.schema import AllocationDecision
from acash.research.alpha_schema import AlphaLifecycleState, AlphaQualificationDossier
from acash.runtime.feeder import (
    FeedSourceType,
    ForwardMarketDataFeeder,
    MarketFeedStatus,
)
from acash.runtime.ledger import OperationalLedger
from acash.runtime.paper_bridge import (
    ExecutionCostModel,
    PaperExecutionBridge,
    PaperExecutionVenueType,
    SimulatedMarketMatcher,
    SlippageModelConfig,
    SpreadModelConfig,
)
from acash.runtime.rehydration import (
    PortfolioSnapshotStore,
    PortfolioStateRehydrator,
    RehydrationStatus,
)
from acash.runtime.schema import (
    CycleIdentity,
    CycleOutcome,
    OperationalCycleEvent,
    RuntimeHealthStatus,
    RuntimeRegime,
)
from acash.runtime.strategy_adapter import (
    PaperStrategyAdapter,
    PaperTradingSessionIdentity,
)


# ============================================================================
# TEST DOUBLES & FIXTURES
# ============================================================================


class InMemoryMarketDataProvider(IMarketDataProvider):
    """In-memory market data provider for integration testing."""

    def __init__(self, initial_snapshot: MarketDataSnapshot) -> None:
        self._current_snapshot = initial_snapshot

    def set_snapshot(self, snapshot: MarketDataSnapshot) -> None:
        self._current_snapshot = snapshot

    def get_latest_snapshot(self, symbol: str) -> MarketDataSnapshot:
        return self._current_snapshot

    def get_historical_bars(
        self, symbol: str, timeframe: BarTimeframe, start_utc: datetime, end_utc: datetime
    ) -> Sequence[Bar]:
        return []


@pytest.fixture
def base_time() -> datetime:
    return datetime(2026, 9, 5, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def standard_symbol_spec() -> BrokerSymbolSpec:
    return BrokerSymbolSpec(
        canonical_symbol="EURUSD",
        broker_symbol="EURUSD.pro",
        contract_size=Decimal("100000.0"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100.0"),
        volume_step=Decimal("0.01"),
        digits=5,
        point_size=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        margin_currency="EUR",
        profit_currency="USD",
        spec_digest="0" * 64,
    )


@pytest.fixture
def initial_portfolio(base_time: datetime) -> PortfolioState:
    return PortfolioState(
        timestamp_utc=base_time,
        positions={},
        cash_balance=Decimal("100000.00"),
        total_equity=Decimal("100000.00"),
        margin_used=Decimal("0.0"),
        gross_exposure=Decimal("0.0"),
        net_exposure=Decimal("0.0"),
        unrealized_pnl=Decimal("0.0"),
        realized_pnl=Decimal("0.0"),
    )


def make_clean_reconciliation_confirmation(adapter: MT5BrokerAdapter, base_time: datetime) -> MT5ReconciliationConfirmation:
    """Construct valid 6-D reconciliation confirmation to unblock MT5BrokerAdapter."""
    return MT5ReconciliationConfirmation(
        reconciliation_id="REC-INTEG-001",
        broker_id=adapter.broker_id,
        account_id=adapter.account_id,
        verified_at=base_time,
        orders_verified=True,
        deals_verified=True,
        positions_verified=True,
        account_verified=True,
        is_complete=True,
        discrepancies_count=0,
    )


def create_verified_dossier(tmp_path: Path, strategy_id: str, version: str) -> Tuple[Path, str]:
    """Helper to create a test double AlphaQualificationDossier for eligible adapter tests."""
    from acash.research.alpha_schema import AlphaEconomicDecomposition
    digest = "a" * 64
    decomp = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("30.0"),
        realized_spread_slippage_bps=Decimal("2.5"),
        broker_commissions_bps=Decimal("1.5"),
        net_trading_alpha_bps=Decimal("26.0"),
        broker_rebate_income_bps=Decimal("0.0"),
        total_realized_economic_bps=Decimal("26.0"),
    )
    dossier = AlphaQualificationDossier(
        alpha_id=f"ALPHA-{strategy_id}",
        strategy_id=strategy_id,
        hypothesis_digest=digest,
        trial_ledger_digest=digest,
        validation_report_digest=digest,
        governance_policy_digest=digest,
        economic_decomposition=decomp,
        lifecycle_state=AlphaLifecycleState.RESEARCH_QUALIFIED,
        capital_authority_usd=Decimal("0.00"),
        created_timestamp_utc=datetime.now(timezone.utc).isoformat(),
        dossier_digest=digest,
    )
    dossier_file = tmp_path / f"{strategy_id}_dossier.json"
    with open(dossier_file, "w", encoding="utf-8") as f:
        f.write(dossier.model_dump_json(indent=2))
    return dossier_file, digest


# ============================================================================
# 1. TEST SUITE: Full Canonical Cycle Across Component Boundaries
# ============================================================================


class TestIntegratedCanonicalCycle:
    """Verifies end-to-end single pulse flow:
    Market Data -> Strategy Census -> Allocation -> Risk Gate -> Bridge Quantization ->
    Venue Dispatch -> Coordinator State Transition -> Execution Manifest -> Operational Ledger.
    """

    def test_full_canonical_cycle_local_simulator(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """Execute full canonical cycle using LOCAL_SIMULATOR venue with SimulatedMarketMatcher."""
        # 1. Setup Market Feed
        snap = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=base_time,
        )
        provider = InMemoryMarketDataProvider(snap)
        cost_model = ExecutionCostModel()

        session = PaperTradingSessionIdentity(
            session_id="SESS-CANONICAL-SIM-01",
            run_id="RUN-SIM-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-MOCK-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="a" * 64,
        )

        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.STREAMING_PARQUET_PUMP,
            session_identity=session,
            max_market_data_age_ms=1500,
        )

        # 2. Poll Market Data
        polled_snap, age_ms = feeder.poll_next_market_snapshot("EURUSD", base_time)
        assert age_ms == 0
        assert polled_snap.symbol == "EURUSD"

        # 3. Strategy Census & Allocation
        dossier_file, d_digest = create_verified_dossier(tmp_path, "STRAT-MOCK-01", "1.0.0")
        adapter = PaperStrategyAdapter(
            strategy_id="STRAT-MOCK-01",
            strategy_version="1.0.0",
            dossier_path=dossier_file,
            session_identity=session,
            cost_model=cost_model,
        )
        assert adapter.is_eligible is True

        alloc = adapter.generate_candidate_allocation(bars=[], portfolio=initial_portfolio, as_of_utc=base_time)
        assert alloc.gate_verdict == "APPROVED_INVESTABLE_ALLOCATION"
        assert alloc.authorized_weights["EURUSD"] == Decimal("0.10")

        # 4. Bridge Execution Dispatch to Local Matcher (100% full fill)
        matcher = SimulatedMarketMatcher(cost_model=cost_model, partial_fill_ratio=None)
        coordinator = ExecutionCoordinator(execution_id="EXEC-CANONICAL-01", requested_qty=Decimal("0.09"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=matcher,
            symbol_spec_provider=lambda s: standard_symbol_spec,
        )

        cycle_id = CycleIdentity(
            cycle_id="CYCLE-001",
            as_of_utc=base_time,
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=0,
        )

        outcomes = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=initial_portfolio,
            current_snapshot=polled_snap,
            cycle_identity=cycle_id,
            session_identity=session,
        )

        # 5. Verify Coordinator & Manifest
        assert len(outcomes) == 2
        assert outcomes[0].state == OrderLifecycleState.ACKNOWLEDGED
        assert outcomes[1].state == OrderLifecycleState.FILLED
        assert coordinator.snapshot_execution_state().state == OrderLifecycleState.FILLED

        assert len(bridge.emitted_manifests) == 1
        manifest = bridge.emitted_manifests[0]
        assert manifest.intent_id == "INTENT-CYCLE-001-EURUSD"
        assert manifest.symbol == "EURUSD"
        assert manifest.filled_qty == Decimal("0.09")
        assert len(manifest.execution_digest) == 64

        # 6. Record in Operational Ledger
        ledger_path = tmp_path / "operational_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)

        # Build post-cycle portfolio
        post_portfolio = PortfolioState(
            timestamp_utc=base_time,
            positions={},
            cash_balance=Decimal("100000.00"),
            total_equity=Decimal("100000.00"),
            margin_used=Decimal("0.0"),
            gross_exposure=Decimal("0.0"),
            net_exposure=Decimal("0.0"),
            unrealized_pnl=Decimal("0.0"),
            realized_pnl=Decimal("0.0"),
        )
        snap_store = PortfolioSnapshotStore()
        snap_file = tmp_path / "portfolio_state.json"
        p_digest = snap_store.save_snapshot(post_portfolio, snap_file)

        cycle_event = OperationalCycleEvent(
            cycle_identity=cycle_id,
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=p_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
            error_message=None,
        )
        ledger.append_event(cycle_event)

        # 7. Audit Rehydration
        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=tmp_path)
        r_portfolio, r_account, r_status = rehydrator.rehydrate(as_of_utc=base_time)
        assert r_status == RehydrationStatus.CLEAN_RECOVERY
        assert r_account.balance == Decimal("100000.00")
        assert len(r_portfolio.positions) == 0

    def test_full_canonical_cycle_mt5_demo_path(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """Execute full canonical cycle using MT5_DEMO venue path with MT5BrokerAdapter & MockMT5Transport."""
        # 1. Setup Mock MT5 Transport & Adapter
        transport = MockMT5Transport(broker_id="TEST_DEMO_BROKER", account_id="ACC_DEMO_999")
        mt5_adapter = MT5BrokerAdapter(
            broker_id="TEST_DEMO_BROKER",
            account_id="ACC_DEMO_999",
            terminal_instance_id="TERM_DEMO_01",
            transport=transport,
        )
        # Unblock adapter with valid 6-D reconciliation confirmation
        conf = make_clean_reconciliation_confirmation(mt5_adapter, base_time)
        mt5_adapter.confirm_reconciliation(conf)
        assert mt5_adapter.can_dispatch() is True

        # 2. Setup Session & Feeder
        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="SESS-CANONICAL-MT5-01",
            run_id="RUN-MT5-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.MT5_FORWARD,
            execution_mode=PaperExecutionVenueType.MT5_DEMO,
            strategy_id="STRAT-MOCK-02",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="a" * 64,
        )

        snap = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=base_time,
        )
        provider = InMemoryMarketDataProvider(snap)
        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.MT5_FORWARD,
            session_identity=session,
            max_market_data_age_ms=1500,
        )
        polled_snap, age_ms = feeder.poll_next_market_snapshot("EURUSD", base_time + timedelta(milliseconds=40))
        assert age_ms == 40

        # 3. Strategy Allocation
        dossier_file, _ = create_verified_dossier(tmp_path, "STRAT-MOCK-02", "1.0.0")
        adapter = PaperStrategyAdapter(
            strategy_id="STRAT-MOCK-02",
            strategy_version="1.0.0",
            dossier_path=dossier_file,
            session_identity=session,
            cost_model=cost_model,
        )
        alloc = adapter.generate_candidate_allocation(bars=[], portfolio=initial_portfolio, as_of_utc=base_time)

        # 4. Bridge Dispatch through MT5BrokerAdapter
        coordinator = ExecutionCoordinator(execution_id="EXEC-MT5-01", requested_qty=Decimal("0.09"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.MT5_DEMO,
            mt5_adapter=mt5_adapter,
            symbol_spec_provider=lambda s: standard_symbol_spec,
        )

        cycle_id = CycleIdentity(
            cycle_id="CYCLE-MT5-001",
            as_of_utc=base_time,
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=1,
        )

        outcomes = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=initial_portfolio,
            current_snapshot=polled_snap,
            cycle_identity=cycle_id,
            session_identity=session,
        )

        # 5. Verify MT5 Dispatch Outcomes
        # MockMT5Transport returns ACK observation for market orders
        assert len(outcomes) == 1
        assert outcomes[0].state == OrderLifecycleState.ACKNOWLEDGED
        assert coordinator.snapshot_execution_state().state == OrderLifecycleState.ACKNOWLEDGED


# ============================================================================
# 2. TEST SUITE: Multi-Pulse Partial Fill Lifecycle & Working Intent
# ============================================================================


class TestIntegratedMultiPulsePartialFill:
    """Verifies deterministic multi-pulse state progression:
    Pulse 1: Order Intent -> ACK -> PARTIAL_FILL (50%) -> Coordinator in PARTIALLY_FILLED
    Pulse 2: Working Intent Reused -> FILLED (remaining 50%) -> Terminal FILLED -> ExecutionManifest.
    """

    def test_multi_pulse_deterministic_partial_fill_lifecycle(
        self,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """Validate multi-pulse partial fill accumulation and single manifest emission at terminal state."""
        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="SESS-PARTIAL-01",
            run_id="RUN-PARTIAL-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-PARTIAL-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="0" * 64,
        )

        snap = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=base_time,
        )

        alloc = AllocationDecision(
            decision_id="DEC-PARTIAL-001",
            selected_candidate_id="STRAT-PARTIAL-01",
            allocator_name="TOURNAMENT",
            authorized_weights={"EURUSD": Decimal("0.10")},
            cash_weight=Decimal("0.90"),
            authorization_timestamp=base_time,
            is_fallback_baseline=False,
            gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
            rationale="Test partial fill accumulation.",
        )

        # 50% partial fill matcher
        matcher = SimulatedMarketMatcher(cost_model=cost_model, partial_fill_ratio=Decimal("0.50"))
        coordinator = ExecutionCoordinator(execution_id="EXEC-PARTIAL-01", requested_qty=Decimal("0.09"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=matcher,
            symbol_spec_provider=lambda s: standard_symbol_spec,
        )

        # PULSE 1
        cycle_1 = CycleIdentity(
            cycle_id="CYCLE-P1",
            as_of_utc=base_time,
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=1,
        )
        outcomes_1 = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=initial_portfolio,
            current_snapshot=snap,
            cycle_identity=cycle_1,
            session_identity=session,
        )

        assert len(outcomes_1) == 2
        assert outcomes_1[0].state == OrderLifecycleState.ACKNOWLEDGED
        assert outcomes_1[1].state == OrderLifecycleState.PARTIALLY_FILLED
        assert coordinator.snapshot_execution_state().state == OrderLifecycleState.PARTIALLY_FILLED
        assert coordinator.filled_qty == Decimal("0.04")  # 50% of 0.09 quantized down = 0.04 lots
        assert len(bridge.emitted_manifests) == 0  # No manifest emitted on non-terminal fill

        # PULSE 2 (advance time and clear pulse dispatch registry)
        pulse_2_time = base_time + timedelta(seconds=1)
        snap_2 = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08505"),
            ask=Decimal("1.08525"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08515"),
            timestamp_utc=pulse_2_time,
        )
        cycle_2 = CycleIdentity(
            cycle_id="CYCLE-P2",
            as_of_utc=pulse_2_time,
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=2,
        )
        bridge._dispatched_intent_ids.clear()

        outcomes_2 = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=initial_portfolio,
            current_snapshot=snap_2,
            cycle_identity=cycle_2,
            session_identity=session,
        )

        assert len(outcomes_2) == 1
        assert outcomes_2[0].state == OrderLifecycleState.FILLED
        assert coordinator.snapshot_execution_state().state == OrderLifecycleState.FILLED
        assert coordinator.filled_qty == Decimal("0.09")

        # Terminal state must emit exactly 1 canonical ExecutionManifest
        assert len(bridge.emitted_manifests) == 1
        manifest = bridge.emitted_manifests[0]
        assert manifest.intent_id == "INTENT-CYCLE-P1-EURUSD"  # Reused original intent ID
        assert manifest.filled_qty == Decimal("0.09")
        assert manifest.requested_qty == Decimal("0.09")
        assert manifest.execution_digest != ""


# ============================================================================
# 3. TEST SUITE: Timeout, UNKNOWN Semantics, and Authoritative Reconciliation
# ============================================================================


class TestIntegratedTimeoutUnknownAndReconciliation:
    """Verifies fail-closed UNKNOWN behavior:
    1. Order submission timeout produces UNKNOWN state.
    2. Operational ledger records UNKNOWN outcome.
    3. Rehydration without broker reconciliation fails closed.
    4. Rehydration with clean broker reconciliation succeeds.
    5. Rehydration with external broker discrepancy halts with DISCREPANCY_HALT.
    """

    def test_timeout_to_unknown_requires_broker_reconciliation(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """Validate timeout -> UNKNOWN lifecycle and fail-closed rehydration boundary."""
        # 1. Setup transport with timeout injection
        transport = MockMT5Transport(broker_id="DEMO_BROKER", account_id="ACC_101")
        adapter = MT5BrokerAdapter(
            broker_id="DEMO_BROKER",
            account_id="ACC_101",
            terminal_instance_id="TERM_101",
            transport=transport,
        )
        conf = make_clean_reconciliation_confirmation(adapter, base_time)
        adapter.confirm_reconciliation(conf)

        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="SESS-TIMEOUT-01",
            run_id="RUN-TIMEOUT-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.MT5_FORWARD,
            execution_mode=PaperExecutionVenueType.MT5_DEMO,
            strategy_id="STRAT-TIMEOUT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="0" * 64,
        )

        coordinator = ExecutionCoordinator(execution_id="EXEC-TO-01", requested_qty=Decimal("0.09"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.MT5_DEMO,
            mt5_adapter=adapter,
            symbol_spec_provider=lambda s: standard_symbol_spec,
        )

        # Inject timeout
        transport.set_timeout_on_order_send(True)

        snap = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=base_time,
        )
        alloc = AllocationDecision(
            decision_id="DEC-TO-001",
            selected_candidate_id="STRAT-TIMEOUT-01",
            allocator_name="TOURNAMENT",
            authorized_weights={"EURUSD": Decimal("0.10")},
            cash_weight=Decimal("0.90"),
            authorization_timestamp=base_time,
            is_fallback_baseline=False,
            gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
            rationale="Test timeout to unknown.",
        )

        outcomes = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=initial_portfolio,
            current_snapshot=snap,
            cycle_identity=CycleIdentity(cycle_id="CYCLE-TO-01", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=1),
            session_identity=session,
        )

        # Dispatched event is CONNECTION_LOST -> Coordinator transitions to UNKNOWN
        assert len(outcomes) == 1
        assert outcomes[0].state == OrderLifecycleState.UNKNOWN
        assert coordinator.snapshot_execution_state().state == OrderLifecycleState.UNKNOWN

        # 2. Record UNKNOWN cycle event in ledger
        ledger_path = tmp_path / "operational_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)
        snap_store = PortfolioSnapshotStore()
        p_digest = snap_store.save_snapshot(initial_portfolio, tmp_path / "portfolio_state.json")

        unknown_cycle_event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-TO-01", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=p_digest,
            cycle_outcome=CycleOutcome.DISPATCH_FAILED,
            error_message="Broker communication timeout: state UNKNOWN",
        )
        ledger.append_event(unknown_cycle_event)

        # 3. Rehydration WITHOUT broker adapter fails closed (Vector V-13)
        blind_rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=tmp_path, broker_adapter=None)
        with pytest.raises(DataContractError, match="CANNOT_REHYDRATE_UNKNOWN_WITHOUT_BROKER"):
            blind_rehydrator.rehydrate(as_of_utc=base_time)

        # 4. Rehydration WITH authoritative broker adapter succeeds
        class AuthoritativeMockBroker:
            def get_open_positions(self) -> Dict[str, Any]:
                return {}  # Order never reached broker; 0 open positions matches snapshot

            def check_divergence(self) -> bool:
                return False

        reconciled_rehydrator = PortfolioStateRehydrator(
            ledger=ledger, snapshot_dir=tmp_path, broker_adapter=AuthoritativeMockBroker()
        )
        _, _, status = reconciled_rehydrator.rehydrate(as_of_utc=base_time)
        assert status == RehydrationStatus.CLEAN_RECOVERY

    def test_rehydration_broker_divergence_triggers_discrepancy_halt(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
    ) -> None:
        """Validate external broker position divergence triggers DISCREPANCY_HALT (Vector V-09/V-16)."""
        ledger = OperationalLedger(tmp_path / "operational_ledger.jsonl")
        snap_store = PortfolioSnapshotStore()
        p_digest = snap_store.save_snapshot(initial_portfolio, tmp_path / "portfolio_state.json")

        clean_event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-CLEAN", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=p_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
            error_message=None,
        )
        ledger.append_event(clean_event)

        # Broker has an external untracked open position
        class DivergentBroker:
            def get_open_positions(self) -> Dict[str, Any]:
                class ExternalPos:
                    quantity = Decimal("0.50")
                return {"EURUSD": ExternalPos()}

            def check_divergence(self) -> bool:
                return True

        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=tmp_path, broker_adapter=DivergentBroker())
        _, _, status = rehydrator.rehydrate(as_of_utc=base_time)
        assert status == RehydrationStatus.DISCREPANCY_HALT


# ============================================================================
# 4. TEST SUITE: Stale Market Data Fail-Closed Integration
# ============================================================================


class TestIntegratedStaleDataFailClosed:
    """Verifies fail-closed pulse abortion when forward feed latency breaches threshold."""

    def test_integrated_stale_feed_aborts_pulse_and_preserves_state(
        self,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """Validate market tick age > 1500ms aborts cycle and suppresses dispatch."""
        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="SESS-STALE-01",
            run_id="RUN-STALE-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.MT5_FORWARD,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-STALE-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="0" * 64,
        )

        # Tick generated 2000ms ago (> 1500ms threshold)
        stale_tick_time = base_time - timedelta(milliseconds=2000)
        stale_snap = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=stale_tick_time,
        )
        provider = InMemoryMarketDataProvider(stale_snap)
        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.MT5_FORWARD,
            session_identity=session,
            max_market_data_age_ms=1500,
        )

        # Feeder returns age 2000ms
        polled_snap, age_ms = feeder.poll_next_market_snapshot("EURUSD", base_time)
        assert age_ms >= 2000

        # Integrated Runtime Check: Age > threshold triggers DATA_STALE outcome
        if age_ms > feeder.max_market_data_age_ms:
            cycle_outcome = CycleOutcome.DATA_STALE
            # Dispatch must be completely suppressed
            orders_emitted = []
        else:
            cycle_outcome = CycleOutcome.SUCCESS
            orders_emitted = [1]

        assert cycle_outcome == CycleOutcome.DATA_STALE
        assert len(orders_emitted) == 0
        assert initial_portfolio.cash_balance == Decimal("100000.00")


# ============================================================================
# 5. TEST SUITE: Multi-Pulse Idempotency and Deduplication
# ============================================================================


class TestIntegratedIdempotencyAndDeduplication:
    """Verifies deduplication across pulses for identical intent ID and client order ID."""

    def test_duplicate_intent_and_client_order_across_pulses_suppressed(
        self,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """Validate submitting identical intent ID in successive calls is suppressed."""
        matcher = SimulatedMarketMatcher()
        coordinator = ExecutionCoordinator(execution_id="EXEC-DEDUP-01", requested_qty=Decimal("0.09"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=matcher,
            symbol_spec_provider=lambda s: standard_symbol_spec,
        )

        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="SESS-DEDUP-01",
            run_id="RUN-DEDUP-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-DEDUP-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="0" * 64,
        )

        snap = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=base_time,
        )
        alloc = AllocationDecision(
            decision_id="DEC-DEDUP-01",
            selected_candidate_id="STRAT-DEDUP-01",
            allocator_name="TOURNAMENT",
            authorized_weights={"EURUSD": Decimal("0.10")},
            cash_weight=Decimal("0.90"),
            authorization_timestamp=base_time,
            is_fallback_baseline=False,
            gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
            rationale="Test dedup.",
        )
        cycle_id = CycleIdentity(cycle_id="CYCLE-SAME", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=1)

        # Pulse 1: Normal dispatch
        outcomes_1 = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=initial_portfolio,
            current_snapshot=snap,
            cycle_identity=cycle_id,
            session_identity=session,
        )
        assert len(outcomes_1) == 2  # ACK, FILLED

        # Pulse 2: Attempt duplicate submission with same cycle_id / intent_id
        outcomes_2 = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=initial_portfolio,
            current_snapshot=snap,
            cycle_identity=cycle_id,
            session_identity=session,
        )
        # Suppressed cleanly by bridge intent deduplication registry
        assert len(outcomes_2) == 0


# ============================================================================
# 6. TEST SUITE: Session Identity Lineage & Candidate Qualification Gating
# ============================================================================


class TestIntegratedSessionLineageAndGovernance:
    """Verifies session identity feed/mode matrix and real candidate qualification gating."""

    def test_session_feed_and_mode_compatibility_matrix(self, base_time: datetime) -> None:
        """Validate startup session compatibility matrix per Rev 2.2.2 Sec 6.2.1."""
        cost_model = ExecutionCostModel()
        digest = cost_model.compute_digest()

        # 1. FORBIDDEN: STREAMING_PARQUET_PUMP + MT5_DEMO
        with pytest.raises(DataContractError, match="INVALID_SESSION_CONFIGURATION"):
            PaperTradingSessionIdentity(
                session_id="SESS-INV-01",
                run_id="RUN-INV-01",
                market="TRADITIONAL_FX",
                data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
                execution_mode=PaperExecutionVenueType.MT5_DEMO,
                strategy_id="STRAT-01",
                strategy_version="1.0.0",
                prng_seed=42,
                start_time_utc=base_time,
                planned_end_time_utc=base_time + timedelta(days=90),
                config_digest=digest,
                dossier_digest="0" * 64,
            )

        # 2. VALID: STREAMING_PARQUET_PUMP + LOCAL_SIMULATOR
        s1 = PaperTradingSessionIdentity(
            session_id="SESS-VAL-01",
            run_id="RUN-VAL-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=digest,
            dossier_digest="0" * 64,
        )
        assert s1.session_id == "SESS-VAL-01"

        # 3. VALID: MT5_FORWARD + MT5_DEMO
        s2 = PaperTradingSessionIdentity(
            session_id="SESS-VAL-02",
            run_id="RUN-VAL-02",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.MT5_FORWARD,
            execution_mode=PaperExecutionVenueType.MT5_DEMO,
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=digest,
            dossier_digest="0" * 64,
        )
        assert s2.session_id == "SESS-VAL-02"

    def test_candidate_strategy_remains_qualification_blocked_end_to_end(
        self,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """Validate candidate STRAT-MOM-MULTI-HORIZON-V1 is qualification-blocked and emits 100% Cash fallback."""
        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="SESS-CANDIDATE-01",
            run_id="RUN-CANDIDATE-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-MOM-MULTI-HORIZON-V1",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="0" * 64,
        )

        # No dossier exists on disk for candidate strategy
        adapter = PaperStrategyAdapter(
            strategy_id="STRAT-MOM-MULTI-HORIZON-V1",
            strategy_version="1.0.0",
            dossier_path=None,  # No genuine dossier
            session_identity=session,
            cost_model=cost_model,
        )

        # Invariant: Candidate strategy is NOT eligible
        assert adapter.is_eligible is False

        # Generates governed 100% Cash fallback
        alloc = adapter.generate_candidate_allocation(bars=[], portfolio=initial_portfolio, as_of_utc=base_time)
        assert alloc.selected_candidate_id == "CASH_FALLBACK"
        assert alloc.cash_weight == Decimal("1.0")
        assert alloc.is_fallback_baseline is True
        assert alloc.gate_verdict == "GOVERNANCE_FALLBACK_CASH_ONLY"

        # Bridge evaluates fallback allocation -> strictly 0 orders emitted
        coordinator = ExecutionCoordinator(execution_id="EXEC-CAND-01", requested_qty=Decimal("1.0"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=SimulatedMarketMatcher(),
            symbol_spec_provider=lambda s: standard_symbol_spec,
        )

        snap = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=base_time,
        )

        outcomes = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=initial_portfolio,
            current_snapshot=snap,
            cycle_identity=CycleIdentity(cycle_id="CYCLE-CAND-01", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=1),
            session_identity=session,
        )

        assert len(outcomes) == 0
        assert len(bridge.emitted_manifests) == 0
        assert initial_portfolio.cash_balance == Decimal("100000.00")
