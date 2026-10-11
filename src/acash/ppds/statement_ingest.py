"""PPDS read-only skeleton: synthetic statement ingestion (no broker I/O).

Parses operator-supplied synthetic statements only. Real statements must
never enter the repository. Malformed rows fail closed; nothing is coerced.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.ppds.lots import CashLot, PositionLot

STATEMENT_SCHEMA_VERSION: int = 1


@dataclass(frozen=True)
class AccountSnapshot:
    """One parsed synthetic statement snapshot (read-only)."""

    as_of: date
    cash_lots: Tuple[CashLot, ...]
    position_lots: Tuple[PositionLot, ...]
    account_id: str = "DEFAULT"

    def cash_by_currency(self) -> Dict[str, Decimal]:
        totals: Dict[str, Decimal] = {}
        for lot in self.cash_lots:
            totals[lot.currency] = totals.get(lot.currency, Decimal("0")) + lot.amount
        return totals

    def quantity_by_symbol(self) -> Dict[str, Decimal]:
        totals: Dict[str, Decimal] = {}
        for lot in self.position_lots:
            totals[lot.symbol] = totals.get(lot.symbol, Decimal("0")) + lot.quantity
        return totals


def parse_statement_csv(text: str) -> List[Dict[str, Any]]:
    """Parse synthetic statement CSV text into raw row mappings."""
    if not isinstance(text, str) or not text.strip():
        raise DataContractError("PPDS_STATEMENT_EMPTY.")
    try:
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise DataContractError("PPDS_STATEMENT_NO_HEADER.")
        required = {"record_type", "symbol", "currency", "quantity", "amount",
                    "cost_basis_per_share", "acquired_on"}
        missing = required - {str(name or "").strip() for name in reader.fieldnames}
        if missing:
            raise DataContractError(
                f"PPDS_STATEMENT_MISSING_COLUMNS: {sorted(missing)}."
            )
        rows: List[Dict[str, Any]] = [dict(row) for row in reader]
        return rows
    except DataContractError:
        raise
    except Exception as exc:
        raise DataContractError(f"PPDS_STATEMENT_PARSE_FAILED: {exc}.") from exc


def ingest_account_snapshot(
    rows: Sequence[Mapping[str, Any]], as_of: date, account_id: str = "DEFAULT"
) -> AccountSnapshot:
    """Build an AccountSnapshot from parsed synthetic rows (fail closed)."""
    if not isinstance(rows, list) or not rows:
        raise DataContractError("PPDS_STATEMENT_NO_ROWS.")
    clean_account_id = str(account_id or "").strip()
    if not clean_account_id:
        raise DataContractError("PPDS_ACCOUNT_ID_INVALID: empty account_id.")

    cash_lots: List[CashLot] = []
    position_lots: List[PositionLot] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise DataContractError(f"PPDS_STATEMENT_ROW_NOT_MAPPING: {index}.")
        row_acc = row.get("account_id")
        if row_acc is not None:
            clean_row_acc = str(row_acc).strip()
            if clean_row_acc and clean_row_acc != clean_account_id:
                raise DataContractError(
                    f"PPDS_STATEMENT_ACCOUNT_ID_MISMATCH: row {index} has '{clean_row_acc}', expected '{clean_account_id}'."
                )
        kind = str(row.get("record_type") or "").strip().upper()
        if kind == "CASH":
            cash_lots.append(CashLot.from_mapping({
                "currency": row.get("currency"),
                "amount": row.get("amount"),
                "acquired_on": row.get("acquired_on"),
            }))
        elif kind == "POSITION":
            position_lots.append(PositionLot.from_mapping({
                "symbol": row.get("symbol"),
                "quantity": row.get("quantity"),
                "cost_basis_per_share": row.get("cost_basis_per_share"),
                "acquired_on": row.get("acquired_on"),
                "currency": row.get("currency"),
            }))
        else:
            raise DataContractError(
                f"PPDS_STATEMENT_UNKNOWN_RECORD_TYPE: {row.get('record_type')!r}."
            )
    return AccountSnapshot(
        as_of=as_of,
        cash_lots=tuple(cash_lots),
        position_lots=tuple(position_lots),
        account_id=clean_account_id,
    )
