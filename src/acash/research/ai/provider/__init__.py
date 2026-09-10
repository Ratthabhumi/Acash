"""Phase 14 Slice 1 (S1) provider package with G-4 inference/cost governance.

Exposes the canonical ``ILLMProvider`` interface, the human-frozen G-4 budget
guard, and the two governed providers (mock + httpx). This package owns NO
trading, execution, capital, or gate authority.
"""

from acash.research.ai.provider.base import (
    BudgetPolicy,
    ILLMProvider,
    InferenceBudgetError,
    InferenceProviderError,
    InvalidProviderResponseError,
    LLMGenerationConfig,
    ProviderResponse,
    RunBudgetSession,
    RunBudgetSnapshot,
    TokenUsage,
    estimate_prompt_tokens,
)
from acash.research.ai.provider.httpx_client import HttpxLLMProvider
from acash.research.ai.provider.mock import MockLLMProvider

__all__ = [
    "ILLMProvider",
    "LLMGenerationConfig",
    "TokenUsage",
    "ProviderResponse",
    "BudgetPolicy",
    "RunBudgetSession",
    "RunBudgetSnapshot",
    "estimate_prompt_tokens",
    "InferenceProviderError",
    "InferenceBudgetError",
    "InvalidProviderResponseError",
    "HttpxLLMProvider",
    "MockLLMProvider",
]