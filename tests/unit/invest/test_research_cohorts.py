"""Two cohorts: established history keeps its floor, recent inception admits a new listing."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List

from acash.invest import research_panel as rp

DAYS = [date(2026, 1, 5) + timedelta(days=i) for i in range(260)]
NEW_DAYS = DAYS[110:]  # a listing that starts later, like NASA on 2026-03-30


def _closes() -> Dict[str, Dict[date, Decimal]]:
    return {"LONG": {d: Decimal("100") + i for i, d in enumerate(DAYS)},
            "NASA": {d: Decimal("20") + Decimal(i) / 10 for i, d in enumerate(NEW_DAYS)}}


def test_established_cohort_excludes_the_new_listing() -> None:
    cohorts = rp.build_cohorts(_closes(), {"LONG": Decimal("0.5"), "NASA": Decimal("0.5")}, ["LONG", "NASA"])
    established = [c for c in cohorts["cohorts"] if c["cohort_id"] == "ESTABLISHED_HISTORY"][0]
    assert established["excluded"]["NASA"]["reason"] == "SESSION_COVERAGE_BELOW_MINIMUM"
    assert established["comparable_to_established"] is True


def test_recent_cohort_includes_the_new_listing_from_its_first_price() -> None:
    cohorts = rp.build_cohorts(_closes(), {"LONG": Decimal("0.5"), "NASA": Decimal("0.5")}, ["LONG", "NASA"])
    recent = [c for c in cohorts["cohorts"] if c["cohort_id"] == "RECENT_INCEPTION"][0]
    assert recent["status"] == "PANEL_READY" and recent["excluded"] == {}
    assert recent["evaluation_window"]["start"] == NEW_DAYS[0].isoformat()
    assert recent["session_count"] < len(DAYS)
    assert recent["comparable_to_established"] is False
    assert recent["labels"]["performance_basis"] == "HYPOTHETICAL_HISTORICAL_BASKET"
    assert recent["labels"]["realized_performance"] is False


def test_instrument_metadata_records_the_inception_limit() -> None:
    cohorts = rp.build_cohorts(_closes(), {"LONG": Decimal("0.5"), "NASA": Decimal("0.5")}, ["LONG", "NASA"])
    rows = {m["security_id"]: m for m in cohorts["cohorts"][0]["instruments"]}
    assert rows["NASA"]["inception_limited_history"] is True
    assert rows["NASA"]["research_eligibility_reason"] == "INCEPTION_LIMITED_HISTORY"
    assert rows["NASA"]["first_qualified_price_date"] == NEW_DAYS[0].isoformat()
    assert rows["LONG"]["qualification_state"] == "QUALIFIED"


def test_cohort_note_forbids_cross_cohort_ranking() -> None:
    cohorts = rp.build_cohorts(_closes(), {"LONG": Decimal("0.5"), "NASA": Decimal("0.5")}, ["LONG", "NASA"])
    assert cohorts["schema"] == "ACASH_RESEARCH_COHORTS_V1"
    assert "not permitted" in cohorts["note"] or "different measurement" in cohorts["note"]
