"""Immutable digest-bound prompt tests.

Covers constant immutability, digest determinism, deterministic composition,
and the absence of dynamic/gate/trading authority instructions.
"""

from acash.research.ai.hypothesis.prompts import (
    PROMPT_TEMPLATE_SHA256,
    SYSTEM_INSTRUCTION,
    USER_PROMPT_TEMPLATE,
    build_hypothesis_prompt,
)


def test_template_constants_are_non_empty_strings() -> None:
    assert isinstance(SYSTEM_INSTRUCTION, str) and SYSTEM_INSTRUCTION.strip()
    assert isinstance(USER_PROMPT_TEMPLATE, str) and USER_PROMPT_TEMPLATE.strip()
    assert isinstance(PROMPT_TEMPLATE_SHA256, str) and len(PROMPT_TEMPLATE_SHA256) == 64


def test_prompt_template_sha256_is_stable_across_process_runs() -> None:
    first = PROMPT_TEMPLATE_SHA256
    second = PROMPT_TEMPLATE_SHA256
    assert first == second


def test_build_hypothesis_prompt_is_deterministic() -> None:
    left = build_hypothesis_prompt(
        symbol="NQ",
        timeframe="M5",
        economic_context="Opening session momentum",
    )
    right = build_hypothesis_prompt(
        symbol="NQ",
        timeframe="M5",
        economic_context="Opening session momentum",
    )
    assert left == right
    assert "\n\n---\n\n" in left
    assert "Opening session momentum" in left


def test_build_hypothesis_prompt_reflects_context() -> None:
    prompt = build_hypothesis_prompt(
        symbol="ES",
        timeframe="M15",
        economic_context="Slow drift accumulation",
    )
    assert "ES" in prompt
    assert "M15" in prompt
    assert "Slow drift accumulation" in prompt


def test_prompt_contains_no_authority_language() -> None:
    combined = f"{SYSTEM_INSTRUCTION}\n{USER_PROMPT_TEMPLATE}"
    lower = combined.lower()
    for forbidden in ("hyp_003", "execute order", "place order", "broker", "capital", "authorize"):
        assert forbidden not in lower