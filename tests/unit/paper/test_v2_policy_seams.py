"""Regression tests — Tournament V2 Execution-Risk Policy Seams (Defects B, C, D).

Pins the H01-derived defects from docs/SESSION_HANDOFF.md:

- Defect B (no portfolio funding policy seam): a config-sealed
  PortfolioFundingPolicy gates projected cash at the risk layer:
  SIMULATED_LEVERAGED preserves H01 accounting; CASH_CONSTRAINED_SPOT rejects
  fills that drive cash below zero; EXPLICIT_BOUNDED_LEVERAGE enforces an
  explicit debt limit. The policy is part of the canonical config hash.
- Defect C (no kill-switch position policy): KillSwitchPositionPolicy decides
  what happens to the open position on a MAX_DAILY_LOSS kill switch — preserve,
  force a simulated flatten at mark, or require an operator resolution.
- Defect D (execution states not propagated): the runner kill switch must
  surface as slot RISK_HALTED, feed halts as FEED_HALTED, operator stops as
  STOPPED; the aggregate execution state is exposed in status JSON and metrics.

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
from acash.paper.journal import JournalEventType
from acash.paper.metrics import MetricsRegistry
from acash.paper.runner import (
    KillSwitchPositionPolicy,
    PaperSessionConfig,
    PaperSessionRunner,
    PortfolioFundingPolicy,
    SyntheticBar,
)
from acash.paper.strategy import InfrastructureTestStrategy
from acash.paper.tournament import (
    SlotExecutionState,
    create_default_shadow_tournament,
)

STRATEGY = InfrastructureTestStrategy


def _make_config(
    tmp_path: Path,
    session_id: str,
    *,
    initial_cash: Decimal = Decimal("10000"),
    max_position_units: Decimal = Decimal("100"),
    max_notional: Decimal = Decimal("100000000"),
    max_daily_loss: Decimal = Decimal("1.0"),
    trade_quantity: Decimal = Decimal("1.0"),
    portfolio_funding_policy: PortfolioFundingPolicy = PortfolioFundingPolicy.SIMULATED_LEVERAGED,
    max_debt_limit_usd: Decimal = Decimal("0"),
    kill_switch_position_policy: KillSwitchPositionPolicy = KillSwitchPositionPolicy.HALT_AND_PRESERVE_POSITION,
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
        portfolio_funding_policy=portfolio_funding_policy,
        max_debt_limit_usd=max_debt_limit_usd,
        kill_switch_position_policy=kill_switch_position_policy,
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
# Defect B — PortfolioFundingPolicy gate
# ---------------------------------------------------------------------------


class TestPortfolioFundingPolicy:
    def test_simulated_leveraged_permits_negative_cash(self, tmp_path: Path) -> None:
        """H01-preserving default: cash may draw negative without a funding block."""
        config = _make_config(
            tmp_path,
            "TEST-FUNDING-SIM-LEV",
            initial_cash=Decimal("1000"),
            max_notional=Decimal("100000"),
        )
        runner = PaperSessionRunner(config)
        runner.start()

        # Rising prices -> persistent LONG of 1.0/bar at ~4900+ (notional builds).
        prices = [str(float(4900 + i * 10)) for i in range(8)]
        for idx, price in enumerate(prices, start=1):
            runner.process_bar(_make_bar(price, idx, datetime(2026, 1, 5, 9, tzinfo=timezone.utc)))

        rejected = [
            ev.payload
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.RISK_REJECTED
        ]
        # Notional cap (100000) never breached at ~5k/unit; funding gate inert.
        assert not any("FUNDING_POLICY" in " ".join(ev.get("violations", [])) for ev in rejected)
        assert runner._portfolio.cash < Decimal("0"), "simulated leverage legacy allows negative cash"

    def test_cash_constrained_spot_rejects_negative_projected_cash(
        self, tmp_path: Path
    ) -> None:
        """CASH_CONSTRAINED_SPOT rejects the fill whose projected cash goes negative."""
        config = _make_config(
            tmp_path,
            "TEST-FUNDING-CASH-SPOT",
            initial_cash=Decimal("10000"),
            portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        )
        runner = PaperSessionRunner(config)
        runner.start()

        base = datetime(2026, 1, 5, 9, tzinfo=timezone.utc)
        for idx, price in enumerate(
            ["5000.0", "5100.0", "5200.0", "5300.0", "5400.0", "5500.0"], start=1
        ):
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

        # ~5k fills: cash (10k) bounds the second purchase -> transient rejections.
        assert rejected, "cash-constrained spot must reject an over-leveraged fill"
        assert any("FUNDING_POLICY" in " ".join(ev.get("violations", [])) for ev in rejected)
        # Every accepted fill keeps cumulative cash >= 0.
        assert runner._portfolio.cash >= Decimal("0"), "spot cash must never go negative"

    def test_explicit_bounded_leverage_enforces_debt_floor(self, tmp_path: Path) -> None:
        """EXPLICIT_BOUNDED_LEVERAGE allows debt up to max_debt_limit_usd, then rejects."""
        config = _make_config(
            tmp_path,
            "TEST-FUNDING-BOUNDED-LEV",
            initial_cash=Decimal("10000"),
            portfolio_funding_policy=PortfolioFundingPolicy.EXPLICIT_BOUNDED_LEVERAGE,
            max_debt_limit_usd=Decimal("5000"),
        )
        runner = PaperSessionRunner(config)
        runner.start()

        base = datetime(2026, 1, 5, 9, tzinfo=timezone.utc)
        prices = [str(float(5000 + i * 10)) for i in range(10)]
        for idx, price in enumerate(prices, start=1):
            runner.process_bar(_make_bar(price, idx, base))

        rejected = [
            ev.payload
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.RISK_REJECTED
        ]
        assert rejected, "bounded leverage must eventually reject a breach"
        assert any("FUNDING_POLICY" in " ".join(ev.get("violations", [])) for ev in rejected)
        assert runner._portfolio.cash >= -config.max_debt_limit_usd

    def test_funding_policy_is_part_of_config_hash(self, tmp_path: Path) -> None:
        """Policy and debt limit are cryptographically sealed in config hash."""
        cfg_a = _make_config(
            tmp_path,
            "TEST-FUNDING-HASH-A",
            portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        )
        cfg_b = _make_config(
            tmp_path,
            "TEST-FUNDING-HASH-B",
            portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
            max_debt_limit_usd=Decimal("100"),
        )
        cfg_c = _make_config(
            tmp_path,
            "TEST-FUNDING-HASH-C",
            portfolio_funding_policy=PortfolioFundingPolicy.SIMULATED_LEVERAGED,
        )
        assert cfg_a.compute_config_hash() != cfg_b.compute_config_hash()
        assert cfg_a.compute_config_hash() != cfg_c.compute_config_hash()

    def test_negative_debt_limit_is_config_contract_violation(self, tmp_path: Path) -> None:
        """A negative debt limit must be fail-closed by the config itself."""
        with pytest.raises(DataContractError, match="max_debt_limit_usd"):
            _make_config(
                tmp_path,
                "TEST-FUNDING-NEG-DEBT",
                portfolio_funding_policy=PortfolioFundingPolicy.EXPLICIT_BOUNDED_LEVERAGE,
                max_debt_limit_usd=Decimal("-1"),
            )


# ---------------------------------------------------------------------------
# Defect C — KillSwitchPositionPolicy
# ---------------------------------------------------------------------------

# Crafted rising-then-crashing price path that produces a realized loss larger
# than max_daily_loss=1.0 on the first closing fill and triggers the kill switch.
def _crash_prices() -> list[str]:
    safe = [str(float(100 + i)) for i in range(8)]  # 100..107 -> builds LONG
    crash = ["55.0", "60.0", "52.0", "50.0"]  # forces SHORT closing fills at losses
    return safe + crash


def _trigger_kill_switch(runner: PaperSessionRunner, base: datetime) -> None:
    for idx, price in enumerate(_crash_prices(), start=1):
        runner.process_bar(_make_bar(price, idx, base))


class TestKillSwitchPositionPolicy:
    def test_default_preserves_position_on_kill_switch(self, tmp_path: Path) -> None:
        config = _make_config(
            tmp_path,
            "TEST-KILLSWITCH-PRESERVE",
            max_daily_loss=Decimal("1.0"),
            kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_PRESERVE_POSITION,
        )
        runner = PaperSessionRunner(config)
        runner.start()
        base = datetime(2026, 1, 5, 9, tzinfo=timezone.utc)
        _trigger_kill_switch(runner, base)

        assert runner.kill_switch_active
        assert not runner.operator_resolution_required
        # Position is preserved (no synthetic flatten chain).
        flatten_governance = [
            ev.payload.get("GOVERNANCE_LABEL")
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.FILL_SIMULATED
        ]
        assert "RISK_KILL_SWITCH_FORCED_FLATTEN" not in flatten_governance

    def test_force_flatten_closes_position_on_kill_switch(self, tmp_path: Path) -> None:
        config = _make_config(
            tmp_path,
            "TEST-KILLSWITCH-FLATTEN",
            max_daily_loss=Decimal("1.0"),
            kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_FORCE_SIMULATED_FLATTEN,
        )
        runner = PaperSessionRunner(config)
        runner.start()
        base = datetime(2026, 1, 5, 9, tzinfo=timezone.utc)
        _trigger_kill_switch(runner, base)

        assert runner.kill_switch_active
        events = runner.journal.read_all()
        assert runner._portfolio.position == Decimal("0"), "flatten policy must exit to flat"
        flatten_fills = [
            ev.payload
            for ev in events
            if ev.event_type == JournalEventType.FILL_SIMULATED
            and ev.payload.get("GOVERNANCE_LABEL") == "RISK_KILL_SWITCH_FORCED_FLATTEN"
        ]
        assert flatten_fills, "a synthetic closing fill must be journaled"
        # Causal chain: intent precedes (or is equal for the flattened unit to) the fill.
        assert "fill_price" in flatten_fills[0]
        assert "reference_price" in flatten_fills[0]

    def test_require_operator_resolution_sets_flag_without_flatten(
        self, tmp_path: Path
    ) -> None:
        config = _make_config(
            tmp_path,
            "TEST-KILLSWITCH-OPERATOR",
            max_daily_loss=Decimal("1.0"),
            kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
        )
        runner = PaperSessionRunner(config)
        runner.start()
        base = datetime(2026, 1, 5, 9, tzinfo=timezone.utc)
        _trigger_kill_switch(runner, base)

        assert runner.kill_switch_active
        assert runner.operator_resolution_required, "operator resolution flag must be set"
        flatten_fills = [
            ev.payload
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.FILL_SIMULATED
            and ev.payload.get("GOVERNANCE_LABEL") == "RISK_KILL_SWITCH_FORCED_FLATTEN"
        ]
        assert not flatten_fills, "operator-resolution policy must not auto-flatten"

    def test_kill_switch_payload_journals_position_policy(self, tmp_path: Path) -> None:
        config = _make_config(
            tmp_path,
            "TEST-KILLSWITCH-PAYLOAD",
            max_daily_loss=Decimal("1.0"),
            kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
        )
        runner = PaperSessionRunner(config)
        runner.start()
        base = datetime(2026, 1, 5, 9, tzinfo=timezone.utc)
        _trigger_kill_switch(runner, base)

        kswitch = [
            ev.payload
            for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.KILL_SWITCH_TRIGGERED
        ]
        assert kswitch, "kill switch must be journaled"
        assert kswitch[0]["position_policy"] == "HALT_AND_REQUIRE_OPERATOR_RESOLUTION"
        assert kswitch[0]["operator_resolution_required"] is True


# ---------------------------------------------------------------------------
# Defect D — execution-state propagation
# ---------------------------------------------------------------------------


class TestExecutionStatePropagation:
    def test_runner_kill_switch_propagates_risk_halted_slot_state(
        self, tmp_path: Path
    ) -> None:
        """Supervisor slot reflects RUNNING -> RISK_HALTED once the runner hits the kill switch."""
        metrics_registry = MetricsRegistry()
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
            metrics_registry=metrics_registry,
        )

        # Seal a tiny daily-loss ceiling + flatten policy directly on Slot A config.
        runner = supervisor.slots["A"].runner
        assert runner is not None
        new_cfg = _remap_slot_a_config(runner)
        runner._config = new_cfg
        runner._config_hash = new_cfg.compute_config_hash()

        supervisor.start()
        base = datetime(2026, 1, 5, 9, tzinfo=timezone.utc)
        for idx, price in enumerate(_crash_prices(), start=1):
            supervisor.process_bar(_make_bar(price, idx, base))

        assert supervisor.slots["A"].status == SlotExecutionState.RISK_HALTED.value
        assert runner.kill_switch_active
        assert "Kill switch active" in (supervisor.slots["A"].halt_reason or "")

        # Aggregate execution state must reflect the risk halt.
        assert supervisor._aggregate_execution_state() == "RISK_HALTED"

    def test_feed_disconnect_halt_is_feed_halted(self, tmp_path: Path) -> None:
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        )
        supervisor.start()
        for i in range(1, 6):
            supervisor.process_bar(_make_bar(str(50000 + i * 10), i, datetime(2026, 1, 5, 9, tzinfo=timezone.utc)))
        supervisor.record_feed_disconnect("Simulated provider disconnect")

        assert supervisor.slots["A"].status == SlotExecutionState.FEED_HALTED.value
        assert supervisor._aggregate_execution_state() == "FEED_HALTED"

    def test_operator_stop_is_stopped(self, tmp_path: Path) -> None:
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        )
        supervisor.start()
        for i in range(1, 6):
            supervisor.process_bar(_make_bar(str(50000 + i * 10), i, datetime(2026, 1, 5, 9, tzinfo=timezone.utc)))
        supervisor.halt("Tournament shutdown complete")

        assert supervisor.slots["A"].status == SlotExecutionState.STOPPED.value
        assert supervisor._aggregate_execution_state() == "STOPPED"

    def test_execution_state_surfaced_in_status_json(self, tmp_path: Path) -> None:
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        )
        supervisor.start()
        out_json = tmp_path / "status.json"
        supervisor.export_status_json(out_json)

        import json

        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["global"]["executionState"] == SlotExecutionState.RUNNING.value
        assert data["slots"]["A"]["status"] == "RUNNING"
        assert data["slots"]["A"]["operatorResolutionRequired"] is False

    def test_execution_state_metric_gauges(self, tmp_path: Path) -> None:
        registry = MetricsRegistry()
        supervisor = create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
            metrics_registry=registry,
        )
        supervisor.start()
        text = registry.render()
        assert 'acash_shadow_tournament_execution_state{state="RUNNING"} 1.0' in text
        assert 'acash_shadow_tournament_slot_execution_state{slot="A",state="RUNNING"} 1.0' in text
        assert 'acash_shadow_tournament_slot_execution_state{slot="B",state="UNASSIGNED"} 1.0' in text


def _remap_slot_a_config(runner: PaperSessionRunner) -> PaperSessionConfig:
    """Rebuild Slot A's config with a tiny daily-loss ceiling + flatten policy."""
    from dataclasses import replace

    return replace(
        runner._config,
        max_daily_loss=Decimal("1.0"),
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_FORCE_SIMULATED_FLATTEN,
    )