# Phase 14 Step R3: HYP_004 Primary Econometric Replication Audit

```text
[STATUS: PRIMARY ECONOMETRIC REPLICATION COMPLETE]
[OUTCOME: PRIMARY_REPLICATION_NOT_ACCEPTED]
[K = 1: SINGLE PRIMARY MODEL]
[SECONDARY ANALYSES STRICTLY LOCKED]
[OOS 2023-2026 STRICTLY SEALED]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true]
```

- **Document ID:** `docs/phase14/phase14_r3_primary_replication_audit_HYP_004.md`
- **Hypothesis:** `HYP_004` (Market Intraday Momentum: Gao Baseline Replication on `SPY`)
- **Mechanism ID:** `MEC-0014A`
- **Starting Git Base:** `6d8a1aa3728bc93cee4197f386671a717164443f`
- **Execution Git HEAD:** `6d8a1aa3728bc93cee4197f386671a717164443f`
- **Execution Timestamp (UTC):** `2026-09-20T08:30:03.081859+00:00`
- **Calendar Authority:** `NyseCa1Calendar`

---

## 1. Upstream Cryptographic Lineage Verification

| Artifact Description | Canonical Filesystem Path | SHA-256 Digest | Precondition Status |
| :--- | :--- | :--- | :--- |
| **HYP_004 Specification** | `docs/phase14/hypotheses/HYP_004.json` | `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d` | VERIFIED MATCH |
| **MEC-0014A Preregistration** | `docs/research/MEC-0014A-statistical-preregistration-draft.md` | `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce` | VERIFIED MATCH |
| **Phase 14 R1 Manifest** | `docs/phase14/manifests/manifest_r1_HYP_004.json` | `eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b` | VERIFIED MATCH |
| **Phase 14 R2 Manifest** | `docs/phase14/manifests/manifest_r2_HYP_004.json` | `25b5ae6c4769064459709bb09bbc759e02f7b340c4d4e94b4ff9442e3082ef71` | VERIFIED MATCH |
| **R2 Endpoint Parquet Dataset** | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` | `096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776` | VERIFIED MATCH |

---

## 2. Sample Census & Derived Return Lineage

- **Total In-Sample Regular Sessions (2017–2022):** 1,498
- **Primary-Regression Eligible Observations ($T$):** **1489**
- **Quarantined Excluded Observations:** 9
  - `AMBIGUOUS_P12_BOUNDARY_PRICE`: 5 sessions (`2017-06-07`, `2017-08-08`, `2017-08-23`, `2017-09-12`, `2021-03-24`)
  - `AMBIGUOUS_P1_BOUNDARY_PRICE`: 3 sessions (`2017-03-31`, `2017-06-02`, `2022-02-14`)
  - `FIRST_SESSION_NO_PRIOR_IN_SAMPLE_CLOSE`: 1 session (`2017-01-03`)

> [!NOTE]
> **Lineage Reconciliation (`EXACT_EXCLUSION_DATE_ENUMERATION_CORRECTED_FROM_LOCAL_HASHED_R2_AUTHORITY`):**
> In the initial drafting of this audit record, 8 ambiguous sessions were errantly enumerated with draft dates (`2017-01-20`, `2017-04-18`, `2017-10-31`, `2018-05-18`, `2020-04-22` and `2017-08-17`, `2019-06-11`, `2021-02-04`). Authoritative local hashed R2 Parquet (`096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776`) and session ledger (`2d07419b1dc9ba34f600e484df17eef90724fc6cbfeb65aa29484b50d8a8ffc2`) establish the true canonical 9 excluded dates above. Because all R3 calculations filtered on `primary_regression_eligible == True` from the hashed R2 Parquet directly, zero empirical calculations were affected.

- **Chronological Date Range:** `2017-01-04` to `2022-12-30`
- **Derived Primary Return Dataset:** `data/parquet/research/HYP_004_MEC0014A_R3_primary_returns.parquet`
- **Derived Return Dataset SHA-256:** `2b37cba80a845102be6a322af7ff12ff34ecd7a7947e10cf663a3bacdd93d8b9`

### Exact Simple Return Specification:
$$r_{1, t} = \frac{p_{1, t}}{p_{0, t}} - 1 = \frac{\text{SIP Trade Price at or before 10:00:00 ET}}{\text{Previous NYSE Arca Qualified Primary Close}} - 1$$
$$r_{13, t} = \frac{p_{13, t}}{p_{12, t}} - 1 = \frac{\text{Current NYSE Arca Qualified Primary Close}}{\text{SIP Trade Price at or before 15:30:00 ET}} - 1$$

---

## 3. Primary Econometric Replication Estimates

| Metric | Estimated Value | Econometric Definition |
| :--- | :---: | :--- |
| **Sample Size ($T$)** | **1489** | Number of eligible regular sessions |
| **HAC Bandwidth ($L$)** | **7** | Newey-West (1994) rule-of-thumb: $\lfloor 4(T/100)^{2/9} \rfloor$ |
| **HAC Kernel** | **Bartlett** | Triangular lag weighting: $w(l, L) = 1 - \frac{l}{L + 1}$ |
| **Intercept ($\hat{\alpha}$)** | **-0.000125752897293718** | $\bar{r}_{13} - \hat{\beta} \bar{r}_1$ |
| **Slope ($\hat{\beta}$)** | **0.022488683629000000** | $\frac{\sum (r_{1, t} - \bar{r}_1)(r_{13, t} - \bar{r}_{13})}{\sum (r_{1, t} - \bar{r}_1)^2}$ |
| **Newey-West HAC Standard Error** | **0.035253777057000000** | Asymptotic square root of HAC variance |
| **HAC $t$-statistic** | **0.637908488282000000** | $\frac{\hat{\beta}}{\text{HAC SE}(\hat{\beta})}$ |
| **Two-Sided Asymptotic $p$-value** | **0.523533251922000000** | $2(1 - \Phi(|t|))$ |
| **In-Sample $R^2$** | **0.002641292938333817** | Unadjusted $1 - \frac{\text{SSE}}{\text{SST}}$ |

---

## 4. Binding Primary Decision Evaluation

- **Preregistered Decision Rule:** $\hat{\beta} > 0 \text{ AND } p < 0.05$ (two-sided Newey-West HAC, $L=7$, $T=1489$)
- **Direction Criterion ($\hat{\beta} > 0$):** **PASS** (Estimated $\hat{\beta} = 0.022488683629000000$)
- **Significance Criterion ($p < 0.05$):** **FAIL** (Estimated $p = 0.523533251922000000$)
- **Primary Binary Replication Outcome:** **`PRIMARY_REPLICATION_NOT_ACCEPTED`**

---

## 5. Execution Governance & Boundary Invariants

1. **Single Primary Model ($K=1$):** Exactly one regression was executed. Zero model searches, zero alternative predictors, zero threshold scans.
2. **Zero Secondary Robustness Analyses Executed:**
   - $r_{12}$ (10:00 to 15:30) was **NOT RUN**.
   - Joint $r_1 + r_{12}$ regression was **NOT RUN**.
   - Log-return specification was **NOT RUN**.
   - Quote-based (bid/ask/midpoint) endpoints were **NOT RUN**.
   - Alternative HAC bandwidths / kernels were **NOT RUN**.
   - Spearman rank IC / Pearson IC were **NOT RUN**.
   - Friction waterfall / cost models were **NOT RUN**.
   - VIX, volume, and macro-event conditioning were **NOT RUN**.
   - Ex-dividend sensitivity was **NOT RUN**.
   - Internal recursive OOS (2020–2022) was **NOT RUN**.
3. **Strict Out-of-Sample Holdout Seal:** Zero queries or data records from $\ge \text{2023-01-01}$ were accessed. External 2023–2026 holdout remains **STRICTLY SEALED**.
4. **Capital & Execution Locks:** Capital remains at **\$0.00**, `NO_REAL_ORDERS = true`, Paper and Live execution remain **STRICTLY LOCKED**.
5. **Human Governance Authority:** The primary replication outcome is sealed for Human contributor review. Step R4 and subsequent phases remain strictly locked pending explicit authorization.
