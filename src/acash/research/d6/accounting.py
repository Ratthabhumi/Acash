"""D6 multi-asset baseline accounting (Decimal, fail-closed, SYNTHETIC_VERIFICATION).

Generalizes the frozen HYP_011 session order to the five registered D6
portfolios without modifying HYP_011:

1. split application to holdings;
2. ex-date entitlement from holdings at the prior close (net of a labelled
   withholding scenario) recorded as a receivable;
3. payable-date settlement into spendable cash (receivables are never spendable);
4. scheduled rebalance at the session OPEN (never at a close already observed);
5. EOD valuation: cash + holdings x close + outstanding receivables.

Prices must be RAW (unadjusted): explicit cash distributions on adjusted
total-return prices would double count. ETF expense ratios are already in the
observed price and are never deducted again. Symbols in
``NO_CASH_DISTRIBUTION_SYMBOLS`` (GLD) reject cash distributions. Regulatory
fees reuse ``acash.execution.regulatory_fees`` (statutory rates, not
account-verified broker pass-through).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, Decimal
from typing import Dict, List, Mapping, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.execution.regulatory_fees import compute_finra_taf, compute_sec31_fee
from acash.research.hyp_009.accounting import DividendEvent, adverse_fill

D6_LABEL = "SYNTHETIC_VERIFICATION"
D6_INITIAL_NAV = Decimal("1000.00")
NO_CASH_DISTRIBUTION_SYMBOLS = frozenset({"GLD"})
FRACTIONAL_SHARE_QUANTUM = Decimal("0.000001")
ZERO = Decimal("0")


@dataclass(frozen=True)
class D6Portfolio:
    name: str
    weights: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        total = sum(self.weights.values(), ZERO)
        if any(w <= ZERO for w in self.weights.values()) or total > Decimal("1"):
            raise DataContractError(f"D6_BAD_WEIGHTS: {self.name}.")


D6_REGISTERED_PORTFOLIOS: tuple[D6Portfolio, ...] = (
    D6Portfolio("CASH_NO_TRADE", {}),
    D6Portfolio("BIL_100", {"BIL": Decimal("1")}),
    D6Portfolio("VOO_100", {"VOO": Decimal("1")}),
    D6Portfolio("VOO_BND_60_40", {"VOO": Decimal("0.60"), "BND": Decimal("0.40")}),
    D6Portfolio(
        "VOO_BND_GLD_BIL_50_30_10_10",
        {"VOO": Decimal("0.50"), "BND": Decimal("0.30"), "GLD": Decimal("0.10"), "BIL": Decimal("0.10")},
    ),
)


@dataclass(frozen=True)
class D6CostModel:
    """Named execution-cost scenario; zero cost is only a labelled upper bound."""

    label: str
    slippage_bps: Decimal = ZERO
    commission_per_share: Decimal = ZERO
    commission_minimum: Decimal = ZERO
    regulatory_fees: bool = False
    withholding_rate: Decimal = ZERO

    def __post_init__(self) -> None:
        if min(self.slippage_bps, self.commission_per_share, self.commission_minimum) < ZERO:
            raise DataContractError("D6_NEGATIVE_COST_PARAMETER.")
        if not ZERO <= self.withholding_rate < Decimal("1"):
            raise DataContractError("D6_BAD_WITHHOLDING_RATE.")

    def commission(self, quantity: Decimal) -> Decimal:
        if quantity <= ZERO:
            return ZERO
        return max(self.commission_minimum, self.commission_per_share * quantity)


@dataclass(frozen=True)
class D6Trade:
    session: date
    symbol: str
    side: str
    quantity: Decimal
    open_price: Decimal
    fill_price: Decimal
    notional: Decimal
    commission: Decimal
    regulatory_fees: Decimal


@dataclass(frozen=True)
class D6NavRecord:
    session: date
    cash: Decimal
    market_value: Decimal
    receivable: Decimal
    nav: Decimal


@dataclass
class D6Result:
    portfolio: str
    cost_label: str
    label: str = D6_LABEL
    nav_curve: List[D6NavRecord] = field(default_factory=list)
    trades: List[D6Trade] = field(default_factory=list)
    holdings: Dict[str, Decimal] = field(default_factory=dict)
    ending_cash: Decimal = ZERO
    terminal_receivable: Decimal = ZERO
    terminal_nav: Decimal = ZERO
    dividends_gross: Decimal = ZERO
    withholding: Decimal = ZERO
    commissions: Decimal = ZERO
    regulatory_fees: Decimal = ZERO


def first_sessions_of_year(sessions: Sequence[date]) -> tuple[date, ...]:
    firsts: dict[int, date] = {}
    for session in sessions:
        firsts.setdefault(session.year, session)
    return tuple(firsts.values())


def _quantize(quantity: Decimal, whole_shares: bool) -> Decimal:
    quantum = Decimal("1") if whole_shares else FRACTIONAL_SHARE_QUANTUM
    return quantity.quantize(quantum, rounding=ROUND_DOWN)


def run_d6_portfolio(
    portfolio: D6Portfolio,
    *,
    sessions: Sequence[date],
    opens: Mapping[str, Mapping[date, Decimal]],
    closes: Mapping[str, Mapping[date, Decimal]],
    dividends: Mapping[str, Sequence[DividendEvent]],
    splits: Mapping[str, Mapping[date, Decimal]] | None = None,
    cost: D6CostModel,
    price_adjustment: str = "raw",
    whole_shares: bool = False,
    initial_nav: Decimal = D6_INITIAL_NAV,
) -> D6Result:
    if price_adjustment != "raw":
        raise DataContractError(
            f"D6_ADJUSTED_PRICES_REJECTED: {price_adjustment!r}; explicit distributions "
            "require raw prices."
        )
    ordered = list(sessions)
    if not ordered or ordered != sorted(set(ordered)):
        raise DataContractError("D6_SESSIONS_MUST_BE_UNIQUE_CHRONOLOGICAL.")
    splits = splits or {}
    symbols = sorted(portfolio.weights)
    for sym in sorted(dividends):
        if dividends[sym] and sym in NO_CASH_DISTRIBUTION_SYMBOLS:
            raise DataContractError(f"D6_NO_CASH_DISTRIBUTION_ENTITLEMENT: {sym}.")
        for event in dividends[sym]:
            if event.payable_date < event.ex_date or event.amount_per_share < ZERO:
                raise DataContractError(f"D6_BAD_DIVIDEND: {sym} {event.ex_date}.")
            if event.ex_date in splits.get(sym, {}):
                raise DataContractError(f"D6_SPLIT_AND_EX_DATE_SAME_SESSION_UNSUPPORTED: {sym}.")
    by_ex = {sym: {e.ex_date: e for e in dividends.get(sym, ())} for sym in symbols}
    rebalance_set = set(first_sessions_of_year(ordered))

    result = D6Result(portfolio=portfolio.name, cost_label=cost.label)
    cash = initial_nav
    flows = ZERO
    holdings: Dict[str, Decimal] = {sym: ZERO for sym in symbols}
    receivables: List[tuple[date, Decimal]] = []

    for session in ordered:
        session_opens = {sym: opens[sym][session] for sym in symbols}
        session_closes = {sym: closes[sym][session] for sym in symbols}
        if any(p <= ZERO for p in [*session_opens.values(), *session_closes.values()]):
            raise DataContractError(f"D6_NONPOSITIVE_PRICE: {session}.")

        for sym in symbols:
            ratio = splits.get(sym, {}).get(session)
            if ratio is not None:
                if ratio <= ZERO:
                    raise DataContractError(f"D6_BAD_SPLIT_RATIO: {sym} {session}.")
                adjusted = holdings[sym] * ratio
                if whole_shares and adjusted != adjusted.to_integral_value():
                    raise DataContractError(f"D6_SPLIT_CASH_IN_LIEU_UNSUPPORTED: {sym} {session}.")
                holdings[sym] = adjusted

        for sym in symbols:
            ex_event = by_ex[sym].get(session)
            if ex_event is not None and holdings[sym] > ZERO:
                gross = holdings[sym] * ex_event.amount_per_share
                withheld = gross * cost.withholding_rate
                result.dividends_gross += gross
                result.withholding += withheld
                receivables.append((ex_event.payable_date, gross - withheld))

        outstanding: List[tuple[date, Decimal]] = []
        for payable, amount in receivables:
            if payable <= session:
                cash += amount
                flows += amount
            else:
                outstanding.append((payable, amount))
        receivables = outstanding

        if session in rebalance_set and symbols:
            cash, flows = _rebalance(
                session, portfolio, cash, flows, holdings, session_opens, cost, whole_shares, result
            )

        market_value = sum((holdings[s] * session_closes[s] for s in symbols), ZERO)
        receivable = sum((a for _, a in receivables), ZERO)
        result.nav_curve.append(
            D6NavRecord(session, cash, market_value, receivable, cash + market_value + receivable)
        )

    if initial_nav + flows != cash:
        raise DataContractError("D6_CASH_CONSERVATION_VIOLATED.")
    result.holdings = dict(holdings)
    result.ending_cash = cash
    result.terminal_receivable = result.nav_curve[-1].receivable
    result.terminal_nav = result.nav_curve[-1].nav
    return result


def _rebalance(
    session: date,
    portfolio: D6Portfolio,
    cash: Decimal,
    flows: Decimal,
    holdings: Dict[str, Decimal],
    opens: Mapping[str, Decimal],
    cost: D6CostModel,
    whole_shares: bool,
    result: D6Result,
) -> tuple[Decimal, Decimal]:
    symbols = sorted(portfolio.weights)
    value = cash + sum((holdings[s] * opens[s] for s in symbols), ZERO)
    for sym in symbols:
        excess = holdings[sym] * opens[sym] - portfolio.weights[sym] * value
        if excess <= ZERO:
            continue
        quantity = min(holdings[sym], _quantize(excess / opens[sym], whole_shares))
        if quantity <= ZERO:
            continue
        fill = adverse_fill(opens[sym], "SELL", cost.slippage_bps)
        notional = fill * quantity
        fees = ZERO
        if cost.regulatory_fees:
            fees = compute_sec31_fee(session, notional) + compute_finra_taf(session, quantity)
        commission = cost.commission(quantity)
        delta = notional - fees - commission
        cash += delta
        flows += delta
        holdings[sym] -= quantity
        result.commissions += commission
        result.regulatory_fees += fees
        result.trades.append(
            D6Trade(session, sym, "SELL", quantity, opens[sym], fill, notional, commission, fees)
        )
    targets = {
        sym: portfolio.weights[sym] * value - holdings[sym] * opens[sym] for sym in symbols
    }
    targets = {sym: t for sym, t in targets.items() if t > ZERO}
    fills = {sym: adverse_fill(opens[sym], "BUY", cost.slippage_bps) for sym in targets}
    reserved = sum((cost.commission(targets[s] / fills[s]) for s in targets), ZERO)
    requested = sum(targets.values(), ZERO)
    scale = Decimal("1")
    if requested > ZERO and requested + reserved > cash:
        scale = max(ZERO, cash - reserved) / requested
    for sym in sorted(targets):
        quantity = _quantize(targets[sym] * scale / fills[sym], whole_shares)
        if quantity <= ZERO:
            continue
        notional = fills[sym] * quantity
        commission = cost.commission(quantity)
        if notional + commission > cash:
            raise DataContractError(f"D6_NEGATIVE_CASH_GUARD: {session} {sym}.")
        cash -= notional + commission
        flows -= notional + commission
        holdings[sym] += quantity
        result.commissions += commission
        result.trades.append(
            D6Trade(session, sym, "BUY", quantity, opens[sym], fills[sym], notional, commission, ZERO)
        )
    return cash, flows


__all__ = [
    "D6_INITIAL_NAV",
    "D6_LABEL",
    "D6_REGISTERED_PORTFOLIOS",
    "D6CostModel",
    "D6NavRecord",
    "D6Portfolio",
    "D6Result",
    "D6Trade",
    "NO_CASH_DISTRIBUTION_SYMBOLS",
    "first_sessions_of_year",
    "run_d6_portfolio",
]
