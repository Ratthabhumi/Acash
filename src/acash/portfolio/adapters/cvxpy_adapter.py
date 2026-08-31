"""Optional CVXPY Optimization Adapters for Phase 8 Portfolio Engine.

Provides lazy-loaded, decoupled adapters for CVXPY convex quadratic/cone solvers:
- CvxpyMeanRiskAdapter: Minimum Variance / Mean-Risk Quadratic Optimization

Strictly enforces:
- Lazy import with fail-closed DataContractError if CVXPY is not installed
- Canonical Decimal <-> IEEE 754 float64 conversion boundary with sorted symbol mapping
- Pure risky-sleeve optimization with explicit ACASH residual cash handling
- Full solver, package, configuration fingerprint, and numeric boundary provenance recording
"""

from decimal import Decimal
import hashlib
import importlib
import json
from typing import Any, Mapping, Optional
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.estimators import CovarianceEstimator, LedoitWolfShrinkageCovarianceEstimator
from acash.portfolio.schema import (
    AllocationCandidate,
    AssetReturnPanel,
    PortfolioConstraints,
)


def _check_and_import_cvxpy() -> Any:
    """Lazy-load cvxpy module or raise fail-closed DataContractError."""
    try:
        cp = importlib.import_module("cvxpy")
        return cp
    except (ImportError, ModuleNotFoundError) as err:
        raise DataContractError(
            "Optional dependency 'cvxpy' is not installed. To use CVXPY adapters, "
            "install the 'portfolio-cvxpy' optional dependency group. Fail closed."
        ) from err


def _get_package_version(pkg_name: str) -> str:
    """Retrieve installed package version or return NOT_INSTALLED."""
    try:
        import importlib.metadata
        return importlib.metadata.version(pkg_name)
    except Exception:
        try:
            mod = importlib.import_module(pkg_name)
            return getattr(mod, "__version__", "UNKNOWN")
        except Exception:
            return "NOT_INSTALLED"


class CvxpyMeanRiskAdapter:
    """Adapter for CVXPY Quadratic Minimum Variance Optimization."""

    def __init__(
        self,
        covariance_estimator: Optional[CovarianceEstimator] = None,
        solver: Optional[str] = None,
        **solver_options: Any,
    ) -> None:
        self.covariance_estimator = covariance_estimator or LedoitWolfShrinkageCovarianceEstimator()
        self.solver = solver
        self.solver_options = solver_options

    @property
    def allocator_name(self) -> str:
        return "CVXPY_MINIMUM_VARIANCE"

    @property
    def config_fingerprint(self) -> str:
        """Deterministic SHA-256 fingerprint of adapter configuration."""
        payload = {
            "allocator": self.allocator_name,
            "solver": self.solver or "DEFAULT_QP",
            "covariance_estimator": self.covariance_estimator.__class__.__name__,
            "solver_options": self.solver_options,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        """Execute CVXPY Minimum Variance optimization and emit AllocationCandidate."""
        cp = _check_and_import_cvxpy()

        sorted_symbols = sorted(panel.symbols)
        n_assets = len(sorted_symbols)
        if n_assets == 0:
            raise DataContractError("Cannot compute CVXPY allocation on empty universe.")

        solver_used = self.solver or "CLARABEL"
        solver_pkg = solver_used.lower()
        provenance = {
            "backend_package": "cvxpy",
            "backend_version": _get_package_version("cvxpy"),
            "solver": solver_used,
            "solver_version": _get_package_version(solver_pkg),
            "solver_status": "PENDING",
            "config_fingerprint": self.config_fingerprint,
            "numeric_backend": "IEEE_754_FLOAT64",
            "input_numeric_projection": "DECIMAL_TO_FLOAT64",
            "output_numeric_projection": "FLOAT64_TO_DECIMAL",
            "conversion_policy": "CANONICAL_DECIMAL_REPRESENTATION_FLOAT64",
            "covariance_estimator": self.covariance_estimator.__class__.__name__,
        }

        if n_assets == 1:
            sym = sorted_symbols[0]
            max_w = min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_weight)
            max_w = min(max_w, constraints.max_gross_leverage)
            cash_w = Decimal("1.0") - max_w
            provenance["solver_status"] = "OPTIMAL"
            return AllocationCandidate(
                candidate_id=f"CAND_CVXPY_MINVAR_{panel.universe_id}",
                allocator_name=self.allocator_name,
                asset_weights={sym: max_w},
                cash_weight=cash_w,
                in_sample_metrics={"expected_return": Decimal("0.0"), "variance": Decimal("0.0")},
                provenance=provenance,
            )

        # 1. Estimate Covariance Matrix (Sorted Symbols)
        cov = self.covariance_estimator.estimate_covariance(panel)
        if cov.shape != (n_assets, n_assets):
            raise DataContractError(f"Covariance shape mismatch: expected ({n_assets}, {n_assets}), got {cov.shape}")

        budget_risky = float(min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_gross_leverage))
        max_w_fl = float(constraints.max_weight)
        min_w_fl = float(constraints.min_weight)

        # 2. Build CVXPY Quadratic Program
        w = cp.Variable(n_assets)
        port_var = cp.quad_form(w, cov)
        obj = cp.Minimize(port_var)

        constraints_list = [
            w >= min_w_fl,
            w <= max_w_fl,
            cp.sum(w) == budget_risky,
        ]

        prob = cp.Problem(obj, constraints_list)

        # 3. Solve CVXPY Problem
        try:
            solve_kwargs = dict(self.solver_options)
            if self.solver is not None:
                solve_kwargs["solver"] = self.solver
            prob.solve(**solve_kwargs)
        except Exception as err:
            raise DataContractError(f"CVXPY solver failed during execution: {err}") from err

        optimal_statuses = ("optimal", "optimal_inaccurate")
        if prob.status not in optimal_statuses:
            raise DataContractError(f"CVXPY solver ended with non-optimal status: '{prob.status}'. Fail closed.")

        if w.value is None:
            raise DataContractError("CVXPY solver returned None weight vector.")

        raw_weights = np.asarray(w.value, dtype=np.float64).flatten()

        # 4. Validate Solver Output
        if len(raw_weights) != n_assets:
            raise DataContractError(
                f"CVXPY output weight count ({len(raw_weights)}) does not match asset count ({n_assets})."
            )
        if np.any(~np.isfinite(raw_weights)):
            raise DataContractError("CVXPY returned non-finite weights.")
        if np.any(raw_weights < -1e-6):
            raise DataContractError("CVXPY returned negative weights for long-only contract.")

        # 5. Convert to Canonical Decimal Representation and Calculate Residual Cash
        out_weights: dict[str, Decimal] = {}
        total_risky_dec = Decimal("0.0")
        for i, sym in enumerate(sorted_symbols):
            w_dec = Decimal(str(round(float(raw_weights[i]), 8)))
            out_weights[sym] = w_dec
            total_risky_dec += w_dec

        cash_w_dec = max(Decimal("0.0"), Decimal("1.0") - total_risky_dec)

        # In-sample variance metric
        sol_var = float(prob.value) if prob.value is not None else 0.0
        provenance["solver_status"] = str(prob.status).upper()

        return AllocationCandidate(
            candidate_id=f"CAND_CVXPY_MINVAR_{panel.universe_id}",
            allocator_name=self.allocator_name,
            asset_weights=out_weights,
            cash_weight=cash_w_dec,
            in_sample_metrics={
                "variance": Decimal(str(round(sol_var, 8))),
                "backend_converged": Decimal("1.0"),
            },
            provenance=provenance,
        )
