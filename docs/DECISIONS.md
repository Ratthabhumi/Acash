# ACASH — Architectural Decision Records (ADRs)

**Document:** `docs/DECISIONS.md`  
**Version:** 3.4.0 (Immutable State Transitions & Normalized Value Applied)  
**Date:** 2026-08-27  

---

## ADR-001: Complete Isolation Between ACASH and Project Atlas
- **Status:** Approved
- **Context:** Project Atlas focuses on global work intelligence. ACASH focuses on market data, quantitative research, capital allocation, risk control, and trade execution.
- **Decision:** ACASH and Project Atlas are completely independent systems. Zero shared code dependencies, zero runtime coupling.
- **Consequences:** Eliminates failure cascading and preserves quantitative research domain purity.

---

## ADR-002: Modular Monolith Architecture
- **Status:** Approved
- **Context:** Splitting early-stage quant systems into distributed microservices creates network latency, serialization overhead, and debugging complexity.
- **Decision:** Build ACASH as a high-cohesion, low-coupling **Modular Monolith** in Python executing locally on a single machine (AIO).
- **Consequences:** Maximizes execution velocity, simplifies testing, and eliminates distributed infrastructure overhead.

---

## ADR-003: Deterministic Hard Risk Engine Boundary
- **Status:** Approved
- **Context:** Algorithmic bugs and statistical regime changes can cause rapid capital depletion if risk controls are probabilistic or advisory.
- **Decision:** The Risk Engine is a strictly deterministic, non-negotiable software gate. If the Risk Engine rejects an allocation or triggers a kill switch, it overrules all Alpha models, Portfolio Optimizers, and AI proposals with 100% authority. Phase 1 defines the `IRiskEngine` interface contract and `RiskAssessment` domain model; real risk evaluation logic is deferred to Phase 9.
- **Consequences:** Mathematically guarantees capital preservation constraints cannot be bypassed.

---

## ADR-004: skfolio Evaluation Against Transparent Baselines
- **Status:** Approved
- **Context:** Complex optimizers can overfit in-sample and fail out-of-sample due to parameter estimation error.
- **Decision:** `skfolio` is adopted behind `IPortfolioOptimizer`, but **must be evaluated for statistically significant incremental value versus transparent baselines out-of-sample** (Equal Weight, Inverse Volatility, Cash/No-Trade). The system must NOT force skfolio to win. If a simple baseline is more robust out-of-sample, ACASH selects the baseline.
- **Consequences:** Balances advanced portfolio optimization and risk-allocation methods with rigorous empirical baseline discipline.

---

## ADR-005: NautilusTrader as Tier-2 Event Simulation Candidate & Phase 1 Boundary
- **Status:** Approved
- **Context:** Realistic backtesting requires order-book matching, queue priority, and latency models.
- **Decision:** NautilusTrader is classified as **ADAPT — Tier-2 event-driven simulation and future execution candidate**. Phase 1 MUST NOT implement live Nautilus execution. Phase 1 defines abstract interfaces (`IBacktestEngine`, `IExecutionEngine`) and Mock/InMemory implementations only. NautilusTrader integration remains a future Phase 5 PoC.
- **Consequences:** Prevents premature coupling and preserves sovereign domain independence.

---

## ADR-006: Analytical Data (Parquet + DuckDB) vs Transactional State (SQLite) & PostgreSQL Deferral
- **Status:** Approved
- **Context:** Analytical time-series queries and transactional operational state require different database characteristics.
- **Decision:**
  - Analytical / Research Data: Local partitioned **Parquet files + DuckDB** query engine. (DuckDB is NOT used as a transactional control-plane DB).
  - Transactional Operational State: Local **SQLite** for V1 (order states, positions, and **append-only decision audit ledger**).
  - Enterprise Control Plane: **PostgreSQL is DEFERRED** until concurrent multi-process writers, production durability, or operational requirements justify it. (Do NOT install PostgreSQL in Phase 1).
- **Consequences:** Delivers optimal performance for each access pattern without premature server overhead.

---

## ADR-007: Bi-Temporal Point-in-Time Data Modeling (Alpha-Lake Principles)
- **Status:** Approved
- **Context:** Temporal leakage and look-ahead bias in data ingestion invalidate backtesting results.
- **Decision:** Adopt bi-temporal modeling principles natively: every record explicitly stores $t_{\text{event}}$ (when it occurred) and $t_{\text{knowledge}}$ (when it was ingested). Queries enforce $t_{\text{knowledge}} \le T_{\text{decision}}$.
- **Consequences:** Guarantees absolute prevention of look-ahead leakage.

---

## ADR-008: Two-Tier Backtesting Substrate
- **Status:** Approved
- **Context:** Exploring wide parameter spaces is slow in event engines, while vectorized engines lack realistic fill fidelity.
- **Decision:** Implement a two-tier methodology:
  1. **Tier-1:** `vectorbt` for rapid exploratory factor scanning and parameter sweeps.
  2. **Tier-2:** `NautilusTrader` candidate / Custom event engine for realistic microstructure validation.
- **Consequences:** Combines maximum research exploration speed with institutional validation rigor.

---

## ADR-009: Strict Confinement of AI & Foundation Models
- **Status:** Approved
- **Context:** Foundation models (e.g. Kronos, Vibe-Trading, LLMs) can hallucinate and are non-deterministic.
- **Decision:** Confine AI strictly to the quantitative research layer (`acash.research.ai`) for hypothesis drafting and summary generation. No AI system will have direct execution, portfolio weight, or risk control access.
- **Consequences:** Harnesses AI for research ideation while keeping operational capital allocation 100% deterministic.

---

## ADR-010: MT5 Adapter as Initial External Execution Gateway
- **Status:** Approved
- **Context:** MetaTrader 5 provides access to retail broker liquidity on Windows.
- **Decision:** MT5 is adopted strictly as an initial external execution adapter behind `IExecutionEngine`. Zero strategy or portfolio logic will be written in MQL5.
- **Consequences:** Allows broker connectivity without platform dependence.

---

## ADR-011: Strategy Lifecycle State Machine & Degradation Policy
- **Status:** Approved
- **Context:** Strategies inevitably experience alpha decay over time.
- **Decision:** Enforce formal state transitions: $\text{IDEA} \to \text{RESEARCH} \to \text{VALIDATION} \to \text{PAPER} \to \text{SMALL LIVE} \to \text{PRODUCTION} \to \text{DEGRADATION} \to \text{REDUCE} \to \text{RETIRE}$.
- **Consequences:** Automatically protects capital against decaying alpha.

---

## ADR-012: Adoption of yfinance as Research Data Adapter
- **Status:** Approved
- **Context:** Quantitative research requires accessible historical market and fundamental data for rapid prototyping.
- **Decision:** Adopt `yfinance` as a **research-oriented market/fundamental data adapter with no paid subscription requirement for the intended research use case, subject to source availability, API limitations, and applicable terms**. It is strictly isolated behind `IMarketDataProvider` and prohibited from live production execution feeds.
- **Consequences:** Enables zero-subscription research prototyping without compromising live data integrity.

---

## ADR-013: Selection of skfolio over PyPortfolioOpt
- **Status:** Approved
- **Context:** Modern portfolio theory and risk budgeting require a unified, scikit-learn compatible optimization framework.
- **Decision:** Adopt `skfolio` and reject `PyPortfolioOpt` to eliminate duplicate dependency bloat and API fragmentation.
- **Consequences:** Standardizes on modern portfolio optimization and cross-validation while eliminating redundant dependencies.

---

## ADR-014: Adoption of Plotly for Research & Analytics Visualization
- **Status:** Approved
- **Context:** Visualizing backtest tear sheets, equity curves, drawdown waterfalls, and factor distributions requires interactive charting.
- **Decision:** Adopt `plotly` as an analytical visualization dependency confined to `acash.telemetry`, research notebooks, and dashboards. Plotly has zero access to decision or risk logic.
- **Consequences:** Provides interactive visualization without impacting core engine performance.

---

## ADR-015: Python-First Core and Conditional Native Performance Acceleration
- **Status:** Approved
- **Context:** Premature C++ implementation introduces high development friction.
- **Decision:** ACASH is built **Python-first**. Native performance optimization follows a strict scientific workflow:
  $$\text{CORRECTNESS (Python)} \to \text{PROFILE} \to \text{IDENTIFY BOTTLENECK} \to \text{BENCHMARK} \to \text{OPTIMIZE (Rust/Numba)}$$
  Custom C++ is rejected for V1. Rust is leveraged via NautilusTrader's pre-compiled event engine bindings when needed.
- **Consequences:** Maximizes development velocity and mathematical correctness while preserving a proven path for high-performance execution.

---

## ADR-016: Domain Entity Flow Decoupling, Normalized Valuation & Append-Only Audit Lineage
- **Status:** Approved
- **Context:** Modeling domain entities as a single parent-child hierarchy violates the semantic separation between capital/portfolio state and decision/execution events.
- **Decision:**
  1. Separate domain entities into two interacting flows:
     - **Capital State Flow:** $\text{AccountState} \to \text{PortfolioState} \to \text{Positions}$
     - **Decision Flow:** $\text{Signal} \to \text{TargetAllocation} \to \text{RiskAssessment} \to \text{Order} \to \text{Fill} \to \text{State Transition}$
  2. **Immutable State Transitions:** State updates never mutate existing frozen objects; receiving a Fill produces **NEW Position**, **NEW PortfolioState**, and **NEW AccountState** snapshots.
  3. `DecisionRecord` is an **append-only audit and lineage object** referencing the complete decision chain. Historical decisions are never overwritten or deleted.
  4. Monetary values are normalized in a defined ACASH base currency. $\text{Equity} = \text{Balance} + \text{Unrealized PnL}$ (where Balance is realized cash). $\text{Gross Exposure} = \sum |\text{Normalized Position Value}|$, where **Normalized Position Value** is the position value expressed in ACASH base currency.
  5. Configuration directory is standardized as `configs/` across documentation and code (`configs/*.yaml`).
- **Consequences:** Establishes mathematically sound domain entities, complete auditability, immutability guarantees, and clean separation of concerns.
