"""Level 1 Baseline Allocators for Phase 8 Portfolio Engine.

Provides closed-form, transparent mathematical implementations of:
- 100% Cash Allocator (CASH)
- Equal Weight Allocator (1/N)
- Inverse Volatility Allocator (1/σ)
"""

from decimal import Decimal
from typing import Mapping, Protocol
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.schema import (
    AllocationCandidate,
    AssetReturnPanel,
    PortfolioConstraints,
)


class PortfolioAllocator(Protocol):
    """Protocol defining the allocator interface for generating candidate weight proposals."""

    @property
    def allocator_name(self) -> str: ...

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        """Compute candidate weight proposal in Decimal space. Fail-closed on invalid state."""
        ...


class CashAllocator:
    """Allocates 100% to Cash with zero risky asset exposure."""

    @property
    def allocator_name(self) -> str:
        return "CASH"

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        weights = {s: Decimal("0.0") for s in panel.symbols}
        return AllocationCandidate(
            candidate_id=f"CAND_CASH_{panel.universe_id}",
            allocator_name=self.allocator_name,
            asset_weights=weights,
            cash_weight=Decimal("1.0"),
            in_sample_metrics={"expected_return": Decimal("0.0"), "variance": Decimal("0.0")},
        )


class EqualWeightAllocator:
    """Allocates available non-cash capital (1.0 - min_cash_buffer) equally across N assets (1/N)."""

    @property
    def allocator_name(self) -> str:
        return "EQUAL_WEIGHT"

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        n = panel.N
        if n < 1:
            raise DataContractError("EqualWeightAllocator requires at least 1 asset in panel.")

        available_capital = max(Decimal("0.0"), Decimal("1.0") - constraints.min_cash_buffer)
        equal_weight = available_capital / Decimal(str(n))

        # Check single asset maximum weight constraint
        capped_weight = min(equal_weight, constraints.max_weight)

        weights = {s: capped_weight for s in panel.symbols}
        actual_risky_sum = sum(weights.values(), Decimal("0.0"))
        derived_cash = max(constraints.min_cash_buffer, Decimal("1.0") - actual_risky_sum)

        return AllocationCandidate(
            candidate_id=f"CAND_EW_{panel.universe_id}",
            allocator_name=self.allocator_name,
            asset_weights=weights,
            cash_weight=derived_cash,
            in_sample_metrics={"assets_count": Decimal(str(n))},
        )


class InverseVolatilityAllocator:
    """Allocates non-cash capital inversely proportional to historical asset standard deviation (1/σ)."""

    @property
    def allocator_name(self) -> str:
        return "INVERSE_VOL"

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        if panel.T < 2:
            raise DataContractError("InverseVolatilityAllocator requires at least T >= 2 observations.")

        matrix_f64 = np.array(
            [[float(val) for val in row] for row in panel.returns_matrix],
            dtype=np.float64,
        )

        stds = np.std(matrix_f64, axis=0, ddof=1)
        inv_vols: list[Decimal] = []

        for idx, std_val in enumerate(stds):
            if std_val <= 1e-12 or not np.isfinite(std_val):
                raise DataContractError(
                    f"Zero or invalid volatility detected for asset {panel.symbols[idx]} (std={std_val}). Fail-closed."
                )
            inv_vols.append(Decimal("1.0") / Decimal(str(std_val)))

        sum_inv_vol = sum(inv_vols, Decimal("0.0"))
        available_capital = max(Decimal("0.0"), Decimal("1.0") - constraints.min_cash_buffer)

        weights: dict[str, Decimal] = {}
        for idx, symbol in enumerate(panel.symbols):
            raw_w = (inv_vols[idx] / sum_inv_vol) * available_capital
            capped_w = min(raw_w, constraints.max_weight)
            weights[symbol] = capped_w

        actual_risky_sum = sum(weights.values(), Decimal("0.0"))
        derived_cash = max(constraints.min_cash_buffer, Decimal("1.0") - actual_risky_sum)

        return AllocationCandidate(
            candidate_id=f"CAND_INVOL_{panel.universe_id}",
            allocator_name=self.allocator_name,
            asset_weights=weights,
            cash_weight=derived_cash,
            in_sample_metrics={"sum_inv_vol": sum_inv_vol},
        )
