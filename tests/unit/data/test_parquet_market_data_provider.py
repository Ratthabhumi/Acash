"""Unit and contract tests for ParquetMarketDataProvider.

Verifies:
A. Valid historical request returns domain Bar models
B. Deterministic event_start_utc ASC ordering
C. Correct symbol selection & cross-symbol isolation
D. Correct timeframe selection & cross-timeframe isolation
E. Interval boundaries inclusive filtering
F. Missing symbol returns empty tuple ()
G. Empty interval returns empty tuple ()
H. Fail-closed on invalid request (naive datetime, start > end, empty symbol, invalid timeframe)
I. Gaps remain gaps (zero forward-fill, zero bar fabrication)
J. Point-in-time revision behavior (constructor-pinned vs default end_utc)
K. Exact Decimal preservation (zero float conversion drift)
L. ForwardMarketDataFeeder integration in STREAMING_PARQUET_PUMP mode
M. get_latest_snapshot fails closed by default; succeeds only when allow_offline_derived_snapshot=True
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


def make_test_bar_table(
    symbol: str,
    timeframe: str,
    bars_data: Sequence[Mapping[str, Any]],
    source_id: str = "test_feed",
) -> pa.Table:
    """Helper to construct canonical PyArrow table for testing."""
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
def data_env(tmp_path: Path) -> Tuple[ParquetStorageEngine, DuckDBStorage]:
    """Fixture providing isolated ParquetStorageEngine, DuckDBStorage, and test directory."""
    base_dir = tmp_path / "parquet"
    manifests_dir = tmp_path / "manifests"
    ledger_path = tmp_path / "provenance_ledger.jsonl"
    quarantine_dir = tmp_path / "quarantine"

    engine = ParquetStorageEngine(
        base_dir=base_dir,
        manifests_dir=manifests_dir,
        ledger_path=ledger_path,
        quarantine_dir=quarantine_dir,
    )
    storage = DuckDBStorage(base_dir=base_dir)
    return engine, storage


class TestParquetMarketDataProvider:
    """Test suite covering scenarios A through M for ParquetMarketDataProvider."""

    def test_a_valid_historical_request(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario A: Valid historical request retrieves standard bars matching canonical schema."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)

        data = [
            {
                "event_start_utc": t0,
                "event_end_utc": t1,
                "knowledge_time_utc": t1,
                "open": Decimal("100.00"),
                "high": Decimal("102.50"),
                "low": Decimal("99.50"),
                "close": Decimal("101.25"),
                "volume": Decimal("15.5"),
            },
            {
                "event_start_utc": t1,
                "event_end_utc": t2,
                "knowledge_time_utc": t2,
                "open": Decimal("101.25"),
                "high": Decimal("103.00"),
                "low": Decimal("101.00"),
                "close": Decimal("102.80"),
                "volume": Decimal("20.0"),
            },
        ]
        table = make_test_bar_table("EURUSD", "M1", data)
        engine.write_canonical_part(
            table=table,
            batch_id="batch_eurusd_m1_001",
            source_id="test_feed",
            source_uri_or_path="mock://eurusd",
            raw_source_sha256="a" * 64,
        )

        provider = ParquetMarketDataProvider(storage=storage)
        bars = provider.get_historical_bars(
            symbol="EURUSD",
            timeframe=BarTimeframe.M1,
            start_utc=t0,
            end_utc=t2,
        )

        assert len(bars) == 2
        assert all(isinstance(b, Bar) for b in bars)
        assert bars[0].symbol == "EURUSD"
        assert bars[0].timeframe == BarTimeframe.M1
        assert bars[0].open == Decimal("100.00")
        assert bars[0].close == Decimal("101.25")
        assert bars[1].close == Decimal("102.80")

    def test_b_deterministic_ordering(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario B: Returned bars are deterministically sorted by event_start_utc ASC."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)

        # Write out of order in raw table
        data = [
            {
                "event_start_utc": t1,
                "event_end_utc": t2,
                "knowledge_time_utc": t2,
                "open": Decimal("101.0"),
                "high": Decimal("102.0"),
                "low": Decimal("100.0"),
                "close": Decimal("101.5"),
                "volume": Decimal("10.0"),
            },
            {
                "event_start_utc": t0,
                "event_end_utc": t1,
                "knowledge_time_utc": t1,
                "open": Decimal("100.0"),
                "high": Decimal("101.0"),
                "low": Decimal("99.0"),
                "close": Decimal("100.5"),
                "volume": Decimal("10.0"),
            },
        ]
        table = make_test_bar_table("GBPUSD", "M1", data)
        engine.write_canonical_part(
            table=table,
            batch_id="batch_gbpusd_001",
            source_id="test_feed",
            source_uri_or_path="mock://gbpusd",
            raw_source_sha256="b" * 64,
        )

        provider = ParquetMarketDataProvider(storage=storage)
        bars = provider.get_historical_bars(
            symbol="GBPUSD",
            timeframe=BarTimeframe.M1,
            start_utc=t0,
            end_utc=t2,
        )

        assert len(bars) == 2
        assert bars[0].event_start_utc == t0
        assert bars[1].event_start_utc == t1

    def test_c_symbol_isolation(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario C: Querying one symbol isolates data and does not leak bars from other symbols."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        eur_table = make_test_bar_table(
            "EURUSD", "M1",
            [{"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t1,
              "open": Decimal("1.10"), "high": Decimal("1.11"), "low": Decimal("1.09"),
              "close": Decimal("1.105"), "volume": Decimal("100")}]
        )
        engine.write_canonical_part(eur_table, "batch_eur_001", "src", "uri", "c" * 64)

        jpy_table = make_test_bar_table(
            "USDJPY", "M1",
            [{"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t1,
              "open": Decimal("150.0"), "high": Decimal("151.0"), "low": Decimal("149.0"),
              "close": Decimal("150.5"), "volume": Decimal("200")}]
        )
        engine.write_canonical_part(jpy_table, "batch_jpy_001", "src", "uri", "d" * 64)

        provider = ParquetMarketDataProvider(storage=storage)
        eur_bars = provider.get_historical_bars("EURUSD", BarTimeframe.M1, t0, t1)
        assert len(eur_bars) == 1
        assert eur_bars[0].symbol == "EURUSD"
        assert eur_bars[0].close == Decimal("1.105")

    def test_d_timeframe_isolation(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario D: Querying one timeframe does not return bars from another timeframe."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t5 = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc)

        m1_table = make_test_bar_table(
            "SPY", "M1",
            [{"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t1,
              "open": Decimal("500.0"), "high": Decimal("501.0"), "low": Decimal("499.0"),
              "close": Decimal("500.5"), "volume": Decimal("1000")}]
        )
        engine.write_canonical_part(m1_table, "batch_spy_m1", "src", "uri", "e" * 64)

        m5_table = make_test_bar_table(
            "SPY", "M5",
            [{"event_start_utc": t0, "event_end_utc": t5, "knowledge_time_utc": t5,
              "open": Decimal("500.0"), "high": Decimal("503.0"), "low": Decimal("498.0"),
              "close": Decimal("502.0"), "volume": Decimal("5000")}]
        )
        engine.write_canonical_part(m5_table, "batch_spy_m5", "src", "uri", "f" * 64)

        provider = ParquetMarketDataProvider(storage=storage)
        m5_bars = provider.get_historical_bars("SPY", BarTimeframe.M5, t0, t5)
        assert len(m5_bars) == 1
        assert m5_bars[0].timeframe == BarTimeframe.M5
        assert m5_bars[0].close == Decimal("502.0")

    def test_e_interval_boundaries(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario E: Query strictly respects requested interval start_utc and end_utc boundaries."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)
        t3 = datetime(2026, 1, 1, 10, 3, tzinfo=timezone.utc)

        data = [
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t1,
             "open": Decimal("10.0"), "high": Decimal("11.0"), "low": Decimal("9.0"), "close": Decimal("10.5"), "volume": Decimal("1")},
            {"event_start_utc": t1, "event_end_utc": t2, "knowledge_time_utc": t2,
             "open": Decimal("10.5"), "high": Decimal("11.5"), "low": Decimal("10.0"), "close": Decimal("11.0"), "volume": Decimal("1")},
            {"event_start_utc": t2, "event_end_utc": t3, "knowledge_time_utc": t3,
             "open": Decimal("11.0"), "high": Decimal("12.0"), "low": Decimal("10.5"), "close": Decimal("11.5"), "volume": Decimal("1")},
        ]
        table = make_test_bar_table("XAUUSD", "M1", data)
        engine.write_canonical_part(table, "batch_xau_001", "src", "uri", "1" * 64)

        provider = ParquetMarketDataProvider(storage=storage)
        # Query only middle bar
        bars = provider.get_historical_bars("XAUUSD", BarTimeframe.M1, start_utc=t1, end_utc=t2)
        assert len(bars) == 1
        assert bars[0].event_start_utc == t1
        assert bars[0].event_end_utc == t2

    def test_f_missing_symbol_returns_empty_tuple(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario F: Requesting a symbol that does not exist in storage returns empty tuple ()."""
        _, storage = data_env
        provider = ParquetMarketDataProvider(storage=storage)
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)

        bars = provider.get_historical_bars("NON_EXISTENT_TICKER", BarTimeframe.M1, t0, t1)
        assert bars == ()

    def test_g_empty_interval_returns_empty_tuple(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario G: Querying an interval where no bars occurred returns empty tuple ()."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        data = [{"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t1,
                 "open": Decimal("10.0"), "high": Decimal("11.0"), "low": Decimal("9.0"),
                 "close": Decimal("10.0"), "volume": Decimal("1")}]
        table = make_test_bar_table("AAPL", "M1", data)
        engine.write_canonical_part(table, "batch_aapl_001", "src", "uri", "2" * 64)

        provider = ParquetMarketDataProvider(storage=storage)
        # Query 1 hour later
        t_later_start = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t_later_end = datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc)
        bars = provider.get_historical_bars("AAPL", BarTimeframe.M1, t_later_start, t_later_end)
        assert bars == ()

    def test_h_invalid_requests_fail_closed(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario H: Invalid inputs trigger explicit exceptions without guessing or silent repairs."""
        _, storage = data_env
        provider = ParquetMarketDataProvider(storage=storage)
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)

        # 1. Empty or whitespace symbol
        with pytest.raises(DomainValidationError, match="Symbol must be a non-empty string"):
            provider.get_historical_bars("", BarTimeframe.M1, t0, t1)

        with pytest.raises(DomainValidationError, match="Symbol must be a non-empty string"):
            provider.get_historical_bars("   ", BarTimeframe.M1, t0, t1)

        # 2. Naive datetime (no timezone)
        t_naive = datetime(2026, 1, 1, 10, 0)
        with pytest.raises(DataContractError, match="start_utc must be a timezone-aware UTC datetime"):
            provider.get_historical_bars("EURUSD", BarTimeframe.M1, t_naive, t1)

        with pytest.raises(DataContractError, match="end_utc must be a timezone-aware UTC datetime"):
            provider.get_historical_bars("EURUSD", BarTimeframe.M1, t0, t_naive)

        # 3. start_utc > end_utc
        with pytest.raises(DataContractError, match="cannot be later than end_utc"):
            provider.get_historical_bars("EURUSD", BarTimeframe.M1, t1, t0)

        # 4. Invalid timeframe
        with pytest.raises(DataContractError, match="Unsupported or invalid timeframe"):
            provider.get_historical_bars("EURUSD", "INVALID_TF", t0, t1)  # type: ignore

    def test_i_gaps_remain_gaps_no_fabrication(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario I: Gaps between observations remain unpopulated; zero forward-fill, zero fabrication."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        # Missing bar from 10:01 to 10:04
        t4 = datetime(2026, 1, 1, 10, 4, tzinfo=timezone.utc)
        t5 = datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc)

        data = [
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t1,
             "open": Decimal("100.0"), "high": Decimal("101.0"), "low": Decimal("99.0"), "close": Decimal("100.5"), "volume": Decimal("1")},
            {"event_start_utc": t4, "event_end_utc": t5, "knowledge_time_utc": t5,
             "open": Decimal("105.0"), "high": Decimal("106.0"), "low": Decimal("104.0"), "close": Decimal("105.5"), "volume": Decimal("1")},
        ]
        table = make_test_bar_table("BTC/USDT", "M1", data)
        engine.write_canonical_part(table, "batch_btc_gap", "src", "uri", "3" * 64)

        provider = ParquetMarketDataProvider(storage=storage)
        bars = provider.get_historical_bars("BTC/USDT", BarTimeframe.M1, t0, t5)

        # Exactly 2 bars; no synthetic bars created for 10:01, 10:02, 10:03
        assert len(bars) == 2
        assert bars[0].event_start_utc == t0
        assert bars[1].event_start_utc == t4

    def test_j_point_in_time_behavior(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario J: Revisions are filtered strictly by point-in-time knowledge horizon."""
        engine, storage = data_env
        t_start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t_end = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        # Revision 1: initial observation published at 11:00 UTC
        t_know_1 = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)
        table1 = make_test_bar_table(
            "MSFT", "M1",
            [{"event_start_utc": t_start, "event_end_utc": t_end, "knowledge_time_utc": t_know_1,
              "revision_seq": 1, "open": Decimal("400.0"), "high": Decimal("402.0"), "low": Decimal("399.0"),
              "close": Decimal("401.0"), "volume": Decimal("100")}]
        )
        engine.write_canonical_part(table1, "batch_msft_v1", "src", "uri", "4" * 64)

        # Revision 2: revised observation published at 13:00 UTC
        t_know_2 = datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc)
        table2 = make_test_bar_table(
            "MSFT", "M1",
            [{"event_start_utc": t_start, "event_end_utc": t_end, "knowledge_time_utc": t_know_2,
              "revision_seq": 2, "open": Decimal("400.0"), "high": Decimal("402.5"), "low": Decimal("399.0"),
              "close": Decimal("401.5"), "volume": Decimal("120")}]
        )
        engine.write_canonical_part(table2, "batch_msft_v2", "src", "uri", "5" * 64)

        # Case 1: Default provider queries up to 10:30 UTC -> Nothing known yet (table empty)
        provider_default = ParquetMarketDataProvider(storage=storage)
        bars_1030 = provider_default.get_historical_bars(
            "MSFT", BarTimeframe.M1, t_start, datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)
        )
        assert len(bars_1030) == 0

        # Case 2: Pinned vintage at 12:00 UTC -> Sees Revision 1 (Close = 401.0, Revision 2 not known yet)
        provider_pinned_1200 = ParquetMarketDataProvider(
            storage=storage, as_of_knowledge_time_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        )
        bars_1200 = provider_pinned_1200.get_historical_bars("MSFT", BarTimeframe.M1, t_start, t_end)
        assert len(bars_1200) == 1
        assert bars_1200[0].close == Decimal("401.0")

        # Case 3: Pinned vintage at 14:00 UTC -> Sees Revision 2 (Close = 401.5)
        provider_pinned_1400 = ParquetMarketDataProvider(
            storage=storage, as_of_knowledge_time_utc=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
        )
        bars_1400 = provider_pinned_1400.get_historical_bars("MSFT", BarTimeframe.M1, t_start, t_end)
        assert len(bars_1400) == 1
        assert bars_1400[0].close == Decimal("401.5")

    def test_k_exact_decimal_preservation(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario K: Decimal values are preserved exactly without IEEE-754 floating point drift."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        exact_open = Decimal("1.234567890123456789")
        exact_high = Decimal("1.234567890123456799")
        exact_low = Decimal("1.234567890123456779")
        exact_close = Decimal("1.234567890123456785")
        exact_vol = Decimal("987654321.123456789012")

        data = [{
            "event_start_utc": t0,
            "event_end_utc": t1,
            "knowledge_time_utc": t1,
            "open": exact_open,
            "high": exact_high,
            "low": exact_low,
            "close": exact_close,
            "volume": exact_vol,
        }]
        table = make_test_bar_table("HIGH_PREC", "M1", data)
        engine.write_canonical_part(table, "batch_prec_001", "src", "uri", "6" * 64)

        provider = ParquetMarketDataProvider(storage=storage)
        bars = provider.get_historical_bars("HIGH_PREC", BarTimeframe.M1, t0, t1)

        assert len(bars) == 1
        b = bars[0]
        assert b.open == exact_open
        assert b.high == exact_high
        assert b.low == exact_low
        assert b.close == exact_close
        assert b.volume == exact_vol
        assert isinstance(b.close, Decimal)

    def test_l_forward_market_data_feeder_integration(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario L: ForwardMarketDataFeeder successfully consumes provider's historical iterator."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)

        data = [
            {"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t1,
             "open": Decimal("100.0"), "high": Decimal("101.0"), "low": Decimal("99.0"), "close": Decimal("100.5"), "volume": Decimal("10")},
            {"event_start_utc": t1, "event_end_utc": t2, "knowledge_time_utc": t2,
             "open": Decimal("100.5"), "high": Decimal("102.0"), "low": Decimal("100.0"), "close": Decimal("101.5"), "volume": Decimal("15")},
        ]
        table = make_test_bar_table("NVDA", "M1", data)
        engine.write_canonical_part(table, "batch_nvda_001", "src", "uri", "7" * 64)

        provider = ParquetMarketDataProvider(storage=storage)
        bars = provider.get_historical_bars("NVDA", BarTimeframe.M1, t0, t2)
        assert len(bars) == 2

        # Create session identity double for STREAMING_PARQUET_PUMP
        class DummySessionIdentity:
            data_source = FeedSourceType.STREAMING_PARQUET_PUMP
            execution_mode = "LOCAL_SIMULATOR"

        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.STREAMING_PARQUET_PUMP,
            session_identity=DummySessionIdentity(),
            historical_iterator=iter(bars),
        )

        now = datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)
        snap1, age1 = feeder.poll_next_market_snapshot("NVDA", now)
        assert snap1.symbol == "NVDA"
        assert snap1.last_price == Decimal("100.5")
        assert age1 == 0

        snap2, age2 = feeder.poll_next_market_snapshot("NVDA", now)
        assert snap2.symbol == "NVDA"
        assert snap2.last_price == Decimal("101.5")
        assert age2 == 0

    def test_m_get_latest_snapshot_fail_closed_and_derived_mode(self, data_env: Tuple[ParquetStorageEngine, DuckDBStorage]) -> None:
        """Scenario M: get_latest_snapshot fails closed by default; derives snapshot only when explicit."""
        engine, storage = data_env
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

        data = [{"event_start_utc": t0, "event_end_utc": t1, "knowledge_time_utc": t1,
                 "open": Decimal("100.0"), "high": Decimal("102.0"), "low": Decimal("99.0"),
                 "close": Decimal("101.0"), "volume": Decimal("10")}]
        table = make_test_bar_table("AMZN", "M1", data)
        engine.write_canonical_part(table, "batch_amzn_001", "src", "uri", "8" * 64)

        # 1. Default instance: FAILS CLOSED with DataContractError
        provider_default = ParquetMarketDataProvider(storage=storage)
        with pytest.raises(DataContractError, match="TOP_OF_BOOK_UNAVAILABLE"):
            provider_default.get_latest_snapshot("AMZN")

        # 2. Explicit rehearsal derived mode: succeeds with documented offline derivation
        provider_derived = ParquetMarketDataProvider(
            storage=storage, allow_offline_derived_snapshot=True
        )
        snap = provider_derived.get_latest_snapshot("AMZN")
        assert isinstance(snap, MarketDataSnapshot)
        assert snap.symbol == "AMZN"
        assert snap.last_price == Decimal("101.0")
        assert snap.bid == Decimal("101.0") - Decimal("0.0001")
        assert snap.ask == Decimal("101.0") + Decimal("0.0001")
        assert snap.timestamp_utc == t1

        # 3. Missing symbol in derived mode: raises KeyError
        with pytest.raises(KeyError, match="No market data available in storage for symbol: 'UNKNOWN'"):
            provider_derived.get_latest_snapshot("UNKNOWN")
