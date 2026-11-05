"""Forward-only shadow research: a frozen protocol and an append-only observation journal.

This is not paper trading. No order, broker position or capital authority exists here. A protocol is
frozen once (content hash), a signal is recorded only for a session strictly after registration, and an
outcome is appended only after the market has actually moved beyond that session. Historical research and
forward observations are never merged into one track record.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.invest import research_panel as rpanel
from acash.invest import research_proposal as rp

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
    """Freeze a protocol. Re-registering the same id with different content is refused."""
    missing = [field for field in REQUIRED if field not in protocol]
    if missing:
        raise DataContractError(f"SHADOW_PROTOCOL_INCOMPLETE: {missing}.")
    if protocol.get("no_execution_authority") != NO_EXECUTION:
        raise DataContractError("SHADOW_PROTOCOL_AUTHORITY_INVALID: research observation only.")
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


def _write(path: Path, doc: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def eligible_from(protocol: Mapping[str, Any]) -> date:
    return date.fromisoformat(str(protocol["registered_at"])[:10])


def evaluate_session(protocol_doc: Mapping[str, Any], closes: Mapping[str, Mapping[date, Decimal]],
                     weights: Mapping[str, Decimal], symbols: Sequence[str], session: date,
                     journal_path: Path, min_sessions: int = rpanel.MIN_SESSIONS) -> Dict[str, Any]:
    """Evaluate the frozen protocol with data up to ``session`` only; never retroactively."""
    protocol = protocol_doc["protocol"]
    if session <= eligible_from(protocol):
        raise DataContractError("SHADOW_NOT_PROSPECTIVE: the first record must follow registration.")
    journal = _journal(journal_path)
    key = (protocol_doc["sha256"], session.isoformat())
    for signal in journal["signals"]:
        if (signal.get("protocol_sha256"), signal.get("session_date")) == key:
            return {"status": "ALREADY_RECORDED", "signal_id": signal.get("signal_id")}
    panel = rpanel.build_panel(closes, weights, symbols, min_sessions=min_sessions)
    entry: Dict[str, Any] = {
        "signal_id": f"{protocol['protocol_id']}:{session.isoformat()}",
        "protocol_id": protocol["protocol_id"], "protocol_sha256": protocol_doc["sha256"],
        "session_date": session.isoformat(), "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision_cutoff": session.isoformat(), "execution_authority": "NONE",
        "kind": "FORWARD_SHADOW_OBSERVATION",
    }
    if panel.get("status") != "PANEL_READY":
        entry.update({"status": "BLOCKED", "reason": "INSUFFICIENT_EVIDENCE",
                      "detail": panel.get("missing_evidence") or panel.get("excluded")})
        journal["signals"].append(entry)
        _write(journal_path, journal)
        return entry
    inputs = panel.pop("inputs")
    proposal = rp.build_proposal(inputs)
    entry.update({
        "status": "OBSERVED",
        "strategy_id": proposal.get("strategy_id"),
        "target_weights": proposal.get("target_weights"),
        "input_sha256": hashlib.sha256(_canonical(
            {s: [str(v) for v in inputs.returns[s]] for s in sorted(inputs.returns)})).hexdigest(),
        "panel_sessions": panel.get("aligned_sessions"),
        "price_basis": "PRICE_RETURN_ONLY",
        "performance_basis": "FORWARD_SHADOW_OBSERVATION",
        "not_a_trade": True,
    })
    journal["signals"].append(entry)
    _write(journal_path, journal)
    return entry


def observe_outcomes(journal_path: Path, closes: Mapping[str, Mapping[date, Decimal]],
                     symbols: Sequence[str]) -> List[Dict[str, Any]]:
    """Append the realized equal-weight market move after each recorded signal, once."""
    journal = _journal(journal_path)
    recorded = {(o.get("signal_id"), o.get("through_session")) for o in journal["outcomes"]}
    added: List[Dict[str, Any]] = []
    for signal in journal["signals"]:
        if signal.get("status") != "OBSERVED":
            continue
        start = date.fromisoformat(str(signal["session_date"]))
        later = sorted(day for day in set.intersection(*(set(closes[s]) for s in symbols)) if day > start)
        if not later:
            continue
        through = later[-1]
        if (signal["signal_id"], through.isoformat()) in recorded:
            continue
        start_index = {s: closes[s] for s in symbols}
        base = sorted(day for day in start_index[symbols[0]] if day <= start)
        if not base:
            continue
        returns = []
        for symbol in symbols:
            series = start_index[symbol]
            if base[-1] not in series or through not in series:
                continue
            returns.append(series[through] / series[base[-1]] - 1)
        if not returns:
            continue
        equal_weight = sum(returns, Decimal(0)) / Decimal(len(returns))
        outcome = {"signal_id": signal["signal_id"], "from_session": base[-1].isoformat(),
                   "through_session": through.isoformat(), "instrument_returns": len(returns),
                   "equal_weight_price_return": format(equal_weight, "f"),
                   "basis": "PRICE_RETURN_ONLY", "kind": "FORWARD_SHADOW_OUTCOME",
                   "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        journal["outcomes"].append(outcome)
        added.append(outcome)
    if added:
        _write(journal_path, journal)
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
