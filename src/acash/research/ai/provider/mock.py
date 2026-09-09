"""Phase 14 S1 deterministic zero-network Mock LLM provider.

Implements ``ILLMProvider`` with:
- zero external network (mock transport-free, pure in-memory)
- deterministic completion and deterministic token usage
- full G-4 budget guard support (warning/ceiling behavior testable offline)
- no cost fabrication: ``inference_cost_usd`` is never produced
- no trading/execution/capital/gate access

The mock never contacts any external service and never consumes real budget.
"""

from datetime import datetime, timezone
from typing import Callable, Optional

from acash.research.ai.provider.base import (
    ILLMProvider,
    LLMGenerationConfig,
    ProviderResponse,
    RunBudgetSession,
    TokenUsage,
    estimate_prompt_tokens,
)

DEFAULT_MOCK_COMPLETION: str = (
    "MOCK COMPLETION: Opening-volume inventory imbalance hypothesis drafted."
)
MOCK_PROVIDER_NAME: str = "mock"
MOCK_MODEL_ID: str = "mock-model-v1"


class MockLLMProvider:
    """Deterministic offline provider used for tests and offline replay.

    Token usage is test-specified or deterministic defaults; the mock never
    fabricates a monetary cost.
    """

    def __init__(
        self,
        *,
        provider_name: str = MOCK_PROVIDER_NAME,
        model_id: str = MOCK_MODEL_ID,
        completion: Optional[str] = None,
        usage: Optional[TokenUsage] = None,
        latency_ms: int = 0,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.provider_name: str = provider_name
        self.model_id: str = model_id
        self._completion: str = completion if completion is not None else DEFAULT_MOCK_COMPLETION
        self._usage: TokenUsage = usage if usage is not None else TokenUsage(
            input_tokens=32,
            output_tokens=64,
            total_tokens=96,
        )
        self._latency_ms: int = max(0, latency_ms)
        self._clock: Callable[[], datetime] = (
            clock if clock is not None else lambda: datetime.now(timezone.utc)
        )

    def __repr__(self) -> str:
        return f"MockLLMProvider(model_id={self.model_id!r}, provider={self.provider_name!r})"

    def __enter__(self) -> "MockLLMProvider":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def generate(
        self,
        config: LLMGenerationConfig,
        prompt: str,
        budget: RunBudgetSession,
    ) -> ProviderResponse:
        estimated_input = estimate_prompt_tokens(prompt)
        budget.assert_can_dispatch(estimated_input, config.max_tokens)
        raw_response = self._completion
        request_id = f"INF-REQ-MOCK-{_mock_request_digest(self.model_id, prompt, config)}"
        budget_warnings = budget.snapshot().budget_warnings
        parsed = ProviderResponse(
            request_id=request_id,
            model_id=self.model_id,
            provider_name=self.provider_name,
            raw_response=raw_response,
            usage=self._usage,
            latency_ms=self._latency_ms,
            attempt_count=1,
            retry_count=0,
            budget_warnings=budget_warnings,
            completed_at_utc=self._clock().isoformat(),
        )
        budget.record_usage(self._usage)
        return parsed.model_copy(update={"budget_warnings": budget.snapshot().budget_warnings})


def _mock_request_digest(model_id: str, prompt: str, config: LLMGenerationConfig) -> str:
    import hashlib
    import json

    payload = (
        model_id,
        prompt,
        str(config.temperature),
        str(config.top_p),
        config.max_tokens,
        config.seed,
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]