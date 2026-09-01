"""ACASH Phase 8 Portfolio Engine.

Public API exports:
- Domain Models & DTOs (PortfolioUniverse, AssetReturnPanel, PortfolioConstraints,
  RiskSnapshot, AllocationCandidate, AllocationEvaluation, AllocationDecision, RebalancePlan)
- Estimators (HistoricalSampleMeanEstimator, SampleCovarianceEstimator, LedoitWolfShrinkageCovarianceEstimator)
- Level 1 Baseline Allocators (CashAllocator, EqualWeightAllocator, InverseVolatilityAllocator)
- Allocator Protocol (PortfolioAllocator)
- Digest utilities (recompute_digest)
"""

from acash.portfolio.baselines import (
    CashAllocator,
    EqualWeightAllocator,
    InverseVolatilityAllocator,
    PortfolioAllocator,
)
from acash.portfolio.estimators import (
    CovarianceEstimator,
    ExpectedReturnEstimator,
    HistoricalSampleMeanEstimator,
    LedoitWolfShrinkageCovarianceEstimator,
    SampleCovarianceEstimator,
)
from acash.portfolio.evaluation import (
    AllocationEvaluator,
    EvaluationConfig,
    FrictionParameters,
)
from acash.portfolio.schema import (
    EPSILON_PSD,
    EPSILON_RANK_TIE,
    EPSILON_WEIGHT_SUM,
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

from acash.portfolio.tournament import (
    AllocationTournamentRunner,
    AllocatorSummary,
    SplitRecord,
    TournamentConfig,
    TournamentReport,
    TournamentSplitConfig,
    slice_panel,
)

__all__ = [
    "AllocationCandidate",
    "AllocationDecision",
    "AllocationEvaluation",
    "AllocationEvaluator",
    "AllocationTournamentRunner",
    "AllocatorSummary",
    "AssetReturnPanel",
    "CashAllocator",
    "CovarianceEstimator",
    "EPSILON_PSD",
    "EPSILON_RANK_TIE",
    "EPSILON_WEIGHT_SUM",
    "EqualWeightAllocator",
    "EvaluationConfig",
    "ExpectedReturnEstimator",
    "FrictionParameters",
    "HistoricalSampleMeanEstimator",
    "InverseVolatilityAllocator",
    "LedoitWolfShrinkageCovarianceEstimator",
    "PortfolioAllocator",
    "PortfolioConstraints",
    "PortfolioUniverse",
    "RebalancePlan",
    "RiskSnapshot",
    "SampleCovarianceEstimator",
    "SplitRecord",
    "TournamentConfig",
    "TournamentReport",
    "TournamentSplitConfig",
    "recompute_digest",
    "slice_panel",
]
