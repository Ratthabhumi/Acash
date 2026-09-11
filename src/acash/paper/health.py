"""ACASH Paper Trading — Health Monitor.

PaperHealthMonitor records system health events to the PaperEventJournal:
- Session startup / shutdown
- Feed connect / disconnect
- Heartbeat (periodic liveness)
- Stale data events
- Exception/error events
- Recovery attempts
- Kill switch activations
- Journal failure events
- Reconciliation completions

All events are written to the journal with layer=SYSTEM.
If the journal is unavailable, the monitor raises DataContractError (fail-closed).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from acash.core.domain.exceptions import DataContractError
from acash.paper.journal import JournalEventType, JournalLayer, PaperEventJournal


class HealthEventKind(str, Enum):
    """Health event kind for structured logging."""

    SESSION_STARTED = "SESSION_STARTED"
    SESSION_STOPPED = "SESSION_STOPPED"
    HEARTBEAT = "HEARTBEAT"
    FEED_CONNECTED = "FEED_CONNECTED"
    FEED_DISCONNECTED = "FEED_DISCONNECTED"
    STALE_DATA = "STALE_DATA"
    EXCEPTION = "EXCEPTION"
    RECOVERY_ATTEMPTED = "RECOVERY_ATTEMPTED"
    KILL_SWITCH = "KILL_SWITCH"
    JOURNAL_FAILURE = "JOURNAL_FAILURE"
    CONFIG_LOADED = "CONFIG_LOADED"
    RECONCILIATION_COMPLETED = "RECONCILIATION_COMPLETED"
    RECONCILIATION_FAILURE = "RECONCILIATION_FAILURE"
    INTEGRITY_CHECK = "INTEGRITY_CHECK"


# Map HealthEventKind → JournalEventType
_KIND_TO_EVENT_TYPE: Dict[HealthEventKind, JournalEventType] = {
    HealthEventKind.SESSION_STARTED: JournalEventType.SESSION_STARTED,
    HealthEventKind.SESSION_STOPPED: JournalEventType.SESSION_STOPPED,
    HealthEventKind.HEARTBEAT: JournalEventType.HEARTBEAT,
    HealthEventKind.FEED_CONNECTED: JournalEventType.FEED_CONNECTED,
    HealthEventKind.FEED_DISCONNECTED: JournalEventType.FEED_DISCONNECTED,
    HealthEventKind.STALE_DATA: JournalEventType.MARKET_BAR_STALE,
    HealthEventKind.EXCEPTION: JournalEventType.EXCEPTION_RECORDED,
    HealthEventKind.RECOVERY_ATTEMPTED: JournalEventType.RECOVERY_ATTEMPTED,
    HealthEventKind.KILL_SWITCH: JournalEventType.KILL_SWITCH_TRIGGERED,
    HealthEventKind.JOURNAL_FAILURE: JournalEventType.STORAGE_FAILURE,
    HealthEventKind.CONFIG_LOADED: JournalEventType.CONFIG_LOADED,
    HealthEventKind.RECONCILIATION_COMPLETED: JournalEventType.RECONCILIATION_COMPLETED,
    HealthEventKind.RECONCILIATION_FAILURE: JournalEventType.RECONCILIATION_FAILURE,
    HealthEventKind.INTEGRITY_CHECK: JournalEventType.JOURNAL_INTEGRITY_CHECK,
}


class PaperHealthMonitor:
    """Records system health events to the PaperEventJournal.

    Fail-closed: if the journal is unavailable, raises DataContractError.
    All events are labeled with layer=SYSTEM.
    """

    COMPONENT = "PaperHealthMonitor"

    def __init__(
        self,
        journal: PaperEventJournal,
        session_id: str,
        component_version: str = "unknown",
    ) -> None:
        self._journal = journal
        self._session_id = session_id
        self._component_version = component_version

    def record(
        self,
        kind: HealthEventKind,
        correlation_id: str,
        payload: Dict[str, Any],
        causation_id: Optional[str] = None,
        event_time_utc: Optional[datetime] = None,
    ) -> str:
        """Record a health event. Returns the committed event_id.

        Fail-closed: raises DataContractError if journal write fails.
        """
        now_utc = event_time_utc or datetime.now(timezone.utc)
        event_type = _KIND_TO_EVENT_TYPE.get(kind)
        if event_type is None:
            raise DataContractError(
                f"PaperHealthMonitor: no JournalEventType mapping for {kind!r}"
            )

        safe_payload = dict(payload)
        safe_payload["health_event_kind"] = kind.value
        safe_payload["session_id"] = self._session_id

        event = self._journal.append(
            event_type=event_type,
            layer=JournalLayer.SYSTEM,
            event_time_utc=now_utc,
            correlation_id=correlation_id,
            causation_id=causation_id,
            component=self.COMPONENT,
            component_version=self._component_version,
            payload=safe_payload,
        )
        return event.event_id

    def session_started(
        self,
        correlation_id: str,
        session_metadata: Dict[str, Any],
    ) -> str:
        """Record session start event."""
        return self.record(
            kind=HealthEventKind.SESSION_STARTED,
            correlation_id=correlation_id,
            payload={
                "event": "SESSION_STARTED",
                **session_metadata,
            },
        )

    def session_stopped(
        self,
        correlation_id: str,
        reason: str,
        final_event_count: int,
    ) -> str:
        """Record session stop event."""
        return self.record(
            kind=HealthEventKind.SESSION_STOPPED,
            correlation_id=correlation_id,
            payload={
                "event": "SESSION_STOPPED",
                "reason": reason,
                "final_event_count": final_event_count,
            },
        )

    def heartbeat(self, correlation_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record a periodic liveness heartbeat."""
        return self.record(
            kind=HealthEventKind.HEARTBEAT,
            correlation_id=correlation_id,
            payload={"event": "HEARTBEAT", **(metadata or {})},
        )

    def record_exception(
        self,
        correlation_id: str,
        exception_type: str,
        message: str,
        component: str,
        causation_id: Optional[str] = None,
    ) -> str:
        """Record an exception event (no credential leakage)."""
        return self.record(
            kind=HealthEventKind.EXCEPTION,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload={
                "event": "EXCEPTION_RECORDED",
                "exception_type": exception_type,
                "message": message[:500],  # Truncate to prevent log injection
                "source_component": component,
            },
        )

    def record_kill_switch(
        self,
        correlation_id: str,
        trigger_reason: str,
        trigger_type: str,
    ) -> str:
        """Record a kill switch activation."""
        return self.record(
            kind=HealthEventKind.KILL_SWITCH,
            correlation_id=correlation_id,
            payload={
                "event": "KILL_SWITCH_TRIGGERED",
                "trigger_reason": trigger_reason,
                "trigger_type": trigger_type,
            },
        )

    def record_reconciliation(
        self,
        correlation_id: str,
        status: str,
        violation_count: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record reconciliation result."""
        kind = (
            HealthEventKind.RECONCILIATION_COMPLETED
            if violation_count == 0
            else HealthEventKind.RECONCILIATION_FAILURE
        )
        return self.record(
            kind=kind,
            correlation_id=correlation_id,
            payload={
                "event": "RECONCILIATION",
                "status": status,
                "violation_count": violation_count,
                **(details or {}),
            },
        )
