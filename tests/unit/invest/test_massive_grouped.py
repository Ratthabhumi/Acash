"""Grouped Daily, quota ledgers and the Massive Basic midnight boundary (no live calls)."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import provider_quota as quota
from acash.market_data import collector as co

SESSION_MS = int(datetime(2026, 11, 4, 14, 30, tzinfo=timezone.utc).timestamp() * 1000)


def _grouped(rows: List[Dict[str, Any]], adjusted: Any = False) -> Dict[str, Any]:
    return {"queryCount": len(rows), "resultsCount": len(rows), "adjusted": adjusted, "results": rows}


def _row(symbol: str, close: str = "100", stamp: int = SESSION_MS) -> Dict[str, Any]:
    return {"T": symbol, "o": close, "h": "101", "l": "99", "c": close, "v": 10, "t": stamp}


def test_grouped_daily_filters_to_held_symbols_and_rejects_adjusted() -> None:
    from acash.market_data import providers as mp
    transport = mp.urllib_transport  # never used: the fake replaces it below
    class Fake:
        def __call__(self, request: mp.HttpRequest) -> Any:
            body = _grouped([_row("VOO"), _row("NOTHELD"), _row("HOOD", "87.26")])
            return 200, json.dumps(body).encode()
    provider = mp.MassiveEODMarketDataProvider(("k", "secret"), Fake(), lambda: True,
                                               lambda: datetime(2026, 11, 5, 6, 0, tzinfo=timezone.utc))
    bars = provider.grouped_daily(date(2026, 11, 4), ["VOO", "HOOD"])
    assert {b["symbol"] for b in bars} == {"VOO", "HOOD"}
    assert all(b["session_date"] == date(2026, 11, 4) and b["adjusted"] is False for b in bars)


def test_grouped_daily_rejects_conflicting_duplicates_and_wrong_session() -> None:
    from acash.market_data import providers as mp

    def fake(body: Dict[str, Any]) -> Any:
        class Fake:
            def __call__(self, request: mp.HttpRequest) -> Any:
                return 200, json.dumps(body).encode()
        return Fake()

    def provider(body: Dict[str, Any]) -> Any:
        return mp.MassiveEODMarketDataProvider(
            ("k", "secret"), fake(body), lambda: True,
            lambda: datetime(2026, 11, 5, 6, 0, tzinfo=timezone.utc))

    with pytest.raises(DataContractError, match="grouped duplicate"):
        provider(_grouped([_row("VOO", "100"), _row("VOO", "101")])).grouped_daily(
            date(2026, 11, 4), ["VOO"])
    with pytest.raises(DataContractError, match="grouped session"):
        wrong = _grouped([_row("VOO", stamp=SESSION_MS - 86_400_000)])
        provider(wrong).grouped_daily(date(2026, 11, 4), ["VOO"])
    with pytest.raises(DataContractError, match="grouped adjusted"):
        provider(_grouped([_row("VOO")], adjusted="false")).grouped_daily(date(2026, 11, 4), ["VOO"])


def test_missing_symbol_is_absent_not_zero() -> None:
    from acash.market_data import providers as mp
    class Fake:
        def __call__(self, request: mp.HttpRequest) -> Any:
            return 200, json.dumps(_grouped([_row("VOO")])).encode()
    bars = mp.MassiveEODMarketDataProvider(("k", "secret"), Fake(), lambda: True,
                                           lambda: datetime(2026, 11, 5, 6, 0, tzinfo=timezone.utc)).grouped_daily(
        date(2026, 11, 4), ["VOO", "HOOD"])
    assert [b["symbol"] for b in bars] == ["VOO"]


def test_basic_boundary_never_requests_the_current_et_day() -> None:
    before = co.latest_completed_session(datetime(2026, 11, 6, 4, 0, tzinfo=timezone.utc))
    assert before["session_date"] == "2026-11-04"  # 23:00 ET on 05 -> not yet midnight ET
    after = co.latest_completed_session(datetime(2026, 11, 6, 6, 0, tzinfo=timezone.utc))
    assert after["session_date"] == "2026-11-05" and after["rule"] == "SESSION_STRICTLY_BEFORE_CURRENT_ET_DATE"
    weekend = co.latest_completed_session(datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc))
    assert weekend["session_date"] == "2026-11-06"


def test_schedule_is_tuesday_to_saturday_0100_et() -> None:
    run = co.next_run(datetime(2026, 11, 6, 5, 0, tzinfo=timezone.utc))  # Friday 00:00 ET
    assert run["next_run_et"] == "2026-11-06T01:00:00-05:00"
    assert run["next_run_ict"].startswith("2026-11-06T13:00:00")
    saturday_after = co.next_run(datetime(2026, 11, 7, 7, 0, tzinfo=timezone.utc))  # Saturday 02:00 ET
    assert saturday_after["session_date"] == "2026-11-10"  # Sun/Mon have no 01:00 run under Tue..Sat


def test_quota_ledger_reserves_and_refuses() -> None:
    ledger = quota.QuotaLedger(path=Path("/tmp/acash-quota-test.json"), clock=lambda: datetime(2026, 11, 5, tzinfo=timezone.utc))
    ledger.path.unlink(missing_ok=True)
    assert ledger.reserve("ALPHA_VANTAGE_FREE", 1)["remaining"] == 2
    assert ledger.reserve("ALPHA_VANTAGE_FREE", 1)["remaining"] == 1
    assert ledger.reserve("ALPHA_VANTAGE_FREE", 1)["remaining"] == 0
    with pytest.raises(DataContractError, match="QUOTA_EXHAUSTED"):
        ledger.reserve("ALPHA_VANTAGE_FREE", 1)
    with pytest.raises(DataContractError, match="QUOTA_PROVIDER_UNKNOWN"):
        ledger.reserve("NOT_A_PROVIDER", 1)
    ledger.path.unlink(missing_ok=True)


def test_secondary_providers_are_known_but_not_adapted() -> None:
    from acash.invest import market_authority as ma
    assert "TWELVE_DATA_BASIC" in ma.KNOWN_PROVIDERS and "ALPHA_VANTAGE_FREE" in ma.KNOWN_PROVIDERS
    assert "TWELVE_DATA_BASIC" not in ma.ADAPTED_PROVIDERS
    assert "ALPHA_VANTAGE_FREE" not in ma.ADAPTED_PROVIDERS
    assert ma.REGISTRY["TWELVE_DATA_BASIC"]["contract_verified"] is False
    assert ma.REGISTRY["ALPHA_VANTAGE_FREE"]["rate_limit"].startswith("25 requests/day")
