# ACASH — System Architecture Specification
## Canonical Sovereign Architecture & Subsystem Invariant Blueprint

> **Document:** `docs/architecture/system_architecture.md`  
> **Version:** 4.0.0 (Pre-Phase-11 Architecture Hygiene & Sovereign Layer Alignment)  
> **Date:** 2026-09-02  
> **Frozen Baselines:** Phase 7 (Execution Reality), Phase 8 (Portfolio), Phase 8.5 (Alpha Research), Phase 9 (Risk Engine), Phase 10 (Runtime Orchestration)  
> **Contract Refinement:** Phase 11 Contract Specification & Red-Team Review v1.1 Locked (`86bff0d`)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Fail-Closed, Strict Separation of Concerns)

---

## 1. Executive Summary & Sovereign Layer Decoupling

ACASH (Automated Capital Allocation System) is an institutional-grade, evidence-driven, deterministic quantitative portfolio management and execution system. ACASH explicitly enforces a non-negotiable five-way sovereign decoupling across all operational planes:

$$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Supervisor\ (10)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)} \neq \mathbf{Forward\ Monitoring\ (11)} \neq \mathbf{Broker}}$$

```
                               ACASH SOVEREIGN ARCHITECTURAL MATRIX
┌───────────────────────┬──────────────────────────────────────┬──────────────────────────────────────────┐
│ Architectural Plane   │ Sovereign Point of Authority         │ Strict Non-Authority / Prohibitions      │
├───────────────────────┼──────────────────────────────────────┼──────────────────────────────────────────┤
│ Phase 8.5 (Research)  │ Historical Research Qualification    │ Forward Health Monitoring, Trading Orders│
│ Phase 8 (Portfolio)   │ Model Selection & Allocation Weights │ Execution Submission, Sovereign Risk Veto│
│ Phase 9 (Risk)        │ Hard Deterministic Boundary Veto     │ Portfolio Optimization, Broker Execution │
│ Phase 10 (Supervisor) │ 5-Stage Pulse Lifecycle Dispatch     │ Alpha Calculation, Direct Broker Wire    │
│ Phase 7 (Execution)   │ Broker Reality & Admission Guard     │ Alpha Qualification, Capital Sizing      │
│ Phase 11 (Forward)    │ Drift Evidence & Cost Attribution    │ Historical Mutation, Allocation Mutation │
│ Broker Wire           │ Raw Exchange / Venue Socket API      │ Internal Quantitative Decision Authority │
└───────────────────────┴──────────────────────────────────────┴──────────────────────────────────────────┘
```

---

## 2. The Seven Sovereign Architectural Layers

1. **RESEARCH DATA & MICROSTRUCTURE LAYER (Analytical Data Plane):**
   - Partitioned Parquet storage + embedded DuckDB analytical SQL engine.
   - Strict Point-In-Time (PIT) bi-temporal indexing (`knowledge_time_utc` vs `as_of_utc`) preventing lookahead bias.
   - DuckDB is strictly analytical, never used as a transactional control-plane database.

2. **QUANTITATIVE RESEARCH & ALPHA ENGINE (Phase 8.5):**
   - Econometric screening, Purged Combinatorial Purged Cross-Validation (CPCV), Deflated Sharpe Ratio (DSR), and Holm-Bonferroni multi-testing correction.
   - Emits immutable, cryptographically sealed `AlphaQualificationDossier` records.
   - Strictly zero capital authority ($0.00) and zero execution capabilities.

3. **PORTFOLIO ENGINE & TOURNAMENT SELECTION (Phase 8):**
   - Native Hierarchical Risk Parity (HRP) and Equal Risk Contribution (ERC) allocators, supplemented by transparent baselines (1/N, Inverse Volatility, Cash/NOWHERE).
   - Out-of-sample rolling tournament selection preserving `Candidate != Evaluation != Decision` and `Ranking != Approval`.
   - Emits versioned `AllocationDecision` records bound by cryptographic lineage digests.

4. **DETERMINISTIC RISK ENGINE & SOVEREIGN KILL SWITCH (Phase 9):**
   - `DeterministicRiskEngine` enforcing strict mathematical boundaries: gross leverage ceilings, asset concentration limits, mandatory cash floors, and rolling drawdown thresholds.
   - Monotonic `EXACT_SCALE_DOWN` derisking and `BINARY_REJECT` veto authority.
   - `SovereignKillSwitchController` with append-only disk persistence, crash/restart lockout (`PERSISTENTLY_BLOCKED`), and multi-sig Ed25519 quorum reset authorization.

5. **RUNTIME ORCHESTRATION & PULSE SUPERVISOR (Phase 10):**
   - 5-stage fail-closed operational supervisor ($\text{Data Freshness} \to \text{Strategy Census} \to \text{Tournament} \to \text{Risk Gate} \to \text{Execution Admission}$).
   - `OperationalScheduler` enforcing dual-clock discipline (`as_of_utc != wall_clock_utc`), pulse cadences, and concurrency lockout (`CYCLE_LOCKED_BUSY`).
   - `OperationalLedger` maintaining append-only SHA-256 hash-chained JSON Lines event persistence.
   - `ContinuousPaperDaemon` providing paper harness operations ($0 live capital authorization, 0 direct broker socket access).

6. **EXECUTION SUBSYSTEM & REALITY BOUNDARY (Phase 7):**
   - `ExecutionCoordinator` decoupling broker transport from order lifecycle management.
   - Pure state machine transition authority (`transition_order`) with absorbing terminal states.
   - Live execution adapter tested against Alpaca Paper (`AlpacaPaperExecutionAdapter`).

7. **ONLINE DRIFT DETECTION & COST ATTRIBUTION (Phase 11):**
   - Independent forward observational plane tracking strategy drift and execution reality drag.
   - Multi-stage decoupled pipeline: $\text{Calculation} \to \text{Detection} \to \text{Evidence} \to \text{Recommendation} \to \text{Governance Decision} \to \text{Eligibility Consequence}$.
   - Strictly observational; does not mutate historical dossiers, overwrite allocation parameters, or command broker orders.

---

## 3. End-to-End System Lifecycle & Execution Dataflow

```
                             ACASH OPERATIONAL PIPELINE
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │  STAGE 1: Ingestion & Telemetry      │
                      │  (Market Data Freshness Gate)        │
                      └──────────────────┬───────────────────┘
                                         │ Data Age <= max_market_data_age_ms
                                         ▼
                      ┌──────────────────────────────────────┐
                      │  STAGE 2: Active Strategy Census     │
                      │  (Filter RESEARCH_QUALIFIED dossiers)│
                      └──────────────────┬───────────────────┘
                                         │ Active Dossiers Available
                                         ▼
                      ┌──────────────────────────────────────┐
                      │  STAGE 3: Phase 8 Allocation         │
                      │  (OOS Tournament & Decision Record)  │
                      └──────────────────┬───────────────────┘
                                         │ AllocationDecision Emitted
                                         ▼
                      ┌──────────────────────────────────────┐
                      │  STAGE 4: Phase 9 Sovereign Risk     │
                      │  (Deterministic Boundary Evaluation) │
                      └──────────────────┬───────────────────┘
                                         │ Verdict in (APPROVED, REDUCED)
                                         ▼
                      ┌──────────────────────────────────────┐
                      │  STAGE 5: Phase 7 Execution Admission│
                      │  (Pre-Flight Order Intent Filtering) │
                      └──────────────────┬───────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
       ┌─────────────────────────┐               ┌─────────────────────────┐
       │ Alpaca Paper Transport  │               │ Operational Event Ledger│
       │ (Phase 7 Broker Wire)   │               │ (SHA-256 Chained Disk)  │
       └─────────────────────────┘               └─────────────────────────┘
```

---

## 4. Architectural Hygiene & Precision Contracts

### A. Dual-Clock Discipline & Runtime Determinism

ACASH enforces strict separation between logical evaluation time and operational observation time:

$$\boxed{\begin{array}{rcl}
\mathbf{Deterministic\ Domain\ Calculation} &\implies& \text{MUST receive explicit } \mathbf{as\_of\_utc} \\
\mathbf{Operational\ Metadata\ /\ Telemetry} &\implies& \text{MAY use } \mathbf{wall\_clock\_utc}
\end{array}}$$

- **Supervisor Guarantee:** The Phase 10 `RuntimeSupervisor` and `ContinuousPaperDaemon` **always explicitly pass `as_of_utc`** to downstream modules (`tournament_runner_fn`, `CandidateRiskAllocation`, and `risk_engine.evaluate_candidate_allocation`). Ambient system clock is never accessed during scheduled supervisor cycles.
- **Standalone Fallback Semantics:** In standalone component APIs (e.g. `PortfolioGovernanceGate`, `DeterministicRiskEngine`, `RebalancePlanner`), default fallbacks of the form `as_of or datetime.now(timezone.utc)` exist solely for unit tests, REPL exploration, and standalone scripts. These fallbacks do not change frozen public method signatures, but are bypassed in production supervisor cycles by explicit timestamp propagation.

---

### B. Numeric Precision Boundary & One-Way Canonicalization

To balance computational efficiency in matrix math with exact monetary conservation and collision-safe cryptographic identity:

```
┌──────────────────────────────────────┬────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Domain Subsystem                     │ Numeric Representation             │ Architectural Rationale                                │
├──────────────────────────────────────┼────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Phase 1 Domain Models (Legacy)       │ float                              │ Maintained for backward compatibility.                 │
│ Phase 8 Allocators (Matrix Solvers)  │ numpy.float64, scipy.optimize      │ Scientific optimization algorithms require float64.    │
│ Phase 8/9 Portfolio & Risk States    │ Decimal (quantized)                │ Exact monetary and weight conservation.                │
│ Phase 9 Risk State Bridge            │ Decimal <-> float conversion       │ Bounded compatibility adapter between layers.          │
│ Phase 10 Runtime Ledger              │ Decimal / ISO-8601 strings         │ Deterministic JSON serialization.                      │
│ Phase 11 Evidence Identity Paths     │ Decimal ONLY                       │ Strict reproducible evidence generation.               │
└──────────────────────────────────────┴────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

#### Strict Precision Invariant for Phase 11:
$$\boxed{\mathbf{Phase\ 11\ Evidence\ Generation} \implies \text{Strictly Prohibits } \mathbf{Decimal \longrightarrow float \longrightarrow Decimal} \text{ in Identity Calculations}}$$
- All forward returns, execution drag calculations, basis point attribution, and evidence digests in `StrategyForwardDriftEvidence` and `ExecutionCostEvidence` must be computed and digested purely in `Decimal` space.
- Existing float usage in numerical optimizers (Phase 8) and legacy domain models (Phase 1) is recognized honestly as layer-specific boundaries and is not obscured.

---

### C. Cryptographic Hashing Authority Hierarchy

To prevent hash collisions, fragmented serialization logic, and unauthorized cross-phase trust assumptions, all cryptographic digests across ACASH are categorized into a strict three-tier hierarchy:

```
┌────────────────────────────────────────┬───────────────────────────────────┬────────────────────────────────────────────┐
│ Hashing Tier                           │ Authoritative Engine              │ Target Domain & Scope                      │
├────────────────────────────────────────┼───────────────────────────────────┼────────────────────────────────────────────┤
│ Tier 1: Canonical Identity Hashes      │ CanonicalConfigSerializer         │ • AlphaQualificationDossier digests        │
│         (Lineage, Trust & Governance)  │ (18-digit Decimal quantization,   │ • StrategyForwardDriftEvidence digests     │
│                                        │  type-preserving delimiters)      │ • ExecutionCostEvidence digests            │
│                                        │                                   │ • Hypothesis & Policy SHA-256 digests      │
├────────────────────────────────────────┼───────────────────────────────────┼────────────────────────────────────────────┤
│ Tier 2: Monotonic Event Chaining       │ OperationalLedger Chaining Engine │ • OperationalCycleEvent previous_digest    │
│         (Disk Journal / Audit)         │ (Canonical JSONL event digest)    │ • Ledger crash & restart verification      │
├────────────────────────────────────────┼───────────────────────────────────┼────────────────────────────────────────────┤
│ Tier 3: Component-Local Convenience    │ Local sha256 helper               │ • Phase 8 tournament report internal digest│
│         (Ephemeral & Non-Authoritative)│ (json.dumps with sort_keys)       │ (Internal component record only)           │
└────────────────────────────────────────┴───────────────────────────────────┴────────────────────────────────────────────┘
```

#### Strict Hashing Invariants:
1. **Tier 3 Digest Trust Invariant:**
   $$\boxed{\mathbf{Tier\ 3\ Digest} \nRightarrow \text{Evidence Identity} \quad \land \quad \mathbf{Tier\ 3\ Digest} \nRightarrow \text{Cross-Phase Trust}}$$
   A Tier 3 local convenience digest must **NEVER** be accepted as an evidence identity, lineage identity, policy identity, or cross-phase authorization token.
2. **Zero 4th Hashing Scheme:**
   Phase 11 is strictly forbidden from introducing a new ad-hoc hashing utility. All Phase 11 evidence documents must exclusively use **Tier 1 (`CanonicalConfigSerializer`)**.

---

## 5. Summary of System Architectural Invariants

$$\boxed{\begin{array}{rcl}
\text{Research Qualification} &\neq& \text{Forward Health} \\
\text{Calculation} \neq \text{Detection} \neq \text{Evidence} &\neq& \text{Recommendation} \neq \text{Governance Decision} \\
\text{No Evidence} &\neq& \text{Negative Evidence} \\
\text{Estimated Friction} &\neq& \text{Empirical Realized Cost} \\
\text{Supervisor Cycle} &\implies& \text{Explicit as\_of\_utc} \\
\text{Zero Direct Broker Wire in Research, Portfolio, Risk, Runtime, or Forward Monitoring}
\end{array}}$$
