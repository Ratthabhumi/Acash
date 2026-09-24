"""Phase-A implementation tests for HYP_009 M1 pipeline (synthetic/mocked only).

No live network. No full M1 data. Covers the frozen §10/§31 verification list:
partitions, guards, signals, execution, accounting, dividends, splits, terminal,
benchmark, metrics, and forbidden-date pre-network rejection.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.daily_models import DailyBar
from acash.data.qualification.hyp_009_daily_client import (
    HYP009AlpacaClient,
    Hyp009PreNetworkGuard,
)
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.execution.alpaca.credentials import AlpacaCredentialError
from acash.research.hyp_009 import accounting as ACC
from acash.research.hyp_009 import gates as GATES
from acash.research.hyp_009 import partitions as PART
from acash.research.hyp_009 import qualification as QUAL
from acash.research.hyp_009 import signals as SIG


def _bar(
    session: date,
    open_px: str,
    high_px: str,
    low_px: str,
    close_px: str,
    volume: str = "1000",
) -> DailyBar:
    return DailyBar(
        timestamp_utc=datetime(
            session.year, session.month, session.day, 14, 30, tzinfo=timezone.utc
        ),
        open=Decimal(open_px),
        high=Decimal(high_px),
        low=Decimal(low_px),
        close=Decimal(close_px),
        volume=Decimal(volume),
    )


def _sessions_2016() -> List[date]:
    cal = NyseCa1Calendar()
    return PART.expected_sessions(cal, date(2016, 1, 1), date(2016, 12, 31))


# ---------------------------------------------------------------- DATA/CALENDAR


def test_frozen_partition_constants() -> None:
    assert PART.WARMUP_START == date(2016, 1, 1)
    assert PART.WARMUP_END == date(2016, 10, 31)
    assert PART.M1_START == date(2016, 11, 1)
    assert PART.M1_END == date(2020, 12, 31)
    assert PART.AUTHORIZED_MIN_DATE == date(2016, 1, 1)
    assert PART.AUTHORIZED_MAX_DATE == date(2020, 12, 31)


def test_pre_2016_window_rejected() -> None:
    with pytest.raises(DataContractError):
        PART.assert_m1_window(date(2015, 12, 31), date(2020, 12, 31))
    guard = Hyp009PreNetworkGuard()
    with pytest.raises(DataContractError):
        guard.validate_window(
            datetime(2015, 12, 31, tzinfo=timezone.utc),
            datetime(2016, 1, 5, tzinfo=timezone.utc),
        )


def _no_network_client() -> HYP009AlpacaClient:
    def _boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network adapter must not be invoked")

    return HYP009AlpacaClient(transport=httpx.MockTransport(_boom))


def _utc(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def test_forbidden_dates_rejected_pre_network() -> None:
    client = _no_network_client()
    cases = [
        (date(2021, 1, 1), date(2021, 1, 5)),  # M2
        (date(2024, 6, 1), date(2024, 6, 5)),  # M2
        (date(2025, 3, 1), date(2025, 3, 5)),  # M3
        (date(2026, 8, 15), date(2026, 8, 20)),  # quarantine
        (date(2026, 9, 24), date(2026, 9, 25)),  # prospective
    ]
    for start, end in cases:
        with pytest.raises(DataContractError):
            client.fetch_historical_bars(
                symbol="SPY",
                start_utc=_utc(start),
                end_utc=_utc(end),
                feed=MarketDataFeed.SIP,
                adjustment=PriceAdjustment.RAW,
                timeframe="1Day",
            )


def test_early_close_accepted_holiday_rejected() -> None:
    cal = NyseCa1Calendar()
    # 2016-11-25: day after Thanksgiving, official early close -> session.
    assert cal.is_trading_session(date(2016, 11, 25)) is True
    assert cal.is_early_close(date(2016, 11, 25)) is True
    # 2016-01-01: New Year holiday -> not a session.
    assert cal.is_trading_session(date(2016, 1, 1)) is False
    assert cal.is_holiday(date(2016, 1, 1)) is True


def test_bar_series_qualification_failures() -> None:
    sessions = _sessions_2016()
    bars = [_bar(s, "100", "101", "99", "100.5") for s in sessions]
    # Happy path passes.
    assert QUAL.qualify_bar_series(sessions, bars, bars) == sessions
    # Missing session fails.
    with pytest.raises(DataContractError):
        QUAL.qualify_bar_series(sessions, bars[1:], bars)
    # Extra session fails.
    with pytest.raises(DataContractError):
        QUAL.qualify_bar_series(sessions, bars, bars + [bars[0]])
    # Duplicate fails.
    dup = bars[:5] + [bars[4]] + bars[5:]
    with pytest.raises(DataContractError):
        QUAL.qualify_bar_series(sessions, dup, bars)
    # Split/raw mismatch fails.
    shifted = [_bar(s, "100", "101", "99", "100.5") for s in sessions[1:]]
    shifted.append(_bar(date(2016, 12, 30), "100", "101", "99", "100.5"))
    with pytest.raises(DataContractError):
        QUAL.qualify_bar_series(sessions, bars, shifted)


# ---------------------------------------------------------------- SIGNAL


def _flat_levels(
    sessions: List[date], level: str = "1.0"
) -> Dict[date, Decimal]:
    return {s: Decimal(level) for s in sessions}


def test_warmup_requires_exactly_10_month_ends() -> None:
    sessions = _sessions_2016()
    month_ends = PART.month_end_sessions(sessions)
    assert len(month_ends) == 12
    closes = _flat_levels(sessions)
    with pytest.raises(DataContractError):
        SIG.compute_signal_states(sessions[:150], closes, {})
    signals = SIG.compute_signal_states(sessions, closes, {})
    # Flat index: level == SMA10 -> CASH; first signal at Oct 2016 (10th month-end).
    assert signals[0].decision_date == date(2016, 10, 31)
    assert all(s.state == "CASH" for s in signals)


def test_month_end_is_last_eligible_session_and_current_month_included() -> None:
    sessions = _sessions_2016()
    month_ends = PART.month_end_sessions(sessions)
    assert month_ends[0] == date(2016, 1, 29)  # Jan 29 Fri; Jan 30-31 weekend.
    # Rising staircase: each month-end level above its 10M mean -> LONG from Oct.
    closes: Dict[date, Decimal] = {}
    level = Decimal("1.0")
    for i, s in enumerate(sessions):
        if s in month_ends:
            level += Decimal("0.01")
        closes[s] = level
    signals = SIG.compute_signal_states(sessions, closes, {})
    assert signals[0].state == "LONG"


def test_long_iff_strictly_greater_equality_is_cash() -> None:
    sessions = _sessions_2016()
    closes = _flat_levels(sessions, "2.0")
    signals = SIG.compute_signal_states(sessions, closes, {})
    assert all(s.signal_level == s.sma10 for s in signals)
    assert all(s.state == "CASH" for s in signals)


def test_total_return_recursion_and_ex_date_dividend() -> None:
    sessions = [date(2016, 11, 1), date(2016, 11, 2), date(2016, 11, 3)]
    closes = {s: Decimal("100") for s in sessions}
    dividends = {date(2016, 11, 2): Decimal("1")}
    index = SIG.build_total_return_index(sessions, closes, dividends)
    assert index[sessions[0]] == Decimal("1.0")
    assert index[sessions[1]] == Decimal("1.01")
    assert index[sessions[2]] == Decimal("1.01")
    with pytest.raises(DataContractError):
        SIG.build_total_return_index(sessions, closes, {sessions[0]: Decimal("-1")})


# ---------------------------------------------------------------- EXECUTION / ACCOUNTING


def _m1_week() -> List[date]:
    return [
        date(2016, 11, 1),
        date(2016, 11, 2),
        date(2016, 11, 3),
        date(2016, 11, 4),
        date(2016, 11, 7),
    ]


def _prices(week: List[date], open_px: str = "100", close_px: str = "100") -> Dict[str, Dict[date, Decimal]]:
    return {
        "open": {s: Decimal(open_px) for s in week},
        "close": {s: Decimal(close_px) for s in week},
    }


def test_next_session_open_execution_and_state_change_only() -> None:
    week = _m1_week()
    px = _prices(week)
    # LONG from first session, hold: exactly one BUY, no churn.
    result = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={week[0]: "LONG"},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    assert len(result.trades) == 1
    assert result.trades[0].side == "BUY"
    assert result.trades[0].execution_date == week[0]
    assert result.ending_shares > 0
    # Repeating LONG on a later session adds no trade.
    result2 = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={week[0]: "LONG", week[2]: "LONG"},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    assert len(result2.trades) == 1


def test_execution_after_close_never_same_close() -> None:
    resolved = SIG.resolve_execution_dates(
        [
            SIG.MonthSignal(
                decision_date=date(2016, 10, 31),
                signal_level=Decimal("1"),
                sma10=Decimal("1"),
                state="LONG",
                prior_state=None,
                transition=False,
            )
        ],
        _m1_week(),
    )
    assert resolved[date(2016, 10, 31)] == date(2016, 11, 1)


def test_whole_share_floor_no_short_no_leverage_no_negative_cash() -> None:
    week = _m1_week()
    px = _prices(week, open_px="333.34", close_px="333.34")
    result = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={week[0]: "LONG"},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    fill = Decimal("333.34") * Decimal("1.0002")
    assert result.ending_shares == int(Decimal("100000") // fill)
    for record in result.equity_curve:
        assert record.cash >= Decimal("0")
        assert record.shares >= 0
        assert record.market_value <= record.total_equity
    # CASH only: zero shares throughout.
    flat = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    assert flat.ending_shares == 0
    assert flat.ending_equity == Decimal("100000")


def test_residual_cash_earns_zero() -> None:
    week = _m1_week()
    px = _prices(week, open_px="100", close_px="100")
    result = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={week[0]: "LONG"},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    cash_values = {r.cash for r in result.equity_curve}
    assert len(cash_values) == 1  # unchanged residual cash while LONG


def test_baseline_and_stress_fills() -> None:
    assert ACC.adverse_fill(Decimal("100"), "BUY", Decimal("2")) == Decimal("100.02")
    assert ACC.adverse_fill(Decimal("100"), "SELL", Decimal("2")) == Decimal("99.98")
    assert ACC.adverse_fill(Decimal("100"), "BUY", Decimal("10")) == Decimal("100.10")
    assert ACC.adverse_fill(Decimal("100"), "SELL", Decimal("10")) == Decimal("99.90")
    with pytest.raises(DataContractError):
        ACC.adverse_fill(Decimal("100"), "HOLD", Decimal("2"))


def test_sell_side_regulatory_fees_buy_side_zero() -> None:
    sec31, taf, cat = ACC.sell_side_fees(date(2018, 6, 1), 100, Decimal("25000"), 1)
    assert sec31 > Decimal("0")
    assert taf > Decimal("0")
    assert cat == Decimal("0.00")
    sec31_s, taf_s, _ = ACC.sell_side_fees(date(2018, 6, 1), 100, Decimal("25000"), 2)
    assert sec31_s == sec31 * 2
    assert taf_s == taf * 2


def test_dividend_receivable_ex_date_and_payable() -> None:
    week = _m1_week()
    px = _prices(week)
    events = [
        ACC.DividendEvent(
            ex_date=week[1], payable_date=week[3], amount_per_share=Decimal("1")
        )
    ]
    result = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={week[0]: "LONG"},
        dividends=events,
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    by_session = {r.session: r for r in result.equity_curve}
    # Receivable in equity from ex-date, cash only from payable date.
    assert by_session[week[1]].dividend_receivable > Decimal("0")
    assert by_session[week[2]].dividend_receivable > Decimal("0")
    assert by_session[week[3]].dividend_receivable == Decimal("0")
    assert result.dividends_received == Decimal(result.ending_shares) * Decimal("1")


def test_split_detection_unbound_raises() -> None:
    sessions = [date(2016, 11, 1), date(2016, 11, 2), date(2016, 11, 3)]
    split = {s: Decimal("100") for s in sessions}
    raw_same = {s: Decimal("200") for s in sessions}
    assert QUAL.require_no_unbound_splits(sessions, split, raw_same) == (
        "NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW"
    )
    raw_jump = dict(raw_same)
    raw_jump[sessions[2]] = Decimal("100")
    with pytest.raises(DataContractError):
        QUAL.require_no_unbound_splits(sessions, split, raw_jump)


def test_dividend_qualification() -> None:
    events = QUAL.qualify_dividends(
        [
            {
                "ex_date": "2016-03-18",
                "payable_date": "2016-04-29",
                "cash_distribution": "1.5",
            }
        ],
        date(2016, 1, 1),
        date(2020, 12, 31),
    )
    assert len(events) == 1
    assert events[0].payable_date == date(2016, 4, 29)
    # Out-of-scope records are excluded (never admitted), not errors.
    scoped = QUAL.qualify_dividends(
        [
            {"ex_date": "2016-03-18", "payable_date": "2016-04-29", "cash_distribution": "1.5"},
            {"ex_date": "2021-03-19", "payable_date": "2021-04-30", "cash_distribution": "1.5"},
        ],
        date(2016, 1, 1),
        date(2020, 12, 31),
    )
    assert [e.ex_date for e in scoped] == [date(2016, 3, 18)]
    with pytest.raises(DataContractError):
        QUAL.qualify_dividends(
            [
                {"ex_date": "2016-03-18", "payable_date": "2016-04-29", "cash_distribution": "1.5"},
                {"ex_date": "2016-03-18", "payable_date": "2016-04-29", "cash_distribution": "1.6"},
            ],
            date(2016, 1, 1),
            date(2020, 12, 31),
        )


def test_terminal_no_liquidation_dec2020_pending() -> None:
    week = _m1_week()
    px = _prices(week)
    result = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={week[0]: "LONG"},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    assert result.ending_shares > 0  # still LONG at terminal: no forced sale
    assert len([t for t in result.trades if t.side == "SELL"]) == 0
    resolved = SIG.resolve_execution_dates(
        [
            SIG.MonthSignal(
                decision_date=date(2020, 12, 31),
                signal_level=Decimal("1"),
                sma10=Decimal("1"),
                state="CASH",
                prior_state="LONG",
                transition=True,
            )
        ],
        week,
    )
    assert resolved[date(2020, 12, 31)] is None  # pending, never triggers 2021 fetch


# ---------------------------------------------------------------- BENCHMARK / METRICS / GATES


def test_benchmark_independent_single_entry() -> None:
    week = _m1_week()
    px = _prices(week, open_px="100", close_px="101")
    bench = ACC.run_portfolio(
        path="BENCHMARK",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={week[0]: "LONG"},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    assert len(bench.trades) == 1
    assert bench.ending_equity > Decimal("100000")


def test_sharpe_convention_and_zero_variance_fail_closed() -> None:
    rets = [Decimal("0.01"), Decimal("-0.005"), Decimal("0.02"), Decimal("0.0")]
    sharpe = ACC.annualized_sharpe(rets)
    assert sharpe > Decimal("0")
    with pytest.raises(DataContractError):
        ACC.annualized_sharpe([Decimal("0.01")] * 5)
    with pytest.raises(DataContractError):
        ACC.annualized_sharpe([Decimal("0.01")])


def test_max_drawdown_calculation() -> None:
    assert ACC.max_drawdown([Decimal("100"), Decimal("110"), Decimal("99")]) == (
        (Decimal("110") - Decimal("99")) / Decimal("110")
    )
    assert ACC.max_drawdown([Decimal("100"), Decimal("101")]) == Decimal("0")


def test_gate_operators_exact() -> None:
    good = GATES.GateInputs(
        baseline_net_total_return=Decimal("0.5"),
        baseline_net_annualized_sharpe=Decimal("0.6"),
        baseline_max_drawdown=Decimal("0.2"),
        benchmark_max_drawdown=Decimal("0.3"),
        stress_net_total_return=Decimal("0.1"),
        no_material_contract_failure=True,
    )
    outcome = GATES.evaluate_gates(good)
    assert outcome.conjunction is True
    assert GATES.classify_m1_verdict(outcome, True) == "M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION"
    # Equality on G4 fails (strict <).
    tied = GATES.GateInputs(
        baseline_net_total_return=Decimal("0.5"),
        baseline_net_annualized_sharpe=Decimal("0.6"),
        baseline_max_drawdown=Decimal("0.3"),
        benchmark_max_drawdown=Decimal("0.3"),
        stress_net_total_return=Decimal("0.1"),
        no_material_contract_failure=True,
    )
    tied_outcome = GATES.evaluate_gates(tied)
    assert tied_outcome.g4 is False
    assert GATES.classify_m1_verdict(tied_outcome, True) == "M1_NOT_SUPPORTED_NO_M2_AUTHORIZATION"
    assert GATES.classify_m1_verdict(outcome, False) == "BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT"
