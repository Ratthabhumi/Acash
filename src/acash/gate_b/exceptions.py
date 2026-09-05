"""Phase 13 Slice 2: Gate B Exception Hierarchy.

Defines fail-closed exception boundaries for Gate B dual-layer authorization,
cryptographic verification, transactional storage, and recovery operations.
"""

from acash.core.domain.exceptions import (
    DataContractError as DataContractError,
    DomainValidationError as DomainValidationError,
)


class GateBError(DomainValidationError):
    """Base exception for all Phase 13 Slice 2 Gate B failures."""


class PreLiveRiskAdmissionError(GateBError):
    """Raised when machine gate, quote freshness, or capital admission constraints fail."""


class CryptographicVerificationError(GateBError):
    """Raised when digital signatures, trust store resolution, or hash continuity checks fail."""


class StorageDurabilityError(GateBError, DataContractError):
    """Raised when filesystem durability barriers, atomic replacements, or CAS operations fail."""


class QuarantineError(GateBError, DataContractError):
    """Raised when consistency violations, unproven commits, or corrupted states enter quarantine."""


class GovernanceSecurityError(GateBError, DataContractError):
    """Raised when process tokens, OS privileges, or module search paths violate governance boundaries."""


class PreExecutionIntegrityError(GateBError, DataContractError):
    """Raised when pre-execution manifests, dependencies, or runtime environments fail attestation."""


__all__ = [
    "CryptographicVerificationError",
    "DataContractError",
    "DomainValidationError",
    "GateBError",
    "GovernanceSecurityError",
    "PreExecutionIntegrityError",
    "PreLiveRiskAdmissionError",
    "QuarantineError",
    "StorageDurabilityError",
]

