"""Unit tests for Binary Serialization, Hashing, and Snapshot ID Derivation for Order Book (Phase 3B)."""

from datetime import date, datetime, timezone
from decimal import Decimal
import io
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from acash.data.orderbook.hashing import (
    calculate_canonical_book_delta_sha256,
    calculate_canonical_book_snapshot_sha256,
    derive_canonical_snapshot_id,
)
from acash.data.orderbook.schema import (
    CANONICAL_BOOK_DELTA_SCHEMA,
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
)


def _make_sample_snapshot_table() -> pa.Table:
    """Helper to build a sample multi-row snapshot frame."""
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc),
        ],
        "source_seq_num": [5000, 5000],
        "source_order_key": ["00000000000000005000", "00000000000000005000"],
        "snapshot_id": ["snap_test_001", "snap_test_001"],
        "is_snapshot_complete": [True, True],
        "side": ["BID", "ASK"],
        "level_idx": [0, 0],
        "price": [Decimal("5000.250000000000000000"), Decimal("5000.500000000000000000")],
        "size": [Decimal("10.000000000000000000"), Decimal("5.000000000000000000")],
        "order_count": [3, 2],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)


def _make_sample_delta_table() -> pa.Table:
    """Helper to build a sample delta table."""
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 200, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 300, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc),
        ],
        "source_seq_num": [5001, 5002],
        "source_order_key": ["00000000000000005001", "00000000000000005002"],
        "action_sub_idx": [0, 0],
        "delta_type": ["MBP", "MBP"],
        "action": ["MODIFY", "CLEAR"],
        "side": ["BID", "ALL"],
        "price": [Decimal("5000.250000000000000000"), None],
        "size": [Decimal("15.000000000000000000"), None],
        "order_id": [None, None],
        "level_idx": [0, None],
        "order_count": [4, None],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_DELTA_SCHEMA)


def test_canonical_book_snapshot_hash_permutation_and_codec_invariance() -> None:
    """Verify that permuting snapshot rows and changing parquet compression codecs produces identical logical SHA-256."""
    table = _make_sample_snapshot_table()
    hash_original = calculate_canonical_book_snapshot_sha256(table)

    # Invert rows
    permuted = table.take([1, 0])
    assert calculate_canonical_book_snapshot_sha256(permuted) == hash_original

    # Parquet zstd vs snappy codec invariance
    buf_zstd = io.BytesIO()
    pq.write_table(table, buf_zstd, compression="zstd")
    buf_zstd.seek(0)
    tbl_zstd = pq.read_table(buf_zstd)

    buf_snappy = io.BytesIO()
    pq.write_table(table, buf_snappy, compression="snappy")
    buf_snappy.seek(0)
    tbl_snappy = pq.read_table(buf_snappy)

    assert calculate_canonical_book_snapshot_sha256(tbl_zstd) == hash_original
    assert calculate_canonical_book_snapshot_sha256(tbl_snappy) == hash_original


def test_canonical_book_delta_hash_permutation_and_codec_invariance() -> None:
    """Verify that permuting delta rows and changing parquet codecs produces identical logical SHA-256."""
    table = _make_sample_delta_table()
    hash_original = calculate_canonical_book_delta_sha256(table)

    permuted = table.take([1, 0])
    assert calculate_canonical_book_delta_sha256(permuted) == hash_original

    buf_zstd = io.BytesIO()
    pq.write_table(table, buf_zstd, compression="zstd")
    buf_zstd.seek(0)
    assert calculate_canonical_book_delta_sha256(pq.read_table(buf_zstd)) == hash_original


def test_canonical_hash_detects_field_modifications() -> None:
    """Verify modifying any snapshot or delta field alters the hash."""
    base_snap = _make_sample_snapshot_table()
    base_hash = calculate_canonical_book_snapshot_sha256(base_snap)

    data_mod = base_snap.to_pydict()
    data_mod["price"][0] = Decimal("5000.260000000000000000")
    tbl_mod = pa.Table.from_pydict(data_mod, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)
    assert calculate_canonical_book_snapshot_sha256(tbl_mod) != base_hash

    data_mod_key = base_snap.to_pydict()
    data_mod_key["source_order_key"][0] = "00000000000000009999"
    tbl_mod_key = pa.Table.from_pydict(data_mod_key, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)
    assert calculate_canonical_book_snapshot_sha256(tbl_mod_key) != base_hash


def test_collision_safe_snapshot_id_derivation() -> None:
    """Verify that snapshot_id derivation prevents delimiter collision."""
    # Compare (source="A_B", channel="C") vs (source="A", channel="B_C")
    id1 = derive_canonical_snapshot_id(
        source_id="A_B",
        channel_id="C",
        symbol="ES",
        trading_date=date(2026, 1, 19),
        source_order_key="001",
    )
    id2 = derive_canonical_snapshot_id(
        source_id="A",
        channel_id="B_C",
        symbol="ES",
        trading_date=date(2026, 1, 19),
        source_order_key="001",
    )
    assert id1 != id2
    assert id1.startswith("snap_")
    assert len(id1) == 5 + 32
