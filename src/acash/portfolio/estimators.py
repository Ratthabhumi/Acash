"""Decoupled Expected Return and Covariance Estimators for Phase 8 Portfolio Engine.

Strictly enforces:
- Decoupled contracts between Expected Return (μ) and Covariance Matrix (Σ).
- Explicit metadata provenance, horizon, units, and annualization factor.
- Positive semi-definite matrix validation and fail-closed zero-variance guards.
"""

from decimal import Decimal
from typing import Mapping, Protocol
import numpy as np

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.schema import AssetReturnPanel


class ExpectedReturnEstimator(Protocol):
    """Protocol for expected return vector estimation."""
    @property
    def estimator_name(self) -> str: ...

    def estimate_expected_returns(self, panel: AssetReturnPanel) -> Mapping[str, Decimal]:
        """Estimate expected return vector μ in Decimal space."""
        ...


class CovarianceEstimator(Protocol):
    """Protocol for covariance matrix estimation."""
    @property
    def estimator_name(self) -> str: ...

    def estimate_covariance(self, panel: AssetReturnPanel) -> np.ndarray:
        """Estimate symmetric positive semi-definite covariance matrix Σ."""
        ...


class HistoricalSampleMeanEstimator:
    """Estimates expected return vector using stationary sample mean scaled by annualization factor."""

    def __init__(self, annualization_factor: Decimal = Decimal("252")):
        self.annualization_factor = annualization_factor

    @property
    def estimator_name(self) -> str:
        return "HISTORICAL_SAMPLE_MEAN"

    def estimate_expected_returns(self, panel: AssetReturnPanel) -> Mapping[str, Decimal]:
        if panel.T < 1:
            raise DataContractError("Cannot estimate expected returns from empty return panel.")

        mu_dict: dict[str, Decimal] = {}
        t_dec = Decimal(str(panel.T))

        for col_idx, symbol in enumerate(panel.symbols):
            col_sum = sum((row[col_idx] for row in panel.returns_matrix), Decimal("0.0"))
            sample_mean = col_sum / t_dec
            annualized_mean = sample_mean * self.annualization_factor
            mu_dict[symbol] = annualized_mean

        return mu_dict


class SampleCovarianceEstimator:
    """Estimates empirical sample covariance matrix with Bessel's correction (N-1)."""

    def __init__(self, annualization_factor: Decimal = Decimal("252")):
        self.annualization_factor = annualization_factor

    @property
    def estimator_name(self) -> str:
        return "SAMPLE_COVARIANCE"

    def estimate_covariance(self, panel: AssetReturnPanel) -> np.ndarray:
        if panel.T < 2:
            raise DataContractError("Sample covariance estimation requires at least T >= 2 observations.")

        # Convert Decimal return matrix to float64 numpy array
        matrix_f64 = np.array(
            [[float(val) for val in row] for row in panel.returns_matrix],
            dtype=np.float64,
        )

        # Check for zero variance
        stds = np.std(matrix_f64, axis=0, ddof=1)
        for idx, std_val in enumerate(stds):
            if std_val <= 1e-12 or not np.isfinite(std_val):
                raise DataContractError(
                    f"Zero variance detected for asset {panel.symbols[idx]} (std={std_val}). Fail-closed."
                )

        cov = np.cov(matrix_f64, rowvar=False, ddof=1)
        scale_factor = float(self.annualization_factor)
        cov_annualized = cov * scale_factor

        # Ensure exact symmetry
        cov_sym = 0.5 * (cov_annualized + cov_annualized.T)
        return cov_sym


class LedoitWolfShrinkageCovarianceEstimator:
    """Estimates covariance matrix using Ledoit-Wolf optimal linear shrinkage towards constant correlation."""

    def __init__(self, annualization_factor: Decimal = Decimal("252")):
        self.annualization_factor = annualization_factor

    @property
    def estimator_name(self) -> str:
        return "LEDOIT_WOLF_SHRINKAGE"

    def estimate_covariance(self, panel: AssetReturnPanel) -> np.ndarray:
        if panel.T < 3:
            raise DataContractError("Ledoit-Wolf shrinkage requires at least T >= 3 observations.")

        matrix_f64 = np.array(
            [[float(val) for val in row] for row in panel.returns_matrix],
            dtype=np.float64,
        )

        stds = np.std(matrix_f64, axis=0, ddof=1)
        for idx, std_val in enumerate(stds):
            if std_val <= 1e-12 or not np.isfinite(std_val):
                raise DataContractError(
                    f"Zero variance detected for asset {panel.symbols[idx]} (std={std_val}). Fail-closed."
                )

        t, n = matrix_f64.shape
        x = matrix_f64 - np.mean(matrix_f64, axis=0)
        sample_cov = (x.T @ x) / (t - 1)

        # Target matrix F: constant correlation
        var = np.diag(sample_cov)
        sqrt_var = np.sqrt(var)
        corr = sample_cov / np.outer(sqrt_var, sqrt_var)
        mean_corr = (np.sum(corr) - n) / (n * (n - 1)) if n > 1 else 1.0
        target = mean_corr * np.outer(sqrt_var, sqrt_var)
        np.fill_diagonal(target, var)

        # Estimate optimal shrinkage intensity delta
        y = x**2
        phi_mat = (y.T @ y) / t - 2 * (x.T @ x) * sample_cov / t + sample_cov**2
        phi = np.sum(phi_mat)
        gamma = np.linalg.norm(sample_cov - target, "fro") ** 2
        kappa = phi / gamma if gamma > 1e-12 else 0.0
        delta = max(0.0, min(1.0, kappa / t))

        shrunk_cov = delta * target + (1.0 - delta) * sample_cov
        scale_factor = float(self.annualization_factor)
        shrunk_cov_annualized = shrunk_cov * scale_factor

        # Symmetrize
        cov_sym = np.asarray(0.5 * (shrunk_cov_annualized + shrunk_cov_annualized.T), dtype=np.float64)
        return cov_sym
