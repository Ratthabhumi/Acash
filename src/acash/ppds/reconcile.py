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
class IndependentLedgerAttestation:
    """Documented evidence attestation binding an independently supplied ledger to verified origin."""

    ledger_source_id: str
    artifact_sha256: str
    account_id: str
    as_of: date
    entry_count: int
    head_sha256: str
    lineage_ref: str
    origin_system: str


@dataclass(frozen=True)
class ReconciliationResult:
    matched: bool
    breaks: List[ReconciliationBreak]
    statement_cash: Dict[str, str]
    ledger_cash: Dict[str, str]
    status: str = "SELF_CONSISTENCY_VERIFIED"
    is_independent: bool = False
    statement_source_id: Optional[str] = None
    ledger_source_id: Optional[str] = None
    attestation: Optional[IndependentLedgerAttestation] = None
    lineage_notes: Tuple[str, ...] = ()


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
    statement_source_id: Optional[str] = None,
    statement_raw_sha256: Optional[str] = None,
    ledger_source_id: Optional[str] = None,
    is_independent: bool = False,
    attestation: Optional[IndependentLedgerAttestation] = None,
) -> ReconciliationResult:
    """Reconcile a statement snapshot against a normalized ledger exactly.

    If transactions are provided, breaks are evaluated against documented
    evidence to classify as SUPPORTED_EXPLANATION, POSSIBLE_CAUSE, or UNEXPLAINED_MISMATCH.

    Distinguishes:
    - SELF_CONSISTENCY_VERIFIED: Statement checked against its own derived ledger.
    - INDEPENDENT_RECONCILIATION_MATCHED: Checked against independently attested ledger.
    - INDEPENDENT_RECONCILIATION_BREAKS: Checked against independent ledger with breaks.
    - NUMERICALLY_MATCHED_INDEPENDENCE_UNVERIFIED: Balances match but independent lineage unverified.
    - SOURCE_LINEAGE_CONFLICT: Attestation conflicts (account mismatch, as-of mismatch, tampered hash, self-masquerade).
    - INDEPENDENCE_UNVERIFIED: Missing or identical source IDs when claiming independence.
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

    matched = not breaks
    lineage_notes: List[str] = []

    if is_independent:
        stmt_src = (statement_source_id or "").strip()
        led_src = (ledger_source_id or (attestation.ledger_source_id if attestation else "")).strip()

        if not stmt_src or not led_src:
            rec_status = "INDEPENDENCE_UNVERIFIED"
            is_indep = False
            lineage_notes.append("Missing source identity for statement or ledger.")
        elif stmt_src == led_src:
            rec_status = "INDEPENDENCE_UNVERIFIED"
            is_indep = False
            lineage_notes.append("Statement and ledger share identical source identity.")
        elif attestation is None:
            # Caller asserted independence with different names, but supplied no verified lineage attestation!
            if matched:
                rec_status = "NUMERICALLY_MATCHED_INDEPENDENCE_UNVERIFIED"
            else:
                rec_status = "INDEPENDENT_RECONCILIATION_BREAKS"
            is_indep = False
            lineage_notes.append("Caller claimed independent reconciliation without verifiable IndependentLedgerAttestation.")
        else:
            # Rigorous lineage attestation verification
            conflict = False
            if attestation.ledger_source_id != led_src:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    f"Attestation ledger_source_id '{attestation.ledger_source_id}' does not match '{led_src}'."
                )
                conflict = True
            elif statement_raw_sha256 and attestation.artifact_sha256 == statement_raw_sha256:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    "Attestation artifact SHA256 matches statement raw content SHA256 (self-origin masquerade)."
                )
                conflict = True
            elif attestation.origin_system.upper() in {"SELF", "STATEMENT_DERIVATION", "STATEMENT_SYNTHETIC_DERIVATION"}:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    f"Attestation origin_system '{attestation.origin_system}' indicates non-independent statement derivation."
                )
                conflict = True
            elif snapshot.as_of != attestation.as_of:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    f"Incompatible as-of dates: snapshot is {snapshot.as_of.isoformat()} but attestation is {attestation.as_of.isoformat()}."
                )
                conflict = True
            elif ledger.as_of is not None and ledger.as_of != snapshot.as_of:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    f"Incompatible as-of dates: snapshot is {snapshot.as_of.isoformat()} but ledger is {ledger.as_of.isoformat()}."
                )
                conflict = True
            elif getattr(snapshot, "account_id", None) and attestation.account_id and snapshot.account_id != attestation.account_id:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    f"Conflicting account identities: snapshot '{snapshot.account_id}' vs attestation '{attestation.account_id}'."
                )
                conflict = True
            elif getattr(ledger, "account_id", None) and attestation.account_id and ledger.account_id != attestation.account_id:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    f"Conflicting account identities: ledger '{ledger.account_id}' vs attestation '{attestation.account_id}'."
                )
                conflict = True
            elif attestation.head_sha256 != ledger.head_sha256:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    f"Ledger head SHA mismatch: expected {attestation.head_sha256[:16]}, got {ledger.head_sha256[:16]}."
                )
                conflict = True
            elif attestation.entry_count != ledger.entry_count:
                rec_status = "SOURCE_LINEAGE_CONFLICT"
                lineage_notes.append(
                    f"Ledger entry count mismatch: expected {attestation.entry_count}, got {ledger.entry_count}."
                )
                conflict = True

            if conflict:
                is_indep = False
            elif matched:
                rec_status = "INDEPENDENT_RECONCILIATION_MATCHED"
                is_indep = True
                lineage_notes.append(
                    f"Verified independent ledger from '{attestation.origin_system}' [{attestation.lineage_ref}]."
                )
            else:
                rec_status = "INDEPENDENT_RECONCILIATION_BREAKS"
                is_indep = True
                lineage_notes.append(
                    f"Verified independent ledger from '{attestation.origin_system}' [{attestation.lineage_ref}] with breaks."
                )
    else:
        is_indep = False
        if matched:
            rec_status = "SELF_CONSISTENCY_VERIFIED"
            lineage_notes.append("Statement reconciled against self-derived ledger.")
        else:
            rec_status = "SELF_CONSISTENCY_BREAKS"
            lineage_notes.append("Self-consistency breaks detected between statement and self-derived ledger.")

    return ReconciliationResult(
        matched=matched,
        breaks=breaks,
        statement_cash={k: _fmt(v) for k, v in snap_cash.items()},
        ledger_cash={k: _fmt(v) for k, v in led_cash.items()},
        status=rec_status,
        is_independent=is_indep,
        statement_source_id=statement_source_id,
        ledger_source_id=ledger_source_id,
        attestation=attestation,
        lineage_notes=tuple(lineage_notes),
    )


def format_reconciliation_report(result: ReconciliationResult) -> str:
    """Generate a deterministic human-readable text report for operator review."""
    lines: List[str] = ["=== PPDS RECONCILIATION REPORT ==="]
    mode_str = "INDEPENDENT RECONCILIATION" if result.is_independent else "SELF-CONSISTENCY CHECK"
    lines.append(f"Verification Mode: {mode_str}")
    lines.append(f"Reconciliation Status: {result.status}")
    if result.statement_source_id or result.ledger_source_id:
        lines.append(
            f"Sources: Statement='{result.statement_source_id or 'UNKNOWN'}' vs "
            f"Ledger='{result.ledger_source_id or 'UNKNOWN'}'"
        )
    if result.attestation:
        lines.append(
            f"Attestation Origin: {result.attestation.origin_system} [{result.attestation.lineage_ref}]"
        )
    status_str = "MATCHED (NO BREAKS)" if result.matched else f"BREAKS DETECTED ({len(result.breaks)} breaks)"
    lines.append(f"Result: {status_str}")
    if result.lineage_notes:
        lines.append("Lineage Notes:")
        for note in result.lineage_notes:
            lines.append(f"  - {note}")
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

