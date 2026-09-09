"""Phase 14 S1 Live HTTP/HTTPS LLM provider governed by the G-4 freeze.

Implements ``ILLMProvider`` using httpx ONLY (no vendor SDK). Canonical safety:
- 30s connect timeout, 60s read timeout (governance plan Section 8.4)
- at most 3 retries restricted to HTTP 429 / 502 / 503 only
- bounded, deterministic backoff (0.25s, 0.5s, 1.0s by default)
- fail-closed on timeout, outage, HTTP error, or protocol violation
- ``ACASH_AI_API_KEY`` / ``ACASH_AI_PROVIDER`` secret isolation (never logged)
- no requests / no subprocess / no vendor packages

G-4 semantics:
- pre-dispatch ceiling check via ``RunBudgetSession.assert_can_dispatch``
  (no network request may occur if the request is already known to exceed)
- retries never multiply the token ceiling
- monetary cost recorded ONLY when explicit pricing metadata is configured;
  ``inference_cost_usd`` stays explicitly unavailable otherwise.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
import time
from typing import Callable, Optional, Sequence

import httpx

from acash.research.ai.provider.base import (
    ILLMProvider,
    InferenceBudgetError,
    InferenceProviderError,
    InvalidProviderResponseError,
    LLMGenerationConfig,
    ProviderResponse,
    RunBudgetSession,
    TokenUsage,
    estimate_prompt_tokens,
)

DEFAULT_CONNECT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_READ_TIMEOUT_SECONDS: float = 60.0
DEFAULT_MAX_NETWORK_RETRIES: int = 3
RETRYABLE_STATUS_CODES: tuple[int, ...] = (429, 502, 503)
DEFAULT_RETRY_BACKOFF_SECONDS: tuple[float, ...] = (0.25, 0.5, 1.0)


class HttpxLLMProvider:
    """G-4 governed live provider over httpx with injectable transport for tests."""

    def __init__(
        self,
        *,
        model_id: str,
        endpoint_url: str,
        api_key: Optional[str] = None,
        provider_name: Optional[str] = None,
        connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
        max_network_retries: int = DEFAULT_MAX_NETWORK_RETRIES,
        retry_backoff_seconds: Sequence[float] = DEFAULT_RETRY_BACKOFF_SECONDS,
        input_price_per_1k_tokens: Optional[Decimal] = None,
        output_price_per_1k_tokens: Optional[Decimal] = None,
        transport: Optional[httpx.BaseTransport] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        from acash.research.ai.provider.base import ClockCallable

        self.model_id: str = model_id
        self.endpoint_url: str = endpoint_url
        self.api_key: Optional[str] = api_key
        if self.api_key is None:
            self.api_key = os.environ.get("ACASH_AI_API_KEY")
        if provider_name is not None:
            self.provider_name: str = provider_name
        else:
            self.provider_name = os.environ.get("ACASH_AI_PROVIDER", "live-httpx")
        self.connect_timeout_seconds: float = connect_timeout_seconds
        self.read_timeout_seconds: float = read_timeout_seconds
        self.max_network_retries: int = max(0, int(max_network_retries))
        self.retry_backoff_seconds: Sequence[float] = tuple(retry_backoff_seconds)
        self.input_price_per_1k_tokens: Optional[Decimal] = input_price_per_1k_tokens
        self.output_price_per_1k_tokens: Optional[Decimal] = output_price_per_1k_tokens
        self._clock: ClockCallable = clock if clock is not None else lambda: datetime.now(timezone.utc)
        if transport is not None:
            self._client: httpx.Client = httpx.Client(transport=transport)
        else:
            self._client = httpx.Client()

    def __repr__(self) -> str:
        return f"HttpxLLMProvider(model_id={self.model_id!r}, provider={self.provider_name!r})"

    def _configured_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            self.read_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )

    def _estimate_prompt_tokens(self, prompt: str) -> int:
        return estimate_prompt_tokens(prompt)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request_payload(self, config: LLMGenerationConfig, prompt: str) -> dict[str, object]:
        return {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.max_tokens,
            "temperature": float(config.temperature),
            "top_p": float(config.top_p),
            "seed": config.seed,
        }

    def _parse_response(
        self,
        *,
        request_id: str,
        raw_text: str,
        attempt_count: int,
        retry_count: int,
        budget_warnings: tuple[str, ...],
        completed_at_utc: str,
        latency_ms: int,
    ) -> ProviderResponse:
        try:
            payload: object = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise InvalidProviderResponseError(
                f"Provider returned non-JSON body for {request_id}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise InvalidProviderResponseError(
                f"Provider response for {request_id} is not a JSON object."
            )
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise InvalidProviderResponseError(
                f"Provider response for {request_id} contains no choices."
            )
        first = choices[0]
        if not isinstance(first, dict):
            raise InvalidProviderResponseError(
                f"Provider response for {request_id} has a malformed choices entry."
            )
        message = first.get("message")
        content = None
        if isinstance(message, dict):
            content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise InvalidProviderResponseError(
                f"Provider response for {request_id} has no textual completion content."
            )
        usage_raw = payload.get("usage")
        if not isinstance(usage_raw, dict):
            raise InvalidProviderResponseError(
                f"Provider response for {request_id} carries no usage accounting."
            )
        try:
            input_tokens = int(usage_raw.get("prompt_tokens", 0))
            output_tokens = int(usage_raw.get("completion_tokens", 0))
            total_tokens = int(usage_raw.get("total_tokens", input_tokens + output_tokens))
        except (TypeError, ValueError) as exc:
            raise InvalidProviderResponseError(
                f"Provider response for {request_id} has non-numeric usage fields."
            ) from exc
        if input_tokens < 0 or output_tokens < 0 or total_tokens < 0:
            raise InvalidProviderResponseError(
                f"Provider response for {request_id} reports negative usage."
            )
        if total_tokens != input_tokens + output_tokens:
            raise InvalidProviderResponseError(
                f"Provider response for {request_id} reports inconsistent token totals."
            )
        inference_cost_usd: Optional[Decimal] = None
        pricing_unavailable = True
        if self.input_price_per_1k_tokens is not None and self.output_price_per_1k_tokens is not None:
            inference_cost_usd = (
                Decimal(input_tokens) / Decimal(1000) * self.input_price_per_1k_tokens
                + Decimal(output_tokens) / Decimal(1000) * self.output_price_per_1k_tokens
            )
            pricing_unavailable = False
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            inference_cost_usd=inference_cost_usd,
            pricing_unavailable=pricing_unavailable,
        )
        return ProviderResponse(
            request_id=request_id,
            model_id=self.model_id,
            provider_name=self.provider_name,
            raw_response=content,
            usage=usage,
            latency_ms=latency_ms,
            attempt_count=attempt_count,
            retry_count=retry_count,
            budget_warnings=budget_warnings,
            completed_at_utc=completed_at_utc,
        )

    def generate(
        self,
        config: LLMGenerationConfig,
        prompt: str,
        budget: RunBudgetSession,
    ) -> ProviderResponse:
        request_id = f"INF-REQ-{_request_digest(self.model_id, prompt, config)}"
        estimated_input = self._estimate_prompt_tokens(prompt)
        budget.assert_can_dispatch(estimated_input, config.max_tokens)

        started = time.monotonic()
        attempt_count = 0
        retry_count = 0
        last_error: Optional[Exception] = None
        while attempt_count <= self.max_network_retries:
            attempt_count += 1
            try:
                response = self._client.post(
                    self.endpoint_url,
                    headers=self._headers(),
                    json=self._request_payload(config, prompt),
                    timeout=self._configured_timeout(),
                )
            except httpx.TimeoutException as exc:
                last_error = exc
            except httpx.HTTPError as exc:
                last_error = exc
            else:
                if response.status_code == 200:
                    latency_ms = int(round((time.monotonic() - started) * 1000.0))
                    raw_text = response.text
                    completed_at_utc = self._clock().isoformat()
                    parsed = self._parse_response(
                        request_id=request_id,
                        raw_text=raw_text,
                        attempt_count=attempt_count,
                        retry_count=retry_count,
                        budget_warnings=budget.snapshot().budget_warnings,
                        completed_at_utc=completed_at_utc,
                        latency_ms=latency_ms,
                    )
                    budget.record_usage(parsed.usage)
                    return parsed.model_copy(
                        update={"budget_warnings": budget.snapshot().budget_warnings}
                    )
                if response.status_code in RETRYABLE_STATUS_CODES and retry_count < self.max_network_retries:
                    backoff = self.retry_backoff_seconds[retry_count % len(self.retry_backoff_seconds)]
                    retry_count += 1
                    if backoff > 0:
                        time.sleep(backoff)
                    continue
                last_error = InferenceProviderError(
                    f"Provider HTTP failure for {request_id}: status={response.status_code}."
                )
                break
        if last_error is None:
            raise InferenceProviderError(f"Provider request failed for {request_id} without detail.")
        if isinstance(last_error, InferenceProviderError):
            raise last_error
        raise InferenceProviderError(
            f"Provider request failed for {request_id} after {attempt_count - 1} retries: {last_error}"
        ) from last_error

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpxLLMProvider":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _request_digest(model_id: str, prompt: str, config: LLMGenerationConfig) -> str:
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