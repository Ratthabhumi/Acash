"""MEC-0016 Historical SIP Quotes Early-M1 Qualification Contract.

Strict Invariants:
1. Endpoint: GET https://data.alpaca.markets/v2/stocks/quotes?symbols=SPY&feed=sip&sort=asc
2. Authorized Probe Dates Only: (2016-06-17, 2017-06-01, 2018-06-01).
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
6. Standalone Slippage:
   $0.001/share adverse per executed side.
7. Diagnostic: quote_delay_ms = (quote_timestamp - execution_boundary) in ms.
8. Zero Strategy Execution: No signal generation, no direction, no backtest, no P&L.
9. Credential Hygiene: Credentials and headers are never serialized or logged.
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

MEC_0016_AUTHORIZED_EARLY_QUOTE_PROBE_DATES: Sequence[date] = (
    date(2016, 6, 17),
    date(2017, 6, 1),
    date(2018, 6, 1),
)

MEC_0016_PROBE_DECISION_TIMES_ET: Sequence[time] = (
    time(10, 0, 0),
    time(12, 0, 0),
    time(15, 30, 0),
)

PRIMARY_EXECUTION_MODEL_NAME: str = "FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY"
SPREAD_MODEL_NAME: str = "EMBEDDED_IN_NBBO_FILL"


@dataclass(frozen=True)
class Mec0016SipQuoteRecord:
    """Parsed single historical SIP NBBO quote for MEC-0016."""

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
class Mec0016BoundaryQuotePair:
    """Boundary evaluation holding latest quote < T and first valid quote >= T."""

    session_date: str
    boundary_time_et: str
    boundary_timestamp_utc: str
    latest_quote_before: Optional[Mec0016SipQuoteRecord]
    first_quote_at_or_after: Mec0016SipQuoteRecord
    quote_delay_ms: float
    simulated_buy_fill: Decimal
    simulated_sell_fill: Decimal
    is_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date,
            "boundary_time_et": self.boundary_time_et,
            "boundary_timestamp_utc": self.boundary_timestamp_utc,
            "latest_quote_before": (
                self.latest_quote_before.to_dict() if self.latest_quote_before else None
            ),
            "first_quote_at_or_after": self.first_quote_at_or_after.to_dict(),
            "quote_delay_ms": round(self.quote_delay_ms, 3),
            "simulated_buy_fill": str(self.simulated_buy_fill),
            "simulated_sell_fill": str(self.simulated_sell_fill),
            "is_valid": self.is_valid,
        }


@dataclass(frozen=True)
class Mec0016QuoteContractReport:
    """Consolidated report for MEC-0016 early-M1 historical SIP quote probe."""

    endpoint: str
    symbol: str
    feed: str
    authorized_probe_dates: List[str]
    boundary_evaluations: List[Mec0016BoundaryQuotePair]
    latency_diagnostics: Dict[str, float]
    is_qualified: bool
    manifest_schema: str = "acash.research.mec_0016_early_quote_manifest.v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_schema": self.manifest_schema,
            "symbol": self.symbol,
            "endpoint": self.endpoint,
            "feed": self.feed,
            "authorized_probe_dates": self.authorized_probe_dates,
            "latency_diagnostics": self.latency_diagnostics,
            "is_qualified": self.is_qualified,
            "execution_contract": {
                "primary_execution_model": PRIMARY_EXECUTION_MODEL_NAME,
                "spread_model": SPREAD_MODEL_NAME,
                "explicit_half_spread_deduction_with_nbbo": "PROHIBITED",
                "standalone_slippage_model": "BASELINE_STANDALONE_SLIPPAGE = $0.001/share per executed side",
                "two_x_friction_stress_definition": (
                    "Retain observed NBBO fill, double non-spread explicit transaction costs, "
                    "and add adverse slippage stress equal to one observed half-spread per side."
                ),
            },
            "boundary_evaluations": [b.to_dict() for b in self.boundary_evaluations],
        }


# Historical R1 acceptable condition set (preserves R1 historical contract authority)
ACCEPTABLE_QUOTE_CONDITIONS = frozenset({"R", "?"})

# Amendment 001 execution conditions policy
ACCEPTABLE_EXECUTION_QUOTE_CONDITIONS = frozenset({"R"})
UNRESOLVED_PROVENANCE_QUOTE_CONDITIONS = frozenset({"?"})
REJECTED_QUOTE_CONDITIONS = frozenset({"N", "C", "L", "A", "B", "H", "E", "F", "U", "W", "4"})


def parse_alpaca_quote(
    raw: Dict[str, Any],
    allow_unresolved_provenance: bool = True,
    execution_mode: bool = False,
) -> Mec0016SipQuoteRecord:
    """Parse raw Alpaca quote record with strict validation.

    Enforces:
    - bid_price > 0 and ask_price > 0
    - bid_size > 0 and ask_size > 0
    - crossed market (bid > ask) is strictly rejected
    - locked market (bid == ask) is tracked (allowed for execution if liquid)
    - Under HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001:
      Condition '?' is classified as STRUCTURALLY_USABLE_BUT_CONDITION_PROVENANCE_UNRESOLVED.
      For dataset execution (allow_unresolved_provenance=False or execution_mode=True), '?' raises
      DataContractError fail-closed.
      For historical probe audit (allow_unresolved_provenance=True), '?' parses successfully.
      Only verified regular condition 'R' is unconditionally acceptable for execution.
      Unacceptable or unknown condition codes raise DataContractError fail-closed.
    """
    t_str = raw["t"]
    bp = Decimal(str(raw["bp"]))
    ap = Decimal(str(raw["ap"]))
    bs = int(raw["bs"])
    as_ = int(raw["as"])
    bx = str(raw.get("bx", ""))
    ax = str(raw.get("ax", ""))
    cond = [str(c) for c in raw.get("c", [])]
    tape = str(raw.get("z", "B"))

    if bp <= Decimal("0") or ap <= Decimal("0"):
        raise DataContractError(f"NONPOSITIVE_NBBO_QUOTE: bid={bp}, ask={ap} at {t_str}")

    if bs <= 0 or as_ <= 0:
        raise DataContractError(f"NONPOSITIVE_QUOTE_SIZE: bid_size={bs}, ask_size={as_} at {t_str}")

    spread = ap - bp
    is_locked = spread == Decimal("0")
    is_crossed = spread < Decimal("0")

    if is_crossed:
        raise DataContractError(f"CROSSED_NBBO_QUOTE: bid={bp} > ask={ap} at {t_str}")

    is_exec = execution_mode or (not allow_unresolved_provenance)

    for c_code in cond:
        if c_code in REJECTED_QUOTE_CONDITIONS:
            raise DataContractError(f"UNACCEPTABLE_QUOTE_CONDITION: condition '{c_code}' is rejected at {t_str}")
        if c_code in UNRESOLVED_PROVENANCE_QUOTE_CONDITIONS:
            if is_exec:
                raise DataContractError(
                    f"UNRESOLVED_QUOTE_CONDITION_PROVENANCE: condition '{c_code}' lacks granular "
                    f"CTA provenance under Amendment 001 at {t_str}"
                )
        elif c_code not in ACCEPTABLE_EXECUTION_QUOTE_CONDITIONS:
            raise DataContractError(f"UNKNOWN_QUOTE_CONDITION: condition '{c_code}' is unmapped/fail-closed at {t_str}")

    return Mec0016SipQuoteRecord(
        timestamp_utc=t_str,
        bid_price=bp,
        ask_price=ap,
        bid_size=bs,
        ask_size=as_,
        bid_exchange=bx,
        ask_exchange=ax,
        conditions=cond,
        tape=tape,
        spread=spread,
        is_locked=is_locked,
        is_crossed=is_crossed,
    )


def qualify_alpaca_quote_for_r2_execution(raw: Dict[str, Any]) -> Mec0016SipQuoteRecord:
    """Pre-R2 qualification layer: validate quote for actual R2 dataset execution.

    Rejects '?' fail-closed under HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.
    """
    return parse_alpaca_quote(raw, allow_unresolved_provenance=False, execution_mode=True)


def evaluate_boundary_quotes(
    session_date: date,
    boundary_time: time,
    quotes_before: List[Dict[str, Any]],
    quotes_after: List[Dict[str, Any]],
    allow_unresolved_provenance: bool = True,
) -> Mec0016BoundaryQuotePair:
    """Evaluate candidate quotes around a decision boundary T."""
    if session_date not in MEC_0016_AUTHORIZED_EARLY_QUOTE_PROBE_DATES:
        raise DataContractError(f"Unauthorized probe date: {session_date}")
    if boundary_time not in MEC_0016_PROBE_DECISION_TIMES_ET:
        raise DataContractError(f"Unauthorized boundary time: {boundary_time}")

    boundary_dt_et = datetime.combine(session_date, boundary_time, tzinfo=NY_TZ)
    boundary_dt_utc = boundary_dt_et.astimezone(timezone.utc)

    latest_before: Optional[Mec0016SipQuoteRecord] = None
    if quotes_before:
        valid_before = [q for q in quotes_before if Decimal(str(q["bp"])) > 0 and Decimal(str(q["ap"])) > 0]
        if valid_before:
            latest_before = parse_alpaca_quote(
                valid_before[-1], allow_unresolved_provenance=allow_unresolved_provenance
            )

    if not quotes_after:
        raise DataContractError(f"No quotes returned at or after {session_date} {boundary_time}")

    valid_after = [q for q in quotes_after if Decimal(str(q["bp"])) > 0 and Decimal(str(q["ap"])) > 0]
    if not valid_after:
        raise DataContractError(f"No valid non-zero quotes at or after {session_date} {boundary_time}")

    first_after = parse_alpaca_quote(
        valid_after[0], allow_unresolved_provenance=allow_unresolved_provenance
    )

    t_str = first_after.timestamp_utc
    if t_str.endswith("Z"):
        t_str_clean = t_str[:-1] + "+00:00"
    else:
        t_str_clean = t_str

    if "." in t_str_clean:
        prefix, rest = t_str_clean.split(".", 1)
        nano_part, tz_part = rest.split("+", 1) if "+" in rest else (rest, "00:00")
        micro_part = nano_part[:6].ljust(6, "0")
        dt_first = datetime.fromisoformat(f"{prefix}.{micro_part}+{tz_part}")
    else:
        dt_first = datetime.fromisoformat(t_str_clean)

    delay_ms = max(0.0, (dt_first - boundary_dt_utc).total_seconds() * 1000.0)

    buy_fill = first_after.ask_price
    sell_fill = first_after.bid_price

    return Mec0016BoundaryQuotePair(
        session_date=session_date.isoformat(),
        boundary_time_et=boundary_time.strftime("%H:%M:%S"),
        boundary_timestamp_utc=boundary_dt_utc.isoformat(),
        latest_quote_before=latest_before,
        first_quote_at_or_after=first_after,
        quote_delay_ms=delay_ms,
        simulated_buy_fill=buy_fill,
        simulated_sell_fill=sell_fill,
        is_valid=True,
    )
