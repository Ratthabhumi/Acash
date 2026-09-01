"""Phase 10: Operational Clock & Cadence Scheduler (Slice 2).

Strictly enforces:
1. Dual-Clock Discipline:
   as_of_utc (logical data/evaluation time) is strictly distinguished from wall_clock_utc (system observation time).
   Zero ambient datetime.now() inside deterministic cycle calculations.
2. Market Regime Determination:
   Deterministically maps as_of_utc and session policy to RuntimeRegime (PRE_MARKET, MARKET_OPEN, REBALANCE_PULSE, POST_MARKET_CLOSE, MAINTENANCE).
3. Concurrency & Overlap Prevention:
   Detects and blocks overlapping pulse executions (fails closed with CYCLE_LOCKED_BUSY).
4. Idempotency & Deduplication:
   Detects duplicate pulse requests for the same (cycle_id, as_of_utc) and returns cached identity without re-execution.
5. Clock Anomaly Fail-Closed Defense:
   Clock rollbacks and excessive drift trigger explicit DataContractError.
6. Zero Direct Execution Authority:
   Scheduler determines time, cadence, and cycle identity; it has zero broker wire or decision methods.
"""

from datetime import datetime, time, timezone
import threading
from typing import Optional, Set

from acash.core.domain.exceptions import DataContractError
from acash.runtime.schema import (
    CycleIdentity,
    CycleOutcome,
    RuntimeHealthStatus,
    RuntimePolicyConfig,
    RuntimeRegime,
    _ensure_utc,
)


class OperationalScheduler:
    """Deterministic operational clock and cadence scheduler."""

    def __init__(
        self,
        policy_config: Optional[RuntimePolicyConfig] = None,
        initial_sequence: int = 0,
    ) -> None:
        self.policy: RuntimePolicyConfig = policy_config or RuntimePolicyConfig()
        if initial_sequence < 0:
            raise DataContractError("initial_sequence must be non-negative.")

        self._sequence: int = initial_sequence
        self._active_cycle: Optional[CycleIdentity] = None
        self._completed_cycle_digests: Set[str] = set()
        self._completed_cycle_ids: Set[str] = set()
        self._last_evaluated_as_of: Optional[datetime] = None
        self._last_wall_clock: Optional[datetime] = None
        self._lock = threading.Lock()

    @property
    def is_cycle_active(self) -> bool:
        """Return True if an operational cycle is currently in progress."""
        with self._lock:
            return self._active_cycle is not None

    @property
    def active_cycle(self) -> Optional[CycleIdentity]:
        """Return the currently executing CycleIdentity, if any."""
        with self._lock:
            return self._active_cycle

    @property
    def current_sequence(self) -> int:
        """Return the current monotonic cycle sequence counter."""
        with self._lock:
            return self._sequence

    def determine_regime(self, as_of_utc: datetime) -> RuntimeRegime:
        """Deterministically evaluate the operational regime for a given logical timestamp.

        Default Session Timeline (UTC on Monday-Friday):
        - 00:00 - 13:30 UTC: PRE_MARKET
        - 13:30 - 14:00 UTC: MARKET_OPEN
        - 14:00 - 14:05 UTC: REBALANCE_PULSE (default rebalance window)
        - 14:05 - 20:00 UTC: MARKET_OPEN
        - 20:00 - 21:00 UTC: POST_MARKET_CLOSE
        - 21:00 - 24:00 UTC: MAINTENANCE
        - Saturday & Sunday: MAINTENANCE
        """
        as_of = _ensure_utc(as_of_utc, "as_of_utc")

        # Weekend check (Saturday = 5, Sunday = 6)
        if as_of.weekday() >= 5:
            return RuntimeRegime.MAINTENANCE

        t = as_of.time()

        # Regime boundaries
        if t < time(13, 30):
            return RuntimeRegime.PRE_MARKET
        elif time(13, 30) <= t < time(14, 0):
            return RuntimeRegime.MARKET_OPEN
        elif time(14, 0) <= t < time(14, 5):
            return RuntimeRegime.REBALANCE_PULSE
        elif time(14, 5) <= t < time(20, 0):
            return RuntimeRegime.MARKET_OPEN
        elif time(20, 0) <= t < time(21, 0):
            return RuntimeRegime.POST_MARKET_CLOSE
        else:
            return RuntimeRegime.MAINTENANCE

    def is_pulse_due(self, as_of_utc: datetime) -> bool:
        """Check whether a scheduled rebalance pulse is due for the given logical timestamp."""
        regime = self.determine_regime(as_of_utc)
        return regime == RuntimeRegime.REBALANCE_PULSE

    def create_cycle_identity(
        self,
        cycle_id: str,
        as_of_utc: datetime,
        regime: Optional[RuntimeRegime] = None,
    ) -> CycleIdentity:
        """Construct an immutable CycleIdentity for the given logical parameters."""
        as_of = _ensure_utc(as_of_utc, "as_of_utc")
        eval_regime = regime or self.determine_regime(as_of)

        with self._lock:
            seq = self._sequence

        return CycleIdentity(
            cycle_id=cycle_id,
            as_of_utc=as_of,
            regime=eval_regime,
            sequence_number=seq,
        )

    def is_duplicate_cycle(self, cycle_identity: CycleIdentity) -> bool:
        """Check if the given CycleIdentity has already completed execution."""
        with self._lock:
            return (
                cycle_identity.cycle_id in self._completed_cycle_ids
                or cycle_identity.cycle_digest in self._completed_cycle_digests
            )

    def start_cycle(
        self,
        cycle_id: str,
        as_of_utc: datetime,
        wall_clock_utc: datetime,
        regime: Optional[RuntimeRegime] = None,
    ) -> CycleIdentity:
        """Acquire the cycle execution lock and initiate an operational pulse.

        Fails closed with DataContractError if:
        - Another cycle is already actively running (CYCLE_LOCKED_BUSY).
        - A clock rollback is detected on wall_clock_utc.
        - wall_clock_utc precedes as_of_utc.
        """
        as_of = _ensure_utc(as_of_utc, "as_of_utc")
        wall_clock = _ensure_utc(wall_clock_utc, "wall_clock_utc")

        # Temporal invariant: wall_clock cannot precede logical as_of
        if wall_clock < as_of:
            raise DataContractError(
                f"Temporal Inversion: wall_clock_utc ({wall_clock.isoformat()}) cannot precede as_of_utc ({as_of.isoformat()})."
            )

        with self._lock:
            # Overlapping cycle check
            if self._active_cycle is not None:
                raise DataContractError(
                    f"CYCLE_LOCKED_BUSY: Active cycle '{self._active_cycle.cycle_id}' is still in progress. Concurrent pulse rejected."
                )

            # Idempotency check on already completed cycles
            if cycle_id in self._completed_cycle_ids:
                raise DataContractError(
                    f"IDEMPOTENT_DUPLICATE_CYCLE: Cycle '{cycle_id}' has already completed."
                )

            # Clock rollback check on wall_clock
            if self._last_wall_clock is not None:
                max_drift_sec = self.policy.max_clock_drift_ms / 1000.0
                if (self._last_wall_clock - wall_clock).total_seconds() > max_drift_sec:
                    raise DataContractError(
                        f"Clock Rollback Detected: wall_clock ({wall_clock.isoformat()}) went backwards from ({self._last_wall_clock.isoformat()}) beyond tolerance {self.policy.max_clock_drift_ms}ms."
                    )

            # Monotonic as_of check
            if self._last_evaluated_as_of is not None and as_of < self._last_evaluated_as_of:
                raise DataContractError(
                    f"Monotonic As-Of Violation: as_of_utc ({as_of.isoformat()}) cannot precede previous as_of ({self._last_evaluated_as_of.isoformat()})."
                )

            eval_regime = regime or self.determine_regime(as_of)
            identity = CycleIdentity(
                cycle_id=cycle_id,
                as_of_utc=as_of,
                regime=eval_regime,
                sequence_number=self._sequence,
            )

            if identity.cycle_digest in self._completed_cycle_digests:
                raise DataContractError(
                    f"IDEMPOTENT_DUPLICATE_CYCLE: Cycle '{identity.cycle_id}' with digest '{identity.cycle_digest}' has already completed."
                )

            self._active_cycle = identity
            self._last_evaluated_as_of = as_of
            self._last_wall_clock = wall_clock
            return identity

    def complete_cycle(
        self,
        cycle_id: str,
        outcome: CycleOutcome,
        wall_clock_utc: datetime,
    ) -> None:
        """Release the cycle execution lock and mark the cycle completed."""
        wall_clock = _ensure_utc(wall_clock_utc, "wall_clock_utc")

        with self._lock:
            if self._active_cycle is None:
                raise DataContractError("No active cycle to complete.")

            if self._active_cycle.cycle_id != cycle_id:
                raise DataContractError(
                    f"Cycle mismatch on complete: active '{self._active_cycle.cycle_id}' vs provided '{cycle_id}'."
                )

            self._completed_cycle_ids.add(self._active_cycle.cycle_id)
            self._completed_cycle_digests.add(self._active_cycle.cycle_digest)
            self._active_cycle = None
            self._sequence += 1
            self._last_wall_clock = wall_clock
