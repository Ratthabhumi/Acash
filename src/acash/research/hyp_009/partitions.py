"""Frozen HYP_009 date partitions and NYSE session utilities (R1 §4 partitions)."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar

# Frozen R1 sample partitions (inclusive calendar dates).
RESEARCH_START: date = date(2016, 1, 1)
WARMUP_START: date = date(2016, 1, 1)
WARMUP_END: date = date(2016, 10, 31)
M1_START: date = date(2016, 11, 1)
M1_END: date = date(2020, 12, 31)

# Hard R2 market-data scope (inclusive).
AUTHORIZED_MIN_DATE: date = date(2016, 1, 1)
AUTHORIZED_MAX_DATE: date = date(2020, 12, 31)

# Forbidden partitions (any touch raises before network).
M2_START: date = date(2021, 1, 1)
M2_END: date = date(2024, 12, 31)
M3_START: date = date(2025, 1, 1)
M3_END: date = date(2026, 8, 14)
QUARANTINE_START: date = date(2026, 8, 15)


def expected_sessions(
    calendar: NyseCa1Calendar, start: date, end: date
) -> List[date]:
    """All eligible NYSE sessions in [start, end] from canonical calendar.

    Early-close sessions are INCLUDED (HYP_009 daily contract; HYP_007's
    390-minute exclusion does NOT apply). Weekends/holidays excluded.
    """
    if start > end:
        raise DataContractError(f"PARTITION_INVERTED: {start} > {end}.")
    sessions: List[date] = []
    cursor = start
    while cursor <= end:
        if calendar.is_trading_session(cursor):
            sessions.append(cursor)
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return sessions


def month_end_sessions(sessions: List[date]) -> List[date]:
    """Last eligible session of each calendar month, in chronological order."""
    if not sessions:
        raise DataContractError("MONTH_END_EMPTY: no sessions supplied.")
    if sessions != sorted(sessions):
        raise DataContractError("MONTH_END_UNORDERED: sessions must be chronological.")
    if len(set(sessions)) != len(sessions):
        raise DataContractError("MONTH_END_DUPLICATE: duplicate sessions supplied.")
    month_ends: List[date] = []
    by_month: Dict[Tuple[int, int], List[date]] = {}
    for session in sessions:
        by_month.setdefault((session.year, session.month), []).append(session)
    for key in sorted(by_month):
        month_ends.append(by_month[key][-1])
    return month_ends


def assert_m1_window(start: date, end: date) -> None:
    """Fail closed unless [start, end] lies within the authorized R2 scope."""
    if start < AUTHORIZED_MIN_DATE or end > AUTHORIZED_MAX_DATE or start > end:
        raise DataContractError(
            f"WINDOW_OUT_OF_SCOPE: [{start}, {end}] outside authorized "
            f"[{AUTHORIZED_MIN_DATE}, {AUTHORIZED_MAX_DATE}]."
        )
