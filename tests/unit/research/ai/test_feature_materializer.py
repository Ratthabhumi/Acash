"""Unit tests for Seam B: trusted causal materialization of AIFeatureProposal.

Test priority order (AGENTS.md Rule 14): happy path -> boundary -> malformed ->
contradictory -> adversarial -> permutation -> numerical stability -> golden reference.

Enforced invariants:
- Only whitelist operators from the canonical feature vocabulary are executable.
- Deterministic warmup (explicit NULL, never future-padding); same-bar two-series math.
- Whole-dataset aggregates, future subscripts, unknown operators/variables, and
  non-causal proposals fail closed with DataContractError.
- No eval/exec/dynamic dispatch; the materializer source is import-scanned.
- Provenance digests are deterministic and detect any tamper.
- Output is decimal128(38, 18) and preserves every source column byte-for-byte.
"""

import ast
import inspect
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path

from typing import Any

import pyarrow as pa
import pytest
from pydantic import ValidationError

from acash.core.domain.exceptions import DataContractError
from acash.research.ai.features import (
    FEATURE_COLUMN_TYPE,
    FeatureMaterializationResult,
    FeatureMaterializer,
    MaterializationProvenance,
    canonical_form,
)
from acash.research.ai.features.library import KNOWN_OPERATORS
from acash.research.ai.features.materializer import _EVALUATED_OPERATOR_NAMES
from acash.research.ai.schema import AIFeatureProposal

MANDATORY_OPERATORS = frozenset(
    {
        "abs",
        "exp",
        "log",
        "sign",
        "sqrt",
        "diff",
        "pct_change",
        "rolling_mean",
        "rolling_std",
        "rolling_var",
        "rolling_sum",
        "rolling_min",
        "rolling_max",
        "rolling_median",
        "ema",
        "zscore",
        "imbalance",
        "macd",
    }
)

QUANTUM = Decimal("1e-18")


def _to_q_arg(value: object) -> int | float | Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    raise AssertionError(f"unexpected expected-value type: {type(value).__name__}")


def _q(value: int | float | Decimal | None) -> Decimal | None:
    """Quantize an expected value identically to the materializer (18dp, ROUND_HALF_EVEN)."""
    if value is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 38
        return Decimal(value).quantize(QUANTUM, rounding=ROUND_HALF_EVEN)


def _proposal(formula: str, name: str = "f_test_rc", **overrides: object) -> AIFeatureProposal:
    return AIFeatureProposal(
        feature_id="AI-FEAT-0123456789abcdef0123456789abcdef",
        feature_name=name,
        mathematical_formula=formula,
        ast_representation_json="{}",
        intended_microstructure_signal="causal deterministic test feature signal",
        provenance_hash="0" * 64,
        **overrides,  # type: ignore[arg-type]
    )


@pytest.fixture
def materializer() -> FeatureMaterializer:
    return FeatureMaterializer()


@pytest.fixture
def sample_table() -> pa.Table:
    values = [1, 2, 3, 4, 5]
    return pa.table(
        {
            "close": pa.array(values, type=pa.float64()),
            "volume": pa.array([10] * len(values), type=pa.int64()),
            "time": pa.array(["t0", "t1", "t2", "t3", "t4"]),
            "sector": pa.array(["a", "a", "a", "a", "a"]),
        }
    )


def _values(result: FeatureMaterializationResult, name: str) -> list[Any]:
    values: list[Any] = result.table.column(name).to_pylist()
    return values


class TestGoldenNumerics:
    """Group A: canonical golden arithmetic references (18dp ROUND_HALF_EVEN)."""

    @pytest.mark.parametrize(
        ("formula", "expected"),
        [
            ("close", [1, 2, 3, 4, 5]),
            ("abs(close)", [1, 2, 3, 4, 5]),
            ("sign(close)", [1, 1, 1, 1, 1]),
            ("-close", [-1, -2, -3, -4, -5]),
            ("diff(close, 1)", [None, 1, 1, 1, 1]),
            ("diff(close, 2)", [None, None, 2, 2, 2]),
            (
                "pct_change(close, 1)",
                [None, 1, Decimal("0.5"), Decimal("1") / 3, Decimal("0.25")],
            ),
            ("rolling_sum(close, 2)", [None, 3, 5, 7, 9]),
            ("rolling_min(close, 2)", [None, 1, 2, 3, 4]),
            ("rolling_max(close, 2)", [None, 2, 3, 4, 5]),
            ("rolling_median(close, 4)", [None, None, None, Decimal("2.5"), Decimal("3.5")]),
            ("rolling_mean(close, 3)", [None, None, 2, 3, 4]),
            (
                "imbalance(close, volume)",
                [
                    Decimal(-9) / 11,
                    Decimal(-8) / 12,
                    Decimal(-7) / 13,
                    Decimal(-6) / 14,
                    Decimal(-5) / 15,
                ],
            ),
            ("close[t-1]", [None, 1, 2, 3, 4]),
            ("close[0]", [1, 2, 3, 4, 5]),
            ("close[t]", [1, 2, 3, 4, 5]),
        ],
    )
    def test_golden_finite(
        self, materializer: FeatureMaterializer, sample_table: pa.Table, formula: str, expected: list[object]
    ) -> None:
        result = materializer.materialize(_proposal(formula), sample_table)
        assert _values(result, "f_test_rc") == [_q(_to_q_arg(v)) for v in expected]

    def test_golden_log_sqrt_exp(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        result = materializer.materialize(_proposal("log(close)"), sample_table)
        assert _values(result, "f_test_rc") == [_q(Decimal(v).ln()) for v in (1, 2, 3, 4, 5)]
        result = materializer.materialize(_proposal("sqrt(close)"), sample_table)
        assert _values(result, "f_test_rc") == [_q(Decimal(v).sqrt()) for v in (1, 2, 3, 4, 5)]
        result = materializer.materialize(_proposal("exp(close) / 100"), sample_table)
        assert _values(result, "f_test_rc") == [_q(Decimal(v).exp() / 100) for v in (1, 2, 3, 4, 5)]

    def test_golden_rolling_var_std_ddof1(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        result = materializer.materialize(_proposal("rolling_std(close, 3)"), sample_table)
        assert _values(result, "f_test_rc") == [None, None, _q(1), _q(1), _q(1)]
        result = materializer.materialize(_proposal("rolling_var(close, 3)"), sample_table)
        assert _values(result, "f_test_rc") == [None, None, _q(1), _q(1), _q(1)]

    def test_golden_zscore(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        result = materializer.materialize(_proposal("zscore(close, 3)"), sample_table)
        assert _values(result, "f_test_rc") == [_q(_to_q_arg(v)) for v in (None, None, 1, 1, 1)]

    def test_golden_ema_recursion(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([2, 4, 6, 8, 10], type=pa.float64())})
        result = materializer.materialize(_proposal("ema(close, 3)"), table)
        alpha = Decimal("0.5")
        seed = _q(Decimal(4))
        e3 = _q(alpha * 8 + (1 - alpha) * Decimal(4))
        e4 = _q(alpha * 10 + (1 - alpha) * (e3 if e3 is not None else Decimal(4)))
        assert _values(result, "f_test_rc") == [None, None, seed, e3, e4]

    def test_golden_macd(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        result = materializer.materialize(_proposal("macd(close, 3, 5)"), sample_table)
        assert _values(result, "f_test_rc") == [_q(v) for v in (None, None, None, None, 1)]

    def test_zero_window_is_rejected(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        with pytest.raises(DataContractError):
            materializer.materialize(_proposal("rolling_mean(close, 0)"), sample_table)

    def test_window_beyond_rows_is_all_null(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        result = materializer.materialize(_proposal("diff(close, 6)"), sample_table)
        assert _values(result, "f_test_rc") == [None] * 5


class TestNullPropagation:
    """Group B: deterministic warmup boundaries and explicit NULL (never future-padding)."""

    def test_rolling_window_containing_null_is_null(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([1, 2, None, 4, 5], type=pa.float64())})
        result = materializer.materialize(_proposal("rolling_mean(close, 3)"), table)
        assert _values(result, "f_test_rc") == [None] * 5

    def test_pct_change_zero_base_is_null(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([0, 5, 10], type=pa.float64())})
        result = materializer.materialize(_proposal("pct_change(close, 1)"), table)
        assert _values(result, "f_test_rc") == [_q(v) for v in (None, None, 1)]

    def test_division_by_zero_is_null(self, materializer: FeatureMaterializer) -> None:
        table = pa.table(
            {
                "num": pa.array([Decimal(1), Decimal(2), Decimal(3)], type=pa.decimal128(10, 0)),
                "zero": pa.array([0, 0, 0], type=pa.int64()),
            }
        )
        result = materializer.materialize(_proposal("num / zero"), table)
        assert _values(result, "f_test_rc") == [None] * 3

    def test_domain_violations_are_null(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([0, -1, 4], type=pa.float64())})
        assert _values(materializer.materialize(_proposal("log(close)"), table), "f_test_rc") == [
            None,
            None,
            _q(Decimal(4).ln()),
        ]
        assert _values(materializer.materialize(_proposal("sqrt(close)"), table), "f_test_rc") == [
            _q(0),
            None,
            _q(2),
        ]

    def test_rolling_std_span_one_is_all_null(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        result = materializer.materialize(_proposal("rolling_std(close, 1)"), sample_table)
        assert _values(result, "f_test_rc") == [None] * 5

    def test_ema_null_input_poisons_tail(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([1, 2, None, 4, 5], type=pa.float64())})
        result = materializer.materialize(_proposal("ema(close, 3)"), table)
        assert _values(result, "f_test_rc") == [None] * 5


class TestFailClosedContract:
    """Group C: causality, whitelist, and proposal-certificate enforcement."""

    @pytest.mark.parametrize(
        "formula",
        [
            "close[t+1]",
            "lead(close,1)",
            "shift(close,2)",
            "forward(close,3)",
            "sma(close,5)",
            "mean(close)",
            "std(close)",
            "abs(close, 2)",
            "rolling_mean(close, 3, 4)",
            "rolling_mean(close, close)",
            "close ** 2",
            "close // 2",
            "close % 2",
            "1 if close > 0 else 0",
            "sector",
        ],
    )
    def test_unsafe_or_unimplemented_formulas_fail_closed(
        self, materializer: FeatureMaterializer, sample_table: pa.Table, formula: str
    ) -> None:
        with pytest.raises(DataContractError):
            materializer.materialize(_proposal(formula), sample_table)

    def test_non_causal_proposal_certificates_fail_closed(self, materializer: FeatureMaterializer) -> None:
        with pytest.raises(DataContractError):
            materializer.materialize(_proposal("close", is_strictly_causal=False), sample_table)
        with pytest.raises(DataContractError):
            materializer.materialize(_proposal("close", point_in_time_verified=False), sample_table)
        with pytest.raises(DataContractError):
            materializer.materialize(_proposal("close", lookahead_terms_detected=1), sample_table)

    def test_wrong_argument_object_fails_closed(self, materializer: FeatureMaterializer) -> None:
        with pytest.raises(DataContractError):
            materializer.materialize("close", sample_table)  # type: ignore[arg-type]

    def test_feature_name_collision_fails_closed(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        with pytest.raises(DataContractError):
            materializer.materialize(_proposal("close", name="close"), sample_table)

    def test_rejecting_formula_referencing_non_numeric_column(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        with pytest.raises(DataContractError):
            materializer.materialize(_proposal("imbalance(close, sector)"), sample_table)

    def test_non_finite_source_value_fails_closed(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([1.0, float("nan"), 3.0], type=pa.float64())})
        with pytest.raises(DataContractError):
            materializer.materialize(_proposal("close"), table)


class TestDeterminism:
    """Group D: byte-reproducible output; mutation-sensitive digests."""

    def test_identical_input_reproduces_identical_provenance(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        first = materializer.materialize(_proposal("pct_change(close, 1)"), sample_table)
        second = materializer.materialize(_proposal("pct_change(close, 1)"), sample_table)
        assert first.provenance == second.provenance
        assert first.table.equals(second.table)

    def test_source_mutation_changes_digests(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        proposal = _proposal("pct_change(close, 1)")
        original = materializer.materialize(proposal, sample_table)
        mutated = sample_table.set_column(0, "close", pa.array([1, 2, 3, 4, 100], type=pa.float64()))
        altered = materializer.materialize(proposal, mutated)
        assert original.provenance.source_table_sha256 != altered.provenance.source_table_sha256
        assert (
            original.provenance.materialized_table_sha256
            != altered.provenance.materialized_table_sha256
        )

    def test_row_order_permutation_keeps_per_row_feature_values(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        proposal = _proposal("close")
        original = materializer.materialize(proposal, sample_table)
        permuted = sample_table.take(pa.array([4, 3, 2, 1, 0]))
        re_materialized = materializer.materialize(proposal, permuted)
        assert re_materialized.provenance.source_table_sha256 == original.provenance.source_table_sha256
        assert _values(re_materialized, "f_test_rc") == [_q(v) for v in (5, 4, 3, 2, 1)]


class TestProvenanceIntegrity:
    """Group E: provenance digest binding and tamper detection."""

    def test_provenance_digest_verifies(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        provenance = materializer.materialize(_proposal("close"), sample_table).provenance
        assert provenance.provenance_digest == provenance.compute_canonical_digest()
        assert provenance.proposal_provenance_hash == "0" * 64
        assert provenance.feature_column_type == str(FEATURE_COLUMN_TYPE)

    def test_tampered_source_hash_rejected(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        provenance = materializer.materialize(_proposal("close"), sample_table).provenance
        with pytest.raises(DataContractError):
            MaterializationProvenance(**{**provenance.model_dump(), "source_table_sha256": "f" * 64})

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MaterializationProvenance(
                feature_id="AI-FEAT-0123456789abcdef0123456789abcdef",
                feature_name="f_test_rc",
                canonical_formula="close",
                proposal_provenance_hash="0" * 64,
                source_table_sha256="0" * 64,
                materialized_table_sha256="0" * 64,
                feature_column_type="decimal128(38, 18)",
                provenance_digest="0" * 64,
                **{"rogue": "x"},
            )

    def test_source_and_materialized_digests_differ(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        provenance = materializer.materialize(_proposal("pct_change(close, 1)"), sample_table).provenance
        assert provenance.source_table_sha256 != provenance.materialized_table_sha256


class TestPhaseFourCompatibility:
    """Group F: output satisfies the Phase 4 feature-table contract conventions."""

    def test_output_schema_and_axis_preservation(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        result = materializer.materialize(_proposal("pct_change(close, 1)", name="f_ret_1"), sample_table)
        assert result.table.column_names == ["close", "volume", "time", "sector", "f_ret_1"]
        assert result.table.field("f_ret_1").type == FEATURE_COLUMN_TYPE
        assert result.table.field("f_ret_1").type == pa.decimal128(38, 18)
        assert result.table.column("time").to_pylist() == ["t0", "t1", "t2", "t3", "t4"]
        assert result.table.column("sector").to_pylist() == ["a"] * 5
        assert result.table.column("close").to_pylist() == [1, 2, 3, 4, 5]

    def test_canonical_formula_propagated(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        result = materializer.materialize(
            _proposal("2 * rolling_mean(close, 3) - close[t-1]"), sample_table
        )
        assert result.provenance.canonical_formula == canonical_form("2 * rolling_mean(close, 3) - close[t-1]")
        assert result.provenance.canonical_formula == "((2*rolling_mean(close,3))-close[(t-1)])"


class TestDegenerateInputs:
    """Group H: empty, degenerate, and adversarial data surfaces."""

    def test_empty_table(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([], type=pa.float64())})
        result = materializer.materialize(_proposal("close"), table)
        assert result.table.num_rows == 0
        assert _values(result, "f_test_rc") == []

    def test_single_row_table(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([7.0], type=pa.float64())})
        assert _values(materializer.materialize(_proposal("close"), table), "f_test_rc") == [_q(7)]
        assert _values(
            materializer.materialize(_proposal("rolling_mean(close, 3)"), table), "f_test_rc"
        ) == [None]

    def test_all_null_source_column(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([None, None, None], type=pa.float64())})
        assert _values(materializer.materialize(_proposal("close"), table), "f_test_rc") == [None, None, None]
        assert _values(
            materializer.materialize(_proposal("ema(close, 3)"), table), "f_test_rc"
        ) == [None, None, None]

    def test_zero_variance_zscore_is_null(self, materializer: FeatureMaterializer) -> None:
        table = pa.table({"close": pa.array([5, 5, 5, 5, 5], type=pa.float64())})
        result = materializer.materialize(_proposal("zscore(close, 3)"), table)
        assert _values(result, "f_test_rc") == [None] * 5


class TestSecurityBoundary:
    """Whitelist-only dispatch: no eval/exec/dynamic import in the materializer source."""

    @staticmethod
    def _module_source() -> str:
        module_path = Path(inspect.getsourcefile(FeatureMaterializer))  # type: ignore[arg-type]
        return module_path.read_text(encoding="utf-8")

    def test_all_executable_operators_are_canonical(self) -> None:
        assert MANDATORY_OPERATORS == _EVALUATED_OPERATOR_NAMES
        assert MANDATORY_OPERATORS.issubset(set(KNOWN_OPERATORS))

    def test_source_contains_no_dynamic_execution(self) -> None:
        source = self._module_source()
        for banned in ("eval(", "exec(", "compile(", "__import__", "importlib", "globals(", "locals("):
            assert banned not in source

    def test_source_imports_stay_within_boundary(self) -> None:
        tree = ast.parse(self._module_source())
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        forbidden_prefixes = (
            "acash.validation",
            "acash.backtest",
            "acash.execution",
            "acash.portfolio",
            "acash.risk",
            "acash.runtime",
            "acash.broker",
            "acash.capital",
            "numpy",
            "pandas",
        )
        assert imported
        for name in imported:
            assert not name.startswith(forbidden_prefixes), f"forbidden import: {name}"

    def test_call_graph_resolves_to_module_helpers_or_pure_builtins(self) -> None:
        tree = ast.parse(self._module_source())
        safe_builtins = {
            "abs",
            "any",
            "bool",
            "dict",
            "frozenset",
            "int",
            "isinstance",
            "len",
            "list",
            "max",
            "min",
            "range",
            "round",
            "set",
            "sorted",
            "str",
            "sum",
            "tuple",
            "type",
            "Decimal",
        }
        statically_bound: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                statically_bound.add(node.name)
                args: list[ast.arg] = list(node.args.posonlyargs)
                args += list(node.args.args) + list(node.args.kwonlyargs)
                if node.args.vararg is not None:
                    args.append(node.args.vararg)
                if node.args.kwarg is not None:
                    args.append(node.args.kwarg)
                statically_bound.update(arg.arg for arg in args)
            elif isinstance(node, ast.ClassDef):
                statically_bound.add(node.name)
            elif isinstance(node, ast.Lambda):
                statically_bound.update(arg.arg for arg in node.args.posonlyargs)
                statically_bound.update(arg.arg for arg in node.args.args + node.args.kwonlyargs)
                if node.args.vararg is not None:
                    statically_bound.add(node.args.vararg.arg)
                if node.args.kwarg is not None:
                    statically_bound.add(node.args.kwarg.arg)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    statically_bound.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    statically_bound.add(alias.asname or alias.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        statically_bound.add(target.id)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id in statically_bound | safe_builtins, (
                    f"unexpected direct callable: {node.func.id}"
                )

    def test_arbitrary_callables_in_formula_fail_closed(self, materializer: FeatureMaterializer, sample_table: pa.Table) -> None:
        proposal = _proposal("__builtins__.open('x')")
        with pytest.raises(DataContractError):
            materializer.materialize(proposal, sample_table)