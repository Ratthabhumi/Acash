"""ACASH Paper Trading — E3 Paper Session Runner.

PaperSessionRunner wires the complete E3 execution chain:

    Market Data (synthetic/recorded)
        ↓
    Feature Snapshot (via InfrastructureTestStrategy)
        ↓
    Signal Evaluation
        ↓
    Risk Check (max position, max notional, kill switch)
        ↓
    Order Intent
        ↓
    SimulatedMarketMatcher (Paper Fill)
        ↓
    Position Update
        ↓
    Portfolio Update
        ↓
    PaperEventJournal (every step hash-linked)
        ↓
    DecisionTrace (queryable by correlation_id)

GOVERNANCE:
===========
- Mode is PAPER_ONLY — no real broker orders
- LIVE mode is structurally absent from this module
- All fills are explicitly labeled SIMULATED
- Strategy is INFRASTRUCTURE_TEST_STRATEGY_ONLY
- Results are NOT research evidence

PaperSessionConfig contains all parameters required for deterministic replay.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.paper.analytics import PaperAnalyticsEngine, PaperAnalyticsReport
from acash.paper.health import HealthEventKind, PaperHealthMonitor, TerminalReason
from acash.paper.journal import (
    JournalEvent,
    JournalEventType,
    JournalLayer,
    PaperEventJournal,
)
from acash.paper.manifest import PaperMode, PaperSessionManifest
from acash.paper.reconcile import PaperReconciliationEngine, ReconciliationResult, ReconciliationStatus
from acash.paper.replay import ReplayEngine, ReplayResult
from acash.paper.snapshot import DailySnapshot, DailySnapshotStore
from acash.paper.strategy import (
    InfrastructureTestStrategy,
    PaperStrategyProtocol,
    SignalDirection,
    StrategySignal,
)
from acash.paper.trace import DecisionTrace


# ---------------------------------------------------------------------------
# Portfolio & kill-switch policy seams (Tournament V2 remediation)
# ---------------------------------------------------------------------------


class PortfolioFundingPolicy(str, Enum):
    """Deterministic policy governing how virtual portfolio cash may be drawn.

    Affects the FAIL-CLOSED funding gate in ``_evaluate_risk``. The policy is
    part of the canonical config hash (single authority for the gate).

    - SIMULATED_LEVERAGED: H01-preserving default. No cash floor; virtual cash
      may go negative (leverage is simulated, mirroring the H01 Slot A state
      where cash reached -699728.123). Presence of negative cash is evidence,
      not an error, under this policy.
    - CASH_CONSTRAINED_SPOT: Strict spot discipline. A fill that would drive
      projected cash below zero is REJECTED by the risk gate (fail-closed).
    - EXPLICIT_BOUNDED_LEVERAGE: Leverage is permitted only up to an explicit,
      config-sealed debt limit (max_debt_limit_usd). A fill that would breach
      the limit is REJECTED.
    """

    SIMULATED_LEVERAGED = "SIMULATED_LEVERAGED"
    CASH_CONSTRAINED_SPOT = "CASH_CONSTRAINED_SPOT"
    EXPLICIT_BOUNDED_LEVERAGE = "EXPLICIT_BOUNDED_LEVERAGE"


class KillSwitchPositionPolicy(str, Enum):
    """Deterministic policy for what happens to the position on kill switch.

    The kill switch is triggered only on a MAX_DAILY_LOSS breach. The chosen
    policy decides whether the open simulated position is preserved, flattened
    at mark (via a synthetic closing fill chain), or preserved while an
    operator resolution is mandatory before any further action.

    - HALT_AND_PRESERVE_POSITION: default, H01-preserving. Trading halts but the
      open position is kept (mark-to-market continues; flight recorder intact).
    - HALT_AND_FORCE_SIMULATED_FLATTEN: the position is closed at the reference
      (mark) price through a synthetic ORDER_INTENT_CREATED -> FILL_SIMULATED ->
      POSITION_UPDATED -> PORTFOLIO_UPDATED journal chain.
    - HALT_AND_REQUIRE_OPERATOR_RESOLUTION: like PRESERVE for accounting, but
      additionally requires an operator resolution (journaled) before resume;
      no automatic flatten and no automatic resume.
    """

    HALT_AND_PRESERVE_POSITION = "HALT_AND_PRESERVE_POSITION"
    HALT_AND_FORCE_SIMULATED_FLATTEN = "HALT_AND_FORCE_SIMULATED_FLATTEN"
    HALT_AND_REQUIRE_OPERATOR_RESOLUTION = "HALT_AND_REQUIRE_OPERATOR_RESOLUTION"


class SignalSizingPolicy(str, Enum):
    """Deterministic policy for deriving the executed quantity from a signal.

    - INFRA_FIXED_QUANTITY: (default, H01-bit-preserving) the strategy's fixed
      trade_quantity is executed verbatim. Preserves the canonical Slot A regime
      (1.0 / 1.5 BTC fixed quantities) so historical replay stays bit-compatible.
    - NAV_RELATIVE_PERCENT: the execution quantity is derived from virtual NAV:
          target_notional = max(0, equity) * nav_sizing_notional_pct / 100
          qty = target_notional / reference_price  (ROUND_DOWN, 8dp)
      This bounds virtual exposure of small-NAV slots. A derived quantity <= 0
      is REJECTED by the risk gate (fail-closed, no zero/negative orders).
    """

    INFRA_FIXED_QUANTITY = "INFRA_FIXED_QUANTITY"
    NAV_RELATIVE_PERCENT = "NAV_RELATIVE_PERCENT"


# V2 safe-sizing default: 10% of virtual NAV per executed order notional.
SAFE_V2_NAV_SIZING_PCT = Decimal("10.0")


# ---------------------------------------------------------------------------
# PaperSessionConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaperSessionConfig:
    """Complete configuration for a paper session.

    All fields required for deterministic replay.
    """

    session_id: str
    strategy_id: str
    strategy_version: str
    instrument: str
    initial_cash: Decimal
    max_position_units: Decimal
    max_notional: Decimal
    max_daily_loss: Decimal
    fill_slippage_bps: Decimal
    fill_commission_per_unit: Decimal
    prng_seed: int
    git_commit: str
    component_version: str
    journal_path: Path
    snapshot_path: Path
    mode: str = PaperMode.PAPER_ONLY
    fill_model_version: str = "LOCAL_SIMULATOR_V1"
    risk_model_version: str = "PAPER_INLINE_RISK_V1"
    data_source: str = "SYNTHETIC_BARS"
    market_domain: str = "SYNTHETIC"
    max_market_data_age_ms: Optional[int] = None
    portfolio_funding_policy: PortfolioFundingPolicy = PortfolioFundingPolicy.SIMULATED_LEVERAGED
    max_debt_limit_usd: Decimal = Decimal("0")
    kill_switch_position_policy: KillSwitchPositionPolicy = KillSwitchPositionPolicy.HALT_AND_PRESERVE_POSITION
    signal_sizing_policy: SignalSizingPolicy = SignalSizingPolicy.INFRA_FIXED_QUANTITY
    nav_sizing_notional_pct: Decimal = Decimal("0")

    def _validate(self) -> None:
        """Fail-fast config validation for the V2 policy seams."""
        if self.portfolio_funding_policy == PortfolioFundingPolicy.EXPLICIT_BOUNDED_LEVERAGE:
            if self.max_debt_limit_usd < Decimal("0"):
                raise DataContractError(
                    f"PaperSessionConfig: max_debt_limit_usd must be >= 0 for "
                    f"EXPLICIT_BOUNDED_LEVERAGE, got {self.max_debt_limit_usd}"
                )
        if self.max_debt_limit_usd < Decimal("0"):
            raise DataContractError(
                f"PaperSessionConfig: max_debt_limit_usd must be >= 0, got {self.max_debt_limit_usd}"
            )
        if (
            self.signal_sizing_policy == SignalSizingPolicy.NAV_RELATIVE_PERCENT
            and not (Decimal("0") < self.nav_sizing_notional_pct <= Decimal("100"))
        ):
            raise DataContractError(
                f"PaperSessionConfig: NAV_RELATIVE_PERCENT requires "
                f"0 < nav_sizing_notional_pct <= 100, got {self.nav_sizing_notional_pct}"
            )
        if (
            self.signal_sizing_policy == SignalSizingPolicy.INFRA_FIXED_QUANTITY
            and self.nav_sizing_notional_pct != Decimal("0")
        ):
            raise DataContractError(
                f"PaperSessionConfig: INFRA_FIXED_QUANTITY requires "
                f"nav_sizing_notional_pct == 0 (no dead sizing config), "
                f"got {self.nav_sizing_notional_pct}"
            )

    def __post_init__(self) -> None:
        self._validate()

    def compute_config_hash(self) -> str:
        """SHA-256 of canonical config (excluding paths which are runtime-dependent)."""
        canonical = {
            "session_id": self.session_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "instrument": self.instrument,
            "initial_cash": str(self.initial_cash),
            "max_position_units": str(self.max_position_units),
            "max_notional": str(self.max_notional),
            "max_daily_loss": str(self.max_daily_loss),
            "fill_slippage_bps": str(self.fill_slippage_bps),
            "fill_commission_per_unit": str(self.fill_commission_per_unit),
            "prng_seed": self.prng_seed,
            "mode": self.mode,
            "fill_model_version": self.fill_model_version,
            "risk_model_version": self.risk_model_version,
            "portfolio_funding_policy": self.portfolio_funding_policy.value,
            "kill_switch_position_policy": self.kill_switch_position_policy.value,
        }
        if self.max_debt_limit_usd != Decimal("0"):
            canonical["max_debt_limit_usd"] = str(self.max_debt_limit_usd)
        if (
            self.signal_sizing_policy
            != SignalSizingPolicy.INFRA_FIXED_QUANTITY
        ):
            canonical["signal_sizing_policy"] = self.signal_sizing_policy.value
        if (
            self.signal_sizing_policy
            == SignalSizingPolicy.NAV_RELATIVE_PERCENT
        ):
            canonical["nav_sizing_notional_pct"] = str(self.nav_sizing_notional_pct)
        if self.max_market_data_age_ms is not None:
            canonical["max_market_data_age_ms"] = self.max_market_data_age_ms
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(
            canonical
        ).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()


# ---------------------------------------------------------------------------
# PaperPortfolioState — in-memory portfolio accounting
# ---------------------------------------------------------------------------


@dataclass
class PaperPortfolioState:
    """Mutable in-memory portfolio state for paper trading."""

    cash: Decimal
    position: Decimal = Decimal("0")
    avg_entry_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    trade_count: int = 0
    order_count: int = 0
    rejected_order_count: int = 0

    @property
    def equity(self) -> Decimal:
        """Equity = cash + unrealized position value (position * avg_entry_price)."""
        return self.cash + (self.position * self.avg_entry_price)

    def to_summary(self) -> Dict[str, Any]:
        return {
            "cash": str(self.cash),
            "position": str(self.position),
            "avg_entry_price": str(self.avg_entry_price),
            "realized_pnl": str(self.realized_pnl),
            "total_fees": str(self.total_fees),
            "equity": str(self.equity),
            "trade_count": self.trade_count,
            "order_count": self.order_count,
            "rejected_order_count": self.rejected_order_count,
        }


# ---------------------------------------------------------------------------
# Bar — synthetic market bar
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticBar:
    """A normalized market bar for paper infrastructure testing.

    When constructed from a real market feed (E3.5) it carries explicit feed
    provenance: feed_source, feed_source_version, feed_source_id,
    received_at_utc, feed_sequence, optional book/trade fields, the explicit
    unavailability list, and observed data age. Never fabricates book/trade
    fields the provider did not supply.
    """

    timestamp_utc: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    # E3.5 real-feed provenance (optional; absent for pure synthetic bars)
    feed_source: Optional[str] = None
    feed_source_version: Optional[str] = None
    feed_source_id: Optional[str] = None
    received_at_utc: Optional[datetime] = None
    feed_sequence: Optional[int] = None
    feed_bid: Optional[Decimal] = None
    feed_ask: Optional[Decimal] = None
    feed_trade_count: Optional[int] = None
    feed_unavailable: Optional[List[str]] = None
    data_age_ms: Optional[int] = None

    @property
    def is_real_feed(self) -> bool:
        """True if this bar came from a real market data feed."""
        return self.feed_source is not None

    def to_journal_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "symbol": self.symbol,
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "volume": str(self.volume),
        }
        if self.is_real_feed:
            payload["source"] = self.feed_source
            payload["feed_source_version"] = self.feed_source_version
            payload["feed_source_id"] = self.feed_source_id
            if self.received_at_utc is not None:
                payload["received_at_utc"] = self.received_at_utc.isoformat()
            if self.feed_sequence is not None:
                payload["feed_sequence"] = self.feed_sequence
            if self.feed_bid is not None:
                payload["bid"] = str(self.feed_bid)
            if self.feed_ask is not None:
                payload["ask"] = str(self.feed_ask)
            if self.feed_trade_count is not None:
                payload["trade_count"] = self.feed_trade_count
            if self.data_age_ms is not None:
                payload["data_age_ms"] = self.data_age_ms
            if self.feed_unavailable:
                payload["unavailable"] = sorted(self.feed_unavailable)
            payload["GOVERNANCE_LABEL"] = "REAL_MARKET_DATA_EXECUTION_INFRA_ONLY"
        else:
            payload["source"] = "SYNTHETIC_BARS"
            payload["GOVERNANCE_LABEL"] = "INFRASTRUCTURE_TEST_DATA"
        return payload


# ---------------------------------------------------------------------------
# PaperSessionRunner — E3 main wiring
# ---------------------------------------------------------------------------


def bar_age_ms(bar: "SyntheticBar") -> int:
    """Compute observed data age in milliseconds for a real-feed bar.

    Uses received_at_utc - timestamp_utc when both are present, otherwise 0
    (synthetic bars carry no wall-clock ingestion delta).
    """
    if bar.received_at_utc is not None:
        delta = (bar.received_at_utc - bar.timestamp_utc).total_seconds()
        return max(0, int(delta * 1000))
    return 0


class PaperSessionRunner:
    """E3 Paper Trading Session — complete execution chain with Black-Box logging.

    GOVERNANCE: PAPER_ONLY — NO REAL ORDERS — INFRASTRUCTURE TEST.

    Safety controls:
    - Max position size
    - Max notional
    - Max daily loss threshold
    - Stale data protection
    - Duplicate order protection (intent_id dedup)
    - Kill switch (triggered on max daily loss breach)
    - Journal failure → fail-closed (raises DataContractError)
    """

    COMPONENT = "PaperSessionRunner"

    def __init__(
        self,
        config: PaperSessionConfig,
        strategy: Optional[PaperStrategyProtocol] = None,
    ) -> None:
        if config.mode != PaperMode.PAPER_ONLY:
            raise DataContractError(
                f"PaperSessionRunner: mode must be PAPER_ONLY, got: {config.mode!r}"
            )

        self._config = config
        self._config_hash = config.compute_config_hash()

        # Core infrastructure
        self._journal = PaperEventJournal(
            session_id=config.session_id,
            persistence_path=config.journal_path,
            git_commit=config.git_commit,
            component_version=config.component_version,
        )
        self._health = PaperHealthMonitor(
            journal=self._journal,
            session_id=config.session_id,
            component_version=config.component_version,
        )
        if strategy is not None:
            self._strategy: PaperStrategyProtocol = strategy
        else:
            self._strategy = InfrastructureTestStrategy(
                fast_period=3,
                slow_period=5,
                trade_quantity=Decimal("1.0"),
                symbol=config.instrument,
                config_hash=self._config_hash,
            )
        self._reconciler = PaperReconciliationEngine(
            session_id=config.session_id,
            journal=self._journal,
        )
        self._analytics = PaperAnalyticsEngine(session_id=config.session_id)
        self._replay_engine = ReplayEngine(
            session_id=config.session_id,
            strategy=self._strategy,
        )
        self._snapshot_store = DailySnapshotStore(config.snapshot_path)

        # Portfolio state
        self._portfolio = PaperPortfolioState(cash=config.initial_cash)

        # Safety state
        self._kill_switch_active = False
        self._kill_switch_pending = False
        self._operator_resolution_required = False
        self._submitted_intent_ids: Set[str] = set()
        self._seen_feed_source_ids: Set[str] = set()
        self._daily_realized_loss = Decimal("0")

        # Session timing
        self._start_time_utc: Optional[datetime] = None
        self._end_time_utc: Optional[datetime] = None
        self._started = False
        self._stopped = False
        self._manifest: Optional[PaperSessionManifest] = None

    @property
    def is_started(self) -> bool:
        """True if the runner session has been started."""
        return self._started

    @property
    def is_finalized(self) -> bool:
        """True if the runner session has been stopped and finalized."""
        return self._stopped

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start(self) -> str:
        """Start the paper session. Returns the session start event_id."""
        if self._started:
            raise DataContractError(
                "PaperSessionRunner: session already started."
            )
        self._start_time_utc = datetime.now(timezone.utc)
        self._started = True

        session_cid = self._journal.new_correlation_id()
        event_id = self._health.session_started(
            correlation_id=session_cid,
            session_metadata={
                "session_id": self._config.session_id,
                "strategy_id": self._config.strategy_id,
                "strategy_version": self._config.strategy_version,
                "instrument": self._config.instrument,
                "initial_cash": str(self._config.initial_cash),
                "mode": self._config.mode,
                "fill_model_version": self._config.fill_model_version,
                "risk_model_version": self._config.risk_model_version,
                "config_hash": self._config_hash,
                "git_commit": self._config.git_commit,
                "GOVERNANCE": "PAPER_ONLY_NO_REAL_ORDERS",
                **self._sizing_metadata(),
            },
        )
        return event_id

    def _sizing_metadata(self) -> Dict[str, str]:
        """Sizing seal for SESSION_STARTED when a non-default policy is active.

        Kept empty for the canonical INFRA_FIXED default so legacy session
        payloads stay byte-identical (H01 replay compatibility).
        """
        if self._config.signal_sizing_policy == SignalSizingPolicy.INFRA_FIXED_QUANTITY:
            return {}
        meta: Dict[str, str] = {
            "signal_sizing_policy": self._config.signal_sizing_policy.value,
        }
        if self._config.signal_sizing_policy == SignalSizingPolicy.NAV_RELATIVE_PERCENT:
            meta["nav_sizing_notional_pct"] = str(self._config.nav_sizing_notional_pct)
        return meta

    def stop(
        self,
        terminal_reason: TerminalReason = TerminalReason.NORMAL_COMPLETION,
    ) -> PaperSessionManifest:
        """Stop the session, run final reconciliation, and seal manifest.

        Args:
            terminal_reason: Canonical causal reason this session ended.
                Preserved in the SESSION_STOPPED journal event. The caller is
                responsible for passing the actual cause (e.g. FEED_DISCONNECTED,
                RISK_KILL_SWITCH, OPERATOR_STOP); never fabricated here.
        """
        if not self._started:
            raise DataContractError(
                "PaperSessionRunner: session not started."
            )

        # Idempotent finalization: a runner finalized once must not be
        # finalized twice, duplicate daily snapshots, or overwrite its manifest.
        if self._stopped:
            if self._manifest is not None:
                return self._manifest
            raise DataContractError(
                "PaperSessionRunner: session marked stopped but manifest is missing."
            )

        self._end_time_utc = datetime.now(timezone.utc)

        # Final reconciliation
        recon_result = self._reconciler.run_full_reconciliation()
        recon_status = recon_result.status.value

        # Final integrity check
        integrity_violations = self._journal.verify_integrity()
        integrity_status = "PASS" if not integrity_violations else "FAIL"

        # Persist end-of-session daily snapshot (append-only, audit reference).
        if self._journal.event_count > 0:
            try:
                self.capture_daily_snapshot()
            except DataContractError:
                # A snapshot failure must not silently destroy the manifest
                # seal; escalate as a session-stop failure (fail-closed).
                raise

        # Record reconciliation to journal
        session_cid = self._journal.new_correlation_id()
        self._health.record_reconciliation(
            correlation_id=session_cid,
            status=recon_status,
            violation_count=recon_result.total_violations,
            details=recon_result.to_summary(),
        )

        # Session stop event — canonical terminal reason (never erased).
        stop_event_id = self._health.session_stopped(
            correlation_id=session_cid,
            reason=terminal_reason,
            final_event_count=self._journal.event_count,
        )

        # Seal manifest
        is_infra = getattr(self._strategy, "is_infrastructure_test", True)
        manifest = PaperSessionManifest.seal(
            session_id=self._config.session_id,
            manifest_id=str(uuid.uuid4()),
            strategy_id=self._config.strategy_id,
            strategy_version=self._config.strategy_version,
            is_infrastructure_test_strategy=is_infra,
            git_commit=self._config.git_commit,
            config_hash=self._config_hash,
            strategy_config_hash=self._config_hash,
            journal_final_hash=self._journal.last_event_hash,
            data_source=self._config.data_source,
            instrument_universe=[self._config.instrument],
            market_domain=self._config.market_domain,
            fill_model_version=self._config.fill_model_version,
            risk_model_version=self._config.risk_model_version,
            start_time_utc=self._start_time_utc,  # type: ignore[arg-type]
            end_time_utc=self._end_time_utc,
            total_event_count=self._journal.event_count,
            total_warning_count=0,
            total_error_count=0,
            total_trade_count=self._portfolio.trade_count,
            total_order_count=self._portfolio.order_count,
            total_rejected_order_count=self._portfolio.rejected_order_count,
            final_portfolio_summary=self._portfolio.to_summary(),
            final_reconciliation_status=recon_status,
            journal_integrity_status=integrity_status,
        )

        # Persist the sealed manifest so audit tools can reload it post-run.
        try:
            manifest_path = (
                self._config.journal_path.parent
                / f"{self._config.session_id}.manifest.json"
            )
            with manifest_path.open("w", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(manifest.model_dump(), indent=2, default=str) + "\n"
                )
                fh.flush()
        except Exception as exc:
            raise DataContractError(
                f"PaperSessionRunner: manifest persistence failure: {exc}"
            ) from exc

        self._manifest = manifest
        self._stopped = True
        return manifest

    @property
    def manifest(self) -> Optional[PaperSessionManifest]:
        """Sealed session manifest if session has stopped, else None."""
        return self._manifest

    def capture_daily_snapshot(self) -> DailySnapshot:
        """Persist an end-of-day operational daily snapshot (append-only).

        The snapshot references journal bounds (first/last sequence + hash)
        so the journal remains the authority; the snapshot is a summary view
        for audit, never a replacement. Fail-closed on persistence failure.
        """
        events = self._journal.read_all()
        ordered = sorted(events, key=lambda e: e.sequence)
        if not ordered:
            raise DataContractError(
                "PaperSessionRunner: cannot snapshot an empty journal."
            )

        first_seq = ordered[0].sequence
        last_seq = ordered[-1].sequence
        first_hash = ordered[0].event_hash
        last_hash = self._journal.last_event_hash

        # Operational counters derived directly from journal events (cannot
        # be confused with research evidence).
        signal_count = 0
        risk_rejection_count = 0
        feed_disconnect_count = 0
        stale_data_count = 0
        exception_count = 0
        reconciliation_failures = 0
        incident_count = 0

        for ev in ordered:
            if ev.event_type in (
                JournalEventType.SIGNAL_LONG,
                JournalEventType.SIGNAL_SHORT,
                JournalEventType.SIGNAL_FLAT,
                JournalEventType.SIGNAL_EVALUATED,
            ):
                signal_count += 1
            elif ev.event_type == JournalEventType.RISK_REJECTED:
                risk_rejection_count += 1
            elif ev.event_type == JournalEventType.FEED_DISCONNECTED:
                feed_disconnect_count += 1
            elif ev.event_type == JournalEventType.MARKET_BAR_STALE:
                stale_data_count += 1
            elif ev.event_type == JournalEventType.EXCEPTION_RECORDED:
                exception_count += 1
            elif ev.event_type == JournalEventType.RECONCILIATION_FAILURE:
                reconciliation_failures += 1

        incident_count = (
            feed_disconnect_count
            + stale_data_count
            + exception_count
            + reconciliation_failures
        )

        integrity_violations = self._journal.verify_integrity()
        integrity_status = "PASS" if not integrity_violations else "FAIL"

        recon_result = self._reconciler.run_full_reconciliation()
        reconciliation_failures = max(
            reconciliation_failures, recon_result.total_violations
        )

        snapshot = DailySnapshot(
            snapshot_id=f"{self._config.session_id}-{uuid.uuid4().hex[:8]}",
            session_id=self._config.session_id,
            trading_date=datetime.now(timezone.utc).date(),
            captured_at_utc=datetime.now(timezone.utc),
            starting_equity=self._config.initial_cash,
            ending_equity=self._portfolio.equity,
            pnl=self._portfolio.equity - self._config.initial_cash,
            cash=self._portfolio.cash,
            trade_count=self._portfolio.trade_count,
            order_count=self._portfolio.order_count,
            rejected_order_count=self._portfolio.rejected_order_count,
            signal_count=signal_count,
            risk_rejection_count=risk_rejection_count,
            system_incident_count=incident_count,
            feed_disconnect_count=feed_disconnect_count,
            stale_data_count=stale_data_count,
            exception_count=exception_count,
            reconciliation_failures=reconciliation_failures,
            journal_integrity_status=integrity_status,
            first_event_sequence=first_seq,
            last_event_sequence=last_seq,
            first_event_hash=first_hash,
            last_event_hash=last_hash,
        )
        self._snapshot_store.append(snapshot)
        return snapshot

    def recover(self) -> Optional[str]:
        """Recover in-memory state from an existing journal (restart recovery).

        Reconstructs portfolio, submitted intent IDs, start time, and kill
        switch state from committed journal events. Returns the recovered
        portfolio-equivalent correlation_id, or the SESSION_STARTED event_id
        when the journal was empty.

        Throws DataContractError when the journal contents conflict with the
        session config (fail-closed; no silent reconciliation).
        """
        if self._started:
            raise DataContractError(
                "PaperSessionRunner: session already started; cannot recover."
            )
        if not self._journal.path.exists():
            raise DataContractError(
                f"PaperSessionRunner: no journal at {self._journal.path}; "
                "cannot recover from nothing."
            )

        events = self._journal.read_all()
        if not events:
            # Empty journal — start fresh
            return self.start()

        # Verify journal integrity before trusting any replay.
        integrity_violations = self._journal.verify_integrity()
        if integrity_violations:
            raise DataContractError(
                "PaperSessionRunner: journal integrity violated during recovery; "
                f"{len(integrity_violations)} chain violations found."
            )

        recovery_cid = self._journal.new_correlation_id()

        # Reconstruct from committed events (in sequence order).
        recovered_position = Decimal("0")
        recovered_avg_entry = Decimal("0")
        recovered_realized_pnl = Decimal("0")
        recovered_fees = Decimal("0")
        recovered_trade_count = 0
        recovered_order_count = 0
        recovered_rejected_count = 0
        recovered_intent_ids: Set[str] = set()
        recovered_feed_source_ids: Set[str] = set()
        recovered_start_time: Optional[datetime] = None
        recovered_kill_switch = False
        saw_feed_provenance = False

        ordered = sorted(events, key=lambda e: e.sequence)
        for ev in ordered:
            if ev.event_type == JournalEventType.SESSION_STARTED:
                recovered_start_time = ev.event_time_utc
            elif ev.event_type == JournalEventType.ORDER_INTENT_CREATED:
                intent_id = ev.payload.get("order_intent_id")
                if intent_id is not None:
                    recovered_intent_ids.add(str(intent_id))
                recovered_order_count += 1
            elif ev.event_type == JournalEventType.KILL_SWITCH_TRIGGERED:
                recovered_kill_switch = True
            elif ev.event_type == JournalEventType.PORTFOLIO_UPDATED:
                pay = ev.payload
                recovered_cash = pay.get("cash")
                if recovered_cash is None:
                    raise DataContractError(
                        "PaperSessionRunner: PORTFOLIO_UPDATED missing cash "
                        "during recovery."
                    )
                recovered_position = Decimal(str(pay.get("position", "0")))
                recovered_avg_entry = Decimal(str(pay.get("avg_entry_price", "0")))
                recovered_realized_pnl = Decimal(str(pay.get("realized_pnl", "0")))
                recovered_fees = Decimal(str(pay.get("total_fees", "0")))
                recovered_trade_count = int(pay.get("trade_count", 0))
                recovered_order_count = int(pay.get("order_count", recovered_order_count))
                recovered_rejected_count = int(
                    pay.get("rejected_order_count", recovered_rejected_count)
                )
                self._portfolio.cash = Decimal(str(recovered_cash))
            elif ev.event_type == JournalEventType.MARKET_BAR_RECEIVED:
                source = ev.payload.get("source")
                if source not in (None, "SYNTHETIC_BARS"):
                    saw_feed_provenance = True
                feed_source_id = ev.payload.get("feed_source_id")
                if feed_source_id is not None:
                    recovered_feed_source_ids.add(str(feed_source_id))

        # Apply recovered portfolio state.
        self._portfolio.position = recovered_position
        self._portfolio.avg_entry_price = recovered_avg_entry
        self._portfolio.realized_pnl = recovered_realized_pnl
        self._portfolio.total_fees = recovered_fees
        self._portfolio.trade_count = recovered_trade_count
        self._portfolio.order_count = recovered_order_count
        self._portfolio.rejected_order_count = recovered_rejected_count
        self._submitted_intent_ids = recovered_intent_ids
        self._seen_feed_source_ids = recovered_feed_source_ids
        self._kill_switch_active = recovered_kill_switch
        self._start_time_utc = recovered_start_time
        self._started = True

        if saw_feed_provenance and self._config.data_source == "SYNTHETIC_BARS":
            raise DataContractError(
                "PaperSessionRunner: journal contains real-feed bars but config "
                "data_source is SYNTHETIC_BARS (config conflict during recovery)."
            )

        self._health.record(
            kind=HealthEventKind.RECOVERY_ATTEMPTED,
            correlation_id=recovery_cid,
            payload={
                "event": "RECOVERY_ATTEMPTED",
                "recovered_position": str(self._portfolio.position),
                "recovered_cash": str(self._portfolio.cash),
                "recovered_intent_ids": len(self._submitted_intent_ids),
                "recovered_order_count": self._portfolio.order_count,
                "recovered_trade_count": self._portfolio.trade_count,
                "recovered_feed_source_ids": len(self._seen_feed_source_ids),
                "recovered_kill_switch": self._kill_switch_active,
                "journal_event_count": len(events),
                "recovered_start_time_utc": (
                    recovered_start_time.isoformat() if recovered_start_time else None
                ),
            },
        )

        return recovery_cid

    # ------------------------------------------------------------------
    # Core decision loop
    # ------------------------------------------------------------------

    def process_bar(self, bar: SyntheticBar) -> Optional[str]:
        """Process one market bar through the complete execution chain.

        Returns correlation_id of the decision chain, or None if no action.
        Raises DataContractError if journal fails (fail-closed).
        """
        if not self._started:
            raise DataContractError(
                "PaperSessionRunner: session not started. Call start() first."
            )
        if self._stopped:
            return None  # Session is finalized/stopped — no new decisions
        if self._kill_switch_active:
            return None  # Hard stop — no new decisions while kill switch active

        # E3.5 duplicate-feed-bar gate: a real-feed bar whose provider
        # source_id was already admitted in this session or a prior session
        # (recovered restart) is refused. This prevents a restarted feed from
        # re-creating a decision/order for a bar it already consumed.
        if (
            bar.feed_source_id is not None
            and bar.feed_source_id in self._seen_feed_source_ids
        ):
            self._journal.append(
                event_type=JournalEventType.MARKET_BAR_REJECTED,
                layer=JournalLayer.MARKET_DATA,
                event_time_utc=bar.timestamp_utc,
                correlation_id=self._journal.new_correlation_id(),
                component=self.COMPONENT,
                payload={
                    "event": "MARKET_BAR_REJECTED",
                    "reason": "DUPLICATE_FEED_SOURCE_ID",
                    "feed_source_id": bar.feed_source_id,
                    "session_id": self._config.session_id,
                },
            )
            return None

        # E3.5 stale-data gate: real-feed bars older than the configured
        # freshness horizon are NOT admitted to the decision pipeline.
        if (
            self._config.max_market_data_age_ms is not None
            and bar.received_at_utc is not None
        ):
            age_ms = bar.data_age_ms if bar.data_age_ms is not None else bar_age_ms(bar)
            if age_ms > self._config.max_market_data_age_ms:
                self._health.record(
                    kind=HealthEventKind.STALE_DATA,
                    correlation_id=self._journal.new_correlation_id(),
                    payload={
                        "reason": "DATA_AGE_EXCEEDED",
                        "age_ms": age_ms,
                        "max_market_data_age_ms": self._config.max_market_data_age_ms,
                        "timestamp_utc": bar.timestamp_utc.isoformat(),
                        "received_at_utc": bar.received_at_utc.isoformat(),
                    },
                )
                return None  # No new trading decision for stale data

        if bar.feed_source_id is not None:
            self._seen_feed_source_ids.add(bar.feed_source_id)

        correlation_id = self._journal.new_correlation_id()

        # --- Layer 1: MARKET_DATA ---
        market_event_id = self._record_market_bar(bar, correlation_id)

        # --- Layer 2: FEATURE + Layer 3: SIGNAL ---
        # Build closing price history from journal
        closes = self._extract_closes_from_journal()
        signal = self._strategy.evaluate(
            closes=closes,
            evaluation_time_utc=bar.timestamp_utc,
            market_event_reference=bar.timestamp_utc.isoformat(),
        )

        if signal is None:
            # Not enough history yet
            self._record_flat_signal(bar, correlation_id, market_event_id, closes)
            return correlation_id

        # Record feature snapshot
        feature_event_id = self._record_feature_snapshot(
            bar, correlation_id, market_event_id, signal
        )

        # Record signal
        signal_event_id = self._record_signal(
            signal, correlation_id, feature_event_id
        )

        if signal.direction == SignalDirection.FLAT:
            return correlation_id

        # --- Layer 3.5: SIZING (V2 safe-sizing seam) ---
        # Derive the executed quantity from the configured policy. The returned
        # execution signal is the single authority downstream
        # (risk -> order -> fill -> portfolio).
        exec_signal, sizing_meta = self._apply_signal_sizing(
            signal, reference_price=bar.close
        )

        # --- Layer 4: RISK ---
        risk_approved, risk_reason, risk_event_id = self._evaluate_risk(
            exec_signal,
            correlation_id,
            signal_event_id,
            reference_price=bar.close,
            sizing_meta=sizing_meta,
        )

        if not risk_approved:
            return correlation_id

        # --- Layer 5: ORDER ---
        intent_id = str(uuid.uuid4())
        if intent_id in self._submitted_intent_ids:
            # Duplicate protection
            self._journal.append(
                event_type=JournalEventType.DUPLICATE_ORDER_BLOCKED,
                layer=JournalLayer.ORDER,
                event_time_utc=bar.timestamp_utc,
                correlation_id=correlation_id,
                causation_id=risk_event_id,
                component=self.COMPONENT,
                payload={"intent_id": intent_id, "reason": "DUPLICATE"},
            )
            return correlation_id

        self._submitted_intent_ids.add(intent_id)
        self._portfolio.order_count += 1

        order_intent_event_id = self._journal.append(
            event_type=JournalEventType.ORDER_INTENT_CREATED,
            layer=JournalLayer.ORDER,
            event_time_utc=bar.timestamp_utc,
            correlation_id=correlation_id,
            causation_id=risk_event_id,
            component=self.COMPONENT,
            payload={
                "order_intent_id": intent_id,
                "symbol": exec_signal.symbol,
                "side": exec_signal.direction.value,
                "quantity": str(exec_signal.target_quantity),
                "order_type": "MARKET",
                "strategy_id": exec_signal.strategy_id,
                "GOVERNANCE_LABEL": "SIMULATED_ORDER",
            },
        ).event_id

        # --- Layer 6: EXECUTION (simulated fill) ---
        fill_price = self._compute_fill_price(bar, exec_signal)
        slippage_bps = self._config.fill_slippage_bps
        commission = exec_signal.target_quantity * self._config.fill_commission_per_unit
        notional = fill_price * exec_signal.target_quantity

        fill_id = str(uuid.uuid4())
        fill_event_id = self._journal.append(
            event_type=JournalEventType.FILL_SIMULATED,
            layer=JournalLayer.EXECUTION,
            event_time_utc=bar.timestamp_utc,
            correlation_id=correlation_id,
            causation_id=order_intent_event_id,
            component=self.COMPONENT,
            payload={
                "fill_id": fill_id,
                "order_intent_id": intent_id,
                "symbol": exec_signal.symbol,
                "side": exec_signal.direction.value,
                "quantity": str(exec_signal.target_quantity),
                "fill_price": str(fill_price),
                "reference_price": str(bar.close),
                "slippage_bps": str(slippage_bps),
                "fees": str(commission),
                "fill_notional": str(notional),
                "fill_model": "LOCAL_SIMULATOR_V1",
                "GOVERNANCE_LABEL": "SIMULATED_FILL_NOT_REAL_BROKER",
            },
        ).event_id

        # --- Layer 7: PORTFOLIO ---
        self._update_portfolio(exec_signal, fill_price, commission, bar.timestamp_utc, correlation_id, fill_event_id)

        return correlation_id

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _record_market_bar(
        self, bar: SyntheticBar, correlation_id: str
    ) -> str:
        """Record market bar to journal, return event_id."""
        ev = self._journal.append(
            event_type=JournalEventType.MARKET_BAR_RECEIVED,
            layer=JournalLayer.MARKET_DATA,
            event_time_utc=bar.timestamp_utc,
            correlation_id=correlation_id,
            component=self.COMPONENT,
            payload=bar.to_journal_payload(),
        )
        return ev.event_id

    def _record_flat_signal(
        self,
        bar: SyntheticBar,
        correlation_id: str,
        causation_id: str,
        closes: List[Decimal],
    ) -> str:
        ev = self._journal.append(
            event_type=JournalEventType.SIGNAL_FLAT,
            layer=JournalLayer.SIGNAL,
            event_time_utc=bar.timestamp_utc,
            correlation_id=correlation_id,
            causation_id=causation_id,
            component=self.COMPONENT,
            payload={
                "direction": "FLAT",
                "reason": "INSUFFICIENT_HISTORY",
                "available_bars": len(closes),
                "required_bars": 5,
                "GOVERNANCE_LABEL": "INFRASTRUCTURE_TEST_SIGNAL",
            },
        )
        return ev.event_id

    def _record_feature_snapshot(
        self,
        bar: SyntheticBar,
        correlation_id: str,
        causation_id: str,
        signal: StrategySignal,
    ) -> str:
        ev = self._journal.append(
            event_type=JournalEventType.FEATURE_SNAPSHOT,
            layer=JournalLayer.FEATURE,
            event_time_utc=bar.timestamp_utc,
            correlation_id=correlation_id,
            causation_id=causation_id,
            component=self.COMPONENT,
            payload={
                "feature_snapshot": signal.feature_snapshot,
                "strategy_id": signal.strategy_id,
                "strategy_version": signal.strategy_version,
                "config_hash": signal.config_hash,
                "GOVERNANCE_LABEL": "INFRASTRUCTURE_TEST_FEATURES",
            },
        )
        return ev.event_id

    def _record_signal(
        self,
        signal: StrategySignal,
        correlation_id: str,
        causation_id: str,
    ) -> str:
        etype_map = {
            SignalDirection.LONG: JournalEventType.SIGNAL_LONG,
            SignalDirection.SHORT: JournalEventType.SIGNAL_SHORT,
            SignalDirection.FLAT: JournalEventType.SIGNAL_FLAT,
        }
        ev = self._journal.append(
            event_type=etype_map.get(signal.direction, JournalEventType.SIGNAL_EVALUATED),
            layer=JournalLayer.SIGNAL,
            event_time_utc=signal.evaluation_timestamp_utc,
            correlation_id=correlation_id,
            causation_id=causation_id,
            component=self.COMPONENT,
            payload=signal.to_journal_payload(),
        )
        return ev.event_id

    def _evaluate_risk(
        self,
        signal: StrategySignal,
        correlation_id: str,
        causation_id: str,
        *,
        reference_price: Optional[Decimal] = None,
        sizing_meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, str]:
        """Inline risk check. Returns (approved: bool, reason: str, event_id: str).

        Risk gates (all are strict; a breach of ANY gate rejects the order):
        - MAX_POSITION: |new_position| <= max_position_units
        - MAX_NOTIONAL: |new_position| * reference_price <= max_notional
          (cumulative exposure bound, enforced when a valid reference price is
          available; missing reference price is a contract violation)
        - SIZING: a non-FLAT execution quantity <= 0 is rejected (fail-closed,
          no zero/negative orders can ever be emitted)
        - FUNDING_POLICY: projected cash gate per portfolio_funding_policy
        - MAX_DAILY_LOSS: triggers the kill switch at the daily loss threshold
        """
        new_position = self._portfolio.position
        if signal.direction == SignalDirection.LONG:
            new_position += signal.target_quantity
        else:
            new_position -= signal.target_quantity

        violations: List[str] = []

        # Sizing guard (fail-closed): a sized execution quantity <= 0 is never
        # allowed to reach the order layer.
        if signal.direction != SignalDirection.FLAT and signal.target_quantity <= Decimal("0"):
            violations.append(
                f"SIZING: execution quantity {signal.target_quantity} <= 0 "
                "(fail-closed, no zero-size orders)"
            )

        # Max position check
        if abs(new_position) > self._config.max_position_units:
            violations.append(
                f"MAX_POSITION: |{new_position}| > {self._config.max_position_units}"
            )

        # Max notional check (cumulative exposure bound).
        # A missing reference price is NOT silently tolerated (fail-closed).
        if reference_price is None:
            violations.append(
                "MAX_NOTIONAL: reference_price missing; cannot size exposure (fail-closed)"
            )
        else:
            proposed_notional = abs(new_position) * reference_price
            if proposed_notional > self._config.max_notional:
                violations.append(
                    f"MAX_NOTIONAL: |{new_position}| * {reference_price} "
                    f"= {proposed_notional} > {self._config.max_notional}"
                )

            # Funding policy gate (projected cash after worst-case fill).
            # Uses the adverse-slippage fill price so a passing gate can never
            # be undone by execution; the gate is the single authority.
            slippage_frac = self._config.fill_slippage_bps / Decimal("10000")
            if signal.direction == SignalDirection.LONG:
                projected_fill = reference_price * (Decimal("1") + slippage_frac)
                projected_cash = self._portfolio.cash - (
                    projected_fill * signal.target_quantity
                ) - (signal.target_quantity * self._config.fill_commission_per_unit)
            else:
                projected_fill = reference_price * (Decimal("1") - slippage_frac)
                projected_cash = self._portfolio.cash + (
                    projected_fill * signal.target_quantity
                ) - (signal.target_quantity * self._config.fill_commission_per_unit)

            funding_policy = self._config.portfolio_funding_policy
            if funding_policy == PortfolioFundingPolicy.CASH_CONSTRAINED_SPOT:
                if projected_cash < Decimal("0"):
                    violations.append(
                        f"FUNDING_POLICY: projected_cash={projected_cash} < 0 "
                        f"(CASH_CONSTRAINED_SPOT)"
                    )
            elif funding_policy == PortfolioFundingPolicy.EXPLICIT_BOUNDED_LEVERAGE:
                debt_floor = -self._config.max_debt_limit_usd
                if projected_cash < debt_floor:
                    violations.append(
                        f"FUNDING_POLICY: projected_cash={projected_cash} < debt_floor="
                        f"{debt_floor} (EXPLICIT_BOUNDED_LEVERAGE, "
                        f"max_debt_limit_usd={self._config.max_debt_limit_usd})"
                    )

        # Kill switch check (daily loss)
        if self._kill_switch_active:
            violations.append(
                f"MAX_DAILY_LOSS: kill switch already active "
                f"(loss {self._daily_realized_loss} >= {self._config.max_daily_loss})"
            )
        elif self._daily_realized_loss >= self._config.max_daily_loss:
            violations.append(
                f"MAX_DAILY_LOSS: {self._daily_realized_loss} >= {self._config.max_daily_loss}"
            )
            self._kill_switch_pending = True

        approved = len(violations) == 0

        ev = self._journal.append(
            event_type=JournalEventType.RISK_APPROVED if approved else JournalEventType.RISK_REJECTED,
            layer=JournalLayer.RISK,
            event_time_utc=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            causation_id=causation_id,
            component=self.COMPONENT,
            payload={
                "approved": approved,
                "violations": violations,
                "current_position": str(self._portfolio.position),
                "proposed_position": str(new_position),
                "proposed_notional": (
                    str(abs(new_position) * reference_price)
                    if reference_price is not None
                    else None
                ),
                "reference_price": str(reference_price) if reference_price is not None else None,
                "max_position_units": str(self._config.max_position_units),
                "max_notional": str(self._config.max_notional),
                "daily_realized_loss": str(self._daily_realized_loss),
                "max_daily_loss": str(self._config.max_daily_loss),
                "risk_model_version": self._config.risk_model_version,
                "portfolio_funding_policy": self._config.portfolio_funding_policy.value,
                "kill_switch_position_policy": self._config.kill_switch_position_policy.value,
                "signal_sizing_policy": self._config.signal_sizing_policy.value,
                **(sizing_meta or {}),
            },
        )
        risk_event_id = ev.event_id

        # Apply kill switch AFTER the risk decision is journaled so the causal
        # chain is RISK_REJECTED -> KILL_SWITCH_TRIGGERED -> [flatten chain].
        if self._kill_switch_pending:
            self._kill_switch_pending = False
            self._trigger_kill_switch(
                correlation_id,
                risk_event_id,
                "MAX_DAILY_LOSS",
                reference_price=reference_price,
            )

        if not approved:
            self._portfolio.rejected_order_count += 1

        return approved, "; ".join(violations) if violations else "APPROVED", risk_event_id

    def _trigger_kill_switch(
        self,
        correlation_id: str,
        causation_id: str,
        trigger_reason: str,
        reference_price: Optional[Decimal] = None,
    ) -> None:
        """Activate kill switch, record to journal, and apply the configured policy.

        The position policy is applied FIRMLY:
        - HALT_AND_PRESERVE_POSITION: no position mutation (H01-preserving).
        - HALT_AND_FORCE_SIMULATED_FLATTEN: close any open position at the
          reference (mark) price via a synthetic closing fill chain. Requires a
          reference price; a missing mark is a fail-closed DataContractError
          because flattening without a price would fabricate a fill.
        - HALT_AND_REQUIRE_OPERATOR_RESOLUTION: marks the session as requiring
          an operator resolution (exposed via `operator_resolution_required`)
          and journals that requirement. No auto-flatten, no auto-resume.
        """
        self._kill_switch_active = True
        policy = self._config.kill_switch_position_policy
        if policy == KillSwitchPositionPolicy.HALT_AND_FORCE_SIMULATED_FLATTEN:
            if self._portfolio.position == Decimal("0"):
                pass  # nothing to flatten; journal policy-only payload below
            elif reference_price is None:
                raise DataContractError(
                    "KillSwitchPositionPolicy.HALT_AND_FORCE_SIMULATED_FLATTEN "
                    "requires a reference price to flatten; got None (fail-closed)"
                )
            else:
                self._force_flatten_at_mark(
                    reference_price=reference_price,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                )
        elif policy == KillSwitchPositionPolicy.HALT_AND_REQUIRE_OPERATOR_RESOLUTION:
            self._operator_resolution_required = True

        self._health.record_kill_switch(
            correlation_id=correlation_id,
            trigger_reason=trigger_reason,
            trigger_type="DAILY_LOSS_LIMIT",
            position_policy=policy.value,
            operator_resolution_required=self._operator_resolution_required,
        )

    def _force_flatten_at_mark(
        self,
        reference_price: Decimal,
        correlation_id: str,
        causation_id: str,
    ) -> None:
        """Simulate a full closing of the open position at the mark price.

        Journals the canonical synthetic closing chain so reconciliation and
        replay remain consistent with a real execution:
        ORDER_INTENT_CREATED -> FILL_SIMULATED -> POSITION_UPDATED -> PORTFOLIO_UPDATED.
        """
        qty = abs(self._portfolio.position)
        direction = (
            SignalDirection.SHORT
            if self._portfolio.position > Decimal("0")
            else SignalDirection.LONG
        )
        symbol = self._config.instrument

        closing = StrategySignal(
            strategy_id=self._config.strategy_id,
            strategy_version=self._config.strategy_version,
            evaluation_timestamp_utc=datetime.now(timezone.utc),
            symbol=symbol,
            direction=direction,
            target_quantity=qty,
            signal_strength=Decimal("1.0"),
            decision_reason="KILL_SWITCH_FORCED_FLATTEN",
            feature_snapshot={"event": "KILL_SWITCH_FORCED_FLATTEN"},
            market_event_reference="kill_switch_flatten",
            config_hash=self._config_hash,
            is_infrastructure_test=True,
            governance_label="RISK_KILL_SWITCH_FORCED_FLATTEN",
        )

        intent_id = str(uuid.uuid4())
        self._submitted_intent_ids.add(intent_id)
        self._portfolio.order_count += 1

        intent_event_id = self._journal.append(
            event_type=JournalEventType.ORDER_INTENT_CREATED,
            layer=JournalLayer.ORDER,
            event_time_utc=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            causation_id=causation_id,
            component=self.COMPONENT,
            payload={
                "order_intent_id": intent_id,
                "symbol": symbol,
                "side": direction.value,
                "quantity": str(qty),
                "order_type": "MARKET",
                "strategy_id": closing.strategy_id,
                "GOVERNANCE_LABEL": "RISK_KILL_SWITCH_FORCED_FLATTEN",
            },
        ).event_id

        fill_price = reference_price
        commission = qty * self._config.fill_commission_per_unit
        notional = fill_price * qty
        fill_id = str(uuid.uuid4())
        fill_event_id = self._journal.append(
            event_type=JournalEventType.FILL_SIMULATED,
            layer=JournalLayer.EXECUTION,
            event_time_utc=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            causation_id=intent_event_id,
            component=self.COMPONENT,
            payload={
                "fill_id": fill_id,
                "order_intent_id": intent_id,
                "symbol": symbol,
                "side": direction.value,
                "quantity": str(qty),
                "fill_price": str(fill_price),
                "reference_price": str(reference_price),
                "slippage_bps": "0",
                "fees": str(commission),
                "fill_notional": str(notional),
                "fill_model": "LOCAL_SIMULATOR_KILL_SWITCH_FLATTEN",
                "GOVERNANCE_LABEL": "RISK_KILL_SWITCH_FORCED_FLATTEN",
            },
        ).event_id

        self._update_portfolio(
            closing,
            fill_price,
            commission,
            datetime.now(timezone.utc),
            correlation_id,
            fill_event_id,
        )

    def _apply_signal_sizing(
        self,
        signal: StrategySignal,
        reference_price: Decimal,
    ) -> Tuple[StrategySignal, Dict[str, Any]]:
        """Derive the executed quantity from the configured sizing policy.

        Returns ``(execution_signal, sizing_meta)``. The execution signal
        carries the sized ``target_quantity`` and is the single authority
        downstream (risk -> order -> fill -> portfolio). Sizing never applies to
        FLAT signals (they carry quantity 0 by construction).

        Fail-closed: an invalid reference price (<= 0) or non-positive equity
        raises DataContractError — a NAV-relative quantity can never be derived
        from a fabricated price/equity baseline.
        """
        if (
            signal.direction == SignalDirection.FLAT
            or self._config.signal_sizing_policy
            == SignalSizingPolicy.INFRA_FIXED_QUANTITY
        ):
            return signal, {
                "signal_sizing_policy": self._config.signal_sizing_policy.value,
                "sizing_input_quantity": str(signal.target_quantity),
                "sizing_output_quantity": str(signal.target_quantity),
            }

        if reference_price <= Decimal("0"):
            raise DataContractError(
                f"PaperSessionRunner: cannot size NAV_RELATIVE order with "
                f"reference_price <= 0 (got {reference_price}). Fail-closed."
            )

        equity = self._portfolio.cash + (self._portfolio.position * reference_price)
        if equity <= Decimal("0"):
            raise DataContractError(
                f"PaperSessionRunner: cannot size NAV_RELATIVE order with "
                f"equity <= 0 (got {equity}). Fail-closed."
            )

        pct = self._config.nav_sizing_notional_pct
        target_notional = equity * pct / Decimal("100")
        raw_qty = target_notional / reference_price
        qty = raw_qty.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

        exec_signal = replace(signal, target_quantity=qty)
        return exec_signal, {
            "signal_sizing_policy": self._config.signal_sizing_policy.value,
            "nav_sizing_notional_pct": str(pct),
            "sizing_reference_equity": str(equity),
            "sizing_target_notional": str(target_notional),
            "sizing_input_quantity": str(signal.target_quantity),
            "sizing_output_quantity": str(qty),
        }

    def _compute_fill_price(self, bar: SyntheticBar, signal: StrategySignal) -> Decimal:
        """Compute deterministic simulated fill price with slippage."""
        slippage = bar.close * self._config.fill_slippage_bps / Decimal("10000")
        if signal.direction == SignalDirection.LONG:
            return (bar.close + slippage).quantize(Decimal("0.00001"))
        else:
            return (bar.close - slippage).quantize(Decimal("0.00001"))

    def _update_portfolio(
        self,
        signal: StrategySignal,
        fill_price: Decimal,
        commission: Decimal,
        event_time_utc: datetime,
        correlation_id: str,
        causation_id: str,
    ) -> None:
        """Update portfolio state and record to journal."""
        qty = signal.target_quantity
        notional = fill_price * qty

        prev_position = self._portfolio.position
        prev_cash = self._portfolio.cash

        if signal.direction == SignalDirection.LONG:
            # Buying
            if self._portfolio.position >= Decimal("0"):
                # Adding to or starting long
                total_position = self._portfolio.position + qty
                if total_position > Decimal("0"):
                    self._portfolio.avg_entry_price = (
                        (self._portfolio.avg_entry_price * self._portfolio.position + fill_price * qty)
                        / total_position
                    )
            else:
                # Closing short
                pnl = (self._portfolio.avg_entry_price - fill_price) * min(qty, abs(self._portfolio.position))
                self._portfolio.realized_pnl += pnl
                self._daily_realized_loss += max(Decimal("0"), -pnl)

            self._portfolio.position += qty
            self._portfolio.cash -= notional
        else:
            # Selling
            if self._portfolio.position <= Decimal("0"):
                # Adding to or starting short
                total_position = abs(self._portfolio.position) + qty
                if total_position > Decimal("0"):
                    self._portfolio.avg_entry_price = (
                        (self._portfolio.avg_entry_price * abs(self._portfolio.position) + fill_price * qty)
                        / total_position
                    )
            else:
                # Closing long
                pnl = (fill_price - self._portfolio.avg_entry_price) * min(qty, self._portfolio.position)
                self._portfolio.realized_pnl += pnl
                self._daily_realized_loss += max(Decimal("0"), -pnl)

            self._portfolio.position -= qty
            self._portfolio.cash += notional

        self._portfolio.cash -= commission
        self._portfolio.total_fees += commission
        self._portfolio.trade_count += 1

        # Record position update
        self._journal.append(
            event_type=JournalEventType.POSITION_UPDATED,
            layer=JournalLayer.PORTFOLIO,
            event_time_utc=event_time_utc,
            correlation_id=correlation_id,
            causation_id=causation_id,
            component=self.COMPONENT,
            payload={
                "previous_position": str(prev_position),
                "new_position": str(self._portfolio.position),
                "fill_price": str(fill_price),
                "quantity": str(qty),
                "side": signal.direction.value,
                "commission": str(commission),
            },
        )

        # Record portfolio update
        self._journal.append(
            event_type=JournalEventType.PORTFOLIO_UPDATED,
            layer=JournalLayer.PORTFOLIO,
            event_time_utc=event_time_utc,
            correlation_id=correlation_id,
            causation_id=causation_id,
            component=self.COMPONENT,
            payload=self._portfolio.to_summary(),
        )

    def _extract_closes_from_journal(self) -> List[Decimal]:
        """Read all MARKET_BAR_RECEIVED events and extract closing prices."""
        events = self._journal.read_all()
        closes: List[Decimal] = []
        for ev in sorted(events, key=lambda e: e.sequence):
            if ev.event_type == JournalEventType.MARKET_BAR_RECEIVED:
                close = ev.payload.get("close")
                if close is not None:
                    closes.append(Decimal(str(close)))
        return closes

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def journal(self) -> PaperEventJournal:
        return self._journal

    @property
    def session_id(self) -> str:
        return self._config.session_id

    @property
    def portfolio(self) -> PaperPortfolioState:
        return self._portfolio

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch_active

    @property
    def operator_resolution_required(self) -> bool:
        return self._operator_resolution_required

    def get_decision_trace(self, correlation_id: str) -> DecisionTrace:
        """Retrieve the complete decision chain for a correlation_id."""
        return DecisionTrace.from_journal(self._journal, correlation_id)

    def run_replay(self) -> ReplayResult:
        """Replay the current session from journal events."""
        return self._replay_engine.replay_from_journal(self._journal)

    def run_reconciliation(self) -> ReconciliationResult:
        return self._reconciler.run_full_reconciliation()

    def compute_analytics(self) -> PaperAnalyticsReport:
        return self._analytics.compute(self._journal)
