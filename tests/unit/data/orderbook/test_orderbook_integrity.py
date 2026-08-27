"""Unit tests for Order Book Integrity Validator (Phase 3B)."""

from datetime import date, datetime, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.data.orderbook.integrity import OrderBookIntegrityValidator
from acash.data.orderbook.schema import (
    CANONICAL_BOOK_DELTA_SCHEMA,
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
)
from acash.data.schema import IntegrityViolationError


def _make_valid_snapshot_table() -> pa.Table:
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
        "source_seq_num": [1000, 1000],
        "source_order_key": ["00000000000000001000", "00000000000000001000"],
        "snapshot_id": ["snap_valid_001", "snap_valid_001"],
        "is_snapshot_complete": [True, True],
        "side": ["BID", "ASK"],
        "level_idx": [0, 0],
        "price": [Decimal("5000.25"), Decimal("5000.50")],
        "size": [Decimal("10"), Decimal("5")],
        "order_count": [3, 2],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)


def _make_valid_delta_table() -> pa.Table:
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
        "source_seq_num": [1001, 1002],
        "source_order_key": ["00000000000000001001", "00000000000000001002"],
        "action_sub_idx": [0, 0],
        "delta_type": ["MBP", "MBP"],
        "action": ["MODIFY", "CLEAR"],
        "side": ["BID", "ALL"],
        "price": [Decimal("5000.25"), None],
        "size": [Decimal("15"), None],
        "order_id": [None, None],
        "level_idx": [0, None],
        "order_count": [4, None],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_DELTA_SCHEMA)


def test_valid_snapshot_and_delta_tables() -> None:
    """Verify valid snapshot and delta tables pass validation."""
    validator = OrderBookIntegrityValidator()
    report_snap, _ = validator.validate_snapshot_table(_make_valid_snapshot_table())
    assert report_snap.is_valid

    report_delta, _ = validator.validate_delta_table(_make_valid_delta_table())
    assert report_delta.is_valid


def test_non_ascii_source_order_key_rejected() -> None:
    """Verify non-ASCII characters in source_order_key raise IntegrityViolationError."""
    validator = OrderBookIntegrityValidator()
    data = _make_valid_snapshot_table().to_pydict()
    data["source_order_key"][0] = "KEY_ไทย_001"  # Non-ASCII!
    table = pa.Table.from_pydict(data, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

    with pytest.raises(IntegrityViolationError, match="non-ASCII"):
        validator.validate_snapshot_table(table)


def test_frame_metadata_inconsistency_rejected() -> None:
    """Verify rows with same snapshot_id having differing timestamps raise IntegrityViolationError."""
    validator = OrderBookIntegrityValidator()
    data = _make_valid_snapshot_table().to_pydict()
    # Modify second row's exchange_time while keeping same snapshot_id
    data["exchange_time_utc"][1] = datetime(2026, 1, 19, 14, 30, 0, 999, tzinfo=timezone.utc)
    table = pa.Table.from_pydict(data, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

    with pytest.raises(IntegrityViolationError, match="FRAME_METADATA_INCONSISTENCY"):
        validator.validate_snapshot_table(table)


def test_clear_control_action_invariants() -> None:
    """Verify CLEAR action invariants (price=None, size=None, level_idx=None, order_id=None)."""
    validator = OrderBookIntegrityValidator()
    data = _make_valid_delta_table().to_pydict()
    # Make CLEAR action contain non-null price -> violation
    data["price"][1] = Decimal("100.0")
    table = pa.Table.from_pydict(data, schema=CANONICAL_BOOK_DELTA_SCHEMA)

    with pytest.raises(IntegrityViolationError, match="CLEAR action MUST have price=None"):
        validator.validate_delta_table(table)


def test_mbp_order_id_must_be_null() -> None:
    """Verify that MBP deltas with populated order_id raise IntegrityViolationError."""
    validator = OrderBookIntegrityValidator()
    data = _make_valid_delta_table().to_pydict()
    data["order_id"][0] = "ORD_123"  # MBP cannot have order_id
    table = pa.Table.from_pydict(data, schema=CANONICAL_BOOK_DELTA_SCHEMA)

    with pytest.raises(IntegrityViolationError, match="MBP delta MUST have order_id=None"):
        validator.validate_delta_table(table)


def test_mbo_missing_order_id_rejected() -> None:
    """Verify that MBO deltas with missing/empty order_id raise IntegrityViolationError."""
    validator = OrderBookIntegrityValidator()
    data = {
        "source_id": ["CME"],
        "channel_id": ["310"],
        "symbol": ["ES.FUT"],
        "trading_date": [date(2026, 1, 19)],
        "exchange_time_utc": [datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)],
        "feed_time_utc": [None],
        "knowledge_time_utc": [datetime(2026, 1, 19, 14, 30, 1, 0, tzinfo=timezone.utc)],
        "source_seq_num": [1001],
        "source_order_key": ["00000000000000001001"],
        "action_sub_idx": [0],
        "delta_type": ["MBO"],
        "action": ["ADD"],
        "side": ["BID"],
        "price": [Decimal("5000.25")],
        "size": [Decimal("10")],
        "order_id": [None],  # Missing for MBO!
        "level_idx": [None],
        "order_count": [None],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_BOOK_DELTA_SCHEMA)

    with pytest.raises(IntegrityViolationError, match="MBO ADD delta MUST have non-null and non-empty order_id"):
        validator.validate_delta_table(table)


def test_duplicate_snapshot_and_delta_identities_rejected() -> None:
    """Verify duplicate Snapshot and Delta Row Identities are rejected."""
    validator = OrderBookIntegrityValidator()

    # 1. Duplicate Snapshot Row Identity in batch
    data_snap = _make_valid_snapshot_table().to_pydict()
    data_snap["side"][1] = "BID"  # Now both rows are (CME, 310, ES, 2026-01-19, 1000, BID, level 0)
    tbl_dup_snap = pa.Table.from_pydict(data_snap, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)
    with pytest.raises(IntegrityViolationError, match="BATCH_SNAPSHOT_IDENTITY_DUPLICATE"):
        validator.validate_snapshot_table(tbl_dup_snap)

    # 2. Duplicate Delta Row Identity in batch
    data_delta = _make_valid_delta_table().to_pydict()
    data_delta["source_seq_num"][1] = 1001  # Now both rows are (CME, 310, ES, 2026-01-19, 1001, action_sub_idx 0)
    tbl_dup_delta = pa.Table.from_pydict(data_delta, schema=CANONICAL_BOOK_DELTA_SCHEMA)
    with pytest.raises(IntegrityViolationError, match="BATCH_DELTA_IDENTITY_DUPLICATE"):
        validator.validate_delta_table(tbl_dup_delta)
