"""Frozen HYP_011 80/20 whole-share allocation accounting (Decimal, fail-closed).

Order per session: ex-date entitlement (prior-close holdings) -> payable
settlement -> scheduled open rebalance -> EOD valuation. Reuses HYP_009-tested
primitives (fills, fees, Sharpe, MDD) whose semantics are identical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.research.hyp_009.accounting import (
    DividendEvent,
    EquityRecord,
    TradeRecord,
    adverse_fill,
    annualized_sharpe,
    max_drawdown,
    sell_side_fees,
)

SIMULATED_STARTING_AUM: Decimal = Decimal("100000.00")
TARGET_WEIGHTS: Dict[str, Decimal] = {"ACWI": Decimal("0.80"), "AGG": Decimal("0.20")}
BASELINE_SLIPPAGE_BPS: Decimal = Decimal("2")
STRESS_SLIPPAGE_BPS: Decimal = Decimal("10")
COMMISSION: Decimal = Decimal("0.00")


@dataclass
class AllocationResult:
    path: str
    equity_curve: List[EquityRecord] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    rebalances: List[Dict[str, str]] = field(default_factory=list)
    ending_equity: Decimal = Decimal("0")
    ending_cash: Decimal = Decimal("0")
    ending_holdings: Dict[str, int] = field(default_factory=dict)
    regulatory_fees_paid: Decimal = Decimal("0")
    dividends_received: Decimal = Decimal("0")
    terminal_receivable: Decimal = Decimal("0")


def _projected_weights(
    cash: Decimal, holdings: Mapping[str, int], opens: Mapping[str, Decimal]
) -> Tuple[Decimal, Decimal, Decimal]:
    total = cash + sum(
        Decimal(holdings.get(sym, 0)) * opens[sym] for sym in TARGET_WEIGHTS
    )
    if total <= Decimal("0"):
        raise DataContractError("HYP_011_NONPOSITIVE_PROJECTED_TOTAL.")
    weights = {
        sym: Decimal(holdings.get(sym, 0)) * opens[sym] / total for sym in TARGET_WEIGHTS
    }
    objective = sum(
        abs(weights[sym] - TARGET_WEIGHTS[sym]) for sym in TARGET_WEIGHTS
    )
    return total, weights["ACWI"], weights["AGG"]


def solve_rebalance(
    session: date,
    cash: Decimal,
    holdings: Mapping[str, int],
    opens: Mapping[str, Decimal],
    slippage_bps: Decimal,
    fee_multiplier: int,
    path: str,
) -> Tuple[List[TradeRecord], Decimal, Dict[str, int]]:
    """Deterministic whole-share rebalance: sells first, min-deviation buys."""
    for sym in TARGET_WEIGHTS:
        if opens[sym] <= Decimal("0"):
            raise DataContractError(f"HYP_011_NONPOSITIVE_OPEN: {session} {sym}.")
    trades: List[TradeRecord] = []
    cash_now = cash
    shares: Dict[str, int] = {sym: int(holdings.get(sym, 0)) for sym in TARGET_WEIGHTS}

    # Sells first.
    pretrade_value = cash_now + sum(Decimal(shares[s]) * opens[s] for s in TARGET_WEIGHTS)
    desired = {
        sym: int((TARGET_WEIGHTS[sym] * pretrade_value) // opens[sym])
        for sym in TARGET_WEIGHTS
    }
    for sym in ("ACWI", "AGG"):
        if desired[sym] < shares[sym]:
            quantity = shares[sym] - desired[sym]
            fill = adverse_fill(opens[sym], "SELL", slippage_bps)
            proceeds = fill * Decimal(quantity)
            sec31, taf, cat = sell_side_fees(session, quantity, proceeds, fee_multiplier)
            friction = sec31 + taf + cat
            cash_before = cash_now
            cash_now = cash_now + proceeds - friction
            trades.append(
                TradeRecord(
                    path=path, decision_date=session, execution_date=session,
                    transition="REBALANCE_SELL", side="SELL", raw_open=opens[sym],
                    fill_price=fill, quantity=quantity, gross_notional=proceeds,
                    commission=COMMISSION, sec31_fee=sec31, finra_taf=taf,
                    cat_fee=cat, regulatory_fees_paid=friction,
                    cash_before=cash_before, cash_after=cash_now,
                    shares_before=shares[sym], shares_after=desired[sym],
                )
            )
            shares[sym] = desired[sym]

    # Proposed buys with min-deviation decrement guard.
    proposed = {
        sym: max(0, desired[sym] - shares[sym]) for sym in TARGET_WEIGHTS
    }
    while True:
        cost = sum(
            adverse_fill(opens[sym], "BUY", slippage_bps) * Decimal(proposed[sym])
            for sym in TARGET_WEIGHTS
        )
        if cost <= cash_now:
            break
        # Decrement the BUY whose one-share reduction minimizes objective increase.
        best_sym: Optional[str] = None
        best_objective: Optional[Decimal] = None
        for sym in ("ACWI", "AGG"):
            if proposed[sym] <= 0:
                continue
            trial = dict(proposed)
            trial[sym] -= 1
            trial_holdings = {
                s: shares[s] + trial[s] for s in TARGET_WEIGHTS
            }
            _, w_acwi, w_agg = _projected_weights(cash_now - sum(
                adverse_fill(opens[s], "BUY", slippage_bps) * Decimal(trial[s])
                for s in TARGET_WEIGHTS
            ), trial_holdings, opens)
            objective = abs(w_acwi - TARGET_WEIGHTS["ACWI"]) + abs(
                w_agg - TARGET_WEIGHTS["AGG"]
            )
            if best_objective is None or objective < best_objective or (
                objective == best_objective and sym == "AGG" and best_sym == "ACWI"
            ):
                best_objective = objective
                best_sym = sym
        if best_sym is None:
            raise DataContractError(f"HYP_011_CANNOT_AFFORD_ANY_SHARE: {session}.")
        proposed[best_sym] -= 1

    for sym in ("ACWI", "AGG"):
        quantity = proposed[sym]
        if quantity <= 0:
            continue
        fill = adverse_fill(opens[sym], "BUY", slippage_bps)
        notional = fill * Decimal(quantity)
        if notional > cash_now:
            raise DataContractError(f"HYP_011_NEGATIVE_CASH_GUARD: {session} {sym}.")
        cash_before = cash_now
        cash_now -= notional
        trades.append(
            TradeRecord(
                path=path, decision_date=session, execution_date=session,
                transition="REBALANCE_BUY", side="BUY", raw_open=opens[sym],
                fill_price=fill, quantity=quantity, gross_notional=notional,
                commission=COMMISSION, sec31_fee=Decimal("0.00"),
                finra_taf=Decimal("0.00"), cat_fee=Decimal("0.00"),
                regulatory_fees_paid=Decimal("0.00"),
                cash_before=cash_before, cash_after=cash_now,
                shares_before=shares[sym], shares_after=shares[sym] + quantity,
            )
        )
        shares[sym] += quantity
    if cash_now < Decimal("0"):
        raise DataContractError(f"HYP_011_NEGATIVE_CASH: {session}.")
    return trades, cash_now, shares


def run_allocation(
    path: str,
    sessions: Sequence[date],
    opens: Mapping[str, Mapping[date, Decimal]],
    closes: Mapping[str, Mapping[date, Decimal]],
    dividends: Mapping[str, Sequence[DividendEvent]],
    rebalance_sessions: Sequence[date],
    slippage_bps: Decimal,
    fee_multiplier: int,
    starting_aum: Decimal = SIMULATED_STARTING_AUM,
) -> AllocationResult:
    """Annual 80/20 whole-share simulation over ordered sessions."""
    ordered = list(sessions)
    if not ordered or ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise DataContractError("HYP_011_SESSIONS_MUST_BE_UNIQUE_CHRONOLOGICAL.")
    rebalance_set = set(rebalance_sessions)
    if not rebalance_set.issubset(set(ordered)):
        raise DataContractError("HYP_011_REBALANCE_OUTSIDE_SESSIONS.")
    by_ex = {sym: {e.ex_date: e for e in dividends.get(sym, [])} for sym in TARGET_WEIGHTS}

    result = AllocationResult(path=path)
    cash = starting_aum
    holdings: Dict[str, int] = {"ACWI": 0, "AGG": 0}
    receivables: List[Tuple[date, Decimal]] = []
    peak = starting_aum
    # Frozen §9: reference equity before the first execution is starting_aum,
    # so the first session carries EOD_1/starting_aum - 1 (never dropped).
    prev_equity: Decimal = starting_aum
    prev_holdings: Dict[str, int] = {"ACWI": 0, "AGG": 0}

    for session in ordered:
        session_opens = {sym: opens[sym][session] for sym in TARGET_WEIGHTS}
        session_closes = {sym: closes[sym][session] for sym in TARGET_WEIGHTS}
        if any(v <= Decimal("0") for v in list(session_opens.values()) + list(session_closes.values())):
            raise DataContractError(f"HYP_011_NONPOSITIVE_PRICE: {session}.")

        # 1. Ex-date entitlement from prior-close holdings.
        for sym in TARGET_WEIGHTS:
            event = by_ex[sym].get(session)
            if event is not None and prev_holdings.get(sym, 0) > 0:
                amount = Decimal(prev_holdings[sym]) * event.amount_per_share
                receivables.append((event.payable_date, amount))
                result.dividends_received += amount

        # 2. Payable settlement into spendable cash.
        outstanding: List[Tuple[date, Decimal]] = []
        for payable, amount in receivables:
            if payable <= session:
                cash += amount
            else:
                outstanding.append((payable, amount))
        receivables = outstanding

        # 3. Scheduled open rebalance.
        if session in rebalance_set:
            new_trades, cash, holdings = solve_rebalance(
                session, cash, holdings, session_opens, slippage_bps, fee_multiplier, path
            )
            result.trades.extend(new_trades)
            for trade in new_trades:
                result.regulatory_fees_paid += trade.regulatory_fees_paid
            result.rebalances.append(
                {
                    "session": session.isoformat(),
                    "acwi_shares": str(holdings["ACWI"]),
                    "agg_shares": str(holdings["AGG"]),
                    "cash": str(cash),
                }
            )

        # 4. EOD valuation.
        market_value = sum(
            (Decimal(holdings[s]) * session_closes[s] for s in TARGET_WEIGHTS),
            Decimal("0"),
        )
        outstanding_value = sum((a for _, a in receivables), Decimal("0"))
        equity = cash + market_value + outstanding_value
        if equity > peak:
            peak = equity
        decline = (peak - equity) / peak if peak > Decimal("0") else Decimal("0")
        if prev_equity <= Decimal("0"):
            raise DataContractError(f"HYP_011_NONPOSITIVE_PREV_EQUITY: {session}.")
        daily_return = equity / prev_equity - Decimal("1")
        result.equity_curve.append(
            EquityRecord(
                session=session, cash=cash,
                shares=holdings["ACWI"] + holdings["AGG"],
                raw_close=session_closes["ACWI"],
                market_value=market_value,
                dividend_receivable=outstanding_value, total_equity=equity,
                daily_return=daily_return, running_peak=peak, drawdown=decline,
            )
        )
        prev_equity = equity
        prev_holdings = dict(holdings)

    result.ending_equity = prev_equity
    result.ending_cash = cash
    result.ending_holdings = dict(holdings)
    result.terminal_receivable = sum((a for _, a in receivables), Decimal("0"))
    return result


def run_single_asset_buy_hold(
    path: str,
    symbol: str,
    sessions: Sequence[date],
    opens: Mapping[date, Decimal],
    closes: Mapping[date, Decimal],
    dividends: Sequence[DividendEvent],
    slippage_bps: Decimal,
) -> AllocationResult:
    """Single-asset buy-and-hold (benchmark leg): one entry, hold, same economics."""
    ordered = list(sessions)
    result = AllocationResult(path=path)
    cash = SIMULATED_STARTING_AUM
    shares = 0
    fill = adverse_fill(opens[ordered[0]], "BUY", slippage_bps)
    shares = int(cash // fill)
    if shares <= 0:
        raise DataContractError(f"HYP_011_BENCHMARK_ZERO_SHARES: {ordered[0]}.")
    notional = fill * Decimal(shares)
    cash -= notional
    result.trades.append(
        TradeRecord(
            path=path, decision_date=ordered[0], execution_date=ordered[0],
            transition="BENCHMARK_ENTRY", side="BUY", raw_open=opens[ordered[0]],
            fill_price=fill, quantity=shares, gross_notional=notional,
            commission=COMMISSION, sec31_fee=Decimal("0.00"),
            finra_taf=Decimal("0.00"), cat_fee=Decimal("0.00"),
            regulatory_fees_paid=Decimal("0.00"),
            cash_before=SIMULATED_STARTING_AUM, cash_after=cash,
            shares_before=0, shares_after=shares,
        )
    )
    receivables: List[Tuple[date, Decimal]] = []
    by_ex = {e.ex_date: e for e in dividends}
    peak = SIMULATED_STARTING_AUM
    # Frozen §9: first-day return anchored at starting_aum (never dropped).
    prev_equity: Decimal = SIMULATED_STARTING_AUM
    prev_close_shares = 0

    for session in ordered:
        event = by_ex.get(session)
        if event is not None and prev_close_shares > 0:
            amount = Decimal(prev_close_shares) * event.amount_per_share
            receivables.append((event.payable_date, amount))
            result.dividends_received += amount
        outstanding: List[Tuple[date, Decimal]] = []
        for payable, amount in receivables:
            if payable <= session:
                cash += amount
            else:
                outstanding.append((payable, amount))
        receivables = outstanding
        market_value = Decimal(shares) * closes[session]
        outstanding_value = sum((a for _, a in receivables), Decimal("0"))
        equity = cash + market_value + outstanding_value
        if equity > peak:
            peak = equity
        decline = (peak - equity) / peak if peak > Decimal("0") else Decimal("0")
        if prev_equity <= Decimal("0"):
            raise DataContractError(f"HYP_011_NONPOSITIVE_PREV_EQUITY: {session}.")
        daily_return = equity / prev_equity - Decimal("1")
        result.equity_curve.append(
            EquityRecord(
                session=session, cash=cash, shares=shares, raw_close=closes[session],
                market_value=market_value, dividend_receivable=outstanding_value,
                total_equity=equity, daily_return=daily_return,
                running_peak=peak, drawdown=decline,
            )
        )
        prev_equity = equity
        prev_close_shares = shares
    result.ending_equity = prev_equity
    result.ending_cash = cash
    result.ending_holdings = {symbol: shares}
    result.terminal_receivable = sum((a for _, a in receivables), Decimal("0"))
    return result
