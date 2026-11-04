"""Owner-run historical backfill of the held US universe into research evidence.

This is the *real* acquisition path: it reads the private snapshot for the held securities, asks the
Massive Basic adapter (5 requests/minute, bounded range, Bearer auth) for daily aggregates, and feeds
the resulting panel to the existing research-proposal engine. It never places an order, never writes a
price it did not receive, and never persists raw bars whose provider lacks established retention
rights: in that case only session dates (a calendar fact) and *derived* research output are written.

Usage (from the repository root):

    uv run python scripts/backfill_massive_universe.py --plan
    uv run python scripts/backfill_massive_universe.py --end 2026-11-04
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.dashboard_api.private_input import RateLimiter  # noqa: E402
from acash.invest import market_authority as ma  # noqa: E402
from acash.invest import research_proposal as rp  # noqa: E402
from acash.market_data import collector as co  # noqa: E402
from acash.market_data import providers as mp  # noqa: E402
from acash.market_data import warehouse as wh  # noqa: E402

PRIVATE = ROOT / "data" / "private"
WAREHOUSE = PRIVATE / "market_warehouse"
NON_US = {"SCBSET50", "MTS-GOLD"}
MIN_SESSIONS = 200


def held_symbols() -> List[str]:
    snapshot = json.loads((PRIVATE / "snapshot.json").read_text(encoding="utf-8"))
    out = [str(sec["security_id"]) for sec in snapshot["securities"]
           if sec.get("figi") and str(sec["security_id"]) not in NON_US]
    return sorted(set(out))


def panel_weights(symbols: List[str]) -> Dict[str, Decimal]:
    """Panel-relative weights from the snapshot's observed market values (never whole-portfolio NAV)."""
    snapshot = json.loads((PRIVATE / "snapshot.json").read_text(encoding="utf-8"))
    values: Dict[str, Decimal] = {}
    for account in snapshot["accounts"]:
        for position in account.get("positions") or []:
            symbol = str(position["security_id"])
            if symbol not in symbols:
                continue
            raw = position.get("observed_market_value")
            if raw is None or position.get("observed_market_value_currency") != "USD":
                continue
            values[symbol] = values.get(symbol, Decimal(0)) + Decimal(str(raw))
    total = sum(values.values(), Decimal(0))
    if total <= 0:
        return {}
    return {symbol: values[symbol] / total for symbol in symbols if symbol in values}


def build_panel(bars: Dict[str, List[Dict[str, Any]]], symbols: List[str]) -> Dict[str, Any]:
    closes: Dict[str, Dict[date, Decimal]] = {}
    for symbol in symbols:
        rows = bars.get(symbol) or []
        closes[symbol] = {date.fromisoformat(str(row["session_date"])): Decimal(str(row["close"])) for row in rows}
    eligible = [s for s in symbols if len(closes[s]) >= MIN_SESSIONS]
    excluded = {s: {"reason": "SESSION_COVERAGE_BELOW_MINIMUM", "sessions": len(closes[s])}
                for s in symbols if s not in eligible}
    if not eligible:
        return {"status": rp.INSUFFICIENT, "excluded": excluded, "eligible": []}
    common = sorted(set.intersection(*(set(closes[s]) for s in eligible)))
    if len(common) < 2:
        return {"status": rp.INSUFFICIENT, "excluded": excluded, "eligible": eligible,
                "missing_evidence": ["fewer than two aligned sessions across the eligible universe"]}
    weights = panel_weights(eligible)
    if not weights:
        return {"status": rp.INSUFFICIENT, "excluded": excluded, "eligible": eligible,
                "missing_evidence": ["no USD observed market value for the eligible universe"]}
    returns = {s: [(closes[s][common[i]] / closes[s][common[i - 1]]) - 1 for i in range(1, len(common))]
               for s in eligible}
    timestamps = [datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) for day in common[1:]]
    inputs = rp.ProposalInputs(returns=returns, timestamps=timestamps, current_weights=weights)
    return {"status": "PANEL_READY", "eligible": eligible, "excluded": excluded, "inputs": inputs,
            "aligned_sessions": len(common), "first": common[0].isoformat(), "last": common[-1].isoformat(),
            "weights": {s: format(w, "f") for s, w in weights.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Massive Basic backfill for the held US universe.")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--start", default=None, help="defaults to 730 days before --end (Basic window)")
    parser.add_argument("--symbols", default=None, help="comma-separated override")
    parser.add_argument("--max-requests", type=int, default=60)
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--plan", action="store_true", help="print the request plan and stop")
    parser.add_argument("--persist", action="store_true", help="demand durable storage (fails closed)")
    args = parser.parse_args()

    end = date.fromisoformat(args.end)
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=730)
    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else held_symbols()
    job_id = args.job_id or f"MASSIVE_BACKFILL_{end.isoformat()}"
    store = wh.BarWarehouse(WAREHOUSE, record=ROOT / ma.RECORD)

    if args.plan:
        print(json.dumps(co.plan(store, symbols, start, end), indent=2, sort_keys=True))
        return 0

    credential: Optional[ma.Credential] = ma.WindowsCredentialStore().lookup("MASSIVE_BASIC")
    if credential is None:
        print("MASSIVE_CREDENTIAL_MISSING: run SETUP-MARKET-DATA.bat first.", file=sys.stderr)
        return 2
    provider = mp.MassiveEODMarketDataProvider(credential, mp.urllib_transport,
                                               RateLimiter(5, time.monotonic, 60).allow,
                                               lambda: datetime.now(timezone.utc), skipped=[])
    report = co.collect(provider, store, symbols, start, end, job_id=job_id,
                        persist=True if args.persist else None, max_requests=args.max_requests,
                        pause=time.sleep)
    payload = report.as_dict()
    panel = build_panel(report.bars, symbols)
    proposal: Dict[str, Any] = {"status": rp.INSUFFICIENT}
    built: Optional[rp.ProposalInputs] = None
    if panel.get("status") == "PANEL_READY":
        built = panel.pop("inputs")
        proposal = rp.build_proposal(built)
    matrix = wh.coverage(store.session_index(), symbols)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "job": payload, "coverage": matrix,
        "panel": {k: v for k, v in panel.items() if k != "inputs"},
        "panel_inputs_sha256": hashlib.sha256(json.dumps(
            {s: [str(v) for v in built.returns[s]] for s in sorted(built.returns)}, sort_keys=True
        ).encode()).hexdigest() if built is not None else None,
        "proposal": proposal,
        "governance": {"execution_authority": "NONE", "real_capital_authority_usd": "0.00",
                       "no_real_orders": True, "retention": report.storage_rights,
                       "note": "Session dates are indexed; raw bars are stored only if retention rights are established."},
    }
    WAREHOUSE.mkdir(parents=True, exist_ok=True)
    (WAREHOUSE / "backfill_report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                    encoding="utf-8")
    co.write_health(store, symbols, WAREHOUSE / "health.json",
                    generated_at=result["generated_at"], job_id=job_id,
                    range={"start": start.isoformat(), "end": end.isoformat()}, requests=report.requests,
                    completed=len(report.completed), failed=len(report.failed), stopped=report.stopped,
                    storage_rights=report.storage_rights)
    summary = {
        "requests": payload["requests"], "provider_calls": payload["provider_calls"],
        "completed": len(report.completed), "failed": len(report.failed),
        "skipped_existing": len(report.skipped_existing), "stopped": report.stopped,
        "storage_rights": report.storage_rights,
        "coverage": {k: matrix[k] for k in ("union_sessions", "covered", "partial", "missing")},
        "panel": panel.get("status"), "aligned_sessions": panel.get("aligned_sessions"),
        "eligible": len(panel.get("eligible", [])), "excluded": panel.get("excluded"),
        "proposal_status": proposal.get("recommendation_status") or proposal.get("status"),
        "strategy": proposal.get("strategy_id"),
        "actions": len(proposal.get("proposed_actions", [])),
    }
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
