"""Trusted causal materialization of AI feature proposals into canonical PyArrow columns (Seam B).

GOVERNANCE MANDATE:
- This module converts a validated :class:`AIFeatureProposal` (symbolic) into a concrete
  point-in-time PyArrow feature column consumable by the Phase 4 feature-table contract
  (``AlphaResearchPipeline.run_hypothesis_evaluation``).
- It is PURE DATA-PLUMBING. It performs zero backtests, zero feature selection, zero
  optimization, zero hypothesis registration, zero gate invocation, and zero trading
  authority of any kind.
- It executes NO arbitrary Python. Only the operators registered in the canonical
  feature vocabulary (``acash.research.ai.features.library``) are evaluated, and only
  through an explicit whitelist. ``eval`` / ``exec`` / dynamic imports are prohibited.

MATERIALIZATION CONTRACT:
1. The proposal formula is revalidated at materialization time by ``CausalAstValidator``.
2. Fail-closed conditions: malformed expression, unknown variable, unknown operator,
   invalid arity, forbidden operation, future index / lookahead subscript, whole-dataset
   aggregate, any operator without a deterministic implementation, any expression not
   canonically representable.
3. Only explicitly registered operators are evaluated.
4. Point-in-time semantics are preserved: every output value at row ``t`` depends only on
   rows ``<= t``.
5. Deterministic warmup semantics: rows without sufficient history become explicit NULL.
   FUTURE VALUES ARE NEVER USED TO PAD HISTORY.
6. Two-series primitives are evaluated strictly on the SAME row (``t``) of both series.
7. Division by zero and domain violations (``log(x)`` for ``x <= 0``, ``sqrt(x)`` for
   ``x < 0``, ``zscore`` with zero variance) produce explicit NULL, never Inf/NaN or a
   fabricated approximation. Non-finite source values fail closed with DataContractError.
8. Every materialized table is deterministic and byte-reproducible for identical input.

WARMUP DEFINITIONS (canonical, per operator; ``t`` is the 0-based row index):
- ``abs/log/sign/sqrt/exp``                       -> defined on every row (domain-NULL where invalid).
- ``diff(x, N)`` , ``pct_change(x, N)``           -> NULL for t < N.
- ``rolling_*(x, N)``                             -> NULL for t < N - 1 (window = x[t-N+1 .. t]).
- ``rolling_var(x, N)`` / ``rolling_std(x, N)``   -> additionally all-NULL when N < 2 (sample ddof=1).
- ``ema(x, N)``                                   -> NULL for t < N - 1; seeded at t=N-1 with
                                                     rolling_mean(x, N); alpha = 2 / (N + 1).
- ``zscore(x, N)``                                -> NULL for t < N - 1 (uses rolling_mean/rolling_std).
- ``macd(x, s, l)``                               -> NULL while either EMA component is NULL.
- ``imbalance(a, b)``                             -> same-bar, whole-column pointwise.

Window size / lag arguments MUST be positive integer literals (deterministic static shape).
Any window containing a NULL input yields NULL output (strict; no silent imputation).

PROVENANCE:
- A :class:`MaterializationProvenance` record binds feature identity, canonical formula,
  proposal provenance hash, source-table canonical SHA-256, resulting materialized-table
  SHA-256, and output column type, sealed by a deterministic ``provenance_digest``.
- Table digests reuse the canonical ``calculate_canonical_feature_table_sha256`` (row- and
  column-order-invariant) from ``acash.research.pipeline``. No second hashing algorithm is
  invented.
- ``ResearchManifest.features_manifest_hash`` is intentionally NOT promoted into a stored
  governance field here: its binding contract is not yet canonical and remains unresolved.
"""

import ast
import math
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.ai.features.ast_validator import CausalAstValidator, _future_offset
from acash.research.ai.features.library import (
    FeatureExpressionError,
    canonical_form,
)
from acash.research.ai.schema import AIFeatureProposal
from acash.research.pipeline import calculate_canonical_feature_table_sha256

FEATURE_COLUMN_TYPE: pa.DataType = pa.decimal128(38, 18)
_FEATURE_SCALE: Decimal = Decimal("1e-18")
_ECON_PRECISION: int = 38

_Series = List[Optional[Decimal]]

_UnaryPointFn = Callable[[Decimal], Optional[Decimal]]


def _int(value: Optional[Decimal]) -> int:
    """Strictly extract a non-None Decimal as int (fail-closed internal guard)."""
    if value is None:
        raise DataContractError("internal: None encountered in mandatory parameter position")
    return int(value)


def _is_numeric_column(field: pa.Field) -> bool:
    return bool(
        pa.types.is_integer(field.type)
        or pa.types.is_floating(field.type)
        or pa.types.is_decimal(field.type)
    )


def _to_decimal_columns(table: pa.Table) -> Dict[str, _Series]:
    """Convert numeric source columns to nullable Decimal series; fail closed on bad values."""
    columns: Dict[str, _Series] = {}
    for field in table.schema:
        if not _is_numeric_column(field):
            continue
        series: _Series = []
        for value in table.column(field.name).to_pylist():
            if value is None:
                series.append(None)
                continue
            if isinstance(value, bool):
                series.append(Decimal(int(value)))
                continue
            if isinstance(value, int):
                series.append(Decimal(value))
                continue
            if isinstance(value, float):
                if not math.isfinite(value):
                    raise DataContractError(
                        f"non-finite value detected in source column '{field.name}'"
                    )
                series.append(Decimal(str(value)))
                continue
            if isinstance(value, Decimal):
                series.append(value)
                continue
            raise DataContractError(
                f"unsupported source column '{field.name}': values are of type "
                f"{type(value).__name__}"
            )
        columns[field.name] = series
    return columns


def _quantize_series(series: _Series) -> List[Optional[Decimal]]:
    """Round every finite result to 18 decimal places (ROUND_HALF_EVEN) under prec=38."""
    with localcontext() as ctx:
        ctx.prec = _ECON_PRECISION
        out: List[Optional[Decimal]] = []
        for value in series:
            if value is None:
                out.append(None)
            else:
                out.append(value.quantize(_FEATURE_SCALE, rounding=ROUND_HALF_EVEN))
        return out


def _to_decimal_array(values: List[Optional[Decimal]]) -> pa.Array:
    return pa.array(values, type=FEATURE_COLUMN_TYPE)


class MaterializationProvenance(BaseModel):
    """Immutable cryptographic provenance record for a single feature materialization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    feature_id: str
    feature_name: str
    canonical_formula: str
    proposal_provenance_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    source_table_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    materialized_table_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    feature_column_type: str
    provenance_digest: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    def compute_canonical_digest(self) -> str:
        """Compute deterministic SHA-256 fingerprint of this provenance excluding stored digest."""
        payload = {
            "canonical_formula": self.canonical_formula,
            "feature_column_type": self.feature_column_type,
            "feature_id": self.feature_id,
            "feature_name": self.feature_name,
            "materialized_table_sha256": self.materialized_table_sha256,
            "proposal_provenance_hash": self.proposal_provenance_hash,
            "source_table_sha256": self.source_table_sha256,
        }
        return CanonicalConfigSerializer.compute_sha256(payload)

    @model_validator(mode="after")
    def verify_provenance_integrity(self) -> "MaterializationProvenance":
        expected = self.compute_canonical_digest()
        if self.provenance_digest != expected:
            raise DataContractError(
                f"MaterializationProvenance digest mismatch: stored '{self.provenance_digest}' "
                f"!= computed '{expected}'."
            )
        return self


@dataclass(frozen=True)
class FeatureMaterializationResult:
    """Deterministic result of materializing one AI feature proposal."""

    table: pa.Table
    provenance: MaterializationProvenance


def _scalar_series(value: Decimal, n: int) -> _Series:
    return [value] * n


def _log_positive(v: Decimal) -> Optional[Decimal]:
    return v.ln() if v > 0 else None


def _sqrt_nonnegative(v: Decimal) -> Optional[Decimal]:
    return v.sqrt() if v >= 0 else None


def _sign(v: Decimal) -> Decimal:
    return Decimal(1) if v > 0 else (Decimal(-1) if v < 0 else Decimal(0))


def _pointwise(fn: _UnaryPointFn, args: Sequence[_Series], n: int) -> _Series:
    series = args[0]
    out: _Series = []
    for i in range(n):
        x = series[i]
        out.append(None if x is None else fn(x))
    return out


def _difference(args: Sequence[_Series], n: int) -> _Series:
    series, (lag,) = args[0], args[1:]
    lag_int = _int(lag[0])
    out: _Series = []
    for i in range(n):
        if i < lag_int:
            out.append(None)
            continue
        a, b = series[i], series[i - lag_int]
        out.append(None if a is None or b is None else a - b)
    return out


def _pct_change(args: Sequence[_Series], n: int) -> _Series:
    series, (lag,) = args[0], args[1:]
    lag_int = _int(lag[0])
    out: _Series = []
    for i in range(n):
        if i < lag_int:
            out.append(None)
            continue
        curr, base = series[i], series[i - lag_int]
        if curr is None or base is None or base == 0:
            out.append(None)
        else:
            out.append(curr / base - 1)
    return out


def _window_values(series: _Series, i: int, window: int) -> Optional[List[Decimal]]:
    if window <= 0:
        return None
    start = i - window + 1
    if start < 0:
        return None
    values = series[start : i + 1]
    return None if any(v is None for v in values) else [v for v in values if v is not None]


def _decimal_sum(values: Sequence[Decimal]) -> Decimal:
    """Explicit Decimal accumulator (deterministic left-to-right), no builtin int fallback."""
    acc: Decimal = Decimal(0)
    for value in values:
        acc += value
    return acc


def _rolling_sum(args: Sequence[_Series], n: int) -> _Series:
    series, (window,) = args[0], args[1:]
    w = _int(window[0])
    out: _Series = []
    for i in range(n):
        values = _window_values(series, i, w)
        out.append(None if values is None else _decimal_sum(values))
    return out


def _rolling_mean(args: Sequence[_Series], n: int) -> _Series:
    series, (window,) = args[0], args[1:]
    w = _int(window[0])
    out: _Series = []
    for i in range(n):
        values = _window_values(series, i, w)
        out.append(None if values is None else _decimal_sum(values) / w)
    return out


def _rolling_var(args: Sequence[_Series], n: int) -> _Series:
    series, (window,) = args[0], args[1:]
    w = _int(window[0])
    out: _Series = []
    for i in range(n):
        values = _window_values(series, i, w)
        if values is None or w < 2:
            out.append(None)
            continue
        w_dec = Decimal(w)
        mean: Decimal = _decimal_sum(values) / w_dec
        deviations = [_square(v - mean) for v in values]
        out.append(_decimal_sum(deviations) / (w_dec - 1))
    return out


def _square(value: Decimal) -> Decimal:
    return value * value


def _rolling_std(args: Sequence[_Series], n: int) -> _Series:
    series, (window,) = args[0], args[1:]
    w = _int(window[0])
    out: _Series = []
    for i in range(n):
        values = _window_values(series, i, w)
        if values is None or w < 2:
            out.append(None)
            continue
        w_dec = Decimal(w)
        mean: Decimal = _decimal_sum(values) / w_dec
        deviations = [_square(v - mean) for v in values]
        var = _decimal_sum(deviations) / (w_dec - 1)
        out.append(None if var <= 0 else var.sqrt())
    return out


def _rolling_min(args: Sequence[_Series], n: int) -> _Series:
    series, (window,) = args[0], args[1:]
    w = _int(window[0])
    out: _Series = []
    for i in range(n):
        values = _window_values(series, i, w)
        out.append(None if values is None else min(values))
    return out


def _rolling_max(args: Sequence[_Series], n: int) -> _Series:
    series, (window,) = args[0], args[1:]
    w = _int(window[0])
    out: _Series = []
    for i in range(n):
        values = _window_values(series, i, w)
        out.append(None if values is None else max(values))
    return out


def _rolling_median(args: Sequence[_Series], n: int) -> _Series:
    series, (window,) = args[0], args[1:]
    w = _int(window[0])
    out: _Series = []
    for i in range(n):
        values = _window_values(series, i, w)
        if values is None:
            out.append(None)
            continue
        ordered = sorted(values)
        mid = len(ordered) // 2
        if len(ordered) % 2 == 1:
            out.append(ordered[mid])
        else:
            out.append((ordered[mid - 1] + ordered[mid]) / Decimal(2))
    return out


def _ema(args: Sequence[_Series], n: int) -> _Series:
    series, (span,) = args[0], args[1:]
    w = _int(span[0])
    if w < 1:
        return [None] * n
    alpha = Decimal(2) / (w + 1)
    one_minus = 1 - alpha
    out: _Series = []
    carry: Optional[Decimal] = None
    for i in range(n):
        if i < w - 1:
            out.append(None)
            continue
        x = series[i]
        if x is None:
            out.append(None)
            continue
        if i == w - 1:
            seed_values = [v for v in series[0 : w - 1] if v is not None]
            if len(seed_values) != w - 1:
                carry = None
            else:
                carry = (sum(seed_values) + x) / w
            out.append(carry)
            continue
        if carry is None:
            out.append(None)
            continue
        carry = alpha * x + one_minus * carry
        out.append(carry)
    return out


def _zscore(args: Sequence[_Series], n: int) -> _Series:
    series, (window,) = args[0], args[1:]
    means = _rolling_mean([series, window], n)
    stds = _rolling_std([series, window], n)
    out: _Series = []
    for i in range(n):
        x, mean, std = series[i], means[i], stds[i]
        if x is None or mean is None or std is None or std == 0:
            out.append(None)
        else:
            out.append((x - mean) / std)
    return out


def _macd(args: Sequence[_Series], n: int) -> _Series:
    series, (short, long_n) = args[0], args[1:]
    s = _int(short[0])
    l_n = _int(long_n[0])
    short_ema = _ema([series, _scalar_series(Decimal(s), n)], n)
    long_ema = _ema([series, _scalar_series(Decimal(l_n), n)], n)
    out: _Series = []
    for i in range(n):
        a, b = short_ema[i], long_ema[i]
        out.append(None if a is None or b is None else a - b)
    return out


def _imbalance(args: Sequence[_Series], n: int) -> _Series:
    lhs, rhs = args[0], args[1]
    out: _Series = []
    for i in range(n):
        a, b = lhs[i], rhs[i]
        if a is None or b is None or (a + b) == 0:
            out.append(None)
        else:
            out.append((a - b) / (a + b))
    return out


# REGISTERED EVALUABLE OPERATORS â€” the ONLY names this module may execute.
# Absence of a canonical operator here means "no deterministic implementation": FAIL CLOSED.
_POINTWISE_UNARY: Dict[str, _UnaryPointFn] = {
    "abs": lambda v: v.__abs__(),
    "log": _log_positive,
    "sign": _sign,
    "sqrt": _sqrt_nonnegative,
    "exp": lambda v: v.exp(),
}

_WINDOWED_ARITY_TWO: Dict[str, Callable[[Sequence[_Series], int], _Series]] = {
    "diff": _difference,
    "pct_change": _pct_change,
    "rolling_mean": _rolling_mean,
    "rolling_std": _rolling_std,
    "rolling_var": _rolling_var,
    "rolling_sum": _rolling_sum,
    "rolling_min": _rolling_min,
    "rolling_max": _rolling_max,
    "rolling_median": _rolling_median,
    "ema": _ema,
    "zscore": _zscore,
}

_TRIPLE: Dict[str, Callable[[Sequence[_Series], int], _Series]] = {"macd": _macd}

_BINARY_PAIR: Dict[str, Callable[[Sequence[_Series], int], _Series]] = {"imbalance": _imbalance}

_EVALUATED_OPERATOR_NAMES: frozenset[str] = frozenset(
    set(_POINTWISE_UNARY) | set(_WINDOWED_ARITY_TWO) | set(_TRIPLE) | set(_BINARY_PAIR)
)


def _constant_value(node: ast.AST) -> Decimal:
    if not isinstance(node, ast.Constant) or isinstance(node.value, bool):
        raise DataContractError("only numeric constants are admissible in feature expressions")
    if isinstance(node.value, int):
        return Decimal(node.value)
    if isinstance(node.value, float):
        return Decimal(str(node.value))
    raise DataContractError(f"unsupported constant kind in feature expression: {node.value!r}")


def _positive_int_literal(node: ast.AST) -> int:
    value = _constant_value(node)
    if value == value.to_integral_value() and value > 0:
        return int(value)
    raise DataContractError("window/lag arguments must be positive integer literals")


class _ExpressionEvaluator:
    """Deterministic, whitelist-only evaluator over columns of Decimal series."""

    def __init__(self, columns: Dict[str, _Series], num_rows: int) -> None:
        self._columns = columns
        self._num_rows = num_rows

    def evaluate(self, node: ast.AST) -> _Series:
        if isinstance(node, ast.Expression):
            return self.evaluate(node.body)
        if isinstance(node, ast.Constant):
            return _scalar_series(_constant_value(node), self._num_rows)
        if isinstance(node, ast.Name):
            return self._current_row_variable(node)
        if isinstance(node, ast.Subscript):
            return self._evaluate_subscript(node)
        if isinstance(node, ast.Call):
            return self._evaluate_call(node)
        if isinstance(node, ast.BinOp):
            return self._evaluate_binop(node)
        if isinstance(node, ast.UnaryOp):
            return self._evaluate_unary(node)
        raise DataContractError(f"unsupported expression node: {node.__class__.__name__}")

    def _current_row_variable(self, node: ast.Name) -> _Series:
        series = self._columns.get(node.id)
        if series is None:
            raise DataContractError(f"variable '{node.id}' is not available in the source table")
        return series

    def _evaluate_subscript(self, node: ast.Subscript) -> _Series:
        if not isinstance(node.value, ast.Name) or node.slice is None:
            raise DataContractError("subscript target must be a named variable with a slice")
        series = self._columns.get(node.value.id)
        if series is None:
            raise DataContractError(
                f"variable '{node.value.id}' is not available in the source table"
            )
        offset = _future_offset(node.slice)
        if offset is None:
            raise DataContractError("subscript offset is not resolvable deterministically")
        if offset > 0:
            raise DataContractError(
                f"subscript references future index offset +{offset} (lookahead); "
                f"only past or current knowledge is admissible"
            )
        n = self._num_rows
        out: _Series = []
        for i in range(n):
            idx = i + offset
            out.append(None if idx < 0 else series[idx])
        return out

    def _evaluate_call(self, node: ast.Call) -> _Series:
        if node.keywords:
            raise DataContractError("keyword arguments are not supported in feature expressions")
        if not isinstance(node.func, ast.Name):
            raise DataContractError("operators must be plain named functions")
        name = node.func.id
        if name not in _EVALUATED_OPERATOR_NAMES:
            raise DataContractError(
                f"operator '{name}' has no deterministic implementation (fail closed)"
            )
        if name in _POINTWISE_UNARY:
            if len(node.args) != 1:
                raise DataContractError(f"operator '{name}' expects arity 1, got {len(node.args)}")
            arg_series = [self.evaluate(arg) for arg in node.args]
            return _pointwise(_POINTWISE_UNARY[name], arg_series, self._num_rows)
        if name in _WINDOWED_ARITY_TWO or name in _TRIPLE:
            expected = 2 if name in _WINDOWED_ARITY_TWO else 3
            if len(node.args) != expected:
                raise DataContractError(
                    f"operator '{name}' expects arity {expected}, got {len(node.args)}"
                )
            for param in node.args[1:]:
                if not isinstance(param, ast.Constant):
                    raise DataContractError(
                        f"operator '{name}' requires literal integer window/lag arguments"
                    )
                _positive_int_literal(param)
            series = self.evaluate(node.args[0])
            param_series = [self.evaluate(param) for param in node.args[1:]]
            arg_series = [series] + param_series
            if name in _WINDOWED_ARITY_TWO:
                return _WINDOWED_ARITY_TWO[name](arg_series, self._num_rows)
            return _TRIPLE[name](arg_series, self._num_rows)
        expected = 2
        if len(node.args) != expected:
            raise DataContractError(f"operator '{name}' expects arity {expected}, got {len(node.args)}")
        arg_series = [self.evaluate(arg) for arg in node.args]
        return _BINARY_PAIR[name](arg_series, self._num_rows)

    def _evaluate_binop(self, node: ast.BinOp) -> _Series:
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        out: _Series = []
        for i in range(self._num_rows):
            a, b = left[i], right[i]
            if a is None or b is None:
                out.append(None)
            elif isinstance(node.op, ast.Add):
                out.append(a + b)
            elif isinstance(node.op, ast.Sub):
                out.append(a - b)
            elif isinstance(node.op, ast.Mult):
                out.append(a * b)
            elif isinstance(node.op, ast.Div):
                out.append(None if b == 0 else a / b)
            else:
                raise DataContractError(
                    f"unsupported binary operator: {node.op.__class__.__name__}"
                )
        return out

    def _evaluate_unary(self, node: ast.UnaryOp) -> _Series:
        operand = self.evaluate(node.operand)
        out: _Series = []
        for v in operand:
            if v is None:
                out.append(None)
            elif isinstance(node.op, ast.USub):
                out.append(-v)
            elif isinstance(node.op, ast.UAdd):
                out.append(v)
            else:
                raise DataContractError(
                    f"unsupported unary operator: {node.op.__class__.__name__}"
                )
        return out


class FeatureMaterializer:
    """Materialize a validated AIFeatureProposal into a canonical point-in-time feature column."""

    def __init__(self) -> None:
        self._validator = CausalAstValidator()

    def materialize(
        self, proposal: AIFeatureProposal, table: pa.Table
    ) -> FeatureMaterializationResult:
        if not isinstance(proposal, AIFeatureProposal):
            raise DataContractError(
                f"materialization requires an AIFeatureProposal, got {type(proposal).__name__}"
            )
        if not proposal.is_strictly_causal or not proposal.point_in_time_verified:
            raise DataContractError(
                f"proposal '{proposal.feature_id}' is not causality-certified"
            )
        if proposal.lookahead_terms_detected != 0:
            raise DataContractError(
                f"proposal '{proposal.feature_id}' reports {proposal.lookahead_terms_detected} "
                f"lookahead terms"
            )

        available_variables: Tuple[str, ...] = tuple(
            field.name for field in table.schema if _is_numeric_column(field)
        )
        validation = self._validator.validate_expression(
            proposal.mathematical_formula, available_variables
        )
        if not validation.point_in_time_verified:
            raise DataContractError(
                f"formula '{proposal.mathematical_formula}' failed materialization-time "
                f"revalidation: {'; '.join(validation.violations)}"
            )

        if proposal.feature_name in table.column_names:
            raise DataContractError(
                f"feature column '{proposal.feature_name}' already exists in the source table"
            )

        try:
            canonical_formula = canonical_form(proposal.mathematical_formula)
        except FeatureExpressionError as exc:
            raise DataContractError(
                f"formula is not canonically representable: {exc}"
            ) from exc

        try:
            tree = ast.parse(canonical_formula, mode="eval")
        except SyntaxError as exc:
            raise DataContractError(f"formula failed to parse: {exc.msg}") from exc

        with localcontext() as ctx:
            ctx.prec = _ECON_PRECISION
            columns = _to_decimal_columns(table)
            num_rows = table.num_rows
            series = _ExpressionEvaluator(columns, num_rows).evaluate(tree)
            feature_values = _quantize_series(series)

        feature_field = pa.field(proposal.feature_name, FEATURE_COLUMN_TYPE)
        featured_table = table.append_column(
            feature_field, _to_decimal_array(feature_values)
        )

        source_table_sha256 = calculate_canonical_feature_table_sha256(table)
        materialized_table_sha256 = calculate_canonical_feature_table_sha256(featured_table)

        provenance_payload = {
            "canonical_formula": canonical_formula,
            "feature_column_type": str(feature_field.type),
            "feature_id": proposal.feature_id,
            "feature_name": proposal.feature_name,
            "materialized_table_sha256": materialized_table_sha256,
            "proposal_provenance_hash": proposal.provenance_hash,
            "source_table_sha256": source_table_sha256,
        }
        provenance_digest = CanonicalConfigSerializer.compute_sha256(provenance_payload)

        provenance = MaterializationProvenance(
            feature_id=proposal.feature_id,
            feature_name=proposal.feature_name,
            canonical_formula=canonical_formula,
            proposal_provenance_hash=proposal.provenance_hash,
            source_table_sha256=source_table_sha256,
            materialized_table_sha256=materialized_table_sha256,
            feature_column_type=str(feature_field.type),
            provenance_digest=provenance_digest,
        )
        return FeatureMaterializationResult(table=featured_table, provenance=provenance)