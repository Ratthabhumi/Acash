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
    extract_exact_nanoseconds,
)
from acash.backtest.engine import (
    EventBacktestRunner,
    SimulatedOrder,
    SimulatedOrderBook,
)
from acash.backtest.nautilus_bridge import (
    ACASHNativeBacktestEngine,
    NautilusCatalogExporter,
    NautilusTraderSubstrate,
    SubstrateRuntimeUnavailableError,
    TradeIdMappingPolicy,
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
    load_current_environment_provenance,
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
    "load_current_environment_provenance",
    "CANONICAL_BACKTEST_FILLS_SCHEMA",
    "CANONICAL_EQUITY_CURVE_SCHEMA",
    # Adapter
    "BacktestEventType",
    "BacktestMarketEvent",
    "CanonicalDataAdapter",
    "extract_exact_nanoseconds",
    # Accounting
    "ACCOUNTING_TOLERANCE",
    "ShadowPositionState",
    "ShadowAccountingLedger",
    # Engine & Substrates
    "SimulatedOrderBook",
    "SimulatedOrder",
    "EventBacktestRunner",
    "ACASHNativeBacktestEngine",
    # Nautilus Integration
    "NautilusCatalogExporter",
    "NautilusTraderSubstrate",
    "SubstrateRuntimeUnavailableError",
    "TradeIdMappingPolicy",
    # Telemetry

    "RealityGapAttributionEngine",
    # Strategies
    "MicrostructureImbalanceActor",
    "VwapMeanReversionActor",
]
