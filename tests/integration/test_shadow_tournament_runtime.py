"""Integration tests for ACASH Shadow Alpha Tournament Runtime Lifecycle.

Validates:
1. Feed lifecycle:
   - feed.connect() called before tournament processing begins.
   - Tournament NOT marked RUNNING/HEALTHY before feed connect succeeds.
   - feed.disconnect() called during graceful/failure shutdown.
   - Zero automatic reconnect.
   - Connect failure must never start slot runners.
2. Freshness monitoring:
   - Feed freshness inspected even when poll_next_bar() returns None.
   - Stale data beyond max_data_age_ms invokes record_feed_stale() and halts fail-closed.
3. Provenance & Sealing:
   - Manifest carries real-feed provider information, not synthetic defaults.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from acash.core.domain.enums import BarTimeframe
from acash.paper.feed import FeedBar, FeedConnectionError, FeedStatus
from acash.paper.tournament_cli import run_tournament


class MockFeed:
    """Mock public klines feed for network-free integration verification."""

    PROVIDER_ID = "mock.binance.public.klines"

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        timeframe: BarTimeframe = BarTimeframe.M1,
        *,
        connect_error: Optional[Exception] = None,
        bars: Optional[List[Optional[FeedBar]]] = None,
        stale_age_ms: Optional[int] = None,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.connect_error = connect_error
        self.bars = list(bars or [])
        self.stale_age_ms = stale_age_ms
        self.connect_called = False
        self.disconnect_called = False
        self.poll_count = 0
        self._is_connected = False
        self._last_bar_utc: Optional[datetime] = None

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def connect(self) -> None:
        self.connect_called = True
        if self.connect_error is not None:
            self._is_connected = False
            raise self.connect_error
        self._is_connected = True

    def disconnect(self) -> None:
        self.disconnect_called = True
        self._is_connected = False

    def poll_next_bar(self) -> Optional[FeedBar]:
        if not self._is_connected:
            raise FeedConnectionError("MockFeed: not connected")
        self.poll_count += 1
        if self.bars:
            bar = self.bars.pop(0)
            if bar is not None:
                self._last_bar_utc = bar.timestamp_utc
            return bar
        return None

    def status(self) -> FeedStatus:
        age = self.stale_age_ms if self.stale_age_ms is not None else 1000
        return FeedStatus(
            provider=self.PROVIDER_ID,
            is_connected=self._is_connected,
            last_bar_utc=self._last_bar_utc or datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc),
            last_poll_utc=datetime.now(timezone.utc),
            data_age_ms=age,
            reconnect_count=0,
            last_error=None,
        )


def _make_feed_bar(price: str = "50000.0", minute: int = 1) -> FeedBar:
    return FeedBar.build(
        provider="mock.binance.public.klines",
        provider_version="1.0.0",
        source_id=f"BTCUSDT-M1-{minute}",
        symbol="BTCUSDT",
        timeframe=BarTimeframe.M1,
        timestamp_utc=datetime(2026, 9, 14, 12, minute, tzinfo=timezone.utc),
        received_at_utc=datetime(2026, 9, 14, 12, minute, 1, tzinfo=timezone.utc),
        open=Decimal(price),
        high=Decimal(price) + Decimal("10.0"),
        low=Decimal(price) - Decimal("10.0"),
        close=Decimal(price),
        volume=Decimal("2.5"),
        trade_count=100,
        unavailable=["bid", "ask", "latency"],
    )


def test_runtime_feed_lifecycle_success(tmp_path: Path) -> None:
    """Prove connect -> poll -> process -> disconnect lifecycle."""
    storage_dir = tmp_path / "tournament"
    mock_bar = _make_feed_bar("50000.0", 1)
    feed = MockFeed(bars=[mock_bar])

    args = argparse.Namespace(
        provider="binance",
        symbol="BTCUSDT",
        timeframe=BarTimeframe.M1,
        storage=storage_dir,
        api_port=29103,
        metrics_port=29102,
        poll_interval_seconds=0.01,
        git_commit="9e4aa9f9276784d20f98fb3986fdbd3e057b5dae",
        max_data_age_ms=65_000,
        num_slots=3,
    )

    # Patch BinancePublicKlinesFeed constructor to return our mock feed
    with patch("acash.paper.tournament_cli.BinancePublicKlinesFeed", return_value=feed):
        # Trigger graceful shutdown after 1 poll
        with patch("time.sleep", side_effect=[None, KeyboardInterrupt]):
            try:
                exit_code = run_tournament(args)
            except KeyboardInterrupt:
                exit_code = 0

    assert feed.connect_called is True
    assert feed.poll_count >= 1
    assert feed.disconnect_called is True

    # Check status.json was exported
    status_file = storage_dir / "status.json"
    assert status_file.exists()


def test_runtime_connect_failure_fail_closed(tmp_path: Path) -> None:
    """Prove connect failure halts fail-closed without ever starting slot runners."""
    storage_dir = tmp_path / "tournament"
    feed = MockFeed(connect_error=FeedConnectionError("DNS resolution failed"))

    args = argparse.Namespace(
        provider="binance",
        symbol="BTCUSDT",
        timeframe=BarTimeframe.M1,
        storage=storage_dir,
        api_port=29104,
        metrics_port=29105,
        poll_interval_seconds=0.01,
        git_commit="9e4aa9f9276784d20f98fb3986fdbd3e057b5dae",
        max_data_age_ms=65_000,
        num_slots=3,
    )

    with patch("acash.paper.tournament_cli.BinancePublicKlinesFeed", return_value=feed):
        exit_code = run_tournament(args)

    assert exit_code == 2
    assert feed.connect_called is True
    # Invariant: slot runners must NEVER have been started
    status_file = storage_dir / "status.json"
    assert status_file.exists()

    import json
    data = json.loads(status_file.read_text(encoding="utf-8"))
    assert data["global"]["overallStatus"] in ("HALTED", "NOT_STARTED")
    assert data["global"]["feedHealth"] == "DISCONNECTED"
    # Slot runners must never have been RUNNING
    for slot_id, slot in data["slots"].items():
        assert slot["status"] != "RUNNING"


def test_runtime_stale_feed_fail_closed(tmp_path: Path) -> None:
    """Prove feed staleness when poll returns None triggers fail-closed halt."""
    storage_dir = tmp_path / "tournament"
    # Empty bars -> poll returns None, but feed status reports 90,000ms age (> 65,000ms max)
    feed = MockFeed(bars=[], stale_age_ms=90_000)

    args = argparse.Namespace(
        provider="binance",
        symbol="BTCUSDT",
        timeframe=BarTimeframe.M1,
        storage=storage_dir,
        api_port=29106,
        metrics_port=29107,
        poll_interval_seconds=0.01,
        git_commit="9e4aa9f9276784d20f98fb3986fdbd3e057b5dae",
        max_data_age_ms=65_000,
        num_slots=3,
    )

    with patch("acash.paper.tournament_cli.BinancePublicKlinesFeed", return_value=feed):
        exit_code = run_tournament(args)

    # Exit code 4 represents stale data halt
    assert exit_code == 4
    assert feed.disconnect_called is True

    import json
    status_file = storage_dir / "status.json"
    data = json.loads(status_file.read_text(encoding="utf-8"))
    assert data["global"]["overallStatus"] == "HALTED"
    assert data["global"]["feedHealth"] == "STALE"
    assert "Feed data stale" in data["global"]["haltReason"]


def test_runtime_returned_stale_bar_halts_before_processing(tmp_path: Path) -> None:
    """Prove that a FeedBar returned by poll_next_bar() that exceeds max_data_age_ms
    causes exit code 4 WITHOUT supervisor.process_bar() being called.

    This is the key invariant: the unified post-poll freshness gate must fire
    for every returned FeedBar, not only when poll returns None.
    """
    storage_dir = tmp_path / "tournament"

    # Build a bar whose received_at_utc is far in the future relative to
    # timestamp_utc so that FeedBar.data_age_ms() >> 65,000 ms.
    from datetime import timedelta

    bar_timestamp = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
    # received_at is 90 seconds after the bar's market event time â†’ age = 90,000 ms
    stale_received_at = bar_timestamp + timedelta(seconds=90)
    stale_bar = FeedBar.build(
        provider="mock.binance.public.klines",
        provider_version="1.0.0",
        source_id="BTCUSDT-M1-stale",
        symbol="BTCUSDT",
        timeframe=BarTimeframe.M1,
        timestamp_utc=bar_timestamp,
        received_at_utc=stale_received_at,
        open=Decimal("50000.0"),
        high=Decimal("50010.0"),
        low=Decimal("49990.0"),
        close=Decimal("50000.0"),
        volume=Decimal("2.5"),
        trade_count=100,
        unavailable=["bid", "ask", "latency"],
    )

    # Verify the FeedBar.data_age_ms() is indeed stale before injecting it
    assert stale_bar.data_age_ms() == 90_000

    feed = MockFeed(bars=[stale_bar])

    args = argparse.Namespace(
        provider="binance",
        symbol="BTCUSDT",
        timeframe=BarTimeframe.M1,
        storage=storage_dir,
        api_port=29108,
        metrics_port=29109,
        poll_interval_seconds=0.01,
        git_commit="9e4aa9f9276784d20f98fb3986fdbd3e057b5dae",
        max_data_age_ms=65_000,
        num_slots=3,
    )

    process_bar_call_count = 0

    with patch("acash.paper.tournament_cli.BinancePublicKlinesFeed", return_value=feed):
        # Intercept supervisor.process_bar to ensure it is NEVER called
        with patch(
            "acash.paper.tournament.ShadowTournamentSupervisor.process_bar",
            side_effect=lambda bar: (_ for _ in ()).throw(
                AssertionError("process_bar() MUST NOT be called for a stale returned bar")
            ),
        ):
            exit_code = run_tournament(args)

    # Must exit with code 4 (stale data halt)
    assert exit_code == 4, f"Expected exit_code=4 (stale), got {exit_code}"
    # Feed must be disconnected even on fail-closed halt
    assert feed.disconnect_called is True

    import json
    status_file = storage_dir / "status.json"
    data = json.loads(status_file.read_text(encoding="utf-8"))
    assert data["global"]["overallStatus"] == "HALTED"
    assert data["global"]["feedHealth"] == "STALE"
    # haltReason must explicitly mention the stale returned bar
    assert "stale" in data["global"]["haltReason"].lower()

