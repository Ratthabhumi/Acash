"""ACASH Market Data Subsystem.

Provides:
- Canonical bi-temporal schema and precision constraints (timestamp[us, tz=UTC], Decimal128(38, 18))
- Per-stream integrity validation & anomaly preservation
- Partitioned immutable Parquet part storage
- Recoverable Batch Commit Protocol with Commit-Intent Manifests
- Crash recovery and quarantine
- DuckDB Point-in-Time qualification analytical layer
- Ingestion pipeline with strict 1:1 Ingestion Unit batch splitting
"""

from acash.data.integrity import (
    DataIntegrityValidator,
    SessionProfile,
    ValidationErrorRecord,
    ValidationAnomalyRecord,
    ValidationMetrics,
    ValidationReport,
)
from acash.data.mock import MockMarketDataProvider
from acash.data.pipeline import (
    IngestedBatchSummary,
    IngestionPipeline,
    IngestionResult,
)
from acash.data.provenance import (
    BatchLifecycleStatus,
    BatchManifest,
    ProvenanceRecord,
    ProvenanceTracker,
    calculate_canonical_batch_sha256,
    calculate_canonical_content_fingerprint,
    calculate_raw_source_sha256,
)
from acash.data.schema import (
    BatchCollisionError,
    CANONICAL_ARROW_SCHEMA,
    CANONICAL_COLUMN_NAMES,
    DataContractError,
    DomainValidationError,
    IntegrityViolationError,
    OrphanPartError,
    validate_decimal128_bounds,
)
from acash.data.sources import (
    CsvSourceAdapter,
    IDataSourceAdapter,
    ParquetSourceAdapter,
    SyntheticSourceAdapter,
)
from acash.data.storage import (
    DuckDBStorage,
    ParquetStorageEngine,
)
from acash.data import trades

__all__ = [
    # Mock
    "MockMarketDataProvider",
    # Schema & Types
    "CANONICAL_ARROW_SCHEMA",
    "CANONICAL_COLUMN_NAMES",
    "DataContractError",
    "DomainValidationError",
    "BatchCollisionError",
    "IntegrityViolationError",
    "OrphanPartError",
    "validate_decimal128_bounds",
    # Provenance & Manifests
    "BatchLifecycleStatus",
    "BatchManifest",
    "ProvenanceRecord",
    "ProvenanceTracker",
    "calculate_raw_source_sha256",
    "calculate_canonical_content_fingerprint",
    "calculate_canonical_batch_sha256",
    # Integrity & Validation
    "DataIntegrityValidator",
    "SessionProfile",
    "ValidationErrorRecord",
    "ValidationAnomalyRecord",
    "ValidationMetrics",
    "ValidationReport",
    # Storage & Query
    "ParquetStorageEngine",
    "DuckDBStorage",
    # Sources
    "IDataSourceAdapter",
    "CsvSourceAdapter",
    "ParquetSourceAdapter",
    "SyntheticSourceAdapter",
    # Pipeline
    "IngestionPipeline",
    "IngestionResult",
    "IngestedBatchSummary",
    # Submodules
    "trades",
]

