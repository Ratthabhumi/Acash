# ACASH — Quantitative Research Architecture & Alpha Engine

**Document:** `docs/architecture/research_architecture.md`  
**Version:** 2.0.0 (Final Addendum Updated)  
**Date:** 2026-08-27  

---

## 1. Quantitative Research Philosophy

ACASH adheres to the core scientific research principle:
> **DO NOT ASSUME AN EDGE. PROVE IT.**

Quantitative research is not curve-fitting dozens of indicator combinations. It is a systematic process of forming economically grounded hypotheses, disproving spurious correlations, measuring transaction cost impacts, and validating strictly out-of-sample.

---

## 2. Quantitative Research Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ 1. HYPOTHESIS FORMULATION                                   │
│    - Economic / Microstructure Rationale                    │
│    - Expected Market Regime & Invalidation Conditions       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. POINT-IN-TIME FEATURE GENERATION                         │
│    - Temporal Isolation: t_event <= T_decision              │
│    - Incremental Predictive Metric (Information Coeff > 0)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TIER-1 RAPID PARAMETER SCREENING (vectorbt)              │
│    - Vectorized parameter sweeps across historical matrix   │
│    - Filter out non-viable parameter spaces                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. TIER-2 REALISTIC EVENT-DRIVEN SIMULATION (Nautilus/Custom)│
│    - Microstructure fidelity: order books, fees, slippage   │
│    - High-precision execution queue & latency modeling      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. STATISTICAL VALIDATION & HARD OOS GATE (skfolio CPCV)    │
│    - Combinatorial Purged Cross-Validation (CPCV)           │
│    - Walk-Forward Analysis & Completely Held-Out OOS Split  │
│    - Deflated Sharpe Ratio (DSR) Multi-Testing Correction   │
│    - Slippage & Spread Stress Testing (2x, 5x friction)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. INTERACTIVE VISUALIZATION & RESEARCH TEAR SHEET (Plotly) │
│    - Equity curves, Underwater Drawdowns, Exposure Surfaces │
│    - Rolling Sharpe, Distribution Skew/Kurtosis Histograms  │
│    - Formal Research Report (Section 33 Compliance)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Two-Tier Backtesting Methodology

ACASH solves the research vs execution dilemma by decoupling backtesting into two distinct tiers:

| Tier | Engine | Primary Objective | Microstructure Fidelity | Compute Speed |
| :--- | :--- | :--- | :--- | :--- |
| **Tier-1: Rapid Screening** | `vectorbt` | Scan parameter combinations (e.g. 100,000 runs) to eliminate noise. | Low (Bar-level vectorized matrices) | Ultra-Fast ($10^6$ ops/sec) |
| **Tier-2: Event Simulation** | `NautilusTrader` / Custom Event | Validate top 1–3 candidate parameter sets with realistic friction. | Ultra-High (Ticks, queue, slippage, fees) | High (Event loops) |

---

## 4. Rigorous Statistical Validation Protocol

To protect against data snooping, ACASH enforces four mandatory validation barriers:

### 4.1 Combinatorial Purged Cross-Validation (CPCV)
Using `skfolio.model_selection.CombinatorialPurgedCV`, the historical timeline is split into $N$ blocks. Training and testing are performed across all permutations $\binom{N}{k}$ while purging overlapping trade returns and applying embargo periods to eliminate autocorrelation leakage.

### 4.2 Deflated Sharpe Ratio (DSR) & Multiple Testing Correction
Whenever a strategy undergoes $K$ parameter iterations, the standard Sharpe ratio is inflated. ACASH computes the Deflated Sharpe Ratio:
$$DSR = \Phi \left( \frac{(\widehat{SR} - SR_0)\sqrt{T-1}}{\sqrt{1 - \widehat{\gamma}_3 \widehat{SR} + \frac{\widehat{\gamma}_4 - 1}{4}\widehat{SR}^2}} \right)$$
where $SR_0$ accounts for the variance across all $K$ tested trials and distribution non-normality (skewness $\gamma_3$ and kurtosis $\gamma_4$). Strategies with $DSR < 0.95$ fail validation.

### 4.3 Friction & Slippage Stress Tests
Every candidate strategy is evaluated across stress scenarios:
- **Baseline Friction:** Normal exchange commission + median bid/ask spread.
- **2x Spread Stress:** Commission + $2\times$ spread + $1\times$ volatility slippage.
- **5x Crisis Stress:** Commission + $5\times$ spread + $3\times$ adverse selection slippage.
- *Rule:* If a strategy is not profitable under 2x spread stress, it is rejected.

---

## 5. Visualization & Research Dashboards (Plotly Integration)

Interactive analytics are powered by **Plotly** in `acash.telemetry` and research notebooks:
- **Interactive Candlesticks with Point-in-Time Markers:** Visualizes exact signal generation and order execution timestamps.
- **Equity Curve & Underwater Drawdown Charts:** Compares strategy equity curve against buy-and-hold and benchmark allocations.
- **Rolling Metrics:** Rolling 30-day Sharpe, Sortino, volatility, and exposure.
- **Return Distribution Plots:** QQ-plots, histogram with normal overlay, skewness, and excess kurtosis indicators.

---

## 6. Engineering Research Addendum

Use the referenced trading-platform examples only as independent research references, not as ACASH architecture.

### Potential Future Concepts Worth Preserving:
- Multi-source news / external evidence ingestion
- Evidence provenance and timestamps
- Forward / out-of-sample testing
- Research reproducibility
- Portfolio analytics

*Do NOT expand Phase 1 scope for these concepts.*

### Important Architectural Rules:
1. **Append-Only Immutable Lineage:** `DecisionRecord` is immutable and append-only. Do not mutate it later to attach Fill/PnL outcomes. Preserve lineage through immutable references/correlation IDs so the complete decision $\to$ execution $\to$ outcome chain can be reconstructed without modifying historical records.
2. **Evidence-Driven Rigor:** Do not treat AI confidence scores, huge backtest returns, or large data-source counts as evidence of trading edge without proper calibration, bias checks, and out-of-sample validation.
3. **Strict External System Isolation:** External systems such as MT4/MT5 or Agentic Trading Lab may only be future adapters/research references and must never become ACASH core dependencies without an explicit ADR.
4. **Phase 1 Boundary:** Keep Phase 1 strictly foundational.

---

## 7. Research Lessons — Trading Systems

From external trading-system examples/research, incorporate these principles into ACASH research architecture where appropriate:

1. **Data Quality and Provenance:**
   $$\text{Source} \to \text{Ingestion} \to \text{Validation} \to \text{Normalization} \to \text{Evidence} \to \text{Decision}$$
2. **AI as Analytical Component, NOT Authority:**
   AI must remain an analytical component, NOT the final trading authority. Never treat AI confidence as proven probability/edge.
3. **Multi-Source Evidence Treatment:**
   News, macro, options, Greeks, IV, and external data should be treated as evidence/research inputs, not automatic signals.
4. **Explainability & Traceability:**
   Every decision should be explainable and traceable back to its evidence, data, calculations, and timestamp.
5. **Backtest Metrics $\neq$ Proven Edge:**
   Backtest metrics (win rate, PF, Sharpe, expectancy, etc.) do NOT prove a real edge without proper OOS/forward testing, leakage checks, costs, slippage, and regime validation.
6. **Observability Hierarchy:**
   $$\text{System State} \to \text{Metrics} \to \text{Monitoring} \to \text{Audit/Investigation}$$
7. **Decoupled External Platforms:**
   External platforms/data providers may be used for independent research/evaluation, but must NOT become ACASH core dependencies without an explicit architectural decision.

> [!IMPORTANT]
> **Do not add new features or perform broad refactors based on these lessons.** Preserve current ACASH boundaries and apply only minimal, reversible documentation/architecture updates where justified.

**Core Research Loop:**
$$\text{Evidence} \to \text{Analysis} \to \text{Decision} \to \text{Execution} \to \text{Outcome} \to \text{Audit/Learning}$$

---

## 8. Final Research Lesson — Market Structure

- **Options Flow as Positioning:** Do NOT interpret Options Flow simply as bullish/bearish sentiment. Flow is an observation of transactions/positioning; the core question is: *"At this price/structure, who is forced to react, and what happens if price reaches that level?"*
- **Market Structure Precedes Strategy:** Market structure comes before strategy. Identify important levels/zones and how price behaves around them before choosing a strategy.
- **3-Dimensional Options Evaluation:** For options, evaluate at least 3 dimensions concurrently: $\text{Direction} \times \text{Volatility} \times \text{Time}$. Do not judge an option setup from direction alone.
- **Market State $\neq$ Trade Signal:** Distinguish "market state / setup" $\neq$ "trade signal". The system should explain what condition exists and what actions/risk responses become relevant, rather than blindly outputting BUY/SELL.
- **Real Arbitrage Exploitability:** Arbitrage is only meaningful when the pricing relationship is actually demonstrably exploitable after transaction costs, liquidity, execution risk, and timing friction.

**Market Structure Decision Loop:**
$$\text{OBSERVE} \to \text{IDENTIFY STRUCTURE} \to \text{QUANTIFY RISK/REWARD} \to \text{EVALUATE CONDITIONS} \to \text{DECIDE}$$

---

## 9. Quantitative Reasoning & Deterministic Risk Pipeline

1. **Risk State Representation:** Continuous tracking of portfolio risk capacity, limit headroom, and drawdown state.
2. **Margin Buffer Safety Threshold:** Mandatory buffer between utilized margin and maintenance thresholds before approving any allocation.
3. **Net & Dollar Exposure Tracking:** Explicit dollar-denominated exposure accounting ($\text{Gross Exposure} = \sum |\text{Dollar Value}|$, $\text{Net Exposure} = \sum \text{Dollar Value}$).
4. **Deterministic Edge Metrics:** All performance metrics (Sharpe, DSR, Information Ratio, expectancy, max drawdown) are calculated strictly by deterministic mathematical algorithms.
5. **Separation of Raw Metrics from AI Reasoning:** Raw quantitative metrics remain pure and immutable. AI reasoning operates strictly downstream as an explanatory research tool, NEVER generating unverified numbers or placing trades.

### Core Processing Flow:
$$\text{DATA} \to \text{QUANT ENGINE} \to \text{RISK STATE} \to \text{AI REASONING}$$

$$\text{NOT: DATA} \to \text{AI} \to \text{Unverified Numbers} \to \text{TRADE}$$

---

## 10. Reality Gap Analysis & Execution Deviation Architecture

The true empirical value of ACASH lies not in assuming theoretical perfection, but in systematically measuring:
> *"How much does what we expected in simulation diverge from what actually happened in the live market?"*

### 10.1 The Reality Gap Pipeline:
```
                 BACKTEST SIMULATION
                          │
                          ▼
                 PAPER / SHADOW TRADING
                          │
                          ▼
                    LIVE EXECUTION
                          │
                          ▼
               REALITY GAP ATTRIBUTION
```

### 10.2 Deviation Attribution Dimensions:
Execution deviations are systematically attributed to four distinct sources:
1. **Data Error:** Quote timestamp jitter, stale prices, bar aggregation anomalies, or tick missingness.
2. **Model / Alpha Error:** Predictive decay, regime shift, or overfitted feature parameters.
3. **Execution Error:** Fill price slippage, queue priority delay, or internal engine latency.
4. **Broker / Venue Conditions:** Spread blowout, asymmetric requotes, margin policy shifts, or liquidity holes.

### 10.3 Execution Deviation Metrics:
$$\Delta_{\text{entry}} = \text{Actual Fill Price} - \text{Expected Model Price}$$
$$\Delta_{\text{spread}} = \text{Actual Realized Spread} - \text{Expected Model Spread}$$
$$\Delta_{\text{slippage}} = \text{Actual Slippage} - \text{Assumed Model Slippage}$$
$$\Delta_{\text{pnl}} = \frac{\text{Actual PnL} - \text{Expected PnL}}{\text{Expected PnL}}$$
$$\Delta_{\text{latency}} = \text{Round-Trip Latency} - \text{Assumed Model Delay}$$

### 10.4 Empirical Modeling Principles:
1. **Spread Modeling:** Execution-sensitive research must model spread at the highest fidelity supported by the available market data and strategy horizon. Lower-fidelity spread assumptions may be used when appropriate, but their limitations must be explicit.
2. **Slippage Modeling:** Adopt a graduated complexity approach ($\text{simple assumption} \to \text{empirical calibration} \to \text{liquidity/order-size aware} \to \text{nonlinear model only when evidence justifies it}$).
3. **Capital Flow Separation:** Deposits, withdrawals, and external cash flows are treated as first-class capital flow events, strictly isolated from Trading PnL and performance attribution metrics.
4. **Martingale & Exposure Escalation:** Classify Martingale-like exposure escalation as a **HARD RISK FLAG** requiring explicit risk justification, tail-loss analysis, ruin probability analysis, and non-bypassable risk-gate enforcement.
5. **Data Fidelity Alignment:** Data fidelity must match strategy horizon, execution sensitivity, and market microstructure requirements. Higher-fidelity tick/quote data is required when lower-resolution data cannot adequately represent the strategy's execution assumptions.

