"""Sovereign domain enumerations for ACASH."""

from enum import Enum


class AssetClass(str, Enum):
    """Supported asset classes."""
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    FX = "FX"
    COMMODITY = "COMMODITY"


class BarTimeframe(str, Enum):
    """Bar-specific timeframes. Note: TICK is not a bar timeframe."""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class OrderType(str, Enum):
    """Execution order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderSide(str, Enum):
    """Order and execution trade direction."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """Lifecycle status of an executable order."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class StrategyState(str, Enum):
    """Lifecycle operational state of an alpha strategy."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
