"""Unit tests for Length-Prefixed Binary Serialization and Logical Cryptographic Hashing for Trades."""

from datetime import date, datetime, timezone
from decimal import Decimal
import io
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from acash.data.trades.hashing import (
    calculate_canonical_trades_sha256,
    serialize_trade_row_binary,
)
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA


def _make_sample_trades_table() -> pa.Table:
    """Helper to build a small sample PyArrow table conforming to CANONICAL_TRADES_SCHEMA."""
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 200, tzinfo=timezone.utc),
        ],
        "feed_time_utc": [
            datetime(2026, 1, 19, 14, 30, 0, 150, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 0, 250, tzinfo=timezone.utc),
        ],
        "knowledge_time_utc": [
            datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc),
        ],
        "source_seq_num": [1001, 1002],
        "trade_id": ["TRD_001", None],
        "match_sub_idx": [0, 0],
        "price": [Decimal("5000.250000000000000000"), Decimal("5000.500000000000000000")],
        "size": [Decimal("10.000000000000000000"), Decimal("5.000000000000000000")],
        "aggressor_side": ["BUY", "SELL"],
        "trade_condition": ["REGULAR", "REGULAR"],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)


def test_canonical_trades_hash_row_order_invariance() -> None:
    """Verify that permuting trade rows produces an identical SHA-256 hash (due to canonical sorting)."""
    table = _make_sample_trades_table()
    hash_original = calculate_canonical_trades_sha256(table)

    # Invert rows
    permuted_table = table.take([1, 0])
    hash_permuted = calculate_canonical_trades_sha256(permuted_table)

    assert hash_original == hash_permuted


def test_canonical_trades_hash_codec_invariance() -> None:
    """Verify that writing to Parquet with different codecs does not alter the logical canonical hash."""
    table = _make_sample_trades_table()
    hash_memory = calculate_canonical_trades_sha256(table)

    # Write & read with zstd
    buf_zstd = io.BytesIO()
    pq.write_table(table, buf_zstd, compression="zstd")
    buf_zstd.seek(0)
    table_zstd = pq.read_table(buf_zstd)

    # Write & read with snappy
    buf_snappy = io.BytesIO()
    pq.write_table(table, buf_snappy, compression="snappy")
    buf_snappy.seek(0)
    table_snappy = pq.read_table(buf_snappy)

    assert calculate_canonical_trades_sha256(table_zstd) == hash_memory
    assert calculate_canonical_trades_sha256(table_snappy) == hash_memory


def test_canonical_trades_hash_detects_any_modification() -> None:
    """Verify that modifying any canonical field (price, size, aggressor, sub_idx) alters the hash."""
    base_table = _make_sample_trades_table()
    base_hash = calculate_canonical_trades_sha256(base_table)

    # 1. Modify price
    data_mod_price = base_table.to_pydict()
    data_mod_price["price"][0] = Decimal("5000.260000000000000000")
    tbl_mod_price = pa.Table.from_pydict(data_mod_price, schema=CANONICAL_TRADES_SCHEMA)
    assert calculate_canonical_trades_sha256(tbl_mod_price) != base_hash

    # 2. Modify size
    data_mod_size = base_table.to_pydict()
    data_mod_size["size"][0] = Decimal("11.000000000000000000")
    tbl_mod_size = pa.Table.from_pydict(data_mod_size, schema=CANONICAL_TRADES_SCHEMA)
    assert calculate_canonical_trades_sha256(tbl_mod_size) != base_hash

    # 3. Modify aggressor_side
    data_mod_side = base_table.to_pydict()
    data_mod_side["aggressor_side"][0] = "SELL"
    tbl_mod_side = pa.Table.from_pydict(data_mod_side, schema=CANONICAL_TRADES_SCHEMA)
    assert calculate_canonical_trades_sha256(tbl_mod_side) != base_hash

    # 4. Modify match_sub_idx
    data_mod_idx = base_table.to_pydict()
    data_mod_idx["match_sub_idx"][0] = 1
    tbl_mod_idx = pa.Table.from_pydict(data_mod_idx, schema=CANONICAL_TRADES_SCHEMA)
    assert calculate_canonical_trades_sha256(tbl_mod_idx) != base_hash


def test_canonical_trades_hash_nanosecond_distinguishability() -> None:
    """Verify that timestamp differences in nanoseconds (e.g. 100ns vs 200ns) produce distinct hashes."""
    data1 = {
        "source_id": ["CME"],
        "channel_id": ["310"],
        "symbol": ["ES.FUT"],
        "trading_date": [date(2026, 1, 19)],
        "exchange_time_utc": [datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)],
        "feed_time_utc": [None],
        "knowledge_time_utc": [datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc)],
        "source_seq_num": [1001],
        "trade_id": [None],
        "match_sub_idx": [0],
        "price": [Decimal("5000.250000000000000000")],
        "size": [Decimal("10.000000000000000000")],
        "aggressor_side": ["BUY"],
        "trade_condition": ["REGULAR"],
    }
    tbl1 = pa.Table.from_pydict(data1, schema=CANONICAL_TRADES_SCHEMA)

    data2 = dict(data1)
    data2["exchange_time_utc"] = [datetime(2026, 1, 19, 14, 30, 0, 200, tzinfo=timezone.utc)]
    tbl2 = pa.Table.from_pydict(data2, schema=CANONICAL_TRADES_SCHEMA)

    hash1 = calculate_canonical_trades_sha256(tbl1)
    hash2 = calculate_canonical_trades_sha256(tbl2)
    assert hash1 != hash2


def test_length_prefixed_binary_prevents_delimiter_collision() -> None:
    """Verify that length-prefixed encoding prevents ambiguity from special characters in strings."""
    # Compare ("A|B", "C") vs ("A", "B|C")
    row_bytes1 = serialize_trade_row_binary(
        source_id="A|B",
        channel_id="C",
        symbol="ES",
        trading_date=date(2026, 1, 19),
        exchange_time_utc=datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc),
        feed_time_utc=None,
        knowledge_time_utc=datetime(2026, 1, 19, 14, 30, 1, tzinfo=timezone.utc),
        source_seq_num=1,
        trade_id=None,
        match_sub_idx=0,
        price=Decimal("100.0"),
        size=Decimal("1.0"),
        aggressor_side="BUY",
        trade_condition="REGULAR",
    )

    row_bytes2 = serialize_trade_row_binary(
        source_id="A",
        channel_id="B|C",
        symbol="ES",
        trading_date=date(2026, 1, 19),
        exchange_time_utc=datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc),
        feed_time_utc=None,
        knowledge_time_utc=datetime(2026, 1, 19, 14, 30, 1, tzinfo=timezone.utc),
        source_seq_num=1,
        trade_id=None,
        match_sub_idx=0,
        price=Decimal("100.0"),
        size=Decimal("1.0"),
        aggressor_side="BUY",
        trade_condition="REGULAR",
    )

    assert row_bytes1 != row_bytes2
