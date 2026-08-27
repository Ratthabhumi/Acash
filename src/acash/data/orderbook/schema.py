"""Canonical PyArrow schemas, types, enums, and data contracts for the ACASH Order Book Subsystem (Phase 3B).

Strictly enforces:
- CANONICAL_BOOK_SNAPSHOT_SCHEMA: Multi-row atomic snapshot frames.
- CANONICAL_BOOK_DELTA_SCHEMA: Incremental mutation deltas with normalized resulting quantities.
- Explicit source_order_key: ASCII-only total-ordered token.
- CLEAR Control Action: price=None, size=None, level_idx=None, order_id=None, side in {BID, ASK, ALL}.
- MBO order_id: Non-null and non-empty for MBO; strictly None for MBP.
- Immutable Stream Scope: (source_id, channel_id, symbol, trading_date).
"""

from decimal import Decimal
from enum import Enum
from typing import Final, FrozenSet, List, Optional, Sequence, Set
import pyarrow as pa

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class BookDeltaType(str, Enum):
    """Domain type of the incremental delta."""
    MBP = "MBP"  # Market By Price (Level 2)
    MBO = "MBO"  # Market By Order (Level 3)


class BookAction(str, Enum):
    """Canonical atomic mutation actions for order book deltas."""
    ADD = "ADD"
    MODIFY = "MODIFY"
    CANCEL = "CANCEL"
    DELETE = "DELETE"
    CLEAR = "CLEAR"  # Control action to clear side or whole book


class BookSide(str, Enum):
    """Canonical sides of the depth ladder."""
    BID = "BID"
    ASK = "ASK"
    ALL = "ALL"  # Applicable only to CLEAR control actions


class SnapshotShapePolicy(str, Enum):
    """Contract policy governing snapshot frame shape and completeness."""
    FIXED_DEPTH_N = "FIXED_DEPTH_N"  # Source guarantees exactly N levels on both sides
    VARIABLE_DEPTH = "VARIABLE_DEPTH"  # Dynamic/sparse depth levels based on market liquidity
    SOURCE_DECLARED_COMPLETE = "SOURCE_DECLARED_COMPLETE"  # Certified by source completion markers


class SourceOrderingPolicy(str, Enum):
    """Adapter-declared ordering capability for incoming stream records."""
    OPAQUE = "OPAQUE"  # Ordered strictly by (exchange_time_utc, source_order_key) via byte/ASCII comparison
    MONOTONIC_INTEGER = "MONOTONIC_INTEGER"  # Monotonically increasing sequence within stream
    CONTIGUOUS_PACKET = "CONTIGUOUS_PACKET"  # Strict arithmetic contiguity guaranteed by source feed
    RESET_AWARE = "RESET_AWARE"  # Declared session rollover / channel reconnect reset support


class CrossedStateCategory(str, Enum):
    """Granular classification of crossed book states (P_bid >= P_ask)."""
    CROSSED_TRANSIENT = "CROSSED_TRANSIENT"  # Resolves within N consecutive deltas / packet burst
    CROSSED_AUCTION_OR_HALT = "CROSSED_AUCTION_OR_HALT"  # Occurs during auction matching / market halt
    CROSSED_DUE_TO_INVALID_RECONSTRUCTION = "CROSSED_DUE_TO_INVALID_RECONSTRUCTION"  # Missing deltas / gap
    CROSSED_PERSISTENT_ANOMALY = "CROSSED_PERSISTENT_ANOMALY"  # True persistent crossed book in continuous market


# ---------------------------------------------------------------------------
# Canonical PyArrow Schemas
# ---------------------------------------------------------------------------

CANONICAL_BOOK_SNAPSHOT_SCHEMA: Final[pa.Schema] = pa.schema([
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("channel_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("feed_time_utc", pa.timestamp("ns", tz="UTC"), nullable=True),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("source_seq_num", pa.int64(), nullable=False),
    pa.field("source_order_key", pa.string(), nullable=False),  # Shared ASCII total-ordered token
    pa.field("snapshot_id", pa.string(), nullable=False),  # Collision-safe Frame Identifier
    pa.field("is_snapshot_complete", pa.bool_(), nullable=False),  # Contract-certified completeness
    pa.field("side", pa.string(), nullable=False),  # "BID", "ASK"
    pa.field("level_idx", pa.int32(), nullable=False),  # 0 = Top of Book (BBO), 1..N Depth Level
    pa.field("price", pa.decimal128(38, 18), nullable=False),
    pa.field("size", pa.decimal128(38, 18), nullable=False),  # Absolute aggregated size at level
    pa.field("order_count", pa.int32(), nullable=True),  # Queue order count if provided
])

CANONICAL_BOOK_DELTA_SCHEMA: Final[pa.Schema] = pa.schema([
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("channel_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("exchange_time_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("feed_time_utc", pa.timestamp("ns", tz="UTC"), nullable=True),
    pa.field("knowledge_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("source_seq_num", pa.int64(), nullable=False),
    pa.field("source_order_key", pa.string(), nullable=False),  # Shared ASCII total-ordered token
    pa.field("action_sub_idx", pa.int32(), nullable=False),  # 0, 1, 2... within packet
    pa.field("delta_type", pa.string(), nullable=False),  # "MBP" or "MBO"
    pa.field("action", pa.string(), nullable=False),  # "ADD", "MODIFY", "CANCEL", "DELETE", "CLEAR"
    pa.field("side", pa.string(), nullable=False),  # "BID", "ASK", "ALL" (for CLEAR)
    pa.field("price", pa.decimal128(38, 18), nullable=True),  # Nullable ONLY for CLEAR control actions
    pa.field("size", pa.decimal128(38, 18), nullable=True),  # Nullable ONLY for CLEAR control actions
    pa.field("order_id", pa.string(), nullable=True),  # Required for MBO, MUST be NULL for MBP
    pa.field("level_idx", pa.int32(), nullable=True),  # Level index for MBP, Null for MBO
    pa.field("order_count", pa.int32(), nullable=True),  # Resulting order count at level (MBP)
])

# ---------------------------------------------------------------------------
# Identity and Column Definitions
# ---------------------------------------------------------------------------

BOOK_STREAM_SCOPE_COLUMNS: Final[List[str]] = [
    "source_id",
    "channel_id",
    "symbol",
    "trading_date",
]

BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS: Final[List[str]] = [
    "source_id",
    "channel_id",
    "symbol",
    "trading_date",
    "source_seq_num",
    "side",
    "level_idx",
]

BOOK_SNAPSHOT_COMPOUND_FRAME_COLUMNS: Final[List[str]] = [
    "source_id",
    "channel_id",
    "symbol",
    "trading_date",
    "source_seq_num",
    "snapshot_id",
]

BOOK_DELTA_ROW_IDENTITY_COLUMNS: Final[List[str]] = [
    "source_id",
    "channel_id",
    "symbol",
    "trading_date",
    "source_seq_num",
    "action_sub_idx",
]

VALID_DELTA_ACTIONS: Final[FrozenSet[str]] = frozenset({"ADD", "MODIFY", "CANCEL", "DELETE", "CLEAR"})
VALID_SNAPSHOT_SIDES: Final[FrozenSet[str]] = frozenset({"BID", "ASK"})
VALID_DELTA_SIDES: Final[FrozenSet[str]] = frozenset({"BID", "ASK", "ALL"})
VALID_DELTA_TYPES: Final[FrozenSet[str]] = frozenset({"MBP", "MBO"})
