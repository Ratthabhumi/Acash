"""Single-session prospective shadow operations (frozen HYP_011 accounting).

Processes exactly one completed eligible session per invocation: entitlement,
payable settlement, scheduled open transaction, EOD valuation, benchmark, and
an append-only observation artifact chained by SHA-256. No network here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_009.accounting import DividendEvent
from acash.research.hyp_011.accounting import (
    SIMULATED_STARTING_AUM,
    TARGET_WEIGHTS,
    solve_rebalance,
)
from acash.research.hyp_011.shadow import (
    QUARANTINE_START,
    RECENT_STRESS_END,
    RECENT_STRESS_START,
    SCIENTIFIC_PROSPECTIVE_BOUNDARY,
    ShadowState,
)


@dataclass
class SessionMarket:
    session: date
    opens_raw: Dict[str, Decimal]
    closes_raw: Dict[str, Decimal]


@dataclass
class ShadowPortfolio:
    cash: Decimal = SIMULATED_STARTING_AUM
    holdings: Dict[str, int] = field(
        default_factory=lambda: {"ACWI": 0, "AGG": 0}
    )
    receivables: List[Tuple[date, Decimal]] = field(default_factory=list)
    peak: Decimal = SIMULATED_STARTING_AUM
    prev_equity: Decimal = SIMULATED_STARTING_AUM


@dataclass
class ShadowBenchmark:
    cash: Decimal = SIMULATED_STARTING_AUM
    shares: int = 0
    receivables: List[Tuple[date, Decimal]] = field(default_factory=list)
    peak: Decimal = SIMULATED_STARTING_AUM
    prev_equity: Decimal = SIMULATED_STARTING_AUM
    entered: bool = False


def _settle_receivables(
    cash: Decimal,
    receivables: List[Tuple[date, Decimal]],
    session: date,
) -> Tuple[Decimal, List[Tuple[date, Decimal]]]:
    outstanding: List[Tuple[date, Decimal]] = []
    for payable, amount in receivables:
        if payable <= session:
            cash += amount
        else:
            outstanding.append((payable, amount))
    return cash, outstanding


def process_strategy_session(
    portfolio: ShadowPortfolio,
    market: SessionMarket,
    dividends: Mapping[str, DividendEvent],
    is_rebalance_event: bool,
    slippage_bps: Decimal,
    fee_multiplier: int,
    path: str,
) -> Dict[str, Any]:
    """Process one session for the strategy path; returns the observation fragment."""
    session = market.session
    for sym in TARGET_WEIGHTS:
        if market.opens_raw[sym] <= Decimal("0") or market.closes_raw[sym] <= Decimal("0"):
            raise DataContractError(f"SHADOW_NONPOSITIVE_PRICE: {session} {sym}.")

    prev_holdings = dict(portfolio.holdings)
    entitlements: List[Dict[str, str]] = []
    for sym in TARGET_WEIGHTS:
        event = dividends.get(sym)
        if event is not None and prev_holdings.get(sym, 0) > 0:
            amount = Decimal(prev_holdings[sym]) * event.amount_per_share
            portfolio.receivables.append((event.payable_date, amount))
            entitlements.append(
                {"symbol": sym, "ex_date": event.ex_date.isoformat(),
                 "amount": str(amount)}
            )

    portfolio.cash, portfolio.receivables = _settle_receivables(
        portfolio.cash, portfolio.receivables, session
    )

    trades: List[Dict[str, str]] = []
    if is_rebalance_event:
        new_trades, portfolio.cash, new_holdings = solve_rebalance(
            session, portfolio.cash, portfolio.holdings, market.opens_raw,
            slippage_bps, fee_multiplier, path,
        )
        portfolio.holdings = new_holdings
        for trade in new_trades:
            trades.append(
                {
                    "side": trade.side, "quantity": str(trade.quantity),
                    "fill": str(trade.fill_price),
                    "sec31": str(trade.sec31_fee), "taf": str(trade.finra_taf),
                }
            )

    market_value = sum(
        Decimal(portfolio.holdings[s]) * market.closes_raw[s] for s in TARGET_WEIGHTS
    )
    outstanding_value = sum((a for _, a in portfolio.receivables), Decimal("0"))
    equity = portfolio.cash + market_value + outstanding_value
    if equity > portfolio.peak:
        portfolio.peak = equity
    decline = (portfolio.peak - equity) / portfolio.peak
    daily_return = equity / portfolio.prev_equity - Decimal("1")
    portfolio.prev_equity = equity
    return {
        "holdings": dict(portfolio.holdings),
        "cash": str(portfolio.cash),
        "market_value": str(market_value),
        "receivable": str(outstanding_value),
        "equity": str(equity),
        "daily_return": str(daily_return),
        "running_peak": str(portfolio.peak),
        "drawdown": str(decline),
        "entitlements": entitlements,
        "trades": trades,
    }


def process_benchmark_session(
    benchmark: ShadowBenchmark,
    session: date,
    spy_open: Decimal,
    spy_close: Decimal,
    dividend: Optional[DividendEvent],
    slippage_bps: Decimal,
) -> Dict[str, Any]:
    """Process one session for the independent SPY benchmark leg (full accounting)."""
    from acash.research.hyp_009.accounting import adverse_fill

    if spy_open <= Decimal("0") or spy_close <= Decimal("0"):
        raise DataContractError(f"SHADOW_BENCH_NONPOSITIVE_PRICE: {session}.")
    held_at_prior_close = benchmark.entered
    entry: Dict[str, str] = {}
    if not benchmark.entered:
        fill = adverse_fill(spy_open, "BUY", slippage_bps)
        shares = int(benchmark.cash // fill)
        if shares <= 0:
            raise DataContractError(f"SHADOW_BENCH_ZERO_SHARES: {session}.")
        benchmark.cash -= fill * Decimal(shares)
        benchmark.shares = shares
        benchmark.entered = True
        entry = {"side": "BUY", "quantity": str(shares), "fill": str(fill)}
    entitled: List[Dict[str, str]] = []
    if dividend is not None and held_at_prior_close and benchmark.shares > 0:
        amount = Decimal(benchmark.shares) * dividend.amount_per_share
        benchmark.receivables.append((dividend.payable_date, amount))
        entitled.append({"ex_date": dividend.ex_date.isoformat(), "amount": str(amount)})
    benchmark.cash, benchmark.receivables = _settle_receivables(
        benchmark.cash, benchmark.receivables, session
    )
    market_value = Decimal(benchmark.shares) * spy_close
    outstanding_value = sum((a for _, a in benchmark.receivables), Decimal("0"))
    equity = benchmark.cash + market_value + outstanding_value
    if equity > benchmark.peak:
        benchmark.peak = equity
    decline = (benchmark.peak - equity) / benchmark.peak
    daily_return = equity / benchmark.prev_equity - Decimal("1")
    benchmark.prev_equity = equity
    return {
        "entry": entry,
        "entitlements": entitled,
        "shares": benchmark.shares,
        "cash": str(benchmark.cash),
        "market_value": str(market_value),
        "receivable": str(outstanding_value),
        "equity": str(equity),
        "daily_return": str(daily_return),
        "running_peak": str(benchmark.peak),
        "drawdown": str(decline),
    }


def append_observation(
    state_dir: Path,
    session: date,
    observation: Dict[str, Any],
    previous_sha: Optional[str],
) -> str:
    """Write an immutable observation artifact; returns its SHA-256."""
    target = state_dir / "observations" / f"{session.isoformat()}.json"
    if target.exists():
        raise DataContractError(f"SHADOW_OBSERVATION_EXISTS: {session}.")
    payload = dict(observation)
    payload["previous_observation_sha256"] = previous_sha
    raw = json.dumps(payload, indent=2, sort_keys=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    state_path = state_dir / "state.json"
    state_doc: Dict[str, Any] = {}
    if state_path.exists():
        state_doc = json.loads(state_path.read_text(encoding="utf-8"))
    state_doc["last_processed_session"] = session.isoformat()
    state_doc["last_observation_sha256"] = digest
    state_doc["observed_session_count"] = int(state_doc.get("observed_session_count", 0)) + 1
    with open(state_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(state_doc, indent=2, sort_keys=True))
    return digest
