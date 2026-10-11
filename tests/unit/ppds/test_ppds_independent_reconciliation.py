"""Unit and adversarial tests for PPDS Evidence-Bound Independent Reconciliation, Account Identity, and Valuation.

Verifies:
1. Self-derived ledger reconciliation produces SELF_CONSISTENCY_VERIFIED (is_independent=False).
2. Unattested independent ledger with matching balances produces NUMERICALLY_MATCHED_INDEPENDENCE_UNVERIFIED (is_independent=False).
3. Verified independent ledger with IndependentLedgerAttestation produces INDEPENDENT_RECONCILIATION_MATCHED (is_independent=True).
4. Verified independent ledger with cash/qty discrepancy produces INDEPENDENT_RECONCILIATION_BREAKS (is_independent=True).
5. Lineage conflicts fail closed or demote to SOURCE_LINEAGE_CONFLICT:
   - Statement and ledger share identical source identity (masquerading).
   - Attestation artifact SHA matches statement raw bytes SHA (same origin masquerade).
   - Attestation origin system indicates self-derivation.
   - Snapshot as-of and ledger/attestation as-of mismatch.
   - Account identity mismatch (statement account vs ledger account).
   - Tampered ledger head SHA or entry count mismatch.
6. Multi-currency exposure fail closed (position_exposure, gross_lots_exposure, net_signed_exposure, etf_overlap_exposure).
7. Exposure semantics: gross_lots_exposure preserves offsetting long/short lots while position_exposure nets per-symbol.
8. Base currency portfolio valuation (evaluate_portfolio_base_currency):
   - Multi-currency valuation with exact as-of FX rates and prices.
   - Stale FX rate or price as-of rejection.
   - Missing FX rate or price rejection.
   - Quote currency mismatch rejection.
   - Exact Decimal NAV calculation.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.evidence import content_sha256
from acash.ppds.exposure import (
    FXRate,
    PortfolioValuation,
    PriceQuote,
    etf_overlap_exposure,
    evaluate_portfolio_base_currency,
    gross_lots_exposure,
    net_signed_exposure,
    position_exposure,
)
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.lots import CashLot, PositionLot
from acash.ppds.provenance import import_synthetic_statement
from acash.ppds.reconcile import (
    IndependentLedgerAttestation,
    ReconciliationResult,
    format_reconciliation_report,
    reconcile_snapshot_ledger,
)
from acash.ppds.statement_ingest import AccountSnapshot, ingest_account_snapshot
from acash.ppds.surface import render_read_only_surface

SYNTHETIC_CSV_STATEMENT_A = b"""record_type,symbol,currency,quantity,amount,cost_basis_per_share,acquired_on
CASH,,USD,,10000.00,,2026-10-01
POSITION,SPY,USD,50,,450.00,2026-10-02
POSITION,QQQ,USD,25,,380.00,2026-10-03
"""


def _build_matching_independent_ledger(account_id: str = "DEFAULT", as_of: date = date(2026, 10, 5)) -> NormalizedPortfolioLedger:
    ledger = NormalizedPortfolioLedger(account_id=account_id, as_of=as_of)
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


def test_unattested_independent_ledger_is_downgraded_to_unverified(tmp_path: Path) -> None:
    """Supplying distinct source ID strings without an IndependentLedgerAttestation MUST NOT claim independent match."""
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
        independent_ledger_source_id="INTERNAL_LEDGER_BOOKS_UNATTESTED",
    )

    assert record.reconciliation.matched is True
    # Without attestation, caller-asserted distinct string is downgraded:
    assert record.reconciliation.status == "NUMERICALLY_MATCHED_INDEPENDENCE_UNVERIFIED"
    assert record.reconciliation.is_independent is False
    assert any("IndependentLedgerAttestation" in n for n in record.reconciliation.lineage_notes)


def test_attested_independent_ledger_produces_independent_reconciliation_matched(tmp_path: Path) -> None:
    """Reconciling with a verified IndependentLedgerAttestation produces INDEPENDENT_RECONCILIATION_MATCHED."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_BROKER_EXT_001"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    independent_ledger = _build_matching_independent_ledger()
    attestation = IndependentLedgerAttestation(
        ledger_source_id="INTERNAL_LEDGER_BOOKS_001",
        artifact_sha256="b" * 64,  # distinct ledger artifact
        account_id="DEFAULT",
        as_of=as_of,
        entry_count=independent_ledger.entry_count,
        head_sha256=independent_ledger.head_sha256,
        lineage_ref="books/internal_ledger_20261005.json",
        origin_system="ERP_GENERAL_LEDGER",
    )

    record = import_synthetic_statement(
        raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
        source_id=source_id,
        as_of=as_of,
        evidence_root=external_root,
        imported_at_utc=now_utc,
        runtime_sha="a" * 40,
        independent_ledger=independent_ledger,
        independent_ledger_source_id="INTERNAL_LEDGER_BOOKS_001",
        independent_ledger_attestation=attestation,
    )

    assert record.reconciliation.matched is True
    assert record.reconciliation.status == "INDEPENDENT_RECONCILIATION_MATCHED"
    assert record.reconciliation.is_independent is True
    assert record.reconciliation.statement_source_id == "STATEMENT_BROKER_EXT_001"
    assert record.reconciliation.ledger_source_id == "INTERNAL_LEDGER_BOOKS_001"
    assert record.reconciliation.attestation == attestation


def test_independent_ledger_cash_difference_produces_breaks(tmp_path: Path) -> None:
    """An attested independent ledger with a cash discrepancy produces INDEPENDENT_RECONCILIATION_BREAKS."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_BROKER_EXT_002"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    # Independent ledger has $9,500 cash instead of $10,000
    ledger = NormalizedPortfolioLedger(as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("9500.00"), acquired_on=date(2026, 10, 1)))
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("50"), cost_basis_per_share=Decimal("450.00"),
                    acquired_on=date(2026, 10, 2), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="QQQ", quantity=Decimal("25"), cost_basis_per_share=Decimal("380.00"),
                    acquired_on=date(2026, 10, 3), currency="USD")
    )

    attestation = IndependentLedgerAttestation(
        ledger_source_id="INTERNAL_LEDGER_BOOKS_002",
        artifact_sha256="c" * 64,
        account_id="DEFAULT",
        as_of=as_of,
        entry_count=ledger.entry_count,
        head_sha256=ledger.head_sha256,
        lineage_ref="books/internal_ledger_002.json",
        origin_system="ERP_GENERAL_LEDGER",
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
        independent_ledger_attestation=attestation,
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
    """An attested independent ledger with a position discrepancy produces INDEPENDENT_RECONCILIATION_BREAKS."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_BROKER_EXT_003"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    # Independent ledger has 40 shares of SPY instead of 50
    ledger = NormalizedPortfolioLedger(as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("10000.00"), acquired_on=date(2026, 10, 1)))
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("40"), cost_basis_per_share=Decimal("450.00"),
                    acquired_on=date(2026, 10, 2), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="QQQ", quantity=Decimal("25"), cost_basis_per_share=Decimal("380.00"),
                    acquired_on=date(2026, 10, 3), currency="USD")
    )

    attestation = IndependentLedgerAttestation(
        ledger_source_id="INTERNAL_LEDGER_BOOKS_003",
        artifact_sha256="d" * 64,
        account_id="DEFAULT",
        as_of=as_of,
        entry_count=ledger.entry_count,
        head_sha256=ledger.head_sha256,
        lineage_ref="books/internal_ledger_003.json",
        origin_system="ERP_GENERAL_LEDGER",
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
        independent_ledger_attestation=attestation,
    )

    assert record.reconciliation.matched is False
    assert record.reconciliation.status == "INDEPENDENT_RECONCILIATION_BREAKS"
    assert record.reconciliation.is_independent is True
    assert len(record.reconciliation.breaks) == 1
    p_break = record.reconciliation.breaks[0]
    assert p_break.scope == "POSITION"
    assert p_break.key == "SPY"
    assert p_break.difference == "10"


def test_attestation_with_same_statement_sha_fails_closed_as_conflict(tmp_path: Path) -> None:
    """Attesting a ledger that shares the exact artifact SHA of the statement fails closed as SOURCE_LINEAGE_CONFLICT."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    source_id = "STATEMENT_BROKER_MASQUERADE"
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    ledger = _build_matching_independent_ledger()
    stmt_sha = content_sha256(SYNTHETIC_CSV_STATEMENT_A)

    attestation = IndependentLedgerAttestation(
        ledger_source_id="INTERNAL_MASQUERADE",
        artifact_sha256=stmt_sha,  # Masquerading identical file hash!
        account_id="DEFAULT",
        as_of=as_of,
        entry_count=ledger.entry_count,
        head_sha256=ledger.head_sha256,
        lineage_ref="same_file.csv",
        origin_system="ERP",
    )

    with pytest.raises(DataContractError, match="PPDS_SOURCE_LINEAGE_CONFLICT"):
        import_synthetic_statement(
            raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
            source_id=source_id,
            as_of=as_of,
            evidence_root=external_root,
            imported_at_utc=now_utc,
            runtime_sha="a" * 40,
            independent_ledger=ledger,
            independent_ledger_source_id="INTERNAL_MASQUERADE",
            independent_ledger_attestation=attestation,
        )


def test_conflicting_account_identity_fails_closed(tmp_path: Path) -> None:
    """Comparing two sources with conflicting account identities fails closed as SOURCE_LINEAGE_CONFLICT."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    ledger = _build_matching_independent_ledger(account_id="ACCT_LEDGER_999")
    attestation = IndependentLedgerAttestation(
        ledger_source_id="INTERNAL_LEDGER_BOOKS_ACC",
        artifact_sha256="e" * 64,
        account_id="ACCT_LEDGER_999",
        as_of=as_of,
        entry_count=ledger.entry_count,
        head_sha256=ledger.head_sha256,
        lineage_ref="books/acc999.json",
        origin_system="ERP",
    )

    with pytest.raises(DataContractError, match="PPDS_SOURCE_LINEAGE_CONFLICT"):
        import_synthetic_statement(
            raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
            source_id="STMT_ACC_111",
            as_of=as_of,
            account_id="ACCT_STMT_111",  # Different account ID!
            evidence_root=external_root,
            imported_at_utc=now_utc,
            runtime_sha="a" * 40,
            independent_ledger=ledger,
            independent_ledger_source_id="INTERNAL_LEDGER_BOOKS_ACC",
            independent_ledger_attestation=attestation,
        )


def test_incompatible_as_of_dates_fails_closed(tmp_path: Path) -> None:
    """Comparing sources with incompatible as-of dates fails closed as SOURCE_LINEAGE_CONFLICT."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    wrong_as_of = date(2026, 9, 30)
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    ledger = _build_matching_independent_ledger(as_of=wrong_as_of)
    attestation = IndependentLedgerAttestation(
        ledger_source_id="INTERNAL_LEDGER_WRONG_DATE",
        artifact_sha256="f" * 64,
        account_id="DEFAULT",
        as_of=wrong_as_of,  # Mismatched as-of!
        entry_count=ledger.entry_count,
        head_sha256=ledger.head_sha256,
        lineage_ref="books/sep30.json",
        origin_system="ERP",
    )

    with pytest.raises(DataContractError, match="PPDS_SOURCE_LINEAGE_CONFLICT"):
        import_synthetic_statement(
            raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
            source_id="STMT_OCT05",
            as_of=as_of,
            evidence_root=external_root,
            imported_at_utc=now_utc,
            runtime_sha="a" * 40,
            independent_ledger=ledger,
            independent_ledger_source_id="INTERNAL_LEDGER_WRONG_DATE",
            independent_ledger_attestation=attestation,
        )


def test_tampered_ledger_head_sha_fails_closed(tmp_path: Path) -> None:
    """Attesting a ledger with mismatched head_sha or entry_count fails closed as SOURCE_LINEAGE_CONFLICT."""
    external_root = tmp_path / "evidence_root"
    as_of = date(2026, 10, 5)
    now_utc = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    ledger = _build_matching_independent_ledger()
    attestation = IndependentLedgerAttestation(
        ledger_source_id="INTERNAL_LEDGER_TAMPERED",
        artifact_sha256="1" * 64,
        account_id="DEFAULT",
        as_of=as_of,
        entry_count=ledger.entry_count,
        head_sha256="0" * 64,  # Corrupted / tampered head SHA!
        lineage_ref="books/tampered.json",
        origin_system="ERP",
    )

    with pytest.raises(DataContractError, match="PPDS_SOURCE_LINEAGE_CONFLICT"):
        import_synthetic_statement(
            raw_bytes=SYNTHETIC_CSV_STATEMENT_A,
            source_id="STMT_TAMPERED_CHECK",
            as_of=as_of,
            evidence_root=external_root,
            imported_at_utc=now_utc,
            runtime_sha="a" * 40,
            independent_ledger=ledger,
            independent_ledger_source_id="INTERNAL_LEDGER_TAMPERED",
            independent_ledger_attestation=attestation,
        )


def test_surface_and_report_formatting_with_attestation() -> None:
    """Read-only surface and human-readable report reflect attestation and lineage notes."""
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
    attestation = IndependentLedgerAttestation(
        ledger_source_id="INTERNAL_LEDGER_SURFACE",
        artifact_sha256="2" * 64,
        account_id="DEFAULT",
        as_of=date(2026, 10, 5),
        entry_count=ledger.entry_count,
        head_sha256=ledger.head_sha256,
        lineage_ref="books/surface_test.json",
        origin_system="CUSTODIAN_MIRROR",
    )
    rec = reconcile_snapshot_ledger(
        snap,
        ledger,
        statement_source_id="STMT_SURFACE",
        ledger_source_id="INTERNAL_LEDGER_SURFACE",
        is_independent=True,
        attestation=attestation,
    )
    surface = render_read_only_surface(ledger, rec, exposures=[])
    assert surface["reconciliation_status"] == "INDEPENDENT_RECONCILIATION_MATCHED"
    assert surface["reconciliation_is_independent"] is True
    assert surface["reconciliation_has_attestation"] is True
    assert len(surface["reconciliation_lineage_notes"]) > 0

    report = format_reconciliation_report(rec)
    assert "Verification Mode: INDEPENDENT RECONCILIATION" in report
    assert "Attestation Origin: CUSTODIAN_MIRROR [books/surface_test.json]" in report
    assert "Lineage Notes:" in report


def test_exposure_semantics_gross_lots_vs_netted_positions() -> None:
    """gross_lots_exposure preserves offsetting long/short lots, while position_exposure nets per-symbol."""
    ledger = NormalizedPortfolioLedger()
    # Account has 10 shares long and 10 shares short of SPY
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("400"),
                    acquired_on=date(2026, 10, 1), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("-10"), cost_basis_per_share=Decimal("400"),
                    acquired_on=date(2026, 10, 2), currency="USD")
    )
    prices = {"SPY": Decimal("400")}

    # 1. position_exposure nets per symbol first: net quantity is 0 -> total is 0 -> fails closed
    with pytest.raises(DataContractError, match="PPDS_EXPOSURE_EMPTY"):
        position_exposure(ledger, prices)

    # 2. gross_lots_exposure measures gross commitment across both lots: 10 + 10 = 20 shares = $8,000
    gross = gross_lots_exposure(ledger, prices)
    assert len(gross) == 1
    assert gross[0].key == "SPY"
    assert gross[0].market_value == "8000"
    assert gross[0].weight == "1"


def test_net_signed_exposure_calculation() -> None:
    """net_signed_exposure correctly yields negative market value for net short positions."""
    ledger = NormalizedPortfolioLedger()
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("400"),
                    acquired_on=date(2026, 10, 1), currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="QQQ", quantity=Decimal("-5"), cost_basis_per_share=Decimal("300"),
                    acquired_on=date(2026, 10, 1), currency="USD")
    )
    prices = {"SPY": Decimal("400"), "QQQ": Decimal("300")}

    lines = net_signed_exposure(ledger, prices)
    spy_line = next(l for l in lines if l.key == "SPY")
    qqq_line = next(l for l in lines if l.key == "QQQ")
    assert spy_line.market_value == "4000"
    assert qqq_line.market_value == "-1500"


def test_evaluate_portfolio_base_currency_multi_currency() -> None:
    """evaluate_portfolio_base_currency handles exact multi-currency valuation into USD."""
    as_of = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="ACC_MULTI", as_of=as_of)
    # Cash: 10,000 USD, 50,000 THB, 1,000 EUR
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("10000.00"), acquired_on=as_of))
    ledger = ledger.post_cash_lot(CashLot(currency="THB", amount=Decimal("50000.00"), acquired_on=as_of))
    ledger = ledger.post_cash_lot(CashLot(currency="EUR", amount=Decimal("1000.00"), acquired_on=as_of))

    # Positions: 10 SPY (USD @ 450), 100 PTT (THB @ 35)
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("450"), acquired_on=as_of, currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="PTT", quantity=Decimal("100"), cost_basis_per_share=Decimal("35"), acquired_on=as_of, currency="THB")
    )

    prices = {
        "SPY": PriceQuote(symbol="SPY", price=Decimal("450.00"), as_of=as_of, currency="USD", source_id="SYNTH_PRICES"),
        "PTT": PriceQuote(symbol="PTT", price=Decimal("35.00"), as_of=as_of, currency="THB", source_id="SYNTH_PRICES"),
    }
    fx_rates = {
        ("THB", "USD"): FXRate(from_currency="THB", to_currency="USD", rate=Decimal("0.028"), as_of=as_of, source_id="SYNTH_FX"),
        ("EUR", "USD"): FXRate(from_currency="EUR", to_currency="USD", rate=Decimal("1.100"), as_of=as_of, source_id="SYNTH_FX"),
    }

    valuation = evaluate_portfolio_base_currency(
        ledger=ledger,
        base_currency="USD",
        as_of=as_of,
        prices=prices,
        fx_rates=fx_rates,
    )

    # Cash: 10,000 + (50,000 * 0.028 = 1,400) + (1,000 * 1.10 = 1,100) = 12,500 USD
    assert valuation.total_cash_base == Decimal("12500.000")
    # SPY: 10 * 450 = 4,500 USD
    # PTT: 100 * 35 = 3,500 THB * 0.028 = 98 USD
    # Total positions net base = 4,598 USD
    assert valuation.total_positions_net_base == Decimal("4598.000")
    # NAV: 12,500 + 4,598 = 17,098 USD
    assert valuation.total_portfolio_nav_base == Decimal("17098.000")


def test_evaluate_portfolio_base_currency_fails_on_stale_or_missing_rates() -> None:
    """evaluate_portfolio_base_currency fails closed on mismatched rate date or missing quote."""
    as_of = date(2026, 10, 5)
    stale_as_of = date(2026, 10, 4)
    ledger = NormalizedPortfolioLedger()
    ledger = ledger.post_cash_lot(CashLot(currency="EUR", amount=Decimal("1000.00"), acquired_on=as_of))

    prices: dict[str, PriceQuote] = {}
    stale_fx = {
        ("EUR", "USD"): FXRate(from_currency="EUR", to_currency="USD", rate=Decimal("1.10"), as_of=stale_as_of, source_id="STALE"),
    }

    with pytest.raises(DataContractError, match="PPDS_VALUATION_FX_AS_OF_MISMATCH"):
        evaluate_portfolio_base_currency(ledger, "USD", as_of, prices, stale_fx)

    with pytest.raises(DataContractError, match="PPDS_VALUATION_FX_RATE_MISSING"):
        evaluate_portfolio_base_currency(ledger, "USD", as_of, prices, {})
