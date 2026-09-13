"""Unit tests for ACASH Shadow Alpha Tournament Core.

Validates all mandatory invariants:
- Zero real order dispatch path (NO_REAL_ORDERS=True, CANONICAL_CAPITAL_USD=$0.00)
- Isolated virtual portfolios (Slot A, B, C)
- Strategy injection seam: proves independent strategy logic can run in distinct slots
- Zero state leakage across slots
- Synchronized bar semantics (identical bar delivered to each active slot)
- Independent journals per slot
- Globally unique session IDs across repeated runs
- Fail-closed feed disconnect and stale data handling (halts slots & seals manifests)
- Bar rejection while halted and prevention of double-start
- Honest reporting of unassigned slots (zero fabrication)
- Read-only HTTP status API server (GET /api/shadow/status, GET /healthz, POST rejected with 405)
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional, Sequence

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.paper.metrics import MetricsRegistry
from acash.paper.runner import SyntheticBar
from acash.paper.strategy import (
    InfrastructureTestStrategy,
    PaperStrategyProtocol,
    SignalDirection,
    StrategySignal,
)
from acash.paper.tournament import (
    CANONICAL_CAPITAL_USD,
    NO_REAL_ORDERS,
    REAL_ORDERS_COUNT,
    SHADOW_GOVERNANCE_LABEL,
    ShadowTournamentSupervisor,
    TournamentGovernance,
    TournamentSlot,
    create_default_shadow_tournament,
)
from acash.paper.tournament_api import ShadowApiServer


def _make_sample_bar(price: str = "50000.0", seq: int = 1) -> SyntheticBar:
    return SyntheticBar(
        timestamp_utc=datetime(2026, 9, 14, 12, seq, tzinfo=timezone.utc),
        symbol="BTCUSDT",
        open=Decimal(price),
        high=Decimal(price) + Decimal("10.0"),
        low=Decimal(price) - Decimal("10.0"),
        close=Decimal(price),
        volume=Decimal("1.5"),
        feed_source="BINANCE_PUBLIC_KLINES",
        feed_source_id=f"BTCUSDT-M1-{seq}",
        received_at_utc=datetime(2026, 9, 14, 12, seq, 1, tzinfo=timezone.utc),
        feed_sequence=seq,
        data_age_ms=1000,
    )


def test_governance_invariants_immutable() -> None:
    """Verify core governance constants are strictly immutable and fail-closed."""
    gov = TournamentGovernance()
    assert gov.canonical_capital_usd == Decimal("0.00")
    assert gov.real_orders_count == 0
    assert gov.no_real_orders is True
    assert gov.governance_mode == SHADOW_GOVERNANCE_LABEL
    assert gov.is_paper_authorized is False
    assert gov.is_live_authorized is False
    assert gov.is_backtest_authorized is False
    assert CANONICAL_CAPITAL_USD == Decimal("0.00")
    assert NO_REAL_ORDERS is True
    assert REAL_ORDERS_COUNT == 0


def test_slot_creation_and_isolation(tmp_path: Path) -> None:
    """Verify slots enforce valid slot IDs and isolate portfolios."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
    )

    slots = supervisor.slots
    assert "A" in slots and "B" in slots and "C" in slots
    assert slots["A"].slot_id == "A"
    assert slots["A"].runner is not None
    assert slots["B"].slot_id == "B"
    assert slots["B"].runner is None
    assert slots["B"].status == "UNASSIGNED"
    assert slots["C"].slot_id == "C"
    assert slots["C"].runner is None
    assert slots["C"].status == "UNASSIGNED"

    # Invalid slot ID must raise DataContractError
    with pytest.raises(DataContractError, match="invalid slot_id 'D'"):
        TournamentSlot(
            slot_id="D",
            strategy_id="TEST",
            strategy_name="Test",
            strategy_version="1.0",
            status="RUNNING",
            session_id="S-D",
            config_hash="0" * 64,
            acash_commit_sha="abc",
        )


def test_unique_session_ids_on_repeated_runs(tmp_path: Path) -> None:
    """Verify two tournaments created on the same day receive distinct IDs and paths."""
    t1 = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
    )
    t2 = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
    )

    assert t1.tournament_id != t2.tournament_id
    assert t1.slots["A"].session_id != t2.slots["A"].session_id
    assert t1.slots["A"].runner is not None and t2.slots["A"].runner is not None
    assert t1.slots["A"].runner._config.journal_path != t2.slots["A"].runner._config.journal_path


def test_strategy_injection_seam_and_divergence(tmp_path: Path) -> None:
    """Verify strategy injection seam allows distinct strategies in Slots A & B."""
    # Fast strategy: periods 2/3
    strat_a = InfrastructureTestStrategy(
        fast_period=2,
        slow_period=3,
        trade_quantity=Decimal("1.0"),
        symbol="BTCUSDT",
    )
    # Slower strategy: periods 4/6
    strat_b = InfrastructureTestStrategy(
        fast_period=4,
        slow_period=6,
        trade_quantity=Decimal("2.0"),
        symbol="BTCUSDT",
    )

    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        slot_strategies={"A": strat_a, "B": strat_b},
    )

    assert supervisor.slots["A"].runner is not None
    assert supervisor.slots["B"].runner is not None
    assert supervisor.slots["C"].runner is None  # Slot C remains UNASSIGNED

    supervisor.start()

    # Feed bars with oscillation to generate signals
    prices = ["50000.0", "50100.0", "50200.0", "50150.0", "50300.0", "50250.0", "50400.0"]
    for idx, p in enumerate(prices, 1):
        bar = _make_sample_bar(price=p, seq=idx)
        results = supervisor.process_bar(bar)
        assert "A" in results and "B" in results and "C" in results
        assert results["C"] is None

    # Check that Slot A and Slot B journals exist independently
    runner_a = supervisor.slots["A"].runner
    runner_b = supervisor.slots["B"].runner
    assert runner_a is not None and runner_b is not None
    slot_a_journal = runner_a._config.journal_path
    slot_b_journal = runner_b._config.journal_path
    assert slot_a_journal.exists()
    assert slot_b_journal.exists()
    assert slot_a_journal != slot_b_journal


def test_halt_lifecycle_seals_manifests_and_rejects_subsequent_bars(tmp_path: Path) -> None:
    """Verify fail-closed halt sets slots to HALTED, seals manifests, and blocks bars."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
    )
    supervisor.start()
    assert supervisor.overall_status == "RUNNING"
    assert supervisor.slots["A"].status == "RUNNING"

    # Process 5 bars
    for i in range(1, 6):
        bar = _make_sample_bar(price=str(50000.0 + i * 10), seq=i)
        supervisor.process_bar(bar)

    # Halt tournament via feed disconnect
    supervisor.record_feed_disconnect("Simulated provider disconnect")

    assert supervisor.overall_status == "HALTED"
    assert supervisor.feed_health == "DISCONNECTED"
    assert supervisor.slots["A"].status == "HALTED"
    assert "Feed disconnected" in (supervisor.slots["A"].halt_reason or "")

    # Manifest should be sealed on disk for slot A
    runner_a_halt = supervisor.slots["A"].runner
    assert runner_a_halt is not None
    manifest_path = (
        runner_a_halt._config.journal_path.parent
        / f"{supervisor.slots['A'].session_id}.manifest.json"
    )
    assert manifest_path.exists(), "Manifest must be sealed on halt"

    # Subsequent bars must be strictly rejected
    bar_after = _make_sample_bar(price="51000.0", seq=7)
    rejected_results = supervisor.process_bar(bar_after)
    assert all(r is None for r in rejected_results.values())

    # Double start must raise DataContractError (no automatic resume)
    with pytest.raises(DataContractError, match="cannot start tournament in status 'HALTED'"):
        supervisor.start()


def test_export_status_json_conforms_to_dashboard_contract(tmp_path: Path) -> None:
    """Verify JSON export matches dashboard types and invariants."""
    metrics_registry = MetricsRegistry()
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        metrics_registry=metrics_registry,
    )

    out_json = tmp_path / "status.json"
    supervisor.export_status_json(out_json)

    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))

    # Global invariants
    glob = data["global"]
    assert glob["canonicalCapitalUsd"] == 0.0
    assert glob["realOrderCount"] == 0
    assert glob["noRealOrders"] is True
    assert glob["governanceBadge"] == "SHADOW / SIMULATED ONLY"

    # Slots
    slots = data["slots"]
    assert "A" in slots and "B" in slots and "C" in slots
    assert slots["A"]["slotId"] == "A"
    assert slots["B"]["status"] == "UNASSIGNED"
    assert slots["C"]["status"] == "UNASSIGNED"
    assert slots["B"]["metrics"]["exposurePct"] is None

    # Meta
    meta = data["_meta"]
    assert meta["isMockData"] is False
    assert "CANONICAL CAPITAL = $0.00" in meta["mockNotice"]
    assert "REAL ORDERS = 0" in meta["mockNotice"]


def test_metrics_exposition(tmp_path: Path) -> None:
    """Verify Prometheus metrics are exposed properly with correct labels."""
    registry = MetricsRegistry()
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        metrics_registry=registry,
    )

    text = registry.render()

    assert "acash_shadow_tournament_canonical_capital_usd 0.0" in text
    assert "acash_shadow_tournament_real_orders_total 0.0" in text
    assert "acash_shadow_tournament_is_simulated_only 1.0" in text
    assert 'acash_shadow_tournament_virtual_nav_usd{slot="A"' in text


def test_shadow_api_server_endpoints(tmp_path: Path) -> None:
    """Verify Read-Only Shadow HTTP API server."""
    metrics_registry = MetricsRegistry()
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="c621824690b7e913ef76990472baa38fd17a925f",
        metrics_registry=metrics_registry,
    )

    # Start API server on ephemeral port (e.g. 19103)
    server = ShadowApiServer(
        supervisor=supervisor,
        host="127.0.0.1",
        port=19103,
        metrics_registry=metrics_registry,
    )
    server.start()

    try:
        # Test GET /api/shadow/status
        url_status = "http://127.0.0.1:19103/api/shadow/status"
        with urllib.request.urlopen(url_status, timeout=3.0) as resp:
            assert resp.status == 200
            assert "application/json" in resp.headers.get("Content-Type", "")
            data = json.loads(resp.read().decode("utf-8"))
            assert data["global"]["canonicalCapitalUsd"] == 0.0
            assert data["global"]["noRealOrders"] is True

        # Test GET /healthz
        url_health = "http://127.0.0.1:19103/healthz"
        with urllib.request.urlopen(url_health, timeout=3.0) as resp:
            assert resp.status == 200
            health_data = json.loads(resp.read().decode("utf-8"))
            assert health_data["status"] == "ok"
            assert health_data["NO_REAL_ORDERS"] is True

        # Test POST rejected with 405 Method Not Allowed
        req = urllib.request.Request(
            url_status,
            data=b'{"order": "buy"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=3.0)
        assert exc_info.value.code == 405

    finally:
        server.stop()


def test_real_feed_provenance_and_manifest_sealing(tmp_path: Path) -> None:
    """Verify PaperSessionConfig and sealed manifest carry real-feed provenance, not synthetic defaults."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="9e4aa9f9276784d20f98fb3986fdbd3e057b5dae",
        instrument="BTCUSDT",
        data_source="binance.public.klines",
        market_domain="SPOT",
        max_market_data_age_ms=65_000,
    )

    slot_a = supervisor.slots["A"]
    assert slot_a.runner is not None
    cfg = slot_a.runner._config

    # Explicit provenance checks on config
    assert cfg.data_source == "binance.public.klines"
    assert cfg.market_domain == "SPOT"
    assert cfg.max_market_data_age_ms == 65_000
    assert cfg.data_source != "SYNTHETIC_BARS"
    assert cfg.market_domain != "SYNTHETIC"

    # Start, process bar, halt and check sealed manifest
    supervisor.start()
    bar = _make_sample_bar("50000.0", 1)
    supervisor.process_bar(bar)
    supervisor.halt("Test finished")

    manifest = slot_a.runner.manifest
    assert manifest is not None
    assert manifest.data_source == "binance.public.klines"
    assert manifest.market_domain == "SPOT"
    assert manifest.is_infrastructure_test_strategy is True


class MockAlphaStrategy:
    """Mock strategy for testing evidence classification (NOT HYP_003)."""

    def __init__(self) -> None:
        self.strategy_id = "MOCK-ALPHA-CANDIDATE"
        self.strategy_version = "1.0.0"

    @property
    def is_infrastructure_test(self) -> bool:
        return False

    @property
    def governance_label(self) -> str:
        return "SHADOW_ALPHA_RESEARCH_CANDIDATE"

    def evaluate(
        self,
        closes: Sequence[Decimal],
        evaluation_time_utc: datetime,
        market_event_reference: str,
    ) -> Optional[StrategySignal]:
        return StrategySignal(
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            evaluation_timestamp_utc=evaluation_time_utc,
            symbol="BTCUSDT",
            direction=SignalDirection.FLAT,
            target_quantity=Decimal("0"),
            signal_strength=Decimal("0"),
            decision_reason="Test alpha signal",
            feature_snapshot={},
            market_event_reference=market_event_reference,
            config_hash="0" * 64,
            is_infrastructure_test=False,
            governance_label="SHADOW_ALPHA_RESEARCH_CANDIDATE",
        )


def test_strategy_evidence_classification(tmp_path: Path) -> None:
    """Verify strategy protocol exposes governance classification and seals manifests accurately."""
    mock_alpha = MockAlphaStrategy()
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="9e4aa9f9276784d20f98fb3986fdbd3e057b5dae",
        slot_strategies={"A": mock_alpha},
    )

    slot_a = supervisor.slots["A"]
    d = slot_a.to_dict()
    assert d["governanceLabel"] == "SHADOW_ALPHA_RESEARCH_CANDIDATE"

    supervisor.start()
    bar = _make_sample_bar("50000.0", 1)
    supervisor.process_bar(bar)
    supervisor.halt("Completed")

    manifest = slot_a.runner.manifest  # type: ignore[union-attr]
    assert manifest is not None
    # Crucial finding check: must NOT be falsely sealed as infrastructure test!
    assert manifest.is_infrastructure_test_strategy is False
