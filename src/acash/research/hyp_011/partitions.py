"""Frozen HYP_011 partitions and session schedule (R1 §17)."""

from __future__ import annotations

from datetime import date
from typing import Dict, List

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar

HISTORICAL_START: date = date(2016, 1, 1)
HISTORICAL_END: date = date(2024, 12, 31)
REBALANCE_YEARS = (2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024)


def expected_sessions(calendar: NyseCa1Calendar) -> List[date]:
    """All eligible NYSE sessions 2016-01-01..2024-12-31 (early closes included)."""
    sessions: List[date] = []
    cursor = HISTORICAL_START
    while cursor <= HISTORICAL_END:
        if calendar.is_trading_session(cursor):
            sessions.append(cursor)
        cursor = date.fromordinal(cursor.toordinal() + 1)
    if not sessions:
        raise DataContractError("HYP_011_PARTITION_EMPTY.")
    return sessions


def expected_rebalance_sessions(sessions: List[date]) -> List[date]:
    """Initial allocation session + first eligible open of each year 2017-2024."""
    if not sessions or sessions != sorted(sessions) or len(set(sessions)) != len(sessions):
        raise DataContractError("HYP_011_SESSIONS_MUST_BE_UNIQUE_CHRONOLOGICAL.")
    by_year: Dict[int, List[date]] = {}
    for session in sessions:
        by_year.setdefault(session.year, []).append(session)
    schedule = [sessions[0]]
    for year in REBALANCE_YEARS:
        if year not in by_year:
            raise DataContractError(f"HYP_011_MISSING_REBALANCE_YEAR: {year}.")
        schedule.append(by_year[year][0])
    if len(schedule) != 1 + len(REBALANCE_YEARS):
        raise DataContractError("HYP_011_REBALANCE_SCHEDULE_CORRUPT.")
    return schedule
