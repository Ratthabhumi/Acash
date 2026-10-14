"""M1.8.1 real-transport execution boundary (STRUCTURALLY DISABLED).

This module defines the narrowest safe path toward a future authorized
real-data canary WITHOUT opening it:

- ``RealTransportBoundary``: allowlist constants (host, method, path) plus a
  ``get()`` that unconditionally fails closed. There is deliberately NO
  socket/HTTP code anywhere in this file: "disabled" is structural, not a
  flag that could be flipped. A future live executor, if ever authorized,
  must live in a SEPARATE audited module and re-prove every gate here.
- ``DurableAttemptJournal``: file-backed append-only run journal. Run
  creation uses atomic directory creation (``mkdir(exist_ok=False)``: a
  colliding run id fails instead of resuming); reopening a journal for
  continuation ALWAYS fails closed — interrupted runs are classifiable
  (``classify_run``) but never resumable under the same authority. A
  restart needs a fresh authority and a fresh run id. Closed journals
  (COMPLETE or ABORTED) reject further appends and duplicate closure.
- ``store_raw_evidence``: immutable raw-byte persistence reusing the
  Evidence Plane (external root validation + create-once writers) with an
  allowlisted, secret-safe metadata schema. ``verify_evidence_pair``
  classifies raw/receipt completeness deterministically.

Persistence contract (honest, minimal)::

    FILE_BACKED_CREATE_ONCE_NOT_CRASH_DURABILITY_VERIFIED

Create-once files and the append-only journal are NOT proven crash-durable
(no fsync/directory-sync proof, no fault-injection durability evidence):
unit tests only establish file existence and content, never survival of a
power loss or process crash. A future active dispatcher MUST separately
prove durable-before-dispatch reservation persistence first. Until then,
real provider dispatch stays BLOCKED.

All timestamps are caller-supplied ISO-8601 timezone-aware strings (no
wall-clock reads: fully deterministic under test). No credentials are
accepted, stored, or logged anywhere in this module. ``authority_ref`` is
a caller-supplied reference string and is NOT proof of external human
approval: future real dispatch requires independent approval verification.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_authority import redact_secrets
from acash.evidence.roots import validate_external_evidence_root
from acash.evidence.writer import write_immutable_bytes, write_immutable_json

ALLOWED_HOSTS: tuple[str, ...] = ("data.alpaca.markets",)
ALLOWED_METHODS: tuple[str, ...] = ("GET",)
ALLOWED_PATHS: tuple[str, ...] = ("/v2/stocks/bars",)

STORAGE_CONTRACT: str = "FILE_BACKED_CREATE_ONCE_NOT_CRASH_DURABILITY_VERIFIED"

JOURNAL_DIRNAME: str = "lane_a_runs"
RUN_MARKER_FILENAME: str = "run.json"
ATTEMPTS_FILENAME: str = "attempts.jsonl"
COMPLETION_FILENAME: str = "completion.json"

COMPLETION_COMPLETE: str = "COMPLETE"
COMPLETION_ABORTED: str = "ABORTED"

# Minimal allowlisted metadata schema: field name -> required value type.
# Anything else (including any secret-bearing field) fails closed.
ALLOWED_METADATA_SCHEMA: Dict[str, type] = {
    "feed": str,
    "timeframe": str,
    "adjustment": str,
    "symbols": str,
    "page_index": int,
    "request_index": int,
    "byte_count": int,
    "note": str,
}

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(secret|token|password|credential|private|apca|api[_-]?key|"
    r"authorization|bearer|session)"
)
_HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def check_request_allowlist(host: str, method: str, path: str) -> None:
    """Fail-closed allowlist gate for any future real request (pure check)."""
    if host not in ALLOWED_HOSTS:
        raise DataContractError(
            f"TRANSPORT_HOST_NOT_ALLOWLISTED: {host!r}."
        )
    if method not in ALLOWED_METHODS:
        raise DataContractError(
            f"TRANSPORT_METHOD_NOT_ALLOWLISTED: {method!r}."
        )
    if path not in ALLOWED_PATHS:
        raise DataContractError(
            f"TRANSPORT_PATH_NOT_ALLOWLISTED: {path!r}."
        )


def _require_aware_timestamp(value: str, context: str) -> str:
    try:
        moment = datetime.fromisoformat(str(value))
    except (ValueError, TypeError) as exc:
        raise DataContractError(
            f"TRANSPORT_MALFORMED_TIME: {context}: {value!r}."
        ) from exc
    if moment.tzinfo is None:
        raise DataContractError(
            f"TRANSPORT_NAIVE_TIME: {context} must be timezone-aware."
        )
    return moment.isoformat()


def _require_runtime_sha(runtime_sha: str) -> str:
    if not isinstance(runtime_sha, str) or not _HEX40_PATTERN.match(runtime_sha):
        raise DataContractError(
            f"TRANSPORT_BAD_RUNTIME_SHA: runtime_sha must be 40-char hex "
            f"git commit SHA, got {runtime_sha!r}."
        )
    return runtime_sha


@dataclass(frozen=True)
class RealTransportBoundary:
    """Disabled real-transport boundary: allowlist checks only, zero I/O.

    ``get()`` ALWAYS fails closed. There is intentionally no enabled flag,
    no socket, no session, and no credential surface: enabling real network
    I/O requires a separate audited executor module, never a flag flip here.
    """

    def get(self, host: str, method: str, path: str) -> None:
        """Refuse every request: real transport is not implemented here."""
        check_request_allowlist(host, method, path)
        raise DataContractError(
            "TRANSPORT_DISABLED: no real network executor exists in this "
            "module. Real provider HTTP requires a separately authorized "
            "and audited executor; this boundary only validates scope."
        )


@dataclass(frozen=True)
class AttemptRecord:
    """One durable attempt journal line (all fields caller-supplied)."""

    seq: int
    kind: str
    outcome: str
    bytes_observed: int
    recorded_at_utc: str
    detail: str = ""


def _run_dir(root: Path, run_id: str) -> Path:
    if not run_id or not run_id.strip():
        raise DataContractError(
            f"TRANSPORT_BAD_RUN_ID: {run_id!r}."
        )
    cleaned = run_id.strip()
    if cleaned in (".", "..") or "/" in cleaned or "\\" in cleaned:
        raise DataContractError(
            f"TRANSPORT_BAD_RUN_ID: {run_id!r}."
        )
    return root / JOURNAL_DIRNAME / cleaned


def _read_completion_record(run_dir: Path) -> Dict[str, Any]:
    """Read and validate the completion record; fail closed on corruption."""
    completion = run_dir / COMPLETION_FILENAME
    try:
        raw = completion.read_bytes()
    except OSError as exc:
        raise DataContractError(
            f"TRANSPORT_COMPLETION_UNREADABLE: {exc}."
        ) from exc
    try:
        record = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise DataContractError(
            "TRANSPORT_COMPLETION_CORRUPT: completion record is not valid JSON."
        ) from exc
    if not isinstance(record, dict):
        raise DataContractError(
            "TRANSPORT_COMPLETION_CORRUPT: completion record must be a JSON object."
        )
    status = record.get("status")
    if status not in (COMPLETION_COMPLETE, COMPLETION_ABORTED):
        raise DataContractError(
            f"TRANSPORT_COMPLETION_CORRUPT: unknown status {status!r}."
        )
    if record.get("run_id") != run_dir.name:
        raise DataContractError(
            "TRANSPORT_COMPLETION_CORRUPT: run_id mismatch."
        )
    _require_aware_timestamp(str(record.get("completed_at_utc")), "completed_at_utc")
    return record


class DurableAttemptJournal:
    """File-backed append-only attempt journal with enforced no-resume.

    - ``create_run`` uses atomic directory creation (``mkdir(exist_ok=False)``):
      a colliding run id fails instead of resuming or overwriting. This is
      directory-collision prevention, NOT the O_EXCL file-creation API.
    - ``record_attempt`` appends one JSONL line; sequence numbers must
      increase strictly. Appends after closure fail closed (checked both
      in-memory and on disk, since separate objects share no state).
    - ``close_run`` writes the completion marker exactly once; duplicate
      closure fails closed.
    - ``open_existing`` ALWAYS fails closed: interrupted runs are observable
      via ``classify_run`` but never continuable under the same authority.
    - ``classify_run`` distinguishes MISSING / INTERRUPTED / COMPLETE /
      ABORTED / CORRUPT by reading the completion record, never by filename
      existence alone.
    """

    def __init__(self, run_dir: Path, run_id: str) -> None:
        self._run_dir = run_dir
        self._run_id = run_id
        self._last_seq = 0
        self._closed = False
        marker = run_dir / RUN_MARKER_FILENAME
        if not marker.is_file():
            raise DataContractError(
                f"TRANSPORT_RUN_MARKER_MISSING: {run_dir}."
            )

    @classmethod
    def create_run(
        cls,
        root: Path,
        run_id: str,
        authority_ref: str,
        runtime_sha: str,
        created_at_utc: str,
    ) -> "DurableAttemptJournal":
        """Create a fresh run journal (fails if the run id already exists).

        ``authority_ref`` is a caller-supplied reference string: it records
        which authority the caller claims, and is NOT proof of external
        human approval.
        """
        resolved = validate_external_evidence_root(root)
        if not authority_ref or not authority_ref.strip():
            raise DataContractError("TRANSPORT_RUN_EMPTY_AUTHORITY_REF.")
        sha = _require_runtime_sha(runtime_sha)
        created = _require_aware_timestamp(created_at_utc, "created_at_utc")
        run_dir = _run_dir(resolved, run_id)
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise DataContractError(
                f"TRANSPORT_RUN_EXISTS_NO_RESUME: {run_dir} already exists; "
                "create a fresh run id under a fresh authority instead."
            ) from exc
        except OSError as exc:
            raise DataContractError(
                f"TRANSPORT_RUN_MKDIR_FAILED: {run_dir}: {exc}."
            ) from exc
        marker = {
            "run_id": run_dir.name,
            "authority_ref": authority_ref,
            "runtime_sha": sha,
            "created_at_utc": created,
        }
        write_immutable_json(run_dir / RUN_MARKER_FILENAME, marker)
        return cls(run_dir, run_dir.name)

    @classmethod
    def open_existing(cls, root: Path, run_id: str) -> "DurableAttemptJournal":
        """Reopening is ALWAYS forbidden: no resume under any authority."""
        raise DataContractError(
            "TRANSPORT_RUN_NO_RESUME: journals are append-only evidence; "
            f"run {run_id!r} cannot be reopened. Classify it and start fresh."
        )

    @staticmethod
    def classify_run(root: Path, run_id: str) -> str:
        """Read-only classification: MISSING/INTERRUPTED/COMPLETE/ABORTED/CORRUPT."""
        resolved = validate_external_evidence_root(root)
        run_dir = _run_dir(resolved, run_id)
        if not (run_dir / RUN_MARKER_FILENAME).is_file():
            return "MISSING"
        if not (run_dir / COMPLETION_FILENAME).is_file():
            return "INTERRUPTED"
        try:
            record = _read_completion_record(run_dir)
        except DataContractError:
            return "CORRUPT"
        status = record["status"]
        if status == COMPLETION_COMPLETE:
            return "COMPLETE"
        if status == COMPLETION_ABORTED:
            return "ABORTED"
        return "CORRUPT"

    def _ensure_open(self) -> None:
        if self._closed or (self._run_dir / COMPLETION_FILENAME).is_file():
            raise DataContractError(
                "TRANSPORT_JOURNAL_CLOSED: no appends after run closure."
            )

    def record_attempt(self, record: AttemptRecord) -> None:
        """Append one attempt line; sequence must increase strictly."""
        self._ensure_open()
        if (
            not isinstance(record.seq, int)
            or isinstance(record.seq, bool)
            or record.seq <= self._last_seq
        ):
            raise DataContractError(
                f"TRANSPORT_ATTEMPT_SEQ_INVALID: seq {record.seq!r} must be an "
                f"int strictly greater than {self._last_seq}."
            )
        if (
            not isinstance(record.bytes_observed, int)
            or isinstance(record.bytes_observed, bool)
            or record.bytes_observed < 0
        ):
            raise DataContractError(
                "TRANSPORT_ATTEMPT_BAD_BYTES: bytes_observed must be a non-negative int."
            )
        _require_aware_timestamp(record.recorded_at_utc, "recorded_at_utc")
        line = json.dumps(
            {
                "seq": record.seq,
                "kind": record.kind,
                "outcome": record.outcome,
                "bytes_observed": record.bytes_observed,
                "recorded_at_utc": record.recorded_at_utc,
                "detail": redact_secrets(record.detail),
            },
            sort_keys=True,
        )
        try:
            with open(self._run_dir / ATTEMPTS_FILENAME, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as exc:
            raise DataContractError(
                f"TRANSPORT_JOURNAL_APPEND_FAILED: {exc}."
            ) from exc
        self._last_seq = record.seq

    def close_run(self, status: str, completed_at_utc: str) -> None:
        """Write the completion marker exactly once (fail-closed on repeat)."""
        if status not in (COMPLETION_COMPLETE, COMPLETION_ABORTED):
            raise DataContractError(
                f"TRANSPORT_CLOSE_INVALID_STATUS: {status!r}."
            )
        if self._closed or (self._run_dir / COMPLETION_FILENAME).is_file():
            raise DataContractError(
                "TRANSPORT_RUN_ALREADY_CLOSED: duplicate closure is forbidden."
            )
        completed = _require_aware_timestamp(completed_at_utc, "completed_at_utc")
        write_immutable_json(
            self._run_dir / COMPLETION_FILENAME,
            {"run_id": self._run_id, "status": status, "completed_at_utc": completed},
        )
        self._closed = True


def _validate_evidence_metadata(metadata: Mapping[str, Any]) -> Dict[str, Any]:
    """Fail-closed allowlisted metadata validation (never sanitize-and-accept)."""
    if not isinstance(metadata, Mapping):
        raise DataContractError("TRANSPORT_EVIDENCE_METADATA_NOT_MAPPING.")
    validated: Dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise DataContractError(
                f"TRANSPORT_EVIDENCE_METADATA_BAD_KEY: {key!r}."
            )
        if _SENSITIVE_KEY_PATTERN.search(key):
            raise DataContractError(
                f"TRANSPORT_EVIDENCE_METADATA_SENSITIVE_KEY: {key!r}."
            )
        expected = ALLOWED_METADATA_SCHEMA.get(key)
        if expected is None:
            raise DataContractError(
                f"TRANSPORT_EVIDENCE_METADATA_UNKNOWN_KEY: {key!r}."
            )
        if expected is int:
            if not isinstance(value, int) or isinstance(value, bool):
                raise DataContractError(
                    f"TRANSPORT_EVIDENCE_METADATA_BAD_TYPE: {key!r} must be int."
                )
        elif expected is str:
            if not isinstance(value, str):
                raise DataContractError(
                    f"TRANSPORT_EVIDENCE_METADATA_BAD_TYPE: {key!r} must be str."
                )
            if redact_secrets(value) != value:
                raise DataContractError(
                    f"TRANSPORT_EVIDENCE_METADATA_SECRET_VALUE: {key!r}."
                )
        else:
            raise DataContractError(
                f"TRANSPORT_EVIDENCE_METADATA_BAD_SCHEMA: {key!r}."
            )
        validated[key] = value
    return validated


def store_raw_evidence(
    root: Path,
    run_id: str,
    name: str,
    payload: bytes,
    metadata: Mapping[str, Any],
) -> Dict[str, Any]:
    """Persist one raw payload immutably under an external evidence root.

    Returns the evidence receipt (path, SHA-256, metadata). Overwrites fail
    closed; repository-local and HYP_011-colliding roots are rejected by the
    Evidence Plane. Metadata must satisfy the allowlisted schema: unknown
    keys, secret-bearing keys, and secret-bearing values are rejected
    (never silently sanitized). The raw write and receipt write are two
    separate create-once operations — NOT an atomic transaction: use
    ``verify_evidence_pair`` to classify incomplete pairs.
    """
    resolved = validate_external_evidence_root(root)
    if not name or not name.strip() or "/" in name or "\\" in name:
        raise DataContractError(f"TRANSPORT_EVIDENCE_BAD_NAME: {name!r}.")
    if not isinstance(payload, (bytes, bytearray)) or not payload:
        raise DataContractError("TRANSPORT_EVIDENCE_EMPTY_PAYLOAD.")
    safe_metadata = _validate_evidence_metadata(metadata)
    run_dir = _run_dir(resolved, run_id)
    if not (run_dir / RUN_MARKER_FILENAME).is_file():
        raise DataContractError(
            f"TRANSPORT_EVIDENCE_UNKNOWN_RUN: no journal marker for {run_id!r}; "
            "evidence attaches only to a created run."
        )
    digest = write_immutable_bytes(run_dir / f"{name.strip()}.bin", bytes(payload))
    manifest_digest = write_immutable_json(
        run_dir / f"{name.strip()}.receipt.json",
        {
            "run_id": run_dir.name,
            "name": name.strip(),
            "content_sha256": digest,
            "byte_count": len(payload),
            "metadata": safe_metadata,
        },
    )
    return {
        "path": str(run_dir / f"{name.strip()}.bin"),
        "content_sha256": digest,
        "receipt_sha256": manifest_digest,
        "byte_count": len(payload),
    }


def verify_evidence_pair(root: Path, run_id: str, name: str) -> str:
    """Deterministic read-only classification of a raw/receipt artifact pair.

    Returns one of: ADMISSIBLE, MISSING, ORPHAN_RAW, ORPHAN_RECEIPT,
    CORRUPT_RECEIPT, HASH_MISMATCH. Incomplete pairs are NEVER admissible.
    """
    resolved = validate_external_evidence_root(root)
    if not name or not name.strip() or "/" in name or "\\" in name:
        raise DataContractError(f"TRANSPORT_EVIDENCE_BAD_NAME: {name!r}.")
    run_dir = _run_dir(resolved, run_id)
    raw_file = run_dir / f"{name.strip()}.bin"
    receipt_file = run_dir / f"{name.strip()}.receipt.json"
    raw_exists = raw_file.is_file()
    receipt_exists = receipt_file.is_file()
    if not raw_exists and not receipt_exists:
        return "MISSING"
    if raw_exists and not receipt_exists:
        return "ORPHAN_RAW"
    if receipt_exists and not raw_exists:
        return "ORPHAN_RECEIPT"
    try:
        receipt = json.loads(receipt_file.read_bytes().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return "CORRUPT_RECEIPT"
    if not isinstance(receipt, dict):
        return "CORRUPT_RECEIPT"
    try:
        raw_bytes = raw_file.read_bytes()
    except OSError:
        return "CORRUPT_RECEIPT"
    actual = hashlib.sha256(raw_bytes).hexdigest()
    if receipt.get("content_sha256") != actual:
        return "HASH_MISMATCH"
    if receipt.get("byte_count") != len(raw_bytes):
        return "HASH_MISMATCH"
    if receipt.get("run_id") != run_dir.name or receipt.get("name") != name.strip():
        return "CORRUPT_RECEIPT"
    return "ADMISSIBLE"
