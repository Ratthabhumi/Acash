"""Corporate-action source ledger: provenance and completeness for D6 corporate actions.

The ledger records *where* each symbol-year comes from and how far it has been
verified. Extraction and completeness are separate facts:

- ``SOURCE_EXTRACTED_PARTIAL`` / ``SOURCE_EXTRACTED_COVERAGE_UNVERIFIED`` prove
  only that rows were parsed; they are never complete.
- ``CENSUS_CLAIM_STRUCTURALLY_VALID`` requires ``CensusEvidence`` (export scope,
  full calendar-year window, year binding, reported row count equal to parsed
  rows, fund identity, reconciled event types, SHA-256 values, reviewer distinct
  from the acquisition operator, retrospective vintage). Expected
  monthly/quarterly cadence is never proof.
- ``NO_CASH_DISTRIBUTION_ENTITLEMENT`` (e.g. GLD) settles the cash-distribution
  dimension only. The split census is a separate dimension that always needs its
  own ``CensusEvidence``.

``CensusEvidence`` is caller-supplied metadata and is only a *structural claim*.
``assess_census_trust`` grades it: ``SOURCE_BYTES_RECONCILED`` needs the actual
source bytes (hash match plus exact record re-derivation). Identity
authentication, independent review and admission need an independently
anchored admission (D5 trust anchors), which this ledger never infers from
strings; with ``D5_ADMISSION_TRUST_ANCHORS`` empty they are unreachable.

Records reuse the canonical ``EtfDistributionRecord``.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError, DomainError
from acash.data.contracts.etf_fx_benchmark import (
    DistributionShareBasis,
    EtfDistributionRecord,
)
from acash.data.qualification.lane_b_d5_rehearsal import D5_ADMISSION_TRUST_ANCHORS

LEDGER_SCHEMA = "ACASH_CORPORATE_ACTION_SOURCE_LEDGER_V3"
REQUIRED_ROW_FIELDS: Tuple[str, ...] = ("ex_date", "payable_date", "gross_amount")
RETROSPECTIVE_VINTAGE = "RETRIEVED_NOW_PIT_UNKNOWN"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SourceStatus(str, Enum):
    SOURCE_IDENTIFIED = "SOURCE_IDENTIFIED"
    SOURCE_EXTRACTED_PARTIAL = "SOURCE_EXTRACTED_PARTIAL"
    SOURCE_EXTRACTED_COVERAGE_UNVERIFIED = "SOURCE_EXTRACTED_COVERAGE_UNVERIFIED"
    CENSUS_CLAIM_STRUCTURALLY_VALID = "CENSUS_CLAIM_STRUCTURALLY_VALID"
    NO_CASH_DISTRIBUTION_ENTITLEMENT = "NO_CASH_DISTRIBUTION_ENTITLEMENT"
    UNKNOWN = "UNKNOWN"


class CensusTrustLevel(str, Enum):
    STRUCTURAL_CENSUS_CHECK_PASSED = "STRUCTURAL_CENSUS_CHECK_PASSED"
    SOURCE_BYTES_RECONCILED = "SOURCE_BYTES_RECONCILED"
    SOURCE_IDENTITY_AUTHENTICATED = "SOURCE_IDENTITY_AUTHENTICATED"
    INDEPENDENT_CENSUS_REVIEWED = "INDEPENDENT_CENSUS_REVIEWED"
    CENSUS_ADMITTED = "CENSUS_ADMITTED"


_EXTRACTED = (SourceStatus.SOURCE_EXTRACTED_PARTIAL, SourceStatus.SOURCE_EXTRACTED_COVERAGE_UNVERIFIED)


@dataclass(frozen=True)
class CensusEvidence:
    """Caller-supplied structural claim that one symbol-year census is complete."""

    fund_symbol: str
    fund_identifier: str
    cell_year: int
    source_scope: str
    covered_start: date
    covered_end: date
    reported_row_count: int
    export_or_pagination_proof: str
    event_types_reconciled: Tuple[str, ...]
    evidence_sha256: Tuple[str, ...]
    acquisition_operator: str
    reviewer: str
    vintage_limitation: str

    def validate_for(self, symbol: str, year: int, row_count: int, event_types: set[str]) -> None:
        where = f"{symbol} {year}"
        if self.fund_symbol != symbol or not self.fund_identifier.strip():
            raise DataContractError(f"CENSUS_FUND_IDENTITY_MISMATCH: {where}.")
        if self.cell_year != year:
            raise DataContractError(f"CENSUS_YEAR_BINDING_MISMATCH: {where} bound to {self.cell_year}.")
        if self.vintage_limitation != RETROSPECTIVE_VINTAGE:
            raise DataContractError(f"CENSUS_PIT_CLAIM_UNSUPPORTED: {where}; no vintage verifier exists.")
        if not self.acquisition_operator.strip():
            raise DataContractError(f"CENSUS_FIELD_MISSING: {where} acquisition_operator.")
        if self.reviewer.strip().casefold() == self.acquisition_operator.strip().casefold():
            raise DataContractError(f"CENSUS_SELF_APPROVAL: {where}.")
        if self.covered_start > date(year, 1, 1) or self.covered_end < date(year, 12, 31):
            raise DataContractError(f"CENSUS_WINDOW_DOES_NOT_COVER_YEAR: {where}.")
        if type(self.reported_row_count) is not int or self.reported_row_count != row_count:
            raise DataContractError(
                f"CENSUS_ROW_COUNT_MISMATCH: {where} reported {self.reported_row_count} parsed {row_count}."
            )
        if not event_types <= set(self.event_types_reconciled):
            raise DataContractError(f"CENSUS_EVENT_TYPES_UNRECONCILED: {where}.")
        if not self.evidence_sha256 or not all(_SHA256.match(h) for h in self.evidence_sha256):
            raise DataContractError(f"CENSUS_EVIDENCE_HASH_INVALID: {where}.")
        for name in ("source_scope", "export_or_pagination_proof", "reviewer"):
            if not str(getattr(self, name)).strip():
                raise DataContractError(f"CENSUS_FIELD_MISSING: {where} {name}.")


@dataclass(frozen=True)
class LedgerCell:
    symbol: str
    year: int
    status: SourceStatus
    source_ref: str
    records: Tuple[EtfDistributionRecord, ...] = ()
    census: Optional[CensusEvidence] = None
    split_census: Optional[CensusEvidence] = None

    def __post_init__(self) -> None:
        where = f"{self.symbol} {self.year}"
        if not self.source_ref.strip() and self.status is not SourceStatus.UNKNOWN:
            raise DataContractError(f"LEDGER_SOURCE_REF_MISSING: {where}.")
        if self.status in _EXTRACTED and not self.records:
            raise DataContractError(f"LEDGER_EXTRACTED_WITHOUT_RECORDS: {where}.")
        if self.records and self.status not in (*_EXTRACTED, SourceStatus.CENSUS_CLAIM_STRUCTURALLY_VALID):
            raise DataContractError(f"LEDGER_RECORDS_WITHOUT_EXTRACTED_STATUS: {where} {self.status.value}.")
        seen: set[Tuple[date, str]] = set()
        for rec in self.records:
            if rec.symbol != self.symbol or rec.ex_date.year != self.year:
                raise DataContractError(f"LEDGER_RECORD_OUTSIDE_CELL: {rec.symbol} {rec.ex_date}.")
            key = (rec.ex_date, rec.distribution_type)
            if key in seen:
                raise DataContractError(f"LEDGER_DUPLICATE_EVENT: {where} {key}.")
            seen.add(key)
        if self.status is SourceStatus.CENSUS_CLAIM_STRUCTURALLY_VALID:
            if self.census is None:
                raise DataContractError(f"CENSUS_EVIDENCE_REQUIRED: {where}.")
            self.census.validate_for(
                self.symbol, self.year, len(self.records), {r.distribution_type for r in self.records}
            )
        elif self.census is not None:
            raise DataContractError(f"CENSUS_EVIDENCE_WITHOUT_CENSUS_STATUS: {where}.")
        if self.split_census is not None:
            self.split_census.validate_for(
                self.symbol, self.year, self.split_census.reported_row_count, {"SPLIT"}
            )

    @property
    def cash_complete(self) -> bool:
        return self.status in (
            SourceStatus.CENSUS_CLAIM_STRUCTURALLY_VALID,
            SourceStatus.NO_CASH_DISTRIBUTION_ENTITLEMENT,
        )

    @property
    def split_complete(self) -> bool:
        return self.split_census is not None

    @property
    def complete(self) -> bool:
        return self.cash_complete and self.split_complete


def parse_distribution_rows(
    rows: Sequence[Mapping[str, str]], *, symbol: str, source_ref: str
) -> List[EtfDistributionRecord]:
    """Parse issuer-style rows (ISO dates, decimal strings) into canonical records."""
    if not source_ref.strip():
        raise DataContractError("LEDGER_SOURCE_REF_MISSING.")
    records: List[EtfDistributionRecord] = []
    seen: set[Tuple[date, str]] = set()
    for index, row in enumerate(rows):
        missing = [f for f in REQUIRED_ROW_FIELDS if not str(row.get(f, "")).strip()]
        if missing:
            raise DataContractError(f"LEDGER_ROW_FIELD_MISSING: row {index} {missing}.")
        try:
            ex_date = date.fromisoformat(row["ex_date"].strip())
            payable = date.fromisoformat(row["payable_date"].strip())
            gross = Decimal(row["gross_amount"].strip())
        except (ValueError, InvalidOperation) as exc:
            raise DataContractError(f"LEDGER_ROW_UNPARSEABLE: row {index}: {exc}.") from exc
        kind = row.get("distribution_type", "DIVIDEND_CASH").strip() or "DIVIDEND_CASH"
        if (ex_date, kind) in seen:
            raise DataContractError(f"LEDGER_DUPLICATE_EVENT: {symbol} {ex_date} {kind}.")
        seen.add((ex_date, kind))
        try:
            records.append(
                EtfDistributionRecord(
                    symbol=symbol,
                    ex_date=ex_date,
                    payable_date=payable,
                    gross_amount=gross,
                    distribution_type=kind,
                    event_id=f"{source_ref}#{index}",
                    share_basis=DistributionShareBasis.POST_SPLIT,
                )
            )
        except (DomainError, ValueError) as exc:
            raise DataContractError(f"LEDGER_ROW_INVALID: row {index}: {exc}.") from exc
    return records


def coverage_report(
    cells: Sequence[LedgerCell], *, symbols: Sequence[str], years: Sequence[int]
) -> Dict[str, object]:
    """Genuine coverage matrix plus missing-source list over the requested grid."""
    index: Dict[Tuple[str, int], LedgerCell] = {}
    for cell in cells:
        key = (cell.symbol, cell.year)
        if key in index:
            raise DataContractError(f"LEDGER_DUPLICATE_CELL: {key}.")
        index[key] = cell
    matrix: Dict[str, Dict[int, str]] = {}
    missing: List[Tuple[str, int, str]] = []
    split_missing: List[Tuple[str, int]] = []
    for sym in symbols:
        matrix[sym] = {}
        for year in years:
            found = index.get((sym, year))
            status = found.status if found is not None else SourceStatus.UNKNOWN
            matrix[sym][year] = status.value
            if found is None or not found.cash_complete:
                missing.append((sym, year, status.value))
            if found is None or not found.split_complete:
                split_missing.append((sym, year))
    requested = len(symbols) * len(years)
    return {
        "schema": LEDGER_SCHEMA,
        "matrix": matrix,
        "missing": missing,
        "split_missing": split_missing,
        "complete": not missing and not split_missing,
        "trust_ceiling": CensusTrustLevel.STRUCTURAL_CENSUS_CHECK_PASSED.value,
        "cells_requested": requested,
        "cash_cells_complete": requested - len(missing),
        "split_cells_complete": requested - len(split_missing),
    }


def require_complete_coverage(
    cells: Sequence[LedgerCell], *, symbols: Sequence[str], years: Sequence[int]
) -> None:
    report = coverage_report(cells, symbols=symbols, years=years)
    if not report["complete"]:
        raise DataContractError(
            f"LEDGER_COVERAGE_INCOMPLETE: cash {report['cash_cells_complete']}/{report['cells_requested']}, "
            f"split {report['split_cells_complete']}/{report['cells_requested']}; "
            f"first missing {report['missing'][:3]}."  # type: ignore[index]
        )


CENSUS_SOURCE_COLUMNS: Tuple[str, ...] = (
    "symbol", "fund_identifier", "ex_date", "payable_date", "gross_amount", "distribution_type",
)


def parse_census_source_bytes(
    payload: bytes, *, symbol: str, fund_identifier: str, source_ref: str
) -> List[EtfDistributionRecord]:
    """Re-derive records from captured source bytes (UTF-8 CSV with identity columns)."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DataContractError(f"CENSUS_SOURCE_NOT_UTF8: {source_ref}.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != CENSUS_SOURCE_COLUMNS:
        raise DataContractError(f"CENSUS_SOURCE_COLUMNS_MISMATCH: {source_ref}.")
    rows = list(reader)
    for row in rows:
        if row["symbol"] != symbol or row["fund_identifier"] != fund_identifier:
            raise DataContractError(f"CENSUS_SOURCE_IDENTITY_MISMATCH: {source_ref}.")
    return parse_distribution_rows(rows, symbol=symbol, source_ref=source_ref)


def _economics(records: Sequence[EtfDistributionRecord]) -> List[Tuple[date, date, Decimal, str]]:
    return sorted((r.ex_date, r.payable_date, r.gross_amount, r.distribution_type) for r in records)


def assess_census_trust(
    cell: LedgerCell, *, source_artifacts: Optional[Mapping[str, bytes]] = None
) -> Tuple[CensusTrustLevel, Tuple[str, ...]]:
    """Grade a cash-distribution census claim; never above what evidence proves.

    Returns the highest level reached and the reasons higher levels were not
    reached. Byte reconciliation failures raise (tampered or unrelated evidence).
    """
    if cell.status is not SourceStatus.CENSUS_CLAIM_STRUCTURALLY_VALID or cell.census is None:
        raise DataContractError(f"CENSUS_NOT_CLAIMED: {cell.symbol} {cell.year} {cell.status.value}.")
    census = cell.census
    level = CensusTrustLevel.STRUCTURAL_CENSUS_CHECK_PASSED
    gaps: List[str] = []
    if source_artifacts is None:
        gaps.append("SOURCE_BYTES_NOT_PROVIDED")
    else:
        derived: List[EtfDistributionRecord] = []
        for digest in census.evidence_sha256:
            payload = source_artifacts.get(digest)
            if payload is None or hashlib.sha256(payload).hexdigest() != digest:
                raise DataContractError(f"CENSUS_SOURCE_BYTES_MISMATCH: {cell.symbol} {cell.year} {digest[:12]}.")
            derived.extend(
                parse_census_source_bytes(
                    payload, symbol=cell.symbol, fund_identifier=census.fund_identifier, source_ref=digest
                )
            )
        in_year = [r for r in derived if r.ex_date.year == cell.year]
        if _economics(in_year) != _economics(cell.records):
            raise DataContractError(f"CENSUS_RECORDS_NOT_RECONCILED: {cell.symbol} {cell.year}.")
        level = CensusTrustLevel.SOURCE_BYTES_RECONCILED
    if not D5_ADMISSION_TRUST_ANCHORS:
        gaps.append("D5_ADMISSION_TRUST_ANCHORS_EMPTY")
    gaps.append("INDEPENDENT_CENSUS_ADMISSION_VERIFIER_NOT_IMPLEMENTED")
    return level, tuple(gaps)
