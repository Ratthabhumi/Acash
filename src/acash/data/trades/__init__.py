"""ACASH Trades Domain Subsystem (Phase 3A).

Provides:
- Canonical Trades PyArrow schema & precision constraints (timestamp[ns, tz=UTC], Decimal128(38,18)).
- Length-Prefixed Binary Serialization & Deterministic Logical Hashing.
- Data integrity validation, sequence gap/reset classification, and duplicate rejection.
- Partitioned daily Parquet part storage & Recoverable Batch Commit Protocol.
- DuckDB Point-in-Time analytical query layer for tick-level trades.
- End-to-end ingestion pipeline with deterministic batch identity derivation and replay idempotency.
"""

from acash.data.trades.hashing import (
    calculate_canonical_trades_sha256,
    serialize_trade_row_binary,
)
from acash.data.trades.integrity import (
    SequenceDiscontinuityType,
    TradesIntegrityValidator,
    TradeValidationErrorRecord,
    TradeValidationAnomalyRecord,
    TradeValidationMetrics,
    TradeValidationReport,
)
from acash.data.trades.pipeline import (
    IngestedTradesBatchSummary,
    TradesIngestionPipeline,
    TradesIngestionResult,
)
from acash.data.trades.schema import (
    CANONICAL_TRADES_COLUMN_NAMES,
    CANONICAL_TRADES_SCHEMA,
    TRADE_ROW_IDENTITY_COLUMNS,
    VALID_AGGRESSOR_SIDES,
    VALID_TRADE_CONDITIONS,
)
from acash.data.trades.storage import (
    TradesBatchManifest,
    TradesStorageEngine,
)

__all__ = [
    # Schema
    "CANONICAL_TRADES_SCHEMA",
    "CANONICAL_TRADES_COLUMN_NAMES",
    "TRADE_ROW_IDENTITY_COLUMNS",
    "VALID_AGGRESSOR_SIDES",
    "VALID_TRADE_CONDITIONS",
    # Hashing
    "calculate_canonical_trades_sha256",
    "serialize_trade_row_binary",
    # Integrity
    "SequenceDiscontinuityType",
    "TradesIntegrityValidator",
    "TradeValidationErrorRecord",
    "TradeValidationAnomalyRecord",
    "TradeValidationMetrics",
    "TradeValidationReport",
    # Storage
    "TradesBatchManifest",
    "TradesStorageEngine",
    # Pipeline
    "TradesIngestionPipeline",
    "TradesIngestionResult",
    "IngestedTradesBatchSummary",
]
