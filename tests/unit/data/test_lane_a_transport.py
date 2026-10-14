"""M1.8.1 dedicated tests for real-transport boundary, durable journal, and immutable evidence persistence.

All tests are structurally/scope verified — no real network I/O, no credentials, no secrets.
Uses only synthetic bytes, temporary external test directories, and ISO-8601 timezone-aware timestamps.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_transport import (
    STORAGE_CONTRACT,
    AttemptRecord,
    DurableAttemptJournal,
    RealTransportBoundary,
    check_request_allowlist,
    store_raw_evidence,
    verify_evidence_pair,
)
from acash.data.qualification.lane_a_authority import redact_secrets
from acash.evidence.roots import validate_external_evidence_root

RUNTIME_SHA = "a" * 40


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_journal(tmp: str, run_id: str) -> DurableAttemptJournal:
    return DurableAttemptJournal.create_run(
        root=Path(tmp) / "external_evidence",
        run_id=run_id,
        authority_ref="auth_test",
        runtime_sha=RUNTIME_SHA,
        created_at_utc=_now(),
    )


def test_storage_contract_label_is_honest() -> None:
    assert STORAGE_CONTRACT == "FILE_BACKED_CREATE_ONCE_NOT_CRASH_DURABILITY_VERIFIED"


def test_real_transport_boundary_allowlist_host() -> None:
    boundary = RealTransportBoundary()
    try:
        boundary.get("data.alpaca.markets", "GET", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass


def test_real_transport_boundary_rejected_host() -> None:
    boundary = RealTransportBoundary()
    try:
        boundary.get("unauthorized.example.com", "GET", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass


def test_real_transport_boundary_rejected_method() -> None:
    boundary = RealTransportBoundary()
    try:
        boundary.get("data.alpaca.markets", "POST", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass


def test_real_transport_boundary_rejected_path() -> None:
    boundary = RealTransportBoundary()
    try:
        boundary.get("data.alpaca.markets", "GET", "/v3/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass


def test_check_request_allowlist_approved() -> None:
    check_request_allowlist("data.alpaca.markets", "GET", "/v2/stocks/bars")


def test_check_request_allowlist_rejected_host() -> None:
    try:
        check_request_allowlist("evil.example.com", "GET", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass


def test_check_request_allowlist_rejected_method() -> None:
    try:
        check_request_allowlist("data.alpaca.markets", "DELETE", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass


def test_check_request_allowlist_rejected_path() -> None:
    try:
        check_request_allowlist("data.alpaca.markets", "GET", "/v3/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass


def test_durable_attempt_journal_create_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        journal = _make_journal(tmp, "test_run_001")
        expected_dir = Path(tmp) / "external_evidence" / "lane_a_runs" / "test_run_001"
        assert expected_dir.is_dir()
        assert (expected_dir / "run.json").is_file()
        assert journal._run_id == "test_run_001"
        try:
            _make_journal(tmp, "test_run_001")
            assert False, "Should have raised DataContractError for duplicate run id"
        except DataContractError:
            pass


def test_durable_attempt_journal_bad_runtime_sha() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            DurableAttemptJournal.create_run(
                root=Path(tmp) / "external_evidence",
                run_id="test_run_sha",
                authority_ref="auth_test",
                runtime_sha="abc123def456",
                created_at_utc=_now(),
            )
            assert False, "Should have raised DataContractError for malformed runtime SHA"
        except DataContractError:
            pass


def test_durable_attempt_journal_dot_run_ids_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for bad in (".", ".."):
            try:
                _make_journal(tmp, bad)
                assert False, f"Should have raised for run id {bad!r}"
            except DataContractError:
                pass


def test_durable_attempt_journal_no_resume() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _make_journal(tmp, "test_run_002")
        try:
            DurableAttemptJournal.open_existing(
                root=Path(tmp) / "external_evidence", run_id="test_run_002"
            )
            assert False, "Should have raised DataContractError for open_existing"
        except DataContractError:
            pass


def test_durable_attempt_journal_classify_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        resolved = validate_external_evidence_root(Path(tmp) / "external_evidence")
        assert DurableAttemptJournal.classify_run(root=resolved, run_id="nonexistent") == "MISSING"

        journal = _make_journal(tmp, "run_complete")
        journal.close_run(status="COMPLETE", completed_at_utc=_now())
        assert DurableAttemptJournal.classify_run(root=resolved, run_id="run_complete") == "COMPLETE"

        journal2 = _make_journal(tmp, "run_aborted")
        journal2.close_run(status="ABORTED", completed_at_utc=_now())
        assert DurableAttemptJournal.classify_run(root=resolved, run_id="run_aborted") == "ABORTED"

        journal3 = _make_journal(tmp, "run_open")
        assert DurableAttemptJournal.classify_run(root=resolved, run_id="run_open") == "INTERRUPTED"
        del journal3


def test_durable_attempt_journal_classify_corrupt_completion() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        resolved = validate_external_evidence_root(Path(tmp) / "external_evidence")
        empty_run = _make_journal(tmp, "run_empty_completion")
        (empty_run._run_dir / "completion.json").write_bytes(b"")
        assert DurableAttemptJournal.classify_run(root=resolved, run_id="run_empty_completion") == "CORRUPT"

        bad_run = _make_journal(tmp, "run_bad_completion")
        (bad_run._run_dir / "completion.json").write_bytes(b'{"status": "SUCCESS"}')
        assert DurableAttemptJournal.classify_run(root=resolved, run_id="run_bad_completion") == "CORRUPT"


def test_durable_attempt_journal_record_attempt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        journal = _make_journal(tmp, "test_run_003")
        journal.record_attempt(
            AttemptRecord(seq=1, kind="test", outcome="observed", bytes_observed=1024,
                          recorded_at_utc=_now(), detail="first attempt")
        )
        journal.record_attempt(
            AttemptRecord(seq=2, kind="test", outcome="observed", bytes_observed=2048,
                          recorded_at_utc=_now(), detail="second attempt")
        )
        attempts_file = journal._run_dir / "attempts.jsonl"
        assert attempts_file.is_file()
        lines = attempts_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["seq"] == 1 and first["bytes_observed"] == 1024
        try:
            journal.record_attempt(
                AttemptRecord(seq=1, kind="test", outcome="observed", bytes_observed=512,
                              recorded_at_utc=_now())
            )
            assert False, "Should have raised DataContractError for non-increasing seq"
        except DataContractError:
            pass
        try:
            journal.record_attempt(
                AttemptRecord(seq=3, kind="test", outcome="observed", bytes_observed=-100,
                              recorded_at_utc=_now())
            )
            assert False, "Should have raised DataContractError for negative bytes"
        except DataContractError:
            pass


def test_durable_attempt_journal_append_after_close_rejected() -> None:
    for status in ("COMPLETE", "ABORTED"):
        with tempfile.TemporaryDirectory() as tmp:
            journal = _make_journal(tmp, "test_run_closed")
            journal.close_run(status=status, completed_at_utc=_now())
            try:
                journal.record_attempt(
                    AttemptRecord(seq=1, kind="test", outcome="observed", bytes_observed=8,
                                  recorded_at_utc=_now())
                )
                assert False, f"Should have raised after {status} closure"
            except DataContractError:
                pass


def test_durable_attempt_journal_duplicate_close_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        journal = _make_journal(tmp, "test_run_004")
        journal.close_run(status="COMPLETE", completed_at_utc=_now())
        assert (journal._run_dir / "completion.json").is_file()
        try:
            journal.close_run(status="COMPLETE", completed_at_utc=_now())
            assert False, "Should have raised DataContractError on repeat close"
        except DataContractError:
            pass


def test_store_raw_evidence_roundtrip_and_verify() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        journal = _make_journal(tmp, "test_run_ev")
        payload = b"synthetic raw payload bytes"
        metadata = {"feed": "alpaca", "timeframe": "1Day", "page_index": 0}
        result = store_raw_evidence(
            root=Path(tmp) / "external_evidence",
            run_id="test_run_ev",
            name="page_0",
            payload=payload,
            metadata=metadata,
        )
        assert result["byte_count"] == len(payload)
        stored = Path(result["path"]).read_bytes()
        assert stored == payload
        import hashlib

        assert result["content_sha256"] == hashlib.sha256(payload).hexdigest()
        assert (
            verify_evidence_pair(
                root=Path(tmp) / "external_evidence", run_id="test_run_ev", name="page_0"
            )
            == "ADMISSIBLE"
        )
        del journal


def test_store_raw_evidence_duplicate_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _make_journal(tmp, "test_run_dup")
        store_raw_evidence(
            root=Path(tmp) / "external_evidence",
            run_id="test_run_dup",
            name="page_0",
            payload=b"bytes",
            metadata={"feed": "alpaca"},
        )
        try:
            store_raw_evidence(
                root=Path(tmp) / "external_evidence",
                run_id="test_run_dup",
                name="page_0",
                payload=b"bytes",
                metadata={"feed": "alpaca"},
            )
            assert False, "Should have raised on duplicate evidence name"
        except DataContractError:
            pass


def test_verify_evidence_pair_orphan_and_tamper() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        resolved = validate_external_evidence_root(Path(tmp) / "external_evidence")
        journal = _make_journal(tmp, "test_run_pair")
        assert (
            verify_evidence_pair(root=resolved, run_id="test_run_pair", name="ghost")
            == "MISSING"
        )
        raw_only = journal._run_dir / "lonely.bin"
        raw_only.write_bytes(b"orphan")
        assert (
            verify_evidence_pair(root=resolved, run_id="test_run_pair", name="lonely")
            == "ORPHAN_RAW"
        )
        receipt_only = journal._run_dir / "ghost2.receipt.json"
        receipt_only.write_bytes(b'{"run_id": "test_run_pair"}')
        assert (
            verify_evidence_pair(root=resolved, run_id="test_run_pair", name="ghost2")
            == "ORPHAN_RECEIPT"
        )
        store_raw_evidence(
            root=resolved, run_id="test_run_pair", name="live",
            payload=b"live bytes", metadata={"feed": "alpaca"},
        )
        live_bin = journal._run_dir / "live.bin"
        live_bin.write_bytes(b"tampered bytes")
        assert (
            verify_evidence_pair(root=resolved, run_id="test_run_pair", name="live")
            == "HASH_MISMATCH"
        )
        del journal


def test_store_raw_evidence_bad_name() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            store_raw_evidence(
                root=Path(tmp), run_id="test_run_006", name="../evil_evidence",
                payload=b"test data", metadata={"feed": "alpaca"},
            )
            assert False, "Should have raised DataContractError for bad name"
        except DataContractError:
            pass


def test_store_raw_evidence_empty_payload() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            store_raw_evidence(
                root=Path(tmp), run_id="test_run_007", name="valid_name",
                payload=b"", metadata={"feed": "alpaca"},
            )
            assert False, "Should have raised DataContractError for empty payload"
        except DataContractError:
            pass


def test_store_raw_evidence_metadata_schema() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _make_journal(tmp, "test_run_meta")
        root = Path(tmp) / "external_evidence"
        try:
            store_raw_evidence(
                root=root, run_id="test_run_meta", name="m1",
                payload=b"x", metadata={"unknown_field": "v"},
            )
            assert False, "Should have raised for unknown metadata key"
        except DataContractError:
            pass
        try:
            store_raw_evidence(
                root=root, run_id="test_run_meta", name="m2",
                payload=b"x", metadata={"api_key": "K" * 8},
            )
            assert False, "Should have raised for secret-bearing metadata key"
        except DataContractError:
            pass
        try:
            store_raw_evidence(
                root=root, run_id="test_run_meta", name="m3",
                payload=b"x", metadata={"note": "bearer abcdefghijklmnop"},
            )
            assert False, "Should have raised for secret-bearing metadata value"
        except DataContractError:
            pass
        try:
            store_raw_evidence(
                root=root, run_id="test_run_meta", name="m4",
                payload=b"x", metadata={"page_index": "zero"},
            )
            assert False, "Should have raised for mistyped metadata value"
        except DataContractError:
            pass
        result = store_raw_evidence(
            root=root, run_id="test_run_meta", name="m5",
            payload=b"x", metadata={"feed": "iex", "page_index": 2},
        )
        assert result["byte_count"] == 1


def test_redact_secrets_in_journal() -> None:
    detail1 = "apikey: secret1234567890"
    redacted1 = redact_secrets(detail1)
    assert "[REDACTED]" in redacted1
    assert "secret1234567890" not in redacted1
    detail2 = "Authorization: bearer eyJhbtoken12345"
    redacted2 = redact_secrets(detail2)
    assert "[REDACTED]" in redacted2
    assert "eyJhbtoken12345" not in redacted2
    detail3 = "api-key: mysecret123 and authorization: bearer tokenabc123"
    redacted3 = redact_secrets(detail3)
    assert "[REDACTED]" in redacted3
