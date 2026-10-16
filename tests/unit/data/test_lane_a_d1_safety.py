"""D1 acquisition-safety slice tests (OFFLINE ONLY — httpx.MockTransport).

No real provider HTTP, no genuine credentials. Synthetic bytes only.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List

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
    D1BoundRequest,
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
    destination_guard("https://data.alpaca.markets/v2/stocks/bars")
    for bad in (
        "http://data.alpaca.markets/v2/stocks/bars",
        "https://evil.example.com/v2/stocks/bars",
        "https://data.alpaca.markets/v2/orders",
        "https://data.alpaca.markets.evil.example.com/v2/stocks/bars",
        "https://data.alpaca.markets/v2/stocks/bars?symbols=VOO",
        "https://data.alpaca.markets/v2/stocks/bars#frag",
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
    # Honest overflow accounting: the breaching 100-byte chunk was consumed
    # into the process, so observed counts it even though nothing returns.
    assert cap.observed == 100


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


def test_destination_guard_adversarial_identities() -> None:
    destination_guard("https://data.alpaca.markets/v2/stocks/bars")
    for bad in (
        # Extra path suffixes change endpoint identity.
        "https://data.alpaca.markets/v2/stocks/bars/extra",
        "https://data.alpaca.markets/v2/stocks/barsextra",
        "https://data.alpaca.markets/v2/stocks/bars/",
        # Explicit ports (including the default) are not the canonical origin.
        "https://data.alpaca.markets:8443/v2/stocks/bars",
        "https://data.alpaca.markets:443/v2/stocks/bars",
        # Userinfo injection.
        "https://user:pass@data.alpaca.markets/v2/stocks/bars",
        "https://user@data.alpaca.markets/v2/stocks/bars",
        # Hostname lookalikes.
        "https://data-alpaca-markets.com/v2/stocks/bars",
        "https://data.alpaca.markets.evil.example.com/v2/stocks/bars",
        "https://evildata.alpaca.markets/v2/stocks/bars",
        # Query and fragment never belong in the destination identity.
        "https://data.alpaca.markets/v2/stocks/bars?symbols=VOO&x=1",
        "https://data.alpaca.markets/v2/stocks/bars#section",
        # Percent-encoded path variants.
        "https://data.alpaca.markets/v2/stocks/%62ars",
        "https://data.alpaca.markets/v2/stocks/bars%2F..",
        "https://data.alpaca.markets/v2/stocks/bars%00",
        # Case and malformed inputs.
        "https://data.alpaca.markets/V2/Stocks/Bars",
        "https://data.alpaca.markets",
        "",
        "not-a-url::::",
    ):
        try:
            destination_guard(bad)
            assert False, f"bad destination admitted: {bad!r}"
        except DataContractError:
            pass
    try:
        destination_guard(None)  # type: ignore[arg-type]
        assert False, "None destination admitted"
    except DataContractError:
        pass


def test_executor_client_pinned_posture(monkeypatch: Any) -> None:
    import httpx as httpx_module

    from acash.data.qualification.lane_a_d1_safety import build_executor_client

    client = build_executor_client()
    assert client.follow_redirects is False
    assert client.trust_env is False
    assert client.timeout.read == 30.0
    # TLS verification is consumed into the transport at construction; pin it
    # by intercepting the constructor kwargs (no network involved).
    captured: Dict[str, Any] = {}
    real_client = httpx_module.Client

    def spy(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return real_client(follow_redirects=False, trust_env=False)

    monkeypatch.setattr(httpx_module, "Client", spy)
    build_executor_client(timeout_seconds=7.5)
    assert captured.get("verify") is True
    assert captured.get("follow_redirects") is False
    assert captured.get("trust_env") is False
    assert captured.get("timeout") == 7.5
    custom = build_executor_client(timeout_seconds=5)
    assert custom.timeout.read == 5.0
    for bad_timeout in (0, -1, "30", True, None):
        try:
            build_executor_client(timeout_seconds=bad_timeout)  # type: ignore[arg-type]
            assert False, f"bad timeout admitted: {bad_timeout!r}"
        except DataContractError:
            pass
    # Hostile ambient environment changes nothing: no proxy inheritance,
    # no credential pickup (the factory takes no provider at all).
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:8080")
    monkeypatch.setenv("ACASH_ALPACA_API_KEY_ID", "junk")
    monkeypatch.setenv("ACASH_ALPACA_API_SECRET", "junk")
    hostile = build_executor_client()
    assert hostile.trust_env is False
    assert hostile.follow_redirects is False
    destination_guard("https://data.alpaca.markets/v2/stocks/bars")


def test_redirect_all_3xx_denied() -> None:
    for status in (300, 301, 302, 303, 304, 305, 307, 308):
        def handler(request: httpx.Request, _s: int = status) -> httpx.Response:
            return httpx.Response(_s, headers={"location": "https://evil.example.com/"})

        with build_test_client(handler) as client:
            response = client.get("https://data.alpaca.markets/v2/stocks/bars")
            assert response.status_code == status
            try:
                classify_response(response)
                assert False, f"3xx {status} must be refused"
            except DataContractError as exc:
                assert "D1_REDIRECT_DENIED" in str(exc)


def test_canonical_contract_is_exactly_nine_fields_no_asof() -> None:
    """Regression lock: M1.7 stays nine fields; asof needs contract migration."""
    for request in _m1_7_requests("iex") + _m1_7_requests("sip"):
        params = canonical_query_parameters(request)
        assert [k for k, _ in params] == [
            "symbols", "timeframe", "start", "end", "adjustment",
            "feed", "sort", "limit", "currency",
        ]
        assert "asof" not in [k for k, _ in params]
        assert "asof" not in [v for _, v in params]


def test_daily_end_semantics_exact_no_expansion() -> None:
    """end=2026-10-02 binds the full session date verbatim (inclusive, unexpanded)."""
    request = _m1_7_requests("iex")[0]
    assert request.end_date.isoformat() == "2026-10-02"
    values = dict(canonical_query_parameters(request))
    assert values["end"] == "2026-10-02"
    assert "T" not in values["end"]


def test_consume_chunk_boundaries_exact() -> None:
    cap = StreamingByteCap(10)
    cap.consume(b"")
    assert cap.observed == 0
    assert cap.halted is False
    for _ in range(7):
        cap.consume(b"x")
    assert cap.observed == 7
    cap.consume(b"yz1")  # exact fit: 7 + 3 == 10 passes
    assert cap.observed == 10
    assert cap.halted is False
    try:
        cap.consume(b"!")
        assert False, "one byte past cap must halt"
    except DataContractError:
        pass
    # The breaching byte was consumed into the process before the halt.
    assert cap.observed == 11
    assert cap.halted is True
    try:
        cap.consume(b"")
        assert False, "halted cap must stay halted"
    except DataContractError:
        pass


def test_overflow_after_partial_accumulation_halts_without_return() -> None:
    import json

    first = json.dumps({"bars": [1, 2, 3]}).encode()
    second = json.dumps({"bars": [4, 5, 6]}).encode()
    assert len(first) + len(second) > 30
    cap = StreamingByteCap(30)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=first)

    with build_test_client(handler) as client:
        raw = read_capped(client.get("https://data.alpaca.markets/v2/stocks/bars"), cap)
    assert raw == first
    assert cap.observed == len(first)
    assert cap.halted is False

    def handler2(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=second)

    with build_test_client(handler2) as client:
        try:
            read_capped(client.get("https://data.alpaca.markets/v2/stocks/bars"), cap)
            assert False, "second body must overflow the shared cap"
        except DataContractError:
            pass
    # Both bodies were consumed: observed accounts every delivered byte.
    assert cap.observed == len(first) + len(second)
    assert cap.halted is True


def test_gzip_body_counts_decoded_bytes() -> None:
    import gzip
    import json

    payload = json.dumps({"bars": [{"t": "2026-09-28T13:30:00Z"}]}).encode()
    wire = gzip.compress(payload)
    assert len(wire) != len(payload)
    cap = StreamingByteCap(524288)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=wire, headers={"content-encoding": "gzip"}
        )

    with build_test_client(handler) as client:
        response = client.get("https://data.alpaca.markets/v2/stocks/bars")
        assert classify_response(response) == "OK"
        raw = read_capped(response, cap)
    # Accounting unit is decoded bytes (what lands in memory/evidence),
    # never wire bytes: the cap constrains the inflated body.
    assert raw == payload
    assert cap.observed == len(payload)


def test_content_length_exact_match_ok() -> None:
    body = b'{"bars": []}'
    cap = StreamingByteCap(100)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=body, headers={"content-length": str(len(body))}
        )

    with build_test_client(handler) as client:
        assert read_capped(client.get("https://data.alpaca.markets/v2/stocks/bars"), cap) == body
    assert cap.observed == len(body)
    assert cap.halted is False


def test_content_length_mismatch_fails_closed() -> None:
    for declared in ("5", "999999"):
        body = b'{"bars": []}'
        cap = StreamingByteCap(100)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, content=body, headers={"content-length": declared}
            )

        with build_test_client(handler) as client:
            try:
                read_capped(client.get("https://data.alpaca.markets/v2/stocks/bars"), cap)
                assert False, f"length {declared} must fail"
            except DataContractError as exc:
                assert "D1_BODY_LENGTH_MISMATCH" in str(exc)
        assert cap.observed == len(body)
        assert cap.halted is True


def test_content_length_skipped_when_encoded_or_unparseable() -> None:
    import gzip

    payload = b'{"bars": []}'
    wire = gzip.compress(payload)
    cap = StreamingByteCap(100)

    def handler(request: httpx.Request) -> httpx.Response:
        # Wrong encoded length is undecidable against decoded bytes: skip.
        return httpx.Response(
            200, content=wire,
            headers={"content-encoding": "gzip", "content-length": "7"},
        )

    with build_test_client(handler) as client:
        assert read_capped(client.get("https://data.alpaca.markets/v2/stocks/bars"), cap) == payload
    assert cap.observed == len(payload)
    assert cap.halted is False

    cap2 = StreamingByteCap(100)

    def handler2(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, headers={"content-length": "nope"})

    with build_test_client(handler2) as client:
        assert read_capped(client.get("https://data.alpaca.markets/v2/stocks/bars"), cap2) == payload
    assert cap2.observed == len(payload)
    assert cap2.halted is False


def test_midstream_transport_failure_poisons_cap() -> None:
    class _BreakingStream(httpx.SyncByteStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            # First pull yields a full 4096 window; the second pull breaks.
            yield b"x" * 5000
            raise httpx.DecodingError("injected mid-stream break")

        def close(self) -> None:
            return None

    response = httpx.Response(200, stream=_BreakingStream())
    cap = StreamingByteCap(100000)
    try:
        read_capped(response, cap)
        assert False, "midstream break must raise"
    except DataContractError as exc:
        assert "D1_STREAM_INTERRUPTED" in str(exc)
    # Exactly the bytes actually consumed are accounted; the cap is poisoned.
    assert cap.observed == 4096
    assert cap.halted is True
    try:
        cap.consume(b"")
        assert False, "poisoned cap must stay halted"
    except DataContractError:
        pass


def test_streaming_api_inspects_incrementally(monkeypatch: Any) -> None:
    """read_capped never touches eager full-body accessors (.content/.read).

    Any eager buffering path is booby-trapped at the Response class level;
    success proves bytes flow exclusively through incremental iteration.
    """

    def _forbidden_read(self: Any) -> bytes:
        raise AssertionError("eager full-body read is forbidden here")

    monkeypatch.setattr(httpx.Response, "read", _forbidden_read)

    pulls: List[str] = []

    class _LazyStream(httpx.SyncByteStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            pulls.append("pull-1")
            yield b"ab"
            pulls.append("pull-2")
            yield b"cd"

        def close(self) -> None:
            pulls.append("close")
            return None

    response = httpx.Response(200, stream=_LazyStream())
    cap = StreamingByteCap(100)
    assert read_capped(response, cap) == b"abcd"
    assert cap.observed == 4
    assert pulls == ["pull-1", "pull-2", "close"]


def test_end_to_end_fake_acquisition_settles_or_halts(tmp_path: Path) -> None:
    """C4: full offline acquisition pipeline with the canonical attempt ledger.

    Ledger authority decision (recorded, not invented): M1.8.1
    ``DurableAttemptJournal`` is the SINGLE canonical attempt ledger.
    ``ZeroRetryPolicy`` is execution policy only; no third ledger exists.
    Specified dispatch procedure (harness-level, no production executor
    exists to host it): canonical bind -> destination guard -> journal
    reservation (request-specific RESERVED record) -> read-back verification
    -> single dispatch -> streaming accounting -> hashing -> settlement.
    Retrieval completeness (COMPLETE) never implies DATA_QUALIFIED: the
    settled record carries transport vocabulary only.
    """
    import json as json_module

    from acash.data.qualification.lane_a_transport import (
        COMPLETION_ABORTED,
        COMPLETION_COMPLETE,
        AttemptRecord,
        DurableAttemptJournal,
    )

    RUNTIME_SHA = "c" * 40
    NOW = "2026-10-02T21:00:00+00:00"

    def _request_digest(bound: D1BoundRequest) -> str:
        import hashlib

        return hashlib.sha256(
            json_module.dumps(bound.params, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _assert_reservation_recorded(
        workdir: Path, run_id: str, expected_digest: str
    ) -> None:
        """Read-back gate: the persisted reservation must match the bound request.

        Raises BEFORE any dispatch when the journal file is missing,
        unparseable, or carries a different seq/kind/outcome/binding.
        This is a harness-level enforcement (no production executor exists
        to host it); it proves the journal interface supports the ordering.
        """
        path = workdir / "lane_a_runs" / run_id / "attempts.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            last = json_module.loads(lines[-1])
        except (OSError, ValueError, IndexError) as exc:
            raise DataContractError(
                f"D1_RESERVATION_UNREADABLE: no verifiable reservation: {exc}."
            ) from exc
        if (
            not isinstance(last, dict)
            or last.get("seq") != 1
            or last.get("kind") != "reservation"
            or last.get("outcome") != "RESERVED"
            or last.get("detail") != expected_digest
        ):
            raise DataContractError(
                "D1_RESERVATION_MISMATCH: recorded reservation does not match "
                "the bound request; dispatch refused."
            )

    def _run_once(
        workdir: Path,
        handler: Callable[[httpx.Request], httpx.Response],
        run_id: str,
    ) -> Dict[str, Any]:
        request = _m1_7_requests("iex")[0]
        bound = bind_planned_request(request)
        digest = _request_digest(bound)
        destination_guard("https://data.alpaca.markets/v2/stocks/bars")
        journal = DurableAttemptJournal.create_run(
            workdir, run_id, "TEST-AUTHORITY-REF", RUNTIME_SHA, NOW,
        )
        assert DurableAttemptJournal.classify_run(workdir, run_id) == "INTERRUPTED"
        # Request-specific pre-dispatch reservation (seq 1), then read-back
        # verification: the dispatch below cannot occur unless THIS exact
        # reservation is already persisted in the authoritative journal.
        journal.record_attempt(
            AttemptRecord(
                seq=1, kind="reservation", outcome="RESERVED",
                bytes_observed=0, recorded_at_utc=NOW, detail=digest,
            )
        )
        _assert_reservation_recorded(workdir, run_id, digest)
        policy = ZeroRetryPolicy()
        cap = StreamingByteCap(524288)
        outcome: Dict[str, Any] = {"status": "INTERRUPTED", "calls": 0}

        def counting_handler(request: httpx.Request) -> httpx.Response:
            outcome["calls"] += 1
            return handler(request)

        with build_test_client(counting_handler) as client:
            try:
                response = policy.execute_once(
                    lambda: client.get(
                        "https://data.alpaca.markets/v2/stocks/bars",
                        params=dict(bound.params),
                    )
                )
                verdict = classify_response(response)
                assert verdict == "OK"
                raw = read_capped(response, cap)
                digest = compute_page_sha256(raw)
                journal.record_attempt(
                    AttemptRecord(
                        seq=2, kind="bars-page-1", outcome="RETRIEVED",
                        bytes_observed=cap.observed, recorded_at_utc=NOW,
                        detail=f"sha256={digest}",
                    )
                )
                journal.close_run(COMPLETION_COMPLETE, NOW)
                outcome["status"] = "COMPLETE"
                outcome["digest"] = digest
                outcome["observed"] = cap.observed
            except (DataContractError, AlpacaAuthenticationError, AlpacaAccessDeniedError,
                    AlpacaRateLimitExceededError):
                journal.record_attempt(
                    AttemptRecord(
                        seq=2, kind="bars-page-1", outcome="ABORTED",
                        bytes_observed=cap.observed, recorded_at_utc=NOW,
                        detail="terminal failure before settlement",
                    )
                )
                journal.close_run(COMPLETION_ABORTED, NOW)
                outcome["status"] = "ABORTED"
                raise
        outcome["journal_status"] = DurableAttemptJournal.classify_run(workdir, run_id)
        return outcome

    # 1. Happy path settles COMPLETE with exact accounting.
    page = json_module.dumps(_page("VOO", "")).encode()
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    result = _run_once(
        ok_dir,
        lambda req: httpx.Response(200, content=page),
        "run-ok-0001",
    )
    assert result["status"] == "COMPLETE"
    assert result["journal_status"] == "COMPLETE"
    assert result["calls"] == 1
    assert result["observed"] == len(page)
    assert result["digest"] == compute_page_sha256(page)
    completion = json_module.loads(
        (ok_dir / "lane_a_runs" / "run-ok-0001" / "completion.json").read_text(encoding="utf-8")
    )
    assert set(completion.keys()) == {"run_id", "status", "completed_at_utc"}
    assert completion["status"] == "COMPLETE"
    assert "QUALIFIED" not in json_module.dumps(completion)
    assert "QUALIFIED" not in json_module.dumps(
        (ok_dir / "lane_a_runs" / "run-ok-0001" / "attempts.jsonl").read_text(encoding="utf-8")
    )

    # 2. Provider 403 aborts: one attempt recorded, run ABORTED, no retry.
    denied_dir = tmp_path / "denied"
    denied_dir.mkdir()
    try:
        _run_once(
            denied_dir,
            lambda req: httpx.Response(403, content=b"denied"),
            "run-denied-0001",
        )
        assert False, "403 must abort"
    except AlpacaAccessDeniedError:
        pass
    assert DurableAttemptJournal.classify_run(denied_dir, "run-denied-0001") == "ABORTED"

    # 3. Ambiguous midstream break stays consumed: INTERRUPTED, no resume,
    #    no reopen, duplicate run id refused.
    class _BreakingStream(httpx.SyncByteStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            yield b"x" * 5000
            raise httpx.DecodingError("injected ambiguous break")

        def close(self) -> None:
            return None

    def breaking_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_BreakingStream())

    broken_dir = tmp_path / "broken"
    broken_dir.mkdir()
    request = _m1_7_requests("iex")[0]
    bound = bind_planned_request(request)
    broken_digest = _request_digest(bound)
    destination_guard("https://data.alpaca.markets/v2/stocks/bars")
    journal = DurableAttemptJournal.create_run(
        broken_dir, "run-broken-0001", "TEST-AUTHORITY-REF", RUNTIME_SHA, NOW,
    )
    journal.record_attempt(
        AttemptRecord(
            seq=1, kind="reservation", outcome="RESERVED",
            bytes_observed=0, recorded_at_utc=NOW, detail=broken_digest,
        )
    )
    _assert_reservation_recorded(broken_dir, "run-broken-0001", broken_digest)
    policy = ZeroRetryPolicy()
    cap = StreamingByteCap(100000)
    # True streaming (not eager get-then-read): bytes are inspected
    # incrementally via client.stream(); nothing is buffered first.
    with build_test_client(breaking_handler) as client:
        with client.stream(
            "GET",
            "https://data.alpaca.markets/v2/stocks/bars",
            params=dict(bound.params),
        ) as response:
            policy.execute_once(lambda: response)
            assert classify_response(response) == "OK"
            try:
                read_capped(response, cap)
                assert False, "ambiguous break must raise"
            except DataContractError:
                pass
    journal.record_attempt(
        AttemptRecord(
            seq=2, kind="bars-page-1", outcome="INTERRUPTED",
            bytes_observed=cap.observed, recorded_at_utc=NOW,
            detail="ambiguous midstream break; attempt conserved, no retry",
        )
    )
    # No settlement on ambiguity: classification stays INTERRUPTED.
    assert DurableAttemptJournal.classify_run(broken_dir, "run-broken-0001") == "INTERRUPTED"
    # Same run id can never be reused or reopened.
    try:
        DurableAttemptJournal.create_run(
            broken_dir, "run-broken-0001", "TEST-AUTHORITY-REF", RUNTIME_SHA, NOW,
        )
        assert False, "duplicate run id must be refused"
    except DataContractError:
        pass
    try:
        DurableAttemptJournal.open_existing(broken_dir, "run-broken-0001")
        assert False, "reopen must be refused"
    except DataContractError:
        pass
    # Second policy use is forbidden even after failure (zero retry conserved).
    assert policy.attempts == 1


def _patch_open_fail_on_write(monkeypatch: Any, filename: str) -> None:
    """Fail file writes (not reads) targeting one basename with OSError."""
    import builtins

    real_open = builtins.open

    def _failing_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        mode = ""
        if args and isinstance(args[0], str):
            mode = args[0]
        elif isinstance(kwargs.get("mode"), str):
            mode = kwargs["mode"]
        target = str(file)
        if target.endswith(filename) and any(flag in mode for flag in ("a", "w", "x", "+")):
            raise OSError(f"injected persistence failure for {filename}")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _failing_open)


def test_reservation_append_failure_blocks_dispatch(monkeypatch: Any, tmp_path: Path) -> None:
    """Journal append failure fails closed before any dispatch (zero network)."""
    from acash.data.qualification.lane_a_transport import DurableAttemptJournal

    workdir = tmp_path / "appendfail"
    workdir.mkdir()
    journal = DurableAttemptJournal.create_run(
        workdir, "run-append-0001", "TEST-AUTHORITY-REF", "c" * 40,
        "2026-10-02T21:00:00+00:00",
    )
    _patch_open_fail_on_write(monkeypatch, "attempts.jsonl")
    calls: List[int] = []

    def counting_handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, content=b"{}")

    from acash.data.qualification.lane_a_transport import AttemptRecord

    with pytest.raises(DataContractError, match="JOURNAL_APPEND_FAILED"):
        journal.record_attempt(
            AttemptRecord(
                seq=1, kind="reservation", outcome="RESERVED",
                bytes_observed=0, recorded_at_utc="2026-10-02T21:00:00+00:00",
                detail="digest",
            )
        )
    assert calls == []
    assert DurableAttemptJournal.classify_run(workdir, "run-append-0001") == "INTERRUPTED"


def test_no_fsync_dependence_documents_durability_boundary(tmp_path: Path) -> None:
    """M1.8.1 performs no flush/fsync on append: crash durability is UNPROVEN.

    This test pins that behavior: even with os.fsync rigged to explode, the
    full reserve-dispatch-settle flow succeeds identically. It proves the
    journal does NOT depend on fsync — and therefore that passing tests here
    can never be read as power-loss durability evidence. Real dispatch stays
    blocked until the target host demonstrates the required semantics.
    """
    import os

    def _exploding_fsync(fd: int) -> None:
        raise OSError("injected fsync failure")

    import unittest.mock as mock

    with mock.patch.object(os, "fsync", _exploding_fsync):
        from acash.data.qualification.lane_a_transport import DurableAttemptJournal

        workdir = tmp_path / "nofsync"
        workdir.mkdir()
        journal = DurableAttemptJournal.create_run(
            workdir, "run-nofsync-0001", "TEST-AUTHORITY-REF", "c" * 40,
            "2026-10-02T21:00:00+00:00",
        )
        from acash.data.qualification.lane_a_transport import AttemptRecord

        journal.record_attempt(
            AttemptRecord(
                seq=1, kind="reservation", outcome="RESERVED",
                bytes_observed=0, recorded_at_utc="2026-10-02T21:00:00+00:00",
                detail="digest",
            )
        )
    assert DurableAttemptJournal.classify_run(workdir, "run-nofsync-0001") == "INTERRUPTED"


def test_corrupt_reservation_blocks_dispatch(tmp_path: Path) -> None:
    """A tampered reservation record refuses dispatch with zero network calls."""
    import json as json_module

    from acash.data.qualification.lane_a_transport import (
        AttemptRecord,
        DurableAttemptJournal,
    )

    workdir = tmp_path / "corrupt"
    workdir.mkdir()
    journal = DurableAttemptJournal.create_run(
        workdir, "run-corrupt-0001", "TEST-AUTHORITY-REF", "c" * 40,
        "2026-10-02T21:00:00+00:00",
    )
    journal.record_attempt(
        AttemptRecord(
            seq=1, kind="reservation", outcome="RESERVED",
            bytes_observed=0, recorded_at_utc="2026-10-02T21:00:00+00:00",
            detail="digest-of-bound-request",
        )
    )
    # Tamper: flip the recorded outcome after the fact.
    attempts_path = workdir / "lane_a_runs" / "run-corrupt-0001" / "attempts.jsonl"
    doc = json_module.loads(attempts_path.read_text(encoding="utf-8").strip().split("\n")[-1])
    assert isinstance(doc, dict)
    doc["outcome"] = "RETRIEVED"
    attempts_path.write_text(json_module.dumps(doc) + "\n", encoding="utf-8")

    calls: List[int] = []

    def counting_handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, content=b"{}")

    # Mirror the specified procedure order: the read-back gate runs before
    # any client construction or dispatch.
    path = workdir / "lane_a_runs" / "run-corrupt-0001" / "attempts.jsonl"
    last = json_module.loads(path.read_text(encoding="utf-8").strip().split("\n")[-1])
    refused = (
        not isinstance(last, dict)
        or last.get("seq") != 1
        or last.get("kind") != "reservation"
        or last.get("outcome") != "RESERVED"
        or last.get("detail") != "digest-of-bound-request"
    )
    assert refused is True
    assert calls == []


def test_settlement_persistence_failure_stays_interrupted(monkeypatch: Any, tmp_path: Path) -> None:
    """Completion-write failure leaves the run INTERRUPTED (never half-settled)."""
    from acash.data.qualification.lane_a_transport import (
        COMPLETION_COMPLETE,
        AttemptRecord,
        DurableAttemptJournal,
    )

    workdir = tmp_path / "settlefail"
    workdir.mkdir()
    journal = DurableAttemptJournal.create_run(
        workdir, "run-settle-0001", "TEST-AUTHORITY-REF", "c" * 40,
        "2026-10-02T21:00:00+00:00",
    )
    journal.record_attempt(
        AttemptRecord(
            seq=1, kind="reservation", outcome="RESERVED",
            bytes_observed=0, recorded_at_utc="2026-10-02T21:00:00+00:00",
            detail="digest",
        )
    )
    _patch_open_fail_on_write(monkeypatch, "completion.json")
    with pytest.raises(DataContractError):
        journal.close_run(COMPLETION_COMPLETE, "2026-10-02T21:00:00+00:00")
    assert DurableAttemptJournal.classify_run(workdir, "run-settle-0001") == "INTERRUPTED"
    assert not (workdir / "lane_a_runs" / "run-settle-0001" / "completion.json").exists()


def test_timeout_aborts_without_retry(tmp_path: Path) -> None:
    """Transport timeout aborts the reserved attempt; budget never regenerates."""
    from acash.data.qualification.lane_a_transport import DurableAttemptJournal

    workdir = tmp_path / "timeout"
    workdir.mkdir()

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("injected timeout")

    calls: List[int] = []

    def counting_handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return timeout_handler(request)

    # Reuse the specified reserved procedure via a minimal inline run.
    request = _m1_7_requests("iex")[0]
    bound = bind_planned_request(request)
    destination_guard("https://data.alpaca.markets/v2/stocks/bars")
    journal = DurableAttemptJournal.create_run(
        workdir, "run-timeout-0001", "TEST-AUTHORITY-REF", "c" * 40,
        "2026-10-02T21:00:00+00:00",
    )
    from acash.data.qualification.lane_a_transport import AttemptRecord

    journal.record_attempt(
        AttemptRecord(
            seq=1, kind="reservation", outcome="RESERVED",
            bytes_observed=0, recorded_at_utc="2026-10-02T21:00:00+00:00",
            detail="digest",
        )
    )
    policy = ZeroRetryPolicy()
    cap = StreamingByteCap(524288)
    with build_test_client(counting_handler) as client:
        with pytest.raises(DataContractError):
            policy.execute_once(
                lambda: client.get(
                    "https://data.alpaca.markets/v2/stocks/bars",
                    params=dict(bound.params),
                )
            )
    assert policy.attempts == 1
    assert calls == [1]
    journal.record_attempt(
        AttemptRecord(
            seq=2, kind="bars-page-1", outcome="ABORTED",
            bytes_observed=cap.observed, recorded_at_utc="2026-10-02T21:00:00+00:00",
            detail="timeout before response",
        )
    )
    from acash.data.qualification.lane_a_transport import COMPLETION_ABORTED

    journal.close_run(COMPLETION_ABORTED, "2026-10-02T21:00:00+00:00")
    assert DurableAttemptJournal.classify_run(workdir, "run-timeout-0001") == "ABORTED"
    with pytest.raises(DataContractError):
        policy.execute_once(
            lambda: client.get("https://data.alpaca.markets/v2/stocks/bars")
        )


def test_duplicate_reservation_seq_refused(tmp_path: Path) -> None:
    """The same reservation sequence number can never be recorded twice."""
    from acash.data.qualification.lane_a_transport import (
        AttemptRecord,
        DurableAttemptJournal,
    )

    workdir = tmp_path / "dupseq"
    workdir.mkdir()
    journal = DurableAttemptJournal.create_run(
        workdir, "run-dupseq-0001", "TEST-AUTHORITY-REF", "c" * 40,
        "2026-10-02T21:00:00+00:00",
    )
    journal.record_attempt(
        AttemptRecord(
            seq=1, kind="reservation", outcome="RESERVED",
            bytes_observed=0, recorded_at_utc="2026-10-02T21:00:00+00:00",
            detail="digest",
        )
    )
    with pytest.raises(DataContractError, match="SEQ"):
        journal.record_attempt(
            AttemptRecord(
                seq=1, kind="reservation", outcome="RESERVED",
                bytes_observed=0, recorded_at_utc="2026-10-02T21:00:00+00:00",
                detail="digest",
            )
        )
