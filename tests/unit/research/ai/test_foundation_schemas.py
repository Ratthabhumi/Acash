"""Unit tests for Phase 14 AI Research Intelligence Foundation Schemas.

Tests:
- Deterministic serialization and cryptographic digest stability.
- Extra-field rejection (extra="forbid").
- Immutable / frozen fields.
- AIHypothesisProposal.proposal_status permanent UNVALIDATED_PROPOSAL constraint.
- Tri-axial epistemic taxonomy enforcement.
- ResearchManifest provenance integrity and lack of governance authority.
"""

from decimal import Decimal
from typing import Any, Dict
import pytest
from pydantic import ValidationError

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
    UnauthorizedProposalTransitionError,
)
from acash.research.ai.schema import (
    AIFeatureProposal,
    AIHypothesisProposal,
    ResearchCandidate,
    ResearchManifest,
    ResearchSourceMetadata,
)
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
)


def test_research_source_metadata_serialization_and_digest() -> None:
    """Test deterministic serialization and SHA-256 computation of source metadata."""
    meta = ResearchSourceMetadata(
        source_id="SRC-12345678abcdef01",
        source_title="Market Intraday Momentum",
        authors_or_publisher=("Gao, L.", "Han, Y.", "Li, S. Z.", "Zhou, G."),
        publication_date="2018-08-01",
        source_url_or_doi="https://doi.org/10.1016/j.jfineco.2018.05.009",
        content_sha256="a" * 64,
        retrieval_timestamp_utc="2026-09-07T00:00:00+00:00",
        source_type=SourceType.ACADEMIC,
        verification_status=VerificationStatus.INDEPENDENTLY_VALIDATED,
        evidence_role=EvidenceRole.EMPIRICAL_EVIDENCE,
        access_method="API",
        content_license_status="PROPRIETARY",
        attribution_required=True,
    )
    digest1 = meta.compute_canonical_digest()
    digest2 = meta.compute_canonical_digest()
    assert digest1 == digest2
    assert len(digest1) == 64


def test_research_source_metadata_extra_field_forbidden() -> None:
    """Assert that passing unmodeled extra fields raises ValidationError."""
    extra_fields: Dict[str, Any] = {"unauthorized_field": "malicious_payload"}  # Extra field
    with pytest.raises(ValidationError):
        ResearchSourceMetadata(
            source_id="SRC-12345678abcdef01",
            source_title="Test Source",
            authors_or_publisher=("Author, A.",),
            content_sha256="b" * 64,
            retrieval_timestamp_utc="2026-09-07T00:00:00+00:00",
            source_type=SourceType.BLOG,
            access_method="SCRAPE",
            content_license_status="UNKNOWN",
            **extra_fields,
        )


def test_research_source_metadata_frozen_immutability() -> None:
    """Assert that mutating fields on an existing instance raises ValidationError."""
    meta = ResearchSourceMetadata(
        source_id="SRC-12345678abcdef01",
        source_title="Test Source",
        authors_or_publisher=("Author, A.",),
        content_sha256="c" * 64,
        retrieval_timestamp_utc="2026-09-07T00:00:00+00:00",
        source_type=SourceType.BLOG,
        access_method="SCRAPE",
        content_license_status="UNKNOWN",
    )
    with pytest.raises(ValidationError):
        meta.source_title = "Mutated Title"


def test_tri_axial_taxonomy_independence() -> None:
    """Verify that source_type, verification_status, and evidence_role are strictly decoupled."""
    # A social media post used as hypothesis source:
    meta = ResearchSourceMetadata(
        source_id="SRC-abcdef0123456789",
        source_title="Trading Strategy Video Claim",
        authors_or_publisher=("Anonymous Creator",),
        content_sha256="d" * 64,
        retrieval_timestamp_utc="2026-09-07T00:00:00+00:00",
        source_type=SourceType.SOCIAL,
        verification_status=VerificationStatus.UNVERIFIED,
        evidence_role=EvidenceRole.HYPOTHESIS_SOURCE,
        access_method="MANUAL_UPLOAD",
        content_license_status="UNKNOWN",
    )
    assert meta.source_type == SourceType.SOCIAL
    assert meta.verification_status == VerificationStatus.UNVERIFIED
    assert meta.evidence_role == EvidenceRole.HYPOTHESIS_SOURCE


def test_research_candidate_schema_and_status() -> None:
    """Test ResearchCandidate creation, default status, and digest computation."""
    candidate = ResearchCandidate(
        candidate_id="CAND_NY_OPEN_EMA_MOMENTUM_M5",
        candidate_family=CandidateFamily.SESSION_EVENT_MOMENTUM,
        working_title="NY Open First-Bar Directional Momentum",
        target_asset_class="Equity Index Futures",
        target_symbol="NQ",
        proposed_timeframe="M5",
        core_premise="Directional continuation after opening candle closes beyond fast EMA.",
        unresolved_specification_gaps=("FAST_EMA_PERIOD", "ATR_PERIOD", "EOD_EXIT"),
        source_metadata_ids=("SRC-abcdef0123456789",),
        candidate_status=CandidateStatus.UNVALIDATED_PROPOSAL,
        recommendation_rationale="Plausible institutional mechanism but lacks exact parameters.",
        created_at_utc="2026-09-07T00:00:00+00:00",
    )
    assert candidate.candidate_status == CandidateStatus.UNVALIDATED_PROPOSAL
    digest = candidate.compute_canonical_digest()
    assert len(digest) == 64


def test_ai_hypothesis_proposal_permanent_status() -> None:
    """Assert that AIHypothesisProposal.proposal_status is locked to UNVALIDATED_PROPOSAL."""
    proposal = AIHypothesisProposal(
        proposal_id="AI-HYP-1234567890abcdef",
        economic_rationale="Institutional order flow digestion at cash equity open creates intraday momentum.",
        market_microstructure_mechanism="Opening cross auction volume imbalance unbundles over first 30 minutes.",
        invalidation_conditions=("Rank IC < 0.02", "HAC t-stat < 2.0"),
        target_symbol="NQ",
        target_timeframe="M5",
        feature_dependencies=("close_price", "ema_fast"),
        expected_direction=ExpectedDirection.LONG,
        target_horizons=(1, 6),
        proposed_invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.025"),
            min_hac_t_stat=Decimal("2.00"),
        ),
        llm_provider="mock_provider",
        llm_model_id="mock-quant-v1",
        prompt_template_sha256="e" * 64,
        temperature=Decimal("0.0"),
        generated_at_utc="2026-09-07T00:00:00+00:00",
        raw_response_sha256="f" * 64,
    )
    assert proposal.proposal_status == CandidateStatus.UNVALIDATED_PROPOSAL

    # Attempting to construct with any other status must raise ValidationError
    with pytest.raises(ValidationError):
        AIHypothesisProposal(
            proposal_id="AI-HYP-1234567890abcdef",
            proposal_status="REGISTERED_ALPHA",  # type: ignore[arg-type]
            economic_rationale="Economic rationale long enough.",
            market_microstructure_mechanism="Microstructure mechanism long enough.",
            invalidation_conditions=("Rank IC < 0.02",),
            target_symbol="NQ",
            target_timeframe="M5",
            feature_dependencies=("close",),
            expected_direction=ExpectedDirection.LONG,
            target_horizons=(1,),
            proposed_invalidation_criteria=InvalidationCriteria(),
            llm_provider="mock",
            llm_model_id="mock-v1",
            prompt_template_sha256="e" * 64,
            temperature=Decimal("0.0"),
            generated_at_utc="2026-09-07T00:00:00+00:00",
            raw_response_sha256="f" * 64,
        )


def test_ai_hypothesis_proposal_cannot_self_convert_to_specification() -> None:
    """Assert that an AI proposal has no method to transform itself into a canonical HypothesisSpecification."""
    proposal = AIHypothesisProposal(
        proposal_id="AI-HYP-1234567890abcdef",
        economic_rationale="Institutional order flow digestion creates persistent morning momentum.",
        market_microstructure_mechanism="Opening cross auction volume imbalance unbundles over 30 mins.",
        invalidation_conditions=("Rank IC < 0.02",),
        target_symbol="NQ",
        target_timeframe="M5",
        feature_dependencies=("close",),
        expected_direction=ExpectedDirection.LONG,
        target_horizons=(1,),
        proposed_invalidation_criteria=InvalidationCriteria(),
        llm_provider="mock",
        llm_model_id="mock-v1",
        prompt_template_sha256="1" * 64,
        temperature=Decimal("0.0"),
        generated_at_utc="2026-09-07T00:00:00+00:00",
        raw_response_sha256="2" * 64,
    )
    # Ensure there are no self-registration or self-conversion methods on the model
    assert not hasattr(proposal, "register")
    assert not hasattr(proposal, "to_hypothesis_specification")
    assert not hasattr(proposal, "authorize")
    assert not hasattr(proposal, "execute_backtest")
    assert not isinstance(proposal, HypothesisSpecification)


def test_ai_feature_proposal_causal_contract() -> None:
    """Test AIFeatureProposal creation and causal invariant defaults."""
    feature = AIFeatureProposal(
        feature_id="AI-FEAT-12345678abcdef01",
        feature_name="opening_imbalance_ratio",
        mathematical_formula="(buy_vol - sell_vol) / (buy_vol + sell_vol)",
        ast_representation_json='{"op": "div"}',
        is_strictly_causal=True,
        lookahead_terms_detected=0,
        point_in_time_verified=True,
        intended_microstructure_signal="Measures net aggressive order imbalance.",
        provenance_hash="3" * 64,
    )
    assert feature.is_strictly_causal is True
    assert feature.lookahead_terms_detected == 0


def test_research_manifest_integrity_and_tamper_detection() -> None:
    """Verify ResearchManifest computes digest and detects tampering."""
    raw_payload = {
        "created_at_utc": "2026-09-07T00:00:00+00:00",
        "dataset_manifest_hash": None,
        "features_manifest_hash": None,
        "generation_seed": 42,
        "generation_temperature": "0.0",
        "git_commit_sha": "a1b2c3d4e5f67890",
        "input_context_sha256": "4" * 64,
        "lifecycle_state_reached": "PROPOSAL_RECORDED",
        "manifest_id": "MAN-RES-12345678abcdef01",
        "model_id": "quant-coder-v1",
        "model_version": "1.0.0",
        "prompt_template_sha256": "5" * 64,
        "proposal_id": "AI-HYP-1234567890abcdef",
        "raw_response_sha256": "6" * 64,
        "source_metadata_hashes": ["7" * 64],
        "system_policy_sha256": "8" * 64,
    }
    import hashlib
    import json
    canonical_json = json.dumps(raw_payload, sort_keys=True, separators=(",", ":"))
    valid_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    manifest = ResearchManifest(
        manifest_id="MAN-RES-12345678abcdef01",
        manifest_sha256=valid_digest,
        created_at_utc="2026-09-07T00:00:00+00:00",
        source_metadata_hashes=("7" * 64,),
        git_commit_sha="a1b2c3d4e5f67890",
        model_id="quant-coder-v1",
        model_version="1.0.0",
        prompt_template_sha256="5" * 64,
        system_policy_sha256="8" * 64,
        generation_temperature=Decimal("0.0"),
        generation_seed=42,
        input_context_sha256="4" * 64,
        raw_response_sha256="6" * 64,
        proposal_id="AI-HYP-1234567890abcdef",
        lifecycle_state_reached="PROPOSAL_RECORDED",
    )
    assert manifest.manifest_sha256 == valid_digest

    # Tampering with digest must trigger DataContractError
    with pytest.raises(DataContractError, match="ResearchManifest digest mismatch"):
        ResearchManifest(
            manifest_id="MAN-RES-12345678abcdef01",
            manifest_sha256="0" * 64,
            created_at_utc="2026-09-07T00:00:00+00:00",
            source_metadata_hashes=("7" * 64,),
            git_commit_sha="a1b2c3d4e5f67890",
            model_id="quant-coder-v1",
            model_version="1.0.0",
            prompt_template_sha256="5" * 64,
            system_policy_sha256="8" * 64,
            generation_temperature=Decimal("0.0"),
            generation_seed=42,
            input_context_sha256="4" * 64,
            raw_response_sha256="6" * 64,
            proposal_id="AI-HYP-1234567890abcdef",
            lifecycle_state_reached="PROPOSAL_RECORDED",
        )


def test_research_manifest_metadata_has_no_governance_authority() -> None:
    """Assert that ResearchManifest is strictly an informational provenance record."""
    raw_payload: Dict[str, Any] = {
        "created_at_utc": "2026-09-07T00:00:00+00:00",
        "dataset_manifest_hash": None,
        "features_manifest_hash": None,
        "generation_seed": None,
        "generation_temperature": "0.5",
        "git_commit_sha": "a1b2c3d4e5f67890",
        "input_context_sha256": "4" * 64,
        "lifecycle_state_reached": "PROPOSAL_RECORDED",
        "manifest_id": "MAN-RES-abcdef1234567890",
        "model_id": "claude-3-5-sonnet",
        "model_version": "20241022",
        "prompt_template_sha256": "5" * 64,
        "proposal_id": "AI-HYP-1234567890abcdef",
        "raw_response_sha256": "6" * 64,
        "source_metadata_hashes": [],
        "system_policy_sha256": "8" * 64,
    }
    import hashlib
    import json
    canonical_json = json.dumps(raw_payload, sort_keys=True, separators=(",", ":"))
    valid_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    manifest = ResearchManifest(
        manifest_id="MAN-RES-abcdef1234567890",
        manifest_sha256=valid_digest,
        created_at_utc="2026-09-07T00:00:00+00:00",
        git_commit_sha="a1b2c3d4e5f67890",
        model_id="claude-3-5-sonnet",
        model_version="20241022",
        prompt_template_sha256="5" * 64,
        system_policy_sha256="8" * 64,
        generation_temperature=Decimal("0.5"),
        input_context_sha256="4" * 64,
        raw_response_sha256="6" * 64,
        proposal_id="AI-HYP-1234567890abcdef",
    )
    # Confirm it holds zero execution methods
    assert not hasattr(manifest, "authorize_trading")
    assert not hasattr(manifest, "allocate_capital")
    assert not hasattr(manifest, "override_quarantine")
    assert not hasattr(manifest, "approve_hypothesis")
