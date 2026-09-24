"""Deterministic canonical ledger serialization and hashing."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Mapping

from acash.core.serialization import CanonicalConfigSerializer
from acash.research.hyp_009.accounting import (
    EquityRecord,
    PortfolioResult,
    execution_slippage_cost,
)
from acash.research.hyp_009.signals import MonthSignal


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return CanonicalConfigSerializer.to_canonical_json(_jsonable(dict(payload))).encode(
        "utf-8"
    )


def sha256_hex(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def signal_ledger(signals: List[MonthSignal], pending: List[MonthSignal]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for signal in signals:
        rows.append(
            {
                "decision_date": signal.decision_date.isoformat(),
                "signal_level": str(signal.signal_level),
                "sma10": str(signal.sma10),
                "state": signal.state,
                "prior_state": signal.prior_state,
                "transition": signal.transition,
            }
        )
    pending_rows = [
        {
            "decision_date": signal.decision_date.isoformat(),
            "signal_level": str(signal.signal_level),
            "sma10": str(signal.sma10),
            "state": signal.state,
            "status": "PENDING_NEXT_PARTITION_EXECUTION_NOT_EXECUTED",
        }
        for signal in pending
    ]
    return {"rows": rows, "pending_terminal": pending_rows}


def execution_ledger(result: PortfolioResult) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for trade in result.trades:
        rows.append(
            {
                "path": trade.path,
                "decision_date": trade.decision_date.isoformat()
                if trade.decision_date
                else None,
                "execution_date": trade.execution_date.isoformat(),
                "transition": trade.transition,
                "side": trade.side,
                "raw_open": str(trade.raw_open),
                "fill_price": str(trade.fill_price),
                "quantity": trade.quantity,
                "gross_notional": str(trade.gross_notional),
                "commission": str(trade.commission),
                "sec31_fee": str(trade.sec31_fee),
                "finra_taf": str(trade.finra_taf),
                "cat_fee": str(trade.cat_fee),
                "regulatory_fees_paid": str(trade.regulatory_fees_paid),
                "execution_slippage_cost": str(execution_slippage_cost(trade)),
                "cash_before": str(trade.cash_before),
                "cash_after": str(trade.cash_after),
                "shares_before": trade.shares_before,
                "shares_after": trade.shares_after,
            }
        )
    return {"path": result.path, "rows": rows}


def equity_ledger(records: List[EquityRecord], path: str) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for record in records:
        rows.append(
            {
                "date": record.session.isoformat(),
                "cash": str(record.cash),
                "shares": record.shares,
                "raw_close": str(record.raw_close),
                "market_value": str(record.market_value),
                "dividend_receivable": str(record.dividend_receivable),
                "total_equity": str(record.total_equity),
                "daily_return": str(record.daily_return)
                if record.daily_return is not None
                else None,
                "running_peak": str(record.running_peak),
                "drawdown": str(record.drawdown),
            }
        )
    return {"path": path, "rows": rows}
