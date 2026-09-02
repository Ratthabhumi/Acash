"""Unit tests for Phase 11 Ingestion, Sequence Guards & Forensic Ledger Adapter.

Verifies:
1. Per-strategy stream isolation and monotonic sequence enforcement (0, 1, 2, ...).
2. Fail-closed defense on sequence gaps (initial and intermediate) marking stream permanently blocked.
3. Monotonic as_of_utc timestamp invariant (as_of[k] > as_of[k-1]).
4. Duplicate observation_id and composite (strategy_id, sequence) identity rejection.
5. Ingestion of invalid telemetry flags stream as invalid (enabling MONITORING_BLOCKED downstream).
6. MonitoringEvidenceLedger domain adapter preserving Tier 1 digests in OperationalCycleEvent envelopes.
7. Cryptographic Tier 2 hash chaining across both drift and execution evidence.
8. Ledger restart integrity verification from disk.
9. Tamper detection on corrupted JSON, broken hash chains, and duplicate replay attacks.
10. Crash safety: partial/truncated write detection on startup.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.ingestion import (
    ForwardTelemetryIngestor,
    StreamIntegrityState,
    StreamStatus,
)
from acash.monitoring.ledger import MonitoringEvidenceLedger
from acash.monitoring.schema import (
    ExecutionCostEvidence,
    ForwardGovernanceRecommendation,
    ForwardHealthPolicy,
    ForwardHealthState,
    ForwardObservation,
    ForwardWindowMetrics,
    StrategyForwardDriftEvidence,
)
from acash.monitoring.state_machine import ForwardHealthStateMachine
from acash.runtime.ledger import GENESIS_PREVIOUS_DIGEST

BASE_TIME = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
VALID_DOSSIER_DIGEST = "a" * 64
VALID_POLICY_DIGEST = "b" * 64


def _create_forward_observation(
    obs_id: str,
    strat_id: str,
    seq: int,
    as_of: datetime,
    is_telemetry_valid: bool = True,
) -> ForwardObservation:
    """Helper creating a valid ForwardObservation."""
    return ForwardObservation(
        observation_id=obs_id,
        strategy_id=strat_id,
        dossier_digest=VALID_DOSSIER_DIGEST,
        as_of_utc=as_of,
        wall_clock_utc=as_of + timedelta(milliseconds=10),
        realized_return=Decimal("0.005"),
        gross_pnl_usd=Decimal("500.00"),
        net_pnl_usd=Decimal("490.00"),
        turnover_ratio=Decimal("0.10"),
        observation_sequence=seq,
        is_telemetry_valid=is_telemetry_valid,
    )


def _create_drift_evidence(
    evidence_id: str,
    as_of: datetime,
    wall_clock: datetime | None = None,
    strategy_id: str = "STRAT_01",
    health_state: ForwardHealthState = ForwardHealthState.HEALTHY,
    recommendation: ForwardGovernanceRecommendation = ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
    policy_digest: str = VALID_POLICY_DIGEST,
) -> StrategyForwardDriftEvidence:
    """Helper creating a valid StrategyForwardDriftEvidence with complete metrics."""
    metrics = ForwardWindowMetrics(
        window_size=60,
        observation_count=60,
        mean_realized_return_annualized=Decimal("0.185"),
        realized_volatility_annualized=Decimal("0.120"),
        realized_sharpe_ratio=Decimal("1.54"),
        max_drawdown=Decimal("0.045"),
        inception_max_drawdown=Decimal("0.062"),
        hit_rate=Decimal("0.58"),
        tracking_error_annualized=Decimal("0.035"),
        t_stat_decay=Decimal("2.41"),
        expected_vs_realized_divergence_bps=Decimal("-12.5"),
    )
    wc = wall_clock if wall_clock is not None else as_of + timedelta(milliseconds=5)
    return StrategyForwardDriftEvidence(
        evidence_id=evidence_id,
        strategy_id=strategy_id,
        dossier_digest=VALID_DOSSIER_DIGEST,
        as_of_utc=as_of,
        wall_clock_utc=wc,
        health_state=health_state,
        recommendation=recommendation,
        metrics=metrics,
        policy_digest=policy_digest,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=(),
    )


# ============================================================================
# 1. FORWARD TELEMETRY INGESTION TESTS
# ============================================================================

def test_valid_per_strategy_sequential_ingestion() -> None:
    """Sequential observations with strictly increasing timestamps ingest cleanly per strategy."""
    ingestor = ForwardTelemetryIngestor()

    t0 = BASE_TIME
    obs_a0 = _create_forward_observation("OBS_A0", "STRAT_A", 0, t0)
    obs_a1 = _create_forward_observation("OBS_A1", "STRAT_A", 1, t0 + timedelta(minutes=5))
    obs_b0 = _create_forward_observation("OBS_B0", "STRAT_B", 0, t0)

    res_a0 = ingestor.ingest_observation(obs_a0)
    res_a1 = ingestor.ingest_observation(obs_a1)
    res_b0 = ingestor.ingest_observation(obs_b0)

    assert res_a0.observation_id == "OBS_A0"
    assert res_a1.observation_id == "OBS_A1"
    assert res_b0.observation_id == "OBS_B0"

    status_a = ingestor.get_stream_status("STRAT_A")
    assert status_a is not None
    assert status_a.last_sequence == 1
    assert status_a.observation_count == 2
    assert status_a.is_telemetry_valid is True

    status_b = ingestor.get_stream_status("STRAT_B")
    assert status_b is not None
    assert status_b.last_sequence == 0
    assert status_b.observation_count == 1


def test_initial_sequence_gap_rejected() -> None:
    """Strategy stream cannot start at sequence > 0 (fail-closed gap defense)."""
    ingestor = ForwardTelemetryIngestor()

    obs = _create_forward_observation("OBS_GAP0", "STRAT_A", 1, BASE_TIME)  # Starts at 1 instead of 0

    with pytest.raises(DataContractError, match="SEQUENCE_GAP_DETECTED"):
        ingestor.ingest_observation(obs)

    # Stream is permanently marked invalid
    assert ingestor.is_telemetry_valid("STRAT_A") is False


def test_intermediate_sequence_gap_rejected_and_stream_blocked() -> None:
    """Missing sequence (e.g. 0 -> 2) raises error and permanently blocks the stream."""
    ingestor = ForwardTelemetryIngestor()
    t0 = BASE_TIME

    # Seq 0 succeeds
    ingestor.ingest_observation(_create_forward_observation("OBS_0", "STRAT_A", 0, t0))

    # Seq 2 arrives (missing seq 1!)
    with pytest.raises(DataContractError, match="SEQUENCE_GAP_DETECTED"):
        ingestor.ingest_observation(_create_forward_observation("OBS_2", "STRAT_A", 2, t0 + timedelta(minutes=10)))

    assert ingestor.is_telemetry_valid("STRAT_A") is False

    # Subsequent observation without explicit reinitialization is rejected
    with pytest.raises(DataContractError, match="STREAM_BLOCKED"):
        ingestor.ingest_observation(_create_forward_observation("OBS_1", "STRAT_A", 1, t0 + timedelta(minutes=5)))


def test_stream_recovery_after_gap_with_explicit_reinitialization() -> None:
    """Explicit stream recovery/reinitialization boundary after a sequence gap outage.

    Contract Invariants:
    1. Stream gap marks integrity_state = BLOCKED.
    2. Attempting to continue the old sequence without reinitialization fails closed.
    3. reinitialize_stream() advances epoch_index, restores VALID state, resets sequence to -1.
    4. In the new epoch, sequence must restart at 0 (does NOT continue old sequence or heal missing bars).
    5. Observation IDs from previous epochs cannot be replayed.
    """
    ingestor = ForwardTelemetryIngestor()
    t0 = BASE_TIME

    # Epoch 0: Ingest seq 0
    obs0 = _create_forward_observation("OBS_0", "STRAT_A", 0, t0)
    ingestor.ingest_observation(obs0)

    # Gap: Observation 2 arrives (missing 1) -> stream blocked!
    obs2 = _create_forward_observation("OBS_2", "STRAT_A", 2, t0 + timedelta(minutes=10))
    with pytest.raises(DataContractError, match="SEQUENCE_GAP_DETECTED"):
        ingestor.ingest_observation(obs2)

    status_blocked = ingestor.get_stream_status("STRAT_A")
    assert status_blocked is not None
    assert status_blocked.integrity_state == StreamIntegrityState.BLOCKED
    assert ingestor.is_telemetry_valid("STRAT_A") is False

    # Attempting to auto-resume from 3 or 1 is strictly rejected
    with pytest.raises(DataContractError, match="STREAM_BLOCKED"):
        ingestor.ingest_observation(_create_forward_observation("OBS_3", "STRAT_A", 3, t0 + timedelta(minutes=15)))

    # Explicit Operator/Supervisor Stream Reinitialization
    status_reinit = ingestor.reinitialize_stream("STRAT_A", recovery_reason="Network gap investigated; epoch re-anchored")
    assert status_reinit.epoch_index == 1
    assert status_reinit.last_sequence == -1
    assert status_reinit.integrity_state == StreamIntegrityState.VALID
    assert ingestor.is_telemetry_valid("STRAT_A") is True

    # In Epoch 1: Attempting to start at sequence 1 fails closed (must start at 0!)
    with pytest.raises(DataContractError, match="SEQUENCE_GAP_DETECTED"):
        ingestor.ingest_observation(_create_forward_observation("OBS_E1_SEQ1", "STRAT_A", 1, t0 + timedelta(minutes=20)))

    # Since attempting sequence 1 blocked Epoch 1, reinitialize again to test clean epoch start
    ingestor.reinitialize_stream("STRAT_A", recovery_reason="Re-anchoring clean epoch after test error")
    assert ingestor.is_telemetry_valid("STRAT_A") is True

    # In clean Epoch 2: Starting cleanly at sequence 0 succeeds!
    t1 = t0 + timedelta(minutes=20)
    obs_e2_0 = _create_forward_observation("OBS_E2_0", "STRAT_A", 0, t1)
    res_e2_0 = ingestor.ingest_observation(obs_e2_0)
    assert res_e2_0.observation_sequence == 0

    # In clean Epoch 2: Sequence 1 follows sequence 0 cleanly
    obs_e2_1 = _create_forward_observation("OBS_E2_1", "STRAT_A", 1, t1 + timedelta(minutes=5))
    res_e2_1 = ingestor.ingest_observation(obs_e2_1)
    assert res_e2_1.observation_sequence == 1

    # Replay of old observation ID from Epoch 0 is rejected fail-closed
    with pytest.raises(DataContractError, match="DUPLICATE_OBSERVATION_REJECTED"):
        ingestor.ingest_observation(_create_forward_observation("OBS_0", "STRAT_A", 2, t1 + timedelta(minutes=10)))


def test_state_machine_recovery_end_to_end_with_ingestor() -> None:
    """End-to-end integration: Ingestor telemetry outage -> MONITORING_BLOCKED -> reinitialization -> INSUFFICIENT_EVIDENCE."""
    ingestor = ForwardTelemetryIngestor()
    policy = ForwardHealthPolicy()
    state_machine = ForwardHealthStateMachine(policy)

    # 1. Telemetry failure on ingestor
    obs_bad = _create_forward_observation("OBS_ERR", "STRAT_A", 0, BASE_TIME, is_telemetry_valid=False)
    ingestor.ingest_observation(obs_bad)
    assert ingestor.is_telemetry_valid("STRAT_A") is False

    # 2. State machine detects invalid telemetry -> enters MONITORING_BLOCKED
    metrics = ForwardWindowMetrics(
        window_size=60,
        observation_count=60,
        mean_realized_return_annualized=Decimal("0.185"),
        realized_volatility_annualized=Decimal("0.120"),
        realized_sharpe_ratio=Decimal("1.54"),
        max_drawdown=Decimal("0.045"),
        inception_max_drawdown=Decimal("0.062"),
        hit_rate=Decimal("0.58"),
        t_stat_decay=Decimal("2.41"),
    )
    res1 = state_machine.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics,
        is_telemetry_valid=ingestor.is_telemetry_valid("STRAT_A"),
    )
    assert res1.state == ForwardHealthState.MONITORING_BLOCKED
    assert res1.recommendation == ForwardGovernanceRecommendation.MONITORING_BLOCKED_FLAG

    # 3. Telemetry Stream Reinitialized
    ingestor.reinitialize_stream("STRAT_A", recovery_reason="Outage resolved")
    assert ingestor.is_telemetry_valid("STRAT_A") is True

    # 4. State machine evaluates step with restored telemetry:
    # Under Slice 3 contract: transitions to INSUFFICIENT_EVIDENCE to rebuild evidence!
    res2 = state_machine.evaluate_step(
        current_state=ForwardHealthState.MONITORING_BLOCKED,
        metrics=metrics,
        is_telemetry_valid=ingestor.is_telemetry_valid("STRAT_A"),
    )
    assert res2.state == ForwardHealthState.INSUFFICIENT_EVIDENCE
    assert res2.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED
    assert "TELEMETRY_RESTORED_RESET_TO_INSUFFICIENT_EVIDENCE" in res2.drift_flags


def test_out_of_order_timestamp_rejected() -> None:
    """Non-increasing as_of_utc timestamp (as_of[k] <= as_of[k-1]) is strictly rejected."""
    ingestor = ForwardTelemetryIngestor()
    t0 = BASE_TIME

    ingestor.ingest_observation(_create_forward_observation("OBS_0", "STRAT_A", 0, t0))

    # Timestamp is identical to preceding observation (not strictly increasing)
    with pytest.raises(DataContractError, match="TEMPORAL_ORDER_VIOLATION"):
        ingestor.ingest_observation(_create_forward_observation("OBS_1", "STRAT_A", 1, t0))

    assert ingestor.is_telemetry_valid("STRAT_A") is False


def test_duplicate_observation_id_rejected() -> None:
    """Replay of an existing observation_id is rejected."""
    ingestor = ForwardTelemetryIngestor()
    obs0 = _create_forward_observation("OBS_DUP", "STRAT_A", 0, BASE_TIME)

    ingestor.ingest_observation(obs0)

    # Attempt to replay same observation
    with pytest.raises(DataContractError, match="DUPLICATE_OBSERVATION_REJECTED"):
        ingestor.ingest_observation(obs0)


def test_duplicate_composite_identity_rejected() -> None:
    """Re-use of (strategy_id, observation_sequence) with different observation_id is rejected."""
    ingestor = ForwardTelemetryIngestor()
    obs0 = _create_forward_observation("OBS_A", "STRAT_A", 0, BASE_TIME)
    obs0_alt = _create_forward_observation("OBS_B", "STRAT_A", 0, BASE_TIME + timedelta(minutes=1))

    ingestor.ingest_observation(obs0)

    with pytest.raises(DataContractError, match="DUPLICATE_COMPOSITE_IDENTITY"):
        ingestor.ingest_observation(obs0_alt)


def test_upstream_invalid_telemetry_flags_stream() -> None:
    """Observation with is_telemetry_valid=False flags stream for MONITORING_BLOCKED state transition."""
    ingestor = ForwardTelemetryIngestor()
    obs_invalid = _create_forward_observation(
        "OBS_BAD", "STRAT_A", 0, BASE_TIME, is_telemetry_valid=False
    )

    ingested = ingestor.ingest_observation(obs_invalid)
    assert ingested.is_telemetry_valid is False
    assert ingestor.is_telemetry_valid("STRAT_A") is False

    status = ingestor.get_stream_status("STRAT_A")
    assert status is not None
    assert status.is_telemetry_valid is False
    assert status.block_reason == "UPSTREAM_TELEMETRY_INVALID"


# ============================================================================
# 2. MONITORING EVIDENCE LEDGER ADAPTER TESTS
# ============================================================================

def test_record_forward_drift_evidence_happy_path(tmp_path: Path) -> None:
    """Verify recording StrategyForwardDriftEvidence into the forensic ledger adapter."""
    ledger_path = tmp_path / "monitoring_events.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    t0 = BASE_TIME
    evidence = _create_drift_evidence("EVID_DRIFT_01", t0)

    cycle_event = ledger.record_forward_drift_evidence(evidence)

    assert cycle_event.cycle_identity.cycle_id == "EVID_DRIFT_01"
    assert cycle_event.cycle_identity.sequence_number == 0
    assert cycle_event.previous_event_digest == GENESIS_PREVIOUS_DIGEST
    assert len(cycle_event.event_digest) == 64
    # Tier 1 evidence digest is preserved in the envelope
    assert evidence.evidence_digest in cycle_event.active_dossier_digests

    assert ledger.event_count == 1
    assert ledger.last_sequence == 0
    assert ledger.last_event_digest == cycle_event.event_digest

    # Verify retrieval
    retrieved = ledger.get_evidence_by_id("EVID_DRIFT_01")
    assert retrieved is not None
    assert retrieved.evidence_id == "EVID_DRIFT_01"


def test_record_execution_cost_evidence_happy_path(tmp_path: Path) -> None:
    """Verify recording ExecutionCostEvidence with cryptographic chaining."""
    ledger_path = tmp_path / "monitoring_events.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    t0 = BASE_TIME
    drift_evidence = _create_drift_evidence("EVID_DRIFT_01", t0)
    event1 = ledger.record_forward_drift_evidence(drift_evidence)

    cost_evidence = ExecutionCostEvidence(
        evidence_id="EVID_COST_01",
        venue="ALPACA_PAPER",
        symbol="AAPL",
        as_of_utc=t0 + timedelta(hours=1),
        coverage_start_utc=t0,
        coverage_end_utc=t0 + timedelta(hours=1),
        fill_count=100,
        effective_sample_count=100,
        coverage_ratio=Decimal("1.0"),
        mean_gross_drag_bps=Decimal("8.5"),
        mean_net_cost_bps=Decimal("7.5"),
        median_net_cost_bps=Decimal("7.0"),
        p95_gross_drag_bps=Decimal("12.0"),
        standard_error_bps=Decimal("0.5"),
        confidence_interval_95_half_width_bps=Decimal("0.98"),
        is_statistically_reliable=True,
        policy_digest=VALID_POLICY_DIGEST,
    )
    event2 = ledger.record_execution_cost_evidence(cost_evidence)

    assert event2.cycle_identity.cycle_id == "EVID_COST_01"
    assert event2.cycle_identity.sequence_number == 1
    # Tier 2 Hash Chain: event2.previous == event1.digest
    assert event2.previous_event_digest == event1.event_digest
    assert cost_evidence.lineage_digest in event2.execution_manifest_digests

    assert ledger.event_count == 2
    assert ledger.last_sequence == 1


def test_ledger_restart_and_chain_verification(tmp_path: Path) -> None:
    """Verify ledger can be closed and re-opened, validating entire on-disk cryptographic chain."""
    ledger_path = tmp_path / "forensic_events.jsonl"
    ledger1 = MonitoringEvidenceLedger(ledger_path)

    t0 = BASE_TIME
    for i in range(3):
        ev = _create_drift_evidence(f"EVID_{i:03d}", t0 + timedelta(minutes=i * 5))
        ledger1.record_forward_drift_evidence(ev)

    last_digest = ledger1.last_event_digest

    # Reopen ledger in a new instance (triggers disk replay and verification)
    ledger2 = MonitoringEvidenceLedger(ledger_path)
    assert ledger2.event_count == 3
    assert ledger2.last_sequence == 2
    assert ledger2.last_event_digest == last_digest

    # Run full integrity audit
    is_valid, count, head_digest = ledger2.verify_ledger_integrity()
    assert is_valid is True
    assert count == 3
    assert head_digest == last_digest


# ============================================================================
# 3. ADVERSARIAL, TAMPER & CRASH DEFENSE TESTS
# ============================================================================

def test_corrupted_line_detection_on_restart(tmp_path: Path) -> None:
    """Malformed JSON line on disk is detected fail-closed on restart."""
    ledger_path = tmp_path / "corrupt_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    ev = _create_drift_evidence("EVID_001", BASE_TIME)
    ledger.record_forward_drift_evidence(ev)

    # Append corrupt garbage to disk
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write("{corrupt_garbage_json_line\n")

    # Restarting ledger must detect corruption immediately
    with pytest.raises(DataContractError, match="Ledger Corrupted"):
        MonitoringEvidenceLedger(ledger_path)


def test_broken_hash_chain_tamper_detection(tmp_path: Path) -> None:
    """Tampering with an event digest or previous digest breaks the hash chain and fails closed."""
    ledger_path = tmp_path / "tampered_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    t0 = BASE_TIME
    for i in range(2):
        ev = _create_drift_evidence(f"EVID_{i:03d}", t0 + timedelta(minutes=i * 5))
        ledger.record_forward_drift_evidence(ev)

    # Tamper with line 2's previous_event_digest in the file
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    tampered_line = lines[1].replace(ledger.read_all_events()[0].event_digest, "f" * 64)
    ledger_path.write_text(lines[0] + "\n" + tampered_line + "\n", encoding="utf-8")

    with pytest.raises(DataContractError, match="Ledger Corrupted|Ledger Hash Chain Broken|Event Digest Mismatch"):
        MonitoringEvidenceLedger(ledger_path)


def test_chain_breakage_with_valid_envelope_digest(tmp_path: Path) -> None:
    """When an event has an internally valid digest but breaks the chain from genesis, it fails closed."""
    from acash.runtime.schema import CycleIdentity, CycleOutcome, OperationalCycleEvent, RuntimeHealthStatus, RuntimeRegime

    ledger_path = tmp_path / "chain_break_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    t0 = BASE_TIME
    ev0 = _create_drift_evidence("EVID_000", t0)
    ledger.record_forward_drift_evidence(ev0)

    # Construct event 1 with valid internal hash but pointing to wrong previous_event_digest
    broken_event = OperationalCycleEvent(
        cycle_identity=CycleIdentity(
            cycle_id="EVID_001_BROKEN",
            as_of_utc=t0 + timedelta(minutes=5),
            regime=RuntimeRegime.POST_MARKET_CLOSE,
            sequence_number=1,
        ),
        wall_clock_utc=t0 + timedelta(minutes=5),
        runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
        cycle_outcome=CycleOutcome.SUCCESS,
        previous_event_digest="f" * 64,  # Does not match event 0 digest!
    )

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(broken_event.model_dump_json() + "\n")

    with pytest.raises(DataContractError, match="Ledger Hash Chain Broken"):
        MonitoringEvidenceLedger(ledger_path)


def test_duplicate_evidence_id_rejected(tmp_path: Path) -> None:
    """Duplicate evidence_id recording attempt is rejected fail-closed."""
    ledger_path = tmp_path / "dup_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    ev = _create_drift_evidence("EVID_DUPLICATE", BASE_TIME)
    ledger.record_forward_drift_evidence(ev)

    with pytest.raises(DataContractError, match="Duplicate Evidence Rejected"):
        ledger.record_forward_drift_evidence(ev)


def test_temporal_inversion_rejected(tmp_path: Path) -> None:
    """Temporal inversion where wall_clock_utc < as_of_utc is rejected."""
    ledger_path = tmp_path / "temporal_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    t0 = BASE_TIME
    inverted_ev = _create_drift_evidence(
        "EVID_INVERTED",
        as_of=t0,
        wall_clock=t0 - timedelta(seconds=10),  # Inverted!
    )

    with pytest.raises(DataContractError, match="Temporal Inversion"):
        ledger.record_forward_drift_evidence(inverted_ev)
