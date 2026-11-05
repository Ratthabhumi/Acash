"""Warehouse storage gate, idempotent commits and incremental collection (synthetic fixtures)."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.market_data import collector as co
from acash.market_data import warehouse as wh

D = date(2026, 1, 5)
CLOCK = lambda: datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


def _record(directory: Path, permitted: bool) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "odr.json"
    path.write_text(json.dumps({
        "status": "RATIFIED", "scope_providers": [{"provider_id": "MASSIVE_BASIC", "cache_permitted": True if permitted else None,
                             "retention_policy_verified": True if permitted else None}],
    }), encoding="utf-8")
    return path


def _bar(symbol: str = "VOO", day: int = 5, close: str = "100") -> Dict[str, Any]:
    middle = Decimal(close)
    return {"symbol": symbol, "session_date": date(2026, 1, day), "open": str(middle), "high": str(middle + 1),
            "low": str(middle - 1), "close": close, "volume": "10", "adjusted": False,
            "provider": "MASSIVE_BASIC", "retrieved_at": "2026-01-10T12:00:00+00:00"}


def test_commit_is_idempotent_and_records_lineage(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    first = store.commit("VOO", [_bar(day=5), _bar(day=6, close="101")], job_id="j1")
    assert first["changed"] is True and first["added"] == 2
    second = store.commit("VOO", [_bar(day=6, close="101")], job_id="j1")
    assert second["changed"] is False and second["added"] == 0 and second["sessions"] == 2
    assert len(store.read("VOO")) == 2
    entry = store.manifest()["partitions"]["VOO"]
    assert entry["sha256"] and entry["storage_rights"] == "PERMITTED" and entry["source"] == "MASSIVE_BASIC"
    assert not list((tmp_path / "w" / "bars").glob("*.tmp"))


def test_conflicting_duplicate_is_refused(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    store.commit("VOO", [_bar(day=5, close="100")], job_id="j1")
    with pytest.raises(DataContractError, match="WAREHOUSE_CONFLICTING_DUPLICATE"):
        store.commit("VOO", [_bar(day=5, close="100.5")], job_id="j2")


def test_retention_rights_are_a_hard_gate(tmp_path: Path) -> None:
    blocked = wh.BarWarehouse(tmp_path / "a", CLOCK, _record(tmp_path / "a_odr", False))
    with pytest.raises(DataContractError, match="STORAGE_RIGHTS_UNESTABLISHED"):
        blocked.commit("VOO", [_bar()], job_id="j1")
    assert not (tmp_path / "a" / "bars").exists()
    # A missing governance record is also not permission.
    assert not wh.storage_permitted("MASSIVE_BASIC", tmp_path / "absent.json")


def test_invalid_bar_is_refused_not_zero_filled(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    for broken in ({**_bar(), "close": "0"}, {**_bar(), "high": "-1"}, {**_bar(), "session_date": "nope"}):
        with pytest.raises(DataContractError, match="WAREHOUSE_BAR_INVALID"):
            store.commit("VOO", [broken], job_id="j1")


def test_session_index_keeps_dates_only(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    store.record_sessions("VOO", [D, date(2026, 1, 6)], source="MASSIVE_BASIC", job_id="j1")
    index = store.session_index()
    assert index["symbols"]["VOO"]["dates"] == ["2026-01-05", "2026-01-06"]
    assert index["symbols"]["VOO"]["contains_prices"] is False and index["contains_prices"] is False


def test_coverage_reports_gaps_without_filling(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    store.record_sessions("VOO", [date(2026, 1, 5), date(2026, 1, 6)], source="MASSIVE_BASIC", job_id="j1")
    store.record_sessions("BIL", [date(2026, 1, 5)], source="MASSIVE_BASIC", job_id="j1")
    matrix = wh.coverage(store.session_index(), ["VOO", "BIL", "GLD"])
    assert matrix["union_sessions"] == 2
    assert matrix["symbols"]["BIL"]["status"] == "PARTIAL" and matrix["symbols"]["BIL"]["missing_vs_union"] == 1
    assert matrix["symbols"]["GLD"]["status"] == "MISSING"
    assert matrix["covered"] == 1 and matrix["partial"] == 1 and matrix["missing"] == 1


class FakeSource:
    provider_id = "MASSIVE_BASIC"

    def __init__(self, rows: Dict[str, List[Dict[str, Any]]], refuse: int = 0,
                 errors: Optional[Dict[str, DataContractError]] = None) -> None:
        self.rows, self.refuse, self.errors = rows, refuse, errors or {}
        self.calls: List[Any] = []
        self.skipped: List[str] = []

    def historical_daily(self, symbols: Sequence[str], start: date, end: date) -> List[Dict[str, Any]]:
        symbol = symbols[0]
        self.calls.append((symbol, start, end))
        if self.refuse > 0:
            self.refuse -= 1
            self.skipped = [symbol]
            return []
        self.skipped = []
        if symbol in self.errors:
            raise self.errors[symbol]
        return [row for row in self.rows.get(symbol, []) if start <= row["session_date"] <= end]


def test_incremental_plan_resumes_from_last_indexed_session(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    store.record_sessions("VOO", [date(2026, 1, 5)], source="MASSIVE_BASIC", job_id="j0")
    roadmap = co.plan(store, ["VOO", "GLD"], date(2025, 12, 1), date(2026, 1, 6))["symbols"]
    assert roadmap["VOO"] == {"status": "NEEDS_INCREMENT", "from": "2026-01-06", "to": "2026-01-06"}
    assert roadmap["GLD"]["status"] == "NEEDS_FULL_RANGE"


def test_collect_pauses_on_rate_limit_then_completes(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    pauses: List[float] = []
    source = FakeSource({"VOO": [_bar(day=5), _bar(day=6)]}, refuse=1)
    report = co.collect(source, store, ["VOO"], date(2026, 1, 5), date(2026, 1, 6), job_id="j1",
                        pause=pauses.append)
    assert report.completed == ["VOO"] and report.requests == 2 and pauses == [co.RATE_LIMIT_PAUSE_SECONDS]
    assert report.persisted is True and len(store.read("VOO")) == 2


def test_failed_symbol_does_not_abort_the_run(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    source = FakeSource({"VOO": [_bar(day=5)]},
                        errors={"SPCX": DataContractError("PROVIDER_UNAVAILABLE: MASSIVE_BASIC HTTP 404.")})
    report = co.collect(source, store, ["SPCX", "VOO"], date(2026, 1, 5), date(2026, 1, 5), job_id="j1")
    assert report.failed == ["SPCX"] and report.completed == ["VOO"]
    assert report.symbols["SPCX"]["status"] == "NOT_FOUND"


def test_access_denied_stops_before_spending_more_requests(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    source = FakeSource({}, errors={"VOO": DataContractError("PROVIDER_ACCESS_DENIED: MASSIVE_BASIC HTTP 401.")})
    report = co.collect(source, store, ["VOO", "GLD"], date(2026, 1, 5), date(2026, 1, 5), job_id="j1")
    assert report.stopped == "ACCESS_DENIED" and report.requests == 1 and source.calls == [("VOO", date(2026, 1, 5),
                                                                                            date(2026, 1, 5))]


def test_request_budget_defers_and_checkpoint_resumes(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    rows = {"VOO": [_bar("VOO", 5)], "GLD": [_bar("GLD", 5, "180")]}
    first = co.collect(FakeSource(rows), store, ["VOO", "GLD"], date(2026, 1, 5), date(2026, 1, 5),
                       job_id="j1", max_requests=1, pause=lambda _: None)
    assert first.completed == ["VOO"] and first.stopped == "REQUEST_BUDGET_EXHAUSTED"
    second = co.collect(FakeSource(rows), store, ["VOO", "GLD"], date(2026, 1, 5), date(2026, 1, 5),
                        job_id="j1", max_requests=1, pause=lambda _: None)
    assert second.completed == ["GLD"] and second.skipped_existing == ["VOO"]


def test_collect_without_retention_rights_never_claims_a_dataset(tmp_path: Path) -> None:
    blocked = _record(tmp_path / "blocked_odr", False)
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, blocked)
    report = co.collect(FakeSource({"VOO": [_bar()]}), store, ["VOO"], D, D, job_id="j1",
                        pause=lambda _: None)
    assert report.persisted is False and report.storage_rights == "UNESTABLISHED"
    assert report.completed == ["VOO"] and not store.partition("VOO").exists()
    with pytest.raises(DataContractError, match="STORAGE_RIGHTS_UNESTABLISHED"):
        co.collect(FakeSource({"VOO": [_bar()]}), store, ["VOO"], D, D, job_id="j2", persist=True)


def test_repository_record_permits_private_storage_with_a_bounded_policy() -> None:
    """The ratified ODR-004 record, not a fixture, is what the gate reads in production."""
    record = Path("docs/governance/ODR_UPI_MARKET_DATA_004.json")
    assert wh.storage_permitted("MASSIVE_BASIC", record) is True
    assert wh.storage_permitted("BOT_REFERENCE_FX", record) is True
    # Memory-only providers stay refused, so the gate is not a blanket "yes".
    assert wh.storage_permitted("ALPACA_BASIC", record) is False
    terms = wh.retention_terms("MASSIVE_BASIC", record)
    assert terms is not None
    assert terms["max_retention_after_terms_termination_days"] == 30
    assert terms["purge_required_on_termination"] is True
    assert terms["terms_revision"]["terms_revision_dated"] == "2026-11-03"
    assert terms["cache_rights"]["redistribution"] == "DENIED"


def test_purge_removes_every_observation_and_records_only_the_deletion(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    store.commit("VOO", [_bar(day=5), _bar(day=6, close="101")], job_id="j1")
    store.record_sessions("VOO", [date(2026, 1, 5)], source="MASSIVE_BASIC", job_id="j1")
    store.save_state("j1", {"completed": ["VOO"]})
    assert store.partition("VOO").is_file()
    with pytest.raises(DataContractError, match="WAREHOUSE_PURGE_REASON_REQUIRED"):
        store.purge("   ")
    result = store.purge("TERMS_ENDED")
    assert result["partitions_removed"] == 1
    assert not store.partition("VOO").exists() and not store.manifest_path.exists()
    log = json.loads((tmp_path / "w" / "purge_log.json").read_text(encoding="utf-8"))
    assert log["purges"][0]["reason"] == "TERMS_ENDED"
    assert "close" not in json.dumps(log)


def test_durable_plan_resumes_from_partitions_not_the_index(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    # The index says the range was seen, but nothing was persisted: a durable pass must refetch it.
    store.record_sessions("VOO", [date(2026, 1, 5)], source="MASSIVE_BASIC", job_id="j0")
    memory = co.plan(store, ["VOO"], date(2026, 1, 1), date(2026, 1, 6))
    durable = co.plan(store, ["VOO"], date(2026, 1, 1), date(2026, 1, 6), durable=True)
    assert memory["symbols"]["VOO"]["status"] == "NEEDS_INCREMENT"
    assert durable["symbols"]["VOO"] == {"status": "NEEDS_FULL_RANGE",
                                         "from": "2026-01-01", "to": "2026-01-06"}
    store.commit("VOO", [_bar(day=5), _bar(day=6, close="101")], job_id="j1")
    assert co.plan(store, ["VOO"], date(2026, 1, 1), date(2026, 1, 6),
                   durable=True)["symbols"]["VOO"]["status"] == "COMPLETE"


def test_durable_pass_writes_partitions_once(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    rows = {"VOO": [_bar(day=5), _bar(day=6, close="101")]}
    first = co.collect(FakeSource(rows), store, ["VOO"], date(2026, 1, 5), date(2026, 1, 6),
                       job_id="j1", pause=lambda _: None)
    assert first.persisted is True and store.partition("VOO").is_file()
    second = co.collect(FakeSource(rows), store, ["VOO"], date(2026, 1, 5), date(2026, 1, 6),
                        job_id="j1", pause=lambda _: None)
    assert second.completed == [] and second.skipped_existing == ["VOO"] and second.requests == 0


def test_force_full_refetches_without_duplicating_rows(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    rows = {"VOO": [_bar(day=5), _bar(day=6, close="101")]}
    co.collect(FakeSource(rows), store, ["VOO"], date(2026, 1, 5), date(2026, 1, 6), job_id="j1",
               pause=lambda _: None)
    again = co.collect(FakeSource(rows), store, ["VOO"], date(2026, 1, 5), date(2026, 1, 6), job_id="j2",
                       pause=lambda _: None, force_full=True)
    assert again.completed == ["VOO"] and again.requests == 1 and again.skipped_existing == []
    assert len(store.read("VOO")) == 2  # refetched, not duplicated


def test_gaps_report_missing_sessions_against_the_union(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path, True))
    store.record_sessions("VOO", [date(2026, 1, 5), date(2026, 1, 6)], source="MASSIVE_BASIC", job_id="j1")
    store.record_sessions("BIL", [date(2026, 1, 5)], source="MASSIVE_BASIC", job_id="j1")
    result = co.gaps(store, ["VOO", "BIL"])
    assert result["symbols_with_gaps"] == ["BIL"]
    assert result["detail"]["BIL"]["missing"] == 1 and result["detail"]["BIL"]["first_missing"] == "2026-01-06"
    assert result["union_sessions"] == 2


def test_next_run_follows_the_venue_calendar_and_dst() -> None:
    from datetime import datetime, timezone
    before_close = co.next_run(datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc))  # 07:00 ET
    assert before_close["session_date"] == "2026-11-05"
    assert before_close["next_run_et"].startswith("2026-11-05T18:30:00-05:00")
    after_close = co.next_run(datetime(2026, 11, 6, 0, 30, tzinfo=timezone.utc))  # 19:30 ET on 11-05
    assert after_close["session_date"] == "2026-11-06"
    thanksgiving = co.next_run(datetime(2026, 11, 26, 23, 0, tzinfo=timezone.utc))  # 18:00 ET holiday
    assert thanksgiving["session_date"] == "2026-11-27" and thanksgiving["session_status"] == "EARLY_CLOSE"


def test_latest_completed_session_waits_for_close_and_publication() -> None:
    from datetime import datetime, timezone
    before_close = co.latest_completed_session(datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc))
    assert before_close["session_date"] == "2026-11-04"  # 07:00 ET, today has not closed
    after_publication = co.latest_completed_session(datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc))
    assert after_publication["session_date"] == "2026-11-05"  # 19:00 ET + 30 min delay
    assert after_publication["eligible_at_ict"].startswith("2026-11-06T04:30:00")


def test_latest_completed_session_skips_holidays_and_weekends() -> None:
    from datetime import datetime, timezone
    thanksgiving = co.latest_completed_session(datetime(2026, 11, 26, 23, 0, tzinfo=timezone.utc))
    assert thanksgiving["session_date"] == "2026-11-25"
    saturday = co.latest_completed_session(datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc))
    assert saturday["session_date"] == "2026-11-06"
    early_close = co.latest_completed_session(datetime(2026, 11, 27, 19, 0, tzinfo=timezone.utc))
    assert early_close["session_date"] == "2026-11-27" and early_close["session_status"] == "EARLY_CLOSE"
