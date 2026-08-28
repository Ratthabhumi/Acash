"""Length-Prefixed Binary Serialization, Logical Cryptographic Hashing, and Unified Reconstruction Ordering for Order Book Subsystem (Phase 3B).

Strictly enforces:
- Length-Prefixed Binary Serialization: Invariant to Parquet chunking, row groups, codecs, or memory layouts.
- Collision-Safe snapshot_id derivation via length-prefixed binary SHA-256.
- ASCII-only byte-wise lexical total ordering for source_order_key.
- Unified 5-Tuple ReconstructionOrder comparator: (exchange_time_utc, source_order_key, message_type_rank, side_rank, level_or_action_idx).
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import struct
from typing import Any, Dict, List, Optional, Tuple, Union
import pyarrow as pa

from acash.data.orderbook.schema import (
    BOOK_DELTA_ROW_IDENTITY_COLUMNS,
    BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS,
    CANONICAL_BOOK_DELTA_SCHEMA,
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
)
from acash.data.schema import DataContractError

# ---------------------------------------------------------------------------
# Binary Serialization Helpers
# ---------------------------------------------------------------------------

NULL_UINT32_TAG: bytes = struct.pack(">I", 0xFFFFFFFF)
NULL_INT64_SENTINEL: bytes = struct.pack(">q", -9223372036854775808)
NULL_INT32_SENTINEL: bytes = struct.pack(">i", -2147483648)
NULL_UINT8_SENTINEL: bytes = struct.pack("B", 0xFF)
RECORD_SEPARATOR: bytes = b"\x1e"


def serialize_string_binary(val: Optional[str]) -> bytes:
    """Serialize a string into [uint32_be(len)][utf8_bytes] or 0xFFFFFFFF null tag."""
    if val is None:
        return NULL_UINT32_TAG
    encoded = str(val).encode("utf-8")
    return struct.pack(">I", len(encoded)) + encoded


def serialize_decimal128_binary(val: Optional[Union[Decimal, str, int, float]]) -> bytes:
    """Serialize Decimal128 into [uint32_be(len)][ascii_bytes] or 0xFFFFFFFF null tag."""
    if val is None:
        return NULL_UINT32_TAG
    d = val if isinstance(val, Decimal) else Decimal(str(val))
    encoded = f"{d:.18f}".encode("ascii")
    return struct.pack(">I", len(encoded)) + encoded


def serialize_timestamp_ns_binary(val: Optional[Union[datetime, int]]) -> bytes:
    """Serialize timestamp into signed 64-bit big-endian epoch nanoseconds."""
    if val is None:
        return NULL_INT64_SENTINEL
    if isinstance(val, int):
        return struct.pack(">q", val)
    dt_utc = val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
    td = dt_utc - datetime(1970, 1, 1, tzinfo=timezone.utc)
    epoch_ns = (td.days * 86400 + td.seconds) * 1_000_000_000 + td.microseconds * 1_000
    return struct.pack(">q", epoch_ns)


def serialize_timestamp_us_binary(val: Optional[Union[datetime, int]]) -> bytes:
    """Serialize timestamp into signed 64-bit big-endian epoch microseconds."""
    if val is None:
        return NULL_INT64_SENTINEL
    if isinstance(val, int):
        return struct.pack(">q", val)
    dt_utc = val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
    td = dt_utc - datetime(1970, 1, 1, tzinfo=timezone.utc)
    epoch_us = (td.days * 86400 + td.seconds) * 1_000_000 + td.microseconds
    return struct.pack(">q", epoch_us)



def serialize_date32_binary(val: Optional[Union[date, str]]) -> bytes:
    """Serialize date into signed 32-bit big-endian epoch days."""
    if val is None:
        return NULL_INT32_SENTINEL
    if isinstance(val, str):
        d = date.fromisoformat(val)
    else:
        d = val
    epoch_days = (d - date(1970, 1, 1)).days
    return struct.pack(">i", epoch_days)


def serialize_int64_binary(val: Optional[int]) -> bytes:
    """Serialize int64 into signed 64-bit big-endian integer."""
    if val is None:
        return NULL_INT64_SENTINEL
    return struct.pack(">q", int(val))


def serialize_int32_binary(val: Optional[int]) -> bytes:
    """Serialize int32 into signed 32-bit big-endian integer."""
    if val is None:
        return NULL_INT32_SENTINEL
    return struct.pack(">i", int(val))


def serialize_bool_binary(val: Optional[bool]) -> bytes:
    """Serialize boolean into single byte (1 for True, 0 for False, 0xFF for Null)."""
    if val is None:
        return NULL_UINT8_SENTINEL
    return struct.pack("B", 1 if val else 0)


# ---------------------------------------------------------------------------
# Canonical snapshot_id Derivation
# ---------------------------------------------------------------------------


def derive_canonical_snapshot_id(
    source_id: str,
    channel_id: str,
    symbol: str,
    trading_date: Union[date, str],
    source_order_key: str,
) -> str:
    """Derive collision-safe, deterministic, replay-stable snapshot_id via length-prefixed binary SHA-256.

    Formula:
    payload = serialize_binary([source_id, channel_id, symbol, trading_date, source_order_key])
    snapshot_id = "snap_" + SHA-256(payload)[:32]
    """
    hasher = hashlib.sha256()
    hasher.update(serialize_string_binary(source_id))
    hasher.update(serialize_string_binary(channel_id))
    hasher.update(serialize_string_binary(symbol))
    hasher.update(serialize_date32_binary(trading_date))
    hasher.update(serialize_string_binary(source_order_key))
    return f"snap_{hasher.hexdigest()[:32]}"


# ---------------------------------------------------------------------------
# Row Binary Serializers
# ---------------------------------------------------------------------------


def serialize_book_snapshot_row_binary(
    source_id: str,
    channel_id: str,
    symbol: str,
    trading_date: Union[date, str],
    exchange_time_utc: Union[datetime, int],
    feed_time_utc: Optional[Union[datetime, int]],
    knowledge_time_utc: Union[datetime, int],
    source_seq_num: int,
    source_order_key: str,
    snapshot_id: str,
    is_snapshot_complete: bool,
    side: str,
    level_idx: int,
    price: Union[Decimal, str, int, float],
    size: Union[Decimal, str, int, float],
    order_count: Optional[int],
) -> bytes:
    """Serialize a single snapshot row into an unambiguous length-prefixed binary byte frame."""
    buf = bytearray()
    buf.extend(serialize_string_binary(source_id))
    buf.extend(serialize_string_binary(channel_id))
    buf.extend(serialize_string_binary(symbol))
    buf.extend(serialize_date32_binary(trading_date))
    buf.extend(serialize_timestamp_ns_binary(exchange_time_utc))
    buf.extend(serialize_timestamp_ns_binary(feed_time_utc))
    buf.extend(serialize_timestamp_us_binary(knowledge_time_utc))
    buf.extend(serialize_int64_binary(source_seq_num))
    buf.extend(serialize_string_binary(source_order_key))
    buf.extend(serialize_string_binary(snapshot_id))
    buf.extend(serialize_bool_binary(is_snapshot_complete))
    buf.extend(serialize_string_binary(side))
    buf.extend(serialize_int32_binary(level_idx))
    buf.extend(serialize_decimal128_binary(price))
    buf.extend(serialize_decimal128_binary(size))
    buf.extend(serialize_int32_binary(order_count))
    buf.extend(RECORD_SEPARATOR)
    return bytes(buf)


def serialize_book_delta_row_binary(
    source_id: str,
    channel_id: str,
    symbol: str,
    trading_date: Union[date, str],
    exchange_time_utc: Union[datetime, int],
    feed_time_utc: Optional[Union[datetime, int]],
    knowledge_time_utc: Union[datetime, int],
    source_seq_num: int,
    source_order_key: str,
    action_sub_idx: int,
    delta_type: str,
    action: str,
    side: str,
    price: Optional[Union[Decimal, str, int, float]],
    size: Optional[Union[Decimal, str, int, float]],
    order_id: Optional[str],
    level_idx: Optional[int],
    order_count: Optional[int],
) -> bytes:
    """Serialize a single delta row into an unambiguous length-prefixed binary byte frame."""
    buf = bytearray()
    buf.extend(serialize_string_binary(source_id))
    buf.extend(serialize_string_binary(channel_id))
    buf.extend(serialize_string_binary(symbol))
    buf.extend(serialize_date32_binary(trading_date))
    buf.extend(serialize_timestamp_ns_binary(exchange_time_utc))
    buf.extend(serialize_timestamp_ns_binary(feed_time_utc))
    buf.extend(serialize_timestamp_us_binary(knowledge_time_utc))
    buf.extend(serialize_int64_binary(source_seq_num))
    buf.extend(serialize_string_binary(source_order_key))
    buf.extend(serialize_int32_binary(action_sub_idx))
    buf.extend(serialize_string_binary(delta_type))
    buf.extend(serialize_string_binary(action))
    buf.extend(serialize_string_binary(side))
    buf.extend(serialize_decimal128_binary(price))
    buf.extend(serialize_decimal128_binary(size))
    buf.extend(serialize_string_binary(order_id))
    buf.extend(serialize_int32_binary(level_idx))
    buf.extend(serialize_int32_binary(order_count))
    buf.extend(RECORD_SEPARATOR)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Cryptographic Logical Hashing
# ---------------------------------------------------------------------------


def calculate_canonical_book_snapshot_sha256(table: pa.Table) -> str:
    """Compute logical, deterministic SHA-256 fingerprint for a canonical book snapshots table.

    Invariant to:
    - Row permutation order (sorted by Snapshot Row Identity ASC).
    - Parquet chunking, row groups, codecs, or memory layouts.
    """
    for field in CANONICAL_BOOK_SNAPSHOT_SCHEMA:
        if field.name not in table.column_names:
            raise DataContractError(f"Missing column in Book Snapshot table: {field.name}")

    if table.num_rows == 0:
        return hashlib.sha256(b"CANONICAL_BOOK_SNAPSHOTS_EMPTY_TABLE_V1").hexdigest()

    # Sort table by Snapshot Row Identity
    sort_indices = pa.compute.sort_indices(
        table,
        sort_keys=[(col, "ascending") for col in BOOK_SNAPSHOT_ROW_IDENTITY_COLUMNS],
    )
    sorted_table = table.take(sort_indices)

    hasher = hashlib.sha256()
    hasher.update(b"ACASH_CANONICAL_BOOK_SNAPSHOT_V1.8\n")

    pydict = sorted_table.to_pydict()
    num_rows = sorted_table.num_rows

    for i in range(num_rows):
        row_bytes = serialize_book_snapshot_row_binary(
            source_id=str(pydict["source_id"][i]),
            channel_id=str(pydict["channel_id"][i]),
            symbol=str(pydict["symbol"][i]),
            trading_date=pydict["trading_date"][i],
            exchange_time_utc=pydict["exchange_time_utc"][i],
            feed_time_utc=pydict["feed_time_utc"][i],
            knowledge_time_utc=pydict["knowledge_time_utc"][i],
            source_seq_num=int(pydict["source_seq_num"][i]),
            source_order_key=str(pydict["source_order_key"][i]),
            snapshot_id=str(pydict["snapshot_id"][i]),
            is_snapshot_complete=bool(pydict["is_snapshot_complete"][i]),
            side=str(pydict["side"][i]),
            level_idx=int(pydict["level_idx"][i]),
            price=pydict["price"][i],
            size=pydict["size"][i],
            order_count=pydict["order_count"][i],
        )
        hasher.update(row_bytes)

    return hasher.hexdigest()


def calculate_canonical_book_delta_sha256(table: pa.Table) -> str:
    """Compute logical, deterministic SHA-256 fingerprint for a canonical book deltas table.

    Invariant to:
    - Row permutation order (sorted by Delta Row Identity ASC).
    - Parquet chunking, row groups, codecs, or memory layouts.
    """
    for field in CANONICAL_BOOK_DELTA_SCHEMA:
        if field.name not in table.column_names:
            raise DataContractError(f"Missing column in Book Delta table: {field.name}")

    if table.num_rows == 0:
        return hashlib.sha256(b"CANONICAL_BOOK_DELTAS_EMPTY_TABLE_V1").hexdigest()

    # Sort table by Delta Row Identity
    sort_indices = pa.compute.sort_indices(
        table,
        sort_keys=[(col, "ascending") for col in BOOK_DELTA_ROW_IDENTITY_COLUMNS],
    )
    sorted_table = table.take(sort_indices)

    hasher = hashlib.sha256()
    hasher.update(b"ACASH_CANONICAL_BOOK_DELTA_V1.8\n")

    pydict = sorted_table.to_pydict()
    num_rows = sorted_table.num_rows

    for i in range(num_rows):
        row_bytes = serialize_book_delta_row_binary(
            source_id=str(pydict["source_id"][i]),
            channel_id=str(pydict["channel_id"][i]),
            symbol=str(pydict["symbol"][i]),
            trading_date=pydict["trading_date"][i],
            exchange_time_utc=pydict["exchange_time_utc"][i],
            feed_time_utc=pydict["feed_time_utc"][i],
            knowledge_time_utc=pydict["knowledge_time_utc"][i],
            source_seq_num=int(pydict["source_seq_num"][i]),
            source_order_key=str(pydict["source_order_key"][i]),
            action_sub_idx=int(pydict["action_sub_idx"][i]),
            delta_type=str(pydict["delta_type"][i]),
            action=str(pydict["action"][i]),
            side=str(pydict["side"][i]),
            price=pydict["price"][i],
            size=pydict["size"][i],
            order_id=pydict["order_id"][i],
            level_idx=pydict["level_idx"][i],
            order_count=pydict["order_count"][i],
        )
        hasher.update(row_bytes)

    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Unified Reconstruction Ordering Comparator
# ---------------------------------------------------------------------------


class ReconstructionOrderKey:
    """Canonical 5-Tuple Reconstruction Order Key representation.

    Tuple: (exchange_time_utc_ns, source_order_key_bytes, message_type_rank, side_rank, level_or_action_idx)
    """

    __slots__ = (
        "exchange_time_ns",
        "source_order_key_bytes",
        "message_type_rank",
        "side_rank",
        "level_or_action_idx",
    )

    def __init__(
        self,
        exchange_time_ns: int,
        source_order_key: str,
        message_type_rank: int,
        side_rank: int,
        level_or_action_idx: int,
    ) -> None:
        self.exchange_time_ns = exchange_time_ns
        self.source_order_key_bytes = source_order_key.encode("ascii")
        self.message_type_rank = message_type_rank
        self.side_rank = side_rank
        self.level_or_action_idx = level_or_action_idx

    def to_tuple(self) -> Tuple[int, bytes, int, int, int]:
        return (
            self.exchange_time_ns,
            self.source_order_key_bytes,
            self.message_type_rank,
            self.side_rank,
            self.level_or_action_idx,
        )

    def __lt__(self, other: "ReconstructionOrderKey") -> bool:
        return self.to_tuple() < other.to_tuple()

    def __le__(self, other: "ReconstructionOrderKey") -> bool:
        return self.to_tuple() <= other.to_tuple()

    def __gt__(self, other: "ReconstructionOrderKey") -> bool:
        return self.to_tuple() > other.to_tuple()

    def __ge__(self, other: "ReconstructionOrderKey") -> bool:
        return self.to_tuple() >= other.to_tuple()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ReconstructionOrderKey):
            return False
        return self.to_tuple() == other.to_tuple()


def create_snapshot_frame_boundary(
    exchange_time_utc: datetime,
    source_order_key: str,
) -> ReconstructionOrderKey:
    """Create the upper ordering boundary of a Root Snapshot Frame.

    Boundary tuple: (exchange_time_ns, source_order_key_bytes, 0, 2147483647, 2147483647).
    Any subsequent delta at the same exchange time and source_order_key (which has message_type_rank=1)
    will strictly satisfy delta.order > snapshot.boundary.
    """
    epoch_ns = int(exchange_time_utc.astimezone(timezone.utc).timestamp() * 1_000_000_000)
    return ReconstructionOrderKey(
        exchange_time_ns=epoch_ns,
        source_order_key=source_order_key,
        message_type_rank=0,
        side_rank=2147483647,
        level_or_action_idx=2147483647,
    )


def create_delta_order_key(
    exchange_time_utc: datetime,
    source_order_key: str,
    action_sub_idx: int,
) -> ReconstructionOrderKey:
    """Create the ReconstructionOrderKey for an incremental delta record."""
    epoch_ns = int(exchange_time_utc.astimezone(timezone.utc).timestamp() * 1_000_000_000)
    return ReconstructionOrderKey(
        exchange_time_ns=epoch_ns,
        source_order_key=source_order_key,
        message_type_rank=1,
        side_rank=0,
        level_or_action_idx=action_sub_idx,
    )
