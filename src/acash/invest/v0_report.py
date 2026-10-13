"""ACASH Invest V0 — offline read-only personal investment report (synthetic only).

Thin composition layer over existing, tested components; this module invents
no accounting, no valuation math, and no statistics:

- valuation ......... reused ``ppds.exposure.evaluate_portfolio_base_currency``
- invested-only lines reused ``ppds.exposure.position_exposure`` (single-currency only)
- reconciliation .... reused ``ppds.reconcile.reconcile_snapshot_ledger``
- read-only surface . reused ``ppds.surface.render_read_only_surface``
- hashing ........... canonical serializer + SHA-256 via the PPDS ledger

What this layer ADDS (and only this): NAV-inclusive allocation weights
(``position_exposure`` normalizes across invested positions and excludes
cash), cost-assumption disclosure with zero UNKNOWN-tolerance on totals,
per-section evidence classification, a missing-data/uncertainty section, an
explicit execution prohibition, and deterministic JSON/Markdown rendering.

Hard boundaries: no order submission, no broker credentials, no network, no
real account data, no expected returns, no Sharpe/VaR/drawdown/alpha/ranking,
no invented statistics, no silent zero-cost assumptions, no currency mixing
without an explicit qualified FX rate. Missing data yields BLOCKED sections,
never fabricated metrics.

Supported-input policy: LONG-ONLY. Negative position quantities and negative
cash lots are rejected fail-closed: V0 has no margin, derivatives, or
leverage accounting, and the personal mandate candidate (itself unratified)
is long-only. Short exposure would make invested-only gross exposure
positive while NAV weights go negative — ambiguous output V0 refuses to emit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.ppds.exposure import (
    FXRate,
    PriceQuote,
    evaluate_portfolio_base_currency,
    position_exposure,
)
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.reconcile import reconcile_snapshot_ledger
from acash.ppds.statement_ingest import AccountSnapshot
from acash.ppds.surface import render_read_only_surface

REPORT_SCHEMA_VERSION: int = 1

EVIDENCE_SYNTHETIC_DEMONSTRATION: str = "SYNTHETIC_DEMONSTRATION"
EVIDENCE_SOURCE_DOCUMENTED: str = "SOURCE_DOCUMENTED"
EVIDENCE_DATA_QUALIFIED: str = "DATA_QUALIFIED"
EVIDENCE_ECONOMICALLY_EVALUATED: str = "ECONOMICALLY_EVALUATED"
EVIDENCE_NOT_ESTABLISHED: str = "NOT_ESTABLISHED"

COST_BASIS_MODELLED: str = "MODELLED"
COST_BASIS_ACCOUNT_VERIFIED: str = "ACCOUNT_VERIFIED"
COST_BASIS_UNKNOWN: str = "UNKNOWN"

_FORBIDDEN_STATISTICS: Tuple[str, ...] = (
    "sharpe",
    "sortino",
    "var",
    "cvar",
    "expected_return",
    "drawdown",
    "max_drawdown",
    "alpha",
    "ranking",
    "rank_score",
    "confidence_interval",
    "win_rate",
    "hit_rate",
)


@dataclass(frozen=True)
class V0CostAssumption:
    """One disclosed cost line. Amount None means unquantified (never zero)."""

    name: str
    basis: str
    detail: str
    amount_base: Optional[Decimal] = None


def _require_money(value: Decimal, context: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise DataContractError(f"INVEST_V0_INVALID_MONEY: {context}.")
    return value


def _validate_costs(costs: Sequence[V0CostAssumption]) -> List[Dict[str, Any]]:
    validated: List[Dict[str, Any]] = []
    for cost in costs:
        if not cost.name or not cost.name.strip():
            raise DataContractError("INVEST_V0_COST_NAME_INVALID.")
        if cost.basis not in (
            COST_BASIS_MODELLED,
            COST_BASIS_ACCOUNT_VERIFIED,
            COST_BASIS_UNKNOWN,
        ):
            raise DataContractError(
                f"INVEST_V0_COST_BASIS_INVALID: {cost.basis!r}."
            )
        if cost.basis == COST_BASIS_ACCOUNT_VERIFIED:
            raise DataContractError(
                f"INVEST_V0_COST_UNVERIFIED_CLAIM: {cost.name!r} claims "
                "ACCOUNT_VERIFIED without an attestation this layer can "
                "check. V0 is restricted to MODELLED and UNKNOWN until a "
                "fee-provenance contract exists."
            )
        if cost.amount_base is not None:
            _require_money(cost.amount_base, f"cost {cost.name}")
            if cost.amount_base < Decimal("0"):
                raise DataContractError(
                    f"INVEST_V0_COST_NEGATIVE: ordinary fee {cost.name!r} "
                    "must be non-negative. Rebates/credits need distinct "
                    "semantics that do not exist here; they are not netted."
                )
        validated.append(
            {
                "name": cost.name,
                "basis": cost.basis,
                "detail": cost.detail,
                "amount_base": (
                    str(cost.amount_base) if cost.amount_base is not None else None
                ),
            }
        )
    return validated


def build_invest_v0_report(
    *,
    ledger: NormalizedPortfolioLedger,
    prices: Mapping[str, PriceQuote],
    fx_rates: Mapping[Tuple[str, str], FXRate],
    base_currency: str,
    as_of: date,
    statement: Optional[AccountSnapshot] = None,
    statement_source_id: str = "",
    ledger_source_id: str = "",
    costs: Sequence[V0CostAssumption] = (),
    evidence_notes: Sequence[str] = (),
) -> Dict[str, Any]:
    """Compose a deterministic read-only investment report (pure function).

    Never emits order controls, statistics, forecasts, or recommendations.
    Every section carries its own evidence classification; anything
    unproven is labelled, never zeroed or interpolated.
    """
    clean_base = str(base_currency or "").strip().upper()
    if len(clean_base) != 3 or not clean_base.isalpha():
        raise DataContractError(
            f"INVEST_V0_BASE_CURRENCY_INVALID: {base_currency!r}."
        )

    for position_lot in ledger.position_lots:
        if position_lot.quantity < Decimal("0"):
            raise DataContractError(
                f"INVEST_V0_SHORT_POSITION_UNSUPPORTED: {position_lot.symbol} "
                f"quantity {position_lot.quantity}. V0 is long-only; short exposure "
                "would make gross exposure positive while NAV weights go "
                "negative, which this report refuses to emit."
            )
    for cash_lot in ledger.cash_lots:
        if cash_lot.amount < Decimal("0"):
            raise DataContractError(
                f"INVEST_V0_NEGATIVE_CASH_UNSUPPORTED: {cash_lot.currency} "
                f"amount {cash_lot.amount}. V0 has no overdraft/margin accounting."
            )

    valuation = evaluate_portfolio_base_currency(
        ledger, clean_base, as_of, prices, fx_rates
    )
    nav = valuation.total_portfolio_nav_base
    if nav <= Decimal("0"):
        raise DataContractError(
            "INVEST_V0_NONPOSITIVE_NAV: allocation weights are undefined."
        )

    # NAV-inclusive allocation (positions + cash). Distinct from the
    # invested-only exposure below, which excludes cash by construction.
    # Position lines carry full valuation provenance (price, date, source,
    # FX); a non-empty source ID attests the quote was supplied, never that
    # it is qualified market data.
    allocation: List[Dict[str, str]] = []
    for position in valuation.positions:
        quote = prices[position.symbol]
        fx_source_id = ""
        if position.pricing_currency != clean_base:
            fx_source_id = fx_rates[
                (position.pricing_currency, clean_base)
            ].source_id
        allocation.append(
            {
                "key": position.symbol,
                "kind": "POSITION",
                "market_value_base": str(position.net_market_value_base),
                "nav_weight": str(position.net_market_value_base / nav),
                "price": str(position.price),
                "price_as_of": position.price_as_of.isoformat(),
                "price_source_id": quote.source_id,
                "pricing_currency": position.pricing_currency,
                "fx_rate_to_base": str(position.fx_rate_to_base),
                "fx_source_id": fx_source_id,
            }
        )
    for currency in sorted(valuation.cash_base):
        allocation.append(
            {
                "key": f"CASH:{currency}",
                "kind": "CASH",
                "market_value_base": str(valuation.cash_base[currency]),
                "nav_weight": str(valuation.cash_base[currency] / nav),
            }
        )

    # Invested-only exposure reuses position_exposure (single-currency lots
    # only); multi-currency position sets are BLOCKED, not approximated.
    position_currencies = {lot.currency for lot in ledger.position_lots}
    exposure_lines = []
    if not ledger.position_lots:
        invested_exposure: Dict[str, Any] = {
            "status": "NOT_ESTABLISHED",
            "reason": "No position lots; nothing to decompose.",
            "lines": [],
        }
    elif len(position_currencies) > 1:
        invested_exposure = {
            "status": "BLOCKED",
            "reason": (
                "Position lots span multiple currencies; invested-only "
                "exposure is not approximated without an explicit "
                "per-currency breakdown."
            ),
            "lines": [],
        }
    else:
        base_prices = {
            symbol: quote.price for symbol, quote in prices.items()
        }
        exposure_lines = position_exposure(ledger, base_prices)
        invested_exposure = {
            "status": "ESTABLISHED",
            "basis": (
                "Invested-positions-only weights (cash excluded by "
                "construction); NOT portfolio NAV weights."
            ),
            "lines": [
                {"key": line.key, "market_value": line.market_value,
                 "weight": line.weight}
                for line in exposure_lines
            ],
        }

    # Reconciliation: self-consistency only. Independence is never claimed
    # without an attestation this layer cannot produce. Status labels say
    # what COMPUTED means: a computed mismatch is still computed output,
    # never a pass.
    reconciliation_result = None
    if statement is None:
        reconciliation: Dict[str, Any] = {
            "status": "NOT_ESTABLISHED",
            "reason": "No statement snapshot supplied; nothing reconciled.",
            "matched": False,
            "is_independent": False,
            "breaks": [],
        }
    else:
        reconciliation_result = reconcile_snapshot_ledger(
            statement,
            ledger,
            statement_source_id=statement_source_id or "SYNTHETIC_STATEMENT",
            ledger_source_id=ledger_source_id or "SYNTHETIC_LEDGER",
            is_independent=False,
        )
        reconciliation = {
            "status": (
                "COMPUTED_MATCH"
                if reconciliation_result.matched
                else "COMPUTED_MISMATCH"
            ),
            "matched": bool(reconciliation_result.matched),
            "reconciliation_status": reconciliation_result.status,
            "is_independent": False,
            "basis": (
                "Self-consistency between the supplied statement and the "
                "derived ledger only; NOT independent broker reconciliation."
            ),
            "breaks": [
                {
                    "scope": item.scope,
                    "key": item.key,
                    "statement_value": item.statement_value,
                    "ledger_value": item.ledger_value,
                    "difference": item.difference,
                    "status": item.status,
                }
                for item in reconciliation_result.breaks
            ],
        }

    # PPDS read-only surface, genuinely reused (not duplicated): it carries
    # the reconciliation breaks, lineage notes, and attestation presence that
    # this report does not recompute. Available only when both reconciliation
    # and invested-only exposure computed; otherwise honestly absent.
    if reconciliation_result is not None and exposure_lines:
        ppds_surface: Dict[str, Any] = {
            "status": "ESTABLISHED",
            "surface": render_read_only_surface(
                ledger, reconciliation_result, exposure_lines
            ),
        }
    else:
        ppds_surface = {
            "status": "NOT_ESTABLISHED",
            "reason": (
                "Requires both a supplied statement and single-currency "
                "positions; absent inputs are not synthesized."
            ),
        }

    cost_lines = _validate_costs(costs)
    if (
        not cost_lines
        or any(
            line["basis"] == COST_BASIS_UNKNOWN or line["amount_base"] is None
            for line in cost_lines
        )
    ):
        # No disclosed lines, or any unknown line: totals stay
        # NOT_ESTABLISHED. Zero is never a default total.
        costs_total = None
    else:
        costs_total = str(
            sum((Decimal(line["amount_base"]) for line in cost_lines), Decimal("0"))
        )

    concentration_symbol = ""
    concentration_weight = Decimal("0")
    for entry in allocation:
        weight = Decimal(entry["nav_weight"])
        if weight > concentration_weight:
            concentration_weight = weight
            concentration_symbol = entry["key"]

    report: Dict[str, Any] = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "report_kind": "ACASH_INVEST_V0_READ_ONLY",
        "evidence_classification": EVIDENCE_SYNTHETIC_DEMONSTRATION,
        "as_of": as_of.isoformat(),
        "base_currency": clean_base,
        "valuation_basis": "Point-in-time synthetic fixture valuation; not market data.",
        "nav_base": str(nav),
        "total_cash_base": str(valuation.total_cash_base),
        "total_positions_net_base": str(valuation.total_positions_net_base),
        "allocation_nav_inclusive": allocation,
        "invested_only_exposure": invested_exposure,
        "largest_concentration": {
            "key": concentration_symbol,
            "nav_weight": str(concentration_weight),
        },
        "reconciliation": reconciliation,
        "ppds_surface": ppds_surface,
        "costs": {
            "lines": cost_lines,
            "total_base": costs_total,
            "total_basis": (
                "SUM_OF_DISCLOSED_LINES"
                if costs_total is not None
                else "NOT_ESTABLISHED"
            ),
        },
        "comparisons_available": {
            "cash_no_trade_path": "BLOCKED: requires qualified historical series.",
            "buy_and_hold_path": "BLOCKED: requires qualified historical series.",
            "allocation_ranking": "BLOCKED: ranking requires statistical evidence.",
        },
        "missing_data_and_uncertainty": [
            "No qualified historical ETF price history.",
            "No expected returns, risk forecasts, or drawdown estimates.",
            "No independent broker reconciliation.",
            "No account-verified fees; all costs are assumptions unless stated.",
            "No tax, FX funding, or market-impact evidence.",
        ] + [str(note) for note in evidence_notes],
        "execution": {
            "order_submission_authorized": False,
            "capital_authority_usd": "0.00",
            "recommendation": (
                "BLOCKED: synthetic demonstration only. No investment "
                "recommendation is authorized. NO_REAL_ORDERS."
            ),
        },
        "ledger_head_sha256": ledger.head_sha256,
        "ledger_entry_count": ledger.entry_count,
    }
    for forbidden in _FORBIDDEN_STATISTICS:
        if forbidden in report:
            raise DataContractError(
                f"INVEST_V0_FORBIDDEN_STATISTIC: {forbidden}."
            )
    return report


def render_v0_json(report: Mapping[str, Any]) -> str:
    """Deterministic JSON rendering (sorted keys, indent 2)."""
    return json.dumps(report, sort_keys=True, indent=2)


def render_v0_markdown(report: Mapping[str, Any]) -> str:
    """Deterministic human-readable Markdown rendering."""
    lines: List[str] = []
    lines.append("# ACASH Invest V0 — Read-Only Investment Report (SYNTHETIC)")
    lines.append("")
    lines.append(f"- As of: `{report['as_of']}`")
    lines.append(f"- Base currency: `{report['base_currency']}`")
    lines.append(f"- Evidence: `{report['evidence_classification']}`")
    lines.append(f"- Total NAV: `{report['nav_base']}` {report['base_currency']}")
    lines.append(f"- Cash total: `{report['total_cash_base']}`")
    lines.append("")
    lines.append("## Allocation (NAV-inclusive)")
    lines.append("")
    lines.append("| Holding | Kind | Market value | NAV weight | Price | Price as-of | Price source |")
    lines.append("|---|---|---|---|---|---|---|")
    allocation = report["allocation_nav_inclusive"]
    assert isinstance(allocation, list)
    for entry in allocation:
        assert isinstance(entry, dict)
        if entry["kind"] == "POSITION":
            lines.append(
                f"| {entry['key']} | {entry['kind']} | {entry['market_value_base']} "
                f"| {entry['nav_weight']} | {entry['price']} ({entry['pricing_currency']}) "
                f"| {entry['price_as_of']} | {entry['price_source_id']} |"
            )
        else:
            lines.append(
                f"| {entry['key']} | {entry['kind']} | {entry['market_value_base']} "
                f"| {entry['nav_weight']} | n/a | n/a | n/a |"
            )
    lines.append("")
    lines.append("## Invested-only exposure (cash excluded by construction)")
    invested = report["invested_only_exposure"]
    assert isinstance(invested, dict)
    lines.append(f"- Status: `{invested['status']}`")
    if invested["status"] == "ESTABLISHED":
        for line in invested["lines"]:
            assert isinstance(line, dict)
            lines.append(f"- {line['key']}: value `{line['market_value']}`, weight `{line['weight']}`")
    else:
        lines.append(f"- Reason: {invested['reason']}")
    lines.append("")
    lines.append("## Reconciliation")
    reconciliation = report["reconciliation"]
    assert isinstance(reconciliation, dict)
    lines.append(f"- Status: `{reconciliation['status']}`")
    if reconciliation["status"] in ("COMPUTED_MATCH", "COMPUTED_MISMATCH"):
        lines.append(f"- Matched: `{reconciliation['matched']}`")
        lines.append(f"- Independent: `{reconciliation['is_independent']}`")
        for break_item in reconciliation["breaks"]:
            assert isinstance(break_item, dict)
            lines.append(
                f"- Break [{break_item['scope']}/{break_item['key']}]: "
                f"statement `{break_item['statement_value']}` vs ledger "
                f"`{break_item['ledger_value']}` "
                f"(diff `{break_item['difference']}`, {break_item['status']})"
            )
    else:
        lines.append(f"- Reason: {reconciliation['reason']}")
    lines.append("")
    lines.append("## PPDS read-only surface (reused, not recomputed)")
    surface_section = report["ppds_surface"]
    assert isinstance(surface_section, dict)
    lines.append(f"- Status: `{surface_section['status']}`")
    if surface_section["status"] == "ESTABLISHED":
        surface = surface_section["surface"]
        assert isinstance(surface, dict)
        lines.append(f"- Ledger head: `{surface['head_sha256']}` "
                     f"({surface['entry_count']} entries)")
        lines.append(f"- Surface matched: `{surface['reconciliation_matched']}`")
        lines.append(f"- Order controls: `{surface['order_controls']}`")
    else:
        lines.append(f"- Reason: {surface_section['reason']}")
    lines.append("")
    lines.append("## Costs")
    costs = report["costs"]
    assert isinstance(costs, dict)
    for line in costs["lines"]:
        assert isinstance(line, dict)
        lines.append(
            f"- {line['name']} [{line['basis']}]: {line['detail']} "
            f"(amount: {line['amount_base']})"
        )
    lines.append(f"- Total: `{costs['total_base']}` ({costs['total_basis']})")
    lines.append("")
    lines.append("## Missing data and uncertainty")
    missing = report["missing_data_and_uncertainty"]
    assert isinstance(missing, list)
    for item in missing:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Execution")
    execution = report["execution"]
    assert isinstance(execution, dict)
    lines.append(f"- Order submission authorized: `{execution['order_submission_authorized']}`")
    lines.append(f"- Capital authority (USD): `{execution['capital_authority_usd']}`")
    lines.append(f"- Recommendation: {execution['recommendation']}")
    lines.append("")
    lines.append(f"Ledger head: `{report['ledger_head_sha256']}` "
                 f"({report['ledger_entry_count']} entries)")
    lines.append("")
    return "\n".join(lines)
