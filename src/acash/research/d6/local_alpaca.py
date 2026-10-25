"""Convert Alpaca historical-bar and corporate-action JSON pages to LOCAL_EXPLORATORY CSV rows.

Pure functions (no network). Daily bar timestamps must be NY-local midnight; the
session is the NY calendar date. Dividend ``rate`` is per share as of the ex-date.

Corporate-action ``start``/``end`` filter on ``process_date``, not ``ex_date``; the
converter therefore windows by ``ex_date`` and reports every excluded event.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from acash.core.domain.exceptions import DataContractError

NY = ZoneInfo("America/New_York")
DISTRIBUTION_COLUMNS = (
    "symbol",
    "ex_date",
    "payable_date",
    "gross_amount",
    "distribution_type",
    "payable_date_source",
    "event_id",
    "process_date",
)
SPLIT_COLUMNS = ("symbol", "session", "ratio", "event_id")
PAYABLE_LAG_POLICIES = ("min", "median", "max")
_ACTION_KEYS = ("cash_dividends", "capital_gains_distributions", "forward_splits", "reverse_splits")
_SUB_TYPES = {"return_of_capital": "RETURN_OF_CAPITAL_CASH", "interest": "INTEREST_CASH"}
_GAIN_LEGS = (("long_term_rate", "CAPITAL_GAIN_LONG_TERM"), ("short_term_rate", "CAPITAL_GAIN_SHORT_TERM"))


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


@dataclass(frozen=True)
class ActionConversion:
    distributions: List[Dict[str, str]]
    splits: List[Dict[str, str]]
    excluded_outside_window: List[Dict[str, str]] = field(default_factory=list)
    cross_page_duplicates: int = 0
    observed_payable_lags: Dict[str, List[int]] = field(default_factory=dict)


def _unique_actions(pages: Iterable[Mapping[str, Any]]) -> Tuple[List[Tuple[str, Mapping[str, Any]]], int]:
    """Provider events by id. Same id twice in a page, or differing across pages, fails."""
    first: Dict[str, Tuple[str, Mapping[str, Any]]] = {}
    ordered: List[Tuple[str, Mapping[str, Any]]] = []
    repeats = 0
    for page in pages:
        actions = page.get("corporate_actions")
        if not isinstance(actions, dict):
            raise DataContractError("ALPACA_CORPORATE_ACTIONS_MISSING.")
        unsupported = sorted(k for k in actions if k not in _ACTION_KEYS and actions[k])
        if unsupported:
            raise DataContractError(f"ALPACA_UNSUPPORTED_ACTION_TYPES: {unsupported}.")
        in_page: set[str] = set()
        for kind in _ACTION_KEYS:
            for item in actions.get(kind) or ():
                event_id = str(_require(item, "id", kind))
                if event_id in in_page:
                    raise DataContractError(f"ALPACA_DUPLICATE_EVENT_IN_PAGE: {kind} {event_id}.")
                in_page.add(event_id)
                if event_id in first:
                    if first[event_id] != (kind, item):
                        raise DataContractError(f"ALPACA_CONFLICTING_REVISION: {kind} {event_id}.")
                    repeats += 1
                    continue
                first[event_id] = (kind, item)
                ordered.append((kind, item))
    return ordered, repeats


def _lag(policy: str, lags: Sequence[int]) -> int:
    if policy == "min":
        return min(lags)
    if policy == "max":
        return max(lags)
    return int(statistics.median_low(lags))


def corporate_action_rows(
    pages: Iterable[Mapping[str, Any]],
    symbols: Iterable[str],
    *,
    window: Tuple[date, date],
    payable_lag_policy: Optional[str] = None,
) -> ActionConversion:
    """Map provider events to rows; identity (``event_id``) is kept apart from economic type.

    A missing payable date raises unless ``payable_lag_policy`` is given; then payable =
    ex-date + the symbol's min / median_low / max provider-observed calendar-day lag,
    labelled in ``payable_date_source``. Imputed dates are never labelled PROVIDER.
    """
    if payable_lag_policy is not None and payable_lag_policy not in PAYABLE_LAG_POLICIES:
        raise DataContractError(f"ALPACA_UNKNOWN_PAYABLE_LAG_POLICY: {payable_lag_policy!r}.")
    start, end = window
    wanted = set(symbols)
    distributions: List[Dict[str, str]] = []
    splits: List[Dict[str, str]] = []
    excluded: List[Dict[str, str]] = []
    unique, repeats = _unique_actions(pages)
    cash_amounts: Dict[Tuple[str, str], List[Decimal]] = {}
    gain_totals: Dict[Tuple[str, str], List[Decimal]] = {}
    for kind, item in unique:
        event_id = str(item["id"])
        sym = str(_require(item, "symbol", kind))
        if sym not in wanted:
            raise DataContractError(f"ALPACA_UNREQUESTED_SYMBOL: {sym}.")
        ex_date = str(_require(item, "ex_date", sym))
        inside = start <= date.fromisoformat(ex_date) <= end
        if kind in ("forward_splits", "reverse_splits"):
            new = Decimal(str(_require(item, "new_rate", sym)))
            old = Decimal(str(_require(item, "old_rate", sym)))
            if new <= 0 or old <= 0:
                raise DataContractError(f"ALPACA_BAD_SPLIT_RATE: {sym}.")
            row = {"symbol": sym, "session": ex_date, "ratio": str(new / old), "event_id": event_id}
            (splits if inside else excluded).append(row)
            continue
        if item.get("currency") not in (None, "", "USD"):
            raise DataContractError(f"ALPACA_NON_USD_DISTRIBUTION: {sym} {ex_date}.")
        legs: List[Tuple[str, Decimal, str]] = []
        if kind == "cash_dividends":
            if item.get("foreign"):
                raise DataContractError(f"ALPACA_FOREIGN_DIVIDEND_UNSUPPORTED: {sym} {ex_date}.")
            sub_type = item.get("sub_type")
            if sub_type and sub_type not in _SUB_TYPES:
                raise DataContractError(f"ALPACA_UNKNOWN_DIVIDEND_SUB_TYPE: {sym} {sub_type!r}.")
            kind_label = (
                "SPECIAL_CASH" if item.get("special") else _SUB_TYPES[sub_type] if sub_type else "DIVIDEND_CASH"
            )
            legs.append((kind_label, Decimal(str(_require(item, "rate", sym))), event_id))
        else:
            for key, label in _GAIN_LEGS:
                if item.get(key) is None:
                    continue
                rate = Decimal(str(item[key]))
                if rate < 0:
                    raise DataContractError(f"ALPACA_BAD_CAPITAL_GAIN_RATE: {sym} {ex_date} {key}.")
                if rate > 0:
                    legs.append((label, rate, f"{event_id}#{key.removesuffix('_rate')}"))
            if not legs:
                raise DataContractError(f"ALPACA_CAPITAL_GAIN_WITHOUT_RATE: {sym} {ex_date}.")
        totals = cash_amounts if kind == "cash_dividends" else gain_totals
        totals.setdefault((sym, ex_date), []).append(sum((leg[1] for leg in legs), Decimal(0)))
        for label, rate, leg_id in legs:
            if rate <= 0:
                raise DataContractError(f"ALPACA_NONPOSITIVE_DISTRIBUTION: {sym} {ex_date}.")
            payable = str(item.get("payable_date") or "")
            row = {
                "symbol": sym,
                "ex_date": ex_date,
                "payable_date": payable,
                "gross_amount": str(rate),
                "distribution_type": label,
                "payable_date_source": "PROVIDER" if payable else "",
                "event_id": leg_id,
                "process_date": str(item.get("process_date") or ""),
            }
            (distributions if inside else excluded).append(row)

    # A capital gain may be reported as a cash dividend (as for BND 2020-12-23); one
    # also reported under the capital-gains type would otherwise be counted twice.
    for pair, gains in gain_totals.items():
        if set(gains) & set(cash_amounts.get(pair, [])):
            raise DataContractError(f"ALPACA_POSSIBLE_CROSS_TYPE_DUPLICATE: {pair[0]} {pair[1]}.")
    lags: Dict[str, List[int]] = {}
    for row in distributions:
        if row["payable_date_source"] == "PROVIDER":
            lag = (date.fromisoformat(row["payable_date"]) - date.fromisoformat(row["ex_date"])).days
            if lag < 0:
                raise DataContractError(f"ALPACA_PAYABLE_BEFORE_EX_DATE: {row['symbol']} {row['ex_date']}.")
            lags.setdefault(row["symbol"], []).append(lag)
    for row in distributions:
        if row["payable_date_source"]:
            continue
        if payable_lag_policy is None:
            raise DataContractError(f"ALPACA_FIELD_MISSING: {row['symbol']} payable_date.")
        if row["symbol"] not in lags:
            raise DataContractError(f"ALPACA_NO_OBSERVED_PAYABLE_LAG: {row['symbol']}; cannot impute.")
        lag = _lag(payable_lag_policy, lags[row["symbol"]])
        row["payable_date"] = (date.fromisoformat(row["ex_date"]) + timedelta(days=lag)).isoformat()
        row["payable_date_source"] = f"IMPUTED_EX_PLUS_{lag}D_{payable_lag_policy.upper()}_OBSERVED_LAG"
    distributions.sort(key=lambda r: (r["symbol"], r["ex_date"], r["distribution_type"], r["event_id"]))
    splits.sort(key=lambda r: (r["symbol"], r["session"]))
    return ActionConversion(
        distributions, splits, excluded, repeats, {s: sorted(v) for s, v in sorted(lags.items())}
    )


def page_record(tag: str, index: int, request_token: Optional[str], payload: bytes) -> Dict[str, Any]:
    """Manifest entry binding one raw response page to its position in a pagination chain."""
    page = json.loads(payload)
    return {
        "tag": tag,
        "index": index,
        "file": f"{tag}_page_{index:02d}.json",
        "request_page_token": request_token,
        "next_page_token": page.get("next_page_token"),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def verify_page_chain(records: Sequence[Mapping[str, Any]]) -> None:
    """Contiguous indices; each request token is the previous page's next token; no repeats."""
    by_tag: Dict[str, List[Mapping[str, Any]]] = {}
    for record in records:
        by_tag.setdefault(str(record["tag"]), []).append(record)
    for tag, chain in by_tag.items():
        seen: set[str] = set()
        previous_next: Optional[str] = None
        for position, record in enumerate(sorted(chain, key=lambda r: int(r["index"])), start=1):
            if int(record["index"]) != position:
                raise DataContractError(f"RAW_PAGE_INDEX_GAP: {tag} {record['index']}.")
            if record["request_page_token"] != previous_next:
                raise DataContractError(f"RAW_PAGE_CHAIN_BROKEN: {tag} page {position}.")
            token = record["next_page_token"]
            if token is not None:
                if token in seen:
                    raise DataContractError(f"RAW_PAGE_TOKEN_REPEATED: {tag} page {position}.")
                seen.add(token)
            previous_next = token
        if previous_next is not None:
            raise DataContractError(f"RAW_PAGE_CHAIN_INCOMPLETE: {tag} ends with a next_page_token.")


def verify_page_bytes(record: Mapping[str, Any], payload: bytes) -> Dict[str, Any]:
    if len(payload) != record["bytes"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
        raise DataContractError(f"RAW_PAGE_DIGEST_MISMATCH: {record['file']}.")
    page: Dict[str, Any] = json.loads(payload)
    if page.get("next_page_token") != record["next_page_token"]:
        raise DataContractError(f"RAW_PAGE_TOKEN_MISMATCH: {record['file']}.")
    return page
