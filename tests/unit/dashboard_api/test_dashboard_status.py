"""Sanitized dashboard system status endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from acash.dashboard_api import dashboard_status, private_input as pi
from acash.dashboard_api import private_view_server as srv
from acash.invest import market_authority as ma
from acash.ppds import private_observation as po
from acash.ppds import transactions as txn

EVIDENCE = Path("docs/research/evidence")
PORT = 8765
TOKEN = "t" * 43
ORIGIN = "http://127.0.0.1:3002"


def _write(root: Path, record: Path, doc: Dict[str, Any]) -> None:
    (root / record).parent.mkdir(parents=True, exist_ok=True)
    (root / record).write_text(json.dumps(doc), encoding="utf-8")


def _odr(root: Path) -> None:
    _write(root, po.AUTHORIZATION_RECORD, {"capability": po.AUTHORIZED_CAPABILITY, "status": "RATIFIED", "ratified_by": "OWNER",
                                           "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2]})


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ma, "_repo_root", lambda: tmp_path)
    _odr(tmp_path)
    return tmp_path


def _call(method: str, name: str, body: Any = None) -> tuple[int, Any]:
    data = b"" if body is None else json.dumps(body).encode("utf-8")
    headers = {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN, "Content-Type": "application/json"}
    status, out_headers, out = srv.respond(method, dashboard_status.PREFIX + name, headers, TOKEN,
                                           Path("unused.json"), PORT, data, pi.InputService())
    assert out_headers["Cache-Control"] == "no-store"
    return status, json.loads(out) if out else None


def test_system_status_returns_framework_matrix_and_shadow(root: Path) -> None:
    http, out = _call("GET", "system")
    assert http == 200 and out["status"] == "OK"
    assert len(out["frameworks"]) == 5
    assert all(fw["execution_authority"] == "NONE" for fw in out["frameworks"])
    assert out["shadow"]["state"] == "FORWARD_OBSERVATIONS_PENDING"


def test_system_status_refuses_without_odr_001(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pi, "odr_state", lambda path, schema, cap=None: "NOT_RATIFIED")
    assert _call("GET", "system")[0] == 403


def test_ops_doctor_scheduled_sync_acceptance(root: Path) -> None:
    from acash.ops import ops_report
    warehouse = root / "data" / "private" / "market_warehouse"
    warehouse.mkdir(parents=True)
    # Manual run: not accepted.
    (warehouse / "sync_state.json").write_text(json.dumps({"status": "SYNCED"}), encoding="utf-8")
    report = ops_report.build_report(root / "data" / "private")
    assert report["windows_sync"]["scheduled_sync_accepted"] is False
    # Scheduled NO_CHANGE: accepted.
    (warehouse / "sync_state.json").write_text(
        json.dumps({"status": "NO_CHANGE", "scheduled_by": "TASK_SCHEDULER"}), encoding="utf-8")
    report = ops_report.build_report(root / "data" / "private")
    assert report["windows_sync"]["scheduled_sync_accepted"] is True
    # Failed run: not accepted even with scheduled_by.
    (warehouse / "sync_state.json").write_text(
        json.dumps({"status": "RESEARCH_REBUILD_FAILED", "scheduled_by": "TASK_SCHEDULER"}), encoding="utf-8")
    report = ops_report.build_report(root / "data" / "private")
    assert report["windows_sync"]["scheduled_sync_accepted"] is False
