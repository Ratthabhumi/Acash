"""Structured JSON logger with automatic credential redaction."""

import logging
import sys
from typing import Any, MutableMapping, cast
import structlog

REDACTED_KEYS = {
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "private_key",
    "access_token",
    "auth_token",
    "secret_key",
}


def secret_redaction_processor(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Structlog processor that recursively redacts sensitive credentials."""
    for key, value in list(event_dict.items()):
        if any(sensitive in key.lower() for sensitive in REDACTED_KEYS):
            event_dict[key] = "[REDACTED]"
        elif isinstance(value, dict):
            event_dict[key] = dict(secret_redaction_processor(logger, method_name, dict(value)))
    return event_dict


def configure_logging(
    json_format: bool = True,
    log_level: str = "INFO",
    redact_secrets: bool = True
) -> None:
    """Configure structured logging pipeline with optional JSON renderer and secret redaction."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_logger_name,
    ]

    if redact_secrets:
        processors.append(secret_redaction_processor)

    processors.append(structlog.processors.StackInfoRenderer())
    processors.append(structlog.processors.format_exc_info)

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "acash") -> structlog.stdlib.BoundLogger:
    """Obtain a structured bound logger instance."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
