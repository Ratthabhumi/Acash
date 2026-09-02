"""Unit tests for Phase 11 Realized Execution Drag Attribution Engine.

Verifies:
1. Strict Maker/Taker scope: Phase 11 v1 is explicitly scoped to aggressive/taker fills.
   Passive/maker fills fail closed with DataContractError(MAKER_EXECUTION_OUT_OF_SCOPE).
2. Authoritative Coverage Denominator Provenance:
   expected_fill_count must be explicitly provided from upstream execution census/manifest.
   Missing denominator cannot be assumed to be 100% and fails closed.
3. BUY order attribution: adverse timing, adverse slippage, spread drag, and fees.
4. SELL order attribution: directional multiplier (-1 for SELL), adverse timing, adverse slippage.
5. SELL price improvement and favorable timing: signed negative values, non-negative gross baseline.
6. Fee & Rebate calculations and legitimate negative net realized cost.
7. Data contract invariants: zero/negative notional, canonical midpoint violation, inverted spread.
8. Sample coverage gating: critical fail-closed threshold (< 80% coverage).
9. Statistical reliability gating (N >= 100 and coverage >= 95%).
10. Deterministic median and P95 nearest-rank percentiles in pure Decimal space.
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
    LiquidityRole,
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
    liquidity_role: LiquidityRole = LiquidityRole.TAKER,
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
        liquidity_role=liquidity_role,
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
# 1. MAKER / TAKER SCOPE GUARDS (OPTION A)
# ============================================================================

def test_maker_liquidity_role_fails_closed_out_of_scope() -> None:
    """Phase 11 v1 attribution engine strictly rejects passive/maker fills."""
    obs = _create_fill_observation(
        obs_id="MAKER_01",
        side=ExecutionSide.BUY,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("99.95"),
        arrival_ask=Decimal("100.05"),
        fill_px=Decimal("99.95"),
        liquidity_role=LiquidityRole.MAKER,
    )

    with pytest.raises(DataContractError, match="MAKER_EXECUTION_OUT_OF_SCOPE"):
        decompose_execution_drag(obs)


def test_taker_liquidity_role_succeeds() -> None:
    """Taker/aggressive executions are in-scope and decomposed cleanly."""
    obs = _create_fill_observation(
        obs_id="TAKER_01",
        side=ExecutionSide.BUY,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("99.95"),
        arrival_ask=Decimal("100.05"),
        fill_px=Decimal("100.05"),
        liquidity_role=LiquidityRole.TAKER,
    )

    drag = decompose_execution_drag(obs)
    assert isinstance(drag, RealizedExecutionDrag)
    assert drag.observation_id == "TAKER_01"


# ============================================================================
# 2. COVERAGE DENOMINATOR PROVENANCE
# ============================================================================

def test_missing_coverage_denominator_fails_closed() -> None:
    """Authoritative expected_fill_count must be explicitly provided from upstream lineage."""
    policy = ExecutionAttributionPolicy()
    obs = _create_fill_observation(
        obs_id="OBS_01",
        side=ExecutionSide.BUY,
        qty=Decimal("10.0"),
        decision_mid=Decimal("100.0"),
        arrival_bid=Decimal("99.9"),
        arrival_ask=Decimal("100.1"),
        fill_px=Decimal("100.1"),
    )

    # Missing denominator cannot be assumed to be 100%
    with pytest.raises(DataContractError, match="UNVERIFIABLE_COVERAGE_DENOMINATOR"):
        aggregate_execution_cost_evidence(
            observations=[obs],
            policy=policy,
            venue="ALPACA_PAPER",
            symbol="AAPL",
            as_of_utc=BASE_TIME,
            coverage_start_utc=BASE_TIME - timedelta(days=1),
            coverage_end_utc=BASE_TIME + timedelta(days=1),
            expected_fill_count=None,  # Missing upstream denominator
        )


def test_invalid_expected_fill_count_fails_closed() -> None:
    """Non-positive expected_fill_count is rejected immediately."""
    policy = ExecutionAttributionPolicy()
    obs = _create_fill_observation(
        obs_id="OBS_01",
        side=ExecutionSide.BUY,
        qty=Decimal("10.0"),
        decision_mid=Decimal("100.0"),
        arrival_bid=Decimal("99.9"),
        arrival_ask=Decimal("100.1"),
        fill_px=Decimal("100.1"),
    )

    with pytest.raises(DataContractError, match="expected_fill_count must be strictly positive"):
        aggregate_execution_cost_evidence(
            observations=[obs],
            policy=policy,
            venue="ALPACA_PAPER",
            symbol="AAPL",
            as_of_utc=BASE_TIME,
            coverage_start_utc=BASE_TIME - timedelta(days=1),
            coverage_end_utc=BASE_TIME + timedelta(days=1),
            expected_fill_count=0,
        )


# ============================================================================
# 3. DIRECTIONAL BUY / SELL ATTRIBUTION & PRICE IMPROVEMENT
# ============================================================================

def test_buy_execution_drag_adverse_milestones() -> None:
    """Verify BUY order attribution with adverse timing and adverse slippage."""
    obs = _create_fill_observation(
        obs_id="BUY_01",
        side=ExecutionSide.BUY,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("100.10"),
        arrival_ask=Decimal("100.30"),
        fill_px=Decimal("100.35"),
        fee_usd=Decimal("1.00"),
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


def test_sell_execution_drag_adverse_milestones() -> None:
    """Verify SELL order attribution with adverse timing and adverse slippage (-1 multiplier)."""
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

    # Market dropped before arrival -> adverse timing for SELL: -1 * (99.80 - 100.00) / 100.00 * 10000 = +20.0 bps
    assert drag.timing_drag_bps == Decimal("20.0")
    # Filled below quoted bid -> adverse slippage for SELL: -1 * (99.65 - 99.70) / 99.70 * 10000 = +5.015... bps
    expected_slippage = (Decimal("0.05") / Decimal("99.70")) * Decimal("10000.0")
    assert drag.slippage_drag_bps == expected_slippage
    assert drag.gross_execution_drag_bps > Decimal("0.0")


def test_sell_favorable_timing_and_price_improvement() -> None:
    """Verify SELL order price improvement (filled above quoted bid) and favorable timing."""
    # Decision mid: 100.00
    # Market rose before arrival: bid 100.20, ask 100.40 -> mid 100.30
    # Favorable timing for SELL: -1 * (100.30 - 100.00) / 100.00 * 10000 = -30.0 bps
    # Filled above quoted bid at 100.25 (better than arrival bid 100.20 -> price improvement!)
    # Slippage drag: -1 * (100.25 - 100.20) / 100.20 * 10000 = -4.990... bps
    obs = _create_fill_observation(
        obs_id="SELL_IMPROVED",
        side=ExecutionSide.SELL,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("100.20"),
        arrival_ask=Decimal("100.40"),
        fill_px=Decimal("100.25"),
        fee_usd=Decimal("0.50"),
    )

    drag = decompose_execution_drag(obs)

    assert drag.timing_drag_bps == Decimal("-30.0")
    assert drag.slippage_drag_bps < Decimal("0.0")

    # Gross drag floor: max(0, timing) == 0, max(0, slippage) == 0
    expected_spread = (Decimal("0.20") / Decimal("200.60")) * Decimal("10000.0")
    expected_fee = (Decimal("0.50") / Decimal("10025.00")) * Decimal("10000.0")
    assert drag.gross_execution_drag_bps == expected_spread + expected_fee


# ============================================================================
# 4. FEE & REBATE CONSERVATION & NEGATIVE NET COST
# ============================================================================

def test_fee_and_rebate_conservation() -> None:
    """Verify exact fee and rebate basis point scaling against filled notional."""
    qty = Decimal("50.0")
    fill_px = Decimal("200.00")
    notional = (qty * fill_px).quantize(USD_SCALE)  # 10,000.00 USD
    fee_usd = Decimal("2.50")  # 2.50 / 10000.00 * 10000 = 2.50 bps
    rebate_usd = Decimal("1.25")  # 1.25 / 10000.00 * 10000 = 1.25 bps

    obs = _create_fill_observation(
        obs_id="FEE_REBATE_01",
        side=ExecutionSide.BUY,
        qty=qty,
        decision_mid=Decimal("200.00"),
        arrival_bid=Decimal("199.95"),
        arrival_ask=Decimal("200.05"),
        fill_px=fill_px,
        fee_usd=fee_usd,
        rebate_usd=rebate_usd,
    )

    drag = decompose_execution_drag(obs)
    assert drag.commission_fee_bps == Decimal("2.50")
    assert drag.rebate_benefit_bps == Decimal("1.25")


def test_legitimate_negative_net_realized_cost_from_rebate() -> None:
    """Verify signed net realized cost can legitimately be negative if rebate exceeds gross drag."""
    obs = _create_fill_observation(
        obs_id="REBATE_DOMINANT",
        side=ExecutionSide.BUY,
        qty=Decimal("100.0"),
        decision_mid=Decimal("100.00"),
        arrival_bid=Decimal("99.99"),
        arrival_ask=Decimal("100.01"),
        fill_px=Decimal("100.01"),
        fee_usd=Decimal("0.00"),
        rebate_usd=Decimal("10.00"),  # ~10 bps rebate on 10,001 USD
    )

    drag = decompose_execution_drag(obs)

    assert drag.spread_drag_bps == Decimal("1.0")
    assert drag.gross_execution_drag_bps == Decimal("1.0")
    assert drag.rebate_benefit_bps > Decimal("9.0")
    assert drag.net_realized_execution_cost_bps < Decimal("0.0")


# ============================================================================
# 5. DATA CONTRACT INVARIANTS (REJECTION OF INVALID STATES)
# ============================================================================

def test_invalid_zero_or_negative_notional_rejected() -> None:
    """ExecutionObservation rejects non-positive notional value."""
    t0 = BASE_TIME
    with pytest.raises(DataContractError, match="filled_notional_usd must be positive"):
        ExecutionObservation(
            observation_id="INV_01",
            execution_id="EXEC_01",
            intent_id="INT_01",
            strategy_id="STRAT_01",
            venue="ALPACA_PAPER",
            symbol="AAPL",
            side=ExecutionSide.BUY,
            requested_quantity=Decimal("10.0"),
            filled_quantity=Decimal("10.0"),
            filled_notional_usd=Decimal("0.00"),  # Invalid zero notional
            decision_mid_price=Decimal("100.00"),
            arrival_bid_price=Decimal("99.90"),
            arrival_ask_price=Decimal("100.10"),
            arrival_mid_price=Decimal("100.00"),
            executed_fill_price=Decimal("100.00"),
            commission_fee_usd=Decimal("0.00"),
            rebate_usd=Decimal("0.00"),
            decision_timestamp_utc=t0,
            arrival_timestamp_utc=t0,
            fill_timestamp_utc=t0,
        )


def test_canonical_midpoint_invariant_violation_rejected() -> None:
    """Option A Canonical Midpoint (bid + ask)/2 is strictly enforced."""
    t0 = BASE_TIME
    with pytest.raises(DataContractError, match="Option A Canonical Midpoint violated"):
        ExecutionObservation(
            observation_id="INV_02",
            execution_id="EXEC_02",
            intent_id="INT_02",
            strategy_id="STRAT_01",
            venue="ALPACA_PAPER",
            symbol="AAPL",
            side=ExecutionSide.BUY,
            requested_quantity=Decimal("10.0"),
            filled_quantity=Decimal("10.0"),
            filled_notional_usd=Decimal("1000.00"),
            decision_mid_price=Decimal("100.00"),
            arrival_bid_price=Decimal("99.90"),
            arrival_ask_price=Decimal("100.10"),
            arrival_mid_price=Decimal("100.05"),  # Inconsistent midpoint! (should be 100.00)
            executed_fill_price=Decimal("100.00"),
            commission_fee_usd=Decimal("0.00"),
            rebate_usd=Decimal("0.00"),
            decision_timestamp_utc=t0,
            arrival_timestamp_utc=t0,
            fill_timestamp_utc=t0,
        )


def test_inverted_spread_rejected() -> None:
    """Inverted spread (bid > ask) is strictly rejected."""
    t0 = BASE_TIME
    with pytest.raises(DataContractError, match="Inverted spread"):
        ExecutionObservation(
            observation_id="INV_03",
            execution_id="EXEC_03",
            intent_id="INT_03",
            strategy_id="STRAT_01",
            venue="ALPACA_PAPER",
            symbol="AAPL",
            side=ExecutionSide.BUY,
            requested_quantity=Decimal("10.0"),
            filled_quantity=Decimal("10.0"),
            filled_notional_usd=Decimal("1000.00"),
            decision_mid_price=Decimal("100.00"),
            arrival_bid_price=Decimal("100.20"),  # Bid > Ask!
            arrival_ask_price=Decimal("100.10"),
            arrival_mid_price=Decimal("100.15"),
            executed_fill_price=Decimal("100.15"),
            commission_fee_usd=Decimal("0.00"),
            rebate_usd=Decimal("0.00"),
            decision_timestamp_utc=t0,
            arrival_timestamp_utc=t0,
            fill_timestamp_utc=t0,
        )


# ============================================================================
# 6. COVERAGE GATING & STATISTICAL RELIABILITY
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

    # 70 fills provided vs 100 expected -> coverage = 70% < 80% critical threshold
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
    """Incomplete evidence (coverage 85%) produces evidence flagged is_statistically_reliable=False."""
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
# 7. DETERMINISTIC PERCENTILE ESTIMATION
# ============================================================================

def test_p95_and_median_deterministic_percentiles() -> None:
    """Verify median and P95 percentile calculation across distinct friction levels."""
    obs_list = [
        _create_fill_observation(
            obs_id=f"OBS_{i:03d}",
            side=ExecutionSide.BUY,
            qty=Decimal("10.0"),
            decision_mid=Decimal("100.0"),
            arrival_bid=Decimal("99.9"),
            arrival_ask=Decimal("100.1"),
            fill_px=Decimal("100.1"),
            fee_usd=Decimal(f"{i + 1}.00"),
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
        expected_fill_count=100,  # Explicit authoritative denominator
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
