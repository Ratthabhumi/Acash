# ACASH — System Architecture Specification (Phase 0)

**Document:** `docs/ARCHITECTURE.md`  
**Version:** 3.4.0 (Immutable State Transitions & Normalized Value Applied)  
**Date:** 2026-08-27  

---

## 1. Core Architectural Layers

ACASH (Automated Capital Allocation System) explicitly distinguishes seven decoupled architectural layers:

1. **RESEARCH DATA LAYER (Analytical):** Local partitioned Parquet files + embedded DuckDB query engine for vectorized analytical queries + `yfinance` research data adapter (strictly isolated behind `IMarketDataProvider`). *DuckDB is used strictly as an analytical engine, not a transactional control-plane DB.*
2. **LOCAL TRANSACTIONAL CONTROL PLANE (Operational Audit):** `SQLite` manages local transactional operational state, order state machines, and **append-only decision audit records** for V1. `PostgreSQL` is **DEFERRED** until concurrent multi-process writers, production durability, or operational requirements justify it.
3. **ANALYTICS & QUANT RESEARCH LAYER:** `pandas` + `NumPy` + `vectorbt` (Tier-1 rapid vectorized screening) + `Plotly` (interactive research visualization).
4. **PORTFOLIO ENGINE:** `skfolio` (portfolio optimization and risk-allocation methods including HRP, ERC, and CVaR) + transparent baselines (Equal Weight, Inverse Volatility, Cash/No-Trade). *skfolio must be evaluated for statistically significant incremental value versus transparent baselines out-of-sample.*
5. **EVENT SIMULATION SUBSTRATE:** `NautilusTrader` as a Tier-2 event-driven simulation candidate, subject to a Phase 5 PoC gate. *Phase 1 defines abstract interfaces and Mock/InMemory implementations only.*
6. **EXECUTION SUBSYSTEM:** Sovereign `IExecutionEngine` abstraction $\to$ `MockExecutionAdapter` for testing $\to$ `MT5Adapter` initially for live testing $\to$ `NautilusAdapter` only after Phase 5 PoC approval.
7. **PERFORMANCE LAYER:** Python-first $\to$ `NumPy` / `Numba` in-process vectorization $\to$ Nautilus Rust core where applicable $\to$ custom C++/Rust only after measured profiling.

---

## 2. End-to-End System Dataflow & Domain Architecture

```
                    ACASH SYSTEM CORE
                          │
          ┌───────────────┴───────────────┐
          │                               │
       DATA LAYER                  QUANT RESEARCH
          │                               │
  Parquet + DuckDB                 pandas + NumPy
  yfinance (Research)              vectorbt / Plotly
          │                               │
          └───────────────┬───────────────┘
                          │
                          ▼
                     ALPHA ENGINE
             (Signals & Expected Returns)
                          │
                          ▼
                  VALIDATION ENGINE
               (Purged CPCV & DSR Gate)
                          │
                          ▼
                  PORTFOLIO ENGINE
             (skfolio + Baselines: EW/InvVol/Cash)
                          │
                          ▼
                     RISK ENGINE
              (Hard Deterministic Boundary)
                          │
                          ▼
                  IExecutionEngine
                  (Mock in Phase 1)
                     /         \
               MT5 Adapter    Nautilus* (Phase 5 PoC)
```

---

## 3. Sovereign Domain Entity Relationships & Immutable Transitions

The domain layer explicitly models two distinct but interacting flows, where state updates create **new immutable snapshots** without mutating existing objects:

```
        CAPITAL & PORTFOLIO STATE FLOW
        ──────────────────────────────
                 AccountState
         EXTERNAL ACCOUNT STATE
         ──────────────────────
         Broker / External Source
                    │
                    ▼
               AccountState

         INTERNAL PORTFOLIO STATE
         ────────────────────────
         Positions + Market Prices
                    │
                    ▼
              PortfolioState
                    │
                    ▼
                Positions
                    ▲
                    │ (Immutable State Transition creates NEW Snapshots)
                    │
         DECISION & EXECUTION FLOW
         ─────────────────────────
                  Signal
                    │
                    ▼
             TargetAllocation
                    │
                    ▼
              RiskAssessment
                    │
                    ▼
                  Order (status: OrderStatus)
                    │
                    ▼
                   Fill
                    │
                    └──────► State Transition ──► NEW Position
                                              ──► NEW PortfolioState


         CROSS-CUTTING AUDIT LINEAGE
         ───────────────────────────
             DecisionRecord (Append-Only)
           ↳ Observed Market Inputs Ref
           ↳ Signal Ref
           ↳ Target Allocation
           ↳ Risk Assessment Verdict
           ↳ Correlation ID
```

### 3.1 Normalized Valuation & Phase 1 Spot-Like Accounting Assumptions
- **Base Currency Normalization:** `Position`, `PortfolioState`, and `AccountState` express monetary values in a defined ACASH base currency.
- **Phase 1 Spot-Like Portfolio Equity Source of Truth:**
  $$\text{Portfolio Total Equity} = \text{cash\_balance} + \sum_{i} \text{Position}_i.\text{market\_value}$$
  where $\text{Position.market\_value} = \text{signed quantity} \times \text{current\_price}$.
  *(Note: This is the Phase 1 spot-like accounting assumption only; it is not claimed as universal multi-asset derivative accounting).*
- **Fill Cash-Flow Semantics:**
  - BUY: `cash_balance` decreases by $(\text{fill\_price} \times \text{fill\_quantity}) + \text{fee}$.
  - SELL: `cash_balance` increases by $(\text{fill\_price} \times \text{fill\_quantity}) - \text{fee}$.
  - Realized PnL is incorporated automatically via resulting cash flows and is strictly NOT added a second time to cash or equity.
- **Gross Exposure Definition:**
  $$\text{Gross Exposure} = \sum_{i} |\text{Normalized Position Value}_i|$$
- **Deferred Valuation Complexity:** Market-specific valuation details (futures multipliers, CFD specs, live FX conversions) remain deferred from Phase 1.


---

## 4. Subsystem Breakdown & Governance Principles

| Subsystem | Components / Libraries | Governance Principle |
| :--- | :--- | :--- |
| **Research Data Layer** | Parquet, DuckDB, `yfinance` | Strict point-in-time bi-temporal indexing; DuckDB for analytical SQL only; `yfinance` is research-only. |
| **Transactional Control Plane** | SQLite (V1), PostgreSQL (Deferred) | SQLite for local transactional operational state and **append-only decision audit records**; PostgreSQL deferred until concurrent writers or multi-user durability mandate it. |
| **Analytics & Research** | `pandas`, `NumPy`, `vectorbt`, `Plotly` | Tier-1 screening filters noisy parameters before event simulation; Plotly provides interactive research visualization. |
| **Portfolio Engine** | `skfolio`, Baselines (1/N, Inv Vol, Cash) | **skfolio must prove statistically significant incremental value over baselines out-of-sample; the system is never forced to select skfolio if a baseline is more robust.** |
| **Validation Engine** | `skfolio.model_selection` (CPCV), DSR | Deflated Sharpe Ratio multi-testing correction; strict out-of-sample held-out partition. |
| **Event Simulation** | `IBacktestEngine` (Phase 1 Mock / Phase 5 Nautilus PoC) | Phase 1 defines interfaces and Mock/InMemory engine; NautilusTrader is evaluated in Phase 5 PoC. |
| **Risk Engine** | Sovereign ACASH Code (Phase 9) | Hard deterministic boundary; 100% authority to approve, reduce, or reject any portfolio allocation. (Interface only in Phase 1). |
| **Execution Engine** | `IExecutionEngine`, `MockAdapter` (Phase 1) | Phase 1 implements Mock/InMemory execution only; MT5 and Nautilus live execution remain decoupled. |
| **Performance** | Python, Numba, Nautilus Rust Core | Python-first; profile and benchmark before any native custom optimization. |

---

## 5. Engineering Workflow Addendum

For ACASH development, follow an agentic engineering workflow:

1. Inspect the existing repository, architecture, ADRs, tests, and git history before modifying code.
2. Do not implement large changes immediately. First explain the impact, assumptions, affected modules, and implementation plan.
3. Preserve ACASH architectural boundaries and source-of-truth documentation.
4. Prefer minimal, reversible changes over broad refactors.
5. After implementation, run tests, static typing, invariant checks, and review the final diff.
6. Perform a self-review: identify assumptions, possible regressions, violated invariants, and unintended scope changes.
7. Record important architectural lessons or recurring mistakes in the appropriate project documentation.
8. Never grant an AI agent authority to bypass ACASH risk controls, decision boundaries, or execution safeguards.
9. External tools such as Agentic Trading Lab may be used only as independent research/evaluation references and must not become ACASH core dependencies without an explicit architectural decision.

### Core Engineering Loop:
$$\text{INSPECT} \to \text{UNDERSTAND} \to \text{PLAN} \to \text{APPROVE} \to \text{IMPLEMENT} \to \text{TEST} \to \text{SELF-REVIEW} \to \text{DOCUMENT}$$

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

From external trading-system examples/research, incorporate these principles into ACASH architecture where appropriate:

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
> **Boundary Preservation:** Do not add new features or perform broad refactors based on these lessons. Preserve current ACASH boundaries and apply only minimal, reversible documentation/architecture updates where justified.

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

ACASH enforces a strict hierarchical separation between deterministic quantitative modeling and qualitative/AI reasoning:

1. **Risk State Representation:** Continuous tracking of portfolio risk capacity, limit headroom, and drawdown state.
2. **Margin Buffer Safety Threshold:** Mandatory buffer between utilized margin and maintenance thresholds before approving any allocation.
3. **Net & Dollar Exposure Tracking:** Explicit dollar-denominated exposure accounting ($\text{Gross Exposure} = \sum |\text{Dollar Value}|$, $\text{Net Exposure} = \sum \text{Dollar Value}$).
4. **Deterministic Edge Metrics:** All performance metrics (Sharpe, DSR, Information Ratio, expectancy, max drawdown) are calculated strictly by deterministic mathematical algorithms.
5. **Separation of Raw Metrics from AI Reasoning:** Raw quantitative metrics remain pure and immutable. AI reasoning operates strictly downstream as an explanatory research tool, NEVER generating unverified numbers or placing trades.

### Core Processing Flow:
$$\text{DATA} \to \text{QUANT ENGINE} \to \text{RISK STATE} \to \text{AI REASONING}$$

$$\text{NOT: DATA} \to \text{AI} \to \text{Unverified Numbers} \to \text{TRADE}$$




