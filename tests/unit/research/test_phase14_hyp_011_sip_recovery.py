"""Deterministic tests for HYP_011 prospective SIP window correction and recovery.

Validates the 12 non-negotiable requirements of the recovery contract:
1. single-session request cannot extend beyond canonical session close
2. free/delayed SIP provider eligibility boundary
3. pre-eligibility invocation fails closed with zero network
4. no IEX fallback
5. no retry/backfill of a formally missed prospective session
6. failed provider access produces zero observation/state mutation
7. observation append occurs only after all six required series are qualified
8. raw/split lineage remains ACWI/AGG/SPY x 2
9. simulated capital remains $100,000 accounting only
10. real capital remains $0
11. paper/live remain false
12. NO_REAL_ORDERS remains true
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List
import json
import pytest
import httpx

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_011_qual_client import (
    HYP011AlpacaClient,
    HYP011_SYMBOLS,
)
from acash.data.qualification.client import SipContractViolationError
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider
from acash.research.hyp_011 import shadow as SH
from acash.research.hyp_011.shadow_ops import (
    build_initial_state,
    validate_initial_state,
    verify_chain,
)
import sys
sys.path.insert(0, "scripts")
import process_hyp_011_prospective_shadow as runner


def _make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    listener: Callable[[], None] | None = None,
) -> HYP011AlpacaClient:
    return HYP011AlpacaClient(
        transport=httpx.MockTransport(handler),
        credential_provider=EnvAlpacaCredentialProvider(
            environ={"ACASH_ALPACA_API_KEY_ID": "mock_key", "ACASH_ALPACA_API_SECRET": "mock_sec"}
        ),
        http_attempt_listener=listener,
    )


def test_1_single_session_request_cannot_extend_beyond_canonical_session_close() -> None:
    """1. Single-session request end boundary is bound to canonical NYSE close, NEVER 23:59:59Z."""
    captured_requests: List[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "bars": [
                    {
                        "t": "2026-09-28T05:00:00Z",
                        "o": 100.0,
                        "h": 101.0,
                        "l": 99.0,
                        "c": 100.5,
                        "v": 1000,
                    }
                ]
            },
        )

    client = _make_client(_handler)
    cal = NyseCa1Calendar()
    session = date(2026, 9, 28)
    session_details = cal.get_session(session)
    assert session_details.close_utc == datetime(2026, 9, 28, 20, 0, 0, tzinfo=timezone.utc)

    # Executing when eligible (post provider delay):
    now_utc = datetime(2026, 9, 28, 20, 20, 0, tzinfo=timezone.utc)
    res = client.fetch_single_session(
        symbol="SPY",
        session=session,
        feed=MarketDataFeed.SIP,
        adjustment=PriceAdjustment.RAW,
        timeframe="1Day",
        now_utc=now_utc,
    )
    assert len(res.bars) == 1
    assert len(captured_requests) == 1
    req = captured_requests[0]
    query_params = dict(req.url.params)
    assert query_params["start"] == "2026-09-28T00:00:00Z"
    # Strict invariant: end parameter MUST equal canonical close (20:00:00Z), NOT 23:59:59Z.
    assert query_params["end"] == "2026-09-28T20:00:00Z"
    assert "23:59:59" not in query_params["end"]


def test_2_delayed_sip_provider_eligibility_boundary() -> None:
    """2. Free/delayed SIP provider eligibility boundary is strictly enforced."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 28)
    close_utc = cal.get_session(session).close_utc
    assert close_utc == datetime(2026, 9, 28, 20, 0, 0, tzinfo=timezone.utc)

    eligible_after = SH.provider_observation_eligible_after(session, cal)
    assert eligible_after == datetime(2026, 9, 28, 20, 15, 0, tzinfo=timezone.utc)

    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}))

    # At market close (20:00:00Z): BLOCKED
    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session("SPY", session, now_utc=close_utc)
    assert "market session incomplete" in str(exc_info.value)

    # At close + 10 minutes (20:10:00Z - attempt #0001 failure time): BLOCKED
    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session(
            "SPY", session, now_utc=close_utc + timedelta(minutes=10)
        )
    assert "provider SIP data not yet accessible" in str(exc_info.value)

    # At exact close + 15 minutes (20:15:00Z): strict fail-closed boundary BLOCKED
    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session("SPY", session, now_utc=eligible_after)
    assert "provider SIP data not yet accessible" in str(exc_info.value)

    # After provider eligibility (20:15:00.000001Z): strictly ELIGIBLE
    # (Client proceeds to network call)
    network_called = [False]

    def _handler(r: httpx.Request) -> httpx.Response:
        network_called[0] = True
        return httpx.Response(
            200,
            json={
                "bars": [
                    {
                        "t": "2026-09-28T05:00:00Z",
                        "o": 100.0,
                        "h": 101.0,
                        "l": 99.0,
                        "c": 100.5,
                        "v": 1000,
                    }
                ]
            },
        )

    client_ok = _make_client(_handler)
    res = client_ok.fetch_single_session(
        "SPY", session, now_utc=eligible_after + timedelta(microseconds=1)
    )
    assert network_called[0] is True
    assert len(res.bars) == 1


def test_3_pre_eligibility_invocation_fails_closed_zero_network() -> None:
    """3. Pre-eligibility invocation fails closed with zero network calls issued."""
    calls = [0]

    def _count() -> None:
        calls[0] += 1

    def _should_not_reach(r: httpx.Request) -> httpx.Response:
        raise AssertionError("Network must not be invoked prior to eligibility")

    client = _make_client(_should_not_reach, listener=_count)
    session = date(2026, 9, 28)

    # At 20:10:00Z: exactly when Attempt #0001 was dispatched
    with pytest.raises(DataContractError):
        client.fetch_single_session(
            "SPY",
            session,
            now_utc=datetime(2026, 9, 28, 20, 10, 0, tzinfo=timezone.utc),
        )
    assert calls[0] == 0


def test_4_no_iex_fallback() -> None:
    """4. No IEX fallback or other feed substitution permitted."""
    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}))
    session = date(2026, 9, 28)
    now_utc = datetime(2026, 9, 28, 20, 20, 0, tzinfo=timezone.utc)

    with pytest.raises(SipContractViolationError) as exc_info:
        client.fetch_single_session(
            "SPY",
            session,
            feed=MarketDataFeed.IEX,
            now_utc=now_utc,
        )
    assert "feed='sip'" in str(exc_info.value)


def test_5_no_retry_backfill_of_missed_prospective_session() -> None:
    """5. Retrying or backfilling an unobserved prior session is strictly forbidden."""
    state = SH.ShadowState(activation_session=date(2026, 9, 28))
    cal = NyseCa1Calendar()
    # Backfill attempt earlier than activation is rejected
    with pytest.raises(DataContractError) as exc_info:
        state.record_session(
            date(2026, 9, 25),
            cal,
            datetime(2026, 9, 29, 21, 0, 0, tzinfo=timezone.utc),
        )
    assert "SHADOW_EARLIER_THAN_ACTIVATION" in str(exc_info.value)


def test_6_failed_provider_access_produces_zero_observation_mutation(tmp_path: Path) -> None:
    """6. Failed provider access (e.g. HTTP 403) leaves state unmutated with zero disk files."""
    def _forbidden_handler(r: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": 40010001, "message": "SIP denied"})

    client = _make_client(_forbidden_handler)
    state_dir = tmp_path / "prospective"
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )

    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001",
        "--ordinal",
        "1",
    ]
    # Execute runner at 20:20Z (post eligibility) where provider returns 403
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 28, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
        )
    assert "Alpaca access forbidden (HTTP 403)" in str(exc_info.value)

    # Invariants: No directory, no observations, no state.json written to disk
    assert not (state_dir / "observations" / "2026-09-28.json").exists()
    assert not (state_dir / "state.json").exists()


def test_7_observation_append_requires_all_six_series_qualified(tmp_path: Path) -> None:
    """7. Observation append occurs ONLY after all 6 required series (3 symbols x 2 adjustments) qualify."""
    attempt_count = [0]

    def _flaky_handler(r: httpx.Request) -> httpx.Response:
        attempt_count[0] += 1
        # Fail on the 4th series
        if attempt_count[0] == 4:
            return httpx.Response(403, json={"code": 40010001, "message": "SIP denied"})
        return httpx.Response(
            200,
            json={
                "bars": [
                    {
                        "t": "2026-09-28T05:00:00Z",
                        "o": 100.0,
                        "h": 101.0,
                        "l": 99.0,
                        "c": 100.5,
                        "v": 1000,
                    }
                ]
            },
        )

    client = _make_client(_flaky_handler)
    state_dir = tmp_path / "prospective"
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001",
        "--ordinal",
        "1",
    ]
    with pytest.raises(DataContractError):
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 28, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
        )

    # Zero observation appended
    assert not (state_dir / "observations" / "2026-09-28.json").exists()
    assert not (state_dir / "state.json").exists()


def test_8_raw_split_lineage_remains_acwi_agg_spy() -> None:
    """8. Universe remains frozen to ACWI, AGG, SPY with split and raw adjustments."""
    assert HYP011_SYMBOLS == frozenset({"ACWI", "AGG", "SPY"})
    assert set(runner.SYMBOLS) == {"ACWI", "AGG", "SPY"}


def test_9_simulated_capital_accounting_only() -> None:
    """9. Simulated starting capital is $100,000.00 accounting only."""
    state = build_initial_state()
    assert state["starting_aum"] == "100000.00"
    assert Decimal(state["starting_aum"]) == Decimal("100000.00")
    validate_initial_state(state)


def test_10_real_capital_remains_zero() -> None:
    """10. Real capital remains strictly $0.00."""
    state = build_initial_state()
    assert state["locks"]["capital_authority_usd"] == "0.00"
    assert Decimal(state["locks"]["capital_authority_usd"]) == Decimal("0.00")


def test_11_paper_and_live_remain_false() -> None:
    """11. Paper and live trading authority are strictly False."""
    state = build_initial_state()
    assert state["locks"]["paper_authorized"] is False
    assert state["locks"]["live_authorized"] is False


def test_12_no_real_orders_remains_true() -> None:
    """12. NO_REAL_ORDERS lock remains strictly True."""
    state = build_initial_state()
    assert state["locks"]["no_real_orders"] is True
