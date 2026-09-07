"""Phase 14 Slice 2 Retrieval Layer Domain Exceptions.

All exceptions inherit from ResearchAiError (which inherits DataContractError),
preserving the repository-wide strict fail-closed contract.
"""

from acash.research.ai.exceptions import ResearchAiError


class RetrievalError(ResearchAiError):
    """Base error for the Phase 14 Slice 2 source retrieval layer."""


class UnknownProviderError(RetrievalError):
    """Raised when a source_id has no registered descriptor/provider binding."""


class ProviderMisconfigurationError(RetrievalError):
    """Raised when a provider returns output inconsistent with the fail-closed contract."""


class EvidenceStoreError(RetrievalError):
    """Raised when an evidence record cannot be persisted or loaded."""


class InvalidResultStateError(RetrievalError):
    """Raised when a retrieval result violates internal consistency invariants."""