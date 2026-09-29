"""Deterministic tests for HYP_011 prospective SIP window correction and recovery.

Validates the complete set of authority and invariant hardening requirements:
A. canonical Stage C-B manifest absent -> SHADOW_RECOVERY_BINDING_REQUIRED -> zero network
B. arbitrary CLI recovery-binding path is impossible / rejected
C. binding with activation_session but no binding_commit_utc -> rejected
D. binding with timestamp but no binding_commit_sha -> rejected
E. invalid SHA -> rejected
F. naive binding timestamp -> rejected
G. declared activation != calendar-derived activation -> rejected
H. valid timestamp + SHA + matching activation -> accepted locally
I. same-day 20:10Z failure boundary blocks retry (20:09:59Z, 20:10:00Z, 20:10:01Z, 20:20:00Z)
J. 20:20Z on failed date still cannot select 2026-09-28
K. Stage-C activation selected only from valid binding
L. validate_initial_state accepts new Stage-C activation when explicitly expected
M. validate_initial_state rejects mismatched activation
N. first committed observation remains ordinal 1
O. Observation 1 recovery dispatch attempt = 2
P. no IEX fallback
Q. provider eligibility remains strict close+15m
R. candidate schedule defaults to close+20m
S. winter and early-close schedules calendar-derived
T. provider 403 produces zero state/observation files
U. all six series required before append
V. paper/live false, capital zero, NO_REAL_ORDERS true
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


def make_valid_stage_c_binding_doc(
    commit_utc: str = "2026-09-29T12:00:00Z",
    activation_session: str = "2026-09-29",
    commit_sha: str = "d9608c0a2353bd5ed41943e5fb893ef9648089d2",
) -> Dict[str, Any]:
    return {
        "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
        "binding_commit_sha": commit_sha,
        "binding_commit_utc": commit_utc,
        "activation_session": activation_session,
        "scientific_prospective_boundary": "2026-09-25",
        "failed_dispatch_session": "2026-09-28",
        "failed_dispatch_attempt": 1,
        "next_observation_ordinal": 1,
        "next_dispatch_attempt": 2,
        "backfill_allowed": False,
        "retry_failed_session_allowed": False,
    }


def test_a_canonical_stage_c_b_manifest_absent_fails_closed_zero_network(tmp_path: Path) -> None:
    """A. canonical Stage C-B manifest absent -> SHADOW_RECOVERY_BINDING_REQUIRED -> zero network."""
    cal = NyseCa1Calendar()
    now_post_failure = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    state_dir = tmp_path / "prospective"

    # 1. Direct function call fails closed
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now_post_failure)
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    # 2. Dry run runner execution fails closed with zero network
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            [],
            _now_utc=now_post_failure,
            _state_dir=state_dir,
        )
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    # 3. Network runner execution fails closed with zero network
    network_attempts = [0]
    client = _make_client(
        lambda r: pytest.fail("Network must not be reached"),
        listener=lambda: network_attempts.__setitem__(0, network_attempts[0] + 1),
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


def test_b_arbitrary_cli_recovery_binding_path_is_rejected() -> None:
    """B. Arbitrary CLI recovery-binding path is impossible / rejected by CLI."""
    argv = ["--recovery-binding", "arbitrary/path/manifest.json"]
    with pytest.raises(SystemExit):
        runner.main(argv)

    argv2 = ["--recovery-binding-id", SH.STAGE_C_RECOVERY_BINDING_ID]
    with pytest.raises(SystemExit):
        runner.main(argv2)


def test_c_binding_with_activation_session_but_no_commit_utc_rejected(tmp_path: Path) -> None:
    """C. Binding with activation_session but no binding_commit_utc -> rejected."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    doc = make_valid_stage_c_binding_doc()
    del doc["binding_commit_utc"]
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=binding_path)
    assert "SHADOW_RECOVERY_BINDING_MISSING_FIELD: binding_commit_utc" in str(exc_info.value)


def test_d_binding_with_timestamp_but_no_commit_sha_rejected(tmp_path: Path) -> None:
    """D. Binding with timestamp but no binding_commit_sha -> rejected."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    doc = make_valid_stage_c_binding_doc()
    del doc["binding_commit_sha"]
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=binding_path)
    assert "SHADOW_RECOVERY_BINDING_MISSING_FIELD: binding_commit_sha" in str(exc_info.value)


def test_e_invalid_commit_sha_rejected(tmp_path: Path) -> None:
    """E. Invalid SHA -> rejected."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Truncated SHA (< 40 characters)
    doc = make_valid_stage_c_binding_doc(commit_sha="d9608c0a")
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=binding_path)
    assert "SHADOW_RECOVERY_BINDING_INVALID_SHA" in str(exc_info.value)

    # 2. 40 characters but non-hex
    doc["binding_commit_sha"] = "z" * 40
    binding_path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=binding_path)
    assert "SHADOW_RECOVERY_BINDING_INVALID_SHA" in str(exc_info.value)


def test_f_naive_binding_timestamp_rejected(tmp_path: Path) -> None:
    """F. Naive binding timestamp -> rejected."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    doc = make_valid_stage_c_binding_doc(commit_utc="2026-09-29T12:00:00")  # missing Z / tz
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=binding_path)
    assert "SHADOW_RECOVERY_BINDING_TIMESTAMP_NAIVE" in str(exc_info.value)


def test_g_declared_activation_mismatch_rejected(tmp_path: Path) -> None:
    """G. Declared activation != calendar-derived activation -> rejected."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    # Commit at 12:00 UTC on 9/29 derives 2026-09-29, but declared is forged as 2026-09-30
    doc = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T12:00:00Z",
        activation_session="2026-09-30",
    )
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=binding_path)
    assert "SHADOW_RECOVERY_BINDING_ACTIVATION_MISMATCH" in str(exc_info.value)


def test_h_valid_timestamp_and_sha_and_matching_activation_accepted(tmp_path: Path) -> None:
    """H. Valid timestamp + SHA + matching activation -> accepted locally."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Pre-open commit qualifies today
    doc1 = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T12:00:00Z",
        activation_session="2026-09-29",
    )
    p1 = tmp_path / "b1.json"
    p1.write_text(json.dumps(doc1), encoding="utf-8")
    assert SH.resolve_operational_activation(cal, now, stage_c_binding_path=p1) == date(2026, 9, 29)

    # Post-open commit qualifies next trading session (2026-09-30)
    doc2 = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T14:00:00Z",
        activation_session="2026-09-30",
    )
    p2 = tmp_path / "b2.json"
    p2.write_text(json.dumps(doc2), encoding="utf-8")
    assert SH.resolve_operational_activation(cal, now, stage_c_binding_path=p2) == date(2026, 9, 30)


def test_i_same_day_failure_boundary_blocks_retry() -> None:
    """I. Same-day 20:10Z failure boundary blocks retry at 20:09:59Z, 20:10:00Z, 20:10:01Z, 20:20:00Z."""
    cal = NyseCa1Calendar()

    # 1. 20:09:59Z: strictly before failed dispatch, Stage-B initial activation returned
    t_before = datetime(2026, 9, 28, 20, 9, 59, tzinfo=timezone.utc)
    assert SH.resolve_operational_activation(cal, t_before) == date(2026, 9, 28)

    # 2. 20:10:00Z: exact historical failure instant, strictly blocked
    t_boundary = datetime(2026, 9, 28, 20, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, t_boundary)
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    # 3. 20:10:01Z: strictly after historical failure instant, strictly blocked
    t_after_1s = datetime(2026, 9, 28, 20, 10, 1, tzinfo=timezone.utc)
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, t_after_1s)
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    # 4. 20:20:00Z: same-day operational schedule time, strictly blocked
    t_after_10m = datetime(2026, 9, 28, 20, 20, 0, tzinfo=timezone.utc)
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, t_after_10m)
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)


def test_j_2020z_on_failed_date_still_cannot_select_2026_09_28(tmp_path: Path) -> None:
    """J. 20:20Z on failed date still cannot select 2026-09-28."""
    state_dir = tmp_path / "prospective"
    t_2020 = datetime(2026, 9, 28, 20, 20, 0, tzinfo=timezone.utc)

    # Runner execution fails closed without selecting 2026-09-28
    with pytest.raises(DataContractError) as exc_info:
        runner.main([], _now_utc=t_2020, _state_dir=state_dir)
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)


def test_k_stage_c_activation_selected_only_from_valid_binding(tmp_path: Path) -> None:
    """K. Stage-C activation selected only from valid binding."""
    cal = NyseCa1Calendar()
    now_post_failure = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Without binding: fails closed
    with pytest.raises(DataContractError):
        SH.resolve_operational_activation(cal, now_post_failure)

    # With valid binding injected internally: selects Stage-C activation
    binding_file = tmp_path / "valid_stage_c.json"
    binding_file.write_text(
        json.dumps(make_valid_stage_c_binding_doc(
            commit_utc="2026-09-29T12:00:00Z",
            activation_session="2026-09-29",
        )),
        encoding="utf-8",
    )
    resolved = SH.resolve_operational_activation(
        cal, now_post_failure, stage_c_binding_path=binding_file
    )
    assert resolved == date(2026, 9, 29)
    next_session = runner._expected_next([], cal, activation_session=resolved)
    assert next_session == date(2026, 9, 29)
    assert next_session != date(2026, 9, 28)


def test_l_validate_initial_state_accepts_new_stage_c_activation() -> None:
    """L. validate_initial_state accepts new Stage-C activation when explicitly expected."""
    doc = build_initial_state(activation_session=date(2026, 9, 29))
    assert doc["activation_session"] == "2026-09-29"
    # Must pass without error when expected activation matches
    validate_initial_state(doc, expected_activation=date(2026, 9, 29))


def test_m_validate_initial_state_rejects_mismatched_activation() -> None:
    """M. validate_initial_state rejects mismatched activation."""
    doc = build_initial_state(activation_session=date(2026, 9, 29))
    with pytest.raises(DataContractError) as exc_info:
        validate_initial_state(doc, expected_activation=date(2026, 9, 30))
    assert "SHADOW_INITIAL_ACTIVATION" in str(exc_info.value)


def test_n_first_committed_observation_remains_ordinal_1(tmp_path: Path) -> None:
    """N. First committed observation remains ordinal 1."""
    state_dir = tmp_path / "prospective"
    verified = verify_chain(state_dir)
    assert len(verified.get("observed_sessions", [])) == 0
    assert verified.get("observed_session_count", 0) == 0
    expected_ordinal = len(verified.get("observed_sessions", [])) + 1
    assert expected_ordinal == 1

    # Pass wrong ordinal to runner -> fails pre-network
    binding_file = tmp_path / "stage_c.json"
    binding_file.write_text(
        json.dumps(make_valid_stage_c_binding_doc()),
        encoding="utf-8",
    )
    network_attempts = [0]
    client = _make_client(
        lambda r: pytest.fail("Network must not be reached"),
        listener=lambda: network_attempts.__setitem__(0, network_attempts[0] + 1),
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
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
            _stage_c_binding_path=binding_file,
        )
    assert "SHADOW_AUTHORIZATION_ORDINAL_MISMATCH" in str(exc_info.value)
    assert network_attempts[0] == 0


def test_o_observation_1_recovery_dispatch_attempt_is_2(tmp_path: Path) -> None:
    """O. Observation 1 recovery dispatch attempt = 2."""
    assert SH.FAILED_DISPATCH_ATTEMPT == 1
    assert SH.NEXT_DISPATCH_ATTEMPT == 2

    binding_file = tmp_path / "stage_c.json"
    binding_file.write_text(
        json.dumps(make_valid_stage_c_binding_doc()),
        encoding="utf-8",
    )
    network_attempts = [0]
    client = _make_client(
        lambda r: pytest.fail("Network must not be reached"),
        listener=lambda: network_attempts.__setitem__(0, network_attempts[0] + 1),
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
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=tmp_path / "prospective",
            _client=client,
            _credential_provider=dummy_prov,
            _stage_c_binding_path=binding_file,
        )
    assert "SHADOW_AUTHORIZATION_ATTEMPT_MISMATCH" in str(exc_info.value)
    assert network_attempts[0] == 0


def test_p_no_iex_fallback() -> None:
    """P. No IEX fallback."""
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


def test_q_provider_eligibility_remains_strict_close_plus_15m() -> None:
    """Q. Provider eligibility remains strict close+15m."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 28)
    close_utc = cal.get_session(session).close_utc
    assert close_utc is not None
    client = _make_client(lambda r: httpx.Response(200, json={"bars": []}))

    # 1. At exact close: incomplete
    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session("SPY", session, now_utc=close_utc)
    assert "market session incomplete" in str(exc_info.value)

    # 2. At close + 10m: inaccessible under 15m rule
    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session("SPY", session, now_utc=close_utc + timedelta(minutes=10))
    assert "provider SIP data not yet accessible" in str(exc_info.value)

    # 3. At exact close + 15m: fails closed (strict > inequality)
    eligible_after = SH.provider_observation_eligible_after(session, cal)
    assert eligible_after == close_utc + timedelta(minutes=15)
    with pytest.raises(DataContractError) as exc_info:
        client.fetch_single_session("SPY", session, now_utc=eligible_after)
    assert "provider SIP data not yet accessible" in str(exc_info.value)

    # 4. Strictly after close + 15m: query executes and query end is exactly canonical close
    captured_requests: List[httpx.Request] = []

    def _handler(req: httpx.Request) -> httpx.Response:
        captured_requests.append(req)
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

    client_valid = _make_client(_handler)
    res = client_valid.fetch_single_session(
        "SPY", session, now_utc=eligible_after + timedelta(microseconds=1)
    )
    assert len(res.bars) == 1
    assert len(captured_requests) == 1
    query_params = dict(captured_requests[0].url.params)
    assert query_params["start"] == "2026-09-28T00:00:00Z"
    assert query_params["end"] == "2026-09-28T20:00:00Z"
    assert "23:59:59" not in query_params["end"]


def test_r_candidate_schedule_defaults_to_close_plus_20m() -> None:
    """R. Candidate schedule defaults to close+20m."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 29)
    close_utc = cal.get_session(session).close_utc
    assert close_utc == datetime(2026, 9, 29, 20, 0, 0, tzinfo=timezone.utc)

    # Provider eligibility: close + 15m + 0m = 20:15 UTC
    elig = SH.provider_observation_eligible_after(session, cal)
    assert elig == datetime(2026, 9, 29, 20, 15, 0, tzinfo=timezone.utc)

    # Candidate operational schedule: close + 15m + 5m = 20:20 UTC
    sched = SH.candidate_schedule_time(session, cal)
    assert sched == datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc)


def test_s_winter_and_early_close_schedules_calendar_derived() -> None:
    """S. Winter and early-close schedules calendar-derived."""
    cal = NyseCa1Calendar()

    # 1. Early-close session: 2026-11-27 (close 13:00 EST -> 18:00 UTC)
    early_session = date(2026, 11, 27)
    early_close = cal.get_session(early_session).close_utc
    assert early_close == datetime(2026, 11, 27, 18, 0, 0, tzinfo=timezone.utc)
    early_sched = SH.candidate_schedule_time(early_session, cal)
    assert early_sched == datetime(2026, 11, 27, 18, 20, 0, tzinfo=timezone.utc)
    assert early_sched != datetime(2026, 11, 27, 20, 20, 0, tzinfo=timezone.utc)

    # 2. Winter session: 2026-12-15 (close 16:00 EST -> 21:00 UTC)
    winter_session = date(2026, 12, 15)
    winter_close = cal.get_session(winter_session).close_utc
    assert winter_close == datetime(2026, 12, 15, 21, 0, 0, tzinfo=timezone.utc)
    winter_sched = SH.candidate_schedule_time(winter_session, cal)
    assert winter_sched == datetime(2026, 12, 15, 21, 20, 0, tzinfo=timezone.utc)
    assert winter_sched != datetime(2026, 12, 15, 20, 20, 0, tzinfo=timezone.utc)


def test_t_provider_403_produces_zero_state_or_observation_files(tmp_path: Path) -> None:
    """T. Provider 403 produces zero state/observation files."""
    def _forbidden_handler(r: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": 40010001, "message": "SIP denied"})

    client = _make_client(_forbidden_handler)
    state_dir = tmp_path / "prospective"
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    binding_file = tmp_path / "stage_c.json"
    binding_file.write_text(
        json.dumps(make_valid_stage_c_binding_doc()),
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
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
            _stage_c_binding_path=binding_file,
        )
    assert "Alpaca access forbidden (HTTP 403)" in str(exc_info.value)
    assert not (state_dir / "observations" / "2026-09-29.json").exists()
    assert not (state_dir / "state.json").exists()


def test_u_all_six_series_required_before_append(tmp_path: Path) -> None:
    """U. All six series required before append."""
    attempt_count = [0]

    def _flaky_handler(r: httpx.Request) -> httpx.Response:
        attempt_count[0] += 1
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
        json.dumps(make_valid_stage_c_binding_doc()),
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
    ]
    with pytest.raises(DataContractError):
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
            _stage_c_binding_path=binding_file,
        )
    assert not (state_dir / "observations" / "2026-09-29.json").exists()
    assert not (state_dir / "state.json").exists()


def test_v_paper_live_false_capital_zero_no_real_orders() -> None:
    """V. Paper/live false, capital zero, NO_REAL_ORDERS true."""
    state = build_initial_state()
    assert state["starting_aum"] == "100000.00"
    assert Decimal(state["starting_aum"]) == Decimal("100000.00")
    validate_initial_state(state)
    assert state["locks"]["capital_authority_usd"] == "0.00"
    assert Decimal(state["locks"]["capital_authority_usd"]) == Decimal("0.00")
    assert state["locks"]["paper_authorized"] is False
    assert state["locks"]["live_authorized"] is False
    assert state["locks"]["no_real_orders"] is True
