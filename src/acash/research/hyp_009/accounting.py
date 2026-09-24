"""Frozen HYP_009 portfolio accounting: whole-share simulation, dividends, metrics.

Bound to HYP_009_PRE_R2_EXECUTION_ACCOUNTING_CLARIFICATION. All money math in
Decimal. No leverage, no shorting, no negative cash (fail closed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.execution.regulatory_fees import compute_finra_taf, compute_sec31_fee
from acash.research.hyp_009.signals import MonthSignal

SIMULATED_STARTING_AUM: Decimal = Decimal("100000.00")

BASELINE_SLIPPAGE_BPS: Decimal = Decimal("2")
STRESS_SLIPPAGE_BPS: Decimal = Decimal("10")
COMMISSION_BASELINE: Decimal = Decimal("0.00")

# No canonical ACASH CAT fee authority exists for the 2016-2020 M1 window; the
# frozen R1 contract includes CAT only "if effective/applicable". Recorded as
# zero with explicit provenance rather than an invented schedule.
CAT_FEE_REASON: str = "NO_CANONICAL_CAT_FEE_AUTHORITY_FOR_M1_WINDOW_RECORDED_ZERO"

SHARPE_PERIODS_PER_YEAR: int = 252
SHARPE_DDOF: int = 1
SHARPE_RISK_FREE: Decimal = Decimal("0")


@dataclass(frozen=True)
class DividendEvent:
    ex_date: date
    payable_date: date
    amount_per_share: Decimal


@dataclass(frozen=True)
class TradeRecord:
    path: str
    decision_date: Optional[date]
    execution_date: date
    transition: str
    side: str
    raw_open: Decimal
    fill_price: Decimal
    quantity: int
    gross_notional: Decimal
    commission: Decimal
    sec31_fee: Decimal
    finra_taf: Decimal
    cat_fee: Decimal
    total_friction: Decimal
    cash_before: Decimal
    cash_after: Decimal
    shares_before: int
    shares_after: int


@dataclass(frozen=True)
class EquityRecord:
    session: date
    cash: Decimal
    shares: int
    raw_close: Decimal
    market_value: Decimal
    dividend_receivable: Decimal
    total_equity: Decimal
    daily_return: Optional[Decimal]
    running_peak: Decimal
    drawdown: Decimal


@dataclass
class PortfolioResult:
    path: str
    equity_curve: List[EquityRecord] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    ending_equity: Decimal = Decimal("0")
    ending_cash: Decimal = Decimal("0")
    ending_shares: int = 0
    total_friction: Decimal = Decimal("0")
    dividends_received: Decimal = Decimal("0")
    terminal_receivable: Decimal = Decimal("0")


def adverse_fill(raw_open: Decimal, side: str, slippage_bps: Decimal) -> Decimal:
    """Adverse execution fill: BUY pays up, SELL receives less."""
    if raw_open <= Decimal("0"):
        raise DataContractError(f"FILL_NONPOSITIVE_OPEN: {raw_open}.")
    factor = slippage_bps / Decimal("10000")
    if side == "BUY":
        return raw_open * (Decimal("1") + factor)
    if side == "SELL":
        return raw_open * (Decimal("1") - factor)
    raise DataContractError(f"FILL_UNKNOWN_SIDE: {side}.")


def sell_side_fees(
    trade_date: date, shares: int, principal: Decimal, fee_multiplier: int
) -> Tuple[Decimal, Decimal, Decimal]:
    """SEC31 + TAF on sells (buys are zero); stress multiplies both by 2."""
    if fee_multiplier not in (1, 2):
        raise DataContractError(f"FEE_MULTIPLIER_INVALID: {fee_multiplier}.")
    sec31 = compute_sec31_fee(trade_date, principal, is_sell=True)
    taf = compute_finra_taf(trade_date, shares, is_sell=True)
    mult = Decimal(fee_multiplier)
    return sec31 * mult, taf * mult, Decimal("0.00")


def annualized_sharpe(daily_returns: Sequence[Decimal]) -> Decimal:
    """Daily-net-return Sharpe (252 / ddof=1 / rf=0); zero variance fails closed."""
    n = len(daily_returns)
    if n < 2:
        raise DataContractError(f"SHARPE_INSUFFICIENT_OBSERVATIONS: n={n}.")
    mean = sum(daily_returns, Decimal("0")) / Decimal(n)
    variance = sum((r - mean) ** 2 for r in daily_returns) / Decimal(n - SHARPE_DDOF)
    if variance <= Decimal("0"):
        raise DataContractError("SHARPE_ZERO_VARIANCE_FAIL_CLOSED.")
    std = variance.sqrt()
    return (mean - SHARPE_RISK_FREE) / std * Decimal(SHARPE_PERIODS_PER_YEAR).sqrt()


def max_drawdown(equities: Sequence[Decimal]) -> Decimal:
    """Maximum peak-to-trough decline over an EOD equity curve."""
    if not equities:
        raise DataContractError("MDD_EMPTY_EQUITY_CURVE.")
    peak = equities[0]
    worst = Decimal("0")
    for equity in equities:
        if equity > peak:
            peak = equity
        if peak <= Decimal("0"):
            raise DataContractError("MDD_NONPOSITIVE_PEAK.")
        decline = (peak - equity) / peak
        if decline > worst:
            worst = decline
    return worst


def run_portfolio(
    path: str,
    m1_sessions: Sequence[date],
    opens_raw: Mapping[date, Decimal],
    closes_raw: Mapping[date, Decimal],
    execution_by_session: Mapping[date, str],
    dividends: Sequence[DividendEvent],
    slippage_bps: Decimal,
    fee_multiplier: int,
    starting_aum: Decimal = SIMULATED_STARTING_AUM,
) -> PortfolioResult:
    """Deterministic whole-share LONG/CASH simulation over M1 sessions.

    execution_by_session maps an M1 session -> target state ("LONG"/"CASH") for
    sessions where a signal transition executes; other sessions hold state.
    """
    sessions = list(m1_sessions)
    if not sessions or sessions != sorted(sessions) or len(set(sessions)) != len(sessions):
        raise DataContractError("PORTFOLIO_SESSIONS_MUST_BE_UNIQUE_CHRONOLOGICAL.")
    if starting_aum <= Decimal("0"):
        raise DataContractError("PORTFOLIO_NONPOSITIVE_STARTING_AUM.")
    by_ex: Dict[date, List[DividendEvent]] = {}
    for event in dividends:
        if event.amount_per_share <= Decimal("0"):
            raise DataContractError(f"DIVIDEND_NONPOSITIVE_AMOUNT: {event.ex_date}.")
        by_ex.setdefault(event.ex_date, []).append(event)

    result = PortfolioResult(path=path)
    cash = starting_aum
    shares = 0
    state = "CASH"
    receivables: List[Tuple[date, Decimal]] = []
    peak = starting_aum
    prev_equity: Optional[Decimal] = None
    prev_close_shares = 0

    for session in sessions:
        if session not in opens_raw or session not in closes_raw:
            raise DataContractError(f"PORTFOLIO_MISSING_MARKET_PRICE: {session}.")
        raw_open = opens_raw[session]
        raw_close = closes_raw[session]
        if raw_open <= Decimal("0") or raw_close <= Decimal("0"):
            raise DataContractError(f"PORTFOLIO_NONPOSITIVE_PRICE: {session}.")

        # Dividend entitlement: shares held at the previous close own the ex-date.
        for event in by_ex.get(session, []):
            if prev_close_shares > 0:
                amount = Decimal(prev_close_shares) * event.amount_per_share
                receivables.append((event.payable_date, amount))
                result.dividends_received += amount

        # Receivables payable on/before today become spendable cash BEFORE trading.
        still_outstanding: List[Tuple[date, Decimal]] = []
        for payable, amount in receivables:
            if payable <= session:
                cash += amount
            else:
                still_outstanding.append((payable, amount))
        receivables = still_outstanding

        # State transition executes at this session's open when scheduled.
        if session in execution_by_session:
            target = execution_by_session[session]
            if target not in ("LONG", "CASH"):
                raise DataContractError(f"PORTFOLIO_UNKNOWN_TARGET_STATE: {target}.")
            if target != state:
                if target == "LONG":
                    fill = adverse_fill(raw_open, "BUY", slippage_bps)
                    quantity = int(cash // fill)
                    if quantity <= 0:
                        raise DataContractError(
                            f"PORTFOLIO_ZERO_SHARES_BUY: {session} cash={cash} fill={fill}."
                        )
                    notional = fill * Decimal(quantity)
                    if notional > cash:
                        raise DataContractError(
                            f"PORTFOLIO_INSUFFICIENT_CASH: {session}."
                        )
                    cash_before = cash
                    cash -= notional
                    if cash < Decimal("0"):
                        raise DataContractError(f"PORTFOLIO_NEGATIVE_CASH: {session}.")
                    result.trades.append(
                        TradeRecord(
                            path=path,
                            decision_date=None,
                            execution_date=session,
                            transition="CASH_TO_LONG",
                            side="BUY",
                            raw_open=raw_open,
                            fill_price=fill,
                            quantity=quantity,
                            gross_notional=notional,
                            commission=COMMISSION_BASELINE,
                            sec31_fee=Decimal("0.00"),
                            finra_taf=Decimal("0.00"),
                            cat_fee=Decimal("0.00"),
                            total_friction=Decimal("0.00"),
                            cash_before=cash_before,
                            cash_after=cash,
                            shares_before=shares,
                            shares_after=shares + quantity,
                        )
                    )
                    shares += quantity
                else:
                    fill = adverse_fill(raw_open, "SELL", slippage_bps)
                    proceeds = fill * Decimal(shares)
                    sec31, taf, cat = sell_side_fees(
                        session, shares, proceeds, fee_multiplier
                    )
                    friction = sec31 + taf + cat
                    cash_before = cash
                    cash = cash + proceeds - friction
                    result.trades.append(
                        TradeRecord(
                            path=path,
                            decision_date=None,
                            execution_date=session,
                            transition="LONG_TO_CASH",
                            side="SELL",
                            raw_open=raw_open,
                            fill_price=fill,
                            quantity=shares,
                            gross_notional=proceeds,
                            commission=COMMISSION_BASELINE,
                            sec31_fee=sec31,
                            finra_taf=taf,
                            cat_fee=cat,
                            total_friction=friction,
                            cash_before=cash_before,
                            cash_after=cash,
                            shares_before=shares,
                            shares_after=0,
                        )
                    )
                    result.total_friction += friction
                    shares = 0
                state = target

        market_value = Decimal(shares) * raw_close
        outstanding = sum((amount for _, amount in receivables), Decimal("0"))
        equity = cash + market_value + outstanding
        if equity > peak:
            peak = equity
        decline = (peak - equity) / peak if peak > Decimal("0") else Decimal("0")
        daily_return: Optional[Decimal] = None
        if prev_equity is not None:
            if prev_equity <= Decimal("0"):
                raise DataContractError(f"PORTFOLIO_NONPOSITIVE_PREV_EQUITY: {session}.")
            daily_return = equity / prev_equity - Decimal("1")
        result.equity_curve.append(
            EquityRecord(
                session=session,
                cash=cash,
                shares=shares,
                raw_close=raw_close,
                market_value=market_value,
                dividend_receivable=outstanding,
                total_equity=equity,
                daily_return=daily_return,
                running_peak=peak,
                drawdown=decline,
            )
        )
        prev_equity = equity
        prev_close_shares = shares

    result.ending_equity = prev_equity if prev_equity is not None else starting_aum
    result.ending_cash = cash
    result.ending_shares = shares
    result.terminal_receivable = sum(
        (amount for _, amount in receivables), Decimal("0")
    )
    return result
