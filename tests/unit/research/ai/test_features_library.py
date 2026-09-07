"""Unit tests for Phase 14 Slice 3 feature operator library and canonicalization.

Tests:
- Registered operator registry integrity (arity, windowed flags, known set).
- Deterministic canonical-form normalization.
- Phase 14 Master Plan Section 5 operator-equivalence: ema-x - ema-y -> macd(x,y).
- Alias equivalence: sma -> rolling_mean (never registered as its own operator).
- Fail-closed rejection of non-canonicalizable AST nodes.
- Determinism / permutation independence of canonical output.
"""

import pytest

from acash.research.ai.features.library import (
    ALIASES,
    FORBIDDEN_OPERATORS,
    GLOBAL_AGGREGATE_NAMES,
    KNOWN_OPERATORS,
    OPERATOR_ARITY,
    FeatureExpressionError,
    FeatureOperator,
    canonical_form,
)


def test_registry_consistency() -> None:
    """Assert the operator registry is internally consistent."""
    assert all(op.name in KNOWN_OPERATORS for op in [
        FeatureOperator("abs", 1, False, "x"),
        FeatureOperator("ema", 2, True, "x"),
        FeatureOperator("macd", 3, True, "x"),
        FeatureOperator("imbalance", 2, False, "x"),
    ])
    assert OPERATOR_ARITY["ema"] == 2
    assert OPERATOR_ARITY["macd"] == 3
    assert OPERATOR_ARITY["abs"] == 1
    assert OPERATOR_ARITY["imbalance"] == 2


def test_knowded_operators_do_not_include_leakage_aggregates() -> None:
    """Whole-dataset aggregates must NOT be valid operators."""
    assert GLOBAL_AGGREGATE_NAMES.isdisjoint(KNOWN_OPERATORS)


def test_forbidden_operators_are_not_known() -> None:
    """Hard-forbidden operator names must never be registered primitives."""
    assert FORBIDDEN_OPERATORS.isdisjoint(KNOWN_OPERATORS)


def test_alias_sma_is_not_registered_operator() -> None:
    """sma is an alias for rolling_mean, not an independently admissible operator."""
    assert "sma" not in KNOWN_OPERATORS
    assert ALIASES["sma"] == "rolling_mean"


def test_canonical_form_simple_expression() -> None:
    """Unary applications canonicalize deterministically."""
    assert canonical_form("ema(close,21)") == "ema(close,21)"
    assert canonical_form("abs(close)") == "abs(close)"


def test_canonical_form_deterministic_across_repetition() -> None:
    """The same expression always canonicalizes to the same string."""
    assert canonical_form("ema(close,21)") == canonical_form("ema(close,21)")
    assert canonical_form("zscore(close,21)") == canonical_form("zscore(close, 21)")


def test_canonical_form_normalizes_sma_alias() -> None:
    """sma(x,N) is normalized to the canonical rolling_mean(x,N) form."""
    assert canonical_form("sma(close,21)") == "rolling_mean(close,21)"


def test_canonical_form_macd_operator_equivalence() -> None:
    """Phase 14 Master Plan Section 5: ema(x,10) - ema(x,50) == macd(x,10,50)."""
    assert canonical_form("ema(close,10) - ema(close,50)") == "macd(close,10,50)"
    assert canonical_form("ema(close, 10) - ema(close, 50)") == "macd(close,10,50)"


def test_canonical_form_macd_requires_ascending_params() -> None:
    """Only short < long collapses to macd; the long-short ordering is preserved."""
    assert canonical_form("ema(close,50) - ema(close,10)") != "macd(close,10,50)"


def test_canonical_form_macd_requires_identical_variables() -> None:
    """ema of differing variables must not collapse to macd."""
    assert canonical_form("ema(close,10) - ema(volume,50)") == "(ema(close,10)-ema(volume,50))"


def test_canonical_form_int_float_normalization() -> None:
    """Integer-valued floats normalize to their integer string."""
    assert canonical_form("log(2.0)") == "log(2)"
    assert canonical_form("ema(close,21.0) - ema(close,35.0)") == "macd(close,21,35)"


def test_canonical_form_boolean_literal() -> None:
    """Boolean literals canonicalize deterministically to 1/0."""
    assert canonical_form("(close + True)") == "(close+1)"


def test_canonical_form_fail_closed_on_unsupported_node() -> None:
    """Non-symbolic AST nodes must raise FeatureExpressionError, never silently pass."""
    with pytest.raises(FeatureExpressionError):
        canonical_form("[close, 1]")
    with pytest.raises(FeatureExpressionError):
        canonical_form("lambda: close")
    with pytest.raises(FeatureExpressionError):
        canonical_form("[x for x in close]")


def test_canonical_form_fail_closed_on_keyword_arguments() -> None:
    """Keyword arguments must not be silently dropped from the canonical form."""
    with pytest.raises(FeatureExpressionError):
        canonical_form("ema(close, n=21)")
    with pytest.raises(FeatureExpressionError):
        canonical_form("rolling_mean(close, window=21)")


def test_canonical_form_tie_symmetry() -> None:
    """Canonical output depends only on expression structure, not on hashing/order."""
    a = canonical_form("(close - open)")
    b = canonical_form("(open - close)")
    assert a != b
    assert canonical_form("(close - open) / (close + open)") == "((close-open)/(close+open))"