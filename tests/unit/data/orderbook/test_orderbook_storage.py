"""Unit tests for Order Book Parquet Storage Engine and DuckDB PIT Query Engine (Phase 3B)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import pyarrow as pa
import pytest

from acash.data.orderbook.schema import (
    CANONICAL_BOOK_DELTA_SCHEMA,
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
)
from acash.data.orderbook.storage import OrderBookStorageEngine
from acash.data.schema import BatchCollisionError


def _make_snapshot_batch(batch_key: str, snap_id: str, is_complete: bool = True) -> pa.Table:
    t = datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc)
    data = {
        "source_id": ["CME", "CME"],
        "channel_id": ["310", "310"],
        "symbol": ["ES.FUT", "ES.FUT"],
        "trading_date": [date(2026, 1, 19), date(2026, 1, 19)],
        "exchange_time_utc": [t, t],
        "feed_time_utc": [None, None],
        "knowledge_time_utc": [t + timedelta(seconds=1), t + timedelta(seconds=1)],
        "source_seq_num": [1000, 1000],
        "source_order_key": [f"KEY_{batch_key}", f"KEY_{batch_key}"],
        "snapshot_id": [snap_id, snap_id],
        "is_snapshot_complete": [is_complete, is_complete],
        "side": ["BID", "ASK"],
        "level_idx": [0, 0],
        "price": [Decimal("5000.00"), Decimal("5000.50")],
        "size": [Decimal("10"), Decimal("15")],
        "order_count": [2, 3],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)


def _make_delta_batch(delta_key: str, exchange_time: datetime, knowledge_time: datetime) -> pa.Table:
    data = {
        "source_id": ["CME"],
        "channel_id": ["310"],
        "symbol": ["ES.FUT"],
        "trading_date": [date(2026, 1, 19)],
        "exchange_time_utc": [exchange_time],
        "feed_time_utc": [None],
        "knowledge_time_utc": [knowledge_time],
        "source_seq_num": [1001],
        "source_order_key": [delta_key],
        "action_sub_idx": [0],
        "delta_type": ["MBP"],
        "action": ["MODIFY"],
        "side": ["BID"],
        "price": [Decimal("5000.00")],
        "size": [Decimal("35")],
        "order_id": [None],
        "level_idx": [0],
        "order_count": [5],
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_BOOK_DELTA_SCHEMA)


def test_orderbook_storage_commit_and_idempotency() -> None:
    """Verify Recoverable Batch Commit protocol and replay idempotency."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        engine = OrderBookStorageEngine(
            base_dir=tmp_path / "parquet",
            manifests_dir=tmp_path / "manifests",
            ledger_path=tmp_path / "ledger.jsonl",
            quarantine_dir=tmp_path / "quarantine",
        )

        snap_tbl = _make_snapshot_batch("001", "snap_001")
        p1 = engine.commit_snapshot_batch(
            batch_id="batch_snap_001",
            table=snap_tbl,
            source_id="CME",
            source_uri="s3://cme/snap1",
            raw_source_sha256="a" * 64,
        )
        assert p1.exists()

        # Replay identical batch -> returns existing path
        p2 = engine.commit_snapshot_batch(
            batch_id="batch_snap_001",
            table=snap_tbl,
            source_id="CME",
            source_uri="s3://cme/snap1",
            raw_source_sha256="a" * 64,
        )
        assert p1 == p2

        # Replay modified batch under same batch_id -> raises BatchCollisionError
        snap_mod = snap_tbl.to_pydict()
        snap_mod["size"][0] = Decimal("99")
        tbl_mod = pa.Table.from_pydict(snap_mod, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

        with pytest.raises(BatchCollisionError):
            engine.commit_snapshot_batch(
                batch_id="batch_snap_001",
                table=tbl_mod,
                source_id="CME",
                source_uri="s3://cme/snap1",
                raw_source_sha256="a" * 64,
            )


def test_duckdb_two_stage_multi_row_pit_query_and_reconstruction() -> None:
    """Verify DuckDB Stage 1 & Stage 2 queries and end-to-end zero lookahead PIT reconstruction."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        engine = OrderBookStorageEngine(
            base_dir=tmp_path / "parquet",
            manifests_dir=tmp_path / "manifests",
            ledger_path=tmp_path / "ledger.jsonl",
            quarantine_dir=tmp_path / "quarantine",
        )

        # Commit Snapshot at T=14:30:00 (knowledge T=14:30:01)
        t_snap = datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc)
        snap_tbl = _make_snapshot_batch("001", "snap_001")
        engine.commit_snapshot_batch(
            batch_id="batch_snap_001",
            table=snap_tbl,
            source_id="CME",
            source_uri="s3://cme/snap1",
            raw_source_sha256="1" * 64,
        )

        # Commit Delta 1 at T=14:30:00.100 (knowledge T=14:30:01) -> updates Bid size to 35
        t_delta1 = datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)
        delta_tbl1 = _make_delta_batch("00000000000000001001", t_delta1, t_snap + timedelta(seconds=1))
        engine.commit_delta_batch(
            batch_id="batch_delta_001",
            table=delta_tbl1,
            source_id="CME",
            source_uri="s3://cme/delta1",
            raw_source_sha256="2" * 64,
        )

        # Commit Delta 2 (Late arrived knowledge at T=14:30:05, exchange time T=14:30:00.200) -> updates Bid size to 99
        t_delta2 = datetime(2026, 1, 19, 14, 30, 0, 200, tzinfo=timezone.utc)
        delta_tbl2 = _make_delta_batch("00000000000000001002", t_delta2, t_snap + timedelta(seconds=5))
        delta_pydict2 = delta_tbl2.to_pydict()
        delta_pydict2["size"][0] = Decimal("99")
        engine.commit_delta_batch(
            batch_id="batch_delta_002",
            table=pa.Table.from_pydict(delta_pydict2, schema=CANONICAL_BOOK_DELTA_SCHEMA),
            source_id="CME",
            source_uri="s3://cme/delta2",
            raw_source_sha256="3" * 64,
        )


        # Query 1: As of knowledge T=14:30:02 (Delta 2 is NOT knowable yet) -> Bid size should be 35
        state_as_of_2 = engine.point_in_time_reconstruct(
            source_id="CME",
            channel_id="310",
            symbol="ES.FUT",
            trading_date_val=date(2026, 1, 19),
            target_exchange_time_utc=datetime(2026, 1, 19, 14, 30, 0, 500, tzinfo=timezone.utc),
            as_of_knowledge_time_utc=datetime(2026, 1, 19, 14, 30, 2, 0, tzinfo=timezone.utc),
            top_n=5,
        )
        assert state_as_of_2.is_valid
        assert state_as_of_2.bids[0].size == Decimal("35")

        # Query 2: As of knowledge T=14:30:06 (Delta 2 is NOW knowable) -> Bid size should be 99
        state_as_of_6 = engine.point_in_time_reconstruct(
            source_id="CME",
            channel_id="310",
            symbol="ES.FUT",
            trading_date_val=date(2026, 1, 19),
            target_exchange_time_utc=datetime(2026, 1, 19, 14, 30, 0, 500, tzinfo=timezone.utc),
            as_of_knowledge_time_utc=datetime(2026, 1, 19, 14, 30, 6, 0, tzinfo=timezone.utc),
            top_n=5,
        )
        assert state_as_of_6.is_valid
        assert state_as_of_6.bids[0].size == Decimal("99")
