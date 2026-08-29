"""Unit tests for Multiple Testing Corrections, Parameter Fragility, and PBO."""

from decimal import Decimal
import hashlib
import math
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.validation.multiple_testing import MultipleTestingEngine
from acash.validation.overfitting import OverfittingEngine
from acash.validation.schema import ParameterPerturbationGrid, ParameterPerturbationPoint


def test_holm_bonferroni_step_down_adjustment() -> None:
    """Verify Holm-Bonferroni step-down adjustment on a known p-value vector."""
    raw_p = [0.01, 0.04, 0.03, 0.005]
    adj_p = MultipleTestingEngine.holm_bonferroni_correction(raw_p)

    assert math.isclose(float(adj_p[0]), 0.03, abs_tol=1e-5)
    assert math.isclose(float(adj_p[1]), 0.06, abs_tol=1e-5)
    assert math.isclose(float(adj_p[2]), 0.06, abs_tol=1e-5)
    assert math.isclose(float(adj_p[3]), 0.02, abs_tol=1e-5)


def test_authoritative_k_enforcement_in_multiple_testing() -> None:
    """Verify that evaluate_multiple_testing rejects p_values vectors whose length != effective_trials_k."""
    with pytest.raises(DataContractError, match="MultipleTestingEngine K mismatch"):
        MultipleTestingEngine.evaluate_multiple_testing(
            p_values=[Decimal("0.01"), Decimal("0.05")],
            estimated_sharpe=1.5,
            sample_size_t=500,
            effective_trials_k=10,  # Mismatch! 2 != 10
        )


def test_haircut_sharpe_ratio_derivation() -> None:
    """Verify non-linear Haircut Sharpe penalization (Harvey, Liu, & Zhu 2016)."""
    # 1. K = 1 produces zero haircut (Haircut SR == raw SR)
    haircut_k1 = MultipleTestingEngine.calculate_haircut_sharpe(
        estimated_sharpe=0.20,
        effective_trials_k=1,
        sample_size_t=100,
    )
    assert math.isclose(float(haircut_k1), 0.20, abs_tol=1e-5)

    # 2. Marginal Sharpe (SR=0.2, T=100, t_raw=2.0, p_raw=0.0455) with K=10
    # p_adj = 0.455 -> t_adj = 0.74706 -> Haircut SR = 0.0747 (~62.6% haircut)
    haircut_marginal = MultipleTestingEngine.calculate_haircut_sharpe(
        estimated_sharpe=0.20,
        effective_trials_k=10,
        sample_size_t=100,
    )
    assert math.isclose(float(haircut_marginal), 0.074706, rel_tol=1e-2)

    # 3. High Sharpe (SR=0.60, T=100, t_raw=6.0) with K=100
    # p_adj = 1.97e-7 -> t_adj = 5.20 -> Haircut SR = 0.520 (~13.3% haircut)
    haircut_high = MultipleTestingEngine.calculate_haircut_sharpe(
        estimated_sharpe=0.60,
        effective_trials_k=100,
        sample_size_t=100,
    )
    assert math.isclose(float(haircut_high), 0.520, rel_tol=1e-2)

    # 4. Strict monotonic decay with increasing K
    k_vals = [1, 2, 5, 10, 20]
    haircuts = [
        float(MultipleTestingEngine.calculate_haircut_sharpe(0.30, k, 100))
        for k in k_vals
    ]
    for i in range(len(haircuts) - 1):
        assert haircuts[i] >= haircuts[i + 1]



def test_parameter_curvature_evaluation_with_lineage() -> None:
    """Verify parameter curvature calculation across +/- 25% perturbation points."""
    theta = Decimal("10.0")
    h1 = "f" * 64
    h2 = "e" * 64
    h3 = "d" * 64
    points = [
        ParameterPerturbationPoint(
            parameter_value=Decimal("7.5"),
            run_id="run_p75",
            manifest_id="MANIFEST_P75",
            input_artifact_hash=h1,
            output_artifact_hash=h1,
            actual_sharpe=Decimal("1.4"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("10.0"),
            run_id="run_p100",
            manifest_id="MANIFEST_P100",
            input_artifact_hash=h2,
            output_artifact_hash=h2,
            actual_sharpe=Decimal("1.5"),
        ),
        ParameterPerturbationPoint(
            parameter_value=Decimal("12.5"),
            run_id="run_p125",
            manifest_id="MANIFEST_P125",
            input_artifact_hash=h3,
            output_artifact_hash=h3,
            actual_sharpe=Decimal("1.35"),
        ),

    ]

    grid = ParameterPerturbationGrid(
        base_parameter_name="lookback",
        base_parameter_value=theta,
        points=points,
    )

    curvature, is_stable = OverfittingEngine.evaluate_parameter_curvature(grid)
    assert curvature >= 0.0
    assert is_stable is True  # Max degradation (1.5 - 1.35) / 1.5 = 10% <= 30%


def test_analytical_friction_stress_monotonicity() -> None:
    """Verify component-wise analytical friction stress monotonicity."""
    is_monotonic = OverfittingEngine.verify_analytical_friction_decay_monotonicity(raw_predictive_edge_bps=15.0)
    assert is_monotonic is True


def test_pbo_calculation_with_midrank_ties() -> None:
    """Verify that identical/tied OOS scores yield symmetric mid-rank omega = 0.50 (logit = 0.0)."""
    C = 10
    M = 5
    # All candidate models have exact identical scores (complete tie)
    is_mat = np.ones((C, M))
    oos_mat = np.ones((C, M))

    pbo, logits_mean, _ = OverfittingEngine.calculate_pbo(is_mat, oos_mat)
    # Mid-rank for 5 tied models is 3.0 -> omega = 3.0 / (5 + 1) = 0.50 -> logit = ln(0.5/0.5) = 0.0
    assert math.isclose(logits_mean, 0.0, abs_tol=1e-6)
    assert pbo == 0.0  # Logit >= 0.0, not strictly underperforming


def test_pbo_discrimination_noise_vs_true_alpha() -> None:
    """Verify that PBO distinguishes overfit random noise from true persistent alpha."""
    np.random.seed(42)
    C = 100
    M = 20

    # Case A: Random noise -> PBO ~ 0.50
    is_noise = np.random.normal(0.0, 1.0, (C, M))
    oos_noise = np.random.normal(0.0, 1.0, (C, M))
    pbo_noise, _, _ = OverfittingEngine.calculate_pbo(is_noise, oos_noise)
    assert 0.35 <= pbo_noise <= 0.65

    # Case B: Strong persistent alpha on index 0 -> PBO < 0.10
    is_signal = np.random.normal(0.0, 1.0, (C, M))
    oos_signal = np.random.normal(0.0, 1.0, (C, M))
    is_signal[:, 0] += 3.0
    oos_signal[:, 0] += 3.0
    pbo_signal, _, _ = OverfittingEngine.calculate_pbo(is_signal, oos_signal)
    assert pbo_signal < 0.10


def test_multiple_testing_rejects_invalid_p_values() -> None:
    """Verify that multiple testing functions reject invalid p-values (< 0, > 1, NaN, Inf)."""
    # 1. Negative p-value
    with pytest.raises(DataContractError, match="must be finite and within"):
        MultipleTestingEngine.holm_bonferroni_correction([0.05, -0.01])

    with pytest.raises(DataContractError, match="must be finite and within"):
        MultipleTestingEngine.benjamini_hochberg_fdr([0.05, -0.01])

    # 2. p-value > 1.0
    with pytest.raises(DataContractError, match="must be finite and within"):
        MultipleTestingEngine.holm_bonferroni_correction([0.05, 1.05])

    with pytest.raises(DataContractError, match="must be finite and within"):
        MultipleTestingEngine.benjamini_hochberg_fdr([0.05, 1.05])

    # 3. Non-finite (NaN / Inf)
    with pytest.raises(DataContractError, match="must be finite and within"):
        MultipleTestingEngine.holm_bonferroni_correction([0.05, float("nan")])

    with pytest.raises(DataContractError, match="must be finite and within"):
        MultipleTestingEngine.calculate_haircut_sharpe(0.5, 10, 100, raw_p_value=float("inf"))

    with pytest.raises(DataContractError, match="must be finite and within"):
        MultipleTestingEngine.calculate_haircut_sharpe(0.5, 10, 100, raw_p_value=-0.05)

