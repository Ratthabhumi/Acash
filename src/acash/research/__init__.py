"""Alpha Research & Hypothesis Engine for ACASH (Phase 4).

Provides:
- Formal Hypothesis Specification Models:
  - ExpectedDirection, InvalidationCriteria, HypothesisSpecification
  - HacBandwidthMethod, HacInferencePolicy
  - CostModelConfig, SplitPolicy, OosExposureState
  - ResearchSearchRecord, ResearchManifest, EvaluationResult
- Forward Outcome & Purging Engine:
  - compute_discrete_forward_returns
  - partition_dataset_with_embargo
- Statistical & HAC Inference:
  - compute_ols_beta_and_hac
  - calculate_pearson_ic
  - calculate_spearman_rank_ic
  - calculate_autocorrelation
  - calculate_3tier_friction_waterfall
  - evaluate_hypothesis_relationship
- Research Baseline Strategies:
  - MicrostructureImbalanceStrategy
  - SessionVwapMeanReversionStrategy
  - MultiHorizonMomentumStrategy
- Pipeline & Manifest Engine:
  - AlphaResearchPipeline
  - ResearchManifestEngine
  - calculate_hypothesis_spec_sha256
  - calculate_research_search_record_sha256
"""

from acash.research.evaluation import (
    calculate_3tier_friction_waterfall,
    calculate_autocorrelation,
    calculate_pearson_ic,
    calculate_spearman_rank_ic,
    compute_ols_beta_and_hac,
    determine_hac_bandwidth,
    evaluate_hypothesis_relationship,
)
from acash.research.manifest import (
    ResearchGovernanceLedger,
    ResearchManifestEngine,
    calculate_hypothesis_spec_sha256,
    calculate_research_search_record_sha256,
)

from acash.research.outcomes import (
    compute_discrete_forward_returns,
    partition_dataset_with_embargo,
)
from acash.research.pipeline import AlphaResearchPipeline
from acash.research.schema import (
    CANONICAL_FORWARD_OUTCOMES_SCHEMA,
    CANONICAL_HYPOTHESIS_EVALUATION_SCHEMA,
    CostModelConfig,
    EvaluationResult,
    ExpectedDirection,
    HacBandwidthMethod,
    HacInferencePolicy,
    HypothesisSpecification,
    InvalidationCriteria,
    OosExposureState,
    ResearchManifest,
    ResearchSearchRecord,
    RobustnessCheckRecord,
    SplitPolicy,
)
from acash.research.strategies import (
    MicrostructureImbalanceStrategy,
    MultiHorizonMomentumStrategy,
    SessionVwapMeanReversionStrategy,
)

__all__ = [
    # Schemas & Models
    "CANONICAL_FORWARD_OUTCOMES_SCHEMA",
    "CANONICAL_HYPOTHESIS_EVALUATION_SCHEMA",
    "ExpectedDirection",
    "InvalidationCriteria",
    "HypothesisSpecification",
    "HacBandwidthMethod",
    "HacInferencePolicy",
    "CostModelConfig",
    "SplitPolicy",
    "OosExposureState",
    "ResearchSearchRecord",
    "RobustnessCheckRecord",
    "EvaluationResult",
    "ResearchManifest",
    # Outcomes & Purging
    "compute_discrete_forward_returns",
    "partition_dataset_with_embargo",
    # Statistical Evaluation & HAC
    "compute_ols_beta_and_hac",
    "determine_hac_bandwidth",
    "calculate_pearson_ic",
    "calculate_spearman_rank_ic",
    "calculate_autocorrelation",
    "calculate_3tier_friction_waterfall",
    "evaluate_hypothesis_relationship",
    # Baseline Strategies
    "MicrostructureImbalanceStrategy",
    "SessionVwapMeanReversionStrategy",
    "MultiHorizonMomentumStrategy",
    # Manifest & Pipeline
    "calculate_hypothesis_spec_sha256",
    "calculate_research_search_record_sha256",
    "ResearchGovernanceLedger",
    "ResearchManifestEngine",
    "AlphaResearchPipeline",
]

