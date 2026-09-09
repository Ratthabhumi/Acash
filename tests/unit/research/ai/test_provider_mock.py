"""Mock provider G-4 tests: zero network, determinism, budget semantics.

The mock must never touch a network, must be deterministic across repeated
invocations, must support warning/ceiling budget tests, and must never fabricate
a monetary cost.
"""

from datetime import datetime, timezone

import pytest

from acash.research.ai.provider.base import (
    BudgetPolicy,
    InferenceBudgetError,
    LLMGenerationConfig,
    RunBudgetSession,
    TokenUsage,
)
from acash.research.ai.provider.mock import MOCK_MODEL_ID, MOCK_PROVIDER_NAME, MockLLMProvider


def _fixed_clock() -> datetime:
    return datetime(2026, 9, 8, 12, 30, 0, tzinfo=timezone.utc)


def _policy() -> BudgetPolicy:
    return BudgetPolicy(
        per_request_max_tokens=10_000,
        per_request_warning_tokens=8_000,
        per_run_max_tokens=20_000,
        per_run_warning_tokens=16_000,
    )


def test_mock_reports_provider_coordinates() -> None:
    provider = MockLLMProvider()
    assert provider.provider_name == MOCK_PROVIDER_NAME
    assert provider.model_id == MOCK_MODEL_ID


def test_mock_is_deterministic_across_repeated_invocation() -> None:
    provider = MockLLMProvider(clock=_fixed_clock)
    session_a = RunBudgetSession(_policy())
    session_b = RunBudgetSession(_policy())
    config = LLMGenerationConfig(seed=42)
    with provider:
        first = provider.generate(config, "prompt a", session_a)
        second = provider.generate(config, "prompt a", session_b)
    assert first.raw_response == second.raw_response
    assert first.usage == second.usage
    assert first.completed_at_utc == second.completed_at_utc
    assert session_a.snapshot().run_digest == session_b.snapshot().run_digest


def test_mock_produces_no_real_cost() -> None:
    provider = MockLLMProvider()
    session = RunBudgetSession(_policy())
    with provider:
        response = provider.generate(LLMGenerationConfig(), "prompt", session)
    assert response.usage.inference_cost_usd is None
    assert response.usage.pricing_unavailable is True
    assert response.provider_name == MOCK_PROVIDER_NAME


def test_mock_supports_warning_threshold() -> None:
    usage = TokenUsage(input_tokens=850, output_tokens=0, total_tokens=850)
    provider = MockLLMProvider(usage=usage, clock=_fixed_clock)
    warning_policy = BudgetPolicy(
        per_request_max_tokens=10_000,
        per_request_warning_tokens=800,
        per_run_max_tokens=20_000,
        per_run_warning_tokens=16_000,
    )
    session = RunBudgetSession(warning_policy)
    with provider:
        response = provider.generate(LLMGenerationConfig(), "prompt", session)
    assert any(w.startswith("PER_REQUEST_WARNING=") for w in response.budget_warnings)
    assert any(w.startswith("PER_REQUEST_WARNING=") for w in session.snapshot().budget_warnings)


def test_mock_ceiling_fails_closed() -> None:
    usage = TokenUsage(input_tokens=1_500, output_tokens=0, total_tokens=1_500)
    provider = MockLLMProvider(usage=usage)
    tight = BudgetPolicy(
        per_request_max_tokens=1_000,
        per_request_warning_tokens=900,
        per_run_max_tokens=5_000,
        per_run_warning_tokens=4_000,
    )
    session = RunBudgetSession(tight)
    with provider:
        with pytest.raises(InferenceBudgetError):
            provider.generate(LLMGenerationConfig(), "prompt", session)
    assert session.tokens_consumed_total == 0


def test_mock_pre_dispatch_guard_blocks_known_over_budget() -> None:
    provider = MockLLMProvider()
    tight = BudgetPolicy(
        per_request_max_tokens=50,
        per_request_warning_tokens=40,
        per_run_max_tokens=5_000,
        per_run_warning_tokens=4_000,
    )
    session = RunBudgetSession(tight)
    with provider:
        with pytest.raises(InferenceBudgetError):
            provider.generate(LLMGenerationConfig(max_tokens=60), "prompt", session)
    assert session.request_count == 0


def test_mock_usage_is_test_specified_and_deterministic() -> None:
    usage = TokenUsage(input_tokens=100, output_tokens=200, total_tokens=300)
    provider = MockLLMProvider(usage=usage)
    session = RunBudgetSession(_policy())
    with provider:
        response = provider.generate(LLMGenerationConfig(), "prompt", session)
    assert response.usage == usage
    assert response.attempt_count == 1
    assert response.retry_count == 0