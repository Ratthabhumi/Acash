"""ACASH Paper Trading — E3 Black-Box Event Journal.

PaperEventJournal is the append-only, hash-chained event log that records
EVERY state transition across all 7 execution layers:

    Layer 1: MARKET_DATA    — normalized market data as seen by strategy
    Layer 2: FEATURE        — feature snapshot and indicator values
    Layer 3: SIGNAL         — strategy evaluation and signal output
    Layer 4: RISK           — pre-trade risk evaluation and verdict
    Layer 5: ORDER          — order intent, lifecycle state transitions
    Layer 6: EXECUTION      — simulated fills, fill model, slippage
    Layer 7: PORTFOLIO      — position and portfolio state updates
    Layer 8: SYSTEM         — health, startup, shutdown, error events

Design contracts:
- Every event has: event_id, session_id, sequence, event_type, event_time,
  recorded_at, schema_version, correlation_id, causation_id, component,
  payload, previous_event_hash, event_hash.
- Hash chain: event_hash = SHA256(canonical_json(event_without_hash))
  event[n].previous_event_hash == event[n-1].event_hash (genesis = "0"*64)
- Fail-closed: if persistence fails → DataContractError, DO NOT continue.
- Append-only: never overwrite or mutate historical events.
- Idempotent: duplicate event_id is rejected with DataContractError.
- Thread-safe: all writes are serialized under a lock.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JOURNAL_SCHEMA_VERSION = "1.0.0"
GENESIS_PREVIOUS_HASH = "0" * 64
_SHA256_PATTERN_LEN = 64


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JournalLayer(str, Enum):
    """Execution layer that produced an event."""

    MARKET_DATA = "MARKET_DATA"
    FEATURE = "FEATURE"
    SIGNAL = "SIGNAL"
    RISK = "RISK"
    ORDER = "ORDER"
    EXECUTION = "EXECUTION"
    PORTFOLIO = "PORTFOLIO"
    SYSTEM = "SYSTEM"


class JournalEventType(str, Enum):
    """Fine-grained event type within a layer."""

    # MARKET_DATA layer
    MARKET_BAR_RECEIVED = "MARKET_BAR_RECEIVED"
    MARKET_BAR_STALE = "MARKET_BAR_STALE"
    MARKET_BAR_REJECTED = "MARKET_BAR_REJECTED"
    FEED_CONNECTED = "FEED_CONNECTED"
    FEED_DISCONNECTED = "FEED_DISCONNECTED"

    # FEATURE layer
    FEATURE_SNAPSHOT = "FEATURE_SNAPSHOT"

    # SIGNAL layer
    SIGNAL_EVALUATED = "SIGNAL_EVALUATED"
    SIGNAL_FLAT = "SIGNAL_FLAT"
    SIGNAL_LONG = "SIGNAL_LONG"
    SIGNAL_SHORT = "SIGNAL_SHORT"

    # RISK layer
    RISK_EVALUATED = "RISK_EVALUATED"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    KILL_SWITCH_TRIGGERED = "KILL_SWITCH_TRIGGERED"

    # ORDER layer
    ORDER_INTENT_CREATED = "ORDER_INTENT_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCEL_REQUESTED = "ORDER_CANCEL_REQUESTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    ORDER_FAILED = "ORDER_FAILED"
    DUPLICATE_ORDER_BLOCKED = "DUPLICATE_ORDER_BLOCKED"

    # EXECUTION layer
    FILL_SIMULATED = "FILL_SIMULATED"
    PARTIAL_FILL_SIMULATED = "PARTIAL_FILL_SIMULATED"

    # PORTFOLIO layer
    POSITION_UPDATED = "POSITION_UPDATED"
    PORTFOLIO_UPDATED = "PORTFOLIO_UPDATED"
    PORTFOLIO_SNAPSHOT = "PORTFOLIO_SNAPSHOT"

    # SYSTEM layer
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_STOPPED = "SESSION_STOPPED"
    HEARTBEAT = "HEARTBEAT"
    JOURNAL_INTEGRITY_CHECK = "JOURNAL_INTEGRITY_CHECK"
    RECONCILIATION_COMPLETED = "RECONCILIATION_COMPLETED"
    RECONCILIATION_FAILURE = "RECONCILIATION_FAILURE"
    STORAGE_FAILURE = "STORAGE_FAILURE"
    CONFIG_LOADED = "CONFIG_LOADED"
    EXCEPTION_RECORDED = "EXCEPTION_RECORDED"
    RECOVERY_ATTEMPTED = "RECOVERY_ATTEMPTED"


# ---------------------------------------------------------------------------
# JournalEvent — the canonical event record
# ---------------------------------------------------------------------------


class JournalEvent(BaseModel):
    """Immutable, hash-chained event record for the Paper Event Journal.

    Invariants:
    - event_id must be globally unique (UUID4 recommended).
    - correlation_id links all events in one decision chain (market→fill).
    - causation_id links to the specific parent event that caused this event.
    - event_hash = SHA256(canonical(self_without_hash_fields))
    - previous_event_hash = event_hash of preceding event (or genesis).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    event_id: str = Field(description="Globally unique event identifier (UUID4).")
    session_id: str = Field(description="Paper trading session identifier.")
    sequence: int = Field(ge=0, description="Monotonically increasing sequence number (0-indexed).")

    # Classification
    event_type: JournalEventType = Field(description="Fine-grained event type.")
    layer: JournalLayer = Field(description="Execution layer that produced this event.")

    # Timing
    event_time_utc: datetime = Field(description="Business time — when the event occurred in market time.")
    recorded_at_utc: datetime = Field(description="Wall clock — when the event was written to journal.")

    # Schema
    schema_version: str = Field(default=JOURNAL_SCHEMA_VERSION, description="Journal schema version.")

    # Tracing
    correlation_id: str = Field(
        description="Links all events in one decision chain (MarketBar → Fill). "
        "Set at MARKET_DATA ingestion; propagated to all downstream events."
    )
    causation_id: Optional[str] = Field(
        default=None,
        description="event_id of the direct parent event that caused this event. "
        "None for root events (MARKET_DATA, SYSTEM).",
    )

    # Component provenance
    component: str = Field(description="Component name that emitted this event.")
    component_version: str = Field(default="unknown", description="Component semantic version.")
    git_commit: str = Field(default="unknown", description="Git commit SHA at session start.")

    # Payload — layer-specific structured data
    payload: Dict[str, Any] = Field(description="Layer-specific structured event payload.")

    # Hash chain
    previous_event_hash: str = Field(
        description="SHA-256 hash of the preceding event. Genesis events use '0'*64."
    )
    event_hash: str = Field(description="SHA-256 hash of this event (canonical serialization).")

    @field_validator("event_id", "session_id", "correlation_id", "component")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise DataContractError(f"JournalEvent field must be non-empty, got: {v!r}")
        return v.strip()

    @field_validator("event_time_utc", "recorded_at_utc", mode="before")
    @classmethod
    def validate_utc(cls, v: Any) -> datetime:
        if isinstance(v, str):
            try:
                v = datetime.fromisoformat(v)
            except Exception as exc:
                raise DataContractError(f"Invalid datetime string: {v!r}") from exc
        if not isinstance(v, datetime):
            raise DataContractError(f"Expected datetime, got {type(v)}")
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise DataContractError("JournalEvent datetimes must be timezone-aware UTC.")
        return v.astimezone(timezone.utc)

    @field_validator("previous_event_hash", "event_hash")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not isinstance(v, str) or len(v) != _SHA256_PATTERN_LEN:
            raise DataContractError(
                f"Hash field must be 64-char hex SHA-256, got: {v!r}"
            )
        if not all(c in "0123456789abcdef" for c in v):
            raise DataContractError(
                f"Hash field must be lowercase hex, got: {v!r}"
            )
        return v

    @staticmethod
    def compute_hash(
        event_id: str,
        session_id: str,
        sequence: int,
        event_type: JournalEventType,
        layer: JournalLayer,
        event_time_utc: datetime,
        recorded_at_utc: datetime,
        schema_version: str,
        correlation_id: str,
        causation_id: Optional[str],
        component: str,
        component_version: str,
        git_commit: str,
        payload: Dict[str, Any],
        previous_event_hash: str,
    ) -> str:
        """Compute canonical SHA-256 hash for this event (excluding event_hash itself)."""
        canonical_payload = {
            "event_id": event_id,
            "session_id": session_id,
            "sequence": sequence,
            "event_type": event_type.value if isinstance(event_type, Enum) else event_type,
            "layer": layer.value if isinstance(layer, Enum) else layer,
            "event_time_utc": event_time_utc.isoformat(),
            "recorded_at_utc": recorded_at_utc.isoformat(),
            "schema_version": schema_version,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "component": component,
            "component_version": component_version,
            "git_commit": git_commit,
            "payload": payload,
            "previous_event_hash": previous_event_hash,
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(
            canonical_payload
        ).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def verify_self_hash(self) -> bool:
        """Verify this event's hash is consistent with its own contents."""
        expected = self.compute_hash(
            event_id=self.event_id,
            session_id=self.session_id,
            sequence=self.sequence,
            event_type=self.event_type,
            layer=self.layer,
            event_time_utc=self.event_time_utc,
            recorded_at_utc=self.recorded_at_utc,
            schema_version=self.schema_version,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            component=self.component,
            component_version=self.component_version,
            git_commit=self.git_commit,
            payload=self.payload,
            previous_event_hash=self.previous_event_hash,
        )
        return self.event_hash == expected


# ---------------------------------------------------------------------------
# PaperEventJournal
# ---------------------------------------------------------------------------


class PaperEventJournal:
    """Append-only, hash-chained, per-event journal for Paper Trading.

    Fail-closed contract:
    - append() raises DataContractError if persistence fails.
    - append() raises DataContractError on duplicate event_id.
    - The journal is NOT usable for trading decisions (it is evidence only).
    - Journal failure MUST cause the caller to halt trading decisions.

    Storage format: JSON Lines (.jsonl), one event per line.
    Encoding: UTF-8.
    """

    def __init__(
        self,
        session_id: str,
        persistence_path: Path,
        git_commit: str = "unknown",
        component_version: str = "unknown",
    ) -> None:
        if not session_id or not session_id.strip():
            raise DataContractError("PaperEventJournal: session_id must be non-empty.")

        self._session_id = session_id
        self._path = Path(persistence_path)
        self._git_commit = git_commit
        self._component_version = component_version

        self._lock = threading.Lock()
        self._sequence: int = -1
        self._last_hash: str = GENESIS_PREVIOUS_HASH
        self._seen_event_ids: Set[str] = set()
        self._event_count: int = 0

        # Ensure directory
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise DataContractError(
                f"PaperEventJournal: cannot create directory "
                f"'{self._path.parent}': {exc}"
            ) from exc

        # Replay existing events on startup
        if self._path.exists() and self._path.stat().st_size > 0:
            self._replay_existing()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def event_count(self) -> int:
        with self._lock:
            return self._event_count

    @property
    def last_event_hash(self) -> str:
        with self._lock:
            return self._last_hash

    @property
    def last_sequence(self) -> int:
        with self._lock:
            return self._sequence

    def new_correlation_id(self) -> str:
        """Generate a new correlation ID (UUID4) for a fresh decision chain."""
        return str(uuid.uuid4())

    def append(
        self,
        *,
        event_type: JournalEventType,
        layer: JournalLayer,
        event_time_utc: datetime,
        correlation_id: str,
        component: str,
        payload: Dict[str, Any],
        causation_id: Optional[str] = None,
        component_version: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> JournalEvent:
        """Append an event to the journal. Fail-closed on any error.

        Returns the committed JournalEvent.
        Raises DataContractError if:
        - event_id already seen (duplicate)
        - persistence fails
        - internal contract violation
        """
        with self._lock:
            eid = event_id or str(uuid.uuid4())

            if eid in self._seen_event_ids:
                raise DataContractError(
                    f"PaperEventJournal: duplicate event_id '{eid}'. "
                    "Idempotency contract violated."
                )

            now_utc = datetime.now(timezone.utc)
            next_seq = self._sequence + 1
            prev_hash = self._last_hash
            cv = component_version or self._component_version

            event_hash = JournalEvent.compute_hash(
                event_id=eid,
                session_id=self._session_id,
                sequence=next_seq,
                event_type=event_type,
                layer=layer,
                event_time_utc=event_time_utc,
                recorded_at_utc=now_utc,
                schema_version=JOURNAL_SCHEMA_VERSION,
                correlation_id=correlation_id,
                causation_id=causation_id,
                component=component,
                component_version=cv,
                git_commit=self._git_commit,
                payload=payload,
                previous_event_hash=prev_hash,
            )

            event = JournalEvent(
                event_id=eid,
                session_id=self._session_id,
                sequence=next_seq,
                event_type=event_type,
                layer=layer,
                event_time_utc=event_time_utc,
                recorded_at_utc=now_utc,
                schema_version=JOURNAL_SCHEMA_VERSION,
                correlation_id=correlation_id,
                causation_id=causation_id,
                component=component,
                component_version=cv,
                git_commit=self._git_commit,
                payload=payload,
                previous_event_hash=prev_hash,
                event_hash=event_hash,
            )

            # Persist — fail-closed
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(event.model_dump_json() + "\n")
                    fh.flush()
            except Exception as exc:
                raise DataContractError(
                    f"PaperEventJournal: persistence failure for event '{eid}': {exc}. "
                    "TRADING DECISIONS MUST HALT."
                ) from exc

            # Update in-memory state only after successful persistence
            self._sequence = next_seq
            self._last_hash = event_hash
            self._seen_event_ids.add(eid)
            self._event_count += 1

            return event

    def read_all(self) -> List[JournalEvent]:
        """Read all events from disk (for replay/audit). Thread-safe."""
        with self._lock:
            return self._load_events()

    def read_by_correlation(self, correlation_id: str) -> List[JournalEvent]:
        """Read all events belonging to a correlation_id (decision chain)."""
        with self._lock:
            return [
                e for e in self._load_events()
                if e.correlation_id == correlation_id
            ]

    def verify_integrity(self) -> List[str]:
        """Verify hash chain integrity. Returns list of violation messages (empty = OK).

        This is a read-only audit operation; it does NOT mutate journal state.
        """
        with self._lock:
            events = self._load_events()
        violations: List[str] = []
        expected_prev = GENESIS_PREVIOUS_HASH
        expected_seq = 0
        seen_ids: Set[str] = set()

        for ev in events:
            # Sequence check
            if ev.sequence != expected_seq:
                violations.append(
                    f"Sequence gap: expected {expected_seq}, got {ev.sequence} "
                    f"(event_id={ev.event_id})"
                )
            # Duplicate check
            if ev.event_id in seen_ids:
                violations.append(f"Duplicate event_id: {ev.event_id}")
            seen_ids.add(ev.event_id)

            # Previous hash chain check
            if ev.previous_event_hash != expected_prev:
                violations.append(
                    f"Chain break at seq={ev.sequence}: "
                    f"expected previous_hash={expected_prev!r}, "
                    f"got {ev.previous_event_hash!r} (event_id={ev.event_id})"
                )

            # Self-hash check
            if not ev.verify_self_hash():
                violations.append(
                    f"Self-hash mismatch at seq={ev.sequence} "
                    f"(event_id={ev.event_id}). TAMPER DETECTED."
                )

            expected_prev = ev.event_hash
            expected_seq += 1

        return violations

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_events(self) -> List[JournalEvent]:
        """Read all events from disk without acquiring the lock (caller holds lock)."""
        if not self._path.exists():
            return []
        events: List[JournalEvent] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    events.append(JournalEvent.model_validate(raw))
                except Exception as exc:
                    raise DataContractError(
                        f"PaperEventJournal: corrupted event at line {line_num} "
                        f"in '{self._path}': {exc}"
                    ) from exc
        return events

    def _replay_existing(self) -> None:
        """On startup, replay existing events to restore in-memory state."""
        events = self._load_events()
        expected_prev = GENESIS_PREVIOUS_HASH
        expected_seq = 0

        for ev in events:
            if ev.sequence != expected_seq:
                raise DataContractError(
                    f"PaperEventJournal startup: sequence gap at seq={expected_seq}, "
                    f"got seq={ev.sequence}. Journal may be corrupt."
                )
            if ev.previous_event_hash != expected_prev:
                raise DataContractError(
                    f"PaperEventJournal startup: hash chain break at seq={ev.sequence}. "
                    "Journal integrity violation."
                )
            if not ev.verify_self_hash():
                raise DataContractError(
                    f"PaperEventJournal startup: self-hash mismatch at seq={ev.sequence}. "
                    "TAMPER DETECTED."
                )
            if ev.event_id in self._seen_event_ids:
                raise DataContractError(
                    f"PaperEventJournal startup: duplicate event_id '{ev.event_id}'."
                )

            self._seen_event_ids.add(ev.event_id)
            expected_prev = ev.event_hash
            expected_seq += 1

        if events:
            self._sequence = events[-1].sequence
            self._last_hash = events[-1].event_hash
            self._event_count = len(events)
