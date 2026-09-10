"""G-4 provider foundation tests: interface contract, usage, guard semantics.

Offline. Verifies the human-frozen G-4 numeric defaults, fail-closed budget
guard, deterministic serialization, and canonical observability projection.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from acash.research.ai.provider.base import (
    BudgetPolicy,
    InferenceBudgetError,
    LLMGenerationConfig,
    RunBudgetSession,
    TokenUsage,
    estimate_prompt_tokens,
)

FROZEN_PER_REQUEST_MAX = 16_384
FROZEN_PER_REQUEST_WARNING = 12_288
FROZEN_PER_RUN_MAX = 100_000
FROZEN_PER_RUN_WARNING = 80_000


def test_budget_policy_defaults_are_human_frozen_values() -> None:
    policy = BudgetPolicy()
    assert policy.per_request_max_tokens == FROZEN_PER_REQUEST_MAX
    assert policy.per_request_warning_tokens == FROZEN_PER_REQUEST_WARNING
    assert policy.per_run_max_tokens == FROZEN_PER_RUN_MAX
    assert policy.per_run_warning_tokens == FROZEN_PER_RUN_WARNING


def test_budget_policy_rejects_warning_above_ceiling() -> None:
    with pytest.raises(InferenceBudgetError):
        BudgetPolicy(
            per_request_max_tokens=100,
            per_request_warning_tokens=150,
            per_run_max_tokens=1000,
            per_run_warning_tokens=200,
        )


def test_generation_config_bounds_max_tokens_by_per_request_ceiling() -> None:
    LLMGenerationConfig(max_tokens=FROZEN_PER_REQUEST_MAX)
    with pytest.raises(ValidationError):
        LLMGenerationConfig(max_tokens=FROZEN_PER_REQUEST_MAX + 1)


def test_pre_dispatch_fails_closed_on_per_request_ceiling() -> None:
    policy = BudgetPolicy(
        per_request_max_tokens=100,
        per_request_warning_tokens=80,
        per_run_max_tokens=100_000,
        per_run_warning_tokens=80_000,
    )
    session = RunBudgetSession(policy)
    with pytest.raises(InferenceBudgetError):
        session.assert_can_dispatch(200, 0)
    assert session.request_count == 0
    assert session.tokens_consumed_total == 0


def test_pre_dispatch_fails_closed_on_per_run_ceiling() -> None:
    policy = BudgetPolicy(
        per_request_max_tokens=1_000,
        per_request_warning_tokens=900,
        per_run_max_tokens=500,
        per_run_warning_tokens=400,
    )
    session = RunBudgetSession(policy)
    session.record_usage(TokenUsage(input_tokens=100, output_tokens=100, total_tokens=200))
    session.record_usage(TokenUsage(input_tokens=100, output_tokens=100, total_tokens=200))
    with pytest.raises(InferenceBudgetError):
        session.assert_can_dispatch(100, 200)


def test_record_usage_fails_closed_on_per_request_ceiling() -> None:
    session = RunBudgetSession(
        BudgetPolicy(
            per_request_max_tokens=100,
            per_request_warning_tokens=90,
            per_run_max_tokens=1_000,
            per_run_warning_tokens=900,
        )
    )
    with pytest.raises(InferenceBudgetError):
        session.record_usage(TokenUsage(input_tokens=60, output_tokens=60, total_tokens=120))


def test_record_usage_accumulates_and_emits_warnings() -> None:
    policy = BudgetPolicy(
        per_request_max_tokens=100,
        per_request_warning_tokens=80,
        per_run_max_tokens=1_000,
        per_run_warning_tokens=900,
    )
    session = RunBudgetSession(policy)
    snapshot = session.record_usage(
        TokenUsage(input_tokens=40, output_tokens=50, total_tokens=90)
    )
    assert session.tokens_consumed_total == 90
    assert session.request_count == 1
    assert snapshot.tokens_consumed_total == 90
    assert any(w.startswith("PER_REQUEST_WARNING=") for w in snapshot.budget_warnings)


def test_snapshot_digest_is_deterministic() -> None:
    policy = BudgetPolicy(
        per_request_max_tokens=1_000,
        per_request_warning_tokens=900,
        per_run_max_tokens=5_000,
        per_run_warning_tokens=4_000,
    )
    first = RunBudgetSession(policy)
    second = RunBudgetSession(policy)
    assert first.snapshot().run_digest == second.snapshot().run_digest
    first.record_usage(TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30))
    second.record_usage(TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30))
    assert first.snapshot().run_digest == second.snapshot().run_digest
    assert first.snapshot().run_digest != RunBudgetSession(policy).snapshot().run_digest


def test_token_usage_observability_projection() -> None:
    usage = TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30)
    metrics = usage.to_observability_metrics()
    assert metrics["tokens_consumed_total"] == 30
    assert metrics["input_tokens"] == 10
    assert metrics["output_tokens"] == 20
    assert metrics["inference_cost_usd"] is None


def test_token_usage_cost_only_when_pricing_provided() -> None:
    priced = TokenUsage(
        input_tokens=1_000,
        output_tokens=2_000,
        total_tokens=3_000,
        inference_cost_usd=Decimal("0.01"),
        pricing_unavailable=False,
    )
    assert priced.inference_cost_usd == Decimal("0.01")
    unpriced = TokenUsage(input_tokens=1_000, output_tokens=2_000, total_tokens=3_000)
    assert unpriced.inference_cost_usd is None
    assert unpriced.pricing_unavailable is True


def test_token_usage_deterministic_serialization() -> None:
    left = TokenUsage(input_tokens=7, output_tokens=13, total_tokens=20)
    right = TokenUsage(input_tokens=7, output_tokens=13, total_tokens=20)
    assert left.model_dump_json() == right.model_dump_json()
    assert left.model_dump() == right.model_dump()


def test_estimate_prompt_tokens_deterministic_and_positive() -> None:
    text = "deterministic prompt payload used for the pre-dispatch estimate"
    assert estimate_prompt_tokens(text) == estimate_prompt_tokens(text)
    assert estimate_prompt_tokens("") == 1
    assert estimate_prompt_tokens(text) >= 1


def test_llm_generation_config_bounded_fields() -> None:
    config = LLMGenerationConfig()
    assert config.temperature == Decimal("0.0")
    assert config.top_p == Decimal("1.0")
    with pytest.raises(ValidationError):
        LLMGenerationConfig(temperature=Decimal("2.1"))
    with pytest.raises(ValidationError):
        LLMGenerationConfig(top_p=Decimal("0.0"))