"""Offline shadow-research entrypoint (no provider calls, no orders).

    uv run python scripts/shadow_eval.py --register
    uv run python scripts/shadow_eval.py --evaluate
    uv run python scripts/shadow_eval.py --observe
    uv run python scripts/shadow_eval.py --report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.invest import research_panel as rpanel  # noqa: E402
from acash.invest import security_identity as si  # noqa: E402
from acash.invest import shadow  # noqa: E402
from acash.market_data import warehouse as wh  # noqa: E402

PRIVATE = Path(os.environ["ACASH_PRIVATE_DIR"]) if os.environ.get("ACASH_PRIVATE_DIR") else ROOT / "data" / "private"
PROTOCOL = PRIVATE / "shadow" / "protocol_v1.json"
JOURNAL = PRIVATE / "shadow" / "journal.json"
NEW_US = {"SCBSET50", "MTS-GOLD"}


def _universe(store: wh.BarWarehouse, registry: List[Any]) -> Dict[str, Any]:
    snapshot = json.loads((PRIVATE / "snapshot.json").read_text(encoding="utf-8"))
    held = sorted({str(s["security_id"]) for s in snapshot["securities"]
                   if s.get("figi") and str(s["security_id"]) not in NEW_US})
    symbols = [s for s in held if store.partition(s).is_file()]
    closes = {s: {d: bar.close for d, bar in store.read(s).items()} for s in symbols}
    weights = rpanel.weights_from_view(PRIVATE / "out" / "upi_view.json", symbols)
    return {"symbols": symbols, "closes": closes, "weights": weights}


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward-only shadow research (read-only).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--register", action="store_true")
    group.add_argument("--evaluate", action="store_true")
    group.add_argument("--observe", action="store_true")
    group.add_argument("--report", action="store_true")
    group.add_argument("--session", default=None)
    args = parser.parse_args()

    store = wh.BarWarehouse()
    if args.report:
        print(json.dumps(shadow.report(JOURNAL), indent=2, sort_keys=True))
        return 0
    if args.register:
        protocol = {
            "protocol_id": "ACASH_SHADOW_V1", "version": 1,
            "registered_at": datetime.now(timezone.utc).date().isoformat(),
            "universe": {"cohort": "ESTABLISHED_HISTORY", "identity_gate": "security_identity_registry",
                         "excluded_identities": ["SPCX"]},
            "strategies": ["CASH", "BUY_AND_HOLD", "EQUAL_WEIGHT"], "benchmark": "EQUAL_WEIGHT",
            "available_data_cutoff": "2026-11-04", "cost_assumptions": "UNKNOWN",
            "fx_basis": "REFERENCE_FX_NOT_EXECUTABLE", "horizon": "OPEN_ENDED",
            "frequency": "DAILY_AFTER_EOD", "trial_count": 3,
            "risk_constraints": "EXISTING_PORTFOLIO_CONSTRAINTS",
            "eligibility_gates": ["storage_rights_permitted", "identity_single", "panel_ready"],
            "no_execution_authority": shadow.NO_EXECUTION,
        }
        doc = shadow.register_protocol(protocol, PROTOCOL)
        print(json.dumps({"status": "REGISTERED", "sha256": doc["sha256"], "path": str(PROTOCOL)}, indent=2))
        return 0
    protocol_doc = shadow.load_protocol(PROTOCOL)
    data = _universe(store, si.load_registry(ROOT / si.DEFAULT_REGISTRY))
    latest = max((d for series in data["closes"].values() for d in series), default=None)
    if args.observe:
        added = shadow.observe_outcomes(JOURNAL, data["closes"], data["symbols"])
        print(json.dumps({"status": "OBSERVED", "outcomes_added": len(added)}, indent=2))
        return 0
    session = date.fromisoformat(args.session) if args.session else latest
    try:
        entry = shadow.evaluate_session(protocol_doc, data["closes"], data["weights"], data["symbols"],
                                        session, JOURNAL)
    except Exception as error:  # evidence, not a crash: report the exact refusal
        print(json.dumps({"status": type(error).__name__, "code": str(error)[:200]}, indent=2))
        return 2
    print(json.dumps({"status": entry.get("status"), "signal_id": entry.get("signal_id"),
                      "strategy": entry.get("strategy_id"), "session": entry.get("session_date")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
