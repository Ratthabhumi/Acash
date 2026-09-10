"""HTTP provider G-4 tests.

All network behavior is exercised through ``httpx.MockTransport``; no real
network I/O is possible. Covers timeout, retries (429/502/503), fail-closed,
secret isolation, token ceiling, warning thresholds, run/session ceiling, and
the no-request-when-pre-check-fails guarantee.
"""

from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from acash.research.ai.provider.base import (
    BudgetPolicy,
    InferenceBudgetError,
    InferenceProviderError,
    InvalidProviderResponseError,
    LLMGenerationConfig,
    RunBudgetSession,
)
from acash.research.ai.provider.httpx_client import HttpxLLMProvider

ENDPOINT = "https://llm.example.com/v1/chat/completions"
MODEL = "test-model"
PROMPT = "Please draft a hypothesis for NQ M5 opening momentum."


def _ok_usage_response(total: int, prompt: int, completion: int) -> dict[str, object]:
    return {
        "choices": [{"message": {"role": "assistant", "content": "drafted content"}}],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        },
    }


def _fixed_clock() -> datetime:
    return datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)


def _policy() -> BudgetPolicy:
    return BudgetPolicy(
        per_request_max_tokens=10_000,
        per_request_warning_tokens=8_000,
        per_run_max_tokens=20_000,
        per_run_warning_tokens=16_000,
    )


def _provider(
    transport: httpx.MockTransport,
    *,
    api_key: str = "test-secret-key-123",
    max_retries: int = 3,
    backoff: tuple[float, ...] = (0.0, 0.0, 0.0),
    input_price_per_1k_tokens: Decimal | None = None,
    output_price_per_1k_tokens: Decimal | None = None,
) -> HttpxLLMProvider:
    return HttpxLLMProvider(
        model_id=MODEL,
        endpoint_url=ENDPOINT,
        api_key=api_key,
        connect_timeout_seconds=30.0,
        read_timeout_seconds=60.0,
        max_network_retries=max_retries,
        retry_backoff_seconds=backoff,
        input_price_per_1k_tokens=input_price_per_1k_tokens,
        output_price_per_1k_tokens=output_price_per_1k_tokens,
        transport=transport,
        clock=_fixed_clock,
    )


def test_success_accounts_usage_and_returns_content() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=_ok_usage_response(30, 10, 20))

    provider = _provider(httpx.MockTransport(handler))
    session = RunBudgetSession(_policy())
    with provider:
        response = provider.generate(LLMGenerationConfig(), PROMPT, session)
    assert response.raw_response == "drafted content"
    assert response.usage.total_tokens == 30
    assert response.retry_count == 0
    assert response.attempt_count == 1
    assert session.tokens_consumed_total == 30
    assert session.request_count == 1
    assert len(calls) == 1


def test_cost_recorded_only_when_pricing_metadata_configured() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ok_usage_response(3_000, 1_000, 2_000))

    cost_policy = BudgetPolicy(
        per_request_max_tokens=10_000,
        per_request_warning_tokens=8_000,
        per_run_max_tokens=20_000,
        per_run_warning_tokens=16_000,
    )
    unpriced = _provider(httpx.MockTransport(handler))
    priced = _provider(
        httpx.MockTransport(handler),
        input_price_per_1k_tokens=Decimal("0.001"),
        output_price_per_1k_tokens=Decimal("0.002"),
    )
    session = RunBudgetSession(cost_policy)
    with unpriced:
        raw = unpriced.generate(LLMGenerationConfig(), PROMPT, session)
    assert raw.usage.inference_cost_usd is None
    assert raw.usage.pricing_unavailable is True
    with priced:
        priced_resp = priced.generate(LLMGenerationConfig(), PROMPT, session)
    assert priced_resp.usage.inference_cost_usd == Decimal("0.005")
    assert priced_resp.usage.pricing_unavailable is False


def test_timeout_fails_closed_and_consumes_no_budget() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out", request=request)

    provider = _provider(httpx.MockTransport(handler))
    session = RunBudgetSession(_policy())
    with provider:
        with pytest.raises(InferenceProviderError):
            provider.generate(LLMGenerationConfig(), PROMPT, session)
    assert session.tokens_consumed_total == 0


def test_retriable_status_retries_then_succeeds() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503, text="service unavailable")
        return httpx.Response(200, json=_ok_usage_response(30, 10, 20))

    provider = _provider(httpx.MockTransport(handler))
    session = RunBudgetSession(_policy())
    with provider:
        response = provider.generate(LLMGenerationConfig(), PROMPT, session)
    assert response.retry_count == 1
    assert response.attempt_count == 2
    assert session.tokens_consumed_total == 30
    assert len(calls) == 2


def test_non_retriable_status_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="oops")

    provider = _provider(httpx.MockTransport(handler))
    session = RunBudgetSession(_policy())
    with provider:
        with pytest.raises(InferenceProviderError):
            provider.generate(LLMGenerationConfig(), PROMPT, session)
    assert session.tokens_consumed_total == 0


def test_retries_bounded_after_429_exhaustion() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, text="rate limited")

    provider = _provider(
        httpx.MockTransport(handler),
        max_retries=2,
        backoff=(0.0, 0.0, 0.0),
    )
    session = RunBudgetSession(_policy())
    with provider:
        with pytest.raises(InferenceProviderError):
            provider.generate(LLMGenerationConfig(), PROMPT, session)
    assert len(calls) == 3


def test_pre_check_failure_dispatches_no_network_request() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=_ok_usage_response(30, 10, 20))

    provider = _provider(httpx.MockTransport(handler))
    tight = BudgetPolicy(
        per_request_max_tokens=100,
        per_request_warning_tokens=80,
        per_run_max_tokens=5_000,
        per_run_warning_tokens=4_000,
    )
    session = RunBudgetSession(tight)
    with provider:
        with pytest.raises(InferenceBudgetError):
            provider.generate(LLMGenerationConfig(max_tokens=99), "x" * 400, session)
    assert calls == []


def test_per_run_ceiling_enforced_across_requests() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ok_usage_response(3_000, 1_000, 2_000))

    provider = _provider(httpx.MockTransport(handler))
    policy = BudgetPolicy(
        per_request_max_tokens=10_000,
        per_request_warning_tokens=8_000,
        per_run_max_tokens=5_000,
        per_run_warning_tokens=2_000,
    )
    session = RunBudgetSession(policy)
    config = LLMGenerationConfig(max_tokens=1_500)
    with provider:
        first = provider.generate(config, PROMPT, session)
        assert first.usage.total_tokens == 3_000
        assert any(w.startswith("PER_RUN_WARNING=") for w in session.snapshot().budget_warnings)
        with pytest.raises(InferenceBudgetError):
            provider.generate(config, PROMPT, session)


def test_secret_key_not_leaked_in_repr_or_errors() -> None:
    secret = "super-secret-api-key-value-9911"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server failure")

    provider = _provider(httpx.MockTransport(handler), api_key=secret)
    assert secret not in repr(provider)
    session = RunBudgetSession(_policy())
    with provider:
        with pytest.raises(InferenceProviderError) as exc:
            provider.generate(LLMGenerationConfig(), PROMPT, session)
    assert secret not in str(exc.value)


def test_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACASH_AI_API_KEY", "env-secret-77")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer env-secret-77"
        return httpx.Response(200, json=_ok_usage_response(30, 10, 20))

    provider = HttpxLLMProvider(
        model_id=MODEL,
        endpoint_url=ENDPOINT,
        connect_timeout_seconds=30.0,
        read_timeout_seconds=60.0,
        retry_backoff_seconds=(0.0, 0.0, 0.0),
        transport=httpx.MockTransport(handler),
        clock=_fixed_clock,
    )
    session = RunBudgetSession(_policy())
    with provider:
        response = provider.generate(LLMGenerationConfig(), PROMPT, session)
    assert response.usage.total_tokens == 30


def test_malformed_response_raises_datacontract_semantics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<not-json>")

    provider = _provider(httpx.MockTransport(handler))
    session = RunBudgetSession(_policy())
    with provider:
        with pytest.raises(InvalidProviderResponseError):
            provider.generate(LLMGenerationConfig(), PROMPT, session)
    assert session.tokens_consumed_total == 0
    assert session.request_count == 0