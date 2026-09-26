"""HYP_011 prospective shadow machinery: activation, guards, append-only state.

No market-data access in this module. All session derivations use the
canonical NYSE calendar only. Missed sessions (scientific boundary up to
operational activation, exclusive) are never backfilled and never counted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar

SCIENTIFIC_PROSPECTIVE_BOUNDARY: date = date(2026, 9, 25)
RECENT_STRESS_START: date = date(2025, 1, 1)
RECENT_STRESS_END: date = date(2026, 8, 14)
QUARANTINE_START: date = date(2026, 8, 15)
PROSPECTIVE_MIN_SESSIONS: int = 504
PROSPECTIVE_MIN_REBALANCES: int = 2
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
