"""Offline defect acceptance tests for audited findings F01, F02, and F09.

REPAIR STATUS: IMPLEMENTED on fix/hyp011-post-obs1-integrity-continuation-20261001.
These tests prove the formerly reproduced gaps now FAIL CLOSED:

- F01: verify_chain() cross-reconciles state economics against the terminal
  observation artifact; divergent balances raise DataContractError.
- F02: verify_chain() inspects on-disk observations before generating initial
  state; orphans without state.json raise DataContractError.
- F09: load_stage_c_recovery_authority() strictly validates the `locks`
  subdocument; corrupt locks raise DataContractError.

HISTORICAL NOTE: before the repair these same scenarios demonstrated the gaps
(state accepted despite divergence; orphans ignored; corrupt locks loaded).
The assertions below encode the REPAIRED contract.

INVARIANT: PASSING_ACCEPTANCE_TEST != PRODUCTION_DEPLOYED
Repair is implemented and unit-proven on this branch; Obs #1 backward
compatibility is proven separately; deployment remains human-gated.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011 import shadow as SH
from acash.research.hyp_011.shadow import StageCRecoveryAuthority
from acash.research.hyp_011.shadow_ops import (
    build_initial_state,
    verify_chain,
)


def _canonical_stage_c_auth(manifest_path: Path) -> StageCRecoveryAuthority:
    return StageCRecoveryAuthority(
        binding_id="HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
        binding_commit_sha="08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
        binding_commit_utc="2026-09-29T17:12:46+00:00",
        activation_session=date(2026, 9, 30),
        manifest_sha256="eea52f69ccc97ece80c03e87780e110031d54db6ec4087b2a79480b7b45ed46f",
        manifest_path=str(manifest_path),
    )


def test_reproduce_f01_economic_state_not_reconciled_with_terminal_observation(tmp_path: Path) -> None:
    """F01 acceptance: tampered state economics are REJECTED against the terminal observation.

    Repaired runtime behavior:
        verify_chain() cross-reconciles state cash/holdings/equity/peak/
        receivable (strategy + benchmark) with the terminal observation
        fragment and raises DataContractError on any divergence.
    """
    state_dir = tmp_path / "prospective"
    obs_dir = state_dir / "observations"
    obs_dir.mkdir(parents=True)

    obs_iso = "2026-09-30"
    obs_doc: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": obs_iso,
        "processed_at_utc": "2026-09-30T20:20:00+00:00",
        "previous_observation_sha256": None,
        "authority": {
            "activation_binding": "docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json",
            "activation_binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
            "activation_binding_sha256": "eea52f69ccc97ece80c03e87780e110031d54db6ec4087b2a79480b7b45ed46f",
            "activation_binding_commit_sha": "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
            "activation_binding_commit_utc": "2026-09-29T17:12:46+00:00",
            "operational_activation_session": "2026-09-30",
            "ordinal": 1,
            "dispatch_attempt": 2,
        },
        "strategy": {
            "equity": "100000.00",
            "cash": "20000.00",
            "holdings": {"ACWI": 500, "AGG": 300},
            "daily_return": "0.00000000",
            "drawdown": "0.00000000",
        },
        "benchmark": {
            "equity": "100000.00",
            "cash": "0.00",
            "shares": "200",
            "daily_return": "0.00000000",
            "drawdown": "0.00000000",
        },
    }
    obs_raw = json.dumps(obs_doc, indent=2, sort_keys=True) + "\n"
    obs_path = obs_dir / f"{obs_iso}.json"
    obs_path.write_bytes(obs_raw.encode("utf-8"))
    obs_sha = hashlib.sha256(obs_raw.encode("utf-8")).hexdigest()

    # Create state.json with matching hash chain, BUT tampered economic balances ($999,999.00 vs $20,000.00 cash)
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
        "activation_authority_sha256": "eea52f69ccc97ece80c03e87780e110031d54db6ec4087b2a79480b7b45ed46f",
        "activation_commit_sha": "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
        "observed_sessions": [obs_iso],
        "observed_session_count": 1,
        "last_processed_session": obs_iso,
        "last_observation_sha256": obs_sha,
        # TAMPERED ECONOMIC VALUES (diverges from observation artifact):
        "strategy": {
            "cash": "999999.00",  # Diverges from obs_doc cash $20,000.00!
            "holdings": {"ACWI": 500, "AGG": 300},
            "receivables": [],
            "running_peak": "999999.00",
            "previous_equity": "999999.00",  # Diverges from obs_doc equity $100,000.00!
        },
        "benchmark": {
            "cash": "999999.00",  # Diverges from obs_doc cash $0.00!
            "SPY_shares": 200,
            "receivables": [],
            "running_peak": "999999.00",
            "previous_equity": "999999.00",  # Diverges from obs_doc equity $100,000.00!
            "entered": True,
        },
        "last_closes_raw": {"ACWI": "100.00", "AGG": "100.00"},
        "last_closes_split": {"ACWI": "100.00", "AGG": "100.00"},
        "completed_annual_rebalances": 0,
    }
    (state_dir / "state.json").write_text(json.dumps(state_doc, indent=2), encoding="utf-8")

    auth = _canonical_stage_c_auth(Path("docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json"))

    # Repaired runtime code rejects the tampered economics fail-closed.
    with pytest.raises(DataContractError, match="diverges from terminal observation"):
        verify_chain(state_dir, expected_recovery_authority=auth)


def test_reproduce_f02_orphan_detection_bypassed_when_state_json_absent(tmp_path: Path) -> None:
    """F02 acceptance: orphan observations without state.json are REJECTED.

    Repaired runtime behavior:
        verify_chain() inspects on-disk observations before generating initial
        state and raises DataContractError when orphans exist.
    """
    state_dir = tmp_path / "prospective"
    obs_dir = state_dir / "observations"
    obs_dir.mkdir(parents=True)

    # Place an orphan observation on disk without creating state.json
    orphan_file = obs_dir / "2026-09-30.json"
    orphan_file.write_text(json.dumps({"session": "2026-09-30", "test": "orphan"}), encoding="utf-8")

    # Repaired runtime code fails closed instead of returning pristine initial state.
    with pytest.raises(DataContractError, match="orphan observation files"):
        verify_chain(state_dir, expected_activation=date(2026, 9, 30))
    assert orphan_file.is_file()


def test_reproduce_f09_stage_c_b_loader_ignores_locks(tmp_path: Path) -> None:
    """F09 acceptance: corrupt Stage C-B locks are REJECTED by the loader.

    Repaired runtime behavior:
        load_stage_c_recovery_authority() requires the `locks` subdocument and
        exactly enforces paper_trading=false, live_trading=false,
        real_capital_authority_usd="0.00", no_real_orders=true.
    """
    cal = NyseCa1Calendar()
    manifest_path = tmp_path / "corrupted_locks_stage_c.json"

    # Manifest with corrupted locks
    corrupted_data = {
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
        # CORRUPTED LOCKS:
        "locks": {
            "paper_trading": True,
            "live_trading": True,
            "real_capital_authority_usd": "50000.00",
            "no_real_orders": False,
        },
    }
    manifest_path.write_text(json.dumps(corrupted_data, indent=2), encoding="utf-8")

    # Repaired runtime code rejects the corrupted locks fail-closed.
    with pytest.raises(DataContractError, match="SHADOW_RECOVERY_BINDING_LOCKS_INVALID"):
        SH.load_stage_c_recovery_authority(cal, manifest_path)


# =============================================================================
# F02 crash/fault variants: pristine vs orphan states
# =============================================================================


def test_f02_pristine_empty_state_dir_returns_initial(tmp_path: Path) -> None:
    """No state.json + no observations -> valid pristine initial state (no false block)."""
    state_dir = tmp_path / "prospective"
    state_dir.mkdir(parents=True)
    state = verify_chain(state_dir, expected_activation=date(2026, 9, 30))
    assert state["observed_sessions"] == []
    assert state["observed_session_count"] == 0
    assert state["activation_session"] == "2026-09-30"


def test_f02_multiple_orphans_block_without_state(tmp_path: Path) -> None:
    """No state.json + multiple observations -> BLOCK (every orphan counts)."""
    state_dir = tmp_path / "prospective"
    obs_dir = state_dir / "observations"
    obs_dir.mkdir(parents=True)
    for iso in ("2026-09-29", "2026-09-30"):
        (obs_dir / f"{iso}.json").write_text(
            json.dumps({"session": iso}), encoding="utf-8"
        )
    with pytest.raises(DataContractError, match="orphan observation files"):
        verify_chain(state_dir, expected_activation=date(2026, 9, 30))


# =============================================================================
# F09 lock-field variants + valid-manifest preservation
# =============================================================================


def _valid_locks_manifest(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "valid_locks_stage_c.json"
    valid_data = {
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
    manifest_path.write_text(json.dumps(valid_data, indent=2), encoding="utf-8")
    return manifest_path


def test_f09_each_corrupt_lock_field_blocks(tmp_path: Path) -> None:
    """Every individual corrupt lock value fails closed (no partial pass)."""
    cal = NyseCa1Calendar()
    base = json.loads(_valid_locks_manifest(tmp_path).read_text(encoding="utf-8"))
    corruptions: List[Dict[str, Any]] = [
        {"paper_trading": True},
        {"live_trading": True},
        {"real_capital_authority_usd": "0.01"},
        {"no_real_orders": False},
    ]
    for corrupt in corruptions:
        manifest_path = tmp_path / "corrupt_one_field.json"
        doc = json.loads(json.dumps(base))
        doc["locks"] = dict(doc["locks"], **corrupt)
        manifest_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        with pytest.raises(
            DataContractError, match="SHADOW_RECOVERY_BINDING_LOCKS_INVALID"
        ):
            SH.load_stage_c_recovery_authority(cal, manifest_path)


def test_f09_missing_locks_block_fails_closed(tmp_path: Path) -> None:
    """A manifest without any locks block fails closed (missing != valid)."""
    cal = NyseCa1Calendar()
    manifest_path = tmp_path / "missing_locks.json"
    doc = json.loads(_valid_locks_manifest(tmp_path).read_text(encoding="utf-8"))
    del doc["locks"]
    manifest_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    with pytest.raises(DataContractError, match="SHADOW_RECOVERY_BINDING"):
        SH.load_stage_c_recovery_authority(cal, manifest_path)


def test_f09_valid_manifest_loads_and_bytes_preserved(tmp_path: Path) -> None:
    """A fully valid manifest loads and its exact bytes are never mutated."""
    import shutil

    cal = NyseCa1Calendar()
    production = Path(
        "docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json"
    )
    assert production.is_file()
    before = production.read_bytes()
    auth = SH.load_stage_c_recovery_authority(cal, production)
    assert auth.binding_id == "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C"
    assert production.read_bytes() == before

    fixture = _valid_locks_manifest(tmp_path)
    before_fixture = fixture.read_bytes()
    auth_fixture = SH.load_stage_c_recovery_authority(cal, fixture)
    assert auth_fixture.activation_session == date(2026, 9, 30)
    assert fixture.read_bytes() == before_fixture
    # Honest lineage: this acceptance copy is a fixture, not the production file.
    shutil.copy(production, tmp_path / "production_copy.json")


# =============================================================================
# F01 per-leg divergence variants
# =============================================================================


def _reconciled_pair(tmp_path: Path) -> Path:
    """Build a synthetic fully-reconciled observation/state pair (Obs #1 shape).

    Mirrors the real artifact structure: INITIAL_ALLOCATION session fragment
    keys on the observation side, portfolio/benchmark subdocuments on the
    state side, with exactly matching economics and a valid authority block.
    """
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
    obs_doc: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": obs_iso,
        "processed_at_utc": "2026-09-30T20:20:00+00:00",
        "previous_observation_sha256": None,
        "authority": {
            "activation_binding": "docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json",
            "activation_binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
            "activation_binding_sha256": "eea52f69ccc97ece80c03e87780e110031d54db6ec4087b2a79480b7b45ed46f",
            "activation_binding_commit_sha": "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
            "activation_binding_commit_utc": "2026-09-29T17:12:46+00:00",
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
        "activation_authority_sha256": "eea52f69ccc97ece80c03e87780e110031d54db6ec4087b2a79480b7b45ed46f",
        "activation_commit_sha": "08530b1ab4ec64788d0eadfaf821aa01e07d0a5f",
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


def test_f01_reconciled_pair_passes_verify_chain(tmp_path: Path) -> None:
    """Obs #1 backward compatibility: a fully reconciled pair PASSES repaired verify_chain."""
    state_dir = _reconciled_pair(tmp_path)
    auth = _canonical_stage_c_auth(Path("docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json"))
    verified = verify_chain(state_dir, expected_recovery_authority=auth)
    assert verified["strategy"]["cash"] == "20000.00"
    assert verified["benchmark"]["SPY_shares"] == 200
    assert verified["observed_session_count"] == 1
    # The sealed chain link matches the recomputed observation bytes.
    recomputed = hashlib.sha256(
        (state_dir / "observations" / "2026-09-30.json").read_bytes()
    ).hexdigest()
    assert verified["last_observation_sha256"] == recomputed


def _tampered_pair(tmp_path: Path, leg: str, key: str, value: Any) -> Path:
    state_dir = _reconciled_pair(tmp_path)
    state_path = state_dir / "state.json"
    state_doc = json.loads(state_path.read_text(encoding="utf-8"))
    state_doc[leg][key] = value
    state_path.write_text(json.dumps(state_doc, indent=2), encoding="utf-8")
    return state_dir


def test_f01_each_divergent_leg_blocks(tmp_path: Path) -> None:
    """Every individual divergent economic field fails closed (no partial pass)."""
    auth = _canonical_stage_c_auth(Path("docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json"))
    divergences = [
        ("strategy", "cash", "20000.01"),
        ("strategy", "holdings", {"ACWI": 500, "AGG": 301}),
        ("strategy", "previous_equity", "100000.01"),
        ("strategy", "running_peak", "100000.01"),
        ("benchmark", "cash", "0.01"),
        ("benchmark", "SPY_shares", 201),
        ("benchmark", "previous_equity", "100000.01"),
        ("benchmark", "running_peak", "100000.01"),
    ]
    for leg, key, value in divergences:
        state_dir = _tampered_pair(tmp_path / leg.replace("_", "") / key.replace("_", ""), leg, key, value)
        with pytest.raises(DataContractError, match="diverges from terminal observation"):
            verify_chain(state_dir, expected_recovery_authority=auth)


def test_f01_nonfinite_and_malformed_observation_blocks(tmp_path: Path) -> None:
    """Non-finite or malformed terminal economics fail closed (never silently coerce)."""
    state_dir = _reconciled_pair(tmp_path)
    obs_path = state_dir / "observations" / "2026-09-30.json"
    obs_doc = json.loads(obs_path.read_text(encoding="utf-8"))
    # Non-finite cash on the observation side; re-seal the chain link so the
    # failure is proven to come from the F01 finite-value gate specifically.
    obs_doc["strategy"] = dict(obs_doc["strategy"], cash="nan")
    obs_raw = json.dumps(obs_doc, indent=2, sort_keys=True) + "\n"
    obs_path.write_bytes(obs_raw.encode("utf-8"))
    new_sha = hashlib.sha256(obs_raw.encode("utf-8")).hexdigest()
    state_path = state_dir / "state.json"
    state_doc = json.loads(state_path.read_text(encoding="utf-8"))
    state_doc["last_observation_sha256"] = new_sha
    state_path.write_text(json.dumps(state_doc, indent=2), encoding="utf-8")
    auth = _canonical_stage_c_auth(Path("docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json"))
    with pytest.raises(DataContractError, match="non-finite decimal"):
        verify_chain(state_dir, expected_recovery_authority=auth)
