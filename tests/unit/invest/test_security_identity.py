"""Ticker reuse: a series that spans two identities is never eligible for research."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import readiness as rd
from acash.invest import research_panel as rp
from acash.invest import security_identity as si

REGISTRY = si.load_registry(Path(si.DEFAULT_REGISTRY))


def test_registry_distinguishes_legacy_and_new_spcx() -> None:
    legacy = si.series_identities(REGISTRY, "SPCX", [date(2026, 3, 2)])
    assert legacy["status"] == "SINGLE_IDENTITY"
    assert legacy["identities"][0]["canonical_id"] == "SPCX_LEGACY_SPAC_AND_NEW_ISSUE_ETF"
    modern = si.series_identities(REGISTRY, "SPCX", [date(2026, 7, 1)])
    assert modern["identities"][0]["canonical_id"] == "SPCX_SPACE_EXPLORATION_TECHNOLOGIES"
    # The rename gap (2026-04-07 .. 2026-06-11) maps to no identity at all.
    gap = si.series_identities(REGISTRY, "SPCX", [date(2026, 5, 1)])
    assert gap["status"] == "NO_MATCHED_DAYS" and gap["unmapped_days"] == 1


def test_a_series_spanning_two_identities_is_blocked() -> None:
    result = si.research_eligibility(REGISTRY, "SPCX", [date(2026, 3, 2), date(2026, 7, 1)])
    assert result["eligible"] is False and result["reason"] == si.MULTI
    with pytest.raises(DataContractError, match="IDENTITY_RETURN_CROSSES_SECURITIES"):
        si.assert_single_identity(REGISTRY, "SPCX", [date(2026, 3, 2), date(2026, 7, 1)])


def test_single_identity_still_blocked_until_eligible() -> None:
    result = si.research_eligibility(REGISTRY, "SPCX", [date(2026, 7, 1)])
    assert result["status"] == "SINGLE_IDENTITY" and result["eligible"] is False
    assert result["reason"] == si.UNVERIFIED


def test_unknown_ticker_keeps_its_snapshot_identity() -> None:
    result = si.research_eligibility(REGISTRY, "NASA", [date(2026, 4, 1)])
    assert result["eligible"] is True and result["reason"] == si.NO_ENTRY


def test_cohorts_exclude_the_identity_collision() -> None:
    days = [date(2026, 1, 5), date(2026, 6, 15)]
    closes: Dict[str, Dict[date, Decimal]] = {
        "SPCX": {days[0]: Decimal("22"), days[1]: Decimal("180")},
        "VOO": {days[0]: Decimal("100"), days[1]: Decimal("105")},
    }
    weights = {"SPCX": Decimal("0.5"), "VOO": Decimal("0.5")}
    panel = rp.build_panel(closes, weights, ["SPCX", "VOO"], min_sessions=1, registry=REGISTRY)
    assert panel["excluded"]["SPCX"]["reason"] == si.MULTI
    assert panel["eligible"] == ["VOO"]
    assert panel["inputs"].current_weights == {"VOO": Decimal(1)}


def test_readiness_blocks_the_decision_when_identity_is_unresolved() -> None:
    report = {"coverage": {"union_last": "2026-11-04", "covered": 23, "partial": 1, "missing": 0},
              "cohort_summary": [{"cohort_id": "ESTABLISHED_HISTORY", "status": "PANEL_READY",
                                  "session_count": 404, "strategy_id": "CASH",
                                  "evaluation_status": "BENCHMARK_ELIGIBLE"}],
              "identity": {"blocked": {"SPCX": {"reason": "MULTI_IDENTITY"}}}}
    view = {"report_metadata": {"valuation_date": "2026-11-02"},
            "portfolio_overview": {"total_best_evidence": "208740.01"}, "positions": {"rows": [{}]},
            "accounts": [{"account_total": {"status": "RECONCILED"}}], "financial_capacity": {}}
    result = rd.build_readiness(view=view, health={"storage_rights": "PERMITTED", "coverage": {}},
                                report=report, tax={"readiness": {"trade_history": "PARTIAL_EVIDENCE_ONLY",
                                                                  "historical_performance": "DATA_REQUIRED"}},
                                registry=REGISTRY)
    assert result["decision_readiness"]["status"] == "BLOCKED"
    assert result["decision_readiness"]["identity"]["blocked"] == ["SPCX"]
    assert any("SPCX" in step for step in result["decision_readiness"]["next_evidence"])
    assert result["historical_research"]["realized_performance"] is False
    assert result["decision_readiness"]["execution_authority"] == "NONE"


def test_sync_is_delta_and_scheduler_waits_for_the_collection_window() -> None:
    sync = Path("scripts/deploy/Sync-WarehouseFromHomelab.ps1").read_text(encoding="utf-8")
    assert "no changed partitions; nothing to transfer" in sync
    assert "SYNC_HASH_MISMATCH" in sync and "market_warehouse.previous" in sync
    assert "scp -q -r \"${HostName}:${RemoteState}/.\"" not in sync  # no whole-warehouse copy
    assert "provider_calls = 0" in sync
    task = Path("scripts/deploy/Register-AcashSyncTask.ps1").read_text(encoding="utf-8")
    assert "13:30" in task and "Tuesday, Wednesday, Thursday, Friday, Saturday" in task
    assert "-StartWhenAvailable" in task
