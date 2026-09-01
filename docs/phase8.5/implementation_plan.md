# Phase 8.5: Alpha Research & Evidence Validation
## Canonical Implementation Plan (Contract v1.3 Locked)

> **Document:** `docs/phase8.5/implementation_plan.md`  
> **Status:** 100% COMPLETE & FROZEN (772/772 Tests Passing, 0 MyPy Errors)  
> **Baseline Commit:** Phase 8.5 Slice 1–6 Complete  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Authority, Strict Fail-Closed, Separation of Concerns)

---

## 1. Executive Summary & Core Architectural Invariants

Phase 8.5 establishes the **Alpha Qualification & Evidence Envelope Pipeline** for ACASH. It bridges Phase 4/6 hypothesis and statistical validation with Phase 8 portfolio allocation tournaments without creating a new research engine from scratch or encroaching on downstream execution authority.

### Non-Negotiable Sovereign Invariants:
1. **Four-Way Separation of Concerns:**
   $$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)}}$$
2. **Zero Capital Authority in Phase 8.5:**
   $$\boxed{\forall s \in \text{AlphaLifecycleState} \implies \mathbf{Capital\ Authority(s) \equiv \$0.00}}$$
3. **No Live Execution Authority:**
   $$\boxed{\mathbf{RESEARCH\_QUALIFIED} \implies \text{Candidate Pool Admissibility ONLY} \quad \land \quad \mathbf{RESEARCH\_QUALIFIED} \nRightarrow \text{Order Authority}}$$
4. **Economic Decomposition & Rebate Isolation:**
   $$\boxed{\text{Net Trading Alpha} = \text{Gross Trading Return} - \text{Realized Friction (Spread + Slippage + Fees)}}$$
   $$\boxed{\text{Qualification Condition: } \mathbf{Net\ Trading\ Alpha \ge Hurdle\ Rate}\text{ (Evaluated with } \text{Rebates} \equiv 0\text{)}}$$
   *Rebates must never rescue a negative-alpha strategy.*
5. **Single Canonical Authority & Cryptographic Lineage:**
   $$\mathbf{HypothesisDigest} \to \mathbf{TrialLedgerDigest} \to \mathbf{ValidationReportDigest} \to \mathbf{GovernanceDecisionDigest} \to \mathbf{AlphaDossierDigest}$$
   *Built exclusively upon `CanonicalConfigSerializer` with zero duplicate hashing or alternate serializers.*
6. **No Retrospective State Mutation:**
   *All lifecycle transitions are forward-moving, immutable, and fail-closed.*

---

## 2. Inventory of Reused Existing Components

| Existing Component | Source Location | Reused Role in Phase 8.5 | Invariant Preserved |
| :--- | :--- | :--- | :--- |
| **`HypothesisSpecification` / `InvalidationCriteria`** | `src/acash/research/schema.py` | Initial hypothesis binding & falsification criteria | Pre-registered economic theory |
| **`SearchTrialLedger` / `SearchTrialRecord`** | `src/acash/validation/schema.py` | Single authority for exploratory trial count $K_{\text{nominal}}$ and return hashes | $K_{\text{ledger}} = K_{\text{DSR}} = K_{\text{FWER}}$ |
| **`StatisticalValidationGate`** | `src/acash/validation/gate.py` | Multi-layer statistical defense (DSR, PBO, FWER, Perturbation, Friction) | Mathematical validation battery |
| **`DeflatedSharpeEngine`** | `src/acash/validation/deflated_sharpe.py` | Selection-bias and trial-mining deflation | Bailey-López de Prado formulation |
| **`CombinatorialPurgedCrossValidation`** | `src/acash/validation/cpcv.py`, `overfitting.py` | PBO distribution across combinatorial partitions (252 CSCV splits) | Anti-overfitting distribution |
| **`MultipleTestingEngine`** | `src/acash/validation/multiple_testing.py` | Family-Wise Error Rate control (Holm-Bonferroni, BHY) | False discovery bounding |
| **`slice_panel` / `TournamentSplitConfig`** | `src/acash/portfolio/tournament.py` | Temporal partitioning and walk-forward slicing | Zero lookahead bias |
| **`CanonicalConfigSerializer` / `_sha256_hexdigest`** | `src/acash/core/serialization.py`, `validation/schema.py` | Canonical JSON serialization and SHA-256 digests | Single serialization authority |
| **`PortfolioGovernanceGate`** | `src/acash/portfolio/governance.py` | Sovereign hurdle rate and capital preservation evaluation | 100% Cash fallback on hurdle failure |
| **`ExecutionCoordinator` / Paper Bridge** | `src/acash/execution/alpaca/`, `backtest/nautilus_bridge.py` | Real broker-observed order evidence | Paper evidence $P\text{-001}$ lineage |

---

## 3. New Phase 8.5 Components (Contract v1.3)

### 3.1 `src/acash/research/alpha_schema.py` (Data Contracts & State Machine)
- **Responsibility:** Define immutable Pydantic models for Alpha lifecycle states, economic decomposition, computable falsification triggers, and the cryptographic evidence envelope.
- **DTOs:**
  - `AlphaLifecycleState` (Enum: `HYPOTHESIS`, `RESEARCH_SEARCH`, `CANDIDATE`, `STATISTICAL_VALIDATED`, `ECONOMIC_EDGE_QUALIFIED`, `FORWARD_PAPER_MONITORED`, `RESEARCH_QUALIFIED`, and terminal states `REJECTED_STATISTICAL_GATE`, `REJECTED_HURDLE_COLLAPSE`, `DEGRADED_FORWARD_TEST`, `RETIRED_STRUCTURAL_BREAK`).
  - `AlphaEconomicDecomposition` (Validates gross return, friction, net trading alpha, and rebate income; enforces `Net = Gross - Friction`).
  - `AlphaFalsificationTrigger` (Deterministic, computable invalidation assertions: metric name, threshold, comparison operator, triggered status).
  - `AlphaQualificationDossier` (Frozen cryptographic envelope binding hypothesis digest, trial ledger digest, validation report digest, governance decision digest, economic decomposition, falsification triggers, and computed dossier digest).
- **Dependencies:** `pydantic`, `decimal`, `acash.core.serialization.CanonicalConfigSerializer`.

### 3.2 `src/acash/research/qualification.py` (`AlphaQualificationGate`)
- **Responsibility:** Orchestrate the qualification battery and state transitions from `STATISTICAL_VALIDATED` to `ECONOMIC_EDGE_QUALIFIED` and `RESEARCH_QUALIFIED`.
- **Core Operations:**
  1. **`evaluate_economic_edge(gross_return_bps, friction_params, hurdle_rate_bps, rebate_income_bps) -> AlphaEconomicDecomposition`**:
     - Computes net trading alpha strictly before rebates.
     - Asserts $\text{Net Trading Alpha} \ge \text{Hurdle Rate}$. If violated, transitions to `REJECTED_HURDLE_COLLAPSE` (fail-closed).
  2. **`evaluate_falsification_triggers(dataset, triggers) -> Tuple[AlphaFalsificationTrigger, ...]`**:
     - Computes empirical metrics (IC decay, autocorrelation, drawdown, spread fragility) and tests against pre-registered thresholds.
     - If any critical trigger trips, transitions to `DEGRADED_FORWARD_TEST`.
  3. **`seal_qualification_dossier(alpha_id, strategy_id, hypothesis_spec, trial_ledger, validation_report, governance_decision, economic_decomp, triggers) -> AlphaQualificationDossier`**:
     - Verifies cryptographic lineage across all input artifacts.
     - Computes deterministic `dossier_digest`.
     - Sets state to `RESEARCH_QUALIFIED`.

---

## 4. Implementation Slices & Execution Order

```
Slice 1: Schema & Data Contracts (alpha_schema.py)
   │
   ▼
Slice 2: Economic Decomposition & Rebate Isolation Engine
   │
   ▼
Slice 3: Computable Falsification & Trigger Engine
   │
   ▼
Slice 4: Alpha Qualification Gate & State Machine (qualification.py)
   │
   ▼
Slice 5: Cryptographic Dossier Envelope & Lineage Sealing
   │
   ▼
Slice 6: Full Integration Test Battery (725+ Regression Green)
```

---

### Slice 1: Core Domain Contracts & State Machine
- **File:** `src/acash/research/alpha_schema.py`
- **Tests:** `tests/unit/research/test_alpha_schema.py`
- **Tasks:**
  1. Implement `AlphaLifecycleState` with all 11 discrete states.
  2. Implement `AlphaEconomicDecomposition` with Pydantic model validator verifying $\text{Net} = \text{Gross} - \text{Friction}$.
  3. Implement `AlphaFalsificationTrigger` and `AlphaQualificationDossier`.
  4. Write tests for immutability (`frozen=True`, `extra="forbid"`), non-negative finite Decimals, and valid JSON serialization.

---

### Slice 2: Economic Decomposition & Rebate Isolation
- **File:** `src/acash/research/qualification.py`
- **Tests:** `tests/unit/research/test_alpha_qualification.py`
- **Tasks:**
  1. Implement `evaluate_economic_edge` calculating gross return, spread, slippage, broker fees, and net trading alpha.
  2. Implement strict zero-rebate qualification invariant:
     $$\text{Net Trading Alpha} < \text{Hurdle} \implies \text{REJECTED\_HURDLE\_COLLAPSE (even if Total Economic Return > 0 with rebates)}$$
  3. Write adversarial tests verifying strategies with positive rebate subsidies but negative raw trading edge are strictly rejected.

---

### Slice 3: Computable Falsification Trigger Engine
- **File:** `src/acash/research/qualification.py`
- **Tests:** `tests/unit/research/test_alpha_falsification.py`
- **Tasks:**
  1. Implement deterministic evaluations for:
     - Rank IC below invalidation threshold
     - Feature autocorrelation saturation ($\rho_{\text{lag1}} > \text{threshold}$)
     - Severe drawdown breach under high-volatility regime
     - Spread fragility ($\text{Edge} / \text{Cost} < \text{threshold}$)
  2. Write unit tests for trigger tripping, boundary evaluation, and fail-closed behavior on NaN/Inf inputs.

---

### Slice 4: Alpha Qualification Gate & Dossier Sealing
- **File:** `src/acash/research/qualification.py`
- **Tests:** `tests/unit/research/test_alpha_qualification.py`
- **Tasks:**
  1. Implement `AlphaQualificationGate` linking Phase 4 hypothesis, Phase 6 validation report, Phase 8 governance decision, and Phase 8.5 economic decomposition.
  2. Compute canonical SHA-256 `dossier_digest` over sorted dictionary payload.
  3. Enforce fail-closed state transition: missing ledger $\to$ rejection, failed statistical gate $\to$ rejection, tripped falsification trigger $\to$ degradation.
  4. Write adversarial tests attacking digest tampering, missing evidence, and out-of-order transitions.

---

### Slice 5: Full End-to-End Integration & Multi-Phase Lineage
- **Tests:** `tests/integration/test_alpha_qualification_pipeline.py`
- **Tasks:**
  1. Test end-to-end flow:
     $$\text{Hypothesis} \to \text{Search Ledger} \to \text{Validation Gate} \to \text{Qualification Gate} \to \text{Dossier} \to \text{Portfolio Universe}$$
  2. Verify Phase 8 allocation tournament consumes `RESEARCH_QUALIFIED` alphas without modifying Phase 8 allocator protocols.
  3. Verify Phase 7 execution coordinator remains isolated.
  4. Verify full test suite passes (725+ existing tests green).

---

## 5. Comprehensive Test Strategy & Invariant Matrix

| Test Category | Target Module | Invariant / Failure Mode Attacked |
| :--- | :--- | :--- |
| **Contract Invariants** | `test_alpha_schema.py` | Immutability, `extra="forbid"`, non-finite Decimal rejection, valid enum types. |
| **State Machine Boundaries** | `test_alpha_qualification.py` | Strict forward-only progression, rejection state finality, zero retrospective mutation. |
| **Rebate Isolation** | `test_alpha_qualification.py` | Strategy with Net Alpha = -2 bps and Rebate = +5 bps must be REJECTED. |
| **Falsification Evaluation** | `test_alpha_falsification.py` | Tripped triggers immediately transition state to `DEGRADED_FORWARD_TEST`. |
| **Lineage & Tampering** | `test_alpha_qualification.py` | Modified hypothesis, ledger, or validation report invalidates `dossier_digest`. |
| **Authority Isolation** | `test_alpha_qualification.py` | Assert `Capital Authority == $0.00` across all Phase 8.5 objects. |
| **Full Regression Battery** | Full repository test suite | 100% pass rate across all 725+ existing unit, integration, and invariant tests. |

---

## 6. Acceptance Criteria for Phase 8.5 Completion

To declare Phase 8.5 complete and frozen:
1. **Contract v1.3 Invariants Verified:** All 6 core invariants (Separation of Concerns, Zero Capital Authority, No Live Execution Authority, Rebate Isolation, Cryptographic Lineage, No Retrospective Mutation) are enforced by source code and tested by unit/adversarial suites.
2. **Zero Code Regression:** 100% of existing tests pass (`uv run pytest -q` -> 725+ passed).
3. **Zero Type Errors:** Full MyPy type checking passes (`uv run mypy src/ tests/` clean).
4. **Clean Architecture:** Zero changes to Phase 7 execution or Phase 8 governance gates; Phase 8.5 operates purely as a research evidence qualification layer.
5. **Complete Documentation:** `docs/phase8.5/` contains canonical contract, architecture specifications, and evidence ledgers.

---

### Implementation Readiness Ledger
- Design Specification: **CONTRACT v1.3 (LOCKED & VERIFIED)**
- Reused Components: **10 EXISTING ENGINES INTEGRATED (ZERO DUPLICATION)**
- Modules Implemented: **`alpha_schema.py`, `qualification.py` (100% COMPLETE)**
- Capital Authority in Phase 8.5: **EXPLICITLY ZERO ($0.00 INVARIANT ENFORCED)**
- Test Suite: **772/772 PASSED (0 REGRESSIONS, 0 FAILURES)**
- Type Check: **MYPY 100% CLEAN (0 ERRORS ACROSS 21 RESEARCH FILES)**
- Status: **PHASE 8.5 COMPLETE & FROZEN -> READY FOR PHASE 9 RISK ENGINE**
