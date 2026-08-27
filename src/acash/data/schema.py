"""Canonical Arrow schema and data types for the ACASH market data subsystem.

Strictly enforces:
- timestamp[us, tz=UTC] (UTC microsecond precision matching DuckDB TIMESTAMPTZ)
- Decimal128(38, 18) (Canonical precision/scale representation)
- Event Observation Key vs Revision Identity distinction
- 1:1 Ingestion Unit mapping
"""

from decimal import Decimal
from typing import Final, Sequence
import pyarrow as pa


class DataContractError(Exception):
    """Base exception for all ACASH data contract violations."""


class DomainValidationError(DataContractError):
    """Raised when incoming field values violate domain invariants (e.g. negative price, non-finite)."""


class BatchCollisionError(DataContractError):
    """Raised when an existing batch_id is ingested with differing canonical content."""


class IntegrityViolationError(DataContractError):
    """Raised when dataset integrity or consistency invariants are violated (e.g. fatal validation errors)."""


class OrphanPartError(DataContractError):
    """Raised when an orphan Parquet part file exists without a corresponding commit-intent manifest or provenance record."""


# Canonical Arrow Schema definitions
CANONICAL_ARROW_SCHEMA: Final[pa.Schema] = pa.schema([
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("timeframe", pa.string(), nullable=False),
    pa.field("event_start_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("event_end_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("revision_seq", pa.int64(), nullable=False),
    pa.field("open", pa.decimal128(38, 18), nullable=False),
    pa.field("high", pa.decimal128(38, 18), nullable=False),
    pa.field("low", pa.decimal128(38, 18), nullable=False),
    pa.field("close", pa.decimal128(38, 18), nullable=False),
    pa.field("volume", pa.decimal128(38, 18), nullable=False),
    pa.field("quote_volume", pa.decimal128(38, 18), nullable=False),
    pa.field("trade_count", pa.int64(), nullable=False),
])

CANONICAL_COLUMN_NAMES: Final[Sequence[str]] = [
    field.name for field in CANONICAL_ARROW_SCHEMA
]

# Decimal bounds for Decimal128(38, 18)
MAX_DECIMAL128_38_18: Final[Decimal] = Decimal("99999999999999999999.999999999999999999")
MIN_DECIMAL128_38_18: Final[Decimal] = Decimal("-99999999999999999999.999999999999999999")


def validate_decimal128_bounds(val: Decimal, field_name: str) -> Decimal:
    """Validate that a Decimal value fits within Decimal128(38, 18) bounds and is finite."""
    if not val.is_finite():
        raise DomainValidationError(f"{field_name} must be a finite decimal, got {val}")
    if val > MAX_DECIMAL128_38_18 or val < MIN_DECIMAL128_38_18:
        raise DomainValidationError(
            f"{field_name} value {val} exceeds Decimal128(38, 18) bounds [{MIN_DECIMAL128_38_18}, {MAX_DECIMAL128_38_18}]"
        )
    return val
