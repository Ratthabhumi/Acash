"""Adversarial and boundary tests for D6 V38 Investor Decision Core."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.broker_profiles import (
    get_default_cash_profile,
    get_default_dime_profile,
    get_default_ibkr_profile,
    get_default_webull_dca_profile,
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


def test_standard_plan_comparison_reproducibility() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_type="MANUAL",
        reference_thb_per_usd=Decimal("35.0"),
    )
    profiles = load_candidate_profiles()
    res1 = compare_investment_plans(profiles, plan, TODAY)
    res2 = compare_investment_plans(profiles, plan, TODAY)
    assert res1.input_hash == res2.input_hash
    assert len(res1.assessments) == 5
    assert res1.overall_status == "COST_EVIDENCE_INCOMPLETE"


def test_dime_free_order_entitlement_applied_to_largest_order() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
    )
    dime = get_default_dime_profile()
    res = compare_investment_plans([dime], plan, TODAY)
    a = res.assessments[0]
    # 3,000 THB total. VOO = 1,800 THB (free order 1), BND = 1,200 THB (0.15% = 1.80 THB)
    assert a.free_orders_used == 1
    assert a.total_orders_count == 2
    assert a.commission_thb == Decimal("1.80")
    # 7% VAT on 1.80 = 0.126 -> 0.13 THB
    assert a.vat_thb == Decimal("0.13")
    assert a.total_known_friction_thb == Decimal("1.93")


def test_webull_manual_charges_commission_on_all_orders_with_vat() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
    )
    webull = get_default_webull_manual_profile()
    res = compare_investment_plans([webull], plan, TODAY)
    a = res.assessments[0]
    # 3,000 * 0.10% = 3.00 THB commission
    assert a.commission_thb == Decimal("3.00")
    # 7% VAT on 3.00 = 0.21 THB
    assert a.vat_thb == Decimal("0.21")
    assert a.total_known_friction_thb == Decimal("3.21")


def test_webull_dca_conflicting_terms_flagged() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        order_type="DCA",
    )
    webull_dca = get_default_webull_dca_profile()
    res = compare_investment_plans([webull_dca], plan, TODAY)
    a = res.assessments[0]
    assert a.commission_thb == Decimal("0.00")
    assert a.vat_thb == Decimal("0.00")
    assert any("TERMS_CONFLICTING" in note for note in a.evidence_notes)


def test_ibkr_tiered_commission_and_swift_friction() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
        ref_prices_usd={"VOO": Decimal("500.0"), "BND": Decimal("72.0")},
    )
    ibkr = get_default_ibkr_profile()
    res = compare_investment_plans([ibkr], plan, TODAY)
    a = res.assessments[0]
    # Funding fee is 250 THB
    assert a.funding_friction_thb == Decimal("250.00")
    # Commission for 2 orders with min $0.35 each = $0.70 = 24.50 THB
    assert a.commission_usd == Decimal("0.70")
    assert a.commission_thb == Decimal("24.50")
    assert a.vat_thb == Decimal("0.00")
    assert a.total_known_friction_thb == Decimal("274.50")
    assert a.cost_status == "LOWER_BOUND_ONLY"
    assert "FX_SPREAD" in a.unknown_components or "IBKR_FX_SPREAD" in a.unknown_components


def test_cash_no_trade_baseline() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("1.0")},
    )
    cash = get_default_cash_profile()
    res = compare_investment_plans([cash], plan, TODAY)
    a = res.assessments[0]
    assert a.total_known_friction_thb == Decimal("0.00")
    assert a.decision_status == "CASH_NO_TRADE"
    assert a.cost_status == "ALL_IN_DOCUMENTED"


def test_quarterly_batching_reduces_relative_swift_drag() -> None:
    plan_monthly = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("1.0")},
    )
    plan_quarterly = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=3,
        portfolio_weights={"VOO": Decimal("1.0")},
    )
    ibkr = get_default_ibkr_profile()
    res_m = compare_investment_plans([ibkr], plan_monthly, TODAY)
    res_q = compare_investment_plans([ibkr], plan_quarterly, TODAY)
    
    drag_m = res_m.assessments[0].friction_share_lower_bound
    drag_q = res_q.assessments[0].friction_share_lower_bound
    assert drag_q < drag_m  # Quarterly batching amortizes the 250 THB fixed fee over 9,000 THB instead of 3,000 THB


def test_portfolio_weights_must_sum_to_one() -> None:
    with pytest.raises(DataContractError, match="DECISION_WEIGHTS_NOT_ONE"):
        InvestmentPlan(
            monthly_savings_thb=Decimal("3000.0"),
            portfolio_weights={"VOO": Decimal("0.5"), "BND": Decimal("0.4")},  # sum = 0.9
        )


def test_invalid_negative_or_zero_savings_raises() -> None:
    with pytest.raises(DataContractError, match="DECISION_INVALID_MONEY"):
        InvestmentPlan(
            monthly_savings_thb=Decimal("-1000.0"),
            portfolio_weights={"VOO": Decimal("1.0")},
        )
    with pytest.raises(DataContractError, match="DECISION_INVALID_MONEY"):
        InvestmentPlan(
            monthly_savings_thb=Decimal("0.0"),
            portfolio_weights={"VOO": Decimal("1.0")},
        )


def test_invalid_batch_months_raises() -> None:
    with pytest.raises(DataContractError, match="DECISION_INVALID_BATCH_MONTHS"):
        InvestmentPlan(
            monthly_savings_thb=Decimal("1000.0"),
            batch_months=0,
            portfolio_weights={"VOO": Decimal("1.0")},
        )


def test_unsupported_symbol_marks_eligibility() -> None:
    restricted_profile = BrokerProfile(
        broker_id="CUSTOM_BROKER",
        display_name="Custom Broker",
        funding_channel="LOCAL_THB_QR_ATS",
        commission_policy=CommissionPolicy(policy_type="PERCENTAGE", rate=Decimal("0.001")),
        fractional_supported=True,
        supported_symbols=("VOO",),  # BND not supported
    )
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
    )
    res = compare_investment_plans([restricted_profile], plan, TODAY)
    a = res.assessments[0]
    assert a.eligibility_status == "NOT_ELIGIBLE"
    assert any("SYMBOL_NOT_SUPPORTED: BND" in note for note in a.evidence_notes)


def test_markdown_report_formatting() -> None:
    plan = InvestmentPlan(
        monthly_savings_thb=Decimal("3000.0"),
        batch_months=1,
        portfolio_weights={"VOO": Decimal("0.6"), "BND": Decimal("0.4")},
    )
    profiles = load_candidate_profiles()
    res = compare_investment_plans(profiles, plan, TODAY)
    report = format_markdown_report(res)
    assert "# ACASH INVESTOR DECISION REPORT" in report
    assert "Interactive Brokers (IBKR Pro)" in report
    assert "Dime! Thailand (KKP)" in report
    assert "Webull Thailand (Manual)" in report
    assert "Webull Thailand (Fixed DCA)" in report
    assert "CASH / NO TRADE" in report
