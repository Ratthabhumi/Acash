"""Lane A data-acquisition authority, dispatch-reserve request ledger, and zero-network dry run.

Lane A is a bounded feasibility canary for daily ETF bars (VOO/BND/GLD/BIL,
1Day, 2026-09-28..2026-10-02, adjustments raw+all). This module is PURELY OFFLINE:
it validates an operator-issued authority, binds an exact multi-symbol request
plan, enforces pre-dispatch reservations against cumulative request-count and
payload-byte budgets, and redacts secrets from any error text. It never opens a
socket, never retries, never falls back to another feed, and never expands
scope. Network execution (if ever separately authorized) must pass through a
transport that reserves budget via LaneARequestLedger.begin_dispatch BEFORE
each page fetch.

Fail-closed contract: a missing, unissued, expired, or revoked authority, a
scope violation, or a budget overrun raises DataContractError. There are no
silent floors, clamps, or fabricated neutral outcomes.

Verification boundary: structural validation != human-approval verification.
This module only checks internal consistency of authority fields (see
validate_authority and describe_approval_provenance); it cannot and does not
confirm that a human operator actually issued the referenced approval. That
binding is out-of-band evidence, not code. A dry_run_validate() PASS is not,
on its own, proof of approval. Unit-test ISSUED fixtures are synthetic and
carry no authority whatsoever.

Durability boundary: request accounting is in-process memory only and is NOT
durable crash-safe state. A process restart between dispatch and completion
loses the reservation record; a restarted run must obtain a fresh authority
and ledger. See LaneARequestLedger.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from enum import Enum
import re
from typing import Dict, FrozenSet, List, Optional, Tuple

from acash.core.domain.exceptions import DataContractError

LANE_A_PROVIDER: str = "ALPACA"
LANE_A_TIMEFRAME: str = "1Day"
LANE_A_MAX_HTTP_OPERATIONS: int = 12
LANE_A_MAX_TOTAL_PAYLOAD_BYTES: int = 524_288
LANE_A_PAID_BUDGET_USD: int = 0
LANE_A_HISTORICAL_START: date = date(2026, 9, 28)
LANE_A_HISTORICAL_END: date = date(2026, 10, 2)

LANE_A_SYMBOLS: FrozenSet[str] = frozenset({"VOO", "BND", "GLD", "BIL"})

# Canonical request-shape bindings (Alpaca GET /v2/stocks/bars, official docs
# at https://docs.alpaca.markets/us/reference/stockbars, retrieved 2026-10-13):
#   start/end are INCLUSIVE and accept YYYY-MM-DD; results are sorted by symbol
#   first then bar timestamp; pagination continues ONLY by echoing the query
#   with page_token set to the response's next_page_token; limit applies to the
#   TOTAL data points (default 1000, max 10000); feed defaults to sip server-side,
#   so it is bound explicitly here rather than trusted as a default.
LANE_A_ENDPOINT_PATH: str = "/v2/stocks/bars"
# Lane A deliberately narrows the official feed enum (iex/otc/sip/boats) to the
# two regular-hours feeds the canary is scoped for; narrowing is fail-closed.
LANE_A_ALLOWED_FEEDS: FrozenSet[str] = frozenset({"iex", "sip"})
LANE_A_SORT: str = "asc"
LANE_A_PAGE_LIMIT: int = 1000
LANE_A_CURRENCY: str = "USD"

# What this module can attest about an approval: field consistency only.
LANE_A_APPROVAL_VERIFICATION_LEVEL: str = "STRUCTURAL_FIELD_CHECKS_ONLY"


class LaneAAuthorityStatus(str, Enum):
    """Lifecycle of an operator-issued Lane A acquisition authority."""

    UNISSUED = "UNISSUED"
    ISSUED = "ISSUED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class LaneAScope:
    """Exact request scope bound to a Lane A authority.

    Every field is mandatory and validated fail-closed in __post_init__; a
    partially specified scope is never silently defaulted. In particular the
    market-data feed (iex or sip) must be explicitly operator-bound: the Alpaca
    endpoint defaults feed to sip server-side, and this module never relies on
    or falls back to a provider default.
    """

    symbols: FrozenSet[str]
    timeframe: str
    start_date: date
    end_date: date
    adjustments: FrozenSet[str]
    provider: str
    feed: str
    paid_budget_usd: int

    def __post_init__(self) -> None:
        if not self.symbols:
            raise DataContractError("LaneAScope.symbols must be non-empty.")
        unknown = self.symbols - LANE_A_SYMBOLS
        if unknown:
            raise DataContractError(
                f"LaneAScope contains symbols outside the Lane A canary universe: {sorted(unknown)}."
            )
        if self.timeframe != LANE_A_TIMEFRAME:
            raise DataContractError(
                f"LaneAScope.timeframe must be '{LANE_A_TIMEFRAME}', got '{self.timeframe}'."
            )
        if self.start_date > self.end_date:
            raise DataContractError(
                f"LaneAScope start_date {self.start_date} is after end_date {self.end_date}."
            )
        if self.start_date != LANE_A_HISTORICAL_START or self.end_date != LANE_A_HISTORICAL_END:
            raise DataContractError(
                "LaneAScope window must be exactly "
                f"{LANE_A_HISTORICAL_START}..{LANE_A_HISTORICAL_END}, got "
                f"{self.start_date}..{self.end_date}."
            )
        unknown_adj = self.adjustments - {"raw", "all"}
        if not self.adjustments or unknown_adj:
            raise DataContractError(
                f"LaneAScope.adjustments must be a non-empty subset of {{'raw','all'}}, "
                f"got {sorted(self.adjustments)}."
            )
        if self.provider != LANE_A_PROVIDER:
            raise DataContractError(
                f"LaneAScope.provider must be '{LANE_A_PROVIDER}', got '{self.provider}'."
            )
        if self.feed not in LANE_A_ALLOWED_FEEDS:
            raise DataContractError(
                f"LaneAScope.feed must be one of {sorted(LANE_A_ALLOWED_FEEDS)}, got "
                f"{self.feed!r}; feed is explicitly bound and never defaulted "
                f"(no silent feed fallback)."
            )
        if self.paid_budget_usd != LANE_A_PAID_BUDGET_USD:
            raise DataContractError(
                f"LaneAScope.paid_budget_usd must be {LANE_A_PAID_BUDGET_USD}, "
                f"got {self.paid_budget_usd}."
            )


@dataclass
class LaneAAuthority:
    """Operator-issued, time-bounded authority to execute the Lane A canary.

    A valid authority must carry an explicit approval reference AND the
    operator's approval timestamp (approved_at_utc); a request or task
    description alone never constitutes issuance. All timestamps must be
    timezone-aware — naive datetimes are rejected at construction.

    This dataclass is a STRUCTURAL container only: constructing it (and even
    validate_authority() passing) does not verify that a human operator issued
    the referenced decision. See describe_approval_provenance() for the
    explicit provenance statement.
    """

    status: LaneAAuthorityStatus
    scope: LaneAScope
    max_http_operations: int
    max_total_payload_bytes: int
    issued_at_utc: Optional[datetime]
    expires_at_utc: Optional[datetime]
    approval_reference: str
    approved_at_utc: Optional[datetime] = None

    def __post_init__(self) -> None:
        for name, value in (
            ("issued_at_utc", self.issued_at_utc),
            ("expires_at_utc", self.expires_at_utc),
            ("approved_at_utc", self.approved_at_utc),
        ):
            if value is not None and value.tzinfo is None:
                raise DataContractError(
                    f"LaneAAuthority.{name} must be timezone-aware; naive "
                    f"timestamps are rejected (fail-closed)."
                )
        if self.max_http_operations <= 0:
            raise DataContractError(
                f"max_http_operations must be positive, got {self.max_http_operations}."
            )
        if self.max_http_operations > LANE_A_MAX_HTTP_OPERATIONS:
            raise DataContractError(
                f"max_http_operations {self.max_http_operations} exceeds the Lane A cap "
                f"of {LANE_A_MAX_HTTP_OPERATIONS}."
            )
        if self.max_total_payload_bytes <= 0:
            raise DataContractError(
                f"max_total_payload_bytes must be positive, got {self.max_total_payload_bytes}."
            )
        if self.max_total_payload_bytes > LANE_A_MAX_TOTAL_PAYLOAD_BYTES:
            raise DataContractError(
                f"max_total_payload_bytes {self.max_total_payload_bytes} exceeds the Lane A cap "
                f"of {LANE_A_MAX_TOTAL_PAYLOAD_BYTES}."
            )
        if not self.approval_reference.strip():
            raise DataContractError("LaneAAuthority.approval_reference must be non-empty.")
        if self.status is LaneAAuthorityStatus.ISSUED and self.approved_at_utc is None:
            raise DataContractError(
                "LaneAAuthority with status ISSUED requires approved_at_utc; "
                f"operator-approval provenance must be bound ({LANE_A_APPROVAL_VERIFICATION_LEVEL})."
            )


class LaneAAuthorityError(DataContractError):
    """Raised when an authority is missing, unissued, expired, or revoked."""


def validate_authority(
    authority: Optional[LaneAAuthority], now_utc: datetime
) -> LaneAAuthority:
    """Fail-closed STRUCTURAL validation of an authority against the given clock.

    Checks: presence, ISSUED status, timezone-aware timestamps, approval
    provenance bound (approved_at_utc present and not after issued_at_utc),
    and the validity window (issued in the future or already expired).

    Boundary: passing this function proves only that the authority's fields
    are internally consistent and in-window. It does NOT independently verify
    that a human operator issued the referenced approval (see
    describe_approval_provenance).

    Raises:
        LaneAAuthorityError: If authority is None, not ISSUED, missing approval
            provenance, backdated relative to approval, or outside its
            validity window.
        DataContractError: If now_utc is not timezone-aware.
    """
    if now_utc.tzinfo is None:
        raise DataContractError("now_utc must be timezone-aware.")
    now = now_utc.astimezone(timezone.utc)
    if authority is None:
        raise LaneAAuthorityError("No Lane A authority present; acquisition is UNISSUED.")
    if authority.status is not LaneAAuthorityStatus.ISSUED:
        raise LaneAAuthorityError(
            f"Lane A authority status is {authority.status.value}, not ISSUED."
        )
    if authority.issued_at_utc is None or authority.expires_at_utc is None:
        raise LaneAAuthorityError(
            "ISSUED authority missing issued_at_utc or expires_at_utc; cannot bound validity."
        )
    if authority.approved_at_utc is None:
        raise LaneAAuthorityError(
            "ISSUED authority missing approved_at_utc; operator-approval "
            "provenance is unbound."
        )
    issued = authority.issued_at_utc.astimezone(timezone.utc)
    expires = authority.expires_at_utc.astimezone(timezone.utc)
    approved = authority.approved_at_utc.astimezone(timezone.utc)
    if issued > expires:
        raise LaneAAuthorityError(
            f"Authority issued_at_utc {issued.isoformat()} is after expires_at_utc "
            f"{expires.isoformat()}."
        )
    if issued < approved:
        raise LaneAAuthorityError(
            f"Authority validity start {issued.isoformat()} precedes approved_at_utc "
            f"{approved.isoformat()}; backdated approval binding rejected."
        )
    if now < issued:
        raise LaneAAuthorityError(
            f"Authority is not yet valid: now {now.isoformat()} < issued {issued.isoformat()}."
        )
    if now >= expires:
        raise LaneAAuthorityError(
            f"Authority expired at {expires.isoformat()}; now {now.isoformat()}."
        )
    return authority


class LaneAOperationState(str, Enum):
    """Lifecycle of one single-use dispatch reservation."""

    DISPATCHED = "DISPATCHED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class LaneAOperationRecord:
    """Immutable evidence for one dispatched operation (one page fetch)."""

    reservation_id: int
    scope_id: str
    adjustment: str
    state: LaneAOperationState
    bytes_observed: int


@dataclass
class LaneARequestLedger:
    """Dispatch-reserve/complete request accounting for the Lane A canary.

    Accounting contract (offline; this module issues no requests itself):

    * ``begin_dispatch`` CONSUMES one operation from the request-count budget
      BEFORE any future transport may send a request. A dispatched attempt
      stays counted even if the transport later times out, errors, or crashes
      before completing — repeated failed dispatches can never bypass the cap.
    * Each dispatch receives a stable, single-use reservation id;
      ``complete_dispatch``/``fail_dispatch`` settle it exactly once. A second
      settlement of the same reservation raises DataContractError (no
      double-counting, no budget refund-by-replay).
    * Byte evidence is cumulative and tracked SEPARATELY from the operation
      count. Bytes observed on failed attempts count against the byte budget.
      Overrunning either budget TERMINATES the ledger (``terminated``):
      no further dispatch is ever admitted. There is no silent extension and
      unused budget is never reallocated to a new scope.
    * Crash/restart boundary (explicit non-guarantee): state lives only in
      process memory and is NOT persisted. A process restart between dispatch
      and completion loses the reservation record; a restarted run must obtain
      a fresh authority and a fresh ledger. This class must never be
      represented as durable crash-safe accounting.
    """

    max_http_operations: int
    max_total_payload_bytes: int
    dispatched_attempts: int = 0
    bytes_received: int = 0
    terminated: bool = False
    _next_reservation_id: int = field(default=1, init=False)
    _reservations: Dict[int, LaneAOperationRecord] = field(
        default_factory=dict, init=False
    )

    def remaining_operations(self) -> int:
        return self.max_http_operations - self.dispatched_attempts

    def remaining_bytes(self) -> int:
        return self.max_total_payload_bytes - self.bytes_received

    def begin_dispatch(self, scope_id: str, adjustment: str) -> int:
        """Reserve (and consume) one operation BEFORE any request is sent.

        Returns the single-use reservation id that must later be settled by
        exactly one of ``complete_dispatch`` or ``fail_dispatch``.
        """
        if self.terminated:
            raise DataContractError(
                "Lane A ledger is TERMINATED after a budget violation; no "
                "further dispatch is permitted."
            )
        if self.dispatched_attempts + 1 > self.max_http_operations:
            raise DataContractError(
                f"Lane A request-count budget exhausted: {self.dispatched_attempts}/"
                f"{self.max_http_operations} operations already dispatched; cannot "
                f"dispatch {scope_id}/{adjustment}."
            )
        reservation_id = self._next_reservation_id
        self._next_reservation_id += 1
        self.dispatched_attempts += 1
        self._reservations[reservation_id] = LaneAOperationRecord(
            reservation_id=reservation_id,
            scope_id=scope_id,
            adjustment=adjustment,
            state=LaneAOperationState.DISPATCHED,
            bytes_observed=0,
        )
        return reservation_id

    def _open_reservation(self, reservation_id: int) -> LaneAOperationRecord:
        record = self._reservations.get(reservation_id)
        if record is None:
            raise DataContractError(
                f"Unknown Lane A dispatch reservation {reservation_id}; only "
                f"issued single-use reservation ids can be settled."
            )
        if record.state is not LaneAOperationState.DISPATCHED:
            raise DataContractError(
                f"Lane A dispatch reservation {reservation_id} is already "
                f"{record.state.value}; each reservation is single-use and "
                f"settles exactly once (no duplicate accounting)."
            )
        return record

    def _settle(
        self,
        reservation_id: int,
        record: LaneAOperationRecord,
        payload_bytes: int,
        state: LaneAOperationState,
    ) -> None:
        if payload_bytes < 0:
            raise DataContractError(
                f"payload_bytes must be non-negative, got {payload_bytes}."
            )
        if self.bytes_received + payload_bytes > self.max_total_payload_bytes:
            # The bytes were observed on the wire, so they are recorded as
            # FAILED evidence, the overrun terminates the ledger, and the
            # violation is raised — never clamped or silently absorbed.
            self._reservations[reservation_id] = replace(
                record, state=LaneAOperationState.FAILED, bytes_observed=payload_bytes
            )
            self.terminated = True
            raise DataContractError(
                f"Lane A byte budget would be exceeded: {self.bytes_received} + "
                f"{payload_bytes} > {self.max_total_payload_bytes}; ledger terminated."
            )
        self.bytes_received += payload_bytes
        self._reservations[reservation_id] = replace(
            record, state=state, bytes_observed=payload_bytes
        )

    def complete_dispatch(self, reservation_id: int, payload_bytes: int) -> None:
        """Settle one dispatched operation with its received payload size."""
        record = self._open_reservation(reservation_id)
        self._settle(reservation_id, record, payload_bytes, LaneAOperationState.COMPLETED)

    def fail_dispatch(self, reservation_id: int, observed_bytes: int = 0) -> None:
        """Settle one dispatched operation that timed out / errored / was partial.

        The attempt already consumed request budget at ``begin_dispatch``;
        ``observed_bytes`` records any partial payload actually received.
        """
        record = self._open_reservation(reservation_id)
        self._settle(reservation_id, record, observed_bytes, LaneAOperationState.FAILED)

    @property
    def request_log(self) -> Tuple[LaneAOperationRecord, ...]:
        return tuple(self._reservations[rid] for rid in sorted(self._reservations))


@dataclass(frozen=True)
class LaneAPlannedRequest:
    """One canonical multi-symbol bars request (one adjustment variant).

    The plan issues ONE request per adjustment covering ALL scope symbols
    (2 base requests total), matching Alpaca's documented multi-symbol
    GET /v2/stocks/bars contract (results sorted by symbol first, then bar
    timestamp). Every acquisition-relevant parameter is bound here — provider,
    endpoint, symbols, timeframe, exact inclusive window, adjustment, feed,
    sort, limit, currency, and the page-token policy — so no transport can
    silently substitute a provider default. page_token is deliberately absent
    from construction: continuation pages are bound to echo the first-page
    query with the response's next_page_token verbatim (see
    canonical_query_parameters).
    """

    symbols: Tuple[str, ...]
    adjustment: str
    timeframe: str
    start_date: date
    end_date: date
    provider: str
    endpoint_path: str
    feed: str
    sort: str
    limit: int
    currency: str


def plan_lane_a_requests(authority: LaneAAuthority) -> Tuple[LaneAPlannedRequest, ...]:
    """Expand an ISSUED authority's scope into the exact allowlisted request list.

    Deterministic ordering (sorted symbols, one entry per sorted adjustment)
    so that replays and permutations produce identical plans. Multi-symbol
    shape: one request per adjustment (2 base operations), leaving the
    remaining operation budget for pagination fetches. The plan never exceeds
    the authority's own operation budget; if it would, it fails closed.
    """
    scope = authority.scope
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
    if len(planned) > authority.max_http_operations:
        raise DataContractError(
            f"Lane A plan requires {len(planned)} operations but the authority caps "
            f"{authority.max_http_operations}; refusing to expand scope."
        )
    return tuple(planned)


def canonical_query_parameters(
    request: LaneAPlannedRequest
) -> Tuple[Tuple[str, str], ...]:
    """Exact first-page query binding for one planned request (contains no secrets).

    Official semantics (https://docs.alpaca.markets/us/reference/stockbars,
    retrieved 2026-10-13): ``start``/``end`` are INCLUSIVE and accept
    YYYY-MM-DD; results are sorted by symbol first, then bar timestamp;
    ``limit`` applies to total data points (default 1000, max 10000);
    ``feed``/``sort``/``currency`` have server-side defaults that this binding
    overrides explicitly (no trusted defaults).

    Pagination policy: continuation requests MUST echo these exact parameters
    with ``page_token`` set verbatim to the response's ``next_page_token``;
    an absent/empty ``next_page_token`` ends the fetch. Cursorless re-querying
    (re-sending the first-page query) is forbidden — each continuation is a
    separately budgeted dispatch.
    """
    return (
        ("symbols", ",".join(request.symbols)),
        ("timeframe", request.timeframe),
        ("start", request.start_date.isoformat()),
        ("end", request.end_date.isoformat()),
        ("adjustment", request.adjustment),
        ("feed", request.feed),
        ("sort", request.sort),
        ("limit", str(request.limit)),
        ("currency", request.currency),
    )


def validate_planned_request(
    authority: LaneAAuthority, request: LaneAPlannedRequest
) -> None:
    """Exact scope binding: reject any request outside the authority's scope.

    Checks BOTH the original (symbol, adjustment, timeframe, window, provider)
    scope AND the canonical request shape (endpoint, feed, sort, limit,
    currency, canonical symbol ordering).
    """
    scope = authority.scope
    canonical_symbols = tuple(sorted(scope.symbols))
    if request.symbols != canonical_symbols:
        raise DataContractError(
            f"Multi-symbol request must equal exactly the authority scope symbols "
            f"in canonical sorted order; got {list(request.symbols)}, scope "
            f"{list(canonical_symbols)}."
        )
    if request.adjustment not in scope.adjustments:
        raise DataContractError(
            f"Request adjustment {request.adjustment} is not in the authority scope."
        )
    if request.timeframe != scope.timeframe:
        raise DataContractError(
            f"Request timeframe {request.timeframe} differs from authority scope."
        )
    if request.start_date != scope.start_date or request.end_date != scope.end_date:
        raise DataContractError(
            f"Request window {request.start_date}..{request.end_date} differs from "
            f"authority scope {scope.start_date}..{scope.end_date}."
        )
    if request.provider != scope.provider:
        raise DataContractError(
            f"Request provider {request.provider} differs from authority scope."
        )
    if request.endpoint_path != LANE_A_ENDPOINT_PATH:
        raise DataContractError(
            f"Request endpoint {request.endpoint_path} is not the allowlisted "
            f"Lane A endpoint {LANE_A_ENDPOINT_PATH}."
        )
    if request.feed != scope.feed:
        raise DataContractError(
            f"Request feed {request.feed} differs from authority-bound feed "
            f"{scope.feed}; no silent feed fallback is permitted."
        )
    if request.sort != LANE_A_SORT:
        raise DataContractError(
            f"Request sort {request.sort} differs from canonical sort {LANE_A_SORT}."
        )
    if request.limit != LANE_A_PAGE_LIMIT:
        raise DataContractError(
            f"Request limit {request.limit} differs from canonical page limit "
            f"{LANE_A_PAGE_LIMIT}."
        )
    if request.currency != LANE_A_CURRENCY:
        raise DataContractError(
            f"Request currency {request.currency} differs from canonical currency "
            f"{LANE_A_CURRENCY}."
        )


@dataclass(frozen=True)
class LaneADryRunResult:
    """Outcome of a zero-network dry run over an authority and its planned requests."""

    planned_requests: Tuple[LaneAPlannedRequest, ...]
    planned_operations: int
    max_http_operations: int
    max_total_payload_bytes: int
    network_requests_issued: int
    approval_provenance: "LaneAApprovalProvenance"


def dry_run_validate(
    authority: Optional[LaneAAuthority], now_utc: datetime
) -> LaneADryRunResult:
    """Validate an authority and its full request plan WITHOUT any network I/O.

    Asserts NETWORK_REQUESTS = 0 by construction: this function touches no
    transport, no credentials, and no sockets. It exists so that operators can
    verify scope binding, budget feasibility, and authority validity before any
    separately authorized network execution.

    PASS boundary: a passing dry run is STRUCTURAL evidence only (fields
    internally consistent, plan fits budget). It is never, on its own,
    evidence that a human operator approved the acquisition — see
    approval_provenance on the result.
    """
    valid = validate_authority(authority, now_utc)
    plan = plan_lane_a_requests(valid)
    return LaneADryRunResult(
        planned_requests=plan,
        planned_operations=len(plan),
        max_http_operations=valid.max_http_operations,
        max_total_payload_bytes=valid.max_total_payload_bytes,
        network_requests_issued=0,
        approval_provenance=describe_approval_provenance(valid),
    )


@dataclass(frozen=True)
class LaneAApprovalProvenance:
    """Explicit statement of what validating an authority does and does not prove.

    Structural validation (this module) != external human-approval
    verification. ``externally_verified`` is always False for anything this
    module produces: it cannot confirm that a human operator issued the
    referenced decision. A dry-run PASS combined with this descriptor is never
    approval evidence on its own; verification requires an out-of-band check
    of the operator's decision record. Unit-test ISSUED fixtures are synthetic
    and carry no authority whatsoever.
    """

    approval_reference: str
    approved_at_utc: Optional[datetime]
    verification_level: str
    externally_verified: bool
    note: str


def describe_approval_provenance(
    authority: Optional[LaneAAuthority],
) -> LaneAApprovalProvenance:
    """Return the provenance descriptor for an authority (or absence of one).

    Minimum verifiable operator-decision binding: a non-empty
    ``approval_reference`` plus a timezone-aware ``approved_at_utc`` recorded
    OUTSIDE this system (in the operator's own decision record). This module
    checks those fields exist and are consistent; only an out-of-band check of
    that record can verify the decision actually happened.
    """
    if authority is None:
        return LaneAApprovalProvenance(
            approval_reference="",
            approved_at_utc=None,
            verification_level=LANE_A_APPROVAL_VERIFICATION_LEVEL,
            externally_verified=False,
            note="No authority present; acquisition is UNISSUED.",
        )
    return LaneAApprovalProvenance(
        approval_reference=authority.approval_reference,
        approved_at_utc=authority.approved_at_utc,
        verification_level=LANE_A_APPROVAL_VERIFICATION_LEVEL,
        externally_verified=False,
        note=(
            "Fields checked structurally only; this module does not verify an "
            "external operator decision record. Verifying the approval requires "
            "an out-of-band check of approval_reference + approved_at_utc, not code."
        ),
    )


_SECRET_HEADER_PATTERN = re.compile(
    r"(?i)(apca-api-(?:secret|key)-id|apca-api-secret-key|authorization|api[-_]?key)"
    r'("?\s*[:=]\s*"?)'
    r"(?:"
    r'"([^"]+)"'
    r"|'([^']+)'"
    r"|([^\s,;&\"'}\]]+)"
    r")"
)
_BEARER_PATTERN = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9\-._~+/=]{8,})")


def _redact_secret_match(match: "re.Match[str]") -> str:
    """Rebuild a matched secret occurrence as key+separator+[REDACTED](+quote)."""
    if match.group(3) is not None:
        suffix = '"'
    elif match.group(4) is not None:
        suffix = "'"
    else:
        suffix = ""
    return f"{match.group(1)}{match.group(2)}[REDACTED]{suffix}"


def redact_secrets(text: str) -> str:
    """Scrub credential-looking values from any text destined for logs/evidence.

    Purely deterministic string transformation; never raises. Handles bare
    header form (``apca-api-key-id: value``), JSON-quoted form
    (``"apca-api-secret-key": "value"``), and quoted values. Redaction is
    applied to error messages and evidence metadata, never to raw payloads
    (which are hashed, not logged, per the manifest contract).
    """
    redacted = _BEARER_PATTERN.sub(lambda m: f"{m.group(1)}[REDACTED]", text)
    redacted = _SECRET_HEADER_PATTERN.sub(_redact_secret_match, redacted)
    return redacted


def build_lane_a_scope(feed: str) -> LaneAScope:
    """Canonical Lane A scope: exact canary universe, window, adjustments, and an
    explicitly operator-bound feed (iex or sip).

    Feed is a REQUIRED argument — this constructor never silently defaults it
    to a provider default (the Alpaca endpoint defaults to sip server-side,
    which may require paid entitlement).
    """
    return LaneAScope(
        symbols=LANE_A_SYMBOLS,
        timeframe=LANE_A_TIMEFRAME,
        start_date=LANE_A_HISTORICAL_START,
        end_date=LANE_A_HISTORICAL_END,
        adjustments=frozenset({"raw", "all"}),
        provider=LANE_A_PROVIDER,
        feed=feed,
        paid_budget_usd=LANE_A_PAID_BUDGET_USD,
    )






