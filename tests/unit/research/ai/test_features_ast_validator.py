"""Unit tests for Phase 14 Slice 3 CausalAstValidator.

Test priority order (AGENTS.md Rule 14): happy path -> boundary -> malformed ->
contradictory -> adversarial -> permutation -> numerical stability -> golden reference.

Enforced invariants:
- lead()/future()/forward()/delay()/shift() and random/time functions rejected.
- Whole-dataset aggregation rejected (cross-future leakage).
- Future index offsets such as x[t+1] rejected; past offsets x[t-1] admissible.
- Unknown operators rejected; arity mismatches rejected; unbound names rejected.
- Syntax errors fail closed. Manifest contract mirrors governance invariants.
"""

import json

import pytest
from pydantic import ValidationError

from acash.research.ai.features import CausalAstValidator
from acash.research.ai.features.library import canonical_form


@pytest.fixture
def validator() -> CausalAstValidator:
    return CausalAstValidator()


def test_happy_path_windowed_expression(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("zscore(close,21)", ("close",))
    assert result.is_strictly_causal is True
    assert result.point_in_time_verified is True
    assert result.lookahead_terms_detected == 0
    assert result.violations == ()
    assert json.loads(result.canonical_ast_json)["canonical_form"] == "zscore(close,21)"


def test_happy_path_macd_expression(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("macd(close,10,50)", ("close",))
    assert result.is_strictly_causal is True
    assert result.lookahead_terms_detected == 0


def test_happy_path_past_subscript(validator: CausalAstValidator) -> None:
    """x[t-1] only references past/current knowledge and is admissible."""
    result = validator.validate_expression("close[t-1]", ("close",))
    assert result.is_strictly_causal is True
    assert result.lookahead_terms_detected == 0


def test_happy_path_reserved_time_name(validator: CausalAstValidator) -> None:
    """t is a reserved time index, not an undeclared variable."""
    result = validator.validate_expression("close[t]", ("close",))
    assert result.is_strictly_causal is True


def test_rejects_lead_operator(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("lead(close,1)", ("close",))
    assert result.is_strictly_causal is False
    assert result.point_in_time_verified is False
    assert result.lookahead_terms_detected == 1


def test_rejects_shift_delay_forward(validator: CausalAstValidator) -> None:
    for expr in ("shift(close,1)", "delay(close,5)", "forward(close,3)", "future(close,2)"):
        result = validator.validate_expression(expr, ("close",))
        assert result.is_strictly_causal is False, expr
        assert result.lookahead_terms_detected >= 1, expr


def test_rejects_non_deterministic_functions(validator: CausalAstValidator) -> None:
    for expr in ("random()", "choice(close)", "normalvariate(0,1)"):
        result = validator.validate_expression(expr, ("close",))
        assert result.is_strictly_causal is False, expr
        assert result.lookahead_terms_detected == 1, expr


def test_rejects_bare_global_aggregates(validator: CausalAstValidator) -> None:
    for expr in ("mean(close)", "std(close)", "median(close)", "sum(close)"):
        result = validator.validate_expression(expr, ("close",))
        assert result.is_strictly_causal is False, expr
        assert any("whole-dataset" in v for v in result.violations), expr


def test_rejects_cross_future_normalization(validator: CausalAstValidator) -> None:
    """The canonical leakage pattern (x - mean(x)) / std(x) must be rejected in full."""
    result = validator.validate_expression("(close - mean(close)) / std(close)", ("close",))
    assert result.is_strictly_causal is False
    assert len(result.violations) >= 2


def test_rejects_unknown_operator(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("ama(close,5)", ("close",))
    assert result.is_strictly_causal is False
    assert any("unknown operator 'ama'" in v for v in result.violations)


def test_rejects_arity_mismatches(validator: CausalAstValidator) -> None:
    assert validator.validate_expression("rolling_mean(close)", ("close",)).is_strictly_causal is False
    assert validator.validate_expression("ema(close,10,5)", ("close",)).is_strictly_causal is False
    assert validator.validate_expression("imbalance(close)", ("close",)).is_strictly_causal is False
    assert validator.validate_expression("macd(close,10)", ("close",)).is_strictly_causal is False


def test_rejects_unbound_variables(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("ema(close,alpha)", ("close",))
    assert result.is_strictly_causal is False
    assert any("'alpha' is not among available variables" in v for v in result.violations)

    result2 = validator.validate_expression("zscore(nasdaq,21)", ("spx",))
    assert result2.is_strictly_causal is False
    assert any("'nasdaq' is not among available variables" in v for v in result2.violations)


def test_rejects_future_index_offsets(validator: CausalAstValidator) -> None:
    for expr in ("close[t+1]", "close[1]", "close[3]"):
        result = validator.validate_expression(expr, ("close",))
        assert result.is_strictly_causal is False, expr
        assert result.lookahead_terms_detected == 1, expr
        assert any("future index" in v for v in result.violations), expr


def test_counts_multiple_lookahead_terms(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("close[t+1] + lead(open,1)", ("close", "open"))
    assert result.is_strictly_causal is False
    assert result.lookahead_terms_detected == 2


def test_rejects_expression_with_no_declared_variable(
    validator: CausalAstValidator,
) -> None:
    """Bare literals and lone reserved names must fail closed as empty features."""
    for expr in ("3.14", "21", "window", "t"):
        result = validator.validate_expression(expr, ("close",))
        assert result.is_strictly_causal is False, expr
        assert any("no declared variable" in v for v in result.violations), expr


def test_reserved_time_index_with_variable_remains_valid(
    validator: CausalAstValidator,
) -> None:
    """close[t] touches the declared variable and is a valid past/current reference."""
    result = validator.validate_expression("close[t]", ("close",))
    assert result.is_strictly_causal is True
    assert result.lookahead_terms_detected == 0


def test_syntax_error_fails_closed(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("close +", ("close",))
    assert result.is_strictly_causal is False
    assert result.point_in_time_verified is False
    assert result.violations[0].startswith("expression failed to parse")


def test_forbidden_attribute_operator(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("numpy.mean(close)", ("close",))
    assert result.is_strictly_causal is False
    assert "plain named functions" in result.violations[0]


def test_determinism_across_validation_runs(validator: CausalAstValidator) -> None:
    r1 = validator.validate_expression("(close - mean(close)) / std(close)", ("close",))
    r2 = validator.validate_expression("(close - mean(close)) / std(close)", ("close",))
    assert r1.model_dump() == r2.model_dump()


def test_permutation_invariance_of_available_variables(validator: CausalAstValidator) -> None:
    a = validator.validate_expression("ema(close,21)", ("close", "volume"))
    b = validator.validate_expression("ema(close,21)", ("volume", "close"))
    assert a.is_strictly_causal == b.is_strictly_causal
    assert a.model_dump() == b.model_dump()


def test_canonical_form_collapses_equivalent_leakage_detection(
    validator: CausalAstValidator,
) -> None:
    """ema-diff and macd canonicalize to the same form; both must validate identically."""
    raw = "ema(close,10) - ema(close,50)"
    macd_form = canonical_form(raw)
    assert macd_form == "macd(close,10,50)"
    raw_result = validator.validate_expression(raw, ("close",))
    macd_result = validator.validate_expression(macd_form, ("close",))
    assert raw_result.is_strictly_causal is True
    assert macd_result.is_strictly_causal is True


def test_result_is_immutable(validator: CausalAstValidator) -> None:
    result = validator.validate_expression("ema(close,21)", ("close",))
    with pytest.raises(ValidationError):
        result.is_strictly_causal = False
    with pytest.raises(ValidationError):
        result.violations = ("tampered",)


def test_no_feature_module_reaches_frozen_core_namespaces() -> None:
    """Slice 3 module attributes must only reference research/core, never frozen execution."""
    import importlib
    import inspect

    forbidden_tops = {
        "backtest",
        "execution",
        "portfolio",
        "account",
        "strategy",
        "broker",
        "mt5",
        "cli",
        "acash_governance",
    }
    for mod_name in ("library", "ast_validator"):
        module = importlib.import_module(f"acash.research.ai.features.{mod_name}")
        for obj in vars(module).values():
            if inspect.ismodule(obj):
                full = obj.__name__
                if not full.startswith("acash."):
                    continue
                top = full.split(".")[1]
                assert top not in forbidden_tops, (
                    f"feature module {mod_name} leaked frozen-core import: {full}"
                )