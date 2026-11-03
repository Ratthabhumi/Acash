"""One manual price refresh: eligible symbols -> provider quotes -> reference FX -> derived snapshot.

Only public US tickers quoted in USD are requested; anything else is reported as unsupported
rather than guessed. The result is a derived V1_2 document (``partial_snapshot``) plus sanitized
metadata; valuing it is left to PPDS. The owner's saved snapshot is never modified.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError
from acash.invest.market_valuation import (
    FXObservation,
    MarketDataProvider,
    QuotePolicy,
    partial_snapshot,
    select_quotes,
)
from acash.ppds.private_observation import PortfolioSnapshot, parse_snapshot

NEW_YORK = ZoneInfo("America/New_York")
SYMBOL = re.compile(r"^[A-Z][A-Z0-9]{0,9}(\.[A-Z])?$")
US_MICS = frozenset({"XNAS", "XNGS", "XNMS", "XNCM", "XNYS", "ARCX", "BATS", "XASE", "IEXG"})
MAX_QUOTE_AGE_DAYS = 7
PRICE_TYPES = ("LAST_TRADE", "INTRADAY_BAR_CLOSE", "EOD_CLOSE")


class FXProvider(Protocol):
    def reference_rates(self, end: date, lookback_days: int = 7) -> Sequence[FXObservation]: ...


def eligible_symbols(snapshot: PortfolioSnapshot) -> Tuple[List[str], int]:
    """(US-listed USD tickers to request, count of held securities that cannot be requested)."""
    price_ccy = {p.symbol: p.currency for p in snapshot.prices}
    classes = {s.security_id: s for s in snapshot.securities}
    held = sorted({p.security_id for a in snapshot.accounts for p in a.positions})
    ok = []
    for sid in held:
        cls = classes.get(sid)
        mic = cls.exchange_mic if cls else None
        ccy = (cls.trading_currency if cls else None) or price_ccy.get(sid)
        if SYMBOL.match(sid) and ccy == "USD" and (mic is None or mic in US_MICS):
            ok.append(sid)
    return ok, len(held) - len(ok)


def _currencies(snapshot: PortfolioSnapshot) -> Set[str]:
    found = set(snapshot.report_currencies)
    for account in snapshot.accounts:
        found.add(account.base_currency)
        found.update(c.currency for c in account.cash)
    found.update(p.currency for p in snapshot.prices)
    return found


def refresh_prices(doc: Dict[str, Any], price_providers: Sequence[MarketDataProvider],
                   fx_provider: Optional[FXProvider], now: datetime, snapshot_id: str,
                   clock: Optional[Callable[[], datetime]] = None) -> Dict[str, Any]:
    snapshot = parse_snapshot(doc)
    symbols, unsupported = eligible_symbols(snapshot)
    as_of = now.astimezone(NEW_YORK).date()
    selection = select_quotes(symbols, price_providers, QuotePolicy(as_of, MAX_QUOTE_AGE_DAYS, PRICE_TYPES, None, clock))
    selected = selection["selected"]
    market_date = max((o.market_date for o in selected.values()), default=None)
    fx: Sequence[FXObservation] = []
    fx_provider_id: Optional[str] = None
    if len(_currencies(snapshot)) <= 1:
        fx_status = "NOT_REQUIRED"
    elif market_date is None:
        fx_status = "NOT_REQUESTED_NO_PRICES"
    elif fx_provider is None:
        fx_status = "FX_PROVIDER_NOT_READY"
    else:
        try:
            fx = fx_provider.reference_rates(market_date)
            fx_status = ("REFERENCE_FX_ON_MARKET_DATE" if any(r.market_date == market_date for r in fx)
                         else "FX_UNAVAILABLE_FOR_MARKET_DATE")
            if fx_status == "REFERENCE_FX_ON_MARKET_DATE":
                fx_provider_id = getattr(fx_provider, "provider_id", None)
        except DataContractError as exc:
            fx_status = str(exc).split(":")[0]
    derived, meta = partial_snapshot(doc, selected, fx, snapshot_id)
    meta["fx_provider_id"] = fx_provider_id
    meta["coverage"]["unsupported_instruments"] = unsupported
    quotes = [{"security_id": sid, "provider_id": o.provider_id, "price": str(o.price), "currency": o.currency,
               "price_type": o.price_type, "coverage": o.coverage, "market_date": o.market_date.isoformat(),
               "market_timestamp": o.market_timestamp.isoformat() if o.market_timestamp else None,
               "retrieved_at": o.retrieved_at.isoformat(),
               "used": derived is not None and o.market_date.isoformat() == meta["market_date"]}
              for sid, o in sorted(selected.items())]
    return {"derived": derived, "meta": meta, "fx_status": fx_status, "quotes": quotes,
            "provider_statuses": selection["provider_statuses"], "rejected": selection["rejected"],
            "requested": len(symbols), "unpriced": selection["unpriced"]}
