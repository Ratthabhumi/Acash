"""Deterministic tests for HYP_011 prospective SIP window correction and recovery.

Test Matrix (Sections 13 & 4):
A. no Stage C-B -> zero network
B. same-day failed-session retry blocked
C. arbitrary CLI binding impossible
D. missing binding commit timestamp rejected
E. missing/invalid SHA rejected
F. activation derived from commit timestamp
G. state activation cannot redefine canonical authority
H. tampered state activation blocks pre-network (circular trust elimination)
I. Stage C binding byte digest deterministic
J. observation seals binding ID/digest/SHA/timestamp/activation
K. state persists activation authority identity after first recovered observation
L. same authority accepted on next invocation
M. changed binding contents rejected against persisted authority
N. changed binding commit SHA rejected
O. no IEX fallback
P. provider query end = canonical close
Q. provider eligibility = strict close + 15m
R. candidate dispatch = close + 20m
S. DST/winter/early-close calendar derivation
T. provider 403 -> zero observation/state commit
U. all six series required before append
V. paper/live false, real capital 0, NO_REAL_ORDERS true
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List
import hashlib
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
    append_observation,
    build_initial_state,
    validate_initial_state,
    verify_chain,
)
import importlib.util


def _load_script_module(name: str) -> Any:
    script_file = Path(__file__).resolve().parents[3] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_file)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner = _load_script_module("process_hyp_011_prospective_shadow")
builder = _load_script_module("build_stage_c_b_recovery_manifest")


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
        "manifest_version": 1,
        "binding_id": SH.STAGE_C_RECOVERY_BINDING_ID,
        "description": "Post-merge Stage C-B operational re-activation binding for HYP_011 prospective shadow.",
        "scientific_prospective_boundary": "2026-09-25",
        "binding_commit_sha": commit_sha,
        "binding_commit_utc": commit_utc,
        "activation_session": activation_session,
        "failed_dispatch_session": "2026-09-28",
        "failed_dispatch_attempt": 1,
        "failed_dispatch_at_utc": "2026-09-28T20:10:00Z",
        "failed_session_classification": "MISSED_UNOBSERVED_DUE_TO_PROVIDER_ACCESS_BLOCK",
        "missed_unobserved_sessions": ["2026-09-25", "2026-09-28"],
        "next_observation_ordinal": 1,
        "next_dispatch_attempt": 2,
        "backfill_allowed": False,
        "retry_failed_session_allowed": False,
        "locks": {
            "paper_trading": False,
            "live_trading": False,
            "real_capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
    }


def _write_binding(path: Path, doc: Dict[str, Any]) -> SH.StageCRecoveryAuthority:
    cal = NyseCa1Calendar()
    raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return SH.load_stage_c_recovery_authority(cal, path)


# -----------------------------------------------------------------------------
# A. no Stage C-B -> zero network
# -----------------------------------------------------------------------------
def test_a_canonical_stage_c_b_manifest_absent_fails_closed_zero_network(
    tmp_path: Path, stage_c_b_absent: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A. Canonical Stage C-B manifest absent -> SHADOW_RECOVERY_BINDING_REQUIRED -> zero network."""
    cal = NyseCa1Calendar()
    now_post_failure = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    state_dir = tmp_path / "prospective"
    monkeypatch.setattr(runner, "STAGE_C_RECOVERY_BINDING_PATH", stage_c_b_absent)

    # 1. Direct function call fails closed
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now_post_failure)
    assert "SHADOW_RECOVERY_BINDING_REQUIRED" in str(exc_info.value)

    # 2. Dry run runner execution fails closed with zero network
    with pytest.raises(DataContractError) as exc_info:
        runner.main([], _now_utc=now_post_failure, _state_dir=state_dir)
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


# -----------------------------------------------------------------------------
# B. same-day failed-session retry blocked
# -----------------------------------------------------------------------------
def test_b_same_day_failure_boundary_blocks_retry(stage_c_b_absent: Path) -> None:
    """B. Same-day 20:10Z failure boundary blocks retry at 20:09:59Z, 20:10:00Z, 20:10:01Z, 20:20:00Z."""
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


# -----------------------------------------------------------------------------
# C. arbitrary CLI binding impossible
# -----------------------------------------------------------------------------
def test_c_arbitrary_cli_recovery_binding_path_is_rejected() -> None:
    """C. Arbitrary CLI recovery-binding path is rejected by CLI argument parser."""
    argv = ["--recovery-binding", "arbitrary/path/manifest.json"]
    with pytest.raises(SystemExit):
        runner.main(argv)

    argv2 = ["--recovery-binding-id", SH.STAGE_C_RECOVERY_BINDING_ID]
    with pytest.raises(SystemExit):
        runner.main(argv2)


# -----------------------------------------------------------------------------
# D. missing binding commit timestamp rejected
# -----------------------------------------------------------------------------
def test_d_missing_binding_commit_timestamp_rejected(tmp_path: Path) -> None:
    """D. Missing or naive binding commit timestamp -> rejected."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Missing field
    doc = make_valid_stage_c_binding_doc()
    del doc["binding_commit_utc"]
    p1 = tmp_path / "missing_ts.json"
    p1.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=p1)
    assert "SHADOW_RECOVERY_BINDING_MISSING_FIELD: binding_commit_utc" in str(exc_info.value)

    # 2. Naive timestamp
    doc_naive = make_valid_stage_c_binding_doc(commit_utc="2026-09-29T12:00:00")
    p2 = tmp_path / "naive_ts.json"
    p2.write_text(json.dumps(doc_naive), encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=p2)
    assert "SHADOW_RECOVERY_BINDING_TIMESTAMP_NAIVE" in str(exc_info.value)


# -----------------------------------------------------------------------------
# E. missing/invalid SHA rejected
# -----------------------------------------------------------------------------
def test_e_missing_or_invalid_sha_rejected(tmp_path: Path) -> None:
    """E. Missing or invalid commit SHA -> rejected."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Missing SHA
    doc1 = make_valid_stage_c_binding_doc()
    del doc1["binding_commit_sha"]
    p1 = tmp_path / "missing_sha.json"
    p1.write_text(json.dumps(doc1), encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=p1)
    assert "SHADOW_RECOVERY_BINDING_MISSING_FIELD: binding_commit_sha" in str(exc_info.value)

    # 2. Truncated SHA (< 40 characters)
    doc2 = make_valid_stage_c_binding_doc(commit_sha="d9608c0a")
    p2 = tmp_path / "trunc_sha.json"
    p2.write_text(json.dumps(doc2), encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=p2)
    assert "SHADOW_RECOVERY_BINDING_INVALID_SHA" in str(exc_info.value)

    # 3. 40 characters but non-hex
    doc3 = make_valid_stage_c_binding_doc(commit_sha="z" * 40)
    p3 = tmp_path / "nonhex_sha.json"
    p3.write_text(json.dumps(doc3), encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=p3)
    assert "SHADOW_RECOVERY_BINDING_INVALID_SHA" in str(exc_info.value)


# -----------------------------------------------------------------------------
# F. activation derived from commit timestamp
# -----------------------------------------------------------------------------
def test_f_activation_derived_from_commit_timestamp(tmp_path: Path) -> None:
    """F. Activation derived strictly from commit timestamp via NYSE calendar."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Pre-open commit qualifies today (2026-09-29)
    doc1 = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T12:00:00Z",
        activation_session="2026-09-29",
    )
    p1 = tmp_path / "b1.json"
    _write_binding(p1, doc1)
    assert SH.resolve_operational_activation(cal, now, stage_c_binding_path=p1) == date(2026, 9, 29)

    # Post-open commit qualifies next trading session (2026-09-30)
    doc2 = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T14:00:00Z",
        activation_session="2026-09-30",
    )
    p2 = tmp_path / "b2.json"
    _write_binding(p2, doc2)
    assert SH.resolve_operational_activation(cal, now, stage_c_binding_path=p2) == date(2026, 9, 30)

    # Declared mismatch rejected
    doc3 = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T12:00:00Z",
        activation_session="2026-09-30",  # Mismatch: derived is 2026-09-29
    )
    p3 = tmp_path / "b3.json"
    p3.write_text(json.dumps(doc3), encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        SH.resolve_operational_activation(cal, now, stage_c_binding_path=p3)
    assert "SHADOW_RECOVERY_BINDING_ACTIVATION_MISMATCH" in str(exc_info.value)


# -----------------------------------------------------------------------------
# G. state activation cannot redefine canonical authority
# -----------------------------------------------------------------------------
def test_g_state_activation_cannot_redefine_canonical_authority(tmp_path: Path) -> None:
    """G. State activation cannot redefine canonical authority; authority derives from Stage C-B."""
    cal = NyseCa1Calendar()
    now = datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc)
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T12:00:00Z",
        activation_session="2026-09-29",
    )
    _write_binding(binding_file, doc)

    # resolve_operational_activation returns canonical binding activation, regardless of state
    resolved = SH.resolve_operational_activation(
        calendar=cal,
        now_utc=now,
        stage_c_binding_path=binding_file,
        committed_observations=5,  # even with prior observations
    )
    assert resolved == date(2026, 9, 29)


# -----------------------------------------------------------------------------
# H. tampered state activation blocks pre-network (Section 4 regression test)
# -----------------------------------------------------------------------------
def test_h_tampered_state_activation_blocks_pre_network(tmp_path: Path) -> None:
    """H. Tampered state.json activation_session fails closed before network execution.

    Deterministic regression test (Section 4):
    1. create valid synthetic Stage C-B binding deriving activation 2026-09-29
    2. create a state/observation chain representing at least one committed observation under 2026-09-29
    3. tamper ONLY: state.json["activation_session"] = "2026-09-30"
    4. invoke dry-run / verification path
    Required: FAIL CLOSED with BLOCK_SHADOW_STATE_INTEGRITY: activation_session
    Network requests: 0
    """
    cal = NyseCa1Calendar()
    state_dir = tmp_path / "prospective"
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T12:00:00Z",
        activation_session="2026-09-29",
    )
    auth = _write_binding(binding_file, doc)

    # 1. Commit observation 1 under activation 2026-09-29
    obs1: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": "2026-09-29",
        "authority": {
            "activation_binding": str(binding_file),
            "activation_binding_id": auth.binding_id,
            "activation_binding_sha256": auth.manifest_sha256,
            "activation_binding_commit_sha": auth.binding_commit_sha,
            "activation_binding_commit_utc": auth.binding_commit_utc,
            "operational_activation_session": "2026-09-29",
            "authorization": "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
            "ordinal": 1,
            "dispatch_attempt": 2,
        },
    }
    append_observation(
        state_dir=state_dir,
        session=date(2026, 9, 29),
        observation=obs1,
        previous_sha=None,
        activation_session=date(2026, 9, 29),
        recovery_authority=auth,
        extra_state={"last_closes_raw": {}, "last_closes_split": {}},
    )

    # Verify chain is clean before tamper
    v_clean = verify_chain(state_dir, expected_activation=date(2026, 9, 29), expected_recovery_authority=auth)
    assert v_clean["activation_session"] == "2026-09-29"

    # 2. Tamper ONLY state.json["activation_session"] = "2026-09-30"
    state_path = state_dir / "state.json"
    state_data = json.loads(state_path.read_text(encoding="utf-8"))
    state_data["activation_session"] = "2026-09-30"
    state_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

    # 3. Dry-run verification path fails closed
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            [],
            _now_utc=datetime(2026, 9, 30, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _stage_c_binding_path=binding_file,
        )
    assert "BLOCK_SHADOW_STATE_INTEGRITY: activation_session" in str(exc_info.value)

    # 4. Network runner verification fails closed with ZERO network requests
    network_attempts = [0]
    client = _make_client(
        lambda r: pytest.fail("Network must not be reached on state integrity failure"),
        listener=lambda: network_attempts.__setitem__(0, network_attempts[0] + 1),
    )
    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )
    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0002",
        "--ordinal",
        "2",
        "--dispatch-attempt",
        "1",
    ]
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            argv,
            _now_utc=datetime(2026, 9, 30, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=client,
            _credential_provider=dummy_prov,
            _stage_c_binding_path=binding_file,
        )
    assert "BLOCK_SHADOW_STATE_INTEGRITY: activation_session" in str(exc_info.value)
    assert network_attempts[0] == 0


# -----------------------------------------------------------------------------
# I. Stage C binding byte digest deterministic
# -----------------------------------------------------------------------------
def test_i_stage_c_binding_byte_digest_deterministic(tmp_path: Path) -> None:
    """I. Stage C binding byte digest is computed over raw on-disk bytes deterministically."""
    cal = NyseCa1Calendar()
    doc = make_valid_stage_c_binding_doc()
    p = tmp_path / "binding.json"
    auth = _write_binding(p, doc)

    expected_sha = hashlib.sha256(p.read_bytes()).hexdigest()
    assert auth.manifest_sha256 == expected_sha
    assert len(auth.manifest_sha256) == 64


# -----------------------------------------------------------------------------
# J. observation seals binding ID/digest/SHA/timestamp/activation
# -----------------------------------------------------------------------------
def test_j_observation_seals_recovery_authority_lineage(tmp_path: Path) -> None:
    """J. Observation artifact seals complete recovery authority lineage."""
    cal = NyseCa1Calendar()
    state_dir = tmp_path / "prospective"
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc(
        commit_utc="2026-09-29T12:00:00Z",
        activation_session="2026-09-29",
        commit_sha="d9608c0a2353bd5ed41943e5fb893ef9648089d2",
    )
    auth = _write_binding(binding_file, doc)

    def _mock_handler(req: httpx.Request) -> httpx.Response:
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

    client = _make_client(_mock_handler)
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
    code = runner.main(
        argv,
        _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
        _state_dir=state_dir,
        _client=client,
        _credential_provider=dummy_prov,
        _stage_c_binding_path=binding_file,
    )
    assert code == 0

    obs_file = state_dir / "observations" / "2026-09-29.json"
    assert obs_file.exists()
    obs_doc = json.loads(obs_file.read_text(encoding="utf-8"))

    authority = obs_doc["authority"]
    assert authority["activation_binding"] == str(binding_file)
    assert authority["activation_binding_id"] == SH.STAGE_C_RECOVERY_BINDING_ID
    assert authority["activation_binding_sha256"] == auth.manifest_sha256
    assert authority["activation_binding_commit_sha"] == "d9608c0a2353bd5ed41943e5fb893ef9648089d2"
    assert authority["activation_binding_commit_utc"] == "2026-09-29T12:00:00+00:00"
    assert authority["operational_activation_session"] == "2026-09-29"
    assert authority["authorization"] == "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002"
    assert authority["ordinal"] == 1
    assert authority["dispatch_attempt"] == 2


# -----------------------------------------------------------------------------
# K. state persists activation authority identity after first recovered observation
# -----------------------------------------------------------------------------
def test_k_state_persists_activation_authority_identity(tmp_path: Path) -> None:
    """K. State persists activation authority identity after first recovered observation."""
    cal = NyseCa1Calendar()
    state_dir = tmp_path / "prospective"
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc()
    auth = _write_binding(binding_file, doc)

    # Run observation 1
    def _mock_handler(req: httpx.Request) -> httpx.Response:
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

    client = _make_client(_mock_handler)
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
    runner.main(
        argv,
        _now_utc=datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc),
        _state_dir=state_dir,
        _client=client,
        _credential_provider=dummy_prov,
        _stage_c_binding_path=binding_file,
    )

    state_file = state_dir / "state.json"
    state_doc = json.loads(state_file.read_text(encoding="utf-8"))
    assert state_doc["activation_authority_id"] == SH.STAGE_C_RECOVERY_BINDING_ID
    assert state_doc["activation_authority_sha256"] == auth.manifest_sha256
    assert state_doc["activation_commit_sha"] == auth.binding_commit_sha


# -----------------------------------------------------------------------------
# L. same authority accepted on next invocation
# -----------------------------------------------------------------------------
def test_l_same_authority_accepted_on_next_invocation(tmp_path: Path) -> None:
    """L. Subsequent invocation using the same binding passes local authority checks."""
    cal = NyseCa1Calendar()
    state_dir = tmp_path / "prospective"
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc()
    auth = _write_binding(binding_file, doc)

    # Set up state with observation 1 committed
    obs1: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": "2026-09-29",
        "authority": {
            "activation_binding": str(binding_file),
            "activation_binding_id": auth.binding_id,
            "activation_binding_sha256": auth.manifest_sha256,
            "activation_binding_commit_sha": auth.binding_commit_sha,
            "activation_binding_commit_utc": auth.binding_commit_utc,
            "operational_activation_session": "2026-09-29",
            "authorization": "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
            "ordinal": 1,
            "dispatch_attempt": 2,
        },
    }
    append_observation(
        state_dir=state_dir,
        session=date(2026, 9, 29),
        observation=obs1,
        previous_sha=None,
        activation_session=date(2026, 9, 29),
        recovery_authority=auth,
        extra_state={"last_closes_raw": {}, "last_closes_split": {}},
    )

    # Next invocation (pretest for observation 2) succeeds
    code = runner.main(
        [],
        _now_utc=datetime(2026, 9, 30, 20, 20, 0, tzinfo=timezone.utc),
        _state_dir=state_dir,
        _stage_c_binding_path=binding_file,
    )
    assert code == 0


# -----------------------------------------------------------------------------
# M. changed binding contents rejected against persisted authority
# -----------------------------------------------------------------------------
def test_m_changed_binding_contents_rejected_against_persisted_authority(tmp_path: Path) -> None:
    """M. Modified binding bytes at same path are rejected against persisted state authority pre-network."""
    cal = NyseCa1Calendar()
    state_dir = tmp_path / "prospective"
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc()
    auth = _write_binding(binding_file, doc)

    # Observation 1 committed under original binding
    obs1: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": "2026-09-29",
        "authority": {
            "activation_binding": str(binding_file),
            "activation_binding_id": auth.binding_id,
            "activation_binding_sha256": auth.manifest_sha256,
            "activation_binding_commit_sha": auth.binding_commit_sha,
            "activation_binding_commit_utc": auth.binding_commit_utc,
            "operational_activation_session": "2026-09-29",
            "authorization": "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
            "ordinal": 1,
            "dispatch_attempt": 2,
        },
    }
    append_observation(
        state_dir=state_dir,
        session=date(2026, 9, 29),
        observation=obs1,
        previous_sha=None,
        activation_session=date(2026, 9, 29),
        recovery_authority=auth,
        extra_state={"last_closes_raw": {}, "last_closes_split": {}},
    )

    # Now modify binding file contents (e.g. description field modified)
    doc_tampered = dict(doc)
    doc_tampered["description"] = "TAMPERED_BINDING_DESCRIPTION"
    binding_file.write_text(json.dumps(doc_tampered, indent=2) + "\n", encoding="utf-8")

    # Invocations fail closed pre-network
    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            [],
            _now_utc=datetime(2026, 9, 30, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _stage_c_binding_path=binding_file,
        )
    assert "BLOCK_SHADOW_STATE_INTEGRITY: authority SHA mismatch" in str(exc_info.value)


# -----------------------------------------------------------------------------
# N. changed binding commit SHA rejected
# -----------------------------------------------------------------------------
def test_n_changed_binding_commit_sha_rejected(tmp_path: Path) -> None:
    """N. Changed binding commit SHA rejected against persisted state authority."""
    cal = NyseCa1Calendar()
    state_dir = tmp_path / "prospective"
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc(commit_sha="a" * 40)
    auth = _write_binding(binding_file, doc)

    # Observation 1 committed
    obs1: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": "2026-09-29",
        "authority": {
            "activation_binding": str(binding_file),
            "activation_binding_id": auth.binding_id,
            "activation_binding_sha256": auth.manifest_sha256,
            "activation_binding_commit_sha": auth.binding_commit_sha,
            "activation_binding_commit_utc": auth.binding_commit_utc,
            "operational_activation_session": "2026-09-29",
            "authorization": "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
            "ordinal": 1,
            "dispatch_attempt": 2,
        },
    }
    append_observation(
        state_dir=state_dir,
        session=date(2026, 9, 29),
        observation=obs1,
        previous_sha=None,
        activation_session=date(2026, 9, 29),
        recovery_authority=auth,
        extra_state={"last_closes_raw": {}, "last_closes_split": {}},
    )

    # Change commit SHA in binding
    doc2 = make_valid_stage_c_binding_doc(commit_sha="b" * 40)
    _write_binding(binding_file, doc2)

    with pytest.raises(DataContractError) as exc_info:
        runner.main(
            [],
            _now_utc=datetime(2026, 9, 30, 20, 20, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _stage_c_binding_path=binding_file,
        )
    assert "BLOCK_SHADOW_STATE_INTEGRITY" in str(exc_info.value)


# -----------------------------------------------------------------------------
# O. no IEX fallback
# -----------------------------------------------------------------------------
def test_o_no_iex_fallback() -> None:
    """O. No IEX fallback."""
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


# -----------------------------------------------------------------------------
# P. provider query end = canonical close
# -----------------------------------------------------------------------------
def test_p_provider_query_end_is_canonical_close() -> None:
    """P. Provider query end is strictly canonical close; 23:59:59 forbidden."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 28)
    close_utc = cal.get_session(session).close_utc
    assert close_utc == datetime(2026, 9, 28, 20, 0, 0, tzinfo=timezone.utc)

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

    client = _make_client(_handler)
    now_utc = close_utc + timedelta(minutes=16)
    res = client.fetch_single_session("SPY", session, now_utc=now_utc)
    assert len(res.bars) == 1
    assert len(captured_requests) == 1
    query_params = dict(captured_requests[0].url.params)
    assert query_params["start"] == "2026-09-28T00:00:00Z"
    assert query_params["end"] == "2026-09-28T20:00:00Z"
    assert "23:59:59" not in query_params["end"]


# -----------------------------------------------------------------------------
# Q. provider eligibility = strict close + 15m
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# R. candidate dispatch = close + 20m
# -----------------------------------------------------------------------------
def test_r_candidate_schedule_defaults_to_close_plus_20m() -> None:
    """R. Candidate schedule defaults to close+20m."""
    cal = NyseCa1Calendar()
    session = date(2026, 9, 29)
    close_utc = cal.get_session(session).close_utc
    assert close_utc == datetime(2026, 9, 29, 20, 0, 0, tzinfo=timezone.utc)

    # Provider eligibility: close + 15m = 20:15 UTC
    elig = SH.provider_observation_eligible_after(session, cal)
    assert elig == datetime(2026, 9, 29, 20, 15, 0, tzinfo=timezone.utc)

    # Candidate operational schedule: close + 15m + 5m = 20:20 UTC
    sched = SH.candidate_schedule_time(session, cal)
    assert sched == datetime(2026, 9, 29, 20, 20, 0, tzinfo=timezone.utc)


# -----------------------------------------------------------------------------
# S. DST/winter/early-close calendar derivation
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# T. provider 403 -> zero observation/state commit
# -----------------------------------------------------------------------------
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
    _write_binding(binding_file, make_valid_stage_c_binding_doc())

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


# -----------------------------------------------------------------------------
# U. all six series required before append
# -----------------------------------------------------------------------------
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
    _write_binding(binding_file, make_valid_stage_c_binding_doc())

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


# -----------------------------------------------------------------------------
# V. paper/live false, real capital 0, NO_REAL_ORDERS true
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# W. Stage C observation missing authority field fails closed (tamper test)
# -----------------------------------------------------------------------------
def test_w_stage_c_observation_missing_any_authority_field_fails_closed(tmp_path: Path) -> None:
    """W. Tamper test: removing ANY Stage C authority field fails closed even if hash chain is reconstructed."""
    cal = NyseCa1Calendar()
    state_dir = tmp_path / "prospective"
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc()
    auth = _write_binding(binding_file, doc)

    # Valid observation 1
    obs1: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": "2026-09-29",
        "authority": {
            "activation_binding": str(binding_file),
            "activation_binding_id": auth.binding_id,
            "activation_binding_sha256": auth.manifest_sha256,
            "activation_binding_commit_sha": auth.binding_commit_sha,
            "activation_binding_commit_utc": auth.binding_commit_utc,
            "operational_activation_session": "2026-09-29",
            "authorization": "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
            "ordinal": 1,
            "dispatch_attempt": 2,
        },
    }
    append_observation(
        state_dir=state_dir,
        session=date(2026, 9, 29),
        observation=obs1,
        previous_sha=None,
        activation_session=date(2026, 9, 29),
        recovery_authority=auth,
        extra_state={"last_closes_raw": {}, "last_closes_split": {}},
    )

    # Verify clean state passes
    assert verify_chain(state_dir, expected_recovery_authority=auth)

    # Tamper: remove ONLY activation_binding_sha256 from observation artifact
    obs_path = state_dir / "observations" / "2026-09-29.json"
    obs_data = json.loads(obs_path.read_text(encoding="utf-8"))
    del obs_data["authority"]["activation_binding_sha256"]

    # Recompute observation hash and update state.json so normal chain is internally consistent
    recomputed_raw = json.dumps(obs_data, indent=2, sort_keys=True)
    obs_path.write_bytes(recomputed_raw.encode("utf-8"))
    new_digest = hashlib.sha256(recomputed_raw.encode("utf-8")).hexdigest()

    state_path = state_dir / "state.json"
    state_data = json.loads(state_path.read_text(encoding="utf-8"))
    state_data["last_observation_sha256"] = new_digest
    state_path.write_bytes(json.dumps(state_data, indent=2).encode("utf-8"))

    # verify_chain with expected recovery authority must fail closed on missing field
    with pytest.raises(DataContractError) as exc_info:
        verify_chain(state_dir, expected_recovery_authority=auth)
    assert "BLOCK_SHADOW_STATE_INTEGRITY: missing recovery authority field activation_binding_sha256" in str(exc_info.value)


# -----------------------------------------------------------------------------
# X. Stage C observation other authority field tamper fails closed
# -----------------------------------------------------------------------------
def test_x_stage_c_observation_other_authority_field_tamper_fails_closed(tmp_path: Path) -> None:
    """X. Tamper tests for all other Stage C authority fields: missing or mismatched values fail closed."""
    cal = NyseCa1Calendar()
    binding_file = tmp_path / "stage_c.json"
    doc = make_valid_stage_c_binding_doc()
    auth = _write_binding(binding_file, doc)

    fields_to_test = [
        ("activation_binding_id", "WRONG_ID", "ID mismatch"),
        ("activation_binding_commit_utc", "2026-09-29T00:00:00+00:00", "UTC mismatch"),
        ("operational_activation_session", "2026-09-30", "session mismatch"),
        ("activation_binding_commit_sha", "f" * 40, "commit SHA mismatch"),
    ]

    for field_name, wrong_val, expected_err_sub in fields_to_test:
        sub_dir = tmp_path / f"test_{field_name}"
        obs1: Dict[str, Any] = {
            "schema_version": 1,
            "hypothesis_id": "HYP_011",
            "session": "2026-09-29",
            "authority": {
                "activation_binding": str(binding_file),
                "activation_binding_id": auth.binding_id,
                "activation_binding_sha256": auth.manifest_sha256,
                "activation_binding_commit_sha": auth.binding_commit_sha,
                "activation_binding_commit_utc": auth.binding_commit_utc,
                "operational_activation_session": "2026-09-29",
                "authorization": "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
                "ordinal": 1,
                "dispatch_attempt": 2,
            },
        }
        append_observation(
            state_dir=sub_dir,
            session=date(2026, 9, 29),
            observation=obs1,
            previous_sha=None,
            activation_session=date(2026, 9, 29),
            recovery_authority=auth,
            extra_state={"last_closes_raw": {}, "last_closes_split": {}},
        )

        obs_path = sub_dir / "observations" / "2026-09-29.json"
        state_path = sub_dir / "state.json"

        # 1. Missing field test
        obs_data = json.loads(obs_path.read_text(encoding="utf-8"))
        del obs_data["authority"][field_name]
        raw_recomputed = json.dumps(obs_data, indent=2, sort_keys=True)
        obs_path.write_bytes(raw_recomputed.encode("utf-8"))
        st = json.loads(state_path.read_text(encoding="utf-8"))
        st["last_observation_sha256"] = hashlib.sha256(raw_recomputed.encode("utf-8")).hexdigest()
        state_path.write_bytes(json.dumps(st, indent=2).encode("utf-8"))

        with pytest.raises(DataContractError) as exc_info:
            verify_chain(sub_dir, expected_recovery_authority=auth)
        assert f"missing recovery authority field {field_name}" in str(exc_info.value)

        # 2. Wrong value test
        obs_data["authority"][field_name] = wrong_val
        raw_recomputed2 = json.dumps(obs_data, indent=2, sort_keys=True)
        obs_path.write_bytes(raw_recomputed2.encode("utf-8"))
        st["last_observation_sha256"] = hashlib.sha256(raw_recomputed2.encode("utf-8")).hexdigest()
        state_path.write_bytes(json.dumps(st, indent=2).encode("utf-8"))

        with pytest.raises(DataContractError) as exc_info:
            verify_chain(sub_dir, expected_recovery_authority=auth)
        assert expected_err_sub in str(exc_info.value)


# -----------------------------------------------------------------------------
# Y. Builder CLI rejects bypass options
# -----------------------------------------------------------------------------
def test_y_builder_cli_rejects_bypass_options() -> None:
    """Y. Production builder CLI rejects bypass options (--skip-ancestor-check, --canonical-ref, --output-path)."""
    # 1. Reject --skip-ancestor-check
    with pytest.raises(SystemExit):
        builder.main(["--commit-sha", "0" * 40, "--skip-ancestor-check"])

    # 2. Reject --canonical-ref
    with pytest.raises(SystemExit):
        builder.main(["--commit-sha", "0" * 40, "--canonical-ref", "arbitrary_branch"])

    # 3. Reject --output-path
    with pytest.raises(SystemExit):
        builder.main(["--commit-sha", "0" * 40, "--output-path", "arbitrary/path.json"])


# -----------------------------------------------------------------------------
# Z. Builder write-mode gates and immutable create-once semantics
# -----------------------------------------------------------------------------
def test_z_builder_write_mode_gates(tmp_path: Path) -> None:
    """Z. Builder write-mode gates: commit mismatch, branch mismatch, dirty tree, immutable create-once."""
    import os
    import subprocess
    tmp_repo = tmp_path / "repo"
    tmp_repo.mkdir()

    # Initialize a temporary git repository
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@acash.local"], cwd=tmp_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ACASH Test"], cwd=tmp_repo, check=True, capture_output=True)

    # Initial commit (commit at 12:00 UTC on 2026-09-29 -> activation 2026-09-29)
    (tmp_repo / "README.md").write_text("ACASH test repo", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_repo, check=True, capture_output=True)
    env = dict(
        GIT_COMMITTER_DATE="2026-09-29T12:00:00Z",
        GIT_AUTHOR_DATE="2026-09-29T12:00:00Z",
    )
    merged_env = {**os.environ, **env}
    subprocess.run(
        ["git", "commit", "-m", "canonical main integration", "--date", "2026-09-29T12:00:00Z"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
        env=merged_env,
    )

    # Set up refs/remotes/origin/main pointing to HEAD
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=tmp_repo, check=True, capture_output=True)

    head_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=tmp_repo).stdout.strip().lower()
    target_manifest = tmp_repo / "target_manifest.json"

    # D. Write with commit != origin/main fails
    with pytest.raises(DataContractError) as exc_info:
        builder.main(
            ["--commit-sha", "a" * 40, "--write"],
            _output_path=target_manifest,
            _repo_root=tmp_repo,
        )
    assert "WRITE_MODE_COMMIT_NOT_ORIGIN_MAIN" in str(exc_info.value)

    # E. Write outside main branch fails
    subprocess.run(["git", "checkout", "-b", "feature/other"], cwd=tmp_repo, check=True, capture_output=True)
    with pytest.raises(DataContractError) as exc_info:
        builder.main(
            ["--commit-sha", head_sha, "--write"],
            _output_path=target_manifest,
            _repo_root=tmp_repo,
        )
    assert "WRITE_MODE_NOT_ON_MAIN_BRANCH" in str(exc_info.value)
    subprocess.run(["git", "checkout", "main"], cwd=tmp_repo, check=True, capture_output=True)

    # F. Dirty tracked working tree fails
    (tmp_repo / "README.md").write_text("dirty tracked content", encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        builder.main(
            ["--commit-sha", head_sha, "--write"],
            _output_path=target_manifest,
            _repo_root=tmp_repo,
        )
    assert "WRITE_MODE_DIRTY_WORKING_TREE" in str(exc_info.value)
    subprocess.run(["git", "checkout", "--", "README.md"], cwd=tmp_repo, check=True, capture_output=True)

    # H. Valid canonical-main write creates exactly one canonical manifest
    code = builder.main(
        ["--commit-sha", head_sha, "--write"],
        _output_path=target_manifest,
        _repo_root=tmp_repo,
    )
    assert code == 0
    assert target_manifest.exists()

    # G. Existing Stage C-B file cannot be overwritten (immutable create-once)
    with pytest.raises(DataContractError) as exc_info:
        builder.main(
            ["--commit-sha", head_sha, "--write"],
            _output_path=target_manifest,
            _repo_root=tmp_repo,
        )
    assert "STAGE_C_B_ALREADY_EXISTS_IMMUTABLE" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Builder dry-run and invariants tests
# -----------------------------------------------------------------------------
def test_builder_dry_run_and_invariants(tmp_path: Path) -> None:
    """Test build_stage_c_b_recovery_manifest dry-run and git validation using hermetic synthetic git fixture."""
    import os
    import subprocess
    tmp_repo = tmp_path / "hermetic_repo"
    tmp_repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@acash.local"], cwd=tmp_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ACASH Test"], cwd=tmp_repo, check=True, capture_output=True)

    # 1. Commit 1: pre-failure commit (2026-09-28T12:00:00Z -> activation 2026-09-28)
    (tmp_repo / "README.md").write_text("commit 1", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_repo, check=True, capture_output=True)
    env1 = {**os.environ, "GIT_COMMITTER_DATE": "2026-09-28T12:00:00Z", "GIT_AUTHOR_DATE": "2026-09-28T12:00:00Z"}
    subprocess.run(["git", "commit", "-m", "pre-failure commit", "--date", "2026-09-28T12:00:00Z"], cwd=tmp_repo, check=True, capture_output=True, env=env1)
    pre_failure_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=tmp_repo).stdout.strip().lower()

    # 2. Commit 2: post-failure commit (2026-09-29T12:00:00Z -> activation 2026-09-29)
    (tmp_repo / "README.md").write_text("commit 2", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_repo, check=True, capture_output=True)
    env2 = {**os.environ, "GIT_COMMITTER_DATE": "2026-09-29T12:00:00Z", "GIT_AUTHOR_DATE": "2026-09-29T12:00:00Z"}
    subprocess.run(["git", "commit", "-m", "post-failure commit", "--date", "2026-09-29T12:00:00Z"], cwd=tmp_repo, check=True, capture_output=True, env=env2)
    post_failure_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=tmp_repo).stdout.strip().lower()

    target_out = tmp_path / "test_stage_c_b.json"

    # 1. Dry-run on valid post-failure commit: does NOT write to disk
    code = builder.main(
        ["--commit-sha", post_failure_sha],
        _output_path=target_out,
        _repo_root=tmp_repo,
    )
    assert code == 0
    assert not target_out.exists()

    # 2. Pre-failure commit rejected because activation <= 2026-09-28
    with pytest.raises(DataContractError) as exc_info:
        builder.main(
            ["--commit-sha", pre_failure_sha],
            _output_path=target_out,
            _repo_root=tmp_repo,
        )
    assert "ACTIVATION_NOT_ADVANCED" in str(exc_info.value)

    # 3. Invalid SHA format fails
    with pytest.raises(DataContractError) as exc_info:
        builder.main(["--commit-sha", "not_a_sha"], _output_path=target_out, _repo_root=tmp_repo)
    assert "INVALID_COMMIT_SHA_FORMAT" in str(exc_info.value)

    # 4. Non-existent SHA fails
    with pytest.raises(DataContractError) as exc_info:
        builder.main(["--commit-sha", "0" * 40], _output_path=target_out, _repo_root=tmp_repo)
    assert "GIT_COMMIT_NOT_FOUND" in str(exc_info.value)


@pytest.mark.non_hermetic
def test_builder_historical_git_audit(tmp_path: Path) -> None:
    """Non-hermetic historical audit validating active Git repository commit timestamps and boundaries."""
    target_out = tmp_path / "audit_stage_c_b.json"

    # Authoritative canonical integration merge commit
    merge_sha = "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f"
    code = builder.main(["--commit-sha", merge_sha], _output_path=target_out)
    assert code == 0
    assert not target_out.exists()

    # Prior canonical main must fail activation advancement
    prior_main_sha = "d9608c0a2353bd5ed41943e5fb893ef9648089d2"
    with pytest.raises(DataContractError) as exc_info:
        builder.main(["--commit-sha", prior_main_sha], _output_path=target_out)
    assert "ACTIVATION_NOT_ADVANCED" in str(exc_info.value)
