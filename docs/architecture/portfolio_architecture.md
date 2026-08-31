# ACASH — Portfolio Architecture & Optimization Specification

**Document:** `docs/architecture/portfolio_architecture.md`  
**Version:** 3.1.0 (Terminology Corrections Applied)  
**Date:** 2026-08-27  

---

## 1. The Core Allocation Problem

ACASH's fundamental question is:
> *"Given the current market, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"*

The system explicitly supports the answer: **"NOWHERE."** (100% Cash / No-Trade Allocation).

---

## 2. Portfolio Optimizer Governance: skfolio vs Transparent Baselines

### 2.1 The Baseline Evaluation Principle
**`skfolio` must be evaluated for statistically significant incremental value versus transparent baselines out-of-sample.**

### 2.2 Required Baselines
1. **Equal Weight ($1/N$):** Naive diversification benchmark with zero estimation error.
2. **Inverse Volatility ($1/\sigma$):** Robust heuristic allocating inversely to historical asset variance.
3. **Cash / No-Trade ($w_{\text{cash}} = 1.0$):** Default state when expected return net of costs does not exceed the hurdle rate or uncertainty is elevated.

### 2.3 Sovereign Selection Rules
- **No Forced Optimization:** The system must **NOT** force `skfolio` to win. If a simple transparent baseline (e.g. Inverse Volatility or Equal Weight) produces more robust, higher risk-adjusted returns out-of-sample after accounting for turnover and transaction costs, ACASH must select the baseline.
- **No Overfitting the Optimizer:** The quant researcher must not tweak optimizer hyperparameters merely to beat the benchmark in-sample.
- **Hurdle Rate Enforcement:** If candidate expected return $\mu_i < \text{Risk-Free Rate} + \text{Turnover Cost} + \text{Hurdle Margin}$, capital remains unallocated in Cash.

---

## 3. Optimization Architecture & Comparison

```
┌─────────────────────────────────────────────────────────────┐
│                 PORTFOLIO OPTIMIZER ENGINE                  │
├──────────────────────────────┬──────────────────────────────┤
│  TRANSPARENT BASELINES       │  skfolio ALLOCATION METHODS  │
│  - 100% Cash ("NOWHERE")     │  - Hierarchical Risk Parity  │
│  - Equal Weight (1/N)        │  - Equal Risk Contribution   │
│  - Inverse Realized Vol      │  - Minimum CVaR / CDaR       │
│  - Volatility-Adjusted Target│  - Mean-Variance (Shrinkage) │
└──────────────┬───────────────┴──────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│               HURDLE RATE & TURNOVER GATE                   │
│  (Expected Return net of fees > Hurdle Rate + Turnover)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 RISK ENGINE (HARD GATE)                     │
│  (Limits, Drawdown, Leverage, Concentration, Kill Switch)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│         TRANSACTIONAL OPERATIONAL AUDIT (SQLite V1)         │
└─────────────────────────────────────────────────────────────┘
```

| Feature / Metric | Simple Baselines | `skfolio` (ADOPTED) | `PyPortfolioOpt` (REJECTED) |
| :--- | :--- | :--- | :--- |
| **API Standard** | Python functional / class | **Scikit-Learn (`fit`, `predict`, `score`, `Pipeline`)** | Custom imperative object API |
| **Optimization & Allocation Methods** | Naive / Heuristic | **Portfolio optimization and risk-allocation methods including HRP, ERC, and CVaR-based approaches** | Mean-Variance, Basic HRP, Black-Litterman |
| **Tail Risk Measures**| Max Drawdown limit | **CVaR, CDaR, Semi-Variance, Higher Moments** | Semi-Variance, Simple CVaR |
| **Validation Integration**| Train/Test split | **Combinatorial Purged CV (`CombinatorialPurgedCV`)**| None built-in |
| **Numerical Solvers / Engines** | Closed-form vector math | **Convex / Cone Solvers (CVXPY), Tree Clustering, Analytical Solvers** | CVXPY / SciPy |
| **Maintenance** | 100% internal control | **Very Active, modern codebase** | Low/Slow maintenance |
| **License** | Proprietary | **BSD-3-Clause** | MIT |
| **ACASH Decision** | **PRIMARY BENCHMARK** | **ADOPT (Primary Optimizer Engine)** | **REJECT (Redundant)** |

---

## 4. Risk State, Margin Buffer & Exposure Invariants

ACASH strictly tracks portfolio risk state and capital exposure before and after allocation:

1. **Risk State Integration:**
   - Formal tracking of account health: $\text{Equity} = \text{Balance} + \text{Unrealized PnL}$.
   - Drawdown state and distance to max drawdown hard limit.
2. **Margin Buffer Safety Threshold:**
   - Explicit margin headroom required prior to order dispatch:
     $$\text{Free Margin} \ge \text{Margin Buffer Threshold}$$
   - Prevents aggressive order sizing from approaching broker margin call levels.
3. **Net & Dollar Exposure Tracking:**
   - **Dollar Gross Exposure:** $\text{Gross Exposure} = \sum_{i} |\text{Normalized Dollar Value}_i|$
   - **Dollar Net Exposure:** $\text{Net Exposure} = \sum_{i} \text{Normalized Dollar Value}_i$
4. **Deterministic Edge Pipeline:**
   $$\text{DATA} \to \text{QUANT ENGINE} \to \text{RISK STATE} \to \text{AI REASONING}$$
   *(Raw quantitative metrics remain pure and immutable; AI reasoning operates downstream for explainability, never trading directly).*

