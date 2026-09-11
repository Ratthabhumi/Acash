# MEC-0013 — Opening Range Breakout (ORB) Quantitative Mechanism & Provenance Audit

**Document ID:** `docs/phase14/mec_0013_orb_research_audit.md`
**Object:** Formal scientific, mathematical, claim-provenance, and governance closure audit of mechanism intake MEC-0013 (Opening Range Breakout).
**Status:** `[RESEARCH INTAKE AUDITED & FORMALIZED]` `[DOCUMENTATION-ONLY]` `[ZERO ACASH EMPIRICAL EVIDENCE]` `[NOT A CANDIDATE]` `[NOT HYP_003]` `[NOT R1]` `[ZERO TRADING AUTHORITY]`
**Date:** 2026-09-11  
**Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)  
**Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Implementation Correctness != Mathematical Validity, Single Canonical Authority).  
**ASCII-Only:** Strict ASCII formatting (no non-ASCII bytes).

---

## 1. Executive Summary & Epistemic Boundary

This document provides the canonical scientific, claim-provenance, and microstructural audit of **MEC-0013: Opening Range Price Discovery & Intraday Boundary Dynamics (ORB)**, formalizing the intake deconstructed in [`docs/phase14/mec_0013_orb_research_intake.md`](./mec_0013_orb_research_intake.md).

### Non-Negotiable Epistemic Invariants:
1. **ACASH Empirical Evidence = NONE:** ACASH has executed **zero** backtests, calculated **zero** return distributions, and derived **zero** statistical performance metrics for MEC-0013.
2. **Strict Separation of Claim, Literature, and ACASH Findings:**
   - `[SOURCE CLAIM]`: Unverified assertions from retail trading infographics / marketing lore.
   - `[EXTERNAL LITERATURE]`: Peer-reviewed academic findings and published empirical studies on specific historical markets/samples (not conducted by ACASH).
   - `[ANALYTICAL MODEL]`: Mathematical and theoretical models formulated to make concepts testable.
   - `[ACASH EMPIRICAL EVIDENCE]`: Empirical findings produced by ACASH's sealed trial ledger. For MEC-0013, this is strictly **EMPTY**.
3. **Data Authority Blocker at $0:** Point-in-time, multi-year consolidated 1-minute intraday data with authoritative opening auction prints and market-wide volume for US equities is **UNAVAILABLE at $0.00**.
4. **Governance Standing:** Per ratified human decision **MEC-0013-D01 = OPTION C**, MEC-0013 is formally **ARCHIVED AS AN AUDITED RESEARCH ASSET**. It is **NOT PROMOTED** to a candidate, does **NOT** create `HYP_003`, and its backtest status remains **STRICTLY LOCKED**.

---

## 2. Claim Provenance & Empirical Citation Audit

To eliminate unverified assertions and comply with `AGENTS.md #1 Zero Unverified Claims`, every quantitative or empirical-sounding statement cited in the intake is audited and classified below:

| Claim Description | Cited / Contextual Origin | Sample / Market / Period | Epistemic Classification | ACASH Transferability & Audit Assessment |
|---|---|---|---|---|
| **"ORB provides high-probability, higher win-rate trend entries"** | Retail trading infographic / social trading lore | Undefined / discretionary chart anecdotes | **E: UNVERIFIED / DOWNGRADED** | Pure retail lore. Zero statistical sample, zero error-rate control, zero scientific validity. Must be completely excluded from quantitative analysis. |
| **"Crabel ORB profitability in commodity futures"** | Crabel, T. (1990) *Day Trading with Short Term Price Patterns* | US Pit-traded Commodity Futures (1980s) | **B: SOURCE-REPORTED (HISTORICAL / NON-TRANSFERABLE)** | Observed in manual open-outcry pit trading 35+ years ago. Non-transferable to modern electronic equity/ETF markets with algorithmic execution and fragmented venues. |
| **"ORB profitability decay in equity & futures markets"** | Holmberg, Lönnbark, & Lundström (2013); Ni, Lee, & Liao (2015) | Nordic equities (OMX); Taiwan Index Futures (TX) (2000–2014) | **A: DIRECTLY SUPPORTED BY CITED SOURCE** | Valid academic finding: documents gross statistical edge in early electronic eras that deteriorated significantly over time and evaporated after transaction costs. |
| **"Naive 15m ORB win rate ~51-53%, PF ~1.01-1.04, net expectancy -0.02R to +0.01R"** | Third-party retail/practitioner backtest aggregators & simulation summaries | US Equities / SPY simulations (2020–2024 reported) | **B: SOURCE-REPORTED CONTEXTUAL CLAIM (NON-CANONICAL)** | **NOT ACASH EVIDENCE.** Reported in third-party backtest summaries under specific arbitrary order-fill rules. Downscaled from empirical fact to external contextual observation. ACASH has not verified this dataset. |
| **"0DTE option dealer gamma hedging induces mean-reverting pin forces"** | Contemporary market microstructure literature (SSRN 2023–2026 working papers on 0DTE flow) | US S&P 500 Index / SPX options market (2022–2026) | **B: LITERATURE-REPORTED THEORETICAL MECHANISM** | Established theoretical and empirical finding in derivatives microstructure: positive dealer gamma dampens realized intraday volatility, combating naive directional breakout momentum. |
| **"1.0 to 1.6 bps roundtrip execution hurdle on SPY"** | Analytical spread + fee schedule derivation (Section 7) | S&P 500 ETF (SPY) at $500 nominal share price | **C: THEORETICAL ILLUSTRATIVE COST MODEL (NON-EMPIRICAL)** | **NOT ACASH EMPIRICAL EVIDENCE.** This is an analytical estimation based on nominal spread widths ($0.01–$0.02), exchange/regulatory fee schedules, and modest slippage assumptions. It is NOT measured from real broker fill reports. |

---

## 3. Mechanism Deconstruction & Observable Market Objects

Practitioner chart lore is converted into deterministic mathematical objects:

```
+-----------------------------------------------------------------------------+
| Category A: SOURCE CLAIM (Subjective Narrative)                             |
| - "ORB gives higher probability entries"                                    |
| - "VWAP confirms smart money accumulation"                                  |
| - "Liquidity sweeps hunt retail stops"                                      |
+-----------------------------------------------------------------------------+
                                     │  (Purged of motive / lore)
                                     ▼
+-----------------------------------------------------------------------------+
| Category B: OBSERVABLE MARKET OBJECT (Deterministic Mathematical Geometry)  |
| - Opening Range High: OR_high = max(High_t) for t in [09:30, 09:45]         |
| - Opening Range Low:  OR_low  = min(Low_t)  for t in [09:30, 09:45]         |
| - Normalized Range Width: OR_width_pct = (OR_high - OR_low) / P_open        |
| - Boundary Breach: Close_t > OR_high or Close_t < OR_low                    |
| - VWAP Distance: Close_t - VWAP_t                                           |
| - Range Violation & Re-entry: Breach outside boundary followed by close     |
|   back inside range within delta_t                                          |
+-----------------------------------------------------------------------------+
                                     │  (Formulated as neutral hypotheses)
                                     ▼
+-----------------------------------------------------------------------------+
| Category C: ACASH RESEARCH HYPOTHESIS (Unproven Empirical Questions)        |
| - H0: E[R_{t+h} | Close_t > OR_high] = E[R_{t+h}] (No directional drift)     |
| - H1: VWAP alignment increases conditional information coefficient          |
| - H2: Range violation and re-entry exhibits conditional mean-reverting drift|
+-----------------------------------------------------------------------------+
```

---

## 4. Market & Instrument Boundaries

- **Supported Context:** US Cash Equities and major Index ETFs (e.g. `SPY`, `QQQ`) during Regular Trading Hours (09:30:00–16:00:00 ET).
- **Excluded Contexts:**
  - *CME Futures (ES, NQ):* Continuous 23-hour trading session; open represents a volume influx rather than overnight price discovery uncross.
  - *Spot Forex:* Decentralized OTC structure; lacks a centralized auction print or official opening cross volume.
  - *Cryptocurrency:* 24/7 continuous trading; arbitrary UTC calendar boundaries lack physical opening uncross dynamics.
- **Rule:** Literature findings cannot be generalized across asset classes. MEC-0013 applies exclusively to regular cash session equities/ETFs.

---

## 5. Session Boundaries & Calendar Authority

- **Timezone Authority:** All internal timestamps strictly normalized to **UTC**.
- **Regular Trading Hours (RTH):**
  - Session Open: `09:30:00 Eastern Time` (14:30:00 UTC EDT / 13:30:00 UTC EST).
  - Session Close: `16:00:00 Eastern Time` (21:00:00 UTC EDT / 20:00:00 UTC EST).
  - Pre-market (04:00–09:30 ET) and Post-market (16:00–20:00 ET) are **EXCLUDED** from opening range boundary calculations.
- **Session Calendar:** Must adhere to **CA-1 (NYSE Session Authority)**:
  - Half-days (13:00 ET closes) and market-wide halts require explicit fail-closed handling.
- **Auction vs. Continuous Print:**
  - The opening bar `09:30:00` must explicitly declare whether its Open price reflects the official consolidated opening cross auction print or the first continuous match.

---

## 6. Mathematical Signal Specifications (Deterministic)

### 6.1 Range Boundaries
For session date $d$ and opening window $\Delta T_{\text{OR}} = 15\text{m}$:
$$T_{\text{OR}}(d) = [09:30:00\text{ ET}, 09:45:00\text{ ET}]$$
$$\text{OR}_{\text{high}}(d) = \max_{t \in T_{\text{OR}}(d)} \text{High}_t, \quad \text{OR}_{\text{low}}(d) = \min_{t \in T_{\text{OR}}(d)} \text{Low}_t$$
$$\text{OR}_{\text{width\_pct}}(d) = \frac{\text{OR}_{\text{high}}(d) - \text{OR}_{\text{low}}(d)}{\text{Open}_{09:30}(d)}$$

### 6.2 Event Classification
To eliminate multiple-testing recursion and dependent serial correlation:
- **`FIRST_BREAK_UP`:** Earliest bar index $t_1 > 09:45:00\text{ ET}$ where $\text{Close}_{t_1} > \text{OR}_{\text{high}}(d)$, provided no prior breach occurred on session $d$.
- **`FIRST_BREAK_DOWN`:** Earliest bar index $t_1 > 09:45:00\text{ ET}$ where $\text{Close}_{t_1} < \text{OR}_{\text{low}}(d)$, provided no prior breach occurred on session $d$.
- **`RECURRENT_BREACH`:** Excluded from primary statistical analysis due to heavy auto-correlation and multiple-testing distortion.

### 6.3 VWAP Conditioning
$$\text{VWAP}_t = \frac{\sum_{i=09:30}^t P_{\text{typical}, i} \cdot V_i}{\sum_{i=09:30}^t V_i}$$
State: $\text{Sign}(\text{Close}_t - \text{VWAP}_t) \in \{+1, -1, 0\}$.

---

## 7. Cost Model Audit & Frictional Breakeven Barrier

### 7.1 Analytical Cost Model Audit `[NON-CANONICAL / ILLUSTRATIVE]`
The reported 1.0–1.6 bps roundtrip hurdle is audited as an **illustrative analytical construct**, not measured empirical slippage:
- Nominal SPY Share Price: $500.00
- Baseline Spread ($0.01 to $0.02): 0.2 to 0.4 bps per leg $\implies$ 0.4 to 0.8 bps roundtrip.
- Adverse Breakout Slippage: Market/stop orders executing into expanding momentum fill 0.2 to 0.4 bps beyond boundary $\implies$ 0.4 to 0.8 bps roundtrip.
- Regulatory & Clearing Fees (SEC, FINRA TAF, clearing): ~$0.01 per share $\implies$ ~0.2 bps roundtrip.
- **Total Illustrative Hurdle:** $\approx 1.0\text{ to }1.8\text{ bps}$ roundtrip.
- **Audit Caveat:** ACASH has not executed live or paper trades on SPY ORB breakouts. This cost hurdle is a theoretical boundary demonstrating that any gross statistical edge below ~2.5 bps is economically unviable.

---

## 8. Data Requirements & $0 Feasibility Blocker

| Source | Resolution | Historical Depth | Consolidation Quality | Feasibility Status |
|---|---|---|---|---|
| **Yahoo Finance** | 1-minute | Trailing 30 calendar days | Unofficial / uncontracted | `[REJECT]` (Sample size $N < 25$ days; statistically underpowered) |
| **Stooq (`S-10`)** | Daily | Multi-decade | Daily only / WAF gated | `[REJECT]` (No intraday data) |
| **Alpha Vantage Free (`S-11`)** | 1-minute | Trailing 1–2 months | Rate-limited (25 req/day) | `[REJECT]` (Truncated history) |
| **Alpaca Free Market Data** | 1-minute | Multi-year | IEX only (~2-3% volume) | `[REJECT]` (Volume invalid; distorts VWAP and opening auction) |
| **FirstRate Data / Databento / Polygon** | 1-minute | 10–20+ years | Consolidated SIP | `[PAID / COMMERCIAL]` (Requires budget authorization) |

**Definitive Data Authority Blocker:**
Multi-year, point-in-time 1-minute consolidated (SIP) equity intraday data **does not exist at $0.00**.

---

## 9. Parameter Search Space & Anti-HARKing Protocol

- **Full Combinatorial Space:** 7 parameters ($P_1$: OR length, $P_2$: Confirmation, $P_3$: Buffer, $P_4$: VWAP, $P_5$: Horizon, $P_6$: Stop loss, $P_7$: Width filter) yield $K = 5,184$ combinations.
- **Statistical Significance Penalty:** Uncontrolled exploration of 5,184 trials mandates a Holm FWER critical threshold $p \le 9.64 \times 10^{-6}$ and a Deflated Sharpe Ratio penalty requiring observed Sharpe $> 2.8$.
- **Anti-HARKing Invariant:** Any future pre-registration must strictly freeze an ex-ante minimal grid ($K \le 6$) to preserve statistical test validity.

---

## 10. MEC-0013 Final Closure Record

In accordance with human decision **`MEC-0013-D01 = OPTION C`**, the research intake for MEC-0013 is formally closed and archived:

```
===============================================================================
MEC-0013 FINAL GOVERNANCE CLOSURE RECORD
===============================================================================
1. Status:                  RESEARCH INTAKE AUDITED & FORMALIZED (ARCHIVED)
2. Research Readiness:       CONDITIONALLY AUDITED / EMPIRICALLY BLOCKED
3. Candidate Standing:       NOT PROMOTED to free_data_research_registry.md
4. Hypothesis Standing:      NOT HYP_003 (HYP_003 remains ABSENT)
5. Inception Gate R1:        NOT INVOKED / NOT AUTHORIZED
6. Empirical Backtest:       STRICTLY LOCKED
7. Data Authority State:     BLOCKED AT $0.00
8. Primary Closure Reason:   No authoritative multi-year PIT 1-minute intraday
                             dataset available under current $0.00 policy.
9. ACASH Empirical Evidence: NONE (Zero backtests, zero Sharpe, zero win rates).
10. Epistemic Assessment:    Mechanism is theoretically formalized; it is neither
                             empirically validated nor empirically falsified.
===============================================================================
```

### Future Reopening Conditions:
MEC-0013 shall remain archived and **SHALL NOT** be reopened automatically. Reopening requires at least one of the following explicit human governance events:
1. Human Governance authorizes a commercial data budget to procure certified consolidated 1-minute SIP historical data.
2. A newly discovered, verified, point-in-time authoritative $0 intraday data source is validated and admitted to the source registry.
3. A formal methodology change (e.g. testing daily opening gap behavior instead of 1-minute intraday bars) is pre-registered and approved.

---

### Verification Ledger
- Implementation Status: COMPLETE (Final claim-provenance audit and formal closure)
- Contract Enforcement: STRICT FAIL-CLOSED (Zero empirical claims, zero parameter tuning, zero backtesting)
- Mathematical Authority: CANONICAL LITERATURE & MICROSTRUCTURE THEORY
- Local Test Suite / MyPy: NOT RUN (Documentation-only artifact)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: All external win rates, profit factors, and cost hurdles are classified as non-canonical external literature claims or illustrative models. ACASH empirical evidence for MEC-0013 is strictly NONE.
