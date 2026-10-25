"""Synthetic tests for the corporate-action source ledger."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.corporate_action_ledger import (
    LedgerCell,
    SourceStatus,
    coverage_report,
    parse_distribution_rows,
    require_complete_coverage,
)

REF = "SYNTHETIC_ISSUER_TABLE"
ROWS = [
    {"ex_date": "2024-03-21", "payable_date": "2024-03-26", "gross_amount": "1.5429"},
    {"ex_date": "2024-06-28", "payable_date": "2024-07-02", "gross_amount": "1.7835"},
]


def test_parse_produces_canonical_records() -> None:
    recs = parse_distribution_rows(ROWS, symbol="VOO", source_ref=REF)
    assert [r.gross_amount for r in recs] == [Decimal("1.5429"), Decimal("1.7835")]
    assert recs[0].event_id == f"{REF}#0" and recs[1].payable_date == date(2024, 7, 2)


@pytest.mark.parametrize(
    "row",
    [
        {"ex_date": "2024-03-21", "payable_date": "2024-03-26"},
        {"ex_date": "21/03/2024", "payable_date": "2024-03-26", "gross_amount": "1"},
        {"ex_date": "2024-03-21", "payable_date": "2024-03-26", "gross_amount": "abc"},
        {"ex_date": "2024-03-21", "payable_date": "2024-03-20", "gross_amount": "1"},
        {"ex_date": "2024-03-21", "payable_date": "2024-03-26", "gross_amount": "0"},
        {"ex_date": "2024-03-21", "payable_date": "2024-03-26", "gross_amount": "NaN"},
    ],
    ids=["missing_amount", "non_iso_date", "bad_decimal", "payable_before_ex", "zero", "nan"],
)
def test_malformed_rows_fail_closed(row: dict[str, str]) -> None:
    with pytest.raises(DataContractError):
        parse_distribution_rows([row], symbol="VOO", source_ref=REF)


def test_duplicate_event_and_missing_source_ref_fail_closed() -> None:
    with pytest.raises(DataContractError, match="LEDGER_DUPLICATE_EVENT"):
        parse_distribution_rows([ROWS[0], ROWS[0]], symbol="VOO", source_ref=REF)
    with pytest.raises(DataContractError, match="LEDGER_SOURCE_REF_MISSING"):
        parse_distribution_rows(ROWS, symbol="VOO", source_ref=" ")


def test_cell_status_contract() -> None:
    recs = tuple(parse_distribution_rows(ROWS, symbol="VOO", source_ref=REF))
    with pytest.raises(DataContractError, match="EXTRACTED_WITHOUT_RECORDS"):
        LedgerCell("VOO", 2024, SourceStatus.PRIMARY_SOURCE_EXTRACTED, REF)
    with pytest.raises(DataContractError, match="RECORDS_WITHOUT_EXTRACTED_STATUS"):
        LedgerCell("VOO", 2024, SourceStatus.SOURCE_IDENTIFIED_NOT_EXTRACTED, REF, recs)
    with pytest.raises(DataContractError, match="RECORD_OUTSIDE_CELL"):
        LedgerCell("VOO", 2023, SourceStatus.PRIMARY_SOURCE_EXTRACTED, REF, recs)
    with pytest.raises(DataContractError, match="SOURCE_REF_MISSING"):
        LedgerCell("BIL", 2024, SourceStatus.SOURCE_IDENTIFIED_NOT_EXTRACTED, "")


def test_coverage_never_claims_unextracted_years() -> None:
    recs = tuple(parse_distribution_rows(ROWS, symbol="VOO", source_ref=REF))
    cells = [
        LedgerCell("VOO", 2024, SourceStatus.PRIMARY_SOURCE_EXTRACTED, REF, recs),
        LedgerCell("BIL", 2024, SourceStatus.SOURCE_IDENTIFIED_NOT_EXTRACTED, "SSGA_BIL_DIST_PAGE"),
        LedgerCell("GLD", 2024, SourceStatus.NO_CASH_DISTRIBUTION_ENTITLEMENT, "GLD_TRUST_PROSPECTUS"),
    ]
    report = coverage_report(cells, symbols=["VOO", "BIL", "GLD"], years=[2024, 2025])
    assert report["complete"] is False
    assert report["cells_complete"] == 2
    assert ("BIL", 2024, "SOURCE_IDENTIFIED_NOT_EXTRACTED") in report["missing"]  # type: ignore[operator]
    assert ("VOO", 2025, "UNKNOWN") in report["missing"]  # type: ignore[operator]
    with pytest.raises(DataContractError, match="LEDGER_COVERAGE_INCOMPLETE"):
        require_complete_coverage(cells, symbols=["VOO", "BIL", "GLD"], years=[2024, 2025])
    require_complete_coverage(cells, symbols=["VOO", "GLD"], years=[2024])


def test_duplicate_cell_fails_closed() -> None:
    cell = LedgerCell("BIL", 2024, SourceStatus.UNKNOWN, "")
    with pytest.raises(DataContractError, match="LEDGER_DUPLICATE_CELL"):
        coverage_report([cell, cell], symbols=["BIL"], years=[2024])
