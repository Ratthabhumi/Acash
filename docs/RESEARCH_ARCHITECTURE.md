# ACASH — Quantitative Research Architecture & Alpha Engine (Phase 0)

**Document:** `docs/RESEARCH_ARCHITECTURE.md`  
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
