"""D6 V38 prospective funding-route cost rule tests (synthetic terms only)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.route_cost import (
    RouteTerms,
    assess_transfer,
    break_even_amount,
    minimum_batch_months,
)

D = Decimal
RATE = D("32")
ON = date(2026, 6, 1)


def _terms(**changes: object) -> RouteTerms:
    base = RouteTerms(
        route_id="SYNTH_SHA",
        delivered_currency="USD",
        fixed_fee_thb=D("250"),
        fx_spread=D("0.005"),
        deducted_fee_usd=D("0"),
        intermediary_fee_usd=D("0"),
        receiving_fee_usd=D("0"),
        purpose_supported=True,
        beneficiary_supported=True,
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def test_all_documented_route_is_all_in() -> None:
    result = assess_transfer(_terms(), D("50000"), RATE, ON)
    assert result.cost_status == "ALL_IN_DOCUMENTED"
    assert result.eligibility_status == "DOCUMENTED"
    assert result.cost_share_lower_bound == D("250") / D("50000") + D("0.005")


def test_unknown_components_give_lower_bound_never_zero_pass() -> None:
    result = assess_transfer(_terms(fx_spread=None, intermediary_fee_usd=None), D("50000"), RATE, ON)
    assert result.cost_status == "LOWER_BOUND_ONLY"
    assert result.unknown_components == ("FX_SPREAD", "INTERMEDIARY_FEE_USD")
    assert result.cost_share_lower_bound == D("250") / D("50000")


def test_unknown_fixed_fee_is_listed() -> None:
    result = assess_transfer(_terms(fixed_fee_thb=None), D("50000"), RATE, ON)
    assert result.unknown_components == ("SENDER_FIXED_FEE",)


@pytest.mark.parametrize("field", ["purpose_supported", "beneficiary_supported"])
def test_unverified_purpose_or_broker_compatibility_is_reported(field: str) -> None:
    result = assess_transfer(_terms(**{field: None}), D("50000"), RATE, ON)
    assert result.eligibility_status == "ACCOUNT_SPECIFIC_UNVERIFIED"


def test_percentage_fee_with_minimum_floor() -> None:
    terms = _terms(fixed_fee_thb=D("0"), variable_fee_rate=D("0.00125"), variable_fee_min_thb=D("500"))
    assert assess_transfer(terms, D("100000"), RATE, ON).fee_thb_known == D("500")
    assert assess_transfer(terms, D("800000"), RATE, ON).fee_thb_known == D("1000")
    unknown_rate = assess_transfer(replace(terms, variable_fee_rate=None), D("100000"), RATE, ON)
    assert unknown_rate.unknown_components == ("VARIABLE_FEE_RATE",)
    assert unknown_rate.fee_thb_known == D("500")


def test_assessment_is_deterministic() -> None:
    terms = _terms(fx_spread=None, receiving_fee_usd=None)
    assert assess_transfer(terms, D("50000"), RATE, ON) == assess_transfer(terms, D("50000"), RATE, ON)


@pytest.mark.parametrize("field", ["purpose_supported", "beneficiary_supported"])
def test_documented_ineligibility_raises(field: str) -> None:
    with pytest.raises(DataContractError, match="ROUTE_NOT_ELIGIBLE"):
        assess_transfer(_terms(**{field: False}), D("50000"), RATE, ON)


def test_sha_and_our_payer_incidence_differ() -> None:
    sha = assess_transfer(_terms(intermediary_fee_usd=D("15")), D("50000"), RATE, ON)
    our = assess_transfer(_terms(fixed_fee_thb=D("950"), intermediary_fee_usd=D("0")), D("50000"), RATE, ON)
    assert sha.fee_thb_known == D("250") + D("15") * RATE
    assert our.fee_thb_known == D("950")
    assert sha.fee_thb_known != our.fee_thb_known


def test_promotion_expiry_switches_to_standard_or_unknown() -> None:
    promo = _terms(promotion_start=date(2026, 1, 1), promotion_end=date(2026, 12, 31), standard_fee_thb=D("400"))
    assert assess_transfer(promo, D("50000"), RATE, ON).fee_thb_known == D("250")
    assert assess_transfer(promo, D("50000"), RATE, date(2027, 1, 1)).fee_thb_known == D("400")
    unknown_after = replace(promo, standard_fee_thb=None)
    result = assess_transfer(unknown_after, D("50000"), RATE, date(2027, 1, 1))
    assert result.unknown_components == ("POST_PROMOTION_FEE",)
    assert result.cost_status == "LOWER_BOUND_ONLY"


def test_undocumented_promotion_end_is_listed() -> None:
    result = assess_transfer(_terms(promotion_end_documented=False), D("50000"), RATE, ON)
    assert result.unknown_components == ("PROMOTION_END_DATE",)


def test_promotion_window_contract() -> None:
    with pytest.raises(DataContractError, match="ROUTE_PARTIAL_PROMOTION_WINDOW"):
        _terms(promotion_start=date(2026, 1, 1))
    with pytest.raises(DataContractError, match="ROUTE_PROMOTION_END_BEFORE_START"):
        _terms(promotion_start=date(2026, 2, 1), promotion_end=date(2026, 1, 1))


def test_currency_mismatch_raises() -> None:
    with pytest.raises(DataContractError, match="ROUTE_CURRENCY_MISMATCH"):
        assess_transfer(_terms(delivered_currency="THB"), D("50000"), RATE, ON)


def test_amount_bounds_enforced() -> None:
    bounded = _terms(min_amount_thb=D("1000"), max_amount_thb=D("1500000"))
    assess_transfer(bounded, D("1500000"), RATE, ON)
    for amount in (D("999"), D("1500001")):
        with pytest.raises(DataContractError, match="ROUTE_AMOUNT_OUT_OF_RANGE"):
            assess_transfer(bounded, amount, RATE, ON)
    with pytest.raises(DataContractError, match="ROUTE_BAD_AMOUNT_RANGE"):
        _terms(min_amount_thb=D("10"), max_amount_thb=D("5"))


def test_fee_exceeding_amount_raises() -> None:
    with pytest.raises(DataContractError, match="ROUTE_FEE_EXCEEDS_AMOUNT"):
        assess_transfer(_terms(), D("250"), RATE, ON)


@pytest.mark.parametrize("bad", [D("0"), D("-1"), D("NaN"), D("Infinity")])
def test_invalid_amount_or_rate_raises(bad: Decimal) -> None:
    with pytest.raises(DataContractError, match="ROUTE_INVALID_AMOUNT"):
        assess_transfer(_terms(), bad, RATE, ON)
    with pytest.raises(DataContractError, match="ROUTE_INVALID_AMOUNT"):
        assess_transfer(_terms(), D("50000"), bad, ON)


@pytest.mark.parametrize(
    "changes",
    [{"fixed_fee_thb": D("-1")}, {"fx_spread": D("1")}, {"fx_spread": D("NaN")}, {"receiving_fee_usd": D("Infinity")}],
)
def test_invalid_terms_raise(changes: dict[str, Decimal]) -> None:
    with pytest.raises(DataContractError):
        _terms(**changes)


def test_unknown_component_order_is_canonical() -> None:
    a = assess_transfer(_terms(receiving_fee_usd=None, fx_spread=None, deducted_fee_usd=None), D("50000"), RATE, ON)
    assert a.unknown_components == tuple(sorted(a.unknown_components))


def test_break_even_rule() -> None:
    assert break_even_amount(D("250"), D("0"), D("0.01")) == D("25000")
    assert break_even_amount(D("250"), D("0.005"), D("0.01")) == D("50000")
    with pytest.raises(DataContractError, match="ROUTE_CEILING_NOT_ABOVE_SPREAD"):
        break_even_amount(D("250"), D("0.01"), D("0.01"))
    with pytest.raises(DataContractError, match="ROUTE_CEILING_NOT_ABOVE_SPREAD"):
        break_even_amount(D("250"), D("0.02"), D("0.01"))


def test_minimum_batch_months_household_examples() -> None:
    months = [minimum_batch_months(D(m), D("250"), D("0"), D("0.01")) for m in ("1000", "3000", "5000", "10000")]
    assert months == [25, 9, 5, 3]
    assert minimum_batch_months(D("100000"), D("250"), D("0"), D("0.01")) == 1
