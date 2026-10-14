"""M1.8.1 real-transport execution boundary (STRUCTURALLY DISABLED).

This module defines the narrowest safe path toward a future authorized
real-data canary WITHOUT opening it:

- ``RealTransportBoundary``: allowlist constants (host, method, path) plus a
  ``get()`` that unconditionally fails closed. There is deliberately NO
  socket/HTTP code anywhere in this file: "disabled" is structural, not a
  flag that could be flipped. A future live executor, if ever authorized,
  must live in a SEPARATE audited module and re-prove every gate here.
- ``DurableAttemptJournal``: file-backed append-only run journal. Run
  creation is O_EXCL (an existing run id fails instead of resuming);
  reopening a journal for continuation ALWAYS fails closed — interrupted
  runs are classifiable (``classify_run``) but never resumable under the
  same authority. A restart needs a fresh authority and a fresh run id.
- ``store_raw_evidence``: immutable raw-byte persistence reusing the
  Evidence Plane (external root validation + create-once writers).

All timestamps are caller-supplied ISO-8601 timezone-aware strings (no
wall-clock reads: fully deterministic under test). No credentials are
accepted, stored, or logged anywhere in this module.
"""

from __future__ import annotations

import json
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

JOURNAL_DIRNAME: str = "lane_a_runs"
RUN_MARKER_FILENAME: str = "run.json"
ATTEMPTS_FILENAME: str = "attempts.jsonl"
COMPLETION_FILENAME: str = "completion.json"


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
    if not run_id or not run_id.strip() or "/" in run_id or "\\" in run_id:
        raise DataContractError(
            f"TRANSPORT_BAD_RUN_ID: {run_id!r}."
        )
    return root / JOURNAL_DIRNAME / run_id.strip()


class DurableAttemptJournal:
    """File-backed append-only attempt journal with enforced no-resume.

    - ``create_run`` uses O_EXCL directory creation: a colliding run id
      fails instead of resuming or overwriting.
    - ``record_attempt`` appends one JSONL line; sequence numbers must
      increase strictly (gapless is NOT required: failed reservations still
      consume sequence space, matching dispatch accounting).
    - ``close_run`` writes the completion marker exactly once.
    - ``open_existing`` ALWAYS fails closed: interrupted runs are observable
      via ``classify_run`` but never continuable under the same authority.
    """

    def __init__(self, run_dir: Path, run_id: str) -> None:
        self._run_dir = run_dir
        self._run_id = run_id
        self._last_seq = 0
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
        """Create a fresh run journal (fails if the run id already exists)."""
        resolved = validate_external_evidence_root(root)
        if not authority_ref or not authority_ref.strip():
            raise DataContractError("TRANSPORT_RUN_EMPTY_AUTHORITY_REF.")
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
            "runtime_sha": runtime_sha,
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
        """Read-only run classification: COMPLETE, INTERRUPTED, or MISSING."""
        resolved = validate_external_evidence_root(root)
        run_dir = _run_dir(resolved, run_id)
        if not (run_dir / RUN_MARKER_FILENAME).is_file():
            return "MISSING"
        if (run_dir / COMPLETION_FILENAME).is_file():
            return "COMPLETE"
        return "INTERRUPTED"

    def record_attempt(self, record: AttemptRecord) -> None:
        """Append one attempt line; sequence must increase strictly."""
        if (
            not isinstance(record.seq, int)
            or isinstance(record.seq, bool)
            or record.seq <= self._last_seq
        ):
            raise DataContractError(
                f"TRANSPORT_ATTEMPT_SEQ_INVALID: seq {record.seq!r} must be an "
                f"int strictly greater than {self._last_seq}."
            )
        if record.bytes_observed < 0:
            raise DataContractError(
                "TRANSPORT_ATTEMPT_NEGATIVE_BYTES."
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
        if status not in ("COMPLETE", "ABORTED"):
            raise DataContractError(
                f"TRANSPORT_CLOSE_INVALID_STATUS: {status!r}."
            )
        completed = _require_aware_timestamp(completed_at_utc, "completed_at_utc")
        write_immutable_json(
            self._run_dir / COMPLETION_FILENAME,
            {"run_id": self._run_id, "status": status, "completed_at_utc": completed},
        )


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
    Evidence Plane. No secrets may appear in metadata (caller responsibility;
    values are never inspected here to avoid logging them anywhere).
    """
    resolved = validate_external_evidence_root(root)
    if not name or not name.strip() or "/" in name or "\\" in name:
        raise DataContractError(f"TRANSPORT_EVIDENCE_BAD_NAME: {name!r}.")
    if not isinstance(payload, (bytes, bytearray)) or not payload:
        raise DataContractError("TRANSPORT_EVIDENCE_EMPTY_PAYLOAD.")
    if not isinstance(metadata, Mapping):
        raise DataContractError("TRANSPORT_EVIDENCE_METADATA_NOT_MAPPING.")
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
            "metadata": dict(metadata),
        },
    )
    return {
        "path": str(run_dir / f"{name.strip()}.bin"),
        "content_sha256": digest,
        "receipt_sha256": manifest_digest,
        "byte_count": len(payload),
    }
