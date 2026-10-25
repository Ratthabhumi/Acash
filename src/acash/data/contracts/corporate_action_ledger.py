"""Corporate-action source ledger: provenance and completeness for D6 distributions.

The ledger records *where* each symbol-year of distribution history comes from
and whether it has actually been extracted. It never fabricates coverage: a
cell is complete only with status ``PRIMARY_SOURCE_EXTRACTED`` plus at least
one parsed record, or ``NO_CASH_DISTRIBUTION_ENTITLEMENT`` with zero records.
Records reuse the canonical ``EtfDistributionRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Dict, List, Mapping, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError, DomainError
from acash.data.contracts.etf_fx_benchmark import (
    DistributionShareBasis,
    EtfDistributionRecord,
)

LEDGER_SCHEMA = "ACASH_CORPORATE_ACTION_SOURCE_LEDGER_V1"
REQUIRED_ROW_FIELDS: Tuple[str, ...] = ("ex_date", "payable_date", "gross_amount")


class SourceStatus(str, Enum):
    PRIMARY_SOURCE_EXTRACTED = "PRIMARY_SOURCE_EXTRACTED"
    SOURCE_IDENTIFIED_NOT_EXTRACTED = "SOURCE_IDENTIFIED_NOT_EXTRACTED"
    NO_CASH_DISTRIBUTION_ENTITLEMENT = "NO_CASH_DISTRIBUTION_ENTITLEMENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class LedgerCell:
    symbol: str
    year: int
    status: SourceStatus
    source_ref: str
    records: Tuple[EtfDistributionRecord, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref.strip() and self.status is not SourceStatus.UNKNOWN:
            raise DataContractError(f"LEDGER_SOURCE_REF_MISSING: {self.symbol} {self.year}.")
        if self.status is SourceStatus.PRIMARY_SOURCE_EXTRACTED and not self.records:
            raise DataContractError(f"LEDGER_EXTRACTED_WITHOUT_RECORDS: {self.symbol} {self.year}.")
        if self.status is not SourceStatus.PRIMARY_SOURCE_EXTRACTED and self.records:
            raise DataContractError(
                f"LEDGER_RECORDS_WITHOUT_EXTRACTED_STATUS: {self.symbol} {self.year} {self.status.value}."
            )
        for rec in self.records:
            if rec.symbol != self.symbol or rec.ex_date.year != self.year:
                raise DataContractError(f"LEDGER_RECORD_OUTSIDE_CELL: {rec.symbol} {rec.ex_date}.")

    @property
    def complete(self) -> bool:
        return self.status in (
            SourceStatus.PRIMARY_SOURCE_EXTRACTED,
            SourceStatus.NO_CASH_DISTRIBUTION_ENTITLEMENT,
        )


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
    for sym in symbols:
        matrix[sym] = {}
        for year in years:
            found = index.get((sym, year))
            status = found.status if found is not None else SourceStatus.UNKNOWN
            matrix[sym][year] = status.value
            if found is None or not found.complete:
                missing.append((sym, year, status.value))
    return {
        "schema": LEDGER_SCHEMA,
        "matrix": matrix,
        "missing": missing,
        "complete": not missing,
        "cells_requested": len(symbols) * len(years),
        "cells_complete": len(symbols) * len(years) - len(missing),
    }


def require_complete_coverage(
    cells: Sequence[LedgerCell], *, symbols: Sequence[str], years: Sequence[int]
) -> None:
    report = coverage_report(cells, symbols=symbols, years=years)
    if not report["complete"]:
        raise DataContractError(
            f"LEDGER_COVERAGE_INCOMPLETE: {report['cells_complete']}/{report['cells_requested']} "
            f"complete; first missing {report['missing'][:3]}."  # type: ignore[index]
        )
