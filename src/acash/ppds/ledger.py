"""PPDS read-only skeleton: append-only hash-chained normalized ledger.

The ledger is immutable: every post returns a NEW ledger with an extended
hash chain. No mutation, no deletion, no orders, no capital movement.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Tuple

from acash.core.serialization import CanonicalConfigSerializer
from acash.ppds.lots import CashLot, PositionLot

LEDGER_SCHEMA_VERSION: int = 1
GENESIS_SHA256: str = "0" * 64


def _entry_sha256(prev_sha: str, kind: str, payload: object) -> str:
    canonical = CanonicalConfigSerializer.to_canonical_json(
        {"prev": prev_sha, "kind": kind, "payload": _payload_to_json(payload)}
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _payload_to_json(payload: object) -> object:
    if isinstance(payload, CashLot):
        return {
            "currency": payload.currency,
            "amount": str(payload.amount),
            "acquired_on": payload.acquired_on.isoformat(),
        }
    if isinstance(payload, PositionLot):
        return {
            "symbol": payload.symbol,
            "quantity": str(payload.quantity),
            "cost_basis_per_share": str(payload.cost_basis_per_share),
            "acquired_on": payload.acquired_on.isoformat(),
            "currency": payload.currency,
        }
    raise TypeError(f"PPDS unsupported ledger payload: {type(payload).__name__}")


@dataclass(frozen=True)
class NormalizedPortfolioLedger:
    """Append-only normalized portfolio ledger (synthetic fixtures only)."""

    cash_lots: Tuple[CashLot, ...] = ()
    position_lots: Tuple[PositionLot, ...] = ()
    head_sha256: str = GENESIS_SHA256
    entry_count: int = 0

    def post_cash_lot(self, lot: CashLot) -> "NormalizedPortfolioLedger":
        head = _entry_sha256(self.head_sha256, "CASH_LOT", lot)
        return NormalizedPortfolioLedger(
            cash_lots=self.cash_lots + (lot,),
            position_lots=self.position_lots,
            head_sha256=head,
            entry_count=self.entry_count + 1,
        )

    def post_position_lot(self, lot: PositionLot) -> "NormalizedPortfolioLedger":
        head = _entry_sha256(self.head_sha256, "POSITION_LOT", lot)
        return NormalizedPortfolioLedger(
            cash_lots=self.cash_lots,
            position_lots=self.position_lots + (lot,),
            head_sha256=head,
            entry_count=self.entry_count + 1,
        )

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
