"""Inception-aware coverage, grouped request accounting and upgrade-safe installation."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.market_data import collector as co
from acash.market_data import warehouse as wh

CLOCK = lambda: datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
D = date(2026, 1, 5)


def _record(directory: Path, permitted: bool = True) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "odr.json"
    path.write_text(json.dumps({
        "status": "RATIFIED",
        "scope_providers": [{"provider_id": "MASSIVE_BASIC", "cache_permitted": permitted,
                             "retention_policy_verified": permitted}]}), encoding="utf-8")
    return path


def _bar(symbol: str, day: date, close: str = "100") -> Dict[str, Any]:
    from decimal import Decimal
    middle = Decimal(close)
    return {"symbol": symbol, "session_date": day, "open": str(middle), "high": str(middle + 1),
            "low": str(middle - 1), "close": close, "volume": "10", "adjusted": False,
            "provider": "MASSIVE_BASIC", "retrieved_at": "2026-01-10T12:00:00+00:00"}


def test_pre_inception_dates_are_not_applicable_not_missing(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path))
    days = [date(2026, 1, 5 + i) for i in range(4)]
    store.record_sessions("VOO", days, source="MASSIVE_BASIC", job_id="j")
    store.record_sessions("NASA", days[2:], source="MASSIVE_BASIC", job_id="j")
    matrix = wh.coverage(store.session_index(), ["VOO", "NASA"])
    nasa = matrix["symbols"]["NASA"]
    assert nasa["not_applicable_pre_inception"] == 2 and nasa["missing_after_inception"] == 0
    assert nasa["status"] == "PARTIAL_LIMITED_HISTORY" and nasa["inception_limited_history"] is True
    assert matrix["covered"] == 1 and matrix["partial_limited_history"] == 1 and matrix["missing"] == 0


def test_a_gap_after_inception_stays_partial(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path))
    days = [date(2026, 1, 5 + i) for i in range(4)]
    store.record_sessions("VOO", days, source="MASSIVE_BASIC", job_id="j")
    store.record_sessions("HOOD", [days[0], days[2], days[3]], source="MASSIVE_BASIC", job_id="j")
    hood = wh.coverage(store.session_index(), ["VOO", "HOOD"])["symbols"]["HOOD"]
    assert hood["not_applicable_pre_inception"] == 0 and hood["missing_after_inception"] == 1
    assert hood["status"] == "PARTIAL"


class FakeGrouped:
    provider_id = "MASSIVE_BASIC"

    def __init__(self, fail: Sequence[date] = (), rows_for: Dict[date, List[Dict[str, Any]]] | None = None) -> None:
        self.fail = set(fail)
        self.rows_for = rows_for or {}
        self.calls: List[date] = []

    def grouped_daily(self, session: date, symbols: Sequence[str]) -> List[Dict[str, Any]]:
        self.calls.append(session)
        if session in self.fail:
            raise DataContractError("PROVIDER_UNAVAILABLE: MASSIVE_BASIC HTTP 500.")
        return self.rows_for.get(session, [_bar("VOO", session)])


def test_grouped_counts_attempts_including_failures_and_keeps_missing(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path))
    day1, day2 = date(2026, 1, 5), date(2026, 1, 6)
    source = FakeGrouped(fail=[day2])
    result = co.collect_grouped(source, store, ["VOO"], [day1, day2], job_id="j1", pause=lambda _: None)
    assert result["requests"] == 2  # the failed attempt is counted too
    assert result["sessions"] == [day1.isoformat()]
    assert result["errors"][day2.isoformat()] == "PROVIDER_UNAVAILABLE"
    assert result["missing_after"] == [day2.isoformat()]
    assert len(store.read("VOO")) == 1


def test_grouped_is_idempotent_when_nothing_is_missing(tmp_path: Path) -> None:
    store = wh.BarWarehouse(tmp_path / "w", CLOCK, _record(tmp_path))
    day = date(2026, 1, 5)
    co.collect_grouped(FakeGrouped(), store, ["VOO"], [day], job_id="j1", pause=lambda _: None)
    assert co.grouped_sessions(store, ["VOO"], day, day) == []
    second = co.collect_grouped(FakeGrouped(), store, ["VOO"], [], job_id="j2", pause=lambda _: None)
    assert second["requests"] == 0 and second["rows_added"] == 0


def test_installer_preserves_newer_host_warehouse_on_upgrade() -> None:
    installer = Path("scripts/deploy/deploy_acash_collector.sh").read_text(encoding="utf-8")
    assert "existing warehouse preserved (bundle data not copied over newer state)" in installer
    assert "if [[ -f \"$STATE_ROOT/private/market_warehouse/manifest.json\" ]]" in installer
    assert "chown -R root:root \"$APP_ROOT\"" in installer
