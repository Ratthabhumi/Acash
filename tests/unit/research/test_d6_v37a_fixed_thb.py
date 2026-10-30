"""V37A native savings, independent conservation and legacy metamorphism."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.funding import (
    FundingScenario, plan_funding, plan_funding_thb, plan_savings_thb, reconcile_funding,
)
from acash.research.d6.local_exploratory import official_sessions

S = official_sessions(date(2023, 12, 27), date(2024, 7, 3))
RATES = {s: D('35') + D(i) / 100 for i, s in enumerate(S)}


def test_exact_native_savings_and_119_events() -> None:
    plan = plan_funding_thb(S, D('1000'), RATES, FundingScenario('Q', cadence=3))
    assert len(plan.savings) == 7
    assert {a for _, a, _ in plan.savings} == {D('1000')}
    assert plan.unremitted_thb == D('1000')
    full = official_sessions(date(2016, 1, 1), date(2025, 12, 31))
    full_plan = plan_funding_thb(full, D('1000'), {s: D('35') for s in full}, FundingScenario('Y', cadence=12))
    assert len(full_plan.savings) == 119
    assert reconcile_funding(full_plan)['total_saved_thb'] == D('119000')


@pytest.mark.parametrize('cadence', [1, 3, 6, 12])
@pytest.mark.parametrize('delay', [0, 1, 3])
def test_dated_schedule_metamorphic_legacy_equivalence(cadence: int, delay: int) -> None:
    scenario = FundingScenario('EQUIV', cadence, D('400'), D('0.005'), D('15'), delay)
    old = plan_funding(S, D('100'), RATES, scenario)
    new = plan_savings_thb(S, [(day, amount) for day, amount, _ in old.savings], RATES, scenario)
    assert new == old


def test_zero_friction_constant_fx_matches_exact_usd_control() -> None:
    rates = {s: D('35') for s in S}
    old = plan_funding(S, D('100'), rates, FundingScenario('F0'))
    new = plan_funding_thb(S, D('3500'), rates, FundingScenario('CTRL', cadence=1))
    assert new.contributions == old.contributions
    assert reconcile_funding(new)['rounding_usd'] == 0
    assert reconcile_funding(old)['direct_funded_thb'] == D('24500')


def test_insufficient_fees_rounding_and_terminal_transit() -> None:
    rates = {s: D('35') for s in S}
    carry = plan_funding_thb(S, D('300'), rates, FundingScenario('F', 1, D('400')))
    assert carry.remittances[0].remit_session == date(2024, 2, 1)
    assert carry.remittances[0].usd_delivered == D('5.71')
    blocked = plan_funding_thb(S, D('100'), rates, FundingScenario('I', 1, intermediary_fee_usd=D('1000')))
    assert not blocked.remittances and blocked.unremitted_thb == D('700')
    delayed = plan_funding_thb(S, D('1000'), rates, FundingScenario('D', 1, delay_sessions=3))
    assert date(2024, 1, 5) in delayed.contributions
    assert delayed.in_transit_usd == D('28.57')
    reconcile_funding(delayed)
    tiny = plan_savings_thb(S, [(date(2024, 1, 2), D('0.34'))], rates, FundingScenario('T', 1))
    assert not tiny.remittances and tiny.unremitted_thb == D('0.34')


@pytest.mark.parametrize('value', ['-1', 'NaN', 'Infinity', '-Infinity'])
def test_bad_savings_fail_closed(value: str) -> None:
    with pytest.raises(DataContractError):
        plan_funding_thb(S, D(value), RATES, FundingScenario('X', 1))
    with pytest.raises(DataContractError):
        plan_funding(S, D(value), RATES, FundingScenario('X', 1))


@pytest.mark.parametrize('field', ['sender_fee_thb', 'fx_spread', 'intermediary_fee_usd'])
@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1'])
def test_bad_costs_fail_closed(field: str, value: str) -> None:
    with pytest.raises(DataContractError):
        FundingScenario('X', cadence=1, **{field: D(value)})  # type: ignore[arg-type]


def test_schedule_and_fx_contracts() -> None:
    scenario = FundingScenario('X', 1)
    a, b = date(2024, 1, 2), date(2024, 2, 1)
    for savings in ([(a, D('1')), (a, D('2'))], [(b, D('1')), (a, D('1'))], [(date(2024, 1, 1), D('1'))]):
        with pytest.raises(DataContractError):
            plan_savings_thb(S, savings, RATES, scenario)
    for sessions in (list(reversed(S)), list(S) + [S[-1]], [date(2024, 1, 1)]):
        with pytest.raises(DataContractError):
            plan_funding_thb(sessions, D('1'), RATES, scenario)
    for rates in ({date(2025, 1, 1): D('35')}, {date(2020, 1, 1): D('35')}, {a: D('NaN')}, {a: D('0')}):
        with pytest.raises(DataContractError):
            plan_savings_thb(S, [(a, D('1000'))], rates, scenario)
    prior = plan_savings_thb(S, [(a, D('1000'))], {date(2023, 12, 29): D('35')}, scenario)
    assert prior.prior_rate_uses == 2
    with pytest.raises(DataContractError):
        plan_funding_thb(S, D('1000'), RATES, FundingScenario('NO_BYPASS'))


@pytest.mark.parametrize('field', ['cadence', 'delay_sessions'])
@pytest.mark.parametrize('value', [True, 1.5])
def test_noninteger_cadence_delay(field: str, value: object) -> None:
    with pytest.raises(DataContractError):
        FundingScenario('X', **{field: value})  # type: ignore[arg-type]


@pytest.mark.parametrize('tamper', ['cash', 'credit', 'transit', 'fee', 'reference'])
def test_independent_conservation_detects_tampering(tamper: str) -> None:
    plan = plan_funding_thb(S, D('1000'), RATES, FundingScenario('X', 3, D('400')))
    if tamper == 'cash':
        plan.unremitted_thb += D('0.01')
    elif tamper == 'credit':
        day = next(iter(plan.contributions))
        plan.contributions[day] += D('0.01')
    elif tamper == 'transit':
        plan.in_transit_usd += D('0.01')
    elif tamper == 'reference':
        plan.unremitted_saved_usd_ref += D('0.01')
    else:
        plan.remittances[0] = replace(plan.remittances[0], sender_fee_usd_ref=plan.remittances[0].sender_fee_usd_ref + D('0.01'))
    with pytest.raises(DataContractError):
        reconcile_funding(plan)


def test_zero_savings_and_invalid_ledger_rate() -> None:
    plan = plan_funding_thb(S, D('0'), RATES, FundingScenario('ZERO', 1))
    assert reconcile_funding(plan)['total_saved_thb'] == 0
    plan = plan_funding_thb(S, D('1000'), RATES, FundingScenario('X', 1))
    day, amount, _ = plan.savings[0]
    plan.savings[0] = (day, amount, D('NaN'))
    with pytest.raises(DataContractError):
        reconcile_funding(plan)
