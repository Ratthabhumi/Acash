"""BOT reference USD/THB series and an exact FX translation decomposition.

Orientation is fixed once: every rate in this module is **THB per 1 USD**. The provider returns both
directions; only ``USD -> THB`` observations are kept, and a date that appears with two different rates
is refused rather than silently resolved.

For a holding with no cash flow in the period:

    (1 + R_THB) = (1 + R_USD) * (1 + R_FX)

so ``R_THB = R_USD + R_FX + R_USD * R_FX`` exactly. The three terms are reported separately — USD price
return, FX translation and the cross term — and never added as if they were percentages of the same
base. If an FX rate is missing on a session, that session is excluded from the decomposition instead of
being forward-filled.

BOT publishes a daily weighted-average interbank reference rate. It is **not** the rate a broker would
execute, and nothing here may be used as an executable conversion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.invest.market_valuation import FXObservation

SCHEMA = "ACASH_FX_REFERENCE_SERIES_V1"
RATE_TYPE = "REFERENCE_WEIGHTED_AVERAGE_INTERBANK"
DEFAULT_ROOT = Path("data/private/market_warehouse/fx")


@dataclass(frozen=True)
class FxPoint:
    day: date
    usd_thb: Decimal
    source: str
    retrieved_at: str
    rate_type: str = RATE_TYPE

    def as_doc(self) -> Dict[str, Any]:
        return {"date": self.day.isoformat(), "usd_thb": format(self.usd_thb, "f"), "source": self.source,
                "rate_type": self.rate_type, "retrieved_at": self.retrieved_at,
                "orientation": "THB_PER_USD", "executable": False}


@dataclass(frozen=True)
class FxSeries:
    points: Mapping[date, FxPoint]
    source: str
    requested: Tuple[date, date]

    @property
    def first(self) -> Optional[date]:
        return min(self.points) if self.points else None

    @property
    def last(self) -> Optional[date]:
        return max(self.points) if self.points else None

    def rates(self) -> Dict[date, Decimal]:
        return {day: point.usd_thb for day, point in self.points.items()}

    def summary(self) -> Dict[str, Any]:
        latest = self.points.get(self.last) if self.last else None
        weekdays = 0
        day = self.requested[0]
        while day <= self.requested[1]:
            if day.weekday() < 5:
                weekdays += 1
            day += timedelta(days=1)
        return {
            "schema": SCHEMA,
            "source": self.source,
            "rate_type": RATE_TYPE,
            "orientation": "THB_PER_USD",
            "executable": False,
            "requested": {"start": self.requested[0].isoformat(), "end": self.requested[1].isoformat()},
            "first": self.first.isoformat() if self.first else None,
            "last": self.last.isoformat() if self.last else None,
            "points": len(self.points),
            "latest": latest.as_doc() if latest else None,
            "weekday_gaps": max(0, weekdays - len(self.points)),
            "note": ("Weekday gaps are informational only: the source has its own publication calendar, "
                     "so a missing weekday is reported, never filled."),
        }


def collect_series(provider: Any, start: date, end: date, *, chunk_days: int = 31,
                   pause_seconds: float = 0.0, pause: Any = None) -> FxSeries:
    """Fetch a bounded daily USD/THB series in chunks; every chunk is one provider request.

    The BOT reference-rate endpoint refuses a window wider than about one month (HTTP 400), so the
    default chunk is 31 days. A 2-year history therefore costs about 24 requests, well inside the
    200/hour product limit.
    """
    if start > end:
        raise DataContractError("FX_RANGE_INVALID: start must be on or before end.")
    if chunk_days < 1 or chunk_days > 366:
        raise DataContractError("FX_CHUNK_INVALID: chunk_days must be 1..366.")
    points: Dict[date, FxPoint] = {}
    source = str(getattr(provider, "provider_id", "BOT_REFERENCE_FX"))
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=chunk_days - 1))
        observations: Sequence[FXObservation] = provider.reference_rates(chunk_end, (chunk_end - cursor).days)
        for obs in observations:
            if obs.from_currency != "USD" or obs.to_currency != "THB":
                continue
            if not cursor <= obs.market_date <= chunk_end:
                raise DataContractError(f"FX_DATE_OUT_OF_CHUNK: {obs.market_date.isoformat()}.")
            if obs.rate <= 0:
                raise DataContractError("FX_RATE_INVALID: non-positive rate.")
            existing = points.get(obs.market_date)
            if existing is not None and existing.usd_thb != obs.rate:
                raise DataContractError(f"FX_CONFLICTING_RATE: {obs.market_date.isoformat()}.")
            points[obs.market_date] = FxPoint(obs.market_date, obs.rate, obs.provider_id,
                                              obs.retrieved_at.isoformat(timespec="seconds"))
        cursor = chunk_end + timedelta(days=1)
        if pause is not None and cursor <= end:
            pause(pause_seconds)
    if not points:
        raise DataContractError("FX_SERIES_EMPTY: the provider returned no USD/THB observation.")
    return FxSeries(points=dict(sorted(points.items())), source=source, requested=(start, end))


def _return(new: Decimal, old: Decimal) -> Decimal:
    if old <= 0 or new <= 0:
        raise DataContractError("FX_RETURN_INVALID: non-positive value.")
    return (new / old) - 1


@dataclass(frozen=True)
class Decomposition:
    sessions: Tuple[date, ...]
    usd: Dict[str, List[Decimal]]
    thb: Dict[str, List[Decimal]]
    fx: List[Decimal]
    cross: Dict[str, List[Decimal]]

    def summary(self, weights: Optional[Mapping[str, Decimal]] = None) -> Dict[str, Any]:
        cumulative_fx = _compound(self.fx)
        latest = self.sessions[-1].isoformat() if self.sessions else None
        per: Dict[str, Any] = {}
        for symbol in sorted(self.usd):
            cumulative_usd = _compound(self.usd[symbol])
            cumulative_thb = _compound(self.thb[symbol])
            per[symbol] = {
                "usd_price_return": format(cumulative_usd, "f"),
                "thb_return": format(cumulative_thb, "f"),
                "fx_translation": format(cumulative_fx, "f"),
                "cross_term": format(cumulative_usd * cumulative_fx, "f"),
                "identity_check": format(cumulative_usd + cumulative_fx + cumulative_usd * cumulative_fx, "f"),
                "identity_residual": format(
                    cumulative_thb - (cumulative_usd + cumulative_fx + cumulative_usd * cumulative_fx), "e"),
            }
        portfolio = None
        if weights and self.usd:
            missing = [s for s in self.usd if s not in weights]
            if missing:
                raise DataContractError(f"FX_PORTFOLIO_WEIGHTS_INCOMPLETE: {sorted(missing)[:3]}.")
            total = sum((weights[s] for s in self.usd), Decimal(0))
            if total <= 0:
                raise DataContractError("FX_PORTFOLIO_WEIGHTS_EMPTY.")
            weighted_usd = [sum((weights[s] * self.usd[s][i] for s in self.usd), Decimal(0)) / total
                            for i in range(len(self.fx))]
            cumulative_usd = _compound(weighted_usd)
            portfolio = {"weight_basis": "CONSTANT_WEIGHTS_DAILY_REBALANCED",
                         "weights_are_current_not_historical": True,
                         "usd_price_return": format(cumulative_usd, "f"),
                         "thb_return": format(cumulative_usd + cumulative_fx + cumulative_usd * cumulative_fx, "f"),
                         "fx_translation": format(cumulative_fx, "f"),
                         "cross_term": format(cumulative_usd * cumulative_fx, "f")}
        return {
            "schema": "ACASH_FX_DECOMPOSITION_V1",
            "sessions": len(self.sessions),
            "first": self.sessions[0].isoformat() if self.sessions else None,
            "last": latest,
            "identity": "(1 + R_THB) = (1 + R_USD) * (1 + R_FX)",
            "performance_basis": "HYPOTHETICAL_HISTORICAL_BASKET",
            "realized_performance": False,
            "labels": [
                "HYPOTHETICAL_HISTORICAL_BASKET",
                "PRICE_RETURN_ONLY",
                "CURRENT_WEIGHTS_APPLIED_HISTORICALLY",
                "NOT_TRANSACTION_RECONSTRUCTED",
                "NOT_REALIZED_PORTFOLIO_PERFORMANCE",
                "BOT_REFERENCE_FX_NOT_EXECUTABLE",
            ],
            "period_count": len(self.fx),
            "instruments": per,
            "portfolio": portfolio,
            "caveats": [
                "BOT reference rates are not executable brokerage rates.",
                "Sessions without an FX rate on the same date are excluded, never filled.",
                "The cross term is R_USD * R_FX; the three terms add to R_THB exactly for the same period.",
            ],
        }


def _compound(values: Sequence[Decimal]) -> Decimal:
    total = Decimal(1)
    for value in values:
        total *= (Decimal(1) + value)
    return total - 1


def decompose(closes: Mapping[str, Mapping[date, Decimal]], rates: Mapping[date, Decimal],
              sessions: Sequence[date]) -> Decomposition:
    """Per-session USD return, FX return and THB return on dates where both are observed."""
    usable = [day for day in sessions if day in rates]
    if len(usable) < 2:
        raise DataContractError("FX_DECOMPOSITION_TOO_SHORT: fewer than two aligned sessions.")
    for symbol, series in closes.items():
        missing = [day for day in usable if day not in series]
        if missing:
            raise DataContractError(f"FX_PRICE_SESSION_MISSING: {symbol} {missing[0].isoformat()}.")
    fx: List[Decimal] = []
    usd: Dict[str, List[Decimal]] = {symbol: [] for symbol in closes}
    thb: Dict[str, List[Decimal]] = {symbol: [] for symbol in closes}
    cross: Dict[str, List[Decimal]] = {symbol: [] for symbol in closes}
    for previous, current in zip(usable, usable[1:]):
        r_fx = _return(rates[current], rates[previous])
        fx.append(r_fx)
        for symbol, series in closes.items():
            r_usd = _return(series[current], series[previous])
            usd[symbol].append(r_usd)
            cross[symbol].append(r_usd * r_fx)
            thb[symbol].append((Decimal(1) + r_usd) * (Decimal(1) + r_fx) - 1)
    return Decomposition(tuple(usable), usd, thb, fx, cross)


def write_series(series: FxSeries, report: Mapping[str, Any], root: Path = DEFAULT_ROOT) -> Path:
    """Persist the reference series and the derived decomposition (private research data)."""
    root.mkdir(parents=True, exist_ok=True)
    doc = {"schema": SCHEMA, "source": series.source, "requested": {
        "start": series.requested[0].isoformat(), "end": series.requested[1].isoformat()},
        "points": [series.points[day].as_doc() for day in sorted(series.points)],
        "summary": series.summary()}
    path = root / "usd_thb_series.json"
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (root / "decomposition.json").write_text(json.dumps(dict(report), indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8", newline="\n")
    return path


def load_series(root: Path = DEFAULT_ROOT) -> Optional[Dict[str, Any]]:
    path = root / "usd_thb_series.json"
    if not path.is_file():
        return None
    try:
        doc: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc


def load_decomposition(root: Path = DEFAULT_ROOT) -> Optional[Dict[str, Any]]:
    path = root / "decomposition.json"
    if not path.is_file():
        return None
    try:
        doc: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc


def iter_points(series: FxSeries) -> Iterable[Tuple[date, Decimal]]:
    for day in sorted(series.points):
        yield day, series.points[day].usd_thb
