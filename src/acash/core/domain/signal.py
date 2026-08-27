"""Signal, TargetAllocation, and RiskAssessment domain models."""

from datetime import datetime
from typing import Any, Mapping, Optional
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_serializer, field_validator

from acash.core.domain.exceptions import DomainValidationError
from acash.core.domain.types import ensure_finite_float, freeze_mapping


class Signal(BaseModel):
    """Directional alpha signal produced by a strategy."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    symbol: str
    direction: float
    expected_return: float
    uncertainty: float
    horizon_seconds: int
    timestamp_utc: datetime

    @field_validator("strategy_id", "symbol")
    @classmethod
    def validate_non_empty_str(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip().upper()

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: float) -> float:
        ensure_finite_float(v, field_name="direction")
        if not (-1.0 <= v <= 1.0):
            raise DomainValidationError(f"direction must be in range [-1.0, 1.0], got: {v}")
        return v

    @field_validator("expected_return")
    @classmethod
    def validate_expected_return(cls, v: float) -> float:
        return ensure_finite_float(v, field_name="expected_return")

    @field_validator("uncertainty")
    @classmethod
    def validate_uncertainty(cls, v: float) -> float:
        ensure_finite_float(v, field_name="uncertainty")
        if not (0.0 <= v <= 1.0):
            raise DomainValidationError(f"uncertainty must be in range [0.0, 1.0], got: {v}")
        return v

    @field_validator("horizon_seconds")
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        if v <= 0:
            raise DomainValidationError(f"horizon_seconds must be positive (> 0), got: {v}")
        return v


class TargetAllocation(BaseModel):
    """Candidate target portfolio weights."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    weights: Mapping[str, float]
    cash_weight: float
    rationale: str
    timestamp_utc: datetime

    @field_validator("weights", mode="after")
    @classmethod
    def validate_and_freeze_weights(cls, v: Mapping[str, float]) -> Mapping[str, float]:
        if not isinstance(v, Mapping):
            raise DomainValidationError("weights must be a Mapping of symbol to float weight.")
        validated: dict[str, float] = {}
        for symbol, weight in v.items():
            if not isinstance(symbol, str) or not symbol.strip():
                raise DomainValidationError(f"Invalid symbol in weights: {symbol}")
            w_float = float(weight)
            ensure_finite_float(w_float, field_name=f"weights[{symbol}]")
            validated[symbol.strip().upper()] = w_float
        return freeze_mapping(validated)

    @field_serializer("weights")
    def serialize_weights(self, weights: Mapping[str, float]) -> dict[str, float]:
        return dict(weights)

    @field_validator("cash_weight")
    @classmethod
    def validate_cash_weight(cls, v: float) -> float:
        return ensure_finite_float(v, field_name="cash_weight")


class RiskAssessment(BaseModel):
    """Deterministic risk evaluation verdict and capacity check."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    approved: bool
    adjusted_weights: Mapping[str, float]
    rejection_reason: Optional[str] = None
    max_drawdown_pct: float
    risk_utilization_pct: float
    timestamp_utc: datetime

    @field_validator("adjusted_weights", mode="after")
    @classmethod
    def validate_and_freeze_adjusted_weights(cls, v: Mapping[str, float]) -> Mapping[str, float]:
        if not isinstance(v, Mapping):
            raise DomainValidationError("adjusted_weights must be a Mapping of symbol to float weight.")
        validated: dict[str, float] = {}
        for symbol, weight in v.items():
            if not isinstance(symbol, str) or not symbol.strip():
                raise DomainValidationError(f"Invalid symbol in adjusted_weights: {symbol}")
            w_float = float(weight)
            ensure_finite_float(w_float, field_name=f"adjusted_weights[{symbol}]")
            validated[symbol.strip().upper()] = w_float
        return freeze_mapping(validated)

    @field_serializer("adjusted_weights")
    def serialize_adjusted_weights(self, adjusted_weights: Mapping[str, float]) -> dict[str, float]:
        return dict(adjusted_weights)

    @field_validator("max_drawdown_pct", "risk_utilization_pct")
    @classmethod
    def validate_pct_floats(cls, v: float, info: ValidationInfo) -> float:
        field_name = info.field_name or "field"
        return ensure_finite_float(v, field_name=field_name)
