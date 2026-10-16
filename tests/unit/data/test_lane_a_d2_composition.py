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

import pytest

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
FIXED_VALID_FROM = "2026-10-15T00:00:00+00:00"
FIXED_VALID_UNTIL = "2026-10-16T00:00:00+00:00"
FIXED_TEST_NOW = "2026-10-15T12:00:00+00:00"


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
        valid_from_utc=FIXED_VALID_FROM,
        valid_until_utc=FIXED_VALID_UNTIL,
        max_operations=CANARY_MAX_OPERATIONS,
        max_bytes=CANARY_MAX_BYTES,
        paid_budget_usd="0.00",
    )
    return CanaryPlan.build(
        approval, feed, FIXED_TEST_NOW, RUNTIME_SHA, _TestVerifier()
    )


def _now() -> str:
    """Deterministic synthetic test clock strictly within synthetic approval window."""
    return FIXED_TEST_NOW


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


def test_approval_window_boundary_before_valid() -> None:
    plan = _plan()
    with pytest.raises(DataContractError, match="D2_APPROVAL_WINDOW_INVALID"):
        validate_plan_binding(
            plan, "OP-2026-10-15-001", RUNTIME_SHA, "2026-10-14T23:59:59+00:00"
        )


def test_approval_window_boundary_exact_start() -> None:
    plan = _plan()
    validate_plan_binding(
        plan, "OP-2026-10-15-001", RUNTIME_SHA, "2026-10-15T00:00:00+00:00"
    )


def test_approval_window_boundary_within_valid() -> None:
    plan = _plan()
    validate_plan_binding(
        plan, "OP-2026-10-15-001", RUNTIME_SHA, "2026-10-15T12:00:00+00:00"
    )


def test_approval_window_boundary_exact_expiry() -> None:
    plan = _plan()
    validate_plan_binding(
        plan, "OP-2026-10-15-001", RUNTIME_SHA, "2026-10-16T00:00:00+00:00"
    )


def test_approval_window_boundary_after_expiry() -> None:
    plan = _plan()
    with pytest.raises(DataContractError, match="D2_APPROVAL_WINDOW_INVALID"):
        validate_plan_binding(
            plan, "OP-2026-10-15-001", RUNTIME_SHA, "2026-10-16T00:00:01+00:00"
        )


def test_approval_window_clock_jump_across_expiry_without_sleep() -> None:
    plan = _plan()
    # Sequence represents synthetic clock advancing deterministically across expiry
    clock_sequence = [
        "2026-10-15T23:59:59+00:00",  # before expiry: VALID
        "2026-10-16T00:00:00+00:00",  # exact boundary: VALID
        "2026-10-16T00:00:01+00:00",  # after expiry: REJECTED
        "2026-10-16T02:42:00+00:00",  # next day: REJECTED
    ]
    validate_plan_binding(plan, "OP-2026-10-15-001", RUNTIME_SHA, clock_sequence[0])
    validate_plan_binding(plan, "OP-2026-10-15-001", RUNTIME_SHA, clock_sequence[1])
    with pytest.raises(DataContractError, match="D2_APPROVAL_WINDOW_INVALID"):
        validate_plan_binding(plan, "OP-2026-10-15-001", RUNTIME_SHA, clock_sequence[2])
    with pytest.raises(DataContractError, match="D2_APPROVAL_WINDOW_INVALID"):
        validate_plan_binding(plan, "OP-2026-10-15-001", RUNTIME_SHA, clock_sequence[3])


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
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        assert len(result.receipts) == 2
        first, second = result.receipts

        # 1. Establish valid control case first: unmodified lineage accepted
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [
            (first.seq, reserved[first.seq], first.evidence_name),
            (second.seq, reserved[second.seq], second.evidence_name),
        ]
        verify_evidence_lineage(root, journal, valid_expected)

        # 2. Introduce exactly one fault: swap evidence name between requests
        swapped = [
            (first.seq, reserved[first.seq], second.evidence_name),
            (second.seq, reserved[second.seq], second.evidence_name),
        ]
        with pytest.raises(
            DataContractError,
            match=f"D2_LINEAGE_RECEIPT_BINDING_MISMATCH: {second.evidence_name}."
        ):
            verify_evidence_lineage(root, journal, swapped)


def test_lineage_rejects_wrong_canonical_request_digest() -> None:
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_wrd_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_wrd_001"
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        first = result.receipts[0]
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [(r.seq, reserved[r.seq], r.evidence_name) for r in result.receipts]
        verify_evidence_lineage(root, journal, valid_expected)

        # Fault: wrong request digest supplied for reservation seq
        wrong_expected = [(first.seq, "f" * 64, first.evidence_name)]
        with pytest.raises(
            DataContractError,
            match=f"D2_LINEAGE_RESERVATION_MISMATCH: seq {first.seq}."
        ):
            verify_evidence_lineage(root, journal, wrong_expected)


def test_lineage_rejects_tampered_raw_payload() -> None:
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_traw_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_traw_001"
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [(r.seq, reserved[r.seq], r.evidence_name) for r in result.receipts]
        verify_evidence_lineage(root, journal, valid_expected)

        # Fault: tamper raw binary bytes
        victim = result.receipts[0]
        (run_dir / f"{victim.evidence_name}.bin").write_bytes(b"tampered-bytes-00")
        with pytest.raises(
            DataContractError,
            match=f"D2_LINEAGE_NOT_ADMISSIBLE: {victim.evidence_name}."
        ):
            verify_evidence_lineage(root, journal, valid_expected)


def test_lineage_rejects_missing_raw_payload() -> None:
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_mraw_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_mraw_001"
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [(r.seq, reserved[r.seq], r.evidence_name) for r in result.receipts]
        verify_evidence_lineage(root, journal, valid_expected)

        # Fault: delete raw binary payload
        victim = result.receipts[0]
        (run_dir / f"{victim.evidence_name}.bin").unlink()
        with pytest.raises(
            DataContractError,
            match=f"D2_LINEAGE_NOT_ADMISSIBLE: {victim.evidence_name}."
        ):
            verify_evidence_lineage(root, journal, valid_expected)


def test_lineage_rejects_missing_receipt() -> None:
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_mrcp_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_mrcp_001"
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [(r.seq, reserved[r.seq], r.evidence_name) for r in result.receipts]
        verify_evidence_lineage(root, journal, valid_expected)

        # Fault: delete receipt json
        victim = result.receipts[0]
        (run_dir / f"{victim.evidence_name}.receipt.json").unlink()
        with pytest.raises(
            DataContractError,
            match=f"D2_LINEAGE_NOT_ADMISSIBLE: {victim.evidence_name}."
        ):
            verify_evidence_lineage(root, journal, valid_expected)


def test_lineage_rejects_corrupt_reservation_history() -> None:
    import json
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_crh_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_crh_001"
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [(r.seq, reserved[r.seq], r.evidence_name) for r in result.receipts]
        verify_evidence_lineage(root, journal, valid_expected)

        # Fault: append a duplicate reserved seq line
        with open(run_dir / "reservations.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "reserved", "seq": 1, "request_digest": "a" * 64}) + "\n")
        with pytest.raises(
            DataContractError,
            match="CANARY_HISTORY_DUP_RESERVED: seq 1."
        ):
            verify_evidence_lineage(root, journal, valid_expected)


def test_lineage_rejects_unsettled_attempt() -> None:
    import json
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_unst_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_unst_001"
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [(r.seq, reserved[r.seq], r.evidence_name) for r in result.receipts]
        verify_evidence_lineage(root, journal, valid_expected)

        # Fault: append a valid monotonic reservation (seq 3) that was never settled
        dummy_digest = "c" * 64
        with open(run_dir / "reservations.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "reserved", "seq": 3, "request_digest": dummy_digest}) + "\n")
        unsettled_expected = valid_expected + [(3, dummy_digest, "seq_0003")]
        with pytest.raises(
            DataContractError,
            match="D2_LINEAGE_UNSETTLED: seq 3."
        ):
            verify_evidence_lineage(root, journal, unsettled_expected)


def test_lineage_rejects_failed_settlement() -> None:
    import json
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_fset_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_fset_001"
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [(r.seq, reserved[r.seq], r.evidence_name) for r in result.receipts]
        verify_evidence_lineage(root, journal, valid_expected)

        # Fault: rewrite reservations.jsonl so seq 2 settled as HTTP_429 instead of OK
        lines = (run_dir / "reservations.jsonl").read_text(encoding="utf-8").strip().splitlines()
        new_lines = []
        for line in lines:
            rec = json.loads(line)
            if rec.get("event") == "settled" and rec.get("seq") == 2:
                rec["outcome"] = "HTTP_429"
            new_lines.append(json.dumps(rec))
        (run_dir / "reservations.jsonl").write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        with pytest.raises(
            DataContractError,
            match="D2_LINEAGE_SETTLEMENT_NOT_OK: seq 2 settled as 'HTTP_429'."
        ):
            verify_evidence_lineage(root, journal, valid_expected)


def test_lineage_rejects_corrupt_receipt_metadata() -> None:
    import json
    from acash.data.qualification.lane_a_canary import ReservationJournal

    plan = _plan()
    transport = FakeD2Transport(script=[
        CanaryPage("OK", 16, ""), CanaryPage("OK", 16, "")])
    with tempfile.TemporaryDirectory() as tmp:
        result = run_d2_composition(
            **_run_kwargs(tmp, "run_crm_001", plan, transport))
        root = Path(tmp) / "ev"
        run_dir = root / "lane_a_runs" / "run_crm_001"
        journal = ReservationJournal(run_dir / "reservations.jsonl", True)
        records = journal.read_reservations()
        reserved = {
            int(r["seq"]): str(r["request_digest"])
            for r in records
            if r.get("event") == "reserved"
        }
        valid_expected = [(r.seq, reserved[r.seq], r.evidence_name) for r in result.receipts]
        verify_evidence_lineage(root, journal, valid_expected)

        # Fault A: bad feed in metadata
        receipt_path = run_dir / f"{result.receipts[0].evidence_name}.receipt.json"
        orig_raw = receipt_path.read_text(encoding="utf-8")
        data = json.loads(orig_raw)
        data["metadata"]["feed"] = "unauthorized_feed"
        receipt_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(
            DataContractError,
            match=f"D2_LINEAGE_RECEIPT_BAD_FEED: {result.receipts[0].evidence_name}."
        ):
            verify_evidence_lineage(root, journal, valid_expected)

        # Restore and test Fault B: bad request_index in metadata
        data = json.loads(orig_raw)
        data["metadata"]["request_index"] = -1
        receipt_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(
            DataContractError,
            match=f"D2_LINEAGE_RECEIPT_BAD_REQUEST_INDEX: {result.receipts[0].evidence_name}."
        ):
            verify_evidence_lineage(root, journal, valid_expected)


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
