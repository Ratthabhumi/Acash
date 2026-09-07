"""Unit tests for Phase 14 Slice 2 retrieval providers & the fail-closed registry.

The HTTP provider is ONLY exercised through ``httpx.MockTransport``: no real network
I/O is possible from these tests.

Covers:
- Deterministic fixture retrieval success + fixed-clock reproducibility.
- Explicit classification: NOT_FOUND / TIMEOUT / HTTP_ERROR / CONTENT_TYPE_REJECTED /
  SIZE_LIMIT_EXCEEDED / PARSE_ERROR / NOT_MODIFIED / PROVIDER_ERROR.
- Registry fail-closed behavior for unknown sources, unregistered providers,
  locator mismatches, and unbound provider outputs.
"""

from datetime import datetime
from typing import Any, Callable, Dict

import hashlib
import httpx
import pytest

from acash.research.ai.retrieval.enums import RetrievalMode, RetrievalStatus
from acash.research.ai.retrieval.exceptions import (
    ProviderMisconfigurationError,
    UnknownProviderError,
)
from acash.research.ai.retrieval.providers import (
    BaseSourceRetriever,
    FixtureContent,
    FixtureSourceRetriever,
    HttpSourceRetriever,
    SourceProviderRegistry,
)
from acash.research.ai.retrieval.schema import (
    RetrievalRequest,
    RetrievalResult,
    SourceDescriptor,
)


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


# ---------------------------------------------------------------------------
# Fixture provider paths
# ---------------------------------------------------------------------------


def test_fixture_provider_success_with_full_provenance(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    fixed_clock: Callable[[], datetime],
) -> None:
    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)

    assert result.retrieval_status == RetrievalStatus.SUCCESS
    assert result.http_status == 200
    assert result.raw_content_sha256 == _sha256(b"line one\r\nline two\r\n")
    assert result.normalized_content_sha256 == _sha256(b"line one\nline two\n")
    assert result.content_length_bytes == len(b"line one\r\nline two\r\n")
    assert result.raw_content_ref is not None
    assert result.provenance.provider_id == "fixture.deterministic.v1"
    assert result.provenance.retrieved_at_utc == "2026-09-07T11:22:33.000000+00:00"


def test_fixture_provider_deterministic_across_repeated_retrieval(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    fixed_clock: Callable[[], datetime],
) -> None:
    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    r1 = provider.retrieve(retrieval_request, retrieval_source)
    r2 = provider.retrieve(retrieval_request, retrieval_source)
    assert r1 == r2
    assert r1.raw_content_sha256 == r2.raw_content_sha256
    assert r1.result_id == r2.result_id
    assert r1.compute_canonical_digest() == r2.compute_canonical_digest()


def test_fixture_provider_retrieval_does_not_mutate_catalog(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    fixed_clock: Callable[[], datetime],
) -> None:
    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    before = fixture_catalog["https://fixture.example.com/paper.txt"].body
    provider.retrieve(retrieval_request, retrieval_source)
    assert fixture_catalog["https://fixture.example.com/paper.txt"].body == before


def test_fixture_provider_not_found_classification(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    provider = FixtureSourceRetriever(catalog={}, clock=fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.NOT_FOUND
    assert result.http_status == 404
    assert result.raw_content_ref is None
    assert result.content_length_bytes == 0


@pytest.mark.parametrize(
    ("override", "expected_status"),
    [
        (RetrievalStatus.TIMEOUT, RetrievalStatus.TIMEOUT),
        (RetrievalStatus.PROVIDER_ERROR, RetrievalStatus.PROVIDER_ERROR),
        (RetrievalStatus.HTTP_ERROR, RetrievalStatus.HTTP_ERROR),
        (RetrievalStatus.PARSE_ERROR, RetrievalStatus.PARSE_ERROR),
    ],
)
def test_fixture_provider_explicit_failure_classifications(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
    override: RetrievalStatus,
    expected_status: RetrievalStatus,
) -> None:
    provider = FixtureSourceRetriever(
        catalog={
            "https://fixture.example.com/paper.txt": FixtureContent(
                body=b"content",
                content_type="text/plain",
                http_status=200,
                status_override=override,
            ),
        },
        clock=fixed_clock,
    )
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == expected_status
    assert result.raw_content_ref is None
    assert result.content_length_bytes == 0


def test_fixture_provider_content_type_rejection(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    fixed_clock: Callable[[], datetime],
) -> None:
    strict_request = retrieval_request.model_copy(update={"accepted_content_types": ("application/json",)})
    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    result = provider.retrieve(strict_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.CONTENT_TYPE_REJECTED


def test_fixture_provider_size_limit_rejection(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    fixed_clock: Callable[[], datetime],
) -> None:
    tiny_request = retrieval_request.model_copy(update={"max_content_bytes": 10})
    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    result = provider.retrieve(tiny_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.SIZE_LIMIT_EXCEEDED
    assert result.content_length_bytes == 0


def test_fixture_provider_parse_error_on_invalid_utf8_text(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    provider = FixtureSourceRetriever(
        catalog={
            "https://fixture.example.com/paper.txt": FixtureContent(
                body=b"\xff\xfe\x00not-utf8",
                content_type="text/plain",
            ),
        },
        clock=fixed_clock,
    )
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.PARSE_ERROR
    assert result.raw_content_ref is None


def test_fixture_provider_conditional_mode_still_full_for_fixtures(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    fixed_clock: Callable[[], datetime],
) -> None:
    conditional = retrieval_request.model_copy(
        update={
            "mode": RetrievalMode.CONDITIONAL,
            "conditional_etag": '"abc"',
            "conditional_last_modified_utc": "2026-09-06T00:00:00+00:00",
        },
    )
    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    result = provider.retrieve(conditional, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.SUCCESS
    assert result.provenance.retrieval_mode == RetrievalMode.CONDITIONAL


# ---------------------------------------------------------------------------
# Registry fail-closed behavior
# ---------------------------------------------------------------------------


def test_registry_unknown_source_raises_unknown_provider(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    provider = FixtureSourceRetriever(catalog=fixture_catalog)
    registry = SourceProviderRegistry(
        providers={"fixture.deterministic.v1": provider},
        source_bindings={},
    )
    with pytest.raises(UnknownProviderError):
        registry.retrieve(retrieval_request)


def test_registry_unregistered_provider_raises_unknown_provider(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    provider = FixtureSourceRetriever(catalog=fixture_catalog)
    registry = SourceProviderRegistry(
        providers={},
        source_bindings={
            retrieval_source.source_id: ("fixture.deterministic.v1", retrieval_source),
        },
    )
    with pytest.raises(UnknownProviderError):
        registry.retrieve(retrieval_request)


def test_registry_locator_mismatch_raises_provider_misconfiguration(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
) -> None:
    provider = FixtureSourceRetriever(catalog=fixture_catalog)
    bogus_request = retrieval_request.model_copy(
        update={"locator": "https://evil.example.com/different.txt"}
    )
    registry = SourceProviderRegistry(
        providers={"fixture.deterministic.v1": provider},
        source_bindings={retrieval_source.source_id: ("fixture.deterministic.v1", retrieval_source)},
    )
    with pytest.raises(ProviderMisconfigurationError):
        registry.retrieve(bogus_request)


def test_registry_rejects_unbound_provider_output(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    fixed_clock: Callable[[], datetime],
) -> None:
    class LooseProvider(BaseSourceRetriever):
        provider_id = "loose.v1"

        def __init__(self, inner: BaseSourceRetriever) -> None:
            self._inner = inner

        def retrieve(self, request: RetrievalRequest, source: SourceDescriptor) -> RetrievalResult:
            different = request.model_copy(update={"request_id": "RET-REQ-ffffffffffffffff"})
            return self._inner.retrieve(different, source)

    inner = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    registry = SourceProviderRegistry(
        providers={"loose.v1": LooseProvider(inner)},
        source_bindings={retrieval_source.source_id: ("loose.v1", retrieval_source)},
    )
    with pytest.raises(ProviderMisconfigurationError):
        registry.retrieve(retrieval_request)


def test_registry_happy_path_resolves_via_source_binding(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixture_catalog: Dict[str, FixtureContent],
    fixed_clock: Callable[[], datetime],
) -> None:
    provider = FixtureSourceRetriever(catalog=fixture_catalog, clock=fixed_clock)
    registry = SourceProviderRegistry(
        providers={"fixture.deterministic.v1": provider},
        source_bindings={retrieval_source.source_id: ("fixture.deterministic.v1", retrieval_source)},
    )
    resolved = registry.resolve_source(retrieval_source.source_id)
    assert resolved == retrieval_source
    result = registry.retrieve(retrieval_request)
    assert result.retrieval_status == RetrievalStatus.SUCCESS
    assert result.request_id == retrieval_request.request_id


# ---------------------------------------------------------------------------
# HTTP provider classification (MockTransport only — zero real network)
# ---------------------------------------------------------------------------


def _http_provider(handler: Any, fixed_clock: Callable[[], datetime]) -> HttpSourceRetriever:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(
        transport=transport,
        follow_redirects=False,
        timeout=httpx.Timeout(15.0, connect=5.0),
    )
    return HttpSourceRetriever(client=client, clock=fixed_clock)


def test_http_provider_success_and_hash_identity(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/plain"},
            content=b"hello\r\nworld",
        )

    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.SUCCESS
    assert result.http_status == 200
    assert result.raw_content_sha256 == _sha256(b"hello\r\nworld")
    assert result.normalized_content_sha256 == _sha256(b"hello\nworld")
    assert result.raw_content_ref == f"httpx.v1:{result.raw_content_sha256}"


def test_http_provider_conditional_etag_304_not_modified(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    observed: Dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["if_none_match"] = request.headers.get("if-none-match", "")
        return httpx.Response(304)

    conditional = retrieval_request.model_copy(
        update={"mode": RetrievalMode.CONDITIONAL, "conditional_etag": '"etag-123"'}
    )
    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(conditional, retrieval_source)
    assert observed["if_none_match"] == '"etag-123"'
    assert result.retrieval_status == RetrievalStatus.NOT_MODIFIED
    assert result.http_status == 304
    assert result.raw_content_ref is None


@pytest.mark.parametrize("status", [404, 410])
def test_http_provider_not_found_classification(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
    status: int,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.NOT_FOUND
    assert result.http_status == status
    assert result.raw_content_ref is None


@pytest.mark.parametrize("status", [301, 302, 500, 503])
def test_http_provider_http_error_for_other_non_success_statuses(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
    status: int,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.HTTP_ERROR
    assert result.http_status == status
    assert result.raw_content_ref is None


def test_http_provider_timeout_classification(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated read timeout")

    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.TIMEOUT
    assert result.http_status is None
    assert result.raw_content_ref is None


def test_http_provider_transport_error_provider_error(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated connection failure")

    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.PROVIDER_ERROR
    assert result.raw_content_ref is None


def test_http_provider_content_type_rejection(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "application/octet-stream"}, content=b"x" * 100)

    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.CONTENT_TYPE_REJECTED
    assert result.raw_content_ref is None


def test_http_provider_size_limit_exceeded(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/plain"}, content=b"a" * 10_000)

    tiny_request = retrieval_request.model_copy(update={"max_content_bytes": 100})
    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(tiny_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.SIZE_LIMIT_EXCEEDED
    assert result.raw_content_ref is None


def test_http_provider_parse_error_on_invalid_utf8_text(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/plain"}, content=b"\xff\xfe\x00bad")

    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.PARSE_ERROR
    assert result.raw_content_ref is None


def test_http_provider_empty_body_success_status_is_error(
    retrieval_request: RetrievalRequest,
    retrieval_source: SourceDescriptor,
    fixed_clock: Callable[[], datetime],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/plain"}, content=b"")

    provider = _http_provider(handler, fixed_clock)
    result = provider.retrieve(retrieval_request, retrieval_source)
    assert result.retrieval_status == RetrievalStatus.HTTP_ERROR
    assert result.raw_content_ref is None