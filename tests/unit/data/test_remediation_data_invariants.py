"""Unit tests verifying Phase 2 & 3 data integrity, revision sequencing, and hashing remediations."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.data.integrity import DataIntegrityValidator
from acash.data.orderbook.hashing import calculate_canonical_book_snapshot_sha256
from acash.data.orderbook.integrity import OrderBookIntegrityValidator

from acash.data.orderbook.schema import CANONICAL_BOOK_SNAPSHOT_SCHEMA
from acash.data.provenance import BatchManifest, calculate_canonical_batch_sha256
from acash.data.schema import CANONICAL_ARROW_SCHEMA, DataContractError, IntegrityViolationError
from acash.data.trades.hashing import calculate_canonical_trades_sha256
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA


def test_revision_sequencing_per_event_observation_and_max_tracking() -> None:
    """Audit Amendment 1: Sequencing continues from existing_event_max_seq per Event Observation."""
    validator = DataIntegrityValidator()
    t_event = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
    t_know1 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)
    t_know2 = datetime(2026, 1, 1, 10, 3, tzinfo=timezone.utc)

    # Incoming batch with 2 new revisions for the same event observation
    data = {
        "source_id": ["binance", "binance"],
        "symbol": ["BTC/USDT", "BTC/USDT"],
        "timeframe": ["M1", "M1"],
        "event_start_utc": [t_event, t_event],
        "event_end_utc": [t_end, t_end],
        "knowledge_time_utc": [t_know2, t_know1],  # Out of order to test deterministic sorting
        "revision_seq": [None, None],  # ACASH must assign deterministically
        "open": [Decimal("100.00"), Decimal("100.00")],
        "high": [Decimal("105.00"), Decimal("105.00")],
        "low": [Decimal("95.00"), Decimal("95.00")],
        "close": [Decimal("102.00"), Decimal("101.00")],
        "volume": [Decimal("10.0"), Decimal("10.0")],
        "quote_volume": [Decimal("1010.0"), Decimal("1010.0")],
        "trade_count": [50, 50],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_ARROW_SCHEMA)

    # Existing storage already has max sequence = 3 for this exact event observation
    event_key = ("binance", "BTC/USDT", "M1", t_event)
    existing_max_map = {event_key: 3}

    report, sequenced_table = validator.validate_table(
        table,
        existing_event_max_seq=existing_max_map,
    )

    assert report.is_valid is True
    pydict = sequenced_table.to_pydict()

    # Must be sequenced as existing_max + 1 (=4), existing_max + 2 (=5) sorted by knowledge_time_utc ASC
    assert pydict["revision_seq"] == [4, 5]
    assert pydict["knowledge_time_utc"][0] == t_know1
    assert pydict["knowledge_time_utc"][1] == t_know2


def test_duplicate_revision_content_rejection_at_same_knowledge_time() -> None:
    """Audit Amendment 1: Duplicate revision content at the same knowledge_time within an event is rejected."""
    validator = DataIntegrityValidator()
    t_event = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
    t_know = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)

    # Identical revision content at identical knowledge time
    data = {
        "source_id": ["binance", "binance"],
        "symbol": ["BTC/USDT", "BTC/USDT"],
        "timeframe": ["M1", "M1"],
        "event_start_utc": [t_event, t_event],
        "event_end_utc": [t_end, t_end],
        "knowledge_time_utc": [t_know, t_know],
        "revision_seq": [None, None],
        "open": [Decimal("100.00"), Decimal("100.00")],
        "high": [Decimal("105.00"), Decimal("105.00")],
        "low": [Decimal("95.00"), Decimal("95.00")],
        "close": [Decimal("102.00"), Decimal("102.00")],
        "volume": [Decimal("10.0"), Decimal("10.0")],
        "quote_volume": [Decimal("1010.0"), Decimal("1010.0")],
        "trade_count": [50, 50],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_ARROW_SCHEMA)
    report, _ = validator.validate_table(table)

    assert report.is_valid is False
    assert any(err.rule == "DUPLICATE_REVISION_CONTENT" for err in report.errors)


def test_orderbook_snapshot_duplicate_price_level_rejection() -> None:
    """Audit Point 9: Order book snapshot validator rejects duplicate price levels on the same side."""
    validator = OrderBookIntegrityValidator()
    t = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)

    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [t, t],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [t + timedelta(seconds=1), t + timedelta(seconds=1)],
        "source_seq_num": [1000, 1000],
        "source_order_key": ["KEY_001", "KEY_001"],
        "snapshot_id": ["snap_001", "snap_001"],

        "is_snapshot_complete": [True, True],
        "side": ["BID", "BID"],  # Same side
        "level_idx": [0, 1],
        "price": [Decimal("5000.00"), Decimal("5000.00")],  # Duplicate price on BID side!
        "size": [Decimal("10"), Decimal("15")],
        "order_count": [2, 3],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

    with pytest.raises(IntegrityViolationError, match="Duplicate price level"):
        validator.validate_snapshot_table(table)


def test_batch_manifest_sha256_format_validation() -> None:
    """Audit Point 12: BatchManifest strictly requires 64 lowercase hexadecimal characters."""
    from acash.data.provenance import BatchLifecycleStatus
    manifest = BatchManifest(
        batch_id="b1",
        status=BatchLifecycleStatus.PREPARED,
        source_id="src",
        source_uri_or_path="path",
        raw_source_sha256="a" * 64,
        canonical_batch_sha256="b" * 64,
        schema_version="1.0",
        transform_version="1.0",
        symbol="BTC/USDT",
        timeframe="M1",
        year_partition=2026,
        part_file_path="part.parquet",
        row_count=1,
        min_event_time_utc="2026-01-01T00:00:00Z",
        max_event_time_utc="2026-01-01T00:01:00Z",
        created_at_utc="2026-01-01T00:00:00Z",
        updated_at_utc="2026-01-01T00:00:00Z",
    )
    assert manifest.raw_source_sha256 == "a" * 64

    # Invalid uppercase or non-hex length
    with pytest.raises(ValueError, match="Invalid SHA-256 hash"):
        BatchManifest(
            batch_id="b1",
            status=BatchLifecycleStatus.PREPARED,
            source_id="src",
            source_uri_or_path="path",
            raw_source_sha256="INVALID_HASH",
            canonical_batch_sha256="b" * 64,
            schema_version="1.0",
            transform_version="1.0",
            symbol="BTC/USDT",
            timeframe="M1",
            year_partition=2026,
            part_file_path="part.parquet",
            row_count=1,
            min_event_time_utc="2026-01-01T00:00:00Z",
            max_event_time_utc="2026-01-01T00:01:00Z",
            created_at_utc="2026-01-01T00:00:00Z",
            updated_at_utc="2026-01-01T00:00:00Z",
        )



def test_empty_table_schema_validation_in_hashing() -> None:
    """Audit Point 13: calculate_canonical_batch_sha256 validates schema before checking empty rows."""
    empty_invalid = pa.Table.from_pydict({"unrelated_col": pa.array([], type=pa.string())})
    with pytest.raises(DataContractError, match="missing required canonical columns"):
        calculate_canonical_batch_sha256(empty_invalid)

    empty_valid = CANONICAL_ARROW_SCHEMA.empty_table()
    h = calculate_canonical_batch_sha256(empty_valid)
    assert len(h) == 64


def test_cross_batch_duplicate_and_conflicting_revision_rejection() -> None:
    """Audit P0/P1: Validate table rejects duplicate content or conflicting revisions across batches."""
    from acash.data.provenance import calculate_canonical_content_fingerprint
    from acash.data.storage import ParquetStorageEngine
    import tempfile
    from pathlib import Path

    validator = DataIntegrityValidator()
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
    t_know = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)

    # 1. Compute fingerprint of initial persisted revision (Close = 100.00)
    fp_initial = calculate_canonical_content_fingerprint(
        open_price=Decimal("100.00"),
        high_price=Decimal("105.00"),
        low_price=Decimal("95.00"),
        close_price=Decimal("100.00"),
        volume=Decimal("10.0"),
        quote_volume=Decimal("1000.0"),
        trade_count=50,
    )

    existing_lookup = {
        ("binance", "BTC/USDT", "M1", t0, t_know): (1, fp_initial)
    }

    # Case A: Same Event, Same Knowledge Time, Same Content -> DUPLICATE_REVISION_CONTENT
    tbl_dup = pa.Table.from_pydict({
        "source_id": ["binance"],
        "symbol": ["BTC/USDT"],
        "timeframe": ["M1"],
        "event_start_utc": [t0],
        "event_end_utc": [t1],
        "knowledge_time_utc": [t_know],
        "revision_seq": [None],
        "open": [Decimal("100.00")],
        "high": [Decimal("105.00")],
        "low": [Decimal("95.00")],
        "close": [Decimal("100.00")],
        "volume": [Decimal("10.0")],
        "quote_volume": [Decimal("1000.0")],
        "trade_count": [50],
    }, schema=CANONICAL_ARROW_SCHEMA)

    report_dup, _ = validator.validate_table(tbl_dup, existing_revisions_lookup=existing_lookup)
    assert report_dup.is_valid is False
    assert any(err.rule == "DUPLICATE_REVISION_CONTENT" for err in report_dup.errors)

    # Case B: Same Event, Same Knowledge Time, Conflicting Content (Close = 105.00) -> CONFLICTING_REVISION_AT_SAME_KNOWLEDGE_TIME
    tbl_conflict = pa.Table.from_pydict({
        "source_id": ["binance"],
        "symbol": ["BTC/USDT"],
        "timeframe": ["M1"],
        "event_start_utc": [t0],
        "event_end_utc": [t1],
        "knowledge_time_utc": [t_know],
        "revision_seq": [None],
        "open": [Decimal("100.00")],
        "high": [Decimal("105.00")],
        "low": [Decimal("95.00")],
        "close": [Decimal("105.00")],  # Changed close price!
        "volume": [Decimal("10.0")],
        "quote_volume": [Decimal("1000.0")],
        "trade_count": [50],
    }, schema=CANONICAL_ARROW_SCHEMA)

    report_conf, _ = validator.validate_table(tbl_conflict, existing_revisions_lookup=existing_lookup)
    assert report_conf.is_valid is False
    assert any(err.rule == "CONFLICTING_REVISION_AT_SAME_KNOWLEDGE_TIME" for err in report_conf.errors)


def test_storage_corrupted_parquet_raises_integrity_violation_error() -> None:
    """Audit P2: ParquetStorageEngine raises IntegrityViolationError on corrupt parquet rather than swallowing exceptions."""
    from acash.data.storage import ParquetStorageEngine
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ParquetStorageEngine(base_dir=Path(tmp_dir))
        part_dir = Path(tmp_dir) / "BTC-USDT" / "M1" / "year=2026"
        part_dir.mkdir(parents=True, exist_ok=True)

        # Write corrupt file
        corrupt_file = part_dir / "part-corrupt_001.parquet"
        corrupt_file.write_bytes(b"CORRUPT_GARBAGE_HEADER_NOT_A_PARQUET_FILE")

        with pytest.raises(IntegrityViolationError, match="Corrupted"):
            engine.get_existing_revisions_lookup([("binance", "BTC/USDT", "M1")])

        with pytest.raises(IntegrityViolationError, match="Corrupted"):
            engine.get_existing_event_max_seq([("binance", "BTC/USDT", "M1")])


