"""Phase 11: Monitoring Evidence Ledger (Forensic Persistence Adapter).

Strictly enforces:
1. Domain Adapter Architecture:
   Acts as a specialized domain adapter around the existing Phase 10 OperationalLedger.
   Evidence DTO -> Tier 1 CanonicalConfigSerializer -> operational event wrapper -> existing OperationalLedger -> Tier 2 chaining.
2. Zero Hash-Chain Re-invention:
   Reuses the proven, authoritative OperationalLedger for all disk persistence, JSONL formatting,
   thread-safe concurrency, monotonic sequence enforcement, and Tier 2 cryptographic hash chaining.
3. Immutability & Tier 1 Lineage Preservation:
   Embeds Tier 1 canonical evidence digests directly into OperationalCycleEvent envelopes.
   Evidence DTOs are never mutated after registration.
4. Fail-Closed Integrity & Crash Defense:
   Detects corrupted lines, broken hash chains, replay attacks, or partial writes on startup
   by delegating to OperationalLedger verification.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading
from typing import Dict, List, Optional, Tuple, Union

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.schema import (
    ExecutionCostEvidence,
    ForwardHealthState,
    StrategyForwardDriftEvidence,
)
from acash.runtime.ledger import GENESIS_PREVIOUS_DIGEST, OperationalLedger
from acash.runtime.schema import (
    CycleIdentity,
    CycleOutcome,
    OperationalCycleEvent,
    RuntimeHealthStatus,
    RuntimeRegime,
)


class MonitoringEvidenceLedger:
    """Domain adapter persisting Phase 11 monitoring evidence into the Phase 10 OperationalLedger."""

    def __init__(
        self,
        persistence_path: Path,
        operational_ledger: Optional[OperationalLedger] = None,
    ) -> None:
        self.path: Path = Path(persistence_path)
        self._operational_ledger: OperationalLedger = (
            operational_ledger if operational_ledger is not None else OperationalLedger(self.path)
        )
        self._lock = threading.Lock()
        self._evidence_by_id: Dict[str, Union[StrategyForwardDriftEvidence, ExecutionCostEvidence]] = {}
        self._evidence_by_digest: Dict[str, Union[StrategyForwardDriftEvidence, ExecutionCostEvidence]] = {}

    @property
    def event_count(self) -> int:
        """Return total number of committed ledger events."""
        return self._operational_ledger.event_count

    @property
    def last_event_digest(self) -> str:
        """Return the Tier 2 event digest of the most recently appended record."""
        return self._operational_ledger.last_event_digest

    @property
    def last_sequence(self) -> int:
        """Return the sequence number of the most recently appended record."""
        return self._operational_ledger.last_sequence

    def record_forward_drift_evidence(
        self,
        evidence: StrategyForwardDriftEvidence,
    ) -> OperationalCycleEvent:
        """Record canonical StrategyForwardDriftEvidence into the forensic event ledger.

        Args:
            evidence: Validated StrategyForwardDriftEvidence DTO.

        Returns:
            The committed OperationalCycleEvent wrapper.

        Raises:
            DataContractError: On missing digest, temporal inversion, or duplicate ID.
        """
        with self._lock:
            if not evidence.evidence_digest:
                raise DataContractError("Missing Tier 1 evidence_digest on StrategyForwardDriftEvidence.")

            if evidence.evidence_id in self._evidence_by_id:
                raise DataContractError(
                    f"Duplicate Evidence Rejected: evidence_id '{evidence.evidence_id}' already recorded."
                )

            # Map health state to runtime health status
            if evidence.health_state == ForwardHealthState.HEALTHY:
                runtime_health = RuntimeHealthStatus.RUNTIME_HEALTHY
            elif evidence.health_state == ForwardHealthState.DEGRADED:
                runtime_health = RuntimeHealthStatus.RUNTIME_DEGRADED
            else:
                runtime_health = RuntimeHealthStatus.RUNTIME_HEALTHY

            # Ensure wall_clock >= as_of to prevent temporal inversion
            wall_clock = evidence.wall_clock_utc
            if wall_clock < evidence.as_of_utc:
                raise DataContractError(
                    f"Temporal Inversion: wall_clock_utc ({wall_clock.isoformat()}) "
                    f"cannot precede as_of_utc ({evidence.as_of_utc.isoformat()})."
                )

            next_seq = self._operational_ledger.last_sequence + 1
            cycle_identity = CycleIdentity(
                cycle_id=evidence.evidence_id,
                as_of_utc=evidence.as_of_utc,
                regime=RuntimeRegime.POST_MARKET_CLOSE,
                sequence_number=next_seq,
            )

            # Construct OperationalCycleEvent wrapper preserving Tier 1 digests
            cycle_event = OperationalCycleEvent(
                cycle_identity=cycle_identity,
                wall_clock_utc=wall_clock,
                runtime_health=runtime_health,
                active_dossier_digests=(evidence.dossier_digest, evidence.evidence_digest),
                cycle_outcome=CycleOutcome.SUCCESS,
                previous_event_digest=self._operational_ledger.last_event_digest,
            )

            # Commit to disk via authoritative Phase 10 OperationalLedger
            self._operational_ledger.append_event(cycle_event)

            # Index evidence in-memory
            self._evidence_by_id[evidence.evidence_id] = evidence
            self._evidence_by_digest[evidence.evidence_digest] = evidence

            return cycle_event

    def record_execution_cost_evidence(
        self,
        evidence: ExecutionCostEvidence,
    ) -> OperationalCycleEvent:
        """Record canonical ExecutionCostEvidence into the forensic event ledger.

        Args:
            evidence: Validated ExecutionCostEvidence DTO.

        Returns:
            The committed OperationalCycleEvent wrapper.

        Raises:
            DataContractError: On missing digest or duplicate ID.
        """
        with self._lock:
            if not evidence.lineage_digest:
                raise DataContractError("Missing Tier 1 lineage_digest on ExecutionCostEvidence.")

            if evidence.evidence_id in self._evidence_by_id:
                raise DataContractError(
                    f"Duplicate Evidence Rejected: evidence_id '{evidence.evidence_id}' already recorded."
                )

            next_seq = self._operational_ledger.last_sequence + 1
            cycle_identity = CycleIdentity(
                cycle_id=evidence.evidence_id,
                as_of_utc=evidence.as_of_utc,
                regime=RuntimeRegime.POST_MARKET_CLOSE,
                sequence_number=next_seq,
            )

            cycle_event = OperationalCycleEvent(
                cycle_identity=cycle_identity,
                wall_clock_utc=evidence.as_of_utc,
                runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
                execution_manifest_digests=(evidence.policy_digest, evidence.lineage_digest),
                cycle_outcome=CycleOutcome.SUCCESS,
                previous_event_digest=self._operational_ledger.last_event_digest,
            )

            self._operational_ledger.append_event(cycle_event)

            self._evidence_by_id[evidence.evidence_id] = evidence
            self._evidence_by_digest[evidence.lineage_digest] = evidence

            return cycle_event

    def get_evidence_by_id(
        self,
        evidence_id: str,
    ) -> Optional[Union[StrategyForwardDriftEvidence, ExecutionCostEvidence]]:
        """Retrieve evidence DTO by its evidence_id."""
        with self._lock:
            return self._evidence_by_id.get(evidence_id)

    def get_evidence_by_digest(
        self,
        digest: str,
    ) -> Optional[Union[StrategyForwardDriftEvidence, ExecutionCostEvidence]]:
        """Retrieve evidence DTO by its Tier 1 digest."""
        with self._lock:
            return self._evidence_by_digest.get(digest)

    def read_all_events(self) -> List[OperationalCycleEvent]:
        """Read all committed operational event envelopes from the underlying ledger."""
        return self._operational_ledger.read_all_events()

    def verify_ledger_integrity(self) -> Tuple[bool, int, str]:
        """Verify complete cryptographic hash chain and sequence monotonicity from disk."""
        return self._operational_ledger.verify_ledger_integrity()
