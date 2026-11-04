"""Dated broker-displayed position observations (evidence, never a transaction or a valuation rewrite).

A broker screenshot is evidence of what the app showed at a moment, not an exchange record and not a
new holding. Each capture is therefore stored as its own dated observation:

* the existing snapshot is never modified, so its ``observed_at`` and valuation date stay truthful;
* no quantity, trade or cash field exists here, so an observation can never create a transaction;
* a sub-portfolio share (for example "17.21% of Newwave") is stored as *displayed metadata* and is never
  used as a global weight — a global weight is computed from qualified values against the portfolio
  total, in Python, on one matching valuation date;
* missing rows are recorded as absent, never as zero, so a sub-portfolio whose fifth asset was not
  visible does not silently sum to 100%.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_BROKER_POSITION_OBSERVATIONS_V1"
DEFAULT_PATH = Path("data/private/broker_position_observations.json")
EVIDENCE_STATUS = "BROKER_DISPLAYED_OBSERVATION"
ROW_FIELDS = {"security_id", "displayed_value", "displayed_currency", "displayed_subportfolio_weight",
              "displayed_price", "note"}


def _decimal(what: str, value: Any, *, positive: bool = False) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DataContractError(f"BROKER_OBSERVATION_INVALID: {what}.") from None
    if not number.is_finite() or (positive and number <= 0):
        raise DataContractError(f"BROKER_OBSERVATION_INVALID: {what}.")
    return number


def _aware(observed_at: str) -> datetime:
    try:
        moment = datetime.fromisoformat(observed_at)
    except ValueError:
        raise DataContractError("BROKER_OBSERVATION_INVALID: observed_at.") from None
    if moment.tzinfo is None:
        raise DataContractError("BROKER_OBSERVATION_INVALID: observed_at must be timezone-aware.")
    return moment


def empty(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or DEFAULT_PATH
    if not p.is_file():
        return {"schema": SCHEMA, "data_class": "OWNER_PRIVATE_OBSERVATION", "observations": []}
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise DataContractError("BROKER_OBSERVATION_SCHEMA_MISMATCH.")
    return doc


def record(doc: Dict[str, Any], *, observation_id: str, broker: str, observed_at: str, currency: str,
           subportfolio: Optional[str], rows: Sequence[Mapping[str, Any]], source: str,
           note: Optional[str] = None) -> Dict[str, Any]:
    """Append one capture. Idempotent by ``observation_id``; a different date is a new capture."""
    if not observation_id.strip() or not broker.strip():
        raise DataContractError("BROKER_OBSERVATION_INVALID: identity.")
    moment = _aware(observed_at)
    if not rows:
        raise DataContractError("BROKER_OBSERVATION_INVALID: no rows.")
    data: Dict[str, Any] = {**doc, "observations": list(doc.get("observations") or [])}
    existing = data["observations"]
    if any(o.get("observation_id") == observation_id for o in existing):
        raise DataContractError(f"BROKER_OBSERVATION_DUPLICATE: {observation_id}.")
    seen: List[str] = []
    clean: List[Dict[str, Any]] = []
    for row in rows:
        extra = set(row) - ROW_FIELDS
        if extra:
            raise DataContractError(f"BROKER_OBSERVATION_INVALID: unexpected field(s) {sorted(extra)}.")
        symbol = str(row.get("security_id") or "").strip().upper()
        if not symbol or symbol in seen:
            raise DataContractError(f"BROKER_OBSERVATION_INVALID: security_id {symbol or '(empty)'}.")
        seen.append(symbol)
        value = _decimal("displayed_value", row.get("displayed_value"), positive=True)
        weight = row.get("displayed_subportfolio_weight")
        clean.append({
            "security_id": symbol, "displayed_value": format(value, "f"),
            "displayed_currency": str(row.get("displayed_currency") or currency),
            "displayed_subportfolio_weight": (format(_decimal("weight", weight), "f")
                                              if weight is not None else None),
            "displayed_price": (format(_decimal("price", row["displayed_price"]), "f")
                                if row.get("displayed_price") is not None else None),
            "note": row.get("note"),
        })
    priced = sum((Decimal(r["displayed_value"]) for r in clean), Decimal(0))
    entry = {
        "observation_id": observation_id, "broker": broker, "observed_at": moment.isoformat(),
        "currency": currency, "subportfolio": subportfolio, "rows": clean,
        "displayed_subportfolio_total": format(priced, "f"),
        "subportfolio_rows_complete": False,
        "source": source, "evidence_status": EVIDENCE_STATUS,
        "is_transaction": False, "creates_position": False,
        "note": note or ("Broker-displayed values at one moment. Rows shown may be fewer than the "
                         "sub-portfolio holds, so the displayed weights may not sum to 1."),
    }
    existing.append(entry)
    existing.sort(key=lambda o: str(o.get("observed_at")))
    data["schema"] = SCHEMA
    data["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    return data


def write(doc: Mapping[str, Any], path: Optional[Path] = None) -> Path:
    target = path or DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    handle, temporary = tempfile.mkstemp(dir=str(target.parent), prefix=target.name, suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return target


def subportfolio_weights(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Decimal]:
    """Weights implied by the *displayed values* of one capture (never a global weight)."""
    values = {str(r["security_id"]): Decimal(str(r["displayed_value"])) for r in rows}
    total = sum(values.values(), Decimal(0))
    if total <= 0:
        raise DataContractError("BROKER_OBSERVATION_INVALID: sub-portfolio total.")
    return {symbol: value / total for symbol, value in values.items()}


def global_weight(displayed_value: Decimal, portfolio_total: Decimal) -> Decimal:
    """A global weight needs one matching valuation date and the portfolio total on that date."""
    if displayed_value <= 0 or portfolio_total <= 0:
        raise DataContractError("BROKER_OBSERVATION_INVALID: weight inputs.")
    return displayed_value / portfolio_total
