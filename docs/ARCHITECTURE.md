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

### 3.1 Normalized Monetary Valuation Assumptions
- **Base Currency Normalization:** `Position`, `PortfolioState`, and `AccountState` express monetary values in a defined ACASH base currency.
- **Account Balance vs Equity:**
  $$\text{Equity} = \text{Balance} + \text{Unrealized PnL}$$
  where $\text{Balance}$ represents the realized cash/account balance before unrealized position PnL is included.
- **Gross Exposure Definition:**
  $$\text{Gross Exposure} = \sum_{i} |\text{Normalized Position Value}_i|$$
  where **Normalized Position Value** is the position value expressed in ACASH base currency.
- **Deferred Valuation Complexity:** Market-specific valuation details (e.g. futures contract multipliers, CFD contract specifications, quote/base conversions, and real-time FX rate conversions) remain deferred and will not be prematurely encoded into Phase 1 domain models.

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
