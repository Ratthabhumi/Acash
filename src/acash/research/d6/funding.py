"""D6 V36 cross-border funding model (pure, Decimal, fail-closed).

An investor saves THB on each monthly contribution date (the THB equivalent of
a USD scenario amount at that date's H.10 rate) and remits the accumulated THB
to the broker on a fixed cadence, paying a sender fee, a conversion spread over
H.10 and an optional intermediary fee. Remitted USD is credited to the broker a
fixed number of NYSE sessions later and becomes a D6 contribution. Fees are
current published schedules applied retrospectively; spreads are hypothetical;
H.10 is a reference rate, not a retail bank rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, Decimal
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.d6.contributions import h10_rate, monthly_contribution_schedule

ZERO = Decimal("0")
CENT = Decimal("0.01")
# Existing V36 tolerance for reassociation of Decimal division, not a cash floor.
DECIMAL_DIVISION_TOLERANCE = Decimal("1e-18")


def _money(value: Decimal, context: str, *, positive: bool = False) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < ZERO or (positive and value == ZERO):
        raise DataContractError(f"FUNDING_INVALID_MONEY: {context}.")


def _rate(rates: Mapping[date, Decimal], day: date) -> Tuple[Decimal, bool]:
    rate, flagged = h10_rate(rates, day)
    _money(rate, "FX rate", positive=True)
    return rate, flagged


@dataclass(frozen=True)
class FundingScenario:
    label: str
    cadence: Optional[int] = None
    sender_fee_thb: Decimal = ZERO
    fx_spread: Decimal = ZERO
    intermediary_fee_usd: Decimal = ZERO
    delay_sessions: int = 0

    def __post_init__(self) -> None:
        if self.cadence is not None and (type(self.cadence) is not int or self.cadence < 1):
            raise DataContractError(f"FUNDING_BAD_CADENCE: {self.cadence}.")
        for value in (self.sender_fee_thb, self.intermediary_fee_usd, self.fx_spread):
            _money(value, "scenario cost")
        if min(self.sender_fee_thb, self.intermediary_fee_usd) < ZERO or not ZERO <= self.fx_spread < Decimal("1"):
            raise DataContractError("FUNDING_BAD_COST_PARAMETER.")
        if type(self.delay_sessions) is not int or self.delay_sessions < 0:
            raise DataContractError("FUNDING_NEGATIVE_DELAY.")
        if self.cadence is None and (
            self.sender_fee_thb or self.fx_spread or self.intermediary_fee_usd or self.delay_sessions
        ):
            raise DataContractError("FUNDING_FRICTIONLESS_WITH_COSTS.")


@dataclass(frozen=True)
class Remittance:
    remit_session: date
    credit_session: Optional[date]
    thb_balance: Decimal
    rate: Decimal
    sender_fee_usd_ref: Decimal
    spread_cost_usd: Decimal
    intermediary_fee_usd: Decimal
    rounding_usd: Decimal
    usd_delivered: Decimal
    saved_usd_ref: Decimal


@dataclass
class FundingPlan:
    scenario: FundingScenario
    savings: List[Tuple[date, Decimal, Decimal]] = field(default_factory=list)
    remittances: List[Remittance] = field(default_factory=list)
    contributions: Dict[date, Decimal] = field(default_factory=dict)
    unremitted_thb: Decimal = ZERO
    unremitted_saved_usd_ref: Decimal = ZERO
    in_transit_usd: Decimal = ZERO
    mean_unremitted_thb: Decimal = ZERO
    prior_rate_uses: int = 0


def plan_funding(
    sessions: Sequence[date],
    usd_monthly: Decimal,
    rates: Mapping[date, Decimal],
    scenario: FundingScenario,
) -> FundingPlan:
    """Legacy USD-native entry point; retain exact F0 USD contributions."""
    _money(usd_monthly, "monthly USD")
    ordered = list(sessions)
    schedule = monthly_contribution_schedule(ordered, usd_monthly)
    plan = FundingPlan(scenario)
    for day in sorted(schedule):
        rate, flagged = _rate(rates, day)
        plan.prior_rate_uses += int(flagged)
        plan.savings.append((day, schedule[day] * rate, rate))
    if scenario.cadence is None:
        plan.contributions = dict(schedule)
        reconcile_funding(plan)
        return plan

    return _plan_remittances(ordered, rates, plan)


def plan_funding_thb(
    sessions: Sequence[date], thb_monthly: Decimal,
    rates: Mapping[date, Decimal], scenario: FundingScenario,
) -> FundingPlan:
    """Exactly fixed THB saving events on the established monthly schedule."""
    _money(thb_monthly, "monthly THB")
    savings = list(monthly_contribution_schedule(sessions, thb_monthly).items())
    return plan_savings_thb(sessions, savings, rates, scenario)


def plan_savings_thb(
    sessions: Sequence[date], savings: Sequence[Tuple[date, Decimal]],
    rates: Mapping[date, Decimal], scenario: FundingScenario,
) -> FundingPlan:
    """Validated dated THB ledger; same remittance authority as legacy USD."""
    ordered = list(sessions)
    monthly_contribution_schedule(ordered, ZERO)  # canonical order/uniqueness check
    calendar = NyseCa1Calendar()
    if any(not calendar.is_trading_session(day) for day in ordered):
        raise DataContractError("FUNDING_NON_TRADING_SESSION.")
    if scenario.cadence is None:
        raise DataContractError("FUNDING_THB_REQUIRES_EXPLICIT_CADENCE.")
    days = [d for d, _ in savings]
    if days != sorted(set(days)) or not set(days).issubset(ordered):
        raise DataContractError("FUNDING_SAVINGS_MUST_BE_UNIQUE_CHRONOLOGICAL_SESSIONS.")
    plan = FundingPlan(scenario)
    for day, amount in savings:
        _money(amount, "THB savings event", positive=True)
        rate, flagged = _rate(rates, day)
        plan.prior_rate_uses += int(flagged)
        plan.savings.append((day, amount, rate))
    return _plan_remittances(ordered, rates, plan)


def _plan_remittances(
    ordered: Sequence[date], rates: Mapping[date, Decimal], plan: FundingPlan,
) -> FundingPlan:
    scenario = plan.scenario
    if scenario.cadence is None:
        raise DataContractError("FUNDING_MISSING_REMITTANCE_CADENCE.")

    index = {s: i for i, s in enumerate(ordered)}
    balance, saved_ref, balance_sum = ZERO, ZERO, ZERO
    saving_by_day = {d: (thb, rate) for d, thb, rate in plan.savings}
    count = 0
    for session in ordered:
        if session in saving_by_day:
            thb, rate = saving_by_day[session]
            balance += thb
            saved_ref += thb / rate
            count += 1
            if count % scenario.cadence == 0:
                remitted = _remit(session, balance, saved_ref, rates, scenario, ordered, index, plan)
                if remitted:
                    balance, saved_ref = ZERO, ZERO
        balance_sum += balance
    plan.unremitted_thb = balance
    plan.unremitted_saved_usd_ref = saved_ref
    plan.mean_unremitted_thb = balance_sum / Decimal(len(ordered))
    reconcile_funding(plan)
    return plan


def _remit(
    session: date,
    balance: Decimal,
    saved_ref: Decimal,
    rates: Mapping[date, Decimal],
    scenario: FundingScenario,
    ordered: Sequence[date],
    index: Mapping[date, int],
    plan: FundingPlan,
) -> bool:
    rate, flagged = _rate(rates, session)
    plan.prior_rate_uses += int(flagged)
    net_thb = balance - scenario.sender_fee_thb
    if net_thb <= ZERO:
        return False
    at_reference = net_thb / rate
    converted = net_thb / (rate * (1 + scenario.fx_spread))
    gross_usd = converted - scenario.intermediary_fee_usd
    if gross_usd <= ZERO:
        return False
    delivered = gross_usd.quantize(CENT, rounding=ROUND_DOWN)
    if delivered <= ZERO:
        return False
    target = index[session] + scenario.delay_sessions
    credit = ordered[target] if target < len(ordered) else None
    if credit is None:
        plan.in_transit_usd += delivered
    else:
        plan.contributions[credit] = plan.contributions.get(credit, ZERO) + delivered
    plan.remittances.append(
        Remittance(
            remit_session=session,
            credit_session=credit,
            thb_balance=balance,
            rate=rate,
            sender_fee_usd_ref=scenario.sender_fee_thb / rate,
            spread_cost_usd=at_reference - converted,
            intermediary_fee_usd=scenario.intermediary_fee_usd,
            rounding_usd=gross_usd - delivered,
            usd_delivered=delivered,
            saved_usd_ref=saved_ref,
        )
    )
    return True


def reconcile_funding(plan: FundingPlan) -> Dict[str, Decimal]:
    """Independent cash partitions, not performance or a compensating adjustment."""
    days = [d for d, _, _ in plan.savings]
    if days != sorted(set(days)):
        raise DataContractError("FUNDING_DUPLICATE_OR_UNORDERED_LEDGER.")
    for _, amount, rate in plan.savings:
        _money(amount, "saved principal", positive=True)
        _money(rate, "saving FX rate", positive=True)
    saved = sum((a for _, a, _ in plan.savings), ZERO)
    remitted = sum((r.thb_balance for r in plan.remittances), ZERO)
    direct = saved if plan.scenario.cadence is None else ZERO
    for value in (saved, remitted, plan.unremitted_thb, plan.unremitted_saved_usd_ref,
                  plan.in_transit_usd, plan.mean_unremitted_thb, *plan.contributions.values()):
        _money(value, "ledger balance")
    if saved != remitted + plan.unremitted_thb + direct:
        raise DataContractError("FUNDING_THB_CONSERVATION_FAILED.")
    credited: Dict[date, Decimal] = {}
    transit = ZERO
    for rem in plan.remittances:
        for value in (rem.thb_balance, rem.rate, rem.usd_delivered, rem.saved_usd_ref):
            _money(value, "remittance principal/rate", positive=True)
        for value in (rem.sender_fee_usd_ref, rem.spread_cost_usd, rem.intermediary_fee_usd, rem.rounding_usd):
            _money(value, "remittance friction")
        costs = rem.sender_fee_usd_ref + rem.spread_cost_usd + rem.intermediary_fee_usd + rem.rounding_usd
        if abs(rem.thb_balance / rem.rate - rem.usd_delivered - costs) > DECIMAL_DIVISION_TOLERANCE:
            raise DataContractError("FUNDING_REMITTANCE_CONSERVATION_FAILED.")
        if abs(rem.sender_fee_usd_ref * rem.rate - plan.scenario.sender_fee_thb) > DECIMAL_DIVISION_TOLERANCE:
            raise DataContractError("FUNDING_SENDER_FEE_MISMATCH.")
        if rem.intermediary_fee_usd != plan.scenario.intermediary_fee_usd:
            raise DataContractError("FUNDING_INTERMEDIARY_FEE_MISMATCH.")
        if rem.credit_session is None:
            transit += rem.usd_delivered
        else:
            if rem.credit_session < rem.remit_session:
                raise DataContractError("FUNDING_CREDIT_BEFORE_REMITTANCE.")
            credited[rem.credit_session] = credited.get(rem.credit_session, ZERO) + rem.usd_delivered
    if plan.scenario.cadence is None:
        if plan.remittances or plan.unremitted_thb or plan.in_transit_usd:
            raise DataContractError("FUNDING_DIRECT_USD_HAS_EXTERNAL_BALANCE.")
        expected = {d: amount / rate for d, amount, rate in plan.savings}
        if set(expected) != set(plan.contributions) or any(
            abs(amount - plan.contributions[d]) > DECIMAL_DIVISION_TOLERANCE for d, amount in expected.items()
        ):
            raise DataContractError("FUNDING_DIRECT_USD_CONSERVATION_FAILED.")
    elif credited != plan.contributions or transit != plan.in_transit_usd:
        raise DataContractError("FUNDING_CREDIT_TRANSIT_CONSERVATION_FAILED.")
    if plan.scenario.cadence is not None:
        saved_ref = sum((amount / rate for _, amount, rate in plan.savings), ZERO)
        assigned_ref = sum((r.saved_usd_ref for r in plan.remittances), ZERO) + plan.unremitted_saved_usd_ref
        if abs(saved_ref - assigned_ref) > DECIMAL_DIVISION_TOLERANCE:
            raise DataContractError("FUNDING_SAVING_REFERENCE_CONSERVATION_FAILED.")
    return {
        "total_saved_thb": saved, "total_remitted_thb": remitted, "direct_funded_thb": direct,
        "credited_usd": sum(plan.contributions.values(), ZERO), "in_transit_usd": transit,
        "unremitted_thb": plan.unremitted_thb,
        "sender_fees_thb": sum((r.sender_fee_usd_ref * r.rate for r in plan.remittances), ZERO),
        "intermediary_fees_usd": sum((r.intermediary_fee_usd for r in plan.remittances), ZERO),
        "fx_spread_usd": sum((r.spread_cost_usd for r in plan.remittances), ZERO),
        "rounding_usd": sum((r.rounding_usd for r in plan.remittances), ZERO),
    }


__all__ = ["FundingPlan", "FundingScenario", "Remittance", "plan_funding", "plan_funding_thb", "plan_savings_thb", "reconcile_funding"]
