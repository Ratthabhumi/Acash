"""BIL 1-for-2 reverse split, 2017-11-30 (State Street IRS Form 8937, CUSIP 78468R663).

Synthetic prices around the real event date; no provider data in the repository.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.etf_fx_benchmark import DistributionShareBasis, EtfDistributionRecord
from acash.research.d6.accounting import D6_REGISTERED_PORTFOLIOS, D6CostModel, run_d6_portfolio

SESSIONS = [date(2017, 11, 27), date(2017, 11, 28), date(2017, 11, 29), date(2017, 11, 30), date(2017, 12, 1)]
PRE, POST = Decimal("45.70"), Decimal("91.40")
SPLIT = {"BIL": {date(2017, 11, 30): Decimal("0.5")}}
ZERO_COST = D6CostModel(label="ZERO_COST_UPPER_BOUND")
PORTFOLIOS = {p.name: p for p in D6_REGISTERED_PORTFOLIOS}


def _prices(sym: str = "BIL") -> dict[str, dict[date, Decimal]]:
    return {sym: {s: PRE if s < date(2017, 11, 30) else POST for s in SESSIONS}}


def _dividend(sym: str = "BIL") -> EtfDistributionRecord:
    return EtfDistributionRecord(
        symbol=sym,
        ex_date=date(2017, 11, 29),
        payable_date=date(2017, 12, 1),
        gross_amount=Decimal("0.05"),
        event_id="pre-split",
        share_basis=DistributionShareBasis.POST_SPLIT,
    )


def test_reverse_split_halves_shares_without_gain_and_keeps_pre_split_receivable() -> None:
    result = run_d6_portfolio(
        PORTFOLIOS["BIL_100"],
        sessions=SESSIONS,
        opens=_prices(),
        closes=_prices(),
        dividends={"BIL": [_dividend()]},
        splits=SPLIT,
        cost=ZERO_COST,
    )
    bought = result.trades[0].quantity
    assert result.holdings["BIL"] == bought * Decimal("0.5")
    nav = {r.session: r for r in result.nav_curve}
    pre, post = nav[date(2017, 11, 29)], nav[date(2017, 11, 30)]
    assert post.market_value == pre.market_value
    assert post.nav == pre.nav
    assert pre.receivable == post.receivable == bought * Decimal("0.05")
    assert result.dividends_gross == bought * Decimal("0.05")
    assert nav[date(2017, 12, 1)].receivable == 0
    assert result.terminal_nav == pre.nav


def test_split_and_ex_date_on_same_session_fails_closed() -> None:
    clash = _dividend().model_copy(update={"ex_date": date(2017, 11, 30)})
    with pytest.raises(DataContractError, match="D6_SPLIT_AND_EX_DATE_SAME_SESSION_UNSUPPORTED"):
        run_d6_portfolio(
            PORTFOLIOS["BIL_100"], sessions=SESSIONS, opens=_prices(), closes=_prices(),
            dividends={"BIL": [clash]}, splits=SPLIT, cost=ZERO_COST,
        )


def test_gld_has_no_cash_entitlement_and_gldm_is_not_gld() -> None:
    gld = PORTFOLIOS["VOO_BND_GLD_BIL_50_30_10_10"]
    assert "GLD" in gld.weights and "GLDM" not in gld.weights
    prices = {**_prices("VOO"), **_prices("BND"), **_prices("GLD"), **_prices("BIL")}
    with pytest.raises(DataContractError, match="D6_NO_CASH_DISTRIBUTION_ENTITLEMENT: GLD"):
        run_d6_portfolio(
            gld, sessions=SESSIONS, opens=prices, closes=prices,
            dividends={"GLD": [_dividend("GLD")]}, splits=SPLIT, cost=ZERO_COST,
        )
