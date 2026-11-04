"""Venue-verified session view: DST, holidays, early closes and Bangkok conversion."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import market_calendar as mc

CAL = mc.load_calendar()


def _view(iso: str) -> dict[str, Any]:
    return mc.session_view(CAL, datetime.fromisoformat(iso))


def test_regular_session_is_2130_to_0400_bangkok() -> None:
    view = _view("2026-11-04T15:00:00+00:00")  # 10:00 EST
    assert view["state"] == "OPEN"
    assert view["today"]["open_ict"] == "2026-11-04 21:30 +07"
    assert view["today"]["close_ict"] == "2026-11-05 04:00 +07"
    assert view["calendar_status"] == "VERIFIED_VENUE_FIXTURE" and view["mic"] == "XNYS"


def test_daylight_saving_moves_the_bangkok_window() -> None:
    # 2026-07-15 14:00 UTC = 10:00 EDT; the same wall-clock session opens at 20:30 ICT.
    view = _view("2026-07-15T14:00:00+00:00")
    assert view["state"] == "OPEN"
    assert view["today"]["open_ict"] == "2026-07-15 20:30 +07"
    assert view["today"]["close_ict"] == "2026-07-16 03:00 +07"


def test_thanksgiving_is_closed_and_the_next_session_is_the_early_close() -> None:
    view = _view("2026-11-26T15:00:00+00:00")
    assert view["state"] == "CLOSED_HOLIDAY"
    assert view["next_session"]["date"] == "2026-11-27"
    assert view["next_session"]["status"] == "EARLY_CLOSE"
    assert view["next_session"]["close_ict"] == "2026-11-28 01:00 +07"


def test_early_close_bounds_the_session_and_the_eod_window() -> None:
    before = _view("2026-11-27T15:00:00+00:00")  # 10:00 EST, inside the shortened session
    after = _view("2026-11-27T19:00:00+00:00")   # 14:00 EST, after the 13:00 close
    assert before["state"] == "OPEN" and before["today"]["status"] == "EARLY_CLOSE"
    assert after["state"] == "CLOSED"
    assert before["eod_eligible_after"] == "2026-11-28 01:30 +07"


def test_christmas_is_closed_and_the_weekend_is_not_a_session() -> None:
    assert _view("2026-12-25T15:00:00+00:00")["state"] == "CLOSED_HOLIDAY"
    saturday = _view("2026-11-07T15:00:00+00:00")
    assert saturday["state"] == "CLOSED_WEEKEND"
    assert saturday["next_session"]["date"] == "2026-11-09"


def test_dates_outside_the_verified_fixture_are_not_guessed() -> None:
    view = _view("2031-03-05T15:00:00+00:00")
    assert view["calendar_status"] == mc.NOT_VERIFIED_PERIOD
    assert view["state"] == mc.NOT_VERIFIED_PERIOD
    assert view["next_session"] is None


def test_next_session_skips_holidays_within_coverage() -> None:
    assert mc.next_session(CAL, date(2026, 11, 26)) == date(2026, 11, 27)
    assert mc.next_session(CAL, date(2026, 12, 25)) == date(2026, 12, 28)
    assert mc.next_session(CAL, date(2029, 1, 1)) is None


def test_session_view_requires_an_aware_timestamp() -> None:
    with pytest.raises(DataContractError, match="CALENDAR_TIMESTAMP_NOT_AWARE"):
        mc.session_view(CAL, datetime(2026, 11, 4, 15, 0))


def test_thai_holidays_are_not_part_of_a_us_session() -> None:
    # 2026-12-07 is a Thai financial-institutions holiday but a normal NYSE session.
    view = mc.session_view(CAL, datetime(2026, 12, 7, 15, 0, tzinfo=timezone.utc))
    assert view["state"] == "OPEN" and view["today"]["status"] == "OPEN"
