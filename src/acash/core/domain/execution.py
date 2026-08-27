"""Order and Fill execution domain models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from acash.core.domain.enums import OrderSide, OrderStatus, OrderType
from acash.core.domain.exceptions import DomainValidationError
from acash.core.domain.types import ensure_finite_decimal


class Order(BaseModel):
    """Executable order intent."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: str
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: Decimal
    price_limit: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    idempotency_key: str
    correlation_id: str
    created_at_utc: datetime

    @field_validator("order_id", "symbol", "idempotency_key", "correlation_id")
    @classmethod
    def validate_non_empty_str(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="quantity")
        if v <= Decimal("0"):
            raise DomainValidationError(f"Order quantity must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("price_limit")
    @classmethod
    def validate_price_limit(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            ensure_finite_decimal(v, field_name="price_limit")
            if v <= Decimal("0"):
                raise DomainValidationError(f"price_limit must be strictly positive (> 0), got: {v}")
        return v


class Fill(BaseModel):
    """Trade execution result."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    fill_price: Decimal
    fill_quantity: Decimal
    fee: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    correlation_id: str
    timestamp_utc: datetime

    @field_validator("fill_id", "order_id", "symbol", "correlation_id")
    @classmethod
    def validate_non_empty_str(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("fill_price", "fill_quantity")
    @classmethod
    def validate_positive_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if v <= Decimal("0"):
            raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("fee", "slippage")
    @classmethod
    def validate_fee_and_slippage(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if field_name == "fee" and v < Decimal("0"):
            raise DomainValidationError(f"fee cannot be negative, got: {v}")
        return v
