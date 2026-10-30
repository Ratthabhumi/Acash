"""Default broker profiles for ACASH V38 Investor Decision Core.

Maintains canonical definitions and evidence links for candidate platforms:
- Interactive Brokers LLC (IBKR Pro Tiered)
- Dime! Thailand (KKP Securities)
- Webull Securities (Thailand) - Manual
- Webull Securities (Thailand) - Fixed DCA (Promotional Zero)
- Webull Securities (Thailand) - Fixed DCA (Standard 0.10%)
- CASH / NO_TRADE
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from acash.research.d6.investor_decision import (
    BrokerProfile,
    CommissionPolicy,
)
from acash.research.d6.route_cost import RouteTerms

ZERO = Decimal("0")
FEE_SNAPSHOT_SHA256 = "3121459a2fcbf10cf9c840b7caa61d4bb2e4fd428262bea134d07de6b1ffd8b5"


def get_default_ibkr_profile(route_terms: RouteTerms | None = None) -> BrokerProfile:
    """IBKR Pro Tiered profile funded via SWIFT outward remittance.

    Strict fail-closed: purpose_supported and beneficiary_supported are None
    (ACCOUNT_SPECIFIC_UNVERIFIED) unless specific account records verify them.
    """
    terms = route_terms
    if terms is None:
        terms = RouteTerms(
            route_id="KBANK_SWIFT_OUTWARD",
            delivered_currency="USD",
            fixed_fee_thb=Decimal("250.0"),
            fx_spread=None,  # UNKNOWN
            deducted_fee_usd=None,
            intermediary_fee_usd=None,
            receiving_fee_usd=None,
            min_amount_thb=Decimal("1000.0"),
            purpose_supported=None,      # ACCOUNT_SPECIFIC_UNVERIFIED
            beneficiary_supported=None,  # ACCOUNT_SPECIFIC_UNVERIFIED
        )
    return BrokerProfile(
        broker_id="IBKR",
        display_name="Interactive Brokers (IBKR Pro)",
        funding_channel="SWIFT_CROSS_BORDER",
        commission_policy=CommissionPolicy(
            policy_type="FIXED_PER_SHARE",
            per_share_usd=Decimal("0.0035"),
            min_commission_usd=Decimal("0.35"),
            vat_applicable=False,
            evidence_status="VERIFIED_DOCUMENTED",
        ),
        fractional_supported=True,
        min_order_thb=Decimal("35.0"),  # ~$1 minimum
        funding_terms=terms,
        eligibility_status="ACCOUNT_SPECIFIC_UNVERIFIED",
        evidence_notes=(
            "US broker pricing: Tiered $0.0035/sh min $0.35; third-party deposits prohibited; bank route eligibility is unverified per account.",
        ),
    )


def get_default_dime_profile() -> BrokerProfile:
    """Dime! Thailand (KKP) profile."""
    return BrokerProfile(
        broker_id="DIME",
        display_name="Dime! Thailand (KKP)",
        funding_channel="LOCAL_THB_QR_ATS",
        commission_policy=CommissionPolicy(
            policy_type="FREE_MONTHLY_TIERED",
            rate=Decimal("0.0015"),  # 0.15% on subsequent orders
            free_orders_count=1,     # 1 free trade per calendar month for first qualifying trade
            vat_applicable=True,     # 7% Thai VAT on paid commission
            evidence_status="VERIFIED_DOCUMENTED",
        ),
        fractional_supported=True,
        min_order_thb=Decimal("50.0"),  # 50 THB minimum
        funding_terms=None,
        eligibility_status="CONDITIONALLY_ELIGIBLE",
        evidence_notes=(
            "Thai licensed broker: 1 free trade/month for first chronological qualifying trade; subsequent 0.15% + 7% VAT; CAT fee $0.000046/sh.",
        ),
    )


def get_default_webull_manual_profile() -> BrokerProfile:
    """Webull Thailand Manual Order profile."""
    return BrokerProfile(
        broker_id="WEBULL_MANUAL",
        display_name="Webull Thailand (Manual)",
        funding_channel="LOCAL_THB_QR_ATS",
        commission_policy=CommissionPolicy(
            policy_type="PERCENTAGE",
            rate=Decimal("0.0010"),  # 0.10% commission
            vat_applicable=True,     # 7% Thai VAT on commission
            evidence_status="VERIFIED_DOCUMENTED",
        ),
        fractional_supported=True,
        min_order_thb=Decimal("40.0"),  # ~$1 / 40 THB
        funding_terms=None,
        eligibility_status="CONDITIONALLY_ELIGIBLE",
        evidence_notes=(
            "Thai licensed broker: 0.10% commission + 7% VAT; no commission minimum; local THB deposit via QR/ATS.",
        ),
    )


def get_default_webull_dca_zero_profile() -> BrokerProfile:
    """Webull Thailand Recurring DCA (Promotional Zero Commission Scenario)."""
    return BrokerProfile(
        broker_id="WEBULL_DCA_ZERO",
        display_name="Webull Thailand (DCA - Promo 0%)",
        funding_channel="LOCAL_THB_QR_ATS",
        commission_policy=CommissionPolicy(
            policy_type="ZERO_PROMOTIONAL",
            rate=Decimal("0.0"),
            vat_applicable=False,
            evidence_status="TERMS_CONFLICTING",
        ),
        fractional_supported=True,
        min_order_thb=Decimal("40.0"),  # 40 THB minimum for fixed DCA
        funding_terms=None,
        eligibility_status="CONDITIONALLY_ELIGIBLE",
        evidence_notes=(
            "SCENARIO_ONLY: DCA promotional marketing advertises 0% commission; conflicts with Recurring Investment Guide 0.10%. Unverified.",
        ),
    )


def get_default_webull_dca_standard_profile() -> BrokerProfile:
    """Webull Thailand Recurring DCA (Standard 0.10% Scenario)."""
    return BrokerProfile(
        broker_id="WEBULL_DCA_STANDARD",
        display_name="Webull Thailand (DCA - Standard 0.10%)",
        funding_channel="LOCAL_THB_QR_ATS",
        commission_policy=CommissionPolicy(
            policy_type="PERCENTAGE",
            rate=Decimal("0.0010"),
            vat_applicable=True,
            evidence_status="TERMS_CONFLICTING",
        ),
        fractional_supported=True,
        min_order_thb=Decimal("40.0"),
        funding_terms=None,
        eligibility_status="CONDITIONALLY_ELIGIBLE",
        evidence_notes=(
            "SCENARIO_ONLY: Standard 0.10% rate from Webull Recurring Investment Guide (June 15, 2026) applied to DCA.",
        ),
    )


def get_default_cash_profile() -> BrokerProfile:
    """CASH / NO_TRADE baseline profile."""
    return BrokerProfile(
        broker_id="CASH",
        display_name="CASH / NO TRADE",
        funding_channel="NONE",
        commission_policy=CommissionPolicy(
            policy_type="NONE",
            rate=Decimal("0.0"),
            vat_applicable=False,
            evidence_status="VERIFIED_DOCUMENTED",
        ),
        fractional_supported=False,
        min_order_thb=Decimal("0.0"),
        funding_terms=None,
        eligibility_status="DOCUMENTED",
        evidence_notes=(
            "Baseline control: 100% held in domestic cash; zero transfer friction, zero market volatility.",
        ),
    )


def load_candidate_profiles(
    route_terms: RouteTerms | None = None,
    include_both_webull_dca_scenarios: bool = True,
) -> Tuple[BrokerProfile, ...]:
    """Return all standard candidate profiles with explicit evidence-aware variants."""
    profiles = [
        get_default_ibkr_profile(route_terms),
        get_default_dime_profile(),
        get_default_webull_manual_profile(),
        get_default_webull_dca_zero_profile(),
    ]
    if include_both_webull_dca_scenarios:
        profiles.append(get_default_webull_dca_standard_profile())
    profiles.append(get_default_cash_profile())
    return tuple(profiles)
