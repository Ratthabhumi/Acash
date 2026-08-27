# ACASH — Automated Capital Allocation System

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary%20%2F%20Research-green.svg)](#)
[![Architecture: Modular Monolith](https://img.shields.io/badge/architecture-Modular%20Monolith-orange.svg)](#)
[![Status: Phase 0 Complete](https://img.shields.io/badge/status-Phase%200%20Approved-success.svg)](#)

---

## 1. Executive Summary & North Star

**ACASH (Automated Capital Allocation System)** is a serious, research-first, evidence-driven capital allocation and portfolio management platform.

ACASH is **NOT** a generic AI trading bot, **NOT** an indicator collection, **NOT** an MT5 Expert Advisor, **NOT** an LLM voting system, and **NOT** an unconstrained machine making "+1% daily" promises.

### The North Star Question
> *"Given the current market, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"*

The system explicitly supports the answer: **"NOWHERE"** (100% Cash / No-Trade Allocation).

### Core Research Principle
$$\text{DATA} \to \text{EVIDENCE} \to \text{HYPOTHESIS} \to \text{RESEARCH} \to \text{ALPHA} \to \text{VALIDATION} \to \text{PORTFOLIO} \to \text{RISK} \to \text{EXECUTION} \to \text{OUTCOME} \to \text{FEEDBACK}$$

> **"DO NOT ASSUME AN EDGE. PROVE IT."**

---

## 2. System Architecture & 7 Decoupled Layers

ACASH is built as a sovereign **Modular Monolith** in Python executing locally on a single workstation (AIO):

```
                               ACASH SYSTEM CORE
                                      │
                      ┌───────────────┴───────────────┐
                      │                               │
             1. RESEARCH DATA LAYER          2. ANALYTICS & RESEARCH
           (Parquet + DuckDB + yfinance)    (pandas + NumPy + vectorbt + Plotly)
                      │                               │
                      └───────────────┬───────────────┘
                                      │
                                      ▼
                                3. ALPHA ENGINE
                         (Signals & Expected Returns)
                                      │
                                      ▼
                            4. VALIDATION ENGINE
                           (Purged CPCV & DSR Gate)
                                      │
                                      ▼
                            5. PORTFOLIO ENGINE
                    (skfolio + Baselines: EW/InvVol/Cash)
                                      │
                                      ▼
                             6. RISK ENGINE
                     (Hard Deterministic Boundary)
                                      │
                                      ▼
                            7. EXECUTION ENGINE
                             (IExecutionEngine)
                                /           \
                          MT5 Adapter      Nautilus Adapter
                          (Initial)        (Phase 5 PoC Gate)
                                │
                                ▼
                   LOCAL TRANSACTIONAL CONTROL PLANE
                      (SQLite Append-Only Ledger)
```

### Layer Responsibilities
1. **Research Data Layer (Analytical):** Partitioned Parquet files + embedded DuckDB query engine for vectorized analytical SQL queries + `yfinance` research data adapter.
2. **Transactional Control Plane (Operational):** `SQLite` handles local ACID operational state, order state machines, and **append-only decision audit records**. `PostgreSQL` is **DEFERRED** until concurrent multi-user/writer requirements justify it.
3. **Analytics & Quant Research:** `pandas`, `NumPy`, `vectorbt` (Tier-1 rapid parameter screening), and `Plotly` (interactive visualization).
4. **Portfolio Engine:** `skfolio` (portfolio optimization and risk-allocation methods including HRP, ERC, CVaR) evaluated strictly against transparent baselines (Equal Weight, Inverse Volatility, Cash/NOWHERE).
5. **Event Simulation:** `NautilusTrader` as a Tier-2 event-driven simulation candidate, subject to a Phase 5 Proof of Concept (PoC) gate.
6. **Execution Subsystem:** Sovereign `IExecutionEngine` abstraction decoupling broker mechanics.
7. **Performance Layer:** Python-first $\to$ NumPy/Numba vectorization $\to$ Nautilus Rust core where applicable $\to$ custom C++/Rust only after measured profiling.

---

## 3. Sovereign Domain Entity Relationships

ACASH explicitly decouples state management from decision and execution flows:

```
        CAPITAL & PORTFOLIO STATE FLOW
        ──────────────────────────────
                 AccountState
                      │
                      ▼
               PortfolioState
                      │
                      ▼
                  Positions
                      ▲
                      │ (Immutable State Transitions: Fill -> NEW Snapshots)
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
              OrderIntent / Order
                      │
                      ▼
                     Fill
                      │
                      └──────► State Transition ──► NEW Position
                                                ──► NEW PortfolioState
                                                ──► NEW AccountState


        CROSS-CUTTING AUDIT LINEAGE
        ───────────────────────────
               DecisionRecord (Append-Only)
          ↳ Observed Market Inputs
          ↳ Signal Reference
          ↳ Target Allocation
          ↳ Risk Assessment Verdict
          ↳ Order Intent / Order ID
          ↳ Fill(s) & Execution Realization
          ↳ PnL Outcome
```

---

## 4. Technology Decision Matrix Summary

| Technology / Tool | Decision | ACASH Role | Key Rationale |
| :--- | :--- | :--- | :--- |
| **ACASH Core** | **ADOPT** | Sovereign Control Plane | Sovereign domain logic, deterministic risk boundary, append-only decision ledger. |
| **skfolio** | **ADOPT** | Portfolio Optimizer Engine | Modern scikit-learn API, HRP, ERC, CVaR; must prove out-of-sample incremental value over baselines. |
| **NautilusTrader** | **ADAPT** | Tier-2 Event Sim Candidate | High-fidelity Rust event core; isolated behind adapters; requires Phase 5 PoC gate before live use. |
| **vectorbt (OSS)** | **ADAPT** | Tier-1 Fast Screening | Numba-accelerated vectorized parameter sweeps to filter noisy hypotheses before event simulation. |
| **yfinance** | **ADAPT** | Research Data Adapter | Research data adapter with no paid subscription requirement for research; strictly isolated. |
| **Plotly** | **ADOPT** | Analytics Visualization | Interactive equity curves, drawdown waterfalls, and research tear sheets in telemetry/notebooks. |
| **Parquet + DuckDB**| **ADOPT** | Local Analytical Storage | Local columnar storage + embedded query engine; zero server overhead. |
| **SQLite** | **ADOPT** | Local Transactional State | V1 append-only decision ledger and operational order/position state persistence. |
| **PostgreSQL** | **DEFERRED**| Enterprise Control Plane | Deferred until concurrent writers, production durability, or multi-user access justify it. |
| **MetaTrader 5** | **ADAPT** | Retail Broker Gateway | Thin Windows IPC execution adapter; zero strategy logic inside MQL5. |
| **PyPortfolioOpt** | **REJECT** | None (Redundant) | Redundant to `skfolio`; lacks native scikit-learn pipeline design and CPCV. |
| **QuantConnect LEAN**| **REFERENCE**| Architectural Reference | Reference for multi-asset slicing and fill models; rejected runtime to avoid .NET CLR bloat. |
| **C++ / Rust** | **PYTHON-FIRST**| Performance Strategy | Python-first; Rust via NautilusTrader pre-compiled core; custom C++ rejected for V1. |

---

## 5. Absolute Engineering & Quantitative Rules

1. **Deterministic Risk Boundary:** The Risk Engine is a non-negotiable software gate. If Risk says `REJECT`, outcome is strictly **`REJECT`**. No AI model or optimizer can override risk limits.
2. **Baseline Beating Rule:** `skfolio` allocations must demonstrate statistically significant outperformance over Equal Weight and Inverse Volatility out-of-sample; otherwise, ACASH selects the simple baseline.
3. **No Look-Ahead Bias:** Strict bi-temporal indexing ($t_{\text{knowledge}} \le T_{\text{decision}}$). Feature calculations must use data available strictly at or before decision time.
4. **Append-Only Decision Ledger:** Historical decisions are never overwritten or deleted during normal operation.
5. **Immutable State Transitions:** State updates never mutate existing frozen objects. Fills produce new snapshot instances.

### ENGINEERING WORKFLOW ADDENDUM

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

Core loop:

$$\text{INSPECT} \to \text{UNDERSTAND} \to \text{PLAN} \to \text{APPROVE} \to \text{IMPLEMENT} \to \text{TEST} \to \text{SELF-REVIEW} \to \text{DOCUMENT}$$

### ENGINEERING RESEARCH ADDENDUM

Use the referenced trading-platform examples only as independent research references, not as ACASH architecture.

Potential future concepts worth preserving:
- Multi-source news / external evidence ingestion
- Evidence provenance and timestamps
- Forward / out-of-sample testing
- Research reproducibility
- Portfolio analytics

Do NOT expand Phase 1 scope for these concepts.

**Important architectural rule:**
`DecisionRecord` is immutable and append-only. Do not mutate it later to attach Fill/PnL outcomes. Preserve lineage through immutable references/correlation IDs so the complete decision $\to$ execution $\to$ outcome chain can be reconstructed without modifying historical records.

Do not treat AI confidence scores, huge backtest returns, or large data-source counts as evidence of trading edge without proper calibration, bias checks, and out-of-sample validation.

External systems such as MT4/MT5 or Agentic Trading Lab may only be future adapters/research references and must never become ACASH core dependencies without an explicit ADR.

Keep Phase 1 strictly foundational.

### RESEARCH LESSONS — TRADING SYSTEMS

From external trading-system examples/research, incorporate these principles into ACASH documentation/architecture only where appropriate:

1. **Data Quality & Provenance are Critical:**
   $$\text{Source} \to \text{Ingestion} \to \text{Validation} \to \text{Normalization} \to \text{Evidence} \to \text{Decision}$$
2. **AI is Analytical, NOT Execution Authority:**
   AI must remain an analytical component, NOT the final trading authority. Never treat AI confidence as proven probability/edge.
3. **Multi-Source Evidence Treatment:**
   News, macro, options, Greeks, IV, and external data should be treated as evidence/research inputs, not automatic signals.
4. **Explainability & Traceability:**
   Every decision should be explainable and traceable back to its evidence, data, calculations, and timestamp.
5. **Backtest Metrics $\neq$ Edge:**
   Backtest metrics (win rate, PF, Sharpe, expectancy, etc.) do NOT prove a real edge without proper OOS/forward testing, leakage checks, costs, slippage, and regime validation.
6. **Observability Matters:**
   $$\text{System State} \to \text{Metrics} \to \text{Monitoring} \to \text{Audit/Investigation}$$
7. **Decoupled External Systems:**
   External platforms/data providers may be used for independent research/evaluation, but must NOT become ACASH core dependencies without an explicit architectural decision.

> [!IMPORTANT]
> **Do not add new features or perform broad refactors based on these lessons.** Preserve current ACASH boundaries and apply only minimal, reversible documentation/architecture updates where justified.

**Core Research Loop:**
$$\text{Evidence} \to \text{Analysis} \to \text{Decision} \to \text{Execution} \to \text{Outcome} \to \text{Audit/Learning}$$

### FINAL RESEARCH LESSON — MARKET STRUCTURE

- **Options Flow is Positioning, Not Sentiment:** Do NOT interpret Options Flow simply as bullish/bearish sentiment. Flow is an observation of transactions/positioning; the essential question is: *"At this price/structure, who is forced to react, and what happens if price reaches that level?"*
- **Market Structure Precedes Strategy:** Market structure comes before strategy. Identify key levels/zones and how price behaves around them before selecting a strategy.
- **3-Dimensional Options Evaluation:** For options, evaluate at least 3 dimensions concurrently: $\text{Direction} \times \text{Volatility} \times \text{Time}$. Never judge an option setup from direction alone.
- **Market State $\neq$ Trade Signal:** Distinguish "market state / setup" $\neq$ "trade signal". The system should explain what condition exists and what actions/risk responses become relevant, rather than blindly outputting BUY/SELL.
- **Strict Arbitrage Exploitation:** Arbitrage is only meaningful when the pricing relationship is demonstrably exploitable after transaction costs, liquidity, execution risk, and timing friction.

**Market Structure Decision Loop:**
$$\text{OBSERVE} \to \text{IDENTIFY STRUCTURE} \to \text{QUANTIFY RISK/REWARD} \to \text{EVALUATE CONDITIONS} \to \text{DECIDE}$$

### QUANTITATIVE REASONING & DETERMINISTIC RISK PIPELINE

1. **Explicit Risk State:** Continuous, mathematical monitoring of portfolio risk health, capacity, and drawdown headroom.
2. **Margin Buffer Safety Threshold:** Mandatory buffer between utilized margin and maintenance limit before allowing new allocations.
3. **Net & Dollar Exposure Tracking:** Explicit dollar-denominated gross and net exposure accounting ($\text{Gross Exposure} = \sum |\text{Dollar Value}|$, $\text{Net Exposure} = \sum \text{Dollar Value}$).
4. **Deterministic Edge Metrics:** All analytical performance indicators (Sharpe, DSR, Information Ratio, expectancy, max drawdown) are calculated strictly by sovereign deterministic math engines, never by probabilistic estimation.
5. **Separation of Raw Metrics from AI Reasoning:** Raw quantitative metrics remain pure and immutable. AI reasoning is strictly downstream as an explanatory research tool, NEVER generating unverified numbers or placing trades.

$$\text{DATA} \to \text{QUANT ENGINE} \to \text{RISK STATE} \to \text{AI REASONING}$$
*$$\text{NOT: DATA} \to \text{AI} \to \text{Unverified Numbers} \to \text{TRADE}$$*

---

## 6. Documentation Index (`docs/`)

The complete canonical documentation suite is organized in [`docs/`](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs):

- **[docs/PROJECT_STATUS.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/PROJECT_STATUS.md)**: Workspace discovery, runtime state, and infrastructure boundaries.
- **[docs/ROADMAP.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/ROADMAP.md)**: Sequential 16-phase development roadmap with explicit phase gates.
- **[docs/TECHNOLOGY_EVALUATION.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/TECHNOLOGY_EVALUATION.md)**: 17-technology evaluation matrix across 10 engineering criteria.
- **[docs/ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/ARCHITECTURE.md)**: 7 decoupled layers, system dataflow, and performance hierarchy.
- **[docs/DATA_ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/DATA_ARCHITECTURE.md)**: Analytical (Parquet+DuckDB) vs Transactional (SQLite), `yfinance` boundaries, and bi-temporal schema.
- **[docs/PORTFOLIO_ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/PORTFOLIO_ARCHITECTURE.md)**: Portfolio optimization and risk-allocation methods vs transparent baselines.
- **[docs/EXECUTION_ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/EXECUTION_ARCHITECTURE.md)**: Pluggable execution adapters (Mock, MT5, Nautilus PoC candidate).
- **[docs/RESEARCH_ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/RESEARCH_ARCHITECTURE.md)**: Two-tier backtesting (vectorbt $\to$ Nautilus), CPCV, Deflated Sharpe Ratio, and Plotly charts.
- **[docs/DECISIONS.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/DECISIONS.md)**: Architectural Decision Records (**ADR-001 through ADR-016**).
- **[docs/RISKS.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/RISKS.md)**: Comprehensive Risk Register across quantitative, financial, operational, and technical dimensions.
- **[docs/PHASE_1_PLAN.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/PHASE_1_PLAN.md)**: Scope, dependency classifications, and correctness acceptance criteria for Phase 1.

---

## 7. Additional Reference Files

- **[Cheatsheet.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/Cheatsheet.md)**: Developer & Quant quick reference cheatsheet.
- **[Roadmap.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/Roadmap.md)**: High-level visual 16-phase development roadmap.
- **[Acash_Talk-27-08-2026.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/Acash_Talk-27-08-2026.md)**: Complete exported transcript of Phase 0 engineering dialogue.
