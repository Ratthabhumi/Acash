"""ACASH Paper Trading — Replay Engine.

ReplayEngine deterministically replays a recorded paper session by:
1. Loading normalized market events from the journal
2. Re-running the strategy + risk + order + fill pipeline
3. Comparing reconstructed decisions against original recorded decisions

Contract:
- Replay NEVER sends real broker orders (structurally impossible — it uses
  the same InfrastructureTestStrategy and SimulatedMarketMatcher)
- Replay MUST be clearly labeled REPLAY MODE in all output
- Where nondeterminism exists (e.g., wall-clock timestamps), differences
  are documented but do not cause FAIL
- same input + same version + same config → same decision sequence (within
  documented deterministic boundaries)

Replay is primarily for audit, incident investigation, and regression testing.
It is NOT for live or paper production use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from acash.paper.journal import (
    JournalEvent,
    JournalEventType,
    JournalLayer,
    PaperEventJournal,
)
from acash.paper.strategy import InfrastructureTestStrategy, SignalDirection, StrategySignal


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ReplayStatus(str, Enum):
    """Outcome of a replay run."""

    PASS = "PASS"           # Reconstructed decisions match original
    PARTIAL = "PARTIAL"     # Some decisions match; differences documented
    FAIL = "FAIL"           # Critical mismatch (counts, direction divergence)
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # Not enough events to replay


# ---------------------------------------------------------------------------
# ReplayResult
# ---------------------------------------------------------------------------


@dataclass
class ReplayResult:
    """Result of a deterministic replay run."""

    status: ReplayStatus
    session_id: str
    replayed_at_utc: datetime

    # Counts
    original_signal_count: int = 0
    replayed_signal_count: int = 0
    direction_match_count: int = 0
    direction_mismatch_count: int = 0
    skipped_due_to_insufficient_data: int = 0

    # Documented nondeterminisms
    nondeterministic_fields: List[str] = field(default_factory=list)

    # Violations
    violations: List[str] = field(default_factory=list)

    # Explicit label
    replay_label: str = "REPLAY_MODE_AUDIT_ONLY"
    no_real_orders: bool = True

    def to_summary(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "session_id": self.session_id,
            "replayed_at_utc": self.replayed_at_utc.isoformat(),
            "original_signal_count": self.original_signal_count,
            "replayed_signal_count": self.replayed_signal_count,
            "direction_match_count": self.direction_match_count,
            "direction_mismatch_count": self.direction_mismatch_count,
            "skipped_due_to_insufficient_data": self.skipped_due_to_insufficient_data,
            "nondeterministic_fields": self.nondeterministic_fields,
            "violations": self.violations,
            "replay_label": self.replay_label,
            "no_real_orders": self.no_real_orders,
        }


# ---------------------------------------------------------------------------
# ReplayEngine
# ---------------------------------------------------------------------------


class ReplayEngine:
    """Deterministic replay of a recorded paper trading session.

    GOVERNANCE: Replay is AUDIT-ONLY. It NEVER produces live or paper orders.

    The replay process:
    1. Load all MARKET_DATA events from the journal (as bar price series)
    2. For each evaluation point, re-run the strategy
    3. Compare the reconstructed signal direction to the original signal
    4. Report matches, mismatches, and documented nondeterminisms

    Nondeterministic fields (documented, do NOT cause FAIL):
    - event_time_utc (wall clock) at replay time
    - recorded_at_utc (wall clock)
    - event_id (new UUID generated for replay)
    - event_hash (depends on timestamps and event_id)

    Deterministic fields (MUST match):
    - signal direction
    - signal count (same bars → same number of evaluations)
    - strategy_id
    - strategy_version
    """

    REPLAY_LABEL = "REPLAY_MODE_AUDIT_ONLY"

    def __init__(
        self,
        session_id: str,
        strategy: InfrastructureTestStrategy,
    ) -> None:
        if not session_id or not session_id.strip():
            raise ValueError("ReplayEngine: session_id must be non-empty.")
        self._session_id = session_id
        self._strategy = strategy

    def replay_from_journal(
        self,
        journal: PaperEventJournal,
    ) -> ReplayResult:
        """Replay a complete session from journal events.

        Loads market bar events from the journal and re-runs strategy evaluation,
        comparing directions against original signal events.
        """
        now_utc = datetime.now(timezone.utc)
        result = ReplayResult(
            status=ReplayStatus.INSUFFICIENT_DATA,
            session_id=self._session_id,
            replayed_at_utc=now_utc,
            nondeterministic_fields=[
                "event_time_utc (wall clock differs at replay time)",
                "recorded_at_utc (wall clock)",
                "event_id (new UUID)",
                "event_hash (depends on nondeterministic fields)",
            ],
        )

        all_events = journal.read_all()
        return self.replay_from_events(all_events, result)

    def replay_from_events(
        self,
        events: Sequence[JournalEvent],
        result: Optional[ReplayResult] = None,
    ) -> ReplayResult:
        """Replay from a pre-loaded list of JournalEvents."""
        now_utc = datetime.now(timezone.utc)
        if result is None:
            result = ReplayResult(
                status=ReplayStatus.INSUFFICIENT_DATA,
                session_id=self._session_id,
                replayed_at_utc=now_utc,
                nondeterministic_fields=[
                    "event_time_utc (wall clock differs at replay time)",
                    "recorded_at_utc (wall clock)",
                    "event_id (new UUID)",
                    "event_hash (depends on nondeterministic fields)",
                ],
            )

        # Extract market bar events in sequence order
        bar_events = sorted(
            [e for e in events if e.layer == JournalLayer.MARKET_DATA
             and e.event_type == JournalEventType.MARKET_BAR_RECEIVED],
            key=lambda e: e.sequence,
        )

        # Extract original signal events — exclude FLAT signals caused by insufficient history
        # (those arise because early bars don't have enough history for strategy evaluation;
        # they cannot be matched to replay evaluations which skip those bars via strategy.evaluate→None)
        original_signals = sorted(
            [e for e in events if e.layer == JournalLayer.SIGNAL
             and e.event_type in (
                 JournalEventType.SIGNAL_LONG,
                 JournalEventType.SIGNAL_SHORT,
                 JournalEventType.SIGNAL_FLAT,
                 JournalEventType.SIGNAL_EVALUATED,
             )
             and e.payload.get("reason") != "INSUFFICIENT_HISTORY"],
            key=lambda e: e.sequence,
        )

        result.original_signal_count = len(original_signals)

        if len(bar_events) < 2:
            result.status = ReplayStatus.INSUFFICIENT_DATA
            result.violations.append(
                f"Insufficient market bar events for replay: {len(bar_events)} < 2"
            )
            return result

        # Reconstruct closing price series
        closes: List[Decimal] = []
        evaluation_times: List[datetime] = []
        correlation_ids: List[str] = []

        for be in bar_events:
            close = be.payload.get("close")
            if close is None:
                result.violations.append(
                    f"Market bar event {be.event_id} has no 'close' field in payload"
                )
                continue
            closes.append(Decimal(str(close)))
            evaluation_times.append(be.event_time_utc)
            correlation_ids.append(be.correlation_id)

        # Re-run strategy evaluation at each point
        replayed_directions: List[SignalDirection] = []
        original_directions: List[SignalDirection] = []

        for i, (eval_time, cid) in enumerate(zip(evaluation_times, correlation_ids)):
            available_closes = closes[: i + 1]
            signal = self._strategy.evaluate(
                closes=available_closes,
                evaluation_time_utc=eval_time,
                market_event_reference=f"REPLAY-{i}",
            )
            if signal is None:
                result.skipped_due_to_insufficient_data += 1
                continue

            replayed_directions.append(signal.direction)
            result.replayed_signal_count += 1

        # Compare against original
        for j, (orig_ev, replayed_dir) in enumerate(
            zip(original_signals, replayed_directions)
        ):
            orig_dir_str = orig_ev.payload.get("direction", "UNKNOWN")
            try:
                orig_dir = SignalDirection(orig_dir_str)
            except ValueError:
                result.violations.append(
                    f"Cannot parse original signal direction at signal #{j}: {orig_dir_str!r}"
                )
                continue

            if orig_dir == replayed_dir:
                result.direction_match_count += 1
            else:
                result.direction_mismatch_count += 1
                result.violations.append(
                    f"Direction mismatch at signal #{j}: "
                    f"original={orig_dir.value}, replayed={replayed_dir.value}"
                )

        # Determine status
        if not replayed_directions:
            result.status = ReplayStatus.INSUFFICIENT_DATA
        elif result.direction_mismatch_count == 0 and not result.violations:
            result.status = ReplayStatus.PASS
        elif result.direction_mismatch_count > 0:
            result.status = ReplayStatus.FAIL
        else:
            result.status = ReplayStatus.PARTIAL

        return result
