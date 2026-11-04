"""Tax and cash-flow intelligence over owner-supplied evidence (never a tax filing).

The module separates four things that are easy to confuse:

1. a broker **annual summary** — an aggregate control total, not an itemised journal;
2. **staged trade candidates** — evidence rows that are not yet canonical transactions;
3. **cash-flow classification** — internal transfers, external contributions, remittances, settlements;
4. **tax liability** — always ``NOT_ESTABLISHED`` until income, residence, remittance and cost evidence
   is complete, because an aggregate cannot prove the character of an individual remittance.

Reuse ``ppds.transactions`` for canonical events; this layer only classifies and stages.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_TAX_EVIDENCE_V1"
RULESET_VERSION = "TH-2026.1"
RULESET = {
    "version": RULESET_VERSION,
    "effective_from": "2026-01-01",
    "citations": {
        "residence_180_days": "https://www.rd.go.th/5937.html",
        "foreign_income_remittance": "https://www.rd.go.th/fileadmin/download/news/question_p161_162.pdf",
        "foreign_tax_credit": "https://www.rd.go.th/68221.html",
        "us_th_treaty": "https://www.irs.gov/pub/irs-trty/thailand.pdf",
        "us_dividend_withholding": ("https://www.irs.gov/individuals/international-taxpayers/"
                                    "federal-income-tax-withholding-and-reporting-on-other-kinds-of-us-source-income-paid-to-nonresident-aliens"),
    },
    "uncertainty": [
        "Residence and remittance facts are owner-supplied, not independently verified.",
        "The 2026-01-01..2026-09-30 summary cannot support an annual liability on its own.",
        "Treaty rates are not assumed for any individual distribution.",
    ],
}
CASH_FLOW_CLASSES = (
    "BROKER_ACCOUNT_INTERNAL_TRANSFER", "OWNER_EXTERNAL_CONTRIBUTION", "OWNER_EXTERNAL_WITHDRAWAL",
    "FOREIGN_INCOME_REMITTANCE", "TRADE_SETTLEMENT", "FX_CONVERSION", "DIVIDEND", "FOREIGN_TAX_WITHHELD",
    "CANCELLED_ORDER", "UNMATCHED_TRANSFER", "UNCLASSIFIED",
)
TRADE_FIELDS = {"date", "security_id", "amount", "amount_currency", "shares", "price_per_share",
                "price_currency", "status", "source", "note"}
TAX_DIR = Path("data/private/tax")
EVIDENCE_FILE = "evidence_2026.json"


def _dec(what: str, value: Any) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DataContractError(f"TAX_EVIDENCE_INVALID: {what}.") from None
    if not number.is_finite():
        raise DataContractError(f"TAX_EVIDENCE_INVALID: {what}.")
    return number


def _day(value: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise DataContractError(f"TAX_EVIDENCE_INVALID: {what}.") from None


@dataclass(frozen=True)
class AnnualSummary:
    tax_year: int
    covered_from: date
    covered_to: date
    funds_in_usd: Decimal
    funds_out_usd: Decimal
    gross_dividends_usd: Decimal
    withheld_usd: Decimal
    net_dividends_usd: Decimal
    source: str
    observed_at: str
    publication_lag_days: int = 6


def parse_summary(doc: Mapping[str, Any]) -> AnnualSummary:
    year = int(_dec("tax_year", doc.get("tax_year")))
    start = _day(doc.get("covered_from"), "covered_from")
    end = _day(doc.get("covered_to"), "covered_to")
    if start > end or start.year != year:
        raise DataContractError("TAX_EVIDENCE_INVALID: coverage window.")
    funds_in = _dec("funds_in_usd", doc.get("funds_in_usd"))
    funds_out = _dec("funds_out_usd", doc.get("funds_out_usd"))
    gross = _dec("gross_dividends_usd", doc.get("gross_dividends_usd"))
    withheld = _dec("withheld_usd", doc.get("withheld_usd"))
    net = _dec("net_dividends_usd", doc.get("net_dividends_usd"))
    if min(funds_in, funds_out, gross, withheld, net) < 0:
        raise DataContractError("TAX_EVIDENCE_INVALID: negative aggregate.")
    if gross - withheld != net:
        raise DataContractError("TAX_EVIDENCE_ARITHMETIC_MISMATCH: gross - withheld != net.")
    observed = datetime.fromisoformat(str(doc.get("observed_at")))
    if observed.tzinfo is None:
        raise DataContractError("TAX_EVIDENCE_INVALID: observed_at must be timezone-aware.")
    return AnnualSummary(year, start, end, funds_in, funds_out, gross, withheld, net,
                         str(doc.get("source")), observed.isoformat(),
                         int(_dec("publication_lag_days", doc.get("publication_lag_days", 6))))


def summary_checks(summary: AnnualSummary) -> Dict[str, Any]:
    """What the aggregate can and cannot support. An aggregate is a control total, not a journal."""
    year_end = date(summary.tax_year, 12, 31)
    ratio = (summary.withheld_usd / summary.gross_dividends_usd) if summary.gross_dividends_usd > 0 else None
    # Monthly data appears on day `publication_lag_days` of the following month. The next report covers
    # the first month after this window and is published one month after that month ends.
    next_month = (summary.covered_to.replace(day=1) + timedelta(days=32)).replace(day=1)
    publication = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1) + timedelta(
        days=summary.publication_lag_days - 1)
    return {
        "coverage_complete_for_year": summary.covered_to == year_end,
        "missing_months": (next_month.month if summary.covered_to < year_end else None),
        "last_covered_date": summary.covered_to.isoformat(),
        "next_expected_update": publication.isoformat(),
        "gross_equals_net_plus_withheld": summary.gross_dividends_usd - summary.withheld_usd == summary.net_dividends_usd,
        "effective_withholding_ratio": None if ratio is None else format(ratio.quantize(Decimal("0.0001")), "f"),
        "observed_ratio_is_not_a_treaty_rate": True,
        "funds_in_minus_out_is_not_taxable_income": True,
        "itemised_dividends_available": False,
        "note": ("Aggregates cannot prove principal versus income, so they never create journal events "
                 "and never establish a tax liability."),
    }


def classify_cash_flow(kind: str, description: str = "") -> str:
    """Classify one cash line. Anything that cannot be proven stays unmatched or unclassified."""
    text = f"{kind} {description}".lower()
    if kind in CASH_FLOW_CLASSES:
        return kind
    if "cancel" in text:
        return "CANCELLED_ORDER"
    if "dividend" in text or "ปันผล" in text:
        return "DIVIDEND"
    if "withhold" in text or "tax" in text:
        return "FOREIGN_TAX_WITHHELD"
    if "exchange" in text or "fx" in text or "แลก" in text:
        return "FX_CONVERSION"
    if "fcd" in text or "internal" in text or "transfer to dime" in text:
        return "BROKER_ACCOUNT_INTERNAL_TRANSFER"
    if "buy" in text or "sell" in text or "settle" in text or "ซื้อ" in text or "ขาย" in text:
        return "TRADE_SETTLEMENT"
    if "withdraw" in text or "ถอน" in text:
        return "OWNER_EXTERNAL_WITHDRAWAL"
    if "deposit" in text or "ฝาก" in text:
        return "UNMATCHED_TRANSFER"
    return "UNCLASSIFIED"


def stage_trades(rows: Sequence[Mapping[str, Any]], baseline_date: date,
                 existing_event_ids: Sequence[str] = ()) -> Dict[str, Any]:
    """Stage trade evidence without touching the canonical journal.

    A trade on or before the frozen baseline is a pre-baseline candidate: replaying it as a new event
    would double-count a position that the snapshot already carries.
    """
    known = set(existing_event_ids)
    accepted: List[Dict[str, Any]] = []
    pre_baseline: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for raw in rows:
        extra = set(raw) - TRADE_FIELDS
        if extra:
            raise DataContractError(f"TAX_EVIDENCE_INVALID: unexpected trade field(s) {sorted(extra)}.")
        symbol = str(raw.get("security_id") or "").strip().upper()
        status = str(raw.get("status") or "EXECUTED").upper()
        day = _day(raw.get("date"), "trade date")
        if status in ("CANCELLED", "REJECTED"):
            rejected.append({"security_id": symbol, "date": day.isoformat(), "status": status,
                             "reason": "CANCELLED_ORDER", "creates_position": False})
            continue
        amount = _dec("amount", raw.get("amount"))
        shares = _dec("shares", raw.get("shares"))
        price = _dec("price_per_share", raw.get("price_per_share"))
        if amount <= 0 or shares <= 0 or price <= 0:
            raise DataContractError(f"TAX_EVIDENCE_INVALID: non-positive trade {symbol}.")
        event_id = _event_id(day, symbol, shares, price, str(raw.get("amount_currency")))
        entry = {"event_id": event_id, "date": day.isoformat(), "security_id": symbol,
                 "shares": format(shares, "f"), "price_per_share": format(price, "f"),
                 "price_currency": str(raw.get("price_currency") or "USD"),
                 "amount": format(amount, "f"), "amount_currency": str(raw.get("amount_currency") or "USD"),
                 "source": str(raw.get("source") or "OWNER_SUPPLIED"),
                 "verification_state": "STAGED_EVIDENCE"}
        if event_id in known:
            rejected.append({**entry, "reason": "DUPLICATE_EVENT"})
        elif day <= baseline_date:
            pre_baseline.append({**entry, "reason": "PRE_BASELINE_CANDIDATE",
                                 "note": ("On or before the frozen snapshot baseline; requires the governed "
                                          "rebase process, never an ordinary post-baseline event.")})
        else:
            accepted.append(entry)
    return {"accepted_for_journal": accepted, "pre_baseline_candidates": pre_baseline,
            "rejected": rejected, "baseline_date": baseline_date.isoformat()}


def _event_id(day: date, symbol: str, shares: Decimal, price: Decimal, currency: str) -> str:
    payload = "|".join([day.isoformat(), symbol, format(shares, "f"), format(price, "f"), currency])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def readiness(summary: AnnualSummary, staged: Mapping[str, Any]) -> Dict[str, Any]:
    """Which part of an actual-performance or tax calculation the evidence can support."""
    pre = staged.get("pre_baseline_candidates") or []
    accepted = staged.get("accepted_for_journal") or []
    return {
        "schema": "ACASH_TAX_READINESS_V1",
        "trade_history": "PARTIAL_EVIDENCE_ONLY" if accepted or pre else "MISSING",
        "trade_history_detail": {"accepted": len(accepted), "pre_baseline": len(pre),
                                 "rejected": len(staged.get("rejected") or [])},
        "currency_conversion": "MISSING_EXECUTION_RATES_FOR_THB_SETTLEMENTS",
        "cash_flow": "PARTIAL_AGGREGATE_ONLY",
        "dividends_and_tax": "AGGREGATE_ONLY_NO_ITEMISED_WITHHOLDING",
        "opening_lots": "UNVERIFIED_PRE_BASELINE",
        "position_reconciliation": "SNAPSHOT_2026_11_02_ONLY",
        "historical_performance": "DATA_REQUIRED",
        "tax_liability": "NOT_ESTABLISHED",
        "foreign_tax_credit": "CREDIT_ELIGIBILITY_UNVERIFIED",
        "coverage_complete_for_year": summary_checks(summary)["coverage_complete_for_year"],
        "reasons": [
            "Trade coverage is a subset supplied by the owner, not a complete broker statement.",
            "THB-settled purchases have no executed USD/THB rate in the evidence.",
            "The annual summary is an aggregate; individual dividends and withholding are not itemised.",
            "The snapshot baseline is 2026-11-02 and has not been rebased from opening lots.",
        ],
    }


def tax_liability(summary: AnnualSummary, staged: Mapping[str, Any]) -> Dict[str, Any]:
    """Never computes a number from an aggregate; says exactly what is missing instead."""
    return {
        "status": "NOT_ESTABLISHED",
        "ruleset": RULESET_VERSION,
        "reasons": [
            "Residence days and remittance dates are owner-supplied and unverified.",
            "Aggregate funds brought into Thailand cannot be split into principal and income.",
            "Dividends are reported only as an annual total; withholding is not itemised per distribution.",
            "Foreign tax credit requires per-income evidence and the Thai tax attributable to it.",
        ],
        "assumptions_not_made": ["principal returned is not automatically tax-free",
                                 "funds in minus funds out is not taxable income",
                                 "observed withholding is not the treaty rate",
                                 "unrealised gains are not taxable gains"],
        "credit_eligibility": "CREDIT_ELIGIBILITY_UNVERIFIED",
    }


def build_evidence(summary_doc: Mapping[str, Any], trades: Sequence[Mapping[str, Any]],
                   cash_lines: Sequence[Mapping[str, Any]], baseline_date: date) -> Dict[str, Any]:
    summary = parse_summary(summary_doc)
    staged = stage_trades(trades, baseline_date)
    flows = [{"description": str(line.get("description") or ""),
              "classification": classify_cash_flow(str(line.get("kind") or ""), str(line.get("description") or "")),
              "amount": str(line.get("amount")), "currency": str(line.get("currency") or ""),
              "date": str(line.get("date") or ""), "source": str(line.get("source") or "OWNER_SUPPLIED")}
             for line in cash_lines]
    return {
        "schema": SCHEMA,
        "data_class": "OWNER_PRIVATE_OBSERVATION",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ruleset": RULESET,
        "annual_summary": {
            "tax_year": summary.tax_year, "covered_from": summary.covered_from.isoformat(),
            "covered_to": summary.covered_to.isoformat(), "source": summary.source,
            "observed_at": summary.observed_at,
            "funds_in_usd": format(summary.funds_in_usd, "f"),
            "funds_out_usd": format(summary.funds_out_usd, "f"),
            "gross_dividends_usd": format(summary.gross_dividends_usd, "f"),
            "withheld_usd": format(summary.withheld_usd, "f"),
            "net_dividends_usd": format(summary.net_dividends_usd, "f"),
            "checks": summary_checks(summary),
        },
        "staged_trades": staged,
        "cash_flows": flows,
        "readiness": readiness(summary, staged),
        "tax_liability": tax_liability(summary, staged),
    }


def write_evidence(doc: Mapping[str, Any], directory: Path = TAX_DIR,
                   name: str = EVIDENCE_FILE) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    target.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return target


def load_evidence(directory: Path = TAX_DIR, name: str = EVIDENCE_FILE) -> Optional[Dict[str, Any]]:
    path = directory / name
    if not path.is_file():
        return None
    try:
        doc: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc
