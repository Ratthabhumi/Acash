"""Lane A bounded canary readiness (OFFLINE PREPARATION — NO LIVE DISPATCH).

Minimal, tightly scoped preparation for ONE future bounded ETF canary.
Everything here runs offline against injected fake transports; no real
provider HTTP exists anywhere in this module.

Design (hard authority boundary between planning and dispatch):

- ``CanaryApproval``: the claimed operator approval. ``verify_approval()``
  fails closed unless an explicitly configured verifier plug approves; no
  verifier exists in production code (test doubles live in tests only). A
  claimed reference string is NEVER genuine approval by itself.
- ``CanaryPlan``: binds approval + canonical scope + the ACTUAL executing
  runtime SHA. The plan is admissible only when the recomputed scope
  digest equals the approval's ``scope_digest``, the runtime SHA matches
  exactly, and every budget matches the packet. Feed must be exactly one
  of ``iex`` / ``sip`` (no default, no fallback). Approval-window checks
  compare true instants (UTC-normalized), never raw strings.
- ``ReservationJournal``: durable-before-dispatch attempt reservation.
  File fsync is REQUIRED: any flush/sync failure raises and blocks the
  reservation (never silently passed). Directory sync is probed and its
  support level exposed via ``dir_sync_supported``; where unsupported the
  journal still functions but the runtime is classified file-sync-only.
  Reservation file creation is atomic exclusive-create (O_CREAT|O_EXCL).
  Ambiguous failures conserve the attempt: budget consumed, no retry.
- ``CanaryBudget``: hard operation-count and streaming-byte caps; any
  breach fails closed and halts the run.
- ``run_canary_offline``: the single reusable offline orchestration
  (planning → reserve → fake dispatch → settle/halt). Transports are
  duck-typed (any object with ``.get(request_digest, page_token)``);
  ``FakeCanaryTransport`` test doubles live in TESTS only, never here.
- ``canary_sessions``: NYSE CA-1 attribution of the canonical window as
  inclusive calendar dates (end-of-day semantics; regression guard
  against midnight-truncation dropping the final session).

Canonical canary scope (proposal, NOT authority): Alpaca
GET /v2/stocks/bars; VOO/BND/GLD/BIL; 1Day; 2026-09-28..2026-10-02;
adjustments raw+all; one feed; <=12 operations; <=524288 bytes; USD 0.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar

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
PAGE_OUTCOMES: Tuple[str, ...] = ("OK",) + STOP_OUTCOMES

_HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _parse_instant(value: str, context: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware datetime (fail-closed)."""
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
    return moment


def _require_aware_timestamp(value: str, context: str) -> str:
    return _parse_instant(value, context).isoformat()


def _require_runtime_sha(runtime_sha: str) -> str:
    if not isinstance(runtime_sha, str) or not _HEX40_PATTERN.match(runtime_sha):
        raise DataContractError(
            f"CANARY_BAD_RUNTIME_SHA: runtime_sha must be 40-char hex "
            f"git commit SHA, got {runtime_sha!r}."
        )
    return runtime_sha


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


def canary_sessions() -> List[date]:
    """NYSE CA-1 trading sessions of the canonical window (inclusive dates).

    Regression guard: the end bound ``2026-10-02`` is a full session date,
    never a midnight timestamp that would truncate the final session.
    """
    calendar = NyseCa1Calendar()
    start = date.fromisoformat(CANARY_START)
    end = date.fromisoformat(CANARY_END)
    sessions: List[date] = []
    current = start
    while current <= end:
        session = calendar.get_session_or_none(current)
        if session is not None:
            sessions.append(session.session_date)
        current += timedelta(days=1)
    if not sessions or sessions[-1] != end:
        raise DataContractError(
            "CANARY_SESSION_WINDOW_TRUNCATED: final session date missing; "
            "end bound must be end-of-day inclusive."
        )
    return sessions


@dataclass(frozen=True)
class CanaryApproval:
    """Claimed operator approval (reference only — NOT verified approval).

    ``verify_approval()`` fails closed unless an explicitly configured
    verifier plug approves. No verifier exists in production code: test
    doubles live in tests only, and passing one is an explicit, auditable
    test act — never implicit trust.
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
        _require_runtime_sha(self.runtime_sha)
        start = _parse_instant(self.valid_from_utc, "valid_from_utc")
        end = _parse_instant(self.valid_until_utc, "valid_until_utc")
        if start >= end:
            raise DataContractError("CANARY_APPROVAL_EMPTY_WINDOW.")
        if self.max_operations <= 0 or self.max_bytes <= 0:
            raise DataContractError("CANARY_APPROVAL_NONPOSITIVE_BUDGET.")
        if self.paid_budget_usd != CANARY_PAID_BUDGET_USD:
            raise DataContractError("CANARY_APPROVAL_NONZERO_PAID_BUDGET.")

    def is_within_window(self, now_utc: str) -> bool:
        """True instant comparison (UTC-normalized), never string comparison."""
        moment = _parse_instant(now_utc, "now_utc")
        return (
            _parse_instant(self.valid_from_utc, "valid_from_utc")
            <= moment
            <= _parse_instant(self.valid_until_utc, "valid_until_utc")
        )

    def verify_approval(self, verifier: object = None) -> None:
        """Independent authentication seam (fails closed without a verifier)."""
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
    """Admissible bounded plan: approval + scope + executing runtime identity."""

    approval: CanaryApproval
    feed: str
    scope_digest: str
    runtime_sha: str

    @classmethod
    def build(
        cls,
        approval: CanaryApproval,
        feed: str,
        now_utc: str,
        actual_runtime_sha: str,
        verifier: object = None,
    ) -> "CanaryPlan":
        """Build and admit a plan; fails closed on any scope/approval gap."""
        approval.verify_approval(verifier)
        if feed not in CANARY_FEEDS:
            raise DataContractError(
                f"CANARY_PLAN_BAD_FEED: {feed!r} must be exactly one of {list(CANARY_FEEDS)}."
            )
        if not approval.is_within_window(now_utc):
            raise DataContractError("CANARY_PLAN_APPROVAL_EXPIRED.")
        _require_runtime_sha(actual_runtime_sha)
        if actual_runtime_sha != approval.runtime_sha:
            raise DataContractError(
                "CANARY_PLAN_RUNTIME_SHA_MISMATCH: executing runtime does not "
                "match the authorized runtime SHA."
            )
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
        return cls(
            approval=approval, feed=feed, scope_digest=digest,
            runtime_sha=actual_runtime_sha,
        )

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


@dataclass(frozen=True)
class CanaryPage:
    """One fake-transport page outcome (test doubles produce these)."""

    outcome: str
    nbytes: int
    next_token: str = ""

    def __post_init__(self) -> None:
        if self.outcome not in PAGE_OUTCOMES:
            raise DataContractError(
                f"CANARY_PAGE_UNKNOWN_OUTCOME: {self.outcome!r}."
            )
        if (
            not isinstance(self.nbytes, int)
            or isinstance(self.nbytes, bool)
            or self.nbytes < 0
        ):
            raise DataContractError("CANARY_PAGE_BAD_BYTES.")


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


def _sync_file(handle: Any) -> None:
    """Flush + fsync a file handle; ANY failure raises (blocks dispatch)."""
    handle.flush()
    try:
        os.fsync(handle.fileno())
    except OSError as exc:
        raise DataContractError(
            f"CANARY_SYNC_FAILED: required file sync failed: {exc}."
        ) from exc


def _probe_dir_sync(path: Path) -> bool:
    """Probe parent-directory sync support (informational, never fatal)."""
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return False
    try:
        os.fsync(dir_fd)
    except OSError:
        return False
    finally:
        os.close(dir_fd)
    return True


def _sync_dir_best_effort(path: Path) -> None:
    """Attempt directory sync; failures are tolerated (see dir_sync_supported)."""
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

    Each reservation is appended as one JSONL line and file-synced BEFORE
    the corresponding dispatch; any sync failure raises and blocks the
    reservation. Directory sync is probed (``dir_sync_supported``) but,
    where the platform lacks it, does not block file-synced operation —
    the limitation is explicit, not silent. Reservation file creation is
    atomic exclusive-create (O_CREAT|O_EXCL). Ambiguous failures conserve
    the attempt: budget stays consumed, no silent retry.
    """

    def __init__(self, journal_file: Path, dir_sync_supported: bool) -> None:
        if journal_file.suffix != ".jsonl":
            raise DataContractError("CANARY_RESERVATION_BAD_FILE.")
        self._file = journal_file
        self._dir_sync_supported = dir_sync_supported
        self._reserved = 0
        self._completed: Dict[int, str] = {}

    @classmethod
    def create(cls, run_dir: Path) -> "ReservationJournal":
        """Atomically create the reservation file (fail-closed on repeat)."""
        journal_file = run_dir / "reservations.jsonl"
        run_dir.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(journal_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise DataContractError(
                "CANARY_RESERVATION_EXISTS: duplicate journal creation forbidden."
            ) from exc
        except OSError as exc:
            raise DataContractError(
                f"CANARY_RESERVATION_CREATE_FAILED: {exc}."
            ) from exc
        try:
            os.fsync(fd)
        except OSError as exc:
            try:
                os.close(fd)
            finally:
                try:
                    journal_file.unlink()
                except OSError:
                    pass
            raise DataContractError(
                f"CANARY_SYNC_FAILED: required file sync failed: {exc}."
            ) from exc
        os.close(fd)
        _sync_dir_best_effort(journal_file)
        return cls(journal_file, _probe_dir_sync(journal_file))

    @property
    def dir_sync_supported(self) -> bool:
        """Whether parent-directory sync is supported on this filesystem."""
        return self._dir_sync_supported

    def reserve(self, seq: int, request_digest: str) -> None:
        """Reserve attempt ``seq`` for ``request_digest`` (sync before return)."""
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
            _sync_file(handle)
        _sync_dir_best_effort(self._file)
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
            _sync_file(handle)
        _sync_dir_best_effort(self._file)
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


@dataclass
class CanaryResult:
    """Offline run outcome (synthetic verdict, never market evidence)."""

    verdict: str
    operations_used: int
    bytes_observed: int
    dispatches: List[str] = field(default_factory=list)


def run_canary_offline(plan: CanaryPlan, transport: Any, run_dir: Path) -> CanaryResult:
    """Run one bounded offline canary against a duck-typed fake transport.

    The transport must expose ``.get(request_digest, page_token)`` returning
    a ``CanaryPage``. Behavior: two initial adjustment requests, durable
    reservation before each fake dispatch, hard budget caps, page-token
    cycle protection, no retry/feed fallback, halt on 401/403/429/timeout.
    Verdicts: COMPLETE (queue drained) or HALTED_<outcome> (stopped early).
    """
    budget = CanaryBudget(plan.approval.max_operations, plan.approval.max_bytes)
    journal = ReservationJournal.create(run_dir)
    seq = 0
    seen_tokens: set[str] = set()
    dispatches: List[str] = []
    pending: List[Tuple[str, str]] = [(digest, "") for digest in plan.request_digests()]
    while pending:
        request_digest, token = pending.pop(0)
        seq += 1
        budget.reserve_operation()
        journal.reserve(seq, request_digest)
        page = transport.get(request_digest, token)
        if not isinstance(page, CanaryPage):
            raise DataContractError(
                f"CANARY_TRANSPORT_BAD_PAGE: {type(page).__name__}."
            )
        dispatches.append(f"{request_digest}:{token}")
        budget.observe_bytes(page.nbytes)
        if page.outcome in STOP_OUTCOMES:
            journal.settle(seq, page.outcome)
            budget.halt(page.outcome)
            return CanaryResult(
                verdict="HALTED_" + page.outcome,
                operations_used=seq,
                bytes_observed=budget.bytes_observed,
                dispatches=dispatches,
            )
        journal.settle(seq, page.outcome)
        if page.next_token:
            if page.next_token in seen_tokens:
                raise DataContractError(
                    f"CANARY_PAGE_TOKEN_CYCLE: {page.next_token!r} already produced."
                )
            seen_tokens.add(page.next_token)
            pending.append((request_digest, page.next_token))
    return CanaryResult(
        verdict="COMPLETE",
        operations_used=seq,
        bytes_observed=budget.bytes_observed,
        dispatches=dispatches,
    )
