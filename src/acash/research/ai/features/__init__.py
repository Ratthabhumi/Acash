"""Phase 14 Slice 3: Exploratory Feature Discovery.

Deterministic, causal, point-in-time symbolic feature proposal capability.

GOVERNANCE BOUNDARY:
- Feature proposals carry NO backtest, validation, capital, quarantine, or trading authority.
- Point-in-time causality is certified exclusively by ``CausalAstValidator``.
- This package performs zero LLM calls, zero provider access, zero data access.
"""

from acash.research.ai.features.ast_validator import (
    AstValidationResult,
    CausalAstValidator,
)
from acash.research.ai.features.discovery import (
    FeatureDiscoveryEngine,
    FeatureDiscoveryRequest,
)
from acash.research.ai.features.library import (
    ALIASES,
    FORBIDDEN_OPERATORS,
    GLOBAL_AGGREGATE_NAMES,
    KNOWN_OPERATORS,
    OPERATOR_ARITY,
    RESERVED_NAMES,
    FeatureExpressionError,
    FeatureOperator,
    canonical_form,
)
from acash.research.ai.schema import AIFeatureProposal

__all__ = [
    "ALIASES",
    "AIFeatureProposal",
    "AstValidationResult",
    "CausalAstValidator",
    "FORBIDDEN_OPERATORS",
    "FeatureDiscoveryEngine",
    "FeatureDiscoveryRequest",
    "FeatureExpressionError",
    "FeatureOperator",
    "GLOBAL_AGGREGATE_NAMES",
    "KNOWN_OPERATORS",
    "OPERATOR_ARITY",
    "RESERVED_NAMES",
    "canonical_form",
]