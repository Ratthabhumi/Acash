# Phase 14 Step R4: HYP_004 Internal Out-of-Sample Diagnostic Audit

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
- **Canonical Starting Base Commit:** `bb2309f5ed570089bfd4c613727f92b3915cd079`
- **Source Git SHA:** `bb2309f5ed570089bfd4c613727f92b3915cd079`
- **Audit Timestamp:** `2026-09-20 09:15:07 UTC`
- **Next Required Action:** `HUMAN_AUDIT_REQUIRED`

---

## 1. Executive Summary & Epistemic Boundaries

Phase 14 Step R4 executed the single authorized preregistered secondary predictive diagnostic for `HYP_004` / `MEC-0014A`:
**Internal Recursive Out-of-Sample (OOS) Evaluation** on the qualified 2017–2022 `SPY` replication sample.

### Crucial Epistemic Boundaries
1. **Primary Outcome Invariant:**
   The primary econometric replication result finalized in Step R3 is **`PRIMARY_REPLICATION_NOT_ACCEPTED`** (two-sided $p = 0.523533 \ge 0.05$). This outcome is **final and immutable**. The internal OOS evaluation is a secondary predictive diagnostic and possesses **zero authority** to overturn, rescue, or relabel the primary replication decision.
2. **No Binary Pass/Fail Threshold:**
   Section 7 of the ratified preregistration (`docs/research/MEC-0014A-statistical-preregistration-draft.md`) specifies $R^2_{OS}$ as a descriptive predictive diagnostic. It establishes **no binary acceptance threshold** (no `OOS_PASS` or `OOS_FAIL`).
3. **External Holdout Preservation:**
   All data from $\ge \text{2023-01-01}$ remains strictly **SEALED & UNREAD**. Zero holdout sessions were accessed.
4. **Trading & Execution Boundaries:**
   No strategy admission, signal generation, backtesting, Paper trading, or Live execution is authorized. Canonical capital remains **$0.00** with `NO_REAL_ORDERS = true`.

---

## 2. Upstream Governance Hash Verification

| Artifact | Canonical Path | Pinned SHA-256 | Audit Status |
| :--- | :--- | :--- | :--- |
| **HYP_004 Specification** | `docs/phase14/hypotheses/HYP_004.json` | `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d` | **VERIFIED MATCH** |
| **Preregistration Document** | `docs/research/MEC-0014A-statistical-preregistration-draft.md` | `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce` | **VERIFIED MATCH** |
| **R1 Registration Manifest** | `docs/phase14/manifests/manifest_r1_HYP_004.json` | `eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b` | **VERIFIED MATCH** |
| **R2 Data Manifest** | `docs/phase14/manifests/manifest_r2_HYP_004.json` | `25b5ae6c4769064459709bb09bbc759e02f7b340c4d4e94b4ff9442e3082ef71` | **VERIFIED MATCH** |
| **R2 Endpoints Dataset** | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` | `096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776` | **VERIFIED MATCH** |
| **R3 Replication Manifest** | `docs/phase14/manifests/manifest_r3_HYP_004.json` | `56d4f79c1e563a81c0b601f695023a5da54cac58e5b9a19a0be9108b3ca4ef40` | **VERIFIED MATCH** |
| **R3 Derived Returns Dataset**| `data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet` | `2b37cba80a845102be6a322af7ff12ff34ecd7a7947e10cf663a3bacdd93d8b9` | **VERIFIED MATCH** |

---

## 3. Preregistered Operationalization Scheme

The internal OOS diagnostic operationalizes the Gao et al. (2018) §3 and Campbell & Thompson (2008) predictive framework:

- **Initial Estimation Window:** `2017-01-04` through `2019-12-31` ($T_{train} = 739$ eligible sessions).
- **Forecast Evaluation Window:** `2020-01-02` through `2022-12-30` ($T_{eval} = 750$ eligible sessions).
- **Monthly Expanding Re-estimation:**
  At the first eligible session of each calendar month $M$ in 2020–2022:
  1. Identify all eligible sessions strictly before calendar date $M\text{-01}$.
  2. Estimate OLS with intercept: $r_{13} = \alpha_M + \beta_M \cdot r_1$.
  3. Freeze $\hat{\alpha}_M$ and $\hat{\beta}_M$ for all forecasts within month $M$.
  4. Total Monthly Fits: Exactly $36$ monthly models (sample sizes expanding from $739$ to $1,468$ sessions).
- **Daily Predictive Forecast:**
  For each evaluation session $t$ in month $M$:
  $$\hat{r}_{13, t} = \hat{\alpha}_M + \hat{\beta}_M \cdot r_{1, t}$$
  where $r_{1, t}$ is the first-half-hour return available at 10:00:00 ET.
- **Historical-Mean Benchmark:**
  For each evaluation session $t$:
  $$\bar{r}_{13, t} = \frac{1}{N_{t-1}} \sum_{s < t} r_{13, s}$$
  Updates daily strictly through session $t-1$ (zero intra-day or forward lookahead).
- **Out-of-Sample $R^2_{OS}$ Metric:**
  $$R^2_{OS} = 1 - \frac{\text{SSE}_{\text{model}}}{\text{SSE}_{\text{benchmark}}} = 1 - \frac{\sum_{t=1}^{750} (r_{13, t} - \hat{r}_{13, t})^2}{\sum_{t=1}^{750} (r_{13, t} - \bar{r}_{13, t})^2}$$

---

## 4. Empirical OOS Results & Point Estimates

| Diagnostic Metric | Empirical Value | Methodology & Canonical Interpretation |
| :--- | :---: | :--- |
| **Initial Estimation Sample ($T_{train}$)** | **739** | Qualified sessions 2017-01-04 through 2019-12-31 |
| **Evaluation Sample ($T_{eval}$)** | **750** | Qualified sessions 2020-01-02 through 2022-12-30 |
| **Evaluation Count (2020)** | **251** | Regular sessions meeting all data contract gates |
| **Evaluation Count (2021)** | **250** | Regular sessions meeting all data contract gates |
| **Evaluation Count (2022)** | **249** | Regular sessions meeting all data contract gates |
| **Monthly OLS Fits ($N_{fits}$)** | **36** | Exactly one fit per calendar month in 2020–2022 |
| **Estimation Sample Size Range** | **[739, 1468]** | Expanding window: Jan 2020 (739) to Dec 2022 (1,468) |
| **Sum of Squared Errors (Model)** | **0.016487341748067845** | $\sum_{t} (r_{13, t} - \hat{r}_{13, t})^2$ |
| **Sum of Squared Errors (Benchmark)** | **0.015726822954313234** | $\sum_{t} (r_{13, t} - \bar{r}_{13, t})^2$ |
| **Root Mean Squared Error (Model)** | **0.004688616249039489** | $\sqrt{\text{SSE}_{\text{model}} / 750}$ |
| **Root Mean Squared Error (Benchmark)** | **0.004579202689597573** | $\sqrt{\text{SSE}_{\text{benchmark}} / 750}$ |
| **Out-of-Sample $R^2_{OS}$** | **-0.048358069265733747** | **$1 - \text{SSE}_{\text{model}} / \text{SSE}_{\text{benchmark}}$ (-4.836%)** |
| **Mean Model Forecast** | **-0.000042495660696730** | Average predicted last-half-hour return |
| **Mean Actual $r_{13}$ (2020–2022)** | **-0.000121954668599038** | Average realized last-half-hour return |

---

## 5. Methodological & Econometric Interpretation

1. **Predictive Performance ($R^2_{OS} < 0$):**
   The Campbell-Thompson out-of-sample diagnostic yields $R^2_{OS} = -0.048358069265733747$ (-4.836%). Because $R^2_{OS} < 0$, the sum of squared forecast errors from the expanding OLS model exceeds that of the simple expanding historical mean benchmark over the 2020–2022 evaluation period.
2. **Consistency with In-Sample Finding:**
   This result is theoretically and empirically congruent with the in-sample replication result from Step R3:
   - In-sample $R^2 = 0.002641$ (0.264%), $\hat{\beta} = +0.022489$, $p = 0.523533$.
   - When the in-sample linear relationship is statistically indistinguishable from zero, parameter estimation variance typically causes out-of-sample recursive forecasts to underperform the historical mean benchmark, yielding slightly negative $R^2_{OS}$.
3. **No Secondary Rescue Permitted:**
   Even if $R^2_{OS}$ had been positive, it could not overturn the primary finding. Because $R^2_{OS} is negative, both in-sample significance ($p = 0.5235$) and out-of-sample predictability ($R^2_{OS} = -4.84%$) fail to support contemporary predictive power of $r_1$ for $r_{13}$ on `SPY`.

---

## 6. Point-in-Time Integrity Assertions

Every forecast observation was programmatically verified against strict point-in-time constraints:
- `estimation_window_end < trading_date`: **PASSED (100% of 750 sessions)**.
- `all benchmark history dates < trading_date`: **PASSED (100% of 750 sessions)**.
- Constant monthly parameters: $\hat{\alpha}_M$ and $\hat{\beta}_M$ remained strictly invariant within each calendar month.
- Zero future targets ($r_{13}$) entered monthly estimation.

---

## 7. Lineage and Artifact Coordinates

- **R3 Derived Returns Dataset:** `data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet`
  - SHA-256: `2b37cba80a845102be6a322af7ff12ff34ecd7a7947e10cf663a3bacdd93d8b9`
- **R4 OOS Forecasts Parquet:** `data/parquet/research/HYP_004_MEC0014A_R4_internal_oos_forecasts.parquet`
  - SHA-256: `982c41c38d8394a379a90da3866255012ad104a3504b38c98768a3111dcb42c4`
  - Row Count: `750`
- **Tracked R4 Manifest:** `docs/phase14/manifests/manifest_r4_HYP_004.json`
  - Manifest SHA-256: `d3e5298ccf66da9854bc84c1ca64aeec112c8e907b96f5fd36a2d8e3f194b9a7`
