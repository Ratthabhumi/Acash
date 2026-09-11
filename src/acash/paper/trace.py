"""ACASH Paper Trading — Decision Trace.

DecisionTrace provides a complete decision chain for a single correlation_id:

    Market Event
        ↓ (correlation_id propagated)
    Feature Snapshot
        ↓
    Strategy Evaluation → Signal
        ↓
    Risk Evaluation → Verdict
        ↓
    Order Intent
        ↓
    Order State Transitions
        ↓
    Simulated Fill(s)
        ↓
    Position Update
        ↓
    Portfolio Update

Any investigator with a correlation_id can retrieve the complete, ordered
chain of events and answer every question about what happened and why.

This module is READ-ONLY. It never writes to the journal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from acash.paper.journal import JournalEvent, JournalEventType, JournalLayer, PaperEventJournal


# ---------------------------------------------------------------------------
# DecisionTraceStep — single step in the chain
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionTraceStep:
    """A single step in the decision trace chain."""

    sequence: int
    layer: JournalLayer
    event_type: JournalEventType
    event_time_utc: datetime
    event_id: str
    correlation_id: str
    causation_id: Optional[str]
    component: str
    payload: Dict[str, Any]


# ---------------------------------------------------------------------------
# DecisionTrace — complete chain for one correlation_id
# ---------------------------------------------------------------------------


@dataclass
class DecisionTrace:
    """Complete, ordered decision chain for a single correlation_id.

    Provides structured access to all 7 execution layers for one
    decision cycle (market bar → fill → portfolio update).
    """

    correlation_id: str
    session_id: str
    steps: List[DecisionTraceStep] = field(default_factory=list)

    # Convenience views by layer
    market_data_events: List[DecisionTraceStep] = field(default_factory=list)
    feature_events: List[DecisionTraceStep] = field(default_factory=list)
    signal_events: List[DecisionTraceStep] = field(default_factory=list)
    risk_events: List[DecisionTraceStep] = field(default_factory=list)
    order_events: List[DecisionTraceStep] = field(default_factory=list)
    execution_events: List[DecisionTraceStep] = field(default_factory=list)
    portfolio_events: List[DecisionTraceStep] = field(default_factory=list)
    system_events: List[DecisionTraceStep] = field(default_factory=list)

    @classmethod
    def from_journal(cls, journal: PaperEventJournal, correlation_id: str) -> "DecisionTrace":
        """Build a complete decision trace by querying the journal."""
        raw_events: List[JournalEvent] = journal.read_by_correlation(correlation_id)
        return cls.from_events(raw_events, correlation_id)

    @classmethod
    def from_events(
        cls,
        events: Sequence[JournalEvent],
        correlation_id: str,
    ) -> "DecisionTrace":
        """Build a DecisionTrace from a pre-loaded list of JournalEvents."""
        relevant = sorted(
            [e for e in events if e.correlation_id == correlation_id],
            key=lambda e: e.sequence,
        )

        if not relevant:
            return cls(correlation_id=correlation_id, session_id="UNKNOWN")

        session_id = relevant[0].session_id
        trace = cls(correlation_id=correlation_id, session_id=session_id)

        _layer_map = {
            JournalLayer.MARKET_DATA: trace.market_data_events,
            JournalLayer.FEATURE: trace.feature_events,
            JournalLayer.SIGNAL: trace.signal_events,
            JournalLayer.RISK: trace.risk_events,
            JournalLayer.ORDER: trace.order_events,
            JournalLayer.EXECUTION: trace.execution_events,
            JournalLayer.PORTFOLIO: trace.portfolio_events,
            JournalLayer.SYSTEM: trace.system_events,
        }

        for ev in relevant:
            step = DecisionTraceStep(
                sequence=ev.sequence,
                layer=ev.layer,
                event_type=ev.event_type,
                event_time_utc=ev.event_time_utc,
                event_id=ev.event_id,
                correlation_id=ev.correlation_id,
                causation_id=ev.causation_id,
                component=ev.component,
                payload=dict(ev.payload),
            )
            trace.steps.append(step)
            target_list = _layer_map.get(ev.layer)
            if target_list is not None:
                target_list.append(step)

        return trace

    # ------------------------------------------------------------------
    # Diagnostic helpers
    # ------------------------------------------------------------------

    def is_complete(self) -> bool:
        """True if the trace covers at least: SIGNAL → RISK → ORDER → EXECUTION."""
        has_signal = bool(self.signal_events)
        has_risk = bool(self.risk_events)
        has_order = bool(self.order_events)
        has_execution = bool(self.execution_events)
        return has_signal and has_risk and has_order and has_execution

    def summary(self) -> Dict[str, Any]:
        """Return a concise summary dictionary for logging/reporting."""
        return {
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "total_steps": len(self.steps),
            "layers_present": sorted(set(s.layer.value for s in self.steps)),
            "is_complete": self.is_complete(),
            "market_data_count": len(self.market_data_events),
            "feature_count": len(self.feature_events),
            "signal_count": len(self.signal_events),
            "risk_count": len(self.risk_events),
            "order_count": len(self.order_events),
            "execution_count": len(self.execution_events),
            "portfolio_count": len(self.portfolio_events),
            "system_count": len(self.system_events),
        }
