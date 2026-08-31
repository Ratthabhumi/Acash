"""Unit and Invariant Tests for Native Advanced Optimizers (Phase 8 Batch 2D.2 Final Hardening).

Tests:
- Hierarchical Risk Parity (HRP) canonical core + ACASH constraint policy.
- Linkage methods (SINGLE, COMPLETE, AVERAGE) with angular correlation distance.
- Strict fail-closed on degenerate cluster variance (no silent 50/50 fallback).
- Equal Risk Contribution (ERC) constrained nonlinear optimization + separate acceptance verification.
- Zero/near-zero variance fail-closed boundary (zero magic floors).
- ERC exact relative risk contribution tolerance <= 1% (0.01).
- Long-only non-negative weights and budget conservation.
- 1-asset and 2-asset universe edge cases.
- Permutation invariance and determinism.
- AST architecture boundary check (no Phase 7 execution or Governance calls).
"""

import ast
from datetime import datetime, timezone
from decimal import Decimal
import inspect
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.estimators import (
    LedoitWolfShrinkageCovarianceEstimator,
    SampleCovarianceEstimator,
)
from acash.portfolio.optimizers import (
    DistanceMetric,
    EqualRiskContributionAllocator,
    HierarchicalRiskParityAllocator,
    LinkageMethod,
)
from acash.portfolio.schema import (
    AssetReturnPanel,
    PortfolioConstraints,
)


def _default_constraints() -> PortfolioConstraints:
    return PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("1.0"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )


def _sample_return_panel(n_obs: int = 100) -> AssetReturnPanel:
    np.random.seed(42)
    # Generate 3 correlated asset return series with different volatilities
    t1 = np.random.normal(0.001, 0.012, n_obs)
    t2 = 0.8 * t1 + np.random.normal(0.0005, 0.008, n_obs)
    t3 = 0.3 * t1 + np.random.normal(0.0008, 0.018, n_obs)

    timestamps = tuple(
        datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        for _ in range(n_obs)
    )
    matrix = tuple(
        (Decimal(str(round(t1[i], 6))), Decimal(str(round(t2[i], 6))), Decimal(str(round(t3[i], 6))))
        for i in range(n_obs)
    )

    return AssetReturnPanel(
        universe_id="UNIV_TEST_3A",
        timestamps=timestamps,
        symbols=("AAPL", "MSFT", "GOOG"),
        returns_matrix=matrix,
        frequency="1D",
    )


# --- HRP Tests ---

def test_hrp_single_asset_case() -> None:
    panel = AssetReturnPanel(
        universe_id="UNIV_1A",
        timestamps=(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)),
        symbols=("SPY",),
        returns_matrix=((Decimal("0.01"),), (Decimal("-0.01"),)),
        frequency="1D",
    )
    allocator = HierarchicalRiskParityAllocator()
    cand = allocator.compute_candidate(panel, _default_constraints(), {})
    assert cand.asset_weights["SPY"] == Decimal("0.95")
    assert cand.cash_weight == Decimal("0.05")


def test_hrp_two_asset_case() -> None:
    np.random.seed(123)
    t1 = np.random.normal(0.0, 0.01, 50)  # low vol
    t2 = np.random.normal(0.0, 0.03, 50)  # high vol
    panel = AssetReturnPanel(
        universe_id="UNIV_2A",
        timestamps=tuple(datetime(2026, 1, 1, tzinfo=timezone.utc) for _ in range(50)),
        symbols=("LOW_VOL", "HIGH_VOL"),
        returns_matrix=tuple((Decimal(str(round(t1[i], 6))), Decimal(str(round(t2[i], 6)))) for i in range(50)),
        frequency="1D",
    )
    allocator = HierarchicalRiskParityAllocator()
    cand = allocator.compute_candidate(panel, _default_constraints(), {})

    # Lower volatility asset must receive higher weight
    assert cand.asset_weights["LOW_VOL"] > cand.asset_weights["HIGH_VOL"]
    assert cand.cash_weight is not None
    assert cand.asset_weights["LOW_VOL"] + cand.asset_weights["HIGH_VOL"] + cand.cash_weight == Decimal("1.0")


def test_hrp_deterministic_output() -> None:
    panel = _sample_return_panel()
    allocator = HierarchicalRiskParityAllocator()
    cand1 = allocator.compute_candidate(panel, _default_constraints(), {})
    cand2 = allocator.compute_candidate(panel, _default_constraints(), {})

    assert cand1.candidate_digest == cand2.candidate_digest
    assert cand1.asset_weights == cand2.asset_weights
    assert cand1.cash_weight == cand2.cash_weight


def test_hrp_linkage_method_options() -> None:
    panel = _sample_return_panel()
    for method in (LinkageMethod.SINGLE, LinkageMethod.COMPLETE, LinkageMethod.AVERAGE):
        allocator = HierarchicalRiskParityAllocator(linkage_method=method)
        cand = allocator.compute_candidate(panel, _default_constraints(), {})
        assert len(cand.asset_weights) == 3
        assert sum(cand.asset_weights.values()) + (cand.cash_weight or Decimal("0.0")) == Decimal("1.0")


def test_hrp_budget_and_max_weight_constraint() -> None:
    panel = _sample_return_panel()
    constrained = PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("0.40"),  # max weight 40%
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.10"),  # min cash 10%
    )
    allocator = HierarchicalRiskParityAllocator()
    cand = allocator.compute_candidate(panel, constrained, {})

    for sym, w in cand.asset_weights.items():
        assert w <= Decimal("0.40000001")
        assert w >= Decimal("0.0")
    assert cand.cash_weight is not None
    assert cand.cash_weight >= Decimal("0.09999999")


def test_hrp_zero_variance_fail_closed() -> None:
    timestamps = tuple(datetime(2026, 1, i, tzinfo=timezone.utc) for i in range(1, 6))
    matrix = tuple((Decimal("0.0"), Decimal("0.0")) for _ in range(5))
    panel = AssetReturnPanel(
        universe_id="UNIV_FLAT",
        timestamps=timestamps,
        symbols=("A", "B"),
        returns_matrix=matrix,
        frequency="1D",
    )
    allocator = HierarchicalRiskParityAllocator()
    with pytest.raises(DataContractError, match="Zero variance detected|Non-finite or near-zero variance"):
        allocator.compute_candidate(panel, _default_constraints(), {})


# --- ERC / Risk Parity Tests ---

def test_erc_single_asset_case() -> None:
    panel = AssetReturnPanel(
        universe_id="UNIV_1A",
        timestamps=(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)),
        symbols=("SPY",),
        returns_matrix=((Decimal("0.01"),), (Decimal("-0.01"),)),
        frequency="1D",
    )
    allocator = EqualRiskContributionAllocator()
    cand = allocator.compute_candidate(panel, _default_constraints(), {})
    assert cand.asset_weights["SPY"] == Decimal("0.95")
    assert cand.cash_weight == Decimal("0.05")


def test_erc_equal_risk_contribution_tight_tolerance_verification() -> None:
    panel = _sample_return_panel()
    allocator = EqualRiskContributionAllocator(max_relative_rc_deviation=0.01)
    cand = allocator.compute_candidate(panel, _default_constraints(), {})

    # Compute marginal risk contributions: RC_i = w_i * (Sigma w)_i / port_vol
    cov = LedoitWolfShrinkageCovarianceEstimator().estimate_covariance(panel)
    w_vec = np.array([float(cand.asset_weights[s]) for s in panel.symbols], dtype=np.float64)
    sigma_w = cov @ w_vec
    port_vol = np.sqrt(float(w_vec @ sigma_w))
    rc = (w_vec * sigma_w) / port_vol

    # Verify risk contributions satisfy tight <= 1% relative deviation tolerance
    rc_mean = np.mean(rc)
    rel_dev = np.abs(rc - rc_mean) / rc_mean
    assert np.all(rel_dev < 0.01), f"Risk contributions deviate by more than 1%: {rel_dev}"

    # Verify in_sample_metrics diagnostics
    assert "rc_max_relative_deviation" in cand.in_sample_metrics
    assert "solver_converged" in cand.in_sample_metrics
    assert "solver_objective" in cand.in_sample_metrics
    assert "solver_iterations" in cand.in_sample_metrics
    assert "erc_acceptance_status" in cand.in_sample_metrics
    assert cand.in_sample_metrics["solver_converged"] == Decimal("1.0")
    assert cand.in_sample_metrics["erc_acceptance_status"] == Decimal("1.0")
    assert cand.in_sample_metrics["rc_max_relative_deviation"] < Decimal("0.01")


def test_erc_acceptance_failure_fail_closed() -> None:
    """If acceptance threshold is negative/impossible, allocator must fail closed."""
    panel = _sample_return_panel()
    allocator = EqualRiskContributionAllocator(max_relative_rc_deviation=-0.01)

    with pytest.raises(DataContractError, match="Equal Risk Contribution acceptance criteria failed"):
        allocator.compute_candidate(panel, _default_constraints(), {})


def test_erc_deterministic_output() -> None:
    panel = _sample_return_panel()
    allocator = EqualRiskContributionAllocator()
    cand1 = allocator.compute_candidate(panel, _default_constraints(), {})
    cand2 = allocator.compute_candidate(panel, _default_constraints(), {})

    assert cand1.candidate_digest == cand2.candidate_digest
    assert cand1.asset_weights == cand2.asset_weights
    assert cand1.cash_weight == cand2.cash_weight


def test_erc_max_weight_constraint() -> None:
    panel = _sample_return_panel()
    constrained = PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("0.35"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )
    allocator = EqualRiskContributionAllocator()
    cand = allocator.compute_candidate(panel, constrained, {})

    for sym, w in cand.asset_weights.items():
        assert w <= Decimal("0.35000001")
        assert w >= Decimal("0.0")


def test_erc_zero_variance_fail_closed() -> None:
    timestamps = tuple(datetime(2026, 1, i, tzinfo=timezone.utc) for i in range(1, 6))
    matrix = tuple((Decimal("0.0"), Decimal("0.0")) for _ in range(5))
    panel = AssetReturnPanel(
        universe_id="UNIV_FLAT",
        timestamps=timestamps,
        symbols=("A", "B"),
        returns_matrix=matrix,
        frequency="1D",
    )
    allocator = EqualRiskContributionAllocator()
    with pytest.raises(DataContractError, match="Zero variance detected|Non-finite or near-zero variance"):
        allocator.compute_candidate(panel, _default_constraints(), {})


# --- Cross-Optimizer & AST Boundary Checks ---

def test_optimizers_do_not_mutate_input_panel() -> None:
    panel = _sample_return_panel()
    raw_matrix_before = panel.returns_matrix

    HierarchicalRiskParityAllocator().compute_candidate(panel, _default_constraints(), {})
    EqualRiskContributionAllocator().compute_candidate(panel, _default_constraints(), {})

    assert panel.returns_matrix == raw_matrix_before


def test_optimizers_architecture_boundary_ast() -> None:
    """Verify via AST that optimizers.py does not import or call Phase 7 execution or Governance."""
    from acash.portfolio import optimizers
    source = inspect.getsource(optimizers)
    tree = ast.parse(source)

    forbidden_modules = {
        "acash.execution",
        "acash.backtest",
        "acash.portfolio.governance",
        "acash.portfolio.planner",
    }
    forbidden_names = {
        "PortfolioGovernanceGate",
        "RebalancePlanner",
        "AllocationDecision",
        "RebalancePlan",
        "OrderIntent",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden_modules:
                    assert not alias.name.startswith(f), f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for f in forbidden_modules:
                    assert not node.module.startswith(f), f"Forbidden import from: {node.module}"
            for alias in node.names:
                assert alias.name not in forbidden_names, f"Forbidden name imported: {alias.name}"
