"""V29-F06: census evidence is a structural claim; trust never exceeds proven evidence."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import date

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.corporate_action_ledger import (
    CensusEvidence,
    CensusTrustLevel,
    LedgerCell,
    SourceStatus,
    assess_census_trust,
    coverage_report,
    parse_census_source_bytes,
)

HEADER = "symbol,fund_identifier,ex_date,payable_date,gross_amount,distribution_type\n"
ROWS_2024 = (
    "BIL,SYN-ID,2024-03-01,2024-03-05,0.40,DIVIDEND_CASH\n"
    "BIL,SYN-ID,2024-12-20,2024-12-27,0.10,CAPITAL_GAIN_SHORT\n"
)
SOURCE = (HEADER + ROWS_2024 + "BIL,SYN-ID,2025-01-02,2025-01-07,0.41,DIVIDEND_CASH\n").encode()
DIGEST = hashlib.sha256(SOURCE).hexdigest()


def _records(payload: bytes = SOURCE) -> tuple:  # type: ignore[type-arg]
    recs = parse_census_source_bytes(payload, symbol="BIL", fund_identifier="SYN-ID", source_ref="X")
    return tuple(r for r in recs if r.ex_date.year == 2024)


def _evidence(**overrides: object) -> CensusEvidence:
    base = CensusEvidence(
        fund_symbol="BIL", fund_identifier="SYN-ID", cell_year=2024,
        source_scope="SYNTHETIC export", covered_start=date(2016, 1, 1), covered_end=date(2025, 12, 31),
        reported_row_count=2, export_or_pagination_proof="footer count",
        event_types_reconciled=("DIVIDEND_CASH", "CAPITAL_GAIN_SHORT"), evidence_sha256=(DIGEST,),
        acquisition_operator="OPERATOR_A", reviewer="REVIEWER_B",
        vintage_limitation="RETRIEVED_NOW_PIT_UNKNOWN",
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def _cell(records: tuple = (), **overrides: object) -> LedgerCell:  # type: ignore[type-arg]
    return LedgerCell(
        "BIL", 2024, SourceStatus.CENSUS_CLAIM_STRUCTURALLY_VALID, "SYN", records or _records(),
        census=_evidence(**overrides),
    )


def test_reconciled_bytes_reach_only_source_bytes_reconciled() -> None:
    level, gaps = assess_census_trust(_cell(), source_artifacts={DIGEST: SOURCE})
    assert level is CensusTrustLevel.SOURCE_BYTES_RECONCILED
    assert "D5_ADMISSION_TRUST_ANCHORS_EMPTY" in gaps


def test_fabricated_reviewer_without_bytes_stays_structural() -> None:
    level, gaps = assess_census_trust(_cell(reviewer="Chief Independent Auditor (VERIFIED)"))
    assert level is CensusTrustLevel.STRUCTURAL_CENSUS_CHECK_PASSED
    assert "SOURCE_BYTES_NOT_PROVIDED" in gaps
    assert coverage_report([_cell()], symbols=["BIL"], years=[2024])["trust_ceiling"] == (
        "STRUCTURAL_CENSUS_CHECK_PASSED"
    )


def test_valid_looking_sha_unrelated_to_bytes_fails() -> None:
    with pytest.raises(DataContractError, match="CENSUS_SOURCE_BYTES_MISMATCH"):
        assess_census_trust(_cell(evidence_sha256=("b" * 64,)), source_artifacts={"b" * 64: SOURCE})


def test_partial_export_claiming_full_year_is_not_reconciled() -> None:
    partial = (HEADER + ROWS_2024.splitlines(keepends=True)[0]).encode()
    digest = hashlib.sha256(partial).hexdigest()
    with pytest.raises(DataContractError, match="CENSUS_RECORDS_NOT_RECONCILED"):
        assess_census_trust(_cell(evidence_sha256=(digest,)), source_artifacts={digest: partial})


def test_altered_amount_is_detected() -> None:
    altered = tuple(
        r.model_copy(update={"gross_amount": r.gross_amount + 1}) if i == 0 else r for i, r in enumerate(_records())
    )
    with pytest.raises(DataContractError, match="CENSUS_RECORDS_NOT_RECONCILED"):
        assess_census_trust(_cell(altered), source_artifacts={DIGEST: SOURCE})


def test_missing_capital_gain_event_fails_structurally() -> None:
    with pytest.raises(DataContractError, match="CENSUS_ROW_COUNT_MISMATCH"):
        _cell(_records()[:1])


def test_wrong_share_class_identity_in_source_bytes() -> None:
    other = SOURCE.replace(b"SYN-ID", b"OTHER-CLASS")
    digest = hashlib.sha256(other).hexdigest()
    with pytest.raises(DataContractError, match="CENSUS_SOURCE_IDENTITY_MISMATCH"):
        assess_census_trust(_cell(evidence_sha256=(digest,)), source_artifacts={digest: other})


def test_missing_split_census_keeps_cell_incomplete() -> None:
    assert _cell().cash_complete is True and _cell().complete is False


def test_duplicate_issuer_events_in_source_fail() -> None:
    dup = (HEADER + ROWS_2024 + ROWS_2024.splitlines(keepends=True)[0]).encode()
    with pytest.raises(DataContractError, match="LEDGER_DUPLICATE_EVENT"):
        parse_census_source_bytes(dup, symbol="BIL", fund_identifier="SYN-ID", source_ref="X")


def test_retrospective_export_cannot_claim_pit() -> None:
    with pytest.raises(DataContractError, match="CENSUS_PIT_CLAIM_UNSUPPORTED"):
        _cell(vintage_limitation="PIT_AS_PUBLISHED")


def test_completeness_decision_replayed_for_other_year_fails() -> None:
    with pytest.raises(DataContractError, match="CENSUS_YEAR_BINDING_MISMATCH"):
        _cell(cell_year=2025)


def test_self_approved_census_fails() -> None:
    with pytest.raises(DataContractError, match="CENSUS_SELF_APPROVAL"):
        _cell(reviewer=" operator_a ")


def test_non_census_cell_cannot_be_graded() -> None:
    cell = LedgerCell("BIL", 2024, SourceStatus.SOURCE_EXTRACTED_PARTIAL, "SYN", _records())
    with pytest.raises(DataContractError, match="CENSUS_NOT_CLAIMED"):
        assess_census_trust(cell)
