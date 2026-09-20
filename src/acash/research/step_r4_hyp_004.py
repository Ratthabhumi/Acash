"""Phase 14 Step R4: HYP_004 / MEC-0014A Internal Recursive OOS Diagnostic.

Executes the single authorized preregistered internal out-of-sample (OOS)
predictive diagnostic of Gao et al. (2018) baseline predictive relation on SPY.

PREREGISTERED SCHEME:
- Initial estimation window: 2017-01-01 through 2019-12-31 (train sample)
- Forecast evaluation window: 2020-01-01 through 2022-12-31 (eval sample)
- Method: Recursive / expanding estimation window
- Re-estimation frequency: Monthly expanding (frozen alpha_M, beta_M per calendar month M)
- Benchmark: Historical mean of r13 available strictly through session t-1 (daily expanding)
- Metric: Campbell-Thompson (2008) / Gao-style out-of-sample R^2_OS:
      R^2_OS = 1 - SSE_model / SSE_benchmark

ROLE & GOVERNANCE:
- SECONDARY DIAGNOSTIC ONLY.
- Possesses ZERO authority to alter, rescue, or relabel PRIMARY_REPLICATION_NOT_ACCEPTED.
- No binary pass/fail labeling on OOS.
- 2023-2026 external holdout remains strictly SEALED & UNREAD.
- Capital = $0.00, NO_REAL_ORDERS = true, Paper/Live locked.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.features.engine import to_decimal18
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification

# Pinned Canonical Upstream Digests
CANONICAL_STARTING_HEAD_SHA: str = "bb2309f5ed570089bfd4c613727f92b3915cd079"
EXPECTED_HYP_004_SHA256: str = "fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d"
EXPECTED_PREREG_SHA256: str = "1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce"
EXPECTED_R1_MANIFEST_SHA256: str = "eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b"
EXPECTED_R2_MANIFEST_SHA256: str = "25b5ae6c4769064459709bb09bbc759e02f7b340c4d4e94b4ff9442e3082ef71"
EXPECTED_R2_PARQUET_SHA256: str = "096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776"
EXPECTED_R3_MANIFEST_SHA256: str = "56d4f79c1e563a81c0b601f695023a5da54cac58e5b9a19a0be9108b3ca4ef40"
EXPECTED_R3_PARQUET_SHA256: str = "2b37cba80a845102be6a322af7ff12ff34ecd7a7947e10cf663a3bacdd93d8b9"
EXPECTED_PRIMARY_OUTCOME: str = "PRIMARY_REPLICATION_NOT_ACCEPTED"

# Frozen Sample Boundaries
INITIAL_ESTIMATION_END_DATE: str = "2019-12-31"
EVALUATION_START_DATE: str = "2020-01-01"
EVALUATION_END_DATE: str = "2022-12-31"
MAX_ADMITTED_DATE: str = "2022-12-31"

EXPECTED_TOTAL_ELIGIBLE_OBSERVATIONS: int = 1489
EXPECTED_INITIAL_TRAIN_OBSERVATIONS: int = 739
EXPECTED_EVALUATION_OBSERVATIONS: int = 750
EXPECTED_MONTHLY_FITS_COUNT: int = 36


@dataclass(frozen=True)
class MonthlyFit:
    """Frozen monthly OLS regression parameters for forecast month M."""
    forecast_month: str
    estimation_window_start: str
    estimation_window_end: str
    estimation_observation_count: int
    alpha_hat: Decimal
    beta_hat: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_month": self.forecast_month,
            "estimation_window_start": self.estimation_window_start,
            "estimation_window_end": self.estimation_window_end,
            "estimation_observation_count": self.estimation_observation_count,
            "alpha_hat": str(self.alpha_hat),
            "beta_hat": str(self.beta_hat),
        }


@dataclass(frozen=True)
class OOSForecastRow:
    """Point-in-time single evaluation session forecast and benchmark record."""
    trading_date: str
    forecast_month: str
    estimation_window_start: str
    estimation_window_end: str
    estimation_observation_count: int
    monthly_alpha_hat: Decimal
    monthly_beta_hat: Decimal
    current_r1: Decimal
    actual_r13: Decimal
    model_forecast_r13: Decimal
    benchmark_mean_r13: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trading_date": self.trading_date,
            "forecast_month": self.forecast_month,
            "estimation_window_start": self.estimation_window_start,
            "estimation_window_end": self.estimation_window_end,
            "estimation_observation_count": self.estimation_observation_count,
            "monthly_alpha_hat": str(self.monthly_alpha_hat),
            "monthly_beta_hat": str(self.monthly_beta_hat),
            "current_r1": str(self.current_r1),
            "actual_r13": str(self.actual_r13),
            "model_forecast_r13": str(self.model_forecast_r13),
            "benchmark_mean_r13": str(self.benchmark_mean_r13),
        }


@dataclass(frozen=True)
class InternalOOSResult:
    """Comprehensive empirical result of Phase 14 Step R4 Internal OOS Diagnostic."""
    evaluation_observation_count: int
    evaluation_counts_by_year: Dict[int, int]
    monthly_fit_count: int
    estimation_sample_min: int
    estimation_sample_max: int
    sse_model: Decimal
    sse_benchmark: Decimal
    rmse_model: Decimal
    rmse_benchmark: Decimal
    r2_os: Decimal
    mean_forecast: Decimal
    mean_actual_r13: Decimal
    source_r3_parquet_sha256: str
    derived_r4_forecast_parquet_sha256: str
    forecast_rows: List[OOSForecastRow]
    monthly_fits: List[MonthlyFit]
    primary_outcome_immutable: str = EXPECTED_PRIMARY_OUTCOME
    secondary_diagnostic_classification: str = "SECONDARY_PREREGISTERED_DIAGNOSTIC"


# PyArrow Schema for R4 Internal OOS Forecasts Parquet
R4_INTERNAL_OOS_FORECASTS_ARROW_SCHEMA = pa.schema([
    ("trading_date", pa.string()),
    ("forecast_month", pa.string()),
    ("estimation_window_start", pa.string()),
    ("estimation_window_end", pa.string()),
    ("estimation_observation_count", pa.int32()),
    ("monthly_alpha_hat", pa.decimal128(38, 18)),
    ("monthly_beta_hat", pa.decimal128(38, 18)),
    ("current_r1", pa.decimal128(38, 18)),
    ("actual_r13", pa.decimal128(38, 18)),
    ("model_forecast_r13", pa.decimal128(38, 18)),
    ("benchmark_mean_r13", pa.decimal128(38, 18)),
])


def validate_r4_preconditions(repo_root: Optional[Path] = None) -> Dict[str, str]:
    """Verify all upstream governance artifacts, hashes, and census before Step R4 execution."""
    root = repo_root or Path(".")

    # 1. Sealed HYP_004 Specification
    hyp_path = root / "docs/phase14/hypotheses/HYP_004.json"
    if not hyp_path.exists():
        raise DataContractError(f"Precondition failed: Sealed HYP_004 not found at {hyp_path}")
    hyp_data = json.loads(hyp_path.read_text(encoding="utf-8"))
    spec = HypothesisSpecification.model_validate(hyp_data)
    computed_hyp_sha = calculate_hypothesis_spec_sha256(spec)
    if computed_hyp_sha != EXPECTED_HYP_004_SHA256:
        raise DataContractError(
            f"Precondition failed: HYP_004 SHA-256 mismatch: {computed_hyp_sha} != {EXPECTED_HYP_004_SHA256}"
        )

    # 2. Frozen Pre-registration
    prereg_path = root / "docs/research/MEC-0014A-statistical-preregistration-draft.md"
    if not prereg_path.exists():
        raise DataContractError(f"Precondition failed: Pre-registration not found at {prereg_path}")
    computed_prereg_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    if computed_prereg_sha != EXPECTED_PREREG_SHA256:
        raise DataContractError(
            f"Precondition failed: Pre-registration SHA-256 mismatch: {computed_prereg_sha} != {EXPECTED_PREREG_SHA256}"
        )

    # 3. Tracked R1 Manifest
    r1_path = root / "docs/phase14/manifests/manifest_r1_HYP_004.json"
    if not r1_path.exists():
        raise DataContractError(f"Precondition failed: R1 Manifest not found at {r1_path}")
    r1_data = json.loads(r1_path.read_text(encoding="utf-8"))
    computed_r1_sha = r1_data.get("manifest_sha256")
    if computed_r1_sha != EXPECTED_R1_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R1 Manifest SHA-256 mismatch: {computed_r1_sha} != {EXPECTED_R1_MANIFEST_SHA256}"
        )

    # 4. Tracked R2 Manifest
    r2_path = root / "docs/phase14/manifests/manifest_r2_HYP_004.json"
    if not r2_path.exists():
        raise DataContractError(f"Precondition failed: R2 Manifest not found at {r2_path}")
    r2_data = json.loads(r2_path.read_text(encoding="utf-8"))
    computed_r2_sha = r2_data.get("manifest_sha256")
    if computed_r2_sha != EXPECTED_R2_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R2 Manifest SHA-256 mismatch: {computed_r2_sha} != {EXPECTED_R2_MANIFEST_SHA256}"
        )

    # 5. Local R2 Parquet Dataset Hash Pin
    r2_parquet_path = root / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
    if not r2_parquet_path.exists():
        raise DataContractError(f"Precondition failed: Local R2 Parquet not found at {r2_parquet_path}")
    computed_r2_parquet_sha = hashlib.sha256(r2_parquet_path.read_bytes()).hexdigest()
    if computed_r2_parquet_sha != EXPECTED_R2_PARQUET_SHA256:
        raise DataContractError(
            f"Precondition failed: R2 Parquet SHA-256 mismatch: {computed_r2_parquet_sha} != {EXPECTED_R2_PARQUET_SHA256}"
        )

    # 6. Tracked R3 Manifest & Immutable Primary Outcome
    r3_path = root / "docs/phase14/manifests/manifest_r3_HYP_004.json"
    if not r3_path.exists():
        raise DataContractError(f"Precondition failed: R3 Manifest not found at {r3_path}")
    r3_data = json.loads(r3_path.read_text(encoding="utf-8"))
    computed_r3_sha = r3_data.get("manifest_sha256")
    if computed_r3_sha != EXPECTED_R3_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R3 Manifest SHA-256 mismatch: {computed_r3_sha} != {EXPECTED_R3_MANIFEST_SHA256}"
        )
    primary_eval = r3_data.get("primary_acceptance_evaluation", {})
    actual_primary_outcome = primary_eval.get("outcome_label")
    if actual_primary_outcome != EXPECTED_PRIMARY_OUTCOME:
        raise DataContractError(
            f"Precondition failed: Primary outcome must be {EXPECTED_PRIMARY_OUTCOME}, got {actual_primary_outcome}"
        )

    # 7. Local R3 Derived Returns Dataset Hash Pin
    r3_parquet_path = root / "data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet"
    if not r3_parquet_path.exists():
        raise DataContractError(f"Precondition failed: Local R3 Parquet not found at {r3_parquet_path}")
    computed_r3_parquet_sha = hashlib.sha256(r3_parquet_path.read_bytes()).hexdigest()
    if computed_r3_parquet_sha != EXPECTED_R3_PARQUET_SHA256:
        raise DataContractError(
            f"Precondition failed: R3 Parquet SHA-256 mismatch: {computed_r3_parquet_sha} != {EXPECTED_R3_PARQUET_SHA256}"
        )

    return {
        "hyp_004_sha256": computed_hyp_sha,
        "preregistration_sha256": computed_prereg_sha,
        "r1_manifest_sha256": computed_r1_sha,
        "r2_manifest_sha256": computed_r2_sha,
        "r2_parquet_sha256": computed_r2_parquet_sha,
        "r3_manifest_sha256": computed_r3_sha,
        "r3_parquet_sha256": computed_r3_parquet_sha,
        "primary_outcome": actual_primary_outcome,
    }


def load_r3_primary_returns(repo_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load and validate the sealed R3 primary returns dataset."""
    root = repo_root or Path(".")
    parquet_path = root / "data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet"
    if not parquet_path.exists():
        raise DataContractError(f"R3 primary returns dataset missing at {parquet_path}")

    file_bytes = parquet_path.read_bytes()
    computed_sha = hashlib.sha256(file_bytes).hexdigest()
    if computed_sha != EXPECTED_R3_PARQUET_SHA256:
        raise DataContractError(
            f"R3 primary returns dataset SHA mismatch: {computed_sha} != {EXPECTED_R3_PARQUET_SHA256}"
        )

    table = pq.read_table(parquet_path)
    if table.num_rows != EXPECTED_TOTAL_ELIGIBLE_OBSERVATIONS:
        raise DataContractError(
            f"Unexpected observation count in R3 dataset: {table.num_rows} != {EXPECTED_TOTAL_ELIGIBLE_OBSERVATIONS}"
        )

    rows: List[Dict[str, Any]] = []
    pydict = table.to_pydict()
    for i in range(table.num_rows):
        trading_date = pydict["trading_date"][i]
        if trading_date > MAX_ADMITTED_DATE:
            raise DataContractError(
                f"Prohibited holdout session detected: {trading_date} > {MAX_ADMITTED_DATE}"
            )
        row = {
            "trading_date": trading_date,
            "calendar_session_ordinal": pydict["calendar_session_ordinal"][i],
            "r1_simple_return": pydict["r1_simple_return"][i],
            "r13_simple_return": pydict["r13_simple_return"][i],
        }
        rows.append(row)

    # Strictly enforce ascending chronological order
    rows.sort(key=lambda r: r["trading_date"])
    return rows


def fit_monthly_ols(history_rows: Sequence[Dict[str, Any]]) -> Tuple[Decimal, Decimal]:
    """Fit ordinary least squares with intercept on historical observations.

    Model: r13 = alpha + beta * r1
    """
    n = len(history_rows)
    if n < 3:
        raise DataContractError(f"Insufficient historical observations for OLS fit: {n} < 3")

    x_vals = np.array([float(r["r1_simple_return"]) for r in history_rows], dtype=np.float64)
    y_vals = np.array([float(r["r13_simple_return"]) for r in history_rows], dtype=np.float64)

    x_bar = float(np.mean(x_vals))
    y_bar = float(np.mean(y_vals))

    x_dm = x_vals - x_bar
    y_dm = y_vals - y_bar

    var_x = float(np.sum(x_dm ** 2))
    if np.all(x_vals == x_vals[0]) or var_x <= 0.0 or math.isnan(var_x):
        raise DataContractError(f"Zero or undefined variance in predictor r1: var_x={var_x}")

    cov_xy = float(np.sum(x_dm * y_dm))
    beta_hat = cov_xy / var_x
    alpha_hat = y_bar - beta_hat * x_bar

    dec_alpha = to_decimal18(alpha_hat)
    dec_beta = to_decimal18(beta_hat)

    if dec_alpha is None or dec_beta is None:
        raise DataContractError("Failed to quantize OLS coefficients to Decimal18")

    return dec_alpha, dec_beta


def compute_historical_mean(history_rows: Sequence[Dict[str, Any]]) -> Decimal:
    """Compute expanding historical mean benchmark of r13 through session t-1."""
    n = len(history_rows)
    if n == 0:
        raise DataContractError("Cannot compute historical mean of empty sequence")

    # Use exact Decimal summation to prevent numerical drift
    total = sum(Decimal(str(r["r13_simple_return"])) for r in history_rows)
    mean_val = total / Decimal(n)
    dec_mean = to_decimal18(mean_val)
    if dec_mean is None:
        raise DataContractError("Failed to quantize historical mean benchmark to Decimal18")
    return dec_mean


def execute_internal_oos_diagnostic(
    rows: Sequence[Dict[str, Any]],
    source_r3_parquet_sha256: str = EXPECTED_R3_PARQUET_SHA256,
) -> InternalOOSResult:
    """Execute monthly expanding re-estimation and daily out-of-sample forecast evaluation."""
    sorted_rows = sorted(rows, key=lambda r: r["trading_date"])

    # Fail closed on any observation >= 2023
    for r in sorted_rows:
        if r["trading_date"] > MAX_ADMITTED_DATE:
            raise DataContractError(
                f"Fail-closed: Prohibited observation {r['trading_date']} > {MAX_ADMITTED_DATE}"
            )

    train_rows = [r for r in sorted_rows if r["trading_date"] <= INITIAL_ESTIMATION_END_DATE]
    eval_rows = [
        r for r in sorted_rows
        if EVALUATION_START_DATE <= r["trading_date"] <= EVALUATION_END_DATE
    ]

    if len(train_rows) != EXPECTED_INITIAL_TRAIN_OBSERVATIONS:
        raise DataContractError(
            f"Initial training observation count mismatch: {len(train_rows)} != {EXPECTED_INITIAL_TRAIN_OBSERVATIONS}"
        )
    if len(eval_rows) != EXPECTED_EVALUATION_OBSERVATIONS:
        raise DataContractError(
            f"Evaluation observation count mismatch: {len(eval_rows)} != {EXPECTED_EVALUATION_OBSERVATIONS}"
        )

    # Identify all distinct calendar months in evaluation sample
    eval_months = sorted(list({r["trading_date"][:7] for r in eval_rows}))
    if len(eval_months) != EXPECTED_MONTHLY_FITS_COUNT:
        raise DataContractError(
            f"Evaluation months count mismatch: {len(eval_months)} != {EXPECTED_MONTHLY_FITS_COUNT}"
        )

    # 1. Fit monthly expanding OLS models
    monthly_fits: Dict[str, MonthlyFit] = {}
    for month_str in eval_months:
        first_day_of_month = f"{month_str}-01"
        hist_for_month = [r for r in sorted_rows if r["trading_date"] < first_day_of_month]
        if not hist_for_month:
            raise DataContractError(f"No historical observations available for month {month_str}")

        alpha_hat, beta_hat = fit_monthly_ols(hist_for_month)
        fit = MonthlyFit(
            forecast_month=month_str,
            estimation_window_start=hist_for_month[0]["trading_date"],
            estimation_window_end=hist_for_month[-1]["trading_date"],
            estimation_observation_count=len(hist_for_month),
            alpha_hat=alpha_hat,
            beta_hat=beta_hat,
        )
        monthly_fits[month_str] = fit

    # 2. Produce point-in-time daily forecasts and benchmarks
    forecast_rows: List[OOSForecastRow] = []
    eval_counts_by_year: Dict[int, int] = {2020: 0, 2021: 0, 2022: 0}

    for row in eval_rows:
        t_date = row["trading_date"]
        year = int(t_date[:4])
        eval_counts_by_year[year] = eval_counts_by_year.get(year, 0) + 1

        month_str = t_date[:7]
        fit = monthly_fits[month_str]

        # Programmatic Point-In-Time Assertions
        if not (fit.estimation_window_end < t_date):
            raise DataContractError(
                f"Lookahead violation: Estimation window end {fit.estimation_window_end} >= trading date {t_date}"
            )

        # Historical observations strictly through session t-1
        hist_t = [r for r in sorted_rows if r["trading_date"] < t_date]
        if not hist_t or hist_t[-1]["trading_date"] >= t_date:
            raise DataContractError(
                f"Benchmark lookahead violation: Last benchmark date >= trading date {t_date}"
            )

        benchmark_mean = compute_historical_mean(hist_t)

        current_r1 = to_decimal18(Decimal(str(row["r1_simple_return"])))
        actual_r13 = to_decimal18(Decimal(str(row["r13_simple_return"])))
        if current_r1 is None or actual_r13 is None:
            raise DataContractError(f"Failed to quantize returns for date {t_date}")

        # Model forecast: r13_hat_t = alpha_M + beta_M * r1_t
        model_forecast = to_decimal18(fit.alpha_hat + fit.beta_hat * current_r1)
        if model_forecast is None:
            raise DataContractError(f"Failed to compute model forecast for date {t_date}")

        forecast_rows.append(
            OOSForecastRow(
                trading_date=t_date,
                forecast_month=month_str,
                estimation_window_start=fit.estimation_window_start,
                estimation_window_end=fit.estimation_window_end,
                estimation_observation_count=fit.estimation_observation_count,
                monthly_alpha_hat=fit.alpha_hat,
                monthly_beta_hat=fit.beta_hat,
                current_r1=current_r1,
                actual_r13=actual_r13,
                model_forecast_r13=model_forecast,
                benchmark_mean_r13=benchmark_mean,
            )
        )

    # 3. Compute Out-of-Sample Metrics
    # SSE_model = sum((actual - model_forecast)^2)
    # SSE_benchmark = sum((actual - benchmark_mean)^2)
    diff_model = [r.actual_r13 - r.model_forecast_r13 for r in forecast_rows]
    diff_bench = [r.actual_r13 - r.benchmark_mean_r13 for r in forecast_rows]

    sse_model_dec: Decimal = sum((d ** 2 for d in diff_model), Decimal("0"))
    sse_bench_dec: Decimal = sum((d ** 2 for d in diff_bench), Decimal("0"))

    if sse_bench_dec <= Decimal("0"):
        raise DataContractError(f"Fail-closed: SSE_benchmark <= 0: {sse_bench_dec}")

    r2_os_dec: Decimal = Decimal("1") - (sse_model_dec / sse_bench_dec)

    t_eval = Decimal(len(forecast_rows))
    rmse_model_dec = Decimal(str(math.sqrt(float(sse_model_dec / t_eval))))
    rmse_bench_dec = Decimal(str(math.sqrt(float(sse_bench_dec / t_eval))))

    mean_forecast_dec = sum((r.model_forecast_r13 for r in forecast_rows), Decimal("0")) / t_eval
    mean_actual_dec = sum((r.actual_r13 for r in forecast_rows), Decimal("0")) / t_eval

    # Quantize metrics to Decimal18
    sse_model_q = to_decimal18(sse_model_dec) or Decimal("0")
    sse_bench_q = to_decimal18(sse_bench_dec) or Decimal("0")
    r2_os_q = to_decimal18(r2_os_dec) or Decimal("0")
    rmse_model_q = to_decimal18(rmse_model_dec) or Decimal("0")
    rmse_bench_q = to_decimal18(rmse_bench_dec) or Decimal("0")
    mean_forecast_q = to_decimal18(mean_forecast_dec) or Decimal("0")
    mean_actual_q = to_decimal18(mean_actual_dec) or Decimal("0")

    fit_counts = [f.estimation_observation_count for f in monthly_fits.values()]

    return InternalOOSResult(
        evaluation_observation_count=len(forecast_rows),
        evaluation_counts_by_year=eval_counts_by_year,
        monthly_fit_count=len(monthly_fits),
        estimation_sample_min=min(fit_counts),
        estimation_sample_max=max(fit_counts),
        sse_model=sse_model_q,
        sse_benchmark=sse_bench_q,
        rmse_model=rmse_model_q,
        rmse_benchmark=rmse_bench_q,
        r2_os=r2_os_q,
        mean_forecast=mean_forecast_q,
        mean_actual_r13=mean_actual_q,
        source_r3_parquet_sha256=source_r3_parquet_sha256,
        derived_r4_forecast_parquet_sha256="",  # Will be populated upon serialization
        forecast_rows=forecast_rows,
        monthly_fits=list(monthly_fits.values()),
        primary_outcome_immutable=EXPECTED_PRIMARY_OUTCOME,
        secondary_diagnostic_classification="SECONDARY_PREREGISTERED_DIAGNOSTIC",
    )


def build_canonical_oos_forecasts_parquet(
    forecast_rows: Sequence[OOSForecastRow],
    output_path: Path,
) -> str:
    """Serialize point-in-time forecast rows to gitignored Parquet and return SHA-256 digest."""
    sorted_rows = sorted(forecast_rows, key=lambda r: r.trading_date)

    # Fail closed if any row >= 2023
    for r in sorted_rows:
        if r.trading_date > MAX_ADMITTED_DATE:
            raise DataContractError(
                f"Fail-closed: Prohibited observation {r.trading_date} in forecast artifact"
            )

    data = {
        "trading_date": [r.trading_date for r in sorted_rows],
        "forecast_month": [r.forecast_month for r in sorted_rows],
        "estimation_window_start": [r.estimation_window_start for r in sorted_rows],
        "estimation_window_end": [r.estimation_window_end for r in sorted_rows],
        "estimation_observation_count": [r.estimation_observation_count for r in sorted_rows],
        "monthly_alpha_hat": [r.monthly_alpha_hat for r in sorted_rows],
        "monthly_beta_hat": [r.monthly_beta_hat for r in sorted_rows],
        "current_r1": [r.current_r1 for r in sorted_rows],
        "actual_r13": [r.actual_r13 for r in sorted_rows],
        "model_forecast_r13": [r.model_forecast_r13 for r in sorted_rows],
        "benchmark_mean_r13": [r.benchmark_mean_r13 for r in sorted_rows],
    }

    arrow_table = pa.Table.from_pydict(data, schema=R4_INTERNAL_OOS_FORECASTS_ARROW_SCHEMA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(arrow_table, output_path, compression="SNAPPY")

    file_bytes = output_path.read_bytes()
    return hashlib.sha256(file_bytes).hexdigest()


def build_r4_manifest(
    result: InternalOOSResult,
    source_git_sha: str,
) -> Dict[str, Any]:
    """Assemble tracked JSON manifest for Phase 14 Step R4 Internal OOS Diagnostic."""
    payload: Dict[str, Any] = {
        "manifest_type": "INTERNAL_OOS_DIAGNOSTIC_MANIFEST",
        "hypothesis_id": "HYP_004",
        "hypothesis_ordinal": 4,
        "mechanism_id": "MEC-0014A",
        "hypothesis_sha256": EXPECTED_HYP_004_SHA256,
        "r1_manifest_sha256": EXPECTED_R1_MANIFEST_SHA256,
        "r2_manifest_sha256": EXPECTED_R2_MANIFEST_SHA256,
        "r3_manifest_sha256": EXPECTED_R3_MANIFEST_SHA256,
        "preregistration_sha256": EXPECTED_PREREG_SHA256,
        "source_git_sha": source_git_sha,
        "primary_replication_outcome": {
            "outcome_label": EXPECTED_PRIMARY_OUTCOME,
            "is_immutable": True,
            "overwritten_or_rescued_by_oos": False,
        },
        "oos_diagnostic_lineage": {
            "source_r3_parquet_sha256": result.source_r3_parquet_sha256,
            "derived_r4_forecast_parquet_sha256": result.derived_r4_forecast_parquet_sha256,
            "initial_estimation_period": {
                "start": "2017-01-04",
                "end": INITIAL_ESTIMATION_END_DATE,
                "observation_count": EXPECTED_INITIAL_TRAIN_OBSERVATIONS,
            },
            "evaluation_period": {
                "start": EVALUATION_START_DATE,
                "end": EVALUATION_END_DATE,
                "observation_count": result.evaluation_observation_count,
                "observation_counts_by_year": {
                    str(yr): count for yr, count in sorted(result.evaluation_counts_by_year.items())
                },
            },
            "re_estimation_scheme": {
                "method": "MONTHLY_EXPANDING_OLS_WITH_INTERCEPT",
                "monthly_fit_count": result.monthly_fit_count,
                "estimation_sample_size_min": result.estimation_sample_min,
                "estimation_sample_size_max": result.estimation_sample_max,
                "benchmark_family": "DAILY_EXPANDING_HISTORICAL_MEAN_THROUGH_T_MINUS_1",
            },
        },
        "oos_predictive_metrics": {
            "sse_model": str(result.sse_model),
            "sse_benchmark": str(result.sse_benchmark),
            "rmse_model": str(result.rmse_model),
            "rmse_benchmark": str(result.rmse_benchmark),
            "r2_os": str(result.r2_os),
            "mean_forecast_r13": str(result.mean_forecast),
            "mean_actual_r13": str(result.mean_actual_r13),
            "diagnostic_role": "SECONDARY_PREREGISTERED_DIAGNOSTIC",
            "binary_acceptance_threshold_exists": False,
            "interpretation": (
                "R2_OS < 0 indicates that model forecast squared error exceeds the historical-mean "
                "benchmark over the frozen 2020-2022 evaluation window. In accordance with preregistration, "
                "this secondary diagnostic characterizes predictive capacity and does not alter the "
                "immutable PRIMARY_REPLICATION_NOT_ACCEPTED primary outcome."
            ),
        },
        "governance_and_execution_invariants": {
            "primary_outcome_changed": False,
            "external_holdout_accessed": False,
            "trading_authorized": False,
            "capital_authority_usd": "0.00",
            "single_model_k_equals_1": True,
            "secondary_analysis_name": "MEC_0014A_INTERNAL_OOS",
        },
        "status": "STEP_R4_INTERNAL_OOS_DIAGNOSTIC_SEALED",
        "next_required_action": "HUMAN_AUDIT_REQUIRED",
    }

    manifest_json = CanonicalConfigSerializer.to_canonical_json(payload)
    manifest_bytes = manifest_json.encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    return payload
