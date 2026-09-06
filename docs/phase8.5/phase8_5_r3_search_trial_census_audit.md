# Phase 8.5 Step R3 — In-Sample Search Trial Census & Screening Audit Report

**Date of Audit:** 2026-09-06  
**Auditor:** Antigravity Automated Verification Agent & Research Governance Engine  
**Governance Phase:** Phase 8.5 (Alpha Research & Strategy Qualification) — Track B  
**Current Step:** Step R3 (In-Sample Search Trial Census & Screening)  
**Target Strategy:** `STRAT-MOM-MULTI-HORIZON-V1`  
**Bound Hypothesis:** `HYP_TSMOM_EURUSD_001` (SHA-256: `5afb92d7175721872d51ab82b2ebaaaa353c2d21bcbbd596e8bf1a3c52de0ef4`)  
**Sealed Ledger ID:** `LEDGER_TSMOM_EURUSD_001_IN_SAMPLE`  
**Ledger Content Digest (SHA-256):** `b1185c4f26d4934e930d526b66d7f3e8786bdbb6c24c263957f9288aa4072b43`  

---

## 1. Executive Summary & Governance Verdict

### Step R3 Census Verdict: **PASS & SEALED** (9/9 Trials Exhaustively Accounted)
### Hypothesis Empirical Outcome: **100% FALSIFIED IN-SAMPLE** (0/9 Trials Qualified)
### Step R4 Status: **GATED / AWAITING GOVERNANCE DIRECTION**
### Strategy Qualification Status: **BLOCKED / FALSIFICATION IMMINENT** (Fails Pre-Registered Criteria)
### Phase 13 Runtime Status: **STEP 8 LOCKED (Human GO Required) / STEP 9 NOT AUTHORIZED** (Unchanged)

Step R3 has executed an exhaustive, immutable **9-trial search space census** ($K = 9$) across the pre-registered lookback universe $\mathcal{L} = [2, 3, 5, 8, 13, 21, 34, 55, 89]$ exclusively using In-Sample training bars (indices `0` to `5,999`, covering `2026-07-20T03:40:00+00:00` to `2026-08-17T23:40:00+00:00 UTC`).

**Zero data leakage occurred:** Validation window bars (`6,060` to `7,999`) and held-out Out-of-Sample bars (`8,060` to `9,999`), along with their 60-bar embargo buffers, remained strictly untouched and unexposed.

**Empirical Finding:**
The scientific hypothesis `HYP_TSMOM_EURUSD_001` (asserting positive intraday trend-following momentum in EURUSD M5) is **decisively falsified by empirical market data**:
- **Rank IC is negative across all 9 lookbacks** for both Primary Horizon $H = 1$ ($-0.0126$ to $-0.0468$) and Secondary Horizon $H = 6$ ($-0.0175$ to $-0.0447$), directly violating the pre-registered minimum hurdle of $+0.025$.
- **HAC $t$-statistics fail to reach significance** (ranging from $-1.032$ to $+0.411$, all failing the $\ge +2.00$ hurdle).
- **Economic edge after friction is negative** across all 9 trials (Tier 3 Economic Edge $\approx -2.00\text{ bps}$ per trade under the 2.0 bps roundtrip friction model).
- Under strict anti-HARKing rules, all 9 trials have been sealed in the `SearchTrialLedger`. Zero trials were pruned, cherry-picked, or retroactively tuned.

---

## 2. In-Sample Search Trial Census Matrix (9/9 Trials)

All 9 candidate lookback parameters were evaluated against the 4 pre-registered invalidation thresholds:
1. $\text{Rank IC} \ge +0.025$
2. $\text{HAC } t\text{-stat} \ge +2.00$
3. $\text{Autocorrelation } (\text{Lag } 1) \le 0.98$
4. $\text{Cost-Adjusted Spread Ratio} \ge 1.50$

| Trial ID | Lookback $L$ | Active Bars | Period Sharpe | Ann. Sharpe | Asymptotic $p$-val | Spearman Rank IC ($H=1$) | HAC $t$-stat ($H=1$) | Autocorr (Lag 1) | Tier 3 Net Edge (bps) | Falsification Verdict |
|:---------|:------------:|:-----------:|:-------------:|:-----------:|:------------------:|:------------------------:|:--------------------:|:----------------:|:---------------------:|:---------------------:|
| `trial_l02` | **2** | 3,240 (54.0%) | $-0.0301$ | **$-8.105$** | $0.0198$ | **$-0.0468$** | $-0.815$ | $0.4763$ | $-2.034$ | **FALSIFIED** |
| `trial_l03` | **3** | 3,613 (60.3%) | $-0.0235$ | **$-6.338$** | $0.0685$ | **$-0.0400$** | $-1.032$ | $0.6450$ | $-2.029$ | **FALSIFIED** |
| `trial_l05` | **5** | 4,031 (67.3%) | $-0.0278$ | **$-7.493$** | $0.0313$ | **$-0.0424$** | $-0.880$ | $0.7846$ | $-2.030$ | **FALSIFIED** |
| `trial_l08` | **8** | 4,407 (73.6%) | $-0.0179$ | **$-4.814$** | $0.1666$ | **$-0.0381$** | $-0.656$ | $0.8633$ | $-2.024$ | **FALSIFIED** |
| `trial_l13` | **13** | 4,722 (78.9%) | $-0.0144$ | **$-3.868$** | $0.2666$ | **$-0.0355$** | $-0.617$ | $0.9153$ | $-2.018$ | **FALSIFIED** |
| `trial_l21` | **21** | 4,945 (82.7%) | $-0.0048$ | **$-1.288$** | $0.7117$ | **$-0.0154$** | $+0.087$ | $0.9475$ | $-2.002$ | **FALSIFIED** |
| `trial_l34` | **34** | 5,184 (86.9%) | $+0.0028$ | **$+0.747$** | $0.8305$ | **$-0.0126$** | $+0.296$ | $0.9686$ | $-1.997$ | **FALSIFIED** |
| `trial_l55` | **55** | 5,330 (89.7%) | $-0.0057$ | **$-1.529$** | $0.6616$ | **$-0.0191$** | $+0.411$ | **$0.9816$** | $-1.998$ | **FALSIFIED** |
| `trial_l89` | **89** | 5,433 (91.9%) | $+0.0122$ | **$+3.290$** | $0.3478$ | **$-0.0189$** | $-0.098$ | **$0.9890$** | $-2.000$ | **FALSIFIED** |

*Note on Secondary Horizon ($H=6$ bars / 30 minutes):* Rank IC remained strictly negative across all 9 lookbacks ($-0.0175$ to $-0.0447$), with maximum HAC $t$-stat of $+0.889$.

---

## 3. Empirical Autopsy: Why Was the Hypothesis Falsified?

### 3.1 Intraday Microstructure Mean Reversion vs. Trend Continuation
The economic rationale in `HYP_TSMOM_EURUSD_001` posited that delayed information diffusion and slow capital reallocation across liquidity tiers would produce positive trend continuation in M5 EURUSD bars.

The empirical evidence demonstrates the exact opposite:
1. **Short Horizons ($L = 2$ to $13$ bars / 10 to 65 minutes):**
   - Negative Spearman Rank IC ($\approx -0.040$ to $-0.047$) indicates statistically detectable **intraday mean reversion**.
   - Price advances over 2 to 13 bars are systematically followed by pullbacks on the subsequent bar ($H=1$). A trend-following strategy buying after price rises buys directly into short-term liquidity provider exhaustion and inventory rebalancing.
   - Consequently, annualized Sharpe ratios for short lookbacks are sharply negative ($-8.105$ for $L=2$, $-6.338$ for $L=3$, $-7.493$ for $L=5$).
2. **Intermediate Horizons ($L = 21$ to $55$ bars / 1.75 to 4.6 hours):**
   - The directional edge vanishes into white noise. Rank IC stays negative ($-0.0126$ to $-0.0191$), while Sharpe ratios hover near zero ($-1.288$ to $+0.747$).
   - Autocorrelation of the feature approaches unity ($0.947$ to $0.982$), violating the $0.98$ ceiling at $L=55$.
3. **Long Horizon ($L = 89$ bars / 7.4 hours):**
   - While $L=89$ produces an unadjusted in-sample annualized Sharpe of $+3.290$, its Rank IC remains negative ($-0.0189$), its HAC $t$-statistic is negative ($-0.098$, $p = 0.348$), and its feature autocorrelation reaches $0.9890$, tripping the persistence invalidation limit.
   - More critically, after deducting realistic trading friction (Tier 3 Economic Edge), the net return collapses to $-2.00\text{ bps}$ per trade.

### 3.2 Friction Sensitivity & Waterfall Collapse
Under the pre-registered 3-tier friction model:
- Tier 1 Raw Predictive Edge: near zero ($-0.03\text{ bps}$ to $+0.003\text{ bps}$ per trade)
- Deduct Quoted Spread (1.0 bps) + Broker Commission (0.5 bps) $\to$ Tier 2 Net Edge $\approx -1.50\text{ bps}$
- Deduct Slippage (0.5 bps) $\to$ Tier 3 Economic Edge $\approx -2.00\text{ bps}$

Because the gross edge at the M5 timeframe is orders of magnitude smaller than market friction ($0.003\text{ bps} \ll 2.00\text{ bps}$), the strategy is completely consumed by trading costs.

---

## 4. Cryptographic Lineage & Data Artifacts

### 4.1 Upstream Invariants
- **Hypothesis Specification:** `docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_001.json`
- **Hypothesis Digest:** `5afb92d7175721872d51ab82b2ebaaaa353c2d21bcbbd596e8bf1a3c52de0ef4`
- **Canonical Dataset:** `data/parquet/research/EURUSD_M5_canonical.parquet`
- **Canonical Batch Hash:** `4a98d857c8ebce92aad4a51e5368175a3b5866cb137a82e9a6b055634392d619`

### 4.2 In-Sample Data Isolation
- **Total Dataset Size:** 10,000 bars
- **In-Sample Slice Used:** Strictly bars `0` through `5,999` (6,000 bars)
- **Time Range:** `2026-07-20T03:40:00+00:00` to `2026-08-17T23:40:00+00:00 UTC`
- **Protected Partitions:**
  - Embargo Buffer 1 (bars `6,000` to `6,059`): Unallocated
  - Validation Window (bars `6,060` to `7,999`): **Untouched**
  - Embargo Buffer 2 (bars `8,000` to `8,059`): Unallocated
  - Held-Out Blind OOS (bars `8,060` to `9,999`): **Strictly Blind & Unexposed**

### 4.3 Sealed Search Trial Ledger
- **Ledger ID:** `LEDGER_TSMOM_EURUSD_001_IN_SAMPLE`
- **Sealed Timestamp:** `2026-09-06T15:45:33.376118+00:00`
- **Total Sealed Trials:** 9 / 9
- **Ledger Content Digest (SHA-256):** `b1185c4f26d4934e930d526b66d7f3e8786bdbb6c24c263957f9288aa4072b43`
- **Storage Locations:**
  - Canonical Manifest: `data/manifests/research/search_trial_ledger_HYP_TSMOM_EURUSD_001.json`
  - Mirrored Documentation: `docs/phase8.5/ledgers/search_trial_ledger_HYP_TSMOM_EURUSD_001.json`
  - Census Manifest: `data/manifests/research/manifest_census_HYP_TSMOM_EURUSD_001.json`

### 4.4 Trial Return Series Parquet Files
Each trial's discrete in-sample return series has been computed and stored with its individual SHA-256 bound in the ledger:
1. $L=2$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l02.parquet` (`b05b16b5...`)
2. $L=3$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l03.parquet` (`eb3b3439...`)
3. $L=5$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l05.parquet` (`96d26b61...`)
4. $L=8$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l08.parquet` (`88e8a247...`)
5. $L=13$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l13.parquet` (`1ab7ed0a...`)
6. $L=21$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l21.parquet` (`5903438c...`)
7. $L=34$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l34.parquet` (`6e551062...`)
8. $L=55$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l55.parquet` (`e9de8424...`)
9. $L=89$: `data/parquet/research/trials/returns_trial_tsmom_eurusd_m5_l89.parquet` (`de525868...`)

---

## 5. Epistemic Evidence Classification Matrix

| Dimension | Standard / Finding | Classification | Status |
|-----------|-------------------|:--------------:|:------:|
| **Hypothesis Verification** | Upstream R1 spec and hash `5afb92d7...` verified bit-for-bit | **VERIFIED** | **PASS** |
| **In-Sample Data Boundary** | Bars 0–5,999 used strictly; max timestamp `2026-08-17T23:40:00 UTC` | **VERIFIED** | **PASS** |
| **Zero Future Leakage** | Validation and Blind OOS bars ($\ge 6,000$) completely untouched | **VERIFIED** | **PASS** |
| **Census Completeness** | All 9 pre-registered lookbacks $[2..89]$ evaluated; 0 pruned | **VERIFIED** | **PASS** |
| **Rank IC Falsification** | Rank IC negative across all 9 lookbacks (min hurdle $+0.025$) | **VERIFIED** | **FALSIFIED** |
| **HAC $t$-stat Falsification** | HAC $t$-stat $< +2.00$ across all 9 lookbacks | **VERIFIED** | **FALSIFIED** |
| **Autocorrelation Check** | $L=55$ ($0.9816$) and $L=89$ ($0.9890$) exceed $0.98$ ceiling | **VERIFIED** | **FALSIFIED** |
| **Economic Edge Falsification**| Tier 3 net edge negative ($\approx -2.00\text{ bps}$) after friction | **VERIFIED** | **FALSIFIED** |
| **Ledger Sealing Integrity** | Pydantic model sealed; SHA-256 digest `b1185c4f...` matches | **VERIFIED** | **PASS** |
| **Multiple Testing Accounting**| Upper bound $K=9$ locked in ledger for downstream DSR/FWER | **VERIFIED** | **PASS** |

---

## 6. Governance Implications & Next Steps

### The Value of a Negative Result
In quantitative trading research governed by anti-HARKing and pre-registration principles, **a falsified hypothesis is a successful research outcome**. It mathematically proves that:
1. The proposed edge does not exist under the declared conditions.
2. Production capital is protected from being deployed into a losing strategy.
3. The research platform works as designed — resisting data snooping, cherry-picking, and hindsight bias.

### Governance Options for Step R4:
Under the pre-registered framework:
- **Option A (Formal Rejection at Step R4):** Proceed with Step R4 (Statistical Validation Gate) on the best candidate ($L=89$ or $L=34$) or all 9 trials. The gate will formally evaluate DSR, PBO, and Holm-Bonferroni FWER, emitting a formal `REJECT` verdict. The lifecycle dossier will then be sealed with terminal status `FALSIFIED_REJECTED`.
- **Option B (Early Termination on Falsification):** Halt the qualification track immediately at Step R3 on grounds of complete in-sample invalidation, saving computational overhead and preserving the blind validation/OOS partitions for future research.

In either option:
- `STRAT-MOM-MULTI-HORIZON-V1` **CANNOT** receive qualification for live trading.
- Phase 13 Step 8 (`Human GO`) and Step 9 (`90-Day Paper`) remain strictly **LOCKED**.

---

### Verification Ledger

```markdown
### Verification Ledger
- Implementation Status: COMPLETE
- Contract Enforcement: STRICT FAIL-CLOSED (100% Pre-Registered Invariants Maintained)
- Mathematical Authority: CANONICAL SPEC (Arrow Decimal128, Canonical Series Hashing, Sealed Ledger)
- In-Sample Data Isolation: VERIFIED (Strictly Bars 0-5,999; Bars >= 6,000 Unexposed)
- Census Accounting: VERIFIED (9/9 Trials Recorded; 0 Omissions; Digest b1185c4f...)
- Empirical Result: 100% FALSIFIED IN-SAMPLE (All 9 Trials Failed Pre-Registered Hurdles)
- Local Test Suite: VERIFIED (82 passed in 3.48s)
- Type Checker (MyPy): VERIFIED (Clean)
- Remote CI Status: NOT APPLICABLE
- Step R4 Transition: GATED (Awaiting Governance Direction)
- Strategy Qualification: BLOCKED (Falsification Imminent)
- Phase 13 Step 8/9: LOCKED
```
