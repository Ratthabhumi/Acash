"""Deterministic Length-Prefixed Binary Serialization and Logical Cryptographic Hashing for Trades.

Guarantees:
- Deterministic and computationally collision-resistant logical hashing under the canonical serialization protocol.
- Lossless nanosecond timestamp serialization via signed 64-bit big-endian epoch integers.
- Exact fixed-point 18-scale decimal serialization.
- Codec, compression, chunking, and physical Parquet layout invariance.
- Row-order permutation invariance via canonical sort on Trade Row Identity.
"""

import hashlib
import struct
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional
import pyarrow as pa
import pyarrow.compute as pc

from acash.data.schema import DataContractError
from acash.data.trades.schema import (
    CANONICAL_TRADES_COLUMN_NAMES,
    TRADE_ROW_IDENTITY_COLUMNS,
)

# Binary frame constants
NULL_UINT32_TAG = 0xFFFFFFFF
NULL_INT64_SENTINEL = -9223372036854775808
NULL_INT32_SENTINEL = -2147483648
RECORD_SEPARATOR_BYTE = b"\x1e"


def _encode_string(val: Optional[str]) -> bytes:
    """Encode string with 4-byte big-endian uint32 length prefix."""
    if val is None:
        return struct.pack(">I", NULL_UINT32_TAG)
    utf8_bytes = val.encode("utf-8")
    return struct.pack(">I", len(utf8_bytes)) + utf8_bytes


def _encode_decimal(val: Optional[Decimal]) -> bytes:
    """Encode Decimal as fixed 18-scale ASCII string with 4-byte big-endian length prefix."""
    if val is None:
        return struct.pack(">I", NULL_UINT32_TAG)
    ascii_bytes = f"{val:.18f}".encode("ascii")
    return struct.pack(">I", len(ascii_bytes)) + ascii_bytes


def _encode_timestamp_ns(val: Any) -> bytes:
    """Encode timestamp with nanosecond resolution as 8-byte big-endian int64 epoch nanoseconds."""
    if val is None:
        return struct.pack(">q", NULL_INT64_SENTINEL)
    if isinstance(val, int):
        return struct.pack(">q", val)
    if isinstance(val, pa.Scalar):
        if val.as_py() is None:
            return struct.pack(">q", NULL_INT64_SENTINEL)
        return struct.pack(">q", val.value)
    if isinstance(val, datetime):
        dt_utc = val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
        epoch_ns = int(dt_utc.timestamp() * 1_000_000_000)
        return struct.pack(">q", epoch_ns)
    raise TypeError(f"Unsupported timestamp_ns type: {type(val)}")


def _encode_timestamp_us(val: Any) -> bytes:
    """Encode timestamp with microsecond resolution as 8-byte big-endian int64 epoch microseconds."""
    if val is None:
        return struct.pack(">q", NULL_INT64_SENTINEL)
    if isinstance(val, int):
        return struct.pack(">q", val)
    if isinstance(val, pa.Scalar):
        if val.as_py() is None:
            return struct.pack(">q", NULL_INT64_SENTINEL)
        return struct.pack(">q", val.value)
    if isinstance(val, datetime):
        dt_utc = val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
        epoch_us = int(dt_utc.timestamp() * 1_000_000)
        return struct.pack(">q", epoch_us)
    raise TypeError(f"Unsupported timestamp_us type: {type(val)}")


def _encode_date32(val: Any) -> bytes:
    """Encode date32 as 4-byte big-endian int32 epoch days."""
    if val is None:
        return struct.pack(">i", NULL_INT32_SENTINEL)
    if isinstance(val, int):
        return struct.pack(">i", val)
    if isinstance(val, pa.Scalar):
        if val.as_py() is None:
            return struct.pack(">i", NULL_INT32_SENTINEL)
        return struct.pack(">i", val.value)
    if isinstance(val, date):
        epoch_days = (val - date(1970, 1, 1)).days
        return struct.pack(">i", epoch_days)
    raise TypeError(f"Unsupported date32 type: {type(val)}")


def _encode_int64(val: Optional[int]) -> bytes:
    """Encode int64 as 8-byte big-endian signed integer."""
    if val is None:
        return struct.pack(">q", NULL_INT64_SENTINEL)
    return struct.pack(">q", int(val))


def _encode_int32(val: Optional[int]) -> bytes:
    """Encode int32 as 4-byte big-endian signed integer."""
    if val is None:
        return struct.pack(">i", NULL_INT32_SENTINEL)
    return struct.pack(">i", int(val))


def serialize_trade_row_binary(
    source_id: str,
    channel_id: str,
    symbol: str,
    trading_date: Any,
    exchange_time_utc: Any,
    feed_time_utc: Any,
    knowledge_time_utc: Any,
    source_seq_num: int,
    trade_id: Optional[str],
    match_sub_idx: int,
    price: Decimal,
    size: Decimal,
    aggressor_side: str,
    trade_condition: str,
) -> bytes:
    """Serialize a single canonical trade row into an unambiguous binary frame."""
    return (
        _encode_string(source_id)
        + _encode_string(channel_id)
        + _encode_string(symbol)
        + _encode_date32(trading_date)
        + _encode_timestamp_ns(exchange_time_utc)
        + _encode_timestamp_ns(feed_time_utc)
        + _encode_timestamp_us(knowledge_time_utc)
        + _encode_int64(source_seq_num)
        + _encode_string(trade_id)
        + _encode_int32(match_sub_idx)
        + _encode_decimal(price)
        + _encode_decimal(size)
        + _encode_string(aggressor_side)
        + _encode_string(trade_condition)
        + RECORD_SEPARATOR_BYTE
    )


def calculate_canonical_trades_sha256(table: pa.Table) -> str:
    """Calculate deterministic canonical SHA-256 hash over a PyArrow Trades Table.

    Execution Protocol:
    1. Verify all required canonical trades columns exist.
    2. Sort table strictly by Trade Row Identity ASC:
       (source_id, channel_id, symbol, trading_date, source_seq_num, match_sub_idx).
    3. Stream rows sequentially into hashlib.sha256() using Length-Prefixed Binary frames.
    4. Return hexadecimal digest string.
    """
    if table.num_rows == 0:
        return hashlib.sha256(b"EMPTY_TRADES_TABLE").hexdigest()

    # Fail-fast check for missing canonical columns
    missing_columns = [col for col in CANONICAL_TRADES_COLUMN_NAMES if col not in table.column_names]
    if missing_columns:
        raise DataContractError(
            f"Cannot compute canonical trades hash: table is missing required columns: {missing_columns}"
        )

    # Sort table strictly by Trade Row Identity ASC
    sort_keys = [(col, "ascending") for col in TRADE_ROW_IDENTITY_COLUMNS]
    sorted_table = table.sort_by(sort_keys)

    hasher = hashlib.sha256()

    # Extract columns in Arrow array form for high performance
    source_ids = sorted_table["source_id"]
    channel_ids = sorted_table["channel_id"]
    symbols = sorted_table["symbol"]
    trading_dates = sorted_table["trading_date"]
    exchange_times = sorted_table["exchange_time_utc"]
    feed_times = sorted_table["feed_time_utc"]
    knowledge_times = sorted_table["knowledge_time_utc"]
    source_seq_nums = sorted_table["source_seq_num"]
    trade_ids = sorted_table["trade_id"]
    match_sub_indices = sorted_table["match_sub_idx"]
    prices = sorted_table["price"]
    sizes = sorted_table["size"]
    aggressor_sides = sorted_table["aggressor_side"]
    trade_conditions = sorted_table["trade_condition"]

    num_rows = sorted_table.num_rows
    for i in range(num_rows):
        row_bytes = serialize_trade_row_binary(
            source_id=source_ids[i].as_py(),
            channel_id=channel_ids[i].as_py(),
            symbol=symbols[i].as_py(),
            trading_date=trading_dates[i],
            exchange_time_utc=exchange_times[i],
            feed_time_utc=feed_times[i],
            knowledge_time_utc=knowledge_times[i],
            source_seq_num=source_seq_nums[i].as_py(),
            trade_id=trade_ids[i].as_py(),
            match_sub_idx=match_sub_indices[i].as_py(),
            price=prices[i].as_py(),
            size=sizes[i].as_py(),
            aggressor_side=aggressor_sides[i].as_py(),
            trade_condition=trade_conditions[i].as_py(),
        )
        hasher.update(row_bytes)

    return hasher.hexdigest()
