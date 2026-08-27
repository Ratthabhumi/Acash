"""Unit tests for Canonical Order Book Schemas, Types, and Enums (Phase 3B)."""

from datetime import date, datetime, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

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


def test_canonical_book_snapshot_schema_types() -> None:
    """Verify PyArrow types and nullabilities in CANONICAL_BOOK_SNAPSHOT_SCHEMA."""
    field_map = {f.name: f for f in CANONICAL_BOOK_SNAPSHOT_SCHEMA}

    assert field_map["source_id"].type == pa.string()
    assert not field_map["source_id"].nullable

    assert field_map["channel_id"].type == pa.string()
    assert not field_map["channel_id"].nullable

    assert field_map["symbol"].type == pa.string()
    assert not field_map["symbol"].nullable

    assert field_map["trading_date"].type == pa.date32()
    assert not field_map["trading_date"].nullable

    assert field_map["exchange_time_utc"].type == pa.timestamp("ns", tz="UTC")
    assert not field_map["exchange_time_utc"].nullable

    assert field_map["feed_time_utc"].type == pa.timestamp("ns", tz="UTC")
    assert field_map["feed_time_utc"].nullable

    assert field_map["knowledge_time_utc"].type == pa.timestamp("us", tz="UTC")
    assert not field_map["knowledge_time_utc"].nullable

    assert field_map["source_seq_num"].type == pa.int64()
    assert not field_map["source_seq_num"].nullable

    assert field_map["source_order_key"].type == pa.string()
    assert not field_map["source_order_key"].nullable

    assert field_map["snapshot_id"].type == pa.string()
    assert not field_map["snapshot_id"].nullable

    assert field_map["is_snapshot_complete"].type == pa.bool_()
    assert not field_map["is_snapshot_complete"].nullable

    assert field_map["side"].type == pa.string()
    assert not field_map["side"].nullable

    assert field_map["level_idx"].type == pa.int32()
    assert not field_map["level_idx"].nullable

    assert field_map["price"].type == pa.decimal128(38, 18)
    assert not field_map["price"].nullable

    assert field_map["size"].type == pa.decimal128(38, 18)
    assert not field_map["size"].nullable

    assert field_map["order_count"].type == pa.int32()
    assert field_map["order_count"].nullable


def test_canonical_book_delta_schema_types() -> None:
    """Verify PyArrow types and nullabilities in CANONICAL_BOOK_DELTA_SCHEMA."""
    field_map = {f.name: f for f in CANONICAL_BOOK_DELTA_SCHEMA}

    assert field_map["source_id"].type == pa.string()
    assert not field_map["source_id"].nullable

    assert field_map["channel_id"].type == pa.string()
    assert not field_map["channel_id"].nullable

    assert field_map["symbol"].type == pa.string()
    assert not field_map["symbol"].nullable

    assert field_map["trading_date"].type == pa.date32()
    assert not field_map["trading_date"].nullable

    assert field_map["exchange_time_utc"].type == pa.timestamp("ns", tz="UTC")
    assert not field_map["exchange_time_utc"].nullable

    assert field_map["feed_time_utc"].type == pa.timestamp("ns", tz="UTC")
    assert field_map["feed_time_utc"].nullable

    assert field_map["knowledge_time_utc"].type == pa.timestamp("us", tz="UTC")
    assert not field_map["knowledge_time_utc"].nullable

    assert field_map["source_seq_num"].type == pa.int64()
    assert not field_map["source_seq_num"].nullable

    assert field_map["source_order_key"].type == pa.string()
    assert not field_map["source_order_key"].nullable

    assert field_map["action_sub_idx"].type == pa.int32()
    assert not field_map["action_sub_idx"].nullable

    assert field_map["delta_type"].type == pa.string()
    assert not field_map["delta_type"].nullable

    assert field_map["action"].type == pa.string()
    assert not field_map["action"].nullable

    assert field_map["side"].type == pa.string()
    assert not field_map["side"].nullable

    assert field_map["price"].type == pa.decimal128(38, 18)
    assert field_map["price"].nullable  # Nullable for CLEAR control action

    assert field_map["size"].type == pa.decimal128(38, 18)
    assert field_map["size"].nullable  # Nullable for CLEAR control action

    assert field_map["order_id"].type == pa.string()
    assert field_map["order_id"].nullable  # Required for MBO, Null for MBP

    assert field_map["level_idx"].type == pa.int32()
    assert field_map["level_idx"].nullable

    assert field_map["order_count"].type == pa.int32()
    assert field_map["order_count"].nullable


def test_orderbook_identity_columns_and_enums() -> None:
    """Verify identity column definitions and enums."""
    assert BOOK_STREAM_SCOPE_COLUMNS == ["source_id", "channel_id", "symbol", "trading_date"]
    assert BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS == [
        "source_id", "channel_id", "symbol", "trading_date", "source_seq_num", "side", "level_idx"
    ]
    assert BOOK_SNAPSHOT_COMPOUND_FRAME_COLUMNS == [
        "source_id", "channel_id", "symbol", "trading_date", "source_seq_num", "snapshot_id"
    ]
    assert BOOK_DELTA_ROW_IDENTITY_COLUMNS == [
        "source_id", "channel_id", "symbol", "trading_date", "source_seq_num", "action_sub_idx"
    ]

    assert set(BookDeltaType) == {BookDeltaType.MBP, BookDeltaType.MBO}
    assert set(BookAction) == {BookAction.ADD, BookAction.MODIFY, BookAction.CANCEL, BookAction.DELETE, BookAction.CLEAR}
    assert set(BookSide) == {BookSide.BID, BookSide.ASK, BookSide.ALL}
    assert set(SnapshotShapePolicy) == {
        SnapshotShapePolicy.FIXED_DEPTH_N, SnapshotShapePolicy.VARIABLE_DEPTH, SnapshotShapePolicy.SOURCE_DECLARED_COMPLETE
    }
    assert set(SourceOrderingPolicy) == {
        SourceOrderingPolicy.OPAQUE, SourceOrderingPolicy.MONOTONIC_INTEGER, SourceOrderingPolicy.CONTIGUOUS_PACKET, SourceOrderingPolicy.RESET_AWARE
    }
    assert set(CrossedStateCategory) == {
        CrossedStateCategory.CROSSED_TRANSIENT, CrossedStateCategory.CROSSED_AUCTION_OR_HALT,
        CrossedStateCategory.CROSSED_DUE_TO_INVALID_RECONSTRUCTION, CrossedStateCategory.CROSSED_PERSISTENT_ANOMALY
    }
