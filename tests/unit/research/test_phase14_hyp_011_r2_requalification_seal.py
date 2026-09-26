"""Seal tests for HYP_011 clean provider requalification + composition.

Asserts the requalification manifest, adjudication record, and overall
composition. No network.
"""

import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_adjudication_record() -> None:
    m = _load(REPO_ROOT / "docs/phase14/manifests/HYP_011_R2_PROVIDER_DEFECT_ADJUDICATION.json")
    assert m["procedural_adjudication"] == "R2_PROVIDER_QUALIFICATION_INVALIDATED_BY_IMPLEMENTATION_DEFECT"
    assert m["first_live_result_rows_per_series"] == 3
    assert m["defect_discovered_after_live_result_observation"] is True
    assert m["scientific_hypothesis_falsified"] is False
    assert m["sponsor_authority_status"] == "PRESERVED_VALID_SUBCOMPONENT"


def test_requalification_manifest() -> None:
    m = _load(REPO_ROOT / "docs/phase14/manifests/HYP_011_R2_PROVIDER_REQUALIFICATION.json")
    assert m["classification"] == "PROVIDER_REQUALIFICATION_PASS"
    assert m["http_attempts"] == 6
    for symbol in ("ACWI", "AGG", "SPY"):
        assert m["results"][symbol]["split_rows"] == 4
        assert m["results"][symbol]["raw_rows"] == 4
        assert m["results"][symbol]["alignment"] == "PASS"
    assert m["spill_count"] == 0
    assert m["new_defect_after_result"] is False


def test_overall_composition() -> None:
    m = _load(REPO_ROOT / "docs/phase14/manifests/HYP_011_R2_REQUALIFIED_SUMMARY.json")
    assert m["provider_state"] == "PROVIDER_REQUALIFICATION_PASS"
    assert m["sponsor_state"] == "SPONSOR_AUTHORITY_REUSED_AND_VERIFIED"
    assert m["overall_classification"] == (
        "R2_PROVIDER_AND_SPONSOR_AUTHORITIES_QUALIFIED_HISTORICAL_BUILD_NOT_EXECUTED"
    )
    assert m["full_historical_acquisition_executed"] is False
    assert m["performance_computed"] is False
    assert m["m2_access_count"] == 0
    assert m["m3_access_count"] == 0
