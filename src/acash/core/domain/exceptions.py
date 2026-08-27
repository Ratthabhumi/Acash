"""Sovereign domain exceptions for ACASH."""


class DomainError(Exception):
    """Base exception for all ACASH domain errors."""
    pass


class DomainValidationError(DomainError):
    """Raised when domain field validation fails (e.g. invalid bounds, non-finite values)."""
    pass


class InvariantViolationError(DomainError):
    """Raised when an architectural or accounting invariant is violated."""
    pass


class LedgerTamperError(DomainError):
    """Raised when an attempt is made to mutate or delete append-only ledger records."""
    pass


class ConfigError(DomainError):
    """Base exception for configuration errors."""
    pass


class ConfigParseError(ConfigError):
    """Raised when YAML configuration parsing fails due to malformed syntax."""
    pass
