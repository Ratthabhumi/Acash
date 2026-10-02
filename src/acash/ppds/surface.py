"""PPDS read-only skeleton: decision surface renderer (text/JSON).

Read-only projection only: positions, exposure, reconciliation status. This
module contains NO order controls, NO endpoints, NO credentials, and performs
NO mutation of its inputs.
"""

from __future__ import annotations

from typing import Any, Dict, List

from acash.ppds.exposure import ExposureLine
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.reconcile import ReconciliationResult


def render_read_only_surface(
    ledger: NormalizedPortfolioLedger,
    reconciliation: ReconciliationResult,
    exposures: List[ExposureLine],
) -> Dict[str, Any]:
    """Render a JSON-serializable read-only decision surface."""
    return {
        "surface_version": 1,
        "entry_count": ledger.entry_count,
        "head_sha256": ledger.head_sha256,
        "cash_by_currency": {
            currency: str(amount)
            for currency, amount in sorted(ledger.cash_by_currency().items())
        },
        "quantity_by_symbol": {
            symbol: str(quantity)
            for symbol, quantity in sorted(ledger.quantity_by_symbol().items())
        },
        "reconciliation_matched": reconciliation.matched,
        "reconciliation_breaks": [
            {
                "scope": item.scope,
                "key": item.key,
                "statement_value": item.statement_value,
                "ledger_value": item.ledger_value,
            }
            for item in reconciliation.breaks
        ],
        "exposures": [
            {"key": line.key, "market_value": line.market_value, "weight": line.weight}
            for line in exposures
        ],
        "order_controls": None,
    }
