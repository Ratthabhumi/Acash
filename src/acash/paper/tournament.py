"""ACASH Paper Trading — Shadow Alpha Tournament Core Engine.

Governance Invariants (Non-Negotiable):
- SHADOW / SIMULATED RESEARCH INFRASTRUCTURE ONLY — NOT Paper GO / NOT Live / NOT HYP_003
- Canonical Capital = $0.00 | Real Orders Dispatched = 0 | NO_REAL_ORDERS = True
- Isolated virtual portfolio state for each strategy slot (A, B, C)
- Zero cross-strategy state leakage (virtual cash, virtual positions, virtual orders, virtual fills)
- Synchronized shared feed: all active slots receive the exact same market bar
- Independent flight recorder journals and manifests per slot
- Read-only dashboard representation: zero trading controls or mutation endpoints
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from acash.core.domain.exceptions import DataContractError
from acash.paper.journal import JournalEventType, PaperEventJournal
from acash.paper.metrics import MetricsRegistry
from acash.paper.runner import (
    PaperSessionConfig,
    PaperSessionRunner,
    SyntheticBar,
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
    exposure_pct: Decimal = Decimal("0.00")
    risk_utilization_pct: Decimal = Decimal("0.00")
    open_position_count: int = 0
    simulated_order_count: int = 0
    simulated_fill_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate_pct: Optional[Decimal] = None
    signal_count: int = 0
    last_signal_utc: Optional[str] = None
    last_fill_utc: Optional[str] = None
    duration_seconds: int = 0


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
    status: str  # 'RUNNING' | 'HALTED' | 'UNASSIGNED' | 'INITIALIZING'
    session_id: str
    config_hash: str
    acash_commit_sha: str
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
        return {
            "slotId": self.slot_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "strategyVersion": self.strategy_version,
            "governanceLabel": "INFRASTRUCTURE_TEST_STRATEGY_ONLY"
            if "INFRA-TEST" in self.strategy_id
            else "SHADOW_ALPHA_CANDIDATE",
            "status": self.status,
            "sessionId": self.session_id,
            "configHash": self.config_hash,
            "acashCommitSha": self.acash_commit_sha,
            "haltReason": self.halt_reason,
            "lastBarUtc": self.last_bar_utc,
            "openPositions": self.open_positions,
            "recentFills": self.recent_fills,
            "equityCurve": self.equity_curve,
            "metrics": {
                "initialNavUsd": float(self.metrics.initial_nav_usd),
                "currentNavUsd": float(self.metrics.current_nav_usd),
                "pnlUsd": float(self.metrics.pnl_usd),
                "pnlPct": float(self.metrics.pnl_pct),
                "realizedPnlUsd": float(self.metrics.realized_pnl_usd),
                "unrealizedPnlUsd": float(self.metrics.unrealized_pnl_usd),
                "maxDrawdownPct": float(self.metrics.max_drawdown_pct),
                "currentDrawdownPct": float(self.metrics.current_drawdown_pct),
                "exposurePct": float(self.metrics.exposure_pct),
                "riskUtilizationPct": float(self.metrics.risk_utilization_pct),
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
                "durationSeconds": self.metrics.duration_seconds,
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
    4. IMMUTABLE REPORTING: Status dictionary faithfully reflects unassigned slots
       rather than fabricating simulated alpha candidates.
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

    def start(self) -> None:
        """Start the tournament.

        Starts the underlying runner for each assigned slot.
        """
        with self._lock:
            if self._overall_status == "RUNNING":
                raise DataContractError(
                    "ShadowTournamentSupervisor: tournament already running."
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

            self._overall_status = "RUNNING"
            self._halt_reason = None
            self._feed_health = "HEALTHY"
            self._last_successful_update_utc = datetime.now(timezone.utc)
            self._update_metrics()

    def process_bar(self, bar: SyntheticBar) -> Dict[str, Optional[str]]:
        """Process a market bar across all slots with strict isolation.

        Returns a mapping of slot_id -> decision correlation_id (or None).
        Raises DataContractError if any slot encounters unrecoverable violation.
        """
        with self._lock:
            if self._overall_status != "RUNNING":
                logger.warning(
                    "ShadowTournamentSupervisor: bar ignored; tournament status is %s",
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

                    # Update slot state from runner portfolio
                    self._sync_slot_portfolio(slot, bar.close, bar.timestamp_utc)

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

    def _sync_slot_portfolio(
        self, slot: TournamentSlot, mark_price: Decimal, bar_time: datetime
    ) -> None:
        """Sync slot metrics from runner portfolio with zero state leakage."""
        if slot.runner is None:
            return

        portfolio = slot.runner._portfolio
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
        slot.metrics.open_position_count = 1 if portfolio.position != Decimal("0") else 0
        slot.last_bar_utc = bar_time.isoformat()

        # Update peak NAV and drawdown
        if equity > slot.peak_nav_usd:
            slot.peak_nav_usd = equity
        if slot.peak_nav_usd > Decimal("0"):
            dd = ((slot.peak_nav_usd - equity) / slot.peak_nav_usd) * Decimal("100.0")
            slot.metrics.current_drawdown_pct = dd
            if dd > slot.metrics.max_drawdown_pct:
                slot.metrics.max_drawdown_pct = dd

        # Update equity curve history (capped to last 100 points)
        slot.equity_curve.append(
            {
                "timestampUtc": bar_time.isoformat(),
                "navUsd": float(equity),
                "pnlUsd": float(pnl),
            }
        )
        if len(slot.equity_curve) > 100:
            slot.equity_curve.pop(0)

    def record_feed_disconnect(self, reason: str) -> None:
        """Record feed disconnection and fail-closed halt."""
        with self._lock:
            self._feed_health = "DISCONNECTED"
            self._overall_status = "HALTED"
            self._halt_reason = f"Feed disconnected: {reason}"
            self._last_successful_update_utc = datetime.now(timezone.utc)
            self._update_metrics()

    def record_feed_stale(self, age_ms: int, max_age_ms: int) -> None:
        """Record stale market data and fail-closed halt."""
        with self._lock:
            self._feed_health = "STALE"
            self._overall_status = "HALTED"
            self._halt_reason = (
                f"Feed data stale: observed {age_ms}ms > allowed {max_age_ms}ms"
            )
            self._last_successful_update_utc = datetime.now(timezone.utc)
            self._update_metrics()

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

        # Per-slot metrics
        for slot_id, slot in self._slots.items():
            labels = {"slot": slot_id, "strategy_id": slot.strategy_id}
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
            active_slots = [
                s
                for s in self._slots.values()
                if s.status == "RUNNING" and s.metrics.simulated_fill_count > 0
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
    metrics_registry: Optional[MetricsRegistry] = None,
) -> ShadowTournamentSupervisor:
    """Construct a canonical Shadow Alpha Tournament instance.

    Slot A is allocated to InfrastructureTestStrategy.
    Slots B and C remain UNASSIGNED pending Human selection.
    """
    storage_dir.mkdir(parents=True, exist_ok=True)
    tournament_id = f"SHADOW-TOURNAMENT-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    # Slot A: InfrastructureTestStrategy
    slot_a_config = PaperSessionConfig(
        session_id=f"{tournament_id}-SLOT-A",
        strategy_id="INFRA-TEST-MOMENTUM-SYNTHETIC-001",
        strategy_version="1.0.0",
        instrument="BTCUSDT",
        initial_cash=Decimal("1000.00"),
        max_position_units=Decimal("10.0"),
        max_notional=Decimal("100000.0"),
        max_daily_loss=Decimal("100.0"),
        fill_slippage_bps=Decimal("5.0"),
        fill_commission_per_unit=Decimal("0.0004"),
        prng_seed=42,
        git_commit=acash_commit_sha,
        component_version="1.0.0",
        journal_path=storage_dir / f"{tournament_id}_slot_a.journal.jsonl",
        snapshot_path=storage_dir / f"{tournament_id}_slot_a.snapshots.jsonl",
    )
    runner_a = PaperSessionRunner(slot_a_config)

    slot_a = TournamentSlot(
        slot_id="A",
        strategy_id="INFRA-TEST-MOMENTUM-SYNTHETIC-001",
        strategy_name="Infrastructure Test Strategy (Slot A)",
        strategy_version="1.0.0",
        status="INITIALIZING",
        session_id=slot_a_config.session_id,
        config_hash=slot_a_config.compute_config_hash(),
        acash_commit_sha=acash_commit_sha,
        runner=runner_a,
    )

    # Slots B and C: UNASSIGNED (honest reporting of repo state)
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

    slots = {"A": slot_a, "B": slot_b, "C": slot_c}

    return ShadowTournamentSupervisor(
        tournament_id=tournament_id,
        slots=slots,
        acash_commit_sha=acash_commit_sha,
        metrics_registry=metrics_registry,
    )
