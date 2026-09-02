"""Phase 12 Slice 2: Deterministic Symbol Specification Normalizer & Unit Sizer.

Enforces:
1. Volume lot quantization with ROUND_DOWN and pre-quantization volume_max checks.
2. Side-aware price tick-grid snapping and decimal digits formatting.
3. Stop-level distance enforcement vs caller-supplied reference prices.
4. Placement-time BOC structural passivity validation.
5. Isolated 28-digit Decimal context arithmetic without ambient context dependency.
"""

from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Decimal,
    localcontext,
)
from typing import Optional

from acash.core.domain.types import ensure_finite_decimal
from acash.execution.mt5.enums import MT5OrderType
from acash.execution.mt5.exceptions import MT5ValidationError
from acash.execution.mt5.schemas import BrokerSymbolSpec

DECIMAL_NORMALIZER_PRECISION = 28


def normalize_volume(target_units: Decimal, symbol_spec: BrokerSymbolSpec) -> Decimal:
    """Quantize target base asset units to valid broker lot volume under strict fail-closed rules.

    Invariants:
    - Target units must be strictly positive (> 0).
    - Raw lots exceeding volume_max are rejected BEFORE quantization (quantization must
      never silently compress an over-limit sizing request).
    - Quantization uses ROUND_DOWN to prevent exceeding sizing budgets.
    - Quantized lots must satisfy volume_min <= quantized_lots <= volume_max.
    - All arithmetic executes inside an isolated 28-digit Decimal context.
    """
    ensure_finite_decimal(target_units, field_name="target_units")
    if target_units <= Decimal("0.0"):
        raise MT5ValidationError(
            f"TARGET_UNITS_MUST_BE_POSITIVE: target_units must be > 0, got: {target_units}"
        )

    with localcontext() as ctx:
        ctx.prec = DECIMAL_NORMALIZER_PRECISION

        raw_lots = target_units / symbol_spec.contract_size

        # Pre-quantization maximum boundary check
        if raw_lots > symbol_spec.volume_max:
            raise MT5ValidationError(
                f"RAW_VOLUME_EXCEEDS_MAXIMUM: raw lots {raw_lots} exceeds volume_max {symbol_spec.volume_max}"
            )

        # Step quantization via ROUND_DOWN (floor towards zero for positive values)
        steps = (raw_lots / symbol_spec.volume_step).to_integral_value(rounding=ROUND_DOWN)
        quantized_lots = steps * symbol_spec.volume_step

        # Post-quantization minimum boundary check
        if quantized_lots < symbol_spec.volume_min:
            raise MT5ValidationError(
                f"VOLUME_BELOW_MINIMUM: quantized volume {quantized_lots} < volume_min {symbol_spec.volume_min}"
            )

        # Defensive post-quantization maximum boundary check
        if quantized_lots > symbol_spec.volume_max:
            raise MT5ValidationError(
                f"VOLUME_ABOVE_MAXIMUM: quantized volume {quantized_lots} > volume_max {symbol_spec.volume_max}"
            )

        # Normalize exponent matching volume_step
        quantized_lots = quantized_lots.quantize(symbol_spec.volume_step, rounding=ROUND_DOWN)
        return quantized_lots


def normalize_price(
    raw_price: Decimal,
    symbol_spec: BrokerSymbolSpec,
    order_type: MT5OrderType,
) -> Decimal:
    """Snap raw price to discrete broker tick-grid using side-aware directional rounding.

    Directional rounding strategy (ACASH execution safety policy):
    - BUY_LIMIT, SELL_STOP   -> ROUND_FLOOR (downwards into resting DOM)
    - SELL_LIMIT, BUY_STOP   -> ROUND_CEILING (upwards into resting DOM)
    - Market / Stop-Limit    -> ROUND_HALF_EVEN (or side-directed per trigger)
    """
    ensure_finite_decimal(raw_price, field_name="raw_price")
    if raw_price <= Decimal("0.0"):
        raise MT5ValidationError(f"PRICE_MUST_BE_POSITIVE: raw_price must be > 0, got: {raw_price}")

    with localcontext() as ctx:
        ctx.prec = DECIMAL_NORMALIZER_PRECISION

        if order_type in (MT5OrderType.BUY_LIMIT, MT5OrderType.SELL_STOP):
            rounding_mode = ROUND_FLOOR
        elif order_type in (MT5OrderType.SELL_LIMIT, MT5OrderType.BUY_STOP):
            rounding_mode = ROUND_CEILING
        else:
            rounding_mode = ROUND_HALF_EVEN

        ticks = (raw_price / symbol_spec.tick_size).to_integral_value(rounding=rounding_mode)
        snapped_price = ticks * symbol_spec.tick_size

        # Format to exact symbol digits precision
        digits_exponent = Decimal(10) ** -symbol_spec.digits
        formatted_price = snapped_price.quantize(digits_exponent, rounding=rounding_mode)
        return formatted_price


def validate_stop_level(
    order_price: Decimal,
    reference_price: Decimal,
    symbol_spec: BrokerSymbolSpec,
) -> None:
    """Validate that order_price satisfies the broker's minimum stop-level distance points.

    INVARIANT:
    The caller is strictly responsible for providing the authoritative reference_price
    (e.g., current Ask for Buy pendings / Short Stop Loss; current Bid for Sell pendings / Long Stop Loss).
    """
    ensure_finite_decimal(order_price, field_name="order_price")
    ensure_finite_decimal(reference_price, field_name="reference_price")

    if order_price <= Decimal("0.0"):
        raise MT5ValidationError(f"order_price must be > 0, got: {order_price}")
    if reference_price <= Decimal("0.0"):
        raise MT5ValidationError(f"reference_price must be > 0, got: {reference_price}")

    with localcontext() as ctx:
        ctx.prec = DECIMAL_NORMALIZER_PRECISION

        min_distance = Decimal(symbol_spec.stops_level_points) * symbol_spec.point_size
        actual_distance = abs(order_price - reference_price)

        if actual_distance < min_distance:
            raise MT5ValidationError(
                f"STOP_LEVEL_VIOLATION: distance {actual_distance} is less than required "
                f"stop level distance {min_distance} ({symbol_spec.stops_level_points} points)"
            )


def validate_boc_passivity(
    order_type: MT5OrderType,
    limit_price: Decimal,
    current_bid: Decimal,
    current_ask: Decimal,
    trigger_price: Optional[Decimal] = None,
) -> None:
    """Verify placement-time structural passivity for Book-or-Cancel (BOC) orders.

    SCOPE STATEMENT:
    This function verifies placement-time structural geometry against current market quotes.
    For Stop-Limit orders, it verifies initial placement geometry (trigger vs quotes, limit vs trigger);
    it does NOT guarantee future DOM passivity of the activated limit order upon trigger execution.
    """
    ensure_finite_decimal(limit_price, field_name="limit_price")
    ensure_finite_decimal(current_bid, field_name="current_bid")
    ensure_finite_decimal(current_ask, field_name="current_ask")

    if limit_price <= Decimal("0.0"):
        raise MT5ValidationError(f"limit_price must be > 0, got: {limit_price}")
    if current_bid <= Decimal("0.0"):
        raise MT5ValidationError(f"current_bid must be > 0, got: {current_bid}")
    if current_ask <= Decimal("0.0"):
        raise MT5ValidationError(f"current_ask must be > 0, got: {current_ask}")
    if current_bid >= current_ask:
        raise MT5ValidationError(
            f"INVALID_MARKET_SPREAD: current_bid ({current_bid}) must be < current_ask ({current_ask})"
        )

    with localcontext() as ctx:
        ctx.prec = DECIMAL_NORMALIZER_PRECISION

        if order_type == MT5OrderType.BUY_LIMIT:
            if limit_price >= current_ask:
                raise MT5ValidationError(
                    f"BOC_PRICE_NOT_PASSIVE: BUY_LIMIT price {limit_price} >= current_ask {current_ask}"
                )

        elif order_type == MT5OrderType.SELL_LIMIT:
            if limit_price <= current_bid:
                raise MT5ValidationError(
                    f"BOC_PRICE_NOT_PASSIVE: SELL_LIMIT price {limit_price} <= current_bid {current_bid}"
                )

        elif order_type == MT5OrderType.BUY_STOP_LIMIT:
            if trigger_price is None:
                raise MT5ValidationError("trigger_price is required for BUY_STOP_LIMIT BOC validation")
            ensure_finite_decimal(trigger_price, field_name="trigger_price")
            if trigger_price <= current_ask:
                raise MT5ValidationError(
                    f"BOC_PRICE_NOT_PASSIVE: BUY_STOP_LIMIT trigger_price {trigger_price} <= current_ask {current_ask}"
                )
            if limit_price >= trigger_price:
                raise MT5ValidationError(
                    f"BOC_PRICE_NOT_PASSIVE: BUY_STOP_LIMIT limit_price {limit_price} >= trigger_price {trigger_price}"
                )

        elif order_type == MT5OrderType.SELL_STOP_LIMIT:
            if trigger_price is None:
                raise MT5ValidationError("trigger_price is required for SELL_STOP_LIMIT BOC validation")
            ensure_finite_decimal(trigger_price, field_name="trigger_price")
            if trigger_price >= current_bid:
                raise MT5ValidationError(
                    f"BOC_PRICE_NOT_PASSIVE: SELL_STOP_LIMIT trigger_price {trigger_price} >= current_bid {current_bid}"
                )
            if limit_price <= trigger_price:
                raise MT5ValidationError(
                    f"BOC_PRICE_NOT_PASSIVE: SELL_STOP_LIMIT limit_price {limit_price} <= trigger_price {trigger_price}"
                )

        else:
            raise MT5ValidationError(f"BOC_UNSUPPORTED_ORDER_TYPE: {order_type}")


def convert_units_to_lots(target_units: Decimal, symbol_spec: BrokerSymbolSpec) -> Decimal:
    """Convert base asset quantity to raw lot volume under an explicit 28-digit arithmetic context with no float conversion."""
    ensure_finite_decimal(target_units, field_name="target_units")
    if target_units <= Decimal("0.0"):
        raise MT5ValidationError(f"target_units must be > 0, got: {target_units}")

    with localcontext() as ctx:
        ctx.prec = DECIMAL_NORMALIZER_PRECISION
        return target_units / symbol_spec.contract_size


def convert_lots_to_units(lots: Decimal, symbol_spec: BrokerSymbolSpec) -> Decimal:
    """Convert lot volume to base asset units under an explicit 28-digit arithmetic context with no float conversion."""
    ensure_finite_decimal(lots, field_name="lots")
    if lots <= Decimal("0.0"):
        raise MT5ValidationError(f"lots must be > 0, got: {lots}")

    with localcontext() as ctx:
        ctx.prec = DECIMAL_NORMALIZER_PRECISION
        return lots * symbol_spec.contract_size


class MT5SymbolNormalizer:
    """Sovereign normalizer and sizer for MetaTrader 5 execution plane."""

    @staticmethod
    def normalize_volume(target_units: Decimal, symbol_spec: BrokerSymbolSpec) -> Decimal:
        return normalize_volume(target_units=target_units, symbol_spec=symbol_spec)

    @staticmethod
    def normalize_price(
        raw_price: Decimal,
        symbol_spec: BrokerSymbolSpec,
        order_type: MT5OrderType,
    ) -> Decimal:
        return normalize_price(
            raw_price=raw_price,
            symbol_spec=symbol_spec,
            order_type=order_type,
        )

    @staticmethod
    def validate_stop_level(
        order_price: Decimal,
        reference_price: Decimal,
        symbol_spec: BrokerSymbolSpec,
    ) -> None:
        return validate_stop_level(
            order_price=order_price,
            reference_price=reference_price,
            symbol_spec=symbol_spec,
        )

    @staticmethod
    def validate_boc_passivity(
        order_type: MT5OrderType,
        limit_price: Decimal,
        current_bid: Decimal,
        current_ask: Decimal,
        trigger_price: Optional[Decimal] = None,
    ) -> None:
        return validate_boc_passivity(
            order_type=order_type,
            limit_price=limit_price,
            current_bid=current_bid,
            current_ask=current_ask,
            trigger_price=trigger_price,
        )

    @staticmethod
    def convert_units_to_lots(target_units: Decimal, symbol_spec: BrokerSymbolSpec) -> Decimal:
        return convert_units_to_lots(target_units=target_units, symbol_spec=symbol_spec)

    @staticmethod
    def convert_lots_to_units(lots: Decimal, symbol_spec: BrokerSymbolSpec) -> Decimal:
        return convert_lots_to_units(lots=lots, symbol_spec=symbol_spec)
