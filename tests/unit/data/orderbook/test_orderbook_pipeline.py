"""Unit tests for Order Book Ingestion Pipeline (Phase 3B)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import pyarrow as pa
import pytest

from acash.data.orderbook.pipeline import OrderBookIngestionPipeline
from acash.data.orderbook.schema import (
    CANONICAL_BOOK_DELTA_SCHEMA,
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
)
from acash.data.orderbook.storage import OrderBookStorageEngine
from acash.data.schema import IntegrityViolationError


def _make_multi_stream_snapshot_table() -> pa.Table:
    t = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    data = {
        "source_id": ["CME", "CME", "CME", "CME"],
        "channel_id": ["310", "310", "310", "310"],
        "symbol": ["ES.FUT", "ES.FUT", "NQ.FUT", "NQ.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19), date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [t, t, t, t],
        "feed_time_utc": [None, None, None, None],
        "knowledge_time_utc": [t + timedelta(seconds=1)] * 4,
        "source_seq_num": [100, 100, 200, 200],
        "source_order_key": ["00000000000000000100", "00000000000000000100", "00000000000000000200", "00000000000000000200"],
        "snapshot_id": ["snap_es_1", "snap_es_1", "snap_nq_1", "snap_nq_1"],
        "is_snapshot_complete": [True, True, True, True],
        "side": ["BID", "ASK", "BID", "ASK"],
        "level_idx": [0, 0, 0, 0],
        "price": [Decimal("5000.00"), Decimal("5000.50"), Decimal("18000.00"), Decimal("18000.50")],
        "size": [Decimal("10"), Decimal("15"), Decimal("20"), Decimal("25")],
        "order_count": [1, 1, 2, 2],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)


def _make_delta_table() -> pa.Table:
    t = datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)
    data = {
        "source_id": ["CME"],
        "channel_id": ["310"],
        "symbol": ["ES.FUT"],
        "trading_date": [date(2026, 1, 19)],
        "exchange_time_utc": [t],
        "feed_time_utc": [None],
        "knowledge_time_utc": [t + timedelta(seconds=1)],
        "source_seq_num": [101],
        "source_order_key": ["00000000000000000101"],
        "action_sub_idx": [0],
        "delta_type": ["MBP"],
        "action": ["MODIFY"],
        "side": ["BID"],
        "price": [Decimal("5000.00")],
        "size": [Decimal("50")],
        "order_id": [None],
        "level_idx": [0],
        "order_count": [3],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_DELTA_SCHEMA)


def test_orderbook_pipeline_ingestion_and_unit_splitting() -> None:
    """Verify end-to-end ingestion splits multi-symbol snapshot tables into distinct 1:1 units."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        engine = OrderBookStorageEngine(
            base_dir=tmp_path / "parquet",
            manifests_dir=tmp_path / "manifests",
            ledger_path=tmp_path / "ledger.jsonl",
            quarantine_dir=tmp_path / "quarantine",
        )
        pipeline = OrderBookIngestionPipeline(storage_engine=engine)

        raw_snap = _make_multi_stream_snapshot_table()
        res = pipeline.ingest_snapshots(
            raw_table=raw_snap,
            source_id="CME",
            source_uri="s3://cme/multisnap",
        )

        assert res.is_success
        assert len(res.batches_ingested) == 2  # ES.FUT and NQ.FUT
        assert res.total_rows == 4

        # Ingest Deltas
        raw_delta = _make_delta_table()
        res_delta = pipeline.ingest_deltas(
            raw_table=raw_delta,
            source_id="CME",
            source_uri="s3://cme/delta1",
        )
        assert res_delta.is_success
        assert len(res_delta.batches_ingested) == 1
        assert res_delta.total_rows == 1


def test_orderbook_pipeline_global_duplicate_rejection() -> None:
    """Verify that attempting to ingest an overlapping batch with duplicate row identities is rejected."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        engine = OrderBookStorageEngine(
            base_dir=tmp_path / "parquet",
            manifests_dir=tmp_path / "manifests",
            ledger_path=tmp_path / "ledger.jsonl",
            quarantine_dir=tmp_path / "quarantine",
        )
        pipeline = OrderBookIngestionPipeline(storage_engine=engine)

        raw_delta = _make_delta_table()
        # Ingest batch 1
        pipeline.ingest_deltas(
            raw_table=raw_delta,
            source_id="CME",
            source_uri="s3://cme/delta1",
            batch_id="batch_delta_1",
        )

        # Ingest batch 2 with different batch_id but containing duplicate Delta Row Identity
        with pytest.raises(IntegrityViolationError, match="GLOBAL_DELTA_IDENTITY_DUPLICATE"):
            pipeline.ingest_deltas(
                raw_table=raw_delta,
                source_id="CME",
                source_uri="s3://cme/delta2",
                batch_id="batch_delta_2",
            )
