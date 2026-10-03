"""Unit tests for F15 dispatch authority and F16 CA intake enforcement.

Covers: ObservationIntent validation (pre-lock, hash, chain head),
DispatchAuthority validation (runtime/ordinal/attempt/expiry/locks/CA-SHA),
single-use ledger replay blocking (including crash-reuse), bare-token
ordinal-2 rejection, and runner-side CA intake gating with zero-network
proofs. No network, no broker, no capital.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider
from acash.research.hyp_011.shadow_authority import (
    ObservationIntent,
    attempt_ledger_key,
    consume_dispatch_attempt,
    register_observation_intent,
    validate_dispatch_authority,
    validate_observation_intent,
)

RUNTIME_SHA = "c" * 40
FAKE_SHA = "ab" * 32


def _load_runner_module() -> Any:
    script_path = (
        Path(__file__).resolve().parents[3] / "scripts" / "process_hyp_011_prospective_shadow.py"
    )
    spec = importlib.util.spec_from_file_location(
        "process_hyp_011_prospective_shadow", script_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mock_creds() -> EnvAlpacaCredentialProvider:
    return EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_k", "ACASH_ALPACA_API_SECRET": "mock_s"}
    )


def _mock_bars_client(calls: List[Any], session_iso: str = "2026-10-01") -> Any:
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "bars": [
                    {
                        "t": f"{session_iso}T05:00:00Z",
                        "o": 100.0,
                        "h": 101.0,
                        "l": 99.0,
                        "c": 100.5,
                        "v": 1000,
                    }
                ]
            },
        )

    return HYP011AlpacaClient(
        transport=httpx.MockTransport(handler),
        credential_provider=_mock_creds(),
    )


def _failing_client() -> Any:
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be reached")

    return HYP011AlpacaClient(
        transport=httpx.MockTransport(handler),
        credential_provider=_mock_creds(),
    )


def _fixture_binding(tmp_path: Path) -> Dict[str, Any]:
    """LF-canonical Stage C-B fixture (activation 2026-09-30)."""
    binding_path = tmp_path / "stage_c_f15.json"
    doc = {
        "binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
        "binding_commit_sha": "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
        "binding_commit_utc": "2026-09-29T17:12:46+00:00",
        "activation_session": "2026-09-30",
        "scientific_prospective_boundary": "2026-09-25",
        "failed_dispatch_session": "2026-09-28",
        "failed_dispatch_attempt": 1,
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
    raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    binding_path.write_bytes(raw)
    return {
        "path": binding_path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "commit_sha": doc["binding_commit_sha"],
        "commit_utc": doc["binding_commit_utc"],
    }


def _reconciled_obs1_state(tmp_path: Path, binding: Dict[str, Any]) -> Path:
    """Reconciled Obs #1 (2026-09-30) state dir bound to the fixture binding."""
    state_dir = tmp_path / "prospective"
    obs_dir = state_dir / "observations"
    obs_dir.mkdir(parents=True)
    obs_iso = "2026-09-30"
    strategy_frag = {
        "holdings": {"ACWI": 500, "AGG": 300},
        "cash": "20000.00",
        "market_value": "80000.00",
        "receivable": "0",
        "equity": "100000.00",
        "daily_return": "0.00000000",
        "running_peak": "100000.00",
        "drawdown": "0.00000000",
        "entitlements": [],
        "trades": [],
    }
    benchmark_frag = {
        "entry": {"side": "BUY", "quantity": "200", "fill": "500.00"},
        "entitlements": [],
        "shares": 200,
        "cash": "0.00",
        "market_value": "100000.00",
        "receivable": "0",
        "equity": "100000.00",
        "daily_return": "0.00000000",
        "running_peak": "100000.00",
        "drawdown": "0.00000000",
    }
    obs_doc = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": obs_iso,
        "processed_at_utc": "2026-09-30T20:20:00+00:00",
        "previous_observation_sha256": None,
        "authority": {
            "activation_binding": str(binding["path"]),
            "activation_binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
            "activation_binding_sha256": binding["sha256"],
            "activation_binding_commit_sha": binding["commit_sha"],
            "activation_binding_commit_utc": binding["commit_utc"],
            "operational_activation_session": "2026-09-30",
            "ordinal": 1,
            "dispatch_attempt": 2,
        },
        "strategy": strategy_frag,
        "benchmark": benchmark_frag,
    }
    obs_raw = json.dumps(obs_doc, indent=2, sort_keys=True) + "\n"
    (obs_dir / f"{obs_iso}.json").write_bytes(obs_raw.encode("utf-8"))
    obs_sha = hashlib.sha256(obs_raw.encode("utf-8")).hexdigest()
    state_doc = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "activation_session": "2026-09-30",
        "starting_aum": "100000.00",
        "locks": {
            "paper_authorized": False,
            "live_authorized": False,
            "capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
        "activation_authority_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
        "activation_authority_sha256": binding["sha256"],
        "activation_commit_sha": binding["commit_sha"],
        "observed_sessions": [obs_iso],
        "observed_session_count": 1,
        "last_processed_session": obs_iso,
        "last_observation_sha256": obs_sha,
        "strategy": {
            "cash": "20000.00",
            "holdings": {"ACWI": 500, "AGG": 300},
            "receivables": [],
            "running_peak": "100000.00",
            "previous_equity": "100000.00",
        },
        "benchmark": {
            "cash": "0.00",
            "SPY_shares": 200,
            "receivables": [],
            "running_peak": "100000.00",
            "previous_equity": "100000.00",
            "entered": True,
        },
        "last_closes_raw": {"ACWI": "100.00", "AGG": "100.00", "SPY": "500.00"},
        "last_closes_split": {"ACWI": "100.00", "AGG": "100.00", "SPY": "500.00"},
        "completed_annual_rebalances": 0,
    }
    (state_dir / "state.json").write_text(json.dumps(state_doc, indent=2), encoding="utf-8")
    return state_dir


def _scope_doc() -> Dict[str, Any]:
    return {
        "schedule_id": "FIXTURE_OFFICIAL_SCOPE_2026_10_01",
        "schedule_sha256": FAKE_SHA,
        "scope_note": "Fixture official-scope coverage for 2026-10-01.",
        "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
    }


def _no_event_intake(symbol: str, sponsor: str, session_iso: str = "2026-10-01") -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "session": session_iso,
        "has_event": False,
        "authority_source": sponsor,
        "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
        "source_sha256": FAKE_SHA,
        "evidence_ref": f"evidence/{symbol.lower()}-scope-fixture.pdf",
        "scope_evidence": _scope_doc(),
    }


def _write_ca_file(tmp_path: Path, name: str = "ca_2026-10-01.json",
                   digests: Dict[str, Dict[str, str]] | None = None) -> Path:
    sponsors = {
        "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
        "AGG": "BLACKROCK_ISHARES_OFFICIAL",
        "SPY": "STATE_STREET_SPDR_OFFICIAL",
    }
    doc = {}
    for symbol in sponsors:
        if digests is not None:
            sha = digests[symbol]["sha"]
            ref = digests[symbol]["ref"]
            sched = digests[symbol]["sched_sha"]
        else:
            sha, ref, sched = FAKE_SHA, f"evidence/{symbol.lower()}-scope-fixture.pdf", FAKE_SHA
        doc[symbol] = _no_event_intake(symbol, sponsors[symbol])
        doc[symbol]["source_sha256"] = sha
        doc[symbol]["evidence_ref"] = ref
        doc[symbol]["scope_evidence"] = dict(_scope_doc(), schedule_sha256=sched)
    path = tmp_path / name
    path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return path


def _write_ca_bundle(tmp_path: Path, name: str = "ca_bundle_2026-10-01") -> Dict[str, Any]:
    """Per-symbol evidence bundles with REAL digests over fixture bytes."""
    urls = {
        "ACWI": "https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf",
        "AGG": "https://www.ishares.com/us/products/239458/ishares-core-us-aggregate-bond-etf",
        "SPY": "https://www.ssga.com/us/en/institutional/etfs/spdr-sp-500-etf-trust-spy",
    }
    identities = {
        "ACWI": {"product_id": "239600", "ticker": "ACWI", "cusip": "464288257",
                 "sponsor": "BLACKROCK_ISHARES_OFFICIAL"},
        "AGG": {"product_id": "239458", "ticker": "AGG",
                "sponsor": "BLACKROCK_ISHARES_OFFICIAL"},
        "SPY": {"schedule": "SSGA_OFFICIAL_2026_DISTRIBUTIONS", "ticker": "SPY",
                "cusip": "78462F103", "sponsor": "STATE_STREET_SPDR_OFFICIAL"},
    }
    sponsors = {"ACWI": "BLACKROCK_ISHARES_OFFICIAL",
                "AGG": "BLACKROCK_ISHARES_OFFICIAL",
                "SPY": "STATE_STREET_SPDR_OFFICIAL"}
    # F19: fixture evidence bytes carry the semantic identity markers.
    marker_bytes = {
        "ACWI": b"OFFICIAL-FIXTURE-EVIDENCE::ACWI::239600::464288257::2026-10-01\n",
        "AGG": b"OFFICIAL-FIXTURE-EVIDENCE::AGG::239458::2026-10-01\n",
        "SPY": b"OFFICIAL-FIXTURE-EVIDENCE::SPY::78462F103::State Street::2026-10-01\n",
    }
    root = tmp_path / name
    digests: Dict[str, Dict[str, str]] = {}
    for symbol in sponsors:
        sdir = root / symbol
        edir = sdir / "evidence"
        edir.mkdir(parents=True)
        ev_bytes = marker_bytes[symbol]
        sched_bytes = f"OFFICIAL-FIXTURE-SCHEDULE::{symbol}::2026-10-01\n".encode()
        ev_name = f"{symbol.lower()}-scope-fixture.pdf"
        sched_name = f"{symbol.lower()}-schedule-fixture.pdf"
        (edir / ev_name).write_bytes(ev_bytes)
        (edir / sched_name).write_bytes(sched_bytes)
        ev_sha = hashlib.sha256(ev_bytes).hexdigest()
        sched_sha = hashlib.sha256(sched_bytes).hexdigest()
        manifest = {
            "schema_version": 1, "symbol": symbol, "target_session": "2026-10-01",
            "authority_source": sponsors[symbol], "official_url": urls[symbol],
            "product_identity": identities[symbol], "evidence_file": ev_name,
            "evidence_sha256": ev_sha,
            "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
            "retrieval_representation": "NORMALIZED_RETRIEVAL_REPRESENTATION",
            "scope_type": "NO_EVENT_SCOPE",
            "schedule_evidence": {"file": sched_name, "sha256": sched_sha},
            "note": "Fixture bundle.",
        }
        (sdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        digests[symbol] = {"sha": ev_sha, "ref": ev_name, "sched_sha": sched_sha}
    return {"root": root, "digests": digests}


def _mint_intent(
    target: str = "2026-10-01",
    ordinal: int = 2,
    prev_sha: str | None = None,
    created: str = "2026-09-30T12:00:00+00:00",
) -> Dict[str, Any]:
    intent = ObservationIntent(
        hypothesis_id="HYP_011",
        target_session=date.fromisoformat(target),
        observation_ordinal=ordinal,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        previous_observation_sha256=prev_sha,
        backfill_allowed=False,
        automatic_skip_allowed=False,
        created_at_utc=datetime.fromisoformat(created),
        authority_identity="OPERATOR_FIXTURE",
    )
    return intent.canonical_doc()


def _mint_authority(
    tmp_path: Path,
    ca_path: Path,
    prev_sha: str,
    target: str = "2026-10-01",
    ordinal: int = 2,
    attempt: int = 1,
    valid_after: str = "2026-10-01T00:00:00+00:00",
    expires_at: str = "2026-10-02T00:00:00+00:00",
    runtime_sha: str = RUNTIME_SHA,
    registry_dir: Path | None = None,
) -> Path:
    # F17: preregister the intent first; the authority binds the REGISTERED
    # digest (server-side timestamp), never a self-declared one.
    registry = registry_dir or (tmp_path / "intent_registry")
    reg_path = register_observation_intent(
        registry_dir=registry, calendar=NyseCa1Calendar(),
        target_session=date.fromisoformat(target), observation_ordinal=ordinal,
        previous_observation_sha256=prev_sha,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        authority_identity="OPERATOR_FIXTURE",
        now_utc=datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc),
    )
    registered_sha = str(json.loads(reg_path.read_text(encoding="utf-8"))["intent_sha256"])
    intent_doc = _mint_intent(target=target, ordinal=ordinal, prev_sha=prev_sha)
    cal = NyseCa1Calendar()
    validate_observation_intent(
        intent_doc, cal, datetime.fromisoformat(valid_after)
    )
    ca_bytes = ca_path.read_bytes()
    doc = {
        "schema_version": 1,
        "intent_sha256": registered_sha,
        "intent": intent_doc,
        "runtime_commit_sha": runtime_sha,
        "target_session": target,
        "observation_ordinal": ordinal,
        "dispatch_attempt": attempt,
        "valid_after_utc": valid_after,
        "expires_at_utc": expires_at,
        "ca_manifest_sha256": hashlib.sha256(ca_bytes).hexdigest(),
        "paper_trading": False,
        "live_trading": False,
        "real_capital_authority_usd": "0.00",
        "no_real_orders": True,
        "authority_identity": "OPERATOR_FIXTURE",
    }
    path = tmp_path / f"dispatch_authority_{ordinal}_{attempt}.json"
    path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return path


def _read_json_dict(path: Path) -> Dict[str, Any]:
    loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"expected JSON object at {path}")
    return dict(loaded)


def _live_argv(
    authority_path: Path | None, ordinal: int = 2, attempt: int = 1,
    bundle_root: Path | None = None,
) -> List[str]:
    auth_token = (
        f"AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_{ordinal:04d}"
        if attempt <= 1
        else f"AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_{ordinal:04d}_ATTEMPT_{attempt:04d}"
    )
    argv = [
        "--execute-network",
        "--authorization",
        auth_token,
        "--ordinal",
        str(ordinal),
        "--dispatch-attempt",
        str(attempt),
    ]
    if authority_path is not None:
        argv += ["--dispatch-authority", str(authority_path)]
    if bundle_root is not None:
        argv += ["--ca-evidence-bundle", str(bundle_root)]
    return argv


# =============================================================================
# F15 intent validation units
# =============================================================================


def test_f15_intent_must_be_pre_locked_before_target_open() -> None:
    """Inclusion intent created at/after target open is rejected (C time model)."""
    cal = NyseCa1Calendar()
    # 2026-10-01 opens 13:30Z; intent stamped after open is too late.
    late = _mint_intent(created="2026-10-01T14:00:00+00:00")
    with pytest.raises(DataContractError, match="SHADOW_INTENT_NOT_PRE_LOCKED"):
        validate_observation_intent(
            late, cal, datetime(2026, 10, 1, 15, 0, 0, tzinfo=timezone.utc)
        )


def test_f15_intent_field_discipline() -> None:
    cal = NyseCa1Calendar()
    now = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    base = _mint_intent()
    validated = validate_observation_intent(base, cal, now)
    assert validated.target_session == date(2026, 10, 1)

    bad_backfill = dict(base, backfill_allowed=True)
    with pytest.raises(DataContractError, match="BACKFILL_NOT_FORBIDDEN"):
        validate_observation_intent(bad_backfill, cal, now)
    bad_skip = dict(base, automatic_skip_allowed=True)
    with pytest.raises(DataContractError, match="SKIP_NOT_FORBIDDEN"):
        validate_observation_intent(bad_skip, cal, now)
    bad_prev = dict(base, previous_observation_sha256="not-a-sha")
    with pytest.raises(DataContractError, match="BAD_PREVIOUS_SHA"):
        validate_observation_intent(bad_prev, cal, now)


# =============================================================================
# F15 authority validation units
# =============================================================================


def _valid_authority_doc(tmp_path: Path, prev_sha: str) -> Dict[str, Any]:
    ca_path = _write_ca_file(tmp_path)
    auth_path = _mint_authority(tmp_path, ca_path, prev_sha)
    return _read_json_dict(auth_path)


def test_f15_authority_rejects_mismatches(tmp_path: Path) -> None:
    cal = NyseCa1Calendar()
    prev_sha = "11" * 32
    doc = _valid_authority_doc(tmp_path, prev_sha)
    ca_bytes = (tmp_path / "ca_2026-10-01.json").read_bytes()
    ca_sha = hashlib.sha256(ca_bytes).hexdigest()
    now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    good_kwargs: Dict[str, Any] = dict(
        calendar=cal,
        now_utc=now,
        target_session=date(2026, 10, 1),
        observation_ordinal=2,
        dispatch_attempt=1,
        state_prev_sha256=prev_sha,
        runtime_sha=RUNTIME_SHA,
        ca_file_sha256=ca_sha,
    )
    validated = validate_dispatch_authority(doc, **good_kwargs)
    assert validated.target_session == date(2026, 10, 1)

    def _break(**over: Any) -> Dict[str, Any]:
        broken: Dict[str, Any] = json.loads(json.dumps(doc))
        broken.update(over)
        return broken

    with pytest.raises(DataContractError, match="RUNTIME_MISMATCH"):
        validate_dispatch_authority(_break(runtime_commit_sha="d" * 40), **good_kwargs)
    with pytest.raises(DataContractError, match="ORDINAL_MISMATCH"):
        validate_dispatch_authority(_break(observation_ordinal=3), **good_kwargs)
    with pytest.raises(DataContractError, match="ATTEMPT_MISMATCH"):
        validate_dispatch_authority(_break(dispatch_attempt=2), **good_kwargs)
    with pytest.raises(DataContractError, match="CHAIN_HEAD_MISMATCH"):
        validate_dispatch_authority(
            _break(), **dict(good_kwargs, state_prev_sha256="22" * 32)
        )
    with pytest.raises(DataContractError, match="CA_SHA_MISMATCH"):
        validate_dispatch_authority(
            _break(), **dict(good_kwargs, ca_file_sha256="33" * 32)
        )
    with pytest.raises(DataContractError, match="LOCKS_INVALID"):
        validate_dispatch_authority(_break(paper_trading=True), **good_kwargs)
    expired = dict(good_kwargs, now_utc=datetime(2026, 10, 3, tzinfo=timezone.utc))
    with pytest.raises(DataContractError, match="OUTSIDE_VALIDITY_WINDOW"):
        validate_dispatch_authority(doc, **expired)
    # Not-yet-valid: after intent creation (09-30 noon) but before valid_after.
    early = dict(
        good_kwargs, now_utc=datetime(2026, 9, 30, 18, 0, 0, tzinfo=timezone.utc)
    )
    with pytest.raises(DataContractError, match="OUTSIDE_VALIDITY_WINDOW"):
        validate_dispatch_authority(doc, **early)


def test_f15_ledger_consume_is_single_use(tmp_path: Path) -> None:
    key = attempt_ledger_key(
        authority_sha256=None,
        authorization="AUTH_X",
        observation_ordinal=1,
        dispatch_attempt=1,
        target_session=date(2026, 9, 29),
    )
    entry = consume_dispatch_attempt(
        tmp_path, key, {"authorization": "AUTH_X"}
    )
    assert entry.is_file()
    with pytest.raises(DataContractError, match="BLOCK_DISPATCH_AUTHORITY_REPLAY"):
        consume_dispatch_attempt(tmp_path, key, {"authorization": "AUTH_X"})


# =============================================================================
# F15 runner enforcement
# =============================================================================


def test_f15_live_ordinal2_without_authority_blocked_zero_network(tmp_path: Path) -> None:
    """Bare-token live dispatch for ordinal >= 2 is rejected before network."""
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_obs1_state(tmp_path / "s", binding)
    with pytest.raises(DataContractError, match="SHADOW_DISPATCH_AUTHORITY_REQUIRED"):
        runner.main(
            _live_argv(None),
            _now_utc=datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=_failing_client(),
            _credential_provider=_mock_creds(),
            _stage_c_binding_path=binding["path"],
            _runtime_sha=RUNTIME_SHA,
        )


def _run_ordinal2_success(tmp_path: Path) -> Path:
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_obs1_state(tmp_path / "s", binding)
    state_doc = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    prev_sha = state_doc["last_observation_sha256"]
    bundle = _write_ca_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, digests=bundle["digests"])
    auth_path = _mint_authority(
        tmp_path, ca_path, prev_sha, registry_dir=state_dir / "intent_registry")
    argv = _live_argv(auth_path, bundle_root=bundle["root"]) + [
        "--ca-determinations", str(ca_path)]
    calls: List[Any] = []
    rc = runner.main(
        argv,
        _now_utc=datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc),
        _state_dir=state_dir,
        _client=_mock_bars_client(calls),
        _credential_provider=_mock_creds(),
        _stage_c_binding_path=binding["path"],
        _runtime_sha=RUNTIME_SHA,
    )
    assert rc == 0
    assert len(calls) == 6
    return state_dir


def test_f15_valid_authority_dispatch_succeeds_and_consumes(tmp_path: Path) -> None:
    """A valid authority dispatches once and leaves a ledger entry."""
    state_dir = _run_ordinal2_success(tmp_path)
    ledger_dir = state_dir / "dispatch_ledger"
    entries = list(ledger_dir.glob("*.json"))
    assert len(entries) == 1
    obs2 = json.loads(
        (state_dir / "observations" / "2026-10-01.json").read_text(encoding="utf-8")
    )
    assert obs2["session"] == "2026-10-01"


def test_f18_local_failure_consumes_nothing_zero_network(tmp_path: Path) -> None:
    """F18: a first invocation failing local preflight (bad CA) burns nothing.

    The identical replay must re-raise the SAME validation error — not a
    ledger replay block — proving the attempt was never consumed.
    """
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_obs1_state(tmp_path / "s", binding)
    state_doc = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    prev_sha = state_doc["last_observation_sha256"]
    bundle = _write_ca_bundle(tmp_path)
    bad_ca = tmp_path / "ca_bad.json"
    bad_ca.write_bytes(b'{"ACWI": {"has_event": "maybe"}}')
    auth_path = _mint_authority(
        tmp_path, bad_ca, prev_sha, registry_dir=state_dir / "intent_registry")
    argv = _live_argv(auth_path, bundle_root=bundle["root"]) + [
        "--ca-determinations", str(bad_ca)]
    now = datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc)
    common = dict(
        _now_utc=now,
        _state_dir=state_dir,
        _client=_failing_client(),
        _credential_provider=_mock_creds(),
        _stage_c_binding_path=binding["path"],
        _runtime_sha=RUNTIME_SHA,
    )
    with pytest.raises(DataContractError):
        runner.main(argv, **common)
    assert not (state_dir / "observations" / "2026-10-01.json").exists()
    ledger = state_dir / "dispatch_ledger"
    assert len(list(ledger.glob("*.json"))) == 0 if ledger.is_dir() else True
    # Identical replay: same local failure, still nothing consumed.
    with pytest.raises(DataContractError):
        runner.main(argv, **common)
    assert len(list(ledger.glob("*.json"))) == 0 if ledger.is_dir() else True


def test_f15_post_success_replay_blocked_zero_network(tmp_path: Path) -> None:
    """Identical replay after a committed dispatch fails closed (ordinal guard)."""
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_obs1_state(tmp_path / "s", binding)
    state_doc = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    prev_sha = state_doc["last_observation_sha256"]
    bundle = _write_ca_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, digests=bundle["digests"])
    auth_path = _mint_authority(
        tmp_path, ca_path, prev_sha, registry_dir=state_dir / "intent_registry")
    argv = _live_argv(auth_path, bundle_root=bundle["root"]) + [
        "--ca-determinations", str(ca_path)]
    now = datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc)
    calls: List[Any] = []
    assert (
        runner.main(
            argv,
            _now_utc=now,
            _state_dir=state_dir,
            _client=_mock_bars_client(calls),
            _credential_provider=_mock_creds(),
            _stage_c_binding_path=binding["path"],
            _runtime_sha=RUNTIME_SHA,
        )
        == 0
    )
    assert (state_dir / "observations" / "2026-10-01.json").is_file()
    # State advanced: the spent (ordinal, attempt) no longer authorizes anything.
    with pytest.raises(DataContractError, match="BLOCK_SHADOW_STATE_INTEGRITY|MISMATCH|REPLAY"):
        runner.main(
            argv,
            _now_utc=now,
            _state_dir=state_dir,
            _client=_failing_client(),
            _credential_provider=_mock_creds(),
            _stage_c_binding_path=binding["path"],
            _runtime_sha=RUNTIME_SHA,
        )
    assert len(calls) == 6


def test_f18_transport_crash_consumes_and_blocks_replay(tmp_path: Path) -> None:
    """F18: only a post-consume transport crash burns the attempt.

    A fully valid ceremony with a transport that explodes at fetch consumes
    exactly one ledger entry; the identical replay then hits the ledger.
    """
    import httpx as _httpx

    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_obs1_state(tmp_path / "s", binding)
    state_doc = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    prev_sha = state_doc["last_observation_sha256"]
    bundle = _write_ca_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, digests=bundle["digests"])
    auth_path = _mint_authority(
        tmp_path, ca_path, prev_sha, registry_dir=state_dir / "intent_registry")
    argv = _live_argv(auth_path, bundle_root=bundle["root"]) + [
        "--ca-determinations", str(ca_path)]
    now = datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc)

    def _boom(request: _httpx.Request) -> _httpx.Response:
        raise _httpx.ConnectError("simulated post-consume transport failure")

    boom_client = HYP011AlpacaClient(
        transport=_httpx.MockTransport(_boom), credential_provider=_mock_creds())
    common = dict(
        _now_utc=now, _state_dir=state_dir,
        _credential_provider=_mock_creds(),
        _stage_c_binding_path=binding["path"], _runtime_sha=RUNTIME_SHA)
    with pytest.raises(Exception):
        runner.main(argv, _client=boom_client, **common)
    assert len(list((state_dir / "dispatch_ledger").glob("*.json"))) == 1
    assert not (state_dir / "observations" / "2026-10-01.json").exists()
    # Identical reuse: ledger blocks before network/state effects.
    with pytest.raises(DataContractError, match="BLOCK_DISPATCH_AUTHORITY_REPLAY"):
        runner.main(argv, _client=_failing_client(), **common)


def test_f15_bare_token_replay_blocked(tmp_path: Path) -> None:
    """Ordinal-1 bare-token live replay blocks on the ledger (no network).

    First invocation crashes at fetch (403, pre-commit); the identical replay
    must hit the single-use ledger rather than re-executing.
    """
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = tmp_path / "fresh"
    now = datetime(2026, 9, 30, 21, 0, 0, tzinfo=timezone.utc)
    argv = [
        "--execute-network",
        "--authorization",
        "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001_ATTEMPT_0002",
        "--ordinal",
        "1",
        "--dispatch-attempt",
        "2",
    ]

    def _denied_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": 40010001, "message": "SIP denied"})

    denied_client = HYP011AlpacaClient(
        transport=httpx.MockTransport(_denied_handler),
        credential_provider=_mock_creds(),
    )
    common = dict(
        _now_utc=now,
        _state_dir=state_dir,
        _credential_provider=_mock_creds(),
        _stage_c_binding_path=binding["path"],
        _runtime_sha=RUNTIME_SHA,
    )
    with pytest.raises(DataContractError, match="HTTP 403"):
        runner.main(argv, _client=denied_client, **common)
    assert not (state_dir / "observations" / "2026-09-30.json").exists()
    # Same bare token replayed: ledger blocks before network/state effects.
    with pytest.raises(DataContractError, match="BLOCK_DISPATCH_AUTHORITY_REPLAY"):
        runner.main(argv, _client=_failing_client(), **common)


# =============================================================================
# F16 runner enforcement + provenance
# =============================================================================


def test_f16_no_scope_intake_blocked_zero_network(tmp_path: Path) -> None:
    """A no-event intake without scope_evidence blocks before any network."""
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_obs1_state(tmp_path / "s", binding)
    state_doc = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    prev_sha = state_doc["last_observation_sha256"]
    bare_doc = {
        symbol: {
            "symbol": symbol,
            "session": "2026-10-01",
            "has_event": False,
            "authority_source": sponsor,
            "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
            "source_sha256": FAKE_SHA,
            "evidence_ref": f"evidence/{symbol.lower()}-scope-fixture.pdf",
        }
        for symbol, sponsor in (
            ("ACWI", "BLACKROCK_ISHARES_OFFICIAL"),
            ("AGG", "BLACKROCK_ISHARES_OFFICIAL"),
            ("SPY", "STATE_STREET_SPDR_OFFICIAL"),
        )
    }
    ca_path = tmp_path / "ca_bare.json"
    ca_path.write_bytes((json.dumps(bare_doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    bundle = _write_ca_bundle(tmp_path)
    auth_path = _mint_authority(
        tmp_path, ca_path, prev_sha, registry_dir=state_dir / "intent_registry")
    argv = _live_argv(auth_path, bundle_root=bundle["root"]) + [
        "--ca-determinations", str(ca_path)]
    with pytest.raises(DataContractError, match="CA_NO_EVENT_SCOPE_REQUIRED"):
        runner.main(
            argv,
            _now_utc=datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=_failing_client(),
            _credential_provider=_mock_creds(),
            _stage_c_binding_path=binding["path"],
            _runtime_sha=RUNTIME_SHA,
        )


def test_f16_bad_source_sha_blocked_zero_network(tmp_path: Path) -> None:
    """A malformed source_sha256 blocks before any network."""
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_obs1_state(tmp_path / "s", binding)
    state_doc = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    prev_sha = state_doc["last_observation_sha256"]
    bundle = _write_ca_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, digests=bundle["digests"])
    doc = json.loads(ca_path.read_text(encoding="utf-8"))
    doc["ACWI"]["source_sha256"] = "not-a-sha"
    ca_path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    auth_path = _mint_authority(
        tmp_path, ca_path, prev_sha, registry_dir=state_dir / "intent_registry")
    argv = _live_argv(auth_path, bundle_root=bundle["root"]) + [
        "--ca-determinations", str(ca_path)]
    with pytest.raises(DataContractError, match="CA_SOURCE_SHA_INVALID"):
        runner.main(
            argv,
            _now_utc=datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=_failing_client(),
            _credential_provider=_mock_creds(),
            _stage_c_binding_path=binding["path"],
            _runtime_sha=RUNTIME_SHA,
        )


def test_f16_authority_ca_sha_mismatch_blocked_zero_network(tmp_path: Path) -> None:
    """Authority bound to different CA bytes than supplied blocks pre-network."""
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_obs1_state(tmp_path / "s", binding)
    state_doc = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    prev_sha = state_doc["last_observation_sha256"]
    bundle = _write_ca_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, digests=bundle["digests"])
    auth_path = _mint_authority(
        tmp_path, ca_path, prev_sha, registry_dir=state_dir / "intent_registry")
    # Mutate the CA file AFTER the authority bound its bytes.
    doc = json.loads(ca_path.read_text(encoding="utf-8"))
    doc["ACWI"]["evidence_ref"] = "evidence/mutated.pdf"
    ca_path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    argv = _live_argv(auth_path, bundle_root=bundle["root"]) + [
        "--ca-determinations", str(ca_path)]
    with pytest.raises(DataContractError, match="SHADOW_AUTHORITY_CA_SHA_MISMATCH"):
        runner.main(
            argv,
            _now_utc=datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc),
            _state_dir=state_dir,
            _client=_failing_client(),
            _credential_provider=_mock_creds(),
            _stage_c_binding_path=binding["path"],
            _runtime_sha=RUNTIME_SHA,
        )


def test_f16_provenance_survives_into_observation(tmp_path: Path) -> None:
    """Sealed corporate_actions retain evidence_ref + scope_evidence + authority."""
    state_dir = _run_ordinal2_success(tmp_path)
    obs2 = json.loads(
        (state_dir / "observations" / "2026-10-01.json").read_text(encoding="utf-8")
    )
    for symbol, sponsor in (
        ("ACWI", "BLACKROCK_ISHARES_OFFICIAL"),
        ("AGG", "BLACKROCK_ISHARES_OFFICIAL"),
        ("SPY", "STATE_STREET_SPDR_OFFICIAL"),
    ):
        manifest = json.loads(
            (tmp_path / "ca_bundle_2026-10-01" / symbol / "manifest.json")
            .read_text(encoding="utf-8"))
        section = obs2["corporate_actions"][symbol]
        assert section["authority_source"] == sponsor
        # F19: sealed digest is the recomputed bundle-evidence digest.
        assert section["source_sha256"] == manifest["evidence_sha256"]
        assert section["evidence_ref"] == manifest["evidence_file"]
        assert section["scope_evidence"]["schedule_sha256"] == manifest[
            "schedule_evidence"]["sha256"]
        assert section["has_event"] is False
