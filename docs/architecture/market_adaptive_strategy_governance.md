# ACASH — Market-Adaptive, Strategy-Agnostic & Event-Aware Trading Principles (ADR-022)

**Document ID:** `docs/architecture/market_adaptive_strategy_governance.md`  
**Related ADR:** `ADR-022` in [`docs/DECISIONS.md`](../DECISIONS.md)  
**Document Type:** Strategic Governance / Architecture Direction / Research Principle  
**Status:** Permanent Strategic Governance & Research Principle (Documentation Only)  
**Scope:** Quantitative Governance, Strategy Neutrality, Event-Aware Risk & Dynamic Capital Allocation  
**Current Operational Baseline:** Phase 13 (Gate A Active / $0.00 Live Capital Authority)  
**Date:** 2026-09-04  

---

## 0. Executive Intent

This document establishes a permanent strategic direction and quantitative operating philosophy for the ACASH quantitative research and execution ecosystem.

ACASH must **NEVER** become permanently coupled to:
- One trading strategy
- One asset class
- One broker
- One execution venue
- One market regime
- One timeframe
- One alpha-generation methodology
- One capital allocation level
- One assumption about market behavior

Instead, ACASH architecture must be systematically designed toward:
$$\mathbf{Strategy\ Flexibility} \quad \times \quad \mathbf{Asset\ Flexibility} \quad \times \quad \mathbf{Venue/Broker\ Flexibility} \quad \times \quad \mathbf{Capital\ Allocation\ Flexibility} \quad \times \quad \mathbf{Time/Event\ Exposure\ Flexibility}$$

While strictly preserving sovereign, non-negotiable foundations:
$$\mathbf{Hard\ Risk\ Governance} \quad \land \quad \mathbf{Fail\text{-}Closed\ Execution} \quad \land \quad \mathbf{Broker\text{-}Observed\ Reality} \quad \land \quad \mathbf{Reconciliation\ Integrity} \quad \land \quad \mathbf{Cryptographic\ Provenance}$$

$$\boxed{\mathbf{CORE\ OPERATING\ PRINCIPLE:\ FLEXIBLE\ DECISION\ MAKING\ +\ FIXED\ SAFETY\ GUARDRAILS}}$$

ACASH adapts dynamically to empirical evidence and evolving market conditions, but **NEVER adapts its safety boundaries arbitrarily**.

---

## 1. Core Philosophy: What ACASH Is and Is Not

- ACASH is **NOT** a Grid EA.
- ACASH is **NOT** a Momentum EA.
- ACASH is **NOT** an AI / Machine Learning EA.
- ACASH is **NOT** an Arbitrage EA.
- ACASH is **NOT** a Forex-only system.
- ACASH is **NOT** a Gold-only (XAUUSD) system.
- ACASH is **NOT** a single-broker trading bot.

ACASH is an **autonomous quantitative infrastructure and decision framework** designed to identify, evaluate, and allocate capital to opportunities, strategies, instruments, and execution venues under strictly bounded risk.

The long-term operational objective of ACASH is to systematically determine:
$$\boxed{\text{What to trade} \quad \to \quad \text{Which strategy} \quad \to \quad \text{Which instrument} \quad \to \quad \text{Which eligible venue} \quad \to \quad \text{What timing} \quad \to \quad \text{How much capital} \quad \to \quad \text{Under what risk limits}}$$

Every element of this decision chain must be governed by **empirical evidence and explicit policy**, never by developer preference, ownership bias, or marketing claims.

---

## 2. Infrastructure != Alpha

Engineering quality must never be confused with trading edge:

$$\mathbf{Engineering\ Quality} \neq \mathbf{Trading\ Alpha} \quad \land \quad \mathbf{Architectural\ Complexity} \neq \mathbf{Economic\ Edge}$$

The core competencies of ACASH infrastructure include:
- Execution reliability and fault tolerance
- Broker abstraction and protocol normalization
- Order lifecycle state management (`transition_order()` sole authority)
- Non-negotiable risk controls and exposure limiting
- Multi-dimensional (6-D) reconciliation against broker reality
- Sovereign shadow ledger accounting
- Real-time telemetry, automated warnings, and human SLA monitoring
- Cryptographic multi-sig kill switch tripping and persistence
- Performance and reality gap attribution
- Strategy lifecycle governance and capital allocation

**These capabilities provide sovereign control and operational safety; they do NOT generate trading alpha by themselves.**

A structurally simple external strategy (such as a basic rule-based breakout or mechanical grid) may outperform a mathematically sophisticated ACASH-native model if it possesses a genuine statistical edge. If empirical evidence demonstrates that outcome, ACASH must accept the result objectively. The correct response is to analyze why the external model succeeded, **never to distort evaluation rules until ACASH wins**.

---

## 3. Strategy-Agnostic Principle

ACASH maintains absolute neutrality toward strategy archetypes. The strategy universe includes, but is not limited to:
- Trend Following & Time-Series Momentum
- Cross-Sectional Momentum & Relative Strength
- Mean Reversion & Statistical Arbitrage
- Grid & Dynamic Mesh Systems
- Pairs Trading & Cointegration Models
- FX Carry & Interest Rate Differentials
- Volatility Arbitrage & Dispersion
- Algorithmic Market Making & Liquidity Provision
- Event-Driven & Macro Release Models
- Machine Learning & Deep/Reinforcement Learning Signal Generators
- Hybrid Multi-Model Ensembles
- External Commercial & Open-Source Expert Advisors (EAs)
- Future quantitative strategy classes

No strategy is inherently preferred because it was developed internally. No strategy is inherently rejected because it is external, simple, retail, or grid-based.

The single evaluation standard across all strategy candidates is:
$$\boxed{\text{"Does this strategy demonstrate a robust, reproducible, risk-adjusted edge under the tested conditions?"}}$$

---

## 4. Treatment of External Strategies as Legitimate Benchmarks

Third-party EAs, commercial systems, and external algorithms must be treated with scientific objectivity. An external strategy may serve as:
- An empirical **benchmark** to measure internal alpha development against.
- A **research candidate** for structural and risk decomposition.
- A **competing alpha source** in strategy tournaments.
- An **integration candidate** wrapped behind ACASH risk adapters.
- A **rejected candidate** documented for failure modes.

### Epistemic Hierarchy of Performance Claims
No strategic decision may rely on marketing screenshots, vendor backtests, social-media follower counts, or displayed profit percentages. All performance claims must be classified into five distinct epistemic tiers:

$$\mathbf{PROVEN} \quad \succ \quad \mathbf{REPORTED} \quad \succ \quad \mathbf{UNVERIFIED} \quad \succ \quad \mathbf{INFERRED} \quad \succ \quad \mathbf{UNKNOWN}$$

> [!CAUTION]
> **Strict Anti-Hype Boundary:** ACASH contributors and agents must **NEVER** upgrade a claim from `REPORTED` to `PROVEN` without independent, reproducible broker-level transaction statements and verified out-of-sample data.

---

## 5. Market-Adaptive Principle & Strategy $\times$ Regime

Market adaptability does **not** mean randomly switching strategies when drawdowns occur. It means implementing an evidence-driven, structured decision sequence:

```
                  Market State Observation
                             │
                             ▼
             Market Regime & Condition Detection
                             │
                             ▼
                Eligible Strategy Universe
                             │
                             ▼
                Current Portfolio Risk State
                             │
                             ▼
               Strategy Suitability Assessment
                             │
                             ▼
                  Capital Allocation Policy
                             │
                             ▼
               Instrument & Venue Routing Policy
                             │
                             ▼
          Execution ONLY IF Hard Guardrails Permit
```

### The $\mathbf{Strategy} \times \mathbf{Regime}$ Analytical Standard
Strategy performance is rarely universal. Strategy ranking must evaluate conditional expectations across distinct market regimes rather than aggregate historical returns:

$$\text{Evaluate } \mathbf{Strategy\ A} \times \mathbf{Regime\ R}, \quad \text{NOT } \mathbf{Strategy\ A} \times \mathbf{Total\ Return}$$

- **Grid / Mean Reversion:** Often exhibits strong risk-adjusted returns during low-volatility, range-bound, oscillating regimes with deep liquidity, but faces existential catastrophic tail risk during non-reverting directional trends.
- **Momentum / Trend Following:** Often suffers persistent whipsaw bleed during range-bound regimes, but captures large right-tail profits during structural breakouts and sustained trends.

ACASH must evaluate candidate models against the specific market regimes in which their statistical assumptions hold valid.

---

## 6. Flexible Strategy, Asset, and Execution Architecture

```
                               ┌──────────────────────────────┐
                               │       ACASH CORE             │
                               │                              │
                               │ Market Observation           │
                               │ Opportunity Discovery        │
                               │ Regime Analysis              │
                               │ Strategy Universe            │
                               │ Standardized Evaluation      │
                               │ Dynamic Capital Allocation   │
                               │ Sovereign Risk Engine        │
                               │ Cryptographic Kill Switch    │
                               │ Sovereign Shadow Ledger      │
                               │ 6-D Reconciliation           │
                               └──────────────┬───────────────┘
                                              │
                                 Instrument & Venue Routing
                                              │
                 ┌────────────────────────────┼────────────────────────────┐
                 │                            │                            │
                 ▼                            ▼                            ▼
          MT5 Adapter                  Alpaca Adapter               Direct API Adapter
          (Pepperstone / MetaQuotes)   (US Equities / ETFs)         (OANDA / FIX / IBKR)
                 │                            │                            │
                 ▼                            ▼                            ▼
           Retail MT5 FX                US Equities / ETFs           Direct API Execution
```

1. **Flexible Strategy:** The Strategy Universe incorporates native models, ML algorithms, and external EAs evaluated side-by-side in standardized tournaments.
2. **Flexible Asset:** Conceptually asset-agnostic (FX, Precious Metals, Commodities, Equities, ETFs, Futures, Options, Digital Assets). Each asset class requires independent data pipelines, risk models, execution adapters, and formal certification.
3. **Flexible Broker / Venue:** The broker is strictly an execution venue, not the boundary of ACASH alpha. One trading intent must **never** be automatically duplicated across multiple venues. Venue routing is deterministic, auditable, and capability-aware.

---

## 7. Dynamic Capital Allocation & Hard Risk Governance

Capital allocation scales with empirical confidence, but remains bounded by hard, non-negotiable risk guardrails:

$$\boxed{\mathbf{Flexible\ Allocation} \quad \longleftrightarrow \quad \mathbf{Fixed\ Risk\ Guardrails}}$$

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   EVIDENCE-DRIVEN ALLOCATION POLICY                     │
├─────────────────────────────────────────────────────────────────────────┤
│ • High-quality opportunity + favorable regime + normal execution        │
│   ──► Higher Risk-Budget Allocation (Within Hard Limits)                │
│                                                                         │
│ • Weak edge + unfavorable regime + deteriorating execution conditions   │
│   ──► Reduced Allocation / Defensive Sizing                             │
│                                                                         │
│ • Extreme uncertainty + risk limit breach + unverified data             │
│   ──► $0.00 ALLOCATION (Absolute Preservation of Capital)               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Non-Negotiable Safety Guardrails
The following boundaries are **immutable** and cannot be bypassed or weakened by any strategy or allocation logic:
- Maximum daily and cumulative loss limits
- Maximum gross and net portfolio exposure bounds
- Maximum account leverage and margin saturation limits
- Single-instrument and currency concentration caps
- Non-bypassable Sovereign Kill Switch lockout
- Canonical 6-D reconciliation confirmation requirements
- Strict fail-closed exception handling (`UNKNOWN` state cannot dispatch)
- Physical separation of paper/demo and live execution credentials

> [!IMPORTANT]
> **No Strategy Overrides Risk:** A strategy can never assert high statistical confidence to request bypassing an established risk boundary. Changing a risk constraint requires formal governance, stress testing, and multi-signature authorization.

---

## 8. Time / Event Exposure & Event-Aware Risk Governance

Market conditions vary dramatically across macroeconomic and corporate news events. ACASH treats event proximity as an explicit dimension of market state:

$$\mathbf{NORMAL} \quad \longrightarrow \quad \mathbf{PRE\text{-}EVENT} \quad \longrightarrow \quad \mathbf{EVENT\ WINDOW} \quad \longrightarrow \quad \mathbf{POST\text{-}EVENT} \quad \longrightarrow \quad \mathbf{NORMALIZED}$$

### 8.1 Event-Aware Risk Model
ACASH rejects the blunt heuristic that "all news trading is forbidden." Instead, high-impact events are processed through an event-aware risk framework:

$$\text{Economic / Market Event} \implies \text{Classification} \implies \text{Severity} \implies \text{Execution Quality} \implies \text{Strategy Suitability} \implies \text{Policy Action}$$

Possible policy outputs include:
$$\mathbf{ALLOW} \quad \mid \quad \mathbf{REDUCE} \quad \mid \quad \mathbf{HOLD} \quad \mid \quad \mathbf{BLOCK\ NEW\ ENTRY} \quad \mid \quad \mathbf{DELAY} \quad \mid \quad \mathbf{FLATTEN} \quad \mid \quad \mathbf{\$0\ ALLOCATION}$$

### 8.2 Execution Realities During High-Impact Events
Under extreme volatility, execution assumptions break down:
- Spreads expand dramatically (e.g. EURUSD spread widening $10\times$).
- Order book depth thins out, generating severe slippage.
- Price jumps and gaps breach resting stop orders.
- Broker API latency spikes or rejects market orders.

> [!CAUTION]
> **Stop Loss $\neq$ Guaranteed Execution Price:** A stop loss is an order trigger, not a price guarantee. During illiquid news shocks, execution may occur significantly worse than the stop price. Any event-aware risk model must explicitly account for slippage and gap risk.

### 8.3 Pre-Event, Event-Time, and Post-Event Policies
- **Pre-Event:** Evaluate existing open positions, margin cushion, distance to stops, and strategy sensitivity. Policies may choose to hold, trim exposure, or suspend new entries. No forced universal flattening is assumed.
- **Event-Time:** Conservative posture. New trade dispatch is suspended unless the strategy has proven empirical robustness specifically within the high-volatility event regime.
- **Post-Event Normalization:** Implement a cooldown check before resuming normal operations:
  $$\text{Event Released} \to \text{Spread Normalized?} \to \text{Liquidity Restored?} \to \text{Volatility Settled?} \to \text{Signal Still Valid?} \to \text{Dispatch Permitted}$$

---

## 9. Explainable & Auditable Capital Allocation

Dynamic capital allocation must **never become an unexplainable black box**. Every future capital allocation decision must be verifiable against an audit trail answering nine explicit questions:

```text
1. Why this strategy?        -> Evidence-backed performance score and regime fit
2. Why this instrument?      -> Opportunity detected and contract verified
3. Why this execution venue? -> Venue capability, counterparty risk, and cost model
4. Why this capital amount?  -> Mathematically scaled risk budget
5. Why at this timestamp?    -> Signal validity and session/event clearance
6. What evidence supports?   -> Cryptographic digest of research/tournament record
7. What risk limits checked? -> Loss, margin, leverage, concentration, and kill switch
8. What event regime exists? -> Event proximity and volatility state
9. What revokes allocation?  -> Explicit drawdown threshold or regime shift trigger
```

---

## 10. Strategy Tournament & Fair Evaluation Rules

Candidate strategies compete in standardized tournaments under identical conditions:

### Fair Comparison Mandate
1. **Pre-Registered Evaluation Protocol:** The evaluation window, performance metrics, and acceptance criteria must be frozen **before** running the comparison. Retrospective shifting of hurdle rates after viewing results is strictly forbidden.
2. **Controlled Variables:** Benchmark evaluations must control for initial capital, instrument, evaluation period, data quality, leverage, realistic spread, commission schedules, overnight swap costs, and tick-level slippage assumptions.
3. **Multi-Dimensional Metrics Beyond Raw Return:**
   - Risk-adjusted ratios: Sharpe Ratio, Sortino Ratio, Calmar Ratio.
   - Tail metrics: Maximum Peak-to-Trough Drawdown, Maximum Floating Drawdown, CVaR 99%.
   - Overfitting tests: Bailey CSCV Probability of Backtest Overfitting (PBO), Deflated Sharpe Ratio (DSR).
   - Friction sensitivity: Slippage sensitivity slope, turnover velocity.
4. **Epistemic Distinctions:**
   $$\mathbf{Backtest} \neq \mathbf{Simulation} \neq \mathbf{Paper} \neq \mathbf{Demo} \neq \mathbf{Live}$$
   A backtest demonstrates historical consistency; it does not prove live execution edge.
5. **Failure as a Valid Outcome:** If all candidate strategies fail risk-adjusted hurdles, the system marks the evaluation `UNVERIFIED / REJECTED` and allocates **$0.00**. There is zero institutional pressure to trade without verified edge.

---

## 11. Anti-Bias Code of Conduct for Quantitative Agents

All AI agents, engineers, and contributors operating within ACASH must adhere to the following anti-bias rules:

1. **Active Bias Challenge:** Actively interrogate internal assumptions. Never assume internal is superior to external, AI is superior to rule-based, or complex is superior to simple.
2. **Accept Empirical Reality:** If an external EA achieves superior risk-adjusted returns under fair conditions:
   $$\mathbf{ACCEPT\ THE\ RESULT} \quad \longrightarrow \quad \mathbf{INVESTIGATE\ THE\ RESULT} \quad \longrightarrow \quad \mathbf{DO\ NOT\ MOVE\ THE\ GOALPOSTS}$$
3. **Intellectual Honesty Over Ownership:** ACASH exists to maximize the probability of making sound capital allocation decisions under controlled risk. It does not exist to prove that ACASH itself is superior.

---

## 12. Current Project Phase & Boundary Locks

> [!IMPORTANT]
> **THIS DIRECTIVE DOES NOT AUTHORIZE CODE IMPLEMENTATION.**
>
> Specifically, this document does **NOT** authorize:
> - Implementing an Event Engine or Economic Calendar feed
> - Implementing a Regime Detector or Strategy Selector
> - Implementing a Dynamic Capital Allocator
> - Implementing retail Grid or Martingale strategies
> - Purchasing or integrating commercial EAs
> - Implementing new broker adapters or connecting new asset classes
> - Autonomous emergency order execution
> - Enabling live trading or Gate B progression ($0.00 live capital authority remains hard-locked)

### Immediate Focus: Phase 13 Slice 1 Gate A Remediation
Phase 13 Slice 1 Gate A remains the immediate priority. The active remediation of findings **B-1** (lineage mismatch) and **B-2** (exit deal binding) must proceed cleanly without scope creep from future strategic architecture.
