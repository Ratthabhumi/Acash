"""Alpaca JSON -> LOCAL_EXPLORATORY rows (offline)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.corporate_action_ledger import parse_distribution_rows
from acash.research.d6.local_alpaca import (
    bar_rows,
    corporate_action_rows,
    page_record,
    verify_page_bytes,
    verify_page_chain,
)

WINDOW = (date(2016, 1, 1), date(2025, 12, 31))


def _bar(t: str, o: float = 100.5, c: float = 101.25) -> dict[str, object]:
    return {"t": t, "o": o, "h": 102, "l": 99, "c": c, "v": 1}


def _div(sym: str, ex: str, rate: float, ident: str, payable: str | None = None, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"symbol": sym, "ex_date": ex, "rate": rate, "id": ident, "process_date": payable or ex}
    if payable:
        item["payable_date"] = payable
    return {**item, **extra}


def _page(**actions: Any) -> dict[str, Any]:
    return {"corporate_actions": actions, "next_page_token": None}


def test_bars_map_ny_midnight_to_session_across_dst() -> None:
    pages: list[dict[str, object]] = [
        {"bars": {"VOO": [_bar("2024-01-02T05:00:00Z")]}, "next_page_token": "x"},
        {"bars": {"VOO": [_bar("2024-07-01T04:00:00Z")], "BND": [_bar("2024-01-02T05:00:00Z", 72, 72.1)]}},
    ]
    rows = bar_rows(pages, ["VOO", "BND"])
    assert [(r["symbol"], r["session"]) for r in rows] == [
        ("BND", "2024-01-02"),
        ("VOO", "2024-01-02"),
        ("VOO", "2024-07-01"),
    ]
    assert rows[1]["open"] == "100.5" and rows[1]["close"] == "101.25" and rows[1]["adjustment"] == "raw"


@pytest.mark.parametrize(
    "page, code",
    [
        ({"bars": {"VOO": [_bar("2024-01-02T14:30:00Z")]}}, "ALPACA_DAILY_BAR_NOT_NY_MIDNIGHT"),
        ({"bars": {"SPY": [_bar("2024-01-02T05:00:00Z")]}}, "ALPACA_UNREQUESTED_SYMBOL"),
        ({"bars": {"VOO": [{"t": "2024-01-02T05:00:00Z", "o": 1}]}}, "ALPACA_FIELD_MISSING"),
        ({"bars": []}, "ALPACA_BARS_NOT_A_SYMBOL_MAP"),
    ],
)
def test_bad_bar_pages_fail_closed(page: dict[str, object], code: str) -> None:
    with pytest.raises(DataContractError, match=code):
        bar_rows([page], ["VOO"])


def test_corporate_actions_map_types_and_keep_identity_separate() -> None:
    page = _page(
        cash_dividends=[
            _div("VOO", "2024-03-22", 1.5429, "d1", "2024-03-27"),
            _div("VOO", "2024-12-23", 0.2, "d2", "2024-12-26", special=True),
            _div("VOO", "2024-06-28", 0.1, "d3", "2024-07-02", sub_type="return_of_capital"),
        ],
        forward_splits=[{"symbol": "BND", "ex_date": "2024-05-01", "new_rate": 2, "old_rate": 1, "id": "s1"}],
    )
    out = corporate_action_rows([page], ["VOO", "BND"], window=WINDOW)
    assert out.distributions[0] == {
        "symbol": "VOO",
        "ex_date": "2024-03-22",
        "payable_date": "2024-03-27",
        "gross_amount": "1.5429",
        "distribution_type": "DIVIDEND_CASH",
        "payable_date_source": "PROVIDER",
        "event_id": "d1",
        "process_date": "2024-03-27",
    }
    assert [d["distribution_type"] for d in out.distributions] == [
        "DIVIDEND_CASH",
        "RETURN_OF_CAPITAL_CASH",
        "SPECIAL_CASH",
    ]
    assert out.splits == [{"symbol": "BND", "session": "2024-05-01", "ratio": "2", "event_id": "s1"}]


def test_capital_gains_legs_are_separate_events_with_leg_identity() -> None:
    gain = {
        "symbol": "VOO", "ex_date": "2025-12-26", "payable_date": "2025-12-30", "process_date": "2025-12-30",
        "id": "g1", "cusip": "x", "long_term_rate": 0.45855, "short_term_rate": 0.11019, "currency": "USD",
    }
    page = _page(cash_dividends=[_div("VOO", "2025-12-26", 1.8, "d1", "2025-12-30")], capital_gains_distributions=[gain])
    rows = corporate_action_rows([page], ["VOO"], window=WINDOW).distributions
    assert [(r["distribution_type"], r["gross_amount"], r["event_id"]) for r in rows] == [
        ("CAPITAL_GAIN_LONG_TERM", "0.45855", "g1#long_term"),
        ("CAPITAL_GAIN_SHORT_TERM", "0.11019", "g1#short_term"),
        ("DIVIDEND_CASH", "1.8", "d1"),
    ]
    only_long = dict(gain, short_term_rate=None)
    assert len(corporate_action_rows([_page(capital_gains_distributions=[only_long])], ["VOO"], window=WINDOW)
               .distributions) == 1
    with pytest.raises(DataContractError, match="ALPACA_CAPITAL_GAIN_WITHOUT_RATE"):
        corporate_action_rows(
            [_page(capital_gains_distributions=[dict(gain, long_term_rate=None, short_term_rate=0)])],
            ["VOO"], window=WINDOW,
        )
    with pytest.raises(DataContractError, match="ALPACA_NON_USD_DISTRIBUTION"):
        corporate_action_rows([_page(capital_gains_distributions=[dict(gain, currency="CAD")])], ["VOO"], window=WINDOW)


def test_same_day_distinct_events_survive_ledger_parse_without_type_tagging() -> None:
    a = _div("BND", "2020-12-23", 0.1471819, "3b63faa9", "2020-12-29")
    b = _div("BND", "2020-12-23", 0.1436, "eb13dcb4", "2020-12-29")
    rows = corporate_action_rows([_page(cash_dividends=[b, a])], ["BND"], window=WINDOW).distributions
    assert {r["distribution_type"] for r in rows} == {"DIVIDEND_CASH"}
    records = parse_distribution_rows(rows, symbol="BND", source_ref="d.csv")
    assert sorted(r.event_id or "" for r in records) == ["3b63faa9", "eb13dcb4"]
    with pytest.raises(DataContractError, match="LEDGER_DUPLICATE_EVENT_ID"):
        parse_distribution_rows([rows[0], rows[0]], symbol="BND", source_ref="d.csv")
    without_ids = [{k: v for k, v in r.items() if k != "event_id"} for r in rows]
    with pytest.raises(DataContractError, match="LEDGER_DUPLICATE_EVENT"):
        parse_distribution_rows(without_ids, symbol="BND", source_ref="d.csv")


def test_duplicates_and_revisions() -> None:
    a = _div("BND", "2021-04-01", 0.0534, "id1", "2021-04-07")
    with pytest.raises(DataContractError, match="ALPACA_DUPLICATE_EVENT_IN_PAGE"):
        corporate_action_rows([_page(cash_dividends=[a, dict(a)])], ["BND"], window=WINDOW)
    out = corporate_action_rows([_page(cash_dividends=[a]), _page(cash_dividends=[dict(a)])], ["BND"], window=WINDOW)
    assert len(out.distributions) == 1 and out.cross_page_duplicates == 1
    with pytest.raises(DataContractError, match="ALPACA_CONFLICTING_REVISION"):
        corporate_action_rows(
            [_page(cash_dividends=[a]), _page(cash_dividends=[dict(a, rate=0.06)])], ["BND"], window=WINDOW
        )
    with pytest.raises(DataContractError, match="ALPACA_FIELD_MISSING"):
        corporate_action_rows([_page(cash_dividends=[{k: v for k, v in a.items() if k != "id"}])], ["BND"],
                              window=WINDOW)


def test_window_is_by_ex_date_and_exclusions_are_reported() -> None:
    late = _div("VOO", "2025-12-30", 1.0, "late", "2026-01-05")
    early = _div("VOO", "2015-12-31", 1.0, "early", "2016-01-05")
    out = corporate_action_rows([_page(cash_dividends=[late, early])], ["VOO"], window=WINDOW)
    assert [r["event_id"] for r in out.distributions] == ["late"]
    assert [r["event_id"] for r in out.excluded_outside_window] == ["early"]


@pytest.mark.parametrize("policy, lag", [("min", 5), ("median", 5), ("max", 7)])
def test_missing_payable_imputed_only_by_named_policy(policy: str, lag: int) -> None:
    divs = [
        _div("BIL", "2017-03-01", 0.01, "old"),
        _div("BIL", "2024-03-01", 0.4, "n1", "2024-03-06"),
        _div("BIL", "2024-04-01", 0.4, "n2", "2024-04-08"),
    ]
    with pytest.raises(DataContractError, match="ALPACA_FIELD_MISSING"):
        corporate_action_rows([_page(cash_dividends=divs)], ["BIL"], window=WINDOW)
    out = corporate_action_rows([_page(cash_dividends=divs)], ["BIL"], window=WINDOW, payable_lag_policy=policy)
    imputed = out.distributions[0]
    assert imputed["payable_date"] == date.fromordinal(date(2017, 3, 1).toordinal() + lag).isoformat()
    assert imputed["payable_date_source"] == f"IMPUTED_EX_PLUS_{lag}D_{policy.upper()}_OBSERVED_LAG"
    assert [d["payable_date_source"] for d in out.distributions[1:]] == ["PROVIDER", "PROVIDER"]
    assert out.observed_payable_lags == {"BIL": [5, 7]}
    with pytest.raises(DataContractError, match="ALPACA_NO_OBSERVED_PAYABLE_LAG"):
        corporate_action_rows([_page(cash_dividends=divs[:1])], ["BIL"], window=WINDOW, payable_lag_policy=policy)
    with pytest.raises(DataContractError, match="ALPACA_UNKNOWN_PAYABLE_LAG_POLICY"):
        corporate_action_rows([_page(cash_dividends=divs)], ["BIL"], window=WINDOW, payable_lag_policy="p90")


@pytest.mark.parametrize(
    "actions, code",
    [
        ({"cash_dividends": [_div("VOO", "2024-03-22", 1, "a", "2024-03-27", foreign=True)]},
         "ALPACA_FOREIGN_DIVIDEND_UNSUPPORTED"),
        ({"cash_dividends": [_div("VOO", "2024-03-22", 1, "a", "2024-03-27", sub_type="stock")]},
         "ALPACA_UNKNOWN_DIVIDEND_SUB_TYPE"),
        ({"cash_dividends": [_div("VOO", "2024-03-22", 1, "a", "2024-03-20")]}, "ALPACA_PAYABLE_BEFORE_EX_DATE"),
        ({"spin_offs": [{"symbol": "VOO"}]}, "ALPACA_UNSUPPORTED_ACTION_TYPES"),
        ({"forward_splits": [{"symbol": "VOO", "ex_date": "2024-05-01", "new_rate": 0, "old_rate": 1, "id": "s"}]},
         "ALPACA_BAD_SPLIT_RATE"),
    ],
)
def test_bad_corporate_actions_fail_closed(actions: dict[str, object], code: str) -> None:
    with pytest.raises(DataContractError, match=code):
        corporate_action_rows([{"corporate_actions": actions}], ["VOO"], window=WINDOW)


def _chain(*tokens: str | None) -> tuple[list[dict[str, Any]], list[bytes]]:
    payloads = [json.dumps({"bars": {}, "next_page_token": t}).encode() for t in tokens]
    records, previous = [], None
    for index, payload in enumerate(payloads, start=1):
        records.append(page_record("bars", index, previous, payload))
        previous = records[-1]["next_page_token"]
    return records, payloads


def test_page_chain_and_digest_verification() -> None:
    records, payloads = _chain("t1", "t2", None)
    verify_page_chain(records)
    assert verify_page_bytes(records[0], payloads[0])["next_page_token"] == "t1"
    with pytest.raises(DataContractError, match="RAW_PAGE_DIGEST_MISMATCH"):
        verify_page_bytes(records[0], payloads[0] + b" ")
    with pytest.raises(DataContractError, match="RAW_PAGE_CHAIN_INCOMPLETE"):
        verify_page_chain(records[:2])
    with pytest.raises(DataContractError, match="RAW_PAGE_INDEX_GAP"):
        verify_page_chain([records[0], records[2]])
    with pytest.raises(DataContractError, match="RAW_PAGE_CHAIN_BROKEN"):
        verify_page_chain([records[0], dict(records[1], request_page_token="other"), records[2]])
    looped, _ = _chain("t1", "t1", None)
    with pytest.raises(DataContractError, match="RAW_PAGE_CHAIN_BROKEN|RAW_PAGE_TOKEN_REPEATED"):
        verify_page_chain(looped)
    repeated = [dict(r) for r in _chain("t1", "t2", "t1", None)[0]]
    with pytest.raises(DataContractError, match="RAW_PAGE_TOKEN_REPEATED"):
        verify_page_chain(repeated)
