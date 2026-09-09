"""Phase 14 Slice 2 (S2) hypothesis package.

Exposes the strictly proposal-only assistant, the immutable digest-bound
prompts, and the human-gated converter. Output proposals permanently remain
``UNVALIDATED_PROPOSAL`` with zero registration, backtest, gate, or trading
authority.
"""

from acash.research.ai.hypothesis.assistant import (
    AIHypothesisAssistant,
    AssistantResult,
)
from acash.research.ai.hypothesis.converter import HypothesisProposalConverter
from acash.research.ai.hypothesis.prompts import (
    PROMPT_TEMPLATE_SHA256,
    SYSTEM_INSTRUCTION,
    USER_PROMPT_TEMPLATE,
    build_hypothesis_prompt,
)

__all__ = [
    "AIHypothesisAssistant",
    "AssistantResult",
    "HypothesisProposalConverter",
    "build_hypothesis_prompt",
    "PROMPT_TEMPLATE_SHA256",
    "SYSTEM_INSTRUCTION",
    "USER_PROMPT_TEMPLATE",
]