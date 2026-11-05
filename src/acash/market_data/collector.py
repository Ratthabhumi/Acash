"""Incremental / backfill daily-bar collection with checkpoint, resume and provider isolation.

The collector does not know how a provider authenticates or limits itself: it asks the adapter for a
bounded range and lets the adapter's limiter refuse work it cannot do. A refusal is a *pause and
retry*, never a silent truncation. Each symbol is independent, so one failing ticker cannot abort the
run, and only a symbol whose request completed is marked done in the checkpoint.

Persistence goes through :class:`acash.market_data.warehouse.BarWarehouse`, which refuses to store
bars whose provider has no established retention rights. Collection therefore still returns a real
coverage result in that case; it just does not claim a durable dataset.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.market_data.warehouse import BarWarehouse, coverage, retention_terms, storage_permitted

#: Adapters refuse a call they cannot afford by returning nothing and naming the symbol in ``skipped``.
RATE_LIMIT_PAUSE_SECONDS = 61.0


class DailyBarSource(Protocol):
    skipped: List[str]
    provider_id: str

    def historical_daily(self, symbols: Sequence[str], start: date, end: date) -> List[Dict[str, Any]]: ...


@dataclass
class CollectionReport:
    job_id: str
    provider_id: str
    start: date
    end: date
    requests: int = 0
    provider_calls: int = 0
    persisted: bool = False
    storage_rights: str = "UNESTABLISHED"
    symbols: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    completed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    skipped_existing: List[str] = field(default_factory=list)
    paused_seconds: float = 0.0
    stopped: Optional[str] = None
    #: In-memory observations from this run only; never serialised into a report or a file.
    bars: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict, repr=False)

    def as_dict(self) -> Dict[str, Any]:
        return {"job_id": self.job_id, "provider_id": self.provider_id,
                "range": {"start": self.start.isoformat(), "end": self.end.isoformat()},
                "requests": self.requests, "provider_calls": self.provider_calls, "persisted": self.persisted,
                "storage_rights": self.storage_rights, "symbols": self.symbols,
                "completed": self.completed, "failed": self.failed,
                "skipped_existing": self.skipped_existing,
                "paused_seconds": round(self.paused_seconds, 3), "stopped": self.stopped}


def plan(warehouse: BarWarehouse, symbols: Sequence[str], start: date, end: date,
         durable: bool = False) -> Dict[str, Any]:
    """What still has to be fetched. ``durable`` resumes from stored partitions, not from the index.

    The session index only proves that a range was *seen*; if the bars were not persisted (or were
    purged), the next persistent pass must fetch the full range again rather than assume it is done.
    """
    index = warehouse.session_index()
    rows = index.get("symbols", {}) if isinstance(index.get("symbols"), dict) else {}
    plan_rows: Dict[str, Any] = {}
    for symbol in symbols:
        entry = rows.get(symbol) or {}
        if durable:
            stored = warehouse.read(symbol)
            last = max(stored).isoformat() if stored else None
        else:
            last = entry.get("last")
        if not last:
            plan_rows[symbol] = {"status": "NEEDS_FULL_RANGE", "from": start.isoformat(), "to": end.isoformat()}
            continue
        resume_at = date.fromisoformat(str(last)) + timedelta(days=1)
        if resume_at > end:
            plan_rows[symbol] = {"status": "COMPLETE", "last": last}
        else:
            plan_rows[symbol] = {"status": "NEEDS_INCREMENT", "from": resume_at.isoformat(),
                                 "to": end.isoformat()}
    return {"job": {"start": start.isoformat(), "end": end.isoformat(), "durable": durable},
            "symbols": plan_rows,
            "needs_work": sorted(s for s, row in plan_rows.items() if row["status"] != "COMPLETE")}


def _classify(error: DataContractError) -> str:
    text = str(error)
    if text.startswith("PROVIDER_ACCESS_DENIED"):
        return "ACCESS_DENIED"
    if text.startswith("PROVIDER_RATE_LIMITED"):
        return "RATE_LIMITED"
    if "HTTP 404" in text:
        return "NOT_FOUND"
    if text.startswith("PROVIDER_UNAVAILABLE"):
        return "PROVIDER_UNAVAILABLE"
    if text.startswith("PROVIDER_RESPONSE_INVALID"):
        return "RESPONSE_INVALID"
    if text.startswith("STORAGE_RIGHTS_UNESTABLISHED"):
        return "STORAGE_RIGHTS_UNESTABLISHED"
    return "CONTRACT_ERROR"


def collect(source: DailyBarSource, warehouse: BarWarehouse, symbols: Sequence[str], start: date, end: date,
            *, job_id: str, persist: Optional[bool] = None, max_requests: int = 60,
            pause: Callable[[float], None] = time.sleep,
            pause_seconds: float = RATE_LIMIT_PAUSE_SECONDS, rate_limit_retries: int = 2,
            force_full: bool = False) -> CollectionReport:
    """Collect ``symbols`` for ``[start, end]``, resuming only the work that is still missing.

    ``persist=None`` follows the storage-rights gate; ``True`` demands persistence and therefore fails
    closed if the gate does not permit it. ``max_requests`` is a hard budget: the run stops cleanly and
    the checkpoint keeps what already succeeded, so the next run continues.
    """
    if start > end:
        raise DataContractError("COLLECTOR_RANGE_INVALID: start must be on or before end.")
    provider_id = getattr(source, "provider_id", "UNKNOWN")
    permitted = storage_permitted(provider_id, warehouse.record)
    report = CollectionReport(job_id=job_id, provider_id=provider_id, start=start, end=end,
                              storage_rights="PERMITTED" if permitted else "UNESTABLISHED")
    if persist is True and not permitted:
        raise DataContractError(f"STORAGE_RIGHTS_UNESTABLISHED: {provider_id}.")
    report.persisted = bool(permitted and persist is not False)
    previous = warehouse.load_state(job_id)
    done = set(previous.get("completed", [])) if isinstance(previous.get("completed"), list) else set()
    if report.persisted:
        done = set()  # a durable pass resumes from partitions, never from a checkpoint alone
    roadmap = plan(warehouse, symbols, start, end, durable=report.persisted)["symbols"]
    if force_full:
        # Catch-up after downtime: a middle gap cannot be reached by resuming from the last session, so
        # the requested symbols are asked for again over the full window.
        roadmap = {symbol: {"status": "NEEDS_FULL_RANGE", "from": start.isoformat(), "to": end.isoformat()}
                   for symbol in symbols}
    for symbol in symbols:
        step = roadmap[symbol]
        if step["status"] == "COMPLETE" or symbol in done:
            report.skipped_existing.append(symbol)
            report.symbols[symbol] = {"status": "ALREADY_COMPLETE", "last": step.get("last")}
            continue
        first = date.fromisoformat(step["from"])
        attempt, refused, bars = 0, 0, []
        while True:
            if report.requests >= max_requests:
                report.stopped = "REQUEST_BUDGET_EXHAUSTED"
                break
            report.requests += 1
            source.skipped.clear() if hasattr(source.skipped, "clear") else setattr(source, "skipped", [])
            try:
                bars = source.historical_daily([symbol], first, end)
            except DataContractError as error:
                kind = _classify(error)
                if kind != "RATE_LIMITED":
                    report.provider_calls += 1
                report.symbols[symbol] = {"status": kind, "error": str(error)[:300], "from": first.isoformat()}
                if kind == "ACCESS_DENIED":
                    report.stopped = "ACCESS_DENIED"
                elif kind != "RATE_LIMITED":
                    report.failed.append(symbol)
                if kind == "ACCESS_DENIED":
                    break
                refused += 1
                attempt += 1
                if kind != "RATE_LIMITED" or attempt > rate_limit_retries:
                    break
                pause(pause_seconds)
                report.paused_seconds += pause_seconds
                continue
            if symbol in getattr(source, "skipped", []):
                attempt += 1
                if attempt > rate_limit_retries:
                    report.symbols[symbol] = {"status": "RATE_LIMITED", "from": first.isoformat()}
                    report.failed.append(symbol)
                    break
                pause(pause_seconds)
                report.paused_seconds += pause_seconds
                continue
            report.provider_calls += 1
            break
        if report.stopped == "ACCESS_DENIED":
            report.failed.append(symbol)
            break
        if report.stopped == "REQUEST_BUDGET_EXHAUSTED":
            report.symbols.setdefault(symbol, {"status": "DEFERRED", "reason": report.stopped})
            report.failed.append(symbol)
            break
        if not bars:
            if symbol not in report.symbols:
                report.symbols[symbol] = {"status": "NO_SESSIONS", "from": first.isoformat()}
                report.failed.append(symbol)
            continue
        sessions = sorted({bar["session_date"] if isinstance(bar["session_date"], date)
                           else date.fromisoformat(str(bar["session_date"])) for bar in bars})
        added = 0
        if report.persisted:
            try:
                result = warehouse.commit(symbol, bars, job_id=job_id, source=provider_id,
                                          requested_start=first, requested_end=end)
                added = int(result["added"])
            except DataContractError as error:
                report.symbols[symbol] = {"status": _classify(error), "error": str(error)[:300]}
                report.failed.append(symbol)
                continue
        else:
            warehouse.record_sessions(symbol, sessions, source=provider_id, job_id=job_id)
        report.completed.append(symbol)
        report.bars[symbol] = list(bars)
        report.symbols[symbol] = {"status": "COLLECTED", "sessions": len(sessions), "added": added,
                                 "first": sessions[0].isoformat(), "last": sessions[-1].isoformat(),
                                 "refused_calls": refused}
        done.add(symbol)
        warehouse.save_state(job_id, {"completed": sorted(done), "requests": report.requests,
                                      "range": {"start": start.isoformat(), "end": end.isoformat()},
                                      "provider_id": provider_id, "persisted": report.persisted,
                                      "completed_at": None})
    warehouse.save_state(job_id, {"completed": sorted(done), "requests": report.requests,
                                  "range": {"start": start.isoformat(), "end": end.isoformat()},
                                  "provider_id": provider_id, "persisted": report.persisted,
                                  "stopped": report.stopped, "failed": sorted(set(report.failed))})
    return report


def gaps(warehouse: BarWarehouse, symbols: Sequence[str]) -> Dict[str, Any]:
    """Sessions a symbol is missing relative to the union of every indexed session."""
    index = warehouse.session_index()
    matrix = coverage(index, symbols)
    rows = index.get("symbols", {}) if isinstance(index.get("symbols"), dict) else {}
    union = sorted({value for symbol in symbols for value in (rows.get(symbol, {}) or {}).get("dates", [])})
    detail: Dict[str, Any] = {}
    for symbol in symbols:
        dates = set((rows.get(symbol) or {}).get("dates") or [])
        missing = [day for day in union if day not in dates]
        if missing:
            detail[symbol] = {"missing": len(missing), "first_missing": missing[0],
                              "last_missing": missing[-1], "dates": missing[:50]}
    return {"symbols_with_gaps": sorted(detail), "detail": detail, "union_sessions": len(union)}


def latest_completed_session(now: datetime | None = None) -> Dict[str, Any]:
    """The newest session whose EOD data is *entitled* on the Massive Basic plan.

    Basic publishes a session's daily bars only after midnight America/New_York on the following
    calendar day, so a session is eligible only when the current ET date is strictly after it. Weekends,
    holidays and early closes are handled by the venue calendar; nothing is inferred.
    """
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo
    from acash.invest import market_calendar as mc
    moment = now or _dt.now(timezone.utc)
    calendar = mc.load_calendar()
    today_et = moment.astimezone(ZoneInfo(calendar.timezone)).date()
    day = today_et - timedelta(days=1)
    for _ in range(14):
        info = mc.session(calendar, day)
        if info["status"] in ("OPEN", "EARLY_CLOSE") and day < today_et:
            midnight_et = _dt.combine(today_et, datetime.min.time(), tzinfo=ZoneInfo(calendar.timezone))
            return {"session_date": day.isoformat(), "session_status": info["status"],
                    "eligible_at_utc": midnight_et.astimezone(timezone.utc).isoformat(),
                    "eligible_at_ict": midnight_et.astimezone(ZoneInfo("Asia/Bangkok")).isoformat(),
                    "rule": "SESSION_STRICTLY_BEFORE_CURRENT_ET_DATE"}
        day = day - timedelta(days=1)
    raise DataContractError("COLLECTOR_NO_ELIGIBLE_SESSION: calendar coverage is too short.")


def next_run(now: datetime | None = None) -> Dict[str, Any]:
    """The next scheduled EOD pass, derived from the venue calendar and 18:30 America/New_York."""
    from datetime import datetime as _dt, time as _time, timedelta as _td
    from zoneinfo import ZoneInfo
    from acash.invest import market_calendar as mc
    moment = now or _dt.now(timezone.utc)
    calendar = mc.load_calendar()
    new_york = ZoneInfo("America/New_York")
    day = moment.astimezone(new_york).date()
    for _ in range(10):
        info = mc.session(calendar, day)
        candidate = moment.astimezone(new_york).replace(hour=1, minute=0, second=0, microsecond=0)
        candidate = candidate.replace(year=day.year, month=day.month, day=day.day)
        if (info["status"] in ("OPEN", "EARLY_CLOSE") and day.weekday() in (1, 2, 3, 4, 5)
                and candidate > moment):
            return {"next_run_et": candidate.isoformat(), "session_date": day.isoformat(),
                    "session_status": info["status"],
                    "next_run_ict": candidate.astimezone(ZoneInfo("Asia/Bangkok")).isoformat()}
        day = day + _td(days=1)
    return {"next_run_et": None, "session_date": None, "session_status": "NOT_VERIFIED_WITHIN_CALENDAR"}


def health(warehouse: BarWarehouse, symbols: Sequence[str]) -> Dict[str, Any]:
    """Collector health from stored evidence only; a timer firing is not ingestion."""
    index = warehouse.session_index()
    state = warehouse.state()
    matrix = coverage(index, symbols)
    jobs = state.get("jobs", {}) if isinstance(state.get("jobs"), dict) else {}
    latest: Mapping[str, Any] = max(jobs.values(), key=lambda job: str(job.get("range", {}).get("end", "")),
                                        default={})
    return {
        "schema": "ACASH_COLLECTOR_HEALTH_V1",
        "coverage": matrix,
        "last_job": {k: latest.get(k) for k in ("completed", "failed", "requests", "range", "stopped",
                                                "persisted", "provider_id")} if latest else None,
        "partitions_present": sum(1 for symbol in symbols if warehouse.partition(symbol).is_file()),
        "retention": retention_terms("MASSIVE_BASIC", warehouse.record),
        "missing_sessions": gaps(warehouse, symbols),
        "next_run": next_run(),
        "storage_bytes": _storage_bytes(warehouse.root),
        "rate_limit": "5 requests/minute (MASSIVE_BASIC)",
        "storage_rights": "PERMITTED" if storage_permitted("MASSIVE_BASIC", warehouse.record)
        else "UNESTABLISHED",
        "note": "Session index holds dates only; prices are stored only where retention rights are established.",
    }


def _storage_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def write_health(warehouse: BarWarehouse, symbols: Sequence[str], path: Path, **extra: Any) -> Dict[str, Any]:
    """Persist the collector health record used by the dashboard (metadata only, no prices)."""
    doc = health(warehouse, symbols)
    doc.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def grouped_sessions(warehouse: BarWarehouse, symbols: Sequence[str], start: date,
                     end: date) -> List[date]:
    """Eligible venue sessions in ``[start, end]`` that are still missing for at least one symbol."""
    from acash.invest import market_calendar as mc
    calendar = mc.load_calendar()
    day = start
    sessions: List[date] = []
    while day <= end:
        if mc.session(calendar, day)["status"] in ("OPEN", "EARLY_CLOSE"):
            sessions.append(day)
        day = day + timedelta(days=1)
    stored = {symbol: set(warehouse.read(symbol)) for symbol in symbols}
    return [day for day in sessions if any(day not in stored[symbol] for symbol in symbols)]


def collect_grouped(source: Any, warehouse: BarWarehouse, symbols: Sequence[str], sessions: Sequence[date],
                    *, job_id: str, max_requests: int = 10,
                    pause: Callable[[float], None] = time.sleep,
                    pause_seconds: float = RATE_LIMIT_PAUSE_SECONDS) -> Dict[str, Any]:
    """One Grouped Daily request per missing session; only held symbols are written.

    The full-market payload never leaves this function. A session that fails is left missing and
    reported, so the next run retries it instead of pretending the day is complete.
    """
    provider_id = getattr(source, "provider_id", "MASSIVE_BASIC")
    if not storage_permitted(provider_id, warehouse.record):
        raise DataContractError(f"STORAGE_RIGHTS_UNESTABLISHED: {provider_id}.")
    by_symbol: Dict[str, List[Dict[str, Any]]] = {symbol: [] for symbol in symbols}
    collected: List[str] = []
    requests = 0
    errors: Dict[str, str] = {}
    for day in sessions:
        if requests >= max_requests:
            errors[day.isoformat()] = "REQUEST_BUDGET_EXHAUSTED"
            break
        for attempt in range(2):
            if requests >= max_requests:
                errors[day.isoformat()] = "REQUEST_BUDGET_EXHAUSTED"
                break
            requests += 1  # Conservative attempts, including rejected HTTP calls.
            try:
                rows = source.grouped_daily(day, symbols)
            except DataContractError as error:
                message = str(error)
                if message.startswith("PROVIDER_RATE_LIMITED") and attempt == 0:
                    pause(pause_seconds)
                    continue
                errors[day.isoformat()] = message.split(":")[0]
                break
            for row in rows:
               by_symbol[row["symbol"]].append(row)
            collected.append(day.isoformat())
            break
    added = 0
    for symbol, rows in by_symbol.items():
        if not rows:
            continue
        result = warehouse.commit(symbol, rows, job_id=job_id, source=provider_id,
                                  requested_start=min(sessions), requested_end=max(sessions))
        added += int(result["added"])
    missing_after = grouped_sessions(warehouse, symbols, min(sessions), max(sessions)) if sessions else []
    return {"job_id": job_id, "provider_id": provider_id, "requests": requests, "sessions": collected,
            "sessions_requested": len(sessions), "rows_added": added,
            "errors": errors, "missing_after": [d.isoformat() for d in missing_after],
            "persisted": True}
