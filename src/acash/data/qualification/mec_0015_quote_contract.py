"""MEC-0015 Historical SIP Quotes Execution Qualification Contract.

Strict Invariants:
1. Endpoint: GET https://data.alpaca.markets/v2/stocks/quotes?symbols=SPY&feed=sip&sort=asc
2. Authorized Probe Dates Only: (2019-06-03, 2022-06-01, 2024-03-01).
   Any date outside this authorized set raises DataContractError immediately.
3. Decision Boundaries: 10:00 ET, 12:00 ET, 15:30 ET.
4. Execution Fill Model:
   PRIMARY_EXECUTION_MODEL = FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY
   - BUY: fill_price = ask
   - SELL: fill_price = bid
   - Reject quote if: bid <= 0, ask <= 0, ask < bid (crossed), or required fields missing.
5. Spread Model:
   ACASH_SPREAD_MODEL = EMBEDDED_IN_NBBO_FILL
   EXPLICIT_HALF_SPREAD_DEDUCTION_WITH_NBBO = PROHIBITED
6. Diagnostic: quote_delay_ms = (quote_timestamp - execution_boundary) in ms.
7. Zero Strategy Execution: No signal generation, no direction, no backtest, no P&L.
8. Credential Hygiene: Credentials and headers are never serialized or logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError

NY_TZ = ZoneInfo("America/New_York")

MEC_0015_AUTHORIZED_QUOTE_PROBE_DATES: Sequence[date] = (
    date(2019, 6, 3),
    date(2022, 6, 1),
    date(2024, 3, 1),
)

MEC_0015_PROBE_DECISION_TIMES_ET: Sequence[time] = (
    time(10, 0, 0),
    time(12, 0, 0),
    time(15, 30, 0),
)

PRIMARY_EXECUTION_MODEL_NAME: str = "FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY"
SPREAD_MODEL_NAME: str = "EMBEDDED_IN_NBBO_FILL"


@dataclass(frozen=True)
class Mec0015SipQuoteRecord:
    """Parsed single historical SIP NBBO quote."""

    timestamp_utc: str
    bid_price: Decimal
    ask_price: Decimal
    bid_size: int
    ask_size: int
    bid_exchange: str
    ask_exchange: str
    conditions: List[str]
    tape: str
    spread: Decimal
    is_locked: bool
    is_crossed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "bid_price": str(self.bid_price),
            "ask_price": str(self.ask_price),
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "bid_exchange": self.bid_exchange,
            "ask_exchange": self.ask_exchange,
            "conditions": self.conditions,
            "tape": self.tape,
            "spread": str(self.spread),
            "is_locked": self.is_locked,
            "is_crossed": self.is_crossed,
        }


@dataclass(frozen=True)
class Mec0015BoundaryQuotePair:
    """Quotes immediately before and immediately after an execution boundary."""

    session_date: str
    boundary_time_et: str
    boundary_timestamp_utc: str
    latest_quote_before: Optional[Mec0015SipQuoteRecord]
    first_quote_at_or_after: Mec0015SipQuoteRecord
    quote_delay_ms: float
    simulated_buy_fill: Decimal
    simulated_sell_fill: Decimal
    is_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date,
            "boundary_time_et": self.boundary_time_et,
            "boundary_timestamp_utc": self.boundary_timestamp_utc,
            "quote_delay_ms": self.quote_delay_ms,
            "simulated_buy_fill": str(self.simulated_buy_fill),
            "simulated_sell_fill": str(self.simulated_sell_fill),
            "is_valid": self.is_valid,
            "first_quote_at_or_after": self.first_quote_at_or_after.to_dict(),
            "latest_quote_before": (
                self.latest_quote_before.to_dict() if self.latest_quote_before else None
            ),
        }


@dataclass(frozen=True)
class Mec0015QuoteContractReport:
    """Complete report for MEC-0015 SIP quotes qualification."""

    endpoint: str
    symbol: str
    feed: str
    authorized_dates: List[str]
    boundaries: List[Mec0015BoundaryQuotePair]
    primary_execution_model: str
    spread_model: str
    explicit_half_spread_deduction_prohibited: bool
    delay_ms_distribution: Dict[str, float]
    all_quotes_valid: bool
    manifest_sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_schema": "acash.research.mec_0015_quote_manifest.v1",
            "endpoint": self.endpoint,
            "symbol": self.symbol,
            "feed": self.feed,
            "authorized_probe_dates": self.authorized_dates,
            "execution_contract": {
                "primary_execution_model": self.primary_execution_model,
                "spread_model": self.spread_model,
                "explicit_half_spread_deduction_with_nbbo": "PROHIBITED",
                "standalone_slippage_model": "BASELINE_STANDALONE_SLIPPAGE = $0.001/share per executed side",
                "two_x_friction_stress_definition": (
                    "Retain observed NBBO fill, double non-spread explicit transaction costs, "
                    "and add adverse slippage stress equal to one observed half-spread per side."
                ),
            },
            "latency_diagnostics": self.delay_ms_distribution,
            "boundary_evaluations": [b.to_dict() for b in self.boundaries],
            "is_qualified": self.all_quotes_valid,
        }


def parse_sip_quote(raw_quote: Dict[str, Any]) -> Mec0015SipQuoteRecord:
    """Parse and validate a raw SIP quote from Alpaca.

    Fails closed if bid/ask prices are missing, nonpositive, or unparseable.
    """
    try:
        t_str = str(raw_quote["t"])
        bp = Decimal(str(raw_quote["bp"]))
        ap = Decimal(str(raw_quote["ap"]))
        bs = int(raw_quote["bs"])
        as_ = int(raw_quote["as"])
        bx = str(raw_quote.get("bx", ""))
        ax = str(raw_quote.get("ax", ""))
        c = [str(cond) for cond in raw_quote.get("c", [])]
        z = str(raw_quote.get("z", ""))
    except (KeyError, ValueError, TypeError) as exc:
        raise DataContractError(f"MALFORMED_QUOTE_STRUCTURE: {exc}") from exc

    if bp <= Decimal("0") or ap <= Decimal("0"):
        raise DataContractError(f"NONPOSITIVE_NBBO_QUOTE: bid={bp}, ask={ap} at {t_str}.")

    spread = ap - bp
    is_locked = (ap == bp)
    is_crossed = (ap < bp)

    return Mec0015SipQuoteRecord(
        timestamp_utc=t_str,
        bid_price=bp,
        ask_price=ap,
        bid_size=bs,
        ask_size=as_,
        bid_exchange=bx,
        ask_exchange=ax,
        conditions=c,
        tape=z,
        spread=spread,
        is_locked=is_locked,
        is_crossed=is_crossed,
    )


def evaluate_boundary_quotes(
    session_date: date,
    boundary_time: time,
    raw_quotes_before: List[Dict[str, Any]],
    raw_quotes_after: List[Dict[str, Any]],
) -> Mec0015BoundaryQuotePair:
    """Evaluate quotes around an execution boundary T and select first valid quote >= T."""
    if session_date not in MEC_0015_AUTHORIZED_QUOTE_PROBE_DATES:
        raise DataContractError(
            f"UNAUTHORIZED_QUOTE_DATE: {session_date} is not in authorized probe set."
        )

    # Convert boundary date + time to UTC datetime
    dt_et = datetime.combine(session_date, boundary_time, tzinfo=NY_TZ)
    dt_utc = dt_et.astimezone(timezone.utc)
    boundary_iso = dt_utc.isoformat()

    quotes_before = [parse_sip_quote(q) for q in raw_quotes_before]
    quotes_after = [parse_sip_quote(q) for q in raw_quotes_after]

    if not quotes_after:
        raise DataContractError(
            f"NO_QUOTE_AT_OR_AFTER_BOUNDARY: Execution boundary {boundary_iso} has no quote >= T."
        )

    latest_before = quotes_before[-1] if quotes_before else None
    first_after = quotes_after[0]

    # Validate first quote
    if first_after.is_crossed:
        raise DataContractError(
            f"CROSSED_NBBO_AT_BOUNDARY: First quote >= T is crossed (ask={first_after.ask_price} < bid={first_after.bid_price})."
        )

    # Compute delay
    clean_ts = first_after.timestamp_utc.rstrip("Z")
    first_after_dt = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
    delay_ms = (first_after_dt - dt_utc).total_seconds() * 1000.0

    # Under PRIMARY_EXECUTION_MODEL: BUY at ask, SELL at bid
    buy_fill = first_after.ask_price
    sell_fill = first_after.bid_price

    return Mec0015BoundaryQuotePair(
        session_date=session_date.isoformat(),
        boundary_time_et=boundary_time.strftime("%H:%M:%S"),
        boundary_timestamp_utc=boundary_iso,
        latest_quote_before=latest_before,
        first_quote_at_or_after=first_after,
        quote_delay_ms=round(delay_ms, 3),
        simulated_buy_fill=buy_fill,
        simulated_sell_fill=sell_fill,
        is_valid=True,
    )
