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
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, cast

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow import (
    QUARANTINE_START,
    RECENT_STRESS_END,
    RECENT_STRESS_START,
    SCIENTIFIC_PROSPECTIVE_BOUNDARY,
    STATE_ACTIVATION_SESSION,
    STATE_HYPOTHESIS_ID,
    STATE_SCHEMA_VERSION,
    ShadowState,
    StageCRecoveryAuthority,
)
from acash.research.hyp_011.shadow_ca import CADetermination
from acash.research.hyp_011.accounting import (
    SIMULATED_STARTING_AUM,
    TARGET_WEIGHTS,
    solve_rebalance,
)


@dataclass
class SessionMarket:
    session: date
    opens_raw: Dict[str, Decimal]
    closes_raw: Dict[str, Decimal]


# Receivable = (symbol, ex_date, payable_date, amount, authority_source, authority_sha).
# The corporate-action authority that created it is never dropped.
Receivable = Tuple[str, date, date, Decimal, str, str]


@dataclass
class ShadowPortfolio:
    cash: Decimal = SIMULATED_STARTING_AUM
    holdings: Dict[str, int] = field(
        default_factory=lambda: {"ACWI": 0, "AGG": 0}
    )
    receivables: List[Receivable] = field(default_factory=list)
    peak: Decimal = SIMULATED_STARTING_AUM
    prev_equity: Decimal = SIMULATED_STARTING_AUM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash": str(self.cash),
            "holdings": {k: v for k, v in self.holdings.items()},
            "receivables": [
                {"symbol": s, "ex_date": e.isoformat(), "payable_date": d.isoformat(),
                 "amount": str(a), "authority_source": src, "authority_sha256": sha}
                for s, e, d, a, src, sha in self.receivables
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
                    (str(r["symbol"]), date.fromisoformat(r["ex_date"]),
                     date.fromisoformat(r["payable_date"]), Decimal(str(r["amount"])),
                     str(r["authority_source"]), str(r["authority_sha256"]))
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
    receivables: List[Receivable] = field(default_factory=list)
    peak: Decimal = SIMULATED_STARTING_AUM
    prev_equity: Decimal = SIMULATED_STARTING_AUM
    entered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash": str(self.cash),
            "SPY_shares": self.shares,
            "receivables": [
                {"symbol": s, "ex_date": e.isoformat(), "payable_date": d.isoformat(),
                 "amount": str(a), "authority_source": src, "authority_sha256": sha}
                for s, e, d, a, src, sha in self.receivables
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
                    (str(r["symbol"]), date.fromisoformat(r["ex_date"]),
                     date.fromisoformat(r["payable_date"]), Decimal(str(r["amount"])),
                     str(r["authority_source"]), str(r["authority_sha256"]))
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
    receivables: List[Receivable],
    session: date,
) -> Tuple[Decimal, List[Receivable]]:
    outstanding: List[Receivable] = []
    for symbol, ex_date, payable, amount, src, sha in receivables:
        if payable <= session:
            cash += amount
        else:
            outstanding.append((symbol, ex_date, payable, amount, src, sha))
    return cash, outstanding


def process_strategy_session(
    portfolio: ShadowPortfolio,
    market: SessionMarket,
    dividends: Mapping[str, CADetermination],
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
        determination = dividends.get(sym)
        if (
            determination is not None
            and determination.has_event
            and prev_holdings.get(sym, 0) > 0
        ):
            if determination.ex_date is None or determination.amount_per_share is None:
                raise DataContractError(f"SHADOW_CA_INCOMPLETE_EVENT: {sym}.")
            amount = Decimal(prev_holdings[sym]) * determination.amount_per_share
            if determination.payable_date is None:
                raise DataContractError(f"SHADOW_CA_MISSING_PAYABLE: {sym}.")
            portfolio.receivables.append(
                (sym, determination.ex_date, determination.payable_date, amount,
                 determination.authority_source, determination.source_sha256)
            )
            entitlements.append(
                {"symbol": sym, "ex_date": determination.ex_date.isoformat(),
                 "amount": str(amount),
                 "authority_source": determination.authority_source,
                 "authority_sha256": determination.source_sha256}
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
    outstanding_value = sum((a for _, _, _, a, _, _ in portfolio.receivables), Decimal("0"))
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
    dividend: Optional[CADetermination],
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
    if (
        dividend is not None
        and dividend.has_event
        and held_at_prior_close
        and benchmark.shares > 0
    ):
        if dividend.ex_date is None or dividend.amount_per_share is None:
            raise DataContractError("SHADOW_CA_INCOMPLETE_BENCH_EVENT.")
        amount = Decimal(benchmark.shares) * dividend.amount_per_share
        if dividend.payable_date is None:
            raise DataContractError("SHADOW_CA_MISSING_BENCH_PAYABLE.")
        benchmark.receivables.append(
            ("SPY", dividend.ex_date, dividend.payable_date, amount,
             dividend.authority_source, dividend.source_sha256)
        )
        entitled.append(
            {"ex_date": dividend.ex_date.isoformat(), "amount": str(amount),
             "authority_source": dividend.authority_source,
             "authority_sha256": dividend.source_sha256}
        )
    benchmark.cash, benchmark.receivables = _settle_receivables(
        benchmark.cash, benchmark.receivables, session
    )
    market_value = Decimal(benchmark.shares) * spy_close
    outstanding_value = sum((a for _, _, _, a, _, _ in benchmark.receivables), Decimal("0"))
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
    activation_session: Optional[date] = None,
    recovery_authority: Optional[StageCRecoveryAuthority] = None,
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
    else:
        segment_id = observation.get("segment_id") if isinstance(observation, dict) else None
        state_doc = build_initial_state(activation_session, segment_id)
    # Re-stamp fixed identity fields (never inferred from a partial doc).
    act = activation_session or (
        date.fromisoformat(state_doc["activation_session"])
        if "activation_session" in state_doc
        else STATE_ACTIVATION_SESSION
    )
    state_doc["schema_version"] = STATE_SCHEMA_VERSION
    state_doc["hypothesis_id"] = STATE_HYPOTHESIS_ID
    state_doc["activation_session"] = act.isoformat()
    if recovery_authority is not None:
        if (
            state_doc.get("activation_authority_sha256") is not None
            and state_doc.get("activation_authority_sha256") != recovery_authority.manifest_sha256
        ):
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: recovery authority changed.")
        state_doc["activation_authority_id"] = recovery_authority.binding_id
        state_doc["activation_authority_sha256"] = recovery_authority.manifest_sha256
        state_doc["activation_commit_sha"] = recovery_authority.binding_commit_sha
    else:
        if "activation_authority_id" not in state_doc:
            state_doc["activation_authority_id"] = None
        if "activation_authority_sha256" not in state_doc:
            state_doc["activation_authority_sha256"] = None
        if "activation_commit_sha" not in state_doc:
            state_doc["activation_commit_sha"] = None
    state_doc["starting_aum"] = str(SIMULATED_STARTING_AUM)
    state_doc["locks"] = {
        "paper_authorized": False,
        "live_authorized": False,
        "capital_authority_usd": "0.00",
        "no_real_orders": True,
    }
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


def build_initial_state(
    activation_session: Optional[date] = None,
    segment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Complete canonical initial state document (never a bare {})."""
    act = activation_session or STATE_ACTIVATION_SESSION
    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "hypothesis_id": STATE_HYPOTHESIS_ID,
        "activation_session": act.isoformat(),
        "activation_authority_id": None,
        "activation_authority_sha256": None,
        "activation_commit_sha": None,
        "starting_aum": str(SIMULATED_STARTING_AUM),
        "observed_sessions": [],
        "observed_session_count": 0,
        "last_processed_session": None,
        "last_observation_sha256": None,
        "completed_annual_rebalances": 0,
        "strategy": ShadowPortfolio().to_dict(),
        "benchmark": ShadowBenchmark().to_dict(),
        "last_closes_raw": {},
        "last_closes_split": {},
        "locks": {
            "paper_authorized": False,
            "live_authorized": False,
            "capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
    }
    if segment_id is not None:
        state["segment_id"] = segment_id
    return state


def validate_initial_state(
    doc: Mapping[str, Any],
    expected_activation: date = STATE_ACTIVATION_SESSION,
) -> None:
    """Enforce §4 initial-state invariants before observation #1 network."""
    if doc.get("schema_version") != 1:
        raise DataContractError("SHADOW_INITIAL_SCHEMA_VERSION.")
    if doc.get("hypothesis_id") != "HYP_011":
        raise DataContractError("SHADOW_INITIAL_HYPOTHESIS_ID.")
    if doc.get("activation_session") != expected_activation.isoformat():
        raise DataContractError("SHADOW_INITIAL_ACTIVATION.")
    if doc.get("activation_authority_id") is not None:
        raise DataContractError("SHADOW_INITIAL_AUTHORITY_ID.")
    if doc.get("activation_authority_sha256") is not None:
        raise DataContractError("SHADOW_INITIAL_AUTHORITY_SHA.")
    if doc.get("activation_commit_sha") is not None:
        raise DataContractError("SHADOW_INITIAL_COMMIT_SHA.")
    if str(doc.get("starting_aum")) != "100000.00":
        raise DataContractError("SHADOW_INITIAL_AUM.")
    if list(doc.get("observed_sessions", [None])) != []:
        raise DataContractError("SHADOW_INITIAL_OBSERVED_NONEMPTY.")
    if int(doc.get("observed_session_count", -1)) != 0:
        raise DataContractError("SHADOW_INITIAL_COUNT_NONZERO.")
    if doc.get("last_processed_session") is not None:
        raise DataContractError("SHADOW_INITIAL_LAST_PROCESSED.")
    if doc.get("last_observation_sha256") is not None:
        raise DataContractError("SHADOW_INITIAL_LAST_SHA.")
    if int(doc.get("completed_annual_rebalances", -1)) != 0:
        raise DataContractError("SHADOW_INITIAL_REBALANCE_NONZERO.")
    strategy = ShadowPortfolio.from_dict(doc["strategy"])
    if (
        strategy.cash != Decimal("100000.00")
        or strategy.holdings != {"ACWI": 0, "AGG": 0}
        or strategy.receivables != []
        or strategy.peak != Decimal("100000.00")
        or strategy.prev_equity != Decimal("100000.00")
    ):
        raise DataContractError("SHADOW_INITIAL_STRATEGY.")
    benchmark = ShadowBenchmark.from_dict(doc["benchmark"])
    if (
        benchmark.cash != Decimal("100000.00")
        or benchmark.shares != 0
        or benchmark.receivables != []
        or benchmark.peak != Decimal("100000.00")
        or benchmark.prev_equity != Decimal("100000.00")
        or benchmark.entered is not False
    ):
        raise DataContractError("SHADOW_INITIAL_BENCHMARK.")
    locks = doc.get("locks", {})
    if (
        locks.get("paper_authorized") is not False
        or locks.get("live_authorized") is not False
        or str(locks.get("capital_authority_usd")) != "0.00"
        or locks.get("no_real_orders") is not True
    ):
        raise DataContractError("SHADOW_INITIAL_LOCKS.")


def _require_finite_decimal(raw: Any, context: str) -> Decimal:
    """Parse an exact Decimal, rejecting malformed or non-finite values fail-closed."""
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError, ArithmeticError) as exc:
        raise DataContractError(
            f"BLOCK_SHADOW_STATE_INTEGRITY: malformed decimal {context}."
        ) from exc
    if not value.is_finite():
        raise DataContractError(
            f"BLOCK_SHADOW_STATE_INTEGRITY: non-finite decimal {context}."
        )
    return value


def _require_holdings_mapping(raw: Any, context: str) -> Dict[str, int]:
    """Validate a holdings mapping ({symbol: int shares}) fail-closed."""
    if not isinstance(raw, dict):
        raise DataContractError(
            f"BLOCK_SHADOW_STATE_INTEGRITY: malformed holdings {context}."
        )
    for key, val in raw.items():
        if not isinstance(key, str) or not isinstance(val, int) or isinstance(val, bool):
            raise DataContractError(
                f"BLOCK_SHADOW_STATE_INTEGRITY: malformed holdings {context}."
            )
    return dict(raw)


def _receivables_total(receivables: List[Receivable], context: str) -> Decimal:
    """Sum outstanding receivable amounts, rejecting non-finite entries fail-closed."""
    total = Decimal("0")
    for _, _, _, amount, _, _ in receivables:
        if not amount.is_finite():
            raise DataContractError(
                f"BLOCK_SHADOW_STATE_INTEGRITY: non-finite receivable {context}."
            )
        total += amount
    return total


def _reconcile_terminal_economics(
    state_dir: Path,
    terminal_iso: str,
    portfolio_state: ShadowPortfolio,
    benchmark_state: ShadowBenchmark,
) -> None:
    """F01: cross-reconcile persisted terminal economics with the terminal observation.

    The terminal observation file was already hash/link-verified by the
    chain walk. Any divergence between persisted state economics and the
    terminal observation fragment fails closed. Never mutates artifacts.
    """
    obs_path = state_dir / "observations" / f"{terminal_iso}.json"
    terminal_doc = json.loads(obs_path.read_text(encoding="utf-8"))
    if not isinstance(terminal_doc, dict):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: terminal observation malformed."
        )
    last_strat = terminal_doc.get("strategy")
    last_bench = terminal_doc.get("benchmark")
    if not isinstance(last_strat, dict) or not isinstance(last_bench, dict):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: terminal observation legs malformed."
        )
    # Strategy leg.
    if (
        _require_finite_decimal(last_strat.get("cash"), "terminal strategy cash")
        != portfolio_state.cash
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: state cash diverges from terminal observation."
        )
    if (
        _require_holdings_mapping(last_strat.get("holdings"), "terminal strategy holdings")
        != dict(portfolio_state.holdings)
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: state holdings diverges from terminal observation."
        )
    if (
        _require_finite_decimal(last_strat.get("equity"), "terminal strategy equity")
        != portfolio_state.prev_equity
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: state equity diverges from terminal observation."
        )
    if (
        _require_finite_decimal(last_strat.get("running_peak"), "terminal strategy peak")
        != portfolio_state.peak
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: state peak diverges from terminal observation."
        )
    if (
        _require_finite_decimal(last_strat.get("receivable"), "terminal strategy receivable")
        != _receivables_total(portfolio_state.receivables, "strategy")
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: state receivable diverges from terminal observation."
        )
    # Benchmark leg.
    if (
        _require_finite_decimal(last_bench.get("cash"), "terminal benchmark cash")
        != benchmark_state.cash
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: benchmark cash diverges from terminal observation."
        )
    obs_shares = last_bench.get("shares")
    if not isinstance(obs_shares, int) or isinstance(obs_shares, bool):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: terminal benchmark shares malformed."
        )
    if benchmark_state.shares != obs_shares:
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: benchmark shares diverges from terminal observation."
        )
    if (
        _require_finite_decimal(last_bench.get("equity"), "terminal benchmark equity")
        != benchmark_state.prev_equity
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: benchmark equity diverges from terminal observation."
        )
    if (
        _require_finite_decimal(last_bench.get("running_peak"), "terminal benchmark peak")
        != benchmark_state.peak
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: benchmark peak diverges from terminal observation."
        )
    if (
        _require_finite_decimal(last_bench.get("receivable"), "terminal benchmark receivable")
        != _receivables_total(benchmark_state.receivables, "benchmark")
    ):
        raise DataContractError(
            "BLOCK_SHADOW_STATE_INTEGRITY: benchmark receivable diverges from terminal observation."
        )


def verify_chain(
    state_dir: Path,
    expected_activation: Optional[date] = None,
    expected_recovery_authority: Optional[StageCRecoveryAuthority] = None,
    expected_segment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Recompute the full observation chain BEFORE any network execution.

    Returns the verified state document. Any mismatch raises
    BLOCK_SHADOW_STATE_INTEGRITY with zero network side effects.
    """
    state_path = state_dir / "state.json"
    obs_dir = state_dir / "observations"
    # F02: orphan check on disk precedes any initial-state generation. An
    # observation file without state.json is a crash/interruption remnant and
    # must BLOCK rather than silently restart from pristine initial state.
    on_disk_all = sorted(
        p.stem for p in obs_dir.glob("*.json") if p.is_file()
    ) if obs_dir.exists() else []
    if not state_path.exists():
        if on_disk_all:
            raise DataContractError(
                f"BLOCK_SHADOW_STATE_INTEGRITY: orphan observation files "
                f"{on_disk_all} exist without state.json."
            )
        return build_initial_state(expected_activation, expected_segment_id)
    state_doc = json.loads(state_path.read_text(encoding="utf-8"))
    # Fixed identity fields (every state, empty or not).
    if state_doc.get("schema_version") != STATE_SCHEMA_VERSION:
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: schema_version.")
    if state_doc.get("hypothesis_id") != STATE_HYPOTHESIS_ID:
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: hypothesis_id.")
    exp_act = (
        expected_activation
        or (expected_recovery_authority.activation_session if expected_recovery_authority is not None else STATE_ACTIVATION_SESSION)
    ).isoformat()
    if state_doc.get("activation_session") != exp_act:
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: activation_session.")
    # Segment identity validation (V2)
    if expected_segment_id is not None:
        actual_segment = state_doc.get("segment_id")
        if actual_segment != expected_segment_id:
            raise DataContractError(
                f"BLOCK_SHADOW_STATE_INTEGRITY: segment_id mismatch, "
                f"expected {expected_segment_id}, got {actual_segment}."
            )
    else:
        # V1: ensure no segment_id contamination
        if state_doc.get("segment_id") is not None:
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: unexpected segment_id.")
    if str(state_doc.get("starting_aum")) != str(SIMULATED_STARTING_AUM):
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: starting_aum.")
    locks = state_doc.get("locks", {})
    if (
        locks.get("paper_authorized") is not False
        or locks.get("live_authorized") is not False
        or str(locks.get("capital_authority_usd")) != "0.00"
        or locks.get("no_real_orders") is not True
    ):
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: locks.")
    observed = list(state_doc.get("observed_sessions", []))
    if not observed:
        validate_initial_state(state_doc, expected_activation or STATE_ACTIVATION_SESSION)
    else:
        # Check recovery authority binding invariants when observations exist
        if expected_recovery_authority is not None:
            if state_doc.get("activation_authority_id") != expected_recovery_authority.binding_id:
                raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: authority ID mismatch.")
            if state_doc.get("activation_authority_sha256") != expected_recovery_authority.manifest_sha256:
                raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: authority SHA mismatch.")
            if state_doc.get("activation_commit_sha") != expected_recovery_authority.binding_commit_sha:
                raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: commit SHA mismatch.")
        elif state_doc.get("activation_authority_sha256") is not None:
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: missing expected recovery authority.")

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
        if expected_recovery_authority is not None:
            auth_doc = doc.get("authority", {})
            required_authority_fields = (
                "activation_binding",
                "activation_binding_id",
                "activation_binding_sha256",
                "activation_binding_commit_sha",
                "activation_binding_commit_utc",
                "operational_activation_session",
            )
            for req_field in required_authority_fields:
                if req_field not in auth_doc or auth_doc[req_field] is None:
                    raise DataContractError(
                        f"BLOCK_SHADOW_STATE_INTEGRITY: missing recovery authority field {req_field} at {iso}."
                    )
            if auth_doc["activation_binding_id"] != expected_recovery_authority.binding_id:
                raise DataContractError(
                    f"BLOCK_SHADOW_STATE_INTEGRITY: observation authority ID mismatch at {iso}."
                )
            if auth_doc["activation_binding_sha256"] != expected_recovery_authority.manifest_sha256:
                raise DataContractError(
                    f"BLOCK_SHADOW_STATE_INTEGRITY: observation binding SHA mismatch at {iso}."
                )
            if auth_doc["activation_binding_commit_sha"] != expected_recovery_authority.binding_commit_sha:
                raise DataContractError(
                    f"BLOCK_SHADOW_STATE_INTEGRITY: observation commit SHA mismatch at {iso}."
                )
            if auth_doc["activation_binding_commit_utc"] != expected_recovery_authority.binding_commit_utc:
                raise DataContractError(
                    f"BLOCK_SHADOW_STATE_INTEGRITY: observation commit UTC mismatch at {iso}."
                )
            if auth_doc["operational_activation_session"] != expected_recovery_authority.activation_session.isoformat():
                raise DataContractError(
                    f"BLOCK_SHADOW_STATE_INTEGRITY: observation activation session mismatch at {iso}."
                )
    if state_doc.get("last_observation_sha256") != previous:
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: last SHA mismatch.")
    if state_doc.get("last_processed_session") != (observed[-1] if observed else None):
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: last session mismatch.")
    if int(state_doc.get("observed_session_count", -1)) != len(observed):
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: count mismatch.")
    if observed:
        for field in (
            "strategy", "benchmark", "last_closes_raw", "last_closes_split",
            "completed_annual_rebalances",
        ):
            if field not in state_doc:
                raise DataContractError(f"BLOCK_SHADOW_STATE_INTEGRITY: missing {field}.")
        # Economic state must deserialize (proves persistence completeness).
        portfolio_state = ShadowPortfolio.from_dict(state_doc["strategy"])
        benchmark_state = ShadowBenchmark.from_dict(state_doc["benchmark"])
        # F01: cross-document economic reconciliation with the terminal
        # observation. Tampered or divergent balances fail closed here even
        # when every subdocument deserializes cleanly.
        _reconcile_terminal_economics(
            state_dir, observed[-1], portfolio_state, benchmark_state
        )
    # Orphan detection: no extra observation files beyond the chain.
    on_disk = sorted(
        p.stem for p in (state_dir / "observations").glob("*.json") if p.is_file()
    ) if (state_dir / "observations").exists() else []
    if on_disk != observed:
        raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: orphan files.")
    return cast(Dict[str, Any], state_doc)
