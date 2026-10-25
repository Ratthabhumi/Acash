"""V36: IBKR interpretation rows, withholding by type, Thai funding cadence, attribution."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import D6_REGISTERED_PORTFOLIOS, D6CostModel, D6Result, run_d6_portfolio
from acash.research.d6.attribution import broker_attribution, household_attribution
from acash.research.d6.contributions import reconcile_cash
from acash.research.d6.funding import FundingScenario, plan_funding
from acash.research.d6.local_exploratory import official_sessions
from acash.research.hyp_009.accounting import DividendEvent

D = Decimal
P = {p.name: p for p in D6_REGISTERED_PORTFOLIOS}
S = official_sessions(date(2023, 12, 27), date(2024, 7, 3))
RATES = {s: D("35") for s in S}
def _fixed(
    label: str,
    *,
    fractional_rate: Decimal | None = None,
    slippage_bps: Decimal = D("0"),
    regulatory_fees: bool = False,
    withholding_rate: Decimal = D("0"),
) -> D6CostModel:
    return D6CostModel(
        label,
        slippage_bps=slippage_bps,
        regulatory_fees=regulatory_fees,
        withholding_rate=withholding_rate,
        commission_per_share=D("0.005"),
        commission_minimum=D("1.00"),
        commission_max_rate=D("0.01"),
        commission_floor=D("0.01"),
        fractional_rate=fractional_rate,
    )


def _flat(price: str) -> dict[date, Decimal]:
    return {s: D(price) for s in S}


def _run(name: str, prices: dict[str, dict[date, Decimal]], **kw: object) -> D6Result:
    kw.setdefault("cost", D6CostModel("FREE"))
    kw.setdefault("dividends", {})
    return run_d6_portfolio(P[name], sessions=S, opens=prices, closes=prices, **kw)  # type: ignore[arg-type]


# --- commission interpretations -------------------------------------------------------


def test_literal_fractional_rule_charges_one_percent_on_large_fractional_orders() -> None:
    general = _fixed("R2")
    literal = _fixed("R2F", fractional_rate=D("0.01"))
    q, value = D("10.5"), D("5250")
    assert general.commission(q, value) == D("1.00")
    assert literal.commission(q, value) == D("52.50")
    # whole-share orders and the page's fractional examples are identical under both
    assert literal.commission(D("100"), D("2500")) == general.commission(D("100"), D("2500")) == D("1.00")
    for qty, val, fee in (("0.5", "5", "0.05"), ("0.05", "0.75", "0.01")):
        assert literal.commission(D(qty), D(val)) == general.commission(D(qty), D(val)) == D(fee)


def test_tiered_half_percent_cap_and_venue_fee() -> None:
    one = D6CostModel("R3", commission_per_share=D("0.0035"), commission_minimum=D("0.35"), commission_max_rate=D("0.01"))
    half = D6CostModel("R3H", commission_per_share=D("0.0035"), commission_minimum=D("0.35"), commission_max_rate=D("0.005"))
    venue = D6CostModel(
        "R3M",
        commission_per_share=D("0.0035"),
        commission_minimum=D("0.35"),
        commission_max_rate=D("0.01"),
        passthrough_rate=D("0.1"),
        exchange_per_share=D("0.0015"),
    )
    assert one.commission(D("0.1"), D("40")) == D("0.35")
    assert half.commission(D("0.1"), D("40")) == D("0.20")
    # venue fee is per share, uncapped and outside the pass-through base
    assert venue.commission(D("10"), D("4000")) == D("0.35") + D("0.035") + D("0.015")


def test_cost_parameter_validation() -> None:
    with pytest.raises(DataContractError, match="NEGATIVE_COST"):
        D6CostModel("BAD", exchange_per_share=D("-0.001"))
    with pytest.raises(DataContractError, match="REQUIRES_NOTIONAL"):
        D6CostModel("X", fractional_rate=D("0.01")).commission(D("0.5"))


# --- withholding by distribution type -------------------------------------------------


def test_withholding_override_precedence_and_validation() -> None:
    cost = D6CostModel(
        "W",
        withholding_rate=D("0.30"),
        withholding_overrides=(("BND", "DIVIDEND_CASH", D("0.15")), ("BND", "*", D("0")), ("VOO", "*", D("0.15"))),
    )
    assert cost.withholding_for("BND", "DIVIDEND_CASH") == D("0.15")
    assert cost.withholding_for("BND", "CAPITAL_GAIN_LONG_TERM") == D("0")
    assert cost.withholding_for("VOO", "DIVIDEND_CASH") == D("0.15")
    assert cost.withholding_for("BIL", "DIVIDEND_CASH") == D("0.30")
    with pytest.raises(DataContractError, match="DUPLICATE_WITHHOLDING"):
        D6CostModel("D", withholding_overrides=(("BND", "*", D("0")), ("BND", "*", D("0.1"))))
    with pytest.raises(DataContractError, match="WITHHOLDING_RATE"):
        D6CostModel("D", withholding_overrides=(("BND", "*", D("1")),))


def test_engine_applies_withholding_by_symbol() -> None:
    divs = {"BIL": [DividendEvent(date(2024, 1, 31), date(2024, 2, 5), D("1"))]}
    cost = D6CostModel("WT", withholding_overrides=(("BIL", "DIVIDEND_CASH", D("0")),), withholding_rate=D("0.3"))
    result = _run("BIL_100", {"BIL": _flat("100")}, dividends=divs, cost=cost)
    assert result.withholding == D("0") and result.dividends_gross == D("10")


# --- funding cadence ------------------------------------------------------------------


def test_f1_without_frictions_reproduces_f0_contributions() -> None:
    f0 = plan_funding(S, D("50"), RATES, FundingScenario("F0"))
    ctrl = plan_funding(S, D("50"), RATES, FundingScenario("F1_CTRL", cadence=1))
    assert ctrl.contributions == f0.contributions
    assert ctrl.unremitted_thb == D("0") and ctrl.in_transit_usd == D("0")


def test_quarterly_keeps_unremitted_thb_and_same_savings() -> None:
    f1 = plan_funding(S, D("50"), RATES, FundingScenario("F1", cadence=1, sender_fee_thb=D("400")))
    f2 = plan_funding(S, D("50"), RATES, FundingScenario("F2", cadence=3, sender_fee_thb=D("400")))
    assert f1.savings == f2.savings  # identical household savings
    assert len(f2.savings) == 7 and len(f2.remittances) == 2  # Jan..Jul 2024
    assert f2.unremitted_thb == D("1750")
    first = f2.remittances[0]
    assert first.remit_session == date(2024, 3, 1)
    assert first.usd_delivered == ((D("5250") - D("400")) / D("35")).quantize(D("0.01"), rounding="ROUND_DOWN")
    assert sum(f1.contributions.values()) < sum(f2.contributions.values()) + f2.unremitted_thb / D("35")


def test_fee_exceeding_balance_carries_and_delay_shifts_credit() -> None:
    carry = plan_funding(S, D("10"), RATES, FundingScenario("F1", cadence=1, sender_fee_thb=D("400")))
    # 350 THB per month < 400 fee: first remittance only once 700 THB accumulated
    assert carry.remittances[0].remit_session == date(2024, 2, 1)
    delayed = plan_funding(S, D("50"), RATES, FundingScenario("F1", cadence=1, delay_sessions=3))
    assert date(2024, 1, 5) in delayed.contributions  # 2024-01-02 + 3 sessions
    tail = plan_funding(S, D("50"), RATES, FundingScenario("F1", cadence=1, delay_sessions=5))
    assert tail.in_transit_usd == D("50.00")  # 2024-07-01 credit falls after the window


def test_funding_scenario_validation_and_no_future_rate() -> None:
    with pytest.raises(DataContractError, match="FRICTIONLESS_WITH_COSTS"):
        FundingScenario("F0", sender_fee_thb=D("1"))
    with pytest.raises(DataContractError, match="BAD_CADENCE"):
        FundingScenario("X", cadence=0)
    sparse = {date(2023, 12, 1): D("35")}
    with pytest.raises(DataContractError, match="NO_RATE"):
        plan_funding(S, D("50"), sparse, FundingScenario("F1", cadence=1))


# --- attribution ----------------------------------------------------------------------


def _closes_last(prices: dict[str, dict[date, Decimal]]) -> dict[str, Decimal]:
    return {s: series[S[-1]] for s, series in prices.items()}


def test_broker_and_household_identities_hold_exactly() -> None:
    prices = {"VOO": _flat("100"), "BND": _flat("80")}
    for s in S[60:]:
        prices["VOO"][s] = D("120")
    divs = {"BND": [DividendEvent(date(2024, 3, 1), date(2024, 3, 6), D("0.2"))]}
    cost = _fixed("R2", slippage_bps=D("2"), regulatory_fees=True, withholding_rate=D("0.15"))
    rates = {s: D("35") + D(i) / 100 for i, s in enumerate(S)}
    plan = plan_funding(
        S, D("100"), rates, FundingScenario("F2", cadence=3, sender_fee_thb=D("400"), fx_spread=D("0.005"))
    )
    result = _run("VOO_BND_60_40", prices, dividends=divs, cost=cost, contributions=plan.contributions)
    reconcile_cash(result, D("1000"))
    broker = broker_attribution(result, D("1000"), _closes_last(prices))
    assert broker["slippage"] < 0 and broker["withholding_BND"] < 0
    household = household_attribution(plan, broker, result.terminal_nav, rates[S[-1]])
    assert household["sender_fees"] < 0 and household["fx_spread"] < 0
    expected = result.terminal_nav + plan.unremitted_thb / rates[S[-1]]
    assert household["household_usd"] == expected


def test_broker_attribution_detects_tampering() -> None:
    prices = {"VOO": _flat("100")}
    result = _run("VOO_100", prices)
    result.commissions += D("1")
    with pytest.raises(DataContractError, match="BROKER_IDENTITY"):
        broker_attribution(result, D("1000"), _closes_last(prices))
    with pytest.raises(DataContractError, match="MISSING_LAST_CLOSE"):
        broker_attribution(_run("VOO_100", prices), D("1000"), {})
