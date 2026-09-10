# ACASH — System Development Roadmap (Phases 0–16)

**Document:** `docs/ROADMAP.md`  
**Version:** 3.5.0  
**Date:** 2026-09-10  
**Governance Principle:** Sequential Phase Progression. No phase skipping. Every phase has explicit gates, acceptance criteria, and human approval checkpoints.

> **Note on Phase 7 scope:** This roadmap's original nominal title for Phase 7
> was "Regime Engine (Trend/Vol Classifiers)". The **actual** Phase 7 work being
> executed in this repository is **Live Execution & Broker Mapping** (Admission →
> Step 8 Contracts → Broker Semantic Mapping → Alpaca Paper exercise). The
> Regime-Engine content is deferred; Phase 7 below reflects the real scope.

---

## ACASH CURRENT NORTH-STAR (2026-09-10)

**North Star.** Under strict scientific governance, answer *"where should capital be allocated?"* — including the valid governed answer **NOWHERE** — by progressing the Phase 14 research lanes (mainline `CAND-FREE-MACRO-001`, parallel `MEC-0011`) to a single canonical frozen pre-registration, then explicit Human authorization, then empirical validation and qualification. All trading / capital / broker authority remains **STRICTLY LOCKED** throughout.

```
CURRENT WORKING MILESTONE (replaces the older "Phase 13 Step 5 soak ACTIVE" framing;
Phase 13 Steps 1-7 are certified; Step 8 LOCKED; Step 9 NOT AUTHORIZED):

  MAINLINE .... CAND-FREE-MACRO-001    FREEDATA research lane; CONDITIONALLY READY;
                                       human binding Rounds 0-3B recorded (K = 3);
                                       S-2 / S-7 (T_eff formula) / S-9 OPEN;
                                       PRE-REGISTRATION NOT FULLY FROZEN;
                                       EMPIRICAL VALIDATION NOT AUTHORIZED
  PARALLEL .... MEC-0011                Gold/DXY relative-movement; RESEARCH INTAKE ONLY;
                                       D1=A / D2=C / D3=B human-ratified 2026-09-10;
                                       DXY source layer BLOCKED (paths P1-P5 await Human);
                                       NOT AUTHORIZED FOR EMPIRICAL VALIDATION
  PARKED ...... F-1 CAND-FLOW-CALENDAR-REBALANCE-001   NOT READY / CONDITIONAL at $0;
                                       PENDING HUMAN RATIFICATION
  LOCKED ...... HYP_003 (NOT CREATED) / R1 (NOT AUTHORIZED) / empirical validation /
               backtest / trading (LOCKED) / capital ($0.00) / broker (DISCONNECTED) /
               quarantined HYP_001/HYP_002 data spans (PRISTINE / NOT REUSABLE BY DEFAULT)
```

### State Register (authoritative boundaries, verified 2026-09-10)

| Class | Lane / Item | State |
|---|---|---|
| CURRENT | `CAND-FREE-MACRO-001` (mainline) | `CONDITIONALLY READY`; Human binding Rounds 0-3B recorded (K = 3); **S-2, S-7 T_eff formula, S-9 = HUMAN DECISION REQUIRED**; PRE-REGISTRATION **NOT FULLY FROZEN**; EMPIRICAL VALIDATION **NOT AUTHORIZED** |
| PARALLEL | `MEC-0011` Gold/DXY relative movement | RESEARCH INTAKE ONLY; D1=A / D2=C / D3=B human-ratified 2026-09-10; **source layer BLOCKED** (B1 CONDITIONAL; B2/B3 BLOCKED; B4-B10 open); DXY resolution path P1-P5 awaiting Human selection; no Gold/DXY source ACCEPTED in the registry; no GLD/UUP variant may be created without explicit Human selection |
| PARKED / BLOCKED | `F-1` CAND-FLOW-CALENDAR-REBALANCE-001 | D1 final verdict **NOT READY / CONDITIONAL** (free-data feasibility not certifiable at $0); PENDING HUMAN RATIFICATION; NOT mainline; NOT HYP_003 |
| PARKED / BLOCKED | Other research directions/candidates (NY-open, prediction-market AI, session momentum, ...) | `UNVALIDATED PROPOSAL`; NOT REGISTERED; NOT SEALED; NOT HYP_003 |
| LOCKED | `HYP_003` | **NOT CREATED** (absent repo-wide) |
| LOCKED | `R1` / `ResearchReInceptionGate` | **NOT AUTHORIZED / NOT INVOKED** |
| LOCKED | Empirical validation / backtest | **NOT AUTHORIZED** for all candidates |
| LOCKED | Trading / Capital / Broker | **LOCKED / $0.00 / DISCONNECTED** (0 live orders; no live credential path) |
| LOCKED | Quarantined data | HYP_001 2026 M5 Holdout; HYP_002 H4 Validation + Blind OOS — PRISTINE / NOT REUSABLE BY DEFAULT |
| LOCKED | Phase 13 Step 8 (Human GO) / Step 9 (90-day paper) | **LOCKED / NOT AUTHORIZED** (no qualified strategy) |
| FUTURE | Phases 18-22 | UPCOMING (tournament / regime detection / selection / allocation solvers / orchestration) |

**Authorization ladder — never conflate:** `INFRASTRUCTURE READY != STRATEGY QUALIFIED != PAPER AUTHORIZED != LIVE AUTHORIZED`. Research capability != strategy qualification != execution authorization. The research lanes above are research configurations / candidates — **NOT** registered hypotheses, strategies, or tradeable configurations.

---

## ACASH NOW / NEXT / LATER (2026-09-10)

- **NOW** (binding / documentation-only; no empirical work):
  1. MACRO-001 ROUND 3B remainder — bind **S-2** (test statistic) and **S-9** (minimum sample size); pre-register the **S-7 (c) post-O-2 T_eff formula**. All three are `HUMAN DECISION REQUIRED`.
  2. MEC-0011 — Human selection among DXY-leg resolution paths **P1** (paid ICE subscription) / **P2** (authorized redistributor) / **P3** (grey private archive) / **P4** (Stooq DX.F) / **P5** (6-FX model inference); downstream blockers B4-B10 remain open.
  3. Phase 14 runtime — research-layer slices remain `UNVALIDATED PROPOSALS`; any runtime authorization stays bounded by ratified Human gate discipline (G-gates).
- **NEXT** (strict sequence; only after S-2 / S-7 / S-9 are bound):
  1. ROUND 4 — D15 OOS -> D16 Blind -> D14 IS -> D9 Cost.
  2. ROUND 5 — D19 Kill -> D20 PASS/FAIL/INVALID.
  3. Draft Freeze Candidate -> Anti-HARKing review -> Pre-registration Freeze -> Data Archive / Manifest -> **Explicit Human Authorization** -> then empirical validation / backtest.
- **LATER** (gated on a HUMAN-AUTHORIZED qualified strategy; nothing before):
  1. Phase 13 Step 8 Human GO -> Step 9 (90-day continuous paper run).
  2. Phases 18-22 upstream milestones (tournament, regime detection, selection, allocation solvers, orchestration). All currently LOCKED / NOT AUTHORIZED.

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
🟡 Phase 13: Live Small Capital Deployment ──► Gate 13 [ACTIVE — Step 5 24h Soak In Progress, Capital $0.00]
   ├─ ✅ Step 1: Implementation & Safety Envelopes [PASSED]
   ├─ ✅ Step 2: Code & Unit Audit [PASSED]
   ├─ ✅ Step 3: Integration Testing & Local Simulator [PASSED]
   ├─ ✅ Step 4: Restart, Recovery & Rehydration [PASSED]
   ├─ 🟡 Step 5: 24-Hour Unattended Soak Test [ACTIVE / IN PROGRESS]
   ├─ 🔒 Step 6: Telemetry, Reconciliation & Forensic Audit [LOCKED]
   ├─ 🔒 Step 7: Continuous Paper Readiness Certification [LOCKED]
   ├─ 🔒 Step 8: Explicit Human GO Checkpoint [LOCKED]
   └─ 🔒 Step 9: 90-Day Continuous Paper Forward Run [LOCKED]
   │
   ▼
📐 Phase 14: AI Quantitative Research Layer ──► Gate 14 [PLAN APPROVED AT PLAN LEVEL — IMPLEMENTATION LOCKED]
   │
   ▼
⏳ Phase 15: Strategy Lifecycle Management [HARMONIZED INTO PHASE 17]
   │
   ▼
⏳ Phase 16: Performance Degradation & Data Flywheel [HARMONIZED INTO PHASE 17–22]
   │
   ▼
✅ Phase 17: Strategy Admission Standard & Regime-Aware Capital Allocation Framework [SPECIFIED — ADR-023]
   │
   ▼
⏳ Phase 18: Strategy Research & Tournament Pipeline [UPCOMING]
   │
   ▼
⏳ Phase 19: Empirical Regime Detection Engine [UPCOMING]
   │
   ▼
⏳ Phase 20: Regime × Strategy Selection & Decision Engine [UPCOMING]
   │
   ▼
⏳ Phase 21: Risk-Based Capital Allocation Solvers [UPCOMING]
   │
   ▼
⏳ Phase 22: Portfolio / Multi-Strategy Orchestration & Memory Flywheel [UPCOMING]
   │
   ▼
🏛️ Phase 23: Adaptive Multi-Horizon Strategy & Microstructure Architecture [ARCHITECTURAL RECORD — ADR-024/025]
```

---

## CURRENT STATE / NEXT STEP (Reconciliated 2026-09-10)

> **Current Repository Milestone:** Phase 14 Governance + Research Lanes (CAND-FREE-MACRO-001 mainline / MEC-0011 parallel). System: **RESEARCH STANDING BY**.  
> **Historical note:** the prior framing "Phase 13 Step 5 (24-Hour Soak) ACTIVE / IN PROGRESS under PID 41844, launched 2026-09-05T10:20:43Z" is a completed historical/snapshot event — Phase 13 Step 5 is VERIFIED COMPLETED (see Phase 13 detail below). Potentially obsolete section found — preserved intentionally.  
> **Live Capital Authority:** Strictly **$0.00 (Hard-Locked)**. Live Orders: **0**. Broker: **DISCONNECTED**.  

### Current Canonical Execution State:
- ✅ **Phases 0–12:** COMPLETED & FROZEN (Gates 1–12 certified, frozen contract baseline sealed).
- ✅ **Phase 13 (Live Small Capital / Forward Paper Validation): INFRASTRUCTURE READY / STRATEGY BLOCKED**
  - ✅ **Step 1 (Implementation & Safety Envelopes):** PASSED.
  - ✅ **Step 2 (Code & Unit Audit):** PASSED.
  - ✅ **Step 3 (Integration Testing & Local Simulator):** PASSED.
  - ✅ **Step 4 (Restart, Recovery & Rehydration):** PASSED.
  - ✅ **Step 5 (24-Hour Unattended Soak Test):** **VERIFIED COMPLETED** (86,400.21s runtime, 86,085 ledger events, 8,608 telemetry records, 0 errors, graceful exit; snapshot launched 2026-09-05T10:20:43Z under PID 41844).
  - ✅ **Step 6 (Telemetry, Reconciliation & Forensic Audit):** PASS (SHA-256 chained integrity, zero gaps >15s, RSS peak 175.29 MB, pulse reconciliation 100%).
  - ✅ **Step 7 (Continuous Paper Readiness Certification):** CONDITIONALLY SATISFIED (runtime infrastructure verified ready; blocked on strategy qualification; B23.2 VM deferred).
  - 🔒 **Step 8 (Explicit Human GO Checkpoint):** STRICTLY LOCKED (no qualified strategy).
  - 🔒 **Step 9 (90-Day Continuous Paper Forward Run):** STRICTLY NOT AUTHORIZED (clock has not started; $0.00 capital authority).
- 📐 **Phase 14 (AI Quantitative Research Layer): GATE 14 ACCEPTED — RESEARCH CAPABILITY — ZERO TRADING AUTHORITY**
  - Master Research Architecture Revision 1.2 approved at plan level by Human Auditor.
  - **Gate 14 = ACCEPTED** (2026-09-08) — technical acceptance of the Phase 14 research capability (G-2 CUSTOM-2 scope). **NOT** trading, runtime, or strategy authorization.
  - Implementation slices exist in the repository as **UNVALIDATED PROPOSALS** (research-AI assistant/converter/prompts/provider; slices 1-4; D6 Option A census sealing; Phase 5 production orchestrator; D8-B release gate, Seam A identity; D5 OOS provenance with PIT lineage). Phase 13 Steps 8-9 remain independently and strictly LOCKED (Human Ratification D1-D4, 2026-09-08).
  - Zero authority to register hypotheses (HYP_003 NOT CREATED), qualify alpha, certify validation, or trade. Capital and broker execution remain completely decoupled ($0.00 / DISCONNECTED).

### Repository Synchronization State:
- **Current Branch:** `main` (HEAD == origin/main == `3bfc2e2`)
- **Documentation Synchronization Date:** 2026-09-10
- **State Source:** Canonical repository contracts (`src/acash/`), Phase 13 audit records (`docs/phase13/`), and Phase 14 governance / research records (`docs/phase14/`). Older checkpoint snapshots (`docs/SESSION_HANDOFF.md`; `docs/PROJECT_STATUS.md` dated 2026-09-04; `docs/README.md` dated 2026-09-07) are historical / checkpoint-only and may lag this file.

### Immediate Next Action:
- Bind the three open MACRO-001 ROUND 3B items (S-2 test statistic, S-9 minimum sample size, S-7 post-O-2 T_eff formula) — `HUMAN DECISION REQUIRED`.
- Continue the frozen worksheet sequence: ROUND 4 (D15 OOS -> D16 Blind -> D14 IS -> D9 Cost) -> ROUND 5 (D19 Kill -> D20 PASS/FAIL/INVALID) -> Draft Freeze -> Anti-HARKing review -> Pre-registration Freeze -> Data Archive / Manifest -> Explicit Human Authorization.
- Await Human selection of the MEC-0011 DXY-leg resolution path (P1–P5).
- No empirical work of any kind until an explicit Human authorization follows a frozen pre-registration.

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
- **Track B (Strategy Qualification Pipeline — `STRAT-MOM-MULTI-HORIZON-V1` / `HYP_TSMOM_EURUSD_001`):**
  - **Status:** `CLOSED / TERMINALLY FALSIFIED` (Option B: Early Termination executed).
  - **Lineage Audit:**
    - Step R1 (Hypothesis Pre-Registration): `✅ PASS / SEALED` (SHA-256: `5afb92d...`).
    - Step R2 (Historical Data Preparation): `✅ PASS / SEALED` (10,000 bars EURUSD M5 canonical parquet; 16/16 gates passed).
    - Step R3 (In-Sample Search Census): `✅ PASS / SEALED` (Census of 9 trials, bars 0..5,999 complete).
    - Hypothesis `HYP_TSMOM_EURUSD_001`: `❌ TERMINALLY FALSIFIED` (9/9 negative Rank IC, negative net edge after friction, HAC $t < 2.0$, autocorrelation violations).
    - Steps R4–R7: `⛔ EARLY TERMINATED` (Discontinued to preserve OOS integrity and prevent multi-testing noise).
    - OOS Holdout: `UNEXPOSED_PRISTINE` (bars 6,060..9,999 100% untouched).
  - **Strategy Authority:** `STRAT-MOM-MULTI-HORIZON-V1` permanently `NOT QUALIFIED / NOT LIVE-ELIGIBLE`. Capital authority remains `$0.00`.
  - **Governing Dossier:** [`docs/phase8.5/phase8_5_hyp_tsmom_eurusd_001_terminal_falsification_dossier.md`](phase8.5/phase8_5_hyp_tsmom_eurusd_001_terminal_falsification_dossier.md).

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

### 🟡 Phase 13: Live Small Capital Deployment [INFRASTRUCTURE READY / STRATEGY BLOCKED]
- **Objective:** Real-world execution validation with micro-capital and strict fail-closed telemetry.
- **Current Step Progress:**
  - **Slice 1 (Gate A Pre-Live Certification):** `✅ CERTIFIED` (Formal Human Sign-Off on 2026-09-04; A-1 through A-11 PASS; B-1/B-2 CLOSED; 0 Active Blockers; Demo `112040157` 100% Flat; Live Capital $0.00). See [`docs/phase13/consolidated_gate_a_audit.md`](phase13/consolidated_gate_a_audit.md).
  - **Step 1 (Implementation & Safety Envelopes):** `✅ PASS` (Bounded position limits, fail-closed kill switch).
  - **Step 2 (Code & Unit Audit):** `✅ PASS` (Full unit audit clean).
  - **Step 3 (Integration Testing):** `✅ PASS` (Integration pipeline verified).
  - **Step 4 (Restart & Recovery):** `✅ PASS` (Rehydration semantics and state reconstruction verified).
  - **Step 5 (24-Hour Unattended Soak):** `✅ VERIFIED COMPLETED` (86,400.21s runtime, 86,085 ledger events, 8,608 telemetry records, 0 errors, graceful exit).
  - **Step 6 (Telemetry Audit):** `✅ PASS` (Full forensic audit verified: SHA-256 chained integrity, zero gaps >15s, RSS peak 175.29 MB, pulse reconciliation 100%). See [`docs/phase13/phase13_step6_full_audit_report.md`](phase13/phase13_step6_full_audit_report.md).
  - **Step 7 (Continuous Paper Readiness):** `✅ CONDITIONALLY SATISFIED` (Runtime infrastructure verified ready; blocked on strategy qualification; B23.2 dedicated VM deferred). See [`docs/phase13/phase13_step7_paper_readiness_review.md`](phase13/phase13_step7_paper_readiness_review.md).
  - **Step 8 (Human GO Checkpoint):** `🔒 LOCKED` (Awaiting qualified strategy & explicit operator authorization).
  - **Step 9 (90-Day Continuous Paper Run):** `🔒 NOT AUTHORIZED` (Clock has not started; $0.00 capital authority).
- **Core Invariants:**
  - Live Capital Authority: **$0.00 (Hard-Locked)**.
  - Live Order Emission: **0 Orders**.
  - Strategy STRAT-MOM-MULTI-HORIZON-V1: **NOT QUALIFIED / TERMINALLY FALSIFIED**.
  - Broker Wire: **DISCONNECTED**.
- **Gate 13 Criteria:** **EXPLICIT HUMAN APPROVAL REQUIRED**; all safety gates, kill switches, and alerts verified operational; full completion of 24h soak evidence audit and subsequent steps.
- **Multi-Broker / Multi-Asset Roadmap (ADR-021):** While Phase 13 currently executes against the active MetaQuotes MT5 Demo baseline under Gate A, the long-term architecture is established as Asset-Agnostic and Multi-Venue (Pepperstone MT5 candidate, Alpaca US Equities/ETF candidate, OANDA API candidate, IBKR multi-asset candidate). See [`docs/architecture/multi_broker_multi_asset_decision.md`](architecture/multi_broker_multi_asset_decision.md).

---

### 📐 Phase 14: AI Quantitative Research Layer [GATE 14 ACCEPTED — RESEARCH CAPABILITY — UNVALIDATED PROPOSALS — ZERO TRADING AUTHORITY]
- **Objective:** Augment quant research with AI-driven hypothesis formulation, feature discovery, and automated research reporting conforming to Section 33.
- **Current Status:**
  - Master Research Architecture Revision 1.2: **APPROVED AT PLAN LEVEL** by Human Auditor (2026-09-08).
  - Gate 14: **ACCEPTED** (2026-09-08) — technical acceptance of the Phase 14 research capability under the G-2 CUSTOM-2 scope. **NOT** trading, runtime, or strategy authorization.
  - Governance records on file in `docs/phase14/`: Human Ratification D1–D4 (2026-09-08), D5/D6 ratification, D8-B acceptance, E1–E9 ratification, Gate 14 acceptance, S5 test-only and Seam B acceptance, evidence-bridge governance freeze.
  - Implementation slices exist in the repository as **UNVALIDATED PROPOSALS** (research-AI hypothesis assistant / converter / prompts / provider; slices 1–4; D6 Option A failed/invalid-trial census sealing; Phase 5 production orchestrator; D8-B release gate; Seam A identity; D5 OOS provenance with PIT lineage; committed 2026-09-07 / 2026-09-09). Zero authority to register hypotheses, qualify alpha, certify validation, connect brokers, or trade.
  - Runtime authorization remains bounded by ratified Human gate discipline (G-gates). Phase 13 Steps 8–9 remain independently and strictly LOCKED. HYP_003 NOT CREATED; R1 NOT INVOKED; capital $0.00; trading LOCKED; broker DISCONNECTED.
  - Governing Specification: [`docs/phase14/phase14_master_research_architecture_plan.md`](phase14/phase14_master_research_architecture_plan.md).
- **Deliverables:**
  - LLM hypothesis formulation assistant (`acash.research.ai.hypothesis`).
  - Automated research report generator conforming to Section 33 (`acash.research.ai.reporting`).
  - Exploratory feature discovery tools with causal AST validation (`acash.research.ai.features`).
  - Research corpus ingestion with tri-axial source epistemic metadata (`acash.research.ai.corpus`).
- **Gate 14 Criteria:** AI outputs are strictly unvalidated proposals; must pass full backtesting, statistical validation, and alpha qualification gates. Zero capital or broker authority.

---

### ⏳ Phase 15: Strategy Lifecycle Management [HARMONIZED INTO PHASE 17]
- **Harmonization Notice:** The original conceptual Phase 15 scope has been preserved and incorporated into the institutional Phase 17 Strategy Admission Standard and Lifecycle Architecture (ADR-023).
- **Preserved Scope:**
  - Strategy Lifecycle State Machine
  - Strategy admission status transitions (`StrategyAdmissionStatus`, `StrategyLifecycleState`)
  - Lifecycle gates and transition authority
  - Rolling strategy health / lifecycle monitoring
- **Canonical Home:** Phase 17 (`StrategyAdmissionStatus`, `StrategyLifecycleState`, ADR-023).
- **No Requirements Deleted:** All original Phase 15 requirements remain traceable in [`docs/architecture/strategy_admission_standard.md`](architecture/strategy_admission_standard.md).
- **Implementation Status:** `HARMONIZED / NOT A SEPARATE IMPLEMENTATION STEP`

---

### ⏳ Phase 16: Performance Degradation & Data Flywheel [HARMONIZED INTO PHASE 17–22]
- **Harmonization Notice:** The original conceptual Phase 16 scope has been redistributed across the institutional Phase 17–22 architecture sequence.
- **Preserved Scope:**
  - Statistical performance degradation detection → Phase 17 + Phase 11
  - Strategy selection and decision outcomes → Phase 20
  - Organizational memory / learning ledger → Phase 22
- **Canonical Traceability:** [`docs/architecture/strategy_admission_standard.md`](architecture/strategy_admission_standard.md) and ADR-023.
- **No Requirements Deleted:** Original Phase 16 concepts remain preserved and traceable.
- **Implementation Status:** `HARMONIZED / NOT A SEPARATE IMPLEMENTATION STEP`

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

### 🏛️ Phase 23: Adaptive Multi-Horizon Strategy & Market-Regime Architecture [ARCHITECTURAL RECORD]
- **Objective:** Establish the foundational architectural principle that ACASH is a strategy-agnostic, risk-controlled trading infrastructure rather than a fixed-style bot (scalping, intraday, swing, long-term).
- **Core Governance & Decoupling:**
  - Decouple ACASH Core (Risk, Execution, Reconciliation, Governance) from Strategy Layer (Alpha models, horizons, styles).
  - Strategy $\neq$ Authority; Signal $\neq$ Order; Target Position $\neq$ Execution.
  - Rejection of global fixed slice allocations (e.g. 30/30/40) in favor of Target Position, Risk Budget, Entry Schedule, and Dynamic Recalculation.
  - Confirmation-driven pyramiding default; strict rejection of blind averaging down as core default.
  - Dynamic risk recalculation per entry tranche; position size strictly bounded by stop distance.
  - Formally specified in ADR-024 and [`docs/architecture/adaptive_multi_horizon_strategy_architecture.md`](architecture/adaptive_multi_horizon_strategy_architecture.md).
- **Phase 23 Amendment (Market Microstructure, Order-Book Intelligence & Shadow Decision Learning):**
  - Formally extends Phase 23 to incorporate Level 3 order-book event streams, temporal microstructure analysis, liquidity anomaly research, and shadow decision evaluation (ADR-025).
  - Documented in [`docs/architecture/phase23_amendment_microstructure_and_shadow_decisions.md`](architecture/phase23_amendment_microstructure_and_shadow_decisions.md).
  - Proposed future implementation phases (pending audit and roadmap approval):
    - *Phase 24 [Proposed]:* Market Microstructure Data Layer & L3 Event Normalization
    - *Phase 25 [Proposed]:* Deterministic Microstructure Replay Engine
    - *Phase 26 [Proposed]:* Temporal Microstructure Feature & Anomaly Research Engine
    - *Phase 27 [Proposed]:* Shadow Decision Evaluation & Counterfactual Learning System
    - *Phase 28 [Proposed]:* Adaptive Strategy Tournament & Multi-Horizon Integration

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
