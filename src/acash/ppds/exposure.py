"""PPDS read-only skeleton: exposure / overlap / FX (pure functions).

All market prices and FX rates are EXPLICIT caller-supplied inputs (synthetic
fixtures). Nothing here fetches prices, rates, or holdings from any live
source. All arithmetic is exact Decimal; division by zero fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Mapping, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.ppds.ledger import NormalizedPortfolioLedger


@dataclass(frozen=True)
class ExposureLine:
    key: str
    market_value: str
    weight: str


def _require_price(prices: Mapping[str, Decimal], symbol: str) -> Decimal:
    try:
        price = prices[symbol]
    except (KeyError, TypeError) as exc:
        raise DataContractError(f"PPDS_PRICE_MISSING: {symbol}.") from exc
    if not isinstance(price, Decimal) or not price.is_finite() or price <= Decimal("0"):
        raise DataContractError(f"PPDS_PRICE_INVALID: {symbol}.")
    return price


def position_exposure(
    ledger: NormalizedPortfolioLedger, prices: Mapping[str, Decimal]
) -> List[ExposureLine]:
    """Gross absolute per-symbol market-value concentration with exact weights (sum to 1).

    Semantics:
    - Calculates gross absolute concentration using abs(quantity).
    - Requires all positions to share a single currency domain. If multiple currencies
      are present, fails closed with DataContractError until explicit FX conversion is supplied.
    - Does NOT represent net directional exposure or multi-currency portfolio allocation.
    """
    currencies = {lot.currency for lot in ledger.position_lots}
    if len(currencies) > 1:
        raise DataContractError(
            f"PPDS_EXPOSURE_MULTI_CURRENCY: positions span multiple currencies {sorted(currencies)}; "
            "cannot aggregate gross exposure without explicit FX conversion."
        )

    quantities = ledger.quantity_by_symbol()
    values: Dict[str, Decimal] = {}
    for symbol, quantity in quantities.items():
        values[symbol] = abs(quantity) * _require_price(prices, symbol)
    total = sum(values.values(), Decimal("0"))
    if total <= Decimal("0"):
        raise DataContractError("PPDS_EXPOSURE_EMPTY.")
    lines = []
    for symbol in sorted(values):
        weight = values[symbol] / total
        lines.append(ExposureLine(
            key=symbol, market_value=str(values[symbol]), weight=str(weight),
        ))
    return lines


def etf_overlap_exposure(
    ledger: NormalizedPortfolioLedger,
    prices: Mapping[str, Decimal],
    constituent_weights: Mapping[str, Mapping[str, Decimal]],
) -> List[ExposureLine]:
    """Holdings-based ETF overlap decomposition (synthetic holdings only).

    constituent_weights maps ETF symbol -> {constituent symbol: weight}, with
    weights summing to exactly 1 per ETF. Constituent prices come from the
    explicit prices map.
    """
    currencies = {lot.currency for lot in ledger.position_lots}
    if len(currencies) > 1:
        raise DataContractError(
            f"PPDS_EXPOSURE_MULTI_CURRENCY: ETF overlap positions span multiple currencies {sorted(currencies)}; "
            "cannot aggregate decomposition without explicit FX conversion."
        )
    decomposed: Dict[str, Decimal] = {}
    for lot in ledger.position_lots:
        weights = constituent_weights.get(lot.symbol)
        if weights is None:
            continue
        total_w = sum(weights.values(), Decimal("0"))
        if total_w != Decimal("1"):
            raise DataContractError(
                f"PPDS_OVERLAP_WEIGHTS_INVALID: {lot.symbol} sums to {total_w}."
            )
        leg_value = abs(lot.quantity) * _require_price(prices, lot.symbol)
        for constituent, weight in weights.items():
            if not isinstance(weight, Decimal) or not weight.is_finite() or weight < Decimal("0"):
                raise DataContractError(f"PPDS_OVERLAP_WEIGHT_INVALID: {constituent}.")
            decomposed[constituent] = (
                decomposed.get(constituent, Decimal("0")) + leg_value * weight
            )
    total = sum(decomposed.values(), Decimal("0"))
    if total <= Decimal("0"):
        raise DataContractError("PPDS_OVERLAP_EMPTY.")
    return [
        ExposureLine(key=k, market_value=str(v), weight=str(v / total))
        for k, v in sorted(decomposed.items())
    ]


def fx_exposure(
    ledger: NormalizedPortfolioLedger,
    fx_to_usd: Mapping[str, Decimal],
) -> List[ExposureLine]:
    """Per-currency cash exposure converted to USD via explicit rates."""
    cash = ledger.cash_by_currency()
    converted: Dict[str, Decimal] = {}
    for currency, amount in cash.items():
        try:
            rate = fx_to_usd[currency]
        except (KeyError, TypeError) as exc:
            raise DataContractError(f"PPDS_FX_RATE_MISSING: {currency}.") from exc
        if not isinstance(rate, Decimal) or not rate.is_finite() or rate <= Decimal("0"):
            raise DataContractError(f"PPDS_FX_RATE_INVALID: {currency}.")
        converted[currency] = abs(amount) * rate
    total = sum(converted.values(), Decimal("0"))
    if total <= Decimal("0"):
        raise DataContractError("PPDS_FX_EMPTY.")
    return [
        ExposureLine(key=k, market_value=str(v), weight=str(v / total))
        for k, v in sorted(converted.items())
    ]


def gross_lots_exposure(
    ledger: NormalizedPortfolioLedger, prices: Mapping[str, Decimal]
) -> List[ExposureLine]:
    """Gross absolute exposure across underlying lots without offsetting per-symbol netting.

    Each lot's absolute quantity (abs(quantity) * price) is summed independently.
    """
    currencies = {lot.currency for lot in ledger.position_lots}
    if len(currencies) > 1:
        raise DataContractError(
            f"PPDS_EXPOSURE_MULTI_CURRENCY: positions span multiple currencies {sorted(currencies)}; "
            "cannot aggregate gross exposure without explicit FX conversion."
        )
    values: Dict[str, Decimal] = {}
    for lot in ledger.position_lots:
        price = _require_price(prices, lot.symbol)
        values[lot.symbol] = values.get(lot.symbol, Decimal("0")) + abs(lot.quantity) * price
    total = sum(values.values(), Decimal("0"))
    if total <= Decimal("0"):
        raise DataContractError("PPDS_EXPOSURE_EMPTY.")
    return [
        ExposureLine(key=k, market_value=str(v), weight=str(v / total))
        for k, v in sorted(values.items())
    ]


def net_signed_exposure(
    ledger: NormalizedPortfolioLedger, prices: Mapping[str, Decimal]
) -> List[ExposureLine]:
    """Net directional exposure per-symbol (long = positive, short = negative).

    Weights are relative to total gross portfolio commitment sum(abs(net_mv)).
    """
    currencies = {lot.currency for lot in ledger.position_lots}
    if len(currencies) > 1:
        raise DataContractError(
            f"PPDS_EXPOSURE_MULTI_CURRENCY: positions span multiple currencies {sorted(currencies)}; "
            "cannot aggregate net exposure without explicit FX conversion."
        )
    quantities = ledger.quantity_by_symbol()
    values: Dict[str, Decimal] = {}
    for symbol, quantity in quantities.items():
        values[symbol] = quantity * _require_price(prices, symbol)
    total_gross = sum((abs(v) for v in values.values()), Decimal("0"))
    if total_gross <= Decimal("0"):
        raise DataContractError("PPDS_EXPOSURE_EMPTY.")
    return [
        ExposureLine(key=k, market_value=str(v), weight=str(v / total_gross))
        for k, v in sorted(values.items())
    ]


@dataclass(frozen=True)
class PriceQuote:
    """Explicit synthetic price quote for position valuation."""

    symbol: str
    price: Decimal
    as_of: date
    currency: str
    source_id: str


@dataclass(frozen=True)
class FXRate:
    """Explicit multiplier converting 1 unit of from_currency into to_currency."""

    from_currency: str
    to_currency: str
    rate: Decimal
    as_of: date
    source_id: str


@dataclass(frozen=True)
class ValuedPosition:
    """Valuation line for an instrument position with exact local and base currency values."""

    symbol: str
    net_quantity: Decimal
    gross_quantity: Decimal
    pricing_currency: str
    price: Decimal
    price_as_of: date
    net_market_value_local: Decimal
    gross_market_value_local: Decimal
    fx_rate_to_base: Decimal
    net_market_value_base: Decimal
    gross_market_value_base: Decimal


@dataclass(frozen=True)
class PortfolioValuation:
    """Comprehensive single or multi-currency portfolio valuation in explicit base currency."""

    as_of: date
    base_currency: str
    account_id: str
    cash_local: Dict[str, Decimal]
    cash_base: Dict[str, Decimal]
    total_cash_base: Decimal
    positions: List[ValuedPosition]
    total_positions_gross_base: Decimal
    total_positions_net_base: Decimal
    total_portfolio_nav_base: Decimal


def evaluate_portfolio_base_currency(
    ledger: NormalizedPortfolioLedger,
    base_currency: str,
    as_of: date,
    prices: Mapping[str, PriceQuote],
    fx_rates: Mapping[Tuple[str, str], FXRate],
) -> PortfolioValuation:
    """Evaluate full portfolio cash and positions into explicit base currency (pure function).

    Fails closed:
    - Missing or non-positive / non-finite prices or FX rates
    - Stale or mismatched price/FX as-of dates
    - Mismatched instrument currency vs quote currency
    """
    clean_base = str(base_currency or "").strip().upper()
    if len(clean_base) != 3 or not clean_base.isalpha():
        raise DataContractError(f"PPDS_VALUATION_BASE_CURRENCY_INVALID: '{base_currency}'.")

    # 1. Value cash lots
    cash_local = ledger.cash_by_currency()
    cash_base: Dict[str, Decimal] = {}
    for currency, amount in sorted(cash_local.items()):
        if currency == clean_base:
            fx_mult = Decimal("1")
        else:
            fx_key = (currency, clean_base)
            if fx_key not in fx_rates:
                raise DataContractError(
                    f"PPDS_VALUATION_FX_RATE_MISSING: missing FX conversion {currency}->{clean_base}."
                )
            fx = fx_rates[fx_key]
            if fx.as_of != as_of:
                raise DataContractError(
                    f"PPDS_VALUATION_FX_AS_OF_MISMATCH: rate {currency}->{clean_base} as_of {fx.as_of.isoformat()} != valuation as_of {as_of.isoformat()}."
                )
            if not isinstance(fx.rate, Decimal) or not fx.rate.is_finite() or fx.rate <= Decimal("0"):
                raise DataContractError(
                    f"PPDS_VALUATION_FX_RATE_INVALID: non-positive or non-finite rate for {currency}->{clean_base}."
                )
            fx_mult = fx.rate
        cash_base[currency] = amount * fx_mult

    total_cash_base = sum(cash_base.values(), Decimal("0"))

    # 2. Value positions
    quantities = ledger.quantity_by_symbol()
    valued_positions: List[ValuedPosition] = []

    for symbol in sorted(quantities):
        net_qty = quantities[symbol]
        gross_qty = sum((abs(lot.quantity) for lot in ledger.position_lots if lot.symbol == symbol), Decimal("0"))
        symbol_currencies = {lot.currency for lot in ledger.position_lots if lot.symbol == symbol}
        if len(symbol_currencies) > 1:
            raise DataContractError(
                f"PPDS_VALUATION_SYMBOL_MULTI_CURRENCY: symbol {symbol} has lots in multiple currencies {sorted(symbol_currencies)}."
            )
        pos_currency = next(iter(symbol_currencies))

        if symbol not in prices:
            raise DataContractError(f"PPDS_VALUATION_PRICE_MISSING: missing price quote for {symbol}.")
        quote = prices[symbol]
        if quote.as_of != as_of:
            raise DataContractError(
                f"PPDS_VALUATION_PRICE_AS_OF_MISMATCH: price for {symbol} as_of {quote.as_of.isoformat()} != valuation as_of {as_of.isoformat()}."
            )
        if not isinstance(quote.price, Decimal) or not quote.price.is_finite() or quote.price <= Decimal("0"):
            raise DataContractError(
                f"PPDS_VALUATION_PRICE_INVALID: non-positive or non-finite price for {symbol}."
            )
        if quote.currency.upper() != pos_currency:
            raise DataContractError(
                f"PPDS_VALUATION_CURRENCY_MISMATCH: symbol {symbol} currency '{pos_currency}' does not match price quote currency '{quote.currency}'."
            )

        if pos_currency == clean_base:
            fx_pos = Decimal("1")
        else:
            fx_key = (pos_currency, clean_base)
            if fx_key not in fx_rates:
                raise DataContractError(
                    f"PPDS_VALUATION_FX_RATE_MISSING: missing FX conversion {pos_currency}->{clean_base} for {symbol}."
                )
            fx = fx_rates[fx_key]
            if fx.as_of != as_of:
                raise DataContractError(
                    f"PPDS_VALUATION_FX_AS_OF_MISMATCH: rate {pos_currency}->{clean_base} as_of {fx.as_of.isoformat()} != valuation as_of {as_of.isoformat()}."
                )
            if not isinstance(fx.rate, Decimal) or not fx.rate.is_finite() or fx.rate <= Decimal("0"):
                raise DataContractError(
                    f"PPDS_VALUATION_FX_RATE_INVALID: non-positive or non-finite rate for {pos_currency}->{clean_base}."
                )
            fx_pos = fx.rate

        net_mv_local = net_qty * quote.price
        gross_mv_local = gross_qty * quote.price
        net_mv_base = net_mv_local * fx_pos
        gross_mv_base = gross_mv_local * fx_pos

        valued_positions.append(ValuedPosition(
            symbol=symbol,
            net_quantity=net_qty,
            gross_quantity=gross_qty,
            pricing_currency=pos_currency,
            price=quote.price,
            price_as_of=quote.as_of,
            net_market_value_local=net_mv_local,
            gross_market_value_local=gross_mv_local,
            fx_rate_to_base=fx_pos,
            net_market_value_base=net_mv_base,
            gross_market_value_base=gross_mv_base,
        ))

    total_positions_gross_base = sum((p.gross_market_value_base for p in valued_positions), Decimal("0"))
    total_positions_net_base = sum((p.net_market_value_base for p in valued_positions), Decimal("0"))
    total_nav_base = total_cash_base + total_positions_net_base

    return PortfolioValuation(
        as_of=as_of,
        base_currency=clean_base,
        account_id=getattr(ledger, "account_id", "DEFAULT"),
        cash_local=cash_local,
        cash_base=cash_base,
        total_cash_base=total_cash_base,
        positions=valued_positions,
        total_positions_gross_base=total_positions_gross_base,
        total_positions_net_base=total_positions_net_base,
        total_portfolio_nav_base=total_nav_base,
    )
