"""Lane A bounded canary readiness (OFFLINE PREPARATION — NO LIVE DISPATCH).

Minimal, tightly scoped preparation for ONE future bounded ETF canary.
Everything here runs offline against injected fake transports; no real
provider HTTP exists anywhere in this module.

Design (hard authority boundary between planning and dispatch):

- ``CanaryApproval``: the claimed operator approval. ``verify_approval()``
  ALWAYS fails closed ("no independent verifier configured"): a
  valid-looking reference string is NEVER genuine approval. Real dispatch
  requires a separately reviewed authentication plug-in, never a flag flip.
- ``CanaryPlan``: binds approval + canonical scope. The plan is admissible
  only when the recomputed scope digest equals the approval's
  ``scope_digest`` and every budget (operations, bytes, paid) matches the
  packet. Feed must be exactly one of ``iex`` / ``sip`` (no default, no
  fallback).
- ``ReservationJournal``: durable-before-dispatch attempt reservation.
  Each reservation is appended and flushed with ``os.fsync`` (file and
  parent directory, best-effort per platform) BEFORE the corresponding
  fake dispatch. Ambiguous failures conserve the attempt: budget consumed,
  no silent retry. Storage contract is documented per record; crash
  survival beyond a clean process exit is NOT claimed beyond what the
  fsync evidence in tests demonstrates on the test filesystem.
- ``CanaryBudget``: hard operation-count and streaming-byte caps; any
  breach fails closed and halts the run.
- ``FakeCanaryTransport`` lives in TESTS only, never here.

Canonical canary scope (proposal, NOT authority): Alpaca
GET /v2/stocks/bars; VOO/BND/GLD/BIL; 1Day; 2026-09-28..2026-10-02;
adjustments raw+all; one feed; <=12 operations; <=524288 bytes; USD 0.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError

CANARY_SYMBOLS: Tuple[str, ...] = ("VOO", "BND", "GLD", "BIL")
CANARY_TIMEFRAME: str = "1Day"
CANARY_START: str = "2026-09-28"
CANARY_END: str = "2026-10-02"
CANARY_ADJUSTMENTS: Tuple[str, ...] = ("raw", "all")
CANARY_FEEDS: Tuple[str, ...] = ("iex", "sip")
CANARY_MAX_OPERATIONS: int = 12
CANARY_MAX_BYTES: int = 524288
CANARY_PAID_BUDGET_USD: str = "0.00"

STOP_OUTCOMES: Tuple[str, ...] = ("HTTP_401", "HTTP_403", "HTTP_429", "TIMEOUT_AMBIGUOUS")


def _require_aware_timestamp(value: str, context: str) -> str:
    try:
        moment = datetime.fromisoformat(str(value))
    except (ValueError, TypeError) as exc:
        raise DataContractError(
            f"CANARY_MALFORMED_TIME: {context}: {value!r}."
        ) from exc
    if moment.tzinfo is None:
        raise DataContractError(
            f"CANARY_NAIVE_TIME: {context} must be timezone-aware."
        )
    return moment.isoformat()


def canonical_scope_digest(
    symbols: Sequence[str],
    timeframe: str,
    start: str,
    end: str,
    adjustments: Sequence[str],
    feed: str,
    max_operations: int,
    max_bytes: int,
    paid_budget_usd: str,
) -> str:
    """Deterministic SHA-256 over the canonical scope document."""
    document = {
        "adjustments": list(adjustments),
        "end": end,
        "feed": feed,
        "max_bytes": max_bytes,
        "max_operations": max_operations,
        "paid_budget_usd": paid_budget_usd,
        "start": start,
        "symbols": list(symbols),
        "timeframe": timeframe,
    }
    return hashlib.sha256(
        json.dumps(document, sort_keys=True).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class CanaryApproval:
    """Claimed operator approval (reference only — NOT verified approval).

    ``verify_approval()`` always fails closed: no independent verifier is
    configured in this module. A separately reviewed authentication
    mechanism must replace this seam before any real dispatch.
    """

    approval_ref: str
    scope_digest: str
    runtime_sha: str
    valid_from_utc: str
    valid_until_utc: str
    max_operations: int
    max_bytes: int
    paid_budget_usd: str

    def __post_init__(self) -> None:
        if not self.approval_ref or not self.approval_ref.strip():
            raise DataContractError("CANARY_APPROVAL_EMPTY_REF.")
        if not isinstance(self.scope_digest, str) or len(self.scope_digest) != 64:
            raise DataContractError("CANARY_APPROVAL_BAD_SCOPE_DIGEST.")
        _require_aware_timestamp(self.valid_from_utc, "valid_from_utc")
        _require_aware_timestamp(self.valid_until_utc, "valid_until_utc")
        if self.valid_from_utc >= self.valid_until_utc:
            raise DataContractError("CANARY_APPROVAL_EMPTY_WINDOW.")
        if self.max_operations <= 0 or self.max_bytes <= 0:
            raise DataContractError("CANARY_APPROVAL_NONPOSITIVE_BUDGET.")
        if self.paid_budget_usd != CANARY_PAID_BUDGET_USD:
            raise DataContractError("CANARY_APPROVAL_NONZERO_PAID_BUDGET.")

    def is_within_window(self, now_utc: str) -> bool:
        moment = _require_aware_timestamp(now_utc, "now_utc")
        return self.valid_from_utc <= moment <= self.valid_until_utc

    def verify_approval(self, verifier: object = None) -> None:
        """Independent authentication seam.

        Fails closed unless an explicitly configured verifier object with a
        ``check(approval) -> bool`` method approves. No verifier exists in
        production code: test doubles live in tests only, and passing one
        is an explicit, auditable test act — never implicit trust.
        """
        check = getattr(verifier, "check", None)
        if not callable(check):
            raise DataContractError(
                "CANARY_APPROVAL_UNVERIFIED: no independent approval verifier "
                "is configured. A claimed reference is not genuine approval."
            )
        if check(self) is not True:
            raise DataContractError(
                "CANARY_APPROVAL_REJECTED: the configured verifier refused "
                "this approval reference."
            )


@dataclass(frozen=True)
class CanaryPlan:
    """Admissible bounded plan: approval + canonical scope, digest-bound."""

    approval: CanaryApproval
    feed: str
    scope_digest: str

    @classmethod
    def build(
        cls, approval: CanaryApproval, feed: str, now_utc: str, verifier: object = None
    ) -> "CanaryPlan":
        """Build and admit a plan; fails closed on any scope/approval gap."""
        approval.verify_approval(verifier)
        if feed not in CANARY_FEEDS:
            raise DataContractError(
                f"CANARY_PLAN_BAD_FEED: {feed!r} must be exactly one of {list(CANARY_FEEDS)}."
            )
        if not approval.is_within_window(now_utc):
            raise DataContractError("CANARY_PLAN_APPROVAL_EXPIRED.")
        if approval.max_operations > CANARY_MAX_OPERATIONS:
            raise DataContractError("CANARY_PLAN_OPERATION_BUDGET_EXCEEDED.")
        if approval.max_bytes > CANARY_MAX_BYTES:
            raise DataContractError("CANARY_PLAN_BYTE_BUDGET_EXCEEDED.")
        digest = canonical_scope_digest(
            CANARY_SYMBOLS, CANARY_TIMEFRAME, CANARY_START, CANARY_END,
            CANARY_ADJUSTMENTS, feed, approval.max_operations,
            approval.max_bytes, approval.paid_budget_usd,
        )
        if digest != approval.scope_digest:
            raise DataContractError("CANARY_PLAN_SCOPE_DIGEST_MISMATCH.")
        return cls(approval=approval, feed=feed, scope_digest=digest)

    def request_digests(self) -> List[str]:
        """Canonical per-adjustment request digests (2 initial requests)."""
        digests: List[str] = []
        for adjustment in CANARY_ADJUSTMENTS:
            digests.append(
                hashlib.sha256(
                    json.dumps(
                        {
                            "adjustment": adjustment,
                            "feed": self.feed,
                            "scope": self.scope_digest,
                        },
                        sort_keys=True,
                    ).encode("utf-8")
                ).hexdigest()
            )
        return digests


class CanaryBudget:
    """Hard operation-count and streaming-byte caps (fail-closed)."""

    def __init__(self, max_operations: int, max_bytes: int) -> None:
        self._max_operations = max_operations
        self._max_bytes = max_bytes
        self.operations_used = 0
        self.bytes_observed = 0
        self.halted = False

    def reserve_operation(self) -> None:
        """Consume one operation; fails closed at the cap."""
        if self.halted:
            raise DataContractError("CANARY_BUDGET_HALTED.")
        if self.operations_used >= self._max_operations:
            self.halted = True
            raise DataContractError("CANARY_BUDGET_OPERATIONS_EXHAUSTED.")
        self.operations_used += 1

    def observe_bytes(self, nbytes: int) -> None:
        """Stream bytes into the cap; any breach halts the run."""
        if self.halted:
            raise DataContractError("CANARY_BUDGET_HALTED.")
        if not isinstance(nbytes, int) or isinstance(nbytes, bool) or nbytes < 0:
            raise DataContractError("CANARY_BUDGET_BAD_BYTE_COUNT.")
        if self.bytes_observed + nbytes > self._max_bytes:
            self.halted = True
            raise DataContractError("CANARY_BUDGET_BYTES_EXCEEDED.")
        self.bytes_observed += nbytes

    def halt(self, reason: str) -> None:
        """Explicit stop (401/403/429/timeout/ambiguous failure)."""
        self.halted = True
        if reason not in STOP_OUTCOMES and reason != "BUDGET":
            raise DataContractError(f"CANARY_HALT_UNKNOWN_REASON: {reason!r}.")


def _fsync_file_and_dir(path: Path) -> None:
    """Flush file and parent directory (best-effort per platform)."""
    with open(path, "a+b") as handle:
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


class ReservationJournal:
    """Durable-before-dispatch attempt reservation (offline-tested).

    Each reservation is appended as one JSONL line and fsync'd (file +
    parent directory) BEFORE the corresponding dispatch. Ambiguous failures
    conserve the attempt: budget stays consumed, no silent retry, and the
    run must halt or continue only under a fresh authority.
    """

    def __init__(self, journal_file: Path) -> None:
        if journal_file.suffix != ".jsonl":
            raise DataContractError("CANARY_RESERVATION_BAD_FILE.")
        self._file = journal_file
        self._reserved = 0
        self._completed: Dict[int, str] = {}

    @classmethod
    def create(cls, run_dir: Path) -> "ReservationJournal":
        """Create the reservation file exactly once (fail-closed on repeat)."""
        journal_file = run_dir / "reservations.jsonl"
        if journal_file.exists():
            raise DataContractError("CANARY_RESERVATION_EXISTS.")
        run_dir.mkdir(parents=True, exist_ok=True)
        journal_file.write_bytes(b"")
        _fsync_file_and_dir(journal_file)
        return cls(journal_file)

    def reserve(self, seq: int, request_digest: str) -> None:
        """Reserve attempt ``seq`` for ``request_digest`` (fsync before return)."""
        if not isinstance(seq, int) or isinstance(seq, bool) or seq <= self._reserved:
            raise DataContractError(
                f"CANARY_RESERVATION_BAD_SEQ: {seq!r}."
            )
        if not isinstance(request_digest, str) or len(request_digest) != 64:
            raise DataContractError("CANARY_RESERVATION_BAD_DIGEST.")
        line = json.dumps(
            {"event": "reserved", "seq": seq, "request_digest": request_digest},
            sort_keys=True,
        )
        with open(self._file, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        _fsync_file_and_dir(self._file)
        self._reserved = seq

    def settle(self, seq: int, outcome: str) -> None:
        """Record the outcome of a reserved attempt (no budget refund)."""
        if seq <= 0 or seq > self._reserved or seq in self._completed:
            raise DataContractError(
                f"CANARY_SETTLE_UNKNOWN_SEQ: {seq!r}."
            )
        line = json.dumps({"event": "settled", "seq": seq, "outcome": outcome}, sort_keys=True)
        with open(self._file, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        _fsync_file_and_dir(self._file)
        self._completed[seq] = outcome

    def read_reservations(self) -> List[Mapping[str, Any]]:
        """Read back all reservation records (deterministic inspection)."""
        records: List[Mapping[str, Any]] = []
        for raw in self._file.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except ValueError as exc:
                raise DataContractError("CANARY_RESERVATION_CORRUPT.") from exc
            if not isinstance(record, dict):
                raise DataContractError("CANARY_RESERVATION_CORRUPT.")
            records.append(record)
        return records

    @property
    def reserved_count(self) -> int:
        """Number of reserved attempts (budget consumed, never refunded)."""
        return self._reserved

    @property
    def completed(self) -> Mapping[int, str]:
        """Settled outcomes by sequence (informational only)."""
        return dict(self._completed)
