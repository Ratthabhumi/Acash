"""Conditional bulk review of OpenFIGI candidates (identity only, never prices).

A single API hit is a candidate, not an identity. This module runs deterministic checks over the
already-retrieved candidate evidence and lets the Owner confirm — in one explicit action — only the
rows that pass every mandatory check. Ambiguous or contradictory rows stay out of the bulk action.

Checks (all must pass for AUTO_VALIDATED_CANDIDATE):
1. exactly one candidate;
2. FIGI matches ``BBG`` + 9 alphanumerics;
3. the candidate ticker equals the requested ticker (case-insensitive);
4. a venue code is present;
5. an instrument type is present;
6. the FIGI is unique across the whole batch;
7. the stored result status is ``SINGLE_CANDIDATE``.

Anything else is REVIEW_REQUIRED, or BLOCKED_CONFLICT when a check contradicts the evidence.
Confirmation writes atomically, records a revision and a timestamp, and never changes quantities,
prices, FX, cash or cost basis.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_SECURITY_IDENTITIES_V1"
FIGI = re.compile(r"^BBG[A-Z0-9]{9}$")
AUTO = "AUTO_VALIDATED_CANDIDATE"
REVIEW = "REVIEW_REQUIRED"
BLOCKED = "BLOCKED_CONFLICT"
CONFIRMED = "OWNER_CONFIRMED"


def _revision(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_batch(path: Path) -> Dict[str, Any]:
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or not isinstance(doc.get("rows"), list):
        raise DataContractError("IDENTITY_BATCH_INVALID.")
    return {"doc": doc, "revision": _revision(raw)}


def validate_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    figi_seen: Dict[str, str] = {}
    out: List[Dict[str, Any]] = []
    for row in rows:
        ticker = str(row.get("ticker") or "")
        candidates = row.get("candidates") or []
        reasons: List[str] = []
        status = AUTO
        if row.get("status") != "SINGLE_CANDIDATE" or len(candidates) != 1:
            status = REVIEW
            reasons.append("NOT_A_SINGLE_CANDIDATE")
        candidate = candidates[0] if len(candidates) == 1 else None
        if candidate is None:
            reasons.append("NO_CANDIDATE_PAYLOAD")
        else:
            figi = str(candidate.get("figi") or "")
            if not FIGI.match(figi):
                status, reasons = BLOCKED, reasons + ["FIGI_FORMAT_INVALID"]
            if str(candidate.get("ticker") or "").upper() != ticker.upper():
                status, reasons = BLOCKED, reasons + ["TICKER_MISMATCH"]
            if not str(candidate.get("exch_code") or "").strip():
                if status == AUTO:
                    status = REVIEW
                reasons.append("VENUE_MISSING")
            if not str(candidate.get("security_type") or "").strip():
                if status == AUTO:
                    status = REVIEW
                reasons.append("INSTRUMENT_TYPE_MISSING")
            if figi:
                if figi in figi_seen and figi_seen[figi] != ticker:
                    status, reasons = BLOCKED, reasons + ["DUPLICATE_FIGI"]
                figi_seen.setdefault(figi, ticker)
        out.append({**row, "validation": status, "reasons": reasons,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return out


def counts(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    tally: Dict[str, int] = {AUTO: 0, REVIEW: 0, BLOCKED: 0, CONFIRMED: 0}
    for row in rows:
        key = row.get("validation", REVIEW)
        tally[key] = tally.get(key, 0) + 1
    return tally


def confirm_bulk(path: Path, expected_revision: str, *, confirm: bool) -> Dict[str, Any]:
    """Confirm only AUTO_VALIDATED rows, and only against the exact revision the Owner reviewed."""
    loaded = load_batch(path)
    if loaded["revision"] != expected_revision:
        raise DataContractError("IDENTITY_REVIEW_REVISION_CONFLICT.")
    if not confirm:
        raise DataContractError("IDENTITY_CONFIRMATION_REQUIRED.")
    rows = validate_rows(loaded["doc"]["rows"])
    eligible = [r for r in rows if r["validation"] == AUTO]
    if not eligible:
        return {"status": "NOTHING_TO_CONFIRM", "confirmed": 0}
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    confirmed_ids = set()
    merged: List[Dict[str, Any]] = []
    for row in rows:
        if row["validation"] == AUTO:
            merged.append({**row, "owner_confirmation": CONFIRMED, "confirmed_at": stamp})
            confirmed_ids.add(row["ticker"])
        else:
            merged.append(row)
    doc = {**loaded["doc"], "rows": merged,
           "confirmation_revision": {"confirmed_at": stamp, "confirmed_by": "OWNER",
                                     "previous_revision": expected_revision,
                                     "confirmed_tickers": sorted(confirmed_ids),
                                     "excluded": [r["ticker"] for r in rows if r["validation"] != AUTO]}}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return {"status": "CONFIRMED", "confirmed": len(confirmed_ids),
            "excluded": [r["ticker"] for r in rows if r["validation"] != AUTO],
            "revision": _revision(path.read_bytes())}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Local review summary; ``--apply`` confirms the validated set only."""
    import sys

    path = Path("data/private/security_identities.json")
    args = list(sys.argv[1:] if argv is None else argv)
    if not path.is_file():
        print("NO_CANDIDATES")
        return 2
    loaded = load_batch(path)
    rows = validate_rows(loaded["doc"]["rows"])
    print("revision=" + loaded["revision"])
    print("counts=" + json.dumps(counts(rows), sort_keys=True))
    for row in rows:
        if row["validation"] != AUTO:
            print(f"review {row['ticker']}: {row['validation']} {row['reasons']}")
    if "--apply" in args:
        result = confirm_bulk(path, loaded["revision"], confirm=True)
        print("apply=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
