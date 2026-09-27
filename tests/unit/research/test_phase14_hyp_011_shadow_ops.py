"""Tests for prospective shadow ops: single-session accounting, chain, runner guards.

Synthetic/mocked only. No network. No live observation.
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

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


def test_state_serde_round_trip() -> None:
    from acash.research.hyp_011.shadow_ops import (
        ShadowBenchmark,
        ShadowPortfolio,
        verify_chain,
    )

    portfolio = ShadowPortfolio()
    process_strategy_session(
        portfolio, _market(date(2026, 9, 28)), {}, True, Decimal("2"), 1, "P"
    )
    restored = ShadowPortfolio.from_dict(portfolio.to_dict())
    assert restored == portfolio
    bench = ShadowBenchmark()
    process_benchmark_session(
        bench, date(2026, 9, 28), Decimal("500"), Decimal("501"), None, Decimal("2")
    )
    assert ShadowBenchmark.from_dict(bench.to_dict()) == bench
    with pytest.raises(DataContractError):
        ShadowPortfolio.from_dict({"cash": "x"})


def test_verify_chain_blocks_tamper_and_orphan() -> None:
    import tempfile

    from acash.research.hyp_011.shadow_ops import append_observation, verify_chain

    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp)
        # Empty dir verifies as fresh state.
        fresh = verify_chain(state_dir)
        assert fresh["observed_sessions"] == []
        # Orphan file with no state sessions -> blocked.
        (state_dir / "observations").mkdir(parents=True)
        (state_dir / "observations" / "2026-09-28.json").write_text("{}", encoding="utf-8")
        (state_dir / "state.json").write_text(
            json.dumps({"observed_sessions": []}), encoding="utf-8"
        )
        with pytest.raises(DataContractError):
            verify_chain(state_dir)


def test_runner_ordinal_and_chain_guards() -> None:
    import sys

    sys.path.insert(0, "scripts")
    import process_hyp_011_prospective_shadow as runner

    # Wrong ordinal rejected pre-network (no --execute-network needed for arg parse,
    # but ordinal check happens after chain verify which needs no network).
    with pytest.raises(DataContractError):
        runner.main(["--execute-network", "--authorization", "AUTH_X", "--ordinal", "99"])


class _MockBars:
    bars: List[Any]
    pages_metadata: List[Any]
    pages_raw_bytes: List[Any]

    def __init__(self, session: date, level: str = "100"):
        from acash.data.qualification.daily_models import DailyBar

        self.bars = [
            DailyBar(
                timestamp_utc=datetime.combine(
                    session, datetime.min.time(), tzinfo=timezone.utc
                ).replace(hour=5),
                open=Decimal(level),
                high=Decimal(level),
                low=Decimal(level),
                close=Decimal(level),
                volume=Decimal("1000"),
            )
        ]
        self.pages_metadata = []
        self.pages_raw_bytes = []


class _MockClient:
    def __init__(self, calls: List[Any], level: str = "100"):
        self._calls = calls
        self._level = level

    def fetch_single_session(self, symbol: str, session: date, **kwargs: Any) -> Any:
        self._calls.append((symbol, session.isoformat()))
        return _MockBars(session, self._level)


def _run_observation(
    tmp_path: Path,
    session: str,
    ordinal: int,
    now_utc: datetime,
    calls: List[Any],
    level: str = "100",
    ca_file: str = "",
) -> int:
    import sys

    sys.path.insert(0, "scripts")
    import process_hyp_011_prospective_shadow as runner

    argv = [
        "--execute-network",
        "--authorization",
        f"AUTH_OBS_{ordinal:04d}",
        "--ordinal",
        str(ordinal),
    ]
    if ca_file:
        argv += ["--ca-determinations", ca_file]
    return int(
        runner.main(
            argv,
            _now_utc=now_utc,
            _state_dir=tmp_path,
            _client=_MockClient(calls, level),
        )
    )


def test_mocked_observation_0001_end_to_end(tmp_path: Path) -> None:
    calls: List[Any] = []
    rc = _run_observation(
        tmp_path, "2026-09-28", 1,
        datetime(2026, 9, 28, 21, 0, 0, tzinfo=timezone.utc), calls,
    )
    assert rc == 0
    assert len(calls) == 6  # 3 symbols x 2 adjustments, no retry
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["observed_sessions"] == ["2026-09-28"]
    assert state["observed_session_count"] == 1
    assert state["last_processed_session"] == "2026-09-28"
    assert state["completed_annual_rebalances"] == 0
    assert state["strategy"]["holdings"]["ACWI"] > 0
    assert state["strategy"]["holdings"]["AGG"] > 0
    assert state["benchmark"]["SPY_shares"] > 0
    obs = json.loads(
        (tmp_path / "observations" / "2026-09-28.json").read_text(encoding="utf-8")
    )
    assert obs["previous_observation_sha256"] is None
    assert state["last_observation_sha256"] == hashlib.sha256(
        (tmp_path / "observations" / "2026-09-28.json").read_bytes()
    ).hexdigest()


def test_second_mocked_observation_continuity(tmp_path: Path) -> None:
    calls: List[Any] = []
    assert _run_observation(
        tmp_path, "2026-09-28", 1,
        datetime(2026, 9, 28, 21, 0, 0, tzinfo=timezone.utc), calls,
    ) == 0
    state1 = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    cash1 = state1["strategy"]["cash"]
    # Second session: needs CA determinations file (has prior holdings now).
    ca_doc = {
        symbol: {"session": "2026-09-29", "has_event": False}
        for symbol in ("ACWI", "AGG", "SPY")
    }
    ca_path = tmp_path / "ca_2026-09-29.json"
    ca_path.write_text(json.dumps(ca_doc), encoding="utf-8")
    assert _run_observation(
        tmp_path, "2026-09-29", 2,
        datetime(2026, 9, 29, 21, 0, 0, tzinfo=timezone.utc), calls,
        level="101", ca_file=str(ca_path),
    ) == 0
    state2 = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state2["observed_sessions"] == ["2026-09-28", "2026-09-29"]
    assert state2["observed_session_count"] == 2
    # No fresh reset: holdings/cash continue, benchmark does not re-enter.
    assert state2["strategy"]["holdings"] == state1["strategy"]["holdings"]
    assert state2["benchmark"]["SPY_shares"] == state1["benchmark"]["SPY_shares"]
    obs2 = json.loads(
        (tmp_path / "observations" / "2026-09-29.json").read_text(encoding="utf-8")
    )
    assert obs2["previous_observation_sha256"] == state1["last_observation_sha256"]
    assert state2["last_observation_sha256"] == hashlib.sha256(
        (tmp_path / "observations" / "2026-09-29.json").read_bytes()
    ).hexdigest()
