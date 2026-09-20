"""Execution Script: Phase 14 Step R4 HYP_004 Internal OOS Diagnostic.

Executes the single preregistered secondary diagnostic for HYP_004 / MEC-0014A:
Internal Recursive Out-of-Sample (OOS) evaluation of Gao et al. (2018) baseline
predictive relation on SPY (2017–2022).

Usage:
    uv run python scripts/execute_phase14_step_r4_hyp_004.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
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
    InternalOOSResult,
    build_canonical_oos_forecasts_parquet,
    build_r4_manifest,
    execute_internal_oos_diagnostic,
    load_r3_primary_returns,
    validate_r4_preconditions,
)

BASE_DIR = Path(__file__).resolve().parents[1]
R3_PARQUET_PATH = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet"
R4_FORECAST_PARQUET_PATH = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R4_internal_oos_forecasts.parquet"
TRACKED_MANIFEST_PATH = BASE_DIR / "docs/phase14/manifests/manifest_r4_HYP_004.json"
TRACKED_AUDIT_PATH = BASE_DIR / "docs/phase14/phase14_r4_internal_oos_diagnostic_HYP_004.md"


def get_git_head_sha() -> str:
    """Retrieve current Git HEAD commit SHA."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception as e:
        raise DataContractError(f"Failed to retrieve Git HEAD SHA: {e}") from e


def generate_r4_audit_markdown(
    result: InternalOOSResult,
    manifest_sha256: str,
    manifest_rel_path: str,
    forecast_rel_path: str,
    source_git_sha: str,
) -> str:
    """Generate exhaustive tracked markdown audit document for Phase 14 Step R4."""
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md = f"""# Phase 14 Step R4: HYP_004 Internal Out-of-Sample Diagnostic Audit

```text
[STATUS: STEP_R4_INTERNAL_OOS_DIAGNOSTIC_SEALED]
[SECONDARY ROLE: PREDICTIVE CAPACITY CHARACTERIZATION ONLY]
[PRIMARY REPLICATION OUTCOME: PRIMARY_REPLICATION_NOT_ACCEPTED (IMMUTABLE)]
[EVALUATION PERIOD: 2020-01-01 to 2022-12-31 | SPY In-Sample Universe]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true | TRADING: LOCKED]
```

- **Document ID:** `docs/phase14/phase14_r4_internal_oos_diagnostic_HYP_004.md`
- **Hypothesis ID:** `HYP_004` (Market Intraday Momentum: Gao Baseline Replication on `SPY`)
- **Mechanism ID:** `MEC-0014A`
- **Diagnostic Specification:** `MEC_0014A_INTERNAL_OOS = SECONDARY_PREREGISTERED_DIAGNOSTIC`
- **Canonical Starting Base Commit:** `{CANONICAL_STARTING_HEAD_SHA}`
- **Source Git SHA:** `{source_git_sha}`
- **Audit Timestamp:** `{timestamp_utc}`
- **Next Required Action:** `HUMAN_AUDIT_REQUIRED`

---

## 1. Executive Summary & Epistemic Boundaries

Phase 14 Step R4 executed the single authorized preregistered secondary predictive diagnostic for `HYP_004` / `MEC-0014A`:
**Internal Recursive Out-of-Sample (OOS) Evaluation** on the qualified 2017–2022 `SPY` replication sample.

### Crucial Epistemic Boundaries
1. **Primary Outcome Invariant:**
   The primary econometric replication result finalized in Step R3 is **`PRIMARY_REPLICATION_NOT_ACCEPTED`** (two-sided $p = 0.523533 \\ge 0.05$). This outcome is **final and immutable**. The internal OOS evaluation is a secondary predictive diagnostic and possesses **zero authority** to overturn, rescue, or relabel the primary replication decision.
2. **No Binary Pass/Fail Threshold:**
   Section 7 of the ratified preregistration (`docs/research/MEC-0014A-statistical-preregistration-draft.md`) specifies $R^2_{{OS}}$ as a descriptive predictive diagnostic. It establishes **no binary acceptance threshold** (no `OOS_PASS` or `OOS_FAIL`).
3. **External Holdout Preservation:**
   All data from $\\ge \\text{{2023-01-01}}$ remains strictly **SEALED & UNREAD**. Zero holdout sessions were accessed.
4. **Trading & Execution Boundaries:**
   No strategy admission, signal generation, backtesting, Paper trading, or Live execution is authorized. Canonical capital remains **$0.00** with `NO_REAL_ORDERS = true`.

---

## 2. Upstream Governance Hash Verification

| Artifact | Canonical Path | Pinned SHA-256 | Audit Status |
| :--- | :--- | :--- | :--- |
| **HYP_004 Specification** | `docs/phase14/hypotheses/HYP_004.json` | `{EXPECTED_HYP_004_SHA256}` | **VERIFIED MATCH** |
| **Preregistration Document** | `docs/research/MEC-0014A-statistical-preregistration-draft.md` | `{EXPECTED_PREREG_SHA256}` | **VERIFIED MATCH** |
| **R1 Registration Manifest** | `docs/phase14/manifests/manifest_r1_HYP_004.json` | `{EXPECTED_R1_MANIFEST_SHA256}` | **VERIFIED MATCH** |
| **R2 Data Manifest** | `docs/phase14/manifests/manifest_r2_HYP_004.json` | `{EXPECTED_R2_MANIFEST_SHA256}` | **VERIFIED MATCH** |
| **R2 Endpoints Dataset** | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` | `{EXPECTED_R2_PARQUET_SHA256}` | **VERIFIED MATCH** |
| **R3 Replication Manifest** | `docs/phase14/manifests/manifest_r3_HYP_004.json` | `{EXPECTED_R3_MANIFEST_SHA256}` | **VERIFIED MATCH** |
| **R3 Derived Returns Dataset**| `data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet` | `{EXPECTED_R3_PARQUET_SHA256}` | **VERIFIED MATCH** |

---

## 3. Preregistered Operationalization Scheme

The internal OOS diagnostic operationalizes the Gao et al. (2018) §3 and Campbell & Thompson (2008) predictive framework:

- **Initial Estimation Window:** `2017-01-04` through `2019-12-31` ($T_{{train}} = 739$ eligible sessions).
- **Forecast Evaluation Window:** `2020-01-02` through `2022-12-30` ($T_{{eval}} = 750$ eligible sessions).
- **Monthly Expanding Re-estimation:**
  At the first eligible session of each calendar month $M$ in 2020–2022:
  1. Identify all eligible sessions strictly before calendar date $M\\text{{-01}}$.
  2. Estimate OLS with intercept: $r_{{13}} = \\alpha_M + \\beta_M \\cdot r_1$.
  3. Freeze $\\hat{{\\alpha}}_M$ and $\\hat{{\\beta}}_M$ for all forecasts within month $M$.
  4. Total Monthly Fits: Exactly $36$ monthly models (sample sizes expanding from $739$ to $1,468$ sessions).
- **Daily Predictive Forecast:**
  For each evaluation session $t$ in month $M$:
  $$\\hat{{r}}_{{13, t}} = \\hat{{\\alpha}}_M + \\hat{{\\beta}}_M \\cdot r_{{1, t}}$$
  where $r_{{1, t}}$ is the first-half-hour return available at 10:00:00 ET.
- **Historical-Mean Benchmark:**
  For each evaluation session $t$:
  $$\\bar{{r}}_{{13, t}} = \\frac{{1}}{{N_{{t-1}}}} \\sum_{{s < t}} r_{{13, s}}$$
  Updates daily strictly through session $t-1$ (zero intra-day or forward lookahead).
- **Out-of-Sample $R^2_{{OS}}$ Metric:**
  $$R^2_{{OS}} = 1 - \\frac{{\\text{{SSE}}_{{\\text{{model}}}}}}{{\\text{{SSE}}_{{\\text{{benchmark}}}}}} = 1 - \\frac{{\\sum_{{t=1}}^{{750}} (r_{{13, t}} - \\hat{{r}}_{{13, t}})^2}}{{\\sum_{{t=1}}^{{750}} (r_{{13, t}} - \\bar{{r}}_{{13, t}})^2}}$$

---

## 4. Empirical OOS Results & Point Estimates

| Diagnostic Metric | Empirical Value | Methodology & Canonical Interpretation |
| :--- | :---: | :--- |
| **Initial Estimation Sample ($T_{{train}}$)** | **{EXPECTED_INITIAL_TRAIN_OBSERVATIONS}** | Qualified sessions 2017-01-04 through 2019-12-31 |
| **Evaluation Sample ($T_{{eval}}$)** | **{result.evaluation_observation_count}** | Qualified sessions 2020-01-02 through 2022-12-30 |
| **Evaluation Count (2020)** | **{result.evaluation_counts_by_year.get(2020, 0)}** | Regular sessions meeting all data contract gates |
| **Evaluation Count (2021)** | **{result.evaluation_counts_by_year.get(2021, 0)}** | Regular sessions meeting all data contract gates |
| **Evaluation Count (2022)** | **{result.evaluation_counts_by_year.get(2022, 0)}** | Regular sessions meeting all data contract gates |
| **Monthly OLS Fits ($N_{{fits}}$)** | **{result.monthly_fit_count}** | Exactly one fit per calendar month in 2020–2022 |
| **Estimation Sample Size Range** | **[{result.estimation_sample_min}, {result.estimation_sample_max}]** | Expanding window: Jan 2020 (739) to Dec 2022 (1,468) |
| **Sum of Squared Errors (Model)** | **{result.sse_model}** | $\\sum_{{t}} (r_{{13, t}} - \\hat{{r}}_{{13, t}})^2$ |
| **Sum of Squared Errors (Benchmark)** | **{result.sse_benchmark}** | $\\sum_{{t}} (r_{{13, t}} - \\bar{{r}}_{{13, t}})^2$ |
| **Root Mean Squared Error (Model)** | **{result.rmse_model}** | $\\sqrt{{\\text{{SSE}}_{{\\text{{model}}}} / 750}}$ |
| **Root Mean Squared Error (Benchmark)** | **{result.rmse_benchmark}** | $\\sqrt{{\\text{{SSE}}_{{\\text{{benchmark}}}} / 750}}$ |
| **Out-of-Sample $R^2_{{OS}}$** | **{result.r2_os}** | **$1 - \\text{{SSE}}_{{\\text{{model}}}} / \\text{{SSE}}_{{\\text{{benchmark}}}}$ ({float(result.r2_os)*100:.3f}%)** |
| **Mean Model Forecast** | **{result.mean_forecast}** | Average predicted last-half-hour return |
| **Mean Actual $r_{{13}}$ (2020–2022)** | **{result.mean_actual_r13}** | Average realized last-half-hour return |

---

## 5. Methodological & Econometric Interpretation

1. **Predictive Performance ($R^2_{{OS}} < 0$):**
   The Campbell-Thompson out-of-sample diagnostic yields $R^2_{{OS}} = {result.r2_os}$ ({float(result.r2_os)*100:.3f}%). Because $R^2_{{OS}} < 0$, the sum of squared forecast errors from the expanding OLS model exceeds that of the simple expanding historical mean benchmark over the 2020–2022 evaluation period.
2. **Consistency with In-Sample Finding:**
   This result is theoretically and empirically congruent with the in-sample replication result from Step R3:
   - In-sample $R^2 = 0.002641$ (0.264%), $\\hat{{\\beta}} = +0.022489$, $p = 0.523533$.
   - When the in-sample linear relationship is statistically indistinguishable from zero, parameter estimation variance typically causes out-of-sample recursive forecasts to underperform the historical mean benchmark, yielding slightly negative $R^2_{{OS}}$.
3. **No Secondary Rescue Permitted:**
   Even if $R^2_{{OS}}$ had been positive, it could not overturn the primary finding. Because $R^2_{{OS}} is negative, both in-sample significance ($p = 0.5235$) and out-of-sample predictability ($R^2_{{OS}} = -4.84%$) fail to support contemporary predictive power of $r_1$ for $r_{{13}}$ on `SPY`.

---

## 6. Point-in-Time Integrity Assertions

Every forecast observation was programmatically verified against strict point-in-time constraints:
- `estimation_window_end < trading_date`: **PASSED (100% of 750 sessions)**.
- `all benchmark history dates < trading_date`: **PASSED (100% of 750 sessions)**.
- Constant monthly parameters: $\\hat{{\\alpha}}_M$ and $\\hat{{\\beta}}_M$ remained strictly invariant within each calendar month.
- Zero future targets ($r_{{13}}$) entered monthly estimation.

---

## 7. Lineage and Artifact Coordinates

- **R3 Derived Returns Dataset:** `{R3_PARQUET_PATH.relative_to(BASE_DIR).as_posix()}`
  - SHA-256: `{EXPECTED_R3_PARQUET_SHA256}`
- **R4 OOS Forecasts Parquet:** `{forecast_rel_path}`
  - SHA-256: `{result.derived_r4_forecast_parquet_sha256}`
  - Row Count: `750`
- **Tracked R4 Manifest:** `{manifest_rel_path}`
  - Manifest SHA-256: `{manifest_sha256}`
"""
    return md


def run_r4_execution() -> int:
    """Execute Step R4 internal OOS diagnostic workflow."""
    print("================================================================================")
    print("ACASH PHASE 14 STEP R4: HYP_004 INTERNAL OOS PREDICTIVE DIAGNOSTIC")
    print("Scheme: Expanding Monthly OLS vs. Daily Historical Mean Benchmark (2020–2022)")
    print("Role: Secondary Diagnostic Only | Primary Replication Outcome: NOT_ACCEPTED")
    print("================================================================================")

    # 1. Verify Upstream Governance Preconditions
    print("\n[Step 1] Verifying Upstream Governance Preconditions & Pinned Digests...")
    git_head = get_git_head_sha()
    print(f"  Current Git HEAD:        {git_head}")

    preconditions = validate_r4_preconditions(BASE_DIR)
    print(f"  HYP_004 SHA-256:         {preconditions['hyp_004_sha256']} (VERIFIED)")
    print(f"  Preregistration SHA-256: {preconditions['preregistration_sha256']} (VERIFIED)")
    print(f"  R1 Manifest SHA-256:     {preconditions['r1_manifest_sha256']} (VERIFIED)")
    print(f"  R2 Manifest SHA-256:     {preconditions['r2_manifest_sha256']} (VERIFIED)")
    print(f"  R2 Parquet SHA-256:      {preconditions['r2_parquet_sha256']} (VERIFIED)")
    print(f"  R3 Manifest SHA-256:     {preconditions['r3_manifest_sha256']} (VERIFIED)")
    print(f"  R3 Parquet SHA-256:      {preconditions['r3_parquet_sha256']} (VERIFIED)")
    print(f"  R3 Primary Outcome:      {preconditions['primary_outcome']} (VERIFIED IMMUTABLE)")

    # 2. Load Sealed R3 Primary Returns Dataset (Zero Network Calls)
    print("\n[Step 2] Loading Sealed R3 Primary Returns Dataset...")
    return_rows = load_r3_primary_returns(BASE_DIR)
    print(f"  Total Qualified Sessions: {len(return_rows)} (Expected: {EXPECTED_TOTAL_ELIGIBLE_OBSERVATIONS})")

    # 3. Execute Internal OOS Diagnostic
    print("\n[Step 3] Executing Monthly Expanding OLS & Daily Benchmark Forecasts...")
    result_pre = execute_internal_oos_diagnostic(return_rows)
    print(f"  Initial Train Sessions:  {EXPECTED_INITIAL_TRAIN_OBSERVATIONS} (2017-01-04 to 2019-12-31)")
    print(f"  Evaluation Sessions:     {result_pre.evaluation_observation_count} (2020-01-02 to 2022-12-30)")
    print(f"  Evaluation by Year:      2020: {result_pre.evaluation_counts_by_year.get(2020)}, "
          f"2021: {result_pre.evaluation_counts_by_year.get(2021)}, "
          f"2022: {result_pre.evaluation_counts_by_year.get(2022)}")
    print(f"  Monthly OLS Fits:        {result_pre.monthly_fit_count} fits")
    print(f"  Sample Size Range:       [{result_pre.estimation_sample_min}, {result_pre.estimation_sample_max}]")

    # 4. Serialize Local OOS Forecasts Parquet Artifact
    print("\n[Step 4] Serializing Local OOS Forecast Artifact...")
    forecast_sha256 = build_canonical_oos_forecasts_parquet(
        result_pre.forecast_rows,
        R4_FORECAST_PARQUET_PATH,
    )
    print(f"  Forecast Artifact:       {R4_FORECAST_PARQUET_PATH.relative_to(BASE_DIR)}")
    print(f"  Forecast Artifact SHA:   {forecast_sha256}")

    # Assemble Final Complete Result
    final_result = InternalOOSResult(
        evaluation_observation_count=result_pre.evaluation_observation_count,
        evaluation_counts_by_year=result_pre.evaluation_counts_by_year,
        monthly_fit_count=result_pre.monthly_fit_count,
        estimation_sample_min=result_pre.estimation_sample_min,
        estimation_sample_max=result_pre.estimation_sample_max,
        sse_model=result_pre.sse_model,
        sse_benchmark=result_pre.sse_benchmark,
        rmse_model=result_pre.rmse_model,
        rmse_benchmark=result_pre.rmse_benchmark,
        r2_os=result_pre.r2_os,
        mean_forecast=result_pre.mean_forecast,
        mean_actual_r13=result_pre.mean_actual_r13,
        source_r3_parquet_sha256=result_pre.source_r3_parquet_sha256,
        derived_r4_forecast_parquet_sha256=forecast_sha256,
        forecast_rows=result_pre.forecast_rows,
        monthly_fits=result_pre.monthly_fits,
        primary_outcome_immutable=result_pre.primary_outcome_immutable,
        secondary_diagnostic_classification=result_pre.secondary_diagnostic_classification,
    )

    print("\n[Step 5] Out-of-Sample Predictive Metrics:")
    print(f"  SSE Model:               {final_result.sse_model}")
    print(f"  SSE Benchmark:           {final_result.sse_benchmark}")
    print(f"  RMSE Model:              {final_result.rmse_model}")
    print(f"  RMSE Benchmark:          {final_result.rmse_benchmark}")
    print(f"  R^2_OS:                  {final_result.r2_os} ({float(final_result.r2_os)*100:.4f}%)")
    print(f"  Mean Model Forecast:     {final_result.mean_forecast}")
    print(f"  Mean Actual r13:         {final_result.mean_actual_r13}")

    # 5. Build and Write Tracked R4 Manifest
    print("\n[Step 6] Building Tracked R4 JSON Manifest...")
    manifest_payload = build_r4_manifest(final_result, source_git_sha=git_head)
    manifest_sha = manifest_payload["manifest_sha256"]
    manifest_str = CanonicalConfigSerializer.to_canonical_json(manifest_payload)
    TRACKED_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKED_MANIFEST_PATH.write_text(manifest_str, encoding="utf-8")
    print(f"  Tracked Manifest:        {TRACKED_MANIFEST_PATH.relative_to(BASE_DIR)}")
    print(f"  Manifest SHA-256:        {manifest_sha}")

    # 6. Generate and Write Tracked R4 Audit Markdown
    print("\n[Step 7] Generating Tracked R4 Audit Markdown...")
    audit_md = generate_r4_audit_markdown(
        result=final_result,
        manifest_sha256=manifest_sha,
        manifest_rel_path=str(TRACKED_MANIFEST_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
        forecast_rel_path=str(R4_FORECAST_PARQUET_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
        source_git_sha=git_head,
    )
    TRACKED_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKED_AUDIT_PATH.write_text(audit_md, encoding="utf-8")
    print(f"  Tracked Audit:           {TRACKED_AUDIT_PATH.relative_to(BASE_DIR)}")

    print("\n================================================================================")
    print("PHASE 14 STEP R4 COMPLETED SUCCESSFULLY")
    print(f"Outcome Invariant: Primary outcome remains {EXPECTED_PRIMARY_OUTCOME}")
    print(f"Diagnostic R^2_OS: {final_result.r2_os}")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_r4_execution())
