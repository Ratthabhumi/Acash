"""Setup Wizard input routes: ODR gating, strict persistence and request security (synthetic, isolated roots)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pytest

from acash.dashboard_api import private_input as pi
from acash.dashboard_api import private_view_server as srv
from acash.dashboard_api import readiness as rd
from acash.invest.capacity_plan import CAPACITY_SCHEMA
from acash.ppds import private_observation as po

PORT = srv.DEFAULT_PORT
TOKEN = "s" * 43
ORIGIN = srv.ALLOWED_ORIGINS[0]
SNAPSHOT = Path("docs/research/evidence/upi_v1_2_synthetic_snapshot.json")
CAPACITY = Path("docs/research/evidence/upi_v1_synthetic_capacity.json")


def _owner(path: Path) -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    return doc


def _record(root: Path, rel: Path, capability: str, status: str, scope: Optional[List[str]] = None) -> None:
    record = root / rel
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"capability": capability, "status": status, "ratified_by": "OWNER",
                                  "ratified_on": "2026-11-02", "scope_schemas": scope or []}), encoding="utf-8")


def _odr1(root: Path, status: str = "RATIFIED") -> None:
    _record(root, po.AUTHORIZATION_RECORD, po.AUTHORIZED_CAPABILITY, status, [po.SCHEMA_V1_2, CAPACITY_SCHEMA])


def _odr3(root: Path, status: str = "RATIFIED") -> None:
    _record(root, pi.AUTHORING_RECORD, pi.AUTHORING_CAPABILITY, status, [po.SCHEMA_V1_2, CAPACITY_SCHEMA])


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    return tmp_path


def _headers(**extra: str) -> Dict[str, str]:
    return {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN,
            "Content-Type": "application/json", **extra}


def _call(service: pi.InputService, method: str, name: str, body: Any = None, raw: Optional[bytes] = None,
          headers: Optional[Dict[str, str]] = None, expired: bool = False) -> Any:
    data = raw if raw is not None else (b"" if body is None else json.dumps(body).encode("utf-8"))
    status, out_headers, out = srv.respond(method, pi.PREFIX + name, headers or _headers(), TOKEN,
                                           Path("unused.json"), PORT, data, service, expired)
    assert out_headers["Cache-Control"] == "no-store"
    return status, json.loads(out) if out else None


def _save(service: pi.InputService, kind: str, doc: Any, base: str = pi.ABSENT) -> Any:
    return _call(service, "PUT", kind, {"document": doc, "base_revision": base, "confirm_replace": True})


def _leaves(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for v in node.values():
            yield from _leaves(v)
    elif isinstance(node, list):
        for v in node:
            yield from _leaves(v)
    elif isinstance(node, str):
        yield node


def test_reading_needs_odr_001_and_saving_also_needs_odr_003(root: Path) -> None:
    service = pi.InputService()
    status, body = _call(service, "GET", "status")
    assert (status, body["status"], body["odr_001"]) == (403, "AUTHORIZATION_REQUIRED", "RECORD_UNREADABLE")
    _odr1(root)
    status, body = _call(service, "GET", "status")
    assert (status, body["odr_003"], body["revisions"]) == (200, "RECORD_UNREADABLE",
                                                            {"snapshot": pi.ABSENT, "capacity": pi.ABSENT})
    for state in ("PROPOSED_NOT_RATIFIED", "REVOKED"):
        _odr3(root, state)
        status, body = _save(service, "snapshot", _owner(SNAPSHOT))
        assert (status, body["status"], body["odr_003"]) == (403, "AUTHORING_AUTHORIZATION_REQUIRED", state)
    assert not (root / pi.PRIVATE_DIR / "snapshot.json").exists()
    assert _call(service, "POST", "validate", {"snapshot": _owner(SNAPSHOT)})[1]["status"] == "VALID"
    _odr1(root, "REVOKED")
    assert _call(service, "POST", "validate", {"snapshot": _owner(SNAPSHOT)})[0] == 403


def test_save_is_strict_atomic_and_detects_conflicts(root: Path) -> None:
    _odr1(root)
    _odr3(root)
    service, path = pi.InputService(), root / pi.PRIVATE_DIR / "snapshot.json"
    status, body = _save(service, "snapshot", _owner(SNAPSHOT))
    assert (status, body["status"]) == (200, "SAVED")
    first = body["revision"]
    assert _call(service, "GET", "snapshot") == (200, {"status": "OK", "revision": first, "document": _owner(SNAPSHOT)})
    assert _call(service, "GET", "capacity") == (404, {"status": "NO_INPUT", "revision": pi.ABSENT})
    assert _save(service, "snapshot", _owner(SNAPSHOT))[1] == {"status": "REVISION_CONFLICT", "revision": first}

    broken = _owner(SNAPSHOT)
    broken["accounts"][0]["cash"][0]["amount"] = "REPLACE_WITH_AMOUNT"
    status, body = _save(service, "snapshot", broken, first)
    assert (status, body["status"]) == (422, "INVALID") and body["errors"][0]["code"].startswith("PRIVATE_")
    synthetic = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert _save(service, "snapshot", synthetic, first)[1]["errors"][0]["code"] == "INPUT_SNAPSHOT_SCHEMA_OR_DATA_CLASS"
    assert pi._revision(path) == first

    request = {"document": _owner(SNAPSHOT), "base_revision": first, "confirm_replace": False}
    assert _call(service, "PUT", "snapshot", request)[1]["status"] == "CONFIRMATION_REQUIRED"
    assert _call(service, "PUT", "snapshot", {**request, "confirm_replace": True, "path": "x"})[1]["status"] == \
        "REQUEST_FIELDS_INVALID"

    changed = _owner(SNAPSHOT)
    changed["snapshot_id"] = "OWNER_SNAPSHOT_TWO"
    status, body = _save(service, "snapshot", changed, first)
    assert (status, body["status"]) == (200, "SAVED") and body["revision"] != first
    backups = list((root / pi.BACKUP_DIR).glob("snapshot-*.json"))
    assert len(backups) == 1 and pi._revision(backups[0]) == first
    assert not list(path.parent.glob(".*.tmp"))


def test_backup_retention_and_failed_write_keep_the_valid_observation(root: Path,
                                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    _odr1(root)
    _odr3(root)
    monkeypatch.setattr(pi, "BACKUPS_KEPT", 2)
    service, path = pi.InputService(), root / pi.PRIVATE_DIR / "capacity.json"
    revision = pi.ABSENT
    for months in ("3", "4", "5", "6"):
        doc = _owner(CAPACITY)
        doc["reserve_target_months"] = months
        status, body = _save(service, "capacity", doc, revision)
        assert status == 200
        revision = body["revision"]
    assert len(list((root / pi.BACKUP_DIR).glob("capacity-*.json"))) == 2

    def fail(*_: Any) -> None:
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", fail)
    doc = _owner(CAPACITY)
    status, body = _save(service, "capacity", doc, revision)
    assert (status, body) == (500, {"status": "WRITE_FAILED", "code": "OSError"})
    assert pi._revision(path) == revision and not list(path.parent.glob(".*.tmp"))


def test_validation_reports_codes_and_locations_never_values(root: Path) -> None:
    _odr1(root)
    service = pi.InputService()
    snapshot, capacity = _owner(SNAPSHOT), _owner(CAPACITY)
    snapshot["fx_rates"] = []
    capacity["essential_expenses_thb"] = "REPLACE_WITH_THB"
    status, body = _call(service, "POST", "validate", {"snapshot": snapshot, "capacity": capacity})
    assert (status, body["status"]) == (200, "INVALID")
    assert body["snapshot"]["errors"][0]["code"] == "PPDS_CONSOLIDATION_FX_MISSING"
    assert body["capacity"]["errors"] == [{"code": "CAPACITY_MALFORMED_DECIMAL", "where": "essential_expenses_thb"}]
    text = json.dumps(body)
    amounts = {v for v in _leaves(_owner(SNAPSHOT)) if any(c.isdigit() for c in v) and "." in v and len(v) >= 4}
    assert amounts and not [a for a in amounts if a in text]
    assert _call(service, "POST", "validate", {"other": {}})[1]["status"] == "REQUEST_FIELDS_INVALID"


def test_generate_runs_the_canonical_pipeline_and_opens_private_mode(root: Path,
                                                                    capsys: pytest.CaptureFixture[str]) -> None:
    _odr1(root)
    _odr3(root)
    service = pi.InputService()
    view = root / srv.DEFAULT_VIEW
    assert rd.readiness(view)["private_mode"] == "SETUP"
    status, body = _call(service, "POST", "generate", {})
    assert (status, body["status"]) == (422, "PREFLIGHT_INVALID") and not view.exists()
    assert _save(service, "snapshot", _owner(SNAPSHOT))[0] == 200
    assert _save(service, "capacity", _owner(CAPACITY))[0] == 200
    assert _call(service, "POST", "generate", {"force": True})[1]["status"] == "REQUEST_FIELDS_INVALID"
    status, body = _call(service, "POST", "generate", {})
    assert (status, body["status"]) == (200, "GENERATED"), body
    assert srv.load_view(view)[0] == "READY"
    assert rd.readiness(view)["private_mode"] == "READY"
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("method, name, raw, headers, expired, status, code", [
    ("GET", "status", b"", {"Host": "evil.example", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN}, False, 421,
     "HOST_NOT_ALLOWED"),
    ("PUT", "snapshot", b"{}", {"Host": f"127.0.0.1:{PORT}", "Origin": "http://evil.example",
                                srv.TOKEN_HEADER: TOKEN, "Content-Type": "application/json"}, False, 403,
     "ORIGIN_NOT_ALLOWED"),
    ("PUT", "snapshot", b"{}", {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN,
                                "Content-Type": "application/json"}, False, 401, "SESSION_TOKEN_REQUIRED"),
    ("PUT", "snapshot", b"{}", None, True, 401, "SESSION_EXPIRED"),
    ("PUT", "snapshot", b"{}", {**_headers(), "Content-Type": "text/plain"}, False, 415, "CONTENT_TYPE_NOT_ALLOWED"),
    ("PUT", "snapshot", b"{" + b" " * po.MAX_INPUT_BYTES + b"}", None, False, 413, "PAYLOAD_TOO_LARGE"),
    ("POST", "validate", b"{bad", None, False, 400, "MALFORMED_JSON"),
    ("GET", "status", b"{}", None, False, 400, "BODY_NOT_ALLOWED"),
    ("DELETE", "snapshot", b"", None, False, 405, "METHOD_NOT_ALLOWED"),
    ("PUT", "status", b"{}", None, False, 405, "METHOD_NOT_ALLOWED"),
    ("PUT", "../snapshot", b"{}", None, False, 404, "NOT_FOUND"),
    ("PUT", "snapshot?path=C:/x.json", b"{}", None, False, 404, "NOT_FOUND"),
    ("PUT", "upi_view", b"{}", None, False, 404, "NOT_FOUND"),
], ids=lambda value: value.decode()[:8] if isinstance(value, bytes) else None)
def test_requests_are_refused_before_any_file_access(root: Path, monkeypatch: pytest.MonkeyPatch, method: str,
                                                     name: str, raw: bytes, headers: Any, expired: bool,
                                                     status: int, code: str) -> None:
    _odr1(root)
    _odr3(root)

    def never(*_: Any) -> None:
        raise AssertionError("file touched before request checks")
    monkeypatch.setattr(pi, "_input_path", never)
    monkeypatch.setattr(po, "read_bounded_json", never)
    assert _call(pi.InputService(), method, name, raw=raw, headers=headers, expired=expired) == (
        status, {"status": code})


def test_preflight_cors_and_disabled_service(root: Path) -> None:
    status, headers, _ = srv.respond("OPTIONS", pi.PREFIX + "snapshot", _headers(), TOKEN, Path("v.json"), PORT,
                                     b"", pi.InputService())
    assert (status, headers["Access-Control-Allow-Methods"]) == (204, "GET, PUT")
    assert "Content-Type" in headers["Access-Control-Allow-Headers"]
    status, _, body = srv.respond("GET", pi.PREFIX + "status", _headers(), TOKEN, Path("v.json"), PORT)
    assert (status, json.loads(body)) == (404, {"status": "NOT_FOUND"})


def test_rate_limits_refuse_bursts(root: Path) -> None:
    _odr1(root)
    _odr3(root)
    now = [0.0]
    service = pi.InputService(clock=lambda: now[0])
    codes = [_save(service, "capacity", _owner(CAPACITY), "stale")[1]["status"] for _ in range(pi.WRITES_PER_MINUTE + 1)]
    assert codes[:-1] == ["REVISION_CONFLICT"] * pi.WRITES_PER_MINUTE and codes[-1] == "RATE_LIMITED"
    now[0] = 61.0
    assert _save(service, "capacity", _owner(CAPACITY), "stale")[1]["status"] == "REVISION_CONFLICT"


def test_launcher_opens_setup_mode_only_with_odr_001(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkey_view = root / srv.DEFAULT_VIEW
    assert rd.readiness(monkey_view)["private_mode"] == "BLOCKED"
    _odr1(root)
    state = rd.readiness(monkey_view)
    assert (state["private_mode"], state["odr_003"]) == ("SETUP", "RECORD_UNREADABLE")
    rd.main(["--require-private"])
    out = capsys.readouterr().out
    assert "Private mode : SETUP - private view NO_REPORT" in out and "ODR-003" in out


def test_committed_authoring_record_is_proposed_and_scoped() -> None:
    doc = json.loads(Path(pi.AUTHORING_RECORD).read_text(encoding="utf-8"))
    assert (doc["status"], doc["ratified_by"], doc["capability"]) == (
        "PROPOSED_NOT_RATIFIED", None, pi.AUTHORING_CAPABILITY)
    assert doc["scope_files"] == [(pi.PRIVATE_DIR / f).as_posix() for f, _ in pi.INPUTS.values()]
    assert doc["scope_schemas"] == [s for _, s in pi.INPUTS.values()]
    assert {"TRADING_AUTHORIZED", "CAPITAL_TRANSFER", "BROKER_ACCOUNT_CONNECTIVITY"} <= set(doc["independent_of"])
    assert po.odr_state(Path(pi.AUTHORING_RECORD), None, pi.AUTHORING_CAPABILITY) == "PROPOSED_NOT_RATIFIED"
