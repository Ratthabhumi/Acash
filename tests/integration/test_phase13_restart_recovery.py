"""Phase 13: Restart & Recovery Testing Suite (Ladder Step 4).

Strictly validates:
- R-01: Clean restart with valid ledger and snapshot -> CLEAN_RECOVERY.
- R-02: Restart while order is UNKNOWN -> broker reconciliation is mandatory before new cycles.
- R-03: Restart after ACK but before FILL -> pending order state is preserved and resolved only by authoritative evidence.
- R-04: Restart during PARTIALLY_FILLED -> cumulative filled quantity and remaining working quantity remain consistent.
- R-05: Corrupted operational ledger -> DataContractError / startup halt.
- R-06: Snapshot digest mismatch -> fail closed.
- R-07: Broker position divergence -> DISCREPANCY_HALT.
- R-08: UNKNOWN with unavailable broker authority -> fail closed.
- R-09: UNKNOWN with valid authoritative broker reconciliation -> CLEAN_RECOVERY.
- R-10: Session identity / configuration tampering across restart -> startup validation failure.

Governance Invariants:
- Live Capital: $0.00
- Live Orders: 0
- Broker Wire: DISCONNECTED
- Frozen Core: 0 modifications
- Strategy Qualification: STRAT-MOM-MULTI-HORIZON-V1 remains BLOCKED
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.market_data import MarketDataSnapshot
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.execution.coordinator import ExecutionCoordinator
from acash.execution.mock_broker import BrokerRawEvent
from acash.execution.mt5.adapter import MT5BrokerAdapter
from acash.execution.mt5.enums import (
    MT5ExecutionPolicy,
    MT5OrderType,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.schemas import BrokerSymbolSpec
from acash.execution.mt5.transport import (
    MockMT5Transport,
    MT5ReconciliationConfirmation,
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
)
from acash.runtime.ledger import OperationalLedger
from acash.runtime.paper_bridge import (
    ExecutionCostModel,
    PaperExecutionBridge,
    PaperExecutionVenueType,
    SimulatedMarketMatcher,
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
# FIXTURES & HELPERS
# ============================================================================


@pytest.fixture
def base_time() -> datetime:
    return datetime(2026, 9, 5, 15, 0, 0, tzinfo=timezone.utc)


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
    return MT5ReconciliationConfirmation(
        reconciliation_id="REC-RECOVERY-001",
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
    from acash.research.alpha_schema import AlphaEconomicDecomposition
    digest = "c" * 64
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
# 1. R-01: CLEAN RESTART WITH VALID LEDGER AND SNAPSHOT
# ============================================================================


class TestCleanRestart:
    """R-01: Clean restart and state reconstitution from disk persistence."""

    def test_r01_clean_restart_with_valid_ledger_and_snapshot(
        self,
        tmp_path: Path,
        base_time: datetime,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """R-01: Valid operational ledger + snapshot reconstitutes exact state -> CLEAN_RECOVERY.
        
        Subsequent trading cycle proceeds without interruption.
        """
        ledger_path = tmp_path / "operational_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"

        # Pre-crash cycle 0: Portfolio has open position of 0.10 lots EURUSD
        pos_qty = Decimal("0.10")
        pos_price = Decimal("1.08500")
        mv = pos_qty * pos_price
        cash = Decimal("99000.00")
        total_eq = cash + mv

        pre_crash_portfolio = PortfolioState(
            timestamp_utc=base_time,
            positions={
                "EURUSD": Position(
                    symbol="EURUSD",
                    quantity=pos_qty,
                    entry_price=pos_price,
                    current_price=pos_price,
                    unrealized_pnl=Decimal("0.0"),
                    realized_pnl=Decimal("0.0"),
                    timestamp_utc=base_time,
                )
            },
            cash_balance=cash,
            total_equity=total_eq,
            margin_used=Decimal("0.0"),
            gross_exposure=mv,
            net_exposure=mv,
            unrealized_pnl=Decimal("0.0"),
            realized_pnl=Decimal("0.0"),
        )
        snap_digest = PortfolioSnapshotStore.save_snapshot(pre_crash_portfolio, snapshot_file)

        cycle_0 = CycleIdentity(
            cycle_id="CYCLE-000",
            as_of_utc=base_time,
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=0,
        )
        event_0 = OperationalCycleEvent(
            cycle_identity=cycle_0,
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snap_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
            error_message=None,
        )
        ledger.append_event(event_0)

        # ---------------------------------------------------------------------
        # SIMULATED CRASH / PROCESS TERMINATION
        # ---------------------------------------------------------------------
        del ledger

        # ---------------------------------------------------------------------
        # PROCESS RESTART: Fresh rehydration from disk files
        # ---------------------------------------------------------------------
        restart_ledger = OperationalLedger(ledger_path)
        assert restart_ledger.event_count == 1
        assert restart_ledger.last_sequence == 0

        # Authoritative broker matching open position
        class MockMatchingBroker:
            def get_open_positions(self) -> Dict[str, Any]:
                class Pos:
                    quantity = Decimal("0.10")
                return {"EURUSD": Pos()}

            def check_divergence(self) -> bool:
                return False

        rehydrator = PortfolioStateRehydrator(
            ledger=restart_ledger,
            snapshot_dir=snapshot_dir,
            broker_adapter=MockMatchingBroker(),
        )

        recovered_portfolio, recovered_account, status = rehydrator.rehydrate(as_of_utc=base_time)

        # Assertions
        assert status == RehydrationStatus.CLEAN_RECOVERY
        assert recovered_portfolio.cash_balance == Decimal("99000.00")
        assert recovered_portfolio.total_equity == total_eq
        assert "EURUSD" in recovered_portfolio.positions
        assert recovered_portfolio.positions["EURUSD"].quantity == Decimal("0.10")
        assert recovered_account.balance == Decimal("99000.00")

        # Verify next cycle (sequence 1) can append cleanly
        cycle_1 = CycleIdentity(
            cycle_id="CYCLE-001",
            as_of_utc=base_time + timedelta(seconds=1),
            regime=RuntimeRegime.MARKET_OPEN,
            sequence_number=1,
        )
        event_1 = OperationalCycleEvent(
            cycle_identity=cycle_1,
            wall_clock_utc=base_time + timedelta(seconds=1),
            previous_event_digest=restart_ledger.last_event_digest,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snap_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
            error_message=None,
        )
        restart_ledger.append_event(event_1)
        assert restart_ledger.event_count == 2
        assert restart_ledger.last_sequence == 1

    def test_r01_genesis_restart_with_empty_ledger(
        self,
        tmp_path: Path,
        base_time: datetime,
    ) -> None:
        """R-01 Genesis: Rehydration with empty ledger returns EMPTY_GENESIS state with $100k balance."""
        ledger = OperationalLedger(tmp_path / "genesis_ledger.jsonl")
        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=tmp_path)

        p, a, status = rehydrator.rehydrate(as_of_utc=base_time)
        assert status == RehydrationStatus.EMPTY_GENESIS
        assert p.cash_balance == Decimal("100000.00")
        assert a.balance == Decimal("100000.00")
        assert len(p.positions) == 0


# ============================================================================
# 2. R-02, R-08, R-09: UNKNOWN ORDER LIFECYCLE & MANDATORY RECONCILIATION
# ============================================================================


class TestUnknownStateRestartAndReconciliation:
    """R-02, R-08, R-09: Fail-closed UNKNOWN semantics and reconciliation requirements."""

    def test_r02_restart_during_unknown_requires_broker_reconciliation_before_new_cycles(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """R-02: Restart while order state is UNKNOWN forces broker reconciliation before new cycles."""
        ledger_path = tmp_path / "unknown_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snap_digest = PortfolioSnapshotStore.save_snapshot(initial_portfolio, snapshot_file)

        # Injected UNKNOWN cycle event
        unknown_event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-UNK-01", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snap_digest,
            cycle_outcome=CycleOutcome.DISPATCH_FAILED,
            error_message="TIMEOUT_OCCURRED_IN_TRANSIT: Order state UNKNOWN",
        )
        ledger.append_event(unknown_event)

        # CRASH & RESTART
        del ledger
        restart_ledger = OperationalLedger(ledger_path)

        # Attempting rehydrate without broker reconciliation FAILS CLOSED
        blind_rehydrator = PortfolioStateRehydrator(ledger=restart_ledger, snapshot_dir=snapshot_dir, broker_adapter=None)
        with pytest.raises(DataContractError, match="CANNOT_REHYDRATE_UNKNOWN_WITHOUT_BROKER"):
            blind_rehydrator.rehydrate(as_of_utc=base_time)

    def test_r08_unknown_with_unavailable_broker_authority_fails_closed(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
    ) -> None:
        """R-08: UNKNOWN state with unavailable / broken broker adapter fails closed."""
        ledger_path = tmp_path / "unknown_fail_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snap_digest = PortfolioSnapshotStore.save_snapshot(initial_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-UNK-08", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snap_digest,
            cycle_outcome=CycleOutcome.DISPATCH_FAILED,
            error_message="Network disconnect: UNKNOWN order status",
        )
        ledger.append_event(event)

        # Broker adapter is None
        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir, broker_adapter=None)
        with pytest.raises(DataContractError, match="CANNOT_REHYDRATE_UNKNOWN_WITHOUT_BROKER"):
            rehydrator.rehydrate(as_of_utc=base_time)

    def test_r09_unknown_with_valid_authoritative_broker_reconciliation(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
    ) -> None:
        """R-09: UNKNOWN state resolved by authoritative broker reconciliation -> CLEAN_RECOVERY."""
        ledger_path = tmp_path / "unknown_resolved_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snap_digest = PortfolioSnapshotStore.save_snapshot(initial_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-UNK-09", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snap_digest,
            cycle_outcome=CycleOutcome.DISPATCH_FAILED,
            error_message="Broker timeout: state UNKNOWN",
        )
        ledger.append_event(event)

        # Authoritative broker confirms 0 open positions (order never reached book)
        class AuthoritativeBroker:
            def get_open_positions(self) -> Dict[str, Any]:
                return {}

            def check_divergence(self) -> bool:
                return False

        rehydrator = PortfolioStateRehydrator(
            ledger=ledger,
            snapshot_dir=snapshot_dir,
            broker_adapter=AuthoritativeBroker(),
        )
        p, a, status = rehydrator.rehydrate(as_of_utc=base_time)
        assert status == RehydrationStatus.CLEAN_RECOVERY
        assert p.cash_balance == Decimal("100000.00")
        assert len(p.positions) == 0


# ============================================================================
# 3. R-03, R-04: IN-FLIGHT ORDERS & PARTIAL FILL ACROSS RESTART
# ============================================================================


class TestInFlightOrderAndPartialFillRecovery:
    """R-03, R-04: Pending order state and partial fill consistency across restart boundaries."""

    def test_r03_restart_after_ack_before_fill_resolved_by_authoritative_evidence(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """R-03: Order was ACKed before crash.
        
        On restart: Pending state is preserved; local runtime NEVER invents fills.
        Case A: Broker reports order did not execute -> state restored identically.
        Case B: Broker reports unhedged fill occurred while offline -> produces DISCREPANCY_HALT.
        """
        ledger_path = tmp_path / "ack_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snap_digest = PortfolioSnapshotStore.save_snapshot(initial_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-ACK-01", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snap_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
            error_message="Order dispatched, ACK received, pending fill",
        )
        ledger.append_event(event)

        # CASE A: Broker reports fill did NOT occur (position matches snapshot)
        class BrokerNoFill:
            def get_open_positions(self) -> Dict[str, Any]:
                return {}

            def check_divergence(self) -> bool:
                return False

        rehydrator_a = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir, broker_adapter=BrokerNoFill())
        p_a, _, status_a = rehydrator_a.rehydrate(as_of_utc=base_time)
        assert status_a == RehydrationStatus.CLEAN_RECOVERY
        assert len(p_a.positions) == 0  # Invariant: No fills invented

        # CASE B: Broker reports unhedged fill occurred while offline -> produces DISCREPANCY_HALT
        class BrokerDidFill:
            def get_open_positions(self) -> Dict[str, Any]:
                class Pos:
                    quantity = Decimal("0.09")
                return {"EURUSD": Pos()}

            def check_divergence(self) -> bool:
                return True

        rehydrator_b = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir, broker_adapter=BrokerDidFill())
        p_b, _, status_b = rehydrator_b.rehydrate(as_of_utc=base_time)
        assert status_b == RehydrationStatus.DISCREPANCY_HALT

    def test_r04_restart_during_partially_filled_preserves_cumulative_and_working_qty(
        self,
        tmp_path: Path,
        base_time: datetime,
        standard_symbol_spec: BrokerSymbolSpec,
    ) -> None:
        """R-04: Restart during PARTIALLY_FILLED preserves cumulative fill and remaining working quantity.
        
        Zero fills invented; zero double counting.
        """
        # Pre-crash: 0.09 lots requested, 0.04 lots filled, 0.05 lots remaining working qty
        pos_qty = Decimal("0.04")
        pos_price = Decimal("1.08500")
        mv = pos_qty * pos_price
        cash = Decimal("99600.00")
        total_eq = cash + mv

        partial_portfolio = PortfolioState(
            timestamp_utc=base_time,
            positions={
                "EURUSD": Position(
                    symbol="EURUSD",
                    quantity=pos_qty,
                    entry_price=pos_price,
                    current_price=pos_price,
                    unrealized_pnl=Decimal("0.0"),
                    realized_pnl=Decimal("0.0"),
                    timestamp_utc=base_time,
                )
            },
            cash_balance=cash,
            total_equity=total_eq,
            margin_used=Decimal("0.0"),
            gross_exposure=mv,
            net_exposure=mv,
            unrealized_pnl=Decimal("0.0"),
            realized_pnl=Decimal("0.0"),
        )
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snap_digest = PortfolioSnapshotStore.save_snapshot(partial_portfolio, snapshot_file)

        ledger_path = tmp_path / "partial_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)
        cycle_1 = CycleIdentity(cycle_id="CYCLE-P1", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0)
        event_1 = OperationalCycleEvent(
            cycle_identity=cycle_1,
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snap_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
            error_message="Pulse 1 partial fill 0.04 lots committed",
        )
        ledger.append_event(event_1)

        # ---------------------------------------------------------------------
        # SIMULATED CRASH & RESTART
        # ---------------------------------------------------------------------
        del ledger

        restart_ledger = OperationalLedger(ledger_path)
        class MockBrokerWith004:
            def get_open_positions(self) -> Dict[str, Any]:
                class Pos:
                    quantity = Decimal("0.04")
                return {"EURUSD": Pos()}

            def check_divergence(self) -> bool:
                return False

        rehydrator = PortfolioStateRehydrator(
            ledger=restart_ledger,
            snapshot_dir=snapshot_dir,
            broker_adapter=MockBrokerWith004(),
        )
        recovered_portfolio, _, status = rehydrator.rehydrate(as_of_utc=base_time)
        assert status == RehydrationStatus.CLEAN_RECOVERY
        assert recovered_portfolio.positions["EURUSD"].quantity == Decimal("0.04")

        # ---------------------------------------------------------------------
        # RECONSTITUTE RUNTIME FOR PULSE 2
        # Target remains 0.09 lots -> delta needed is 0.09 - 0.04 = 0.05 lots
        # ---------------------------------------------------------------------
        cost_model = ExecutionCostModel()
        session = PaperTradingSessionIdentity(
            session_id="SESS-P2-RECOVER",
            run_id="RUN-P2-RECOVER",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-RECOVER-01",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=cost_model.compute_digest(),
            dossier_digest="0" * 64,
        )

        alloc = AllocationDecision(
            decision_id="DEC-P2-01",
            selected_candidate_id="STRAT-RECOVER-01",
            allocator_name="TOURNAMENT",
            authorized_weights={"EURUSD": Decimal("0.10")},  # Target: 0.09 lots
            cash_weight=Decimal("0.90"),
            authorization_timestamp=base_time + timedelta(seconds=1),
            is_fallback_baseline=False,
            gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
            rationale="Resume working position.",
        )

        matcher = SimulatedMarketMatcher(cost_model=cost_model, partial_fill_ratio=None)
        # Coordinator for Pulse 2 requests remaining 0.05 lots
        coordinator = ExecutionCoordinator(execution_id="EXEC-P2-01", requested_qty=Decimal("0.05"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=PaperExecutionVenueType.LOCAL_SIMULATOR,
            matcher=matcher,
            symbol_spec_provider=lambda s: standard_symbol_spec,
        )

        snap_p2 = MarketDataSnapshot(
            symbol="EURUSD",
            bid=Decimal("1.08510"),
            ask=Decimal("1.08530"),
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=Decimal("1.08520"),
            timestamp_utc=base_time + timedelta(seconds=1),
        )

        outcomes = bridge.evaluate_and_dispatch(
            allocation=alloc,
            portfolio=recovered_portfolio,
            current_snapshot=snap_p2,
            cycle_identity=CycleIdentity(cycle_id="CYCLE-P2", as_of_utc=base_time + timedelta(seconds=1), regime=RuntimeRegime.MARKET_OPEN, sequence_number=1),
            session_identity=session,
        )

        assert len(outcomes) == 2
        assert outcomes[-1].state == OrderLifecycleState.FILLED
        assert coordinator.filled_qty == Decimal("0.05")
        assert len(bridge.emitted_manifests) == 1
        manifest = bridge.emitted_manifests[0]
        # Manifest covers the executed delta of 0.05 lots
        assert manifest.filled_qty == Decimal("0.05")


# ============================================================================
# 4. R-05, R-06, R-07: INTEGRITY CORRUPTION & DISCREPANCY DEFENSES
# ============================================================================


class TestIntegrityCorruptionDefenses:
    """R-05, R-06, R-07: Strict fail-closed integrity defense and discrepancy detection."""

    def test_r05_corrupted_operational_ledger_causes_startup_halt(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
    ) -> None:
        """R-05: Corrupted operational ledger lines, non-monotonic sequence, or broken hash chain halts startup."""
        ledger_path = tmp_path / "corrupt_ledger.jsonl"
        ledger = OperationalLedger(ledger_path)
        snap_store = PortfolioSnapshotStore()
        p_digest = snap_store.save_snapshot(initial_portfolio, tmp_path / "portfolio_state.json")

        # Add valid event 0
        event_0 = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-000", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=p_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        ledger.append_event(event_0)

        # SUBCASE A: Corrupt with invalid JSON
        corrupt_file_a = tmp_path / "corrupt_a.jsonl"
        with open(corrupt_file_a, "w", encoding="utf-8") as f:
            f.write(ledger_path.read_text(encoding="utf-8"))
            f.write("NOT_A_VALID_JSON_LINE\n")

        with pytest.raises(DataContractError, match="invalid JSON"):
            OperationalLedger(corrupt_file_a)

        # SUBCASE B: Non-monotonic sequence jump (sequence 0 -> sequence 2)
        event_jump = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-002", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=2),
            wall_clock_utc=base_time,
            previous_event_digest=event_0.event_digest,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=p_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        corrupt_file_b = tmp_path / "corrupt_b.jsonl"
        with open(corrupt_file_b, "w", encoding="utf-8") as f:
            f.write(event_0.model_dump_json() + "\n")
            f.write(event_jump.model_dump_json() + "\n")

        with pytest.raises(DataContractError, match="expected sequence 1, got 2"):
            OperationalLedger(corrupt_file_b)

        # SUBCASE C: Broken hash chain (tampered previous_event_digest)
        event_broken_chain = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-001", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=1),
            wall_clock_utc=base_time,
            previous_event_digest="f" * 64,  # Invalid previous hash
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=p_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        corrupt_file_c = tmp_path / "corrupt_c.jsonl"
        with open(corrupt_file_c, "w", encoding="utf-8") as f:
            f.write(event_0.model_dump_json() + "\n")
            f.write(event_broken_chain.model_dump_json() + "\n")

        with pytest.raises(DataContractError, match="expected previous_event_digest"):
            OperationalLedger(corrupt_file_c)

    def test_r06_snapshot_digest_mismatch_fails_closed(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
    ) -> None:
        """R-06: Snapshot file tampered on disk fails rehydration closed with DataContractError."""
        ledger_path = tmp_path / "ledger_r06.jsonl"
        ledger = OperationalLedger(ledger_path)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        genuine_digest = PortfolioSnapshotStore.save_snapshot(initial_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-R06", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=genuine_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        ledger.append_event(event)

        # Tamper snapshot on disk with internally consistent accounting so it parses,
        # but digest does not match ledger's committed genuine_digest.
        with open(snapshot_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["state"]["cash_balance"] = "105000.00"
        data["state"]["total_equity"] = "105000.00"
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=snapshot_dir)
        with pytest.raises(DataContractError, match="SNAPSHOT_DIGEST_MISMATCH"):
            rehydrator.rehydrate(as_of_utc=base_time)

    def test_r07_broker_position_divergence_triggers_discrepancy_halt(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
    ) -> None:
        """R-07: External broker position divergence flags DISCREPANCY_HALT and blocks trading."""
        ledger_path = tmp_path / "ledger_r07.jsonl"
        ledger = OperationalLedger(ledger_path)
        snapshot_dir = tmp_path / "snapshots"
        snapshot_file = snapshot_dir / "portfolio_state.json"
        snap_digest = PortfolioSnapshotStore.save_snapshot(initial_portfolio, snapshot_file)

        event = OperationalCycleEvent(
            cycle_identity=CycleIdentity(cycle_id="CYCLE-R07", as_of_utc=base_time, regime=RuntimeRegime.MARKET_OPEN, sequence_number=0),
            wall_clock_utc=base_time,
            runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
            portfolio_state_digest=snap_digest,
            cycle_outcome=CycleOutcome.SUCCESS,
        )
        ledger.append_event(event)

        # Broker has an untracked open position of 0.20 lots
        class DivergentBroker:
            def get_open_positions(self) -> Dict[str, Any]:
                class Pos:
                    quantity = Decimal("0.20")
                return {"EURUSD": Pos()}

            def check_divergence(self) -> bool:
                return True

        rehydrator = PortfolioStateRehydrator(
            ledger=ledger,
            snapshot_dir=snapshot_dir,
            broker_adapter=DivergentBroker(),
        )
        _, _, status = rehydrator.rehydrate(as_of_utc=base_time)
        assert status == RehydrationStatus.DISCREPANCY_HALT


# ============================================================================
# 5. R-10: SESSION IDENTITY & CONFIGURATION LINEAGE DEFENSE
# ============================================================================


class TestSessionLineageDefense:
    """R-10: Startup validation failure on session tampering or forbidden venue pairing."""

    def test_r10_session_identity_and_config_tampering_fails_startup(
        self,
        tmp_path: Path,
        base_time: datetime,
        initial_portfolio: PortfolioState,
    ) -> None:
        """R-10: Tampered config digest, mismatched version, or forbidden venue pairing raises DataContractError.
        
        Tampered dossier digest renders strategy ineligible (is_eligible = False).
        """
        cost_model = ExecutionCostModel()
        digest = cost_model.compute_digest()

        # SUBCASE A: Tampered config_digest in StrategyAdapter raises DataContractError
        dossier_file, d_digest = create_verified_dossier(tmp_path, "STRAT-TAMPER", "1.0.0")
        tampered_session = PaperTradingSessionIdentity(
            session_id="SESS-TAMPER-01",
            run_id="RUN-TAMPER-01",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-TAMPER",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest="e" * 64,  # Tampered config digest
            dossier_digest=d_digest,
        )

        with pytest.raises(DataContractError, match="CONFIG_DIGEST_MISMATCH"):
            PaperStrategyAdapter(
                strategy_id="STRAT-TAMPER",
                strategy_version="1.0.0",
                dossier_path=dossier_file,
                session_identity=tampered_session,
                cost_model=cost_model,
            )

        # SUBCASE B: Strategy ID or version mismatch raises DataContractError
        version_tampered_session = tampered_session.model_copy(update={"strategy_version": "2.0.0", "config_digest": digest})
        with pytest.raises(DataContractError, match="STRATEGY_VERSION_MISMATCH"):
            PaperStrategyAdapter(
                strategy_id="STRAT-TAMPER",
                strategy_version="1.0.0",
                dossier_path=dossier_file,
                session_identity=version_tampered_session,
                cost_model=cost_model,
            )

        # SUBCASE C: Tampered dossier_digest makes strategy ineligible (is_eligible = False)
        tampered_dossier_session = PaperTradingSessionIdentity(
            session_id="SESS-TAMPER-02",
            run_id="RUN-TAMPER-02",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=PaperExecutionVenueType.LOCAL_SIMULATOR,
            strategy_id="STRAT-TAMPER",
            strategy_version="1.0.0",
            prng_seed=42,
            start_time_utc=base_time,
            planned_end_time_utc=base_time + timedelta(days=90),
            config_digest=digest,
            dossier_digest="b" * 64,  # Tampered / mismatched dossier digest
        )
        adapter_tampered_dossier = PaperStrategyAdapter(
            strategy_id="STRAT-TAMPER",
            strategy_version="1.0.0",
            dossier_path=dossier_file,
            session_identity=tampered_dossier_session,
            cost_model=cost_model,
        )
        assert adapter_tampered_dossier.is_eligible is False

        # SUBCASE D: Incompatible feed and execution venue raises DataContractError
        with pytest.raises(DataContractError, match="INVALID_SESSION_CONFIGURATION"):
            PaperTradingSessionIdentity(
                session_id="SESS-FORBIDDEN",
                run_id="RUN-FORBIDDEN",
                market="TRADITIONAL_FX",
                data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
                execution_mode=PaperExecutionVenueType.MT5_DEMO,
                strategy_id="STRAT-TAMPER",
                strategy_version="1.0.0",
                prng_seed=42,
                start_time_utc=base_time,
                planned_end_time_utc=base_time + timedelta(days=90),
                config_digest=digest,
                dossier_digest=d_digest,
            )

        # SUBCASE E: Candidate strategy without dossier remains strictly qualification blocked
        blocked_adapter = PaperStrategyAdapter(
            strategy_id="STRAT-MOM-MULTI-HORIZON-V1",
            strategy_version="1.0.0",
            dossier_path=None,
            session_identity=tampered_session.model_copy(update={"strategy_id": "STRAT-MOM-MULTI-HORIZON-V1", "config_digest": digest, "dossier_digest": "0" * 64}),
            cost_model=cost_model,
        )
        assert blocked_adapter.is_eligible is False
        fallback_alloc = blocked_adapter.generate_candidate_allocation(bars=[], portfolio=initial_portfolio, as_of_utc=base_time)
        assert fallback_alloc.selected_candidate_id == "CASH_FALLBACK"
        assert fallback_alloc.cash_weight == Decimal("1.0")
