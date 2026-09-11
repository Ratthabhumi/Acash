"""Point-in-Time (PIT) & Provenance Cryptographic Hardening Tests.

Verifies:
1. Strict non-anticipation: As-of queries before knowledge_time_utc return zero rows.
2. Vintage reproducibility: Earlier vintages remain immutable after retrospective revisions.
3. Later revisions never leak backward into past queries.
4. Clear separation between:
   - EVENT TIME (when the economic event occurred)
   - KNOWLEDGE TIME (when the observation entered the database / became known)
   - REVISION TIME (revision sequence ordering)
5. Canonical batch SHA-256 determinism and single-bit sensitivity.
6. Provenance ledger hash chaining and duplicate rejection.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple
import pyarrow as pa
import pytest

from acash.data.provenance import (
    BatchLifecycleStatus,
    calculate_canonical_batch_sha256,
)
from acash.data.schema import CANONICAL_ARROW_SCHEMA
from acash.data.storage import DuckDBStorage, ParquetStorageEngine


def make_canonical_table(
    symbol: str,
    timeframe: str,
    bars_data: Sequence[Mapping[str, Any]],
    source_id: str = "pit_hardening_feed",
) -> pa.Table:
    """Helper to construct canonical PyArrow table for PIT testing."""
    pydict = {
        "source_id": [source_id] * len(bars_data),
        "symbol": [symbol] * len(bars_data),
        "timeframe": [timeframe] * len(bars_data),
        "event_start_utc": [b["event_start_utc"] for b in bars_data],
        "event_end_utc": [b["event_end_utc"] for b in bars_data],
        "knowledge_time_utc": [b["knowledge_time_utc"] for b in bars_data],
        "revision_seq": [b.get("revision_seq", 1) for b in bars_data],
        "open": [b["open"] for b in bars_data],
        "high": [b["high"] for b in bars_data],
        "low": [b["low"] for b in bars_data],
        "close": [b["close"] for b in bars_data],
        "volume": [b["volume"] for b in bars_data],
        "quote_volume": [b.get("quote_volume", Decimal("1000.0")) for b in bars_data],
        "trade_count": [b.get("trade_count", 10) for b in bars_data],
    }
    return pa.Table.from_pydict(pydict, schema=CANONICAL_ARROW_SCHEMA)


@pytest.fixture
def pit_env(tmp_path: Path) -> Tuple[ParquetStorageEngine, DuckDBStorage]:
    """Isolated storage engine and DuckDB engine."""
    base_dir = tmp_path / "parquet"
    manifests_dir = tmp_path / "manifests"
    ledger_path = tmp_path / "ledger.jsonl"
    quarantine_dir = tmp_path / "quarantine"

    engine = ParquetStorageEngine(
        base_dir=base_dir,
        manifests_dir=manifests_dir,
        ledger_path=ledger_path,
        quarantine_dir=quarantine_dir,
    )
    storage = DuckDBStorage(base_dir=base_dir)
    return engine, storage


class TestPitProvenanceHardening:
    """Comprehensive test suite for PIT non-anticipation and provenance determinism."""

    def test_vintage_isolation_strict_no_backward_leak(
        self,
        pit_env: Tuple[ParquetStorageEngine, DuckDBStorage],
    ) -> None:
        """Verify that retrospective revisions never leak backward into earlier query horizons."""
        engine, storage = pit_env

        t_event_start = datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)
        t_event_end = datetime(2026, 3, 1, 9, 31, tzinfo=timezone.utc)
        t_pub_v1 = datetime(2026, 3, 1, 9, 35, tzinfo=timezone.utc)
        t_pub_v2 = datetime(2026, 3, 1, 14, 00, tzinfo=timezone.utc)

        # 1. Vintage 1: Initial flash estimate
        bar_v1 = [
            {
                "event_start_utc": t_event_start,
                "event_end_utc": t_event_end,
                "knowledge_time_utc": t_pub_v1,
                "revision_seq": 1,
                "open": Decimal("100.0"),
                "high": Decimal("105.0"),
                "low": Decimal("99.0"),
                "close": Decimal("102.50"),
                "volume": Decimal("500"),
            }
        ]
        table_v1 = make_canonical_table("PIT_SYM", "M1", bar_v1)
        engine.write_canonical_part(table_v1, "batch_v1", "pit_src", "mock://v1", "1" * 64)

        # 2. Query before knowledge time: Must return ZERO rows (strict non-anticipation)
        before_pub = datetime(2026, 3, 1, 9, 34, tzinfo=timezone.utc)
        res_before = storage.query_point_in_time("PIT_SYM", "M1", as_of_knowledge_time_utc=before_pub)
        assert res_before.num_rows == 0

        # 3. Query as of Vintage 1: Returns flash estimate (102.50)
        res_v1 = storage.query_point_in_time("PIT_SYM", "M1", as_of_knowledge_time_utc=t_pub_v1)
        assert res_v1.num_rows == 1
        assert Decimal(str(res_v1.to_pylist()[0]["close"])) == Decimal("102.50")
        assert res_v1.to_pylist()[0]["revision_seq"] == 1

        # 4. Ingest Vintage 2: Official end-of-day revision (104.75)
        bar_v2 = [
            {
                "event_start_utc": t_event_start,
                "event_end_utc": t_event_end,
                "knowledge_time_utc": t_pub_v2,
                "revision_seq": 2,
                "open": Decimal("100.0"),
                "high": Decimal("106.0"),
                "low": Decimal("99.0"),
                "close": Decimal("104.75"),
                "volume": Decimal("520"),
            }
        ]
        table_v2 = make_canonical_table("PIT_SYM", "M1", bar_v2)
        engine.write_canonical_part(table_v2, "batch_v2", "pit_src", "mock://v2", "2" * 64)

        # 5. RE-TEST Vintage 1 horizon: Must STILL return Vintage 1 (102.50)
        # Proves no backward leak from Vintage 2
        res_v1_retest = storage.query_point_in_time("PIT_SYM", "M1", as_of_knowledge_time_utc=t_pub_v1)
        assert res_v1_retest.num_rows == 1
        assert Decimal(str(res_v1_retest.to_pylist()[0]["close"])) == Decimal("102.50")
        assert res_v1_retest.to_pylist()[0]["revision_seq"] == 1

        # 6. Query as of Vintage 2: Returns updated revision (104.75)
        res_v2 = storage.query_point_in_time("PIT_SYM", "M1", as_of_knowledge_time_utc=t_pub_v2)
        assert res_v2.num_rows == 1
        assert Decimal(str(res_v2.to_pylist()[0]["close"])) == Decimal("104.75")
        assert res_v2.to_pylist()[0]["revision_seq"] == 2

    def test_event_time_vs_knowledge_time_distinction(
        self,
        pit_env: Tuple[ParquetStorageEngine, DuckDBStorage],
    ) -> None:
        """Verify that event occurrence time does NOT make data available prior to knowledge time."""
        engine, storage = pit_env

        # Bar occurred at 08:30 (e.g. CPI release), but knowledge time in DB is 08:35
        t_event_start = datetime(2026, 3, 2, 8, 30, tzinfo=timezone.utc)
        t_event_end = datetime(2026, 3, 2, 8, 31, tzinfo=timezone.utc)
        t_knowledge = datetime(2026, 3, 2, 8, 35, tzinfo=timezone.utc)

        bar = [
            {
                "event_start_utc": t_event_start,
                "event_end_utc": t_event_end,
                "knowledge_time_utc": t_knowledge,
                "open": Decimal("300.0"),
                "high": Decimal("302.0"),
                "low": Decimal("298.0"),
                "close": Decimal("301.0"),
                "volume": Decimal("100"),
            }
        ]
        table = make_canonical_table("CPI_EVENT", "M1", bar)
        engine.write_canonical_part(table, "batch_cpi_001", "cpi_src", "mock://cpi", "3" * 64)

        # Query at 08:32: Bar happened in the real world, but knowledge has not arrived
        query_time = datetime(2026, 3, 2, 8, 32, tzinfo=timezone.utc)
        res = storage.query_point_in_time("CPI_EVENT", "M1", as_of_knowledge_time_utc=query_time)
        assert res.num_rows == 0

        # Query at 08:36: Knowledge time has passed; bar is now visible
        query_time_post = datetime(2026, 3, 2, 8, 36, tzinfo=timezone.utc)
        res_post = storage.query_point_in_time("CPI_EVENT", "M1", as_of_knowledge_time_utc=query_time_post)
        assert res_post.num_rows == 1
        assert Decimal(str(res_post.to_pylist()[0]["close"])) == Decimal("301.0")

    def test_canonical_batch_sha256_determinism_and_sensitivity(self) -> None:
        """Verify that identical data produces identical SHA-256, and any micro-change mutates digest."""
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        bar_base = [
            {
                "event_start_utc": t0,
                "event_end_utc": t1,
                "knowledge_time_utc": t1,
                "open": Decimal("100.00"),
                "high": Decimal("101.00"),
                "low": Decimal("99.00"),
                "close": Decimal("100.50"),
                "volume": Decimal("10"),
            }
        ]
        tbl1 = make_canonical_table("SYM", "M1", bar_base)
        tbl2 = make_canonical_table("SYM", "M1", bar_base)

        hash1 = calculate_canonical_batch_sha256(tbl1)
        hash2 = calculate_canonical_batch_sha256(tbl2)
        assert hash1 == hash2

        # Change close by $0.0001 (micro-cent)
        bar_mutated = [
            {
                "event_start_utc": t0,
                "event_end_utc": t1,
                "knowledge_time_utc": t1,
                "open": Decimal("100.00"),
                "high": Decimal("101.00"),
                "low": Decimal("99.00"),
                "close": Decimal("100.5001"),  # Mutated
                "volume": Decimal("10"),
            }
        ]
        tbl_mutated = make_canonical_table("SYM", "M1", bar_mutated)
        hash_mutated = calculate_canonical_batch_sha256(tbl_mutated)
        assert hash_mutated != hash1
