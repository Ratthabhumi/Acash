"""PPDS read-only skeleton: statement-vs-ledger reconciliation (exact Decimal).

Reports match/mismatch with exact equality — no tolerance, no silent
rounding. Any break fails the reconciliation (it never mutates either side).
Provides evidence-backed diagnostic classification for breaks when transaction
evidence is supplied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.statement_ingest import AccountSnapshot


@dataclass(frozen=True)
class StatementTransaction:
    """Read-only synthetic transaction evidence item (dividend, trade, fee, etc.)."""

    transaction_id: str
    transaction_date: date
    record_type: str  # DIVIDEND, FEE, TRADE, CORPORATE_ACTION, TRANSFER
    currency: str
    amount: Decimal  # Cash delta or value
    quantity: Optional[Decimal] = None  # Share quantity delta for positions
    symbol: Optional[str] = None
    description: str = ""


@dataclass(frozen=True)
class ReconciliationBreak:
    scope: str  # CASH or POSITION
    key: str  # Currency or Symbol
    statement_value: str
    ledger_value: str
    difference: str = ""
    status: str = "UNEXPLAINED_MISMATCH"  # SUPPORTED_EXPLANATION, POSSIBLE_CAUSE, UNEXPLAINED_MISMATCH
    explanation: Optional[str] = None
    evidence_refs: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.difference:
            try:
                diff = Decimal(self.statement_value) - Decimal(self.ledger_value)
                object.__setattr__(self, "difference", str(diff))
            except Exception:
                pass


@dataclass(frozen=True)
class ReconciliationResult:
    matched: bool
    breaks: List[ReconciliationBreak]
    statement_cash: Dict[str, str]
    ledger_cash: Dict[str, str]


def _fmt(amount: Decimal) -> str:
    return str(amount)


def _diagnose_cash_break(
    currency: str,
    delta: Decimal,
    transactions: Sequence[StatementTransaction],
) -> Tuple[str, Optional[str], Tuple[str, ...]]:
    """Match cash difference against explicit transaction evidence (never guess)."""
    matches: List[StatementTransaction] = [
        tx for tx in transactions
        if tx.currency == currency and tx.amount == delta
    ]
    if len(matches) == 1:
        tx = matches[0]
        desc = f" ({tx.description})" if tx.description else ""
        expl = (
            f"Documented {tx.record_type} transaction {tx.transaction_id}"
            f" matches cash difference {delta} {currency}{desc}"
        )
        return "SUPPORTED_EXPLANATION", expl, (tx.transaction_id,)
    if len(matches) > 1:
        ids = tuple(tx.transaction_id for tx in matches)
        expl = f"Multiple candidate transactions match cash difference {delta} {currency}: {', '.join(ids)}"
        return "POSSIBLE_CAUSE", expl, ids

    return "UNEXPLAINED_MISMATCH", None, ()


def _diagnose_position_break(
    symbol: str,
    delta: Decimal,
    transactions: Sequence[StatementTransaction],
) -> Tuple[str, Optional[str], Tuple[str, ...]]:
    """Match position quantity difference against explicit transaction evidence."""
    matches: List[StatementTransaction] = [
        tx for tx in transactions
        if tx.symbol == symbol and tx.quantity == delta
    ]
    if len(matches) == 1:
        tx = matches[0]
        desc = f" ({tx.description})" if tx.description else ""
        expl = (
            f"Documented {tx.record_type} transaction {tx.transaction_id}"
            f" matches position difference {delta} shares of {symbol}{desc}"
        )
        return "SUPPORTED_EXPLANATION", expl, (tx.transaction_id,)
    if len(matches) > 1:
        ids = tuple(tx.transaction_id for tx in matches)
        expl = f"Multiple candidate transactions match position difference {delta} {symbol}: {', '.join(ids)}"
        return "POSSIBLE_CAUSE", expl, ids

    return "UNEXPLAINED_MISMATCH", None, ()


def reconcile_snapshot_ledger(
    snapshot: AccountSnapshot,
    ledger: NormalizedPortfolioLedger,
    *,
    transactions: Sequence[StatementTransaction] = (),
) -> ReconciliationResult:
    """Reconcile a statement snapshot against the normalized ledger exactly.

    If transactions are provided, breaks are evaluated against documented
    evidence to classify as SUPPORTED_EXPLANATION, POSSIBLE_CAUSE, or UNEXPLAINED_MISMATCH.
    """
    breaks: List[ReconciliationBreak] = []
    snap_cash = snapshot.cash_by_currency()
    led_cash = ledger.cash_by_currency()
    for currency in sorted(set(snap_cash) | set(led_cash)):
        left = snap_cash.get(currency, Decimal("0"))
        right = led_cash.get(currency, Decimal("0"))
        if left != right:
            delta = left - right
            status, explanation, evidence_refs = _diagnose_cash_break(currency, delta, transactions)
            breaks.append(ReconciliationBreak(
                scope="CASH",
                key=currency,
                statement_value=_fmt(left),
                ledger_value=_fmt(right),
                difference=_fmt(delta),
                status=status,
                explanation=explanation,
                evidence_refs=evidence_refs,
            ))

    snap_qty = snapshot.quantity_by_symbol()
    led_qty = ledger.quantity_by_symbol()
    for symbol in sorted(set(snap_qty) | set(led_qty)):
        left = snap_qty.get(symbol, Decimal("0"))
        right = led_qty.get(symbol, Decimal("0"))
        if left != right:
            delta = left - right
            status, explanation, evidence_refs = _diagnose_position_break(symbol, delta, transactions)
            breaks.append(ReconciliationBreak(
                scope="POSITION",
                key=symbol,
                statement_value=_fmt(left),
                ledger_value=_fmt(right),
                difference=_fmt(delta),
                status=status,
                explanation=explanation,
                evidence_refs=evidence_refs,
            ))

    return ReconciliationResult(
        matched=not breaks,
        breaks=breaks,
        statement_cash={k: _fmt(v) for k, v in snap_cash.items()},
        ledger_cash={k: _fmt(v) for k, v in led_cash.items()},
    )


def format_reconciliation_report(result: ReconciliationResult) -> str:
    """Generate a deterministic human-readable text report for operator review."""
    lines: List[str] = ["=== PPDS RECONCILIATION REPORT ==="]
    status_str = "MATCHED (NO BREAKS)" if result.matched else f"BREAKS DETECTED ({len(result.breaks)} breaks)"
    lines.append(f"Status: {status_str}")
    lines.append("")
    if result.breaks:
        lines.append("Break Details:")
        for idx, brk in enumerate(result.breaks, 1):
            lines.append(
                f"  [{idx}] Scope: {brk.scope} | Key: {brk.key} | Statement: {brk.statement_value} | Ledger: {brk.ledger_value} | Delta: {brk.difference}"
            )
            lines.append(f"      Diagnostic Status: {brk.status}")
            if brk.explanation:
                lines.append(f"      Explanation: {brk.explanation}")
            if brk.evidence_refs:
                lines.append(f"      Evidence Refs: {', '.join(brk.evidence_refs)}")
    else:
        lines.append("All cash balances and position quantities match ledger perfectly.")
    return "\n".join(lines)
