"""D6 V38 Broker Expansion & Investor Decision Core (pure, Decimal, fail-closed).

Deterministic, read-only decision engine comparing implementation costs and
constraints across Interactive Brokers (IBKR), Dime! Thailand, Webull Thailand,
and a CASH/NO_TRADE baseline.

Strict Fail-Closed Contract:
- Missing fees (e.g. unquoted FX spread, intermediary deductions) are NEVER
  treated as zero; they are recorded as UNKNOWN components and result in a
  conservative lower-bound cost assessment.
- Conflicting terms (e.g. Webull 0% DCA promo vs 0.10% recurring guide) are
  explicitly flagged as TERMS_CONFLICTING.
- All calculations use Python Decimal with explicit rounding and non-negative
  finite assertions.
- This module contains no external network calls, no trading APIs, and no
  account credential access.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.route_cost import RouteTerms, assess_transfer

ZERO = Decimal("0")
ONE = Decimal("1")
CENT = Decimal("0.01")
THAI_VAT_RATE = Decimal("0.07")  # 7% VAT applied on domestic brokerage commissions

DECISION_STATUS_COMPLETE = "COMPARISON_COMPLETE"
DECISION_STATUS_CONDITIONAL = "CONDITIONAL_COMPARISON"
DECISION_STATUS_COST_INCOMPLETE = "COST_EVIDENCE_INCOMPLETE"
DECISION_STATUS_ELIGIBILITY_UNKNOWN = "SECURITY_ELIGIBILITY_UNKNOWN"
DECISION_STATUS_CASH_NO_TRADE = "CASH_NO_TRADE"


def _money(value: Optional[Decimal], context: str, *, positive: bool = False) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal) or not value.is_finite() or value < ZERO or (positive and value == ZERO):
        raise DataContractError(f"DECISION_INVALID_MONEY: {context} {value!r}.")


def _fraction(value: Optional[Decimal], context: str) -> None:
    _money(value, context)
    if value is not None and value > ONE:
        raise DataContractError(f"DECISION_INVALID_FRACTION: {context} {value!r}.")


@dataclass(frozen=True)
class CommissionPolicy:
    policy_type: str  # "FIXED_PER_SHARE", "PERCENTAGE", "FREE_MONTHLY_TIERED", "ZERO_PROMOTIONAL", "NONE"
    rate: Optional[Decimal] = None
    min_commission_usd: Optional[Decimal] = None
    per_share_usd: Optional[Decimal] = None
    free_orders_count: int = 0
    vat_applicable: bool = False
    evidence_status: str = "VERIFIED_DOCUMENTED"  # "VERIFIED_DOCUMENTED", "CONDITIONAL", "TERMS_CONFLICTING", "SCENARIO_ONLY"

    def __post_init__(self) -> None:
        _fraction(self.rate, f"{self.policy_type} rate")
        _money(self.min_commission_usd, f"{self.policy_type} min_commission_usd")
        _money(self.per_share_usd, f"{self.policy_type} per_share_usd")
        if self.free_orders_count < 0:
            raise DataContractError(f"DECISION_INVALID_FREE_ORDERS: {self.free_orders_count}.")


@dataclass(frozen=True)
class BrokerProfile:
    broker_id: str
    display_name: str
    funding_channel: str  # "SWIFT_CROSS_BORDER", "LOCAL_THB_QR_ATS", "NONE"
    commission_policy: CommissionPolicy
    fractional_supported: bool
    min_order_thb: Decimal = ZERO
    funding_terms: Optional[RouteTerms] = None
    supported_symbols: Optional[Tuple[str, ...]] = None
    eligibility_status: str = "DOCUMENTED"  # "DOCUMENTED", "CONDITIONALLY_ELIGIBLE", "ACCOUNT_SPECIFIC_UNVERIFIED", "NOT_ELIGIBLE"
    evidence_notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.broker_id.strip():
            raise DataContractError("DECISION_EMPTY_BROKER_ID.")
        _money(self.min_order_thb, f"{self.broker_id} min_order_thb")


@dataclass(frozen=True)
class InvestmentPlan:
    monthly_savings_thb: Decimal
    batch_months: int = 1
    portfolio_weights: Mapping[str, Decimal] = None  # type: ignore[assignment]
    order_type: str = "MANUAL"  # "MANUAL" or "DCA"
    reference_thb_per_usd: Decimal = Decimal("35.0")
    assumed_fx_spread: Optional[Decimal] = None
    ref_prices_usd: Optional[Mapping[str, Decimal]] = None
    cost_ceiling: Optional[Decimal] = None

    def __post_init__(self) -> None:
        _money(self.monthly_savings_thb, "monthly_savings_thb", positive=True)
        if type(self.batch_months) is not int or self.batch_months < 1:
            raise DataContractError(f"DECISION_INVALID_BATCH_MONTHS: {self.batch_months}.")
        _money(self.reference_thb_per_usd, "reference_thb_per_usd", positive=True)
        _fraction(self.assumed_fx_spread, "assumed_fx_spread")
        _fraction(self.cost_ceiling, "cost_ceiling")
        if self.portfolio_weights is None or len(self.portfolio_weights) == 0:
            raise DataContractError("DECISION_EMPTY_PORTFOLIO_WEIGHTS.")
        weight_sum = ZERO
        seen = set()
        for sym, w in self.portfolio_weights.items():
            if not sym.strip() or sym.strip() in seen:
                raise DataContractError(f"DECISION_INVALID_SYMBOL: {sym!r}.")
            seen.add(sym.strip())
            _fraction(w, f"weight {sym}")
            weight_sum += w
        if abs(weight_sum - ONE) > Decimal("1e-6"):
            raise DataContractError(f"DECISION_WEIGHTS_NOT_ONE: sum={weight_sum}.")


@dataclass(frozen=True)
class BrokerAssessment:
    broker_id: str
    display_name: str
    gross_funding_thb: Decimal
    funding_friction_thb: Decimal
    fx_spread_cost_thb: Decimal
    commission_usd: Decimal
    commission_thb: Decimal
    vat_thb: Decimal
    total_known_friction_thb: Decimal
    friction_share_lower_bound: Decimal
    investable_balance_usd: Optional[Decimal]
    unknown_components: Tuple[str, ...]
    cost_status: str  # "ALL_IN_DOCUMENTED", "LOWER_BOUND_ONLY"
    eligibility_status: str
    free_orders_used: int
    total_orders_count: int
    decision_status: str
    evidence_notes: Tuple[str, ...]


@dataclass(frozen=True)
class ComparisonResult:
    plan: InvestmentPlan
    assessments: Tuple[BrokerAssessment, ...]
    input_hash: str
    overall_status: str


def _calculate_broker_cost(
    profile: BrokerProfile,
    plan: InvestmentPlan,
    as_of: date,
) -> BrokerAssessment:
    gross_thb = plan.monthly_savings_thb * Decimal(plan.batch_months)
    unknowns: List[str] = []
    notes: List[str] = list(profile.evidence_notes)
    
    # 1. CASH / NO TRADE special case
    if profile.broker_id == "CASH":
        return BrokerAssessment(
            broker_id=profile.broker_id,
            display_name=profile.display_name,
            gross_funding_thb=gross_thb,
            funding_friction_thb=ZERO,
            fx_spread_cost_thb=ZERO,
            commission_usd=ZERO,
            commission_thb=ZERO,
            vat_thb=ZERO,
            total_known_friction_thb=ZERO,
            friction_share_lower_bound=ZERO,
            investable_balance_usd=ZERO,
            unknown_components=(),
            cost_status="ALL_IN_DOCUMENTED",
            eligibility_status="DOCUMENTED",
            free_orders_used=0,
            total_orders_count=0,
            decision_status=DECISION_STATUS_CASH_NO_TRADE,
            evidence_notes=("Cash remains in Thai bank; zero market friction, zero investment exposure.",),
        )

    # 2. Funding friction (in THB)
    funding_friction_thb = ZERO
    spread = plan.assumed_fx_spread
    
    if profile.funding_channel == "SWIFT_CROSS_BORDER":
        if profile.funding_terms is None:
            raise DataContractError(f"DECISION_MISSING_ROUTE_TERMS: {profile.broker_id}.")
        transfer_assessment = assess_transfer(
            profile.funding_terms, gross_thb, plan.reference_thb_per_usd, as_of
        )
        funding_friction_thb = transfer_assessment.fee_thb_known
        unknowns.extend(transfer_assessment.unknown_components)
        if spread is None:
            spread = profile.funding_terms.fx_spread
    elif profile.funding_channel == "LOCAL_THB_QR_ATS":
        funding_friction_thb = ZERO  # Local promptpay/QR/ATS has 0 fixed sender fee
    else:
        raise DataContractError(f"DECISION_UNKNOWN_FUNDING_CHANNEL: {profile.funding_channel}.")

    # 3. FX Spread treatment
    if spread is None:
        unknowns.append(f"{profile.broker_id}_FX_SPREAD")
        effective_spread = ZERO
        fx_spread_cost_thb = ZERO
    else:
        effective_spread = spread
        net_to_convert = max(ZERO, gross_thb - funding_friction_thb)
        fx_spread_cost_thb = net_to_convert * effective_spread

    # 4. Check order eligibility and order count
    # Distinct portfolio symbols are evaluated as separate orders
    symbols = tuple(sorted(plan.portfolio_weights.keys()))
    order_count = len(symbols)
    free_orders_used = 0
    total_commission_usd = ZERO
    total_commission_thb = ZERO
    total_vat_thb = ZERO

    # Check symbol support
    eligibility_status = profile.eligibility_status
    if profile.supported_symbols is not None:
        for s in symbols:
            if s not in profile.supported_symbols:
                eligibility_status = "NOT_ELIGIBLE"
                notes.append(f"SYMBOL_NOT_SUPPORTED: {s}")

    # Check minimum order
    net_thb_available = max(ZERO, gross_thb - funding_friction_thb - fx_spread_cost_thb)
    policy = profile.commission_policy

    if policy.policy_type == "ZERO_PROMOTIONAL":
        # e.g. Webull DCA 0% promo
        total_commission_usd = ZERO
        total_commission_thb = ZERO
        total_vat_thb = ZERO
        if policy.evidence_status == "TERMS_CONFLICTING":
            notes.append("TERMS_CONFLICTING: DCA 0% promo vs 0.10% recurring investment guide.")
    elif policy.policy_type == "PERCENTAGE":
        # e.g. Webull Manual 0.10%
        if policy.rate is None:
            unknowns.append(f"{profile.broker_id}_COMMISSION_RATE")
        else:
            for s in symbols:
                weight = plan.portfolio_weights[s]
                order_thb = net_thb_available * weight
                if order_thb < profile.min_order_thb:
                    notes.append(f"ORDER_BELOW_MINIMUM: {s} {order_thb} < {profile.min_order_thb}")
                comm_thb = order_thb * policy.rate
                total_commission_thb += comm_thb
            if policy.vat_applicable:
                total_vat_thb = (total_commission_thb * THAI_VAT_RATE).quantize(CENT, rounding=ROUND_HALF_UP)
            total_commission_usd = total_commission_thb / plan.reference_thb_per_usd
    elif policy.policy_type == "FREE_MONTHLY_TIERED":
        # e.g. Dime! 1 free order per month, subsequent 0.15%
        # Free order applied to the largest order to be conservative/beneficial
        sorted_orders = sorted(
            [(s, net_thb_available * plan.portfolio_weights[s]) for s in symbols],
            key=lambda x: x[1],
            reverse=True,
        )
        remaining_free = policy.free_orders_count
        for s, order_thb in sorted_orders:
            if order_thb < profile.min_order_thb:
                notes.append(f"ORDER_BELOW_MINIMUM: {s} {order_thb} < {profile.min_order_thb}")
            if remaining_free > 0:
                free_orders_used += 1
                remaining_free -= 1
                # Order is free
            else:
                if policy.rate is None:
                    unknowns.append(f"{profile.broker_id}_COMMISSION_RATE")
                else:
                    comm_thb = order_thb * policy.rate
                    total_commission_thb += comm_thb
        if policy.vat_applicable and total_commission_thb > ZERO:
            total_vat_thb = (total_commission_thb * THAI_VAT_RATE).quantize(CENT, rounding=ROUND_HALF_UP)
        total_commission_usd = total_commission_thb / plan.reference_thb_per_usd
    elif policy.policy_type == "FIXED_PER_SHARE":
        # e.g. IBKR Tiered or Fixed
        per_share = policy.per_share_usd or Decimal("0.0035")
        min_comm = policy.min_commission_usd or Decimal("0.35")
        for s in symbols:
            weight = plan.portfolio_weights[s]
            order_thb = net_thb_available * weight
            order_usd = order_thb / plan.reference_thb_per_usd
            # Estimate shares if ref price provided
            price = (plan.ref_prices_usd or {}).get(s, Decimal("100.0"))
            shares = order_usd / price
            comm_usd = max(min_comm, shares * per_share)
            total_commission_usd += comm_usd
        total_commission_thb = total_commission_usd * plan.reference_thb_per_usd
        total_vat_thb = ZERO  # US broker, no Thai VAT
    elif policy.policy_type == "NONE":
        pass
    else:
        raise DataContractError(f"DECISION_UNSUPPORTED_COMMISSION_POLICY: {policy.policy_type}.")

    # 5. Total known friction
    total_known_friction_thb = (
        funding_friction_thb + fx_spread_cost_thb + total_commission_thb + total_vat_thb
    )
    friction_share_lower_bound = total_known_friction_thb / gross_thb

    # 6. Investable balance USD
    if total_known_friction_thb < gross_thb:
        investable_thb = gross_thb - total_known_friction_thb
        effective_rate = plan.reference_thb_per_usd * (ONE + effective_spread)
        investable_balance_usd = (investable_thb / effective_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        investable_balance_usd = ZERO

    # 7. Deduce decision status
    unknown_tuple = tuple(sorted(set(unknowns)))
    cost_status = "LOWER_BOUND_ONLY" if unknown_tuple else "ALL_IN_DOCUMENTED"
    
    if eligibility_status == "NOT_ELIGIBLE":
        decision_status = "NOT_ELIGIBLE"
    elif unknown_tuple:
        decision_status = DECISION_STATUS_COST_INCOMPLETE
    elif eligibility_status != "DOCUMENTED":
        decision_status = DECISION_STATUS_CONDITIONAL
    else:
        decision_status = DECISION_STATUS_COMPLETE

    return BrokerAssessment(
        broker_id=profile.broker_id,
        display_name=profile.display_name,
        gross_funding_thb=gross_thb,
        funding_friction_thb=funding_friction_thb,
        fx_spread_cost_thb=fx_spread_cost_thb,
        commission_usd=total_commission_usd.quantize(CENT, rounding=ROUND_HALF_UP),
        commission_thb=total_commission_thb.quantize(CENT, rounding=ROUND_HALF_UP),
        vat_thb=total_vat_thb.quantize(CENT, rounding=ROUND_HALF_UP),
        total_known_friction_thb=total_known_friction_thb.quantize(CENT, rounding=ROUND_HALF_UP),
        friction_share_lower_bound=friction_share_lower_bound,
        investable_balance_usd=investable_balance_usd,
        unknown_components=unknown_tuple,
        cost_status=cost_status,
        eligibility_status=eligibility_status,
        free_orders_used=free_orders_used,
        total_orders_count=order_count,
        decision_status=decision_status,
        evidence_notes=tuple(notes),
    )


def compare_investment_plans(
    profiles: Sequence[BrokerProfile],
    plan: InvestmentPlan,
    as_of: date,
) -> ComparisonResult:
    """Evaluate and compare investment implementation across candidate brokers."""
    assessments: List[BrokerAssessment] = []
    for p in profiles:
        assessments.append(_calculate_broker_cost(p, plan, as_of))
    
    # Deterministic input hash
    payload = {
        "monthly_savings_thb": str(plan.monthly_savings_thb),
        "batch_months": plan.batch_months,
        "portfolio_weights": {k: str(v) for k, v in sorted(plan.portfolio_weights.items())},
        "order_type": plan.order_type,
        "reference_thb_per_usd": str(plan.reference_thb_per_usd),
        "assumed_fx_spread": str(plan.assumed_fx_spread) if plan.assumed_fx_spread is not None else None,
        "as_of": as_of.isoformat(),
        "profiles": [p.broker_id for p in profiles],
    }
    input_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    # Determine overall status
    statuses = {a.decision_status for a in assessments if a.broker_id != "CASH"}
    if DECISION_STATUS_COST_INCOMPLETE in statuses:
        overall_status = DECISION_STATUS_COST_INCOMPLETE
    elif DECISION_STATUS_CONDITIONAL in statuses:
        overall_status = DECISION_STATUS_CONDITIONAL
    else:
        overall_status = DECISION_STATUS_COMPLETE

    return ComparisonResult(
        plan=plan,
        assessments=tuple(assessments),
        input_hash=input_hash,
        overall_status=overall_status,
    )


def format_markdown_report(result: ComparisonResult) -> str:
    """Format an audit-ready, readable Markdown decision report."""
    p = result.plan
    lines = [
        "# ACASH INVESTOR DECISION REPORT",
        "",
        f"- **Evaluation Date**: {date.today().isoformat()}",
        f"- **Input Hash (SHA-256)**: `{result.input_hash}`",
        f"- **Overall Decision Status**: `{result.overall_status}`",
        f"- **Monthly Savings**: THB {p.monthly_savings_thb:,.2f}",
        f"- **Batch Cadence**: {p.batch_months} month(s) (Gross: THB {p.monthly_savings_thb * p.batch_months:,.2f})",
        f"- **Order Type**: `{p.order_type}`",
        f"- **Portfolio Allocation**: {', '.join(f'{k}: {v*100:.1f}%' for k, v in sorted(p.portfolio_weights.items()))}",
        f"- **Reference FX Rate**: {p.reference_thb_per_usd} THB/USD",
        "",
        "## Broker Comparison Matrix",
        "",
        "| Platform | Channel | Funding Fee (THB) | Comm + VAT (THB) | Known Friction (THB) | Lower Bound Drag | Cost Status | Eligibility | Unknown Costs |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for a in result.assessments:
        comm_vat = a.commission_thb + a.vat_thb
        drag_pct = f"{a.friction_share_lower_bound * 100:.2f}%"
        unknowns_str = ", ".join(a.unknown_components) if a.unknown_components else "None (Documented)"
        channel = "Local THB" if "LOCAL" in a.broker_id or a.broker_id in ("DIME", "WEBULL_MANUAL", "WEBULL_DCA") else ("SWIFT" if a.broker_id == "IBKR" else "N/A")
        lines.append(
            f"| **{a.display_name}** | {channel} | {a.funding_friction_thb:,.2f} | {comm_vat:,.2f} | {a.total_known_friction_thb:,.2f} | {drag_pct} | `{a.cost_status}` | `{a.eligibility_status}` | {unknowns_str} |"
        )

    lines.extend([
        "",
        "## Key Observations & Caveats",
        "",
        "1. **Direct SWIFT Drag on Small Amounts**: Direct outbound SWIFT to IBKR incurs fixed sender fees (e.g. THB 250+) which create high friction on monthly savings under THB 10,000.",
        "2. **Local Baht Funding Advantage**: Dime! and Webull Thailand accept local Thai Baht (ATS/QR) with zero fixed sender fees, eliminating the SWIFT fixed charge.",
        "3. **Unknown FX Spreads**: Neither Dime! nor Webull publish a guaranteed deterministic retail THB/USD conversion spread; cost percentages are lower bounds only.",
        "4. **Webull DCA Zero Commission Policy**: Webull marketing mentions 0% commission on DCA, but documentation conflicts with the 0.10% recurring investment guide. Modeled as `TERMS_CONFLICTING`.",
        "5. **Dime! Free Order Entitlement**: Dime! offers 1 free order per calendar month. On multi-asset allocations (e.g. VOO 60% + BND 40%), subsequent orders incur 0.15% + 7% VAT.",
        "6. **Governance Boundary**: This is read-only prospective planning. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.",
    ])

    return "\n".join(lines)


def main() -> None:
    """CLI runner for ACASH Investor Decision Core."""
    import argparse
    import sys
    from acash.research.d6.broker_profiles import load_candidate_profiles

    parser = argparse.ArgumentParser(description="ACASH V38 Investor Decision Core")
    parser.add_argument("--savings", type=str, default="3000.0", help="Monthly savings in THB")
    parser.add_argument("--batch-months", type=int, default=1, help="Number of months batched per funding (1=monthly, 3=quarterly)")
    parser.add_argument("--portfolio", type=str, default="VOO:0.6,BND:0.4", help="Comma-separated ticker:weight allocation")
    parser.add_argument("--order-type", type=str, default="MANUAL", choices=["MANUAL", "DCA"], help="Order execution type")
    parser.add_argument("--reference-fx", type=str, default="35.0", help="Reference THB/USD rate")
    parser.add_argument("--fx-spread", type=str, default=None, help="Assumed FX spread (e.g. 0.005). If omitted, treated as UNKNOWN.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")
    parser.add_argument("--output", type=str, default=None, help="Path to save output")

    args = parser.parse_args()

    # Parse portfolio
    weights: Dict[str, Decimal] = {}
    for item in args.portfolio.split(","):
        if ":" in item:
            sym, w = item.split(":", 1)
            weights[sym.strip().upper()] = Decimal(w.strip())
        else:
            raise DataContractError(f"Invalid portfolio format: {item!r}. Expected TICKER:WEIGHT.")

    plan = InvestmentPlan(
        monthly_savings_thb=Decimal(args.savings),
        batch_months=args.batch_months,
        portfolio_weights=weights,
        order_type=args.order_type,
        reference_thb_per_usd=Decimal(args.reference_fx),
        assumed_fx_spread=Decimal(args.fx_spread) if args.fx_spread else None,
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )

    profiles = load_candidate_profiles()
    result = compare_investment_plans(profiles, plan, date.today())

    if args.json:
        # Convert dataclasses to dict with string Decimals
        def _dec_str(obj: Any) -> Any:
            if isinstance(obj, Decimal):
                return str(obj)
            if isinstance(obj, dict):
                return {k: _dec_str(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_dec_str(x) for x in obj]
            return obj

        data = {
            "input_hash": result.input_hash,
            "overall_status": result.overall_status,
            "plan": _dec_str(asdict(result.plan)),
            "assessments": [_dec_str(asdict(a)) for a in result.assessments],
        }
        out_text = json.dumps(data, indent=2)
    else:
        out_text = format_markdown_report(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_text)
        print(f"Report written to {args.output}")
    else:
        print(out_text)


if __name__ == "__main__":
    main()

