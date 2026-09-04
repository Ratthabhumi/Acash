# ACASH Strategy Forensic Evaluation & Risk Analysis Framework
## Quantitative Research, Strategy Evaluation & Risk Governance Specification

> **Document Type:** Quantitative Research / Strategy Evaluation / Risk Governance Specification  
> **Status:** Research Specification — Documentation Only  
> **Parent Governance:** ADR-022 (Market-Adaptive, Strategy-Agnostic & Event-Aware Trading Governance)  
> **Date:** 2026-09-04  
> **Version:** 1.0.0  

---

> [!IMPORTANT]
> **STRICT GOVERNANCE BOUNDARY & NON-AUTHORIZATION STATEMENTS:**
> - **THIS DOCUMENT DOES NOT AUTHORIZE LIVE TRADING.**
> - **THIS DOCUMENT DOES NOT AUTHORIZE CAPITAL ALLOCATION.**
> - **THIS DOCUMENT DOES NOT CHANGE GATE A OR GATE B STATUS.**
> - **THIS DOCUMENT DOES NOT IMPLEMENT ANY STRATEGY OR EXECUTION ENGINE.**
> - **THIS DOCUMENT DOES NOT APPROVE OR ENDORSE EA ALICE OR ANY COMMERCIAL EA.**
> - **CAPITAL ALLOCATION AUTHORITY REMAINS STRICTLY $0.00.**

---

## 1. Executive Summary & Objective

This specification establishes a permanent, mathematically rigorous, and strategy-agnostic framework for evaluating **ANY** trading strategy candidate considered for deployment within the ACASH quantitative infrastructure.

The framework applies identically across all strategy archetypes:
- ACASH-native quantitative models (Momentum, Mean Reversion, Statistical Arbitrage)
- Commercial Expert Advisors (EAs) and vendor algorithms
- Grid, Martingale, Averaging, and Recovery systems
- Machine Learning / Deep Learning / Reinforcement Learning models
- Discretionary or hybrid algorithmic strategies
- Third-party candidate systems (e.g., EA Alice)
- Future unknown or emergent strategy classes

The objective is **NOT** to implement an evaluation engine today. The objective is to permanently codify **WHAT** ACASH must measure, **HOW** empirical evidence must be gathered, and **UNDER WHAT CONDITIONS** capital may be allocated before any strategy touches capital.

```
                             Strategy Candidate
                                     │
                 ┌───────────────────┼───────────────────┐
                 ▼                   ▼                   ▼
           ACASH-Native         External EA          ML / DL Model
           (e.g. Trend)        (e.g. Alice)          (e.g. Kronos)
                 │                   │                   │
                 └───────────────────┼───────────────────┘
                                     ▼
                       IDENTICAL EVALUATION FRAMEWORK
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
      Performance                Risk & Tail              Robustness &
       Forensics                  Survival                  Regimes
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     ▼
                             Strategy × Regime
                                     ▼
                          Near-Death & Margin Risk
                                     ▼
                          Execution Microstructure
                                     ▼
                          Capital Requirement Audit
                                     ▼
                         FAIR STRATEGY TOURNAMENT
                           (Frozen Prior Rules)
                                     ▼
                            GOVERNANCE VERDICT
                                     │
                       ┌─────────────┼─────────────┐
                       ▼             ▼             ▼
                     $0.00        $Small        $Scale
                  (Unproven)     (Proven)      (Mature)
```

---

## 2. Absolute Governance Principles

### 2.1 Strategy Neutrality & Anti-Dogmatism
ACASH operates under absolute strategy neutrality. Dogmatic assertions are strictly prohibited in research and governance:
- `"Grid = bad"` $\to$ **PROHIBITED**
- `"AI = superior"` $\to$ **PROHIBITED**
- `"Internal strategy = superior"` $\to$ **PROHIBITED**
- `"External EA = inferior"` $\to$ **PROHIBITED**

Strategy quality is determined exclusively from reproducible, statistically significant, risk-adjusted empirical evidence.

### 2.2 Core Governing Question
Every candidate strategy must answer a single empirical question:
$$\text{"Does this strategy demonstrate a robust, reproducible, risk-adjusted economic edge under observed market conditions while remaining strictly within acceptable tail-risk, margin-consumption, and operational-risk boundaries?"}$$

### 2.3 Engineering Quality $\neq$ Trading Alpha
Sophisticated software engineering, clean modular architecture, formal state machines, and cryptographic reconciliation do not produce economic edge. They protect capital from operational failure. Conversely, an architecturally simple external algorithm may possess genuine market alpha. If evidence proves that an external strategy outperforms an internal model, ACASH must accept the empirical finding without bias.

### 2.4 Default Capital Allocation: $0.00
If a strategy fails any mandatory evaluation layer, or if data is insufficient, ambiguous, or unverified, the mandatory outcome is:
$$\text{Capital Allocation} = \$0.00$$

---

## 3. Relationship to ADR-022

This specification is an implementation-independent extension of [ADR-022 (Market-Adaptive, Strategy-Agnostic & Event-Aware Trading Governance)](./market_adaptive_strategy_governance.md).

It reinforces ADR-022 across all dimensions:
1. **Flexible Decision Making + Fixed Safety Guardrails:** Dynamic strategy selection operates exclusively within hard, non-negotiable risk limits.
2. **Strategy $\times$ Regime Evaluation:** Alpha is evaluated as a conditional property of market regimes, not an unconditional scalar return.
3. **Event-Aware Risk Governance:** High-impact economic releases are treated as distinct risk regimes requiring graduated operational policies.
4. **Anti-Bias Governance:** Evaluator identity is decoupled from strategy ownership; claims are strictly categorized by epistemic evidence level.
5. **Frozen Tournament Criteria:** Evaluation criteria must be sealed prior to tournament execution to eliminate retrospective goalpost shifting.

---

## 4. The 12 Mandatory Strategy Evaluation Layers

Every strategy candidate must be evaluated across twelve distinct forensic layers before capital consideration.

```
┌────────────────────────────────────────────────────────────────────────┐
│               THE 12 STRATEGY FORENSIC EVALUATION LAYERS               │
├────────────────────────────────────────────────────────────────────────┤
│  Layer 1: Performance Forensics (Return, Drawdown, Expectancy)         │
│  Layer 2: Position & Basket Forensics (Baskets, Exposure, Duration)   │
│  Layer 3: Position Sizing & Progression Mechanics (Linear/Martingale)  │
│  Layer 4: Hedge Forensics (Ratio, Timing, Unwind, Net Residual)        │
│  Layer 5: Capital & Margin Risk (Peak Margin, Liquidation Distance)   │
│  Layer 6: Tail Risk & Survival Stress Testing (10 Stress Scenarios)    │
│  Layer 7: Near-Death Analysis (Close-to-Liquidation Recovery Traps)    │
│  Layer 8: Cash-Flow & Capital-Injection Audit (Organic vs Rescued)     │
│  Layer 9: Robustness & Generalization (OOS, Walk-Forward, Monte Carlo) │
│  Layer 10: Regime Analysis (Strategy × Regime Performance Matrix)      │
│  Layer 11: Event-Aware Analysis (High-Impact Economic Release Behavior)│
│  Layer 12: Execution Microstructure (Slippage, Spread, Fill Latency)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Layer 1 — Performance Forensics
Measures fundamental risk-adjusted return properties.

| Metric | Mathematical Description | Governance Standard |
|---|---|---|
| **Net Return** | Total realized P/L after all costs | Must be net of spread, commission, swap, slippage |
| **CAGR** | Compound Annual Growth Rate | Computed over realistic multi-year spans |
| **Maximum Closed Drawdown** | Peak-to-trough decline in closed balance | Standard accounting drawdown |
| **Maximum Floating Drawdown** | Peak-to-trough decline in total equity | **Primary drawdown authority**; must capture unclosed floating losses |
| **Drawdown Duration** | Time from equity peak to recovery | Measures capital lock-up duration |
| **Recovery Factor** | Net Return / Max Floating Drawdown | Ratio of economic gain to peak distress |
| **Sharpe Ratio** | $\frac{\mathbb{E}[R - R_f]}{\sigma(R)}$ | Canonical Newey-West adjusted; period discipline enforced |
| **Sortino Ratio** | $\frac{\mathbb{E}[R - R_f]}{\sigma_{\text{down}}(R)}$ | Penalizes downside volatility only |
| **Calmar Ratio** | $\frac{\text{CAGR}}{\text{Max Floating Drawdown}}$ | Measures return relative to catastrophic risk |
| **Profit Factor** | $\frac{\sum \text{Gross Profits}}{\sum \text{Gross Losses}}$ | Must strictly exceed 1.0 net of all frictions |
| **Expectancy** | $\mathbb{E}[\text{Trade P/L}] = (P_{\text{win}} \cdot \bar{W}) - (P_{\text{loss}} \cdot \bar{L})$ | Must be strictly positive |
| **Win Rate** | Count(Win) / Count(Total) | **NOT EVIDENCE OF SAFETY** |
| **Average Win / Average Loss** | $\bar{W} / \bar{L}$ | Win-loss payout symmetry |
| **Return Distribution & Skewness** | Third standardized moment $\tilde{\mu}_3$ | Negative skew reveals hidden tail risk |
| **Tail Loss (CVaR / Expected Shortfall)** | $\mathbb{E}[R \mid R \le \text{VaR}_\alpha]$ | Quantifies expected loss beyond confidence threshold |

> [!WARNING]
> **MANDATORY INVARIANT: WIN RATE IS NOT EVIDENCE OF SAFETY**  
> High win rates (e.g., 90–98%) routinely coexist with catastrophic negative skewness and liquidation risk (e.g., picking up nickels in front of a steamroller). A 95% win rate strategy with an unhedged averaging tail can lose 100% of accumulated capital in a single unrecovered adverse move.

---

### Layer 2 — Position & Basket Forensics
For strategies using multiple concurrent positions, grids, scaling, averaging, or recovery mechanics, performance must be evaluated at the **Basket Level** rather than treating each fill as an independent bet.

- **Maximum Positions per Basket:** Peak count of concurrent open positions belonging to a single logical sequence.
- **Average Positions per Basket:** Mean position count per resolved sequence.
- **Maximum Basket Gross Exposure:** Peak aggregated notional exposure across all legs in a basket.
- **Basket Duration (Mean & Max):** Elapsed time from basket inception (first leg) to complete resolution (final exit).
- **Maximum Adverse Excursion (MAE):** Maximum floating loss experienced by the basket before exit.
- **Maximum Favorable Excursion (MFE):** Maximum floating gain achieved by the basket before exit.
- **Recovery Behavior:** Rate and trajectory at which floating losses normalize toward the exit target.
- **Entry Spacing Dynamics:** Distance between successive orders (fixed pips, ATR-dynamic, or volatility-scaled).
- **Exit Structure:** Uniform basket TP, trailing stop, partial close, or individual leg exits.
- **Basket P/L vs. Leg P/L:** Individual leg profits are meaningless if earlier legs are closed at catastrophic losses.

---

### Layer 3 — Position Sizing & Progression Mechanics
Detects and classifies the mathematical progression governing lot sizing across consecutive orders.

$$\text{Lot Size Progression: } L_n = L_0 \cdot f(n)$$

| Progression Type | Formula $f(n)$ | Growth Rate | Risk Classification |
|---|---|---|---|
| **Fixed Sizing** | $f(n) = 1$ | $O(1)$ | Low structural leverage drift |
| **Linear Sizing** | $f(n) = 1 + c \cdot n$ | $O(n)$ | Moderate margin accumulation |
| **Geometric / Multiplier** | $f(n) = k^n \quad (k > 1)$ | $O(k^n)$ | **High / Exponential margin exhaustion** |
| **Classical Martingale** | $f(n) = 2^n$ | Exponential | **Extreme / Critical ruin probability** |
| **Anti-Martingale** | Scales with profits | Path-dependent | Controlled downside |
| **Volatility-Scaled (ATR)** | $f(n) \propto \frac{1}{\text{ATR}_n}$ | Inverse volatility | Dynamically bounded |

**Forensic Requirements:**
1. Estimate maximum theoretical exposure at level $N_{\text{max}}$.
2. Calculate margin exhaustion point: at what level does Free Margin reach zero?
3. Calculate capital required to survive $K$ standard deviation market extensions.
4. **Evidence-based classification:** ACASH must not label a strategy as "Martingale" merely because it opens multiple positions. The classification must be proven mathematically from observed sizing progression.

---

### Layer 4 — Hedge Forensics
For strategies employing hedging, opposite-side positioning, or lock mechanisms, the framework evaluates whether risk is genuinely mitigated or merely transformed into a complex margin lock.

$$\text{Hedge Ratio: } H(t) = \frac{|\text{Hedged Exposure}(t)|}{|\text{Directional Exposure}(t)|}$$

**Forensic Dimensions:**
- **Hedge Activation Trigger:** Distance, drawdown percentage, volatility breach, or indicator crossover.
- **Hedge Sizing:** Full hedge ($H=1.0$), partial hedge ($H < 1.0$), or over-hedge ($H > 1.0$).
- **Hedge Timing & Latency:** Execution delay between trigger condition and hedge fill.
- **Hedge Unwind Logic:** Mathematical criteria for closing hedge legs without realizing locked losses.
- **Residual Directional Exposure:** Net delta exposed during hedged states.
- **Hedge Carrying Cost:** Accumulated spread costs, double commissions, negative swap drag, and margin lockup.

> [!IMPORTANT]
> **MANDATORY INVARIANT: HEDGING DOES NOT ELIMINATE RISK**  
> Hedging transforms directional market risk into basis risk, spread-widening risk, swap drag, and execution unwind risk. In retail MT5 brokers, a fully hedged position ($H=1.0$) still consumes margin under retail hedging rules and remains exposed to spread expansion and overnight financing costs.

---

### Layer 5 — Capital & Margin Risk
Evaluates the strategy's consumption of broker credit and capital survivability.

- **Margin Used & Margin Level:** Peak margin utilization and minimum observed margin level:
  $$\text{Margin Level \%} = \frac{\text{Equity}}{\text{Margin Used}} \times 100$$
- **Gross vs. Net Exposure:**
  $$\text{Gross Exposure} = \sum |V_i| \cdot P_i \cdot \text{ContractSize}$$
  $$\text{Net Exposure} = \left| \sum \text{side}_i \cdot V_i \cdot P_i \cdot \text{ContractSize} \right|$$
- **Effective Leverage:** $\frac{\text{Gross Exposure}}{\text{Equity}}$
- **Liquidation Distance:** Point distance to broker stop-out level under adverse price movement:
  $$\Delta P_{\text{stop-out}} = \frac{\text{Equity} - \text{Margin Used} \cdot (\text{SO Level \%} / 100)}{\text{Gross Volume} \cdot \text{Tick Value}}$$
- **Peak Capital Requirement:** Total cash capital required to survive historical adverse excursions without approaching margin call thresholds.

> [!CAUTION]
> **MANDATORY INVARIANT: PROFITABILITY CANNOT BE EVALUATED INDEPENDENTLY FROM CAPITAL REQUIREMENTS**  
> A strategy that produces +$30 average profit per basket while requiring -$4,000 floating drawdown is **NOT** a low-risk $30 strategy. It is a $4,000 capital commitment yielding a 0.75% return with high liquidation risk.

---

### Layer 6 — Tail Risk & Survival Stress Testing
Mandatory stress testing evaluates strategy behavior under ten adverse market dislocations.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   10 MANDATORY STRESS TEST SCENARIOS                   │
├────────────────────────────────────────────────────────────────────────┤
│  1. Persistent Directional Trend (Uninterrupted 500-pip move)         │
│  2. Extreme Volatility Spike (VIX / ATR 400% expansion)               │
│  3. Weekend / Overnight Gap (Price gap across resting SL/TP)           │
│  4. Macro News Shock (Instantaneous multi-sigma price jump)            │
│  5. Spread Expansion (Spread widening to 10x normal during rollover)   │
│  6. Execution Slippage (Adverse fill slippage of 5–50 pips)            │
│  7. Liquidity Deterioration (Thin book, partial fills, requotes)       │
│  8. Execution Rejection (Broker reject code 10027, 10014, 10018)       │
│  9. Terminal / Network Disconnect (Extended outage during open basket) │
│  10. Delayed Recovery (Prolonged multi-month consolidation at adverse) │
└────────────────────────────────────────────────────────────────────────┘
```

For each scenario, the framework estimates:
- Minimum projected Equity and Free Margin
- Maximum projected Gross Exposure and Position Count
- Margin Level at peak distress
- Survival Classification:
  - **SAFE:** Equity remains $> 80\%$ of nominal; Margin Level $> 500\%$.
  - **WARNING:** Equity between $50–80\%$; Margin Level $300–500\%$.
  - **DANGER:** Equity between $20–50\%$; Margin Level $150–300\%$.
  - **CRITICAL:** Equity $< 20\%$; Margin Level approaching stop-out ($\le 150\%$).
  - **LIQUIDATION / FAILURE:** Margin call or stop-out triggered ($\le 50\%$).

---

### Layer 7 — Near-Death Analysis
Identifies whether historical survival was due to mathematical edge or statistical survivorship bias.

**Definition of a Near-Death Event:**
Any occurrence where a strategy:
1. Consumed $> 70\%$ of available equity in floating drawdown.
2. Reached a Margin Level $< 200\%$.
3. Approached within $\le 30$ pips of broker stop-out.
4. Required external human intervention or risk override to prevent liquidation.
5. Recovered only after experiencing an adverse price move that had a $< 1\%$ historical probability.

> [!WARNING]
> **MANDATORY INVARIANT: RECOVERY DOES NOT PROVE SAFETY**  
> A strategy that repeatedly experiences Near-Death Events before recovering is structurally unsafe. In finite sample sizes, a strategy with an absorbing ruin barrier that has not yet hit ruin will look superficially profitable. ACASH rejects strategies that rely on tail survival luck.

---

### Layer 8 — Cash-Flow & Capital-Injection Audit
Strictly separates trading performance from exogenous balance modifications.

$$\text{True Trading P/L} = \Delta \text{Balance} - (\text{Deposits} - \text{Withdrawals}) - \text{Transfers} - \text{Adjustments}$$

**Forensic Audit Rules:**
1. Never confuse Account Balance Growth with Trading Alpha.
2. Detect whether external capital was injected during a drawdown to prevent margin stop-out.
3. Record formal finding:
   $$\text{"Was the strategy able to recover using only its original capital allocation?"} \in \{\text{YES}, \text{NO}, \text{UNKNOWN}\}$$
4. Any strategy requiring external capital injection to avoid liquidation receives an immediate **CRITICAL FAIL**.

---

### Layer 9 — Robustness & Generalization
Prevents in-sample overfitting and data mining bias.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   ROBUSTNESS VERIFICATION PIPELINE                     │
├──────────────────┬──────────────────┬──────────────────────────────────┤
│  In-Sample (IS)  │ Validation (VAL) │ Out-of-Sample (OOS)             │
│  Parameter Scan  │ Hurdle Selection │ Unseen Market Data               │
│  (60% Data)      │ (20% Data)       │ (20% Data — Strict Zero Leakage) │
└──────────────────┴──────────────────┴──────────────────────────────────┘
                         │
                         ▼
        Walk-Forward Analysis (Rolling Windows)
                         │
                         ▼
        Monte Carlo Resampling & Trade Shuffling
                         │
                         ▼
        Cost & Microstructure Sensitivity (Spread × 2, Slippage × 2)
```

- **Parameter Sensitivity:** Alpha must not exist as an isolated "spike" in parameter space. Wide parameter plateaus indicate structural robustness.
- **Monte Carlo Permutation:** Trade order randomization to establish distribution of maximum drawdown.
- **Cost Sensitivity:** Recalculate performance under $2\times$ spread and $2\times$ commission. Fragile strategies collapse under friction.

---

### Layer 10 — Regime Analysis
Evaluates performance across multi-dimensional market regimes rather than aggregate historical return.

$$\text{Alpha} = f(\text{Strategy}, \text{Regime})$$

```
                            MARKET REGIMES
     ┌──────────────────────┬──────────────────────┐
     │   Low Volatility     │   High Volatility    │
┌────┼──────────────────────┼──────────────────────┤
│ T  │ Trend + Low Vol      │ Trend + High Vol     │
│ R  │ (Steady Momentum)    │ (Violent Breakouts)  │
│ E  │                      │                      │
├────┼──────────────────────┼──────────────────────┤
│ R  │ Range + Low Vol      │ Range + High Vol     │
│ N  │ (Tight Consolidation)│ (Wide Mean-Reverting)│
│ G  │                      │                      │
└────┴──────────────────────┴──────────────────────┘
```

**Regime Dimensions:**
- **Trend Regime:** Strong Trend, Weak Trend, Mean-Reverting Range.
- **Volatility Regime:** Compressed Volatility, Normal Volatility, Volatility Expansion, Crisis Spike.
- **Liquidity Regime:** High Liquidity (NY/London overlap), Thin Liquidity (Rollover, Asian off-hours).
- **Macro / Event Proximity:** Quiet baseline vs. Pre-Event / Event dislocation.

> [!NOTE]
> **RESEARCH HYPOTHESIS vs. AXIOMATIC FACT**  
> Assertions such as *"Grid works in range"* or *"Trend following works in high volatility"* are **testable research hypotheses**, not proven facts. The framework must empirically demonstrate that performance diverges statistically across identified regimes.

---

### Layer 11 — Event-Aware Analysis
Evaluates strategy behavior in the vicinity of scheduled and unscheduled macro announcements.

**Observation Windows:**
- **Pre-Event Window ($T - 60\text{m}$ to $T$):** Does the strategy accumulate dangerous exposure immediately before news?
- **Event Shock Window ($T$ to $T + 15\text{m}$):** How does the strategy handle spread expansion, slippage, and price jumps?
- **Post-Event Window ($T + 15\text{m}$ to $T + 4\text{h}$):** How does the strategy recover or exit dislocated positions?

**Graduated Event Policies (Research Candidates):**
1. **ALLOW:** Unrestricted operation (only if verified tail-safe under event conditions).
2. **REDUCE:** Scale position sizing by factor $\kappa \in (0, 1)$.
3. **HOLD:** Maintain existing positions, block new entries.
4. **BLOCK NEW ENTRY:** Cease all new orders $T - \Delta t$ until $T + \Delta t$.
5. **DELAY:** Defer execution signals until spread normalizes below threshold.
6. **FLATTEN:** Orderly close of open positions prior to event shock.
7. **EXIT:** Immediate market exit upon volatility threshold breach.
8. **$0.00 ALLOCATION:** Zero capital assigned to strategy during high-impact event regimes.

---

### Layer 12 — Execution Microstructure Quality
Decouples theoretical strategy alpha from real-world execution feasibility.

- **Fill Slippage:** Delta between requested order price and actual executed deal price:
  $$\text{Slippage} = \text{Price}_{\text{deal}} - \text{Price}_{\text{requested}}$$
- **Effective Spread at Execution:** Broker spread observed at exact timestamp of entry/exit.
- **Order Latency:** Time delta from signal generation to broker confirmation.
- **Rejection & Requote Rate:** Percentage of orders rejected (retcode 10004, 10006, 10027).
- **Partial Fill Frequency:** Impact of partial execution on multi-leg basket balance.

> [!IMPORTANT]
> **MANDATORY INVARIANT: BACKTEST EXECUTION $\neq$ BROKER REALITY**  
> A backtest showing positive return under zero-slippage, fixed-spread assumptions carries zero evidentiary value if the strategy relies on executing inside volatile news spikes or off-market spreads.

---

## 5. Comprehensive Cost Model

Strategy comparison must use a uniform, complete cost framework. Gross returns are strictly non-evidentiary.

$$\text{Net Trade P/L} = \text{Gross P/L} - \text{Commission} - \text{Spread Cost} - \text{Swap Drag} - \text{Slippage Cost} - \text{Financing Cost}$$

1. **Spread Cost:** Half-spread on entry + half-spread on exit $\times$ volume $\times$ contract size.
2. **Commission:** Broker round-turn commission.
3. **Swap / Financing Drag:** Overnight rollover interest (critical for long-duration grid baskets).
4. **Slippage Friction:** Actual fill price divergence from signal price.
5. **Venue-Specific Fees:** Regulatory, exchange, or gateway surcharges where applicable.

---

## 6. Evidence Hierarchy & Epistemic Discipline

Per ADR-022 Section 7, all analytical assertions must be explicitly tagged with an epistemic evidence classification:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      ACASH EPISTEMIC HIERARCHY                         │
├─────────────────┬──────────────────────────────────────────────────────┤
│  PROVEN         │ Mathematically proven or independently verified on   │
│                 │ authoritative broker trade execution records.        │
├─────────────────┼──────────────────────────────────────────────────────┤
│  REPORTED       │ Stated in vendor marketing, backtest summaries, or   │
│                 │ unverified performance dashboards.                   │
├─────────────────┼──────────────────────────────────────────────────────┤
│  UNVERIFIED     │ Plausible hypothesis derived from visual observation │
│                 │ or indirect signals without raw deal data.           │
├─────────────────┼──────────────────────────────────────────────────────┤
│  INFERRED       │ Deductions derived from partial evidence via         │
│                 │ explicit mathematical models.                        │
├─────────────────┼──────────────────────────────────────────────────────┤
│  UNKNOWN        │ Implementation details, internal state, or code      │
│                 │ logic that cannot be inspected.                      │
└─────────────────┴──────────────────────────────────────────────────────┘
```

**Epistemic Rules:**
- Marketing screenshots showing `+40% return`: **`REPORTED / UNVERIFIED`**.
- Independently audited MT5 broker deal history: **`PROVEN`**.
- Proprietary closed-source EA internal parameters: **`UNKNOWN`**.
- Claims must never be upgraded without primary cryptographic or broker source evidence.

---

## 7. Fair Strategy Tournament Framework

When ACASH evaluates multiple candidate strategies, every candidate receives identical evaluation across all 12 layers.

```
                      CANDIDATE INGESTION
             (Internal Models, EAs, Vendor Algos)
                              │
                              ▼
            FROZEN TOURNAMENT EVALUATION CRITERIA
              (Sealed Prior to Tournament Run)
                              │
                              ▼
               UNIFORM DATASET & COST SUBSTRATE
          (Identical Regimes, Spreads, Slippage Models)
                              │
                              ▼
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
     Performance         Tail Survival      Robustness
      Forensics             Stress          Scorecards
           │                  │                  │
           └──────────────────┼──────────────────┘
                              ▼
                  STRATEGY SCORECARD MATRIX
                              │
                              ▼
                EXPLAINABLE CAPITAL ALLOCATION
           ($0.00 / Seed Capital / Scaled Capital)
```

**Tournament Governance Rules:**
1. **Prior Rule Freezing:** Hurdle rates, risk limits, and scorecards must be cryptographically hashed and sealed before ingesting strategy outputs.
2. **Zero Retrospective Goalpost Shifting:** Adjusting evaluation criteria after inspecting which strategy performed best is strictly prohibited.
3. **Transparent Head-to-Head Comparison:** If an external commercial EA outperforms an ACASH internal model under identical frozen criteria, ACASH accepts the result without bias.

---

## 8. Capital Allocation Principles: Flexible Decisions + Fixed Safety

Capital allocation is dynamic and evidence-driven, but operates strictly inside non-negotiable risk boundaries:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   SOVEREIGN HARD RISK BOUNDARIES                       │
│  - Maximum Aggregate Gross Exposure Limit (Frozen)                    │
│  - Maximum Daily Loss Hard Stop (Deterministic Risk Engine)            │
│  - Sovereign Kill Switch (PERSISTENTLY_BLOCKED on Breach)              │
│  - Mandatory 6-D Reconciliation Clean State Required for Dispatch      │
│  - Live Capital Authority = $0.00 (Hard-Locked Pre-Gate B)             │
└────────────────────────────────────────────────────────────────────────┘
                                ▲
                                │ Strictly Bounded By
                                │
┌────────────────────────────────────────────────────────────────────────┐
│                   DYNAMIC ALLOCATION DISCRETION                        │
│  - Capital Allocation by Strategy × Regime Edge                        │
│  - Performance Scorecard Weighting                                     │
│  - Volatility-Scaled Sizing                                            │
│  - De-allocation to $0.00 during Unfavorable Regimes                  │
└────────────────────────────────────────────────────────────────────────┘
```

**Core Principle:** Flexible strategy selection and capital allocation can **NEVER** override hard safety guardrails, kill switches, or reconciliation invariants.

---

## 9. Standardized Strategy Scorecard

Candidates receive a standardized multi-dimensional audit scorecard:

| Dimension | Mandatory Invariants / Hurdle Standard | Status |
|---|---|---|
| **Performance** | Positive expectancy, Calmar $> 1.0$, recovery factor $> 2.0$ net of costs | `PASS / FAIL / UNKNOWN` |
| **Position Forensics** | Bounded basket duration, bounded max basket exposure | `PASS / FAIL / UNKNOWN` |
| **Sizing Mechanics** | Proven non-exponential margin exhaustion trajectory | `PASS / FAIL / UNKNOWN` |
| **Hedge Forensics** | Non-absorbing hedge unlock logic, carrying cost within bounds | `PASS / FAIL / UNKNOWN` |
| **Capital & Margin** | Liquidation distance $> 500$ pips, margin level never $< 300\%$ | `PASS / FAIL / UNKNOWN` |
| **Tail Survival** | Passes all 10 stress test scenarios without liquidation | `PASS / FAIL / UNKNOWN` |
| **Near-Death Audit** | Zero historical Near-Death Events ($\ge 70\%$ DD or margin $< 200\%$) | `PASS / FAIL / UNKNOWN` |
| **Cash-Flow Audit** | Zero external capital injections required during drawdowns | `PASS / FAIL / UNKNOWN` |
| **Robustness** | Statistically significant out-of-sample edge, Monte Carlo passes | `PASS / FAIL / UNKNOWN` |
| **Regime Clarity** | Identified and documented profitable vs. unprofitable regimes | `PASS / FAIL / UNKNOWN` |
| **Event Policy** | Explicit graduated policy defined for high-impact releases | `PASS / FAIL / UNKNOWN` |
| **Execution Reality** | Edge survives $2\times$ spread and adverse slippage models | `PASS / FAIL / UNKNOWN` |

---

## 10. Illustrative Case Study: EA Alice

EA Alice is examined strictly as an **illustrative case study** demonstrating why this framework exists.

### 10.1 Observed Phenomenon & Classification
- **Source Data:** Screenshot evidence showing high win rates, profitable closed sequences, and low closed drawdown.
- **Epistemic Classification:** **`REPORTED / UNVERIFIED`**.
- **Working Research Hypothesis:** The observed behavior appears consistent with a multi-position, averaging, grid, recovery, and/or hedging architecture.
- **Unverified Status:** Zero internal source code, broker transaction logs, or tick-by-tick deal tickets have been independently audited by ACASH.

### 10.2 Objective Evaluation Requirements for Alice
If EA Alice is formally submitted as an ACASH strategy candidate, she will be evaluated under the exact same 12-layer framework as any native model:
1. **What is Alice's maximum floating drawdown during adverse moves?**
2. **What is Alice's lot progression formula $L_n$? Is it linear, multiplier, or Martingale?**
3. **What is Alice's maximum observed basket duration and gross exposure?**
4. **How does Alice behave during a 500-pip persistent one-way trend?**
5. **How does Alice handle extreme spread widening during news releases?**
6. **Did Alice survive historical drawdowns organically, or was new capital injected?**
7. **Did Alice experience Near-Death Events where liquidation was narrowly avoided?**

### 10.3 Impartial Governance Outcomes
- **If Alice passes all 12 layers objectively:** ACASH must accept the result and allocate capital according to the scorecard.
- **If Alice fails any tail-risk or margin boundary:** ACASH must document the exact failure mechanism and assign **$0.00 allocation**.
- **If evidence remains incomplete:** Alice remains classified as **`UNKNOWN`** with **$0.00 allocation**.

---

## 11. Verification & Compliance Ledger

```markdown
### Strategy Evaluation Framework Governance Ledger
- Document Type: Quantitative Research / Strategy Evaluation / Risk Governance Specification
- Status: DOCUMENTATION ONLY (No software implementation authorized)
- Governing Authority: ADR-022 (Market-Adaptive, Strategy-Agnostic & Event-Aware Governance)
- Software Codebase (src/): 100% FROZEN (0 diff)
- Test Codebase (tests/): 100% FROZEN (0 diff)
- Live Capital Authority: $0.00 (Strict Invariant)
- MT5 Broker Orders: STRICTLY ZERO (order_send = 0)
- Gate A Status: NOT CERTIFIED (Remains unchanged)
- Gate B Status: LOCKED (Remains unchanged)
- Candidate Evaluation Engine: NOT IMPLEMENTED (Conceptual / Research specification only)
```
