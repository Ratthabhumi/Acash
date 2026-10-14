"""Bounded canary readiness tests (OFFLINE ONLY — fake transports, synthetic bytes).

No real provider HTTP, no credentials, no network. The fake transport
lives in this test module, never in the implementation.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_canary import (
    CANARY_MAX_BYTES,
    CANARY_MAX_OPERATIONS,
    CanaryApproval,
    CanaryBudget,
    CanaryPlan,
    ReservationJournal,
    canonical_scope_digest,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _TestVerifier:
    """Test-only approval plug (lives in tests, never in production code)."""

    def check(self, approval: CanaryApproval) -> bool:
        return approval.approval_ref.startswith("OP-")


_VERIFIER = _TestVerifier()


def _build(
    feed: str = "iex", now_utc: str = "2026-10-14T12:00:00+00:00", **overrides: Any
) -> CanaryPlan:
    return CanaryPlan.build(_approval(feed, **overrides), feed, now_utc, _VERIFIER)


def _approval(feed: str = "iex", **overrides: Any) -> CanaryApproval:
    digest = canonical_scope_digest(
        ("VOO", "BND", "GLD", "BIL"), "1Day", "2026-09-28", "2026-10-02",
        ("raw", "all"), feed, CANARY_MAX_OPERATIONS, CANARY_MAX_BYTES, "0.00",
    )
    params = {
        "approval_ref": "OP-2026-10-14-001",
        "scope_digest": digest,
        "runtime_sha": "b" * 40,
        "valid_from_utc": "2026-10-14T00:00:00+00:00",
        "valid_until_utc": "2026-10-15T00:00:00+00:00",
        "max_operations": CANARY_MAX_OPERATIONS,
        "max_bytes": CANARY_MAX_BYTES,
        "paid_budget_usd": "0.00",
    }
    params.update(overrides)
    return CanaryApproval(**params)  # type: ignore[arg-type]


@dataclass
class FakePage:
    outcome: str
    nbytes: int
    next_token: str = ""


@dataclass
class FakeCanaryTransport:
    """Scripted fake transport (test-only): canned pages, byte accounting, zero I/O."""

    script: List[FakePage]
    calls: List[str] = field(default_factory=list)

    def get(self, request_digest: str, page_token: str) -> FakePage:
        self.calls.append(request_digest + ":" + page_token)
        if not self.script:
            raise AssertionError("script exhausted: pagination exceeded budget")
        return self.script.pop(0)


def _run_canary(
    transport: FakeCanaryTransport, plan: CanaryPlan, run_dir: Path
) -> Tuple[str, int, int]:
    """Offline canary driver: reserve-before-dispatch, capped, fail-closed."""
    budget = CanaryBudget(plan.approval.max_operations, plan.approval.max_bytes)
    journal = ReservationJournal.create(run_dir)
    seq = 0
    pending: List[Tuple[str, str]] = [
        (digest, "") for digest in plan.request_digests()
    ]
    while pending:
        request_digest, token = pending.pop(0)
        seq += 1
        budget.reserve_operation()
        journal.reserve(seq, request_digest)
        page = transport.get(request_digest, token)
        budget.observe_bytes(page.nbytes)
        if page.outcome in ("HTTP_401", "HTTP_403", "HTTP_429", "TIMEOUT_AMBIGUOUS"):
            journal.settle(seq, page.outcome)
            budget.halt(page.outcome)
            return ("HALTED_" + page.outcome, seq, budget.bytes_observed)
        journal.settle(seq, page.outcome)
        if page.next_token:
            pending.append((request_digest, page.next_token))
    return ("COMPLETE", seq, budget.bytes_observed)


def test_plan_build_and_request_digests() -> None:
    plan = _build()
    assert len(plan.request_digests()) == 2
    assert plan.scope_digest == _approval().scope_digest


def test_approval_never_verifies() -> None:
    try:
        _approval().verify_approval()
        assert False, "verify_approval must always fail closed"
    except DataContractError:
        pass


def test_plan_build_without_verifier_fails() -> None:
    try:
        CanaryPlan.build(_approval(), "iex", "2026-10-14T12:00:00+00:00")
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


def test_plan_rejects_digest_mismatch() -> None:
    try:
        CanaryPlan.build(
            _approval(feed="sip"), "iex", "2026-10-14T12:00:00+00:00", _VERIFIER
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


def test_canary_pagination_completes_within_budget() -> None:
    plan = _build()
    transport = FakeCanaryTransport(script=[
        FakePage("OK", 1000, "t1"), FakePage("OK", 1000, ""),
        FakePage("OK", 500, ""),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        verdict, ops, observed = _run_canary(transport, plan, Path(tmp) / "run")
        assert verdict == "COMPLETE"
        assert ops == 3
        assert observed == 2500
        assert len(transport.calls) == 3


def test_canary_halts_on_429_with_budget_conserved() -> None:
    plan = _build("sip")
    transport = FakeCanaryTransport(script=[
        FakePage("OK", 100, ""), FakePage("HTTP_429", 50, ""),
        FakePage("OK", 100, ""),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        verdict, ops, observed = _run_canary(transport, plan, Path(tmp) / "run")
        assert verdict == "HALTED_HTTP_429"
        assert ops == 2
        assert observed == 150
        assert len(transport.calls) == 2


def test_canary_byte_cap_breach_halts() -> None:
    plan = _build()
    transport = FakeCanaryTransport(script=[FakePage("OK", CANARY_MAX_BYTES + 1, "")])
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _run_canary(transport, plan, Path(tmp) / "run")
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
