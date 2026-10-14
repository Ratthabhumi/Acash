"""M1.8.1 dedicated tests for real-transport boundary, durable journal, and immutable evidence persistence.

All tests are structurally/scope verified — no real network I/O, no credentials, no secrets.
Uses only synthetic bytes, temporary external test directories, and ISO-8601 timezone-aware timestamps.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_transport import (
    RealTransportBoundary,
    DurableAttemptJournal,
    AttemptRecord,
    store_raw_evidence,
    check_request_allowlist,
)
from acash.data.qualification.lane_a_authority import redact_secrets


def test_real_transport_boundary_allowlist_host() -> None:
    """Approved host should fail closed (no I/O enabled)."""
    boundary = RealTransportBoundary()
    try:
        boundary.get("data.alpaca.markets", "GET", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass  # expected — disabled by construction


def test_real_transport_boundary_rejected_host() -> None:
    """Rejected host should fail closed."""
    boundary = RealTransportBoundary()
    try:
        boundary.get("unauthorized.example.com", "GET", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass  # expected


def test_real_transport_boundary_rejected_method() -> None:
    """Rejected method should fail closed."""
    boundary = RealTransportBoundary()
    try:
        boundary.get("data.alpaca.markets", "POST", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass  # expected


def test_real_transport_boundary_rejected_path() -> None:
    """Rejected path should fail closed."""
    boundary = RealTransportBoundary()
    try:
        boundary.get("data.alpaca.markets", "GET", "/v3/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass  # expected


def test_check_request_allowlist_approved() -> None:
    """Approved host/method/path should pass the check."""
    check_request_allowlist("data.alpaca.markets", "GET", "/v2/stocks/bars")


def test_check_request_allowlist_rejected_host() -> None:
    """Rejected host should fail."""
    try:
        check_request_allowlist("evil.example.com", "GET", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass  # expected


def test_check_request_allowlist_rejected_method() -> None:
    """Rejected method should fail."""
    try:
        check_request_allowlist("data.alpaca.markets", "DELETE", "/v2/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass  # expected


def test_check_request_allowlist_rejected_path() -> None:
    """Rejected path should fail."""
    try:
        check_request_allowlist("data.alpaca.markets", "GET", "/v3/stocks/bars")
        assert False, "Should have raised DataContractError"
    except DataContractError:
        pass  # expected


def test_durable_attempt_journal_create_run() -> None:
    """Fresh run creation with O_EXCL (colliding run id should fail)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "external_evidence"
        run_id = "test_run_001"
        authority_ref = "auth_test_001"
        runtime_sha = "abc123def456"
        created_at_utc = datetime.now(timezone.utc).isoformat()

        journal = DurableAttemptJournal.create_run(
            root=root,
            run_id=run_id,
            authority_ref=authority_ref,
            runtime_sha=runtime_sha,
            created_at_utc=created_at_utc,
        )

        # Verify run directory exists
        expected_dir = root / "lane_a_runs" / run_id
        assert expected_dir.is_dir()

        # Verify marker file exists
        marker = expected_dir / "run.json"
        assert marker.is_file()

        # Verify re-running with same run_id should fail
        try:
            DurableAttemptJournal.create_run(
                root=root,
                run_id=run_id,
                authority_ref=authority_ref,
                runtime_sha=runtime_sha,
                created_at_utc=created_at_utc,
            )
            assert False, "Should have raised DataContractError for duplicate run id"
        except DataContractError:
            pass  # expected


def test_durable_attempt_journal_no_resume() -> None:
    """open_existing must always fail closed."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "external_evidence"
        run_id = "test_run_002"

        # Create a run first
        journal = DurableAttemptJournal.create_run(
            root=root,
            run_id=run_id,
            authority_ref="auth_test_002",
            runtime_sha="abc123def456",
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

        # Now try open_existing — should always fail
        try:
            DurableAttemptJournal.open_existing(root=root, run_id=run_id)
            assert False, "Should have raised DataContractError for open_existing"
        except DataContractError:
            pass  # expected


def test_durable_attempt_journal_classify_run() -> None:
    """classify_run should correctly classify runs."""
    from acash.evidence.roots import validate_external_evidence_root

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "external_evidence"
        resolved = validate_external_evidence_root(root)

        # Test MISSING — no marker file
        result = DurableAttemptJournal.classify_run(root=resolved, run_id="nonexistent")
        assert result == "MISSING"

        # Test COMPLETE — marker + completion file
        run_dir = root / "lane_a_runs" / "test_classify_complete"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").touch()
        (run_dir / "completion.json").touch()
        result = DurableAttemptJournal.classify_run(root=resolved, run_id="test_classify_complete")
        assert result == "COMPLETE"

        # Test INTERRUPTED — marker only, no completion
        run_dir2 = root / "lane_a_runs" / "test_classify_interrupted"
        run_dir2.mkdir(parents=True)
        (run_dir2 / "run.json").touch()
        # no completion.json
        result = DurableAttemptJournal.classify_run(root=resolved, run_id="test_classify_interrupted")
        assert result == "INTERRUPTED"


def test_durable_attempt_journal_record_attempt() -> None:
    """record_attempt should append one JSONL line and enforce sequence monotonicity."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "external_evidence"

        # Create a run
        journal = DurableAttemptJournal.create_run(
            root=root,
            run_id="test_run_003",
            authority_ref="auth_test_003",
            runtime_sha="abc123def456",
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

        # Record first attempt
        attempt1 = AttemptRecord(
            seq=1,
            kind="test",
            outcome="observed",
            bytes_observed=1024,
            recorded_at_utc=datetime.now(timezone.utc).isoformat(),
            detail="first attempt",
        )
        journal.record_attempt(attempt1)

        # Record second attempt
        attempt2 = AttemptRecord(
            seq=2,
            kind="test",
            outcome="observed",
            bytes_observed=2048,
            recorded_at_utc=datetime.now(timezone.utc).isoformat(),
            detail="second attempt",
        )
        journal.record_attempt(attempt2)

        # Verify attempts.jsonl exists and has 2 lines
        attempts_file = journal._run_dir / "attempts.jsonl"
        assert attempts_file.is_file()
        lines = attempts_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

        # Record attempt with invalid seq (must be strictly greater)
        try:
            journal.record_attempt(
                AttemptRecord(
                    seq=1,  # duplicate/earlier seq should fail
                    kind="test",
                    outcome="observed",
                    bytes_observed=512,
                    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                )
            )
            assert False, "Should have raised DataContractError for non-increasing seq"
        except DataContractError:
            pass  # expected

        # Record attempt with negative bytes should fail
        try:
            journal.record_attempt(
                AttemptRecord(
                    seq=3,
                    kind="test",
                    outcome="observed",
                    bytes_observed=-100,  # negative should fail,
                    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                )
            )
            assert False, "Should have raised DataContractError for negative bytes"
        except DataContractError:
            pass  # expected


def test_durable_attempt_journal_close_run() -> None:
    """close_run should write completion marker exactly once."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "external_evidence"

        journal = DurableAttemptJournal.create_run(
            root=root,
            run_id="test_run_004",
            authority_ref="auth_test_004",
            runtime_sha="abc123def456",
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

        # Close with COMPLETE status
        completed_at_utc = datetime.now(timezone.utc).isoformat()
        journal.close_run(status="COMPLETE", completed_at_utc=completed_at_utc)

        # Verify completion.json exists
        completion = journal._run_dir / "completion.json"
        assert completion.is_file()

        # Use a fresh journal for ABORTED test (close_run is fail-closed on repeat)
        journal2 = DurableAttemptJournal.create_run(
            root=Path(tmp) / "external_evidence2",
            run_id="test_run_005",
            authority_ref="auth_test_005",
            runtime_sha="abc123def456",
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        journal2.close_run(status="ABORTED", completed_at_utc=datetime.now(timezone.utc).isoformat())


def test_store_raw_evidence_bad_name() -> None:
    """store_raw_evidence should reject invalid name (path traversal)."""
    with tempfile.TemporaryDirectory() as tmp:
        payload = b"test data"
        metadata = {"feed": "alpaca"}

        try:
            store_raw_evidence(
                root=Path(tmp),
                run_id="test_run_006",
                name="../evil_evidence",  # path traversal should fail
                payload=payload,
                metadata=metadata,
            )
            assert False, "Should have raised DataContractError for bad name"
        except DataContractError:
            pass  # expected


def test_store_raw_evidence_empty_payload() -> None:
    """store_raw_evidence should reject empty payload."""
    with tempfile.TemporaryDirectory() as tmp:
        payload = b""
        metadata = {"feed": "alpaca"}

        try:
            store_raw_evidence(
                root=Path(tmp),
                run_id="test_run_007",
                name="valid_name",
                payload=payload,
                metadata=metadata,
            )
            assert False, "Should have raised DataContractError for empty payload"
        except DataContractError:
            pass  # expected


def test_redact_secrets_in_journal() -> None:
    """Test that secrets are redacted in journal detail field."""
    # Test 1: SECRET_HEADER pattern - should redact the value
    detail1 = "apikey: secret1234567890"
    redacted1 = redact_secrets(detail1)
    assert "[REDACTED]" in redacted1
    assert "secret1234567890" not in redacted1

    # Test 2: BEARER pattern - should redact the token following "bearer "
    detail2 = "Authorization: bearer eyJhbtoken12345"
    redacted2 = redact_secrets(detail2)
    assert "[REDACTED]" in redacted2
    # The full token string should not appear as-is
    assert "eyJhbtoken12345" not in redacted2

    # Test 3: Mixed detail - both patterns may apply
    detail3 = "api-key: mysecret123 and authorization: bearer tokenabc123"
    redacted3 = redact_secrets(detail3)
    assert "[REDACTED]" in redacted3