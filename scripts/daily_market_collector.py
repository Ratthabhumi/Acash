"""Daily market-data collector entry point (research only; never places an order).

Runs one bounded, idempotent collection pass over the held US universe:

    python scripts/daily_market_collector.py            # incremental: only what is still missing
    python scripts/daily_market_collector.py --backfill # same code, wider requested window

The pass is safe to run twice. A symbol that is already complete for the requested window is skipped
from the session index, so a timer firing twice does not duplicate a partition. If the provider is
rate-limited the pass pauses and retries instead of silently truncating; if the provider denies access
the pass stops at once. Writes are atomic, and a partition is committed only after a symbol's request
completed. Storage of raw bars additionally requires established retention rights; without them the
run still proves coverage but says so (``storage_rights: UNESTABLISHED``) and stores dates only.

Exit codes: 0 = pass completed (with or without work), 2 = no credential, 3 = access denied.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.dashboard_api.private_input import RateLimiter  # noqa: E402
from acash.invest import market_authority as ma  # noqa: E402
from acash.market_data import collector as co  # noqa: E402
from acash.market_data import providers as mp  # noqa: E402
from acash.market_data import warehouse as wh  # noqa: E402

PRIVATE = Path(os.environ["ACASH_PRIVATE_DIR"]) if os.environ.get("ACASH_PRIVATE_DIR") else ROOT / "data" / "private"
WAREHOUSE = PRIVATE / "market_warehouse"
NON_US = {"SCBSET50", "MTS-GOLD"}
NEW_YORK = ZoneInfo("America/New_York")


def held_symbols() -> List[str]:
    path = PRIVATE / "snapshot.json"
    if not path.is_file():
        return []
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    return sorted({str(sec["security_id"]) for sec in snapshot.get("securities", [])
                   if sec.get("figi") and str(sec["security_id"]) not in NON_US})


def main() -> int:
    parser = argparse.ArgumentParser(description="ACASH daily market-data collector (research only).")
    parser.add_argument("--end", default=None,
                        help="explicit session date; defaults to the latest completed eligible session")
    parser.add_argument("--backfill", action="store_true", help="request the full Basic window, not just new sessions")
    parser.add_argument("--start", default=None)
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--max-requests", type=int, default=40)
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--force", action="store_true", help="collect even when the venue is closed")
    parser.add_argument("--per-ticker", action="store_true",
                        help="use per-symbol historical bars instead of one Grouped Daily request per session")
    parser.add_argument("--catch-up", action="store_true",
                        help="after the incremental pass, refetch symbols that have middle gaps")
    parser.add_argument("--max-gap-symbols", type=int, default=5)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    eligible = co.latest_completed_session()
    end = date.fromisoformat(args.end) if args.end else date.fromisoformat(eligible["session_date"])
    if args.end and end > date.fromisoformat(eligible["session_date"]):
        print(json.dumps({"status": "SESSION_NOT_YET_ELIGIBLE", "requested": end.isoformat(),
                          "latest_eligible": eligible["session_date"],
                          "eligible_at_ict": eligible["eligible_at_ict"],
                          "detail": "EOD data for a session is not requested before its close and publication."},
                         indent=2, sort_keys=True))
        return 0
    if not args.force:
        from acash.invest import market_calendar as mc
        calendar = mc.load_calendar()
        venue_day = end
        info = mc.session(calendar, venue_day)
        if info["status"] not in ("OPEN", "EARLY_CLOSE"):
            print(json.dumps({"status": "NO_SESSION", "date": venue_day.isoformat(),
                              "reason": info["status"], "mic": calendar.mic,
                              "detail": "The venue calendar has no session today; no provider request was made."},
                             indent=2, sort_keys=True))
            return 0
    start = (date.fromisoformat(args.start) if args.start
             else end - timedelta(days=730 if args.backfill else 10))
    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else held_symbols()
    if not symbols:
        print(json.dumps({"status": "NO_UNIVERSE", "detail": "no held US security with a verified identity"}))
        return 0
    job_id = args.job_id or f"DAILY_{end.isoformat()}"
    store = wh.BarWarehouse(WAREHOUSE, record=ROOT / ma.RECORD)
    credential: Optional[ma.Credential] = ma.default_credential_store().lookup("MASSIVE_BASIC")
    if credential is None:
        print(json.dumps({"status": "CREDENTIAL_MISSING", "provider_id": "MASSIVE_BASIC"}))
        return 2
    provider = mp.MassiveEODMarketDataProvider(credential, mp.urllib_transport,
                                               RateLimiter(5, time.monotonic, 60).allow,
                                               lambda: datetime.now(timezone.utc), skipped=[])
    grouped: Dict[str, Any] | None = None
    if not args.per_ticker and not args.symbols:
        sessions = co.grouped_sessions(store, symbols, start, end)[-max(1, args.max_requests):]
        grouped = co.collect_grouped(provider, store, symbols, sessions, job_id=job_id,
                                     max_requests=args.max_requests, pause=time.sleep)
        report = co.CollectionReport(job_id=job_id, provider_id="MASSIVE_BASIC", start=start, end=end,
                                     requests=grouped["requests"], persisted=True,
                                     storage_rights="PERMITTED")
        report.completed = list(symbols) if grouped["rows_added"] else []
        report.failed = sorted(grouped["errors"])
    else:
        report = co.collect(provider, store, symbols, start, end, job_id=job_id,
                            max_requests=args.max_requests, pause=time.sleep)
    catch_up: Dict[str, Any] = {"requested": [], "report": None}
    if args.catch_up:
        missing = co.gaps(store, symbols)
        repair = [s for s in missing["symbols_with_gaps"] if s not in report.failed][:args.max_gap_symbols]
        if repair:
            catch_up["requested"] = repair
            second = co.collect(provider, store, repair, start, end, job_id=f"{job_id}_CATCHUP",
                                max_requests=min(args.max_requests, len(repair) + 2), pause=time.sleep,
                                force_full=True)
            catch_up["report"] = {"completed": second.completed, "failed": second.failed,
                                  "requests": second.requests, "stopped": second.stopped}
    health = co.write_health(store, symbols, WAREHOUSE / "health.json",
                             generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             job_id=job_id, range={"start": start.isoformat(), "end": end.isoformat()},
                             requests=report.requests, completed=len(report.completed),
                             failed=len(report.failed), stopped=report.stopped,
                             storage_rights=report.storage_rights)
    summary: Dict[str, Any] = {
        "status": "STOPPED" if report.stopped else ("NO_WORK" if not report.completed else "COLLECTED"),
        "job_id": job_id, "range": health["range"], "requests": report.requests,
        "completed": len(report.completed), "failed": len(report.failed),
        "skipped_existing": len(report.skipped_existing), "stopped": report.stopped,
        "storage_rights": report.storage_rights,
        "covered": health["coverage"]["covered"], "partial": health["coverage"]["partial"],
        "missing": health["coverage"]["missing"], "union_sessions": health["coverage"]["union_sessions"],
    }
    if not args.quiet:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if report.stopped != "ACCESS_DENIED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
