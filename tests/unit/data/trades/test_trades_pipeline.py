"""Unit and integration tests for the Trades Ingestion Pipeline (Phase 3A)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import pyarrow as pa
import pytest

from acash.data.schema import (
    BatchCollisionError,
    IntegrityViolationError,
)
from acash.data.trades.pipeline import TradesIngestionPipeline
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA
from acash.data.trades.storage import TradesStorageEngine


def _make_test_trades_table(
    symbol: str = "ES.FUT",
    trading_date_val: date = date(2026, 1, 19),
    seq_start: int = 500,
    num_rows: int = 4,
) -> pa.Table:
    """Helper to generate a clean trades table for pipeline tests."""
    base_time = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    data = {
        "source_id": ["CME"] * num_rows,
        "channel_id": ["310"] * num_rows,
        "symbol": [symbol] * num_rows,
        "trading_date": [trading_date_val] * num_rows,
        "exchange_time_utc": [base_time + timedelta(milliseconds=i * 10) for i in range(num_rows)],
        "feed_time_utc": [base_time + timedelta(milliseconds=i * 10 + 2) for i in range(num_rows)],
        "knowledge_time_utc": [base_time + timedelta(seconds=1) for _ in range(num_rows)],
        "source_seq_num": [seq_start + i for i in range(num_rows)],
        "trade_id": [f"TRD_{seq_start + i}" for i in range(num_rows)],
        "match_sub_idx": [0] * num_rows,
        "price": [Decimal(f"5000.{10 + i:02d}0000000000000000") for i in range(num_rows)],
        "size": [Decimal(f"{5 + i}.000000000000000000") for i in range(num_rows)],
        "aggressor_side": ["BUY" if i % 2 == 0 else "SELL" for i in range(num_rows)],
        "trade_condition": ["REGULAR"] * num_rows,
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)


def test_trades_pipeline_ingestion_and_idempotent_replay(tmp_path: Path) -> None:
    """Verify that trades ingestion pipeline commits batches and replaying is idempotent."""
    storage = TradesStorageEngine(
        base_dir=tmp_path / "parquet" / "trades",
        manifests_dir=tmp_path / "manifests",
        ledger_path=tmp_path / "provenance_ledger.jsonl",
        quarantine_dir=tmp_path / "quarantine",
    )
    pipeline = TradesIngestionPipeline(storage_engine=storage)

    tbl = _make_test_trades_table()

    # Ingest batch
    result1 = pipeline.ingest(
        raw_table=tbl,
        source_id="CME",
        source_uri="cme://md3/ch310",
    )
    assert result1.is_success
    assert len(result1.batches_ingested) == 1
    assert result1.total_rows == 4
    batch_summary1 = result1.batches_ingested[0]
    assert Path(batch_summary1.part_file_path).exists()

    # Replay exact same batch
    result2 = pipeline.ingest(
        raw_table=tbl,
        source_id="CME",
        source_uri="cme://md3/ch310",
    )
    assert result2.is_success
    assert len(result2.batches_ingested) == 1
    batch_summary2 = result2.batches_ingested[0]
    assert batch_summary1.batch_id == batch_summary2.batch_id
    assert batch_summary1.canonical_trades_sha256 == batch_summary2.canonical_trades_sha256
    assert batch_summary1.part_file_path == batch_summary2.part_file_path


def test_trades_batch_collision_on_same_batch_id(tmp_path: Path) -> None:
    """Verify that ingesting different trade data with an existing batch_id raises BatchCollisionError."""
    storage = TradesStorageEngine(
        base_dir=tmp_path / "parquet" / "trades",
        manifests_dir=tmp_path / "manifests",
        ledger_path=tmp_path / "provenance_ledger.jsonl",
        quarantine_dir=tmp_path / "quarantine",
    )
    pipeline = TradesIngestionPipeline(storage_engine=storage)

    tbl1 = _make_test_trades_table()
    fixed_batch_id = "batch_fixed_collision_test"

    pipeline.ingest(
        raw_table=tbl1,
        source_id="CME",
        source_uri="cme://md3/ch310",
        batch_id=fixed_batch_id,
    )

    # Ingest modified data with same batch_id
    data2 = tbl1.to_pydict()
    data2["price"][0] = Decimal("9999.00")
    tbl2 = pa.Table.from_pydict(data2, schema=CANONICAL_TRADES_SCHEMA)

    with pytest.raises(BatchCollisionError, match="Batch collision"):
        pipeline.ingest(
            raw_table=tbl2,
            source_id="CME",
            source_uri="cme://md3/ch310",
            batch_id=fixed_batch_id,
        )


def test_trades_global_duplicate_identity_rejected(tmp_path: Path) -> None:
    """Verify that ingesting an already-persisted Trade Row Identity in a new batch raises IntegrityViolationError."""
    storage = TradesStorageEngine(
        base_dir=tmp_path / "parquet" / "trades",
        manifests_dir=tmp_path / "manifests",
        ledger_path=tmp_path / "provenance_ledger.jsonl",
        quarantine_dir=tmp_path / "quarantine",
    )
    pipeline = TradesIngestionPipeline(storage_engine=storage)

    tbl1 = _make_test_trades_table(seq_start=100, num_rows=2)
    pipeline.ingest(
        raw_table=tbl1,
        source_id="CME",
        source_uri="cme://md3/ch310",
        batch_id="batch_initial",
    )

    # New batch with overlapping Trade Row Identity (same channel, seq 100, match_sub_idx 0)
    tbl2 = _make_test_trades_table(seq_start=100, num_rows=1)
    with pytest.raises(IntegrityViolationError, match="GLOBAL_TRADE_IDENTITY_DUPLICATE"):
        pipeline.ingest(
            raw_table=tbl2,
            source_id="CME",
            source_uri="cme://md3/ch310",
            batch_id="batch_secondary_duplicate",
        )


def test_multi_unit_table_batch_splitting(tmp_path: Path) -> None:
    """Verify that a table containing multiple (symbol, trading_date) is split into distinct 1:1 Ingestion Units."""
    storage = TradesStorageEngine(
        base_dir=tmp_path / "parquet" / "trades",
        manifests_dir=tmp_path / "manifests",
        ledger_path=tmp_path / "provenance_ledger.jsonl",
        quarantine_dir=tmp_path / "quarantine",
    )
    pipeline = TradesIngestionPipeline(storage_engine=storage)

    base_time = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    # 2 rows for ES on 2026-01-19, 2 rows for NQ on 2026-01-19
    data = {
        "source_id": ["CME", "CME", "CME", "CME"],
        "channel_id": ["310", "310", "311", "311"],
        "symbol": ["ES.FUT", "ES.FUT", "NQ.FUT", "NQ.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19), date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [base_time, base_time, base_time, base_time],
        "feed_time_utc": [None, None, None, None],
        "knowledge_time_utc": [base_time + timedelta(seconds=1)] * 4,
        "source_seq_num": [10, 11, 20, 21],
        "trade_id": [None, None, None, None],
        "match_sub_idx": [0, 0, 0, 0],
        "price": [Decimal("5000.25"), Decimal("5000.50"), Decimal("18000.25"), Decimal("18000.50")],
        "size": [Decimal("10"), Decimal("5"), Decimal("2"), Decimal("3")],
        "aggressor_side": ["BUY", "SELL", "BUY", "SELL"],
        "trade_condition": ["REGULAR", "REGULAR", "REGULAR", "REGULAR"],
    }
    multi_table = pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)

    result = pipeline.ingest(
        raw_table=multi_table,
        source_id="CME",
        source_uri="cme://md3/multi",
    )

    assert result.is_success
    assert len(result.batches_ingested) == 2  # 1 batch for ES, 1 batch for NQ
    assert result.total_rows == 4
    symbols_ingested = {b.symbol for b in result.batches_ingested}
    assert symbols_ingested == {"ES.FUT", "NQ.FUT"}
