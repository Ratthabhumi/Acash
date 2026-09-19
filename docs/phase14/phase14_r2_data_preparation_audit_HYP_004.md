# Phase 14 Step R2: HYP_004 Historical Dataset Preparation & Qualification Audit

```text
[STATUS: HISTORICAL DATASET QUALIFIED & SEALED]
[HYP_004 R2 PASS]
[STEP R3 STRICTLY LOCKED]
[ZERO RETURNS COMPUTED]
[ZERO REGRESSIONS RUN]
[OOS 2023-2026 STRICTLY SEALED]
```

- **Document ID:** `docs/phase14/phase14_r2_data_preparation_audit_HYP_004.md`
- **Hypothesis:** `HYP_004` (Market Intraday Momentum: Gao Baseline Replication on `SPY`)
- **Mechanism ID:** `MEC-0014A`
- **Starting Git HEAD:** `fc5af17f6e335bb25722f142c6bce58e31f38632`
- **Generated UTC:** `2026-09-19T18:45:13.151564+00:00`
- **Calendar Authority:** `NyseCa1Calendar`

---

## 1. Upstream Governance Lineage Verification

| Artifact Description | Canonical Git-Tracked Path | SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| **Preregistration Document** | `docs/research/MEC-0014A-statistical-preregistration-draft.md` | `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce` | VERIFIED MATCH |
| **Sealed Hypothesis (Phase 8.5 Mirror)** | `docs/phase8.5/hypotheses/HYP_004.json` | `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d` | VERIFIED MATCH |
| **Sealed Hypothesis (Phase 14 Mirror)** | `docs/phase14/hypotheses/HYP_004.json` | `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d` | VERIFIED MATCH |
| **R1 Registration Manifest** | `docs/phase14/manifests/manifest_r1_HYP_004.json` | `eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b` | VERIFIED MATCH |

---

## 2. Calendar Session Census & Acquisition Totals

| Year | Regular Sessions (390m) | Completed Raw Acquisition | Candidate Sessions | Excluded First Session |
| :---: | :---: | :---: | :---: | :---: |
| **2017** | 249 | 248 | 248 | 1 (`2017-01-03`) |
| **2018** | 248 | 248 | 248 | 0 |
| **2019** | 249 | 249 | 249 | 0 |
| **2020** | 251 | 251 | 251 | 0 |
| **2021** | 251 | 251 | 251 | 0 |
| **2022** | 250 | 250 | 250 | 0 |
| **TOTAL** | **1,498** | **1,497** | **1,497** | **1** |

- **Total Enumerated Calendar Sessions:** 1,498
- **Total Raw SIP Trade Pages Downloaded / Indexed:** 68100
- **Total Raw SIP Trade Records Processed:** 673,451,966
- **Total Regular-Session SIP Trade Records:** 673,451,966
- **HTTP 429 Responses Encountered:** 0 (Handled via adaptive backoff)
- **Exact Transport Duplicate Records:** 0 (Clean transport integrity)

---

## 3. Session Eligibility & Scientific Exclusion Census

- **Primary-Regression Eligible Sessions:** 1489
- **Total Excluded Sessions:** 9

### Exclusion Breakdown

| Exclusion Reason Code | Session Count | Scientific Classification |
| :--- | :---: | :--- |
| `AMBIGUOUS_P12_BOUNDARY_PRICE` | 5 | Preregistered Scientific Rule |
| `AMBIGUOUS_P1_BOUNDARY_PRICE` | 3 | Preregistered Scientific Rule |
| `FIRST_SESSION_NO_PRIOR_IN_SAMPLE_CLOSE` | 1 | Preregistered Scientific Rule |

---

## 4. Provenance & Cryptographic Lineage Manifest

| Artifact Description | Filesystem Path | SHA-256 Digest |
| :--- | :--- | :--- |
| **Canonical Local Dataset (Parquet)** | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` | `096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776` |
| **Local Session Ledger** | `data/manifests/research/HYP_004_R2_session_ledger.json` | `2d07419b1dc9ba34f600e484df17eef90724fc6cbfeb65aa29484b50d8a8ffc2` |
| **Local Raw Page Manifest** | `data/manifests/research/HYP_004_R2_raw_page_manifest.json` | `560815d3cac7230b2449bc814d9520094608633cfa91608b4b55b47ca7f07802` |
| **Raw Evidence Aggregate Digest** | Deterministic page-chain hash | `2e359c58fe949a7f0e5d62c864db6b214ec13da4d8b071a71388e313b4e14386` |
| **Tracked R2 Qualification Manifest** | `docs/phase14/manifests/manifest_r2_HYP_004.json` | `25b5ae6c4769064459709bb09bbc759e02f7b340c4d4e94b4ff9442e3082ef71` |

---

## 5. Absolute Empirical Boundary Statements

1. **Zero Return Computation:** No return ($r_1$ or $r_13$), price ratio, or price subtraction has been evaluated.
2. **Zero Regression Execution:** No slope ($\\beta$), standard error, Newey-West HAC covariance, $t$-statistic, or $p$-value has been computed.
3. **Strict OOS Holdout Seal:** Zero data queries or records from $\ge \text{2023-01-01}$ were accessed.
4. **Capital & Execution Locks:** Capital remains at **\$0.00**, `NO_REAL_ORDERS = true`, Paper and Live execution remain **STRICTLY LOCKED**.
5. **Step R3 Status:** Step R3 remains **LOCKED_PENDING_SEPARATE_HUMAN_AUTHORIZATION**.
