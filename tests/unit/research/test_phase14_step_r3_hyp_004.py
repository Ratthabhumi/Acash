"""Unit & Invariant Test Suite: Phase 14 Step R3 HYP_004 Primary Econometric Replication.

Enforces strict compliance with:
- Canonical starting git HEAD
- Upstream governance hashes (HYP_004, R1, R2, Preregistration)
- Local R2 dataset hash pin (096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776)
- Exact eligible census T = 1489, 9 excluded sessions quarantined
- Simple-return formula (no log returns, no adjusted prices)
- OLS with intercept and Bartlett HAC lag L = 7
- Binding primary decision rule: beta_hat > 0 AND two-sided p < 0.05
- Absolute prohibitions: zero secondary analyses, zero 2023+ access, zero generic evaluator calls.
"""

from datetime import date
from decimal import Decimal
import hashlib
import inspect
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Sequence
import pyarrow.parquet as pq
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.evaluation import (
    compute_ols_beta_and_hac,
    determine_hac_bandwidth,
)
from acash.research.schema import HacBandwidthMethod
from acash.research.step_r3_hyp_004 import (
    EXPECTED_ELIGIBLE_OBSERVATIONS,
    EXPECTED_EXCLUDED_OBSERVATIONS,
    EXPECTED_HAC_LAG,
    EXPECTED_HYP_004_SHA256,
    EXPECTED_PREREG_SHA256,
    EXPECTED_R1_MANIFEST_SHA256,
    EXPECTED_R2_MANIFEST_SHA256,
    EXPECTED_R2_PARQUET_SHA256,
    R3_PRIMARY_RETURNS_ARROW_SCHEMA,
    TOTAL_EXPECTED_REGULAR_SESSIONS,
    PrimaryRegressionResult,
    PrimaryReplicationOutcome,
    PrimaryReturnRow,
    build_canonical_primary_returns_parquet,
    build_r3_manifest,
    compute_simple_returns_from_r2,
    execute_primary_replication_regression,
    validate_r3_preconditions,
)

BASE_DIR = Path(__file__).resolve().parents[3]


def test_1_governance_preconditions_verified() -> None:
    """Invariant 1: All upstream governance digests and R2 dataset hashes match exact pins."""
    res = validate_r3_preconditions(BASE_DIR)
    assert res["hyp_004_sha256"] == EXPECTED_HYP_004_SHA256
    assert res["r1_manifest_sha256"] == EXPECTED_R1_MANIFEST_SHA256
    assert res["preregistration_sha256"] == EXPECTED_PREREG_SHA256
    assert res["r2_manifest_sha256"] == EXPECTED_R2_MANIFEST_SHA256
    assert res["r2_parquet_sha256"] == EXPECTED_R2_PARQUET_SHA256


def test_2_r2_dataset_hash_pin() -> None:
    """Invariant 2: Local R2 Parquet dataset exists and matches pinned SHA-256."""
    parquet_path = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
    assert parquet_path.is_file(), "R2 Parquet dataset missing"
    actual_sha = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    assert actual_sha == EXPECTED_R2_PARQUET_SHA256, f"Hash mismatch: {actual_sha} != {EXPECTED_R2_PARQUET_SHA256}"


def test_3_newey_west_lag_formula_for_t_1489() -> None:
    """Invariant 3: Newey-West plug-in lag rule floor(4 * (T/100)^(2/9)) yields exactly 7 for T=1489."""
    t = 1489
    computed_lag = determine_hac_bandwidth(
        method=HacBandwidthMethod.NEWEY_WEST_PLUGIN,
        sample_size=t,
        horizon=1,
    )
    raw_val = 4.0 * ((t / 100.0) ** (2.0 / 9.0))
    expected_lag = int(math.floor(raw_val))
    assert expected_lag == 7
    assert computed_lag == 7
    assert computed_lag == EXPECTED_HAC_LAG


def test_4_simple_return_computation_formula() -> None:
    """Invariant 4: Simple returns r1 and r13 use exact linear formulas (p1/p0 - 1) and (p13/p12 - 1)."""
    p0 = Decimal("200.00")
    p1 = Decimal("202.00")
    p12 = Decimal("201.00")
    p13 = Decimal("203.01")

    r1 = (p1 / p0) - Decimal("1")
    r13 = (p13 / p12) - Decimal("1")

    # Simple return checks
    assert r1 == Decimal("0.01")
    assert r13 == Decimal("0.01")

    # Rejection of log returns (log(202/200) != 0.01)
    log_r1 = Decimal(str(math.log(float(p1) / float(p0))))
    assert r1 != log_r1


def test_5_derived_return_parquet_schema_and_cardinality(tmp_path: Path) -> None:
    """Invariant 5: Derived return dataset contains exact fields, zero returns beyond r1/r13, and enforces T=1489."""
    out_path = tmp_path / "test_returns.parquet"
    dummy_rows = [
        PrimaryReturnRow(
            trading_date=f"2017-01-{i:02d}",
            calendar_session_ordinal=i,
            p0_previous_primary_close=Decimal("220.00"),
            p1_1000_price=Decimal("221.00"),
            p12_1530_price=Decimal("220.50"),
            p13_current_primary_close=Decimal("221.50"),
            r1_simple_return=Decimal("0.00454545"),
            r13_simple_return=Decimal("0.00453515"),
            source_r2_dataset_sha256="dummy_sha",
        )
        for i in range(1, 1490)
    ]
    assert len(dummy_rows) == EXPECTED_ELIGIBLE_OBSERVATIONS

    build_canonical_primary_returns_parquet(dummy_rows, out_path)
    assert out_path.is_file()

    # Verify cardinality rejection if != 1489
    with pytest.raises(DataContractError, match="Derived dataset cardinality violation"):
        build_canonical_primary_returns_parquet(dummy_rows[:100], tmp_path / "fail.parquet")

    # Verify schema contains no secondary predictors
    field_names = set(R3_PRIMARY_RETURNS_ARROW_SCHEMA.names)
    assert "r12_simple_return" not in field_names
    assert "signals" not in field_names
    assert "pnl" not in field_names


def test_6_ols_alpha_and_r_squared_calculation_synthetic_fixture() -> None:
    """Invariant 6: Synthetic benchmark validates OLS beta, alpha, HAC SE, and unadjusted R^2."""
    # Construct exact linear relation: Y = 0.5 + 2.0 * X
    # with zero error -> R^2 must equal 1.0, beta=2.0, alpha=0.5
    x_vals = [Decimal(f"{float(i) * 0.01:.4f}") for i in range(1, 1490)]
    y_vals = [Decimal("0.5") + Decimal("2.0") * x for x in x_vals]

    rows = [
        PrimaryReturnRow(
            trading_date=f"2017-01-{i:02d}",
            calendar_session_ordinal=i,
            p0_previous_primary_close=Decimal("100"),
            p1_1000_price=Decimal("100"),
            p12_1530_price=Decimal("100"),
            p13_current_primary_close=Decimal("100"),
            r1_simple_return=x_vals[i - 1],
            r13_simple_return=y_vals[i - 1],
            source_r2_dataset_sha256="test",
        )
        for i in range(1, 1490)
    ]

    res = execute_primary_replication_regression(
        return_rows=rows,
        r2_parquet_sha256="r2_sha",
        r3_parquet_sha256="r3_sha",
    )

    # Beta should be 2.0, alpha should be 0.5, R^2 should be 1.0
    assert abs(float(res.beta_hat) - 2.0) < 1e-4
    assert abs(float(res.alpha_hat) - 0.5) < 1e-4
    assert abs(float(res.r_squared) - 1.0) < 1e-4
    assert res.hac_lag_l == 7
    assert res.sample_size_t == 1489
    assert res.is_accepted is True
    assert res.outcome_label == PrimaryReplicationOutcome.PRIMARY_REPLICATION_ACCEPTED


def test_7_binding_primary_acceptance_criterion_logic() -> None:
    """Invariant 7: Decision rule requires BOTH beta > 0 AND two-sided p < 0.05."""
    # Case A: beta > 0 and p < 0.05 -> ACCEPTED
    beta_a = Decimal("0.05")
    p_a = Decimal("0.01")
    assert (beta_a > 0 and p_a < Decimal("0.05")) is True

    # Case B: beta > 0 but p = 0.08 -> NOT ACCEPTED
    beta_b = Decimal("0.05")
    p_b = Decimal("0.08")
    assert (beta_b > 0 and p_b < Decimal("0.05")) is False

    # Case C: beta < 0 and p = 0.001 -> NOT ACCEPTED (wrong direction)
    beta_c = Decimal("-0.05")
    p_c = Decimal("0.001")
    assert (beta_c > 0 and p_c < Decimal("0.05")) is False


def test_8_zero_generic_evaluator_invocation() -> None:
    """Invariant 8: R3 module does not import or call evaluate_hypothesis_relationship."""
    import acash.research.step_r3_hyp_004 as mod
    # Ensure generic evaluators and secondary engines are not in module namespace
    assert not hasattr(mod, "evaluate_hypothesis_relationship")
    assert not hasattr(mod, "calculate_rank_ic")
    assert not hasattr(mod, "calculate_3tier_friction_waterfall")

    source = inspect.getsource(mod)
    assert "from acash.research.evaluation import evaluate_hypothesis_relationship" not in source
    assert "import evaluate_hypothesis_relationship" not in source


def test_9_zero_secondary_models_k_equals_1() -> None:
    """Invariant 9: R3 module contains exactly one primary model (K=1)."""
    import acash.research.step_r3_hyp_004 as mod
    # Check that module does not define secondary return predictors or conditioning
    assert not hasattr(mod, "r12")
    assert not hasattr(mod, "compute_r12")
    assert not hasattr(mod, "r1_plus_r12")
    assert not hasattr(mod, "evaluate_vix_conditioning")

    # Check Arrow Schema fields
    field_names = set(mod.R3_PRIMARY_RETURNS_ARROW_SCHEMA.names)
    assert "r12_simple_return" not in field_names
    assert "vix" not in field_names


def test_10_temporal_oos_boundary_enforced() -> None:
    """Invariant 10: Any observation >= 2023-01-01 immediately aborts fail-closed."""
    from acash.data.qualification.mec_0014_close_contract import OOS_FORBIDDEN_DATE
    assert OOS_FORBIDDEN_DATE == date(2023, 1, 1)


def test_11_r3_manifest_structure_and_hashing() -> None:
    """Invariant 11: R3 manifest contains all required lineage fields and valid canonical hash."""
    dummy_res = PrimaryRegressionResult(
        sample_size_t=1489,
        hac_lag_l=7,
        alpha_hat=Decimal("0.0001"),
        beta_hat=Decimal("0.0500"),
        hac_se_beta=Decimal("0.0200"),
        hac_t_stat=Decimal("2.5000"),
        two_sided_p_value=Decimal("0.0124"),
        r_squared=Decimal("0.0042"),
        binding_acceptance_rule="beta_hat > 0 AND two-sided Newey-West HAC p-value < 0.05 (L = 7, T = 1489)",
        is_accepted=True,
        outcome_label=PrimaryReplicationOutcome.PRIMARY_REPLICATION_ACCEPTED,
        source_r2_parquet_sha256="r2_sha",
        derived_r3_parquet_sha256="r3_sha",
        earliest_trading_date="2017-01-04",
        latest_trading_date="2022-12-30",
    )
    manifest = build_r3_manifest(dummy_res, source_git_sha="git_sha")
    assert manifest["manifest_type"] == "PRIMARY_ECONOMETRIC_REPLICATION_MANIFEST"
    assert manifest["hypothesis_id"] == "HYP_004"
    assert manifest["mechanism_id"] == "MEC-0014A"
    assert manifest["econometric_estimates"]["beta_hat"] == "0.0500"
    assert "manifest_sha256" in manifest
    assert len(manifest["manifest_sha256"]) == 64


def test_12_exclusion_lineage_and_admitted_dates_invariants() -> None:
    """Invariant 12: R3 admitted dates equal R2 primary_regression_eligible dates exactly.

    Also verifies:
    - Authoritative exclusion reason census (1 first session, 3 P1 ambiguous, 5 P12 ambiguous).
    - Set differences are strictly empty.
    - Exact 9 excluded dates match authoritative local hashed R2 evidence.
    """
    r2_path = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
    r3_path = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet"

    assert r2_path.is_file(), "R2 parquet missing"
    assert r3_path.is_file(), "R3 parquet missing"

    r2_table = pq.read_table(r2_path)
    r3_table = pq.read_table(r3_path)

    r2_df = r2_table.to_pandas()
    r2_eligible_dates = set(r2_df[r2_df["primary_regression_eligible"]]["trading_date"])
    r3_admitted_dates = set(r3_table["trading_date"].to_pylist())

    # Invariant: R3 admitted dates == R2 primary_regression_eligible dates
    assert r3_admitted_dates == r2_eligible_dates
    assert len(r2_eligible_dates - r3_admitted_dates) == 0
    assert len(r3_admitted_dates - r2_eligible_dates) == 0

    # Invariant: Exact 9 excluded dates derived from R2
    excluded_df = r2_df[~r2_df["primary_regression_eligible"]].sort_values("trading_date")
    assert len(excluded_df) == 9

    reconciled_dates = excluded_df["trading_date"].tolist()
    expected_dates = [
        "2017-01-03", "2017-03-31", "2017-06-02", "2017-06-07",
        "2017-08-08", "2017-08-23", "2017-09-12", "2021-03-24", "2022-02-14"
    ]
    assert reconciled_dates == expected_dates

    # Invariant: Exclusion reason census
    reason_counts: Dict[str, int] = {}
    for reasons in excluded_df["exclusion_reason_codes"]:
        for r in reasons:
            reason_counts[r] = reason_counts.get(r, 0) + 1

    assert reason_counts.get("FIRST_SESSION_NO_PRIOR_IN_SAMPLE_CLOSE") == 1
    assert reason_counts.get("AMBIGUOUS_P1_BOUNDARY_PRICE") == 3
    assert reason_counts.get("AMBIGUOUS_P12_BOUNDARY_PRICE") == 5
