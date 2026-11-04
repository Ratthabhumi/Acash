"""Economic asset-class registry (separate from the Owner's strategy/risk classification).

Instrument type (COMMON_STOCK / ETF / MUTUAL_FUND) and economic exposure (EQUITY / FIXED_INCOME /
CASH / COMMODITY_GOLD / MIXED_ASSET / OTHER / UNKNOWN) are two dimensions and are never merged. A
classification is only accepted when the evidence reference and its effective date are present;
otherwise the instrument stays UNKNOWN rather than being inferred from a ticker or a portfolio label.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_ECONOMIC_CLASSIFICATION_V1"
DATA_CLASS = "OWNER_PRIVATE_OBSERVATION"
CLASSES = ("EQUITY", "FIXED_INCOME", "CASH", "COMMODITY_GOLD", "MIXED_ASSET", "OTHER", "UNKNOWN")
INSTRUMENTS = ("COMMON_STOCK", "ETF", "MUTUAL_FUND", "OTHER")


@dataclass(frozen=True)
class Classification:
    security_id: str
    instrument_type: str
    economic_asset_class: str
    methodology: str
    evidence_ref: str
    effective_date: date
    verification_status: str


def load_registry(path: Path) -> Dict[str, Classification]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or doc.get("data_class") != DATA_CLASS:
        raise DataContractError("CLASSIFICATION_SCHEMA_INVALID.")
    rows = doc.get("classifications")
    if not isinstance(rows, list):
        raise DataContractError("CLASSIFICATION_SCHEMA_INVALID.")
    out: Dict[str, Classification] = {}
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise DataContractError(f"CLASSIFICATION_INVALID: rows[{index}].")
        sid = str(raw.get("security_id") or "")
        asset = raw.get("economic_asset_class")
        instrument = raw.get("instrument_type")
        if not sid or sid in out:
            raise DataContractError("CLASSIFICATION_DUPLICATE_OR_MISSING_ID.")
        if asset not in CLASSES or instrument not in INSTRUMENTS:
            raise DataContractError(f"CLASSIFICATION_INVALID: {sid} enums.")
        evidence = str(raw.get("evidence_ref") or "").strip()
        if asset != "UNKNOWN" and not evidence:
            raise DataContractError(f"CLASSIFICATION_EVIDENCE_REQUIRED: {sid}.")
        out[sid] = Classification(sid, instrument, asset, str(raw.get("methodology") or ""), evidence,
                                  date.fromisoformat(str(raw.get("effective_date"))),
                                  str(raw.get("verification_status") or "UNKNOWN"))
    return out


def security_values(snapshot_path: Path, reporting_currency: str = "THB") -> Dict[str, Decimal]:
    """Holding value per security in the reporting currency, using the snapshot's own FX rates."""
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    fx = {(row["from"], row["to"]): Decimal(str(row["rate"])) for row in snapshot.get("fx_rates", [])}
    prices = {row["security_id"]: row for row in snapshot.get("prices", [])}
    values: Dict[str, Decimal] = {}
    for account in snapshot.get("accounts", []):
        for position in account.get("positions", []):
            sid = position.get("security_id")
            if "quantity" not in position or sid not in prices:
                continue
            quote = prices[sid]
            native = Decimal(str(position["quantity"])) * Decimal(str(quote["price"]))
            currency = str(quote["currency"])
            if currency == reporting_currency:
                converted = native
            else:
                rate = fx.get((currency, reporting_currency))
                if rate is None:
                    continue
                converted = native * rate
            values[sid] = values.get(sid, Decimal(0)) + converted
    return values


def coverage(registry: Dict[str, Classification],
             values: Mapping[str, Optional[Decimal]]) -> Dict[str, Any]:
    """Coverage by both instrument count and holding value; unknown is never rounded into coverage."""
    classified_ids = [sid for sid, c in registry.items() if c.economic_asset_class != "UNKNOWN"]
    unknown_ids = [sid for sid, c in registry.items() if c.economic_asset_class == "UNKNOWN"]
    universe = sorted(set(values) | set(registry))
    missing = sorted(sid for sid in universe if sid not in registry)
    total_value = sum((v for v in values.values() if v is not None), Decimal(0))
    classified_value = sum((values.get(sid) or Decimal(0) for sid in classified_ids
                            if sid in values and values[sid] is not None), Decimal(0))
    unknown_value = total_value - classified_value
    by_class: Dict[str, Decimal] = {}
    for sid, c in registry.items():
        if c.economic_asset_class == "UNKNOWN" or values.get(sid) is None:
            continue
        by_class[c.economic_asset_class] = by_class.get(c.economic_asset_class, Decimal(0)) + (values[sid] or Decimal(0))
    return {
        "status": "PARTIAL_COVERAGE" if unknown_ids or missing else "FULL_COVERAGE_WITHIN_UNIVERSE",
        "instrument_count": len(universe),
        "classified_count": len(classified_ids),
        "unknown_count": len(unknown_ids),
        "missing_registry_entries": missing,
        "classified_value": format(classified_value, "f"),
        "unknown_value": format(unknown_value, "f"),
        "total_value": format(total_value, "f"),
        "by_class": {k: format(v, "f") for k, v in sorted(by_class.items())},
        "coverage_by_count": "0" if not universe else format(Decimal(len(classified_ids)) / Decimal(len(universe)), "f"),
        "coverage_by_value": "0" if total_value == 0 else format(classified_value / total_value, "f"),
        "note": "Coverage is measured against the instruments present in the current report only.",
    }
