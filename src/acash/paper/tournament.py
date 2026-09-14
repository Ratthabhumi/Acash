"""ACASH Paper Trading — Shadow Alpha Tournament Core Engine.

Governance Invariants (Non-Negotiable):
- SHADOW / SIMULATED RESEARCH INFRASTRUCTURE ONLY — NOT Paper GO / NOT Live / NOT HYP_003
- Canonical Capital = $0.00 | Real Orders Dispatched = 0 | NO_REAL_ORDERS = True
- Isolated virtual portfolio state for each strategy slot (A, B, C)
- Zero cross-strategy state leakage (virtual cash, virtual positions, virtual orders, virtual fills)
- Synchronized shared feed: all active slots receive the exact same market bar
- Independent flight recorder journals and manifests per slot
- Fail-closed lifecycle: feed disconnect/stale data halts all active slots and seals journals
- Read-only dashboard representation: zero trading controls or mutation endpoints
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.paper.health import HealthEventKind, PaperHealthMonitor, TerminalReason
from acash.paper.metrics import MetricsRegistry
from acash.paper.runner import (
    PaperSessionConfig,
    PaperSessionRunner,
    SyntheticBar,
)
from acash.paper.strategy import (
    InfrastructureTestStrategy,
    PaperStrategyProtocol,
    SignalDirection,
    StrategySignal,
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

SLOT_IDS = ("A", "B", "C")


class SlotExecutionState(str, Enum):
    """Granular per-slot & aggregate execution states (Tournament V2 Defect D).

    Surfaced in slot status, aggregate `executionState`, API JSON, Prometheus
    metrics, and the dashboard contract. Replaces the former coarse HALTED
    bucket so operators can distinguish WHY a slot is not trading:

    - RUNNING            slot actively processing synchronized bars
    - RISK_HALTED        kill switch active (MAX_DAILY_LOSS) on this slot
    - FEED_HALTED        halted fail-closed due to feed disconnect/staleness
    - STOPPED            stopped by operator/normal shutdown
    - UNASSIGNED         no runner attached
    """

    RUNNING = "RUNNING"
    RISK_HALTED = "RISK_HALTED"
    FEED_HALTED = "FEED_HALTED"
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
    status: str  # SlotExecutionState: RUNNING|RISK_HALTED|FEED_HALTED|STOPPED|UNASSIGNED
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

    def __post_init__(self) -> None:
        if self.slot_id not in SLOT_IDS:
            raise DataContractError(
                f"TournamentSlot: invalid slot_id '{self.slot_id}'. Must be one of {SLOT_IDS}"
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
    ) -> None:
        self._tournament_id = tournament_id
        self._slots = slots
        self._acash_commit_sha = acash_commit_sha
        self._deployment_image_id = deployment_image_id
        self._metrics_registry = metrics_registry
        self._lock = threading.Lock()

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
            s: [] for s in SLOT_IDS
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
        RISK_HALTED > FEED_HALTED > STOPPED > RUNNING > UNASSIGNED > NOT_STARTED.
        When every slot is halted, the halt kind is preserved at aggregate level;
        otherwise the most severe active state wins.
        """
        slot_states = [s.status for s in self._slots.values()]
        priority = [
            SlotExecutionState.RISK_HALTED,
            SlotExecutionState.FEED_HALTED,
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

            for slot_id, slot in self._slots.items():
                if slot.status != "RUNNING":
                    continue
                # Granular execution state: an already risk-halted slot stays
                # RISK_HALTED; feed failures -> FEED_HALTED; else STOPPED.
                if slot.runner is not None and slot.runner.kill_switch_active:
                    slot.status = SlotExecutionState.RISK_HALTED.value
                elif feed_health in ("DISCONNECTED", "STALE"):
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

        # Duration
        if self._start_time_utc is not None:
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

            # Build leaderboard rankings
            ranked_slots: List[Dict[str, Any]] = []
            ranked_statuses = {
                SlotExecutionState.RUNNING.value,
                SlotExecutionState.RISK_HALTED.value,
                SlotExecutionState.FEED_HALTED.value,
                SlotExecutionState.STOPPED.value,
            }
            active_slots = [
                s
                for s in self._slots.values()
                if s.status in ranked_statuses and s.metrics.simulated_fill_count > 0
            ]
            active_slots.sort(key=lambda s: s.metrics.pnl_usd, reverse=True)

            for rank_idx, s in enumerate(active_slots, 1):
                ranked_slots.append(
                    {
                        "rank": rank_idx,
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
                    }
                )

            comp_avail = (
                "AVAILABLE"
                if len(active_slots) >= 2
                else "INSUFFICIENT_SAMPLE"
            )
            comp_note = (
                "Tournament in progress with active fills."
                if comp_avail == "AVAILABLE"
                else "Tournament awaiting sufficient fill sample across active strategies."
            )

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


def create_default_shadow_tournament(
    storage_dir: Path,
    acash_commit_sha: str,
    slot_strategies: Optional[Dict[str, PaperStrategyProtocol]] = None,
    metrics_registry: Optional[MetricsRegistry] = None,
    *,
    instrument: str = "BTCUSDT",
    data_source: str = "binance.public.klines",
    market_domain: str = "SPOT",
    max_market_data_age_ms: Optional[int] = 65_000,
) -> ShadowTournamentSupervisor:
    """Construct a canonical Shadow Alpha Tournament instance with globally unique ID.

    Parameters:
    - storage_dir: Destination path for slot journals and manifests.
    - acash_commit_sha: Commit SHA for provenance audit.
    - slot_strategies: Optional map of slot_id -> StrategyProtocol instance.
      If a slot has no strategy provided, Slot A defaults to InfrastructureTestStrategy
      while Slots B and C remain UNASSIGNED (honest reporting).
    - instrument: Target symbol (default BTCUSDT).
    - data_source: Feed data source provider string for manifest provenance.
    - market_domain: Market domain string (e.g. SPOT, CRYPTO_SPOT).
    - max_market_data_age_ms: Max market data staleness horizon before fail-closed halt.
    """
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Globally unique tournament ID: timestamp with seconds + 8 hex chars
    unique_suffix = uuid.uuid4().hex[:8]
    tournament_id = (
        f"SHADOW-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{unique_suffix}"
    )

    strategies = slot_strategies or {}

    # Helper to build a slot runner with its own strategy instance
    def _build_slot_runner(slot_id: str, strategy: PaperStrategyProtocol) -> Tuple[TournamentSlot, PaperSessionRunner]:
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
        )
        return slot, runner

    slots: Dict[str, TournamentSlot] = {}

    # Slot A: injected strategy or default InfrastructureTestStrategy
    if "A" in strategies:
        slot_a, _ = _build_slot_runner("A", strategies["A"])
    else:
        default_strat_a = InfrastructureTestStrategy(
            fast_period=3,
            slow_period=5,
            trade_quantity=Decimal("1.0"),
            symbol=instrument,
        )
        slot_a, _ = _build_slot_runner("A", default_strat_a)
    slots["A"] = slot_a

    # Slot B: injected strategy or UNASSIGNED
    if "B" in strategies:
        slot_b, _ = _build_slot_runner("B", strategies["B"])
    else:
        slot_b = TournamentSlot(
            slot_id="B",
            strategy_id="UNASSIGNED",
            strategy_name="UNASSIGNED — Awaiting Human Strategy Selection (H02)",
            strategy_version="N/A",
            status="UNASSIGNED",
            session_id=f"{tournament_id}-SLOT-B-UNASSIGNED",
            config_hash="0" * 64,
            acash_commit_sha=acash_commit_sha,
            runner=None,
            halt_reason="No candidate selected. Zero alpha candidates approved in repo.",
        )
    slots["B"] = slot_b

    # Slot C: injected strategy or UNASSIGNED
    if "C" in strategies:
        slot_c, _ = _build_slot_runner("C", strategies["C"])
    else:
        slot_c = TournamentSlot(
            slot_id="C",
            strategy_id="UNASSIGNED",
            strategy_name="UNASSIGNED — Awaiting Human Strategy Selection (H02)",
            strategy_version="N/A",
            status="UNASSIGNED",
            session_id=f"{tournament_id}-SLOT-C-UNASSIGNED",
            config_hash="0" * 64,
            acash_commit_sha=acash_commit_sha,
            runner=None,
            halt_reason="No candidate selected. Zero alpha candidates approved in repo.",
        )
    slots["C"] = slot_c

    return ShadowTournamentSupervisor(
        tournament_id=tournament_id,
        slots=slots,
        acash_commit_sha=acash_commit_sha,
        metrics_registry=metrics_registry,
    )
