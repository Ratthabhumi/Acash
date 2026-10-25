"""V35 contribution accounting, IBKR cost adapter and flow-aware metrics (synthetic)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import (
    D6_REGISTERED_PORTFOLIOS,
    D6_TIMING_OPEN_SENSITIVITY,
    D6CostModel,
    D6Result,
    run_d6_portfolio,
)
from acash.research.d6.contributions import (
    cash_drag,
    h10_rate,
    investor_flows,
    monthly_contribution_schedule,
    parse_h10_rates,
    reconcile_cash,
    thb_view,
    twr_index,
    xirr,
)
from acash.research.d6.local_exploratory import compute_metrics, official_sessions
from acash.research.hyp_009.accounting import DividendEvent

D = Decimal
P = {p.name: p for p in D6_REGISTERED_PORTFOLIOS}
FREE = D6CostModel("ZERO_COST_UPPER_BOUND")
FIXED = D6CostModel(
    "IBKR_PRO_FIXED",
    commission_per_share=D("0.005"),
    commission_minimum=D("1.00"),
    commission_max_rate=D("0.01"),
    commission_floor=D("0.01"),
)
S = official_sessions(date(2023, 12, 27), date(2024, 3, 6))


def _flat(price: str, overrides: dict[date, str] | None = None) -> dict[date, Decimal]:
    series = {s: D(price) for s in S}
    for day, value in (overrides or {}).items():
        series[day] = D(value)
    return series


def _run(name: str, prices: dict[str, dict[date, Decimal]], **kw: object) -> D6Result:
    kw.setdefault("cost", FREE)
    kw.setdefault("dividends", {})
    return run_d6_portfolio(P[name], sessions=S, opens=prices, closes=prices, **kw)  # type: ignore[arg-type]


# --- IBKR cost adapter (examples from the official pricing page) -----------------


@pytest.mark.parametrize(
    ("quantity", "price", "expected"),
    [
        ("100", "25", "1.00"),  # Fixed example: minimum
        ("1000", "25", "5.00"),  # Fixed example: per share
        ("1000", "0.25", "2.50"),  # Fixed example: 1% cap
        ("10", "0.20", "0.02"),  # footnote 8: cap overrides the minimum
        ("0.5", "10", "0.05"),  # footnote 11: fractional = 1% of value
        ("0.05", "15", "0.01"),  # footnote 11: USD 0.01 floor
    ],
)
def test_ibkr_fixed_commission_matches_published_examples(quantity: str, price: str, expected: str) -> None:
    q = D(quantity)
    assert FIXED.commission(q, q * D(price)) == D(expected)


def test_tiered_clearing_and_passthrough_are_added_once() -> None:
    tiered = D6CostModel(
        "T",
        commission_per_share=D("0.0035"),
        commission_minimum=D("0.35"),
        commission_max_rate=D("0.01"),
        clearing_per_share=D("0.0002"),
        clearing_max_rate=D("0.005"),
        passthrough_rate=D("0.000735"),
    )
    base = D("0.35")
    assert tiered.commission(D("10"), D("1000")) == base + D("0.002") + base * D("0.000735")
    # 1% cap on the commission and 0.5% cap on clearing for a cheap stock
    assert tiered.commission(D("1000"), D("10")) == D("0.10") + D("0.05") + D("0.10") * D("0.000735")


def test_legacy_cost_model_is_unchanged_and_cap_requires_notional() -> None:
    legacy = D6CostModel("L", commission_per_share=D("0.005"), commission_minimum=D("1.00"))
    assert legacy.commission(D("10")) == D("1.00")
    assert legacy.commission(D("0")) == D("0")
    with pytest.raises(DataContractError, match="REQUIRES_NOTIONAL"):
        FIXED.commission(D("1"))
    with pytest.raises(DataContractError, match="NEGATIVE_COST"):
        D6CostModel("BAD", commission_max_rate=D("-0.01"))


# --- schedule ---------------------------------------------------------------------


def test_schedule_first_admitted_session_after_initial_month() -> None:
    schedule = monthly_contribution_schedule(S, D("50"))
    # 2024-01-01 is a holiday; initial month (2023-12) gets nothing; 2024-03 included.
    assert sorted(schedule) == [date(2024, 1, 2), date(2024, 2, 1), date(2024, 3, 1)]
    assert set(schedule.values()) == {D("50")}
    assert monthly_contribution_schedule(S, D("0")) == {}
    with pytest.raises(DataContractError):
        monthly_contribution_schedule(S, D("-1"))
    with pytest.raises(DataContractError):
        monthly_contribution_schedule(list(reversed(S)), D("1"))


# --- engine -----------------------------------------------------------------------


def test_c0_none_and_empty_are_identical() -> None:
    prices = {"VOO": _flat("100", {S[10]: "110"})}
    a = _run("VOO_100", prices)
    b = _run("VOO_100", prices, contributions={})
    assert a.nav_curve == b.nav_curve and a.trades == b.trades and b.contributed == D("0")


def test_contribution_credited_then_deployed_buy_only_next_open() -> None:
    day = date(2024, 2, 1)
    nxt = S[S.index(day) + 1]
    # VOO doubles before the contribution: a full rebalance would SELL, buy-only must not.
    prices = {"VOO": _flat("100"), "BND": _flat("100")}
    for s in S[S.index(date(2024, 1, 10)):]:
        prices["VOO"][s] = D("200")
    result = _run("VOO_BND_60_40", prices, contributions={day: D("100")})
    on_day = next(r for r in result.nav_curve if r.session == day)
    assert on_day.cash == D("100")  # credited at start, not traded that session
    deploy = [t for t in result.trades if t.session == nxt]
    assert {t.side for t in deploy} == {"BUY"}
    assert {t.symbol: t.quantity for t in deploy} == {"VOO": D("0.3"), "BND": D("0.4")}
    assert result.contributions == [(day, D("100"))]
    assert reconcile_cash(result, D("1000"))["ending_cash"] == result.ending_cash


def test_min_commission_exceeding_contribution_skips_and_carries_cash() -> None:
    cost = D6CostModel("MIN100", commission_minimum=D("100"))
    result = _run("VOO_100", {"VOO": _flat("100")}, cost=cost, contributions={date(2024, 2, 1): D("50")})
    reasons = {o.reason for o in result.skipped_orders}
    assert "INSUFFICIENT_CASH_SKIPPED" in reasons
    assert all(r.cash >= 0 for r in result.nav_curve)
    assert result.ending_cash >= D("50")
    reconcile_cash(result, D("1000"))


def test_whole_shares_carry_cash_until_affordable() -> None:
    sched = monthly_contribution_schedule(S, D("60"))
    result = _run("VOO_100", {"VOO": _flat("100")}, whole_shares=True, contributions=sched)
    buys = [t for t in result.trades if t.side == "BUY"]
    # initial 10 shares; 60 (Jan) cannot buy; 120 after Feb buys 1; 80 after Mar cannot buy
    assert [(t.session, t.quantity) for t in buys] == [
        (S[1], D("10")),
        (date(2024, 2, 2), D("1")),
    ]
    assert result.ending_cash == D("80")
    reconcile_cash(result, D("1000"))


def test_min_order_notional_skips_small_orders() -> None:
    cost = D6CostModel("MIN_NOTIONAL", min_order_notional=D("1.00"))
    result = _run(
        "VOO_BND_GLD_BIL_50_30_10_10",
        {s: _flat("100") for s in ("VOO", "BND", "GLD", "BIL")},
        cost=cost,
        contributions={date(2024, 2, 1): D("5")},
    )
    skipped = [o for o in result.skipped_orders if o.reason == "BELOW_MIN_NOTIONAL_SKIPPED"]
    assert {o.symbol for o in skipped} == {"GLD", "BIL"}  # 0.50 USD each
    reconcile_cash(result, D("1000"))


def test_fixed_commission_on_small_fractional_buys_is_one_percent() -> None:
    result = _run("VOO_100", {"VOO": _flat("400")}, cost=FIXED, contributions={date(2024, 2, 1): D("50")})
    buy = next(t for t in result.trades if t.session == date(2024, 2, 2))
    assert buy.commission == (buy.notional * D("0.01"))
    assert buy.notional + buy.commission <= D("50")
    reconcile_cash(result, D("1000"))


@pytest.mark.parametrize(
    ("day", "amount", "match"),
    [
        (date(2024, 1, 1), D("10"), "NOT_A_SESSION"),
        (S[0], D("10"), "INITIAL_SESSION"),
        (date(2024, 2, 1), D("0"), "NONPOSITIVE"),
        (date(2024, 2, 1), D("-5"), "NONPOSITIVE"),
    ],
)
def test_bad_contributions_fail_closed(day: date, amount: Decimal, match: str) -> None:
    with pytest.raises(DataContractError, match=match):
        _run("VOO_100", {"VOO": _flat("100")}, contributions={day: amount})


def test_contributions_reject_idealized_timing() -> None:
    with pytest.raises(DataContractError, match="PRIMARY_TIMING"):
        _run(
            "VOO_100",
            {"VOO": _flat("100")},
            contributions={date(2024, 2, 1): D("10")},
            execution_timing=D6_TIMING_OPEN_SENSITIVITY,
        )


def test_contribution_on_last_session_stays_cash() -> None:
    result = _run("VOO_100", {"VOO": _flat("100")}, contributions={S[-1]: D("75")})
    assert result.ending_cash == D("75")
    assert all(t.session != S[-1] for t in result.trades)


def test_rebalance_precedes_deployment_on_first_session_of_year() -> None:
    # Contribution on 2023-12-29 (last 2023 session) -> next session 2024-01-02 is the rebalance.
    prices = {"VOO": _flat("100"), "BND": _flat("100")}
    prices["VOO"][date(2023, 12, 29)] = D("150")
    for s in S[S.index(date(2024, 1, 2)):]:
        prices["VOO"][s] = D("150")
    result = _run("VOO_BND_60_40", prices, contributions={date(2023, 12, 29): D("100")})
    jan = [t for t in result.trades if t.session == date(2024, 1, 2)]
    assert {t.side for t in jan} == {"SELL", "BUY"}  # full rebalance, cash included
    eod = next(r for r in result.nav_curve if r.session == date(2024, 1, 2))
    assert eod.cash == D("0")


def test_receivable_not_deployed_until_paid_and_not_a_contribution() -> None:
    divs = {"BIL": [DividendEvent(date(2024, 1, 31), date(2024, 2, 5), D("1"))]}
    result = _run(
        "BIL_100", {"BIL": _flat("100")}, dividends=divs, contributions={date(2024, 2, 1): D("50")}
    )
    deploy = next(t for t in result.trades if t.session == date(2024, 2, 2))
    assert deploy.quantity == D("0.5")  # only the contribution, receivable excluded
    assert result.contributed == D("50") and result.dividends_gross == D("10")
    reconcile_cash(result, D("1000"))


def test_split_between_decision_and_deployment_scales_target() -> None:
    day = date(2024, 2, 1)
    nxt = S[S.index(day) + 1]
    prices = {"BIL": _flat("100")}
    for s in S[S.index(nxt):]:
        prices["BIL"][s] = D("200")
    result = _run(
        "BIL_100", prices, splits={"BIL": {nxt: D("0.5")}}, contributions={day: D("100")}
    )
    deploy = next(t for t in result.trades if t.session == nxt)
    assert deploy.quantity == D("0.5")
    assert result.holdings["BIL"] == D("5.5")
    reconcile_cash(result, D("1000"))


def test_compute_metrics_rejects_flow_contaminated_nav() -> None:
    result = _run("VOO_100", {"VOO": _flat("100")}, contributions={date(2024, 2, 1): D("10")})
    with pytest.raises(DataContractError, match="FLOW_CONTAMINATED"):
        compute_metrics(result, D("1000"))


# --- TWR / XIRR / cash drag ---------------------------------------------------------


def test_twr_flat_prices_ignores_contributions() -> None:
    sched = monthly_contribution_schedule(S, D("250"))
    result = _run("VOO_100", {"VOO": _flat("100")}, contributions=sched)
    index = twr_index(result, D("1000"))
    assert set(index) == {D("1000")}
    assert result.terminal_nav == D("1750")


def test_twr_equals_nav_curve_without_flows() -> None:
    prices = {"VOO": _flat("100", {S[20]: "120", S[21]: "90"})}
    result = _run("VOO_100", prices)
    assert twr_index(result, D("1000")) == [r.nav for r in result.nav_curve]


def test_twr_and_xirr_on_a_rising_market() -> None:
    prices = {"VOO": _flat("100")}
    for s in S[S.index(date(2024, 2, 20)):]:
        prices["VOO"][s] = D("110")
    result = _run("VOO_100", prices, contributions={date(2024, 2, 1): D("1000")})
    index = twr_index(result, D("1000"))
    assert index[-1] == D("1100")  # +10% regardless of the flow
    rate = xirr(investor_flows(result, D("1000")))
    assert rate > 0.10  # money-weighted, short holding period annualized


def test_xirr_golden_and_undefined() -> None:
    t0 = date(2020, 1, 1)
    assert xirr([(t0, D("-1000")), (date(2020, 12, 31), D("1100"))]) == pytest.approx(0.10, abs=1e-9)
    with pytest.raises(DataContractError, match="SIGN_PATTERN"):
        xirr([(t0, D("1000")), (date(2021, 1, 1), D("1100"))])
    with pytest.raises(DataContractError, match="SIGN_PATTERN"):
        xirr([(t0, D("-1000")), (date(2021, 1, 1), D("0"))])
    with pytest.raises(DataContractError, match="TOO_FEW"):
        xirr([(t0, D("-1"))])
    with pytest.raises(DataContractError, match="ZERO_HORIZON"):
        xirr([(t0, D("-1")), (t0, D("2"))])


def test_twr_rejects_flow_outside_curve() -> None:
    result = _run("VOO_100", {"VOO": _flat("100")}, contributions={date(2024, 2, 1): D("10")})
    result.contributions.append((date(2030, 1, 2), D("1")))
    with pytest.raises(DataContractError):
        twr_index(result, D("1000"))


def test_cash_drag_cash_portfolio_is_full_share() -> None:
    result = _run("CASH_NO_TRADE", {}, contributions={date(2024, 2, 1): D("10")})
    mean, end = cash_drag(result)
    assert mean == D("1") and end == D("1010")


def test_reconcile_detects_tampered_ledger() -> None:
    result = _run("VOO_100", {"VOO": _flat("100")}, contributions={date(2024, 2, 1): D("10")})
    result.contributions.append((date(2024, 3, 1), D("1")))
    with pytest.raises(DataContractError, match="RECONCILIATION"):
        reconcile_cash(result, D("1000"))


# --- H.10 / THB ---------------------------------------------------------------------

H10 = """
| 2-JAN-24 | 34.2000 |
| 3-JAN-24 | ND |
| 4-JAN-24 | 34.4000 |
| 2-JAN-25 | 34.0000 |
"""


def test_h10_parse_and_prior_rate_policy() -> None:
    rates = parse_h10_rates(H10)
    assert date(2024, 1, 3) not in rates
    assert h10_rate(rates, date(2024, 1, 3)) == (D("34.2000"), True)
    assert h10_rate(rates, date(2024, 1, 4)) == (D("34.4000"), False)
    with pytest.raises(DataContractError, match="NO_RATE"):
        h10_rate(rates, date(2024, 6, 3))
    with pytest.raises(DataContractError, match="DUPLICATE"):
        parse_h10_rates(H10 + "| 2-JAN-24 | 1.0 |\n")
    with pytest.raises(DataContractError, match="NO_RATES"):
        parse_h10_rates("nothing")


def test_thb_view_constant_rate_matches_usd_and_spread_hurts() -> None:
    rates = {date(2024, 1, 2): D("34"), date(2025, 1, 2): D("34")}
    flows = [(date(2024, 1, 2), D("-1000")), (date(2025, 1, 2), D("1100"))]
    flat = thb_view(flows, rates, funding_spread=D("0"), liquidation_spread=D("0"))
    assert flat["thb_xirr"] == pytest.approx(xirr(flows))
    assert flat["thb_contributed"] == D("34000")
    costly = thb_view(flows, rates, funding_spread=D("0.01"), liquidation_spread=D("0.01"))
    assert costly["thb_xirr"] < flat["thb_xirr"]  # type: ignore[operator]
    with pytest.raises(DataContractError):
        thb_view(flows, rates, funding_spread=D("-0.01"), liquidation_spread=D("0"))
