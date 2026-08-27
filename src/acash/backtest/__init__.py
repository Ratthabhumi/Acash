"""Sovereign Event-Driven Backtesting Substrate Package (Phase 5)."""

from acash.backtest.accounting import (
    ACCOUNTING_TOLERANCE,
    ShadowAccountingLedger,
    ShadowPositionState,
)
from acash.backtest.adapter import (
    BacktestEventType,
    BacktestMarketEvent,
    CanonicalDataAdapter,
)
from acash.backtest.engine import (
    EventBacktestRunner,
    SimulatedOrder,
)
from acash.backtest.schema import (
    CANONICAL_BACKTEST_FILLS_SCHEMA,
    CANONICAL_EQUITY_CURVE_SCHEMA,
    BacktestEngineConfig,
    BacktestExecutionSummary,
    BacktestFillRecord,
    BacktestManifest,
    BacktestOrderStatus,
    FeeModelConfig,
    LiquidityType,
    OrderType,
    RealityGapSummary,
    SimulationLatencyConfig,
    SlippageModelConfig,
    calculate_backtest_manifest_id,
)
from acash.backtest.strategies import (
    MicrostructureImbalanceActor,
    VwapMeanReversionActor,
)
from acash.backtest.telemetry import RealityGapAttributionEngine

__all__ = [
    # Schema & Config
    "OrderType",
    "BacktestOrderStatus",
    "LiquidityType",
    "SimulationLatencyConfig",
    "FeeModelConfig",
    "SlippageModelConfig",
    "BacktestEngineConfig",
    "BacktestFillRecord",
    "BacktestExecutionSummary",
    "RealityGapSummary",
    "BacktestManifest",
    "calculate_backtest_manifest_id",
    "CANONICAL_BACKTEST_FILLS_SCHEMA",
    "CANONICAL_EQUITY_CURVE_SCHEMA",
    # Adapter
    "BacktestEventType",
    "BacktestMarketEvent",
    "CanonicalDataAdapter",
    # Accounting
    "ACCOUNTING_TOLERANCE",
    "ShadowPositionState",
    "ShadowAccountingLedger",
    # Engine
    "SimulatedOrder",
    "EventBacktestRunner",
    # Telemetry
    "RealityGapAttributionEngine",
    # Strategies
    "MicrostructureImbalanceActor",
    "VwapMeanReversionActor",
]
