"""Phase 14 AI Research Intelligence Schemas & Domain Contracts.

Strictly enforces:
1. Pydantic v2 validation with ConfigDict(frozen=True, extra="forbid") on all models.
2. AIHypothesisProposal.proposal_status is permanently UNVALIDATED_PROPOSAL.
3. Model/prompt metadata in ResearchManifest is descriptive provenance ONLY with ZERO governance authority.
4. Deterministic canonical SHA-256 computation over sorted payload dictionaries.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, Final, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError
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
    UnauthorizedProposalTransitionError,
)
from acash.research.schema import ExpectedDirection, InvalidationCriteria


def _canonical_sha256(payload: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 over a dictionary with canonical JSON serialization."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 1. Research Source Metadata (Tri-Axial Provenance Model)
# ---------------------------------------------------------------------------


class ResearchSourceMetadata(BaseModel):
    """Immutable provenance record describing an external research source or document.

    Enforces tri-axial taxonomy:
    1. source_type: Origin platform or medium.
    2. verification_status: Independent empirical verification state.
    3. evidence_role: Epistemic role in the research pipeline.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(pattern=r"^SRC-[0-9a-fA-F]{8,32}$")
    source_title: str = Field(min_length=3)
    authors_or_publisher: Tuple[str, ...] = Field(min_length=1)
    publication_date: Optional[str] = None
    source_url_or_doi: Optional[str] = None
    content_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    retrieval_timestamp_utc: str

    # Tri-Axial Epistemic Classification
    source_type: SourceType
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    evidence_role: EvidenceRole = Field(default=EvidenceRole.HYPOTHESIS_SOURCE)

    # Licensing & Compliance
    access_method: str = Field(description="API, SCRAPE, MANUAL_UPLOAD, LOCAL_ARCHIVE")
    content_license_status: str = Field(description="OPEN_ACCESS, CC_BY, PROPRIETARY, UNKNOWN")
    attribution_required: bool = Field(default=True)

    def compute_canonical_digest(self) -> str:
        """Compute authoritative SHA-256 digest of this source metadata record."""
        payload = {
            "access_method": self.access_method,
            "attribution_required": self.attribution_required,
            "authors_or_publisher": list(self.authors_or_publisher),
            "content_license_status": self.content_license_status,
            "content_sha256": self.content_sha256,
            "evidence_role": self.evidence_role.value,
            "publication_date": self.publication_date,
            "retrieval_timestamp_utc": self.retrieval_timestamp_utc,
            "source_id": self.source_id,
            "source_title": self.source_title,
            "source_type": self.source_type.value,
            "source_url_or_doi": self.source_url_or_doi,
            "verification_status": self.verification_status.value,
        }
        return _canonical_sha256(payload)


# ---------------------------------------------------------------------------
# 2. Research Candidate Contract
# ---------------------------------------------------------------------------


class ResearchCandidate(BaseModel):
    """Encapsulates an exploratory research idea or external strategy claim.

    A ResearchCandidate is an UNVALIDATED PROPOSAL awaiting human review.
    It holds zero authority to execute orders, access market data, or self-promote to HYP_003.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str = Field(pattern=r"^[A-Z0-9_]{5,64}$")
    candidate_family: CandidateFamily
    working_title: str = Field(min_length=5)
    target_asset_class: str = Field(min_length=2)
    target_symbol: str = Field(min_length=2)
    proposed_timeframe: str = Field(min_length=1)
    core_premise: str = Field(min_length=20)
    unresolved_specification_gaps: Tuple[str, ...] = Field(default=())
    source_metadata_ids: Tuple[str, ...] = Field(default=())
    candidate_status: CandidateStatus = Field(default=CandidateStatus.UNVALIDATED_PROPOSAL)
    recommendation_rationale: str = Field(min_length=10)
    created_at_utc: str

    def compute_canonical_digest(self) -> str:
        """Compute authoritative SHA-256 digest of this candidate record."""
        payload = {
            "candidate_family": self.candidate_family.value,
            "candidate_id": self.candidate_id,
            "candidate_status": self.candidate_status.value,
            "core_premise": self.core_premise,
            "created_at_utc": self.created_at_utc,
            "proposed_timeframe": self.proposed_timeframe,
            "recommendation_rationale": self.recommendation_rationale,
            "source_metadata_ids": list(self.source_metadata_ids),
            "target_asset_class": self.target_asset_class,
            "target_symbol": self.target_symbol,
            "unresolved_specification_gaps": list(self.unresolved_specification_gaps),
            "working_title": self.working_title,
        }
        return _canonical_sha256(payload)


# ---------------------------------------------------------------------------
# 3. AI Hypothesis Proposal (Strictly Stamped UNVALIDATED_PROPOSAL)
# ---------------------------------------------------------------------------


class AIHypothesisProposal(BaseModel):
    """Structured hypothesis proposal generated by an AI Research Assistant.

    INVARIANTS:
    - proposal_status is permanently UNVALIDATED_PROPOSAL.
    - Zero capability to self-convert into HypothesisSpecification or HYP_003.
    - Zero capability to authorize backtesting, trading, or capital.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(pattern=r"^AI-HYP-[0-9a-fA-F]{8,32}$")
    proposal_status: Literal[CandidateStatus.UNVALIDATED_PROPOSAL] = CandidateStatus.UNVALIDATED_PROPOSAL

    # Core Quantitative Hypotheses
    economic_rationale: str = Field(min_length=20)
    market_microstructure_mechanism: str = Field(min_length=20)
    invalidation_conditions: Tuple[str, ...] = Field(min_length=1)

    # Concrete Parameters
    target_symbol: str = Field(min_length=2)
    target_timeframe: str = Field(min_length=1)
    feature_dependencies: Tuple[str, ...] = Field(min_length=1)
    expected_direction: ExpectedDirection
    target_horizons: Tuple[int, ...] = Field(min_length=1)
    proposed_invalidation_criteria: InvalidationCriteria

    # Source Binding
    source_metadata_id: Optional[str] = None

    # Provenance & Lineage (Descriptive metadata only)
    llm_provider: str = Field(min_length=1)
    llm_model_id: str = Field(min_length=1)
    prompt_template_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    temperature: Decimal = Field(ge=Decimal("0.0"), le=Decimal("2.0"))
    seed: Optional[int] = None
    generated_at_utc: str
    raw_response_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    @field_validator("proposal_status")
    @classmethod
    def validate_permanent_status(cls, v: Any) -> Any:
        if v != CandidateStatus.UNVALIDATED_PROPOSAL:
            raise UnauthorizedProposalTransitionError(
                f"proposal_status cannot be set to '{v}'. "
                f"AI proposals must permanently remain UNVALIDATED_PROPOSAL."
            )
        return v

    def compute_canonical_digest(self) -> str:
        """Compute authoritative SHA-256 digest of this proposal."""
        payload = {
            "economic_rationale": self.economic_rationale,
            "expected_direction": self.expected_direction.value,
            "feature_dependencies": list(self.feature_dependencies),
            "generated_at_utc": self.generated_at_utc,
            "invalidation_conditions": list(self.invalidation_conditions),
            "llm_model_id": self.llm_model_id,
            "llm_provider": self.llm_provider,
            "market_microstructure_mechanism": self.market_microstructure_mechanism,
            "prompt_template_sha256": self.prompt_template_sha256,
            "proposal_id": self.proposal_id,
            "proposal_status": self.proposal_status.value,
            "raw_response_sha256": self.raw_response_sha256,
            "seed": self.seed,
            "source_metadata_id": self.source_metadata_id,
            "target_horizons": list(self.target_horizons),
            "target_symbol": self.target_symbol,
            "target_timeframe": self.target_timeframe,
            "temperature": str(self.temperature),
        }
        return _canonical_sha256(payload)


# ---------------------------------------------------------------------------
# 4. AI Feature Proposal (Symbolic Point-in-Time Contract)
# ---------------------------------------------------------------------------


class AIFeatureProposal(BaseModel):
    """Structured symbolic feature transformation proposed by exploratory AI."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    feature_id: str = Field(pattern=r"^AI-FEAT-[0-9a-fA-F]{8,32}$")
    feature_name: str = Field(pattern=r"^[a-z0-9_]{3,32}$")
    mathematical_formula: str = Field(min_length=3)
    ast_representation_json: str

    # Point-in-Time & Leakage Certification
    is_strictly_causal: bool = Field(default=True)
    lookahead_terms_detected: int = Field(default=0)
    point_in_time_verified: bool = Field(default=True)

    # Economic Rationale & Lineage
    intended_microstructure_signal: str = Field(min_length=10)
    provenance_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


# ---------------------------------------------------------------------------
# 5. Research Manifest Contract (Provenance Metadata Only)
# ---------------------------------------------------------------------------


class ResearchManifest(BaseModel):
    """Cryptographic audit record binding research execution lineage.

    GOVERNANCE MANDATE:
    Model metadata, prompt metadata, provider coordinates, and completion hashes
    contained herein are PURELY DESCRIPTIVE PROVENANCE.
    They MUST NOT grant:
    - Hypothesis registration authority
    - Backtest authority
    - Validation authority
    - Capital authority ($0.00 hard-locked)
    - Trading authority (LOCKED)
    - Quarantine override authority
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str = Field(pattern=r"^MAN-RES-[0-9a-fA-F]{8,32}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    created_at_utc: str

    # Input Lineage
    source_metadata_hashes: Tuple[str, ...] = Field(default=())
    dataset_manifest_hash: Optional[str] = None
    features_manifest_hash: Optional[str] = None
    git_commit_sha: str = Field(min_length=7, max_length=64)

    # AI Generation Coordinates (PROVENANCE ONLY - ZERO GOVERNANCE AUTHORITY)
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    prompt_template_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    system_policy_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    generation_temperature: Decimal = Field(ge=Decimal("0.0"), le=Decimal("2.0"))
    generation_seed: Optional[int] = None
    input_context_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    raw_response_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    # Research Coordinates
    proposal_id: str = Field(pattern=r"^AI-(HYP|FEAT)-[0-9a-fA-F]{8,32}$")
    lifecycle_state_reached: str = Field(default="PROPOSAL_RECORDED")

    def compute_canonical_digest(self) -> str:
        """Compute authoritative SHA-256 digest of this manifest excluding stored digest."""
        payload = {
            "created_at_utc": self.created_at_utc,
            "dataset_manifest_hash": self.dataset_manifest_hash,
            "features_manifest_hash": self.features_manifest_hash,
            "generation_seed": self.generation_seed,
            "generation_temperature": str(self.generation_temperature),
            "git_commit_sha": self.git_commit_sha,
            "input_context_sha256": self.input_context_sha256,
            "lifecycle_state_reached": self.lifecycle_state_reached,
            "manifest_id": self.manifest_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prompt_template_sha256": self.prompt_template_sha256,
            "proposal_id": self.proposal_id,
            "raw_response_sha256": self.raw_response_sha256,
            "source_metadata_hashes": list(self.source_metadata_hashes),
            "system_policy_sha256": self.system_policy_sha256,
        }
        return _canonical_sha256(payload)

    @model_validator(mode="after")
    def verify_manifest_integrity(self) -> "ResearchManifest":
        """Assert that stored manifest_sha256 matches canonical digest bit-for-bit."""
        expected_digest = self.compute_canonical_digest()
        if self.manifest_sha256 != expected_digest:
            raise DataContractError(
                f"ResearchManifest digest mismatch: stored '{self.manifest_sha256}' "
                f"!= computed '{expected_digest}'."
            )
        return self
