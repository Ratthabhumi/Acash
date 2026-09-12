# Foundational Academic Literature in Quantitative Finance

**Status:** ACADEMIC_REFERENCE — Theoretical Reference Only  
**Canonical Governance Authority:** Non-Executable Research Reference. Does NOT authorize backtest, paper trading, or live execution. Does NOT create HYP_003. Preserves Canonical Capital = $0.00 and NO_REAL_ORDERS = true.

---

## 1. Overview & Research Scope

This document catalogues 10 cornerstone academic papers and quantitative finance frameworks. These references represent theoretical benchmarks and mathematical foundations for portfolio theory, market efficiency, information economics, derivative pricing, and execution modeling.

> [!IMPORTANT]
> **ACASH Epistemic Boundary:**
> - None of these academic papers constitute active ACASH trading strategies.
> - Inclusion in this reference library does NOT imply empirical alpha in modern cryptocurrency or FX markets.
> - Any operational translation requires formal hypothesis registration, anti-p-hacking controls, out-of-sample testing, and explicit human governance ratification.

---

## 2. The 10 Foundational Academic References

### 1. Markowitz (1952) — Portfolio Selection
- **Citation:** Markowitz, H. (1952). *Portfolio Selection*. The Journal of Finance, 7(1), 77–91.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `FUTURE_ARCHITECTURE` | `NOT CURRENTLY IMPLEMENTED`
- **Core Concepts:**
  - Modern Portfolio Theory (MPT) and mean-variance optimization.
  - Expected portfolio return vs. variance/covariance of returns.
  - The concept of the **efficient frontier**: maximizing return for a given level of risk or minimizing risk for a given expected return.
  - Mathematical demonstration that asset diversification depends crucially on covariance/correlation, not simply holding multiple assets.
- **ACASH System Relevance:**
  - Foundational blueprint for the future ACASH portfolio-level risk engine.
  - Informs covariance estimation, dynamic correlation matrices, strategy capital allocation, and asset concentration constraints.
  - Essential for evaluating portfolio-wide drawdown risk rather than evaluating standalone strategies in isolation.
- **Governance Constraints:**
  - Not currently active in runtime execution. Standalone paper soak runs under zero-capital observation.

---

### 2. Modigliani & Miller (1958) — Capital Structure & Idealized Frictions
- **Citation:** Modigliani, F., & Miller, M. H. (1958). *The Cost of Capital, Corporation Finance and the Theory of Investment*. The American Economic Review, 48(3), 261–297.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `LOW DIRECT TRADING RELEVANCE` | `EPISTEMIC PRINCIPLE`
- **Core Concepts:**
  - Capital structure irrelevance theorem under idealized conditions (no taxes, no bankruptcy costs, zero transaction fees, symmetric information).
  - Demonstrates that theoretical proofs hold only under their explicit axiomatic assumptions; real-world frictions break idealized invariance.
- **ACASH System Relevance:**
  - **Research Philosophy:** Constant awareness of assumptions vs. production reality.
  - In institutional trading, real-world frictions (fees, slippage, borrowing costs, latency, funding rates, counterparty risk) dominate frictionless mathematical models.
- **Governance Constraints:**
  - Serves as a philosophical reminder: theories that assume zero friction cannot be directly deployed into live market environments.

---

### 3. Sharpe (1964) — Capital Asset Pricing Model (CAPM)
- **Citation:** Sharpe, W. F. (1964). *Capital Asset Prices: A Theory of Market Equilibrium under Conditions of Risk*. The Journal of Finance, 19(3), 425–442.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `FUTURE EVALUATION FRAMEWORK`
- **Core Concepts:**
  - Linear relationship between systematic risk ($eta$) and expected return in market equilibrium.
  - Separation of total risk into systematic (undiversifiable) market exposure and idiosyncratic (firm-specific) risk.
  - Return decomposition: $R_i = R_f + eta_i (R_m - R_f) + \epsilon_i$.
- **ACASH System Relevance:**
  - Standard benchmarking framework to distinguish market beta from active excess return (alpha).
  - Prevents treating passive market drift as proprietary algorithmic skill.
  - Informs residual return calculation and systematic factor neutralization.
- **Governance Constraints:**
  - Not an active trading signal. Serves as a post-trade evaluation and attribution metric.

---

### 4. Fama (1970) — Efficient Capital Markets & Joint-Hypothesis Problem
- **Citation:** Fama, E. F. (1970). *Efficient Capital Markets: A Review of Theory and Empirical Work*. The Journal of Finance, 25(2), 383–417.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `HIGH RESEARCH-GOVERNANCE RELEVANCE`
- **Core Concepts:**
  - Taxonomy of market efficiency: Weak form (past prices), Semi-strong form (public information), Strong form (all information, including private).
  - **The Joint-Hypothesis Problem:** Any empirical test of market efficiency is simultaneously a test of market efficiency and the underlying equilibrium asset pricing model. If anomalous returns are found, one cannot determine whether the market is inefficient or the asset pricing model is incorrect.
- **ACASH System Relevance:**
  - Critical guardrail against naive feature generation: always ask whether information is already incorporated into market prices.
  - Enforces the principle that feature novelty does not equate to incremental predictive power.
  - Prevents the false assumption that observable public data automatically implies profitable trading signals.
- **Governance Constraints:**
  - Mandates strict out-of-sample and cross-regime testing before accepting that a discovered anomaly reflects an exploitable edge.

---

### 5. Black & Scholes (1973) — Option Pricing & Replication Limits
- **Citation:** Black, F., & Scholes, M. (1973). *The Pricing of Options and Corporate Liabilities*. Journal of Political Economy, 81(3), 637–654.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `FUTURE DERIVATIVES RESEARCH ONLY`
- **Core Concepts:**
  - Continuous-time dynamic replication of derivative payoffs using underlying asset and riskless bond.
  - Derivation of the Black–Scholes partial differential equation and closed-form European option formula.
  - Critical assumptions: log-normal returns, constant volatility, frictionless continuous rebalancing, zero transaction costs, no jumps.
- **ACASH System Relevance:**
  - Theoretical benchmark for future options and derivatives feature engineering.
  - Understanding where classical assumptions fail in production: volatility smiles, implied volatility skew, discrete hedging latency, transaction costs, and jump risk.
- **Governance Constraints:**
  - Quarantined to future derivatives research. ACASH V5 spot/paper infrastructure does NOT trade or model options at present.

---

### 6. Kelly (1956) — Optimal Capital Allocation Criterion
- **Citation:** Kelly, J. L. (1956). *A New Interpretation of Information Rate*. Bell System Technical Journal, 35(4), 917–926.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `FUTURE RISK/POSITION-SIZING FRAMEWORK`
- **Core Concepts:**
  - Information-theoretic derivation of the optimal fraction of capital to bet ($f^*$) to maximize the asymptotic growth rate of wealth: $f^* = rac{p \cdot b - q}{b}$.
  - Demonstrates that betting beyond the Kelly criterion exponentially increases variance and inevitably leads to ruin.
- **ACASH System Relevance:**
  - Theoretical basis for future mathematical position sizing and risk budgeting.
  - Extreme sensitivity to estimation error: in empirical trading, estimated edge ($p, b$) is uncertain. Using "full Kelly" causes severe drawdowns.
  - ACASH standard direction: evaluate fractional Kelly (e.g., quarter-Kelly or tenth-Kelly) combined with hard capital stop limits.
- **Governance Constraints:**
  - **DO NOT implement Kelly sizing now.** Kelly is a capital sizing formula, NEVER an alpha signal. Canonical capital remains locked at $0.00.

---

### 7. Grossman & Stiglitz (1980) — The Information Acquisition Paradox
- **Citation:** Grossman, S. J., & Stiglitz, J. E. (1980). *On the Impossibility of Informationally Efficient Markets*. The American Economic Review, 70(3), 393–408.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `HIGH RESEARCH ARCHITECTURE RELEVANCE`
- **Core Concepts:**
  - Information acquisition is costly. If markets were perfectly informationally efficient, prices would fully reflect all information, eliminating any compensation for information gatherers.
  - Therefore, competitive equilibrium requires an equilibrium degree of disequilibrium: prices reflect information only to the extent that market participants are compensated for the cost of acquiring it.
- **ACASH System Relevance:**
  - Architecture principle: **Information cost vs. incremental utility.**
  - Every new data stream, alternative data feed, or complex feature incurs computational, cognitive, maintenance, and latency costs.
  - Core ACASH evaluation question: *"Does this new feature provide incremental predictive information beyond what is already captured by standard market data?"*
  - Direct protection against feature bloat.

---

### 8. Fama & French (1992, 1993) — Multi-Factor Asset Pricing Models
- **Citation:** Fama, E. F., & French, K. R. (1993). *Common Risk Factors in the Returns on Stocks and Bonds*. Journal of Financial Economics, 33(1), 3–56.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `CANDIDATE RESEARCH DIRECTION`
- **Core Concepts:**
  - Extension of single-factor CAPM to multi-factor models incorporating Size (SMB) and Value (HML) factors, later extended to Investment (CMA) and Profitability (RMW).
  - Empirical demonstration that cross-sectional stock returns are multi-dimensional.
- **ACASH System Relevance:**
  - Factor attribution and return decomposition framework.
  - Helps determine whether a candidate trading model is generating idiosyncratic alpha or merely taking on uncompensated risk factor exposures (e.g., illiquidity, carry, momentum).
- **Governance Constraints:**
  - Factor models are attribution frameworks, not active trade triggers.

---

### 9. Jegadeesh & Titman (1993) — Cross-Sectional Momentum
- **Citation:** Jegadeesh, N., & Titman, S. (1993). *Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency*. The Journal of Finance, 48(1), 65–91.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `CANDIDATE RESEARCH DIRECTION` | `REQUIRES FORMAL AUTHORIZATION`
- **Core Concepts:**
  - Empirical identification of medium-term price momentum: assets that performed well over a 3-to-12 month lookback continue to outperform over the subsequent 3-to-12 months.
  - Documentation of severe momentum crashes during market turning points.
- **ACASH System Relevance:**
  - Potential candidate strategy family for future cross-sectional or time-series research.
  - Demonstrates the necessity of rigorous risk management: unmanaged momentum strategies suffer catastrophic tail drawdowns.
- **Governance Constraints:**
  - **Momentum is NOT an active ACASH strategy.**
  - Must not be implemented, backtested, or traded without an authorized hypothesis specification and formal governance ratification.

---

### 10. Almgren & Chriss (2000) — Optimal Execution of Portfolio Transactions
- **Citation:** Almgren, R., & Chriss, N. (2000). *Optimal Execution of Portfolio Transactions*. Journal of Risk, 3(2), 5–40.
- **Epistemic Status:** `ACADEMIC_REFERENCE` | `HIGH FUTURE EXECUTION-ARCHITECTURE RELEVANCE`
- **Core Concepts:**
  - Framework for optimal liquidation/acquisition of large positions trading off market impact against timing risk.
  - Decomposition of market impact into temporary impact (instantaneous liquidity depletion) and permanent impact (information leakage).
  - Derivation of the efficient execution frontier balancing expected transaction cost vs. execution variance.
- **ACASH System Relevance:**
  - Crucial foundation for the ACASH execution layer and broker boundary.
  - Mandates execution realism: raw signal performance must be penalized by slippage, bid-ask spread, fee schedules, and market impact models.
  - Informs future TWAP/VWAP execution slicing and participation rate constraints.
- **Governance Constraints:**
  - Informs execution simulation and slippage models. Stage S11 soak runs strictly under zero-order passive observation.
