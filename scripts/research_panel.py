"""Rebuild the research panel from the stored warehouse — zero provider calls.

This is the offline path used after the weight source was corrected. It reads the 26 persisted Parquet
partitions and the authoritative position rows in the private view, then regenerates
``backfill_report.json`` so the Dashboard shows the corrected, fully weighted panel.

    uv run python scripts/research_panel.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.invest import research_panel as rpanel  # noqa: E402
from acash.invest import research_proposal as rp  # noqa: E402
from acash.market_data import collector as co  # noqa: E402
from acash.market_data import warehouse as wh  # noqa: E402

PRIVATE = Path(os.environ["ACASH_PRIVATE_DIR"]) if os.environ.get("ACASH_PRIVATE_DIR") else ROOT / "data" / "private"
WAREHOUSE = PRIVATE / "market_warehouse"
VIEW = PRIVATE / "out" / "upi_view.json"
NON_US = {"SCBSET50", "MTS-GOLD"}


def held_symbols() -> List[str]:
    snapshot = json.loads((PRIVATE / "snapshot.json").read_text(encoding="utf-8"))
    return sorted({str(sec["security_id"]) for sec in snapshot["securities"]
                   if sec.get("figi") and str(sec["security_id"]) not in NON_US})


def main() -> int:
    store = wh.BarWarehouse(WAREHOUSE)
    held = held_symbols()
    symbols = [s for s in held if store.partition(s).is_file()]
    if not symbols:
        print(json.dumps({"status": "NO_STORED_BARS"}))
        return 2
    closes = {symbol: {day: bar.close for day, bar in store.read(symbol).items()} for symbol in symbols}
    weights = rpanel.weights_from_view(VIEW, symbols)
    panel = rpanel.build_panel(closes, weights, symbols)
    cohorts = rpanel.build_cohorts(closes, weights, symbols)
    proposal: Dict[str, Any] = {"status": rp.INSUFFICIENT}
    inputs = None
    if panel.get("status") == "PANEL_READY":
        inputs = panel.pop("inputs")
        proposal = rp.build_proposal(inputs)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    coverage = wh.coverage(store.session_index(), symbols)
    report = {
        "generated_at": generated,
        "job": {"job_id": "OFFLINE_PANEL_REBUILD", "requests": 0, "provider_calls": 0,
                "storage_rights": "PERMITTED", "stopped": None,
                "symbols": {s: {"status": "ALREADY_STORED"} for s in symbols}},
        "coverage": coverage,
        "panel": {k: v for k, v in panel.items() if k != "inputs"},
        "panel_inputs_sha256": hashlib.sha256(json.dumps(
            {s: [str(v) for v in inputs.returns[s]] for s in sorted(inputs.returns)}, sort_keys=True
        ).encode()).hexdigest() if inputs is not None else None,
        "proposal": proposal,
        "labels": rpanel.real_vs_hypothetical(panel),
        "cohorts": cohorts,
        "cohort_summary": [
            {"cohort_id": c["cohort_id"], "status": c["status"],
             "evaluation_status": c["evaluation_status"],
             "comparable_to_established": c["comparable_to_established"],
             "session_count": c.get("session_count"),
             "evaluation_window": c.get("evaluation_window"),
             "strategy_id": (c.get("proposal") or {}).get("strategy_id"),
             "out_of_sample_periods": ((c.get("proposal") or {}).get("out_of_sample_period") or {}).get("periods"),
             "excluded": sorted(c.get("excluded") or {})}
            for c in cohorts["cohorts"]],
        "governance": {"execution_authority": "NONE", "real_capital_authority_usd": "0.00",
                       "no_real_orders": True, "retention": "PERMITTED",
                       "note": "Rebuilt offline from stored partitions; no provider was called."},
    }
    (WAREHOUSE / "backfill_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                                    encoding="utf-8")
    co.write_health(store, symbols, WAREHOUSE / "health.json", generated_at=generated,
                    job_id="OFFLINE_PANEL_REBUILD", requests=0, completed=0, failed=0, stopped=None,
                    storage_rights="PERMITTED")
    print(json.dumps({
        "status": panel.get("status"), "eligible": len(panel.get("eligible") or []),
        "excluded": panel.get("excluded"), "sessions": panel.get("aligned_sessions"),
        "range": [panel.get("first"), panel.get("last")],
        "weights_renormalised": panel.get("weights_renormalised_to_panel"),
        "strategy": proposal.get("strategy_id"),
        "proposal_status": proposal.get("recommendation_status") or proposal.get("status"),
        "provider_calls": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
