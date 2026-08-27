"""Hand-Calculated Golden Mathematical Reference Tests for Alpha Research Engine (Phase 4).

Eliminates shared implementation bias by verifying calculations against independently derived manual reference vectors.
"""

from decimal import Decimal
import math
import pytest

from acash.research.evaluation import (
    calculate_3tier_friction_waterfall,
    calculate_pearson_ic,
    calculate_spearman_rank_ic,
    compute_ols_beta_and_hac,
)
from acash.research.schema import CostModelConfig


def test_hand_calculated_ols_slope_and_pearson_ic() -> None:
    """Verify OLS slope beta and Pearson IC against exact manual derivations.

    Vector:
    X = [1.0, 2.0, 3.0, 4.0, 5.0]
    Y = [2.0, 4.0, 5.0, 4.0, 5.0]

    Manual calculations:
    mean(X) = 3.0, mean(Y) = 4.0
    x_dm = [-2, -1, 0, 1, 2], sum(x_dm^2) = 10.0
    y_dm = [-2, 0, 1, 0, 1], sum(y_dm^2) = 6.0
    sum(x_dm * y_dm) = (-2)*(-2) + 0 + 0 + 0 + (2)*(1) = 4 + 2 = 6.0

    OLS Beta = 6.0 / 10.0 = 0.60
    Pearson IC = 6.0 / sqrt(10.0 * 6.0) = 6.0 / sqrt(60.0) = 0.7745966692414834
    """
    x = [Decimal("1.0"), Decimal("2.0"), Decimal("3.0"), Decimal("4.0"), Decimal("5.0")]
    y = [Decimal("2.0"), Decimal("4.0"), Decimal("5.0"), Decimal("4.0"), Decimal("5.0")]

    beta, se, t_stat, p_val = compute_ols_beta_and_hac(x, y, lag_bandwidth=1)
    assert beta == Decimal("0.60")

    p_ic = calculate_pearson_ic(x, y)
    assert p_ic is not None
    assert math.isclose(float(p_ic), 6.0 / math.sqrt(60.0), rel_tol=1e-6)


def test_hand_calculated_spearman_rank_ic_with_fractional_ties() -> None:
    """Verify Spearman Rank IC with fractional tie handling against manual derivation.

    X = [1.0, 2.0, 3.0, 4.0, 5.0] -> ranks: [0, 1, 2, 3, 4]
    Y = [2.0, 4.0, 5.0, 4.0, 5.0] -> unique: 2.0 (rank 0), 4.0 (ranks 1, 2 -> avg 1.5), 5.0 (ranks 3, 4 -> avg 3.5)
    Y ranks: [0, 1.5, 3.5, 1.5, 3.5]
    """
    x = [Decimal("1.0"), Decimal("2.0"), Decimal("3.0"), Decimal("4.0"), Decimal("5.0")]
    y = [Decimal("2.0"), Decimal("4.0"), Decimal("5.0"), Decimal("4.0"), Decimal("5.0")]

    r_ic = calculate_spearman_rank_ic(x, y)
    assert r_ic is not None

    # Expected correlation between [1, 2, 3, 4, 5] and [1.0, 2.5, 4.5, 2.5, 4.5]
    # Cov = 7.0, Var(X) = 10, Var(Y) = 9.0 -> corr = 7.0 / sqrt(90) = 0.7378647873726218
    expected_corr = 7.0 / math.sqrt(90.0)
    assert math.isclose(float(r_ic), expected_corr, rel_tol=1e-6)



def test_hand_calculated_3tier_friction_waterfall() -> None:
    """Verify 3-tier friction deductions and basis point conversions.

    Forward Returns: [0.0010, 0.0020] (mean = 0.0015 = 15 bps)
    Signals: [1.0, 1.0]
    Tier 1 Raw Edge = 15.0 bps
    Cost Config:
      quoted_spread_bps = 2.0 bps
      roundtrip_broker_fee_bps = 1.0 bps
      fixed_slippage_bps = 0.5 bps
    Tier 2 Net Edge = 15.0 - (2.0 + 1.0) = 12.0 bps
    Tier 3 Economic Edge = 12.0 - 0.5 = 11.5 bps
    """
    fwd_ret = [Decimal("0.0010"), Decimal("0.0020")]
    signals = [Decimal("1.0"), Decimal("1.0")]
    cfg = CostModelConfig(
        quoted_spread_bps=Decimal("2.0"),
        roundtrip_broker_fee_bps=Decimal("1.0"),
        fixed_slippage_bps=Decimal("0.5"),
    )

    t1, t2, t3 = calculate_3tier_friction_waterfall(fwd_ret, signals, cfg)
    assert t1 == Decimal("15.0")
    assert t2 == Decimal("12.0")
    assert t3 == Decimal("11.5")
