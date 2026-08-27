"""Canonical Order Book Subsystem for ACASH (Phase 3B).

Provides:
- CANONICAL_BOOK_SNAPSHOT_SCHEMA & CANONICAL_BOOK_DELTA_SCHEMA
- Length-prefixed binary serializers & logical SHA-256 hashers
- Collision-safe canonical snapshot_id derivation
- Unified ReconstructionOrderKey & strict boundary comparator
- In-memory deterministic MbpOrderBookReconstructor & MboOrderBookReconstructor
- OrderBookIntegrityValidator with contract & shape verification
- OrderBookStorageEngine with daily partitioning & two-stage multi-row PIT queries
- OrderBookIngestionPipeline with idempotent batch handling
"""

from acash.data.orderbook.hashing import (
    ReconstructionOrderKey,
    calculate_canonical_book_delta_sha256,
    calculate_canonical_book_snapshot_sha256,
    create_delta_order_key,
    create_snapshot_frame_boundary,
    derive_canonical_snapshot_id,
    serialize_book_delta_row_binary,
    serialize_book_snapshot_row_binary,
)
from acash.data.orderbook.integrity import OrderBookIntegrityValidator
from acash.data.orderbook.pipeline import (
    BookIngestionResult,
    IngestedBookBatchSummary,
    OrderBookIngestionPipeline,
)
from acash.data.orderbook.reconstruction import (
    DepthLadderState,
    MbpOrderBookReconstructor,
    MboOrderBookReconstructor,
    OrderEntry,
    PriceLevel,
)
from acash.data.orderbook.schema import (
    BOOK_DELTA_ROW_IDENTITY_COLUMNS,
    BOOK_SNAPSHOT_COMPOUND_FRAME_COLUMNS,
    BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS,
    BOOK_STREAM_SCOPE_COLUMNS,
    CANONICAL_BOOK_DELTA_SCHEMA,
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
    BookAction,
    BookDeltaType,
    BookSide,
    CrossedStateCategory,
    SnapshotShapePolicy,
    SourceOrderingPolicy,
)
from acash.data.orderbook.storage import OrderBookStorageEngine

__all__ = [
    # Schemas & Constants
    "CANONICAL_BOOK_SNAPSHOT_SCHEMA",
    "CANONICAL_BOOK_DELTA_SCHEMA",
    "BOOK_STREAM_SCOPE_COLUMNS",
    "BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS",
    "BOOK_SNAPSHOT_COMPOUND_FRAME_COLUMNS",
    "BOOK_DELTA_ROW_IDENTITY_COLUMNS",
    # Enums
    "BookDeltaType",
    "BookAction",
    "BookSide",
    "SnapshotShapePolicy",
    "SourceOrderingPolicy",
    "CrossedStateCategory",
    # Binary Hashing & Ordering
    "derive_canonical_snapshot_id",
    "serialize_book_snapshot_row_binary",
    "serialize_book_delta_row_binary",
    "calculate_canonical_book_snapshot_sha256",
    "calculate_canonical_book_delta_sha256",
    "ReconstructionOrderKey",
    "create_snapshot_frame_boundary",
    "create_delta_order_key",
    # State Reconstruction
    "PriceLevel",
    "OrderEntry",
    "DepthLadderState",
    "MbpOrderBookReconstructor",
    "MboOrderBookReconstructor",
    # Validation & Integrity
    "OrderBookIntegrityValidator",
    # Storage & Query
    "OrderBookStorageEngine",
    # Pipeline
    "OrderBookIngestionPipeline",
    "IngestedBookBatchSummary",
    "BookIngestionResult",
]
