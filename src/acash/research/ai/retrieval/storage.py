"""Phase 14 Slice 2 Immutable Evidence Storage Interface.

Evidence records are immutable after creation. Storage of an evidence record never
mutates it; persistence ID collision with a differing digest fails closed.
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple

from acash.research.ai.retrieval.exceptions import EvidenceStoreError
from acash.research.ai.retrieval.schema import EvidenceRecord


class BaseEvidenceStore(ABC):
    """Interface for persisting and loading immutable evidence records."""

    @abstractmethod
    def store(self, record: EvidenceRecord) -> str:
        """Persist an evidence record; returns its evidence_ref. Idempotent when identical."""

    @abstractmethod
    def load(self, evidence_ref: str) -> EvidenceRecord:
        """Load an evidence record by its evidence_ref; raises EvidenceStoreError when absent."""

    @abstractmethod
    def list_refs(self) -> Tuple[str, ...]:
        """Return all stored evidence refs in deterministic order."""


class InMemoryEvidenceStore(BaseEvidenceStore):
    """Deterministic in-memory evidence store for unit tests and offline use."""

    def __init__(self) -> None:
        self._records: Dict[str, EvidenceRecord] = {}

    def store(self, record: EvidenceRecord) -> str:
        ref = f"evid:{record.evidence_id}"
        existing = self._records.get(ref)
        if existing is not None:
            if existing.compute_record_digest() != record.compute_record_digest():
                raise EvidenceStoreError(
                    f"Evidence collision at '{ref}': identical evidence_id with a differing "
                    f"record digest. Immutable records must not be overwritten."
                )
            return ref
        self._records[ref] = record
        return ref

    def load(self, evidence_ref: str) -> EvidenceRecord:
        record = self._records.get(evidence_ref)
        if record is None:
            raise EvidenceStoreError(f"No evidence record at '{evidence_ref}'.")
        return record

    def list_refs(self) -> Tuple[str, ...]:
        return tuple(sorted(self._records.keys()))