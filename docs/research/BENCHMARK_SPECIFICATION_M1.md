# ACASH — Benchmark Specification & Research Safeguards (Milestone M1)

**Document ID:** `DOC-ACASH-BENCHMARK-SPEC-20261012`  
**Classification:** Quantitative Benchmark Formulation & Statistical Protocol  
**Governing Authority:** `AGENTS.md` (Single Canonical Authority, Strict Fail-Closed, Units & Space Discipline)  
**Effective Date:** 2026-10-12  
**Outcome Testing Status:** `NO_STRATEGY_OUTCOME_TESTING = true`; Zero historical backtests executed in this milestone.  

---

## 1. Objective & Sovereign Benchmark Hierarchy

To prevent self-deceptive quantitative research, any proposed investment strategy—whether passive core or active trend-following—must be evaluated against a strict hierarchy of transparent, reproducible baselines.

```text
┌────────────────────────────────────────────────────────┐
│                   SOVEREIGN HURDLES                    │
├──────────────────────────┬─────────────────────────────┤
│ 1. Cash / T-Bills (BIL)  │ Risk-free return; zero drawdown baseline │
│ 2. S&P 500 Buy-and-Hold  │ Broad-market equity beta (VOO Total Return) │
│ 3. 60/40 Balanced Core   │ 60% Equity / 40% Bond (VOO/BND) quarterly │
│ 4. Naive Equal Weight    │ 1/N across universe; zero estimation error │
│ 5. Inverse Volatility    │ 1/σ heuristic; covariance-free risk balance│
└──────────────────────────┴─────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│       ACTIVE RESEARCH CANDIDATE (MULTI-ASSET TREND)    │
│  - Evaluated on PRE-REGISTERED PRIMARY ENDPOINT        │
│  - Not forced to beat every metric simultaneously      │
│  - Friction-adjusted with small-order minimum fees     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Benchmark Definitions & Total Return Conventions

### 2.1 Cash / Risk-Free Baseline (`BM-CASH`)
- **Instrument**: U.S. 3-Month Treasury Bill Secondary Market Rate (`DTB3` via FRED) or SPDR 1-3 Month T-Bill ETF (`BIL`).
- **Accrual Convention**: Daily compounding in Decimal space using ACT/360.
- **Role**: The uncompromised capital preservation baseline. If a candidate cannot clear this hurdle net of friction, capital remains in cash.

### 2.2 Broad Equity Market Buy-and-Hold (`BM-SP500`)
- **Instrument**: Vanguard S&P 500 ETF (`VOO`).
- **Inception Boundary**: September 7, 2010. Observations prior to this date require explicit `SPX_SYNTHETIC_PROXY` notation.
- **Return Space**: Total Return (dividends reinvested on ex-date net of withholding tax).
- **Role**: Evaluates whether active timing generates positive value beyond passive market risk premium.

### 2.3 Classical Balanced Core (`BM-6040`)
- **Allocation**: 60% VOO / 40% BND (Vanguard Total Bond Market ETF).
- **Rebalance Schedule**: Calendar quarterly with frictionless target resetting for baseline purposes, and realistic friction when comparing portfolio implementations.
- **Role**: Industry standard asset-allocation benchmark for retail wealth compounding.

### 2.4 Naive Equal Weight (`BM-EW`)
- **Allocation**: $w_i = \frac{1}{N}$ across the eligible investable universe (`VOO`, `BND`, `GLD`, `BIL`).
- **Rebalance Schedule**: Monthly rebalancing.
- **Role**: Transparent benchmark with zero estimation risk, demonstrating the pure value of naive diversification.

### 2.5 Inverse Volatility Heuristic (`BM-INVVOL`)
- **Allocation**: $w_{i,t} \propto \frac{1}{\sigma_{i,t}}$, where $\sigma_{i,t}$ is the 60-day rolling sample return standard deviation.
- **Role**: Robust risk-budgeting heuristic avoiding inverted covariance matrix instability.

---

## 3. Active Candidate Formulation: Multi-Asset Trend Following

### 3.1 Critical Literature Distinction
- **Academic Canon (Moskowitz, Ooi, Pedersen 2012 - "Time Series Momentum")**:
  - Examined 58 liquid futures and currency forward contracts.
  - Employed bidirectional exposure (both long and short), active leverage, and daily margin financing.
- **ACASH Retail Adaptation**:
  - **Long-Only ETF Universe**: `VOO`, `BND`, `GLD`, `BIL`.
  - **Zero Shorting / Zero Margin Borrowing**: Gross leverage capped at 1.00x.
  - **Defensive Mechanism**: When 12-month momentum is non-positive ($R_{i, 12M} \le 0$), capital rotates into Cash / T-Bills (`BIL`), rather than initiating short positions.
  - **Epistemic Standing**: This is an **asymmetric capital-preservation adaptation**, NOT an academic replication of Moskowitz et al. (2012).

### 3.2 Scientifically Correct Evaluation Protocol (Avoiding Multi-Metric Traps)
In PR #22's draft, the falsification rule asserted that Trend Following must beat 60/40 on CAGR, Sharpe, *and* Maximum Drawdown simultaneously. This is mathematically flawed:
- Trend-following strategies commonly exhibit lower CAGR than 100% equity during secular bull markets due to rebalancing lag ("whipsaw" during sudden trend reversals).
- Their primary economic utility is **downside tail-risk reduction** (crisis alpha / capital preservation during deep recessions and market panics).

#### Pre-Registered Evaluation Design
1. **Primary Success Endpoint**: Net-of-Friction Out-of-Sample **Calmar Ratio** ($\text{CAGR} / |\text{Max Drawdown}|$) over the evaluation timeline.
2. **Hard Risk Constraints (Mandate Enforced)**:
   - Maximum Peak-to-Trough Drawdown $\le 50.0\%$ (Personal Mandate ceiling).
   - Maximum Annualized Volatility $\le 18.0\%$.
   - Gross Leverage $\le 1.00$.
3. **Secondary Diagnostics (Informational)**:
   - Annualized Sharpe Ratio net of small-order friction.
   - Monthly turnover and ticket count (to monitor small-account commission drag).
   - CVaR 95% tail risk.
4. **Pass/Fail Decision Rule**:
   - The candidate passes if and only if:
     $$\text{Calmar}_{\text{OOS}}(\text{Trend}) > \text{Calmar}_{\text{OOS}}(\text{BM-6040})$$
     $$\text{AND } \text{MaxDD}_{\text{OOS}}(\text{Trend}) \le 50.0\%$$
     $$\text{AND Expected Return Net of Friction} > \text{Cash Hurdle}$$

---

## 4. Friction & Small-Account Reality Check ($1,000 Portfolio)
For a $1,000 portfolio:
- A $50 rebalance ticket incurring an IBKR Tiered minimum commission of $0.35 represents a **0.70% one-way cost drag**.
- High-frequency daily or weekly rebalancing will rapidly destroy capital through ticket minimums.
- **Mandatory Policy**: Rebalance frequency is strictly limited to **Monthly** with a minimum rebalance threshold $\Delta w \ge 3.0\%$ to filter out micro-turnover noise.
