"""Forward-only shadow research: frozen protocol, point-in-time inputs, append-only journal.

Not paper trading. No order, broker position or capital authority exists here.

Every data boundary is gated: the frozen universe and its exclusions are enforced, input series are
truncated at the decision cutoff, the identity registry is applied, outcomes use the *recorded strategy
weights* (never an equal-weight basket), and the journal is published atomically under a single-writer
lock with a durable backup. Historical research is never mixed into this track record.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.invest import research_panel as rpanel
from acash.invest import research_proposal as rp
from acash.invest import security_identity as si

PROTOCOL_SCHEMA = "ACASH_SHADOW_PROTOCOL_V1"
JOURNAL_SCHEMA = "ACASH_SHADOW_JOURNAL_V1"
REQUIRED = ("protocol_id", "universe", "strategies", "benchmark", "registered_at", "cost_assumptions",
            "horizon", "no_execution_authority")
NO_EXECUTION = "NONE_RESEARCH_OBSERVATION_ONLY"


def _canonical(doc: Mapping[str, Any]) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def protocol_hash(protocol: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(protocol)).hexdigest()


def register_protocol(protocol: Mapping[str, Any], path: Path) -> Dict[str, Any]:
    missing = [field for field in REQUIRED if field not in protocol]
    if missing:
        raise DataContractError(f"SHADOW_PROTOCOL_INCOMPLETE: {missing}.")
    if protocol.get("no_execution_authority") != NO_EXECUTION:
        raise DataContractError("SHADOW_PROTOCOL_AUTHORITY_INVALID: research observation only.")
    if not protocol.get("universe", {}).get("symbols"):
        raise DataContractError("SHADOW_PROTOCOL_UNIVERSE_UNFROZEN: an explicit symbol list is required.")
    digest = protocol_hash(protocol)
    doc = {"schema": PROTOCOL_SCHEMA, "sha256": digest, "protocol": dict(protocol)}
    if path.is_file():
        existing: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("protocol", {}).get("protocol_id") != protocol["protocol_id"]:
            raise DataContractError("SHADOW_PROTOCOL_PATH_COLLISION: different protocol id at this path.")
        if existing.get("sha256") != digest:
            raise DataContractError("SHADOW_PROTOCOL_IMMUTABLE: a changed specification needs a new version.")
        return existing
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return doc


def load_protocol(path: Path) -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != PROTOCOL_SCHEMA:
        raise DataContractError("SHADOW_PROTOCOL_SCHEMA_MISMATCH.")
    if protocol_hash(doc["protocol"]) != doc.get("sha256"):
        raise DataContractError("SHADOW_PROTOCOL_HASH_MISMATCH: the file was edited after freezing.")
    return doc


def _journal(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"schema": JOURNAL_SCHEMA, "signals": [], "outcomes": []}
    doc: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != JOURNAL_SCHEMA:
        raise DataContractError("SHADOW_JOURNAL_SCHEMA_MISMATCH.")
    return doc


def _atomic_write(path: Path, doc: Mapping[str, Any]) -> None:
    """Atomic publication with a durable backup of the previous valid generation."""
    payload = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_bytes(path.read_bytes())
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class _Lock:
    """Single-writer lock; a second process fails closed instead of interleaving writes."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> "_Lock":
        try:
            self.handle = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise DataContractError("SHADOW_JOURNAL_LOCKED: another evaluation is running.") from None
        return self

    def __exit__(self, *_: Any) -> None:
        os.close(self.handle)
        self.path.unlink(missing_ok=True)


def eligible_from(protocol: Mapping[str, Any]) -> date:
    return date.fromisoformat(str(protocol["registered_at"])[:10])


def _truncate(closes: Mapping[str, Mapping[date, Decimal]], cutoff: date) -> Dict[str, Dict[date, Decimal]]:
    return {symbol: {day: value for day, value in series.items() if day <= cutoff}
            for symbol, series in closes.items()}


def _frozen_universe(protocol: Mapping[str, Any], closes: Mapping[str, Mapping[date, Decimal]],
                     symbols: Sequence[str]) -> List[str]:
    universe = protocol.get("universe") or {}
    frozen = list(universe.get("symbols") or [])
    excluded = set(universe.get("excluded_identities") or [])
    if not frozen:
        raise DataContractError("SHADOW_PROTOCOL_UNIVERSE_UNFROZEN.")
    if set(frozen) != set(symbols) - excluded:
        raise DataContractError("SHADOW_UNIVERSE_MISMATCH: symbols differ from the frozen protocol.")
    missing = [symbol for symbol in frozen if symbol not in closes]
    if missing:
        raise DataContractError(f"SHADOW_UNIVERSE_INCOMPLETE: {sorted(missing)[:5]}.")
    return frozen


def evaluate_session(protocol_doc: Mapping[str, Any], closes: Mapping[str, Mapping[date, Decimal]],
                     weights: Mapping[str, Decimal], symbols: Sequence[str], session: date,
                     journal_path: Path, *, registry: Optional[Sequence[Any]] = None,
                     min_sessions: int = rpanel.MIN_SESSIONS) -> Dict[str, Any]:
    """Evaluate with data available at ``session`` only and record the decision once."""
    protocol = protocol_doc["protocol"]
    if session <= eligible_from(protocol):
        raise DataContractError("SHADOW_NOT_PROSPECTIVE: the first record must follow registration.")
    universe = _frozen_universe(protocol, closes, symbols)
    journal = _journal(journal_path)
    key = (protocol_doc["sha256"], session.isoformat())
    for signal in journal["signals"]:
        if (signal.get("protocol_sha256"), signal.get("session_date")) == key:
            return {"status": "ALREADY_RECORDED", "signal_id": signal.get("signal_id")}

    cut_closes = _truncate({s: closes[s] for s in universe}, session)
    cut_weights = {s: weights[s] for s in universe if s in weights}
    if len(cut_weights) != len(universe):
        raise DataContractError("SHADOW_WEIGHTS_INCOMPLETE: every frozen constituent needs a qualified weight.")
    for symbol in universe:
        if session not in cut_closes[symbol]:
            raise DataContractError(f"SHADOW_SESSION_MISSING: {symbol} has no bar on {session.isoformat()}.")
    panel = rpanel.build_panel(cut_closes, cut_weights, universe, min_sessions=min_sessions,
                               registry=registry)
    entry: Dict[str, Any] = {
        "signal_id": f"{protocol['protocol_id']}:{session.isoformat()}",
        "protocol_id": protocol["protocol_id"], "protocol_sha256": protocol_doc["sha256"],
        "session_date": session.isoformat(),
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision_cutoff": session.isoformat(), "execution_authority": "NONE",
        "kind": "FORWARD_SHADOW_OBSERVATION", "universe_size": len(universe),
        "cash_return": "0", "fees": "UNKNOWN", "fx_basis": "UNREFERENCED_PRICE_RETURN",
    }
    if panel.get("status") == "PANEL_READY" and set(panel.get("eligible") or []) != set(universe):
        # Never silently renormalise away a frozen constituent.
        entry.update({"status": "BLOCKED", "reason": "CONSTITUENT_NOT_QUALIFIED",
                      "detail": sorted(set(universe) - set(panel.get("eligible") or []))})
        with _Lock(journal_path.with_suffix(".lock")):
            journal["signals"].append(entry)
            _atomic_write(journal_path, journal)
        return entry
    if panel.get("status") != "PANEL_READY":
        entry.update({"status": "BLOCKED", "reason": "INSUFFICIENT_EVIDENCE",
                      "detail": panel.get("missing_evidence") or panel.get("excluded")})
        with _Lock(journal_path.with_suffix(".lock")):
            journal["signals"].append(entry)
            _atomic_write(journal_path, journal)
        return entry
    inputs = panel.pop("inputs")
    proposal = rp.build_proposal(inputs)
    entry.update({
        "status": "OBSERVED",
        "strategy_id": proposal.get("strategy_id"),
        "target_weights": proposal.get("target_weights"),
        "cash_weight": proposal.get("cash_weight"),
        "benchmark": protocol.get("benchmark"),
        "input_sha256": hashlib.sha256(_canonical(
            {s: [str(v) for v in inputs.returns[s]] for s in sorted(inputs.returns)})).hexdigest(),
        "panel_sessions": panel.get("aligned_sessions"),
        "price_basis": "PRICE_RETURN_ONLY",
        "performance_basis": "FORWARD_SHADOW_OBSERVATION",
        "not_a_trade": True,
    })
    with _Lock(journal_path.with_suffix(".lock")):
        current = _journal(journal_path)
        if any(s.get("signal_id") == entry["signal_id"] for s in current["signals"]):
            return {"status": "ALREADY_RECORDED", "signal_id": entry["signal_id"]}
        current["signals"].append(entry)
        _atomic_write(journal_path, current)
    return entry


def observe_outcomes(journal_path: Path, closes: Mapping[str, Mapping[date, Decimal]],
                     symbols: Sequence[str]) -> List[Dict[str, Any]]:
    """Append the realized move of the *recorded strategy weights* plus an independent benchmark."""
    journal = _journal(journal_path)
    added: List[Dict[str, Any]] = []
    with _Lock(journal_path.with_suffix(".lock")):
        current = _journal(journal_path)
        recorded = {(o.get("signal_id"), o.get("through_session")) for o in current["outcomes"]}
        for signal in current["signals"]:
            if signal.get("status") != "OBSERVED":
                continue
            start = date.fromisoformat(str(signal["session_date"]))
            weights = {k: Decimal(str(v)) for k, v in (signal.get("target_weights") or {}).items()}
            if not weights:
                continue
            constituent = sorted(weights)
            if any(s not in closes for s in constituent):
                continue
            later = sorted(day for day in set.intersection(*(set(closes[s]) for s in constituent)) if day > start)
            if not later:
                continue
            through = later[-1]
            if (signal["signal_id"], through.isoformat()) in recorded:
                continue
            base = max(day for day in closes[constituent[0]] if day <= start)
            if any(base not in closes[s] or through not in closes[s] for s in constituent):
                continue
            strategy_return = Decimal(0)
            for symbol in constituent:
                weight = weights[symbol]
                strategy_return += weight * (closes[symbol][through] / closes[symbol][base] - 1)
            benchmark_weights = {s: Decimal(1) / Decimal(len(constituent)) for s in constituent}
            benchmark_return = sum(((closes[s][through] / closes[s][base] - 1) * benchmark_weights[s]
                                    for s in constituent), Decimal(0))
            outcome = {"signal_id": signal["signal_id"], "from_session": base.isoformat(),
                       "through_session": through.isoformat(), "constituents": len(constituent),
                       "strategy_return": format(strategy_return, "f"),
                       "benchmark": "EQUAL_WEIGHT", "benchmark_return": format(benchmark_return, "f"),
                       "basis": "PRICE_RETURN_ONLY", "fees": "UNKNOWN",
                       "kind": "FORWARD_SHADOW_OUTCOME",
                       "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            current["outcomes"].append(outcome)
            added.append(outcome)
        if added:
            _atomic_write(journal_path, current)
    return added


def report(journal_path: Path) -> Dict[str, Any]:
    journal = _journal(journal_path)
    signals = journal["signals"]
    outcomes = journal["outcomes"]
    observed = [s for s in signals if s.get("status") == "OBSERVED"]
    return {
        "schema": "ACASH_SHADOW_REPORT_V1",
        "signals": len(signals), "observed": len(observed),
        "blocked": len([s for s in signals if s.get("status") == "BLOCKED"]),
        "outcomes": len(outcomes),
        "earliest_signal": min((s["session_date"] for s in signals), default=None),
        "latest_outcome": max((o["through_session"] for o in outcomes), default=None),
        "forward_observations": len(outcomes),
        "performance_basis": "FORWARD_SHADOW_OBSERVATION",
        "execution_authority": "NONE",
        "statistical_validation": ("STATISTICAL_VALIDATION_NOT_ESTABLISHED" if len(outcomes) < 30
                                   else "INSUFFICIENT_SAMPLE_FOR_CANONICAL_DSR"),
        "note": "Historical retrospective research is never merged with these forward observations.",
    }
