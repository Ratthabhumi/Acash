"""Unit tests for Phase 11 Realized Execution Drag Attribution Engine.

Verifies:
1. BUY order attribution with discrete price milestones (spread, adverse timing, adverse slippage, fees).
2. SELL order attribution with directional side-sign multiplier (+1 BUY, -1 SELL).
3. Favorable timing drift and price improvement (signed negative values, non-negative gross drag).
4. Legitimate negative net realized cost from liquidity provider maker rebates.
5. Sample coverage gating: critical fail-closed threshold (< 80% coverage raises DataContractError).
6. Statistical reliability gating (min_reliable_sample_count=100, min_reliable_coverage=95%).
7. Incomplete evidence philosophy: incomplete sample is a coverage/reliability issue, not a performance penalty.
8. Deterministic median and P95 percentile rank calculation in pure Decimal space.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.attribution import (
    ExecutionAttributionEngine,
    aggregate_execution_cost_evidence,
    decompose_execution_drag,
)
from acash.monitoring.schema import (
    USD_SCALE,
    ExecutionAttributionPolicy,
    ExecutionCostEvidence,
    ExecutionObservation,
    ExecutionSide,
    RealizedExecutionDrag,
)

BASE_TIME = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)


def _create_fill_observation(
    obs_id: str,
    side: ExecutionSide,
    qty: Decimal,
    decision_mid: Decimal,
    arrival_bid: Decimal,
    arrival_ask: Decimal,
    fill_px: Decimal,
    fee_usd: Decimal = Decimal("0.35"),
    rebate_usd: Decimal = Decimal("0.00"),
    ts: datetime = BASE_TIME,
) -> ExecutionObservation:
    """Helper creating a validated ExecutionObservation with Option A canonical midpoint."""
    arrival_mid = (arrival_bid + arrival_ask) / Decimal("2.0")
    notional = (qty * fill_px).quantize(USD_SCALE)

    return ExecutionObservation(
        observation_id=obs_id,
        execution_id=f"EXEC_{obs_id}",
        intent_id=f"INT_{obs_id}",
        strategy_id="STRAT_01",
        venue="ALPACA_PAPER",
        symbol="AAPL",
        side=side,
        requested_quantity=qty,
        filled_quantity=qty,
        filled_notional_usd=notional,
        decision_mid_price=decision_mid,
        arrival_bid_price=arrival_bid,
        arrival_ask_price=arrival_ask,
        arrival_mid_price=arrival_mid,
        executed_fill_price=fill_px,
        commission_fee_usd=fee_usd,
        rebate_usd=rebate_usd,
        decision_timestamp_utc=ts,
        arrival_timestamp_utc=ts + timedelta(milliseconds=20),
        fill_timestamp_utc=ts + timedelta(milliseconds=100),
    )


# ============================================================================
# 1. BUY & SELL DIRECTIONAL ATTRIBUTION
# ============================================================================

def test_buy_execution_drag_adverse_milestones() -> None:
    """Verify BUY order attribution with adverse timing and adverse slippage."""
    # Decision mid: 100.00
    # Arrival: bid 100.10, ask 100.30 -> mid 100.20
    # Adverse timing: +1 * (100.20 - 100.00) / 100.00 * 10000 = +20.0 bps
    # Fill: 100.35 (worse than arrival ask 100.30)
    # Adverse slippage: +1 * (100.35 - 100.30) / 100.30 * 10000 = 4.985... bps
    # Spread drag: (100.30 - 100.10) / (2 * 100.20) * 10000 = 0.20 / 200.40 * 10000 = 9.980... bps
    # Qty = 100, notional = 10035.00, fee = 1.00 -> fee drag = 1.00 / 10035 * 10000 = 0.9965... bps
    obs = _create_fill_observation(
        obs_id="BUY_01",
        side=ExecutionSide.BUY,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("100.10"),
        arrival_ask=Decimal("100.30"),
        fill_px=Decimal("100.35"),
        fee_usd=Decimal("1.00"),
        rebate_usd=Decimal("0.00"),
    )

    drag = decompose_execution_drag(obs)

    assert isinstance(drag, RealizedExecutionDrag)
    assert drag.timing_drag_bps == Decimal("20.0")

    expected_spread = (Decimal("0.20") / Decimal("200.40")) * Decimal("10000.0")
    assert drag.spread_drag_bps == expected_spread

    expected_slippage = (Decimal("0.05") / Decimal("100.30")) * Decimal("10000.0")
    assert drag.slippage_drag_bps == expected_slippage

    expected_fee = (Decimal("1.00") / Decimal("10035.00")) * Decimal("10000.0")
    assert drag.commission_fee_bps == expected_fee

    assert drag.gross_execution_drag_bps == expected_spread + Decimal("20.0") + expected_slippage + expected_fee
    assert drag.net_realized_execution_cost_bps == drag.gross_execution_drag_bps


def test_sell_execution_drag_directional_inversion() -> None:
    """Verify SELL order attribution directional multiplier (-1 for SELL)."""
    # Decision mid: 100.00
    # Market dropped to arrival bid 99.70, ask 99.90 -> mid 99.80
    # Adverse timing for SELL: -1 * (99.80 - 100.00) / 100.00 * 10000 = +20.0 bps (adverse)
    # Fill: 99.65 (worse than arrival bid 99.70)
    # Adverse slippage for SELL: -1 * (99.65 - 99.70) / 99.70 * 10000 = -1 * (-0.05) / 99.70 * 10000 = +5.015... bps
    obs = _create_fill_observation(
        obs_id="SELL_01",
        side=ExecutionSide.SELL,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("99.70"),
        arrival_ask=Decimal("99.90"),
        fill_px=Decimal("99.65"),
        fee_usd=Decimal("1.00"),
    )

    drag = decompose_execution_drag(obs)

    assert drag.timing_drag_bps == Decimal("20.0")
    expected_slippage = (Decimal("0.05") / Decimal("99.70")) * Decimal("10000.0")
    assert drag.slippage_drag_bps == expected_slippage
    assert drag.gross_execution_drag_bps > Decimal("0.0")


# ============================================================================
# 2. FAVORABLE TIMING, PRICE IMPROVEMENT & NEGATIVE NET COST
# ============================================================================

def test_favorable_timing_and_price_improvement() -> None:
    """Verify signed negative values for favorable timing and price improvement."""
    # BUY order with price moving lower before arrival (favorable timing)
    # Decision mid: 100.00 -> arrival mid 99.80 (bid 99.70, ask 99.90)
    # Timing drag = +1 * (99.80 - 100.00) / 100.00 * 10000 = -20.0 bps (favorable!)
    # Fill executed inside spread at 99.80 (better than ask 99.90 -> price improvement!)
    # Slippage drag = +1 * (99.80 - 99.90) / 99.90 * 10000 = -10.01... bps (price improvement!)
    obs = _create_fill_observation(
        obs_id="BUY_IMPROVED",
        side=ExecutionSide.BUY,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("99.70"),
        arrival_ask=Decimal("99.90"),
        fill_px=Decimal("99.80"),
        fee_usd=Decimal("0.50"),
    )

    drag = decompose_execution_drag(obs)

    assert drag.timing_drag_bps == Decimal("-20.0")
    assert drag.slippage_drag_bps < Decimal("0.0")

    # Gross drag enforces non-negative floor on timing and slippage components
    # max(0, timing) == 0, max(0, slippage) == 0
    # gross drag = spread + fee >= 0
    expected_spread = (Decimal("0.20") / Decimal("199.60")) * Decimal("10000.0")
    expected_fee = (Decimal("0.50") / Decimal("9980.00")) * Decimal("10000.0")
    assert drag.gross_execution_drag_bps == expected_spread + expected_fee


def test_legitimate_negative_net_realized_cost_from_maker_rebate() -> None:
    """Verify signed net realized cost can legitimately be negative if maker rebate exceeds gross drag."""
    # Zero timing drift, zero slippage (filled at ask), spread = 1.0 bps, fee = 0.0, rebate = 5.0 bps
    # arrival bid: 99.99, ask: 100.01 -> mid: 100.00 -> spread = 0.02 / 200.00 * 10000 = 1.0 bps
    # fill: 100.01 -> slippage = 0.0
    # rebate = 10.00 USD on 10001.00 USD notional = ~9.999 bps
    obs = _create_fill_observation(
        obs_id="MAKER_REBATE_01",
        side=ExecutionSide.BUY,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("99.99"),
        arrival_ask=Decimal("100.01"),
        fill_px=Decimal("100.01"),
        fee_usd=Decimal("0.00"),
        rebate_usd=Decimal("10.00"),
    )

    drag = decompose_execution_drag(obs)

    assert drag.spread_drag_bps == Decimal("1.0")
    assert drag.gross_execution_drag_bps == Decimal("1.0")
    assert drag.rebate_benefit_bps > Decimal("9.0")
    # Net cost is negative (profit/benefit to strategy)
    assert drag.net_realized_execution_cost_bps < Decimal("0.0")


# ============================================================================
# 3. SAMPLE COVERAGE & STATISTICAL RELIABILITY GATING
# ============================================================================

def test_critical_coverage_ratio_breach_fail_closed() -> None:
    """Fail closed when coverage ratio < critical_fail_closed_coverage_ratio (0.80)."""
    policy = ExecutionAttributionPolicy(
        critical_fail_closed_coverage_ratio=Decimal("0.80"),
    )

    obs = _create_fill_observation(
        obs_id="OBS_01",
        side=ExecutionSide.BUY,
        qty=Decimal("10.0"),
        decision_mid=Decimal("100.0"),
        arrival_bid=Decimal("99.9"),
        arrival_ask=Decimal("100.1"),
        fill_px=Decimal("100.1"),
    )

    # Expected 100 fills, but only 70 fills provided -> coverage = 70% < 80%
    with pytest.raises(DataContractError, match="CRITICAL_COVERAGE_BREACH"):
        aggregate_execution_cost_evidence(
            observations=[obs] * 70,
            policy=policy,
            venue="ALPACA_PAPER",
            symbol="AAPL",
            as_of_utc=BASE_TIME,
            coverage_start_utc=BASE_TIME - timedelta(days=1),
            coverage_end_utc=BASE_TIME + timedelta(days=1),
            expected_fill_count=100,
        )


def test_incomplete_evidence_is_unreliable_not_performance_penalty() -> None:
    """Incomplete evidence (N < 100 or 80% <= coverage < 95%) marks is_statistically_reliable=False.

    Enforces: No Evidence != Negative Evidence.
    It does NOT fail closed and does NOT artificially penalize the strategy.
    """
    policy = ExecutionAttributionPolicy(
        min_reliable_sample_count=100,
        min_reliable_coverage_ratio=Decimal("0.95"),
        critical_fail_closed_coverage_ratio=Decimal("0.80"),
    )

    obs = _create_fill_observation(
        obs_id="OBS_01",
        side=ExecutionSide.BUY,
        qty=Decimal("10.0"),
        decision_mid=Decimal("100.0"),
        arrival_bid=Decimal("99.9"),
        arrival_ask=Decimal("100.1"),
        fill_px=Decimal("100.1"),
    )

    # 85 fills out of 100 expected -> coverage = 85% (acceptable for unverified telemetry, but unreliable)
    evidence = aggregate_execution_cost_evidence(
        observations=[obs] * 85,
        policy=policy,
        venue="ALPACA_PAPER",
        symbol="AAPL",
        as_of_utc=BASE_TIME,
        coverage_start_utc=BASE_TIME - timedelta(days=1),
        coverage_end_utc=BASE_TIME + timedelta(days=1),
        expected_fill_count=100,
    )

    assert isinstance(evidence, ExecutionCostEvidence)
    assert evidence.fill_count == 85
    assert evidence.coverage_ratio == Decimal("0.85")
    # Explicitly flagged as not statistically reliable without failing the system
    assert evidence.is_statistically_reliable is False
    assert len(evidence.lineage_digest) == 64


def test_statistically_reliable_evidence_generation() -> None:
    """Verify evidence aggregation when sample size >= 100 and coverage >= 95%."""
    policy = ExecutionAttributionPolicy(
        min_reliable_sample_count=100,
        min_reliable_coverage_ratio=Decimal("0.95"),
    )

    obs_list = [
        _create_fill_observation(
            obs_id=f"OBS_{i:03d}",
            side=ExecutionSide.BUY if i % 2 == 0 else ExecutionSide.SELL,
            qty=Decimal("10.0"),
            decision_mid=Decimal("100.0"),
            arrival_bid=Decimal("99.9"),
            arrival_ask=Decimal("100.1"),
            fill_px=Decimal("100.1") if i % 2 == 0 else Decimal("99.9"),
        )
        for i in range(120)
    ]

    evidence = aggregate_execution_cost_evidence(
        observations=obs_list,
        policy=policy,
        venue="ALPACA_PAPER",
        symbol="AAPL",
        as_of_utc=BASE_TIME,
        coverage_start_utc=BASE_TIME - timedelta(days=1),
        coverage_end_utc=BASE_TIME + timedelta(days=1),
        expected_fill_count=120,
    )

    assert evidence.fill_count == 120
    assert evidence.coverage_ratio == Decimal("1.0")
    assert evidence.is_statistically_reliable is True
    assert evidence.standard_error_bps >= Decimal("0.0")
    assert evidence.confidence_interval_95_half_width_bps >= Decimal("0.0")
    assert isinstance(evidence.mean_gross_drag_bps, Decimal)
    assert isinstance(evidence.median_net_cost_bps, Decimal)
    assert isinstance(evidence.p95_gross_drag_bps, Decimal)


# ============================================================================
# 4. P95 & MEDIAN BEHAVIOR
# ============================================================================

def test_p95_and_median_deterministic_percentiles() -> None:
    """Verify median and P95 percentile calculation across distinct friction levels."""
    # 100 observations with net costs ranging from 1.0 to 100.0 bps
    obs_list = [
        _create_fill_observation(
            obs_id=f"OBS_{i:03d}",
            side=ExecutionSide.BUY,
            qty=Decimal("10.0"),
            decision_mid=Decimal("100.0"),
            arrival_bid=Decimal("99.9"),
            arrival_ask=Decimal("100.1"),
            fill_px=Decimal("100.1"),
            fee_usd=Decimal(f"{i + 1}.00"),  # varying fee directly translates to varying drag
        )
        for i in range(100)
    ]

    policy = ExecutionAttributionPolicy()
    evidence = aggregate_execution_cost_evidence(
        observations=obs_list,
        policy=policy,
        venue="ALPACA_PAPER",
        symbol="AAPL",
        as_of_utc=BASE_TIME,
        coverage_start_utc=BASE_TIME - timedelta(days=1),
        coverage_end_utc=BASE_TIME + timedelta(days=1),
    )

    # Median of 100 elements: average of index 49 and 50
    drags = [decompose_execution_drag(o).net_realized_execution_cost_bps for o in obs_list]
    sorted_drags = sorted(drags)
    expected_median = (sorted_drags[49] + sorted_drags[50]) / Decimal("2.0")
    assert evidence.median_net_cost_bps == expected_median

    # P95 element: index 94 (95th element)
    gross_drags = sorted([decompose_execution_drag(o).gross_execution_drag_bps for o in obs_list])
    expected_p95 = gross_drags[94]
    assert evidence.p95_gross_drag_bps == expected_p95
