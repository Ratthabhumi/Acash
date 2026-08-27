"""Tests for ParquetStorageEngine and DuckDB Point-in-Time qualification layer."""

import os
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from acash.data.provenance import (
    BatchLifecycleStatus,
    BatchManifest,
    ProvenanceRecord,
    calculate_canonical_batch_sha256,
)
from acash.data.schema import (
    BatchCollisionError,
    CANONICAL_ARROW_SCHEMA,
)
from acash.data.storage import DuckDBStorage, ParquetStorageEngine


def make_sample_table(
    source_id: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "M1",
    event_start: datetime = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
    event_end: datetime = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc),
    knowledge_time: datetime = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc),
    revision_seq: int = 1,
    close_price: Decimal = Decimal("100.00"),
) -> pa.Table:
    pydict = {
        "source_id": [source_id],
        "symbol": [symbol],
        "timeframe": [timeframe],
        "event_start_utc": [event_start],
        "event_end_utc": [event_end],
        "knowledge_time_utc": [knowledge_time],
        "revision_seq": [revision_seq],
        "open": [close_price],
        "high": [close_price + Decimal("5.0")],
        "low": [close_price - Decimal("5.0")],
        "close": [close_price],
        "volume": [Decimal("10.0")],
        "quote_volume": [Decimal("1000.0")],
        "trade_count": [50],
    }
    return pa.Table.from_pydict(pydict, schema=CANONICAL_ARROW_SCHEMA)


class TestStorageAndPointInTime:
    """Test suite for storage engine, crash recovery, and PIT queries."""

    @pytest.fixture
    def test_dir(self, tmp_path: Path) -> Path:
        base = tmp_path / "acash_data"
        base.mkdir()
        return base

    @pytest.fixture
    def engine(self, test_dir: Path) -> ParquetStorageEngine:
        return ParquetStorageEngine(
            base_dir=test_dir / "parquet",
            manifests_dir=test_dir / "manifests",
            ledger_path=test_dir / "provenance_ledger.jsonl",
            quarantine_dir=test_dir / "quarantine",
        )

    @pytest.fixture
    def duckdb_storage(self, test_dir: Path) -> DuckDBStorage:
        return DuckDBStorage(base_dir=test_dir / "parquet")

    def test_strict_1_to_1_batch_commit_and_idempotency(self, engine: ParquetStorageEngine) -> None:
        table = make_sample_table()
        batch_id = "batch_unit_001"

        # First write
        part_path = engine.write_canonical_part(
            table=table,
            batch_id=batch_id,
            source_id="binance",
            source_uri_or_path="mock://raw",
            raw_source_sha256="raw_hash_001",
        )
        assert part_path.exists()
        assert "part-batch_unit_001.parquet" in part_path.name

        # Manifest status must be COMMITTED
        manifest = engine.provenance_tracker.load_manifest(batch_id)
        assert manifest is not None
        assert manifest.status == BatchLifecycleStatus.COMMITTED

        # Provenance ledger has exactly 1 record
        records = engine.provenance_tracker.read_provenance_records()
        assert len(records) == 1
        assert records[0].batch_id == batch_id

        # Second write with same content is idempotent
        part_path_2 = engine.write_canonical_part(
            table=table,
            batch_id=batch_id,
            source_id="binance",
            source_uri_or_path="mock://raw",
            raw_source_sha256="raw_hash_001",
        )
        assert part_path_2 == part_path
        # No duplicate records
        records_after = engine.provenance_tracker.read_provenance_records()
        assert len(records_after) == 1

    def test_batch_collision_raises_error(self, engine: ParquetStorageEngine) -> None:
        table1 = make_sample_table(close_price=Decimal("100.00"))
        table2 = make_sample_table(close_price=Decimal("200.00"))
        batch_id = "batch_collision_001"

        engine.write_canonical_part(
            table=table1,
            batch_id=batch_id,
            source_id="binance",
            source_uri_or_path="mock://raw",
            raw_source_sha256="raw_hash_001",
        )

        with pytest.raises(BatchCollisionError):
            engine.write_canonical_part(
                table=table2,
                batch_id=batch_id,
                source_id="binance",
                source_uri_or_path="mock://raw",
                raw_source_sha256="raw_hash_001",
            )

    def test_crash_recovery_part_published_missing_provenance(self, engine: ParquetStorageEngine) -> None:
        table = make_sample_table()
        batch_id = "batch_crash_001"
        c_hash = calculate_canonical_batch_sha256(table)

        part_path = engine.get_part_file_path("BTC/USDT", "M1", 2026, batch_id)
        part_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, part_path)

        # Simulate manifest in PART_PUBLISHED state
        manifest = BatchManifest(
            batch_id=batch_id,
            status=BatchLifecycleStatus.PART_PUBLISHED,
            source_id="binance",
            source_uri_or_path="mock://raw",
            raw_source_sha256="raw_hash",
            canonical_batch_sha256=c_hash,
            schema_version="1.16.0",
            transform_version="v1",
            symbol="BTC/USDT",
            timeframe="M1",
            year_partition=2026,
            part_file_path=str(part_path).replace("\\", "/"),
            row_count=1,
            min_event_time_utc="2026-01-01T10:00:00.000000Z",
            max_event_time_utc="2026-01-01T10:01:00.000000Z",
            created_at_utc="2026-01-01T10:05:00.000000Z",
            updated_at_utc="2026-01-01T10:05:00.000000Z",
        )
        engine.provenance_tracker.save_manifest(manifest)

        # Ensure provenance ledger is empty
        assert len(engine.provenance_tracker.read_provenance_records()) == 0

        # Run recovery pass
        recovery_results = engine.run_crash_recovery_pass()
        assert recovery_results[batch_id] == "RECOVERED_COMMITTED"

        # Manifest must now be COMMITTED
        updated_manifest = engine.provenance_tracker.load_manifest(batch_id)
        assert updated_manifest is not None
        assert updated_manifest.status == BatchLifecycleStatus.COMMITTED

        # Provenance ledger must now have the record
        records = engine.provenance_tracker.read_provenance_records()
        assert len(records) == 1
        assert records[0].batch_id == batch_id
        assert records[0].canonical_batch_sha256 == c_hash

    def test_crash_recovery_after_provenance_append_before_committed(self, engine: ParquetStorageEngine) -> None:
        table = make_sample_table()
        batch_id = "batch_crash_post_prov"
        c_hash = calculate_canonical_batch_sha256(table)

        part_path = engine.get_part_file_path("BTC/USDT", "M1", 2026, batch_id)
        part_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, part_path)

        # Manifest is PART_PUBLISHED
        manifest = BatchManifest(
            batch_id=batch_id,
            status=BatchLifecycleStatus.PART_PUBLISHED,
            source_id="binance",
            source_uri_or_path="mock://raw",
            raw_source_sha256="raw_hash",
            canonical_batch_sha256=c_hash,
            schema_version="1.16.0",
            transform_version="v1",
            symbol="BTC/USDT",
            timeframe="M1",
            year_partition=2026,
            part_file_path=str(part_path).replace("\\", "/"),
            row_count=1,
            min_event_time_utc="2026-01-01T10:00:00.000000Z",
            max_event_time_utc="2026-01-01T10:01:00.000000Z",
            created_at_utc="2026-01-01T10:05:00.000000Z",
            updated_at_utc="2026-01-01T10:05:00.000000Z",
        )
        engine.provenance_tracker.save_manifest(manifest)

        # Provenance record already appended
        prov = ProvenanceRecord(
            provenance_id=f"prov_{batch_id}",
            batch_id=batch_id,
            source_id="binance",
            source_uri_or_path="mock://raw",
            part_file_path=str(part_path).replace("\\", "/"),
            ingest_time_utc="2026-01-01T10:05:00.000000Z",
            raw_source_sha256="raw_hash",
            canonical_batch_sha256=c_hash,
            schema_version="1.16.0",
            transform_version="v1",
            symbol="BTC/USDT",
            timeframe="M1",
            row_count=1,
            min_event_time_utc="2026-01-01T10:00:00.000000Z",
            max_event_time_utc="2026-01-01T10:01:00.000000Z",
            validation_status="VALID",
        )
        engine.provenance_tracker.append_provenance_record(prov)

        # Run recovery
        engine.run_crash_recovery_pass()

        # Must mark COMMITTED and not duplicate provenance
        updated_manifest = engine.provenance_tracker.load_manifest(batch_id)
        assert updated_manifest is not None
        assert updated_manifest.status == BatchLifecycleStatus.COMMITTED
        assert len(engine.provenance_tracker.read_provenance_records()) == 1

    def test_orphan_part_is_quarantined_without_guessing(self, engine: ParquetStorageEngine) -> None:
        orphan_path = engine.base_dir / "BTC-USDT" / "M1" / "year=2026" / "part-orphan_batch_999.parquet"
        orphan_path.parent.mkdir(parents=True, exist_ok=True)
        table = make_sample_table()
        pq.write_table(table, orphan_path)

        results = engine.run_crash_recovery_pass()
        assert results["orphan_batch_999"] == "ORPHAN_QUARANTINED"
        assert not orphan_path.exists()
        assert (engine.quarantine_dir / "part-orphan_batch_999.parquet").exists()

    def test_cross_part_point_in_time_with_historical_backfill(
        self, engine: ParquetStorageEngine, duckdb_storage: DuckDBStorage
    ) -> None:
        """Verify DuckDB PIT query across parts including historical backfill."""
        t_event_start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t_event_end = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        # Part 1: Initial observation at 12:00 UTC (Close = 100, seq = 1)
        t_know_1 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        table1 = make_sample_table(
            event_start=t_event_start,
            event_end=t_event_end,
            knowledge_time=t_know_1,
            revision_seq=1,
            close_price=Decimal("100.00"),
        )
        engine.write_canonical_part(
            table=table1,
            batch_id="batch_part_001",
            source_id="binance",
            source_uri_or_path="mock://part1",
            raw_source_sha256="raw1",
        )

        # Part 2: Historical backfill arriving later with knowledge_time = 11:00 UTC (Close = 105, seq = 2)
        t_know_2 = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)
        table2 = make_sample_table(
            event_start=t_event_start,
            event_end=t_event_end,
            knowledge_time=t_know_2,
            revision_seq=2,
            close_price=Decimal("105.00"),
        )
        engine.write_canonical_part(
            table=table2,
            batch_id="batch_part_002_backfill",
            source_id="binance",
            source_uri_or_path="mock://part2",
            raw_source_sha256="raw2",
        )

        # Query 1: As of 10:30 UTC -> Nothing known yet
        res_1030 = duckdb_storage.query_point_in_time(
            symbol="BTC/USDT",
            timeframe="M1",
            as_of_knowledge_time_utc=datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc),
        )
        assert res_1030.num_rows == 0

        # Query 2: As of 11:30 UTC -> Sees Part 2 revision (Close = 105.00, seq = 2)
        res_1130 = duckdb_storage.query_point_in_time(
            symbol="BTC/USDT",
            timeframe="M1",
            as_of_knowledge_time_utc=datetime(2026, 1, 1, 11, 30, tzinfo=timezone.utc),
        )
        assert res_1130.num_rows == 1
        row_1130 = res_1130.to_pylist()[0]
        assert row_1130["close"] == Decimal("105.00")
        assert row_1130["revision_seq"] == 2

        # Query 3: As of 13:00 UTC -> Sees Part 1 revision (Close = 100.00, seq = 1, latest knowledge = 12:00)
        res_1300 = duckdb_storage.query_point_in_time(
            symbol="BTC/USDT",
            timeframe="M1",
            as_of_knowledge_time_utc=datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc),
        )
        assert res_1300.num_rows == 1
        row_1300 = res_1300.to_pylist()[0]
        assert row_1300["close"] == Decimal("100.00")
        assert row_1300["revision_seq"] == 1

    def test_multi_source_pit_independent_observations(
        self, engine: ParquetStorageEngine, duckdb_storage: DuckDBStorage
    ) -> None:
        """Verify PIT query returns separate authoritative records for different sources without merging."""
        t_event_start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t_event_end = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t_know = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc)

        # Source A
        table_a = make_sample_table(
            source_id="binance",
            close_price=Decimal("100.00"),
            event_start=t_event_start,
            event_end=t_event_end,
            knowledge_time=t_know,
        )
        engine.write_canonical_part(
            table=table_a,
            batch_id="batch_source_a",
            source_id="binance",
            source_uri_or_path="mock://a",
            raw_source_sha256="raw_a",
        )

        # Source B
        table_b = make_sample_table(
            source_id="dukascopy",
            close_price=Decimal("101.00"),
            event_start=t_event_start,
            event_end=t_event_end,
            knowledge_time=t_know,
        )
        engine.write_canonical_part(
            table=table_b,
            batch_id="batch_source_b",
            source_id="dukascopy",
            source_uri_or_path="mock://b",
            raw_source_sha256="raw_b",
        )

        # Query PIT as of 11:00 UTC
        res = duckdb_storage.query_point_in_time(
            symbol="BTC/USDT",
            timeframe="M1",
            as_of_knowledge_time_utc=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
        )
        assert res.num_rows == 2
        rows = res.to_pylist()
        source_map = {r["source_id"]: r["close"] for r in rows}
        assert source_map["binance"] == Decimal("100.00")
        assert source_map["dukascopy"] == Decimal("101.00")
