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

import csv
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Optional, Sequence, Tuple

from acash.research.d6.investor_decision import (
    FEE_SNAPSHOT_SHA256 as FEE_SNAPSHOT_SHA256,
    BrokerProfile,
    CommissionPolicy,
    SecurityEligibility,
)
from acash.core.domain.exceptions import DataContractError
from acash.research.d6.route_cost import RouteTerms

ZERO = Decimal("0")
DIME_CAT_FEE_PER_SHARE_USD = Decimal("0.000046")
WEBULL_CAT_FEE_PER_SHARE_USD = Decimal("0.000024")


KBANK_KPLUS_SWIFT_SOURCE = (
    "https://www.kasikornbank.com/en/international-business/global-money-transfer/pages/international-transferviakplus.aspx"
)
KBANK_SWIFT_CHARGE_BEARERS = ("SHAR", "DEBT", "CRED")


def kbank_kplus_swift_terms(charge_bearer: str = "SHAR") -> RouteTerms:
    """K PLUS Global Outward SWIFT terms for USD, published promotion 2026-01-01..2026-12-31.

    SHAR: THB 250; DEBT: THB 950 (subject to conditions); CRED: USD 12 deducted from the amount.
    Foreign-bank charges may still apply, so intermediary and receiving fees stay UNKNOWN; the
    post-promotion fee is UNKNOWN. K BIZ terms are a separate channel and are not modeled here.
    Beneficiary/purpose eligibility for an IBKR deposit is not inferred from the generic tariff.
    """
    if charge_bearer not in KBANK_SWIFT_CHARGE_BEARERS:
        raise DataContractError(f"KBANK_UNKNOWN_CHARGE_BEARER: {charge_bearer}.")
    fixed = {"SHAR": Decimal("250"), "DEBT": Decimal("950"), "CRED": ZERO}[charge_bearer]
    return RouteTerms(
        route_id=f"KBANK_KPLUS_SWIFT_{charge_bearer}",
        delivered_currency="USD",
        fixed_fee_thb=fixed,
        fx_spread=None,
        deducted_fee_usd=Decimal("12") if charge_bearer == "CRED" else ZERO,
        intermediary_fee_usd=None,
        receiving_fee_usd=None,
        min_amount_thb=ZERO,
        promotion_start=date(2026, 1, 1),
        promotion_end=date(2026, 12, 31),
        standard_fee_thb=None,
        purpose_supported=None,
        beneficiary_supported=None,
        evidence_status="OFFICIAL_PROVIDER_TARIFF",
    )


def get_default_ibkr_profile(route_terms: RouteTerms | None = None) -> BrokerProfile:
    """IBKR Pro Tiered profile funded via K PLUS SWIFT (SHAR) unless other terms are supplied.

    Strict fail-closed: purpose_supported and beneficiary_supported are None
    (ACCOUNT_SPECIFIC_UNVERIFIED) unless specific account records verify them.
    """
    terms = route_terms if route_terms is not None else kbank_kplus_swift_terms("SHAR")
    return BrokerProfile(
        broker_id="IBKR",
        display_name="Interactive Brokers (IBKR Pro)",
        funding_channel="SWIFT_CROSS_BORDER",
        commission_policy=CommissionPolicy(
            policy_type="FIXED_PER_SHARE",
            per_share_usd=Decimal("0.0035"),
            min_commission_usd=Decimal("0.35"),
            vat_applicable=False,
            applicable_order_type="ALL",
            evidence_status="OFFICIAL_PROVIDER_TARIFF",
            pass_through_fees_known=False,
            fractional_rate=Decimal("0.01"),       # Footnote 11: max(1% of fractional value, USD 0.01)
            fractional_min_usd=Decimal("0.01"),
        ),
        fractional_supported=True,
        min_order_thb=ZERO,
        funding_terms=terms,
        eligibility_status="ACCOUNT_SPECIFIC_UNVERIFIED",
        evidence_notes=(
            "IBKR Pro Tiered base USD 0.0035/sh, min USD 0.35; exchange, clearing and regulatory pass-through UNKNOWN; pure fractional trades use Footnote 11 max(1% of value, USD 0.01); mixed whole/fractional split UNKNOWN; minimum order not modeled; third-party deposits prohibited.",
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
            applicable_order_type="ALL",
            evidence_status="OFFICIAL_PROVIDER_TARIFF",
            cat_fee_per_share_usd=DIME_CAT_FEE_PER_SHARE_USD,
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
            applicable_order_type="MANUAL",
            evidence_status="OFFICIAL_PROVIDER_TARIFF",
            cat_fee_per_share_usd=WEBULL_CAT_FEE_PER_SHARE_USD,
        ),
        fractional_supported=True,
        min_order_usd=Decimal("1"),
        platform_id="WEBULL",
        eligibility_status="CONDITIONALLY_ELIGIBLE",
        evidence_notes=(
            "Thai licensed broker: 0.10% commission + 7% VAT; CAT fee $0.000024/sh; no commission minimum; local THB deposit via QR/ATS.",
        ),
    )


def get_default_webull_dca_zero_profile() -> BrokerProfile:
    """Webull Thailand Recurring DCA (Promotional Zero Commission Scenario)."""
    return BrokerProfile(
        broker_id="WEBULL_DCA_ZERO",
        display_name="Webull Thailand (DCA - currently advertised 0%)",
        funding_channel="LOCAL_THB_QR_ATS",
        commission_policy=CommissionPolicy(
            policy_type="ZERO_PROMOTIONAL",
            rate=Decimal("0.0"),
            vat_applicable=False,
            applicable_order_type="DCA",
            evidence_status="OFFICIAL_SOURCE_CONFLICT",
            cat_fee_per_share_usd=WEBULL_CAT_FEE_PER_SHARE_USD,
        ),
        fractional_supported=True,
        min_order_usd=Decimal("1"),
        platform_id="WEBULL",
        eligibility_status="CONDITIONALLY_ELIGIBLE",
        evidence_notes=(
            "CURRENTLY_ADVERTISED_0_PERCENT: official DCA page advertises zero commission for eligible US stocks/ETFs (min USD 1); owner app showed the same claim on 2026-11-01. Conflict with the 2026-06-15 guide (0.10%) is unresolved; duration not established; zero commission is not zero regulatory, FX or other cost.",
        ),
    )


def get_default_webull_dca_standard_profile() -> BrokerProfile:
    """Webull Thailand Recurring DCA (Standard 0.10% Scenario)."""
    return BrokerProfile(
        broker_id="WEBULL_DCA_STANDARD",
        display_name="Webull Thailand (DCA - 0.10% conflict sensitivity)",
        funding_channel="LOCAL_THB_QR_ATS",
        commission_policy=CommissionPolicy(
            policy_type="PERCENTAGE",
            rate=Decimal("0.0010"),
            vat_applicable=True,
            applicable_order_type="DCA",
            evidence_status="OFFICIAL_SOURCE_CONFLICT",
            cat_fee_per_share_usd=WEBULL_CAT_FEE_PER_SHARE_USD,
        ),
        fractional_supported=True,
        min_order_usd=Decimal("1"),
        platform_id="WEBULL",
        eligibility_status="CONDITIONALLY_ELIGIBLE",
        evidence_notes=(
            "0.10_PERCENT_CONFLICT_SENSITIVITY: 0.10% rate described by the Webull guide published 2026-06-15, kept until the conflict is resolved.",
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
            applicable_order_type="ALL",
            evidence_status="NOT_APPLICABLE",
        ),
        fractional_supported=False,
        min_order_thb=Decimal("0.0"),
        funding_terms=None,
        eligibility_status="DOCUMENTED",
        evidence_notes=(
            "Baseline control: 100% held in domestic cash; zero transfer friction, zero market volatility.",
        ),
    )


ELIGIBILITY_COLUMNS = (
    "broker_id", "symbol", "instrument_type", "searchable", "whole_share_eligible", "fractional_eligible",
    "manual_order_eligible", "dca_eligible", "min_notional", "trading_session", "account_permission",
    "source_url", "verified_date", "evidence_status",
)


def _tri_state(value: str, field: str) -> Optional[bool]:
    text = value.strip().upper()
    if text in ("", "UNKNOWN"):
        return None
    if text in ("TRUE", "FALSE"):
        return text == "TRUE"
    raise DataContractError(f"ELIGIBILITY_BAD_BOOLEAN: {field}={value!r}.")


def load_security_eligibility(path: str) -> Tuple[SecurityEligibility, ...]:
    """Read the owner-maintained ETF eligibility matrix; UNKNOWN cells stay ``None``."""
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != ELIGIBILITY_COLUMNS:
            raise DataContractError(f"ELIGIBILITY_BAD_COLUMNS: {reader.fieldnames}.")
        rows = list(reader)
    entries = []
    for row in rows:
        min_text = row["min_notional"].strip().upper()
        entries.append(
            SecurityEligibility(
                platform_id=row["broker_id"].strip(),
                symbol=row["symbol"].strip().upper(),
                instrument_type=row["instrument_type"].strip(),
                searchable=_tri_state(row["searchable"], "searchable"),
                whole_share_eligible=_tri_state(row["whole_share_eligible"], "whole_share_eligible"),
                fractional_eligible=_tri_state(row["fractional_eligible"], "fractional_eligible"),
                manual_order_eligible=_tri_state(row["manual_order_eligible"], "manual_order_eligible"),
                dca_eligible=_tri_state(row["dca_eligible"], "dca_eligible"),
                min_notional_usd=None if min_text in ("", "UNKNOWN") else Decimal(min_text),
                trading_session=row["trading_session"].strip(),
                account_permission=row["account_permission"].strip(),
                source_url=row["source_url"].strip(),
                verified_date=row["verified_date"].strip(),
                evidence_status=row["evidence_status"].strip(),
            )
        )
    return tuple(entries)


def load_candidate_profiles(
    route_terms: RouteTerms | None = None,
    include_both_webull_dca_scenarios: bool = True,
    eligibility: Sequence[SecurityEligibility] = (),
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
    return tuple(
        replace(p, security_eligibility=tuple(e for e in eligibility if e.platform_id == p.platform_id))
        for p in profiles
    )
