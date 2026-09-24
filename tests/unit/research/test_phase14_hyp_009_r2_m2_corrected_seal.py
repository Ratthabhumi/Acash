"""Seal tests for corrected HYP_009 M2 (16-event authority, contract-valid FAIL).

Verifies corrected dataset/result seals, exact metrics, derived G6, terminal
closure, and locks. No network.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "hyp_009"
RESULT = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_009_R2_M2_DIVIDEND_CORRECTED_RESULT.json"
)
DATASET_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_009_R2_M2_DIVIDEND_CORRECTED_DATASET.json"
)
TERMINAL = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_TERMINAL_M2_DECISION.json"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_corrected_dataset_seal_16_events() -> None:
    ds = _load(DATASET_MANIFEST)
    assert ds["dataset_state"] == "M2_DIVIDEND_CORRECTED_DATASET_SEALED_PERFORMANCE_REPLAYED_ONCE"
    assert ds["expected_sessions"] == 1005
    assert ds["split_bar_count"] == 1005
    assert ds["raw_bar_count"] == 1005
    assert ds["missing_sessions"] == 0
    assert ds["dividend_event_count"] == 16
    assert ds["payable_completeness"] == "COMPLETE_16_OF_16"
    assert ds["actual_http_transport_attempts"] == 2
    raw = (DATA_DIR / "m2_dataset_dividend_corrected_001.json").read_bytes()
    assert b"\r" not in raw
    assert hashlib.sha256(raw).hexdigest() == ds["dataset_sha256"]
    assert ds["m3_access_count"] == 0
    assert ds["quarantine_access_count"] == 0
    assert ds["prospective_access_count"] == 0


def test_corrected_exact_metrics() -> None:
    r = _load(RESULT)
    base, stress, bench = r["baseline_metrics"], r["stress_metrics"], r["benchmark_metrics"]
    assert base["starting_aum"] == "100000.00"
    assert base["ending_aum"] == "137508.7611884"
    assert base["net_total_return"] == "0.375087611884"
    assert base["annualized_sharpe"] == "0.7503662265800349025883731009"
    assert base["max_drawdown"] == "0.2557624443312489943856781208"
    assert base["terminal_shares"] == "231"
    assert base["terminal_receivable"] == "454.04205"
    assert stress["ending_aum"] == "136468.430449"
    assert stress["net_total_return"] == "0.36468430449"
    assert stress["annualized_sharpe"] == "0.7362489911056248154166420563"
    assert stress["max_drawdown"] == "0.2596240811274515820595574966"
    assert bench["ending_aum"] == "162891.092082"
    assert bench["net_total_return"] == "0.62891092082"
    assert bench["max_drawdown"] == "0.2409397072449208847315742869"


def test_corrected_gates_g4_fail_verdict() -> None:
    r = _load(RESULT)
    assert r["gates"] == {
        "G1": True, "G2": True, "G3": True, "G4": False,
        "G5": True, "G6": True, "conjunction": False,
    }
    assert r["contract_qualification_derived"] is True
    assert r["verdict"] == "FAIL_CORE_EDGE_NOT_SUPPORTED"
    assert r["dividend_authority"] == "COMPOSITE_MEC0015_PLUS_2024_SUPPLEMENT_16_EVENTS"
    assert r["invalidation"] == "M2_INVALIDATED_BY_DIVIDEND_AUTHORITY_GAP"


def test_corrected_signal_structure() -> None:
    sig = _load(DATA_DIR / "m2_signal_ledger_dividend_corrected_001.json")
    assert len(sig["rows"]) == 48
    states = [row["state"] for row in sig["rows"]]
    assert states.count("LONG") == 38
    assert states.count("CASH") == 10
    assert sig["pending_terminal"] == []
    base_exec = _load(DATA_DIR / "m2_execution_ledger_baseline_dividend_corrected_001.json")
    assert len(base_exec["rows"]) == 9


def test_corrected_ledger_pins_and_locks() -> None:
    r = _load(RESULT)
    pairs = [
        ("signal_ledger_sha256", DATA_DIR / "m2_signal_ledger_dividend_corrected_001.json"),
        ("baseline_execution_ledger_sha256", DATA_DIR / "m2_execution_ledger_baseline_dividend_corrected_001.json"),
        ("stress_execution_ledger_sha256", DATA_DIR / "m2_execution_ledger_stress_dividend_corrected_001.json"),
        ("baseline_equity_ledger_sha256", DATA_DIR / "m2_equity_baseline_dividend_corrected_001.json"),
        ("stress_equity_ledger_sha256", DATA_DIR / "m2_equity_stress_dividend_corrected_001.json"),
        ("benchmark_equity_ledger_sha256", DATA_DIR / "m2_equity_benchmark_dividend_corrected_001.json"),
        ("dataset_sha256", DATA_DIR / "m2_dataset_dividend_corrected_001.json"),
    ]
    for key, path in pairs:
        raw = path.read_bytes()
        assert b"\r" not in raw, f"CR byte: {path.name}"
        assert hashlib.sha256(raw).hexdigest() == r[key], f"mismatch: {key}"
    assert r["m2_access_count"] == 2
    assert r["m3_access_count"] == 0
    assert r["quarantine_access_count"] == 0
    assert r["prospective_access_count"] == 0
    assert r["hyp_007_empirical_read_count"] == 0
    assert r["paper_authorized"] is False
    assert r["live_authorized"] is False
    assert r["capital_authority_usd"] == "0.00"
    assert r["no_real_orders"] is True


def test_terminal_closure_hyp_009_core_001_open() -> None:
    t = _load(TERMINAL)
    assert t["hyp_009_state"] == "HYP_009_TERMINAL_NOT_SUPPORTED_AT_LOCKED_M2"
    assert t["core_001_state"] == "CORE-001_RESEARCH_OBJECTIVE_REMAINS_OPEN"
    assert t["corrected_m2_verdict"] == "FAIL_CORE_EDGE_NOT_SUPPORTED"
    assert t["failing_gate"] == "G4"
    assert t["m3_authorized"] is False
    assert t["successor_hypothesis_created"] is False
