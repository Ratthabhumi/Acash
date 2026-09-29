"""HYP_011 prospective shadow machinery: activation, guards, append-only state.

No market-data access in this module. All session derivations use the
canonical NYSE calendar only. Missed sessions (scientific boundary up to
operational activation, exclusive) are never backfilled and never counted.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar

SCIENTIFIC_PROSPECTIVE_BOUNDARY: date = date(2026, 9, 25)
RECENT_STRESS_START: date = date(2025, 1, 1)
RECENT_STRESS_END: date = date(2026, 8, 14)
QUARANTINE_START: date = date(2026, 8, 15)
PROSPECTIVE_MIN_SESSIONS: int = 504
PROSPECTIVE_MIN_REBALANCES: int = 2
STATE_SCHEMA_VERSION: int = 1
STATE_HYPOTHESIS_ID: str = "HYP_011"
STAGE_B_ACTIVATION_SESSION: date = date(2026, 9, 28)
STATE_ACTIVATION_SESSION: date = STAGE_B_ACTIVATION_SESSION

# Stage-C Recovery Governance constants
FAILED_ACTIVATION_SESSION: date = date(2026, 9, 28)
FAILED_DISPATCH_ATTEMPT: int = 1
FAILED_DISPATCH_AT_UTC: datetime = datetime(2026, 9, 28, 20, 10, 0, tzinfo=timezone.utc)
NEXT_DISPATCH_ATTEMPT: int = 2
STAGE_C_RECOVERY_BINDING_ID: str = "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C"
STAGE_C_RECOVERY_BINDING_PATH: Path = Path(
    "docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json"
)
STAGE_C_A_SPEC_PATH: Path = Path(
    "docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_A.json"
)

# Timing semantics (never hard-code UTC market times: DST changes the offset).
# session.open_utc  = portfolio execution timestamp semantics (calendar-derived).
# session.close_utc = market session completion instant (calendar-derived).
# Provider data accessibility boundary:
# Alpaca historical SIP requires at least 15-minute delay for accounts without
# real-time SIP subscription. Querying earlier or querying into the future returns HTTP 403.
ALPACA_SIP_DELAY: timedelta = timedelta(minutes=15)
PROVIDER_SAFETY_MARGIN: timedelta = timedelta(minutes=0)
DEFAULT_PROVIDER_SAFETY_MARGIN: timedelta = PROVIDER_SAFETY_MARGIN
CANDIDATE_OPERATIONAL_MARGIN: timedelta = timedelta(minutes=5)


@dataclass(frozen=True)
class StageCRecoveryAuthority:
    """Authoritative Stage C-B recovery binding metadata loaded from disk."""

    binding_id: str
    binding_commit_sha: str
    binding_commit_utc: str
    activation_session: date
    manifest_sha256: str
    manifest_path: str


def load_stage_c_recovery_authority(
    calendar: NyseCa1Calendar,
    stage_c_binding_path: Optional[Path] = None,
) -> StageCRecoveryAuthority:
    """Validate Stage C-B recovery binding manifest and return authoritative metadata.

    Computes deterministic SHA-256 digest over the raw canonical file bytes on disk.
    Enforces all 11 required fields, valid 40-character hex commit SHA,
    timezone-aware commit timestamp, matching NYSE-derived activation session,
    failed session invariants, and advance beyond 2026-09-28.
    """
    path = stage_c_binding_path or STAGE_C_RECOVERY_BINDING_PATH
    if not path.is_file():
        raise DataContractError(f"SHADOW_RECOVERY_BINDING_NOT_FOUND: {path}.")

    raw_bytes = path.read_bytes()
    manifest_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        raise DataContractError(f"SHADOW_RECOVERY_BINDING_CORRUPT: {exc}.") from exc

    required_fields = (
        "binding_id",
        "binding_commit_sha",
        "binding_commit_utc",
        "activation_session",
        "scientific_prospective_boundary",
        "failed_dispatch_session",
        "failed_dispatch_attempt",
        "next_observation_ordinal",
        "next_dispatch_attempt",
        "backfill_allowed",
        "retry_failed_session_allowed",
    )
    for req_field in required_fields:
        if req_field not in data:
            raise DataContractError(
                f"SHADOW_RECOVERY_BINDING_MISSING_FIELD: {req_field}."
            )

    if data["binding_id"] != STAGE_C_RECOVERY_BINDING_ID:
        raise DataContractError(
            f"SHADOW_RECOVERY_BINDING_ID_MISMATCH: expected {STAGE_C_RECOVERY_BINDING_ID}, "
            f"got {data['binding_id']}."
        )

    commit_sha = str(data["binding_commit_sha"])
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
        raise DataContractError(
            f"SHADOW_RECOVERY_BINDING_INVALID_SHA: {commit_sha}."
        )

    commit_ts_raw = data["binding_commit_utc"]
    try:
        commit_ts = datetime.fromisoformat(str(commit_ts_raw))
    except Exception as exc:
        raise DataContractError(
            f"SHADOW_RECOVERY_BINDING_INVALID_TIMESTAMP: {exc}."
        ) from exc

    if commit_ts.tzinfo is None:
        raise DataContractError("SHADOW_RECOVERY_BINDING_TIMESTAMP_NAIVE.")
    commit_utc = commit_ts.astimezone(timezone.utc)

    derived_act = derive_activation_session(calendar, commit_utc)

    try:
        declared_act = date.fromisoformat(str(data["activation_session"]))
    except Exception as exc:
        raise DataContractError(
            f"SHADOW_RECOVERY_BINDING_INVALID_ACTIVATION: {exc}."
        ) from exc

    if declared_act != derived_act:
        raise DataContractError(
            f"SHADOW_RECOVERY_BINDING_ACTIVATION_MISMATCH: declared {declared_act} "
            f"!= derived {derived_act} from commit {commit_ts_raw}."
        )

    if data["scientific_prospective_boundary"] != SCIENTIFIC_PROSPECTIVE_BOUNDARY.isoformat():
        raise DataContractError("SHADOW_RECOVERY_BINDING_BOUNDARY_MISMATCH.")
    if data["failed_dispatch_session"] != FAILED_ACTIVATION_SESSION.isoformat():
        raise DataContractError("SHADOW_RECOVERY_BINDING_FAILED_SESSION_MISMATCH.")
    if data["failed_dispatch_attempt"] != FAILED_DISPATCH_ATTEMPT:
        raise DataContractError("SHADOW_RECOVERY_BINDING_FAILED_ATTEMPT_MISMATCH.")
    if data["next_observation_ordinal"] != 1:
        raise DataContractError("SHADOW_RECOVERY_BINDING_ORDINAL_MISMATCH.")
    if data["next_dispatch_attempt"] != NEXT_DISPATCH_ATTEMPT:
        raise DataContractError("SHADOW_RECOVERY_BINDING_NEXT_ATTEMPT_MISMATCH.")
    if data["backfill_allowed"] is not False:
        raise DataContractError("SHADOW_RECOVERY_BINDING_BACKFILL_NOT_FORBIDDEN.")
    if data["retry_failed_session_allowed"] is not False:
        raise DataContractError("SHADOW_RECOVERY_BINDING_RETRY_NOT_FORBIDDEN.")

    if derived_act <= FAILED_ACTIVATION_SESSION:
        raise DataContractError(
            f"SHADOW_RECOVERY_ACTIVATION_NOT_ADVANCED: bound {derived_act} <= "
            f"failed {FAILED_ACTIVATION_SESSION}."
        )
    if not calendar.is_trading_session(derived_act):
        raise DataContractError(f"SHADOW_RECOVERY_NON_TRADING_SESSION: {derived_act}.")

    return StageCRecoveryAuthority(
        binding_id=str(data["binding_id"]),
        binding_commit_sha=commit_sha,
        binding_commit_utc=commit_utc.isoformat(),
        activation_session=derived_act,
        manifest_sha256=manifest_sha256,
        manifest_path=str(path),
    )


def resolve_operational_activation(
    calendar: NyseCa1Calendar,
    now_utc: datetime,
    stage_c_binding_path: Optional[Path] = None,
    committed_observations: int = 0,
) -> date:
    """Resolve authoritative operational activation session.

    Activation authority strictly originates from canonical Stage C-B binding
    or historical Stage-B boundary, never from mutable runtime state.
    """
    if now_utc.tzinfo is None:
        raise DataContractError("SHADOW_NOW_MUST_BE_TIMEZONE_AWARE.")
    now = now_utc.astimezone(timezone.utc)

    if stage_c_binding_path is not None and not stage_c_binding_path.is_file():
        raise DataContractError(
            f"SHADOW_RECOVERY_BINDING_NOT_FOUND: {stage_c_binding_path}."
        )

    binding_file = stage_c_binding_path or STAGE_C_RECOVERY_BINDING_PATH
    if binding_file.is_file():
        auth = load_stage_c_recovery_authority(calendar, binding_file)
        return auth.activation_session

    # No Stage C-B binding exists.
    if committed_observations == 0 and now >= FAILED_DISPATCH_AT_UTC:
        raise DataContractError(
            "SHADOW_RECOVERY_BINDING_REQUIRED: Attempt 1 on 2026-09-28 failed/blocked. "
            "Operational re-activation strictly requires a ratified Stage C-B binding."
        )

    return STAGE_B_ACTIVATION_SESSION


def candidate_schedule_time(
    session_date: date,
    calendar: NyseCa1Calendar,
    provider_delay: timedelta = ALPACA_SIP_DELAY,
    operational_margin: timedelta = CANDIDATE_OPERATIONAL_MARGIN,
) -> datetime:
    """Derive candidate operational dispatch timestamp: session.close_utc + provider_delay + margin."""
    session = calendar.get_session(session_date)
    if session.close_utc is None:
        raise DataContractError(f"SHADOW_NO_CLOSE_TIME: {session_date.isoformat()}.")
    return session.close_utc + provider_delay + operational_margin


def market_session_completed_after(
    session_date: date, calendar: NyseCa1Calendar
) -> datetime:
    """Canonical completion instant: the session's calendar-derived close_utc.

    Strict: session is completed strictly when now_utc > close_utc.
    """
    close_utc = calendar.get_session(session_date).close_utc
    if close_utc is None:
        raise DataContractError(
            f"SHADOW_NO_CLOSE_TIME: {session_date.isoformat()}."
        )
    return close_utc


def provider_observation_eligible_after(
    session_date: date,
    calendar: NyseCa1Calendar,
    provider_delay: timedelta = ALPACA_SIP_DELAY,
    safety_margin: timedelta = PROVIDER_SAFETY_MARGIN,
) -> datetime:
    """Canonical instant after which delayed SIP historical data is accessible.

    Separates MARKET SESSION COMPLETE from PROVIDER DATA ACCESSIBLE.
    Under Alpaca delayed historical SIP rules, queries must not include data
    fresher than 15 minutes.
    Strict fail-closed: request is only eligible when now_utc > provider_eligible_after_utc.
    """
    return market_session_completed_after(session_date, calendar) + provider_delay + safety_margin


def observation_eligible_after(
    session_date: date, calendar: NyseCa1Calendar
) -> datetime:
    """Canonical overall observation eligibility instant.

    Observation requires BOTH market session completion and delayed SIP provider
    data accessibility. Production eligibility is STRICT: now_utc > eligible_after.
    At exactly eligible_after the session is NOT YET PROCESSABLE.
    """
    return provider_observation_eligible_after(session_date, calendar)
SHADOW_STARTING_AUM: Decimal = Decimal("100000.00")


@dataclass
class ShadowState:
    """Append-only prospective observation state (sessions observed, never edited)."""

    activation_session: date
    observed_sessions: List[str] = field(default_factory=list)
    completed_annual_rebalances: int = 0

    def record_session(
        self, session: date, calendar: NyseCa1Calendar, now_utc: datetime
    ) -> None:
        """Append exactly the next unprocessed eligible COMPLETED session.

        Completion is determined by the canonical session close_utc, never by
        calendar date alone. now_utc is an explicit parameter (pure function).
        """
        if now_utc.tzinfo is None:
            raise DataContractError("SHADOW_NOW_MUST_BE_TIMEZONE_AWARE.")
        now = now_utc.astimezone(timezone.utc)
        iso = session.isoformat()
        if iso in self.observed_sessions:
            raise DataContractError(f"SHADOW_DUPLICATE_SESSION: {iso}.")
        if self.observed_sessions and iso <= self.observed_sessions[-1]:
            raise DataContractError(f"SHADOW_OUT_OF_ORDER_SESSION: {iso}.")
        if session < self.activation_session:
            raise DataContractError(f"SHADOW_EARLIER_THAN_ACTIVATION: {iso}.")
        if not calendar.is_trading_session(session):
            raise DataContractError(f"SHADOW_NON_SESSION: {iso}.")
        if RECENT_STRESS_START <= session <= RECENT_STRESS_END:
            raise DataContractError(f"SHADOW_RECENT_STRESS_SESSION: {iso}.")
        if QUARANTINE_START <= session < SCIENTIFIC_PROSPECTIVE_BOUNDARY:
            raise DataContractError(f"SHADOW_QUARANTINE_SESSION: {iso}.")
        close_utc = calendar.get_session(session).close_utc
        if close_utc is None:
            raise DataContractError(f"SHADOW_NO_CLOSE_TIME: {iso}.")
        if now <= close_utc:
            raise DataContractError(f"SHADOW_INCOMPLETE_SESSION: {iso}.")
        self.observed_sessions.append(iso)

    @property
    def observed_count(self) -> int:
        return len(self.observed_sessions)

    def minimums_satisfied(self) -> bool:
        return (
            self.observed_count >= PROSPECTIVE_MIN_SESSIONS
            and self.completed_annual_rebalances >= PROSPECTIVE_MIN_REBALANCES
        )


def missed_unobserved_sessions(
    calendar: NyseCa1Calendar, activation_exclusive_upper: date
) -> List[date]:
    """Eligible sessions in [2026-09-25, activation_exclusive_upper).

    These completed without authorized observation: never backfilled, never
    counted toward the 504-session clock or any metric.
    """
    missed: List[date] = []
    cursor = SCIENTIFIC_PROSPECTIVE_BOUNDARY
    while cursor < activation_exclusive_upper:
        if calendar.is_trading_session(cursor):
            missed.append(cursor)
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return missed


def derive_activation_session(
    calendar: NyseCa1Calendar, activation_commit_utc: datetime
) -> date:
    """First canonical session OPEN strictly after the commit timestamp.

    The commit's own calendar date is considered: a commit before today's
    eligible open qualifies today; exactly-at-open or after-open moves on.
    """
    if activation_commit_utc.tzinfo is None:
        raise DataContractError("SHADOW_ACTIVATION_TS_MUST_BE_TIMEZONE_AWARE.")
    commit_utc = activation_commit_utc.astimezone(timezone.utc)
    cursor = commit_utc.date()
    for _ in range(15):
        if calendar.is_trading_session(cursor):
            session = calendar.get_session(cursor)
            open_utc = session.open_utc
            if open_utc is None:
                raise DataContractError(f"SHADOW_NO_OPEN_TIME: {cursor}.")
            if open_utc > commit_utc:
                return cursor
        cursor = date.fromordinal(cursor.toordinal() + 1)
    raise DataContractError("SHADOW_NO_ACTIVATION_SESSION_WITHIN_15_DAYS.")


def shadow_readiness(
    corrected_verdict: str, gates_conjunction: bool
) -> Dict[str, object]:
    """Arm the shadow only on the corrected historical authority."""
    if (
        corrected_verdict != "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW"
        or not gates_conjunction
    ):
        raise DataContractError(
            "SHADOW_REFUSES_ARBITRARY_BASELINE: corrected R3 authority required."
        )
    return {
        "state": "PROSPECTIVE_SHADOW_ARMED_WAITING_FOR_FIRST_COMPLETED_SESSION",
        "starting_aum": str(SHADOW_STARTING_AUM),
        "observed_sessions": 0,
        "completed_rebalances": 0,
    }
