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
from typing import Any, Dict, List, Mapping, Optional, Tuple, cast

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
    receivables: List[Tuple[str, date, Decimal]] = field(default_factory=list)
    peak: Decimal = SIMULATED_STARTING_AUM
    prev_equity: Decimal = SIMULATED_STARTING_AUM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash": str(self.cash),
            "holdings": {k: v for k, v in self.holdings.items()},
            "receivables": [
                {"symbol": s, "payable_date": d.isoformat(), "amount": str(a)}
                for s, d, a in self.receivables
            ],
            "running_peak": str(self.peak),
            "previous_equity": str(self.prev_equity),
        }

    @classmethod
    def from_dict(cls, doc: Mapping[str, Any]) -> "ShadowPortfolio":
        try:
            return cls(
                cash=Decimal(str(doc["cash"])),
                holdings={k: int(v) for k, v in dict(doc["holdings"]).items()},
                receivables=[
                    (str(r["symbol"]), date.fromisoformat(r["payable_date"]),
                     Decimal(str(r["amount"])))
                    for r in list(doc["receivables"])
                ],
                peak=Decimal(str(doc["running_peak"])),
                prev_equity=Decimal(str(doc["previous_equity"])),
            )
        except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
            raise DataContractError(f"SHADOW_PORTFOLIO_DESERIALIZE: {exc}.") from exc


@dataclass
class ShadowBenchmark:
    cash: Decimal = SIMULATED_STARTING_AUM
    shares: int = 0
    receivables: List[Tuple[str, date, Decimal]] = field(default_factory=list)
    peak: Decimal = SIMULATED_STARTING_AUM
    prev_equity: Decimal = SIMULATED_STARTING_AUM
    entered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash": str(self.cash),
            "SPY_shares": self.shares,
            "receivables": [
                {"symbol": s, "payable_date": d.isoformat(), "amount": str(a)}
                for s, d, a in self.receivables
            ],
            "running_peak": str(self.peak),
            "previous_equity": str(self.prev_equity),
            "entered": self.entered,
        }

    @classmethod
    def from_dict(cls, doc: Mapping[str, Any]) -> "ShadowBenchmark":
        try:
            entered = doc["entered"]
            if not isinstance(entered, bool):
                raise ValueError("entered must be bool")
            return cls(
                cash=Decimal(str(doc["cash"])),
                shares=int(doc["SPY_shares"]),
                receivables=[
                    (str(r["symbol"]), date.fromisoformat(r["payable_date"]),
                     Decimal(str(r["amount"])))
                    for r in list(doc["receivables"])
                ],
                peak=Decimal(str(doc["running_peak"])),
                prev_equity=Decimal(str(doc["previous_equity"])),
                entered=entered,
            )
        except (KeyError, ValueError, TypeError, ArithmeticError) as exc:
            raise DataContractError(f"SHADOW_BENCHMARK_DESERIALIZE: {exc}.") from exc


def _settle_receivables(
    cash: Decimal,
    receivables: List[Tuple[str, date, Decimal]],
    session: date,
) -> Tuple[Decimal, List[Tuple[str, date, Decimal]]]:
    outstanding: List[Tuple[str, date, Decimal]] = []
    for symbol, payable, amount in receivables:
        if payable <= session:
            cash += amount
        else:
            outstanding.append((symbol, payable, amount))
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
            portfolio.receivables.append((sym, event.payable_date, amount))
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
    outstanding_value = sum((a for _, _, a in portfolio.receivables), Decimal("0"))
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
        benchmark.receivables.append(("SPY", dividend.payable_date, amount))
        entitled.append({"ex_date": dividend.ex_date.isoformat(), "amount": str(amount)})
    benchmark.cash, benchmark.receivables = _settle_receivables(
        benchmark.cash, benchmark.receivables, session
    )
    market_value = Decimal(benchmark.shares) * spy_close
    outstanding_value = sum((a for _, _, a in benchmark.receivables), Decimal("0"))
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
    portfolio: Optional[ShadowPortfolio] = None,
    benchmark: Optional[ShadowBenchmark] = None,
    completed_annual_rebalances: int = 0,
    extra_state: Optional[Dict[str, Any]] = None,
) -> str:
    """Write an immutable observation artifact; persist full state; return SHA.

    Crash-safe ordering: observation file first, then state file. A crash
    between the two surfaces as an integrity mismatch on next invocation
    (state SHA != recomputed file SHA) and BLOCKS rather than auto-healing.
    """
    target = state_dir / "observations" / f"{session.isoformat()}.json"
    if target.exists():
        raise DataContractError(f"SHADOW_OBSERVATION_EXISTS: {session}.")
    payload = dict(observation)
    payload["previous_observation_sha256"] = previous_sha
    raw = json.dumps(payload, indent=2, sort_keys=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_obs = target.with_suffix(".json.tmp")
    with open(tmp_obs, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    tmp_obs.replace(target)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    state_path = state_dir / "state.json"
    state_doc: Dict[str, Any] = {}
    if state_path.exists():
        state_doc = json.loads(state_path.read_text(encoding="utf-8"))
    observed_list = list(state_doc.get("observed_sessions", []))
    if session.isoformat() in observed_list:
        raise DataContractError(f"SHADOW_STATE_ALREADY_CONTAINS: {session}.")
    observed_list.append(session.isoformat())
    state_doc["observed_sessions"] = observed_list
    state_doc["last_processed_session"] = session.isoformat()
    state_doc["last_observation_sha256"] = digest
    state_doc["observed_session_count"] = int(state_doc.get("observed_session_count", 0)) + 1
    if portfolio is not None:
        state_doc["strategy"] = portfolio.to_dict()
    if benchmark is not None:
        state_doc["benchmark"] = benchmark.to_dict()
    state_doc["completed_annual_rebalances"] = completed_annual_rebalances
    if extra_state:
        state_doc.update(extra_state)
    state_raw = json.dumps(state_doc, indent=2, sort_keys=True)
    tmp_state = state_path.with_suffix(".json.tmp")
    with open(tmp_state, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(state_raw)
    tmp_state.replace(state_path)
    return digest


def verify_chain(state_dir: Path) -> Dict[str, Any]:
    """Recompute the full observation chain BEFORE any network execution.

    Returns the verified state document. Any mismatch raises
    BLOCK_SHADOW_STATE_INTEGRITY with zero network side effects.
    """
    state_path = state_dir / "state.json"
    if not state_path.exists():
        return {
            "observed_sessions": [],
            "observed_session_count": 0,
            "last_processed_session": None,
            "last_observation_sha256": None,
        }
    state_doc = json.loads(state_path.read_text(encoding="utf-8"))
    observed = list(state_doc.get("observed_sessions", []))
    if observed != sorted(observed):
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: sessions unordered.")
    previous: Optional[str] = None
    for iso in observed:
        obs_path = state_dir / "observations" / f"{iso}.json"
        if not obs_path.exists():
            raise DataContractError(f"BLOCK_SHADOW_STATE_INTEGRITY: missing {iso}.")
        raw = obs_path.read_bytes()
        if b"\r" in raw:
            raise DataContractError(f"BLOCK_SHADOW_STATE_INTEGRITY: CR bytes {iso}.")
        digest = hashlib.sha256(raw).hexdigest()
        doc = json.loads(raw.decode("utf-8"))
        if doc.get("previous_observation_sha256") != previous:
            raise DataContractError(
                f"BLOCK_SHADOW_STATE_INTEGRITY: broken link at {iso}."
            )
        previous = digest
    if state_doc.get("last_observation_sha256") != previous:
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: last SHA mismatch.")
    if state_doc.get("last_processed_session") != (observed[-1] if observed else None):
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: last session mismatch.")
    if int(state_doc.get("observed_session_count", -1)) != len(observed):
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: count mismatch.")
    # Orphan detection: no extra observation files beyond the chain.
    on_disk = sorted(
        p.stem for p in (state_dir / "observations").glob("*.json") if p.is_file()
    ) if (state_dir / "observations").exists() else []
    if on_disk != observed:
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: orphan files.")
    return cast(Dict[str, Any], state_doc)
