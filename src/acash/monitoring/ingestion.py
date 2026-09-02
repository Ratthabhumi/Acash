"""Phase 11: Forward Telemetry Stream Ingestion & Sequence Guards.

Strictly enforces:
1. Per-Strategy Stream Identity:
   Telemetry streams are partition-isolated by strategy_id.
2. Monotonic Sequence Invariant:
   Seq_s[k] = Seq_s[k-1] + 1 (starts at sequence 0).
3. Monotonic As-Of Timestamp Invariant:
   as_of_utc[k] > as_of_utc[k-1] (strictly increasing time).
4. Duplicate Protection:
   Rejects duplicate observation_id or duplicate (strategy_id, observation_sequence) keys.
5. Fail-Closed Gap Defense (MONITORING_BLOCKED):
   Sequence gaps, temporal reversals, or corrupt observations permanently block the stream,
   forcing downstream state machines to transition to MONITORING_BLOCKED.
6. Separation of Concerns:
   Ingestion is solely responsible for data integrity and stream continuity.
   It does NOT evaluate strategy health, performance degradation, or exclusion.
"""

from __future__ import annotations

from datetime import datetime
import threading
from typing import Any, Dict, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.schema import ForwardObservation


class StreamStatus(BaseModel):
    """Immutable snapshot of an ingested strategy telemetry stream."""

    model_config = ConfigDict(frozen=True)

    strategy_id: str
    last_sequence: int = -1
    last_as_of_utc: Optional[datetime] = None
    observation_count: int = 0
    is_telemetry_valid: bool = True
    block_reason: Optional[str] = None


class ForwardTelemetryIngestor:
    """Thread-safe stream ingestor enforcing sequence continuity and fail-closed telemetry guards."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Per-strategy mutable tracking state: strategy_id -> dict
        self._stream_state: Dict[str, Dict[str, Any]] = {}
        self._seen_observation_ids: Set[str] = set()
        self._seen_composite_keys: Set[Tuple[str, int]] = set()

    def ingest_observation(self, observation: ForwardObservation) -> ForwardObservation:
        """Ingest and validate a forward observation against stream continuity invariants.

        Args:
            observation: Validated ForwardObservation DTO.

        Returns:
            The identical ForwardObservation if all stream invariants hold.

        Raises:
            DataContractError: On sequence gap, temporal reversal, duplicate observation,
                               or if the stream is already permanently blocked.
        """
        with self._lock:
            strat_id = observation.strategy_id
            state = self._stream_state.get(strat_id)

            # 1. Stream Blocked Check
            if state is not None and not state["is_telemetry_valid"]:
                raise DataContractError(
                    f"STREAM_PERMANENTLY_BLOCKED: Strategy '{strat_id}' telemetry stream was permanently "
                    f"blocked due to: {state['block_reason']}. Ingestion rejected."
                )

            # 2. Duplicate Check
            if observation.observation_id in self._seen_observation_ids:
                self._block_stream_internal(strat_id, f"DUPLICATE_OBSERVATION_ID: {observation.observation_id}")
                raise DataContractError(
                    f"DUPLICATE_OBSERVATION_REJECTED: observation_id '{observation.observation_id}' "
                    f"already ingested for strategy '{strat_id}'."
                )

            comp_key = (strat_id, observation.observation_sequence)
            if comp_key in self._seen_composite_keys:
                self._block_stream_internal(strat_id, f"DUPLICATE_SEQUENCE_NUMBER: {observation.observation_sequence}")
                raise DataContractError(
                    f"DUPLICATE_COMPOSITE_IDENTITY: Sequence {observation.observation_sequence} "
                    f"already ingested for strategy '{strat_id}'."
                )

            # 3. Monotonic Sequence Invariant
            if state is None:
                # First observation in the stream must start at sequence 0
                if observation.observation_sequence != 0:
                    self._block_stream_internal(
                        strat_id,
                        f"INITIAL_SEQUENCE_GAP: Expected sequence 0, got {observation.observation_sequence}",
                    )
                    raise DataContractError(
                        f"SEQUENCE_GAP_DETECTED: Strategy '{strat_id}' stream must start at sequence 0, "
                        f"got {observation.observation_sequence}."
                    )
            else:
                expected_seq = state["last_sequence"] + 1
                if observation.observation_sequence != expected_seq:
                    self._block_stream_internal(
                        strat_id,
                        f"SEQUENCE_GAP: Expected sequence {expected_seq}, got {observation.observation_sequence}",
                    )
                    raise DataContractError(
                        f"SEQUENCE_GAP_DETECTED: Strategy '{strat_id}' expected sequence {expected_seq}, "
                        f"got {observation.observation_sequence}."
                    )

            # 4. Monotonic Timestamp Invariant (as_of[k] > as_of[k-1])
            if state is not None and state["last_as_of_utc"] is not None:
                last_as_of = state["last_as_of_utc"]
                if observation.as_of_utc <= last_as_of:
                    self._block_stream_internal(
                        strat_id,
                        f"TEMPORAL_REVERSAL: as_of_utc {observation.as_of_utc.isoformat()} <= {last_as_of.isoformat()}",
                    )
                    raise DataContractError(
                        f"TEMPORAL_ORDER_VIOLATION: Strategy '{strat_id}' as_of_utc ({observation.as_of_utc.isoformat()}) "
                        f"must be strictly greater than preceding as_of_utc ({last_as_of.isoformat()})."
                    )

            # 5. Upstream Telemetry Corruption Guard
            if not observation.is_telemetry_valid:
                self._block_stream_internal(strat_id, "UPSTREAM_TELEMETRY_INVALID")
                # Stream is blocked, but this observation is recorded to allow downstream
                # state machine to transition to MONITORING_BLOCKED.

            # Commit to stream state
            self._seen_observation_ids.add(observation.observation_id)
            self._seen_composite_keys.add(comp_key)

            if state is None:
                self._stream_state[strat_id] = {
                    "strategy_id": strat_id,
                    "last_sequence": observation.observation_sequence,
                    "last_as_of_utc": observation.as_of_utc,
                    "observation_count": 1,
                    "is_telemetry_valid": observation.is_telemetry_valid,
                    "block_reason": "UPSTREAM_TELEMETRY_INVALID" if not observation.is_telemetry_valid else None,
                }
            else:
                state["last_sequence"] = observation.observation_sequence
                state["last_as_of_utc"] = observation.as_of_utc
                state["observation_count"] += 1
                if not observation.is_telemetry_valid:
                    state["is_telemetry_valid"] = False
                    state["block_reason"] = "UPSTREAM_TELEMETRY_INVALID"

            return observation

    def is_telemetry_valid(self, strategy_id: str) -> bool:
        """Check whether the strategy stream is active and free from sequence gaps or corruption."""
        with self._lock:
            state = self._stream_state.get(strategy_id)
            if state is None:
                return True
            return bool(state["is_telemetry_valid"])

    def get_stream_status(self, strategy_id: str) -> Optional[StreamStatus]:
        """Return an immutable status snapshot of the specified strategy stream."""
        with self._lock:
            state = self._stream_state.get(strategy_id)
            if state is None:
                return None
            return StreamStatus(
                strategy_id=state["strategy_id"],
                last_sequence=state["last_sequence"],
                last_as_of_utc=state["last_as_of_utc"],
                observation_count=state["observation_count"],
                is_telemetry_valid=state["is_telemetry_valid"],
                block_reason=state["block_reason"],
            )

    def _block_stream_internal(self, strategy_id: str, reason: str) -> None:
        """Internal helper marking a strategy stream permanently blocked (must be called with lock held)."""
        state = self._stream_state.get(strategy_id)
        if state is None:
            self._stream_state[strategy_id] = {
                "strategy_id": strategy_id,
                "last_sequence": -1,
                "last_as_of_utc": None,
                "observation_count": 0,
                "is_telemetry_valid": False,
                "block_reason": reason,
            }
        else:
            state["is_telemetry_valid"] = False
            state["block_reason"] = reason
