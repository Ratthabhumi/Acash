# src/acash/data/qualification/daily_models.py
"""Typed immutable model for daily SIP bars used by HYP_009 qualification.
This model mirrors the validation logic of HistoricalSipBar but is named
explicitly for the daily timeframe to avoid confusion with the 1‑minute
client.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.types import ensure_finite_decimal

class DailyBar(BaseModel):
    """Immutable DTO for a daily SIP bar.

    Validation guarantees:
    * timestamp_utc is timezone‑aware UTC
    * open, high, low, close are strictly positive Decimals
    * high >= max(open, close) and low <= min(open, close)
    * volume is non‑negative
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp_utc: datetime = Field(description="Bar start timestamp (UTC).")
    open: Decimal = Field(description="Opening price (strictly > 0).")
    high: Decimal = Field(description="Highest price (>= max(open, close)).")
    low: Decimal = Field(description="Lowest price (<= min(open, close)).")
    close: Decimal = Field(description="Closing price (strictly > 0).")
    volume: Decimal = Field(description="Traded volume (>= 0).")

    @field_validator("timestamp_utc")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise DataContractError("Bar timestamp must be timezone-aware UTC.")
        return v.astimezone(timezone.utc)

    @field_validator("open", "high", "low", "close")
    @classmethod
    def validate_prices(cls, v: Decimal, info) -> Decimal:
        field_name = getattr(info, "field_name", "price") or "price"
        ensure_finite_decimal(v, field_name=field_name)
        if v <= Decimal("0"):
            raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="volume")
        if v < Decimal("0"):
            raise DomainValidationError(f"volume must be non‑negative (>= 0), got: {v}")
        return v

    @model_validator(mode="after")
    def validate_geometry(self) -> "DailyBar":
        max_body = max(self.open, self.close)
        min_body = min(self.open, self.close)
        if self.high < max_body:
            raise DomainValidationError(
                f"high ({self.high}) cannot be less than max(open, close) ({max_body})"
            )
        if self.low > min_body:
            raise DomainValidationError(
                f"low ({self.low}) cannot be greater than min(open, close) ({min_body})"
            )
        return self
