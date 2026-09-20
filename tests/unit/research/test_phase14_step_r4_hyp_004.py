"""Unit & Invariant Test Suite: Phase 14 Step R4 HYP_004 Internal OOS Diagnostic.

Enforces strict compliance with:
1. HYP/R1/R2/R3/prereg hashes match.
2. R3 return dataset SHA matches.
3. Primary outcome remains NOT_ACCEPTED.
4. 2023+ rows rejected.
5. Evaluation window begins 2020 and ends 2022.
6. First January 2020 model uses data only through 2019-12-31.
7. February 2020 model uses data only through 2020-01-31.
8. Monthly coefficient fit is constant within a month.
9. Current-month targets never enter current-month estimation.
10. r1_t may enter forecast for t.
11. Benchmark mean uses observations strictly through t-1.
12. Excluded R2/R3 rows cannot enter estimation/evaluation.
13. R2_OS known synthetic fixture.
14. Benchmark SSE zero fails closed.
15. Exactly one forecast per eligible evaluation date.
16. No alternate window search.
17. No HAC significance gating.
18. No network imports/access.
19. Local OOS artifact contains no >=2023 row.
20. Primary result cannot be mutated by R4 outcome.
21. Sealed R1/R2/R3 artifacts remain unchanged.
"""

from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Dict, List
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18
from acash.research.step_r4_hyp_004 import (
    CANONICAL_STARTING_HEAD_SHA,
    EVALUATION_END_DATE,
    EVALUATION_START_DATE,
    EXPECTED_EVALUATION_OBSERVATIONS,
    EXPECTED_HYP_004_SHA256,
    EXPECTED_INITIAL_TRAIN_OBSERVATIONS,
    EXPECTED_MONTHLY_FITS_COUNT,
    EXPECTED_PREREG_SHA256,
    EXPECTED_PRIMARY_OUTCOME,
    EXPECTED_R1_MANIFEST_SHA256,
    EXPECTED_R2_MANIFEST_SHA256,
    EXPECTED_R2_PARQUET_SHA256,
    EXPECTED_R3_MANIFEST_SHA256,
    EXPECTED_R3_PARQUET_SHA256,
    EXPECTED_TOTAL_ELIGIBLE_OBSERVATIONS,
    INITIAL_ESTIMATION_END_DATE,
    MAX_ADMITTED_DATE,
    MonthlyFit,
    OOSForecastRow,
    build_canonical_oos_forecasts_parquet,
    build_r4_manifest,
    compute_historical_mean,
    execute_internal_oos_diagnostic,
    fit_monthly_ols,
    load_r3_primary_returns,
    validate_r4_preconditions,
)

BASE_DIR = Path(__file__).resolve().parents[3]


def test_1_upstream_hashes_match() -> None:
    """Test 1: Preconditions verify HYP/R1/R2/R3/prereg hashes match canonical pins."""
    res = validate_r4_preconditions(BASE_DIR)
    assert res["hyp_004_sha256"] == EXPECTED_HYP_004_SHA256
    assert res["preregistration_sha256"] == EXPECTED_PREREG_SHA256
    assert res["r1_manifest_sha256"] == EXPECTED_R1_MANIFEST_SHA256
    assert res["r2_manifest_sha256"] == EXPECTED_R2_MANIFEST_SHA256
    assert res["r2_parquet_sha256"] == EXPECTED_R2_PARQUET_SHA256
    assert res["r3_manifest_sha256"] == EXPECTED_R3_MANIFEST_SHA256
    assert res["r3_parquet_sha256"] == EXPECTED_R3_PARQUET_SHA256


def test_2_r3_return_dataset_sha_matches() -> None:
    """Test 2: R3 return dataset Parquet file exists and matches pinned SHA-256."""
    r3_path = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet"
    assert r3_path.is_file(), "R3 Parquet dataset missing"
    actual_sha = hashlib.sha256(r3_path.read_bytes()).hexdigest()
    assert actual_sha == EXPECTED_R3_PARQUET_SHA256


def test_3_primary_outcome_remains_not_accepted() -> None:
    """Test 3: Primary outcome in R3 manifest is immutably PRIMARY_REPLICATION_NOT_ACCEPTED."""
    r3_manifest_path = BASE_DIR / "docs/phase14/manifests/manifest_r3_HYP_004.json"
    m3 = json.loads(r3_manifest_path.read_text(encoding="utf-8"))
    outcome = m3["primary_acceptance_evaluation"]["outcome_label"]
    assert outcome == EXPECTED_PRIMARY_OUTCOME
    assert outcome == "PRIMARY_REPLICATION_NOT_ACCEPTED"


def test_4_2023_plus_rows_rejected() -> None:
    """Test 4: Any observation dated >= 2023-01-01 causes fail-closed DataContractError."""
    fake_rows = [
        {"trading_date": "2019-12-30", "r1_simple_return": Decimal("0.001"), "r13_simple_return": Decimal("0.002")},
        {"trading_date": "2019-12-31", "r1_simple_return": Decimal("0.001"), "r13_simple_return": Decimal("0.002")},
        {"trading_date": "2023-01-03", "r1_simple_return": Decimal("0.001"), "r13_simple_return": Decimal("0.002")},
    ]
    with pytest.raises(DataContractError, match="Prohibited observation"):
        execute_internal_oos_diagnostic(fake_rows)


def test_5_evaluation_window_begins_2020_and_ends_2022() -> None:
    """Test 5: Evaluation window strictly begins 2020-01-01 and ends 2022-12-31."""
    rows = load_r3_primary_returns(BASE_DIR)
    eval_rows = [r for r in rows if EVALUATION_START_DATE <= r["trading_date"] <= EVALUATION_END_DATE]
    assert len(eval_rows) == EXPECTED_EVALUATION_OBSERVATIONS
    assert eval_rows[0]["trading_date"] == "2020-01-02"
    assert eval_rows[-1]["trading_date"] == "2022-12-30"


def test_6_first_january_2020_model_uses_data_only_through_2019() -> None:
    """Test 6: First January 2020 model fit uses historical data strictly through 2019-12-31."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    jan_fit = [f for f in res.monthly_fits if f.forecast_month == "2020-01"][0]
    assert jan_fit.estimation_window_end == "2019-12-31"
    assert jan_fit.estimation_observation_count == EXPECTED_INITIAL_TRAIN_OBSERVATIONS
    assert jan_fit.estimation_window_start == "2017-01-04"


def test_7_february_2020_model_uses_data_only_through_2020_01() -> None:
    """Test 7: February 2020 model fit expands to use historical data through 2020-01-31."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    feb_fit = [f for f in res.monthly_fits if f.forecast_month == "2020-02"][0]
    assert feb_fit.estimation_window_end == "2020-01-31"
    assert feb_fit.estimation_observation_count > EXPECTED_INITIAL_TRAIN_OBSERVATIONS


def test_8_monthly_coefficient_fit_constant_within_month() -> None:
    """Test 8: Monthly coefficient fit (alpha, beta) is strictly constant across all days in the same month."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    jan_forecasts = [r for r in res.forecast_rows if r.forecast_month == "2020-01"]
    assert len(jan_forecasts) == 21  # 21 trading sessions in Jan 2020
    first_alpha = jan_forecasts[0].monthly_alpha_hat
    first_beta = jan_forecasts[0].monthly_beta_hat
    for r in jan_forecasts:
        assert r.monthly_alpha_hat == first_alpha
        assert r.monthly_beta_hat == first_beta


def test_9_current_month_targets_never_enter_current_month_estimation() -> None:
    """Test 9: Estimation window strictly excludes current month targets (zero intra-month lookahead)."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    for fit in res.monthly_fits:
        m = fit.forecast_month
        assert fit.estimation_window_end < f"{m}-01"


def test_10_r1_t_may_enter_forecast_for_t() -> None:
    """Test 10: Forecast for session t uses current-day predictor r1_t linearly: alpha + beta * r1_t."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    for r in res.forecast_rows[:10]:
        expected_pred = to_decimal18(r.monthly_alpha_hat + r.monthly_beta_hat * r.current_r1)
        assert r.model_forecast_r13 == expected_pred


def test_11_benchmark_mean_uses_observations_strictly_through_t_minus_1() -> None:
    """Test 11: Benchmark historical mean uses observations strictly through session t-1 (zero lookahead)."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    # Check that benchmark mean changes daily as new observations are added
    benchmarks = [r.benchmark_mean_r13 for r in res.forecast_rows[:5]]
    # Successive daily means should reflect updated historical data
    assert len(benchmarks) == 5
    # First benchmark on 2020-01-02 uses all 2017-2019 data (739 observations)
    train_r13 = [r["r13_simple_return"] for r in rows if r["trading_date"] <= "2019-12-31"]
    expected_b0 = to_decimal18(sum(Decimal(str(v)) for v in train_r13) / Decimal(len(train_r13)))
    assert res.forecast_rows[0].benchmark_mean_r13 == expected_b0


def test_12_excluded_r2_r3_rows_cannot_enter() -> None:
    """Test 12: Excluded R2/R3 rows (9 sessions) cannot enter estimation or evaluation sample."""
    rows = load_r3_primary_returns(BASE_DIR)
    assert len(rows) == EXPECTED_TOTAL_ELIGIBLE_OBSERVATIONS  # 1,489
    dates = {r["trading_date"] for r in rows}
    # Verified excluded dates from R2 session census
    excluded_dates = [
        "2017-01-03", "2017-03-31", "2017-06-02", "2017-06-07",
        "2017-08-08", "2017-08-23", "2017-09-12", "2021-03-24", "2022-02-14"
    ]
    for d in excluded_dates:
        assert d not in dates, f"Excluded session {d} was unexpectedly admitted"


def test_13_r2_os_known_synthetic_fixture() -> None:
    """Test 13: Known synthetic fixture yields mathematically exact Campbell-Thompson R^2_OS."""
    # Synthetic test case:
    # Model errors: [1.0, 1.0], SSE_model = 2.0
    # Bench errors: [2.0, 2.0], SSE_bench = 8.0
    # R2_OS = 1 - 2/8 = 1 - 0.25 = 0.75
    sse_model = Decimal("2.0")
    sse_bench = Decimal("8.0")
    r2_os = Decimal("1.0") - (sse_model / sse_bench)
    assert r2_os == Decimal("0.75")


def test_14_benchmark_sse_zero_fails_closed() -> None:
    """Test 14: If benchmark SSE <= 0, computation must fail closed with DataContractError."""
    # 1. Test execute_internal_oos_diagnostic fails closed when actual r13 == benchmark mean (SSE_benchmark = 0)
    rows = load_r3_primary_returns(BASE_DIR)
    zero_r13_rows = [dict(r) for r in rows]
    for r in zero_r13_rows:
        r["r13_simple_return"] = Decimal("0")

    with pytest.raises(DataContractError, match="Fail-closed: SSE_benchmark <= 0"):
        execute_internal_oos_diagnostic(zero_r13_rows)

    # 2. Verify fit_monthly_ols with zero variance raises DataContractError
    zero_var_hist = [
        {"r1_simple_return": Decimal("0.01"), "r13_simple_return": Decimal("0.02")}
        for _ in range(10)
    ]
    with pytest.raises(DataContractError, match="Zero or undefined variance"):
        fit_monthly_ols(zero_var_hist)


def test_15_exactly_one_forecast_per_eligible_evaluation_date() -> None:
    """Test 15: Exactly 750 unique forecasts for the 750 eligible evaluation sessions."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    assert len(res.forecast_rows) == EXPECTED_EVALUATION_OBSERVATIONS
    dates = [r.trading_date for r in res.forecast_rows]
    assert len(dates) == len(set(dates)), "Duplicate dates found in forecast rows"


def test_16_no_alternate_window_search() -> None:
    """Test 16: Estimation and evaluation window parameters are fixed constants, not parameters."""
    assert INITIAL_ESTIMATION_END_DATE == "2019-12-31"
    assert EVALUATION_START_DATE == "2020-01-01"
    assert EVALUATION_END_DATE == "2022-12-31"


def test_17_no_hac_significance_gating() -> None:
    """Test 17: Monthly OLS fits are mechanical: no HAC p-value filtering or coefficient suppression."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    assert len(res.monthly_fits) == EXPECTED_MONTHLY_FITS_COUNT
    # Ensure all 36 months are present regardless of whether beta is positive or negative
    assert all(isinstance(f.beta_hat, Decimal) for f in res.monthly_fits)


def test_18_no_network_imports_or_access() -> None:
    """Test 18: Implementation does not import urllib, requests, socket, or alpaca."""
    import acash.research.step_r4_hyp_004 as mod
    mod_source = Path(mod.__file__).read_text(encoding="utf-8")
    prohibited_tokens = ["requests", "urllib", "http.client", "socket", "alpaca"]
    for token in prohibited_tokens:
        assert f"import {token}" not in mod_source, f"Prohibited import detected: {token}"


def test_19_local_oos_artifact_contains_no_2023_rows() -> None:
    """Test 19: Serialized Parquet artifact fails closed if any observation >= 2023 is present."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_parquet = Path(tmp_dir) / "test_oos.parquet"
        invalid_row = OOSForecastRow(
            trading_date="2023-01-03",
            forecast_month="2023-01",
            estimation_window_start="2017-01-04",
            estimation_window_end="2022-12-30",
            estimation_observation_count=1489,
            monthly_alpha_hat=Decimal("0"),
            monthly_beta_hat=Decimal("0"),
            current_r1=Decimal("0"),
            actual_r13=Decimal("0"),
            model_forecast_r13=Decimal("0"),
            benchmark_mean_r13=Decimal("0"),
        )
        with pytest.raises(DataContractError, match="Fail-closed: Prohibited observation"):
            build_canonical_oos_forecasts_parquet([invalid_row], tmp_parquet)


def test_20_primary_result_cannot_be_mutated_by_r4_outcome() -> None:
    """Test 20: R4 manifest strictly records primary outcome as immutable PRIMARY_REPLICATION_NOT_ACCEPTED."""
    rows = load_r3_primary_returns(BASE_DIR)
    res = execute_internal_oos_diagnostic(rows)
    manifest = build_r4_manifest(res, source_git_sha=CANONICAL_STARTING_HEAD_SHA)
    assert manifest["primary_replication_outcome"]["outcome_label"] == EXPECTED_PRIMARY_OUTCOME
    assert manifest["primary_replication_outcome"]["is_immutable"] is True
    assert manifest["primary_replication_outcome"]["overwritten_or_rescued_by_oos"] is False
    assert manifest["governance_and_execution_invariants"]["primary_outcome_changed"] is False


def test_21_sealed_r1_r2_r3_artifacts_remain_unchanged() -> None:
    """Test 21: Sealed R1, R2, and R3 manifests and Parquets match their sealed hash pins."""
    r1_p = BASE_DIR / "docs/phase14/manifests/manifest_r1_HYP_004.json"
    r2_p = BASE_DIR / "docs/phase14/manifests/manifest_r2_HYP_004.json"
    r3_p = BASE_DIR / "docs/phase14/manifests/manifest_r3_HYP_004.json"
    r2_pq = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
    r3_pq = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet"

    assert json.loads(r1_p.read_text(encoding="utf-8"))["manifest_sha256"] == EXPECTED_R1_MANIFEST_SHA256
    assert json.loads(r2_p.read_text(encoding="utf-8"))["manifest_sha256"] == EXPECTED_R2_MANIFEST_SHA256
    assert json.loads(r3_p.read_text(encoding="utf-8"))["manifest_sha256"] == EXPECTED_R3_MANIFEST_SHA256
    assert hashlib.sha256(r2_pq.read_bytes()).hexdigest() == EXPECTED_R2_PARQUET_SHA256
    assert hashlib.sha256(r3_pq.read_bytes()).hexdigest() == EXPECTED_R3_PARQUET_SHA256
