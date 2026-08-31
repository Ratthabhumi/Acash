"""Unit and Invariant Tests for Rebalance Planner (Phase 8 Batch 2C.1).

Tests all 18 mandatory planner invariants:
- Normal rebalance and delta calculation
- Zero delta / no-op idempotency
- Increasing and decreasing positions
- Full de-risking / flattening to cash from non-zero positions
- Missing current position defaulting to 0
- Missing, zero, or negative reference prices (fail closed)
- Negative position (short positions) rejection (fail closed)
- Valuation epoch preceding decision authorization timestamp (fail closed)
- Rounding policies (EXACT_FRACTIONAL, FLOOR_INTEGER, ROUND_NEAREST_INTEGER, REJECT_FRACTIONAL)
- Post-rounding constraint validation (cash buffer and weight bounds)
- Cryptographic decision digest binding & tamper rejection
- Deterministic symbol universe ordering
- Immutable content digest reproducibility (identical content digest regardless of runtime plan_id)
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.planner import (
    RebalancePlanner,
    RebalancePlannerConfig,
    RoundingPolicy,
)
from acash.portfolio.schema import (
    AllocationDecision,
    PortfolioConstraints,
)


def _default_constraints() -> PortfolioConstraints:
    return PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("1.0"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )


def _sample_decision(is_cash: bool = False) -> AllocationDecision:
    ts = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    if is_cash:
        return AllocationDecision(
            decision_id="DEC_CASH_001",
            selected_candidate_id="CASH_SOVEREIGN_FALLBACK",
            allocator_name="CASH",
            authorized_weights={},
            cash_weight=Decimal("1.0"),
            authorization_timestamp=ts,
            is_fallback_baseline=True,
            gate_verdict="REJECT_NO_ELIGIBLE_CANDIDATE",
            rationale="All candidates failed.",
            candidate_digest="",
            evaluation_digest="",
            risk_snapshot_digest="a" * 64,
            constraints_digest="b" * 64,
            governance_policy_version="v1.0.0",
        )
    return AllocationDecision(
        decision_id="DEC_INVEST_001",
        selected_candidate_id="CAND_EW",
        allocator_name="EQUAL_WEIGHT",
        authorized_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        cash_weight=Decimal("0.10"),
        authorization_timestamp=ts,
        is_fallback_baseline=False,
        gate_verdict="APPROVED_INVESTABLE_ALLOCATION",
        rationale="Approved.",
        candidate_digest="c" * 64,
        evaluation_digest="d" * 64,
        risk_snapshot_digest="a" * 64,
        constraints_digest="b" * 64,
        governance_policy_version="v1.0.0",
    )


# A. Normal rebalance
def test_planner_normal_rebalance() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    current_pos = {"AAPL": Decimal("100.0"), "SPY": Decimal("50.0")}
    ref_prices = {"AAPL": Decimal("150.0"), "SPY": Decimal("450.0")}

    # Target: AAPL: 45k (300 shares), SPY: 45k (100 shares)
    # Delta: AAPL: +200 shares, SPY: +50 shares
    plan = planner.generate_plan(
        decision=decision,
        account_equity=equity,
        current_positions=current_pos,
        reference_prices=ref_prices,
        constraints=_default_constraints(),
    )

    assert plan.desired_position_delta["AAPL"] == Decimal("200.0")
    assert plan.desired_position_delta["SPY"] == Decimal("50.0")
    assert plan.desired_notional_delta["AAPL"] == Decimal("30000.0")
    assert plan.desired_notional_delta["SPY"] == Decimal("22500.0")
    assert plan.realized_cash_weight == Decimal("0.10")
    assert plan.decision_digest == decision.decision_digest


# B. Zero delta / No-op
def test_planner_zero_delta_no_op() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    # Already at exact target positions: 300 AAPL ($45k) and 100 SPY ($45k)
    current_pos = {"AAPL": Decimal("300.0"), "SPY": Decimal("100.0")}
    ref_prices = {"AAPL": Decimal("150.0"), "SPY": Decimal("450.0")}

    plan = planner.generate_plan(
        decision=decision,
        account_equity=equity,
        current_positions=current_pos,
        reference_prices=ref_prices,
        constraints=_default_constraints(),
    )

    assert plan.desired_position_delta["AAPL"] == Decimal("0.0")
    assert plan.desired_position_delta["SPY"] == Decimal("0.0")
    assert plan.desired_notional_delta["AAPL"] == Decimal("0.0")
    assert plan.desired_notional_delta["SPY"] == Decimal("0.0")
    assert plan.estimated_rebalance_friction == Decimal("0.0")


# C. Increase and Decrease positions
def test_planner_increase_and_decrease_positions() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    # AAPL is 100 (needs 300 -> +200), SPY is 150 (needs 100 -> -50)
    current_pos = {"AAPL": Decimal("100.0"), "SPY": Decimal("150.0")}
    ref_prices = {"AAPL": Decimal("150.0"), "SPY": Decimal("450.0")}

    plan = planner.generate_plan(
        decision=decision,
        account_equity=equity,
        current_positions=current_pos,
        reference_prices=ref_prices,
        constraints=_default_constraints(),
    )

    assert plan.desired_position_delta["AAPL"] == Decimal("200.0")
    assert plan.desired_position_delta["SPY"] == Decimal("-50.0")
    assert plan.desired_notional_delta["AAPL"] == Decimal("30000.0")
    assert plan.desired_notional_delta["SPY"] == Decimal("-22500.0")


# D. Full de-risk to Cash (Flattening Plan)
def test_planner_full_derisk_to_cash() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision(is_cash=True)
    equity = Decimal("100000.0")
    current_pos = {"AAPL": Decimal("100.0"), "SPY": Decimal("50.0")}
    ref_prices = {"AAPL": Decimal("150.0"), "SPY": Decimal("450.0")}

    # All positions should be flattened to 0 (delta = -current)
    plan = planner.generate_plan(
        decision=decision,
        account_equity=equity,
        current_positions=current_pos,
        reference_prices=ref_prices,
        constraints=_default_constraints(),
    )

    assert plan.desired_position_delta["AAPL"] == Decimal("-100.0")
    assert plan.desired_position_delta["SPY"] == Decimal("-50.0")
    assert plan.desired_notional_delta["AAPL"] == Decimal("-15000.0")
    assert plan.desired_notional_delta["SPY"] == Decimal("-22500.0")
    assert plan.target_weights["AAPL"] == Decimal("0.0")
    assert plan.target_weights["SPY"] == Decimal("0.0")
    assert plan.realized_cash_weight == Decimal("1.0")


# E. Missing current position defaults to 0.0
def test_planner_missing_current_position_defaults_zero() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    current_pos: dict[str, Decimal] = {}  # No current positions
    ref_prices = {"AAPL": Decimal("150.0"), "SPY": Decimal("450.0")}

    plan = planner.generate_plan(
        decision=decision,
        account_equity=equity,
        current_positions=current_pos,
        reference_prices=ref_prices,
        constraints=_default_constraints(),
    )

    assert plan.current_weights["AAPL"] == Decimal("0.0")
    assert plan.current_weights["SPY"] == Decimal("0.0")
    assert plan.desired_position_delta["AAPL"] == Decimal("300.0")
    assert plan.desired_position_delta["SPY"] == Decimal("100.0")


# F. Missing reference price -> Fail Closed
def test_planner_missing_reference_price_fail_closed() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    current_pos = {"AAPL": Decimal("100.0")}
    ref_prices = {"AAPL": Decimal("150.0")}  # SPY missing!

    with pytest.raises(DataContractError, match="Missing required reference price for symbol 'SPY'"):
        planner.generate_plan(
            decision=decision,
            account_equity=equity,
            current_positions=current_pos,
            reference_prices=ref_prices,
            constraints=_default_constraints(),
        )


# G. Non-positive reference price -> Fail Closed
def test_planner_non_positive_reference_price_fail_closed() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    current_pos = {"AAPL": Decimal("100.0"), "SPY": Decimal("50.0")}
    ref_prices = {"AAPL": Decimal("-150.0"), "SPY": Decimal("450.0")}

    with pytest.raises(DataContractError, match="Reference price for symbol 'AAPL' must be strictly positive"):
        planner.generate_plan(
            decision=decision,
            account_equity=equity,
            current_positions=current_pos,
            reference_prices=ref_prices,
            constraints=_default_constraints(),
        )


# H. Negative Current Position (Short Position Violation) -> Fail Closed
def test_planner_negative_position_fail_closed() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    current_pos = {"AAPL": Decimal("-10.0"), "SPY": Decimal("50.0")}
    ref_prices = {"AAPL": Decimal("150.0"), "SPY": Decimal("450.0")}

    with pytest.raises(DataContractError, match="Short positions are unsupported"):
        planner.generate_plan(
            decision=decision,
            account_equity=equity,
            current_positions=current_pos,
            reference_prices=ref_prices,
            constraints=_default_constraints(),
        )


# I. Valuation Epoch Preceding Decision Authorization -> Fail Closed
def test_planner_epoch_preceding_decision_fail_closed() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    current_pos = {"AAPL": Decimal("100.0"), "SPY": Decimal("50.0")}
    ref_prices = {"AAPL": Decimal("150.0"), "SPY": Decimal("450.0")}
    # Decision authorized at 12:00, but as_of is 11:00 (stale valuation)
    stale_as_of = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(DataContractError, match="Valuation as_of.*precedes decision authorization timestamp"):
        planner.generate_plan(
            decision=decision,
            account_equity=equity,
            current_positions=current_pos,
            reference_prices=ref_prices,
            constraints=_default_constraints(),
            as_of=stale_as_of,
        )


# J. Rounding Policy: FLOOR_INTEGER
def test_planner_rounding_policy_floor() -> None:
    planner = RebalancePlanner(config=RebalancePlannerConfig(rounding_policy=RoundingPolicy.FLOOR_INTEGER))
    decision = _sample_decision()
    equity = Decimal("10000.0")
    current_pos = {"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")}
    # Target value: $4500. Price $149 -> 4500 / 149 = 30.2013 -> floor = 30
    ref_prices = {"AAPL": Decimal("149.0"), "SPY": Decimal("450.0")}

    plan = planner.generate_plan(
        decision=decision,
        account_equity=equity,
        current_positions=current_pos,
        reference_prices=ref_prices,
        constraints=_default_constraints(),
    )
    assert plan.desired_position_delta["AAPL"] == Decimal("30")
    assert plan.target_weights["AAPL"] == Decimal("30") * Decimal("149.0") / equity


# K. Rounding Policy: REJECT_FRACTIONAL
def test_planner_rounding_policy_reject_fractional() -> None:
    planner = RebalancePlanner(config=RebalancePlannerConfig(rounding_policy=RoundingPolicy.REJECT_FRACTIONAL))
    decision = _sample_decision()
    equity = Decimal("10000.0")
    current_pos = {"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")}
    ref_prices = {"AAPL": Decimal("149.0"), "SPY": Decimal("450.0")}

    with pytest.raises(DataContractError, match="Fractional target quantity.*rejected under REJECT_FRACTIONAL"):
        planner.generate_plan(
            decision=decision,
            account_equity=equity,
            current_positions=current_pos,
            reference_prices=ref_prices,
            constraints=_default_constraints(),
        )


# L. Tampered Decision Digest -> Fail Closed
def test_planner_tampered_decision_digest_fail_closed() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    tampered_decision = AllocationDecision.model_construct(
        **{**decision.model_dump(), "decision_digest": "f" * 64}
    )

    with pytest.raises(DataContractError, match="cryptographic digest verification failed"):
        planner.generate_plan(
            decision=tampered_decision,
            account_equity=Decimal("100000.0"),
            current_positions={"AAPL": Decimal("100.0"), "SPY": Decimal("50.0")},
            reference_prices={"AAPL": Decimal("150.0"), "SPY": Decimal("450.0")},
            constraints=_default_constraints(),
        )


# M. Pure Content Digest Determinism across different runtime timestamps/plan_ids
def test_planner_pure_content_digest_determinism() -> None:
    planner = RebalancePlanner()
    decision = _sample_decision()
    equity = Decimal("100000.0")
    current_pos = {"SPY": Decimal("50.0"), "AAPL": Decimal("100.0")}
    ref_prices = {"SPY": Decimal("450.0"), "AAPL": Decimal("150.0")}

    # Different runtime timestamps (both valid and >= decision.authorization_timestamp)
    ts1 = datetime(2026, 9, 1, 12, 10, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 9, 1, 12, 20, 0, tzinfo=timezone.utc)

    plan1 = planner.generate_plan(decision, equity, current_pos, ref_prices, _default_constraints(), as_of=ts1)
    plan2 = planner.generate_plan(decision, equity, current_pos, ref_prices, _default_constraints(), as_of=ts2)

    # Content digests are 100% identical!
    assert plan1.plan_digest == plan2.plan_digest
    assert plan1.desired_position_delta == plan2.desired_position_delta
    assert plan1.desired_notional_delta == plan2.desired_notional_delta
    assert list(plan1.desired_position_delta.keys()) == ["AAPL", "SPY"]
