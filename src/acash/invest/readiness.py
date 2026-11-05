"""One read-only investment-readiness contract built from existing authority outputs.

A category is qualified only when its own inputs are qualified. Presence of a number is not evidence
that the number is reconcilied, fresh, identity-verified or performance-grade, so each component is
gated separately and the overall decision status is never promoted to hide a blocked component.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.invest import security_identity as si

SCHEMA = "ACASH_INVESTMENT_READINESS_V1"
QUALIFIED = "QUALIFIED"
PARTIAL = "PARTIAL_COVERAGE"
BLOCKED = "BLOCKED"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
NOT_APPLICABLE = "NOT_APPLICABLE"
STALE = "STALE"

CRITICAL = ("valuation", "identity", "reconciliation", "transactions", "realized_performance")


def _component(status: str, basis: Optional[str] = None, detail: Optional[str] = None) -> Dict[str, Any]:
    return {"status": status, "basis": basis, "detail": detail}


def _reconciled(view: Mapping[str, Any]) -> bool:
    accounts = view.get("accounts") or []
    return bool(accounts) and all(
        isinstance(account.get("account_total"), dict)
        and account["account_total"].get("status") in ("RECONCILED", "CONSISTENT_WITH_DISPLAY_ROUNDING")
        for account in accounts)


def build_readiness(view: Optional[Mapping[str, Any]] = None,
                    health: Optional[Mapping[str, Any]] = None,
                    report: Optional[Mapping[str, Any]] = None,
                    tax: Optional[Mapping[str, Any]] = None,
                    registry: Optional[Sequence[Any]] = None,
                    journal_events: int = 0,
                    shadow_report: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    view = view or {}
    health = health or {}
    report = report or {}
    meta = view.get("report_metadata") or {}
    overview = view.get("portfolio_overview") or {}
    positions = view.get("positions") or {}
    rows = positions.get("rows") or []
    coverage = report.get("coverage") or {}
    cohorts = report.get("cohort_summary") or []
    identity_report = report.get("identity") or {}
    identity_blocked = identity_report.get("blocked") or {}
    tax_ready = (tax or {}).get("readiness") or {}
    capacity = view.get("financial_capacity") or {}

    total = overview.get("total_best_evidence")
    stale = bool(meta.get("valuation_stale"))
    reconciled = _reconciled(view)

    components: Dict[str, Dict[str, Any]] = {
        "valuation": _component(
            BLOCKED if not total else STALE if stale else QUALIFIED,
            basis="total_best_evidence", detail=f"{total} as of {meta.get('valuation_date')}"),
        "identity": _component(
            BLOCKED if identity_blocked else PARTIAL if registry else INSUFFICIENT,
            basis="security_identity_registry",
            detail="; ".join(sorted(identity_blocked)) or "registered identities; unregistered tickers are snapshot-only"),
        "position_coverage": _component(
            QUALIFIED if rows else INSUFFICIENT, basis="ACASH_POSITION_ROWS_V1", detail=f"{len(rows)} rows"),
        "reconciliation": _component(QUALIFIED if reconciled else PARTIAL, basis="account_total",
                                    detail="all accounts reconciled" if reconciled else "one or more accounts unreconciled"),
        "cash_and_reserve": _component(
            QUALIFIED if (capacity.get("reserve") or {}).get("status") in ("ESTABLISHED", "FUNDED") else PARTIAL,
            basis="capacity_inputs", detail=str((capacity.get("reserve") or {}).get("status"))),
        "transactions": _component(
            QUALIFIED if journal_events > 0 and tax_ready.get("trade_history") == QUALIFIED else
            PARTIAL if journal_events > 0 or tax_ready.get("trade_history") else INSUFFICIENT,
            basis="canonical transaction journal",
            detail=f"{journal_events} journal event(s); tax readiness {tax_ready.get('trade_history', 'MISSING')}"),
        "realized_performance": _component(
            QUALIFIED if tax_ready.get("historical_performance") == QUALIFIED else INSUFFICIENT,
            basis="flows + opening/closing valuations", detail=str(tax_ready.get("historical_performance", "DATA_REQUIRED"))),
        "fx": _component(
            QUALIFIED if (report.get("fx") or {}).get("status") == "AVAILABLE" else PARTIAL,
            basis="BOT reference FX", detail=str((report.get("fx") or {}).get("status"))),
        "calendar": _component(
            _calendar_status(health, coverage), basis="verified XNYS session fixture",
            detail=str(coverage.get("union_last"))),
        "corporate_actions": _component(INSUFFICIENT, basis="dividend/split evidence", detail="no itemised distribution evidence"),
        "etf_lookthrough": _component(BLOCKED, basis="dated issuer holdings", detail="OVERLAP_NOT_ESTABLISHED"),
        "fees": _component(INSUFFICIENT, basis="broker fee schedule", detail="no route-cost evidence"),
        "quant_validation": _component(
            _validation_status(shadow_report), basis="frozen protocol + forward journal",
            detail=str((shadow_report or {}).get("statistical_validation",
                                                 "STATISTICAL_VALIDATION_NOT_ESTABLISHED"))),
    }

    portfolio_health = _component(
        QUALIFIED if components["valuation"]["status"] == QUALIFIED and reconciled else
        BLOCKED if components["valuation"]["status"] == BLOCKED else PARTIAL,
        basis="valuation + reconciliation",
        detail=f"{total} {meta.get('report_currency', '')} as of {meta.get('valuation_date')}")
    portfolio_health.update({"total_best_evidence": total, "position_rows": len(rows),
                             "valuation_date": meta.get("valuation_date"),
                             "observed_at": meta.get("observed_at"),
                             "reconciliation": components["reconciliation"]["detail"]})

    long_term = _component(PARTIAL, basis="evidenced capacity inputs",
                           detail="scenarios use declared capacity; future returns are not predicted")
    long_term.update({"monthly_surplus_thb": capacity.get("monthly_surplus_thb"),
                      "reserve": capacity.get("reserve"), "scenarios": capacity.get("scenarios")})

    historical = _component(
        PARTIAL if cohorts else INSUFFICIENT, basis="PRICE_RETURN_ONLY / HYPOTHETICAL_HISTORICAL_BASKET",
        detail=f"{len(cohorts)} cohorts; current weights applied historically")
    historical.update({
        "cohorts": [{"cohort_id": c.get("cohort_id"), "status": c.get("status"),
                     "sessions": c.get("session_count"), "window": c.get("evaluation_window"),
                     "strategy": c.get("strategy_id"), "evaluation_status": c.get("evaluation_status")}
                    for c in cohorts],
        "realized_performance": False,
        "unsupported": ["transaction reconstruction", "dividend/total-return basis", "selection-bias-free universe"],
    })

    critical_statuses = [components[name]["status"] for name in CRITICAL]
    if BLOCKED in critical_statuses:
        decision_status = BLOCKED
    elif all(status == QUALIFIED for status in critical_statuses):
        decision_status = QUALIFIED
    elif any(status == INSUFFICIENT for status in critical_statuses):
        decision_status = PARTIAL if cohorts else INSUFFICIENT
    else:
        decision_status = PARTIAL
    decision = _component(decision_status, basis="critical gates",
                          detail="one or more critical inputs are not qualified")
    decision.update({
        "identity": {"status": components["identity"]["status"], "blocked": sorted(identity_blocked),
                     "detail": components["identity"]["detail"]},
        "warehouse": {"last_session": coverage.get("union_last"),
                      "covered": coverage.get("covered"), "partial": coverage.get("partial"),
                      "partial_inception_unverified": coverage.get("partial_inception_unverified"),
                      "missing": coverage.get("missing"),
                      "storage_rights": health.get("storage_rights")},
        "execution_authority": "NONE",
        "next_evidence": _next_evidence(identity_blocked, tax_ready, components),
    })

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "portfolio_health": portfolio_health,
        "long_term_planning": long_term,
        "historical_research": historical,
        "decision_readiness": decision,
        "components": components,
        "labels": ["READ_ONLY", "NO_EXECUTION_AUTHORITY", "NOT_REALIZED_PERFORMANCE"],
        "note": ("Each component is gated on its own evidence. A partial or unreconciled portfolio is never "
                 "presented as fully qualified, and missing evidence is never replaced by a value."),
    }


def _next_evidence(identity_blocked: Mapping[str, Any], tax_ready: Mapping[str, Any],
                   components: Mapping[str, Mapping[str, Any]]) -> List[str]:
    steps: List[str] = []
    for symbol in sorted(identity_blocked):
        steps.append(f"{symbol}: reconcile the owner position with its official CUSIP/ISIN before admitting history")
    if components["transactions"]["status"] != QUALIFIED:
        steps.append("transactions: complete the life-of-account trade and cash-flow journal")
    if components["realized_performance"]["status"] != QUALIFIED:
        steps.append("performance: provide opening and closing valuations plus every external cash flow")
    if components["corporate_actions"]["status"] != QUALIFIED:
        steps.append("corporate actions: itemised dividend, withholding and split evidence")
    if components["etf_lookthrough"]["status"] != QUALIFIED:
        steps.append("look-through: dated issuer holdings with permitted-use evidence")
    if components["fees"]["status"] != QUALIFIED:
        steps.append("fees: broker commission/FX spread evidence")
    if components["quant_validation"]["status"] != QUALIFIED:
        steps.append("validation: frozen trials and enough forward shadow observations")
    return steps or ["none: all evaluated inputs are qualified"]


def _calendar_status(health: Mapping[str, Any], coverage: Mapping[str, Any]) -> str:
    """The venue fixture must actually cover the last stored session."""
    last = coverage.get("union_last")
    if not last:
        return INSUFFICIENT
    try:
        from datetime import date as _date
        from acash.invest import market_calendar as mc
        calendar = mc.load_calendar()
        info = mc.session(calendar, _date.fromisoformat(str(last)))
    except Exception:
        return INSUFFICIENT
    return QUALIFIED if info["status"] in ("OPEN", "EARLY_CLOSE", "CLOSED_HOLIDAY", "CLOSED_WEEKEND") else INSUFFICIENT


def _validation_status(shadow_report: Optional[Mapping[str, Any]]) -> str:
    outcomes = int((shadow_report or {}).get("forward_observations") or 0)
    if outcomes == 0:
        return INSUFFICIENT
    if outcomes < 30:
        return PARTIAL
    return INSUFFICIENT  # canonical DSR/PBO still needs the full trial ledger
