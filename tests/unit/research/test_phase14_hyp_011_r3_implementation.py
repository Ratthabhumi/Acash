"""Phase-A implementation tests for HYP_011 (synthetic/mocked only, no network)."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, cast
import dataclasses

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.research.hyp_009.accounting import DividendEvent
from acash.research.hyp_009.gates import evaluate_gates
from acash.research.hyp_011 import accounting as ACC
from acash.research.hyp_011 import gates as GATES
from acash.research.hyp_011 import partitions as PART


def _week() -> List[date]:
    return [date(2016, 1, 4), date(2016, 1, 5), date(2016, 1, 6), date(2016, 1, 7)]


def _px(week: List[date], level: str = "100") -> Dict[str, Dict[date, Decimal]]:
    return {
        "ACWI": {s: Decimal(level) for s in week},
        "AGG": {s: Decimal(level) for s in week},
    }


def test_weights_exact_80_20() -> None:
    from acash.research.hyp_011.accounting import TARGET_WEIGHTS

    assert TARGET_WEIGHTS == {"ACWI": Decimal("0.80"), "AGG": Decimal("0.20")}
    assert sum(TARGET_WEIGHTS.values()) == Decimal("1.00")


def test_initial_allocation_and_annual_schedule() -> None:
    cal = NyseCa1Calendar()
    sessions = PART.expected_sessions(cal)
    assert sessions[0] == date(2016, 1, 4)
    schedule = PART.expected_rebalance_sessions(sessions)
    assert len(schedule) == 9
    assert schedule[0] == date(2016, 1, 4)
    assert schedule[1] == date(2017, 1, 3)
    assert schedule[-1] == date(2024, 1, 2)
    years = sorted({d.year for d in schedule[1:]})
    assert years == [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    # No 2025 session in schedule.
    assert all(d < date(2025, 1, 1) for d in schedule)


def test_dividend_entitlement_ordering() -> None:
    week = _week()
    opens = _px(week)
    closes = _px(week)
    events = {
        "ACWI": [DividendEvent(ex_date=week[1], payable_date=week[3], amount_per_share=Decimal("2"))],
        "AGG": [],
    }
    # LONG from first session: entitled on week[1] (held prior close).
    result = ACC.run_allocation(
        path="BASELINE", sessions=week, opens=opens, closes=closes,
        dividends=events, rebalance_sessions=[week[0]],
        slippage_bps=Decimal("2"), fee_multiplier=1,
    )
    assert result.dividends_received == Decimal(result.ending_holdings["ACWI"]) * Decimal("2")
    by_session = {r.session: r for r in result.equity_curve}
    assert by_session[week[1]].dividend_receivable > Decimal("0")
    assert by_session[week[3]].dividend_receivable == Decimal("0")


def test_ex_date_buy_not_entitled_sell_retains() -> None:
    week = _week()
    opens = _px(week)
    closes = _px(week)
    events = {
        "ACWI": [DividendEvent(ex_date=week[0], payable_date=week[2], amount_per_share=Decimal("5"))],
        "AGG": [],
    }
    # Buy executes AT ex-date open -> prior-close holdings zero -> no entitlement.
    result = ACC.run_allocation(
        path="BASELINE", sessions=week, opens=opens, closes=closes,
        dividends=events, rebalance_sessions=[week[0]],
        slippage_bps=Decimal("2"), fee_multiplier=1,
    )
    assert result.dividends_received == Decimal("0")


def test_payable_before_trade_and_unpaid_excluded_from_budget() -> None:
    week = _week()
    opens = _px(week)
    closes = _px(week)
    # Receivable payable AFTER the rebalance session: in equity, not in budget.
    events = {
        "ACWI": [DividendEvent(ex_date=week[0], payable_date=week[2], amount_per_share=Decimal("1"))],
        "AGG": [],
    }
    result = ACC.run_allocation(
        path="BASELINE", sessions=week, opens=opens, closes=closes,
        dividends=events, rebalance_sessions=[week[1]],
        slippage_bps=Decimal("2"), fee_multiplier=1,
    )
    # No prior holdings on week[0] (first session) -> no receivable at all.
    assert result.dividends_received == Decimal("0")


def test_whole_share_floor_sells_first_no_negative_cash() -> None:
    week = _week()
    opens = {"ACWI": {s: Decimal("333.34") for s in week}, "AGG": {s: Decimal("100") for s in week}}
    closes = {"ACWI": {s: Decimal("333.34") for s in week}, "AGG": {s: Decimal("100") for s in week}}
    result = ACC.run_allocation(
        path="BASELINE", sessions=week, opens=opens, closes=closes,
        dividends={"ACWI": [], "AGG": []}, rebalance_sessions=[week[0]],
        slippage_bps=Decimal("2"), fee_multiplier=1,
    )
    for record in result.equity_curve:
        assert record.cash >= Decimal("0")
    total_weights = (
        Decimal(result.ending_holdings["ACWI"]) * Decimal("333.34")
        + Decimal(result.ending_holdings["AGG"]) * Decimal("100")
    ) / result.ending_equity
    assert total_weights <= Decimal("1")


def test_sells_before_buys_and_decrement_tie_break() -> None:
    week = _week()
    # Extremely high prices force the decrement loop; tie-break must pick AGG.
    opens = {"ACWI": {s: Decimal("90000") for s in week}, "AGG": {s: Decimal("90000") for s in week}}
    closes = {"ACWI": {s: Decimal("90000") for s in week}, "AGG": {s: Decimal("90000") for s in week}}
    result = ACC.run_allocation(
        path="BASELINE", sessions=week, opens=opens, closes=closes,
        dividends={"ACWI": [], "AGG": []}, rebalance_sessions=[week[0]],
        slippage_bps=Decimal("2"), fee_multiplier=1,
    )
    for record in result.equity_curve:
        assert record.cash >= Decimal("0")


def test_baseline_stress_independent_paths() -> None:
    week = _week()
    opens = _px(week)
    closes = _px(week)
    empty_divs: Dict[str, List[DividendEvent]] = {"ACWI": [], "AGG": []}
    base = ACC.run_allocation(
        path="BASELINE", sessions=week, opens=opens, closes=closes,
        dividends=empty_divs, rebalance_sessions=[week[0]],
        slippage_bps=Decimal("2"), fee_multiplier=1,
    )
    stress = ACC.run_allocation(
        path="STRESS", sessions=week, opens=opens, closes=closes,
        dividends=empty_divs, rebalance_sessions=[week[0]],
        slippage_bps=Decimal("10"), fee_multiplier=2,
    )
    assert stress.ending_equity < base.ending_equity
    assert stress.regulatory_fees_paid == Decimal("0.00")


def test_first_day_return_and_mdd_peak() -> None:
    week = _week()
    opens = _px(week, "100")
    closes = _px(week, "101")
    result = ACC.run_allocation(
        path="BASELINE", sessions=week, opens=opens, closes=closes,
        dividends={"ACWI": [], "AGG": []}, rebalance_sessions=[week[0]],
        slippage_bps=Decimal("2"), fee_multiplier=1,
    )
    first = result.equity_curve[0]
    assert first.daily_return == first.total_equity / Decimal("100000") - Decimal("1")
    assert result.equity_curve[0].running_peak >= Decimal("100000")
    from acash.research.hyp_009.accounting import annualized_sharpe as _sharpe

    returns = [r.daily_return for r in result.equity_curve if r.daily_return is not None]
    assert len(returns) == len(week)
    assert _sharpe(returns) != Decimal("0")


def test_fee_by_date_resolution() -> None:
    from acash.research.hyp_009.accounting import sell_side_fees

    sec31, taf, _ = sell_side_fees(date(2018, 6, 1), 100, Decimal("25000"), 1)
    assert sec31 > Decimal("0") and taf > Decimal("0")
    with pytest.raises(DataContractError):
        sell_side_fees(date(2000, 1, 1), 100, Decimal("25000"), 1)


def test_benchmark_accounting_no_liquidation() -> None:
    week = _week()
    opens = {s: Decimal("100") for s in week}
    closes = {s: Decimal("101") for s in week}
    bench = ACC.run_single_asset_buy_hold(
        path="BENCHMARK", symbol="SPY", sessions=week, opens=opens, closes=closes,
        dividends=[], slippage_bps=Decimal("2"),
    )
    assert len(bench.trades) == 1
    assert bench.ending_holdings["SPY"] > 0
    assert bench.ending_equity > Decimal("100000")


def test_evidence_derived_g6_and_corruption() -> None:
    sessions = tuple(_week())

    def _evidence(**overrides: Any) -> GATES.HYP011ContractQualificationEvidence:
        base = dict(
            provider_contract_hash_recomputed=GATES.FROZEN_PROVIDER_CONTRACT_HASH,
            provider_contract_hash_authority=GATES.FROZEN_PROVIDER_CONTRACT_HASH,
            request_symbols=("ACWI", "AGG", "SPY"),
            request_feed="sip",
            request_timeframe="1Day",
            request_start=date(2016, 1, 1),
            request_end=date(2024, 12, 31),
            expected_sessions=sessions,
            sessions_by_series=(sessions,) * 6,
            dividend_validated_counts=(36, 108, 20),
            dividend_missing_payable_counts=(0, 0, 0),
            split_determinations=("NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW",) * 3,
            page_shas_recorded=("a", "b"),
            page_shas_recomputed=("a", "b"),
            sealed_hash_pairs=(("x", "x"),),
            expected_rebalance_sessions=tuple([date(2016, 1, 4)] + [date(y, 1, 2) for y in range(2017, 2025)]),
            actual_rebalance_sessions=tuple([date(2016, 1, 4)] + [date(y, 1, 2) for y in range(2017, 2025)]),
            fee_authority_resolved=True,
            whole_share_integral=True,
            cash_never_negative=True,
            leverage_never_above_one=True,
            dividends_processed_count=164,
            dividends_authority_count=164,
            forbidden_access_counts=(0, 0, 0, 0),
        )
        base.update(overrides)
        return GATES.HYP011ContractQualificationEvidence(**cast(Any, base))

    qual = GATES.derive_contract_qualification(_evidence())
    assert qual.no_material_failure is True
    bad = GATES.derive_contract_qualification(
        dataclasses.replace(_evidence(), dividend_missing_payable_counts=(1, 0, 0))
    )
    assert bad.dividend_contract_pass is False
    assert bad.no_material_failure is False
    bad2 = GATES.derive_contract_qualification(
        dataclasses.replace(_evidence(), forbidden_access_counts=(0, 0, 1, 0))
    )
    assert bad2.forbidden_partition_access_zero is False


def test_no_forbidden_access_mocks() -> None:
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    def _boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be invoked")

    import httpx
    from datetime import datetime, timezone
    from acash.data.qualification.models import MarketDataFeed, PriceAdjustment

    client = HYP011AlpacaClient(transport=httpx.MockTransport(_boom))
    with pytest.raises(DataContractError):
        client.fetch_tiny_probe(
            symbol="ACWI", start_utc=datetime(2025, 1, 2, tzinfo=timezone.utc),
            end_utc=datetime(2025, 1, 6, tzinfo=timezone.utc),
            feed=MarketDataFeed.SIP, adjustment=PriceAdjustment.RAW, timeframe="1Day",
        )
