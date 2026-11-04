"""Financial capacity, liquidity adequacy and contribution-first allocation (read-only).

Pure Decimal arithmetic on owner-declared figures. No return forecasts, no
risk-profile inference, no orders, no recurring plans. Quant capital is
never funded from the emergency reserve and is never authorized here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_DOWN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.ppds.private_observation import (
    DATA_CLASSES,
    assert_private_location,
    assert_private_observation_authorized,
    read_gated_json,
)

CAPACITY_SCHEMA = "ACASH_PRIVATE_CAPACITY_V1"
ZERO = Decimal("0")
CENT = Decimal("0.01")
CONTRIBUTION_SCENARIOS_THB = (Decimal("5000"), Decimal("7500"), Decimal("10000"))
POLICY_FAMILIES: Dict[str, Dict[str, Any]] = {
    "A_HOLD_CURRENT": {"description": "Keep current holdings; contribute to cash only.", "example_instruments": []},
    "B_GLOBAL_EQUITY": {"description": "Single global equity index fund.", "example_instruments": ["VT"]},
    "C_US_CORE_PLUS_EX_US": {"description": "US broad index plus ex-US index.", "example_instruments": ["VOO", "VXUS"]},
    "D_EQUITY_PLUS_DEFENSIVE": {"description": "Broad equity plus bonds or T-bills.", "example_instruments": ["VT", "BND", "BIL"]},
    "E_CASH_ACCUMULATION": {"description": "Accumulate cash/reserve before any investing.", "example_instruments": ["BIL"]},
}
POLICY_NOTE = "DESCRIPTIVE_ONLY: families are not ranked, not recommended and not suitability-assessed."
_FIELDS = {"schema", "data_class", "monthly_income_thb", "essential_expenses_thb", "obligations_thb",
           "emergency_reserve_thb", "reserve_target_months", "planned_contribution_thb",
           "flexible_contribution_thb", "exceptional_expenses_12m_thb", "horizon_years", "quant_budget_thb"}


def _money(raw: Any, name: str) -> Decimal:
    if not isinstance(raw, str):
        raise DataContractError(f"CAPACITY_NUMBER_MUST_BE_STRING: {name}.")
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise DataContractError(f"CAPACITY_MALFORMED_DECIMAL: {name}.") from exc
    if not value.is_finite() or value < ZERO:
        raise DataContractError(f"CAPACITY_INVALID_AMOUNT: {name}.")
    return value


@dataclass(frozen=True)
class CapacityInputs:
    data_class: str
    monthly_income_thb: Decimal
    essential_expenses_thb: Decimal
    obligations_thb: Decimal
    emergency_reserve_thb: Decimal
    reserve_target_months: Decimal
    planned_contribution_thb: Decimal
    flexible_contribution_thb: Decimal
    exceptional_expenses_12m_thb: Decimal
    horizon_years: int
    quant_budget_thb: Decimal


def parse_capacity(doc: Any) -> CapacityInputs:
    if not isinstance(doc, Mapping):
        raise DataContractError("CAPACITY_NOT_A_MAPPING.")
    unknown = set(doc) - _FIELDS
    if unknown:
        raise DataContractError(f"CAPACITY_UNKNOWN_FIELDS: {sorted(unknown)}.")
    if doc.get("schema") != CAPACITY_SCHEMA or doc.get("data_class") not in DATA_CLASSES:
        raise DataContractError("CAPACITY_SCHEMA_OR_DATA_CLASS_INVALID.")
    horizon = doc.get("horizon_years")
    if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon <= 0:
        raise DataContractError("CAPACITY_HORIZON_INVALID.")
    inputs = CapacityInputs(
        data_class=str(doc["data_class"]),
        monthly_income_thb=_money(doc.get("monthly_income_thb"), "monthly_income_thb"),
        essential_expenses_thb=_money(doc.get("essential_expenses_thb"), "essential_expenses_thb"),
        obligations_thb=_money(doc.get("obligations_thb"), "obligations_thb"),
        emergency_reserve_thb=_money(doc.get("emergency_reserve_thb"), "emergency_reserve_thb"),
        reserve_target_months=_money(doc.get("reserve_target_months"), "reserve_target_months"),
        planned_contribution_thb=_money(doc.get("planned_contribution_thb"), "planned_contribution_thb"),
        flexible_contribution_thb=_money(doc.get("flexible_contribution_thb", "0"), "flexible_contribution_thb"),
        exceptional_expenses_12m_thb=_money(doc.get("exceptional_expenses_12m_thb", "0"), "exceptional_expenses_12m_thb"),
        horizon_years=horizon,
        quant_budget_thb=_money(doc.get("quant_budget_thb", "0"), "quant_budget_thb"),
    )
    if inputs.essential_expenses_thb + inputs.obligations_thb <= ZERO:
        raise DataContractError("CAPACITY_MONTHLY_NEED_ZERO: reserve coverage undefined.")
    return inputs


def load_capacity(path: Path) -> CapacityInputs:
    inputs = parse_capacity(read_gated_json(Path(path), "CAPACITY"))
    if inputs.data_class == "OWNER_PRIVATE_OBSERVATION":
        assert_private_observation_authorized(inputs.data_class, CAPACITY_SCHEMA)
        assert_private_location(Path(path))
    return inputs


def _q(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _months_to(amount: Decimal, per_month: Decimal) -> Optional[int]:
    if amount <= ZERO:
        return 0
    if per_month <= ZERO:
        return None
    return int((amount / per_month).to_integral_value(rounding=ROUND_CEILING))


def assess_capacity(inputs: CapacityInputs, scenarios: Sequence[Decimal] = CONTRIBUTION_SCENARIOS_THB) -> Dict[str, Any]:
    """Liquidity adequacy and per-scenario contribution feasibility; never a recommendation."""
    need = inputs.essential_expenses_thb + inputs.obligations_thb
    surplus = inputs.monthly_income_thb - need
    target = inputs.reserve_target_months * need
    effective_reserve = inputs.emergency_reserve_thb - inputs.exceptional_expenses_12m_thb
    shortfall = target - effective_reserve if effective_reserve < target else ZERO
    excess = effective_reserve - target if effective_reserve > target else ZERO

    rows: List[Dict[str, Any]] = []
    for amount in list(dict.fromkeys([*scenarios, inputs.planned_contribution_thb])):
        residual = surplus - amount
        if residual < ZERO:
            status = "CONTRIBUTION_EXCEEDS_SURPLUS"
        elif shortfall > ZERO:
            status = "RESERVE_SHORTFALL_PRIORITY"
        else:
            status = "WITHIN_SURPLUS_RESERVE_MET"
        rows.append({
            "monthly_contribution_thb": _q(amount),
            "residual_after_contribution_thb": _q(residual),
            "months_to_reserve_target_from_residual": _months_to(shortfall, residual),
            "status": status,
        })

    quant_months = _months_to(inputs.quant_budget_thb - excess if inputs.quant_budget_thb > excess else ZERO,
                              surplus - inputs.planned_contribution_thb)
    return {
        "monthly_need_thb": _q(need),
        "monthly_surplus_thb": _q(surplus),
        "capacity_status": "SURPLUS_POSITIVE" if surplus > ZERO else "CAPACITY_NOT_POSITIVE",
        "reserve": {
            "current_thb": _q(inputs.emergency_reserve_thb),
            "exceptional_expenses_12m_thb": _q(inputs.exceptional_expenses_12m_thb),
            "effective_thb": _q(effective_reserve),
            "target_thb": _q(target),
            "coverage_months": str((effective_reserve / need).quantize(Decimal("0.01"))),
            "shortfall_thb": _q(shortfall),
            "status": "RESERVE_TARGET_MET" if shortfall == ZERO else "RESERVE_SHORTFALL",
        },
        "scenarios": rows,
        "flexible_contribution_thb": _q(inputs.flexible_contribution_thb),
        "horizon_years": inputs.horizon_years,
        "quant_budget": {
            "budget_thb": _q(inputs.quant_budget_thb),
            "label": "HYPOTHETICAL_RESEARCH_BUDGET",
            "authorization": "NOT_AUTHORIZED",
            "reserve_funding": "FORBIDDEN",
            "fundable_from_reserve_excess": inputs.quant_budget_thb <= excess,
            "months_from_residual_after_planned_contribution": quant_months,
        },
        "notes": [
            "Contributions are not profit; no return forecast is made.",
            "Reserve target and horizon are owner declarations; ACASH does not infer risk tolerance.",
        ],
    }


def contribution_first_allocation(current: Mapping[str, Decimal], target_weights: Mapping[str, Decimal],
                                  contribution: Decimal) -> Dict[str, Any]:
    """Direct a new contribution to underweight buckets without selling anything.

    Rounding policy (largest remainder): each bucket's exact share is truncated to the cent, and
    the leftover cents go one each to the largest truncated remainders, ties broken by bucket name.
    Only buckets with a positive exact share can receive a cent, so the rounded allocations always
    sum to the contribution.
    """
    if contribution <= ZERO:
        raise DataContractError("CONTRIBUTION_NONPOSITIVE.")
    if contribution != contribution.quantize(CENT):
        raise DataContractError("CONTRIBUTION_SUB_CENT: contribution must be whole minor units.")
    if not target_weights or sum(target_weights.values(), ZERO) != Decimal("1"):
        raise DataContractError("CONTRIBUTION_TARGET_WEIGHTS_MUST_SUM_TO_ONE.")
    if any(w < ZERO for w in target_weights.values()) or any(v < ZERO for v in current.values()):
        raise DataContractError("CONTRIBUTION_NEGATIVE_INPUT.")
    buckets = sorted(set(current) | set(target_weights))
    total_after = sum(current.values(), ZERO) + contribution
    deficits = {b: max(ZERO, target_weights.get(b, ZERO) * total_after - current.get(b, ZERO)) for b in buckets}
    deficit_sum = sum(deficits.values(), ZERO)
    exact = {b: contribution * deficits[b] / deficit_sum for b in buckets}
    alloc = {b: exact[b].quantize(CENT, rounding=ROUND_DOWN) for b in buckets}
    leftover = int((contribution - sum(alloc.values(), ZERO)) / CENT)
    order = sorted((b for b in buckets if exact[b] > alloc[b]), key=lambda b: (-(exact[b] - alloc[b]), b))
    if leftover > len(order):
        raise DataContractError("CONTRIBUTION_ROUNDING_INVARIANT_BROKEN.")
    for b in order[:leftover]:
        alloc[b] += CENT
    after = {b: current.get(b, ZERO) + alloc[b] for b in buckets}
    return {
        "label": "ILLUSTRATIVE_ALLOCATION_NOT_AN_ORDER",
        "rounding_policy": "LARGEST_REMAINDER_CENTS_TIE_BY_BUCKET_NAME",
        "contribution": _q(contribution),
        "allocation": {b: _q(alloc[b]) for b in buckets},
        "weights_after": {b: str((after[b] / total_after).quantize(Decimal("0.0001"))) for b in buckets},
        "residual_drift": {b: str((after[b] / total_after - target_weights.get(b, ZERO)).quantize(Decimal("0.0001")))
                           for b in buckets},
        "sells": "NONE",
    }
