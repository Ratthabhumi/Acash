"""Read-only dashboard view model projected from a UPI wealth pack (``ACASH_UPI_VIEW_V1``).

Python remains the calculation authority: every amount and weight is copied verbatim as a
decimal string from the pack; nothing is recomputed here or in the dashboard. Missing data
stays explicit (``None`` plus a status), never zero. Owner-private views are written only to
authorized private locations; synthetic views may be exported into the dashboard sources.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.invest.wealth_pack import PACK_VERSION
from acash.ppds.private_observation import (
    SCHEMA_V1_2,
    assert_private_location,
    assert_private_observation_authorized,
    read_gated_json,
)

VIEW_SCHEMA = "ACASH_UPI_VIEW_V1"
DATA_MODES = {"SYNTHETIC_PUBLIC_FIXTURE": "SYNTHETIC_DEMO", "OWNER_PRIVATE_OBSERVATION": "OWNER_PRIVATE_READ_ONLY"}
SYNTHETIC_PACK = "docs/research/evidence/upi_v1_2_synthetic_pack/upi_v1_pack.json"
SYNTHETIC_EVIDENCE_ONLY_PACK = "docs/research/evidence/upi_v1_2_synthetic_totals_only_pack/upi_v1_pack.json"
DASHBOARD_FIXTURES = {
    SYNTHETIC_PACK: "dashboard/src/fixtures/upi_synthetic_view.json",
    SYNTHETIC_EVIDENCE_ONLY_PACK: "dashboard/src/fixtures/upi_synthetic_evidence_only_view.json",
}


def _account_total(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {"status": str(raw)}
    keys = ("status", "observed_total", "known_components", "difference", "tolerance", "currency", "fx_source_may_differ")
    return {k: raw.get(k) for k in keys}


def build_view(pack: Mapping[str, Any]) -> Dict[str, Any]:
    if pack.get("pack_version") != PACK_VERSION:
        raise DataContractError("VIEW_PACK_VERSION_UNSUPPORTED.")
    data_class = pack.get("data_class")
    if data_class not in DATA_MODES:
        raise DataContractError("VIEW_DATA_CLASS_INVALID.")
    a = pack["A_total_wealth"]
    if a.get("schema") != SCHEMA_V1_2 or "evidence" not in a:
        raise DataContractError("VIEW_SNAPSHOT_SCHEMA_UNSUPPORTED: the dashboard view requires a V1_2 evidence pack.")
    authority = pack["observation_authority"]
    expected = "OWNER_PRIVATE_READ_ONLY_OBSERVATION" if data_class == "OWNER_PRIVATE_OBSERVATION" else "NOT_REQUIRED_SYNTHETIC_FIXTURE"
    if authority.get("observation_authority") != expected:
        raise DataContractError("PACK_AUTHORITY_INCONSISTENT: observation_authority does not match data_class.")
    ccy = next(iter(a["evidence"]))
    ev, d, c, e = a["evidence"][ccy], pack["D_financial_capacity"], pack["C_quant_workspace"], pack["E_decision"]
    meta = {acct["account_ref"]: acct for acct in a["accounts"]}
    analytics = a["analytics"].get(ccy) if a["analytics"] else None
    positions_block = ev.get("positions") if isinstance(ev.get("positions"), dict) else {}
    position_rows = positions_block.get("rows") if isinstance(positions_block.get("rows"), list) else []
    accounts: List[Dict[str, Any]] = []
    for acct in ev["accounts"]:
        m = meta.get(acct["account_ref"], {})
        accounts.append({
            "account_ref": acct["account_ref"], "broker": m.get("broker"), "role": m.get("role"),
            "base_currency": m.get("base_currency"), "evidence_level": acct["evidence_level"],
            "computed_value": acct["computed_value"], "observed_position_value": acct["observed_position_value"],
            "unclassified_holdings_value": acct["unclassified_holdings_value"],
            "cash_lines_observed": acct["cash_lines_observed"], "account_total": _account_total(acct["account_total"]),
            "sub_portfolio_totals": acct["sub_portfolio_totals"], "flags": acct["flags"]})
    view: Dict[str, Any] = {
        "view_schema": VIEW_SCHEMA,
        "data_mode": DATA_MODES[data_class],
        "report_metadata": {
            "pack_version": pack["pack_version"], "pack_sha256": pack["pack_sha256"], "snapshot_id": a["snapshot_id"],
            "snapshot_schema": a["schema"], "report_type": a["report_type"], "report_currency": ccy,
            "valuation_date": a["valuation_date"], "observed_at": a["time_alignment"]["observed_at"],
            "observation_lag_days": a["time_alignment"]["observation_lag_days"],
            "valuation_age_days": a["valuation_age_days"], "valuation_stale": a["valuation_stale"],
            "stale_after_days": a["stale_after_days"], "support_state": a["support_state"],
            "unsupported_analyses": a.get("unsupported_analyses", [])},
        "portfolio_overview": {**ev["valuation_basis"], "computed_nav_is_total_best_evidence": False},
        "coverage": ev["coverage"],
        "accounts": accounts,
        "allocation": {
            "by_sub_portfolio_best_evidence": ev["allocation_by_sub_portfolio_best_evidence"],
            "currency_exposure_best_evidence": ev["currency_exposure_best_evidence"],
            "computed_by_classification": analytics["allocation_by_classification"] if analytics else None,
            "computed_status": "COMPUTED_SUBSET_PPDS" if analytics else "NOT_COMPUTED_EVIDENCE_ONLY_REPORT"},
        "concentration": ev["concentration_best_evidence"],
        "positions": {
            "schema": positions_block.get("schema", "ACASH_POSITION_ROWS_V1"),
            "status": "AVAILABLE" if position_rows else "NO_POSITION_ROWS",
            "weight_basis": positions_block.get("weight_basis"),
            "position_value_total": positions_block.get("position_value_total"),
            "qualification": positions_block.get("qualification"),
            "rows": position_rows,
        },
        "security_identity": ev["security_identity"],
        "financial_capacity": {
            "capacity_status": d["capacity_status"], "monthly_surplus_thb": d["monthly_surplus_thb"],
            "reserve": d["reserve"], "scenarios": d["scenarios"], "quant_budget": c["budget"]},
        "quant_workspace": {k: c[k] for k in ("status", "real_capital_authority_usd", "paper_or_live_connectivity",
                                               "required_benchmarks", "required_validation", "new_strategies")},
        "decision_status": {"conclusion": e["conclusion"], "reasons": e["reasons"], "orders_generated": e["orders_generated"]},
        "governance": {"observation_authority": authority, "flags": pack["governance"]},
        "data_quality": {
            "performance_status": a["performance_status"], "market_session_status": ev["market_session_status"],
            "reason_codes": [r.split(":")[0] for r in e["reasons"]]},
    }
    view["view_sha256"] = CanonicalConfigSerializer.compute_sha256(json.loads(json.dumps(view, sort_keys=True)))
    return view


def write_view(view: Mapping[str, Any], path: Path) -> Path:
    if view["data_mode"] == "OWNER_PRIVATE_READ_ONLY":
        assert_private_observation_authorized("OWNER_PRIVATE_OBSERVATION", view["report_metadata"]["snapshot_schema"])
        assert_private_location(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(view, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Project a UPI pack into the read-only dashboard view (ACASH_UPI_VIEW_V1).")
    parser.add_argument("--pack", default=None, help="Pack JSON; omit to regenerate the synthetic dashboard fixtures.")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    if args.pack is None:
        for pack_path, out in DASHBOARD_FIXTURES.items():
            print(write_view(build_view(read_gated_json(Path(pack_path), "UPI_PACK")), Path(out)))
        return
    if args.output is None:
        raise DataContractError("VIEW_OUTPUT_REQUIRED.")
    print(write_view(build_view(read_gated_json(Path(args.pack), "UPI_PACK")), Path(args.output)))


if __name__ == "__main__":
    main()
