"""Deterministic tests for HYP_011 prospective SIP window correction and recovery.

Validates the 20 non-negotiable requirements of the recovery contract:
A. 2026-09-28 failed session cannot be selected again.
B. No Stage-C-B binding -> zero network.
C. A future synthetic Stage-C binding derives next session exclusively from calendar + binding timestamp.
D. Sessions before new activation are missed/unobserved and count 0.
E. Observation ordinal remains 1 when committed count is 0.
F. Dispatch attempt is 2 after failed attempt 1.
G. Wrong observation ordinal fails pre-network.
H. Wrong dispatch attempt fails pre-network.
I. Wrong recovery-binding identity fails pre-network.
J. At close: provider inaccessible.
K. At close + 10m: inaccessible under 15m rule.
L. At exact +15m: fail closed.
M. After +15m: provider-eligible.
N. Query end exactly canonical close.
O. Early-close session derives correct close.
P. Winter session derives correct UTC close.
Q. No IEX fallback.
R. Provider 403 creates zero disk mutation.
S. All six series required before append.
T. No real/paper/live authority changes.
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
import process_hyp_011_prospective_shadow as runner  # type: ignore[import-not-found]


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


def test_a_failed_session_2026_09_28_cannot_be_selected_again(tmp_path: Path) -> None:
    """A. 2026-09-28 failed session cannot be selected again."""
    cal = NyseCa1Calendar()
    # Reproduce failure state: no state.json, no observations, current time after 2026-09-28 close
    now_post_failure = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    state_dir = tmp_path / "prospective"

    # 1. Without Stage-C binding: fails closed with SHADOW_RECOVERY_BINDING_REQUIRED
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now_post_failure)
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    # 2. In DRY RUN without binding: raises SHADOW_RECOVERY_BINDING_REQUIRED (never selects 2026-09-28)
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            [],
            _now_utc=now_post_failure,
            _state_dir=state_dir,
        )
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    # 3. With a Stage C binding to 2026-09-29 or later: _expected_next returns the new activation, NOT 2026-09-28
    synthetic_binding = tmp_path / "stage_c.json"
    synthetic_binding.write_text(
        json.dumps({
            "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
            "activation_session": "2026-09-29",
        }),
        encoding="utf-8",
    )
    resolved = SH.resolve_operational_activation(
        cal, now_post_failure, stage_c_binding_path=synthetic_binding
    )
    assert resolved == date(2026, 9, 29)
    next_session = runner._expected_next([], cal, activation_session=resolved)
    assert next_session == date(2026, 9, 29)
    assert next_session != date(2026, 9, 28)

    # 4. Any direct attempt to record 2026-09-28 under the new activation is rejected as backfill
    state = SH.ShadowState(activation_session=resolved)
    with pytest.raises(DataContractError) as exc_info:
        state.record_session(
            date(2026, 9, 28),
            cal,
            datetime(2026, 9, 29, 21, 0, 0, tzinfo=timezone.utc),
        )
    assert "SHADOW_EARLIER_THAN_ACTIVATION" in str(exc_info.value)


def test_b_no_stage_c_b_binding_zero_network(tmp_path: Path) -> None:
    """B. No Stage-C-B binding -> zero network requests issued."""
    network_attempts = [0]

    def _listener() -> None:
        network_attempts[0] += 1

    def _should_not_reach(r: httpx.Request) -> httpx.Response:
        raise AssertionError("Network must not be reached without Stage-C binding")

    client = _make_client(_should_not_reach, listener=_listener)
    state_dir = tmp_path / "prospective"
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    now_post_failure = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
        "--ordinal",
        "1",
        "--dispatch-attempt",
        "2",
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=now_post_failure,
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
        )
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)
    assert network_attempts[0] == 0


def test_c_synthetic_stage_c_binding_derives_next_session_from_calendar_and_commit(tmp_path: Path) -> None:
    """C. A future synthetic Stage-C binding derives next session exclusively from calendar + commit timestamp."""
    cal = NyseCa1Calendar()
    # Case 1: Commit at 14:00 UTC on 2026-09-29 is AFTER NYSE open (13:30 UTC).
    # The first NYSE open strictly after this timestamp is 2026-09-30 (13:30 UTC).
    binding_file = tmp_path / "binding_after_open.json"
    binding_file.write_text(
        json.dumps({
            "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
            "binding_commit_utc": "2026-09-29T14:00:00Z",
        }),
        encoding="utf-8",
    )
    act1 = SH.resolve_operational_activation(
        cal, datetime(2026, 9, 29, 15, 0, 0, tzinfo=timezone.utc), stage_c_binding_path=binding_file
    )
    assert act1 == date(2026, 9, 30)

    # Case 2: Commit at 12:00 UTC on 2026-09-29 is BEFORE NYSE open (13:30 UTC).
    # The first NYSE open strictly after this timestamp is 2026-09-29 (13:30 UTC).
    binding_file2 = tmp_path / "binding_before_open.json"
    binding_file2.write_text(
        json.dumps({
            "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
            "binding_commit_utc": "2026-09-29T12:00:00Z",
        }),
        encoding="utf-8",
    )
    act2 = SH.resolve_operational_activation(
        cal, datetime(2026, 9, 29, 12, 30, 0, tzinfo=timezone.utc), stage_c_binding_path=binding_file2
    )
    assert act2 == date(2026, 9, 29)


def test_d_sessions_before_new_activation_are_missed_unobserved_and_count_zero() -> None:
    """D. Sessions before new activation are missed/unobserved and count 0."""
    cal = NyseCa1Calendar()
    # For new activation 2026-09-29: missed interval [2026-09-25, 2026-09-29) contains 9/25 and 9/28
    missed_29 = SH.missed_unobserved_sessions(cal, date(2026, 9, 29))
    assert missed_29 == [date(2026, 9, 25), date(2026, 9, 28)]

    # For new activation 2026-09-30: missed interval [2026-09-25, 2026-09-30) contains 9/25, 9/28, 9/29
    missed_30 = SH.missed_unobserved_sessions(cal, date(2026, 9, 30))
    assert missed_30 == [date(2026, 9, 25), date(2026, 9, 28), date(2026, 9, 29)]

    # State rejects any attempt to record sessions in the missed interval
    state = SH.ShadowState(activation_session=date(2026, 9, 30))
    for s in missed_30:
        with pytest.raises(DataContractError) as exc_info:
            state.record_session(s, cal, datetime(2026, 9, 30, 21, 0, 0, tzinfo=timezone.utc))
        assert "SHADOW_EARLIER_THAN_ACTIVATION" in str(exc_info.value)
    assert len(state.observed_sessions) == 0


def test_e_observation_ordinal_remains_1_when_committed_count_is_0(tmp_path: Path) -> None:
    """E. Observation ordinal remains 1 when committed count is 0."""
    state_dir = tmp_path / "prospective"
    verified = verify_chain(state_dir)
    assert len(verified.get("observed_sessions", [])) == 0
    assert verified.get("observed_session_count", 0) == 0
    expected_ordinal = len(verified.get("observed_sessions", [])) + 1
    assert expected_ordinal == 1


def test_f_dispatch_attempt_is_2_after_failed_attempt_1() -> None:
    """F. Dispatch attempt is 2 after failed attempt 1."""
    assert SH.FAILED_DISPATCH_ATTEMPT == 1
    assert SH.NEXT_DISPATCH_ATTEMPT == 2
    assert SH.FAILED_ACTIVATION_SESSION == date(2026, 9, 28)


def test_g_wrong_observation_ordinal_fails_prenetwork(tmp_path: Path) -> None:
    """G. Wrong observation ordinal fails pre-network."""
    network_attempts = [0]
    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}), listener=lambda: network_attempts.__setitem__(0, network_attempts[0] + 1))
    binding_file = tmp_path / "stage_c.json"
    binding_file.write_text(
        json.dumps({
            "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
            "activation_session": "2026-09-29",
        }),
        encoding="utf-8",
    )
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0002_ATTEMPT_0002",
        "--ordinal",
        "2",  # WRONG: expected 1
        "--dispatch-attempt",
        "2",
        "--recovery-binding",
        str(binding_file),
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=tmp_path / "prospective",
            _client=client,
            _credential_provider=dummy_prov,
        )
    assert "SHADOW_AUTHORIZATION_ORDINAL_MISMATCH" in str(exc_info.value)
    assert network_attempts[0] == 0


def test_h_wrong_dispatch_attempt_fails_prenetwork(tmp_path: Path) -> None:
    """H. Wrong dispatch attempt fails pre-network."""
    network_attempts = [0]
    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}), listener=lambda: network_attempts.__setitem__(0, network_attempts[0] + 1))
    binding_file = tmp_path / "stage_c.json"
    binding_file.write_text(
        json.dumps({
            "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
            "activation_session": "2026-09-29",
        }),
        encoding="utf-8",
    )
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
        "--ordinal",
        "1",
        "--dispatch-attempt",
        "1",  # WRONG: expected 2 under recovery
        "--recovery-binding",
        str(binding_file),
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=tmp_path / "prospective",
            _client=client,
            _credential_provider=dummy_prov,
        )
    assert "SHADOW_AUTHORIZATION_ATTEMPT_MISMATCH" in str(exc_info.value)
    assert network_attempts[0] == 0


def test_i_wrong_recovery_binding_identity_fails_prenetwork(tmp_path: Path) -> None:
    """I. Wrong recovery-binding identity fails pre-network."""
    network_attempts = [0]
    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}), listener=lambda: network_attempts.__setitem__(0, network_attempts[0] + 1))
    binding_file = tmp_path / "corrupt_binding.json"
    binding_file.write_text(
        json.dumps({
            "binding_id": "WRONG_BINDING_IDENTIFIER",
            "activation_session": "2026-09-29",
        }),
        encoding="utf-8",
    )
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
        "--ordinal",
        "1",
        "--dispatch-attempt",
        "2",
        "--recovery-binding",
        str(binding_file),
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=tmp_path / "prospective",
            _client=client,
            _credential_provider=dummy_prov,
        )
    assert "SHADOW_RECOVERY_BINDING_ID_MISMATCH" in str(exc_info.value)
    assert network_attempts[0] == 0


def test_j_at_close_provider_inaccessible() -> None:
    """J. At close: provider inaccessible."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 28)
    close_utc = cal.get_session(session).close_utc
    assert close_utc is not None
    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}))

    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session("SPY", session, now_utc=close_utc)
    assert "market session incomplete" in str(exc_info.value)


def test_k_at_close_plus_10m_inaccessible_under_15m_rule() -> None:
    """K. At close + 10m: inaccessible under 15m rule."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 28)
    close_utc = cal.get_session(session).close_utc
    assert close_utc is not None
    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}))

    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session(
            "SPY", session, now_utc=close_utc + timedelta(minutes=10)
        )
    assert "provider SIP data not yet accessible" in str(exc_info.value)


def test_l_at_exact_close_plus_15m_fails_closed() -> None:
    """L. At exact +15m: fail closed (strict > inequality)."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 28)
    eligible_after = SH.provider_observation_eligible_after(session, cal)
    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}))

    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session("SPY", session, now_utc=eligible_after)
    assert "provider SIP data not yet accessible" in str(exc_info.value)


def test_m_after_close_plus_15m_provider_eligible() -> None:
    """M. After +15m: provider-eligible."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 28)
    eligible_after = SH.provider_observation_eligible_after(session, cal)
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

    client = _make_client(_handler)
    res = client.fetch_single_session(
        "SPY", session, now_utc=eligible_after + timedelta(microseconds=1)
    )
    assert network_called[0] is True
    assert len(res.bars) == 1


def test_n_query_end_exactly_canonical_close() -> None:
    """N. Query end exactly canonical close."""
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
    now_utc = datetime(2026, 9, 28, 20, 20, 0, tzinfo=timezone.utc)
    client.fetch_single_session(
        symbol="SPY",
        session=session,
        feed=MarketDataFeed.SIP,
        adjustment=PriceAdjustment.RAW,
        timeframe="1Day",
        now_utc=now_utc,
    )
    assert len(captured_requests) == 1
    req = captured_requests[0]
    query_params = dict(req.url.params)
    assert query_params["start"] == "2026-09-28T00:00:00Z"
    assert query_params["end"] == "2026-09-28T20:00:00Z"
    assert "23:59:59" not in query_params["end"]


def test_o_early_close_session_derives_correct_close() -> None:
    """O. Early-close session derives correct close."""
    cal = NyseCa1Calendar()
    # 2026-11-27 is Day after Thanksgiving (early close 13:00 EST -> 18:00 UTC)
    early_session = date(2026, 11, 27)
    session_details = cal.get_session(early_session)
    assert session_details.close_utc == datetime(2026, 11, 27, 18, 0, 0, tzinfo=timezone.utc)

    # Candidate schedule derives 18:00 UTC + 15m delay + 5m margin = 18:20 UTC
    sched = SH.candidate_schedule_time(
        early_session, cal, operational_margin=timedelta(minutes=5)
    )
    assert sched == datetime(2026, 11, 27, 18, 20, 0, tzinfo=timezone.utc)
    assert sched != datetime(2026, 11, 27, 20, 20, 0, tzinfo=timezone.utc)


def test_p_winter_session_derives_correct_utc_close() -> None:
    """P. Winter session derives correct UTC close (proving 20:20 UTC is not universal)."""
    cal = NyseCa1Calendar()
    # 2026-12-15 is regular session during Standard Time (EST = UTC-5: close 16:00 EST -> 21:00 UTC)
    winter_session = date(2026, 12, 15)
    session_details = cal.get_session(winter_session)
    assert session_details.close_utc == datetime(2026, 12, 15, 21, 0, 0, tzinfo=timezone.utc)

    # Candidate schedule derives 21:00 UTC + 15m delay + 5m margin = 21:20 UTC
    sched = SH.candidate_schedule_time(
        winter_session, cal, operational_margin=timedelta(minutes=5)
    )
    assert sched == datetime(2026, 12, 15, 21, 20, 0, tzinfo=timezone.utc)
    assert sched != datetime(2026, 12, 15, 20, 20, 0, tzinfo=timezone.utc)


def test_q_no_iex_fallback() -> None:
    """Q. No IEX fallback."""
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


def test_r_provider_403_creates_zero_disk_mutation(tmp_path: Path) -> None:
    """R. Provider 403 creates zero disk mutation."""
    def _forbidden_handler(r: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": 40010001, "message": "SIP denied"})

    client = _make_client(_forbidden_handler)
    state_dir = tmp_path / "prospective"
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    binding_file = tmp_path / "stage_c.json"
    binding_file.write_text(
        json.dumps({
            "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
            "activation_session": "2026-09-29",
        }),
        encoding="utf-8",
    )

    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
        "--ordinal",
        "1",
        "--dispatch-attempt",
        "2",
        "--recovery-binding",
        str(binding_file),
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
        )
    assert "Alpaca access forbidden (HTTP 403)" in str(exc_info.value)
    assert not (state_dir / "observations" / "2026-09-29.json").exists()
    assert not (state_dir / "state.json").exists()


def test_s_all_six_series_required_before_append(tmp_path: Path) -> None:
    """S. All six series required before append."""
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
                        "t": "2026-09-29T05:00:00Z",
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
    binding_file = tmp_path / "stage_c.json"
    binding_file.write_text(
        json.dumps({
            "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
            "activation_session": "2026-09-29",
        }),
        encoding="utf-8",
    )
    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
        "--ordinal",
        "1",
        "--dispatch-attempt",
        "2",
        "--recovery-binding",
        str(binding_file),
    ]
    with pytest.raises(DataContractError):
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
        )
    assert not (state_dir / "observations" / "2026-09-29.json").exists()
    assert not (state_dir / "state.json").exists()


def test_t_no_real_paper_live_authority_changes() -> None:
    """T. No real/paper/live authority changes."""
    state = build_initial_state()
    assert state["starting_aum"] == "100000.00"
    assert Decimal(state["starting_aum"]) == Decimal("100000.00")
    validate_initial_state(state)
    assert state["locks"]["capital_authority_usd"] == "0.00"
    assert Decimal(state["locks"]["capital_authority_usd"]) == Decimal("0.00")
    assert state["locks"]["paper_authorized"] is False
    assert state["locks"]["live_authorized"] is False
    assert state["locks"]["no_real_orders"] is True
