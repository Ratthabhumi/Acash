"""Seal tests for HYP_011 corrected reproducibility (ONE zero-network replay).

Verifies ledger equality, corrected MDD values, economics invariance, gates,
verdict, and locks. No network.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
CORRECTED = (
    REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_011_R3_CORRECTED_REPRODUCIBILITY_RESULT.json"
)
ORIGINAL = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_011_R3_HISTORICAL_RESULT.json"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_original_preserved_and_adjudicated() -> None:
    orig = _load(ORIGINAL)
    assert orig["manifest_id"] == "HYP_011_R3_HISTORICAL_RESULT"
    assert orig["verdict"] == "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW"
    new = _load(CORRECTED)
    assert new["invalidation"] == "HISTORICAL_RESULT_INVALIDATED_BY_IMPLEMENTATION_DEFECT"
    assert new["supersedes_invalidated_run"].endswith("HYP_011_R3_HISTORICAL_RESULT.json")


def test_ledger_pins_match_original() -> None:
    new = _load(CORRECTED)
    orig = _load(ORIGINAL)
    for key in (
        "dataset_sha256", "signal_ledger_sha256",
        "baseline_execution_ledger_sha256", "stress_execution_ledger_sha256",
        "baseline_equity_ledger_sha256", "stress_equity_ledger_sha256",
        "benchmark_equity_ledger_sha256", "acwi_benchmark_equity_ledger_sha256",
    ):
        assert new[key] == orig[key], f"ledger drift: {key}"


def test_corrected_mdd_values() -> None:
    new = _load(CORRECTED)
    assert new["baseline_metrics"]["max_drawdown"] == "0.2706804464703170979420276404"
    assert new["stress_metrics"]["max_drawdown"] == "0.2707610914922089320548722783"
    assert new["benchmark_metrics"]["max_drawdown"] == "0.3185096087705842203186407916"
    assert new["acwi_benchmark_metrics"]["max_drawdown"] == "0.3123026836287247134564365735"
    comp = new["mdd_correction"]
    assert comp["baseline_mdd_original"] == comp["baseline_mdd_corrected"]
    assert comp["benchmark_mdd_original"] == comp["benchmark_mdd_corrected"]


def test_economics_unchanged() -> None:
    new = _load(CORRECTED)
    flags = new["economics_unchanged"]
    assert all(flags.values()), [k for k, v in flags.items() if not v]
    assert new["baseline_metrics"]["ending_aum"] == "218852.857740"
    assert new["baseline_metrics"]["net_total_return"] == "1.1885285774"
    assert new["baseline_metrics"]["annualized_sharpe"] == "0.7082199886205631037448519049"


def test_gates_verdict_locks() -> None:
    new = _load(CORRECTED)
    assert new["gates"] == {
        "G1": True, "G2": True, "G3": True, "G4": True,
        "G5": True, "G6": True, "conjunction": True,
    }
    assert new["contract_qualification_derived"] is True
    assert new["verdict"] == "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW"
    assert new["network_requests_issued"] == 0
    assert new["recent_stress_access_count"] == 0
    assert new["quarantine_access_count"] == 0
    assert new["prospective_access_count"] == 0
    assert new["hyp_007_empirical_read_count"] == 0
    assert new["paper_authorized"] is False
    assert new["live_authorized"] is False
    assert new["capital_authority_usd"] == "0.00"
    assert new["no_real_orders"] is True
