"""ACASH Paper Trading — Real-Feed Session Supervisor (E3.5).

Wires a concrete ``IMarketDataFeed`` into the ``PaperSessionRunner`` with
strict, fail-closed operational semantics:

- Feed connects  -> journal FEED_CONNECTED (health layer).
- Feed disconnects / loses connection -> FEED_DISCONNECTED and NO further bars
  are admitted to the decision pipeline (a decision made on disconnected data
  is a contract violation, so we halt before journaling any new bar).
- Malformed/malformed-adjacent provider payloads -> recorded, rejected,
  decision pipeline untouched.
- Duplicate bars (idempotent polling) -> the feed itself returns None; if a
  duplicate sneaks through it is rejected via the runner dupe-protection.
- Stale bars -> length of the runner freshness gate; recorded as
  MARKET_BAR_STALE and NO new decision is made.

GOVERNANCE (E3.5):
==================
- This supervisor is EXECUTION/PAPER INFRASTRUCTURE ONLY.
- It never fabricates data. If the feed has nothing fresh it yields nothing.
- It can only feed a PaperSessionRunner in PAPER_ONLY mode (never LIVE).
- The ``PaperSessionRunner`` still owns every decision; the supervisor is a
  transport/orchestration layer only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.paper.feed import (
    FeedBar,
    FeedConnectionError,
    FeedContractError,
    FeedDataValidationError,
    FeedMalformedResponseError,
    IMarketDataFeed,
    feed_bar_to_synthetic_bar,
)
from acash.paper.health import HealthEventKind, PaperHealthMonitor
from acash.paper.journal import JournalEventType, JournalLayer, PaperEventJournal
from acash.paper.runner import PaperSessionRunner


@dataclass
class FeedSupervisorStats:
    """Counter/timing telemetry for one supervised session."""

    connected_at_utc: Optional[datetime] = None
    disconnected_at_utc: Optional[datetime] = None
    poll_count: int = 0
    bars_admitted: int = 0
    bars_rejected: int = 0
    stale_bars: int = 0
    duplicate_bars_skipped: int = 0
    disconnect_count: int = 0
    last_error: Optional[str] = None
    halted: bool = False
    halted_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connected_at_utc": (
                self.connected_at_utc.isoformat() if self.connected_at_utc else None
            ),
            "disconnected_at_utc": (
                self.disconnected_at_utc.isoformat()
                if self.disconnected_at_utc
                else None
            ),
            "poll_count": self.poll_count,
            "bars_admitted": self.bars_admitted,
            "bars_rejected": self.bars_rejected,
            "stale_bars": self.stale_bars,
            "duplicate_bars_skipped": self.duplicate_bars_skipped,
            "disconnect_count": self.disconnect_count,
            "last_error": self.last_error,
            "halted": self.halted,
            "halted_reason": self.halted_reason,
        }


class PaperFeedSessionSupervisor:
    """Supervise a real-feed paper session with fail-closed semantics.

    Responsibilities:
    - Connect/disconnect the feed (and journal the transitions).
    - Poll once per step, admit exactly the bars that are fresh and valid, and
      reject/record everything else.
    - Halt the session on feed disconnection (no decisions on disconnected
      data) — a fresh reconnect + explicit resume is required afterwards.
    - Delegate every trading decision to the PaperSessionRunner (strategy,
      risk, fill, portfolio all stay in the runner).
    """

    def __init__(
        self,
        feed: IMarketDataFeed,
        runner: PaperSessionRunner,
        health: PaperHealthMonitor,
        journal: PaperEventJournal,
        strategy_symbol: str,
        *,
        share_bar: Optional[FeedBar] = None,
    ) -> None:
        if runner.kill_switch_active:
            raise DataContractError(
                "PaperFeedSessionSupervisor: cannot supervise a session whose "
                "kill switch is already active."
            )
        self._feed = feed
        self._runner = runner
        self._health = health
        self._journal = journal
        self._strategy_symbol = strategy_symbol
        self._share_bar = share_bar
        self._stats = FeedSupervisorStats()
        self._resume_count = 0
        self._is_connected = False

    # -- lifecycle ---------------------------------------------------------

    def connect(self) -> None:
        """Connect the feed and journal FEED_CONNECTED."""
        try:
            self._feed.connect()
        except FeedConnectionError as exc:
            self._stats.disconnect_count += 1
            self._stats.last_error = str(exc)
            self._stats.halted = True
            self._stats.halted_reason = "FEED_CONNECT_FAILED"
            cid = self._journal.new_correlation_id()
            self._health.record(
                kind=HealthEventKind.FEED_DISCONNECTED,
                correlation_id=cid,
                payload={
                    "event": "FEED_CONNECT_FAILED",
                    "provider": self._feed.provider_id,
                    "reason": str(exc)[:500],
                    "session_id": self._runner.session_id,
                },
            )
            raise

        self._stats.connected_at_utc = datetime.now(timezone.utc)
        self._stats.disconnected_at_utc = None
        self._stats.halted = False
        self._stats.halted_reason = None
        self._is_connected = True
        cid = self._journal.new_correlation_id()
        self._health.record(
            kind=HealthEventKind.FEED_CONNECTED,
            correlation_id=cid,
            payload={
                "event": "FEED_CONNECTED",
                "provider": self._feed.provider_id,
                "provider_version": self._feed.provider_version,
                "symbol": self._feed.symbol,
                "timeframe": self._feed.timeframe.value,
                "session_id": self._runner.session_id,
            },
        )

    def disconnect(self) -> None:
        """Disconnect the feed idempotently and journal FEED_DISCONNECTED."""
        self._feed.disconnect()
        self._is_connected = False
        self._stats.disconnected_at_utc = datetime.now(timezone.utc)
        self._stats.halted = True
        self._stats.halted_reason = "FEED_DISCONNECTED"
        cid = self._journal.new_correlation_id()
        self._health.record(
            kind=HealthEventKind.FEED_DISCONNECTED,
            correlation_id=cid,
            payload={
                "event": "FEED_DISCONNECTED",
                "provider": self._feed.provider_id,
                "session_id": self._runner.session_id,
            },
        )

    def reconnect(self) -> None:
        """Attempt to reconnect a disconnected feed (idempotent).

        Fails closed: if the reconnect does not succeed, the session stays
        halted and no bars are admitted.
        """
        self._resume_count += 1
        self.connect()
        self._is_connected = True

    # -- step ---------------------------------------------------------------

    def step_once(self) -> Optional[str]:
        """Poll the feed and admit at most one fresh, valid bar.

        Returns the decision correlation_id when a bar was processed by the
        runner, or None otherwise. Raises FeedContractError on a hard feed
        failure (the session remains halted after a disconnect).
        """
        if self._stats.halted:
            # A halted session does not produce new decisions. Silent None is
            # NOT a fabricated outcome — it is an explicit refuse-to-act.
            return None

        self._stats.poll_count += 1
        try:
            bar: Optional[FeedBar] = self._feed.poll_next_bar()
        except FeedConnectionError as exc:
            self._stats.disconnect_count += 1
            self._stats.last_error = str(exc)
            self._stats.halted = True
            self._stats.halted_reason = "FEED_DISCONNECTED"
            cid = self._journal.new_correlation_id()
            self._health.record(
                kind=HealthEventKind.FEED_DISCONNECTED,
                correlation_id=cid,
                payload={
                    "event": "FEED_DISCONNECTED",
                    "provider": self._feed.provider_id,
                    "reason": str(exc)[:500],
                    "session_id": self._runner.session_id,
                },
            )
            raise
        except (FeedMalformedResponseError, FeedDataValidationError) as exc:
            # Malformed provider data: record + reject, leave pipeline intact.
            self._stats.bars_rejected += 1
            self._stats.last_error = str(exc)
            cid = self._journal.new_correlation_id()
            self._record_bar_rejected(
                correlation_id=cid,
                reason=str(exc)[:250],
                provider=self._feed.provider_id,
            )
            return None

        if bar is None:
            # Idempotent polling: no new bar exists yet. Not an error.
            self._stats.duplicate_bars_skipped += 1
            return None

        self._stats.bars_admitted += 1
        synthetic = feed_bar_to_synthetic_bar(bar, self._strategy_symbol)
        return self._runner.process_bar(synthetic)

    def _record_bar_rejected(
        self,
        correlation_id: str,
        reason: str,
        provider: str,
    ) -> None:
        """Journal a MARKET_BAR_REJECTED event on the SYSTEM layer."""
        self._journal.append(
            event_type=JournalEventType.MARKET_BAR_REJECTED,
            layer=JournalLayer.SYSTEM,
            event_time_utc=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            component="PaperFeedSessionSupervisor",
            payload={
                "event": "MARKET_BAR_REJECTED",
                "provider": provider,
                "reason": reason,
                "session_id": self._runner.session_id,
            },
        )

    # -- observability ------------------------------------------------------

    @property
    def stats(self) -> FeedSupervisorStats:
        return self._stats

    @property
    def feed(self) -> IMarketDataFeed:
        return self._feed

    @property
    def resumed(self) -> bool:
        return self._resume_count > 0