"""Regression tests for Shadow Tournament RISK_HALTED slot finalization.

Validates the D5 post-mortem invariants:
1. A slot that is already RISK_HALTED is NOT skipped during tournament halt/shutdown.
2. Final reconciliation, daily snapshot, SESSION_STOPPED event, and sealed manifest
   are executed exactly once for RISK_HALTED slots.
3. The slot remains in RISK_HALTED execution state (not reverted to RUNNING or STOPPED).
4. Causal reason provenance is preserved: terminal reason is RISK_KILL_SWITCH,
   not fabricated as OPERATOR_STOP or NORMAL_COMPLETION.
5. operatorResolutionRequired remains True.
6. Zero post-kill simulated fills, orders, or strategy resume.
7. Mixed slot configurations (RISK_HALTED, RUNNING, UNASSIGNED) finalize correctly.
8. Shutdown and PaperSessionRunner.stop() are idempotent (no duplicate snapshots,
   no duplicate SESSION_STOPPED events, no manifest overwriting).
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.paper.health import TerminalReason
from acash.paper.journal import JournalEventType
from acash.paper.metrics import MetricsRegistry
from acash.paper.runner import (
    KillSwitchPositionPolicy,
    PaperSessionConfig,
    PaperSessionRunner,
    PortfolioFundingPolicy,
    SignalSizingPolicy,
    SyntheticBar,
)
from acash.paper.strategy import InfrastructureTestStrategy
from acash.paper.tournament import (
    ShadowTournamentSupervisor,
    SlotExecutionState,
    TournamentSlot,
    create_default_shadow_tournament,
)


def _make_bar(price: str, seq: int, base: datetime) -> SyntheticBar:
    price_dec = Decimal(price)
    return SyntheticBar(
        timestamp_utc=base + timedelta(minutes=seq),
        symbol="BTCUSDT",
        open=price_dec,
        high=price_dec + Decimal("10.0"),
        low=price_dec - Decimal("10.0"),
        close=price_dec,
        volume=Decimal("1.5"),
        feed_source="SYNTHETIC_TEST",
        feed_source_id=f"BTCUSDT-M1-{seq}",
        received_at_utc=base + timedelta(minutes=seq, seconds=1),
        feed_sequence=seq,
        data_age_ms=1000,
    )


def _crash_prices() -> List[str]:
    # Builds a long position over 8 bars, then crashes to trigger realized loss >= 1.0
    safe = [str(float(100 + i)) for i in range(8)]
    crash = ["55.0", "60.0", "52.0", "50.0"]
    return safe + crash


def _make_session_config(
    tmp_path: Path,
    session_id: str,
    *,
    initial_cash: Decimal = Decimal("1000.00"),
    max_daily_loss: Decimal = Decimal("100.00"),
) -> PaperSessionConfig:
    return PaperSessionConfig(
        session_id=session_id,
        strategy_id="INFRA-TEST-MOMENTUM-SYNTHETIC-001",
        strategy_version="1.0.0",
        instrument="BTCUSDT",
        initial_cash=initial_cash,
        max_position_units=Decimal("10.0"),
        max_notional=Decimal("100000.0"),
        max_daily_loss=max_daily_loss,
        fill_slippage_bps=Decimal("0.5"),
        fill_commission_per_unit=Decimal("7.0"),
        prng_seed=42,
        git_commit="test-commit",
        component_version="0.1.0-test",
        journal_path=tmp_path / f"{session_id}.journal.jsonl",
        snapshot_path=tmp_path / f"{session_id}.snapshots.jsonl",
        portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        max_debt_limit_usd=Decimal("0"),
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
        signal_sizing_policy=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        nav_sizing_notional_pct=Decimal("10.0"),
    )


def _configure_slot_tight_daily_loss(
    runner: PaperSessionRunner,
    max_daily_loss: Decimal = Decimal("1.0"),
) -> None:
    cfg = runner._config
    new_cfg = PaperSessionConfig(
        session_id=cfg.session_id,
        strategy_id=cfg.strategy_id,
        strategy_version=cfg.strategy_version,
        instrument=cfg.instrument,
        initial_cash=cfg.initial_cash,
        max_position_units=cfg.max_position_units,
        max_notional=cfg.max_notional,
        max_daily_loss=max_daily_loss,
        fill_slippage_bps=cfg.fill_slippage_bps,
        fill_commission_per_unit=cfg.fill_commission_per_unit,
        prng_seed=cfg.prng_seed,
        git_commit=cfg.git_commit,
        component_version=cfg.component_version,
        journal_path=cfg.journal_path,
        snapshot_path=cfg.snapshot_path,
        portfolio_funding_policy=cfg.portfolio_funding_policy,
        max_debt_limit_usd=cfg.max_debt_limit_usd,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
        signal_sizing_policy=cfg.signal_sizing_policy,
        nav_sizing_notional_pct=cfg.nav_sizing_notional_pct,
    )
    runner._config = new_cfg
    runner._config_hash = new_cfg.compute_config_hash()


class TestRiskHaltedSlotFinalization:
    def test_risk_halted_slot_finalizes_on_tournament_shutdown(
        self, tmp_path: Path
    ) -> None:
        """A slot in RISK_HALTED state must be finalized when supervisor.halt() runs."""
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="4b2269d49cc36be94d4f7fb93a8b5e120a292cf6",
        )
        runner_a = supervisor.slots["A"].runner
        assert runner_a is not None
        _configure_slot_tight_daily_loss(runner_a, max_daily_loss=Decimal("1.0"))

        supervisor.start()
        assert runner_a.is_started is True
        assert runner_a.is_finalized is False

        # Feed crash prices to trigger kill switch
        base = datetime(2026, 9, 16, 0, 7, 16, tzinfo=timezone.utc)
        for idx, price in enumerate(_crash_prices(), start=1):
            supervisor.process_bar(_make_bar(price, idx, base))

        # Verify mid-run risk-halt state
        slot_a = supervisor.slots["A"]
        assert slot_a.status == SlotExecutionState.RISK_HALTED.value
        assert runner_a.kill_switch_active is True
        assert runner_a.operator_resolution_required is True
        assert runner_a.is_finalized is False
        assert runner_a.manifest is None
        manifest_file = tmp_path / f"{slot_a.session_id}.manifest.json"
        assert not manifest_file.exists()

        # Perform tournament shutdown (simulating watchdog 24h completion / operator stop)
        supervisor.halt(
            "Tournament shutdown complete",
            terminal_reason=TerminalReason.OPERATOR_STOP,
        )

        # Invariants after shutdown:
        # 1. Slot status remains RISK_HALTED
        assert slot_a.status == SlotExecutionState.RISK_HALTED.value
        assert "Kill switch active" in (slot_a.halt_reason or "")
        # 2. Operator resolution requirement preserved
        assert runner_a.operator_resolution_required is True
        # 3. Runner is marked finalized
        assert runner_a.is_finalized is True
        # 4. Manifest exists and is sealed
        assert runner_a.manifest is not None
        assert manifest_file.exists()
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest_data["session_id"] == slot_a.session_id
        assert manifest_data["final_reconciliation_status"] == "PASS"
        assert manifest_data["journal_integrity_status"] == "PASS"

        # 5. Daily snapshot exists
        snapshots = runner_a._snapshot_store.read_all()
        assert len(snapshots) >= 1
        assert snapshots[-1].session_id == slot_a.session_id
        assert snapshots[-1].journal_integrity_status == "PASS"

        # 6. Journal preserves causal terminal reason (RISK_KILL_SWITCH)
        events = runner_a.journal.read_all()
        stopped_events = [
            ev for ev in events if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert len(stopped_events) == 1
        assert stopped_events[0].payload["reason"] == TerminalReason.RISK_KILL_SWITCH.value

    def test_no_post_kill_execution_during_or_after_shutdown(
        self, tmp_path: Path
    ) -> None:
        """Kill switch halts execution: zero fills, zero intents, zero strategy resume."""
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="4b2269d49cc36be94d4f7fb93a8b5e120a292cf6",
        )
        runner_a = supervisor.slots["A"].runner
        assert runner_a is not None
        _configure_slot_tight_daily_loss(runner_a, max_daily_loss=Decimal("1.0"))

        supervisor.start()
        base = datetime(2026, 9, 16, 0, 7, 16, tzinfo=timezone.utc)
        for idx, price in enumerate(_crash_prices(), start=1):
            supervisor.process_bar(_make_bar(price, idx, base))

        assert runner_a.kill_switch_active is True

        # Read journal counts right after kill switch
        events_post_kill = runner_a.journal.read_all()
        kill_idx = next(
            i
            for i, ev in enumerate(events_post_kill)
            if ev.event_type == JournalEventType.KILL_SWITCH_TRIGGERED
        )
        fills_after_kill = [
            ev
            for ev in events_post_kill[kill_idx:]
            if ev.event_type == JournalEventType.FILL_SIMULATED
        ]
        orders_after_kill = [
            ev
            for ev in events_post_kill[kill_idx:]
            if ev.event_type == JournalEventType.ORDER_INTENT_CREATED
        ]
        assert len(fills_after_kill) == 0, "No fills must occur after kill switch"
        assert len(orders_after_kill) == 0, "No orders must occur after kill switch"

        # Attempt to process further bars while risk halted
        res = supervisor.process_bar(_make_bar("45.0", 99, base))
        assert res["A"] is None

        # Halt tournament
        supervisor.halt(
            "Tournament shutdown complete",
            terminal_reason=TerminalReason.OPERATOR_STOP,
        )

        # Verify again on finalized journal: no fills, no orders added during halt
        final_events = runner_a.journal.read_all()
        post_shutdown_fills = [
            ev
            for ev in final_events[kill_idx:]
            if ev.event_type == JournalEventType.FILL_SIMULATED
        ]
        post_shutdown_orders = [
            ev
            for ev in final_events[kill_idx:]
            if ev.event_type == JournalEventType.ORDER_INTENT_CREATED
        ]
        assert len(post_shutdown_fills) == 0
        assert len(post_shutdown_orders) == 0

    def test_multi_slot_mixed_finalization_risk_halted_and_running(
        self, tmp_path: Path
    ) -> None:
        """Tournament with mixed slot states (RISK_HALTED, RUNNING, UNASSIGNED)."""
        strat_a = InfrastructureTestStrategy(
            fast_period=2, slow_period=3, trade_quantity=Decimal("1.0"), symbol="BTCUSDT"
        )
        strat_b = InfrastructureTestStrategy(
            fast_period=2, slow_period=3, trade_quantity=Decimal("1.0"), symbol="BTCUSDT"
        )
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="4b2269d49cc36be94d4f7fb93a8b5e120a292cf6",
            slot_strategies={"A": strat_a, "B": strat_b},
        )
        runner_a = supervisor.slots["A"].runner
        runner_b = supervisor.slots["B"].runner
        assert runner_a is not None and runner_b is not None
        assert supervisor.slots["C"].runner is None

        # Only tighten Slot A daily loss so Slot A risk-halts while Slot B remains running
        _configure_slot_tight_daily_loss(runner_a, max_daily_loss=Decimal("1.0"))

        supervisor.start()
        base = datetime(2026, 9, 16, 0, 7, 16, tzinfo=timezone.utc)
        for idx, price in enumerate(_crash_prices(), start=1):
            supervisor.process_bar(_make_bar(price, idx, base))

        assert supervisor.slots["A"].status == SlotExecutionState.RISK_HALTED.value
        assert supervisor.slots["B"].status == SlotExecutionState.RUNNING.value
        assert supervisor.slots["C"].status == SlotExecutionState.UNASSIGNED.value

        # Halt tournament
        supervisor.halt(
            "Operator shutdown",
            terminal_reason=TerminalReason.OPERATOR_STOP,
        )

        # Slot A: RISK_HALTED, finalized with RISK_KILL_SWITCH
        assert supervisor.slots["A"].status == SlotExecutionState.RISK_HALTED.value
        assert runner_a.is_finalized is True
        assert (tmp_path / f"{supervisor.slots['A'].session_id}.manifest.json").exists()
        events_a = runner_a.journal.read_all()
        stopped_a = [
            ev for ev in events_a if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert stopped_a[0].payload["reason"] == TerminalReason.RISK_KILL_SWITCH.value

        # Slot B: STOPPED, finalized with OPERATOR_STOP
        assert supervisor.slots["B"].status == SlotExecutionState.STOPPED.value
        assert runner_b.is_finalized is True
        assert (tmp_path / f"{supervisor.slots['B'].session_id}.manifest.json").exists()
        events_b = runner_b.journal.read_all()
        stopped_b = [
            ev for ev in events_b if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert stopped_b[0].payload["reason"] == TerminalReason.OPERATOR_STOP.value

        # Slot C: remains UNASSIGNED
        assert supervisor.slots["C"].status == SlotExecutionState.UNASSIGNED.value

        # Status JSON export conforms
        status_file = tmp_path / "status.json"
        supervisor.export_status_json(status_file)
        data = json.loads(status_file.read_text(encoding="utf-8"))
        assert data["slots"]["A"]["status"] == "RISK_HALTED"
        assert data["slots"]["A"]["operatorResolutionRequired"] is True
        assert data["slots"]["B"]["status"] == "STOPPED"
        assert data["slots"]["B"]["operatorResolutionRequired"] is False
        assert data["slots"]["C"]["status"] == "UNASSIGNED"

    def test_shutdown_and_runner_stop_idempotency(self, tmp_path: Path) -> None:
        """Invoking halt() or runner.stop() multiple times must be strictly idempotent."""
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="4b2269d49cc36be94d4f7fb93a8b5e120a292cf6",
        )
        runner_a = supervisor.slots["A"].runner
        assert runner_a is not None
        _configure_slot_tight_daily_loss(runner_a, max_daily_loss=Decimal("1.0"))

        supervisor.start()
        base = datetime(2026, 9, 16, 0, 7, 16, tzinfo=timezone.utc)
        for idx, price in enumerate(_crash_prices(), start=1):
            supervisor.process_bar(_make_bar(price, idx, base))

        # First halt
        supervisor.halt(
            "Tournament shutdown complete",
            terminal_reason=TerminalReason.OPERATOR_STOP,
        )
        first_manifest = runner_a.manifest
        assert first_manifest is not None
        first_manifest_id = first_manifest.manifest_id

        # Second halt on supervisor (should be no-op)
        supervisor.halt(
            "Second shutdown attempt",
            terminal_reason=TerminalReason.OPERATOR_STOP,
        )

        # Direct call to runner.stop() again
        repeated_manifest = runner_a.stop(terminal_reason=TerminalReason.INTERNAL_ERROR)
        assert repeated_manifest.manifest_id == first_manifest_id

        # Verify idempotency invariants:
        # 1. Exactly 1 SESSION_STOPPED event
        events = runner_a.journal.read_all()
        stopped_events = [
            ev for ev in events if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert len(stopped_events) == 1
        assert stopped_events[0].payload["reason"] == TerminalReason.RISK_KILL_SWITCH.value

        # 2. Exactly 1 daily snapshot
        snapshots = runner_a._snapshot_store.read_all()
        assert len(snapshots) == 1

        # 3. Manifest file was not corrupted or modified to a different manifest ID
        manifest_file = tmp_path / f"{supervisor.slots['A'].session_id}.manifest.json"
        saved = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert saved["manifest_id"] == first_manifest_id

    def test_running_runner_stop_idempotency(self, tmp_path: Path) -> None:
        """PaperSessionRunner.stop() on a normally completed runner is idempotent."""
        cfg = _make_session_config(tmp_path, "S-RUNNING-IDEM")
        runner = PaperSessionRunner(cfg)
        runner.start()
        base = datetime(2026, 9, 16, 0, 7, 16, tzinfo=timezone.utc)
        runner.process_bar(_make_bar("50000.0", 1, base))

        manifest1 = runner.stop(terminal_reason=TerminalReason.NORMAL_COMPLETION)
        manifest2 = runner.stop(terminal_reason=TerminalReason.OPERATOR_STOP)

        assert manifest1.manifest_id == manifest2.manifest_id
        assert runner.is_finalized is True
        snapshots = runner._snapshot_store.read_all()
        assert len(snapshots) == 1
        stopped_events = [
            ev
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert len(stopped_events) == 1
        assert stopped_events[0].payload["reason"] == "NORMAL_COMPLETION"

    def test_unstarted_runner_stop_raises_datacontracterror(self, tmp_path: Path) -> None:
        """Calling stop() on an unstarted runner raises DataContractError (fail-closed)."""
        cfg = _make_session_config(tmp_path, "S-UNSTARTED")
        runner = PaperSessionRunner(cfg)
        assert runner.is_started is False
        assert runner.is_finalized is False

        with pytest.raises(DataContractError, match="session not started"):
            runner.stop()
