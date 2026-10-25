"""V29-F05: D6 never borrows; uneconomic orders are skipped and audited; cash reconciles."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from acash.research.d6.accounting import (
    D6_REGISTERED_PORTFOLIOS,
    D6_TIMING_OPEN_SENSITIVITY,
    D6CostModel,
    D6Result,
    run_d6_portfolio,
)

D = Decimal
S = (date(2024, 12, 30), date(2024, 12, 31), date(2025, 1, 2), date(2025, 1, 3))
P = {p.name: p for p in D6_REGISTERED_PORTFOLIOS}


def _flat(price: str, overrides: dict[date, str] | None = None) -> dict[date, Decimal]:
    series = {s: D(price) for s in S}
    for day, value in (overrides or {}).items():
        series[day] = D(value)
    return series


def _independent_cash(result: D6Result, initial: Decimal = D("1000.00")) -> Decimal:
    cash = initial
    for t in result.trades:
        if t.side == "BUY":
            cash -= t.notional + t.commission
        else:
            cash += t.notional - t.commission - t.regulatory_fees
    for e in result.entitlements:
        if e.payable_date <= result.nav_curve[-1].session:
            cash += e.gross - e.withheld
    return cash


def _assert_invariants(result: D6Result) -> None:
    assert all(r.cash >= 0 for r in result.nav_curve)
    assert result.ending_cash == _independent_cash(result)
    for r in result.nav_curve:
        assert r.nav == r.cash + r.market_value + r.receivable


def _sixty_forty(cost: D6CostModel, voo_jan: str, timing: str = D6_TIMING_OPEN_SENSITIVITY) -> D6Result:
    voo = _flat("100", {S[1]: voo_jan, S[2]: voo_jan, S[3]: voo_jan})
    return run_d6_portfolio(
        P["VOO_BND_60_40"], sessions=S, opens={"VOO": voo, "BND": _flat("50")},
        closes={"VOO": voo, "BND": _flat("50")}, dividends={}, cost=cost, execution_timing=timing,
    )


def test_minimum_commission_exceeding_sale_proceeds_never_creates_negative_cash() -> None:
    cost = D6CostModel("MIN5", commission_minimum=D("5.00"))
    result = _sixty_forty(cost, "100.2")
    _assert_invariants(result)
    skipped = [o for o in result.skipped_orders if o.session == S[2]]
    assert skipped and all(o.reason == "UNECONOMIC_SELL_SKIPPED" for o in skipped if o.side == "SELL")


@pytest.mark.parametrize(
    "cost",
    [
        D6CostModel("MIN5_FEES", commission_minimum=D("5.00"), regulatory_fees=True),
        D6CostModel("SLIP_5000", slippage_bps=D("5000"), commission_minimum=D("1.00")),
        D6CostModel("PER_SHARE_HEAVY", commission_per_share=D("50"), commission_minimum=D("1.00")),
    ],
    ids=["min_commission_and_fees", "extreme_slippage", "heavy_per_share"],
)
@pytest.mark.parametrize("voo_jan", ["100.2", "125", "60"], ids=["tiny_drift", "gap_up", "gap_down"])
def test_cost_grid_reconciles_without_borrowing(cost: D6CostModel, voo_jan: str) -> None:
    for timing in (D6_TIMING_OPEN_SENSITIVITY, "PRIOR_CLOSE_DECISION_NEXT_OPEN"):
        _assert_invariants(_sixty_forty(cost, voo_jan, timing))


def test_unaffordable_buy_is_skipped_and_audited() -> None:
    cost = D6CostModel("MIN2000", commission_minimum=D("2000"))
    px = {"BIL": _flat("100")}
    result = run_d6_portfolio(
        P["BIL_100"], sessions=S, opens=px, closes=px, dividends={}, cost=cost,
        execution_timing=D6_TIMING_OPEN_SENSITIVITY,
    )
    _assert_invariants(result)
    assert result.trades == [] and result.terminal_nav == D("1000.00")
    assert {o.reason for o in result.skipped_orders} == {"INSUFFICIENT_CASH_SKIPPED"}
