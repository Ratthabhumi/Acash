"""Governance tests for HYP_009 post-R1 canonical metadata reconciliation.

Proves the authorized lifecycle-only transition of two stale PRE-R1 metadata
structures with zero scientific change. No network calls, no market-data reads,
no calculations beyond hash recomputation over committed artifacts.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

from acash.core.serialization import CanonicalConfigSerializer

REPO_ROOT = Path(__file__).resolve().parents[3]
HYP_PATH = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_009.json"
R1_MANIFEST_PATH = REPO_ROOT / "docs" / "phase14" / "manifests" / "manifest_r1_HYP_009.json"
R1_RECORD_PATH = (
    REPO_ROOT / "docs" / "phase14" / "phase14_r1_hypothesis_registration_record_HYP_009.md"
)
RECON_MANIFEST_PATH = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_POST_R1_METADATA_RECONCILIATION.json"
)
RECON_DOC_PATH = REPO_ROOT / "docs" / "phase14" / "HYP_009_POST_R1_METADATA_RECONCILIATION.md"

PRIOR_HYP_009_SHA = "f927ccd7b2a3adec18d8097fb09eea90a7bbeebe9872c9f563811bdb6b4842fa"
NEW_HYP_009_SHA = "fb855542e86aa91139a0c7cdbedaad60de113ccbf679fe3e12a7465bcae13f2d"
GATE_CONTRACT_HASH = "052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b"
R1_MANIFEST_SHA = "ded1528d78f92003ab538a1ade7b9e047ed7306feaac4faa3270c67df27fce7c"

FIVE_ITEMS = [
    "OPEN_BEFORE_R1_TOTAL_RETURN_SIGNAL_CONSTRUCTION",
    "OPEN_BEFORE_R1_EXECUTION_COST_MODEL",
    "OPEN_BEFORE_R1_SAMPLE_PARTITION_DATES",
    "OPEN_BEFORE_R1_LOCKED_OOS_BOUNDARY",
    "OPEN_BEFORE_R1_PROSPECTIVE_BOUNDARY",
]


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_state_remains_r1_preregistered_sealed() -> None:
    h = _load(HYP_PATH)
    assert h["state"] == "R1_PREREGISTERED_SEALED"
    assert h["registered_at_utc"] == "2026-09-23T22:41:00Z"


def test_invalidation_no_longer_claims_not_preregistered() -> None:
    h = _load(HYP_PATH)
    inv = h["invalidation_criteria"]
    assert inv["status"] != "NOT_PREREGISTERED_NO_NUMERICAL_GATES_AUTHORIZED"
    assert inv["status"] == "R1_NUMERICAL_GATES_SEALED"


def test_invalidation_points_to_sealed_r1_gate_authority() -> None:
    h = _load(HYP_PATH)
    inv = h["invalidation_criteria"]
    assert inv["authority"] == "docs/phase14/manifests/manifest_r1_HYP_009.json"
    assert inv["gate_contract_hash"] == GATE_CONTRACT_HASH
    assert inv["logical_conjunction"] == "G1 AND G2 AND G3 AND G4 AND G5 AND G6"


def test_gate_contract_hash_exact() -> None:
    h = _load(HYP_PATH)
    m = _load(R1_MANIFEST_PATH)
    assert h["invalidation_criteria"]["gate_contract_hash"] == GATE_CONTRACT_HASH
    assert m["contract_hashes"]["gate_contract_hash"] == GATE_CONTRACT_HASH
    assert hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(m["acceptance_gates"]).encode("utf-8")
    ).hexdigest() == GATE_CONTRACT_HASH


def test_open_before_r1_empty_and_resolved_lineage_complete() -> None:
    h = _load(HYP_PATH)
    assert h["open_before_r1"] == []
    assert h["resolved_before_r1"] == FIVE_ITEMS
    assert h["r1_resolution_authority"] == "docs/phase14/manifests/manifest_r1_HYP_009.json"


def test_contract_hashes_unchanged() -> None:
    m = _load(R1_MANIFEST_PATH)
    pins = m["contract_hashes"]
    for block_key, pin_key in (
        ("strategy_contract", "strategy_specification_hash"),
        ("provider_contract", "provider_contract_hash"),
        ("sample_partitions", "sample_partition_hash"),
        ("acceptance_gates", "gate_contract_hash"),
    ):
        assert pins[pin_key] == hashlib.sha256(
            CanonicalConfigSerializer.to_canonical_json(m[block_key]).encode("utf-8")
        ).hexdigest(), f"stale pin: {pin_key}"


def test_scientific_parameter_config_unchanged() -> None:
    h = _load(HYP_PATH)
    params = json.loads(h["parameter_config_json"])
    assert params["signal_name"] == "10_MONTH_SIMPLE_MOVING_AVERAGE"
    assert params["lookback_month_ends"] == 10
    assert params["equality_behavior"] == "CASH"
    assert params["direction_states"] == ["LONG", "CASH"]
    assert params["max_gross_leverage"] == 1.0
    assert params["volatility_targeting"] is False
    assert params["cash_return"] == 0.0
    assert params["execution_timing"] == "NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL"
    assert h["target_horizons"] == [21]
    assert h["primary_horizon"] == 21
    assert h["expected_direction"] == "LONG"


def test_r1_manifest_byte_unchanged() -> None:
    # Repo convention (HYP_005/007): manifest SHA = hash over canonical payload,
    # not raw file bytes. Recompute and compare to the sealed record value.
    m = _load(R1_MANIFEST_PATH)
    payload = {k: v for k, v in m.items() if k != "manifest_sha256"}
    assert m["manifest_sha256"] == R1_MANIFEST_SHA
    assert hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
    ).hexdigest() == R1_MANIFEST_SHA


def test_r1_registration_record_unchanged() -> None:
    assert R1_RECORD_PATH.is_file()
    text = R1_RECORD_PATH.read_text(encoding="utf-8")
    assert "HYP_009 = PREREGISTERED_SEALED_R1" in text
    assert "AUTH_INCEPTION_HYP_009_e2ee71d26cf5891c" in text


def test_reconciliation_manifest_records_transition() -> None:
    r = _load(RECON_MANIFEST_PATH)
    assert r["prior_hyp_009_sha256"] == PRIOR_HYP_009_SHA
    assert r["new_hyp_009_sha256"] == NEW_HYP_009_SHA
    assert hashlib.sha256(HYP_PATH.read_bytes()).hexdigest() == NEW_HYP_009_SHA
    assert r["scientific_contract_changed"] is False
    assert r["r1_verdict_unchanged"] is True
    assert r["r1_manifest_mutated"] is False
    assert r["r1_registration_record_mutated"] is False
    assert r["open_before_r1_after_count"] == 0
    assert r["resolved_before_r1_count"] == 5


def test_no_data_no_backtest_locks_intact() -> None:
    r = _load(RECON_MANIFEST_PATH)
    m = _load(R1_MANIFEST_PATH)
    assert r["market_data_access"] == "ZERO"
    assert r["backtest_executed"] is False
    assert m["m2_data_access"] == "ZERO"
    assert m["m3_data_access"] == "ZERO"
    assert m["sample_partitions"]["prospective"]["state_at_r1"] == "LOCKED_ZERO_ACCESS"
    assert r["paper_authorized"] is False
    assert r["live_authorized"] is False
    assert r["capital_authority_usd"] == "0.00"
    assert r["no_real_orders"] is True


def test_reconciliation_doc_states_transition() -> None:
    assert RECON_DOC_PATH.is_file()
    text = RECON_DOC_PATH.read_text(encoding="utf-8")
    assert "R1_NUMERICAL_GATES_SEALED" in text
    assert PRIOR_HYP_009_SHA in text
    assert NEW_HYP_009_SHA in text
    assert "AUTHORIZE_CORE_001_HYP_009_POST_R1_METADATA_RECONCILIATION" in text
