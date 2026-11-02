"""XNYS 2026-2028 offline calendar fixture: source metadata, DST-aware sessions, fail-closed parsing."""

from __future__ import annotations

import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import market_calendar as mc
from acash.invest import preflight as pf

CAL = mc.load_calendar()


def _doc() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads((Path(mc.__file__).resolve().parents[3] / mc.NYSE_CALENDAR).read_text(encoding="utf-8"))
    return doc


def test_fixture_scope_and_source() -> None:
    assert (CAL.mic, CAL.timezone, CAL.coverage_start, CAL.coverage_end) == (
        "XNYS", "America/New_York", date(2026, 1, 1), date(2028, 12, 31))
    assert (len(CAL.full_closures), len(CAL.early_closes)) == (29, 5)
    assert CAL.source["issuer_release_published_on"] == "2025-12-23"
    assert CAL.source["official_calendar_url"] == "https://www.nyse.com/trade/hours-calendars"
    assert len(CAL.document_sha256) == 64


@pytest.mark.parametrize("day, status, open_utc, close_utc", [
    (date(2026, 1, 2), "OPEN", "2026-01-02T14:30:00+00:00", "2026-01-02T21:00:00+00:00"),
    (date(2026, 3, 6), "OPEN", "2026-03-06T14:30:00+00:00", "2026-03-06T21:00:00+00:00"),
    (date(2026, 3, 9), "OPEN", "2026-03-09T13:30:00+00:00", "2026-03-09T20:00:00+00:00"),
    (date(2026, 7, 3), "CLOSED_HOLIDAY", None, None),
    (date(2026, 10, 31), "CLOSED_WEEKEND", None, None),
    (date(2026, 11, 27), "EARLY_CLOSE", "2026-11-27T14:30:00+00:00", "2026-11-27T18:00:00+00:00"),
    (date(2028, 7, 3), "EARLY_CLOSE", "2028-07-03T13:30:00+00:00", "2028-07-03T17:00:00+00:00"),
    (date(2028, 1, 3), "OPEN", "2028-01-03T14:30:00+00:00", "2028-01-03T21:00:00+00:00"),
    (date(2025, 12, 31), mc.NOT_VERIFIED_PERIOD, None, None),
    (date(2029, 1, 2), mc.NOT_VERIFIED_PERIOD, None, None),
])
def test_dst_aware_sessions(day: date, status: str, open_utc: Any, close_utc: Any) -> None:
    assert mc.session(CAL, day) == {"status": status, "open_utc": open_utc, "close_utc": close_utc}


@pytest.mark.parametrize("mic, stamp, expected", [
    ("ARCX", "2026-10-30T16:00:00-04:00", mc.NOT_VERIFIED_VENUE),
    (None, "2026-10-30T16:00:00-04:00", mc.NOT_VERIFIED_VENUE),
    ("XNYS", "2026-10-30T16:00:00-04:00", "WITHIN_REGULAR_SESSION"),
    ("XNYS", "2026-10-30T20:00:00+00:00", "WITHIN_REGULAR_SESSION"),
    ("XNYS", "2026-10-30T16:00:01-04:00", "OUTSIDE_REGULAR_SESSION"),
    ("XNYS", "2026-11-27T14:00:00-05:00", "OUTSIDE_REGULAR_SESSION"),
    ("XNYS", "2026-12-25T12:00:00-05:00", "PRICE_TIME_ON_CLOSED_HOLIDAY"),
    ("XNYS", "2030-01-02T12:00:00-05:00", mc.NOT_VERIFIED_PERIOD),
])
def test_price_session_status(mic: Any, stamp: str, expected: str) -> None:
    assert mc.price_session_status(CAL, mic, datetime.fromisoformat(stamp)) == expected


def test_naive_timestamp_fails_closed() -> None:
    with pytest.raises(DataContractError, match="CALENDAR_TIMESTAMP_NOT_AWARE"):
        mc.price_session_status(CAL, "XNYS", datetime(2026, 10, 30, 16, 0))
    assert mc.price_session_status(CAL, "XNYS", datetime(2026, 10, 30, 19, 0, tzinfo=timezone.utc)) == "WITHIN_REGULAR_SESSION"


def _set(key: str, value: Any) -> Callable[[Dict[str, Any]], None]:
    return lambda d: d.__setitem__(key, value)


@pytest.mark.parametrize("mutate, code", [
    (_set("schema", "X"), "CALENDAR_SCHEMA_MISMATCH"),
    (_set("extra", 1), "CALENDAR_FIELDS_INVALID"),
    (_set("timezone", "Mars/Olympus"), "CALENDAR_TIMEZONE_INVALID"),
    (_set("regular_open", "9:30"), "CALENDAR_TIME_INVALID"),
    (_set("early_close", "16:30"), "CALENDAR_SESSION_TIMES_INCONSISTENT"),
    (_set("coverage_end", "2025-01-01"), "CALENDAR_COVERAGE_INVALID"),
    (_set("full_closures", ["2026-01-19", "2026-01-01"]), "CALENDAR_DATES_NOT_SORTED_UNIQUE"),
    (_set("full_closures", ["2026-01-01", "2026-01-01"]), "CALENDAR_DATES_NOT_SORTED_UNIQUE"),
    (_set("full_closures", ["2026-01-03"]), "CALENDAR_DATE_ON_WEEKEND"),
    (_set("full_closures", ["2029-01-01"]), "CALENDAR_DATE_OUTSIDE_COVERAGE"),
    (_set("early_closes", ["2026-01-01"]), "CALENDAR_DATE_BOTH_CLOSED_AND_EARLY_CLOSE"),
    (_set("full_closures", ["not-a-date"]), "CALENDAR_DATE_INVALID"),
    (lambda d: d["source"].pop("issuer_release_url"), "CALENDAR_SOURCE_INVALID"),
])
def test_malformed_calendar_fails_closed(mutate: Callable[[Dict[str, Any]], None], code: str) -> None:
    doc = copy.deepcopy(_doc())
    mutate(doc)
    with pytest.raises(DataContractError, match=code):
        mc.parse_calendar(doc)


def test_preflight_keeps_uncovered_venue_not_verified() -> None:
    report = pf.preflight(Path("docs/research/evidence/upi_v1_2_synthetic_snapshot.json"))
    check = next(c for c in report["checks"] if c["check"] == "market_session:SYNIDX")
    assert check["status"] == "INFO" and check["detail"].startswith(mc.NOT_VERIFIED_VENUE)
    assert report["preflight"] == "READY_WITH_WARNINGS"
