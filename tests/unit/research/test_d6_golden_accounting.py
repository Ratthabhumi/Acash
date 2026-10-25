"""D6 golden accounting tests (synthetic prices; hand-derived expected values)."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_CEILING, Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import (
    D6_LABEL,
    D6_REGISTERED_PORTFOLIOS,
    D6CostModel,
    D6Portfolio,
    first_sessions_of_year,
    run_d6_portfolio,
)
from acash.research.hyp_009.accounting import DividendEvent

D = Decimal
S = (date(2024, 12, 30), date(2024, 12, 31), date(2025, 1, 2), date(2025, 1, 3))
FREE = D6CostModel("ZERO_COST_UPPER_BOUND")
PORTFOLIOS = {p.name: p for p in D6_REGISTERED_PORTFOLIOS}


def _flat(price: str, overrides: dict[date, str] | None = None) -> dict[date, Decimal]:
    series = {s: D(price) for s in S}
    for day, value in (overrides or {}).items():
        series[day] = D(value)
    return series


def _prices(**symbols: dict[date, Decimal]) -> dict[str, dict[date, Decimal]]:
    return dict(symbols)


def _cent_up(value: Decimal) -> Decimal:
    return value.quantize(D("0.01"), rounding=ROUND_CEILING)


def test_registered_comparators_are_exactly_the_five() -> None:
    assert [p.name for p in D6_REGISTERED_PORTFOLIOS] == [
        "CASH_NO_TRADE", "BIL_100", "VOO_100", "VOO_BND_60_40", "VOO_BND_GLD_BIL_50_30_10_10",
    ]
    assert sum(PORTFOLIOS["VOO_BND_GLD_BIL_50_30_10_10"].weights.values()) == D("1")


def test_cash_no_trade_is_constant() -> None:
    result = run_d6_portfolio(
        PORTFOLIOS["CASH_NO_TRADE"], sessions=S, opens={}, closes={}, dividends={}, cost=FREE
    )
    assert result.label == D6_LABEL
    assert [r.nav for r in result.nav_curve] == [D("1000.00")] * 4
    assert result.trades == []


def test_bil_dividend_receivable_is_not_spendable_until_payable() -> None:
    closes = _flat("100", {S[0]: "100.5"})
    divs = {"BIL": [DividendEvent(S[1], S[3], D("0.40"))]}
    result = run_d6_portfolio(
        PORTFOLIOS["BIL_100"], sessions=S, opens={"BIL": _flat("100")},
        closes={"BIL": closes}, dividends=divs, cost=FREE,
    )
    assert result.holdings["BIL"] == D("10")
    navs = [(r.cash, r.receivable, r.nav) for r in result.nav_curve]
    assert navs[0] == (D("0"), D("0"), D("1005.0"))
    assert navs[1] == (D("0"), D("4.00"), D("1004.00"))
    assert navs[2] == (D("0"), D("4.00"), D("1004.00"))
    assert navs[3] == (D("4.00"), D("0"), D("1004.00"))
    assert [t.session for t in result.trades] == [S[0]]


def test_withholding_scenario_and_payment_after_end() -> None:
    divs = {"BIL": [DividendEvent(S[1], date(2025, 1, 10), D("0.40"))]}
    cost = D6CostModel("WITHHOLDING_15PCT_SCENARIO", withholding_rate=D("0.15"))
    result = run_d6_portfolio(
        PORTFOLIOS["BIL_100"], sessions=S, opens={"BIL": _flat("100")},
        closes={"BIL": _flat("100")}, dividends=divs, cost=cost,
    )
    assert result.dividends_gross == D("4.00") and result.withholding == D("0.6000")
    assert result.ending_cash == D("0")
    assert result.terminal_receivable == D("3.4000")
    assert result.terminal_nav == D("1003.4000")


@pytest.mark.parametrize(
    ("whole", "expected_qty"),
    [(True, D("2")), (False, D("2.495004"))],
    ids=["whole_shares", "fractional"],
)
def test_voo_slippage_minimum_commission_and_residual_cash(whole: bool, expected_qty: Decimal) -> None:
    cost = D6CostModel("SLIP10_MIN1", slippage_bps=D("10"), commission_minimum=D("1.00"))
    result = run_d6_portfolio(
        PORTFOLIOS["VOO_100"], sessions=S, opens={"VOO": _flat("400")},
        closes={"VOO": _flat("400")}, dividends={}, cost=cost, whole_shares=whole,
    )
    fill = D("400") * (D("1") + D("10") / D("10000"))
    assert fill == D("400.4")
    assert result.holdings["VOO"] == expected_qty
    assert result.ending_cash == D("1000.00") - fill * expected_qty - D("1.00")
    assert result.commissions == D("1.00")
    assert result.terminal_nav == result.ending_cash + expected_qty * D("400")


def test_sixty_forty_annual_rebalance_with_historical_fees() -> None:
    opens = _prices(VOO=_flat("100", {S[1]: "120", S[2]: "125", S[3]: "125"}), BND=_flat("50"))
    closes = _prices(VOO=_flat("100", {S[1]: "120", S[2]: "125", S[3]: "125"}), BND=_flat("50"))
    cost = D6CostModel("STATUTORY_FEES_ONLY", regulatory_fees=True)
    result = run_d6_portfolio(
        PORTFOLIOS["VOO_BND_60_40"], sessions=S, opens=opens, closes=closes, dividends={}, cost=cost,
    )
    assert first_sessions_of_year(S) == (S[0], S[2])
    sell = next(t for t in result.trades if t.side == "SELL")
    assert (sell.session, sell.symbol, sell.quantity, sell.notional) == (S[2], "VOO", D("0.48"), D("60.00"))
    sec31 = _cent_up(D("60.00") * D("0.0000278"))
    taf = _cent_up(D("0.48") * D("0.000166"))
    assert sell.regulatory_fees == sec31 + taf == D("0.02")
    assert result.holdings == {"BND": D("9.199600"), "VOO": D("5.52")}
    assert result.ending_cash == D("0")
    assert result.nav_curve[2].nav == D("1149.98") == D("1150") - sec31 - taf


def test_diversified_buys_fractional_targets_and_conserves_nav() -> None:
    opens = _prices(VOO=_flat("100"), BND=_flat("50"), GLD=_flat("200"), BIL=_flat("100"))
    result = run_d6_portfolio(
        PORTFOLIOS["VOO_BND_GLD_BIL_50_30_10_10"], sessions=S, opens=opens, closes=opens,
        dividends={}, cost=FREE,
    )
    assert result.holdings == {"BIL": D("1"), "BND": D("6"), "GLD": D("0.5"), "VOO": D("5")}
    assert all(r.nav == D("1000") for r in result.nav_curve)


def test_gld_cash_distribution_is_rejected() -> None:
    opens = _prices(VOO=_flat("100"), BND=_flat("50"), GLD=_flat("200"), BIL=_flat("100"))
    with pytest.raises(DataContractError, match="D6_NO_CASH_DISTRIBUTION_ENTITLEMENT"):
        run_d6_portfolio(
            PORTFOLIOS["VOO_BND_GLD_BIL_50_30_10_10"], sessions=S, opens=opens, closes=opens,
            dividends={"GLD": [DividendEvent(S[1], S[2], D("0.10"))]}, cost=FREE,
        )


def test_split_keeps_nav_continuous_and_whole_share_cash_in_lieu_fails_closed() -> None:
    prices = _flat("100", {S[1]: "50", S[2]: "50", S[3]: "50"})
    result = run_d6_portfolio(
        PORTFOLIOS["VOO_100"], sessions=S, opens={"VOO": prices}, closes={"VOO": prices},
        dividends={}, splits={"VOO": {S[1]: D("2")}}, cost=FREE,
    )
    assert result.holdings["VOO"] == D("20")
    assert [r.nav for r in result.nav_curve] == [D("1000")] * 4
    odd = _flat("300", {S[1]: "200", S[2]: "200", S[3]: "200"})
    with pytest.raises(DataContractError, match="D6_SPLIT_CASH_IN_LIEU_UNSUPPORTED"):
        run_d6_portfolio(
            PORTFOLIOS["VOO_100"], sessions=S, opens={"VOO": odd}, closes={"VOO": odd},
            dividends={}, splits={"VOO": {S[1]: D("1.5")}}, cost=FREE, whole_shares=True,
        )


def test_adjusted_prices_with_explicit_distributions_are_rejected() -> None:
    with pytest.raises(DataContractError, match="D6_ADJUSTED_PRICES_REJECTED"):
        run_d6_portfolio(
            PORTFOLIOS["BIL_100"], sessions=S, opens={"BIL": _flat("100")},
            closes={"BIL": _flat("100")}, dividends={}, cost=FREE, price_adjustment="all",
        )


def test_rebalance_uses_open_not_same_session_close() -> None:
    def run(close_on_rebalance: str) -> list[tuple[str, Decimal]]:
        closes = _prices(VOO=_flat("100", {S[2]: close_on_rebalance}), BND=_flat("50"))
        opens = _prices(VOO=_flat("100", {S[2]: "110"}), BND=_flat("50"))
        result = run_d6_portfolio(
            PORTFOLIOS["VOO_BND_60_40"], sessions=S, opens=opens, closes=closes, dividends={}, cost=FREE,
        )
        return [(t.symbol, t.quantity) for t in result.trades if t.session == S[2]]

    assert run("110") == run("500") == run("1")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sessions": (S[1], S[0])},
        {"sessions": ()},
        {"dividends": {"BIL": [DividendEvent(S[2], S[1], D("0.1"))]}},
        {"dividends": {"BIL": [DividendEvent(S[1], S[2], D("-0.1"))]}},
    ],
    ids=["unordered", "empty", "payable_before_ex", "negative_amount"],
)
def test_malformed_inputs_fail_closed(kwargs: dict[str, object]) -> None:
    args: dict[str, object] = {
        "sessions": S, "opens": {"BIL": _flat("100")}, "closes": {"BIL": _flat("100")},
        "dividends": {}, "cost": FREE,
    }
    args.update(kwargs)
    with pytest.raises(DataContractError):
        run_d6_portfolio(PORTFOLIOS["BIL_100"], **args)  # type: ignore[arg-type]


def test_bad_portfolio_and_cost_definitions_fail_closed() -> None:
    with pytest.raises(DataContractError):
        D6Portfolio("OVER", {"VOO": D("0.7"), "BND": D("0.4")})
    with pytest.raises(DataContractError):
        D6CostModel("BAD", slippage_bps=D("-1"))
    with pytest.raises(DataContractError):
        D6CostModel("BAD", withholding_rate=D("1"))
