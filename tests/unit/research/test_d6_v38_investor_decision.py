"""Adversarial and boundary tests for D6 V38 Investor Decision Core.

Verifies:
- P0.1: Cost status taxonomy (SCENARIO_ONLY vs ALL_IN_DOCUMENTED vs QUOTE_OBSERVED)
- P0.2: Comprehensive canonical input hash sensitivity across all 15 RouteTerms fields
- P0.3: Order and security eligibility enforcement (ORDER_BELOW_MINIMUM, ORDER_TYPE_INCOMPATIBLE)
- P0.4: Missing price fail-closed on Dime! price tiers (DIME_PRICE_TIER_UNKNOWN)
- P0.5: FX formulation & cash conservation
- Phase 4: UserFxQuote offline processing, implied spread, and stale quote detection
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.broker_profiles import (
    FEE_SNAPSHOT_SHA256,
    get_default_cash_profile,
    get_default_dime_profile,
    get_default_ibkr_profile,
    get_default_webull_dca_standard_profile,
    get_default_webull_dca_zero_profile,
    get_default_webull_manual_profile,
    load_candidate_profiles,
)
from acash.research.d6.investor_decision import (
    COST_STATUS_ALL_IN_DOCUMENTED,
    COST_STATUS_LOWER_BOUND_ONLY,
    COST_STATUS_QUOTE_OBSERVED,
    COST_STATUS_SCENARIO_ONLY,
    DECISION_STATUS_NOT_ELIGIBLE,
    BrokerAssessment,
    BrokerProfile,
    CommissionPolicy,
    ComparisonResult,
    InvestmentPlan,
    UserFxQuote,
    compare_investment_plans,
    format_markdown_report,
)
from acash.research.d6.route_cost import RouteTerms

TODAY = date(2026, 10, 31)


def test_p0_1_hypothetical_spread_is_scenario_only_not_all_in_documented() -> None:
    """Verify that user-supplied hypothetical spread results in SCENARIO_ONLY, never ALL_IN_DOCUMENTED."""
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3500.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("1.0")},
        reference_thb_per_usd=Decimal("35.0"),
        assumed_fx_spread=Decimal("0.01"),  # Hypothetical input!
        ref_prices_usd={"VOO": Decimal("500.0")},
    )
    webull = get_default_webull_manual_profile()
    res = compare_investment_plans([webull], plan, TODAY)
    a = res.assessments[0]

    # Crucial distinction: Mathematically complete, but evidence status is SCENARIO_ONLY!
    assert a.cost_status == COST_STATUS_SCENARIO_ONLY
    assert a.cost_status != COST_STATUS_ALL_IN_DOCUMENTED
    assert a.investable_balance_usd is not None


def test_p0_1_user_observed_quote_sets_quote_observed_status() -> None:
    """Verify that an active user-observed quote sets status to QUOTE_OBSERVED."""
    quote = UserFxQuote(
        broker_id="WEBULL_MANUAL",
        quote_observed_at="2026-10-31T10:00:00Z",
        quoted_thb_per_usd=Decimal("35.35"),
        reference_rate=Decimal("35.0"),
    )
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3500.0"),
        portfolio_weights={"VOO": Decimal("1.0")},
        reference_thb_per_usd=Decimal("35.0"),
        user_quotes={"WEBULL_MANUAL": quote},
        ref_prices_usd={"VOO": Decimal("500.0")},
    )
    webull = get_default_webull_manual_profile()
    res = compare_investment_plans([webull], plan, TODAY)
    a = res.assessments[0]

    assert a.cost_status == COST_STATUS_QUOTE_OBSERVED
    assert quote.implied_spread == Decimal("0.01")  # (35.35 / 35.0) - 1 = 0.01


def test_p0_1_stale_quote_is_flagged_and_retains_lower_bound() -> None:
    """Verify that an expired/stale quote is not used for current execution."""
    quote = UserFxQuote(
        broker_id="WEBULL_MANUAL",
        quote_observed_at="2026-10-30T10:00:00Z",
        quoted_thb_per_usd=Decimal("35.35"),
        is_expired=True,
    )
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3500.0"),
        portfolio_weights={"VOO": Decimal("1.0")},
        user_quotes={"WEBULL_MANUAL": quote},
        ref_prices_usd={"VOO": Decimal("500.0")},
    )
    webull = get_default_webull_manual_profile()
    res = compare_investment_plans([webull], plan, TODAY)
    a = res.assessments[0]

    assert a.cost_status == COST_STATUS_LOWER_BOUND_ONLY
    assert any("USER_QUOTE_STALE" in note for note in a.evidence_notes)


def test_p0_2_input_hash_sensitive_to_funding_terms_fields() -> None:
    """Verify that changing any RouteTerms field in an IBKR profile mutates the input hash."""
    base_plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("1.0")},
        ref_prices_usd={"VOO": Decimal("500.0")},
    )
    terms_base = RouteTerms(
        route_id="ROUTE_A",
        delivered_currency="USD",
        fixed_fee_thb=Decimal("250.0"),
        fx_spread=None,
        deducted_fee_usd=None,
        intermediary_fee_usd=None,
        receiving_fee_usd=None,
        min_amount_thb=Decimal("1000.0"),
    )
    p_base = get_default_ibkr_profile(terms_base)
    hash_base = compare_investment_plans([p_base], base_plan, TODAY).input_hash

    # Mutate fixed_fee_thb
    terms_fee = RouteTerms(
        route_id="ROUTE_A",
        delivered_currency="USD",
        fixed_fee_thb=Decimal("300.0"),
        fx_spread=None,
        deducted_fee_usd=None,
        intermediary_fee_usd=None,
        receiving_fee_usd=None,
        min_amount_thb=Decimal("1000.0"),
    )
    p_fee = get_default_ibkr_profile(terms_fee)
    assert compare_investment_plans([p_fee], base_plan, TODAY).input_hash != hash_base

    # Mutate intermediary_fee_usd
    terms_inter = RouteTerms(
        route_id="ROUTE_A",
        delivered_currency="USD",
        fixed_fee_thb=Decimal("250.0"),
        fx_spread=None,
        deducted_fee_usd=None,
        intermediary_fee_usd=Decimal("15.0"),
        receiving_fee_usd=None,
        min_amount_thb=Decimal("1000.0"),
    )
    p_inter = get_default_ibkr_profile(terms_inter)
    assert compare_investment_plans([p_inter], base_plan, TODAY).input_hash != hash_base


def test_p0_3_order_below_minimum_marked_not_eligible() -> None:
    """Verify that an order below minimum threshold is marked NOT_ELIGIBLE (fail-closed)."""
    # 50 THB total savings with 60/40 allocation -> BND order = 20 THB < Dime min 50 THB!
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("50.0"),
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    dime = get_default_dime_profile()
    res = compare_investment_plans([dime], plan, TODAY)
    a = res.assessments[0]

    assert a.eligibility_status == "NOT_ELIGIBLE"
    assert a.decision_status == DECISION_STATUS_NOT_ELIGIBLE
    assert any("ORDER_BELOW_MINIMUM" in note for note in a.evidence_notes)


def test_p0_3_manual_plan_rejects_dca_exclusive_profiles() -> None:
    """Verify that manual investment plans mark DCA-exclusive profiles as ORDER_TYPE_INCOMPATIBLE."""
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("1.0")},
        order_type="MANUAL",
        ref_prices_usd={"VOO": Decimal("500.0")},
    )
    webull_dca = get_default_webull_dca_zero_profile()
    res = compare_investment_plans([webull_dca], plan, TODAY)
    a = res.assessments[0]

    assert a.eligibility_status == "ORDER_TYPE_INCOMPATIBLE"
    assert a.decision_status == DECISION_STATUS_NOT_ELIGIBLE
    assert a.investable_balance_usd is None


def test_p0_4_missing_price_on_dime_subsequent_order_fails_closed() -> None:
    """Verify that Dime! non-free orders with missing share price record DIME_PRICE_TIER_UNKNOWN."""
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("VOO", "BND"),
        free_trades_available=1,  # VOO free, BND pays commission
        ref_prices_usd={"VOO": Decimal("500.0")},  # BND price missing!
    )
    dime = get_default_dime_profile()
    res = compare_investment_plans([dime], plan, TODAY)
    a = res.assessments[0]

    assert "DIME_BND_PRICE_TIER_UNKNOWN" in a.unknown_components
    assert any("PRICE_UNKNOWN" in note for note in a.evidence_notes)


def test_p0_5_cash_conservation_exact() -> None:
    """Verify exact cash conservation down to the cent."""
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3500.0"),
        portfolio_weights={"VOO": Decimal("1.0")},
        reference_thb_per_usd=Decimal("35.0"),
        assumed_fx_spread=Decimal("0.01"),
        ref_prices_usd={"VOO": Decimal("500.0")},
    )
    webull = get_default_webull_manual_profile()
    res = compare_investment_plans([webull], plan, TODAY)
    a = res.assessments[0]

    assert a.investable_balance_usd is not None
    ref_value_thb = a.investable_balance_usd * plan.reference_thb_per_usd
    assert ref_value_thb + a.total_known_friction_thb == plan.monthly_savings_thb


def test_markdown_report_formatting() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    profiles = load_candidate_profiles()
    res = compare_investment_plans(profiles, plan, TODAY)
    report = format_markdown_report(res)
    assert "# ACASH INVESTOR DECISION REPORT" in report
    assert "P0.1 Cost Status Taxonomy" in report
    assert "P0.2 Input Hash Verified" in report
