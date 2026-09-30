"""Offline defect reproduction and acceptance test cases for audited findings F01, F02, and F09.

CRITICAL INVARIANT: DO NOT ALTER RUNTIME CODE IN src/** BEFORE OBSERVATION #1 ATTEMPT #2.
These tests demonstrate and document the exact gaps identified during repository audit:
- F01: verify_chain() validates that state economic subdocuments deserialize, but does not cross-reconcile
       state equity/cash/holdings with the terminal observation artifact.
- F02: verify_chain() returns build_initial_state() when state.json is absent, bypassing orphan detection.
- F09: load_stage_c_recovery_authority() does not validate the `locks` block in Stage C-B manifests.

INVARIANT: PASSING_REPRODUCTION_TEST != DEFECT_REPAIRED
These reproduction tests pass when they successfully reproduce the current unpatched behavior.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

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
    """F01 Reproduction: State economic values are deserialized but not cross-reconciled against observation.

    Current runtime behavior:
        verify_chain() calls `ShadowPortfolio.from_dict(state_doc["strategy"])` (lines 600-602),
        proving that the state dictionary has valid keys/types, but it does NOT verify that
        `state_doc["strategy"]["cash"]` or `previous_equity` equals the observation artifact values.

    Intended post-Attempt #2 repair:
        verify_chain() must assert that post-session portfolio and benchmark equity/holdings/cash in state.json
        strictly equal the final values reported in the terminal observation artifact.
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

    # In current runtime code, this passes because ShadowPortfolio.from_dict() and
    # ShadowBenchmark.from_dict() only check schema/deserialization, NOT reconciliation with obs_doc.
    verified = verify_chain(state_dir, expected_recovery_authority=auth)
    assert verified["strategy"]["cash"] == "999999.00"
    assert verified["strategy"]["previous_equity"] == "999999.00"
    # Proves the gap: state values diverge from observation values, yet chain verification succeeded.
    assert verified["strategy"]["cash"] != obs_doc["strategy"]["cash"]
    assert verified["strategy"]["previous_equity"] != obs_doc["strategy"]["equity"]


def test_reproduce_f02_orphan_detection_bypassed_when_state_json_absent(tmp_path: Path) -> None:
    """F02 Reproduction: Orphan observations are ignored if state.json does not exist.

    Current runtime behavior:
        verify_chain() checks `if not state_path.exists(): return build_initial_state(...)`
        at line 496 before orphan inspection at line 604. Therefore, an uncommitted or orphaned
        observation on disk silently returns initial state instead of failing closed.

    Intended post-Attempt #2 repair:
        verify_chain() must check for orphaned observation files *even if* state.json is absent,
        raising DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: orphan files without state.json").
    """
    state_dir = tmp_path / "prospective"
    obs_dir = state_dir / "observations"
    obs_dir.mkdir(parents=True)

    # Place an orphan observation on disk without creating state.json
    orphan_file = obs_dir / "2026-09-30.json"
    orphan_file.write_text(json.dumps({"session": "2026-09-30", "test": "orphan"}), encoding="utf-8")

    # In current runtime code, this does NOT raise DataContractError. It returns fresh initial state.
    state = verify_chain(state_dir, expected_activation=date(2026, 9, 30))
    assert state["observed_sessions"] == []
    assert state["observed_session_count"] == 0
    # Proves the gap: the orphan file exists on disk, but verify_chain did not fail closed.
    assert orphan_file.is_file()


def test_reproduce_f09_stage_c_b_loader_ignores_locks(tmp_path: Path) -> None:
    """F09 Reproduction: load_stage_c_recovery_authority() does not validate the locks sub-dictionary.

    Current runtime behavior:
        load_stage_c_recovery_authority() validates 11 top-level fields (binding_id, commit_sha,
        activation_session, etc.), but completely ignores `locks`. A corrupted manifest with
        `paper_trading=True`, `live_trading=True`, `capital=$100,000` is accepted without error.

    Intended post-Attempt #2 repair:
        load_stage_c_recovery_authority() must strictly validate `locks` requiring
        paper_trading=False, live_trading=False, real_capital_authority_usd=="0.00", no_real_orders=True,
        raising DataContractError("SHADOW_RECOVERY_BINDING_LOCKS_INVALID") if violated.
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

    # In current runtime code, this loads successfully despite corrupted locks!
    auth = SH.load_stage_c_recovery_authority(cal, manifest_path)
    assert auth.binding_id == "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C"
    # Proves the gap: the loader returned valid authority despite invalid locks.
