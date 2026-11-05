"""Point-in-time security identity, independent of ticker text.

A ticker is a label, not an identity. Nasdaq explicitly forbids linking the historical data of a reused
ticker to the new security, so a price series is only research-eligible when every stored session maps to
**one** canonical identity, and that identity is itself research-eligible.

The registry is a small, dated, source-cited file. It intentionally contains no private data: only
ticker validity intervals, canonical ids and why an interval is or is not eligible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_SECURITY_IDENTITY_REGISTRY_V1"
DEFAULT_REGISTRY = Path("docs/research/evidence/security_identity_registry.json")
ELIGIBLE = "VERIFIED_SINGLE_IDENTITY"
UNVERIFIED = "IDENTITY_UNVERIFIED"
MULTI = "MULTI_IDENTITY"
NO_ENTRY = "NO_REGISTRY_ENTRY"


@dataclass(frozen=True)
class Identity:
    canonical_id: str
    ticker: str
    valid_from: Optional[date]
    valid_to: Optional[date]
    instrument_type: str
    figi: Optional[str]
    cusip: Optional[str]
    isin: Optional[str]
    status: str
    research_eligible: bool
    inception_verified: bool
    lineage: str
    evidence: Tuple[str, ...]

    def covers(self, day: date) -> bool:
        if self.valid_from is None:
            return self.valid_to is None or day <= self.valid_to
        return self.valid_from <= day and (self.valid_to is None or day <= self.valid_to)

    @property
    def pit_qualified(self) -> bool:
        """Point-in-time qualification needs an identifier beyond the ticker text."""
        return bool(self.cusip or self.isin or self.figi)


def _day(value: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise DataContractError(f"IDENTITY_REGISTRY_INVALID: {what}.") from None


def parse_registry(doc: Mapping[str, Any]) -> List[Identity]:
    if doc.get("schema") != SCHEMA or not isinstance(doc.get("entries"), list):
        raise DataContractError("IDENTITY_REGISTRY_INVALID: envelope.")
    out: List[Identity] = []
    for row in doc["entries"]:
        if not isinstance(row, dict):
            raise DataContractError("IDENTITY_REGISTRY_INVALID: entry.")
        start = None if row.get("valid_from") in (None, "") else _day(row.get("valid_from"), "valid_from")
        end = None if row.get("valid_to") in (None, "") else _day(row.get("valid_to"), "valid_to")
        if end is not None and start is not None and end < start:
            raise DataContractError("IDENTITY_REGISTRY_INVALID: interval.")
        out.append(Identity(
            canonical_id=str(row.get("canonical_id") or ""), ticker=str(row.get("ticker") or "").upper(),
            valid_from=start, valid_to=end, instrument_type=str(row.get("instrument_type") or "UNKNOWN"),
            figi=(str(row["figi"]) if row.get("figi") else None),
            cusip=(str(row["cusip"]) if row.get("cusip") else None),
            isin=(str(row["isin"]) if row.get("isin") else None),
            status=str(row.get("status") or "UNKNOWN"),
            research_eligible=bool(row.get("research_eligible")),
            inception_verified=bool(row.get("inception_verified")),
            lineage=str(row.get("lineage") or ""),
            evidence=tuple(str(item) for item in (row.get("evidence") or []))))
    return out


def load_registry(path: Optional[Path] = None) -> List[Identity]:
    target = Path(path or DEFAULT_REGISTRY)
    if not target.is_file():
        return []
    return parse_registry(json.loads(target.read_text(encoding="utf-8")))


def _overlaps(entries: Sequence[Identity]) -> List[str]:
    problems: List[str] = []
    ordered = sorted(entries, key=lambda entry: entry.valid_from or date.min)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.valid_to is None or current.valid_from is None or previous.valid_to >= current.valid_from:
            problems.append(f"{previous.canonical_id} overlaps {current.canonical_id}")
    return problems


def series_identities(registry: Sequence[Identity], ticker: str, days: Sequence[date]) -> Dict[str, Any]:
    """Which canonical identities the stored sessions actually belong to."""
    entries = [entry for entry in registry if entry.ticker == ticker.upper()]
    if not entries:
        return {"ticker": ticker.upper(), "status": NO_ENTRY, "identities": [], "unmapped_days": 0,
                "overlaps": [], "evidence_needed": []}
    matched: Dict[str, Identity] = {}
    unmapped = 0
    for day in days:
        hit = [entry for entry in entries if entry.covers(day)]
        if not hit:
            unmapped += 1
            continue
        matched[hit[0].canonical_id] = hit[0]
    return {
        "ticker": ticker.upper(),
        "status": MULTI if len(matched) > 1 else "SINGLE_IDENTITY" if matched else "NO_MATCHED_DAYS",
        "identities": [{"canonical_id": entry.canonical_id, "status": entry.status,
                        "research_eligible": entry.research_eligible,
                        "valid_from": entry.valid_from.isoformat() if entry.valid_from else None,
                        "valid_to": entry.valid_to.isoformat() if entry.valid_to else None,
                        "instrument_type": entry.instrument_type, "figi": entry.figi,
                        "cusip": entry.cusip, "isin": entry.isin, "pit_qualified": entry.pit_qualified,
                        "lineage": entry.lineage} for entry in matched.values()],
        "unmapped_days": unmapped,
        "overlaps": _overlaps(entries),
        "evidence_needed": sorted({item for entry in matched.values() for item in entry.evidence}),
    }


def research_eligibility(registry: Sequence[Identity], ticker: str,
                         days: Sequence[date]) -> Dict[str, Any]:
    """A series is eligible only when it maps to exactly one research-eligible identity."""
    report = series_identities(registry, ticker, days)
    if report["status"] == NO_ENTRY:
        # Legacy research may continue, but an unregistered ticker is never point-in-time qualified.
        return {**report, "eligible": True, "pit_qualified": False, "reason": NO_ENTRY,
                "detail": "No identity registry entry; qualification rests on the snapshot FIGI only."}
    if report["status"] == MULTI:
        return {**report, "eligible": False, "pit_qualified": False, "reason": MULTI,
                "detail": "Stored sessions span more than one security identity; a return across them is invalid."}
    if report["status"] != "SINGLE_IDENTITY":
        return {**report, "eligible": False, "pit_qualified": False, "reason": UNVERIFIED,
                "detail": "No stored session maps to a canonical identity."}
    identity = report["identities"][0]
    if not identity["research_eligible"]:
        return {**report, "eligible": False, "pit_qualified": False, "reason": UNVERIFIED,
                "detail": f"Identity {identity['canonical_id']} is {identity['status']}; history is not qualified."}
    if report["unmapped_days"]:
        return {**report, "eligible": False, "pit_qualified": False, "reason": UNVERIFIED,
                "detail": f"{report['unmapped_days']} session(s) fall outside every registered interval."}
    return {**report, "eligible": True, "pit_qualified": bool(identity["pit_qualified"]), "reason": ELIGIBLE}


def assert_single_identity(registry: Sequence[Identity], ticker: str, days: Sequence[date]) -> None:
    """Fail closed if a return series would cross two securities."""
    result = research_eligibility(registry, ticker, days)
    if not result["eligible"]:
        raise DataContractError(f"IDENTITY_RETURN_CROSSES_SECURITIES: {ticker.upper()} {result['reason']}.")


def inception_evidence(registry: Sequence[Identity], ticker: str) -> Dict[str, Any]:
    """Listing evidence for a ticker: a verified date, or an explicit unverified state."""
    for entry in registry:
        if entry.ticker == ticker.upper() and entry.valid_from is not None:
            return {"ticker": ticker.upper(), "date": entry.valid_from.isoformat(),
                    "verified": entry.inception_verified, "source": entry.evidence[:2]}
    return {"ticker": ticker.upper(), "date": None, "verified": False, "source": []}
