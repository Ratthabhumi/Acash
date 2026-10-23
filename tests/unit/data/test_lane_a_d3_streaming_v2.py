"""D3 V2 byte-contract amendment tests (OFFLINE ONLY, httpx.MockTransport).

V2 rejects ambiguous, malformed or negative Content-Length BEFORE the body
iterator is touched. V1 remains unchanged and is covered separately.
No provider HTTP, credentials or network access is used here.
"""

from __future__ import annotations

import gzip
from typing import Any, Iterator, List

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_d1_safety import (
    StreamingByteCap,
    build_test_client,
)
from acash.data.qualification.lane_a_d3_streaming import (
    BYTE_CONTRACT_V1,
    BYTE_CONTRACT_V2,
    D3_OBSERVED_BYTE_BUDGET,
    read_identity_capped_v2,
)
from acash.data.qualification.manifest import compute_page_sha256

_URL = "https://data.alpaca.markets/v2/stocks/bars"


def _handler(
    payload: bytes, headers: Any = None, started: List[bool] | None = None
) -> Any:
    def gen() -> Iterator[bytes]:
        if started is not None:
            started.append(True)
        yield payload

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=gen(), headers=headers or {})

    return handler


@pytest.mark.parametrize(
    "raw_length",
    ["not-a-number", "-5", " 5", "+5", "", "5, 5", "0x10", "5.0"],
)
def test_invalid_content_length_rejected_before_body(raw_length: str) -> None:
    started: List[bool] = []
    cap = StreamingByteCap(100)
    handler = _handler(b"ok", {"content-length": raw_length}, started)
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            with pytest.raises(DataContractError):
                read_identity_capped_v2(response, cap)
    assert started == []
    assert cap.observed == 0
    assert cap.halted is True


def test_duplicate_content_length_headers_rejected_before_body() -> None:
    started: List[bool] = []
    cap = StreamingByteCap(100)
    handler = _handler(
        b"ok",
        [("content-length", "5"), ("content-length", "5")],
        started,
    )
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            with pytest.raises(DataContractError):
                read_identity_capped_v2(response, cap)
    assert started == []
    assert cap.observed == 0
    assert cap.halted is True


def test_absent_content_length_uses_chunk_accounting() -> None:
    payload = b"abc"
    cap = StreamingByteCap(100)
    with build_test_client(_handler(payload)) as client:
        with client.stream("GET", _URL) as response:
            body, digest = read_identity_capped_v2(response, cap)
    assert body == payload
    assert digest == compute_page_sha256(payload)
    assert cap.observed == 3
    assert cap.halted is False


def test_zero_content_length_with_empty_body_passes() -> None:
    cap = StreamingByteCap(16)
    with build_test_client(_handler(b"", {"content-length": "0"})) as client:
        with client.stream("GET", _URL) as response:
            body, digest = read_identity_capped_v2(response, cap)
    assert body == b""
    assert digest == compute_page_sha256(b"")
    assert cap.observed == 0


def test_zero_content_length_with_body_fails_after_accounting() -> None:
    cap = StreamingByteCap(16)
    with build_test_client(_handler(b"ok", {"content-length": "0"})) as client:
        with client.stream("GET", _URL) as response:
            with pytest.raises(DataContractError):
                read_identity_capped_v2(response, cap)
    assert cap.observed == 2
    assert cap.halted is True


def test_exact_content_length_passes() -> None:
    payload = b"abcd"
    cap = StreamingByteCap(100)
    with build_test_client(
        _handler(payload, {"content-length": str(len(payload))})
    ) as client:
        with client.stream("GET", _URL) as response:
            body, digest = read_identity_capped_v2(response, cap)
    assert body == payload
    assert digest == compute_page_sha256(payload)
    assert cap.observed == 4


def test_non_identity_encoding_rejected_before_length_and_body() -> None:
    started: List[bool] = []
    raw = b'{"bars": []}' * 10
    gzipped = gzip.compress(raw)
    cap = StreamingByteCap(10_000)
    handler = _handler(
        gzipped,
        {"content-encoding": "gzip", "content-length": "not-a-number"},
        started,
    )
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            with pytest.raises(DataContractError):
                read_identity_capped_v2(response, cap)
    assert started == []
    assert cap.observed == 0


def test_cap_overflow_is_counted_then_halted() -> None:
    cap = StreamingByteCap(64)
    with build_test_client(_handler(b"x" * 100_000)) as client:
        with client.stream("GET", _URL) as response:
            with pytest.raises(DataContractError):
                read_identity_capped_v2(response, cap)
    assert cap.observed == 100_000
    assert cap.halted is True


def test_interrupted_stream_poisons_cap() -> None:
    def gen() -> Iterator[bytes]:
        yield b"ab"
        raise httpx.StreamClosed()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=gen())

    cap = StreamingByteCap(100)
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            with pytest.raises(DataContractError):
                read_identity_capped_v2(response, cap)
    assert cap.observed == 2
    assert cap.halted is True


def test_eagerly_read_response_rejected() -> None:
    cap = StreamingByteCap(100)
    with build_test_client(_handler(b"data")) as client:
        response = client.get(_URL)
        with pytest.raises(DataContractError):
            read_identity_capped_v2(response, cap)
    assert cap.observed == 0


def test_contract_versions_are_distinct() -> None:
    assert BYTE_CONTRACT_V1 == "IDENTITY_ONLY_RAW_RESPONSE_BODY_V1"
    assert BYTE_CONTRACT_V2 == "IDENTITY_ONLY_RAW_RESPONSE_BODY_V2"
    assert BYTE_CONTRACT_V1 != BYTE_CONTRACT_V2
    assert D3_OBSERVED_BYTE_BUDGET == 524_288
