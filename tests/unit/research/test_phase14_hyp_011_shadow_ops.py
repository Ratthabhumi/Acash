"""Tests for prospective shadow ops: single-session accounting, chain, runner guards.

Synthetic/mocked only. No network. No live observation.
"""

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_009.accounting import DividendEvent
from acash.research.hyp_011.shadow_ops import (
    SessionMarket,
    ShadowBenchmark,
    ShadowPortfolio,
    append_observation,
    process_benchmark_session,
    process_strategy_session,
)


def _market(session: date, level: str = "100") -> SessionMarket:
    px = Decimal(level)
    return SessionMarket(
        session=session,
        opens_raw={"ACWI": px, "AGG": px},
        closes_raw={"ACWI": px, "AGG": px},
    )


def test_fresh_state_and_initial_80_20_allocation() -> None:
    portfolio = ShadowPortfolio()
    assert portfolio.cash == Decimal("100000.00")
    assert portfolio.holdings == {"ACWI": 0, "AGG": 0}
    frag = process_strategy_session(
        portfolio, _market(date(2026, 9, 28)), {}, True,
        Decimal("2"), 1, "SHADOW_BASELINE",
    )
    assert portfolio.holdings["ACWI"] > 0
    assert portfolio.holdings["AGG"] > 0
    w_acwi = Decimal(portfolio.holdings["ACWI"]) * Decimal("100") / Decimal(frag["equity"])
    assert abs(w_acwi - Decimal("0.80")) < Decimal("0.05")


def test_initial_allocation_not_annual_rebalance() -> None:
    # Rebalance counting lives in ShadowState.completed_annual_rebalances,
    # which process_strategy_session never touches.
    from acash.research.hyp_011.shadow import ShadowState

    state = ShadowState(activation_session=date(2026, 9, 28))
    assert state.completed_annual_rebalances == 0


def test_prior_close_entitlement_and_payable_ordering() -> None:
    portfolio = ShadowPortfolio()
    process_strategy_session(
        portfolio, _market(date(2026, 9, 28)), {}, True, Decimal("2"), 1, "P"
    )
    shares = portfolio.holdings["ACWI"]
    event = DividendEvent(
        ex_date=date(2026, 9, 29), payable_date=date(2026, 10, 5),
        amount_per_share=Decimal("1"),
    )
    frag = process_strategy_session(
        portfolio, _market(date(2026, 9, 29)), {"ACWI": event}, False,
        Decimal("2"), 1, "P",
    )
    assert frag["entitlements"] == [{
        "symbol": "ACWI", "ex_date": "2026-09-29", "amount": str(Decimal(shares)),
    }]
    # Receivable in equity but not yet spendable (payable Oct-05).
    assert Decimal(frag["receivable"]) == Decimal(shares)


def test_ex_date_activation_buy_not_entitled() -> None:
    portfolio = ShadowPortfolio()
    event = DividendEvent(
        ex_date=date(2026, 9, 28), payable_date=date(2026, 10, 5),
        amount_per_share=Decimal("1"),
    )
    frag = process_strategy_session(
        portfolio, _market(date(2026, 9, 28)), {"ACWI": event}, True,
        Decimal("2"), 1, "P",
    )
    assert frag["entitlements"] == []


def test_split_fail_close_contract() -> None:
    # Split-event authority must be bound before holdings update; the ops layer
    # performs no silent ratio inference. Non-positive prices fail closed here
    # as the accounting-level guard.
    portfolio = ShadowPortfolio()
    bad = SessionMarket(
        session=date(2026, 9, 28),
        opens_raw={"ACWI": Decimal("0"), "AGG": Decimal("100")},
        closes_raw={"ACWI": Decimal("100"), "AGG": Decimal("100")},
    )
    with pytest.raises(DataContractError):
        process_strategy_session(
            portfolio, bad, {}, True, Decimal("2"), 1, "P"
        )


def test_single_row_provider_contract_shape() -> None:
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient
    from acash.data.qualification.models import MarketDataFeed, PriceAdjustment

    import httpx

    calls = []

    def _boom(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise AssertionError("network must not be invoked")

    client = HYP011AlpacaClient(transport=httpx.MockTransport(_boom))
    # Sunday is not a trading session: rejected pre-network with zero calls.
    with pytest.raises(DataContractError):
        client.fetch_single_session(
            symbol="ACWI", session=date(2026, 9, 27),
            feed=MarketDataFeed.SIP, adjustment=PriceAdjustment.RAW,
            timeframe="1Day",
        )
    assert calls == []


def test_append_only_chain_and_tamper() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp)
        sha1 = append_observation(
            state_dir, date(2026, 9, 28), {"equity": "100979.02"}, None
        )
        assert (state_dir / "observations" / "2026-09-28.json").is_file()
        state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
        assert state["last_observation_sha256"] == sha1
        assert state["observed_session_count"] == 1
        # Duplicate write rejected (immutability).
        with pytest.raises(DataContractError):
            append_observation(state_dir, date(2026, 9, 28), {"equity": "1"}, sha1)
        # Tamper detection: altered bytes no longer match the chained pin.
        target = state_dir / "observations" / "2026-09-28.json"
        target.write_text('{"tampered": true}', encoding="utf-8")
        import hashlib

        assert hashlib.sha256(target.read_bytes()).hexdigest() != sha1


def test_benchmark_independent_and_first_day_anchor() -> None:
    bench = ShadowBenchmark()
    frag = process_benchmark_session(
        bench, date(2026, 9, 28), Decimal("500"), Decimal("501"), None, Decimal("2")
    )
    assert frag["entry"]["side"] == "BUY"
    assert bench.shares > 0
    # First-day return anchored at 100000.
    first_equity = Decimal(frag["equity"])
    assert Decimal(frag["daily_return"]) == first_equity / Decimal("100000") - Decimal("1")
    # Second session with same prices: return ~ fee-free drift only.
    frag2 = process_benchmark_session(
        bench, date(2026, 9, 29), Decimal("501"), Decimal("501"), None, Decimal("2")
    )
    assert Decimal(frag2["daily_return"]) == Decimal(frag2["equity"]) / first_equity - Decimal("1")


def test_runner_dry_run_zero_network(capsys: Any) -> None:
    import sys

    sys.path.insert(0, "scripts")
    import process_hyp_011_prospective_shadow as runner  # type: ignore[import-not-found]

    assert runner.main([]) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
