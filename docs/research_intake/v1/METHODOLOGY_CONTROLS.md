# ACASH Research Methodology & Quantitative Controls Standard

## 1. Overview & Architectural Role

This document establishes the mandatory quantitative, statistical, and empirical controls for the ACASH quantitative research lifecycle. It serves as an unyielding standard to prevent data snooping, selection bias, survivorship bias, multiple-testing contamination, and execution friction underestimation.

---

## 2. Core Methodology Control Standards (Sections A – P)

### A. The Three-Layer Validation Question
Every proposed quantitative candidate must successfully resolve three distinct, sequential questions before consideration:
1. **Plausible Economic / Microstructure Mechanism**: Does the underlying driver (e.g., inventory balancing, order flow imbalance, hedging demand, informational latency) plausibly exist in academic literature and actual market structure?
2. **Incremental Predictive Information**: Does a mathematically defined, pre-registered signal provide statistically significant forecast power regarding future conditional return distributions beyond unconditional baseline controls?
3. **Survival of Execution Friction**: Does the gross theoretical edge survive realistic transaction costs, market impact, slippage, latency, financing, and exchange fees under executable bid/ask semantics?

### B. Source Claims Are Not Empirical Evidence
All metrics, win rates, profit factors, drawdowns, and returns originating from creator videos, courses, vendor marketing, or social media must be formally classified as `EXTERNAL_UNVERIFIED_CLAIM`.
- Statements such as "982% return", "PF 1.49", "57% win rate", or "best timeframe is 5-minute" have zero evidentiary weight.
- External claims represent historical context explaining why a mechanism was catalogued; they do NOT constitute prior empirical verification.

### C. Complete & Uncompromising Execution Cost Accounting
Gross backtest returns are mathematically meaningless. Every future empirical candidate must account for all relevant frictions:
- **spread**: Half-spread crossing cost on market orders or limit order queue positioning models.
- **commission**: Explicit per-share, per-contract, or broker commissions and turnover fees.
- **slippage**: Empirical function of order size relative to available depth.
- **swap**: Financing and overnight swap fees, margin interest, or CFD financing.
- **market impact**: Dynamic market impact (e.g., Almgren-Chriss or square-root law).
- **borrow**: Hard-to-borrow fees, borrow recall risk, and locate fees.
- **exchange fees**: Regulatory and exchange transaction/clearing fees (SEC/FINRA fees).
- **futures roll**: Calendar spread transaction costs, roll timing yield drag, and tick-size frictions.
- **option spread**: Wide strike-dependent spreads, contract assignment/exercise fees, pin risk, and margin maintenance.
- *Rule*: While not all friction types apply to every instrument, omitting an applicable friction constitutes an immediate failure of the research contract.

### D. Bar-Path Ambiguity & Strict Fail-Closed Rule
Standard OHLC (Open, High, Low, Close) price bars discard intrabar sequence information.
- If a strategy establishes an entry, stop-loss (SL), and take-profit (TP) where both SL and TP lie within the high-low range of a single bar, the exact outcome sequence is mathematically indeterminate from OHLC data alone.
- **bar-path ambiguity**: Never assume a favorable fill sequence (e.g., assuming TP was hit before SL).
- **Mandatory Policy**:
  1. Implement a strict **fail-closed convention**: evaluate the worst-case intrabar path (assume SL is triggered first), OR
  2. Require high-resolution tick-level or sub-minute data with verified microsecond sequencing to adjudicate fills deterministically.

### E. Data Feed Semantics & Quote Dissemination
The term "tick" is ambiguous and mathematically dangerous across different market venues:
- **Direct Exchange Feeds (ITCH/OUCH, CME MDP 3.0)**: Order-by-order, deterministic queue state.
- **Consolidated Tape (SIP / NBBO)**: Dissemination latency creates localized crossed or stale quotes relative to exchange direct feeds.
- **Broker Tick Feeds**: Often filtered, subsampled, or synthetic mid-prices.
- **CFD Tick Volume**: Represents dealer platform update frequency, NOT market transaction volume or aggregate traded contracts.
- **Equity Consolidated Volume vs. Futures Volume**: Distinct settlement and reporting rules.
- **Option OPRA Feeds**: High-bandwidth, message-suppressed consolidated option quotes.
- *Rule*: Research models must specify exact feed semantics. CFD tick volume cannot be substituted for CME futures volume.

### F. Canonical Timezone & Session Authority
Arbitrary vendor labels such as "broker time", "server time", or "local PC time" are strictly prohibited in research definitions.
- All timestamps must be anchored to canonical market-local exchange time (e.g., US Equity / Index Futures: America/New_York) and stored in UTC.
- Research specifications must explicitly account for:
  - Daylight Saving Time (DST) transitions (US vs. European DST shift divergence).
  - Exchange holiday schedules and scheduled early closes (e.g., 13:00 ET bond/equity closes).
  - Trading halt handling (LULD halts, CME circuit breakers).

### G. Multiple Testing & Rigorous Trial Ledger (K)
Every empirical test, indicator variation, parameter adjustment, filter addition, or exploratory scan increments the total trial count $K$.
- **multiple testing**: This includes:
  - Human-driven interactive parameter scans.
  - Automated grid searches and AI-driven exploratory routines.
  - Deleted, discarded, or unpublished scripts ("file-drawer" trials).
  - Variations in lookback windows, stop distances, target multiples, session filters, or asset lists.
- **Example of $K$ Expansion**: Testing 3 opening windows $\times$ 3 stop-loss distances $\times$ 3 take-profit targets $\times$ 3 volume multipliers yields:
  $$3 \times 3 \times 3 \times 3 = 81 \text{ empirical trials}$$
- Every trial must be logged in a sealed cryptographic ledger. Significance thresholds must be adjusted using family-wise error rate (FWER) controls or False Discovery Rate (FDR) adjustments, including the Deflated Sharpe Ratio (DSR) and White's Reality Check.

### H. Mandatory Negative & Placebo Controls
A proposed candidate strategy cannot be evaluated in isolation. Every empirical evaluation must incorporate matched baseline, negative control, and random control designs:
- **ORB Breakout**: Compare against an identical breakout logic triggered at random, non-opening times of day or matched volatility intervals.
- **Fair Value Gap (FVG)**: Compare performance against mechanically identical price displacements lacking the 3-candle FVG geometry.
- **Volume Spike**: Compare against identical price displacements occurring under normal/median volume conditions.
- **Order Flow Imbalance (OFI)**: Compare against time-shuffled or cross-sectionally permuted order flow series.
- **Relative Value / Pairs**: Compare against bootstrapped random pairs with matched market cap and industry classification.

### I. Out-of-Sample (OOS) Integrity & Prospective Isolation
- **Development / In-Sample (IS)**: Used exclusively for initial model specification.
- **hard OOS**: Must remain completely untouched and uninspected until the model and its parameters are permanently frozen.
- *Contamination Invariant*: Once hard OOS data has been inspected or used to guide model refinements, it is permanently contaminated and converts into In-Sample data.
- **prospective shadow observation**: The ultimate validation layer is real-time forward prospective tracking without execution.

### J. The "100 Trades" Fallacy: 100 Trades Is Not Proof
The heuristic that "100 trades proves a strategy" is `INCORRECT_AS_STATED`.
- **100 trades is not proof**: 100 trades is a bare empirical checkpoint, not a mathematical proof of edge.
- Statistical significance is a function of:
  - Effect size (mean excess return over benchmark).
  - Variance, skewness, and kurtosis of return distribution.
  - Serial dependence and autocorrelation.
  - Number of independent market regimes traversed (e.g., high vs. low vol, bull vs. bear).
  - Trial count $K$ accumulated during research.

### K. Multi-Dimensional Performance Evaluation: Profit Factor Is Not Supreme
**profit factor is not supreme**: Profit Factor (PF) is an incomplete, fragile ratio that ignores drawdowns, tail risk, and autocorrelation.
- **Mandatory Policy**: `NO_SINGLE_METRIC_IS_DECISIVE`.
- Evaluation must report a balanced multi-dimensional diagnostic matrix:
  - Net return and expectancy per dollar risked.
  - Annualized Sharpe Ratio and Sortino Ratio.
  - Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR).
  - Maximum Drawdown (MDD), duration of drawdown, and Calmar Ratio.
  - Tail risk measures: Expected Shortfall (CVaR at 95% and 99%), Value at Risk (VaR).
  - Turnover, holding period distribution, and capacity estimation.
  - Regime conditional performance (bull, bear, sideways, high-vol, low-vol).

### L. Beta Drift & Unconditional Equity Drift Controls
Long-only equity or index strategies often confuse broad macroeconomic drift with alpha.
- A long strategy in Nasdaq or S&P 500 that achieves positive returns during a secular bull market may simply possess positive market beta.
- All candidate strategies must be benchmarked against:
  - Buy-and-hold underlying asset return over the identical period.
  - Time-matched exposure controls (e.g., random entry with identical holding duration).
  - Factor-adjusted alphas (Fama-French 5-factor or Q-factor model).

### M. Elimination of Subjective Terminology
Discretionary trading terminology such as "clean level", "obvious breakout", "respecting the moving average", "strong momentum", or "whale activity" cannot be scientifically evaluated.
- All signals must be machine-deterministic and fully codified into mathematical expressions before accessing data.
- Any subjective interpretation that cannot be reduced to deterministic code remains catalogued as an unsupported discretionary heuristic.

### N. Parameter Robustness & Perturbation Boundaries
Testing parameter perturbations ($\pm 10\%$, $\pm 20\%$) around an optimal point provides diagnostic evidence of surface stability, but:
- Stability under perturbation is a necessary condition, NOT a sufficient condition for predictive validity.
- Smooth parameter response surfaces can still be overfitted to sample-wide structural regimes.

### O. Human Discretion Requires Formal A/B Validation
Claims that "human discretion adds value" or that "discretionary intervention improves prop passing rates" have no baseline standing.
- Discretionary claims require prospective, pre-registered A/B testing where human decisions are logged in real time against an unmanaged systematic benchmark.
- Without prospective randomized verification, discretion is treated as unquantified cognitive bias.

### P. Sovereign Capital Authority
Research findings—regardless of statistical significance, Sharpe ratio, or academic pedigree—carry zero authorization to allocate capital.
- $\text{PAPER\_ELIGIBLE} \neq \text{PAPER\_AUTHORIZED}$.
- $\text{LIVE\_REVIEW} \neq \text{LIVE\_AUTHORIZED}$.
- Current Repository Status:
  - Real Capital Authority: **$0.00**
  - Order Execution Boundary: `NO_REAL_ORDERS = true`
