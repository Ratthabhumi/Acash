"""Alpaca JSON -> LOCAL_EXPLORATORY rows (offline)."""

from __future__ import annotations

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.local_alpaca import bar_rows, corporate_action_rows


def _bar(t: str, o: float = 100.5, c: float = 101.25) -> dict[str, object]:
    return {"t": t, "o": o, "h": 102, "l": 99, "c": c, "v": 1}


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


def test_corporate_actions_map_dividends_and_splits() -> None:
    page = {
        "corporate_actions": {
            "cash_dividends": [
                {"symbol": "VOO", "ex_date": "2024-03-22", "payable_date": "2024-03-27", "rate": 1.5429},
                {"symbol": "VOO", "ex_date": "2024-12-23", "payable_date": "2024-12-26", "rate": 0.2, "special": True},
            ],
            "forward_splits": [{"symbol": "BND", "ex_date": "2024-05-01", "new_rate": 2, "old_rate": 1}],
            "reverse_splits": [],
        }
    }
    dists, splits = corporate_action_rows([page], ["VOO", "BND"])
    assert dists[0] == {
        "symbol": "VOO",
        "ex_date": "2024-03-22",
        "payable_date": "2024-03-27",
        "gross_amount": "1.5429",
        "distribution_type": "DIVIDEND_CASH",
        "payable_date_source": "PROVIDER",
    }
    assert dists[1]["distribution_type"] == "SPECIAL_CASH"
    assert splits == [{"symbol": "BND", "session": "2024-05-01", "ratio": "2"}]


def test_same_day_distinct_events_kept_and_tagged_identical_ids_rejected() -> None:
    a = {"symbol": "BND", "ex_date": "2020-12-23", "payable_date": "2020-12-29", "rate": 0.147, "id": "3b63faa9-x"}
    b = {"symbol": "BND", "ex_date": "2020-12-23", "payable_date": "2020-12-29", "rate": 0.1436, "id": "eb13dcb4-y"}
    dists, _ = corporate_action_rows([{"corporate_actions": {"cash_dividends": [b, a]}}], ["BND"])
    assert [d["distribution_type"] for d in dists] == ["DIVIDEND_CASH:3b63faa9", "DIVIDEND_CASH:eb13dcb4"]
    with pytest.raises(DataContractError, match="ALPACA_DUPLICATE_EVENT_WITHOUT_DISTINCT_ID"):
        corporate_action_rows([{"corporate_actions": {"cash_dividends": [a, dict(b, id=a["id"])]}}], ["BND"])


def test_missing_payable_imputed_only_on_request_with_max_observed_lag() -> None:
    divs = [
        {"symbol": "BIL", "ex_date": "2017-03-01", "rate": 0.01},
        {"symbol": "BIL", "ex_date": "2024-03-01", "payable_date": "2024-03-06", "rate": 0.4},
        {"symbol": "BIL", "ex_date": "2024-04-01", "payable_date": "2024-04-08", "rate": 0.4},
    ]
    page = {"corporate_actions": {"cash_dividends": divs}}
    with pytest.raises(DataContractError, match="ALPACA_FIELD_MISSING"):
        corporate_action_rows([page], ["BIL"])
    dists, _ = corporate_action_rows([page], ["BIL"], impute_missing_payable=True)
    assert dists[0]["payable_date"] == "2017-03-08"
    assert dists[0]["payable_date_source"] == "IMPUTED_EX_PLUS_7D"
    assert [d["payable_date_source"] for d in dists[1:]] == ["PROVIDER", "PROVIDER"]
    lone = {"corporate_actions": {"cash_dividends": divs[:1]}}
    with pytest.raises(DataContractError, match="ALPACA_NO_OBSERVED_PAYABLE_LAG"):
        corporate_action_rows([lone], ["BIL"], impute_missing_payable=True)


@pytest.mark.parametrize(
    "actions, code",
    [
        ({"cash_dividends": [{"symbol": "VOO", "ex_date": "2024-03-22", "rate": 1}]}, "ALPACA_FIELD_MISSING"),
        (
            {"cash_dividends": [{"symbol": "VOO", "ex_date": "2024-03-22", "payable_date": "2024-03-27",
                                 "rate": 1, "foreign": True}]},
            "ALPACA_FOREIGN_DIVIDEND_UNSUPPORTED",
        ),
        ({"spin_offs": [{"symbol": "VOO"}]}, "ALPACA_UNSUPPORTED_ACTION_TYPES"),
        ({"forward_splits": [{"symbol": "VOO", "ex_date": "2024-05-01", "new_rate": 0, "old_rate": 1}]},
         "ALPACA_BAD_SPLIT_RATE"),
    ],
)
def test_bad_corporate_actions_fail_closed(actions: dict[str, object], code: str) -> None:
    with pytest.raises(DataContractError, match=code):
        corporate_action_rows([{"corporate_actions": actions}], ["VOO"])
