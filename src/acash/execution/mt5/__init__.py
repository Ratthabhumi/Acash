"""Phase 12 MetaTrader 5 (MT5) Execution Adapter Domain Module."""

from acash.execution.mt5.enums import (
    MT5DealEntry,
    MT5DealType,
    MT5ExecutionPolicy,
    MT5FillingMode,
    MT5OrderState,
    MT5OrderTime,
    MT5OrderType,
    MT5PositionType,
    MT5Retcode,
    MT5TradeAction,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5FillingModeError,
    MT5NormalizationError,
    MT5RetcodeError,
    MT5SymbolSpecError,
    MT5ValidationError,
)
from acash.execution.mt5.mapping import (
    REJECT_RETCODES,
    SUPPORTED_MT5_RETCODES,
    classify_trade_result_observation,
    map_order_intent_to_trade_request,
    select_mt5_filling_mode,
)
from acash.execution.mt5.schemas import (
    BrokerSymbolSpec,
    MT5AccountReality,
    MT5DealReality,
    MT5ExecutionLineage,
    MT5OrderReality,
    MT5PositionReality,
    MT5TradeRequest,
    MT5TradeResult,
)

__all__ = [
    # Enums
    "MT5OrderType",
    "MT5FillingMode",
    "MT5ExecutionPolicy",
    "MT5TradeAction",
    "MT5OrderState",
    "MT5OrderTime",
    "MT5DealType",
    "MT5DealEntry",
    "MT5PositionType",
    "MT5TradeExecutionMode",
    "MT5Retcode",
    # Exceptions
    "MT5DomainError",
    "MT5ValidationError",
    "MT5NormalizationError",
    "MT5RetcodeError",
    "MT5FillingModeError",
    "MT5SymbolSpecError",
    # Schemas
    "BrokerSymbolSpec",
    "MT5TradeRequest",
    "MT5TradeResult",
    "MT5DealReality",
    "MT5OrderReality",
    "MT5PositionReality",
    "MT5AccountReality",
    "MT5ExecutionLineage",
    # Mapping
    "SUPPORTED_MT5_RETCODES",
    "REJECT_RETCODES",
    "classify_trade_result_observation",
    "select_mt5_filling_mode",
    "map_order_intent_to_trade_request",
]
