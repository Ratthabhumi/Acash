"""Seal tests for HYP_009 R2 M2 single canonical run (K=1, G4 FAIL verdict).

Verifies sealed dataset, exact metrics, derived G6, verdict label, and locks.
No network.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "hyp_009"
RESULT = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_R2_M2_RESULT.json"
DATASET_MANIFEST = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_R2_M2_DATASET.json"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_m2_dataset_seal() -> None:
    ds = _load(DATASET_MANIFEST)
    assert ds["dataset_state"] == "M2_DATASET_QUALIFIED_AND_SEALED_PERFORMANCE_REPLAYED_ONCE"
    assert ds["expected_sessions"] == 1005
    assert ds["split_bar_count"] == 1005
    assert ds["raw_bar_count"] == 1005
    assert ds["missing_sessions"] == 0
    assert ds["duplicate_sessions"] == 0
    assert ds["dividend_event_count"] == 13
    assert ds["split_determination"] == "NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW"
    assert ds["actual_http_transport_attempts"] == 2
    raw = (DATA_DIR / "m2_dataset.json").read_bytes()
    assert b"\r" not in raw
    assert hashlib.sha256(raw).hexdigest() == ds["dataset_sha256"]
    assert ds["m3_access_count"] == 0
    assert ds["quarantine_access_count"] == 0
    assert ds["prospective_access_count"] == 0


def test_m2_exact_metrics() -> None:
    r = _load(RESULT)
    base, stress, bench = r["baseline_metrics"], r["stress_metrics"], r["benchmark_metrics"]
    assert base["starting_aum"] == "100000.00"
    assert base["ending_aum"] == "136245.1680884"
    assert base["net_total_return"] == "0.362451680884"
    assert base["annualized_sharpe"] == "0.7310806434865794464782941709"
    assert base["max_drawdown"] == "0.2557624443312489943856781208"
    assert base["completed_trades"] == "9"
    assert stress["ending_aum"] == "135215.777549"
    assert stress["net_total_return"] == "0.35215777549"
    assert stress["annualized_sharpe"] == "0.7170002785477880420023898889"
    assert stress["max_drawdown"] == "0.2596240811274515820595574966"
    assert bench["ending_aum"] == "161436.045482"
    assert bench["net_total_return"] == "0.61436045482"
    assert bench["max_drawdown"] == "0.2409397072449208847315742869"


def test_m2_gates_g4_fail_verdict() -> None:
    r = _load(RESULT)
    assert r["gates"] == {
        "G1": True, "G2": True, "G3": True, "G4": False,
        "G5": True, "G6": True, "conjunction": False,
    }
    assert r["contract_qualification_derived"] is True
    assert r["verdict"] == "FAIL_CORE_EDGE_NOT_SUPPORTED"
    assert r["dec2020_initial_state"] == "LONG"
    assert r["first_m2_execution_date"] == "2021-01-04"


def test_m2_signal_structure() -> None:
    sig = _load(DATA_DIR / "m2_signal_ledger.json")
    assert len(sig["rows"]) == 48
    states = [row["state"] for row in sig["rows"]]
    assert states.count("LONG") == 38
    assert states.count("CASH") == 10
    assert sig["pending_terminal"] == []
    assert sig["warmup_authority"] == "SEALED_M1_SIGNAL_HISTORY_THROUGH_2020_12_31"
    assert sig["dec2020_injected_state"] == "LONG"


def test_m2_ledger_pins_and_locks() -> None:
    r = _load(RESULT)
    pairs = [
        ("signal_ledger_sha256", DATA_DIR / "m2_signal_ledger.json"),
        ("baseline_execution_ledger_sha256", DATA_DIR / "m2_execution_ledger_baseline.json"),
        ("stress_execution_ledger_sha256", DATA_DIR / "m2_execution_ledger_stress.json"),
        ("baseline_equity_ledger_sha256", DATA_DIR / "m2_equity_baseline.json"),
        ("stress_equity_ledger_sha256", DATA_DIR / "m2_equity_stress.json"),
        ("benchmark_equity_ledger_sha256", DATA_DIR / "m2_equity_benchmark.json"),
        ("dataset_sha256", DATA_DIR / "m2_dataset.json"),
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
