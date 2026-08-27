"""Decision ledger abstract interface contract."""

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from acash.core.domain.audit import DecisionRecord


class IDecisionLedger(ABC):
    """Abstract interface contract for append-only audit ledger and research memory."""

    @abstractmethod
    def append_decision(self, record: DecisionRecord) -> str:
        """Append an immutable decision record to the ledger. Returns decision_id."""
        pass

    @abstractmethod
    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Retrieve a specific decision record by unique decision_id."""
        pass

    @abstractmethod
    def query_by_correlation_id(self, correlation_id: str) -> Sequence[DecisionRecord]:
        """Query decision records associated with a correlation_id."""
        pass
