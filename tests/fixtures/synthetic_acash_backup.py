"""Deterministic Synthetic ACASH Backup Fixture (E3.6 WS10).

WARNING:
========
SYNTHETIC / TEST ONLY / NOT TRADING AUTHORIZATION.
Does NOT represent real trading data, real market observations, or real orders.
Does NOT constitute Paper or Live trading authorization. Canonical capital = $0.

This fixture generates a canonical synthetic persistent root matching all
E3.6 storage invariants:
- windows/ (interlock marker + WindowManifest + runtime segments)
- sessions/ (PaperEventJournal + PaperSessionManifest)
- logs/ (contract layout)
- review/ (contract layout)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional

from acash.paper.journal import (
    JournalEventType,
    JournalLayer,
    PaperEventJournal,
)
from acash.paper.manifest import PaperSessionManifest
from acash.paper.window import WindowAuthoringService

SYNTHETIC_GIT_COMMIT = "8a233cf032d48e2b4a9eb842700d7be90d186ed3"
SYNTHETIC_IMAGE_DIGEST = "sha256:e360000000000000000000000000000000000000000000000000000000000001"
SYNTHETIC_CONTAINER_ID = "cont-synthetic-ws10"
SYNTHETIC_CONFIG_HASH = "cfg0000000000000000000000000000000000000000000000000000000000000"


def create_synthetic_acash_storage_root(
    storage_root: Path,
    *,
    session_id: str = "SES-SYNTHETIC-WS10-01",
    window_id: str = "WIN-SYNTHETIC-WS10-01",
    git_commit: str = SYNTHETIC_GIT_COMMIT,
    image_digest: str = SYNTHETIC_IMAGE_DIGEST,
    container_id: str = SYNTHETIC_CONTAINER_ID,
    config_hash: str = SYNTHETIC_CONFIG_HASH,
    seal_window: bool = True,
) -> Path:
    """Populate storage_root with a deterministic synthetic ACASH state.

    Creates:
    - windows/<window_id>.state.json
    - windows/<window_id>.manifest.json
    - sessions/<session_id>.journal.jsonl
    - sessions/<session_id>.manifest.json
    - logs/
    - review/
    """
    root = Path(storage_root)
    windows_dir = root / "windows"
    sessions_dir = root / "sessions"
    logs_dir = root / "logs"
    review_dir = root / "review"

    windows_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=1)
    end_time = now - timedelta(minutes=5)

    # 1. Create Synthetic Event Journal
    journal_path = sessions_dir / f"{session_id}.journal.jsonl"
    journal = PaperEventJournal(
        session_id=session_id,
        persistence_path=journal_path,
        git_commit=git_commit,
        component_version="0.1.0-test",
    )

    corr_id = journal.new_correlation_id()

    # Append deterministic sequence across layers
    journal.append(
        event_type=JournalEventType.FEED_CONNECTED,
        layer=JournalLayer.MARKET_DATA,
        event_time_utc=start_time,
        correlation_id=corr_id,
        payload={"feed": "synthetic", "status": "CONNECTED"},
        component="test_feed",
    )
    journal.append(
        event_type=JournalEventType.MARKET_BAR_RECEIVED,
        layer=JournalLayer.MARKET_DATA,
        event_time_utc=start_time + timedelta(seconds=1),
        correlation_id=corr_id,
        payload={"symbol": "BTCUSDT", "close": 50000.0, "volume": 1.5},
        component="test_feed",
    )
    journal.append(
        event_type=JournalEventType.SESSION_STARTED,
        layer=JournalLayer.SYSTEM,
        event_time_utc=start_time + timedelta(seconds=2),
        correlation_id=corr_id,
        payload={"status": "INITIALIZED", "marker": "SYNTHETIC_TEST_ONLY"},
        component="test_runner",
    )
    journal.append(
        event_type=JournalEventType.SESSION_STOPPED,
        layer=JournalLayer.SYSTEM,
        event_time_utc=end_time,
        correlation_id=corr_id,
        payload={"reason": "SESSION_COMPLETE", "clean": True},
        component="test_runner",
    )

    # Verify journal integrity immediately to ensure fixture is clean
    violations = journal.verify_integrity()
    if violations:
        raise RuntimeError(f"Synthetic journal fixture creation failed: {violations}")

    final_hash = journal.last_event_hash or "0" * 64
    event_count = journal.event_count

    # 2. Create Synthetic PaperSessionManifest using canonical .seal()
    session_manifest_id = f"MAN-{session_id}"
    session_manifest = PaperSessionManifest.seal(
        session_id=session_id,
        manifest_id=session_manifest_id,
        strategy_id="STRAT-SYNTHETIC-INFRA",
        strategy_version="0.1.0",
        is_infrastructure_test_strategy=True,
        git_commit=git_commit,
        config_hash=config_hash,
        strategy_config_hash=config_hash,
        journal_final_hash=final_hash,
        data_source="synthetic:test",
        instrument_universe=["BTCUSDT"],
        market_domain="CRYPTO_SPOT",
        fill_model_version="0.1.0-sim",
        risk_model_version="0.1.0-sim",
        start_time_utc=start_time,
        end_time_utc=end_time,
        total_event_count=event_count,
        total_warning_count=0,
        total_error_count=0,
        total_trade_count=0,
        total_order_count=0,
        total_rejected_order_count=0,
        final_portfolio_summary={"cash": "0", "positions": {}, "equity": "0"},
        final_reconciliation_status="PASS",
        journal_integrity_status="PASS",
    )

    manifest_path = sessions_dir / f"{session_id}.manifest.json"
    manifest_path.write_text(session_manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")

    # 3. Create Synthetic Window and Deployment Interlock
    service = WindowAuthoringService(
        storage_root=root,
        window_id=window_id,
        author="test-harness",
        created_by_version="0.1.0-e36",
        data_source="synthetic:test",
        instrument_universe=["BTCUSDT"],
        market_domain="CRYPTO_SPOT",
        timeframe="M1",
        host_identity="test-homelab-host",
    )

    # Open window + record open attestation
    service.open_window(
        container_id=container_id,
        image_reference="acash:paper-v1",
        image_digest=image_digest,
        git_commit=git_commit,
        transition_recorded_by="test-harness",
    )
    service.record_clock_attestation(
        source="host-timesyncd-synthetic",
        captured_at_utc=start_time,
        ntp_synced=True,
        reported_skew_ms=1,
        at_open=True,
    )

    # Attach member session
    service.attach_session(
        session_id=session_id,
        journal_final_hash=final_hash,
        session_manifest_hash=session_manifest.manifest_hash,
        sealed_at_utc=end_time,
        event_count=event_count,
    )

    if seal_window:
        # Close segment + record close attestation + verify watchtower + seal
        service.close_runtime_segment(
            transition_reason="WINDOW_SEAL",
            transition_recorded_by="test-harness",
        )
        service.record_clock_attestation(
            source="host-timesyncd-synthetic",
            captured_at_utc=now,
            ntp_synced=True,
            reported_skew_ms=1,
            at_open=False,
        )
        service.verify_watchtower_exclusion(verified=True)
        service.seal(aggregate_reconciliation_status="PASS")

    return root
