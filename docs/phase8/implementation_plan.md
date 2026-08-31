# Phase 8: Portfolio Engine Implementation Plan

> **Document:** `docs/phase8/implementation_plan.md`  
> **Status:** IMPLEMENTATION PLAN ONLY — ZERO CODE MUTATION  
> **Version:** 1.0.0  
> **Authority:** Frozen Contract [`docs/phase8/phase_8_proposal.md`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/docs/phase8/phase_8_proposal.md) (Commit `9ff7cdf`)  
> **Governing Methodology:** Test-Driven Development (TDD) First $\longrightarrow$ Implementation $\longrightarrow$ Verification

---

## 0. Executive Summary & Objective

The objective of Phase 8 is to construct the **ACASH Portfolio Engine**, enabling rigorous, deterministic multi-asset capital allocation, baseline-versus-optimizer evaluation, sovereign 100% Cash risk gates, and rebalancing delta generation for Phase 7 execution.

### Architectural Invariants:
1. $\boxed{\text{AllocationCandidate} \neq \text{AllocationEvaluation} \neq \text{AllocationDecision}}$
2. $\boxed{\text{RankScore (Sorting)} \neq \text{Acceptance Gate (Capital Authorization)}}$
3. $\boxed{\text{100\% Cash is a Sovereign Decision ("NOWHERE")}}$
4. $\boxed{\text{Core ACASH (Levels 1 \& 2) is 100\% Independent of Level 3 (skfolio/CVXPY)}}$
5. $\boxed{\text{Phase 8 outputs RebalancePlan (Desired Delta } \Delta q_i\text{); Phase 7 owns Order Execution}}$

---

## 1. Existing Domain Integration & Migration Strategy

### 1.1 Reusable Pure Domain Models (Zero Duplication)
- [`src/acash/core/domain/portfolio.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/src/acash/core/domain/portfolio.py):
  - `PortfolioState`: Tracks `cash_balance`, `margin_used`, `total_equity`, and active positions map.
  - `AccountState`: Tracks account balances, currency, and leverage settings.
- [`src/acash/core/domain/transitions.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/src/acash/core/domain/transitions.py):
  - `apply_fill_to_portfolio()`: Pure accounting transition applied when Phase 7 fills occur.
  - `update_portfolio_market_prices()`: Pure valuation update based on market price updates.
- **Integration Action:** Phase 8 directly imports and consumes `PortfolioState` for current holdings and `RiskSnapshot` extraction.

### 1.2 Legacy `IPortfolioOptimizer` Migration & Deprecation
- **Current State:** [`src/acash/core/interfaces/portfolio.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/src/acash/core/interfaces/portfolio.py) exposes `IPortfolioOptimizer.calculate_target_allocation(signals, current_portfolio, timestamp) -> TargetAllocation`.
- **Architectural Defect:** `Signal -> TargetAllocation` bypasses the `Candidate -> Evaluation -> Decision` governance gate.
- **Migration Plan:**
  1. Deprecate legacy `IPortfolioOptimizer` in `src/acash/core/interfaces/portfolio.py`.
  2. Implement a thin backward-compatibility adapter (`LegacySignalAllocationAdapter`) if existing backtest harnesses call it, wrapping the new `PortfolioEngine` pipeline.
  3. All Phase 8 components use the canonical `PortfolioAllocator`, `AllocationEvaluator`, and `PortfolioGovernanceGate` interfaces.

---

## 2. Planned Source Structure & Module Responsibilities

All new source code will reside exclusively in `src/acash/portfolio/`.

```
src/acash/portfolio/
├── __init__.py          # Public API exports
├── schema.py            # 8 Canonical DTOs & Invariant Validators
├── estimators.py        # Expected Return (μ) & Covariance (Σ) Estimators
├── baselines.py         # Level 1 Baselines (Cash, 1/N, Inverse-Vol)
├── optimizers.py        # Level 2 Native Advanced Allocators (HRP, ERC)
├── adapters.py          # Level 3 Optional skfolio/CVXPY Seam (Conditional)
├── evaluation.py        # AllocationEvaluator (CPCV Splits, Turnover, Friction, RankScore)
├── governance.py        # PortfolioGovernanceGate (Risk, Margin Buffer, Hurdle Gate)
└── planner.py           # RebalancePlanner (Desired Delta Shares & Notional Sizing)
```

### Module Breakdown Matrix

| Source File | Primary Responsibility | Key Inputs | Key Outputs | Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **`schema.py`** | Immutable DTOs & Validation | Raw financial fields | Validated 8 Domain DTOs | `pydantic`, `Decimal`, `hashlib` |
| **`estimators.py`** | Decoupled $\boldsymbol{\mu}$ and $\mathbf{\Sigma}$ Math | `AssetReturnPanel` | $\boldsymbol{\mu} \in \mathbb{R}^N$, $\mathbf{\Sigma} \in \mathbb{R}^{N \times N}$ | `numpy`, `scipy` |
| **`baselines.py`** | Level 1 Closed-Form Allocators | `AssetReturnPanel`, Constraints | `AllocationCandidate` | `schema.py`, `numpy` |
| **`optimizers.py`** | Level 2 Native HRP & ERC | `AssetReturnPanel`, $\mathbf{\Sigma}$ | `AllocationCandidate` | `schema.py`, `scipy.cluster`, `scipy.optimize` |
| **`adapters.py`** | Level 3 Conditional Solver Seam | `AssetReturnPanel`, Constraints | `AllocationCandidate` | `schema.py`, optional `skfolio` |
| **`evaluation.py`** | OOS Evaluation & Scoring | Candidates, Panel, Friction | `AllocationEvaluation` | `schema.py`, `acash.validation.cpcv` |
| **`governance.py`** | Sovereign Risk & Hurdle Gates | Evaluations, RiskSnapshot | `AllocationDecision` | `schema.py`, `estimators.py` |
| **`planner.py`** | Desired Delta Shares Generation | `AllocationDecision`, Reference BBO | `RebalancePlan` | `schema.py`, `PortfolioState` |

---

## 3. Detailed Component Specifications

### 3.1 Domain Models (`src/acash/portfolio/schema.py`)
1. **`PortfolioUniverse`:** Lexicographically sorted unique uppercase symbols, UTC timestamp, `universe_digest`.
2. **`AssetReturnPanel`:** $T \times N$ matrix of simple period returns (`Decimal`), strictly increasing UTC timestamps ($T \ge T_{\text{min}}$), `panel_digest`.
3. **`PortfolioConstraints`:** Long-only bounds ($w_i \in [\text{min\_weight}, \text{max\_weight}]$), gross leverage $\le 1.0$, min cash buffer $B_{\text{cash}} \in [0.0, 1.0]$.
4. **`RiskSnapshot`:** Account equity ($> 0$), cash balance, free margin headroom, margin buffer threshold, drawdown percentage, kill switch flag.
5. **`AllocationCandidate`:** Allocator name, `asset_weights: Mapping[str, Decimal]`, `cash_weight: Optional[Decimal]`, in-sample metrics, `candidate_digest`.
6. **`AllocationEvaluation`:** Normalized weights ($\sum w_i + w_{\text{cash}} = 1.0$), OOS Sharpe, OOS CVaR 95%, required turnover $\mathcal{T}$, estimated dollar friction $\mathcal{F}$, `net_expected_excess_return`, `hurdle_rate_cleared`, `rank_score`, `evaluation_digest`.
7. **`AllocationDecision`:** Authorized weights, cash weight, `gate_verdict` (`"AUTHORIZED"`, `"FORCED_CASH_RISK"`, `"FORCED_CASH_HURDLE"`, `"FORCED_CASH_CONSTRAINT"`), rationale, `decision_digest`.
8. **`RebalancePlan`:** Desired delta shares ($\Delta q_i = \text{truncate}(\Delta D_i / \text{BBO Mid}_i)$), desired notional delta ($\Delta D_i = D_i^* - D_{i, \text{current}}$), reference snapshot prices, estimated friction, `plan_digest`.

### 3.2 Estimators (`src/acash/portfolio/estimators.py`)
- **`ExpectedReturnEstimator` (Protocol):** Produces $\boldsymbol{\mu} \in \mathbb{R}^N$ with explicit metadata (provenance, horizon $T$, annualization factor $\sqrt{252}$). Canonical implementation: `HistoricalSampleMeanEstimator`.
- **`CovarianceEstimator` (Protocol):** Produces symmetric positive semi-definite matrix $\mathbf{\Sigma} \in \mathbb{R}^{N \times N}$. Canonical implementations:
  1. `SampleCovarianceEstimator`: Unbiased empirical sample covariance.
  2. `LedoitWolfShrinkageCovarianceEstimator`: Optimal linear shrinkage towards constant correlation target.

### 3.3 Allocators (`src/acash/portfolio/baselines.py` & `optimizers.py`)
- **`PortfolioAllocator` (Protocol):**
  ```python
  class PortfolioAllocator(Protocol):
      @property
      def allocator_name(self) -> str: ...
      def compute_candidate(
          self,
          panel: AssetReturnPanel,
          constraints: PortfolioConstraints,
          current_weights: Mapping[str, Decimal],
      ) -> AllocationCandidate: ...
  ```
- **Level 1 Baselines (`baselines.py`):**
  1. `CashAllocator`: Proposes $w_i = 0 \quad \forall i$, $w_{\text{cash}} = 1.0$.
  2. `EqualWeightAllocator` ($1/N$): Proposes $w_i = (1 - B_{\text{cash}}) / N$.
  3. `InverseVolatilityAllocator` ($1/\sigma$): Proposes $w_i \propto 1/\sigma_i$. Fail-closed on $\sigma_i \le 0$.
- **Level 2 Native Advanced Allocators (`optimizers.py`):**
  1. `HierarchicalRiskParityAllocator` (`HRP`): Computes correlation distance $d_{i,j} = \sqrt{\frac{1}{2}(1 - \rho_{i,j})}$, single/complete linkage tree clustering, quasi-diagonalization, and recursive bisection inverse-variance allocation.
  2. `EqualRiskContributionAllocator` (`ERC`): Solves risk parity equation $w_i (\mathbf{\Sigma} \mathbf{w})_i = w_j (\mathbf{\Sigma} \mathbf{w})_j$ via coordinate descent / SQP.
- **Level 3 Conditional Adapters (`adapters.py`):**
  - Conditional wrappers for `skfolio` / `cvxpy`. If packages are not installed, `is_available()` returns `False` and attempting invocation raises explicit `DependencyUnavailableError` with graceful baseline fallback.

### 3.4 Out-of-Sample Evaluation Engine (`src/acash/portfolio/evaluation.py`)
- Reuses Phase 6 [`CombinatorialPurgedCrossValidation`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/src/acash/validation/cpcv.py) to split historical return panels into $K$ train/test partitions with embargo.
- Computes out-of-sample portfolio return series: $r_{\text{oos}, k, t} = \mathbf{w}_{\text{train}, k}^T \mathbf{r}_{\text{test}, k, t}$.
- Evaluates annualized Sharpe ratio, 95% CVaR, required turnover $\mathcal{T}$, and friction $\mathcal{F}$.
- Computes canonical `RankScore`:
  $$\text{Rank Score} = \text{Annualized Sharpe}(r_{\text{oos}}) - \lambda_{\text{TO}} \cdot \mathcal{T} - \lambda_{\text{Tail}} \cdot \text{CVaR}_{95}(r_{\text{oos}})$$
- Applies deterministic tie-breaking: $\text{CASH} > \text{EQUAL\_WEIGHT} > \text{INVERSE\_VOL} > \text{HRP} > \text{ERC}$.

### 3.5 Governance & Sovereign Decision Gate (`src/acash/portfolio/governance.py`)
- **Pre-Allocation Risk Gate:**
  - Evaluates `RiskSnapshot`: Kill Switch active, Drawdown $\ge$ limit, Free Margin $<$ buffer threshold, or Data Health failure $\implies$ Forces `AllocationDecision(CASH, verdict="FORCED_CASH_RISK")`.
- **Post-Evaluation Hurdle Gate:**
  - Evaluates top-ranked candidate:
    $$\mathbb{E}[R_p] - \mathcal{F} \ge r_f + H_0$$
  - If condition fails $\implies$ Forces `AllocationDecision(CASH, verdict="FORCED_CASH_HURDLE")`.
- **Sovereign Baseline Selection Invariant:**
  - If $\text{RankScore}(\text{Baseline}) \ge \text{RankScore}(\text{Advanced Optimizer}) \implies$ Baseline is selected.

### 3.6 Rebalance Planning & Phase 7 Interface (`src/acash/portfolio/planner.py`)
- Translates `AllocationDecision` into discrete target holdings:
  $$\Delta D_i = w_i^* \times \text{Equity} - q_{i, \text{current}} \times \text{BBO Mid}_i$$
  $$\Delta q_i = \text{truncate}(\Delta D_i / \text{BBO Mid}_i)$$
- **Phase 7 Boundary Protection:** Outputs `RebalancePlan` containing desired delta shares $\Delta q_i$ and reference notionals $\Delta D_i$. Does **not** dispatch orders or execute trades. Phase 7 `ExecutionCoordinator` owns order creation, wire submission, fills, and reconciliation.

---

## 4. Test-Driven Development (TDD) Plan

Testing suite will be organized under `tests/unit/portfolio/`.

```
tests/unit/portfolio/
├── test_portfolio_schema.py          # DTO validation, immutability & cryptographic digests
├── test_estimators.py                # μ and Σ estimator invariants & Ledoit-Wolf benchmarks
├── test_baseline_allocators.py       # Cash, 1/N, Inverse-Vol numerical reference tests
├── test_native_optimizers.py         # HRP & ERC numerical convergence & risk parity checks
├── test_optional_adapters.py         # Level 3 conditional loading & graceful fallback
├── test_allocation_evaluation.py     # CPCV OOS evaluation, turnover friction & RankScore
├── test_governance_gate.py           # Pre-risk gate, hurdle gate, sovereign Cash enforcement
├── test_rebalance_planner.py         # Delta shares calculation & Phase 7 boundary protection
└── test_portfolio_invariants.py      # Adversarial, zero-variance, degenerate, and tie-breaking tests
```

### Planned Test Cases by Category
1. **Schema & Integrity Tests (`test_portfolio_schema.py`):**
   - Immutability of all 8 DTOs.
   - Fail-closed validation on $T < T_{\text{min}}$, non-finite `NaN`/`Inf` returns, duplicate universe assets.
   - Deterministic 64-hex SHA-256 digest recomputation for every DTO.
2. **Numerical Benchmark Tests (`test_estimators.py` & `test_baseline_allocators.py`):**
   - Closed-form $1/N$ weight sum $= 1.0 - B_{\text{cash}}$.
   - Inverse-Vol exact weights against manual analytical reference.
   - Fail-closed error boundary when asset volatility $\sigma_i \le 0$ (zero magic floors).
3. **Advanced Allocator Tests (`test_native_optimizers.py`):**
   - HRP quasi-diagonalization and tree clustering permutation invariance.
   - ERC risk parity invariant: $|w_i (\mathbf{\Sigma} \mathbf{w})_i - w_j (\mathbf{\Sigma} \mathbf{w})_j| < 10^{-6}$.
4. **Governance & Gate Adversarial Tests (`test_governance_gate.py`):**
   - Active Kill Switch forces 100% Cash.
   - Margin buffer breach forces 100% Cash.
   - Drawdown limit breach forces 100% Cash.
   - Expected return below hurdle rate forces 100% Cash.
   - `RankScore` #1 candidate rejected when failing hurdle.
5. **Phase 7 Integration Boundary Tests (`test_rebalance_planner.py`):**
   - Desired delta shares $\Delta q_i$ correctly computed without mutating broker state.
   - Rebalance plan rejection when estimated margin requirement exceeds free margin.

---

## 5. Implementation Step Sequence

```
[Step 1] Unit Tests for Schema & Invariants (tests/unit/portfolio/test_portfolio_schema.py)
   ↓
[Step 2] Domain Models Implementation (src/acash/portfolio/schema.py)
   ↓
[Step 3] Estimators Tests & Implementation (test_estimators.py -> estimators.py)
   ↓
[Step 4] Baseline Allocators Tests & Implementation (test_baseline_allocators.py -> baselines.py)
   ↓
[Step 5] Native Advanced Optimizers Tests & Implementation (test_native_optimizers.py -> optimizers.py)
   ↓
[Step 6] Optional skfolio Adapters Seam (test_optional_adapters.py -> adapters.py)
   ↓
[Step 7] Evaluation Engine Tests & Implementation (test_allocation_evaluation.py -> evaluation.py)
   ↓
[Step 8] Governance Gate Tests & Implementation (test_governance_gate.py -> governance.py)
   ↓
[Step 9] Rebalance Planner Tests & Implementation (test_rebalance_planner.py -> planner.py)
   ↓
[Step 10] Public Exports & Integration Verification (src/acash/portfolio/__init__.py)
   ↓
[Step 11] Full Verification Suite (610+ tests, MyPy Strict Clean) & Gate 8 Review
```

---

## 6. Gate 8 Measurable Acceptance Criteria

Gate 8 will be marked **PASSED** when:
- [ ] 1. **Baseline Golden Reference:** $1/N$, $1/\sigma$, and 100% Cash produce deterministic, closed-form weights matching analytical reference benchmarks.
- [ ] 2. **Sovereign Cash Enforcement:** Pre-allocation risk distress (kill switch, margin, drawdown) or post-evaluation hurdle shortfall forces `AllocationDecision = CASH` deterministically.
- [ ] 3. **Candidate $\neq$ Decision Invariant:** Allocators propose weights; only Governance Gate authorizes decisions.
- [ ] 4. **Ranking $\neq$ Approval Invariant:** Highest `RankScore` candidate is rejected if failing absolute hurdle/risk limits.
- [ ] 5. **Friction & Baseline Preference:** OOS evaluation penalizes turnover and selects baselines over overfitted optimizers.
- [ ] 6. **Phase 7 Boundary Preserved:** `RebalancePlan` produces desired position deltas ($\Delta q_i$); Phase 7 owns order execution and reconciliation.
- [ ] 7. **Full Test Suite & Typing Clean:** 100% pass on all new unit/adversarial tests, full repository test suite (>= 610 tests), MyPy clean (0 new errors).
- [ ] 8. **Live Execution Remains HARD-LOCKED (OFF).**
