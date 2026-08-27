"""Market data domain models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DomainValidationError, InvariantViolationError
from acash.core.domain.types import ensure_finite_decimal


class Bar(BaseModel):
    """Bi-temporal OHLCV candlestick bar record."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    timeframe: BarTimeframe
    event_start_utc: datetime
    event_end_utc: datetime
    knowledge_time_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    provenance_hash: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or not v.strip():
            raise DomainValidationError("Symbol must be a non-empty string.")
        return v.strip().upper()

    @field_validator("open", "high", "low", "close")
    @classmethod
    def validate_prices(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "price"
        ensure_finite_decimal(v, field_name=field_name)
        if v <= Decimal("0"):
            raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="volume")
        if v < Decimal("0"):
            raise DomainValidationError(f"volume must be non-negative (>= 0), got: {v}")
        return v

    @model_validator(mode="after")
    def validate_invariants(self) -> "Bar":
        # Temporal Invariants
        if self.event_end_utc < self.event_start_utc:
            raise InvariantViolationError(
                f"event_end_utc ({self.event_end_utc}) cannot be earlier than event_start_utc ({self.event_start_utc})"
            )
        if self.knowledge_time_utc < self.event_end_utc:
            raise InvariantViolationError(
                f"knowledge_time_utc ({self.knowledge_time_utc}) cannot precede event_end_utc ({self.event_end_utc})"
            )

        # Geometry Invariants
        max_body = max(self.open, self.close)
        min_body = min(self.open, self.close)
        if self.high < max_body:
            raise InvariantViolationError(
                f"high ({self.high}) must be >= max(open, close) ({max_body})"
            )
        if self.low > min_body:
            raise InvariantViolationError(
                f"low ({self.low}) must be <= min(open, close) ({min_body})"
            )

        return self


class MarketDataSnapshot(BaseModel):
    """Real-time top-of-book market snapshot."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal
    last_price: Decimal
    timestamp_utc: datetime

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or not v.strip():
            raise DomainValidationError("Symbol must be a non-empty string.")
        return v.strip().upper()

    @field_validator("bid", "ask", "last_price")
    @classmethod
    def validate_prices(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "price"
        ensure_finite_decimal(v, field_name=field_name)
        if v <= Decimal("0"):
            raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("bid_size", "ask_size")
    @classmethod
    def validate_sizes(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "size"
        ensure_finite_decimal(v, field_name=field_name)
        if v < Decimal("0"):
            raise DomainValidationError(f"{field_name} must be non-negative (>= 0), got: {v}")
        return v

    @model_validator(mode="after")
    def validate_spread(self) -> "MarketDataSnapshot":
        if self.ask < self.bid:
            raise InvariantViolationError(
                f"Inverted spread: ask ({self.ask}) cannot be strictly less than bid ({self.bid})"
            )
        return self
