"""ACASH Paper Trading — Shadow Alpha Tournament Core Engine.

Governance Invariants (Non-Negotiable):
- SHADOW / SIMULATED RESEARCH INFRASTRUCTURE ONLY — NOT Paper GO / NOT Live / NOT HYP_003
- Canonical Capital = $0.00 | Real Orders Dispatched = 0 | NO_REAL_ORDERS = True
- Isolated virtual portfolio state for each active strategy slot (default A, B, C; num_slots-driven A..Z)
- Zero cross-strategy state leakage (virtual cash, virtual positions, virtual orders, virtual fills)
- Synchronized shared feed: all active slots receive the exact same market bar
- Independent flight recorder journals and manifests per slot
- Fail-closed lifecycle: feed disconnect/stale data halts all active slots and seals journals
- Read-only dashboard representation: zero trading controls or mutation endpoints
"""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.paper.health import HealthEventKind, PaperHealthMonitor, TerminalReason
from acash.paper.metrics import MetricsRegistry
from acash.paper.runner import (
    SAFE_V2_NAV_SIZING_PCT,
    PaperSessionConfig,
    PaperSessionRunner,
    SignalSizingPolicy,
    SyntheticBar,
)
from acash.paper.strategy import (
    InfrastructureTestStrategy,
    PaperStrategyProtocol,
    SignalDirection,
    StrategySignal,
    get_infrastructure_candidate,
    get_infrastructure_candidate_by_strategy_id,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Governance Constants
# ---------------------------------------------------------------------------

SHADOW_GOVERNANCE_LABEL = "SHADOW_SIMULATED_RESEARCH_INFRA_ONLY"
CANONICAL_CAPITAL_USD = Decimal("0.00")
NO_REAL_ORDERS = True
REAL_ORDERS_COUNT = 0


@dataclass(frozen=True)
class TournamentGovernance:
    """Immutable governance bounds for the Shadow Alpha Tournament."""

    canonical_capital_usd: Decimal = CANONICAL_CAPITAL_USD
    real_orders_count: int = REAL_ORDERS_COUNT
    no_real_orders: bool = NO_REAL_ORDERS
    governance_mode: str = SHADOW_GOVERNANCE_LABEL
    governance_badge: str = "SHADOW / SIMULATED ONLY"
    is_paper_authorized: bool = False
    is_live_authorized: bool = False
    is_backtest_authorized: bool = False
    hyp_003_exists: bool = False
    r1_started: bool = False


# ---------------------------------------------------------------------------
# Slot Configuration and State
# ---------------------------------------------------------------------------

_SLOT_ID_PATTERN = re.compile(r"^[A-Z]$")


def slot_ids_for_count(num_slots: int) -> Tuple[str, ...]:
    """Deterministically generate slot ids A..Z for a fanout of num_slots.

    Governance note: slot ids are cosmetic coordinate labels, NOT strategy
    identities. Up to 26 slots (A-Z) are supported; a larger fanout is a
    contract violation.
    """
    if num_slots < 1 or num_slots > 26:
        raise DataContractError(
            f"slot fanout must be in [1, 26]; got {num_slots}"
        )
    return tuple(chr(ord("A") + i) for i in range(num_slots))


class SlotExecutionState(str, Enum):
    """Granular per-slot & aggregate execution states (Tournament V2 Defect D).

    Surfaced in slot status, aggregate `executionState`, API JSON, Prometheus
    metrics, and the dashboard contract. Replaces the former coarse HALTED
    bucket so operators can distinguish WHY a slot is not trading:

    - RUNNING            slot actively processing synchronized bars
    - RISK_HALTED        kill switch active (MAX_DAILY_LOSS) on this slot
    - FEED_HALTED        halted fail-closed due to feed disconnect/staleness
    - FEED_RECOVERING    feed disconnected; controlled transient recovery in
                         progress (zero bars consumed, zero decisions, zero orders)
    - STOPPED            stopped by operator/normal shutdown
    - UNASSIGNED         no runner attached
    """

    RUNNING = "RUNNING"
    RISK_HALTED = "RISK_HALTED"
    FEED_HALTED = "FEED_HALTED"
    FEED_RECOVERING = "FEED_RECOVERING"
    STOPPED = "STOPPED"
    UNASSIGNED = "UNASSIGNED"


@dataclass
class SlotMetrics:
    """Performance and operational metrics for a single tournament slot."""

    initial_nav_usd: Decimal = Decimal("1000.00")
    current_nav_usd: Decimal = Decimal("1000.00")
    pnl_usd: Decimal = Decimal("0.00")
    pnl_pct: Decimal = Decimal("0.00")
    realized_pnl_usd: Decimal = Decimal("0.00")
    unrealized_pnl_usd: Decimal = Decimal("0.00")
    max_drawdown_pct: Decimal = Decimal("0.00")
    current_drawdown_pct: Decimal = Decimal("0.00")
    exposure_pct: Optional[Decimal] = None
    risk_utilization_pct: Optional[Decimal] = None
    open_position_count: int = 0
    simulated_order_count: int = 0
    simulated_fill_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate_pct: Optional[Decimal] = None
    signal_count: int = 0
    last_signal_utc: Optional[str] = None
    last_fill_utc: Optional[str] = None
    duration_seconds: Optional[int] = None


@dataclass
class TournamentSlot:
    """An isolated tournament slot running in parallel against synchronized data.

    Invariants:
    - Dedicated virtual portfolio with isolated virtual cash and virtual fills.
    - Zero state leakage to other slots.
    - Dedicated journal and manifest files.
    """

    slot_id: str
    strategy_id: str
    strategy_name: str
    strategy_version: str
    status: str  # SlotExecutionState: RUNNING|RISK_HALTED|FEED_HALTED|FEED_RECOVERING|STOPPED|UNASSIGNED
    session_id: str
    config_hash: str
    acash_commit_sha: str
    max_position_units: Decimal = Decimal("10.0")
    metrics: SlotMetrics = field(default_factory=SlotMetrics)
    runner: Optional[PaperSessionRunner] = None
    halt_reason: Optional[str] = None
    last_bar_utc: Optional[str] = None
    open_positions: List[Dict[str, Any]] = field(default_factory=list)
    recent_fills: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    peak_nav_usd: Decimal = Decimal("1000.00")

    # Provenance & observation-window identity (V2 follow-up).
    # The observation window is the single authority for leaderboard
    # comparability: late-join slots are ranked ONLY within their own cohort.
    started_at_utc: Optional[str] = None
    first_market_bar_utc: Optional[str] = None
    observation_kind: str = "NONE"  # NONE | CONTINUOUS | LATE_JOIN
    cohort_id: Optional[str] = None
    comparison_window_id: Optional[str] = None
    baseline_nav_usd: Decimal = Decimal("1000.00")

    def __post_init__(self) -> None:
        if not _SLOT_ID_PATTERN.fullmatch(self.slot_id):
            raise DataContractError(
                f"TournamentSlot: invalid slot_id '{self.slot_id}'. "
                "Must be a single uppercase letter (A..Z)."
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize slot to dictionary matching TypeScript StrategySlot contract."""
        is_unassigned = self.status == "UNASSIGNED" or self.runner is None

        gov_label: str
        if is_unassigned or self.runner is None:
            gov_label = "UNASSIGNED_SLOT"
        else:
            strat = self.runner._strategy
            if hasattr(strat, "governance_label"):
                gov_label = strat.governance_label
            elif getattr(strat, "is_infrastructure_test", True):
                gov_label = "INFRASTRUCTURE_TEST_STRATEGY_ONLY"
            else:
                gov_label = "SHADOW_ALPHA_CANDIDATE"

        return {
            "slotId": self.slot_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "strategyVersion": self.strategy_version,
            "governanceLabel": gov_label,
            "status": self.status,
            "sessionId": self.session_id,
            "configHash": self.config_hash,
            "acashCommitSha": self.acash_commit_sha,
            "haltReason": self.halt_reason,
            "operatorResolutionRequired": (
                self.runner.operator_resolution_required
                if self.runner is not None
                else False
            ),
            "lastBarUtc": self.last_bar_utc,
            "startedAtUtc": self.started_at_utc,
            "firstMarketBarUtc": self.first_market_bar_utc,
            "observationKind": self.observation_kind,
            "cohortId": self.cohort_id,
            "comparisonWindowId": self.comparison_window_id,
            "baselineNavUsd": float(self.baseline_nav_usd),
            "openPositions": self.open_positions if not is_unassigned else [],
            "recentFills": self.recent_fills if not is_unassigned else [],
            "equityCurve": self.equity_curve if not is_unassigned else [],
            "metrics": {
                "initialNavUsd": float(self.metrics.initial_nav_usd),
                "currentNavUsd": float(self.metrics.current_nav_usd),
                "pnlUsd": float(self.metrics.pnl_usd),
                "pnlPct": float(self.metrics.pnl_pct),
                "realizedPnlUsd": float(self.metrics.realized_pnl_usd),
                "unrealizedPnlUsd": float(self.metrics.unrealized_pnl_usd),
                "maxDrawdownPct": float(self.metrics.max_drawdown_pct),
                "currentDrawdownPct": float(self.metrics.current_drawdown_pct),
                "exposurePct": float(self.metrics.exposure_pct)
                if self.metrics.exposure_pct is not None
                else (0.0 if not is_unassigned else None),
                "riskUtilizationPct": float(self.metrics.risk_utilization_pct)
                if self.metrics.risk_utilization_pct is not None
                else (0.0 if not is_unassigned else None),
                "openPositionCount": self.metrics.open_position_count,
                "simulatedOrderCount": self.metrics.simulated_order_count,
                "simulatedFillCount": self.metrics.simulated_fill_count,
                "winCount": self.metrics.win_count,
                "lossCount": self.metrics.loss_count,
                "winRatePct": float(self.metrics.win_rate_pct)
                if self.metrics.win_rate_pct is not None
                else None,
                "signalCount": self.metrics.signal_count,
                "lastSignalUtc": self.metrics.last_signal_utc,
                "lastFillUtc": self.metrics.last_fill_utc,
                "durationSeconds": self.metrics.duration_seconds
                if not is_unassigned
                else None,
            },
        }


# ---------------------------------------------------------------------------
# ShadowTournamentSupervisor
# ---------------------------------------------------------------------------


class ShadowTournamentSupervisor:
    """Orchestrates multi-strategy tournament execution against synchronized data.

    Safety & Boundary Rules:
    1. ZERO REAL ORDERS: All executions are simulated through PaperSessionRunner.
    2. STATE ISOLATION: Slot A, B, and C maintain completely independent runners,
       memory spaces, journals, snapshots, and metrics registries.
    3. SYNCHRONIZED MARKET DATA: When a bar is received, it is processed sequentially
       across active slots with identical bar payload.
    4. FAIL-CLOSED HALT: Any feed disconnect or stale data puts tournament in HALTED
       state, stops active runners, seals manifests, and rejects subsequent bars.
    5. RESUME DISCIPLINE: No automatic resume. Calling start() on an already-started
       or halted tournament raises DataContractError.
    """

    def __init__(
        self,
        tournament_id: str,
        slots: Dict[str, TournamentSlot],
        acash_commit_sha: str,
        deployment_image_id: str = "acash-staging:sha-pinned",
        metrics_registry: Optional[MetricsRegistry] = None,
        *,
        slot_builder: Optional[
            Callable[
                [str, PaperStrategyProtocol],
                Tuple[TournamentSlot, PaperSessionRunner],
            ]
        ] = None,
        candidate_resolver: Optional[
            Callable[[str], Optional[PaperStrategyProtocol]]
        ] = None,
    ) -> None:
        self._tournament_id = tournament_id
        self._slots = slots
        self._acash_commit_sha = acash_commit_sha
        self._deployment_image_id = deployment_image_id
        self._metrics_registry = metrics_registry
        self._lock = threading.Lock()

        self._slot_builder = slot_builder
        self._candidate_resolver = candidate_resolver
        self._pending_candidate_adds: List[Dict[str, Any]] = []
        self._operator_action_results: List[Dict[str, Any]] = []
        self._feed_recovery_active = False

        self._feed_health: str = "UNKNOWN"
        self._overall_status: str = "NOT_STARTED"
        self._halt_reason: Optional[str] = (
            "Tournament has not been started. Awaiting Human authorization (H01) "
            "and strategy candidate selection (H02)."
        )
        self._start_time_utc: Optional[datetime] = None
        self._last_data_timestamp_utc: Optional[datetime] = None
        self._last_successful_update_utc: datetime = datetime.now(timezone.utc)
        self._bar_count: int = 0
        self._closed_positions_history: Dict[str, List[Decimal]] = {
            s: [] for s in self._slots
        }

        self._update_metrics()

    @property
    def tournament_id(self) -> str:
        return self._tournament_id

    @property
    def slots(self) -> Dict[str, TournamentSlot]:
        return self._slots

    @property
    def feed_health(self) -> str:
        return self._feed_health

    @property
    def overall_status(self) -> str:
        return self._overall_status

    def _aggregate_execution_state(self) -> str:
        """Derive a single tournament-level execution state from slot states.

        Deterministic precedence (fail-closed first):
        RISK_HALTED > FEED_HALTED > FEED_RECOVERING > STOPPED > RUNNING > UNASSIGNED > NOT_STARTED.
        When every slot is halted, the halt kind is preserved at aggregate level;
        otherwise the most severe active state wins.
        """
        slot_states = [s.status for s in self._slots.values()]
        priority = [
            SlotExecutionState.RISK_HALTED,
            SlotExecutionState.FEED_HALTED,
            SlotExecutionState.FEED_RECOVERING,
            SlotExecutionState.STOPPED,
            SlotExecutionState.RUNNING,
            SlotExecutionState.UNASSIGNED,
        ]
        for state in priority:
            if state.value in slot_states:
                return state.value
        return "NOT_STARTED"

    def start(self) -> None:
        """Start the tournament.

        Starts the underlying runner for each assigned slot.
        Raises DataContractError if already started or halted (fail-closed).
        """
        with self._lock:
            if self._overall_status in ("RUNNING", "HALTED"):
                raise DataContractError(
                    f"ShadowTournamentSupervisor: cannot start tournament in status '{self._overall_status}'."
                )

            active_slots = [s for s in self._slots.values() if s.runner is not None]
            if not active_slots:
                self._overall_status = "HALTED"
                self._halt_reason = "Cannot start tournament: zero active runners configured."
                return

            self._start_time_utc = datetime.now(timezone.utc)
            for slot in active_slots:
                if slot.runner is not None:
                    slot.runner.start()
                    slot.status = "RUNNING"
                    slot.metrics.duration_seconds = 0
                    if slot.started_at_utc is None:
                        slot.started_at_utc = self._start_time_utc.isoformat()

            self._overall_status = "RUNNING"
            self._halt_reason = None
            self._feed_health = "HEALTHY"
            self._last_successful_update_utc = datetime.now(timezone.utc)
            self._update_metrics()

    def halt(
        self,
        reason: str,
        feed_health: str = "HALTED",
        terminal_reason: Optional[TerminalReason] = None,
    ) -> None:
        """Halt tournament and all active slot runners fail-closed.

        Seals manifests for active runners so journals are safely finalized.

        Args:
            reason: Human-readable halt cause (preserved verbatim).
            feed_health: Feed integrity state ("HALTED", "DISCONNECTED", "STALE").
            terminal_reason: Canonical causal reason propagated to each slot
                runner's SESSION_STOPPED event. When omitted it is derived
                deterministically from feed_health (never silently defaulted):
                DISCONNECTED/STALE -> FEED_DISCONNECTED; else OPERATOR_STOP.
        """
        if terminal_reason is None:
            if feed_health in ("DISCONNECTED", "STALE"):
                terminal_reason = TerminalReason.FEED_DISCONNECTED
            else:
                terminal_reason = TerminalReason.OPERATOR_STOP

        with self._lock:
            if self._overall_status == "HALTED":
                return  # already halted

            self._overall_status = "HALTED"
            self._halt_reason = reason
            self._feed_health = feed_health
            self._last_successful_update_utc = datetime.now(timezone.utc)
            # A halt is terminal: any in-flight recovery episode is over.
            self._feed_recovery_active = False

            for slot_id, slot in self._slots.items():
                if slot.status not in (
                    SlotExecutionState.RUNNING.value,
                    SlotExecutionState.FEED_RECOVERING.value,
                ):
                    continue
                # Granular execution state derived from the CAUSAL terminal
                # reason (single authority): an already risk-halted slot stays
                # RISK_HALTED; feed-terminal causes (disconnect/stale/recovery
                # failure) -> FEED_HALTED; everything else -> STOPPED (operator).
                if slot.runner is not None and slot.runner.kill_switch_active:
                    slot.status = SlotExecutionState.RISK_HALTED.value
                elif terminal_reason in (
                    TerminalReason.FEED_DISCONNECTED,
                    TerminalReason.FEED_RECOVERY_FAILED,
                ):
                    slot.status = SlotExecutionState.FEED_HALTED.value
                else:
                    slot.status = SlotExecutionState.STOPPED.value
                slot.halt_reason = reason
                if slot.runner is not None and slot.runner._started:
                    try:
                        slot.runner.stop(terminal_reason=terminal_reason)
                        logger.info(
                            "ShadowTournamentSupervisor: sealed manifest for slot %s on halt",
                            slot_id,
                        )
                    except Exception as exc:
                        logger.error(
                            "ShadowTournamentSupervisor: error stopping slot %s runner: %s",
                            slot_id,
                            exc,
                        )

            self._update_metrics()

    def process_bar(self, bar: SyntheticBar) -> Dict[str, Optional[str]]:
        """Process a market bar across all slots with strict isolation.

        Returns a mapping of slot_id -> decision correlation_id (or None).
        Raises DataContractError if any slot encounters unrecoverable violation.
        """
        with self._lock:
            if self._overall_status != "RUNNING":
                logger.warning(
                    "ShadowTournamentSupervisor: bar rejected; tournament status is %s",
                    self._overall_status,
                )
                return {s: None for s in self._slots}

            # Quiescence during a controlled transient recovery: NO bar is
            # consumed, NO decision is made, NO order can be formed. The feed
            # health metric keeps reporting RECOVERING until the episode exits.
            if self._feed_health == "RECOVERING":
                logger.info(
                    "ShadowTournamentSupervisor: bar %s suppressed; feed recovery "
                    "in progress (zero bars consumed, zero decisions)",
                    bar.timestamp_utc,
                )
                return {s: None for s in self._slots}

            # Materialize staged operator candidate adds at this finalized-bar
            # boundary, before any slot consumes the bar. (Lock held by caller.)
            self._materialize_candidate_adds(bar)

            self._bar_count += 1
            self._last_data_timestamp_utc = bar.timestamp_utc
            self._last_successful_update_utc = datetime.now(timezone.utc)
            self._feed_health = "HEALTHY"

            results: Dict[str, Optional[str]] = {}

            # Deliver identical bar to each slot independently
            for slot_id, slot in self._slots.items():
                if slot.runner is None or slot.status != "RUNNING":
                    results[slot_id] = None
                    continue

                try:
                    # Isolated execution within slot's runner
                    cid = slot.runner.process_bar(bar)
                    results[slot_id] = cid

                    # Update slot state from runner portfolio and events
                    self._sync_slot_state(slot, bar, cid)

                except Exception as exc:
                    slot.status = "ERROR"
                    slot.halt_reason = f"Execution failure on bar {bar.timestamp_utc}: {exc}"
                    logger.error(
                        "ShadowTournamentSupervisor: slot %s encountered error: %s",
                        slot_id,
                        exc,
                        exc_info=True,
                    )
                    results[slot_id] = None

            self._update_metrics()
            return results

    def _sync_slot_state(
        self,
        slot: TournamentSlot,
        bar: SyntheticBar,
        decision_cid: Optional[str],
    ) -> None:
        """Sync slot metrics from runner portfolio with zero state leakage."""
        if slot.runner is None:
            return

        # Defect D: propagate the runner's kill switch into the slot execution
        # state so status JSON / API / metrics reflect WHY a slot stopped.
        if slot.runner.kill_switch_active and slot.status == "RUNNING":
            slot.status = SlotExecutionState.RISK_HALTED.value
            slot.halt_reason = "Kill switch active (max daily loss breached)"

        portfolio = slot.runner._portfolio
        mark_price = bar.close
        equity = portfolio.cash + (portfolio.position * mark_price)
        pnl = equity - slot.metrics.initial_nav_usd
        pnl_pct = (pnl / slot.metrics.initial_nav_usd) * Decimal("100.0")

        slot.metrics.current_nav_usd = equity
        slot.metrics.pnl_usd = pnl
        slot.metrics.pnl_pct = pnl_pct
        slot.metrics.realized_pnl_usd = portfolio.realized_pnl
        slot.metrics.unrealized_pnl_usd = portfolio.position * (mark_price - portfolio.avg_entry_price)
        slot.metrics.simulated_order_count = portfolio.order_count
        slot.metrics.simulated_fill_count = portfolio.trade_count
        slot.last_bar_utc = bar.timestamp_utc.isoformat()

        # Provenance: first market bar consumed by this slot (observation window
        # lower bound), deterministically stamped on first sync.
        if slot.first_market_bar_utc is None:
            slot.first_market_bar_utc = bar.timestamp_utc.isoformat()

        # Position tracking & open positions
        if portfolio.position != Decimal("0"):
            slot.metrics.open_position_count = 1
            side = "LONG" if portfolio.position > Decimal("0") else "SHORT"
            slot.open_positions = [
                {
                    "symbol": bar.symbol,
                    "side": side,
                    "quantity": float(abs(portfolio.position)),
                    "entryPrice": float(portfolio.avg_entry_price),
                    "currentPrice": float(mark_price),
                    "unrealizedPnlUsd": float(slot.metrics.unrealized_pnl_usd),
                }
            ]
            # Exposure & risk utilization
            position_notional = abs(portfolio.position * mark_price)
            slot.metrics.exposure_pct = (
                (position_notional / equity * Decimal("100.0"))
                if equity > Decimal("0")
                else Decimal("0.0")
            )
            slot.metrics.risk_utilization_pct = (
                (abs(portfolio.position) / slot.max_position_units * Decimal("100.0"))
                if slot.max_position_units > Decimal("0")
                else Decimal("0.0")
            )
        else:
            slot.metrics.open_position_count = 0
            slot.open_positions = []
            slot.metrics.exposure_pct = Decimal("0.0")
            slot.metrics.risk_utilization_pct = Decimal("0.0")

        # Duration: measured from the slot's OWN observation-window start when
        # present (late joiners get an honest, window-local duration), else from
        # tournament start. Only ever uses a wall clock ceiling (worst-case).
        if slot.started_at_utc is not None:
            slot.metrics.duration_seconds = int(
                (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(slot.started_at_utc)
                ).total_seconds()
            )
        elif self._start_time_utc is not None:
            slot.metrics.duration_seconds = int(
                (datetime.now(timezone.utc) - self._start_time_utc).total_seconds()
            )

        # Decision & fill timestamps
        if decision_cid is not None:
            slot.metrics.signal_count += 1
            slot.metrics.last_signal_utc = bar.timestamp_utc.isoformat()

        # Update peak NAV and drawdown
        if equity > slot.peak_nav_usd:
            slot.peak_nav_usd = equity
        if slot.peak_nav_usd > Decimal("0"):
            dd = ((slot.peak_nav_usd - equity) / slot.peak_nav_usd) * Decimal("100.0")
            slot.metrics.current_drawdown_pct = dd
            if dd > slot.metrics.max_drawdown_pct:
                slot.metrics.max_drawdown_pct = dd

        # Update equity curve history (capped to last 100 points of recent M1 window)
        slot.equity_curve.append(
            {
                "timestampUtc": bar.timestamp_utc.isoformat(),
                "navUsd": float(equity),
                "pnlUsd": float(pnl),
            }
        )
        if len(slot.equity_curve) > 100:
            slot.equity_curve.pop(0)

    def record_feed_disconnect(self, reason: str) -> None:
        """Record feed disconnection and fail-closed halt."""
        self.halt(reason=f"Feed disconnected: {reason}", feed_health="DISCONNECTED")

    def record_feed_stale(self, age_ms: int, max_age_ms: int) -> None:
        """Record stale market data and fail-closed halt."""
        self.halt(
            reason=f"Feed data stale: observed {age_ms}ms > allowed {max_age_ms}ms",
            feed_health="STALE",
        )

    # ------------------------------------------------------------------
    # Controlled transient feed recovery (V2 follow-up, API-level opt-in /
    # CLI --enable-feed-recovery explicit opt-in)
    # ------------------------------------------------------------------

    def enter_feed_recovery(self, reason: str) -> str:
        """Mark the tournament as entering a controlled transient recovery.

        Every RUNNING slot transitions to FEED_RECOVERING; from that instant
        zero bars are consumed and zero decisions/orders are made until the
        episode exits (fail-closed quiescence during recovery).

        Returns a fresh evidence correlation_id for the episode, which the
        caller MUST reuse for every journaled phase of this episode.
        """
        with self._lock:
            if self._feed_recovery_active:
                raise DataContractError(
                    "ShadowTournamentSupervisor: feed recovery is already active; "
                    "no concurrent recovery episodes are allowed (fail-closed)."
                )
            if self._overall_status != "RUNNING":
                raise DataContractError(
                    "ShadowTournamentSupervisor: cannot enter feed recovery while "
                    f"status is {self._overall_status!r} (fail-closed)."
                )
            self._feed_recovery_active = True
            self._feed_health = "RECOVERING"
            recovery_cid = str(uuid.uuid4())
            for slot in self._slots.values():
                if slot.status == SlotExecutionState.RUNNING.value:
                    slot.status = SlotExecutionState.FEED_RECOVERING.value
            self._journal_system_event_unlocked(
                HealthEventKind.FEED_RECOVERING,
                recovery_cid,
                {"reason": reason},
            )
            self._update_metrics()
            return recovery_cid

    def exit_feed_recovery(self, correlation_id: str, resumed_bar_utc: str) -> None:
        """Successfully conclude a recovery episode and resume slots.

        RUNNING is restored only for slots that were FEED_RECOVERING; risk-halted
        slots stay RISK_HALTED (never silently resumed).
        """
        with self._lock:
            if not self._feed_recovery_active:
                raise DataContractError(
                    "ShadowTournamentSupervisor: exit_feed_recovery called with no "
                    "active recovery episode (fail-closed)."
                )
            self._feed_recovery_active = False
            self._feed_health = "HEALTHY"
            for slot in self._slots.values():
                if slot.status == SlotExecutionState.FEED_RECOVERING.value:
                    slot.status = SlotExecutionState.RUNNING.value
            self._journal_system_event_unlocked(
                HealthEventKind.FEED_RECOVERY_SUCCEEDED,
                correlation_id,
                {"resumed_bar_utc": resumed_bar_utc},
            )
            self._update_metrics()

    def fail_feed_recovery(self, correlation_id: str, reason: str) -> None:
        """Fail a recovery episode and halt the tournament fail-closed.

        Slots stop with TerminalReason.FEED_RECOVERY_FAILED; this is a terminal
        cause (no automatic retry, no silent resume).
        """
        with self._lock:
            self._feed_recovery_active = False
            if self._overall_status != "RUNNING":
                return  # already halted with an earlier preserved cause
            self._journal_system_event_unlocked(
                HealthEventKind.FEED_RECOVERY_FAILED,
                correlation_id,
                {"reason": reason},
            )
        self.halt(
            reason=f"Feed recovery failed: {reason}",
            feed_health="HALTED",
            terminal_reason=TerminalReason.FEED_RECOVERY_FAILED,
        )

    @property
    def feed_recovery_active(self) -> bool:
        return self._feed_recovery_active

    @property
    def last_accepted_bar_utc(self) -> Optional[str]:
        """UTC ISO timestamp of the last bar fully accepted for processing.

        Single authority for the recovery line of provenance: the next recovery
        episode resumes from the first bar strictly after this boundary.
        """
        if self._last_data_timestamp_utc is None:
            return None
        return self._last_data_timestamp_utc.isoformat()

    def journal_system_event(
        self,
        kind: HealthEventKind,
        correlation_id: str,
        payload: Dict[str, Any],
    ) -> List[str]:
        """Record a tournament-level SYSTEM event into every started slot journal.

        Systemic evidence (recovery phases, candidate admission) is mirrored into
        each active slot's flight recorder so replay/audit tools can render the
        full timeline per slot without cross-reading files. Returns the recorded
        event_ids.

        All internal mutation paths hold ``self._lock`` already (single write
        authority); they MUST call ``_journal_system_event_unlocked`` instead to
        avoid a re-entrant deadlock on the plain mutex. External callers (e.g.
        the CLI recovery journal callback) use this public wrapper.
        """
        with self._lock:
            return self._journal_system_event_unlocked(
                kind, correlation_id, payload
            )

    def _journal_system_event_unlocked(
        self,
        kind: HealthEventKind,
        correlation_id: str,
        payload: Dict[str, Any],
    ) -> List[str]:
        recorded: List[str] = []
        for slot_id, slot in self._slots.items():
            runner = slot.runner
            if runner is None or not getattr(runner, "_started", False):
                continue
            event_id = runner._health.record(
                kind=kind,
                correlation_id=correlation_id,
                payload=dict(payload),
            )
            recorded.append(event_id)
        return recorded

    # ------------------------------------------------------------------
    # Operator-driven dynamic candidate admission (V2 follow-up)
    # ------------------------------------------------------------------

    def stage_candidate_add(self, slot_id: str, strategy_id: str) -> Dict[str, Any]:
        """Validate and stage a late-join candidate add for the next bar boundary.

        Admission gate (ALL must hold; a single violation is a clean rejection):
        - slot_id is a valid, configured coordinate;
        - the slot is still UNASSIGNED (no runner attached);
        - strategy_id resolves to the approved INFRASTRUCTURE_TEST catalog
          (single authority — no fabricated candidate identities);
        - strategy_id is not already active or staged (no duplicates);
        - tournament capacity bounds are respected (active + staged < num_slots);
        - the tournament is currently RUNNING.

        Returns a typed result dict; the candidate is only materialized by
        ``apply_pending_candidate_adds`` at a finalized-bar boundary.
        """
        if self._overall_status != "RUNNING":
            return self._candidate_result(slot_id, strategy_id, "TOURNAMENT_NOT_RUNNING")
        if not _SLOT_ID_PATTERN.fullmatch(slot_id):
            return self._candidate_result(slot_id, strategy_id, "INVALID_SLOT_ID")
        slot = self._slots.get(slot_id)
        if slot is None:
            return self._candidate_result(slot_id, strategy_id, "UNKNOWN_SLOT")
        if slot.runner is not None and slot.status != "UNASSIGNED":
            return self._candidate_result(slot_id, strategy_id, "SLOT_OCCUPIED")
        if self._candidate_resolver is None or self._slot_builder is None:
            return self._candidate_result(
                slot_id, strategy_id, "CANDIDATE_ADD_UNCONFIGURED"
            )
        if self._candidate_resolver(strategy_id) is None:
            return self._candidate_result(
                slot_id, strategy_id, "UNKNOWN_STRATEGY_ID"
            )

        active_ids = {
            s.strategy_id for s in self._slots.values() if s.runner is not None
        }
        staged_ids = {p["strategy_id"] for p in self._pending_candidate_adds}
        if strategy_id in active_ids or strategy_id in staged_ids:
            return self._candidate_result(slot_id, strategy_id, "DUPLICATE_STRATEGY_ID")

        staged_slots = {p["slot_id"] for p in self._pending_candidate_adds}
        if len(active_ids) + len(staged_slots) + 1 > len(self._slots):
            return self._candidate_result(slot_id, strategy_id, "CAPACITY_EXCEEDED")

        with self._lock:
            # Re-check under the lock (status could have changed concurrently).
            current = self._slots.get(slot_id)
            if current is None or (
                current.runner is not None and current.status != "UNASSIGNED"
            ):
                return self._candidate_result(slot_id, strategy_id, "SLOT_OCCUPIED")
            entry: Dict[str, Any] = {
                "slot_id": slot_id,
                "strategy_id": strategy_id,
                "staged_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            self._pending_candidate_adds.append(entry)
            self._journal_system_event_unlocked(
                HealthEventKind.CANDIDATE_ADDED,
                str(uuid.uuid4()),
                {
                    "slot_id": slot_id,
                    "strategy_id": strategy_id,
                    "event": "CANDIDATE_STAGED",
                    "staged_at_utc": entry["staged_at_utc"],
                },
            )
        return self._candidate_result(slot_id, strategy_id, "STAGED", ok=True)

    @staticmethod
    def _candidate_result(
        slot_id: str, strategy_id: str, reason: str, ok: bool = False
    ) -> Dict[str, Any]:
        return {
            "slotId": slot_id,
            "strategyId": strategy_id,
            "ok": ok,
            "reason": reason,
        }

    def _materialize_candidate_adds(self, bar: SyntheticBar) -> None:
        """Materialize staged candidate adds at a finalized-bar boundary.

        Called at the top of ``process_bar`` BEFORE any slot consumes the bar so
        that a late joiner starts consuming at exactly this bar (deterministic
        window identity). The caller holds the supervisor lock. Raises
        DataContractError if the runtime is not configured for candidate adds
        (fail-closed, never silently dropped).
        """
        if not self._pending_candidate_adds:
            return
        if self._slot_builder is None or self._candidate_resolver is None:
            raise DataContractError(
                "ShadowTournamentSupervisor: staged candidate adds require a slot "
                "builder and candidate resolver (runtime unconfigured)."
            )

        batch_ts = datetime.now(timezone.utc)
        cohort_id = f"{self._tournament_id}:ADD:{batch_ts.strftime('%Y%m%d_%H%M%S_%f')}"
        results: List[Dict[str, Any]] = []

        pending = list(self._pending_candidate_adds)
        for entry in pending:
            slot_id = entry["slot_id"]
            strategy_id = entry["strategy_id"]
            strategy = self._candidate_resolver(strategy_id)
            if strategy is None:
                results.append(
                    self._candidate_result(
                        slot_id, strategy_id, "UNKNOWN_STRATEGY_ID"
                    )
                )
                self._journal_system_event_unlocked(
                    HealthEventKind.CANDIDATE_REJECTED,
                    str(uuid.uuid4()),
                    {
                        "slot_id": slot_id,
                        "strategy_id": strategy_id,
                        "reason": "UNKNOWN_STRATEGY_ID",
                    },
                )
                continue

            slot, runner = self._slot_builder(slot_id, strategy)
            # Late-join provenance: new cohort, no cross-cohort ranking.
            slot.observation_kind = "LATE_JOIN"
            slot.cohort_id = cohort_id
            slot.comparison_window_id = cohort_id
            slot.started_at_utc = batch_ts.isoformat()
            runner.start()
            slot.status = SlotExecutionState.RUNNING.value
            slot.metrics.duration_seconds = 0
            self._slots[slot_id] = slot
            self._closed_positions_history.setdefault(slot_id, [])

            self._journal_system_event_unlocked(
                HealthEventKind.CANDIDATE_ADDED,
                str(uuid.uuid4()),
                {
                    "slot_id": slot_id,
                    "strategy_id": strategy_id,
                    "event": "CANDIDATE_ADMITTED",
                    "cohort_id": cohort_id,
                    "bar_utc": bar.timestamp_utc.isoformat(),
                    "started_at_utc": slot.started_at_utc,
                    "baseline_nav_usd": str(slot.baseline_nav_usd),
                },
            )
            results.append(
                self._candidate_result(slot_id, strategy_id, "ADMITTED", ok=True)
            )

        # Every staged entry was either admitted or rejected; drop the whole
        # batch. New stages can only arrive from another thread holding the
        # lock, so nothing new can appear here mid-materialization.
        self._pending_candidate_adds.clear()

        self._operator_action_results.extend(results)
        logger.info(
            "ShadowTournamentSupervisor: materialized candidate adds at bar %s: %s",
            bar.timestamp_utc,
            results,
        )

    @property
    def last_operator_action_results(self) -> List[Dict[str, Any]]:
        """Results of the most recent operator-driven mutation batch."""
        with self._lock:
            return list(self._operator_action_results)

    def clear_operator_action_results(self) -> None:
        """Clear recorded operator action results (caller has consumed them)."""
        with self._lock:
            self._operator_action_results.clear()

    def _update_metrics(self) -> None:
        """Export operational Prometheus metrics if registry configured."""
        if self._metrics_registry is None:
            return

        uptime_seconds = (
            (datetime.now(timezone.utc) - self._start_time_utc).total_seconds()
            if self._start_time_utc
            else 0.0
        )

        # Global metrics
        self._metrics_registry.set_gauge(
            "acash_shadow_tournament_uptime_seconds", float(uptime_seconds)
        )
        self._metrics_registry.set_gauge(
            "acash_shadow_tournament_canonical_capital_usd", 0.0
        )
        self._metrics_registry.set_gauge(
            "acash_shadow_tournament_real_orders_total", 0.0
        )
        self._metrics_registry.set_gauge(
            "acash_shadow_tournament_is_simulated_only", 1.0
        )

        # Aggregate execution state (V2 Defect D): one-hot over the derived
        # tournament-level state so dashboards can chart severity over time.
        aggregate_state = self._aggregate_execution_state()
        for state in SlotExecutionState:
            self._metrics_registry.set_gauge(
                "acash_shadow_tournament_execution_state",
                1.0 if state.value == aggregate_state else 0.0,
                {"state": state.value},
            )

        # Feed health (V2 follow-up): bounded one-hot gauge so dashboards can
        # chart the recovery lifecycle (HEALTHY/RECOVERING/STALE/HALTED/
        # DISCONNECTED/UNKNOWN) over time.
        for feed_state in ("HEALTHY", "RECOVERING", "STALE", "HALTED", "DISCONNECTED", "UNKNOWN"):
            self._metrics_registry.set_gauge(
                "acash_shadow_tournament_feed_health",
                1.0 if self._feed_health == feed_state else 0.0,
                {"state": feed_state},
            )

        # Per-slot metrics
        for slot_id, slot in self._slots.items():
            labels = {"slot": slot_id, "strategy_id": slot.strategy_id}
            # Per-slot execution state (V2 Defect D).
            for state in SlotExecutionState:
                self._metrics_registry.set_gauge(
                    "acash_shadow_tournament_slot_execution_state",
                    1.0 if slot.status == state.value else 0.0,
                    {"slot": slot_id, "state": state.value},
                )
            self._metrics_registry.set_gauge(
                "acash_shadow_tournament_virtual_nav_usd",
                float(slot.metrics.current_nav_usd),
                labels,
            )
            self._metrics_registry.set_gauge(
                "acash_shadow_tournament_virtual_pnl_usd",
                float(slot.metrics.pnl_usd),
                labels,
            )
            self._metrics_registry.set_gauge(
                "acash_shadow_tournament_virtual_pnl_pct",
                float(slot.metrics.pnl_pct),
                labels,
            )
            self._metrics_registry.set_gauge(
                "acash_shadow_tournament_simulated_orders_total",
                float(slot.metrics.simulated_order_count),
                labels,
            )
            self._metrics_registry.set_gauge(
                "acash_shadow_tournament_simulated_fills_total",
                float(slot.metrics.simulated_fill_count),
                labels,
            )
            self._metrics_registry.set_gauge(
                "acash_shadow_tournament_max_drawdown_pct",
                float(slot.metrics.max_drawdown_pct),
                labels,
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete tournament state conforming to dashboard TypeScript contract."""
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            uptime_seconds = int(
                (datetime.now(timezone.utc) - self._start_time_utc).total_seconds()
                if self._start_time_utc
                else 0
            )

            # Build leaderboard rankings with cohort integrity (V2 follow-up).
            # A rank is only meaningful WITHIN an observation cohort because each
            # cohort independently defines its own observation window. Ranks are
            # assigned per cohort when a cohort has >= 2 comparable members;
            # single-member cohorts are reported UNRANKED (rank = null). This is
            # the honest alternative to silently ranking an apples-vs-oranges
            # late joiner against boot-time peers.
            ranked_statuses = {
                SlotExecutionState.RUNNING.value,
                SlotExecutionState.RISK_HALTED.value,
                SlotExecutionState.FEED_HALTED.value,
                SlotExecutionState.STOPPED.value,
            }
            comparable_slots = [
                s
                for s in self._slots.values()
                if s.status in ranked_statuses and s.metrics.simulated_fill_count > 0
            ]
            cohorts: Dict[Optional[str], List[TournamentSlot]] = {}
            for s in comparable_slots:
                cohorts.setdefault(s.comparison_window_id, []).append(s)
            for cohort_slots in cohorts.values():
                cohort_slots.sort(key=lambda x: x.metrics.pnl_usd, reverse=True)

            ranked_slots: List[Dict[str, Any]] = []
            has_late_joiners = any(
                s.observation_kind == "LATE_JOIN" for s in comparable_slots
            )
            for cohort_slots in cohorts.values():
                rankable = len(cohort_slots) >= 2
                for rank_idx, s in enumerate(cohort_slots, 1):
                    window_anchor = s.started_at_utc
                    start_ts = (
                        datetime.fromisoformat(window_anchor)
                        if window_anchor
                        else self._start_time_utc
                    )
                    obs_duration = (
                        int(
                            (
                                datetime.now(timezone.utc) - start_ts
                            ).total_seconds()
                        )
                        if start_ts
                        else 0
                    )
                    ranked_slots.append(
                        {
                            "rank": rank_idx if rankable else None,
                            "slotId": s.slot_id,
                            "strategyId": s.strategy_id,
                            "navUsd": float(s.metrics.current_nav_usd),
                            "pnlUsd": float(s.metrics.pnl_usd),
                            "pnlPct": float(s.metrics.pnl_pct),
                            "winRatePct": float(s.metrics.win_rate_pct)
                            if s.metrics.win_rate_pct is not None
                            else None,
                            "maxDrawdownPct": float(s.metrics.max_drawdown_pct),
                            "simulatedFills": s.metrics.simulated_fill_count,
                            "observationKind": s.observation_kind,
                            "cohortId": s.cohort_id,
                            "comparisonWindowId": s.comparison_window_id,
                            "observationDurationSeconds": obs_duration,
                        }
                    )

            comp_avail = (
                "AVAILABLE"
                if len(cohorts) >= 1 and any(len(c) >= 2 for c in cohorts.values())
                else "INSUFFICIENT_SAMPLE"
            )
            if comp_avail == "AVAILABLE" and not has_late_joiners:
                comp_note = (
                    "Tournament in progress with active fills; "
                    "all ranked slots share the boot observation window."
                )
            elif comp_avail == "AVAILABLE" and has_late_joiners:
                comp_note = (
                    "Tournament in progress with active fills; late-join slots "
                    "are ranked ONLY within their own cohort (comparisonWindowId), "
                    "never against boot-time peers."
                )
            else:
                comp_note = "Tournament awaiting sufficient fill sample across active strategies."

            return {
                "global": {
                    "tournamentId": self._tournament_id,
                    "label": "Shadow Alpha Tournament",
                    "governanceBadge": "SHADOW / SIMULATED ONLY",
                    "canonicalCapitalUsd": 0.00,
                    "realOrderCount": 0,
                    "noRealOrders": True,
                    "feedHealth": self._feed_health,
                    "runtimeUptimeSeconds": uptime_seconds,
                    "acashCommitSha": self._acash_commit_sha,
                    "deploymentImageId": self._deployment_image_id,
                    "tournamentStartUtc": self._start_time_utc.isoformat()
                    if self._start_time_utc
                    else None,
                    "lastDataTimestampUtc": self._last_data_timestamp_utc.isoformat()
                    if self._last_data_timestamp_utc
                    else None,
                    "lastSuccessfulUpdateUtc": self._last_successful_update_utc.isoformat(),
                    "overallStatus": self._overall_status,
                    "executionState": self._aggregate_execution_state(),
                    "haltReason": self._halt_reason,
                },
                "slots": {
                    slot_id: slot.to_dict() for slot_id, slot in self._slots.items()
                },
                "leaderboard": {
                    "rankedSlots": ranked_slots,
                    "comparisonAvailability": comp_avail,
                    "comparisonNote": comp_note,
                },
                "_meta": {
                    "fetchedAtUtc": now_iso,
                    "dataSource": "SHADOW_RUNTIME",
                    "isMockData": False,
                    "mockNotice": (
                        "SHADOW RUNTIME · SIMULATED RESEARCH INFRASTRUCTURE ONLY · "
                        "NOT ACASH RESEARCH EVIDENCE · CANONICAL CAPITAL = $0.00 · "
                        "REAL ORDERS = 0 · NO_REAL_ORDERS = true"
                    ),
                },
            }

    def export_status_json(self, output_path: Path) -> None:
        """Export tournament state atomically to JSON file for dashboard polling."""
        payload = self.to_dict()
        tmp_path = output_path.with_suffix(".tmp")
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
        tmp_path.replace(output_path)


def build_slot_runner(
    *,
    storage_dir: Path,
    tournament_id: str,
    slot_id: str,
    strategy: PaperStrategyProtocol,
    acash_commit_sha: str,
    instrument: str,
    data_source: str,
    market_domain: str,
    max_market_data_age_ms: Optional[int],
    signal_sizing_policy: SignalSizingPolicy,
    nav_sizing_notional_pct: Decimal,
    baseline_nav_usd: Decimal = Decimal("1000.00"),
) -> Tuple[TournamentSlot, PaperSessionRunner]:
    """Single authority that builds a slot runner for a strategy.

    Used both at boot (create_default_shadow_tournament) and for operator-driven
    late-join candidate adds (supervisor slot_builder override). Every slot
    constructor path flows through this one helper so provenance defaults
    (observation_kind, baseline_nav_usd) can never diverge.
    """
    cfg = PaperSessionConfig(
        session_id=f"{tournament_id}-SLOT-{slot_id}",
        strategy_id=strategy.strategy_id,
        strategy_version=strategy.strategy_version,
        instrument=instrument,
        initial_cash=Decimal("1000.00"),
        max_position_units=Decimal("10.0"),
        max_notional=Decimal("100000.0"),
        max_daily_loss=Decimal("100.0"),
        fill_slippage_bps=Decimal("5.0"),
        fill_commission_per_unit=Decimal("0.0004"),
        prng_seed=42 + ord(slot_id),
        git_commit=acash_commit_sha,
        component_version="1.0.0",
        journal_path=storage_dir / f"{tournament_id}_slot_{slot_id.lower()}.journal.jsonl",
        snapshot_path=storage_dir / f"{tournament_id}_slot_{slot_id.lower()}.snapshots.jsonl",
        data_source=data_source,
        market_domain=market_domain,
        max_market_data_age_ms=max_market_data_age_ms,
        signal_sizing_policy=signal_sizing_policy,
        nav_sizing_notional_pct=nav_sizing_notional_pct,
    )
    runner = PaperSessionRunner(cfg, strategy=strategy)
    slot = TournamentSlot(
        slot_id=slot_id,
        strategy_id=strategy.strategy_id,
        strategy_name=f"Strategy ({slot_id}): {strategy.strategy_id}",
        strategy_version=strategy.strategy_version,
        status="INITIALIZING",
        session_id=cfg.session_id,
        config_hash=cfg.compute_config_hash(),
        acash_commit_sha=acash_commit_sha,
        runner=runner,
        observation_kind="CONTINUOUS",  # boot-time slot; late-join overrides
        comparison_window_id=None,  # assigned by the tournament creator
        cohort_id=None,
        baseline_nav_usd=baseline_nav_usd,
    )
    return slot, runner


def create_default_shadow_tournament(
    storage_dir: Path,
    acash_commit_sha: str,
    slot_strategies: Optional[Dict[str, PaperStrategyProtocol]] = None,
    metrics_registry: Optional[MetricsRegistry] = None,
    *,
    num_slots: int = 3,
    auto_mount_infrastructure_candidates: bool = False,
    infra_mount_count: Optional[int] = None,
    signal_sizing_policy: Optional[SignalSizingPolicy] = None,
    nav_sizing_notional_pct: Decimal = SAFE_V2_NAV_SIZING_PCT,
    instrument: str = "BTCUSDT",
    data_source: str = "binance.public.klines",
    market_domain: str = "SPOT",
    max_market_data_age_ms: Optional[int] = 65_000,
) -> ShadowTournamentSupervisor:
    """Construct a canonical Shadow Alpha Tournament instance with globally unique ID.

    Slot fanout is configurable (num_slots). For each slot coordinate:
    - an injected strategy in slot_strategies {slot_id: strategy} is mounted as a
      live simulated runner with INFRA_FIXED_QUANTITY sizing (preserves the
      canonical Slot A / H01 fixed quantity 1.0);
    - otherwise the slot stays UNASSIGNED (honest reporting — no phantom alpha).
    Slot A defaults to InfrastructureTestStrategy when not injected.

    When auto_mount_infrastructure_candidates is True, the deterministic V2
    catalog (INFRASTRUCTURE_CANDIDATES_10SLOT) is mounted for any slot whose
    coordinate has a catalog entry and which was not explicitly injected. This
    is an explicit infrastructure-exercise opt-in (INFRA_TEST only, zero alpha
    candidates) for the 10-slot V2 readiness layout.

    Parameters:
    - storage_dir: Destination path for slot journals and manifests.
    - acash_commit_sha: Commit SHA for provenance audit.
    - slot_strategies: Optional map of slot_id -> StrategyProtocol instance.
    - num_slots: Number of slot coordinates in [1, 26] (default 3).
    - auto_mount_infrastructure_candidates: Mount deterministic INFRA_TEST
      candidates for catalog slot coordinates (default False).
    - infra_mount_count: Maximum number of CATALOG candidates to auto-mount
      (injected strategies are excluded from this budget). None mounts the full
      catalog; the CLI operational layout uses 3. 0 is a dead config and is
      rejected fail-closed.
    - signal_sizing_policy: Tournament sizing policy. None resolves to
      NAV_RELATIVE_PERCENT for auto-mounted catalog candidates (safe 10% of NAV)
      and INFRA_FIXED_QUANTITY otherwise (legacy canonical layout).
    - nav_sizing_notional_pct: NAV-relative notional share in (0, 100]. Normalized
      to 0.0 when the resolved policy is INFRA_FIXED_QUANTITY (the runner rejects
      any dead sizing config).
    - instrument: Target symbol (default BTCUSDT).
    - data_source: Feed data source provider string for manifest provenance.
    - market_domain: Market domain string (e.g. SPOT, CRYPTO_SPOT).
    - max_market_data_age_ms: Max market data staleness horizon before fail-closed halt.
    """
    storage_dir.mkdir(parents=True, exist_ok=True)

    if infra_mount_count is not None:
        if not auto_mount_infrastructure_candidates:
            raise DataContractError(
                "create_default_shadow_tournament: infra_mount_count requires "
                "auto_mount_infrastructure_candidates=True (dead config, fail-closed)."
            )
        if not (1 <= infra_mount_count <= num_slots):
            raise DataContractError(
                f"create_default_shadow_tournament: infra_mount_count must be in "
                f"[1, num_slots={num_slots}], got {infra_mount_count} (fail-closed)."
            )

    resolved_policy = signal_sizing_policy
    if resolved_policy is None:
        resolved_policy = (
            SignalSizingPolicy.NAV_RELATIVE_PERCENT
            if auto_mount_infrastructure_candidates
            else SignalSizingPolicy.INFRA_FIXED_QUANTITY
        )
    if (
        resolved_policy == SignalSizingPolicy.NAV_RELATIVE_PERCENT
        and not (Decimal("0") < nav_sizing_notional_pct <= Decimal("100"))
    ):
        raise DataContractError(
            "create_default_shadow_tournament: NAV_RELATIVE sizing requires "
            f"0 < nav_sizing_notional_pct <= 100, got {nav_sizing_notional_pct} "
            "(fail-closed)."
        )
    effective_nav_pct = (
        nav_sizing_notional_pct
        if resolved_policy == SignalSizingPolicy.NAV_RELATIVE_PERCENT
        else Decimal("0")
    )

    # Globally unique tournament ID: timestamp with seconds + 8 hex chars
    unique_suffix = uuid.uuid4().hex[:8]
    tournament_id = (
        f"SHADOW-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{unique_suffix}"
    )

    strategies = slot_strategies or {}
    _INJECTED_SIZING = SignalSizingPolicy.INFRA_FIXED_QUANTITY  # canonical fixed qty

    def _mount(
        slot_id: str, strategy: PaperStrategyProtocol, sizing: SignalSizingPolicy
    ) -> TournamentSlot:
        slot, _ = build_slot_runner(
            storage_dir=storage_dir,
            tournament_id=tournament_id,
            slot_id=slot_id,
            strategy=strategy,
            acash_commit_sha=acash_commit_sha,
            instrument=instrument,
            data_source=data_source,
            market_domain=market_domain,
            max_market_data_age_ms=max_market_data_age_ms,
            signal_sizing_policy=(
                sizing if sizing is not None else resolved_policy
            ),
            nav_sizing_notional_pct=(
                effective_nav_pct if sizing is resolved_policy else Decimal("0")
            ),
        )
        slot.cohort_id = tournament_id
        slot.comparison_window_id = tournament_id
        return slot

    slots: Dict[str, TournamentSlot] = {}
    catalog_mounted = 0

    # Deterministic fanout: num_slots coordinates in [A..Z].
    for slot_id in slot_ids_for_count(num_slots):
        strategy = strategies.get(slot_id)
        if strategy is not None:
            slots[slot_id] = _mount(slot_id, strategy, _INJECTED_SIZING)
            continue
        if slot_id == "A":
            strategy = InfrastructureTestStrategy(
                fast_period=3,
                slow_period=5,
                trade_quantity=Decimal("1.0"),
                symbol=instrument,
            )
            slots[slot_id] = _mount(slot_id, strategy, _INJECTED_SIZING)
            continue
        if auto_mount_infrastructure_candidates:
            candidate = get_infrastructure_candidate(slot_id, symbol=instrument)
            if candidate is None:
                slots[slot_id] = _unassigned_slot(tournament_id, slot_id, acash_commit_sha)
                continue
            if infra_mount_count is not None and catalog_mounted >= infra_mount_count:
                slots[slot_id] = _unassigned_slot(tournament_id, slot_id, acash_commit_sha)
                continue
            catalog_mounted += 1
            slots[slot_id] = _mount(slot_id, candidate, resolved_policy)
            continue
        slots[slot_id] = _unassigned_slot(tournament_id, slot_id, acash_commit_sha)

    return ShadowTournamentSupervisor(
        tournament_id=tournament_id,
        slots=slots,
        acash_commit_sha=acash_commit_sha,
        metrics_registry=metrics_registry,
        slot_builder=(
            lambda slot_id, strategy: build_slot_runner(
                storage_dir=storage_dir,
                tournament_id=tournament_id,
                slot_id=slot_id,
                strategy=strategy,
                acash_commit_sha=acash_commit_sha,
                instrument=instrument,
                data_source=data_source,
                market_domain=market_domain,
                max_market_data_age_ms=max_market_data_age_ms,
                signal_sizing_policy=resolved_policy,
                nav_sizing_notional_pct=effective_nav_pct,
            )
        ),
        candidate_resolver=(
            lambda strategy_id: get_infrastructure_candidate_by_strategy_id(
                strategy_id, symbol=instrument
            )
        ),
    )


def _unassigned_slot(
    tournament_id: str, slot_id: str, acash_commit_sha: str
) -> TournamentSlot:
    """Canonical UNASSIGNED slot with honest zero-provenance reporting."""
    return TournamentSlot(
        slot_id=slot_id,
        strategy_id="UNASSIGNED",
        strategy_name=(
            f"UNASSIGNED — Awaiting Human Strategy Selection (H02)"
        ),
        strategy_version="N/A",
        status="UNASSIGNED",
        session_id=f"{tournament_id}-SLOT-{slot_id}-UNASSIGNED",
        config_hash="0" * 64,
        acash_commit_sha=acash_commit_sha,
        runner=None,
        halt_reason=(
            "No candidate selected. Zero alpha candidates approved in repo."
        ),
        observation_kind="NONE",
        cohort_id=None,
        comparison_window_id=None,
    )
