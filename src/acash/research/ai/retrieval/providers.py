"""Phase 14 Slice 2 Source Retrieval Providers.

- BaseSourceRetriever: the replaceable provider interface (retrieve(request, source)).
- SourceProviderRegistry: resolves source_id -> (provider_id, descriptor) and delegates,
  enforcing the fail-closed cross-reference contract on provider output.
- FixtureSourceRetriever: deterministic, zero-network provider for unit tests / offline use.
- HttpSourceRetriever: httpx-based HTTP provider enforcing explicit timeout, body-size cap,
  content-type validation and status classification. Unit tests NEVER route through it over a
  real network; httpx MockTransport is used instead.

GOVERNANCE FIREWALL
-------------------
Retrieval is evidence collection. Nothing in this module can register hypotheses, qualify
strategies, authorize trading, or mutate governance state.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

import httpx

from acash.research.ai.retrieval.enums import NormalizationPolicy, RetrievalMode, RetrievalStatus
from acash.research.ai.schema import _canonical_sha256
from acash.research.ai.retrieval.exceptions import (
    ProviderMisconfigurationError,
    UnknownProviderError,
)
from acash.research.ai.retrieval.normalization import (
    compute_raw_content_sha256,
    content_type_accepted,
    is_normalizable_content_type,
    normalize_text_content,
)
from acash.research.ai.retrieval.schema import (
    RetrievalProvenance,
    RetrievalRequest,
    RetrievalResult,
    SourceDescriptor,
)

_ALLOWED_FAILURE_HTTP_STATUSES: Tuple[int, ...] = (404, 410)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def _derive_result_id(
    request_id: str,
    provider_id: str,
    retrieved_at_utc: str,
    status: RetrievalStatus,
    raw_sha: Optional[str],
) -> str:
    """Deterministic result identifier derived from stable retrieval coordinates."""
    payload: Dict[str, Any] = {
        "provider_id": provider_id,
        "raw_content_sha256": raw_sha,
        "request_id": request_id,
        "retrieved_at_utc": retrieved_at_utc,
        "status": status.value,
    }
    return "RET-RES-" + _canonical_sha256(payload)[:32]


def _failure_result(
    request: RetrievalRequest,
    source: SourceDescriptor,
    provider_id: str,
    status: RetrievalStatus,
    retrieved_at_utc: str,
    http_status: Optional[int] = None,
    detail: Optional[str] = None,
) -> RetrievalResult:
    """Build a classified failure result (no content acquired)."""
    provenance = RetrievalProvenance(
        source_id=source.source_id,
        locator=request.locator,
        provider_id=provider_id,
        requested_at_utc=request.created_at_utc,
        retrieved_at_utc=retrieved_at_utc,
        http_status=http_status,
        content_type_received=None,
        content_bytes_observed=0,
        raw_content_sha256=None,
        normalized_content_sha256=None,
        normalization_policy=NormalizationPolicy.NONE,
        retrieval_mode=request.mode,
        retrieval_status=status,
        content_ref="NONE_CONTENT",
    )
    return RetrievalResult(
        result_id=_derive_result_id(
            request.request_id, provider_id, retrieved_at_utc, status, None
        ),
        request_id=request.request_id,
        source_id=source.source_id,
        retrieval_status=status,
        retrieved_at_utc=retrieved_at_utc,
        http_status=http_status,
        returned_content_type=None,
        content_length_bytes=0,
        raw_content_sha256=None,
        normalized_content_sha256=None,
        normalization_policy=NormalizationPolicy.NONE,
        raw_content_ref=None,
        error_detail=detail,
        provenance=provenance,
    )


def _content_result(
    request: RetrievalRequest,
    source: SourceDescriptor,
    provider_id: str,
    retrieved_at_utc: str,
    http_status: int,
    content_type: str,
    raw_bytes: bytes,
) -> RetrievalResult:
    """Build a SUCCESS result performing the deterministic normalization parse gate.

    A declared-text content body that fails strict UTF-8 normalization is surfaced as an
    explicit PARSE_ERROR rather than being stored ambiguously.
    """
    raw_sha = compute_raw_content_sha256(raw_bytes)
    normalization_policy = NormalizationPolicy.NONE
    normalized_sha: Optional[str] = None
    if is_normalizable_content_type(content_type):
        normalized = normalize_text_content(raw_bytes)
        if normalized is None:
            return _failure_result(
                request,
                source,
                provider_id,
                RetrievalStatus.PARSE_ERROR,
                retrieved_at_utc,
                http_status=http_status,
                detail="Declared text content failed the strict UTF-8 normalization pass.",
            )
        normalized_sha = compute_raw_content_sha256(normalized)
        normalization_policy = NormalizationPolicy.UTF8_LINE_ENDINGS

    content_ref = f"{provider_id}:{raw_sha}"
    provenance = RetrievalProvenance(
        source_id=source.source_id,
        locator=request.locator,
        provider_id=provider_id,
        requested_at_utc=request.created_at_utc,
        retrieved_at_utc=retrieved_at_utc,
        http_status=http_status,
        content_type_received=content_type,
        content_bytes_observed=len(raw_bytes),
        raw_content_sha256=raw_sha,
        normalized_content_sha256=normalized_sha,
        normalization_policy=normalization_policy,
        retrieval_mode=request.mode,
        retrieval_status=RetrievalStatus.SUCCESS,
        content_ref=content_ref,
    )
    return RetrievalResult(
        result_id=_derive_result_id(
            request.request_id, provider_id, retrieved_at_utc, RetrievalStatus.SUCCESS, raw_sha
        ),
        request_id=request.request_id,
        source_id=source.source_id,
        retrieval_status=RetrievalStatus.SUCCESS,
        retrieved_at_utc=retrieved_at_utc,
        http_status=http_status,
        returned_content_type=content_type,
        content_length_bytes=len(raw_bytes),
        raw_content_sha256=raw_sha,
        normalized_content_sha256=normalized_sha,
        normalization_policy=normalization_policy,
        raw_content_ref=content_ref,
        error_detail=None,
        provenance=provenance,
    )


class BaseSourceRetriever(ABC):
    """Replaceable provider interface for retrieving a single source."""

    provider_id: str

    @abstractmethod
    def retrieve(
        self,
        request: RetrievalRequest,
        source: SourceDescriptor,
    ) -> RetrievalResult:
        """Retrieve ``source`` per ``request`` and return an immutable, classified result."""


class SourceProviderRegistry:
    """Binds source identities to providers and enforces the fail-closed contract.

    The registry is the single place that MUST know which provider serves which source.
    It never fabricates a default provider for an unknown source. It is NOT itself a
    provider (it never issues a retrieval directly).
    """

    def __init__(
        self,
        providers: Mapping[str, BaseSourceRetriever],
        source_bindings: Mapping[str, Tuple[str, SourceDescriptor]],
    ) -> None:
        self._providers: Dict[str, BaseSourceRetriever] = dict(providers)
        self._source_bindings: Dict[str, Tuple[str, SourceDescriptor]] = dict(source_bindings)

    def registered_provider_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self._providers.keys()))

    def registered_source_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self._source_bindings.keys()))

    def resolve_source(self, source_id: str) -> SourceDescriptor:
        binding = self._source_bindings.get(source_id)
        if binding is None:
            raise UnknownProviderError(
                f"No registered source descriptor for source_id '{source_id}'."
            )
        return binding[1]

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        binding = self._source_bindings.get(request.source_id)
        if binding is None:
            raise UnknownProviderError(
                f"No registered source descriptor for source_id '{request.source_id}'."
            )
        provider_id, source = binding
        provider = self._providers.get(provider_id)
        if provider is None:
            raise UnknownProviderError(
                f"Provider '{provider_id}' requested by source '{request.source_id}' is not registered."
            )
        if request.locator != source.locator:
            raise ProviderMisconfigurationError(
                f"request.locator '{request.locator}' does not match source descriptor "
                f"locator '{source.locator}'."
            )
        result = provider.retrieve(request=request, source=source)
        if result.request_id != request.request_id or result.source_id != request.source_id:
            raise ProviderMisconfigurationError(
                "Provider returned a result not bound to the originating request/source."
            )
        if result.provenance.locator != request.locator:
            raise ProviderMisconfigurationError(
                "Provider returned provenance.locator that does not match the originating request locator."
            )
        if result.provenance.source_id != request.source_id:
            raise ProviderMisconfigurationError(
                "Provider returned provenance.source_id that does not match the originating request source_id."
            )
        return result


# ---------------------------------------------------------------------------
# Deterministic, zero-network fixture provider
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureContent:
    """Deterministic canned content served by FixtureSourceRetriever.

    ``status_override`` lets tests simulate TIMEOUT / HTTP_ERROR / PARSE_ERROR /
    PROVIDER_ERROR without any IO or timing.
    """

    body: bytes
    content_type: str = "text/plain"
    http_status: int = 200
    status_override: Optional[RetrievalStatus] = None


class FixtureSourceRetriever(BaseSourceRetriever):
    """Deterministic, zero-network retriever for unit tests and offline demos.

    A fixed ``clock`` makes repeated retrieval byte-identical (used by determinism tests).
    """

    provider_id = "fixture.deterministic.v1"

    def __init__(
        self,
        catalog: Mapping[str, FixtureContent],
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._catalog: Dict[str, FixtureContent] = dict(catalog)
        self._clock: Callable[[], datetime] = clock if clock is not None else _utc_now

    def retrieve(
        self,
        request: RetrievalRequest,
        source: SourceDescriptor,
    ) -> RetrievalResult:
        retrieved_at_utc = _iso_dt(self._clock())
        item = self._catalog.get(request.locator)
        if item is None:
            return _failure_result(
                request,
                source,
                self.provider_id,
                RetrievalStatus.NOT_FOUND,
                retrieved_at_utc,
                http_status=404,
                detail="No fixture content registered for the requested locator.",
            )
        if item.status_override is not None:
            simulated = item.status_override
            http_status: Optional[int] = item.http_status
            if simulated in (RetrievalStatus.TIMEOUT, RetrievalStatus.PROVIDER_ERROR):
                http_status = None
            return _failure_result(
                request,
                source,
                self.provider_id,
                simulated,
                retrieved_at_utc,
                http_status=http_status,
                detail=f"Fixture simulates retrieval outcome {simulated.value}.",
            )
        if len(item.body) > request.max_content_bytes:
            return _failure_result(
                request,
                source,
                self.provider_id,
                RetrievalStatus.SIZE_LIMIT_EXCEEDED,
                retrieved_at_utc,
                http_status=item.http_status,
                detail=f"Fixture body ({len(item.body)} bytes) exceeds max_content_bytes={request.max_content_bytes}.",
            )
        if not content_type_accepted(item.content_type, request.accepted_content_types):
            return _failure_result(
                request,
                source,
                self.provider_id,
                RetrievalStatus.CONTENT_TYPE_REJECTED,
                retrieved_at_utc,
                http_status=item.http_status,
                detail=f"content_type '{item.content_type}' is not accepted by the request.",
            )
        return _content_result(
            request,
            source,
            self.provider_id,
            retrieved_at_utc,
            item.http_status,
            item.content_type,
            item.body,
        )


# ---------------------------------------------------------------------------
# httpx-based HTTP provider (NEVER used over a real network by unit tests)
# ---------------------------------------------------------------------------


class HttpSourceRetriever(BaseSourceRetriever):
    """HTTP/HTTPS retrieval via httpx with fail-closed timeout/size/type handling.

    Policy:
    - explicit per-request timeout
    - maximum body size enforced while streaming (never buffered unbounded)
    - content-type validated against the request's accepted types
    - redirects are NOT silently followed (3xx surfaces as HTTP_ERROR)
    - failures are classified explicitly (TIMEOUT / HTTP_ERROR / NOT_FOUND /
      NOT_MODIFIED / CONTENT_TYPE_REJECTED / SIZE_LIMIT_EXCEEDED / PARSE_ERROR /
      PROVIDER_ERROR)
    """

    provider_id = "httpx.v1"

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        clock: Optional[Callable[[], datetime]] = None,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 15.0,
    ) -> None:
        if client is None:
            client = httpx.Client(
                follow_redirects=False,
                timeout=httpx.Timeout(read_timeout_seconds, connect=connect_timeout_seconds),
                limits=httpx.Limits(max_keepalive_connections=4, max_connections=8),
            )
        self._client = client
        self._clock: Callable[[], datetime] = clock if clock is not None else _utc_now

    def retrieve(
        self,
        request: RetrievalRequest,
        source: SourceDescriptor,
    ) -> RetrievalResult:
        retrieved_at_utc = _iso_dt(self._clock())
        headers: Dict[str, str] = {}
        if request.mode == RetrievalMode.CONDITIONAL:
            if request.conditional_etag:
                headers["If-None-Match"] = request.conditional_etag
            if request.conditional_last_modified_utc:
                headers["If-Modified-Since"] = request.conditional_last_modified_utc
        try:
            with self._client.stream(
                "GET",
                request.locator,
                headers=headers,
                timeout=request.timeout_seconds,
            ) as response:
                if response.status_code == 304:
                    return _failure_result(
                        request,
                        source,
                        self.provider_id,
                        RetrievalStatus.NOT_MODIFIED,
                        retrieved_at_utc,
                        http_status=304,
                        detail="Conditional request returned 304 Not Modified.",
                    )
                if response.status_code in _ALLOWED_FAILURE_HTTP_STATUSES:
                    return _failure_result(
                        request,
                        source,
                        self.provider_id,
                        RetrievalStatus.NOT_FOUND,
                        retrieved_at_utc,
                        http_status=response.status_code,
                        detail=f"HTTP status {response.status_code}: resource not found.",
                    )
                if response.status_code < 200 or response.status_code >= 300:
                    return _failure_result(
                        request,
                        source,
                        self.provider_id,
                        RetrievalStatus.HTTP_ERROR,
                        retrieved_at_utc,
                        http_status=response.status_code,
                        detail=f"Non-success HTTP status {response.status_code} (redirects are not followed).",
                    )

                returned_header = response.headers.get("content-type")
                returned_content_type = returned_header.split(";")[0].strip().lower() if returned_header else ""
                if not returned_content_type or not content_type_accepted(
                    returned_content_type, request.accepted_content_types
                ):
                    return _failure_result(
                        request,
                        source,
                        self.provider_id,
                        RetrievalStatus.CONTENT_TYPE_REJECTED,
                        retrieved_at_utc,
                        http_status=response.status_code,
                        detail=f"content_type '{returned_header}' is not accepted by the request.",
                    )

                # Streaming consumption: the body is read lazily and the cumulative
                # size is checked after every chunk, so network consumption is bounded
                # by max_content_bytes plus at most one transport chunk.
                raw_bytes = b""
                try:
                    for chunk in response.iter_bytes():
                        raw_bytes += chunk
                        if len(raw_bytes) > request.max_content_bytes:
                            return _failure_result(
                                request,
                                source,
                                self.provider_id,
                                RetrievalStatus.SIZE_LIMIT_EXCEEDED,
                                retrieved_at_utc,
                                http_status=response.status_code,
                                detail=f"body exceeds max_content_bytes={request.max_content_bytes}.",
                            )
                except httpx.TimeoutException as exc:
                    return _failure_result(
                        request,
                        source,
                        self.provider_id,
                        RetrievalStatus.TIMEOUT,
                        retrieved_at_utc,
                        http_status=response.status_code,
                        detail=f"HTTP read timed out while streaming the body: {exc}",
                    )
                except httpx.RequestError as exc:
                    return _failure_result(
                        request,
                        source,
                        self.provider_id,
                        RetrievalStatus.PROVIDER_ERROR,
                        retrieved_at_utc,
                        http_status=response.status_code,
                        detail=f"HTTP transport error while streaming the body: {exc}",
                    )
                if len(raw_bytes) == 0:
                    return _failure_result(
                        request,
                        source,
                        self.provider_id,
                        RetrievalStatus.HTTP_ERROR,
                        retrieved_at_utc,
                        http_status=response.status_code,
                        detail="Received an empty body with a 2xx status.",
                    )
                return _content_result(
                    request,
                    source,
                    self.provider_id,
                    retrieved_at_utc,
                    response.status_code,
                    returned_content_type,
                    raw_bytes,
                )
        except httpx.TimeoutException as exc:
            return _failure_result(
                request,
                source,
                self.provider_id,
                RetrievalStatus.TIMEOUT,
                retrieved_at_utc,
                detail=f"HTTP request timed out: {exc}",
            )
        except httpx.RequestError as exc:
            return _failure_result(
                request,
                source,
                self.provider_id,
                RetrievalStatus.PROVIDER_ERROR,
                retrieved_at_utc,
                detail=f"HTTP transport error: {exc}",
            )