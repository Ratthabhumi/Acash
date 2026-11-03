"""Owner-directed authoring of the two private input files for the dashboard Setup Wizard.

Routes live under ``/api/upi/input/`` on the loopback private-view server, behind its Host,
Origin and session-token checks. Reading, in-memory validation and report generation need
ODR-001; saving additionally needs ODR-003 (``OWNER_LOCAL_INPUT_AUTHORING_AUTHORIZED``) with its
exact identity, dependency and scope. Both records are re-read on every request and again
before each file replacement. Only ``data/private/snapshot.json`` and
``data/private/capacity.json`` can be written, always together: two separate paths cannot be
replaced atomically, so a save is a journaled transaction that restores the previous pair
from backups if any replacement fails or the process stops midway. Reports are built in a
fresh generation directory and published by atomically replacing the view and its generation
record. Responses carry statuses, codes and field locations, never amounts; nothing is logged.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
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
AUTHORING_DECISION_ID = "ODR_UPI_LOCAL_INPUT_AUTHORING_003"
AUTHORING_CAPABILITY = "OWNER_LOCAL_INPUT_AUTHORING_AUTHORIZED"
OBSERVATION_DECISION_ID = "ODR_UPI_PRIVATE_OBSERVATION_001"
PRIVATE_DIR = Path("data/private")
INPUTS: Dict[str, Tuple[str, str]] = {
    "snapshot": ("snapshot.json", SCHEMA_V1_2),
    "capacity": ("capacity.json", CAPACITY_SCHEMA),
}
SCOPE_FILES = sorted((PRIVATE_DIR / name).as_posix() for name, _ in INPUTS.values())
SCOPE_SCHEMAS = sorted(schema for _, schema in INPUTS.values())
OUTPUT_DIR = PRIVATE_DIR / "out"
VIEW_FILE = "upi_view.json"
GENERATION_RECORD = "report_generation.json"
GENERATIONS_DIR = OUTPUT_DIR / "generations"
GENERATIONS_KEPT = 5
BACKUP_DIR = PRIVATE_DIR / "backups"
BACKUPS_KEPT = 20
JOURNAL = PRIVATE_DIR / ".input_transaction.json"
_BACKUP_NAME = re.compile(r"^(snapshot|capacity)-\d{8}T\d{12}Z-[0-9a-f]{12}\.json$")
ABSENT = "ABSENT"
DATA_CLASS = "OWNER_PRIVATE_OBSERVATION"
WRITES_PER_MINUTE = 20
REQUESTS_PER_MINUTE = 240

Result = Tuple[int, Dict[str, Any]]


class RateLimiter:
    """Sliding window (one minute unless given); a refused request is not counted."""

    def __init__(self, limit: int, clock: Callable[[], float] = time.monotonic, window: float = 60) -> None:
        self._limit, self._clock, self._lock, self._window = limit, clock, threading.Lock(), window
        self._hits: Deque[float] = deque()

    def allow(self) -> bool:
        with self._lock:
            now = self._clock()
            while self._hits and now - self._hits[0] >= self._window:
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


class AuthorityLost(Exception):
    """ODR-001 or ODR-003 stopped being RATIFIED during a save."""


def _code(exc: Exception) -> Dict[str, str]:
    text = str(exc)
    code, _, where = text.partition(":")
    return {"code": code.rstrip(". "), "where": where.strip().rstrip(".")[:200]}


def _root() -> Path:
    return po._repo_root()


def _is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _private_dir(*parts: str) -> Path:
    """``data/private`` (or a fixed subdirectory) with no symlink or junction on the way."""
    root = _root().resolve()
    path = root / PRIVATE_DIR
    for candidate in (root / "data", path, *[path.joinpath(*parts[:i + 1]) for i in range(len(parts))]):
        if _is_link(candidate):
            raise DataContractError("INPUT_PATH_LINK_REFUSED: data/private must not contain links.")
    return path.joinpath(*parts)


def _input_path(kind: str) -> Path:
    path = _private_dir() / INPUTS[kind][0]
    if _is_link(path):
        raise DataContractError(f"INPUT_PATH_LINK_REFUSED: {kind}.")
    return path


def _revision(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return ABSENT


def authoring_state() -> str:
    """ODR-003 state: RATIFIED only with exact identity, ODR-001 dependency and the two-file scope."""
    path = _root() / AUTHORING_RECORD
    state = odr_state(path, None, AUTHORING_CAPABILITY)
    if state != "RATIFIED":
        return state
    doc = json.loads(path.read_text(encoding="utf-8"))
    try:
        date.fromisoformat(doc["ratified_on"])
    except ValueError:
        return "RECORD_INVALID"
    if doc.get("decision_id") != AUTHORING_DECISION_ID:
        return "RECORD_IDENTITY_MISMATCH"
    if doc.get("requires") != [OBSERVATION_DECISION_ID]:
        return "RECORD_DEPENDENCY_INVALID"
    for key, expected in (("scope_schemas", SCOPE_SCHEMAS), ("scope_files", SCOPE_FILES)):
        value = doc.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value) or sorted(value) != expected:
            return "RECORD_SCOPE_INVALID"
    return "RATIFIED"


def authority() -> Dict[str, str]:
    return {"odr_001": odr_state(None, SCHEMA_V1_2), "odr_003": authoring_state()}


def write_authorized() -> bool:
    return (all(odr_state(None, schema) == "RATIFIED" for _, schema in INPUTS.values())
            and authoring_state() == "RATIFIED")


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
    if summary.get("report_type") == "EVIDENCE_ONLY_REPORT":
        warnings.append({"code": "EVIDENCE_ONLY_REPORT", "where": "report_type"})
    value_only = sum(len(a.observed_value_positions) for a in snapshot.accounts)
    unknown = sum(s.classification == "UNKNOWN" for s in snapshot.securities)
    if value_only:
        warnings.append({"code": "VALUE_ONLY_HOLDINGS", "where": f"count={value_only}"})
    if unknown:
        warnings.append({"code": "UNKNOWN_CLASSIFICATION", "where": f"count={unknown}"})
    if evidence:
        for acct in evidence[snapshot.reporting_currency]["accounts"]:
            total = acct["account_total"]
            status = total["status"] if isinstance(total, dict) else str(total)
            if status not in ("RECONCILED", "CONSISTENT_WITH_DISPLAY_ROUNDING", "NOT_REPORTED"):
                warnings.append({"code": status, "where": acct["account_ref"]})
    return [], warnings


def _check_capacity(doc: Any) -> List[Dict[str, str]]:
    if not isinstance(doc, dict) or doc.get("schema") != CAPACITY_SCHEMA or doc.get("data_class") != DATA_CLASS:
        return [{"code": "INPUT_CAPACITY_SCHEMA_OR_DATA_CLASS", "where": "schema,data_class"}]
    try:
        parse_capacity(doc)
    except DataContractError as exc:
        return [_code(exc)]
    return []


def _check(kind: str, doc: Any, report_date: Optional[date]) -> Dict[str, Any]:
    errors, warnings = _check_snapshot(doc, report_date) if kind == "snapshot" else (_check_capacity(doc), [])
    return {"status": "INVALID" if errors else "VALID", "errors": errors, "warnings": warnings}


def validate(body: Any, report_date: Optional[date] = None) -> Result:
    if not isinstance(body, dict) or not body or set(body) - set(INPUTS):
        return 400, {"status": "REQUEST_FIELDS_INVALID"}
    out = {kind: _check(kind, doc, report_date or date.today()) for kind, doc in body.items()}
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


def _backup(path: Path, kind: str, revision: str) -> str:
    backups = _private_dir("backups")
    backups.mkdir(parents=True, exist_ok=True)
    name = f"{kind}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{revision[:12]}.json"
    _atomic_write(backups / name, path.read_bytes())
    return name


def _prune_backups() -> None:
    backups = _private_dir("backups")
    for kind in INPUTS:
        for old in sorted(backups.glob(f"{kind}-*.json"))[:-BACKUPS_KEPT]:
            old.unlink()


def _restore(journal: Mapping[str, Any]) -> None:
    """Put back the pre-transaction pair; idempotent, so it is safe after a partial replacement."""
    files = journal["files"]
    if not isinstance(files, dict) or set(files) != set(INPUTS):
        raise DataContractError("INPUT_JOURNAL_INVALID: unexpected files.")
    previous: Dict[str, Optional[bytes]] = {}
    for kind, entry in files.items():
        if not isinstance(entry, dict):
            raise DataContractError("INPUT_JOURNAL_INVALID: entry.")
        backup = entry.get("backup")
        if backup is None:
            if entry.get("previous_revision") != ABSENT:
                raise DataContractError("INPUT_JOURNAL_INVALID: missing backup.")
            previous[kind] = None
            continue
        if not isinstance(backup, str) or not _BACKUP_NAME.match(backup) or not backup.startswith(kind):
            raise DataContractError("INPUT_JOURNAL_INVALID: backup name.")
        data = (_private_dir("backups") / backup).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry.get("previous_revision"):
            raise DataContractError("INPUT_JOURNAL_INVALID: backup digest.")
        previous[kind] = data
    for kind, content in previous.items():
        target = _input_path(kind)
        if content is not None:
            _atomic_write(target, content)
        elif target.exists():
            target.unlink()
    for leftover in _private_dir().glob(f".*.{journal['transaction']}.staged"):
        leftover.unlink()


def recover() -> str:
    """Finish an interrupted save by restoring the previous pair: NONE, RECOVERED or RECOVERY_REQUIRED."""
    path = _private_dir() / JOURNAL.name
    if not path.exists():
        return "NONE"
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(journal, dict) or not re.fullmatch(r"[0-9a-f]{16}", str(journal.get("transaction"))):
            raise DataContractError("INPUT_JOURNAL_INVALID: transaction id.")
        _restore(journal)
    except (OSError, ValueError, KeyError, DataContractError):
        return "RECOVERY_REQUIRED"
    path.unlink()
    return "RECOVERED"


def _commit(data: Dict[str, bytes], current: Dict[str, str]) -> Result:
    txn = secrets.token_hex(8)
    _private_dir().mkdir(parents=True, exist_ok=True)
    _private_dir("backups")
    paths = {kind: _input_path(kind) for kind in INPUTS}
    staged = {kind: path.with_name(f".{path.name}.{txn}.staged") for kind, path in paths.items()}
    journal_path = _private_dir() / JOURNAL.name
    try:
        for kind, path in staged.items():
            with open(path, "xb") as handle:
                handle.write(data[kind])
                handle.flush()
                os.fsync(handle.fileno())
    except OSError:
        for path in staged.values():
            path.unlink(missing_ok=True)
        raise
    files = {kind: {"previous_revision": current[kind],
                    "backup": None if current[kind] == ABSENT else _backup(paths[kind], kind, current[kind])}
             for kind in INPUTS}
    journal = {"transaction": txn, "files": files}
    _atomic_write(journal_path, json.dumps(journal, sort_keys=True).encode("utf-8"))
    try:
        for kind in INPUTS:
            if not write_authorized():
                raise AuthorityLost()
            os.replace(staged[kind], paths[kind])
    except (OSError, AuthorityLost) as exc:
        try:
            _restore(journal)
            journal_path.unlink()
        except (OSError, DataContractError):
            return 500, {"status": "WRITE_FAILED_RECOVERY_PENDING", "code": type(exc).__name__}
        status = "AUTHORING_AUTHORIZATION_REQUIRED" if isinstance(exc, AuthorityLost) else "WRITE_FAILED_ROLLED_BACK"
        return (403 if isinstance(exc, AuthorityLost) else 500), {"status": status, "code": type(exc).__name__,
                                                                  **authority()}
    journal_path.unlink()
    _prune_backups()
    return 200, {"status": "SAVED", "revisions": {kind: _revision(path) for kind, path in paths.items()}}


def save_inputs(body: Any, service: InputService) -> Result:
    """Validate both documents, check both revisions, then replace the pair as one recoverable transaction."""
    if not isinstance(body, dict) or set(body) != {*INPUTS, "base_revisions", "confirm_replace"}:
        return 400, {"status": "REQUEST_FIELDS_INVALID"}
    bases = body["base_revisions"]
    if body["confirm_replace"] is not True:
        return 400, {"status": "CONFIRMATION_REQUIRED"}
    if not isinstance(bases, dict) or set(bases) != set(INPUTS) or not all(isinstance(v, str) for v in bases.values()):
        return 400, {"status": "REQUEST_FIELDS_INVALID"}
    checks = {kind: _check(kind, body[kind], None) for kind in INPUTS}
    if any(c["status"] == "INVALID" for c in checks.values()):
        return 422, {"status": "INVALID", **checks}
    data = {kind: (json.dumps(body[kind], indent=2, ensure_ascii=False) + "\n").encode("utf-8") for kind in INPUTS}
    if any(len(d) > MAX_INPUT_BYTES for d in data.values()):
        return 413, {"status": "PAYLOAD_TOO_LARGE"}
    with service.write_lock:
        try:
            if recover() == "RECOVERY_REQUIRED":
                return 409, {"status": "INPUT_RECOVERY_REQUIRED"}
            if not write_authorized():
                return 403, {"status": "AUTHORING_AUTHORIZATION_REQUIRED", **authority()}
            current = {kind: _revision(_input_path(kind)) for kind in INPUTS}
            if current != bases:
                return 409, {"status": "REVISION_CONFLICT", "revisions": current}
            return _commit(data, current)
        except DataContractError as exc:
            return 403, {"status": "INPUT_PATH_REFUSED", **_code(exc)}
        except OSError as exc:
            return 500, {"status": "WRITE_FAILED", "code": type(exc).__name__}


def _generation_record() -> Dict[str, Any]:
    out = _private_dir("out")
    record_path, view_path = out / GENERATION_RECORD, out / VIEW_FILE
    if not view_path.is_file():
        return {"status": "NO_REPORT"}
    if not record_path.is_file():
        return {"status": "RECORD_ABSENT"}
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        view_sha = json.loads(view_path.read_text(encoding="utf-8")).get("view_sha256")
    except (OSError, ValueError):
        return {"status": "RECORD_UNREADABLE"}
    if not isinstance(record, dict) or record.get("view_sha256") != view_sha:
        return {"status": "RECORD_MISMATCH"}
    current = {kind: _revision(_input_path(kind)) for kind in INPUTS}
    return {"status": "CONSISTENT", "generation_id": record.get("generation_id"),
            "generated_at": record.get("generated_at"), "preflight": record.get("preflight"),
            "inputs_changed_since": record.get("input_revisions") != current}


def generate(report_date: Optional[date] = None) -> Result:
    """Build pack and view into a new generation directory, then publish view and record atomically."""
    if recover() == "RECOVERY_REQUIRED":
        return 409, {"status": "INPUT_RECOVERY_REQUIRED"}
    day = report_date or date.today()
    snapshot_path, capacity_path = _input_path("snapshot"), _input_path("capacity")
    revisions = {kind: _revision(_input_path(kind)) for kind in INPUTS}
    out = _private_dir("out")
    check = preflight(snapshot_path, capacity_path, out, day)
    if check["preflight"] not in ("READY", "READY_WITH_WARNINGS"):
        return 422, {"status": "PREFLIGHT_" + check["preflight"], "checks": check["checks"]}
    stamp = datetime.now(timezone.utc)
    generation_id = f"{stamp.strftime('%Y%m%dT%H%M%S%fZ')}-{secrets.token_hex(4)}"
    gen_dir = _private_dir("out", "generations") / generation_id
    previous_view = (out / VIEW_FILE).read_bytes() if (out / VIEW_FILE).is_file() else None
    published = False
    try:
        pack = build_wealth_pack(build_book(load_snapshot(snapshot_path)), load_capacity(capacity_path), None, day)
        view = build_view(json.loads(json.dumps(pack)))
        write_pack(pack, gen_dir)
        view_bytes = write_view(view, gen_dir / VIEW_FILE).read_bytes()
        if json.loads(view_bytes).get("view_sha256") != view["view_sha256"]:
            raise DataContractError("GENERATION_VIEW_MISMATCH.")
        if {kind: _revision(_input_path(kind)) for kind in INPUTS} != revisions:
            raise DataContractError("GENERATION_INPUTS_CHANGED: inputs changed while the report was built.")
        record = {"generation_id": generation_id, "generated_at": stamp.isoformat(timespec="seconds"),
                  "input_revisions": revisions, "view_sha256": view["view_sha256"],
                  "pack_sha256": pack["pack_sha256"], "preflight": check["preflight"]}
        record_bytes = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
        _atomic_write(gen_dir / GENERATION_RECORD, record_bytes)
        _atomic_write(out / VIEW_FILE, view_bytes)
        published = True
        _atomic_write(out / GENERATION_RECORD, record_bytes)
    except (DataContractError, OSError) as exc:
        if published:
            try:
                if previous_view is None:
                    (out / VIEW_FILE).unlink()
                else:
                    _atomic_write(out / VIEW_FILE, previous_view)
            except OSError:
                return 500, {"status": "GENERATION_PUBLISH_INCOMPLETE", "code": type(exc).__name__}
        shutil.rmtree(gen_dir, ignore_errors=True)
        if isinstance(exc, DataContractError):
            return 422, {"status": "GENERATION_FAILED", **_code(exc)}
        return 500, {"status": "GENERATION_FAILED", "code": type(exc).__name__}
    for old in sorted(p for p in gen_dir.parent.iterdir() if p.is_dir() and p != gen_dir)[:-GENERATIONS_KEPT + 1]:
        shutil.rmtree(old, ignore_errors=True)
    return 200, {"status": "GENERATED", "generation_id": generation_id, "preflight": check["preflight"],
                 "checks": check["checks"]}


def status() -> Result:
    files = {kind: _revision(_input_path(kind)) for kind in INPUTS}
    pending = (_private_dir() / JOURNAL.name).exists()
    return 200, {"status": "OK", **authority(), "revisions": files, "report": _generation_record(),
                 "recovery_pending": pending, "backups_kept": BACKUPS_KEPT}


ROUTES: Dict[str, Tuple[str, ...]] = {
    "status": ("GET",), "snapshot": ("GET",), "capacity": ("GET",), "inputs": ("PUT",),
    "validate": ("POST",), "generate": ("POST",),
}


def handle(method: str, name: str, body: Any, service: InputService) -> Result:
    """Dispatch after the server's Host, Origin, token and body checks have passed."""
    if not service.requests.allow():
        return 429, {"status": "RATE_LIMITED"}
    auth = authority()
    if auth["odr_001"] != "RATIFIED":
        return 403, {"status": "AUTHORIZATION_REQUIRED", **auth}
    try:
        if name == "inputs":
            if auth["odr_003"] != "RATIFIED":
                return 403, {"status": "AUTHORING_AUTHORIZATION_REQUIRED", **auth}
            if not service.writes.allow():
                return 429, {"status": "RATE_LIMITED"}
            return save_inputs(body, service)
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
    except DataContractError as exc:
        return 403, {"status": "INPUT_PATH_REFUSED", **_code(exc)}


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
