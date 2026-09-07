"""Canonical symbolic feature operator primitives for Phase 14 Slice 3.

This module defines the deterministic operator vocabulary consumed by
``CausalAstValidator`` and ``FeatureDiscoveryEngine``, plus a canonical
normalization transform used for operator-equivalence / duplication detection
(Phase 14 Master Plan Section 5: Operator Equivalence).

Properties:
- PURELY DETERMINISTIC SYMBOLIC METADATA: this module performs zero arithmetic over data.
- Every feature expression is expressed as a function application over named variables.
- Whole-dataset aggregation (``mean(x)``, ``std(x)``) is intentionally NOT a registered
  operator because it admits global cross-future normalization (leakage). Only windowed
  variants (``rolling_mean(x, N)`` ...) are canonical, with ``N`` bounded to lookback.

GOVERNANCE:
- These primitives are capability metadata, not evidence, not strategy, not authority.
- No expression here represents validated alpha or trading authority.
"""

from dataclasses import dataclass
import ast
from typing import Mapping, Optional, Tuple

from acash.research.ai.exceptions import ResearchAiError


class FeatureExpressionError(ResearchAiError):
    """Raised when a symbolic expression cannot be canonically represented fail-closed."""


@dataclass(frozen=True)
class FeatureOperator:
    """A registered canonical symbolic feature operator primitive."""

    name: str
    arity: int
    windowed: bool
    description: str


_OPERATOR_DEFS: Tuple[FeatureOperator, ...] = (
    # Unary pointwise transforms (no lookback required).
    FeatureOperator("abs", 1, False, "Absolute value."),
    FeatureOperator("log", 1, False, "Natural logarithm."),
    FeatureOperator("sign", 1, False, "Sign of the argument."),
    FeatureOperator("sqrt", 1, False, "Principal square root."),
    FeatureOperator("exp", 1, False, "Exponential function."),
    # Two-argument windowed statistical transforms (lookback N > 0, N <= t).
    FeatureOperator("rolling_mean", 2, True, "Rolling mean over a window of length N."),
    FeatureOperator("rolling_std", 2, True, "Rolling standard deviation over a window of length N."),
    FeatureOperator("rolling_var", 2, True, "Rolling variance over a window of length N."),
    FeatureOperator("rolling_sum", 2, True, "Rolling sum over a window of length N."),
    FeatureOperator("rolling_min", 2, True, "Rolling minimum over a window of length N."),
    FeatureOperator("rolling_max", 2, True, "Rolling maximum over a window of length N."),
    FeatureOperator("rolling_median", 2, True, "Rolling median over a window of length N."),
    FeatureOperator("ema", 2, True, "Exponential moving average with span N."),
    FeatureOperator("pct_change", 2, True, "Relative change from N bars ago."),
    FeatureOperator("diff", 2, True, "Difference from N bars ago (past-looking)."),
    FeatureOperator("zscore", 2, True, "Rolling z-score of the argument over window N."),
    # Two-series primitives.
    FeatureOperator("imbalance", 2, False, "(x - y) / (x + y) order-flow style imbalance."),
    # Three-argument composite primitives.
    FeatureOperator("macd", 3, True, "ema(x, short) - ema(x, long)."),
)

KNOWN_OPERATORS: frozenset[str] = frozenset(op.name for op in _OPERATOR_DEFS)

OPERATOR_ARITY: Mapping[str, int] = {op.name: op.arity for op in _OPERATOR_DEFS}

#: Reserved time-index / loop names permitted as bare Names without being variables.
RESERVED_NAMES: frozenset[str] = frozenset({"t", "i", "n", "N", "window", "lookback", "idx", "index"})

#: Non-canonical aliases that are normalized for equivalence detection but are NOT
#: admissible operators at validation time (fail-closed: the canonical form must be used).
ALIASES: Mapping[str, str] = {"sma": "rolling_mean"}

#: Operator names whose bare single-argument application implies whole-dataset
#: aggregation (global cross-future statistics) and is therefore leakage-flagged.
GLOBAL_AGGREGATE_NAMES: frozenset[str] = frozenset(
    {"mean", "std", "var", "median", "sum", "skew", "kurtosis", "min", "max"}
)

#: Operator names that are hard-forbidden as potential lookahead / non-determinism.
FORBIDDEN_OPERATORS: frozenset[str] = frozenset(
    {
        "lead",
        "future",
        "forward",
        "delay",
        "shift",
        "random",
        "rand",
        "choice",
        "seed",
        "normalvariate",
        "gauss",
        "time",
        "datetime",
        "today",
        "uuid",
        "np",
        "numpy",
    }
)


def _num_str(value: ast.Constant) -> str:
    """Deterministic string for a numeric/boolean/string literal."""
    if isinstance(value.value, bool):
        return "1" if value.value else "0"
    if isinstance(value.value, int):
        return str(value.value)
    if isinstance(value.value, float):
        if value.value.is_integer() and abs(value.value) < 1e16:
            return str(int(value.value))
        return repr(value.value)
    if isinstance(value.value, str):
        return value.value
    raise FeatureExpressionError(f"Unsupported literal kind in expression: {value!r}")


_BINOP: Mapping[type, str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Mod: "%",
    ast.FloorDiv: "//",
    ast.Pow: "**",
    ast.BitOr: "|",
    ast.BitAnd: "&",
}


def _canonicalize(node: ast.AST) -> str:
    """Deterministically rebuild an AST node into a canonical string form."""
    if isinstance(node, ast.Expression):
        return _canonicalize(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool, str)):
            return _num_str(node)
        raise FeatureExpressionError(f"Unsupported constant in expression: {node.value!r}")
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        if node.keywords:
            raise FeatureExpressionError(
                "keyword arguments are not supported in canonical feature expressions"
            )
        if isinstance(node.func, ast.Name):
            name = ALIASES.get(node.func.id, node.func.id)
        else:
            name = _canonicalize(node.func)
        args = ",".join(_canonicalize(arg) for arg in node.args)
        return f"{name}({args})"
    if isinstance(node, ast.BinOp):
        left = _canonicalize(node.left)
        right = _canonicalize(node.right)
        op = _BINOP.get(node.op.__class__)
        if op is None:
            raise FeatureExpressionError(
                f"Unsupported binary operator in expression: {node.op.__class__.__name__}"
            )
        # Operator-equivalence transform (Phase 14 Master Plan Section 5):
        # ema(v, short) - ema(v, long) -> macd(v, short, long) when short < long.
        ema_diff = _try_macd_transform(node.left, node.right)
        if ema_diff is not None:
            return ema_diff
        return f"({left}{op}{right})"
    if isinstance(node, ast.UnaryOp):
        operand = _canonicalize(node.operand)
        if isinstance(node.op, ast.USub):
            return f"(-{operand})"
        if isinstance(node.op, ast.UAdd):
            return f"(+{operand})"
        raise FeatureExpressionError(
            f"Unsupported unary operator in expression: {node.op.__class__.__name__}"
        )
    if isinstance(node, ast.Subscript):
        value = _canonicalize(node.value)
        index = _canonicalize(node.slice)
        return f"{value}[{index}]"
    raise FeatureExpressionError(
        f"Unsupported AST node in expression: {node.__class__.__name__}"
    )


def _try_macd_transform(left: ast.AST, right: ast.AST) -> Optional[str]:
    """Return canonical ``macd`` form when the AST matches ``ema(v,a) - ema(v,b)``."""
    if not isinstance(left, ast.Call) or not isinstance(right, ast.Call):
        return None
    if not isinstance(left.func, ast.Name) or not isinstance(right.func, ast.Name):
        return None
    if left.func.id != "ema" or right.func.id != "ema":
        return None
    if not isinstance(left.args[0], ast.Name) or not isinstance(right.args[0], ast.Name):
        return None
    if left.args[0].id != right.args[0].id:
        return None
    if len(left.args) != 2 or len(right.args) != 2:
        return None
    n1 = left.args[1]
    n2 = right.args[1]
    if not isinstance(n1, ast.Constant) or not isinstance(n2, ast.Constant):
        return None
    if not isinstance(n1.value, (int, float)) or not isinstance(n2.value, (int, float)):
        return None
    if isinstance(n1.value, bool) or isinstance(n2.value, bool):
        return None
    a = float(n1.value)
    b = float(n2.value)
    if a >= b:
        return None
    var = left.args[0].id
    return f"macd({var},{_num_str(n1)},{_num_str(n2)})"


def canonical_form(expression: str) -> str:
    """Canonical, deterministic symbolic form of a feature expression.

    Two mathematically equivalent expressions (per the registered operator
    equivalence rules) yield identical canonical forms. Unknown AST node kinds
    fail closed with :class:`FeatureExpressionError`.
    """
    tree = ast.parse(expression, mode="eval")
    return _canonicalize(tree)