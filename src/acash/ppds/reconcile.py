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


VALID_CASH_RECORD_TYPES = {
    "DIVIDEND", "FEE", "TRANSFER", "INTEREST", "TAX", "TRADE", "CORPORATE_ACTION"
}
VALID_POSITION_RECORD_TYPES = {
    "TRADE", "CORPORATE_ACTION", "TRANSFER", "SPLIT"
}


@dataclass(frozen=True)
class StatementTransaction:
    """Read-only synthetic transaction evidence item (dividend, trade, fee, etc.)."""

    transaction_id: str
    transaction_date: date
    record_type: str  # DIVIDEND, FEE, TRADE, CORPORATE_ACTION, TRANSFER, TAX, INTEREST
    currency: str
    amount: Decimal  # Cash delta or value
    quantity: Optional[Decimal] = None  # Share quantity delta for positions
    symbol: Optional[str] = None
    description: str = ""
    settled: Optional[bool] = None  # None = unknown/unverified, True = confirmed settled, False = pending
    provenance: str = ""  # Documented source statement or audit confirmation ref
    already_reflected: Optional[bool] = None  # None = unknown/unverified, True = posted to ledger, False = unposted


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
    as_of: date,
    duplicate_tx_ids: set[str],
    consumed_tx_ids: set[str],
) -> Tuple[str, Optional[str], Tuple[str, ...]]:
    """Match cash difference against explicit transaction evidence with causal validation."""
    all_matching = [
        tx for tx in transactions
        if tx.currency == currency and tx.amount == delta
    ]
    unreflected_matching = [tx for tx in all_matching if tx.already_reflected is not True]

    if not unreflected_matching:
        if all_matching:
            ids = tuple(tx.transaction_id for tx in all_matching)
            expl = (
                f"Matching transactions ({', '.join(ids)}) are already reflected in internal ledger; "
                f"cannot explain unreflected cash difference {delta} {currency}"
            )
            return "UNEXPLAINED_MISMATCH", expl, ()
        return "UNEXPLAINED_MISMATCH", None, ()

    if len(unreflected_matching) > 1:
        ids = tuple(tx.transaction_id for tx in unreflected_matching)
        expl = f"Multiple candidate transactions match cash difference {delta} {currency}: {', '.join(ids)}"
        return "POSSIBLE_CAUSE", expl, ids

    tx = unreflected_matching[0]
    tx_id = tx.transaction_id

    if tx_id in consumed_tx_ids:
        expl = (
            f"Candidate transaction {tx_id} matches cash difference {delta} {currency} "
            f"but was already consumed by another reconciliation break"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx_id in duplicate_tx_ids:
        expl = (
            f"Candidate transaction {tx_id} matches cash difference {delta} {currency} "
            f"but transaction ID is duplicated across evidence records"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx.transaction_date > as_of:
        expl = (
            f"Candidate transaction {tx_id} matches cash difference {delta} {currency} "
            f"but transaction date {tx.transaction_date.isoformat()} is after statement as-of {as_of.isoformat()}"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx.settled is None:
        expl = (
            f"Candidate transaction {tx_id} matches cash difference {delta} {currency} "
            f"but settlement status is unverified/unknown"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if not tx.settled:
        expl = (
            f"Candidate transaction {tx_id} matches cash difference {delta} {currency} "
            f"but transaction status is unsettled/pending"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx.already_reflected is None:
        expl = (
            f"Candidate transaction {tx_id} matches cash difference {delta} {currency} "
            f"but ledger posting status is unverified/unknown"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if not tx.provenance or not tx.provenance.strip():
        expl = (
            f"Candidate transaction {tx_id} matches cash difference {delta} {currency} "
            f"but lacks documented source provenance"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx.record_type.upper() not in VALID_CASH_RECORD_TYPES:
        expl = (
            f"Candidate transaction {tx_id} matches amount {delta} {currency} "
            f"but has invalid record type '{tx.record_type}' for cash discrepancy"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    consumed_tx_ids.add(tx_id)
    desc = f" ({tx.description})" if tx.description else ""
    expl = (
        f"Documented {tx.record_type} transaction {tx_id} [{tx.provenance}]"
        f" matches cash difference {delta} {currency}{desc}"
    )
    return "SUPPORTED_EXPLANATION", expl, (tx_id,)


def _diagnose_position_break(
    symbol: str,
    delta: Decimal,
    transactions: Sequence[StatementTransaction],
    as_of: date,
    duplicate_tx_ids: set[str],
    consumed_tx_ids: set[str],
) -> Tuple[str, Optional[str], Tuple[str, ...]]:
    """Match position quantity difference against explicit transaction evidence with causal validation."""
    all_matching = [
        tx for tx in transactions
        if tx.symbol == symbol and tx.quantity == delta
    ]
    unreflected_matching = [tx for tx in all_matching if tx.already_reflected is not True]

    if not unreflected_matching:
        if all_matching:
            ids = tuple(tx.transaction_id for tx in all_matching)
            expl = (
                f"Matching transactions ({', '.join(ids)}) are already reflected in internal ledger; "
                f"cannot explain unreflected position difference {delta} {symbol}"
            )
            return "UNEXPLAINED_MISMATCH", expl, ()
        return "UNEXPLAINED_MISMATCH", None, ()

    if len(unreflected_matching) > 1:
        ids = tuple(tx.transaction_id for tx in unreflected_matching)
        expl = f"Multiple candidate transactions match position difference {delta} {symbol}: {', '.join(ids)}"
        return "POSSIBLE_CAUSE", expl, ids

    tx = unreflected_matching[0]
    tx_id = tx.transaction_id

    if tx_id in consumed_tx_ids:
        expl = (
            f"Candidate transaction {tx_id} matches position difference {delta} shares of {symbol} "
            f"but was already consumed by another reconciliation break"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx_id in duplicate_tx_ids:
        expl = (
            f"Candidate transaction {tx_id} matches position difference {delta} shares of {symbol} "
            f"but transaction ID is duplicated across evidence records"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx.transaction_date > as_of:
        expl = (
            f"Candidate transaction {tx_id} matches position difference {delta} shares of {symbol} "
            f"but transaction date {tx.transaction_date.isoformat()} is after statement as-of {as_of.isoformat()}"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx.settled is None:
        expl = (
            f"Candidate transaction {tx_id} matches position difference {delta} shares of {symbol} "
            f"but settlement status is unverified/unknown"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if not tx.settled:
        expl = (
            f"Candidate transaction {tx_id} matches position difference {delta} shares of {symbol} "
            f"but transaction status is unsettled/pending"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx.already_reflected is None:
        expl = (
            f"Candidate transaction {tx_id} matches position difference {delta} shares of {symbol} "
            f"but ledger posting status is unverified/unknown"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if not tx.provenance or not tx.provenance.strip():
        expl = (
            f"Candidate transaction {tx_id} matches position difference {delta} shares of {symbol} "
            f"but lacks documented source provenance"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    if tx.record_type.upper() not in VALID_POSITION_RECORD_TYPES:
        expl = (
            f"Candidate transaction {tx_id} matches quantity {delta} {symbol} "
            f"but has invalid record type '{tx.record_type}' for position discrepancy"
        )
        return "POSSIBLE_CAUSE", expl, (tx_id,)

    consumed_tx_ids.add(tx_id)
    desc = f" ({tx.description})" if tx.description else ""
    expl = (
        f"Documented {tx.record_type} transaction {tx_id} [{tx.provenance}]"
        f" matches position difference {delta} shares of {symbol}{desc}"
    )
    return "SUPPORTED_EXPLANATION", expl, (tx_id,)


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
    seen_tx_ids: set[str] = set()
    duplicate_tx_ids: set[str] = set()
    for tx in transactions:
        if tx.transaction_id in seen_tx_ids:
            duplicate_tx_ids.add(tx.transaction_id)
        seen_tx_ids.add(tx.transaction_id)

    consumed_tx_ids: set[str] = set()
    as_of = snapshot.as_of

    breaks: List[ReconciliationBreak] = []
    snap_cash = snapshot.cash_by_currency()
    led_cash = ledger.cash_by_currency()
    for currency in sorted(set(snap_cash) | set(led_cash)):
        left = snap_cash.get(currency, Decimal("0"))
        right = led_cash.get(currency, Decimal("0"))
        if left != right:
            delta = left - right
            status, explanation, evidence_refs = _diagnose_cash_break(
                currency, delta, transactions, as_of, duplicate_tx_ids, consumed_tx_ids
            )
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
            status, explanation, evidence_refs = _diagnose_position_break(
                symbol, delta, transactions, as_of, duplicate_tx_ids, consumed_tx_ids
            )
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
