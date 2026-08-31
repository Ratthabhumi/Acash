"""Unit and invariant tests for Phase 8 Portfolio Domain Schema and DTOs."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.portfolio.schema import (
    AllocationCandidate,
    AllocationDecision,
    AllocationEvaluation,
    AssetReturnPanel,
    PortfolioConstraints,
    PortfolioUniverse,
    RebalancePlan,
    RiskSnapshot,
    recompute_digest,
)


def _utc_now() -> datetime:
    return datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)


# ============================================================================
# 1. PortfolioUniverse Tests
# ============================================================================

def test_portfolio_universe_canonical_creation_and_digest() -> None:
    """Verify PortfolioUniverse sorts symbols lexicographically and generates deterministic SHA-256."""
    u1 = PortfolioUniverse(
        universe_id="UNIV_TEST",
        assets=("SPY", "AAPL", "MSFT"),
        as_of=_utc_now(),
    )
    # Must be sorted uppercase
    assert u1.assets == ("AAPL", "MSFT", "SPY")
    assert len(u1.universe_digest) == 64
    assert u1.universe_digest == recompute_digest(u1)


def test_portfolio_universe_empty_or_duplicate_rejection() -> None:
    """Verify PortfolioUniverse fails-closed on empty or duplicate assets."""
    with pytest.raises(DataContractError, match="must contain at least one asset"):
        PortfolioUniverse(universe_id="UNIV_EMPTY", assets=(), as_of=_utc_now())

    with pytest.raises(DataContractError, match="Duplicate symbol detected"):
        PortfolioUniverse(universe_id="UNIV_DUP", assets=("SPY", "AAPL", "SPY"), as_of=_utc_now())


def test_portfolio_universe_permutation_invariance() -> None:
    """Verify PortfolioUniverse generates identical sorted assets and digest regardless of input order."""
    u1 = PortfolioUniverse(universe_id="UNIV_P", assets=("MSFT", "AAPL", "NVDA"), as_of=_utc_now())
    u2 = PortfolioUniverse(universe_id="UNIV_P", assets=("NVDA", "MSFT", "AAPL"), as_of=_utc_now())
    assert u1.assets == u2.assets == ("AAPL", "MSFT", "NVDA")
    assert u1.universe_digest == u2.universe_digest


# ============================================================================
# 2. AssetReturnPanel Tests
# ============================================================================

def test_asset_return_panel_canonical_creation_and_digest() -> None:
    """Verify AssetReturnPanel validates dimensions, types, and computes digest."""
    t1 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    returns = (
        (Decimal("0.01"), Decimal("0.02")),
        (Decimal("-0.005"), Decimal("0.015")),
        (Decimal("0.02"), Decimal("-0.01")),
    )

    panel = AssetReturnPanel(
        universe_id="UNIV_TEST",
        timestamps=(t1, t2, t3),
        symbols=("AAPL", "SPY"),
        returns_matrix=returns,
        frequency="1D",
    )

    assert panel.T == 3
    assert panel.N == 2
    assert len(panel.panel_digest) == 64
    assert panel.panel_digest == recompute_digest(panel)


def test_asset_return_panel_non_finite_or_mismatch_rejection() -> None:
    """Verify AssetReturnPanel fails closed on NaN/Inf or dimension mismatch."""
    t1 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Dimension mismatch: 2 timestamps but 1 return row
    with pytest.raises(DataContractError, match="Return matrix row count"):
        AssetReturnPanel(
            universe_id="UNIV_TEST",
            timestamps=(t1, t2),
            symbols=("AAPL", "SPY"),
            returns_matrix=((Decimal("0.01"), Decimal("0.02")),),
            frequency="1D",
        )

    # Non-finite entry (NaN)
    with pytest.raises(DomainValidationError, match="must be a finite Decimal"):
        AssetReturnPanel(
            universe_id="UNIV_TEST",
            timestamps=(t1,),
            symbols=("AAPL", "SPY"),
            returns_matrix=((Decimal("NaN"), Decimal("0.02")),),
            frequency="1D",
        )


# ============================================================================
# 3. PortfolioConstraints Tests
# ============================================================================

def test_portfolio_constraints_invariants() -> None:
    """Verify PortfolioConstraints validates long-only and leverage bounds."""
    c = PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("0.5"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
        max_turnover_per_rebalance=Decimal("0.20"),
    )
    assert c.min_weight == Decimal("0.0")
    assert c.max_weight == Decimal("0.5")
    assert c.min_cash_buffer == Decimal("0.05")

    # Infeasible bounds: min_weight > max_weight
    with pytest.raises(DomainValidationError, match="min_weight.*cannot exceed max_weight"):
        PortfolioConstraints(
            min_weight=Decimal("0.6"),
            max_weight=Decimal("0.4"),
        )


# ============================================================================
# 4. RiskSnapshot Tests
# ============================================================================

def test_risk_snapshot_invariants() -> None:
    """Verify RiskSnapshot valid attributes and positive equity requirement."""
    snap = RiskSnapshot(
        snapshot_id="SNAP_001",
        timestamp=_utc_now(),
        account_equity=Decimal("100000.00"),
        cash_balance=Decimal("50000.00"),
        margin_used=Decimal("0.00"),
        margin_headroom=Decimal("100000.00"),
        margin_buffer_threshold=Decimal("10000.00"),
        current_drawdown_pct=Decimal("0.02"),
        max_drawdown_limit_pct=Decimal("0.10"),
        is_kill_switch_active=False,
    )
    assert snap.account_equity == Decimal("100000.00")
    assert not snap.is_kill_switch_active

    with pytest.raises(DomainValidationError, match="account_equity must be strictly positive"):
        RiskSnapshot(
            snapshot_id="SNAP_ZERO",
            timestamp=_utc_now(),
            account_equity=Decimal("0.00"),
            cash_balance=Decimal("0.00"),
            margin_used=Decimal("0.00"),
            margin_headroom=Decimal("0.00"),
            margin_buffer_threshold=Decimal("1000.00"),
            current_drawdown_pct=Decimal("0.0"),
            max_drawdown_limit_pct=Decimal("0.10"),
            is_kill_switch_active=False,
        )


# ============================================================================
# 5. AllocationCandidate Tests
# ============================================================================

def test_allocation_candidate_creation_and_normalization() -> None:
    """Verify AllocationCandidate handles raw asset weights and derived cash."""
    cand = AllocationCandidate(
        candidate_id="CAND_01",
        allocator_name="EQUAL_WEIGHT",
        asset_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        cash_weight=Decimal("0.10"),
        in_sample_metrics={"variance": Decimal("0.0004")},
    )
    assert cand.cash_weight == Decimal("0.10")
    assert len(cand.candidate_digest) == 64
    assert cand.candidate_digest == recompute_digest(cand)


def test_allocation_candidate_weight_sum_exceeded() -> None:
    """Verify AllocationCandidate rejects weights summing to > 1.0."""
    with pytest.raises(DomainValidationError, match="Asset weights sum.*exceeds 1.0"):
        AllocationCandidate(
            candidate_id="CAND_OVER",
            allocator_name="TEST",
            asset_weights={"AAPL": Decimal("0.60"), "SPY": Decimal("0.50")},
        )


# ============================================================================
# 6. AllocationEvaluation Tests
# ============================================================================

def test_allocation_evaluation_invariants() -> None:
    """Verify AllocationEvaluation enforces normalized sum = 1.0 and generates digest."""
    eval_record = AllocationEvaluation(
        candidate_id="CAND_01",
        normalized_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        normalized_cash_weight=Decimal("0.10"),
        oos_sharpe_ratio=Decimal("1.45"),
        oos_cvar_95=Decimal("0.025"),
        turnover_required=Decimal("0.10"),
        estimated_transaction_cost=Decimal("15.00"),
        net_expected_excess_return=Decimal("0.065"),
        hurdle_rate_cleared=True,
        constraints_satisfied=True,
        rank_score=Decimal("1.35"),
    )
    assert eval_record.rank_score == Decimal("1.35")
    assert len(eval_record.evaluation_digest) == 64
    assert eval_record.evaluation_digest == recompute_digest(eval_record)


# ============================================================================
# 7. AllocationDecision Tests
# ============================================================================

def test_allocation_decision_invariants() -> None:
    """Verify AllocationDecision binds authorized weights and handles FORCED_CASH verdicts."""
    decision = AllocationDecision(
        decision_id="DEC_01",
        selected_candidate_id="CAND_01",
        allocator_name="EQUAL_WEIGHT",
        authorized_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        cash_weight=Decimal("0.10"),
        authorization_timestamp=_utc_now(),
        is_fallback_baseline=True,
        gate_verdict="AUTHORIZED",
        rationale="Top baseline cleared hurdle and risk constraints.",
    )
    assert decision.gate_verdict == "AUTHORIZED"
    assert len(decision.decision_digest) == 64
    assert decision.decision_digest == recompute_digest(decision)

    cash_decision = AllocationDecision(
        decision_id="DEC_CASH",
        selected_candidate_id="CAND_CASH",
        allocator_name="CASH",
        authorized_weights={"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")},
        cash_weight=Decimal("1.0"),
        authorization_timestamp=_utc_now(),
        is_fallback_baseline=True,
        gate_verdict="FORCED_CASH_RISK",
        rationale="Kill switch active.",
    )
    assert cash_decision.cash_weight == Decimal("1.0")


# ============================================================================
# 8. RebalancePlan Tests
# ============================================================================

def test_rebalance_plan_notional_and_delta_invariants() -> None:
    """Verify RebalancePlan captures desired delta and reference notional correctly."""
    plan = RebalancePlan(
        plan_id="PLAN_01",
        decision_id="DEC_01",
        as_of=_utc_now(),
        current_weights={"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")},
        target_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        desired_notional_delta={"AAPL": Decimal("45000.00"), "SPY": Decimal("45000.00")},
        desired_position_delta={"AAPL": Decimal("300"), "SPY": Decimal("75")},
        reference_prices={"AAPL": Decimal("150.00"), "SPY": Decimal("600.00")},
        estimated_rebalance_friction=Decimal("25.00"),
    )
    assert plan.desired_position_delta["AAPL"] == Decimal("300")
    assert len(plan.plan_digest) == 64
    assert plan.plan_digest == recompute_digest(plan)
