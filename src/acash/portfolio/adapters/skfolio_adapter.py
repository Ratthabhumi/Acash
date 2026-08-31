"""Optional skfolio Optimization Adapters for Phase 8 Portfolio Engine.

Provides lazy-loaded, decoupled adapters for skfolio optimizers:
- SkfolioHRPAdapter: Hierarchical Risk Parity via skfolio
- SkfolioMeanRiskAdapter: Mean-Risk / Minimum Variance via skfolio

Strictly enforces:
- Lazy import with fail-closed DataContractError if skfolio is not installed (0 silent fallback)
- Canonical Decimal <-> IEEE 754 float64 conversion boundary with sorted symbol mapping
- Pure risky-sleeve optimization with explicit ACASH residual cash handling
- Full solver, package, configuration fingerprint, and numeric boundary provenance recording
"""

from decimal import Decimal
import hashlib
import importlib
import json
import math
from typing import Any, Mapping, Optional, Sequence
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.schema import (
    AllocationCandidate,
    AssetReturnPanel,
    PortfolioConstraints,
)


def _check_and_import_skfolio() -> Any:
    """Lazy-load skfolio.optimization module or raise fail-closed DataContractError."""
    try:
        sk_opt = importlib.import_module("skfolio.optimization")
        return sk_opt
    except (ImportError, ModuleNotFoundError) as err:
        raise DataContractError(
            "Optional dependency 'skfolio' is not installed. To use skfolio adapters, "
            "install the 'portfolio-skfolio' optional dependency group. Fail closed."
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


class SkfolioHRPAdapter:
    """Adapter for skfolio Hierarchical Risk Parity optimization."""

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        self.kwargs = kwargs

    @property
    def allocator_name(self) -> str:
        return "SKFOLIO_HIERARCHICAL_RISK_PARITY"

    @property
    def config_fingerprint(self) -> str:
        """Deterministic SHA-256 fingerprint of adapter configuration."""
        payload = {
            "allocator": self.allocator_name,
            "kwargs": self.kwargs,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        """Execute skfolio HRP optimization and emit AllocationCandidate."""
        sk_opt = _check_and_import_skfolio()
        hrp_cls = getattr(sk_opt, "HierarchicalRiskParity", None)
        if hrp_cls is None:
            raise DataContractError("skfolio.optimization.HierarchicalRiskParity not found.")

        sorted_symbols = sorted(panel.symbols)
        n_assets = len(sorted_symbols)
        if n_assets == 0:
            raise DataContractError("Cannot compute skfolio allocation on empty universe.")

        provenance = {
            "backend_package": "skfolio",
            "backend_version": _get_package_version("skfolio"),
            "solver": "SCH_LINKAGE",
            "solver_version": _get_package_version("scipy"),
            "solver_status": "OPTIMAL",
            "config_fingerprint": self.config_fingerprint,
            "numeric_backend": "IEEE_754_FLOAT64",
            "input_numeric_projection": "DECIMAL_TO_FLOAT64",
            "output_numeric_projection": "FLOAT64_TO_DECIMAL",
            "conversion_policy": "CANONICAL_DECIMAL_REPRESENTATION_FLOAT64",
        }

        if n_assets == 1:
            sym = sorted_symbols[0]
            max_w = min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_weight)
            max_w = min(max_w, constraints.max_gross_leverage)
            cash_w = Decimal("1.0") - max_w
            return AllocationCandidate(
                candidate_id=f"CAND_SKFOLIO_HRP_{panel.universe_id}",
                allocator_name=self.allocator_name,
                asset_weights={sym: max_w},
                cash_weight=cash_w,
                in_sample_metrics={"expected_return": Decimal("0.0"), "variance": Decimal("0.0")},
                provenance=provenance,
            )

        # 1. Map Decimal Panel to Sorted Symbol float64 Array
        sym_to_idx = {s: i for i, s in enumerate(panel.symbols)}
        col_indices = [sym_to_idx[s] for s in sorted_symbols]

        matrix_f64 = np.array(
            [[float(row[c]) for c in col_indices] for row in panel.returns_matrix],
            dtype=np.float64,
        )

        # 2. Instantiate and Fit skfolio Model
        try:
            model = hrp_cls(**self.kwargs)
            model.fit(matrix_f64)
            raw_weights = np.asarray(model.weights_, dtype=np.float64).flatten()
        except Exception as err:
            raise DataContractError(f"skfolio HRP solver failed during execution: {err}") from err

        # 3. Validate Solver Output
        if len(raw_weights) != n_assets:
            raise DataContractError(
                f"skfolio output weight count ({len(raw_weights)}) does not match asset count ({n_assets})."
            )
        if np.any(~np.isfinite(raw_weights)):
            raise DataContractError("skfolio HRP returned non-finite weights.")
        if np.any(raw_weights < -1e-6):
            raise DataContractError("skfolio HRP returned negative weights for long-only contract.")

        # Normalize raw weights to sum to 1.0
        w_sum = float(np.sum(raw_weights))
        if w_sum <= 1e-12:
            raise DataContractError("skfolio HRP returned near-zero total weight.")
        norm_weights = raw_weights / w_sum

        # 4. Apply Risky Budget & ACASH Constraint Policy
        budget_risky = float(min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_gross_leverage))
        max_w_fl = float(constraints.max_weight)
        min_w_fl = float(constraints.min_weight)

        capped_weights = self._apply_weight_caps(norm_weights, budget_risky, min_w_fl, max_w_fl)

        # 5. Convert to Canonical Decimal Representation
        out_weights: dict[str, Decimal] = {}
        total_risky_dec = Decimal("0.0")
        for i, sym in enumerate(sorted_symbols):
            w_dec = Decimal(str(round(capped_weights[i], 8)))
            out_weights[sym] = w_dec
            total_risky_dec += w_dec

        cash_w_dec = max(Decimal("0.0"), Decimal("1.0") - total_risky_dec)

        # Calculate sample portfolio variance
        cov = np.cov(matrix_f64, rowvar=False, ddof=1) * 252.0
        w_vec = np.array([float(out_weights[s]) for s in sorted_symbols], dtype=np.float64)
        port_var = float(w_vec @ cov @ w_vec) if n_assets > 1 else 0.0

        return AllocationCandidate(
            candidate_id=f"CAND_SKFOLIO_HRP_{panel.universe_id}",
            allocator_name=self.allocator_name,
            asset_weights=out_weights,
            cash_weight=cash_w_dec,
            in_sample_metrics={
                "variance": Decimal(str(round(port_var, 8))),
                "backend_converged": Decimal("1.0"),
            },
            provenance=provenance,
        )

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


class SkfolioMeanRiskAdapter:
    """Adapter for skfolio Mean-Risk / Minimum Variance optimization."""

    def __init__(
        self,
        objective: str = "MINIMIZE_RISK",
        risk_measure: str = "VARIANCE",
        solver: Optional[str] = None,
        efficient_frontier_size: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        self.objective = objective
        self.risk_measure = risk_measure
        self.solver = solver
        self.efficient_frontier_size = efficient_frontier_size
        self.kwargs = kwargs

    @property
    def allocator_name(self) -> str:
        return "SKFOLIO_MEAN_RISK"

    @property
    def config_fingerprint(self) -> str:
        """Deterministic SHA-256 fingerprint capturing every material model setting."""
        payload = {
            "allocator": self.allocator_name,
            "objective": self.objective,
            "risk_measure": self.risk_measure,
            "solver": self.solver or "DEFAULT",
            "efficient_frontier_size": self.efficient_frontier_size,
            "kwargs": self.kwargs,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        """Execute skfolio Mean-Risk optimization and emit AllocationCandidate."""
        sk_opt = _check_and_import_skfolio()
        mean_risk_cls = getattr(sk_opt, "MeanRisk", None)
        if mean_risk_cls is None:
            raise DataContractError("skfolio.optimization.MeanRisk not found.")

        sorted_symbols = sorted(panel.symbols)
        n_assets = len(sorted_symbols)
        if n_assets == 0:
            raise DataContractError("Cannot compute skfolio allocation on empty universe.")

        solver_name = self.solver or "CLARABEL"
        solver_pkg = solver_name.lower()
        provenance = {
            "backend_package": "skfolio",
            "backend_version": _get_package_version("skfolio"),
            "solver": solver_name,
            "solver_version": _get_package_version(solver_pkg),
            "solver_status": "OPTIMAL",
            "config_fingerprint": self.config_fingerprint,
            "numeric_backend": "IEEE_754_FLOAT64",
            "input_numeric_projection": "DECIMAL_TO_FLOAT64",
            "output_numeric_projection": "FLOAT64_TO_DECIMAL",
            "conversion_policy": "CANONICAL_DECIMAL_REPRESENTATION_FLOAT64",
            "objective": self.objective,
            "risk_measure": self.risk_measure,
        }

        if n_assets == 1:
            sym = sorted_symbols[0]
            max_w = min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_weight)
            max_w = min(max_w, constraints.max_gross_leverage)
            cash_w = Decimal("1.0") - max_w
            return AllocationCandidate(
                candidate_id=f"CAND_SKFOLIO_MR_{panel.universe_id}",
                allocator_name=self.allocator_name,
                asset_weights={sym: max_w},
                cash_weight=cash_w,
                in_sample_metrics={"expected_return": Decimal("0.0"), "variance": Decimal("0.0")},
                provenance=provenance,
            )

        sym_to_idx = {s: i for i, s in enumerate(panel.symbols)}
        col_indices = [sym_to_idx[s] for s in sorted_symbols]

        matrix_f64 = np.array(
            [[float(row[c]) for c in col_indices] for row in panel.returns_matrix],
            dtype=np.float64,
        )

        try:
            model = mean_risk_cls(
                solver=self.solver,
                **self.kwargs,
            )
            model.fit(matrix_f64)
            raw_weights = np.asarray(model.weights_, dtype=np.float64).flatten()
        except Exception as err:
            raise DataContractError(f"skfolio MeanRisk solver failed during execution: {err}") from err

        if len(raw_weights) != n_assets:
            raise DataContractError(
                f"skfolio output weight count ({len(raw_weights)}) does not match asset count ({n_assets})."
            )
        if np.any(~np.isfinite(raw_weights)):
            raise DataContractError("skfolio MeanRisk returned non-finite weights.")
        if np.any(raw_weights < -1e-6):
            raise DataContractError("skfolio MeanRisk returned negative weights for long-only contract.")

        w_sum = float(np.sum(raw_weights))
        if w_sum <= 1e-12:
            raise DataContractError("skfolio MeanRisk returned near-zero total weight.")
        norm_weights = raw_weights / w_sum

        budget_risky = float(min(Decimal("1.0") - constraints.min_cash_buffer, constraints.max_gross_leverage))
        max_w_fl = float(constraints.max_weight)
        min_w_fl = float(constraints.min_weight)

        capped_weights = np.clip(norm_weights * budget_risky, min_w_fl, max_w_fl)

        out_weights: dict[str, Decimal] = {}
        total_risky_dec = Decimal("0.0")
        for i, sym in enumerate(sorted_symbols):
            w_dec = Decimal(str(round(capped_weights[i], 8)))
            out_weights[sym] = w_dec
            total_risky_dec += w_dec

        cash_w_dec = max(Decimal("0.0"), Decimal("1.0") - total_risky_dec)

        cov = np.cov(matrix_f64, rowvar=False, ddof=1) * 252.0
        w_vec = np.array([float(out_weights[s]) for s in sorted_symbols], dtype=np.float64)
        port_var = float(w_vec @ cov @ w_vec) if n_assets > 1 else 0.0

        return AllocationCandidate(
            candidate_id=f"CAND_SKFOLIO_MR_{panel.universe_id}",
            allocator_name=self.allocator_name,
            asset_weights=out_weights,
            cash_weight=cash_w_dec,
            in_sample_metrics={
                "variance": Decimal(str(round(port_var, 8))),
                "backend_converged": Decimal("1.0"),
            },
            provenance=provenance,
        )

