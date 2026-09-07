# Phase 8.5 Step R3 — In-Sample Search Trial Census & Screening Audit Report (HYP_002)

**Date of Audit:** 2026-09-07  
**Auditor:** Antigravity Automated Verification Agent & Research Governance Engine  
**Governance Phase:** Phase 8.5 (Alpha Research & Strategy Qualification) — Track B  
**Current Step:** Step R3 (In-Sample Search Trial Census & Screening)  
**Target Strategy:** `STRAT-MOM-HTF-H4-V1`  
**Bound Hypothesis:** `HYP_TSMOM_EURUSD_HTF_002` (SHA-256: `47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe`)  
**Canonical Dataset ID:** `DS_EURUSD_H4_2021_2024_CANONICAL` (SHA-256: `c665cbed5f452eca19c0bc4e09edfc7642e1527dd968cbb87a93e229f3a45aed`)  
**Sealed Ledger ID:** `ledger_HYP_TSMOM_EURUSD_HTF_002_20260907T002550Z`  
**Ledger Content Digest (SHA-256):** `d6d627334a1560193c495947e4f9ab3a62e983ac46cba1ef4cf51a1707dd6565`  
**R3 Result Manifest SHA-256:** `809ac530c69745924550723b19b79a7a82bd4182659f6eb2a5cfc4b019c24ccd`  

---

## 1. Executive Summary & Governance Verdict

### Step R3 Census Verdict: **PASS & SEALED** (12/12 Trials Exhaustively Accounted)
### Hypothesis Empirical Outcome: **100% FALSIFIED IN-SAMPLE** (0/12 Trials Qualified)
### Lifecycle State: **TERMINALLY_FALSIFIED**
### Step R4 Status: **GATED / EARLY TERMINATION RECOMMENDED (SCIENTIFICALLY REDUNDANT)**
### Strategy Qualification Status: **BLOCKED / FALSIFIED** (Fails Pre-Registered Criteria)
### Capital Allocation Authority: **$0.00 (Zero Trading Authority Hard-Locked)**
### Phase 13 Runtime Status: **STEP 8 LOCKED (Human GO Required) / STEP 9 NOT AUTHORIZED** (Unchanged)

Step R3 has executed an exhaustive, immutable **12-trial search space census** ($K = 12$) across the pre-registered search geometry:
- Lookbacks: $\mathcal{L} = [3, 6, 12, 24, 48, 120]$ H4 bars ($12\text{ hours}$ to $20\text{ trading days}$)
- Deadbands: $\Theta = [3.0, 6.0]\text{ bps}$
- Primary Horizon: $H = 1$ (Next-bar H4 return)

Execution was conducted exclusively using In-Sample training bars (indices `0` to `3,738`, covering `3,739` bars from `2021-01-03` to `2023-05-30 UTC`).

**Zero data leakage occurred:** Validation window bars (`3,751` to `4,996`) and held-out Out-of-Sample bars (`5,009` to `6,230`), along with their 12-bar embargo buffers (`3,739..3,750` and `4,997..5,008`), remained strictly untouched, unexposed, and pristine. The quarantined 2026 M5 holdout from `HYP_001` also remains untouched.

**Empirical Finding:**
The scientific hypothesis `HYP_TSMOM_EURUSD_HTF_002` (asserting economically tradeable positive time-series momentum in EURUSD at the H4 timeframe) is **decisively falsified by empirical market data**:
- **Rank IC is negative across 10 of 12 trials** ($-0.0103$ to $-0.0384$) and statistically indistinguishable from zero for $L=120$ ($+0.00006$), directly violating the pre-registered minimum hurdle of $+0.025$.
- **HAC $t$-statistics fail completely**, being negative across all 12 trials (ranging from $-0.314$ to $-1.579$, failing the $\ge +2.00$ hurdle).
- **Economic edge after friction is negative** across all 12 trials (average net PnL ranges from $-1.25\text{ bps}$ to $-2.04\text{ bps}$ per trade under the institutional 1.2 bps roundtrip friction model).
- **Annualized Haircut Sharpe is deeply negative** across all 12 trials ($-2.23$ to $-3.68$, failing the $\ge +0.50$ hurdle).
- Under strict anti-HARKing governance, all 12 trials have been sealed in `SearchTrialLedger`. Zero trials were pruned, cherry-picked, or retroactively tuned.

---

## 2. In-Sample Search Trial Census Matrix (12/12 Trials)

All 12 candidate parameter combinations were evaluated against the 5 pre-registered conjunctive qualification gates:
1. $\text{Rank IC} \ge +0.025$
2. $\text{HAC } t\text{-stat} \ge +2.00$ (executed with `HacBandwidthMethod.NEWEY_WEST_PLUGIN`; bandwidth 8 for all trials — see Governance Maintenance Annotation, Sec. 5)
3. $\text{Signal Autocorrelation } (\rho_1) \le 0.98$
4. $\text{Net Average PnL} \ge +1.50\text{ bps}$
5. $\text{Haircut Annualized Sharpe} \ge +0.50$

| Trial ID | Lookback $L$ | Deadband $\theta$ | Obs $N$ | Active Trades | Spearman Rank IC | HAC $t$-stat | Autocorr $\rho_1$ | Net PnL (bps/trade) | Haircut Sharpe (Ann.) | Conjunctive Gate Verdict |
|:---------|:------------:|:-----------------:|:-------:|:-------------:|:----------------:|:------------:|:-----------------:|:-------------------:|:---------------------:|:------------------------:|
| `TRIAL-01` | 3 | 3.0 bps | 3,735 | 3,412 | $-0.0321$ | $-1.579$ | $0.4594$ [P] | $-1.765$ | $-3.222$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-02` | 3 | 6.0 bps | 3,735 | 3,089 | $-0.0321$ | $-1.579$ | $0.4821$ [P] | $-1.635$ | $-2.943$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-03` | 6 | 3.0 bps | 3,732 | 3,519 | $-0.0384$ | $-1.093$ | $0.6637$ [P] | $-1.642$ | $-2.972$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-04` | 6 | 6.0 bps | 3,732 | 3,309 | $-0.0384$ | $-1.093$ | $0.6823$ [P] | $-1.610$ | $-2.942$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-05` | 12 | 3.0 bps | 3,726 | 3,561 | $-0.0314$ | $-1.235$ | $0.7413$ [P] | $-2.043$ | $-3.677$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-06` | 12 | 6.0 bps | 3,726 | 3,411 | $-0.0314$ | $-1.235$ | $0.7643$ [P] | $-1.952$ | $-3.507$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-07` | 24 | 3.0 bps | 3,714 | 3,617 | $-0.0240$ | $-1.017$ | $0.8390$ [P] | $-1.381$ | $-2.496$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-08` | 24 | 6.0 bps | 3,714 | 3,515 | $-0.0240$ | $-1.017$ | $0.8550$ [P] | $-1.389$ | $-2.495$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-09` | 48 | 3.0 bps | 3,690 | 3,603 | $-0.0103$ | $-1.299$ | $0.8676$ [P] | $-1.561$ | $-2.820$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-10` | 48 | 6.0 bps | 3,690 | 3,523 | $-0.0103$ | $-1.299$ | $0.8803$ [P] | $-1.584$ | $-2.852$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-11` | 120 | 3.0 bps | 3,618 | 3,574 | $+0.0001$ | $-0.314$ | $0.9374$ [P] | $-1.248$ | $-2.246$ | **DISQUALIFIED (FAIL)** |
| `TRIAL-12` | 120 | 6.0 bps | 3,618 | 3,532 | $+0.0001$ | $-0.314$ | $0.9425$ [P] | $-1.245$ | $-2.234$ | **DISQUALIFIED (FAIL)** |

---

## 3. Empirical Autopsy: Why Was HTF Momentum Falsified?

1. **Failure of Unconditional Momentum at Intermediate Horizons:**
   Under `HYP_002`, which tested univariate unconditional price momentum on EURUSD H4, the In-Sample Census does not support the momentum hypothesis. For lookbacks $L \in [3, 6, 12, 24, 48]$ bars ($12\text{ hours}$ to $8\text{ days}$), the Spearman Rank IC is negative ($-0.010$ to $-0.038$) and HAC $t$-statistics are negative ($-1.01$ to $-1.58$).
   *Epistemic Boundary Note:* This empirical result decisively falsifies `HYP_002`'s directional momentum thesis, but it is **NOT** evidence that "EURUSD H4 is universally mean-reverting." Proving mean-reversion would require a separate, pre-registered, conditioned hypothesis rather than an unverified extrapolation from a failed momentum test.
2. **Signal Decays to Zero at Longer Horizons:**
   At $L = 120$ bars ($20\text{ trading days}$ / 1 month), the Rank IC is $+0.00006$, indicating that unconditioned trailing returns have zero linear or monotonic predictive power over subsequent 4-hour price moves.
3. **Transaction Friction Accumulation:**
   Even at an institutional friction of $1.2\text{ bps}$ roundtrip (spread $0.4\text{ bps}$, commission $0.5\text{ bps}$, slippage $0.3\text{ bps}$), constant position flipping across 3,000+ trades drains between $1.25\text{ bps}$ and $2.04\text{ bps}$ per trade.
4. **Conjunctive Gate Failure:**
   Zero out of 12 candidate specifications met the statistical or economic performance hurdles (only the stationarity constraint $\rho_1 \le 0.98$ was satisfied).

---

## 4. Governance Ledger & Cryptographic Integrity

- **Sealed Ledger:** `ledger_HYP_TSMOM_EURUSD_HTF_002_20260907T002550Z`
- **Sealed Digest:** `d6d627334a1560193c495947e4f9ab3a62e983ac46cba1ef4cf51a1707dd6565`
- **R3 Manifest:** `docs/phase8.5/manifests/r3_manifest_HYP_TSMOM_EURUSD_HTF_002.json`
- **R3 Manifest Digest:** `809ac530c69745924550723b19b79a7a82bd4182659f6eb2a5cfc4b019c24ccd`

### Boundary & Cross-Hypothesis Data Quarantine Enforcements:
- **Validation Partition (`3751..4996`):** Untouched, pristine, and **QUARANTINED** (NOT reusable for `HYP_003` by default).
- **Blind OOS Partition (`5009..6230`):** Untouched, pristine, and **QUARANTINED** (NOT reusable for `HYP_003` by default).
- **2026 M5 Holdout (`6060..9999`):** Untouched, pristine, and **QUARANTINED**.
- **Capital Authority:** Strictly hard-locked at `$0.00`.
- **Trading Authority:** Strictly `LOCKED`.
- **Broker Connection:** Strictly `NONE / DISCONNECTED`.

---

## 5. Governance Maintenance Annotations (Recorded Under STEP-G Closure)

The following annotations are **governance-maintenance records only**. They do not modify, recompute, or re-open any historical HYP_002 result. All sealed digests above remain binding and unchanged.

### 5.1 HAC Bandwidth Method — Documentation vs. Executed Implementation

- **Pre-registration design documentation** (`HYP_TSMOM_EURUSD_HTF_002_design.md`) references the Andrews (1991) AR(1) automatic plug-in bandwidth selection.
- **Executed R3 implementation** (`scripts/execute_phase8_5_step_r3_census_htf.py`) used `HacBandwidthMethod.NEWEY_WEST_PLUGIN` (Newey-West 1994 rule-of-thumb `floor(4 * (T / 100)^(2/9))`), which yields bandwidth `8` for every in-sample trial (`T_eff ∈ [3618, 3735]`).
- **Governance decision:** the executed method stands as the authoritative R3 method; the design-doc reference is recorded as a documentation deviation, not silently rewritten. No empirical re-run is required or permitted. Because all 12 HAC $t$-statistics are negative and far below the `+2.00` conjunctive hurdle, the method difference cannot overturn the verdict.

### 5.2 "Haircut Sharpe" Terminology — Canonical Mapping

The R3 report field rendered as **"Haircut Sharpe (Annualized)"** is **NOT** the canonical Phase-6 multiple-testing-adjusted Haircut Sharpe. These must never be conflated:

| Term | Definition | Space |
| :--- | :--- | :--- |
| R3 field `haircut_sharpe_annualized` / ledger `in_sample_sharpe` | Undeflated annualized in-sample Sharpe `mean / std(ddof=1) × √1512` computed over active-trade net returns in R3 only. **No Bonferroni/DSR deflation applied.** | ANNUAL |
| Canonical Haircut Sharpe (`MultipleTestingEngine.calculate_bonferroni_haircut_sharpe`) | Multiple-testing-adjusted Sharpe via Bonferroni tail-probability inversion ($|t_{adj}|/\sqrt{T} \times \sqrt{ann}$). Applied at Phase 6 / R4 statistical validation gates. | ANNUAL (and PERIOD) |

- R3 executed the **undeflated annualized** quantity. This is a recognized terminology seam, preserved as-is for historical R3 artifacts.
- HYP_002 was falsified on Rank IC, HAC $t$-stat, and Net PnL across all 12 trials, so no retroactive haircut value is manufactured and the terminal verdict is unaffected.
