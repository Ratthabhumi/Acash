# Research Hypothesis Design Draft: EURUSD Higher-Timeframe Time-Series Momentum (HYP_002)

> **Document ID:** `DESIGN-HYP-TSMOM-EURUSD-HTF-001`  
> **Timestamp:** `2026-09-06T23:38:00+00:00`  
> **Classification:** `DESIGN PROPOSAL DRAFT ONLY — NOT REGISTERED — NOT SEALED`  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Honest Scientific Skepticism)  
> **Status:** `READY FOR HUMAN R1 REVIEW`  
> **Governing Gate:** `ResearchReInceptionGate` (R1 Entry Control)  

---

## 1. Governance Affirmations & Boundary Notice

### Strict Non-Execution Boundaries
- **No Market Data Accessed:** Zero market-data files were opened, read, or inspected during the drafting of this proposal.
- **No Empirical Research Executed:** Zero backtests, regressions, or statistical calculations were performed.
- **No Hypothesis Registered:** This document is a **design specification draft only**. It has NOT been submitted to `ResearchReInceptionGate`, and no sealed JSON file has been written to `docs/phase8.5/hypotheses/`.
- **Zero Holdout Exposure:** The quarantined M5 holdout (bars 6,060..9,999 from `HYP_TSMOM_EURUSD_001`) remains **100% unexposed and pristine**.
- **Immutable Prior Falsification:** `HYP_TSMOM_EURUSD_001` remains permanently closed in `TERMINALLY_FALSIFIED` state.
- **Capital Authority:** Strictly hard-locked at **`$0.00`**.
- **Phase 13 Step 8/9:** Strictly **LOCKED / NOT AUTHORIZED**.

---

## 2. Hypothesis Identity & Research Question

### 2.1 Candidate Hypothesis Identity
- **Candidate Hypothesis ID:** `HYP_TSMOM_EURUSD_HTF_001`
- **Candidate Version:** `1.0.0`
- **Target Instrument:** `EURUSD`
- **Asset Class:** Foreign Exchange Spot / Institutional ECN Standard

### 2.2 Core Research Question
$$\begin{aligned}
&\text{\textit{“Does EURUSD exhibit economically meaningful positive time-series momentum at higher timeframes}} \\
&\text{\textit{(e.g., H1, H4, D1) where gross price displacements are large enough to comfortably surmount}} \\
&\text{\textit{institutional transaction frictions (spread, commission, and slippage)?”}}
\end{aligned}$$

---

## 3. Honest Epistemic Evaluation & Scientific Rating

### Rating: 6.5 / 10 (Moderate Plausibility, High Empirical Uncertainty)

- **Theoretical Grounding (7.5 / 10):**
  - Canonical financial literature establishes that macro trend following and currency momentum exist over multi-week to multi-month horizons due to delayed price discovery, central bank monetary policy divergence, and gradual institutional capital reallocation (*Moskowitz, Ooi, Pedersen 2012*; *Menkhoff, Sarno, Schmeling, Zhu 2012*).
  - Microstructure friction collapse is mitigated: On M5, average gross moves were ~0.3–0.5 bps, which were obliterated by 2.0 bps roundtrip friction. On H1/H4, average bar ranges are 20–50 bps, providing an expected signal-to-friction ratio of $15:1$ to $30:1$.
- **Empirical Skepticism (5.5 / 10):**
  - EURUSD is the single most liquid macro asset in the world ($>\$1\text{T}$ daily volume). Macro information is disseminated rapidly by global algorithmic market makers.
  - A single currency pair without cross-sectional basket diversification is prone to long, choppy range-bound regimes (e.g. monetary policy convergence between Fed and ECB).
  - **Verdict:** Higher-timeframe momentum is a scientifically sound research question, but its profitability on EURUSD is strictly **NOT PROVEN**. It must be subjected to an exhaustive, un-tweaked in-sample census before any empirical claims are made.

---

## 4. Structural Economic Rationale

### 4.1 Theoretical Drivers of Higher-Timeframe Persistence
1. **Central Bank Monetary Policy Inertia:**
   - Central bank interest rate cycles (Fed vs. ECB) operate over months and quarters, producing prolonged interest rate differential trends.
   - Unlike intraday noise, macro capital flows (corporate FX hedging, real-money asset allocation) unfold over days and weeks.
2. **Gradual Information Diffusion:**
   - Institutional macro market participants do not execute large billion-dollar portfolio rebalances instantaneously; order execution algorithms slice parent orders over multi-day execution horizons (TWAP/VWAP), generating auto-correlated drift at H1/H4 timeframes.
3. **Friction-to-Volatility Asymmetry:**
   - Institutional FX roundtrip transaction costs are relatively fixed ($\approx 1.0\text{ to } 1.8\text{ bps}$).
   - By moving from M5 (bar volatility $\approx 3\text{ bps}$) to H4 (bar volatility $\approx 35\text{ bps}$), the transaction cost hurdle drops from $60\%\text{--}100\%$ of the price move down to $< 5\%$ of the price move.

---

## 5. Candidate Timeframe Universe & Trade-Offs

The research protocol must explicitly freeze the timeframe universe. Two mutually exclusive design options are presented for human operator review:

### Option A: Focused Single-Timeframe Universe (H4 Session Momentum) — *RECOMMENDED*
- **Timeframe:** `H4` (4-hour bars, capturing Asian, European, and US operational sessions).
- **Rationale:** Minimizes multiple testing penalty ($K$ is kept small); bar volatility ($~35\text{ bps}$) is well above friction; eliminates overnight intraday microstructure noise.
- **Search Grid:** 6 lookbacks $\times$ 2 deadbands = **12 total trials** ($K=12$).

### Option B: Multi-Timeframe Universe (H1 and H4 Dual-Scale)
- **Timeframes:** `H1` and `H4` (both evaluated in the search grid).
- **Rationale:** Tests whether trend persistence is scale-invariant across intraday hourly flow and multi-session flow.
- **Penalty:** Increases search trials by $2\times$ ($K=24$), increasing the Deflated Sharpe Ratio (DSR) haircut and Bonferroni/FWER penalty at the statistical validation gate.

---

## 6. Causal Feature Formulation & Label Definition

### 6.1 Feature Definition: Time-Series Return Momentum with Deadband
For bar $t$ at timeframe $\Delta t$, the momentum signal $s_{t, L, \theta}$ over lookback window $L$ is:
$$r_{t, L} = \ln\left(\frac{P_{close, t}}{P_{close, t-L}}\right)$$

$$s_{t, L, \theta} = \begin{cases} 
+1 & \text{if } r_{t, L} > +\theta \\
-1 & \text{if } r_{t, L} < -\theta \\
0 & \text{if } |r_{t, L}| \le \theta
\end{cases}$$

- **Causality Guarantee:** Feature uses prices strictly up to bar $t$ Close.
- **Deadband $\theta$:** Rejects whipsaw micro-oscillations around zero return.

### 6.2 Forward Label Horizons ($H$)
Returns are evaluated at forward horizons $H \in \{1, 6\}$ bars:
- **Primary Horizon ($H=1$):**
  $$R_{t+1 \to t+2} = \frac{P_{open, t+2} - P_{open, t+1}}{P_{open, t+1}}$$
  Executed at bar $t+1$ Open, closed at bar $t+2$ Open (strict next-bar non-anticipation).
- **Secondary Horizon ($H=6$):**
  Multi-bar holding horizon ($6 \times 4\text{h} = 24\text{ hours}$ on H4; $6\text{ hours}$ on H1) with mandatory interval purging and embargo.

---

## 7. Anti-HARKing Search Universe & Trial-Count Arithmetic

Under **Governance Amendment 2** and `ResearchReInceptionGate`, `planned_trial_count` must strictly equal the exact Cartesian product cardinality of the parameter grid:

### Parameter Search Grid (Under Option A: H4 Primary)
```json
{
  "lookback_bars": [3, 6, 12, 24, 48, 120],
  "deadband_bps": [3.0, 6.0]
}
```

### Search Degree-of-Freedom Cardinality
$$\mathbf{|Lookbacks| \times |Deadbands| = 6 \times 2 = 12\ trials}$$
$$\mathbf{planned\_trial\_count \equiv 12}$$

- **Horizon Policy:** $H=1$ is the primary optimization objective. $H=6$ is evaluated as a secondary robustness check without independent retuning.
- **Anti-HARKing Invariant:** All 12 trials must be executed in Step R3. No selective trial removal, no post-hoc grid modification.

---

## 8. Invalidation & Falsification Criteria

A candidate trial or the entire hypothesis will be **falsified in Step R3** if it triggers any of the following boundaries:

1. **Rank Information Coefficient (Rank IC):**
   $$\text{Spearman Rank IC} \le +0.025$$
   (Negative or near-zero correlation between signal and forward return).
2. **HAC Statistical Significance:**
   $$t_{\text{HAC}} < +2.00$$
   (Evaluated using Andrews 1991 AR(1) automatic bandwidth selection).
3. **Autocorrelation Ceiling:**
   $$\rho_1(s_t) \ge 0.98$$
   (Guards against near unit-root trend persistence).
4. **Economic Edge Hurdle (After Friction Waterfall):**
   $$\text{Gross PnL} \le \text{Roundtrip Friction Waterfall}$$
   $$\text{Average Net Trade PnL} < +1.5\text{ bps}$$
   $$\text{Annualized Haircut Sharpe} < +0.50$$
5. **Terminal Hypothesis Rejection Condition:**
   If $12 / 12$ trials fail to clear the Invalidation Criteria in-sample, the hypothesis is declared **`TERMINALLY_FALSIFIED`** with zero outbound transitions.

---

## 9. Proposed Cost Model (Friction Waterfall)

Institutional ECN cost assumptions for EURUSD on higher timeframes:

| Cost Component | Baseline Assumption | High-Stress Assumption | Governance Status |
| :--- | :--- | :--- | :--- |
| **Quoted Spread** | $0.4\text{ pips}$ ($0.4\text{ bps}$) | $0.8\text{ pips}$ ($0.8\text{ bps}$) | **PROPOSED** (Awaiting R2 broker audit) |
| **Roundtrip Fee** | $\$5.00/\text{lot}$ ($0.5\text{ bps}$) | $\$7.00/\text{lot}$ ($0.7\text{ bps}$) | **PROPOSED** |
| **Fixed Slippage** | $0.3\text{ bps}$ | $0.6\text{ bps}$ | **PROPOSED** |
| **Total Roundtrip Drag** | **$1.2\text{ bps}$** | **$2.1\text{ bps}$** | **PROPOSED** |

*Invariant:* All cost parameters are marked `PROPOSED` until independently calibrated against broker execution logs during Step R2.

---

## 10. Historical Data Contract Requirements (For Step R2)

### 10.1 Required Data Span (Completely New Window)
- **Timeframe:** `H4` (or `H1` if Option B selected).
- **Target Bar Count:** $6,000\text{ to } 10,000$ bars.
  - On H4: 6,000 bars $\approx 4.0\text{ calendar years}$ (e.g., 2021-01-01 to 2024-12-31).
- **Quarantine Isolation:** The proposed research window is completely disjoint from the 2026 M5 holdout window (`2026-08-18` to `2026-09-04`).

### 10.2 Partition Policy
- **In-Sample Training (Census):** $60\%$ (bars $0$ to $3,599$).
- **Validation Partition (Statistical Gate):** $20\%$ (bars $3,600$ to $4,799$) with 12-bar purge boundary.
- **Held-Out Blind OOS:** $20\%$ (bars $4,800$ to $5,999$) with 12-bar purge boundary.
- **Pristine Rule:** Validation and OOS partitions remain `UNEXPOSED_PRISTINE` until Step R4/R5.

---

## 11. Evidence Classification Table

| Proposition / Claim | Evidence Classification | Ground Truth Reference |
| :--- | :--- | :--- |
| **M5 Momentum Falsified on EURUSD** | **VERIFIED** | Proved in Phase 8.5 Track B Census ($9/9$ trials negative Rank IC) |
| **M5 Holdout Quarantine Active** | **VERIFIED** | Locked in `PERMANENTLY_QUARANTINED_WINDOWS` |
| **Academic HTF Momentum Literature** | **REPORTED** | Moskowitz et al. (2012), Menkhoff et al. (2012) |
| **Friction Relief on H4 vs M5** | **INFERRED** | Average bar move 35 bps vs 0.5 bps; friction percentage drops from $100\%+$ to $<5\%$ |
| **EURUSD HTF Momentum Predictive Power** | **NOT PROVEN** | Unproven on historical dataset; requires Step R3 Census |
| **Strategy Live Qualification** | **BLOCKED** | $0.00 Capital Authority, Disconnected wire, 0 orders |

---

## 12. Human Operator Decision Checkpoints

Before this proposal can be submitted to `ResearchReInceptionGate` and registered as Step R1:

1. **Timeframe Scope Decision:** Confirm **Option A (H4 Primary, $K=12$)** or **Option B (H1 + H4, $K=24$)**.
2. **Historical Window Approval:** Confirm the 4-year historical target span (e.g. 2021–2024).
3. **Authorization to Proceed to Step R1:** Human operator sign-off required to generate `docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_001.json` and compute its canonical registration digest.

---

## 13. Final Design Verdict

$$\boxed{\mathbf{VERDICT:\ READY\ FOR\ HUMAN\ R1\ REVIEW}}$$

*(The draft proposal satisfies all 6 Re-Inception Gate prerequisites in design. Zero market data was touched. Zero empirical research was run. Capital authority remains strictly $0.00).*
