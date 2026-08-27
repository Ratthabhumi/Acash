"""Pydantic configuration schemas for ACASH."""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.enums import BarTimeframe


class SystemConfig(BaseModel):
    """System and environment runtime settings."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    environment: str = "base"
    base_currency: str = "USD"
    log_level: str = "INFO"
    json_logs: bool = True


class DataConfig(BaseModel):
    """Market data and storage settings."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    default_timeframe: BarTimeframe = BarTimeframe.M1
    max_lookback_bars: int = Field(default=5000, gt=0)
    storage_path: str = "data/parquet"


class ExecutionConfig(BaseModel):
    """Order routing and execution settings."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: str = "mock"
    default_slippage_model: str = "zero"
    default_fee_rate: Decimal = Field(default=Decimal("0.0001"), ge=Decimal("0"))


class RiskConfig(BaseModel):
    """Deterministic hard risk limits and margin settings."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_drawdown_limit_pct: float = Field(default=0.15, gt=0.0, le=1.0)
    margin_buffer_threshold: Decimal = Field(default=Decimal("1000.00"), ge=Decimal("0"))
    max_gross_leverage: float = Field(default=1.0, ge=1.0)


class TelemetryConfig(BaseModel):
    """Logging, metrics, and secret redaction settings."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    redact_secrets: bool = True


class AppConfig(BaseModel):
    """Root configuration object for ACASH."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    system: SystemConfig = Field(default_factory=SystemConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
