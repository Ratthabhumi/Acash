"""Flow-aware portfolio performance on reconciled transaction histories (read-only).

TWR chain-linking and XIRR reuse the D6 authorities (``twr_levels``, ``xirr``).
Performance is reported only when the history is reconciled and a valuation
exists at the start, at every external-flow date and at the end; otherwise the
status says why it is not established. Benchmark comparison and FX attribution
are not computed in V2.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.ppds.transactions import LedgerState
from acash.research.d6.contributions import twr_levels, xirr

ZERO = Decimal("0")
TWR_METHOD = "CHAIN_LINKED_FLOW_AT_START_OF_PERIOD (r_t = V_t / (V_{t-1} + CF_t) - 1)"
XIRR_METHOD = "ACT/365 bisection; unique root only for outflows followed by one terminal inflow"


def external_flows_in(state: LedgerState, reporting_currency: str,
                      fx: Mapping[Tuple[date, str], Decimal]) -> Dict[date, Decimal]:
    """DEPOSIT/WITHDRAWAL per date in reporting currency; internal transfers and FX are not flows."""
    totals: Dict[date, Decimal] = {}
    for day, _, ccy, amount in state.external_flows:
        if ccy == reporting_currency:
            rate = Decimal("1")
        elif (day, ccy) in fx:
            rate = fx[(day, ccy)]
        else:
            raise DataContractError(f"PERF_FX_MISSING: {ccy}->{reporting_currency} on {day.isoformat()}.")
        if not rate.is_finite() or rate <= ZERO:
            raise DataContractError(f"PERF_FX_INVALID: {ccy} on {day.isoformat()}.")
        totals[day] = totals.get(day, ZERO) + amount * rate
    return totals


def _not_established(reason: str, **extra: Any) -> Dict[str, Any]:
    return {"status": "PERFORMANCE_NOT_ESTABLISHED", "reason": reason, **extra}


def performance_report(state: LedgerState, support_state: str, valuations: Sequence[Tuple[date, Decimal]],
                       reporting_currency: str, fx: Mapping[Tuple[date, str], Decimal]) -> Dict[str, Any]:
    """TWR, XIRR and income for a reconciled history with explicit valuation points."""
    base = {
        "reporting_currency": reporting_currency,
        "income_and_costs_by_currency": {k: {c: str(v) for c, v in sorted(m.items())} for k, m in sorted(state.income.items())},
        "realized": list(state.realized),
        "benchmark": "BENCHMARK_NOT_EVALUATED: requires a matched-date, same-currency, flow-matched benchmark series",
        "fx_attribution": "FX_ATTRIBUTION_NOT_ESTABLISHED",
        "twr_method": TWR_METHOD,
        "xirr_method": XIRR_METHOD,
    }
    if support_state != "TRANSACTIONS_RECONCILED":
        return {**base, **_not_established(f"SUPPORT_STATE_{support_state}")}
    points = sorted(valuations)
    days = [d for d, _ in points]
    if len(points) < 2 or len(set(days)) != len(days):
        return {**base, **_not_established("VALUATIONS_INSUFFICIENT_OR_DUPLICATED")}
    if any((not v.is_finite()) or v <= ZERO for _, v in points):
        raise DataContractError("PERF_VALUATION_NONPOSITIVE.")
    start, end = points[0][0], points[-1][0]
    if start < state.history_start or end != state.as_of:
        return {**base, **_not_established("VALUATIONS_OUTSIDE_HISTORY: start must be >= first transaction, end == replay as_of")}
    flows = external_flows_in(state, reporting_currency, fx)
    early = sorted(d for d in flows if d <= start)
    if early:
        return {**base, **_not_established("FLOW_ON_OR_BEFORE_FIRST_VALUATION", dates=[d.isoformat() for d in early])}
    missing = sorted(d for d in flows if d not in set(days))
    if missing:
        return {**base, **_not_established("VALUATION_MISSING_AT_FLOW_DATES", dates=[d.isoformat() for d in missing])}

    levels = twr_levels(points[0][1], points[1:], flows)
    twr = levels[-1] / points[0][1] - 1
    investor: List[Tuple[date, Decimal]] = [(start, -points[0][1])]
    investor += [(d, -flows[d]) for d in sorted(flows)]
    investor.append((end, points[-1][1]))
    try:
        irr: Dict[str, Any] = {"status": "ESTABLISHED", "value": f"{xirr(investor):.10f}"}
    except DataContractError as exc:
        irr = {"status": "XIRR_NOT_ESTABLISHED", "reason": str(exc).split(":")[0].rstrip(".")}
    contributions = sum((v for v in flows.values() if v > ZERO), ZERO)
    withdrawals = sum((v for v in flows.values() if v < ZERO), ZERO)
    return {
        **base,
        "status": "PERFORMANCE_QUALIFIED",
        "period": {"start": start.isoformat(), "end": end.isoformat(), "days": (end - start).days},
        "beginning_value": str(points[0][1]),
        "ending_value": str(points[-1][1]),
        "external_contributions": str(contributions),
        "external_withdrawals": str(withdrawals),
        "value_change_excluding_flows": str(points[-1][1] - points[0][1] - contributions - withdrawals),
        "twr_cumulative": f"{twr:.10f}",
        "xirr_annual": irr,
        "opening_balances": list(state.opening_balances),
    }
