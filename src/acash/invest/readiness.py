"""One read-only investment-readiness contract built from existing authority outputs.

Nothing is recomputed here: the module only classifies what the portfolio, warehouse, identity registry,
research report and tax evidence already say, and states what would have to be evidenced next. It never
produces an order, a target price or a claim of realized performance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from acash.invest import security_identity as si

SCHEMA = "ACASH_INVESTMENT_READINESS_V1"
READY = "QUALIFIED"
PARTIAL = "PARTIAL_COVERAGE"
BLOCKED = "BLOCKED"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
NOT_APPLICABLE = "NOT_APPLICABLE"


def _status(items: Sequence[str], ready: str = READY, partial: str = PARTIAL,
            blocked: str = BLOCKED) -> str:
    if ready in items:
        return READY
    if partial in items:
        return PARTIAL
    if blocked in items:
        return BLOCKED
    return INSUFFICIENT


def build_readiness(view: Optional[Mapping[str, Any]] = None,
                    health: Optional[Mapping[str, Any]] = None,
                    report: Optional[Mapping[str, Any]] = None,
                    tax: Optional[Mapping[str, Any]] = None,
                    registry: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
    meta = (view or {}).get("report_metadata") or {}
    overview = (view or {}).get("portfolio_overview") or {}
    positions = (view or {}).get("positions") or {}
    rows = positions.get("rows") or []
    coverage = ((report or {}).get("coverage") or {})
    cohorts = ((report or {}).get("cohort_summary") or [])
    identity_blocked = ((report or {}).get("identity") or {}).get("blocked") or {}
    health_coverage = (health or {}).get("coverage") or {}

    identity_reason = None
    if identity_blocked:
        identity_reason = "; ".join(f"{symbol}: {row.get('reason')}"
                                    for symbol, row in sorted(identity_blocked.items()))
    identity_status = BLOCKED if identity_blocked else (READY if registry else NOT_APPLICABLE)

    portfolio_health = {
        "status": READY if overview.get("total_best_evidence") else INSUFFICIENT,
        "total_best_evidence": overview.get("total_best_evidence"),
        "broker_displayed": None,
        "position_rows": len(rows),
        "reconciliation": ((view or {}).get("accounts") or [{}])[0].get("account_total", {}).get("status")
        if (view or {}).get("accounts") else None,
        "valuation_date": meta.get("valuation_date"),
        "observed_at": meta.get("observed_at"),
        "reasons": [] if overview.get("total_best_evidence") else ["no qualified portfolio value"],
    }

    long_term = {
        "status": PARTIAL,
        "monthly_surplus_thb": ((view or {}).get("financial_capacity") or {}).get("monthly_surplus_thb"),
        "reserve": ((view or {}).get("financial_capacity") or {}).get("reserve"),
        "scenarios": ((view or {}).get("financial_capacity") or {}).get("scenarios"),
        "reasons": ["contribution scenarios use evidenced capacity inputs; future returns are not predicted"],
    }

    historical = {
        "status": PARTIAL if cohorts else INSUFFICIENT,
        "cohorts": [{"cohort_id": c.get("cohort_id"), "status": c.get("status"),
                     "sessions": c.get("session_count"), "window": c.get("evaluation_window"),
                     "strategy": c.get("strategy_id"),
                     "evaluation_status": c.get("evaluation_status")}
                    for c in cohorts],
        "price_basis": "PRICE_RETURN_ONLY",
        "performance_basis": "HYPOTHETICAL_HISTORICAL_BASKET",
        "realized_performance": False,
        "reasons": ["current weights applied historically", "no transaction reconstruction",
                    "partial universe" if coverage.get("partial") else "coverage complete for the stored universe"],
    }

    tax_block = (tax or {}).get("readiness") or {}
    decision = {
        "status": PARTIAL if cohorts and not identity_blocked else BLOCKED if identity_blocked else INSUFFICIENT,
        "identity": {"status": identity_status, "blocked": sorted(identity_blocked), "reason": identity_reason},
        "warehouse": {"last_session": coverage.get("union_last"),
                      "covered": health_coverage.get("covered", coverage.get("covered")),
                      "partial": health_coverage.get("partial", coverage.get("partial")),
                      "missing": health_coverage.get("missing", coverage.get("missing")),
                      "storage_rights": (health or {}).get("storage_rights")},
        "fx": {"status": "REFERENCE_ONLY" if report and report.get("fx") else "NOT_EVALUATED"},
        "transactions": tax_block.get("trade_history", "MISSING"),
        "realized_performance": tax_block.get("historical_performance", "DATA_REQUIRED"),
        "lookthrough": "OVERLAP_NOT_ESTABLISHED",
        "execution_authority": "NONE",
        "next_evidence": _next_evidence(identity_blocked, tax_block, coverage),
    }

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "portfolio_health": portfolio_health,
        "long_term_planning": long_term,
        "historical_research": historical,
        "decision_readiness": decision,
        "labels": ["READ_ONLY", "NO_EXECUTION_AUTHORITY", "NOT_REALIZED_PERFORMANCE"],
        "note": ("A category is QUALIFIED only when its inputs are evidenced. Missing evidence is reported as "
                 "BLOCKED or INSUFFICIENT_EVIDENCE and never replaced by a fabricated value."),
    }


def _next_evidence(identity_blocked: Mapping[str, Any], tax_block: Mapping[str, Any],
                   coverage: Mapping[str, Any]) -> list[str]:
    steps: list[str] = []
    for symbol in sorted(identity_blocked):
        steps.append(f"{symbol}: confirm FIGI/CUSIP and the listing interval before using its history")
    if tax_block.get("trade_history", "MISSING") != READY:
        steps.append("transactions: complete the life-of-account trade and cash-flow journal")
    if tax_block.get("dividends_and_tax") not in (None, READY):
        steps.append("dividends: itemised gross and withholding evidence per distribution")
    if int(coverage.get("missing") or 0) > 0:
        steps.append("warehouse: repair the missing sessions before extending the research window")
    if not steps:
        steps.append("none: all currently evaluated inputs are qualified")
    return steps
