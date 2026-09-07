"""Phase 14 AI Research Intelligence Enums & Epistemic Taxonomies.

Establishes:
1. Tri-axial source classification (SourceType, VerificationStatus, EvidenceRole)
2. Epistemic evidence classification (EvidenceClassification)
3. Research Candidate lifecycle and family taxonomies (CandidateStatus, CandidateFamily)

All enums inherit from str to support strict JSON serialization and deterministic hashing.
"""

from enum import Enum


class SourceType(str, Enum):
    """Origin media, platform, or format of external research source material."""

    ACADEMIC = "ACADEMIC"
    BLOG = "BLOG"
    GITHUB = "GITHUB"
    VENDOR = "VENDOR"
    COURSE = "COURSE"
    SOCIAL = "SOCIAL"
    DATASET = "DATASET"
    OTHER = "OTHER"


class VerificationStatus(str, Enum):
    """Empirical verification state of an external research claim."""

    UNVERIFIED = "UNVERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    REPRODUCED = "REPRODUCED"
    INDEPENDENTLY_VALIDATED = "INDEPENDENTLY_VALIDATED"


class EvidenceRole(str, Enum):
    """Epistemic function that a source serves in the ACASH quantitative pipeline."""

    BACKGROUND = "BACKGROUND"
    HYPOTHESIS_SOURCE = "HYPOTHESIS_SOURCE"
    METHOD_REFERENCE = "METHOD_REFERENCE"
    EMPIRICAL_EVIDENCE = "EMPIRICAL_EVIDENCE"


class EvidenceClassification(str, Enum):
    """Strict epistemic classification applied to claims, propositions, and metrics."""

    VERIFIED = "VERIFIED"
    REPORTED = "REPORTED"
    SELF_REPORTED = "SELF_REPORTED"
    INFERRED = "INFERRED"
    NOT_PROVEN = "NOT_PROVEN"
    BLOCKED = "BLOCKED"


class CandidateStatus(str, Enum):
    """Lifecycle state of an exploratory research candidate.

    IMPORTANT:
    - UNVALIDATED_PROPOSAL is the mandatory initial state for any AI proposal.
    - READY_FOR_HUMAN_R1_DESIGN_REVIEW does NOT authorize R1.
    - Candidates hold zero trading, backtest, or hypothesis registration authority.
    """

    UNVALIDATED_PROPOSAL = "UNVALIDATED_PROPOSAL"
    NEEDS_MORE_RESEARCH = "NEEDS_MORE_RESEARCH"
    REJECTED = "REJECTED"
    READY_FOR_HUMAN_R1_DESIGN_REVIEW = "READY_FOR_HUMAN_R1_DESIGN_REVIEW"


class CandidateFamily(str, Enum):
    """Taxonomy of quantitative trading and alpha research candidate families."""

    SESSION_EVENT_MOMENTUM = "SESSION_EVENT_MOMENTUM"
    TIME_SERIES_MOMENTUM = "TIME_SERIES_MOMENTUM"
    CROSS_SECTIONAL_MOMENTUM = "CROSS_SECTIONAL_MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    VOLATILITY_BREAKOUT = "VOLATILITY_BREAKOUT"
    ORDER_FLOW_IMBALANCE = "ORDER_FLOW_IMBALANCE"
    STATISTICAL_ARBITRAGE = "STATISTICAL_ARBITRAGE"
    MACRO_REGIME = "MACRO_REGIME"
    OTHER = "OTHER"
