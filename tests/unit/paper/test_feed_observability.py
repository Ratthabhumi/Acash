"""Comprehensive Regression and Adversarial Tests for Feed Observability and Diagnostics.

Validates the Feed Resilience & Observability contract:
1. Successful feed connection
2. Successful normal bar read
3. ReadTimeout classification
4. Connection error classification
5. HTTP error classification (e.g. 429 rate limit)
6. Reconnect attempt instrumentation (RECOVERY_ATTEMPTED)
7. Successful reconnect instrumentation (FEED_CONNECTED with recovery metadata)
8. Failed reconnect instrumentation (RECOVERY_ATTEMPTED -> FEED_CONNECT_FAILED)
9. Terminal disconnect without recovery
10. No fake FEED_CONNECTED event on reconnect failure
11. Data gap measurement after recovery
12. No market-data decision while disconnected/unhealthy
13. Sensitive credential redaction
14. Fail-closed contract enforcement
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List

import httpx
import pytest

from acash.core.domain.enums import BarTimeframe
from acash.paper.feed import (
    BinancePublicKlinesFeed,
    FeedBar,
    FeedConnectionError,
    sanitize_diagnostic_text,
)
from acash.paper.health import HealthEventKind, PaperHealthMonitor
from acash.paper.journal import JournalEventType, PaperEventJournal
from acash.paper.runner import PaperSessionRunner
from acash.paper.session import PaperFeedSessionSupervisor
from tests.unit.paper.test_paper_e35_real_alpha_feed import make_runner


_SAMPLE_KLINE_ROW: List[Any] = [
    1704441600000,       # 0: Open time
    "42000.00",          # 1: Open
    "42100.00",          # 2: High
    "41950.00",          # 3: Low
    "42050.00",          # 4: Close
    "123.456",           # 5: Volume
    1704441659999,       # 6: Close time
    "5191334.40",        # 7: Quote asset volume
    42,                  # 8: Number of trades
    "60.123",            # 9: Taker buy base volume
    "2528170.80",        # 10: Taker buy quote volume
    "0",                 # 11: Ignore
]


def _make_mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(handler=handler),
        timeout=httpx.Timeout(10.0, connect=5.0, read=10.0),
    )


@pytest.fixture
def session_env(tmp_path: Path) -> Dict[str, Any]:
    session_id = "test-feed-obs-session"
    journal_path = tmp_path / f"{session_id}.journal.jsonl"
    snapshot_path = tmp_path / f"{session_id}.snapshots.jsonl"
    runner = make_runner(
        session_id,
        journal_path,
        snapshot_path,
    )
    runner.start()
    journal = runner.journal
    health = PaperHealthMonitor(
        journal=journal,
        session_id=session_id,
        component_version="0.1.0-test",
    )
    return {
        "session_id": session_id,
        "runner": runner,
        "journal": journal,
        "health": health,
        "journal_path": journal_path,
    }


class TestFeedObservabilityAndDiagnostics:
    """Tests covering feed diagnostics, failure classification, and recovery auditing."""

    def test_successful_feed_connection_and_bar_read(self, session_env: Dict[str, Any]) -> None:
        """Scenario 1 & 2: Successful connect and normal bar read tracks last_bar_utc."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[_SAMPLE_KLINE_ROW])

        client = _make_mock_client(handler)
        feed = BinancePublicKlinesFeed("BTCUSDT", BarTimeframe.M1, client=client)
        supervisor = PaperFeedSessionSupervisor(
            feed=feed,
            runner=session_env["runner"],
            health=session_env["health"],
            journal=session_env["journal"],
            strategy_symbol="BTCUSDT",
        )
        supervisor.connect()

        events = session_env["journal"].read_all()
        connect_events = [e for e in events if e.event_type == JournalEventType.FEED_CONNECTED]
        assert len(connect_events) == 1
        assert connect_events[0].payload["event"] == "FEED_CONNECTED"
        assert connect_events[0].payload["provider"] == "binance.public.klines"
        assert connect_events[0].payload["symbol"] == "BTCUSDT"

        cid = supervisor.step_once()
        assert cid is not None
        assert feed._last_bar_utc is not None

    def test_read_timeout_classification(self) -> None:
        """Scenario 3: ReadTimeout is properly classified with error_class, category, and timeout."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("The read operation timed out")

        client = _make_mock_client(handler)
        feed = BinancePublicKlinesFeed("BTCUSDT", BarTimeframe.M1, client=client)
        feed._is_connected = True  # simulate already connected

        with pytest.raises(FeedConnectionError) as exc_info:
            feed.poll_next_bar()

        exc = exc_info.value
        assert exc.error_class == "ReadTimeout"
        assert exc.category == "TIMEOUT"
        assert exc.operation == "poll"
        assert exc.timeout_seconds == 10.0
        assert "ReadTimeout" in str(exc)

    def test_connect_error_classification(self) -> None:
        """Scenario 4: Connection error is classified as CONNECTION_ERROR."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Failed to establish connection")

        client = _make_mock_client(handler)
        feed = BinancePublicKlinesFeed("BTCUSDT", BarTimeframe.M1, client=client)

        with pytest.raises(FeedConnectionError) as exc_info:
            feed.connect()

        exc = exc_info.value
        assert exc.error_class == "ConnectError"
        assert exc.category == "CONNECTION_ERROR"
        assert exc.operation == "connect"
        assert exc.timeout_seconds == 5.0

    def test_http_status_error_classification(self) -> None:
        """Scenario 5: HTTP status 429 rate limit is classified as HTTP_ERROR with status_code."""
        def handler(request: httpx.Request) -> httpx.Response:
            req = httpx.Request("GET", "https://api.binance.com/api/v3/klines")
            resp = httpx.Response(429, json={"code": -1003, "msg": "Way too many requests"}, request=req)
            resp.raise_for_status()
            return resp

        client = _make_mock_client(handler)
        feed = BinancePublicKlinesFeed("BTCUSDT", BarTimeframe.M1, client=client)
        feed._is_connected = True

        with pytest.raises(FeedConnectionError) as exc_info:
            feed.poll_next_bar()

        exc = exc_info.value
        assert exc.error_class == "HTTPStatusError"
        assert exc.category == "HTTP_ERROR"
        assert exc.status_code == 429

    def test_reconnect_attempt_and_success_instrumentation(self, session_env: Dict[str, Any]) -> None:
        """Scenario 6 & 7: Reconnect attempt emits RECOVERY_ATTEMPTED, and success records FEED_CONNECTED."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # Disconnect on step_once poll
                raise httpx.ReadTimeout("Simulated timeout")
            return httpx.Response(200, json=[_SAMPLE_KLINE_ROW])

        client = _make_mock_client(handler)
        feed = BinancePublicKlinesFeed("BTCUSDT", BarTimeframe.M1, client=client)
        supervisor = PaperFeedSessionSupervisor(
            feed=feed,
            runner=session_env["runner"],
            health=session_env["health"],
            journal=session_env["journal"],
            strategy_symbol="BTCUSDT",
        )
        supervisor.connect()

        # Step fails with timeout
        with pytest.raises(FeedConnectionError):
            supervisor.step_once()

        assert supervisor.stats.halted is True
        assert supervisor.stats.halted_reason == "FEED_DISCONNECTED"

        # Explicit operator reconnect
        supervisor.reconnect()

        assert supervisor.stats.halted is False
        assert supervisor.stats.resume_count == 1

        events = session_env["journal"].read_all()
        event_types = [e.event_type for e in events]

        assert JournalEventType.FEED_DISCONNECTED in event_types
        assert JournalEventType.RECOVERY_ATTEMPTED in event_types
        assert event_types.count(JournalEventType.FEED_CONNECTED) == 2

        # Check diagnostic payload of FEED_DISCONNECTED
        disc_ev = [e for e in events if e.event_type == JournalEventType.FEED_DISCONNECTED][0]
        assert disc_ev.payload["error_class"] == "ReadTimeout"
        assert disc_ev.payload["category"] == "TIMEOUT"
        assert disc_ev.payload["operation"] == "poll"

        # Check RECOVERY_ATTEMPTED payload
        rec_ev = [e for e in events if e.event_type == JournalEventType.RECOVERY_ATTEMPTED][0]
        assert rec_ev.payload["attempt_number"] == 1

        # Check recovered FEED_CONNECTED payload
        conn2_ev = [e for e in events if e.event_type == JournalEventType.FEED_CONNECTED][1]
        assert conn2_ev.payload["is_recovery"] is True
        assert conn2_ev.payload["resume_count"] == 1

    def test_failed_reconnect_emits_recovery_attempt_and_fails_closed(self, session_env: Dict[str, Any]) -> None:
        """Scenario 8 & 10: Reconnect failure logs RECOVERY_ATTEMPTED -> FEED_CONNECT_FAILED, no fake CONNECTED."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Network still dead")

        client = _make_mock_client(handler)
        feed = BinancePublicKlinesFeed("BTCUSDT", BarTimeframe.M1, client=client)
        supervisor = PaperFeedSessionSupervisor(
            feed=feed,
            runner=session_env["runner"],
            health=session_env["health"],
            journal=session_env["journal"],
            strategy_symbol="BTCUSDT",
        )

        with pytest.raises(FeedConnectionError):
            supervisor.reconnect()

        assert supervisor.stats.halted is True
        assert supervisor.stats.halted_reason == "FEED_CONNECT_FAILED"

        events = session_env["journal"].read_all()
        event_types = [e.event_type for e in events]
        assert JournalEventType.RECOVERY_ATTEMPTED in event_types
        assert JournalEventType.FEED_CONNECTED not in event_types  # NO FAKE EVENT
        assert JournalEventType.FEED_DISCONNECTED in event_types

    def test_no_market_data_decision_while_disconnected(self, session_env: Dict[str, Any]) -> None:
        """Scenario 9 & 12: While disconnected / halted, step_once strictly refuses to act."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Timeout")

        client = _make_mock_client(handler)
        feed = BinancePublicKlinesFeed("BTCUSDT", BarTimeframe.M1, client=client)
        feed._is_connected = True
        supervisor = PaperFeedSessionSupervisor(
            feed=feed,
            runner=session_env["runner"],
            health=session_env["health"],
            journal=session_env["journal"],
            strategy_symbol="BTCUSDT",
        )
        with pytest.raises(FeedConnectionError):
            supervisor.step_once()

        assert supervisor.stats.halted is True
        # Further step_once calls return None without raising or evaluating strategy
        assert supervisor.step_once() is None
        assert supervisor.step_once() is None

    def test_data_gap_measurement_after_recovery(self, session_env: Dict[str, Any]) -> None:
        """Scenario 11: Data gap between pre-disconnect and post-recovery bar is measured."""
        row1 = list(_SAMPLE_KLINE_ROW)
        row1[0] = 1704441600000  # T0
        row1[6] = 1704441659999

        row2 = list(_SAMPLE_KLINE_ROW)
        row2[0] = 1704441600000 + 300000  # T0 + 5 minutes gap
        row2[6] = 1704441659999 + 300000

        current_row = row1

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[current_row])

        client = _make_mock_client(handler)
        feed = BinancePublicKlinesFeed("BTCUSDT", BarTimeframe.M1, client=client)
        supervisor = PaperFeedSessionSupervisor(
            feed=feed,
            runner=session_env["runner"],
            health=session_env["health"],
            journal=session_env["journal"],
            strategy_symbol="BTCUSDT",
        )
        supervisor.connect()
        supervisor.step_once()

        # Switch to row 2 after a gap
        current_row = row2
        supervisor.step_once()

        assert supervisor.stats.last_gap_seconds == 300.0  # 5 minutes gap captured

    def test_credential_redaction(self) -> None:
        """Scenario 13: Secrets, tokens, and basic auth are cleanly scrubbed from diagnostic strings."""
        dirty = "Error from https://apiuser:SuperSecretPassword123@api.binance.com?api_key=myApiKey999 with Bearer eyJhbGciOi"
        clean = sanitize_diagnostic_text(dirty)
        assert "SuperSecretPassword123" not in clean
        assert "myApiKey999" not in clean
        assert "eyJhbGciOi" not in clean
        assert clean == "Error from https://apiuser:***@api.binance.com?api_key=*** with Bearer ***"
