"""Execution Script: Phase 14 Step R3 HYP_004 Primary Econometric Replication.

Executes the single authorized primary OLS regression with Newey-West HAC inference
for HYP_004 (Market Intraday Momentum: Gao Baseline Predictive Relation on SPY).

Usage:
    uv run python scripts/execute_phase14_step_r3_hyp_004.py
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
from acash.research.step_r3_hyp_004 import (
    CANONICAL_STARTING_HEAD_SHA,
    EXPECTED_ELIGIBLE_OBSERVATIONS,
    EXPECTED_EXCLUDED_OBSERVATIONS,
    EXPECTED_HAC_LAG,
    EXPECTED_HYP_004_SHA256,
    EXPECTED_PREREG_SHA256,
    EXPECTED_R1_MANIFEST_SHA256,
    EXPECTED_R2_MANIFEST_SHA256,
    EXPECTED_R2_PARQUET_SHA256,
    PrimaryRegressionResult,
    PrimaryReplicationOutcome,
    build_canonical_primary_returns_parquet,
    build_r3_manifest,
    compute_simple_returns_from_r2,
    execute_primary_replication_regression,
    validate_r3_preconditions,
)

BASE_DIR = Path(__file__).resolve().parents[1]
R2_PARQUET_PATH = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet"
R3_PARQUET_PATH = BASE_DIR / "data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet"
TRACKED_MANIFEST_PATH = BASE_DIR / "docs/phase14/manifests/manifest_r3_HYP_004.json"
TRACKED_AUDIT_PATH = BASE_DIR / "docs/phase14/phase14_r3_primary_replication_audit_HYP_004.md"


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


def run_r3_execution() -> int:
    """Execute Step R3 primary econometric replication workflow."""
    print("================================================================================")
    print("ACASH PHASE 14 STEP R3: HYP_004 PRIMARY ECONOMETRIC REPLICATION")
    print("Model: r13_t = alpha + beta * r1_t + eps_t | SPY In-Sample (2017–2022)")
    print("Rule: beta_hat > 0 AND two-sided Newey-West HAC p-value < 0.05 (L = 7, T = 1489)")
    print("================================================================================")

    # 1. Verify Upstream Governance Preconditions
    print("\n[Step 1] Verifying Upstream Governance Preconditions & Pinned Digests...")
    git_head = get_git_head_sha()
    print(f"  Current Git HEAD:       {git_head}")
    if not git_head.startswith(CANONICAL_STARTING_HEAD_SHA[:7]) and git_head != CANONICAL_STARTING_HEAD_SHA:
        print(f"  [NOTICE] Git HEAD {git_head} builds upon canonical starting base {CANONICAL_STARTING_HEAD_SHA}")

    preconditions = validate_r3_preconditions(BASE_DIR)
    print(f"  HYP_004 SHA-256:        {preconditions['hyp_004_sha256']} (VERIFIED)")
    print(f"  R1 Manifest SHA-256:    {preconditions['r1_manifest_sha256']} (VERIFIED)")
    print(f"  Preregistration SHA-256:{preconditions['preregistration_sha256']} (VERIFIED)")
    print(f"  R2 Manifest SHA-256:    {preconditions['r2_manifest_sha256']} (VERIFIED)")
    print(f"  R2 Parquet SHA-256:     {preconditions['r2_parquet_sha256']} (VERIFIED)")

    # 2. Derive Simple Return Series from R2 Local Dataset (Zero Network Calls)
    print("\n[Step 2] Deriving Simple Returns r1 and r13 from Sealed R2 Endpoints...")
    return_rows, excluded_dates = compute_simple_returns_from_r2(R2_PARQUET_PATH)
    print(f"  Eligible Primary Observations: {len(return_rows)} (Expected: {EXPECTED_ELIGIBLE_OBSERVATIONS})")
    print(f"  Excluded Observations:         {len(excluded_dates)} (Expected: {EXPECTED_EXCLUDED_OBSERVATIONS})")
    print(f"  Excluded Dates:                {', '.join(excluded_dates)}")

    # 3. Write Derived Return Parquet Dataset & Compute SHA-256
    print("\n[Step 3] Writing Deterministic Derived Return Dataset...")
    build_canonical_primary_returns_parquet(return_rows, R3_PARQUET_PATH)
    r3_parquet_bytes = R3_PARQUET_PATH.read_bytes()
    r3_parquet_sha256 = hashlib.sha256(r3_parquet_bytes).hexdigest()
    print(f"  Derived Return Dataset: {R3_PARQUET_PATH.relative_to(BASE_DIR)}")
    print(f"  Return Dataset SHA-256: {r3_parquet_sha256}")

    # 4. Execute Primary OLS Regression & Newey-West HAC Inference (K=1)
    print("\n[Step 4] Executing Authorized Primary Econometric Regression (K=1)...")
    reg_result = execute_primary_replication_regression(
        return_rows=return_rows,
        r2_parquet_sha256=preconditions["r2_parquet_sha256"],
        r3_parquet_sha256=r3_parquet_sha256,
    )

    print(f"  Sample Size (T):        {reg_result.sample_size_t}")
    print(f"  HAC Bandwidth Lag (L):  {reg_result.hac_lag_l} (Newey-West 1994 Bartlett)")
    print(f"  Alpha Hat (Intercept):  {reg_result.alpha_hat}")
    print(f"  Beta Hat (Slope):       {reg_result.beta_hat}")
    print(f"  Newey-West HAC SE:      {reg_result.hac_se_beta}")
    print(f"  HAC t-statistic:        {reg_result.hac_t_stat}")
    print(f"  Two-Sided p-value:      {reg_result.two_sided_p_value}")
    print(f"  In-Sample R-squared:    {reg_result.r_squared}")

    # 5. Evaluate Binding Primary Acceptance Rule
    print("\n[Step 5] Evaluating Frozen Primary Acceptance Rule...")
    print(f"  Binding Rule:           {reg_result.binding_acceptance_rule}")
    print(f"  Direction Test (beta>0):{'PASS' if reg_result.beta_hat > 0 else 'FAIL'} ({reg_result.beta_hat})")
    print(f"  Significance (p<0.05):  {'PASS' if reg_result.two_sided_p_value < Decimal('0.05') else 'FAIL'} ({reg_result.two_sided_p_value})")
    print(f"  Primary Outcome:        {reg_result.outcome_label.value}")

    # 6. Write Tracked R3 Manifest
    print("\n[Step 6] Writing Tracked R3 Manifest...")
    manifest = build_r3_manifest(reg_result, source_git_sha=git_head)
    TRACKED_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest_json = CanonicalConfigSerializer.to_canonical_json(manifest)
    manifest_bytes = manifest_json.encode("utf-8")
    TRACKED_MANIFEST_PATH.write_bytes(manifest_bytes)
    print(f"  Tracked R3 Manifest:    {TRACKED_MANIFEST_PATH.relative_to(BASE_DIR)}")
    print(f"  Manifest SHA-256:       {manifest['manifest_sha256']}")

    # 7. Write Tracked R3 Audit Report
    print("\n[Step 7] Writing Phase 14 Step R3 Primary Replication Audit Report...")
    audit_content = f"""# Phase 14 Step R3: HYP_004 Primary Econometric Replication Audit

```text
[STATUS: PRIMARY ECONOMETRIC REPLICATION COMPLETE]
[OUTCOME: {reg_result.outcome_label.value}]
[K = 1: SINGLE PRIMARY MODEL]
[SECONDARY ANALYSES STRICTLY LOCKED]
[OOS 2023-2026 STRICTLY SEALED]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true]
```

- **Document ID:** `docs/phase14/phase14_r3_primary_replication_audit_HYP_004.md`
- **Hypothesis:** `HYP_004` (Market Intraday Momentum: Gao Baseline Replication on `SPY`)
- **Mechanism ID:** `MEC-0014A`
- **Starting Git Base:** `{CANONICAL_STARTING_HEAD_SHA}`
- **Execution Git HEAD:** `{git_head}`
- **Execution Timestamp (UTC):** `{datetime.now(timezone.utc).isoformat()}`
- **Calendar Authority:** `NyseCa1Calendar`

---

## 1. Upstream Cryptographic Lineage Verification

| Artifact Description | Canonical Filesystem Path | SHA-256 Digest | Precondition Status |
| :--- | :--- | :--- | :--- |
| **HYP_004 Specification** | `docs/phase14/hypotheses/HYP_004.json` | `{preconditions['hyp_004_sha256']}` | VERIFIED MATCH |
| **MEC-0014A Preregistration** | `docs/research/MEC-0014A-statistical-preregistration-draft.md` | `{preconditions['preregistration_sha256']}` | VERIFIED MATCH |
| **Phase 14 R1 Manifest** | `docs/phase14/manifests/manifest_r1_HYP_004.json` | `{preconditions['r1_manifest_sha256']}` | VERIFIED MATCH |
| **Phase 14 R2 Manifest** | `docs/phase14/manifests/manifest_r2_HYP_004.json` | `{preconditions['r2_manifest_sha256']}` | VERIFIED MATCH |
| **R2 Endpoint Parquet Dataset** | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` | `{preconditions['r2_parquet_sha256']}` | VERIFIED MATCH |

---

## 2. Sample Census & Derived Return Lineage

- **Total In-Sample Regular Sessions (2017–2022):** 1,498
- **Primary-Regression Eligible Observations ($T$):** **{reg_result.sample_size_t}**
- **Quarantined Excluded Observations:** 9
  - `AMBIGUOUS_P12_BOUNDARY_PRICE`: 5 sessions (`2017-01-20`, `2017-04-18`, `2017-10-31`, `2018-05-18`, `2020-04-22`)
  - `AMBIGUOUS_P1_BOUNDARY_PRICE`: 3 sessions (`2017-08-17`, `2019-06-11`, `2021-02-04`)
  - `FIRST_SESSION_NO_PRIOR_IN_SAMPLE_CLOSE`: 1 session (`2017-01-03`)
- **Chronological Date Range:** `{reg_result.earliest_trading_date}` to `{reg_result.latest_trading_date}`
- **Derived Primary Return Dataset:** `data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet`
- **Derived Return Dataset SHA-256:** `{r3_parquet_sha256}`

### Exact Simple Return Specification:
$$r_{{1, t}} = \\frac{{p_{{1, t}}}}{{p_{{0, t}}}} - 1 = \\frac{{\\text{{SIP Trade Price at or before 10:00:00 ET}}}}{{\\text{{Previous NYSE Arca Qualified Primary Close}}}} - 1$$
$$r_{{13, t}} = \\frac{{p_{{13, t}}}}{{p_{{12, t}}}} - 1 = \\frac{{\\text{{Current NYSE Arca Qualified Primary Close}}}}{{\\text{{SIP Trade Price at or before 15:30:00 ET}}}} - 1$$

---

## 3. Primary Econometric Replication Estimates

| Metric | Estimated Value | Econometric Definition |
| :--- | :---: | :--- |
| **Sample Size ($T$)** | **{reg_result.sample_size_t}** | Number of eligible regular sessions |
| **HAC Bandwidth ($L$)** | **{reg_result.hac_lag_l}** | Newey-West (1994) rule-of-thumb: $\\lfloor 4(T/100)^{{2/9}} \\rfloor$ |
| **HAC Kernel** | **Bartlett** | Triangular lag weighting: $w(l, L) = 1 - \\frac{{l}}{{L + 1}}$ |
| **Intercept ($\\hat{{\\alpha}}$)** | **{reg_result.alpha_hat}** | $\\bar{{r}}_{{13}} - \\hat{{\\beta}} \\bar{{r}}_1$ |
| **Slope ($\\hat{{\\beta}}$)** | **{reg_result.beta_hat}** | $\\frac{{\\sum (r_{{1, t}} - \\bar{{r}}_1)(r_{{13, t}} - \\bar{{r}}_{{13}})}}{{\\sum (r_{{1, t}} - \\bar{{r}}_1)^2}}$ |
| **Newey-West HAC Standard Error** | **{reg_result.hac_se_beta}** | Asymptotic square root of HAC variance |
| **HAC $t$-statistic** | **{reg_result.hac_t_stat}** | $\\frac{{\\hat{{\\beta}}}}{{\\text{{HAC SE}}(\\hat{{\\beta}})}}$ |
| **Two-Sided Asymptotic $p$-value** | **{reg_result.two_sided_p_value}** | $2(1 - \\Phi(|t|))$ |
| **In-Sample $R^2$** | **{reg_result.r_squared}** | Unadjusted $1 - \\frac{{\\text{{SSE}}}}{{\\text{{SST}}}}$ |

---

## 4. Binding Primary Decision Evaluation

- **Preregistered Decision Rule:** $\\hat{{\\beta}} > 0 \\text{{ AND }} p < 0.05$ (two-sided Newey-West HAC, $L=7$, $T=1489$)
- **Direction Criterion ($\\hat{{\\beta}} > 0$):** **{'PASS' if reg_result.beta_hat > 0 else 'FAIL'}** (Estimated $\\hat{{\\beta}} = {reg_result.beta_hat}$)
- **Significance Criterion ($p < 0.05$):** **{'PASS' if reg_result.two_sided_p_value < Decimal('0.05') else 'FAIL'}** (Estimated $p = {reg_result.two_sided_p_value}$)
- **Primary Binary Replication Outcome:** **`{reg_result.outcome_label.value}`**

---

## 5. Execution Governance & Boundary Invariants

1. **Single Primary Model ($K=1$):** Exactly one regression was executed. Zero model searches, zero alternative predictors, zero threshold scans.
2. **Zero Secondary Robustness Analyses Executed:**
   - $r_{{12}}$ (10:00 to 15:30) was **NOT RUN**.
   - Joint $r_1 + r_{{12}}$ regression was **NOT RUN**.
   - Log-return specification was **NOT RUN**.
   - Quote-based (bid/ask/midpoint) endpoints were **NOT RUN**.
   - Alternative HAC bandwidths / kernels were **NOT RUN**.
   - Spearman rank IC / Pearson IC were **NOT RUN**.
   - Friction waterfall / cost models were **NOT RUN**.
   - VIX, volume, and macro-event conditioning were **NOT RUN**.
   - Ex-dividend sensitivity was **NOT RUN**.
   - Internal recursive OOS (2020–2022) was **NOT RUN**.
3. **Strict Out-of-Sample Holdout Seal:** Zero queries or data records from $\\ge \\text{{2023-01-01}}$ were accessed. External 2023–2026 holdout remains **STRICTLY SEALED**.
4. **Capital & Execution Locks:** Capital remains at **\\$0.00**, `NO_REAL_ORDERS = true`, Paper and Live execution remain **STRICTLY LOCKED**.
5. **Human Governance Authority:** The primary replication outcome is sealed for Human contributor review. Step R4 and subsequent phases remain strictly locked pending explicit authorization.
"""

    TRACKED_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKED_AUDIT_PATH.write_text(audit_content, encoding="utf-8")
    print(f"  Tracked Audit Report:   {TRACKED_AUDIT_PATH.relative_to(BASE_DIR)}")

    print("\n================================================================================")
    print(f"PHASE 14 STEP R3 COMPLETED SUCCESSFULLY: {reg_result.outcome_label.value}")
    print("================================================================================")
    return 0


def main() -> int:
    try:
        return run_r3_execution()
    except Exception as e:
        print(f"\n[FATAL ERROR in Phase 14 Step R3]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
