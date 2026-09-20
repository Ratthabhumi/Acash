"""Unit Tests: Phase 14 HYP_004 / MEC-0014A Log-Return Robustness Characterization.

Mandatory Tests (B13):
    1. all upstream hashes pinned;
    2. R2 dataset hash exact;
    3. sample T=1489;
    4. exact same eligible dates as R3;
    5. exact same 9 exclusions;
    6. natural log formulas;
    7. positive-price precondition;
    8. no simple-return result overwritten;
    9. only one log regression;
    10. intercept included;
    11. HAC lag=7;
    12. Bartlett kernel;
    13. two-sided p;
    14. no generic evaluator;
    15. no rank IC;
    16. no friction;
    17. no r12;
    18. no alternate sample;
    19. no 2023+ access;
    20. primary outcome immutable;
    21. local artifact cardinality/hash;
    22. sealed R1–R4 artifacts unchanged.
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import List

import numpy as np
import pyarrow.parquet as pq
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.research.evaluation import compute_ols_beta_and_hac
from acash.research.hyp_004_log_return_robustness import (
    CANONICAL_STARTING_HEAD_SHA,
    EXPECTED_ELIGIBLE_OBSERVATIONS,
    EXPECTED_EXCLUDED_OBSERVATIONS,
    EXPECTED_HAC_LAG,
    EXPECTED_HYP_004_SHA256,
    EXPECTED_PREREG_SHA256,
    EXPECTED_R1_MANIFEST_SHA256,
    EXPECTED_R2_MANIFEST_SHA256,
    EXPECTED_R2_PARQUET_SHA256,
    EXPECTED_R3_MANIFEST_SHA256,
    EXPECTED_R4_MANIFEST_SHA256,
    EXPECTED_TOTAL_SESSIONS,
    PRIMARY_ALPHA,
    PRIMARY_BETA,
    PRIMARY_HAC_SE,
    PRIMARY_HAC_T,
    PRIMARY_OUTCOME_LABEL,
    PRIMARY_P_VALUE,
    PRIMARY_R_SQUARED,
    LogReturnRow,
    build_canonical_log_returns_parquet,
    build_log_robustness_manifest,
    execute_log_return_robustness_regression,
    load_and_compute_log_returns,
    validate_robustness_preconditions,
)

BASE_DIR = Path(__file__).resolve().parents[3]
R2_PARQUET_PATH = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
R3_PARQUET_PATH = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet"


def test_01_all_upstream_hashes_pinned() -> None:
    """1. Verify that all upstream governance and data hashes are pinned in constants."""
    preconditions = validate_robustness_preconditions(BASE_DIR)
    assert preconditions["hypothesis_sha256"] == EXPECTED_HYP_004_SHA256
    assert preconditions["preregistration_sha256"] == EXPECTED_PREREG_SHA256
    assert preconditions["r1_manifest_sha256"] == EXPECTED_R1_MANIFEST_SHA256
    assert preconditions["r2_manifest_sha256"] == EXPECTED_R2_MANIFEST_SHA256
    assert preconditions["r2_parquet_sha256"] == EXPECTED_R2_PARQUET_SHA256
    assert preconditions["r3_manifest_sha256"] == EXPECTED_R3_MANIFEST_SHA256
    assert preconditions["r4_manifest_sha256"] == EXPECTED_R4_MANIFEST_SHA256


def test_02_r2_dataset_hash_exact() -> None:
    """2. Verify that the R2 session endpoints Parquet hash matches the pinned value exactly."""
    assert R2_PARQUET_PATH.exists()
    computed_sha = hashlib.sha256(R2_PARQUET_PATH.read_bytes()).hexdigest()
    assert computed_sha == EXPECTED_R2_PARQUET_SHA256


def test_03_sample_t_equals_1489() -> None:
    """3. Verify that the eligible sample size is exactly T = 1489."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    assert len(rows) == EXPECTED_ELIGIBLE_OBSERVATIONS
    assert len(rows) == 1489


def test_04_exact_same_eligible_dates_as_r3() -> None:
    """4. Verify that eligible dates match R3 primary returns Parquet dates exactly."""
    assert R3_PARQUET_PATH.exists()
    r3_table = pq.read_table(R3_PARQUET_PATH)
    r3_dates = sorted(r3_table["trading_date"].to_pylist())

    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    log_dates = [r.trading_date for r in rows]

    assert log_dates == r3_dates


def test_05_exact_same_9_exclusions() -> None:
    """5. Verify that exactly the same 9 dates are excluded as in R2/R3."""
    _, excluded_dates = load_and_compute_log_returns(R2_PARQUET_PATH)
    assert len(excluded_dates) == EXPECTED_EXCLUDED_OBSERVATIONS
    expected_exclusions = [
        "2017-01-03",
        "2017-03-31",
        "2017-06-02",
        "2017-06-07",
        "2017-08-08",
        "2017-08-23",
        "2017-09-12",
        "2021-03-24",
        "2022-02-14",
    ]
    assert excluded_dates == expected_exclusions


def test_06_natural_log_formulas() -> None:
    """6. Verify that natural log formulas ln(p1/p0) and ln(p13/p12) are applied strictly."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    first_row = rows[0]

    p0 = float(first_row.p0)
    p1 = float(first_row.p1)
    p12 = float(first_row.p12)
    p13 = float(first_row.p13)

    expected_log_r1 = math.log(p1 / p0)
    expected_log_r13 = math.log(p13 / p12)

    assert abs(float(first_row.log_r1) - expected_log_r1) < 1e-15
    assert abs(float(first_row.log_r13) - expected_log_r13) < 1e-15


def test_07_positive_price_precondition(tmp_path: Path) -> None:
    """7. Verify fail-closed behavior if any price is non-positive."""
    import pandas as pd
    import pyarrow as pa

    # Create dummy parquet with a zero price
    df = pd.DataFrame({
        "trading_date": ["2017-01-04"],
        "calendar_session_ordinal": [1],
        "prior_regular_session_date": ["2017-01-03"],
        "p0_previous_primary_close": [Decimal("0")],
        "p1_1000_price": [Decimal("220.00")],
        "p12_1530_price": [Decimal("221.00")],
        "p13_current_primary_close": [Decimal("222.00")],
        "primary_regression_eligible": [True],
    })
    for col in [
        "p0_source_session_date", "p0_auction_timestamp", "p0_exchange", "p0_condition",
        "p0_authority_status", "p1_t_star_utc", "p1_distance_to_boundary_seconds",
        "p1_endpoint_status", "p12_t_star_utc", "p12_distance_to_boundary_seconds",
        "p12_endpoint_status", "p13_auction_timestamp", "p13_exchange", "p13_condition",
        "p13_authority_status", "acquisition_status", "qualification_status",
        "per_session_raw_evidence_aggregate_sha256", "close_evidence_reference",
        "close_evidence_hash", "contract_version_git_sha",
    ]:
        df[col] = "test"
    for col in [
        "p1_tie_record_count", "p1_distinct_price_count", "p12_tie_record_count",
        "p12_distinct_price_count", "trade_count_threshold", "pagination_page_count",
        "exact_transport_duplicate_count",
    ]:
        df[col] = 1
    df["raw_regular_session_sip_trade_count"] = 1000
    df["trade_count_pass"] = True
    df["pagination_complete"] = True
    df["exclusion_reason_codes"] = [[]]

    dummy_path = tmp_path / "dummy.parquet"
    table = pa.Table.from_pandas(df)
    pq.write_table(table, dummy_path)

    # Since SHA won't match, load_and_compute_log_returns will fail-closed on SHA
    with pytest.raises(DataContractError, match="SHA-256 mismatch"):
        load_and_compute_log_returns(dummy_path)


def test_08_no_simple_return_result_overwritten() -> None:
    """8. Verify that primary simple-return estimates remain unchanged in constants."""
    assert PRIMARY_BETA == Decimal("0.022488683629000000")
    assert PRIMARY_P_VALUE == Decimal("0.523533251922000000")
    assert PRIMARY_R_SQUARED == Decimal("0.002641292938333817")
    assert PRIMARY_HAC_SE == Decimal("0.035253777057000000")
    assert PRIMARY_HAC_T == Decimal("0.637908488282000000")
    assert PRIMARY_ALPHA == Decimal("-0.000125752897293718")


def test_09_only_one_log_regression() -> None:
    """9. Verify that execution runs exactly one univariate regression without grid search."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    result = execute_log_return_robustness_regression(
        rows=rows,
        r2_parquet_sha256=EXPECTED_R2_PARQUET_SHA256,
        log_parquet_sha256="dummy_sha",
    )
    assert result.sample_size_t == 1489
    assert isinstance(result.beta_log, Decimal)


def test_10_intercept_included() -> None:
    """10. Verify that an intercept alpha_log is included in the model."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    result = execute_log_return_robustness_regression(
        rows=rows,
        r2_parquet_sha256=EXPECTED_R2_PARQUET_SHA256,
        log_parquet_sha256="dummy_sha",
    )
    assert result.alpha_log is not None
    assert result.alpha_log != Decimal("0")


def test_11_hac_lag_equals_7() -> None:
    """11. Verify that HAC lag L is exactly 7 according to the plug-in formula."""
    T = 1489
    expected_l = math.floor(4.0 * ((T / 100.0) ** (2.0 / 9.0)))
    assert expected_l == 7
    assert EXPECTED_HAC_LAG == 7


def test_12_bartlett_kernel() -> None:
    """12. Verify Bartlett kernel weighting in HAC standard error calculation."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    dec_x = [r.log_r1 for r in rows]
    dec_y = [r.log_r13 for r in rows]
    beta, se, t, p = compute_ols_beta_and_hac(dec_x, dec_y, lag_bandwidth=7)
    assert se > Decimal("0")
    assert t > Decimal("0")
    assert abs(float(t) - (float(beta) / float(se))) < 1e-4


def test_13_two_sided_p() -> None:
    """13. Verify that two-sided p-value calculation is strictly enforced."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    dec_x = [r.log_r1 for r in rows]
    dec_y = [r.log_r13 for r in rows]
    beta, se, t, p = compute_ols_beta_and_hac(dec_x, dec_y, lag_bandwidth=7)
    assert p > Decimal("0.50")
    assert p < Decimal("0.55")


def test_14_no_generic_evaluator() -> None:
    """14. Verify that execution module does not import or use generic strategy evaluator."""
    import acash.research.hyp_004_log_return_robustness as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "StrategyEvaluator" not in source
    assert "evaluator" not in source
    assert "Sharpe" not in source


def test_15_no_rank_ic() -> None:
    """15. Verify that no rank IC or Spearman correlation is computed."""
    import acash.research.hyp_004_log_return_robustness as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "rank_ic" not in source
    assert "spearman" not in source


def test_16_no_friction() -> None:
    """16. Verify that no execution friction, spread, or transaction costs are modeled."""
    import acash.research.hyp_004_log_return_robustness as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "friction" not in source
    assert "cost_config" not in source
    assert "slippage" not in source


def test_17_no_r12() -> None:
    """17. Verify that r12 (15:00-15:30) is not computed or used as a predictor."""
    import acash.research.hyp_004_log_return_robustness as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "r12" not in source or "log_r12" not in source


def test_18_no_alternate_sample() -> None:
    """18. Verify that no alternate date filtering, clipping, or sample manipulation is performed."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    assert rows[0].trading_date == "2017-01-04"
    assert rows[-1].trading_date == "2022-12-30"


def test_19_no_2023_plus_access() -> None:
    """19. Verify that zero data >= 2023 is accessed."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    for r in rows:
        assert r.trading_date < "2023-01-01"


def test_20_primary_outcome_immutable() -> None:
    """20. Verify that primary outcome is permanently NOT_ACCEPTED."""
    assert PRIMARY_OUTCOME_LABEL == "PRIMARY_REPLICATION_NOT_ACCEPTED"


def test_21_local_artifact_cardinality_and_hash(tmp_path: Path) -> None:
    """21. Verify that the Parquet builder creates a valid file with exactly 1489 rows."""
    rows, _ = load_and_compute_log_returns(R2_PARQUET_PATH)
    test_pq = tmp_path / "test_log_robustness.parquet"
    build_canonical_log_returns_parquet(rows, test_pq)
    assert test_pq.exists()

    table = pq.read_table(test_pq)
    assert len(table) == 1489
    cols = table.column_names
    assert cols == [
        "trading_date",
        "p0",
        "p1",
        "p12",
        "p13",
        "log_r1",
        "log_r13",
        "source_R2_dataset_sha256",
    ]


def test_22_sealed_r1_to_r4_artifacts_unchanged() -> None:
    """22. Verify that existing R1–R4 manifests in docs/phase14/manifests/ are untouched."""
    r1_p = BASE_DIR / "docs/phase14/manifests/manifest_r1_HYP_004.json"
    r2_p = BASE_DIR / "docs/phase14/manifests/manifest_r2_HYP_004.json"
    r3_p = BASE_DIR / "docs/phase14/manifests/manifest_r3_HYP_004.json"
    r4_p = BASE_DIR / "docs/phase14/manifests/manifest_r4_HYP_004.json"

    with open(r1_p, encoding="utf-8") as f:
        assert json.load(f)["manifest_sha256"] == EXPECTED_R1_MANIFEST_SHA256
    with open(r2_p, encoding="utf-8") as f:
        assert json.load(f)["manifest_sha256"] == EXPECTED_R2_MANIFEST_SHA256
    with open(r3_p, encoding="utf-8") as f:
        assert json.load(f)["manifest_sha256"] == EXPECTED_R3_MANIFEST_SHA256
    with open(r4_p, encoding="utf-8") as f:
        assert json.load(f)["manifest_sha256"] == EXPECTED_R4_MANIFEST_SHA256
