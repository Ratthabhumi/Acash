"""D6 V38 prospective retail funding-route cost rule (pure, Decimal, fail-closed).

A route is a THB -> USD transfer from an investor-owned Thai bank account to the
investor's own broker account. Every cost component is either documented
(a Decimal) or UNKNOWN (None). Unknown components are never treated as zero:
the assessment then reports a lower bound on cost, not an all-in cost.

The rule uses the additive effective cost ``F / A + s`` where ``F`` is the fixed
THB-equivalent fee, ``A`` the THB amount and ``s`` the conversion spread. Under
both the V36 convention (``A / (rate * (1 + s))``) and a proportional haircut
convention, the exact cost share is at most ``F / A + s``, so the threshold
``A >= F / (c - s)`` is sufficient (conservative) for a cost ceiling ``c``.
This module does not quote, fetch or execute anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, Decimal
from typing import Optional, Tuple

from acash.core.domain.exceptions import DataContractError

ZERO = Decimal("0")
ONE = Decimal("1")
FUNDING_CURRENCY = "USD"


def _amount(value: Optional[Decimal], context: str, *, positive: bool = False) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal) or not value.is_finite() or value < ZERO or (positive and value == ZERO):
        raise DataContractError(f"ROUTE_INVALID_AMOUNT: {context} {value!r}.")


def _fraction(value: Optional[Decimal], context: str) -> None:
    _amount(value, context)
    if value is not None and value >= ONE:
        raise DataContractError(f"ROUTE_INVALID_FRACTION: {context} {value!r}.")


@dataclass(frozen=True)
class RouteTerms:
    route_id: str
    delivered_currency: str
    fixed_fee_thb: Optional[Decimal]
    fx_spread: Optional[Decimal]
    deducted_fee_usd: Optional[Decimal]
    intermediary_fee_usd: Optional[Decimal]
    receiving_fee_usd: Optional[Decimal]
    variable_fee_rate: Optional[Decimal] = ZERO
    variable_fee_min_thb: Decimal = ZERO
    min_amount_thb: Decimal = ZERO
    max_amount_thb: Optional[Decimal] = None
    promotion_start: Optional[date] = None
    promotion_end: Optional[date] = None
    promotion_end_documented: bool = True
    standard_fee_thb: Optional[Decimal] = None
    purpose_supported: Optional[bool] = None
    beneficiary_supported: Optional[bool] = None

    def __post_init__(self) -> None:
        if not self.route_id.strip():
            raise DataContractError("ROUTE_EMPTY_ID.")
        for name in ("fixed_fee_thb", "deducted_fee_usd", "intermediary_fee_usd", "receiving_fee_usd", "standard_fee_thb"):
            _amount(getattr(self, name), f"{self.route_id} {name}")
        _amount(self.variable_fee_min_thb, f"{self.route_id} variable_fee_min_thb")
        _fraction(self.variable_fee_rate, f"{self.route_id} variable_fee_rate")
        _amount(self.min_amount_thb, f"{self.route_id} min_amount_thb")
        _amount(self.max_amount_thb, f"{self.route_id} max_amount_thb", positive=True)
        _fraction(self.fx_spread, f"{self.route_id} fx_spread")
        if self.max_amount_thb is not None and self.max_amount_thb < self.min_amount_thb:
            raise DataContractError(f"ROUTE_BAD_AMOUNT_RANGE: {self.route_id}.")
        if (self.promotion_start is None) != (self.promotion_end is None) and self.promotion_end_documented:
            raise DataContractError(f"ROUTE_PARTIAL_PROMOTION_WINDOW: {self.route_id}.")
        if self.promotion_start and self.promotion_end and self.promotion_end < self.promotion_start:
            raise DataContractError(f"ROUTE_PROMOTION_END_BEFORE_START: {self.route_id}.")


@dataclass(frozen=True)
class TransferAssessment:
    route_id: str
    amount_thb: Decimal
    fee_thb_known: Decimal
    cost_share_lower_bound: Decimal
    unknown_components: Tuple[str, ...]
    cost_status: str
    eligibility_status: str


def _effective_fixed_fee(terms: RouteTerms, on: date, unknown: list[str]) -> Decimal:
    fee = terms.fixed_fee_thb
    if terms.promotion_start is not None and terms.promotion_end is not None:
        if not terms.promotion_start <= on <= terms.promotion_end:
            fee = terms.standard_fee_thb
            if fee is None:
                unknown.append("POST_PROMOTION_FEE")
    elif not terms.promotion_end_documented:
        unknown.append("PROMOTION_END_DATE")
    if fee is None:
        if "POST_PROMOTION_FEE" not in unknown:
            unknown.append("SENDER_FIXED_FEE")
        return ZERO
    return fee


def assess_transfer(
    terms: RouteTerms, amount_thb: Decimal, reference_thb_per_usd: Decimal, on: date
) -> TransferAssessment:
    """Cost lower bound of one transfer; unknown components are listed, never zeroed."""
    _amount(amount_thb, "amount_thb", positive=True)
    _amount(reference_thb_per_usd, "reference_thb_per_usd", positive=True)
    if terms.delivered_currency != FUNDING_CURRENCY:
        raise DataContractError(f"ROUTE_CURRENCY_MISMATCH: {terms.route_id} delivers {terms.delivered_currency}.")
    if amount_thb < terms.min_amount_thb or (terms.max_amount_thb is not None and amount_thb > terms.max_amount_thb):
        raise DataContractError(f"ROUTE_AMOUNT_OUT_OF_RANGE: {terms.route_id} {amount_thb}.")
    if terms.purpose_supported is False or terms.beneficiary_supported is False:
        raise DataContractError(f"ROUTE_NOT_ELIGIBLE: {terms.route_id}.")
    unknown: list[str] = []
    fee = _effective_fixed_fee(terms, on, unknown)
    if terms.variable_fee_rate is None:
        unknown.append("VARIABLE_FEE_RATE")
        fee += terms.variable_fee_min_thb
    else:
        fee += max(terms.variable_fee_rate * amount_thb, terms.variable_fee_min_thb)
    for name in ("deducted_fee_usd", "intermediary_fee_usd", "receiving_fee_usd"):
        value = getattr(terms, name)
        if value is None:
            unknown.append(name.upper())
        else:
            fee += value * reference_thb_per_usd
    if fee >= amount_thb:
        raise DataContractError(f"ROUTE_FEE_EXCEEDS_AMOUNT: {terms.route_id} {fee} >= {amount_thb}.")
    spread = terms.fx_spread
    if spread is None:
        unknown.append("FX_SPREAD")
        spread = ZERO
    eligibility_unknown = terms.purpose_supported is None or terms.beneficiary_supported is None
    return TransferAssessment(
        route_id=terms.route_id,
        amount_thb=amount_thb,
        fee_thb_known=fee,
        cost_share_lower_bound=fee / amount_thb + spread,
        unknown_components=tuple(sorted(unknown)),
        cost_status="LOWER_BOUND_ONLY" if unknown else "ALL_IN_DOCUMENTED",
        eligibility_status="ACCOUNT_SPECIFIC_UNVERIFIED" if eligibility_unknown else "DOCUMENTED",
    )


def break_even_amount(fixed_fee_thb: Decimal, spread: Decimal, cost_ceiling: Decimal) -> Decimal:
    """Smallest THB amount with ``F / A + s <= c``; requires ``c > s``."""
    _amount(fixed_fee_thb, "fixed_fee_thb")
    _fraction(spread, "spread")
    _fraction(cost_ceiling, "cost_ceiling")
    if cost_ceiling <= spread:
        raise DataContractError(f"ROUTE_CEILING_NOT_ABOVE_SPREAD: c={cost_ceiling} s={spread}.")
    return fixed_fee_thb / (cost_ceiling - spread)


def minimum_batch_months(monthly_thb: Decimal, fixed_fee_thb: Decimal, spread: Decimal, cost_ceiling: Decimal) -> int:
    """Smallest whole number of monthly savings batched so one transfer meets the ceiling."""
    _amount(monthly_thb, "monthly_thb", positive=True)
    months = (break_even_amount(fixed_fee_thb, spread, cost_ceiling) / monthly_thb).to_integral_value(ROUND_CEILING)
    return max(1, int(months))
