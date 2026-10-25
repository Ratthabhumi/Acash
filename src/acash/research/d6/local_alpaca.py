"""Convert Alpaca historical-bar and corporate-action JSON pages to LOCAL_EXPLORATORY CSV rows.

Pure functions (no network). Daily bar timestamps must be NY-local midnight; the
session is the NY calendar date. Dividend ``rate`` is per share as of the ex-date.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Tuple
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError

NY = ZoneInfo("America/New_York")


def _require(item: Mapping[str, Any], key: str, where: str) -> Any:
    value = item.get(key)
    if value is None or value == "":
        raise DataContractError(f"ALPACA_FIELD_MISSING: {where} {key}.")
    return value


def bar_rows(pages: Iterable[Mapping[str, Any]], symbols: Iterable[str]) -> List[Dict[str, str]]:
    wanted = set(symbols)
    rows: List[Dict[str, str]] = []
    for page in pages:
        bars = page.get("bars")
        if not isinstance(bars, dict):
            raise DataContractError("ALPACA_BARS_NOT_A_SYMBOL_MAP.")
        for sym, items in bars.items():
            if sym not in wanted:
                raise DataContractError(f"ALPACA_UNREQUESTED_SYMBOL: {sym}.")
            for item in items or ():
                stamp = datetime.fromisoformat(str(_require(item, "t", sym)).replace("Z", "+00:00"))
                local = stamp.astimezone(NY)
                if local.time() != time(0, 0):
                    raise DataContractError(f"ALPACA_DAILY_BAR_NOT_NY_MIDNIGHT: {sym} {stamp.isoformat()}.")
                rows.append(
                    {
                        "symbol": sym,
                        "session": local.date().isoformat(),
                        "open": str(Decimal(str(_require(item, "o", sym)))),
                        "close": str(Decimal(str(_require(item, "c", sym)))),
                        "adjustment": "raw",
                    }
                )
    rows.sort(key=lambda r: (r["symbol"], r["session"]))
    return rows


def corporate_action_rows(
    pages: Iterable[Mapping[str, Any]], symbols: Iterable[str], *, impute_missing_payable: bool = False
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Map actions to rows. A missing payable date raises unless ``impute_missing_payable``.

    Imputation sets payable = ex-date + the symbol's largest observed provider lag
    (conservative: the receivable stays unspendable longest) and labels the row.
    """
    wanted = set(symbols)
    distributions: List[Dict[str, str]] = []
    splits: List[Dict[str, str]] = []
    for page in pages:
        actions = page.get("corporate_actions")
        if not isinstance(actions, dict):
            raise DataContractError("ALPACA_CORPORATE_ACTIONS_MISSING.")
        unsupported = set(actions) - {"cash_dividends", "forward_splits", "reverse_splits"}
        if any(actions[k] for k in unsupported):
            raise DataContractError(f"ALPACA_UNSUPPORTED_ACTION_TYPES: {sorted(unsupported)}.")
        for item in actions.get("cash_dividends") or ():
            sym = str(_require(item, "symbol", "cash_dividend"))
            if sym not in wanted:
                raise DataContractError(f"ALPACA_UNREQUESTED_SYMBOL: {sym}.")
            if item.get("foreign"):
                raise DataContractError(f"ALPACA_FOREIGN_DIVIDEND_UNSUPPORTED: {sym} {item.get('ex_date')}.")
            if not item.get("payable_date") and not impute_missing_payable:
                _require(item, "payable_date", sym)
            distributions.append(
                {
                    "symbol": sym,
                    "ex_date": str(_require(item, "ex_date", sym)),
                    "payable_date": str(item.get("payable_date") or ""),
                    "gross_amount": str(Decimal(str(_require(item, "rate", sym)))),
                    "distribution_type": "SPECIAL_CASH" if item.get("special") else "DIVIDEND_CASH",
                    "payable_date_source": "PROVIDER" if item.get("payable_date") else "",
                    "_id": str(item.get("id") or ""),
                }
            )
        for kind in ("forward_splits", "reverse_splits"):
            for item in actions.get(kind) or ():
                sym = str(_require(item, "symbol", kind))
                if sym not in wanted:
                    raise DataContractError(f"ALPACA_UNREQUESTED_SYMBOL: {sym}.")
                new = Decimal(str(_require(item, "new_rate", sym)))
                old = Decimal(str(_require(item, "old_rate", sym)))
                if new <= 0 or old <= 0:
                    raise DataContractError(f"ALPACA_BAD_SPLIT_RATE: {sym}.")
                splits.append(
                    {"symbol": sym, "session": str(_require(item, "ex_date", sym)), "ratio": str(new / old)}
                )
    lags: Dict[str, int] = {}
    for row in distributions:
        if row["payable_date_source"] == "PROVIDER":
            lag = (date.fromisoformat(row["payable_date"]) - date.fromisoformat(row["ex_date"])).days
            lags[row["symbol"]] = max(lag, lags.get(row["symbol"], lag))
    for row in distributions:
        if not row["payable_date_source"]:
            if row["symbol"] not in lags:
                raise DataContractError(f"ALPACA_NO_OBSERVED_PAYABLE_LAG: {row['symbol']}; cannot impute.")
            lag = lags[row["symbol"]]
            row["payable_date"] = (date.fromisoformat(row["ex_date"]) + timedelta(days=lag)).isoformat()
            row["payable_date_source"] = f"IMPUTED_EX_PLUS_{lag}D"
    # Same-day distinct provider events (e.g. dividend + capital gain) stay separate,
    # each tagged with its provider id so the ledger key (ex_date, type) is unique.
    groups: Dict[Tuple[str, str, str], List[Dict[str, str]]] = {}
    for row in distributions:
        groups.setdefault((row["symbol"], row["ex_date"], row["distribution_type"]), []).append(row)
    for key, members in groups.items():
        if len(members) > 1:
            ids = [m["_id"] for m in members]
            if not all(ids) or len(set(ids)) != len(ids):
                raise DataContractError(f"ALPACA_DUPLICATE_EVENT_WITHOUT_DISTINCT_ID: {key}.")
            for m in members:
                m["distribution_type"] = f"{m['distribution_type']}:{m['_id'][:8]}"
    for row in distributions:
        del row["_id"]
    distributions.sort(key=lambda r: (r["symbol"], r["ex_date"], r["distribution_type"]))
    splits.sort(key=lambda r: (r["symbol"], r["session"]))
    return distributions, splits
