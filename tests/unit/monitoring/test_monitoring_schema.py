"""Unit tests for Phase 11 monitoring domain schemas and contract invariants.

Verifies:
1. ExecutionSide enum directional semantics and string safety.
2. ExecutionObservation validation, price milestones, Option A canonical midpoint,
   chronological timestamp ordering, notional value conservation, and non-self-referential digest.
3. ForwardObservation validation, sequence constraints, turnover limits, and Tier 1 digest.
4. ForwardHealthPolicy asymmetric hysteresis invariant (M > N) and parameter bounds.
5. StrategyForwardDriftEvidence authority creep prevention (strict rejection of is_tournament_eligible).
6. ExecutionAttributionPolicy and ExecutionCostEvidence validation and statistical metadata.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, cast
import pytest

from acash.core.domain.exceptions import DataContractError
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
    RealizedExecutionDrag,
    StrategyForwardDriftEvidence,
)

VALID_DIGEST_A = "a" * 64
VALID_DIGEST_B = "b" * 64
VALID_DIGEST_C = "c" * 64


# ============================================================================
# 1. EXECUTION SIDE & DIRECTIONAL SEMANTICS
# ============================================================================

def test_execution_side_directional_semantics() -> None:
    """Verify ExecutionSide directional multipliers."""
    assert ExecutionSide.BUY.side_sign == Decimal("1.0")
    assert ExecutionSide.SELL.side_sign == Decimal("-1.0")
    assert ExecutionSide("BUY") == ExecutionSide.BUY
    assert ExecutionSide("SELL") == ExecutionSide.SELL

    with pytest.raises(ValueError):
        ExecutionSide("HOLD")


# ============================================================================
# 2. EXECUTION OBSERVATION INVARIANTS
# ============================================================================

@pytest.fixture
def valid_execution_obs_payload() -> dict[str, Any]:
    t0 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(milliseconds=25)
    t2 = t1 + timedelta(milliseconds=150)
    qty = Decimal("100.0")
    fill_px = Decimal("150.25")
    notional = (qty * fill_px).quantize(USD_SCALE)

    return {
        "observation_id": "EXOBS_001",
        "execution_id": "EXEC_ALPACA_101",
        "intent_id": "INTENT_STRAT_01_001",
        "strategy_id": "STRAT_MOMENTUM_01",
        "venue": "ALPACA_PAPER",
        "symbol": "AAPL",
        "side": ExecutionSide.BUY,
        "requested_quantity": Decimal("100.0"),
        "filled_quantity": qty,
        "filled_notional_usd": notional,
        "decision_mid_price": Decimal("150.10"),
        "arrival_bid_price": Decimal("150.15"),
        "arrival_ask_price": Decimal("150.25"),
        "arrival_mid_price": Decimal("150.20"),  # (150.15 + 150.25) / 2
        "executed_fill_price": fill_px,
        "commission_fee_usd": Decimal("0.35"),
        "rebate_usd": Decimal("0.00"),
        "decision_timestamp_utc": t0,
        "arrival_timestamp_utc": t1,
        "fill_timestamp_utc": t2,
        "network_latency_ms": 25.0,
        "is_partial_fill": False,
    }


def test_execution_observation_happy_path(valid_execution_obs_payload: dict[str, Any]) -> None:
    """Verify clean instantiation and automatic Tier 1 non-self-referential execution digest."""
    obs = ExecutionObservation(**valid_execution_obs_payload)
    assert obs.observation_id == "EXOBS_001"
    assert obs.side == ExecutionSide.BUY
    assert len(obs.execution_digest) == 64
    assert obs.filled_notional_usd == Decimal("15025.00")


def test_execution_observation_string_side_coercion(valid_execution_obs_payload: dict[str, Any]) -> None:
    """Verify string 'BUY'/'SELL' is safely coerced to ExecutionSide enum."""
    valid_execution_obs_payload["side"] = "BUY"
    obs = ExecutionObservation(**valid_execution_obs_payload)
    assert obs.side == ExecutionSide.BUY

    valid_execution_obs_payload["side"] = "INVALID"
    with pytest.raises(DataContractError, match="Invalid ExecutionSide"):
        ExecutionObservation(**valid_execution_obs_payload)


def test_execution_observation_option_a_canonical_midpoint_violation(valid_execution_obs_payload: dict[str, Any]) -> None:
    """Fail closed when arrival_mid_price does not equal (bid + ask) / 2."""
    valid_execution_obs_payload["arrival_mid_price"] = Decimal("150.22")  # Expected 150.20
    with pytest.raises(DataContractError, match="Option A Canonical Midpoint violated"):
        ExecutionObservation(**valid_execution_obs_payload)


def test_execution_observation_inverted_spread_violation(valid_execution_obs_payload: dict[str, Any]) -> None:
    """Fail closed when arrival_bid > arrival_ask."""
    valid_execution_obs_payload["arrival_bid_price"] = Decimal("150.30")
    valid_execution_obs_payload["arrival_ask_price"] = Decimal("150.20")
    valid_execution_obs_payload["arrival_mid_price"] = Decimal("150.25")
    with pytest.raises(DataContractError, match="Inverted spread"):
        ExecutionObservation(**valid_execution_obs_payload)


def test_execution_observation_notional_conservation_violation(valid_execution_obs_payload: dict[str, Any]) -> None:
    """Fail closed when filled_notional_usd does not match quantized(qty * fill_px)."""
    valid_execution_obs_payload["filled_notional_usd"] = Decimal("15026.00")  # Should be 15025.00
    with pytest.raises(DataContractError, match="Notional conservation violated"):
        ExecutionObservation(**valid_execution_obs_payload)


def test_execution_observation_temporal_ordering_violation(valid_execution_obs_payload: dict[str, Any]) -> None:
    """Fail closed when timestamps violate decision <= arrival <= fill."""
    t0 = valid_execution_obs_payload["decision_timestamp_utc"]
    # Invert arrival and decision
    valid_execution_obs_payload["arrival_timestamp_utc"] = t0 - timedelta(seconds=1)
    with pytest.raises(DataContractError, match="Temporal ordering violation"):
        ExecutionObservation(**valid_execution_obs_payload)


def test_execution_observation_digest_tamper_detection(valid_execution_obs_payload: dict[str, Any]) -> None:
    """Fail closed when supplied execution_digest does not match recomputed Tier 1 digest."""
    valid_execution_obs_payload["execution_digest"] = "f" * 64
    with pytest.raises(DataContractError, match="Execution digest tampering detected"):
        ExecutionObservation(**valid_execution_obs_payload)


# ============================================================================
# 3. FORWARD OBSERVATION INVARIANTS
# ============================================================================

@pytest.fixture
def valid_forward_obs_payload() -> dict[str, Any]:
    t0 = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    return {
        "observation_id": "FOBS_001",
        "strategy_id": "STRAT_MOMENTUM_01",
        "dossier_digest": VALID_DIGEST_A,
        "as_of_utc": t0,
        "wall_clock_utc": t0 + timedelta(milliseconds=5),
        "realized_return": Decimal("0.0012"),
        "expected_return": Decimal("0.0015"),
        "benchmark_return": Decimal("0.0002"),
        "gross_pnl_usd": Decimal("120.00"),
        "net_pnl_usd": Decimal("112.50"),
        "turnover_ratio": Decimal("0.15"),
        "observation_sequence": 1,
        "is_telemetry_valid": True,
    }


def test_forward_observation_happy_path(valid_forward_obs_payload: dict[str, Any]) -> None:
    """Verify clean instantiation and auto Tier 1 non-self-referential digest generation."""
    obs = ForwardObservation(**valid_forward_obs_payload)
    assert obs.observation_id == "FOBS_001"
    assert len(obs.observation_digest) == 64
    assert obs.observation_sequence == 1


def test_forward_observation_negative_sequence_violation(valid_forward_obs_payload: dict[str, Any]) -> None:
    """Fail closed when sequence number is negative."""
    valid_forward_obs_payload["observation_sequence"] = -1
    with pytest.raises(DataContractError, match="observation_sequence must be non-negative"):
        ForwardObservation(**valid_forward_obs_payload)


def test_forward_observation_turnover_bounds_violation(valid_forward_obs_payload: dict[str, Any]) -> None:
    """Fail closed when turnover_ratio is outside [0.0, 2.0]."""
    valid_forward_obs_payload["turnover_ratio"] = Decimal("2.5")
    with pytest.raises(DataContractError, match="turnover_ratio must be in"):
        ForwardObservation(**valid_forward_obs_payload)


def test_forward_observation_invalid_dossier_digest(valid_forward_obs_payload: dict[str, Any]) -> None:
    """Fail closed when dossier_digest is not a valid 64-hex lowercase string."""
    valid_forward_obs_payload["dossier_digest"] = "invalid_hash"
    with pytest.raises(DataContractError, match="Invalid SHA-256 digest format"):
        ForwardObservation(**valid_forward_obs_payload)


def test_forward_observation_digest_tamper_detection(valid_forward_obs_payload: dict[str, Any]) -> None:
    """Fail closed when supplied observation_digest does not match recomputed hash."""
    valid_forward_obs_payload["observation_digest"] = "e" * 64
    with pytest.raises(DataContractError, match="Observation digest tampering detected"):
        ForwardObservation(**valid_forward_obs_payload)


# ============================================================================
# 4. FORWARD HEALTH POLICY INVARIANTS
# ============================================================================

def test_forward_health_policy_happy_path() -> None:
    """Verify default policy parameters and deterministic policy digest generation."""
    policy = ForwardHealthPolicy()
    assert policy.min_observations == 30
    assert policy.rolling_window_size == 60
    assert policy.degradation_persistence_n == 3
    assert policy.recovery_persistence_m == 10
    assert policy.recovery_cooldown_periods == 5
    assert len(policy.policy_digest) == 64


def test_forward_health_policy_asymmetric_hysteresis_invariant() -> None:
    """Fail closed when recovery_persistence_m <= degradation_persistence_n."""
    # Equal persistence violates strict asymmetry
    with pytest.raises(DataContractError, match="Asymmetric hysteresis invariant violated"):
        ForwardHealthPolicy(degradation_persistence_n=5, recovery_persistence_m=5)

    # Inverted persistence
    with pytest.raises(DataContractError, match="Asymmetric hysteresis invariant violated"):
        ForwardHealthPolicy(degradation_persistence_n=5, recovery_persistence_m=4)


def test_forward_health_policy_window_bounds() -> None:
    """Fail closed when min_observations exceeds rolling_window_size."""
    with pytest.raises(DataContractError, match="Invalid observation window"):
        ForwardHealthPolicy(min_observations=70, rolling_window_size=60)


def test_forward_health_policy_drawdown_limit_bounds() -> None:
    """Fail closed when critical_drawdown_limit <= 0 or > 1.0."""
    with pytest.raises(DataContractError, match="critical_drawdown_limit must be in"):
        ForwardHealthPolicy(critical_drawdown_limit=Decimal("0.0"))

    with pytest.raises(DataContractError, match="critical_drawdown_limit must be in"):
        ForwardHealthPolicy(critical_drawdown_limit=Decimal("1.2"))


# ============================================================================
# 5. STRATEGY FORWARD DRIFT EVIDENCE & AUTHORITY INVARIANTS
# ============================================================================

@pytest.fixture
def sample_metrics() -> ForwardWindowMetrics:
    return ForwardWindowMetrics(
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
        information_coefficient=None,
        ic_decay_slope=None,
    )


def test_strategy_forward_drift_evidence_happy_path(sample_metrics: ForwardWindowMetrics) -> None:
    """Verify clean instantiation of evidence document."""
    t0 = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    policy = ForwardHealthPolicy()

    evidence = StrategyForwardDriftEvidence(
        evidence_id="EVID_001",
        strategy_id="STRAT_01",
        dossier_digest=VALID_DIGEST_A,
        as_of_utc=t0,
        wall_clock_utc=t0,
        health_state=ForwardHealthState.HEALTHY,
        recommendation=ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
        metrics=sample_metrics,
        policy_digest=policy.policy_digest,
        consecutive_degraded_periods=0,
        consecutive_recovery_periods=10,
        drift_flags=(),
    )
    assert evidence.evidence_id == "EVID_001"
    assert len(evidence.evidence_digest) == 64
    assert not hasattr(evidence, "is_tournament_eligible")


def test_strategy_forward_drift_evidence_authority_creep_forbidden(sample_metrics: ForwardWindowMetrics) -> None:
    """Strictly reject attempt to inject is_tournament_eligible into StrategyForwardDriftEvidence."""
    t0 = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    policy = ForwardHealthPolicy()

    payload: dict[str, Any] = {
        "evidence_id": "EVID_001",
        "strategy_id": "STRAT_01",
        "dossier_digest": VALID_DIGEST_A,
        "as_of_utc": t0,
        "wall_clock_utc": t0,
        "health_state": ForwardHealthState.HEALTHY,
        "recommendation": ForwardGovernanceRecommendation.CONTINUE_UNRESTRICTED,
        "metrics": sample_metrics,
        "policy_digest": policy.policy_digest,
        "consecutive_degraded_periods": 0,
        "consecutive_recovery_periods": 10,
        "drift_flags": (),
        "is_tournament_eligible": True,  # PROHIBITED AUTHORITY CREEP
    }

    with pytest.raises(DataContractError, match="AUTHORITY_CREEP_DETECTED"):
        StrategyForwardDriftEvidence(**cast(Any, payload))


# ============================================================================
# 6. EXECUTION ATTRIBUTION POLICY & COST EVIDENCE
# ============================================================================

def test_execution_attribution_policy_happy_path() -> None:
    """Verify execution attribution policy default parameters."""
    policy = ExecutionAttributionPolicy()
    assert policy.sample_window_days == 30
    assert policy.min_reliable_sample_count == 100
    assert policy.min_reliable_coverage_ratio == Decimal("0.95")
    assert policy.critical_fail_closed_coverage_ratio == Decimal("0.80")
    assert len(policy.policy_digest) == 64


def test_execution_attribution_policy_coverage_inversion_rejection() -> None:
    """Fail closed when critical coverage >= reliable coverage."""
    with pytest.raises(DataContractError, match="Coverage ratio policy invalid"):
        ExecutionAttributionPolicy(
            min_reliable_coverage_ratio=Decimal("0.80"),
            critical_fail_closed_coverage_ratio=Decimal("0.85"),
        )


def test_execution_cost_evidence_happy_path() -> None:
    """Verify execution cost evidence DTO and Tier 1 lineage digest generation."""
    t0 = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    policy = ExecutionAttributionPolicy()

    cost_evidence = ExecutionCostEvidence(
        evidence_id="CEVID_001",
        venue="ALPACA_PAPER",
        symbol="AAPL",
        as_of_utc=t0,
        coverage_start_utc=t0 - timedelta(days=30),
        coverage_end_utc=t0,
        fill_count=150,
        effective_sample_count=150,
        coverage_ratio=Decimal("0.98"),
        mean_gross_drag_bps=Decimal("4.25"),
        mean_net_cost_bps=Decimal("3.85"),
        median_net_cost_bps=Decimal("3.50"),
        p95_gross_drag_bps=Decimal("8.10"),
        standard_error_bps=Decimal("0.35"),
        confidence_interval_95_half_width_bps=Decimal("0.69"),
        is_statistically_reliable=True,
        policy_digest=policy.policy_digest,
    )
    assert cost_evidence.evidence_id == "CEVID_001"
    assert len(cost_evidence.lineage_digest) == 64
    assert cost_evidence.is_statistically_reliable is True
