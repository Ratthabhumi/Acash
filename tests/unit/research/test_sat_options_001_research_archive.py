"""Governance tests for SAT-OPTIONS-001 research archive (documentation-only).

No network calls, no market-data reads, no calculations. Asserts exclusively
on committed archive artifacts.
"""

import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCHIVE_DOC = (
    REPO_ROOT
    / "docs"
    / "research"
    / "SAT-OPTIONS-001-dealer-gamma-intraday-regime-research.md"
)
ARCHIVE_MANIFEST = (
    REPO_ROOT / "docs" / "research" / "manifests" / "SAT-OPTIONS-001-research-archive.json"
)


def _load_manifest() -> Dict[str, Any]:
    assert ARCHIVE_MANIFEST.is_file(), "archive manifest missing"
    return cast(Dict[str, Any], json.loads(ARCHIVE_MANIFEST.read_text(encoding="utf-8")))


def test_archive_state_is_research_only() -> None:
    m = _load_manifest()
    assert m["research_branch_id"] == "SAT-OPTIONS-001"
    assert m["state"] == "RESEARCH_ARCHIVE_ONLY"


def test_no_hypothesis_mechanism_or_preregistration() -> None:
    m = _load_manifest()
    assert m["hypothesis_id"] is None
    assert m["mechanism_id"] is None
    assert m["preregistration"] is None
    assert m["backtest_authorization"] is None
    assert m["data_access_authorization"] is None


def test_no_authority_and_core_untouched() -> None:
    m = _load_manifest()
    assert m["core_001_modified"] is False
    assert m["hyp_009_modified"] is False
    assert m["paper_authorized"] is False
    assert m["live_authorized"] is False
    assert m["capital_authority_usd"] == "0.00"
    assert m["no_real_orders"] is True


def test_archive_doc_encodes_conclusions() -> None:
    assert ARCHIVE_DOC.is_file(), "archive doc missing"
    text = ARCHIVE_DOC.read_text(encoding="utf-8")
    assert "RESEARCH_ARCHIVE_ONLY" in text
    assert "OFFICIAL_OPTION_OPEN_INTEREST_IS_NOT_INTRADAY_LIVE_POSITION_DATA" in text
    assert "OPEN_INTEREST_ALONE_DOES_NOT_IDENTIFY_DEALER_POSITION_SIGN" in text
    assert "SOURCE_METADATA_TO_VERIFY_BEFORE_FORMAL_PREREGISTRATION" in text
    assert "AUTHORIZE_SAT_OPTIONS_001_RESEARCH_ARCHIVE_DOCUMENTATION" in text
