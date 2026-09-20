# Phase 14 HYP_004: MEC-0014A Log-Return Robustness Characterization Audit

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
- **Canonical Starting Base Commit:** `373c0dc98cde53f77fa23f7d9bde6c2ae0ba52cf`
- **Source Git SHA:** `373c0dc98cde53f77fa23f7d9bde6c2ae0ba52cf`
- **Audit Timestamp:** `2026-09-20 09:32:18 UTC`
- **Next Required Action:** `HUMAN_AUDIT_REQUIRED`

---

## 1. Primary Sealed Fact vs. Secondary Robustness Result

### 1.1 PRIMARY SEALED FACT (IMMUTABLE)
- **Status:** **`PRIMARY_REPLICATION_NOT_ACCEPTED`**
- **Binding Primary Specification:** Simple returns $r_1$ and $r_{13}$ on $T = 1,489$ eligible sessions.
- **Primary Replication Estimates:**
  - $\hat{\alpha} = -0.000125752897293718$
  - $\hat{\beta} = 0.022488683629000000$
  - $\text{HAC SE} = 0.035253777057000000$
  - $\text{HAC } t = 0.637908488282000000$
  - Two-sided $p = 0.523533251922000000 \ge 0.05$ (Fail to reject null at 5% level)
  - In-Sample $R^2 = 0.002641292938333817$ (0.264%)
- **Binding Rule:** $\hat{\beta} > 0 \text{ AND } p < 0.05$. Because $p = 0.523533 \ge 0.05$, the primary baseline predictive relation was **NOT ACCEPTED**.
- **Permanence Contract:** This primary replication decision is permanent and immutable. Nothing in this secondary robustness analysis has authority to modify, rescue, overwrite, or relabel this primary result.

### 1.2 SECONDARY ROBUSTNESS RESULT
- **Specification:** Univariate OLS on natural log returns with Newey-West HAC ($L = 7$, Bartlett kernel).
- **Log Robustness Estimates:**
  - $\hat{\alpha}_{\log} = -0.000131862165631716$
  - $\hat{\beta}_{\log} = 0.023451449509000000$
  - $\text{HAC SE} = 0.035461704650000000$
  - $\text{HAC } t = 0.661317602770000000$
  - Two-sided $p = 0.508408655057000000$
  - In-Sample $R^2_{\log} = 0.002909813254966642$ (0.291%)
- **Qualitative Finding:** The log-return coefficient is positive ($\hat{\beta}_{\log} = +0.023451 > 0$), descriptively almost identical in magnitude to the simple-return estimate ($+0.022489$), and statistically insignificant at all standard descriptive levels ($p = 0.508409 \gg 0.05$).
- **Conclusion:** Secondary log-return robustness evidence is entirely consistent with the primary finding: no statistically detectable predictive relation between first-half-hour return and last-half-hour return in SPY 2017–2022.

---

## 2. Upstream Governance Hash Lineage

| Artifact | Canonical Path | Pinned SHA-256 | Audit Status |
| :--- | :--- | :--- | :--- |
| **HYP_004 Specification** | `docs/phase14/hypotheses/HYP_004.json` | `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d` | **VERIFIED MATCH** |
| **Preregistration Document** | `docs/research/MEC-0014A-statistical-preregistration-draft.md` | `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce` | **VERIFIED MATCH** |
| **R1 Registration Manifest** | `docs/phase14/manifests/manifest_r1_HYP_004.json` | `eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b` | **VERIFIED MATCH** |
| **R2 Data Manifest** | `docs/phase14/manifests/manifest_r2_HYP_004.json` | `25b5ae6c4769064459709bb09bbc759e02f7b340c4d4e94b4ff9442e3082ef71` | **VERIFIED MATCH** |
| **R2 Endpoints Dataset** | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` | `096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776` | **VERIFIED MATCH** |
| **R3 Replication Manifest** | `docs/phase14/manifests/manifest_r3_HYP_004.json` | `56d4f79c1e563a81c0b601f695023a5da54cac58e5b9a19a0be9108b3ca4ef40` | **VERIFIED MATCH** |
| **R4 Diagnostic Manifest** | `docs/phase14/manifests/manifest_r4_HYP_004.json` | `d3e5298ccf66da9854bc84c1ca64aeec112c8e907b96f5fd36a2d8e3f194b9a7` | **VERIFIED MATCH** |
| **Log Robustness Dataset** | `data/parquet/research/HYP_004_MEC0014A_log_return_robustness.parquet` | `1499e0900def843ec64a7ffe385151d8660e46836383d6c07f31b8f71a0c4d13` | **VERIFIED DERIVED** |
| **Tracked Manifest** | `docs/phase14/manifests/manifest_log_return_robustness_HYP_004.json` | `f749a0d39a88d9ff670023e3eaa0db75744656e2b79516921c4d7a3727d04fb6` | **SEALED** |

---

## 3. Comparative Metric Table

| Metric | Primary Simple Return (R3) | Secondary Log Return (Robustness) | Comparative Assessment |
| :--- | :--- | :--- | :--- |
| **Sample Size ($T$)** | 1,489 | 1,489 | Identical ($T = 1489$) |
| **Date Range** | 2017-01-04 to 2022-12-30 | 2017-01-04 to 2022-12-30 | Identical eligible sessions |
| **Intercept ($\alpha$)** | -0.000125752897293718 | -0.000131862165631716 | Descriptively comparable |
| **Slope ($\beta$)** | +0.022488683629000000 | +0.023451449509000000 | Same sign (+); diff = +0.000963 |
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
- Single univariate OLS with intercept: $\ln(p_{13}/p_{12}) = \alpha_{\log} + \beta_{\log} \cdot \ln(p_1/p_0) + \epsilon$.
- One-dimension-at-a-time variation: return calculation convention only (natural log instead of simple ratio).
- Sample: Exactly 1,489 eligible sessions from the qualified 2017–2022 dataset.

### 5.2 Explicitly NOT Executed (Scope Boundaries)
The following potential analyses were **NOT executed** and remain unauthorized:
1. **$r_{12}$ Predictor:** Not evaluated.
2. **Joint Regression ($r_1 + r_{12}$):** Not evaluated.
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
