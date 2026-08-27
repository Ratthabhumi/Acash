"""In-memory append-only decision ledger adapter."""

from typing import Optional, Sequence

from acash.core.domain.audit import DecisionRecord
from acash.core.domain.exceptions import LedgerTamperError
from acash.core.interfaces.ledger import IDecisionLedger


class InMemoryDecisionLedger(IDecisionLedger):
    """In-memory append-only decision ledger enforcing record immutability."""

    def __init__(self) -> None:
        self._records: dict[str, DecisionRecord] = {}
        self._order: list[str] = []

    def append_decision(self, record: DecisionRecord) -> str:
        """Append an immutable decision record. Rejects overwrite attempts."""
        if record.decision_id in self._records:
            raise LedgerTamperError(
                f"Cannot overwrite decision {record.decision_id}: DecisionRecord is strictly append-only."
            )
        self._records[record.decision_id] = record
        self._order.append(record.decision_id)
        return record.decision_id

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Retrieve a decision record by decision_id."""
        return self._records.get(decision_id)

    def query_by_correlation_id(self, correlation_id: str) -> Sequence[DecisionRecord]:
        """Retrieve all decision records associated with a correlation_id in chronological order."""
        return [
            self._records[did] for did in self._order
            if self._records[did].correlation_id == correlation_id
        ]

    def all_records(self) -> Sequence[DecisionRecord]:
        """Retrieve all records in the ledger."""
        return [self._records[did] for did in self._order]
