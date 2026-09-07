"""Phase 14 Slice 2 Retrieval Layer Enums.

Defines:
- RetrievalStatus: exhaustive, mutually exclusive retrieval outcome classification.
- RetrievalMode: full vs conditional retrieval.
- NormalizationPolicy: deterministic content normalization identifiers.
"""

from enum import Enum


class RetrievalStatus(str, Enum):
    """Exhaustive retrieval outcome classification.

    Failures are NEVER collapsed into a generic ERROR; each outcome category is
    explicit and mutually exclusive.
    """

    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    NOT_MODIFIED = "NOT_MODIFIED"
    TIMEOUT = "TIMEOUT"
    HTTP_ERROR = "HTTP_ERROR"
    CONTENT_TYPE_REJECTED = "CONTENT_TYPE_REJECTED"
    SIZE_LIMIT_EXCEEDED = "SIZE_LIMIT_EXCEEDED"
    PARSE_ERROR = "PARSE_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class RetrievalMode(str, Enum):
    """Retrieval mode. CONDITIONAL uses conditional request metadata (ETag / Last-Modified)."""

    FULL = "FULL"
    CONDITIONAL = "CONDITIONAL"


class NormalizationPolicy(str, Enum):
    """Deterministic normalization policy applied to content, when any.

    NONE: content stored verbatim; only the RAW content hash exists.
    UTF8_LINE_ENDINGS: strict UTF-8 decode + CRLF/CR -> LF normalization, re-encoded UTF-8.
    """

    NONE = "NONE"
    UTF8_LINE_ENDINGS = "UTF8_LINE_ENDINGS"