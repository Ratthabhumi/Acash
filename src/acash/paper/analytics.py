"""ACASH Paper Trading — Analytics Engine.

PaperAnalyticsEngine computes observed metrics from paper trading journal data.

GOVERNANCE SEPARATION:
======================
Metrics produced here are OBSERVED PAPER DATA.
They are NOT:
- Strategy validation evidence
- Statistical qualification evidence
- Proof of future profitability
- Authorization for any trading
- Evidence that D17-E is resolved

All analytics outputs are labeled:
    OBSERVED_PAPER_DATA_ONLY
    NOT_STRATEGY_QUALIFICATION_EVIDENCE

Metrics are computed from FILL events in the journal (not assumed or modeled).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from acash.paper.journal import JournalEvent, JournalEventType, JournalLayer, PaperEventJournal


# ---------------------------------------------------------------------------
# PaperAnalyticsReport
# ---------------------------------------------------------------------------


@dataclass
class PaperAnalyticsReport:
    """Observed metrics from a paper trading session.

    GOVERNANCE: OBSERVED_PAPER_DATA_ONLY — not strategy qualification.
    """

    session_id: str
    computed_at_utc: datetime
    governance_label: str = "OBSERVED_PAPER_DATA_ONLY"
    not_qualification_evidence: bool = True

    # Strategy metrics (from SIGNAL events)
    total_signal_evaluations: int = 0
    long_signals: int = 0
    short_signals: int = 0
    flat_signals: int = 0

    # Order metrics (from ORDER events)
    total_orders_submitted: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    orders_cancelled: int = 0
    orders_expired: int = 0

    # Fill metrics (from EXECUTION events)
    total_fills: int = 0
    total_volume: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    total_notional: Decimal = Decimal("0")
    avg_fill_slippage_bps: Optional[Decimal] = None

    # Risk metrics (from RISK events)
    risk_approvals: int = 0
    risk_rejections: int = 0
    kill_switch_events: int = 0

    # System metrics (from SYSTEM events)
    feed_disconnects: int = 0
    stale_data_events: int = 0
    exception_events: int = 0
    reconciliation_failures: int = 0

    # Data quality
    total_bars_received: int = 0
    total_bars_stale: int = 0
    total_bars_rejected: int = 0

    # Raw fill records for P&L calculation
    fill_records: List[Dict[str, Any]] = field(default_factory=list)

    def fill_rate(self) -> Optional[Decimal]:
        """Fill rate = filled / submitted."""
        if self.total_orders_submitted == 0:
            return None
        return Decimal(str(self.orders_filled)) / Decimal(str(self.total_orders_submitted))

    def reject_rate(self) -> Optional[Decimal]:
        """Rejection rate = rejected / submitted."""
        if self.total_orders_submitted == 0:
            return None
        return Decimal(str(self.orders_rejected)) / Decimal(str(self.total_orders_submitted))

    def to_summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "computed_at_utc": self.computed_at_utc.isoformat(),
            "governance_label": self.governance_label,
            "not_qualification_evidence": self.not_qualification_evidence,
            # Strategy
            "total_signal_evaluations": self.total_signal_evaluations,
            "long_signals": self.long_signals,
            "short_signals": self.short_signals,
            "flat_signals": self.flat_signals,
            # Orders
            "total_orders_submitted": self.total_orders_submitted,
            "orders_filled": self.orders_filled,
            "orders_rejected": self.orders_rejected,
            "orders_cancelled": self.orders_cancelled,
            "fill_rate": str(self.fill_rate()) if self.fill_rate() is not None else None,
            "reject_rate": str(self.reject_rate()) if self.reject_rate() is not None else None,
            # Execution
            "total_fills": self.total_fills,
            "total_volume": str(self.total_volume),
            "total_fees": str(self.total_fees),
            "total_notional": str(self.total_notional),
            "avg_fill_slippage_bps": str(self.avg_fill_slippage_bps) if self.avg_fill_slippage_bps else None,
            # Risk
            "risk_approvals": self.risk_approvals,
            "risk_rejections": self.risk_rejections,
            "kill_switch_events": self.kill_switch_events,
            # System
            "feed_disconnects": self.feed_disconnects,
            "stale_data_events": self.stale_data_events,
            "exception_events": self.exception_events,
            "reconciliation_failures": self.reconciliation_failures,
            # Data quality
            "total_bars_received": self.total_bars_received,
            "total_bars_stale": self.total_bars_stale,
            "total_bars_rejected": self.total_bars_rejected,
        }


# ---------------------------------------------------------------------------
# PaperAnalyticsEngine
# ---------------------------------------------------------------------------


class PaperAnalyticsEngine:
    """Compute observed metrics from paper trading journal.

    GOVERNANCE: Outputs are OBSERVED_PAPER_DATA_ONLY.
    Never use as strategy qualification evidence.
    """

    def __init__(self, session_id: str) -> None:
        if not session_id or not session_id.strip():
            raise ValueError("PaperAnalyticsEngine: session_id must be non-empty.")
        self._session_id = session_id

    def compute(self, journal: PaperEventJournal) -> PaperAnalyticsReport:
        """Compute analytics report from journal events."""
        now_utc = datetime.now(timezone.utc)
        report = PaperAnalyticsReport(
            session_id=self._session_id,
            computed_at_utc=now_utc,
        )

        events = journal.read_all()
        slippage_values: List[Decimal] = []

        for ev in events:
            layer = ev.layer
            etype = ev.event_type

            # MARKET_DATA metrics
            if layer == JournalLayer.MARKET_DATA:
                if etype == JournalEventType.MARKET_BAR_RECEIVED:
                    report.total_bars_received += 1
                elif etype == JournalEventType.MARKET_BAR_STALE:
                    report.total_bars_stale += 1
                elif etype == JournalEventType.MARKET_BAR_REJECTED:
                    report.total_bars_rejected += 1
                elif etype == JournalEventType.FEED_DISCONNECTED:
                    report.feed_disconnects += 1

            # SIGNAL metrics
            elif layer == JournalLayer.SIGNAL:
                if etype in (
                    JournalEventType.SIGNAL_EVALUATED,
                    JournalEventType.SIGNAL_LONG,
                    JournalEventType.SIGNAL_SHORT,
                    JournalEventType.SIGNAL_FLAT,
                ):
                    report.total_signal_evaluations += 1
                    direction = ev.payload.get("direction", "")
                    if direction == "LONG":
                        report.long_signals += 1
                    elif direction == "SHORT":
                        report.short_signals += 1
                    else:
                        report.flat_signals += 1

            # RISK metrics
            elif layer == JournalLayer.RISK:
                if etype == JournalEventType.RISK_APPROVED:
                    report.risk_approvals += 1
                elif etype == JournalEventType.RISK_REJECTED:
                    report.risk_rejections += 1
                elif etype == JournalEventType.KILL_SWITCH_TRIGGERED:
                    report.kill_switch_events += 1

            # ORDER metrics
            elif layer == JournalLayer.ORDER:
                if etype == JournalEventType.ORDER_SUBMITTED:
                    report.total_orders_submitted += 1
                elif etype in (
                    JournalEventType.FILL_SIMULATED,
                    JournalEventType.PARTIAL_FILL_SIMULATED,
                ):
                    report.orders_filled += 1
                elif etype == JournalEventType.ORDER_REJECTED:
                    report.orders_rejected += 1
                elif etype == JournalEventType.ORDER_CANCELLED:
                    report.orders_cancelled += 1
                elif etype == JournalEventType.ORDER_EXPIRED:
                    report.orders_expired += 1

            # EXECUTION metrics
            elif layer == JournalLayer.EXECUTION:
                if etype in (
                    JournalEventType.FILL_SIMULATED,
                    JournalEventType.PARTIAL_FILL_SIMULATED,
                ):
                    report.total_fills += 1
                    qty = ev.payload.get("quantity") or ev.payload.get("fill_quantity", "0")
                    fees = ev.payload.get("fees", "0")
                    notional = ev.payload.get("fill_notional", "0")
                    slippage = ev.payload.get("slippage_bps")

                    report.total_volume += Decimal(str(qty))
                    report.total_fees += Decimal(str(fees))
                    report.total_notional += Decimal(str(notional))

                    if slippage is not None:
                        slippage_values.append(Decimal(str(slippage)))

                    report.fill_records.append(dict(ev.payload))

            # SYSTEM metrics
            elif layer == JournalLayer.SYSTEM:
                if etype == JournalEventType.EXCEPTION_RECORDED:
                    report.exception_events += 1
                elif etype == JournalEventType.RECONCILIATION_FAILURE:
                    report.reconciliation_failures += 1
                elif etype == JournalEventType.MARKET_BAR_STALE:
                    report.stale_data_events += 1

        if slippage_values:
            report.avg_fill_slippage_bps = sum(slippage_values, Decimal("0")) / Decimal(len(slippage_values))

        return report
