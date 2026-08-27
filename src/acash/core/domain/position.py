"""Position domain model."""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from acash.core.domain.exceptions import DomainValidationError
from acash.core.domain.types import ensure_finite_decimal


class Position(BaseModel):
    """Sovereign position holding snapshot."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    timestamp_utc: datetime

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or not v.strip():
            raise DomainValidationError("Symbol must be a non-empty string.")
        return v.strip().upper()

    @field_validator("quantity", "entry_price", "current_price", "unrealized_pnl", "realized_pnl")
    @classmethod
    def validate_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if field_name in ("entry_price", "current_price") and v < Decimal("0"):
            raise DomainValidationError(f"{field_name} cannot be negative, got: {v}")
        return v

    @property
    def market_value(self) -> Decimal:
        """Phase 1 spot-like signed market valuation (quantity * current_price)."""
        return self.quantity * self.current_price

    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.quantity > Decimal("0")

    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.quantity < Decimal("0")

    @property
    def is_flat(self) -> bool:
        """Check if position is closed / flat."""
        return self.quantity == Decimal("0")
