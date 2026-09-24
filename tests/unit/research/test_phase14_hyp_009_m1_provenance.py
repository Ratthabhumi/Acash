"""Provenance/G6/slippage correction tests for HYP_009 M1 (mocked transport only).

No live network. Proves: actual HTTP-attempt listener semantics, page
provenance recording, G6 derivation from qualification state, and exact
friction reporting (regulatory fees vs slippage separated).
"""

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

import httpx
import pytest
from typing import Any, Callable, Dict, List

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.hyp_009_daily_client import HYP009AlpacaClient
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.research.hyp_009 import accounting as ACC
from acash.research.hyp_009 import gates as GATES


def _bar_row(session: str) -> Dict[str, Any]:
    return {
        "t": f"{session}T05:00:00Z",
        "o": 100.0,
        "h": 101.0,
        "l": 99.0,
        "c": 100.5,
        "v": 1000,
    }


def _mock_client(
    handler: Callable[[httpx.Request], httpx.Response], calls: List[int]
) -> HYP009AlpacaClient:
    def _wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return handler(request)

    from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider

    # Isolated dummy environ (never real secrets): proves listener semantics
    # through the real credential-provider path.
    provider = EnvAlpacaCredentialProvider(
        environ={
            "ACASH_ALPACA_API_KEY_ID": "TEST_ISOLATED_KEY",
            "ACASH_ALPACA_API_SECRET": "TEST_ISOLATED_SECRET",
        }
    )
    return HYP009AlpacaClient(
        transport=httpx.MockTransport(_wrapped),
        credential_provider=provider,
        http_attempt_listener=lambda: calls.append(10),
    )


def _ok_payload(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"bars": rows, "next_page_token": None}


def test_pre_network_reject_zero_attempts() -> None:
    calls: List[int] = []
    client = _mock_client(lambda request: httpx.Response(200, json=_ok_payload([])), calls)
    with pytest.raises(DataContractError):
        client.fetch_historical_bars(
            symbol="SPY",
            start_utc=datetime(2021, 1, 1, tzinfo=timezone.utc),
            end_utc=datetime(2021, 1, 5, tzinfo=timezone.utc),
            feed=MarketDataFeed.SIP,
            adjustment=PriceAdjustment.RAW,
            timeframe="1Day",
        )
    assert calls == []


def test_one_page_counts_one_attempt() -> None:
    calls: List[int] = []
    rows = [_bar_row("2016-11-01"), _bar_row("2016-11-02")]
    client = _mock_client(lambda request: httpx.Response(200, json=_ok_payload(rows)), calls)
    result = client.fetch_historical_bars(
        symbol="SPY",
        start_utc=datetime(2016, 11, 1, tzinfo=timezone.utc),
        end_utc=datetime(2016, 11, 4, tzinfo=timezone.utc),
        feed=MarketDataFeed.SIP,
        adjustment=PriceAdjustment.RAW,
        timeframe="1Day",
    )
    assert len(result.bars) == 2
    assert calls.count(10) == 1  # exactly one actual transport execution
    assert len(result.pages_raw_bytes) == 1


def test_429_retry_counts_two_attempts() -> None:
    calls: List[int] = []
    state = {"n": 0}

    def _handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(429, json={})
        return httpx.Response(200, json=_ok_payload([_bar_row("2016-11-01")]))

    client = _mock_client(_handler, calls)
    result = client.fetch_historical_bars(
        symbol="SPY",
        start_utc=datetime(2016, 11, 1, tzinfo=timezone.utc),
        end_utc=datetime(2016, 11, 4, tzinfo=timezone.utc),
        feed=MarketDataFeed.SIP,
        adjustment=PriceAdjustment.RAW,
        timeframe="1Day",
    )
    assert len(result.bars) == 1
    assert calls.count(10) == 2


def test_two_pages_count_two_attempts_with_provenance() -> None:
    calls: List[int] = []
    pages = [
        {"bars": [_bar_row("2016-11-01")], "next_page_token": "tok-1"},
        {"bars": [_bar_row("2016-11-02")], "next_page_token": None},
    ]
    state = {"n": 0}

    def _handler(request: httpx.Request) -> httpx.Response:
        page = pages[state["n"]]
        state["n"] += 1
        return httpx.Response(200, json=page)

    client = _mock_client(_handler, calls)
    result = client.fetch_historical_bars(
        symbol="SPY",
        start_utc=datetime(2016, 11, 1, tzinfo=timezone.utc),
        end_utc=datetime(2016, 11, 4, tzinfo=timezone.utc),
        feed=MarketDataFeed.SIP,
        adjustment=PriceAdjustment.RAW,
        timeframe="1Day",
    )
    assert len(result.bars) == 2
    assert calls.count(10) == 2
    assert len(result.pages_raw_bytes) == 2
    assert len(result.pages_metadata) == 2
    assert result.pages_metadata[0].next_page_token == "tok-1"


def _full_pass_qualification() -> GATES.ContractQualification:
    return GATES.ContractQualification(
        provider_contract_pass=True,
        calendar_coverage_pass=True,
        split_raw_alignment_pass=True,
        dividend_contract_pass=True,
        payable_date_contract_pass=True,
        split_contract_pass=True,
        response_scope_pass=True,
        provenance_hash_pass=True,
        serialization_integrity_pass=True,
        forbidden_partition_access_zero=True,
    )


def test_g6_derived_true_only_when_all_pass() -> None:
    assert _full_pass_qualification().no_material_failure is True


def test_any_single_failure_forces_g6_false_and_blocks_verdict() -> None:
    import dataclasses

    fields = [f.name for f in dataclasses.fields(GATES.ContractQualification)]
    assert len(fields) == 10
    for field in fields:
        qual = dataclasses.replace(_full_pass_qualification(), **{field: False})
        assert qual.no_material_failure is False, field
        outcome = GATES.evaluate_gates(
            GATES.GateInputs(
                baseline_net_total_return=Decimal("0.5"),
                baseline_net_annualized_sharpe=Decimal("0.9"),
                baseline_max_drawdown=Decimal("0.2"),
                benchmark_max_drawdown=Decimal("0.3"),
                stress_net_total_return=Decimal("0.4"),
                no_material_contract_failure=qual.no_material_failure,
            )
        )
        assert outcome.g6 is False
        assert GATES.classify_m1_verdict(outcome, qual.no_material_failure) == (
            "BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT"
        )


def test_friction_reporting_regulatory_vs_slippage() -> None:
    week = [date(2016, 11, 1), date(2016, 11, 2)]
    opens = {s: Decimal("100") for s in week}
    closes = {s: Decimal("100") for s in week}
    result = ACC.run_portfolio(
        path="BASELINE",
        m1_sessions=week,
        opens_raw=opens,
        closes_raw=closes,
        execution_by_session={week[0]: "LONG", week[1]: "CASH"},
        dividends=[],
        slippage_bps=Decimal("2"),
        fee_multiplier=1,
    )
    buy, sell = result.trades
    assert ACC.execution_slippage_cost(buy) == Decimal("0.02") * Decimal(buy.quantity)
    assert ACC.execution_slippage_cost(sell) == Decimal("0.02") * Decimal(sell.quantity)
    assert buy.regulatory_fees_paid == Decimal("0.00")
    assert sell.regulatory_fees_paid > Decimal("0.00")
    assert result.regulatory_fees_paid == sell.regulatory_fees_paid
    with pytest.raises(DataContractError):
        ACC.sell_side_fees(date(2018, 1, 1), 10, Decimal("100"), 3)
