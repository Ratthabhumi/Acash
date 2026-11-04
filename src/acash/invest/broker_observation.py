"""Immutable broker-displayed observations (category totals), separate from transactions and NAV.

A Dime! asset-tracker screenshot states what the broker app displayed at one moment. It is
evidence of a *display*, not a transaction, not a per-security price, and not an ACASH-computed
NAV. Recording it must never create balancing cash, trades or FX adjustments, and comparing it with
a valuation from another date must stay ``TIME_MISALIGNED``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_BROKER_OBSERVATIONS_V1"
DATA_CLASS = "OWNER_PRIVATE_OBSERVATION"
EVIDENCE = "BROKER_DISPLAYED_OBSERVATION"
CATEGORIES = ("us_equities", "cash", "mutual_fund", "gold", "thai_equities")
TOLERANCE = Decimal("0.01")
# A date match alone is not a time match: two same-day observations hours apart compare different
# prices, FX and transaction cutoffs.
ALIGNMENT_TOLERANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class BrokerObservation:
    observation_id: str
    broker: str
    observed_at: datetime
    currency: str
    categories: Dict[str, Decimal]
    displayed_total: Decimal
    source: str
    evidence_status: str = EVIDENCE

    @property
    def observed_date(self) -> date:
        return self.observed_at.date()


def parse_observation(raw: Any) -> BrokerObservation:
    if not isinstance(raw, dict):
        raise DataContractError("BROKER_OBSERVATION_INVALID.")
    try:
        observed_at = datetime.fromisoformat(str(raw["observed_at"]))
    except (KeyError, ValueError):
        raise DataContractError("BROKER_OBSERVATION_TIMESTAMP_INVALID.") from None
    if observed_at.tzinfo is None:
        raise DataContractError("BROKER_OBSERVATION_TIMESTAMP_INVALID: timezone required.")
    cats = raw.get("categories")
    if not isinstance(cats, dict) or set(cats) - set(CATEGORIES):
        raise DataContractError("BROKER_OBSERVATION_CATEGORIES_INVALID.")
    categories: Dict[str, Decimal] = {}
    for key, value in cats.items():
        try:
            number = Decimal(str(value))
        except Exception:
            raise DataContractError(f"BROKER_OBSERVATION_CATEGORY_INVALID: {key}.") from None
        if not number.is_finite() or number < 0:
            raise DataContractError(f"BROKER_OBSERVATION_CATEGORY_INVALID: {key}.")
        categories[key] = number
    try:
        total = Decimal(str(raw["displayed_total"]))
    except (KeyError, Exception):
        raise DataContractError("BROKER_OBSERVATION_TOTAL_INVALID.") from None
    obs = BrokerObservation(observation_id=str(raw.get("observation_id") or ""), broker=str(raw.get("broker") or ""),
                            observed_at=observed_at, currency=str(raw.get("currency") or "THB"),
                            categories=categories, displayed_total=total,
                            source=str(raw.get("source") or "OWNER_SCREENSHOT"),
                            evidence_status=str(raw.get("evidence_status") or EVIDENCE))
    validate_arithmetic(obs)
    return obs


def validate_arithmetic(obs: BrokerObservation) -> None:
    """Category totals must add up to the displayed total; USD-derived categories stay as displayed."""
    if obs.evidence_status != EVIDENCE:
        raise DataContractError("BROKER_OBSERVATION_EVIDENCE_INVALID.")
    aggregate = sum(obs.categories.values(), Decimal(0))
    if abs(aggregate - obs.displayed_total) > TOLERANCE:
        raise DataContractError("BROKER_OBSERVATION_ARITHMETIC_MISMATCH.")


def load_observations(path: Path) -> List[BrokerObservation]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise DataContractError("BROKER_OBSERVATION_SCHEMA_INVALID.")
    rows = doc.get("observations")
    if not isinstance(rows, list):
        raise DataContractError("BROKER_OBSERVATION_SCHEMA_INVALID.")
    return [parse_observation(row) for row in rows]


def latest(path: Path) -> Optional[BrokerObservation]:
    observations = load_observations(path)
    return max(observations, key=lambda o: o.observed_at) if observations else None


def record(path: Path, obs: BrokerObservation) -> str:
    """Append one observation atomically; an identical id or timestamp is not re-appended."""
    existing = load_observations(path)
    if any(o.observation_id == obs.observation_id for o in existing):
        return "ALREADY_RECORDED"
    if any(o.broker == obs.broker and o.observed_at == obs.observed_at for o in existing):
        raise DataContractError("BROKER_OBSERVATION_DUPLICATE_TIMESTAMP.")
    rows = [{"observation_id": o.observation_id, "broker": o.broker, "observed_at": o.observed_at.isoformat(),
             "currency": o.currency, "categories": {k: format(v, "f") for k, v in o.categories.items()},
             "displayed_total": format(o.displayed_total, "f"), "source": o.source,
             "evidence_status": o.evidence_status} for o in existing]
    rows.append({"observation_id": obs.observation_id, "broker": obs.broker,
                 "observed_at": obs.observed_at.isoformat(), "currency": obs.currency,
                 "categories": {k: format(v, "f") for k, v in obs.categories.items()},
                 "displayed_total": format(obs.displayed_total, "f"), "source": obs.source,
                 "evidence_status": obs.evidence_status})
    doc = {"schema": SCHEMA, "data_class": DATA_CLASS, "observations": rows}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return "RECORDED"


def compare(observation: BrokerObservation, calculated_total: Optional[Decimal],
            calculated_at: Optional[datetime]) -> Dict[str, Any]:
    """Time-qualified comparison; a calendar-date match alone is never enough.

    SAME_TIME_COMPARABLE       both timestamps present, same UTC day, within the alignment tolerance
    SAME_DATE_TIME_UNALIGNED   same day but the gap exceeds the tolerance (intraday prices/FX move)
    CROSS_DATE_TIME_MISALIGNED different days
    INSUFFICIENT_TIME_EVIDENCE no calculation timestamp, or a naive one
    """
    if calculated_total is None:
        return {"status": "CALCULATED_VALUE_UNAVAILABLE", "difference": None}
    if calculated_at is None or calculated_at.tzinfo is None:
        return {"status": "INSUFFICIENT_TIME_EVIDENCE", "difference": None,
                "broker_observed_at": observation.observed_at.isoformat(),
                "note": "The calculated valuation has no timezone-aware observation time, so no time "
                        "alignment can be claimed."}
    difference = observation.displayed_total - calculated_total
    gap = abs(observation.observed_at - calculated_at)
    same_day = observation.observed_at.astimezone(calculated_at.tzinfo).date() == calculated_at.date()
    if not same_day:
        status, note = "CROSS_DATE_TIME_MISALIGNED", (
            "Different observation days: market movement and FX timing can explain the gap, so this is "
            "not proof of a missing transaction or a valuation defect.")
    elif gap <= ALIGNMENT_TOLERANCE:
        status, note = "SAME_TIME_COMPARABLE", (
            "Same day and within the alignment tolerance; a residual still needs transaction-level evidence.")
    else:
        status, note = "SAME_DATE_TIME_UNALIGNED", (
            f"Same day but {int(gap.total_seconds() // 60)} minutes apart, beyond the "
            f"{int(ALIGNMENT_TOLERANCE.total_seconds() // 60)}-minute tolerance: intraday prices, FX and the "
            "transaction cutoff may differ, so this is not a settled reconciliation.")
    return {
        "status": status,
        "difference": format(difference, "f"),
        "difference_pct": None if calculated_total == 0 else
        format((difference / calculated_total * 100).quantize(Decimal("0.01")), "f"),
        "broker_observed_at": observation.observed_at.isoformat(),
        "calculated_observed_at": calculated_at.isoformat(),
        "alignment_tolerance_minutes": int(ALIGNMENT_TOLERANCE.total_seconds() // 60),
        "note": note,
    }


@dataclass(frozen=True)
class CashComponent:
    """One broker-visible cash account at the same observation time."""

    account_ref: str
    currency: str
    amount: Decimal
    thb_equivalent: Optional[Decimal] = None


def cash_breakdown(displayed_total: Decimal, components: Sequence[CashComponent]) -> Dict[str, Any]:
    """Explain a broker cash category from visible accounts, keeping any residual unexplained.

    Only accounts that actually appear in the broker evidence may be passed. A residual is never
    assigned to a new account, to FCD, or to buying power: it is reported as unexplained until the
    Owner supplies an account-level observation that covers it.
    """
    known = [c for c in components if c.thb_equivalent is not None]
    explained = sum((c.thb_equivalent for c in known if c.thb_equivalent is not None), Decimal(0))
    missing = [c.account_ref for c in components if c.thb_equivalent is None]
    residual = displayed_total - explained
    if missing:
        status = "PARTIAL_COMPONENTS_NOT_VALUED"
    elif residual == 0:
        status = "EXPLAINED"
    elif abs(residual) <= TOLERANCE:
        status = "EXPLAINED_WITH_ROUNDING"
    else:
        status = "UNEXPLAINED_RESIDUAL"
    return {
        "status": status,
        "displayed_total": format(displayed_total, "f"),
        "explained_total": format(explained, "f"),
        "residual": format(residual, "f"),
        "components": [{"account_ref": c.account_ref, "currency": c.currency,
                        "amount": format(c.amount, "f"),
                        "thb_equivalent": None if c.thb_equivalent is None else format(c.thb_equivalent, "f")}
                       for c in components],
        "components_not_valued": missing,
        "note": ("The residual is evidence of an incomplete breakdown, not a new cash account. "
                 "It is never added to any account, FCD, buying power or portfolio value."),
    }


def summary(observation: Optional[BrokerObservation]) -> Dict[str, Any]:
    if observation is None:
        return {"status": "NO_OBSERVATION"}
    return {"status": "OBSERVED", "observation_id": observation.observation_id, "broker": observation.broker,
            "observed_at": observation.observed_at.isoformat(), "currency": observation.currency,
            "displayed_total": format(observation.displayed_total, "f"),
            "categories": {k: format(v, "f") for k, v in observation.categories.items()},
            "evidence_status": observation.evidence_status,
            "arithmetic": "CATEGORY_SUM_MATCHES_DISPLAYED_TOTAL"}
