"""Unit tests for Phase 12 Slice 2: MT5 Symbol Specification Normalizer & Unit Sizer."""

import decimal
from decimal import Decimal
import pytest

from acash.execution.mt5.enums import MT5OrderType, MT5TradeExecutionMode
from acash.execution.mt5.exceptions import MT5ValidationError
from acash.execution.mt5.normalizer import (
    MT5SymbolNormalizer,
    convert_lots_to_units,
    convert_units_to_lots,
    normalize_price,
    normalize_volume,
    validate_boc_passivity,
    validate_stop_level,
)
from acash.execution.mt5.schemas import BrokerSymbolSpec


@pytest.fixture
def eur_usd_spec() -> BrokerSymbolSpec:
    digest = BrokerSymbolSpec.compute_spec_digest(
        canonical_symbol="EURUSD",
        broker_symbol="EURUSD.pro",
        contract_size=Decimal("100000"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100.00"),
        volume_step=Decimal("0.01"),
        digits=5,
        point_size=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=10,
        margin_currency="EUR",
        profit_currency="USD",
    )
    return BrokerSymbolSpec(
        canonical_symbol="EURUSD",
        broker_symbol="EURUSD.pro",
        contract_size=Decimal("100000"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100.00"),
        volume_step=Decimal("0.01"),
        digits=5,
        point_size=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=10,
        margin_currency="EUR",
        profit_currency="USD",
        spec_digest=digest,
    )


@pytest.fixture
def step_05_spec() -> BrokerSymbolSpec:
    digest = BrokerSymbolSpec.compute_spec_digest(
        canonical_symbol="XAUUSD",
        broker_symbol="XAUUSD.pro",
        contract_size=Decimal("100"),
        volume_min=Decimal("0.10"),
        volume_max=Decimal("1.00"),
        volume_step=Decimal("0.05"),
        digits=2,
        point_size=Decimal("0.01"),
        tick_size=Decimal("0.01"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=20,
        margin_currency="USD",
        profit_currency="USD",
    )
    return BrokerSymbolSpec(
        canonical_symbol="XAUUSD",
        broker_symbol="XAUUSD.pro",
        contract_size=Decimal("100"),
        volume_min=Decimal("0.10"),
        volume_max=Decimal("1.00"),
        volume_step=Decimal("0.05"),
        digits=2,
        point_size=Decimal("0.01"),
        tick_size=Decimal("0.01"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
        allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=20,
        margin_currency="USD",
        profit_currency="USD",
        spec_digest=digest,
    )


# --- 1. Volume Lot Sizing & Quantization Tests ---

def test_volume_quantization_round_down(eur_usd_spec: BrokerSymbolSpec) -> None:
    """Verify volume quantization uses strict ROUND_DOWN towards zero."""
    # 10,540 units / 100,000 = 0.1054 raw lots -> 0.10 lots with 0.01 step
    vol = normalize_volume(Decimal("10540"), eur_usd_spec)
    assert vol == Decimal("0.10")

    # 10,999 units / 100,000 = 0.10999 raw lots -> 0.10 lots (never rounded up to 0.11)
    vol_down = normalize_volume(Decimal("10999"), eur_usd_spec)
    assert vol_down == Decimal("0.10")


def test_volume_max_pre_quantization_rejection(step_05_spec: BrokerSymbolSpec) -> None:
    """Verify raw lots exceeding volume_max are strictly rejected BEFORE quantization.

    INVARIANT: 1.05 raw lots with volume_max=1.00 and volume_step=0.05 must be rejected,
    and never silently compressed to 1.00 lots.
    """
    # 105 units / 100 contract_size = 1.05 raw lots (> volume_max 1.00)
    with pytest.raises(MT5ValidationError, match="RAW_VOLUME_EXCEEDS_MAXIMUM"):
        normalize_volume(Decimal("105"), step_05_spec)


def test_volume_min_rejection(eur_usd_spec: BrokerSymbolSpec) -> None:
    """Verify quantized volume below volume_min fails closed."""
    # 500 units / 100,000 = 0.005 raw lots -> 0.00 quantized lots (< volume_min 0.01)
    with pytest.raises(MT5ValidationError, match="VOLUME_BELOW_MINIMUM"):
        normalize_volume(Decimal("500"), eur_usd_spec)


def test_volume_non_positive_rejection(eur_usd_spec: BrokerSymbolSpec) -> None:
    """Verify zero or negative target units fail closed."""
    with pytest.raises(MT5ValidationError, match="TARGET_UNITS_MUST_BE_POSITIVE"):
        normalize_volume(Decimal("0.0"), eur_usd_spec)

    with pytest.raises(MT5ValidationError, match="TARGET_UNITS_MUST_BE_POSITIVE"):
        normalize_volume(Decimal("-10000"), eur_usd_spec)


# --- 2. Price Tick-Grid Snapping & Directional Rounding Tests ---

def test_price_tick_snapping_and_digits(eur_usd_spec: BrokerSymbolSpec) -> None:
    """Verify price formatting to exact digits and tick size alignment."""
    # 5 digits EURUSD
    price = normalize_price(Decimal("1.085001"), eur_usd_spec, MT5OrderType.BUY)
    assert price == Decimal("1.08500")


def test_price_directional_rounding_policies() -> None:
    """Verify directional rounding: BUY_LIMIT/SELL_STOP down (floor), SELL_LIMIT/BUY_STOP up (ceiling)."""
    digest = BrokerSymbolSpec.compute_spec_digest(
        canonical_symbol="TEST",
        broker_symbol="TEST.pro",
        contract_size=Decimal("1"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("10.00"),
        volume_step=Decimal("0.01"),
        digits=4,
        point_size=Decimal("0.0001"),
        tick_size=Decimal("0.0005"),  # 0.0005 tick step
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE,
        allowed_filling_flags=("SYMBOL_FILLING_FOK",),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=0,
        margin_currency="USD",
        profit_currency="USD",
    )
    spec = BrokerSymbolSpec(
        canonical_symbol="TEST",
        broker_symbol="TEST.pro",
        contract_size=Decimal("1"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("10.00"),
        volume_step=Decimal("0.01"),
        digits=4,
        point_size=Decimal("0.0001"),
        tick_size=Decimal("0.0005"),
        trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE,
        allowed_filling_flags=("SYMBOL_FILLING_FOK",),
        allowed_order_modes=("SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"),
        stops_level_points=0,
        margin_currency="USD",
        profit_currency="USD",
        spec_digest=digest,
    )

    # Raw price 10.0004 with 0.0005 tick
    # BUY_LIMIT -> FLOOR -> 10.0000
    p_buy_limit = normalize_price(Decimal("10.0004"), spec, MT5OrderType.BUY_LIMIT)
    assert p_buy_limit == Decimal("10.0000")

    # SELL_LIMIT -> CEILING -> 10.0005
    p_sell_limit = normalize_price(Decimal("10.0001"), spec, MT5OrderType.SELL_LIMIT)
    assert p_sell_limit == Decimal("10.0005")

    # BUY_STOP -> CEILING -> 10.0005
    p_buy_stop = normalize_price(Decimal("10.0001"), spec, MT5OrderType.BUY_STOP)
    assert p_buy_stop == Decimal("10.0005")

    # SELL_STOP -> FLOOR -> 10.0000
    p_sell_stop = normalize_price(Decimal("10.0004"), spec, MT5OrderType.SELL_STOP)
    assert p_sell_stop == Decimal("10.0000")


def test_price_non_positive_rejection(eur_usd_spec: BrokerSymbolSpec) -> None:
    """Verify zero or negative raw price fails closed."""
    with pytest.raises(MT5ValidationError, match="PRICE_MUST_BE_POSITIVE"):
        normalize_price(Decimal("0.0"), eur_usd_spec, MT5OrderType.BUY)

    with pytest.raises(MT5ValidationError, match="PRICE_MUST_BE_POSITIVE"):
        normalize_price(Decimal("-1.0850"), eur_usd_spec, MT5OrderType.BUY)


# --- 3. Stop-Level Distance Validation Tests ---

def test_stop_level_validation_pass_and_fail(eur_usd_spec: BrokerSymbolSpec) -> None:
    """Verify stop-level points distance enforcement against caller reference price."""
    # stops_level_points = 10 -> min_distance = 10 * 0.00001 = 0.00010
    ref_ask = Decimal("1.08500")

    # Distance = 0.00015 >= 0.00010 -> PASS
    valid_order_price = Decimal("1.08515")
    validate_stop_level(valid_order_price, ref_ask, eur_usd_spec)

    # Distance = 0.00005 < 0.00010 -> FAIL
    invalid_order_price = Decimal("1.08505")
    with pytest.raises(MT5ValidationError, match="STOP_LEVEL_VIOLATION"):
        validate_stop_level(invalid_order_price, ref_ask, eur_usd_spec)


# --- 4. Placement-Time BOC Passivity Tests ---

def test_boc_passivity_limit_orders() -> None:
    """Verify placement-time passivity checks for BUY_LIMIT and SELL_LIMIT."""
    bid = Decimal("1.08500")
    ask = Decimal("1.08520")

    # BUY_LIMIT at bid (passive, < ask) -> PASS
    validate_boc_passivity(MT5OrderType.BUY_LIMIT, limit_price=bid, current_bid=bid, current_ask=ask)

    # BUY_LIMIT at ask (aggressive, >= ask) -> FAIL
    with pytest.raises(MT5ValidationError, match="BOC_PRICE_NOT_PASSIVE"):
        validate_boc_passivity(MT5OrderType.BUY_LIMIT, limit_price=ask, current_bid=bid, current_ask=ask)

    # SELL_LIMIT at ask (passive, > bid) -> PASS
    validate_boc_passivity(MT5OrderType.SELL_LIMIT, limit_price=ask, current_bid=bid, current_ask=ask)

    # SELL_LIMIT at bid (aggressive, <= bid) -> FAIL
    with pytest.raises(MT5ValidationError, match="BOC_PRICE_NOT_PASSIVE"):
        validate_boc_passivity(MT5OrderType.SELL_LIMIT, limit_price=bid, current_bid=bid, current_ask=ask)


def test_boc_passivity_stop_limit_orders() -> None:
    """Verify placement-time structural geometry for BUY_STOP_LIMIT and SELL_STOP_LIMIT."""
    bid = Decimal("1.08500")
    ask = Decimal("1.08520")

    # BUY_STOP_LIMIT: trigger > ask and limit < trigger -> PASS
    validate_boc_passivity(
        MT5OrderType.BUY_STOP_LIMIT,
        limit_price=Decimal("1.08540"),
        current_bid=bid,
        current_ask=ask,
        trigger_price=Decimal("1.08550"),
    )

    # BUY_STOP_LIMIT: trigger <= ask -> FAIL
    with pytest.raises(MT5ValidationError, match="BOC_PRICE_NOT_PASSIVE"):
        validate_boc_passivity(
            MT5OrderType.BUY_STOP_LIMIT,
            limit_price=Decimal("1.08510"),
            current_bid=bid,
            current_ask=ask,
            trigger_price=Decimal("1.08510"),
        )

    # SELL_STOP_LIMIT: trigger < bid and limit > trigger -> PASS
    validate_boc_passivity(
        MT5OrderType.SELL_STOP_LIMIT,
        limit_price=Decimal("1.08470"),
        current_bid=bid,
        current_ask=ask,
        trigger_price=Decimal("1.08460"),
    )

    # SELL_STOP_LIMIT: trigger >= bid -> FAIL
    with pytest.raises(MT5ValidationError, match="BOC_PRICE_NOT_PASSIVE"):
        validate_boc_passivity(
            MT5OrderType.SELL_STOP_LIMIT,
            limit_price=Decimal("1.08510"),
            current_bid=bid,
            current_ask=ask,
            trigger_price=Decimal("1.08500"),
        )


def test_boc_invalid_spread_rejection() -> None:
    """Verify inverted or crossed market quotes fail closed."""
    with pytest.raises(MT5ValidationError, match="INVALID_MARKET_SPREAD"):
        validate_boc_passivity(
            MT5OrderType.BUY_LIMIT,
            limit_price=Decimal("1.08500"),
            current_bid=Decimal("1.08520"),
            current_ask=Decimal("1.08500"),
        )


# --- 5. Bidirectional Unit Conversions & Decimal Isolation Tests ---

def test_unit_lot_conversions(eur_usd_spec: BrokerSymbolSpec) -> None:
    """Verify conversion between base units and lots."""
    lots = convert_units_to_lots(Decimal("250000"), eur_usd_spec)
    assert lots == Decimal("2.5")

    units = convert_lots_to_units(Decimal("2.5"), eur_usd_spec)
    assert units == Decimal("250000")


def test_decimal_context_isolation(eur_usd_spec: BrokerSymbolSpec) -> None:
    """Verify normalizer executes in isolated 28-digit context independent of ambient context."""
    # Temporarily degrade ambient context precision
    orig_prec = decimal.getcontext().prec
    try:
        decimal.getcontext().prec = 2  # Degraded ambient context

        # Sizing division 10540 / 100000 under prec=2 would be 0.11, but normalizer uses prec=28 -> 0.1054 -> 0.10
        vol = normalize_volume(Decimal("10540"), eur_usd_spec)
        assert vol == Decimal("0.10")

        # Class wrapper test
        vol_cls = MT5SymbolNormalizer.normalize_volume(Decimal("10540"), eur_usd_spec)
        assert vol_cls == Decimal("0.10")

    finally:
        decimal.getcontext().prec = orig_prec
