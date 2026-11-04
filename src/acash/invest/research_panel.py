"""Research-panel construction from qualified inputs (no provider access, no fabrication).

Two distinct eligibilities are kept apart on purpose:

* **valuation eligibility** — a holding has a qualified value from the authoritative position rows
  (quantity x price on the snapshot's valuation date). This is what a portfolio weight needs.
* **historical eligibility** — a holding has enough stored sessions to enter the return panel.

A symbol without a valuation weight is excluded and reported; it is never given a zero weight, because
a zero silently changes the portfolio that was evaluated. Sub-portfolio shares (for example a "17.21% of
Newwave" label) are broker-display metadata and are never used as global weights.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.invest import research_proposal as rp

MIN_SESSIONS = 200
# Exploratory cohort: NASA listed on 2026-03-30, so a 200-session floor would drop it permanently.
# The recent cohort uses a lower floor and is never compared with the established-history one.
RECENT_INCEPTION_MIN_SESSIONS = 120
COHORTS: Dict[str, Dict[str, Any]] = {
    "ESTABLISHED_HISTORY": {"min_sessions": MIN_SESSIONS, "evaluation_status": "BENCHMARK_ELIGIBLE",
                            "comparable": True},
    "RECENT_INCEPTION": {"min_sessions": RECENT_INCEPTION_MIN_SESSIONS,
                         "evaluation_status": "EXPLORATORY_SMALL_SAMPLE", "comparable": False},
}
WEIGHT_BASIS = "QUALIFIED_POSITION_VALUE_ON_VALUATION_DATE"


def qualified_weights(rows: Sequence[Mapping[str, Any]], symbols: Sequence[str],
                      currency: str = "USD") -> Dict[str, Decimal]:
    """Global weights from authoritative position rows, by local value in one pricing currency."""
    totals: Dict[str, Decimal] = {}
    for row in rows:
        symbol = str(row.get("security_id"))
        if symbol not in symbols or row.get("price_currency") != currency:
            continue
        value = row.get("value_local")
        if value is None:
            raise DataContractError(f"PANEL_WEIGHT_UNQUALIFIED: {symbol} has no qualified value.")
        totals[symbol] = totals.get(symbol, Decimal(0)) + Decimal(str(value))
    total = sum(totals.values(), Decimal(0))
    if total <= 0:
        raise DataContractError("PANEL_WEIGHT_TOTAL_INVALID: no qualified value in the panel currency.")
    return {symbol: value / total for symbol, value in totals.items()}


def weights_from_view(view_path: Path, symbols: Sequence[str],
                      currency: str = "USD") -> Dict[str, Decimal]:
    """Read the derived private view and keep only its authoritative position rows."""
    if not view_path.is_file():
        raise DataContractError("PANEL_VIEW_MISSING: regenerate the private view first.")
    view = json.loads(view_path.read_text(encoding="utf-8"))
    positions = view.get("positions") if isinstance(view.get("positions"), dict) else {}
    rows = positions.get("rows") if isinstance(positions.get("rows"), list) else []
    if not rows:
        raise DataContractError("PANEL_POSITIONS_MISSING: the view carries no position rows.")
    if view.get("report_metadata", {}).get("valuation_date") is None:
        raise DataContractError("PANEL_VALUATION_DATE_MISSING.")
    return qualified_weights(rows, symbols, currency)


def build_panel(closes: Mapping[str, Mapping[date, Decimal]], weights: Mapping[str, Decimal],
                symbols: Sequence[str], min_sessions: int = MIN_SESSIONS) -> Dict[str, Any]:
    """Aligned return panel from stored closes, with explicit reasons for every exclusion."""
    excluded: Dict[str, Any] = {}
    eligible: List[str] = []
    for symbol in symbols:
        series = closes.get(symbol) or {}
        if len(series) < min_sessions:
            excluded[symbol] = {"reason": "SESSION_COVERAGE_BELOW_MINIMUM", "sessions": len(series)}
        elif symbol not in weights:
            excluded[symbol] = {"reason": "NO_QUALIFIED_POSITION_VALUE", "sessions": len(series)}
        else:
            eligible.append(symbol)
    if not eligible:
        return {"status": rp.INSUFFICIENT, "eligible": [], "excluded": excluded,
                "missing_evidence": ["no instrument is both valued and historically covered"]}
    common = sorted(set.intersection(*(set(closes[s]) for s in eligible)))
    if len(common) < 2:
        return {"status": rp.INSUFFICIENT, "eligible": eligible, "excluded": excluded,
                "missing_evidence": ["fewer than two aligned sessions across the eligible universe"]}
    returns = {s: [(closes[s][common[i]] / closes[s][common[i - 1]]) - 1 for i in range(1, len(common))]
               for s in eligible}
    timestamps = [datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) for day in common[1:]]
    total = sum((weights[s] for s in eligible), Decimal(0))
    if total <= 0:
        raise DataContractError("PANEL_WEIGHT_TOTAL_INVALID: eligible weights sum to zero.")
    normalised = {s: weights[s] / total for s in eligible}
    inputs = rp.ProposalInputs(returns=returns, timestamps=timestamps, current_weights=normalised)
    return {"status": "PANEL_READY", "eligible": eligible, "excluded": excluded, "inputs": inputs,
            "aligned_sessions": len(common), "first": common[0].isoformat(), "last": common[-1].isoformat(),
            "weights": {s: format(w, "f") for s, w in normalised.items()},
            "weight_basis": WEIGHT_BASIS,
            "weights_renormalised_to_panel": total != 1}


def panel_inputs_from_warehouse(store: Any, symbols: Sequence[str], view_path: Path,
                                min_sessions: int = MIN_SESSIONS) -> Dict[str, Any]:
    """Convenience path used by the offline rebuild: stored partitions + the private view."""
    closes = {symbol: {day: bar.close for day, bar in store.read(symbol).items()} for symbol in symbols}
    return build_panel(closes, weights_from_view(view_path, symbols), symbols, min_sessions)


def instrument_metadata(closes: Mapping[str, Mapping[date, Decimal]], weights: Mapping[str, Decimal],
                        symbols: Sequence[str], cohort_id: str, min_sessions: int) -> List[Dict[str, Any]]:
    """Per-instrument coverage facts, including why an instrument is or is not in a cohort."""
    rows: List[Dict[str, Any]] = []
    for symbol in symbols:
        series = closes.get(symbol) or {}
        sessions = sorted(series)
        eligible = len(sessions) >= min_sessions and symbol in weights
        if len(sessions) < min_sessions:
            reason = "INCEPTION_LIMITED_HISTORY"
        elif symbol not in weights:
            reason = "NO_QUALIFIED_POSITION_VALUE"
        else:
            reason = "ELIGIBLE"
        rows.append({
            "security_id": symbol, "cohort_id": cohort_id if eligible else None,
            "observed_sessions": len(sessions),
            "first_tradable_date": sessions[0].isoformat() if sessions else None,
            "first_qualified_price_date": sessions[0].isoformat() if sessions else None,
            "coverage_start": sessions[0].isoformat() if sessions else None,
            "coverage_end": sessions[-1].isoformat() if sessions else None,
            "inception_limited_history": len(sessions) < MIN_SESSIONS,
            "research_eligibility_reason": reason,
            "excluded_capital_weight": None if eligible else format(weights.get(symbol, Decimal(0)), "f"),
            "qualification_state": "QUALIFIED" if eligible else "EXCLUDED",
        })
    return rows


def build_cohorts(closes: Mapping[str, Mapping[date, Decimal]], weights: Mapping[str, Decimal],
                  symbols: Sequence[str]) -> Dict[str, Any]:
    """Two independent cohorts over the same inputs; their scores are not comparable.

    ESTABLISHED_HISTORY keeps the original 200-session floor and the long benchmark window.
    RECENT_INCEPTION lowers the floor only for this cohort so a genuinely new listing (NASA,
    2026-03-30) can be studied over the window it actually has. No pre-inception price is ever used,
    and the smaller IS/OOS windows are reported with the result.
    """
    cohorts: List[Dict[str, Any]] = []
    for cohort_id, config in COHORTS.items():
        panel = build_panel(closes, weights, symbols, min_sessions=int(config["min_sessions"]))
        entry: Dict[str, Any] = {
            "cohort_id": cohort_id,
            "evaluation_status": config["evaluation_status"],
            "comparable_to_established": config["comparable"],
            "min_sessions": config["min_sessions"],
            "status": panel.get("status"),
            "excluded": panel.get("excluded", {}),
            "instruments": instrument_metadata(closes, weights, symbols, cohort_id, int(config["min_sessions"])),
        }
        if panel.get("status") == "PANEL_READY":
            inputs = panel.pop("inputs")
            proposal = rp.build_proposal(inputs)
            entry.update({
                "session_count": panel.get("aligned_sessions"),
                "evaluation_window": {"start": panel.get("first"), "end": panel.get("last")},
                "weights": panel.get("weights"),
                "weights_renormalised_to_panel": panel.get("weights_renormalised_to_panel"),
                "weight_basis": panel.get("weight_basis"),
                "proposal": proposal,
                "labels": real_vs_hypothetical(panel),
            })
            if cohort_id == "RECENT_INCEPTION":
                in_sample = (proposal.get("in_sample_period") or {}).get("periods") or 0
                out_sample = (proposal.get("out_of_sample_period") or {}).get("periods") or 0
                entry["sample_warning"] = (
                    f"Exploratory only: {in_sample} in-sample and {out_sample} out-of-sample periods from "
                    "the instruments' actual first qualified prices. Not comparable with the "
                    "established-history cohort, and never used to select thresholds.")
        else:
            entry["sample_warning"] = "Not evaluable: no instrument set clears this cohort's minimum history."
        cohorts.append(entry)
    return {
        "schema": "ACASH_RESEARCH_COHORTS_V1",
        "note": ("Cohorts are evaluated separately. A shorter window is not a better or worse score: it is a "
                 "different measurement, so cross-cohort ranking is not permitted."),
        "cohorts": cohorts,
    }


def real_vs_hypothetical(panel: Mapping[str, Any]) -> Dict[str, Any]:
    """The labels every consumer must carry; a panel is never realized performance."""
    return {
        "performance_basis": "HYPOTHETICAL_HISTORICAL_BASKET",
        "realized_performance": False,
        "transaction_reconstructed": False,
        "labels": ["HYPOTHETICAL_HISTORICAL_BASKET", "PRICE_RETURN_ONLY",
                   "CURRENT_WEIGHTS_APPLIED_HISTORICALLY", "NOT_TRANSACTION_RECONSTRUCTED",
                   "NOT_REALIZED_PORTFOLIO_PERFORMANCE",
                   "PARTIAL_UNIVERSE_RESEARCH" if panel.get("excluded") else "FULL_UNIVERSE_QUALIFIED",
                   "EXECUTION_AUTHORITY_NONE"],
        "weight_basis": panel.get("weight_basis"),
        "weights_renormalised_to_panel": panel.get("weights_renormalised_to_panel"),
    }
