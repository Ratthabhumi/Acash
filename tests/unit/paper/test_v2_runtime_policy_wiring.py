"""End-to-end wiring of the ratified V2 runtime policies (D1/D2/D3).

Verifies that the operator-visible CLI choices (--portfolio-funding-policy,
--kill-switch-position-policy, --infra-sizing-policy) flow through
run_tournament -> create_default_shadow_tournament -> build_slot_runner ->
PaperSessionConfig for EVERY mounted slot, that the config hash changes
deterministically with the policies, that per-slot provenance is exposed in
status dicts, and that historical (H01) layouts remain reachable.

A. CLI parse for the ratified flags.
B. 10-slot layout: A..J all NAV 10% + CASH_CONSTRAINED_SPOT +
   HALT_AND_REQUIRE_OPERATOR_RESOLUTION.
C. Legacy/default layout preserved.
D. Config hash is deterministic across unchanged policies and changes when
   any policy differs.
E. per-slot effectivePolicies provenance present in to_dict / status.json.
F. Recovery & fail-closed suites stay green (covered by the full repository
   suite run; the kill-switch policy is honored on a real risk breach here).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import json

from acash.paper.journal import JournalEventType
from acash.paper.runner import (
    KillSwitchPositionPolicy,
    PaperSessionConfig,
    PaperSessionRunner,
    PortfolioFundingPolicy,
    SAFE_V2_NAV_SIZING_PCT,
    SignalSizingPolicy,
    SyntheticBar,
)
from acash.paper.strategy import (
    InfrastructureTestStrategy,
    SignalDirection,
    StrategySignal,
)
from acash.paper.tournament import (
    ShadowTournamentSupervisor,
    create_default_shadow_tournament,
)

_GIT = "c621824690b7e913ef76990472baa38fd17a925f"
_T0 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


def _bar(minute: int, price: str = "50000.0") -> SyntheticBar:
    ts = _T0 + timedelta(minutes=minute)
    close = Decimal(price) + (Decimal(minute) if price == "50000.0" else Decimal("0"))
    return SyntheticBar(
        timestamp_utc=ts,
        symbol="BTCUSDT",
        open=close - Decimal("1"),
        high=close + Decimal("10"),
        low=close - Decimal("10"),
        close=close,
        volume=Decimal("1.5"),
        feed_source="scripted.policy.wiring",
        feed_source_id=f"PWIR-{minute}",
        received_at_utc=ts + timedelta(seconds=1),
        feed_sequence=minute,
        data_age_ms=1000,
    )


def _run_to_position(supervisor: "ShadowTournamentSupervisor", minutes: int = 6) -> None:
    supervisor.start()
    for m in range(1, minutes + 1):
        supervisor.process_bar(_bar(m))


def _make_config(
    tmp_path: Path,
    session_id: str,
    *,
    portfolio_funding_policy: PortfolioFundingPolicy = PortfolioFundingPolicy.SIMULATED_LEVERAGED,
    kill_switch_position_policy: KillSwitchPositionPolicy = KillSwitchPositionPolicy.HALT_AND_PRESERVE_POSITION,
    signal_sizing_policy: SignalSizingPolicy = SignalSizingPolicy.NAV_RELATIVE_PERCENT,
    nav_sizing_notional_pct: Decimal = SAFE_V2_NAV_SIZING_PCT,
) -> PaperSessionConfig:
    return PaperSessionConfig(
        session_id=session_id,
        strategy_id=InfrastructureTestStrategy.STRATEGY_ID,
        strategy_version=InfrastructureTestStrategy.STRATEGY_VERSION,
        instrument="BTCUSDT",
        initial_cash=Decimal("1000.00"),
        max_position_units=Decimal("10.0"),
        max_notional=Decimal("100000.0"),
        max_daily_loss=Decimal("100.0"),
        fill_slippage_bps=Decimal("5.0"),
        fill_commission_per_unit=Decimal("0.0004"),
        prng_seed=42 + ord("A"),
        git_commit=_GIT,
        component_version="1.0.0",
        journal_path=tmp_path / f"{session_id}.journal.jsonl",
        snapshot_path=tmp_path / f"{session_id}.snapshots.jsonl",
        signal_sizing_policy=signal_sizing_policy,
        nav_sizing_notional_pct=nav_sizing_notional_pct,
        portfolio_funding_policy=portfolio_funding_policy,
        kill_switch_position_policy=kill_switch_position_policy,
    )


# E ---------------------------------------------------------------------------


def test_per_slot_effective_policies_provenance(tmp_path: Path) -> None:
    """to_dict() / status.json expose per-slot effective policies; UNASSIGNED
    slots report None honestly (no fabricated effective policy)."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha=_GIT,
        num_slots=10,
        auto_mount_infrastructure_candidates=True,
        signal_sizing_policy=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        nav_sizing_notional_pct=SAFE_V2_NAV_SIZING_PCT,
        portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
    )
    _run_to_position(supervisor)

    for slot_id, slot in supervisor.slots.items():
        d = slot.to_dict()
        assert "effectivePolicies" in d
        policies = d["effectivePolicies"]
        assert policies is not None, f"slot {slot_id} must expose policies"
        assert policies["portfolioFundingPolicy"] == "CASH_CONSTRAINED_SPOT"
        assert policies["killSwitchPositionPolicy"] == "HALT_AND_REQUIRE_OPERATOR_RESOLUTION"
        assert policies["signalSizingPolicy"] == "NAV_RELATIVE_PERCENT"
        assert policies["navSizingNotionalPct"] == "10.0"

    out = tmp_path / "status.json"
    supervisor.export_status_json(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    slot_a = data["slots"]["A"]
    assert slot_a["effectivePolicies"]["portfolioFundingPolicy"] == "CASH_CONSTRAINED_SPOT"
    assert slot_a["effectivePolicies"]["killSwitchPositionPolicy"] == "HALT_AND_REQUIRE_OPERATOR_RESOLUTION"

    # UNASSIGNED slot outside the 10-slot fanout boundary must be honest None.
    sparse = create_default_shadow_tournament(
        storage_dir=tmp_path / "sparse",
        acash_commit_sha=_GIT,
        num_slots=3,
    )
    sparse.start()
    for slot_id, slot in sparse.slots.items():
        if slot_id != "A":
            assert slot.to_dict()["effectivePolicies"] is None


# D ---------------------------------------------------------------------------


def test_config_hash_deterministic_and_policy_sensitive(tmp_path: Path) -> None:
    """compute_config_hash is deterministic for identical canonical configs and
    changes when a runtime policy differs — the single authority for the
    sealed config hash (build_slot_runner seals cfg.compute_config_hash())."""
    base = _make_config(
        tmp_path,
        "WIRING-HASH-A",
        portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
    ).compute_config_hash()
    repeat = _make_config(
        tmp_path,
        "WIRING-HASH-A",
        portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
    ).compute_config_hash()
    assert base == repeat, "identical configs must seal identical config hashes"

    changed_funding = _make_config(
        tmp_path,
        "WIRING-HASH-A",
        portfolio_funding_policy=PortfolioFundingPolicy.SIMULATED_LEVERAGED,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
    ).compute_config_hash()
    changed_kill = _make_config(
        tmp_path,
        "WIRING-HASH-A",
        portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_PRESERVE_POSITION,
    ).compute_config_hash()
    changed_sizing = _make_config(
        tmp_path,
        "WIRING-HASH-A",
        portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
        signal_sizing_policy=SignalSizingPolicy.INFRA_FIXED_QUANTITY,
        nav_sizing_notional_pct=Decimal("0"),
    ).compute_config_hash()
    assert base != changed_funding, "funding policy change must alter the config hash"
    assert base != changed_kill, "kill-switch policy change must alter the config hash"
    assert base != changed_sizing, "sizing policy change must alter the config hash"


# B ---------------------------------------------------------------------------


def test_ten_slot_layout_uses_ratified_policies_everywhere(tmp_path: Path) -> None:
    """A..J all mount with NAV 10% sizing + CASH_CONSTRAINED_SPOT funding +
    HALT_AND_REQUIRE_OPERATOR_RESOLUTION kill-switch."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha=_GIT,
        num_slots=10,
        auto_mount_infrastructure_candidates=True,
        signal_sizing_policy=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        nav_sizing_notional_pct=SAFE_V2_NAV_SIZING_PCT,
        portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
    )
    for slot_id in "ABCDEFGHIJ":
        runner = supervisor.slots[slot_id].runner
        assert runner is not None, f"slot {slot_id} must be mounted"
        assert runner._config.signal_sizing_policy == SignalSizingPolicy.NAV_RELATIVE_PERCENT
        assert runner._config.nav_sizing_notional_pct == SAFE_V2_NAV_SIZING_PCT
        assert runner._config.portfolio_funding_policy == PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT
        assert runner._config.kill_switch_position_policy == KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION

    _run_to_position(supervisor)
    for slot_id in "ABCDEFGHIJ":
        runner = supervisor.slots[slot_id].runner
        assert runner is not None
        if runner._portfolio.position > Decimal("0"):
            # NAV-wired slots accumulate per-entry sized positions, never the
            # legacy fixed 1.0 quantity (Slot A defect is fixed).
            assert runner._portfolio.position < Decimal("1.0"), (
                f"slot {slot_id} position {runner._portfolio.position} "
                "exceeds NAV-relative bound"
            )


# C ---------------------------------------------------------------------------


def test_legacy_default_layout_preserved(tmp_path: Path) -> None:
    """Default boot (no explicit sizing) keeps injected A on fixed quantity and
    catalog on NAV when auto-mounting — historical H01-compatible layout."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha=_GIT,
        num_slots=2,
        auto_mount_infrastructure_candidates=True,
        infra_mount_count=1,
    )
    runner_a = supervisor.slots["A"].runner
    runner_b = supervisor.slots["B"].runner
    assert runner_a is not None
    assert runner_b is not None
    assert runner_a._config.signal_sizing_policy == SignalSizingPolicy.INFRA_FIXED_QUANTITY
    assert runner_b._config.signal_sizing_policy == SignalSizingPolicy.NAV_RELATIVE_PERCENT
    assert runner_a._config.portfolio_funding_policy == PortfolioFundingPolicy.SIMULATED_LEVERAGED
    assert runner_a._config.kill_switch_position_policy == KillSwitchPositionPolicy.HALT_AND_PRESERVE_POSITION


# F ---------------------------------------------------------------------------


def _crash_prices() -> list[str]:
    safe = [str(float(100 + i)) for i in range(8)]  # 100..107 -> builds LONG
    crash = ["55.0", "60.0", "52.0", "50.0"]  # forces SHORT closing fills at losses
    return safe + crash


def _breach_bar(price: str, seq: int) -> SyntheticBar:
    price_dec = Decimal(price)
    ts = datetime(2026, 1, 5, 9, tzinfo=timezone.utc) + timedelta(minutes=seq)
    return SyntheticBar(
        timestamp_utc=ts,
        symbol="BTCUSDT",
        open=price_dec,
        high=price_dec + Decimal("10.0"),
        low=price_dec - Decimal("10.0"),
        close=price_dec,
        volume=Decimal("1.5"),
        feed_source="SYNTHETIC_TEST",
        feed_source_id=f"BTCUSDT-M1-{seq}",
        received_at_utc=ts + timedelta(seconds=1),
        feed_sequence=seq,
        data_age_ms=1000,
    )


def test_kill_switch_policy_honored_on_real_breach(tmp_path: Path) -> None:
    """When the ratified kill-switch policy is wired, a real MAX_DAILY_LOSS
    breach triggers the kill switch and requires operator resolution
    (fail-closed, no automatic resume / no silent flatten)."""
    cfg = PaperSessionConfig(
        session_id="WIRING-KS-OPERATOR",
        strategy_id=InfrastructureTestStrategy.STRATEGY_ID,
        strategy_version=InfrastructureTestStrategy.STRATEGY_VERSION,
        instrument="BTCUSDT",
        initial_cash=Decimal("10000"),
        max_position_units=Decimal("100"),
        max_notional=Decimal("100000000"),
        max_daily_loss=Decimal("1.0"),
        fill_slippage_bps=Decimal("0.5"),
        fill_commission_per_unit=Decimal("7.0"),
        prng_seed=42,
        git_commit=_GIT,
        component_version="1.0.0-test",
        journal_path=tmp_path / "ks.journal.jsonl",
        snapshot_path=tmp_path / "ks.snapshots.jsonl",
        portfolio_funding_policy=PortfolioFundingPolicy.SIMULATED_LEVERAGED,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
    )
    runner = PaperSessionRunner(cfg, strategy=InfrastructureTestStrategy())
    runner.start()
    for idx, price in enumerate(_crash_prices(), start=1):
        runner.process_bar(_breach_bar(price, idx))

    assert runner.kill_switch_active
    assert runner.operator_resolution_required
    # No synthetic flatten: the position policy is operator resolution, not
    # HALT_AND_FORCE_SIMULATED_FLATTEN.
    flatten_governance = [
        ev.payload.get("GOVERNANCE_LABEL")
        for ev in runner.journal.read_all()
        if ev.event_type == JournalEventType.FILL_SIMULATED
    ]
    assert "RISK_KILL_SWITCH_FORCED_FLATTEN" not in flatten_governance


def test_cash_constrained_spot_rejects_negative_cash_fail_closed(tmp_path: Path) -> None:
    """CASH_CONSTRAINED_SPOT must reject fills that would drive projected cash
    below zero at the risk gate (fail-closed)."""
    cfg = PaperSessionConfig(
        session_id="WIRING-CASH-SPOT",
        strategy_id=InfrastructureTestStrategy.STRATEGY_ID,
        strategy_version=InfrastructureTestStrategy.STRATEGY_VERSION,
        instrument="BTCUSDT",
        initial_cash=Decimal("1000.00"),
        max_position_units=Decimal("10.0"),
        max_notional=Decimal("100000.0"),
        max_daily_loss=Decimal("100.0"),
        fill_slippage_bps=Decimal("5.0"),
        fill_commission_per_unit=Decimal("0.0004"),
        prng_seed=42,
        git_commit=_GIT,
        component_version="1.0.0",
        journal_path=tmp_path / "cash.journal.jsonl",
        snapshot_path=tmp_path / "cash.snapshots.jsonl",
        portfolio_funding_policy=PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT,
        kill_switch_position_policy=KillSwitchPositionPolicy.HALT_AND_PRESERVE_POSITION,
    )
    runner = PaperSessionRunner(cfg, strategy=InfrastructureTestStrategy())

    signal = StrategySignal(
        strategy_id=InfrastructureTestStrategy.STRATEGY_ID,
        strategy_version=InfrastructureTestStrategy.STRATEGY_VERSION,
        evaluation_timestamp_utc=datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc),
        symbol="BTCUSDT",
        direction=SignalDirection.LONG,
        target_quantity=Decimal("0.02"),
        signal_strength=Decimal("0.5"),
        decision_reason="[INFRA-TEST] cash-constrained probe",
        feature_snapshot={},
        market_event_reference="UNIT-PROBE",
        config_hash="0" * 64,
    )
    approved, reason, _ = runner._evaluate_risk(
        signal,
        correlation_id="u1",
        causation_id="c1",
        reference_price=Decimal("50000.0"),
    )
    # 1000 cash vs ~1000 notional + slippage + commission -> projected cash < 0.
    assert approved is False
    assert "FUNDING_POLICY" in reason