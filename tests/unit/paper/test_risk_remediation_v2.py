"""Regression tests — Tournament V2 Risk Remediation (Defects A & E).

Pins the H01-derived defects from docs/SESSION_HANDOFF.md:

- Defect A (MAX_NOTIONAL never enforced): a cumulative exposure that breaches
  max_notional MUST be strictly rejected (RISK_REJECTED with MAX_NOTIONAL
  violation), independent of the max_position_units gate. No order may exceed
  the notional bound even while |position| stays under max_position_units.
- Defect E (terminal reason erased as NORMAL_SHUTDOWN): runner.stop() and the
  tournament halt path MUST propagate a canonical TerminalReason into the
  SESSION_STOPPED journal event. The default remains available for call sites
  that legitimately mean a normal completion; an invalid reason is a fail-closed
  DataContractError.

GOVERNANCE:
- Tests use INFRASTRUCTURE_TEST_STRATEGY_ONLY / SHADOW_SIMULATED_RESEARCH_INFRA_ONLY.
- No research evidence is produced. D17-E remains HOLD.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.paper.health import PaperHealthMonitor, TerminalReason
from acash.paper.journal import JournalEventType, PaperEventJournal
from acash.paper.runner import PaperSessionConfig, PaperSessionRunner, SyntheticBar
from acash.paper.strategy import InfrastructureTestStrategy
from acash.paper.tournament import create_default_shadow_tournament

STRATEGY = InfrastructureTestStrategy


def _make_config(
    tmp_path: Path,
    session_id: str,
    *,
    initial_cash: Decimal = Decimal("1000000"),
    max_position_units: Decimal = Decimal("100"),
    max_notional: Decimal = Decimal("120000"),
    max_daily_loss: Decimal = Decimal("500000"),
    trade_quantity: Decimal = Decimal("1.0"),
) -> PaperSessionConfig:
    return PaperSessionConfig(
        session_id=session_id,
        strategy_id=STRATEGY.STRATEGY_ID,
        strategy_version=STRATEGY.STRATEGY_VERSION,
        instrument="BTCUSDT",
        initial_cash=initial_cash,
        max_position_units=max_position_units,
        max_notional=max_notional,
        max_daily_loss=max_daily_loss,
        fill_slippage_bps=Decimal("0.5"),
        fill_commission_per_unit=Decimal("7.0"),
        prng_seed=42,
        git_commit="test-commit",
        component_version="0.1.0-test",
        journal_path=tmp_path / f"{session_id}.journal.jsonl",
        snapshot_path=tmp_path / f"{session_id}.snapshots.jsonl",
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


# ---------------------------------------------------------------------------
# Defect A — MAX_NOTIONAL gate (cumulative exposure)
# ---------------------------------------------------------------------------


class TestMaxNotionalGate:
    def test_notional_bounded_even_when_position_within_units(
        self, tmp_path: Path
    ) -> None:
        """Position stays under max_position_units but must be capped by notional."""
        config = _make_config(
            tmp_path,
            "TEST-NOTIONAL-GATE",
            max_position_units=Decimal("100"),
            max_notional=Decimal("120000"),
            max_daily_loss=Decimal("500000"),
        )
        runner = PaperSessionRunner(config)
        runner.start()

        # Monotonically rising prices force persistent LONG signals of 1.0 unit.
        # (slow=5 warm-up: signals begin at bar 5.)
        prices = [
            "49000.0",
            "49100.0",
            "49200.0",
            "49300.0",
            "49400.0",  # bar 5: first trade (pos 1 -> ~49k notional) APPROVED
            "49500.0",  # pos 2 -> ~98k notional APPROVED
            "49600.0",  # pos 3 -> ~147k notional > 120k REJECTED (breach)
            "49700.0",  # pos still 2 -> ~99k APPROVED again
            "49800.0",  # pos 3 (rejected) -> no accumulation beyond cap
        ]
        for idx, price in enumerate(prices, start=1):
            runner.process_bar(_make_bar(price, idx, datetime(2026, 1, 5, 9, tzinfo=timezone.utc)))

        events = runner.journal.read_all()
        rejected = [
            ev.payload
            for ev in events
            if ev.event_type == JournalEventType.RISK_REJECTED
        ]
        fills = [
            ev.payload
            for ev in events
            if ev.event_type == JournalEventType.FILL_SIMULATED
        ]

        # At least one rejection, and it must be a NOTIONAL breach (not position).
        assert len(rejected) >= 1, "a notional breach must be rejected"
        assert any("MAX_NOTIONAL" in " ".join(ev.get("violations", [])) for ev in rejected)
        assert any("MAX_POSITION" not in " ".join(ev.get("violations", [])) for ev in rejected)

        # The rejected breach must not have produced a fill.
        notional_capped = runner._portfolio.position <= Decimal("2.0")
        assert notional_capped, "cumulative exposure must never breach max_notional"
        assert len(fills) >= 2, "first trades that stay in bounds should fill"

    def test_notional_rejection_records_sizing_provenance(self, tmp_path: Path) -> None:
        """RISK_REJECTED payload carries proposed notional and reference price."""
        config = _make_config(
            tmp_path,
            "TEST-NOTIONAL-PROVENANCE",
            max_position_units=Decimal("100"),
            max_notional=Decimal("10"),
            max_daily_loss=Decimal("500000"),
        )
        runner = PaperSessionRunner(config)
        runner.start()

        for idx, price in enumerate(
            ["49000.0", "49100.0", "49200.0", "49300.0", "49400.0"], start=1
        ):
            runner.process_bar(_make_bar(price, idx, datetime(2026, 1, 5, 9, tzinfo=timezone.utc)))

        rejected = [
            ev.payload
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.RISK_REJECTED
        ]
        assert rejected
        payload = rejected[0]
        assert "proposed_notional" in payload, "notional evidence must be journaled"
        assert "reference_price" in payload, "reference price must be journaled"
        assert "max_notional" in payload, "bound must be journaled"
        assert float(payload["proposed_notional"]) > 10.0  # breaches

    def test_notional_gate_prevents_h01_style_leverage_accumulation(
        self, tmp_path: Path
    ) -> None:
        """Reproduce H01 Slot A: the MAX_NOTIONAL cap must stop exposure buildup.

        H01 evidence shows final position 9 BTC at avg_entry ~77846 with cash
        driven deeply negative (-699728): max_position_units was never the bound
        that fired. The notional gate (cumulative |pos| * mark <= max_notional)
        is the FAIL-CLOSED boundary that prevents that accumulation.
        """
        config = _make_config(
            tmp_path,
            "TEST-H01-NOTIONAL",
            initial_cash=Decimal("1000"),
            max_position_units=Decimal("10.0"),
            max_notional=Decimal("100000"),
            max_daily_loss=Decimal("100.0"),
            trade_quantity=Decimal("1.0"),
        )
        runner = PaperSessionRunner(config)
        runner.start()

        base = datetime(2026, 9, 14, 7, 33, tzinfo=timezone.utc)
        # Rising prices -> persistent LONG, 1.0 BTC per bar.
        prices = [str(float(77000 + i * 50)) for i in range(10)]
        for idx, price in enumerate(prices, start=1):
            runner.process_bar(_make_bar(price, idx, base))

        events = runner.journal.read_all()
        rejected = [
            ev.payload
            for ev in events
            if ev.event_type == JournalEventType.RISK_REJECTED
        ]
        fills = [
            ev.payload for ev in events if ev.event_type == JournalEventType.FILL_SIMULATED
        ]

        # Fail-closed: exposure must stay well under H01's breached 9 BTC.
        assert runner._portfolio.position < Decimal("3")
        assert len(fills) >= 1

        # Every rejection must be a MAX_NOTIONAL or MAX_DAILY_LOSS breach (never
        # a silent pass-through, never merely a position bound that H01 bypassed).
        if rejected:
            all_violations = " ".join(
                v for ev in rejected for v in ev.get("violations", [])
            )
            assert "MAX_NOTIONAL" in all_violations or "MAX_DAILY_LOSS" in all_violations


# ---------------------------------------------------------------------------
# Defect E — terminal reason preserved through stop / halt
# ---------------------------------------------------------------------------


class TestTerminalReason:
    def test_stop_preserves_operator_stop_reason(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, "TEST-REASON-OPERATOR")
        runner = PaperSessionRunner(config)
        runner.start()
        runner.stop(terminal_reason=TerminalReason.OPERATOR_STOP)

        stopped = [
            ev
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert len(stopped) == 1
        assert stopped[0].payload["reason"] == "OPERATOR_STOP"

    def test_stop_preserves_feed_disconnected_reason(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, "TEST-REASON-FEED")
        runner = PaperSessionRunner(config)
        runner.start()
        # Simulate connection loss before stop (no reconnection, fail-closed).
        runner.stop(terminal_reason=TerminalReason.FEED_DISCONNECTED)

        stopped = [
            ev
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert stopped[0].payload["reason"] == "FEED_DISCONNECTED"

    def test_default_stop_is_normal_completion(self, tmp_path: Path) -> None:
        """Call sites without an explicit reason mean a normal completion."""
        config = _make_config(tmp_path, "TEST-REASON-DEFAULT")
        runner = PaperSessionRunner(config)
        runner.start()
        runner.stop()

        stopped = [
            ev
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert stopped[0].payload["reason"] == "NORMAL_COMPLETION"

    def test_session_stopped_rejects_invalid_reason_fail_closed(
        self, tmp_path: Path
    ) -> None:
        """An unknown terminal reason is a DataContractError, never defaulted."""
        journal = PaperEventJournal(
            session_id="TEST-REASON-INVALID",
            persistence_path=tmp_path / "TEST-REASON-INVALID.journal.jsonl",
        )
        monitor = PaperHealthMonitor(
            journal=journal,
            session_id="TEST-REASON-INVALID",
            component_version="0.1.0-test",
        )
        with pytest.raises(DataContractError, match="invalid terminal reason"):
            monitor.session_stopped(
                correlation_id=journal.new_correlation_id(),
                reason="NORMAL_SHUTDOWN",  # type: ignore[arg-type]  # legacy H01 value
                final_event_count=0,
            )

    def test_tournament_feed_disconnect_halt_records_feed_reason(
        self, tmp_path: Path
    ) -> None:
        """Supervisor halt through record_feed_disconnect -> SESSION_STOPPED FEED_DISCONNECTED."""
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        )
        supervisor.start()

        base = datetime(2026, 9, 14, 12, tzinfo=timezone.utc)
        for i in range(1, 6):
            supervisor.process_bar(_make_bar(str(50000.0 + i * 10), i, base))

        supervisor.record_feed_disconnect("Simulated provider disconnect")

        runner = supervisor.slots["A"].runner
        assert runner is not None
        stopped = [
            ev
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert stopped, "halt must seal all active slot journals"
        assert stopped[0].payload["reason"] == "FEED_DISCONNECTED"

    def test_tournament_operator_halt_records_operator_reason(
        self, tmp_path: Path
    ) -> None:
        """Explicit operator halt -> OPERATOR_STOP, not a fabricated NORMAL_SHUTDOWN."""
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        )
        supervisor.start()

        base = datetime(2026, 9, 14, 12, tzinfo=timezone.utc)
        for i in range(1, 6):
            supervisor.process_bar(_make_bar(str(50000.0 + i * 10), i, base))

        supervisor.halt(
            "Tournament shutdown complete",
            terminal_reason=TerminalReason.OPERATOR_STOP,
        )

        runner = supervisor.slots["A"].runner
        assert runner is not None
        stopped = [
            ev
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.SESSION_STOPPED
        ]
        assert stopped[0].payload["reason"] == "OPERATOR_STOP"