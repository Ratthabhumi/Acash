"""Unit tests for Phase 11 ForwardMetricsCalculator and econometric estimators.

Verifies:
1. Deterministic mathematical accuracy against golden analytical reference benchmarks.
2. Separation of rolling window max drawdown from inception high-water mark drawdown.
3. Strict fail-closed zero-variance guards (no magic floor, raises DataContractError).
4. Boundary condition guards (empty series, N < 2, negative window, telemetry corruption).
5. Option B invariant: information_coefficient and ic_decay_slope are strictly None.
6. Pure Decimal space preservation (zero float casting).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.monitoring.metrics import (
    DEFAULT_ANNUALIZATION_FACTOR,
    ForwardMetricsCalculator,
    calculate_forward_window_metrics,
)
from acash.monitoring.schema import ForwardObservation

VALID_DOSSIER_DIGEST = "d" * 64


def _create_dummy_observation(
    seq: int,
    realized_return: Decimal,
    expected_return: Decimal | None = None,
    is_telemetry_valid: bool = True,
) -> ForwardObservation:
    """Helper to create a valid ForwardObservation for testing."""
    base_t = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    obs_t = base_t + timedelta(days=seq)
    pnl = realized_return * Decimal("100000.0")

    return ForwardObservation(
        observation_id=f"FOBS_{seq:03d}",
        strategy_id="STRAT_TEST",
        dossier_digest=VALID_DOSSIER_DIGEST,
        as_of_utc=obs_t,
        wall_clock_utc=obs_t + timedelta(milliseconds=10),
        realized_return=realized_return,
        expected_return=expected_return,
        benchmark_return=Decimal("0.0"),
        gross_pnl_usd=pnl,
        net_pnl_usd=pnl,
        turnover_ratio=Decimal("0.10"),
        observation_sequence=seq,
        is_telemetry_valid=is_telemetry_valid,
    )


# ============================================================================
# 1. GOLDEN ANALYTICAL BENCHMARK ACCURACY
# ============================================================================

def test_window_metrics_golden_analytical_reference() -> None:
    """Verify metrics against exact hand-calculated analytical reference values."""
    # 5 observations:
    # returns: [0.01, 0.02, -0.01, 0.00, 0.03]
    # sum = 0.05, mean = 0.01
    # annualized return (A=252) = 0.01 * 252 = 2.52
    # deviations: [0.00, 0.01, -0.02, -0.01, 0.02]
    # sum of squares = 0.0000 + 0.0001 + 0.0004 + 0.0001 + 0.0004 = 0.0010
    # sample variance (N-1 = 4) = 0.0010 / 4 = 0.00025
    # daily vol = sqrt(0.00025)
    # annualized vol = sqrt(0.00025 * 252) = sqrt(0.063)
    raw_returns = [
        Decimal("0.01"),
        Decimal("0.02"),
        Decimal("-0.01"),
        Decimal("0.00"),
        Decimal("0.03"),
    ]
    expected_returns = [
        Decimal("0.015"),
        Decimal("0.015"),
        Decimal("0.015"),
        Decimal("0.015"),
        Decimal("0.015"),
    ]

    obs_list = [
        _create_dummy_observation(i + 1, r, exp)
        for i, (r, exp) in enumerate(zip(raw_returns, expected_returns))
    ]

    metrics = calculate_forward_window_metrics(
        observations=obs_list,
        annualization_factor=Decimal("252"),
        risk_free_rate_annualized=Decimal("0.0"),
    )

    # 1. Realized Annualized Return
    assert metrics.mean_realized_return_annualized == Decimal("2.52")

    # 2. Realized Volatility
    expected_vol = Decimal("0.063").sqrt()
    assert metrics.realized_volatility_annualized == expected_vol

    # 3. Sharpe Ratio
    expected_sharpe = Decimal("2.52") / expected_vol
    assert metrics.realized_sharpe_ratio == expected_sharpe

    # 4. Max Drawdown
    # Equity path: 1.0 -> 1.01 -> 1.0302 -> 1.019898 (dd = 0.010302/1.0302 = 0.01) -> 1.019898 -> 1.05049494
    assert metrics.max_drawdown == Decimal("0.01")
    assert metrics.inception_max_drawdown == Decimal("0.01")

    # 5. Hit Rate: 3 out of 5 positive (0.01, 0.02, 0.03) -> 3/5 = 0.60
    assert metrics.hit_rate == Decimal("0.60")

    # 6. Option B Invariants
    assert metrics.information_coefficient is None
    assert metrics.ic_decay_slope is None

    # 7. Verification that all numeric metrics are Decimal instances
    assert isinstance(metrics.mean_realized_return_annualized, Decimal)
    assert isinstance(metrics.realized_volatility_annualized, Decimal)
    assert isinstance(metrics.realized_sharpe_ratio, Decimal)
    assert isinstance(metrics.max_drawdown, Decimal)
    assert isinstance(metrics.hit_rate, Decimal)
    assert isinstance(metrics.tracking_error_annualized, Decimal)
    assert isinstance(metrics.t_stat_decay, Decimal)
    assert isinstance(metrics.expected_vs_realized_divergence_bps, Decimal)


# ============================================================================
# 2. INCEPTION HIGH-WATER MARK VS ROLLING WINDOW DRAWDOWN
# ============================================================================

def test_inception_hwm_drawdown_vs_rolling_window() -> None:
    """Verify that inception HWM preserves historical drawdown even when rolling window is calm."""
    # 8 total observations:
    # First 3 suffer a deep drawdown:
    # 1: -0.10 (equity = 0.90, peak = 1.0, dd = 0.10)
    # 2: -0.10 (equity = 0.81, peak = 1.0, dd = 0.19)
    # 3: +0.05 (equity = 0.8505, peak = 1.0, dd = 0.1495)
    # Next 5 are the rolling window (window_size = 5), all mildly positive or flat:
    # 4: +0.01
    # 5: +0.02
    # 6: +0.01
    # 7: +0.02
    # 8: +0.01
    history_returns = [
        Decimal("-0.10"),
        Decimal("-0.10"),
        Decimal("0.05"),
        Decimal("0.01"),
        Decimal("0.02"),
        Decimal("0.01"),
        Decimal("0.02"),
        Decimal("0.01"),
    ]

    all_obs = [_create_dummy_observation(i + 1, r) for i, r in enumerate(history_returns)]

    # Calculate metrics with window_size = 5
    metrics = calculate_forward_window_metrics(
        observations=all_obs,
        window_size=5,
        inception_observations=all_obs,
    )

    assert metrics.observation_count == 5
    # The last 5 observations have zero drawdown because equity strictly monotonically increases
    assert metrics.max_drawdown == Decimal("0.0")

    # Inception drawdown must reflect the -19% drop from the inception peak (1.0 -> 0.81)
    assert metrics.inception_max_drawdown == Decimal("0.19")


# ============================================================================
# 3. FAIL-CLOSED ZERO VARIANCE GUARD (AGENTS.MD PRINCIPLE 3)
# ============================================================================

def test_fail_closed_zero_sample_variance_rejection() -> None:
    """Strictly reject constant return series (zero variance).

    Must raise DataContractError immediately rather than applying silent artificial floors.
    """
    constant_returns = [Decimal("0.01"), Decimal("0.01"), Decimal("0.01")]
    obs_list = [_create_dummy_observation(i + 1, r) for i, r in enumerate(constant_returns)]

    with pytest.raises(DataContractError, match="Zero sample variance detected"):
        calculate_forward_window_metrics(obs_list)


# ============================================================================
# 4. BOUNDARY CONDITIONS & ADVERSARIAL CHECKS
# ============================================================================

def test_empty_observations_rejection() -> None:
    """Reject empty observation sequence."""
    with pytest.raises(DataContractError, match="Cannot calculate metrics on empty observation sequence"):
        calculate_forward_window_metrics([])


def test_insufficient_observations_for_variance_rejection() -> None:
    """Reject single observation sequence (N < 2)."""
    single_obs = [_create_dummy_observation(1, Decimal("0.01"))]
    with pytest.raises(DataContractError, match="At least 2 valid observations required"):
        calculate_forward_window_metrics(single_obs)


def test_invalid_window_size_rejection() -> None:
    """Reject non-positive window_size."""
    obs_list = [_create_dummy_observation(1, Decimal("0.01")), _create_dummy_observation(2, Decimal("0.02"))]
    with pytest.raises(DataContractError, match="window_size must be strictly positive"):
        calculate_forward_window_metrics(obs_list, window_size=0)


def test_invalid_annualization_factor_rejection() -> None:
    """Reject non-positive annualization factor."""
    with pytest.raises(DataContractError, match="annualization_factor must be strictly positive"):
        ForwardMetricsCalculator(annualization_factor=Decimal("0.0"))


def test_telemetry_integrity_flag_fail_closed() -> None:
    """Fail closed when any observation in the window has is_telemetry_valid=False."""
    obs_valid = _create_dummy_observation(1, Decimal("0.01"), is_telemetry_valid=True)
    obs_corrupt = _create_dummy_observation(2, Decimal("0.02"), is_telemetry_valid=False)

    with pytest.raises(DataContractError, match="TELEMETRY_INVALID"):
        calculate_forward_window_metrics([obs_valid, obs_corrupt])


def test_inconsistent_expected_returns_fail_closed() -> None:
    """Fail closed when expected_return is present on some observations and None on others."""
    obs_1 = _create_dummy_observation(1, Decimal("0.01"), expected_return=Decimal("0.01"))
    obs_2 = _create_dummy_observation(2, Decimal("0.02"), expected_return=None)

    with pytest.raises(DataContractError, match="Inconsistent expected_return telemetry"):
        calculate_forward_window_metrics([obs_1, obs_2])


# ============================================================================
# 5. TRACKING ERROR & EXPECTED VS REALIZED DIVERGENCE
# ============================================================================

def test_tracking_error_and_divergence_calculation() -> None:
    """Verify tracking error and divergence in basis points."""
    # realized: [0.02, 0.01, 0.00] -> mean = 0.01
    # expected: [0.01, 0.01, 0.01] -> mean = 0.01
    # diff: [0.01, 0.00, -0.01] -> mean diff = 0.0
    # diff sq: [0.0001, 0.0, 0.0001] = 0.0002 -> var = 0.0002 / 2 = 0.0001
    # daily te = 0.01 -> annualized te = 0.01 * sqrt(252)
    # divergence = (mean_realized - mean_expected) * 10000 = (0.01 - 0.01) * 10000 = 0.0
    r_list = [Decimal("0.02"), Decimal("0.01"), Decimal("0.00")]
    e_list = [Decimal("0.01"), Decimal("0.01"), Decimal("0.01")]

    obs_list = [
        _create_dummy_observation(i + 1, r, e)
        for i, (r, e) in enumerate(zip(r_list, e_list))
    ]

    metrics = calculate_forward_window_metrics(obs_list)
    expected_te = Decimal("0.0001").sqrt() * Decimal("252").sqrt()
    assert metrics.tracking_error_annualized == expected_te
    assert metrics.expected_vs_realized_divergence_bps == Decimal("0.0")


def test_none_expected_returns_yields_none_divergence_and_tracking_error() -> None:
    """Verify that when expected_return is None on all observations, divergence and TE are None.

    Enforces: No Evidence != Negative Evidence.
    Missing ex-ante expectation must not be penalized as 0.0 or negative drift.
    """
    obs_list = [
        _create_dummy_observation(1, Decimal("0.01"), expected_return=None),
        _create_dummy_observation(2, Decimal("0.02"), expected_return=None),
    ]
    metrics = calculate_forward_window_metrics(obs_list)
    assert metrics.tracking_error_annualized is None
    assert metrics.expected_vs_realized_divergence_bps is None
