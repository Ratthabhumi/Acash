"""Tests for HYP_010 VEU authority resolution pass (block retained).

Asserts the resolution record: amounts corroborated, U.S. dates absent, no
inference/substitution, block retained. Tracked artifacts only. No network.
"""

import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
RES_DOC = REPO_ROOT / "docs" / "phase14" / "HYP_010_VEU_AUTHORITY_RESOLUTION.md"
RES_MANIFEST = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_010_VEU_AUTHORITY_RESOLUTION.json"
)


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_amounts_corroborated_dates_absent() -> None:
    m = _load(RES_MANIFEST)
    assert m["march_2016_source"]["amount_usd"] == "0.148"
    assert m["march_2016_source"]["amount_status"] == "ISSUER_ORIGIN_CORROBORATED"
    assert m["june_2016_source"]["amount_usd"] == "0.53"
    assert m["june_2016_source"]["amount_status"] == "ISSUER_ORIGIN_CORROBORATED"
    assert m["march_2016_source"]["us_share_dates"] == "ABSENT"
    assert m["june_2016_source"]["us_share_dates"] == "ABSENT"
    assert m["june_2016_source"]["context"] == "AUSTRALIAN_CDI_ONLY_US_AU_DIFFERENCES_STATED"


def test_no_inference_no_substitution_block_retained() -> None:
    m = _load(RES_MANIFEST)
    assert m["inference_used"] is False
    assert m["substitution_used"] is False
    assert m["veu_verdict"] == "BLOCKED_VEU_DIVIDEND_AUTHORITY_NO_RECORDS"
    assert m["overall_r2_verdict"] == "R2_PROVIDER_QUALIFIED_SPONSOR_AUTHORITY_BLOCKED"
    assert m["full_acquisition_executed"] is False
    assert m["momentum_computed"] is False
    assert m["performance_computed"] is False
    assert m["vanguard_ten_year_limitation_reproduced"] is True


def test_resolution_doc_states() -> None:
    assert RES_DOC.is_file()
    text = RES_DOC.read_text(encoding="utf-8")
    assert "BLOCKED_VEU_DIVIDEND_AUTHORITY_NO_RECORDS RETAINED" in text
    assert "tenYearsMessage" in text
    assert "ten years of distributions for this fund" in text
    assert "MUST NOT be mapped" in text or "MUST NOT" in text
