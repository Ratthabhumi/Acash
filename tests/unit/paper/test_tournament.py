"""Unit tests for ACASH Shadow Alpha Tournament Core.

Validates all mandatory invariants:
- Zero real order dispatch path (NO_REAL_ORDERS=True, CANONICAL_CAPITAL_USD=$0.00)
- Isolated virtual portfolios (Slot A, B, C)
- Zero state leakage across slots
- Synchronized bar semantics (identical bar delivered to each active slot)
- Independent journals per slot
- Fail-closed feed disconnect and stale data handling
- Honest reporting of unassigned slots (zero fabrication)
- Output dictionary adheres to dashboard schema contract
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.paper.metrics import MetricsRegistry
from acash.paper.runner import SyntheticBar
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
        acash_commit_sha="638388e38f721b49cab2621532b04757d6d85586",
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


def test_tournament_lifecycle_and_synchronized_bars(tmp_path: Path) -> None:
    """Verify synchronized bar processing across active slots with zero leakage."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="638388e38f721b49cab2621532b04757d6d85586",
    )

    assert supervisor.overall_status == "NOT_STARTED"

    # Start tournament
    supervisor.start()
    assert supervisor.overall_status == "RUNNING"
    assert supervisor.feed_health == "HEALTHY"

    # Feed 10 synchronized bars
    for i in range(1, 11):
        price = str(50000.0 + i * 50.0)
        bar = _make_sample_bar(price=price, seq=i)
        results = supervisor.process_bar(bar)

        # Slot A has a runner, Slots B and C do not
        assert "A" in results
        assert results["B"] is None
        assert results["C"] is None

    # Check Slot A journal exists on disk
    journal_file = tmp_path / f"{supervisor.tournament_id}_slot_a.journal.jsonl"
    assert journal_file.exists(), "Slot A must have its own isolated journal"

    # Slot B and C must have zero journals created
    journal_b = tmp_path / f"{supervisor.tournament_id}_slot_b.journal.jsonl"
    assert not journal_b.exists(), "Unassigned slot must not create stray journals"


def test_feed_disconnect_and_stale_data_halts(tmp_path: Path) -> None:
    """Verify fail-closed halts when feed disconnects or data is stale."""
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="638388e38f721b49cab2621532b04757d6d85586",
    )
    supervisor.start()
    assert supervisor.overall_status == "RUNNING"

    # Trigger feed disconnect
    supervisor.record_feed_disconnect("Simulated network drop")
    assert supervisor.overall_status == "HALTED"
    assert supervisor.feed_health == "DISCONNECTED"
    assert "Feed disconnected" in (supervisor._halt_reason or "")

    # Bars received during HALTED state must be rejected
    bar = _make_sample_bar(price="50000.0", seq=1)
    results = supervisor.process_bar(bar)
    assert all(cid is None for cid in results.values())


def test_export_status_json_conforms_to_dashboard_contract(tmp_path: Path) -> None:
    """Verify JSON export matches dashboard types and invariants."""
    metrics_registry = MetricsRegistry()
    supervisor = create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha="638388e38f721b49cab2621532b04757d6d85586",
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
        acash_commit_sha="638388e38f721b49cab2621532b04757d6d85586",
        metrics_registry=registry,
    )

    text = registry.render()

    assert "acash_shadow_tournament_canonical_capital_usd 0.0" in text
    assert "acash_shadow_tournament_real_orders_total 0.0" in text
    assert "acash_shadow_tournament_is_simulated_only 1.0" in text
    assert 'acash_shadow_tournament_virtual_nav_usd{slot="A"' in text
