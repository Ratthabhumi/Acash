"""Hypothesis assistant tests.

The assistant must ALWAYS produce an ``AIHypothesisProposal`` stamped
``UNVALIDATED_PROPOSAL`` with full provenance, must propagate G-4 usage, and
must never touch gates, trading, execution, or capital.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json

import pytest

from acash.research.ai.enums import CandidateStatus
from acash.research.ai.hypothesis.assistant import AIHypothesisAssistant
from acash.research.ai.hypothesis.prompts import PROMPT_TEMPLATE_SHA256
from acash.research.ai.provider.base import (
    BudgetPolicy,
    InferenceBudgetError,
    InvalidProviderResponseError,
    LLMGenerationConfig,
    RunBudgetSession,
)
from acash.research.ai.provider.mock import MockLLMProvider

VALID_COMPLETION: str = json.dumps(
    {
        "economic_rationale": "Opening volume surge drives directional trend continuation in the morning session.",
        "market_microstructure_mechanism": "Opening cross auction order unbundling creates persistent inventory imbalance.",
        "invalidation_conditions": ["Rank IC < 0.02"],
        "target_symbol": "NQ",
        "target_timeframe": "M5",
        "feature_dependencies": ["close", "ema_fast"],
        "expected_direction": "LONG",
        "target_horizons": [1, 6],
        "proposed_invalidation_criteria": {
            "min_in_sample_rank_ic": "0.025",
            "min_hac_t_stat": "2.00",
            "max_feature_autocorrelation": "0.98",
            "min_cost_adjusted_spread_ratio": "1.50",
        },
    }
)


def _fixed_clock() -> datetime:
    return datetime(2026, 9, 8, 13, 0, 0, tzinfo=timezone.utc)


def _policy() -> BudgetPolicy:
    return BudgetPolicy(
        per_request_max_tokens=16_384,
        per_request_warning_tokens=12_288,
        per_run_max_tokens=100_000,
        per_run_warning_tokens=80_000,
    )


def test_assistant_output_is_always_unvalidated_proposal() -> None:
    provider = MockLLMProvider(completion=VALID_COMPLETION, clock=_fixed_clock)
    assistant = AIHypothesisAssistant(provider, clock=_fixed_clock)
    result = assistant.generate_hypothesis(
        symbol="NQ",
        timeframe="M5",
        economic_context="Opening session momentum research",
    )
    assert result.proposal.proposal_status == CandidateStatus.UNVALIDATED_PROPOSAL
    assert result.proposal.target_symbol == "NQ"
    assert result.proposal.target_timeframe == "M5"
    assert result.proposal.expected_direction.value == "LONG"


def test_assistant_preserves_provenance() -> None:
    provider = MockLLMProvider(completion=VALID_COMPLETION, clock=_fixed_clock)
    assistant = AIHypothesisAssistant(
        provider,
        config=LLMGenerationConfig(temperature=Decimal("0.3"), seed=7),
        clock=_fixed_clock,
    )
    result = assistant.generate_hypothesis(
        symbol="ES",
        timeframe="M15",
        economic_context="Slow drift accumulation",
        source_metadata_id="SRC-0011223344556677",
    )
    proposal = result.proposal
    assert proposal.llm_provider == provider.provider_name
    assert proposal.llm_model_id == provider.model_id
    assert proposal.prompt_template_sha256 == PROMPT_TEMPLATE_SHA256
    assert proposal.temperature == Decimal("0.3")
    assert proposal.seed == 7
    assert proposal.source_metadata_id == "SRC-0011223344556677"
    assert proposal.raw_response_sha256
    assert proposal.proposal_id.startswith("AI-HYP-")


def test_assistant_propagates_g4_usage() -> None:
    provider = MockLLMProvider(completion=VALID_COMPLETION, clock=_fixed_clock)
    assistant = AIHypothesisAssistant(provider, clock=_fixed_clock)
    session = RunBudgetSession(_policy())
    result = assistant.generate_hypothesis(
        symbol="NQ",
        timeframe="M5",
        economic_context="Opening session research",
        budget=session,
    )
    assert result.usage.total_tokens == 96
    assert session.tokens_consumed_total == 96
    assert session.request_count == 1
    assert result.budget.tokens_consumed_total == 96


def test_assistant_rejects_malformed_provider_output() -> None:
    provider = MockLLMProvider(completion="<not-json>", clock=_fixed_clock)
    assistant = AIHypothesisAssistant(provider, clock=_fixed_clock)
    with pytest.raises(InvalidProviderResponseError):
        assistant.generate_hypothesis(
            symbol="NQ",
            timeframe="M5",
            economic_context="Opening session research",
        )


def test_assistant_rejects_invalid_expected_direction() -> None:
    bad = json.loads(VALID_COMPLETION)
    bad["expected_direction"] = "UP"
    provider = MockLLMProvider(completion=json.dumps(bad), clock=_fixed_clock)
    assistant = AIHypothesisAssistant(provider, clock=_fixed_clock)
    with pytest.raises(InvalidProviderResponseError):
        assistant.generate_hypothesis(
            symbol="NQ",
            timeframe="M5",
            economic_context="Opening session research",
        )


def test_assistant_rejects_missing_required_keys() -> None:
    bad = json.loads(VALID_COMPLETION)
    del bad["target_horizons"]
    provider = MockLLMProvider(completion=json.dumps(bad), clock=_fixed_clock)
    assistant = AIHypothesisAssistant(provider, clock=_fixed_clock)
    with pytest.raises(InvalidProviderResponseError):
        assistant.generate_hypothesis(
            symbol="NQ",
            timeframe="M5",
            economic_context="Opening session research",
        )


def test_assistant_budget_precheck_blocks_before_dispatch() -> None:
    provider = MockLLMProvider(completion=VALID_COMPLETION, clock=_fixed_clock)
    assistant = AIHypothesisAssistant(
        provider,
        config=LLMGenerationConfig(max_tokens=16_384),
        clock=_fixed_clock,
    )
    tight = BudgetPolicy(
        per_request_max_tokens=100,
        per_request_warning_tokens=80,
        per_run_max_tokens=100_000,
        per_run_warning_tokens=80_000,
    )
    session = RunBudgetSession(tight)
    with pytest.raises(InferenceBudgetError):
        assistant.generate_hypothesis(
            symbol="NQ",
            timeframe="M5",
            economic_context="x" * 2000,
            budget=session,
        )
    assert session.request_count == 0
    assert session.tokens_consumed_total == 0