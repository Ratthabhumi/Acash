"""Governance tests for HYP_010 post-R1 metadata + prospective reconciliation.

Additive reconciliation only. No market-data access. Proves the live record
transition, R1 historical immutability, and prospective timestamp authority.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
HYP_PATH = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_010.json"
R1_MANIFEST = REPO_ROOT / "docs" / "phase14" / "manifests" / "manifest_r1_HYP_010.json"
REG_RECORD = (
    REPO_ROOT / "docs" / "phase14" / "phase14_r1_hypothesis_registration_record_HYP_010.md"
)
PREREG = REPO_ROOT / "docs" / "research" / "CORE-001-HYP-010-strategy-preregistration.md"
RECON_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_010_POST_R1_METADATA_AND_PROSPECTIVE_RECONCILIATION.json"
)
RECON_DOC = (
    REPO_ROOT / "docs" / "phase14" / "HYP_010_POST_R1_METADATA_AND_PROSPECTIVE_RECONCILIATION.md"
)


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_state_still_r1_sealed_and_gate_points_to_r1() -> None:
    h = _load(HYP_PATH)
    assert h["state"] == "R1_PREREGISTERED_SEALED"
    assert h["invalidation_criteria"]["status"] == "R1_NUMERICAL_GATES_SEALED"
    assert h["invalidation_criteria"]["authority"] == (
        "docs/phase14/manifests/manifest_r1_HYP_010.json"
    )
    assert h["invalidation_criteria"]["gate_contract_hash"] == (
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b"
    )
    assert h["r1_gate_contract_hash"] == (
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b"
    )


def test_numerical_gates_flag_post_r1_metadata_only() -> None:
    h = _load(HYP_PATH)
    params = json.loads(h["parameter_config_json"])
    assert params["numerical_gates_authorized"] is True
    # Strategy keys intact around the single-flag change.
    assert params["momentum_formula"] == "M12_ASSET_T_EQ_TR_T_DIV_TR_T-12_MINUS_1"
    assert params["lookback_months"] == 12
    assert params["target_holdings"] == ["SPY", "VEU", "AGG"]


def test_contract_hashes_unchanged() -> None:
    m = _load(R1_MANIFEST)
    assert m["contract_hashes"]["strategy_specification_hash"] == (
        "63ff2373c08dde547495f96bc62564ac2851933da33ca7fb074fd5575ae984e3"
    )
    assert m["contract_hashes"]["provider_contract_hash"] == (
        "a91ce9ec239dfc239f8e772d5ea89d4ff474507a1c51b319849dca35b313e3a9"
    )
    assert m["contract_hashes"]["sample_partition_hash"] == (
        "a9cf14955fffcf16719f8cdd36a7bf1ab81f6ff4bdbdf1c083e13c1663c66d13"
    )
    assert m["contract_hashes"]["gate_contract_hash"] == (
        "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b"
    )


def test_historical_r1_artifacts_unchanged() -> None:
    m = _load(R1_MANIFEST)
    assert m["manifest_sha256"] == "fba365716f7494275537f6118ccaa70efc25629f1f1f47bfd1b4046ebee17ff0"
    assert m["hypothesis_sha256"] == "a32698926a8968820b81239d910a4e5db42f6b101cd09fb73c859b0675464d0b"
    assert m["preregistration_sha256"] == "e4d873d78131974a8f7e29c5146e526615d78257abb3f51ae338b86403fda456"
    text = REG_RECORD.read_text(encoding="utf-8")
    assert "HYP_010 = PREREGISTERED_SEALED_R1" in text
    assert "PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_R1_SEAL" in PREREG.read_text(
        encoding="utf-8"
    )


def test_prospective_timestamp_authority() -> None:
    r = _load(RECON_MANIFEST)
    assert r["actual_r1_commit_sha"] == "3282e78e38989e94eb68a04b8c6ff2965fa7ff7f"
    assert r["actual_r1_commit_timestamp_utc"] == "2026-09-24T20:00:10Z"
    assert r["historical_registration_metadata_timestamp"] == "2026-09-24T00:00:00Z"
    assert r["prospective_boundary_timestamp_authority"] == "ACTUAL_R1_GIT_COMMIT_TIMESTAMP"
    assert r["prospective_session_resolved"] is False
    assert _load(HYP_PATH)["registered_at_utc"] == "2026-09-24T00:00:00Z"


def test_midnight_value_not_prospective_authority() -> None:
    doc_text = RECON_DOC.read_text(encoding="utf-8")
    assert "MUST NOT be used" in doc_text or "MUST NOT" in doc_text
    assert "2026-09-24T20:00:10Z" in doc_text


def test_zero_access_and_locks_and_hyp009_untouched() -> None:
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
    term = _load(REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_TERMINAL_M2_DECISION.json")
    assert term["hyp_009_state"] == "HYP_009_TERMINAL_NOT_SUPPORTED_AT_LOCKED_M2"
