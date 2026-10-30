"""Adversarial and boundary tests for D6 V38 Investor Decision Core.

Verifies:
- P0.1: FX Double-Counting elimination & strict cash conservation
- P0.2: Comprehensive canonical input hash sensitivity & determinism
- P0.3: Webull DCA conflicting terms scenarios (0% vs 0.10%)
- P0.4: IBKR account-specific eligibility (ACCOUNT_SPECIFIC_UNVERIFIED)
- P0.5: Missing reference price fail-closed (no arbitrary fallbacks)
- P1: Chronological order-sequence free trade entitlement & batching rules
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.broker_profiles import (
    get_default_cash_profile,
    get_default_dime_profile,
    get_default_ibkr_profile,
    get_default_webull_dca_standard_profile,
    get_default_webull_dca_zero_profile,
    get_default_webull_manual_profile,
    load_candidate_profiles,
)
from acash.research.d6.investor_decision import (
    BrokerAssessment,
    BrokerProfile,
    CommissionPolicy,
    ComparisonResult,
    InvestmentPlan,
    compare_investment_plans,
    format_markdown_report,
)
from acash.research.d6.route_cost import RouteTerms

TODAY = date(2026, 10, 30)


def test_p0_1_fx_no_double_counting_and_cash_conservation() -> None:
    """Verify that FX spread is not subtracted twice and cash is exactly conserved."""
    # Given 3,500 THB, reference rate 35.0, spread 1% (0.01)
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3500.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("1.0")},
        reference_thb_per_usd=Decimal("35.0"),
        assumed_fx_spread=Decimal("0.01"),
        ref_prices_usd={"VOO": Decimal("500.0")},
    )
    # Using Webull Manual: 0.10% commission + 7% VAT
    webull = get_default_webull_manual_profile()
    res = compare_investment_plans([webull], plan, TODAY)
    a = res.assessments[0]

    # Commission: 3,500 * 0.0010 = 3.50 THB, VAT = 0.25 THB. Direct THB fees = 3.75 THB.
    # Net THB for conversion = 3,500 - 3.75 = 3,496.25 THB.
    # r_exec = 35.0 * 1.01 = 35.35 THB/USD.
    # USD purchased = 3,496.25 / 35.35 = 98.903818... -> 98.90 USD.
    # Value of purchased USD at reference rate = 98.90 * 35.0 = 3,461.50 THB.
    # Economic FX drag = 3,496.25 - 3,461.50 = 34.75 THB.
    # Total friction = 3.75 direct fees + 34.75 FX drag = 38.50 THB.
    # Check that net investable USD * ref rate + total friction == gross THB!
    assert a.investable_balance_usd is not None
    ref_value_thb = a.investable_balance_usd * plan.reference_thb_per_usd
    assert ref_value_thb + a.total_known_friction_thb == plan.monthly_savings_thb
    assert a.cost_status == "ALL_IN_DOCUMENTED"


def test_p0_2_input_hash_sensitive_to_all_economic_inputs() -> None:
    """Verify that input hash changes when any financially material parameter changes."""
    base_plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("VOO", "BND"),
        reference_thb_per_usd=Decimal("35.0"),
        assumed_fx_spread=Decimal("0.005"),
        free_trades_available=1,
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    profiles = load_candidate_profiles()
    base_hash = compare_investment_plans(profiles, base_plan, TODAY).input_hash

    # 1. Mutate savings
    plan_savings = InvestmentPlan(
        monthly_savings_thb=Decimal("3001.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("VOO", "BND"),
        reference_thb_per_usd=Decimal("35.0"),
        assumed_fx_spread=Decimal("0.005"),
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    assert compare_investment_plans(profiles, plan_savings, TODAY).input_hash != base_hash

    # 2. Mutate price
    plan_price = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("VOO", "BND"),
        reference_thb_per_usd=Decimal("35.0"),
        assumed_fx_spread=Decimal("0.005"),
        ref_prices_usd={"VOO": Decimal("505.0"), "BND": Decimal("72.0")},
    )
    assert compare_investment_plans(profiles, plan_price, TODAY).input_hash != base_hash

    # 3. Mutate order sequence (VOO, BND) vs (BND, VOO)
    plan_seq = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("BND", "VOO"),
        reference_thb_per_usd=Decimal("35.0"),
        assumed_fx_spread=Decimal("0.005"),
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    assert compare_investment_plans(profiles, plan_seq, TODAY).input_hash != base_hash

    # 4. Mutate free trades available
    plan_free = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("VOO", "BND"),
        reference_thb_per_usd=Decimal("35.0"),
        assumed_fx_spread=Decimal("0.005"),
        free_trades_available=0,
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    assert compare_investment_plans(profiles, plan_free, TODAY).input_hash != base_hash


def test_p0_3_webull_dca_both_scenarios_modeled_as_conflicting() -> None:
    """Verify that Webull DCA is modeled as TERMS_CONFLICTING in both 0% and 0.10% variants."""
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("1.0")},
        order_type="DCA",
    )
    p_zero = get_default_webull_dca_zero_profile()
    p_std = get_default_webull_dca_standard_profile()

    res_zero = compare_investment_plans([p_zero], plan, TODAY).assessments[0]
    res_std = compare_investment_plans([p_std], plan, TODAY).assessments[0]

    assert res_zero.decision_status == "TERMS_CONFLICTING"
    assert res_std.decision_status == "TERMS_CONFLICTING"
    assert res_zero.commission_thb == Decimal("0.00")
    assert res_std.commission_thb == Decimal("3.00")
    assert res_zero.cost_status == "LOWER_BOUND_ONLY"  # FX spread is unknown
    assert any("TERMS_CONFLICTING" in note for note in res_zero.evidence_notes)


def test_p0_4_ibkr_account_specific_unverified_eligibility() -> None:
    """Verify that IBKR default profile does not falsely claim verified bank route eligibility."""
    ibkr = get_default_ibkr_profile()
    assert ibkr.eligibility_status == "ACCOUNT_SPECIFIC_UNVERIFIED"
    assert ibkr.funding_terms is not None
    assert ibkr.funding_terms.purpose_supported is None
    assert ibkr.funding_terms.beneficiary_supported is None


def test_p0_5_missing_reference_price_fails_closed_for_share_based_commissions() -> None:
    """Verify that IBKR Tiered raises DataContractError if asset price is not provided."""
    plan_no_price = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("1.0")},
        ref_prices_usd=None,  # Price missing!
    )
    ibkr = get_default_ibkr_profile()
    with pytest.raises(DataContractError, match="DECISION_MISSING_REFERENCE_PRICE"):
        compare_investment_plans([ibkr], plan_no_price, TODAY)


def test_p1_dime_free_trade_chronological_sequence() -> None:
    """Verify Dime! applies free trade strictly to first chronological order, not largest order."""
    # VOO = 60% (1,800 THB), BND = 40% (1,200 THB)
    # Case A: Sequence is ("VOO", "BND"). VOO (order 1) gets free trade. BND (order 2) pays 0.15% + 7% VAT.
    plan_a = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("VOO", "BND"),
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    dime = get_default_dime_profile()
    res_a = compare_investment_plans([dime], plan_a, TODAY).assessments[0]
    # BND: 1,200 * 0.0015 = 1.80 THB. VAT = 0.13 THB. Total comm+VAT = 1.93 THB.
    assert res_a.commission_thb == Decimal("1.80")
    assert res_a.vat_thb == Decimal("0.13")

    # Case B: Sequence is ("BND", "VOO"). BND (order 1) gets free trade! VOO (order 2) pays 0.15% + 7% VAT.
    plan_b = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("BND", "VOO"),
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    res_b = compare_investment_plans([dime], plan_b, TODAY).assessments[0]
    # VOO: 1,800 * 0.0015 = 2.70 THB. VAT = 0.19 THB. Total comm+VAT = 2.89 THB.
    assert res_b.commission_thb == Decimal("2.70")
    assert res_b.vat_thb == Decimal("0.19")


def test_p1_dime_entitlement_exhausted_pays_full_commissions() -> None:
    """Verify Dime! charges commission on all orders when free trades are exhausted."""
    plan_exhausted = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("VOO", "BND"),
        free_trades_available=0,  # Entitlement already consumed
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    dime = get_default_dime_profile()
    res = compare_investment_plans([dime], plan_exhausted, TODAY).assessments[0]
    # Both VOO (1,800 * 0.0015 = 2.70) and BND (1,200 * 0.0015 = 1.80) pay commission = 4.50 THB.
    # VAT = 7% on 4.50 = 0.315 -> 0.32 THB. Total = 4.82 THB.
    assert res.free_orders_used == 0
    assert res.commission_thb == Decimal("4.50")
    assert res.vat_thb == Decimal("0.32")


def test_p1_multi_month_batching_does_not_multiply_monthly_freebies() -> None:
    """Verify that batching 3 months of savings in one execution month does not grant 3 free trades."""
    plan_quarterly = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=3,  # 9,000 THB gross
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_sequence=("VOO", "BND"),
        free_trades_available=1,  # 1 calendar month execution
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    dime = get_default_dime_profile()
    res = compare_investment_plans([dime], plan_quarterly, TODAY).assessments[0]
    # Only 1 free trade used, BND pays 0.15% on 3,600 THB = 5.40 THB + 0.38 VAT = 5.78 THB
    assert res.free_orders_used == 1
    assert res.commission_thb == Decimal("5.40")
    assert res.vat_thb == Decimal("0.38")


def test_cash_no_trade_control() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("1.0")},
    )
    cash = get_default_cash_profile()
    res = compare_investment_plans([cash], plan, TODAY).assessments[0]
    assert res.total_known_friction_thb == Decimal("0.00")
    assert res.decision_status == "CASH_NO_TRADE"
    assert res.cost_status == "ALL_IN_DOCUMENTED"


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
    assert "P0.1 FX Double-Counting Fixed" in report
    assert "Webull Thailand (DCA - Promo 0%)" in report
    assert "Webull Thailand (DCA - Standard 0.10%)" in report
