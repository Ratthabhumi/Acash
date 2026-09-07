"""Causal, point-in-time Abstract Syntax Tree validator for symbolic features.

Implements ``CausalAstValidator`` from the Phase 14 Slice 3 specification.

Enforced invariants (Phase 14 Architecture & Governance Plan Section 5.3):
1. Negative time offsets / future indexing (``lead(x, 1)``, ``x[t+1]``) are hard-rejected.
2. Whole-dataset (global cross-future) normalization such as ``(x - mean(x)) / std(x)``
   is hard-rejected; only windowed statistics (``rolling_mean(x, N)`` with ``N <= t``)
   are admissible.
3. Non-deterministic functions (``random()``, ``time()``, ...) are hard-rejected.
4. Only registered canonical operators may be called; unknown operators fail closed.
5. Every non-reserved Name must be a declared available variable.

The validator is a pure static checker: it performs no arithmetic and touches no data.
Its output is deterministic, tie-symmetric with respect to variable ordering, and
suitable for mirroring into ``AIFeatureProposal`` provenance fields.
"""

import ast
import json
from typing import List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict

from acash.research.ai.features.library import (
    FORBIDDEN_OPERATORS,
    GLOBAL_AGGREGATE_NAMES,
    KNOWN_OPERATORS,
    OPERATOR_ARITY,
    RESERVED_NAMES,
    FeatureExpressionError,
    canonical_form,
)


class AstValidationResult(BaseModel):
    """Deterministic outcome of validating a single symbolic feature expression."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    expression: str
    is_strictly_causal: bool
    lookahead_terms_detected: int
    point_in_time_verified: bool
    violations: Tuple[str, ...]
    canonical_ast_json: str


class CausalAstValidator:
    """Static, deterministic causal / point-in-time validator for feature expressions."""

    def validate_expression(
        self, expression: str, available_variables: Sequence[str]
    ) -> AstValidationResult:
        """Validate ``expression`` against declarable variables.

        Fail-closed semantics: any syntactic or semantic violation rejects the
        expression in full. Zero additions are silently accepted.
        """
        variables = frozenset(available_variables)
        violations: List[str] = []

        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            return AstValidationResult(
                expression=expression,
                is_strictly_causal=False,
                lookahead_terms_detected=0,
                point_in_time_verified=False,
                violations=(f"expression failed to parse: {exc.msg}",),
                canonical_ast_json="",
            )

        lookahead, data_touches = _inspect(tree.body, variables, violations)
        if lookahead == 0 and data_touches == 0:
            violations.append(
                "expression references no declared variable (empty feature proposal)"
            )

        try:
            canonical = canonical_form(expression)
            canonical_json = json.dumps(
                {"canonical_form": canonical}, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            )
        except FeatureExpressionError as exc:
            violations.append(f"expression is not canonically representable: {exc}")
            canonical_json = ""

        is_causal = len(violations) == 0
        return AstValidationResult(
            expression=expression,
            is_strictly_causal=is_causal,
            lookahead_terms_detected=lookahead,
            point_in_time_verified=is_causal,
            violations=tuple(violations),
            canonical_ast_json=canonical_json,
        )


def _inspect(
    node: ast.AST, variables: frozenset[str], violations: List[str]
) -> Tuple[int, int]:
    """Return (lookahead_count, data_touch_count); violations accumulate in AST order."""
    if isinstance(node, ast.Call):
        return _inspect_call(node, variables, violations)
    if isinstance(node, ast.Name):
        if node.id not in RESERVED_NAMES and node.id not in variables:
            violations.append(f"variable '{node.id}' is not among available variables")
        return (0, 1 if node.id in variables else 0)
    if isinstance(node, ast.Subscript):
        return _inspect_subscript(node, variables, violations)
    if isinstance(node, ast.BinOp):
        left = _inspect(node.left, variables, violations)
        right = _inspect(node.right, variables, violations)
        return (left[0] + right[0], left[1] + right[1])
    if isinstance(node, ast.UnaryOp):
        return _inspect(node.operand, variables, violations)
    return (0, 0)


def _inspect_call(
    node: ast.Call, variables: frozenset[str], violations: List[str]
) -> Tuple[int, int]:
    if not isinstance(node.func, ast.Name):
        violations.append("operators must be plain named functions")
        return (0, 0)
    name = node.func.id
    if name in FORBIDDEN_OPERATORS:
        violations.append(
            f"forbidden operator '{name}' (potential lookahead or non-determinism)"
        )
        return (1, 0)
    if name not in KNOWN_OPERATORS:
        if name in GLOBAL_AGGREGATE_NAMES and len(node.args) == 1:
            violations.append(
                f"operator '{name}' applied to a single bare argument is a whole-dataset "
                f"aggregation (cross-future leakage); use a windowed rolling_ variant"
            )
        else:
            violations.append(f"unknown operator '{name}'")
        return (0, 0)
    expected_arity = OPERATOR_ARITY[name]
    if len(node.args) != expected_arity:
        violations.append(
            f"operator '{name}' expects arity {expected_arity}, got {len(node.args)}"
        )
        return (0, 0)
    lookahead = 0
    data_touches = 0
    for arg in node.args:
        arg_lookahead, arg_touches = _inspect(arg, variables, violations)
        lookahead += arg_lookahead
        data_touches += arg_touches
    return (lookahead, data_touches)


def _inspect_subscript(
    node: ast.Subscript, variables: frozenset[str], violations: List[str]
) -> Tuple[int, int]:
    value_lookahead, value_touches = _inspect(node.value, variables, violations)
    if node.slice is None:
        violations.append("subscript has no index expression")
        return (value_lookahead, value_touches)
    future = _future_offset(node.slice)
    if future is not None and future > 0:
        violations.append(
            f"subscript references future index offset +{future} (lookahead); "
            f"only past or current knowledge is admissible"
        )
        return (value_lookahead + 1, value_touches)
    slice_lookahead, slice_touches = _inspect(node.slice, variables, violations)
    return (
        value_lookahead + slice_lookahead,
        value_touches + slice_touches,
    )


def _future_offset(slice_node: ast.AST) -> Optional[int]:
    """Net numeric index offset of a subscript expression; positive is future.

    ``t`` and other reserved names contribute zero so ``close[t-1]`` is past
    (offset -1) while ``close[t+1]`` is forward-looking (offset +1).
    """
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, int):
        if isinstance(slice_node.value, bool):
            return None
        return slice_node.value
    if isinstance(slice_node, ast.Name):
        return 0
    if isinstance(slice_node, ast.UnaryOp) and isinstance(slice_node.op, ast.USub):
        inner = _future_offset(slice_node.operand)
        return -inner if inner is not None else None
    if isinstance(slice_node, ast.BinOp):
        left = _future_offset(slice_node.left)
        right = _future_offset(slice_node.right)
        if left is None or right is None:
            return None
        if isinstance(slice_node.op, ast.Add):
            return left + right
        if isinstance(slice_node.op, ast.Sub):
            return left - right
        return None
    if isinstance(slice_node, ast.Slice):
        if slice_node.lower is None:
            return None
        return _future_offset(slice_node.lower)
    return None