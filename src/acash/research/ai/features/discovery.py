"""Deterministic exploratory feature discovery engine (Phase 14 Slice 3).

Generates candidate symbolic feature transformations over declared microstructure
variables, validates every candidate with ``CausalAstValidator``, de-duplicates via
canonical operator-equivalence normalization, and emits immutable ``AIFeatureProposal``
records.

GOVERNANCE BOUNDARY:
- Pure deterministic symbolic generation. NO LLM call, NO provider, NO network, NO data.
- Every emitted proposal is structurally relaxed only through Point-in-Time causality
  certification: ``is_strictly_causal``, ``lookahead_terms_detected == 0`` and
  ``point_in_time_verified == True`` are only set when the validator independently
  verifies them.
- A feature proposal is NOT a strategy, NOT verified alpha, and NOT trading authority.
"""

import hashlib
import json
import re
from typing import Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.research.ai.features.ast_validator import CausalAstValidator
from acash.research.ai.features.library import canonical_form
from acash.research.ai.schema import AIFeatureProposal


class FeatureDiscoveryRequest(BaseModel):
    """Input contract for deterministic exploratory feature discovery."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base_variables: Tuple[str, ...] = Field(min_length=1)
    target_phenomenon: str = Field(min_length=3)
    max_features: int = Field(default=5, ge=1, le=50)
    max_expression_depth: int = Field(default=2, ge=1, le=4)


class FeatureDiscoveryEngine:
    """Deterministically proposes causal candidate features from canonical primitives."""

    def __init__(self) -> None:
        self._validator = CausalAstValidator()

    def discover(self, request: FeatureDiscoveryRequest) -> Tuple[AIFeatureProposal, ...]:
        """Return at most ``max_features`` validated, de-duplicated feature proposals."""

        variables = request.base_variables
        raw_candidates = self._enumerate_candidates(variables)

        validated: list[str] = []
        for expression in raw_candidates:
            result = self._validator.validate_expression(expression, variables)
            if result.point_in_time_verified:
                validated.append(canonical_form(expression))

        deduplicated: list[str] = []
        for canonical in sorted(validated):
            if canonical not in deduplicated:
                deduplicated.append(canonical)

        capped = deduplicated[: request.max_features]

        seed_base = f"{request.target_phenomenon}|{request.max_expression_depth}"
        proposals: list[AIFeatureProposal] = []
        for idx, formula in enumerate(capped):
            digest = hashlib.sha256(f"{seed_base}|{idx}|{formula}".encode("utf-8")).hexdigest()
            provenance = {
                "base_variables": list(variables),
                "engine": "acash.research.ai.features.discovery.v1",
                "target_phenomenon": request.target_phenomenon,
                "feature": formula,
            }
            provenance_hash = hashlib.sha256(
                json.dumps(provenance, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
                    "utf-8"
                )
            ).hexdigest()
            proposals.append(
                AIFeatureProposal(
                    feature_id=f"AI-FEAT-{digest[:16]}",
                    feature_name=self._feature_name(formula),
                    mathematical_formula=formula,
                    ast_representation_json=json.dumps(
                        {"canonical_form": formula}, ensure_ascii=True, sort_keys=True, separators=(",", ":")
                    ),
                    is_strictly_causal=True,
                    lookahead_terms_detected=0,
                    point_in_time_verified=True,
                    intended_microstructure_signal=(
                        f"candidate {request.target_phenomenon} feature: {formula}"
                    ),
                    provenance_hash=provenance_hash,
                )
            )
        return tuple(proposals)

    def _enumerate_candidates(self, variables: Sequence[str]) -> list[str]:
        """Generate deterministic candidate expressions over the base variables."""
        candidates: list[str] = []
        for var in variables:
            candidates.extend(
                [
                    f"abs({var})",
                    f"log({var})",
                    f"sign({var})",
                    f"sqrt({var})",
                    f"exp({var})",
                    f"ema({var},21)",
                    f"rolling_mean({var},21)",
                    f"rolling_std({var},21)",
                    f"rolling_sum({var},21)",
                    f"rolling_median({var},21)",
                    f"diff({var},1)",
                    f"pct_change({var},21)",
                    f"zscore({var},21)",
                ]
            )
            candidates.append(f"macd({var},10,50)")
            candidates.append(f"macd({var},5,35)")
            candidates.append(f"{var}[t]")
        for a in variables:
            for b in variables:
                if a < b:
                    candidates.append(f"({a} - {b})")
                    candidates.append(f"({a} + {b})")
                    candidates.append(f"({a} - {b}) / ({a} + {b})")
                    candidates.append(f"imbalance({a},{b})")
        return candidates

    _PARAM_OPERATORS: frozenset[str] = frozenset(
        {
            "abs",
            "exp",
            "log",
            "sign",
            "sqrt",
            "macd",
            "ema",
            "rolling_mean",
            "rolling_std",
            "rolling_var",
            "rolling_sum",
            "rolling_min",
            "rolling_max",
            "rolling_median",
            "pct_change",
            "diff",
            "zscore",
        }
    )

    def _feature_name(self, formula: str) -> str:
        """Deterministic, schema-conformant slug for a canonical formula."""
        head, _, rest = formula.partition("(")
        if not rest:
            return "feature_candidate"
        stem = head.strip()
        if not stem or not re.fullmatch(r"[a-z][a-z0-9_]*", stem):
            digest = hashlib.sha256(formula.encode("utf-8")).hexdigest()
            return f"pair_expr_{digest[:8]}"
        if stem not in self._PARAM_OPERATORS:
            return stem if len(stem) >= 3 else f"{stem}_value"
        arg_tokens = [token.strip() for token in rest.rstrip(")").split(",") if token.strip()]
        suffix = "_".join(
            re.sub(r"[^0-9a-z_]", "", token.lower()) or "v" for token in arg_tokens
        )
        name = f"{stem}_{suffix}"
        if len(name) > 32:
            name = f"{stem}_{suffix[-15:]}"
        return name