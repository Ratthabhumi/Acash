# ACASH — Automated Capital Allocation System

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary%20%2F%20Research-green.svg)](#)
[![Architecture: Modular Monolith](https://img.shields.io/badge/architecture-Modular%20Monolith-orange.svg)](#)
[![Status: Phase 5 Hardened](https://img.shields.io/badge/status-Phase%205%20Gate%20Passed%20(200%2F200%20Tests)-success.svg)](#)



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
                           MT5 Adapter      NautilusTrader Substrate
                           (Phase 12)       (Phase 5 Gate Passed)
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
5. **Event Simulation Substrate:** Native unmocked `NautilusTrader` Substrate and Sovereign Event Matching Engine (Phase 5 Gate Passed with Level-2 Depth Sweeps, Maker Queue Tracking, Double-Entry Shadow Ledger, and Disjoint Reference-Price Telemetry Attribution).
6. **Execution Subsystem:** Sovereign `IExecutionEngine` abstraction decoupling broker mechanics (Phase 12 MT5 adapter for live execution).
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

## 4. Completed Milestones & Quality Gates (Phases 0–16)

```
✅ Phase 0: Discovery & Architecture ──► [PASSED — Architecture & Decision Records Approved]
✅ Phase 1: Foundation & Domain Core ──► [GATE 1 PASSED — 27/27 Unit Tests, mypy clean]
✅ Phase 2: Data Ingestion & Integrity Engine ──► [GATE 2 PASSED — 57/57 Tests, mypy clean]
✅ Phase 3: Market Microstructure & PIT Feature Engine ──► [GATE 3 PASSED — 122/122 Tests, mypy clean]
   ├─ ✅ Phase 3A: Canonical Trades Domain (Time & Sales, Aggressor Side)
   ├─ ✅ Phase 3B: Canonical Order Book (L2 Depth Multi-Row Frames & Deltas, L3 MBO)
   └─ ✅ Phase 3C: Microstructure Feature Engine (VWAP, Volume Profile, Footprint, OBI, Micro-Price)
✅ Phase 4: Alpha Research Engine & Hypothesis Contract ──► [GATE 4 PASSED — 139/139 Tests, mypy clean]
✅ Phase 5: Backtesting Substrate & Simulation Engine ──► [GATE 5 PASSED — 200/200 Tests, mypy clean]
🔄 Phase 6: Statistical Validation & OOS Hard Gate ──► [UPCOMING — DESIGN PROPOSAL SIGNED OFF]
⏳ Phase 7: Regime Engine (Trend/Vol Classifiers) ──► Gate 7
⏳ Phase 8: Portfolio Engine (skfolio vs Baselines) ──► Gate 8
⏳ Phase 9: Deterministic Risk Engine & Kill Switch ──► Gate 9
⏳ Phase 10: Transaction Cost & Slippage Modeling ──► Gate 10
⏳ Phase 11: Paper Trading Subsystem ──► Gate 11
⏳ Phase 12: MT5 & Venue Execution Adapters ──► Gate 12
⏳ Phase 13: Live Small Capital Deployment ──► Gate 13 (MANDATORY HUMAN APPROVAL)
⏳ Phase 14: AI Quantitative Research Layer ──► Gate 14
⏳ Phase 15: Strategy Lifecycle State Machine ──► Gate 15
⏳ Phase 16: Performance Degradation & Learning Flywheel ──► Ongoing
```


### Detailed Summary of Delivered Capabilities:
1. **Phase 0 — Discovery & Architecture:**
   - Evaluated 17 quantitative & infrastructure technologies across 10 engineering criteria.
   - Established 7 decoupled layers and 19 Architectural Decision Records (ADR-001 to ADR-019).
2. **Phase 1 — Foundation & Domain Core:**
   - Sovereign immutable domain models (`src/acash/core/domain/`) with strict Decimal finite arithmetic.
   - Pure state transitions for 8 signed-quantity position fill scenarios, spot cash flows, and zero Realized PnL double-counting.
   - Append-only decision audit ledger and structured telemetry logger with recursive secret redaction.
3. **Phase 2 — Data Ingestion & Integrity Engine:**
   - Canonical PyArrow schema (`Decimal128(38,18)`, `timestamp[us, tz=UTC]`) in `src/acash/data/schema.py`.
   - Per-Stream Data Integrity Validator (`integrity.py`) enforcing event monotonicity and anomaly preservation without data mutation.
   - Provenance & Manifest Engine (`provenance.py`) with raw source SHA-256 and canonical logical SHA-256 invariant to Parquet compression and row ordering.
   - Parquet Storage Engine (`storage.py`) with strict 1:1 Ingestion Unit mapping, Recoverable Batch Commit Protocol (`PREPARED` $\to$ `PART_PUBLISHED` $\to$ `COMMITTED`), crash recovery, and orphan part quarantine.
   - DuckDB Point-in-Time qualification query layer with multi-source isolation and lookahead prevention.
4. **Phase 3A — Canonical Trades Domain:**
   - Canonical trades schema supporting nanosecond-precision trade records, aggressor side classifications, and trade conditions.
   - Length-prefixed binary serialization and logical SHA-256 hashing.
5. **Phase 3B — Canonical Order Book Domain:**
   - Canonical L2 Market-by-Price (MBP) multi-row frame snapshots and deltas, and L3 Market-by-Order (MBO).
   - Deterministic 5-tuple order reconstruction (`exchange_time_utc`, `source_order_key`, `message_type_rank`, `stream_id`, `row_sub_index`).
   - Explicit `CLEAR` level semantics (distinguishing zero-volume deletions from NULL clear operations).
6. **Phase 3C — Microstructure Feature Engine:**
   - Derived mathematical features: Session VWAP, Volume-Weighted Dispersion ($\sigma$), Volume Profile with POC lower-price tie-breakers, Value Area 70% bounds, Footprint Analytics (Stacked Imbalances, CVD, Absorption), and Depth-Weighted Micro-Price.
   - Dual-temporal point-in-time filtering ($T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$) preventing lookahead and revision leakage.
7. **Phase 4 — Alpha Research Engine & Hypothesis Contract:**
   - Formal, pre-registered `HypothesisSpecification` with explicit falsification criteria.
   - Discrete bar-indexed forward returns ($R(t,H) = \frac{P_{\text{close}, t+H} - P_{\text{open}, t+1}}{P_{\text{open}, t+1}}$) eliminating off-by-one ambiguities.
   - Primary econometric inference via OLS slope $\hat{\beta}_H$ under Newey-West / HAC covariance using Bartlett kernel with verified analytical reference vector.
   - Descriptive non-parametric association: Pearson IC, Spearman Rank IC (with fractional tie-handling), and Autocorrelation.
   - 3-Tier Friction Waterfall: Raw Predictive Edge $\to$ Spread + Fee Net $\to$ Fixed Slippage Proxy Economic Edge.
   - Interval-based boundary purging across partition splits and unallocated embargo buffers ($\ge \max(H)$ bars).
   - Durable Blind OOS Governance Ledger (`data/manifests/research/governance_ledger.json`) locking OOS exposure (`UNEXPOSED` $\to$ `EVALUATED_LOCKED` $\to$ `EXHAUSTED`).
8. **Phase 5 — Backtesting Substrate & Simulation Engine:**
   - Sovereign event-driven simulation substrate with simulated order lifecycle state machine (`CREATED` $\to$ `SUBMITTED` $\to$ `ACCEPTED` $\to$ `FILLED`).
   - Canonical Data Adapter enforcing Phase 3B total ordering 5-tuple: $(T_{\text{event\_utc}}, \text{source\_order\_key}, \text{message\_rank}, \text{stream\_id}, \text{row\_sub\_index})$.
   - Decoupled double-entry shadow ledger (Balance-Sheet View vs Performance Attribution View) eliminating Realized PnL double counting ($|\text{AccountingResidual}| \le 10^{-10}$).
   - Unmocked native `NautilusTrader` execution substrate with Parquet catalog bridge and contract specification mapping.
   - Deterministic content-derived `BacktestManifest` identity: $\text{manifest\_id} = \text{SHA256}(\text{canonical}(\text{hypothesis\_hash} + \text{data\_hashes} + \text{engine\_hash} + \text{strategy\_hash} + \text{seed}))[:32]$.
   - Reality Gap Telemetry Engine implementing disjoint non-overlapping reference-price decomposition: Spread Drag, Slippage Drag, Latency Drag, Fee Drag, Maker Adverse Selection Drag, and Unmodelled Residual.
   - Baseline strategy actors: Microstructure Imbalance (OBI) & Session VWAP Mean Reversion.

---

## 5. Documentation Index (`docs/`)

The complete canonical documentation suite is organized in [`docs/`](docs/):

- **[`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md)**: Canonical Market Data Contract, Decimal128(38,18), bi-temporal precision, and Recoverable Batch Commit Protocol.
- **[`docs/DATA_ARCHITECTURE.md`](docs/DATA_ARCHITECTURE.md)**: Analytical (Parquet+DuckDB) partitioned immutable parts, bi-temporal P-I-T qualification queries, and provenance ledger.
- **[`docs/DECISIONS.md`](docs/DECISIONS.md)**: Architectural Decision Records (**ADR-001 through ADR-019**).
- **[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)**: Workspace discovery, runtime state, and infrastructure boundaries.
- **[`docs/ROADMAP.md`](docs/ROADMAP.md)**: Sequential 16-phase development roadmap with explicit phase gates.
- **[`docs/PHASE_3C_DESIGN_PROPOSAL.md`](docs/PHASE_3C_DESIGN_PROPOSAL.md)**: Microstructure Feature Extraction Engine Design Proposal (Signed Off).
- **[`docs/PHASE_4_DESIGN_PROPOSAL.md`](docs/PHASE_4_DESIGN_PROPOSAL.md)**: Alpha Research Engine and Hypothesis Contract (Signed Off).
- **[`docs/PHASE_5_DESIGN_PROPOSAL.md`](docs/PHASE_5_DESIGN_PROPOSAL.md)**: Event-Driven Backtesting Substrate & Simulation Integration (v1.2.0 Signed Off).

- **[`docs/TECHNOLOGY_EVALUATION.md`](docs/TECHNOLOGY_EVALUATION.md)**: 17-technology evaluation matrix across 10 engineering criteria.
- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**: 7 decoupled layers, system dataflow, and performance hierarchy.
- **[`docs/PORTFOLIO_ARCHITECTURE.md`](docs/PORTFOLIO_ARCHITECTURE.md)**: Portfolio optimization and risk-allocation methods vs transparent baselines.
- **[`docs/EXECUTION_ARCHITECTURE.md`](docs/EXECUTION_ARCHITECTURE.md)**: Pluggable execution adapters (Mock, MT5, Nautilus substrate).
- **[`docs/RESEARCH_ARCHITECTURE.md`](docs/RESEARCH_ARCHITECTURE.md)**: Two-tier backtesting (vectorbt $\to$ Nautilus), CPCV, Deflated Sharpe Ratio, and Reality Gap Analysis.
- **[`docs/RISKS.md`](docs/RISKS.md)**: Comprehensive Risk Register across quantitative, financial, operational, and technical dimensions.

---

## 6. License & Proprietary Rights

**Copyright © 2026 Ratthabhumi & ACASH Contributors. All Rights Reserved.**

This software, including all underlying source code, documentation, schemas, algorithms, and mathematical models, is proprietary and confidential. Unauthorized copying, distribution, modification, public display, reverse engineering, or extraction of any part of this repository, via any medium, is strictly prohibited without explicit written consent.
