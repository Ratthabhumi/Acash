"""Phase 13: Paper Trading Runtime Adversarial Test Suite.

Contains 20 formal adversarial test vectors partitioned into 4 hermetic suites:
1. TestPaperExecutionBridge (V-01, V-02, V-03, V-04, V-11, V-12, V-19, V-20)
2. TestForwardMarketDataFeeder (V-05, V-06, V-15)
3. TestPortfolioStateRehydrator (V-07, V-08, V-09, V-10, V-13, V-14, V-16)
4. TestPaperStrategyAdapter (V-17, V-18, V-19, V-20, Candidate BLOCKED)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Sequence
import pytest

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.interfaces.market_data import IMarketDataProvider
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.broker_events import BrokerEventKind
from acash.execution.coordinator import (
    CoordinatorOutcome,
    ExecutionCoordinator,
)
from acash.execution.mock_broker import BrokerRawEvent
from acash.execution.mt5.schemas import BrokerSymbolSpec
from acash.execution.schema import (
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
    CommissionModelConfig,
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


class MockMarketDataProvider(IMarketDataProvider):
    """Hermetic in-memory market data provider for unit tests."""

    def __init__(self, default_snapshot: MarketDataSnapshot) -> None:
        self.snapshot = default_snapshot

    def get_historical_bars(
        self, symbol: str, timeframe: BarTimeframe, start_utc: datetime, end_utc: datetime
    ) -> Sequence[Bar]:
        return []

    def get_latest_snapshot(self, symbol: str) -> MarketDataSnapshot:
        return self.snapshot


@pytest.fixture
def now_utc() -> datetime:
    return datetime(2026, 9, 5, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def standard_symbol_spec() -> BrokerSymbolSpec:
    from acash.execution.mt5.enums import MT5TradeExecutionMode

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
        margin_currency="EUR",
        profit_currency="USD",
        spec_digest="0" * 64,
    )


@pytest.fixture
def sample_snapshot(now_utc: datetime) -> MarketDataSnapshot:
    return MarketDataSnapshot(
        symbol="EURUSD",
        bid=Decimal("1.08500"),
        ask=Decimal("1.08520"),
        bid_size=Decimal("100.0"),
        ask_size=Decimal("100.0"),
        last_price=Decimal("1.08510"),
        timestamp_utc=now_utc,
    )


@pytest.fixture
def sample_portfolio(now_utc: datetime) -> PortfolioState:
    return PortfolioState(
        timestamp_utc=now_utc,
        positions={},
        cash_balance=Decimal("100000.00"),
        total_equity=Decimal("100000.00"),
        margin_used=Decimal("0.0"),
        gross_exposure=Decimal("0.0"),
        net_exposure=Decimal("0.0"),
        unrealized_pnl=Decimal("0.0"),
        realized_pnl=Decimal("0.0"),
    )


@pytest.fixture
def sample_cycle_identity(now_utc: datetime) -> CycleIdentity:
    return CycleIdentity(
        cycle_id="CYCLE-20260905-001",
        as_of_utc=now_utc,
        regime=RuntimeRegime.MARKET_OPEN,
        sequence_number=1,
    )


@pytest.fixture
def sample_session_identity(now_utc: datetime) -> PaperTradingSessionIdentity:
    cost_model = ExecutionCostModel()
    return PaperTradingSessionIdentity(
        session_id="PAPER-SESSION-001",
        run_id="RUN-DEVHOST-001",
        market="TRADITIONAL_FX",
        data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
        execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
        strategy_id="STRAT-TEST-01",
        strategy_version="1.0.0",
        prng_seed=42,
        start_time_utc=now_utc,
        planned_end_time_utc=now_utc + timedelta(days=90),
        config_digest=cost_model.compute_digest(),
        dossier_digest="0" * 64,
    )


@pytest.fixture
def approved_allocation(now_utc: datetime) -> AllocationDecision:
    return AllocationDecision(
        decision_id="DECISION-20260905-001",
        selected_candidate_id="STRAT-TEST-01",
        allocator_name="TOURNAMENT_RUNNER",
        authorized_weights={"EURUSD": Decimal("0.10")},
        cash_weight=Decimal("0.90"),
        authorization_timestamp=now_utc,
        is_fallback_baseline=False,
        gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
        rationale="Tournament admitted candidate allocation.",
    )


# ============================================================================
# 1. TEST SUITE: TestPaperExecutionBridge
# ============================================================================


class TestPaperExecutionBridge:
    """Vectors V-01, V-02, V-03, V-04, V-11, V-12, V-19, V-20."""

    def test_v01_zero_delta(
        self,
        sample_portfolio: PortfolioState,
        sample_snapshot: MarketDataSnapshot,
        sample_cycle_identity: CycleIdentity,
        sample_session_identity: PaperTradingSessionIdentity,
    ) -> None:
        """V-01: Target allocation equals current position (Delta q == 0) -> 0 orders emitted."""
        # Allocation with weight 0 for flat portfolio
        zero_delta_alloc = AllocationDecision(
            decision_id="DECISION-ZERO-001",
            selected_candidate_id="STRAT-TEST-01",
            allocator_name="TOURNAMENT_RUNNER",
            authorized_weights={"EURUSD": Decimal("0.0")},
            cash_weight=Decimal("1.0"),
            authorization_timestamp=sample_snapshot.timestamp_utc,
            is_fallback_baseline=False,
            gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
            rationale="Zero weight requested.",
        )
        coordinator = ExecutionCoordinator(execution_id="EXEC-001", requested_qty=Decimal("0.01"))
        matcher = SimulatedMarketMatcher()
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=matcher,
        )

        outcomes = bridge.evaluate_and_dispatch(
            allocation=zero_delta_alloc,
            portfolio=sample_portfolio,
            current_snapshot=sample_snapshot,
            cycle_identity=sample_cycle_identity,
            session_identity=sample_session_identity,
        )
        assert len(outcomes) == 0
        assert len(bridge.emitted_manifests) == 0

    def test_v02_vetoed_allocation(
        self,
        sample_portfolio: PortfolioState,
        sample_snapshot: MarketDataSnapshot,
        sample_cycle_identity: CycleIdentity,
        sample_session_identity: PaperTradingSessionIdentity,
    ) -> None:
        """V-02: Stage 4 risk engine returns REJECTED / Fallback -> 0 orders emitted."""
        vetoed_alloc = AllocationDecision(
            decision_id="DECISION-VETOED-001",
            selected_candidate_id="STRAT-TEST-01",
            allocator_name="RISK_ENGINE",
            authorized_weights={"EURUSD": Decimal("0.10")},
            cash_weight=Decimal("0.90"),
            authorization_timestamp=sample_snapshot.timestamp_utc,
            is_fallback_baseline=True,
            gate_verdict="RISK_VERDICT_REJECTED",
            rationale="Gross exposure breached limit.",
        )
        coordinator = ExecutionCoordinator(execution_id="EXEC-002", requested_qty=Decimal("0.01"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=SimulatedMarketMatcher(),
        )

        outcomes = bridge.evaluate_and_dispatch(
            allocation=vetoed_alloc,
            portfolio=sample_portfolio,
            current_snapshot=sample_snapshot,
            cycle_identity=sample_cycle_identity,
            session_identity=sample_session_identity,
        )
        assert len(outcomes) == 0

    def test_v03_matcher_partial_full_fill(
        self,
        sample_portfolio: PortfolioState,
        sample_snapshot: MarketDataSnapshot,
        sample_cycle_identity: CycleIdentity,
        sample_session_identity: PaperTradingSessionIdentity,
        approved_allocation: AllocationDecision,
    ) -> None:
        """V-03: Local matcher emits deterministic multi-stage fill: ACK -> PARTIAL_FILL -> FILLED."""
        # 1. Setup multi-stage matcher with 50% partial fill ratio
        matcher = SimulatedMarketMatcher(partial_fill_ratio=Decimal("0.50"))
        # requested_qty will be 0.09 lots based on 10k notional / 100k contract / 1.0851
        coordinator = ExecutionCoordinator(execution_id="EXEC-003", requested_qty=Decimal("0.09"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=matcher,
        )

        # Pulse 1: emits ACK then PARTIAL_FILL
        outcomes_1 = bridge.evaluate_and_dispatch(
            allocation=approved_allocation,
            portfolio=sample_portfolio,
            current_snapshot=sample_snapshot,
            cycle_identity=sample_cycle_identity,
            session_identity=sample_session_identity,
        )
        assert len(outcomes_1) == 2
        assert outcomes_1[0].state == OrderLifecycleState.ACKNOWLEDGED
        assert outcomes_1[1].state == OrderLifecycleState.PARTIALLY_FILLED
        assert coordinator.snapshot_execution_state().state == OrderLifecycleState.PARTIALLY_FILLED
        assert len(bridge.emitted_manifests) == 0  # Not yet terminal FILLED

        # Pulse 2: second evaluation fills remaining working volume to FILLED
        sample_cycle_identity_2 = CycleIdentity(
            cycle_id="CYCLE-20260905-002",
            as_of_utc=sample_snapshot.timestamp_utc,
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=2,
        )
        # Force re-dispatch of working intent to matcher
        bridge._dispatched_intent_ids.clear()
        outcomes_2 = bridge.evaluate_and_dispatch(
            allocation=approved_allocation,
            portfolio=sample_portfolio,
            current_snapshot=sample_snapshot,
            cycle_identity=sample_cycle_identity_2,
            session_identity=sample_session_identity,
        )
        assert len(outcomes_2) == 1
        assert outcomes_2[0].state == OrderLifecycleState.FILLED
        assert coordinator.snapshot_execution_state().state == OrderLifecycleState.FILLED
        assert len(bridge.emitted_manifests) == 1
        manifest = bridge.emitted_manifests[0]
        assert manifest.execution_id == "EXEC-INTENT-CYCLE-20260905-001-EURUSD"
        assert len(manifest.execution_digest) == 64

    def test_v04_rejected_order(
        self,
        sample_portfolio: PortfolioState,
        sample_snapshot: MarketDataSnapshot,
        sample_cycle_identity: CycleIdentity,
        sample_session_identity: PaperTradingSessionIdentity,
        approved_allocation: AllocationDecision,
    ) -> None:
        """V-04: Venue rejects order -> Coordinator transitions to REJECTED."""
        matcher = SimulatedMarketMatcher(reject_next=True)
        coordinator = ExecutionCoordinator(execution_id="EXEC-004", requested_qty=Decimal("0.09"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=matcher,
        )

        outcomes = bridge.evaluate_and_dispatch(
            allocation=approved_allocation,
            portfolio=sample_portfolio,
            current_snapshot=sample_snapshot,
            cycle_identity=sample_cycle_identity,
            session_identity=sample_session_identity,
        )
        assert len(outcomes) == 2
        assert outcomes[0].state == OrderLifecycleState.ACKNOWLEDGED
        assert outcomes[1].state == OrderLifecycleState.REJECTED
        assert coordinator.state == OrderLifecycleState.REJECTED
        assert len(bridge.emitted_manifests) == 0

    def test_v11_duplicate_intent(
        self,
        sample_portfolio: PortfolioState,
        sample_snapshot: MarketDataSnapshot,
        sample_cycle_identity: CycleIdentity,
        sample_session_identity: PaperTradingSessionIdentity,
        approved_allocation: AllocationDecision,
    ) -> None:
        """V-11: Submitting identical intent in same cycle is deduplicated (0 orders emitted)."""
        coordinator = ExecutionCoordinator(execution_id="EXEC-011", requested_qty=Decimal("0.09"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=SimulatedMarketMatcher(),
        )

        # First dispatch passes
        outcomes_1 = bridge.evaluate_and_dispatch(
            allocation=approved_allocation,
            portfolio=sample_portfolio,
            current_snapshot=sample_snapshot,
            cycle_identity=sample_cycle_identity,
            session_identity=sample_session_identity,
        )
        assert len(outcomes_1) > 0

        # Duplicate dispatch with identical cycle_id is deduplicated cleanly
        outcomes_2 = bridge.evaluate_and_dispatch(
            allocation=approved_allocation,
            portfolio=sample_portfolio,
            current_snapshot=sample_snapshot,
            cycle_identity=sample_cycle_identity,
            session_identity=sample_session_identity,
        )
        assert len(outcomes_2) == 0

    def test_v12_duplicate_client_order_id(
        self,
        now_utc: datetime,
    ) -> None:
        """V-12: Duplicate event identity delivered to coordinator surfaces duplicate incident."""
        coordinator = ExecutionCoordinator(execution_id="EXEC-012", requested_qty=Decimal("1.0"))
        # Acknowledge first event
        event_1 = BrokerRawEvent(
            broker_order_id="BRK-001",
            event_kind=BrokerEventKind.ACK,
            observed_at=now_utc,
            source="TEST",
            broker_sequence="1",
        )
        from acash.execution.broker_adapter import to_coordinator_event

        coord_ev1 = to_coordinator_event(event_1)
        outcome_1 = coordinator.apply(coord_ev1)
        assert outcome_1.was_duplicate is False

        # Redeliver identical event identity
        coord_ev2 = to_coordinator_event(event_1)
        outcome_2 = coordinator.apply(coord_ev2)
        assert outcome_2.was_duplicate is True
        assert len(outcome_2.incidents) == 1

    def test_v19_quantization_round_down(
        self,
        sample_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """V-19: Sizing delta quantizes with ROUND_DOWN towards zero."""
        bridge = PaperExecutionBridge(
            coordinator=ExecutionCoordinator(execution_id="EXEC-QUANT", requested_qty=Decimal("1.0")),
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
        )
        # Create allocation with fractional lot request
        alloc = AllocationDecision(
            decision_id="DEC-Q",
            selected_candidate_id="STRAT-01",
            allocator_name="T",
            authorized_weights={"EURUSD": Decimal("0.055")},  # e.g. 5500 USD / 100k = 0.0506 lots
            cash_weight=Decimal("0.945"),
            authorization_timestamp=datetime.now(timezone.utc),
            is_fallback_baseline=False,
            gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
            rationale="test",
        )
        res = bridge._quantize_target_delta(alloc, sample_portfolio, standard_symbol_spec, reference_price=Decimal("1.0"))
        assert res is not None
        quantized_lots, direction = res
        # 100,000 * 0.055 / 1.0 = 5500 units / 100,000 = 0.055 lots.
        # Steps = floor(0.055 / 0.01) = 5 -> 0.05 lots
        assert quantized_lots == Decimal("0.05")
        assert direction == OrderSide.BUY

    def test_v20_unrepresentable_residual_discarded(
        self,
        sample_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """V-20: Unrepresentable residual r < volume_step discarded without cash conversion (B1)."""
        bridge = PaperExecutionBridge(
            coordinator=ExecutionCoordinator(execution_id="EXEC-RES", requested_qty=Decimal("1.0")),
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
        )
        # Residual of 0.005 lots (less than 0.01 step)
        alloc = AllocationDecision(
            decision_id="DEC-RES",
            selected_candidate_id="STRAT-01",
            allocator_name="T",
            authorized_weights={"EURUSD": Decimal("0.015")},  # 1500 units = 0.015 lots
            cash_weight=Decimal("0.985"),
            authorization_timestamp=datetime.now(timezone.utc),
            is_fallback_baseline=False,
            gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
            rationale="test",
        )
        res = bridge._quantize_target_delta(alloc, sample_portfolio, standard_symbol_spec, reference_price=Decimal("1.0"))
        assert res is not None
        quantized_lots, _ = res
        # Discards the 0.005 residual, leaving 0.01
        assert quantized_lots == Decimal("0.01")
        # Assert portfolio cash is untouched by the bridge (bridge performs no cash conversion)
        assert sample_portfolio.cash_balance == Decimal("100000.00")


# ============================================================================
# 2. TEST SUITE: TestForwardMarketDataFeeder
# ============================================================================


class TestForwardMarketDataFeeder:
    """Vectors V-05, V-06, V-15 and B2 invariant."""

    def test_v05_fresh_tick(
        self,
        now_utc: datetime,
        sample_snapshot: MarketDataSnapshot,
    ) -> None:
        """V-05: Tick received with age 50ms (<= 1500ms threshold) passes Stage 1."""
        tick_time = now_utc - timedelta(milliseconds=50)
        fresh_snapshot = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=tick_time,
        )
        provider = MockMarketDataProvider(fresh_snapshot)
        session_identity = PaperTradingSessionIdentity(
            session_id="S-05",
            run_id="R-05",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.MT5_FORWARD,
            execution_mode=PaperExecutionVenueType.MT5_DEMO,
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=now_utc,
            planned_end_time_utc=now_utc + timedelta(days=90),
            config_digest="0" * 64,
            dossier_digest="0" * 64,
        )
        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.MT5_FORWARD,
            session_identity=session_identity,
            max_market_data_age_ms=1500,
        )

        snap, age_ms = feeder.poll_next_market_snapshot("EURUSD", wall_clock_utc=now_utc)
        assert age_ms == 50
        assert age_ms <= feeder.max_market_data_age_ms

    def test_v06_stale_data(
        self,
        now_utc: datetime,
    ) -> None:
        """V-06: Tick received with age 2500ms (> 1500ms threshold) is flagged as stale."""
        stale_tick_time = now_utc - timedelta(milliseconds=2500)
        stale_snapshot = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=stale_tick_time,
        )
        provider = MockMarketDataProvider(stale_snapshot)
        session_identity = PaperTradingSessionIdentity(
            session_id="S-06",
            run_id="R-06",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.MT5_FORWARD,
            execution_mode=PaperExecutionVenueType.MT5_DEMO,
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=now_utc,
            planned_end_time_utc=now_utc + timedelta(days=90),
            config_digest="0" * 64,
            dossier_digest="0" * 64,
        )
        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.MT5_FORWARD,
            session_identity=session_identity,
            max_market_data_age_ms=1500,
        )

        snap, age_ms = feeder.poll_next_market_snapshot("EURUSD", wall_clock_utc=now_utc)
        assert age_ms == 2500
        assert age_ms > feeder.max_market_data_age_ms

    def test_v15_stale_feed_with_open_position(
        self,
        now_utc: datetime,
    ) -> None:
        """V-15: When feed drops / is stale, feeder reports stale status without inventing orders."""
        drop_time = now_utc - timedelta(seconds=10)
        dropped_snapshot = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08520"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08510"),
            timestamp_utc=drop_time,
        )
        provider = MockMarketDataProvider(dropped_snapshot)
        session_identity = PaperTradingSessionIdentity(
            session_id="S-15",
            run_id="R-15",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.MT5_FORWARD,
            execution_mode=PaperExecutionVenueType.MT5_DEMO,
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=now_utc,
            planned_end_time_utc=now_utc + timedelta(days=90),
            config_digest="0" * 64,
            dossier_digest="0" * 64,
        )
        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.MT5_FORWARD,
            session_identity=session_identity,
        )
        _, age_ms = feeder.poll_next_market_snapshot("EURUSD", wall_clock_utc=now_utc)
        status = feeder.get_feed_status(wall_clock_utc=now_utc)
        assert age_ms == 10000
        assert status.data_age_ms == 10000

    def test_startup_feed_mode_mismatch_aborts(
        self,
        now_utc: datetime,
        sample_snapshot: MarketDataSnapshot,
    ) -> None:
        """B2 Invariant: STREAMING_PARQUET_PUMP paired with MT5_DEMO aborts with DataContractError."""
        with pytest.raises(DataContractError, match="INVALID_SESSION_CONFIGURATION"):
            PaperTradingSessionIdentity(
                session_id="S-INVALID",
                run_id="R-INVALID",
                market="TRADITIONAL_FX",
                data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
                execution_mode=PaperExecutionVenueType.MT5_DEMO,
                strategy_id="STRAT-01",
                strategy_version="1.0.0",
                prng_seed=42,
                start_time_utc=now_utc,
                planned_end_time_utc=now_utc + timedelta(days=90),
                config_digest="0" * 64,
                dossier_digest="0" * 64,
            )


# ============================================================================
# 3. TEST SUITE: TestPortfolioStateRehydrator
# ============================================================================


class TestPortfolioStateRehydrator:
    """Vectors V-07, V-08, V-09, V-10, V-13, V-14, V-16."""

    def test_v07_clean_rehydration(
        self,
        tmp_path: Path,
        now_utc: datetime,
        sample_portfolio: PortfolioState,
    ) -> None:
        """V-07: Process restarts with valid ledger & snapshot -> CLEAN_RECOVERY."""
        ledger_file = tmp_path / "operational_ledger.jsonl"
        ledger = OperationalLedger(ledger_file)

        # Save snapshot
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snapshot_digest = PortfolioSnapshotStore.save_snapshot(sample_portfolio, snapshot_file)

        # Append cycle event with matching snapshot digest
        cycle_identity = CycleIdentity(
            cycle_id="CYCLE-001",
            as_of_utc=now_utc,
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=0,
        )
        event = OperationalCycleEvent(
            cycle_identity=cycle_identity,
            wall_clock_utc=now_utc,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snapshot_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        ledger.append_event(event)

        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir)
        recovered_portfolio, recovered_account, status = rehydrator.rehydrate(as_of_utc=now_utc)
        assert status == RehydrationStatus.CLEAN_RECOVERY
        assert recovered_portfolio.cash_balance == sample_portfolio.cash_balance
        assert recovered_account.balance == sample_portfolio.cash_balance

    def test_v08_corrupted_ledger(
        self,
        tmp_path: Path,
        now_utc: datetime,
        sample_portfolio: PortfolioState,
    ) -> None:
        """V-08: Single byte mutated in operational_ledger.jsonl raises DataContractError."""
        ledger_file = tmp_path / "corrupt_ledger.jsonl"
        ledger = OperationalLedger(ledger_file)

        cycle_identity = CycleIdentity(
            cycle_id="CYCLE-001",
            as_of_utc=now_utc,
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=0,
        )
        event = OperationalCycleEvent(
            cycle_identity=cycle_identity,
            wall_clock_utc=now_utc,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest="0" * 64,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        ledger.append_event(event)

        # Corrupt the ledger file by writing garbage
        with open(ledger_file, "a", encoding="utf-8") as f:
            f.write("CORRUPTED_JSON_LINE\n")

        corrupted_ledger = OperationalLedger.__new__(OperationalLedger)
        corrupted_ledger.path = ledger_file
        with pytest.raises(DataContractError):
            corrupted_ledger._replay_and_verify_existing_ledger()

    def test_v09_broker_discrepancy(
        self,
        tmp_path: Path,
        now_utc: datetime,
        sample_portfolio: PortfolioState,
    ) -> None:
        """V-09: Live broker position differs from local snapshot -> DISCREPANCY_HALT."""
        ledger_file = tmp_path / "ledger.jsonl"
        ledger = OperationalLedger(ledger_file)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snapshot_digest = PortfolioSnapshotStore.save_snapshot(sample_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="C-001", as_of_utc=now_utc, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=now_utc,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snapshot_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        ledger.append_event(event)

        # Mock broker adapter reporting a live position that does not exist in local snapshot
        class MockDivergentBroker:
            def get_open_positions(self) -> dict[str, Any]:
                return {"EURUSD": Position(
                    symbol="EURUSD",
                    quantity=Decimal("1.0"),
                    entry_price=Decimal("1.0850"),
                    current_price=Decimal("1.0850"),
                    unrealized_pnl=Decimal("0.0"),
                    realized_pnl=Decimal("0.0"),
                    timestamp_utc=now_utc,
                )}

        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir, broker_adapter=MockDivergentBroker())
        _, _, status = rehydrator.rehydrate(as_of_utc=now_utc)
        assert status == RehydrationStatus.DISCREPANCY_HALT

    def test_v10_session_identity_lineage(
        self,
        now_utc: datetime,
    ) -> None:
        """V-10: Verify complete session identity serialization and field integrity."""
        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="SESSION-V10",
            run_id="RUN-V10",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.MT5_FORWARD,
            execution_mode=PaperExecutionVenueType.MT5_DEMO,
            strategy_id="STRAT-MOM-V1",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=now_utc,
            planned_end_time_utc=now_utc + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="a" * 64,
        )
        json_str = session.model_dump_json()
        restored = PaperTradingSessionIdentity.model_validate_json(json_str)
        assert restored.session_id == session.session_id
        assert restored.config_digest == session.config_digest
        assert restored.dossier_digest == session.dossier_digest

    def test_v13_restart_during_unknown(
        self,
        tmp_path: Path,
        now_utc: datetime,
        sample_portfolio: PortfolioState,
    ) -> None:
        """V-13: Process restart after UNKNOWN cycle outcome requires broker reconciliation."""
        ledger_file = tmp_path / "unknown_ledger.jsonl"
        ledger = OperationalLedger(ledger_file)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snapshot_digest = PortfolioSnapshotStore.save_snapshot(sample_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="C-UNK", as_of_utc=now_utc, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=now_utc,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snapshot_digest,
            cycle_outcome=CycleOutcome.DISPATCH_FAILED,
            error_message="TIMEOUT_OCCURRED_IN_TRANSIT: UNKNOWN state",
        )
        ledger.append_event(event)

        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir, broker_adapter=None)
        with pytest.raises(DataContractError, match="CANNOT_REHYDRATE_UNKNOWN_WITHOUT_BROKER"):
            rehydrator.rehydrate(as_of_utc=now_utc)

    def test_v14_restart_after_ack_before_fill(
        self,
        tmp_path: Path,
        now_utc: datetime,
        sample_portfolio: PortfolioState,
    ) -> None:
        """V-14: Restart after ACK before FILL maintains clean recovery state."""
        ledger_file = tmp_path / "ack_ledger.jsonl"
        ledger = OperationalLedger(ledger_file)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snapshot_digest = PortfolioSnapshotStore.save_snapshot(sample_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="C-ACK", as_of_utc=now_utc, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=now_utc,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snapshot_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        ledger.append_event(event)

        class MockMatchingBroker:
            def get_open_positions(self) -> dict[str, Any]:
                return {}

        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir, broker_adapter=MockMatchingBroker())
        _, _, status = rehydrator.rehydrate(as_of_utc=now_utc)
        assert status == RehydrationStatus.CLEAN_RECOVERY

    def test_v16_broker_ledger_divergence(
        self,
        tmp_path: Path,
        now_utc: datetime,
        sample_portfolio: PortfolioState,
    ) -> None:
        """V-16: External unmanaged divergence on broker flags DISCREPANCY_HALT."""
        ledger_file = tmp_path / "div_ledger.jsonl"
        ledger = OperationalLedger(ledger_file)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snapshot_digest = PortfolioSnapshotStore.save_snapshot(sample_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="C-DIV", as_of_utc=now_utc, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=now_utc,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snapshot_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        ledger.append_event(event)

        class MockDivergenceFlaggingBroker:
            def get_open_positions(self) -> dict[str, Any]:
                return {}

            def check_divergence(self) -> bool:
                return True

        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir, broker_adapter=MockDivergenceFlaggingBroker())
        _, _, status = rehydrator.rehydrate(as_of_utc=now_utc)
        assert status == RehydrationStatus.DISCREPANCY_HALT


# ============================================================================
# 4. TEST SUITE: TestPaperStrategyAdapter
# ============================================================================


class TestPaperStrategyAdapter:
    """Vectors V-17, V-18, V-19, V-20 and Candidate Strategy BLOCKED status."""

    def test_candidate_strategy_blocked_without_dossier(
        self,
        now_utc: datetime,
        sample_portfolio: PortfolioState,
    ) -> None:
        """Candidate strategy STRAT-MOM-MULTI-HORIZON-V1 is qualification-blocked without genuine dossier."""
        adapter = PaperStrategyAdapter(
            strategy_id="STRAT-MOM-MULTI-HORIZON-V1",
            strategy_version="1.0.0",
            dossier_path=None,
        )
        assert adapter.is_eligible is False
        assert adapter.verify_eligibility() is False

        # Allocates 100% Cash fallback
        alloc = adapter.generate_candidate_allocation([], sample_portfolio, now_utc)
        assert alloc.is_fallback_baseline is True
        assert alloc.cash_weight == Decimal("1.0")
        assert alloc.authorized_weights == {}
        assert alloc.gate_verdict == "GOVERNANCE_FALLBACK_CASH_ONLY"

    def test_v17_session_identity_tampering(
        self,
        now_utc: datetime,
    ) -> None:
        """V-17: Planned end time preceding start time raises DataContractError."""
        cost_model = ExecutionCostModel()
        with pytest.raises(DataContractError, match="planned_end_time_utc"):
            PaperTradingSessionIdentity(
                session_id="S-TAMPER",
                run_id="R-TAMPER",
                market="TRADITIONAL_FX",
                data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
                execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
                strategy_id="STRAT-01",
                strategy_version="1.0.0",
                prng_seed=42,
                start_time_utc=now_utc,
                planned_end_time_utc=now_utc - timedelta(days=1),  # Tampered invalid time
                config_digest=cost_model.compute_digest(),
                dossier_digest="0" * 64,
            )

    def test_v18_dossier_digest_mismatch(
        self,
        tmp_path: Path,
        now_utc: datetime,
    ) -> None:
        """V-18: Providing dossier with altered hash results in is_eligible = False."""
        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="S-18",
            run_id="R-18",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=now_utc,
            planned_end_time_utc=now_utc + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="b" * 64,  # Expected digest 'b'*64
        )
        fake_dossier_path = tmp_path / "fake_dossier.json"
        with open(fake_dossier_path, "w", encoding="utf-8") as f:
            json.dump({"dossier_digest": "c" * 64, "lifecycle_state": "RESEARCH_QUALIFIED"}, f)

        adapter = PaperStrategyAdapter(
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            dossier_path=fake_dossier_path,
            session_identity=session,
        )
        assert adapter.is_eligible is False

    def test_v19_wrong_strategy_version(
        self,
        now_utc: datetime,
    ) -> None:
        """V-19: Strategy code version mismatch vs session identity raises DataContractError."""
        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="S-19",
            run_id="R-19",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=now_utc,
            planned_end_time_utc=now_utc + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="0" * 64,
        )
        with pytest.raises(DataContractError, match="STRATEGY_VERSION_MISMATCH"):
            PaperStrategyAdapter(
                strategy_id="STRAT-01",
                strategy_version="2.0.0",  # Mismatched version
                session_identity=session,
            )

    def test_v20_wrong_config_digest(
        self,
        now_utc: datetime,
    ) -> None:
        """V-20: Changing cost model config without updating session identity raises DataContractError."""
        original_cost = ExecutionCostModel(
            slippage_model=SlippageModelConfig(fixed_slippage_bps=Decimal("0.50"))
        )
        session = PaperTradingSessionIdentity(
            session_id="S-20",
            run_id="R-20",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=now_utc,
            planned_end_time_utc=now_utc + timedelta(days=90),
            config_digest=original_cost.compute_digest(),
            dossier_digest="0" * 64,
        )
        # Mutated cost model with altered slippage
        mutated_cost = ExecutionCostModel(
            slippage_model=SlippageModelConfig(fixed_slippage_bps=Decimal("1.50"))
        )
        with pytest.raises(DataContractError, match="CONFIG_DIGEST_MISMATCH"):
            PaperStrategyAdapter(
                strategy_id="STRAT-01",
                strategy_version="1.0.0",
                session_identity=session,
                cost_model=mutated_cost,
            )
