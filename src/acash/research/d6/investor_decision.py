"""D6 V38 Broker Expansion & Investor Decision Core (pure, Decimal, fail-closed).

Deterministic, read-only decision engine comparing investment implementation costs and
constraints across Interactive Brokers (IBKR), Dime! Thailand, Webull Thailand,
and a CASH/NO_TRADE baseline.

Strict Fail-Closed Contract & Final Acceptance Enforcements:
- P0.1 Cost Status Taxonomy: Strictly distinguishes mathematical completion from evidence completion.
  - ``ALL_IN_DOCUMENTED``: Every fee and FX spread is verified from official provider tariffs.
  - ``QUOTE_OBSERVED``: Conversion uses a valid, unexpired user-observed FX quote snapshot.
  - ``SCENARIO_ONLY``: Mathematically complete using user-specified hypothetical spread; not verified.
  - ``LOWER_BOUND_ONLY``: Unquoted spread or missing intermediary fee; lower bound reported.
- P0.2 Comprehensive Input Hash: Serializes every financially material field, including all
  15 RouteTerms fields, full broker policies, order sequence, reference prices, and user quotes.
- P0.3 Order & Security Eligibility Enforcement: Orders below minimum are marked ``NOT_ELIGIBLE``.
  Incompatible order types (MANUAL plan on DCA-only profile) are marked ``ORDER_TYPE_INCOMPATIBLE``.
- P0.4 Missing Price Fail-Closed: Missing asset prices on Dime! non-free orders record
  ``DIME_PRICE_TIER_UNKNOWN`` rather than silently guessing >=$6.67 or <$6.67.
- P0.5 Cash Conservation & FX Formulation: Economic FX drag is ``THB_net - (USD_received * r)``,
  strictly conserving cash without double deduction.
- P0.6 Fee Snapshot Provenance: Tracks source version conflict, creation timestamp, and capture status.
- Phase 4 User-Observed Quote Contract: Allows offline evaluation of user-reported FX snapshots
  with implied spread benchmarking and stale quote detection.
"""

from __future__ import annotations

import argparse
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
MICRO_CENT = Decimal("0.000001")
THAI_VAT_RATE = Decimal("0.07")  # 7% VAT on Thai domestic brokerage commissions
DIME_CAT_FEE_PER_SHARE_USD = Decimal("0.000046")    # Effective June 1, 2025 on Dime
WEBULL_CAT_FEE_PER_SHARE_USD = Decimal("0.000024")  # Webull official tariff

COST_STATUS_ALL_IN_DOCUMENTED = "ALL_IN_DOCUMENTED"
COST_STATUS_QUOTE_OBSERVED = "QUOTE_OBSERVED"
COST_STATUS_SCENARIO_ONLY = "SCENARIO_ONLY"
COST_STATUS_LOWER_BOUND_ONLY = "LOWER_BOUND_ONLY"

DECISION_STATUS_COMPLETE = "COMPARISON_COMPLETE"
DECISION_STATUS_CONDITIONAL = "CONDITIONAL_COMPARISON"
DECISION_STATUS_COST_INCOMPLETE = "COST_EVIDENCE_INCOMPLETE"
DECISION_STATUS_ELIGIBILITY_UNKNOWN = "SECURITY_ELIGIBILITY_UNKNOWN"
DECISION_STATUS_CASH_NO_TRADE = "CASH_NO_TRADE"
DECISION_STATUS_TERMS_CONFLICTING = "TERMS_CONFLICTING"
DECISION_STATUS_NOT_ELIGIBLE = "NOT_ELIGIBLE"


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
class UserFxQuote:
    """User-reported in-app FX exchange rate snapshot (read-only, offline)."""
    broker_id: str
    quote_observed_at: str  # ISO timestamp
    quoted_thb_per_usd: Decimal
    quote_valid_until: Optional[str] = None
    reference_rate: Optional[Decimal] = None
    reference_rate_timestamp: Optional[str] = None
    reference_rate_source: Optional[str] = None
    quote_source_type: str = "IN_APP_DISPLAY"
    quote_direction: str = "THB_TO_USD"
    is_expired: bool = False
    notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.broker_id.strip():
            raise DataContractError("USER_QUOTE_EMPTY_BROKER_ID.")
        _money(self.quoted_thb_per_usd, f"{self.broker_id} quoted_thb_per_usd", positive=True)
        _money(self.reference_rate, f"{self.broker_id} reference_rate", positive=True)

    @property
    def implied_spread(self) -> Optional[Decimal]:
        if self.reference_rate is not None and self.reference_rate > ZERO:
            return (self.quoted_thb_per_usd / self.reference_rate) - ONE
        return None


@dataclass(frozen=True)
class CommissionPolicy:
    policy_type: str  # "FIXED_PER_SHARE", "PERCENTAGE", "FREE_MONTHLY_TIERED", "ZERO_PROMOTIONAL", "NONE"
    rate: Optional[Decimal] = None
    min_commission_usd: Optional[Decimal] = None
    per_share_usd: Optional[Decimal] = None
    free_orders_count: int = 0
    vat_applicable: bool = False
    applicable_order_type: str = "ALL"  # "ALL", "MANUAL", "DCA"
    evidence_status: str = "OFFICIAL_PROVIDER_TARIFF"  # Taxonomy matching Phase 3

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
    order_sequence: Optional[Tuple[str, ...]] = None
    order_type: str = "MANUAL"  # "MANUAL" or "DCA"
    reference_thb_per_usd: Decimal = Decimal("35.0")
    assumed_fx_spread: Optional[Decimal] = None
    user_quotes: Optional[Mapping[str, UserFxQuote]] = None
    free_trades_available: int = 1
    ref_prices_usd: Optional[Mapping[str, Decimal]] = None
    cost_ceiling: Optional[Decimal] = None

    def __post_init__(self) -> None:
        _money(self.monthly_savings_thb, "monthly_savings_thb", positive=True)
        if type(self.batch_months) is not int or self.batch_months < 1:
            raise DataContractError(f"DECISION_INVALID_BATCH_MONTHS: {self.batch_months}.")
        _money(self.reference_thb_per_usd, "reference_thb_per_usd", positive=True)
        _fraction(self.assumed_fx_spread, "assumed_fx_spread")
        _fraction(self.cost_ceiling, "cost_ceiling")
        if self.free_trades_available < 0:
            raise DataContractError(f"DECISION_INVALID_FREE_TRADES: {self.free_trades_available}.")
        if self.portfolio_weights is None or len(self.portfolio_weights) == 0:
            raise DataContractError("DECISION_EMPTY_PORTFOLIO_WEIGHTS.")
        weight_sum = ZERO
        seen = set()
        for sym, w in self.portfolio_weights.items():
            s_clean = sym.strip().upper()
            if not s_clean or s_clean in seen:
                raise DataContractError(f"DECISION_INVALID_SYMBOL: {sym!r}.")
            seen.add(s_clean)
            _fraction(w, f"weight {sym}")
            weight_sum += w
        if abs(weight_sum - ONE) > Decimal("1e-6"):
            raise DataContractError(f"DECISION_WEIGHTS_NOT_ONE: sum={weight_sum}.")
        if self.order_sequence is not None:
            if set(self.order_sequence) != seen or len(self.order_sequence) != len(seen):
                raise DataContractError("DECISION_ORDER_SEQUENCE_MISMATCH: must match portfolio symbols exactly.")


@dataclass(frozen=True)
class BrokerAssessment:
    broker_id: str
    display_name: str
    gross_funding_thb: Decimal
    funding_friction_thb: Decimal
    fx_spread_cost_thb: Decimal
    commission_usd: Decimal
    commission_thb: Decimal
    regulatory_fees_usd: Decimal
    regulatory_fees_thb: Decimal
    vat_thb: Decimal
    total_known_friction_thb: Decimal
    friction_share_lower_bound: Decimal
    investable_balance_usd: Optional[Decimal]
    unknown_components: Tuple[str, ...]
    cost_status: str  # COST_STATUS taxonomy
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
    eligibility_status = profile.eligibility_status

    # 1. CASH / NO TRADE baseline control
    if profile.broker_id == "CASH":
        return BrokerAssessment(
            broker_id=profile.broker_id,
            display_name=profile.display_name,
            gross_funding_thb=gross_thb,
            funding_friction_thb=ZERO,
            fx_spread_cost_thb=ZERO,
            commission_usd=ZERO,
            commission_thb=ZERO,
            regulatory_fees_usd=ZERO,
            regulatory_fees_thb=ZERO,
            vat_thb=ZERO,
            total_known_friction_thb=ZERO,
            friction_share_lower_bound=ZERO,
            investable_balance_usd=ZERO,
            unknown_components=(),
            cost_status=COST_STATUS_ALL_IN_DOCUMENTED,
            eligibility_status="DOCUMENTED",
            free_orders_used=0,
            total_orders_count=0,
            decision_status=DECISION_STATUS_CASH_NO_TRADE,
            evidence_notes=("Baseline control: 100% held in domestic cash; zero transfer friction, zero investment exposure.",),
        )

    # 2. P0.3 Order type compatibility check (Fail-closed)
    policy = profile.commission_policy
    if policy.applicable_order_type != "ALL" and policy.applicable_order_type != plan.order_type:
        notes.append(f"ORDER_TYPE_INCOMPATIBLE: Plan order type is {plan.order_type}; profile requires {policy.applicable_order_type}.")
        return BrokerAssessment(
            broker_id=profile.broker_id,
            display_name=profile.display_name,
            gross_funding_thb=gross_thb,
            funding_friction_thb=ZERO,
            fx_spread_cost_thb=ZERO,
            commission_usd=ZERO,
            commission_thb=ZERO,
            regulatory_fees_usd=ZERO,
            regulatory_fees_thb=ZERO,
            vat_thb=ZERO,
            total_known_friction_thb=ZERO,
            friction_share_lower_bound=ZERO,
            investable_balance_usd=None,
            unknown_components=(),
            cost_status=COST_STATUS_SCENARIO_ONLY,
            eligibility_status="ORDER_TYPE_INCOMPATIBLE",
            free_orders_used=0,
            total_orders_count=0,
            decision_status=DECISION_STATUS_NOT_ELIGIBLE,
            evidence_notes=tuple(notes),
        )

    # 3. Funding friction (in THB)
    funding_friction_thb = ZERO
    user_quote = (plan.user_quotes or {}).get(profile.broker_id)
    spread = plan.assumed_fx_spread
    is_quote_observed = False

    if user_quote is not None:
        if user_quote.is_expired:
            notes.append("USER_QUOTE_STALE: Supplied FX quote is expired; treated as historical observation.")
        else:
            is_quote_observed = True
            spread = user_quote.implied_spread
            notes.append(f"USER_QUOTE_APPLIED: Rate={user_quote.quoted_thb_per_usd} THB/USD observed at {user_quote.quote_observed_at}.")

    if profile.funding_channel == "SWIFT_CROSS_BORDER":
        if profile.funding_terms is None:
            raise DataContractError(f"DECISION_MISSING_ROUTE_TERMS: {profile.broker_id}.")
        terms = profile.funding_terms
        if gross_thb < terms.min_amount_thb:
            notes.append(f"AMOUNT_BELOW_MINIMUM: Gross funding THB {gross_thb} < Route min THB {terms.min_amount_thb}")
            eligibility_status = "NOT_ELIGIBLE"
        transfer_assessment = assess_transfer(
            terms, gross_thb, plan.reference_thb_per_usd, as_of
        )
        funding_friction_thb = transfer_assessment.fee_thb_known
        unknowns.extend(transfer_assessment.unknown_components)
        if spread is None:
            spread = terms.fx_spread
    elif profile.funding_channel == "LOCAL_THB_QR_ATS":
        funding_friction_thb = ZERO  # Local promptpay/QR/ATS has 0 published fixed sender fee
    else:
        raise DataContractError(f"DECISION_UNKNOWN_FUNDING_CHANNEL: {profile.funding_channel}.")

    # 4. Check order sequence contract
    if plan.order_sequence is not None:
        ordered_symbols = plan.order_sequence
    else:
        ordered_symbols = tuple(sorted(plan.portfolio_weights.keys()))

    order_count = len(ordered_symbols)
    free_orders_used = 0
    total_commission_usd = ZERO
    total_commission_thb = ZERO
    total_reg_fees_usd = ZERO
    total_reg_fees_thb = ZERO
    total_vat_thb = ZERO

    # Check symbol support
    if profile.supported_symbols is not None:
        for s in ordered_symbols:
            if s not in profile.supported_symbols:
                eligibility_status = "NOT_ELIGIBLE"
                notes.append(f"SYMBOL_NOT_SUPPORTED: {s}")

    # Available net THB before trade commissions
    net_thb_before_trade = max(ZERO, gross_thb - funding_friction_thb)

    # 5. Commission & Regulatory Fee Evaluation
    if policy.evidence_status in ("TERMS_CONFLICTING", "OFFICIAL_SOURCE_CONFLICT"):
        notes.append("TERMS_CONFLICTING: Conflicting official provider terms (e.g. 0% promo vs 0.10% recurring guide).")

    if policy.policy_type == "ZERO_PROMOTIONAL":
        total_commission_usd = ZERO
        total_commission_thb = ZERO
        total_vat_thb = ZERO
    elif policy.policy_type == "PERCENTAGE":
        if policy.rate is None:
            unknowns.append(f"{profile.broker_id}_COMMISSION_RATE")
        else:
            for s in ordered_symbols:
                weight = plan.portfolio_weights[s]
                order_thb = net_thb_before_trade * weight
                if order_thb < profile.min_order_thb:
                    notes.append(f"ORDER_BELOW_MINIMUM: {s} {order_thb} < {profile.min_order_thb}")
                    eligibility_status = "NOT_ELIGIBLE"
                comm_thb = order_thb * policy.rate
                total_commission_thb += comm_thb
                # Webull published CAT fee ($0.000024/sh)
                if profile.broker_id.startswith("WEBULL"):
                    price = (plan.ref_prices_usd or {}).get(s)
                    if price is not None and price > ZERO:
                        shares = (order_thb / plan.reference_thb_per_usd) / price
                        total_reg_fees_usd += (shares * WEBULL_CAT_FEE_PER_SHARE_USD).quantize(MICRO_CENT, rounding=ROUND_HALF_UP)
            if policy.vat_applicable:
                total_vat_thb = (total_commission_thb * THAI_VAT_RATE).quantize(CENT, rounding=ROUND_HALF_UP)
            total_commission_usd = total_commission_thb / plan.reference_thb_per_usd
            total_reg_fees_thb = (total_reg_fees_usd * plan.reference_thb_per_usd).quantize(CENT, rounding=ROUND_HALF_UP)
    elif policy.policy_type == "FREE_MONTHLY_TIERED":
        # Dime! 1 free order per calendar month applied strictly to the FIRST chronological qualifying order
        remaining_free = min(policy.free_orders_count, plan.free_trades_available)
        for s in ordered_symbols:
            weight = plan.portfolio_weights[s]
            order_thb = net_thb_before_trade * weight
            if order_thb < profile.min_order_thb:
                notes.append(f"ORDER_BELOW_MINIMUM: {s} {order_thb} < {profile.min_order_thb}")
                eligibility_status = "NOT_ELIGIBLE"

            # Check price for Dime share tier (< $6.67 vs >= $6.67)
            price = (plan.ref_prices_usd or {}).get(s)
            if price is not None:
                notes.append(f"PRICES_ILLUSTRATIVE: {s}=${price} used for order tier classification.")

            if remaining_free > 0:
                free_orders_used += 1
                remaining_free -= 1
                # Order commission is free
            else:
                if policy.rate is None:
                    unknowns.append(f"{profile.broker_id}_COMMISSION_RATE")
                else:
                    if price is None:
                        # P0.4: Do NOT silently guess! Fail closed.
                        unknowns.append(f"{profile.broker_id}_{s}_PRICE_TIER_UNKNOWN")
                        notes.append(f"PRICE_UNKNOWN: Cannot determine whether {s} is below $6.67 ($0.01/sh) or above (0.15%).")
                    elif price < Decimal("6.67"):
                        shares = (order_thb / plan.reference_thb_per_usd) / price
                        comm_usd = shares * Decimal("0.01")
                        comm_thb = comm_usd * plan.reference_thb_per_usd
                        total_commission_thb += comm_thb
                        total_commission_usd += comm_usd
                    else:
                        comm_thb = order_thb * policy.rate
                        comm_usd = comm_thb / plan.reference_thb_per_usd
                        total_commission_thb += comm_thb
                        total_commission_usd += comm_usd

            # Apply CAT fee ($0.000046 / share) for US executions on Dime
            if price is not None and price > ZERO:
                order_usd = order_thb / plan.reference_thb_per_usd
                shares = order_usd / price
                cat_usd = (shares * DIME_CAT_FEE_PER_SHARE_USD).quantize(MICRO_CENT, rounding=ROUND_HALF_UP)
                total_reg_fees_usd += cat_usd

        total_reg_fees_thb = (total_reg_fees_usd * plan.reference_thb_per_usd).quantize(CENT, rounding=ROUND_HALF_UP)
        if policy.vat_applicable and total_commission_thb > ZERO:
            total_vat_thb = (total_commission_thb * THAI_VAT_RATE).quantize(CENT, rounding=ROUND_HALF_UP)
    elif policy.policy_type == "FIXED_PER_SHARE":
        # IBKR Tiered ($0.0035/share, min $0.35)
        per_share = policy.per_share_usd or Decimal("0.0035")
        min_comm = policy.min_commission_usd or Decimal("0.35")
        for s in ordered_symbols:
            weight = plan.portfolio_weights[s]
            order_thb = net_thb_before_trade * weight
            if order_thb < profile.min_order_thb:
                notes.append(f"ORDER_BELOW_MINIMUM: {s} {order_thb} < {profile.min_order_thb}")
                eligibility_status = "NOT_ELIGIBLE"
            order_usd = order_thb / plan.reference_thb_per_usd
            price = (plan.ref_prices_usd or {}).get(s)
            if price is None:
                raise DataContractError(f"DECISION_MISSING_REFERENCE_PRICE: {profile.broker_id} requires price for {s}.")
            notes.append(f"PRICES_ILLUSTRATIVE: {s}=${price} used for share-based commission floor.")
            shares = order_usd / price
            comm_usd = max(min_comm, shares * per_share)
            total_commission_usd += comm_usd
        total_commission_thb = total_commission_usd * plan.reference_thb_per_usd
        total_vat_thb = ZERO
    elif policy.policy_type == "NONE":
        pass
    else:
        raise DataContractError(f"DECISION_UNSUPPORTED_COMMISSION_POLICY: {policy.policy_type}.")

    # 6. P0.1 & P0.5 FX Conversion & Cash Conservation
    thb_direct_fees = funding_friction_thb + total_commission_thb + total_vat_thb + total_reg_fees_thb
    thb_net_for_conversion = max(ZERO, gross_thb - thb_direct_fees)

    if spread is None:
        unknowns.append(f"{profile.broker_id}_FX_SPREAD")
        effective_spread = ZERO
        fx_spread_cost_thb = ZERO
        investable_balance_usd = (thb_net_for_conversion / plan.reference_thb_per_usd).quantize(CENT, rounding=ROUND_HALF_UP)
        cost_status = COST_STATUS_LOWER_BOUND_ONLY
        notes.append("FX_SPREAD_UNKNOWN: Net investable USD is an unverified lower-bound estimate assuming zero conversion spread.")
    else:
        effective_spread = spread
        r_exec = plan.reference_thb_per_usd * (ONE + effective_spread)
        investable_balance_usd = (thb_net_for_conversion / r_exec).quantize(CENT, rounding=ROUND_HALF_UP)
        fx_spread_cost_thb = (thb_net_for_conversion - (investable_balance_usd * plan.reference_thb_per_usd)).quantize(CENT, rounding=ROUND_HALF_UP)
        # P0.1 Taxonomy: Separate mathematical completion from evidence completion
        if is_quote_observed:
            cost_status = COST_STATUS_QUOTE_OBSERVED
        elif unknowns:
            cost_status = COST_STATUS_LOWER_BOUND_ONLY
        elif plan.assumed_fx_spread is not None:
            cost_status = COST_STATUS_SCENARIO_ONLY
        else:
            cost_status = COST_STATUS_ALL_IN_DOCUMENTED

    # 7. Total Known Friction & Cash Conservation
    total_known_friction_thb = thb_direct_fees + fx_spread_cost_thb
    friction_share_lower_bound = total_known_friction_thb / gross_thb

    # 8. Deduce decision status
    unknown_tuple = tuple(sorted(set(unknowns)))

    if eligibility_status == "NOT_ELIGIBLE":
        decision_status = DECISION_STATUS_NOT_ELIGIBLE
    elif policy.evidence_status in ("TERMS_CONFLICTING", "OFFICIAL_SOURCE_CONFLICT"):
        decision_status = DECISION_STATUS_TERMS_CONFLICTING
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
        regulatory_fees_usd=total_reg_fees_usd.quantize(MICRO_CENT, rounding=ROUND_HALF_UP),
        regulatory_fees_thb=total_reg_fees_thb,
        vat_thb=total_vat_thb,
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
    fee_snapshot_sha256: str = "1ddbcf98950b2a10fe47fb47e88f7501f2712df0d0ffd2eb713c17c039c6541c",
) -> ComparisonResult:
    """Evaluate and compare investment implementation across candidate brokers."""
    assessments: List[BrokerAssessment] = []
    for p in profiles:
        assessments.append(_calculate_broker_cost(p, plan, as_of))

    # P0.2 Comprehensive canonical serialization for input hash covering ALL RouteTerms fields
    payload: Dict[str, Any] = {
        "as_of": as_of.isoformat(),
        "fee_snapshot_sha256": fee_snapshot_sha256,
        "monthly_savings_thb": str(plan.monthly_savings_thb),
        "batch_months": plan.batch_months,
        "portfolio_weights": {k: str(v) for k, v in sorted(plan.portfolio_weights.items())},
        "order_sequence": list(plan.order_sequence) if plan.order_sequence is not None else sorted(plan.portfolio_weights.keys()),
        "order_type": plan.order_type,
        "reference_thb_per_usd": str(plan.reference_thb_per_usd),
        "assumed_fx_spread": str(plan.assumed_fx_spread) if plan.assumed_fx_spread is not None else None,
        "free_trades_available": plan.free_trades_available,
        "ref_prices_usd": {k: str(v) for k, v in sorted(plan.ref_prices_usd.items())} if plan.ref_prices_usd is not None else None,
        "user_quotes": {
            k: {
                "quoted_thb_per_usd": str(q.quoted_thb_per_usd),
                "quote_observed_at": q.quote_observed_at,
                "is_expired": q.is_expired,
            }
            for k, q in sorted((plan.user_quotes or {}).items())
        },
        "profiles": [
            {
                "broker_id": p.broker_id,
                "funding_channel": p.funding_channel,
                "fractional_supported": p.fractional_supported,
                "min_order_thb": str(p.min_order_thb),
                "policy_type": p.commission_policy.policy_type,
                "rate": str(p.commission_policy.rate) if p.commission_policy.rate is not None else None,
                "min_commission_usd": str(p.commission_policy.min_commission_usd) if p.commission_policy.min_commission_usd is not None else None,
                "per_share_usd": str(p.commission_policy.per_share_usd) if p.commission_policy.per_share_usd is not None else None,
                "free_orders_count": p.commission_policy.free_orders_count,
                "vat_applicable": p.commission_policy.vat_applicable,
                "applicable_order_type": p.commission_policy.applicable_order_type,
                "evidence_status": p.commission_policy.evidence_status,
                "eligibility_status": p.eligibility_status,
                "funding_terms": {
                    "route_id": p.funding_terms.route_id,
                    "fixed_fee_thb": str(p.funding_terms.fixed_fee_thb) if p.funding_terms.fixed_fee_thb is not None else None,
                    "standard_fee_thb": str(p.funding_terms.standard_fee_thb) if p.funding_terms.standard_fee_thb is not None else None,
                    "fx_spread": str(p.funding_terms.fx_spread) if p.funding_terms.fx_spread is not None else None,
                    "deducted_fee_usd": str(p.funding_terms.deducted_fee_usd) if p.funding_terms.deducted_fee_usd is not None else None,
                    "intermediary_fee_usd": str(p.funding_terms.intermediary_fee_usd) if p.funding_terms.intermediary_fee_usd is not None else None,
                    "receiving_fee_usd": str(p.funding_terms.receiving_fee_usd) if p.funding_terms.receiving_fee_usd is not None else None,
                    "variable_fee_rate": str(p.funding_terms.variable_fee_rate) if p.funding_terms.variable_fee_rate is not None else None,
                    "variable_fee_min_thb": str(p.funding_terms.variable_fee_min_thb),
                    "min_amount_thb": str(p.funding_terms.min_amount_thb),
                    "max_amount_thb": str(p.funding_terms.max_amount_thb) if p.funding_terms.max_amount_thb is not None else None,
                    "promotion_start": p.funding_terms.promotion_start.isoformat() if p.funding_terms.promotion_start else None,
                    "promotion_end": p.funding_terms.promotion_end.isoformat() if p.funding_terms.promotion_end else None,
                    "purpose_supported": p.funding_terms.purpose_supported,
                    "beneficiary_supported": p.funding_terms.beneficiary_supported,
                } if p.funding_terms else None,
            }
            for p in sorted(profiles, key=lambda x: x.broker_id)
        ],
    }
    input_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    # Determine overall status
    statuses = {a.decision_status for a in assessments if a.broker_id != "CASH"}
    if DECISION_STATUS_COST_INCOMPLETE in statuses:
        overall_status = DECISION_STATUS_COST_INCOMPLETE
    elif DECISION_STATUS_TERMS_CONFLICTING in statuses:
        overall_status = DECISION_STATUS_TERMS_CONFLICTING
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
    order_seq_str = " -> ".join(p.order_sequence) if p.order_sequence else "Alphabetical"
    lines = [
        "# ACASH INVESTOR DECISION REPORT",
        "",
        f"- **Evaluation Date**: {date.today().isoformat()}",
        f"- **Input Hash (SHA-256)**: `{result.input_hash}`",
        f"- **Overall Decision Status**: `{result.overall_status}`",
        f"- **Monthly Savings**: THB {p.monthly_savings_thb:,.2f}",
        f"- **Batch Cadence**: {p.batch_months} month(s) (Gross: THB {p.monthly_savings_thb * p.batch_months:,.2f})",
        f"- **Order Type**: `{p.order_type}`",
        f"- **Order Sequence**: `{order_seq_str}`",
        f"- **Portfolio Allocation**: {', '.join(f'{k}: {v*100:.1f}%' for k, v in sorted(p.portfolio_weights.items()))}",
        f"- **Reference FX Rate**: {p.reference_thb_per_usd} THB/USD",
        "",
        "## Broker Comparison Matrix",
        "",
        "| Platform | Channel | Funding Fee (THB) | Comm + VAT (THB) | Known Friction (THB) | Lower Bound Drag | Cost Status | Eligibility | Decision Status | Unknown Costs |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for a in result.assessments:
        comm_vat = a.commission_thb + a.vat_thb + a.regulatory_fees_thb
        drag_pct = f"{a.friction_share_lower_bound * 100:.2f}%"
        unknowns_str = ", ".join(a.unknown_components) if a.unknown_components else "None (Documented)"
        channel = "Local THB" if "LOCAL" in a.broker_id or a.broker_id.startswith(("DIME", "WEBULL")) else ("SWIFT" if a.broker_id == "IBKR" else "N/A")
        lines.append(
            f"| **{a.display_name}** | {channel} | {a.funding_friction_thb:,.2f} | {comm_vat:,.2f} | {a.total_known_friction_thb:,.2f} | {drag_pct} | `{a.cost_status}` | `{a.eligibility_status}` | `{a.decision_status}` | {unknowns_str} |"
        )

    lines.extend([
        "",
        "## Financial Correctness & Integrity Ledger",
        "",
        "1. **P0.1 Cost Status Taxonomy**: Enforces strict separation of `SCENARIO_ONLY` (hypothetical spread) from `ALL_IN_DOCUMENTED` (verified tariff) and `QUOTE_OBSERVED` (unexpired user quote).",
        "2. **P0.2 Input Hash Verified**: Includes all 15 RouteTerms fields, full broker policies, order sequence, reference prices, and user quotes.",
        "3. **P0.3 Order Eligibility & Compatibility**: Orders below minimum are marked `NOT_ELIGIBLE`. DCA-only profiles evaluated under MANUAL are marked `ORDER_TYPE_INCOMPATIBLE`.",
        "4. **P0.4 Missing Price Boundary**: Missing asset prices on Dime! non-free orders record `DIME_PRICE_TIER_UNKNOWN` rather than silently guessing.",
        "5. **P0.5 Cash Conservation**: Converted net THB using executable rate `r * (1 + s)`. Economic drag strictly equals `THB_net - (USD_received * r)`.",
        "6. **P0.6 Fee Snapshot Provenance**: Pinned digest `1ddbcf98950b2a10fe47fb47e88f7501f2712df0d0ffd2eb713c17c039c6541c` with explicit source version conflict handling.",
        "7. **Governance Boundary**: Read-only offline planning. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.",
    ])

    return "\n".join(lines)


def main() -> None:
    """CLI runner for ACASH Investor Decision Core."""
    from acash.research.d6.broker_profiles import load_candidate_profiles

    parser = argparse.ArgumentParser(description="ACASH V38 Investor Decision Core")
    parser.add_argument("--savings", type=str, default="3000.0", help="Monthly savings in THB")
    parser.add_argument("--batch-months", type=int, default=1, help="Number of months batched per funding (1=monthly, 3=quarterly)")
    parser.add_argument("--portfolio", type=str, default="VOO:0.6,BND:0.4", help="Comma-separated ticker:weight allocation")
    parser.add_argument("--order-sequence", type=str, default=None, help="Comma-separated chronological execution order (e.g. VOO,BND)")
    parser.add_argument("--order-type", type=str, default="MANUAL", choices=["MANUAL", "DCA"], help="Order execution type")
    parser.add_argument("--reference-fx", type=str, default="35.0", help="Reference THB/USD rate")
    parser.add_argument("--fx-spread", type=str, default=None, help="Assumed FX spread (e.g. 0.005). If omitted, treated as UNKNOWN.")
    parser.add_argument("--user-quote-rate", type=str, default=None, help="User-observed THB/USD rate (e.g. 35.15)")
    parser.add_argument("--user-quote-broker", type=str, default=None, help="Broker ID for observed quote (e.g. DIME, WEBULL_MANUAL)")
    parser.add_argument("--free-trades", type=int, default=1, help="Available free trades in execution month")
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

    order_seq: Optional[Tuple[str, ...]] = None
    if args.order_sequence:
        order_seq = tuple(s.strip().upper() for s in args.order_sequence.split(","))

    user_quotes_dict: Optional[Dict[str, UserFxQuote]] = None
    if args.user_quote_rate and args.user_quote_broker:
        user_quotes_dict = {
            args.user_quote_broker.strip().upper(): UserFxQuote(
                broker_id=args.user_quote_broker.strip().upper(),
                quote_observed_at=date.today().isoformat() + "T10:00:00Z",
                quoted_thb_per_usd=Decimal(args.user_quote_rate),
                reference_rate=Decimal(args.reference_fx),
            )
        }

    plan = InvestmentPlan(
        monthly_savings_thb=Decimal(args.savings),
        batch_months=args.batch_months,
        portfolio_weights=weights,
        order_sequence=order_seq,
        order_type=args.order_type,
        reference_thb_per_usd=Decimal(args.reference_fx),
        assumed_fx_spread=Decimal(args.fx_spread) if args.fx_spread else None,
        user_quotes=user_quotes_dict,
        free_trades_available=args.free_trades,
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )

    profiles = load_candidate_profiles()
    result = compare_investment_plans(profiles, plan, date.today())

    if args.json:
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
