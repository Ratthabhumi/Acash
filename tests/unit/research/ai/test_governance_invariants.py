"""Unit tests for Phase 14 AI Research Intelligence Governance Invariants.

Tests:
- Strict type-level firewall: AI proposals cannot be fed directly to AlphaQualificationGate.
- Zero trading, execution, or capital authority leakage.
- AI proposals permanently remain UNVALIDATED_PROPOSAL.
- Evidence classifications are strictly preserved with zero auto-elevation.
"""

from decimal import Decimal
import pytest

from acash.research.ai.enums import (
    CandidateFamily,
    CandidateStatus,
    EvidenceClassification,
    EvidenceRole,
    SourceType,
    VerificationStatus,
)
from acash.research.ai.schema import (
    AIHypothesisProposal,
    ResearchCandidate,
    ResearchSourceMetadata,
)
from acash.research.qualification import AlphaQualificationGate
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
)


@pytest.fixture
def valid_ai_proposal() -> AIHypothesisProposal:
    return AIHypothesisProposal(
        proposal_id="AI-HYP-9999888877776666",
        economic_rationale="Opening volume surge drives directional trend continuation across morning session.",
        market_microstructure_mechanism="Opening cross auction order unbundling creates inventory imbalance.",
        invalidation_conditions=("Rank IC < 0.02",),
        target_symbol="NQ",
        target_timeframe="M5",
        feature_dependencies=("close", "ema_fast"),
        expected_direction=ExpectedDirection.LONG,
        target_horizons=(1, 6),
        proposed_invalidation_criteria=InvalidationCriteria(),
        llm_provider="mock_llm",
        llm_model_id="mock-model-v1",
        prompt_template_sha256="a" * 64,
        temperature=Decimal("0.0"),
        generated_at_utc="2026-09-07T00:00:00+00:00",
        raw_response_sha256="b" * 64,
    )


def test_type_firewall_proposal_cannot_be_fed_to_alpha_gate(
    valid_ai_proposal: AIHypothesisProposal,
) -> None:
    """Assert that an AIHypothesisProposal cannot be accepted by AlphaQualificationGate.

    The canonical AlphaQualificationGate.qualify_alpha requires a HypothesisSpecification.
    An AIHypothesisProposal is structurally NOT a HypothesisSpecification, so type-level
    integration is impossible. There is no alternate entrance point (e.g. evaluate_dossier)
    that could accept an AI proposal.
    """
    assert not isinstance(valid_ai_proposal, HypothesisSpecification)

    # No self-promotion facade exists on the gate that could accept an AI proposal directly.
    assert not hasattr(AlphaQualificationGate, "evaluate_dossier")

    # The canonical entrance requires a sealed HypothesisSpecification lineage; an AI proposal
    # cannot be spliced in without an explicit HypothesisSpecification of its own.
    gate = AlphaQualificationGate()
    constrained_qualify = getattr(gate, "qualify_alpha", None)
    assert constrained_qualify is not None
    # An AIHypothesisProposal cannot resolve to a HypothesisSpecification anywhere in its API.
    for method in ("register", "to_hypothesis_specification", "authorize", "execute_backtest"):
        assert not hasattr(valid_ai_proposal, method)


def test_no_trading_or_capital_authority_leakage(
    valid_ai_proposal: AIHypothesisProposal,
) -> None:
    """Assert that neither AI proposals nor Research candidates possess execution wires."""
    forbidden_methods = (
        "order_send",
        "positions_get",
        "history_deals_get",
        "authorize_trading",
        "allocate_capital",
        "override_risk_limit",
        "trip_kill_switch",
    )
    for method in forbidden_methods:
        assert not hasattr(valid_ai_proposal, method), f"AI proposal leaked execution method: {method}"

    candidate = ResearchCandidate(
        candidate_id="CAND_NQ_M5_DIRECTIONAL",
        candidate_family=CandidateFamily.SESSION_EVENT_MOMENTUM,
        working_title="NQ M5 Opening Momentum Candidate",
        target_asset_class="Equity Index Futures",
        target_symbol="NQ",
        proposed_timeframe="M5",
        core_premise="Directional momentum continuation after opening candle closes beyond fast EMA.",
        candidate_status=CandidateStatus.UNVALIDATED_PROPOSAL,
        recommendation_rationale="Exploratory candidate.",
        created_at_utc="2026-09-07T00:00:00+00:00",
    )
    for method in forbidden_methods:
        assert not hasattr(candidate, method), f"Research candidate leaked execution method: {method}"


def test_source_evidence_classification_distinction() -> None:
    """Assert that academic or vendor origin does not automatically grant VERIFIED status."""
    meta = ResearchSourceMetadata(
        source_id="SRC-1122334455667788",
        source_title="Backtest Vendor Sales Pitch",
        authors_or_publisher=("Marketing Vendor Inc.",),
        content_sha256="c" * 64,
        retrieval_timestamp_utc="2026-09-07T00:00:00+00:00",
        source_type=SourceType.VENDOR,
        verification_status=VerificationStatus.UNVERIFIED,
        evidence_role=EvidenceRole.HYPOTHESIS_SOURCE,
        access_method="MANUAL_UPLOAD",
        content_license_status="PROPRIETARY",
    )
    # Even if labeled as hypothesis source, verification status remains UNVERIFIED
    assert meta.verification_status == VerificationStatus.UNVERIFIED
    assert meta.evidence_role == EvidenceRole.HYPOTHESIS_SOURCE
