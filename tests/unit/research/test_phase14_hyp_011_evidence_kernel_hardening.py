"""F17/F18/F19 evidence-kernel hardening tests (zero network, zero broker).

F17: create-once preregistered ObservationIntent (server-side timestamp,
O_EXCL, strict pre-open). Backdated unregistered JSON can never dispatch.
F18: single TRUE network-attempt boundary — every local preflight passes
before consume_dispatch_attempt; local failures leave the ledger unchanged
with NETWORK_REQUESTS = 0.
F19: CA evidence bundles verified from raw preserved bytes + frozen
sponsor/product identity (239707 is IWB, never ACWI).

Fixtures are synthetic; no real observation/state is touched.
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
    load_registered_intent,
    register_observation_intent,
    verify_registered_intent_binding,
)
from acash.research.hyp_011.shadow_ca_bundle import (
    verify_determination_evidence_binding,
    verify_evidence_bundle,
)

RUNTIME_SHA = "c" * 40
TARGET = date(2026, 10, 1)
TARGET_OPEN = datetime(2026, 10, 1, 13, 30, 0, tzinfo=timezone.utc)
PRE_OPEN = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
LIVE_NOW = datetime(2026, 10, 1, 21, 0, 0, tzinfo=timezone.utc)
PREV_SHA = "aa" * 32

SYMBOLS = ("ACWI", "AGG", "SPY")
SPONSORS = {
    "ACWI": "BLACKROCK_ISHARES_OFFICIAL",
    "AGG": "BLACKROCK_ISHARES_OFFICIAL",
    "SPY": "STATE_STREET_SPDR_OFFICIAL",
}
OFFICIAL_URLS = {
    "ACWI": "https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf",
    "AGG": "https://www.ishares.com/us/products/239458/ishares-core-us-aggregate-bond-etf",
    "SPY": "https://www.ssga.com/us/en/institutional/etfs/spdr-sp-500-etf-trust-spy",
}
PRODUCT_IDENTITY = {
    "ACWI": {"product_id": "239600", "ticker": "ACWI", "sponsor": "BLACKROCK_ISHARES_OFFICIAL"},
    "AGG": {"product_id": "239458", "ticker": "AGG", "sponsor": "BLACKROCK_ISHARES_OFFICIAL"},
    "SPY": {"schedule": "SSGA_OFFICIAL_2026_DISTRIBUTIONS", "ticker": "SPY", "sponsor": "STATE_STREET_SPDR_OFFICIAL"},
}


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


def _no_creds() -> EnvAlpacaCredentialProvider:
    return EnvAlpacaCredentialProvider(environ={})


def _mock_bars_client(calls: List[Any]) -> Any:
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            200,
            json={"bars": [{"t": "2026-10-01T05:00:00Z", "o": 100.0, "h": 101.0,
                            "l": 99.0, "c": 100.5, "v": 1000}]},
        )

    return HYP011AlpacaClient(
        transport=httpx.MockTransport(handler), credential_provider=_mock_creds()
    )


def _failing_client() -> Any:
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be reached")

    return HYP011AlpacaClient(
        transport=httpx.MockTransport(handler), credential_provider=_mock_creds()
    )


def _exploding_client() -> Any:
    """Fails INSIDE transport (simulates post-consume transport crash)."""
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated transport failure")

    return HYP011AlpacaClient(
        transport=httpx.MockTransport(handler), credential_provider=_mock_creds()
    )


def _fixture_binding(tmp_path: Path) -> Dict[str, Any]:
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
        "locks": {"paper_trading": False, "live_trading": False,
                  "real_capital_authority_usd": "0.00", "no_real_orders": True},
    }
    raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    binding_path.write_bytes(raw)
    return {"path": binding_path, "sha256": hashlib.sha256(raw).hexdigest()}


def _reconciled_state(tmp_path: Path, binding: Dict[str, Any]) -> Path:
    state_dir = tmp_path / "prospective"
    obs_dir = state_dir / "observations"
    obs_dir.mkdir(parents=True)
    frag_s = {"holdings": {"ACWI": 500, "AGG": 300}, "cash": "20000.00",
              "market_value": "80000.00", "receivable": "0", "equity": "100000.00",
              "daily_return": "0.00000000", "running_peak": "100000.00",
              "drawdown": "0.00000000", "entitlements": [], "trades": []}
    frag_b = {"entry": {"side": "BUY", "quantity": "200", "fill": "500.00"},
              "entitlements": [], "shares": 200, "cash": "0.00",
              "market_value": "100000.00", "receivable": "0", "equity": "100000.00",
              "daily_return": "0.00000000", "running_peak": "100000.00",
              "drawdown": "0.00000000"}
    obs_doc = {"schema_version": 1, "hypothesis_id": "HYP_011", "session": "2026-09-30",
               "processed_at_utc": "2026-09-30T20:20:00+00:00",
               "previous_observation_sha256": None,
               "authority": {"activation_binding": str(binding["path"]),
                             "activation_binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
                             "activation_binding_sha256": binding["sha256"],
                             "activation_binding_commit_sha": "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
                             "activation_binding_commit_utc": "2026-09-29T17:12:46+00:00",
                             "operational_activation_session": "2026-09-30",
                             "ordinal": 1, "dispatch_attempt": 2},
               "strategy": frag_s, "benchmark": frag_b}
    obs_raw = json.dumps(obs_doc, indent=2, sort_keys=True) + "\n"
    (obs_dir / "2026-09-30.json").write_bytes(obs_raw.encode("utf-8"))
    obs_sha = hashlib.sha256(obs_raw.encode("utf-8")).hexdigest()
    state_doc = {"schema_version": 1, "hypothesis_id": "HYP_011",
                 "activation_session": "2026-09-30", "starting_aum": "100000.00",
                 "locks": {"paper_authorized": False, "live_authorized": False,
                           "capital_authority_usd": "0.00", "no_real_orders": True},
                 "activation_authority_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
                 "activation_authority_sha256": binding["sha256"],
                 "activation_commit_sha": "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
                 "observed_sessions": ["2026-09-30"], "observed_session_count": 1,
                 "last_processed_session": "2026-09-30", "last_observation_sha256": obs_sha,
                 "strategy": {"cash": "20000.00", "holdings": {"ACWI": 500, "AGG": 300},
                              "receivables": [], "running_peak": "100000.00",
                              "previous_equity": "100000.00"},
                 "benchmark": {"cash": "0.00", "SPY_shares": 200, "receivables": [],
                               "running_peak": "100000.00", "previous_equity": "100000.00",
                               "entered": True},
                 "last_closes_raw": {"ACWI": "100.00", "AGG": "100.00", "SPY": "500.00"},
                 "last_closes_split": {"ACWI": "100.00", "AGG": "100.00", "SPY": "500.00"},
                 "completed_annual_rebalances": 0}
    (state_dir / "state.json").write_text(json.dumps(state_doc, indent=2), encoding="utf-8")
    return state_dir


def _register(tmp_path: Path, state_dir: Path, prev_sha: str,
              at: datetime = PRE_OPEN) -> str:
    registry = state_dir / "intent_registry"
    path = register_observation_intent(
        registry_dir=registry, calendar=NyseCa1Calendar(), target_session=TARGET,
        observation_ordinal=2, previous_observation_sha256=prev_sha,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        authority_identity="OPERATOR_FIXTURE", now_utc=at,
    )
    stored = json.loads(path.read_text(encoding="utf-8"))
    return str(stored["intent_sha256"])


def _write_bundle(tmp_path: Path, name: str = "ca_bundle_2026-10-01") -> Dict[str, Any]:
    """Per-symbol evidence bundles with REAL digests over fixture bytes."""
    root = tmp_path / name
    digests: Dict[str, Dict[str, str]] = {}
    for symbol in SYMBOLS:
        sdir = root / symbol
        edir = sdir / "evidence"
        edir.mkdir(parents=True)
        ev_bytes = f"OFFICIAL-FIXTURE-EVIDENCE::{symbol}::2026-10-01\n".encode()
        sched_bytes = f"OFFICIAL-FIXTURE-SCHEDULE::{symbol}::2026-10-01\n".encode()
        ev_name = f"{symbol.lower()}-scope-fixture.pdf"
        sched_name = f"{symbol.lower()}-schedule-fixture.pdf"
        (edir / ev_name).write_bytes(ev_bytes)
        (edir / sched_name).write_bytes(sched_bytes)
        ev_sha = hashlib.sha256(ev_bytes).hexdigest()
        sched_sha = hashlib.sha256(sched_bytes).hexdigest()
        manifest = {
            "schema_version": 1, "symbol": symbol, "target_session": "2026-10-01",
            "authority_source": SPONSORS[symbol], "official_url": OFFICIAL_URLS[symbol],
            "product_identity": PRODUCT_IDENTITY[symbol], "evidence_file": ev_name,
            "evidence_sha256": ev_sha, "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
            "scope_type": "NO_EVENT_SCOPE",
            "schedule_evidence": {"file": sched_name, "sha256": sched_sha},
            "note": "Fixture bundle for hardening tests.",
        }
        (sdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        digests[symbol] = {"sha": ev_sha, "ref": ev_name, "sched_sha": sched_sha}
    return {"root": root, "digests": digests}


def _write_ca_file(tmp_path: Path, digests: Dict[str, Dict[str, str]],
                   name: str = "ca_2026-10-01.json") -> Path:
    doc = {
        symbol: {
            "symbol": symbol, "session": "2026-10-01", "has_event": False,
            "authority_source": SPONSORS[symbol],
            "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
            "source_sha256": digests[symbol]["sha"],
            "evidence_ref": digests[symbol]["ref"],
            "scope_evidence": {
                "schedule_id": f"FIXTURE_OFFICIAL_SCOPE_{symbol}_2026_10_01",
                "schedule_sha256": digests[symbol]["sched_sha"],
                "scope_note": "Fixture scope.",
                "retrieved_at_utc": "2026-10-01T12:00:00+00:00",
            },
        }
        for symbol in SYMBOLS
    }
    path = tmp_path / name
    path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return path


def _mint_authority(tmp_path: Path, ca_path: Path, prev_sha: str,
                    registered_sha: str,
                    expires_at: str = "2026-10-02T00:00:00+00:00") -> Path:
    intent_doc = {
        "schema_version": 1, "hypothesis_id": "HYP_011",
        "target_session": "2026-10-01", "observation_ordinal": 2,
        "scientific_inclusion_intent": "INCLUDE_PROSPECTIVE",
        "previous_observation_sha256": prev_sha, "backfill_allowed": False,
        "automatic_skip_allowed": False,
        "created_at_utc": "2026-09-30T12:00:00+00:00",
        "authority_identity": "OPERATOR_FIXTURE",
    }
    ca_bytes = ca_path.read_bytes()
    doc = {
        "schema_version": 1, "intent_sha256": registered_sha, "intent": intent_doc,
        "runtime_commit_sha": RUNTIME_SHA, "target_session": "2026-10-01",
        "observation_ordinal": 2, "dispatch_attempt": 1,
        "valid_after_utc": "2026-10-01T00:00:00+00:00",
        "expires_at_utc": expires_at,
        "ca_manifest_sha256": hashlib.sha256(ca_bytes).hexdigest(),
        "paper_trading": False, "live_trading": False,
        "real_capital_authority_usd": "0.00", "no_real_orders": True,
        "authority_identity": "OPERATOR_FIXTURE",
    }
    path = tmp_path / "dispatch_authority_2_1.json"
    path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return path


def _live_argv(auth_path: Path, ca_path: Path, bundle_root: Path,
               extra: List[str] | None = None) -> List[str]:
    argv = ["--execute-network", "--authorization",
            "AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0002",
            "--ordinal", "2", "--dispatch-attempt", "1",
            "--dispatch-authority", str(auth_path),
            "--ca-determinations", str(ca_path),
            "--ca-evidence-bundle", str(bundle_root)]
    return argv + (extra or [])


def _prev_sha(state_dir: Path) -> str:
    return str(json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
               ["last_observation_sha256"])


def _ledger_entries(state_dir: Path) -> List[Path]:
    ledger = state_dir / "dispatch_ledger"
    return list(ledger.glob("*.json")) if ledger.is_dir() else []


# =============================================================================
# F17 units
# =============================================================================


def test_f17_register_before_open_pass(tmp_path: Path) -> None:
    registry = tmp_path / "reg"
    path = register_observation_intent(
        registry_dir=registry, calendar=NyseCa1Calendar(), target_session=TARGET,
        observation_ordinal=2, previous_observation_sha256=PREV_SHA,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        authority_identity="OPERATOR_FIXTURE", now_utc=PRE_OPEN)
    assert path.is_file()
    loaded = load_registered_intent(registry, TARGET, 2)
    assert loaded.registered_at_utc == PRE_OPEN
    assert loaded.previous_observation_sha256 == PREV_SHA


def test_f17_register_at_or_after_open_blocked(tmp_path: Path) -> None:
    registry = tmp_path / "reg"
    with pytest.raises(DataContractError, match="REGISTRATION_CLOSED"):
        register_observation_intent(
            registry_dir=registry, calendar=NyseCa1Calendar(), target_session=TARGET,
            observation_ordinal=2, previous_observation_sha256=PREV_SHA,
            scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
            authority_identity="OPERATOR_FIXTURE", now_utc=TARGET_OPEN)
    with pytest.raises(DataContractError, match="REGISTRATION_CLOSED"):
        register_observation_intent(
            registry_dir=registry, calendar=NyseCa1Calendar(), target_session=TARGET,
            observation_ordinal=2, previous_observation_sha256=PREV_SHA,
            scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
            authority_identity="OPERATOR_FIXTURE",
            now_utc=datetime(2026, 10, 1, 15, 0, 0, tzinfo=timezone.utc))


def test_f17_backdated_unregistered_intent_blocked(tmp_path: Path) -> None:
    registry = tmp_path / "reg"
    with pytest.raises(DataContractError, match="REGISTERED_INTENT_MISSING"):
        verify_registered_intent_binding(
            registry_dir=registry, bound_intent_sha256="ab" * 32,
            target_session=TARGET, observation_ordinal=2, state_prev_sha256=PREV_SHA)


def test_f17_modified_registered_intent_blocked(tmp_path: Path) -> None:
    registry = tmp_path / "reg"
    register_observation_intent(
        registry_dir=registry, calendar=NyseCa1Calendar(), target_session=TARGET,
        observation_ordinal=2, previous_observation_sha256=PREV_SHA,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        authority_identity="OPERATOR_FIXTURE", now_utc=PRE_OPEN)
    entry = registry / "2026-10-01_ord0002.json"
    doc = json.loads(entry.read_text(encoding="utf-8"))
    doc["scientific_inclusion_intent"] = "INCLUDE_SOMETHING_ELSE"
    entry.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match="REGISTERED_INTENT_TAMPERED"):
        load_registered_intent(registry, TARGET, 2)


def test_f17_duplicate_registration_blocked(tmp_path: Path) -> None:
    registry = tmp_path / "reg"
    kwargs: Dict[str, Any] = dict(
        registry_dir=registry, calendar=NyseCa1Calendar(), target_session=TARGET,
        observation_ordinal=2, previous_observation_sha256=PREV_SHA,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        authority_identity="OPERATOR_FIXTURE", now_utc=PRE_OPEN)
    register_observation_intent(**kwargs)
    with pytest.raises(DataContractError, match="ALREADY_REGISTERED"):
        register_observation_intent(**kwargs)


def test_f17_wrong_chain_head_blocked(tmp_path: Path) -> None:
    registry = tmp_path / "reg"
    path = register_observation_intent(
        registry_dir=registry, calendar=NyseCa1Calendar(), target_session=TARGET,
        observation_ordinal=2, previous_observation_sha256=PREV_SHA,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        authority_identity="OPERATOR_FIXTURE", now_utc=PRE_OPEN)
    bound = str(json.loads(path.read_text(encoding="utf-8"))["intent_sha256"])
    with pytest.raises(DataContractError, match="CHAIN_HEAD_MISMATCH"):
        verify_registered_intent_binding(
            registry_dir=registry, bound_intent_sha256=bound,
            target_session=TARGET, observation_ordinal=2,
            state_prev_sha256="bb" * 32)


def test_f17_ordinal1_must_start_chain(tmp_path: Path) -> None:
    with pytest.raises(DataContractError, match="ORDINAL1_MUST_START_CHAIN"):
        register_observation_intent(
            registry_dir=tmp_path / "reg", calendar=NyseCa1Calendar(),
            target_session=TARGET, observation_ordinal=1,
            previous_observation_sha256=PREV_SHA,
            scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
            authority_identity="OPERATOR_FIXTURE", now_utc=PRE_OPEN)


# =============================================================================
# F19 units
# =============================================================================


def test_f19_valid_bundle_and_binding_pass(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    manifest = verify_evidence_bundle(
        bundle["root"] / "ACWI", "ACWI", TARGET, LIVE_NOW)
    assert manifest["product_identity"]["product_id"] == "239600"
    det = {"source_sha256": bundle["digests"]["ACWI"]["sha"],
           "evidence_ref": bundle["digests"]["ACWI"]["ref"]}
    verify_determination_evidence_binding(det, manifest, "ACWI")


def test_f19_invented_digest_blocked(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    manifest_path = bundle["root"] / "ACWI" / "manifest.json"
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    doc["evidence_sha256"] = "de" * 32
    manifest_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match="DIGEST_MISMATCH"):
        verify_evidence_bundle(bundle["root"] / "ACWI", "ACWI", TARGET, LIVE_NOW)


def test_f19_modified_evidence_byte_blocked(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    ev = bundle["root"] / "ACWI" / "evidence" / "acwi-scope-fixture.pdf"
    ev.write_bytes(ev.read_bytes() + b"X")
    with pytest.raises(DataContractError, match="DIGEST_MISMATCH"):
        verify_evidence_bundle(bundle["root"] / "ACWI", "ACWI", TARGET, LIVE_NOW)


def test_f19_missing_evidence_blocked(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    (bundle["root"] / "ACWI" / "evidence" / "acwi-scope-fixture.pdf").unlink()
    with pytest.raises(DataContractError, match="EVIDENCE_ABSENT"):
        verify_evidence_bundle(bundle["root"] / "ACWI", "ACWI", TARGET, LIVE_NOW)


def test_f19_wrong_product_identity_blocked(tmp_path: Path) -> None:
    """239707 (IWB) mislabeled as ACWI evidence is rejected by identity."""
    bundle = _write_bundle(tmp_path)
    manifest_path = bundle["root"] / "ACWI" / "manifest.json"
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    doc["official_url"] = "https://www.ishares.com/us/products/239707/ishares-msci-acwi-etf"
    doc["product_identity"] = {"product_id": "239707", "ticker": "ACWI",
                               "sponsor": "BLACKROCK_ISHARES_OFFICIAL"}
    manifest_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match="PRODUCT_IDENTITY_MISMATCH"):
        verify_evidence_bundle(bundle["root"] / "ACWI", "ACWI", TARGET, LIVE_NOW)


def test_f19_schedule_digest_mismatch_blocked(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    manifest_path = bundle["root"] / "AGG" / "manifest.json"
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(doc["schedule_evidence"], dict)
    doc["schedule_evidence"]["sha256"] = "de" * 32
    manifest_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match="SCHEDULE_DIGEST_MISMATCH"):
        verify_evidence_bundle(bundle["root"] / "AGG", "AGG", TARGET, LIVE_NOW)


def test_f19_determination_binding_mismatch_blocked(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    manifest = verify_evidence_bundle(
        bundle["root"] / "SPY", "SPY", TARGET, LIVE_NOW)
    with pytest.raises(DataContractError, match="DIGEST_NOT_BOUND"):
        verify_determination_evidence_binding(
            {"source_sha256": "de" * 32,
             "evidence_ref": bundle["digests"]["SPY"]["ref"]},
            manifest, "SPY")


# =============================================================================
# F18 runner boundary + full success
# =============================================================================


def _full_ceremony(tmp_path: Path) -> tuple[
    Dict[str, Any], Path, Path, Path, Dict[str, Any]]:
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_state(tmp_path / "s", binding)
    prev = _prev_sha(state_dir)
    registered_sha = _register(tmp_path, state_dir, prev)
    bundle = _write_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, bundle["digests"])
    auth_path = _mint_authority(tmp_path, ca_path, prev, registered_sha)
    return binding, state_dir, ca_path, auth_path, bundle


def _common(state_dir: Path, binding: Dict[str, Any], client: Any,
            now: datetime = LIVE_NOW, creds: Any = None) -> Dict[str, Any]:
    return dict(_now_utc=now, _state_dir=state_dir, _client=client,
                _credential_provider=creds or _mock_creds(),
                _stage_c_binding_path=binding["path"], _runtime_sha=RUNTIME_SHA)


def test_f18_full_success_consumes_once_and_seals(tmp_path: Path) -> None:
    runner = _load_runner_module()
    binding, state_dir, ca_path, auth_path, bundle = _full_ceremony(tmp_path)
    calls: List[Any] = []
    rc = runner.main(
        _live_argv(auth_path, ca_path, bundle["root"]),
        **_common(state_dir, binding, _mock_bars_client(calls)))
    assert rc == 0
    assert len(calls) == 6
    assert len(_ledger_entries(state_dir)) == 1
    obs = json.loads((state_dir / "observations" / "2026-10-01.json").read_text(
        encoding="utf-8"))
    assert obs["session"] == "2026-10-01"


def test_f18_bad_authority_not_consumed_zero_network(tmp_path: Path) -> None:
    runner = _load_runner_module()
    binding, state_dir, ca_path, auth_path, bundle = _full_ceremony(tmp_path)
    doc = json.loads(auth_path.read_text(encoding="utf-8"))
    doc["runtime_commit_sha"] = "d" * 40
    auth_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match="RUNTIME_MISMATCH"):
        runner.main(_live_argv(auth_path, ca_path, bundle["root"]),
                    **_common(state_dir, binding, _failing_client()))
    assert _ledger_entries(state_dir) == []


def test_f18_unregistered_intent_not_consumed_zero_network(tmp_path: Path) -> None:
    """Backdated hand-made authority without registry entry burns nothing."""
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_state(tmp_path / "s", binding)
    prev = _prev_sha(state_dir)
    bundle = _write_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, bundle["digests"])
    auth_path = _mint_authority(tmp_path, ca_path, prev, "ab" * 32)
    with pytest.raises(DataContractError, match="REGISTERED_INTENT"):
        runner.main(_live_argv(auth_path, ca_path, bundle["root"]),
                    **_common(state_dir, binding, _failing_client()))
    assert _ledger_entries(state_dir) == []


def test_f18_bad_ca_not_consumed_zero_network(tmp_path: Path) -> None:
    # Authority binds the BROKEN bytes (so CA-SHA passes) to prove the
    # intake gate itself fails pre-consume.
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_state(tmp_path / "s", binding)
    prev = _prev_sha(state_dir)
    registered_sha = _register(tmp_path, state_dir, prev)
    bundle = _write_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, bundle["digests"])
    doc = json.loads(ca_path.read_text(encoding="utf-8"))
    del doc["AGG"]
    ca_path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode())
    auth_path = _mint_authority(tmp_path, ca_path, prev, registered_sha)
    with pytest.raises(DataContractError, match="SHADOW_CA_MISSING_AGG"):
        runner.main(_live_argv(auth_path, ca_path, bundle["root"]),
                    **_common(state_dir, binding, _failing_client()))
    assert _ledger_entries(state_dir) == []


def test_f18_bad_bundle_not_consumed_zero_network(tmp_path: Path) -> None:
    runner = _load_runner_module()
    binding, state_dir, ca_path, auth_path, bundle = _full_ceremony(tmp_path)
    ev = bundle["root"] / "ACWI" / "evidence" / "acwi-scope-fixture.pdf"
    ev.write_bytes(ev.read_bytes() + b"TAMPER")
    with pytest.raises(DataContractError, match="DIGEST_MISMATCH"):
        runner.main(_live_argv(auth_path, ca_path, bundle["root"]),
                    **_common(state_dir, binding, _failing_client()))
    assert _ledger_entries(state_dir) == []


def test_f18_missing_credentials_not_consumed(tmp_path: Path) -> None:
    runner = _load_runner_module()
    binding, state_dir, ca_path, auth_path, bundle = _full_ceremony(tmp_path)
    rc = runner.main(
        _live_argv(auth_path, ca_path, bundle["root"]),
        **_common(state_dir, binding, _failing_client(), creds=_no_creds()))
    assert rc == 2
    assert _ledger_entries(state_dir) == []


def test_f18_stale_target_not_consumed_zero_network(tmp_path: Path) -> None:
    runner = _load_runner_module()
    binding = _fixture_binding(tmp_path)
    state_dir = _reconciled_state(tmp_path / "s", binding)
    prev = _prev_sha(state_dir)
    registered_sha = _register(tmp_path, state_dir, prev)
    bundle = _write_bundle(tmp_path)
    ca_path = _write_ca_file(tmp_path, bundle["digests"])
    auth_path = _mint_authority(tmp_path, ca_path, prev, registered_sha,
                               expires_at="2026-10-03T00:00:00+00:00")
    stale_now = datetime(2026, 10, 2, 14, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(DataContractError, match="MISSED_REACTIVATION_REQUIRED"):
        runner.main(_live_argv(auth_path, ca_path, bundle["root"]),
                    **_common(state_dir, binding, _failing_client(), now=stale_now))
    assert _ledger_entries(state_dir) == []


def test_f18_too_early_not_consumed_zero_network(tmp_path: Path) -> None:
    runner = _load_runner_module()
    binding, state_dir, ca_path, auth_path, bundle = _full_ceremony(tmp_path)
    early_now = datetime(2026, 10, 1, 20, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(DataContractError, match="NOT_YET_ACCESSIBLE"):
        runner.main(_live_argv(auth_path, ca_path, bundle["root"]),
                    **_common(state_dir, binding, _failing_client(), now=early_now))
    assert _ledger_entries(state_dir) == []


def test_f18_transport_failure_after_consume_burns_and_blocks_replay(
    tmp_path: Path,
) -> None:
    runner = _load_runner_module()
    binding, state_dir, ca_path, auth_path, bundle = _full_ceremony(tmp_path)
    argv = _live_argv(auth_path, ca_path, bundle["root"])
    with pytest.raises(Exception):
        runner.main(argv, **_common(state_dir, binding, _exploding_client()))
    assert len(_ledger_entries(state_dir)) == 1
    assert not (state_dir / "observations" / "2026-10-01.json").exists()
    with pytest.raises(DataContractError, match="BLOCK_DISPATCH_AUTHORITY_REPLAY"):
        runner.main(argv, **_common(state_dir, binding, _failing_client()))


def test_f18_local_preflight_pass_without_consume_or_network(tmp_path: Path) -> None:
    runner = _load_runner_module()
    binding, state_dir, ca_path, auth_path, bundle = _full_ceremony(tmp_path)
    argv = _live_argv(auth_path, ca_path, bundle["root"], ["--local-preflight"])
    rc = runner.main(argv, **_common(state_dir, binding, _failing_client()))
    assert rc == 0
    assert _ledger_entries(state_dir) == []
    assert not (state_dir / "observations" / "2026-10-01.json").exists()
