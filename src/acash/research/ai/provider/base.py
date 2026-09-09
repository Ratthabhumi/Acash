"""Phase 14 Slice 1 (S1) Provider Foundation & G-4 Inference/Cost Governance.

Establishes the canonical provider contract per the Phase 14 Architecture &
Governance Plan (Section 8.2) and the human-ratified G-4 freeze:

G4-1 HYBRID : observability mandatory, warning thresholds supported, hard
             ceiling mandatory for LIVE/HTTP inference, no quota subsystem,
             fail-closed enforcement.
G4-2 Dims  : per inference request, per research run/session, and aggregate
             process/run total. No daily/monthly/provider/project quotas.
G4-3 Values: per-request ceiling 16,384 tokens / warning 12,288; per-run
             ceiling 100,000 tokens / warning 80,000. Monetary cost is
             OBSERVED ONLY, never invented.
G4-5 Guard : provider-layer governance mechanism only; domain logic stays clean.
G4-6 Retry : retries must not bypass the token ceiling; a request rejected
             before network dispatch consumes no retry attempts.
G4-7 Fail  : over-limit = FAIL-CLOSED; timeout/provider outage = fail-closed.

INVARIANTS:
- None of the types below import or reference trading, execution, capital,
  broker, ValidationGate, AlphaQualificationGate, or ResearchReInceptionGate.
- Token ceilings are enforcement limits; monetary cost is observability-only.
- No persistent quota, no hidden global state.
"""

from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Callable, Dict, Final, Optional, Protocol, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from acash.research.ai.exceptions import ResearchAiError

FROZEN_PER_REQUEST_MAX_TOKENS: Final[int] = 16_384
FROZEN_PER_REQUEST_WARNING_TOKENS: Final[int] = 12_288
FROZEN_PER_RUN_MAX_TOKENS: Final[int] = 100_000
FROZEN_PER_RUN_WARNING_TOKENS: Final[int] = 80_000


class InferenceProviderError(ResearchAiError):
    """Raised when an LLM provider request fails (timeout, outage, HTTP, protocol)."""


class InferenceBudgetError(ResearchAiError):
    """Raised when a G-4 token ceiling would be exceeded (fail-closed)."""


class InvalidProviderResponseError(ResearchAiError):
    """Raised when a provider response violates the G-4/schema contract (DataContractError semantics)."""


def estimate_prompt_tokens(prompt: str) -> int:
    """Deterministic conservative prompt-size heuristic for pre-dispatch checks.

    Named HEURISTIC: roughly 4 characters per token. Only used to determine
    whether a request is *already known* to exceed a ceiling before any network
    request is sent. Actual consumption always comes from provider usage data.
    """
    if not prompt:
        return 1
    return max(1, (len(prompt) + 3) // 4)


class LLMGenerationConfig(BaseModel):
    """Bounded-model-interaction configuration (master plan Section 12.2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    temperature: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), le=Decimal("2.0"))
    top_p: Decimal = Field(default=Decimal("1.0"), gt=Decimal("0.0"), le=Decimal("1.0"))
    max_tokens: int = Field(default=8_192, ge=1, le=FROZEN_PER_REQUEST_MAX_TOKENS)
    seed: Optional[int] = None


class TokenUsage(BaseModel):
    """Deterministic token/cost accounting for a single provider response.

    Monetary cost is recorded ONLY when provider pricing metadata is available.
    ``inference_cost_usd`` remains ``None`` (explicitly unknown) otherwise; it is
    never fabricated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    inference_cost_usd: Optional[Decimal] = None
    pricing_unavailable: bool = Field(default=True)

    def to_observability_metrics(self) -> Dict[str, object]:
        """Canonical G-4 observability projection (master plan Section 14)."""
        return {
            "tokens_consumed_total": self.total_tokens,
            "inference_cost_usd": self.inference_cost_usd,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class ProviderResponse(BaseModel):
    """Canonical result of a single provider invocation with deterministic G-4 usage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    model_id: str
    provider_name: str
    raw_response: str
    usage: TokenUsage
    latency_ms: int = Field(default=0, ge=0)
    attempt_count: int = Field(default=1, ge=1)
    retry_count: int = Field(default=0, ge=0)
    budget_warnings: Tuple[str, ...] = Field(default=())
    completed_at_utc: str


class BudgetPolicy(BaseModel):
    """Human-frozen G-4 numeric contract.

    DEFAULTS ARE THE HUMAN-FROZEN VALUES (2026-09-08 G-4 ratification).
    Instances may override for deterministic tests only; production use must
    keep the frozen defaults unless the human amends the freeze.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    per_request_max_tokens: int = Field(default=FROZEN_PER_REQUEST_MAX_TOKENS, ge=1)
    per_request_warning_tokens: int = Field(default=FROZEN_PER_REQUEST_WARNING_TOKENS, ge=1)
    per_run_max_tokens: int = Field(default=FROZEN_PER_RUN_MAX_TOKENS, ge=1)
    per_run_warning_tokens: int = Field(default=FROZEN_PER_RUN_WARNING_TOKENS, ge=1)

    @model_validator(mode="after")
    def _warnings_below_ceilings(self) -> "BudgetPolicy":
        if self.per_request_warning_tokens > self.per_request_max_tokens:
            raise InferenceBudgetError(
                "per_request_warning_tokens must not exceed per_request_max_tokens."
            )
        if self.per_run_warning_tokens > self.per_run_max_tokens:
            raise InferenceBudgetError(
                "per_run_warning_tokens must not exceed per_run_max_tokens."
            )
        return self


class RunBudgetSnapshot(BaseModel):
    """Immutable audit projection of G-4 accounting at a point in time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tokens_consumed_total: int = Field(ge=0)
    request_count: int = Field(ge=0)
    per_request_remaining: int = Field(ge=0)
    per_run_remaining: int = Field(ge=0)
    budget_warnings: Tuple[str, ...] = Field(default=())
    run_digest: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


class RunBudgetSession:
    """Deterministic provider-side G-4 budget guard (single session, no global state).

    Usage points:
    - ``assert_can_dispatch`` BEFORE any network request (pre-check).
    - ``record_usage`` AFTER a response to accumulate actual consumption.
    Fail-closed: any ceiling breach raises ``InferenceBudgetError``.
    """

    def __init__(self, policy: Optional[BudgetPolicy] = None) -> None:
        self._policy: BudgetPolicy = policy if policy is not None else BudgetPolicy()
        self._consumed: int = 0
        self._requests: int = 0
        self._warnings: list[str] = []

    @property
    def policy(self) -> BudgetPolicy:
        return self._policy

    @property
    def tokens_consumed_total(self) -> int:
        return self._consumed

    @property
    def request_count(self) -> int:
        return self._requests

    def assert_can_dispatch(self, estimated_input_tokens: int, max_output_tokens: int) -> None:
        """Fail-closed pre-dispatch check. Raises before any network request occurs."""
        estimated_total = max(0, estimated_input_tokens) + max(0, max_output_tokens)
        if estimated_total > self._policy.per_request_max_tokens:
            raise InferenceBudgetError(
                f"G-4 per-request ceiling exceeded: estimated {estimated_total} "
                f"> {self._policy.per_request_max_tokens}. No request dispatched."
            )
        if self._consumed + estimated_total > self._policy.per_run_max_tokens:
            raise InferenceBudgetError(
                f"G-4 per-run ceiling exceeded: consumed {self._consumed} + estimated "
                f"{estimated_total} > {self._policy.per_run_max_tokens}. No request dispatched."
            )

    def record_usage(self, usage: TokenUsage) -> RunBudgetSnapshot:
        """Accumulate actual consumption. Fail-closed on any ceiling breach."""
        if usage.total_tokens > self._policy.per_request_max_tokens:
            raise InferenceBudgetError(
                f"G-4 per-request ceiling exceeded by response: {usage.total_tokens} "
                f"> {self._policy.per_request_max_tokens}."
            )
        if self._consumed + usage.total_tokens > self._policy.per_run_max_tokens:
            raise InferenceBudgetError(
                f"G-4 per-run ceiling exceeded: consumed {self._consumed} + "
                f"{usage.total_tokens} > {self._policy.per_run_max_tokens}."
            )
        self._consumed += usage.total_tokens
        self._requests += 1
        if usage.total_tokens >= self._policy.per_request_warning_tokens:
            self._warnings.append(
                f"PER_REQUEST_WARNING={usage.total_tokens}>={self._policy.per_request_warning_tokens}"
            )
        if self._consumed >= self._policy.per_run_warning_tokens:
            self._warnings.append(
                f"PER_RUN_WARNING={self._consumed}>={self._policy.per_run_warning_tokens}"
            )
        snapshot = self.snapshot()
        return snapshot

    def snapshot(self) -> RunBudgetSnapshot:
        """Immutable audit projection (deterministic, includes digest)."""
        consumed = self._consumed
        requests = self._requests
        warnings = tuple(self._warnings)
        per_request_remaining = max(0, self._policy.per_request_max_tokens - consumed)
        per_run_remaining = max(0, self._policy.per_run_max_tokens - consumed)
        return RunBudgetSnapshot(
            tokens_consumed_total=consumed,
            request_count=requests,
            per_request_remaining=per_request_remaining,
            per_run_remaining=per_run_remaining,
            budget_warnings=warnings,
            run_digest=_stable_run_digest(consumed, requests, warnings),
        )


def _stable_run_digest(consumed: int, requests: int, warnings: Tuple[str, ...]) -> str:
    payload = {
        "policy_anchor": "G4-2026-09-08-HUMAN-FROZEN",
        "request_count": requests,
        "tokens_consumed_total": consumed,
        "budget_warnings": list(warnings),
    }
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class ILLMProvider(Protocol):
    """Canonical provider interface (governance plan Section 8.2)."""

    provider_name: str
    model_id: str

    def generate(
        self,
        config: LLMGenerationConfig,
        prompt: str,
        budget: RunBudgetSession,
    ) -> ProviderResponse:
        """Run one bounded inference request under the G-4 budget guard."""
        ...


ClockCallable = Callable[[], datetime]