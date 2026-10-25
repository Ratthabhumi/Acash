"""Synthetic tests for the corporate-action source ledger."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.corporate_action_ledger import (
    CensusEvidence,
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


def _census(symbol: str = "VOO", rows: int = 2, **overrides: object) -> CensusEvidence:
    base = CensusEvidence(
        fund_symbol=symbol,
        fund_identifier="SYNTHETIC-CUSIP",
        cell_year=2024,
        source_scope="SYNTHETIC full-history export",
        covered_start=date(2016, 1, 1),
        covered_end=date(2025, 12, 31),
        reported_row_count=rows,
        export_or_pagination_proof="single export, footer row count",
        event_types_reconciled=("DIVIDEND_CASH",),
        evidence_sha256=("a" * 64,),
        acquisition_operator="SYNTHETIC_OPERATOR",
        reviewer="SYNTHETIC_REVIEWER",
        vintage_limitation="RETRIEVED_NOW_PIT_UNKNOWN",
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def _recs() -> tuple:  # type: ignore[type-arg]
    return tuple(parse_distribution_rows(ROWS, symbol="VOO", source_ref=REF))


def test_partial_or_unverified_extraction_is_never_complete() -> None:
    for status in (SourceStatus.SOURCE_EXTRACTED_PARTIAL, SourceStatus.SOURCE_EXTRACTED_COVERAGE_UNVERIFIED):
        cell = LedgerCell("VOO", 2024, status, REF, _recs()[:1])
        assert cell.cash_complete is False and cell.complete is False


def test_cell_status_contract() -> None:
    with pytest.raises(DataContractError, match="EXTRACTED_WITHOUT_RECORDS"):
        LedgerCell("VOO", 2024, SourceStatus.SOURCE_EXTRACTED_PARTIAL, REF)
    with pytest.raises(DataContractError, match="RECORDS_WITHOUT_EXTRACTED_STATUS"):
        LedgerCell("VOO", 2024, SourceStatus.SOURCE_IDENTIFIED, REF, _recs())
    with pytest.raises(DataContractError, match="RECORD_OUTSIDE_CELL"):
        LedgerCell("VOO", 2023, SourceStatus.SOURCE_EXTRACTED_PARTIAL, REF, _recs())
    with pytest.raises(DataContractError, match="SOURCE_REF_MISSING"):
        LedgerCell("BIL", 2024, SourceStatus.SOURCE_IDENTIFIED, "")
    with pytest.raises(DataContractError, match="CENSUS_EVIDENCE_REQUIRED"):
        LedgerCell("VOO", 2024, SourceStatus.CENSUS_CLAIM_STRUCTURALLY_VALID, REF, _recs())
    with pytest.raises(DataContractError, match="CENSUS_EVIDENCE_WITHOUT_CENSUS_STATUS"):
        LedgerCell("VOO", 2024, SourceStatus.SOURCE_EXTRACTED_PARTIAL, REF, _recs(), census=_census())


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"rows": 3}, "CENSUS_ROW_COUNT_MISMATCH"),
        ({"rows": 1}, "CENSUS_ROW_COUNT_MISMATCH"),
        ({"fund_symbol": "BND"}, "CENSUS_FUND_IDENTITY_MISMATCH"),
        ({"fund_identifier": " "}, "CENSUS_FUND_IDENTITY_MISMATCH"),
        ({"covered_start": date(2024, 2, 1)}, "CENSUS_WINDOW_DOES_NOT_COVER_YEAR"),
        ({"covered_end": date(2024, 12, 30)}, "CENSUS_WINDOW_DOES_NOT_COVER_YEAR"),
        ({"event_types_reconciled": ()}, "CENSUS_EVENT_TYPES_UNRECONCILED"),
        ({"evidence_sha256": ()}, "CENSUS_EVIDENCE_HASH_INVALID"),
        ({"evidence_sha256": ("ABC",)}, "CENSUS_EVIDENCE_HASH_INVALID"),
        ({"reviewer": ""}, "CENSUS_FIELD_MISSING"),
        ({"vintage_limitation": " "}, "CENSUS_PIT_CLAIM_UNSUPPORTED"),
    ],
)
def test_census_evidence_must_prove_completeness(overrides: dict[str, object], code: str) -> None:
    rows = overrides.pop("rows", 2)
    with pytest.raises(DataContractError, match=code):
        LedgerCell(
            "VOO", 2024, SourceStatus.CENSUS_CLAIM_STRUCTURALLY_VALID, REF, _recs(),
            census=_census(rows=rows, **overrides),  # type: ignore[arg-type]
        )


def test_gld_policy_does_not_establish_split_census() -> None:
    gld = LedgerCell("GLD", 2024, SourceStatus.NO_CASH_DISTRIBUTION_ENTITLEMENT, "GLD_TRUST_PROSPECTUS")
    assert gld.cash_complete is True and gld.split_complete is False and gld.complete is False
    split_ev = _census("GLD", 0, event_types_reconciled=("SPLIT",))
    gld_full = replace(gld, split_census=split_ev)
    assert gld_full.complete is True


def test_coverage_requires_cash_and_split_census() -> None:
    voo = LedgerCell(
        "VOO", 2024, SourceStatus.CENSUS_CLAIM_STRUCTURALLY_VALID, REF, _recs(), census=_census(),
        split_census=_census(rows=0, event_types_reconciled=("SPLIT",)),
    )
    cells = [
        voo,
        LedgerCell("BIL", 2024, SourceStatus.SOURCE_IDENTIFIED, "SSGA_BIL_DIST_PAGE"),
        LedgerCell("GLD", 2024, SourceStatus.NO_CASH_DISTRIBUTION_ENTITLEMENT, "GLD_TRUST_PROSPECTUS"),
    ]
    report = coverage_report(cells, symbols=["VOO", "BIL", "GLD"], years=[2024, 2025])
    assert report["complete"] is False
    assert (report["cash_cells_complete"], report["split_cells_complete"]) == (2, 1)
    assert ("BIL", 2024, "SOURCE_IDENTIFIED") in report["missing"]  # type: ignore[operator]
    assert ("GLD", 2024) in report["split_missing"]  # type: ignore[operator]
    with pytest.raises(DataContractError, match="LEDGER_COVERAGE_INCOMPLETE"):
        require_complete_coverage(cells, symbols=["VOO", "GLD"], years=[2024])
    require_complete_coverage([voo], symbols=["VOO"], years=[2024])


def test_duplicate_cell_fails_closed() -> None:
    cell = LedgerCell("BIL", 2024, SourceStatus.UNKNOWN, "")
    with pytest.raises(DataContractError, match="LEDGER_DUPLICATE_CELL"):
        coverage_report([cell, cell], symbols=["BIL"], years=[2024])


