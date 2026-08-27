"""Unit tests for Canonical Trades Arrow schema and types (Phase 3A)."""

from datetime import date, datetime, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.data.schema import DomainValidationError, validate_decimal128_bounds
from acash.data.trades.schema import (
    CANONICAL_TRADES_COLUMN_NAMES,
    CANONICAL_TRADES_SCHEMA,
    TRADE_ROW_IDENTITY_COLUMNS,
    VALID_AGGRESSOR_SIDES,
    VALID_TRADE_CONDITIONS,
)


def test_canonical_trades_schema_types() -> None:
    """Verify exact PyArrow data types and nullability in CANONICAL_TRADES_SCHEMA."""
    field_map = {f.name: f for f in CANONICAL_TRADES_SCHEMA}

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
    assert field_map["feed_time_utc"].nullable  # Optional / Nullable

    assert field_map["knowledge_time_utc"].type == pa.timestamp("us", tz="UTC")
    assert not field_map["knowledge_time_utc"].nullable

    assert field_map["source_seq_num"].type == pa.int64()
    assert not field_map["source_seq_num"].nullable

    assert field_map["trade_id"].type == pa.string()
    assert field_map["trade_id"].nullable  # Nullable: never synthetically fabricated

    assert field_map["match_sub_idx"].type == pa.int32()
    assert not field_map["match_sub_idx"].nullable

    assert field_map["price"].type == pa.decimal128(38, 18)
    assert not field_map["price"].nullable

    assert field_map["size"].type == pa.decimal128(38, 18)
    assert not field_map["size"].nullable

    assert field_map["aggressor_side"].type == pa.string()
    assert not field_map["aggressor_side"].nullable

    assert field_map["trade_condition"].type == pa.string()
    assert not field_map["trade_condition"].nullable


def test_trade_row_identity_columns() -> None:
    """Verify required columns for Trade Row Identity."""
    assert TRADE_ROW_IDENTITY_COLUMNS == [
        "source_id",
        "channel_id",
        "symbol",
        "trading_date",
        "source_seq_num",
        "match_sub_idx",
    ]


def test_valid_enumerations() -> None:
    """Verify valid aggressor sides and trade conditions."""
    assert VALID_AGGRESSOR_SIDES == frozenset({"BUY", "SELL", "UNKNOWN"})
    assert VALID_TRADE_CONDITIONS == frozenset({"REGULAR", "SPREAD", "BLOCK", "AUCTION"})
