"""PPDS read-only skeleton: exposure / overlap / FX (pure functions).

All market prices and FX rates are EXPLICIT caller-supplied inputs (synthetic
fixtures). Nothing here fetches prices, rates, or holdings from any live
source. All arithmetic is exact Decimal; division by zero fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Mapping

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
    """Per-symbol market-value exposure with exact weights (sum to 1)."""
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
