"""D6 multi-asset baseline accounting (Decimal, fail-closed, SYNTHETIC_VERIFICATION).

Generalizes the frozen HYP_011 session order to the five registered D6
portfolios without modifying HYP_011:

1. split application to holdings (and to any frozen order targets);
2. ex-date entitlement per distribution event from holdings before the
   session's trades (net of a labelled withholding scenario) as a receivable;
3. payable-date settlement per event into spendable cash (receivables are
   never spendable);
4. scheduled orders executed at the session OPEN with adverse costs;
5. EOD valuation: cash + holdings x close + outstanding receivables.

Cash may never be negative. A run is a pure function of its inputs: any contract
violation raises and no partial result is returned. Final cash must equal cash
rebuilt independently from the trade and entitlement ledgers.

Execution timing (``execution_timing``):

- ``PRIOR_CLOSE_DECISION_NEXT_OPEN`` (PRIMARY): target share quantities are
  frozen from information through the previous admitted session close and
  executed at the next open. The first admitted session has no prior close, so
  the portfolio stays in cash and initial construction executes at the second
  admitted session; no prior close is ever synthesized.
- ``SAME_OPEN_SIZING_IDEALIZED`` (SENSITIVITY): targets sized from the open of
  the execution session itself, which an investor cannot know before submitting.

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
from typing import Dict, List, Mapping, Sequence, Tuple, Union

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.etf_fx_benchmark import (
    DistributionTaxClassification,
    EtfDistributionRecord,
    FxFixingRecord,
    HoldingsBasedBenchmark,
    resolve_fx_fixing_for_date,
)
from acash.execution.regulatory_fees import compute_finra_taf, compute_sec31_fee
from acash.research.hyp_009.accounting import DividendEvent, adverse_fill

D6_LABEL = "SYNTHETIC_VERIFICATION"
D6_INITIAL_NAV = Decimal("1000.00")
NO_CASH_DISTRIBUTION_SYMBOLS = frozenset({"GLD"})
FRACTIONAL_SHARE_QUANTUM = Decimal("0.000001")
ZERO = Decimal("0")
D6_TIMING_PRIMARY = "PRIOR_CLOSE_DECISION_NEXT_OPEN"
D6_TIMING_OPEN_SENSITIVITY = "SAME_OPEN_SIZING_IDEALIZED"

D6Distribution = Union[DividendEvent, EtfDistributionRecord]


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
    commission_max_rate: Decimal | None = None
    commission_floor: Decimal = ZERO
    clearing_per_share: Decimal = ZERO
    clearing_max_rate: Decimal | None = None
    passthrough_rate: Decimal = ZERO
    min_order_notional: Decimal = ZERO
    fractional_rate: Decimal | None = None
    exchange_per_share: Decimal = ZERO
    withholding_overrides: Tuple[Tuple[str, str, Decimal], ...] = ()

    def __post_init__(self) -> None:
        keys = [(sym, kind) for sym, kind, _ in self.withholding_overrides]
        if len(keys) != len(set(keys)):
            raise DataContractError("D6_DUPLICATE_WITHHOLDING_OVERRIDE.")
        if any(not ZERO <= rate < Decimal("1") for _, _, rate in self.withholding_overrides):
            raise DataContractError("D6_BAD_WITHHOLDING_RATE.")
        optional = [
            r for r in (self.commission_max_rate, self.clearing_max_rate, self.fractional_rate) if r is not None
        ]
        values = [
            self.exchange_per_share,
            self.slippage_bps,
            self.commission_per_share,
            self.commission_minimum,
            self.commission_floor,
            self.clearing_per_share,
            self.passthrough_rate,
            self.min_order_notional,
            *optional,
        ]
        if min(values) < ZERO:
            raise DataContractError("D6_NEGATIVE_COST_PARAMETER.")
        if not ZERO <= self.withholding_rate < Decimal("1"):
            raise DataContractError("D6_BAD_WITHHOLDING_RATE.")

    def commission(self, quantity: Decimal, notional: Decimal | None = None) -> Decimal:
        """Broker charge: per-share with minimum, value cap overriding the minimum,
        floor, plus per-share clearing (value-capped), pass-through on the base and
        an uncapped per-share venue fee. With ``fractional_rate`` a non-integer
        order is charged ``max(floor, fractional_rate x notional)`` instead."""
        if quantity <= ZERO:
            return ZERO
        capped = any(r is not None for r in (self.commission_max_rate, self.clearing_max_rate, self.fractional_rate))
        if capped and (notional is None or notional <= ZERO):
            raise DataContractError("D6_COMMISSION_CAP_REQUIRES_NOTIONAL.")
        if self.fractional_rate is not None and notional is not None and quantity != quantity.to_integral_value():
            base = max(self.commission_floor, self.fractional_rate * notional)
        else:
            base = max(self.commission_minimum, self.commission_per_share * quantity)
            if self.commission_max_rate is not None and notional is not None:
                base = min(base, self.commission_max_rate * notional)
            base = max(self.commission_floor, base)
        clearing = self.clearing_per_share * quantity
        if self.clearing_max_rate is not None and notional is not None:
            clearing = min(clearing, self.clearing_max_rate * notional)
        return base + clearing + base * self.passthrough_rate + self.exchange_per_share * quantity

    def withholding_for(self, symbol: str, distribution_type: str) -> Decimal:
        """Override by (symbol, type), then (symbol, "*"), else ``withholding_rate``."""
        table = {(sym, kind): rate for sym, kind, rate in self.withholding_overrides}
        for key in ((symbol, distribution_type), (symbol, "*")):
            if key in table:
                return table[key]
        return self.withholding_rate


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
    ordered_quantity: Decimal = ZERO


@dataclass(frozen=True)
class D6SkippedOrder:
    session: date
    symbol: str
    side: str
    ordered_quantity: Decimal
    reason: str


@dataclass(frozen=True)
class D6NavRecord:
    session: date
    cash: Decimal
    market_value: Decimal
    receivable: Decimal
    nav: Decimal


@dataclass(frozen=True)
class D6Entitlement:
    symbol: str
    ex_date: date
    payable_date: date
    distribution_type: str
    identity: Tuple[object, ...]
    gross: Decimal
    withheld: Decimal


@dataclass
class D6Result:
    portfolio: str
    cost_label: str
    execution_timing: str = D6_TIMING_PRIMARY
    label: str = D6_LABEL
    nav_curve: List[D6NavRecord] = field(default_factory=list)
    trades: List[D6Trade] = field(default_factory=list)
    skipped_orders: List[D6SkippedOrder] = field(default_factory=list)
    entitlements: List[D6Entitlement] = field(default_factory=list)
    holdings: Dict[str, Decimal] = field(default_factory=dict)
    ending_cash: Decimal = ZERO
    terminal_receivable: Decimal = ZERO
    terminal_nav: Decimal = ZERO
    dividends_gross: Decimal = ZERO
    withholding: Decimal = ZERO
    commissions: Decimal = ZERO
    regulatory_fees: Decimal = ZERO
    contributions: List[Tuple[date, Decimal]] = field(default_factory=list)
    contributed: Decimal = ZERO


@dataclass(frozen=True)
class _Event:
    ex_date: date
    payable_date: date
    amount_per_share: Decimal
    distribution_type: str
    identity: Tuple[object, ...]


def first_sessions_of_year(sessions: Sequence[date]) -> tuple[date, ...]:
    firsts: dict[int, date] = {}
    for session in sessions:
        firsts.setdefault(session.year, session)
    return tuple(firsts.values())


def _quantize(quantity: Decimal, whole_shares: bool) -> Decimal:
    quantum = Decimal("1") if whole_shares else FRACTIONAL_SHARE_QUANTUM
    return quantity.quantize(quantum, rounding=ROUND_DOWN)


def _price(table: Mapping[str, Mapping[date, Decimal]], kind: str, sym: str, session: date) -> Decimal:
    try:
        price = table[sym][session]
    except KeyError:
        raise DataContractError(f"D6_MISSING_{kind}_PRICE: {sym} {session}; no fallback.") from None
    if price <= ZERO:
        raise DataContractError(f"D6_NONPOSITIVE_PRICE: {sym} {session}.")
    return price


def _normalize_events(
    sym: str, events: Sequence[D6Distribution], splits: Mapping[date, Decimal]
) -> Dict[date, List[_Event]]:
    """Index events by ex-date without merging; reject duplicates and revisions."""
    by_ex: Dict[date, List[_Event]] = {}
    seen: set[Tuple[object, ...]] = set()
    provider_ids: Dict[str, Tuple[object, ...]] = {}
    for event in events:
        if isinstance(event, EtfDistributionRecord):
            if event.symbol != sym:
                raise DataContractError(f"D6_DISTRIBUTION_SYMBOL_MISMATCH: {event.symbol} != {sym}.")
            if (
                event.net_amount is not None
                or event.tax_classification is not DistributionTaxClassification.GROSS_BEFORE_WITHHOLDING
            ):
                raise DataContractError(
                    f"D6_GROSS_RECORD_REQUIRED: {sym} {event.ex_date}; withholding is a D6 cost scenario."
                )
            identity: Tuple[object, ...] = HoldingsBasedBenchmark._entitlement_key(event)
            if event.event_id is not None:
                prior = provider_ids.setdefault(event.event_id, identity)
                if prior != identity:
                    raise DataContractError(f"D6_REVISED_EVENT: {sym} event_id {event.event_id}.")
            item = _Event(event.ex_date, event.payable_date, event.gross_amount, event.distribution_type, identity)
        else:
            identity = (sym, event.ex_date, event.payable_date, "DIVIDEND_CASH", str(event.amount_per_share))
            item = _Event(event.ex_date, event.payable_date, event.amount_per_share, "DIVIDEND_CASH", identity)
        if item.payable_date < item.ex_date or item.amount_per_share <= ZERO:
            raise DataContractError(f"D6_BAD_DIVIDEND: {sym} {item.ex_date}.")
        if item.ex_date in splits:
            raise DataContractError(f"D6_SPLIT_AND_EX_DATE_SAME_SESSION_UNSUPPORTED: {sym}.")
        if identity in seen:
            raise DataContractError(f"D6_DUPLICATE_DISTRIBUTION: {sym} {item.ex_date} {item.distribution_type}.")
        seen.add(identity)
        by_ex.setdefault(item.ex_date, []).append(item)
    return by_ex


def run_d6_portfolio(
    portfolio: D6Portfolio,
    *,
    sessions: Sequence[date],
    opens: Mapping[str, Mapping[date, Decimal]],
    closes: Mapping[str, Mapping[date, Decimal]],
    dividends: Mapping[str, Sequence[D6Distribution]],
    splits: Mapping[str, Mapping[date, Decimal]] | None = None,
    cost: D6CostModel,
    price_adjustment: str = "raw",
    whole_shares: bool = False,
    initial_nav: Decimal = D6_INITIAL_NAV,
    execution_timing: str = D6_TIMING_PRIMARY,
    contributions: Mapping[date, Decimal] | None = None,
) -> D6Result:
    """``contributions`` are external cash flows credited at the start of the
    given session; spendable cash is deployed buy-only by weight, decided at that
    session's close and executed at the next open (annual rebalance precedes)."""
    if price_adjustment != "raw":
        raise DataContractError(
            f"D6_ADJUSTED_PRICES_REJECTED: {price_adjustment!r}; explicit distributions "
            "require raw prices."
        )
    if execution_timing not in (D6_TIMING_PRIMARY, D6_TIMING_OPEN_SENSITIVITY):
        raise DataContractError(f"D6_UNKNOWN_EXECUTION_TIMING: {execution_timing!r}.")
    ordered = list(sessions)
    if not ordered or ordered != sorted(set(ordered)):
        raise DataContractError("D6_SESSIONS_MUST_BE_UNIQUE_CHRONOLOGICAL.")
    splits = splits or {}
    symbols = sorted(portfolio.weights)
    for sym in sorted(dividends):
        if dividends[sym] and sym in NO_CASH_DISTRIBUTION_SYMBOLS:
            raise DataContractError(f"D6_NO_CASH_DISTRIBUTION_ENTITLEMENT: {sym}.")
    by_ex = {sym: _normalize_events(sym, dividends.get(sym, ()), splits.get(sym, {})) for sym in symbols}

    yearly = set(first_sessions_of_year(ordered))
    if execution_timing == D6_TIMING_PRIMARY:
        execute_at = {s for s in ordered[1:] if s in yearly}
        if len(ordered) > 1:
            execute_at.add(ordered[1])
    else:
        execute_at = yearly

    contributions = dict(contributions or {})
    if contributions:
        if execution_timing != D6_TIMING_PRIMARY:
            raise DataContractError("D6_CONTRIBUTIONS_REQUIRE_PRIMARY_TIMING.")
        known = set(ordered)
        for day, amount in contributions.items():
            if day not in known:
                raise DataContractError(f"D6_CONTRIBUTION_NOT_A_SESSION: {day}.")
            if day == ordered[0]:
                raise DataContractError(f"D6_CONTRIBUTION_ON_INITIAL_SESSION: {day}.")
            if amount <= ZERO:
                raise DataContractError(f"D6_NONPOSITIVE_CONTRIBUTION: {day} {amount}.")
    deploy_at = {ordered[i + 1] for i, s in enumerate(ordered[:-1]) if s in contributions} - execute_at

    result = D6Result(portfolio=portfolio.name, cost_label=cost.label, execution_timing=execution_timing)
    cash = initial_nav
    flows = ZERO
    holdings: Dict[str, Decimal] = {sym: ZERO for sym in symbols}
    receivables: List[D6Entitlement] = []
    frozen: Dict[str, Decimal] | None = None

    for index, session in enumerate(ordered):
        session_opens = {sym: _price(opens, "OPEN", sym, session) for sym in symbols}
        session_closes = {sym: _price(closes, "CLOSE", sym, session) for sym in symbols}

        for sym in symbols:
            ratio = splits.get(sym, {}).get(session)
            if ratio is not None:
                if ratio <= ZERO:
                    raise DataContractError(f"D6_BAD_SPLIT_RATIO: {sym} {session}.")
                adjusted = holdings[sym] * ratio
                if whole_shares and adjusted != adjusted.to_integral_value():
                    raise DataContractError(f"D6_SPLIT_CASH_IN_LIEU_UNSUPPORTED: {sym} {session}.")
                holdings[sym] = adjusted
                if frozen is not None:
                    frozen[sym] = _quantize(frozen[sym] * ratio, whole_shares)

        for sym in symbols:
            for item in by_ex[sym].get(session, ()):
                if holdings[sym] <= ZERO:
                    continue
                gross = holdings[sym] * item.amount_per_share
                withheld = gross * cost.withholding_for(sym, item.distribution_type)
                entitlement = D6Entitlement(
                    sym, item.ex_date, item.payable_date, item.distribution_type, item.identity, gross, withheld
                )
                result.entitlements.append(entitlement)
                result.dividends_gross += gross
                result.withholding += withheld
                receivables.append(entitlement)

        outstanding: List[D6Entitlement] = []
        for ent in receivables:
            if ent.payable_date <= session:
                cash += ent.gross - ent.withheld
                flows += ent.gross - ent.withheld
            else:
                outstanding.append(ent)
        receivables = outstanding

        added = contributions.get(session)
        if added is not None:
            cash += added
            result.contributed += added
            result.contributions.append((session, added))

        if (session in execute_at or session in deploy_at) and symbols:
            if execution_timing == D6_TIMING_OPEN_SENSITIVITY:
                frozen = _target_shares(portfolio, cash, holdings, session_opens, whole_shares)
            if frozen is None:
                raise DataContractError(f"D6_NO_CAUSAL_DECISION: {session}.")
            cash, flows = _execute(session, frozen, cash, flows, holdings, session_opens, cost, whole_shares, result)
        frozen = None

        if cash < ZERO:
            raise DataContractError(f"D6_NEGATIVE_CASH: {session} {cash}; borrowing is prohibited.")
        market_value = sum((holdings[s] * session_closes[s] for s in symbols), ZERO)
        receivable = sum((e.gross - e.withheld for e in receivables), ZERO)
        result.nav_curve.append(
            D6NavRecord(session, cash, market_value, receivable, cash + market_value + receivable)
        )

        nxt = ordered[index + 1] if index + 1 < len(ordered) else None
        if execution_timing == D6_TIMING_PRIMARY and nxt in execute_at and symbols:
            frozen = _target_shares(portfolio, cash, holdings, session_closes, whole_shares)
        elif nxt in deploy_at and symbols:
            frozen = _buy_only_targets(portfolio, cash, holdings, session_closes, whole_shares)

    total_in = initial_nav + result.contributed
    if total_in + flows != cash or _reconstruct_cash(result, initial_nav, ordered[-1]) != cash:
        raise DataContractError("D6_CASH_CONSERVATION_VIOLATED.")
    result.holdings = dict(holdings)
    result.ending_cash = cash
    result.terminal_receivable = result.nav_curve[-1].receivable
    result.terminal_nav = result.nav_curve[-1].nav
    return result


def _target_shares(
    portfolio: D6Portfolio,
    cash: Decimal,
    holdings: Mapping[str, Decimal],
    prices: Mapping[str, Decimal],
    whole_shares: bool,
) -> Dict[str, Decimal]:
    """Target quantities from spendable value (receivables excluded) at ``prices``."""
    symbols = sorted(portfolio.weights)
    value = cash + sum((holdings[s] * prices[s] for s in symbols), ZERO)
    return {s: _quantize(portfolio.weights[s] * value / prices[s], whole_shares) for s in symbols}


def _buy_only_targets(
    portfolio: D6Portfolio,
    cash: Decimal,
    holdings: Mapping[str, Decimal],
    prices: Mapping[str, Decimal],
    whole_shares: bool,
) -> Dict[str, Decimal]:
    """Holdings plus spendable cash split by weight at ``prices``; never sells."""
    return {
        s: holdings[s] + _quantize(portfolio.weights[s] * cash / prices[s], whole_shares)
        for s in sorted(portfolio.weights)
    }


def _execute(
    session: date,
    targets: Mapping[str, Decimal],
    cash: Decimal,
    flows: Decimal,
    holdings: Dict[str, Decimal],
    opens: Mapping[str, Decimal],
    cost: D6CostModel,
    whole_shares: bool,
    result: D6Result,
) -> tuple[Decimal, Decimal]:
    """Sells first, then buys; buys scale down (partial) if open gaps exhaust cash.

    A sell whose proceeds do not exceed its commission and fees is skipped
    (``UNECONOMIC_SELL_SKIPPED``); a buy that cannot be funded after scaling is
    skipped (``INSUFFICIENT_CASH_SKIPPED``). Both are recorded; nothing borrows.
    """
    for sym in sorted(targets):
        quantity = min(holdings[sym], holdings[sym] - targets[sym])
        if quantity <= ZERO:
            continue
        fill = adverse_fill(opens[sym], "SELL", cost.slippage_bps)
        notional = fill * quantity
        if notional < cost.min_order_notional:
            result.skipped_orders.append(
                D6SkippedOrder(session, sym, "SELL", quantity, "BELOW_MIN_NOTIONAL_SKIPPED")
            )
            continue
        fees = ZERO
        if cost.regulatory_fees:
            fees = compute_sec31_fee(session, notional) + compute_finra_taf(session, quantity)
        commission = cost.commission(quantity, notional)
        delta = notional - fees - commission
        if delta <= ZERO:
            result.skipped_orders.append(
                D6SkippedOrder(session, sym, "SELL", quantity, "UNECONOMIC_SELL_SKIPPED")
            )
            continue
        cash += delta
        flows += delta
        holdings[sym] -= quantity
        result.commissions += commission
        result.regulatory_fees += fees
        result.trades.append(
            D6Trade(session, sym, "SELL", quantity, opens[sym], fill, notional, commission, fees, quantity)
        )
    wanted = {s: targets[s] - holdings[s] for s in targets if targets[s] > holdings[s]}
    fills = {s: adverse_fill(opens[s], "BUY", cost.slippage_bps) for s in wanted}
    gross = sum((wanted[s] * fills[s] for s in wanted), ZERO)
    reserved = sum((cost.commission(wanted[s], wanted[s] * fills[s]) for s in wanted), ZERO)
    scale = Decimal("1")
    if gross > ZERO and gross + reserved > cash:
        scale = max(ZERO, cash - reserved) / gross
    for sym in sorted(wanted):
        quantity = _quantize(wanted[sym] * scale, whole_shares)
        if quantity <= ZERO:
            result.skipped_orders.append(
                D6SkippedOrder(session, sym, "BUY", wanted[sym], "INSUFFICIENT_CASH_SKIPPED")
            )
            continue
        notional = fills[sym] * quantity
        if notional < cost.min_order_notional:
            result.skipped_orders.append(
                D6SkippedOrder(session, sym, "BUY", wanted[sym], "BELOW_MIN_NOTIONAL_SKIPPED")
            )
            continue
        commission = cost.commission(quantity, notional)
        if notional + commission > cash:
            raise DataContractError(f"D6_NEGATIVE_CASH_GUARD: {session} {sym}.")
        cash -= notional + commission
        flows -= notional + commission
        holdings[sym] += quantity
        result.commissions += commission
        result.trades.append(
            D6Trade(session, sym, "BUY", quantity, opens[sym], fills[sym], notional, commission, ZERO, wanted[sym])
        )
    return cash, flows


def _reconstruct_cash(result: D6Result, initial_nav: Decimal, last_session: date) -> Decimal:
    """Cash rebuilt only from the trade, entitlement and contribution ledgers."""
    cash = initial_nav + sum((amount for _, amount in result.contributions), ZERO)
    for t in result.trades:
        if t.side == "BUY":
            cash -= t.notional + t.commission
        else:
            cash += t.notional - t.commission - t.regulatory_fees
    for e in result.entitlements:
        if e.payable_date <= last_session:
            cash += e.gross - e.withheld
    return cash


def d6_nav_in_currency(
    nav_curve: Sequence[D6NavRecord],
    fixings: Mapping[date, FxFixingRecord],
    *,
    currency: str,
) -> List[Tuple[date, Decimal]]:
    """Reporting overlay only: USD NAV converted at exact-date fixings (no fallback)."""
    return [
        (r.session, resolve_fx_fixing_for_date(fixings, r.session).convert(r.nav, "USD", currency))
        for r in nav_curve
    ]


__all__ = [
    "D6_INITIAL_NAV",
    "D6_LABEL",
    "D6_REGISTERED_PORTFOLIOS",
    "D6_TIMING_OPEN_SENSITIVITY",
    "D6_TIMING_PRIMARY",
    "D6CostModel",
    "D6Distribution",
    "D6Entitlement",
    "D6NavRecord",
    "D6Portfolio",
    "D6Result",
    "D6SkippedOrder",
    "D6Trade",
    "NO_CASH_DISTRIBUTION_SYMBOLS",
    "d6_nav_in_currency",
    "first_sessions_of_year",
    "run_d6_portfolio",
]
