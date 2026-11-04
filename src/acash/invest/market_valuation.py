"""Market price observations, provider gating, quote selection and same-date revaluation.

Observations are evidence with provenance; this module never fetches anything. A revaluation
copies the owner's saved quantities and cash into a new V1_2 snapshot document pinned to one
market date and validates it with ``parse_snapshot``, so PPDS stays the only valuation authority.
Broker-displayed totals belong to the original observation time and are not carried over.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple

from decimal import Decimal

from acash.core.domain.exceptions import DataContractError
from acash.ppds.private_observation import SCHEMA_V1_2, parse_snapshot

PRICE_TYPES = ("EOD_CLOSE", "LAST_TRADE", "INTRADAY_BAR_CLOSE", "HISTORICAL_DELAYED_LAST",
               "OWNER_OBSERVED", "SYNTHETIC")
COVERAGES = ("CONSOLIDATED", "NASDAQ_BASIC", "IEX_ONLY", "UNKNOWN")
FX_KINDS = ("REFERENCE_FX", "BROKER_EXECUTED_FX", "INDICATIVE_FX")
_CCY = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class PriceObservation:
    security_id: str
    provider_id: str
    provider_symbol: str
    currency: str
    price: Decimal
    price_type: str
    market_date: date
    retrieved_at: datetime
    coverage: str = "UNKNOWN"
    market_timestamp: Optional[datetime] = None
    exchange_mic: Optional[str] = None
    adjustment_policy: str = "UNADJUSTED"


@dataclass(frozen=True)
class FXObservation:
    from_currency: str
    to_currency: str
    rate: Decimal
    market_date: date
    kind: str
    provider_id: str
    retrieved_at: datetime


@dataclass(frozen=True)
class ProviderCapabilities:
    """``None`` means not established; only explicit ``True`` on every check makes a provider usable."""

    provider_id: str
    price_types: Tuple[str, ...]
    coverage: str
    governance_authorized: Optional[bool] = None
    entitlement_verified: Optional[bool] = None
    display_permitted: Optional[bool] = None
    cache_permitted: Optional[bool] = None

    @property
    def status(self) -> str:
        checks = (self.governance_authorized, self.entitlement_verified, self.display_permitted)
        if all(c is True for c in checks):
            return "READY"
        if any(c is False for c in checks):
            return "NOT_PERMITTED"
        return "NOT_ENABLED_UNVERIFIED"


class MarketDataProvider(Protocol):
    def capabilities(self) -> ProviderCapabilities: ...

    def latest_prices(self, security_ids: Sequence[str], as_of: date) -> Sequence[PriceObservation]: ...


@dataclass
class SyntheticProvider:
    """Test provider: returns the observations it was given; never used for owner data."""

    provider_id: str
    observations: Sequence[PriceObservation]
    price_types: Tuple[str, ...] = ("SYNTHETIC",)
    ready: bool = True
    failure: Optional[str] = None
    calls: List[Tuple[str, ...]] = field(default_factory=list)

    def capabilities(self) -> ProviderCapabilities:
        flag = True if self.ready else None
        return ProviderCapabilities(self.provider_id, self.price_types, "UNKNOWN", flag, flag, flag, flag)

    def latest_prices(self, security_ids: Sequence[str], as_of: date) -> Sequence[PriceObservation]:
        self.calls.append(tuple(security_ids))
        if self.failure:
            raise DataContractError(f"{self.failure}: {self.provider_id}.")
        return [o for o in self.observations if o.security_id in security_ids]


@dataclass(frozen=True)
class DisabledProvider:
    """A researched candidate with no network client: it stays disabled until an ODR authorizes
    egress and the Owner verifies entitlement and display rights."""

    provider_id: str
    price_types: Tuple[str, ...]
    coverage: str
    role: str

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.provider_id, self.price_types, self.coverage)

    def latest_prices(self, security_ids: Sequence[str], as_of: date) -> Sequence[PriceObservation]:
        raise DataContractError(f"PROVIDER_NOT_ENABLED: {self.provider_id} has no authorized client.")


CANDIDATE_PROVIDERS: Tuple[DisabledProvider, ...] = (
    DisabledProvider("WEBULL_TH_OPENAPI", ("LAST_TRADE",), "NASDAQ_BASIC", "PRIMARY_INTRADAY_CANDIDATE"),
    DisabledProvider("ALPACA_BASIC", ("LAST_TRADE",), "IEX_ONLY", "FALLBACK_INTRADAY_CANDIDATE"),
    DisabledProvider("MASSIVE_BASIC", ("EOD_CLOSE",), "UNKNOWN", "FALLBACK_EOD_CANDIDATE"),
    DisabledProvider("BOT_REFERENCE_FX", (), "UNKNOWN", "REFERENCE_FX_CANDIDATE"),
)


def provider_matrix(providers: Sequence[DisabledProvider] = CANDIDATE_PROVIDERS) -> List[Dict[str, Any]]:
    out = []
    for p in providers:
        caps = p.capabilities()
        out.append({"provider_id": p.provider_id, "role": p.role, "coverage": p.coverage, "status": caps.status,
                    "governance_authorized": caps.governance_authorized,
                    "entitlement_verified": caps.entitlement_verified, "display_permitted": caps.display_permitted})
    return out


@dataclass(frozen=True)
class QuotePolicy:
    as_of: date
    max_age_days: int
    price_types: Tuple[str, ...] = ("EOD_CLOSE",)
    now: Optional[datetime] = None
    clock: Optional[Callable[[], datetime]] = None

    def current(self) -> datetime:
        return self.now or (self.clock() if self.clock else datetime.now(timezone.utc))


def _aware(stamp: Optional[datetime]) -> bool:
    return stamp is None or stamp.tzinfo is not None


def _reject_reason(o: PriceObservation, policy: QuotePolicy, now: datetime) -> Optional[str]:
    if o.price_type not in PRICE_TYPES or o.coverage not in COVERAGES:
        return "OBSERVATION_TYPE_INVALID"
    if o.price_type not in policy.price_types:
        return "PRICE_TYPE_NOT_REQUESTED"
    if not o.price.is_finite() or o.price <= 0:
        return "PRICE_NONPOSITIVE"
    if not _CCY.match(o.currency):
        return "CURRENCY_INVALID"
    if not _aware(o.retrieved_at) or not _aware(o.market_timestamp):
        return "TIMESTAMP_NOT_TIMEZONE_AWARE"
    if (o.retrieved_at > now or (o.market_timestamp is not None and o.market_timestamp > o.retrieved_at)
            or o.market_date > o.retrieved_at.astimezone(timezone.utc).date()):
        return "FUTURE_TIMESTAMP"
    if o.market_date > policy.as_of:
        return "AFTER_VALUATION_DATE"
    if (policy.as_of - o.market_date).days > policy.max_age_days:
        return "STALE_PRICE"
    return None


def select_quotes(security_ids: Sequence[str], providers: Sequence[MarketDataProvider],
                  policy: QuotePolicy) -> Dict[str, Any]:
    """Walk providers in priority order; a provider is asked only for still-unpriced securities.

    Observations are never averaged. Within one provider the latest eligible market date wins;
    differing prices for the same date are rejected as conflicting.
    """
    if policy.max_age_days < 0:
        raise DataContractError("QUOTE_POLICY_INVALID: max_age_days must be >= 0.")
    wanted_all = sorted(set(security_ids))
    selected: Dict[str, PriceObservation] = {}
    rejected: List[Dict[str, str]] = []
    statuses: Dict[str, str] = {}
    for provider in providers:
        caps = provider.capabilities()
        pid = caps.provider_id
        if caps.status != "READY":
            statuses[pid] = caps.status
            continue
        wanted = [s for s in wanted_all if s not in selected]
        if not wanted:
            statuses[pid] = "NOT_NEEDED"
            continue
        try:
            observations = provider.latest_prices(wanted, policy.as_of)
        except DataContractError as exc:
            statuses[pid] = str(exc).split(":")[0]
            continue
        statuses[pid] = "QUERIED"
        now = policy.current()
        candidates: Dict[str, List[PriceObservation]] = {}
        for o in observations:
            if o.provider_id != pid or o.security_id not in wanted:
                rejected.append({"security_id": o.security_id, "provider_id": pid, "reason": "UNREQUESTED_OR_MISATTRIBUTED"})
                continue
            reason = _reject_reason(o, policy, now)
            if reason:
                rejected.append({"security_id": o.security_id, "provider_id": pid, "reason": reason})
                continue
            candidates.setdefault(o.security_id, []).append(o)
        for sid in sorted(candidates):
            latest = max(o.market_date for o in candidates[sid])
            same_day = [o for o in candidates[sid] if o.market_date == latest]
            if len({(o.price, o.currency, o.price_type) for o in same_day}) > 1:
                rejected.append({"security_id": sid, "provider_id": pid, "reason": "CONFLICTING_OBSERVATIONS"})
                continue
            selected[sid] = same_day[0]
    return {"selected": selected, "rejected": rejected, "provider_statuses": statuses,
            "unpriced": [s for s in wanted_all if s not in selected]}


def revalue_snapshot(doc: Dict[str, Any], selected: Dict[str, PriceObservation],
                     fx: Sequence[FXObservation], snapshot_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return a new V1_2 document valued at one market date, plus sanitized metadata."""
    original = parse_snapshot(doc)
    if original.schema != SCHEMA_V1_2:
        raise DataContractError("REVALUATION_REQUIRES_V1_2.")
    value_only = sum(len(a.observed_value_positions) for a in original.accounts)
    if value_only:
        raise DataContractError(f"REVALUATION_VALUE_ONLY_PRESENT: {value_only} holdings have no quantity; "
                                "their value cannot be repriced and is not treated as zero.")
    totals_only = sum(not (a.positions or a.cash) for a in original.accounts)
    if totals_only:
        raise DataContractError(f"REVALUATION_TOTAL_ONLY_ACCOUNT: {totals_only} accounts have only broker totals; "
                                "their value cannot be repriced and is not treated as zero.")
    needed = sorted({p.security_id for a in original.accounts for p in a.positions})
    missing = [s for s in needed if s not in selected]
    if missing:
        raise DataContractError(f"REVALUATION_PRICE_UNAVAILABLE: {len(missing)} held securities have no eligible "
                                "price; unknown value is not treated as zero.")
    dates = {selected[s].market_date for s in needed} | {r.market_date for r in fx}
    if len(dates) != 1:
        raise DataContractError("REVALUATION_TIME_MISALIGNED: prices and FX span several market dates; "
                                "a same-date valuation cannot be formed.")
    market_date = dates.pop()
    if any(r.kind not in FX_KINDS for r in fx):
        raise DataContractError("REVALUATION_FX_KIND_INVALID.")
    observed_at = max([selected[s].retrieved_at for s in needed] + [r.retrieved_at for r in fx])

    new = copy.deepcopy(doc)
    new.update(snapshot_id=snapshot_id, observed_at=observed_at.isoformat(), valuation_date=market_date.isoformat())
    new["prices"] = [{"security_id": s, "currency": selected[s].currency, "price": str(selected[s].price),
                      "as_of": market_date.isoformat(),
                      "published_at": (selected[s].market_timestamp or selected[s].retrieved_at).isoformat(),
                      "source_id": selected[s].provider_id} for s in needed]
    new["fx_rates"] = [{"from": r.from_currency, "to": r.to_currency, "rate": str(r.rate),
                        "as_of": market_date.isoformat(), "source_id": r.provider_id} for r in fx]
    for account in new["accounts"]:
        account.pop("reported_total", None)
        account.pop("sub_portfolio_totals", None)
        for position in account.get("positions") or []:
            position.pop("observed_market_value", None)
            position.pop("observed_market_value_currency", None)
    parse_snapshot(new)

    types = {selected[s].price_type for s in needed}
    meta = {
        "valuation_mode": "SAME_DATE_EOD" if types == {"EOD_CLOSE"} else "SAME_DATE_INDICATIVE",
        "market_date": market_date.isoformat(),
        "holdings_observed_on": original.valuation_date.isoformat(),
        "price_sources": sorted({selected[s].provider_id for s in needed}),
        "price_coverage": sorted({selected[s].coverage for s in needed}),
        "fx_kinds": sorted({r.kind for r in fx}),
        "broker_total_comparison": ("TIME_MISALIGNED_COMPARISON" if market_date != original.valuation_date
                                    else "NOT_CARRIED_INTO_REVALUATION"),
        "cash_basis": "CASH_AS_OF_HOLDINGS_OBSERVATION",
        "flags": sorted(f for f in (
            "PRICES_PREDATE_HOLDINGS_OBSERVATION" if market_date < original.valuation_date else "",
            "MIXED_PRICE_SOURCES" if len({selected[s].provider_id for s in needed}) > 1 else "",
            "REFERENCE_FX_NOT_EXECUTABLE" if any(r.kind == "REFERENCE_FX" for r in fx) else "",
        ) if f),
    }
    return new, meta


def partial_snapshot(doc: Dict[str, Any], selected: Dict[str, PriceObservation], fx: Sequence[FXObservation],
                     snapshot_id: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Derived V1_2 document holding only the components that can be valued at one market date.

    The market date is the latest date among the selected quotes. Positions without a quote,
    with a quote from another date, or without a quantity, and accounts with only broker totals,
    are left out and counted in ``coverage``; nothing is valued at zero or carried forward. Cash
    is the owner's observed cash at the holdings observation date. FX is used only when it is
    dated on the market date. The returned document is validated by ``parse_snapshot``; the
    valuation itself is left to PPDS ``build_book``.
    """
    original = parse_snapshot(doc)
    if original.schema != SCHEMA_V1_2:
        raise DataContractError("REVALUATION_REQUIRES_V1_2.")
    held = sorted({p.security_id for a in original.accounts for p in a.positions})
    quoted = [s for s in held if s in selected]
    market_date = max((selected[s].market_date for s in quoted), default=None)
    priced = [s for s in quoted if selected[s].market_date == market_date]
    misaligned = [s for s in quoted if s not in priced]
    fx_used = [r for r in fx if r.market_date == market_date and r.kind in FX_KINDS]
    total_only = [a.account_ref for a in original.accounts if not (a.positions or a.cash or a.observed_value_positions)]
    coverage = {
        "held_with_quantity": len(held), "priced": len(priced), "misaligned_date": len(misaligned),
        "unpriced": len(held) - len(quoted),
        "value_only": sum(len(a.observed_value_positions) for a in original.accounts),
        "total_only_accounts": len(total_only),
    }
    complete = coverage["priced"] == coverage["held_with_quantity"] and not (
        coverage["value_only"] or coverage["total_only_accounts"])
    sources = sorted({selected[s].provider_id for s in priced})
    meta: Dict[str, Any] = {
        "market_date": market_date.isoformat() if market_date else None,
        "holdings_observed_on": original.valuation_date.isoformat(),
        "coverage": coverage,
        "price_sources": sources,
        "price_types": sorted({selected[s].price_type for s in priced}),
        "price_coverage": sorted({selected[s].coverage for s in priced}),
        "fx_dates": sorted({r.market_date.isoformat() for r in fx}),
        "fx_used": bool(fx_used),
        "cash_basis": "CASH_AS_OF_HOLDINGS_OBSERVATION",
        "broker_total_comparison": "TIME_MISALIGNED_COMPARISON",
        "flags": sorted(f for f in (
            "REFERENCE_FX_NOT_EXECUTABLE" if any(r.kind == "REFERENCE_FX" for r in fx_used) else "",
            "PRICES_PREDATE_HOLDINGS_OBSERVATION" if market_date and market_date < original.valuation_date else "",
            "IEX_ONLY_NOT_CONSOLIDATED" if any(selected[s].coverage == "IEX_ONLY" for s in priced) else "",
        ) if f),
    }
    if not priced or market_date is None:
        meta["valuation_status"] = "UNAVAILABLE"
        return None, meta
    meta["valuation_status"] = ("PARTIAL_INDICATIVE_VALUATION" if not complete
                                else "MIXED_SOURCE_INDICATIVE_VALUATION" if len(sources) > 1
                                else "INDICATIVE_VALUATION")

    keep = set(priced)
    new = copy.deepcopy(doc)
    observed_at = max([selected[s].retrieved_at for s in priced] + [r.retrieved_at for r in fx_used])
    new.update(snapshot_id=snapshot_id, observed_at=observed_at.isoformat(), valuation_date=market_date.isoformat())
    accounts = []
    for account in new["accounts"]:
        account.pop("reported_total", None)
        account.pop("sub_portfolio_totals", None)
        account["positions"] = [p for p in account.get("positions") or []
                                if p.get("quantity") is not None and p.get("security_id") in keep]
        for position in account["positions"]:
            position.pop("observed_market_value", None)
            position.pop("observed_market_value_currency", None)
        if account["positions"] or account.get("cash"):
            accounts.append(account)
    new["accounts"] = accounts
    new["securities"] = [s for s in new.get("securities") or [] if s.get("security_id") in keep]
    new["prices"] = [{"security_id": s, "currency": selected[s].currency, "price": str(selected[s].price),
                      "as_of": market_date.isoformat(),
                      "published_at": (selected[s].market_timestamp or selected[s].retrieved_at).isoformat(),
                      "source_id": selected[s].provider_id} for s in priced]
    new["fx_rates"] = [{"from": r.from_currency, "to": r.to_currency, "rate": str(r.rate),
                        "as_of": market_date.isoformat(), "source_id": r.provider_id} for r in fx_used]
    parse_snapshot(new)
    return new, meta
