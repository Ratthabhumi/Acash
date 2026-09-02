"""Sovereign domain exceptions for MetaTrader 5 (MT5) execution adapter."""

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

