"""Phase 14 AI Research Intelligence Domain Exceptions.

All exceptions inherit from DataContractError to preserve the strict fail-closed contract.
"""

from acash.core.domain.exceptions import DataContractError


class ResearchAiError(DataContractError):
    """Base exception for all Phase 14 AI Research Intelligence errors."""


class QuarantineContaminationError(ResearchAiError):
    """Raised when a research candidate or proposal touches permanently quarantined data."""


class InvalidEvidenceRoleError(ResearchAiError):
    """Raised when an invalid or contradictory epistemic evidence role is assigned."""


class MissingProvenanceError(ResearchAiError):
    """Raised when mandatory cryptographic provenance or source metadata is absent."""


class UnauthorizedProposalTransitionError(ResearchAiError):
    """Raised when an unauthorized attempt to promote or register an AI proposal is detected."""
