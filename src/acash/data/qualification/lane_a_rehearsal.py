"""Lane A offline acquisition rehearsal (M1.8 preparation, zero network).

Thin execution layer over the M1.7 authority contracts
(``lane_a_authority``): it replays a validated authority's planned requests
against an INJECTED transport, enforcing dispatch-before-send budget
accounting, byte caps, pagination discipline, and response-contract checks.
The only transports that may ever be injected in tests are synthetic fakes;
this module opens no socket, loads no credentials, and performs no retry.

Outcome taxonomy (returned, never silent):
- PASS: every planned request exhausted its pages, coverage is complete for
  all scope symbols x expected sessions, and every page was structurally valid.
- PARTIAL: a budget (operations or bytes) was exhausted with pages remaining.
- REJECTED: a provider-side contract violation (bad JSON, missing symbol,
  duplicate cursor, off-calendar bar, non-monotonic bars).
- BLOCKED: an execution prerequisite failed (entitlement denial, transport
  failure/timeout, rate-limit stop).
- UNKNOWN: reserved for admission-stage questions this runner cannot answer
  (e.g. historical PIT vintage); never emitted here.

Authority/scope problems (missing, unissued, expired, out-of-scope plan)
RAISE via the M1.7 validators instead of returning verdicts — identical to
``dry_run_validate`` conventions.

Durability boundary (explicit non-guarantee): accounting lives in the passed
``LaneARequestLedger`` (in-process memory only). There is no resume across
process restarts; a restarted run needs a fresh authority and ledger. This is
marked BLOCKED for crash-safe persistence, with a test proving a fresh
ledger restarts accounting from zero.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union, final
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.lane_a_authority import (
    LaneAAuthority,
    LaneAPlannedRequest,
    LaneARequestLedger,
    canonical_query_parameters,
    plan_lane_a_requests,
    redact_secrets,
    validate_authority,
    validate_planned_request,
)

# Trading-day convention for daily-bar date attribution (Alpaca daily bars
# are New-York-date stamped; a UTC calendar date is NOT the trading date).
_NY_TZ = ZoneInfo("America/New_York")


class RehearsalVerdict(str, Enum):
    """Unambiguous acquisition-rehearsal outcome."""

    PASS = "PASS"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class RehearsalTransportError(Exception):
    """Transport-level failure (timeout, disconnect) raised by fake transports."""


@dataclass(frozen=True)
class RehearsalHttpResponse:
    """One synthetic transport response (test fakes only, never live)."""

    status_code: int
    content: bytes
    headers: Mapping[str, str]


@final
class ScriptedTransport:
    """Sealed offline transport: canned script, call recording, zero I/O.

    This is the ONLY transport ``run_rehearsal`` accepts (enforced by an
    exact-type gate: ``type(transport) is ScriptedTransport``): arbitrary
    callers cannot inject a live HTTP adapter, and even a subclass
    overriding ``.get()`` fails closed with zero dispatches, because
    ``@final`` alone does not prohibit subclassing at runtime. There is
    deliberately no URL, credential, socket, or retry surface anywhere on
    this class. A future real transport, if ever authorized, lives in a
    separate audited API — never here.
    """

    def __init__(
        self, script: Sequence[Union[RehearsalHttpResponse, Exception]]
    ) -> None:
        self._script = list(script)
        self.calls: List[Tuple[str, Tuple[Tuple[str, str], ...]]] = []

    def get(
        self, path: str, params: Sequence[Tuple[str, str]]
    ) -> RehearsalHttpResponse:
        """Serve the next canned page (or raise the canned failure)."""
        self.calls.append((path, tuple(params)))
        if not self._script:
            raise RehearsalTransportError(
                "ScriptedTransport script exhausted: unexpected request."
            )
        action = self._script.pop(0)
        if isinstance(action, Exception):
            raise action
        return action


@dataclass(frozen=True)
class PageReceipt:
    """Immutable evidence receipt for one fetched page."""

    adjustment: str
    page_index: int
    byte_count: int
    content_sha256: str
    outcome: str
    next_token_seen: Optional[str]


@dataclass(frozen=True)
class RehearsalManifest:
    """Deterministic synthetic acquisition manifest (no wall-clock fields).

    ``synthetic_dispatch_attempts`` counts budgeted offline dispatches;
    ``actual_network_requests_issued`` is ALWAYS zero here — fake-transport
    calls must never be reported as real provider HTTP, or a downstream
    research ledger could mistake rehearsal for acquisition.
    ``evidence_persistence`` states the storage truth: in-memory synthetic
    receipts only, never durable immutable persistence.
    """

    authority_reference: str
    scope_digest: str
    runtime_commit_sha: str
    planned_operations: int
    dispatched_operations: int
    bytes_received: int
    receipts: Tuple[PageReceipt, ...]
    verdict: RehearsalVerdict
    verdict_reason: str
    synthetic_dispatch_attempts: int
    actual_network_requests_issued: int
    evidence_persistence: str


def _scope_digest(plan: Sequence[LaneAPlannedRequest]) -> str:
    canonical = CanonicalConfigSerializer.to_canonical_json(
        [
            {
                "symbols": list(request.symbols),
                "adjustment": request.adjustment,
                "timeframe": request.timeframe,
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
                "provider": request.provider,
                "endpoint_path": request.endpoint_path,
                "feed": request.feed,
                "sort": request.sort,
                "limit": request.limit,
                "currency": request.currency,
            }
            for request in plan
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_runtime_sha(runtime_sha: str) -> str:
    clean = str(runtime_sha or "").strip().lower()
    if len(clean) != 40 or any(c not in "0123456789abcdef" for c in clean):
        raise DataContractError(
            "Rehearsal runtime_commit_sha must be a 40-hex commit SHA."
        )
    return clean


def _expected_session_dates(
    start_date: date, end_date: date, calendar: NyseCa1Calendar
) -> List[date]:
    """Every trading session in the inclusive window (fail-closed range)."""
    if start_date > end_date:
        raise DataContractError(
            f"Rehearsal window inverted: {start_date} > {end_date}."
        )
    sessions: List[date] = []
    cursor = start_date
    while cursor <= end_date:
        if calendar.is_trading_session(cursor):
            sessions.append(cursor)
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return sessions


def _parse_bars_page(
    content: bytes, symbols: Sequence[str], context: str
) -> Tuple[Dict[str, List[Dict[str, Any]]], Optional[str]]:
    """Parse one bars page; fail-closed on malformed provider payloads."""
    try:
        doc = json.loads(content.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise DataContractError(f"REHEARSAL_MALFORMED_PAGE: {context}: {exc}.") from exc
    if not isinstance(doc, dict):
        raise DataContractError(f"REHEARSAL_MALFORMED_PAGE: {context} is not an object.")
    bars = doc.get("bars")
    if not isinstance(bars, dict):
        raise DataContractError(
            f"REHEARSAL_MALFORMED_PAGE: {context} has no 'bars' mapping."
        )
    # Unexpected symbols are rejected/quarantined, never silently discarded:
    # side data outside the authorized universe must surface, not vanish.
    for key in bars:
        if key not in symbols:
            raise DataContractError(
                f"REHEARSAL_UNEXPECTED_SYMBOL: {context} contains out-of-scope "
                f"symbol {key!r}; expected only {sorted(symbols)}."
            )
    parsed: Dict[str, List[Dict[str, Any]]] = {}
    for symbol in symbols:
        entries = bars.get(symbol, [])
        if not isinstance(entries, list):
            raise DataContractError(
                f"REHEARSAL_MALFORMED_PAGE: {context} symbol {symbol} bars are not a list."
            )
        for entry in entries:
            if not isinstance(entry, dict):
                raise DataContractError(
                    f"REHEARSAL_MALFORMED_PAGE: {context} symbol {symbol} has a non-object bar."
                )
            # Structural bar shape only (t/o/h/l/c/v keys present); numeric
            # qualification belongs to a later admission stage, not transport.
            for key in ("t", "o", "h", "l", "c", "v"):
                if key not in entry:
                    raise DataContractError(
                        f"REHEARSAL_MALFORMED_PAGE: {context} symbol {symbol} "
                        f"bar is missing {key!r}."
                    )
        parsed[symbol] = entries
    token = doc.get("next_page_token")
    if token is not None and not isinstance(token, str):
        raise DataContractError(
            f"REHEARSAL_MALFORMED_PAGE: {context} next_page_token is not a string."
        )
    return parsed, (token or None)


def _bar_date(entry: Mapping[str, Any], context: str) -> date:
    """Attribute a bar timestamp to its New York trading date.

    Daily bars are New-York-date stamped (Alpaca convention): the instant is
    normalized to America/New_York BEFORE taking the calendar date, across
    EST/EDT via ZoneInfo. A bare UTC calendar date is NOT the trading date
    (e.g. 00:30 UTC is still the prior New York day). Naive timestamps are
    rejected, never assumed UTC.
    """
    raw = entry.get("t")
    try:
        moment = datetime.fromisoformat(str(raw))
    except (ValueError, TypeError) as exc:
        raise DataContractError(
            f"REHEARSAL_MALFORMED_BAR_TIME: {context}: {raw!r}."
        ) from exc
    if moment.tzinfo is None:
        raise DataContractError(
            f"REHEARSAL_NAIVE_BAR_TIME: {context}: {raw!r}."
        )
    return moment.astimezone(_NY_TZ).date()


def run_rehearsal(
    *,
    authority: Optional[LaneAAuthority],
    transport: ScriptedTransport,
    runtime_sha: str,
    now_utc: datetime,
    ledger: Optional[LaneARequestLedger] = None,
) -> Tuple[RehearsalManifest, RehearsalVerdict]:
    """Execute a bounded offline acquisition rehearsal (sealed transport only).

    Only ``ScriptedTransport`` is accepted: the offline seal is structural,
    not a matter of caller discipline — any other object (including a live
    HTTP adapter implementing a similar surface) fails closed with zero
    dispatches. Authority/scope/plan problems raise (fail-closed, M1.7
    conventions). Execution outcomes return (manifest, verdict); the manifest
    is fully deterministic (no timestamps, no wall-clock).
    """
    # Exact-type seal (not isinstance): @final is a static-typing-only
    # restriction in Python, so a subclass overriding .get() would still
    # satisfy isinstance. The offline guarantee therefore checks the exact
    # runtime type. Threat-model note: this stops accidental or in-process
    # misuse within trusted code; it is NOT an operating-system network
    # sandbox, and no such sandbox is claimed here.
    if type(transport) is not ScriptedTransport:
        raise DataContractError(
            "Rehearsal transport must be exactly a ScriptedTransport (sealed "
            "offline script); subclasses and arbitrary transports are "
            "rejected with zero dispatches."
        )
    clean_sha = _require_runtime_sha(runtime_sha)
    valid = validate_authority(authority, now_utc)
    if ledger is not None and (
        ledger.max_http_operations > valid.max_http_operations
        or ledger.max_total_payload_bytes > valid.max_total_payload_bytes
    ):
        raise DataContractError(
            "Rehearsal ledger budgets exceed the authority budgets; "
            "a looser ledger must never widen an authority."
        )
    plan = plan_lane_a_requests(valid)
    calendar = NyseCa1Calendar()
    expected_sessions = _expected_session_dates(
        valid.scope.start_date, valid.scope.end_date, calendar
    )
    active_ledger = (
        ledger
        if ledger is not None
        else LaneARequestLedger(
            max_http_operations=valid.max_http_operations,
            max_total_payload_bytes=valid.max_total_payload_bytes,
        )
    )
    scope_id = (
        f"{valid.scope.provider}/{valid.scope.feed}/"
        f"{valid.scope.start_date.isoformat()}..{valid.scope.end_date.isoformat()}"
    )
    receipts: List[PageReceipt] = []
    # Coverage is tracked per (adjustment, symbol): every adjustment variant
    # needs its own complete session grid (raw and all-adjusted snapshots can
    # diverge, which is exactly what Lane A compares).
    seen_dates: Dict[Tuple[str, str], List[date]] = {
        (request.adjustment, symbol): []
        for request in plan
        for symbol in valid.scope.symbols
    }

    for request in plan:
        validate_planned_request(valid, request)
        base_params = list(canonical_query_parameters(request))
        page_token: Optional[str] = None
        seen_tokens: List[Optional[str]] = []
        page_index = 0
        while True:
            params = list(base_params)
            if page_token is not None:
                params.append(("page_token", page_token))
            if active_ledger.remaining_operations() <= 0:
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.PARTIAL,
                    "Operation budget exhausted with pages remaining; "
                    "no auto-retry or extension.",
                )
            reservation = active_ledger.begin_dispatch(scope_id, request.adjustment)
            try:
                response = transport.get(request.endpoint_path, params)
            except RehearsalTransportError as exc:
                # Reservation freshness is guaranteed by construction
                # (begin_dispatch immediately above, single settle below), so
                # any ledger raise here can only be budget termination.
                try:
                    active_ledger.fail_dispatch(reservation, 0)
                except DataContractError:
                    return _manifest(
                        valid, plan, active_ledger, clean_sha, receipts,
                        RehearsalVerdict.PARTIAL,
                        "Byte budget exhausted; ledger terminated.",
                    )
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.BLOCKED,
                    "Transport failure with uncertain consumption: "
                    f"{redact_secrets(str(exc))}. "
                    "No resume without a fresh authority and ledger.",
                )
            if response.status_code in (401, 403):
                try:
                    active_ledger.fail_dispatch(reservation, len(response.content))
                except DataContractError:
                    return _manifest(
                        valid, plan, active_ledger, clean_sha, receipts,
                        RehearsalVerdict.PARTIAL,
                        "Byte budget exhausted; ledger terminated.",
                    )
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.BLOCKED,
                    f"Entitlement denial (HTTP {response.status_code}); "
                    "entitlement is never inferred.",
                )
            if response.status_code == 429:
                try:
                    active_ledger.fail_dispatch(reservation, len(response.content))
                except DataContractError:
                    return _manifest(
                        valid, plan, active_ledger, clean_sha, receipts,
                        RehearsalVerdict.PARTIAL,
                        "Byte budget exhausted; ledger terminated.",
                    )
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.BLOCKED,
                    "Rate limited (HTTP 429); stop with no retry in this packet.",
                )
            if 500 <= response.status_code < 600:
                try:
                    active_ledger.fail_dispatch(reservation, len(response.content))
                except DataContractError:
                    return _manifest(
                        valid, plan, active_ledger, clean_sha, receipts,
                        RehearsalVerdict.PARTIAL,
                        "Byte budget exhausted; ledger terminated.",
                    )
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.BLOCKED,
                    f"Server error (HTTP {response.status_code}) with uncertain "
                    "consumption; no resume without a fresh authority and ledger.",
                )
            if response.status_code != 200:
                try:
                    active_ledger.fail_dispatch(reservation, len(response.content))
                except DataContractError:
                    return _manifest(
                        valid, plan, active_ledger, clean_sha, receipts,
                        RehearsalVerdict.PARTIAL,
                        "Byte budget exhausted; ledger terminated.",
                    )
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.REJECTED,
                    f"Unexpected HTTP {response.status_code}; contract violation.",
                )
            try:
                active_ledger.complete_dispatch(reservation, len(response.content))
            except DataContractError:
                receipts.append(
                    PageReceipt(
                        adjustment=request.adjustment,
                        page_index=page_index,
                        byte_count=len(response.content),
                        content_sha256=hashlib.sha256(response.content).hexdigest(),
                        outcome="BYTE_OVERRUN",
                        next_token_seen=None,
                    )
                )
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.PARTIAL,
                    "Byte budget exhausted by the received page; ledger terminated. "
                    "The overrun page is preserved as evidence, not absorbed.",
                )
            receipts.append(
                PageReceipt(
                    adjustment=request.adjustment,
                    page_index=page_index,
                    byte_count=len(response.content),
                    content_sha256=hashlib.sha256(response.content).hexdigest(),
                    outcome="OK",
                    next_token_seen=None,
                )
            )
            try:
                parsed, next_token = _parse_bars_page(
                    response.content,
                    list(valid.scope.symbols),
                    f"{request.adjustment}/page{page_index}",
                )
                page_dates: List[Tuple[str, date]] = []
                for symbol, entries in parsed.items():
                    for entry in entries:
                        bar_date = _bar_date(entry, f"{symbol}/{request.adjustment}")
                        if not calendar.is_trading_session(bar_date):
                            raise DataContractError(
                                f"Off-calendar bar {bar_date.isoformat()} for {symbol}; "
                                "weekend/holiday bars are omissions, never observations."
                            )
                        if not (
                            valid.scope.start_date <= bar_date <= valid.scope.end_date
                        ):
                            raise DataContractError(
                                f"Off-scope bar {bar_date.isoformat()} for {symbol}; "
                                "observations outside the authorized "
                                f"{valid.scope.start_date.isoformat()}.."
                                f"{valid.scope.end_date.isoformat()} window are "
                                "rejected even when complete and ordered."
                            )
                        page_dates.append((symbol, bar_date))
            except DataContractError as exc:
                receipts[-1] = PageReceipt(
                    adjustment=receipts[-1].adjustment,
                    page_index=receipts[-1].page_index,
                    byte_count=receipts[-1].byte_count,
                    content_sha256=receipts[-1].content_sha256,
                    outcome="REJECTED_PAGE",
                    next_token_seen=None,
                )
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.REJECTED,
                    f"Provider payload contract violation: {exc}.",
                )
            receipts[-1] = PageReceipt(
                adjustment=receipts[-1].adjustment,
                page_index=receipts[-1].page_index,
                byte_count=receipts[-1].byte_count,
                content_sha256=receipts[-1].content_sha256,
                outcome=receipts[-1].outcome,
                next_token_seen=next_token,
            )
            for symbol, bar_date in page_dates:
                seen_dates[(request.adjustment, symbol)].append(bar_date)
            if next_token is not None:
                if next_token in seen_tokens:
                    return _manifest(
                        valid, plan, active_ledger, clean_sha, receipts,
                        RehearsalVerdict.REJECTED,
                        f"Duplicate page cursor {next_token!r}; pagination loop rejected.",
                    )
                seen_tokens.append(next_token)
                page_token = next_token
                page_index += 1
                continue
            break

    for request in plan:
        for symbol in sorted(valid.scope.symbols):
            observed = seen_dates[(request.adjustment, symbol)]
            if list(observed) != sorted(observed):
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.REJECTED,
                    f"Non-monotonic bar sequence for {symbol} "
                    f"({request.adjustment}).",
                )
            if len(set(observed)) != len(observed):
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.REJECTED,
                    f"Duplicate bar dates for {symbol} ({request.adjustment}).",
                )
            missing = [day for day in expected_sessions if day not in set(observed)]
            if missing:
                return _manifest(
                    valid, plan, active_ledger, clean_sha, receipts,
                    RehearsalVerdict.PARTIAL,
                    f"Incomplete coverage for {symbol} ({request.adjustment}), "
                    "missing: "
                    + ",".join(day.isoformat() for day in missing)
                    + ". Absence is DATA_UNAVAILABLE, never imputed; "
                    "qualification is BLOCKED on complete coverage.",
                )
    return _manifest(
        valid, plan, active_ledger, clean_sha, receipts,
        RehearsalVerdict.PASS,
        "Bounded, complete, structurally valid acquisition rehearsal.",
    )


def _manifest(
    valid: LaneAAuthority,
    plan: Sequence[LaneAPlannedRequest],
    active_ledger: LaneARequestLedger,
    clean_sha: str,
    receipts: List[PageReceipt],
    verdict: RehearsalVerdict,
    verdict_reason: str,
) -> Tuple[RehearsalManifest, RehearsalVerdict]:
    authority_reference = getattr(valid, "approval_reference", "")
    manifest = RehearsalManifest(
        authority_reference=str(authority_reference),
        scope_digest=_scope_digest(plan),
        runtime_commit_sha=clean_sha,
        planned_operations=len(plan),
        dispatched_operations=active_ledger.dispatched_attempts,
        bytes_received=active_ledger.bytes_received,
        receipts=tuple(receipts),
        verdict=verdict,
        verdict_reason=verdict_reason,
        synthetic_dispatch_attempts=active_ledger.dispatched_attempts,
        actual_network_requests_issued=0,
        evidence_persistence="IN_MEMORY_SYNTHETIC_ONLY",
    )
    return manifest, verdict
