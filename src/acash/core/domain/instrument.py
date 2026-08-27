"""Instrument domain model."""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from acash.core.domain.enums import AssetClass
from acash.core.domain.exceptions import DomainValidationError
from acash.core.domain.types import ensure_finite_decimal


class Instrument(BaseModel):
    """Sovereign financial instrument specification."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    asset_class: AssetClass
    base_currency: str
    quote_currency: str
    tick_size: Decimal
    lot_size: Decimal
    min_order_quantity: Decimal

    @field_validator("symbol", "base_currency", "quote_currency")
    @classmethod
    def validate_non_empty_str(cls, v: str, info: ValidationInfo) -> str:
        if not v or not v.strip():
            raise DomainValidationError("Symbol and currencies must be non-empty strings.")
        return v.strip().upper()

    @field_validator("tick_size", "lot_size", "min_order_quantity")
    @classmethod
    def validate_positive_finite_decimal(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if v <= Decimal("0"):
            raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v
