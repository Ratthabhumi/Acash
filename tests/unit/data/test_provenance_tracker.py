"""Tests for ProvenanceTracker and logical canonical hash determinism."""

import io
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from acash.data.provenance import (
    BatchLifecycleStatus,
    BatchManifest,
    ProvenanceRecord,
    ProvenanceTracker,
    calculate_canonical_batch_sha256,
    calculate_canonical_content_fingerprint,
    calculate_raw_source_sha256,
)
from acash.data.schema import BatchCollisionError, CANONICAL_ARROW_SCHEMA


def make_test_table_multiple_rows() -> pa.Table:
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)

    pydict = {
        "source_id": ["binance", "binance"],
        "symbol": ["BTC/USDT", "BTC/USDT"],
        "timeframe": ["M1", "M1"],
        "event_start_utc": [t0, t1],
        "event_end_utc": [t1, t2],
        "knowledge_time_utc": [t1, t2],
        "revision_seq": [1, 1],
        "open": [Decimal("100.00"), Decimal("102.00")],
        "high": [Decimal("105.00"), Decimal("106.00")],
        "low": [Decimal("95.00"), Decimal("101.00")],
        "close": [Decimal("102.00"), Decimal("104.00")],
        "volume": [Decimal("10.0"), Decimal("15.0")],
        "quote_volume": [Decimal("1010.0"), Decimal("1545.0")],
        "trade_count": [50, 75],
    }
    return pa.Table.from_pydict(pydict, schema=CANONICAL_ARROW_SCHEMA)


class TestProvenanceTracker:
    """Test suite for logical hashing, manifests, and audit ledger."""

    @pytest.fixture
    def tracker(self, tmp_path: Path) -> ProvenanceTracker:
        return ProvenanceTracker(
            ledger_path=tmp_path / "provenance_ledger.jsonl",
            manifests_dir=tmp_path / "manifests",
        )

    def test_raw_source_sha256(self) -> None:
        payload = b"timestamp,open,high,low,close,volume\n2026-01-01,100,105,95,102,10\n"
        h = calculate_raw_source_sha256(payload)
        assert len(h) == 64
        assert h == calculate_raw_source_sha256(payload)

    def test_canonical_batch_sha256_row_order_invariance(self) -> None:
        table_forward = make_test_table_multiple_rows()
        # Permute rows
        table_reversed = table_forward.take([1, 0])

        hash_forward = calculate_canonical_batch_sha256(table_forward)
        hash_reversed = calculate_canonical_batch_sha256(table_reversed)

        assert hash_forward == hash_reversed, "Logical hash must be strictly row-order invariant"

    def test_canonical_batch_sha256_physical_layout_invariance(self) -> None:
        table = make_test_table_multiple_rows()
        original_hash = calculate_canonical_batch_sha256(table)

        # Write with snappy compression
        buf_snappy = io.BytesIO()
        pq.write_table(table, buf_snappy, compression="snappy")
        buf_snappy.seek(0)
        table_from_snappy = pq.read_table(buf_snappy)

        # Write with zstd compression
        buf_zstd = io.BytesIO()
        pq.write_table(table, buf_zstd, compression="zstd")
        buf_zstd.seek(0)
        table_from_zstd = pq.read_table(buf_zstd)

        assert calculate_canonical_batch_sha256(table_from_snappy) == original_hash
        assert calculate_canonical_batch_sha256(table_from_zstd) == original_hash

    def test_canonical_batch_sha256_detects_data_modifications(self) -> None:
        table = make_test_table_multiple_rows()
        original_hash = calculate_canonical_batch_sha256(table)

        # Modify close price in second row
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)
        pydict_mod = {
            "source_id": ["binance", "binance"],
            "symbol": ["BTC/USDT", "BTC/USDT"],
            "timeframe": ["M1", "M1"],
            "event_start_utc": [t0, t1],
            "event_end_utc": [t1, t2],
            "knowledge_time_utc": [t1, t2],
            "revision_seq": [1, 1],
            "open": [Decimal("100.00"), Decimal("102.00")],
            "high": [Decimal("105.00"), Decimal("106.00")],
            "low": [Decimal("95.00"), Decimal("101.00")],
            "close": [Decimal("102.00"), Decimal("104.01")],  # 104.01 instead of 104.00
            "volume": [Decimal("10.0"), Decimal("15.0")],
            "quote_volume": [Decimal("1010.0"), Decimal("1545.0")],
            "trade_count": [50, 75],
        }
        mod_table = pa.Table.from_pydict(pydict_mod, schema=CANONICAL_ARROW_SCHEMA)
        mod_hash = calculate_canonical_batch_sha256(mod_table)

        assert mod_hash != original_hash

    def test_canonical_batch_sha256_fails_on_missing_columns(self) -> None:
        """Fail-fast: Hashing fails explicitly if required canonical schema columns are missing."""
        from acash.data.schema import DataContractError
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        incomplete_dict = {
            "source_id": ["binance"],
            "symbol": ["BTC/USDT"],
            "event_start_utc": [t0],
            "event_end_utc": [t1],
            "close": [Decimal("100.00")],
            # Missing open, high, low, volume, timeframe, revision_seq, etc.
        }
        incomplete_table = pa.Table.from_pydict(incomplete_dict)

        with pytest.raises(DataContractError) as excinfo:
            calculate_canonical_batch_sha256(incomplete_table)

        assert "missing required canonical columns" in str(excinfo.value)


    def test_manifest_lifecycle_and_updates(self, tracker: ProvenanceTracker) -> None:
        batch_id = "batch_test_manifest_001"
        manifest = BatchManifest(
            batch_id=batch_id,
            status=BatchLifecycleStatus.PREPARED,
            source_id="binance",
            source_uri_or_path="mock://path",
            raw_source_sha256="a" * 64,
            canonical_batch_sha256="b" * 64,
            schema_version="1.16.0",
            transform_version="v1",
            symbol="BTC/USDT",
            timeframe="M1",
            year_partition=2026,
            part_file_path="data/parquet/BTC-USDT/M1/year=2026/part-batch_test_manifest_001.parquet",
            row_count=10,
            min_event_time_utc="2026-01-01T10:00:00.000000Z",
            max_event_time_utc="2026-01-01T10:10:00.000000Z",
            created_at_utc="2026-01-01T10:15:00.000000Z",
            updated_at_utc="2026-01-01T10:15:00.000000Z",
        )

        saved_path = tracker.save_manifest(manifest)
        assert saved_path.exists()

        loaded = tracker.load_manifest(batch_id)
        assert loaded is not None
        assert loaded.status == BatchLifecycleStatus.PREPARED

        # Transition to PART_PUBLISHED
        tracker.update_manifest_status(batch_id, BatchLifecycleStatus.PART_PUBLISHED)
        updated_1 = tracker.load_manifest(batch_id)
        assert updated_1 is not None
        assert updated_1.status == BatchLifecycleStatus.PART_PUBLISHED

        # Transition to COMMITTED
        tracker.update_manifest_status(batch_id, BatchLifecycleStatus.COMMITTED)
        updated_2 = tracker.load_manifest(batch_id)
        assert updated_2 is not None
        assert updated_2.status == BatchLifecycleStatus.COMMITTED

    def test_provenance_ledger_idempotency_and_collision(self, tracker: ProvenanceTracker) -> None:
        rec1 = ProvenanceRecord(
            provenance_id="prov_001",
            batch_id="batch_001",
            source_id="binance",
            source_uri_or_path="mock://path",
            part_file_path="part.parquet",
            ingest_time_utc="2026-01-01T10:00:00.000000Z",
            raw_source_sha256="a" * 64,
            canonical_batch_sha256="b" * 64,
            schema_version="1.16.0",
            transform_version="v1",
            symbol="BTC/USDT",
            timeframe="M1",
            row_count=5,
            min_event_time_utc="2026-01-01T10:00:00.000000Z",
            max_event_time_utc="2026-01-01T10:05:00.000000Z",
            validation_status="VALID",
        )

        # First append
        tracker.append_provenance_record(rec1)
        records = tracker.read_provenance_records()
        assert len(records) == 1

        # Second append (identical) -> Idempotent
        tracker.append_provenance_record(rec1)
        records_after = tracker.read_provenance_records()
        assert len(records_after) == 1

        # Third append with same batch_id but different hash -> Collision Error
        rec1_collision = ProvenanceRecord(
            provenance_id="prov_001",
            batch_id="batch_001",
            source_id="binance",
            source_uri_or_path="mock://path",
            part_file_path="part.parquet",
            ingest_time_utc="2026-01-01T10:00:00.000000Z",
            raw_source_sha256="a" * 64,
            canonical_batch_sha256="c" * 64,
            schema_version="1.16.0",
            transform_version="v1",
            symbol="BTC/USDT",
            timeframe="M1",
            row_count=5,
            min_event_time_utc="2026-01-01T10:00:00.000000Z",
            max_event_time_utc="2026-01-01T10:05:00.000000Z",
            validation_status="VALID",
        )
        with pytest.raises(BatchCollisionError):
            tracker.append_provenance_record(rec1_collision)

