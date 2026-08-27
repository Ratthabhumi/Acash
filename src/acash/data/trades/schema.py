"""Canonical PyArrow schema and data contracts for the ACASH Trades Domain (Phase 3A).

Strictly enforces:
- exchange_time_utc: timestamp[ns, tz=UTC] (lossless nanosecond matching chronology)
- feed_time_utc: timestamp[ns, tz=UTC] (optional/nullable network egress timestamp)
- knowledge_time_utc: timestamp[us, tz=UTC] (microsecond ACASH observation timestamp)
- source_seq_num: int64 (opaque upstream sequence identifier)
- trade_id: string (nullable, source-provided when available; never synthetically fabricated)
- match_sub_idx: int32 (deterministic sub-index for multi-match packets)
- price, size: Decimal128(38, 18) (canonical precision financial numerics)
- aggressor_side: string ("BUY", "SELL", "UNKNOWN")
- trade_condition: string ("REGULAR", "SPREAD", "BLOCK", "AUCTION")
- trading_date: date32 (calendar-driven session label)
"""

from decimal import Decimal
from typing import Final, Sequence
import pyarrow as pa

from acash.data.schema import (
    BatchCollisionError,
    DataContractError,
    DomainValidationError,
    IntegrityViolationError,
    OrphanPartError,
    validate_decimal128_bounds,
)

# Canonical Trades Arrow Schema
CANONICAL_TRADES_SCHEMA: Final[pa.Schema] = pa.schema([
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("channel_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("feed_time_utc", pa.timestamp("ns", tz="UTC"), nullable=True),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("source_seq_num", pa.int64(), nullable=False),
    pa.field("trade_id", pa.string(), nullable=True),
    pa.field("match_sub_idx", pa.int32(), nullable=False),
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),
    pa.field("aggressor_side", pa.string(), nullable=False),
    pa.field("trade_condition", pa.string(), nullable=False),
])

CANONICAL_TRADES_COLUMN_NAMES: Final[Sequence[str]] = [
    field.name for field in CANONICAL_TRADES_SCHEMA
]

# Allowed enumerated string sets
VALID_AGGRESSOR_SIDES: Final[frozenset[str]] = frozenset({"BUY", "SELL", "UNKNOWN"})
VALID_TRADE_CONDITIONS: Final[frozenset[str]] = frozenset(
    {"REGULAR", "SPREAD", "BLOCK", "AUCTION"}
)

# Canonical Trade Row Identity components
TRADE_ROW_IDENTITY_COLUMNS: Final[Sequence[str]] = [
    "source_id",
    "channel_id",
    "symbol",
    "trading_date",
    "source_seq_num",
    "match_sub_idx",
]
