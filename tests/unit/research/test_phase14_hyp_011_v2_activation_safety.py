"""HYP_011 V2 activation-safety correction tests (final pre-deployment gate).

Proves the V2 SegmentActivationAuthority contract, V2 ordinal-1 strong
ceremony (RegisteredIntent + DispatchAuthority from session one), the
session-one non-event CA binding, full zero-network local preflight, timer
template wiring, and calendar-derived dispatch expressions.

Hermetic only: tmp_path roots, mocked transport, fixed timestamps, zero
network, no Homelab mutation, no V1 evidence writes.
"""

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider
from acash.research.hyp_011.shadow import candidate_schedule_time
from acash.research.hyp_011.shadow_authority import (
    ObservationIntent,
    register_observation_intent,
)
from acash.research.hyp_011.shadow_v2_activation import (
    SEGMENT_ID_V2,
    load_segment_activation_authority,
    session_one_ca_binding_sha256,
    systemd_oncalendar_expression,
    validate_segment_activation_authority,
)

RUNTIME_SHA = "e" * 40
ACTIVATION_SESSION = date(2026, 10, 6)
AUTHORIZED_AT = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
LIVE_NOW = datetime(2026, 10, 6, 21, 0, 0, tzinfo=timezone.utc)
STALE_NOW = datetime(2026, 10, 7, 15, 0, 0, tzinfo=timezone.utc)
AUTH_STRING = "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001"


def _load_runner_module() -> Any:
    import importlib.util

    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "process_hyp_011_prospective_shadow.py"
    )
    spec = importlib.util.spec_from_file_location(
        "process_hyp_011_prospective_shadow_v2safety", script_path
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _activation_doc(**overrides: Any) -> Dict[str, Any]:
    doc: Dict[str, Any] = {
        "schema_version": 1,
        "segment_id": SEGMENT_ID_V2,
        "hypothesis_id": "HYP_011",
        "activation_session": ACTIVATION_SESSION.isoformat(),
        "runtime_commit_sha": RUNTIME_SHA,
        "starting_aum": "100000.00",
        "paper_trading": False,
        "live_trading": False,
        "real_capital_authority_usd": "0.00",
        "no_real_orders": True,
        "authorized_at_utc": AUTHORIZED_AT.isoformat(),
        "authority_identity": "TEST_V2_AUTHORITY",
    }
    doc.update(overrides)
    return doc


def _write_activation_file(tmp_path: Path, **overrides: Any) -> Path:
    path = tmp_path / "segment_activation_authority.json"
    path.write_text(json.dumps(_activation_doc(**overrides)), encoding="utf-8")
    return path


def _v2_argv(
    v2_root: Path,
    activation_path: Path,
    authority_path: Path,
    mode: str,
) -> List[str]:
    argv = [
        "--authorization",
        AUTH_STRING,
        "--ordinal",
        "1",
        "--dispatch-attempt",
        "1",
        "--dispatch-authority",
        str(authority_path),
        "--runtime-sha",
        RUNTIME_SHA,
        "--state-dir",
        str(v2_root),
        "--segment-id",
        SEGMENT_ID_V2,
        "--segment-activation-authority",
        str(activation_path),
    ]
    if mode == "live":
        argv.insert(0, "--execute-network")
    elif mode == "preflight":
        argv.insert(0, "--local-preflight")
    else:
        raise AssertionError(f"unknown mode {mode}")
    return argv


def _dummy_creds() -> EnvAlpacaCredentialProvider:
    return EnvAlpacaCredentialProvider(
        environ={
            "ACASH_ALPACA_API_KEY_ID": "mock_id",
            "ACASH_ALPACA_API_SECRET": "mock_secret",
        }
    )


class _MockBars:
    def __init__(self, session: date) -> None:
        from acash.data.qualification.daily_models import DailyBar

        self.bars = [
            DailyBar(
                timestamp_utc=datetime.combine(
                    session, datetime.min.time(), tzinfo=timezone.utc
                ).replace(hour=5),
                open=Decimal("100"),
                high=Decimal("100"),
                low=Decimal("100"),
                close=Decimal("100"),
                volume=Decimal("1000"),
            )
        ]
        self.pages_metadata: List[Any] = []
        self.pages_raw_bytes: List[Any] = []


class _MockClient:
    def __init__(self, calls: List[Any]) -> None:
        self._calls = calls

    def fetch_single_session(self, symbol: str, session: date, **kwargs: Any) -> Any:
        self._calls.append((symbol, session.isoformat()))
        return _MockBars(session)


def _register_v2_intent(v2_root: Path) -> Path:
    # The runner resolves the registry to <state_dir>/intent_registry unless
    # --intent-registry overrides it, so the ceremony registers there.
    registry = v2_root / "intent_registry"
    return register_observation_intent(
        registry_dir=registry,
        calendar=NyseCa1Calendar(),
        target_session=ACTIVATION_SESSION,
        observation_ordinal=1,
        previous_observation_sha256=None,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        authority_identity="TEST_V2",
        now_utc=AUTHORIZED_AT,
    )


def _mint_v2_dispatch_authority(
    tmp_path: Path,
    registered_sha: str,
    ca_sha: Optional[str] = None,
    valid_after: str = "2026-10-06T00:00:00+00:00",
    expires_at: str = "2026-10-07T00:00:00+00:00",
) -> Path:
    intent = ObservationIntent(
        hypothesis_id="HYP_011",
        target_session=ACTIVATION_SESSION,
        observation_ordinal=1,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        previous_observation_sha256=None,
        backfill_allowed=False,
        automatic_skip_allowed=False,
        created_at_utc=AUTHORIZED_AT,
        authority_identity="TEST_V2",
    )
    doc = {
        "schema_version": 1,
        "intent_sha256": registered_sha,
        "intent": intent.canonical_doc(),
        "runtime_commit_sha": RUNTIME_SHA,
        "target_session": ACTIVATION_SESSION.isoformat(),
        "observation_ordinal": 1,
        "dispatch_attempt": 1,
        "valid_after_utc": valid_after,
        "expires_at_utc": expires_at,
        "ca_manifest_sha256": (
            ca_sha if ca_sha is not None else session_one_ca_binding_sha256()
        ),
        "paper_trading": False,
        "live_trading": False,
        "real_capital_authority_usd": "0.00",
        "no_real_orders": True,
        "authority_identity": "TEST_V2",
    }
    path = tmp_path / "dispatch_authority_v2_0001.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def _full_v2_ceremony(tmp_path: Path) -> Dict[str, Path]:
    v2_root = tmp_path / "v2-external"
    activation_path = _write_activation_file(tmp_path)
    reg_path = _register_v2_intent(v2_root)
    registered_sha = str(json.loads(reg_path.read_text(encoding="utf-8"))["intent_sha256"])
    authority_path = _mint_v2_dispatch_authority(tmp_path, registered_sha)
    return {
        "v2_root": v2_root,
        "activation": activation_path,
        "authority": authority_path,
    }


# --- SegmentActivationAuthority adversarial matrix ---


@pytest.mark.parametrize(
    "mutation",
    [
        {"segment_id": "HYP_011_PROSPECTIVE_V1"},
        {"hypothesis_id": "HYP_009"},
        {"runtime_commit_sha": "f" * 40},
        {"starting_aum": "99999.99"},
        {"paper_trading": True},
        {"live_trading": True},
        {"real_capital_authority_usd": "0.01"},
        {"no_real_orders": False},
        {"authority_identity": "  "},
        {"activation_session": "2026-10-04"},  # Sunday: not a trading session
        {"activation_session": "not-a-date"},
        {"authorized_at_utc": "2026-10-06T12:00:00"},  # naive timestamp
        {"schema_version": 2},
    ],
)
def test_v2_activation_authority_rejects_malformed(mutation: Dict[str, Any]) -> None:
    calendar = NyseCa1Calendar()
    with pytest.raises(DataContractError):
        validate_segment_activation_authority(
            _activation_doc(**mutation), calendar, LIVE_NOW, RUNTIME_SHA
        )


def test_v2_activation_rejects_missing_field() -> None:
    doc = _activation_doc()
    del doc["authority_identity"]
    with pytest.raises(DataContractError):
        validate_segment_activation_authority(
            doc, NyseCa1Calendar(), LIVE_NOW, RUNTIME_SHA
        )


def test_v2_activation_rejects_non_prospective_session() -> None:
    # Activation 2026-09-28 authorized 2026-10-02 is stale history, not a
    # prospective V2 activation — V1 lineage can never leak in this way.
    doc = _activation_doc(
        activation_session="2026-09-28",
        authorized_at_utc="2026-10-02T12:00:00+00:00",
    )
    with pytest.raises(DataContractError):
        validate_segment_activation_authority(
            doc, NyseCa1Calendar(), LIVE_NOW, RUNTIME_SHA
        )


def test_v2_activation_rejects_future_authorization() -> None:
    doc = _activation_doc(
        authorized_at_utc="2026-10-06T22:00:00+00:00",
    )
    with pytest.raises(DataContractError):
        validate_segment_activation_authority(
            doc, NyseCa1Calendar(), LIVE_NOW, RUNTIME_SHA
        )


def test_v2_activation_file_digest_bound(tmp_path: Path) -> None:
    path = _write_activation_file(tmp_path)
    authority, file_sha = load_segment_activation_authority(
        path, NyseCa1Calendar(), LIVE_NOW, RUNTIME_SHA
    )
    assert authority.activation_session == ACTIVATION_SESSION
    assert file_sha == hashlib.sha256(path.read_bytes()).hexdigest()


def test_v2_activation_rejects_unreadable_file(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        load_segment_activation_authority(
            tmp_path / "absent.json", NyseCa1Calendar(), LIVE_NOW, RUNTIME_SHA
        )


# --- V2 runner path: no V1 inheritance ---


def test_v2_dry_run_requires_activation_authority(tmp_path: Path) -> None:
    runner = _load_runner_module()
    with pytest.raises(DataContractError):
        runner.main(
            [
                "--state-dir",
                str(tmp_path / "v2"),
                "--segment-id",
                SEGMENT_ID_V2,
            ],
            _now_utc=LIVE_NOW,
        )


def test_v2_ignores_stage_c_binding(tmp_path: Path, capsys: Any) -> None:
    runner = _load_runner_module()
    repo_root = Path(__file__).resolve().parents[3]
    stage_c = (
        repo_root
        / "docs"
        / "phase14"
        / "manifests"
        / "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json"
    )
    activation_path = _write_activation_file(tmp_path)
    assert (
        runner.main(
            [
                "--state-dir",
                str(tmp_path / "v2"),
                "--segment-id",
                SEGMENT_ID_V2,
                "--segment-activation-authority",
                str(activation_path),
                "--runtime-sha",
                RUNTIME_SHA,
            ],
            _now_utc=LIVE_NOW,
            _stage_c_binding_path=stage_c,
        )
        == 0
    )
    out = capsys.readouterr().out
    # Fresh V2 target comes from the activation authority, never Stage-C.
    assert f"EXPECTED_SESSION = {ACTIVATION_SESSION.isoformat()}" in out
    assert "NETWORK_REQUESTS = 0" in out


# --- V2 ordinal-1 strong ceremony ---


def test_v2_ordinal1_requires_dispatch_authority(tmp_path: Path) -> None:
    runner = _load_runner_module()
    ceremony = _full_v2_ceremony(tmp_path)
    # Same ceremony argv but WITHOUT --dispatch-authority: V2 ordinal 1
    # must fail closed (the V1 bare-token exception does not apply).
    argv = [
        "--execute-network",
        "--authorization",
        AUTH_STRING,
        "--ordinal",
        "1",
        "--dispatch-attempt",
        "1",
        "--runtime-sha",
        RUNTIME_SHA,
        "--state-dir",
        str(ceremony["v2_root"]),
        "--segment-id",
        SEGMENT_ID_V2,
        "--segment-activation-authority",
        str(ceremony["activation"]),
    ]
    with pytest.raises(DataContractError):
        runner.main(
            argv,
            _now_utc=LIVE_NOW,
            _runtime_sha=RUNTIME_SHA,
            _credential_provider=_dummy_creds(),
            _client=_MockClient([]),
        )


def test_v2_ordinal1_requires_registered_intent(tmp_path: Path) -> None:
    runner = _load_runner_module()
    v2_root = tmp_path / "v2-external"
    activation_path = _write_activation_file(tmp_path)
    # Mint an authority against an intent that was NEVER registered.
    authority_path = _mint_v2_dispatch_authority(tmp_path, "a" * 64)
    with pytest.raises(DataContractError):
        runner.main(
            _v2_argv(v2_root, activation_path, authority_path, "live"),
            _now_utc=LIVE_NOW,
            _runtime_sha=RUNTIME_SHA,
            _credential_provider=_dummy_creds(),
            _client=_MockClient([]),
        )


def test_v2_ordinal1_rejects_wrong_ca_binding(tmp_path: Path) -> None:
    runner = _load_runner_module()
    ceremony = _full_v2_ceremony(tmp_path)
    reg_path = (
        ceremony["v2_root"]
        / "intent_registry"
        / f"{ACTIVATION_SESSION.isoformat()}_ord0001.json"
    )
    registered_sha = str(
        json.loads(reg_path.read_text(encoding="utf-8"))["intent_sha256"]
    )
    bad_authority = _mint_v2_dispatch_authority(
        tmp_path, registered_sha, ca_sha="0" * 64
    )
    with pytest.raises(DataContractError):
        runner.main(
            _v2_argv(ceremony["v2_root"], ceremony["activation"], bad_authority, "live"),
            _now_utc=LIVE_NOW,
            _runtime_sha=RUNTIME_SHA,
            _credential_provider=_dummy_creds(),
            _client=_MockClient([]),
        )


def test_v2_session1_full_preflight_zero_consume_zero_network(
    tmp_path: Path, capsys: Any
) -> None:
    runner = _load_runner_module()
    ceremony = _full_v2_ceremony(tmp_path)
    assert (
        runner.main(
            _v2_argv(ceremony["v2_root"], ceremony["activation"], ceremony["authority"], "preflight"),
            _now_utc=LIVE_NOW,
            _runtime_sha=RUNTIME_SHA,
            _credential_provider=_dummy_creds(),
            _client=_MockClient([]),
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "LOCAL_PREFLIGHT = PASS" in out
    assert "ATTEMPT_CONSUMED = false" in out
    assert "NETWORK_REQUESTS = 0" in out
    ledger = ceremony["v2_root"] / "dispatch_ledger"
    assert not ledger.exists() or list(ledger.glob("*.json")) == []
    assert not (ceremony["v2_root"] / "observations").exists()


def test_v2_preflight_stale_target_fails_nonzero(tmp_path: Path) -> None:
    runner = _load_runner_module()
    ceremony = _full_v2_ceremony(tmp_path)
    # Widen the authority window so the failure lands on freshness, not expiry.
    reg_path = (
        ceremony["v2_root"]
        / "intent_registry"
        / f"{ACTIVATION_SESSION.isoformat()}_ord0001.json"
    )
    registered_sha = str(
        json.loads(reg_path.read_text(encoding="utf-8"))["intent_sha256"]
    )
    wide_authority = _mint_v2_dispatch_authority(
        tmp_path,
        registered_sha,
        valid_after="2026-10-06T00:00:00+00:00",
        expires_at="2026-10-08T00:00:00+00:00",
    )
    with pytest.raises(DataContractError):
        runner.main(
            _v2_argv(ceremony["v2_root"], ceremony["activation"], wide_authority, "preflight"),
            _now_utc=STALE_NOW,
            _runtime_sha=RUNTIME_SHA,
            _credential_provider=_dummy_creds(),
            _client=_MockClient([]),
        )
    ledger = ceremony["v2_root"] / "dispatch_ledger"
    assert not ledger.exists() or list(ledger.glob("*.json")) == []


def test_v2_session1_live_observation_and_replay(tmp_path: Path) -> None:
    runner = _load_runner_module()
    ceremony = _full_v2_ceremony(tmp_path)
    calls: List[Any] = []
    argv = _v2_argv(ceremony["v2_root"], ceremony["activation"], ceremony["authority"], "live")
    assert (
        runner.main(
            argv,
            _now_utc=LIVE_NOW,
            _runtime_sha=RUNTIME_SHA,
            _credential_provider=_dummy_creds(),
            _client=_MockClient(calls),
        )
        == 0
    )
    assert len(calls) == 6  # 3 symbols x 2 adjustments, no retry
    state = json.loads((ceremony["v2_root"] / "state.json").read_text(encoding="utf-8"))
    assert state["segment_id"] == SEGMENT_ID_V2
    assert state["activation_session"] == ACTIVATION_SESSION.isoformat()
    assert state["observed_sessions"] == [ACTIVATION_SESSION.isoformat()]
    assert state["observed_session_count"] == 1
    assert state["segment_activation_authority_sha256"] == hashlib.sha256(
        ceremony["activation"].read_bytes()
    ).hexdigest()
    obs = json.loads(
        (ceremony["v2_root"] / "observations" / f"{ACTIVATION_SESSION.isoformat()}.json").read_text(
            encoding="utf-8"
        )
    )
    assert obs["segment_id"] == SEGMENT_ID_V2
    assert obs["previous_observation_sha256"] is None
    for symbol in ("ACWI", "AGG", "SPY"):
        assert obs["corporate_actions"][symbol] == {
            "status": "CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS"
        }
    # Replay of the identical dispatch burns closed.
    with pytest.raises(DataContractError):
        runner.main(
            argv,
            _now_utc=LIVE_NOW,
            _runtime_sha=RUNTIME_SHA,
            _credential_provider=_dummy_creds(),
            _client=_MockClient([]),
        )


# --- Timer expression + template wiring ---


def test_dispatch_expression_derived_from_canonical_timing() -> None:
    calendar = NyseCa1Calendar()
    assert systemd_oncalendar_expression(
        ACTIVATION_SESSION, calendar
    ) == "2026-10-06 20:20:00 UTC"
    expected = candidate_schedule_time(ACTIVATION_SESSION, calendar)
    assert expected.isoformat() == "2026-10-06T20:20:00+00:00"


def test_session_one_ca_binding_stable() -> None:
    first = session_one_ca_binding_sha256()
    assert len(first) == 64 and all(c in "0123456789abcdef" for c in first)
    assert session_one_ca_binding_sha256() == first


def test_v2_timer_template_wiring() -> None:
    ops = Path(__file__).resolve().parents[3] / "docs" / "operations"
    timer = (ops / "acash-hyp011-v2.timer").read_text(encoding="utf-8")
    assert "Requires=acash-hyp011-v2.service" not in timer
    assert "Unit=acash-hyp011-v2.service" in timer
    assert "RemainAfterElapse=false" in timer
    assert "Persistent=false" in timer
    assert not any(
        line.strip().startswith("OnCalendar=") for line in timer.splitlines()
    )
    # Activation drop-in shape: clear first, then set the validated expression.
    assert "OnCalendar=" in timer
    service = (ops / "acash-hyp011-v2.service").read_text(encoding="utf-8")
    assert "--segment-activation-authority" in service
    assert "${SEGMENT_ACTIVATION_AUTHORITY}" in service


def test_runbook_binds_no_stale_sha() -> None:
    runbook = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "operations"
        / "HYP_011_V2_HOMELAB_DEPLOYMENT.md"
    ).read_text(encoding="utf-8")
    assert "49b26f1" not in runbook
    assert "APPROVED_RUNTIME_SHA" in runbook
    assert "20:15" not in runbook
    assert not any(
        line.strip().startswith("Timezone=") for line in runbook.splitlines()
    )
