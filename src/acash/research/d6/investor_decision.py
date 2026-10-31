"""D6 V38 Investor Decision Core (pure, Decimal, fail-closed, offline).

Compares implementation friction for one savings batch across IBKR, Dime!
Thailand, Webull Thailand and a CASH / NO_TRADE control. Nothing here fetches
quotes, authenticates, funds an account or places an order.

Each assessment answers three questions separately:
- ``numerically_complete``: every cost component has a value (documented, observed or assumed).
- ``cost_status``: what evidence supports those values.
  - ``ALL_IN_DOCUMENTED``: official tariff terms and a documented route spread; no unknowns.
  - ``QUOTE_OBSERVED``: official tariff terms plus a current, timing-comparable user quote.
  - ``SCENARIO_ONLY``: complete only through hypothetical inputs, historical quotes or
    non-tariff (promotional, conflicting) terms.
  - ``LOWER_BOUND_ONLY``: at least one component is unknown; friction is a lower bound.
- ``eligibility_status``: whether the route, order type and security are executable for the account.

Currency incidence: THB funding fees are paid before conversion; the remaining THB is
converted at ``reference * (1 + spread)``; commissions, VAT and per-share regulatory fees
are USD charges on the converted balance. USD is rounded down to the cent and the rounding
residual is reported, so ``gross = known friction + investable USD * reference`` exactly.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.d6.route_cost import EVIDENCE_STATUSES, RouteTerms, assess_transfer

ZERO = Decimal("0")
ONE = Decimal("1")
CENT = Decimal("0.01")
THAI_VAT_RATE = Decimal("0.07")
DIME_PRICE_TIER_USD = Decimal("6.67")
DIME_LOW_PRICE_PER_SHARE_USD = Decimal("0.01")
# Comparability policy for implied spreads (not a market constant): a reference rate stamped
# further than this from the quote cannot separate spread from market movement.
QUOTE_REFERENCE_MAX_GAP = timedelta(minutes=5)
# Displayed USD amounts are rounded to the cent, so amount/rate consistency allows half a cent.
QUOTE_DISPLAY_TOLERANCE_USD = Decimal("0.005")

FEE_SNAPSHOT_VERSION = "2026-11-01b"
FEE_SNAPSHOT_SHA256 = "b837ea49d9075b5e9c5ca3a58d49636627d8e728014e5bddeedb4e6dad5c0baa"

COST_STATUS_ALL_IN_DOCUMENTED = "ALL_IN_DOCUMENTED"
COST_STATUS_QUOTE_OBSERVED = "QUOTE_OBSERVED"
COST_STATUS_SCENARIO_ONLY = "SCENARIO_ONLY"
COST_STATUS_LOWER_BOUND_ONLY = "LOWER_BOUND_ONLY"
COST_STATUS_NOT_EVALUATED = "NOT_EVALUATED"
COST_STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"

DECISION_STATUS_COMPLETE = "COMPARISON_COMPLETE"
DECISION_STATUS_CONDITIONAL = "CONDITIONAL_COMPARISON"
DECISION_STATUS_COST_INCOMPLETE = "COST_EVIDENCE_INCOMPLETE"
DECISION_STATUS_ELIGIBILITY_UNKNOWN = "SECURITY_ELIGIBILITY_UNKNOWN"
DECISION_STATUS_CASH_NO_TRADE = "CASH_NO_TRADE"
DECISION_STATUS_TERMS_CONFLICTING = "TERMS_CONFLICTING"
DECISION_STATUS_NOT_ELIGIBLE = "NOT_ELIGIBLE"

QUOTE_SOURCE_TYPES = ("IN_APP_DISPLAY", "SYNTHETIC_FIXTURE", "HYPOTHETICAL_INPUT")
QUOTE_OBSERVATIONAL_STATUSES = ("USER_OBSERVED_QUOTE", "USER_SCREENSHOT_INDICATIVE", "SYNTHETIC")
REFERENCE_RATE_KINDS = ("CONTEMPORANEOUS", "DAILY_PROXY", "HYPOTHETICAL")
SIZING_POLICY = "FEES_SOLVED_ON_FINAL_NOTIONAL"
CONFLICT_STATUSES = ("OFFICIAL_SOURCE_CONFLICT",)
POLICY_TYPES = ("FIXED_PER_SHARE", "PERCENTAGE", "FREE_MONTHLY_TIERED", "ZERO_PROMOTIONAL", "NONE")
ORDER_TYPES = ("MANUAL", "DCA")
FUNDING_CHANNELS = ("SWIFT_CROSS_BORDER", "LOCAL_THB_QR_ATS", "NONE")
ELIGIBILITY_ORDER = ("DOCUMENTED", "CONDITIONALLY_ELIGIBLE", "ACCOUNT_SPECIFIC_UNVERIFIED", "NOT_ELIGIBLE")

SPREAD_UNKNOWN = "UNKNOWN"
SPREAD_ASSUMED = "HYPOTHETICAL_INPUT"
SPREAD_ROUTE_TERMS = "ROUTE_TERMS"
SPREAD_QUOTE_CURRENT = "USER_QUOTE_CURRENT"
SPREAD_QUOTE_HISTORICAL = "USER_QUOTE_HISTORICAL"
SPREAD_QUOTE_SYNTHETIC = "SYNTHETIC_QUOTE"
SPREAD_QUOTE_INDICATIVE = "USER_QUOTE_INDICATIVE"
SPREAD_QUOTE_REFERENCE_LIMITED = "USER_QUOTE_REFERENCE_LIMITED"


def _money(value: Optional[Decimal], context: str, *, positive: bool = False) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal) or not value.is_finite() or value < ZERO or (positive and value == ZERO):
        raise DataContractError(f"DECISION_INVALID_MONEY: {context} {value!r}.")


def _fraction(value: Optional[Decimal], context: str) -> None:
    _money(value, context)
    if value is not None and value > ONE:
        raise DataContractError(f"DECISION_INVALID_FRACTION: {context} {value!r}.")


def _timestamp(value: str, context: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise DataContractError(f"DECISION_INVALID_TIMESTAMP: {context} {value!r}.") from exc
    if parsed.tzinfo is None:
        raise DataContractError(f"DECISION_TIMESTAMP_WITHOUT_ZONE: {context} {value!r}.")
    return parsed


def _worse(current: str, candidate: str) -> str:
    return max(current, candidate, key=ELIGIBILITY_ORDER.index)


@dataclass(frozen=True)
class UserFxQuote:
    """User-reported in-app THB -> USD quote (offline observation; never refreshed)."""

    broker_id: str
    quote_observed_at: str
    quoted_thb_per_usd: Decimal
    quote_direction: str = "THB_TO_USD"
    source_currency: str = "THB"
    target_currency: str = "USD"
    source_amount: Optional[Decimal] = None
    target_amount: Optional[Decimal] = None
    quote_valid_until: Optional[str] = None
    reference_rate: Optional[Decimal] = None
    reference_rate_timestamp: Optional[str] = None
    reference_rate_source: Optional[str] = None
    reference_rate_kind: str = "CONTEMPORANEOUS"
    quote_source_type: str = "IN_APP_DISPLAY"
    observational_status: str = "USER_OBSERVED_QUOTE"

    def __post_init__(self) -> None:
        if not self.broker_id.strip():
            raise DataContractError("USER_QUOTE_EMPTY_BROKER_ID.")
        if (
            self.quote_source_type not in QUOTE_SOURCE_TYPES
            or self.observational_status not in QUOTE_OBSERVATIONAL_STATUSES
            or self.reference_rate_kind not in REFERENCE_RATE_KINDS
        ):
            raise DataContractError(f"USER_QUOTE_UNKNOWN_PROVENANCE: {self.broker_id}.")
        if (self.quote_source_type == "IN_APP_DISPLAY") != self.observational_status.startswith("USER_"):
            raise DataContractError(f"USER_QUOTE_PROVENANCE_CONTRADICTION: {self.broker_id}.")
        if (self.quote_direction, self.source_currency, self.target_currency) != ("THB_TO_USD", "THB", "USD"):
            raise DataContractError(
                f"USER_QUOTE_UNSUPPORTED_DIRECTION: {self.quote_direction} {self.source_currency}->{self.target_currency}."
            )
        _money(self.quoted_thb_per_usd, f"{self.broker_id} quoted_thb_per_usd", positive=True)
        _money(self.reference_rate, f"{self.broker_id} reference_rate", positive=True)
        _money(self.source_amount, f"{self.broker_id} source_amount", positive=True)
        _money(self.target_amount, f"{self.broker_id} target_amount", positive=True)
        observed = _timestamp(self.quote_observed_at, "quote_observed_at")
        if self.quote_valid_until is not None and _timestamp(self.quote_valid_until, "quote_valid_until") < observed:
            raise DataContractError(f"USER_QUOTE_VALIDITY_BEFORE_OBSERVATION: {self.broker_id}.")
        if self.reference_rate_timestamp is not None:
            _timestamp(self.reference_rate_timestamp, "reference_rate_timestamp")
        if (self.source_amount is None) != (self.target_amount is None):
            raise DataContractError(f"USER_QUOTE_PARTIAL_AMOUNTS: {self.broker_id}.")
        if self.source_amount is not None and self.target_amount is not None:
            tolerance = QUOTE_DISPLAY_TOLERANCE_USD * self.quoted_thb_per_usd
            if abs(self.source_amount - self.target_amount * self.quoted_thb_per_usd) > tolerance:
                raise DataContractError(f"USER_QUOTE_AMOUNT_RATE_MISMATCH: {self.broker_id}.")

    @property
    def implied_spread(self) -> Optional[Decimal]:
        """``quoted / reference - 1`` in THB-per-USD terms; includes market moves and basis differences."""
        if self.reference_rate is None:
            return None
        return self.quoted_thb_per_usd / self.reference_rate - ONE

    @property
    def spread_basis(self) -> str:
        if self.reference_rate is None:
            return "NO_REFERENCE"
        if self.reference_rate_kind == "HYPOTHETICAL":
            return "HYPOTHETICAL_REFERENCE"
        if self.reference_rate_kind == "DAILY_PROXY":
            return "DAILY_REFERENCE_PROXY"
        if self.reference_rate_timestamp is None:
            return "REFERENCE_TIME_UNKNOWN"
        gap = abs(_timestamp(self.reference_rate_timestamp, "reference") - _timestamp(self.quote_observed_at, "quote"))
        return "CONTEMPORANEOUS_COMPARABLE_REFERENCE" if gap <= QUOTE_REFERENCE_MAX_GAP else "TIMING_MISMATCH"

    @property
    def is_user_observed_notional_quote(self) -> bool:
        """User-reported (not authenticated) in-app quote for a stated THB/USD notional."""
        return self.observational_status == "USER_OBSERVED_QUOTE" and self.source_amount is not None

    def is_current(self, evaluated_at: Optional[str]) -> bool:
        """True only when a validity window is known and the evaluation instant falls inside it."""
        if evaluated_at is None or self.quote_valid_until is None:
            return False
        moment = _timestamp(evaluated_at, "evaluated_at")
        return _timestamp(self.quote_observed_at, "quote") <= moment <= _timestamp(self.quote_valid_until, "valid_until")


@dataclass(frozen=True)
class CommissionPolicy:
    policy_type: str
    rate: Optional[Decimal] = None
    min_commission_usd: Optional[Decimal] = None
    per_share_usd: Optional[Decimal] = None
    free_orders_count: int = 0
    vat_applicable: bool = False
    applicable_order_type: str = "ALL"
    evidence_status: str = "OFFICIAL_PROVIDER_TARIFF"
    cat_fee_per_share_usd: Optional[Decimal] = None
    pass_through_fees_known: bool = True
    # Separate schedule for pure fractional-share trades (e.g. IBKR Footnote 11); mixed
    # whole/fractional orders keep the cheaper schedule as a lower bound and stay UNKNOWN.
    fractional_rate: Optional[Decimal] = None
    fractional_min_usd: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if self.policy_type not in POLICY_TYPES:
            raise DataContractError(f"DECISION_UNSUPPORTED_COMMISSION_POLICY: {self.policy_type}.")
        if self.applicable_order_type not in ("ALL",) + ORDER_TYPES:
            raise DataContractError(f"DECISION_UNSUPPORTED_ORDER_TYPE: {self.applicable_order_type}.")
        if self.evidence_status not in EVIDENCE_STATUSES:
            raise DataContractError(f"DECISION_UNKNOWN_EVIDENCE_STATUS: {self.evidence_status}.")
        _fraction(self.rate, f"{self.policy_type} rate")
        _money(self.min_commission_usd, f"{self.policy_type} min_commission_usd")
        _money(self.per_share_usd, f"{self.policy_type} per_share_usd")
        _money(self.cat_fee_per_share_usd, f"{self.policy_type} cat_fee_per_share_usd")
        _fraction(self.fractional_rate, f"{self.policy_type} fractional_rate")
        _money(self.fractional_min_usd, f"{self.policy_type} fractional_min_usd")
        if self.free_orders_count < 0:
            raise DataContractError(f"DECISION_INVALID_FREE_ORDERS: {self.free_orders_count}.")


@dataclass(frozen=True)
class SecurityEligibility:
    """Per-platform, per-symbol eligibility; ``None`` means UNKNOWN, never eligible."""

    platform_id: str
    symbol: str
    instrument_type: str
    searchable: Optional[bool]
    whole_share_eligible: Optional[bool]
    fractional_eligible: Optional[bool]
    manual_order_eligible: Optional[bool]
    dca_eligible: Optional[bool]
    min_notional_usd: Optional[Decimal]
    trading_session: str
    account_permission: str
    source_url: str
    verified_date: str
    evidence_status: str

    def __post_init__(self) -> None:
        if not self.platform_id.strip() or not self.symbol.strip():
            raise DataContractError("ELIGIBILITY_EMPTY_KEY.")
        if self.evidence_status not in EVIDENCE_STATUSES:
            raise DataContractError(f"ELIGIBILITY_UNKNOWN_EVIDENCE_STATUS: {self.evidence_status}.")
        if self.account_permission not in ("VERIFIED", "DENIED", "UNVERIFIED"):
            raise DataContractError(f"ELIGIBILITY_BAD_ACCOUNT_PERMISSION: {self.account_permission}.")
        _money(self.min_notional_usd, f"{self.symbol} min_notional_usd")


@dataclass(frozen=True)
class BrokerProfile:
    broker_id: str
    display_name: str
    funding_channel: str
    commission_policy: CommissionPolicy
    fractional_supported: bool
    min_order_thb: Decimal = ZERO
    min_order_usd: Decimal = ZERO
    funding_terms: Optional[RouteTerms] = None
    platform_id: str = ""
    security_eligibility: Tuple[SecurityEligibility, ...] = ()
    eligibility_status: str = "ACCOUNT_SPECIFIC_UNVERIFIED"
    evidence_notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.broker_id.strip():
            raise DataContractError("DECISION_EMPTY_BROKER_ID.")
        if not self.platform_id:
            object.__setattr__(self, "platform_id", self.broker_id)
        _money(self.min_order_usd, f"{self.broker_id} min_order_usd")
        keys = [(e.platform_id, e.symbol) for e in self.security_eligibility]
        if len(set(keys)) != len(keys) or any(p != self.platform_id for p, _ in keys):
            raise DataContractError(f"DECISION_BAD_ELIGIBILITY_MATRIX: {self.broker_id}.")
        if self.funding_channel not in FUNDING_CHANNELS:
            raise DataContractError(f"DECISION_UNKNOWN_FUNDING_CHANNEL: {self.funding_channel}.")
        if self.eligibility_status not in ELIGIBILITY_ORDER:
            raise DataContractError(f"DECISION_UNKNOWN_ELIGIBILITY: {self.eligibility_status}.")
        _money(self.min_order_thb, f"{self.broker_id} min_order_thb")


@dataclass(frozen=True)
class InvestmentPlan:
    monthly_savings_thb: Decimal
    reference_thb_per_usd: Decimal
    portfolio_weights: Mapping[str, Decimal]
    batch_months: int = 1
    order_sequence: Optional[Tuple[str, ...]] = None
    order_type: str = "MANUAL"
    assumed_fx_spread: Optional[Decimal] = None
    user_quotes: Optional[Mapping[str, UserFxQuote]] = None
    free_trades_available: int = 1
    ref_prices_usd: Optional[Mapping[str, Decimal]] = None
    evaluated_at: Optional[str] = None

    def __post_init__(self) -> None:
        _money(self.monthly_savings_thb, "monthly_savings_thb", positive=True)
        _money(self.reference_thb_per_usd, "reference_thb_per_usd", positive=True)
        _fraction(self.assumed_fx_spread, "assumed_fx_spread")
        if type(self.batch_months) is not int or self.batch_months < 1:
            raise DataContractError(f"DECISION_INVALID_BATCH_MONTHS: {self.batch_months}.")
        if self.order_type not in ORDER_TYPES:
            raise DataContractError(f"DECISION_UNSUPPORTED_ORDER_TYPE: {self.order_type}.")
        if self.free_trades_available < 0:
            raise DataContractError(f"DECISION_INVALID_FREE_TRADES: {self.free_trades_available}.")
        if self.evaluated_at is not None:
            _timestamp(self.evaluated_at, "evaluated_at")
        if not self.portfolio_weights:
            raise DataContractError("DECISION_EMPTY_PORTFOLIO_WEIGHTS.")
        weight_sum = ZERO
        seen = set()
        for sym, w in self.portfolio_weights.items():
            if not sym.strip() or sym != sym.strip().upper() or sym in seen:
                raise DataContractError(f"DECISION_INVALID_SYMBOL: {sym!r}.")
            seen.add(sym)
            _fraction(w, f"weight {sym}")
            weight_sum += w
        if weight_sum != ONE:
            raise DataContractError(f"DECISION_WEIGHTS_NOT_ONE: sum={weight_sum}.")
        if self.order_sequence is not None and (
            set(self.order_sequence) != seen or len(self.order_sequence) != len(seen)
        ):
            raise DataContractError("DECISION_ORDER_SEQUENCE_MISMATCH: must match portfolio symbols exactly.")
        for sym, price in (self.ref_prices_usd or {}).items():
            _money(price, f"price {sym}", positive=True)
        for key, quote in (self.user_quotes or {}).items():
            if quote.broker_id != key:
                raise DataContractError(f"USER_QUOTE_BROKER_MISMATCH: key {key} != {quote.broker_id}.")


@dataclass(frozen=True)
class BrokerAssessment:
    broker_id: str
    display_name: str
    funding_channel: str
    gross_funding_thb: Decimal
    funding_friction_thb: Decimal
    fx_spread_cost_thb: Decimal
    commission_usd: Decimal
    commission_thb: Decimal
    regulatory_fees_usd: Decimal
    regulatory_fees_thb: Decimal
    vat_thb: Decimal
    rounding_residual_thb: Decimal
    total_known_friction_thb: Decimal
    friction_share_lower_bound: Decimal
    investable_balance_usd: Optional[Decimal]
    order_notionals_usd: Tuple[Tuple[str, Decimal], ...]
    unknown_components: Tuple[str, ...]
    numerically_complete: bool
    spread_source: str
    cost_status: str
    eligibility_status: str
    free_orders_used: int
    total_orders_count: int
    decision_status: str
    evidence_notes: Tuple[str, ...]


@dataclass(frozen=True)
class ComparisonResult:
    as_of: date
    plan: InvestmentPlan
    assessments: Tuple[BrokerAssessment, ...]
    input_hash: str
    fee_snapshot_sha256: str
    overall_status: str


def _fixed_assessment(
    profile: BrokerProfile, gross: Decimal, notes: List[str], *, cost_status: str, eligibility: str, decision: str
) -> BrokerAssessment:
    is_cash = decision == DECISION_STATUS_CASH_NO_TRADE
    return BrokerAssessment(
        broker_id=profile.broker_id,
        display_name=profile.display_name,
        funding_channel=profile.funding_channel,
        gross_funding_thb=gross,
        funding_friction_thb=ZERO,
        fx_spread_cost_thb=ZERO,
        commission_usd=ZERO,
        commission_thb=ZERO,
        regulatory_fees_usd=ZERO,
        regulatory_fees_thb=ZERO,
        vat_thb=ZERO,
        rounding_residual_thb=ZERO,
        total_known_friction_thb=ZERO,
        friction_share_lower_bound=ZERO,
        investable_balance_usd=ZERO if is_cash else None,
        order_notionals_usd=(),
        unknown_components=(),
        numerically_complete=is_cash,
        spread_source="NOT_APPLICABLE",
        cost_status=cost_status,
        eligibility_status=eligibility,
        free_orders_used=0,
        total_orders_count=0,
        decision_status=decision,
        evidence_notes=tuple(notes),
    )


def _not_eligible(profile: BrokerProfile, gross: Decimal, notes: List[str], eligibility: str = "NOT_ELIGIBLE") -> BrokerAssessment:
    return _fixed_assessment(
        profile, gross, notes, cost_status=COST_STATUS_NOT_EVALUATED, eligibility=eligibility, decision=DECISION_STATUS_NOT_ELIGIBLE
    )


def _select_spread(profile: BrokerProfile, plan: InvestmentPlan, as_of: date, notes: List[str]) -> Tuple[Optional[Decimal], str]:
    quote = (plan.user_quotes or {}).get(profile.broker_id)
    if quote is not None:
        spread = quote.implied_spread
        if spread is None:
            notes.append("USER_QUOTE_WITHOUT_REFERENCE: implied spread cannot be computed.")
        else:
            current = plan.evaluated_at is not None and quote.is_current(plan.evaluated_at) and (
                _timestamp(plan.evaluated_at, "evaluated_at").date() == as_of
            )
            basis = quote.spread_basis
            if quote.observational_status == "SYNTHETIC":
                notes.append("SYNTHETIC_QUOTE: fixture or hypothetical quote; not market evidence.")
                return spread, SPREAD_QUOTE_SYNTHETIC
            if not current:
                notes.append(f"USER_QUOTE_STALE: quote observed {quote.quote_observed_at} kept as historical observation only.")
                return spread, SPREAD_QUOTE_HISTORICAL
            if not quote.is_user_observed_notional_quote:
                notes.append("USER_QUOTE_INDICATIVE: displayed rate without a stated notional; spread is an estimate.")
                return spread, SPREAD_QUOTE_INDICATIVE
            if basis != "CONTEMPORANEOUS_COMPARABLE_REFERENCE":
                notes.append(f"USER_QUOTE_REFERENCE_{basis}: implied spread is an estimate that may include market movement.")
                return spread, SPREAD_QUOTE_REFERENCE_LIMITED
            notes.append("USER_QUOTE_CURRENT: user-reported, not independently authenticated.")
            return spread, SPREAD_QUOTE_CURRENT
    if plan.assumed_fx_spread is not None:
        return plan.assumed_fx_spread, SPREAD_ASSUMED
    return None, SPREAD_UNKNOWN


def _order_eligibility(
    profile: BrokerProfile, plan: InvestmentPlan, sym: str, needs_fraction: bool, notional: Decimal, notes: List[str]
) -> Tuple[bool, bool]:
    """Return ``(not_eligible, unverified)`` for one symbol on one platform."""
    entry = next((e for e in profile.security_eligibility if e.symbol == sym), None)
    if needs_fraction and not profile.fractional_supported:
        notes.append(f"FRACTIONAL_NOT_SUPPORTED: {sym}")
        return True, False
    if entry is None:
        notes.append(f"SECURITY_ELIGIBILITY_UNKNOWN: {sym} on {profile.platform_id}.")
        return False, True
    order_flag = entry.manual_order_eligible if plan.order_type == "MANUAL" else entry.dca_eligible
    share_flag = entry.fractional_eligible if needs_fraction else entry.whole_share_eligible
    flags = (entry.searchable, order_flag, share_flag)
    below_min = entry.min_notional_usd is not None and notional < entry.min_notional_usd
    if False in flags or entry.account_permission == "DENIED" or below_min:
        notes.append(f"SECURITY_NOT_ELIGIBLE: {sym} on {profile.platform_id} ({plan.order_type}, fractional={needs_fraction}).")
        return True, False
    if None in flags or entry.account_permission != "VERIFIED":
        notes.append(f"SECURITY_ELIGIBILITY_UNVERIFIED: {sym} on {profile.platform_id}.")
        return False, True
    return False, False


def _solve_order(allocation: Decimal, rate: Decimal, minimum: Decimal, vat_rate: Decimal, per_value_fee: Decimal) -> Tuple[Decimal, Decimal]:
    """Solve ``allocation = n + max(minimum, rate*n)*(1+vat) + per_value_fee*n`` for the final notional ``n``."""
    notional = allocation / (ONE + rate * (ONE + vat_rate) + per_value_fee)
    if rate * notional < minimum:
        notional = (allocation - minimum * (ONE + vat_rate)) / (ONE + per_value_fee)
    return notional, max(minimum, rate * notional)


def _calculate_broker_cost(profile: BrokerProfile, plan: InvestmentPlan, as_of: date) -> BrokerAssessment:
    gross = plan.monthly_savings_thb * Decimal(plan.batch_months)
    ref = plan.reference_thb_per_usd
    notes: List[str] = list(profile.evidence_notes)
    unknowns: List[str] = []
    policy = profile.commission_policy
    bid = profile.broker_id

    if profile.funding_channel == "NONE":
        if bid != "CASH":
            raise DataContractError(f"DECISION_NONE_CHANNEL_NOT_CASH: {bid}.")
        notes.append("Baseline control: savings stay in THB cash; no transfer, conversion or market exposure.")
        return _fixed_assessment(
            profile, gross, notes, cost_status=COST_STATUS_NOT_APPLICABLE, eligibility="DOCUMENTED",
            decision=DECISION_STATUS_CASH_NO_TRADE,
        )

    if policy.applicable_order_type not in ("ALL", plan.order_type):
        notes.append(f"ORDER_TYPE_INCOMPATIBLE: plan {plan.order_type}; profile requires {policy.applicable_order_type}.")
        return _not_eligible(profile, gross, notes, "ORDER_TYPE_INCOMPATIBLE")

    eligibility = profile.eligibility_status
    security_unknown = False
    spread, spread_source = _select_spread(profile, plan, as_of, notes)

    thb_route_fee = ZERO
    usd_route_fee = ZERO
    route_documented = False
    if profile.funding_channel == "SWIFT_CROSS_BORDER":
        terms = profile.funding_terms
        if terms is None:
            raise DataContractError(f"DECISION_MISSING_ROUTE_TERMS: {bid}.")
        if gross < terms.min_amount_thb or (terms.max_amount_thb is not None and gross > terms.max_amount_thb):
            notes.append(f"AMOUNT_OUT_OF_ROUTE_RANGE: THB {gross} outside route limits.")
            return _not_eligible(profile, gross, notes)
        try:
            transfer = assess_transfer(terms, gross, ref, as_of)
        except DataContractError as exc:
            if not str(exc).startswith("ROUTE_FEE_EXCEEDS_AMOUNT"):
                raise
            notes.append(f"FEES_EXCEED_FUNDING: {exc}")
            return _not_eligible(profile, gross, notes)
        thb_route_fee = transfer.thb_fee_known
        usd_route_fee = transfer.usd_fee_known
        unknowns.extend(c for c in transfer.unknown_components if c != "FX_SPREAD")
        eligibility = _worse(eligibility, transfer.eligibility_status)
        route_documented = terms.evidence_status == "OFFICIAL_PROVIDER_TARIFF"
        if spread is None and terms.fx_spread is not None:
            spread, spread_source = terms.fx_spread, SPREAD_ROUTE_TERMS
    elif profile.funding_terms is not None:
        raise DataContractError(f"DECISION_ROUTE_TERMS_ON_LOCAL_CHANNEL: {bid}.")

    thb_to_convert = gross - thb_route_fee
    if spread is None:
        unknowns.append(f"{bid}_FX_SPREAD")
        notes.append("FX_SPREAD_UNKNOWN: converted at the reference rate; USD is an upper bound and friction a lower bound.")
        rate_used = ref
    else:
        rate_used = ref * (ONE + spread)
    usd_bought = thb_to_convert / rate_used
    fx_cost_thb = thb_to_convert - usd_bought * ref
    usd_converted = usd_bought - usd_route_fee
    if usd_converted <= ZERO:
        notes.append("FEES_EXCEED_FUNDING: USD funding deductions consume the converted balance.")
        return _not_eligible(profile, gross, notes)

    ordered = plan.order_sequence if plan.order_sequence is not None else tuple(sorted(plan.portfolio_weights))
    prices = plan.ref_prices_usd or {}
    remaining_free = min(policy.free_orders_count, plan.free_trades_available)
    free_used = 0
    commission_usd = ZERO
    vat_usd = ZERO
    regulatory_usd = ZERO
    notionals: List[Tuple[str, Decimal]] = []

    vat_rate = THAI_VAT_RATE if policy.vat_applicable else ZERO
    for sym in ordered:
        allocation = usd_converted * plan.portfolio_weights[sym]
        price = prices.get(sym)
        cat_rate = ZERO
        if policy.cat_fee_per_share_usd is not None:
            if price is None:
                unknowns.append(f"{bid}_{sym}_CAT_FEE")
            else:
                cat_rate = policy.cat_fee_per_share_usd / price
        rate, minimum = ZERO, ZERO
        fractional_schedule: Optional[Tuple[Decimal, Decimal]] = None
        if policy.policy_type == "PERCENTAGE":
            if policy.rate is None:
                unknowns.append(f"{bid}_COMMISSION_RATE")
            else:
                rate = policy.rate
        elif policy.policy_type == "FREE_MONTHLY_TIERED":
            if remaining_free > 0:
                remaining_free -= 1
                free_used += 1
            elif policy.rate is None:
                unknowns.append(f"{bid}_COMMISSION_RATE")
            elif price is None:
                unknowns.append(f"{bid}_{sym}_PRICE_TIER_UNKNOWN")
                notes.append(f"PRICE_UNKNOWN: cannot tell whether {sym} is below USD {DIME_PRICE_TIER_USD}.")
            elif price < DIME_PRICE_TIER_USD:
                rate = DIME_LOW_PRICE_PER_SHARE_USD / price
            else:
                rate = policy.rate
        elif policy.policy_type == "FIXED_PER_SHARE":
            if policy.per_share_usd is None or policy.min_commission_usd is None:
                unknowns.append(f"{bid}_COMMISSION_SCHEDULE")
            else:
                minimum = policy.min_commission_usd
                if price is None:
                    unknowns.append(f"{bid}_{sym}_SHARE_COUNT")
                else:
                    rate = policy.per_share_usd / price
                if policy.fractional_rate is not None and policy.fractional_min_usd is not None:
                    fractional_schedule = (policy.fractional_rate, policy.fractional_min_usd)
        notional, commission = _solve_order(allocation, rate, minimum, vat_rate, cat_rate)
        if fractional_schedule is not None:
            f_notional, f_commission = _solve_order(allocation, *fractional_schedule, vat_rate, cat_rate)
            whole = price is not None and notional > ZERO and (notional / price) == (notional / price).to_integral_value()
            pure_fraction = price is not None and notional < price and f_notional < price
            if pure_fraction:
                notional, commission = f_notional, f_commission
            elif not whole:
                if f_commission < commission:
                    notional, commission = f_notional, f_commission
                if price is not None:
                    unknowns.append(f"{bid}_{sym}_MIXED_ORDER_COMMISSION")
                    notes.append(f"MIXED_ORDER: {sym} whole/fractional pricing split undocumented; cheaper schedule kept as lower bound.")
        if notional <= ZERO:
            notes.append(f"FEES_EXCEED_ORDER: {sym} charges consume the allocation.")
            return _not_eligible(profile, gross, notes)
        vat = commission * vat_rate
        regulatory = notional * cat_rate
        shares = notional / price if price is not None else None
        needs_fraction = shares is None or shares != shares.to_integral_value()
        commission_usd += commission
        vat_usd += vat
        regulatory_usd += regulatory
        notionals.append((sym, notional))
        if notional * ref < profile.min_order_thb or notional < profile.min_order_usd:
            eligibility = "NOT_ELIGIBLE"
            notes.append(f"ORDER_BELOW_MINIMUM: {sym} post-fee notional USD {notional.quantize(CENT, rounding=ROUND_DOWN)}.")
        not_eligible, unverified = _order_eligibility(profile, plan, sym, needs_fraction, notional, notes)
        if not_eligible:
            eligibility = "NOT_ELIGIBLE"
        security_unknown = security_unknown or unverified

    if policy.evidence_status in CONFLICT_STATUSES:
        notes.append("TERMS_CONFLICTING: official provider sources disagree on this commission.")
    if not policy.pass_through_fees_known:
        unknowns.append(f"{bid}_PASS_THROUGH_FEES")
    investable = sum((n for _, n in notionals), ZERO).quantize(CENT, rounding=ROUND_DOWN)
    total_friction = gross - investable * ref
    known_components = (
        thb_route_fee + usd_route_fee * ref + fx_cost_thb + commission_usd * ref + vat_usd * ref + regulatory_usd * ref
    )
    unknown_tuple = tuple(sorted(set(unknowns)))
    official = policy.evidence_status == "OFFICIAL_PROVIDER_TARIFF"

    if unknown_tuple:
        cost_status = COST_STATUS_LOWER_BOUND_ONLY
    elif official and spread_source == SPREAD_QUOTE_CURRENT:
        cost_status = COST_STATUS_QUOTE_OBSERVED
    elif official and spread_source == SPREAD_ROUTE_TERMS and route_documented:
        cost_status = COST_STATUS_ALL_IN_DOCUMENTED
    else:
        cost_status = COST_STATUS_SCENARIO_ONLY

    if security_unknown:
        eligibility = _worse(eligibility, "ACCOUNT_SPECIFIC_UNVERIFIED")
    if eligibility == "NOT_ELIGIBLE":
        decision = DECISION_STATUS_NOT_ELIGIBLE
    elif policy.evidence_status in CONFLICT_STATUSES:
        decision = DECISION_STATUS_TERMS_CONFLICTING
    elif unknown_tuple:
        decision = DECISION_STATUS_COST_INCOMPLETE
    elif security_unknown:
        decision = DECISION_STATUS_ELIGIBILITY_UNKNOWN
    elif eligibility != "DOCUMENTED" or cost_status == COST_STATUS_SCENARIO_ONLY:
        decision = DECISION_STATUS_CONDITIONAL
    else:
        decision = DECISION_STATUS_COMPLETE

    return BrokerAssessment(
        broker_id=bid,
        display_name=profile.display_name,
        funding_channel=profile.funding_channel,
        gross_funding_thb=gross,
        funding_friction_thb=thb_route_fee + usd_route_fee * ref,
        fx_spread_cost_thb=fx_cost_thb,
        commission_usd=commission_usd,
        commission_thb=commission_usd * ref,
        regulatory_fees_usd=regulatory_usd,
        regulatory_fees_thb=regulatory_usd * ref,
        vat_thb=vat_usd * ref,
        rounding_residual_thb=total_friction - known_components,
        total_known_friction_thb=total_friction,
        friction_share_lower_bound=total_friction / gross,
        investable_balance_usd=investable,
        order_notionals_usd=tuple(notionals),
        unknown_components=unknown_tuple,
        numerically_complete=not unknown_tuple,
        spread_source=spread_source,
        cost_status=cost_status,
        eligibility_status=eligibility,
        free_orders_used=free_used,
        total_orders_count=len(ordered),
        decision_status=decision,
        evidence_notes=tuple(notes),
    )


def _plain(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def comparison_input_hash(
    profiles: Sequence[BrokerProfile], plan: InvestmentPlan, as_of: date, fee_snapshot_sha256: str
) -> str:
    """SHA-256 over every input field (plan, quotes, profiles, route terms, as-of, snapshot digest)."""
    payload = {
        "as_of": as_of.isoformat(),
        "fee_snapshot_sha256": fee_snapshot_sha256,
        "plan": _plain(asdict(plan)),
        "profiles": [_plain(asdict(p)) for p in sorted(profiles, key=lambda p: p.broker_id)],
    }
    return CanonicalConfigSerializer.compute_sha256(payload)


def compare_investment_plans(
    profiles: Sequence[BrokerProfile],
    plan: InvestmentPlan,
    as_of: date,
    fee_snapshot_sha256: str = FEE_SNAPSHOT_SHA256,
) -> ComparisonResult:
    """Evaluate one savings batch across candidate profiles; never ranks brokers."""
    ids = [p.broker_id for p in profiles]
    if len(set(ids)) != len(ids):
        raise DataContractError("DECISION_DUPLICATE_BROKER_ID.")
    assessments = tuple(_calculate_broker_cost(p, plan, as_of) for p in profiles)
    statuses = {a.decision_status for a in assessments if a.broker_id != "CASH"}
    for status in (
        DECISION_STATUS_COST_INCOMPLETE,
        DECISION_STATUS_TERMS_CONFLICTING,
        DECISION_STATUS_ELIGIBILITY_UNKNOWN,
        DECISION_STATUS_CONDITIONAL,
        DECISION_STATUS_COMPLETE,
    ):
        if status in statuses:
            overall = status
            break
    else:
        overall = DECISION_STATUS_NOT_ELIGIBLE if statuses else DECISION_STATUS_CASH_NO_TRADE
    return ComparisonResult(
        as_of=as_of,
        plan=plan,
        assessments=assessments,
        input_hash=comparison_input_hash(profiles, plan, as_of, fee_snapshot_sha256),
        fee_snapshot_sha256=fee_snapshot_sha256,
        overall_status=overall,
    )


def comparison_to_dict(result: ComparisonResult) -> Dict[str, Any]:
    def _strings(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, Mapping):
            return {k: _strings(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_strings(v) for v in value]
        return value

    return {
        "as_of": result.as_of.isoformat(),
        "fee_snapshot_version": FEE_SNAPSHOT_VERSION,
        "fee_snapshot_sha256": result.fee_snapshot_sha256,
        "input_hash": result.input_hash,
        "overall_status": result.overall_status,
        "plan": _strings(_plain(asdict(result.plan))),
        "assessments": [_strings(asdict(a)) for a in result.assessments],
    }


def _thb(value: Decimal) -> str:
    return f"{value.quantize(CENT):,.2f}"


def format_markdown_report(result: ComparisonResult) -> str:
    """Deterministic Markdown report; contains no wall-clock value."""
    p = result.plan
    hypothetical = [f"reference FX {p.reference_thb_per_usd} THB/USD (HYPOTHETICAL_INPUT unless sourced)"]
    if p.assumed_fx_spread is not None:
        hypothetical.append(f"assumed FX spread {p.assumed_fx_spread}")
    if p.ref_prices_usd:
        hypothetical.append("prices " + ", ".join(f"{k} USD {v}" for k, v in sorted(p.ref_prices_usd.items())))
    lines = [
        "# ACASH Investor Decision Report",
        "",
        f"- Scenario date: {result.as_of.isoformat()}",
        f"- Fee snapshot: version {FEE_SNAPSHOT_VERSION}, SHA-256 `{result.fee_snapshot_sha256}`",
        f"- Input SHA-256: `{result.input_hash}`",
        f"- Overall status: `{result.overall_status}`",
        f"- Savings: THB {_thb(p.monthly_savings_thb)} x {p.batch_months} month(s); order type `{p.order_type}`; "
        + "weights " + ", ".join(f"{k} {v}" for k, v in sorted(p.portfolio_weights.items())),
        f"- Hypothetical inputs: {'; '.join(hypothetical)}",
        "",
        "| Platform | Funding THB | Commission+VAT THB | Regulatory THB | FX cost THB | Known friction THB | Share | Numerically complete | Cost evidence | Spread source | Eligibility | Decision | Unknown |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for a in result.assessments:
        lines.append(
            f"| {a.display_name} | {_thb(a.funding_friction_thb)} | {_thb(a.commission_thb + a.vat_thb)} | "
            f"{_thb(a.regulatory_fees_thb)} | {_thb(a.fx_spread_cost_thb)} | {_thb(a.total_known_friction_thb)} | "
            f"{(a.friction_share_lower_bound * 100).quantize(CENT)}% | {'yes' if a.numerically_complete else 'no'} | "
            f"`{a.cost_status}` | `{a.spread_source}` | `{a.eligibility_status}` | `{a.decision_status}` | "
            f"{', '.join(a.unknown_components) or '-'} |"
        )
    lines += [
        "",
        "No ranking is produced: unknown or hypothetical components can reverse any ordering. "
        "CASH / NO TRADE has zero friction and zero market exposure.",
        "",
        f"Sizing policy `{SIZING_POLICY}`: each allocation splits exactly into final notional plus commission, VAT "
        "and per-share regulatory fees charged on that final notional; minimum-order and fractional checks use it. "
        "THB funding fees apply before conversion; USD deducted, intermediary and receiving fees apply after it.",
        "",
        "## Disclosures (informational, not advice)",
        "",
        "- Reference FX provenance: the reference rate is a scenario input. A daily central-bank reference "
        "rate is a `DAILY_REFERENCE_PROXY`, not a contemporaneous mid-rate; implied spreads against it include "
        "intraday movement.",
        "- Cadence: batching months lowers fixed per-transfer and per-order charges but keeps savings in cash "
        "longer. No expected return is assumed, so the opportunity cost of waiting is disclosed, not computed.",
        "- Portfolio risks: equity drawdown; bond duration/interest-rate risk; gold price risk; USD/THB currency "
        "risk on every USD asset; concentration in US-listed funds; inflation erodes THB cash; holding cash "
        "carries opportunity cost; historical drawdowns can be exceeded.",
        "- Tax and jurisdiction (verify with a qualified adviser; no tax is calculated): US dividend withholding "
        "is 30% by default and may be 15% under the US-Thailand treaty with a valid W-8BEN; Thai rules on "
        "foreign income remitted from 2024 onward may apply; US estate tax may apply to US-situs assets above "
        "USD 60,000 for non-resident aliens (Form 706-NA); custody and broker-insolvency protection differ by "
        "platform and jurisdiction.",
        "",
        "Before any real decision: observe a current FX quote per platform with a comparable reference "
        "timestamp; confirm per-security and fractional eligibility in the account; resolve conflicting "
        "commission terms; confirm funding-route fees and eligibility. "
        "`REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.",
        "",
    ]
    return "\n".join(lines)


# Frozen synthetic acceptance scenario; every market value below is a HYPOTHETICAL_INPUT.
DEMO_AS_OF = date(2026, 10, 31)
DEMO_REFERENCE_THB_PER_USD = Decimal("35.00")
DEMO_PRICES_USD = {"BND": Decimal("72.00"), "VOO": Decimal("500.00")}
DEMO_WEIGHTS = {"BND": Decimal("0.4"), "VOO": Decimal("0.6")}
DEMO_QUOTE = UserFxQuote(
    broker_id="DIME",
    quote_observed_at="2026-10-31T10:00:00+07:00",
    quoted_thb_per_usd=Decimal("35.21"),
    source_amount=Decimal("3000.00"),
    target_amount=Decimal("85.20"),
    quote_valid_until="2026-10-31T10:01:30+07:00",
    reference_rate=Decimal("35.00"),
    reference_rate_timestamp="2026-10-31T10:02:00+07:00",
    reference_rate_source="SYNTHETIC_FIXTURE",
    reference_rate_kind="HYPOTHETICAL",
    quote_source_type="SYNTHETIC_FIXTURE",
    observational_status="SYNTHETIC",
)


def acceptance_demo() -> List[Tuple[str, ComparisonResult]]:
    from acash.research.d6.broker_profiles import load_candidate_profiles

    profiles = load_candidate_profiles()
    base = InvestmentPlan(
        monthly_savings_thb=Decimal("3000"),
        reference_thb_per_usd=DEMO_REFERENCE_THB_PER_USD,
        portfolio_weights=DEMO_WEIGHTS,
        order_sequence=("VOO", "BND"),
        ref_prices_usd=DEMO_PRICES_USD,
    )
    scenarios = [
        ("manual_1m", base),
        ("manual_3m", replace(base, batch_months=3)),
        ("dca_1m", replace(base, order_type="DCA")),
        ("manual_1m_dime_quote", replace(base, user_quotes={"DIME": DEMO_QUOTE}, evaluated_at="2026-10-31T10:01:00+07:00")),
    ]
    return [(label, compare_investment_plans(profiles, plan, DEMO_AS_OF)) for label, plan in scenarios]


def demo_outputs() -> Tuple[str, str]:
    results = acceptance_demo()
    payload = {label: comparison_to_dict(r) for label, r in results}
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    md_text = "\n".join(f"## Scenario `{label}`\n\n{format_markdown_report(r)}" for label, r in results)
    return json_text, md_text


def _parse_pairs(text: Optional[str]) -> Dict[str, Decimal]:
    pairs: Dict[str, Decimal] = {}
    for item in (text or "").split(","):
        if not item.strip():
            continue
        if ":" not in item:
            raise DataContractError(f"DECISION_BAD_PAIR: {item!r}. Expected TICKER:VALUE.")
        key, value = item.split(":", 1)
        pairs[key.strip().upper()] = Decimal(value.strip())
    return pairs


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Offline CLI. Writes files with LF endings; never contacts a provider."""
    from acash.research.d6.broker_profiles import load_candidate_profiles, load_security_eligibility

    parser = argparse.ArgumentParser(description="ACASH V38 Investor Decision Core (offline)")
    parser.add_argument("--acceptance-demo", action="store_true", help="Emit the frozen synthetic acceptance demo")
    parser.add_argument("--as-of", type=date.fromisoformat, help="Scenario date YYYY-MM-DD")
    parser.add_argument("--savings", type=Decimal, help="Monthly savings in THB")
    parser.add_argument("--reference-fx", type=Decimal, help="Reference THB per USD")
    parser.add_argument("--batch-months", type=int, default=1)
    parser.add_argument("--portfolio", default="VOO:0.6,BND:0.4")
    parser.add_argument("--order-sequence", default=None)
    parser.add_argument("--order-type", default="MANUAL", choices=list(ORDER_TYPES))
    parser.add_argument("--fx-spread", type=Decimal, default=None, help="Hypothetical spread; omitted means UNKNOWN")
    parser.add_argument("--prices", default=None, help="Hypothetical prices TICKER:USD,...; omitted means UNKNOWN")
    parser.add_argument("--quote-file", default=None, help="JSON list of UserFxQuote objects")
    parser.add_argument("--evaluated-at", default=None, help="ISO timestamp with zone for quote validity")
    parser.add_argument("--free-trades", type=int, default=1)
    parser.add_argument("--eligibility-file", default=None, help="Owner-maintained ETF eligibility CSV")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default=None, help="Output file (or prefix with --acceptance-demo)")
    args = parser.parse_args(argv)

    if args.acceptance_demo:
        json_text, md_text = demo_outputs()
        if args.output:
            for suffix, text in ((".json", json_text), (".md", md_text)):
                with open(args.output + suffix, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
        else:
            print(json_text if args.json else md_text)
        return

    if args.as_of is None or args.savings is None or args.reference_fx is None:
        raise DataContractError("DECISION_CLI_MISSING_INPUT: --as-of, --savings and --reference-fx are required.")
    quotes: Optional[Dict[str, UserFxQuote]] = None
    if args.quote_file:
        with open(args.quote_file, encoding="utf-8") as handle:
            raw = json.load(handle)
        decimal_fields = ("quoted_thb_per_usd", "reference_rate", "source_amount", "target_amount")
        quotes = {}
        for item in raw:
            fields: Dict[str, Any] = {k: (Decimal(v) if k in decimal_fields and v is not None else v) for k, v in item.items()}
            quote = UserFxQuote(**fields)
            quotes[quote.broker_id] = quote
    plan = InvestmentPlan(
        monthly_savings_thb=args.savings,
        reference_thb_per_usd=args.reference_fx,
        portfolio_weights=_parse_pairs(args.portfolio),
        batch_months=args.batch_months,
        order_sequence=tuple(s.strip().upper() for s in args.order_sequence.split(",")) if args.order_sequence else None,
        order_type=args.order_type,
        assumed_fx_spread=args.fx_spread,
        user_quotes=quotes,
        free_trades_available=args.free_trades,
        ref_prices_usd=_parse_pairs(args.prices) or None,
        evaluated_at=args.evaluated_at,
    )
    eligibility = load_security_eligibility(args.eligibility_file) if args.eligibility_file else ()
    result = compare_investment_plans(load_candidate_profiles(eligibility=eligibility), plan, args.as_of)
    text = json.dumps(comparison_to_dict(result), indent=2, sort_keys=True) + "\n" if args.json else format_markdown_report(result)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
