"""Unit tests for Phase 14 Slice 2 immutable evidence records & evidence storage.

Covers:
- Evidence record creation with content identity = raw content hash.
- Cross-reference binding violations rejected (fail-closed).
- Record digest stability and timestamp sensitivity (content identity unaffected).
- Immutable in-memory store: idempotent storage, collision detection.
- Governance firewall: evidence records carry ZERO trading / hypothesis authority.
"""

from datetime import datetime, timezone
from typing import Callable, Dict, Optional

import pytest
from pydantic import ValidationError

from acash.research.ai.enums import EvidenceClassification
from acash.research.ai.retrieval.enums import RetrievalStatus
from acash.research.ai.retrieval.exceptions import (
    EvidenceStoreError,
    InvalidResultStateError,
    RetrievalError,
)
from acash.research.ai.retrieval.providers import (
    FixtureContent,
    FixtureSourceRetriever,
)
from acash.research.ai.retrieval.schema import (
    EvidenceRecord,
    RetrievalRequest,
    RetrievalResult,
    SourceDescriptor,
)
from acash.research.ai.retrieval.storage import InMemoryEvidenceStore


def _build_result(
    request: RetrievalRequest,
    source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    clock: Optional[Callable[[], datetime]] = None,
) -> RetrievalResult:
    if clock is None:
        clock = lambda: datetime(2026, 9, 7, 11, 22, 33, tzinfo=timezone.utc)
    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=clock)
    return provider.retrieve(request, source)


def _evidence(
    request: RetrievalRequest,
    source: SourceDescriptor,
    result: RetrievalResult,
    evidence_id: str = "EVID-0011223344556677",
    recorded_at_utc: str = "2026-09-07T11:30:00+00:00",
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source=source,
        request=request,
        result=result,
        recorded_at_utc=recorded_at_utc,
    )


def test_evidence_record_creation_and_content_identity(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)
    record = _evidence(retrieval_request, retrieval_source, result)
    assert record.result == result
    assert record.content_identity_sha256 == result.raw_content_sha256
    assert len(record.compute_record_digest()) == 64


def test_evidence_record_immutable_and_extra_forbidden(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)
    record = _evidence(retrieval_request, retrieval_source, result)
    with pytest.raises(ValidationError):
        record.recorded_at_utc = "2026-09-07T99:99:99"


def test_evidence_record_rejects_cross_reference_violations(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)

    other_source = retrieval_source.model_copy(update={"source_id": "SRC-ffee123412341234"})
    with pytest.raises(InvalidResultStateError):
        _evidence(retrieval_request, other_source, result)

    other_request = retrieval_request.model_copy(
        update={"request_id": "RET-REQ-ffffffffffffffff", "source_id": "SRC-ffee123412341234"}
    )
    with pytest.raises(InvalidResultStateError):
        _evidence(other_request, retrieval_source, result)

    mismatched_result = result.model_copy(update={"request_id": "RET-REQ-ffffffffffffffff"})
    with pytest.raises(InvalidResultStateError):
        _evidence(retrieval_request, retrieval_source, mismatched_result)


def test_evidence_record_forbids_model_copy_verified_escalation(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)
    assert result.epistemic_classification == EvidenceClassification.REPORTED

    # Exact live audit exploit: pydantic model_copy(update=...) bypasses the
    # RetrievalResult __init__ validator because validate=False is the default.
    escalated = result.model_copy(
        update={"epistemic_classification": EvidenceClassification.VERIFIED}
    )
    assert escalated.epistemic_classification == EvidenceClassification.VERIFIED

    # The EvidenceRecord construction boundary MUST fail closed on the escalation.
    with pytest.raises(RetrievalError):
        _evidence(retrieval_request, retrieval_source, escalated)


@pytest.mark.parametrize(
    ("forged_field", "forged_value"),
    [
        ("locator", "https://evil.example.com/planted.txt"),
        ("raw_content_sha256", "b" * 64),
        ("normalized_content_sha256", "c" * 64),
        ("content_bytes_observed", 424_242),
        ("http_status", 500),
        ("content_type_received", "application/json"),
        ("retrieval_status", RetrievalStatus.NOT_FOUND),
        ("requested_at_utc", "2026-09-07T00:00:00+00:00"),
    ],
)
def test_evidence_record_rejects_forged_provenance_pair_mismatch(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    forged_field: str,
    forged_value: object,
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)
    forged_provenance = result.provenance.model_copy(update={forged_field: forged_value})
    forged_result = result.model_copy(update={"provenance": forged_provenance})
    with pytest.raises(InvalidResultStateError):
        _evidence(retrieval_request, retrieval_source, forged_result)


def test_evidence_record_digest_stability_and_timestamp_sensitivity(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)
    record_a = _evidence(retrieval_request, retrieval_source, result, recorded_at_utc="2026-09-07T11:30:00+00:00")
    record_b = _evidence(retrieval_request, retrieval_source, result, recorded_at_utc="2026-09-07T11:31:00+00:00")

    assert record_a.compute_record_digest() == record_a.compute_record_digest()
    assert record_a.compute_record_digest() != record_b.compute_record_digest()
    # Content identity is timestamp-independent:
    assert record_a.content_identity_sha256 == record_b.content_identity_sha256


def test_in_memory_store_idempotent_store_and_load(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)
    record = _evidence(retrieval_request, retrieval_source, result)
    store = InMemoryEvidenceStore()

    ref1 = store.store(record)
    ref2 = store.store(record)
    assert ref1 == ref2 == f"evid:{record.evidence_id}"
    assert store.list_refs() == (ref1,)
    loaded = store.load(ref1)
    assert loaded == record
    assert loaded.compute_record_digest() == record.compute_record_digest()


def test_in_memory_store_collision_with_differing_digest_raises(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)
    store = InMemoryEvidenceStore()

    store.store(_evidence(retrieval_request, retrieval_source, result, recorded_at_utc="2026-09-07T11:30:00+00:00"))
    conflicting = _evidence(
        retrieval_request,
        retrieval_source,
        result,
        recorded_at_utc="2026-09-07T11:45:00+00:00",
    )
    with pytest.raises(EvidenceStoreError):
        store.store(conflicting)


def test_in_memory_store_load_missing_raises() -> None:
    store = InMemoryEvidenceStore()
    with pytest.raises(EvidenceStoreError):
        store.load("evid:does-not-exist")


def test_evidence_records_carry_zero_governance_authority(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    result = _build_result(retrieval_request, retrieval_source, fixture_catalog)
    record = _evidence(retrieval_request, retrieval_source, result)
    for forbidden in (
        "authorize_trading",
        "allocate_capital",
        "approve_hypothesis",
        "override_quarantine",
        "execute_backtest",
    ):
        assert not hasattr(record, forbidden)
        assert not hasattr(EvidenceRecord, forbidden)

    import acash.research.ai.retrieval as retrieval_pkg

    for forbidden_attr in (
        "authorize_trading",
        "allocate_capital",
        "approve_hypothesis",
        "execute_backtest",
        "create_hypothesis",
    ):
        assert not hasattr(retrieval_pkg, forbidden_attr)