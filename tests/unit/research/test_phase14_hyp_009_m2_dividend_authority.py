"""Dividend-authority coverage tests (HYP_009 M2 corrective lineage).

Proves the old 13-event authority alone CANNOT qualify M2 (coverage gap) and
the composite 16-event authority (sealed manifest + official 2024 supplement)
DOES qualify. Reads sealed artifacts only. No network.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, cast

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.hyp_009 import partitions as PART
from acash.research.hyp_009 import qualification as QUAL

REPO_ROOT = Path(__file__).resolve().parents[3]
MEC_0015_MANIFEST = (
    REPO_ROOT / "docs" / "research" / "manifests" / "MEC-0015-SPY-dividend-authority-manifest.json"
)
SUPPLEMENT_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "research"
    / "manifests"
    / "HYP_009_SPY_2024_DIVIDEND_AUTHORITY_SUPPLEMENT.json"
)


def _records(path: Path) -> List[Dict[str, Any]]:
    manifest = cast(
        Dict[str, Any], json.loads(path.read_text(encoding="utf-8"))
    )
    return cast(List[Dict[str, Any]], manifest["distributions"])


def test_supplement_encodes_exact_supplied_records() -> None:
    records = _records(SUPPLEMENT_MANIFEST)
    assert len(records) == 3
    by_ex = {r["ex_date"]: r for r in records}
    assert by_ex["2024-06-21"]["cash_distribution"] == "1.75902"
    assert by_ex["2024-06-21"]["payable_date"] == "2024-08-14"
    assert by_ex["2024-09-20"]["cash_distribution"] == "1.74553"
    assert by_ex["2024-09-20"]["payable_date"] == "2024-11-14"
    assert by_ex["2024-12-20"]["cash_distribution"] == "1.96555"
    assert by_ex["2024-12-20"]["payable_date"] == "2025-02-14"


def test_old_authority_alone_fails_m2_coverage() -> None:
    events = QUAL.qualify_dividends(
        _records(MEC_0015_MANIFEST), PART.M2_START, PART.M2_END
    )
    assert len(events) == 13
    with pytest.raises(DataContractError, match="BLOCKED_DIVIDEND_AUTHORITY_COVERAGE_GAP"):
        QUAL.require_quarterly_authority_coverage(
            events, PART.M2_START, PART.M2_END
        )


def test_composite_authority_qualifies_m2_with_16_events() -> None:
    combined = _records(MEC_0015_MANIFEST) + _records(SUPPLEMENT_MANIFEST)
    events = QUAL.qualify_dividends(combined, PART.M2_START, PART.M2_END)
    assert len(events) == 16
    assert QUAL.require_quarterly_authority_coverage(
        events, PART.M2_START, PART.M2_END
    ) == "DIVIDEND_AUTHORITY_COVERAGE_COMPLETE"
    assert all(e.payable_date is not None for e in events)
    ex_dates = sorted(e.ex_date for e in events)
    assert date(2024, 6, 21) in ex_dates
    assert date(2024, 9, 20) in ex_dates
    assert date(2024, 12, 20) in ex_dates
