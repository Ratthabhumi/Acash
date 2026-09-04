# ACASH — System Development Roadmap (Phases 0–16)

**Document:** `docs/ROADMAP.md`  
**Version:** 3.3.0  
**Date:** 2026-08-28  
**Governance Principle:** Sequential Phase Progression. No phase skipping. Every phase has explicit gates, acceptance criteria, and human approval checkpoints.

> **Note on Phase 7 scope:** This roadmap's original nominal title for Phase 7
> was "Regime Engine (Trend/Vol Classifiers)". The **actual** Phase 7 work being
> executed in this repository is **Live Execution & Broker Mapping** (Admission →
> Step 8 Contracts → Broker Semantic Mapping → Alpaca Paper exercise). The
> Regime-Engine content is deferred; Phase 7 below reflects the real scope.

---

## Roadmap Overview

```
✅ Phase 0: Discovery & Architecture ──► [COMPLETED - PASSED]
   │
   ▼
✅ Phase 1: Foundation & Domain Core ──► Gate 1 [COMPLETED - PASSED — 27/27 Tests]
   │
   ▼
✅ Phase 2: Data Ingestion & Integrity Engine ──► Gate 2 [COMPLETED - PASSED — 57/57 Tests]
   │
   ▼
✅ Phase 3: Point-in-Time Microstructure & Feature Engine (3A/3B/3C) ──► Gate 3 [COMPLETED - PASSED — 122/122 Tests]
   ├─ ✅ Phase 3A: Canonical Trades Domain
   ├─ ✅ Phase 3B: Canonical Order Book Domain
   └─ ✅ Phase 3C: Microstructure Feature Engine
   │
   ▼
✅ Phase 4: Alpha Research Engine & Hypotheses ──► Gate 4 [COMPLETED - PASSED — 139/139 Tests]
   │
   ▼
✅ Phase 5: Backtesting Substrate & Simulation Engine ──► Gate 5 [COMPLETED - PASSED — 200/200 Tests]
   │
   ▼
✅ Phase 6: Statistical Validation & Overfitting Controls ──► Gate 6 [COMPLETED - PASSED — 252/252 Tests]
   │
   ▼

✅ Phase 7: Live Execution & Broker Mapping (Admission → Coordinator → BMAP → Alpaca Paper) ──► Gate 7 [COMPLETED - PASSED — 610/610 Tests, P = 1 (P-001)]
   │
✅ Phase 8: Portfolio Engine (skfolio & Baselines) ──► Gate 8 [COMPLETED - PASSED]
   │
   ▼
✅ Phase 8.5: Alpha Research & Economic Evidence Engine ──► Gate 8.5 [COMPLETED - PASSED]
   │
   ▼
✅ Phase 9: Deterministic Risk Engine & Kill Switch ──► Gate 9 [COMPLETED - PASSED]
   │
   ▼
✅ Phase 10: Runtime Orchestration & Continuous Paper Operations ──► Gate 10 [COMPLETED - PASSED]
   │
   ▼
✅ Phase 11: Forward Tracking, Online Drift Detection & Execution Reality Attribution ──► Gate 11 [COMPLETED - PASSED — 107 Tests, 26 Red Team, 9 Integration]
   │
   ▼
✅ Phase 12: MT5 & Venue Execution Adapters ──► Gate 12 [COMPLETED & FROZEN — 1240/1240 Tests, 1e1d154]
   │
   ▼
⏳ Phase 13: Live Small Capital (MANDATORY HUMAN APPROVAL) ──► Gate 13
   │
   ▼
⏳ Phase 14: AI Quantitative Research Layer ──► Gate 14
   │
   ▼
⏳ Phase 15: Strategy Lifecycle State Machine ──► Gate 15
   │
   ▼
⏳ Phase 16: Performance Degradation & Data Flywheel ──► Ongoing
```

---

## CURRENT STATUS / NEXT STEP — Phase 7 Passed (P = 1) ──► Phase 8 Portfolio Engine

> **As of Checkpoint `P-001` (Order 003).**
> Gate 7 is officially verified and accepted. Live execution remains **HARD-LOCKED (OFF)**.

### Completed milestones
- ✅ Phases 0–6: Gates 1–6 passed (validated statistical governance FROZEN).
- ✅ Phase 7 design/contract layer: Admission LOCKED; Step 8 / 8B / 8C / 8D / 8E
  LOCKED; Operational Restriction LOCKED; Real Broker Contract LOCKED; BMAP
  framework LOCKED.
- ✅ Alpaca concrete BMAP: Conformance Matrix 100% PASS (`P = 1`).
- ✅ Concrete Alpaca Paper Transport, Paper Credential Boundary (`ALPACA_PAPER`),
  `AlpacaPaperAdapter`, DPAPI User Vault & Secure Launcher.
- ✅ R1-REAL Broker Observation Driver: Dual-channel observation (SSE Primary + REST Polling Recovery), strict BMAP-07 cancellation reconciliation, fail-closed timeout to `UNKNOWN`, and live quote benchmark derivation.
- ✅ **First Accepted Paper Evidence Checkpoint (P-001):**
  - Order 003 (`acash-r1-paper-20260901-003`, Broker UUID `99a989f8-969d-4640-9598-4d8a3911a1d7`).
  - Terminal `FILLED`, 1 share SPY @ `765.26` (Benchmark Mid `765.24`, Slippage `+0.2614 bps`).
  - Strict Conjunctive P Audit **PASSED** (TerminalVerified, EvidenceLineageComplete, ReconciliationVerified, NoDispute, BrokerSnapshotBound).
  - **Status:** $$\boxed{P = 1}$$

### Tri-Partite Evidence Architecture ($\text{Unit Tests} \neq E \neq P$)
- **Local Unit Tests:** 610/610 tests passing (100% clean implementation & invariant verification).
- **E (Broker Semantic Evidence):** Independently verified against Alpaca API/documentation.
- **P (Paper Runtime Observation):** **P = 1** (Checkpoint `P-001` officially accepted).

$$\boxed{\text{610 Unit Tests} \land E \text{ (Broker Semantic Review)} \land P \text{ (Empirical Paper Execution P-001)} \implies \text{Gate 7 PASSED}}$$

### Paper Order Forensic History
- `acash-r1-paper-20260831-001`: Real Paper POST succeeded $\to$ rested in `accepted` $\to$ verified `CANCELED` via REST ($P = 0$).
- `acash-r1-paper-20260831-002`: Real Paper POST succeeded $\to$ filled post-session $\to$ flattened via incident cleanup ($P = 0$).
- `acash-r1-paper-20260901-003` (**P-001**): Real Paper POST $\to$ real-time fill observed @ 765.26 $\to$ parity verified ($\mathbf{P = 1}$).

### Next milestones
- ⏳ Operational cleanup of +1 SPY paper position (isolated operational step, distinct from P-001).
- ⏳ Phase 8: Portfolio Engine (skfolio vs transparent baselines) ── Gate 8.
- ⏳ Phases 9–16: Risk/Kill Switch, friction, Paper subsystem, MT5 adapters, Live
  (MANDATORY HUMAN APPROVAL), AI research layer, strategy lifecycle, flywheel.
- ❌ **Live readiness is NOT implied anywhere in this phase.** Phase 13 gate
  requires explicit human approval.

---

## Detailed Phase Breakdown

### ✅ Phase 0: Discovery & Architecture [COMPLETED - PASSED]
- **Objective:** Evaluate technologies, define domain architecture, produce ADRs, risk register, and establish project boundaries.
- **Deliverables:** Complete documentation suite in `docs/`.
- **Gate 0 Criteria:** Technology candidate matrix approved; architecture review signed off; Phase 1 implementation plan approved.

---

### ✅ Phase 1: Foundation & Domain Core [COMPLETED - PASSED]
- **Objective:** Establish the modular monolith structure, domain types, abstract interfaces, configuration management, structured logging, in-memory mock adapters, and correctness test harness.
- **Deliverables:**
  - Python project environment (`pyproject.toml`, virtual environment).
  - Core domain models (`Instrument`, `Bar`, `MarketDataSnapshot`, `Signal`, `TargetAllocation`, `RiskAssessment`, `Order`, `Fill`).
  - Core interface definitions (`IMarketDataProvider`, `IFeatureEngine`, `IStrategy`, `IPortfolioOptimizer`, `IRiskEngine`, `IBacktestEngine`, `IExecutionEngine`, `IDecisionLedger`).
  - Mock in-memory execution engine and market data provider for unit testing.
  - Structured JSON logger and typed configuration loader (`Pydantic` + `YAML`).
  - Unit and contract test suite verifying domain invariants, invalid states, interface contracts, serialization, and deterministic equivalent outcomes.
- **Gate 1 Criteria:** All unit tests pass (27/27); domain invariants verified; typing strictly enforced (`mypy` clean); zero live broker or Nautilus dependencies in core.

---

### ✅ Phase 2: Data Ingestion & Integrity Engine [COMPLETED - PASSED]
- **Objective:** Implement reliable ingestion for **one market** and **one primary data source** with strict point-in-time validation.
- **Deliverables:**
  - Ingestion adapter (`yfinance` research adapter / local Parquet for single liquid symbol).
  - Normalization pipeline with timestamp timezone enforcement (UTC only) and sequencing verification.
  - Automated data integrity checker (detects missing timestamps, impossible negative prices, duplicates, unit errors).
  - Provenance tracker recording dataset hash and retrieval metadata.
  - Recoverable Batch Commit Protocol (`PREPARED` $\to$ `PART_PUBLISHED` $\to$ `COMMITTED`).
  - DuckDB Point-in-Time qualification layer with multi-source isolation and lookahead prevention.
- **Gate 2 Criteria:** Data validation suite catches 100% of synthetic data corruption test cases (57/57 tests pass, `mypy` clean).

---

### ✅ Phase 3: Point-in-Time Feature Engine (3A/3B/3C) [COMPLETED - PASSED]
- **Objective:** Build modular, deterministic feature calculations with zero look-ahead bias across Trades, Order Book, and Microstructure.
- **Deliverables:**
  - **Phase 3A:** Canonical Trades Domain (Time & Sales, Aggressor Side flags, length-prefixed hashing).
  - **Phase 3B:** Canonical Order Book (L2 Depth Multi-Row Frames & Deltas, L3 MBO, deterministic 5-tuple order).
  - **Phase 3C:** Microstructure Feature Engine (Session VWAP, Volume Profile with POC lower-price tie-breakers, Value Area 70% bounds, Footprint Analytics, Depth-Weighted Micro-Price).
  - Dual-temporal point-in-time filtering ($T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$).
- **Gate 3 Criteria:** Automated leakage unit tests verify zero future bar indexing; 122/122 tests pass, `mypy` clean.

---

### ✅ Phase 4: Alpha Research Engine & Baseline Hypotheses [COMPLETED - PASSED]
- **Objective:** Implement formal hypothesis registration, econometric OLS slope Beta HAC inference under Bartlett kernel, discrete forward returns, interval-based purging/embargo, and durable Blind OOS governance.
- **Deliverables:**
  - Hypothesis specification schema (`HypothesisSpecification`, `InvalidationCriteria`, parameter spaces).
  - Discrete bar-indexed forward returns ($R(t,H)$) with next-bar open entry alignment.
  - Econometric OLS slope $\hat{\beta}_H$ inference with Newey-West HAC covariance under Bartlett kernel.
  - Descriptive non-parametric association metrics: Pearson IC, Spearman Rank IC (fractional ties), autocorrelation.
  - 3-tier friction waterfall (Raw Edge $\to$ Net Edge $\to$ Economic Edge).
  - Interval-based boundary purging and unallocated embargo gaps ($\ge \max(H)$ bars).
  - Durable Blind OOS Governance Ledger (`data/manifests/research/governance_ledger.json`) with strict re-tuning locks (`UNEXPOSED` $\to$ `EVALUATED_LOCKED` $\to$ `EXHAUSTED`).
  - Baseline research models: Microstructure Imbalance Skew, VWAP Mean Reversion, Multi-Horizon Momentum.
- **Gate 4 Criteria:** Strategies generate reproducible signals on historical data without look-ahead errors; 139/139 unit tests pass, `mypy` clean.

---

### ✅ Phase 5: Backtesting Substrate & Simulation Engine [COMPLETED - PASSED]
- **Objective:** Establish the deterministic event-driven simulation backtest substrate preserving ACASH as the single source of truth for canonical data, features, accounting, and manifests.
- **Deliverables:**
  - Event-driven backtesting execution substrate with full simulated order lifecycle state machine.
  - Canonical Data Adapter with Phase 3B total ordering 5-tuple contract: $(T_{\text{event\_utc}}, \text{source\_order\_key}, \text{message\_rank}, \text{stream\_id}, \text{row\_sub\_index})$.
  - Realistic friction simulation (maker/taker fee tiers, bid/ask spread, fixed & dynamic slippage, causal dual-sided latency).
  - Independent double-entry shadow ledger decoupling Balance-Sheet View from Performance Attribution View ($|\text{AccountingResidual}| \le 10^{-10}$).
  - Deterministic content-derived `BacktestManifest` identity: $\text{manifest\_id} = \text{SHA256}(\text{canonical}(\text{hypothesis\_hash} + \text{data\_hashes} + \text{engine\_hash} + \text{strategy\_hash} + \text{seed}))[:32]$.
  - Reality Gap Telemetry Engine implementing disjoint non-overlapping reference-price decomposition: Spread Drag, Slippage Drag, Latency Drag, Fee Drag, Maker Adverse Selection Drag, and Unmodelled Residual.
  - Baseline strategy actors: Microstructure Imbalance (OBI) & Session VWAP Mean Reversion.
- **Gate 5 Criteria:** Bitwise-identical replay across identical inputs/configs, exact double-entry cash conservation, unmocked NautilusTrader integration, and zero phantom liquidity; 200/200 tests pass, `mypy` clean.



---

### ✅ Phase 6: Statistical Validation & Overfitting Controls [COMPLETED - PASSED]

- **Objective:** Enforce quantitative validation gates to eliminate data-snooping, selection bias, and backtest overfitting.
- **Deliverables:**
  - Combinatorial Purged Cross-Validation (CPCV) engine with contiguous $N$-group partitioning, exhaustive $\binom{N}{k}$ combinations, strict $[t+1, t+H]$ interval purging, post-test embargo buffers, and continuous pseudo-OOS path reconstruction ($\phi = \frac{k}{N}\binom{N}{k}$).
  - Deflated Sharpe Ratio (DSR) & Minimum Track Record Length (MinTRL) engine implementing Bailey & López de Prado (2014) non-normal asymptotic inference with Euler-Mascheroni constant $\gamma_E$, empirical trial variance $V$, Fisher-Pearson skewness $g_1$, and Pearson kurtosis $g_2$.
  - Multiple-testing accounting: Holm-Bonferroni step-down (FWER), Benjamini-Hochberg (FDR), and Harvey-Liu-Zhu (2016) Haircut Sharpe Ratio.
  - Probability of Backtest Overfitting (PBO) log-odds evaluation and parameter surface curvature / fragility testing across mandatory $\pm 25\%$ parameter grids.
  - Sovereign `StatisticalValidationGate` orchestrating multi-gate sequential evaluation, authoritative $K_{\text{ledger}} \equiv K_{\text{DSR}} \equiv K_{\text{Holm}} \equiv K_{\text{BH}}$ trial coupling, fail-closed missing data defense, and emitting immutable `ValidationReport` certificates with dual cryptographic lineage digests.
- **Gate 6 Criteria:** Strategies must satisfy DSR $\ge 0.95$, MinTRL, Holm-Bonferroni FWER significance, PBO $< 0.25$, flat parameter curvature, analytical friction monotonicity, and sealed OOS performance retention ($\text{SR}_{\text{OOS}} \ge 0.50 \cdot \text{SR}_{\text{IS}}$); 252/252 tests pass, `mypy` clean.

---

### 🟡 Phase 7: Live Execution & Broker Mapping [IN PROGRESS]
- **Specification & Evolution Proposal:** [`docs/phase7/phase_7_proposal.md`](phase7/phase_7_proposal.md)
- **Objective:** Build the sovereign execution stack from authorization/admission
  through broker-neutral semantic mapping to a concrete Alpaca Paper integration,
  and exercise a real (Paper) order lifecycle.
- **Explicit Paper-before-Live Execution Sequence:**
  $$\text{Phase 7 Implementation} \to \text{R0 (Read-Only)} \to \text{R1 (Lifecycle Harness)} \to \text{Security Preflight} \to \text{Paper Exercise} \to \text{P Evidence} \to \text{Readiness Review} \to \text{Live Authorization Hard-Lock}$$
- **Completed (LOCKED / E-reviewed — 588 tests passing):**
  - Admission/Authorization gate, Step 8 Execution Contract, Step 8B State
    Machine, Step 8C Broker Event Normalizer, Step 8D Mock Broker, Step 8E
    Execution Coordinator & Reconciliation Boundary, Operational Restriction,
    Real Broker Contract.
  - Vendor-Agnostic Broker Semantic Mapping Framework + Alpaca Concrete BMAP:
    `BMAP 01–10 = E`, `BMAP 11 = E*`, `BMAP 12 = D`.
  - Concrete Alpaca Paper Transport (`PaperHttpAlpacaTransport`), Paper
    Credential Boundary (venue-pinned `ALPACA_PAPER`), `AlpacaPaperAdapter`.
  - Local Windows User Vault & Launcher: `scripts/setup_paper_credentials.ps1` (DPAPI/SecretStore) and `scripts/run_paper.ps1` (Paper-only child process injection).
  - R0 read-only Paper Exercise harness; R1 order-lifecycle exercise harness
    (`run_order_exercise_verification`); R1 contract frozen.
  - R1 entry-point fixes: `4a92348` connect-before-submit; `8e92188` paper-only
    transport injection guard.
- **Evidence Model ($\text{Unit Tests} \neq E \neq P$):**
  - **Local Unit Tests:** 588/588 unit tests passing (automated regression & invariant protection).
  - **`D` (Design-Conformant):** Specification and schema match the canonical domain contracts.
  - **`E` (Broker Semantic Review):** Broker semantic mapping verified against official vendor documentation (`01–10 E`, `11 E*`, `12 D`).
  - **`E*` (Partially Bounded):** Bounded behavior with known vendor API caveats (e.g. BMAP-11 SSE replay gaps).
  - **`P` (Empirically Proven):** Real execution observed against live Paper venue satisfying full cryptographic lineage ($P = 0$).
  - $$\boxed{\text{588 Unit Tests} \neq E \text{ (Broker Semantic Review)} \neq P \text{ (Empirical Paper Execution)}}$$
- **Current milestone (in progress):** final Paper preflight via `run_paper.ps1 -PreflightOnly` → authorized single Paper run → first **P** evidence.
- **Blockers & Resolution Workflow:**
  1. Interactive local credential entry via `.\scripts\setup_paper_credentials.ps1` into Windows User Vault (DPAPI / SecretStore) outside Git.
  2. Safe preflight check via `.\scripts\run_paper.ps1 -PreflightOnly` (`ALPACA_PAPER` provider, `CREDENTIALS_LOADED=True`, `paper-api.alpaca.markets/v2` endpoint).
  3. Real Paper run is **NO-GO** until operator green-lights after a passing final preflight.
- **Approved run parameters (single order):** `SPY` / `quantity=1` /
  `client_order_id=acash-r1-paper-20260831-001`.
- **P acceptance (conjunctive — ALL must hold):**
  $$\text{P} = \text{TerminalVerified} \land \text{EvidenceLineageComplete} \land \text{ReconciliationVerified} \land \text{NoDispute}$$
  $E \neq P$; HTTP-success $\neq P$; FILLED alone $\neq P$; unit tests $\neq P$.
- **Gate 7 Criteria (design intent):** verified real Paper order-lifecycle
  evidence (P) through the canonical authority pipeline (`AlpacaPaperAdapter` →
  `normalize_broker_event()` → `to_coordinator_event()` →
  `ExecutionCoordinator.apply()/reconcile()` → `transition_order()`).
  (Original Regime-Engine content deferred to a later phase.)

---

### ✅ Phase 8: Portfolio Engine (Native Optimizers, Baselines & Governance) [COMPLETED & FROZEN]
- **Objective:** Allocate capital across candidate assets/signals and cash ("NOWHERE").
- **Deliverables:**
  - Transparent Baseline Allocators: Equal Weight (1/N), Inverse Volatility (1/$\sigma$), 100% Cash (`CashAllocator`, `EqualWeightAllocator`, `InverseVolatilityAllocator`).
  - Native Portfolio Optimizers: Hierarchical Risk Parity (HRP) and Equal Risk Contribution (ERC) with zero-leakage out-of-sample tournament (`AllocationTournamentRunner`).
  - Optional Adapters: `skfolio` and `cvxpy` adapters with graceful degradation when optional packages are not installed in clean core.
  - Sovereign Governance Gate: If net expected return fails risk-free rate + hurdle margin, sovereignly allocate 100% Cash via `GOVERNANCE_FALLBACK`.
- **Gate 8 Criteria:** Fully audited out-of-sample tournament (`Gate 8 Native Allocation Tournament`); Candidate $\neq$ Evaluation $\neq$ Decision; Ranking $\neq$ Approval; Policy-estimated friction (12 bps); Max Drawdown evaluated on net equity path. Commit: `e6f1d04`.

---

### ✅ Phase 8.5: Alpha Research & Economic Evidence Engine [COMPLETED & FROZEN]
- **Objective:** Establish formal alpha qualification, research lineage DTOs, and multi-horizon falsification hurdles with zero trading authority.
- **Deliverables:**
  - `AlphaQualificationDossier` and `AlphaEconomicDecomposition` DTOs enforcing $Net = Gross - Friction$.
  - Formal multi-hurdle qualification gate (`AlphaQualificationGate`) requiring positive net edge, Holm-Bonferroni FWER significance, and zero rebate-inflated edge.
  - Explicit forward lifecycle state machine (`HYPOTHESIS` $\to$ `CANDIDATE` $\to$ `RESEARCH_QUALIFIED` $\to$ `RETIRED_STRUCTURAL_BREAK`).
  - Strict boundary: $CapitalAuthorityUSD \equiv 0.00$.
- **Gate 8.5 Criteria:** 100% passing tests across 6 slices; cryptographic SHA-256 DAG binding hypothesis, trial ledger, and validation reports. Commit: `9ce1365`.

---

### ✅ Phase 9: Deterministic Risk Engine & Sovereign Kill Switch [COMPLETED & FROZEN]
- **Objective:** Implement non-negotiable sovereign risk boundaries that overrule all upstream models.
- **Deliverables:**
  - `DeterministicRiskEngine` realizing `IRiskEngine` with multi-tier boundary evaluation (gross leverage, asset concentration, mandatory cash floor, drawdown, daily loss).
  - `DeriskEngine` implementing proven monotonic `EXACT_SCALE_DOWN` derisking and `BINARY_REJECT`.
  - `SovereignKillSwitchController` with append-only disk persistence, crash/restart recovery in `PERSISTENTLY_BLOCKED`, and multi-sig `Ed25519TrustStore` quorum reset verification.
  - `EmergencyFlattenGenerator` emitting zero-target liquidation intents ($q_{\text{target}} \equiv 0.0, \Delta q_i = -q_i$) and `EmergencyFlattenTracker` evaluating completion strictly against Phase 7 broker reconciliation.
  - `RiskStateBridge` ensuring type-safe, loss-bounded conversions across `PortfolioState`, `RiskSnapshot`, `CandidateRiskAllocation`, and `RiskState`.
- **Gate 9 Criteria:** 100% passing rate on 70 unit and integration tests; strict fail-closed contract; zero direct broker execution authority in Phase 9. Commit: `6bd40d8`.

---

### ✅ Phase 10: Runtime Orchestration & Continuous Paper Operations [COMPLETED & FROZEN]
- **Objective:** Establish the 5-stage authoritative runtime supervisor, operational scheduler, and append-only event ledger for continuous paper operations.
- **Deliverables:**
  - `RuntimeSupervisor`: 5-stage fail-closed pipeline orchestrator ($\text{Data} \to \text{Census} \to \text{Tournament} \to \text{Risk} \to \text{Admission}$).
  - `OperationalScheduler`: Dual-clock discipline ($as\_of\_utc \neq wall\_clock\_utc$), cadence evaluation, and concurrency lockout.
  - `OperationalLedger`: Append-only SHA-256 chained disk ledger (`OperationalCycleEvent`) with replay and tampering verification.
  - `ContinuousPaperDaemon`: Long-running paper harness loop with pre-flight fail-closed ledger checks and zero live capital authority.
- **Gate 10 Criteria:** 904 repository tests passing; full cross-phase integration suite; zero direct broker sockets in runtime layer. Commit: `3955bf6`.

---

### ✅ Phase 11: Forward Tracking, Online Drift Detection & Execution Reality Attribution [APPROVED & FROZEN]
- **Objective:** Provide an independent observational and evidence plane to monitor forward strategy decay and attribute realized execution drag from Phase 7 fills without mutating historical research or overwriting allocation policies.
- **Pre-Phase-11 Architecture Hygiene:** Source-of-truth documentation synchronized (`docs/architecture/system_architecture.md`), dual-clock determinism verified (`Supervisor cycle => explicit as_of_utc`), one-way Decimal precision boundary established, and 3-tier hashing authority classified.
- **Deliverables (Contract v1.1):**
  - **Track A (Strategy Drift):** `ForwardObservation`, `ForwardWindowMetrics`, `ForwardHealthPolicy` (with anti-whipsaw hysteresis $N_{\text{degrade}}, M_{\text{recover}}, T_{\text{cooldown}}$), `ForwardHealthState`, `ForwardGovernanceRecommendation`, `StrategyForwardDriftEvidence`.
  - **Track B (Execution Reality):** `ExecutionObservation`, `RealizedExecutionDrag` (explicit signed conventions: gross drag $\ge 0$, net realized drag = gross - rebate), `ExecutionAttributionPolicy`, `ExecutionCostEvidence` (with sample count, coverage ratio, and confidence interval metadata).
  - **Track C (Ingestion & Forensic Persistence):** `ForwardTelemetryIngestor` with decoupled Stream Integrity Plane (`VALID` $\leftrightarrow$ `BLOCKED`) vs Strategy Health Plane, explicit `reinitialize_stream()` epoch recovery without backfilling gaps, and `MonitoringEvidenceLedger` adapting Phase 10 `OperationalLedger`.
  - **Core Invariants:**
    - $\text{Historical Research Qualification } (\text{Phase 8.5}) \neq \text{Current Forward Health } (\text{Phase 11})$.
    - $\text{Detection } \neq \text{Governance } \neq \text{Eligibility}$ (Phase 11 recommends; Phase 10 Stage 2 Census decides).
    - $\text{No Evidence } \neq \text{Negative Evidence}$ (telemetry disruption $\implies \text{MONITORING\_BLOCKED}$, not strategy decay).
    - $\text{Zero Decimal } \to \text{float } \to \text{Decimal in Evidence Generation}$.
    - $\text{Tier 1 CanonicalConfigSerializer Authority for all Evidence Digests}$.
    - $\text{Taker-Only Execution Scope Guard in v1 (Maker execution strictly rejected fail-closed)}$.
- **Gate 11 Criteria:** 1,020 collected tests (1,017 passed, 3 skipped, 0 failed); 26/26 Red-Team Adversarial Vectors PASSED; 9/9 Cross-Phase Integration Tests PASSED; 107/107 Monitoring Unit Tests PASSED; MyPy 0 errors across 40 files; Git clean with zero modifications to Phases 1–10. Commit: `092a2b1`.
- **Release Caveats:**
  1. Authority decoupling ("no authority creep") is verified against current implementation behaviors and structural interfaces rather than an eternal mathematical impossibility against future arbitrary modification.
  2. Remote CI was not independently available/executed in this environment; all release guarantees are fully verified on local canonical execution.

---

### ✅ Phase 12: MT5 & Venue Execution Adapters [COMPLETED & FROZEN — `1e1d154`]
- **Objective:** Build thin, secure broker connectivity adapters with authoritative 6-D reconciliation.
- **Deliverables:**
  - **Slice 1:** MT5 Domain Schemas, Enums & Broker Mapping (BMAP-MT5)
  - **Slice 2:** `BrokerSymbolSpec` — Immutable instrument spec, Decimal volume quantization, tick-grid price alignment
  - **Slice 3:** MT5 Terminal Driver & IPC Transport Bridge (Windows Local `NativeMT5Transport`)
  - **Slice 4:** `MT5BrokerAdapter` & Authoritative 6-Dimensional Reconciliation Engine
  - **RECON-6D Rev1–7:** Reconciliation remediation (R4-FIX through R7-FIX, all fail-closed). Commit: `44202fe`
  - **Slice 5:** Execution Lifecycle Integration — `intent_id` as exclusive Gate 6 routing key; Two-Phase preflight atomicity routing (Phase A: duplicate/lineage/coordinator validation; Phase B: evidence delivery). Commit: `1e1d154`
  - **Slice 6 (Freeze):** Architecture conformance audit, safety gate verification, frozen contract inventory, TradingView deferred backlog. See: `docs/phase12/closeout_report.md`
- **Frozen Contracts:** `transition_order()` sole authority; `intent_id` sole routing key; `can_dispatch()` gate; UNKNOWN semantics; ACK≠FILLED; BLOCKED absorbing; $0.00 live capital
- **Deferred:** TradingView Ingress Gateway (signal ingress — separate independent backlog item; does NOT gate Phase 13)
- **Gate 12 Criteria Met:** 1240/1240 tests passed (1158 unit + 82 integration); MyPy 0 errors in 263 files; Architecture conformance audit passed; Full frozen contract inventory documented. Commit: `1e1d154`.

---

### ⏳ Phase 13: Live Small Capital Deployment [SLICE 1 GATE A CERTIFIED]
- **Objective:** Real-world execution validation with micro-capital.
- **Progress:**
  - **Slice 1 (Gate A Pre-Live Certification):** `✅ CERTIFIED` (Formal Human Sign-Off on 2026-09-04; A-1 through A-11 PASS; B-1/B-2 CLOSED; 0 Active Blockers; Demo `112040157` 100% Flat; Live Capital $0.00). See [`docs/phase13/consolidated_gate_a_audit.md`](phase13/consolidated_gate_a_audit.md).
  - **Gate B Status:** `🔒 STRICTLY LOCKED` ($0.00 Live Capital Authority).
- **Deliverables:**
  - Live execution harness with minimum position sizes (micro-lots).
  - Live telemetry dashboard and real-time risk monitor.
  - Reconciliation between expected vs broker execution prices.
- **Gate 13 Criteria:** **EXPLICIT HUMAN APPROVAL REQUIRED (Section 37)**; all safety gates, kill switches, and alerts verified operational.
- **Multi-Broker / Multi-Asset Roadmap (ADR-021):** While Phase 13 currently executes against the active MetaQuotes MT5 Demo baseline under Gate A, the long-term architecture is established as Asset-Agnostic and Multi-Venue (Pepperstone MT5 candidate, Alpaca US Equities/ETF candidate, OANDA API candidate, IBKR multi-asset candidate). See [`docs/architecture/multi_broker_multi_asset_decision.md`](architecture/multi_broker_multi_asset_decision.md).

---

### ⏳ Phase 14: AI Quantitative Research Layer [UPCOMING]
- **Objective:** Augment quant research with AI-driven hypothesis generation and reporting.
- **Deliverables:**
  - LLM hypothesis formulation assistant (`acash.research.ai`).
  - Automated research report generator conforming to Section 33.
  - Exploratory feature discovery tools.
- **Gate 14 Criteria:** AI outputs are treated strictly as unvalidated proposals; must pass full backtesting and statistical validation gates.

---

### ⏳ Phase 15: Strategy Lifecycle Management & Phase 16: Performance Degradation (Harmonized)
- **Harmonization Notice:** The early conceptual drafts of Phase 15 (Strategy Lifecycle Management) and Phase 16 (Performance Degradation & Memory Flywheel) have been formally extracted, preserved, and structured into the institutional **Phase 17–22 Architecture Sequence** (ADR-023).
  - *Lifecycle State Machine & Rolling Monitors:* Merged into **Phase 17** (`StrategyAdmissionStatus` + `StrategyLifecycleState` + Gate 9).
  - *Statistical Degradation Detection:* Preserved in **Phase 17** Gate 9 and Phase 11 `ForwardTelemetryIngestor`.
  - *Decision Outcome Recording & Memory Ledger:* Deferred to **Phase 20** (Strategy Selection) and **Phase 22** (Organizational Memory Ledger).
  - *Zero Requirements Deleted:* Complete traceability preserved in [`docs/architecture/strategy_admission_standard.md`](architecture/strategy_admission_standard.md).

---

### ✅ Phase 17: Strategy Admission Standard & Regime-Aware Capital Allocation Framework [SPECIFIED — ADR-023]
- **Objective:** Institutional governance foundation establishing the mandatory gateway before any strategy may enter the catalog or receive capital.
- **Deliverables:**
  - 11-Gate Admission Standard (Gate 0–10) incorporating the 20 Mandatory Admission Questions.
  - Epistemic Identity: $\text{Observed Profit} \neq \text{Proven Skill} \neq \text{Structural Edge} \neq \text{Luck-Free Performance}$.
  - Performance Attribution across 5 sources (Skill, Structural Edge, Beta/Factor, Regime Tailwind, Luck).
  - Multi-dimensional `SkillEvidence` vector DTO using `EvidenceSupportLevel` (scalar composite scores strictly forbidden).
  - `AlternativeExplanationRegister` tracking counter-hypotheses (Market Beta, Short Vol, Regime Tailwind, Selection Bias, Execution Fantasy).
  - `EffectiveEvidenceSample` ($N_{\text{eff}}$) with declared dependency assumptions (rejection of raw trade count & calendar duration as sole evidence).
  - Quant Candlestick Architecture: `PriceStructureMeasurements` (returns, range/ATR, body/range, wick asymmetry, close location, gap) feeding continuous `MarketStateVector`.
  - Decoupled `VolumeType` (`TICK_VOLUME`, `REAL_VOLUME`, `EXCHANGE_VOLUME`, `UNKNOWN`).
  - Decoupled `StrategyMechanism` (market interaction) vs `StrategyStyle` (behavioral style).
  - Bounded Capital Allocation contracts enforcing the core invariant: **`allocation = $0.00` is always valid and default**.
- **Governance:** Live capital remains hard-locked at $0.00; zero broker mutations; optimization solvers deferred to Phase 21; live regime engine deferred to Phase 19.

---

### ⏳ Phase 18: Strategy Research & Tournament Pipeline [UPCOMING]
- **Objective:** Automated, reproducible research execution, hypothesis evaluation, and fair tournament ranking with frozen prior criteria and winner's curse discounting.

---

### ⏳ Phase 19: Empirical Regime Detection Engine [UPCOMING]
- **Objective:** Empirical estimation and online classification of market states (orthogonal trend, volatility, liquidity, spread, and microstructure dimensions) with probabilistic confidence.

---

### ⏳ Phase 20: Regime × Strategy Selection & Decision Engine [UPCOMING]
- **Objective:** Dynamic strategy eligibility gating, state compatibility matching, and multi-horizon decision memory recording.

---

### ⏳ Phase 21: Risk-Based Capital Allocation Solvers [UPCOMING]
- **Objective:** Production mathematical solvers (Equal Risk Contribution, Volatility Targeting, Haircut Optimization) adhering to Phase 17 `IAllocationPolicy` and safety bounds.

---

### ⏳ Phase 22: Portfolio / Multi-Strategy Orchestration & Memory Flywheel [UPCOMING]
- **Objective:** Enterprise multi-strategy execution orchestration, aggregate exposure netting, cross-strategy margin monitoring, and long-term organizational decision memory ledger.

---

## Reality Gap Analysis & Execution Deviation

The core empirical objective of ACASH is measuring:
> *"How much does what we expected in simulation diverge from what actually happened in the live market?"*

```
                 BACKTEST SIMULATION
                          │
                          ▼
                 PAPER / SHADOW TRADING
                          │
                          ▼
                    LIVE EXECUTION
                          │
                          ▼
               REALITY GAP ATTRIBUTION
```

### Multi-Phase Reality Pipeline:
- **Phase 2+ (Data Quality):** Data fidelity matching strategy horizon, timestamp integrity, provenance, spread capture.
- **Phase 5+ (Backtest):** Tick-aware simulation, data-supported spread fidelity, graduated slippage models (simple $\to$ calibrated $\to$ liquidity-aware).
- **Phase 6+ (Validation):** OOS, walk-forward matrix, forward testing, stress testing, regime analysis.
- **Phase 12+ (Live):** Actual fills, realized spreads, actual slippage, latency, broker reconciliation.
- **Phase 13+ (Reality Gap Attribution):** Systematic deviation tracking attributed to: Data error, Model/alpha error, Execution error, or Venue conditions.

### Deviation Metrics & Example:
| Metric | Expected (Simulation) | Actual (Live) | Reality Gap Deviation |
| :--- | :--- | :--- | :--- |
| **Entry Price** | 100.00 | 100.07 | **+7 bps** |
| **Prevailing Spread** | 2 bps | 9 bps | **+7 bps** |
| **Execution Slippage** | 1 bp | 6 bps | **+5 bps** |
| **Trade PnL** | +$240 | +$181 | **-24.6%** |
| **Roundtrip Latency** | 15 ms | 120 ms | **+105 ms** |

---

## License Notice

**Copyright © 2026 Ratthabhumi & ACASH Contributors. All Rights Reserved.**  
Proprietary and Confidential. Unauthorized copying, distribution, modification, or extraction is strictly prohibited.
