"""Adversarial tests for the Lane A offline acquisition rehearsal (M1.8).

Attack order: happy path -> boundary -> malformed -> contradictory ->
adversarial -> fail-closed. NETWORK is never touched: every transport here
is a synthetic fake; a raising transport proves zero-network paths. No
credentials are loaded anywhere in this file; the rehearsal protocol carries
no auth headers by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import List, Optional, Sequence, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.lane_a_authority import (
    LANE_A_MAX_TOTAL_PAYLOAD_BYTES,
    LaneAAuthority,
    LaneAAuthorityStatus,
    LaneARequestLedger,
    build_lane_a_scope,
)
from acash.data.qualification.lane_a_rehearsal import (
    RehearsalHttpResponse,
    RehearsalTransportError,
    RehearsalVerdict,
    run_rehearsal,
)

NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
APPROVED_AT = datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc)
ISSUED_AT = datetime(2026, 10, 13, 0, 30, 0, tzinfo=timezone.utc)
EXPIRES_AT = datetime(2026, 10, 14, 0, 0, 0, tzinfo=timezone.utc)
RUNTIME_SHA = "a" * 40

SESSIONS = [
    date(2026, 9, 28),
    date(2026, 9, 29),
    date(2026, 9, 30),
    date(2026, 10, 1),
    date(2026, 10, 2),
]
SYMBOLS = ("VOO", "BND", "GLD", "BIL")


def _authority(
    status: LaneAAuthorityStatus = LaneAAuthorityStatus.ISSUED,
    max_ops: int = 12,
    max_bytes: int = LANE_A_MAX_TOTAL_PAYLOAD_BYTES,
    feed: str = "iex",
) -> LaneAAuthority:
    return LaneAAuthority(
        status=status,
        scope=build_lane_a_scope(feed),
        max_http_operations=max_ops,
        max_total_payload_bytes=max_bytes,
        issued_at_utc=ISSUED_AT,
        expires_at_utc=EXPIRES_AT,
        approval_reference="OP-APPROVAL-TEST-001",
        approved_at_utc=APPROVED_AT,
    )


def _bar_payload(
    sessions: Sequence[date] = SESSIONS,
    symbols: Sequence[str] = SYMBOLS,
    token: Optional[str] = None,
) -> bytes:
    import json

    bars = {
        symbol: [
            {
                "t": f"{day.isoformat()}T13:30:00+00:00",
                "o": 100,
                "h": 101,
                "l": 99,
                "c": 100.5,
                "v": 1000,
            }
            for day in sessions
        ]
        for symbol in symbols
    }
    return json.dumps({"bars": bars, "next_page_token": token}).encode("utf-8")


@dataclass
class FakeTransport:
    """Scripted synthetic transport; records every call for budget proofs."""

    calls: List[Tuple[str, Tuple[Tuple[str, str], ...]]] = field(default_factory=list)
    script: List[object] = field(default_factory=list)

    def get(
        self, path: str, params: Sequence[Tuple[str, str]]
    ) -> RehearsalHttpResponse:
        self.calls.append((path, tuple(params)))
        if not self.script:
            raise AssertionError("FakeTransport script exhausted: unexpected request.")
        action = self.script.pop(0)
        if isinstance(action, Exception):
            raise action
        assert isinstance(action, RehearsalHttpResponse)
        return action


def _ok(content: bytes) -> RehearsalHttpResponse:
    return RehearsalHttpResponse(status_code=200, content=content, headers={})


class TestHappyPath:
    def test_full_run_passes_with_complete_coverage(self) -> None:
        transport = FakeTransport(
            script=[_ok(_bar_payload()), _ok(_bar_payload())]
        )
        manifest, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.PASS
        assert manifest.planned_operations == 2
        assert manifest.dispatched_operations == 2
        assert manifest.network_requests_issued == 2
        assert len(manifest.receipts) == 2
        assert manifest.runtime_commit_sha == RUNTIME_SHA
        assert manifest.authority_reference == "OP-APPROVAL-TEST-001"
        assert len(transport.calls) == 2

    def test_multi_page_pagination_to_exhaustion(self) -> None:
        first = _bar_payload(SESSIONS[:3])
        second = _bar_payload(SESSIONS[3:])
        import json

        first_doc = json.loads(first.decode("utf-8"))
        first_doc["next_page_token"] = "page2"
        first = json.dumps(first_doc).encode("utf-8")
        transport = FakeTransport(
            script=[_ok(first), _ok(second), _ok(_bar_payload())]
        )
        manifest, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.PASS
        assert manifest.dispatched_operations == 3
        # Continuation echoes the base query with the verbatim cursor.
        _, continuation_params = transport.calls[1]
        params = dict(continuation_params)
        assert params["page_token"] == "page2"
        assert params["symbols"] == "BIL,BND,GLD,VOO"

    def test_deterministic_manifests(self) -> None:
        def run_once() -> object:
            transport = FakeTransport(
                script=[_ok(_bar_payload()), _ok(_bar_payload())]
            )
            return run_rehearsal(
                authority=_authority(),
                transport=transport,
                runtime_sha=RUNTIME_SHA,
                now_utc=NOW,
            )[0]

        assert run_once() == run_once()

    def test_scope_digest_stable(self) -> None:
        transport = FakeTransport(
            script=[_ok(_bar_payload()), _ok(_bar_payload())]
        )
        manifest, _ = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert len(manifest.scope_digest) == 64


class TestFailClosedAuthority:
    def test_missing_authority_raises_before_network(self) -> None:
        transport = FakeTransport(script=[])
        with pytest.raises(DataContractError):
            run_rehearsal(
                authority=None,
                transport=transport,
                runtime_sha=RUNTIME_SHA,
                now_utc=NOW,
            )
        assert transport.calls == []

    def test_unissued_authority_raises_before_network(self) -> None:
        transport = FakeTransport(script=[])
        with pytest.raises(DataContractError):
            run_rehearsal(
                authority=_authority(status=LaneAAuthorityStatus.UNISSUED),
                transport=transport,
                runtime_sha=RUNTIME_SHA,
                now_utc=NOW,
            )
        assert transport.calls == []

    def test_malformed_runtime_sha_raises_before_network(self) -> None:
        transport = FakeTransport(script=[])
        with pytest.raises(DataContractError):
            run_rehearsal(
                authority=_authority(),
                transport=transport,
                runtime_sha="not-a-sha",
                now_utc=NOW,
            )
        assert transport.calls == []

    def test_naive_now_raises(self) -> None:
        transport = FakeTransport(script=[])
        with pytest.raises(DataContractError):
            run_rehearsal(
                authority=_authority(),
                transport=transport,
                runtime_sha=RUNTIME_SHA,
                now_utc=datetime(2026, 10, 13, 12, 0, 0),
            )
        assert transport.calls == []


class TestExecutionVerdicts:
    def test_entitlement_denial_blocks_without_evidence(self) -> None:
        transport = FakeTransport(
            script=[
                RehearsalHttpResponse(status_code=401, content=b"{}", headers={}),
                _ok(_bar_payload()),
            ]
        )
        manifest, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.BLOCKED
        assert manifest.dispatched_operations == 1
        assert manifest.receipts == ()

    def test_rate_limit_blocks_without_retry(self) -> None:
        transport = FakeTransport(
            script=[
                RehearsalHttpResponse(status_code=429, content=b"{}", headers={}),
            ]
        )
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.BLOCKED

    def test_server_error_blocks(self) -> None:
        transport = FakeTransport(
            script=[
                RehearsalHttpResponse(status_code=500, content=b"{}", headers={}),
            ]
        )
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.BLOCKED

    def test_unexpected_status_rejects(self) -> None:
        transport = FakeTransport(
            script=[
                RehearsalHttpResponse(status_code=418, content=b"{}", headers={}),
            ]
        )
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.REJECTED

    def test_transport_timeout_blocks_and_conserves_budget(self) -> None:
        transport = FakeTransport(
            script=[RehearsalTransportError("simulated timeout")]
        )
        manifest, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.BLOCKED
        assert manifest.dispatched_operations == 1

    def test_invalid_json_rejects(self) -> None:
        transport = FakeTransport(
            script=[_ok(b"not-json{{{")]
        )
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.REJECTED

    def test_missing_symbol_rejects(self) -> None:
        transport = FakeTransport(
            script=[
                _ok(_bar_payload(symbols=("VOO", "BND", "GLD"))),
                _ok(_bar_payload()),
            ]
        )
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.REJECTED

    def test_duplicate_cursor_rejects(self) -> None:
        import json

        first = _bar_payload(SESSIONS[:3])
        doc = json.loads(first.decode("utf-8"))
        doc["next_page_token"] = "loop"
        first = json.dumps(doc).encode("utf-8")
        second = _bar_payload(SESSIONS[3:])
        doc2 = json.loads(second.decode("utf-8"))
        doc2["next_page_token"] = "loop"
        second = json.dumps(doc2).encode("utf-8")
        transport = FakeTransport(script=[_ok(first), _ok(second)])
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.REJECTED

    def test_off_calendar_bar_rejects(self) -> None:
        transport = FakeTransport(
            script=[
                _ok(_bar_payload(sessions=[date(2026, 9, 27)])),
                _ok(_bar_payload()),
            ]
        )
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.REJECTED

    def test_non_monotonic_bars_reject(self) -> None:
        transport = FakeTransport(
            script=[
                _ok(_bar_payload(sessions=list(reversed(SESSIONS)))),
                _ok(_bar_payload()),
            ]
        )
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.REJECTED

    def test_duplicate_bar_dates_reject(self) -> None:
        transport = FakeTransport(
            script=[
                _ok(_bar_payload(sessions=SESSIONS + [SESSIONS[0]])),
                _ok(_bar_payload()),
            ]
        )
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.REJECTED

    def test_naive_bar_timestamp_rejects(self) -> None:
        import json

        bars = [
            {
                "t": "2026-09-28T13:30:00",
                "o": 100,
                "h": 101,
                "l": 99,
                "c": 100.5,
                "v": 1000,
            }
        ]
        body = json.dumps(
            {"bars": {symbol: bars for symbol in SYMBOLS}, "next_page_token": None}
        ).encode("utf-8")
        transport = FakeTransport(script=[_ok(body), _ok(_bar_payload())])
        _, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.REJECTED


class TestBudgetExhaustion:
    def test_operation_budget_partial(self) -> None:
        first = _bar_payload(SESSIONS[:3])
        import json

        doc = json.loads(first.decode("utf-8"))
        doc["next_page_token"] = "page2"
        first = json.dumps(doc).encode("utf-8")
        transport = FakeTransport(
            script=[_ok(first), _ok(_bar_payload(SESSIONS[3:]))]
        )
        manifest, verdict = run_rehearsal(
            authority=_authority(max_ops=2),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.PARTIAL
        assert manifest.dispatched_operations == 2
        assert len(transport.calls) == 2

    def test_byte_budget_partial_with_overrun_receipt(self) -> None:
        transport = FakeTransport(
            script=[_ok(_bar_payload()), _ok(_bar_payload())]
        )
        manifest, verdict = run_rehearsal(
            authority=_authority(max_bytes=10),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
        )
        assert verdict is RehearsalVerdict.PARTIAL
        assert manifest.receipts[-1].outcome == "BYTE_OVERRUN"


    def test_looser_ledger_than_authority_rejected(self) -> None:
        ledger = LaneARequestLedger(
            max_http_operations=12,
            max_total_payload_bytes=10_000_000,
        )
        transport = FakeTransport(
            script=[_ok(_bar_payload()), _ok(_bar_payload())]
        )
        with pytest.raises(DataContractError):
            run_rehearsal(
                authority=_authority(max_bytes=100),
                transport=transport,
                runtime_sha=RUNTIME_SHA,
                now_utc=NOW,
                ledger=ledger,
            )
        assert transport.calls == []


class TestDurabilityBoundary:
    def test_used_ledger_accumulates_no_silent_reset(self) -> None:
        ledger = LaneARequestLedger(
            max_http_operations=12,
            max_total_payload_bytes=LANE_A_MAX_TOTAL_PAYLOAD_BYTES,
        )
        transport = FakeTransport(
            script=[_ok(_bar_payload()), _ok(_bar_payload())]
        )
        first, verdict = run_rehearsal(
            authority=_authority(),
            transport=transport,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
            ledger=ledger,
        )
        assert verdict is RehearsalVerdict.PASS
        assert first.dispatched_operations == 2
        transport2 = FakeTransport(
            script=[_ok(_bar_payload()), _ok(_bar_payload())]
        )
        second, _ = run_rehearsal(
            authority=_authority(),
            transport=transport2,
            runtime_sha=RUNTIME_SHA,
            now_utc=NOW,
            ledger=ledger,
        )
        assert second.dispatched_operations == 4


class TestNoNetworkCapability:
    def test_module_imports_no_sockets_or_credentials(self) -> None:
        import re
        from pathlib import Path

        import acash.data.qualification.lane_a_rehearsal as rehearsal_mod

        text = Path(rehearsal_mod.__file__).read_text(encoding="utf-8")
        import_pattern = re.compile(r"^\s*(import|from)\s+([\w\.]+)", re.MULTILINE)
        for match in import_pattern.finditer(text):
            module = match.group(2).lower()
            for banned in (
                "socket",
                "httpx",
                "urllib",
                "requests",
                "http.client",
                "ssl",
                "websocket",
            ):
                assert banned not in module.split("."), (
                    f"lane_a_rehearsal.py imports {module!r}"
                )
        lowered = text.lower()
        for token in ("api_secret", "api_key", "password", "secret_ref"):
            assert token not in lowered, f"lane_a_rehearsal.py contains {token!r}"

    def test_expected_window_sessions(self) -> None:
        calendar = NyseCa1Calendar()
        assert [day for day in SESSIONS if calendar.is_trading_session(day)] == SESSIONS
