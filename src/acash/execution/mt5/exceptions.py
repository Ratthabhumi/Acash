from typing import Optional

from acash.core.domain.exceptions import DomainValidationError

class MT5DomainError(DomainValidationError):
    """Base exception for all MT5 execution domain errors."""


class MT5ValidationError(MT5DomainError):
    """Raised when MT5 schema, range, or parameter contract validation fails."""


class MT5NormalizationError(MT5DomainError):
    """Raised when raw MT5 vendor responses cannot be deterministically normalized."""


class MT5RetcodeError(MT5DomainError):
    """Raised on unmapped, invalid, or unrecognized MQL5 trade return codes."""


class MT5FillingModeError(MT5DomainError):
    """Raised when an invalid filling mode is requested or conflicts with the filling policy matrix."""


class MT5SymbolSpecError(MT5DomainError):
    """Raised on malformed, non-positive, or inconsistent symbol specifications."""


class MT5TransportError(MT5DomainError):
    """Raised on low-level transport, IPC, or network communication failures."""

    def __init__(
        self,
        message: str,
        api_code: Optional[int] = None,
        is_timeout: bool = False,
    ) -> None:
        super().__init__(message)
        self.api_code = api_code
        self.is_timeout = is_timeout


class MT5ReconciliationError(MT5DomainError):
    """Raised when critical 6-D reconciliation discrepancies prevent dispatch."""


class ReconciliationIntegrityError(MT5DomainError):
    """Raised when reconciliation digests or cryptographic lineage proof are tampered or mismatched."""



