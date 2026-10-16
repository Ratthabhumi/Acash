"""D3-01 streaming proof tests (OFFLINE ONLY — httpx.MockTransport).

No real provider HTTP, no credentials, no network. All reads go through
streaming requests (client.stream) with GENERATOR bodies: httpx preloads
plain-bytes MockTransport bodies, so generator content is what exercises
the true streaming path. Eagerly read responses fail closed.
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any, Iterator, List

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_d1_safety import (
    StreamingByteCap,
    ZeroRetryPolicy,
    build_test_client,
    classify_response,
)
from acash.data.qualification.lane_a_d3_streaming import read_identity_capped
from acash.data.qualification.manifest import compute_page_sha256

_URL = "https://data.alpaca.markets/v2/stocks/bars"


def _streaming_handler(
    payload: bytes, headers: dict[str, str] | None = None
) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=(chunk for chunk in [payload]), headers=headers or {}
        )

    return handler


def test_exact_budget_boundary_passes() -> None:
    payload = b"x" * 64
    cap = StreamingByteCap(64)
    with build_test_client(_streaming_handler(payload)) as client:
        with client.stream("GET", _URL) as response:
            body, digest = read_identity_capped(response, cap)
    assert body == payload
    assert digest == compute_page_sha256(payload)
    assert cap.observed == 64
    assert cap.halted is False


def test_one_byte_beyond_limit_fails() -> None:
    cap = StreamingByteCap(64)
    with build_test_client(_streaming_handler(b"x" * 65)) as client:
        with client.stream("GET", _URL) as response:
            try:
                read_identity_capped(response, cap)
                assert False, "one byte over cap must fail"
            except DataContractError:
                pass
    assert cap.halted is True


def test_zero_length_payload() -> None:
    import hashlib

    cap = StreamingByteCap(16)
    with build_test_client(_streaming_handler(b"")) as client:
        with client.stream("GET", _URL) as response:
            body, digest = read_identity_capped(response, cap)
    assert body == b""
    assert digest == hashlib.sha256(b"").hexdigest()
    assert cap.observed == 0


def test_multi_chunk_response() -> None:
    chunks = [b"ab", b"cdef", b"gh"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=(c for c in chunks))

    cap = StreamingByteCap(100)
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            body, digest = read_identity_capped(response, cap)
    assert body == b"abcdefgh"
    assert digest == compute_page_sha256(b"abcdefgh")
    assert cap.observed == 8


def test_compressed_response_rejected_under_identity_only() -> None:
    raw = b'{"bars": []}' * 10
    gzipped = gzip.compress(raw)
    assert len(gzipped) != len(raw)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=(c for c in [gzipped]),
            headers={"content-encoding": "gzip"},
        )

    cap = StreamingByteCap(10_000)
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            try:
                read_identity_capped(response, cap)
                assert False, "gzip content must be rejected under identity-only"
            except DataContractError:
                pass
    assert cap.observed == 0


def test_header_body_disagreement_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=(c for c in [b"12345"]),
            headers={"content-length": "999"},
        )

    cap = StreamingByteCap(10_000)
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            try:
                read_identity_capped(response, cap)
                assert False, "content-length mismatch must fail"
            except DataContractError:
                pass
    assert cap.halted is True


def test_malformed_content_length_treated_absent() -> None:
    cap = StreamingByteCap(100)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=(c for c in [b"ok"]),
            headers={"content-length": "not-a-number"},
        )

    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            body, _ = read_identity_capped(response, cap)
    assert body == b"ok"
    assert cap.observed == 2


def test_interrupted_stream() -> None:
    def gen() -> Iterator[bytes]:
        yield b"ab"
        raise httpx.StreamClosed()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=gen())

    cap = StreamingByteCap(100)
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            try:
                read_identity_capped(response, cap)
                assert False, "interrupted stream must fail"
            except DataContractError:
                pass
    assert cap.halted is True
    assert cap.observed == 2


def test_eagerly_read_response_rejected() -> None:
    cap = StreamingByteCap(100)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"data")

    with build_test_client(handler) as client:
        response = client.get(_URL)
        try:
            read_identity_capped(response, cap)
            assert False, "eagerly read body must fail closed"
        except DataContractError:
            pass
    assert cap.observed == 0


def test_pagination_cumulative_budget() -> None:
    bodies = [b"a" * 40, b"b" * 40]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=(c for c in [bodies.pop(0)]))

    cap = StreamingByteCap(64)
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as first:
            body, _ = read_identity_capped(first, cap)
            assert body == b"a" * 40
        with client.stream("GET", _URL, params={"page_token": "t1"}) as second:
            try:
                read_identity_capped(second, cap)
                assert False, "cumulative overflow must fail"
            except DataContractError:
                pass
    # Breaching chunk is counted (it entered process memory), then halted.
    assert cap.observed == 80
    assert cap.halted is True


def test_reservation_before_dispatch_with_budget() -> None:
    from acash.data.qualification.lane_a_canary import ReservationJournal
    import tempfile

    policy = ZeroRetryPolicy()
    cap = StreamingByteCap(100)
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=(c for c in [b"data"]))

    with tempfile.TemporaryDirectory() as tmp:
        journal = ReservationJournal.create(Path(tmp) / "run")
        journal.reserve(1, "d" * 64)
        with build_test_client(handler) as client:
            with client.stream("GET", _URL) as response:
                streamed = policy.execute_once(lambda: response)
                assert classify_response(streamed) == "OK"
                body, _ = read_identity_capped(streamed, cap)
            journal.settle(1, "OK")
        assert body == b"data"
        assert journal.reserved_count == 1
        assert journal.completed == {1: "OK"}
        assert calls != []


def test_no_retry_no_fallback_no_credentials_in_module() -> None:
    import acash.data.qualification.lane_a_d3_streaming as module

    source = Path(str(module.__file__)).read_text(encoding="utf-8")
    for banned in ("import socket", "time.sleep", "max_retries",
                   "APCA-API", "api_secret", "os.environ", "getenv",
                   "fallback", "trust_env"):
        assert banned not in source, f"banned surface {banned!r} present"


def test_digest_matches_stored_evidence_helper() -> None:
    from acash.data.qualification.lane_a_transport import store_raw_evidence
    import tempfile

    payload = b"evidence-bytes-0123456789"
    cap = StreamingByteCap(1024)
    with build_test_client(_streaming_handler(payload)) as client:
        with client.stream("GET", _URL) as response:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "ev"
                run_dir = root / "lane_a_runs" / "run_ev_001"
                run_dir.mkdir(parents=True)
                (run_dir / "run.json").write_text("{}")
                body, digest = read_identity_capped(response, cap)
                receipt = store_raw_evidence(
                    root=root, run_id="run_ev_001", name="page",
                    payload=body, metadata={"feed": "iex", "request_index": 0},
                )
                assert receipt["content_sha256"] == digest
                assert (run_dir / "page.bin").read_bytes() == body


def test_decoded_vs_raw_populations_differ_under_coding() -> None:
    raw = b'{"bars": []}' * 20
    gzipped = gzip.compress(raw)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=(c for c in [gzipped]),
            headers={"content-encoding": "gzip"},
        )

    wire_seen: List[bytes] = []
    with build_test_client(handler) as client:
        with client.stream("GET", _URL) as response:
            wire_seen.append(b"".join(list(response.iter_raw())))
    assert wire_seen[0] == gzipped
    assert len(wire_seen[0]) != len(raw)
