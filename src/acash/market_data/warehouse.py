"""Source-aware daily-bar warehouse for research panels.

The warehouse is deliberately split from the providers: a provider returns observations, and the
warehouse decides whether those observations may be *written to disk at all*.  A provider whose ODR
scope has not established caching/retention rights cannot persist raw bars, however convenient that
would be; the caller receives ``STORAGE_RIGHTS_UNESTABLISHED`` and must keep the observations in
memory for that run.  Session *dates* (a calendar fact, no prices) may still be indexed so the
collector can detect missing sessions without retaining market data.

Writes are atomic (temporary file + ``os.replace``) and idempotent: re-committing the same sessions
is a no-op, a conflicting duplicate is refused rather than overwritten, and only a complete symbol is
recorded as done.  Nothing here fabricates a session: a missing date is reported by absence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.invest import market_authority as ma

SCHEMA = "ACASH_MARKET_WAREHOUSE_V1"
DEFAULT_ROOT = Path("data/private/market_warehouse")
BAR_FIELDS = ("open", "high", "low", "close", "volume")
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9]{0,9}(\.[A-Z])?$")
PARQUET_SCHEMA = pa.schema([
    ("symbol", pa.string()), ("session_date", pa.date32()),
    ("open", pa.string()), ("high", pa.string()), ("low", pa.string()),
    ("close", pa.string()), ("volume", pa.string()), ("adjusted", pa.bool_()),
    ("provider", pa.string()), ("retrieved_at", pa.string()),
])


@dataclass(frozen=True)
class Bar:
    symbol: str
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    adjusted: bool
    provider: str
    retrieved_at: str

    def key(self) -> Tuple[str, date]:
        return (self.symbol, self.session_date)


def _decimal(what: str, value: Any) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DataContractError(f"WAREHOUSE_BAR_INVALID: {what}.") from None
    if not number.is_finite():
        raise DataContractError(f"WAREHOUSE_BAR_INVALID: {what}.")
    return number


def parse_bar(row: Mapping[str, Any]) -> Bar:
    """Validate one provider row. Missing or non-positive prices are refused, never zero-filled."""
    symbol = str(row.get("symbol") or "")
    if not _SYMBOL.match(symbol):
        raise DataContractError("WAREHOUSE_BAR_INVALID: symbol.")
    raw_session = row.get("session_date")
    session = raw_session if isinstance(raw_session, date) else None
    if session is None:
        try:
            session = date.fromisoformat(str(raw_session))
        except ValueError:
            raise DataContractError("WAREHOUSE_BAR_INVALID: session_date.") from None
    prices = {name: _decimal(name, row.get(name)) for name in ("open", "high", "low", "close")}
    if any(value <= 0 for value in prices.values()):
        raise DataContractError("WAREHOUSE_BAR_INVALID: non-positive price.")
    if prices["high"] < max(prices["open"], prices["close"], prices["low"]):
        raise DataContractError("WAREHOUSE_BAR_INVALID: high below another price.")
    if prices["low"] > min(prices["open"], prices["close"]):
        raise DataContractError("WAREHOUSE_BAR_INVALID: low above open/close.")
    volume = _decimal("volume", row.get("volume", "0"))
    if volume < 0:
        raise DataContractError("WAREHOUSE_BAR_INVALID: volume.")
    return Bar(symbol, session, prices["open"], prices["high"], prices["low"], prices["close"],
               volume, bool(row.get("adjusted", False)), str(row.get("provider") or ""),
               str(row.get("retrieved_at") or ""))


def storage_permitted(provider_id: str, record: Optional[Path] = None) -> bool:
    """True only when the ODR-004 scope explicitly permits caching *and* has a verified retention policy.

    ``cache_permitted`` alone is not enough: retaining a market observation needs both the permission
    and a policy that describes how long it may stay. ``None``/missing is not permission.
    """
    state, entries = _odr_scope(record)
    if state != "RATIFIED":
        return False
    for entry in entries:
        if entry.get("provider_id") == provider_id:
            return entry.get("cache_permitted") is True and entry.get("retention_policy_verified") is True
    return False


def _odr_scope(record: Optional[Path]) -> Tuple[str, List[Mapping[str, Any]]]:
    path = record or Path(ma.RECORD)
    if not path.is_file():
        return "MISSING", []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "UNREADABLE", []
    scope = doc.get("scope_providers") if isinstance(doc, dict) else None
    state = doc.get("state") if isinstance(doc, dict) else None
    entries: List[Mapping[str, Any]] = [e for e in scope if isinstance(e, dict)] if isinstance(scope, list) else []
    return str(state or "UNKNOWN"), entries


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class BarWarehouse:
    """Partitioned daily bars plus a session index, manifest and resumable job state."""

    def __init__(self, root: Path = DEFAULT_ROOT, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 record: Optional[Path] = None) -> None:
        self.root = Path(root)
        self.clock = clock
        self.record = record

    # -- paths -------------------------------------------------------------------------------------
    def partition(self, symbol: str) -> Path:
        if not _SYMBOL.match(symbol):
            raise DataContractError("WAREHOUSE_SYMBOL_INVALID.")
        return self.root / "bars" / f"{symbol}.parquet"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    @property
    def index_path(self) -> Path:
        return self.root / "session_index.json"

    @property
    def state_path(self) -> Path:
        return self.root / "job_state.json"

    # -- reads -------------------------------------------------------------------------------------
    def read(self, symbol: str) -> Dict[date, Bar]:
        path = self.partition(symbol)
        if not path.is_file():
            return {}
        try:
            table = pq.read_table(path)
        except (OSError, pa.ArrowInvalid) as error:
            raise DataContractError(f"WAREHOUSE_PARTITION_UNREADABLE: {symbol} ({type(error).__name__}).") from None
        out: Dict[date, Bar] = {}
        for row in table.to_pylist():
            session = row["session_date"]
            if not isinstance(session, date):
                raise DataContractError(f"WAREHOUSE_PARTITION_UNREADABLE: {symbol} session.")
            bar = Bar(str(row["symbol"]), session, _decimal("open", row["open"]), _decimal("high", row["high"]),
                      _decimal("low", row["low"]), _decimal("close", row["close"]),
                      _decimal("volume", row["volume"]), bool(row["adjusted"]), str(row["provider"]),
                      str(row["retrieved_at"]))
            if bar.symbol != symbol:
                raise DataContractError(f"WAREHOUSE_PARTITION_UNREADABLE: {symbol} symbol mismatch.")
            out[session] = bar
        return dict(sorted(out.items()))

    def closes(self, symbols: Sequence[str]) -> Dict[str, Dict[date, Decimal]]:
        return {symbol: {s: bar.close for s, bar in self.read(symbol).items()} for symbol in symbols}

    def manifest(self) -> Dict[str, Any]:
        return _read_json(self.manifest_path) or {"schema": SCHEMA, "partitions": {}}

    def session_index(self) -> Dict[str, Any]:
        return _read_json(self.index_path) or {"schema": SCHEMA, "symbols": {}}

    def state(self) -> Dict[str, Any]:
        return _read_json(self.state_path) or {"schema": SCHEMA, "jobs": {}}

    # -- writes ------------------------------------------------------------------------------------
    def commit(self, symbol: str, rows: Iterable[Mapping[str, Any]], *, job_id: str,
               source: str = "MASSIVE_BASIC", requested_start: Optional[date] = None,
               requested_end: Optional[date] = None) -> Dict[str, Any]:
        """Merge validated bars into one partition. Refuses retention without established rights."""
        if not storage_permitted(source, self.record):
            raise DataContractError(f"STORAGE_RIGHTS_UNESTABLISHED: {source}.")
        incoming = [parse_bar(row) for row in rows]
        if not incoming:
            raise DataContractError("WAREHOUSE_COMMIT_EMPTY: no bars to commit.")
        if any(bar.symbol != symbol for bar in incoming):
            raise DataContractError("WAREHOUSE_COMMIT_SYMBOL_MISMATCH.")
        merged = self.read(symbol)
        before = dict(merged)
        for bar in incoming:
            existing = merged.get(bar.session_date)
            if existing is not None and existing.close != bar.close:
                raise DataContractError(f"WAREHOUSE_CONFLICTING_DUPLICATE: {symbol} {bar.session_date.isoformat()}.")
            merged[bar.session_date] = bar if existing is None else existing
        ordered = [merged[key] for key in sorted(merged)]
        changed = merged != before
        partition_sha = _partition_sha(self.partition(symbol))
        if changed:
            table = pa.Table.from_pylist([_bar_row(bar) for bar in ordered], schema=PARQUET_SCHEMA)
            sink = pa.BufferOutputStream()
            pq.write_table(table, sink, compression="snappy")
            data = sink.getvalue().to_pybytes()
            _atomic_write(self.partition(symbol), data)
            partition_sha = _sha256(data)
        manifest = self.manifest()
        partitions = manifest.setdefault("partitions", {})
        now = self.clock().isoformat(timespec="seconds")
        entry = partitions.get(symbol, {})
        entry.update({
            "symbol": symbol, "source": source, "adjustment_basis": "SPLIT_ADJUSTED_IF_PROVIDER" if any(
                bar.adjusted for bar in ordered) else "UNADJUSTED",
            "sessions": len(ordered), "first": ordered[0].session_date.isoformat(),
            "last": ordered[-1].session_date.isoformat(), "sha256": partition_sha,
            "rows_added": len(ordered) - len(before), "job_id": job_id, "updated_at": now,
            "requested": {"start": requested_start.isoformat() if requested_start else None,
                          "end": requested_end.isoformat() if requested_end else None},
            "storage_rights": "PERMITTED", "schema": SCHEMA,
        })
        partitions[symbol] = entry
        manifest.update({"schema": SCHEMA, "updated_at": now, "generated_by": "acash.market_data.warehouse"})
        _atomic_write(self.manifest_path, _json_bytes(manifest))
        self.record_sessions(symbol, [bar.session_date for bar in ordered], source=source, job_id=job_id)
        return {"symbol": symbol, "changed": changed, "sessions": len(ordered), "added": len(ordered) - len(before),
                "first": ordered[0].session_date.isoformat(), "last": ordered[-1].session_date.isoformat()}

    def record_sessions(self, symbol: str, sessions: Sequence[date], *, source: str, job_id: str,
                        error: Optional[str] = None) -> None:
        """Index *dates only* so missing-session detection works without retaining prices."""
        doc = self.session_index()
        symbols = doc.setdefault("symbols", {})
        ordered = sorted({s for s in sessions})
        entry: Dict[str, Any] = {"source": source, "job_id": job_id,
                                 "retrieved_at": self.clock().isoformat(timespec="seconds"),
                                 "sessions": len(ordered),
                                 "first": ordered[0].isoformat() if ordered else None,
                                 "last": ordered[-1].isoformat() if ordered else None,
                                 "dates": [s.isoformat() for s in ordered],
                                 "contains_prices": False}
        if error:
            entry["error"] = error
        previous = symbols.get(symbol)
        if previous and previous.get("dates") == entry["dates"] and not error:
            entry["retrieved_at"] = previous.get("retrieved_at", entry["retrieved_at"])
        symbols[symbol] = entry
        doc.update({"schema": SCHEMA, "contains_prices": False,
                    "updated_at": self.clock().isoformat(timespec="seconds")})
        _atomic_write(self.index_path, _json_bytes(doc))

    def save_state(self, job_id: str, state: Mapping[str, Any]) -> None:
        doc = self.state()
        doc.setdefault("jobs", {})[job_id] = dict(state)
        doc.update({"schema": SCHEMA, "updated_at": self.clock().isoformat(timespec="seconds")})
        _atomic_write(self.state_path, _json_bytes(doc))

    def load_state(self, job_id: str) -> Dict[str, Any]:
        job = self.state().get("jobs", {}).get(job_id)
        return dict(job) if isinstance(job, dict) else {}


def _bar_row(bar: Bar) -> Dict[str, Any]:
    return {"symbol": bar.symbol, "session_date": bar.session_date, "open": str(bar.open), "high": str(bar.high),
            "low": str(bar.low), "close": str(bar.close), "volume": str(bar.volume),
            "adjusted": bar.adjusted, "provider": bar.provider, "retrieved_at": bar.retrieved_at}


def _partition_sha(path: Path) -> Optional[str]:
    return _sha256(path.read_bytes()) if path.is_file() else None


def _json_bytes(doc: Mapping[str, Any]) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def coverage(index: Mapping[str, Any], symbols: Sequence[str]) -> Dict[str, Any]:
    """Per-symbol coverage plus gaps against the union of indexed sessions (no forward fill)."""
    rows = index.get("symbols", {}) if isinstance(index.get("symbols"), dict) else {}
    union = sorted({value for symbol in symbols for value in (rows.get(symbol, {}) or {}).get("dates", [])})
    per: Dict[str, Any] = {}
    for symbol in symbols:
        entry = rows.get(symbol) or {}
        dates = entry.get("dates") or []
        if not dates:
            per[symbol] = {"sessions": 0, "status": "MISSING", "error": entry.get("error")}
            continue
        missing = sorted(set(union) - set(dates))
        per[symbol] = {"sessions": len(dates), "first": dates[0], "last": dates[-1],
                       "missing_vs_union": len(missing), "missing_sample": missing[:5],
                       "status": "COVERED" if not missing else "PARTIAL", "error": entry.get("error")}
    return {"schema": SCHEMA, "union_sessions": len(union), "union_first": union[0] if union else None,
            "union_last": union[-1] if union else None, "symbols": per,
            "covered": sum(1 for v in per.values() if v["status"] == "COVERED"),
            "partial": sum(1 for v in per.values() if v["status"] == "PARTIAL"),
            "missing": sum(1 for v in per.values() if v["status"] == "MISSING"),
            "contains_prices": False}
