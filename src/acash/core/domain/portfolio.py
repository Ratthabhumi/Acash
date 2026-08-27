"""Portfolio and Account state domain models."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Optional
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_serializer, field_validator, model_validator

from acash.core.domain.exceptions import DomainValidationError, InvariantViolationError
from acash.core.domain.position import Position
from acash.core.domain.types import ensure_finite_decimal, ensure_finite_float, freeze_mapping


class PortfolioState(BaseModel):
    """Aggregated portfolio state snapshot."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    timestamp_utc: datetime
    positions: Mapping[str, Position]
    cash_balance: Decimal
    total_equity: Decimal
    margin_used: Decimal
    gross_exposure: Decimal
    net_exposure: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal

    @field_validator("positions", mode="after")
    @classmethod
    def validate_and_freeze_positions(cls, v: Mapping[str, Position]) -> Mapping[str, Position]:
        if not isinstance(v, Mapping):
            raise DomainValidationError("positions must be a Mapping of symbol to Position.")
        validated: dict[str, Position] = {}
        for symbol, pos in v.items():
            if not isinstance(pos, Position):
                raise DomainValidationError(f"Invalid position entry for symbol {symbol}: {pos}")
            validated[str(symbol).upper()] = pos
        return freeze_mapping(validated)

    @field_serializer("positions")
    def serialize_positions(self, positions: Mapping[str, Position]) -> dict[str, Any]:
        return {k: v.model_dump() for k, v in positions.items()}

    @field_validator("cash_balance", "total_equity", "margin_used", "gross_exposure", "net_exposure", "unrealized_pnl", "realized_pnl")
    @classmethod
    def validate_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if field_name == "margin_used" and v < Decimal("0"):
            raise DomainValidationError(f"margin_used cannot be negative, got: {v}")
        return v

    @model_validator(mode="after")
    def validate_accounting_invariants(self) -> "PortfolioState":
        # Calculate expected sums from current positions
        calc_market_val_sum = Decimal("0")
        calc_gross_exposure = Decimal("0")
        calc_unrealized_pnl = Decimal("0")

        for pos in self.positions.values():
            mv = pos.market_value
            calc_market_val_sum += mv
            calc_gross_exposure += abs(mv)
            calc_unrealized_pnl += pos.unrealized_pnl

        expected_equity = self.cash_balance + calc_market_val_sum
        if self.total_equity != expected_equity:
            raise InvariantViolationError(
                f"Portfolio total_equity mismatch: expected {expected_equity} (cash={self.cash_balance} + positions={calc_market_val_sum}), got {self.total_equity}"
            )

        if self.gross_exposure != calc_gross_exposure:
            raise InvariantViolationError(
                f"gross_exposure mismatch: expected {calc_gross_exposure}, got {self.gross_exposure}"
            )

        if self.net_exposure != calc_market_val_sum:
            raise InvariantViolationError(
                f"net_exposure mismatch: expected {calc_market_val_sum}, got {self.net_exposure}"
            )

        if self.unrealized_pnl != calc_unrealized_pnl:
            raise InvariantViolationError(
                f"unrealized_pnl mismatch: expected {calc_unrealized_pnl}, got {self.unrealized_pnl}"
            )

        return self


class AccountState(BaseModel):
    """External broker account state snapshot."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    account_id: str
    currency: str
    balance: Decimal
    equity: Decimal
    free_margin: Decimal
    margin_level_pct: Optional[float] = None
    leverage: float
    is_live: bool
    timestamp_utc: datetime

    @field_validator("account_id", "currency")
    @classmethod
    def validate_non_empty_str(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip().upper()

    @field_validator("balance", "equity", "free_margin")
    @classmethod
    def validate_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        return ensure_finite_decimal(v, field_name=field_name)

    @field_validator("margin_level_pct")
    @classmethod
    def validate_margin_level(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            ensure_finite_float(v, field_name="margin_level_pct")
        return v

    @field_validator("leverage")
    @classmethod
    def validate_leverage(cls, v: float) -> float:
        ensure_finite_float(v, field_name="leverage")
        if v < 1.0:
            raise DomainValidationError(f"leverage must be >= 1.0, got: {v}")
        return v
