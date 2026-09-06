# Research Hypothesis Design Draft: EURUSD Higher-Timeframe Time-Series Momentum (HYP_002)

> **Document ID:** `DESIGN-HYP-TSMOM-EURUSD-HTF-001`  
> **Timestamp:** `2026-09-06T23:42:00+00:00`  
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
&\text{\textit{(specifically H4) where gross price displacements are large enough to comfortably surmount}} \\
&\text{\textit{institutional transaction frictions (spread, commission, and slippage)?”}}
\end{aligned}$$

---

## 3. Honest Epistemic Evaluation & Scientific Rating

### Rating: 6.5 / 10 (Moderate Plausibility, High Empirical Uncertainty)

- **Theoretical Grounding (7.5 / 10):**
  - Canonical financial literature establishes that macro trend following and currency momentum exist over multi-week to multi-month horizons due to delayed price discovery, central bank monetary policy divergence, and gradual institutional capital reallocation (*Moskowitz, Ooi, Pedersen 2012*; *Menkhoff, Sarno, Schmeling, Zhu 2012*).
  - Microstructure friction collapse is mitigated: On M5, average gross moves were ~0.3–0.5 bps, which were obliterated by 2.0 bps roundtrip friction. On H4, average bar ranges are 20–50 bps, providing an expected signal-to-friction ratio of $15:1$ to $30:1$.
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
   - Institutional macro market participants do not execute large billion-dollar portfolio rebalances instantaneously; order execution algorithms slice parent orders over multi-day execution horizons (TWAP/VWAP), generating auto-correlated drift at H4 session timeframes.
3. **Friction-to-Volatility Asymmetry:**
   - Institutional FX roundtrip transaction costs are relatively fixed ($\approx 1.2\text{ to } 2.1\text{ bps}$).
   - By moving from M5 (bar volatility $\approx 3\text{ bps}$) to H4 (bar volatility $\approx 35\text{ bps}$), the transaction cost hurdle drops from $60\%\text{--}100\%$ of the price move down to $< 6\%$ of the price move.

---

## 5. Candidate Timeframe Universe (Approved Option A: H4 Primary)

The research protocol explicitly freezes the timeframe universe to **Option A (H4 Primary)**:
- **Primary Timeframe:** `H4` (4-hour bars, capturing Asian, European, and US operational sessions).
- **Rationale for H4 Selection:**
  - Minimizes multiple-testing penalty by keeping search degrees of freedom compact ($K=12$).
  - Average bar volatility ($~35\text{ bps}$) is well above realistic transaction frictions.
  - Eliminates overnight intraday microstructure bid-ask bounce that falsified M5.
- **Trial Count Economy:** Avoids diluting statistical power across dual timeframes ($K=24$), preventing excessive Deflated Sharpe Ratio (DSR) haircutting at the validation gate.

---

## 6. Causal Feature Formulation & Label Definition

### 6.1 Feature Definition: Time-Series Return Momentum with Deadband
For bar $t$ at timeframe $H4$, the momentum signal $s_{t, L, \theta}$ over lookback window $L$ is:
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
  Multi-bar holding horizon ($6 \times 4\text{h} = 24\text{ hours}$) with mandatory interval purging and embargo. Evaluated as a secondary robustness check without independent retuning.

---

## 7. Anti-HARKing Search Universe & Trial-Count Cardinality

Under **Governance Amendment 2** and `ResearchReInceptionGate`, `planned_trial_count` must strictly equal the exact Cartesian product cardinality of the parameter grid:

### Parameter Search Grid (H4 Primary)
```json
{
  "lookback_bars": [3, 6, 12, 24, 48, 120],
  "deadband_bps": [3.0, 6.0]
}
```

### Search Degree-of-Freedom Cardinality
$$\mathbf{|Lookbacks| \times |Deadbands| = 6 \times 2 = 12\ trials}$$
$$\mathbf{planned\_trial\_count \equiv 12}$$

- **Parameter Geometry:**
  - $L \in \{3, 6, 12, 24, 48, 120\}$ bars represents historical lookbacks of $12\text{ hours}$, $24\text{ hours}$ (1 day), $48\text{ hours}$ (2 days), $4\text{ days}$, $8\text{ days}$, and $20\text{ days}$ (1 trading month).
  - $\theta \in \{3.0, 6.0\}\text{ bps}$ represents deadband filtering to suppress low-volatility chop.
- **Anti-HARKing Invariant:** All 12 trials must be executed in Step R3. No selective trial removal, no post-hoc grid modification.

---

## 8. Invalidation Criteria & Conjunctive Boolean Logic

### 8.1 Unambiguous Threshold Semantics (Strict Complements)

To prevent boundary ambiguity, pass and fail criteria are defined as strict mathematical complements:

| Metric | PASS Condition | FAIL (Invalidation) Condition |
| :--- | :--- | :--- |
| **Spearman Rank IC** | $\text{Rank IC} \ge +0.025$ | $\text{Rank IC} < +0.025$ |
| **HAC Statistical Significance** | $t_{\text{HAC}} \ge +2.00$ | $t_{\text{HAC}} < +2.00$ |
| **Feature Autocorrelation** | $\rho_1(s_t) \le 0.98$ | $\rho_1(s_t) > 0.98$ |
| **Average Net Trade PnL** | $\overline{\text{Net PnL}} \ge +1.5\text{ bps}$ | $\overline{\text{Net PnL}} < +1.5\text{ bps}$ |
| **Annualized Haircut Sharpe** | $\text{Haircut } SR \ge +0.50$ | $\text{Haircut } SR < +0.50$ |

*HAC Bandwidth:* Evaluated using Andrews 1991 AR(1) automatic plug-in bandwidth selection.

### 8.2 Mandatory Boolean Conjunction Logic
A candidate trial is **QUALIFIED** if and only if **ALL** mandatory criteria pass simultaneously:
$$\mathbf{Qualified \iff (\text{Rank IC} \ge 0.025) \land (t_{\text{HAC}} \ge 2.00) \land (\rho_1 \le 0.98) \land (\overline{\text{Net PnL}} \ge +1.5\text{ bps}) \land (\text{Haircut } SR \ge +0.50)}$$

- **Disqualification Rule:** A trial is invalidated/disqualified if **ANY single mandatory criterion fails**. There are no alternative or partial qualifications.
- **Terminal Hypothesis Rejection Rule:** If **$12 / 12$ trials** fail to clear the Invalidation Criteria in-sample, the hypothesis is declared **`TERMINALLY_FALSIFIED`** with zero outbound transitions.

---

## 9. Proposed Research Cost Model (Friction Waterfall)

> [!IMPORTANT]
> **PROPOSED RESEARCH COST MODEL — Subject to Independent R2 Verification**  
> These parameters represent the theoretical cost model proposed for Step R1 pre-registration. They do **NOT** represent empirically verified broker facts and are subject to independent calibration and replacement against actual broker execution logs during Step R2.

| Cost Component | Baseline Assumption | High-Stress Assumption | Governance Status |
| :--- | :--- | :--- | :--- |
| **Quoted Spread** | $0.4\text{ pips}$ ($0.4\text{ bps}$) | $0.8\text{ pips}$ ($0.8\text{ bps}$) | **PROPOSED** (Awaiting R2 broker audit) |
| **Roundtrip Fee** | $\$5.00/\text{lot}$ ($0.5\text{ bps}$) | $\$7.00/\text{lot}$ ($0.7\text{ bps}$) | **PROPOSED** (Awaiting R2 broker audit) |
| **Fixed Slippage** | $0.3\text{ bps}$ | $0.6\text{ bps}$ | **PROPOSED** (Awaiting R2 broker audit) |
| **Total Roundtrip Drag** | **$1.2\text{ bps}$** | **$2.1\text{ bps}$** | **PROPOSED** (Awaiting R2 broker audit) |

---

## 10. Historical Data Contract Requirements (For Step R2)

### 10.1 Deterministic Calendar Window Contract
To eliminate arithmetic ambiguity between calendar time and market sessions, the data contract establishes **Calendar Window** as the primary authority:

- **Canonical Research Window:**
  $$\mathbf{2021\text{-}01\text{-}01T00:00:00+00:00 \quad \text{through} \quad 2024\text{-}12\text{-}31T23:59:59+00:00}$$
  (4 full calendar years).
- **Minimum Usable H4 Bar Count:**
  $$\mathbf{N_{\text{usable}} \ge 5,000\ H4\ bars}$$
  *(Note: A 4-year calendar span contains $24\text{h} \times 365\text{d} \times 4 / 4\text{h} = 8,760$ raw time buckets. Accounting for ~52 weekends/year and institutional holiday closures, the observed FX trading bar count is expected to be approximately 6,000–6,500 bars. Step R2 will audit and certify the exact observed bar count).*
- **Quarantine Isolation:** The proposed research window is completely disjoint from the 2026 M5 holdout window (`2026-08-18` to `2026-09-04`).

### 10.2 Partition Policy
- **In-Sample Training (Census):** $60\%$ (bars $0$ to $0.60 \times N - 1$).
- **Validation Partition (Statistical Gate):** $20\%$ with 12-bar purge boundary.
- **Held-Out Blind OOS:** $20\%$ with 12-bar purge boundary.
- **Pristine Rule:** Validation and OOS partitions remain `UNEXPOSED_PRISTINE` until Step R4/R5.

---

## 11. Evidence Classification Table

| Proposition / Claim | Evidence Classification | Ground Truth Reference |
| :--- | :--- | :--- |
| **M5 Momentum Falsified on EURUSD** | **VERIFIED** | Proved in Phase 8.5 Track B Census ($9/9$ trials negative Rank IC) |
| **M5 Holdout Quarantine Active** | **VERIFIED** | Locked in `PERMANENTLY_QUARANTINED_WINDOWS` |
| **Academic HTF Momentum Literature** | **REPORTED** | Moskowitz et al. (2012), Menkhoff et al. (2012) |
| **Friction Relief on H4 vs M5** | **INFERRED** | Average bar move 35 bps vs 0.5 bps; friction percentage drops from $100\%+$ to $<6\%$ |
| **EURUSD HTF Momentum Predictive Power** | **NOT PROVEN** | Unproven on historical dataset; requires Step R3 Census |
| **Strategy Live Qualification** | **BLOCKED** | $0.00 Capital Authority, Disconnected wire, 0 orders |

---

## 12. Human Operator Decision Checkpoints

Before this proposal can be submitted to `ResearchReInceptionGate` and registered as Step R1:

1. **Timeframe Scope:** Option A (H4 Primary, $K=12$) is **APPROVED**.
2. **Calendar Window Scope:** 2021-01-01 to 2024-12-31 with $N \ge 5,000$ usable H4 bars is **APPROVED**.
3. **Authorization to Proceed to Step R1:** Human operator sign-off required to submit the proposal to `ResearchReInceptionGate`, emit `InceptionAuthorizationToken`, and generate sealed `docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_001.json`.

---

## 13. Final Design Verdict

$$\boxed{\mathbf{VERDICT:\ READY\ FOR\ HUMAN\ R1\ REVIEW}}$$

*(All 4 mandatory contract corrections applied. Zero market data was touched. Zero empirical research was run. Capital authority remains strictly $0.00).*
