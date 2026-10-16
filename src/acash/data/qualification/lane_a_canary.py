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
  duck-typed (any object with ``.get(request_digest, page_token)``) under
  an explicit TRUSTED-INJECTION boundary: the runner executes inside a
  trusted offline test process and trusts the injected object to be a
  scripted fake. This is NOT a sandbox against hostile Python objects; a
  deliberately network-capable injected object would violate the caller's
  offline assumption. Observed bytes are SYNTHETIC accounting from
  ``CanaryPage.nbytes``, never proof of streaming-HTTP enforcement.
- Verdict ``TRANSPORT_PAGINATION_COMPLETE`` means the pagination queue
  drained inside budget. It is NOT data qualification: symbol coverage,
  session coverage, OHLCV validity, corporate actions, and
  point-in-time correctness are separate gates (see M1.8 rehearsal
  contracts for the eventual validation stage).
- Terminology contract (never collapsed):
  OFFLINE_TESTED != PROVIDER_VERIFIED;
  FILE_SYNCED != CRASH_DURABLE;
  RUNTIME_SHA_EQUALS_CLAIM != INDEPENDENT_ATTESTATION;
  APPROVAL_REFERENCE != AUTHENTICATED_APPROVAL;
  SYNTHETIC_BYTE_COUNT != STREAMING_HTTP_BYTE_ENFORCEMENT;
  TRANSPORT_PAGINATION_COMPLETE != DATA_QUALIFIED.
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
from acash.data.qualification.lane_a_authority import (
    LANE_A_ALLOWED_FEEDS,
    LANE_A_CURRENCY,
    LANE_A_ENDPOINT_PATH,
    LANE_A_HISTORICAL_END,
    LANE_A_HISTORICAL_START,
    LANE_A_PAGE_LIMIT,
    LANE_A_PROVIDER,
    LANE_A_SORT,
    LaneAPlannedRequest,
    LaneAScope,
    canonical_query_parameters,
)

# Single canonical HTTP authority: M1.7. This module defines NO competing
# request specification. The constants below are display/budget mirrors only;
# every request is built as a LaneAPlannedRequest and serialized exclusively
# through M1.7's canonical_query_parameters(). No ISSUED LaneAAuthority is
# ever fabricated here: scope/request objects carry no authority status.
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
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def canary_scope(feed: str) -> LaneAScope:
    """Build the canary scope as an M1.7 LaneAScope (validated by M1.7).

    LaneAScope.__post_init__ enforces the canonical universe, timeframe,
    exact historical window, provider, feed allowlist, and paid budget, so
    any divergence from M1.7 fails here, not downstream.
    """
    return LaneAScope(
        symbols=frozenset(CANARY_SYMBOLS),
        timeframe=CANARY_TIMEFRAME,
        start_date=date.fromisoformat(CANARY_START),
        end_date=date.fromisoformat(CANARY_END),
        adjustments=frozenset(CANARY_ADJUSTMENTS),
        provider=LANE_A_PROVIDER,
        feed=feed,
        paid_budget_usd=0,
    )


def canary_planned_requests(feed: str) -> Tuple[LaneAPlannedRequest, ...]:
    """Build the canary requests exactly as M1.7 plans them.

    Same construction as plan_lane_a_requests (sorted symbols, one entry
    per sorted adjustment, M1.7 sort/limit/currency/endpoint) but WITHOUT
    requiring an ISSUED authority object: no authority status is fabricated.
    """
    scope = canary_scope(feed)
    symbols = tuple(sorted(scope.symbols))
    planned: List[LaneAPlannedRequest] = []
    for adjustment in sorted(scope.adjustments):
        planned.append(
            LaneAPlannedRequest(
                symbols=symbols,
                adjustment=adjustment,
                timeframe=scope.timeframe,
                start_date=scope.start_date,
                end_date=scope.end_date,
                provider=scope.provider,
                endpoint_path=LANE_A_ENDPOINT_PATH,
                feed=scope.feed,
                sort=LANE_A_SORT,
                limit=LANE_A_PAGE_LIMIT,
                currency=LANE_A_CURRENCY,
            )
        )
    if len(planned) > CANARY_MAX_OPERATIONS:
        raise DataContractError(
            f"CANARY_PLAN_TOO_LARGE: {len(planned)} base requests exceed "
            f"the canary operation cap {CANARY_MAX_OPERATIONS}."
        )
    return tuple(planned)


def canonical_scope_digest(
    requests: Sequence[LaneAPlannedRequest], max_operations: int, max_bytes: int
) -> str:
    """Deterministic SHA-256 binding the ACTUAL canonical 9-tuples + budgets.

    The digest covers M1.7's canonical_query_parameters() output per
    request (symbols, timeframe, start, end, adjustment, feed, sort, limit,
    currency) — never a simplified offline summary. Continuation identity
    additionally binds the verbatim page token (see continuation_digest).
    """
    document = {
        "max_bytes": max_bytes,
        "max_operations": max_operations,
        "requests": [list(canonical_query_parameters(request)) for request in requests],
    }
    return hashlib.sha256(
        json.dumps(document, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _first_page_digest(request: LaneAPlannedRequest) -> str:
    """Identity of a first-page dispatch: canonical params, empty token."""
    return hashlib.sha256(
        json.dumps(
            {
                "params": list(canonical_query_parameters(request)),
                "page_token": "",
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def continuation_digest(
    request: LaneAPlannedRequest, page_token: str
) -> str:
    """Identity of a continuation dispatch: canonical params + verbatim token."""
    if not page_token:
        raise DataContractError("CANARY_CONTINUATION_EMPTY_TOKEN.")
    return hashlib.sha256(
        json.dumps(
            {
                "params": list(canonical_query_parameters(request)),
                "page_token": page_token,
            },
            sort_keys=True,
        ).encode("utf-8")
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
    """Admissible bounded plan: approval + M1.7 requests + runtime identity."""

    approval: CanaryApproval
    feed: str
    scope_digest: str
    runtime_sha: str
    requests: Tuple[LaneAPlannedRequest, ...] = ()

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
        if feed not in CANARY_FEEDS or feed not in LANE_A_ALLOWED_FEEDS:
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
        if approval.paid_budget_usd != CANARY_PAID_BUDGET_USD:
            raise DataContractError("CANARY_PLAN_NONZERO_PAID_BUDGET.")
        requests = canary_planned_requests(feed)
        digest = canonical_scope_digest(
            requests, approval.max_operations, approval.max_bytes
        )
        if digest != approval.scope_digest:
            raise DataContractError("CANARY_PLAN_SCOPE_DIGEST_MISMATCH.")
        return cls(
            approval=approval, feed=feed, scope_digest=digest,
            runtime_sha=actual_runtime_sha, requests=requests,
        )

    def request_digests(self) -> List[Tuple[int, str]]:
        """Canonical per-request identities: (index, first-page digest)."""
        return [
            (index, _first_page_digest(request))
            for index, request in enumerate(self.requests)
        ]


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
        self._poisoned = False

    @classmethod
    def create(cls, run_dir: Path) -> "ReservationJournal":
        """Atomically create the reservation file (fail-closed on repeat).

        If the initial required sync fails, the file is LEFT IN PLACE (never
        silently unlinked): a later create attempt for the same run fails
        with EXISTS, so an ambiguous namespace can never be silently
        recreated and reused.
        """
        journal_file = run_dir / "reservations.jsonl"
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DataContractError(
                f"CANARY_RESERVATION_CREATE_FAILED: {exc}."
            ) from exc
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
            except OSError:
                pass
            raise DataContractError(
                f"CANARY_SYNC_FAILED: required file sync failed: {exc}. "
                "The run namespace is ambiguous and must not be reused."
            ) from exc
        try:
            os.close(fd)
        except OSError as exc:
            raise DataContractError(
                f"CANARY_SYNC_FAILED: failed closing reservation file: {exc}."
            ) from exc
        _sync_dir_best_effort(journal_file)
        return cls(journal_file, _probe_dir_sync(journal_file))

    @property
    def dir_sync_supported(self) -> bool:
        """Whether parent-directory sync is supported on this filesystem."""
        return self._dir_sync_supported

    def _ensure_usable(self) -> None:
        if self._poisoned:
            raise DataContractError(
                "CANARY_JOURNAL_POISONED: a required sync failed; this journal "
                "is unusable. On-disk state is ambiguous — classify it by "
                "reading, then continue only under a fresh run."
            )

    def reserve(self, seq: int, request_digest: str) -> None:
        """Reserve attempt ``seq`` for ``request_digest`` (sync before return)."""
        self._ensure_usable()
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
        try:
            with open(self._file, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                _sync_file(handle)
        except (DataContractError, OSError) as exc:
            self._poisoned = True
            if isinstance(exc, DataContractError):
                raise
            raise DataContractError(
                f"CANARY_JOURNAL_IO_FAILED: reserve write failed: {exc}. "
                "Journal poisoned; classify on-disk state by reading."
            ) from exc
        _sync_dir_best_effort(self._file)
        self._reserved = seq

    def settle(self, seq: int, outcome: str) -> None:
        """Record the outcome of a reserved attempt (no budget refund)."""
        self._ensure_usable()
        if seq <= 0 or seq > self._reserved or seq in self._completed:
            raise DataContractError(
                f"CANARY_SETTLE_UNKNOWN_SEQ: {seq!r}."
            )
        line = json.dumps({"event": "settled", "seq": seq, "outcome": outcome}, sort_keys=True)
        try:
            with open(self._file, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                _sync_file(handle)
        except (DataContractError, OSError) as exc:
            self._poisoned = True
            if isinstance(exc, DataContractError):
                raise
            raise DataContractError(
                f"CANARY_JOURNAL_IO_FAILED: settle write failed: {exc}. "
                "Journal poisoned; classify on-disk state by reading."
            ) from exc
        _sync_dir_best_effort(self._file)
        self._completed[seq] = outcome

    def read_reservations(self) -> List[Mapping[str, Any]]:
        """Read back all reservation records (deterministic inspection).

        Structurally invalid events (unknown event names, missing keys,
        wrong types) are NEVER promoted into trusted evidence: they fail
        closed as CORRUPT.
        """
        records: List[Mapping[str, Any]] = []
        try:
            content = self._file.read_text(encoding="utf-8")
        except OSError as exc:
            raise DataContractError(
                f"CANARY_JOURNAL_UNREADABLE: {exc}."
            ) from exc
        for raw in content.splitlines():
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except ValueError as exc:
                raise DataContractError("CANARY_RESERVATION_CORRUPT.") from exc
            if not isinstance(record, dict):
                raise DataContractError("CANARY_RESERVATION_CORRUPT.")
            event = record.get("event")
            if event == "reserved":
                if (
                    not isinstance(record.get("seq"), int)
                    or not isinstance(record.get("request_digest"), str)
                ):
                    raise DataContractError("CANARY_RESERVATION_CORRUPT.")
            elif event == "settled":
                if (
                    not isinstance(record.get("seq"), int)
                    or not isinstance(record.get("outcome"), str)
                ):
                    raise DataContractError("CANARY_RESERVATION_CORRUPT.")
            else:
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


def audit_reservation_history(records: Sequence[Mapping[str, Any]]) -> Dict[int, str]:
    """Enforce the complete legal event state machine (fail-closed).

    Rules: reserved seqs are positive ints (bool rejected), strictly
    increasing, never duplicated, with 64-hex digests; settled seqs must
    reference a preceding reservation exactly once with a known outcome;
    torn/corrupt/contradictory histories raise. Returns settled outcomes.
    No invalid history is admitted as a trustworthy consumed-attempt ledger.
    """
    reserved: set[int] = set()
    settled: Dict[int, str] = {}
    last_reserved_seq = 0
    for record in records:
        event = record.get("event")
        seq = record.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq <= 0:
            raise DataContractError(
                f"CANARY_HISTORY_BAD_SEQ: {seq!r}."
            )
        if event == "reserved":
            digest = record.get("request_digest")
            if not isinstance(digest, str) or not _HEX64_PATTERN.match(digest):
                raise DataContractError(
                    "CANARY_HISTORY_BAD_DIGEST: request_digest must be 64-char hex."
                )
            if seq in reserved:
                raise DataContractError(
                    f"CANARY_HISTORY_DUP_RESERVED: seq {seq}."
                )
            if seq <= last_reserved_seq:
                raise DataContractError(
                    f"CANARY_HISTORY_NONMONOTONIC: seq {seq} after {last_reserved_seq}."
                )
            reserved.add(seq)
            last_reserved_seq = seq
        elif event == "settled":
            outcome = record.get("outcome")
            if not isinstance(outcome, str) or outcome not in PAGE_OUTCOMES:
                raise DataContractError(
                    f"CANARY_HISTORY_BAD_OUTCOME: {outcome!r}."
                )
            if seq not in reserved:
                raise DataContractError(
                    f"CANARY_HISTORY_SETTLE_WITHOUT_RESERVE: seq {seq}."
                )
            if seq in settled:
                raise DataContractError(
                    f"CANARY_HISTORY_DUP_SETTLE: seq {seq}."
                )
            settled[seq] = outcome
        else:
            raise DataContractError(
                f"CANARY_HISTORY_UNKNOWN_EVENT: {event!r}."
            )
    return settled


def verify_request_window_against_sessions() -> List[date]:
    """Cross-check the canonical request window against CA-1 sessions.

    Asserts the M1.7-planned request window exactly spans the attributed
    sessions with the end date included end-of-day. This verifies CALENDAR
    coverage only: the provider's timestamp interpretation of the ``end``
    parameter remains a PRE-EXECUTION verification gate (unresolved without
    a network probe; HYP_010 midnight-end lesson). Never call this proof of
    provider response bounds.
    """
    requests = canary_planned_requests("iex")
    sessions = canary_sessions()
    for request in requests:
        if request.start_date != sessions[0] or request.end_date != sessions[-1]:
            raise DataContractError(
                "CANARY_WINDOW_SESSION_MISMATCH: request window does not "
                "exactly span the attributed sessions."
            )
    return sessions


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
    a ``CanaryPage``. Behavior: two initial adjustment requests (M1.7
    canonical 9-tuples), durable reservation before each fake dispatch,
    hard budget caps, per-chain page-token cycle protection keyed by
    (request index, token), continuation digests binding canonical params +
    verbatim token, no retry/feed fallback, halt on 401/403/429/timeout.
    Verdicts: TRANSPORT_PAGINATION_COMPLETE (queue drained; NOT data
    qualification) or HALTED_<outcome> (stopped early).
    """
    budget = CanaryBudget(plan.approval.max_operations, plan.approval.max_bytes)
    journal = ReservationJournal.create(run_dir)
    seq = 0
    seen_chain_tokens: set[Tuple[int, str]] = set()
    dispatches: List[str] = []
    pending: List[Tuple[int, str]] = [
        (index, "") for index, _ in plan.request_digests()
    ]
    while pending:
        index, token = pending.pop(0)
        request = plan.requests[index]
        if token == "":
            request_digest = _first_page_digest(request)
        else:
            request_digest = continuation_digest(request, token)
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
            chain_key = (index, page.next_token)
            if chain_key in seen_chain_tokens:
                raise DataContractError(
                    f"CANARY_PAGE_TOKEN_CYCLE: {page.next_token!r} already "
                    "produced in this request chain."
                )
            seen_chain_tokens.add(chain_key)
            pending.append((index, page.next_token))
    return CanaryResult(
        verdict="TRANSPORT_PAGINATION_COMPLETE",
        operations_used=seq,
        bytes_observed=budget.bytes_observed,
        dispatches=dispatches,
    )
