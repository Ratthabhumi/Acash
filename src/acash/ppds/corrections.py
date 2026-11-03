"""Append-only transaction corrections under ODR_UPI_OWNER_TRANSACTION_CORRECTIONS_006.

Methodology: APPEND_ONLY_SUPERSEDE_BY_ID. The original V1 journal stays byte-for-byte intact;
corrections live in a separate versioned envelope and the *effective* event set (what
``acash.ppds.transactions.replay`` replays) is resolved deterministically from original + corrections.

Correction kinds:
- VOID_ENTERED_EVENT: removes one recorded event from the effective set; the original row is kept
  as evidence and is never deleted or overwritten.
- SUPERSEDE_ENTERED_EVENT: removes one recorded event and substitutes a replacement row; both the
  original and the replacement remain as evidence.

Rejections: nonexistent target, correction cycle, conflicting supersession of the same target,
double application of one correction id, and correction of an already-voided event without an
explicit re-supersession chain. A correction is an amendment to evidence, never an executed trade,
so a mistaken BUY is never represented as a real SELL.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.ppds import transactions as txn

CORRECTION_SCHEMA = "ACASH_CANONICAL_TRANSACTIONS_V2_CORRECTION_ENVELOPE"
CORRECTION_DATA_CLASS = "OWNER_PRIVATE_OBSERVATION"
VOID_ENTERED_EVENT = "VOID_ENTERED_EVENT"
SUPERSEDE_ENTERED_EVENT = "SUPERSEDE_ENTERED_EVENT"
CORRECTION_KINDS = (VOID_ENTERED_EVENT, SUPERSEDE_ENTERED_EVENT)
CORRECTION_ID = re.compile(r"^COR_[A-Z]{8,28}$")
CORRECTIONS_FILE = "corrections.json"


@dataclass(frozen=True)
class Correction:
    correction_id: str
    kind: str
    target_id: str
    reason: str
    confirmed_by: str
    confirmed_at: datetime
    replacement: Optional[Dict[str, Any]] = None
    superseded_by: Optional[str] = None

    def key(self) -> Tuple[str, str]:
        return (self.kind, self.correction_id)


def _invalid(what: str) -> DataContractError:
    return DataContractError(f"CORRECTION_INVALID: {what}.")


def parse_correction(raw: Any, index: int) -> Correction:
    if not isinstance(raw, dict):
        raise _invalid(f"correction[{index}] is not an object.")
    cid = raw.get("correction_id")
    if not isinstance(cid, str) or not CORRECTION_ID.match(cid):
        raise _invalid(f"correction[{index}] correction_id must match COR_ plus 8-28 capitals.")
    kind = raw.get("kind")
    if kind not in CORRECTION_KINDS:
        raise _invalid(f"correction[{index}] kind must be {list(CORRECTION_KINDS)}.")
    target = raw.get("target_id")
    if not isinstance(target, str) or not target:
        raise _invalid(f"correction[{index}] target_id required.")
    reason = raw.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise _invalid(f"correction[{index}] reason required.")
    confirmed_by = raw.get("confirmed_by")
    if not isinstance(confirmed_by, str) or not confirmed_by:
        raise _invalid(f"correction[{index}] confirmed_by required.")
    confirmed_at = raw.get("confirmed_at")
    if not isinstance(confirmed_at, str):
        raise _invalid(f"correction[{index}] confirmed_at required.")
    try:
        moment = datetime.fromisoformat(confirmed_at)
    except ValueError:
        raise _invalid(f"correction[{index}] confirmed_at must be ISO-8601.") from None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    replacement: Optional[Dict[str, Any]] = None
    if kind == SUPERSEDE_ENTERED_EVENT:
        replacement = raw.get("replacement")
        if not isinstance(replacement, dict):
            raise _invalid(f"correction[{index}] SUPERSEDE requires replacement row.")
        txn.parse_transaction(replacement, index)  # must be a valid transaction row
    superseded_by = raw.get("superseded_by")
    if superseded_by is not None and (not isinstance(superseded_by, str) or not superseded_by):
        raise _invalid(f"correction[{index}] superseded_by must be a correction id.")
    return Correction(cid, kind, target, reason, confirmed_by, moment, replacement, superseded_by)


def load_envelope_from_doc(doc: Any) -> Dict[str, Any]:
    """Validate a correction envelope document and return its parsed corrections."""
    if not isinstance(doc, dict) or doc.get("schema") != CORRECTION_SCHEMA:
        raise _invalid("envelope schema.")
    corrections = doc.get("corrections")
    if not isinstance(corrections, list):
        raise _invalid("corrections must be a list.")
    return {"schema": CORRECTION_SCHEMA, "data_class": doc.get("data_class", CORRECTION_DATA_CLASS),
            "corrections": [parse_correction(c, i) for i, c in enumerate(corrections)]}


def load_envelope(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"schema": CORRECTION_SCHEMA, "data_class": CORRECTION_DATA_CLASS,
                "corrections": []}
    return load_envelope_from_doc(json.loads(path.read_text(encoding="utf-8")))


def _order(corrections: List[Correction]) -> List[Correction]:
    """Deterministic application order: earliest confirmation first, then correction id."""
    return sorted(corrections, key=lambda c: (c.confirmed_at, c.correction_id))


def resolve_effective(original_rows: List[Dict[str, Any]],
                      corrections: List[Correction]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Resolve the effective event set.

    Returns (effective_rows, audit) where audit records every accepted and rejected correction with
    its reason. Original rows are never modified: voided/superseded events simply drop out of the
    effective set, and replacements join it.
    """
    originals: Dict[str, Dict[str, Any]] = {}
    for row in original_rows:
        key = row.get("transaction_id") if isinstance(row, dict) else None
        if not isinstance(key, str) or not key:
            raise _invalid("every original event needs a transaction_id.")
        originals[key] = row
    effective: Dict[str, Dict[str, Any]] = copy.deepcopy(originals)
    voided: Dict[str, Correction] = {}          # target_id -> voiding correction
    superseded: Dict[str, Correction] = {}      # target_id -> superseding correction
    applied: Dict[str, Correction] = {}         # correction_id -> correction
    audit: List[Dict[str, Any]] = []

    def record(cid: str, status: str, reason: str, **extra: Any) -> None:
        entry = {"correction_id": cid, "status": status, "reason": reason, **extra}
        audit.append(entry)

    for c in _order(corrections):
        if c.correction_id in applied:
            record(c.correction_id, "REJECTED", "DOUBLE_APPLICATION", kind=c.kind, target_id=c.target_id)
            continue
        if c.target_id not in originals and c.target_id not in effective:
            record(c.correction_id, "REJECTED", "NONEEXISTENT_TARGET", kind=c.kind, target_id=c.target_id)
            continue
        if c.target_id in voided:
            record(c.correction_id, "REJECTED", "TARGET_ALREADY_VOIDED", kind=c.kind, target_id=c.target_id)
            continue
        if c.target_id in superseded:
            record(c.correction_id, "REJECTED", "CONFLICTING_SUPERSESSION", kind=c.kind,
                   target_id=c.target_id, already_by=superseded[c.target_id].correction_id)
            continue
        if c.superseded_by is not None and c.superseded_by in applied:
            record(c.correction_id, "REJECTED", "CORRECTION_CYCLE", kind=c.kind,
                   target_id=c.target_id, superseded_by=c.superseded_by)
            continue
        if c.kind == VOID_ENTERED_EVENT:
            voided[c.target_id] = c
            effective.pop(c.target_id, None)
            applied[c.correction_id] = c
            record(c.correction_id, "APPLIED", "VOIDED", kind=c.kind, target_id=c.target_id)
        else:
            repl = c.replacement
            if not isinstance(repl, dict):
                record(c.correction_id, "REJECTED", "REPLACEMENT_ROW_MISSING", kind=c.kind,
                       target_id=c.target_id)
                continue
            repl_id = repl.get("transaction_id")
            if not isinstance(repl_id, str) or not repl_id:
                record(c.correction_id, "REJECTED", "REPLACEMENT_ID_REQUIRED", kind=c.kind, target_id=c.target_id)
                continue
            if repl_id in effective and repl_id != c.target_id:
                record(c.correction_id, "REJECTED", "REPLACEMENT_ID_CONFLICT", kind=c.kind,
                       target_id=c.target_id, replacement_id=repl_id)
                continue
            effective.pop(c.target_id, None)
            effective[repl_id] = copy.deepcopy(repl)
            superseded[c.target_id] = c
            applied[c.correction_id] = c
            record(c.correction_id, "APPLIED", "SUPERSEDED", kind=c.kind, target_id=c.target_id,
                   replacement_id=repl_id)

    return list(effective.values()), audit


def correction_state(rows: List[Dict[str, Any]], path: Path) -> Dict[str, Any]:
    """Read-only projection: original count, effective count, and per-correction audit."""
    envelope = load_envelope(path)
    effective, audit = resolve_effective(rows, envelope["corrections"])
    return {"schema": CORRECTION_SCHEMA, "original_count": len(rows), "effective_count": len(effective),
            "corrections": [{"correction_id": c.correction_id, "kind": c.kind, "target_id": c.target_id,
                             "applied": c.correction_id in {a["correction_id"] for a in audit if a["status"] == "APPLIED"}}
                            for c in envelope["corrections"]], "audit": audit}
