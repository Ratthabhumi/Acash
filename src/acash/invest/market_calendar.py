"""Offline, source-attributed exchange session calendar (validation and reporting only).

The fixture covers one venue (a single MIC) for a fixed date range. Anything outside that
venue or range stays ``MARKET_SESSION_NOT_VERIFIED``; no dates are inferred and no market
data is fetched. Session times are converted with ``zoneinfo`` so DST is handled per date.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.ppds.private_observation import read_bounded_json

CALENDAR_SCHEMA = "ACASH_EXCHANGE_CALENDAR_V1"
NYSE_CALENDAR = Path("docs/research/evidence/nyse_xnys_calendar_2026_2028.json")
NOT_VERIFIED_VENUE = "MARKET_SESSION_NOT_VERIFIED_VENUE_NOT_COVERED"
NOT_VERIFIED_PERIOD = "MARKET_SESSION_NOT_VERIFIED_PERIOD_NOT_COVERED"
_FIELDS = {"schema", "calendar_id", "mic", "venue_scope", "timezone", "regular_open", "regular_close", "early_close",
           "coverage_start", "coverage_end", "full_closures", "early_closes", "source"}
_SOURCE_FIELDS = {"official_calendar_url", "issuer_release_url", "issuer_release_published_on", "transcribed_by", "use"}
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@dataclass(frozen=True)
class ExchangeCalendar:
    calendar_id: str
    mic: str
    timezone: str
    regular_open: time
    regular_close: time
    early_close: time
    coverage_start: date
    coverage_end: date
    full_closures: FrozenSet[date]
    early_closes: FrozenSet[date]
    source: Dict[str, str]
    document_sha256: str


def _clock(raw: Any, key: str) -> time:
    if not isinstance(raw, str) or not _HHMM.match(raw):
        raise DataContractError(f"CALENDAR_TIME_INVALID: {key}.")
    hour, minute = raw.split(":")
    return time(int(hour), int(minute))


def _day(raw: Any, key: str) -> date:
    try:
        return date.fromisoformat(str(raw))
    except ValueError as exc:
        raise DataContractError(f"CALENDAR_DATE_INVALID: {key}.") from exc


def _days(raw: Any, key: str, start: date, end: date) -> FrozenSet[date]:
    if not isinstance(raw, list):
        raise DataContractError(f"CALENDAR_LIST_REQUIRED: {key}.")
    days = [_day(d, key) for d in raw]
    if days != sorted(days) or len(set(days)) != len(days):
        raise DataContractError(f"CALENDAR_DATES_NOT_SORTED_UNIQUE: {key}.")
    for d in days:
        if not start <= d <= end:
            raise DataContractError(f"CALENDAR_DATE_OUTSIDE_COVERAGE: {key} {d.isoformat()}.")
        if d.weekday() >= 5:
            raise DataContractError(f"CALENDAR_DATE_ON_WEEKEND: {key} {d.isoformat()}.")
    return frozenset(days)


def parse_calendar(doc: Any) -> ExchangeCalendar:
    if not isinstance(doc, dict) or set(doc) != _FIELDS:
        raise DataContractError("CALENDAR_FIELDS_INVALID.")
    if doc["schema"] != CALENDAR_SCHEMA:
        raise DataContractError("CALENDAR_SCHEMA_MISMATCH.")
    source = doc["source"]
    if not isinstance(source, dict) or set(source) != _SOURCE_FIELDS or not all(isinstance(v, str) and v for v in source.values()):
        raise DataContractError("CALENDAR_SOURCE_INVALID.")
    try:
        ZoneInfo(str(doc["timezone"]))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise DataContractError("CALENDAR_TIMEZONE_INVALID.") from exc
    start, end = _day(doc["coverage_start"], "coverage_start"), _day(doc["coverage_end"], "coverage_end")
    if end < start:
        raise DataContractError("CALENDAR_COVERAGE_INVALID.")
    opening, closing, early = (_clock(doc[k], k) for k in ("regular_open", "regular_close", "early_close"))
    if not opening < early < closing:
        raise DataContractError("CALENDAR_SESSION_TIMES_INCONSISTENT.")
    closures = _days(doc["full_closures"], "full_closures", start, end)
    earlies = _days(doc["early_closes"], "early_closes", start, end)
    if closures & earlies:
        raise DataContractError("CALENDAR_DATE_BOTH_CLOSED_AND_EARLY_CLOSE.")
    return ExchangeCalendar(str(doc["calendar_id"]), str(doc["mic"]), str(doc["timezone"]), opening, closing, early,
                            start, end, closures, earlies, dict(source), CanonicalConfigSerializer.compute_sha256(doc))


def load_calendar(path: Optional[Path] = None) -> ExchangeCalendar:
    """Load a committed public calendar fixture, resolved against this checkout."""
    return parse_calendar(read_bounded_json(Path(__file__).resolve().parents[3] / (path or NYSE_CALENDAR), "CALENDAR"))


def session(cal: ExchangeCalendar, day: date) -> Dict[str, Optional[str]]:
    if not cal.coverage_start <= day <= cal.coverage_end:
        return {"status": NOT_VERIFIED_PERIOD, "open_utc": None, "close_utc": None}
    if day.weekday() >= 5:
        return {"status": "CLOSED_WEEKEND", "open_utc": None, "close_utc": None}
    if day in cal.full_closures:
        return {"status": "CLOSED_HOLIDAY", "open_utc": None, "close_utc": None}
    tz = ZoneInfo(cal.timezone)
    closing = cal.early_close if day in cal.early_closes else cal.regular_close
    utc = ZoneInfo("UTC")
    return {"status": "EARLY_CLOSE" if day in cal.early_closes else "OPEN",
            "open_utc": datetime.combine(day, cal.regular_open, tz).astimezone(utc).isoformat(),
            "close_utc": datetime.combine(day, closing, tz).astimezone(utc).isoformat()}


def price_session_status(cal: ExchangeCalendar, mic: Optional[str], published_at: datetime) -> str:
    """Where a price timestamp falls relative to the venue session; never evidence of availability."""
    if published_at.tzinfo is None:
        raise DataContractError("CALENDAR_TIMESTAMP_NOT_AWARE.")
    if mic != cal.mic:
        return NOT_VERIFIED_VENUE
    day = published_at.astimezone(ZoneInfo(cal.timezone)).date()
    info = session(cal, day)
    if info["open_utc"] is None or info["close_utc"] is None:
        return str(info["status"]) if info["status"] == NOT_VERIFIED_PERIOD else f"PRICE_TIME_ON_{info['status']}"
    opening, closing = datetime.fromisoformat(info["open_utc"]), datetime.fromisoformat(info["close_utc"])
    return "WITHIN_REGULAR_SESSION" if opening <= published_at <= closing else "OUTSIDE_REGULAR_SESSION"
