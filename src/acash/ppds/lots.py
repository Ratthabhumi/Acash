"""PPDS read-only skeleton: exact lot models (synthetic fixtures only).

No broker access. No real statements. No capital movement. All quantities
are exact Decimals; malformed or non-finite inputs fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from acash.core.domain.exceptions import DataContractError


def _exact_decimal(raw: Any, context: str) -> Decimal:
    if raw is None or isinstance(raw, bool) or isinstance(raw, float):
        raise DataContractError(f"PPDS_MALFORMED_DECIMAL: {context}.")
    try:
        value = Decimal(str(raw)) if not isinstance(raw, Decimal) else raw
    except (InvalidOperation, ValueError, TypeError, ArithmeticError) as exc:
        raise DataContractError(f"PPDS_MALFORMED_DECIMAL: {context}.") from exc
    if not value.is_finite():
        raise DataContractError(f"PPDS_NONFINITE_DECIMAL: {context}.")
    return value


def _exact_date(raw: Any, context: str) -> date:
    try:
        return date.fromisoformat(str(raw))
    except (ValueError, TypeError) as exc:
        raise DataContractError(f"PPDS_MALFORMED_DATE: {context}.") from exc


@dataclass(frozen=True)
class CashLot:
    """One exact cash balance lot (synthetic)."""

    currency: str
    amount: Decimal
    acquired_on: date

    @classmethod
    def from_mapping(cls, doc: Mapping[str, Any]) -> "CashLot":
        if not isinstance(doc, Mapping):
            raise DataContractError("PPDS_CASH_LOT_NOT_A_MAPPING.")
        currency = str(doc.get("currency") or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise DataContractError("PPDS_CASH_CURRENCY_INVALID.")
        return cls(
            currency=currency,
            amount=_exact_decimal(doc.get("amount"), "cash amount"),
            acquired_on=_exact_date(doc.get("acquired_on"), "cash acquired_on"),
        )


@dataclass(frozen=True)
class PositionLot:
    """One exact position lot (synthetic; quantity may be negative for shorts)."""

    symbol: str
    quantity: Decimal
    cost_basis_per_share: Decimal
    acquired_on: date
    currency: str

    @classmethod
    def from_mapping(cls, doc: Mapping[str, Any]) -> "PositionLot":
        if not isinstance(doc, Mapping):
            raise DataContractError("PPDS_POSITION_LOT_NOT_A_MAPPING.")
        symbol = str(doc.get("symbol") or "").strip().upper()
        if not symbol:
            raise DataContractError("PPDS_POSITION_SYMBOL_INVALID.")
        quantity = _exact_decimal(doc.get("quantity"), "position quantity")
        if quantity == Decimal("0"):
            raise DataContractError("PPDS_POSITION_ZERO_QUANTITY.")
        currency = str(doc.get("currency") or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise DataContractError("PPDS_POSITION_CURRENCY_INVALID.")
        return cls(
            symbol=symbol,
            quantity=quantity,
            cost_basis_per_share=_exact_decimal(
                doc.get("cost_basis_per_share"), "position cost basis"
            ),
            acquired_on=_exact_date(doc.get("acquired_on"), "position acquired_on"),
            currency=currency,
        )
