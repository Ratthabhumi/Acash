"""End-to-end integration tests for IngestionPipeline."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pandas as pd
import pytest

from acash.data.pipeline import IngestionPipeline
from acash.data.schema import BatchCollisionError, IntegrityViolationError
from acash.data.sources.csv_source import CsvSourceAdapter
from acash.data.sources.synthetic import SyntheticSourceAdapter
from acash.data.storage import DuckDBStorage, ParquetStorageEngine


class TestIngestionPipeline:
    """Test suite for pipeline orchestration, multi-stream splitting, global duplicate rejection, and idempotency."""

    @pytest.fixture
    def test_dir(self, tmp_path: Path) -> Path:
        base = tmp_path / "acash_pipeline_data"
        base.mkdir()
        return base

    @pytest.fixture
    def pipeline(self, test_dir: Path) -> IngestionPipeline:
        storage = ParquetStorageEngine(
            base_dir=test_dir / "parquet",
            manifests_dir=test_dir / "manifests",
            ledger_path=test_dir / "provenance_ledger.jsonl",
            quarantine_dir=test_dir / "quarantine",
        )
        return IngestionPipeline(storage_engine=storage)

    @pytest.fixture
    def duckdb_storage(self, test_dir: Path) -> DuckDBStorage:
        return DuckDBStorage(base_dir=test_dir / "parquet")

    def test_synthetic_data_end_to_end_ingestion(
        self, pipeline: IngestionPipeline, duckdb_storage: DuckDBStorage
    ) -> None:
        synth_adapter = SyntheticSourceAdapter(
            source_id="synthetic_binance",
            symbol="BTC/USDT",
            timeframe="M1",
            bar_count=60,
            start_time_utc=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        )

        result = pipeline.ingest(
            source_path_or_uri="synthetic://btc_60m",
            adapter=synth_adapter,
        )

        assert result.is_successful
        assert len(result.ingested_batches) == 1
        assert len(result.committed_part_paths) == 1
        assert result.committed_part_paths[0].exists()

        # Query back via DuckDB
        table = duckdb_storage.query_point_in_time(
            symbol="BTC/USDT",
            timeframe="M1",
            as_of_knowledge_time_utc=datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc),
        )
        assert table.num_rows == 60

    def test_csv_multi_stream_splitting_into_1_to_1_units(
        self, pipeline: IngestionPipeline, tmp_path: Path, duckdb_storage: DuckDBStorage
    ) -> None:
        csv_file = tmp_path / "multi_stream.csv"
        df = pd.DataFrame([
            # Stream 1: BTC/USDT M1 2026
            {
                "source_id": "binance",
                "symbol": "BTC/USDT",
                "timeframe": "M1",
                "event_start_utc": "2026-01-01T10:00:00Z",
                "event_end_utc": "2026-01-01T10:01:00Z",
                "knowledge_time_utc": "2026-01-01T10:01:00Z",
                "revision_seq": 1,
                "open": "50000.0",
                "high": "50100.0",
                "low": "49900.0",
                "close": "50050.0",
                "volume": "1.0",
                "quote_volume": "50025.0",
                "trade_count": 25,
            },
            # Stream 2: ETH/USDT M1 2026
            {
                "source_id": "binance",
                "symbol": "ETH/USDT",
                "timeframe": "M1",
                "event_start_utc": "2026-01-01T10:00:00Z",
                "event_end_utc": "2026-01-01T10:01:00Z",
                "knowledge_time_utc": "2026-01-01T10:01:00Z",
                "revision_seq": 1,
                "open": "3000.0",
                "high": "3010.0",
                "low": "2990.0",
                "close": "3005.0",
                "volume": "10.0",
                "quote_volume": "30025.0",
                "trade_count": 30,
            },
        ])
        df.to_csv(csv_file, index=False)

        csv_adapter = CsvSourceAdapter()
        result = pipeline.ingest(source_path_or_uri=csv_file, adapter=csv_adapter)

        assert result.is_successful
        # Multi-stream split into 2 independent batches
        assert len(result.ingested_batches) == 2
        symbols_ingested = {b.symbol for b in result.ingested_batches}
        assert symbols_ingested == {"BTC/USDT", "ETH/USDT"}

        # Query BTC
        btc_tbl = duckdb_storage.query_point_in_time(
            symbol="BTC/USDT",
            timeframe="M1",
            as_of_knowledge_time_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert btc_tbl.num_rows == 1
        assert btc_tbl.to_pylist()[0]["close"] == Decimal("50050.0")

        # Query ETH
        eth_tbl = duckdb_storage.query_point_in_time(
            symbol="ETH/USDT",
            timeframe="M1",
            as_of_knowledge_time_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert eth_tbl.num_rows == 1
        assert eth_tbl.to_pylist()[0]["close"] == Decimal("3005.0")

    def test_pipeline_rejects_global_duplicate_revision_across_batches(
        self, pipeline: IngestionPipeline, tmp_path: Path
    ) -> None:
        """Integration test: Ingesting a revision identity already existing in storage must be rejected."""
        # Batch 1
        csv1 = tmp_path / "batch1.csv"
        df1 = pd.DataFrame([
            {
                "source_id": "binance",
                "symbol": "BTC/USDT",
                "timeframe": "M1",
                "event_start_utc": "2026-01-01T10:00:00Z",
                "event_end_utc": "2026-01-01T10:01:00Z",
                "knowledge_time_utc": "2026-01-01T10:05:00Z",
                "revision_seq": 1,
                "open": "50000.0",
                "high": "50100.0",
                "low": "49900.0",
                "close": "50050.0",
                "volume": "1.0",
                "quote_volume": "50025.0",
                "trade_count": 25,
            }
        ])
        df1.to_csv(csv1, index=False)

        csv_adapter = CsvSourceAdapter()
        res1 = pipeline.ingest(source_path_or_uri=csv1, adapter=csv_adapter, batch_id="batch_initial_001")
        assert res1.is_successful

        # Batch 2: Different batch ID and different file, but contains the EXACT SAME Revision Identity
        csv2 = tmp_path / "batch2.csv"
        df2 = pd.DataFrame([
            {
                "source_id": "binance",
                "symbol": "BTC/USDT",
                "timeframe": "M1",
                "event_start_utc": "2026-01-01T10:00:00Z",
                "event_end_utc": "2026-01-01T10:01:00Z",
                "knowledge_time_utc": "2026-01-01T10:05:00Z",
                "revision_seq": 1,  # Exact duplicate Revision Identity
                "open": "50000.0",
                "high": "50100.0",
                "low": "49900.0",
                "close": "50050.0",
                "volume": "1.0",
                "quote_volume": "50025.0",
                "trade_count": 25,
            }
        ])
        df2.to_csv(csv2, index=False)

        # Must reject with IntegrityViolationError
        with pytest.raises(IntegrityViolationError) as excinfo:
            pipeline.ingest(source_path_or_uri=csv2, adapter=csv_adapter, batch_id="batch_incoming_002")

        assert "GLOBAL_REVISION_IDENTITY_DUPLICATE" in str(excinfo.value)

    def test_pipeline_replay_idempotency_without_duplicate_parts(
        self, pipeline: IngestionPipeline, tmp_path: Path
    ) -> None:
        """Integration test: Replaying the same ingestion operation is idempotent and creates no second part."""
        csv_file = tmp_path / "replay_test.csv"
        df = pd.DataFrame([
            {
                "source_id": "binance",
                "symbol": "BTC/USDT",
                "timeframe": "M1",
                "event_start_utc": "2026-01-01T10:00:00Z",
                "event_end_utc": "2026-01-01T10:01:00Z",
                "knowledge_time_utc": "2026-01-01T10:01:00Z",
                "revision_seq": 1,
                "open": "50000.0",
                "high": "50100.0",
                "low": "49900.0",
                "close": "50050.0",
                "volume": "1.0",
                "quote_volume": "50025.0",
                "trade_count": 25,
            }
        ])
        df.to_csv(csv_file, index=False)

        csv_adapter = CsvSourceAdapter()

        # First ingestion
        res1 = pipeline.ingest(source_path_or_uri=csv_file, adapter=csv_adapter)
        assert res1.is_successful
        assert len(res1.committed_part_paths) == 1
        part_1 = res1.committed_part_paths[0]

        # Check total parquet parts on disk
        parquet_parts = list(pipeline.storage_engine.base_dir.glob("**/*.parquet"))
        assert len(parquet_parts) == 1

        # Check provenance ledger records
        prov_records_1 = pipeline.storage_engine.provenance_tracker.read_provenance_records()
        assert len(prov_records_1) == 1

        # Replay exact same ingestion
        res2 = pipeline.ingest(source_path_or_uri=csv_file, adapter=csv_adapter)
        assert res2.is_successful
        assert res2.committed_part_paths[0] == part_1

        # Verify NO second part or second provenance record created
        parquet_parts_after = list(pipeline.storage_engine.base_dir.glob("**/*.parquet"))
        assert len(parquet_parts_after) == 1

        prov_records_2 = pipeline.storage_engine.provenance_tracker.read_provenance_records()
        assert len(prov_records_2) == 1

    def test_pipeline_batch_collision_on_same_batch_id(
        self, pipeline: IngestionPipeline, tmp_path: Path
    ) -> None:
        """Integration test: Passing same batch_id with different content raises BatchCollisionError."""
        csv1 = tmp_path / "collision1.csv"
        pd.DataFrame([{
            "source_id": "binance", "symbol": "BTC/USDT", "timeframe": "M1",
            "event_start_utc": "2026-01-01T10:00:00Z", "event_end_utc": "2026-01-01T10:01:00Z",
            "knowledge_time_utc": "2026-01-01T10:01:00Z", "revision_seq": 1,
            "open": "50000.0", "high": "50100.0", "low": "49900.0", "close": "50050.0",
            "volume": "1.0", "quote_volume": "50025.0", "trade_count": 25,
        }]).to_csv(csv1, index=False)

        csv2 = tmp_path / "collision2.csv"
        pd.DataFrame([{
            "source_id": "binance", "symbol": "BTC/USDT", "timeframe": "M1",
            "event_start_utc": "2026-01-01T10:00:00Z", "event_end_utc": "2026-01-01T10:01:00Z",
            "knowledge_time_utc": "2026-01-01T10:01:00Z", "revision_seq": 1,
            "open": "60000.0", "high": "60100.0", "low": "59900.0", "close": "60050.0",
            "volume": "1.0", "quote_volume": "60025.0", "trade_count": 25,
        }]).to_csv(csv2, index=False)

        csv_adapter = CsvSourceAdapter()
        res1 = pipeline.ingest(source_path_or_uri=csv1, adapter=csv_adapter, batch_id="batch_collision_test")
        assert res1.is_successful

        with pytest.raises(BatchCollisionError):
            # Batch 2 with same batch_id but different data will raise BatchCollisionError
            pipeline.ingest(source_path_or_uri=csv2, adapter=csv_adapter, batch_id="batch_collision_test")


    def test_pipeline_aborts_on_invalid_data(
        self, pipeline: IngestionPipeline, tmp_path: Path
    ) -> None:
        csv_file = tmp_path / "invalid.csv"
        df = pd.DataFrame([
            {
                "source_id": "binance",
                "symbol": "BTC/USDT",
                "timeframe": "M1",
                "event_start_utc": "2026-01-01T10:00:00Z",
                "event_end_utc": "2026-01-01T10:01:00Z",
                "knowledge_time_utc": "2026-01-01T10:01:00Z",
                "revision_seq": 1,
                "open": "-100.0",  # Negative price -> INVALID
                "high": "105.0",
                "low": "95.0",
                "close": "100.0",
                "volume": "1.0",
                "quote_volume": "100.0",
                "trade_count": 5,
            }
        ])
        df.to_csv(csv_file, index=False)

        csv_adapter = CsvSourceAdapter()
        with pytest.raises(IntegrityViolationError):
            pipeline.ingest(source_path_or_uri=csv_file, adapter=csv_adapter, abort_on_validation_error=True)
