"""Append-only audit lineage domain models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from acash.core.domain.exceptions import DomainValidationError
from acash.core.domain.signal import RiskAssessment, TargetAllocation


class DecisionRecord(BaseModel):
    """Append-only immutable audit record capturing a capital allocation decision."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    timestamp_utc: datetime
    inputs_snapshot_ref: str
    signal_ref: Optional[str] = None
    target_allocation: Optional[TargetAllocation] = None
    risk_assessment: Optional[RiskAssessment] = None
    correlation_id: str
    schema_version: str = "1.0.0"

    @field_validator("decision_id", "inputs_snapshot_ref", "correlation_id", "schema_version")
    @classmethod
    def validate_non_empty_str(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise DomainValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()
