"""Adversarial tests for the offline Scope -> D5-candidate harness (MockTransport only)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.d5_offline_harness import (
    HARNESS_LABEL,
    D5HarnessScope,
    replay_d5_harness_run,
    run_d5_offline_harness,
)
from acash.data.qualification.lane_b_d5_rehearsal import (
    D5AdmissionAuthority,
    D5AdmissionVerdict,
    D5AuthorityProvenance,
    D5AuthorityStatus,
    D5DividendRecord,
    DatasetOrigin,
)

SESSIONS = tuple(date(2026, 9, 28) + timedelta(days=i) for i in range(5))
SYMBOLS = ("BIL", "BND", "GLD", "VOO")
CREATED = "2026-10-23T12:00:00+00:00"
RUNTIME_SHA = "f" * 40
CREDENTIAL_HEADERS = ("apca-api-key-id", "apca-api-secret-key", "authorization")

PageSpec = tuple[Sequence[date], Sequence[str], str | None]


def _authority(**overrides: object) -> D5AdmissionAuthority:
    base: dict[str, object] = {
        "status": D5AuthorityStatus.ISSUED,
        "provenance": D5AuthorityProvenance.TEST_FIXTURE,
        "authority_ref": "TEST_D5_HARNESS_AUTHORITY",
        "provider": "ALPACA",
        "feed": "sip",
        "timeframe": "1Day",
        "symbols": SYMBOLS,
        "start_date": SESSIONS[0],
        "end_date": SESSIONS[-1],
        "adjustments": ("raw", "split"),
        "max_http_requests": 4,
        "max_observed_bytes": 100_000,
        "issued_at_utc": datetime(2026, 10, 20, tzinfo=timezone.utc),
        "expires_at_utc": datetime(2026, 12, 31, tzinfo=timezone.utc),
        "approval_reference": "TEST_APPROVAL_REFERENCE",
    }
    base.update(overrides)
    return D5AdmissionAuthority(**base)  # type: ignore[arg-type]


def _dividend(symbol: str, ex: date, pay: date, amount: str) -> D5DividendRecord:
    return D5DividendRecord(
        symbol=symbol,
        ex_date=ex,
        record_date=ex,
        payable_date=pay,
        amount_per_share=Decimal(amount),
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
        source_row_ref=f"synthetic:{symbol.lower()}:{ex.isoformat()}",
        pit_vintage_known=True,
    )


def _scope(authority: D5AdmissionAuthority | None = None, asof: Any = date(2026, 10, 2)) -> D5HarnessScope:
    return D5HarnessScope(
        authority=authority or _authority(),
        asof=asof,
        dividends=(
            _dividend("BIL", date(2026, 10, 1), date(2026, 10, 5), "0.228000"),
            _dividend("BND", date(2026, 10, 1), date(2026, 10, 5), "0.237328"),
            _dividend("VOO", date(2026, 9, 30), date(2026, 10, 2), "1.740000"),
        ),
        expected_ex_dates={
            "BIL": (date(2026, 10, 1),),
            "BND": (date(2026, 10, 1),),
            "VOO": (date(2026, 9, 30),),
        },
    )


def _body(sessions: Sequence[date], symbols: Sequence[str], next_token: str | None) -> bytes:
    bars = {
        symbol: [
            {
                "t": datetime(d.year, d.month, d.day, 13, 30, tzinfo=timezone.utc).isoformat(),
                "o": "100", "h": "100", "l": "100", "c": "100", "v": 1000,
            }
            for d in sessions
        ]
        for symbol in symbols
    }
    return json.dumps({"bars": bars, "next_page_token": next_token}, separators=(",", ":")).encode()


class _Body(httpx.SyncByteStream):
    """Lazy body so responses stay unconsumed until the harness streams them."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __iter__(self) -> Iterator[bytes]:
        yield self._body


class _Recorder:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []


def _transport(
    chains: dict[str, list[PageSpec]] | None = None,
    *,
    recorder: _Recorder | None = None,
    respond: Callable[[httpx.Request, bytes], httpx.Response] | None = None,
) -> httpx.MockTransport:
    chains = chains or {adj: [(SESSIONS, SYMBOLS, None)] for adj in ("raw", "split")}

    def handler(request: httpx.Request) -> httpx.Response:
        if recorder is not None:
            recorder.requests.append(request)
        adjustment = request.url.params["adjustment"]
        token = request.url.params.get("page_token")
        chain = chains[adjustment]
        index = 0 if token is None else 1 + [spec[2] for spec in chain].index(token)
        sessions, symbols, next_token = chain[index]
        body = _body(sessions, symbols, next_token)
        if respond is not None:
            return respond(request, body)
        return httpx.Response(200, stream=_Body(body), headers={"content-length": str(len(body))})

    return httpx.MockTransport(handler)


def _run(tmp_path: Path, transport: httpx.MockTransport, scope: D5HarnessScope | None = None, run_id: str = "run1") -> Any:
    return run_d5_offline_harness(
        scope or _scope(),
        transport,
        evidence_root=tmp_path,
        run_id=run_id,
        runtime_sha=RUNTIME_SHA,
        created_at_utc=CREATED,
    )


def _completed(tmp_path: Path, run_id: str = "run1") -> bool:
    return (tmp_path / "lane_a_runs" / run_id / "completion.json").is_file()


def test_happy_path_produces_reproducible_synthetic_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APCA_API_KEY_ID", "should-never-be-sent")
    recorder = _Recorder()
    result = _run(tmp_path, _transport(recorder=recorder))
    assert result.admission.verdict is D5AdmissionVerdict.SYNTHETIC_ONLY
    assert result.admission.manifest["origin"] == DatasetOrigin.SYNTHETIC_FIXTURE.value
    assert result.manifest["label"] == HARNESS_LABEL
    assert result.manifest["real_data_admitted"] is False
    assert result.operations_used == 2 and result.planned_min_requests == 2
    assert _completed(tmp_path)
    for request in recorder.requests:
        assert request.url.params["asof"] == "2026-10-02"
        assert request.url.params["limit"] == "1000"
        assert request.headers["accept-encoding"] == "identity"
        assert not any(h in request.headers for h in CREDENTIAL_HEADERS)
    replayed = replay_d5_harness_run(_scope(), result, evidence_root=tmp_path, created_at_utc=CREATED)
    assert replayed.dataset_sha256 == result.admission.dataset_sha256
    again = _run(tmp_path, _transport(), run_id="run2")
    assert again.admission.dataset_sha256 == result.admission.dataset_sha256
    assert again.scope_sha256 == result.scope_sha256


def test_short_page_with_token_and_cross_symbol_pagination(tmp_path: Path) -> None:
    chains: dict[str, list[PageSpec]] = {
        "raw": [(SESSIONS, ("BIL", "BND"), "p2"), (SESSIONS, ("GLD", "VOO"), None)],
        "split": [(SESSIONS[:2], SYMBOLS, "s2"), (SESSIONS[2:], SYMBOLS, None)],
    }
    result = _run(tmp_path, _transport(chains))
    assert result.operations_used == 4
    assert result.admission.verdict is D5AdmissionVerdict.SYNTHETIC_ONLY, result.admission.blockers


@pytest.mark.parametrize(
    "raw_chain",
    [
        [(SESSIONS, SYMBOLS, "a"), (SESSIONS, SYMBOLS, "a")],
        [(SESSIONS[:2], SYMBOLS, "a"), (SESSIONS[2:3], SYMBOLS, "b"), (SESSIONS[3:], SYMBOLS, "a")],
    ],
    ids=["self_cycle", "duplicate_token"],
)
def test_pagination_cycles_fail_closed(tmp_path: Path, raw_chain: list[PageSpec]) -> None:
    chains: dict[str, list[PageSpec]] = {"raw": raw_chain, "split": [(SESSIONS, SYMBOLS, None)]}
    with pytest.raises(DataContractError, match="D5_HARNESS_PAGE_TOKEN_CYCLE|CANARY_BUDGET"):
        _run(tmp_path, _transport(chains), _scope(_authority(max_http_requests=8)))
    assert not _completed(tmp_path)


def test_truncated_pagination_is_not_qualified(tmp_path: Path) -> None:
    chains: dict[str, list[PageSpec]] = {
        "raw": [(SESSIONS[:3], SYMBOLS, None)],
        "split": [(SESSIONS, SYMBOLS, None)],
    }
    result = _run(tmp_path, _transport(chains))
    assert result.admission.verdict is D5AdmissionVerdict.BLOCKED


@pytest.mark.parametrize(
    "build",
    [
        lambda: _scope(_authority(adjustments=("raw",))),
        lambda: _scope(asof=None),
        lambda: _scope(asof="2026-10-02"),
        lambda: _scope(asof=datetime(2026, 10, 2, tzinfo=timezone.utc)),
        lambda: _scope(asof=date(2026, 9, 1)),
        lambda: _scope(_authority(provenance=D5AuthorityProvenance.OPERATOR_ISSUED)),
    ],
    ids=["one_adjustment", "asof_missing", "asof_string", "asof_datetime", "asof_before_end", "real_authority"],
)
def test_scope_contract_fails_closed(build: Callable[[], D5HarnessScope]) -> None:
    with pytest.raises(DataContractError):
        build()


def test_scope_digest_binds_asof() -> None:
    assert _scope().digest() != _scope(asof=date(2026, 10, 3)).digest()


def test_real_transport_refused_before_any_artifact(tmp_path: Path) -> None:
    with pytest.raises(DataContractError, match="D5_HARNESS_NETWORK_REFUSED"):
        _run(tmp_path, httpx.HTTPTransport())  # type: ignore[arg-type]
    assert not (tmp_path / "lane_a_runs").exists()


def test_budget_insufficient_before_dispatch_and_exhaustion_at_runtime(tmp_path: Path) -> None:
    with pytest.raises(DataContractError, match="D5_HARNESS_BUDGET_INSUFFICIENT"):
        _run(tmp_path, _transport(), _scope(_authority(max_http_requests=1)))
    assert not (tmp_path / "lane_a_runs").exists()
    chains: dict[str, list[PageSpec]] = {
        "raw": [(SESSIONS[:2], SYMBOLS, "p2"), (SESSIONS[2:], SYMBOLS, None)],
        "split": [(SESSIONS, SYMBOLS, None)],
    }
    with pytest.raises(DataContractError, match="CANARY_BUDGET_OPERATIONS_EXHAUSTED"):
        _run(tmp_path, _transport(chains), _scope(_authority(max_http_requests=2)))
    assert not _completed(tmp_path)


def _with_headers(**headers: str) -> Callable[[httpx.Request, bytes], httpx.Response]:
    def respond(_: httpx.Request, body: bytes) -> httpx.Response:
        return httpx.Response(200, stream=_Body(body), headers=headers)

    return respond


@pytest.mark.parametrize(
    ("respond", "code"),
    [
        (_with_headers(**{"content-length": "12a"}), "D3_CONTENT_LENGTH_MALFORMED"),
        (_with_headers(**{"content-encoding": "gzip"}), "D3_IDENTITY_ENCODING_REJECTED"),
        (_with_headers(**{"content-length": "1"}), "D3_BODY_LENGTH_MISMATCH"),
        (lambda _r, _b: httpx.Response(429), "D5_HARNESS_HALTED_HTTP_429"),
        (lambda _r, _b: httpx.Response(500), "D5_HARNESS_UNEXPECTED_STATUS"),
        (lambda _r, _b: httpx.Response(200, stream=_Body(b"\xff\xfe")), "D5_HARNESS_MALFORMED_PAGE"),
    ],
    ids=["content_length", "encoding", "length_mismatch", "http_429", "http_500", "bad_utf8"],
)
def test_response_contract_violations_fail_closed(
    tmp_path: Path, respond: Callable[[httpx.Request, bytes], httpx.Response], code: str
) -> None:
    with pytest.raises(DataContractError, match=code):
        _run(tmp_path, _transport(respond=respond))
    assert not _completed(tmp_path)


def test_oversized_response_breaches_byte_cap(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        _run(tmp_path, _transport(), _scope(_authority(max_observed_bytes=200)))
    assert not _completed(tmp_path)


class _InterruptedStream(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield b'{"bars":'
        raise httpx.ReadError("synthetic interruption")


def test_stream_interruption_leaves_run_interrupted_and_id_unusable(tmp_path: Path) -> None:
    def respond(_: httpx.Request, __: bytes) -> httpx.Response:
        return httpx.Response(200, stream=_InterruptedStream())

    with pytest.raises(DataContractError, match="D3_STREAM_INTERRUPTED"):
        _run(tmp_path, _transport(respond=respond))
    assert not _completed(tmp_path)
    with pytest.raises(DataContractError):
        _run(tmp_path, _transport())


def test_receipt_tampering_breaks_replay(tmp_path: Path) -> None:
    result = _run(tmp_path, _transport())
    raw_file = tmp_path / "lane_a_runs" / "run1" / "seq_0001.bin"
    raw_file.chmod(0o644)
    raw_file.write_bytes(raw_file.read_bytes().replace(b'"100"', b'"999"', 1))
    with pytest.raises(DataContractError, match="D5_HARNESS_REPLAY_NOT_ADMISSIBLE"):
        replay_d5_harness_run(_scope(), result, evidence_root=tmp_path, created_at_utc=CREATED)
