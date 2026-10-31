"""ACASH Investor Decision Pack (read-only, offline, illustrative).

Combines the V38 cost engine, the eligibility matrix and sanitized owner observations into one
deterministic report. It never ranks brokers, prescribes a portfolio, fetches data or trades.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from acash.core.serialization import CanonicalConfigSerializer
from acash.research.d6.broker_profiles import (
    kbank_kplus_swift_terms,
    load_candidate_profiles,
    load_security_eligibility,
)
from acash.research.d6.investor_decision import (
    CENT,
    DISCLOSURE_LINES,
    FEE_SNAPSHOT_SHA256,
    FEE_SNAPSHOT_VERSION,
    SIZING_POLICY,
    BrokerProfile,
    ComparisonResult,
    InvestmentPlan,
    SecurityEligibility,
    _plain,
    compare_investment_plans,
    comparison_to_dict,
)
from acash.research.d6.owner_evidence import (
    OwnerObservation,
    Reconciliation,
    evidence_digest,
    fx_comparability,
    load_observations,
    reconcile,
)

PACK_VERSION = "V38_DECISION_PACK_1"
PACK_AS_OF = date(2026, 11, 1)
PACK_MONTHLY_SAVINGS_THB = Decimal("3000")
# Illustrative inputs, not market data: chosen near the owner's indicative previews, not a mid-rate.
PACK_REFERENCE_THB_PER_USD = Decimal("33.86")
PACK_PRICES_USD = {"BND": Decimal("72.00"), "VOO": Decimal("500.00")}
PACK_WEIGHTS = {"BND": Decimal("0.4"), "VOO": Decimal("0.6")}
PACK_SCENARIOS = (("MANUAL", 1), ("MANUAL", 3), ("DCA", 1), ("DCA", 3))
DEFAULT_OBSERVATIONS = "docs/research/evidence/v38_owner_observations_public_20261101.json"
DEFAULT_ELIGIBILITY = "docs/research/evidence/v38_etf_eligibility_matrix_20261101.csv"
GOVERNANCE = {
    "NO_REAL_ORDERS": True,
    "REAL_CAPITAL_AUTHORITY_USD": "0.00",
    "D5_REAL_ADMISSION": "NOT_ADMITTED",
    "LANE_A_B": "UNISSUED",
    "HYP_003": "TERMINALLY_FALSIFIED",
    "EXECUTION_AUTHORITY_FROM_EVIDENCE": "NONE",
}
NEXT_EVIDENCE_RULES: Tuple[Tuple[str, str], ...] = (
    ("_FX_SPREAD", "OWNER: in-app FX quote with amount and timestamp, captured with an independent mid at the same minute."),
    ("INTERMEDIARY_FEE_USD", "OWNER or RESEARCH: bank/IBKR statement or receiving-bank terms showing intermediary and receiving deductions."),
    ("PASS_THROUGH_FEES", "RESEARCH: IBKR exchange, clearing and regulatory pass-through charges for small US ETF buys."),
    ("MIXED_ORDER_COMMISSION", "RESEARCH: IBKR pricing of mixed whole/fractional executions."),
    ("POST_PROMOTION_FEE", "RESEARCH: KBank K PLUS SWIFT fees after 2026-12-31."),
    ("PRICE_TIER_UNKNOWN", "SCENARIO: explicit hypothetical prices for every symbol."),
)


def pack_profiles(eligibility: Sequence[SecurityEligibility]) -> Tuple[BrokerProfile, ...]:
    profiles = list(load_candidate_profiles(eligibility=eligibility))
    at = next(i for i, p in enumerate(profiles) if p.broker_id == "IBKR")
    ibkr = profiles[at]
    variants = [replace(ibkr, display_name="IBKR Pro via K PLUS SWIFT SHAR")] + [
        replace(ibkr, broker_id=f"IBKR_{bearer}", display_name=f"IBKR Pro via K PLUS SWIFT {bearer}",
                funding_terms=kbank_kplus_swift_terms(bearer))
        for bearer in ("DEBT", "CRED")
    ]
    return tuple(profiles[:at] + variants + profiles[at + 1:])


def _plan(order_type: str, months: int) -> InvestmentPlan:
    return InvestmentPlan(
        monthly_savings_thb=PACK_MONTHLY_SAVINGS_THB,
        reference_thb_per_usd=PACK_REFERENCE_THB_PER_USD,
        portfolio_weights=PACK_WEIGHTS,
        batch_months=months,
        order_sequence=("VOO", "BND"),
        order_type=order_type,
        ref_prices_usd=PACK_PRICES_USD,
    )


def _strings(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _strings(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_strings(v) for v in value]
    return value


def _flag(value: Optional[bool]) -> str:
    return "UNKNOWN" if value is None else ("YES" if value else "NO")


def _eligibility_row(e: SecurityEligibility) -> Dict[str, Any]:
    return {
        "platform_id": e.platform_id, "symbol": e.symbol, "searchable": _flag(e.searchable),
        "fractional_eligible": _flag(e.fractional_eligible), "manual_order_eligible": _flag(e.manual_order_eligible),
        "dca_eligible": _flag(e.dca_eligible), "account_permission": e.account_permission,
        "evidence_status": e.evidence_status, "ui_capability_observed": list(e.ui_capability_observed),
    }


def _batching(results: Dict[str, ComparisonResult]) -> List[Dict[str, Any]]:
    rows = []
    for order_type in ("MANUAL", "DCA"):
        one = {a.broker_id: a for a in results[f"{order_type.lower()}_1m"].assessments}
        three = {a.broker_id: a for a in results[f"{order_type.lower()}_3m"].assessments}
        for bid, a1 in one.items():
            a3 = three[bid]
            if a1.investable_balance_usd is None or a3.investable_balance_usd is None or bid == "CASH":
                continue
            rows.append({
                "order_type": order_type, "broker_id": bid,
                "monthly_friction_thb_1m": a1.total_known_friction_thb.quantize(CENT),
                "monthly_friction_thb_3m": (a3.total_known_friction_thb / 3).quantize(CENT),
                "lower_bound": not (a1.numerically_complete and a3.numerically_complete),
            })
    return rows


def _coverage(profiles: Sequence[BrokerProfile], results: Dict[str, ComparisonResult], recon: Sequence[Reconciliation],
              observations: Sequence[OwnerObservation]) -> Dict[str, Dict[str, Any]]:
    coverage: Dict[str, Dict[str, Any]] = {}
    for platform in ("DIME", "WEBULL", "IBKR"):
        members = [p for p in profiles if p.platform_id == platform]
        ids = {p.broker_id for p in members}
        unknowns = sorted({u for r in results.values() for a in r.assessments if a.broker_id in ids for u in a.unknown_components})
        coverage[platform] = {
            "published_fees": list(dict.fromkeys(p.evidence_notes[0] for p in members if p.evidence_notes)),
            "observed": [f"{r.observation_id}: {r.status}" for r in recon if r.platform_id == platform],
            "fx": [f"{o.observation_id}: {o.target_amount_usd} USD for {o.payable_thb or o.source_amount_thb} THB at {o.displayed_rate_thb_per_usd} (indicative; spread UNKNOWN)"
                   for o in observations if o.platform_id == platform and o.kind == "FX_AMOUNT_PREVIEW"] or ["NO_OBSERVATION; spread UNKNOWN"],
            "eligibility": [_eligibility_row(e) for p in members[:1] for e in p.security_eligibility] or ["NO_MATRIX_ROWS"],
            "dca_profiles": sorted(p.broker_id for p in members if p.commission_policy.applicable_order_type == "DCA"),
            "funding": sorted({p.funding_terms.route_id if p.funding_terms else p.funding_channel for p in members}),
            "unknowns": unknowns,
        }
    return coverage


def _next_evidence(results: Dict[str, ComparisonResult]) -> List[str]:
    assessments = [a for r in results.values() for a in r.assessments]
    unknowns = {u for a in assessments for u in a.unknown_components}
    items = [text for key, text in NEXT_EVIDENCE_RULES if any(key in u for u in unknowns)]
    if any(a.eligibility_status == "ACCOUNT_SPECIFIC_UNVERIFIED" for a in assessments):
        items.append("OWNER: in-app per-symbol eligibility (searchable, fractional, manual/DCA) for VOO and BND on each platform considered.")
    if any(a.decision_status == "TERMS_CONFLICTING" for a in assessments):
        items.append("RESEARCH: Webull DCA contractual commission and effective dates (0% advertised vs 0.10% guide).")
    items.append("OWNER: investment horizon, emergency liquidity and risk tolerance; ACASH does not infer a risk profile.")
    return items


def build_pack(observations: Sequence[OwnerObservation], eligibility: Sequence[SecurityEligibility]) -> Dict[str, Any]:
    profiles = pack_profiles(eligibility)
    results = {f"{ot.lower()}_{m}m": compare_investment_plans(profiles, _plan(ot, m), PACK_AS_OF) for ot, m in PACK_SCENARIOS}
    recon = [reconcile(o, profiles) for o in observations]
    matrix_digest = CanonicalConfigSerializer.compute_sha256(_plain(_strings([asdict(e) for e in eligibility])))
    hashes = {
        "fee_snapshot_sha256": FEE_SNAPSHOT_SHA256,
        "owner_evidence_digest": evidence_digest(observations),
        "eligibility_matrix_digest": matrix_digest,
        "scenario_input_hashes": {k: r.input_hash for k, r in sorted(results.items())},
    }
    pack: Dict[str, Any] = {
        "pack_version": PACK_VERSION,
        "as_of": PACK_AS_OF.isoformat(),
        "fee_snapshot_version": FEE_SNAPSHOT_VERSION,
        "sizing_policy": SIZING_POLICY,
        "hypothetical_inputs": {
            "monthly_savings_thb": str(PACK_MONTHLY_SAVINGS_THB),
            "reference_thb_per_usd": str(PACK_REFERENCE_THB_PER_USD),
            "reference_kind": "HYPOTHETICAL_INPUT (illustrative; not a market mid)",
            "prices_usd": {k: str(v) for k, v in sorted(PACK_PRICES_USD.items())},
            "weights": {k: str(v) for k, v in sorted(PACK_WEIGHTS.items())},
            "fx_spread": "UNKNOWN (not assumed)",
        },
        "governance": GOVERNANCE,
        "fx_comparability": fx_comparability(observations),
        "reconciliation": [_strings(asdict(r)) for r in recon],
        "coverage": _strings(_coverage(profiles, results, recon, observations)),
        "batching": _strings(_batching(results)),
        "scenarios": {k: comparison_to_dict(r) for k, r in sorted(results.items())},
        "next_evidence": _next_evidence(results),
        "hashes": hashes,
    }
    pack["pack_sha256"] = CanonicalConfigSerializer.compute_sha256(_plain(pack))
    return pack


def _row(a: Dict[str, Any]) -> str:
    usd = a["investable_balance_usd"] or "-"
    return (f"| {a['display_name']} | {usd} | {a['cost_status']} | {a['eligibility_status']} | {a['decision_status']} | "
            f"{', '.join(a['unknown_components']) or '-'} |")


def format_pack_markdown(pack: Dict[str, Any]) -> str:
    hyp = pack["hypothetical_inputs"]
    lines = [
        "# ACASH Investor Decision Pack (illustrative, not advice)",
        "",
        f"- As of {pack['as_of']}; fee snapshot {pack['fee_snapshot_version']} `{pack['hashes']['fee_snapshot_sha256']}`; pack `{pack['pack_sha256']}`",
        f"- Governance: NO_REAL_ORDERS=true; REAL_CAPITAL_AUTHORITY=USD 0.00; evidence grants no execution authority.",
        "",
        "## 1. Savings",
        f"THB {hyp['monthly_savings_thb']} per month; batches of 1 and 3 months; VOO 60% / BND 40% is an illustrative "
        "allocation, not a recommendation. CASH / NO TRADE is the zero-friction, zero-exposure baseline.",
        "",
        "## 2. USD that might be obtained (one month)",
        f"Hypothetical reference {hyp['reference_thb_per_usd']} THB/USD; FX spread UNKNOWN, so USD is an upper bound.",
        "",
    ]
    for key in ("manual_1m", "dca_1m"):
        lines += [f"### `{key}`", "", "| Route | USD investable (upper bound if FX unknown) | Cost evidence | Eligibility | Decision | Unknown |",
                  "| :--- | ---: | :---: | :---: | :---: | :--- |"]
        lines += [_row(a) for a in pack["scenarios"][key]["assessments"]]
        lines.append("")
    lines += ["## 3-5. Documented, observed and unknown costs", "", "Published terms per platform:", ""]
    for platform, cov in pack["coverage"].items():
        lines.append(f"- **{platform}**: " + " / ".join(cov["published_fees"]))
        lines.append(f"  - FX: {'; '.join(cov['fx'])}")
        lines.append(f"  - Funding: {', '.join(cov['funding'])}; unknowns: {', '.join(cov['unknowns']) or '-'}")
    lines += ["", f"Observed previews (FX comparability: `{pack['fx_comparability']}`):", "",
              "| Observation | Status | Checks | Missing |", "| :--- | :--- | :--- | :--- |"]
    for r in pack["reconciliation"]:
        checks = "; ".join(
            f"{c['item']} {c['verdict']}"
            + (f" (residual {Decimal(c['residual']).quantize(Decimal('0.000001'))})" if c["residual"] is not None else "")
            for c in r["checks"]
        ) or "-"
        lines.append(f"| {r['observation_id']} | {r['status']} | {checks} | {', '.join(r['missing_components'])} |")
    scenario_keys = sorted(pack["scenarios"])
    lines += ["", "A rounding residual is not a broker fee; a rounded zero is not proof of zero; a preview is not an execution.", "",
              "## 6. Route status (no route is confirmed without account-level evidence)", "",
              "| Route | " + " | ".join(scenario_keys) + " |", "| :--- |" + " :---: |" * len(scenario_keys)]
    first = pack["scenarios"][scenario_keys[0]]["assessments"]
    for i, a in enumerate(first):
        lines.append(f"| {a['display_name']} | " + " | ".join(pack["scenarios"][k]["assessments"][i]["decision_status"] for k in scenario_keys) + " |")
    lines += ["", "| Platform | Symbol | Searchable | Fractional | Manual | DCA | Account permission | Evidence | UI observed |",
              "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |"]
    for cov in pack["coverage"].values():
        for e in cov["eligibility"]:
            if isinstance(e, dict):
                lines.append(f"| {e['platform_id']} | {e['symbol']} | {e['searchable']} | {e['fractional_eligible']} | {e['manual_order_eligible']} | "
                             f"{e['dca_eligible']} | {e['account_permission']} | {e['evidence_status']} | {', '.join(e['ui_capability_observed']) or '-'} |")
    lines += ["", "## 7. Monthly versus batched explicit friction", "",
              "| Order type | Route | THB/month (1m) | THB/month (3m batch) | Lower bound |", "| :--- | :--- | ---: | ---: | :---: |"]
    lines += [f"| {b['order_type']} | {b['broker_id']} | {b['monthly_friction_thb_1m']} | {b['monthly_friction_thb_3m']} | {'yes' if b['lower_bound'] else 'no'} |"
              for b in pack["batching"]]
    lines += ["", "## 8. Hypothetical assumptions", ""]
    lines += [f"- {k}: {v}" for k, v in hyp.items()]
    lines += ["", "## 9. Risks and disclosures", "", *DISCLOSURE_LINES, "",
              "## 10. Evidence needed next", ""]
    lines += [f"- {item}" for item in pack["next_evidence"]]
    lines += ["", "## Reproducibility", ""]
    lines += [f"- {k}: `{v}`" for k, v in pack["hashes"].items() if not isinstance(v, dict)]
    lines += [f"- scenario `{k}`: `{v}`" for k, v in pack["hashes"]["scenario_input_hashes"].items()]
    lines.append("")
    return "\n".join(lines)


def pack_outputs(observations_path: str = DEFAULT_OBSERVATIONS, eligibility_path: str = DEFAULT_ELIGIBILITY) -> Tuple[str, str]:
    pack = build_pack(load_observations(observations_path), load_security_eligibility(eligibility_path))
    return json.dumps(pack, indent=2, sort_keys=True) + "\n", format_pack_markdown(pack)


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Offline CLI; reads local files only and writes LF-terminated outputs."""
    parser = argparse.ArgumentParser(description="ACASH Investor Decision Pack (offline, illustrative)")
    parser.add_argument("--observations", default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--eligibility", default=DEFAULT_ELIGIBILITY)
    parser.add_argument("--output", default=None, help="Output prefix; writes .json and .md")
    args = parser.parse_args(argv)
    json_text, md_text = pack_outputs(args.observations, args.eligibility)
    if args.output:
        for suffix, text in ((".json", json_text), (".md", md_text)):
            with open(args.output + suffix, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
    else:
        print(md_text)


if __name__ == "__main__":
    main()
