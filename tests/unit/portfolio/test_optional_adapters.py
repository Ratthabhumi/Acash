"""Unit and Boundary Invariant Tests for Level 3 Optional Optimizer Adapters (Phase 8 Batch 3C).

Includes:
1. Mocked tests for missing dependencies and failure modes (runs in all environments).
2. Real-package integration tests (executed when skfolio/cvxpy are installed, skipped cleanly otherwise).
3. Cross-model semantic parity verification between Native HRP and skfolio HRP.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.adapters.cvxpy_adapter import CvxpyMeanRiskAdapter
from acash.portfolio.adapters.skfolio_adapter import SkfolioHRPAdapter, SkfolioMeanRiskAdapter
from acash.portfolio.estimators import SampleCovarianceEstimator
from acash.portfolio.optimizers import HierarchicalRiskParityAllocator
from acash.portfolio.schema import (
    AllocationCandidate,
    AssetReturnPanel,
    PortfolioConstraints,
)


def _default_constraints() -> PortfolioConstraints:
    return PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("1.0"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )


def _sample_return_panel(n_obs: int = 100) -> AssetReturnPanel:
    np.random.seed(42)
    t1 = np.random.normal(0.001, 0.012, n_obs)
    t2 = 0.8 * t1 + np.random.normal(0.0005, 0.008, n_obs)
    t3 = 0.3 * t1 + np.random.normal(0.0008, 0.018, n_obs)

    timestamps = tuple(
        datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        for _ in range(n_obs)
    )
    matrix = tuple(
        (Decimal(str(round(t1[i], 6))), Decimal(str(round(t2[i], 6))), Decimal(str(round(t3[i], 6))))
        for i in range(n_obs)
    )
    return AssetReturnPanel(
        universe_id="UNIV_OPT_3A",
        timestamps=timestamps,
        symbols=("AAPL", "MSFT", "GOOG"),
        returns_matrix=matrix,
        frequency="1D",
    )


# ==============================================================================
# SECTION 1: Mocked Unit Tests (Run in ALL environments without packages)
# ==============================================================================

def test_skfolio_missing_dependency_fail_closed() -> None:
    adapter = SkfolioHRPAdapter()
    panel = _sample_return_panel()

    with patch("importlib.import_module", side_effect=ModuleNotFoundError("No module named 'skfolio'")):
        with pytest.raises(DataContractError, match="Optional dependency 'skfolio' is not installed"):
            adapter.compute_candidate(panel, _default_constraints(), {})


def test_cvxpy_missing_dependency_fail_closed() -> None:
    adapter = CvxpyMeanRiskAdapter()
    panel = _sample_return_panel()

    with patch("importlib.import_module", side_effect=ModuleNotFoundError("No module named 'cvxpy'")):
        with pytest.raises(DataContractError, match="Optional dependency 'cvxpy' is not installed"):
            adapter.compute_candidate(panel, _default_constraints(), {})


def test_skfolio_hrp_mocked_successful_solve() -> None:
    adapter = SkfolioHRPAdapter()
    panel = _sample_return_panel()

    mock_sk_opt = MagicMock()
    mock_model = MagicMock()
    mock_model.weights_ = np.array([0.3, 0.4, 0.3], dtype=np.float64)
    mock_sk_opt.HierarchicalRiskParity.return_value = mock_model

    with patch("importlib.import_module", return_value=mock_sk_opt):
        cand = adapter.compute_candidate(panel, _default_constraints(), {})

        assert isinstance(cand, AllocationCandidate)
        assert cand.allocator_name == "SKFOLIO_HIERARCHICAL_RISK_PARITY"
        assert len(cand.asset_weights) == 3
        assert cand.cash_weight == Decimal("0.05")
        assert cand.candidate_digest != ""


def test_skfolio_solver_exception_fail_closed() -> None:
    adapter = SkfolioHRPAdapter()
    panel = _sample_return_panel()

    mock_sk_opt = MagicMock()
    mock_model = MagicMock()
    mock_model.fit.side_effect = RuntimeError("Singular distance matrix")
    mock_sk_opt.HierarchicalRiskParity.return_value = mock_model

    with patch("importlib.import_module", return_value=mock_sk_opt):
        with pytest.raises(DataContractError, match="skfolio HRP solver failed during execution"):
            adapter.compute_candidate(panel, _default_constraints(), {})


def test_skfolio_nan_weights_fail_closed() -> None:
    adapter = SkfolioHRPAdapter()
    panel = _sample_return_panel()

    mock_sk_opt = MagicMock()
    mock_model = MagicMock()
    mock_model.weights_ = np.array([np.nan, 0.5, 0.5], dtype=np.float64)
    mock_sk_opt.HierarchicalRiskParity.return_value = mock_model

    with patch("importlib.import_module", return_value=mock_sk_opt):
        with pytest.raises(DataContractError, match="skfolio HRP returned non-finite weights"):
            adapter.compute_candidate(panel, _default_constraints(), {})


def test_skfolio_negative_weights_fail_closed() -> None:
    adapter = SkfolioHRPAdapter()
    panel = _sample_return_panel()

    mock_sk_opt = MagicMock()
    mock_model = MagicMock()
    mock_model.weights_ = np.array([-0.2, 0.6, 0.6], dtype=np.float64)
    mock_sk_opt.HierarchicalRiskParity.return_value = mock_model

    with patch("importlib.import_module", return_value=mock_sk_opt):
        with pytest.raises(DataContractError, match="skfolio HRP returned negative weights"):
            adapter.compute_candidate(panel, _default_constraints(), {})


def test_skfolio_length_mismatch_fail_closed() -> None:
    adapter = SkfolioHRPAdapter()
    panel = _sample_return_panel()

    mock_sk_opt = MagicMock()
    mock_model = MagicMock()
    mock_model.weights_ = np.array([0.5, 0.5], dtype=np.float64)  # 2 weights for 3 assets
    mock_sk_opt.HierarchicalRiskParity.return_value = mock_model

    with patch("importlib.import_module", return_value=mock_sk_opt):
        with pytest.raises(DataContractError, match="skfolio output weight count.*does not match asset count"):
            adapter.compute_candidate(panel, _default_constraints(), {})


def test_cvxpy_mocked_successful_solve() -> None:
    adapter = CvxpyMeanRiskAdapter()
    panel = _sample_return_panel()

    mock_cp = MagicMock()
    mock_var = MagicMock()
    mock_var.__ge__.return_value = MagicMock()
    mock_var.__le__.return_value = MagicMock()
    mock_var.value = np.array([0.30, 0.35, 0.30], dtype=np.float64)
    mock_cp.Variable.return_value = mock_var

    mock_prob = MagicMock()
    mock_prob.status = "optimal"
    mock_prob.value = 0.015
    mock_cp.Problem.return_value = mock_prob

    with patch("importlib.import_module", return_value=mock_cp):
        cand = adapter.compute_candidate(panel, _default_constraints(), {})

        assert isinstance(cand, AllocationCandidate)
        assert cand.allocator_name == "CVXPY_MINIMUM_VARIANCE"
        assert cand.asset_weights["AAPL"] == Decimal("0.3")
        assert cand.asset_weights["GOOG"] == Decimal("0.35")
        assert cand.asset_weights["MSFT"] == Decimal("0.3")
        assert cand.cash_weight == Decimal("0.05")


def test_cvxpy_infeasible_status_fail_closed() -> None:
    adapter = CvxpyMeanRiskAdapter()
    panel = _sample_return_panel()

    mock_cp = MagicMock()
    mock_var = MagicMock()
    mock_var.__ge__.return_value = MagicMock()
    mock_var.__le__.return_value = MagicMock()
    mock_cp.Variable.return_value = mock_var

    mock_prob = MagicMock()
    mock_prob.status = "infeasible"
    mock_cp.Problem.return_value = mock_prob

    with patch("importlib.import_module", return_value=mock_cp):
        with pytest.raises(DataContractError, match="CVXPY solver ended with non-optimal status: 'infeasible'"):
            adapter.compute_candidate(panel, _default_constraints(), {})


def test_cvxpy_none_weights_fail_closed() -> None:
    adapter = CvxpyMeanRiskAdapter()
    panel = _sample_return_panel()

    mock_cp = MagicMock()
    mock_var = MagicMock()
    mock_var.__ge__.return_value = MagicMock()
    mock_var.__le__.return_value = MagicMock()
    mock_var.value = None
    mock_cp.Variable.return_value = mock_var
    mock_prob = MagicMock()
    mock_prob.status = "optimal"
    mock_cp.Problem.return_value = mock_prob

    with patch("importlib.import_module", return_value=mock_cp):
        with pytest.raises(DataContractError, match="CVXPY solver returned None weight vector"):
            adapter.compute_candidate(panel, _default_constraints(), {})


# ==============================================================================
# SECTION 2: Provenance & Fingerprint Invariant Tests (Mocked & Unit)
# ==============================================================================

def test_skfolio_meanrisk_config_fingerprint_sensitivity() -> None:
    """Verify that changing any material MeanRisk parameter alters the configuration fingerprint."""
    mr1 = SkfolioMeanRiskAdapter(objective="MINIMIZE_RISK", risk_measure="VARIANCE")
    mr2 = SkfolioMeanRiskAdapter(objective="MAXIMIZE_RATIO", risk_measure="VARIANCE")
    mr3 = SkfolioMeanRiskAdapter(objective="MINIMIZE_RISK", risk_measure="CVAR")
    mr4 = SkfolioMeanRiskAdapter(objective="MINIMIZE_RISK", risk_measure="VARIANCE", solver="OSQP")
    mr5 = SkfolioMeanRiskAdapter(objective="MINIMIZE_RISK", risk_measure="VARIANCE", efficient_frontier_size=10)

    fingerprints = {mr1.config_fingerprint, mr2.config_fingerprint, mr3.config_fingerprint, mr4.config_fingerprint, mr5.config_fingerprint}
    assert len(fingerprints) == 5, "Each distinct MeanRisk configuration must have a unique SHA-256 fingerprint."


def test_skfolio_hrp_config_fingerprint_sensitivity() -> None:
    """Verify that changing HRP kwargs alters configuration fingerprint."""
    hrp1 = SkfolioHRPAdapter()
    hrp2 = SkfolioHRPAdapter(min_weights=0.01)
    hrp3 = SkfolioHRPAdapter(min_weights=0.05)

    fingerprints = {hrp1.config_fingerprint, hrp2.config_fingerprint, hrp3.config_fingerprint}
    assert len(fingerprints) == 3, "Each distinct HRP configuration must have a unique SHA-256 fingerprint."


def test_cvxpy_solver_config_fingerprint_sensitivity() -> None:
    """Verify that specifying different solvers in CVXPY alters configuration fingerprint."""
    c1 = CvxpyMeanRiskAdapter(solver="CLARABEL")
    c2 = CvxpyMeanRiskAdapter(solver="OSQP")
    c3 = CvxpyMeanRiskAdapter(solver="SCS")

    fingerprints = {c1.config_fingerprint, c2.config_fingerprint, c3.config_fingerprint}
    assert len(fingerprints) == 3, "Different CVXPY solvers must have distinct SHA-256 fingerprints."


def test_cvxpy_provenance_and_numeric_boundary_structure() -> None:
    """Verify that AllocationCandidate from CVXPY adapter captures full solver and numeric provenance."""
    adapter = CvxpyMeanRiskAdapter(solver="CLARABEL")
    panel = _sample_return_panel()

    mock_cp = MagicMock()
    mock_var = MagicMock()
    mock_var.__ge__.return_value = MagicMock()
    mock_var.__le__.return_value = MagicMock()
    mock_var.value = np.array([0.30, 0.35, 0.30], dtype=np.float64)
    mock_cp.Variable.return_value = mock_var
    mock_prob = MagicMock()
    mock_prob.status = "optimal"
    mock_prob.value = 0.015
    mock_cp.Problem.return_value = mock_prob

    with patch("importlib.import_module", return_value=mock_cp):
        cand = adapter.compute_candidate(panel, _default_constraints(), {})

        prov = cand.provenance
        assert prov["backend_package"] == "cvxpy"
        assert prov["solver"] == "CLARABEL"
        assert prov["solver_status"] == "OPTIMAL"
        assert prov["config_fingerprint"] == adapter.config_fingerprint
        assert prov["numeric_backend"] == "IEEE_754_FLOAT64"
        assert prov["input_numeric_projection"] == "DECIMAL_TO_FLOAT64"
        assert prov["output_numeric_projection"] == "FLOAT64_TO_DECIMAL"
        assert prov["conversion_policy"] == "CANONICAL_DECIMAL_REPRESENTATION_FLOAT64"


def test_skfolio_provenance_and_numeric_boundary_structure() -> None:
    """Verify that AllocationCandidate from skfolio adapter captures full solver and numeric provenance."""
    adapter = SkfolioHRPAdapter(linkage_method="single")
    panel = _sample_return_panel()

    mock_sk_opt = MagicMock()
    mock_model = MagicMock()
    mock_model.weights_ = np.array([0.3, 0.4, 0.3], dtype=np.float64)
    mock_sk_opt.HierarchicalRiskParity.return_value = mock_model

    with patch("importlib.import_module", return_value=mock_sk_opt):
        cand = adapter.compute_candidate(panel, _default_constraints(), {})

        prov = cand.provenance
        assert prov["backend_package"] == "skfolio"
        assert prov["solver"] == "SCH_LINKAGE"
        assert prov["solver_status"] == "OPTIMAL"
        assert prov["config_fingerprint"] == adapter.config_fingerprint
        assert prov["numeric_backend"] == "IEEE_754_FLOAT64"
        assert prov["input_numeric_projection"] == "DECIMAL_TO_FLOAT64"
        assert prov["output_numeric_projection"] == "FLOAT64_TO_DECIMAL"
        assert prov["conversion_policy"] == "CANONICAL_DECIMAL_REPRESENTATION_FLOAT64"


# ==============================================================================
# SECTION 3: Real Integration Tests (Executed when optional packages installed)
# ==============================================================================

def test_skfolio_real_runtime_hrp_execution() -> None:
    pytest.importorskip("skfolio")
    adapter = SkfolioHRPAdapter()
    panel = _sample_return_panel()
    cand = adapter.compute_candidate(panel, _default_constraints(), {})

    assert isinstance(cand, AllocationCandidate)
    assert cand.allocator_name == "SKFOLIO_HIERARCHICAL_RISK_PARITY"
    assert len(cand.asset_weights) == 3
    assert cand.cash_weight is not None
    assert cand.cash_weight >= Decimal("0.05")
    assert sum(cand.asset_weights.values()) + cand.cash_weight == Decimal("1.0")
    assert cand.provenance["backend_package"] == "skfolio"
    assert cand.provenance["solver"] == "SCH_LINKAGE"
    assert cand.provenance["numeric_backend"] == "IEEE_754_FLOAT64"


def test_cvxpy_real_runtime_minimum_variance_execution() -> None:
    pytest.importorskip("cvxpy")
    adapter = CvxpyMeanRiskAdapter(solver="CLARABEL")
    panel = _sample_return_panel()
    cand = adapter.compute_candidate(panel, _default_constraints(), {})

    assert isinstance(cand, AllocationCandidate)
    assert cand.allocator_name == "CVXPY_MINIMUM_VARIANCE"
    assert len(cand.asset_weights) == 3
    assert cand.cash_weight is not None
    assert cand.cash_weight >= Decimal("0.05")
    assert sum(cand.asset_weights.values()) + cand.cash_weight == Decimal("1.0")
    assert cand.provenance["backend_package"] == "cvxpy"
    assert cand.provenance["solver"] == "CLARABEL"
    assert cand.provenance["solver_status"] == "OPTIMAL"


def test_cross_model_parity_native_vs_skfolio_hrp() -> None:
    pytest.importorskip("skfolio")
    panel = _sample_return_panel()
    constraints = _default_constraints()

    # When both Native HRP and skfolio HRP use sample covariance, they are identical to high precision
    native_cand = HierarchicalRiskParityAllocator(covariance_estimator=SampleCovarianceEstimator()).compute_candidate(panel, constraints, {})
    skfolio_cand = SkfolioHRPAdapter().compute_candidate(panel, constraints, {})

    for sym in panel.symbols:
        native_w = native_cand.asset_weights[sym]
        skfolio_w = skfolio_cand.asset_weights[sym]
        diff = abs(native_w - skfolio_w)
        assert diff < Decimal("0.0001"), f"HRP discrepancy on {sym}: Native={native_w}, skfolio={skfolio_w}"
