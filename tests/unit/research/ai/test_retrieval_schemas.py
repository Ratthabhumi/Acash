"""Unit tests for Phase 14 Slice 2 retrieval schema contracts.

Covers:
- Immutability and extra-field rejection of source identity / request / result / evidence.
- Identifier pattern enforcement.
- Deterministic serialization and canonical digest stability.
- Epistemic boundary: retrieval can NEVER be classified VERIFIED.
- Fail-closed SUCCESS result invariants and failure-result invariants.
"""

from typing import Any, Dict

import pytest
from pydantic import ValidationError

from acash.research.ai.enums import EvidenceClassification, SourceType
from acash.research.ai.retrieval.enums import (
    NormalizationPolicy,
    RetrievalMode,
    RetrievalStatus,
)
from acash.research.ai.retrieval.exceptions import (
    InvalidResultStateError,
    RetrievalError,
)
from acash.research.ai.retrieval.schema import (
    RetrievalRequest,
    RetrievalResult,
    SourceDescriptor,
    SourceRetrievalPolicy,
    utc_now_iso,
)


def test_utc_now_iso_is_deterministic_format() -> None:
    stamp = utc_now_iso()
    assert isinstance(stamp, str)
    assert "T" in stamp
    assert stamp.endswith("+00:00")


def test_source_descriptor_immutable_and_extra_forbidden(retrieval_source: SourceDescriptor) -> None:
    assert retrieval_source.source_id == "SRC-0011223344556677"
    with pytest.raises(ValidationError):
        retrieval_source.locator = "mutated://locator"
    with pytest.raises(ValidationError):
        SourceDescriptor(
            source_id="SRC-0011223344556677",
            locator="https://fixture.example.com/paper.txt",
            source_type=SourceType.ACADEMIC,
            recorded_at_utc="2026-09-06T00:00:00+00:00",
            unauthorized_field="malicious_payload",  # type: ignore[call-arg]
        )


def test_source_and_request_identifier_patterns_enforced() -> None:
    with pytest.raises(ValidationError):
        SourceDescriptor(
            source_id="NOT-A-VALID-ID",
            locator="https://example.com",
            source_type=SourceType.ACADEMIC,
            recorded_at_utc="2026-09-06T00:00:00+00:00",
        )
    with pytest.raises(ValidationError):
        RetrievalRequest(
            request_id="bad",
            source_id="SRC-0011223344556677",
            locator="https://fixture.example.com/paper.txt",
            timeout_seconds=10.0,
            max_content_bytes=1000,
            accepted_content_types=("text/plain",),
            created_at_utc="2026-09-07T11:00:00+00:00",
        )


def test_source_descriptor_deterministic_serialization_and_digest(
    retrieval_source: SourceDescriptor,
) -> None:
    dump1 = retrieval_source.model_dump_json()
    dump2 = retrieval_source.model_dump_json()
    assert dump1 == dump2
    assert retrieval_source.compute_canonical_digest() == retrieval_source.compute_canonical_digest()
    assert len(retrieval_source.compute_canonical_digest()) == 64

    rebuilt = SourceDescriptor.model_validate_json(dump1)
    assert rebuilt == retrieval_source
    assert rebuilt.compute_canonical_digest() == retrieval_source.compute_canonical_digest()


def test_request_deterministic_serialization_and_digest(
    retrieval_request: RetrievalRequest,
) -> None:
    d1 = retrieval_request.compute_canonical_digest()
    d2 = retrieval_request.compute_canonical_digest()
    assert d1 == d2
    assert len(d1) == 64
    dump1 = retrieval_request.model_dump_json()
    dump2 = RetrievalRequest.model_validate_json(dump1)
    assert dump2 == retrieval_request
    assert dump2.compute_canonical_digest() == d1


def test_request_rejects_zero_or_negative_constraints() -> None:
    with pytest.raises(ValidationError):
        RetrievalRequest(
            request_id="RET-REQ-0011223344556677",
            source_id="SRC-0011223344556677",
            locator="https://fixture.example.com/paper.txt",
            timeout_seconds=0.0,
            max_content_bytes=1,
            accepted_content_types=("text/plain",),
            created_at_utc="2026-09-07T11:00:00+00:00",
        )
    with pytest.raises(ValidationError):
        RetrievalRequest(
            request_id="RET-REQ-0011223344556677",
            source_id="SRC-0011223344556677",
            locator="https://fixture.example.com/paper.txt",
            timeout_seconds=1.0,
            max_content_bytes=0,
            accepted_content_types=("text/plain",),
            created_at_utc="2026-09-07T11:00:00+00:00",
        )


def test_result_defaults_to_reported_and_forbids_verified(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
) -> None:
    from acash.research.ai.retrieval.providers import FixtureContent, FixtureSourceRetriever

    provider = FixtureSourceRetriever(
        catalog={"https://fixture.example.com/paper.txt": FixtureContent(body=b"ok", content_type="text/plain")},
    )
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert isinstance(result.epistemic_classification, EvidenceClassification)
    assert result.epistemic_classification == EvidenceClassification.REPORTED

    forbidden: Dict[str, Any] = {
        "result_id": "RET-RES-0011223344556677",
        "request_id": retrieval_request.request_id,
        "source_id": retrieval_request.source_id,
        "retrieval_status": RetrievalStatus.SUCCESS,
        "retrieved_at_utc": "2026-09-07T11:22:33+00:00",
        "http_status": 200,
        "returned_content_type": "text/plain",
        "content_length_bytes": 2,
        "raw_content_sha256": "a" * 64,
        "normalization_policy": NormalizationPolicy.NONE,
        "raw_content_ref": "ref:hash",
        "provenance": result.provenance,
        "epistemic_classification": EvidenceClassification.VERIFIED,
    }
    with pytest.raises(RetrievalError):
        RetrievalResult(**forbidden)


def test_success_result_requires_hash_positive_length_and_ref(
    retrieval_request: RetrievalRequest,
) -> None:
    with pytest.raises(InvalidResultStateError):
        RetrievalResult(
            result_id="RET-RES-0011223344556677",
            request_id=retrieval_request.request_id,
            source_id=retrieval_request.source_id,
            retrieval_status=RetrievalStatus.SUCCESS,
            retrieved_at_utc="2026-09-07T11:22:33+00:00",
            http_status=200,
            returned_content_type="text/plain",
            content_length_bytes=0,
            raw_content_sha256=None,
            normalization_policy=NormalizationPolicy.NONE,
            raw_content_ref=None,
            provenance=_dummy_provenance(),
        )


def _dummy_provenance() -> Any:
    from acash.research.ai.retrieval.enums import RetrievalMode
    from acash.research.ai.retrieval.schema import RetrievalProvenance

    return RetrievalProvenance(
        source_id="SRC-0011223344556677",
        locator="https://fixture.example.com/paper.txt",
        provider_id="fixture.deterministic.v1",
        requested_at_utc="2026-09-07T11:00:00+00:00",
        retrieved_at_utc="2026-09-07T11:22:33+00:00",
        http_status=200,
        content_type_received="text/plain",
        content_bytes_observed=0,
        raw_content_sha256=None,
        normalized_content_sha256=None,
        normalization_policy=NormalizationPolicy.NONE,
        retrieval_mode=RetrievalMode.FULL,
        retrieval_status=RetrievalStatus.SUCCESS,
        content_ref="NONE_CONTENT",
    )


def test_normalized_hash_requires_non_none_policy(
    retrieval_request: RetrievalRequest,
) -> None:
    from acash.research.ai.retrieval.schema import RetrievalProvenance

    provenance = RetrievalProvenance(
        source_id=retrieval_request.source_id,
        locator=retrieval_request.locator,
        provider_id="fixture.deterministic.v1",
        requested_at_utc=retrieval_request.created_at_utc,
        retrieved_at_utc="2026-09-07T11:22:33+00:00",
        content_bytes_observed=0,
        raw_content_sha256=None,
        normalization_policy=NormalizationPolicy.NONE,
        retrieval_mode=RetrievalMode.FULL,
        retrieval_status=RetrievalStatus.NOT_FOUND,
        content_ref="NONE_CONTENT",
    )
    with pytest.raises(InvalidResultStateError):
        RetrievalResult(
            result_id="RET-RES-0011223344556677",
            request_id=retrieval_request.request_id,
            source_id=retrieval_request.source_id,
            retrieval_status=RetrievalStatus.NOT_FOUND,
            retrieved_at_utc="2026-09-07T11:22:33+00:00",
            content_length_bytes=0,
            normalization_policy=NormalizationPolicy.NONE,
            normalized_content_sha256="a" * 64,
            raw_content_ref=None,
            provenance=provenance,
        )


def test_provenance_is_explicit_and_complete(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, Any],
    fixed_clock: Any,
) -> None:
    from acash.research.ai.retrieval.providers import FixtureSourceRetriever

    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    provenance = result.provenance

    # The eight audit dimensions must all be present and cross-consistent.
    assert provenance.source_id == retrieval_source.source_id
    assert provenance.locator == retrieval_request.locator
    assert provenance.provider_id == "fixture.deterministic.v1"
    assert provenance.requested_at_utc == retrieval_request.created_at_utc
    assert provenance.retrieved_at_utc == result.retrieved_at_utc
    assert provenance.http_status == 200
    assert provenance.content_type_received == "text/plain"
    assert provenance.content_bytes_observed == len(b"line one\r\nline two\r\n")
    assert provenance.raw_content_sha256 == result.raw_content_sha256
    assert provenance.normalized_content_sha256 == result.normalized_content_sha256
    assert provenance.normalization_policy == NormalizationPolicy.UTF8_LINE_ENDINGS
    assert provenance.retrieval_status == RetrievalStatus.SUCCESS
    assert provenance.content_ref == result.raw_content_ref


def test_failure_result_invariants_without_content(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
) -> None:
    from acash.research.ai.retrieval.providers import FixtureContent, FixtureSourceRetriever
    from acash.research.ai.retrieval.schema import RetrievalProvenance

    provider = FixtureSourceRetriever(
        catalog={},
        clock=lambda: _fixed_dt(),
    )
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.NOT_FOUND
    assert result.content_length_bytes == 0
    assert result.raw_content_sha256 is None
    assert result.raw_content_ref is None
    assert result.http_status == 404
    assert isinstance(result.provenance, RetrievalProvenance)
    assert result.provenance.content_bytes_observed == 0
    assert result.compute_canonical_digest() == result.compute_canonical_digest()


def _fixed_dt() -> Any:
    from datetime import datetime, timezone

    return datetime(2026, 9, 7, 11, 22, 33, tzinfo=timezone.utc)


def test_source_retrieval_policy_digest_deterministic() -> None:
    policy = SourceRetrievalPolicy(
        preferred_timeout_seconds=15.0,
        declared_max_content_bytes=1_000_000,
        declared_content_types=("text/plain",),
        notes=("cached mirror",),
    )
    assert policy.compute_canonical_digest() == policy.compute_canonical_digest()
    assert len(policy.compute_canonical_digest()) == 64