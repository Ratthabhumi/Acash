"""Cross-Phase End-to-End Integration Pipeline Tests for Phase 11.

Proves the complete decoupled observational & forensic pipeline:
1. End-to-End Drift Monitoring Lineage:
   Phase 8.5 AlphaQualificationDossier
          │ (dossier_digest)
          ▼
   ForwardTelemetryIngestor (Stream Sequence & Timestamp Validation)
          │
          ▼
   ForwardMetricsCalculator (Discrete Simple Returns, Multiplicative Compounding)
          │
          ▼
   ForwardHealthStateMachine (Asymmetric Hysteresis, Cooldown, Reset)
          │
          ▼
   StrategyForwardDriftEvidence (Tier 1 SHA-256 Digest)
          │
          ▼
   MonitoringEvidenceLedger (Phase 10 OperationalCycleEvent Envelope, Tier 2 Chain)
          │
          ▼
   Phase 10 Stage 2 Census (Sovereign Governance Consumption)

2. End-to-End Execution Drag Lineage:
   Phase 7 Execution Fills
          │
          ▼
   ExecutionObservation (Taker-Only, Positive Prices, Arrival Midpoint)
          │
          ▼
   ExecutionAttributionEngine (7 Cost Components, Required Manifest Denominator)
          │
          ▼
   ExecutionCostEvidence (Tier 1 Lineage Digest)
          │
          ▼
   MonitoringEvidenceLedger (Chained to OperationalLedger)

3. Sovereign Authority & Seam Guarantees:
   - Phase 11 cannot mutate historical Phase 8.5 AlphaQualificationDossier.
   - Phase 11 cannot directly exclude strategies or mutate Phase 10 census.
   - Phase 11 cannot overwrite Phase 8 friction config.
   - Phase 7 UNKNOWN orders cannot become execution evidence without authoritative fill resolution.
   - Late broker fills follow declared lineage/reconciliation.
   - Stream reinitialization creates a new epoch without backfilling the outage.
   - Tier 1 evidence digest remains strictly distinct from Tier 2 ledger event chaining.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.attribution import ExecutionAttributionEngine
from acash.monitoring.ingestion import (
    ForwardTelemetryIngestor,
    StreamIntegrityState,
)
from acash.monitoring.ledger import MonitoringEvidenceLedger
from acash.monitoring.metrics import ForwardMetricsCalculator
from acash.monitoring.schema import (
    USD_SCALE,
    ExecutionAttributionPolicy,
    ExecutionObservation,
    ExecutionSide,
    ForwardGovernanceRecommendation,
    ForwardHealthPolicy,
    ForwardHealthState,
    ForwardObservation,
    LiquidityRole,
    StrategyForwardDriftEvidence,
)
from acash.monitoring.state_machine import ForwardHealthStateMachine
from acash.portfolio.planner import RebalancePlannerConfig
from acash.research.alpha_schema import (
    AlphaEconomicDecomposition,
    AlphaLifecycleState,
    AlphaQualificationDossier,
)
from acash.runtime.ledger import GENESIS_PREVIOUS_DIGEST

BASE_TIME = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
DUMMY_DIGEST = "a" * 64


def _create_sample_dossier(alpha_id: str, strat_id: str) -> AlphaQualificationDossier:
    """Helper creating a valid frozen Phase 8.5 AlphaQualificationDossier."""
    econ = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("25.0"),
        realized_spread_slippage_bps=Decimal("5.0"),
        broker_commissions_bps=Decimal("2.0"),
        net_trading_alpha_bps=Decimal("18.0"),
        broker_rebate_income_bps=Decimal("0.0"),
        total_realized_economic_bps=Decimal("18.0"),
    )
    dossier = AlphaQualificationDossier(
        alpha_id=alpha_id,
        strategy_id=strat_id,
        lifecycle_state=AlphaLifecycleState.RESEARCH_QUALIFIED,
        hypothesis_digest=DUMMY_DIGEST,
        trial_ledger_digest=DUMMY_DIGEST,
        validation_report_digest=DUMMY_DIGEST,
        governance_policy_digest=DUMMY_DIGEST,
        economic_decomposition=econ,
        created_timestamp_utc="2026-09-01T00:00:00Z",
    )
    object.__setattr__(dossier, "dossier_digest", dossier.compute_dossier_digest())
    return dossier


def _create_execution_obs(
    obs_id: str,
    fill_px: Decimal = Decimal("120.00"),
    qty: Decimal = Decimal("100"),
    side: ExecutionSide = ExecutionSide.BUY,
    decision_mid: Decimal = Decimal("119.90"),
    arrival_bid: Decimal = Decimal("119.91"),
    arrival_ask: Decimal = Decimal("119.93"),
    fee_usd: Decimal = Decimal("0.35"),
    rebate_usd: Decimal = Decimal("0.00"),
    ts: datetime = BASE_TIME,
    arrival_ts: datetime | None = None,
    fill_ts: datetime | None = None,
) -> ExecutionObservation:
    """Helper creating a valid ExecutionObservation."""
    arr_mid = (arrival_bid + arrival_ask) / Decimal("2.0")
    notional = (qty * fill_px).quantize(USD_SCALE)
    a_ts = arrival_ts or (ts + timedelta(milliseconds=20))
    f_ts = fill_ts or (ts + timedelta(milliseconds=100))

    return ExecutionObservation(
        observation_id=obs_id,
        execution_id=f"EXEC_{obs_id}",
        intent_id=f"INT_{obs_id}",
        strategy_id="STRAT_01",
        venue="ALPACA_PAPER",
        symbol="NVDA",
        side=side,
        liquidity_role=LiquidityRole.TAKER,
        requested_quantity=qty,
        filled_quantity=qty,
        filled_notional_usd=notional,
        decision_mid_price=decision_mid,
        arrival_bid_price=arrival_bid,
        arrival_ask_price=arrival_ask,
        arrival_mid_price=arr_mid,
        executed_fill_price=fill_px,
        commission_fee_usd=fee_usd,
        rebate_usd=rebate_usd,
        decision_timestamp_utc=ts,
        arrival_timestamp_utc=a_ts,
        fill_timestamp_utc=f_ts,
    )


# ============================================================================
# 1. END-TO-END DRIFT MONITORING LINEAGE
# ============================================================================

def test_end_to_end_drift_monitoring_lineage(tmp_path: Path) -> None:
    """Verify complete forward monitoring pipeline from dossier to forensic ledger persistence."""
    # 1. Historical Dossier
    dossier = _create_sample_dossier("ALPHA_001", "STRAT_MOMENTUM_01")
    assert dossier.dossier_digest != ""
    assert len(dossier.dossier_digest) == 64

    # 2. Ingest stream of observations
    ingestor = ForwardTelemetryIngestor()
    observations = []
    t0 = BASE_TIME

    # Ingest 60 consecutive daily observations with non-zero return variance
    for i in range(60):
        obs_time = t0 + timedelta(days=i)
        r = Decimal("0.0020") + Decimal(str(i % 5)) * Decimal("0.0003")
        obs = ForwardObservation(
            observation_id=f"OBS_{i:03d}",
            strategy_id="STRAT_MOMENTUM_01",
            dossier_digest=dossier.dossier_digest,
            as_of_utc=obs_time,
            wall_clock_utc=obs_time + timedelta(milliseconds=15),
            realized_return=r,
            gross_pnl_usd=Decimal("200.00"),
            net_pnl_usd=Decimal("190.00"),
            turnover_ratio=Decimal("0.05"),
            observation_sequence=i,
            is_telemetry_valid=True,
        )
        ingested = ingestor.ingest_observation(obs)
        observations.append(ingested)

    assert len(observations) == 60
    assert ingestor.is_telemetry_valid("STRAT_MOMENTUM_01") is True

    # 3. Compute forward rolling metrics (Slice 2)
    calc = ForwardMetricsCalculator()
    metrics = calc.calculate_window_metrics(observations)
    assert metrics.observation_count == 60
    assert metrics.realized_sharpe_ratio > Decimal("1.0")

    # 4. State Machine Evaluation (Slice 3)
    policy = ForwardHealthPolicy()
    state_machine = ForwardHealthStateMachine(policy)
    transition = state_machine.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics,
        is_telemetry_valid=ingestor.is_telemetry_valid("STRAT_MOMENTUM_01"),
    )
    assert transition.state == ForwardHealthState.HEALTHY
    assert transition.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED

    # 5. Construct Canonical Drift Evidence DTO (Slice 1)
    evidence = StrategyForwardDriftEvidence(
        evidence_id="EVID_DRIFT_DAY_60",
        strategy_id="STRAT_MOMENTUM_01",
        dossier_digest=dossier.dossier_digest,
        as_of_utc=observations[-1].as_of_utc,
        wall_clock_utc=observations[-1].wall_clock_utc,
        health_state=transition.state,
        recommendation=transition.recommendation,
        metrics=metrics,
        policy_digest=policy.policy_digest,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=transition.drift_flags,
    )
    assert len(evidence.evidence_digest) == 64

    # 6. Forensic Ledger Persistence (Slice 5)
    ledger_file = tmp_path / "forensic_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_file)
    event = ledger.record_forward_drift_evidence(evidence)

    assert event.cycle_identity.cycle_id == "EVID_DRIFT_DAY_60"
    assert event.previous_event_digest == GENESIS_PREVIOUS_DIGEST
    assert evidence.evidence_digest in event.active_dossier_digests
    assert ledger.event_count == 1

    # 7. Phase 10 Governance Consumption:
    # Phase 10 reads evidence and recommendation, while Phase 11 DOES NOT claim eligibility authority
    assert evidence.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED
    assert not hasattr(evidence, "is_tournament_eligible")


# ============================================================================
# 2. END-TO-END EXECUTION DRAG ATTRIBUTION LINEAGE
# ============================================================================

def test_end_to_end_execution_reality_lineage(tmp_path: Path) -> None:
    """Verify execution attribution pipeline from execution fills to forensic ledger persistence."""
    t0 = BASE_TIME
    policy = ExecutionAttributionPolicy(min_reliable_sample_count=50)
    engine = ExecutionAttributionEngine()

    # 1. Create 50 valid TAKER buy execution observations
    observations = [
        _create_execution_obs(
            obs_id=f"FILL_{i:03d}",
            fill_px=Decimal("120.00"),
            qty=Decimal("100"),
            ts=t0 + timedelta(minutes=i),
        )
        for i in range(50)
    ]

    # 2. Aggregate into ExecutionCostEvidence
    cost_evidence = engine.aggregate_execution_cost_evidence(
        observations=tuple(observations),
        policy=policy,
        venue="ALPACA_PAPER",
        symbol="NVDA",
        as_of_utc=t0 + timedelta(minutes=60),
        coverage_start_utc=t0,
        coverage_end_utc=t0 + timedelta(minutes=60),
        expected_fill_count=50,
        evidence_id="EVID_COST_01",
    )

    assert cost_evidence.fill_count == 50
    assert cost_evidence.coverage_ratio == Decimal("1.0")
    assert cost_evidence.is_statistically_reliable is True
    assert cost_evidence.mean_gross_drag_bps > Decimal("0.0")
    assert len(cost_evidence.lineage_digest) == 64

    # 3. Persist to forensic ledger
    ledger_file = tmp_path / "forensic_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_file)
    event = ledger.record_execution_cost_evidence(cost_evidence)

    assert event.cycle_identity.cycle_id == "EVID_COST_01"
    assert event.previous_event_digest == GENESIS_PREVIOUS_DIGEST
    assert cost_evidence.lineage_digest in event.execution_manifest_digests
    assert ledger.event_count == 1


# ============================================================================
# 3. AUTHORITY BOUNDARY & DECOUPLING INVARIANTS
# ============================================================================

def test_phase7_unknown_order_cannot_become_execution_evidence() -> None:
    """Phase 7 UNKNOWN / unconfirmed order state cannot become execution evidence without fill resolution."""
    # Attempting to create an ExecutionObservation with fill_price = 0 fails closed
    with pytest.raises(DataContractError, match="filled_notional_usd must be positive|executed_fill_price must be positive"):
        _create_execution_obs("EXEC_UNKNOWN", fill_px=Decimal("0.00"))


def test_late_broker_fill_packet_asynchronous_reconciliation() -> None:
    """Late-arriving broker fill packet binds via intent lineage to original decision midpoint."""
    # Intent generated at t0, arrival at t0 + 5s, fill arrives at t0 + 2 hours (multi-cycle delay)
    t_intent = BASE_TIME
    t_arr = BASE_TIME + timedelta(seconds=5)
    t_late_fill = BASE_TIME + timedelta(hours=2)

    obs = _create_execution_obs(
        obs_id="LATE_FILL_01",
        fill_px=Decimal("120.50"),
        decision_mid=Decimal("119.50"),  # Baseline from original intent cycle!
        arrival_bid=Decimal("119.80"),
        arrival_ask=Decimal("120.00"),
        ts=t_intent,
        arrival_ts=t_arr,
        fill_ts=t_late_fill,
    )

    drag = ExecutionAttributionEngine.decompose_execution_drag(obs)

    # Timing drag correctly captures delay from decision (119.50) to arrival midpoint (119.90)
    assert drag.timing_drag_bps > Decimal("0.0")
    assert drag.gross_execution_drag_bps > Decimal("0.0")


def test_phase11_recommendation_is_not_phase10_eligibility() -> None:
    """Phase 11 recommendation (advisory only) cannot mutate Phase 10 census or claim tournament authority."""
    metrics = ForwardMetricsCalculator().calculate_window_metrics([
        ForwardObservation(
            observation_id=f"OBS_{i:02d}",
            strategy_id="STRAT_FAIL",
            dossier_digest=DUMMY_DIGEST,
            as_of_utc=BASE_TIME + timedelta(days=i),
            wall_clock_utc=BASE_TIME + timedelta(days=i, milliseconds=10),
            realized_return=Decimal("-0.002") + Decimal(str(i % 4)) * Decimal("0.0005"),
            gross_pnl_usd=Decimal("-200.00"),
            net_pnl_usd=Decimal("-210.00"),
            turnover_ratio=Decimal("0.10"),
            observation_sequence=i,
            is_telemetry_valid=True,
        )
        for i in range(35)
    ])

    policy = ForwardHealthPolicy()
    state_machine = ForwardHealthStateMachine(policy)

    # Drive state machine into degradation
    current_state = ForwardHealthState.HEALTHY
    consec_deg = 0
    for _ in range(policy.degradation_persistence_n):
        transition = state_machine.evaluate_step(
            current_state=current_state,
            metrics=metrics,
            consecutive_degraded_periods=consec_deg,
            is_telemetry_valid=True,
        )
        current_state = transition.state
        consec_deg = transition.consecutive_degraded_periods

    assert transition.state == ForwardHealthState.DEGRADED
    assert transition.recommendation == ForwardGovernanceRecommendation.DEGRADED_PROBATION

    # Verify Phase 11 has no methods or fields for tournament admission
    assert not hasattr(transition, "is_tournament_eligible")
    assert not hasattr(transition, "exclude_strategy")
    assert not hasattr(transition, "admitted_strategies")


def test_phase11_cannot_mutate_phase8_friction_config() -> None:
    """Phase 11 cannot directly overwrite Phase 8 RebalancePlannerConfig friction parameters."""
    planner_config = RebalancePlannerConfig(cost_basis_bps=Decimal("0.0005"))

    # Attempt to overwrite cost_basis_bps fails closed (frozen Pydantic model)
    with pytest.raises((TypeError, ValueError)):
        planner_config.cost_basis_bps = Decimal("0.0025")


def test_phase11_cannot_mutate_phase85_dossier() -> None:
    """Phase 11 cannot mutate historical Phase 8.5 AlphaQualificationDossier."""
    dossier = _create_sample_dossier("ALPHA_001", "STRAT_001")
    original_digest = dossier.dossier_digest

    # Attempt to change lifecycle_state or dossier_digest fails closed
    with pytest.raises((TypeError, ValueError)):
        dossier.lifecycle_state = AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK

    with pytest.raises((TypeError, ValueError)):
        dossier.dossier_digest = "f" * 64

    assert dossier.dossier_digest == original_digest


def test_reinitialized_stream_new_epoch_lineage() -> None:
    """Outage causes MONITORING_BLOCKED, reinitialization creates epoch 1 starting at 0, evidence is rebuilt."""
    ingestor = ForwardTelemetryIngestor()
    t0 = BASE_TIME

    # Ingest 5 observations cleanly in epoch 0
    for i in range(5):
        ingestor.ingest_observation(
            ForwardObservation(
                observation_id=f"OBS_E0_{i}",
                strategy_id="STRAT_EPOCH",
                dossier_digest=DUMMY_DIGEST,
                as_of_utc=t0 + timedelta(hours=i),
                wall_clock_utc=t0 + timedelta(hours=i, milliseconds=5),
                realized_return=Decimal("0.001"),
                gross_pnl_usd=Decimal("100.00"),
                net_pnl_usd=Decimal("95.00"),
                turnover_ratio=Decimal("0.05"),
                observation_sequence=i,
                is_telemetry_valid=True,
            )
        )

    # Sequence gap: observation 7 arrives (missing 5 and 6) -> BLOCKED
    with pytest.raises(DataContractError, match="SEQUENCE_GAP_DETECTED"):
        ingestor.ingest_observation(
            ForwardObservation(
                observation_id="OBS_E0_GAP7",
                strategy_id="STRAT_EPOCH",
                dossier_digest=DUMMY_DIGEST,
                as_of_utc=t0 + timedelta(hours=7),
                wall_clock_utc=t0 + timedelta(hours=7, milliseconds=5),
                realized_return=Decimal("0.001"),
                gross_pnl_usd=Decimal("100.00"),
                net_pnl_usd=Decimal("95.00"),
                turnover_ratio=Decimal("0.05"),
                observation_sequence=7,
                is_telemetry_valid=True,
            )
        )

    assert ingestor.is_telemetry_valid("STRAT_EPOCH") is False

    # Explicit reinitialization starts Epoch 1
    status = ingestor.reinitialize_stream("STRAT_EPOCH", recovery_reason="Outage resolved")
    assert status.epoch_index == 1
    assert status.last_sequence == -1
    assert status.integrity_state == StreamIntegrityState.VALID
    assert ingestor.is_telemetry_valid("STRAT_EPOCH") is True

    # Epoch 1 must restart cleanly at sequence 0
    t1 = t0 + timedelta(hours=10)
    obs_new = ingestor.ingest_observation(
        ForwardObservation(
            observation_id="OBS_E1_0",
            strategy_id="STRAT_EPOCH",
            dossier_digest=DUMMY_DIGEST,
            as_of_utc=t1,
            wall_clock_utc=t1 + timedelta(milliseconds=5),
            realized_return=Decimal("0.001"),
            gross_pnl_usd=Decimal("100.00"),
            net_pnl_usd=Decimal("95.00"),
            turnover_ratio=Decimal("0.05"),
            observation_sequence=0,
            is_telemetry_valid=True,
        )
    )
    assert obs_new.observation_sequence == 0


def test_tier1_vs_tier2_digest_lineage_preservation(tmp_path: Path) -> None:
    """Verify Tier 1 evidence digests remain immutable and distinct from Tier 2 ledger event chaining."""
    ledger_path = tmp_path / "dual_tier_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    t0 = BASE_TIME
    metrics = ForwardMetricsCalculator().calculate_window_metrics([
        ForwardObservation(
            observation_id=f"OBS_TIER_{i}",
            strategy_id="STRAT_TIER",
            dossier_digest=DUMMY_DIGEST,
            as_of_utc=t0 + timedelta(days=i),
            wall_clock_utc=t0 + timedelta(days=i, milliseconds=5),
            realized_return=Decimal("0.002") + Decimal(str(i % 5)) * Decimal("0.0004"),
            gross_pnl_usd=Decimal("200.00"),
            net_pnl_usd=Decimal("190.00"),
            turnover_ratio=Decimal("0.05"),
            observation_sequence=i,
            is_telemetry_valid=True,
        )
        for i in range(30)
    ])

    evidence1 = StrategyForwardDriftEvidence(
        evidence_id="EVID_01",
        strategy_id="STRAT_TIER",
        dossier_digest=DUMMY_DIGEST,
        as_of_utc=t0,
        wall_clock_utc=t0 + timedelta(milliseconds=5),
        health_state=ForwardHealthState.HEALTHY,
        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
        metrics=metrics,
        policy_digest="b" * 64,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=(),
    )
    event1 = ledger.record_forward_drift_evidence(evidence1)

    evidence2 = StrategyForwardDriftEvidence(
        evidence_id="EVID_02",
        strategy_id="STRAT_TIER",
        dossier_digest=DUMMY_DIGEST,
        as_of_utc=t0 + timedelta(days=1),
        wall_clock_utc=t0 + timedelta(days=1, milliseconds=5),
        health_state=ForwardHealthState.HEALTHY,
        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
        metrics=metrics,
        policy_digest="b" * 64,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=(),
    )
    event2 = ledger.record_forward_drift_evidence(evidence2)

    # Tier 1 digests are distinct content digests of the evidence DTOs
    assert evidence1.evidence_digest != evidence2.evidence_digest
    assert set(event1.active_dossier_digests) == {DUMMY_DIGEST, evidence1.evidence_digest}
    assert set(event2.active_dossier_digests) == {DUMMY_DIGEST, evidence2.evidence_digest}

    # Tier 2 digests chain the operational ledger events
    assert event1.previous_event_digest == GENESIS_PREVIOUS_DIGEST
    assert event2.previous_event_digest == event1.event_digest
    assert event2.event_digest != event1.event_digest
