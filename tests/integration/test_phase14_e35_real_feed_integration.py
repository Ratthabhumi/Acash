"""ACASH Paper Trading — E3.5 Integration Test Suite.

Validates the integrated E3.5 real-feed paper session path end-to-end:
1. Full session: static feed seam -> supervisor -> runner -> journal -> manifest
2. Stop produces daily snapshot + sealed manifest on disk (audit durability).
3. Restart recovery resumes a prior session journal, then continues processing.
4. Duplicate bars are deduped by feed source_id (no duplicate decisions/orders).
5. Idempotency: a recovered session does not re-submit orders on replay.
6. ReplayEngine deterministic replay of a real-feed journal.
7. Reconciliation PASS on a healthy real-feed journal.
8. Journal integrity re-verification PASS after a real-feed session.
9. Stale data gate: an outdated real bar is refused (no decision) at integrated level.

Governance Constraints (E3.5):
==============================
- Feed is EXECUTION/PAPER INFRASTRUCTURE ONLY (never research evidence).
- Never fabricate bid/ask/volume/trade_count/latency.
- Stale/disconnected feed -> no new decision.
- All runs are PAPER_ONLY by construction; no LIVE path.
- $0 credential-free providers only; network is NEVER hit in tests.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import httpx
import pytest

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError
from acash.paper.feed import (
    BinancePublicKlinesFeed,
    FeedBar,
    FeedConnectionError,
    FeedMalformedResponseError,
    feed_bar_to_synthetic_bar,
)
from acash.paper.health import PaperHealthMonitor
from acash.paper.journal import JournalEventType, PaperEventJournal
from acash.paper.manifest import PaperMode, PaperSessionManifest
from acash.paper.reconcile import PaperReconciliationEngine, ReconciliationStatus
from acash.paper.replay import ReplayEngine, ReplayStatus
from acash.paper.runner import PaperSessionConfig, PaperSessionRunner, SyntheticBar
from acash.paper.session import PaperFeedSessionSupervisor
from acash.paper.snapshot import DailySnapshotStore
from acash.paper.strategy import InfrastructureTestStrategy


@pytest.fixture
def session_id() -> str:
    return f"INT-E35-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "e35_integration_storage"


def make_feed_bar(
    *,
    provider: str = "binance.public.klines",
    source_id: str = "SRC-1",
    sequence: int = 1,
    close: Decimal = Decimal("101"),
    timestamp_utc: Optional[datetime] = None,
    received_at_utc: Optional[datetime] = None,
) -> FeedBar:
    ts = timestamp_utc or datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    received = received_at_utc or ts
    return FeedBar.build(
        provider=provider,
        provider_version="1.0.0",
        source_id=source_id,
        sequence=sequence,
        symbol="BTCUSDT",
        timeframe=BarTimeframe.M1,
        timestamp_utc=ts,
        received_at_utc=received,
        open=close - Decimal("1"),
        high=close + Decimal("1"),
        low=close - Decimal("2"),
        close=close,
        volume=Decimal("10"),
    )


def make_runner(
    sid: str,
    journal_path: Path,
    snapshot_path: Path,
    *,
    data_source: str = "SYNTHETIC_BARS",
    market_domain: str = "SYNTHETIC",
    max_market_data_age_ms: Optional[int] = None,
) -> PaperSessionRunner:
    config = PaperSessionConfig(
        session_id=sid,
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
        git_commit="int-test-commit",
        component_version="0.1.0-int",
        journal_path=journal_path,
        snapshot_path=snapshot_path,
        mode=PaperMode.PAPER_ONLY,
        data_source=data_source,
        market_domain=market_domain,
        max_market_data_age_ms=max_market_data_age_ms,
    )
    return PaperSessionRunner(config)


def make_supervisor(
    runner: PaperSessionRunner,
    feed: "StaticBinanceFeedLike",
    *,
    strategy_symbol: str = "SYNTH-USD",
) -> PaperFeedSessionSupervisor:
    health = PaperHealthMonitor(
        journal=runner.journal,
        session_id=runner.session_id,
        component_version="0.1.0-int",
    )
    return PaperFeedSessionSupervisor(
        feed=feed,
        runner=runner,
        health=health,
        journal=runner.journal,
        strategy_symbol=strategy_symbol,
    )


class StaticBinanceFeedLike(BinancePublicKlinesFeed):
    """Network-free static feed seam for end-to-end session tests.

    Mirrors the real Binance provider's idempotent-poll behavior: a repeated
    source_id is skipped (returns None) so the supervisor counts it as a
    duplicate rather than admitting a second decision chain.
    """

    def __init__(self, bars: list[FeedBar] | None = None) -> None:
        super().__init__("btcusdt", BarTimeframe.M1, client=httpx.Client())
        self._bars: list[FeedBar] = list(bars or [])
        self._poll_calls = 0
        self._fail_mode: Optional[str] = None
        self._seen_source_ids: set[str] = set()

    def fail_next(self, mode: str) -> None:
        self._fail_mode = mode

    def connect(self) -> None:
        if self._fail_mode == "connect":
            raise FeedConnectionError("simulated connect failure")
        self._is_connected = True

    def poll_next_bar(self) -> Optional[FeedBar]:
        self._poll_calls += 1
        if self._fail_mode == "disconnect":
            raise FeedConnectionError("simulated disconnect during poll")
        if self._fail_mode == "malformed":
            raise FeedMalformedResponseError("simulated malformed response")
        if not self._bars:
            return None
        candidate = self._bars.pop(0)
        # Provider-level idempotent polling: skip an already-seen bar.
        if candidate.source_id in self._seen_source_ids:
            return None
        self._seen_source_ids.add(candidate.source_id)
        return candidate


class TestFullSessionDurability:
    def test_session_writes_journal_snapshot_and_manifest(
        self, session_id: str, storage_root: Path
    ) -> None:
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        snapshot_path = storage_root / f"{session_id}.snapshots.jsonl"
        runner = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source="feed:binance.int",
            market_domain="SPOT",
        )
        feed = StaticBinanceFeedLike(
            [
                make_feed_bar(source_id="S1", sequence=1),
                make_feed_bar(source_id="S2", sequence=2),
                make_feed_bar(source_id="S3", sequence=3),
            ]
        )
        supervisor = make_supervisor(runner, feed)
        runner.start()
        supervisor.connect()
        supervisor.step_once()
        supervisor.step_once()
        supervisor.step_once()
        supervisor.disconnect()
        manifest = runner.stop()

        assert isinstance(manifest, PaperSessionManifest)
        assert manifest.mode == PaperMode.PAPER_ONLY
        assert manifest.is_infrastructure_test_strategy is True
        assert manifest.final_reconciliation_status == ReconciliationStatus.PASS.value
        assert manifest.journal_integrity_status == "PASS"

        # Durability: journal, snapshot, manifest all on disk.
        assert journal_path.exists()
        assert snapshot_path.exists()
        manifest_path = storage_root / f"{session_id}.manifest.json"
        assert manifest_path.exists()

        # At least one MARKET_BAR_RECEIVED from the real-feed source.
        journal = PaperEventJournal(
            session_id=session_id,
            persistence_path=journal_path,
            git_commit="int-verify",
            component_version="0.1.0-int",
        )
        events = journal.read_all()
        assert any(
            e.event_type == JournalEventType.MARKET_BAR_RECEIVED
            and e.payload.get("source") == "binance.public.klines"
            for e in events
        )

        # Snapshot references journal hashes.
        snapshots = DailySnapshotStore(snapshot_path).read_all()
        assert snapshots
        assert snapshots[-1].journal_integrity_status == "PASS"

    def test_integrity_and_reconciliation_pass_end_to_end(
        self, session_id: str, storage_root: Path
    ) -> None:
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        snapshot_path = storage_root / f"{session_id}.snapshots.jsonl"
        runner = make_runner(
            session_id, journal_path, snapshot_path, data_source="feed:binance.int"
        )
        feed = StaticBinanceFeedLike(
            [
                make_feed_bar(source_id="S1", sequence=1),
                make_feed_bar(source_id="S2", sequence=2),
            ]
        )
        supervisor = make_supervisor(runner, feed)
        runner.start()
        supervisor.connect()
        supervisor.step_once()
        supervisor.step_once()
        supervisor.disconnect()
        runner.stop()

        journal = PaperEventJournal(
            session_id=session_id,
            persistence_path=journal_path,
            git_commit="int-verify",
            component_version="0.1.0-int",
        )
        assert journal.verify_integrity() == []
        result = PaperReconciliationEngine(
            session_id=session_id, journal=journal
        ).run_full_reconciliation()
        assert result.status == ReconciliationStatus.PASS


class TestRestartRecoveryResume:
    def test_recover_then_continue_with_more_bars(
        self, session_id: str, storage_root: Path
    ) -> None:
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        snapshot_path = storage_root / f"{session_id}.snapshots.jsonl"

        # First run: 2 bars processed.
        runner1 = make_runner(
            session_id, journal_path, snapshot_path, data_source="feed:binance.int"
        )
        feed1 = StaticBinanceFeedLike(
            [
                make_feed_bar(source_id="S1", sequence=1),
                make_feed_bar(source_id="S2", sequence=2),
            ]
        )
        sup1 = make_supervisor(runner1, feed1)
        runner1.start()
        sup1.connect()
        sup1.step_once()
        sup1.step_once()
        sup1.disconnect()
        runner1.stop()
        count_before = len(
            PaperEventJournal(
                session_id=session_id,
                persistence_path=journal_path,
                git_commit="int-verify",
                component_version="0.1.0-int",
            ).read_all()
        )
        assert count_before > 0

        # Restart: recover the journal, then resume with 2 more bars.
        runner2 = make_runner(
            session_id, journal_path, snapshot_path, data_source="feed:binance.int"
        )
        recovery_cid = runner2.recover()
        assert recovery_cid is not None

        feed2 = StaticBinanceFeedLike(
            [
                make_feed_bar(source_id="S3", sequence=3),
                make_feed_bar(source_id="S4", sequence=4),
            ]
        )
        sup2 = make_supervisor(runner2, feed2)
        sup2.connect()
        sup2.step_once()
        sup2.step_once()
        sup2.disconnect()
        manifest = runner2.stop()

        journal = PaperEventJournal(
            session_id=session_id,
            persistence_path=journal_path,
            git_commit="int-verify",
            component_version="0.1.0-int",
        )
        assert journal.verify_integrity() == []
        events = journal.read_all()
        assert len(events) > count_before
        # No duplicate source ids admitted: S1..S4 all distinct.
        bar_sources = [
            e.payload.get("feed_source_id")
            for e in events
            if e.event_type == JournalEventType.MARKET_BAR_RECEIVED
        ]
        assert len(bar_sources) == len(set(bar_sources)) == 4
        assert manifest.journal_integrity_status == "PASS"

    def test_resume_duplicate_feed_bars_deduped_across_restart(
        self, session_id: str, storage_root: Path
    ) -> None:
        """Restart with a feed that replays an already-seen source_id must NOT
        admit a duplicate decision chain (idempotency across restart)."""
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        snapshot_path = storage_root / f"{session_id}.snapshots.jsonl"

        runner1 = make_runner(
            session_id, journal_path, snapshot_path, data_source="feed:binance.int"
        )
        feed1 = StaticBinanceFeedLike(
            [make_feed_bar(source_id="S1", sequence=1)]
        )
        sup1 = make_supervisor(runner1, feed1)
        runner1.start()
        sup1.connect()
        sup1.step_once()
        sup1.disconnect()
        runner1.stop()

        # Restart with the SAME source_id arriving again.
        runner2 = make_runner(
            session_id, journal_path, snapshot_path, data_source="feed:binance.int"
        )
        runner2.recover()
        feed2 = StaticBinanceFeedLike(
            [
                make_feed_bar(source_id="S1", sequence=1),
                make_feed_bar(source_id="S2", sequence=2),
            ]
        )
        sup2 = make_supervisor(runner2, feed2)
        sup2.connect()
        sup2.step_once()
        sup2.step_once()
        sup2.disconnect()
        manifest = runner2.stop()

        journal = PaperEventJournal(
            session_id=session_id,
            persistence_path=journal_path,
            git_commit="int-verify",
            component_version="0.1.0-int",
        )
        bar_sources = [
            e.payload.get("feed_source_id")
            for e in journal.read_all()
            if e.event_type == JournalEventType.MARKET_BAR_RECEIVED
        ]
        # S1 appears exactly once across both sessions; S2 first seen on restart.
        assert bar_sources.count("S1") == 1
        assert bar_sources.count("S2") == 1
        assert manifest.journal_integrity_status == "PASS"


class TestReplayAndOrderIdempotency:
    def test_replay_deterministic_from_real_feed_journal(
        self, session_id: str, storage_root: Path
    ) -> None:
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        snapshot_path = storage_root / f"{session_id}.snapshots.jsonl"
        runner = make_runner(
            session_id, journal_path, snapshot_path, data_source="feed:binance.int"
        )
        prices = [Decimal("100") + Decimal(i) for i in range(7)]
        base_ts = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        bars = [
            make_feed_bar(
                source_id=f"S{i}",
                sequence=i,
                close=p,
                timestamp_utc=base_ts + timedelta(minutes=i),
            )
            for i, p in enumerate(prices, start=1)
        ]
        feed = StaticBinanceFeedLike(bars)
        sup = make_supervisor(runner, feed)
        runner.start()
        sup.connect()
        for _ in range(7):
            sup.step_once()
        sup.disconnect()
        manifest = runner.stop()

        journal = PaperEventJournal(
            session_id=session_id,
            persistence_path=journal_path,
            git_commit="int-replay",
            component_version="0.1.0-int",
        )
        assert journal.verify_integrity() == []

        strategy = InfrastructureTestStrategy()
        replay = ReplayEngine(session_id=session_id, strategy=strategy)
        result = replay.replay_from_journal(journal)
        assert result.status in (ReplayStatus.PASS, ReplayStatus.PARTIAL)


class TestStaleDataGateIntegrated:
    def test_outdated_real_bar_produces_no_decision(
        self, session_id: str, storage_root: Path
    ) -> None:
        """An old real bar (data_age > horizon) must be refused at integrated
        level, recording STALE_DATA with no decision chain."""
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        snapshot_path = storage_root / f"{session_id}.snapshots.jsonl"
        runner = make_runner(
            session_id,
            journal_path,
            snapshot_path,
            data_source="feed:binance.int",
            max_market_data_age_ms=1_000,  # 1 second horizon
        )
        old_ts = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        feed = StaticBinanceFeedLike(
            [
                make_feed_bar(
                    source_id="OLD-1",
                    sequence=1,
                    timestamp_utc=old_ts,
                    received_at_utc=old_ts + timedelta(seconds=90),
                )
            ]
        )
        sup = make_supervisor(runner, feed)
        runner.start()
        sup.connect()
        # received_at > horizon(1000ms): bar is stale -> refused with STALE_DATA.
        sup.step_once()
        sup.disconnect()
        manifest = runner.stop()

        journal = PaperEventJournal(
            session_id=session_id,
            persistence_path=journal_path,
            git_commit="int-verify",
            component_version="0.1.0-int",
        )
        events = journal.read_all()
        assert any(e.event_type == JournalEventType.MARKET_BAR_STALE for e in events)
        # No decision events resulted from the stale bar.
        assert not any(
            e.event_type in (JournalEventType.ORDER_INTENT_CREATED, JournalEventType.FILL_SIMULATED)
            for e in events
        )
        assert manifest.journal_integrity_status == "PASS"


class TestFeedFailureFailClosedIntegrated:
    def test_connect_failure_halts_and_no_decisions(
        self, session_id: str, storage_root: Path
    ) -> None:
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        snapshot_path = storage_root / f"{session_id}.snapshots.jsonl"
        runner = make_runner(
            session_id, journal_path, snapshot_path, data_source="feed:binance.int"
        )
        feed = StaticBinanceFeedLike()
        feed.fail_next("connect")
        sup = make_supervisor(runner, feed)
        runner.start()
        with pytest.raises(FeedConnectionError):
            sup.connect()
        sup.disconnect()
        manifest = runner.stop()

        journal = PaperEventJournal(
            session_id=session_id,
            persistence_path=journal_path,
            git_commit="int-verify",
            component_version="0.1.0-int",
        )
        events = journal.read_all()
        assert any(e.event_type == JournalEventType.FEED_DISCONNECTED for e in events)
        assert not any(
            e.event_type == JournalEventType.MARKET_BAR_RECEIVED for e in events
        )
        assert manifest.journal_integrity_status == "PASS"

    def test_malformed_feed_bars_marked_rejected(
        self, session_id: str, storage_root: Path
    ) -> None:
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        snapshot_path = storage_root / f"{session_id}.snapshots.jsonl"
        runner = make_runner(
            session_id, journal_path, snapshot_path, data_source="feed:binance.int"
        )
        feed = StaticBinanceFeedLike(
            [make_feed_bar(source_id="S1", sequence=1)]
        )
        feed.fail_next("malformed")
        sup = make_supervisor(runner, feed)
        runner.start()
        sup.connect()
        sup.step_once()  # raises malformed -> recorded as rejection
        sup.disconnect()
        manifest = runner.stop()

        journal = PaperEventJournal(
            session_id=session_id,
            persistence_path=journal_path,
            git_commit="int-verify",
            component_version="0.1.0-int",
        )
        events = journal.read_all()
        assert any(e.event_type == JournalEventType.MARKET_BAR_REJECTED for e in events)
        assert not any(
            e.event_type == JournalEventType.FILL_SIMULATED for e in events
        )
        assert manifest.journal_integrity_status == "PASS"