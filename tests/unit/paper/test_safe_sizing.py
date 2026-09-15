"""Safe NAV-relative signal sizing (V2 follow-up).

Target order of tests (AGENTS.md principle 14): happy path -> boundary ->
malformed -> contradictory -> numerical stability -> golden reference.
"""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.paper.runner import (
    SAFE_V2_NAV_SIZING_PCT,
    PaperSessionConfig,
    PaperSessionRunner,
    SignalSizingPolicy,
    SyntheticBar,
)
from acash.paper.strategy import (
    InfrastructureTestStrategy,
    SignalDirection,
    StrategySignal,
)
from acash.paper.tournament import create_default_shadow_tournament

_GIT = "a11995373bcb293135374e8c7dce6091963fea4a"
_ZERO_HASH = "0" * 64


def _cfg(
    tmp_path: Path,
    *,
    sizing: SignalSizingPolicy = SignalSizingPolicy.INFRA_FIXED_QUANTITY,
    pct: Decimal = Decimal("0"),
) -> PaperSessionConfig:
    return PaperSessionConfig(
        session_id="SIZING-TEST-SLOT-A",
        strategy_id="INFRA-TEST-MOMENTUM-SYNTHETIC-001",
        strategy_version="1.0.0",
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
        journal_path=tmp_path / "j.jsonl",
        snapshot_path=tmp_path / "s.jsonl",
        data_source="binance.public.klines",
        market_domain="SPOT",
        max_market_data_age_ms=65_000,
        signal_sizing_policy=sizing,
        nav_sizing_notional_pct=pct,
    )


def _bars(count: int, base: Decimal = Decimal("50000")) -> List[SyntheticBar]:
    out: List[SyntheticBar] = []
    for i in range(1, count + 1):
        p = base + Decimal(i)
        out.append(
            SyntheticBar(
                timestamp_utc=datetime(2026, 9, 14, 12, i, tzinfo=timezone.utc),
                symbol="BTCUSDT",
                open=p,
                high=p + Decimal("1.0"),
                low=p - Decimal("1.0"),
                close=p,
                volume=Decimal("1.5"),
                feed_source="BINANCE_PUBLIC_KLINES",
                feed_source_id=f"B{i}",
                received_at_utc=datetime(2026, 9, 14, 12, i, 1, tzinfo=timezone.utc),
                feed_sequence=i,
                data_age_ms=1000,
            )
        )
    return out


def _long_signal() -> StrategySignal:
    return StrategySignal(
        strategy_id="INFRA-TEST-MOMENTUM-SYNTHETIC-001",
        strategy_version="1.0.0",
        evaluation_timestamp_utc=datetime(2026, 9, 14, 12, 59, tzinfo=timezone.utc),
        symbol="BTCUSDT",
        direction=SignalDirection.LONG,
        target_quantity=Decimal("1.0"),
        signal_strength=Decimal("0.5"),
        decision_reason="[INFRA-TEST] unit sizing probe",
        feature_snapshot={},
        market_event_reference="UNIT-PROBE",
        config_hash=_ZERO_HASH,
    )


def _runner(tmp_path: Path, *, sizing: SignalSizingPolicy, pct: Decimal) -> PaperSessionRunner:
    cfg = _cfg(tmp_path, sizing=sizing, pct=pct)
    strategy = InfrastructureTestStrategy(symbol="BTCUSDT", trade_quantity=Decimal("1.0"))
    return PaperSessionRunner(cfg, strategy=strategy)


def test_nav_relative_quantity_derivation_golden(tmp_path: Path) -> None:
    runner = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    runner._portfolio.cash = Decimal("1000.00")
    runner._portfolio.position = Decimal("0")
    exec_signal, meta = runner._apply_signal_sizing(
        _long_signal(), reference_price=Decimal("50000")
    )
    # Golden reference: target_notional = 1000 * 0.10 = 100; qty = 100/50000.
    assert exec_signal.target_quantity == Decimal("0.00200000")
    assert meta["signal_sizing_policy"] == "NAV_RELATIVE_PERCENT"
    assert meta["sizing_output_quantity"] == "0.00200000"


def test_quantization_rounds_down_never_up(tmp_path: Path) -> None:
    runner = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    runner._portfolio.cash = Decimal("1000.00")
    runner._portfolio.position = Decimal("0")
    exec_signal, _ = runner._apply_signal_sizing(_long_signal(), reference_price=Decimal("3"))
    raw = Decimal("100") / Decimal("3")
    expected = raw.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    assert exec_signal.target_quantity == expected
    assert exec_signal.target_quantity < raw  # strictly floor, never rounding up


def test_flat_signal_bypasses_sizing(tmp_path: Path) -> None:
    runner = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    flat = StrategySignal(
        strategy_id="INFRA-TEST-MOMENTUM-SYNTHETIC-001",
        strategy_version="1.0.0",
        evaluation_timestamp_utc=datetime(2026, 9, 14, 12, 59, tzinfo=timezone.utc),
        symbol="BTCUSDT",
        direction=SignalDirection.FLAT,
        target_quantity=Decimal("0"),
        signal_strength=Decimal("0"),
        decision_reason="unit probe",
        feature_snapshot={},
        market_event_reference="UNIT-PROBE",
        config_hash=_ZERO_HASH,
    )
    exec_signal, meta = runner._apply_signal_sizing(flat, reference_price=Decimal("50000"))
    assert exec_signal is flat
    assert exec_signal.target_quantity == Decimal("0")
    assert meta["sizing_output_quantity"] == "0"


def test_infra_fixed_passthrough_meta(tmp_path: Path) -> None:
    runner = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.INFRA_FIXED_QUANTITY,
        pct=Decimal("0"),
    )
    exec_signal, meta = runner._apply_signal_sizing(
        _long_signal(), reference_price=Decimal("50000")
    )
    assert exec_signal is _long_signal() or exec_signal.target_quantity == Decimal("1.0")
    assert meta["signal_sizing_policy"] == "INFRA_FIXED_QUANTITY"
    assert meta["sizing_output_quantity"] == "1.0"


def test_zero_reference_price_raises_fail_closed(tmp_path: Path) -> None:
    runner = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    with pytest.raises(DataContractError):
        runner._apply_signal_sizing(_long_signal(), reference_price=Decimal("0"))


def test_negative_reference_price_raises_fail_closed(tmp_path: Path) -> None:
    runner = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    with pytest.raises(DataContractError):
        runner._apply_signal_sizing(_long_signal(), reference_price=Decimal("-1"))


def test_non_positive_equity_raises_fail_closed(tmp_path: Path) -> None:
    runner = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    runner._portfolio.cash = Decimal("0.00")
    runner._portfolio.position = Decimal("0")
    with pytest.raises(DataContractError):
        runner._apply_signal_sizing(_long_signal(), reference_price=Decimal("50000"))


def test_zero_quantity_rejected_by_risk_gate(tmp_path: Path) -> None:
    """A sized quantity <= 0 must be REJECTED, never silently floored."""
    sized = _long_signal()
    zero_sized = StrategySignal(
        strategy_id=sized.strategy_id,
        strategy_version=sized.strategy_version,
        evaluation_timestamp_utc=sized.evaluation_timestamp_utc,
        symbol=sized.symbol,
        direction=SignalDirection.LONG,
        target_quantity=Decimal("0.00000000"),
        signal_strength=sized.signal_strength,
        decision_reason=sized.decision_reason,
        feature_snapshot={},
        market_event_reference=sized.market_event_reference,
        config_hash=_ZERO_HASH,
    )
    approved, reason, _ = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )._evaluate_risk(
        zero_sized,
        correlation_id="u1",
        causation_id="c1",
        reference_price=Decimal("50000"),
        sizing_meta={"sizing_output_quantity": "0.00000000"},
    )
    assert approved is False
    assert "SIZING" in reason


def test_config_rejects_nav_with_zero_pct(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        _cfg(tmp_path, sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT, pct=Decimal("0"))


def test_config_rejects_nav_with_pct_over_100(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        _cfg(tmp_path, sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT, pct=Decimal("150"))


def test_config_rejects_fixed_with_nonzero_pct_dead_config(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        _cfg(
            tmp_path,
            sizing=SignalSizingPolicy.INFRA_FIXED_QUANTITY,
            pct=SAFE_V2_NAV_SIZING_PCT,
        )


def test_compute_config_hash_back_compat(tmp_path: Path) -> None:
    legacy = _cfg(tmp_path)
    explicit_default = _cfg(
        tmp_path, sizing=SignalSizingPolicy.INFRA_FIXED_QUANTITY, pct=Decimal("0")
    )
    nav = _cfg(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    assert legacy.compute_config_hash() == explicit_default.compute_config_hash()
    assert legacy.compute_config_hash() != nav.compute_config_hash()


def test_session_started_metadata_seal_only_when_non_default(tmp_path: Path) -> None:
    fixed_runner = _runner(
        tmp_path / "fixed",
        sizing=SignalSizingPolicy.INFRA_FIXED_QUANTITY,
        pct=Decimal("0"),
    )
    nav_runner = _runner(
        tmp_path / "nav",
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    (tmp_path / "fixed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "nav").mkdir(parents=True, exist_ok=True)
    fixed_runner.start()
    nav_runner.start()
    fixed_start = next(
        e
        for e in fixed_runner.journal.read_all()
        if e.event_type.value == "SESSION_STARTED"
    )
    nav_start = next(
        e
        for e in nav_runner.journal.read_all()
        if e.event_type.value == "SESSION_STARTED"
    )
    assert "signal_sizing_policy" not in fixed_start.payload
    assert "signal_sizing_policy" in nav_start.payload
    assert "nav_sizing_notional_pct" in nav_start.payload
    assert "signal_sizing_policy" not in fixed_runner._sizing_metadata()
    assert "nav_sizing_notional_pct" in nav_runner._sizing_metadata()


def test_end_to_end_nav_sized_position_matches_derivation(tmp_path: Path) -> None:
    """Through the full runner pipeline the first LONG fill is NAV-derived."""
    runner = _runner(
        tmp_path,
        sizing=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        pct=SAFE_V2_NAV_SIZING_PCT,
    )
    runner.start()
    for bar in _bars(5):
        runner.process_bar(bar)
    if runner._portfolio.position == Decimal("0"):
        runner.process_bar(_bars(6)[5])
    assert runner._portfolio.position > Decimal("0")
    assert runner._portfolio.position <= Decimal("0.00200000") + Decimal("0.0001")


def test_tournament_canonical_a_keeps_fixed_quantity_under_nav_policy(tmp_path: Path) -> None:
    """Injected/canonical Slot A stays legacy-fixed even when the tournament
    resolves a NAV-relative policy for auto-mounted catalog candidates."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha=_GIT,
        num_slots=2,
        auto_mount_infrastructure_candidates=True,
        infra_mount_count=1,  # only B from the catalog
        signal_sizing_policy=SignalSizingPolicy.NAV_RELATIVE_PERCENT,
        nav_sizing_notional_pct=SAFE_V2_NAV_SIZING_PCT,
    )
    supervisor.start()
    for bar in _bars(6):
        supervisor.process_bar(bar)
    slot_a = supervisor.to_dict()["slots"]["A"]
    assert slot_a["strategyId"] == "INFRA-TEST-MOMENTUM-SYNTHETIC-001"
    assert slot_a["observationKind"] == "CONTINUOUS"

    # A runs the canonical fixed 1.0 quantity; B is catalog NAV-sized.
    runner_a = supervisor._slots["A"].runner
    runner_b = supervisor._slots["B"].runner
    assert runner_a is not None
    assert runner_b is not None
    if runner_a._portfolio.position > Decimal("0"):
        assert runner_a._portfolio.position >= Decimal("1.0")
    if runner_b._portfolio.position > Decimal("0"):
        assert runner_b._portfolio.position <= Decimal("0.0021")


def test_infra_mount_count_dead_config_rejected(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha=_GIT,
            num_slots=3,
            auto_mount_infrastructure_candidates=False,
            infra_mount_count=3,
        )


def test_infra_mount_count_out_of_range_rejected(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha=_GIT,
            num_slots=3,
            auto_mount_infrastructure_candidates=True,
            infra_mount_count=9,
        )
    with pytest.raises(DataContractError):
        create_default_shadow_tournament(
            storage_dir=tmp_path,
            acash_commit_sha=_GIT,
            num_slots=3,
            auto_mount_infrastructure_candidates=True,
            infra_mount_count=0,
        )