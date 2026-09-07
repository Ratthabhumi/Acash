"""ACASH Phase 14 AI Quantitative Research & Evidence Layer (Slice 1 Foundation).

Exposes:
- Tri-Axial Epistemic Taxonomy & Enums
- Core Schemas: ResearchSourceMetadata, ResearchCandidate, AIHypothesisProposal, AIFeatureProposal, ResearchManifest
- Fail-Closed Domain Exceptions
- Canonical Quarantine Verification Helpers

INVARIANTS:
- All AI proposals are permanently UNVALIDATED_PROPOSAL.
- Model and prompt metadata are purely descriptive provenance with ZERO governance authority.
- No direct hypothesis registration, backtest execution, or trading authority.
"""

from acash.research.ai.enums import (
    CandidateFamily,
    CandidateStatus,
    EvidenceClassification,
    EvidenceRole,
    SourceType,
    VerificationStatus,
)
from acash.research.ai.exceptions import (
    InvalidEvidenceRoleError,
    MissingProvenanceError,
    QuarantineContaminationError,
    ResearchAiError,
    UnauthorizedProposalTransitionError,
)
from acash.research.ai.quarantine import (
    assert_research_candidate_quarantine_clean,
    is_candidate_window_clean,
)
from acash.research.ai.schema import (
    AIFeatureProposal,
    AIHypothesisProposal,
    ResearchCandidate,
    ResearchManifest,
    ResearchSourceMetadata,
)

__all__ = [
    # Enums & Taxonomies
    "SourceType",
    "VerificationStatus",
    "EvidenceRole",
    "EvidenceClassification",
    "CandidateStatus",
    "CandidateFamily",
    # Exceptions
    "ResearchAiError",
    "QuarantineContaminationError",
    "InvalidEvidenceRoleError",
    "MissingProvenanceError",
    "UnauthorizedProposalTransitionError",
    # Schemas
    "ResearchSourceMetadata",
    "ResearchCandidate",
    "AIHypothesisProposal",
    "AIFeatureProposal",
    "ResearchManifest",
    # Quarantine Integration
    "assert_research_candidate_quarantine_clean",
    "is_candidate_window_clean",
]
