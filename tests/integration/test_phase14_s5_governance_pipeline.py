"""S5 TEST-ONLY governance pipeline (Phase 14).

HUMAN-AUTHORIZED SCOPE (S5 TEST-ONLY slice):
- This file is the ONLY artifact authorized for creation/modification by S5.
- It proves, against the canonical runtime code, that the Phase 14 research
  capability preserves the governance boundaries: AI research capability is
  strict UNVALIDATED_PROPOSAL-only; G-4 frozen token governance is enforced;
  conversion is artifact-only; features stay causal and non-tradeable; Phases
  5/6/8.5 fail closed; Section 33 reports are grounded in sealed evidence;
  behavior is deterministic; and the new AI modules carry zero authority and
  zero runtime wiring.
- S5 is TEST-ONLY: every assertion is a static claim about pre-existing
  canonical code. Synthetic, in-memory gate calls are NOT canonical gate
  invocations, do NOT persist authorizations, and are NOT trading authority.

DEPLOY BRIEF:
- No production files are modified. No config, registry, credential, network,
  broker, or gate state is touched. Hypothesis IDs used below are test-local
  and are never written to any repo-managed registry.
- HYP_003 ABSENT. R1 NOT STARTED. Gates NOT invoked as execution authorities.
- Test semantics never change the invariant matrix (Capital $0.00, Broker
  DISCONNECTED, Orders 0, Trading LOCKED, F-1 UNTOUCHED, Retrieval
  UNRESOLVED/EXCLUDED, E9 DEFERRED, Gate 14 = ACCEPTED).

KNOWN DEFERRED SEAMS (NOT worked around; asserted truthfully):
- Seam 1 (RESOLVED by Seam A): ``ACASHNativeBacktestEngine`` (Phase 5) now
  carries the genuine upstream ``HypothesisSpecification.hypothesis_id`` into
  its emitted ``BacktestManifest`` (src/acash/backtest/engine.py). The truth
  is asserted below; the placeholder has been eliminated.
- Seam 2: ``FeatureDiscoveryEngine`` emits ``AIFeatureProposal`` (symbolic),
  while ``AlphaResearchPipeline`` consumes a concrete element-wise PyArrow
  feature table. No implicit bridge exists (asserted below); the human-gated
  materialization adapter is DEFERRED pending separate human authorization.
"""

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyarrow as pa
import pytest
from pydantic import ValidationError

from acash.backtest.adapter import BacktestEventType, BacktestMarketEvent
from acash.backtest.nautilus_bridge import ACASHNativeBacktestEngine
from acash.backtest.schema import BacktestEngineConfig, OrderType
from acash.core.domain.exceptions import DataContractError
from acash.research.ai.enums import CandidateStatus
from acash.research.ai.features.ast_validator import CausalAstValidator
from acash.research.ai.features.discovery import (
    FeatureDiscoveryEngine,
    FeatureDiscoveryRequest,
)
from acash.research.ai.hypothesis.assistant import AIHypothesisAssistant, AssistantResult
from acash.research.ai.hypothesis.converter import HypothesisProposalConverter
from acash.research.ai.hypothesis.prompts import (
    PROMPT_TEMPLATE_SHA256,
    USER_PROMPT_TEMPLATE,
)
from acash.research.ai.provider.base import (
    FROZEN_PER_REQUEST_MAX_TOKENS,
    FROZEN_PER_REQUEST_WARNING_TOKENS,
    FROZEN_PER_RUN_MAX_TOKENS,
    FROZEN_PER_RUN_WARNING_TOKENS,
    BudgetPolicy,
    InferenceBudgetError,
    RunBudgetSession,
    TokenUsage,
)
from acash.research.ai.provider.mock import MOCK_MODEL_ID, MOCK_PROVIDER_NAME, MockLLMProvider
from acash.research.ai.reporting import (
    OMITTED_MARKER,
    EvidenceGroundingVerifier,
    Section33Report,
    Section33ReportGenerator,
    validate_evidence_chain,
)
from acash.research.ai.schema import AIFeatureProposal, AIHypothesisProposal
from acash.research.alpha_schema import (
    AlphaEconomicDecomposition,
    AlphaLifecycleState,
    AlphaQualificationDossier,
)
from acash.research.manifest import ResearchManifestEngine, calculate_hypothesis_spec_sha256
from acash.research.pipeline import AlphaResearchPipeline
from acash.research.qualification import AlphaQualificationGate
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
)
from acash.validation.gate import StatisticalValidationGate
from acash.validation.schema import (
    DSRResult,
    MultipleTestingResult,
    OverfittingReport,
    SearchTrialLedger,
    SearchTrialRecord,
    SharpeSpace,
    ValidationGateVerdict,
    ValidationReport,
)

# ---------------------------------------------------------------------------
# Test-local constants (never registered, never persisted beyond tmp dirs)
# ---------------------------------------------------------------------------

S5_STRATEGY_ID = "STRREG_001"
S5_HYPOTHESIS_ID = "HYP_TEST_0001"
S5_ALPHA_ID = "ALPHA_0001"

S5_DECISION_DIGEST = hashlib.sha256(b"s5-validation-report-fixture-v1").hexdigest()
S5_EVIDENCE_DIGEST = hashlib.sha256(b"s5-evidence-fixture-v1").hexdigest()
S5_GOVERNANCE_DIGEST = hashlib.sha256(b"s5-governance-policy-v1").hexdigest()

FIXED_TS = "2026-09-08T12:00:00+00:00"


def _fixed_clock() -> datetime:
    return datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)


# Byte-deterministic mock provider completion: a valid single-JSON-object draft.
_COMPLETION_DICT: Dict[str, object] = {
    "economic_rationale": (
        "Opening-volume order flow imbalance predicts short-horizon directional "
        "continuation across liquid index constituents, falsifiable if the relation decays."
    ),
    "market_microstructure_mechanism": (
        "Inventory-driven liquidity withdrawals at session open amplify transient price "
        "pressure that mean-reverts once dealer inventory is rebalanced."
    ),
    "invalidation_conditions": [
        "HAC t-stat falls below the pre-registered threshold",
        "In-sample rank IC turns non-positive",
    ],
    "target_symbol": "ES.FUT",
    "target_timeframe": "M5",
    "feature_dependencies": ["opening_volume_imbalance", "vwap_std"],
    "expected_direction": "LONG",
    "target_horizons": [1, 5],
    "proposed_invalidation_criteria": {
        "min_in_sample_rank_ic": "0.01",
        "min_hac_t_stat": "1.50",
        "max_feature_autocorrelation": "0.98",
        "min_cost_adjusted_spread_ratio": "1.00",
    },
}
_COMPLETION_JSON: str = json.dumps(_COMPLETION_DICT, sort_keys=True)


def _make_assistant(
    *,
    usage: Optional[TokenUsage] = None,
    completion: Optional[str] = None,
) -> AIHypothesisAssistant:
    provider = MockLLMProvider(
        completion=_COMPLETION_JSON if completion is None else completion,
        usage=usage,
        clock=_fixed_clock,
    )
    return AIHypothesisAssistant(provider=provider, clock=_fixed_clock)


def _make_proposal(*, fresh_budget: bool = False) -> AssistantResult:
    """Deterministic assistant output shape used by multiple sections."""
    budget_arg = RunBudgetSession() if fresh_budget else None
    return _make_assistant().generate_hypothesis(
        symbol="ES.FUT",
        timeframe="M5",
        economic_context=(
            "Session open, elevated imbalance, dealer inventory pressure; draft a "
            "falsifiable short-horizon directional hypothesis."
        ),
        proposal_id="AI-HYP-1234abcd5678ef00",
        budget=budget_arg,
    )


# ---------------------------------------------------------------------------
# Sealed evidence bundle recipe (mirrors tests/unit/research/ai
# test_research_ai_reporting.py: stable, cross-digest-consistent).
# ---------------------------------------------------------------------------


@dataclass
class S5EvidenceBundle:
    """A fully sealed, cross-digest-consistent evidence bundle."""

    hypothesis: HypothesisSpecification
    ledger: SearchTrialLedger
    validation: ValidationReport
    dossier: AlphaQualificationDossier


def _make_dsr() -> DSRResult:
    return DSRResult(
        estimated_sharpe=Decimal("1.2"),
        benchmark_sharpe=Decimal("0.0"),
        expected_max_sharpe_sr0=Decimal("0.70"),
        sample_skewness=Decimal("-0.30"),
        sample_kurtosis=Decimal("3.10"),
        sample_size_t=2500,
        dsr_trials_k=45,
        trial_variance_used=Decimal("0.09"),
        dsr_statistic=Decimal("1.645"),
        dsr_probability=Decimal("0.95"),
        is_statistically_significant=True,
        has_sufficient_track_record=True,
    )


def _make_multiple_testing() -> MultipleTestingResult:
    return MultipleTestingResult(
        dsr_trials_k=45,
        raw_p_values=[Decimal("0.01")],
        holm_bonferroni_p_values=[Decimal("0.45")],
        benjamini_hochberg_q_values=[Decimal("0.10")],
        bonferroni_haircut_sharpe_ratio=Decimal("1.40"),
        is_fwer_significant=True,
    )


def _make_overfitting() -> OverfittingReport:
    return OverfittingReport(
        pbo_estimate=Decimal("0.05"),
        logits_distribution_mean=Decimal("-1.20"),
        logits_distribution_std=Decimal("0.30"),
        is_pbo_acceptable=True,
        parameter_fragility_max_curvature=Decimal("0.10"),
        is_parameter_stable=True,
        analytical_friction_monotonicity_passed=True,
    )


def _make_econ(
    gross: str = "-12.50",
    spread: str = "2.00",
    commissions: str = "1.00",
    net: str = "-15.50",
    rebate: str = "0.00",
    total: str = "-15.50",
) -> AlphaEconomicDecomposition:
    return AlphaEconomicDecomposition(
        gross_trading_pnl_bps=Decimal(gross),
        realized_spread_slippage_bps=Decimal(spread),
        broker_commissions_bps=Decimal(commissions),
        net_trading_alpha_bps=Decimal(net),
        broker_rebate_income_bps=Decimal(rebate),
        total_realized_economic_bps=Decimal(total),
    )


def _make_bundle_hypothesis() -> HypothesisSpecification:
    return HypothesisSpecification(
        hypothesis_id=S5_HYPOTHESIS_ID,
        hypothesis_version="v1",
        parent_hypothesis_id=None,
        economic_rationale=(
            "Fragmented order flow predicts short-horizon directional continuation across "
            "liquid index constituents; the candidate edge is falsified if the HAC t-stat "
            "falls below the pre-registered threshold."
        ),
        target_symbol="EQX:INDEX_0099",
        feature_dependencies=["order_flow_imbalance"],
        parameter_config_json='{"window": 5, "direction": "long"}',
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[5],
        primary_horizon=5,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-01-01T00:00:00+00:00",
        author="QA_Auditor",
    )


def _make_trial() -> SearchTrialRecord:
    p_value = Decimal("0.01")
    p_value_method = "ASYMPTOTIC_TWO_SIDED_ZERO_SHARPE_NORMAL_TEST_V1"
    config_sha256 = SearchTrialRecord.compute_config_sha256(
        feature_names=("order_flow_imbalance",), parameters={"window": 5}
    )
    p_value_input_hash = SearchTrialRecord.compute_p_value_input_hash(
        return_series_sha256="b" * 64,
        config_sha256=config_sha256,
        p_value=p_value,
        p_value_method=p_value_method,
    )
    return SearchTrialRecord(
        trial_id="TRIAL_0001",
        strategy_id=S5_STRATEGY_ID,
        hypothesis_id=S5_HYPOTHESIS_ID,
        feature_names=("order_flow_imbalance",),
        parameters={"window": 5},
        in_sample_sharpe=Decimal("1.8"),
        p_value=p_value,
        p_value_method=p_value_method,
        p_value_input_hash=p_value_input_hash,
        config_sha256=config_sha256,
        in_sample_return_series_sha256="b" * 64,
        execution_manifest_id="BM_0001",
    )


def make_s5_bundle() -> S5EvidenceBundle:
    hypothesis = _make_bundle_hypothesis()
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_0001",
        strategy_id=S5_STRATEGY_ID,
        hypothesis_id=S5_HYPOTHESIS_ID,
        trials=(_make_trial(),),
        sharpe_space=SharpeSpace.ANNUAL,
    ).seal(sealed_at_utc="2026-01-02T00:00:00+00:00")
    assert ledger.ledger_digest is not None

    validation = ValidationReport(
        validation_id=S5_DECISION_DIGEST,
        evidence_digest=S5_EVIDENCE_DIGEST,
        decision_digest=S5_DECISION_DIGEST,
        strategy_id=S5_STRATEGY_ID,
        hypothesis_id=S5_HYPOTHESIS_ID,
        verdict=ValidationGateVerdict.PASS_TRADEABLE_ALPHA,
        is_tradeable_alpha=True,
        dsr_result=_make_dsr(),
        multiple_testing_result=_make_multiple_testing(),
        overfitting_report=_make_overfitting(),
        in_sample_sharpe=Decimal("1.8"),
        out_of_sample_sharpe=Decimal("0.95"),
        oos_retention_pct=Decimal("50.0"),
        created_timestamp_utc="2026-01-03T00:00:00+00:00",
    )

    dossier = AlphaQualificationDossier(
        alpha_id=S5_ALPHA_ID,
        strategy_id=S5_STRATEGY_ID,
        lifecycle_state=AlphaLifecycleState.RESEARCH_QUALIFIED,
        hypothesis_digest=calculate_hypothesis_spec_sha256(hypothesis),
        trial_ledger_digest=ledger.ledger_digest,
        validation_report_digest=S5_DECISION_DIGEST,
        governance_policy_digest=S5_GOVERNANCE_DIGEST,
        economic_decomposition=_make_econ(),
        falsification_triggers=(),
        governance_policy_version="v1.0",
        created_timestamp_utc="2026-01-04T00:00:00+00:00",
        capital_authority_usd=Decimal("0.00"),
        dossier_digest="",
    )
    dossier = dossier.model_copy(update={"dossier_digest": dossier.compute_dossier_digest()})
    return S5EvidenceBundle(hypothesis=hypothesis, ledger=ledger, validation=validation, dossier=dossier)


# ---------------------------------------------------------------------------
# Item 1: AI capability is research-only, strictly UNVALIDATED_PROPOSAL.
# ---------------------------------------------------------------------------


def test_ai_proposal_is_unvalidated_research_only() -> None:
    result = _make_proposal()
    proposal = result.proposal
    assert isinstance(proposal, AIHypothesisProposal)
    assert proposal.proposal_id == "AI-HYP-1234abcd5678ef00"
    assert proposal.proposal_status == CandidateStatus.UNVALIDATED_PROPOSAL
    assert proposal.proposal_status.value == "UNVALIDATED_PROPOSAL"

    # Provenance is bound, not invented.
    assert proposal.llm_provider == MOCK_PROVIDER_NAME
    assert proposal.llm_model_id == MOCK_MODEL_ID
    assert proposal.prompt_template_sha256 == PROMPT_TEMPLATE_SHA256
    assert proposal.raw_response_sha256 == hashlib.sha256(_COMPLETION_JSON.encode("utf-8")).hexdigest()
    assert proposal.generated_at_utc == FIXED_TS

    # Deterministic usage + budget snapshot are propagated, not fabricated.
    assert result.usage.total_tokens == 96
    assert result.usage.inference_cost_usd is None
    assert result.usage.pricing_unavailable is True
    assert result.budget.tokens_consumed_total == 96
    assert result.budget.request_count == 1
    assert result.budget.budget_warnings == ()
    assert len(result.budget.run_digest) == 64

    # No gate/registry/authority surface exists on the proposal artifact.
    for forbidden_attr in ("register", "seal", "qualify", "authorize", "promote"):
        assert not hasattr(proposal, forbidden_attr), forbidden_attr


def test_ai_proposal_cannot_be_promoted_at_type_level() -> None:
    proposal = _make_proposal().proposal
    payload = proposal.model_dump(mode="python")
    payload.pop("proposal_status")
    # The Literal type itself refuses any non-UNVALIDATED_PROPOSAL assignment.
    with pytest.raises(ValidationError, match="proposal_status"):
        AIHypothesisProposal(**payload, proposal_status=CandidateStatus.REJECTED)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Item 2: G-4 budget governance uses the human-frozen values, fail-closed.
# ---------------------------------------------------------------------------


def test_g4_frozen_values_are_the_ratified_defaults() -> None:
    policy = BudgetPolicy()
    assert policy.per_request_max_tokens == FROZEN_PER_REQUEST_MAX_TOKENS == 16_384
    assert policy.per_request_warning_tokens == FROZEN_PER_REQUEST_WARNING_TOKENS == 12_288
    assert policy.per_run_max_tokens == FROZEN_PER_RUN_MAX_TOKENS == 100_000
    assert policy.per_run_warning_tokens == FROZEN_PER_RUN_WARNING_TOKENS == 80_000


def test_g4_per_request_warning_allowed_ceiling_closed() -> None:
    session = RunBudgetSession()
    session.record_usage(TokenUsage(input_tokens=7_000, output_tokens=6_000, total_tokens=13_000))
    snap = session.snapshot()
    assert snap.tokens_consumed_total == 13_000
    assert any("PER_REQUEST_WARNING=13000>=12288" in w for w in snap.budget_warnings)

    # A single response that exceeds the per-request ceiling is refused (fail-closed).
    with pytest.raises(InferenceBudgetError, match="per-request ceiling exceeded by response"):
        session.record_usage(TokenUsage(input_tokens=8_000, output_tokens=9_000, total_tokens=17_000))
    assert session.request_count == 1


def test_g4_per_request_pre_dispatch_raises_with_zero_dispatch() -> None:
    session = RunBudgetSession()
    with pytest.raises(InferenceBudgetError, match="per-request ceiling"):
        _make_assistant().generate_hypothesis(
            symbol="ES.FUT",
            timeframe="M5",
            economic_context="x" * 70_000,
            budget=session,
        )
    # Pre-check rejection consumes zero usage and zero requests.
    snap = session.snapshot()
    assert snap.tokens_consumed_total == 0
    assert snap.request_count == 0


def test_g4_per_run_warning_and_ceiling_through_assistant() -> None:
    provider = MockLLMProvider(
        completion=_COMPLETION_JSON,
        usage=TokenUsage(input_tokens=10_000, output_tokens=6_000, total_tokens=16_000),
        clock=_fixed_clock,
    )
    assistant = AIHypothesisAssistant(provider=provider, clock=_fixed_clock)
    session = RunBudgetSession()
    for expected_consumed in (16_000, 32_000, 48_000, 64_000, 80_000, 96_000):
        result = assistant.generate_hypothesis(
            symbol="ES.FUT",
            timeframe="M5",
            economic_context="Deterministic session-open imbalance context.",
            proposal_id="AI-HYP-1234abcd5678ef00",
            budget=session,
        )
        assert result.budget.tokens_consumed_total == expected_consumed
    assert any("PER_RUN_WARNING" in w for w in session.snapshot().budget_warnings)

    # The 7th request is rejected BEFORE dispatch: 96,000 + est(prompt)+8192 > 100,000.
    with pytest.raises(InferenceBudgetError, match="per-run ceiling"):
        assistant.generate_hypothesis(
            symbol="ES.FUT",
            timeframe="M5",
            economic_context="Deterministic session-open imbalance context.",
            proposal_id="AI-HYP-1234abcd5678ef00",
            budget=session,
        )
    assert session.request_count == 6
    assert session.tokens_consumed_total == 96_000


def test_g4_run_digest_is_deterministic() -> None:
    def _sequence() -> str:
        session = RunBudgetSession()
        for _ in range(3):
            session.record_usage(TokenUsage(total_tokens=300))
        return session.snapshot().run_digest

    assert _sequence() == _sequence()
    assert len(_sequence()) == 64


# ---------------------------------------------------------------------------
# Item 3: Proposal -> Specification conversion is a pure, artifact-only step.
# ---------------------------------------------------------------------------


def test_converter_purity_no_side_effects(tmp_path: Path) -> None:
    proposal = _make_proposal().proposal
    converter = HypothesisProposalConverter()
    spec = converter.to_hypothesis_specification(
        proposal,
        hypothesis_id="HYP_S5_CONVERT_001",
        hypothesis_version="1.0.0",
        author="S5-Audit",
        registered_at_utc=FIXED_TS,
        primary_horizon=5,
        parameter_config_json='{"window": 5}',
    )
    assert isinstance(spec, HypothesisSpecification)
    assert spec.hypothesis_id == "HYP_S5_CONVERT_001"
    assert spec.parent_hypothesis_id is None
    assert spec.primary_horizon == 5
    assert list(spec.target_horizons) == [1, 5]
    assert list(spec.feature_dependencies) == list(proposal.feature_dependencies)
    assert spec.invalidation_criteria == proposal.proposed_invalidation_criteria

    # Pure conversion: zero filesystem/registry mutation; proposal unchanged.
    assert list(tmp_path.rglob("*")) == []
    assert proposal.proposal_status == CandidateStatus.UNVALIDATED_PROPOSAL


def test_converter_refuses_non_unvalidated_proposal() -> None:
    proposal = _make_proposal().proposal
    non_unvalidated = proposal.model_copy(update={"proposal_status": CandidateStatus.REJECTED})
    converter = HypothesisProposalConverter()
    with pytest.raises(DataContractError, match="Refusing to convert"):
        converter.to_hypothesis_specification(
            non_unvalidated,
            hypothesis_id="HYP_S5_CONVERT_001",
            hypothesis_version="1.0.0",
            author="S5-Audit",
            registered_at_utc=FIXED_TS,
            primary_horizon=5,
            parameter_config_json="{}",
        )


def test_converter_fail_closed_on_bad_parameters() -> None:
    proposal = _make_proposal().proposal
    converter = HypothesisProposalConverter()
    kwargs = {
        "hypothesis_id": "HYP_S5_CONVERT_001",
        "hypothesis_version": "1.0.0",
        "author": "S5-Audit",
        "registered_at_utc": FIXED_TS,
    }
    with pytest.raises(DataContractError, match="primary_horizon"):
        converter.to_hypothesis_specification(
            proposal, **kwargs, primary_horizon=9, parameter_config_json="{}"
        )
    with pytest.raises(DataContractError, match="not valid JSON"):
        converter.to_hypothesis_specification(
            proposal, **kwargs, primary_horizon=5, parameter_config_json="{nope}"
        )
    with pytest.raises(DataContractError, match="deserialize to an object"):
        converter.to_hypothesis_specification(
            proposal, **kwargs, primary_horizon=5, parameter_config_json="[1, 2]"
        )


# ---------------------------------------------------------------------------
# Item 4: Proposal -> validation firewall (no path skips the converted spec).
# ---------------------------------------------------------------------------


def test_proposal_to_validation_firewall() -> None:
    proposal = _make_proposal().proposal
    # The AI proposal carries no ValidationReport-shaped fields: a report cannot
    # be fabricated from a proposal artifact.
    for field in ("decision_digest", "is_tradeable_alpha", "verdict"):
        assert field not in AIHypothesisProposal.model_fields, field
    # Only the human-gated converter bridges proposal -> HypothesisSpecification.
    converter = HypothesisProposalConverter()
    spec = converter.to_hypothesis_specification(
        proposal,
        hypothesis_id="HYP_S5_FIREWALL_001",
        hypothesis_version="1.0.0",
        author="S5-Audit",
        registered_at_utc=FIXED_TS,
        primary_horizon=5,
        parameter_config_json="{}",
    )
    # The firewall gate still refuses a disguised, non-UNVALIDATED lookalike.
    lookalike = proposal.model_copy(update={"proposal_status": CandidateStatus.REJECTED})
    with pytest.raises(DataContractError, match="Refusing to convert"):
        converter.to_hypothesis_specification(
            lookalike,
            hypothesis_id="HYP_S5_FIREWALL_001",
            hypothesis_version="1.0.0",
            author="S5-Audit",
            registered_at_utc=FIXED_TS,
            primary_horizon=5,
            parameter_config_json="{}",
        )
    assert spec.hypothesis_id == "HYP_S5_FIREWALL_001"


# ---------------------------------------------------------------------------
# Item 5: Feature discovery is isolated, causal, and non-tradeable.
# ---------------------------------------------------------------------------


def test_feature_discovery_deterministic_causal() -> None:
    engine = FeatureDiscoveryEngine()
    request = FeatureDiscoveryRequest(
        base_variables=("close", "volume"),
        target_phenomenon="short_term_flow",
        max_features=5,
        max_expression_depth=2,
    )
    proposals = engine.discover(request)
    proposals_again = engine.discover(request)
    assert len(proposals) > 0
    assert [p.feature_id for p in proposals] == [p.feature_id for p in proposals_again]
    for p in proposals:
        assert isinstance(p, AIFeatureProposal)
        assert p.feature_id.startswith("AI-FEAT-")
        assert p.is_strictly_causal is True
        assert p.lookahead_terms_detected == 0
        assert p.point_in_time_verified is True
        assert len(p.provenance_hash) == 64


def test_feature_proposal_is_not_an_implicit_pyarrow_table() -> None:
    engine = FeatureDiscoveryEngine()
    proposals = engine.discover(
        FeatureDiscoveryRequest(
            base_variables=("close",), target_phenomenon="short_term_flow", max_features=2
        )
    )
    assert len(proposals) > 0
    example = proposals[0]
    assert isinstance(example, AIFeatureProposal)
    assert not isinstance(example, pa.Table)
    # Seam 2: no implicit conversion bridge exists in the canonical runtime.
    for attr in ("to_pyarrow", "to_arrow", "as_table", "to_table"):
        assert not hasattr(example, attr), attr


def test_lookahead_expression_rejected_by_causal_validator() -> None:
    result = CausalAstValidator().validate_expression("close[t+5]", ("close",))
    assert result.point_in_time_verified is False
    assert result.lookahead_terms_detected >= 1
    assert any("lookahead" in v for v in result.violations)


# ---------------------------------------------------------------------------
# Item 6: Phase 4/5 research pipeline fail-closed + Phase 5 manifest seam.
# ---------------------------------------------------------------------------


def _research_hypothesis() -> HypothesisSpecification:
    return HypothesisSpecification(
        hypothesis_id="HYP_S5_RESEARCH_001",
        hypothesis_version="1.0.0",
        economic_rationale="S5 deterministic research contract.",
        target_symbol="ES.FUT",
        feature_dependencies=["vwap_std"],
        parameter_config_json='{"z_window": 20}',
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1, 5],
        primary_horizon=5,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.01"), min_hac_t_stat=Decimal("1.5")
        ),
        registered_at_utc="2026-09-08T00:00:00Z",
        author="S5-Audit",
    )


def _research_tables() -> Tuple[pa.Table, pa.Table]:
    num_bars = 60
    t0 = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)
    timestamps = [
        datetime.fromtimestamp(t0.timestamp() + i * 60, tz=timezone.utc) for i in range(num_bars)
    ]
    t_end = [
        datetime.fromtimestamp(t0.timestamp() + (i + 1) * 60, tz=timezone.utc)
        for i in range(num_bars)
    ]
    feat_vals = [Decimal(f"{10.0 + (i * 0.1):.4f}") for i in range(num_bars)]
    prices = [Decimal(f"{100.0 + (i * 0.5):.4f}") for i in range(num_bars)]
    features = pa.Table.from_pydict({"timestamp_utc": timestamps, "vwap_std": feat_vals})
    bars = pa.Table.from_pydict(
        {
            "timestamp_utc": timestamps,
            "bar_start_utc": timestamps,
            "bar_end_utc": t_end,
            "open": prices,
            "high": [p + Decimal("1.0") for p in prices],
            "low": [p - Decimal("1.0") for p in prices],
            "close": prices,
            "volume": [Decimal("1000") for _ in prices],
        }
    )
    return features, bars


def test_phase5_fail_closed_missing_feature(tmp_path: Path) -> None:
    features, bars = _research_tables()
    pipeline = AlphaResearchPipeline(
        manifest_engine=ResearchManifestEngine(manifests_dir=Path(tmp_path) / "manifests")
    )
    with pytest.raises(DataContractError, match="not found in features table"):
        pipeline.run_hypothesis_evaluation(
            features_table=features,
            bars_table=bars,
            feature_name="nonexistent_feature",
            hypothesis=_research_hypothesis(),
        )


def test_phase5_fail_closed_insufficient_bars(tmp_path: Path) -> None:
    features, bars = _research_tables()
    short_bars = bars.slice(0, 5)
    pipeline = AlphaResearchPipeline(
        manifest_engine=ResearchManifestEngine(manifests_dir=Path(tmp_path) / "manifests")
    )
    with pytest.raises(DataContractError, match="Insufficient bars"):
        pipeline.run_hypothesis_evaluation(
            features_table=features,
            bars_table=short_bars,
            feature_name="vwap_std",
            hypothesis=_research_hypothesis(),
        )


def test_phase5_fail_closed_oos_requires_search_record(tmp_path: Path) -> None:
    features, bars = _research_tables()
    pipeline = AlphaResearchPipeline(
        manifest_engine=ResearchManifestEngine(manifests_dir=Path(tmp_path) / "manifests")
    )
    with pytest.raises(DataContractError, match="ResearchSearchRecord is mandatory"):
        pipeline.run_hypothesis_evaluation(
            features_table=features,
            bars_table=bars,
            feature_name="vwap_std",
            hypothesis=_research_hypothesis(),
            evaluate_oos=True,
        )


def test_phase5_positive_run_is_deterministic_and_identity_preserving(tmp_path: Path) -> None:
    features, bars = _research_tables()
    hyp = _research_hypothesis()
    engine = ResearchManifestEngine(manifests_dir=Path(tmp_path) / "manifests")
    pipeline = AlphaResearchPipeline(manifest_engine=engine)
    m1, _, _ = pipeline.run_hypothesis_evaluation(
        features_table=features, bars_table=bars, feature_name="vwap_std", hypothesis=hyp
    )
    m2, _, _ = pipeline.run_hypothesis_evaluation(
        features_table=features, bars_table=bars, feature_name="vwap_std", hypothesis=hyp
    )
    assert m1.manifest_id == m2.manifest_id
    assert m1.input_feature_hashes == m2.input_feature_hashes
    assert m1.manifest_id.startswith(f"res_{hyp.hypothesis_id}_")
    assert m1.hypothesis_id == hyp.hypothesis_id


class _S5SeamActor:
    """Minimal actor placing one deterministic simulated order (test-local)."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.order_placed = False

    def on_bar(self, event: Any, runner: Any) -> None:
        if not self.order_placed:
            runner.submit_order(
                order_id="ORD-S5-SEAM-001",
                symbol=self.symbol,
                order_type=OrderType.MARKET,
                side="BUY",
                quantity=Decimal("2.0"),
            )
            self.order_placed = True

    def on_trade(self, event: Any, runner: Any) -> None:
        pass


def test_phase5_engine_manifest_carries_genuine_hypothesis_id() -> None:
    """Seam A resolved: the Phase 5 manifest carries the genuine hypothesis id."""
    hyp = _research_hypothesis()
    actor = _S5SeamActor(symbol="ES.FUT")
    config = BacktestEngineConfig(
        engine_id="BKT-S5-SEAM", symbol="ES.FUT", initial_cash=Decimal("100000.00")
    )
    runner = ACASHNativeBacktestEngine(config=config, strategy_actor=actor)
    t0_ns = 1768833000_000_000_000
    events = [
        BacktestMarketEvent(
            event_type=BacktestEventType.DEPTH_SNAPSHOT,
            symbol="ES.FUT",
            event_timestamp_ns=t0_ns,
            source_order_key="ES.FUT:DEPTH:0:snap1",
            message_rank=0,
            stream_id="DEPTH",
            row_sub_index=0,
            payload={
                "bids": [(Decimal("5000.00"), Decimal("10.0")), (Decimal("4999.00"), Decimal("20.0"))],
                "asks": [(Decimal("5001.00"), Decimal("10.0")), (Decimal("5002.00"), Decimal("20.0"))],
            },
        ),
    ]
    closes = [Decimal("5004.00"), Decimal("5007.00"), Decimal("5002.00")]
    bar_events = [
        BacktestMarketEvent(
            event_type=BacktestEventType.BAR,
            symbol="ES.FUT",
            event_timestamp_ns=t0_ns + (60_000_000_000 * (i + 1)),
            source_order_key=f"ES.FUT:BARS:{i + 1}",
            message_rank=10,
            stream_id="BARS",
            row_sub_index=0,
            payload={
                "open": closes[i] - Decimal("1.00"),
                "high": closes[i] + Decimal("2.00"),
                "low": closes[i] - Decimal("2.00"),
                "close": closes[i],
                "volume": Decimal("500.0"),
                "bar_index": i,
            },
        )
        for i in range(3)
    ]
    events = events + bar_events
    hyp_digest = calculate_hypothesis_spec_sha256(hyp)
    manifest, _, _ = runner.run_backtest(
        events=events,
        hypothesis_id=hyp.hypothesis_id,
        hypothesis_spec_sha256=hyp_digest,
        strategy_config_hash="0" * 64,
        pyproject_toml_sha256="0" * 64,
        git_commit_hash="a" * 40,
        periods_per_year=Decimal("252.0"),
        canonical_data_hashes=[hyp_digest],
    )
    # Truthful identity propagation (Seam A resolved): the engine now carries
    # the genuine upstream HypothesisSpecification.hypothesis_id, not a placeholder.
    assert manifest.hypothesis_id == hyp.hypothesis_id
    assert manifest.hypothesis_spec_sha256 == hyp_digest


# ---------------------------------------------------------------------------
# Item 7: Phase 6 statistical validation gate fail-closed paths.
# ---------------------------------------------------------------------------


def _phase6_call(
    gate: StatisticalValidationGate,
    hyp: HypothesisSpecification,
    *,
    trial_ledger: Optional[SearchTrialLedger] = None,
    out_of_sample_returns: Optional[List[float]] = None,
) -> ValidationReport:
    return gate.evaluate_strategy(
        strategy_id="S5-STR-001",
        hypothesis_id=hyp.hypothesis_id,
        hypothesis_spec=hyp,
        in_sample_returns=[0.001] * 20,
        trial_matrix_column_trial_ids=[],
        manifest_store={},
        trial_ledger=trial_ledger,
        out_of_sample_returns=out_of_sample_returns,
        perturbation_grid=None,
        fixed_created_timestamp_utc=FIXED_TS,
    )


def test_phase6_reject_missing_trial_ledger() -> None:
    gate = StatisticalValidationGate()
    report = _phase6_call(gate, _research_hypothesis(), trial_ledger=None)
    assert report.verdict == ValidationGateVerdict.REJECT_MISSING_TRIAL_LEDGER
    assert report.is_tradeable_alpha is False


def test_phase6_reject_missing_oos() -> None:
    gate = StatisticalValidationGate()
    ledged_hyp = _make_bundle_hypothesis()
    bundle_ledger = make_s5_bundle().ledger
    report = _phase6_call(gate, ledged_hyp, trial_ledger=bundle_ledger, out_of_sample_returns=None)
    assert report.verdict == ValidationGateVerdict.REJECT_MISSING_OOS_DATA
    assert report.is_tradeable_alpha is False


def test_phase6_reject_missing_perturbation_grid() -> None:
    gate = StatisticalValidationGate()
    ledged_hyp = _make_bundle_hypothesis()
    bundle_ledger = make_s5_bundle().ledger
    report = _phase6_call(
        gate, ledged_hyp, trial_ledger=bundle_ledger, out_of_sample_returns=[0.001] * 5
    )
    assert report.verdict == ValidationGateVerdict.REJECT_MISSING_PERTURBATION_GRID
    assert report.is_tradeable_alpha is False


def test_phase6_fail_closed_spec_binding() -> None:
    gate = StatisticalValidationGate()
    hyp = _research_hypothesis()
    with pytest.raises(DataContractError, match="Mandatory hypothesis_spec"):
        gate.evaluate_strategy(
            strategy_id="S5-STR-001",
            hypothesis_id="ANY",
            hypothesis_spec=None,  # type: ignore[arg-type]
            in_sample_returns=[0.001] * 20,
            trial_matrix_column_trial_ids=[],
            manifest_store={},
            fixed_created_timestamp_utc=FIXED_TS,
        )
    with pytest.raises(DataContractError, match="does not match"):
        gate.evaluate_strategy(
            strategy_id="S5-STR-001",
            hypothesis_id="S5-WRONG-ID",
            hypothesis_spec=hyp,
            in_sample_returns=[0.001] * 20,
            trial_matrix_column_trial_ids=[],
            manifest_store={},
            fixed_created_timestamp_utc=FIXED_TS,
        )


def test_phase6_reject_verdict_digest_is_deterministic() -> None:
    gate = StatisticalValidationGate()
    hyp = _research_hypothesis()
    r1 = _phase6_call(gate, hyp)
    r2 = _phase6_call(gate, hyp)
    assert r1.decision_digest == r2.decision_digest
    assert r1.validation_id == r2.validation_id


# ---------------------------------------------------------------------------
# Item 8: Phase 8.5 alpha qualification gate fail-closed + zero-capital dossier.
# ---------------------------------------------------------------------------


def test_phase85_mandatory_artifacts_fail_closed() -> None:
    bundle = make_s5_bundle()
    gate = AlphaQualificationGate()

    def _call(overrides: Dict[str, Any]) -> Any:
        args: Dict[str, Any] = {
            "alpha_id": "ALPHA_S5_1",
            "strategy_id": bundle.dossier.strategy_id,
            "hypothesis_spec": bundle.hypothesis,
            "trial_ledger": bundle.ledger,
            "validation_report": bundle.validation,
            "economic_decomposition": bundle.dossier.economic_decomposition,
            "fixed_created_timestamp_utc": FIXED_TS,
        }
        args.update(overrides)
        return gate.qualify_alpha(**args)

    with pytest.raises(DataContractError, match="alpha_id"):
        _call({"alpha_id": ""})
    with pytest.raises(DataContractError, match="Mandatory hypothesis_spec"):
        _call({"hypothesis_spec": None})
    with pytest.raises(DataContractError, match="Mandatory trial_ledger"):
        _call({"trial_ledger": None})
    with pytest.raises(DataContractError, match="Mandatory validation_report"):
        _call({"validation_report": None})
    with pytest.raises(DataContractError, match="Mandatory economic_decomposition"):
        _call({"economic_decomposition": None})


def test_phase85_lineage_mismatch_and_unsealed_ledger_fail_closed() -> None:
    bundle = make_s5_bundle()
    gate = AlphaQualificationGate()
    mismatch = bundle.validation.model_copy(update={"hypothesis_id": "HYP_TEST_9999"})
    with pytest.raises(DataContractError, match="Lineage mismatch"):
        gate.qualify_alpha(
            alpha_id="ALPHA_S5_2",
            strategy_id=bundle.dossier.strategy_id,
            hypothesis_spec=bundle.hypothesis,
            trial_ledger=bundle.ledger,
            validation_report=mismatch,
            economic_decomposition=bundle.dossier.economic_decomposition,
            fixed_created_timestamp_utc=FIXED_TS,
        )
    unsealed = SearchTrialLedger(
        ledger_id="LEDGER_0001",
        strategy_id=bundle.ledger.strategy_id,
        hypothesis_id=bundle.ledger.hypothesis_id,
        trials=bundle.ledger.trials,
        sharpe_space=SharpeSpace.ANNUAL,
        is_sealed=False,
        ledger_digest=None,
    )
    with pytest.raises(DataContractError, match="SEALED state before Alpha qualification"):
        gate.qualify_alpha(
            alpha_id="ALPHA_S5_3",
            strategy_id=bundle.dossier.strategy_id,
            hypothesis_spec=bundle.hypothesis,
            trial_ledger=unsealed,
            validation_report=bundle.validation,
            economic_decomposition=bundle.dossier.economic_decomposition,
            fixed_created_timestamp_utc=FIXED_TS,
        )


def test_phase85_qualification_seals_zero_capital_dossier() -> None:
    """A complete evidence chain produces a dossier with capital_authority $0.00."""
    bundle = make_s5_bundle()
    positive_econ = _make_econ(gross="25.00", spread="2.00", commissions="1.00", net="22.00", total="22.00")
    gate = AlphaQualificationGate()
    result = gate.qualify_alpha(
        alpha_id="ALPHA_S5_4",
        strategy_id=bundle.dossier.strategy_id,
        hypothesis_spec=bundle.hypothesis,
        trial_ledger=bundle.ledger,
        validation_report=bundle.validation,
        economic_decomposition=positive_econ,
        falsification_triggers=(),
        fixed_created_timestamp_utc=FIXED_TS,
    )
    assert result.is_qualified is True
    assert result.dossier is not None
    assert result.dossier.lifecycle_state == AlphaLifecycleState.RESEARCH_QUALIFIED
    assert result.dossier.capital_authority_usd == Decimal("0.00")


# ---------------------------------------------------------------------------
# Item 9: Section 33 report grounding is sealed-evidence-bound (fail-closed).
# ---------------------------------------------------------------------------


def test_reporting_sealed_row_grounded_happy_path() -> None:
    bundle = make_s5_bundle()
    generator = Section33ReportGenerator()
    verifier = EvidenceGroundingVerifier()
    report = generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    result = verifier.verify_report(
        report.report_markdown, bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis
    )
    assert result.is_grounded
    assert result.report_sha256 == report.report_sha256
    assert result.trial_ledger_digest == bundle.ledger.ledger_digest
    assert result.validation_report_decision_digest == bundle.validation.decision_digest
    assert result.dossier_digest == bundle.dossier.dossier_digest
    assert "| In-Sample Sharpe | 1.8 |" in report.report_markdown
    assert "| Out-of-Sample Sharpe | 0.95 |" in report.report_markdown


def test_reporting_tampered_claim_rejects() -> None:
    bundle = make_s5_bundle()
    verifier = EvidenceGroundingVerifier()
    with pytest.raises(DataContractError, match="deviates"):
        verifier.verify_report(
            "| In-Sample Sharpe | 9.9 |", bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis
        )


def test_reporting_fabricated_unregistered_claim_rejects() -> None:
    bundle = make_s5_bundle()
    verifier = EvidenceGroundingVerifier()
    with pytest.raises(DataContractError, match="profit factor"):
        verifier.verify_report(
            "| Profit Factor | 1.29 |", bundle.dossier, bundle.validation, bundle.ledger, bundle.hypothesis
        )


def test_reporting_unsealed_ledger_rejects(tmp_path: Path) -> None:
    bundle = make_s5_bundle()
    generator = Section33ReportGenerator()
    unsealed = SearchTrialLedger(
        ledger_id="LEDGER_0001",
        strategy_id=bundle.ledger.strategy_id,
        hypothesis_id=bundle.ledger.hypothesis_id,
        trials=bundle.ledger.trials,
        sharpe_space=SharpeSpace.ANNUAL,
        is_sealed=False,
        ledger_digest=None,
    )
    with pytest.raises(DataContractError, match="SEALED"):
        generator.generate(bundle.hypothesis, unsealed, bundle.validation, bundle.dossier)


def test_reporting_dossier_digest_tamper_rejects() -> None:
    bundle = make_s5_bundle()
    tampered = bundle.dossier.model_copy(update={"dossier_digest": "0" * 64})
    with pytest.raises(DataContractError, match="Tampered AlphaQualificationDossier"):
        validate_evidence_chain(tampered, bundle.validation, bundle.ledger, bundle.hypothesis)


def test_reporting_missing_metrics_omitted_never_fabricated() -> None:
    bundle = make_s5_bundle()
    generator = Section33ReportGenerator()
    report = generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    for metric in ("Sortino", "Max Drawdown", "Calmar", "Profit Factor", "Friction Sensitivity Matrix"):
        assert f"| {metric} | {OMITTED_MARKER} |" in report.report_markdown, metric


def test_reporting_byte_exact_determinism() -> None:
    bundle = make_s5_bundle()
    generator = Section33ReportGenerator()
    r1 = generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    r2 = generator.generate(bundle.hypothesis, bundle.ledger, bundle.validation, bundle.dossier)
    assert isinstance(r1, Section33Report)
    assert r1.report_markdown == r2.report_markdown
    assert r1.report_sha256 == r2.report_sha256


# ---------------------------------------------------------------------------
# Item 10: Determinism (prompt template golden hash; fixed-clock proposals).
# ---------------------------------------------------------------------------


def test_golden_prompt_template_sha256() -> None:
    canonical_json = json.dumps(USER_PROMPT_TEMPLATE, sort_keys=True, separators=(",", ":"), default=str)
    assert PROMPT_TEMPLATE_SHA256 == hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def test_assistant_fixed_clock_proposal_determinism() -> None:
    p1 = _make_proposal()
    p2 = _make_proposal()
    assert p1.proposal.compute_canonical_digest() == p2.proposal.compute_canonical_digest()
    assert p1.proposal.raw_response_sha256 == p2.proposal.raw_response_sha256
    assert p1.proposal.economic_rationale == p2.proposal.economic_rationale
    assert p1.usage == p2.usage
    assert p1.budget.tokens_consumed_total == p2.budget.tokens_consumed_total
    assert p1.budget.run_digest == p2.budget.run_digest


# ---------------------------------------------------------------------------
# Item 11: Static authority boundary (no trading/execution/gate imports).
# ---------------------------------------------------------------------------


def _ai_module_paths() -> List[Path]:
    from acash.research import ai as ai_pkg

    root = Path(ai_pkg.__file__).parent
    paths: List[Path] = []
    for sub in ("provider", "hypothesis", "features"):
        paths.extend((root / sub).glob("*.py"))
    # provider/httpx_client.py is the separately-authorized HTTP-capable provider;
    # it is the sanctioned network path and is EXCLUDED from the zero-network scan.
    return sorted(p for p in paths if p.name != "httpx_client.py")


def _assert_no_forbidden_imports(src_text: str) -> None:
    tree = ast.parse(src_text)
    banned_prefixed: Tuple[str, ...] = (
        "acash.execution",
        "acash.portfolio",
        "acash.runtime",
        "acash.backtest",
        "acash.risk",
        "acash.data",
        "MetaTrader5",
        "mt5",
        "httpx",
        "requests",
        "socket",
        "numpy",
        "pandas",
    )
    imported_modules: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
    for mod in imported_modules:
        assert not any(mod == banned or mod.startswith(banned + ".") for banned in banned_prefixed), mod


def _code_without_strings_and_comments(src_text: str) -> str:
    """Return the runnable token stream minus strings and comments."""
    import io
    import tokenize

    tokens: List[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(src_text).readline):
        if tok.type in (
            tokenize.COMMENT,
            tokenize.STRING,
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENCODING,
        ):
            continue
        tokens.append(tok.string)
    return " ".join(tokens)


def test_ai_provider_hypothesis_features_import_firewall() -> None:
    for path in _ai_module_paths():
        src = path.read_text(encoding="utf-8")
        _assert_no_forbidden_imports(src)
        # HYP_003 may appear only as a negative declaration inside docstrings
        # (e.g., the assistant's "NEVER creates HYP_003"); it must never be a
        # runtime identifier, string constant, or macro token in executable code.
        assert "HYP_003" not in _code_without_strings_and_comments(src), path


def test_mock_provider_module_is_zero_network() -> None:
    from acash.research.ai.provider import mock as _mock

    src = Path(_mock.__file__).read_text(encoding="utf-8")
    assert "httpx" not in src
    assert "requests" not in src
    assert "socket" not in src


# ---------------------------------------------------------------------------
# Item 12: Runtime wiring is capability-only (no consumers outside the package).
# ---------------------------------------------------------------------------


def _acash_src_files() -> List[Path]:
    import acash as acash_pkg

    return sorted(Path(acash_pkg.__file__).parent.rglob("*.py"))


def test_runtime_wiring_capability_only_packaging() -> None:
    from acash.research import ai as ai_pkg

    ai_root = Path(ai_pkg.__file__).parent.resolve()
    offenders: List[Tuple[str, str]] = []
    for path in _acash_src_files():
        text = path.read_text(encoding="utf-8")
        for token in ("acash.research.ai.provider", "acash.research.ai.hypothesis"):
            if token in text and not path.resolve().is_relative_to(ai_root):
                offenders.append((str(path), token))
    assert offenders == []