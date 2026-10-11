"""Unit and adversarial tests for PPDS Independent Reconciliation and Exposure Contracts.

Verifies:
1. Self-derived ledger reconciliation produces SELF_CONSISTENCY_VERIFIED (is_independent=False),
   and NEVER INDEPENDENT_RECONCILIATION_MATCHED.
2. Independent ledger matching cash and positions produces INDEPENDENT_RECONCILIATION_MATCHED (is_independent=True).
3. Independent ledger with cash difference produces INDEPENDENT_RECONCILIATION_BREAKS.
4. Independent ledger with position difference produces INDEPENDENT_RECONCILIATION_BREAKS.
5. Missing or whitespace-only source IDs demote to INDEPENDENCE_UNVERIFIED (is_independent=False).
6. Same source ID masquerading as independent source demotes to INDEPENDENCE_UNVERIFIED.
7. Surface rendering preserves reconciliation_status and reconciliation_is_independent.
8. Multi-currency position lots fail closed in position_exposure() and etf_overlap_exposure().
9. Reconcile report formatting displays verification mode and status cleanly.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.ppds.exposure import etf_overlap_exposure, position_exposure
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.lots import CashLot, PositionLot
from acash.ppds.provenance import import_synthetic_statement
from acash.ppds.reconcile import (
    ReconciliationBreak,
    ReconciliationResult,
    StatementTransaction,
    format_reconciliation_report,
    reconcile_snapshot_ledger,
)
from acash.ppds.statement_ingest import AccountSnapshot
from acash.ppds.surface import render_read_only_surface

SYNTHETIC_CSV_STATEMENT_A = b"""record_type,symbol,currency,quantity,amount,cost_basis_per_share,acquired_on
CASH,,USD,,10000.00,,2026-10-01
POSITION,SPY,USD,50,,450.00,2026-10-02
POSITION,QQQ,USD,25,,380.00,2026-10-03
"""


def _build_matching_independent_ledger() -> NormalizedPortfolioLedger:
    ledger = NormalizedPortfolioLedger()
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("10000.00"), acquired_on=date(2026, 10, 1)))
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("50"), cost_basis_per_share=Decimal("450.00"),
                    acquired_on=date(2026, 10, 2), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="QQQ", quantity=Decimal("25"), cost_basis_per_share=Decimal("380.00"),
                    acquired_on=date(2026, 10, 3), currency="USD")
    )
    return ledger


def test_self_derived_statement_is_never_classified_as_independent(tmp_path: Path) -> None:
    """A statement reconciled against its own generated ledger must be SELF_CONSISTENCY_VERIFIED."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_SYNTH_SELF"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha="a" * 40,
    )

    assert record.reconciliation.matched is True
    assert record.reconciliation.status == "SELF_CONSISTENCY_VERIFIED"
    assert record.reconciliation.is_independent is False
    assert record.reconciliation.status != "INDEPENDENT_RECONCILIATION_MATCHED"


def test_independent_ledger_matching_produces_independent_reconciliation_matched(tmp_path: Path) -> None:
    """Reconciling against an external, independent ledger with different source produces INDEPENDENT_RECONCILIATION_MATCHED."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_BROKER_EXT_001"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    independent_ledger = _build_matching_independent_ledger()

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha="a" * 40,
        independent_ledger=independent_ledger,
        independent_ledger_source_id="INTERNAL_LEDGER_BOOKS_001",
    )

    assert record.reconciliation.matched is True
    assert record.reconciliation.status == "INDEPENDENT_RECONCILIATION_MATCHED"
    assert record.reconciliation.is_independent is True
    assert record.reconciliation.statement_source_id == "STATEMENT_BROKER_EXT_001"
    assert record.reconciliation.ledger_source_id == "INTERNAL_LEDGER_BOOKS_001"


def test_independent_ledger_cash_difference_produces_breaks(tmp_path: Path) -> None:
    """An independent ledger with a cash discrepancy produces INDEPENDENT_RECONCILIATION_BREAKS."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_BROKER_EXT_002"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    # Independent ledger has $9,500 cash instead of $10,000
    ledger = NormalizedPortfolioLedger()
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("9500.00"), acquired_on=date(2026, 10, 1)))
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("50"), cost_basis_per_share=Decimal("450.00"),
                    acquired_on=date(2026, 10, 2), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="QQQ", quantity=Decimal("25"), cost_basis_per_share=Decimal("380.00"),
                    acquired_on=date(2026, 10, 3), currency="USD")
    )

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha="a" * 40,
        independent_ledger=ledger,
        independent_ledger_source_id="INTERNAL_LEDGER_BOOKS_002",
    )

    assert record.reconciliation.matched is False
    assert record.reconciliation.status == "INDEPENDENT_RECONCILIATION_BREAKS"
    assert record.reconciliation.is_independent is True
    assert len(record.reconciliation.breaks) == 1
    c_break = record.reconciliation.breaks[0]
    assert c_break.scope == "CASH"
    assert c_break.key == "USD"
    assert c_break.difference == "500.00"


def test_independent_ledger_quantity_difference_produces_breaks(tmp_path: Path) -> None:
    """An independent ledger with a position quantity discrepancy produces INDEPENDENT_RECONCILIATION_BREAKS."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_BROKER_EXT_003"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    # Independent ledger has 40 shares of SPY instead of 50
    ledger = NormalizedPortfolioLedger()
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("10000.00"), acquired_on=date(2026, 10, 1)))
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("40"), cost_basis_per_share=Decimal("450.00"),
                    acquired_on=date(2026, 10, 2), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="QQQ", quantity=Decimal("25"), cost_basis_per_share=Decimal("380.00"),
                    acquired_on=date(2026, 10, 3), currency="USD")
    )

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha="a" * 40,
        independent_ledger=ledger,
        independent_ledger_source_id="INTERNAL_LEDGER_BOOKS_003",
    )

    assert record.reconciliation.matched is False
    assert record.reconciliation.status == "INDEPENDENT_RECONCILIATION_BREAKS"
    assert record.reconciliation.is_independent is True
    assert len(record.reconciliation.breaks) == 1
    p_break = record.reconciliation.breaks[0]
    assert p_break.scope == "POSITION"
    assert p_break.key == "SPY"
    assert p_break.difference == "10"


def test_masquerading_same_source_as_independent_is_demoted(tmp_path: Path) -> None:
    """Reusing the same source ID as the ledger source ID fails independence and demotes to INDEPENDENCE_UNVERIFIED."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_SOURCE_COMMON"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    ledger = _build_matching_independent_ledger()

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha="a" * 40,
        independent_ledger=ledger,
        independent_ledger_source_id="STATEMENT_SOURCE_COMMON",  # Masquerading identical source
    )

    assert record.reconciliation.matched is True
    assert record.reconciliation.status == "INDEPENDENCE_UNVERIFIED"
    assert record.reconciliation.is_independent is False


def test_missing_or_blank_ledger_source_demotes_to_independence_unverified(tmp_path: Path) -> None:
    """Supplying an independent ledger without an authoritative source ID demotes to INDEPENDENCE_UNVERIFIED."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_BROKER_004"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    ledger = _build_matching_independent_ledger()

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha="a" * 40,
        independent_ledger=ledger,
        independent_ledger_source_id="",  # Blank ledger source
    )

    assert record.reconciliation.matched is True
    assert record.reconciliation.status == "INDEPENDENCE_UNVERIFIED"
    assert record.reconciliation.is_independent is False


def test_read_only_surface_contains_reconciliation_independence_metadata() -> None:
    """The rendered surface must expose reconciliation_status, is_independent, and provenance source IDs."""
    ledger = _build_matching_independent_ledger()
    snap = AccountSnapshot(
        as_of=date(2026, 10, 5),
        cash_lots=(CashLot(currency="USD", amount=Decimal("10000.00"), acquired_on=date(2026, 10, 1)),),
        position_lots=(
            PositionLot(symbol="SPY", quantity=Decimal("50"), cost_basis_per_share=Decimal("450.00"),
                        acquired_on=date(2026, 10, 2), currency="USD"),
            PositionLot(symbol="QQQ", quantity=Decimal("25"), cost_basis_per_share=Decimal("380.00"),
                        acquired_on=date(2026, 10, 3), currency="USD"),
        ),
    )
    rec = reconcile_snapshot_ledger(
        snap,
        ledger,
        statement_source_id="EXT_BROKER_STMT",
        ledger_source_id="INTERNAL_LEDGER",
        is_independent=True,
    )
    surface = render_read_only_surface(ledger, rec, exposures=[])
    assert surface["reconciliation_matched"] is True
    assert surface["reconciliation_status"] == "INDEPENDENT_RECONCILIATION_MATCHED"
    assert surface["reconciliation_is_independent"] is True
    assert surface["reconciliation_statement_source_id"] == "EXT_BROKER_STMT"
    assert surface["reconciliation_ledger_source_id"] == "INTERNAL_LEDGER"


def test_multi_currency_positions_fail_closed_in_position_exposure() -> None:
    """position_exposure must fail closed with PPDS_EXPOSURE_MULTI_CURRENCY when lots have mixed currencies."""
    ledger = NormalizedPortfolioLedger()
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("450"),
                    acquired_on=date(2026, 10, 1), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="PTT", quantity=Decimal("100"), cost_basis_per_share=Decimal("35"),
                    acquired_on=date(2026, 10, 1), currency="THB")
    )

    prices = {"SPY": Decimal("450"), "PTT": Decimal("35")}
    with pytest.raises(DataContractError, match="PPDS_EXPOSURE_MULTI_CURRENCY"):
        position_exposure(ledger, prices)


def test_multi_currency_positions_fail_closed_in_etf_overlap_exposure() -> None:
    """etf_overlap_exposure must fail closed with PPDS_EXPOSURE_MULTI_CURRENCY when lots have mixed currencies."""
    ledger = NormalizedPortfolioLedger()
    ledger = ledger.post_position_lot(
        PositionLot(symbol="VT", quantity=Decimal("10"), cost_basis_per_share=Decimal("100"),
                    acquired_on=date(2026, 10, 1), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SET50", quantity=Decimal("50"), cost_basis_per_share=Decimal("900"),
                    acquired_on=date(2026, 10, 1), currency="THB")
    )

    prices = {"VT": Decimal("100"), "SET50": Decimal("900"), "AAPL": Decimal("150")}
    weights = {"VT": {"AAPL": Decimal("1.0")}}

    with pytest.raises(DataContractError, match="PPDS_EXPOSURE_MULTI_CURRENCY"):
        etf_overlap_exposure(ledger, prices, weights)


def test_format_reconciliation_report_shows_mode_and_status() -> None:
    """format_reconciliation_report must display verification mode and status cleanly."""
    rec = ReconciliationResult(
        matched=True,
        breaks=[],
        statement_cash={"USD": "10000.00"},
        ledger_cash={"USD": "10000.00"},
        status="INDEPENDENT_RECONCILIATION_MATCHED",
        is_independent=True,
        statement_source_id="BROKER_STMT_A",
        ledger_source_id="LEDGER_BOOKS_B",
    )
    report = format_reconciliation_report(rec)
    assert "Verification Mode: INDEPENDENT RECONCILIATION" in report
    assert "Reconciliation Status: INDEPENDENT_RECONCILIATION_MATCHED" in report
    assert "Statement='BROKER_STMT_A'" in report
    assert "Ledger='LEDGER_BOOKS_B'" in report
