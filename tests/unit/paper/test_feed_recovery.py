"""Controlled transient feed recovery (V2 follow-up).

Proves the fail-closed quiescence contract of the FEED_RECOVERING lifecycle:
- zero bars consumed / zero decisions / zero orders during a recovery episode;
- resumed only from the first unapplied bar (continuity + freshness gate);
- budget exhaustion / invalid bar -> terminal FEED_RECOVERY_FAILED halt;
- operator stop during recovery seals slots as STOPPED (never FEED_HALTED).

Test discipline follows AGENTS.md principle 14: happy path -> boundary ->
malformed -> adversarial -> golden reference (journal ordering).
"""

from collections import deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

import pytest

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError
from acash.paper.feed import (
    FeedBar,
    FeedConnectionError,
    FeedContractError,
    FeedStatus,
    IMarketDataFeed,
)
from acash.paper.health import HealthEventKind, TerminalReason
from acash.paper.journal import JournalEventType, JournalLayer
from acash.paper.recovery import (
    FeedRecoveryConfig,
    FeedRecoveryResult,
    FeedRecoveryState,
    RECOVERY_PHASE_ABORTED,
    RECOVERY_PHASE_ATTEMPT,
    RECOVERY_PHASE_ATTEMPT_FAILED,
    backoff_delay_seconds,
    run_feed_recovery,
)
from acash.paper.runner import SignalSizingPolicy, SyntheticBar
from acash.paper.tournament import (
    SlotExecutionState,
    ShadowTournamentSupervisor,
    create_default_shadow_tournament,
)

_GIT = "a11995373bcb293135374e8c7dce6091963fea4a"
_T0 = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)


def _feed_bar(minute: int, *, received_offset_s: int = 1) -> FeedBar:
    ts = _T0 + timedelta(minutes=minute)
    return FeedBar.build(
        provider="scripted.recovery.test",
        provider_version="1.0.0",
        source_id=f"SRC-{minute}",
        symbol="BTCUSDT",
        timeframe="M1",
        timestamp_utc=ts,
        received_at_utc=ts + timedelta(seconds=received_offset_s),
        open=Decimal("50000"),
        high=Decimal("50010"),
        low=Decimal("49990"),
        close=Decimal("50005"),
        volume=Decimal("1.5"),
        sequence=minute,
    )


class ScriptedFeed(IMarketDataFeed):
    """Fake feed whose connect/poll failures are fully scripted."""

    def __init__(self, *, connect_failures: int = 0, poll_failures: int = 0) -> None:
        self._connect_failures = connect_failures
        self._poll_failures = poll_failures
        self._bars: Deque[Optional[FeedBar]] = deque()
        self._connected = False

    @property
    def provider_id(self) -> str:
        return "scripted.recovery.test"

    @property
    def provider_version(self) -> str:
        return "1.0.0"

    @property
    def symbol(self) -> str:
        return "BTCUSDT"

    @property
    def timeframe(self) -> BarTimeframe:
        return BarTimeframe.M1

    def queue(self, bar: Optional[FeedBar]) -> "ScriptedFeed":
        self._bars.append(bar)
        return self

    def connect(self) -> None:
        if self._connect_failures > 0:
            self._connect_failures -= 1
            raise FeedConnectionError(
                "scripted connect failure",
                category="CONNECTION_ERROR",
                operation="connect",
            )
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def poll_next_bar(self) -> Optional[FeedBar]:
        if self._poll_failures > 0:
            self._poll_failures -= 1
            raise FeedConnectionError(
                "scripted poll failure",
                category="CONNECTION_ERROR",
                operation="poll_next_bar",
            )
        return self._bars.popleft() if self._bars else None

    def status(self) -> FeedStatus:
        return FeedStatus(provider=self.provider_id, is_connected=self._connected)


def _phases(
    supervisor: ShadowTournamentSupervisor,
    slot_id: str,
    event_type: str,
) -> List[Dict[str, Any]]:
    runner = supervisor._slots[slot_id].runner
    if runner is None:
        return []
    return [
        e.payload
        for e in runner.journal.read_all()
        if e.event_type.value == event_type
    ]


def _run_episode(
    supervisor: ShadowTournamentSupervisor,
    feed: IMarketDataFeed,
    *,
    last_accepted_utc: Optional[datetime],
    config: FeedRecoveryConfig,
) -> FeedRecoveryResult:
    """Mirror tournament_cli._run_recovery_episode ordering exactly."""
    cid = supervisor.enter_feed_recovery("test episode")

    def journal_callback(phase: str, details: Dict[str, Any]) -> None:
        if phase in ("ATTEMPT", "ATTEMPT_FAILED"):
            supervisor.journal_system_event(
                HealthEventKind.FEED_RECOVERY_ATTEMPTED,
                cid,
                {"phase": phase, **details},
            )

    result = run_feed_recovery(
        feed=feed,
        config=config,
        last_accepted_utc=last_accepted_utc,
        timeframe=BarTimeframe.M1,
        max_data_age_ms=65_000,
        should_stop=lambda: False,
        journal_event=journal_callback,
        sleeper=lambda _s: None,
    )
    if result.state == FeedRecoveryState.RESUMED and result.resumed_bar is not None:
        supervisor.exit_feed_recovery(cid, result.resumed_bar.timestamp_utc.isoformat())
    elif result.state in (
        FeedRecoveryState.BUDGET_EXHAUSTED,
        FeedRecoveryState.INVALID_BAR,
    ):
        supervisor.fail_feed_recovery(cid, result.reason or "feed recovery failed")
    return result


def _supervisor(tmp_path: Path, count: int = 3) -> ShadowTournamentSupervisor:
    return create_default_shadow_tournament(
        storage_dir=tmp_path,
        acash_commit_sha=_GIT,
        num_slots=count,
        auto_mount_infrastructure_candidates=True,
        infra_mount_count=None,
        signal_sizing_policy=SignalSizingPolicy.INFRA_FIXED_QUANTITY,
        nav_sizing_notional_pct=Decimal("0"),
    )


def _bar(minute: int) -> SyntheticBar:
    ts = _T0 + timedelta(minutes=minute)
    return SyntheticBar(
        timestamp_utc=ts,
        symbol="BTCUSDT",
        open=Decimal("50000"),
        high=Decimal("50010"),
        low=Decimal("49990"),
        close=Decimal("50005"),
        volume=Decimal("1.5"),
        feed_source="scripted.recovery.test",
        feed_source_id=f"BINFRA-{minute}",
        received_at_utc=ts + timedelta(seconds=1),
        feed_sequence=minute,
        data_age_ms=1000,
    )


# ---------------------------------------------------------------------------
# Validation primitives
# ---------------------------------------------------------------------------


def test_validate_reconnect_bar_rejects_past_timestamp() -> None:
    from acash.paper.recovery import (
        ReconnectBarVerdict,
        validate_reconnect_bar,
    )

    last = _T0 + timedelta(minutes=5)
    dup = _feed_bar(5)
    verdict = validate_reconnect_bar(dup, last, BarTimeframe.M1, 65_000)
    assert verdict.verdict == ReconnectBarVerdict.TIMESTAMP_IN_PAST


def test_validate_reconnect_bar_rejects_continuity_gap() -> None:
    from acash.paper.recovery import (
        ReconnectBarVerdict,
        validate_reconnect_bar,
    )

    last = _T0 + timedelta(minutes=5)
    gap = _feed_bar(7)  # expected minute 6
    verdict = validate_reconnect_bar(gap, last, BarTimeframe.M1, 65_000)
    assert verdict.verdict == ReconnectBarVerdict.CONTINUITY_GAP


# ---------------------------------------------------------------------------
# Episode drivers
# ---------------------------------------------------------------------------


def test_resume_after_single_transient_connect_failure(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    result = _run_episode(
        supervisor,
        ScriptedFeed(connect_failures=1).queue(_feed_bar(1)),
        last_accepted_utc=None,
        config=FeedRecoveryConfig(max_attempts=5, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.RESUMED
    assert result.attempts_used == 1
    assert result.resumed_bar is not None
    assert supervisor.feed_recovery_active is False
    assert supervisor.to_dict()["global"]["overallStatus"] == "RUNNING"


def test_resume_after_multiple_transient_failures_within_budget(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    result = _run_episode(
        supervisor,
        ScriptedFeed(connect_failures=3).queue(_feed_bar(1)),
        last_accepted_utc=None,
        config=FeedRecoveryConfig(max_attempts=5, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.RESUMED
    assert result.attempts_used == 3


def test_poll_none_before_valid_bar_resumes(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    result = _run_episode(
        supervisor,
        ScriptedFeed().queue(None).queue(_feed_bar(1)),
        last_accepted_utc=None,
        config=FeedRecoveryConfig(max_attempts=5, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.RESUMED
    assert result.attempts_used == 0


def test_budget_exhausted_halts_feed_halted(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    result = _run_episode(
        supervisor,
        ScriptedFeed(connect_failures=99),
        last_accepted_utc=None,
        config=FeedRecoveryConfig(max_attempts=3, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.BUDGET_EXHAUSTED
    assert result.attempts_used == 3
    status = supervisor.to_dict()
    assert status["global"]["overallStatus"] == "HALTED"
    assert status["global"]["feedHealth"] == "HALTED"
    assert all(
        slot["status"] == SlotExecutionState.FEED_HALTED.value
        for slot in status["slots"].values()
    )


def test_stale_bar_fails_closed(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    # received 100s later than market time -> age 100000ms > 65000ms
    stale = _feed_bar(1, received_offset_s=100)
    result = _run_episode(
        supervisor,
        ScriptedFeed().queue(stale),
        last_accepted_utc=None,
        config=FeedRecoveryConfig(max_attempts=5, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.INVALID_BAR
    assert supervisor.to_dict()["global"]["overallStatus"] == "HALTED"


def test_timestamp_in_past_fails_closed(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    result = _run_episode(
        supervisor,
        ScriptedFeed().queue(_feed_bar(5)),
        last_accepted_utc=_T0 + timedelta(minutes=5),
        config=FeedRecoveryConfig(max_attempts=5, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.INVALID_BAR
    assert supervisor.to_dict()["global"]["overallStatus"] == "HALTED"


def test_continuity_gap_fails_closed(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    result = _run_episode(
        supervisor,
        ScriptedFeed().queue(_feed_bar(7)),
        last_accepted_utc=_T0 + timedelta(minutes=5),
        config=FeedRecoveryConfig(max_attempts=5, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.INVALID_BAR
    assert supervisor.to_dict()["global"]["overallStatus"] == "HALTED"


# ---------------------------------------------------------------------------
# Deterministic engine-driven hardening guards (backoff & bounded bar-wait)
# ---------------------------------------------------------------------------


class _FakeClock:
    """Deterministic monotonic clock advanced by the recorded sleeper."""

    def __init__(self) -> None:
        self._now = 0.0

    def __call__(self) -> float:
        return self._now

    def advance(self, amount: float) -> None:
        self._now += amount


def _engine_episode(
    feed: IMarketDataFeed,
    config: FeedRecoveryConfig,
    *,
    should_stop: Callable[[], bool],
) -> Tuple[FeedRecoveryResult, List[float], List[Dict[str, Any]], _FakeClock]:
    """Drive run_feed_recovery directly with a deterministic clock + sleep recorder."""
    sleeps: List[float] = []
    events: List[Dict[str, Any]] = []
    clock = _FakeClock()

    def journal(phase: str, details: Dict[str, Any]) -> None:
        events.append({"phase": phase, **details})

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        clock.advance(seconds)

    result = run_feed_recovery(
        feed=feed,
        config=config,
        last_accepted_utc=None,
        timeframe=BarTimeframe.M1,
        max_data_age_ms=65_000,
        should_stop=should_stop,
        journal_event=journal,
        sleeper=sleeper,
        monotonic=clock,
    )
    return result, sleeps, events, clock


def test_backoff_schedule_exact_no_terminal_sleep() -> None:
    result, sleeps, _events, _clock = _engine_episode(
        ScriptedFeed(connect_failures=99),
        FeedRecoveryConfig(
            max_attempts=5,
            backoff_seconds=(2.0, 5.0, 10.0, 20.0, 30.0),
            poll_interval_seconds=0.0,
        ),
        should_stop=lambda: False,
    )
    assert result.state == FeedRecoveryState.BUDGET_EXHAUSTED
    assert result.attempts_used == 5
    # Attempt 1 failure sleeps backoff[0]=2.0, ..., attempt 4 failure sleeps
    # backoff[3]=20.0. The 5th (terminal) failure sleeps NOTHING — there is no
    # sleep after budget exhaustion.
    assert sleeps == [2.0, 5.0, 10.0, 20.0]


def test_backoff_journaled_equals_actual_sleep() -> None:
    result, sleeps, events, _clock = _engine_episode(
        ScriptedFeed(connect_failures=99),
        FeedRecoveryConfig(
            max_attempts=5,
            backoff_seconds=(2.0, 5.0, 10.0, 20.0, 30.0),
            poll_interval_seconds=0.0,
        ),
        should_stop=lambda: False,
    )
    assert result.state == FeedRecoveryState.BUDGET_EXHAUSTED
    failed = [e for e in events if e["phase"] == RECOVERY_PHASE_ATTEMPT_FAILED]
    failed.sort(key=lambda e: e["attempt"])
    applied: List[float] = [e["backoff_seconds"] for e in failed]
    # The journaled post-failure delay is the single authority: it must equal the
    # recorded actual sleep for every non-terminal attempt, and be 0.0 (no sleep)
    # for the terminal attempt.
    assert applied == sleeps + [0.0]


def test_backoff_short_schedule_clamps_to_last_entry() -> None:
    result, sleeps, _events, _clock = _engine_episode(
        ScriptedFeed(connect_failures=99),
        FeedRecoveryConfig(
            max_attempts=5,
            backoff_seconds=(1.0, 2.0),
            poll_interval_seconds=0.0,
        ),
        should_stop=lambda: False,
    )
    assert result.state == FeedRecoveryState.BUDGET_EXHAUSTED
    # Schedule exercises backoff[0]=1.0, then clamps to the last entry backoff[1]=2.0.
    assert sleeps == [1.0, 2.0, 2.0, 2.0]


def test_backoff_delay_seconds_single_authority() -> None:
    backoff = (1.0, 2.0, 3.0)
    assert backoff_delay_seconds(1, backoff) == 1.0
    assert backoff_delay_seconds(2, backoff) == 2.0
    assert backoff_delay_seconds(3, backoff) == 3.0
    # Attempts beyond the schedule length take the last entry (never an index error).
    assert backoff_delay_seconds(4, backoff) == 3.0
    assert backoff_delay_seconds(99, backoff) == 3.0


def test_bar_wait_timeout_consumes_attempt_then_recovers() -> None:
    # Attempt 1: connected, no bar within the 1s monotonic budget -> the attempt's
    # retry budget is consumed and the configured backoff applied.
    # Attempt 2: connected, a valid bar arrives -> RESUMED with attempts_used=1.
    feed = ScriptedFeed().queue(None).queue(None).queue(_feed_bar(1))
    result, sleeps, events, _clock = _engine_episode(
        feed,
        FeedRecoveryConfig(
            max_attempts=2,
            backoff_seconds=(0.5, 1.0),
            poll_interval_seconds=1.0,
            bar_wait_timeout_seconds=1.0,
        ),
        should_stop=lambda: False,
    )
    assert result.state == FeedRecoveryState.RESUMED
    assert result.attempts_used == 1
    assert result.resumed_bar is not None
    # Attempt 1: poll(None) sleep 1.0 -> poll(None) deadline reached -> timeout,
    # then backoff 0.5. Attempt 2: poll -> bar immediately.
    assert sleeps == [1.0, 0.5]
    timeouts = [e for e in events if e.get("reason") == "BAR_WAIT_TIMEOUT"]
    assert len(timeouts) == 1
    assert timeouts[0]["attempt"] == 1
    assert timeouts[0]["waited_seconds"] == 1.0
    assert timeouts[0]["backoff_seconds"] == 0.5


def test_bar_wait_timeout_all_attempts_exhausted() -> None:
    result, sleeps, events, _clock = _engine_episode(
        ScriptedFeed(),  # connected but never any bar
        FeedRecoveryConfig(
            max_attempts=2,
            backoff_seconds=(0.5, 1.0),
            poll_interval_seconds=1.0,
            bar_wait_timeout_seconds=1.0,
        ),
        should_stop=lambda: False,
    )
    assert result.state == FeedRecoveryState.BUDGET_EXHAUSTED
    assert result.attempts_used == 2
    failed = [e for e in events if e["phase"] == RECOVERY_PHASE_ATTEMPT_FAILED]
    assert len(failed) == 2
    assert all(e["reason"] == "BAR_WAIT_TIMEOUT" for e in failed)
    # Attempt 1: one poll sleep (0.0->1.0) then BAR_WAIT_TIMEOUT, backoff 0.5;
    # Attempt 2: one poll sleep (1.5->2.5) then terminal timeout, no sleep.
    assert sleeps == [1.0, 0.5, 1.0]


def test_bar_wait_timeout_budget_wallclock_bounded() -> None:
    # Even with a no-op sleeper and the real monotonic clock, a never-barring
    # feed cannot wait indefinitely: the deadline is checked against the wall
    # clock, so the budget (not the poll count) is the hard bound.
    events: List[Dict[str, Any]] = []

    def journal(phase: str, details: Dict[str, Any]) -> None:
        events.append({"phase": phase, **details})

    result = run_feed_recovery(
        feed=ScriptedFeed(),  # connected, never any bar
        config=FeedRecoveryConfig(
            max_attempts=1,
            backoff_seconds=(0.0,),
            poll_interval_seconds=0.0,
            bar_wait_timeout_seconds=0.05,
        ),
        last_accepted_utc=None,
        timeframe=BarTimeframe.M1,
        max_data_age_ms=65_000,
        should_stop=lambda: False,
        journal_event=journal,
        sleeper=lambda _s: None,
    )
    assert result.state == FeedRecoveryState.BUDGET_EXHAUSTED
    assert result.attempts_used == 1
    assert any(e.get("reason") == "BAR_WAIT_TIMEOUT" for e in events)


def test_operator_stop_during_bar_wait() -> None:
    stop_after_one_sleep = {"value": 0}

    def should_stop() -> bool:
        return stop_after_one_sleep["value"] >= 1

    def sleeper(seconds: float) -> None:
        stop_after_one_sleep["value"] += 1

    clock = _FakeClock()
    events: List[Dict[str, Any]] = []

    def journal(phase: str, details: Dict[str, Any]) -> None:
        events.append({"phase": phase, **details})

    result = run_feed_recovery(
        feed=ScriptedFeed(),  # connected, never a bar
        config=FeedRecoveryConfig(
            max_attempts=5,
            backoff_seconds=(0.5,),
            poll_interval_seconds=1.0,
            bar_wait_timeout_seconds=60.0,
        ),
        last_accepted_utc=None,
        timeframe=BarTimeframe.M1,
        max_data_age_ms=65_000,
        should_stop=should_stop,
        journal_event=journal,
        sleeper=sleeper,
        monotonic=clock,
    )
    assert result.state == FeedRecoveryState.OPERATOR_STOP
    assert result.attempts_used == 0
    assert any(e["phase"] == RECOVERY_PHASE_ABORTED for e in events)


def test_feed_contract_error_bypasses_recovery() -> None:
    class ContractBreakingFeed(ScriptedFeed):
        def connect(self) -> None:
            raise FeedContractError("structural feed contract violation")

    # FeedContractError must NOT be consumed into the retry budget: it propagates
    # to the caller's fail-closed handler instead of being retried.
    with pytest.raises(FeedContractError):
        run_feed_recovery(
            feed=ContractBreakingFeed(),
            config=FeedRecoveryConfig(
                max_attempts=5,
                backoff_seconds=(0.0,),
            ),
            last_accepted_utc=None,
            timeframe=BarTimeframe.M1,
            max_data_age_ms=65_000,
            should_stop=lambda: False,
            journal_event=lambda _p, _d: None,
            sleeper=lambda _s: None,
        )


def test_bar_wait_timeout_non_positive_rejected() -> None:
    with pytest.raises(DataContractError):
        FeedRecoveryConfig(bar_wait_timeout_seconds=0.0)
    with pytest.raises(DataContractError):
        FeedRecoveryConfig(bar_wait_timeout_seconds=-1.0)


def test_config_rejects_non_finite_backoff_seconds() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(DataContractError):
            FeedRecoveryConfig(backoff_seconds=(bad,))
        with pytest.raises(DataContractError):
            FeedRecoveryConfig(backoff_seconds=(2.0, bad, 10.0))


def test_config_rejects_non_finite_poll_interval() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(DataContractError):
            FeedRecoveryConfig(poll_interval_seconds=bad)


def test_config_rejects_non_finite_bar_wait_timeout() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(DataContractError):
            FeedRecoveryConfig(bar_wait_timeout_seconds=bad)


def test_config_finite_zero_poll_interval_remains_valid() -> None:
    # The library contract permits a finite zero poll interval (deterministic
    # tests / busy-poll); only non-finite or negative values are rejected.
    config = FeedRecoveryConfig(poll_interval_seconds=0.0)
    assert config.poll_interval_seconds == 0.0


# ---------------------------------------------------------------------------
# Quiescence contract
# ---------------------------------------------------------------------------


def test_zero_decisions_during_recovery(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    for minute in range(1, 5):
        supervisor.process_bar(_bar(minute))
    bars_before = supervisor._bar_count
    supervisor.enter_feed_recovery("test")
    for minute in range(5, 9):
        results = supervisor.process_bar(_bar(minute))
        assert all(cid is None for cid in results.values())
    assert supervisor._bar_count == bars_before
    status = supervisor.to_dict()
    assert all(
        slot["status"] == SlotExecutionState.FEED_RECOVERING.value
        for slot in status["slots"].values()
    )


def test_zero_orders_and_signals_during_recovery(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    for minute in range(1, 4):
        supervisor.process_bar(_bar(minute))
    slot_a = supervisor._slots["A"].runner
    assert slot_a is not None
    orders_before = len(
        [e for e in slot_a.journal.read_all() if e.layer == JournalLayer.EXECUTION]
    )
    signals_before = len(
        [e for e in slot_a.journal.read_all() if e.layer == JournalLayer.SIGNAL]
    )
    cid = supervisor.enter_feed_recovery("test")
    for minute in range(4, 7):
        supervisor.process_bar(_bar(minute))
    orders_after = len(
        [e for e in slot_a.journal.read_all() if e.layer == JournalLayer.EXECUTION]
    )
    signals_after = len(
        [e for e in slot_a.journal.read_all() if e.layer == JournalLayer.SIGNAL]
    )
    assert orders_after == orders_before
    assert signals_after == signals_before


def test_portfolio_and_closed_positions_preserved(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    for minute in range(1, 9):
        supervisor.process_bar(_bar(minute))
    slot_a = supervisor._slots["A"].runner
    assert slot_a is not None
    if slot_a._portfolio.position == Decimal("0"):
        supervisor.process_bar(_bar(9))
    cash_before = slot_a._portfolio.cash
    position_before = slot_a._portfolio.position
    history_before = len(supervisor._closed_positions_history["A"])
    bars_before = supervisor._bar_count
    result = _run_episode(
        supervisor,
        ScriptedFeed().queue(_feed_bar(10)),
        last_accepted_utc=datetime.fromisoformat(
            supervisor.last_accepted_bar_utc
        )
        if supervisor.last_accepted_bar_utc is not None
        else None,
        config=FeedRecoveryConfig(max_attempts=3, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.RESUMED
    supervisor.process_bar(_bar(11))
    # Portfolio state survived the episode: nothing was reset to baseline.
    assert slot_a._portfolio.cash == cash_before
    assert slot_a._portfolio.position == position_before
    assert len(supervisor._closed_positions_history["A"]) >= history_before
    assert supervisor._bar_count == bars_before + 1
    assert supervisor.to_dict()["global"]["overallStatus"] == "RUNNING"


def test_journal_ordering_recovery_episode(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    for minute in range(1, 3):
        supervisor.process_bar(_bar(minute))
    result = _run_episode(
        supervisor,
        ScriptedFeed().queue(_feed_bar(3)),
        last_accepted_utc=datetime.fromisoformat(
            supervisor.last_accepted_bar_utc
        )
        if supervisor.last_accepted_bar_utc is not None
        else None,
        config=FeedRecoveryConfig(max_attempts=2, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.RESUMED
    # Events flow through a single episode correlation id that is authoritatively
    # created by enter_feed_recovery and reused for every journaled phase.
    events: List[Any] = []
    for slot in supervisor._slots.values():
        if slot.runner is not None:
            events.extend(slot.runner.journal.read_all())
    types_all = [e.event_type.value for e in events]
    assert "FEED_RECOVERING" in types_all
    assert "FEED_RECOVERY_ATTEMPTED" in types_all
    assert "FEED_RECOVERY_SUCCEEDED" in types_all
    # Ordering: RECOVERING before ATTEMPTED before SUCCEEDED.
    assert types_all.index("FEED_RECOVERING") < types_all.index("FEED_RECOVERY_ATTEMPTED")
    assert (
        types_all.index("FEED_RECOVERY_ATTEMPTED")
        < types_all.index("FEED_RECOVERY_SUCCEEDED")
    )
    # Every phase of one episode shares the same correlation id.
    by_corr: Dict[str, Set[str]] = {}
    for e in events:
        by_corr.setdefault(e.correlation_id, set()).add(e.event_type.value)
    episode = [s for s in by_corr.values() if "FEED_RECOVERING" in s]
    assert len(episode) == 1
    assert {"FEED_RECOVERING", "FEED_RECOVERY_ATTEMPTED", "FEED_RECOVERY_SUCCEEDED"} <= episode[0]


def test_operator_stop_during_recovery_seals_stopped(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    cid = supervisor.enter_feed_recovery("test")
    # MyPy: cid is an authoritative episode correlation id but the halt path
    # does not need it; the supervisor must reconcile flags regardless.
    supervisor.halt(
        reason="Operator shutdown during feed recovery.",
        feed_health="DISCONNECTED",
        terminal_reason=TerminalReason.OPERATOR_STOP,
    )
    status = supervisor.to_dict()
    assert status["global"]["overallStatus"] == "HALTED"
    assert all(
        slot["status"] == SlotExecutionState.STOPPED.value
        for slot in status["slots"].values()
    )
    assert supervisor.feed_recovery_active is False


def test_resume_from_first_unapplied_bar_boundary(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    for minute in range(1, 4):
        supervisor.process_bar(_bar(minute))
    last = _T0 + timedelta(minutes=3)
    assert supervisor.last_accepted_bar_utc == last.isoformat()
    result = _run_episode(
        supervisor,
        ScriptedFeed().queue(_feed_bar(4)),
        last_accepted_utc=last,
        config=FeedRecoveryConfig(max_attempts=3, backoff_seconds=(0.0,)),
    )
    assert result.state == FeedRecoveryState.RESUMED
    assert result.resumed_bar is not None
    assert result.resumed_bar.timestamp_utc == last + timedelta(minutes=1)


def test_double_enter_recovery_rejected(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    supervisor.enter_feed_recovery("first")
    with pytest.raises(DataContractError):
        supervisor.enter_feed_recovery("second")


def test_exit_without_active_recovery_rejected(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    with pytest.raises(DataContractError):
        supervisor.exit_feed_recovery("ghost", "2026-09-14T12:06:00+00:00")


def test_enter_recovery_while_halted_rejected(tmp_path: Path) -> None:
    supervisor = _supervisor(tmp_path)
    supervisor.start()
    supervisor.halt(reason="first halt", terminal_reason=TerminalReason.OPERATOR_STOP)
    with pytest.raises(DataContractError):
        supervisor.enter_feed_recovery("too late")