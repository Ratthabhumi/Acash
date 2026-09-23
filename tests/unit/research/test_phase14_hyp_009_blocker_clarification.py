"""Governance tests for HYP_009 blocker semantic clarification (additive).

Proves the narrowed interpretation without history rewrite. No network calls,
no secret inspection.
"""

import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAR_DOC = REPO_ROOT / "docs" / "phase14" / "HYP_009_DATA_ENTITLEMENT_BLOCK_001_CLARIFICATION.md"
CLAR_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_009_DATA_ENTITLEMENT_BLOCK_001_CLARIFICATION.json"
)
ORIG_BLOCK_DOC = REPO_ROOT / "docs" / "phase14" / "HYP_009_DATA_ENTITLEMENT_BLOCK_001.md"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_clarification_narrows_blocker_interpretation() -> None:
    m = _load(CLAR_MANIFEST)
    assert m["original_block_label"] == "BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT"
    assert m["audited_evidence_actually_established"] == (
        "MISSING_PRIMARY_PROVIDER_CREDENTIALS_PREVENTED_AUTHENTICATION"
    )
    assert m["entitlement_check_performed"] is False
    assert m["network_requests_issued"] == 0
    assert m["correct_operational_interpretation"] == (
        "BLOCKED_PRE_ENTITLEMENT_CHECK_MISSING_CREDENTIALS"
    )


def test_future_resume_state_machine_bound() -> None:
    m = _load(CLAR_MANIFEST)
    sm = m["future_resume_state_machine"]
    assert sm["step_a_credentials_absent"] == "BLOCKED_PRE_ENTITLEMENT_CHECK_MISSING_CREDENTIALS"
    assert sm["step_b_authentication_fails"] == "BLOCKED_PROVIDER_AUTHENTICATION"
    assert sm["step_b_sip_or_historical_unavailable"] == "BLOCKED_DATA_ENTITLEMENT"
    assert sm["step_b_m1_coverage_unavailable"] == "BLOCKED_DATA_COVERAGE"
    assert sm["step_b_all_qualification_passes"] == "PROCEED_TO_M1_ONLY_DATASET_ACQUISITION"


def test_non_falsifying_verdicts_preserved() -> None:
    m = _load(CLAR_MANIFEST)
    assert m["hypothesis_falsified"] is False
    assert m["hypothesis_rejected"] is False
    assert m["r2_dataset_build"] == "NOT_STARTED"
    assert m["resumable"] is True
    assert m["original_artifact_rewritten"] is False
    assert ORIG_BLOCK_DOC.is_file(), "original blocker artifact must be preserved"


def test_clarification_doc_states() -> None:
    assert CLAR_DOC.is_file()
    text = CLAR_DOC.read_text(encoding="utf-8")
    assert "BLOCKED_PRE_ENTITLEMENT_CHECK_MISSING_CREDENTIALS" in text
    assert "ENTITLEMENT_CHECK_PERFORMED" in text
    assert "AUTHORIZE_HYP_009_PRE_R2_BLOCKER_RESUMABILITY_PATCH" in text
