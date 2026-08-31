"""Native Level 2 Advanced Portfolio Optimizers for Phase 8 Portfolio Engine.

Provides mathematically rigorous, deterministic implementations of:
- Hierarchical Risk Parity (HRP) (Lopez de Prado 2016) with ACASH Constraint Policy
- Equal Risk Contribution / Risk Parity (ERC) (Maillard, Roncalli, Teïletche 2010)

Strictly preserves Phase 8 architecture:
- Reuses decoupled CovarianceEstimators
- Emits AllocationCandidate without calling Governance or Phase 7 execution
- Strict fail-closed contracts on numerical singularity, degenerate clusters, or non-convergence (0 magic floors)
"""

from decimal import Decimal
from enum import Enum
import math
from typing import Mapping, Optional, Sequence
import numpy as np
import scipy.cluster.hierarchy as sch  # type: ignore[import-untyped]
import scipy.optimize as sco  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.portfolio.estimators import (
    CovarianceEstimator,
    LedoitWolfShrinkageCovarianceEstimator,
    SampleCovarianceEstimator,
)
from acash.portfolio.schema import (
    AllocationCandidate,
    AssetReturnPanel,
    PortfolioConstraints,
)


# Centralized Numerical Admissibility & Convergence Constants
EPSILON_VARIANCE_ADMISSIBILITY: float = 1e-14  # Strict fail-closed threshold for zero/near-zero variance
EPSILON_CLUSTER_VARIANCE: float = 1e-16  # Guard for degenerate zero variance cluster bisection (fail closed)
ERC_SOLVER_FTOL: float = 1e-12  # SciPy SLSQP optimization termination tolerance
ERC_MAX_ITERATIONS: int = 1000  # Maximum solver iterations
ERC_DEFAULT_MAX_RELATIVE_RC_DEVIATION: float = 0.01  # 1% maximum relative risk contribution deviation for unconstrained ERC


class LinkageMethod(str, Enum):
    """Hierarchical clustering linkage methods compatible with metric correlation distance."""
    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"


class DistanceMetric(str, Enum):
    """Correlation distance formulation for HRP."""
    ANGULAR = "ANGULAR"  # Canonical Lopez de Prado (2016): d_ij = sqrt(0.5 * (1 - rho_ij))
    ABSOLUTE = "ABSOLUTE"  # Absolute correlation distance: d_ij = sqrt(1 - |rho_ij|)


class HierarchicalRiskParityAllocator:
    """Hierarchical Risk Parity (HRP) Allocator (Lopez de Prado 2016 with ACASH Constraint Policy).

    Classification of Mathematical Steps:
    1. Canonical HRP Core:
       - Angular correlation distance: d_ij = sqrt(0.5 * (1 - rho_ij))
       - Quasi-diagonalization via hierarchical tree leaf traversal
       - Recursive bisection with cluster inverse-variance weighting
    2. ACASH Implementation Choice:
       - Metric linkage method selection (default: SINGLE, compatible with COMPLETE / AVERAGE)
       - Decoupled CovarianceEstimator protocol integration
    3. ACASH Constraint Policy:
       - Sizing budget allocation B_risky = min(1.0 - min_cash_buffer, max_gross_leverage)
       - Deterministic post-processing weight capping and proportional excess redistribution
       - Strict fail-closed boundary on degenerate cluster variance (no silent 50/50 fallback)
    """

    def __init__(
        self,
        covariance_estimator: Optional[CovarianceEstimator] = None,
        linkage_method: LinkageMethod = LinkageMethod.SINGLE,
        distance_metric: DistanceMetric = DistanceMetric.ANGULAR,
    ) -> None:
        self.covariance_estimator = covariance_estimator or LedoitWolfShrinkageCovarianceEstimator()
        self.linkage_method = linkage_method
        self.distance_metric = distance_metric

    @property
    def allocator_name(self) -> str:
        return "HIERARCHICAL_RISK_PARITY"

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        """Compute HRP candidate weights in Decimal space. Fail-closed on invalid state."""
        n_assets = len(panel.symbols)
        if n_assets == 0:
            raise DataContractError("Cannot compute HRP allocation on empty universe.")

        # Single asset edge case
        if n_assets == 1:
            sym = panel.symbols[0]
            max_w = min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_weight)
            max_w = min(max_w, constraints.max_gross_leverage)
            cash_w = Decimal("1.0") - max_w
            return AllocationCandidate(
                candidate_id=f"CAND_HRP_{panel.universe_id}",
                allocator_name=self.allocator_name,
                asset_weights={sym: max_w},
                cash_weight=cash_w,
                in_sample_metrics={"expected_return": Decimal("0.0"), "variance": Decimal("0.0")},
            )

        # 1. Estimate Covariance & Correlation Matrix (Risky Assets Only)
        cov = self.covariance_estimator.estimate_covariance(panel)
        if cov.shape != (n_assets, n_assets):
            raise DataContractError(f"Covariance shape mismatch: expected ({n_assets}, {n_assets}), got {cov.shape}")

        diag_var = np.diag(cov)
        if np.any(diag_var <= EPSILON_VARIANCE_ADMISSIBILITY) or np.any(~np.isfinite(diag_var)):
            raise DataContractError(
                f"Non-finite or near-zero variance (<= {EPSILON_VARIANCE_ADMISSIBILITY}) in covariance diagonal. Fail closed."
            )

        diag_std = np.sqrt(diag_var)
        inv_std = 1.0 / diag_std
        corr = cov * np.outer(inv_std, inv_std)
        np.fill_diagonal(corr, 1.0)
        corr = np.clip(corr, -1.0, 1.0)

        # 2. Compute Distance Matrix (Canonical Angular or Absolute)
        if self.distance_metric == DistanceMetric.ANGULAR:
            dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
        elif self.distance_metric == DistanceMetric.ABSOLUTE:
            dist = np.sqrt(np.clip(1.0 - np.abs(corr), 0.0, 1.0))
        else:
            raise DataContractError(f"Unsupported distance metric: {self.distance_metric}")
        np.fill_diagonal(dist, 0.0)

        # 3. Hierarchical Tree Clustering (Linkage)
        dist_condensed = dist[np.triu_indices(n_assets, k=1)]
        linkage_mat = sch.linkage(dist_condensed, method=self.linkage_method.value)

        # 4. Quasi-Diagonalization (Canonical Leaf Traversal)
        sorted_indices = self._get_quasi_diagonal_indices(linkage_mat, n_assets)

        # 5. Recursive Bisection (Canonical Inverse-Variance Cluster Allocation)
        raw_weights = self._compute_recursive_bisection(cov, sorted_indices)

        # 6. Apply Budget, Max Weight Constraints & Residual Cash (ACASH Constraint Policy)
        budget_risky = float(min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_gross_leverage))
        max_w_fl = float(constraints.max_weight)
        min_w_fl = float(constraints.min_weight)

        constrained_weights = self._apply_weight_caps(raw_weights, budget_risky, min_w_fl, max_w_fl)

        # Convert to Decimal dict
        out_weights: dict[str, Decimal] = {}
        total_risky_dec = Decimal("0.0")
        for i, sym in enumerate(panel.symbols):
            w_dec = Decimal(str(round(constrained_weights[i], 8)))
            out_weights[sym] = w_dec
            total_risky_dec += w_dec

        cash_w_dec = max(Decimal("0.0"), Decimal("1.0") - total_risky_dec)

        # Compute in-sample variance metric
        w_vec = np.array([float(out_weights[s]) for s in panel.symbols], dtype=np.float64)
        port_var = float(w_vec @ cov @ w_vec)

        return AllocationCandidate(
            candidate_id=f"CAND_HRP_{panel.universe_id}",
            allocator_name=self.allocator_name,
            asset_weights=out_weights,
            cash_weight=cash_w_dec,
            in_sample_metrics={"variance": Decimal(str(round(port_var, 8)))},
        )

    def _get_quasi_diagonal_indices(self, linkage_mat: np.ndarray, num_items: int) -> list[int]:
        """Traverse dendrogram tree to obtain ordered leaf indices."""
        root_node = sch.to_tree(linkage_mat, rd=False)
        order: list[int] = []

        def _traverse(node: sch.ClusterNode) -> None:
            if node.is_leaf():
                order.append(node.id)
            else:
                if node.left:
                    _traverse(node.left)
                if node.right:
                    _traverse(node.right)

        _traverse(root_node)
        return order

    def _compute_recursive_bisection(self, cov: np.ndarray, sorted_indices: list[int]) -> np.ndarray:
        """Perform recursive bisection to compute unconstrained HRP weights. Fail-closed on degenerate cluster variance."""
        weights = np.ones(len(sorted_indices), dtype=np.float64)
        cluster_list = [sorted_indices]

        while len(cluster_list) > 0:
            next_clusters = []
            for cluster in cluster_list:
                if len(cluster) > 1:
                    mid = len(cluster) // 2
                    c1 = cluster[:mid]
                    c2 = cluster[mid:]

                    v1 = self._get_cluster_variance(cov, c1)
                    v2 = self._get_cluster_variance(cov, c2)

                    if v1 + v2 <= EPSILON_CLUSTER_VARIANCE or not (np.isfinite(v1) and np.isfinite(v2)):
                        raise DataContractError(
                            f"Degenerate or near-zero cluster variance encountered in HRP recursive bisection (V1={v1}, V2={v2}). Fail closed."
                        )

                    alpha1 = 1.0 - (v1 / (v1 + v2))
                    alpha2 = 1.0 - alpha1

                    weights[c1] *= alpha1
                    weights[c2] *= alpha2

                    next_clusters.append(c1)
                    next_clusters.append(c2)
            cluster_list = next_clusters

        # Normalize weights to sum to 1.0
        w_sum = np.sum(weights)
        if w_sum > 0:
            weights = weights / w_sum
        return weights

    def _get_cluster_variance(self, cov: np.ndarray, cluster_indices: list[int]) -> float:
        """Compute variance of a cluster under inverse-variance weighting."""
        sub_cov = cov[np.ix_(cluster_indices, cluster_indices)]
        diag_sub = np.diag(sub_cov)
        if np.any(diag_sub <= EPSILON_VARIANCE_ADMISSIBILITY) or np.any(~np.isfinite(diag_sub)):
            raise DataContractError(
                f"Zero or near-zero variance (<= {EPSILON_VARIANCE_ADMISSIBILITY}) in sub-cluster covariance diagonal. Fail closed."
            )
        inv_diag = 1.0 / diag_sub
        w_sub = inv_diag / np.sum(inv_diag)
        var = float(w_sub @ sub_cov @ w_sub)
        if var <= EPSILON_CLUSTER_VARIANCE or not np.isfinite(var):
            raise DataContractError(
                f"Calculated cluster variance ({var}) is non-positive or non-finite. Fail closed."
            )
        return var

    def _apply_weight_caps(
        self,
        weights: np.ndarray,
        budget: float,
        min_weight: float,
        max_weight: float,
    ) -> np.ndarray:
        """Scale by budget and redistribute excess weight exceeding max_weight deterministically."""
        w = weights * budget
        for _ in range(50):
            excess = 0.0
            excess_indices = []
            free_indices = []
            for i, val in enumerate(w):
                if val > max_weight + 1e-8:
                    excess += val - max_weight
                    w[i] = max_weight
                    excess_indices.append(i)
                else:
                    free_indices.append(i)

            if excess <= 1e-8 or len(free_indices) == 0:
                break

            free_sum = np.sum(w[free_indices])
            if free_sum > 1e-8:
                for idx in free_indices:
                    w[idx] += excess * (w[idx] / free_sum)
            else:
                share = excess / len(free_indices)
                for idx in free_indices:
                    w[idx] += share

        return np.clip(w, min_weight, max_weight)


class EqualRiskContributionAllocator:
    """Equal Risk Contribution (ERC / Risk Parity) Allocator (Maillard et al. 2010).

    Classification of Mathematical Steps:
    1. Canonical ERC Mathematical Formulation:
       - Marginal Risk Contribution: RC_i = w_i * (Sigma w)_i / port_vol
       - Target Risk Parity Condition: RC_i = RC_j = port_vol / N for all i, j in Risky Assets
    2. Numerical Optimization Method:
       - Constrained nonlinear numerical optimization using scipy.optimize.minimize(method='SLSQP')
       - Loss function: sum_i (RC_i - port_vol / N)^2
    3. Risky Asset Scope & Cash Separation:
       - Risk parity budget applies exclusively to Risky Assets in panel.symbols
       - Cash is excluded from covariance matrix and risk contribution accounting
    4. Mathematical Acceptance Separation:
       - Separates solver convergence (res.success) from mathematical RC deviation acceptance (max_rel_rc_dev <= threshold)
    """

    def __init__(
        self,
        covariance_estimator: Optional[CovarianceEstimator] = None,
        convergence_tolerance: float = ERC_SOLVER_FTOL,
        max_iterations: int = ERC_MAX_ITERATIONS,
        max_relative_rc_deviation: float = ERC_DEFAULT_MAX_RELATIVE_RC_DEVIATION,
    ) -> None:
        self.covariance_estimator = covariance_estimator or LedoitWolfShrinkageCovarianceEstimator()
        self.convergence_tolerance = convergence_tolerance
        self.max_iterations = max_iterations
        self.max_relative_rc_deviation = max_relative_rc_deviation

    @property
    def allocator_name(self) -> str:
        return "EQUAL_RISK_CONTRIBUTION"

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        """Compute ERC candidate weights solving equal risk contribution optimization."""
        n_assets = len(panel.symbols)
        if n_assets == 0:
            raise DataContractError("Cannot compute ERC allocation on empty universe.")

        # Single asset edge case
        if n_assets == 1:
            sym = panel.symbols[0]
            max_w = min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_weight)
            max_w = min(max_w, constraints.max_gross_leverage)
            cash_w = Decimal("1.0") - max_w
            return AllocationCandidate(
                candidate_id=f"CAND_ERC_{panel.universe_id}",
                allocator_name=self.allocator_name,
                asset_weights={sym: max_w},
                cash_weight=cash_w,
                in_sample_metrics={"expected_return": Decimal("0.0"), "variance": Decimal("0.0")},
            )

        # 1. Estimate Covariance Matrix (Risky Assets Only)
        cov = self.covariance_estimator.estimate_covariance(panel)
        if cov.shape != (n_assets, n_assets):
            raise DataContractError(f"Covariance shape mismatch: expected ({n_assets}, {n_assets}), got {cov.shape}")

        diag_var = np.diag(cov)
        if np.any(diag_var <= EPSILON_VARIANCE_ADMISSIBILITY) or np.any(~np.isfinite(diag_var)):
            raise DataContractError(
                f"Non-finite or near-zero variance (<= {EPSILON_VARIANCE_ADMISSIBILITY}) in covariance diagonal. Fail closed."
            )

        budget_risky = float(min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_gross_leverage))
        max_w_fl = float(constraints.max_weight)
        min_w_fl = float(constraints.min_weight)

        # 2. Objective Function: Constrained nonlinear sum-of-squares risk parity objective
        def _objective(w_vec: np.ndarray) -> float:
            sigma_w = cov @ w_vec
            port_var = float(w_vec @ sigma_w)
            if port_var <= 1e-16:
                return 1e10
            port_vol = math.sqrt(port_var)
            # Marginal risk contribution: RC_i = w_i * (Sigma w)_i / port_vol
            rc = (w_vec * sigma_w) / port_vol
            target_rc = port_vol / n_assets
            return float(np.sum((rc - target_rc) ** 2))

        # Initial guess: Inverse Volatility proportional weights scaled by budget
        inv_vols = 1.0 / np.sqrt(diag_var)
        w0 = (inv_vols / np.sum(inv_vols)) * budget_risky

        bounds = [(min_w_fl, max_w_fl) for _ in range(n_assets)]
        budget_constraint = {
            "type": "eq",
            "fun": lambda w_vec: float(np.sum(w_vec) - budget_risky),
        }

        # 3. Solve Constrained Nonlinear Optimization with SLSQP
        res = sco.minimize(
            _objective,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=[budget_constraint],
            options={
                "ftol": self.convergence_tolerance,
                "maxiter": self.max_iterations,
                "disp": False,
            },
        )

        if not res.success:
            raise DataContractError(
                f"Equal Risk Contribution solver failed to converge: {res.message}. Fail-closed."
            )

        optimized_weights = res.x
        if np.any(~np.isfinite(optimized_weights)):
            raise DataContractError("ERC solver returned non-finite weights.")

        # 4. Compute Marginal Risk Contributions and Acceptance Metrics
        sigma_w = cov @ optimized_weights
        port_var = float(optimized_weights @ sigma_w)
        if port_var <= 1e-16 or not np.isfinite(port_var):
            raise DataContractError(f"Optimized portfolio variance ({port_var}) is non-positive or non-finite. Fail closed.")
        port_vol = math.sqrt(port_var)
        rc = (optimized_weights * sigma_w) / port_vol
        mean_rc = float(np.mean(rc))
        max_rel_rc_dev = float(np.max(np.abs(rc - mean_rc)) / mean_rc) if mean_rc > 0 else 0.0

        # Check if box constraints (min_weight / max_weight) are active/binding
        is_boundary_active = any(
            (w >= max_w_fl - 1e-6) or (w <= min_w_fl + 1e-6)
            for w in optimized_weights
        )

        # Mathematical Acceptance Verification:
        # For interior (unconstrained) solutions, strict RC equality (within max_relative_rc_deviation) is required.
        # For boundary-active solutions, solver convergence to constrained minimum is required.
        if is_boundary_active:
            is_erc_accepted = bool(res.success)
        else:
            is_erc_accepted = bool(res.success and (max_rel_rc_dev <= self.max_relative_rc_deviation))

        if not is_erc_accepted:
            raise DataContractError(
                f"Equal Risk Contribution acceptance criteria failed: max relative RC deviation ({max_rel_rc_dev:.6f}) exceeds threshold ({self.max_relative_rc_deviation}). Solver status: {res.message}."
            )

        # Convert to Decimal dict
        out_weights: dict[str, Decimal] = {}
        total_risky_dec = Decimal("0.0")
        for i, sym in enumerate(panel.symbols):
            w_dec = Decimal(str(round(optimized_weights[i], 8)))
            out_weights[sym] = w_dec
            total_risky_dec += w_dec

        cash_w_dec = max(Decimal("0.0"), Decimal("1.0") - total_risky_dec)

        return AllocationCandidate(
            candidate_id=f"CAND_ERC_{panel.universe_id}",
            allocator_name=self.allocator_name,
            asset_weights=out_weights,
            cash_weight=cash_w_dec,
            in_sample_metrics={
                "variance": Decimal(str(round(port_var, 8))),
                "solver_converged": Decimal("1.0") if res.success else Decimal("0.0"),
                "solver_objective": Decimal(str(round(float(res.fun), 10))),
                "solver_iterations": Decimal(str(int(res.nit))),
                "rc_max_relative_deviation": Decimal(str(round(max_rel_rc_dev, 6))),
                "is_boundary_active": Decimal("1.0") if is_boundary_active else Decimal("0.0"),
                "erc_acceptance_status": Decimal("1.0") if is_erc_accepted else Decimal("0.0"),
            },
        )
