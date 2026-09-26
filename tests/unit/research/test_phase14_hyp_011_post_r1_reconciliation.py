"""Governance tests for HYP_011 post-R1 metadata + prospective reconciliation.

Additive reconciliation only. No market-data access. Proves the live record
transition, R1 historical immutability, and prospective timestamp authority.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
HYP_PATH = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_011.json"
R1_MANIFEST = REPO_ROOT / "docs" / "phase14" / "manifests" / "manifest_r1_HYP_011.json"
REG_RECORD = (
    REPO_ROOT / "docs" / "phase14" / "phase14_r1_hypothesis_registration_record_HYP_011.md"
)
PREREG = REPO_ROOT / "docs" / "research" / "CORE-001-HYP-011-strategy-preregistration.md"
RECON_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_011_POST_R1_METADATA_AND_PROSPECTIVE_RECONCILIATION.json"
)
RECON_DOC = (
    REPO_ROOT / "docs" / "phase14" / "HYP_011_POST_R1_METADATA_AND_PROSPECTIVE_RECONCILIATION.md"
)
PARK_MANIFEST = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_010_PARKED_NON_FALSIFIED_BLOCKER.json"
)


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_state_still_r1_sealed_and_gate_points_to_r1() -> None:
    h = _load(HYP_PATH)
    assert h["state"] == "R1_PREREGISTERED_SEALED"
    assert h["invalidation_criteria"]["status"] == "R1_NUMERICAL_GATES_SEALED"
    assert h["invalidation_criteria"]["authority"] == (
        "docs/phase14/manifests/manifest_r1_HYP_011.json"
    )
    assert h["invalidation_criteria"]["gate_contract_hash"] == (
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b"
    )
    assert h["target_holdings"] == {"ACWI": 0.8, "AGG": 0.2}


def test_numerical_gates_flag_single_flag_change() -> None:
    h = _load(HYP_PATH)
    params = json.loads(h["parameter_config_json"])
    assert params["numerical_gates_authorized"] is True
    assert params["target_weights"] == {"ACWI": 0.8, "AGG": 0.2}
    assert params["rebalance_frequency"] == "ANNUAL"
    assert params["max_gross_leverage"] == 1.0


def test_contract_hashes_unchanged() -> None:
    m = _load(R1_MANIFEST)
    assert m["contract_hashes"]["strategy_specification_hash"] == (
        "3b2159c02d4013711523538f9ea5ea8668aa0761cc05b12c2d163a9721c35c68"
    )
    assert m["contract_hashes"]["provider_contract_hash"] == (
        "fc2f1e7525d9cb69e74ac4d1464acab4b4855ee2e0e4ed72208f2591af749edc"
    )
    assert m["contract_hashes"]["sample_partition_hash"] == (
        "0bf1c4fe4762037f542caf7562a10ab97a0fb23d1f0fc20b967f0830762f3a13"
    )
    assert m["contract_hashes"]["gate_contract_hash"] == (
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b"
    )


def test_historical_r1_artifacts_unchanged() -> None:
    m = _load(R1_MANIFEST)
    assert m["manifest_sha256"] == "fc81757fc333f9a62c3bf25264cf51091f4895825353313e1d8c086570b0fbab"
    assert m["hypothesis_sha256"] == "7cfc74f16ef85ac222f6605c3eae0b1cf499848bb71c797efbd7fef79a570e78"
    assert m["preregistration_sha256"] == "04dab8edb5b3c442094c284485eeddfc83c0b3c91e9c6db59e0f7694144fbe2e"
    assert "HYP_011 = PREREGISTERED_SEALED_R1" in REG_RECORD.read_text(encoding="utf-8")
    assert "PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_R1_SEAL" in PREREG.read_text(
        encoding="utf-8"
    )


def test_prospective_timestamp_authority() -> None:
    r = _load(RECON_MANIFEST)
    assert r["actual_r1_commit_sha"] == "dfdd085c5a6c41f9ff19eac5ea68512f884ed0eb"
    assert r["actual_r1_commit_timestamp_utc"] == "2026-09-24T22:34:44Z"
    assert r["historical_registration_metadata_timestamp"] == "2026-09-24T21:00:00Z"
    assert r["prospective_boundary_timestamp_authority"] == "ACTUAL_R1_GIT_COMMIT_TIMESTAMP"
    assert r["prospective_session_resolved"] is False
    assert _load(HYP_PATH)["registered_at_utc"] == "2026-09-24T21:00:00Z"
    assert hashlib.sha256(HYP_PATH.read_bytes()).hexdigest() == r["new_live_hypothesis_sha256"]


def test_zero_access_locks_park_untouched() -> None:
    r = _load(RECON_MANIFEST)
    assert r["market_data_requests"] == 0
    assert r["historical_access"] == 0
    assert r["recent_stress_access"] == 0
    assert r["quarantine_access"] == 0
    assert r["prospective_empirical_access"] == 0
    assert r["paper_authorized"] is False
    assert r["live_authorized"] is False
    assert r["capital_authority_usd"] == "0.00"
    assert r["no_real_orders"] is True
    park = _load(PARK_MANIFEST)
    assert park["new_lifecycle_state"] == "HYP_010_BLOCKED_NON_FALSIFIED_BY_DIVIDEND_AUTHORITY"
    assert RECON_DOC.is_file()
