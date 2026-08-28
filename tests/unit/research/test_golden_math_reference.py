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

    # 1. Exact OLS Beta
    assert beta == Decimal("0.60")

    # 2. Exact Hand-Calculated Newey-West HAC Covariance (L=1, Bartlett Kernel):
    # u = [1.6, -0.6, 0.0, -0.6, -0.4]
    # Gamma_0 = 3.44 / 5 = 0.688
    # Gamma_1 = -0.72 / 5 = -0.144
    # Omega_hat = 0.688 + 2 * (0.5) * (-0.144) = 0.544
    # Var(Beta) = (5 * 0.544) / 100 = 0.0272
    # SE(Beta) = sqrt(0.0272) = 0.16492422502470642
    # t_stat = 0.60 / sqrt(0.0272) = 3.6380343755449944
    # p_val = 2 * (1 - Phi(3.6380343755449944)) = 0.0002747372134262
    expected_se = math.sqrt(0.0272)
    expected_t = 0.60 / expected_se
    expected_p = 2.0 * (1.0 - (1.0 + math.erf(expected_t / math.sqrt(2.0))) / 2.0)

    assert math.isclose(float(se), expected_se, rel_tol=1e-5)
    assert math.isclose(float(t_stat), expected_t, rel_tol=1e-5)
    assert math.isclose(float(p_val), expected_p, rel_tol=1e-4)

    p_ic = calculate_pearson_ic(x, y)
    assert p_ic is not None
    assert math.isclose(float(p_ic), 6.0 / math.sqrt(60.0), rel_tol=1e-6)


def test_hand_calculated_spearman_rank_ic_with_fractional_ties() -> None:
    """Verify Spearman Rank IC with fractional tie handling against manual derivation."""
    x = [Decimal("1.0"), Decimal("2.0"), Decimal("3.0"), Decimal("4.0"), Decimal("5.0")]
    y = [Decimal("2.0"), Decimal("4.0"), Decimal("5.0"), Decimal("4.0"), Decimal("5.0")]

    r_ic = calculate_spearman_rank_ic(x, y)
    assert r_ic is not None

    # Expected correlation between [1, 2, 3, 4, 5] and [1.0, 2.5, 4.5, 2.5, 4.5]
    # Cov = 7.0, Var(X) = 10, Var(Y) = 9.0 -> corr = 7.0 / sqrt(90) = 0.7378647873726218
    expected_corr = 7.0 / math.sqrt(90.0)
    assert math.isclose(float(r_ic), expected_corr, rel_tol=1e-6)


def test_hand_calculated_3tier_friction_waterfall() -> None:
    """Verify 3-tier friction deductions and basis point conversions."""
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


def test_hand_calculated_andrews_ar1_and_newey_west_bandwidths() -> None:
    """Verify Andrews (1991, Econometrica 59(3)) AR(1) plug-in and Newey-West (1994) lag selection against manual derivations."""
    from acash.research.evaluation import determine_hac_bandwidth
    from acash.research.schema import HacBandwidthMethod
    import numpy as np

    # 1. Newey-West rule-of-thumb: floor(4 * (T / 100)^(2/9))
    # For T = 1000: floor(4 * 10^(2/9)) = floor(4 * 1.6681005372) = floor(6.6724) = 6
    nw_bw = determine_hac_bandwidth(HacBandwidthMethod.NEWEY_WEST_PLUGIN, sample_size=1000, horizon=5)
    assert nw_bw == 6

    # 2. Andrews (1991) AR(1) Bartlett kernel plug-in:
    # S_T = floor(1.1447 * (alpha(1) * T)^(1/3))
    # where alpha(1) = 4 * rho^2 / (1 - rho^2)^2
    # Let rho = 0.5 -> rho^2 = 0.25 -> alpha(1) = 4 * 0.25 / (1 - 0.25)^2 = 1.0 / 0.5625 = 16/9 = 1.7777777778
    # For T = 1000: (alpha(1) * T)^(1/3) = (1777.7777778)^(1/3) = 12.114137286
    # S_T = floor(1.1447 * 12.114137286) = floor(13.86705295) = 13

    # Generate synthetic score process with known sample autocorrelation rho ~ 0.50
    np.random.seed(42)
    e = np.random.normal(0, 1, 1000)
    score_proc = np.zeros(1000)
    for t in range(1, 1000):
        score_proc[t] = 0.50 * score_proc[t - 1] + e[t]

    sample_rho = float(np.corrcoef(score_proc[:-1], score_proc[1:])[0, 1])
    expected_alpha = (4.0 * (sample_rho ** 2)) / ((1.0 - (sample_rho ** 2)) ** 2)
    expected_andrews_bw = int(math.floor(1.1447 * ((expected_alpha * 1000.0) ** (1.0 / 3.0))))

    andrews_bw = determine_hac_bandwidth(
        HacBandwidthMethod.ANDREWS_AR1_PLUGIN,
        sample_size=1000,
        horizon=5,
        score_process=score_proc,
    )
    assert andrews_bw == expected_andrews_bw


def test_empty_orderbook_and_trades_tables_validate_canonical_schema() -> None:
    """Verify that empty tables with malformed schemas fail-fast rather than silently returning success."""
    from acash.data.orderbook.pipeline import OrderBookIngestionPipeline
    from acash.data.trades.pipeline import TradesIngestionPipeline
    from acash.data.schema import IntegrityViolationError
    import pyarrow as pa

    ob_pipeline = OrderBookIngestionPipeline()
    trades_pipeline = TradesIngestionPipeline()

    # Empty table with completely invalid schema (missing mandatory fields)
    bad_empty_table = pa.Table.from_pydict({"invalid_col_a": [], "invalid_col_b": []})

    with pytest.raises(IntegrityViolationError, match="Empty Order Book Snapshot table has invalid canonical schema"):
        ob_pipeline.ingest_snapshots(raw_table=bad_empty_table, source_id="binance", source_uri="file://test")

    with pytest.raises(IntegrityViolationError, match="Empty Order Book Delta table has invalid canonical schema"):
        ob_pipeline.ingest_deltas(raw_table=bad_empty_table, source_id="binance", source_uri="file://test")

    with pytest.raises(IntegrityViolationError, match="Empty Trades table has invalid canonical schema"):
        trades_pipeline.ingest(raw_table=bad_empty_table, source_id="binance", source_uri="file://test")

