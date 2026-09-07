"""Unit tests for Phase 14 Slice 2 deterministic content normalization & hashing.

Covers:
- RAW vs NORMALIZED hash separation (never conflated).
- Deterministic golden hashing values.
- Strict UTF-8 policy: decode failures surface explicitly (None), never silently stored.
- Content-type acceptance wildcard matching.
"""

from typing import Optional

import pytest

from acash.research.ai.retrieval.normalization import (
    compute_normalized_content_sha256,
    compute_raw_content_sha256,
    content_type_accepted,
    is_normalizable_content_type,
    normalize_text_content,
)
from acash.data.provenance import calculate_raw_source_sha256


def test_raw_sha256_deterministic_and_single_canonical_authority() -> None:
    body = b"line one\r\nline two\r\n"
    ours = compute_raw_content_sha256(body)
    assert ours == compute_raw_content_sha256(body)
    assert ours == calculate_raw_source_sha256(body)
    assert len(ours) == 64


def test_raw_and_normalized_hashes_are_distinct_for_crlf_content() -> None:
    body = b"line one\r\nline two\r\n"
    raw = compute_raw_content_sha256(body)
    normalized = compute_normalized_content_sha256(body, "text/plain")
    assert normalized is not None
    assert raw != normalized
    assert normalized == compute_raw_content_sha256(b"line one\nline two\n")


def test_normalization_golden_reference() -> None:
    assert normalize_text_content(b"a\r\nb\r") == b"a\nb\n"
    assert normalize_text_content(b"a\r\nb\n") == b"a\nb\n"
    assert normalize_text_content(b"plain") == b"plain"


def test_non_normalizable_content_type_has_no_normalized_hash() -> None:
    body = b"\x00\x01\x02binary"
    assert compute_normalized_content_sha256(body, "application/octet-stream") is None
    assert compute_normalized_content_sha256(body, None) is None


def test_normalize_text_content_returns_none_on_invalid_utf8() -> None:
    assert normalize_text_content(b"\xff\xfe\x00invalid") is None


def test_normalization_eligibility_classification() -> None:
    assert is_normalizable_content_type("text/plain")
    assert is_normalizable_content_type("Text/HTML; charset=utf-8")
    assert is_normalizable_content_type("application/json")
    assert is_normalizable_content_type("application/json; charset=utf-8")
    assert is_normalizable_content_type("application/vnd.api+json")
    assert is_normalizable_content_type("application/atom+xml")
    assert not is_normalizable_content_type("application/octet-stream")
    assert not is_normalizable_content_type(None)
    assert not is_normalizable_content_type("image/png")


def test_content_type_accepted_wildcard_matching() -> None:
    assert content_type_accepted("text/plain", ("text/plain",))
    assert content_type_accepted("text/plain", ("text/*",))
    assert content_type_accepted("text/html", ("text/*",))
    assert content_type_accepted("application/json", ("*/*",))
    assert content_type_accepted("TEXT/PLAIN; charset=utf-8", ("text/plain",))
    assert not content_type_accepted("application/octet-stream", ("text/*",))
    assert not content_type_accepted("text/plain", ("application/json",))


def test_normalized_hash_matches_request_policy_composition() -> None:
    body = b"hello\r\nworld"
    raw = compute_raw_content_sha256(body)
    normalized: Optional[bytes] = normalize_text_content(body)
    assert normalized is not None
    assert compute_raw_content_sha256(normalized) == compute_raw_content_sha256(b"hello\nworld")
    assert raw != compute_raw_content_sha256(normalized)