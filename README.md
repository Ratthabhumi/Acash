# ACASH — Automated Capital Allocation System
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary%20%2F%20Research-green.svg)](#)
[![Architecture: Modular Monolith](https://img.shields.io/badge/architecture-Modular%20Monolith-orange.svg)](#)
[![Status: Phase 10 Frozen (904 tests) - Phase 11 Contract Locked](https://img.shields.io/badge/status-Phase%2010%20Frozen%20(904%20tests)%20--%20Phase%2011%20Contract%20Locked-green.svg)](docs/ROADMAP.md)

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

## 2. System Architecture & Decoupled Sovereign Layers

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
                          (Signals & Hypothesis Specification)
                                        │
                                        ▼
                                4. VALIDATION ENGINE
                             (Purged CPCV & DSR Gate)
                                        │
                                        ▼
                              5. ALPHA QUALIFICATION
                       (Phase 8.5 Dossiers & Economic Lineage)
                                        │
                                        ▼
                               6. PORTFOLIO ENGINE
                      (Phase 8 Tournament vs Baselines: EW/InvVol/Cash)
                                        │
                                        ▼
                              7. RUNTIME SUPERVISOR
                     (Phase 10 5-Stage Orchestrator & Dual-Clock)
                                        │
                                        ▼
                                8. SOVEREIGN RISK
                     (Phase 9 Deterministic Veto & Kill Switch)
                                        │
                                        ▼
                               9. EXECUTION ENGINE
                      (Phase 7 Coordinator & Alpaca Paper)
                                        │
                                        ▼
                    10. APPEND-ONLY OPERATIONAL LEDGER
                      (Phase 10 SHA-256 Chained Disk Events)
                                        │
                                        ▼
                    11. FORWARD MONITORING & REALITY GAP
                     (Phase 11 Strategy Drift & Drag Attribution)
```

### Sovereign Layer Responsibilities
1. **Research Data Layer (Analytical):** Partitioned Parquet files + embedded DuckDB query engine for vectorized analytical SQL queries + `yfinance` research data adapter.
2. **Analytics & Quant Research:** `pandas`, `NumPy`, `vectorbt` (Tier-1 rapid parameter screening), and `Plotly` (interactive visualization).
3. **Alpha Engine & Hypothesis Contract:** Strict pre-registered hypothesis contracts, econometric forward returns, and Newey-West / HAC inference.
4. **Statistical Validation Engine:** Combinatorial Purged Cross-Validation (CPCV), Deflated Sharpe Ratio (DSR), MinTRL, Holm-Bonferroni FWER multiple testing corrections, and Probability of Backtest Overfitting (PBO).
5. **Alpha Qualification Engine (Phase 8.5):** Canonical `AlphaQualificationDossier` and `AlphaEconomicDecomposition` DTOs certifying economic edge ($Net = Gross - Friction$) with **$0.00 capital authority**.
6. **Portfolio Engine & Tournament (Phase 8):** Native HRP and ERC optimizers evaluated strictly in zero-leakage tournaments against transparent baselines (Equal Weight, Inverse Volatility, Cash/NOWHERE).
7. **Runtime Supervisor & Operational Scheduler (Phase 10):** Dual-clock cadence coordination ($as\_of\_utc \neq wall\_clock\_utc$) and authoritative 5-stage cycle orchestration ($\text{Data} \to \text{Census} \to \text{Tournament} \to \text{Risk} \to \text{Admission}$).
8. **Deterministic Risk Engine & Kill Switch (Phase 9):** Non-negotiable sovereign risk boundary (`DeterministicRiskEngine`), exact monotonic derisking (`EXACT_SCALE_DOWN`), and multi-sig `Ed25519TrustStore` quorum reset control.
9. **Execution Engine & Broker Mapping (Phase 7):** Sovereign `ExecutionCoordinator`, vendor-agnostic broker semantic mapping (BMAP), and venue-pinned Alpaca Paper adapter.
10. **Operational Ledger (Phase 10):** Cryptographic SHA-256 chained disk ledger (`OperationalLedger`) with full crash recovery and tamper detection.
11. **Forward Monitoring & Execution Reality (Phase 11):** Independent observational plane tracking online strategy decay (`StrategyForwardDriftEvidence`) and empirical execution drag decomposition (`ExecutionCostEvidence`).

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
        CROSS-CUTTING AUDIT LINEAGE
        ───────────────────────────
               OperationalCycleEvent / DecisionRecord (Append-Only)
          ↳ Observed Market Inputs
          ↳ Alpha Qualification Dossier Hash
          ↳ Target Allocation Decision Hash
          ↳ Risk Evaluation Verdict
          ↳ Execution Manifest Digest
          ↳ Chained Event Digest (SHA-256)
```

---

## 4. Completed Milestones & Quality Gates (Phases 0–11)

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
✅ Phase 6: Statistical Validation & Overfitting Controls ──► [GATE 6 PASSED — CPCV, DSR, MinTRL, PBO, Search Ledger, OOS Hard Gate]
✅ Phase 7: Live Execution & Broker Mapping (Admission → Coordinator → BMAP → Alpaca Paper) ──► Gate 7 [FROZEN — E-verified code path, P = 0]
✅ Phase 8: Portfolio Engine (Native HRP/ERC Optimizers vs Baselines & Tournament) ──► Gate 8 [FROZEN @ e6f1d04]
✅ Phase 8.5: Alpha Research & Economic Evidence Engine (Dossier Gate & Lineage DTOs) ──► Gate 8.5 [FROZEN @ 9ce1365]
✅ Phase 9: Deterministic Risk Engine & Sovereign Kill Switch ──► Gate 9 [FROZEN @ 6bd40d8]
✅ Phase 10: Runtime Orchestration & Continuous Paper Operations (Supervisor + Scheduler + Ledger) ──► Gate 10 [FROZEN @ 3955bf6]
🟡 Phase 11: Forward Tracking, Online Drift Detection & Execution Reality Attribution ──► Gate 11 [CONTRACT SPEC v1.0 LOCKED @ e2534dc]
⏳ Phase 12: MT5 & Multi-Venue Execution Adapters ──► Gate 12
⏳ Phase 13: Live Small Capital Deployment ──► Gate 13 (MANDATORY HUMAN APPROVAL)
⏳ Phase 14: AI Quantitative Research Layer ──► Gate 14
⏳ Phase 15: Strategy Lifecycle Management ──► Gate 15
⏳ Phase 16: Performance Degradation & Data Flywheel ──► Ongoing
```es) ──► Gate 8
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
9. **Phase 6 — Statistical Validation & Overfitting Controls:**
   - Combinatorial Purged Cross-Validation (`cpcv.py`): Contiguous $N$-group partitioning, exhaustive $\binom{N}{k}$ combinatorial splits, strict $[t+1, t+H]$ interval purging, post-test embargo buffers, and chronological pseudo-OOS path reconstruction ($\phi = \frac{k}{N}\binom{N}{k}$).
   - Deflated Sharpe Ratio & MinTRL (`deflated_sharpe.py`): Non-normal asymptotic inference (Bailey & López de Prado 2014) with Euler-Mascheroni constant $\gamma_E$, empirical trial variance $V$, Fisher-Pearson skewness $g_1$, and Pearson kurtosis $g_2$.
   - Multiple Testing Corrections (`multiple_testing.py`): Holm-Bonferroni (FWER), Benjamini-Hochberg (FDR), and Harvey-Liu-Zhu (2016) Haircut Sharpe Ratio.
   - Probability of Backtest Overfitting & Fragility (`overfitting.py`): Mid-rank tie-breaking log-odds PBO, parameter sensitivity curvature over strict $[0.75\theta_0, 1.0\theta_0, 1.25\theta_0]$ grids, and component-wise friction stress decay monotonicity.
   - Sovereign Validation Gate (`gate.py`): Invariant trial intensity coupling ($K_{\text{ledger}} \equiv K_{\text{DSR}} \equiv K_{\text{Holm}} \equiv K_{\text{BH}}$), strict fail-closed OOS execution, and dual cryptographic lineage digests (`evidence_digest` and `decision_digest`).
10. **Phase 7 — Live Execution & Broker Mapping (IN PROGRESS — 588 Unit Tests Passed, BMAP E-Reviewed, P = 0):**
    - Admission/Authorization gate, Step 8 Execution Contract, Step 8B State Machine, Step 8C Broker Event Normalizer, Step 8D Mock Broker, Step 8E Execution Coordinator & Reconciliation Boundary, Operational Restriction, Real Broker Contract, and Vendor-Agnostic Broker Semantic Mapping Framework: **LOCKED**.
    - **Implementation & Local Test Verification:** Complete (588/588 unit tests passing across entire repository).
    - **Broker Semantic Evidence (BMAP):** E-reviewed against official broker API documentation (`BMAP 01–10 = E`, `BMAP 11 = E*`, `BMAP 12 = D`).
    - **Concrete Components:** Alpaca Paper Transport (`PaperHttpAlpacaTransport`), Paper Credential Boundary (venue-pinned `ALPACA_PAPER`), `AlpacaPaperAdapter`, R0 read-only harness, R1 lifecycle harness, and local Windows DPAPI vault launcher.
    - **Defect Fixes Committed:** `4a92348` (connect-before-submit) and `8e92188` (paper-only transport injection guard).
    - **Paper Runtime Evidence:** **P = 0.** No real Paper order has been executed; no live/paper telemetry collected; Live trading NOT ready.

---

## 5. Documentation Index (`docs/`)

The complete canonical documentation suite is organized systematically in [`docs/`](docs/):

### 🧭 System Governance & Roadmap
- **[`docs/README.md`](docs/README.md)**: Master Documentation Hub and Progressive Disclosure Index.
- **[`docs/ROADMAP.md`](docs/ROADMAP.md)**: Sequential 16-phase development roadmap with explicit quality gates.
- **[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)**: Current system discovery, runtime state, and infrastructure boundaries.
- **[`docs/DECISIONS.md`](docs/DECISIONS.md)**: Canonical Architectural Decision Records (**ADR-001 through ADR-019**).
- **[`docs/RISKS.md`](docs/RISKS.md)**: Comprehensive Risk Register across quantitative, financial, operational, and technical dimensions.

### 🏛️ Core Architecture Specifications (`docs/architecture/`)
- **[`docs/architecture/system_architecture.md`](docs/architecture/system_architecture.md)**: 7 decoupled layers, system dataflow, and performance hierarchy.
- **[`docs/architecture/data_architecture.md`](docs/architecture/data_architecture.md)**: Analytical (Parquet+DuckDB) partitioned immutable storage & bi-temporal qualification.
- **[`docs/architecture/data_contract.md`](docs/architecture/data_contract.md)**: Canonical Market Data Contract, `Decimal128(38,18)`, and Recoverable Batch Commit Protocol.
- **[`docs/architecture/execution_architecture.md`](docs/architecture/execution_architecture.md)**: Sovereign execution subsystem, order lifecycle state machine, and reconciliation loop.
- **[`docs/architecture/portfolio_architecture.md`](docs/architecture/portfolio_architecture.md)**: `skfolio` optimization vs transparent baselines (Equal Weight, Inv Vol, Cash).
- **[`docs/architecture/research_architecture.md`](docs/architecture/research_architecture.md)**: Two-tier research engine, econometric inference, and reality gap decomposition.
- **[`docs/architecture/technology_evaluation.md`](docs/architecture/technology_evaluation.md)**: 17-technology evaluation matrix across 10 engineering criteria.

### 📜 Historical Phase Plans & Proposals (`docs/proposals/`)
- **[`docs/proposals/phase_1_foundation.md`](docs/proposals/phase_1_foundation.md)**: Phase 1 Foundation & Domain Core Plan.
- **[`docs/proposals/phase_3_microstructure.md`](docs/proposals/phase_3_microstructure.md)**: Phase 3 Market Microstructure & PIT Feature Engine Plan.
- **[`docs/proposals/phase_3b_orderbook.md`](docs/proposals/phase_3b_orderbook.md)**: Phase 3B Canonical Order Book & Reconstruction Proposal.
- **[`docs/proposals/phase_3c_feature_engine.md`](docs/proposals/phase_3c_feature_engine.md)**: Phase 3C Microstructure Feature Extraction Engine Proposal.
- **[`docs/proposals/phase_4_alpha_engine.md`](docs/proposals/phase_4_alpha_engine.md)**: Phase 4 Alpha Research Engine and Hypothesis Contract.
- **[`docs/proposals/phase_5_simulation.md`](docs/proposals/phase_5_simulation.md)**: Phase 5 Event-Driven Backtesting Substrate & Simulation Proposal.
- **[`docs/proposals/phase_6_validation.md`](docs/proposals/phase_6_validation.md)**: Phase 6 Statistical Validation & Overfitting Controls Proposal.

### 🛡️ Phase 6: Statistical Governance (`docs/validation/`)
- **[`docs/validation/methodology_contract.md`](docs/validation/methodology_contract.md)**: Master Methodology Contract (DSR, MinTRL, CPCV, Mid-Rank PBO, FWER).
- **[`docs/validation/phase6_methodology_dgp_report.md`](docs/validation/phase6_methodology_dgp_report.md)**: Data Generating Process (DGP) benchmark empirical experiments report.

### ⚡ Phase 7: Live Execution & Broker Integration (`docs/phase7/`)
- **[`docs/phase7/phase_7_proposal.md`](docs/phase7/phase_7_proposal.md)**: Phase 7 Proposal & Evolution Specification (Active Phase Architecture & Evidence Model).
- **[`docs/phase7/CONTEXT_MAP.md`](docs/phase7/CONTEXT_MAP.md)**: Phase 7 navigation context map and core invariants.
- **[`docs/phase7/alpaca_bmap.md`](docs/phase7/alpaca_bmap.md)**: Alpaca Concrete Broker Semantic Mapping (BMAP).
- **[`docs/phase7/paper_exercise_r1.md`](docs/phase7/paper_exercise_r1.md)**: R1 order-lifecycle contract & P evidence checklist.
- **[`docs/phase7/r1_paper_run_runbook.md`](docs/phase7/r1_paper_run_runbook.md)**: R1 Paper-run operational runbook.
- **[`docs/phase7/execution_state_machine.md`](docs/phase7/execution_state_machine.md)**: Sovereign order & fill execution state machine.

### 🌐 Project Atlas Knowledge Graph (`docs/atlas/`)
- **[`docs/atlas/CONTEXT_MAP.md`](docs/atlas/CONTEXT_MAP.md)**: Project Atlas Master Architecture & Microstructure Ontology.

---

## 5.5 CURRENT STATUS / NEXT STEP — Phase 7 / R1-REAL Broker-Observed Execution

> **As of HEAD `4faa81a` (pushed to `origin/main`).** This is the authoritative resume point
> for the current session — see [`docs/ROADMAP.md`](docs/ROADMAP.md) and
> [`Cheatsheet.md`](Cheatsheet.md) for the identical status block.

### Where the project is
- Phases 0–6 complete & hardened (Gates 1–6 passed).
- **Phase 7 (Live Execution & Broker Mapping): IN PROGRESS.**
  - Real Broker Observation Driver `R1RealOrderExerciseDriver` implemented and provenance-hardened (`4faa81a`).
  - Strict BMAP-07 cancellation reconciliation, dual-channel observation (SSE Primary + REST Polling Recovery), and fail-closed timeout to `UNKNOWN`.
  - **598 unit and invariant tests passing** (100% clean offline).
  - DPAPI Local User Vault & Secure Launcher operational.
- **Key Phase 7 Commits Trail:** `22b6a28` (R1 harness) · `4a92348` (connect-before-submit fix) · `8e92188` (paper-only injection guard) · `61233ad` (Phase 7 proposal) · `3dd9f25` (Paper incident checkpoint) · `353ac8c` (R1-REAL spec) · `4faa81a` (R1-REAL provenance hardening).

### Tri-Partite Evidence & Verification Architecture
| Dimension | Meaning | Current Phase 7 Status |
| :--- | :--- | :--- |
| **Local Unit Tests** | Automated code regression & invariant verification | **598/598 tests passing** (100% clean) |
| **E (Broker Semantic Review)** | Specification verified against official broker API documentation | **BMAP 01–10 = E, BMAP 11 = E\*, BMAP 12 = D** |
| **P (Paper Runtime Observation)** | Actual Paper runtime execution with complete cryptographic lineage | **P = 0** (Paper orders submitted & audited, zero unverified fills) |

$$\boxed{\text{598 Unit Tests} \neq E \text{ (Broker Semantic Review)} \neq P \text{ (Empirical Paper Execution)}}$$

A successful HTTP response, a unit test pass, or a `FILLED` state alone is **not** P.
Only a real Paper order whose evidence satisfies the full conjunctive rule produces valid P evidence.

### What has and has NOT been proven
- **Proven (Implementation, E-Review, & Real Wire POST):** Real HTTP order submission to Alpaca Paper, REST snapshot recovery, BMAP-07 reconciliation, fail-closed timeout to `UNKNOWN`, zero synthetic event injections, DPAPI credential protection.
- **NOT proven (P & Live):** Executed fill under real market conditions ($P = 0$), Live readiness. **Live trading is HARD-LOCKED.**

### Paper Order Forensic History
- **Order 001 (`acash-r1-paper-20260831-001`):** Real Paper POST succeeded $\to$ rested in `accepted` $\to$ confirmed `CANCELED` via REST ($P = 0$).
- **Order 002 (`acash-r1-paper-20260831-002`):** Real Paper POST succeeded $\to$ resting in `new` with `filled_qty = 0` ($P = 0$).

### P acceptance rule (conjunctive — ALL must hold)
$$\text{P} = \text{TerminalVerified} \land \text{EvidenceLineageComplete} \land \text{ReconciliationVerified} \land \text{NoDispute}$$

---

## 6. License & Proprietary Rights

**Copyright © 2026 Ratthabhumi & ACASH Contributors. All Rights Reserved.**

This software, including all underlying source code, documentation, schemas, algorithms, and mathematical models, is proprietary and confidential. Unauthorized copying, distribution, modification, public display, reverse engineering, or extraction of any part of this repository, via any medium, is strictly prohibited without explicit written consent.
