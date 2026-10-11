"""Unit and adversarial tests for PPDS explainable reconciliation diagnostics."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.lots import CashLot, PositionLot
from acash.ppds.reconcile import (
    ReconciliationBreak,
    StatementTransaction,
    format_reconciliation_report,
    reconcile_snapshot_ledger,
)
from acash.ppds.statement_ingest import AccountSnapshot
from acash.ppds.surface import render_read_only_surface


def _snapshot() -> AccountSnapshot:
    return AccountSnapshot(
        as_of=date(2026, 9, 30),
        cash_lots=(CashLot(currency="USD", amount=Decimal("100150.00"), acquired_on=date(2026, 9, 30)),),
        position_lots=(
            PositionLot(
                symbol="ACWI", quantity=Decimal("510"),
                cost_basis_per_share=Decimal("100"),
                acquired_on=date(2026, 9, 30), currency="USD"
            ),
        ),
    )


def _ledger() -> NormalizedPortfolioLedger:
    ledger = NormalizedPortfolioLedger()
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("100000.00"), acquired_on=date(2026, 9, 1)))
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ACWI", quantity=Decimal("500"),
                    cost_basis_per_share=Decimal("100"),
                    acquired_on=date(2026, 9, 1), currency="USD")
    )
    return ledger


def test_exact_match_no_breaks() -> None:
    snap = AccountSnapshot(
        as_of=date(2026, 9, 30),
        cash_lots=(CashLot(currency="USD", amount=Decimal("100000.00"), acquired_on=date(2026, 9, 30)),),
        position_lots=(
            PositionLot(symbol="ACWI", quantity=Decimal("500"),
                        cost_basis_per_share=Decimal("100"),
                        acquired_on=date(2026, 9, 30), currency="USD"),
        ),
    )
    result = reconcile_snapshot_ledger(snap, _ledger())
    assert result.matched is True
    assert len(result.breaks) == 0
    report = format_reconciliation_report(result)
    assert "MATCHED (NO BREAKS)" in report
    assert "All cash balances and position quantities match ledger perfectly" in report


def test_cash_break_unexplained_without_transactions() -> None:
    result = reconcile_snapshot_ledger(_snapshot(), _ledger(), transactions=())
    assert result.matched is False
    cash_break = next(b for b in result.breaks if b.scope == "CASH" and b.key == "USD")
    assert cash_break.difference == "150.00"
    assert cash_break.status == "UNEXPLAINED_MISMATCH"
    assert cash_break.explanation is None
    assert cash_break.evidence_refs == ()


def test_cash_break_supported_by_dividend_transaction() -> None:
    tx = StatementTransaction(
        transaction_id="TX_DIV_001",
        transaction_date=date(2026, 9, 29),
        record_type="DIVIDEND",
        currency="USD",
        amount=Decimal("150.00"),
        symbol="ACWI",
        description="Quarterly Dividend Distribution",
    )
    result = reconcile_snapshot_ledger(_snapshot(), _ledger(), transactions=(tx,))
    assert result.matched is False
    cash_break = next(b for b in result.breaks if b.scope == "CASH" and b.key == "USD")
    assert cash_break.difference == "150.00"
    assert cash_break.status == "SUPPORTED_EXPLANATION"
    assert "TX_DIV_001" in (cash_break.explanation or "")
    assert "DIVIDEND" in (cash_break.explanation or "")
    assert cash_break.evidence_refs == ("TX_DIV_001",)


def test_cash_break_ambiguous_transactions_is_possible_cause() -> None:
    tx1 = StatementTransaction(
        transaction_id="TX_DIV_001",
        transaction_date=date(2026, 9, 29),
        record_type="DIVIDEND",
        currency="USD",
        amount=Decimal("150.00"),
    )
    tx2 = StatementTransaction(
        transaction_id="TX_TRANSFER_002",
        transaction_date=date(2026, 9, 29),
        record_type="TRANSFER",
        currency="USD",
        amount=Decimal("150.00"),
    )
    result = reconcile_snapshot_ledger(_snapshot(), _ledger(), transactions=(tx1, tx2))
    cash_break = next(b for b in result.breaks if b.scope == "CASH" and b.key == "USD")
    assert cash_break.status == "POSSIBLE_CAUSE"
    assert cash_break.evidence_refs == ("TX_DIV_001", "TX_TRANSFER_002")
    assert "Multiple candidate transactions" in (cash_break.explanation or "")


def test_position_break_supported_by_trade_transaction() -> None:
    tx = StatementTransaction(
        transaction_id="TX_BUY_001",
        transaction_date=date(2026, 9, 28),
        record_type="TRADE",
        currency="USD",
        amount=Decimal("1000.00"),
        quantity=Decimal("10"),
        symbol="ACWI",
        description="Market Buy 10 shares",
    )
    result = reconcile_snapshot_ledger(_snapshot(), _ledger(), transactions=(tx,))
    pos_break = next(b for b in result.breaks if b.scope == "POSITION" and b.key == "ACWI")
    assert pos_break.difference == "10"
    assert pos_break.status == "SUPPORTED_EXPLANATION"
    assert pos_break.evidence_refs == ("TX_BUY_001",)


def test_position_break_unexplained_when_symbol_or_quantity_mismatches() -> None:
    wrong_symbol_tx = StatementTransaction(
        transaction_id="TX_WRONG_SYM",
        transaction_date=date(2026, 9, 28),
        record_type="TRADE",
        currency="USD",
        amount=Decimal("1000.00"),
        quantity=Decimal("10"),
        symbol="SPY",  # Target is ACWI
    )
    wrong_qty_tx = StatementTransaction(
        transaction_id="TX_WRONG_QTY",
        transaction_date=date(2026, 9, 28),
        record_type="TRADE",
        currency="USD",
        amount=Decimal("1000.00"),
        quantity=Decimal("9"),  # Target delta is 10
        symbol="ACWI",
    )
    result = reconcile_snapshot_ledger(_snapshot(), _ledger(), transactions=(wrong_symbol_tx, wrong_qty_tx))
    pos_break = next(b for b in result.breaks if b.scope == "POSITION" and b.key == "ACWI")
    assert pos_break.status == "UNEXPLAINED_MISMATCH"
    assert pos_break.evidence_refs == ()


def test_conflicting_currency_never_explains_cash_break() -> None:
    eur_tx = StatementTransaction(
        transaction_id="TX_EUR_001",
        transaction_date=date(2026, 9, 29),
        record_type="DIVIDEND",
        currency="EUR",  # Target delta is in USD
        amount=Decimal("150.00"),
    )
    result = reconcile_snapshot_ledger(_snapshot(), _ledger(), transactions=(eur_tx,))
    cash_break = next(b for b in result.breaks if b.scope == "CASH" and b.key == "USD")
    assert cash_break.status == "UNEXPLAINED_MISMATCH"
    assert cash_break.evidence_refs == ()


def test_format_reconciliation_report_with_breaks() -> None:
    tx = StatementTransaction(
        transaction_id="TX_DIV_001",
        transaction_date=date(2026, 9, 29),
        record_type="DIVIDEND",
        currency="USD",
        amount=Decimal("150.00"),
    )
    result = reconcile_snapshot_ledger(_snapshot(), _ledger(), transactions=(tx,))
    report = format_reconciliation_report(result)
    assert "BREAKS DETECTED (2 breaks)" in report
    assert "Scope: CASH | Key: USD" in report
    assert "Diagnostic Status: SUPPORTED_EXPLANATION" in report
    assert "Evidence Refs: TX_DIV_001" in report
    assert "Scope: POSITION | Key: ACWI" in report
    assert "Diagnostic Status: UNEXPLAINED_MISMATCH" in report


def test_surface_rendering_with_diagnostic_breaks() -> None:
    tx = StatementTransaction(
        transaction_id="TX_DIV_001",
        transaction_date=date(2026, 9, 29),
        record_type="DIVIDEND",
        currency="USD",
        amount=Decimal("150.00"),
    )
    result = reconcile_snapshot_ledger(_snapshot(), _ledger(), transactions=(tx,))
    surface = render_read_only_surface(_ledger(), result, exposures=[])
    assert surface["reconciliation_matched"] is False
    assert len(surface["reconciliation_breaks"]) == 2
    cash_break = next(b for b in surface["reconciliation_breaks"] if b["scope"] == "CASH")
    assert cash_break["difference"] == "150.00"
    assert cash_break["status"] == "SUPPORTED_EXPLANATION"
    assert cash_break["evidence_refs"] == ["TX_DIV_001"]
