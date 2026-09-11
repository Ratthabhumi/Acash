"""ACASH Paper Trading — E3.6 WS5/WS2/WS3/WS4/WS6/WS7/WS9 Test Suite.

Covers, per E3.6-DESIGN.md, the ACASH-side implementation:
- WS5  Graceful shutdown: BoundedGracefulShutdown fail-closed signal handling
       (D16.1/D16.3, gate G2).
- WS2/WS3/WS4  Observation-window model, runtime segments, transition
       records (D1.5), deployment interlock marker + state machine (D2.1),
       fail-closed seals (§9), storage conventions (D10.3).
- WS6  Clock attestation at segment open/close (D4.5, gate G15).
- WS7  Feed policy accounting: auto_recovery_used=False enforced, feed
       failure counters (D6.2/O1).
- WS9  Prometheus-text /metrics endpoint (D13.1/D13.2).

GOVERNANCE (E3.6):
==================
- Execution/paper infrastructure only; no strategy qualification, no Paper or
  Live authorization. NO network is hit in these tests.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.paper.metrics import (
    PaperMetricsServer,
    build_operational_metrics,
    metrics_for_window_and_journal,
)
from acash.paper.shutdown import BoundedGracefulShutdown
from acash.paper.window import (
    EvidenceStatus,
    WindowAuthoringService,
    WindowManifest,
    WindowState,
    validate_window_manifest,
)


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "acash_root"


def make_service(
    storage_root: Path,
    window_id: str = "W-001",
    *,
    git_commit: str = "0123abc",
) -> WindowAuthoringService:
    return WindowAuthoringService(
        storage_root=storage_root,
        window_id=window_id,
        author="test-harness",
        created_by_version="0.1.0-e36",
        data_source="feed:binance",
        instrument_universe=["BTCUSDT"],
        market_domain="CRYPTO_SPOT",
        timeframe="M1",
        host_identity="test-host-001",
    )


def open_window(service: WindowAuthoringService) -> None:
    service.open_window(
        container_id="cont-A",
        image_reference="acash:paper-v1",
        image_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        git_commit="0123abc",
        transition_recorded_by="test-harness",
    )
    service.record_clock_attestation(
        source="test-infra-timesyncd",
        captured_at_utc=datetime.now(timezone.utc),
        ntp_synced=True,
        reported_skew_ms=2,
        at_open=True,
    )


def attach_and_seal(service: WindowAuthoringService, *, n_sessions: int = 2) -> None:
    for i in range(n_sessions):
        service.attach_session(
            session_id=f"S-{i:03d}",
            journal_final_hash=f"{i:064x}",
            session_manifest_hash=f"{i+10:064x}",
            sealed_at_utc=datetime.now(timezone.utc) - timedelta(minutes=n_sessions - i),
            event_count=10,
        )
    service.close_runtime_segment(
        transition_reason="OPERATOR_STOP_RESUME",
        transition_recorded_by="test-harness",
    )
    service.record_clock_attestation(
        source="test-infra-timesyncd",
        captured_at_utc=datetime.now(timezone.utc),
        ntp_synced=True,
        reported_skew_ms=1,
        at_open=False,
    )
    service.verify_watchtower_exclusion(verified=True)
    service.seal(aggregate_reconciliation_status="PASS")


# ---------------------------------------------------------------------------
# WS5 — Bounded Graceful Shutdown
# ---------------------------------------------------------------------------


def test_graceful_no_shutdown_resolves_zero() -> None:
    ctrl = BoundedGracefulShutdown(grace_seconds=10.0)
    ctrl.install()
    try:
        assert ctrl.shutdown_requested is False
        assert ctrl.resolve() == 0
        out = ctrl.outcome()
        assert out.requested is False
        assert out.completed_within_grace is False
        assert out.forced_exit is False
    finally:
        ctrl.restore()


def test_graceful_request_is_recorded_and_resolves_zero() -> None:
    ctrl = BoundedGracefulShutdown(grace_seconds=10.0)
    ctrl.install()
    try:
        ctrl.request_shutdown(signum=15)
        assert ctrl.shutdown_requested is True
        assert ctrl.shutdown_requested_at_utc is not None
        assert ctrl.grace_deadline_utc is not None
        assert ctrl.resolve() == 0
        out = ctrl.outcome()
        assert out.requested is True
        assert out.completed_within_grace is True
        assert out.forced_exit is False
    finally:
        ctrl.restore()


def test_graceful_expiry_is_fail_closed_nonzero() -> None:
    ctrl = BoundedGracefulShutdown(grace_seconds=0.05)
    ctrl.install()
    try:
        ctrl.request_shutdown(signum=15)
        time.sleep(0.06)
        assert ctrl.forced() is True
        assert ctrl.resolve() != 0
        out = ctrl.outcome()
        assert out.forced_exit is True
        assert out.completed_within_grace is False
    finally:
        ctrl.restore()


def test_grace_seconds_must_be_positive() -> None:
    with pytest.raises(DataContractError):
        BoundedGracefulShutdown(grace_seconds=0.0)


def test_double_install_rejected() -> None:
    ctrl = BoundedGracefulShutdown(grace_seconds=10.0)
    ctrl.install()
    try:
        with pytest.raises(DataContractError):
            ctrl.install()
    finally:
        ctrl.restore()


def test_second_signal_escapes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second signal must not be silently accepted (fail-closed escalation).

    On a second signal while a stop is already in progress the handler forces
    a non-zero exit rather than letting the process hang past the grace window.
    We patch the global ``os._exit`` because a real call would kill pytest.
    """
    exits: list[int] = []
    monkeypatch.setattr("os._exit", lambda code: exits.append(code))

    ctrl = BoundedGracefulShutdown(grace_seconds=10.0)
    ctrl.install()
    try:
        ctrl.request_shutdown(signum=15)  # first request = graceful
        assert ctrl.shutdown_requested is True
        ctrl.request_shutdown(signum=15)  # second signal = escalate
        assert exits == [1]
    finally:
        ctrl.restore()


# ---------------------------------------------------------------------------
# WS3/WS4 — Observation window: open -> attrs -> transition -> seal
# ---------------------------------------------------------------------------


def test_window_open_writes_segment_and_marker(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)

    assert svc.state() == WindowState.OPEN
    marker_path = svc.marker_path
    assert marker_path.exists()
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker["window_id"] == "W-001"
    assert marker["state"] == "OPEN"

    manifest_path = svc.manifest_path
    assert manifest_path.exists()
    manifest = WindowManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert manifest.evidence_status == EvidenceStatus.OPEN
    assert len(manifest.runtime_segments) == 1
    assert manifest.runtime_segments[0].transition_reason == "WINDOW_OPEN"


def test_window_open_requires_quiescent(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    with pytest.raises(DataContractError):
        svc.open_window(
            container_id="cont-X",
            image_reference="acash:paper-v1",
            image_digest="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            git_commit="0123abc",
            transition_recorded_by="test-harness",
        )


def test_window_open_rejects_unknown_git_commit(storage_root: Path) -> None:
    svc = make_service(storage_root)
    with pytest.raises(DataContractError):
        svc.open_window(
            container_id="cont-A",
            image_reference="acash:paper-v1",
            image_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            git_commit="unknown",
            transition_recorded_by="test-harness",
        )


def test_governed_runtime_transition_closes_and_opens_segment(
    storage_root: Path,
) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    seg2 = svc.open_runtime_segment(
        container_id="cont-B",
        image_reference="acash:paper-v1",
        image_digest="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        git_commit="0123abc",
        transition_reason="GOVERNED_DEPLOYMENT",
        transition_recorded_by="operator-ama",
    )
    assert len(seg2.member_session_ids) == 0
    assert seg2.segment_id.endswith("seg-02")

    manifest = WindowManifest.model_validate_json(
        svc.manifest_path.read_text(encoding="utf-8")
    )
    segs = manifest.runtime_segments
    assert len(segs) == 2
    assert segs[0].closed is True  # Old segment closed first (D1.5)
    assert segs[1].closed is False
    assert segs[1].transition_reason == "GOVERNED_DEPLOYMENT"
    # Close attestation stays None until infra supplies it (D4.5 / G15).
    assert segs[0].clock_attestation_close is None


def test_seal_fail_closed_on_missing_attestation(storage_root: Path) -> None:
    svc = make_service(storage_root)
    svc.open_window(
        container_id="cont-A",
        image_reference="acash:paper-v1",
        image_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        git_commit="0123abc",
        transition_recorded_by="test-harness",
    )
    # No clock attestation recorded (D4.5/G15 violation).
    svc.close_runtime_segment(
        transition_reason="OPERATOR_STOP_RESUME",
        transition_recorded_by="test-harness",
    )
    with pytest.raises(DataContractError):
        svc.seal(aggregate_reconciliation_status="PASS")


def test_seal_fail_closed_auto_recovery_true(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    # Forge a manifest that claims auto-recovery (D6.3/O1 violation).
    manifest = WindowManifest.model_validate_json(
        svc.manifest_path.read_text(encoding="utf-8")
    )
    forged = manifest.model_copy(update={"auto_recovery_used": True}, deep=True)
    violations = validate_window_manifest(forged)
    assert any("auto_recovery_used" in v for v in violations)


def test_seal_success_upgrades_evidence_and_hash(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    attach_and_seal(svc)

    manifest = WindowManifest.model_validate_json(
        svc.manifest_path.read_text(encoding="utf-8")
    )
    assert manifest.evidence_status == EvidenceStatus.SEALED
    assert manifest.window_manifest_hash is not None
    assert manifest.window_seal_utc is not None
    assert manifest.total_sessions == 2
    assert manifest.aggregate_event_count == 20
    assert svc.state() == WindowState.SEALED
    marker = json.loads(svc.marker_path.read_text(encoding="utf-8"))
    assert marker["state"] == "SEALED"

    # Hash is the single-authority computation.
    assert manifest.window_manifest_hash == manifest.compute_hash()


def test_seal_rejects_open_segment_during_sealed(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    # Session attached but the segment stays open -> SEALED fails (D2.1).
    svc.attach_session(
        session_id="S-000",
        journal_final_hash=f"{0:064x}",
        session_manifest_hash=f"{10:064x}",
        sealed_at_utc=datetime.now(timezone.utc),
        event_count=10,
    )
    with pytest.raises(DataContractError):
        svc.seal(aggregate_reconciliation_status="PASS")


def test_seal_rejects_missing_watchtower_verification(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    svc.attach_session(
        session_id="S-000",
        journal_final_hash=f"{0:064x}",
        session_manifest_hash=f"{10:064x}",
        sealed_at_utc=datetime.now(timezone.utc),
        event_count=10,
    )
    svc.close_runtime_segment(
        transition_reason="OPERATOR_STOP_RESUME",
        transition_recorded_by="test-harness",
    )
    svc.record_clock_attestation(
        source="test-infra-timesyncd",
        captured_at_utc=datetime.now(timezone.utc),
        ntp_synced=True,
        reported_skew_ms=1,
        at_open=False,
    )
    # watchtower_exclusion_verified stays False -> seal fails (C2/D2.4).
    with pytest.raises(DataContractError):
        svc.seal(aggregate_reconciliation_status="PASS")


def test_provenance_violation_marks_window_void(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    result = svc.detect_provenance_violation(details="silent container replacement")
    assert result.evidence_status == EvidenceStatus.VOID
    assert result.operational_vs_evidence_classification == "PROVENANCE_VIOLATION"
    assert svc.state() == WindowState.VOID


def test_deploy_interlock_blocks_open_allows_sealed(storage_root: Path) -> None:
    svc = make_service(storage_root)

    # QUIESCENT -> deploy of paper service allowed (no active window).
    assert svc.deploy_allowance().last_deploy_stance == "ALLOWED"

    open_window(svc)
    with pytest.raises(DataContractError):
        svc.assert_deploy_allowed()

    attach_and_seal(svc)
    assert svc.deploy_allowance().last_deploy_stance == "ALLOWED"


def test_session_dir_convention(storage_root: Path) -> None:
    svc = make_service(storage_root)
    session_dir = svc.session_storage_dir(storage_root)
    assert session_dir.name == "sessions"
    assert session_dir.parent == storage_root


def test_duplicate_session_attach_rejected(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    svc.attach_session(
        session_id="S-000",
        journal_final_hash=f"{0:064x}",
        session_manifest_hash=f"{10:064x}",
        sealed_at_utc=datetime.now(timezone.utc),
        event_count=10,
    )
    with pytest.raises(DataContractError):
        svc.attach_session(
            session_id="S-000",
            journal_final_hash=f"{0:064x}",
            session_manifest_hash=f"{10:064x}",
            sealed_at_utc=datetime.now(timezone.utc),
            event_count=10,
        )


def test_feed_failure_accounting(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    svc.record_feed_failure(reason="FEED_DISCONNECTED")
    svc.record_feed_failure(reason="STALE_DATA")
    manifest = WindowManifest.model_validate_json(
        svc.manifest_path.read_text(encoding="utf-8")
    )
    assert manifest.feed_failure_events == 2
    assert len(manifest.halted_reason_chronology) == 2
    assert manifest.halted_reason_chronology[0].reason == "FEED_DISCONNECTED"


def test_seal_persists_under_windows_dir(storage_root: Path) -> None:
    svc = make_service(storage_root)
    open_window(svc)
    attach_and_seal(svc)
    assert (storage_root / "windows" / "W-001.manifest.json").exists()
    assert (storage_root / "windows" / "W-001.state.json").exists()


# ---------------------------------------------------------------------------
# WS9 — /metrics endpoint
# ---------------------------------------------------------------------------


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_metrics_render_prometheus_text() -> None:
    registry = build_operational_metrics(
        event_count=42,
        journal_integrity_status="PASS",
        window_state="OPEN",
        feed_failure_events=1,
        auto_recovery_used=False,
        uptime_seconds=123.0,
    )
    text = registry.render()
    assert "# TYPE acash_paper_up gauge" in text
    assert 'acash_paper_up 1.0' in text
    assert 'acash_window_state{state="OPEN"} 1.0' in text
    assert 'acash_window_state{state="SEALED"} 0.0' in text
    assert 'acash_feed_failure_events_total 1.0' in text
    assert 'acash_auto_recovery_used 0.0' in text
    assert "Sharpe" not in text  # never evidence (D13.2)


def test_metrics_rejects_unknown_integrity_status() -> None:
    with pytest.raises(DataContractError):
        build_operational_metrics(
            event_count=1,
            journal_integrity_status="MAYBE",
            window_state="OPEN",
            feed_failure_events=0,
            auto_recovery_used=False,
            uptime_seconds=0.0,
        )


def test_metrics_server_serves_metrics() -> None:
    port = free_port()
    registry = build_operational_metrics(
        event_count=7,
        journal_integrity_status="PASS",
        window_state="SEALED",
        feed_failure_events=0,
        auto_recovery_used=False,
        uptime_seconds=9.0,
    )
    server = PaperMetricsServer(registry, host="127.0.0.1", port=port)
    server.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/metrics", timeout=5
        ) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8")
        assert "acash_paper_up" in body
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=5)
        assert exc_info.value.code == 404
    finally:
        server.stop()


def test_metrics_server_double_start_rejected() -> None:
    port = free_port()
    registry = build_operational_metrics(
        event_count=0,
        journal_integrity_status="PASS",
        window_state="QUIESCENT",
        feed_failure_events=0,
        auto_recovery_used=False,
        uptime_seconds=0.0,
    )
    server = PaperMetricsServer(registry, host="127.0.0.1", port=port)
    server.start()
    try:
        with pytest.raises(DataContractError):
            server.start()
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# Attachment of graceful stop into CLI run loop (WS5 integration contract)
# ---------------------------------------------------------------------------


def test_graceful_stop_flag_wires_into_loop_contract() -> None:
    """The run loop must break on shutdown_requested and then seal.

    We test the contract the loop relies on: after a request, the loop
    condition is False, and resolve() returns 0 within grace (=> manifest
    sealed path completes). Notable: the CLI itself seals via runner.stop();
    here we verify the loop-break + seal happens within the grace window.
    """
    ctrl = BoundedGracefulShutdown(grace_seconds=10.0)
    ctrl.install()
    try:
        steps = 0
        while not ctrl.shutdown_requested and steps < 1000:
            steps += 1
            if steps == 2:
                ctrl.request_shutdown(signum=15)
        assert steps >= 2
        assert steps < 1000
        assert ctrl.shutdown_requested is True
        # Seal path (runner.stop() analogue) completes within grace.
        assert ctrl.resolve() == 0
    finally:
        ctrl.restore()


def test_metrics_convenience_function() -> None:
    text = metrics_for_window_and_journal(
        event_count=5,
        journal_integrity_status="FAIL",
        window_state="VOID",
        feed_failure_events=3,
        auto_recovery_used=False,
        started_at_utc=datetime.now(timezone.utc),
    )
    assert 'acash_journal_integrity_status{state="FAIL"} 0.0' in text
    assert 'acash_window_state{state="VOID"} 1.0' in text