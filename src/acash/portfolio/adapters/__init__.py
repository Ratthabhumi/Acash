"""Level 3 Optional Portfolio Optimizer Adapters for Phase 8.

Provides decoupled adapter interfaces for optional third-party optimization engines
(skfolio, CVXPY) with strict lazy imports and fail-closed contracts.
"""

from acash.portfolio.adapters.cvxpy_adapter import CvxpyMeanRiskAdapter
from acash.portfolio.adapters.skfolio_adapter import SkfolioHRPAdapter, SkfolioMeanRiskAdapter

__all__ = [
    "SkfolioHRPAdapter",
    "SkfolioMeanRiskAdapter",
    "CvxpyMeanRiskAdapter",
]
