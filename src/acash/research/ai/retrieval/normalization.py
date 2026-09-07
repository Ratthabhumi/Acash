"""Deterministic content normalization & content hashing policy.

Canonical content identity = SHA-256 over the EXACT received bytes. This delegates to
the repository's single raw-bytes hash authority ``calculate_raw_source_sha256`` in
``acash.data.provenance`` (no duplicate/divergent hashing helper is introduced).

Normalization (when applicable) is byte-for-byte deterministic:
- NONE: no normalization; only the RAW content hash is meaningful.
- UTF8_LINE_ENDINGS: strict UTF-8 decode + CRLF/CR -> LF + UTF-8 re-encode.

RAW content hash and NORMALIZED content hash are always kept distinct.
"""

from typing import Optional

from acash.data.provenance import calculate_raw_source_sha256
from acash.research.ai.retrieval.enums import NormalizationPolicy

NORMALIZABLE_EXACT_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/json",
        "application/xml",
        "application/yaml",
        "application/x-yaml",
    }
)

NORMALIZABLE_TRAILING_SUFFIXES: tuple[str, ...] = ("+json", "+xml", "+yaml", "+text")

TEXT_CONTENT_TYPE_PREFIX: str = "text/"


def normalize_text_content(raw: bytes) -> Optional[bytes]:
    """Deterministically normalize UTF-8 textual content (CRLF/CR -> LF) or return None.

    Returns ``None`` when the bytes cannot be strictly decoded as UTF-8, which the
    retrieval providers surface as an explicit ``PARSE_ERROR`` for declared-text content.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.encode("utf-8")


def is_normalizable_content_type(content_type: Optional[str]) -> bool:
    """Return whether a declared content-type is eligible for textual normalization."""
    if not content_type:
        return False
    base = content_type.split(";")[0].strip().lower()
    if base.startswith(TEXT_CONTENT_TYPE_PREFIX):
        return True
    if base in NORMALIZABLE_EXACT_CONTENT_TYPES:
        return True
    return any(base.endswith(suffix) for suffix in NORMALIZABLE_TRAILING_SUFFIXES)


def compute_raw_content_sha256(raw: bytes) -> str:
    """SHA-256 over the exact received bytes (canonical repository authority)."""
    return calculate_raw_source_sha256(raw)


def compute_normalized_content_sha256(
    raw: bytes,
    content_type: Optional[str],
) -> Optional[str]:
    """SHA-256 over normalized content, or None when content is not normalizable.

    The caller distinguishes "not eligible" (None) from "decode failure". Decode
    failure of declared-text content is surfaced as an explicit PARSE_ERROR by the
    retrieval providers rather than silently returning a raw-only hash.
    """
    if not is_normalizable_content_type(content_type):
        return None
    normalized = normalize_text_content(raw)
    if normalized is None:
        return None
    return compute_raw_content_sha256(normalized)


def content_type_accepted(returned_content_type: str, accepted: tuple[str, ...]) -> bool:
    """Deterministic content-type acceptance matching.

    Accepted patterns may be exact types ("text/plain"), wildcard category
    ("text/*"), or the universal wildcard ("*/*"). Comparison is case-insensitive
    and ignores content-type parameters.
    """
    base = returned_content_type.split(";")[0].strip().lower()
    for candidate in accepted:
        pattern = candidate.strip().lower()
        if pattern == "*/*" or pattern == base:
            return True
        if pattern.endswith("/*") and base.startswith(pattern[:-1]):
            return True
    return False