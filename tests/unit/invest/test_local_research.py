"""Local D6 dataset qualification and reuse (synthetic fixtures only)."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Sequence

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import local_research as lr
from acash.invest import research_proposal as rp

BARS = [
    ("VOO", "2026-01-02", 100, 100, "raw"), ("VOO", "2026-01-05", 101, 101, "raw"),
    ("VOO", "2026-01-06", 102, 102, "raw"), ("VOO", "2026-01-07", 103, 103, "raw"),
    ("VOO", "2026-01-08", 104, 104, "raw"),
    ("BIL", "2026-01-02", 91, 91, "raw"), ("BIL", "2026-01-06", 91.1, 91.1, "raw"),
    ("GLD", "2026-01-02", 180, 180, "raw"), ("GLD", "2026-01-05", 181, 181, "raw"),
    ("GLD", "2026-01-06", 182, 182, "raw"), ("GLD", "2026-01-07", 183, 183, "raw"),
    ("GLD", "2026-01-08", 184, 184, "raw"),
]


def _write(dir_path: Path, rows: Sequence[Sequence[object]] = BARS, distributions: int = 1, splits: int = 0,
           asof: str = "provider default (not pinned)") -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    with (dir_path / "bars_raw.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "session", "open", "close", "adjustment"])
        writer.writerows(rows)
    with (dir_path / "distributions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "ex_date", "payable_date", "gross_amount", "distribution_type"])
        for i in range(distributions):
            writer.writerow(["VOO", "2026-01-05", "2026-01-08", "1.00", "CASH"])
    with (dir_path / "splits.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "session", "ratio"])
        for i in range(splits):
            writer.writerow(["VOO", "2026-01-05", "2"])
    (dir_path / "fetch_manifest.json").write_text(json.dumps({"asof": asof, "counts": {"bars": len(rows)}}),
                                                  encoding="utf-8")
    return dir_path


def test_coverage_reports_gaps_without_filling(tmp_path: Path) -> None:
    dataset = lr.load_d6(_write(tmp_path))
    result = lr.coverage(dataset, ["VOO", "BIL"])
    assert result["status"] == "QUALIFIED_FOR_PRICE_RETURN"
    assert result["price_basis"] == lr.PRICE_RETURN
    assert result["distributions"] == 1 and result["splits"] == 0
    assert result["symbols"]["VOO"]["sessions"] == 5 and result["symbols"]["VOO"]["status"] == "COVERED"
    assert result["symbols"]["BIL"]["gaps_vs_union"] == 3 and result["symbols"]["BIL"]["status"] == "PARTIAL"
    assert result["manifest_asof"] == "provider default (not pinned)"


def test_aligned_returns_use_the_intersection_only(tmp_path: Path) -> None:
    dataset = lr.load_d6(_write(tmp_path))
    sessions, returns = lr.aligned_returns(dataset, ["VOO", "BIL"])
    # VOO has an extra session on 2026-01-05; the intersection drops it rather than filling BIL.
    assert [s.isoformat() for s in sessions] == ["2026-01-06"]
    assert len(returns["VOO"]) == len(returns["BIL"]) == 1
    assert returns["VOO"][0] == (Decimal("102") / Decimal("100")) - 1


def test_conflicting_duplicate_bar_is_refused(tmp_path: Path) -> None:
    rows = BARS + [("VOO", "2026-01-05", 999, 999, "raw")]
    with pytest.raises(DataContractError, match="LOCAL_BAR_DUPLICATE_CONFLICT"):
        lr.load_d6(_write(tmp_path, rows=rows))


def test_qualified_panel_feeds_the_existing_proposal_engine(tmp_path: Path) -> None:
    dataset = lr.load_d6(_write(tmp_path))
    built = lr.proposal_inputs(dataset, ["VOO", "GLD"], {"VOO": Decimal("1"), "GLD": Decimal("0")})
    assert built["price_basis"] == lr.PRICE_RETURN and built["sessions"] == 4
    proposal = rp.build_proposal(built["inputs"])
    assert proposal["recommendation_status"] == rp.RESEARCH_ONLY
    assert proposal["execution_authority"] == "NONE"
    assert set(proposal) >= {"strategy_id", "target_weights", "cash_weight", "proposed_actions"}
