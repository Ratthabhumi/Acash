"""D2 composition tests (OFFLINE ONLY — fake transports, synthetic bytes).

No real provider HTTP, no credentials, no network. Proves the composed
reserve -> fake dispatch -> settle -> evidence chain end-to-end offline.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_canary import (
    CANARY_MAX_BYTES,
    CANARY_MAX_OPERATIONS,
    CanaryApproval,
    CanaryPage,
    CanaryPlan,
    canonical_scope_digest,
    canary_planned_requests,
)
from acash.data.qualification.lane_a_d2_composition import (
    run_d2_composition,
    validate_plan_binding,
    verify_evidence_lineage,
)
from acash.data.qualification.lane_a_transport import (
    DurableAttemptJournal,
    store_raw_evidence,
    verify_evidence_pair,
)

RUNTIME_SHA = "b" * 40


class _TestVerifier:
    def check(self, approval: CanaryApproval) -> bool:
        return approval.approval_ref.startswith("OP-")


def _plan(feed: str = "iex") -> CanaryPlan:
    requests = canary_planned_requests(feed)
    digest = canonical_scope_digest(requests, CANARY_MAX_OPERATIONS, CANARY_MAX_BYTES)
    approval = CanaryApproval(
        approval_ref="OP-2026-10-15-001",
        scope_digest=digest,
        runtime_sha=RUNTIME_SHA,
        valid_from_utc="2026-10-15T00:00:00+00:00",
        valid_until_utc="2026-10-16T00:00:00+00:00",
        max_operations=CANARY_MAX_OPERATIONS,
        max_bytes=CANARY_MAX_BYTES,
        paid_budget_usd="0.00",
    )
    return CanaryPlan.build(
        approval, feed, "2026-10-15T12:00:00+00:00", RUNTIME_SHA, _TestVerifier()
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FakeD2Transport:
    script: List[CanaryPage]
    calls: List[str] = field(default_factory=list)

    def get(self, request_digest: str, page_token: str) -> CanaryPage:
        self.calls.append(request_digest + ":" + page_token)
        if not self.script:
            raise AssertionError("script exhausted")
        return self.script.pop(0)


def _payload(request_digest: str, token: str, page: CanaryPage) -> bytes:
    return b"p" * page.nbytes


def test_composed_run_complete_with_admissible_evidence() -> None:
    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 100, "t1"), CanaryPage("OK", 200, ""),
        CanaryPage("OK", 50, ""),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            plan=plan,
            transport=transport,
            evidence_root=Path(tmp) / "ev",
            run_id="run_compose_001",
            authority_ref="OP-2026-10-15-001",
            runtime_sha=RUNTIME_SHA,
            created_at_utc=_now(),
            payload_fn=_payload,
        )
        assert result.verdict == "TRANSPORT_PAGINATION_COMPLETE"
        assert result.operations_used == 3
        assert result.bytes_observed == 350
        assert len(result.receipts) == 3
        root = Path(tmp) / "ev"
        for receipt in result.receipts:
            assert receipt.byte_count > 0
            assert (
                verify_evidence_pair(root=root, run_id="run_compose_001",
                                     name=receipt.evidence_name)
                == "ADMISSIBLE"
            )
        assert DurableAttemptJournal.classify_run(root=root, run_id="run_compose_001") == "COMPLETE"


def test_composed_run_halts_on_429_with_aborted_lifecycle() -> None:
    plan = _plan("sip")
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 64, ""), CanaryPage("HTTP_429", 32, ""),
        CanaryPage("OK", 64, ""),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            plan=plan,
            transport=transport,
            evidence_root=Path(tmp) / "ev",
            run_id="run_compose_002",
            authority_ref="OP-2026-10-15-001",
            runtime_sha=RUNTIME_SHA,
            created_at_utc=_now(),
            payload_fn=_payload,
        )
        assert result.verdict == "HALTED_HTTP_429"
        assert result.operations_used == 2
        assert len(result.receipts) == 1
        assert len(transport.calls) == 2
        root = Path(tmp) / "ev"
        assert DurableAttemptJournal.classify_run(root=root, run_id="run_compose_002") == "ABORTED"


def test_composed_run_rejects_payload_byte_mismatch() -> None:
    plan = _plan()
    transport = FakeD2Transport(script=[CanaryPage("OK", 100, "")])

    def _bad_payload(request_digest: str, token: str, page: CanaryPage) -> bytes:
        return b"short"

    with tempfile.TemporaryDirectory() as tmp:
        try:
            run_d2_composition(
                plan=plan,
                transport=transport,
                evidence_root=Path(tmp) / "ev",
                run_id="run_compose_003",
                authority_ref="OP-2026-10-15-001",
                runtime_sha=RUNTIME_SHA,
                created_at_utc=_now(),
                payload_fn=_bad_payload,
            )
            assert False, "payload/nbytes mismatch must fail"
        except DataContractError:
            pass


def test_composed_run_no_resume_same_run_id() -> None:
    plan = _plan()
    with tempfile.TemporaryDirectory() as tmp:
        run_d2_composition(
            plan=plan,
            transport=FakeD2Transport(script=[
                CanaryPage("OK", 8, ""), CanaryPage("OK", 8, "")]),
            evidence_root=Path(tmp) / "ev",
            run_id="run_compose_004",
            authority_ref="OP-2026-10-15-001",
            runtime_sha=RUNTIME_SHA,
            created_at_utc=_now(),
            payload_fn=_payload,
        )
        try:
            run_d2_composition(
                plan=plan,
                transport=FakeD2Transport(script=[
                    CanaryPage("OK", 8, ""), CanaryPage("OK", 8, "")]),
                evidence_root=Path(tmp) / "ev",
                run_id="run_compose_004",
                authority_ref="OP-2026-10-15-001",
                runtime_sha=RUNTIME_SHA,
                created_at_utc=_now(),
                payload_fn=_payload,
            )
            assert False, "same run id must never resume"
        except DataContractError:
            pass


def test_composed_run_rejects_bad_transport_page() -> None:
    plan = _plan()

    class _BadTransport:
        def get(self, request_digest: str, page_token: str) -> Any:
            return {"outcome": "OK"}

    with tempfile.TemporaryDirectory() as tmp:
        try:
            run_d2_composition(
                plan=plan,
                transport=_BadTransport(),
                evidence_root=Path(tmp) / "ev",
                run_id="run_compose_005",
                authority_ref="OP-2026-10-15-001",
                runtime_sha=RUNTIME_SHA,
                created_at_utc=_now(),
                payload_fn=_payload,
            )
            assert False, "non-page transport output must fail"
        except DataContractError:
            pass


def test_no_network_imports_in_composition_module() -> None:
    import acash.data.qualification.lane_a_d2_composition as module

    source = Path(str(module.__file__)).read_text(encoding="utf-8")
    for banned in ("import socket", "import httpx", "import urllib",
                   "import requests", "import aiohttp", "APCA-API",
                   "api_secret", "credential_provider", "os.environ"):
        assert banned not in source, f"banned surface {banned!r} present"


def _run_kwargs(tmp: str, run_id: str, plan: CanaryPlan, transport: Any) -> Any:
    return {
        "plan": plan,
        "transport": transport,
        "evidence_root": Path(tmp) / "ev",
        "run_id": run_id,
        "authority_ref": "OP-2026-10-15-001",
        "runtime_sha": RUNTIME_SHA,
        "created_at_utc": _now(),
        "payload_fn": _payload,
    }


def test_binding_rejects_authority_runtime_mismatch() -> None:
    plan = _plan()
    for kwargs_change in (
        {"authority_ref": "OP-OTHER"},
        {"runtime_sha": "c" * 40},
    ):
        with tempfile.TemporaryDirectory() as tmp:
            kwargs = _run_kwargs(tmp, "run_bind_001", plan,
                                 FakeD2Transport(script=[]))
            kwargs.update(kwargs_change)
            try:
                run_d2_composition(**kwargs)
                assert False, f"mismatch admitted: {kwargs_change!r}"
            except DataContractError:
                pass
            root = Path(tmp) / "ev"
            assert DurableAttemptJournal.classify_run(root=root, run_id="run_bind_001") == "MISSING"


def test_binding_rejects_tampered_plan() -> None:
    import dataclasses

    plan = _plan()
    tampered = dataclasses.replace(plan, scope_digest="0" * 64)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            validate_plan_binding(
                tampered, "OP-2026-10-15-001", RUNTIME_SHA, _now())
            assert False, "tampered digest must fail"
        except DataContractError:
            pass
    empty = dataclasses.replace(plan, requests=())
    with tempfile.TemporaryDirectory() as tmp:
        try:
            validate_plan_binding(
                empty, "OP-2026-10-15-001", RUNTIME_SHA, _now())
            assert False, "empty plan must fail"
        except DataContractError:
            pass


def test_binding_rejects_wrong_feed_requests() -> None:
    other = _plan("sip")
    import dataclasses

    mixed = dataclasses.replace(other, feed="iex")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            validate_plan_binding(
                mixed, "OP-2026-10-15-001", RUNTIME_SHA, _now())
            assert False, "feed/request mismatch must fail"
        except DataContractError:
            pass


def test_exception_leaves_interrupted_never_complete() -> None:
    plan = _plan()

    class _ExplodingTransport:
        def get(self, request_digest: str, page_token: str) -> Any:
            raise RuntimeError("injected mid-run transport failure")

    with tempfile.TemporaryDirectory() as tmp:
        try:
            run_d2_composition(
                **_run_kwargs(tmp, "run_exc_001", plan, _ExplodingTransport()))
            assert False, "transport explosion must propagate"
        except RuntimeError:
            pass
        root = Path(tmp) / "ev"
        assert DurableAttemptJournal.classify_run(root=root, run_id="run_exc_001") == "INTERRUPTED"
        assert not (root / "lane_a_runs" / "run_exc_001" / "completion.json").is_file()


def test_evidence_payload_readback_matches() -> None:
    import hashlib

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 32, ""), CanaryPage("OK", 32, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_rb_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_rb_001"
        for receipt in result.receipts:
            raw = (run_dir / f"{receipt.evidence_name}.bin").read_bytes()
            assert hashlib.sha256(raw).hexdigest() == receipt.content_sha256
            assert len(raw) == receipt.byte_count == 32


def test_lineage_rejects_swapped_receipt() -> None:
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_sw_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_sw_001"
        journal = ReservationJournal(run_dir / "attempts.jsonl", True)
        assert len(result.receipts) == 2
        first, second = result.receipts
        swapped = [(first.seq, second.content_sha256, first.evidence_name)]
        try:
            verify_evidence_lineage(root, journal, swapped)
            assert False, "swapped digest binding must fail"
        except DataContractError:
            pass


def test_lineage_rejects_missing_and_tampered_artifacts() -> None:
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_tm_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_tm_001"
        victim = result.receipts[0]
        (run_dir / f"{victim.evidence_name}.bin").write_bytes(b"tampered-bytes-00")
        journal = ReservationJournal(run_dir / "attempts.jsonl", True)
        expected = [(r.seq, "0" * 64, r.evidence_name) for r in result.receipts]
        try:
            verify_evidence_lineage(root, journal, expected)
            assert False, "tampered pair must fail lineage"
        except DataContractError:
            pass


def test_metadata_request_digest_schema() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_meta_001"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text("{}")
        good = store_raw_evidence(
            root=root, run_id="run_meta_001", name="ok",
            payload=b"payload-bytes",
            metadata={"feed": "iex", "request_index": 0,
                      "request_digest": "a" * 64},
        )
        assert good["byte_count"] == len(b"payload-bytes")
        for bad_meta in (
            {"feed": "iex", "request_digest": "not-hex"},
            {"feed": "iex", "request_digest": "A" * 64},
            {"feed": "iex", "api_key": "K" * 8},
        ):
            try:
                store_raw_evidence(
                    root=root, run_id="run_meta_001", name="bad",
                    payload=b"payload-bytes", metadata=bad_meta)
                assert False, f"bad metadata admitted: {bad_meta!r}"
            except DataContractError:
                pass


def test_no_socket_use_on_exercised_path(monkeypatch: Any) -> None:
    import socket

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("socket must never be created on the offline path")

    monkeypatch.setattr(socket, "socket", _boom)
    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 24, ""), CanaryPage("OK", 24, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_nsock_001", plan, transport))
        assert result.verdict == "TRANSPORT_PAGINATION_COMPLETE"
