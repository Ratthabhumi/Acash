"""Unit and adversarial tests for Phase 10 Operational Event Ledger & Telemetry Store (Slice 3).

Tests:
- Empty ledger initialization and genesis properties.
- Sequential event appending and SHA-256 hash chaining.
- Monotonic sequence verification and duplicate cycle_id rejection.
- Process crash and restart recovery with chain integrity.
- Tamper and corruption fail-closed defense (JSON corruption, broken digests, sequence gaps).
- Full ledger replay and audit verification.
- Zero broker execution authority on OperationalLedger.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.runtime.ledger import GENESIS_PREVIOUS_DIGEST, OperationalLedger
from acash.runtime.schema import (
    CycleIdentity,
    CycleOutcome,
    OperationalCycleEvent,
    RuntimeHealthStatus,
    RuntimeRegime,
)


def _create_sample_event(
    cycle_id: str,
    sequence: int,
    previous_digest: str,
    outcome: CycleOutcome = CycleOutcome.SUCCESS,
) -> OperationalCycleEvent:
    now = datetime(2026, 9, 2, 14, 0, sequence, tzinfo=timezone.utc)
    cid = CycleIdentity(
        cycle_id=cycle_id,
        as_of_utc=now,
        regime=RuntimeRegime.REBALANCE_PULSE,
        sequence_number=sequence,
    )
    return OperationalCycleEvent(
        cycle_identity=cid,
        wall_clock_utc=now,
        runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
        cycle_outcome=outcome,
        previous_event_digest=previous_digest,
    )


# ============================================================================
# 1. INITIALIZATION & SEQUENTIAL APPEND TESTS
# ============================================================================


def test_empty_ledger_initialization(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"
    ledger = OperationalLedger(persistence_path=ledger_path)

    assert ledger.event_count == 0
    assert ledger.last_sequence == -1
    assert ledger.last_event_digest == GENESIS_PREVIOUS_DIGEST
    assert ledger.read_all_events() == []

    is_valid, count, head_digest = ledger.verify_ledger_integrity()
    assert is_valid is True
    assert count == 0
    assert head_digest == GENESIS_PREVIOUS_DIGEST


def test_sequential_append_and_hash_chaining(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"
    ledger = OperationalLedger(persistence_path=ledger_path)

    # Append Event 0
    e0 = _create_sample_event("CYCLE_000", 0, GENESIS_PREVIOUS_DIGEST)
    ledger.append_event(e0)
    assert ledger.event_count == 1
    assert ledger.last_sequence == 0
    assert ledger.last_event_digest == e0.event_digest

    # Append Event 1
    e1 = _create_sample_event("CYCLE_001", 1, e0.event_digest)
    ledger.append_event(e1)
    assert ledger.event_count == 2
    assert ledger.last_sequence == 1
    assert ledger.last_event_digest == e1.event_digest

    # Append Event 2
    e2 = _create_sample_event("CYCLE_002", 2, e1.event_digest)
    ledger.append_event(e2)
    assert ledger.event_count == 3
    assert ledger.last_sequence == 2
    assert ledger.last_event_digest == e2.event_digest

    # Verify read all events
    events = ledger.read_all_events()
    assert len(events) == 3
    assert events[0].event_digest == e0.event_digest
    assert events[1].event_digest == e1.event_digest
    assert events[2].event_digest == e2.event_digest


# ============================================================================
# 2. IDEMPOTENCY & REPLAY PROTECTION TESTS
# ============================================================================


def test_ledger_rejects_duplicate_cycle_id(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"
    ledger = OperationalLedger(persistence_path=ledger_path)

    e0 = _create_sample_event("CYCLE_000", 0, GENESIS_PREVIOUS_DIGEST)
    ledger.append_event(e0)

    # Attempt to append duplicate cycle_id "CYCLE_000" with sequence 1
    e_dup = _create_sample_event("CYCLE_000", 1, e0.event_digest)
    with pytest.raises(DataContractError, match="Duplicate Event Rejected"):
        ledger.append_event(e_dup)


def test_ledger_rejects_out_of_order_sequence(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"
    ledger = OperationalLedger(persistence_path=ledger_path)

    e0 = _create_sample_event("CYCLE_000", 0, GENESIS_PREVIOUS_DIGEST)
    ledger.append_event(e0)

    # Attempt to append sequence 5 (expected 1)
    e_jump = _create_sample_event("CYCLE_005", 5, e0.event_digest)
    with pytest.raises(DataContractError, match="Invalid Event Sequence: expected 1, got 5"):
        ledger.append_event(e_jump)


def test_ledger_rejects_broken_hash_chain(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"
    ledger = OperationalLedger(persistence_path=ledger_path)

    e0 = _create_sample_event("CYCLE_000", 0, GENESIS_PREVIOUS_DIGEST)
    ledger.append_event(e0)

    # Attempt to append event with bogus previous_event_digest
    bogus_prev = "a" * 64
    e1_broken = _create_sample_event("CYCLE_001", 1, bogus_prev)
    with pytest.raises(DataContractError, match="Broken Event Chain"):
        ledger.append_event(e1_broken)


# ============================================================================
# 3. RESTART RECOVERY & PERSISTENCE TESTS
# ============================================================================


def test_ledger_restart_recovery_and_append_continuation(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"

    # Instance 1: Append 2 events
    ledger1 = OperationalLedger(persistence_path=ledger_path)
    e0 = _create_sample_event("CYCLE_000", 0, GENESIS_PREVIOUS_DIGEST)
    e1 = _create_sample_event("CYCLE_001", 1, e0.event_digest)
    ledger1.append_event(e0)
    ledger1.append_event(e1)

    # Simulate process crash and restart: create Instance 2 from same file
    ledger2 = OperationalLedger(persistence_path=ledger_path)
    assert ledger2.event_count == 2
    assert ledger2.last_sequence == 1
    assert ledger2.last_event_digest == e1.event_digest

    # Continue appending cleanly
    e2 = _create_sample_event("CYCLE_002", 2, e1.event_digest)
    ledger2.append_event(e2)
    assert ledger2.event_count == 3
    assert ledger2.last_sequence == 2
    assert ledger2.last_event_digest == e2.event_digest


# ============================================================================
# 4. TAMPER & CORRUPTION FAIL-CLOSED DEFENSE TESTS
# ============================================================================


def test_ledger_detects_tampered_event_payload(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"
    ledger = OperationalLedger(persistence_path=ledger_path)

    e0 = _create_sample_event("CYCLE_000", 0, GENESIS_PREVIOUS_DIGEST)
    ledger.append_event(e0)

    # Tamper with the raw JSON file (modify outcome)
    with open(ledger_path, "r", encoding="utf-8") as f:
        content = f.read()

    tampered_content = content.replace('"SUCCESS"', '"RISK_REJECTED"')
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write(tampered_content)

    # Re-instantiating ledger must detect digest mismatch fail-closed
    with pytest.raises(DataContractError):
        OperationalLedger(persistence_path=ledger_path)


def test_ledger_detects_broken_hash_chain_on_startup(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"
    ledger = OperationalLedger(persistence_path=ledger_path)

    e0 = _create_sample_event("CYCLE_000", 0, GENESIS_PREVIOUS_DIGEST)
    # Create e1 with wrong previous digest (valid internal digest, but broken chain from e0)
    e1_wrong_chain = _create_sample_event("CYCLE_001", 1, "f" * 64)

    # Write manually to file
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write(e0.model_dump_json() + "\n")
        f.write(e1_wrong_chain.model_dump_json() + "\n")

    with pytest.raises(DataContractError, match="Ledger Hash Chain Broken"):
        OperationalLedger(persistence_path=ledger_path)


def test_ledger_detects_malformed_json(tmp_path: Path) -> None:
    ledger_path = tmp_path / "operational_ledger.jsonl"
    ledger = OperationalLedger(persistence_path=ledger_path)

    e0 = _create_sample_event("CYCLE_000", 0, GENESIS_PREVIOUS_DIGEST)
    ledger.append_event(e0)

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write("{malformed json line\n")

    with pytest.raises(DataContractError, match="Ledger Corrupted"):
        OperationalLedger(persistence_path=ledger_path)


# ============================================================================
# 5. AUTHORITY BOUNDARY TESTS
# ============================================================================


def test_ledger_zero_broker_execution_authority() -> None:
    forbidden = [
        "submit_order",
        "execute_order",
        "cancel_order",
        "send_wire",
        "get_broker_client",
        "evaluate_risk",
        "optimize_portfolio",
    ]
    for m in forbidden:
        assert not hasattr(OperationalLedger, m)
