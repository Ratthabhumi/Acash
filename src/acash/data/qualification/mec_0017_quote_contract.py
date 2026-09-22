"""MEC-0017 Historical Direct-SIP Quote Execution Contract (HYP_007).

Strict Invariants:
1. Endpoint: GET https://data.alpaca.markets/v2/stocks/quotes?symbols=SPY&feed=sip&sort=asc
2. Direct-SIP Provenance: Sample start is 2021-07-01 (post-transition direct SIP capture).
   Sample end is 2024-04-30 (M1 terminal publication-exposed date).
   Any date >= 2024-05-01 is firewalled under M2 locked access.
3. Decision Boundaries: 10:00 ET through 15:30 ET every 30 minutes, plus 15:59 ET forced flatten.
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
7. Quote Condition Enforcement:
   - Acceptable: {'R'} (Regular, Two-Sided Open Quote).
   - Rejected: {'?', 'N', 'C', 'L', 'A', 'B', 'H', 'E', 'F', 'U', 'W', '4'}.
   - Condition '?' is strictly rejected fail-closed with zero exception.
   - Unknown conditions fail closed immediately.
8. Zero Strategy Execution: No signal generation, no direction, no backtest, no P&L.
9. Credential Hygiene: Credentials and headers are never serialized or logged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError

NY_TZ = ZoneInfo("America/New_York")

MEC_0017_M1_START_DATE = date(2021, 7, 1)
MEC_0017_M1_END_DATE = date(2024, 4, 30)

PRIMARY_EXECUTION_MODEL_NAME: str = "FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY"
SPREAD_MODEL_NAME: str = "EMBEDDED_IN_NBBO_FILL"

ACCEPTABLE_EXECUTION_QUOTE_CONDITIONS = frozenset({"R"})
REJECTED_QUOTE_CONDITIONS = frozenset({"?", "N", "C", "L", "A", "B", "H", "E", "F", "U", "W", "4"})


@dataclass(frozen=True)
class Mec0017SipQuoteRecord:
    """Parsed single historical Direct-SIP NBBO quote for MEC-0017."""

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


def parse_alpaca_direct_sip_quote(raw: Dict[str, Any]) -> Mec0017SipQuoteRecord:
    """Parse raw Alpaca quote record with strict MEC-0017 direct-SIP validation.

    Enforces:
    - bid_price > 0 and ask_price > 0
    - bid_size > 0 and ask_size > 0
    - crossed market (bid > ask) is strictly rejected
    - locked market (bid == ask) is tracked (allowed for execution if liquid)
    - Condition code '?' is strictly prohibited and raises DataContractError fail-closed.
    - Only verified regular condition 'R' is acceptable.
    - Unacceptable or unknown condition codes raise DataContractError fail-closed.
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

    for c_code in cond:
        if c_code == "?":
            raise DataContractError(
                f"UNRESOLVED_QUOTE_CONDITION_PROVENANCE: condition '?' is strictly prohibited under MEC-0017 at {t_str}"
            )
        if c_code in REJECTED_QUOTE_CONDITIONS:
            raise DataContractError(f"UNACCEPTABLE_QUOTE_CONDITION: condition '{c_code}' is rejected at {t_str}")
        if c_code not in ACCEPTABLE_EXECUTION_QUOTE_CONDITIONS:
            raise DataContractError(f"UNKNOWN_QUOTE_CONDITION: condition '{c_code}' is unmapped/fail-closed at {t_str}")

    return Mec0017SipQuoteRecord(
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
