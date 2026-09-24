"""Seal tests for HYP_009 M1 reproducibility run (ONE corrective execution).

Verifies exact reproduction of frozen §14 targets, corrected provenance, and
preservation of original a3170aa artifacts. No network.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "hyp_009"
REPRO_RESULT = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_R2_M1_REPRODUCIBILITY_RESULT.json"
)
REPRO_DATASET = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_R2_M1_REPRODUCIBILITY_DATASET.json"
)
ORIG_RESULT = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_R2_M1_RESULT.json"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_repro_exact_metric_targets() -> None:
    r = _load(REPRO_RESULT)
    base, stress, bench = (
        r["baseline_metrics"],
        r["stress_metrics"],
        r["benchmark_metrics"],
    )
    assert base["ending_aum"] == "145227.3118497"
    assert base["net_total_return"] == "0.452273118497"
    assert base["annualized_sharpe"] == "0.7873848313776889894031366474"
    assert base["max_drawdown"] == "0.2243751746642665240571654904"
    assert base["terminal_shares"] == "383"
    assert stress["ending_aum"] == "144262.5069729"
    assert stress["net_total_return"] == "0.442625069729"
    assert stress["annualized_sharpe"] == "0.7757119247420111210807917343"
    assert stress["max_drawdown"] == "0.2281301602333229542420748959"
    assert bench["ending_aum"] == "186210.7615481"
    assert bench["net_total_return"] == "0.862107615481"
    assert bench["max_drawdown"] == "0.3214097537014617766443093897"


def test_repro_signal_trade_structure() -> None:
    sig = _load(DATA_DIR / "signal_ledger_reproducibility_001.json")
    assert len(sig["rows"]) == 51
    states = [row["state"] for row in sig["rows"]]
    assert states.count("LONG") == 44
    assert states.count("CASH") == 7
    assert len(sig["pending_terminal"]) == 1
    assert sig["pending_terminal"][0]["decision_date"] == "2020-12-31"
    base_exec = _load(DATA_DIR / "execution_ledger_baseline_reproducibility_001.json")
    assert len(base_exec["rows"]) == 9
    assert sum(1 for row in base_exec["rows"] if row["side"] == "BUY") == 5
    assert sum(1 for row in base_exec["rows"] if row["side"] == "SELL") == 4
    assert "regulatory_fees_paid" in base_exec["rows"][0]
    assert "execution_slippage_cost" in base_exec["rows"][0]
    assert "total_friction" not in base_exec["rows"][0]


def test_repro_gates_derived_and_verdict() -> None:
    r = _load(REPRO_RESULT)
    assert r["gates"] == {
        "G1": True, "G2": True, "G3": True, "G4": True,
        "G5": True, "G6": True, "conjunction": True,
    }
    qual = r["contract_qualification"]
    assert qual["g6_derived"] is True
    assert all(
        qual[key] is True
        for key in (
            "provider_contract_pass", "calendar_coverage_pass",
            "split_raw_alignment_pass", "dividend_contract_pass",
            "payable_date_contract_pass", "split_contract_pass",
            "response_scope_pass", "provenance_hash_pass",
            "serialization_integrity_pass", "forbidden_partition_access_zero",
        )
    )
    assert r["verdict"] == "M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION"
    assert r["actual_http_transport_attempts"] == 2


def test_repro_dataset_seal_and_provenance() -> None:
    ds = _load(REPRO_DATASET)
    assert ds["dataset_state"] == (
        "M1_REPRODUCIBILITY_DATASET_SEALED_PERFORMANCE_REPLAYED_ONCE"
    )
    assert ds["expected_sessions"] == 1259
    assert ds["split_bar_count"] == 1259
    assert ds["raw_bar_count"] == 1259
    assert ds["missing_sessions"] == 0
    assert ds["duplicate_sessions"] == 0
    assert ds["dividend_event_count"] == 20
    assert ds["actual_http_transport_attempts"] == 2
    assert len(ds["split_page_sha256"]) == 1
    assert len(ds["raw_page_sha256"]) == 1
    assert ds["m2_access_count"] == 0
    assert ds["m3_access_count"] == 0
    assert ds["quarantine_access_count"] == 0
    assert ds["prospective_access_count"] == 0
    raw = (DATA_DIR / "m1_dataset_reproducibility_001.json").read_bytes()
    assert b"\r" not in raw
    assert hashlib.sha256(raw).hexdigest() == ds["dataset_sha256"]


def test_original_a3170aa_artifacts_preserved() -> None:
    orig = _load(ORIG_RESULT)
    assert orig["manifest_id"] == "HYP_009_R2_M1_RESULT"
    assert orig["verdict"] == "M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION"
    assert orig["baseline_metrics"]["ending_aum"] == "145227.3118497"
    assert "total_friction" in orig["baseline_metrics"]
    assert (REPO_ROOT / "docs" / "phase14" / "HYP_009_R2_M1_EXECUTION_REPORT.md").is_file()
    assert (REPO_ROOT / "docs" / "phase14" / "HYP_009_R2_M1_DATA_QUALIFICATION.md").is_file()


def test_repro_locks_intact() -> None:
    r = _load(REPRO_RESULT)
    assert r["m2_access_count"] == 0
    assert r["m3_access_count"] == 0
    assert r["quarantine_access_count"] == 0
    assert r["prospective_access_count"] == 0
    assert r["hyp_007_empirical_read_count"] == 0
    assert r["paper_authorized"] is False
    assert r["live_authorized"] is False
    assert r["capital_authority_usd"] == "0.00"
    assert r["no_real_orders"] is True
