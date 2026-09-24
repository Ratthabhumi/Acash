"""Seal tests for HYP_009 R2 M1 dataset + result (post-execution, K=1 canonical run).

Verifies pinned hashes, CR-free sealed bytes, gate verdict, and locks.
No network. Reads committed artifacts + gitignored local dataset mirror.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "hyp_009"
RESULT_MANIFEST = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_R2_M1_RESULT.json"
DATASET_MANIFEST = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_009_R2_M1_DATASET.json"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_sealed_files_cr_free_and_hashes_match() -> None:
    pairs = [
        ("signal_ledger_sha256", DATA_DIR / "signal_ledger.json"),
        ("baseline_execution_ledger_sha256", DATA_DIR / "execution_ledger_baseline.json"),
        ("stress_execution_ledger_sha256", DATA_DIR / "execution_ledger_stress.json"),
        ("baseline_equity_ledger_sha256", DATA_DIR / "equity_baseline.json"),
        ("stress_equity_ledger_sha256", DATA_DIR / "equity_stress.json"),
        ("benchmark_equity_ledger_sha256", DATA_DIR / "equity_benchmark.json"),
        ("dataset_sha256", DATA_DIR / "m1_dataset.json"),
    ]
    res = _load(RESULT_MANIFEST)
    for key, path in pairs:
        raw = path.read_bytes()
        assert b"\r" not in raw, f"CR byte in sealed file: {path.name}"
        assert hashlib.sha256(raw).hexdigest() == res[key], f"hash mismatch: {key}"


def test_result_verdict_and_gates_sealed() -> None:
    res = _load(RESULT_MANIFEST)
    assert res["verdict"] == "M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION"
    gates = res["gates"]
    assert gates == {
        "G1": True,
        "G2": True,
        "G3": True,
        "G4": True,
        "G5": True,
        "G6": True,
        "conjunction": True,
    }
    assert res["baseline_metrics"]["ending_aum"] == "145227.3118497"
    assert res["stress_metrics"]["ending_aum"] == "144262.5069729"
    assert res["benchmark_metrics"]["ending_aum"] == "186210.7615481"


def test_dataset_manifest_sealed_state() -> None:
    ds = _load(DATASET_MANIFEST)
    assert ds["dataset_state"] == "SEALED_M1_DATASET"
    assert ds["expected_sessions"] == 1259
    assert ds["split_bar_count"] == 1259
    assert ds["raw_bar_count"] == 1259
    assert ds["missing_sessions"] == 0
    assert ds["duplicate_sessions"] == 0
    assert ds["unauthorized_rows"] == 0
    assert ds["dividend_event_count"] == 20
    assert ds["split_determination"] == "NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW"
    assert ds["m2_access_count"] == 0
    assert ds["m3_access_count"] == 0
    assert ds["quarantine_access_count"] == 0
    assert ds["prospective_access_count"] == 0


def test_result_locks_intact() -> None:
    res = _load(RESULT_MANIFEST)
    assert res["m2_access_count"] == 0
    assert res["m3_access_count"] == 0
    assert res["quarantine_access_count"] == 0
    assert res["prospective_access_count"] == 0
    assert res["hyp_007_empirical_read_count"] == 0
    assert res["paper_authorized"] is False
    assert res["live_authorized"] is False
    assert res["capital_authority_usd"] == "0.00"
    assert res["no_real_orders"] is True
