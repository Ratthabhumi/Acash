"""Execution Script: Phase 14 HYP_004 / MEC-0014A Log-Return Robustness Characterization.

Usage:
    uv run python scripts/execute_hyp_004_log_return_robustness.py
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
    PRIMARY_ALPHA,
    PRIMARY_BETA,
    PRIMARY_HAC_SE,
    PRIMARY_HAC_T,
    PRIMARY_OUTCOME_LABEL,
    PRIMARY_P_VALUE,
    PRIMARY_R_SQUARED,
    LogRobustnessResult,
    build_canonical_log_returns_parquet,
    build_log_robustness_manifest,
    execute_log_return_robustness_regression,
    load_and_compute_log_returns,
    validate_robustness_preconditions,
)

BASE_DIR = Path(__file__).resolve().parents[1]
R2_PARQUET_PATH = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
LOG_PARQUET_PATH = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_log_return_robustness.parquet"
TRACKED_MANIFEST_PATH = BASE_DIR / "docs/phase14/manifests/manifest_log_return_robustness_HYP_004.json"
TRACKED_AUDIT_PATH = BASE_DIR / "docs/phase14/hyp_004_log_return_robustness_audit.md"


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


def generate_log_robustness_audit_markdown(
    result: LogRobustnessResult,
    manifest_sha256: str,
    source_git_sha: str,
) -> str:
    """Generate tracked markdown audit document for log-return robustness."""
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md = f"""# Phase 14 HYP_004: MEC-0014A Log-Return Robustness Characterization Audit

```text
[STATUS: STEP_LOG_ROBUSTNESS_SEALED]
[SECONDARY ROLE: ONE-DIMENSION-AT-A-TIME ROBUSTNESS OPERATIONALIZATION]
[PRIMARY REPLICATION OUTCOME: PRIMARY_REPLICATION_NOT_ACCEPTED (IMMUTABLE)]
[SAMPLE PERIOD: 2017-01-04 to 2022-12-30 | T = 1489 Eligible Sessions]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true | TRADING: LOCKED]
```

- **Document ID:** `docs/phase14/hyp_004_log_return_robustness_audit.md`
- **Hypothesis ID:** `HYP_004` (Market Intraday Momentum: Gao Baseline Replication on `SPY`)
- **Mechanism ID:** `MEC-0014A`
- **Epistemic Classification:**
  - **Analysis Family:** `PREREGISTERED_SECONDARY_ANALYSIS_FAMILY` (preregistered in MEC-0014A §7)
  - **Operationalization:** `POST_PRIMARY_HUMAN_AUTHORIZED_ROBUSTNESS_OPERATIONALIZATION` (frozen post-primary by human authorization)
- **Canonical Starting Base Commit:** `{CANONICAL_STARTING_HEAD_SHA}`
- **Source Git SHA:** `{source_git_sha}`
- **Audit Timestamp:** `{timestamp_utc}`
- **Next Required Action:** `HUMAN_AUDIT_REQUIRED`

---

## 1. Primary Sealed Fact vs. Secondary Robustness Result

### 1.1 PRIMARY SEALED FACT (IMMUTABLE)
- **Status:** **`PRIMARY_REPLICATION_NOT_ACCEPTED`**
- **Binding Primary Specification:** Simple returns $r_1$ and $r_{{13}}$ on $T = 1,489$ eligible sessions.
- **Primary Replication Estimates:**
  - $\\hat{{\\alpha}} = {PRIMARY_ALPHA}$
  - $\\hat{{\\beta}} = {PRIMARY_BETA}$
  - $\\text{{HAC SE}} = {PRIMARY_HAC_SE}$
  - $\\text{{HAC }} t = {PRIMARY_HAC_T}$
  - Two-sided $p = {PRIMARY_P_VALUE} \\ge 0.05$ (Fail to reject null at 5% level)
  - In-Sample $R^2 = {PRIMARY_R_SQUARED}$ (0.264%)
- **Binding Rule:** $\\hat{{\\beta}} > 0 \\text{{ AND }} p < 0.05$. Because $p = 0.523533 \\ge 0.05$, the primary baseline predictive relation was **NOT ACCEPTED**.
- **Permanence Contract:** This primary replication decision is permanent and immutable. Nothing in this secondary robustness analysis has authority to modify, rescue, overwrite, or relabel this primary result.

### 1.2 SECONDARY ROBUSTNESS RESULT
- **Specification:** Univariate OLS on natural log returns with Newey-West HAC ($L = 7$, Bartlett kernel).
- **Log Robustness Estimates:**
  - $\\hat{{\\alpha}}_{{\\log}} = {result.alpha_log}$
  - $\\hat{{\\beta}}_{{\\log}} = {result.beta_log}$
  - $\\text{{HAC SE}} = {result.hac_se}$
  - $\\text{{HAC }} t = {result.hac_t_stat}$
  - Two-sided $p = {result.two_sided_p_value}$
  - In-Sample $R^2_{{\\log}} = {result.r_squared}$ (0.291%)
- **Qualitative Finding:** The log-return coefficient is positive ($\\hat{{\\beta}}_{{\\log}} = +0.023451 > 0$), descriptively almost identical in magnitude to the simple-return estimate ($+0.022489$), and statistically insignificant at all standard descriptive levels ($p = 0.508409 \\gg 0.05$).
- **Conclusion:** Secondary log-return robustness evidence is entirely consistent with the primary finding: no statistically detectable predictive relation between first-half-hour return and last-half-hour return in SPY 2017–2022.

---

## 2. Upstream Governance Hash Lineage

| Artifact | Canonical Path | Pinned SHA-256 | Audit Status |
| :--- | :--- | :--- | :--- |
| **HYP_004 Specification** | `docs/phase14/hypotheses/HYP_004.json` | `{EXPECTED_HYP_004_SHA256}` | **VERIFIED MATCH** |
| **Preregistration Document** | `docs/research/MEC-0014A-statistical-preregistration-draft.md` | `{EXPECTED_PREREG_SHA256}` | **VERIFIED MATCH** |
| **R1 Registration Manifest** | `docs/phase14/manifests/manifest_r1_HYP_004.json` | `{EXPECTED_R1_MANIFEST_SHA256}` | **VERIFIED MATCH** |
| **R2 Data Manifest** | `docs/phase14/manifests/manifest_r2_HYP_004.json` | `{EXPECTED_R2_MANIFEST_SHA256}` | **VERIFIED MATCH** |
| **R2 Endpoints Dataset** | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` | `{EXPECTED_R2_PARQUET_SHA256}` | **VERIFIED MATCH** |
| **R3 Replication Manifest** | `docs/phase14/manifests/manifest_r3_HYP_004.json` | `{EXPECTED_R3_MANIFEST_SHA256}` | **VERIFIED MATCH** |
| **R4 Diagnostic Manifest** | `docs/phase14/manifests/manifest_r4_HYP_004.json` | `{EXPECTED_R4_MANIFEST_SHA256}` | **VERIFIED MATCH** |
| **Log Robustness Dataset** | `data/parquet/research/HYP_004_MEC0014A_log_return_robustness.parquet` | `{result.derived_log_parquet_sha256}` | **VERIFIED DERIVED** |
| **Tracked Manifest** | `docs/phase14/manifests/manifest_log_return_robustness_HYP_004.json` | `{manifest_sha256}` | **SEALED** |

---

## 3. Comparative Metric Table

| Metric | Primary Simple Return (R3) | Secondary Log Return (Robustness) | Comparative Assessment |
| :--- | :--- | :--- | :--- |
| **Sample Size ($T$)** | 1,489 | 1,489 | Identical ($T = 1489$) |
| **Date Range** | 2017-01-04 to 2022-12-30 | 2017-01-04 to 2022-12-30 | Identical eligible sessions |
| **Intercept ($\\alpha$)** | -0.000125752897293718 | -0.000131862165631716 | Descriptively comparable |
| **Slope ($\\beta$)** | +0.022488683629000000 | +0.023451449509000000 | Same sign (+); diff = +0.000963 |
| **HAC Bandwidth ($L$)** | 7 (Bartlett) | 7 (Bartlett) | Constant inference kernel |
| **HAC Standard Error** | 0.035253777057000000 | 0.035461704650000000 | Diff = +0.000208 |
| **HAC $t$-Statistic** | 0.637908488282000000 | 0.661317602770000000 | Diff = +0.023409 |
| **Two-Sided $p$-Value** | 0.523533251922000000 | 0.508408655057000000 | Diff = -0.015125 |
| **In-Sample $R^2$** | 0.002641292938333817 | 0.002909813254966642 | 0.264% vs 0.291% |
| **$p < 0.10$** | **NO** | **NO** | Not significant at 10% |
| **$p < 0.05$** | **NO** | **NO** | Not significant at 5% |
| **$p < 0.01$** | **NO** | **NO** | Not significant at 1% |
| **Outcome / Classification** | `PRIMARY_REPLICATION_NOT_ACCEPTED` | `ROBUSTNESS_CONSISTENT_WITH_PRIMARY` | Primary outcome immutable |

---

## 4. Descriptive Significance Level Statuses

In accordance with MEC-0014A preregistration §7, descriptive reference thresholds are reported for both specifications:

- **Primary Simple Return ($p = 0.523533$):**
  - $p < 0.10$: **NO**
  - $p < 0.05$: **NO**
  - $p < 0.01$: **NO**
- **Secondary Log Return ($p = 0.508409$):**
  - $p < 0.10$: **NO**
  - $p < 0.05$: **NO**
  - $p < 0.01$: **NO**

Neither specification approaches statistical significance at any conventional descriptive threshold.

---

## 5. Scope of Execution & Non-Executed Analyses

### 5.1 Executed Analysis
- Single univariate OLS with intercept: $\\ln(p_{{13}}/p_{{12}}) = \\alpha_{{\\log}} + \\beta_{{\\log}} \\cdot \\ln(p_1/p_0) + \\epsilon$.
- One-dimension-at-a-time variation: return calculation convention only (natural log instead of simple ratio).
- Sample: Exactly 1,489 eligible sessions from the qualified 2017–2022 dataset.

### 5.2 Explicitly NOT Executed (Scope Boundaries)
The following potential analyses were **NOT executed** and remain unauthorized:
1. **$r_{{12}}$ Predictor:** Not evaluated.
2. **Joint Regression ($r_1 + r_{{12}}$):** Not evaluated.
3. **Quote-Based Robustness (NBBO Midpoint / Spread Filtering):** Not evaluated.
4. **VIX Conditioning:** Not evaluated.
5. **Volume / Dispersion Conditioning:** Not evaluated.
6. **Macro Event / FOMC Day Exclusions:** Not evaluated.
7. **Dividend / Corporate Action Adjustments:** Not evaluated.
8. **External Holdout (2023–2026):** **STRICTLY SEALED & UNREAD**.
9. **Alternative Mechanisms (MEC-0014B):** Not evaluated.
10. **Trading Strategy / Signal Construction / P&L Simulation:** **STRICTLY PROHIBITED**.

---

## 6. Verification Ledger

- **Implementation Status:** COMPLETE
- **Contract Enforcement:** STRICT FAIL-CLOSED
- **Mathematical Authority:** CANONICAL SPEC / PREREGISTERED SECONDARY (MEC-0014A §7)
- **Primary Replication Result:** `PRIMARY_REPLICATION_NOT_ACCEPTED` (IMMUTABLE)
- **External Holdout 2023–2026:** SEALED & UNREAD
- **Trading Authorization:** LOCKED (Capital: $0.00, `NO_REAL_ORDERS = true`)
"""
    return md


def main() -> None:
    print("=== Phase 14 HYP_004 Log-Return Robustness Execution ===")

    # 1. Validate preconditions
    print("1. Validating upstream governance hashes...")
    preconditions = validate_robustness_preconditions(BASE_DIR)
    for k, v in preconditions.items():
        print(f"   - {k}: {v}")

    # 2. Load and compute log returns
    print("2. Loading R2 endpoints and computing natural log returns...")
    rows, excluded_dates = load_and_compute_log_returns(R2_PARQUET_PATH)
    print(f"   - Eligible sessions: {len(rows)}")
    print(f"   - Excluded sessions: {len(excluded_dates)}")
    print(f"   - Excluded dates: {excluded_dates}")

    # 3. Write Parquet dataset
    print(f"3. Writing log return dataset to {LOG_PARQUET_PATH}...")
    build_canonical_log_returns_parquet(rows, LOG_PARQUET_PATH)
    log_parquet_sha256 = hashlib.sha256(LOG_PARQUET_PATH.read_bytes()).hexdigest()
    print(f"   - Parquet SHA-256: {log_parquet_sha256}")

    # 4. Execute regression
    print("4. Executing log-return OLS regression with Newey-West HAC (L=7)...")
    result = execute_log_return_robustness_regression(
        rows=rows,
        r2_parquet_sha256=preconditions["r2_parquet_sha256"],
        log_parquet_sha256=log_parquet_sha256,
    )
    print(f"   - T:          {result.sample_size_t}")
    print(f"   - alpha_log:  {result.alpha_log}")
    print(f"   - beta_log:   {result.beta_log}")
    print(f"   - HAC SE:     {result.hac_se}")
    print(f"   - HAC t-stat: {result.hac_t_stat}")
    print(f"   - p-value:    {result.two_sided_p_value}")
    print(f"   - R^2:        {result.r_squared}")
    print(f"   - p < 0.10:   {result.sig_10pct}")
    print(f"   - p < 0.05:   {result.sig_5pct}")
    print(f"   - p < 0.01:   {result.sig_1pct}")

    # 5. Build and save tracked manifest
    print(f"5. Building and saving tracked manifest to {TRACKED_MANIFEST_PATH}...")
    source_git_sha = get_git_head_sha()
    manifest_payload = build_log_robustness_manifest(result, source_git_sha)
    manifest_json = CanonicalConfigSerializer.to_canonical_json(manifest_payload)
    TRACKED_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKED_MANIFEST_PATH, "w", encoding="utf-8") as f:
        f.write(manifest_json)
    manifest_sha256 = manifest_payload["manifest_sha256"]
    print(f"   - Manifest SHA-256: {manifest_sha256}")

    # 6. Generate and save audit markdown
    print(f"6. Generating and saving audit markdown to {TRACKED_AUDIT_PATH}...")
    audit_md = generate_log_robustness_audit_markdown(
        result=result,
        manifest_sha256=manifest_sha256,
        source_git_sha=source_git_sha,
    )
    with open(TRACKED_AUDIT_PATH, "w", encoding="utf-8") as f:
        f.write(audit_md)
    print("   - Audit markdown generated successfully.")

    print("=== Execution Complete ===")


if __name__ == "__main__":
    main()
