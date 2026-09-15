"""ACASH Paper Trading — Controlled Transient Feed Recovery (SHADOW, opt-in).

Fail-closed transient-feed-recovery state machine for the Shadow Alpha
Tournament runtime.

BOUNDARY STATEMENTS (non-negotiable):
======================================
- Recovery applies ONLY to transient ``FeedConnectionError`` (connect or poll).
  Structural contract violations (``FeedContractError``, ``FeedMalformedResponseError``,
  stale-returned-bar trips) are NOT recoverable here; they must keep the original
  immediate fail-closed halt path in the caller.
- A reconnected bar is admitted ONLY when it satisfies both:
    1. continuity: exactly ``last_accepted + timeframe_step`` (a duplicate, a past
       bar, or a forward gap is REJECTED — ACASH never fabricates missing bars), and
    2. freshness: observed data age within ``max_data_age_ms``.
  A rejected bar is final for that recovery episode (INVALID_BAR) — the module
  will not silently retry past a suspect bar.
- Zero trading decisions occur while the tournament is in the FEED_RECOVERING
  state; the supervisor guard is the enforcement point.
- Budget: ``max_attempts`` reconnect attempts with deterministic backoff. Exhaustion
  is a final, explicitly-labeled outcome (BUDGET_EXHAUSTED) — never a silent resume.
- Bar-wait is bounded: once a reconnect succeeds, the episode waits up to
  ``bar_wait_timeout_seconds`` (monotonic deadline) for the first bar. A timeout
  consumes the retry budget for that attempt (BAR_WAIT_TIMEOUT) and applies the
  configured backoff — it is never an unbounded/indefinite wait.
- Backoff indexing is canonical: the delay applied after attempt ``n`` is
  ``backoff_delay_seconds(n, backoff)`` = ``backoff[min(n-1, len-1)]``, and the
  journaled ``backoff_seconds`` value always equals the actual sleep.
- Operator stop is respected at every loop boundary (connect wait and bar wait)
  and yields OPERATOR_STOP (a clean abort, not a failure).
- This mechanism is SHADOW, and CLI recovery is OFF by default: the canonical
  runtime setting is "Automatic Feed Reconnect | DISABLED" (immediate fail-closed
  halt, operator resume required). Operators elect recovery explicitly with
  ``--enable-feed-recovery``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError
from acash.paper.feed import FeedBar, FeedConnectionError, IMarketDataFeed
from acash.paper.metrics import MetricsRegistry


# ---------------------------------------------------------------------------
# State model
# ---------------------------------------------------------------------------


class FeedRecoveryState(str, Enum):
    """Canonical states of one feed-recovery episode.

    IDLE            no recovery episode in progress
    RECOVERING      reconnect attempts / poll wait in progress
    RESUMED         a continuity+freshness-validated bar was found and accepted
    BUDGET_EXHAUSTED all reconnect attempts consumed without a valid bar
    INVALID_BAR     the first returned bar failed continuity/freshness (fail-closed)
    OPERATOR_STOP   operator requested shutdown during the episode (clean abort)
    """

    IDLE = "IDLE"
    RECOVERING = "RECOVERING"
    RESUMED = "RESUMED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    INVALID_BAR = "INVALID_BAR"
    OPERATOR_STOP = "OPERATOR_STOP"


# ---------------------------------------------------------------------------
# Config & result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeedRecoveryConfig:
    """Deterministic bounds for one transient-recovery episode. Fail-closed.

    max_attempts:           reconnects attempted per episode (>= 1).
    backoff_seconds:        per-attempt post-failure delay schedule (>= 0 each;
                            index n-1 applies after attempt n). Zero delays are
                            permitted for deterministic tests; the operator CLI
                            enforces strictly positive delays.
    poll_interval_seconds:  idle poll cadence while waiting for the first bar.
    bar_wait_timeout_seconds: monotonic budget for the first bar after a
                            successful reconnect (must be > 0). A timeout
                            consumes the retry budget of that attempt.
    """

    max_attempts: int = 5
    backoff_seconds: Tuple[float, ...] = (2.0, 5.0, 10.0, 20.0, 30.0)
    poll_interval_seconds: float = 2.0
    bar_wait_timeout_seconds: float = 90.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise DataContractError(
                f"FeedRecoveryConfig: max_attempts must be >= 1, got {self.max_attempts}"
            )
        if len(self.backoff_seconds) == 0:
            raise DataContractError(
                "FeedRecoveryConfig: backoff_seconds must be a non-empty sequence."
            )
        if any(b < 0 for b in self.backoff_seconds):
            raise DataContractError(
                f"FeedRecoveryConfig: backoff_seconds must be >= 0, got {self.backoff_seconds}"
            )
        if self.poll_interval_seconds < 0:
            raise DataContractError(
                "FeedRecoveryConfig: poll_interval_seconds must be >= 0, "
                f"got {self.poll_interval_seconds}"
            )
        if self.bar_wait_timeout_seconds <= 0:
            raise DataContractError(
                "FeedRecoveryConfig: bar_wait_timeout_seconds must be > 0, "
                f"got {self.bar_wait_timeout_seconds}"
            )


# Timeframe -> canonical bar step in seconds. A reconnected bar must be exactly
# one step after the last accepted bar; ACASH never fabricates missing bars.
TIMEFRAME_STEP_SECONDS: Dict[BarTimeframe, int] = {
    BarTimeframe.M1: 60,
    BarTimeframe.M5: 300,
    BarTimeframe.M15: 900,
    BarTimeframe.H1: 3600,
    BarTimeframe.H4: 14400,
    BarTimeframe.D1: 86400,
}


@dataclass(frozen=True)
class FeedRecoveryResult:
    """Outcome of one feed-recovery episode."""

    state: FeedRecoveryState
    attempts_used: int
    reason: Optional[str] = None
    resumed_bar: Optional[FeedBar] = None

    @property
    def success(self) -> bool:
        return self.state == FeedRecoveryState.RESUMED


# ---------------------------------------------------------------------------
# Reconnect-bar validation
# ---------------------------------------------------------------------------


class ReconnectBarVerdict(str, Enum):
    """Validation verdict for the bar returned after a reconnect attempt."""

    ACCEPT = "ACCEPT"
    STALE_BAR = "STALE_BAR"
    TIMESTAMP_IN_PAST = "TIMESTAMP_IN_PAST"
    CONTINUITY_GAP = "CONTINUITY_GAP"


@dataclass(frozen=True)
class ReconnectBarValidation:
    """Structured result of reconnect-bar validation."""

    verdict: ReconnectBarVerdict
    reason: str
    expected_next_utc: Optional[datetime] = None


def validate_reconnect_bar(
    bar: FeedBar,
    last_accepted_utc: Optional[datetime],
    timeframe: BarTimeframe,
    max_data_age_ms: Optional[int],
) -> ReconnectBarValidation:
    """Validate one reconnected bar against continuity and freshness.

    Rules (ALL must hold for ACCEPT):
    - bootstrap (last_accepted is None): freshness only — there is no prior
      accepted bar to be continuous with.
    - continuity: bar.timestamp_utc MUST equal last_accepted + timeframe_step.
      A duplicate/past timestamp -> TIMESTAMP_IN_PAST;
      a different future timestamp -> CONTINUITY_GAP.
    - freshness: when max_data_age_ms is set, observed age MUST be within it.
      Otherwise -> STALE_BAR.

    Raises DataContractError when timeframe has no known step (should be
    impossible for BarTimeframe members; fail-closed regardless).
    """
    step_seconds = TIMEFRAME_STEP_SECONDS.get(timeframe)
    if step_seconds is None:
        raise DataContractError(
            f"validate_reconnect_bar: no canonical step for timeframe {timeframe!r}."
        )
    if bar.timestamp_utc.tzinfo is None:
        raise DataContractError(
            "validate_reconnect_bar: resumed bar timestamp must be timezone-aware "
            "UTC (feed contract violation)."
        )

    if last_accepted_utc is not None:
        if last_accepted_utc.tzinfo is None:
            raise DataContractError(
                "validate_reconnect_bar: last_accepted_utc must be timezone-aware UTC."
            )
        last_utc = last_accepted_utc.astimezone(timezone.utc)
        bar_utc = bar.timestamp_utc.astimezone(timezone.utc)
        if bar_utc <= last_utc:
            return ReconnectBarValidation(
                verdict=ReconnectBarVerdict.TIMESTAMP_IN_PAST,
                reason=(
                    f"resumed bar {bar_utc.isoformat()} <= last accepted "
                    f"{last_utc.isoformat()} (duplicate or past bar)"
                ),
                expected_next_utc=last_utc + timedelta(seconds=step_seconds),
            )
        expected_next = last_utc + timedelta(seconds=step_seconds)
        if bar_utc != expected_next:
            return ReconnectBarValidation(
                verdict=ReconnectBarVerdict.CONTINUITY_GAP,
                reason=(
                    f"continuity gap: expected {expected_next.isoformat()} "
                    f"({timeframe.value}), got {bar_utc.isoformat()}. "
                    "ACASH does not fabricate missing bars."
                ),
                expected_next_utc=expected_next,
            )

    # Freshness gate (applies to bootstrap and continuation alike).
    if max_data_age_ms is not None:
        age_ms = bar.data_age_ms()
        if age_ms > max_data_age_ms:
            return ReconnectBarValidation(
                verdict=ReconnectBarVerdict.STALE_BAR,
                reason=(
                    f"resumed bar stale: age {age_ms}ms > max_data_age_ms "
                    f"{max_data_age_ms}ms"
                ),
                expected_next_utc=(
                    last_accepted_utc + timedelta(seconds=step_seconds)
                    if last_accepted_utc is not None
                    else None
                ),
            )

    return ReconnectBarValidation(
        verdict=ReconnectBarVerdict.ACCEPT,
        reason="resumed bar satisfies continuity and freshness.",
        expected_next_utc=(
            last_accepted_utc + timedelta(seconds=step_seconds)
            if last_accepted_utc is not None
            else None
        ),
    )


# ---------------------------------------------------------------------------
# Recovery episode driver
# ---------------------------------------------------------------------------

# Phase vocabulary passed to the journal_event callback. The caller maps each
# phase to its HealthEventKind / JournalEventType (single authority there).
RECOVERY_PHASE_ENTER = "ENTER"
RECOVERY_PHASE_ATTEMPT = "ATTEMPT"
RECOVERY_PHASE_ATTEMPT_FAILED = "ATTEMPT_FAILED"
RECOVERY_PHASE_POLLING = "POLLING"
RECOVERY_PHASE_RESUMED = "RESUMED"
RECOVERY_PHASE_BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
RECOVERY_PHASE_INVALID_BAR = "INVALID_BAR"
RECOVERY_PHASE_ABORTED = "ABORTED"


def backoff_delay_seconds(attempt_no: int, backoff: Tuple[float, ...]) -> float:
    """Single authority for the post-failure delay scheduled for attempt ``attempt_no``.

    Attempt 1 failing sleeps ``backoff[0]``, attempt 2 sleeping ``backoff[1]``, and
    any attempt past the schedule length takes the last entry. Because both the
    journaled ``backoff_seconds`` value and the driver's actual sleep derive from
    this one function, the recorded schedule always equals the applied delay.
    """
    return backoff[min(max(attempt_no, 1) - 1, len(backoff) - 1)]


def run_feed_recovery(
    *,
    feed: IMarketDataFeed,
    config: FeedRecoveryConfig,
    last_accepted_utc: Optional[datetime],
    timeframe: BarTimeframe,
    max_data_age_ms: Optional[int],
    should_stop: Callable[[], bool],
    journal_event: Callable[[str, Dict[str, Any]], None],
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> FeedRecoveryResult:
    """Run one deterministic transient-feed-recovery episode.

    Returns the final episode result. Never raises for bounded transient
    connection failures (they are consumed into the attempts budget). The
    monotonic clock is injectable so bar-wait-timeout behavior is testable
    deterministically without real-time waits.
    """
    attempts_used = 0
    backoff = config.backoff_seconds
    max_attempts = config.max_attempts
    poll_interval = config.poll_interval_seconds
    bar_wait_timeout = config.bar_wait_timeout_seconds
    clock = monotonic

    def _abort_operator_stop() -> FeedRecoveryResult:
        journal_event(
            RECOVERY_PHASE_ABORTED,
            {"attempts_used": attempts_used, "reason": "OPERATOR_STOP"},
        )
        return FeedRecoveryResult(
            state=FeedRecoveryState.OPERATOR_STOP,
            attempts_used=attempts_used,
            reason="Operator requested shutdown during recovery episode.",
        )

    def _fail_attempt(
        attempt_no: int,
        *,
        reason: str,
        error_category: str = "CONNECTION_ERROR",
        error: str = "",
        waited_seconds: Optional[float] = None,
    ) -> Optional[float]:
        """Journal one failed attempt and consume retry budget.

        Returns the exact post-failure delay to sleep (identical to the journaled
        ``backoff_seconds``), or None when the budget is exhausted (terminal — the
        caller must not sleep after the final attempt).
        """
        nonlocal attempts_used
        attempts_used += 1
        applied_delay = (
            0.0
            if attempts_used >= max_attempts
            else backoff_delay_seconds(attempt_no, backoff)
        )
        details: Dict[str, Any] = {
            "attempt": attempt_no,
            "attempts_used": attempts_used,
            "reason": reason,
            "error_category": error_category,
            "error": error[:500],
            "backoff_seconds": applied_delay,
        }
        if waited_seconds is not None:
            details["waited_seconds"] = waited_seconds
        journal_event(RECOVERY_PHASE_ATTEMPT_FAILED, details)
        return None if attempts_used >= max_attempts else applied_delay

    while attempts_used < max_attempts:
        if should_stop():
            return _abort_operator_stop()

        attempt_no = attempts_used + 1
        journal_event(
            RECOVERY_PHASE_ATTEMPT,
            {
                "attempt": attempt_no,
                "max_attempts": max_attempts,
                "last_accepted_utc": (
                    last_accepted_utc.isoformat() if last_accepted_utc else None
                ),
                "backoff_seconds": backoff_delay_seconds(attempt_no, backoff),
            },
        )

        # --- Reconnect (single bounded connect attempt) ---
        try:
            feed.connect()
        except FeedConnectionError as exc:
            applied_delay = _fail_attempt(
                attempt_no,
                reason="CONNECT_FAILED",
                error_category=getattr(exc, "category", "CONNECTION_ERROR"),
                error=str(exc),
            )
            if applied_delay is None:
                break
            sleeper(applied_delay)
            continue

        # --- Connected: wait for the next bar within this bounded attempt ---
        wait_started = clock()
        wait_deadline = wait_started + bar_wait_timeout
        while True:
            if should_stop():
                return _abort_operator_stop()

            journal_event(
                RECOVERY_PHASE_POLLING,
                {
                    "attempt": attempt_no,
                    "attempts_used": attempts_used,
                    "waited_seconds": max(0.0, clock() - wait_started),
                    "bar_wait_timeout_seconds": bar_wait_timeout,
                },
            )
            try:
                bar = feed.poll_next_bar()
            except FeedConnectionError as exc:
                applied_delay = _fail_attempt(
                    attempt_no,
                    reason="POLL_FAILED",
                    error_category=getattr(exc, "category", "CONNECTION_ERROR"),
                    error=str(exc),
                )
                if applied_delay is None:
                    break
                sleeper(applied_delay)
                break  # back to the reconnect (outer) loop

            if bar is None:
                if clock() >= wait_deadline:
                    waited = max(0.0, clock() - wait_started)
                    applied_delay = _fail_attempt(
                        attempt_no,
                        reason="BAR_WAIT_TIMEOUT",
                        error_category="BAR_WAIT_TIMEOUT",
                        error=(
                            f"no bar within {bar_wait_timeout}s of a successful "
                            "reconnect"
                        ),
                        waited_seconds=waited,
                    )
                    if applied_delay is None:
                        break
                    sleeper(applied_delay)
                    break  # back to the reconnect (outer) loop
                sleeper(poll_interval)
                continue

            # A bar was returned — validate continuity + freshness.
            validation = validate_reconnect_bar(
                bar,
                last_accepted_utc=last_accepted_utc,
                timeframe=timeframe,
                max_data_age_ms=max_data_age_ms,
            )
            if validation.verdict == ReconnectBarVerdict.ACCEPT:
                journal_event(
                    RECOVERY_PHASE_RESUMED,
                    {
                        "attempt": attempt_no,
                        "attempts_used": attempts_used,
                        "source_id": bar.source_id,
                        "bar_utc": bar.timestamp_utc.isoformat(),
                    },
                )
                return FeedRecoveryResult(
                    state=FeedRecoveryState.RESUMED,
                    attempts_used=attempts_used,
                    reason=validation.reason,
                    resumed_bar=bar,
                )

            # Fail-closed: a suspect bar ends the episode immediately.
            journal_event(
                RECOVERY_PHASE_INVALID_BAR,
                {
                    "attempt": attempt_no,
                    "attempts_used": attempts_used,
                    "verdict": validation.verdict.value,
                    "reason": validation.reason,
                    "source_id": bar.source_id,
                },
            )
            return FeedRecoveryResult(
                state=FeedRecoveryState.INVALID_BAR,
                attempts_used=attempts_used,
                reason=validation.reason,
            )

        # If the inner poll loop broke and the budget was consumed, the outer
        # loop terminates below.

    journal_event(
        RECOVERY_PHASE_BUDGET_EXHAUSTED,
        {"attempts_used": attempts_used, "max_attempts": max_attempts},
    )
    return FeedRecoveryResult(
        state=FeedRecoveryState.BUDGET_EXHAUSTED,
        attempts_used=attempts_used,
        reason=(
            f"feed recovery budget exhausted after {attempts_used} "
            f"of {max_attempts} attempts."
        ),
    )


# ---------------------------------------------------------------------------
# Operational metrics (bounded — no tournamentId/sessionId labels)
# ---------------------------------------------------------------------------

FEED_RECOVERY_STATE_VALUES = tuple(state.value for state in FeedRecoveryState)


def update_recovery_metrics(
    registry: MetricsRegistry,
    *,
    state: str,
    attempts_used: int,
    success_total: int,
    failure_total: int,
) -> None:
    """Export bounded feed-recovery operational gauges.

    The state one-hot is bounded to the fixed FeedRecoveryState vocabulary;
    no per-episode, per-slot, or per-tournament labels are ever emitted
    (operational telemetry only, never research evidence).
    """
    for state_value in FEED_RECOVERY_STATE_VALUES:
        registry.set_gauge(
            "acash_shadow_feed_recovery_state",
            1.0 if state_value == state else 0.0,
            {"state": state_value},
        )
    registry.set_gauge(
        "acash_shadow_feed_recovery_attempts_total", float(attempts_used)
    )
    registry.set_gauge(
        "acash_shadow_feed_recovery_success_total", float(success_total)
    )
    registry.set_gauge(
        "acash_shadow_feed_recovery_failure_total", float(failure_total)
    )