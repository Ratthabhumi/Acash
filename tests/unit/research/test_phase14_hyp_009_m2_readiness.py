"""M2 readiness tests (zero M2 reads): continuity, timing, guards, accounting.

All tests use synthetic data, the canonical calendar, or sealed M1 artifacts.
No network calls. No M2 market-data access.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_009_daily_client import HYP009AlpacaClient
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.research.hyp_009 import accounting as ACC
from acash.research.hyp_009 import partitions as PART
from acash.research.hyp_009 import qualification as QUAL
from acash.research.hyp_009 import signals as SIG


def test_m2_partition_constants_and_guard() -> None:
    assert PART.M2_START == date(2021, 1, 1)
    assert PART.M2_END == date(2024, 12, 31)

    def _boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be invoked")

    client = HYP009AlpacaClient(transport=httpx.MockTransport(_boom))
    with pytest.raises(DataContractError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=datetime(2021, 1, 1, tzinfo=timezone.utc),
            end_utc=datetime(2021, 1, 5, tzinfo=timezone.utc),
            feed=MarketDataFeed.SIP,
            adjustment=PriceAdjustment.RAW,
            timeframe="1Day",
        )


def test_first_m2_execution_derived_from_calendar() -> None:
    cal = NyseCa1Calendar()
    assert cal.is_holiday(date(2021, 1, 1)) is True
    m2 = PART.expected_sessions(cal, PART.M2_START, PART.M2_END)
    assert m2[0] == date(2021, 1, 4)
    resolved = SIG.resolve_execution_dates(
        [
            SIG.MonthSignal(
                decision_date=date(2020, 12, 31),
                signal_level=Decimal("2"),
                sma10=Decimal("1"),
                state="LONG",
                prior_state="LONG",
                transition=False,
            )
        ],
        m2,
    )
    assert resolved[date(2020, 12, 31)] == date(2021, 1, 4)


def test_dec2020_frozen_state_binding() -> None:
    import json
    from pathlib import Path

    sig = json.loads(
        Path("data/hyp_009/signal_ledger_reproducibility_001.json").read_text(
            encoding="utf-8"
        )
    )
    dec2020 = next(r for r in sig["rows"] if r["decision_date"] == "2020-12-31")
    assert dec2020["state"] == "LONG"
    assert dec2020["signal_level"] == "2.051430715393109079173373811"
    assert dec2020["sma10"] == "1.760537145277627779062534321"


def test_tr_continuity_uses_full_history() -> None:
    sessions = [date(2021, 1, d) for d in (4, 5, 6, 7, 8)]
    closes = {s: Decimal("100") for s in sessions}
    index = SIG.build_total_return_index(sessions, closes, {})
    assert index[sessions[0]] == Decimal("1.0")
    assert all(v == Decimal("1.0") for v in index.values())


def test_dec2024_pending_no_2025_access() -> None:
    cal = NyseCa1Calendar()
    m2 = PART.expected_sessions(cal, PART.M2_START, PART.M2_END)
    assert m2[-1] == date(2024, 12, 31)
    resolved = SIG.resolve_execution_dates(
        [
            SIG.MonthSignal(
                decision_date=date(2024, 12, 31),
                signal_level=Decimal("1"),
                sma10=Decimal("2"),
                state="CASH",
                prior_state="LONG",
                transition=True,
            )
        ],
        m2,
    )
    assert resolved[date(2024, 12, 31)] is None


def test_m2_dividend_scope_qualification() -> None:
    events = QUAL.qualify_dividends(
        [
            {"ex_date": "2021-03-19", "payable_date": "2021-04-30", "cash_distribution": "1.2"},
            {"ex_date": "2020-12-18", "payable_date": "2021-01-29", "cash_distribution": "1.5"},
        ],
        PART.M2_START,
        PART.M2_END,
    )
    assert [e.ex_date for e in events] == [date(2021, 3, 19)]


def test_m2_verdict_labels_distinct_from_m1() -> None:
    from acash.research.hyp_009 import gates as GATES

    good = GATES.GateInputs(
        baseline_net_total_return=Decimal("0.5"),
        baseline_net_annualized_sharpe=Decimal("0.9"),
        baseline_max_drawdown=Decimal("0.2"),
        benchmark_max_drawdown=Decimal("0.3"),
        stress_net_total_return=Decimal("0.4"),
        no_material_contract_failure=True,
    )
    outcome = GATES.evaluate_gates(good)
    assert GATES.classify_m2_verdict(outcome, True) == (
        "M2_SUPPORTED_FOR_RECENT_STRESS_CONSIDERATION"
    )
    bad = GATES.evaluate_gates(
        GATES.GateInputs(
            baseline_net_total_return=Decimal("-0.1"),
            baseline_net_annualized_sharpe=Decimal("0.9"),
            baseline_max_drawdown=Decimal("0.2"),
            benchmark_max_drawdown=Decimal("0.3"),
            stress_net_total_return=Decimal("0.4"),
            no_material_contract_failure=True,
        )
    )
    assert GATES.classify_m2_verdict(bad, True) == "FAIL_CORE_EDGE_NOT_SUPPORTED"
    assert GATES.classify_m2_verdict(bad, False) == (
        "BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT"
    )


def test_independent_m2_starting_aum() -> None:
    week = [date(2021, 1, 4), date(2021, 1, 5)]
    px: Dict[str, Dict[date, Decimal]] = {
        "open": {s: Decimal("100") for s in week},
        "close": {s: Decimal("100") for s in week},
    }
    result = ACC.run_portfolio(
        path="M2_BASELINE",
        m1_sessions=week,
        opens_raw=px["open"],
        closes_raw=px["close"],
        execution_by_session={},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
        starting_aum=Decimal("100000.00"),
    )
    assert result.ending_equity == Decimal("100000.00")
    assert result.equity_curve[0].total_equity == Decimal("100000.00")
