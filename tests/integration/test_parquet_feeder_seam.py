"""Offline Data-Plane Integration Seam Tests.

Validates the full offline data pipeline:
    ParquetStorageEngine
            │
            ▼
       DuckDBStorage
            │
            ▼
    ParquetMarketDataProvider (IMarketDataProvider)
            │
            ▼
    ForwardMarketDataFeeder (STREAMING_PARQUET_PUMP)

Contract Invariants Verified:
1. Zero live broker or external network connectivity.
2. Canonical PyArrow schema persistence via ParquetStorageEngine.
3. Point-in-time (PIT) revision isolation via DuckDBStorage analytical engine.
4. ParquetMarketDataProvider compliance with IMarketDataProvider canonical contract.
5. Exact Decimal preservation across Arrow -> DuckDB -> Domain Bar -> Feeder Snapshot.
6. ForwardMarketDataFeeder historical bar replay and offline derived snapshot modes.
7. Strict fail-closed boundaries (TOP_OF_BOOK_UNAVAILABLE, session mismatches, naive datetimes).
8. Telemetry and freshness tracking under STREAMING_PARQUET_PUMP.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple
import pyarrow as pa
import pytest

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.data.parquet_provider import ParquetMarketDataProvider
from acash.data.schema import CANONICAL_ARROW_SCHEMA
from acash.data.storage import DuckDBStorage, ParquetStorageEngine
from acash.runtime.feeder import FeedSourceType, ForwardMarketDataFeeder


def make_synthetic_arrow_table(
    symbol: str,
    timeframe: str,
    bars_data: Sequence[Mapping[str, Any]],
    source_id: str = "synth_offline_fixture",
) -> pa.Table:
    """Build a canonical PyArrow Table with strictly typed columns."""
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
        "quote_volume": [b.get("quote_volume", Decimal("10000.0")) for b in bars_data],
        "trade_count": [b.get("trade_count", 50) for b in bars_data],
    }
    return pa.Table.from_pydict(pydict, schema=CANONICAL_ARROW_SCHEMA)


class SyntheticSessionIdentity:
    """Session identity test double for offline pipeline validation."""

    def __init__(
        self,
        data_source: FeedSourceType = FeedSourceType.STREAMING_PARQUET_PUMP,
        execution_mode: str = "LOCAL_SIMULATOR",
    ) -> None:
        self.data_source = data_source
        self.execution_mode = execution_mode


@pytest.fixture
def offline_data_substrate(tmp_path: Path) -> Tuple[ParquetStorageEngine, DuckDBStorage]:
    """Provide isolated offline Parquet storage and DuckDB engine."""
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


class TestParquetFeederIntegrationSeam:
    """End-to-end integration tests for the Parquet -> DuckDB -> Provider -> Feeder seam."""

    def test_end_to_end_historical_replay_pipeline(
        self,
        offline_data_substrate: Tuple[ParquetStorageEngine, DuckDBStorage],
    ) -> None:
        """Verify ingestion into Parquet, PIT query via DuckDB, provider bar conversion, and feeder replay."""
        engine, storage = offline_data_substrate

        # 1. Ingest synthetic historical bars into Parquet storage
        t0 = datetime(2026, 1, 5, 14, 30, tzinfo=timezone.utc)
        t1 = t0 + timedelta(minutes=1)
        t2 = t0 + timedelta(minutes=2)
        t3 = t0 + timedelta(minutes=3)

        bars_raw = [
            {
                "event_start_utc": t0,
                "event_end_utc": t1,
                "knowledge_time_utc": t1,
                "open": Decimal("5000.25"),
                "high": Decimal("5005.50"),
                "low": Decimal("4998.00"),
                "close": Decimal("5002.75"),
                "volume": Decimal("1250.0"),
            },
            {
                "event_start_utc": t1,
                "event_end_utc": t2,
                "knowledge_time_utc": t2,
                "open": Decimal("5002.75"),
                "high": Decimal("5010.00"),
                "low": Decimal("5001.25"),
                "close": Decimal("5008.50"),
                "volume": Decimal("1400.0"),
            },
            {
                "event_start_utc": t2,
                "event_end_utc": t3,
                "knowledge_time_utc": t3,
                "open": Decimal("5008.50"),
                "high": Decimal("5012.00"),
                "low": Decimal("5005.00"),
                "close": Decimal("5007.25"),
                "volume": Decimal("980.0"),
            },
        ]
        table = make_synthetic_arrow_table("SYNTH_INDEX", "M1", bars_raw)
        engine.write_canonical_part(
            table=table,
            batch_id="batch_synth_001",
            source_id="synth_feed",
            source_uri_or_path="file:///synth/batch_001.parquet",
            raw_source_sha256="a" * 64,
        )

        # 2. Instantiate ParquetMarketDataProvider over DuckDBStorage
        provider = ParquetMarketDataProvider(storage=storage)

        # 3. Retrieve historical bars via canonical contract
        bars = provider.get_historical_bars(
            symbol="SYNTH_INDEX",
            timeframe=BarTimeframe.M1,
            start_utc=t0,
            end_utc=t3,
        )
        assert len(bars) == 3
        assert all(isinstance(b, Bar) for b in bars)
        assert bars[0].close == Decimal("5002.75")
        assert bars[1].close == Decimal("5008.50")
        assert bars[2].close == Decimal("5007.25")

        # 4. Feed bars through ForwardMarketDataFeeder in STREAMING_PARQUET_PUMP mode
        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.STREAMING_PARQUET_PUMP,
            session_identity=SyntheticSessionIdentity(),
            historical_iterator=iter(bars),
        )

        sim_now = datetime(2026, 1, 5, 16, 0, tzinfo=timezone.utc)

        # Step through bars
        snap1, age1 = feeder.poll_next_market_snapshot("SYNTH_INDEX", sim_now)
        assert snap1.symbol == "SYNTH_INDEX"
        assert snap1.last_price == Decimal("5002.75")
        assert snap1.bid == Decimal("5002.75") - Decimal("0.0001")
        assert snap1.ask == Decimal("5002.75") + Decimal("0.0001")
        assert age1 == 0  # Offline replay has 0 age by construction

        snap2, age2 = feeder.poll_next_market_snapshot("SYNTH_INDEX", sim_now)
        assert snap2.last_price == Decimal("5008.50")
        assert age2 == 0

        snap3, age3 = feeder.poll_next_market_snapshot("SYNTH_INDEX", sim_now)
        assert snap3.last_price == Decimal("5007.25")
        assert age3 == 0

        # After iterator is exhausted, feeder retains the last snapshot
        snap_post, _ = feeder.poll_next_market_snapshot("SYNTH_INDEX", sim_now)
        assert snap_post.last_price == Decimal("5007.25")

        # Verify feed telemetry status
        status = feeder.get_feed_status(sim_now)
        assert status.is_connected is True
        assert status.feed_source == FeedSourceType.STREAMING_PARQUET_PUMP
        assert status.last_tick_utc == t3

    def test_point_in_time_revision_isolation_seam(
        self,
        offline_data_substrate: Tuple[ParquetStorageEngine, DuckDBStorage],
    ) -> None:
        """Verify that revisions written with later knowledge time are isolated point-in-time."""
        engine, storage = offline_data_substrate

        t_event_start = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
        t_event_end = datetime(2026, 1, 10, 10, 1, tzinfo=timezone.utc)
        t_v1_knowledge = datetime(2026, 1, 10, 10, 5, tzinfo=timezone.utc)
        t_v2_knowledge = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)

        # Vintage 1: initial publication
        bar_v1 = [
            {
                "event_start_utc": t_event_start,
                "event_end_utc": t_event_end,
                "knowledge_time_utc": t_v1_knowledge,
                "revision_seq": 1,
                "open": Decimal("100.00"),
                "high": Decimal("105.00"),
                "low": Decimal("99.00"),
                "close": Decimal("102.00"),
                "volume": Decimal("500.0"),
            }
        ]
        table_v1 = make_synthetic_arrow_table("RESTATED_ASSET", "M1", bar_v1)
        engine.write_canonical_part(table_v1, "batch_v1", "src", "uri_v1", "b" * 64)

        # Vintage 2: retrospective correction
        bar_v2 = [
            {
                "event_start_utc": t_event_start,
                "event_end_utc": t_event_end,
                "knowledge_time_utc": t_v2_knowledge,
                "revision_seq": 2,
                "open": Decimal("100.00"),
                "high": Decimal("106.00"),
                "low": Decimal("99.00"),
                "close": Decimal("104.50"),  # Restated close
                "volume": Decimal("520.0"),
            }
        ]
        table_v2 = make_synthetic_arrow_table("RESTATED_ASSET", "M1", bar_v2)
        engine.write_canonical_part(table_v2, "batch_v2", "src", "uri_v2", "c" * 64)

        # Provider pinned to Vintage 1 knowledge time
        provider_v1 = ParquetMarketDataProvider(
            storage=storage,
            as_of_knowledge_time_utc=t_v1_knowledge,
        )
        bars_v1 = provider_v1.get_historical_bars(
            "RESTATED_ASSET", BarTimeframe.M1, t_event_start, t_event_end
        )
        assert len(bars_v1) == 1
        assert bars_v1[0].close == Decimal("102.00")

        # Provider pinned to Vintage 2 knowledge time sees restatement
        provider_v2 = ParquetMarketDataProvider(
            storage=storage,
            as_of_knowledge_time_utc=t_v2_knowledge,
        )
        bars_v2 = provider_v2.get_historical_bars(
            "RESTATED_ASSET", BarTimeframe.M1, t_event_start, t_event_end
        )
        assert len(bars_v2) == 1
        assert bars_v2[0].close == Decimal("104.50")

    def test_derived_snapshot_mode_direct_polling(
        self,
        offline_data_substrate: Tuple[ParquetStorageEngine, DuckDBStorage],
    ) -> None:
        """Verify ForwardMarketDataFeeder polling directly from provider when allow_offline_derived_snapshot=True."""
        engine, storage = offline_data_substrate

        t_bar_start = datetime(2026, 2, 1, 9, 30, tzinfo=timezone.utc)
        t_bar_end = datetime(2026, 2, 1, 9, 31, tzinfo=timezone.utc)

        data = [
            {
                "event_start_utc": t_bar_start,
                "event_end_utc": t_bar_end,
                "knowledge_time_utc": t_bar_end,
                "open": Decimal("250.00"),
                "high": Decimal("252.00"),
                "low": Decimal("249.50"),
                "close": Decimal("251.50"),
                "volume": Decimal("2000.0"),
            }
        ]
        table = make_synthetic_arrow_table("DERIVED_FEED", "M1", data)
        engine.write_canonical_part(table, "batch_derived", "src", "uri_der", "d" * 64)

        provider = ParquetMarketDataProvider(
            storage=storage,
            allow_offline_derived_snapshot=True,
            as_of_knowledge_time_utc=t_bar_end,
        )

        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.STREAMING_PARQUET_PUMP,
            session_identity=SyntheticSessionIdentity(),
            historical_iterator=None,  # Feeder delegates directly to provider.get_latest_snapshot
        )

        wall_clock = datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc)
        snap, age = feeder.poll_next_market_snapshot("DERIVED_FEED", wall_clock)

        assert snap.symbol == "DERIVED_FEED"
        assert snap.last_price == Decimal("251.50")
        assert snap.bid == Decimal("251.50") - Decimal("0.0001")
        assert snap.ask == Decimal("251.50") + Decimal("0.0001")
        assert snap.timestamp_utc == t_bar_end
        assert age == 0

    def test_strict_fail_closed_session_and_contract_boundaries(
        self,
        offline_data_substrate: Tuple[ParquetStorageEngine, DuckDBStorage],
    ) -> None:
        """Verify strict fail-closed exceptions when protocol contracts are violated."""
        _, storage = offline_data_substrate
        provider = ParquetMarketDataProvider(storage=storage)

        # 1. Default provider get_latest_snapshot fails closed with DataContractError
        with pytest.raises(DataContractError, match="TOP_OF_BOOK_UNAVAILABLE"):
            provider.get_latest_snapshot("ANY_SYM")

        # 2. Feeder pairing STREAMING_PARQUET_PUMP with MT5_DEMO fails closed
        class InvalidMT5Session:
            data_source = FeedSourceType.STREAMING_PARQUET_PUMP
            execution_mode = "MT5_DEMO"

        with pytest.raises(DataContractError, match="INVALID_SESSION_CONFIGURATION"):
            ForwardMarketDataFeeder(
                provider=provider,
                source_type=FeedSourceType.STREAMING_PARQUET_PUMP,
                session_identity=InvalidMT5Session(),
            )

        # 3. Feeder source type mismatch with session identity fails closed
        class MismatchedSession:
            data_source = FeedSourceType.MT5_FORWARD
            execution_mode = "LIVE"

        with pytest.raises(DataContractError, match="FEED_SOURCE_MISMATCH"):
            ForwardMarketDataFeeder(
                provider=provider,
                source_type=FeedSourceType.STREAMING_PARQUET_PUMP,
                session_identity=MismatchedSession(),
            )

        # 4. Feeder poll with naive datetime fails closed
        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.STREAMING_PARQUET_PUMP,
            session_identity=SyntheticSessionIdentity(),
        )
        with pytest.raises(DataContractError, match="wall_clock_utc must be a timezone-aware UTC datetime"):
            feeder.poll_next_market_snapshot("SYM", datetime(2026, 1, 1, 12, 0))  # Naive
