"""V28: D6 distribution identity (F03), causal prior-close sizing (P4), FX overlay."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.corporate_action_ledger import parse_distribution_rows
from acash.data.contracts.etf_fx_benchmark import EtfDistributionRecord, FxFixingRecord
from acash.research.d6.accounting import (
    D6_REGISTERED_PORTFOLIOS,
    D6_TIMING_OPEN_SENSITIVITY,
    D6_TIMING_PRIMARY,
    D6CostModel,
    d6_nav_in_currency,
    run_d6_portfolio,
)
from acash.research.hyp_009.accounting import DividendEvent

D = Decimal
S = (date(2024, 12, 30), date(2024, 12, 31), date(2025, 1, 2), date(2025, 1, 3))
FREE = D6CostModel("ZERO_COST_UPPER_BOUND")
P = {p.name: p for p in D6_REGISTERED_PORTFOLIOS}
AFTER_END = date(2025, 1, 10)


def _flat(price: str, overrides: dict[date, str] | None = None) -> dict[date, Decimal]:
    series = {s: D(price) for s in S}
    for day, value in (overrides or {}).items():
        series[day] = D(value)
    return series


def _rec(kind: str, amount: str, payable: date, event_id: str | None = None) -> EtfDistributionRecord:
    return EtfDistributionRecord(
        symbol="BIL", ex_date=S[1], payable_date=payable, gross_amount=D(amount),
        distribution_type=kind, event_id=event_id,
    )


def _bil(dividends: dict[str, list], timing: str = D6_TIMING_OPEN_SENSITIVITY):  # type: ignore[type-arg, no-untyped-def]
    px = {"BIL": _flat("100")}
    return run_d6_portfolio(
        P["BIL_100"], sessions=S, opens=px, closes=px, dividends=dividends, cost=FREE,
        execution_timing=timing,
    )


# --- F03: same-ex-date distribution identity -------------------------------------------


def test_income_and_capital_gain_on_same_ex_date_are_both_booked_and_settled_separately() -> None:
    result = _bil({"BIL": [_rec("DIVIDEND_CASH", "0.40", S[3]), _rec("CAPITAL_GAIN_LONG", "1.00", AFTER_END)]})
    assert [(e.distribution_type, e.gross) for e in result.entitlements] == [
        ("DIVIDEND_CASH", D("4.00")), ("CAPITAL_GAIN_LONG", D("10.00")),
    ]
    assert result.dividends_gross == D("14.00")
    assert result.nav_curve[1].receivable == D("14.00")
    assert (result.ending_cash, result.terminal_receivable, result.terminal_nav) == (
        D("4.00"), D("10.00"), D("1014.00"),
    )


def test_legacy_dividend_events_on_same_ex_date_are_not_overwritten() -> None:
    events = [DividendEvent(S[1], S[3], D("0.40")), DividendEvent(S[1], AFTER_END, D("1.00"))]
    assert _bil({"BIL": events}).dividends_gross == D("14.00")


@pytest.mark.parametrize(
    ("events", "code"),
    [
        ([_rec("DIVIDEND_CASH", "0.40", S[3]), _rec("DIVIDEND_CASH", "0.40", S[3])], "D6_DUPLICATE_DISTRIBUTION"),
        ([DividendEvent(S[1], S[3], D("0.40"))] * 2, "D6_DUPLICATE_DISTRIBUTION"),
        ([_rec("DIVIDEND_CASH", "0.40", S[3], "E1"), _rec("DIVIDEND_CASH", "0.41", S[3], "E1")], "D6_REVISED_EVENT"),
    ],
    ids=["duplicate_record", "duplicate_legacy", "revised_provider_event"],
)
def test_duplicates_and_revisions_fail_closed(events: list, code: str) -> None:  # type: ignore[type-arg]
    with pytest.raises(DataContractError, match=code):
        _bil({"BIL": events})


def test_net_or_foreign_symbol_records_fail_closed() -> None:
    net = EtfDistributionRecord(
        symbol="BIL", ex_date=S[1], payable_date=S[3], gross_amount=D("0.40"),
        net_amount=D("0.34"), withholding_rate=D("0.15"),
    )
    with pytest.raises(DataContractError, match="D6_GROSS_RECORD_REQUIRED"):
        _bil({"BIL": [net]})
    other = EtfDistributionRecord(symbol="BND", ex_date=S[1], payable_date=S[3], gross_amount=D("0.4"))
    with pytest.raises(DataContractError, match="D6_DISTRIBUTION_SYMBOL_MISMATCH"):
        _bil({"BIL": [other]})


def test_ledger_records_flow_into_d6_without_losing_type_or_identity() -> None:
    rows = [
        {"ex_date": "2024-12-31", "payable_date": "2025-01-03", "gross_amount": "0.40"},
        {"ex_date": "2024-12-31", "payable_date": "2025-01-03", "gross_amount": "0.40",
         "distribution_type": "CAPITAL_GAIN_SHORT"},
    ]
    records = parse_distribution_rows(rows, symbol="BIL", source_ref="SYNTHETIC")
    result = _bil({"BIL": records})
    assert [e.distribution_type for e in result.entitlements] == ["DIVIDEND_CASH", "CAPITAL_GAIN_SHORT"]
    assert {e.identity[3] for e in result.entitlements} == {"SYNTHETIC#0", "SYNTHETIC#1"}
    assert result.ending_cash == D("8.00")


# --- P4: causal prior-close decision, next-open execution ------------------------------


def test_first_session_stays_cash_and_ex_date_on_execution_session_is_not_entitled() -> None:
    result = _bil({"BIL": [DividendEvent(S[1], S[3], D("0.40"))]}, timing=D6_TIMING_PRIMARY)
    assert result.nav_curve[0].cash == D("1000.00") and result.nav_curve[0].market_value == D("0")
    assert [(t.session, t.side, t.quantity) for t in result.trades] == [(S[1], "BUY", D("10.000000"))]
    assert result.entitlements == []


@pytest.mark.parametrize(
    ("open_s1", "filled", "cash"),
    [("125", D("8.000000"), D("0.000000")), ("90", D("10.000000"), D("100.000000"))],
    ids=["gap_up_partial", "gap_down_full"],
)
def test_order_quantity_frozen_at_prior_close_regardless_of_open(open_s1: str, filled: Decimal, cash: Decimal) -> None:
    result = run_d6_portfolio(
        P["VOO_100"], sessions=S, opens={"VOO": _flat("100", {S[1]: open_s1})},
        closes={"VOO": _flat("100")}, dividends={}, cost=FREE,
    )
    buy = result.trades[0]
    assert (buy.session, buy.ordered_quantity, buy.quantity) == (S[1], D("10.000000"), filled)
    assert result.nav_curve[1].cash == cash


def test_split_between_decision_and_execution_rescales_frozen_order() -> None:
    prices = _flat("100", {S[1]: "50", S[2]: "50", S[3]: "50"})
    result = run_d6_portfolio(
        P["VOO_100"], sessions=S, opens={"VOO": prices}, closes={"VOO": prices}, dividends={},
        splits={"VOO": {S[1]: D("2")}}, cost=FREE,
    )
    assert result.holdings["VOO"] == D("20.000000") and result.ending_cash == D("0")


def test_annual_rebalance_sized_on_december_close_executed_at_january_open() -> None:
    voo = {S[0]: "100", S[1]: "100", S[2]: "130", S[3]: "130"}
    closes = {"VOO": _flat("100", {S[1]: "125", S[2]: "130", S[3]: "130"}), "BND": _flat("50")}
    opens = {"VOO": {s: D(v) for s, v in voo.items()}, "BND": _flat("50")}
    result = run_d6_portfolio(
        P["VOO_BND_60_40"], sessions=S, opens=opens, closes=closes, dividends={}, cost=FREE,
    )
    jan = [(t.side, t.symbol, t.quantity, t.notional) for t in result.trades if t.session == S[2]]
    assert jan == [("SELL", "VOO", D("0.48"), D("62.40")), ("BUY", "BND", D("1.2"), D("60.0"))]
    assert result.holdings == {"BND": D("9.2"), "VOO": D("5.52")}
    assert result.ending_cash == D("2.40")


def test_single_session_and_missing_prior_close_fail_or_hold_cash() -> None:
    one = run_d6_portfolio(
        P["VOO_100"], sessions=S[:1], opens={"VOO": _flat("100")}, closes={"VOO": _flat("100")},
        dividends={}, cost=FREE,
    )
    assert one.trades == [] and one.terminal_nav == D("1000.00")
    closes = _flat("100")
    del closes[S[0]]
    with pytest.raises(DataContractError, match="D6_MISSING_CLOSE_PRICE"):
        run_d6_portfolio(
            P["VOO_100"], sessions=S, opens={"VOO": _flat("100")}, closes={"VOO": closes},
            dividends={}, cost=FREE,
        )
    with pytest.raises(DataContractError, match="D6_UNKNOWN_EXECUTION_TIMING"):
        run_d6_portfolio(
            P["VOO_100"], sessions=S, opens={"VOO": _flat("100")}, closes={"VOO": _flat("100")},
            dividends={}, cost=FREE, execution_timing="CLOSE",
        )


def test_whole_share_primary_keeps_residual_cash_without_borrowing() -> None:
    cost = D6CostModel("SLIP10_MIN1", slippage_bps=D("10"), commission_minimum=D("1.00"))
    result = run_d6_portfolio(
        P["VOO_100"], sessions=S, opens={"VOO": _flat("400", {S[1]: "450"})},
        closes={"VOO": _flat("400")}, dividends={}, cost=cost, whole_shares=True,
    )
    buy = result.trades[0]
    assert (buy.ordered_quantity, buy.quantity) == (D("2"), D("2"))
    assert result.ending_cash == D("1000.00") - D("450.45") * 2 - D("1.00")
    assert result.ending_cash >= 0


# --- P8: FX reporting overlay (synthetic fixings only) ----------------------------------


def test_fx_overlay_converts_at_exact_date_and_fails_on_missing_fixing() -> None:
    cash = run_d6_portfolio(P["CASH_NO_TRADE"], sessions=S, opens={}, closes={}, dividends={}, cost=FREE)
    fixings = {s: FxFixingRecord(base_currency="USD", quote_currency="THB", fixing_date=s, rate=D("36.5")) for s in S}
    assert {v for _, v in d6_nav_in_currency(cash.nav_curve, fixings, currency="THB")} == {D("36500.0000")}
    del fixings[S[2]]
    with pytest.raises(DataContractError, match="MISSING_FX_FIXING"):
        d6_nav_in_currency(cash.nav_curve, fixings, currency="THB")
