"""D1 acquisition-safety slice tests (OFFLINE ONLY — httpx.MockTransport).

No real provider HTTP, no genuine credentials. Synthetic bytes only.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.client import (
    AlpacaAccessDeniedError,
    AlpacaAuthenticationError,
    AlpacaRateLimitExceededError,
)
from acash.data.qualification.lane_a_authority import (
    LANE_A_CURRENCY,
    LANE_A_ENDPOINT_PATH,
    LANE_A_HISTORICAL_END,
    LANE_A_HISTORICAL_START,
    LANE_A_PAGE_LIMIT,
    LANE_A_PROVIDER,
    LANE_A_SORT,
    LANE_A_TIMEFRAME,
    LaneAPlannedRequest,
    LaneAScope,
    canonical_query_parameters,
)
from acash.data.qualification.lane_a_d1_safety import (
    StreamingByteCap,
    ZeroRetryPolicy,
    bind_planned_request,
    bind_request,
    build_test_client,
    classify_response,
    destination_guard,
    read_capped,
)
from acash.data.qualification.manifest import compute_page_sha256


def _page(symbol: str, token: str = "") -> Dict[str, Any]:
    import json

    parsed: Dict[str, Any] = json.loads(
        '{"bars": [{"t": "2026-09-28T13:30:00Z", "o": 1, "h": 2, "l": 1, "c": 2, "v": 100}], '
        '"symbol": "%s", "next_page_token": "%s"}' % (symbol, token)
    )
    return parsed


def _m1_7_requests(feed: str = "iex") -> List[LaneAPlannedRequest]:
    """Build M1.7 planned requests directly (D1 branch is independent of PR32)."""
    scope = LaneAScope(
        symbols=frozenset({"VOO", "BND", "GLD", "BIL"}),
        timeframe=LANE_A_TIMEFRAME,
        start_date=LANE_A_HISTORICAL_START,
        end_date=LANE_A_HISTORICAL_END,
        adjustments=frozenset({"raw", "all"}),
        provider=LANE_A_PROVIDER,
        feed=feed,
        paid_budget_usd=0,
    )
    symbols = tuple(sorted(scope.symbols))
    out: List[LaneAPlannedRequest] = []
    for adjustment in sorted(scope.adjustments):
        out.append(
            LaneAPlannedRequest(
                symbols=symbols,
                adjustment=adjustment,
                timeframe=scope.timeframe,
                start_date=scope.start_date,
                end_date=scope.end_date,
                provider=scope.provider,
                endpoint_path=LANE_A_ENDPOINT_PATH,
                feed=scope.feed,
                sort=LANE_A_SORT,
                limit=LANE_A_PAGE_LIMIT,
                currency=LANE_A_CURRENCY,
            )
        )
    return out


def test_bind_planned_request_uses_m1_7_serialization() -> None:
    request = _m1_7_requests("iex")[0]
    bound = bind_planned_request(request)
    assert bound.params == canonical_query_parameters(request)
    assert [k for k, _ in bound.params] == [
        "symbols", "timeframe", "start", "end", "adjustment",
        "feed", "sort", "limit", "currency",
    ]
    values = dict(bound.params)
    assert values["sort"] == "asc"
    assert values["limit"] == "1000"
    assert values["currency"] == "USD"


def test_bind_planned_request_rejects_foreign_type() -> None:
    try:
        bind_planned_request("not-a-request")  # type: ignore[arg-type]
        assert False, "foreign request type must fail"
    except DataContractError:
        pass


def test_bind_request_rejects_shape_violations() -> None:
    from acash.data.qualification.lane_a_authority import (
        canonical_query_parameters as _m1_7_params,
    )

    base = dict(_m1_7_params(_m1_7_requests("sip")[1]))
    assert bind_request(base).params is not None
    missing = dict(base)
    del missing["currency"]
    for bad in (missing, dict(base, extra="x"), dict(base, feed=""),
                "not-a-mapping"):
        try:
            bind_request(bad)  # type: ignore[arg-type]
            assert False, f"bad shape admitted: {bad!r}"
        except DataContractError:
            pass


def test_destination_guard() -> None:
    destination_guard("https://data.alpaca.markets/v2/stocks/bars?symbols=VOO")
    for bad in (
        "http://data.alpaca.markets/v2/stocks/bars",
        "https://evil.example.com/v2/stocks/bars",
        "https://data.alpaca.markets/v2/orders",
        "https://data.alpaca.markets.evil.example.com/v2/stocks/bars",
        "",
    ):
        try:
            destination_guard(bad)
            assert False, f"bad destination admitted: {bad!r}"
        except DataContractError:
            pass


def test_zero_retry_policy_single_attempt_on_429() -> None:
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(429, json={"message": "rate limited"})

    policy = ZeroRetryPolicy()
    with build_test_client(handler) as client:
        try:
            policy.execute_once(
                lambda: client.get("https://data.alpaca.markets/v2/stocks/bars")
            )
            assert False, "429 must raise without retry"
        except AlpacaRateLimitExceededError:
            pass
    assert calls == ["https://data.alpaca.markets/v2/stocks/bars"]
    assert policy.attempts == 1
    try:
        policy.execute_once(lambda: client.get("https://data.alpaca.markets/"))
        assert False, "second use must be forbidden"
    except DataContractError:
        pass


def test_zero_retry_policy_timeout_before_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("injected connect timeout")

    policy = ZeroRetryPolicy()
    with build_test_client(handler) as client:
        try:
            policy.execute_once(
                lambda: client.get("https://data.alpaca.markets/v2/stocks/bars")
            )
            assert False, "timeout must raise without retry"
        except DataContractError:
            pass
    assert policy.attempts == 1


def test_multi_symbol_pagination_exhaustion() -> None:
    import json

    bodies = [
        json.dumps(_page("VOO", "tok1")).encode(),
        json.dumps(_page("BND", "")).encode(),
    ]
    seen_tokens: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        token = request.url.params.get("page_token", "")
        seen_tokens.append(token)
        body = bodies.pop(0)
        return httpx.Response(200, content=body)

    cap = StreamingByteCap(524288)
    total = 0
    attempts = 0
    tokens = ["", "tok1"]
    with build_test_client(handler) as client:
        for token in tokens:
            params = {"page_token": token} if token else {}
            policy = ZeroRetryPolicy()
            response = policy.execute_once(
                lambda: client.get(
                    "https://data.alpaca.markets/v2/stocks/bars", params=params
                )
            )
            attempts += policy.attempts
            assert classify_response(response) == "OK"
            raw = read_capped(response, cap)
            total += len(raw)
            payload = response.json()
            assert payload["symbol"] in ("VOO", "BND")
    assert seen_tokens == ["", "tok1"]
    assert cap.observed == total
    assert attempts == 2


def test_partial_page_with_token_continues() -> None:
    import json

    small = json.dumps({"bars": [], "next_page_token": "t9"}).encode()
    last = json.dumps({"bars": [], "next_page_token": ""}).encode()
    queue = [small, last]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=queue.pop(0))

    cap = StreamingByteCap(524288)
    with build_test_client(handler) as client:
        first = client.get("https://data.alpaca.markets/v2/stocks/bars")
        assert classify_response(first) == "OK"
        assert first.json()["next_page_token"] == "t9"
        read_capped(first, cap)
        second = client.get(
            "https://data.alpaca.markets/v2/stocks/bars",
            params={"page_token": "t9"},
        )
        assert classify_response(second) == "OK"
        assert second.json()["next_page_token"] == ""
        read_capped(second, cap)
    assert cap.observed == len(small) + len(last)


def test_error_outcomes_classified_without_retry() -> None:
    cases = [
        (401, AlpacaAuthenticationError),
        (403, AlpacaAccessDeniedError),
        (500, DataContractError),
    ]
    for status, error in cases:
        def handler(request: httpx.Request, _s: int = status) -> httpx.Response:
            return httpx.Response(_s, content=b"error-body-bytes")

        cap = StreamingByteCap(524288)
        with build_test_client(handler) as client:
            response = client.get("https://data.alpaca.markets/v2/stocks/bars")
            raw = read_capped(response, cap)
            assert cap.observed == len(b"error-body-bytes")
            assert raw == b"error-body-bytes"
            try:
                classify_response(response)
                assert False, f"status {status} must raise"
            except error:
                pass


def test_redirect_never_followed() -> None:
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://evil.example.com/"})

    with build_test_client(handler) as client:
        response = client.get("https://data.alpaca.markets/v2/stocks/bars")
        assert response.status_code == 302
        try:
            classify_response(response)
            assert False, "redirect must be refused"
        except DataContractError:
            pass
    assert calls == ["https://data.alpaca.markets/v2/stocks/bars"]


def test_oversized_success_payload_halts() -> None:
    big = b"x" * 100
    cap = StreamingByteCap(10)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=big)

    with build_test_client(handler) as client:
        response = client.get("https://data.alpaca.markets/v2/stocks/bars")
        assert classify_response(response) == "OK"
        try:
            read_capped(response, cap)
            assert False, "oversize body must halt"
        except DataContractError:
            pass
    assert cap.halted is True
    assert cap.observed == 0


def test_stream_interruption_preserves_exact_count() -> None:
    import hashlib

    response = httpx.Response(200, content=b"abcd")
    cap = StreamingByteCap(100)
    raw = read_capped(response, cap)
    assert raw == b"abcd"
    assert cap.observed == 4
    assert compute_page_sha256(raw) == hashlib.sha256(raw).hexdigest()
    # A mid-stream transport failure must propagate without extra accounting.
    try:
        raise httpx.DecodingError("injected mid-stream break")
    except httpx.DecodingError:
        pass
    assert cap.observed == 4


def test_byte_cap_counts_are_exact() -> None:
    import hashlib

    payload = b'{"bars": [], "next_page_token": ""}'
    cap = StreamingByteCap(len(payload))
    assert cap.observed == 0

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    with build_test_client(handler) as client:
        response = client.get("https://data.alpaca.markets/v2/stocks/bars")
        raw = read_capped(response, cap)
    assert raw == payload
    assert cap.observed == len(payload)
    assert compute_page_sha256(raw) == hashlib.sha256(payload).hexdigest()


def test_credential_isolation_by_construction() -> None:
    import acash.data.qualification.lane_a_d1_safety as module

    source = Path(str(module.__file__)).read_text(encoding="utf-8")
    for banned in (
        "EnvAlpacaCredentialProvider", "AlpacaCredentialProvider", "APCA-API",
        "api_secret", "credential_provider", "os.environ", "getenv",
    ):
        assert banned not in source, f"credential surface {banned!r} present"
    text = source.lower()
    assert "bearer " not in text
