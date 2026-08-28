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
    # Sorted: p_(1)=0.005, p_(2)=0.01, p_(3)=0.03, p_(4)=0.04 (K=4)
    # Step 1: 4 * 0.005 = 0.02
    # Step 2: 3 * 0.01 = 0.03 (max(0.02, 0.03) = 0.03)
    # Step 3: 2 * 0.03 = 0.06 (max(0.03, 0.06) = 0.06)
    # Step 4: 1 * 0.04 = 0.04 (max(0.06, 0.04) = 0.06)
    # Restored to original indices [0.01, 0.04, 0.03, 0.005]:
    # idx 0 (0.01) -> 0.03
    # idx 1 (0.04) -> 0.06
    # idx 2 (0.03) -> 0.06
    # idx 3 (0.005) -> 0.02
    adj_p = MultipleTestingEngine.holm_bonferroni_correction(raw_p)

    assert math.isclose(float(adj_p[0]), 0.03, abs_tol=1e-5)
    assert math.isclose(float(adj_p[1]), 0.06, abs_tol=1e-5)
    assert math.isclose(float(adj_p[2]), 0.06, abs_tol=1e-5)
    assert math.isclose(float(adj_p[3]), 0.02, abs_tol=1e-5)


def test_haircut_sharpe_ratio_derivation() -> None:
    """Verify Haircut Sharpe penalization formula (Harvey, Liu, & Zhu 2016)."""
    # Base Sharpe = 2.0, K = 100 trials, T = 1000 bars
    # Penalty = sqrt(2 * ln(100)) / (2.0 * sqrt(1000)) = sqrt(9.21034) / (2.0 * 31.62277) = 3.03485 / 63.2455 = 0.047985
    # Haircut SR = 2.0 * (1 - 0.047985) = 1.90403
    haircut = MultipleTestingEngine.calculate_haircut_sharpe(
        estimated_sharpe=2.0,
        effective_trials_k=100,
        sample_size_t=1000,
    )
    assert math.isclose(float(haircut), 1.90403, rel_tol=1e-3)


def test_pbo_calculation_on_overfit_vs_robust_strategies() -> None:
    """Verify that PBO distinguishes completely overfit random noise from true persistent alpha."""
    np.random.seed(42)
    C = 100  # 100 CPCV combinations
    M = 20   # 20 candidate strategies

    # Case A: Pure random noise (IS and OOS uncorrelated standard normal) -> PBO ~ 0.50
    is_noise = np.random.normal(0.0, 1.0, (C, M))
    oos_noise = np.random.normal(0.0, 1.0, (C, M))

    pbo_noise, _, _ = OverfittingEngine.calculate_pbo(is_noise, oos_noise)
    assert 0.35 <= pbo_noise <= 0.65

    # Case B: True signal present on strategy index 0 (IS and OOS consistently superior) -> PBO -> 0.0
    is_signal = np.random.normal(0.0, 1.0, (C, M))
    oos_signal = np.random.normal(0.0, 1.0, (C, M))
    is_signal[:, 0] += 3.0
    oos_signal[:, 0] += 3.0

    pbo_signal, _, _ = OverfittingEngine.calculate_pbo(is_signal, oos_signal)
    assert pbo_signal < 0.10
