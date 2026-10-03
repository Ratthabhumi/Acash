"""PPDS read-only skeleton: statement-vs-ledger reconciliation (exact Decimal).

Reports match/mismatch with exact equality — no tolerance, no silent
rounding. Any break fails the reconciliation (it never mutates either side).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List

from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.statement_ingest import AccountSnapshot


@dataclass(frozen=True)
class ReconciliationBreak:
    scope: str
    key: str
    statement_value: str
    ledger_value: str


@dataclass(frozen=True)
class ReconciliationResult:
    matched: bool
    breaks: List[ReconciliationBreak]
    statement_cash: Dict[str, str]
    ledger_cash: Dict[str, str]


def _fmt(amount: Decimal) -> str:
    return str(amount)


def reconcile_snapshot_ledger(
    snapshot: AccountSnapshot, ledger: NormalizedPortfolioLedger
) -> ReconciliationResult:
    """Reconcile a statement snapshot against the normalized ledger exactly."""
    breaks: List[ReconciliationBreak] = []
    snap_cash = snapshot.cash_by_currency()
    led_cash = ledger.cash_by_currency()
    for currency in sorted(set(snap_cash) | set(led_cash)):
        left = snap_cash.get(currency, Decimal("0"))
        right = led_cash.get(currency, Decimal("0"))
        if left != right:
            breaks.append(ReconciliationBreak(
                scope="CASH", key=currency,
                statement_value=_fmt(left), ledger_value=_fmt(right),
            ))
    snap_qty = snapshot.quantity_by_symbol()
    led_qty = ledger.quantity_by_symbol()
    for symbol in sorted(set(snap_qty) | set(led_qty)):
        left = snap_qty.get(symbol, Decimal("0"))
        right = led_qty.get(symbol, Decimal("0"))
        if left != right:
            breaks.append(ReconciliationBreak(
                scope="POSITION", key=symbol,
                statement_value=_fmt(left), ledger_value=_fmt(right),
            ))
    return ReconciliationResult(
        matched=not breaks,
        breaks=breaks,
        statement_cash={k: _fmt(v) for k, v in snap_cash.items()},
        ledger_cash={k: _fmt(v) for k, v in led_cash.items()},
    )
