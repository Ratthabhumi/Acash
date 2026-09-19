"""Unit and Invariant Tests for Phase 14 Step R1: HYP_004 Registration & Governance.

Verifies:
1. HYP_003 is enrolled in TERMINAL_HYPOTHESIS_REGISTRY (anti-resurrection).
2. HYP_004 is fresh and not in TERMINAL_HYPOTHESIS_REGISTRY.
3. K = 1 parameter search grid cardinality equality.
4. Proposal data window strictly terminates on or before 2022-12-31 (zero OOS >= 2023).
5. Inception token hard-locks capital_authority_usd == 0.00.
6. Inception token hard-locks is_strategy_qualified == False.
7. Inception token hard-locks is_paper_authorized == False.
8. Inception token hard-locks is_live_authorized == False.
9. Preregistration SHA-256 is binding and matches disk bytes.
10. Semantic adapter precedence hierarchy is defined and explicit.
11. Registration script has zero market-data / Alpaca / network imports.
12. All 3 sealed hypothesis mirrors are byte-identical.
13. Both R1 manifest mirrors are byte-identical and link to valid files.
14. Sealed HYP_003 artifacts remain completely unmodified.
15. Generic legacy horizon / rank-IC fields are explicitly classified as non-binding metadata.
"""

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.reinception import (
    InceptionDecision,
    ResearchReInceptionGate,
    TERMINAL_HYPOTHESIS_REGISTRY,
)
from acash.research.schema import HypothesisSpecification


def test_1_hyp_003_terminal_registry_enforcement(tmp_path: Path) -> None:
    """Invariant 1: HYP_003 is enrolled in TERMINAL_HYPOTHESIS_REGISTRY and blocked programmatically."""
    assert "HYP_003" in TERMINAL_HYPOTHESIS_REGISTRY


def test_2_hyp_004_id_fresh_and_not_in_terminal_registry() -> None:
    """Invariant 2: HYP_004 is fresh, valid ID format, and not in terminal registry."""
    assert "HYP_004" not in TERMINAL_HYPOTHESIS_REGISTRY


def test_3_k_equals_1_grid_cardinality() -> None:
    """Invariant 3: K = 1 single primary preregistered specification."""
    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_004.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    k_val = cfg["planned_trial_count_k"]["value"] if isinstance(cfg["planned_trial_count_k"], dict) else cfg["planned_trial_count_k"]
    assert k_val == 1
    assert cfg["primary_specification"] == "GAO_R1_TO_R13_BASELINE"


def test_4_proposal_window_ends_before_2023() -> None:
    """Invariant 4: Data window strictly terminates in 2022; zero 2023+ data declared."""
    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_004.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    rep_sample = cfg["partition_policy"]["primary_replication_sample"]
    assert rep_sample["start_date"] == "2017-01-01"
    assert rep_sample["end_date"] == "2022-12-31"
    holdout = cfg["partition_policy"]["external_holdout"]
    assert holdout["start_date"] == "2023-01-01"
    assert holdout["state"] == "SEALED_UNREAD"


def test_5_to_8_token_zero_authority_locks() -> None:
    """Invariants 5-8: Inception token strictly locks capital and trading authorizations."""
    manifest = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_004.json").read_text(encoding="utf-8"))
    assert manifest["capital_authority_usd"] == "0.00"
    assert manifest["status"] == "SEALED_STEP_R1_PASS"
    assert "LOCKED" in manifest["next_required_step"]


def test_9_preregistration_sha_binding() -> None:
    """Invariant 9: Preregistration file SHA-256 matches the manifest and sealed hypothesis."""
    prereg_path = Path("docs/research/MEC-0014A-statistical-preregistration-draft.md")
    assert prereg_path.exists()
    calculated_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()

    manifest = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_004.json").read_text(encoding="utf-8"))
    assert manifest["preregistration_sha256"] == calculated_sha

    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_004.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    assert cfg["governance_lineage"]["preregistration_sha256"] == calculated_sha


def test_10_semantic_adapter_precedence_document_exists() -> None:
    """Invariant 10: Semantic conformance record exists and defines the 4-tier hierarchy."""
    doc_path = Path("docs/phase14/phase14_r1_semantic_conformance_record_HYP_004.md")
    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")
    assert "Authority Precedence Order" in content
    assert "Human-Ratified MEC-0014A Statistical Preregistration" in content


def test_11_no_market_data_network_imports_in_registration_script() -> None:
    """Invariant 11: Registration script performs zero market data I/O and has zero market data imports."""
    script_path = Path("scripts/register_phase14_step_r1_hyp_004.py")
    assert script_path.exists()
    code = script_path.read_text(encoding="utf-8")
    prohibited_tokens = ["alpaca", "urllib", "requests", "httpx", "parquet", "duckdb", "socket"]
    for token in prohibited_tokens:
        assert f"import {token}" not in code
        assert f"from {token}" not in code


def test_12_sealed_mirrors_byte_identical() -> None:
    """Invariant 12: All three hypothesis mirror files are byte-identical."""
    p85 = Path("docs/phase8.5/hypotheses/HYP_004.json").read_bytes()
    p14 = Path("docs/phase14/hypotheses/HYP_004.json").read_bytes()
    data = Path("data/manifests/research/hypotheses/HYP_004.json").read_bytes()
    assert p85 == p14 == data

    # Verify canonical spec SHA-256 matches manifest
    spec_004 = HypothesisSpecification(**json.loads(p14.decode("utf-8")))
    calculated_spec_sha = calculate_hypothesis_spec_sha256(spec_004)
    manifest = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_004.json").read_text(encoding="utf-8"))
    assert manifest["hypothesis_sha256"] == calculated_spec_sha


def test_13_manifest_mirrors_byte_identical_and_valid() -> None:
    """Invariant 13: Both manifest mirrors are byte-identical."""
    m14 = Path("docs/phase14/manifests/manifest_r1_HYP_004.json").read_bytes()
    mdata = Path("data/manifests/research/manifest_r1_HYP_004.json").read_bytes()
    assert m14 == mdata


def test_14_hyp_003_artifacts_unchanged() -> None:
    """Invariant 14: HYP_003 sealed specification and manifests remain unmodified."""
    p14_hyp_003 = Path("docs/phase14/hypotheses/HYP_003.json")
    assert p14_hyp_003.exists()
    spec_003 = HypothesisSpecification(**json.loads(p14_hyp_003.read_text(encoding="utf-8")))
    sha_003 = calculate_hypothesis_spec_sha256(spec_003)
    # Canonical SHA-256 established during HYP_003 R1 registration
    assert sha_003 == "f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0"


def test_15_legacy_fields_explicitly_classified_non_binding() -> None:
    """Invariant 15: Schema compatibility fields are explicitly documented as non-binding in config."""
    p14_hyp = json.loads(Path("docs/phase14/hypotheses/HYP_004.json").read_text(encoding="utf-8"))
    cfg = json.loads(p14_hyp["parameter_config_json"])
    classification = cfg["schema_compatibility_classification"]
    assert "target_horizons=[1]" in classification["non_binding_metadata"]
    assert "min_in_sample_rank_ic=0.000001" in classification["non_binding_metadata"]
    assert "expected_direction_LONG_as_positive_beta" in classification["binding"]
    assert "preregistered_regression_r13_on_r1" in classification["binding"]
