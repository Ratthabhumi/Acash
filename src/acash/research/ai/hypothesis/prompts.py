"""Phase 14 S2 immutable, digest-bound hypothesis prompt constants.

Invariants:
- Constants are immutable ``Final`` strings; no dynamic hidden instructions.
- ``PROMPT_TEMPLATE_SHA256`` is the canonical digest of ``USER_PROMPT_TEMPLATE``
  and is recorded as proposal provenance (never a hidden instruction).
- Prompt content contains ZERO authority language: nothing about registration,
  backtesting, validation, alpha qualification, capital, or trading.
"""

import hashlib
import json
from typing import Final

SYSTEM_INSTRUCTION: Final[str] = (
    "You are a quantitative research assistant producing a strictly preliminary, "
    "unvalidated hypothesis draft. The draft is a PROPOSAL ONLY: it carries no "
    "research, validation, registration, or trading authority."
)

USER_PROMPT_TEMPLATE: Final[str] = (
    "Draft a structured quantitative hypothesis from the context below.\n"
    "Return ONLY one JSON object with exactly these keys:\n"
    "- economic_rationale: string (>= 20 chars)\n"
    "- market_microstructure_mechanism: string (>= 20 chars)\n"
    "- invalidation_conditions: array of strings (>= 1)\n"
    "- target_symbol: string\n"
    "- target_timeframe: string\n"
    "- feature_dependencies: array of strings (>= 1)\n"
    "- expected_direction: one of LONG | SHORT | DISPERSION\n"
    "- target_horizons: array of integers (>= 1)\n"
    "- proposed_invalidation_criteria: object with keys "
    "min_in_sample_rank_ic, min_hac_t_stat, max_feature_autocorrelation, "
    "min_cost_adjusted_spread_ratio (decimal strings)\n"
    "Context: symbol={symbol}; timeframe={timeframe}; economic_context={economic_context}"
)


def _canonical_sha256(payload: object) -> str:
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


PROMPT_TEMPLATE_SHA256: Final[str] = _canonical_sha256(USER_PROMPT_TEMPLATE)


def build_hypothesis_prompt(
    *,
    symbol: str,
    timeframe: str,
    economic_context: str,
) -> str:
    """Compose the deterministic full prompt for a single hypothesis draft."""
    context = {
        "symbol": symbol,
        "timeframe": timeframe,
        "economic_context": economic_context,
    }
    user_prompt = USER_PROMPT_TEMPLATE.format(**context)
    return f"{SYSTEM_INSTRUCTION}\n\n---\n\n{user_prompt}"