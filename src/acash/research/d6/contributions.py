"""D6 V35 contribution-study primitives (pure, Decimal, fail-closed).

External cash flows are first-class ledger events in ``run_d6_portfolio``; this
module only schedules them and measures flow-aware performance:

- time-weighted return index (flows credited at the start of a session);
- XIRR (ACT/365) where the cash-flow sign pattern makes it unique;
- translation of USD flows into THB at Federal Reserve H.10 noon rates with
  labelled hypothetical conversion spreads.

Dollar wealth across different contribution levels is not a skill measure.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import D6Result

ZERO = Decimal("0")
XIRR_LOW = -0.99
XIRR_HIGH = 10.0
_H10_ROW = re.compile(r"^\|\s*(\d{1,2}-[A-Z]{3}-\d{2})\s*\|\s*([0-9.]+|ND)\s*\|\s*$")


def monthly_contribution_schedule(sessions: Sequence[date], amount: Decimal) -> Dict[date, Decimal]:
    """First admitted session of each month after the initial-investment month."""
    if amount < ZERO:
        raise DataContractError(f"CONTRIB_NEGATIVE_AMOUNT: {amount}.")
    ordered = list(sessions)
    if not ordered or ordered != sorted(set(ordered)):
        raise DataContractError("CONTRIB_SESSIONS_MUST_BE_UNIQUE_CHRONOLOGICAL.")
    if amount == ZERO:
        return {}
    initial_month = (ordered[0].year, ordered[0].month)
    firsts: Dict[Tuple[int, int], date] = {}
    for session in ordered:
        firsts.setdefault((session.year, session.month), session)
    return {day: amount for month, day in firsts.items() if month != initial_month}


def twr_index(result: D6Result, initial_nav: Decimal) -> List[Decimal]:
    """Chained index with r_t = NAV_t / (NAV_{t-1} + CF_t) - 1, base ``initial_nav``."""
    flows = dict(result.contributions)
    if len(flows) != len(result.contributions):
        raise DataContractError("TWR_DUPLICATE_CONTRIBUTION_SESSION.")
    index: List[Decimal] = []
    prior_nav, level = initial_nav, initial_nav
    for record in result.nav_curve:
        start = prior_nav + flows.pop(record.session, ZERO)
        if start <= ZERO:
            raise DataContractError(f"TWR_NONPOSITIVE_START_VALUE: {record.session}.")
        level = level * record.nav / start
        index.append(level)
        prior_nav = record.nav
    if flows:
        raise DataContractError(f"TWR_FLOW_OUTSIDE_CURVE: {sorted(flows)[0]}.")
    return index


def xirr(flows: Sequence[Tuple[date, Decimal]]) -> float:
    """Annual IRR (ACT/365) for outflows followed by one terminal inflow.

    Only the pattern "all non-positive, then one positive final flow" is
    accepted; it has exactly one sign change, hence a unique root.
    """
    if len(flows) < 2:
        raise DataContractError("XIRR_TOO_FEW_FLOWS.")
    days = [d for d, _ in flows]
    if days != sorted(days):
        raise DataContractError("XIRR_FLOWS_NOT_CHRONOLOGICAL.")
    if any(a > ZERO for _, a in flows[:-1]) or flows[-1][1] <= ZERO or all(a == ZERO for _, a in flows[:-1]):
        raise DataContractError("XIRR_UNDEFINED_SIGN_PATTERN.")
    if days[-1] == days[0]:
        raise DataContractError("XIRR_ZERO_HORIZON.")
    t0 = days[0]
    terms = [((d - t0).days / 365.0, float(a)) for d, a in flows]

    def npv(rate: float) -> float:
        return float(sum(a * (1.0 + rate) ** (-t) for t, a in terms))

    low, high = XIRR_LOW, XIRR_HIGH
    f_low, f_high = npv(low), npv(high)
    if f_low == 0.0:
        return low
    if f_low * f_high > 0.0:
        raise DataContractError("XIRR_ROOT_NOT_BRACKETED.")
    for _ in range(200):
        mid = (low + high) / 2.0
        f_mid = npv(mid)
        if f_mid == 0.0 or high - low < 1e-12:
            return mid
        if (f_mid > 0.0) == (f_low > 0.0):
            low, f_low = mid, f_mid
        else:
            high = mid
    return (low + high) / 2.0


def investor_flows(result: D6Result, initial_nav: Decimal) -> List[Tuple[date, Decimal]]:
    """Investor-view flows: -initial, -contributions, +terminal NAV."""
    if not result.nav_curve:
        raise DataContractError("XIRR_EMPTY_NAV_CURVE.")
    first, last = result.nav_curve[0].session, result.nav_curve[-1].session
    flows = [(first, -initial_nav)] + [(d, -a) for d, a in result.contributions]
    flows.append((last, result.nav_curve[-1].nav))
    return flows


def cash_drag(result: D6Result) -> Tuple[Decimal, Decimal]:
    """(mean cash share of NAV over sessions, terminal uninvested cash)."""
    if not result.nav_curve:
        raise DataContractError("CASH_DRAG_EMPTY_NAV_CURVE.")
    shares = []
    for record in result.nav_curve:
        if record.nav <= ZERO:
            raise DataContractError(f"CASH_DRAG_NONPOSITIVE_NAV: {record.session}.")
        shares.append(record.cash / record.nav)
    return sum(shares, ZERO) / Decimal(len(shares)), result.nav_curve[-1].cash


def reconcile_cash(result: D6Result, initial_nav: Decimal) -> Dict[str, Decimal]:
    """Independent cash identity from the ledgers; raises on any mismatch."""
    last = result.nav_curve[-1].session
    buys = sum((t.notional for t in result.trades if t.side == "BUY"), ZERO)
    sells = sum((t.notional for t in result.trades if t.side == "SELL"), ZERO)
    fees = sum((t.commission + t.regulatory_fees for t in result.trades), ZERO)
    distributions = sum((e.gross - e.withheld for e in result.entitlements if e.payable_date <= last), ZERO)
    contributed = sum((a for _, a in result.contributions), ZERO)
    ending = initial_nav + contributed - buys + sells - fees + distributions
    if ending != result.ending_cash or contributed != result.contributed:
        raise DataContractError("CONTRIB_CASH_RECONCILIATION_FAILED.")
    return {
        "beginning_cash": initial_nav,
        "contributions": contributed,
        "buys": buys,
        "sells": sells,
        "fees": fees,
        "distributions": distributions,
        "ending_cash": ending,
    }


def parse_h10_rates(text: str) -> Dict[date, Decimal]:
    """Parse ``| D-MON-YY | rate |`` rows of an H.10 historical page; ``ND`` skipped."""
    rates: Dict[date, Decimal] = {}
    for line in text.splitlines():
        match = _H10_ROW.match(line.strip())
        if not match:
            continue
        day = datetime.strptime(match.group(1).title(), "%d-%b-%y").date()
        if day in rates:
            raise DataContractError(f"H10_DUPLICATE_DATE: {day}.")
        if match.group(2) == "ND":
            continue
        rate = Decimal(match.group(2))
        if rate <= ZERO:
            raise DataContractError(f"H10_NONPOSITIVE_RATE: {day}.")
        rates[day] = rate
    if not rates:
        raise DataContractError("H10_NO_RATES_PARSED.")
    return rates


def h10_rate(rates: Mapping[date, Decimal], day: date, max_gap_days: int = 7) -> Tuple[Decimal, bool]:
    """Rate on ``day`` or the latest prior published rate (flagged), within a bounded gap."""
    if day in rates:
        return rates[day], False
    prior = [d for d in rates if d < day and (day - d).days <= max_gap_days]
    if not prior:
        raise DataContractError(f"H10_NO_RATE_WITHIN_{max_gap_days}D: {day}.")
    return rates[max(prior)], True


def thb_view(
    flows: Sequence[Tuple[date, Decimal]],
    rates: Mapping[date, Decimal],
    *,
    funding_spread: Decimal,
    liquidation_spread: Decimal,
) -> Dict[str, object]:
    """THB investor flows: USD bought at rate x (1 + funding spread), terminal
    USD sold at rate x (1 - liquidation spread). Spreads are hypothetical."""
    if not (ZERO <= funding_spread < Decimal("1") and ZERO <= liquidation_spread < Decimal("1")):
        raise DataContractError("THB_BAD_SPREAD.")
    thb: List[Tuple[date, Decimal]] = []
    prior_rate_uses = 0
    for i, (day, usd) in enumerate(flows):
        rate, flagged = h10_rate(rates, day)
        prior_rate_uses += int(flagged)
        factor = (1 - liquidation_spread) if i == len(flows) - 1 else (1 + funding_spread)
        thb.append((day, usd * rate * factor))
    return {
        "thb_contributed": -sum((a for _, a in thb[:-1]), ZERO),
        "thb_terminal": thb[-1][1],
        "thb_xirr": xirr(thb),
        "prior_h10_rate_uses": prior_rate_uses,
    }


__all__ = [
    "cash_drag",
    "h10_rate",
    "investor_flows",
    "monthly_contribution_schedule",
    "parse_h10_rates",
    "reconcile_cash",
    "thb_view",
    "twr_index",
    "xirr",
]
