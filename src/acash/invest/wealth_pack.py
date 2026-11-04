"""Unified Portfolio Intelligence pack V1 (read-only, offline, deterministic).

Sections: A total wealth, B long-term accounts, C quant research workspace,
D financial capacity, E decision status. Reuses the PPDS private observation
book, the capacity planner and the V38 cost engine. It never ranks brokers,
generates orders, moves money or grants authority.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import replace
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.invest.capacity_plan import (
    CONTRIBUTION_SCENARIOS_THB,
    POLICY_FAMILIES,
    POLICY_NOTE,
    CapacityInputs,
    assess_capacity,
    contribution_first_allocation,
    load_capacity,
)
from acash.ppds.private_observation import (
    AUTHORIZATION_RECORD,
    PortfolioBook,
    _repo_root,
    assert_private_location,
    assert_private_observation_authorized,
    book_summary,
    build_book,
    load_snapshot,
    odr_state,
    read_gated_json,
)
from acash.research.d6.broker_profiles import load_security_eligibility
from acash.research.d6.decision_pack import (
    DEFAULT_ELIGIBILITY,
    GOVERNANCE,
    PACK_AS_OF,
    _plan,
    pack_profiles,
)
from acash.research.d6.investor_decision import compare_investment_plans

PACK_VERSION = "UNIFIED_PORTFOLIO_INTELLIGENCE_V1"
V38_PACK_JSON = "docs/research/evidence/v38_investor_decision_pack_20261101.json"
PUBLIC_SNAPSHOT = "docs/research/evidence/upi_v1_synthetic_snapshot.json"
PUBLIC_CAPACITY = "docs/research/evidence/upi_v1_synthetic_capacity.json"
QUANT_WORKSPACE = {
    "status": "RESEARCH_ONLY_NOT_AUTHORIZED",
    "real_capital_authority_usd": "0.00",
    "new_strategies": "NONE_CREATED",
    "required_benchmarks": ["CASH", "BUY_AND_HOLD", "EQUAL_WEIGHT"],
    "required_validation": ["DSR", "CPCV", "PBO"],
    "webull_openapi": "INTERFACE_NOT_DOCUMENTED: EXTERNAL_RESEARCH_REQUIRED (no credentials, no endpoints called)",
    "paper_or_live_connectivity": "DISABLED",
}


def _v38_scenarios(amounts: Sequence[Decimal]) -> Dict[str, Any]:
    profiles = pack_profiles(load_security_eligibility(DEFAULT_ELIGIBILITY))
    out: Dict[str, Any] = {}
    for amount in amounts:
        plan = replace(_plan("MANUAL", 1), monthly_savings_thb=amount)
        result = compare_investment_plans(profiles, plan, PACK_AS_OF)
        out[str(amount)] = {
            "input_hash": result.input_hash,
            "rows": [{"route": a.display_name,
                      "investable_usd": None if a.investable_balance_usd is None else str(a.investable_balance_usd),
                      "known_friction_thb": str(a.total_known_friction_thb), "cost_status": a.cost_status,
                      "eligibility_status": a.eligibility_status, "decision_status": a.decision_status}
                     for a in result.assessments],
        }
    return out


def _v38_reference() -> Dict[str, str]:
    doc = json.loads(Path(V38_PACK_JSON).read_text(encoding="utf-8"))
    return {"path": V38_PACK_JSON, "pack_version": doc["pack_version"], "pack_sha256": doc["pack_sha256"]}


def observation_authority(data_class: str, schema: str) -> Dict[str, str]:
    """Observation authority for the pack, derived from ``odr_state``; never trading authority."""
    block = {"odr_record": AUTHORIZATION_RECORD.as_posix(), "snapshot_schema": schema, "trading_authority": "NONE",
             "capital_authority_usd": "0.00"}
    if data_class != "OWNER_PRIVATE_OBSERVATION":
        return {**block, "odr_state": "NOT_CONSULTED_SYNTHETIC_FIXTURE",
                "observation_authority": "NOT_REQUIRED_SYNTHETIC_FIXTURE"}
    state = odr_state(None, schema)
    if state != "RATIFIED":
        raise DataContractError(f"PRIVATE_OBSERVATION_NOT_AUTHORIZED: {AUTHORIZATION_RECORD.as_posix()} {state} for {schema}.")
    return {**block, "odr_state": state, "observation_authority": "OWNER_PRIVATE_READ_ONLY_OBSERVATION"}


def _authority_reason(authority: Mapping[str, str]) -> str:
    if authority["odr_state"] == "NOT_CONSULTED_SYNTHETIC_FIXTURE":
        return "PRIVATE_OBSERVATION_AUTHORIZATION_NOT_REQUIRED: synthetic fixture; no trading or capital authority."
    return (f"OWNER_PRIVATE_OBSERVATION_AUTHORIZED: {authority['odr_record']} {authority['odr_state']} for "
            f"{authority['snapshot_schema']}; read-only observation, no trading or capital authority.")


def _decision(summary: Mapping[str, Any], capacity: Mapping[str, Any], authority: Mapping[str, str],
              economic_complete: bool = False) -> Dict[str, Any]:
    reasons: List[str] = []
    if summary["performance_status"] != "PERFORMANCE_QUALIFIED":
        reasons.append("PERFORMANCE_NOT_ESTABLISHED: snapshot only, no cash-flow history.")
    if not summary["analytics"]:
        reasons.append("EVIDENCE_ONLY_REPORT: no cash or quantity line carries value; allocation, concentration, "
                       "P&L and stress are not computed.")
    else:
        analytics = summary["analytics"][next(iter(summary["analytics"]))]
        if analytics["concentration"]["look_through_status"] != "LOOK_THROUGH_QUALIFIED":
            reasons.append("OVERLAP_NOT_ESTABLISHED: no dated constituent weights.")
        if analytics["unrealized_pnl"]["status"] != "OBSERVED_COST_BASIS":
            reasons.append(f"COST_BASIS_INCOMPLETE: {analytics['unrealized_pnl']['status']}; unrealized P&L only for the known-cost subset.")
        if "UNKNOWN" in analytics["allocation_by_classification"] and not economic_complete:
            reasons.append("UNKNOWN_CLASSIFICATION_PRESENT: evidence-backed classification missing for some holdings.")
    if capacity["reserve"]["status"] != "RESERVE_TARGET_MET":
        reasons.append("RESERVE_SHORTFALL: rebuild emergency reserve before new risk.")
    if summary["valuation_stale"]:
        reasons.append("STALE_VALUATION: snapshot older than the freshness window.")
    evidence = summary.get("evidence")
    if evidence:
        block = evidence[next(iter(evidence))]
        residual = block["valuation_basis"].get("unreconciled_broker_difference", "0.00")
        if residual != "0.00":
            reasons.append(
                "BROKER_TOTAL_RECONCILIATION_DIFFERENCE: broker total exceeds identified lines by "
                f"{residual} THB. Classified {block['valuation_basis'].get('residual_classification')}: it is a "
                "reconciliation difference, not unidentified investable assets, and it is excluded from "
                "allocation, NAV and concentration.")
        unverified_ids = sorted(s["security_id"] for s in block["security_identity"]
                                if s["identity_status"] == "SECURITY_IDENTITY_UNVERIFIED")
        if unverified_ids:
            reasons.append("SECURITY_IDENTITY_UNVERIFIED: " + ", ".join(unverified_ids)
                           + " still lack an owner-confirmed identifier; venue-unverified instruments are "
                             "reported separately and are not merged across accounts.")
        if any(not isinstance(a["account_total"], dict) or a["account_total"]["status"] not in
               ("RECONCILED", "CONSISTENT_WITH_DISPLAY_ROUNDING") for a in block["accounts"]):
            reasons.append("ACCOUNT_TOTALS_NOT_FULLY_RECONCILED: see evidence.accounts.")
        reasons.append("MARKET_SESSION_NOT_VERIFIED: the pack applies no exchange calendar; preflight checks XNYS "
                       "price times against the 2026-2028 NYSE fixture only.")
    reasons.append("V38_ROUTE_EVIDENCE_INCOMPLETE: FX spread and per-symbol eligibility remain owner-evidence items.")
    reasons.append(_authority_reason(authority))
    return {"conclusion": "NO_ACTION_PENDING_EVIDENCE", "reasons": reasons, "orders_generated": 0}


def build_wealth_pack(book: PortfolioBook, capacity_inputs: CapacityInputs,
                      target_weights: Optional[Mapping[str, Decimal]] = None,
                      report_date: Optional[date] = None,
                      economic_classes: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    if capacity_inputs.data_class != book.snapshot.data_class:
        raise DataContractError("PACK_DATA_CLASS_MISMATCH: snapshot and capacity must share a data class.")
    authority = observation_authority(book.snapshot.data_class, book.snapshot.schema)
    summary = book_summary(book, report_date, economic_classes)
    held_ids = {p.security_id for a in book.snapshot.accounts for p in a.positions}
    economic_complete = (economic_classes is not None and bool(held_ids)
                         and all(economic_classes.get(sid, 'UNKNOWN') != 'UNKNOWN' for sid in held_ids))
    capacity = assess_capacity(capacity_inputs)
    reporting = book.snapshot.reporting_currency
    evidence_only = not summary["analytics"]
    if evidence_only:
        allocation = summary["evidence"][reporting]["allocation_by_sub_portfolio_best_evidence"]
    else:
        allocation = summary["analytics"][reporting]["allocation_by_sub_portfolio"]
    long_term = {k: v for k, v in allocation.items()
                 if any(a.role == "LONG_TERM" and k.startswith(f"{a.account_ref}/") for a in book.snapshot.accounts)}
    contribution_view: Any = None
    if target_weights is not None and evidence_only:
        contribution_view = "NOT_EVALUATED_EVIDENCE_ONLY_REPORT"
    elif target_weights is not None:
        analytics = summary["analytics"][reporting]
        current = {k: Decimal(v["value"]) for k, v in analytics["allocation_by_classification"].items()}
        contribution_view = contribution_first_allocation(current, target_weights, capacity_inputs.planned_contribution_thb)
    pack: Dict[str, Any] = {
        "pack_version": PACK_VERSION,
        "data_class": book.snapshot.data_class,
        "governance": {**GOVERNANCE, **summary["governance"]},
        "observation_authority": authority,
        "A_total_wealth": summary,
        "B_long_term": {"sub_portfolios": long_term, "policy_families": POLICY_FAMILIES, "policy_note": POLICY_NOTE,
                        "contribution_first": contribution_view or "NOT_EVALUATED_NO_TARGET_WEIGHTS"},
        "C_quant_workspace": {**QUANT_WORKSPACE, "budget": capacity["quant_budget"],
                              "quant_accounts": [a.account_ref for a in book.snapshot.accounts if a.role == "QUANT_RESEARCH"]},
        "D_financial_capacity": {**capacity, "v38_route_costs_per_contribution": _v38_scenarios(CONTRIBUTION_SCENARIOS_THB)},
        "E_decision": {**_decision(summary, capacity, authority, economic_complete),
                       "v38_decision_pack": _v38_reference()},
    }
    pack["pack_sha256"] = CanonicalConfigSerializer.compute_sha256(json.loads(json.dumps(pack, sort_keys=True)))
    return pack


def _table(rows: Mapping[str, Mapping[str, str]]) -> List[str]:
    lines = ["| Bucket | Value | Weight |", "|---|---:|---:|"]
    lines += [f"| {k} | {v['value']} | {v['weight']} |" for k, v in rows.items()]
    return lines


def _evidence_markdown(ev: Mapping[str, Any]) -> List[str]:
    vb, cov, conc = ev["valuation_basis"], ev["coverage"], ev["concentration_best_evidence"]
    out = ["", f"### Evidence and observed totals ({ev['report_currency']})",
           f"- Computed (PPDS quantity x price + settled cash): {vb['computed_nav_ppds']}; observed value-only positions: "
           f"{vb['observed_position_value']}; UNCLASSIFIED_HOLDINGS_VALUE: {vb['unclassified_holdings_value']}; "
           f"total best evidence: **{vb['total_best_evidence']}**",
           f"- Coverage: known value {cov['known_value_coverage']}, position level {cov['position_level_coverage']}, "
           f"cash observed accounts {cov['cash_observed_accounts']}, totals reconciled {cov['account_total_reconciliation_coverage']}, "
           f"cost basis {cov['cost_basis_coverage']}, history {cov['historical_transaction_coverage']}",
           f"- Concentration ({conc['status']}): top1 {conc['top1_weight']}, unclassified share {conc['unclassified_share']}, "
           f"HHI {conc['hhi_identified_securities']}; market session {ev['market_session_status']}",
           "| Account | Evidence level | Account total | Difference | Flags |", "|---|---|---|---:|---|"]
    for acct in ev["accounts"]:
        total = acct["account_total"]
        status, diff = (total["status"], total["difference"]) if isinstance(total, dict) else (total, "")
        out.append(f"| {acct['account_ref']} | {acct['evidence_level']} | {status} | {diff} | {', '.join(acct['flags']) or '-'} |")
    out += [f"- Identity {s['security_id']}: {s['identity_status']}" for s in ev["security_identity"]]
    return out


def format_wealth_markdown(pack: Mapping[str, Any]) -> str:
    a, d, e = pack["A_total_wealth"], pack["D_financial_capacity"], pack["E_decision"]
    out = [f"# ACASH Unified Portfolio Intelligence — {pack['data_class']}", "",
           f"Snapshot `{a['snapshot_id']}` valued {a['valuation_date']} (observed {a['time_alignment']['observed_at']}) · support state **{a['support_state']}** · "
           f"performance **{a['performance_status']}** · pack `{pack['pack_sha256'][:16]}`", "",
           "Read-only decision support. No orders, transfers, recurring plans or authority. Stress figures are illustrative, not forecasts.", "",
           "## A. Total wealth"]
    if not a["analytics"]:
        rep = next(iter(a["evidence"]))
        out += [f"**{a['report_type']}**: computed analytics are not produced. Not supported: {', '.join(a['unsupported_analyses'])}."]
        out += _evidence_markdown(a["evidence"][rep])
        return "\n".join(out + _sections_b_to_e(pack, d, e))
    rep = next(iter(a["analytics"]))
    an = a["analytics"][rep]
    for ccy, block in a["analytics"].items():
        out.append(f"- NAV {ccy}: **{block['nav']}** (securities {block['securities_value']}, settled cash {block['settled_cash']}; "
                   f"accrued interest excluded {block['accrued_interest_excluded_from_nav']})")
    out += ["", "### By classification", *_table(an["allocation_by_classification"]),
            "", "### By broker", *_table(an["allocation_by_broker"]),
            "", "### By currency", *_table(an["allocation_by_currency"]),
            "", f"Concentration ({an['concentration']['basis']}; {an['concentration']['look_through_status']}): "
            f"top1 {an['concentration']['top1_weight']}, top5 {an['concentration']['top5_weight']}, "
            f"HHI {an['concentration']['hhi_securities_of_nav']}",
            f"Unrealized P&L ({an['unrealized_pnl']['status']}, cost-basis coverage {an['unrealized_pnl']['cost_basis_value_coverage']}): "
            f"{an['unrealized_pnl']['unrealized_pnl_security_currency_known_cost_subset']} — {'; '.join(an['unrealized_pnl']['limitations'])}",
            "", "### Illustrative stress (not forecasts)", "| Scenario | NAV delta | Share |", "|---|---:|---:|"]
    out += [f"| {s['scenario']} | {s['nav_delta']} | {s['nav_delta_share']} |" for s in an["stress_illustrative"]["scenarios"]]
    out += [f"Not evaluated: {an['stress_illustrative']['not_evaluated']}", "",
            "### Reconciliation (observed vs quantity x price)"]
    out += [f"- {r['account_ref']} {r['security_id']} {r['sub_portfolio']}: {r['verdict']}" for r in a["reconciliation"]]
    if "evidence" in a:
        out += _evidence_markdown(a["evidence"][rep])
    return "\n".join(out + _sections_b_to_e(pack, d, e))


def _sections_b_to_e(pack: Mapping[str, Any], d: Mapping[str, Any], e: Mapping[str, Any]) -> List[str]:
    out = ["", "## B. Long-term accounts", *_table(pack["B_long_term"]["sub_portfolios"]), "",
           pack["B_long_term"]["policy_note"]]
    out += [f"- {k}: {v['description']} e.g. {', '.join(v['example_instruments']) or '-'}"
            for k, v in pack["B_long_term"]["policy_families"].items()]
    cf = pack["B_long_term"]["contribution_first"]
    out.append(f"- Contribution-first view: {cf if isinstance(cf, str) else cf['allocation']}")
    c = pack["C_quant_workspace"]
    out += ["", "## C. Quant research workspace", f"- Status: {c['status']}; budget {c['budget']['budget_thb']} THB "
            f"({c['budget']['label']}, {c['budget']['authorization']}, reserve funding {c['budget']['reserve_funding']})",
            f"- Benchmarks required: {', '.join(c['required_benchmarks'])}; validation {', '.join(c['required_validation'])}",
            f"- Webull OpenAPI: {c['webull_openapi']}", "", "## D. Financial capacity",
            f"- Monthly surplus {d['monthly_surplus_thb']} THB; reserve {d['reserve']['effective_thb']} / target "
            f"{d['reserve']['target_thb']} ({d['reserve']['coverage_months']} months, {d['reserve']['status']})",
            "| Contribution | Residual | Months to reserve target | Status |", "|---:|---:|---:|---|"]
    out += [f"| {r['monthly_contribution_thb']} | {r['residual_after_contribution_thb']} | "
            f"{r['months_to_reserve_target_from_residual']} | {r['status']} |" for r in d["scenarios"]]
    for amount, block in d["v38_route_costs_per_contribution"].items():
        out += ["", f"V38 route costs for {amount} THB (MANUAL, 1 month; unranked):", "| Route | Investable USD | Cost status | Decision |",
                "|---|---:|---|---|"]
        out += [f"| {r['route']} | {r['investable_usd'] or '-'} | {r['cost_status']} | {r['decision_status']} |" for r in block["rows"]]
    out += ["", "## E. Decision status", f"**{e['conclusion']}** (orders generated: {e['orders_generated']})"]
    out += [f"- {r}" for r in e["reasons"]]
    out += [f"- V38 pack reference `{e['v38_decision_pack']['pack_sha256'][:16]}` ({e['v38_decision_pack']['path']})", "",
            "## Governance", *[f"- {k}: {v}" for k, v in pack["governance"].items()], ""]
    return out


def write_pack(pack: Mapping[str, Any], output_dir: Path) -> List[Path]:
    schema = pack["A_total_wealth"]["schema"]
    expected = ("OWNER_PRIVATE_READ_ONLY_OBSERVATION" if pack["data_class"] == "OWNER_PRIVATE_OBSERVATION"
                else "NOT_REQUIRED_SYNTHETIC_FIXTURE")
    if pack["observation_authority"]["observation_authority"] != expected:
        raise DataContractError("PACK_AUTHORITY_INCONSISTENT: observation_authority does not match data_class.")
    if pack["data_class"] == "OWNER_PRIVATE_OBSERVATION":
        assert_private_observation_authorized(pack["data_class"], schema)
        assert_private_location(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "upi_v1_pack"
    json_path, md_path = output_dir / f"{stem}.json", output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(pack, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(format_wealth_markdown(pack), encoding="utf-8", newline="\n")
    written = [json_path, md_path]
    if pack["data_class"] == "OWNER_PRIVATE_OBSERVATION":
        manifest = {"pack_version": PACK_VERSION, "pack_sha256": pack["pack_sha256"],
                    "snapshot_schema": schema,
                    "observation_authority": pack["observation_authority"],
                    "odr_state_at_write": odr_state(None, schema),
                    "snapshot_content_sha256": pack["A_total_wealth"]["snapshot_content_sha256"],
                    "code_version": _code_version(), "files": [p.name for p in written],
                    "note": "Private run record. Digests identify private inputs; do not publish."}
        manifest_path = output_dir / "upi_run_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        written.append(manifest_path)
    return written


def _code_version() -> Dict[str, str]:
    try:
        root = _repo_root()
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return {"commit": "NOT_AVAILABLE", "working_tree": "NOT_AVAILABLE"}
    return {"commit": sha.stdout.strip(), "working_tree": "DIRTY" if dirty.stdout.strip() else "CLEAN"}


def _weights(raw: Optional[str], path: Optional[str] = None) -> Optional[Dict[str, Decimal]]:
    if raw is not None and path is not None:
        raise DataContractError("TARGET_WEIGHTS_AMBIGUOUS: use --target-weights or --target-weights-file, not both.")
    if raw is None and path is None:
        return None
    try:
        doc = read_gated_json(Path(path), "TARGET_WEIGHTS") if path is not None else json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise DataContractError("TARGET_WEIGHTS_MALFORMED_JSON.") from exc
    if not isinstance(doc, dict) or not all(isinstance(v, str) for v in doc.values()):
        raise DataContractError("TARGET_WEIGHTS_MUST_BE_STRING_MAPPING.")
    try:
        return {str(k): Decimal(v) for k, v in doc.items()}
    except InvalidOperation as exc:
        raise DataContractError("TARGET_WEIGHTS_MALFORMED_DECIMAL.") from exc


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="ACASH unified portfolio intelligence pack (read-only).")
    parser.add_argument("--snapshot", default=PUBLIC_SNAPSHOT)
    parser.add_argument("--capacity", default=PUBLIC_CAPACITY)
    parser.add_argument("--target-weights", default=None, help='JSON mapping, e.g. {"CORE_DIVERSIFIED": "0.8", "CASH": "0.2"}')
    parser.add_argument("--target-weights-file", default=None, help="Path to the same JSON mapping (avoids shell quoting).")
    parser.add_argument("--report-date", default=None, help="ISO date used for the staleness check.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    book = build_book(load_snapshot(Path(args.snapshot)))
    capacity = load_capacity(Path(args.capacity))
    report_date = date.fromisoformat(args.report_date) if args.report_date else None
    pack = build_wealth_pack(book, capacity, _weights(args.target_weights, args.target_weights_file), report_date)
    for path in write_pack(pack, Path(args.output)):
        print(path)


if __name__ == "__main__":
    main()
