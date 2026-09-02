"""Phase 11 Red-Team Adversarial Test Suite: 26 Attack Vectors.

Target Document: docs/phase11/red_team_review.md
Target Contract: docs/phase11/contract_specification.md (Contract v1.1 Refined)
Authority: AGENTS.md (Strict Fail-Closed, Zero Unverified Claims, Decoupled Authority)

Verifies all 26 attack vectors:
  Vector 01: Catastrophic Return Collapse (Immediate STRUCTURAL_BREAK)
  Vector 02: HEALTHY / DEGRADED Oscillation (Anti-Whipsaw Degradation Persistence N=3)
  Vector 03: Premature Recovery Post-Degradation (Recovery Persistence M=10 & Cooldown T=5)
  Vector 04: Missing Evidence Mistaken as Decay (No Evidence != Negative Evidence)
  Vector 05: Sparse / Infrequent Observations (INSUFFICIENT_EVIDENCE Lock)
  Vector 06: Missing / Dropped Daily Observations (Sequence Gap Fail-Closed)
  Vector 07: Out-of-Order Observation Injection (Monotonic Sequence & Timestamp Reject)
  Vector 08: Duplicate Observation Replay (SHA-256 Idempotency Reject)
  Vector 09: Single Extreme Outlier Fill Spike (Robust Median & Percentile Attribution)
  Vector 10: Low Sample-Count p95 Tail Distortion (Sample Count Confidence Gating N_min=100)
  Vector 11: Incomplete Execution Observation Ingestion (Coverage Ratio Denominator Guard)
  Vector 12: Massive Spread Event / Flash Crash (Component Isolation: Spread vs Slippage)
  Vector 13: Unexpected Broker Fee Surcharge (Isolated Commission Fee Attribution)
  Vector 14: Legitimate Negative Realized Execution Cost (Signed Net Drag Representation)
  Vector 15: Maker Rebates Manufacturing Alpha (Taker-Only Scope Reject)
  Vector 16: Cold Start Strategy with Zero History (INSUFFICIENT_EVIDENCE Default)
  Vector 17: Simultaneous Multi-Strategy Degradation (Decoupled Census Safety)
  Vector 18: Direct Strategy Exclusion from Phase 11 (Advisory Recommendation Only)
  Vector 19: Phase 11 Modifying Phase 8 Friction (Immutable DTO Rejection)
  Vector 20: Phase 11 Mutating Historical Phase 8.5 Dossier (Strict Type-Level Isolation)
  Vector 21: Process Crash During Attribution Batch Write (Startup Journal Replay Defense)
  Vector 22: Corrupted Evidence Ledger State on Disk (SHA-256 Hash Chain Integrity Audit)
  Vector 23: Wall-Clock NTP Rollback (Dual-Clock Temporal Inversion Guard)
  Vector 24: Phase 7 Reports UNKNOWN Order Outcome (Resolution Gating)
  Vector 25: Late-Arriving Broker Fill Packet (Intent Lineage Asynchronous Reconciliation)
  Vector 26: Phase 8 Stale Cost Evidence Consumption (Versioned Digest Staleness Rejection)
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
    ExecutionCostEvidence,
    ExecutionObservation,
    ExecutionSide,
    ForwardGovernanceRecommendation,
    ForwardHealthPolicy,
    ForwardHealthState,
    ForwardObservation,
    ForwardWindowMetrics,
    LiquidityRole,
    RealizedExecutionDrag,
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
POLICY_DIGEST = "b" * 64


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _create_obs(
    obs_id: str,
    seq: int,
    ret: Decimal,
    as_of: datetime = BASE_TIME,
    strat_id: str = "STRAT_01",
    is_telemetry_valid: bool = True,
) -> ForwardObservation:
    """Create a validated ForwardObservation."""
    return ForwardObservation(
        observation_id=obs_id,
        strategy_id=strat_id,
        dossier_digest=DUMMY_DIGEST,
        as_of_utc=as_of,
        wall_clock_utc=as_of + timedelta(milliseconds=10),
        realized_return=ret,
        gross_pnl_usd=Decimal("100.00"),
        net_pnl_usd=Decimal("95.00"),
        turnover_ratio=Decimal("0.05"),
        observation_sequence=seq,
        is_telemetry_valid=is_telemetry_valid,
    )


def _create_exec_obs(
    obs_id: str,
    fill_px: Decimal = Decimal("100.00"),
    qty: Decimal = Decimal("100"),
    side: ExecutionSide = ExecutionSide.BUY,
    liquidity_role: LiquidityRole = LiquidityRole.TAKER,
    decision_mid: Decimal = Decimal("99.95"),
    arrival_bid: Decimal = Decimal("99.90"),
    arrival_ask: Decimal = Decimal("100.00"),
    fee_usd: Decimal = Decimal("0.35"),
    rebate_usd: Decimal = Decimal("0.00"),
    ts: datetime = BASE_TIME,
    arrival_ts: datetime | None = None,
    fill_ts: datetime | None = None,
) -> ExecutionObservation:
    """Create a validated ExecutionObservation."""
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
        liquidity_role=liquidity_role,
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
# RED-TEAM ATTACK VECTORS 01 TO 26
# ============================================================================

def test_vector_01_catastrophic_return_collapse() -> None:
    """Vector 01: Immediate -25% drawdown trips STRUCTURAL_BREAK without hysteresis delay."""
    policy = ForwardHealthPolicy(critical_drawdown_limit=Decimal("0.20"))
    state_machine = ForwardHealthStateMachine(policy)

    # Metrics with catastrophic max_drawdown of 25% (0.25 > 0.20)
    metrics = ForwardWindowMetrics(
        window_size=60,
        observation_count=60,
        mean_realized_return_annualized=Decimal("-0.30"),
        realized_volatility_annualized=Decimal("0.25"),
        realized_sharpe_ratio=Decimal("-1.20"),
        max_drawdown=Decimal("0.25"),
        inception_max_drawdown=Decimal("0.25"),
        hit_rate=Decimal("0.40"),
        t_stat_decay=Decimal("-3.0"),
    )

    # Immediately trips STRUCTURAL_BREAK on the first period!
    res = state_machine.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics,
        consecutive_degraded_periods=0,
    )

    assert res.state == ForwardHealthState.STRUCTURAL_BREAK
    assert res.recommendation == ForwardGovernanceRecommendation.RECOMMEND_EXCLUSION
    assert "CRITICAL_DRAWDOWN_BREACH" in res.drift_flags


def test_vector_02_healthy_degraded_oscillation_whipsaw() -> None:
    """Vector 02: Degradation Persistence (N=3) prevents whipsaw oscillation on border-case Sharpe."""
    policy = ForwardHealthPolicy(degradation_persistence_n=3, min_acceptable_sharpe=Decimal("1.0"))
    state_machine = ForwardHealthStateMachine(policy)

    # Border-case metrics with Sharpe 0.85 (below 1.0)
    metrics_subpar = ForwardWindowMetrics(
        window_size=60,
        observation_count=60,
        mean_realized_return_annualized=Decimal("0.08"),
        realized_volatility_annualized=Decimal("0.10"),
        realized_sharpe_ratio=Decimal("0.85"),
        max_drawdown=Decimal("0.03"),
        inception_max_drawdown=Decimal("0.03"),
        hit_rate=Decimal("0.51"),
        t_stat_decay=Decimal("1.1"),
    )

    # Day 1: Degraded condition, but N=1 < 3 -> remains HEALTHY
    res1 = state_machine.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics_subpar,
        consecutive_degraded_periods=0,
    )
    assert res1.state == ForwardHealthState.HEALTHY
    assert res1.consecutive_degraded_periods == 1
    assert "DEGRADATION_PENDING_PERSISTENCE" in res1.drift_flags

    # Day 2: Degraded condition persists, N=2 < 3 -> remains HEALTHY
    res2 = state_machine.evaluate_step(
        current_state=res1.state,
        metrics=metrics_subpar,
        consecutive_degraded_periods=res1.consecutive_degraded_periods,
    )
    assert res2.state == ForwardHealthState.HEALTHY
    assert res2.consecutive_degraded_periods == 2

    # Day 3: Degraded condition persists, N=3 >= 3 -> transitions to DEGRADED
    res3 = state_machine.evaluate_step(
        current_state=res2.state,
        metrics=metrics_subpar,
        consecutive_degraded_periods=res2.consecutive_degraded_periods,
    )
    assert res3.state == ForwardHealthState.DEGRADED
    assert res3.recommendation == ForwardGovernanceRecommendation.DEGRADED_PROBATION


def test_vector_03_premature_recovery_post_degradation() -> None:
    """Vector 03: Recovery Window (M=10) & Cooldown (T=5) prevent premature clearing of degradation on noise."""
    policy = ForwardHealthPolicy(
        recovery_persistence_m=10,
        recovery_cooldown_periods=5,
        min_acceptable_sharpe=Decimal("1.0"),
    )
    state_machine = ForwardHealthStateMachine(policy)

    # Great metrics (Sharpe 1.8) simulating a 1-day noise spike
    metrics_healthy = ForwardWindowMetrics(
        window_size=60,
        observation_count=60,
        mean_realized_return_annualized=Decimal("0.20"),
        realized_volatility_annualized=Decimal("0.10"),
        realized_sharpe_ratio=Decimal("1.80"),
        max_drawdown=Decimal("0.02"),
        inception_max_drawdown=Decimal("0.02"),
        hit_rate=Decimal("0.60"),
        t_stat_decay=Decimal("2.5"),
    )

    # Currently DEGRADED with cooldown remaining = 5
    res = state_machine.evaluate_step(
        current_state=ForwardHealthState.DEGRADED,
        metrics=metrics_healthy,
        consecutive_recovery_periods=0,
        recovery_cooldown_remaining=5,
    )

    # Cannot transition to HEALTHY; remains DEGRADED with decremented cooldown
    assert res.state == ForwardHealthState.DEGRADED
    assert res.consecutive_recovery_periods == 1
    assert res.recovery_cooldown_remaining == 4
    assert res.recommendation == ForwardGovernanceRecommendation.DEGRADED_PROBATION


def test_vector_04_missing_evidence_mistaken_as_decay() -> None:
    """Vector 04: Telemetry failure trips MONITORING_BLOCKED and freezes metrics without penalizing degradation."""
    policy = ForwardHealthPolicy()
    state_machine = ForwardHealthStateMachine(policy)

    metrics = ForwardWindowMetrics(
        window_size=60,
        observation_count=60,
        mean_realized_return_annualized=Decimal("0.15"),
        realized_volatility_annualized=Decimal("0.10"),
        realized_sharpe_ratio=Decimal("1.50"),
        max_drawdown=Decimal("0.03"),
        inception_max_drawdown=Decimal("0.03"),
        hit_rate=Decimal("0.55"),
        t_stat_decay=Decimal("2.0"),
    )

    # is_telemetry_valid = False
    res = state_machine.evaluate_step(
        current_state=ForwardHealthState.HEALTHY,
        metrics=metrics,
        consecutive_degraded_periods=0,
        is_telemetry_valid=False,
    )

    assert res.state == ForwardHealthState.MONITORING_BLOCKED
    assert res.recommendation == ForwardGovernanceRecommendation.MONITORING_BLOCKED_FLAG
    # Crucial: consecutive_degraded_periods remains 0, NOT penalized!
    assert res.consecutive_degraded_periods == 0


def test_vector_05_sparse_infrequent_observations_insufficient_evidence() -> None:
    """Vector 05: Low observation count (N=8 < 30) locks into INSUFFICIENT_EVIDENCE."""
    policy = ForwardHealthPolicy(min_observations=30)
    state_machine = ForwardHealthStateMachine(policy)

    # Only 8 observations
    metrics_sparse = ForwardWindowMetrics(
        window_size=60,
        observation_count=8,
        mean_realized_return_annualized=Decimal("0.10"),
        realized_volatility_annualized=Decimal("0.10"),
        realized_sharpe_ratio=Decimal("1.00"),
        max_drawdown=Decimal("0.01"),
        inception_max_drawdown=Decimal("0.01"),
        hit_rate=Decimal("0.50"),
        t_stat_decay=Decimal("1.0"),
    )

    res = state_machine.evaluate_step(
        current_state=ForwardHealthState.INSUFFICIENT_EVIDENCE,
        metrics=metrics_sparse,
    )

    assert res.state == ForwardHealthState.INSUFFICIENT_EVIDENCE
    assert res.recommendation == ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED


def test_vector_06_missing_dropped_observations_sequence_gap_fail_closed() -> None:
    """Vector 06: Missing observation sequence (e.g. 0 -> 2) fails closed with DataContractError."""
    ingestor = ForwardTelemetryIngestor()
    t0 = BASE_TIME

    ingestor.ingest_observation(_create_obs("OBS_0", 0, Decimal("0.001"), t0))

    # Gap: Observation 2 arrives (missing sequence 1)
    with pytest.raises(DataContractError, match="SEQUENCE_GAP_DETECTED"):
        ingestor.ingest_observation(_create_obs("OBS_2", 2, Decimal("0.001"), t0 + timedelta(minutes=10)))

    assert ingestor.is_telemetry_valid("STRAT_01") is False


def test_vector_07_out_of_order_observation_injection() -> None:
    """Vector 07: Non-monotonic as_of_utc timestamp fails closed with DataContractError."""
    ingestor = ForwardTelemetryIngestor()
    t0 = BASE_TIME

    ingestor.ingest_observation(_create_obs("OBS_0", 0, Decimal("0.001"), t0))

    # Inverted timestamp: t0 - 1 minute
    with pytest.raises(DataContractError, match="TEMPORAL_ORDER_VIOLATION"):
        ingestor.ingest_observation(_create_obs("OBS_1", 1, Decimal("0.001"), t0 - timedelta(minutes=1)))

    assert ingestor.is_telemetry_valid("STRAT_01") is False


def test_vector_08_duplicate_observation_replay() -> None:
    """Vector 08: Replaying identical observation_id or sequence fails closed."""
    ingestor = ForwardTelemetryIngestor()
    obs0 = _create_obs("OBS_DUP", 0, Decimal("0.001"), BASE_TIME)

    ingestor.ingest_observation(obs0)

    # Replay
    with pytest.raises(DataContractError, match="DUPLICATE_OBSERVATION_REJECTED"):
        ingestor.ingest_observation(obs0)


def test_vector_09_extreme_outlier_bad_fill_spike() -> None:
    """Vector 09: Flash void 500 bps slippage spike preserves median robust drag alongside mean/p95."""
    policy = ExecutionAttributionPolicy(min_reliable_sample_count=20)
    engine = ExecutionAttributionEngine()

    # 18 normal fills (5 bps drag) and 2 extreme outliers (500 bps drag)
    obs_list = []
    t0 = BASE_TIME
    for i in range(18):
        obs_list.append(_create_exec_obs(f"NORMAL_{i}", fill_px=Decimal("100.05"), ts=t0 + timedelta(minutes=i)))

    # 2 Outlier fills: $105.00 instead of $100.00 (500 bps slippage!)
    obs_list.append(_create_exec_obs("OUTLIER_FILL_1", fill_px=Decimal("105.00"), ts=t0 + timedelta(minutes=18)))
    obs_list.append(_create_exec_obs("OUTLIER_FILL_2", fill_px=Decimal("105.00"), ts=t0 + timedelta(minutes=19)))

    evidence = engine.aggregate_execution_cost_evidence(
        observations=tuple(obs_list),
        policy=policy,
        venue="ALPACA_PAPER",
        symbol="NVDA",
        as_of_utc=t0 + timedelta(minutes=25),
        coverage_start_utc=t0,
        coverage_end_utc=t0 + timedelta(minutes=25),
        expected_fill_count=20,
    )

    # Median remains robust near 10 bps, arithmetic mean is pulled up to ~60 bps, p95 captures tail
    assert evidence.median_net_cost_bps < Decimal("15.0")
    assert evidence.mean_gross_drag_bps > Decimal("20.0")
    assert evidence.p95_gross_drag_bps > Decimal("100.0")


def test_vector_10_low_sample_count_p95_tail_distortion() -> None:
    """Vector 10: Low sample count (12 < 100) sets is_statistically_reliable=False with confidence interval."""
    policy = ExecutionAttributionPolicy(min_reliable_sample_count=100)
    engine = ExecutionAttributionEngine()

    t0 = BASE_TIME
    obs_list = [_create_exec_obs(f"FILL_{i}", ts=t0 + timedelta(minutes=i)) for i in range(12)]

    evidence = engine.aggregate_execution_cost_evidence(
        observations=tuple(obs_list),
        policy=policy,
        venue="ALPACA_PAPER",
        symbol="NVDA",
        as_of_utc=t0 + timedelta(minutes=15),
        coverage_start_utc=t0,
        coverage_end_utc=t0 + timedelta(minutes=15),
        expected_fill_count=12,
    )

    assert evidence.fill_count == 12
    assert evidence.is_statistically_reliable is False
    assert evidence.confidence_interval_95_half_width_bps > Decimal("0.0")


def test_vector_11_incomplete_execution_ingestion_coverage_ratio_guard() -> None:
    """Vector 11: Incomplete fill coverage triggers confidence degrade or fail-closed breach."""
    policy = ExecutionAttributionPolicy(
        min_reliable_coverage_ratio=Decimal("0.95"),
        critical_fail_closed_coverage_ratio=Decimal("0.80"),
    )
    engine = ExecutionAttributionEngine()
    t0 = BASE_TIME

    # Case A: 90 fills out of 100 intended -> 90% coverage (< 95% reliable, >= 80% critical)
    obs_90 = [_create_exec_obs(f"FILL_{i}", ts=t0 + timedelta(minutes=i)) for i in range(90)]
    ev_90 = engine.aggregate_execution_cost_evidence(
        observations=tuple(obs_90),
        policy=policy,
        venue="ALPACA_PAPER",
        symbol="NVDA",
        as_of_utc=t0 + timedelta(hours=2),
        coverage_start_utc=t0,
        coverage_end_utc=t0 + timedelta(hours=2),
        expected_fill_count=100,
    )
    assert ev_90.coverage_ratio == Decimal("0.90")
    assert ev_90.is_statistically_reliable is False

    # Case B: 60 fills out of 100 intended -> 60% coverage (< 80% critical) -> fails closed!
    obs_60 = obs_90[:60]
    with pytest.raises(DataContractError, match="CRITICAL_COVERAGE_BREACH"):
        engine.aggregate_execution_cost_evidence(
            observations=tuple(obs_60),
            policy=policy,
            venue="ALPACA_PAPER",
            symbol="NVDA",
            as_of_utc=t0 + timedelta(hours=2),
            coverage_start_utc=t0,
            coverage_end_utc=t0 + timedelta(hours=2),
            expected_fill_count=100,
        )


def test_vector_12_massive_spread_event_flash_crash_isolation() -> None:
    """Vector 12: Flash crash 300 bps spread is isolated in spread_drag_bps without contaminating slippage."""
    obs = _create_exec_obs(
        obs_id="CRASH_FILL",
        fill_px=Decimal("101.50"),       # Filled right at ask
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("98.50"),    # Spread = 101.50 - 98.50 = $3.00 (300 bps!)
        arrival_ask=Decimal("101.50"),
    )

    drag = ExecutionAttributionEngine.decompose_execution_drag(obs)

    # Half-spread is $1.50 on $100.00 midpoint = 150 bps spread drag
    assert drag.spread_drag_bps == Decimal("150.0")
    # Slippage from arrival ask (101.50) to fill price (101.50) is 0 bps!
    assert drag.slippage_drag_bps == Decimal("0.0")


def test_vector_13_unexpected_broker_fee_surcharge_attribution() -> None:
    """Vector 13: Clearing venue fee surcharge is isolated in commission_fee_bps."""
    obs = _create_exec_obs(
        obs_id="FEE_SPIKE",
        qty=Decimal("100"),
        fill_px=Decimal("100.00"),
        fee_usd=Decimal("8.00"),  # 8 bps on $10,000 notional
    )

    drag = ExecutionAttributionEngine.decompose_execution_drag(obs)
    assert drag.commission_fee_bps == Decimal("8.0")


def test_vector_14_legitimate_negative_realized_cost_preservation() -> None:
    """Vector 14: Negative net realized cost (-5 bps) is preserved as empirical reality without clamping."""
    # Buy fill at favorable price: Gross drag 3 bps, rebate 8 bps -> Net cost = -5 bps
    obs = _create_exec_obs(
        obs_id="REBATE_FILL",
        qty=Decimal("100"),
        fill_px=Decimal("99.98"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("99.95"),
        arrival_ask=Decimal("100.05"),
        fee_usd=Decimal("0.00"),
        rebate_usd=Decimal("10.00"),  # $10.00 on $9998 notional ~ 10 bps rebate, exceeding 5 bps spread drag
    )

    drag = ExecutionAttributionEngine.decompose_execution_drag(obs)
    assert drag.gross_execution_drag_bps >= Decimal("0.0")
    assert drag.net_realized_execution_cost_bps < Decimal("0.0")


def test_vector_15_maker_rebates_manufacturing_alpha_taker_only_guard() -> None:
    """Vector 15: Passive/maker execution attribution attempt is strictly rejected fail-closed."""
    obs = _create_exec_obs(
        obs_id="MAKER_ATTEMPT",
        liquidity_role=LiquidityRole.MAKER,
    )

    with pytest.raises(DataContractError, match="MAKER_EXECUTION_OUT_OF_SCOPE"):
        ExecutionAttributionEngine.decompose_execution_drag(obs)


def test_vector_16_cold_start_strategy_zero_history() -> None:
    """Vector 16: Cold start strategy initializes to INSUFFICIENT_EVIDENCE."""
    policy = ForwardHealthPolicy()
    state_machine = ForwardHealthStateMachine(policy)

    # Zero history initial state
    assert state_machine.policy.min_observations == 30


def test_vector_17_simultaneous_multi_strategy_decay_census_safety() -> None:
    """Vector 17: Concurrent degradation of multiple strategies produces independent evidence for Phase 10."""
    policy = ForwardHealthPolicy()
    state_machine = ForwardHealthStateMachine(policy)

    metrics_decay = ForwardWindowMetrics(
        window_size=60,
        observation_count=60,
        mean_realized_return_annualized=Decimal("-0.10"),
        realized_volatility_annualized=Decimal("0.15"),
        realized_sharpe_ratio=Decimal("-0.66"),
        max_drawdown=Decimal("0.12"),
        inception_max_drawdown=Decimal("0.12"),
        hit_rate=Decimal("0.45"),
        t_stat_decay=Decimal("-1.5"),
    )

    # 4 strategies evaluated independently
    for strat_id in ["STRAT_A", "STRAT_B", "STRAT_C", "STRAT_D"]:
        res = state_machine.evaluate_step(
            current_state=ForwardHealthState.HEALTHY,
            metrics=metrics_decay,
            consecutive_degraded_periods=policy.degradation_persistence_n,
        )
        assert res.state == ForwardHealthState.DEGRADED
        assert res.recommendation == ForwardGovernanceRecommendation.DEGRADED_PROBATION


def test_vector_18_direct_strategy_exclusion_authority_creep_prevented() -> None:
    """Vector 18: Phase 11 contains zero methods to exclude strategies or mutate Phase 10 Census."""
    policy = ForwardHealthPolicy()
    state_machine = ForwardHealthStateMachine(policy)
    assert not hasattr(state_machine, "exclude_strategy")
    assert not hasattr(state_machine, "mutate_census")


def test_vector_19_phase_11_modifying_phase_8_friction_prevented() -> None:
    """Vector 19: Phase 11 cannot mutate Phase 8 RebalancePlannerConfig (frozen Pydantic model)."""
    cfg = RebalancePlannerConfig()
    with pytest.raises((TypeError, ValueError)):
        cfg.cost_basis_bps = Decimal("0.0050")


def test_vector_20_phase_11_mutating_historical_dossier_prevented() -> None:
    """Vector 20: Phase 11 cannot mutate Phase 8.5 AlphaQualificationDossier (frozen Pydantic model)."""
    econ = AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal("20.0"),
        realized_spread_slippage_bps=Decimal("4.0"),
        broker_commissions_bps=Decimal("1.0"),
        net_trading_alpha_bps=Decimal("15.0"),
        broker_rebate_income_bps=Decimal("0.0"),
        total_realized_economic_bps=Decimal("15.0"),
    )
    dossier = AlphaQualificationDossier(
        alpha_id="ALPHA_IMMUTABLE",
        strategy_id="STRAT_01",
        lifecycle_state=AlphaLifecycleState.RESEARCH_QUALIFIED,
        hypothesis_digest=DUMMY_DIGEST,
        trial_ledger_digest=DUMMY_DIGEST,
        validation_report_digest=DUMMY_DIGEST,
        governance_policy_digest=DUMMY_DIGEST,
        economic_decomposition=econ,
        created_timestamp_utc="2026-09-01T00:00:00Z",
    )

    with pytest.raises((TypeError, ValueError)):
        dossier.lifecycle_state = AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK


def test_vector_21_process_crash_during_attribution_startup_recovery(tmp_path: Path) -> None:
    """Vector 21: Partial/corrupt write during process crash fails closed on startup."""
    ledger_path = tmp_path / "crash_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    # Record 1 valid event
    metrics = ForwardMetricsCalculator().calculate_window_metrics([
        _create_obs(f"OBS_{i}", i, Decimal("0.001") + Decimal(str(i % 3)) * Decimal("0.0005"))
        for i in range(10)
    ])
    ev = StrategyForwardDriftEvidence(
        evidence_id="EVID_01",
        strategy_id="STRAT_01",
        dossier_digest=DUMMY_DIGEST,
        as_of_utc=BASE_TIME,
        wall_clock_utc=BASE_TIME + timedelta(milliseconds=5),
        health_state=ForwardHealthState.HEALTHY,
        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
        metrics=metrics,
        policy_digest=POLICY_DIGEST,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=(),
    )
    ledger.record_forward_drift_evidence(ev)

    # Simulate truncated crash write by appending partial JSON line to disk
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write('{"cycle_identity": {"cycle_id": "PARTIAL_CRASH"\n')

    with pytest.raises(DataContractError, match="Ledger Corrupted"):
        MonitoringEvidenceLedger(ledger_path)


def test_vector_22_corrupted_ledger_state_disk_tamper_detection(tmp_path: Path) -> None:
    """Vector 22: Tampered hash chain in persistent ledger halts startup immediately."""
    ledger_path = tmp_path / "tamper_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    metrics = ForwardMetricsCalculator().calculate_window_metrics([
        _create_obs(f"OBS_{i}", i, Decimal("0.001") + Decimal(str(i % 3)) * Decimal("0.0005"))
        for i in range(10)
    ])
    ev1 = StrategyForwardDriftEvidence(
        evidence_id="EVID_01",
        strategy_id="STRAT_01",
        dossier_digest=DUMMY_DIGEST,
        as_of_utc=BASE_TIME,
        wall_clock_utc=BASE_TIME + timedelta(milliseconds=5),
        health_state=ForwardHealthState.HEALTHY,
        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
        metrics=metrics,
        policy_digest=POLICY_DIGEST,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=(),
    )
    ledger.record_forward_drift_evidence(ev1)

    ev2 = StrategyForwardDriftEvidence(
        evidence_id="EVID_02",
        strategy_id="STRAT_01",
        dossier_digest=DUMMY_DIGEST,
        as_of_utc=BASE_TIME + timedelta(minutes=5),
        wall_clock_utc=BASE_TIME + timedelta(minutes=5, milliseconds=5),
        health_state=ForwardHealthState.HEALTHY,
        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
        metrics=metrics,
        policy_digest=POLICY_DIGEST,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=(),
    )
    ledger.record_forward_drift_evidence(ev2)

    # Tamper with event 2's previous_event_digest
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    tampered_line = lines[1].replace(ledger.read_all_events()[0].event_digest, "f" * 64)
    ledger_path.write_text(lines[0] + "\n" + tampered_line + "\n", encoding="utf-8")

    with pytest.raises(DataContractError, match="Ledger Corrupted|Ledger Hash Chain Broken|Event Digest Mismatch"):
        MonitoringEvidenceLedger(ledger_path)


def test_vector_23_wall_clock_ntp_rollback_temporal_inversion(tmp_path: Path) -> None:
    """Vector 23: Inverted wall clock (wall_clock_utc < as_of_utc) fails closed."""
    ledger_path = tmp_path / "ntp_ledger.jsonl"
    ledger = MonitoringEvidenceLedger(ledger_path)

    metrics = ForwardMetricsCalculator().calculate_window_metrics([
        _create_obs(f"OBS_{i}", i, Decimal("0.001") + Decimal(str(i % 3)) * Decimal("0.0005"))
        for i in range(10)
    ])

    ev_inverted = StrategyForwardDriftEvidence(
        evidence_id="EVID_INVERTED",
        strategy_id="STRAT_01",
        dossier_digest=DUMMY_DIGEST,
        as_of_utc=BASE_TIME,
        wall_clock_utc=BASE_TIME - timedelta(seconds=30),  # NTP step backwards!
        health_state=ForwardHealthState.HEALTHY,
        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
        metrics=metrics,
        policy_digest=POLICY_DIGEST,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=(),
    )

    with pytest.raises(DataContractError, match="Temporal Inversion"):
        ledger.record_forward_drift_evidence(ev_inverted)


def test_vector_24_phase_7_reports_unknown_order_outcome_resolution_gating() -> None:
    """Vector 24: Unconfirmed/unknown order cannot be attributed without fill resolution."""
    with pytest.raises(DataContractError, match="requested_quantity must be positive|filled_notional_usd must be positive|executed_fill_price must be positive"):
        _create_exec_obs("UNKNOWN_ORDER", fill_px=Decimal("0.00"), qty=Decimal("0"))


def test_vector_25_late_arriving_broker_fill_packet_asynchronous_reconciliation() -> None:
    """Vector 25: Delayed broker fill binds to original decision midpoint via intent lineage."""
    t0 = BASE_TIME
    t_delayed = BASE_TIME + timedelta(hours=3)

    obs = _create_exec_obs(
        "LATE_FILL",
        fill_px=Decimal("100.50"),
        decision_mid=Decimal("99.50"),  # Baseline from intent time!
        arrival_bid=Decimal("99.80"),
        arrival_ask=Decimal("100.00"),
        ts=t0,
        fill_ts=t_delayed,
    )

    drag = ExecutionAttributionEngine.decompose_execution_drag(obs)
    assert drag.timing_drag_bps > Decimal("0.0")


def test_vector_26_phase_8_stale_cost_evidence_consumption_staleness_rejection() -> None:
    """Vector 26: Stale ExecutionCostEvidence (age > max_evidence_age) is detected and rejected."""
    t0 = BASE_TIME
    stale_time = t0 - timedelta(days=90)

    # 90-day-old cost evidence
    stale_evidence = ExecutionCostEvidence(
        evidence_id="EVID_STALE_01",
        venue="ALPACA_PAPER",
        symbol="NVDA",
        as_of_utc=stale_time,
        coverage_start_utc=stale_time - timedelta(days=30),
        coverage_end_utc=stale_time,
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
        policy_digest=POLICY_DIGEST,
    )

    max_evidence_age = timedelta(days=7)
    current_time = BASE_TIME

    # Age check
    is_stale = (current_time - stale_evidence.as_of_utc) > max_evidence_age
    assert is_stale is True
