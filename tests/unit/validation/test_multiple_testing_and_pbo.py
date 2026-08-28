"""Unit tests for Multiple Testing Corrections and Probability of Backtest Overfitting (PBO)."""

from decimal import Decimal
import math
import numpy as np
import pytest

from acash.validation.multiple_testing import MultipleTestingEngine
from acash.validation.overfitting import OverfittingEngine


def test_holm_bonferroni_step_down_adjustment() -> None:
    """Verify Holm-Bonferroni step-down adjustment on a known p-value vector."""
    raw_p = [0.01, 0.04, 0.03, 0.005]
    adj_p = MultipleTestingEngine.holm_bonferroni_correction(raw_p)

    assert math.isclose(float(adj_p[0]), 0.03, abs_tol=1e-5)
    assert math.isclose(float(adj_p[1]), 0.06, abs_tol=1e-5)
    assert math.isclose(float(adj_p[2]), 0.06, abs_tol=1e-5)
    assert math.isclose(float(adj_p[3]), 0.02, abs_tol=1e-5)


def test_haircut_sharpe_ratio_derivation() -> None:
    """Verify Haircut Sharpe penalization formula (Harvey, Liu, & Zhu 2016)."""
    haircut = MultipleTestingEngine.calculate_haircut_sharpe(
        estimated_sharpe=2.0,
        effective_trials_k=100,
        sample_size_t=1000,
    )
    assert math.isclose(float(haircut), 1.90403, rel_tol=1e-3)


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
