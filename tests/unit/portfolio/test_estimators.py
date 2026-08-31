"""Unit tests for Phase 8 Expected Return and Covariance Estimators."""

from datetime import datetime, timezone
from decimal import Decimal
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.estimators import (
    HistoricalSampleMeanEstimator,
    LedoitWolfShrinkageCovarianceEstimator,
    SampleCovarianceEstimator,
)
from acash.portfolio.schema import AssetReturnPanel


def _sample_panel() -> AssetReturnPanel:
    t1 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    t4 = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)

    returns = (
        (Decimal("0.010"), Decimal("0.020")),
        (Decimal("-0.005"), Decimal("0.015")),
        (Decimal("0.020"), Decimal("-0.010")),
        (Decimal("0.005"), Decimal("0.005")),
    )

    return AssetReturnPanel(
        universe_id="UNIV_TEST",
        timestamps=(t1, t2, t3, t4),
        symbols=("AAPL", "SPY"),
        returns_matrix=returns,
        frequency="1D",
    )


def test_historical_sample_mean_estimator_annualization() -> None:
    """Verify ExpectedReturnEstimator calculates sample mean and scales by annualization factor."""
    panel = _sample_panel()
    estimator = HistoricalSampleMeanEstimator(annualization_factor=Decimal("252"))

    mu = estimator.estimate_expected_returns(panel)
    assert len(mu) == 2
    assert "AAPL" in mu and "SPY" in mu

    # Mean of (0.01, -0.005, 0.02, 0.005) = 0.03 / 4 = 0.0075
    # Annualized = 0.0075 * 252 = 1.89
    assert abs(mu["AAPL"] - Decimal("1.89")) < Decimal("1e-6")


def test_sample_covariance_estimator_symmetry_and_psd() -> None:
    """Verify SampleCovarianceEstimator produces a symmetric positive semi-definite matrix."""
    panel = _sample_panel()
    estimator = SampleCovarianceEstimator(annualization_factor=Decimal("252"))

    cov_matrix = estimator.estimate_covariance(panel)
    assert cov_matrix.shape == (2, 2)

    # Symmetry check
    assert abs(cov_matrix[0, 1] - cov_matrix[1, 0]) < 1e-12

    # Positive semi-definite (eigenvalues >= 0)
    eigenvalues = np.linalg.eigvalsh(cov_matrix)
    assert all(ev >= -1e-10 for ev in eigenvalues)


def test_ledoit_wolf_covariance_estimator() -> None:
    """Verify Ledoit-Wolf shrinkage produces a well-conditioned symmetric positive definite matrix."""
    panel = _sample_panel()
    estimator = LedoitWolfShrinkageCovarianceEstimator(annualization_factor=Decimal("252"))

    cov_matrix = estimator.estimate_covariance(panel)
    assert cov_matrix.shape == (2, 2)
    assert abs(cov_matrix[0, 1] - cov_matrix[1, 0]) < 1e-12
    eigenvalues = np.linalg.eigvalsh(cov_matrix)
    assert all(ev > 0 for ev in eigenvalues)


def test_zero_variance_panel_fail_closed() -> None:
    """Verify covariance and volatility estimators fail closed on zero variance degenerate series."""
    t1 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Constant zero return -> zero variance
    degenerate_returns = (
        (Decimal("0.0"), Decimal("0.01")),
        (Decimal("0.0"), Decimal("0.02")),
    )
    panel = AssetReturnPanel(
        universe_id="UNIV_DEGEN",
        timestamps=(t1, t2),
        symbols=("CASH_LIKE", "SPY"),
        returns_matrix=degenerate_returns,
        frequency="1D",
    )

    estimator = SampleCovarianceEstimator()
    with pytest.raises(DataContractError, match="Zero variance detected for asset"):
        estimator.estimate_covariance(panel)
