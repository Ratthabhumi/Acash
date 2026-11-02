"""Owner-directed authoring of the two private input files for the dashboard Setup Wizard.

Routes live under ``/api/upi/input/`` on the loopback private-view server, behind its Host,
Origin and session-token checks. Reading, in-memory validation and report generation need
ODR-001; replacing a file additionally needs ODR-003 (``OWNER_LOCAL_INPUT_AUTHORING_AUTHORIZED``).
Both records are re-read on every request. Only ``data/private/snapshot.json`` and
``data/private/capacity.json`` can be written; the target is chosen from a fixed table, never
from the request. Responses carry statuses, codes and field locations, never amounts, and
nothing is logged.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
from collections import deque
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Mapping, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.invest.capacity_plan import CAPACITY_SCHEMA, load_capacity, parse_capacity
from acash.invest.preflight import duplicate_cash_groups, preflight
from acash.invest.upi_view import build_view, write_view
from acash.invest.wealth_pack import build_wealth_pack, write_pack
from acash.ppds import private_observation as po
from acash.ppds.private_observation import (
    MAX_INPUT_BYTES,
    SCHEMA_V1_2,
    book_summary,
    build_book,
    load_snapshot,
    odr_state,
    parse_snapshot,
    read_gated_json,
)

PREFIX = "/api/upi/input/"
AUTHORING_RECORD = Path("docs/governance/ODR_UPI_LOCAL_INPUT_AUTHORING_003.json")
AUTHORING_CAPABILITY = "OWNER_LOCAL_INPUT_AUTHORING_AUTHORIZED"
PRIVATE_DIR = Path("data/private")
INPUTS: Dict[str, Tuple[str, str]] = {
    "snapshot": ("snapshot.json", SCHEMA_V1_2),
    "capacity": ("capacity.json", CAPACITY_SCHEMA),
}
OUTPUT_DIR = PRIVATE_DIR / "out"
VIEW_FILE = "upi_view.json"
BACKUP_DIR = PRIVATE_DIR / "backups"
BACKUPS_KEPT = 20
ABSENT = "ABSENT"
DATA_CLASS = "OWNER_PRIVATE_OBSERVATION"
WRITES_PER_MINUTE = 20
REQUESTS_PER_MINUTE = 240

Result = Tuple[int, Dict[str, Any]]


class RateLimiter:
    """Sliding one-minute window; a refused request is not counted."""

    def __init__(self, limit: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit, self._clock, self._lock = limit, clock, threading.Lock()
        self._hits: Deque[float] = deque()

    def allow(self) -> bool:
        with self._lock:
            now = self._clock()
            while self._hits and now - self._hits[0] >= 60:
                self._hits.popleft()
            if len(self._hits) >= self._limit:
                return False
            self._hits.append(now)
            return True


class InputService:
    """Per-process state: write lock and rate limits. Paths are resolved per request."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.write_lock = threading.Lock()
        self.requests = RateLimiter(REQUESTS_PER_MINUTE, clock)
        self.writes = RateLimiter(WRITES_PER_MINUTE, clock)


def _code(exc: Exception) -> Dict[str, str]:
    text = str(exc)
    code, _, where = text.partition(":")
    return {"code": code.rstrip(". "), "where": where.strip().rstrip(".")[:200]}


def _root() -> Path:
    return po._repo_root()


def _input_path(kind: str) -> Path:
    return _root() / PRIVATE_DIR / INPUTS[kind][0]


def _revision(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return ABSENT


def authority() -> Dict[str, str]:
    return {"odr_001": odr_state(None, SCHEMA_V1_2),
            "odr_003": odr_state(_root() / AUTHORING_RECORD, None, AUTHORING_CAPABILITY)}


def _check_snapshot(doc: Any, report_date: Optional[date]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_V1_2 or doc.get("data_class") != DATA_CLASS:
        return [{"code": "INPUT_SNAPSHOT_SCHEMA_OR_DATA_CLASS", "where": "schema,data_class"}], []
    try:
        snapshot = parse_snapshot(doc)
        summary = book_summary(build_book(snapshot), report_date)
    except DataContractError as exc:
        return [_code(exc)], []
    warnings = [{"code": "POSSIBLE_DUPLICATE_CASH_ACROSS_ACCOUNTS", "where": group}
                for group in duplicate_cash_groups(snapshot)]
    if summary["valuation_stale"]:
        warnings.append({"code": "STALE_VALUATION", "where": f"valuation_age_days={summary['valuation_age_days']}"})
    evidence = summary.get("evidence")
    if evidence:
        for acct in evidence[snapshot.reporting_currency]["accounts"]:
            total = acct["account_total"]
            status = total["status"] if isinstance(total, dict) else str(total)
            if status not in ("RECONCILED", "CONSISTENT_WITH_DISPLAY_ROUNDING", "NOT_REPORTED"):
                warnings.append({"code": status, "where": acct["account_ref"]})
    return [], warnings


def _check_capacity(doc: Any) -> List[Dict[str, str]]:
    if not isinstance(doc, dict) or doc.get("data_class") != DATA_CLASS:
        return [{"code": "INPUT_CAPACITY_SCHEMA_OR_DATA_CLASS", "where": "schema,data_class"}]
    try:
        parse_capacity(doc)
    except DataContractError as exc:
        return [_code(exc)]
    return []


def validate(body: Any, report_date: Optional[date] = None) -> Result:
    if not isinstance(body, dict) or not body or set(body) - set(INPUTS):
        return 400, {"status": "REQUEST_FIELDS_INVALID"}
    out: Dict[str, Any] = {}
    for kind, doc in body.items():
        if kind == "snapshot":
            errors, warnings = _check_snapshot(doc, report_date or date.today())
        else:
            errors, warnings = _check_capacity(doc), []
        out[kind] = {"status": "INVALID" if errors else "VALID", "errors": errors, "warnings": warnings}
    valid = all(v["status"] == "VALID" for v in out.values())
    return 200, {"status": "VALID" if valid else "INVALID", **out}


def read_input(kind: str) -> Result:
    path = _input_path(kind)
    if not path.is_file():
        return 404, {"status": "NO_INPUT", "revision": ABSENT}
    revision = _revision(path)
    try:
        doc = read_gated_json(path, "INPUT")
    except DataContractError as exc:
        return 422, {"status": "INPUT_UNREADABLE", "revision": revision, **_code(exc)}
    return 200, {"status": "OK", "revision": revision, "document": doc}


def _backup(path: Path, kind: str, revision: str) -> None:
    backups = _root() / BACKUP_DIR
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = backups / f"{kind}-{stamp}-{revision[:12]}.json"
    target.write_bytes(path.read_bytes())
    kept = sorted(backups.glob(f"{kind}-*.json"))
    for old in kept[:-BACKUPS_KEPT]:
        old.unlink()


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        with open(tmp, "xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def save_input(kind: str, body: Any, service: InputService) -> Result:
    if not isinstance(body, dict) or set(body) != {"document", "base_revision", "confirm_replace"}:
        return 400, {"status": "REQUEST_FIELDS_INVALID"}
    if body["confirm_replace"] is not True or not isinstance(body["base_revision"], str):
        return 400, {"status": "CONFIRMATION_REQUIRED"}
    doc = body["document"]
    if kind == "snapshot":
        errors, _ = _check_snapshot(doc, None)
    else:
        errors = _check_capacity(doc)
    if errors:
        return 422, {"status": "INVALID", "errors": errors}
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if len(data) > MAX_INPUT_BYTES:
        return 413, {"status": "PAYLOAD_TOO_LARGE"}
    path = _input_path(kind)
    with service.write_lock:
        current = _revision(path)
        if current != body["base_revision"]:
            return 409, {"status": "REVISION_CONFLICT", "revision": current}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if current != ABSENT:
                _backup(path, kind, current)
            _atomic_write(path, data)
        except OSError as exc:
            return 500, {"status": "WRITE_FAILED", "code": type(exc).__name__}
        return 200, {"status": "SAVED", "revision": _revision(path)}


def generate(report_date: Optional[date] = None) -> Result:
    root, day = _root(), report_date or date.today()
    snapshot_path, capacity_path = _input_path("snapshot"), _input_path("capacity")
    out_dir = root / OUTPUT_DIR
    check = preflight(snapshot_path, capacity_path, out_dir, day)
    if check["preflight"] not in ("READY", "READY_WITH_WARNINGS"):
        return 422, {"status": "PREFLIGHT_" + check["preflight"], "checks": check["checks"]}
    try:
        pack = build_wealth_pack(build_book(load_snapshot(snapshot_path)), load_capacity(capacity_path), None, day)
        view = build_view(json.loads(json.dumps(pack)))
        write_pack(pack, out_dir)
        write_view(view, out_dir / VIEW_FILE)
    except DataContractError as exc:
        return 422, {"status": "GENERATION_FAILED", **_code(exc)}
    return 200, {"status": "GENERATED", "preflight": check["preflight"], "checks": check["checks"]}


def status() -> Result:
    files = {kind: _revision(_input_path(kind)) for kind in INPUTS}
    view = _root() / OUTPUT_DIR / VIEW_FILE
    return 200, {"status": "OK", **authority(), "revisions": files, "report_present": view.is_file(),
                 "backups_kept": BACKUPS_KEPT}


ROUTES: Dict[str, Tuple[str, ...]] = {
    "status": ("GET",), "snapshot": ("GET", "PUT"), "capacity": ("GET", "PUT"),
    "validate": ("POST",), "generate": ("POST",),
}


def handle(method: str, name: str, body: Any, service: InputService) -> Result:
    """Dispatch after the server's Host, Origin, token and body checks have passed."""
    if not service.requests.allow():
        return 429, {"status": "RATE_LIMITED"}
    auth = authority()
    if auth["odr_001"] != "RATIFIED":
        return 403, {"status": "AUTHORIZATION_REQUIRED", **auth}
    if method == "PUT":
        if auth["odr_003"] != "RATIFIED":
            return 403, {"status": "AUTHORING_AUTHORIZATION_REQUIRED", **auth}
        if not service.writes.allow():
            return 429, {"status": "RATE_LIMITED"}
        return save_input(name, body, service)
    if name == "generate":
        if body != {}:
            return 400, {"status": "REQUEST_FIELDS_INVALID"}
        if not service.writes.allow():
            return 429, {"status": "RATE_LIMITED"}
        with service.write_lock:
            return generate()
    if name == "validate":
        return validate(body)
    if name == "status":
        return status()
    return read_input(name)


def parse_body(method: str, headers: Mapping[str, str], body: bytes) -> Tuple[Optional[Result], Any]:
    """Content-type, size and JSON checks for PUT/POST; GET must carry no body."""
    if method == "GET":
        return (None, None) if not body else ((400, {"status": "BODY_NOT_ALLOWED"}), None)
    if headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
        return (415, {"status": "CONTENT_TYPE_NOT_ALLOWED"}), None
    if len(body) > MAX_INPUT_BYTES:
        return (413, {"status": "PAYLOAD_TOO_LARGE"}), None
    try:
        return None, json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return (400, {"status": "MALFORMED_JSON"}), None
