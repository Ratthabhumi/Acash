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
    load_candidate_profiles,
)
from acash.research.d6.investor_decision import (
    COST_STATUS_ALL_IN_DOCUMENTED,
    COST_STATUS_LOWER_BOUND_ONLY,
    COST_STATUS_QUOTE_OBSERVED,
    COST_STATUS_SCENARIO_ONLY,
    DECISION_STATUS_COMPLETE,
    DECISION_STATUS_NOT_ELIGIBLE,
    SPREAD_QUOTE_CURRENT,
    SPREAD_QUOTE_HISTORICAL,
    BrokerAssessment,
    BrokerProfile,
    CommissionPolicy,
    InvestmentPlan,
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


def _documented_synthetic_profile() -> BrokerProfile:
    terms = _terms(
        fx_spread=D("0.01"), deducted_fee_usd=D("0"), intermediary_fee_usd=D("0"), receiving_fee_usd=D("0"),
        purpose_supported=True, beneficiary_supported=True,
    )
    return replace(
        get_default_ibkr_profile(terms),
        broker_id="SYNTH_DOC",
        commission_policy=replace(get_default_ibkr_profile().commission_policy, pass_through_fees_known=True),
        supported_symbols=("VOO",),
        fractional_symbols=("VOO",),
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


def test_current_quote_sets_quote_observed() -> None:
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
    assert a.cost_status == COST_STATUS_SCENARIO_ONLY
    assert any("TIMING_MISMATCH" in n for n in a.evidence_notes)
    assert _quote(reference_rate_timestamp=None).spread_basis == "REFERENCE_TIME_UNKNOWN"


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"quote_direction": "USD_TO_THB"}, "USER_QUOTE_UNSUPPORTED_DIRECTION"),
        ({"source_amount": D("3000")}, "USER_QUOTE_PARTIAL_AMOUNTS"),
        ({"source_amount": D("3000"), "target_amount": D("80")}, "USER_QUOTE_AMOUNT_RATE_MISMATCH"),
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


def test_complete_synthetic_fixture_is_documented_but_only_synthetic() -> None:
    a = _one(_documented_synthetic_profile(), _plan())
    assert a.cost_status == COST_STATUS_ALL_IN_DOCUMENTED
    assert a.decision_status == DECISION_STATUS_COMPLETE
    default_terms = get_default_ibkr_profile().funding_terms
    assert default_terms is not None and default_terms.fx_spread is None


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
        _hash(replace(get_default_webull_manual_profile(), supported_symbols=("VOO",))),
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
    assert any(n.startswith("FRACTIONAL_ELIGIBILITY_UNVERIFIED: VOO") for n in a.evidence_notes)
    unsupported = replace(get_default_webull_manual_profile(), supported_symbols=("BND",))
    assert _one(unsupported, _plan()).decision_status == DECISION_STATUS_NOT_ELIGIBLE
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
    assert any(n.startswith("FEES_EXCEED_FUNDING") for n in a.evidence_notes)


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
    assert first_voo.commission_usd == usd * D("0.4") * D("0.0015")
    assert first_bnd.commission_usd == usd * D("0.6") * D("0.0015")
    assert first_voo.free_orders_used == first_bnd.free_orders_used == 1
    none_free = _one(get_default_dime_profile(), _plan(portfolio_weights=weights, free_trades_available=0, assumed_fx_spread=D("0")))
    assert none_free.free_orders_used == 0


def test_dime_low_price_tier_uses_per_share_commission() -> None:
    plan = _plan(free_trades_available=0, ref_prices_usd={"VOO": D("5")}, assumed_fx_spread=D("0"))
    a = _one(get_default_dime_profile(), plan)
    assert a.commission_usd == (D("3500") / REF / D("5")) * D("0.01")


def test_dime_supplemental_promotion_is_not_applied_and_conflict_recorded() -> None:
    assert get_default_dime_profile().commission_policy.free_orders_count == 1
    rules = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["rules"]
    promo = [r for r in rules if r["fee_category"] == "PROMOTION_SUPPLEMENTAL_FREEBIE"]
    assert len(promo) == 1 and promo[0]["campaign_status"] == "SOURCE_VERSION_CONFLICT"
    assert promo[0]["observed_end_dates"] == ["2026-08-31", "2026-12-31"]


def test_webull_buy_side_cat_fee_and_missing_price() -> None:
    a = _one(get_default_webull_manual_profile(), _plan(assumed_fx_spread=D("0")))
    assert a.regulatory_fees_usd == (D("3500") / REF / D("500")) * D("0.000024")
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


@pytest.mark.parametrize(
    ("profile", "plan"),
    [
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
    assert [x["sha256"][:8] for x in prov["lineage"]] == ["ccb899ca", "1ddbcf98"]
    created = date.fromisoformat(prov["snapshot_created_on"])
    assert all(date.fromisoformat(r["verified_date"]) <= created for r in data["rules"])


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
    assert COST_STATUS_ALL_IN_DOCUMENTED not in statuses
    dime = [a for a in payload["manual_1m_dime_quote"]["assessments"] if a["broker_id"] == "DIME"][0]
    assert dime["spread_source"] == SPREAD_QUOTE_CURRENT and dime["cost_status"] == COST_STATUS_QUOTE_OBSERVED
    assert Path(str(DEMO_PREFIX) + ".json").read_bytes() == json_text.encode("utf-8")
    assert Path(str(DEMO_PREFIX) + ".md").read_bytes() == md_text.encode("utf-8")


def test_engine_has_no_network_or_account_access() -> None:
    source = Path(decision_module.__file__).read_text(encoding="utf-8")
    for token in ("import requests", "urllib", "socket", "http.client", "httpx"):
        assert token not in source
