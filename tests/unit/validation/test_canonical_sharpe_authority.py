"""Adversarial tests for the single canonical annualized Sharpe authority (Phase 14, D4 / D7).

Attack the ratified D7 contract:
- behavioral equivalence with the Phase 6 gate's inline Sharpe mathematics on valid inputs;
- annualization via sqrt(periods_per_year) from ValidationConfig (sole authority, D4);
- fail-closed on zero variance, non-finite inputs, insufficient observations, and
  unsupported/undefined periods_per_year.
"""

import math
from decimal import Decimal
from typing import Sequence, Union

import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.deflated_sharpe import (
    MIN_ANNUALIZED_SHARPE_OBSERVATIONS,
    ZERO_VARIANCE_STD_EPSILON,
    calculate_annualized_sharpe,
)

_PPY = Decimal("252.0")

# (series, annualization) drawn to mirror Phase 6 gate math (mean, std ddof=1, sqrt(ppy)).
_GATE_STYLE_SERIES: list[tuple[list[Union[Decimal, float]], Decimal]] = [
    ([Decimal("0.01"), Decimal("0.02"), Decimal("-0.01"), Decimal("0.03")], _PPY),
    ([Decimal("0.001"), Decimal("-0.002"), Decimal("0.004"), Decimal("0.0005")], Decimal("252.0")),
    ([Decimal("-0.01"), Decimal("0.02"), Decimal("-0.015"), Decimal("0.01"), Decimal("0.005")], _PPY),
    ([0.0001, -0.0002, 0.0003, -0.0001, 0.0002, 0.00015], Decimal("12.0")),
    ([Decimal("0.0002") * 4, Decimal("0.0006"), Decimal("-0.0003")], Decimal("52.0")),
]


def _gate_reference(returns: Sequence[Union[Decimal, float]], ppy: Decimal) -> float:
    arr = np.asarray([float(r) for r in returns], dtype=np.float64)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    assert std > ZERO_VARIANCE_STD_EPSILON
    return (mean / std) * math.sqrt(float(ppy))


class TestGateEquivalence:
    @pytest.mark.parametrize("series,ppy", _GATE_STYLE_SERIES)
    def test_behaviorally_equivalent_to_gate_math(
        self, series: list[Union[Decimal, float]], ppy: Decimal
    ) -> None:
        canonical = calculate_annualized_sharpe(series, ppy)
        ref = _gate_reference(series, ppy)
        assert abs(float(canonical) - ref) < 1e-6

    def test_golden_series_black_box(self) -> None:
        # Structural checks independent of the reference implementation.
        sr = calculate_annualized_sharpe([Decimal("0.01"), Decimal("0.02")], _PPY)
        assert sr > Decimal("0")
        assert abs(float(sr)) < 100.0

    def test_annualization_scaling_sqrt_ppy(self) -> None:
        series = [Decimal("0.01"), Decimal("-0.005"), Decimal("0.02"), Decimal("0.0")]
        sr_252 = float(calculate_annualized_sharpe(series, Decimal("252.0")))
        sr_1 = float(calculate_annualized_sharpe(series, Decimal("1.0")))
        assert abs(sr_252 - sr_1 * math.sqrt(252.0)) < 1e-6

    def test_returns_decimal_quantized_to_18_places(self) -> None:
        sr = calculate_annualized_sharpe(
            [Decimal("0.01"), Decimal("0.02"), Decimal("-0.01"), Decimal("0.03")], _PPY
        )
        assert isinstance(sr, Decimal)
        assert sr == sr.quantize(Decimal("0.000000000000000001"))

    def test_accepts_float_series_and_int_ppy(self) -> None:
        sr = calculate_annualized_sharpe([0.01, -0.005, 0.02], 252)
        assert isinstance(sr, Decimal)


class TestFailClosed:
    def test_insufficient_observations(self) -> None:
        with pytest.raises(DataContractError, match="insufficient observations"):
            calculate_annualized_sharpe([], _PPY)
        with pytest.raises(DataContractError, match="insufficient observations"):
            calculate_annualized_sharpe([Decimal("0.01")], _PPY)
        assert MIN_ANNUALIZED_SHARPE_OBSERVATIONS == 2

    def test_zero_variance_constant_series(self) -> None:
        with pytest.raises(DataContractError, match="zero-variance"):
            calculate_annualized_sharpe([Decimal("0.0"), Decimal("0.0"), Decimal("0.0")], _PPY)
        with pytest.raises(DataContractError, match="zero-variance"):
            calculate_annualized_sharpe([Decimal("0.01"), Decimal("0.01"), Decimal("0.01")], Decimal("252"))
        with pytest.raises(DataContractError, match="zero-variance"):
            calculate_annualized_sharpe([0.0, 0.0], 252)

    def test_non_finite_return_decimal(self) -> None:
        with pytest.raises(DataContractError, match="non-finite return observation"):
            calculate_annualized_sharpe([Decimal("0.01"), Decimal("NaN"), Decimal("0.02")], _PPY)
        with pytest.raises(DataContractError, match="non-finite return observation"):
            calculate_annualized_sharpe([Decimal("Infinity"), Decimal("0.01")], _PPY)

    def test_non_finite_return_float(self) -> None:
        with pytest.raises(DataContractError, match="non-finite return observation"):
            calculate_annualized_sharpe([0.01, float("inf")], _PPY)
        with pytest.raises(DataContractError, match="non-finite return observation"):
            calculate_annualized_sharpe([float("nan"), 0.01], _PPY)

    def test_unsupported_periods_per_year_zero(self) -> None:
        with pytest.raises(DataContractError, match="invalid periods_per_year"):
            calculate_annualized_sharpe([Decimal("0.01"), Decimal("0.02")], Decimal("0.0"))
        with pytest.raises(DataContractError, match="invalid periods_per_year"):
            calculate_annualized_sharpe([0.01, 0.02], 0)

    def test_unsupported_periods_per_year_negative(self) -> None:
        with pytest.raises(DataContractError, match="invalid periods_per_year"):
            calculate_annualized_sharpe([Decimal("0.01"), Decimal("0.02")], Decimal("-252.0"))

    def test_unsupported_periods_per_year_non_finite(self) -> None:
        with pytest.raises(DataContractError, match="invalid periods_per_year"):
            calculate_annualized_sharpe([Decimal("0.01"), Decimal("0.02")], float("nan"))
        with pytest.raises(DataContractError, match="invalid periods_per_year"):
            calculate_annualized_sharpe([Decimal("0.01"), Decimal("0.02")], Decimal("Infinity"))