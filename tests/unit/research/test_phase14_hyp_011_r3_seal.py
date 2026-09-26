"""Seal tests for HYP_011 R3 historical single canonical run (K=1).

Verifies dataset seal, exact metrics, derived G6, verdict, and locks.
No network.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "hyp_011"
RESULT = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_011_R3_HISTORICAL_RESULT.json"
DATASET_MANIFEST = REPO_ROOT / "docs" / "phase14" / "manifests" / "HYP_011_R3_HISTORICAL_DATASET.json"


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_dataset_seal() -> None:
    ds = _load(DATASET_MANIFEST)
    assert ds["dataset_state"] == "HISTORICAL_DATASET_QUALIFIED_AND_SEALED_PERFORMANCE_REPLAYED_ONCE"
    assert ds["expected_sessions"] == 2264
    assert ds["series_counts"]["ACWI"] == {"split": 2264, "raw": 2264}
    assert ds["series_counts"]["AGG"] == {"split": 2264, "raw": 2264}
    assert ds["series_counts"]["SPY"] == {"split": 2264, "raw": 2264}
    assert ds["missing_sessions"] == 0
    assert ds["actual_http_transport_attempts"] == 6
    raw = (DATA_DIR / "historical_dataset_001.json").read_bytes()
    assert b"\r" not in raw
    assert hashlib.sha256(raw).hexdigest() == ds["dataset_sha256"]
    assert ds["recent_stress_access_count"] == 0
    assert ds["quarantine_access_count"] == 0
    assert ds["prospective_access_count"] == 0


def test_exact_metrics() -> None:
    r = _load(RESULT)
    base, stress = r["baseline_metrics"], r["stress_metrics"]
    bench, acwi = r["benchmark_metrics"], r["acwi_benchmark_metrics"]
    assert base["starting_aum"] == "100000.00"
    assert base["ending_aum"] == "218852.857740"
    assert base["net_total_return"] == "1.1885285774"
    assert base["annualized_sharpe"] == "0.7082199886205631037448519049"
    assert base["max_drawdown"] == "0.2706804464703170979420276404"
    assert base["completed_trades"] == "18"
    assert base["terminal_holdings"] == {"ACWI": "1507", "AGG": "385"}
    assert stress["ending_aum"] == "218619.359444"
    assert stress["net_total_return"] == "1.18619359444"
    assert stress["annualized_sharpe"] == "0.7072509593375763856321580724"
    assert stress["max_drawdown"] == "0.2707610914922089320548722783"
    assert bench["ending_aum"] == "317645.2207582"
    assert bench["net_total_return"] == "2.176452207582"
    assert bench["max_drawdown"] == "0.3185096087705842203186407916"
    assert acwi["ending_aum"] == "240741.694289"


def test_gates_verdict_rebalances() -> None:
    r = _load(RESULT)
    assert r["gates"] == {
        "G1": True, "G2": True, "G3": True, "G4": True,
        "G5": True, "G6": True, "conjunction": True,
    }
    assert r["contract_qualification_derived"] is True
    assert r["verdict"] == "HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW"
    be = _load(DATA_DIR / "execution_ledger_baseline.json")
    assert len(be["rows"]) == 18
    assert sum(1 for t in be["rows"] if t["side"] == "BUY") == 11
    assert sum(1 for t in be["rows"] if t["side"] == "SELL") == 7
    sessions = sorted({t["execution_date"] for t in be["rows"]})
    assert sessions == [
        "2016-01-04", "2017-01-03", "2018-01-02", "2019-01-02", "2020-01-02",
        "2021-01-04", "2022-01-03", "2023-01-03", "2024-01-02",
    ]


def test_ledger_pins_cash_leverage_dividends() -> None:
    r = _load(RESULT)
    pairs = [
        ("signal_ledger_sha256", DATA_DIR / "rebalance_schedule.json"),
        ("baseline_execution_ledger_sha256", DATA_DIR / "execution_ledger_baseline.json"),
        ("stress_execution_ledger_sha256", DATA_DIR / "execution_ledger_stress.json"),
        ("baseline_equity_ledger_sha256", DATA_DIR / "equity_baseline.json"),
        ("stress_equity_ledger_sha256", DATA_DIR / "equity_stress.json"),
        ("benchmark_equity_ledger_sha256", DATA_DIR / "equity_spy_benchmark.json"),
        ("acwi_benchmark_equity_ledger_sha256", DATA_DIR / "equity_acwi_benchmark.json"),
        ("dataset_sha256", DATA_DIR / "historical_dataset_001.json"),
    ]
    for key, path in pairs:
        raw = path.read_bytes()
        assert b"\r" not in raw, f"CR byte: {path.name}"
        assert hashlib.sha256(raw).hexdigest() == r[key], f"mismatch: {key}"
    for eq_file in ("equity_baseline.json", "equity_stress.json"):
        for row in _load(DATA_DIR / eq_file)["rows"]:
            assert float(row["cash"]) >= 0.0
            assert float(row["market_value"]) <= float(row["total_equity"])


def test_locks_intact() -> None:
    r = _load(RESULT)
    assert r["recent_stress_access_count"] == 0
    assert r["quarantine_access_count"] == 0
    assert r["prospective_access_count"] == 0
    assert r["hyp_007_empirical_read_count"] == 0
    assert r["paper_authorized"] is False
    assert r["live_authorized"] is False
    assert r["capital_authority_usd"] == "0.00"
    assert r["no_real_orders"] is True
