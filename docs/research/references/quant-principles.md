# The 12 Quantitative Research Laws & Heuristics

**Status:** RESEARCH_PRINCIPLE — Epistemic Heuristics & Practical Guidelines  
**Canonical Governance Authority:** Non-Executable Research Reference. Does NOT authorize backtest, paper trading, or live execution. Does NOT create HYP_003. Preserves Canonical Capital = $0.00 and NO_REAL_ORDERS = true.

---

## 1. Executive Summary & Epistemic Status

The "12 Quant Laws" represent institutional heuristics and empirical rules of thumb distilled from decades of systematic trading and quantitative research experience.

> [!WARNING]
> **Epistemic Note:**
> - These 12 principles are **heuristics and philosophical guardrails**, NOT universal, mathematically proven laws of nature.
> - Statements such as *"Risk management is the only alpha that compounds"* or *"Every edge decays the day it's discovered"* are practical operational aphorisms intended to enforce humility and survivability.
> - In ACASH, these heuristics serve as non-negotiable architectural design criteria to prevent overconfidence, backtest overfitting, and catastrophic operational failures.

---

## 2. Detailed Principles & ACASH System Mapping

```text
LAW 1: Model Humility        → Known Limitations & Out-of-Sample Survival
LAW 2: Reality vs Math       → Data Quality, Infrastructure & Execution Fidelity
LAWS 3–4: Risk & Uncertainty → Sovereign Risk Engine & Capital Preservation
LAW 5: Backtest Humility     → In-Sample Past != Future Guarantee
LAW 6: Edge Lifecycle        → Validation → Deployment → Decay Monitoring → Retirement
LAW 7: Execution Realism     → Net = Gross - Fees - Spread - Slippage - Impact - Latency
LAW 8: Capacity Limits       → Position Ceilings, ADV Participation & Liquidity Bounds
LAW 9: Complexity Control    → Parameter Parsimony & Occam's Razor
LAW 10: Tail Correlation     → Stress Testing & Regime-Dependent Breakdown
LAW 11: Sizing Primacy       → Risk Engine Dominates Raw Signal
LAW 12: Risk Compounding     → Survival as the Prerequisite for Long-Term Growth
```

---

### Law 1: Every model is wrong. A few are useful — briefly.
- **Core Principle:** Mathematical models are simplified abstractions of an extraordinarily complex, non-stationary, multi-agent dynamic system. No financial model captures ground truth.
- **ACASH Mapping:**
  - Maintain absolute model humility.
  - Document explicit assumptions and known failure modes for every quantitative module.
  - Require continuous out-of-sample monitoring; design models for robust graceful degradation rather than perfection.

---

### Law 2: Reality is always messier than the mathematics.
- **Core Principle:** Real-world trading environments contain network drops, socket timeouts, stale feeds, exchange downtime, partial fills, API rate limits, non-linear slippage, and subtle data corruption.
- **ACASH Mapping:**
  - Build fail-closed infrastructure first (e.g., Gate G10 telemetry, Gate G7 continuous soak).
  - Invest in rigorous deterministic logging, chained SHA-256 event journaling, and immutable audit manifests.
  - Treat execution fidelity and operational uptime as prerequisites to strategy evaluation.

---

### Law 3: Risk is what hasn't happened yet.
- **Core Principle:** Historical price series only reflect one realized path of an infinite distribution. Severe tail events (black swans, structural breaks, liquidity vacuums) are rarely present in recent backtest samples.
- **ACASH Mapping:**
  - Stress-test all risk models against synthetic volatility shocks, gap events, and liquidity drying scenarios.
  - Enforce absolute position and capital limits that do not depend on statistical distribution normality.

---

### Law 4: The market pays you to bear uncertainty.
- **Core Principle:** In equilibrium, expected returns are compensation for bearing systematic risks that other market participants are unwilling or unable to hold. A risk-free positive return does not exist in competitive markets.
- **ACASH Mapping:**
  - Identify the economic source of return: ask who is on the other side of the trade, why they are trading, and what risk is being absorbed.
  - Differentiate between genuine statistical compensation for liquidity provision/risk bearing vs. unhedged tail exposure.

---

### Law 5: A backtest measures the past, not the future.
- **Core Principle:** A backtest is an accounting historical simulation conditional on past market structure. It proves only that a given set of rules produced a specific curve on historical data, subject to lookahead bias, selection bias, and survival bias.
- **ACASH Mapping:**
  - Enforce strict separation between In-Sample (IS), Out-of-Sample (OOS), and Walk-Forward optimization.
  - Backtesting remains locked under Phase 8.5 / Phase 14 governance until explicit human authorization is granted.
  - A successful backtest is never evidence of future profitability.

---

### Law 6: Every edge decays the day it's discovered.
- **Core Principle:** Alpha is non-stationary. As information spreads, capital allocates, or market structure shifts, trading edges decay and eventually disappear or invert.
- **ACASH Mapping:**
  - Formalize the complete **Edge Lifecycle**:
    $$	ext{Birth} 	o 	ext{Validation} 	o 	ext{Staged Deployment} 	o 	ext{Active Monitoring} 	o 	ext{Decay Detection} 	o 	ext{Quarantine} 	o 	ext{Retirement}$$
  - Implement real-time rolling performance, information coefficient, and Sharpe decay monitors.

---

### Law 7: Costs and slippage kill most "profitable" strategies.
- **Core Principle:** Academic and retail strategies frequently exhibit high theoretical Sharpe ratios that completely collapse once exchange maker/taker fees, bid-ask spreads, non-linear market impact, and latency slippage are subtracted.
- **ACASH Mapping:**
  - Apply the ACASH Net Equation to every simulation:
    $$	ext{Net Return} = 	ext{Gross Return} - 	ext{Exchange Fees} - 	ext{Spread} - 	ext{Slippage} - 	ext{Market Impact} - 	ext{Borrow Costs}$$
  - Reject any candidate model whose edge does not comfortably exceed 2.5x estimated transaction frictions.

---

### Law 8: Capacity is finite — size destroys edges.
- **Core Principle:** Every strategy has a liquidity ceiling. As assets under management (AUM) grow, the strategy's market impact erodes its own profitability until the marginal return equals zero.
- **ACASH Mapping:**
  - Calculate strategy capacity bounds based on Average Daily Volume (ADV) participation rates (e.g., maximum 1–2% of 5-minute volume).
  - Reject strategies that rely on micro-cap or thin liquidity pools where execution cannot scale.

---

### Law 9: More parameters, less out-of-sample survival.
- **Core Principle:** Every additional degree of freedom increases the probability of fitting noise rather than signal. Complex multi-parameter models invariably fit the past perfectly and fail catastrophically in the future.
- **ACASH Mapping:**
  - Practice radical parameter parsimony (Occam's razor).
  - Impose strict complexity penalties; require models with few parameters and clear economic mechanisms.
  - Falsify candidate ideas that require fine-tuning of thresholds across different time windows.

---

### Law 10: Correlation isn't diversification — it vanishes when you need it most.
- **Core Principle:** Linear correlation between assets and strategies typically increases towards 1.0 during market crashes and liquidity panics, destroying naive portfolio diversification.
- **ACASH Mapping:**
  - Analyze tail risk, drawdown correlation, and regime-dependent copulas rather than simple static Pearson correlation.
  - Evaluate multi-strategy risk under synchronized stress regimes.

---

### Law 11: Position sizing matters more than the signal.
- **Core Principle:** A mediocre signal with mathematically disciplined position sizing will survive and compound. A brilliant signal with flawed, oversized position sizing will inevitably hit a drawdown that causes ruin.
- **ACASH Mapping:**
  - Strictly decouple the **Alpha Engine** (signal generation) from the **Sovereign Risk Engine** (position sizing and capital allocation).
  - The signal may generate directional conviction, but the Risk Engine unilaterally dictates exposure based on volatility, liquidity, and portfolio constraints.

---

### Law 12: Risk management is the only alpha that compounds.
- **Core Principle:** Compounding requires avoiding catastrophic drawdowns. A 50% loss requires a 100% gain to break even; a 90% loss requires a 900% gain. Capital preservation is the mathematical prerequisite for geometric wealth accumulation.
- **ACASH Mapping:**
  - Capital preservation is the foundational mandate of ACASH.
  - The system explicitly defaults to 100% cash allocation ("NOWHERE") whenever market risk, telemetry uncertainty, or data integrity fails.
