"""Deterministic mapping and classification logic for MetaTrader 5 execution."""

from decimal import Decimal
from typing import Dict, Optional, Set, Tuple

from acash.execution.broker_events import BrokerEventKind
from acash.execution.mt5.enums import (
    MT5AccountMarginMode,
    MT5DealEntry,
    MT5DealType,
    MT5ExecutionPolicy,
    MT5FillingMode,
    MT5OrderTime,
    MT5OrderType,
    MT5Retcode,
    MT5TradeAction,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5FillingModeError,
    MT5RetcodeError,
    MT5ValidationError,
)
from acash.execution.mt5.schemas import BrokerSymbolSpec, MT5TradeRequest, MT5TradeResult
from acash.execution.schema import OrderIntent, OrderSide, OrderType, TimeInForce

# Canonical set of all supported MQL5 trade return codes
SUPPORTED_MT5_RETCODES: Set[int] = {code.value for code in MT5Retcode}

REJECT_RETCODES: Set[int] = {
    MT5Retcode.TRADE_RETCODE_REQUOTE.value,
    MT5Retcode.TRADE_RETCODE_REJECT.value,
    MT5Retcode.TRADE_RETCODE_ERROR.value,
    MT5Retcode.TRADE_RETCODE_TIMEOUT.value,
    MT5Retcode.TRADE_RETCODE_INVALID.value,
    MT5Retcode.TRADE_RETCODE_INVALID_VOLUME.value,
    MT5Retcode.TRADE_RETCODE_INVALID_PRICE.value,
    MT5Retcode.TRADE_RETCODE_INVALID_STOPS.value,
    MT5Retcode.TRADE_RETCODE_TRADE_DISABLED.value,
    MT5Retcode.TRADE_RETCODE_MARKET_CLOSED.value,
    MT5Retcode.TRADE_RETCODE_NO_MONEY.value,
    MT5Retcode.TRADE_RETCODE_PRICE_CHANGED.value,
    MT5Retcode.TRADE_RETCODE_PRICE_OFF.value,
    MT5Retcode.TRADE_RETCODE_INVALID_EXPIRATION.value,
    MT5Retcode.TRADE_RETCODE_ORDER_CHANGED.value,
    MT5Retcode.TRADE_RETCODE_TOO_MANY_REQUESTS.value,
    MT5Retcode.TRADE_RETCODE_NO_CHANGES.value,
    MT5Retcode.TRADE_RETCODE_SERVER_DISABLES_AT.value,
    MT5Retcode.TRADE_RETCODE_CLIENT_DISABLES_AT.value,
    MT5Retcode.TRADE_RETCODE_LOCKED.value,
    MT5Retcode.TRADE_RETCODE_FROZEN.value,
    MT5Retcode.TRADE_RETCODE_INVALID_FILL.value,
    MT5Retcode.TRADE_RETCODE_CONNECTION.value,
    MT5Retcode.TRADE_RETCODE_ONLY_REAL.value,
    MT5Retcode.TRADE_RETCODE_LIMIT_ORDERS.value,
    MT5Retcode.TRADE_RETCODE_LIMIT_VOLUME.value,
    MT5Retcode.TRADE_RETCODE_INVALID_ORDER.value,
    MT5Retcode.TRADE_RETCODE_POSITION_CLOSED.value,
    MT5Retcode.TRADE_RETCODE_INVALID_CLOSE_VOLUME.value,
    MT5Retcode.TRADE_RETCODE_CLOSE_ORDER_EXIST.value,
    MT5Retcode.TRADE_RETCODE_LIMIT_POSITIONS.value,
    MT5Retcode.TRADE_RETCODE_REJECT_CANCEL.value,
    MT5Retcode.TRADE_RETCODE_LONG_ONLY.value,
    MT5Retcode.TRADE_RETCODE_SHORT_ONLY.value,
    MT5Retcode.TRADE_RETCODE_CLOSE_ONLY.value,
    MT5Retcode.TRADE_RETCODE_FIFO_CLOSE.value,
    MT5Retcode.TRADE_RETCODE_HEDGE_PROHIBITED.value,
}


def classify_trade_result_observation(
    result: MT5TradeResult,
    authoritative_deal_confirmed: bool = False,
) -> BrokerEventKind:
    """Classify an MT5TradeResult observation without granting terminal lifecycle authority.

    INVARIANT: order_send() / MqlTradeResult return codes are strictly request-processing
    observations. retcode == 10009 alone NEVER constitutes terminal fill authority.
    """
    retcode = result.retcode
    if retcode not in SUPPORTED_MT5_RETCODES:
        raise MT5RetcodeError(f"Unrecognized or unsupported MT5 retcode: {retcode}")

    if retcode == MT5Retcode.TRADE_RETCODE_DONE.value:  # 10009
        if result.deal > 0 and authoritative_deal_confirmed:
            return BrokerEventKind.FILLED
        return BrokerEventKind.ACK

    if retcode == MT5Retcode.TRADE_RETCODE_PLACED.value:  # 10008
        return BrokerEventKind.ACK

    if retcode == MT5Retcode.TRADE_RETCODE_DONE_PARTIAL.value:  # 10010
        return BrokerEventKind.PARTIAL_FILL

    if retcode == MT5Retcode.TRADE_RETCODE_CANCEL.value:  # 10007
        return BrokerEventKind.ORDER_CANCELLED

    if retcode in REJECT_RETCODES:
        return BrokerEventKind.REJECT

    raise MT5RetcodeError(f"Unhandled MT5 retcode mapping: {retcode}")


def select_mt5_filling_mode(
    execution_mode: MT5TradeExecutionMode,
    order_type: MT5OrderType,
    execution_policy: MT5ExecutionPolicy,
    allowed_filling_flags: Tuple[str, ...],
) -> MT5FillingMode:
    """Deterministically select MT5FillingMode adhering to canonical MQL5 & ACASH policy matrix.

    Rules:
    1. Market Execution (SYMBOL_TRADE_EXECUTION_MARKET):
       - ORDER_FILLING_RETURN is strictly forbidden.
       - ORDER_FILLING_BOC is strictly forbidden.
       - PASSIVE_MAKER policy is strictly forbidden on market orders.
       - Allowed: FOK (if SYMBOL_FILLING_FOK) or IOC (if SYMBOL_FILLING_IOC).
    2. PASSIVE_MAKER Book-or-Cancel (ORDER_FILLING_BOC):
       - execution_policy == PASSIVE_MAKER only.
       - order_type in (BUY_LIMIT, SELL_LIMIT, BUY_STOP_LIMIT, SELL_STOP_LIMIT) only.
       - execution_mode == SYMBOL_TRADE_EXECUTION_EXCHANGE only.
       - SYMBOL_FILLING_BOC must be in allowed_filling_flags.
    3. Pending Orders:
       - Default filling mode is ORDER_FILLING_RETURN.
    """
    if order_type == MT5OrderType.CLOSE_BY:
        raise MT5FillingModeError("Close-By filling mode is not handled directly in standard selection.")

    # Rule 1: Market Execution & Market Orders (BUY/SELL)
    if order_type in (MT5OrderType.BUY, MT5OrderType.SELL):
        if execution_policy == MT5ExecutionPolicy.PASSIVE_MAKER:
            raise MT5FillingModeError("PASSIVE_MAKER policy cannot be applied to market orders.")

        if execution_mode == MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET:
            # Market Execution forbids RETURN and BOC
            has_fok = "SYMBOL_FILLING_FOK" in allowed_filling_flags
            has_ioc = "SYMBOL_FILLING_IOC" in allowed_filling_flags

            if execution_policy == MT5ExecutionPolicy.TAKER_SWEEP:
                if has_ioc:
                    return MT5FillingMode.ORDER_FILLING_IOC
                if has_fok:
                    return MT5FillingMode.ORDER_FILLING_FOK
            else:
                if has_fok:
                    return MT5FillingMode.ORDER_FILLING_FOK
                if has_ioc:
                    return MT5FillingMode.ORDER_FILLING_IOC

            raise MT5FillingModeError(
                "Symbol does not support SYMBOL_FILLING_FOK or SYMBOL_FILLING_IOC for Market Execution."
            )

        # For non-Market execution modes (REQUEST, INSTANT, EXCHANGE)
        has_fok = "SYMBOL_FILLING_FOK" in allowed_filling_flags
        has_ioc = "SYMBOL_FILLING_IOC" in allowed_filling_flags
        if has_fok:
            return MT5FillingMode.ORDER_FILLING_FOK
        if has_ioc:
            return MT5FillingMode.ORDER_FILLING_IOC
        return MT5FillingMode.ORDER_FILLING_RETURN

    # Rule 2: Book-or-Cancel (BOC) for Passive Maker
    if execution_policy == MT5ExecutionPolicy.PASSIVE_MAKER:
        allowed_boc_types = (
            MT5OrderType.BUY_LIMIT,
            MT5OrderType.SELL_LIMIT,
            MT5OrderType.BUY_STOP_LIMIT,
            MT5OrderType.SELL_STOP_LIMIT,
        )
        if order_type not in allowed_boc_types:
            raise MT5FillingModeError(
                f"PASSIVE_MAKER BOC filling requires a Limit or Stop-Limit order, got: {order_type.value}"
            )

        if execution_mode != MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE:
            raise MT5FillingModeError(
                f"PASSIVE_MAKER BOC filling requires Exchange execution mode, got: {execution_mode.value}"
            )

        if "SYMBOL_FILLING_BOC" not in allowed_filling_flags:
            raise MT5FillingModeError("Symbol does not support SYMBOL_FILLING_BOC capability.")

        return MT5FillingMode.ORDER_FILLING_BOC

    # Rule 3: Standard Pending Orders (BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP, etc.)
    return MT5FillingMode.ORDER_FILLING_RETURN


def map_order_intent_to_trade_request(
    intent: OrderIntent,
    symbol_spec: BrokerSymbolSpec,
    execution_policy: MT5ExecutionPolicy = MT5ExecutionPolicy.DEFAULT,
    magic: int = 0,
    comment: str = "",
    position: Optional[int] = None,
    position_by: Optional[int] = None,
) -> MT5TradeRequest:
    """Map an OrderIntent to canonical MT5TradeRequest preserving already-normalized values.

    INVARIANT:
    - Normalization, volume-step quantization, and tick snapping belong strictly to Slice 2.
    - Slice 1 strictly validates and preserves the already-normalized Decimal values.
    - Close-By operations intentionally fail closed in Slice 1.
    """
    if position_by is not None:
        raise MT5ValidationError(
            "Close-By execution (position_by) is intentionally deferred in Slice 1."
        )

    # Determine MT5OrderType and MT5TradeAction
    if intent.order_type == OrderType.MARKET:
        action = MT5TradeAction.TRADE_ACTION_DEAL
        if intent.side == OrderSide.BUY:
            mt5_type = MT5OrderType.BUY
        elif intent.side == OrderSide.SELL:
            mt5_type = MT5OrderType.SELL
        else:
            raise MT5ValidationError(f"Unsupported OrderSide: {intent.side}")
        price = Decimal("0.0")
        stoplimit = None

    elif intent.order_type == OrderType.LIMIT:
        action = MT5TradeAction.TRADE_ACTION_PENDING
        if intent.side == OrderSide.BUY:
            mt5_type = MT5OrderType.BUY_LIMIT
        elif intent.side == OrderSide.SELL:
            mt5_type = MT5OrderType.SELL_LIMIT
        else:
            raise MT5ValidationError(f"Unsupported OrderSide: {intent.side}")
        if intent.limit_price is None:
            raise MT5ValidationError("limit_price is required for LIMIT orders.")
        price = intent.limit_price
        stoplimit = None

    elif intent.order_type == OrderType.STOP_LIMIT:
        action = MT5TradeAction.TRADE_ACTION_PENDING
        if intent.side == OrderSide.BUY:
            mt5_type = MT5OrderType.BUY_STOP_LIMIT
        elif intent.side == OrderSide.SELL:
            mt5_type = MT5OrderType.SELL_STOP_LIMIT
        else:
            raise MT5ValidationError(f"Unsupported OrderSide: {intent.side}")
        if intent.stop_price is None:
            raise MT5ValidationError("stop_price is required for STOP_LIMIT orders.")
        if intent.limit_price is None:
            raise MT5ValidationError("limit_price is required for STOP_LIMIT orders.")
        price = intent.stop_price
        stoplimit = intent.limit_price

    else:
        raise MT5ValidationError(f"Unsupported OrderType: {intent.order_type}")

    # Determine filling mode
    filling_mode = select_mt5_filling_mode(
        execution_mode=symbol_spec.trade_execution_mode,
        order_type=mt5_type,
        execution_policy=execution_policy,
        allowed_filling_flags=symbol_spec.allowed_filling_flags,
    )

    # Determine time in force
    if intent.time_in_force == TimeInForce.DAY:
        type_time = MT5OrderTime.ORDER_TIME_DAY
    else:
        type_time = MT5OrderTime.ORDER_TIME_GTC

    # Truncate or validate comment to 31 chars
    sanitized_comment = comment[:31] if comment else ""

    return MT5TradeRequest(
        action=action,
        magic=magic,
        symbol=symbol_spec.broker_symbol,
        volume=intent.quantity,
        price=price,
        stoplimit=stoplimit,
        sl=Decimal("0.0"),
        tp=Decimal("0.0"),
        deviation=0,
        type=mt5_type,
        type_filling=filling_mode,
        type_time=type_time,
        comment=sanitized_comment,
        position=position,
        position_by=None,
    )


# ============================================================================
# PROTOCOL BOUNDARY CANONICAL MQL5 INTEGER DECODERS (SINGLE CANONICAL AUTHORITY)
# ============================================================================

# Canonical MQL5 ENUM_DEAL_TYPE mapping (0..17)
MQL5_DEAL_TYPE_DECODE_MAP: Dict[int, MT5DealType] = {
    0: MT5DealType.DEAL_TYPE_BUY,
    1: MT5DealType.DEAL_TYPE_SELL,
    2: MT5DealType.DEAL_TYPE_BALANCE,
    3: MT5DealType.DEAL_TYPE_CREDIT,
    4: MT5DealType.DEAL_TYPE_CHARGE,
    5: MT5DealType.DEAL_TYPE_CORRECTION,
    6: MT5DealType.DEAL_TYPE_BONUS,
    7: MT5DealType.DEAL_TYPE_COMMISSION,
    8: MT5DealType.DEAL_TYPE_COMMISSION_DAILY,
    9: MT5DealType.DEAL_TYPE_COMMISSION_MONTHLY,
    10: MT5DealType.DEAL_TYPE_COMMISSION_AGENT_DAILY,
    11: MT5DealType.DEAL_TYPE_COMMISSION_AGENT_MONTHLY,
    12: MT5DealType.DEAL_TYPE_INTEREST,
    13: MT5DealType.DEAL_TYPE_BUY_CANCELED,
    14: MT5DealType.DEAL_TYPE_SELL_CANCELED,
    15: MT5DealType.DEAL_DIVIDEND,
    16: MT5DealType.DEAL_DIVIDEND_FRANKED,
    17: MT5DealType.DEAL_TAX,
}


def decode_mt5_deal_type(raw: int) -> MT5DealType:
    """Protocol boundary decoder: maps raw external MQL5 integer to canonical MT5DealType."""
    if raw not in MQL5_DEAL_TYPE_DECODE_MAP:
        raise MT5DomainError(f"UNKNOWN_MQL5_DEAL_TYPE: {raw}")
    return MQL5_DEAL_TYPE_DECODE_MAP[raw]


# Canonical MQL5 ENUM_DEAL_ENTRY mapping (0..3)
MQL5_DEAL_ENTRY_DECODE_MAP: Dict[int, MT5DealEntry] = {
    0: MT5DealEntry.DEAL_ENTRY_IN,
    1: MT5DealEntry.DEAL_ENTRY_OUT,
    2: MT5DealEntry.DEAL_ENTRY_INOUT,
    3: MT5DealEntry.DEAL_ENTRY_OUT_BY,
}


def decode_mt5_deal_entry(raw: int) -> MT5DealEntry:
    """Protocol boundary decoder: maps raw external MQL5 integer to canonical MT5DealEntry."""
    if raw not in MQL5_DEAL_ENTRY_DECODE_MAP:
        raise MT5ValidationError(f"UNKNOWN_DEAL_ENTRY: unmapped deal entry {raw}")
    return MQL5_DEAL_ENTRY_DECODE_MAP[raw]


# Canonical MQL5 ENUM_ACCOUNT_MARGIN_MODE mapping (0..2)
MQL5_MARGIN_MODE_DECODE_MAP: Dict[int, MT5AccountMarginMode] = {
    0: MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_NETTING,
    1: MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_EXCHANGE,
    2: MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
}


def decode_mt5_margin_mode(raw: int) -> MT5AccountMarginMode:
    """Protocol boundary decoder: maps raw external MQL5 integer to canonical MT5AccountMarginMode."""
    if raw not in MQL5_MARGIN_MODE_DECODE_MAP:
        raise MT5DomainError(f"UNKNOWN_ACCOUNT_MARGIN_MODE: unmapped margin_mode {raw}")
    return MQL5_MARGIN_MODE_DECODE_MAP[raw]

