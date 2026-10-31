"""D6 V38 Investor Decision Core acceptance tests (synthetic inputs only)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import date
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Any, Optional

import pytest

import acash.research.d6.investor_decision as decision_module
from acash.core.domain.exceptions import DataContractError
from acash.research.d6.broker_profiles import (
    FEE_SNAPSHOT_SHA256,
    get_default_cash_profile,
    get_default_dime_profile,
    get_default_ibkr_profile,
    get_default_webull_dca_zero_profile,
    get_default_webull_manual_profile,
    kbank_kplus_swift_terms,
    load_candidate_profiles,
    load_security_eligibility,
)
from acash.research.d6.investor_decision import (
    COST_STATUS_ALL_IN_DOCUMENTED,
    COST_STATUS_LOWER_BOUND_ONLY,
    COST_STATUS_QUOTE_OBSERVED,
    COST_STATUS_SCENARIO_ONLY,
    DECISION_STATUS_COMPLETE,
    DECISION_STATUS_NOT_ELIGIBLE,
    SIZING_POLICY,
    SPREAD_QUOTE_CURRENT,
    SPREAD_QUOTE_HISTORICAL,
    SPREAD_QUOTE_INDICATIVE,
    SPREAD_QUOTE_REFERENCE_LIMITED,
    SPREAD_QUOTE_SYNTHETIC,
    BrokerAssessment,
    BrokerProfile,
    CommissionPolicy,
    InvestmentPlan,
    SecurityEligibility,
    UserFxQuote,
    compare_investment_plans,
    demo_outputs,
    format_markdown_report,
)
from acash.research.d6.route_cost import RouteTerms

D = Decimal
AS_OF = date(2026, 10, 31)
REF = D("35")
REPO = Path(__file__).resolve().parents[3]
SNAPSHOT = REPO / "docs/research/evidence/v38_fee_snapshot_20261030.json"
DEMO_PREFIX = REPO / "docs/research/evidence/v38_acceptance_demo_20261031"
MATRIX = REPO / "docs/research/evidence/v38_etf_eligibility_matrix_20261101.csv"


def _plan(**changes: Any) -> InvestmentPlan:
    base = InvestmentPlan(
        monthly_savings_thb=D("3500"),
        reference_thb_per_usd=REF,
        portfolio_weights={"VOO": D("1")},
        ref_prices_usd={"VOO": D("500"), "BND": D("72")},
    )
    return replace(base, **changes)


def _quote(**changes: Any) -> UserFxQuote:
    base = UserFxQuote(
        broker_id="WEBULL_MANUAL",
        quote_observed_at="2026-10-31T10:00:00+07:00",
        quoted_thb_per_usd=D("35.35"),
        source_amount=D("3535"),
        target_amount=D("100.00"),
        quote_valid_until="2026-10-31T10:01:30+07:00",
        reference_rate=D("35"),
        reference_rate_timestamp="2026-10-31T10:01:00+07:00",
    )
    return replace(base, **changes)


def _one(profile: BrokerProfile, plan: InvestmentPlan, as_of: date = AS_OF) -> BrokerAssessment:
    return compare_investment_plans([profile], plan, as_of).assessments[0]


def _terms(**changes: Any) -> RouteTerms:
    base = RouteTerms(
        route_id="SYNTH_ROUTE",
        delivered_currency="USD",
        fixed_fee_thb=D("250"),
        fx_spread=None,
        deducted_fee_usd=None,
        intermediary_fee_usd=None,
        receiving_fee_usd=None,
        min_amount_thb=D("1000"),
    )
    return replace(base, **changes)


def _verified(platform_id: str, symbol: str = "VOO", **changes: Any) -> SecurityEligibility:
    base = SecurityEligibility(
        platform_id=platform_id, symbol=symbol, instrument_type="ETF", searchable=True, whole_share_eligible=True,
        fractional_eligible=True, manual_order_eligible=True, dca_eligible=True, min_notional_usd=None,
        trading_session="REGULAR", account_permission="VERIFIED", source_url="SYNTHETIC_FIXTURE",
        verified_date="2026-10-31", evidence_status="HYPOTHETICAL_INPUT",
    )
    return replace(base, **changes)


def _documented_synthetic_profile(route_evidence: str = "OFFICIAL_PROVIDER_TARIFF", **term_changes: Any) -> BrokerProfile:
    fields: dict[str, Any] = {
        "fx_spread": D("0.01"), "deducted_fee_usd": D("0"), "intermediary_fee_usd": D("0"), "receiving_fee_usd": D("0"),
        "purpose_supported": True, "beneficiary_supported": True, "evidence_status": route_evidence,
    }
    fields.update(term_changes)
    policy = replace(
        get_default_ibkr_profile().commission_policy,
        pass_through_fees_known=True, fractional_rate=None, fractional_min_usd=None,
    )
    return replace(
        get_default_ibkr_profile(_terms(**fields)),
        broker_id="SYNTH_DOC",
        platform_id="SYNTH_DOC",
        commission_policy=policy,
        security_eligibility=(_verified("SYNTH_DOC"),),
        eligibility_status="DOCUMENTED",
    )


# --- P0.1 numerical completeness versus evidence ---------------------------------------------

def test_hypothetical_spread_completes_math_but_is_scenario_only() -> None:
    a = _one(get_default_webull_manual_profile(), _plan(assumed_fx_spread=D("0.01")))
    assert a.numerically_complete is True
    assert a.cost_status == COST_STATUS_SCENARIO_ONLY


def test_unknown_fx_is_preserved_as_lower_bound() -> None:
    a = _one(get_default_webull_manual_profile(), _plan())
    assert "WEBULL_MANUAL_FX_SPREAD" in a.unknown_components
    assert a.cost_status == COST_STATUS_LOWER_BOUND_ONLY and a.numerically_complete is False


def test_current_user_notional_quote_sets_quote_observed() -> None:
    a = _one(get_default_webull_manual_profile(), _plan(user_quotes={"WEBULL_MANUAL": _quote()}, evaluated_at="2026-10-31T10:01:10+07:00"))
    assert a.spread_source == SPREAD_QUOTE_CURRENT
    assert a.cost_status == COST_STATUS_QUOTE_OBSERVED
    assert _quote().implied_spread == D("0.01")


def test_observed_quote_cannot_verify_unrelated_charges() -> None:
    quote = _quote(broker_id="IBKR")
    a = _one(get_default_ibkr_profile(), _plan(user_quotes={"IBKR": quote}, evaluated_at="2026-10-31T10:01:10+07:00"))
    assert a.spread_source == SPREAD_QUOTE_CURRENT
    assert "INTERMEDIARY_FEE_USD" in a.unknown_components
    assert "IBKR_PASS_THROUGH_FEES" in a.unknown_components
    assert "FX_SPREAD" not in a.unknown_components and "IBKR_FX_SPREAD" not in a.unknown_components
    assert a.cost_status == COST_STATUS_LOWER_BOUND_ONLY
    unquoted = _one(get_default_ibkr_profile(), _plan())
    assert [c for c in unquoted.unknown_components if c.endswith("FX_SPREAD")] == ["IBKR_FX_SPREAD"]


def test_current_quote_cannot_qualify_a_historical_scenario() -> None:
    plan = _plan(user_quotes={"WEBULL_MANUAL": _quote()}, evaluated_at="2026-10-31T10:01:10+07:00")
    a = _one(get_default_webull_manual_profile(), plan, as_of=date(2020, 1, 2))
    assert a.spread_source == SPREAD_QUOTE_HISTORICAL
    assert a.cost_status == COST_STATUS_SCENARIO_ONLY


def test_stale_quote_is_historical_only() -> None:
    plan = _plan(user_quotes={"WEBULL_MANUAL": _quote()}, evaluated_at="2026-10-31T10:05:00+07:00")
    a = _one(get_default_webull_manual_profile(), plan)
    assert a.spread_source == SPREAD_QUOTE_HISTORICAL
    assert any(n.startswith("USER_QUOTE_STALE") for n in a.evidence_notes)
    unknown_validity = _plan(user_quotes={"WEBULL_MANUAL": _quote(quote_valid_until=None)}, evaluated_at="2026-10-31T10:00:30+07:00")
    assert _one(get_default_webull_manual_profile(), unknown_validity).spread_source == SPREAD_QUOTE_HISTORICAL


def test_quote_reference_timing_mismatch_is_not_an_exact_spread() -> None:
    quote = _quote(reference_rate_timestamp="2026-10-30T16:00:00+00:00")
    assert quote.spread_basis == "TIMING_MISMATCH"
    a = _one(get_default_webull_manual_profile(), _plan(user_quotes={"WEBULL_MANUAL": quote}, evaluated_at="2026-10-31T10:01:10+07:00"))
    assert a.spread_source == SPREAD_QUOTE_REFERENCE_LIMITED
    assert a.cost_status == COST_STATUS_SCENARIO_ONLY
    assert any("TIMING_MISMATCH" in n for n in a.evidence_notes)
    assert _quote(reference_rate_timestamp=None).spread_basis == "REFERENCE_TIME_UNKNOWN"


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"quote_direction": "USD_TO_THB"}, "USER_QUOTE_UNSUPPORTED_DIRECTION"),
        ({"target_amount": None}, "USER_QUOTE_PARTIAL_AMOUNTS"),
        ({"target_amount": D("80")}, "USER_QUOTE_AMOUNT_RATE_MISMATCH"),
        ({"quote_source_type": "SCREEN_SCRAPE"}, "USER_QUOTE_UNKNOWN_PROVENANCE"),
        ({"quote_source_type": "SYNTHETIC_FIXTURE"}, "USER_QUOTE_PROVENANCE_CONTRADICTION"),
        ({"observational_status": "SYNTHETIC"}, "USER_QUOTE_PROVENANCE_CONTRADICTION"),
        ({"reference_rate_kind": "MIDPOINT"}, "USER_QUOTE_UNKNOWN_PROVENANCE"),
        ({"quote_observed_at": "2026-10-31T10:00:00"}, "DECISION_TIMESTAMP_WITHOUT_ZONE"),
        ({"quote_valid_until": "2026-10-31T09:00:00+07:00"}, "USER_QUOTE_VALIDITY_BEFORE_OBSERVATION"),
        ({"quoted_thb_per_usd": D("NaN")}, "DECISION_INVALID_MONEY"),
    ],
)
def test_quote_contract_rejects_malformed_input(changes: dict[str, Any], code: str) -> None:
    with pytest.raises(DataContractError, match=code):
        _quote(**changes)


def test_quote_broker_key_mismatch_raises() -> None:
    with pytest.raises(DataContractError, match="USER_QUOTE_BROKER_MISMATCH"):
        _plan(user_quotes={"DIME": _quote()})


# --- P0-A quote provenance ------------------------------------------------------------------

LIVE = "2026-10-31T10:01:10+07:00"


def _webull_with(quote: UserFxQuote, evaluated_at: str = LIVE) -> BrokerAssessment:
    return _one(get_default_webull_manual_profile(), _plan(user_quotes={"WEBULL_MANUAL": quote}, evaluated_at=evaluated_at))


def test_synthetic_quote_never_becomes_quote_observed() -> None:
    synthetic = _quote(quote_source_type="SYNTHETIC_FIXTURE", observational_status="SYNTHETIC")
    a = _webull_with(synthetic)
    assert a.spread_source == SPREAD_QUOTE_SYNTHETIC and a.cost_status == COST_STATUS_SCENARIO_ONLY
    hypothetical = _quote(quote_source_type="HYPOTHETICAL_INPUT", observational_status="SYNTHETIC")
    assert _webull_with(hypothetical).cost_status == COST_STATUS_SCENARIO_ONLY


def test_timestamp_alone_is_not_authenticity_and_indicative_rate_is_not_a_quote() -> None:
    indicative = _quote(source_amount=None, target_amount=None)
    assert _webull_with(indicative).spread_source == SPREAD_QUOTE_INDICATIVE
    screenshot = _quote(observational_status="USER_SCREENSHOT_INDICATIVE")
    a = _webull_with(screenshot)
    assert a.spread_source == SPREAD_QUOTE_INDICATIVE and a.cost_status == COST_STATUS_SCENARIO_ONLY
    observed = _webull_with(_quote())
    assert any("not independently authenticated" in n for n in observed.evidence_notes)


def test_expired_quote_is_not_current() -> None:
    a = _webull_with(_quote(), evaluated_at="2026-10-31T10:01:31+07:00")
    assert a.spread_source == SPREAD_QUOTE_HISTORICAL and a.cost_status == COST_STATUS_SCENARIO_ONLY


@pytest.mark.parametrize(
    ("kind", "basis"),
    [("DAILY_PROXY", "DAILY_REFERENCE_PROXY"), ("HYPOTHETICAL", "HYPOTHETICAL_REFERENCE")],
)
def test_non_contemporaneous_reference_is_reference_limited(kind: str, basis: str) -> None:
    quote = _quote(reference_rate_kind=kind)
    assert quote.spread_basis == basis
    a = _webull_with(quote)
    assert a.spread_source == SPREAD_QUOTE_REFERENCE_LIMITED and a.cost_status == COST_STATUS_SCENARIO_ONLY
    assert _quote().spread_basis == "CONTEMPORANEOUS_COMPARABLE_REFERENCE"


# --- P1-B route evidence ---------------------------------------------------------------------

def test_synthetic_route_terms_cannot_be_all_in_documented() -> None:
    synthetic = _one(_documented_synthetic_profile(route_evidence="HYPOTHETICAL_INPUT"), _plan())
    assert synthetic.numerically_complete is True
    assert synthetic.cost_status == COST_STATUS_SCENARIO_ONLY
    promo = _one(_documented_synthetic_profile(route_evidence="PROMOTIONAL_CLAIM"), _plan())
    assert promo.cost_status == COST_STATUS_SCENARIO_ONLY
    official = _one(_documented_synthetic_profile(), _plan())
    assert official.cost_status == COST_STATUS_ALL_IN_DOCUMENTED and official.decision_status == DECISION_STATUS_COMPLETE
    default_terms = get_default_ibkr_profile().funding_terms
    assert default_terms is not None and default_terms.fx_spread is None
    assert default_terms.route_id == "KBANK_KPLUS_SWIFT_SHAR" and default_terms.standard_fee_thb is None
    assert _one(get_default_ibkr_profile(), _plan()).cost_status == COST_STATUS_LOWER_BOUND_ONLY


# --- P0.2 input hash coverage ----------------------------------------------------------------

def _hash(profile: BrokerProfile, plan: Optional[InvestmentPlan] = None, as_of: date = AS_OF, digest: str = FEE_SNAPSHOT_SHA256) -> str:
    return compare_investment_plans([profile], plan or _plan(), as_of, digest).input_hash


@pytest.mark.parametrize(
    "changes",
    [
        {"fixed_fee_thb": D("300")},
        {"intermediary_fee_usd": D("15")},
        {"receiving_fee_usd": D("1")},
        {"purpose_supported": True},
        {"beneficiary_supported": True},
        {"promotion_end_documented": False},
        {"max_amount_thb": D("2000000")},
        {"variable_fee_min_thb": D("1")},
    ],
)
def test_route_term_changes_change_hash(changes: dict[str, Any]) -> None:
    assert _hash(get_default_ibkr_profile(_terms(**changes))) != _hash(get_default_ibkr_profile(_terms()))


def test_plan_profile_and_context_changes_change_hash() -> None:
    base = _hash(get_default_webull_manual_profile())
    variants = [
        _hash(replace(get_default_webull_manual_profile(), security_eligibility=(_verified("WEBULL"),))),
        _hash(replace(get_default_webull_manual_profile(), min_order_usd=D("2"))),
        _hash(replace(get_default_webull_manual_profile(), min_order_thb=D("41"))),
        _hash(get_default_webull_manual_profile(), _plan(ref_prices_usd={"VOO": D("501")})),
        _hash(get_default_webull_manual_profile(), _plan(user_quotes={"WEBULL_MANUAL": _quote()})),
        _hash(get_default_webull_manual_profile(), _plan(user_quotes={"WEBULL_MANUAL": _quote(reference_rate_timestamp=None)})),
        _hash(get_default_webull_manual_profile(), _plan(order_type="DCA")),
        _hash(get_default_webull_manual_profile(), _plan(free_trades_available=0)),
        _hash(get_default_webull_manual_profile(), as_of=date(2026, 11, 1)),
        _hash(get_default_webull_manual_profile(), digest="0" * 64),
    ]
    assert base not in variants and len(set(variants)) == len(variants)


def test_hash_is_profile_order_invariant() -> None:
    profiles = list(load_candidate_profiles())
    plan = _plan()
    assert compare_investment_plans(profiles, plan, AS_OF).input_hash == compare_investment_plans(profiles[::-1], plan, AS_OF).input_hash


# --- P0.3 order and security eligibility -----------------------------------------------------

def test_order_below_minimum_is_not_executable() -> None:
    plan = _plan(monthly_savings_thb=D("100"), portfolio_weights={"VOO": D("0.6"), "BND": D("0.4")})
    a = _one(get_default_dime_profile(), plan)
    assert a.eligibility_status == "NOT_ELIGIBLE" and a.decision_status == DECISION_STATUS_NOT_ELIGIBLE
    assert any(n.startswith("ORDER_BELOW_MINIMUM: BND") for n in a.evidence_notes)


def test_manual_and_dca_incompatibility_both_directions() -> None:
    a = _one(get_default_webull_dca_zero_profile(), _plan(order_type="MANUAL"))
    b = _one(get_default_webull_manual_profile(), _plan(order_type="DCA"))
    for result in (a, b):
        assert result.eligibility_status == "ORDER_TYPE_INCOMPATIBLE"
        assert result.investable_balance_usd is None


def test_security_and_fractional_eligibility_default_to_unverified() -> None:
    a = _one(get_default_webull_manual_profile(), _plan(assumed_fx_spread=D("0.01")))
    assert a.eligibility_status == "ACCOUNT_SPECIFIC_UNVERIFIED"
    assert any(n.startswith("SECURITY_ELIGIBILITY_UNKNOWN: VOO on WEBULL") for n in a.evidence_notes)
    base = _verified("WEBULL")
    for entry in (
        replace(base, searchable=False), replace(base, fractional_eligible=False),
        replace(base, manual_order_eligible=False), replace(base, account_permission="DENIED"),
    ):
        denied = replace(get_default_webull_manual_profile(), security_eligibility=(entry,))
        assert _one(denied, _plan()).decision_status == DECISION_STATUS_NOT_ELIGIBLE
    partial = replace(get_default_webull_manual_profile(), security_eligibility=(_verified("WEBULL", fractional_eligible=None),))
    assert _one(partial, _plan()).eligibility_status == "ACCOUNT_SPECIFIC_UNVERIFIED"
    whole_only = replace(get_default_webull_manual_profile(), fractional_supported=False)
    assert _one(whole_only, _plan()).decision_status == DECISION_STATUS_NOT_ELIGIBLE


def test_route_amount_out_of_range_is_not_eligible() -> None:
    a = _one(get_default_ibkr_profile(_terms(min_amount_thb=D("5000"))), _plan())
    assert a.decision_status == DECISION_STATUS_NOT_ELIGIBLE


def test_fees_exceeding_funding_are_not_eligible() -> None:
    policy = CommissionPolicy(policy_type="FIXED_PER_SHARE", per_share_usd=D("0.0035"), min_commission_usd=D("5"))
    profile = replace(get_default_webull_manual_profile(), commission_policy=policy)
    a = _one(profile, _plan(monthly_savings_thb=D("100"), assumed_fx_spread=D("0")))
    assert a.decision_status == DECISION_STATUS_NOT_ELIGIBLE
    assert any(n.startswith("FEES_EXCEED_ORDER") for n in a.evidence_notes)
    for receiving in (D("200"), D("92")):
        route = _one(_documented_synthetic_profile(receiving_fee_usd=receiving), _plan())
        assert route.decision_status == DECISION_STATUS_NOT_ELIGIBLE
    assert any(n.startswith("FEES_EXCEED_FUNDING") for n in route.evidence_notes)


# --- P0.4 price-dependent fees ---------------------------------------------------------------

def test_dime_missing_price_on_paid_order_is_unknown_including_cat() -> None:
    plan = _plan(
        monthly_savings_thb=D("3000"), portfolio_weights={"VOO": D("0.6"), "BND": D("0.4")},
        order_sequence=("VOO", "BND"), ref_prices_usd={"VOO": D("500")},
    )
    a = _one(get_default_dime_profile(), plan)
    assert {"DIME_BND_PRICE_TIER_UNKNOWN", "DIME_BND_CAT_FEE"} <= set(a.unknown_components)


def test_dime_free_entitlement_follows_chronology() -> None:
    weights = {"VOO": D("0.6"), "BND": D("0.4")}
    first_voo = _one(get_default_dime_profile(), _plan(portfolio_weights=weights, order_sequence=("VOO", "BND"), assumed_fx_spread=D("0")))
    first_bnd = _one(get_default_dime_profile(), _plan(portfolio_weights=weights, order_sequence=("BND", "VOO"), assumed_fx_spread=D("0")))
    usd = D("3500") / REF

    def paid(allocation: D, price: D) -> D:
        return allocation / (1 + D("0.0015") * D("1.07") + D("0.000046") / price) * D("0.0015")

    assert first_voo.commission_usd == paid(usd * D("0.4"), D("72"))
    assert first_bnd.commission_usd == paid(usd * D("0.6"), D("500"))
    assert first_voo.free_orders_used == first_bnd.free_orders_used == 1
    none_free = _one(get_default_dime_profile(), _plan(portfolio_weights=weights, free_trades_available=0, assumed_fx_spread=D("0")))
    assert none_free.free_orders_used == 0


def test_dime_low_price_tier_uses_per_share_commission() -> None:
    plan = _plan(free_trades_available=0, ref_prices_usd={"VOO": D("5")}, assumed_fx_spread=D("0"))
    a = _one(get_default_dime_profile(), plan)
    notional = (D("3500") / REF) / (1 + D("0.002") * D("1.07") + D("0.000046") / D("5"))
    assert a.commission_usd == notional / D("5") * D("0.01")


def test_dime_supplemental_promotion_is_not_applied_and_conflict_recorded() -> None:
    assert get_default_dime_profile().commission_policy.free_orders_count == 1
    rules = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["rules"]
    promo = [r for r in rules if r["fee_category"] == "PROMOTION_SUPPLEMENTAL_FREEBIE"]
    assert len(promo) == 1 and promo[0]["campaign_status"] == "CURRENT_SOURCE_2026-12-31_WITH_HISTORICAL_CONFLICT"
    assert promo[0]["observed_end_dates"] == ["2026-08-31", "2026-12-31"]


def test_webull_buy_side_cat_fee_and_missing_price() -> None:
    a = _one(get_default_webull_manual_profile(), _plan(assumed_fx_spread=D("0")))
    notional = (D("3500") / REF) / (1 + D("0.001") * D("1.07") + D("0.000024") / D("500"))
    assert a.regulatory_fees_usd == notional / D("500") * D("0.000024")
    b = _one(get_default_webull_manual_profile(), _plan(ref_prices_usd=None, assumed_fx_spread=D("0")))
    assert "WEBULL_MANUAL_VOO_CAT_FEE" in b.unknown_components


def test_ibkr_missing_price_keeps_minimum_as_lower_bound() -> None:
    a = _one(get_default_ibkr_profile(), _plan(ref_prices_usd=None))
    assert a.commission_usd == D("0.35")
    assert "IBKR_VOO_SHARE_COUNT" in a.unknown_components


# --- P0.5 currency incidence and conservation ------------------------------------------------

def test_thb_fees_before_conversion_and_usd_fees_after() -> None:
    a = _one(_documented_synthetic_profile(), _plan())
    converted = (D("3500") - D("250")) / (REF * D("1.01"))
    commission = max(D("0.35"), converted / D("500") * D("0.0035"))
    assert a.funding_friction_thb == D("250")
    assert a.fx_spread_cost_thb == D("3250") - converted * REF
    assert a.commission_usd == commission
    assert a.investable_balance_usd == (converted - commission).quantize(D("0.01"), rounding=ROUND_DOWN)


def test_usd_route_fees_are_deducted_after_conversion_without_spread_markup() -> None:
    profile = _documented_synthetic_profile(deducted_fee_usd=D("3"), intermediary_fee_usd=D("15"), receiving_fee_usd=D("5"))
    a = _one(profile, _plan())
    bought = D("3250") / (REF * D("1.01"))
    converted = bought - D("23")
    commission = max(D("0.35"), converted / D("500") * D("0.0035"))
    assert a.funding_friction_thb == D("250") + D("23") * REF
    assert a.fx_spread_cost_thb == D("3250") - bought * REF
    assert a.investable_balance_usd == (converted - commission).quantize(D("0.01"), rounding=ROUND_DOWN)
    wrong = (D("3500") - D("250") - D("23") * REF) / (REF * D("1.01"))
    assert a.investable_balance_usd != (wrong - commission).quantize(D("0.01"), rounding=ROUND_DOWN)


@pytest.mark.parametrize(
    ("profile", "plan"),
    [
        (_documented_synthetic_profile(intermediary_fee_usd=D("15"), receiving_fee_usd=D("5")), _plan()),
        (get_default_webull_manual_profile(), _plan(assumed_fx_spread=D("0.0123"))),
        (get_default_dime_profile(), _plan(portfolio_weights={"VOO": D("0.6"), "BND": D("0.4")}, free_trades_available=0)),
        (get_default_ibkr_profile(), _plan(assumed_fx_spread=D("0.005"))),
        (_documented_synthetic_profile(), _plan(monthly_savings_thb=D("3333.33"))),
    ],
)
def test_cash_conservation_and_bounded_rounding_residual(profile: BrokerProfile, plan: InvestmentPlan) -> None:
    a = _one(profile, plan)
    assert a.investable_balance_usd is not None
    assert a.total_known_friction_thb + a.investable_balance_usd * REF == a.gross_funding_thb
    parts = a.funding_friction_thb + a.fx_spread_cost_thb + a.commission_thb + a.vat_thb + a.regulatory_fees_thb
    assert abs(parts + a.rounding_residual_thb - a.total_known_friction_thb) <= DECIMAL_PRECISION_TOL
    assert -DECIMAL_PRECISION_TOL <= a.rounding_residual_thb < D("0.01") * REF


# 28-digit Decimal context precision on THB sums, not a cash tolerance.
DECIMAL_PRECISION_TOL = D("1e-20")


def test_cash_control_has_no_friction_and_no_exposure() -> None:
    a = _one(get_default_cash_profile(), _plan())
    assert a.total_known_friction_thb == 0 and a.investable_balance_usd == 0
    assert a.decision_status == "CASH_NO_TRADE"


# --- P0.6 snapshot provenance ----------------------------------------------------------------

def test_snapshot_digest_and_provenance() -> None:
    raw = SNAPSHOT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FEE_SNAPSHOT_SHA256
    data = json.loads(raw)
    prov = data["provenance"]
    assert prov["capture_timestamp_status"] == "CAPTURE_TIME_UNKNOWN"
    assert "generated_at" not in data
    assert [x["sha256"][:8] for x in prov["lineage"]] == ["ccb899ca", "1ddbcf98", "b2db8e05", "89d223fa"]
    assert FEE_SNAPSHOT_SHA256 not in {x["sha256"] for x in prov["lineage"]}
    by_key = {(r["broker_id"], r["fee_category"]): r for r in data["rules"]}
    assert (by_key[("WEBULL", "REGULATORY_TAF")]["min_fee"], by_key[("WEBULL", "REGULATORY_TAF")]["max_fee"]) == ("0.01", "9.79")
    assert by_key[("WEBULL", "REGULATORY_SEC")]["min_fee"] == "0.01"
    assert by_key[("IBKR", "COMMISSION_FRACTIONAL")]["evidence_status"] == "OFFICIAL_PROVIDER_TARIFF"
    assert {b: by_key[("KBANK_KPLUS", f"FUNDING_SWIFT_{b}")]["currency"] for b in ("SHAR", "DEBT", "CRED")} == {"SHAR": "THB", "DEBT": "THB", "CRED": "USD"}
    assert by_key[("KBANK_KBIZ", "FUNDING_SWIFT_PROMOTION")]["promotion_effective_dates"] == "UNKNOWN"
    assert "PENDING_RESEARCH_SOURCE" not in raw.decode("utf-8")
    freebie = by_key[("DIME", "PROMOTION_SUPPLEMENTAL_FREEBIE")]
    assert freebie["current_source_version"]["end_date"] == "2026-12-31" and "2026-08-31" in freebie["observed_end_dates"]
    created = date.fromisoformat(prov["snapshot_created_on"])
    assert all(date.fromisoformat(r["verified_date"]) <= created for r in data["rules"])


# --- P1-A order notional versus fee affordability -------------------------------------------

def _zero_commission_profile() -> BrokerProfile:
    return replace(
        get_default_webull_dca_zero_profile(),
        broker_id="ZERO_MANUAL",
        commission_policy=replace(get_default_webull_dca_zero_profile().commission_policy, applicable_order_type="ALL"),
    )


AFFORDABILITY_CASES = [
    (profile, savings, weights)
    for profile in (
        get_default_dime_profile(), get_default_webull_manual_profile(), get_default_ibkr_profile(),
        _documented_synthetic_profile(), _zero_commission_profile(),
    )
    for savings in (D("60"), D("125.05"), D("500"), D("3000"), D("100000"))
    for weights in ({"VOO": D("1")}, {"VOO": D("0.6"), "BND": D("0.4")}, {"VOO": D("0.5"), "BND": D("0.3"), "GLD": D("0.1"), "BIL": D("0.1")})
]


@pytest.mark.parametrize(("profile", "savings", "weights"), AFFORDABILITY_CASES)
def test_order_notional_plus_charges_never_exceeds_cash(profile: BrokerProfile, savings: D, weights: dict[str, D]) -> None:
    prices = {"VOO": D("500"), "BND": D("72"), "GLD": D("240"), "BIL": D("91.5")}
    plan = _plan(monthly_savings_thb=savings, portfolio_weights=weights, ref_prices_usd=prices, assumed_fx_spread=D("0.01"), free_trades_available=0)
    a = _one(profile, plan)
    if a.decision_status == DECISION_STATUS_NOT_ELIGIBLE:
        return
    assert a.investable_balance_usd is not None
    charges_usd = a.commission_usd + a.vat_thb / REF + a.regulatory_fees_usd
    spent_thb = a.funding_friction_thb + a.fx_spread_cost_thb + (sum(n for _, n in a.order_notionals_usd) + charges_usd) * REF
    assert spent_thb <= a.gross_funding_thb + DECIMAL_PRECISION_TOL
    for sym, notional in a.order_notionals_usd:
        assert notional > 0
        assert notional * REF >= profile.min_order_thb and notional >= profile.min_order_usd, sym


def test_minimum_is_checked_on_post_fee_notional() -> None:
    plan = _plan(
        monthly_savings_thb=D("125.05"), portfolio_weights={"VOO": D("0.6"), "BND": D("0.4")},
        order_sequence=("VOO", "BND"), assumed_fx_spread=D("0"), free_trades_available=0,
    )
    a = _one(get_default_dime_profile(), plan)
    assert D("125.05") * D("0.4") > D("50")
    assert a.decision_status == DECISION_STATUS_NOT_ELIGIBLE
    assert any(n.startswith("ORDER_BELOW_MINIMUM: BND") for n in a.evidence_notes)
    assert SIZING_POLICY == "FEES_SOLVED_ON_FINAL_NOTIONAL"


def test_webull_usd_one_minimum_is_separate_from_thb() -> None:
    profile = get_default_webull_manual_profile()
    assert profile.min_order_usd == D("1") and profile.min_order_thb == 0
    plan = _plan(monthly_savings_thb=D("60"), portfolio_weights={"VOO": D("0.5"), "BND": D("0.5")}, assumed_fx_spread=D("0"))
    assert _one(profile, plan).decision_status == DECISION_STATUS_NOT_ELIGIBLE


# --- KBank K PLUS SWIFT charge bearers -------------------------------------------------------

@pytest.mark.parametrize(("bearer", "thb", "usd"), [("SHAR", "250", "0"), ("DEBT", "950", "0"), ("CRED", "0", "12")])
def test_kbank_charge_bearers_preserve_currency_incidence(bearer: str, thb: str, usd: str) -> None:
    profile = get_default_ibkr_profile(kbank_kplus_swift_terms(bearer))
    a = _one(profile, _plan(assumed_fx_spread=D("0")))
    assert a.funding_friction_thb == D(thb) + D(usd) * REF
    assert {"INTERMEDIARY_FEE_USD", "RECEIVING_FEE_USD"} <= set(a.unknown_components)
    later = _one(profile, _plan(assumed_fx_spread=D("0")), as_of=date(2027, 1, 4))
    assert "POST_PROMOTION_FEE" in later.unknown_components and later.cost_status == COST_STATUS_LOWER_BOUND_ONLY
    with pytest.raises(DataContractError, match="KBANK_UNKNOWN_CHARGE_BEARER"):
        kbank_kplus_swift_terms("OUR")


# --- IBKR whole versus fractional (Footnote 11) ----------------------------------------------

def _ibkr_local(price: D) -> tuple[BrokerProfile, Any]:
    profile = replace(
        get_default_webull_manual_profile(), broker_id="IBKR_LOCAL", platform_id="IBKR_LOCAL",
        commission_policy=get_default_ibkr_profile().commission_policy, min_order_usd=D("0"),
    )
    return profile, lambda usd: _plan(monthly_savings_thb=usd * REF, assumed_fx_spread=D("0"), ref_prices_usd={"VOO": price})


@pytest.mark.parametrize(("allocation", "notional", "commission"), [(D("5.05"), D("5.00"), D("0.05")), (D("0.76"), D("0.75"), D("0.01"))])
def test_ibkr_pure_fractional_uses_footnote_11_on_final_value(allocation: D, notional: D, commission: D) -> None:
    profile, plan = _ibkr_local(D("500"))
    a = _one(profile, plan(allocation))
    assert a.order_notionals_usd == (("VOO", notional),)
    assert a.commission_usd == commission
    assert not any("FRACTIONAL" in c or "MIXED" in c for c in a.unknown_components)


def test_ibkr_whole_share_uses_ordinary_minimum() -> None:
    profile, plan = _ibkr_local(D("100"))
    a = _one(profile, plan(D("300.35")))
    assert a.order_notionals_usd == (("VOO", D("300.00")),) and a.commission_usd == D("0.35")


def test_ibkr_whole_share_allocation_turns_mixed_after_fees() -> None:
    profile, plan = _ibkr_local(D("100"))
    a = _one(profile, plan(D("300")))
    assert a.commission_usd == D("0.35") and a.order_notionals_usd == (("VOO", D("299.65")),)
    assert "IBKR_LOCAL_VOO_MIXED_ORDER_COMMISSION" in a.unknown_components
    assert a.cost_status == COST_STATUS_LOWER_BOUND_ONLY


def test_fee_feedback_reclassifies_and_conserves_cash() -> None:
    profile, plan = _ibkr_local(D("100"))
    a = _one(profile, plan(D("100.20")))
    ((_, notional),) = a.order_notionals_usd
    assert notional < D("100") and a.commission_usd == notional * D("0.01")
    assert notional + a.commission_usd == D("100.20")


# --- ETF eligibility matrix ------------------------------------------------------------------

def test_committed_eligibility_matrix_is_all_unverified() -> None:
    entries = load_security_eligibility(str(MATRIX))
    assert {(e.platform_id, e.symbol) for e in entries} == {
        (b, s) for b in ("DIME", "IBKR", "WEBULL") for s in ("BIL", "BND", "GLD", "VOO")
    }
    assert all(e.evidence_status == "ACCOUNT_SPECIFIC_UNVERIFIED" and e.account_permission == "UNVERIFIED" for e in entries)
    assert all(e.searchable is None and e.fractional_eligible is None for e in entries)
    profiles = load_candidate_profiles(eligibility=entries)
    webull = [p for p in profiles if p.platform_id == "WEBULL"]
    assert len(webull) == 3 and all(len(p.security_eligibility) == 4 for p in webull)
    a = _one(webull[0], _plan(assumed_fx_spread=D("0")))
    assert a.eligibility_status == "ACCOUNT_SPECIFIC_UNVERIFIED"


def test_eligibility_matrix_rejects_malformed_rows(tmp_path: Path) -> None:
    text = MATRIX.read_text(encoding="utf-8")
    bad_bool = tmp_path / "bad_bool.csv"
    bad_bool.write_text(text.replace("ETF,UNKNOWN", "ETF,MAYBE", 1), encoding="utf-8")
    with pytest.raises(DataContractError, match="ELIGIBILITY_BAD_BOOLEAN"):
        load_security_eligibility(str(bad_bool))
    bad_cols = tmp_path / "bad_cols.csv"
    bad_cols.write_text(text.replace("broker_id,", "broker,", 1), encoding="utf-8")
    with pytest.raises(DataContractError, match="ELIGIBILITY_BAD_COLUMNS"):
        load_security_eligibility(str(bad_cols))
    with pytest.raises(DataContractError, match="DECISION_BAD_ELIGIBILITY_MATRIX"):
        replace(get_default_dime_profile(), security_eligibility=(_verified("WEBULL"),))


def test_matrix_minimum_notional_is_enforced() -> None:
    profile = replace(get_default_webull_manual_profile(), security_eligibility=(_verified("WEBULL", min_notional_usd=D("500")),))
    assert _one(profile, _plan(assumed_fx_spread=D("0"))).decision_status == DECISION_STATUS_NOT_ELIGIBLE


# --- Reports and demo ------------------------------------------------------------------------

def test_markdown_is_deterministic_and_separates_questions() -> None:
    result = compare_investment_plans(load_candidate_profiles(), _plan(), AS_OF)
    report = format_markdown_report(result)
    assert report == format_markdown_report(result)
    assert "Scenario date: 2026-10-31" in report and result.input_hash in report
    assert "Numerically complete" in report and "Cost evidence" in report and "Eligibility" in report
    assert "No ranking is produced" in report


def test_demo_outputs_match_committed_artifacts_and_contain_no_all_in() -> None:
    json_text, md_text = demo_outputs()
    assert (json_text, md_text) == demo_outputs()
    payload = json.loads(json_text)
    statuses = {a["cost_status"] for s in payload.values() for a in s["assessments"]}
    assert COST_STATUS_ALL_IN_DOCUMENTED not in statuses and COST_STATUS_QUOTE_OBSERVED not in statuses
    dime = [a for a in payload["manual_1m_dime_quote"]["assessments"] if a["broker_id"] == "DIME"][0]
    assert dime["spread_source"] == SPREAD_QUOTE_SYNTHETIC and dime["cost_status"] == COST_STATUS_SCENARIO_ONLY
    assert SIZING_POLICY in md_text and "DAILY_REFERENCE_PROXY" in md_text and "Form 706-NA" in md_text
    assert Path(str(DEMO_PREFIX) + ".json").read_bytes() == json_text.encode("utf-8")
    assert Path(str(DEMO_PREFIX) + ".md").read_bytes() == md_text.encode("utf-8")


def test_engine_has_no_network_or_account_access() -> None:
    source = Path(decision_module.__file__).read_text(encoding="utf-8")
    for token in ("import requests", "urllib", "socket", "http.client", "httpx"):
        assert token not in source
