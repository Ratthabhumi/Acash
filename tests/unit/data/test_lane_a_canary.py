"""Bounded canary readiness tests (OFFLINE ONLY — fake transports, synthetic bytes).

No real provider HTTP, no credentials, no network. Fake transports live in
this test module and drive the PRODUCTION runner ``run_canary_offline``.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_canary import (
    CANARY_MAX_BYTES,
    CANARY_MAX_OPERATIONS,
    CanaryApproval,
    CanaryBudget,
    CanaryPage,
    CanaryPlan,
    ReservationJournal,
    canonical_scope_digest,
    canary_sessions,
    run_canary_offline,
)

RUNTIME_SHA = "b" * 40


class _TestVerifier:
    """Test-only approval plug (lives in tests, never in production code)."""

    def check(self, approval: CanaryApproval) -> bool:
        return approval.approval_ref.startswith("OP-")


_VERIFIER = _TestVerifier()


def _approval(feed: str = "iex", **overrides: Any) -> CanaryApproval:
    digest = canonical_scope_digest(
        ("VOO", "BND", "GLD", "BIL"), "1Day", "2026-09-28", "2026-10-02",
        ("raw", "all"), feed, CANARY_MAX_OPERATIONS, CANARY_MAX_BYTES, "0.00",
    )
    params: Dict[str, Any] = {
        "approval_ref": "OP-2026-10-14-001",
        "scope_digest": digest,
        "runtime_sha": RUNTIME_SHA,
        "valid_from_utc": "2026-10-14T00:00:00+00:00",
        "valid_until_utc": "2026-10-15T00:00:00+00:00",
        "max_operations": CANARY_MAX_OPERATIONS,
        "max_bytes": CANARY_MAX_BYTES,
        "paid_budget_usd": "0.00",
    }
    params.update(overrides)
    return CanaryApproval(**params)


def _build(
    feed: str = "iex",
    now_utc: str = "2026-10-14T12:00:00+00:00",
    runtime_sha: str = RUNTIME_SHA,
    **overrides: Any,
) -> CanaryPlan:
    return CanaryPlan.build(_approval(feed, **overrides), feed, now_utc, runtime_sha, _VERIFIER)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FakeCanaryTransport:
    """Scripted fake transport (test-only): canned pages, zero I/O."""

    script: List[CanaryPage]
    calls: List[str] = field(default_factory=list)

    def get(self, request_digest: str, page_token: str) -> CanaryPage:
        self.calls.append(request_digest + ":" + page_token)
        if not self.script:
            raise AssertionError("script exhausted: pagination exceeded budget")
        return self.script.pop(0)


def test_plan_build_and_request_digests() -> None:
    plan = _build()
    assert len(plan.request_digests()) == 2
    assert plan.scope_digest == _approval().scope_digest
    assert plan.runtime_sha == RUNTIME_SHA


def test_approval_never_verifies() -> None:
    try:
        _approval().verify_approval()
        assert False, "verify_approval must always fail closed"
    except DataContractError:
        pass


def test_plan_build_without_verifier_fails() -> None:
    try:
        CanaryPlan.build(_approval(), "iex", "2026-10-14T12:00:00+00:00", RUNTIME_SHA)
        assert False, "production path (no verifier) must fail closed"
    except DataContractError:
        pass


def test_plan_rejects_bad_feed() -> None:
    try:
        _build("sip2")
        assert False, "unknown feed must fail"
    except DataContractError:
        pass


def test_plan_rejects_expired_approval() -> None:
    try:
        _build("iex", "2026-10-16T00:00:00+00:00")
        assert False, "expired approval must fail"
    except DataContractError:
        pass


def test_approval_window_compares_instants_not_strings() -> None:
    # Same instant in +07:00 must be accepted where the +00:00 form is.
    approval = _approval(
        valid_from_utc="2026-10-14T07:00:00+07:00",
        valid_until_utc="2026-10-15T07:00:00+07:00",
    )
    assert approval.is_within_window("2026-10-14T00:00:00+00:00") is True
    assert approval.is_within_window("2026-10-13T23:59:59+00:00") is False
    # A lexicographically "smaller" +07:00 string that is actually later.
    assert approval.is_within_window("2026-10-14T05:00:00+07:00") is False
    assert approval.is_within_window("2026-10-14T12:00:00+07:00") is True


def test_approval_window_rejects_naive_and_unordered() -> None:
    try:
        _approval(valid_from_utc="2026-10-14T00:00:00")
        assert False, "naive valid_from must fail"
    except DataContractError:
        pass
    try:
        _approval(
            valid_from_utc="2026-10-15T00:00:00+00:00",
            valid_until_utc="2026-10-14T00:00:00+00:00",
        )
        assert False, "unordered window must fail"
    except DataContractError:
        pass


def test_plan_rejects_digest_mismatch() -> None:
    try:
        CanaryPlan.build(
            _approval(feed="sip"), "iex", "2026-10-14T12:00:00+00:00", RUNTIME_SHA, _VERIFIER
        )
        assert False, "scope digest mismatch must fail"
    except DataContractError:
        pass


def test_plan_rejects_over_budget_approval() -> None:
    try:
        _build("iex", max_operations=CANARY_MAX_OPERATIONS + 1)
        assert False, "over-budget approval must fail"
    except DataContractError:
        pass


def test_plan_rejects_runtime_sha_mismatch() -> None:
    try:
        CanaryPlan.build(
            _approval(), "iex", "2026-10-14T12:00:00+00:00", "c" * 40, _VERIFIER
        )
        assert False, "runtime SHA mismatch must fail"
    except DataContractError:
        pass
    try:
        CanaryPlan.build(
            _approval(), "iex", "2026-10-14T12:00:00+00:00", "not-a-sha", _VERIFIER
        )
        assert False, "malformed runtime SHA must fail"
    except DataContractError:
        pass


def test_canary_sessions_cover_full_window() -> None:
    sessions = canary_sessions()
    assert [s.isoformat() for s in sessions] == [
        "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02",
    ]
    assert sessions[-1] == date(2026, 10, 2)


def test_canary_pagination_completes_within_budget() -> None:
    plan = _build()
    transport = FakeCanaryTransport(script=[
        CanaryPage("OK", 1000, "t1"), CanaryPage("OK", 1000, ""),
        CanaryPage("OK", 500, ""),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_canary_offline(plan, transport, Path(tmp) / "run")
        assert result.verdict == "TRANSPORT_PAGINATION_COMPLETE"
        assert result.operations_used == 3
        assert result.bytes_observed == 2500
        assert len(result.dispatches) == 3


def test_canary_halts_on_429_with_budget_conserved() -> None:
    plan = _build("sip")
    transport = FakeCanaryTransport(script=[
        CanaryPage("OK", 100, ""), CanaryPage("HTTP_429", 50, ""),
        CanaryPage("OK", 100, ""),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_canary_offline(plan, transport, Path(tmp) / "run")
        assert result.verdict == "HALTED_HTTP_429"
        assert result.operations_used == 2
        assert result.bytes_observed == 150
        assert len(transport.calls) == 2


def test_canary_rejects_unknown_outcome_at_construction() -> None:
    try:
        CanaryPage("HTTP_418", 10, "")
        assert False, "unknown outcome must fail at page construction"
    except DataContractError:
        pass


def test_canary_rejects_page_token_cycle() -> None:
    plan = _build()
    transport = FakeCanaryTransport(script=[
        CanaryPage("OK", 10, "t1"), CanaryPage("OK", 10, ""),
        CanaryPage("OK", 10, "t1"),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        try:
            run_canary_offline(plan, transport, Path(tmp) / "run")
            assert False, "page token cycle must fail"
        except DataContractError:
            pass


def test_canary_same_token_across_chains_allowed() -> None:
    plan = _build()
    transport = FakeCanaryTransport(script=[
        CanaryPage("OK", 10, "shared"), CanaryPage("OK", 10, "shared"),
        CanaryPage("OK", 10, ""), CanaryPage("OK", 10, ""),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_canary_offline(plan, transport, Path(tmp) / "run")
        assert result.verdict == "TRANSPORT_PAGINATION_COMPLETE"
        assert result.operations_used == 4


def test_canary_second_run_same_dir_rejected() -> None:
    plan = _build()
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp) / "run"
        first = FakeCanaryTransport(script=[CanaryPage("OK", 1, ""), CanaryPage("OK", 1, "")])
        assert run_canary_offline(plan, first, run_dir).verdict == "TRANSPORT_PAGINATION_COMPLETE"
        second = FakeCanaryTransport(script=[CanaryPage("OK", 1, ""), CanaryPage("OK", 1, "")])
        try:
            run_canary_offline(plan, second, run_dir)
            assert False, "no resume under the same run directory"
        except DataContractError:
            pass


def test_canary_request_params_keep_end_of_day() -> None:
    from acash.data.qualification.lane_a_canary import canonical_request_params

    for adjustment in ("raw", "all"):
        params = canonical_request_params("iex", adjustment)
        assert params["start"] == "2026-09-28"
        assert params["end"] == "2026-10-02"
        assert date.fromisoformat(params["end"]) == date(2026, 10, 2)
        assert params["symbols"] == "VOO,BND,GLD,BIL"
        assert params["timeframe"] == "1Day"
    try:
        canonical_request_params("sip2", "raw")
        assert False, "unknown feed must fail"
    except DataContractError:
        pass


def test_reservation_failed_sync_consumes_no_sequence(monkeypatch: Any) -> None:
    import os as _os

    with tempfile.TemporaryDirectory() as tmp:
        journal = ReservationJournal.create(Path(tmp) / "run")

        def _boom(fd: int) -> None:
            raise OSError("injected sync failure")

        monkeypatch.setattr(_os, "fsync", _boom)
        try:
            journal.reserve(1, "d" * 64)
            assert False, "failed sync must block the reservation"
        except DataContractError:
            pass
        # The journal is poisoned: no further operations allowed, the
        # on-disk bytes are ambiguous (the write landed, the sync did not).
        try:
            journal.reserve(1, "d" * 64)
            assert False, "poisoned journal must refuse all further writes"
        except DataContractError:
            pass
        records = journal.read_reservations()
        assert len(records) == 1
        assert records[0]["event"] == "reserved"


def test_reservation_corrupt_record_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        journal = ReservationJournal.create(Path(tmp) / "run")
        journal.reserve(1, "e" * 64)
        with open(journal._file, "a", encoding="utf-8") as handle:
            handle.write("{torn json\n")
        try:
            journal.read_reservations()
            assert False, "torn record must fail closed"
        except DataContractError:
            pass


def test_reservation_settle_unknown_seq_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        journal = ReservationJournal.create(Path(tmp) / "run")
        journal.reserve(1, "f" * 64)
        try:
            journal.settle(2, "OK")
            assert False, "settle of unreserved seq must fail"
        except DataContractError:
            pass
        journal.settle(1, "OK")
        try:
            journal.settle(1, "OK")
            assert False, "duplicate settle must fail"
        except DataContractError:
            pass


def test_canary_byte_cap_breach_halts() -> None:
    plan = _build()
    transport = FakeCanaryTransport(script=[CanaryPage("OK", CANARY_MAX_BYTES + 1, "")])
    with tempfile.TemporaryDirectory() as tmp:
        try:
            run_canary_offline(plan, transport, Path(tmp) / "run")
            assert False, "byte cap breach must fail"
        except DataContractError:
            pass


def test_canary_operation_cap_exhaustion() -> None:
    budget = CanaryBudget(2, CANARY_MAX_BYTES)
    budget.reserve_operation()
    budget.reserve_operation()
    try:
        budget.reserve_operation()
        assert False, "operation cap must fail closed"
    except DataContractError:
        pass


def test_reservation_records_survive_reread() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        journal = ReservationJournal.create(Path(tmp) / "run")
        digest = "c" * 64
        journal.reserve(1, digest)
        journal.settle(1, "OK")
        records = journal.read_reservations()
        assert len(records) == 2
        assert records[0]["event"] == "reserved"
        assert records[0]["request_digest"] == digest
        assert records[1] == {"event": "settled", "outcome": "OK", "seq": 1}
        assert journal.reserved_count == 1


def test_reservation_file_created_once() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ReservationJournal.create(Path(tmp) / "run")
        try:
            ReservationJournal.create(Path(tmp) / "run")
            assert False, "duplicate reservation file must fail"
        except DataContractError:
            pass


def test_reservation_fsync_failure_blocks_dispatch(monkeypatch: Any) -> None:
    import os as _os

    def _boom(fd: int) -> None:
        raise OSError("injected sync failure")

    monkeypatch.setattr(_os, "fsync", _boom)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            ReservationJournal.create(Path(tmp) / "run")
            assert False, "failed required sync must block reservation setup"
        except DataContractError:
            pass


def test_reservation_fsync_failure_blocks_reserve(monkeypatch: Any) -> None:
    import os as _os

    with tempfile.TemporaryDirectory() as tmp:
        journal = ReservationJournal.create(Path(tmp) / "run")

        def _boom(fd: int) -> None:
            raise OSError("injected sync failure")

        monkeypatch.setattr(_os, "fsync", _boom)
        try:
            journal.reserve(1, "d" * 64)
            assert False, "failed required sync must block the reservation"
        except DataContractError:
            pass


def test_dir_sync_support_is_explicit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        journal = ReservationJournal.create(Path(tmp) / "run")
        assert isinstance(journal.dir_sync_supported, bool)


def test_no_network_imports_in_canary_module() -> None:
    import acash.data.qualification.lane_a_canary as module

    source = Path(str(module.__file__)).read_text(encoding="utf-8")
    for banned in ("import socket", "import httpx", "import urllib",
                   "import requests", "import aiohttp", "API_KEY", "api_secret"):
        assert banned not in source, f"banned surface {banned!r} present"


def test_secret_scan_canary_sources() -> None:
    import acash.data.qualification.lane_a_canary as module

    text = Path(str(module.__file__)).read_text(encoding="utf-8").lower()
    assert "bearer " not in text
    assert "apca-api" not in text


def test_budget_state_after_halt() -> None:
    budget = CanaryBudget(12, CANARY_MAX_BYTES)
    budget.observe_bytes(10)
    budget.halt("HTTP_403")
    assert budget.halted is True
    assert budget.bytes_observed == 10
    try:
        budget.reserve_operation()
        assert False, "halted budget must refuse operations"
    except DataContractError:
        pass


def test_canary_constants_match_packet() -> None:
    from acash.data.qualification.lane_a_canary import (
        CANARY_ADJUSTMENTS,
        CANARY_END,
        CANARY_FEEDS,
        CANARY_PAID_BUDGET_USD,
        CANARY_START,
        CANARY_SYMBOLS,
        CANARY_TIMEFRAME,
    )

    assert CANARY_SYMBOLS == ("VOO", "BND", "GLD", "BIL")
    assert (CANARY_START, CANARY_END) == ("2026-09-28", "2026-10-02")
    assert CANARY_TIMEFRAME == "1Day"
    assert CANARY_ADJUSTMENTS == ("raw", "all")
    assert set(CANARY_FEEDS) == {"iex", "sip"}
    assert CANARY_PAID_BUDGET_USD == "0.00"
