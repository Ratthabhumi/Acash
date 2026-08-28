"""Unit tests for Trades Parquet Storage Engine and DuckDB PIT Query layer (Phase 3A)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from acash.data.provenance import BatchLifecycleStatus
from acash.data.schema import BatchCollisionError
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA
from acash.data.trades.storage import TradesStorageEngine


def _make_trades_table(
    symbol: str = "ES.FUT",
    trading_date_val: date = date(2026, 1, 19),
    seq_start: int = 1000,
    num_rows: int = 5,
    knowledge_offset_sec: int = 0,
) -> pa.Table:
    """Helper to generate a valid trades table for testing storage."""
    base_time = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    base_know = datetime(2026, 1, 19, 14, 30, 10 + knowledge_offset_sec, tzinfo=timezone.utc)

    data = {
        "source_id": ["CME"] * num_rows,
        "channel_id": ["310"] * num_rows,
        "symbol": [symbol] * num_rows,
        "trading_date": [trading_date_val] * num_rows,
        "exchange_time_utc": [base_time + timedelta(milliseconds=i * 100) for i in range(num_rows)],
        "feed_time_utc": [base_time + timedelta(milliseconds=i * 100 + 5) for i in range(num_rows)],
        "knowledge_time_utc": [base_know for _ in range(num_rows)],
        "source_seq_num": [seq_start + i for i in range(num_rows)],
        "trade_id": [f"TRD_{seq_start + i}" for i in range(num_rows)],
        "match_sub_idx": [0] * num_rows,
        "price": [Decimal(f"5000.{25 + i:02d}0000000000000000") for i in range(num_rows)],
        "size": [Decimal(f"{10 + i}.000000000000000000") for i in range(num_rows)],
        "aggressor_side": ["BUY" if i % 2 == 0 else "SELL" for i in range(num_rows)],
        "trade_condition": ["REGULAR"] * num_rows,
    }
    return pa.Table.from_pydict(data, schema=CANONICAL_TRADES_SCHEMA)


def test_trades_commit_batch_and_storage_layout(tmp_path: Path) -> None:
    """Verify that commit_batch creates daily partitioned Parquet and manifest/provenance."""
    engine = TradesStorageEngine(
        base_dir=tmp_path / "parquet" / "trades",
        manifests_dir=tmp_path / "manifests",
        ledger_path=tmp_path / "provenance_ledger.jsonl",
        quarantine_dir=tmp_path / "quarantine",
    )

    table = _make_trades_table()
    batch_id = "batch_trades_test_001"

    part_path = engine.commit_batch(
        batch_id=batch_id,
        table=table,
        source_id="CME",
        source_uri="cme://md3/ch310",
        raw_source_sha256="a" * 64,
    )

    # 1. Verify part path partition layout: symbol/year=YYYY/date=YYYY-MM-DD/part-{batch_id}.parquet
    expected_path = (
        tmp_path / "parquet" / "trades" / "ES.FUT" / "year=2026" / "date=2026-01-19" / f"part-{batch_id}.parquet"
    )
    assert part_path == expected_path
    assert part_path.exists()

    # 2. Verify manifest transitioned to COMMITTED
    manifest = engine.provenance_tracker.load_manifest(batch_id)
    assert manifest is not None
    assert manifest.status == BatchLifecycleStatus.COMMITTED
    assert manifest.row_count == 5

    # 3. Verify provenance record appended
    prov_record = engine.provenance_tracker.get_provenance_record(batch_id)
    assert prov_record is not None
    assert prov_record.batch_id == batch_id


def test_trades_storage_replay_idempotency_and_collision(tmp_path: Path) -> None:
    """Verify idempotent replay returns existing part and modified payload raises BatchCollisionError."""
    engine = TradesStorageEngine(
        base_dir=tmp_path / "parquet" / "trades",
        manifests_dir=tmp_path / "manifests",
        ledger_path=tmp_path / "provenance_ledger.jsonl",
        quarantine_dir=tmp_path / "quarantine",
    )

    table = _make_trades_table()
    batch_id = "batch_trades_test_idemp"

    # First commit
    part1 = engine.commit_batch(
        batch_id=batch_id,
        table=table,
        source_id="CME",
        source_uri="cme://md3/ch310",
        raw_source_sha256="a" * 64,
    )

    # Replay with identical table
    part2 = engine.commit_batch(
        batch_id=batch_id,
        table=table,
        source_id="CME",
        source_uri="cme://md3/ch310",
        raw_source_sha256="a" * 64,
    )
    assert part1 == part2

    # Modified table under same batch_id -> collision
    data_mod = table.to_pydict()
    data_mod["price"][0] = Decimal("9999.99")
    tbl_mod = pa.Table.from_pydict(data_mod, schema=CANONICAL_TRADES_SCHEMA)

    with pytest.raises(BatchCollisionError, match="Batch collision"):
        engine.commit_batch(
            batch_id=batch_id,
            table=tbl_mod,
            source_id="CME",
            source_uri="cme://md3/ch310",
            raw_source_sha256="a" * 64,
        )


def test_trades_crash_recovery_and_quarantine(tmp_path: Path) -> None:
    """Verify crash recovery recovers PART_PUBLISHED parts and quarantines orphans."""
    engine = TradesStorageEngine(
        base_dir=tmp_path / "parquet" / "trades",
        manifests_dir=tmp_path / "manifests",
        ledger_path=tmp_path / "provenance_ledger.jsonl",
        quarantine_dir=tmp_path / "quarantine",
    )

    table = _make_trades_table()
    batch_id = "batch_crash_recovery_test"

    # Simulate crash at PART_PUBLISHED
    target_path = engine.get_part_file_path("ES.FUT", date(2026, 1, 19), batch_id)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, target_path)

    from acash.data.provenance import BatchManifest
    from acash.data.trades.hashing import calculate_canonical_trades_sha256
    hash_val = calculate_canonical_trades_sha256(table)

    manifest = BatchManifest(
        batch_id=batch_id,
        status=BatchLifecycleStatus.PART_PUBLISHED,
        source_id="CME",
        source_uri_or_path="cme://md3/ch310",
        raw_source_sha256="a" * 64,
        canonical_batch_sha256=hash_val,
        schema_version="1.3.0",
        transform_version="1.0.0",
        symbol="ES.FUT",
        timeframe="TICK",
        year_partition=2026,
        part_file_path=str(target_path),
        row_count=table.num_rows,
        min_event_time_utc="2026-01-19T14:30:00Z",
        max_event_time_utc="2026-01-19T14:30:01Z",
        created_at_utc="2026-01-19T14:30:00Z",
        updated_at_utc="2026-01-19T14:30:00Z",
    )
    engine.provenance_tracker.save_manifest(manifest)

    # Create an orphan parquet file without a manifest
    orphan_path = target_path.parent / "part-orphan_batch_999.parquet"
    pq.write_table(table, orphan_path)

    # Run crash recovery pass
    recovery_result = engine.run_crash_recovery_pass()

    assert batch_id in recovery_result["recovered_batches"]
    assert any("orphan_batch_999" in q for q in recovery_result["quarantined_parts"])

    # Manifest should now be COMMITTED
    updated_manifest = engine.provenance_tracker.load_manifest(batch_id)
    assert updated_manifest is not None
    assert updated_manifest.status == BatchLifecycleStatus.COMMITTED

    # Orphan file moved to quarantine
    assert not orphan_path.exists()
    assert (tmp_path / "quarantine" / "part-orphan_batch_999.parquet").exists()


def test_duckdb_point_in_time_trades_query(tmp_path: Path) -> None:
    """Verify DuckDB PIT query retrieves trades with strict zero lookahead leakage."""
    engine = TradesStorageEngine(
        base_dir=tmp_path / "parquet" / "trades",
        manifests_dir=tmp_path / "manifests",
        ledger_path=tmp_path / "provenance_ledger.jsonl",
        quarantine_dir=tmp_path / "quarantine",
    )

    # Batch 1 ingested at knowledge_time 14:30:10
    tbl1 = _make_trades_table(seq_start=100, num_rows=5, knowledge_offset_sec=0)
    engine.commit_batch(
        batch_id="batch_pit_1",
        table=tbl1,
        source_id="CME",
        source_uri="cme://md3/ch310",
        raw_source_sha256="1" * 64,
    )

    # Batch 2 ingested later at knowledge_time 14:30:20
    tbl2 = _make_trades_table(seq_start=200, num_rows=5, knowledge_offset_sec=10)
    engine.commit_batch(
        batch_id="batch_pit_2",
        table=tbl2,
        source_id="CME",
        source_uri="cme://md3/ch310",
        raw_source_sha256="2" * 64,
    )


    # PIT Query as-of 14:30:15 (should see only Batch 1, NOT Batch 2)
    as_of_t = datetime(2026, 1, 19, 14, 30, 15, tzinfo=timezone.utc)
    start_t = datetime(2026, 1, 19, 14, 0, 0, tzinfo=timezone.utc)
    end_t = datetime(2026, 1, 19, 15, 0, 0, tzinfo=timezone.utc)

    result_table = engine.point_in_time_query(
        symbol="ES.FUT",
        as_of_knowledge_time_utc=as_of_t,
        start_exchange_time_utc=start_t,
        end_exchange_time_utc=end_t,
    )

    assert result_table.num_rows == 5
    seq_nums = result_table["source_seq_num"].to_pylist()
    assert seq_nums == [100, 101, 102, 103, 104]

    # PIT Query as-of 14:30:25 (should see both Batch 1 and Batch 2)
    as_of_t2 = datetime(2026, 1, 19, 14, 30, 25, tzinfo=timezone.utc)
    result_table2 = engine.point_in_time_query(
        symbol="ES.FUT",
        as_of_knowledge_time_utc=as_of_t2,
        start_exchange_time_utc=start_t,
        end_exchange_time_utc=end_t,
    )
    assert result_table2.num_rows == 10
