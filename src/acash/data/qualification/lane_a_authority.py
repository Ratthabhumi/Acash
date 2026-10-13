"""Lane A data-acquisition authority, request budget ledger, and zero-network dry run.

Lane A is a bounded feasibility canary for daily ETF bars (VOO/BND/GLD/BIL,
1Day, 2026-09-28..2026-10-02, adjustments raw+all). This module is PURELY OFFLINE:
it validates an operator-issued authority, allowlists planned requests, enforces
cumulative request-count and payload-byte budgets, and redacts secrets from any
error text. It never opens a socket, never retries, never falls back to another
feed, and never expands scope. Network execution (if ever separately authorized)
must pass through a transport that this module's ledger gates request-by-request.

Fail-closed contract: a missing, unissued, expired, or revoked authority, a
scope violation, or a budget overrun raises DataContractError. There are no
silent floors, clamps, or fabricated neutral outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
import re
from typing import FrozenSet, List, Optional, Tuple

from acash.core.domain.exceptions import DataContractError

LANE_A_PROVIDER: str = "ALPACA"
LANE_A_TIMEFRAME: str = "1Day"
LANE_A_MAX_HTTP_OPERATIONS: int = 12
LANE_A_MAX_TOTAL_PAYLOAD_BYTES: int = 524_288
LANE_A_PAID_BUDGET_USD: int = 0
LANE_A_HISTORICAL_START: date = date(2026, 9, 28)
LANE_A_HISTORICAL_END: date = date(2026, 10, 2)

LANE_A_SYMBOLS: FrozenSet[str] = frozenset({"VOO", "BND", "GLD", "BIL"})


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
    partially specified scope is never silently defaulted.
    """

    symbols: FrozenSet[str]
    timeframe: str
    start_date: date
    end_date: date
    adjustments: FrozenSet[str]
    provider: str
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
        if self.paid_budget_usd != LANE_A_PAID_BUDGET_USD:
            raise DataContractError(
                f"LaneAScope.paid_budget_usd must be {LANE_A_PAID_BUDGET_USD}, "
                f"got {self.paid_budget_usd}."
            )


@dataclass(frozen=True)
class LaneAAuthority:
    """Operator-issued, time-bounded authority to execute the Lane A canary.

    A valid authority must carry an explicit approval reference; a request or
    task description alone never constitutes issuance.
    """

    status: LaneAAuthorityStatus
    scope: LaneAScope
    max_http_operations: int
    max_total_payload_bytes: int
    issued_at_utc: Optional[datetime]
    expires_at_utc: Optional[datetime]
    approval_reference: str

    def __post_init__(self) -> None:
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


class LaneAAuthorityError(DataContractError):
    """Raised when an authority is missing, unissued, expired, or revoked."""


def validate_authority(
    authority: Optional[LaneAAuthority], now_utc: datetime
) -> LaneAAuthority:
    """Fail-closed authority validation against the given clock.

    Raises:
        LaneAAuthorityError: If authority is None, not ISSUED, or outside its
            validity window (issued in the future or already expired).
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
    issued = authority.issued_at_utc.astimezone(timezone.utc)
    expires = authority.expires_at_utc.astimezone(timezone.utc)
    if issued > expires:
        raise LaneAAuthorityError(
            f"Authority issued_at_utc {issued.isoformat()} is after expires_at_utc "
            f"{expires.isoformat()}."
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


@dataclass
class LaneARequestLedger:
    """Cumulative request-count and payload-byte budget gate.

    Every HTTP operation (one page fetch = one operation) must be recorded
    before it is issued. Overrunning either budget fails closed; there is no
    silent extension, and unused budget is never reallocated to a new scope.
    """

    max_http_operations: int
    max_total_payload_bytes: int
    requests_issued: int = 0
    bytes_received: int = 0
    _request_log: List[Tuple[str, str, int]] = field(default_factory=list)

    def remaining_operations(self) -> int:
        return self.max_http_operations - self.requests_issued

    def remaining_bytes(self) -> int:
        return self.max_total_payload_bytes - self.bytes_received

    def authorize_operation(self, symbol: str, adjustment: str) -> None:
        """Pre-flight gate: reserve one operation before issuing the request."""
        if self.requests_issued + 1 > self.max_http_operations:
            raise DataContractError(
                f"Lane A request-count budget exhausted: {self.requests_issued}/"
                f"{self.max_http_operations} operations used; cannot authorize "
                f"{symbol}/{adjustment}."
            )

    def record_operation(self, symbol: str, adjustment: str, payload_bytes: int) -> None:
        """Record a completed operation with its payload size; fail closed on overrun."""
        if payload_bytes < 0:
            raise DataContractError(f"payload_bytes must be non-negative, got {payload_bytes}.")
        self.authorize_operation(symbol, adjustment)
        if self.bytes_received + payload_bytes > self.max_total_payload_bytes:
            raise DataContractError(
                f"Lane A byte budget would be exceeded: {self.bytes_received} + "
                f"{payload_bytes} > {self.max_total_payload_bytes}."
            )
        self.requests_issued += 1
        self.bytes_received += payload_bytes
        self._request_log.append((symbol, adjustment, payload_bytes))

    @property
    def request_log(self) -> Tuple[Tuple[str, str, int], ...]:
        return tuple(self._request_log)


@dataclass(frozen=True)
class LaneAPlannedRequest:
    """One allowlisted (symbol, adjustment) request within the Lane A window."""

    symbol: str
    adjustment: str
    timeframe: str
    start_date: date
    end_date: date
    provider: str


def plan_lane_a_requests(authority: LaneAAuthority) -> Tuple[LaneAPlannedRequest, ...]:
    """Expand an ISSUED authority's scope into the exact allowlisted request list.

    Deterministic ordering (sorted symbols, sorted adjustments) so that replays
    and permutations produce identical plans. The plan never exceeds the
    authority's own operation budget; if the cross-product would, it fails closed.
    """
    scope = authority.scope
    planned: List[LaneAPlannedRequest] = []
    for symbol in sorted(scope.symbols):
        for adjustment in sorted(scope.adjustments):
            planned.append(
                LaneAPlannedRequest(
                    symbol=symbol,
                    adjustment=adjustment,
                    timeframe=scope.timeframe,
                    start_date=scope.start_date,
                    end_date=scope.end_date,
                    provider=scope.provider,
                )
            )
    if len(planned) > authority.max_http_operations:
        raise DataContractError(
            f"Lane A plan requires {len(planned)} operations but the authority caps "
            f"{authority.max_http_operations}; refusing to expand scope."
        )
    return tuple(planned)


def validate_planned_request(
    authority: LaneAAuthority, request: LaneAPlannedRequest
) -> None:
    """Exact scope binding: reject any request outside the authority's scope."""
    scope = authority.scope
    if request.symbol not in scope.symbols:
        raise DataContractError(
            f"Request symbol {request.symbol} is not in the authority scope."
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


@dataclass(frozen=True)
class LaneADryRunResult:
    """Outcome of a zero-network dry run over an authority and its planned requests."""

    planned_requests: Tuple[LaneAPlannedRequest, ...]
    planned_operations: int
    max_http_operations: int
    max_total_payload_bytes: int
    network_requests_issued: int


def dry_run_validate(
    authority: Optional[LaneAAuthority], now_utc: datetime
) -> LaneADryRunResult:
    """Validate an authority and its full request plan WITHOUT any network I/O.

    Asserts NETWORK_REQUESTS = 0 by construction: this function touches no
    transport, no credentials, and no sockets. It exists so that operators can
    verify scope binding, budget feasibility, and authority validity before any
    separately authorized network execution.
    """
    valid = validate_authority(authority, now_utc)
    plan = plan_lane_a_requests(valid)
    return LaneADryRunResult(
        planned_requests=plan,
        planned_operations=len(plan),
        max_http_operations=valid.max_http_operations,
        max_total_payload_bytes=valid.max_total_payload_bytes,
        network_requests_issued=0,
    )


_SECRET_HEADER_PATTERN = re.compile(
    r"(?i)(apca-api-(?:secret|key)-id|apca-api-secret-key|authorization|api[-_]?key)"
    r"(\s*[:=]\s*)([^\s\"']+)"
)
_BEARER_PATTERN = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9\-._~+/=]{8,})")


def redact_secrets(text: str) -> str:
    """Scrub credential-looking values from any text destined for logs/evidence.

    Purely deterministic string transformation; never raises. Redaction is
    applied to error messages and evidence metadata, never to raw payloads
    (which are hashed, not logged, per the manifest contract).
    """
    redacted = _BEARER_PATTERN.sub(lambda m: f"{m.group(1)}[REDACTED]", text)
    redacted = _SECRET_HEADER_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", redacted)
    return redacted


def build_lane_a_scope() -> LaneAScope:
    """Canonical Lane A scope: the exact canary universe, window, and adjustments."""
    return LaneAScope(
        symbols=LANE_A_SYMBOLS,
        timeframe=LANE_A_TIMEFRAME,
        start_date=LANE_A_HISTORICAL_START,
        end_date=LANE_A_HISTORICAL_END,
        adjustments=frozenset({"raw", "all"}),
        provider=LANE_A_PROVIDER,
        paid_budget_usd=LANE_A_PAID_BUDGET_USD,
    )
