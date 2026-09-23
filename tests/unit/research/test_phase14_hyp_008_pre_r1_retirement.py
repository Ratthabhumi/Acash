"""Governance tests for HYP_008 pre-R1 additive retirement.

Implementation-only invariants. No market-data network calls, no signal
computation, no performance evaluation. Asserts exclusively on committed
governance artifacts.
"""

import json
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[3]
RETIREMENT_MANIFEST = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_008_PRE_R1_RETIREMENT.json"
)
RETIREMENT_DOC = REPO_ROOT / "docs" / "phase14" / "HYP_008_PRE_R1_RETIREMENT.md"
HISTORICAL_PROPOSAL = REPO_ROOT / "docs" / "research" / "MEC-0018-HYP-008-proposal.md"
HISTORICAL_REVIEW = (
    REPO_ROOT / "docs" / "phase14" / "HYP_008_RESEARCH_INCEPTION_REVIEW.md"
)


def _load_manifest() -> Dict[str, Any]:
    assert RETIREMENT_MANIFEST.is_file(), "retirement manifest missing"
    return json.loads(RETIREMENT_MANIFEST.read_text(encoding="utf-8"))


def test_retirement_manifest_prior_state_is_proposed_not_preregistered() -> None:
    m = _load_manifest()
    assert m["hypothesis_id"] == "HYP_008"
    assert m["mechanism_id"] == "MEC-0018"
    assert m["prior_state"] == "PROPOSED_NOT_PREREGISTERED"


def test_retirement_manifest_new_state_is_retired_before_preregistration() -> None:
    m = _load_manifest()
    assert m["new_state"] == "RETIRED_BEFORE_PREREGISTRATION"
    assert (
        m["retirement_reason"]
        == "HUMAN_RESEARCH_PRIORITY_CHANGED_TO_CORE_FIRST_ARCHITECTURE"
    )


def test_retirement_manifest_not_an_empirical_rejection() -> None:
    m = _load_manifest()
    assert m["is_falsification"] is False
    assert m["is_empirical_rejection"] is False
    assert m["is_backtest_failure"] is False


def test_retirement_manifest_r1_never_opened() -> None:
    m = _load_manifest()
    assert m["r1_opened"] is False
    assert m["backtest_executed"] is False
    assert m["historical_signal_evaluation"] is False


def test_retirement_manifest_no_market_or_capital_authority() -> None:
    m = _load_manifest()
    assert m["m3_accessed"] is False
    assert m["paper_authorized"] is False
    assert m["live_authorized"] is False
    assert m["capital_authority_usd"] == "0.00"
    assert m["no_real_orders"] is True


def test_retirement_manifest_marks_historical_proposal_unmutated() -> None:
    m = _load_manifest()
    assert m["historical_proposal_mutated"] is False
    assert "docs/research/MEC-0018-HYP-008-proposal.md" in m["preserved_artifacts"]
    assert (
        "docs/phase14/HYP_008_RESEARCH_INCEPTION_REVIEW.md"
        in m["preserved_artifacts"]
    )


def test_historical_hyp_008_artifacts_still_exist() -> None:
    assert HISTORICAL_PROPOSAL.is_file(), "historical HYP_008 proposal must be preserved"
    assert HISTORICAL_REVIEW.is_file(), "historical HYP_008 review must be preserved"


def test_retirement_doc_records_transition() -> None:
    assert RETIREMENT_DOC.is_file(), "retirement doc missing"
    text = RETIREMENT_DOC.read_text(encoding="utf-8")
    assert "RETIRED_BEFORE_PREREGISTRATION" in text
    assert "HUMAN_RESEARCH_PRIORITY_CHANGED_TO_CORE_FIRST_ARCHITECTURE" in text
    assert "AUTHORIZE_RETIRE_HYP_008_AND_OPEN_CORE_001_HYP_009_IMPLEMENTATION" in text
