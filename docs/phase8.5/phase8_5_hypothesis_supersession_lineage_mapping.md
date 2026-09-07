# Phase 8.5 Research Governance: Hypothesis Supersession & Lineage Mapping

> **Document ID:** `LINEAGE-PHASE85-SUPERSESSION-001`  
> **Timestamp:** `2026-09-07T00:05:00+00:00`  
> **Authority:** `AGENTS.md` (Single Canonical Authority, Cryptographic Lineage, Zero Unverified Claims)  
> **Action Type:** `ADMINISTRATIVE NOMENCLATURE NORMALIZATION (GOVERNANCE-CONTROLLED)`  
> **Status:** `SEALED & RATIFIED`  

---

## 1. Executive Summary & Administrative Rationale

This document establishes the official cryptographic and governance lineage mapping for the normalization of the second quantitative research hypothesis in ACASH.

### Rationale for Normalization
During initial Step R1 design and pre-registration, the higher-timeframe EURUSD time-series momentum hypothesis was designated using the descriptive identifier `HYP_TSMOM_EURUSD_HTF_001`. While descriptive, this identifier did not explicitly encode sequential hypothesis ordinality (`HYP_002`), introducing potential lineage confusion with `HYP_001` (`HYP_TSMOM_EURUSD_001`) or future hypotheses (`HYP_003`, `HYP_004`).

To ensure absolute lineage transparency across automated agents and human contributors:
- The canonical active identifier is normalized to: **`HYP_TSMOM_EURUSD_HTF_002`** (representing **`HYP_002`**).
- The provisional identifier `HYP_TSMOM_EURUSD_HTF_001` is classified as **`SUPERSEDED ADMINISTRATIVE IDENTIFIER`**.
- The prior sealed artifact and its cryptographic digests are **preserved intact** as historical audit evidence, preventing silent revisionism.

---

## 2. Cryptographic Lineage & Supersession Mapping

| Governance Property | Superseded Administrative Milestone | Active Canonical Operational Milestone | Status |
| :--- | :--- | :--- | :--- |
| **Hypothesis Ordinal** | `HYP_002` (Provisional / Implicit) | `HYP_002` (Explicit Sequential Ordinal) | **VERIFIED** |
| **Hypothesis Identifier** | `HYP_TSMOM_EURUSD_HTF_001` | `HYP_TSMOM_EURUSD_HTF_002` | **ACTIVE CANONICAL** |
| **Inception Auth Token** | `AUTH_INCEPTION_HYP_TSMOM_EURUSD_HTF_001_dc9eebd1502d7ed4` | `AUTH_INCEPTION_HYP_TSMOM_EURUSD_HTF_002_fb926a6f495c73a0` | **VERIFIED BOUND** |
| **Proposal SHA-256** | `dc9eebd1502d7ed4701f9c2edc456d927c0bedc8601940ad26ac1bbed2b15714` | `fb926a6f495c73a0dd5c288bac134babe677e1282ff9c6410ab947b553951e95` | **VERIFIED BOUND** |
| **Sealed Hypothesis SHA-256** | `9c8c5e19a87c3780c779c4f4364b80a5f6331c309b011d0318aa5f44cacb8ac9` | `47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe` | **VERIFIED SEALED** |
| **R1 Manifest SHA-256** | `0a5159097cbec296b0d2f66cb735011f96a6ee931d0ef7b795eaa77fedcb2e91` | `d7d4a2b41be6e589357b1140fc3e92e0b70260fe261c01aba8ed32004d3aec8b` | **VERIFIED SEALED** |
| **Sealed Spec File Path** | `./docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_001.json` *(Preserved Archive)* | `./docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_002.json` *(Authoritative)* | **VERIFIED** |
| **R1 Manifest File Path** | `./docs/phase8.5/manifests/manifest_r1_HYP_TSMOM_EURUSD_HTF_001.json` *(Preserved Archive)* | `./docs/phase8.5/manifests/manifest_r1_HYP_TSMOM_EURUSD_HTF_002.json` *(Authoritative)* | **VERIFIED** |

---

## 3. Invariance of Scientific Specification

This normalization represents an administrative identifier adjustment ONLY. Zero scientific parameters were modified:

1. **Target Instrument & Timeframe:** `EURUSD`, `H4` (100% invariant).
2. **Search Space Geometry ($K=12$):**
   - Lookbacks: $[3, 6, 12, 24, 48, 120]$ bars.
   - Deadbands: $[3.0, 6.0]$ bps.
   - Total Trials: Strictly 12 ($6 \times 2 = 12$).
3. **Causal Signal Definition:** Log-return momentum with deadband $\theta$, evaluated at Close($t$) and executed at Open($t+1$).
4. **Target Horizons:** Primary $H=1$, Secondary $H=6$.
5. **Invalidation Criteria:** Strict Boolean conjunction:
   - Rank IC $\ge 0.025$
   - HAC $t$-statistic $\ge 2.00$
   - Autocorrelation $\rho_1 \le 0.98$
   - Net Trade PnL $\ge +1.5$ bps
   - Haircut Sharpe $\ge +0.50$
6. **Data Contract Window:** Calendar window `2021-01-01T00:00:00Z` through `2024-12-31T23:59:59Z` with minimum usable $N \ge 5,000$ H4 bars.
7. **Quarantine Boundary:** Completely disjoint from 2026 M5 holdout.

---

## 4. Operational Invariant Verification

- **Single Active Canonical Authority:** Exactly **one** active hypothesis specification exists for `HYP_002`: [`docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_002.json`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_002.json).
- **No Operational Ambiguity:** All subsequent execution scripts (R2 data preparation, R3 census) must bind strictly to `HYP_TSMOM_EURUSD_HTF_002`.
- **Zero Market Data Touch:** No market data was read or processed during this normalization.
- **Zero Capital Authority:** Capital authority remains strictly hard-locked at **`$0.00`**.
- **Step R2 & Trading Locked:** Step R2 remains strictly `LOCKED`; Phase 13 Step 8/9 remain strictly `LOCKED`.
