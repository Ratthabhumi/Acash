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
from acash.research.d6.contributions import h10_rate, monthly_contribution_schedule

ZERO = Decimal("0")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class FundingScenario:
    label: str
    cadence: Optional[int] = None
    sender_fee_thb: Decimal = ZERO
    fx_spread: Decimal = ZERO
    intermediary_fee_usd: Decimal = ZERO
    delay_sessions: int = 0

    def __post_init__(self) -> None:
        if self.cadence is not None and self.cadence < 1:
            raise DataContractError(f"FUNDING_BAD_CADENCE: {self.cadence}.")
        if min(self.sender_fee_thb, self.intermediary_fee_usd) < ZERO or not ZERO <= self.fx_spread < Decimal("1"):
            raise DataContractError("FUNDING_BAD_COST_PARAMETER.")
        if self.delay_sessions < 0:
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
    ordered = list(sessions)
    schedule = monthly_contribution_schedule(ordered, usd_monthly)
    plan = FundingPlan(scenario)
    for day in sorted(schedule):
        rate, flagged = h10_rate(rates, day)
        plan.prior_rate_uses += int(flagged)
        plan.savings.append((day, schedule[day] * rate, rate))
    if scenario.cadence is None:
        plan.contributions = dict(schedule)
        return plan

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
    rate, flagged = h10_rate(rates, session)
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


__all__ = ["FundingPlan", "FundingScenario", "Remittance", "plan_funding"]
