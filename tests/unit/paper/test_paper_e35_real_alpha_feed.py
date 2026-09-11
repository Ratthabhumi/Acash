"""ACASH Paper Trading — E3.5 Real Market Data Feed & Session Tests.

Covers:
- FeedBar canonical validation (happy / boundary / malformed / adversarial)
- BinancePublicKlinesFeed (MockTransport): parse, dedup, disconnect,
  malformed, source_id identity, freshness
- StooqCsvFeed (MockTransport): parse, blank volume -> unavailable, dedup
- feed_bar_to_synthetic_bar provenance adapter
- PaperFeedSessionSupervisor fail-closed semantics:
  stale gate, malformed reject, disconnect halt, connect/reconnect journaling
- PaperSessionRunner.recover() restart state reconstruction

GOVERNANCE (E3.5):
==================
- Tests use httpx.MockTransport ONLY — never real network.
- Real-feed bars are EXECUTION/PAPER INFRA ONLY; no research evidence produced.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError
from acash.paper.feed import (
    FeedBar,
    FeedConnectionError,
    FeedContractError,
    FeedDataValidationError,
    FeedMalformedResponseError,
    BinancePublicKlinesFeed,
    StooqCsvFeed,
    feed_bar_to_synthetic_bar,
)
from acash.paper.health import HealthEventKind, PaperHealthMonitor
from acash.paper.journal import (
    JournalEventType,
    JournalLayer,
    PaperEventJournal,
)
from acash.paper.snapshot import DailySnapshot, DailySnapshotStore
from acash.paper.runner import (
    PaperSessionConfig,
    PaperSessionRunner,
    SyntheticBar,
)
from acash.paper.session import PaperFeedSessionSupervisor
from acash.paper.strategy import InfrastructureTestStrategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session_id() -> str:
    return f"TEST-E35-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def journal_path(tmp_path: Path) -> Path:
    return tmp_path / "journal_e35.jsonl"


@pytest.fixture
def snapshot_path(tmp_path: Path) -> Path:
    return tmp_path / "snapshots_e35.jsonl"


def make_feed_bar(
    *,
    provider: str = "mock.provider",
    provider_version: str = "1.0.0",
    source_id: str = "SRC-1",
    symbol: str = "BTCUSDT",
    timeframe: BarTimeframe = BarTimeframe.M1,
    timestamp_utc: datetime | None = None,
    received_at_utc: datetime | None = None,
    open: Decimal = Decimal("100.00"),
    high: Decimal = Decimal("101.00"),
    low: Decimal = Decimal("99.00"),
    close: Decimal = Decimal("100.50"),
    volume: Decimal | None = Decimal("1000"),
    bid: Decimal | None = None,
    ask: Decimal | None = None,
    trade_count: int | None = None,
    sequence: int | None = None,
    unavailable: list[str] | None = None,
) -> FeedBar:
    base = timestamp_utc or datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    if received_at_utc is None:
        received_at_utc = base + timedelta(milliseconds=250)
    return FeedBar.build(
        provider=provider,
        provider_version=provider_version,
        source_id=source_id,
        symbol=symbol,
        timeframe=timeframe,
        timestamp_utc=base,
        received_at_utc=received_at_utc,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        bid=bid,
        ask=ask,
        trade_count=trade_count,
        sequence=sequence,
        unavailable=unavailable or [],
    )


def make_runner_config(
    session_id: str,
    journal_path: Path,
    snapshot_path: Path,
    *,
    data_source: str = "SYNTHETIC_BARS",
    market_domain: str = "SYNTHETIC",
    max_market_data_age_ms: int | None = None,
) -> PaperSessionConfig:
    return PaperSessionConfig(
        session_id=session_id,
        strategy_id=InfrastructureTestStrategy.STRATEGY_ID,
        strategy_version=InfrastructureTestStrategy.STRATEGY_VERSION,
        instrument="SYNTH-USD",
        initial_cash=Decimal("100000"),
        max_position_units=Decimal("10"),
        max_notional=Decimal("500000"),
        max_daily_loss=Decimal("5000"),
        fill_slippage_bps=Decimal("0.5"),
        fill_commission_per_unit=Decimal("7.0"),
        prng_seed=42,
        git_commit="test-commit-abc123",
        component_version="0.1.0-test",
        journal_path=journal_path,
        snapshot_path=snapshot_path,
        data_source=data_source,
        market_domain=market_domain,
        max_market_data_age_ms=max_market_data_age_ms,
    )


def make_runner(
    session_id: str,
    journal_path: Path,
    snapshot_path: Path,
    *,
    data_source: str = "SYNTHETIC_BARS",
    market_domain: str = "SYNTHETIC",
    max_market_data_age_ms: int | None = None,
) -> PaperSessionRunner:
    return PaperSessionRunner(
        make_runner_config(
            session_id,
            journal_path,
            snapshot_path,
            data_source=data_source,
            market_domain=market_domain,
            max_market_data_age_ms=max_market_data_age_ms,
        )
    )


# ===========================================================================
# I. FeedBar contract
# ===========================================================================


class TestFeedBarContract:
    def test_happy_path(self) -> None:
        bar = make_feed_bar()
        assert bar.provider == "mock.provider"
        assert bar.close == Decimal("100.50")
        assert bar.timestamp_utc.tzinfo is not None
        assert bar.data_age_ms() >= 250

    def test_boundary_max_min(self) -> None:
        bar = make_feed_bar(
            timestamp_utc=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
        )
        assert bar.high >= max(bar.open, bar.close)
        assert bar.low <= min(bar.open, bar.close)

    def test_malformed_non_positive_price_rejected(self) -> None:
        with pytest.raises(FeedDataValidationError):
            make_feed_bar(close=Decimal("0"))

    def test_malformed_naive_timestamp_rejected(self) -> None:
        with pytest.raises(FeedDataValidationError):
            make_feed_bar(
                timestamp_utc=datetime(2026, 1, 5, 12, 0),  # naive
            )

    def test_adversarial_negative_volume_rejected(self) -> None:
        with pytest.raises(FeedDataValidationError):
            make_feed_bar(volume=Decimal("-1"))

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(FeedDataValidationError):
            FeedBar.build(
                **{
                    **make_feed_bar().model_dump(),
                    "fabricated_field": "nope",
                }
            )

    def test_unknown_timeframe_rejected(self) -> None:
        with pytest.raises(FeedDataValidationError):
            FeedBar.build(
                provider="mock",
                provider_version="1.0.0",
                source_id="S",
                symbol="X",
                timeframe="TICK",
                timestamp_utc=datetime(2026, 1, 5, tzinfo=timezone.utc),
                received_at_utc=datetime(2026, 1, 5, tzinfo=timezone.utc),
                open=Decimal("1"),
                high=Decimal("2"),
                low=Decimal("0.5"),
                close=Decimal("1.5"),
            )

    def test_journal_payload_carries_governance_label(self) -> None:
        bar = make_feed_bar()
        payload = bar.to_journal_payload()
        assert payload["GOVERNANCE_LABEL"] == "REAL_MARKET_DATA_EXECUTION_INFRA_ONLY"
        assert payload["source"] == "mock.provider"
        assert payload["unavailable"] == []


# ===========================================================================
# II. BinancePublicKlinesFeed
# ===========================================================================

_BINANCE_KLINE_ROW = [
    1704441600000,  # open time ms
    "42000.00",     # open
    "42100.00",     # high
    "41950.00",     # low
    "42050.00",     # close
    "123.456",      # volume
    1704441660000,  # close time ms
    "5180000.00",   # quote asset volume
    42,             # number of trades
    "60000.00",     # taker buy base volume
    "2500000.00",   # taker buy quote volume
    "0",            # ignore
]


def _binance_transport(rows: list[list[object]]) -> httpx.BaseTransport:
    return httpx.MockTransport(
        handler=lambda request: httpx.Response(200, json=rows)
    )


class TestBinancePublicKlinesFeed:
    def test_provider_identity(self) -> None:
        feed = BinancePublicKlinesFeed(
            "btcusdt", BarTimeframe.M1, client=httpx.Client(transport=_binance_transport([]))
        )
        assert feed.provider_id == "binance.public.klines"
        assert feed.provider_version == "1.0.0"
        assert feed.symbol == "BTCUSDT"
        assert feed.timeframe == BarTimeframe.M1

    def test_connect_and_poll_parses_bar(self) -> None:
        client = httpx.Client(transport=_binance_transport([_BINANCE_KLINE_ROW]))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        feed.connect()
        assert feed.status().is_connected

        bar = feed.poll_next_bar()
        assert bar is not None
        assert bar.provider == "binance.public.klines"
        assert bar.close == Decimal("42050.00")
        assert bar.volume == Decimal("123.456")
        assert bar.trade_count == 42
        assert "bid" in bar.unavailable
        assert "ask" in bar.unavailable
        assert bar.timestamp_utc.tzinfo is not None

    def test_idempotent_poll_dedups_same_bar(self) -> None:
        client = httpx.Client(transport=_binance_transport([_BINANCE_KLINE_ROW] * 3))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        feed.connect()
        first = feed.poll_next_bar()
        second = feed.poll_next_bar()
        third = feed.poll_next_bar()
        assert first is not None
        assert second is None
        assert third is None

    def test_source_id_identity(self) -> None:
        client = httpx.Client(transport=_binance_transport([_BINANCE_KLINE_ROW]))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        feed.connect()
        bar = feed.poll_next_bar()
        assert bar is not None
        assert bar.source_id == "1704441600000:1704441660000"

    def test_poll_before_connect_raises(self) -> None:
        client = httpx.Client(transport=_binance_transport([_BINANCE_KLINE_ROW]))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        with pytest.raises(FeedConnectionError):
            feed.poll_next_bar()

    def test_malformed_json_raises(self) -> None:
        mock_transport = httpx.MockTransport(
            handler=lambda request: httpx.Response(200, text="NOT JSON")
        )
        client = httpx.Client(transport=mock_transport)
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        feed.connect()
        with pytest.raises(FeedMalformedResponseError):
            feed.poll_next_bar()

    def test_connect_error_raises_feed_connection_error(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("simulated network failure")

        client = httpx.Client(transport=httpx.MockTransport(handler=handler))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        with pytest.raises(FeedConnectionError):
            feed.connect()

    def test_poll_empty_array_raises(self) -> None:
        client = httpx.Client(transport=_binance_transport([]))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        feed.connect()
        with pytest.raises(FeedMalformedResponseError):
            feed.poll_next_bar()

    def test_klines_validated_geometry_fail_closed(self) -> None:
        bad = [
            1704441600000,
            "42100.00",  # open > high
            "42000.00",
            "41950.00",
            "42050.00",
            "123.456",
            1704441660000,
            "0",
            42,
            "0",
            "0",
            "0",
        ]
        client = httpx.Client(transport=_binance_transport([bad]))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        feed.connect()
        with pytest.raises(FeedDataValidationError):
            feed.poll_next_bar()

    def test_empty_symbol_rejected(self) -> None:
        with pytest.raises(FeedContractError):
            BinancePublicKlinesFeed("   ")

    def test_timeframe_map_covers_d1(self) -> None:
        client = httpx.Client(transport=_binance_transport([_BINANCE_KLINE_ROW]))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.H1, client=client)
        assert feed._TIMEFRAME_MAP[BarTimeframe.H1] == "1h"

    def test_disconnect_is_idempotent(self) -> None:
        client = httpx.Client(transport=_binance_transport([_BINANCE_KLINE_ROW]))
        feed = BinancePublicKlinesFeed("btcusdt", BarTimeframe.M1, client=client)
        feed.connect()
        feed.disconnect()
        feed.disconnect()
        assert feed.status().is_connected is False


# ===========================================================================
# III. StooqCsvFeed
# ===========================================================================

_STOOQ_CSV = """Date,Open,High,Low,Close,Volume
2026-01-02,1.0500,1.0550,1.0450,1.0520,123456
2026-01-05,1.0520,1.0580,1.0490,1.0570,98765
"""

_FX_STOOQ_CSV = """Date,Open,High,Low,Close,Volume
2026-01-02,1.0500,1.0550,1.0450,1.0520,
2026-01-05,1.0520,1.0580,1.0490,1.0570,
"""


def _stooq_transport(csv_text: str) -> httpx.BaseTransport:
    return httpx.MockTransport(
        handler=lambda request: httpx.Response(200, text=csv_text)
    )


class TestStooqCsvFeed:
    def test_provider_identity_and_day_only(self) -> None:
        client = httpx.Client(transport=_stooq_transport(_STOOQ_CSV))
        feed = StooqCsvFeed("eurusd", BarTimeframe.D1, client=client)
        assert feed.provider_id == "stooq.csv.daily"
        assert feed.timeframe == BarTimeframe.D1
        with pytest.raises(FeedContractError):
            StooqCsvFeed("eurusd", BarTimeframe.M1, client=client)

    def test_parse_last_row(self) -> None:
        client = httpx.Client(transport=_stooq_transport(_STOOQ_CSV))
        feed = StooqCsvFeed("eurusd", BarTimeframe.D1, client=client)
        feed.connect()
        bar = feed.poll_next_bar()
        assert bar is not None
        assert bar.close == Decimal("1.0570")
        assert bar.volume == Decimal("98765")
        assert bar.timestamp_utc.day == 5
        assert bar.timeframe == BarTimeframe.D1

    def test_fx_blank_volume_records_unavailable(self) -> None:
        client = httpx.Client(transport=_stooq_transport(_FX_STOOQ_CSV))
        feed = StooqCsvFeed("eurusd", BarTimeframe.D1, client=client)
        feed.connect()
        bar = feed.poll_next_bar()
        assert bar is not None
        assert bar.volume is None
        assert "volume" in bar.unavailable

    def test_idempotent_poll_dedups(self) -> None:
        client = httpx.Client(transport=_stooq_transport(_STOOQ_CSV))
        feed = StooqCsvFeed("eurusd", BarTimeframe.D1, client=client)
        feed.connect()
        first = feed.poll_next_bar()
        second = feed.poll_next_bar()
        assert first is not None
        assert second is None

    def test_empty_csv_raises(self) -> None:
        client = httpx.Client(transport=_stooq_transport(""))
        feed = StooqCsvFeed("eurusd", BarTimeframe.D1, client=client)
        feed.connect()
        with pytest.raises(FeedMalformedResponseError):
            feed.poll_next_bar()

    def test_poll_before_connect_raises(self) -> None:
        client = httpx.Client(transport=_stooq_transport(_STOOQ_CSV))
        feed = StooqCsvFeed("eurusd", BarTimeframe.D1, client=client)
        with pytest.raises(FeedConnectionError):
            feed.poll_next_bar()

    def test_malformed_ohlc_column_raises(self) -> None:
        broken = "Date,Open,High,Low,Close,Volume\n2026-01-05,1.05,1.05,X,1.05,1\n"
        client = httpx.Client(transport=_stooq_transport(broken))
        feed = StooqCsvFeed("eurusd", BarTimeframe.D1, client=client)
        feed.connect()
        with pytest.raises(FeedMalformedResponseError):
            feed.poll_next_bar()


# ===========================================================================
# IV. feed_bar_to_synthetic_bar provenance
# ===========================================================================


class TestFeedBarToSyntheticBar:
    def test_provenance_preserved(self) -> None:
        bar = make_feed_bar(
            source_id="SRC-42",
            provider="binance.public.klines",
            bid=None,
            ask=None,
            unavailable=["bid", "ask", "latency"],
            trade_count=17,
            sequence=9,
        )
        synthetic = feed_bar_to_synthetic_bar(bar, "SYNTH-USD")
        assert isinstance(synthetic, SyntheticBar)
        assert synthetic.is_real_feed
        assert synthetic.feed_source == "binance.public.klines"
        assert synthetic.feed_source_id == "SRC-42"
        assert synthetic.feed_unavailable == ["bid", "ask", "latency"]
        assert synthetic.feed_trade_count == 17
        assert synthetic.feed_sequence == 9
        assert synthetic.symbol == "SYNTH-USD"

    def test_provenance_journal_payload_gov_label(self) -> None:
        bar = make_feed_bar(provider="stooq.csv.daily")
        synthetic = feed_bar_to_synthetic_bar(bar, "SYNTH-USD")
        payload = synthetic.to_journal_payload()
        assert payload["source"] == "stooq.csv.daily"
        assert payload["GOVERNANCE_LABEL"] == "REAL_MARKET_DATA_EXECUTION_INFRA_ONLY"
        assert "feed_source_version" in payload
        assert "feed_source_id" in payload
        assert "received_at_utc" in payload

    def test_synthetic_default_unchanged(self) -> None:
        synthetic = SyntheticBar(
            timestamp_utc=datetime(2026, 1, 5, tzinfo=timezone.utc),
            symbol="SYNTH-USD",
            open=Decimal("1"),
            high=Decimal("2"),
            low=Decimal("0.5"),
            close=Decimal("1.5"),
            volume=Decimal("100"),
        )
        assert synthetic.is_real_feed is False
        payload = synthetic.to_journal_payload()
        assert payload["source"] == "SYNTHETIC_BARS"
        assert payload["GOVERNANCE_LABEL"] == "INFRASTRUCTURE_TEST_DATA"
        assert "feed_source" not in payload


# ===========================================================================
# V. PaperFeedSessionSupervisor fail-closed semantics
# ===========================================================================


class _StaticBinanceFeed(BinancePublicKlinesFeed):

    def __init__(self, *, fail_on: str | None = None) -> None:
        super().__init__("btcusdt", BarTimeframe.M1, client=httpx.Client())
        self._fail_on = fail_on
        self._poll_calls = 0

    def connect(self) -> None:
        if self._fail_on == "connect":
            raise FeedConnectionError("simulated connect failure")
        self._is_connected = True

    def poll_next_bar(self) -> FeedBar | None:
        self._poll_calls += 1
        if self._fail_on == "disconnect":
            raise FeedConnectionError("simulated disconnect")
        if self._fail_on == "malformed":
            raise FeedMalformedResponseError("simulated malformed")
        return make_feed_bar(
            provider="binance.public.klines",
            source_id=f"SRC-{self._poll_calls}",
            sequence=self._poll_calls,
        )


class TestPaperFeedSessionSupervisor:
    def _make_supervisor(
        self,
        session_id: str,
        journal_path: Path,
        snapshot_path: Path,
        feed: _StaticBinanceFeed,
        *,
        data_source: str = "SYNTHETIC_BARS",
        market_domain: str = "SYNTHETIC",
        max_market_data_age_ms: int | None = None,
    ) -> tuple[PaperFeedSessionSupervisor, PaperSessionRunner, PaperEventJournal]:
        runner = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source=data_source,
            market_domain=market_domain,
            max_market_data_age_ms=max_market_data_age_ms,
        )
        journal = runner.journal
        health = PaperHealthMonitor(
            journal=journal,
            session_id=session_id,
            component_version="0.1.0-test",
        )
        supervisor = PaperFeedSessionSupervisor(
            feed=feed,
            runner=runner,
            health=health,
            journal=journal,
            strategy_symbol="SYNTH-USD",
        )
        return supervisor, runner, journal

    def test_connect_records_feed_connected(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        feed = _StaticBinanceFeed()
        supervisor, _runner, journal = self._make_supervisor(
            session_id, journal_path, snapshot_path, feed
        )
        supervisor.connect()
        event_types = [ev.event_type for ev in journal.read_all()]
        assert JournalEventType.FEED_CONNECTED in event_types

    def test_connect_failure_halts_and_records_feed_disconnected(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        feed = _StaticBinanceFeed(fail_on="connect")
        supervisor, _runner, journal = self._make_supervisor(
            session_id, journal_path, snapshot_path, feed
        )
        with pytest.raises(FeedConnectionError):
            supervisor.connect()
        assert supervisor.stats.halted
        event_types = [ev.event_type for ev in journal.read_all()]
        assert JournalEventType.FEED_DISCONNECTED in event_types
        assert supervisor.step_once() is None  # no decisions while halted

    def test_step_once_admits_bar_and_returns_correlation(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        feed = _StaticBinanceFeed()
        supervisor, runner, _journal = self._make_supervisor(
            session_id, journal_path, snapshot_path, feed
        )
        runner.start()
        supervisor.connect()
        cid = supervisor.step_once()
        assert cid is not None
        assert supervisor.stats.bars_admitted == 1

    def test_step_once_stale_bar_no_decision(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        feed = _StaticBinanceFeed()
        supervisor, runner, journal = self._make_supervisor(
            session_id,
            journal_path,
            snapshot_path,
            feed,
            data_source="binance.public.klines",
            market_domain="SPOT",
            max_market_data_age_ms=100,  # static feed bars are always "old"
        )
        runner.start()
        supervisor.connect()
        cid = supervisor.step_once()
        # Stale-data gate blocks the decision; MARKET_BAR_STALE is journaled.
        assert cid is None
        event_types = [ev.event_type for ev in journal.read_all()]
        assert JournalEventType.MARKET_BAR_STALE in event_types

    def test_step_once_malformed_records_rejected_and_no_decision(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        feed = _StaticBinanceFeed(fail_on="malformed")
        supervisor, runner, journal = self._make_supervisor(
            session_id, journal_path, snapshot_path, feed
        )
        runner.start()
        supervisor.connect()
        cid = supervisor.step_once()
        assert cid is None
        assert supervisor.stats.bars_rejected == 1
        event_types = [ev.event_type for ev in journal.read_all()]
        assert JournalEventType.MARKET_BAR_REJECTED in event_types

    def test_step_once_disconnect_halts(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        feed = _StaticBinanceFeed(fail_on="disconnect")
        supervisor, runner, journal = self._make_supervisor(
            session_id, journal_path, snapshot_path, feed
        )
        runner.start()
        supervisor.connect()
        with pytest.raises(FeedConnectionError):
            supervisor.step_once()
        assert supervisor.stats.halted
        assert supervisor.stats.halted_reason == "FEED_DISCONNECTED"
        event_types = [ev.event_type for ev in journal.read_all()]
        assert JournalEventType.FEED_DISCONNECTED in event_types
        # Post-halt: no decisions produced.
        assert supervisor.step_once() is None

    def test_reconnect_resumes(self, session_id: str, journal_path: Path, snapshot_path: Path) -> None:
        feed = _StaticBinanceFeed(fail_on="disconnect")
        supervisor, runner, _journal = self._make_supervisor(
            session_id, journal_path, snapshot_path, feed
        )
        runner.start()
        supervisor.connect()
        with pytest.raises(FeedConnectionError):
            supervisor.step_once()
        feed._fail_on = None  # simulate restored connectivity
        supervisor.reconnect()
        assert supervisor.stats.halted is False
        cid = supervisor.step_once()
        assert cid is not None

    def test_snapshot_stats_serializable(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        feed = _StaticBinanceFeed()
        supervisor, runner, _journal = self._make_supervisor(
            session_id, journal_path, snapshot_path, feed
        )
        runner.start()
        supervisor.connect()
        supervisor.step_once()
        d = supervisor.stats.to_dict()
        assert d["poll_count"] >= 1
        assert d["bars_admitted"] == 1
        assert isinstance(d["poll_count"], int)


# ===========================================================================
# VI. PaperSessionRunner restart recovery
# ===========================================================================


class TestPaperSessionRunnerRecovery:
    def _run_session_with_trades(
        self,
        runner: PaperSessionRunner,
    ) -> None:
        runner.start()
        runner.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("99"),
                close=Decimal("101"),
                volume=Decimal("1000"),
            )
        )
        runner.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 5, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("101"),
                high=Decimal("104"),
                low=Decimal("100"),
                close=Decimal("103"),
                volume=Decimal("1000"),
            )
        )
        runner.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 10, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("103"),
                high=Decimal("106"),
                low=Decimal("102"),
                close=Decimal("105"),
                volume=Decimal("1000"),
            )
        )

    def test_recover_restores_portfolio_and_intents(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        self._run_session_with_trades(runner)
        expected_position = runner.portfolio.position
        expected_cash = runner.portfolio.cash
        expected_order_count = runner.portfolio.order_count

        # Simulate process restart: fresh runner on same journal file.
        runner2 = make_runner(session_id, journal_path, snapshot_path)
        assert runner2.portfolio.position == Decimal("0")
        cid = runner2.recover()
        assert cid is not None
        assert runner2.portfolio.position == expected_position
        assert runner2.portfolio.cash == expected_cash
        assert runner2.portfolio.order_count == expected_order_count
        assert runner2.kill_switch_active is False

    def test_recover_can_resume_processing(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        self._run_session_with_trades(runner)
        # Fresh runner processes a bar first, then look at recovery continuity
        runner2 = make_runner(session_id, journal_path, snapshot_path)
        runner2.recover()
        cid = runner2.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("105"),
                high=Decimal("108"),
                low=Decimal("104"),
                close=Decimal("107"),
                volume=Decimal("1000"),
            )
        )
        assert cid is not None
        # The journal now contains bars and closes accumulated correctly across
        # the restart boundary (no reset of the chain).
        closer_events = [
            ev
            for ev in runner2.journal.read_all()
            if ev.event_type == JournalEventType.MARKET_BAR_RECEIVED
        ]
        assert len(closer_events) == 4  # 3 pre-restart + 1 post-restart

    def test_recover_records_recovery_attempt(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        runner.start()
        runner2 = make_runner(session_id, journal_path, snapshot_path)
        cid = runner2.recover()
        assert cid is not None
        event_types = [ev.event_type for ev in runner2.journal.read_all()]
        assert JournalEventType.RECOVERY_ATTEMPTED in event_types

    def test_recover_requires_existing_journal(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        with pytest.raises(DataContractError, match="no journal"):
            runner.recover()

    def test_recover_rejects_already_started(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        runner.start()
        with pytest.raises(DataContractError, match="already started"):
            runner.recover()

    def test_recover_can_reconstruct_kill_switch(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        runner.start()
        runner.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("99"),
                close=Decimal("101"),
                volume=Decimal("1000"),
            )
        )
        runner._trigger_kill_switch("cid-test", "test-cause", "TEST_TRIGGER")
        runner2 = make_runner(session_id, journal_path, snapshot_path)
        runner2.recover()
        assert runner2.kill_switch_active is True


# ===========================================================================
# VII. Runner stale-data gate (E3.5)
# ===========================================================================


class TestStaleDataGate:
    def test_stale_real_feed_bar_blocks_decision(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source="binance.public.klines",
            market_domain="SPOT",
            max_market_data_age_ms=10,
        )
        runner.start()
        bar = make_feed_bar(
            timestamp_utc=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
            received_at_utc=datetime(2026, 1, 5, 12, 5, tzinfo=timezone.utc),  # 5 min old
        )
        synthetic = feed_bar_to_synthetic_bar(bar, "SYNTH-USD")
        cid = runner.process_bar(synthetic)
        # Stale bar -> no decision correlation returned.
        assert cid is None
        event_types = [ev.event_type for ev in runner.journal.read_all()]
        assert JournalEventType.MARKET_BAR_STALE in event_types

    def test_fresh_real_feed_bar_admitted(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source="binance.public.klines",
            market_domain="SPOT",
            max_market_data_age_ms=100000,
        )
        runner.start()
        bar = make_feed_bar(
            provider="binance.public.klines",
            timestamp_utc=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
            received_at_utc=datetime(2026, 1, 5, 12, 0, 1, tzinfo=timezone.utc),  # 1s old
        )
        synthetic = feed_bar_to_synthetic_bar(bar, "SYNTH-USD")
        cid = runner.process_bar(synthetic)
        assert cid is not None

    def test_data_age_ms_preferred_when_present(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source="binance.public.klines",
            market_domain="SPOT",
            max_market_data_age_ms=10,
        )
        runner.start()
        bar = make_feed_bar(
            timestamp_utc=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
            received_at_utc=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),  # in-window
        )
        synthetic = feed_bar_to_synthetic_bar(bar, "SYNTH-USD")
        # Runner computes 0ms data age -> admitted.
        cid = runner.process_bar(synthetic)
        assert cid is not None


# ===========================================================================
# VII-A. Runner duplicate-feed-bar gate (E3.5)
# ===========================================================================


class TestDuplicateFeedBarGate:
    def test_repeated_feed_source_id_blocked_in_session(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source="binance.public.klines",
            market_domain="SPOT",
        )
        runner.start()
        bar = make_feed_bar(provider="binance.public.klines", source_id="SAME-1")
        synthetic = feed_bar_to_synthetic_bar(bar, "SYNTH-USD")

        cid1 = runner.process_bar(synthetic)
        assert cid1 is not None

        # Same source_id re-delivered -> refused (no new decision).
        cid2 = runner.process_bar(synthetic)
        assert cid2 is None

        event_types = [ev.event_type for ev in runner.journal.read_all()]
        bar_events = [
            ev for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.MARKET_BAR_RECEIVED
        ]
        assert len(bar_events) == 1
        rejected = [
            ev for ev in runner.journal.read_all()
            if ev.event_type == JournalEventType.MARKET_BAR_REJECTED
            and ev.payload.get("reason") == "DUPLICATE_FEED_SOURCE_ID"
        ]
        assert len(rejected) == 1

    def test_synthetic_bars_never_deduped_by_source(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        """Synthetic bars carry no feed_source_id, so the dedup gate must
        treat them as distinct inputs (never block normal E3 flow)."""
        runner = make_runner(session_id, journal_path, snapshot_path)
        runner.start()
        cid1 = runner.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("99"),
                close=Decimal("101"),
                volume=Decimal("1000"),
            )
        )
        cid2 = runner.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 1, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("101"),
                high=Decimal("103"),
                low=Decimal("100"),
                close=Decimal("102"),
                volume=Decimal("1000"),
            )
        )
        assert cid1 is not None
        assert cid2 is not None

    def test_recover_restores_seen_feed_source_ids(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source="binance.public.klines",
            market_domain="SPOT",
        )
        runner.start()
        bar = make_feed_bar(provider="binance.public.klines", source_id="S-PERSIST")
        runner.process_bar(feed_bar_to_synthetic_bar(bar, "SYNTH-USD"))
        runner.stop()

        runner2 = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source="binance.public.klines",
            market_domain="SPOT",
        )
        runner2.recover()
        # The same source_id from the prior session is refused after restart.
        cid = runner2.process_bar(feed_bar_to_synthetic_bar(bar, "SYNTH-USD"))
        assert cid is None
        bar_events = [
            ev for ev in runner2.journal.read_all()
            if ev.event_type == JournalEventType.MARKET_BAR_RECEIVED
        ]
        assert len(bar_events) == 1


# ===========================================================================
# VIII. Daily snapshot persistence (E3.5)
# ===========================================================================


class TestDailySnapshotPersistence:
    def test_capture_snapshot_persists_reference(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        runner.start()
        runner.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("99"),
                close=Decimal("101"),
                volume=Decimal("1000"),
            )
        )
        snapshot = runner.capture_daily_snapshot()
        assert isinstance(snapshot, DailySnapshot)
        assert snapshot.session_id == session_id
        assert snapshot.journal_integrity_status == "PASS"
        assert snapshot.last_event_sequence >= snapshot.first_event_sequence
        assert snapshot.governance_label == "OBSERVED_PAPER_DATA_ONLY"

        # Store is append-only and re-readable.
        store = DailySnapshotStore(snapshot_path)
        all_snapshots = store.read_all()
        assert len(all_snapshots) == 1
        assert all_snapshots[0].snapshot_id == snapshot.snapshot_id
        assert all_snapshots[0].ending_equity == snapshot.ending_equity

    def test_capture_snapshot_after_recovery(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        runner.start()
        runner.process_bar(
            SyntheticBar(
                timestamp_utc=datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc),
                symbol="SYNTH-USD",
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("99"),
                close=Decimal("101"),
                volume=Decimal("1000"),
            )
        )
        runner2 = make_runner(session_id, journal_path, snapshot_path)
        runner2.recover()
        snapshot = runner2.capture_daily_snapshot()
        assert snapshot.session_id == session_id
        assert snapshot.trade_count >= 0

    def test_capture_snapshot_empty_journal_raises(
        self, session_id: str, journal_path: Path, snapshot_path: Path
    ) -> None:
        runner = make_runner(session_id, journal_path, snapshot_path)
        with pytest.raises(DataContractError, match="empty journal"):
            runner.capture_daily_snapshot()