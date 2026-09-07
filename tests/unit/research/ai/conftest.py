"""Shared deterministic fixtures for Phase 14 Slice 2 retrieval layer tests.

All fixtures are fully synthetic and offline. No real network I/O is possible
from these tests: the HTTP provider under test is always driven through an
``httpx.MockTransport`` (or not exercised at all).
"""

from datetime import datetime, timezone
from typing import Callable, Dict

import pytest

from acash.research.ai.enums import SourceType
from acash.research.ai.retrieval.providers import FixtureContent
from acash.research.ai.retrieval.schema import (
    RetrievalRequest,
    SourceDescriptor,
    SourceRetrievalPolicy,
)

FI_SOURCE_ID: str = "SRC-0011223344556677"
FI_LOCATOR: str = "https://fixture.example.com/paper.txt"


@pytest.fixture
def retrieval_source() -> SourceDescriptor:
    return SourceDescriptor(
        source_id=FI_SOURCE_ID,
        locator=FI_LOCATOR,
        source_type=SourceType.ACADEMIC,
        publisher_or_owner="Fixture Lab",
        title="Deterministic Fixture Paper",
        recorded_at_utc="2026-09-06T00:00:00+00:00",
        retrieval_policy=SourceRetrievalPolicy(
            preferred_timeout_seconds=15.0,
            declared_max_content_bytes=1_000_000,
            declared_content_types=("text/plain",),
        ),
    )


@pytest.fixture
def retrieval_request() -> RetrievalRequest:
    return RetrievalRequest(
        request_id="RET-REQ-0011223344556677",
        source_id=FI_SOURCE_ID,
        locator=FI_LOCATOR,
        timeout_seconds=10.0,
        max_content_bytes=1_000_000,
        accepted_content_types=("text/plain",),
        created_at_utc="2026-09-07T11:00:00+00:00",
    )


@pytest.fixture
def fixture_catalog() -> Dict[str, FixtureContent]:
    return {
        FI_LOCATOR: FixtureContent(
            body=b"line one\r\nline two\r\n",
            content_type="text/plain",
            http_status=200,
        ),
    }


@pytest.fixture
def fixed_clock() -> Callable[[], datetime]:
    """Deterministic clock so repeated retrieval is byte-identical."""

    def _clock() -> datetime:
        return datetime(2026, 9, 7, 11, 22, 33, tzinfo=timezone.utc)

    return _clock