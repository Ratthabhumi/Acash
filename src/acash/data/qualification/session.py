"""Intraday Regular Trading Hours (RTH) boundary helpers and session schedule contracts.

IMPORTANT ARCHITECTURAL NOTE:
This module provides intraday time-window boundaries (09:30:00 to 16:00:00 America/New_York).
It is NOT the sovereign NYSE CA-1 calendar authority. It does NOT hard-code a holiday calendar
or assume that any given calendar date is an official trading day. Completeness checks require
an explicit verified session schedule; in its absence, CALENDAR_AUTHORITY_UNVERIFIED is emitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.models import (
    HistoricalSipBar,
    QualityFinding,
    QualityRuleCode,
    QualitySeverity,
)

NY_TZ = ZoneInfo("America/New_York")
RTH_OPEN_TIME: time = time(9, 30, 0)
RTH_CLOSE_TIME: time = time(16, 0, 0)


@dataclass(frozen=True)
class VerifiedSessionSchedule:
    """Explicit verified session schedule supplied by a certified calendar authority (e.g. CA-1)."""
    trading_date: date
    session_open_utc: datetime
    session_close_utc: datetime
    is_early_close: bool
    expected_bar_count: int


class RthSessionBounds:
    """Validates intraday timestamps against standard US Equity Regular Trading Hours (09:30 - 16:00 ET).

    Does NOT determine whether a date is a valid trading session, does NOT hard-code holidays,
    and does NOT automatically expect 390 bars.
    """

    @staticmethod
    def to_ny_time(dt_utc: datetime) -> datetime:
        """Convert a UTC datetime to America/New_York."""
        if dt_utc.tzinfo is None:
            raise DataContractError("dt_utc must be timezone-aware.")
        return dt_utc.astimezone(NY_TZ)

    @classmethod
    def is_within_rth(cls, dt_utc: datetime) -> bool:
        """Check if a bar's timestamp falls within 09:30:00 <= t < 16:00:00 America/New_York.

        For 1-minute bars, the bar starting at 09:30:00 ET is the first RTH bar, and the bar
        starting at 15:59:00 ET (closing at 16:00:00 ET) is the final regular session bar.
        """
        ny_dt = cls.to_ny_time(dt_utc)
        ny_time = ny_dt.time()
        return RTH_OPEN_TIME <= ny_time < RTH_CLOSE_TIME

    @classmethod
    def get_rth_query_interval(
        cls,
        session_date: date,
        inclusive_end_offset_seconds: int = 1,
    ) -> tuple[datetime, datetime]:
        """Compute UTC start and end bounds for querying a standard RTH session.

        Conceptual session:
            [09:30:00, 16:00:00) America/New_York (half-open, exactly 390 1-minute buckets).

        Provider query boundary adaptation:
            Alpaca's historical endpoint treats `end` as INCLUSIVE on bar start timestamps [T, T+1m).
            A query with `end = 16:00:00 ET` would inclusively match the 16:00 ET bar [16:00, 16:01),
            resulting in 391 bars including post-close / closing-auction crosses.
            To query strictly the regular session buckets [09:30:00, 15:59:00 ET] (390 bars),
            the inclusive `end` parameter must be set immediately prior to 16:00:00 ET
            (default offset: 1 second -> 15:59:59 ET -> 19:59:59Z on EDT / 20:59:59Z on EST).

        Returns:
            (start_utc, end_query_utc) as timezone-aware UTC datetimes.
        """
        from datetime import timedelta
        if inclusive_end_offset_seconds < 1:
            raise DataContractError("inclusive_end_offset_seconds must be at least 1 second.")

        open_et = datetime.combine(session_date, RTH_OPEN_TIME, tzinfo=NY_TZ)
        close_et = datetime.combine(session_date, RTH_CLOSE_TIME, tzinfo=NY_TZ)

        start_utc = open_et.astimezone(timezone.utc)
        end_query_utc = (close_et - timedelta(seconds=inclusive_end_offset_seconds)).astimezone(timezone.utc)
        return (start_utc, end_query_utc)

    @classmethod
    def validate_bar_intraday_hours(cls, bar: HistoricalSipBar) -> Optional[QualityFinding]:
        """Flag bars that fall outside standard Regular Trading Hours."""
        if not cls.is_within_rth(bar.timestamp_utc):
            ny_dt = cls.to_ny_time(bar.timestamp_utc)
            return QualityFinding(
                rule=QualityRuleCode.OUTSIDE_REGULAR_HOURS,
                severity=QualitySeverity.WARNING,
                message=(
                    f"Bar timestamp {bar.timestamp_utc.isoformat()} ({ny_dt.strftime('%H:%M:%S')} ET) "
                    f"falls outside standard RTH (09:30:00–16:00:00 ET)."
                ),
                timestamp_utc=bar.timestamp_utc,
                details={"ny_time": ny_dt.strftime("%H:%M:%S ET")},
            )
        return None

    @classmethod
    def evaluate_session_completeness(
        cls,
        session_date: date,
        bars: Sequence[HistoricalSipBar],
        verified_schedule: Optional[VerifiedSessionSchedule] = None,
    ) -> Sequence[QualityFinding]:
        """Evaluate completeness of observed bars for session_date.

        If verified_schedule is None, emits CALENDAR_AUTHORITY_UNVERIFIED without fabricating
        expected bar counts or falsely flagging holidays/early-closes as missing data.
        """
        findings: list[QualityFinding] = []
        if verified_schedule is None:
            findings.append(
                QualityFinding(
                    rule=QualityRuleCode.CALENDAR_AUTHORITY_UNVERIFIED,
                    severity=QualitySeverity.INFO,
                    message=(
                        f"Calendar authority unverified for {session_date.isoformat()}; "
                        "completeness and missing-bar evaluation skipped to prevent false missing-data claims."
                    ),
                    details={"session_date": session_date.isoformat()},
                )
            )
            return findings

        # When an authoritative verified schedule is provided:
        observed_timestamps = {b.timestamp_utc for b in bars}
        # Iterate expected minute timestamps
        from datetime import timedelta
        curr = verified_schedule.session_open_utc
        missing_count = 0
        first_missing: Optional[datetime] = None
        while curr < verified_schedule.session_close_utc:
            if curr not in observed_timestamps:
                missing_count += 1
                if first_missing is None:
                    first_missing = curr
            curr += timedelta(minutes=1)

        if missing_count > 0:
            findings.append(
                QualityFinding(
                    rule=QualityRuleCode.MISSING_BAR,
                    severity=QualitySeverity.WARNING,
                    message=(
                        f"Verified session {session_date.isoformat()} has {missing_count} missing minute bars "
                        f"(expected {verified_schedule.expected_bar_count}, observed {len(observed_timestamps)}). "
                        "Zero silent imputation performed."
                    ),
                    timestamp_utc=first_missing,
                    details={
                        "missing_count": missing_count,
                        "expected_count": verified_schedule.expected_bar_count,
                        "observed_count": len(observed_timestamps),
                    },
                )
            )
        return findings
