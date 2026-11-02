"""Setup Wizard input routes: ODR gating and scope, transactional saves, report publication and request
security (synthetic fixtures, isolated roots)."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set

import pytest

from acash.dashboard_api import launcher
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
BOTH = {"snapshot": pi.ABSENT, "capacity": pi.ABSENT}


def _owner(path: Path) -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    return doc


def _odr1(root: Path, status: str = "RATIFIED") -> None:
    record = root / po.AUTHORIZATION_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"capability": po.AUTHORIZED_CAPABILITY, "status": status, "ratified_by": "OWNER",
                                  "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA]}),
                      encoding="utf-8")


def _odr3_doc(status: str = "RATIFIED") -> Dict[str, Any]:
    return {"decision_id": pi.AUTHORING_DECISION_ID, "capability": pi.AUTHORING_CAPABILITY, "status": status,
            "ratified_by": "OWNER", "ratified_on": "2026-11-02", "requires": [pi.OBSERVATION_DECISION_ID],
            "scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA],
            "scope_files": ["data/private/snapshot.json", "data/private/capacity.json"]}


def _odr3(root: Path, status: str = "RATIFIED", **changes: Any) -> None:
    doc = {**_odr3_doc(status), **changes}
    record = root / pi.AUTHORING_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({k: v for k, v in doc.items() if v is not ...}), encoding="utf-8")


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def authorized(root: Path) -> Path:
    _odr1(root)
    _odr3(root)
    return root


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


def _save(service: pi.InputService, snapshot: Any = None, capacity: Any = None,
          bases: Optional[Dict[str, str]] = None) -> Any:
    return _call(service, "PUT", "inputs", {"snapshot": snapshot or _owner(SNAPSHOT),
                                            "capacity": capacity or _owner(CAPACITY),
                                            "base_revisions": bases or BOTH, "confirm_replace": True})


def _files(root: Path) -> Dict[str, str]:
    return {kind: pi._revision(root / pi.PRIVATE_DIR / name) for kind, (name, _) in pi.INPUTS.items()}


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
    assert (status, body["odr_003"], body["revisions"], body["report"]) == (200, "RECORD_UNREADABLE", BOTH,
                                                                            {"status": "NO_REPORT"})
    for state in ("PROPOSED_NOT_RATIFIED", "REVOKED"):
        _odr3(root, state)
        status, body = _save(service)
        assert (status, body["status"], body["odr_003"]) == (403, "AUTHORING_AUTHORIZATION_REQUIRED", state)
    assert _files(root) == BOTH
    assert _call(service, "POST", "validate", {"snapshot": _owner(SNAPSHOT)})[1]["status"] == "VALID"
    _odr3(root)
    _odr1(root, "REVOKED")
    assert _save(service)[0] == 403 and _files(root) == BOTH
    assert _call(service, "POST", "validate", {"snapshot": _owner(SNAPSHOT)})[0] == 403


@pytest.mark.parametrize("changes, state", [
    ({}, "RATIFIED"),
    ({"decision_id": "ODR_SOMETHING_ELSE"}, "RECORD_IDENTITY_MISMATCH"),
    ({"capability": "OWNER_TRADING_AUTHORIZED"}, "RECORD_CAPABILITY_MISMATCH"),
    ({"ratified_by": "CODING_AGENT"}, "RECORD_INVALID"),
    ({"ratified_on": "yesterday"}, "RECORD_INVALID"),
    ({"requires": ...}, "RECORD_DEPENDENCY_INVALID"),
    ({"requires": ["ODR_UPI_PRIVATE_TRANSACTIONS_002"]}, "RECORD_DEPENDENCY_INVALID"),
    ({"scope_schemas": ...}, "RECORD_SCOPE_INVALID"),
    ({"scope_schemas": [po.SCHEMA_V1_2]}, "RECORD_SCOPE_INVALID"),
    ({"scope_schemas": [po.SCHEMA_V1_2, CAPACITY_SCHEMA, "ACASH_CANONICAL_TRANSACTIONS_V1"]}, "RECORD_SCOPE_INVALID"),
    ({"scope_files": ...}, "RECORD_SCOPE_INVALID"),
    ({"scope_files": ["data/private/snapshot.json"]}, "RECORD_SCOPE_INVALID"),
    ({"scope_files": ["data/private/snapshot.json", "data/private/capacity.json", "data/private/x.json"]},
     "RECORD_SCOPE_INVALID"),
    ({"scope_files": ["data/private/snapshot.json", "../capacity.json"]}, "RECORD_SCOPE_INVALID"),
])
def test_odr_003_identity_dependency_and_scope_are_exact(authorized: Path, changes: Dict[str, Any], state: str) -> None:
    _odr3(authorized, **changes)
    assert pi.authoring_state() == state
    status, body = _save(pi.InputService())
    assert (status == 200) is (state == "RATIFIED")
    if state != "RATIFIED":
        assert body["status"] == "AUTHORING_AUTHORIZATION_REQUIRED" and _files(authorized) == BOTH


def test_save_is_strict_confirmed_and_detects_conflicts(authorized: Path) -> None:
    service = pi.InputService()
    status, body = _save(service)
    assert (status, body["status"]) == (200, "SAVED")
    first = body["revisions"]
    assert first == _files(authorized) and pi.ABSENT not in first.values()
    assert _call(service, "GET", "snapshot") == (200, {"status": "OK", "revision": first["snapshot"],
                                                       "document": _owner(SNAPSHOT)})
    assert _save(service)[1] == {"status": "REVISION_CONFLICT", "revisions": first}

    broken = _owner(CAPACITY)
    broken["essential_expenses_thb"] = "REPLACE_WITH_THB"
    status, body = _save(service, capacity=broken, bases=first)
    assert (status, body["status"], body["capacity"]["errors"][0]["code"]) == (422, "INVALID", "CAPACITY_MALFORMED_DECIMAL")
    synthetic = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert _save(service, snapshot=synthetic, bases=first)[1]["snapshot"]["errors"][0]["code"] == \
        "INPUT_SNAPSHOT_SCHEMA_OR_DATA_CLASS"
    assert _files(authorized) == first

    request = {"snapshot": _owner(SNAPSHOT), "capacity": _owner(CAPACITY), "base_revisions": first,
               "confirm_replace": False}
    assert _call(service, "PUT", "inputs", request)[1]["status"] == "CONFIRMATION_REQUIRED"
    for bad in ({**request, "confirm_replace": True, "path": "x"}, {**request, "confirm_replace": True,
                                                                    "base_revisions": {"snapshot": "x"}}):
        assert _call(service, "PUT", "inputs", bad)[1]["status"] == "REQUEST_FIELDS_INVALID"

    changed = _owner(SNAPSHOT)
    changed["snapshot_id"] = "OWNER_SNAPSHOT_TWO"
    status, body = _save(service, snapshot=changed, bases=first)
    assert (status, body["status"]) == (200, "SAVED") and body["revisions"]["snapshot"] != first["snapshot"]
    backups = sorted((authorized / pi.BACKUP_DIR).glob("*.json"))
    assert {pi._revision(b) for b in backups} == set(first.values())
    assert not list((authorized / pi.PRIVATE_DIR).glob(".*"))


@pytest.mark.parametrize("fail_on", [1, 2])
def test_failed_replacement_restores_the_previous_pair(authorized: Path, monkeypatch: pytest.MonkeyPatch,
                                                       fail_on: int) -> None:
    service = pi.InputService()
    first = _save(service)[1]["revisions"]
    real_replace, calls = os.replace, []

    def flaky(src: Any, dst: Any) -> None:
        if str(src).endswith(".staged"):
            calls.append(dst)
            if len(calls) == fail_on:
                raise OSError("disk full")
        real_replace(src, dst)
    monkeypatch.setattr(os, "replace", flaky)
    changed_snap, changed_cap = _owner(SNAPSHOT), _owner(CAPACITY)
    changed_snap["snapshot_id"] = "OWNER_SNAPSHOT_TWO"
    changed_cap["reserve_target_months"] = "6"
    status, body = _save(service, changed_snap, changed_cap, first)
    assert (status, body["status"]) == (500, "WRITE_FAILED_ROLLED_BACK")
    assert _files(authorized) == first
    assert not (authorized / pi.JOURNAL).exists() and not list((authorized / pi.PRIVATE_DIR).glob(".*.staged"))


def test_interrupted_save_is_recovered_before_any_further_write_or_report(authorized: Path,
                                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    service = pi.InputService()
    first = _save(service)[1]["revisions"]
    real_replace, calls = os.replace, []

    def crash(src: Any, dst: Any) -> None:
        if str(src).endswith(".staged"):
            calls.append(dst)
            if len(calls) == 2:
                raise KeyboardInterrupt
        real_replace(src, dst)
    monkeypatch.setattr(os, "replace", crash)
    changed = _owner(SNAPSHOT)
    changed["snapshot_id"] = "OWNER_SNAPSHOT_TWO"
    with pytest.raises(KeyboardInterrupt):
        _save(service, snapshot=changed, bases=first)
    monkeypatch.setattr(os, "replace", real_replace)
    assert (authorized / pi.JOURNAL).exists() and _files(authorized) != first
    assert _call(service, "GET", "status")[1]["recovery_pending"] is True
    assert pi.recover() == "RECOVERED" and _files(authorized) == first
    (authorized / pi.JOURNAL).write_text("{not json", encoding="utf-8")
    assert _save(service, bases=first)[1]["status"] == "INPUT_RECOVERY_REQUIRED"
    assert pi.generate()[1]["status"] == "INPUT_RECOVERY_REQUIRED"
    (authorized / pi.JOURNAL).write_text(json.dumps({"transaction": "0" * 16, "files": {
        "snapshot": {"previous_revision": "x", "backup": "../../snapshot.json"},
        "capacity": {"previous_revision": pi.ABSENT, "backup": None}}}), encoding="utf-8")
    assert pi.recover() == "RECOVERY_REQUIRED" and _files(authorized) == first


def test_revocation_between_validation_and_replacement_stops_the_write(authorized: Path,
                                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    service = pi.InputService()
    first = _save(service)[1]["revisions"]
    real_backup = pi._backup

    def revoke_then_backup(*args: Any) -> str:
        _odr3(authorized, "REVOKED")
        return real_backup(*args)
    monkeypatch.setattr(pi, "_backup", revoke_then_backup)
    changed = _owner(SNAPSHOT)
    changed["snapshot_id"] = "OWNER_SNAPSHOT_TWO"
    status, body = _save(service, snapshot=changed, bases=first)
    assert (status, body["status"], body["odr_003"]) == (403, "AUTHORING_AUTHORIZATION_REQUIRED", "REVOKED")
    assert _files(authorized) == first


@pytest.mark.parametrize("link", ["data/private", "data/private/snapshot.json", "data/private/backups"])
def test_links_inside_the_private_tree_are_refused(authorized: Path, tmp_path_factory: pytest.TempPathFactory,
                                                   link: str) -> None:
    outside = tmp_path_factory.mktemp("outside")
    target = authorized / link
    target.parent.mkdir(parents=True, exist_ok=True)
    if link.endswith("backups"):
        assert _save(pi.InputService())[0] == 200
    try:
        if target.is_dir():
            shutil.rmtree(target)
        target.symlink_to(outside / "x.json" if link.endswith(".json") else outside,
                          target_is_directory=not link.endswith(".json"))
    except OSError:
        if sys.platform != "win32" or link.endswith(".json"):
            pytest.skip("symlink creation not permitted on this host")
        else:
            import _winapi  # junctions need no privilege on Windows

            _winapi.CreateJunction(str(outside), str(target))
    status, body = _save(pi.InputService(), bases=_files(authorized) if link.endswith("backups") else None)
    assert (status, body["status"]) == (403, "INPUT_PATH_REFUSED")
    assert body["code"] == "INPUT_PATH_LINK_REFUSED" and not list(outside.iterdir())


def test_backup_retention_keeps_recent_copies(authorized: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pi, "BACKUPS_KEPT", 2)
    service, bases = pi.InputService(), BOTH
    for months in ("3", "4", "5", "6"):
        cap = _owner(CAPACITY)
        cap["reserve_target_months"] = months
        status, body = _save(service, capacity=cap, bases=bases)
        assert status == 200
        bases = body["revisions"]
    backups = authorized / pi.BACKUP_DIR
    assert len(list(backups.glob("capacity-*.json"))) == 2 and len(list(backups.glob("snapshot-*.json"))) == 2
    assert (authorized / pi.PRIVATE_DIR / "capacity.json").is_file()


def test_validation_reports_codes_and_locations_never_values(authorized: Path) -> None:
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
    totals_only = json.loads(Path("docs/research/evidence/upi_v1_2_synthetic_totals_only.json").read_text("utf-8"))
    totals_only["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    body = _call(service, "POST", "validate", {"snapshot": totals_only})[1]
    assert body["status"] == "VALID" and "EVIDENCE_ONLY_REPORT" in {w["code"] for w in body["snapshot"]["warnings"]}


def test_generate_publishes_one_consistent_generation(authorized: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = pi.InputService()
    view = authorized / srv.DEFAULT_VIEW
    assert rd.readiness(view)["private_mode"] == "SETUP"
    status, body = _call(service, "POST", "generate", {})
    assert (status, body["status"]) == (422, "PREFLIGHT_INVALID") and not view.exists()
    revisions = _save(service)[1]["revisions"]
    assert _call(service, "POST", "generate", {"force": True})[1]["status"] == "REQUEST_FIELDS_INVALID"
    status, body = _call(service, "POST", "generate", {})
    assert (status, body["status"]) == (200, "GENERATED"), body
    assert srv.load_view(view)[0] == "READY" and rd.readiness(view)["private_mode"] == "READY"
    report = _call(service, "GET", "status")[1]["report"]
    assert (report["status"], report["generation_id"], report["inputs_changed_since"]) == (
        "CONSISTENT", body["generation_id"], False)
    record = json.loads((view.parent / pi.GENERATION_RECORD).read_text(encoding="utf-8"))
    assert record["input_revisions"] == revisions
    assert (view.parent / "generations" / body["generation_id"] / "upi_v1_pack.json").is_file()
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("break_step", ["build_view", "write_view", "publish_record"])
def test_failed_generation_keeps_the_previous_report(authorized: Path, monkeypatch: pytest.MonkeyPatch,
                                                     break_step: str) -> None:
    service = pi.InputService()
    _save(service)
    first = _call(service, "POST", "generate", {})[1]["generation_id"]
    view = authorized / srv.DEFAULT_VIEW
    before = view.read_bytes()

    def boom(*_: Any, **__: Any) -> Any:
        raise OSError("disk full")
    if break_step == "publish_record":
        real: Callable[[Path, bytes], None] = pi._atomic_write

        def fail_on_record(path: Path, data: bytes) -> None:
            if path.name == pi.GENERATION_RECORD and path.parent.name == "out":
                raise OSError("disk full")
            real(path, data)
        monkeypatch.setattr(pi, "_atomic_write", fail_on_record)
    else:
        monkeypatch.setattr(pi, break_step, boom)
    status, body = _call(service, "POST", "generate", {})
    assert (status, body["status"]) == (500, "GENERATION_FAILED")
    report = _call(service, "GET", "status")[1]["report"]
    assert view.read_bytes() == before and (report["status"], report["generation_id"]) == ("CONSISTENT", first)
    assert [p.name for p in (view.parent / "generations").iterdir()] == [first]


@pytest.mark.parametrize("method, name, raw, headers, expired, status, code", [
    ("GET", "status", b"", {"Host": "evil.example", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN}, False, 421,
     "HOST_NOT_ALLOWED"),
    ("PUT", "inputs", b"{}", {"Host": f"127.0.0.1:{PORT}", "Origin": "http://evil.example",
                              srv.TOKEN_HEADER: TOKEN, "Content-Type": "application/json"}, False, 403,
     "ORIGIN_NOT_ALLOWED"),
    ("PUT", "inputs", b"{}", {"Host": f"127.0.0.1:{PORT}", "Content-Type": "application/json",
                              srv.TOKEN_HEADER: TOKEN}, False, 403, "ORIGIN_NOT_ALLOWED"),
    ("PUT", "inputs", b"{}", {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN,
                              "Content-Type": "application/json"}, False, 401, "SESSION_TOKEN_REQUIRED"),
    ("PUT", "inputs", b"{}", {**_headers(), srv.TOKEN_HEADER: "wrong"}, False, 401, "SESSION_TOKEN_REQUIRED"),
    ("PUT", "inputs", b"{}", None, True, 401, "SESSION_EXPIRED"),
    ("PUT", "inputs", b"{}", {**_headers(), "Content-Type": "text/plain"}, False, 415, "CONTENT_TYPE_NOT_ALLOWED"),
    ("PUT", "inputs", b"a=1", {**_headers(), "Content-Type": "application/x-www-form-urlencoded"}, False, 415,
     "CONTENT_TYPE_NOT_ALLOWED"),
    ("PUT", "inputs", b"{" + b" " * po.MAX_INPUT_BYTES + b"}", None, False, 413, "PAYLOAD_TOO_LARGE"),
    ("POST", "validate", b"{bad", None, False, 400, "MALFORMED_JSON"),
    ("GET", "status", b"{}", None, False, 400, "BODY_NOT_ALLOWED"),
    ("DELETE", "inputs", b"", None, False, 405, "METHOD_NOT_ALLOWED"),
    ("PUT", "snapshot", b"{}", None, False, 405, "METHOD_NOT_ALLOWED"),
    ("PUT", "../inputs", b"{}", None, False, 404, "NOT_FOUND"),
    ("PUT", "inputs?path=C:/x.json", b"{}", None, False, 404, "NOT_FOUND"),
    ("PUT", "upi_view", b"{}", None, False, 404, "NOT_FOUND"),
], ids=lambda value: value.decode()[:8] if isinstance(value, bytes) else None)
def test_requests_are_refused_before_any_file_access(authorized: Path, monkeypatch: pytest.MonkeyPatch, method: str,
                                                     name: str, raw: bytes, headers: Any, expired: bool,
                                                     status: int, code: str) -> None:
    def never(*_: Any) -> None:
        raise AssertionError("file touched before request checks")
    monkeypatch.setattr(pi, "_input_path", never)
    monkeypatch.setattr(po, "read_bounded_json", never)
    assert _call(pi.InputService(), method, name, raw=raw, headers=headers, expired=expired) == (
        status, {"status": code})


def test_preflight_cors_and_disabled_service(root: Path) -> None:
    status, headers, _ = srv.respond("OPTIONS", pi.PREFIX + "inputs", _headers(), TOKEN, Path("v.json"), PORT,
                                     b"", pi.InputService())
    assert (status, headers["Access-Control-Allow-Methods"]) == (204, "PUT")
    assert "Content-Type" in headers["Access-Control-Allow-Headers"]
    status, _, body = srv.respond("GET", pi.PREFIX + "status", _headers(), TOKEN, Path("v.json"), PORT)
    assert (status, json.loads(body)) == (404, {"status": "NOT_FOUND"})


def test_rate_limits_refuse_bursts(authorized: Path) -> None:
    now = [0.0]
    service = pi.InputService(clock=lambda: now[0])
    stale = {"snapshot": "stale", "capacity": "stale"}
    codes: List[str] = [_save(service, bases=stale)[1]["status"] for _ in range(pi.WRITES_PER_MINUTE + 1)]
    assert codes[:-1] == ["REVISION_CONFLICT"] * pi.WRITES_PER_MINUTE and codes[-1] == "RATE_LIMITED"
    now[0] = 61.0
    assert _save(service, bases=stale)[1]["status"] == "REVISION_CONFLICT"


def test_launcher_opens_setup_mode_only_with_odr_001(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    view = root / srv.DEFAULT_VIEW
    assert rd.readiness(view)["private_mode"] == "BLOCKED"
    _odr1(root)
    state = rd.readiness(view)
    assert (state["private_mode"], state["odr_003"]) == ("SETUP", "RECORD_UNREADABLE")
    rd.main(["--require-private"])
    out = capsys.readouterr().out
    assert "Private mode : SETUP - private view NO_REPORT" in out and "ODR-003" in out


def _session(launch_key: Optional[str] = "k" * 64, seconds: float = 100.0) -> srv.Session:
    return srv.Session(TOKEN, time.monotonic() + seconds, launch_key)


def _boot(session: Optional[srv.Session], target: str, method: str = "GET", **headers: str) -> Any:
    return srv.respond(method, target, {"Host": f"127.0.0.1:{PORT}", **headers}, TOKEN, Path("v.json"), PORT,
                       b"", pi.InputService(), False, session)


def test_sign_in_link_sets_an_httponly_strict_cookie_exactly_once(authorized: Path) -> None:
    session = _session()
    nonce = session.mint()
    status, headers, _ = _boot(session, f"{srv.SESSION_ROUTE}?nonce={nonce}", **{"Sec-Fetch-Site": "none"})
    assert (status, headers["Location"]) == (303, srv.DASHBOARD_URL)
    assert headers["Set-Cookie"] == f"{srv.COOKIE}={TOKEN}; HttpOnly; SameSite=Strict; Path=/api/upi"
    assert TOKEN not in headers["Location"] and headers["Referrer-Policy"] == "no-referrer"
    assert _boot(session, f"{srv.SESSION_ROUTE}?nonce={nonce}")[0] == 403
    cookie = {k: v for k, v in _headers(Cookie=f"{srv.COOKIE}={TOKEN}").items() if k != srv.TOKEN_HEADER}
    status, body = _call(pi.InputService(), "GET", "status", headers=cookie)
    assert (status, body["odr_003"]) == (200, "RATIFIED")
    _, cors, _ = srv.respond("GET", srv.ROUTE, cookie, TOKEN, Path("v.json"), PORT)
    assert (cors["Access-Control-Allow-Origin"], cors["Access-Control-Allow-Credentials"]) == (ORIGIN, "true")


@pytest.mark.parametrize("case", ["wrong", "extra", "cross_site", "post", "stale", "expired_session", "none"])
def test_sign_in_link_is_refused_unless_fresh_unused_and_top_level(case: str) -> None:
    session = None if case == "none" else _session(seconds=-1 if case == "expired_session" else 100)
    nonce = session.mint() if session else "x"
    if case == "stale" and session:
        session._nonces[nonce] = 0.0
    target = f"{srv.SESSION_ROUTE}?nonce={'other' if case == 'wrong' else nonce}" + ("&x=1" if case == "extra" else "")
    headers = {"Sec-Fetch-Site": "cross-site"} if case == "cross_site" else {}
    status, out_headers, body = _boot(session, target, "POST" if case == "post" else "GET", **headers)
    assert (status, json.loads(body)["status"]) == (403, "SESSION_BOOTSTRAP_REJECTED")
    assert "Set-Cookie" not in out_headers


def test_launch_route_needs_the_key_and_refuses_browser_pages() -> None:
    session = _session()
    status, _, body = _boot(session, srv.LAUNCH_ROUTE, "POST", **{srv.LAUNCH_HEADER: "k" * 64})
    assert status == 200 and session.consume(json.loads(body)["nonce"])
    for s, method, headers in [(session, "POST", {srv.LAUNCH_HEADER: "k" * 64, "Origin": ORIGIN}),
                               (session, "POST", {srv.LAUNCH_HEADER: "j" * 64}), (session, "GET", {srv.LAUNCH_HEADER: "k" * 64}),
                               (_session(None), "POST", {srv.LAUNCH_HEADER: "k" * 64}), (session, "POST", {})]:
        assert _boot(s, srv.LAUNCH_ROUTE, method, **headers)[:1] == (403,)


@pytest.mark.parametrize("cookie,origin,expired,revoked,expected", [
    (f"{srv.COOKIE}={TOKEN}", "http://evil.example", False, False, (403, "ORIGIN_NOT_ALLOWED")),
    (f"{srv.COOKIE}=wrong", ORIGIN, False, False, (401, "SESSION_TOKEN_REQUIRED")),
    ('acash_session="unterminated', ORIGIN, False, False, (401, "SESSION_TOKEN_REQUIRED")),
    ("", ORIGIN, False, False, (401, "SESSION_TOKEN_REQUIRED")),
    (f"{srv.COOKIE}={TOKEN}", ORIGIN, True, False, (401, "SESSION_EXPIRED")),
    (f"{srv.COOKIE}={TOKEN}", ORIGIN, False, True, (403, "AUTHORIZATION_REQUIRED")),
])
def test_cookie_session_keeps_origin_expiry_and_odr_checks(authorized: Path, cookie: str, origin: str, expired: bool,
                                                          revoked: bool, expected: Any) -> None:
    if revoked:
        _odr1(authorized, "REVOKED")
    headers = {"Host": f"127.0.0.1:{PORT}", "Origin": origin, "Cookie": cookie}
    status, body = _call(pi.InputService(), "GET", "status", headers=headers, expired=expired)
    assert (status, body["status"]) == expected


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_launcher_reaches_only_its_own_service(root: Path) -> None:
    _odr1(root)
    port = _free_port()
    server = srv.serve(port, launch_key="k" * 64)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        nonce = launcher.request_nonce(port, "k" * 64)
        assert nonce and getattr(server, "acash_session").consume(nonce)
        assert launcher.request_nonce(port, "j" * 64) is None
    finally:
        server.shutdown()
        server.server_close()
    assert launcher.request_nonce(port, "k" * 64) is None


@pytest.mark.parametrize("busy,key,nonce,code", [
    ({PORT}, None, None, launcher.EXIT_PORT_BUSY),
    ({PORT}, "k" * 64, None, launcher.EXIT_PORT_BUSY),
    ({launcher.DASHBOARD_PORT}, None, None, launcher.EXIT_PORT_BUSY),
    ({PORT, launcher.DASHBOARD_PORT}, "k" * 64, "n" * 43, 0),
])
def test_launcher_refuses_unverified_ports_and_reuses_its_own_instance(
        root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
        busy: Set[int], key: Optional[str], nonce: Optional[str], code: int) -> None:
    _odr1(root)
    if key:
        (root / pi.PRIVATE_DIR).mkdir(parents=True, exist_ok=True)
        (root / pi.PRIVATE_DIR / launcher.KEY_NAME).write_text(key, encoding="utf-8")
    monkeypatch.setattr(launcher, "port_open", lambda p: p in busy)
    monkeypatch.setattr(launcher, "request_nonce", lambda p, k: nonce)
    monkeypatch.setattr(launcher, "dashboard_is_acash", lambda: True)
    started: List[Any] = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: started.append(a))
    assert launcher.main(["--no-browser"]) == code and not started
    out = capsys.readouterr().out
    assert (f"nonce={nonce}" in out) == (code == 0) and TOKEN not in out


def test_launcher_starts_nothing_without_odr_001(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "port_open", lambda p: False)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("started"))
    assert launcher.main(["--no-browser"]) == launcher.EXIT_NOT_AUTHORIZED
    assert not (root / pi.PRIVATE_DIR / launcher.KEY_NAME).exists()


def test_launcher_talks_only_to_loopback_and_never_prints_the_session_secret() -> None:
    text = Path(launcher.__file__).read_text(encoding="utf-8")
    assert text.count("HTTPConnection(") == 2 and text.count("HTTPConnection(srv.HOST, ") == 2
    assert srv.HOST == "127.0.0.1" and "session.token" not in text and "acash_session.token" not in text


def test_committed_authoring_record_keeps_its_exact_scope() -> None:
    doc = json.loads(Path(pi.AUTHORING_RECORD).read_text(encoding="utf-8"))
    assert (doc["decision_id"], doc["capability"], doc["requires"]) == (
        pi.AUTHORING_DECISION_ID, pi.AUTHORING_CAPABILITY, [pi.OBSERVATION_DECISION_ID])
    assert sorted(doc["scope_files"]) == pi.SCOPE_FILES and sorted(doc["scope_schemas"]) == pi.SCOPE_SCHEMAS
    assert {"TRADING_AUTHORIZED", "CAPITAL_TRANSFER", "BROKER_ACCOUNT_CONNECTIVITY",
            "OWNER_PRIVATE_TRANSACTIONS_AUTHORIZED"} <= set(doc["independent_of"])
    state = po.odr_state(Path(pi.AUTHORING_RECORD), None, pi.AUTHORING_CAPABILITY)
    assert state in ("PROPOSED_NOT_RATIFIED", "RATIFIED")
    if state == "RATIFIED":
        lineage = doc["ratification_lineage"]
        assert (doc["ratified_by"], lineage["decided_by"], lineage["applied_by"], lineage["scope_changed"]) == (
            "OWNER", "OWNER", "CODING_AGENT_AT_OWNER_DIRECTION", False)
        evidence = json.loads(Path(lineage["acceptance_evidence"]).read_text(encoding="utf-8"))
        assert evidence["decision_id"] == pi.AUTHORING_DECISION_ID and evidence["result"] == "ALL_P0_PASSED"
        assert lineage["acceptance_commit"] in evidence["security_fix_commits"]
        assert all(check["result"] == "PASS" for check in evidence["p0_checks"])
        assert evidence["unchanged"]["scope_changed"] is False
