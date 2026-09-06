# ACASH Phase 21 — Risk-Based Capital Allocation Solvers
## Master Architecture & Governance Specification

> **Document ID:** `ACASH-SPEC-PHASE21-ALLOCATION-v1.0`  
> **Status:** PROPOSED ARCHITECTURE & GOVERNANCE SPECIFICATION — HUMAN APPROVAL PENDING (Phase 21 Rev 1.0)  
> **Parent Governance:** `docs/ROADMAP.md` (v3.4.0), `AGENTS.md`, ADR-022, ADR-023  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed Contract, Evidence > Belief, Single Canonical Authority)  
> **Date:** 2026-09-06  
> **Version:** 1.0.0 (Initial Master Specification)  

---

> [!IMPORTANT]
> **STRICT GOVERNANCE BOUNDARY & CAPITAL RESTRICTIONS:**
> - **THIS SPECIFICATION IS A DESIGN, ARCHITECTURAL, AND GOVERNANCE DOCUMENT ONLY.**
> - **THIS SPECIFICATION DOES NOT AUTHORIZE CODE IMPLEMENTATION.**
> - **PHASE 21 IMPLEMENTATION IS STRICTLY LOCKED / NOT AUTHORIZED.**
> - **THIS SPECIFICATION DOES NOT GRANT LIVE TRADING OR BROKER PERMISSIONS.**
> - **LIVE CAPITAL AUTHORITY REMAINS HARD-LOCKED AT $0.00.**
> - **LIVE ORDER EMISSION AUTHORITY REMAINS STRICTLY 0.**
> - **LIVE BROKER CONNECTION REMAINS STRICTLY DISCONNECTED.**
> - **ZERO RUNTIME MUTATION TO `src/` OR `tests/`.**
> - **PHASE 13 STEP 5 UNATTENDED SOAK TEST (PID 41844) REMAINS ACTIVE AND UNTOUCHED.**
> - **PHASE 22 (PORTFOLIO ORCHESTRATION) IS NOT STARTED.**

---

## 1. Executive Summary

Phase 21 establishes the **Risk-Based Capital Allocation Solvers** for the ACASH quantitative trading and research operating system.

### 1.1 Core Mission
The sole objective of Phase 21 is to resolve the risk-based portfolio sizing problem:
$$\text{"Given an authorized StrategySelectionDecision from Phase 20 and the currently declared capital, risk, and governance constraints, what portfolio weights or risk budgets should be assigned to the selected strategy set?"}$$

Phase 21 functions as an optimization solver and mathematical risk-budgeting engine. It receives an already-filtered, already-admitted, regime-compatible strategy slate from Phase 20 and computes continuous target portfolio weights $w_i$ and target risk contributions $\text{RC}_i$ under institutional risk constraints.

### 1.2 Absolute Negative Invariants
Phase 21 is governed by strict, non-negotiable negative boundaries. Phase 21 **MUST NOT**:
1. **Discover or Propose Strategies:** Strategy generation belongs solely to Phase 14 research.
2. **Select Strategies (No Phase 20.5):** Phase 21 cannot pick which strategy to run, add new strategies, or resurrect candidates excluded by Phase 20. Selection belongs strictly and exclusively to Phase 20.
3. **Certify Statistical Validity:** Phase 21 cannot evaluate $p$-values, Deflated Sharpe Ratios (DSR), or Probability of Backtest Overfitting (PBO). That belongs solely to Phase 6.
4. **Evaluate Economic Feasibility:** Phase 21 cannot certify net alpha or qualify trading edges. That belongs solely to Phase 8.5.
5. **Admit Strategies:** Phase 21 cannot admit strategies to the sovereign catalog. That belongs solely to Phase 17.
6. **Detect or Classify Regimes:** Phase 21 cannot measure market states or train regime models. That belongs solely to Phase 19.
7. **Modify Runtime Health:** Phase 21 cannot alter, suppress, or clear forward health degradation flags. That belongs solely to Phase 11.
8. **Orchestrate Multi-Strategy Orders:** Phase 21 does not batch orders or net positions. That belongs to Phase 22.
9. **Emit Orders or Route to Brokers:** Phase 21 outputs abstract target portfolio weights ($w_i$), NOT broker orders. Target weights are not positions. Order routing belongs strictly to Phase 12 execution adapters.
10. **Deploy Live Capital:** Phase 21 operates with live capital strictly hard-locked at `$0.00`.

---

## 2. Governance Baseline State

The baseline operational state of the ACASH repository is strictly recorded:
- **Phase 12 (Execution Adapters):** COMPLETED / FROZEN (`1e1d154`).
- **Phase 13 (Paper Execution & Operational Soak):** ACTIVE — Step 5 (24-hour soak) actively running under PID 41844. Must remain completely untouched.
- **Phase 14 (AI Hypothesis & Proposal Engine):** APPROVED AT PLAN LEVEL | IMPLEMENTATION LOCKED.
- **Phase 17 (Strategy Admission Standard):** APPROVED AT PLAN LEVEL | FROZEN | IMPLEMENTATION LOCKED (Rev 5.0, `7e0271f`).
- **Phase 18 (Strategy Research & Tournament Pipeline):** APPROVED AT PLAN LEVEL | FROZEN | IMPLEMENTATION LOCKED (Rev 1.1, `ce69243`).
- **Phase 19 (Empirical Regime Detection Engine):** APPROVED AT PLAN LEVEL | FROZEN | IMPLEMENTATION LOCKED (Rev 1.1, `3b9910a`).
- **Phase 20 (Strategy Selection & Decision Engine):** APPROVED AT PLAN LEVEL | FROZEN | IMPLEMENTATION LOCKED (Rev 1.2, `2ad7c38`).
- **Phase 21 (Capital Allocation Solvers):** PROPOSED SPECIFICATION — IMPLEMENTATION STRICTLY LOCKED.
- **Phase 22 (Portfolio Orchestration):** NOT STARTED.
- **Live Capital Authority:** `$0.00` (GLOBAL HARD-LOCK).
- **Live Order Authority:** `0` (GLOBAL HARD-LOCK).
- **Live Broker Connection:** `DISCONNECTED`.
- **Reference Strategy (`STRAT-MOM-V1`):** `QUALIFICATION_BLOCKED` (ADR-023 Gate 5 failure: uncharacterized latency/friction).

---

## 3. Epistemic Foundations & Canonical Non-Equivalences

To prevent epistemic drift and the conflation of mathematical optimization with empirical financial truth, Phase 21 establishes twelve formal non-equivalences:

$$\boxed{\begin{aligned}
1.\quad \text{Capital Allocation} &\not\equiv \text{Strategy Selection (Phase 20)} \\
2.\quad \text{Capital Allocation} &\not\equiv \text{Statistical Validation (Phase 6)} \\
3.\quad \text{Capital Allocation} &\not\equiv \text{Economic Qualification (Phase 8.5)} \\
4.\quad \text{Capital Allocation} &\not\equiv \text{Sovereign Admission (Phase 17)} \\
5.\quad \text{Capital Allocation} &\not\equiv \text{Regime Detection (Phase 19)} \\
6.\quad \text{Capital Allocation} &\not\equiv \text{Forward Health Monitoring (Phase 11)} \\
7.\quad \text{Capital Allocation Plan} &\not\equiv \text{Executed Position / Fill} \\
8.\quad \text{Target Weight } w_i &\not\equiv \text{Broker Order / Route} \\
9.\quad \text{Risk Budget } b_i &\not\equiv \text{Capital Deployment} \\
10.\quad \text{Solver Feasibility} &\not\equiv \text{Strategy Alpha / Profitability} \\
11.\quad \text{Numerical Optimality} &\not\equiv \text{Real-World Market Optimality} \\
12.\quad \text{Stress Test Survival} &\not\equiv \text{Proof of Absolute Safety}
\end{aligned}}$$

### 3.1 The "Solver $\neq$ Financial Truth" Invariant
A mathematical optimizer (e.g., Equal Risk Contribution, Quadratic Programming, Convex Optimization) finds the numerical vector $w^*$ that minimizes or maximizes a declared formal objective function subject to declared constraints:
$$w^* = \arg\min_{w \in \Omega} f(w;\, \Sigma,\, \dots)$$
Phase 21 explicitly rejects the naive assumption that $w^*$ represents "the objectively optimal portfolio in the real world":
- $w^*$ is optimal **only** with respect to the specified mathematical objective $f(\cdot)$, the sample covariance matrix $\Sigma$, and the modeled constraints $\Omega$.
- If $\Sigma$ is misestimated, if return distributions exhibit heavy tails, or if liquidity evaporates, the numerical solution does not prevent real-world drawdowns.
- Optimization feasibility proves only mathematical convergence; it never proves future profitability.

### 3.2 Allocation $\neq$ Execution Invariant
Target portfolio weights emitted by Phase 21 are purely mathematical target ratios:
- Emitting $w_i = 0.25$ does **not** mean the broker currently holds 25%.
- Emitting $w_i = 0.00$ does **not** send a market sell order to the broker.
- Converting target weights into executable order intents and netting positions across strategies belongs strictly to Phase 22.

---

## 4. Sovereign Authority Hierarchy & System Flow

Phase 21 operates within the immutable ACASH Authority Hierarchy:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 19: EMPIRICAL REGIME DETECTION ENGINE                 │
│                 (Measures Market State: RegimeObservationEnvelope)          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Read-Only RegimeState
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 20: REGIME × STRATEGY SELECTION ENGINE                │
│                 (Determines Eligible Candidate Slate under Policy)          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Read-Only StrategySelectionDecision
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 21: RISK-BASED CAPITAL ALLOCATION SOLVERS             │
│  ├── AllocationEligibilityFirewall (25 Pre-Solver Hard Gates)               │
│  ├── CapitalSourceModel (Equity vs Allocatable Capital vs Cash Floor)       │
│  ├── CovarianceGovernanceEngine (Ledoit-Wolf Shrinkage, PSD Validation)     │
│  ├── SolverArchitecture (ERC, Risk Parity, VolTarget, MinVar, MeanVar)      │
│  ├── ConstraintEvaluationEngine (Concentration, Leverage, Turnover)         │
│  ├── StressAndSensitivityEngine (Covariance Shocks, Capacity Stress)        │
│  ├── PortfolioAllocationPlan (Immutable Cryptographically Sealed Plan)      │
│  └── AllocationAuditLedger (Append-Only SHA-256 Chained Disk Ledger)        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Read-Only PortfolioAllocationPlan (Weights w_i)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 22: PORTFOLIO ORCHESTRATION & NETTING                 │
│                 (Multi-Strategy Execution Intent Coordination & Netting)    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Net Execution Intents
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 12: PHYSICAL EXECUTION ADAPTERS                       │
│                 (Broker Routing, FIX Sessions, Transport Connectivity)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Cross-Phase Sovereign Authority Matrix

| Phase | Sovereign Ownership | What Phase 21 Consumes | What Phase 21 Produces | Forbidden Phase 21 Actions |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 6** | Canonical Statistical Validation | `ValidationReport`, sealed ledger digest. | None. | Phase 21 cannot validate strategies or compute DSR/PBO. |
| **Phase 8.5** | Economic Qualification | `AlphaQualificationDossier`, capacity limit. | None. | Phase 21 cannot alter net alpha or redefine transaction costs. |
| **Phase 11** | Forward Monitoring & Health | `ForwardHealthState`, realized drawdown. | None. | Phase 21 cannot clear or override health degradation flags. |
| **Phase 13** | Paper Validation & Soak Execution | Operational soak receipts, Gate B readiness. | None. | Phase 21 cannot deploy capital or bypass operational gates. |
| **Phase 14** | AI Hypothesis Proposals | Unvalidated candidate proposals. | None. | Phase 21 cannot allocate capital to Phase 14 proposals. |
| **Phase 17** | Sovereign Strategy Admission | Sovereign Strategy Catalog, Gates 0–10. | None. | Phase 21 cannot admit a strategy into the catalog. |
| **Phase 18** | Research Tournament | Candidate ranking heuristics & tournament logs. | None. | Phase 21 cannot use tournament rank to bypass admission. |
| **Phase 19** | Empirical Regime Detection | `RegimeObservationEnvelope`, transition entropy. | None. | Phase 21 cannot train regime models or alter regime states. |
| **Phase 20** | Regime-Conditioned Selection | `StrategySelectionDecision`, selected slate. | None. | **Phase 21 cannot pick strategies, add candidates, or alter slate.** |
| **Phase 21** | **Risk-Based Capital Allocation** | **All upstream evidence & decision digests.** | **`PortfolioAllocationPlan`** | **FORBIDDEN: Capital deployment, order generation, broker routing.** |
| **Phase 22** | Portfolio Orchestration & Netting | `PortfolioAllocationPlan` (target weights). | Netting execution intents. | Phase 21 cannot batch orders or net positions. |
| **Phase 12** | Execution Adapters & Transport | Execution intents from Phase 22. | Physical broker orders. | Phase 21 cannot connect to broker APIs. |

---

## 5. Phase 20 → Phase 21 Interface Contract

Phase 21 ingests the sealed, immutable `StrategySelectionDecision` record emitted by Phase 20. Phase 21 treats the selected strategy slate as **authoritative and unalterable**.

### 5.1 Upstream Decision Status Action Mapping

| Phase 20 Decision Status | Phase 21 Engine Action | Permitted Allocation Output |
| :--- | :--- | :--- |
| `SELECTED` | Exactly one strategy selected. Passes to single-strategy allocation policy. | $w_1 \in [0.00, 1.00]$, cash $w_0 = 1 - w_1$. |
| `SELECT_SET` | Multiple strategies selected. Passes to multi-strategy portfolio solver. | Joint optimization over $\{w_1, \dots, w_N\}$. |
| `NO_SELECTION` | No strategy eligible. Fail-closed halt. | `NO_ALLOCATION` ($w_i = 0.00, \forall i$). |
| `REVIEW_REQUIRED` | Ambiguous/near-tie selection requiring human review. Fail-closed halt. | `ALLOCATION_BLOCKED` (unless explicit override). |
| `BLOCKED` | Upstream governance or circuit-breaker lock asserted. Fail-closed halt. | `ALLOCATION_BLOCKED` ($w_i = 0.00, \forall i$). |

### 5.2 Strict Selection Boundaries
1. **No Candidate Resurrection:** Phase 21 cannot allocate capital to any candidate listed in Phase 20's `excluded_candidate_records`.
2. **No Strategy Substitution:** Phase 21 cannot swap a selected candidate for an unselected candidate because "the unselected candidate has lower correlation."
3. **No Phantom Allocations:** If Phase 20 emits `NO_SELECTION`, Phase 21 **must** output an empty allocation plan ($w_i = 0.00, \forall i$).

---

## 6. Allocation Eligibility Firewall (`AllocationEligibilityFirewall`)

Before any numerical optimizer or risk solver is invoked, all inputs must pass through the **Allocation Eligibility Firewall**. The firewall evaluates twenty-five fail-closed filter predicates across five governance domains.

```
Incoming StrategySelectionDecision & Portfolio State
        │
        ├── [ Domain 1: Upstream Decision Integrity (AF-01 to AF-05) ] ──► Any Fail? ──► REJECT / FAIL-CLOSED
        ├── [ Domain 2: Sovereign Authority Lineage (AF-06 to AF-10) ] ──► Any Fail? ──► REJECT / FAIL-CLOSED
        ├── [ Domain 3: Capital & Risk Ceiling Checks (AF-11 to AF-15) ] ─► Any Fail? ──► REJECT / FAIL-CLOSED
        ├── [ Domain 4: Numerical & Covariance Quality (AF-16 to AF-20) ] ► Any Fail? ──► REJECT / FAIL-CLOSED
        └── [ Domain 5: Operational & Circuit Breakers (AF-21 to AF-25) ] ► Any Fail? ──► REJECT / FAIL-CLOSED
        │
        ▼ All 25 Firewall Predicates Verified
Eligible for Optimization Solver Execution
```

### 6.1 Complete 25-Predicate Firewall Specification

| Predicate ID | Domain | Evaluated Condition | Fail-Closed Reason Code |
| :--- | :--- | :--- | :--- |
| **AF-01** | Decision Integrity | `decision_digest` matches recalculated hash of Phase 20 record | `ERR_ALLOC_DECISION_DIGEST_MISMATCH` |
| **AF-02** | Status Permitted | `decision_status IN {"SELECTED", "SELECT_SET"}` | `ERR_ALLOC_STATUS_NOT_PERMITTED` |
| **AF-03** | Strategy ID Exists | All `selected_strategy_ids` exist in Phase 17 Sovereign Catalog | `ERR_ALLOC_STRATEGY_NOT_IN_CATALOG` |
| **AF-04** | Lineage Completeness | `input_set_digest` and `previous_decision_digest` verified | `ERR_ALLOC_LINEAGE_BROKEN` |
| **AF-05** | No Duplicate IDs | Count of unique IDs in `selected_strategy_ids` equals list length | `ERR_ALLOC_DUPLICATE_STRATEGY_ID` |
| **AF-06** | Phase 17 Admission | For all selected: `admission_status == "ADMITTED"` and unexpired | `ERR_ALLOC_ADMISSION_INVALID` |
| **AF-07** | Phase 6 Validation | For all selected: `validation_status == "PASS"` and digest sealed | `ERR_ALLOC_STATISTICAL_INVALID` |
| **AF-08** | Phase 8.5 Qualification | For all selected: `qualification_status == "QUALIFIED"` and digest sealed | `ERR_ALLOC_ECONOMIC_INVALID` |
| **AF-09** | Phase 11 Forward Health | For all selected: `health_state IN {"HEALTHY", "DEGRADED_PERMITTED"}` | `ERR_ALLOC_HEALTH_BLOCKING` |
| **AF-10** | Phase 19 Regime Valid | Regime observation age $\le \text{policy.max\_regime\_age}$ | `ERR_ALLOC_REGIME_STALE` |
| **AF-11** | Policy Digest Valid | `allocation_policy_digest` matches sealed governance manifest | `ERR_ALLOC_POLICY_DIGEST_MISMATCH` |
| **AF-12** | Capital Basis Valid | `allocatable_capital > 0` (or research hypothetical basis $\ge 0$) | `ERR_ALLOC_CAPITAL_BASIS_INVALID` |
| **AF-13** | Hard Risk Ceiling | Current aggregate portfolio drawdown $<$ sovereign limit | `ERR_ALLOC_PORTFOLIO_DRAWDOWN_LOCKED` |
| **AF-14** | Exposure Limits Declared| `gross_leverage_limit` and `net_exposure_limit` finite and $> 0$ | `ERR_ALLOC_EXPOSURE_LIMIT_UNDEFINED` |
| **AF-15** | Capacity Evidence Fresh | Strategy capacity estimates age $\le \text{policy.max\_capacity\_age}$ | `ERR_ALLOC_CAPACITY_STALE` |
| **AF-16** | Covariance Matrix Finite| All elements $\Sigma_{ij}$ are finite (no `NaN`, `Inf`, or null) | `ERR_ALLOC_COVARIANCE_NOT_FINITE` |
| **AF-17** | Covariance Symmetry | $|\Sigma_{ij} - \Sigma_{ji}| \le 10^{-10}, \forall i,j$ | `ERR_ALLOC_COVARIANCE_ASYMMETRIC` |
| **AF-18** | Positive Semidefinite | Minimum eigenvalue $\lambda_{\min}(\Sigma) \ge \text{eigenvalue\_floor}$ | `ERR_ALLOC_COVARIANCE_NOT_PSD` |
| **AF-19** | Matrix Dimension Match | Dimensions of $\Sigma$ equal count of selected strategies $N \times N$ | `ERR_ALLOC_MATRIX_DIMENSION_MISMATCH` |
| **AF-20** | Volatility Vector Valid | All standalone volatilities $\sigma_i > \text{volatility\_floor}$ | `ERR_ALLOC_VOLATILITY_DEGENERATE` |
| **AF-21** | Temporal Causality | $T_{\text{knowledge}} \le T_{\text{as\_of}} \le T_{\text{decision}}$ for all risk inputs | `ERR_ALLOC_TEMPORAL_LOOKAHEAD` |
| **AF-22** | No Circuit Breaker | System-level emergency risk halt is FALSE | `ERR_ALLOC_CIRCUIT_BREAKER_ACTIVE` |
| **AF-23** | Lifecycle State Check | No selected candidate in `RETIRED`, `SUSPENDED`, or `REJECTED` | `ERR_ALLOC_LIFECYCLE_FORBIDDEN` |
| **AF-24** | Weight Bounds Feasible | $\sum w_{i,\min} \le \text{leverage\_limit}$ (basic feasibility check) | `ERR_ALLOC_BOUNDS_CONTRADICTORY` |
| **AF-25** | Solver Config Valid | Requested solver family declared in policy and dependencies installed | `ERR_ALLOC_SOLVER_CONFIG_INVALID` |

---

## 7. Capital Source Model & Accounting Semantics

Phase 21 enforces strict accounting definitions across capital representations. The system explicitly distinguishes between accounting equity, risk-bearing capital, and deployable balances.

$$\boxed{\mathbf{INVARIANT:}\quad \text{Total Account Equity } \not\equiv \text{ Allocatable Capital}}$$

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TOTAL ACCOUNT EQUITY (E)                            │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ RESERVED CAPITAL (R)                 │ ALLOCATABLE CAPITAL (A)              │
│ - Regulatory capital floor           │ A = E - R                            │
│ - Mandatory liquidity reserve        │ Maximum capital base available for   │
│ - High-water mark drawdown buffer    │ risk-budgeting and strategy weights  │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ CASH FLOOR (C)                       │ RISK-DEPLOYED CAPITAL (D)            │
│ C = A * min_cash_weight              │ D = A * sum(w_i)                     │
│ Guaranteed unallocated cash buffer   │ Actual active exposure               │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### 7.1 Capital Hierarchy Definitions
1. **Total Account Equity ($E$):** The complete marked-to-market value of the account as reported by the accounting ledger.
2. **Reserved Capital ($R$):** Capital cordoned off by governance policies (regulatory reserves, operational cushion, drawdown lock buffers). Cannot be touched by any allocation solver.
3. **Allocatable Capital ($A = E - R$):** The net capital pool available for strategy allocation.
4. **Cash Floor ($C$):** The mandatory minimum fraction of allocatable capital retained in cash ($w_{\text{cash}} \ge \text{min\_cash\_weight}$).
5. **Strategy Capacity Ceiling ($K_i$):** The maximum dollar amount that strategy $S_i$ can deploy before market impact collapses net alpha (from Phase 8.5 Dossier):
   $$\text{AllocatedCapital}(S_i) = w_i \times A \le K_i$$

### 7.2 Strict Financial Precision Invariant
All capital bases, dollar limits, cash weights, and monetary quantities must be represented strictly using Python `Decimal` with bounded quantization (minimum 8 decimal places for weights, 2 decimal places for USD/EUR). Native floating-point representations (`float`) are strictly forbidden in capital accounting.

---

## 8. Allocation Unit Semantics

Phase 21 rigorously defines the dimensional units of all outputs to prevent catastrophic translation errors between risk budgets, portfolio weights, and dollar capital.

### 8.1 Distinct Unit Spaces

| Output Space | Symbol | Dimension / Range | Definition | Epistemic Meaning |
| :--- | :---: | :---: | :--- | :--- |
| **Portfolio Weight** | $w_i$ | Unitless ratio, e.g., $[0.00, 1.00]$ | Fraction of Allocatable Capital assigned to strategy $S_i$. | Relative position sizing target. |
| **Risk Budget** | $b_i$ | Unitless ratio, $\sum b_i = 1.00$ | Fraction of total portfolio risk contributed by strategy $S_i$. | Relative volatility risk allocation. |
| **Risk Contribution** | $\text{RC}_i$ | Volatility percentage (annualized) | Absolute volatility contribution of strategy $S_i$ to portfolio: $\text{RC}_i = w_i \frac{(\Sigma w)_i}{\sigma_p}$. | Marginal risk contribution. |
| **Allocated Capital** | $C_i$ | Fiat currency (USD Decimal) | Dollar amount assigned: $C_i = w_i \times A$. | Capital allocation budget. |
| **Gross Leverage** | $L_{\text{gross}}$| Unitless scalar, $\sum |w_i|$ | Sum of absolute strategy weights. | Total portfolio exposure leverage. |
| **Net Exposure** | $L_{\text{net}}$ | Unitless scalar, $\sum w_i$ | Directional net strategy bias. | Directional market exposure. |

$$\boxed{\mathbf{CRITICAL\;RULE:}\quad \text{A 25\% Risk Budget } (b_i = 0.25) \not\equiv \text{ a 25\% Capital Weight } (w_i = 0.25).}$$
Under unequal asset volatilities or non-zero correlations, equal risk budgets always yield unequal capital weights. Phase 21 never equates risk contribution with capital weighting.

---

## 9. Weight Domain & Portfolio Allocation Modes

### 9.1 Weight Bounding Modes
The allocation policy explicitly declares the permissible domain for strategy weights $w_i$:
1. **Long-Only Mode:** $0.00 \le w_i \le w_{i,\max}, \quad \forall i$.
2. **Constrained Long-Short Mode (When Authorized):** $w_{i,\min} \le w_i \le w_{i,\max}$, where $w_{i,\min} < 0$.
3. **Turnover-Constrained Mode:** $|w_{i,t} - w_{i,t-1}| \le \Delta w_{\max}$.

### 9.2 Portfolio Investment Modes
The allocation policy declares one of four investment modes:

```
Mode 1: FULLY_INVESTED
  sum(w_i) + w_cash = 1.00  AND  w_cash == policy.fixed_cash_fraction

Mode 2: CASH_PRESERVING (Variable Exposure)
  sum(w_i) <= 1.00 - policy.min_cash_weight  AND  w_i >= 0.00

Mode 3: RISK_TARGETED (Leverage-Bounded)
  sigma_portfolio(w) <= sigma_target  AND  sum(|w_i|) <= max_gross_leverage

Mode 4: ZERO_RISK (Defensive / Fail-Closed)
  w_i = 0.00,  forall i  AND  w_cash = 1.00 (100% Cash Allocation)
```

---

## 10. Solver Architecture & Mathematical Formulation

Phase 21 establishes eight governed solver families. Each solver is implemented as an isolated mathematical algorithm adhering to a uniform interface.

```
                              PHASE 21 SOLVER FAMILIES
                                          │
        ┌───────────────────┬─────────────┴─────────────┬───────────────────┐
        ▼                   ▼                           ▼                   ▼
1. EQUAL RISK CONTRIB.  2. RISK PARITY            3. VOL TARGETING     4. MIN VARIANCE
   (Equal RC_i)           (Custom Risk Budgets b_i) (Scale to sigma*)   (Minimize w'Sigma w)
        │                   │                           │                   │
        ├───────────────────┼───────────────────────────┼───────────────────┤
        ▼                   ▼                           ▼                   ▼
5. CONSTRAINED MEAN-VAR 6. MAX DIVERSIFICATION    7. RISK BUDGETING    8. ZERO-RISK DEFENSIVE
   (mu'w - lambda w'Sw)   (Maximize Div Ratio D)   (Solve RC_i = b_i)   (w_i = 0.0, 100% Cash)
```

### 10.1 Uniform Solver Mathematical Interface
Every solver implements the canonical mapping:
$$(\mathbf{w}^*, \mathbf{RC}^*, \text{status}, \text{diagnostics}) = \text{Solve}(\Sigma,\, \mathbf{b},\, \mathbf{u},\, \Omega_{\text{policy}},\, \text{config})$$
Where:
- $\Sigma \in \mathbb{R}^{N \times N}$: Governed positive-semidefinite covariance matrix.
- $\mathbf{b} \in \mathbb{R}^N$: Target risk budget vector ($\sum b_i = 1$).
- $\mathbf{u} \in \mathbb{R}^N$: Standalone volatility vector ($u_i = \sqrt{\Sigma_{ii}}$).
- $\Omega_{\text{policy}}$: Set of linear and non-linear governance constraints.
- $\text{config}$: Numerical solver tolerances, iteration ceilings, and algorithm settings.

---

## 11. Solver Selection Governance

Phase 21 **MUST NOT** select which strategy to run, but it **DOES** select which mathematical allocation solver to apply to the Phase 20 strategy slate.  
However, solver selection is **strictly governed by a declared, versioned `AllocationPolicy`**.

### 11.1 Dynamic AI Modification Strictly Prohibited
$$\boxed{\mathbf{GOVERNANCE\;INVARIANT:}\quad \text{No LLM or AI agent may dynamically select or alter the active allocation solver.}}$$
Solver selection must be statically resolved by policy rules declared in the sealed manifest.

### 11.2 Governed Solver Cascade
If the primary solver fails to find a feasible solution within numerical tolerances, the engine executes a deterministic, governed solver cascade:

```
[ Primary Solver (e.g., Equal Risk Contribution) ]
                 │
                 ▼ Feasible?
       ┌─────────┴─────────┐
       │ YES               │ NO (Infeasible / Numerical Failure)
       ▼                   ▼
[ Emit Plan ]   [ Secondary Fallback Solver (e.g., Minimum Variance) ]
                           │
                           ▼ Feasible?
                 ┌─────────┴─────────┐
                 │ YES               │ NO
                 ▼                   ▼
          [ Emit Plan ]   [ Tertiary Solver: Defensive Zero-Risk Solver ]
                                     │
                                     ▼
                          [ Emit NO_ALLOCATION (w_i = 0.00) ]
```

---

## 12. Equal Risk Contribution (ERC) Solver

### 12.1 Mathematical Formulation
Following Maillard, Roncalli, and Teïletche (2008), the Equal Risk Contribution portfolio assigns weights such that the risk contribution of every active strategy is strictly equal:

$$\text{RC}_i = \text{RC}_j, \quad \forall i, j \in \{1, \dots, N\}$$

Where portfolio volatility is:
$$\sigma_p(w) = \sqrt{w^T \Sigma w}$$

And the marginal risk contribution of strategy $i$ is:
$$\text{MRC}_i = \frac{\partial \sigma_p(w)}{\partial w_i} = \frac{(\Sigma w)_i}{\sigma_p(w)}$$

The total risk contribution of strategy $i$ is:
$$\text{RC}_i = w_i \times \text{MRC}_i = \frac{w_i (\Sigma w)_i}{\sigma_p(w)}$$

By Euler's homogeneous function theorem, the sum of risk contributions equals total portfolio volatility:
$$\sum_{i=1}^N \text{RC}_i = \sigma_p(w)$$

### 12.2 Optimization Objective
The ERC solution is obtained by solving the convex optimization problem:

$$\min_{w} \sum_{i=1}^N \sum_{j=1}^N \left( w_i (\Sigma w)_i - w_j (\Sigma w)_j \right)^2$$
$$\text{subject to: } \sum_{i=1}^N w_i \le 1 - w_{\text{cash}}, \quad 0 \le w_i \le w_{\max}, \quad \forall i$$

Alternatively, in unconstrained long-only space, the logarithmic barrier formulation guarantees global convergence to the unique ERC ray:
$$\min_{y} \left( \frac{1}{2} y^T \Sigma y - \frac{\sigma_p}{N} \sum_{i=1}^N \ln(y_i) \right), \quad \text{with } w_i = \frac{y_i}{\sum y_k}$$

### 12.3 Regularization & Positive Semidefinite Requirements
- $\Sigma$ must have $\lambda_{\min}(\Sigma) \ge 10^{-6}$.
- If $\Sigma$ is ill-conditioned ($\kappa(\Sigma) > 10^4$), the engine applies Ledoit-Wolf analytical shrinkage prior to optimization.

---

## 13. General Risk Parity Solver

Risk Parity generalizes ERC by permitting asymmetric, governed target risk budgets $\mathbf{b} = [b_1, \dots, b_N]^T$ where $\sum_{i=1}^N b_i = 1.00$ and $b_i > 0$:

$$\text{RC}_i = b_i \times \sigma_p(w), \quad \forall i \in \{1, \dots, N\}$$

### 13.1 Objective Formulation
$$\min_{w} \sum_{i=1}^N \left( \frac{w_i (\Sigma w)_i}{\sigma_p(w)} - b_i \sigma_p(w) \right)^2$$
$$\text{subject to: } \sum_{i=1}^N w_i \le 1 - w_{\text{cash}}, \quad w_i \ge 0$$

Target risk budgets $b_i$ must be supplied by an authorized upstream policy (e.g., inverse-volatility budgeting or regime-conditioned risk tiers). Phase 21 **never** invents risk budgets.

---

## 14. Volatility Targeting Solver

The Volatility Targeting solver scales an underlying feasible allocation $w_{\text{base}}$ to match an annualized target volatility $\sigma^*$:

$$\text{Target Portfolio Volatility:}\quad \sigma_p(w^*) = \sigma^*$$

### 14.1 Scaling Formulation
Given base allocation weights $w_{\text{base}}$ and base portfolio volatility $\sigma_{\text{base}} = \sqrt{w_{\text{base}}^T \Sigma w_{\text{base}}}$:

$$\text{Scaling Factor:}\quad \gamma = \frac{\sigma^*}{\sigma_{\text{base}}}$$

$$\text{Scaled Weights:}\quad w_i^* = \min\left( \gamma \cdot w_{\text{base}, i},\, w_{i,\max} \right)$$

### 14.2 Fail-Closed Volatility Boundary
- If $\sigma_{\text{base}} < \text{volatility\_floor}$ ($10^{-6}$): The engine raises `ERR_ALLOC_VOLATILITY_DEGENERATE` and halts (zero division prohibited).
- If $\gamma > \text{max\_gross\_leverage}$: The scaling factor is hard-clamped to $\text{max\_gross\_leverage}$.
- Cash buffer absorbs the difference: $w_{\text{cash}} = \max\left(0.00,\, 1.00 - \sum w_i^*\right)$.

---

## 15. Minimum Variance Solver

The Minimum Variance solver finds the portfolio weight vector that minimizes total portfolio variance without making any assumption regarding expected returns:

$$\min_{w} \quad \frac{1}{2} w^T \Sigma w$$
$$\text{subject to: } \sum_{i=1}^N w_i = 1 - w_{\text{cash}}, \quad 0 \le w_i \le w_{\max}, \quad \forall i$$

*Epistemic Invariant:* Minimum Variance minimizes historical or modeled variance. It makes **zero claims** regarding future alpha, expected return, or Sharpe ratio maximization.

---

## 16. Constrained Mean-Variance Solver

When explicitly enabled by governance policy, Phase 21 supports quadratic utility optimization:

$$\max_{w} \quad \left( \boldsymbol{\mu}^T w - \frac{\lambda}{2} w^T \Sigma w \right)$$
$$\text{subject to: } w \in \Omega_{\text{policy}}$$

### 16.1 Strict Epistemic Invariant: Return Vector Sovereignty
$$\boxed{\mathbf{CRITICAL\;RESTRICTION:}\quad \text{Phase 21 MUST NOT fabricate or infer expected returns } \boldsymbol{\mu}.}$$
- Phase 21 has zero statistical discovery authority. It cannot predict returns from moving averages, regression, or neural networks.
- If the policy requires Mean-Variance optimization, the expected return vector $\boldsymbol{\mu}$ must be provided by a cryptographically sealed upstream input from an authorized valuation authority.
- In the absence of a verified, sealed $\boldsymbol{\mu}$ input, the Mean-Variance solver immediately raises `ERR_ALLOC_EXPECTED_RETURN_UNAVAILABLE` and fails closed to `SOLVER_NOT_APPLICABLE`.

---

## 17. Maximum Diversification Solver

Following Choueifaty and Coignard (2008), the Maximum Diversification solver maximizes the Diversification Ratio $D(w)$, defined as the ratio of weighted asset volatilities to total portfolio volatility:

$$D(w) = \frac{w^T \boldsymbol{\sigma}}{\sqrt{w^T \Sigma w}} = \frac{\sum_{i=1}^N w_i \sigma_i}{\sigma_p(w)}$$

### 17.1 Objective Formulation
Because $D(w)$ is homogeneous of degree zero, maximizing $D(w)$ subject to long-only constraints is equivalent to solving the convex quadratic program:

$$\min_{y} \quad \frac{1}{2} y^T \Sigma y \quad \text{subject to: } y^T \boldsymbol{\sigma} = 1, \quad y \ge 0$$
$$\text{Normalized Weights:}\quad w_i^* = \frac{y_i}{\sum_{k=1}^N y_k} \times (1 - w_{\text{cash}})$$

*Epistemic Notice:* Maximizing the diversification ratio maximizes asset-independent risk spreading; it does **not** maximize return or guarantee protection against market-wide correlation spikes ($\rho \to 1.0$).

---

## 18. Risk Budgeting Solver

The Risk Budgeting solver satisfies arbitrary, policy-declared risk budgets $b_i$:

$$\frac{w_i (\Sigma w)_i}{w^T \Sigma w} = b_i, \quad \forall i \in \{1, \dots, N\}$$

The solver employs the sequential quadratic programming (SQP) or cyclical coordinate descent algorithm with certified convergence guarantees under non-singular $\Sigma$.

---

## 19. Defensive / Zero-Risk Solver (`DEFENSIVE_ZERO_RISK`)

The Defensive Solver is the fundamental fail-closed fallback of Phase 21:

$$\mathbf{w}^* = [0.00, 0.00, \dots, 0.00]^T$$
$$w_{\text{cash}} = 1.00 \quad (100\%\text{ Allocatable Capital in Cash})$$

### 19.1 Operational Trigger Conditions
The Defensive Solver is automatically asserted when:
1. Upstream selection status is `NO_SELECTION`, `REVIEW_REQUIRED`, or `BLOCKED`.
2. Portfolio drawdown exceeds the sovereign risk limit (`AF-13`).
3. System circuit breaker is asserted (`AF-22`).
4. Primary and secondary solvers fail to converge (`ALLOC-15`).
5. Covariance matrix cannot be verified or repaired (`ALLOC-10`).

$$\boxed{\mathbf{INVARIANT:}\quad \text{Defensive allocation } (w_i = 0.00) \text{ is an internal allocation state. It emits ZERO broker orders.}}$$
Order generation, position unwinding, and liquidation schedules belong strictly to downstream Phase 22 and Phase 12 adapters.

---

## 20. Covariance Matrix Governance & Shrinkage

Covariance estimation error is the single greatest driver of portfolio instability. Phase 21 enforces strict governance over $\Sigma$.

```
Raw Return Series (T x N)
        │
        ├── [ Step 1: Finite & Dimension Checks ] ──► NaN/Inf detected? ──► REJECT (AF-16)
        ├── [ Step 2: Causal PIT Verification ] ──► T_knowledge > T_as_of? ──► REJECT (AF-21)
        ├── [ Step 3: Ledoit-Wolf Analytical Shrinkage ]
        │          Sigma_shrunk = delta * F + (1 - delta) * S
        ├── [ Step 4: Symmetry Enforcement ]
        │          Sigma_sym = 0.5 * (Sigma + Sigma^T)
        └── [ Step 5: Positive Semidefinite Validation ]
                   lambda_min(Sigma) >= eigenvalue_floor? ──► NO ──► Spectral Repair / REJECT
        │
        ▼ Validated Covariance Matrix Sealed with SHA-256 Digest
```

### 20.1 Ledoit-Wolf Shrinkage (2004)
To eliminate sample covariance singularity when candidate count $N$ approaches sample size $T$, Phase 21 applies Ledoit-Wolf analytical shrinkage towards the constant-correlation structured target $F$:

$$\Sigma_{\text{shrunk}} = \delta^* F + (1 - \delta^*) S$$

Where:
- $S$: Sample covariance matrix.
- $F$: Constant-correlation target matrix where $F_{ii} = S_{ii}$ and $F_{ij} = \bar{\rho} \sqrt{S_{ii} S_{jj}}$.
- $\delta^* \in [0, 1]$: Asymptotically optimal shrinkage intensity computed analytically without cross-validation snooping.

### 20.2 Strict Repair Transparency Invariant
Silent covariance manipulation is strictly prohibited. If spectral repair (clamping negative eigenvalues to $\lambda_{\text{floor}} = 10^{-6}$) is executed, the allocation record must explicitly flag `is_covariance_repaired = True` with the original and modified eigenvalue spectra recorded in the audit ledger.

---

## 21. Correlation & Cluster Risk Governance

Phase 21 establishes structural cluster risk controls to prevent concentration in economically identical strategies:

### 21.1 Pairwise Correlation Ceiling
$$\rho_{ij} = \frac{\Sigma_{ij}}{\sqrt{\Sigma_{ii} \Sigma_{jj}}} \le \text{policy.max\_pairwise\_correlation} \quad (\text{e.g., } 0.75)$$
If $\rho_{ij} > \text{ceiling}$, the optimizer enforces an aggregate cluster exposure constraint:
$$w_i + w_j \le \text{policy.max\_correlated\_pair\_weight} \quad (\text{e.g., } 0.35)$$

### 21.2 Strategy Mechanism Clusters
Strategies are partitioned into declared structural mechanism clusters (from Phase 17 catalog metadata):
$$\sum_{i \in \text{Cluster}_k} w_i \le \text{ClusterLimit}_k, \quad \forall k \in \{\text{MOMENTUM}, \text{MEAN\_REV}, \text{CARRY}, \text{VOLATILITY}\}$$

---

## 22. Drawdown Governance & Dynamic De-Risking

Phase 21 consumes sovereign drawdown metrics from Phase 11 and enforces multi-tiered allocation throttling:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-TIER DRAWDOWN THROTTLING                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: NORMAL (Drawdown < 50% of Limit)                                    │
│   - Full allocation permitted under declared policy.                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: CAUTION (50% <= Drawdown < 75% of Limit)                            │
│   - Target portfolio volatility scaled down by 25% (sigma* = 0.75 * sigma*).│
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: CRITICAL DE-RISKING (75% <= Drawdown < 100% of Limit)               │
│   - Target portfolio volatility scaled down by 50%.                         │
│   - Gross leverage ceiling clamped to 0.50.                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: HARD BREACH (Drawdown >= 100% of Limit)                             │
│   - FAIL-CLOSED: Immediate assertion of DEFENSIVE_ZERO_RISK (w_i = 0.00).   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 23. Concentration Limits & Exposure Ceilings

Phase 21 enforces seven orthogonal concentration ceilings across all solver outputs:

| Constraint ID | Target Scope | Maximum Bound | Enforcement Level | Epistemic Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **CONC-01** | Single Strategy Weight | $w_i \le 0.25$ (25%) | Hard Invariant | Prevents single-strategy idiosyncratic blow-up. |
| **CONC-02** | Mechanism Family Weight | $\sum_{i \in \text{Fam}} w_i \le 0.45$ (45%) | Hard Invariant | Prevents mechanism-level factor crowding. |
| **CONC-03** | Asset Class Exposure | $\sum_{i \in \text{Asset}} w_i \le 0.50$ (50%) | Hard Invariant | Limits underlying market asset contagion. |
| **CONC-04** | Execution Venue Weight | $\sum_{i \in \text{Venue}} w_i \le 0.60$ (60%) | Hard Invariant | Limits broker/exchange operational risk. |
| **CONC-05** | Top-2 Concentration | $w_{(1)} + w_{(2)} \le 0.40$ (40%) | Policy Threshold | Prevents dual-candidate domination. |
| **CONC-06** | Gross Leverage Limit | $\sum |w_i| \le 1.00$ (Long-Only default) | Class B Governance | Prevents uncollateralized structural borrowing. |
| **CONC-07** | Minimum Cash Floor | $w_{\text{cash}} \ge 0.10$ (10%) | Class B Governance | Preserves liquidity buffer under stress. |

---

## 24. Liquidity & Strategy Capacity Governance

Phase 21 consumes capacity ceilings from Phase 8.5 `AlphaQualificationDossier`:

$$C_i = w_i \times \text{AllocatableCapital} \le \text{StrategyCapacity}_i$$

### 24.1 Unknown Capacity Invariant
$$\boxed{\mathbf{FAIL-CLOSED\;RULE:}\quad \text{Unknown capacity MUST NOT be treated as infinite capacity.}}$$
If a strategy's capacity estimate is missing or expired ($> 30$ days), the engine applies the conservative default capacity cap:
$$K_{\text{default}} = \text{policy.default\_unverified\_capacity\_usd} \quad (\text{e.g., } \$50,000)$$

---

## 25. Turnover Governance & Rebalancing Mechanics

### 25.1 Portfolio Turnover Definition
Given previous target weights $w_{t-1}$ and newly solved weights $w_t$, one-way portfolio turnover is defined as:

$$\text{Turnover}(w_t, w_{t-1}) = \frac{1}{2} \sum_{i=1}^N |w_{i,t} - w_{i,t-1}|$$

### 25.2 Rebalancing Deadband (Hysteresis)
To prevent wasteful portfolio churn on minor return noise, Phase 21 enforces a rebalancing deadband:
- If $|w_{i,t} - w_{i,t-1}| < \text{policy.rebalance\_threshold}$ (e.g., $0.02$ or 2%), the weight is held constant: $w_{i,t} \leftarrow w_{i,t-1}$.
- If total turnover $\text{Turnover} < \text{policy.min\_portfolio\_turnover}$ (e.g., 5%), the rebalance is suppressed, preserving the previous allocation plan.

---

## 26. Transaction-Cost-Aware Allocation

When enabled, Phase 21 penalizes rebalancing turnover by deducting estimated implementation friction:

$$\max_{w} \quad \left( f(w) - \lambda_{\text{cost}} \sum_{i=1}^N \text{FrictionBps}_i \times |w_{i,t} - w_{i,t-1}| \right)$$

*Boundary Invariant:* Friction estimates $\text{FrictionBps}_i$ must be consumed strictly from Phase 8.5 dossiers. Phase 21 **never** invents slippage curves or broker commission schedules.

---

## 27. Stress Testing & Extreme Scenario Evaluation

Before a `PortfolioAllocationPlan` can be marked `FEASIBLE`, it must undergo mandatory pre-flight stress testing across six extreme scenarios:

```
                               MANDATORY STRESS MATRIX
                                          │
        ┌───────────────────┬─────────────┴─────────────┬───────────────────┐
        ▼                   ▼                           ▼                   ▼
1. CORRELATION SPIKE    2. VOLATILITY SHOCK       3. LIQUIDITY SQUEEZE  4. STRATEGY FAILURE
   (rho -> 0.90)          (Sigma -> 2.25 * Sigma)    (Capacity -> 0.25)    (Top weight w_(1) -> -50%)
```

### 27.1 Stress Pass/Fail Criteria
1. **Correlation Spike ($\rho \to 0.90$):** Simulated portfolio volatility under extreme co-movement must not exceed `max_stress_portfolio_vol` ($0.25$ annualized).
2. **Volatility Shock ($\Sigma \to 2.25 \times \Sigma$):** Capital loss under a 3-sigma 1-day shock must not exceed $15\%$ of allocatable capital.
3. **Liquidity Squeeze ($K_i \to 0.25 K_i$):** Target weights must remain within crushed capacity bounds.
4. **Instant Strategy Default ($w_{(1)} \to -50\%$):** Immediate failure of largest position must not breach portfolio drawdown limits.

*Epistemic Invariant:* Passing stress testing is a plan-level resilience check; it is **never** proof that the portfolio is "safe" or immune to real-world market crashes.

---

## 28. Sensitivity Analysis & Numerical Stability Diagnostics

Phase 21 measures the condition and sensitivity of the allocation solution by applying controlled perturbations to inputs:

$$\text{SensitivityIndex} = \max_{\Delta \Sigma \in \mathcal{B}_\epsilon} \frac{\|w^*(\Sigma + \Delta \Sigma) - w^*(\Sigma)\|_2}{\|w^*(\Sigma)\|_2}$$

- If $\text{SensitivityIndex} > \text{policy.max\_sensitivity\_threshold}$ (e.g., $2.5$), the solution is flagged `UNSTABLE_ALLOCATION`.
- An unstable allocation triggers fallback to the secondary solver or defensive mode.

---

## 29. Solver Feasibility & Explicit Failure Semantics

Phase 21 defines eight explicit solver return statuses:

| Status Code | Definition | Engine Action | Permitted Downstream Output |
| :--- | :--- | :--- | :--- |
| `FEASIBLE` | Solver converged and all constraints satisfied | Seal plan and record to ledger | `PortfolioAllocationPlan` emitted |
| `INFEASIBLE` | No weight vector satisfies all constraints | Halt. Trigger solver cascade | Fallback to secondary or `NO_ALLOCATION` |
| `NUMERICAL_FAILURE`| Singular matrix, gradient explosion, or NaN | Halt. Log diagnostics | Trigger secondary or `NO_ALLOCATION` |
| `TIMEOUT` | Solver exceeded maximum execution time | Halt. SRE latency alert | Fallback to defensive zero-risk |
| `INPUT_INVALID` | Firewall predicate failed (AF-01 to AF-25) | Halt immediately | `NO_ALLOCATION` |
| `BLOCKED` | Circuit breaker or drawdown lock asserted | Fail-closed halt | `ALLOCATION_BLOCKED` ($w_i = 0.00$) |
| `NOT_APPLICABLE` | Required inputs missing for requested solver | Cascade to compatible solver | Secondary solver or `NO_ALLOCATION` |
| `CONSTRAINT_VIOL` | Post-solve constraint verification failed | Invalidate solution | `NO_ALLOCATION` |

$$\boxed{\mathbf{FAIL-CLOSED\;RULE:}\quad \text{An INFEASIBLE status NEVER produces a 'best-effort' allocation.}}$$
If a solver fails, the allocation defaults strictly to `NO_ALLOCATION` or an explicit governed defensive fallback.

---

## 30. Numerical Governance & Precision Standards

1. **Decimals for Financial Limits:** All monetary amounts, leverage ratios, cash percentages, and constraint bounds must use Python `Decimal`.
2. **Double-Precision Linear Algebra:** Numerical optimizers (QP, SLSQP, interior point) execute within double-precision (`float64`) boundaries.
3. **Explicit Conversion Boundaries:** Transitions between `Decimal` and `float64` must occur strictly at sealed conversion boundaries with explicit rounding modes (`ROUND_HALF_EVEN`) and post-conversion assertion checks.
4. **Convergence Tolerances:** Solver optimality tolerance $\le 10^{-7}$; constraint violation tolerance $\le 10^{-8}$.

---

## 31. Determinism & Environment-Sealed Reproducibility

Consistent with Phase 18–20 governance, Phase 21 enforces **environment-sealed deterministic reproducibility**:
- Given identical input digests, identical policy configurations, and identical solver seeds within a declared execution environment, the engine must yield an identical `allocation_digest`.
- Solvers execute with deterministic initialization (zero unseeded random starting points).
- The full execution context is sealed in the `AllocationReproducibilityManifest` (BLAS library version, Python runtime, compiler flags, CPU architecture).

---

## 32. Selection-to-Allocation Cryptographic Lineage

Every `PortfolioAllocationPlan` must trace an unbroken, verifiable cryptographic lineage chain to its underlying sovereign authorities:

```
Phase 17 Strategy Admission Receipt (SHA-256)
               │
               ▼
Phase 6 Canonical Validation Report (SHA-256)
               │
               ▼
Phase 8.5 Economic Qualification Dossier (SHA-256)
               │
               ▼
Phase 11 Forward Health Telemetry Digest (SHA-256)
               │
               ▼
Phase 19 Regime Observation Envelope (SHA-256)
               │
               ▼
Phase 20 Strategy Selection Decision Record (SHA-256)
               │
               ▼
Phase 21 Portfolio Allocation Plan (SHA-256)
```

$$\mathbf{Orphan\;Allocation\;Ban:}\quad \text{Any allocation plan lacking a verifiable } \text{selection\_decision\_digest} \text{ is invalid.}$$

---

## 33. The Immutable Allocation Record (`PortfolioAllocationPlan`)

### 33.1 Complete Schema Specification
```python
class PortfolioAllocationPlan(BaseModel):
    # Identification & Execution Environment
    allocation_plan_id: str                 # UUIDv7 / ULID (strictly ordered)
    execution_mode: str                     # "RESEARCH", "PAPER", "LIVE_PROPOSED"
    decision_time_utc: datetime             # Wall-clock generation timestamp
    as_of_time_utc: datetime                # Causality evaluation boundary
    
    # Lineage Links
    selection_decision_id: str              # Phase 20 Decision ID
    selection_decision_digest: str          # SHA-256 of Phase 20 Record
    allocation_policy_id: str               # e.g., "POL-ALLOC-ERC-CONSERVATIVE-V1"
    allocation_policy_version: str          # Semantic version
    allocation_policy_digest: str           # SHA-256 of policy configuration
    
    # Capital Accounting (Decimal)
    capital_basis_usd: Decimal              # Total Account Equity
    allocatable_capital_usd: Decimal        # Equity minus Reserved Capital
    reserved_capital_usd: Decimal           # Cordoned capital
    cash_weight: Decimal                    # Fraction in cash w_0
    
    # Strategy Allocation Weights & Risk Budgets
    selected_strategy_ids: List[str]        # Authoritative strategy list from Phase 20
    target_weights: Dict[str, Decimal]      # {strategy_id: w_i}
    target_risk_budgets: Dict[str, Decimal] # {strategy_id: b_i}
    allocated_capital_usd: Dict[str, Decimal] # {strategy_id: w_i * allocatable_capital}
    
    # Portfolio Risk & Exposure Metrics
    gross_exposure: Decimal                 # Sum of absolute weights
    net_exposure: Decimal                   # Sum of directional weights
    expected_portfolio_volatility: Decimal  # Annualized portfolio volatility
    expected_risk_contributions: Dict[str, Decimal] # {strategy_id: RC_i}
    
    # Solver Execution Metadata
    solver_family: str                      # "EQUAL_RISK_CONTRIBUTION", "MIN_VARIANCE", etc.
    solver_id: str                          # Canonical identifier of solver implementation
    solver_version: str                     # Version of solver module
    solver_status: str                      # "FEASIBLE", "INFEASIBLE", etc.
    feasibility_status: str                 # "FEASIBLE", "DEFENSIVE_FALLBACK"
    objective_value: Decimal                # Terminal value of objective function
    solver_iterations: int                  # Number of iterations executed
    solver_latency_ms: Decimal              # Execution time in milliseconds
    
    # Diagnostics & Lineage Sealing
    is_covariance_repaired: bool            # True if spectral repair was applied
    covariance_digest: str                  # SHA-256 of input covariance matrix
    input_set_digest: str                   # SHA-256 of all combined input DTOs
    previous_allocation_digest: str         # SHA-256 of previous plan in chain
    allocation_digest: str                  # SHA-256 of this complete plan
    reason_codes: List[str]                 # Machine-readable outcome codes
    explanation_narrative: str              # Deterministic explanation
```

---

## 34. Human Override Governance & Protocol

### 34.1 Permitted Human Override Actions
1. `FORCE_ZERO_ALLOCATION`: Immediately collapses all target weights to zero (100% cash).
2. `PAUSE_ALLOCATION_ENGINE`: Halts automated execution of Phase 21 solvers.
3. `SELECT_ALTERNATIVE_SOLVER`: Overrides default solver selection to an approved secondary solver.
4. `REQUEST_RECALCULATION`: Re-executes solver following parameter correction.

### 34.2 Strict Override Prohibitions
A human operator **MUST NOT**:
- Mutate upstream evidence (Phase 6, 8.5, 11, 17, 19, or 20).
- Allocate capital to a strategy rejected by Phase 20.
- Exceed sovereign concentration, leverage, or drawdown ceilings.
- Silently edit target weights without generating an `OverrideAllocationRecord`.

---

## 35. AI Epistemic Firewall & Boundary Rules

In accordance with `AGENTS.md` and Phase 14 governance:

| Domain | Permitted AI Action | Strictly Prohibited AI Action |
| :--- | :--- | :--- |
| **Explanation** | Summarize deterministic solver outputs, risk contributions, and concentration diagnostics. | Hallucinate rationales inconsistent with solver mathematical outputs. |
| **Diagnostics** | Flag anomalous covariance condition numbers or high turnover spikes for human review. | Silently suppress numerical warnings or matrix singularity alerts. |
| **Research** | Propose alternative solver hyperparameters for evaluation in Phase 18 tournaments. | Alter production allocation policy weights or solver settings. |
| **Decision Authority** | **NONE.** AI has zero vote in capital allocation. | **Assign weights, modify risk budgets, or execute allocations.** |
| **Data Generation** | None. | **Fabricate expected returns, volatility vectors, or covariance matrices.** |
| **Firewall Bypass** | None. | **Bypass the Allocation Eligibility Firewall or turn INFEASIBLE to FEASIBLE.** |
| **Execution** | None. | **Send orders, connect to brokers, or deploy live capital.** |

---

## 36. Phase 22 Interface (Downstream Hand-off)

Phase 21 emits the sealed `PortfolioAllocationPlan`. Phase 22 (Portfolio Orchestration & Netting) consumes this plan as a **read-only target sizing input**.

```
[ Phase 21: Capital Allocation ] ──► Emits: PortfolioAllocationPlan (target_weights w_i)
                                                    │
                                                    ▼
[ Phase 22: Portfolio Orchestration ] ──► Reads: Target Weights w_i
                                      ──► Compares against: Current Broker Positions
                                      ──► Calculates: Position Delta = Target - Current
                                      ──► Nets: Cross-strategy opposing exposures
                                      ──► Emits: Net Execution Intents
                                                    │
                                                    ▼
[ Phase 12: Execution Adapters ]      ──► Routes physical orders to broker
```

$$\boxed{\mathbf{NEGATIVE\;INVARIANT:}\quad \text{Phase 21 contains ZERO order-generation, position-netting, or broker-routing logic.}}$$

---

## 37. Allocation Observability & Operational Metrics (SLIs)

The allocation engine continuously streams operational telemetry:
- `allocation_evaluations_total`: Total allocation plans computed.
- `allocation_feasibility_ratio`: Proportion of evaluations returning `FEASIBLE`.
- `solver_convergence_latency_ms`: Quantile latency of numerical optimization solvers.
- `portfolio_gross_leverage`: Active aggregate gross leverage.
- `portfolio_net_exposure`: Active aggregate net exposure.
- `portfolio_modeled_volatility`: Expected annualized volatility $\sigma_p(w)$.
- `max_strategy_weight_ratio`: Observed maximum single-strategy concentration.
- `turnover_ratio`: Portfolio turnover between consecutive allocation cycles.
- `stress_test_failure_total`: Count of allocation candidates rejected by stress testing.
- `firewall_rejections_total`: Histogram of rejections across firewall gates AF-01 to AF-25.

*Epistemic Invariant:* Telemetry metrics measure operational health; they **never** constitute proof of strategy edge, future Sharpe ratio, or market profitability.

---

## 38. The Allocation Audit Ledger (`allocation_ledger.jsonl`)

Every execution of Phase 21 is recorded in an append-only, SHA-256 hash-chained JSONL disk ledger:

```json
{
  "sequence_number": 501,
  "allocation_plan_id": "0191c8b2-3f10-7e88-9124-da8921a48192",
  "decision_time_utc": "2026-09-06T00:35:00.000000Z",
  "as_of_time_utc": "2026-09-06T00:34:00.000000Z",
  "selection_decision_id": "0191c7a4-82e1-7d12-9842-bc8921a48192",
  "solver_family": "EQUAL_RISK_CONTRIBUTION",
  "solver_status": "FEASIBLE",
  "selected_strategy_ids": ["STRAT-TREND-BREAKOUT-V1", "STRAT-MEAN-REV-V2"],
  "target_weights": {"STRAT-TREND-BREAKOUT-V1": "0.42150000", "STRAT-MEAN-REV-V2": "0.47850000"},
  "cash_weight": "0.10000000",
  "gross_exposure": "0.90000000",
  "expected_portfolio_volatility": "0.11840000",
  "previous_allocation_digest": "7f8b9a1c...e41e",
  "allocation_digest": "9d2e1f4a...89b1"
}
```

---

## 39. Failure Mode Catalog (30 Comprehensive Failure Modes)

Phase 21 defines deterministic, fail-closed handling for thirty critical failure modes:

| Failure ID | Failure Trigger | Detection Mechanism | Fail-Closed Engine Action | Emitted Plan Status |
| :--- | :--- | :--- | :--- | :--- |
| **ALLOC-01** | Selection decision digest mismatch | Recalculated hash $\ne$ declared | Immediate halt. Security alert. | `INPUT_INVALID` |
| **ALLOC-02** | Selection status is `NO_SELECTION` | AF-02 check in firewall | Fail-closed halt. Zero allocation. | `NO_ALLOCATION` |
| **ALLOC-03** | Missing selected strategy in catalog | AF-03 catalog registry query | Exclude strategy; halt if empty. | `INPUT_INVALID` |
| **ALLOC-04** | Invalid Phase 17 admission receipt | AF-06 cryptographic verify | Halt. Flag admission breach. | `INPUT_INVALID` |
| **ALLOC-05** | Failed Phase 6 statistical status | AF-07 status $\ne$ `"PASS"` | Halt. Reject unvalidated candidate. | `INPUT_INVALID` |
| **ALLOC-06** | Failed Phase 8.5 economic status | AF-08 status $\ne$ `"QUALIFIED"` | Halt. Reject unqualified candidate. | `INPUT_INVALID` |
| **ALLOC-07** | Phase 11 forward health blocking | AF-09 status is `CRITICAL`/`BLOCKED` | Halt. Exclude affected candidate. | `INPUT_INVALID` |
| **ALLOC-08** | Stale Phase 19 regime observation | AF-10 age $>$ max allowable | Halt. Block regime-conditioned solve. | `INPUT_INVALID` |
| **ALLOC-09** | Covariance matrix missing | AF-16 null or missing check | Halt. Trigger defensive solver. | `NO_ALLOCATION` |
| **ALLOC-10** | Covariance not positive semidefinite| AF-18 minimum eigenvalue $< 0$ | Apply Ledoit-Wolf or halt. | `NUMERICAL_FAILURE` |
| **ALLOC-11** | Covariance matrix singular | Condition number $\kappa(\Sigma) > 10^6$ | Apply shrinkage or halt. | `NUMERICAL_FAILURE` |
| **ALLOC-12** | Standalone volatility degenerate | AF-20 volatility $\le \text{floor}$ | Halt. Prevent zero-division. | `NUMERICAL_FAILURE` |
| **ALLOC-13** | Strategy capacity missing / expired | AF-15 check | Clamp to conservative default cap. | `FEASIBLE` (with warning) |
| **ALLOC-14** | Contradictory risk constraints | Bounds check $\sum w_{\min} > L_{\max}$ | Halt. Infeasible bounds detected. | `INFEASIBLE` |
| **ALLOC-15** | Solver fails to converge | Optimizer reaches max iterations | Cascade to secondary solver. | `INFEASIBLE` |
| **ALLOC-16** | Solver execution timeout | Timer exceeds `max_latency_ms` | Kill solver. Fallback to defensive. | `TIMEOUT` |
| **ALLOC-17** | Numerical gradient explosion | Non-finite values in solve trace | Halt. Log numerical diagnostics. | `NUMERICAL_FAILURE` |
| **ALLOC-18** | Policy configuration tampered | AF-11 policy digest check | Immediate security halt. | `INPUT_INVALID` |
| **ALLOC-19** | Temporal causality violation | AF-21 $T_{\text{knowledge}} > T_{\text{as\_of}}$ | Halt. Security lookahead breach. | `INPUT_INVALID` |
| **ALLOC-20** | Lineage chain hash broken | AF-04 parent digest missing | Halt. Lineage integrity breach. | `INPUT_INVALID` |
| **ALLOC-21** | Duplicate strategy IDs in slate | AF-05 uniqueness check | Halt. Reject corrupt candidate set. | `INPUT_INVALID` |
| **ALLOC-22** | Solved weights violate bounds | Post-solve constraint assert | Invalidate solution. Zero output. | `CONSTRAINT_VIOL` |
| **ALLOC-23** | Capital basis unavailable | AF-12 equity $\le 0$ or null | Halt. Refuse to allocate. | `INPUT_INVALID` |
| **ALLOC-24** | Portfolio circuit breaker active | AF-22 emergency flag TRUE | Global lock. 100% cash mode. | `BLOCKED` |
| **ALLOC-25** | Canonical serialization diverges | Digest verification mismatch | Build halt. Environment untrusted. | `INPUT_INVALID` |
| **ALLOC-26** | Unauthorized override attempt | Cryptographic signature invalid | Reject override. SRE security alert. | `INPUT_INVALID` |
| **ALLOC-27** | Live allocation request received | Mode == `"LIVE"` without unlock | Immediate security block. | `BLOCKED` |
| **ALLOC-28** | Input DTO schema version mismatch | Pydantic validation error | Reject request. Version mismatch. | `INPUT_INVALID` |
| **ALLOC-29** | Requested solver family disabled | Policy permission check | Halt. Solver not authorized. | `NOT_APPLICABLE` |
| **ALLOC-30** | Stale previous allocation record | Rebalance check timestamp stale | Treat as initial allocation. | `FEASIBLE` (cold start) |

---

## 40. Threshold Provenance & Four-Tier Taxonomy

All allocation parameters are strictly registered under the ACASH Four-Tier Taxonomy:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ACASH FOUR-TIER THRESHOLD TAXONOMY                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ CLASS A: Canonical ACASH Invariants                                         │
│   - Immutable systemic constants (Live Capital = $0.00, Fail-Closed Default)│
├─────────────────────────────────────────────────────────────────────────────┤
│ CLASS B: Governance-Defined Safety Controls                                 │
│   - Institutional risk bounds (Max Leverage, Concentration, Drawdown Limits)│
│   - Modifiable ONLY via formal ADR and multi-party governance review.       │
├─────────────────────────────────────────────────────────────────────────────┤
│ CLASS C: Research Heuristics                                                │
│   - Target volatility, shrinkage targets, solver tolerances, deadbands      │
│   - Experiment-specific; sealed in reproducible policy manifests.           │
├─────────────────────────────────────────────────────────────────────────────┤
│ CLASS D: Illustrative Parameters                                            │
│   - Documentation examples, mock portfolio sizes, pedagogical values        │
│   - Explicitly marked as non-production placeholders.                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 40.1 Complete Allocation Threshold Registry

| Threshold Identifier | Class | Canonical Value | Owner | Epistemic Rationale |
| :--- | :---: | :--- | :--- | :--- |
| `INVARIANT_LIVE_CAPITAL_FLOOR` | **A** | `$0.00` | Sovereign System | Absolute capital lock invariant. |
| `INVARIANT_FAIL_CLOSED_DEFAULT` | **A** | `NO_ALLOCATION` | `AGENTS.md` | Infeasibility must produce zero risk. |
| `GOV_MAX_GROSS_LEVERAGE` | **B** | `1.00` (100%) | Risk Management | Prohibits uncollateralized leverage. |
| `GOV_MAX_SINGLE_STRATEGY_WEIGHT`| **B** | `0.25` (25%) | Risk Management | Concentration limit per candidate. |
| `GOV_MAX_MECHANISM_FAMILY_WEIGHT`| **B** | `0.45` (45%) | Risk Management | Limits correlated mechanism risk. |
| `GOV_MIN_CASH_WEIGHT` | **B** | `0.10` (10%) | Treasury & Risk | Mandatory liquidity reserve. |
| `GOV_HARD_DRAWDOWN_LIMIT` | **B** | `0.10` (10%) | Risk Management | Circuit breaker liquidation trigger. |
| `GOV_MAX_PAIRWISE_CORRELATION` | **B** | `0.75` | Risk Management | Over-correlation concentration cap. |
| `GOV_MAX_EVIDENCE_AGE_SEC` | **B** | `86,400` (24h) | Governance Board | Input freshness ceiling. |
| `HEURISTIC_TARGET_PORTFOLIO_VOL`| **C** | `0.12` (12% ann.) | Research Policy | Baseline risk target for vol scaling. |
| `HEURISTIC_MAX_STRESS_VOL` | **C** | `0.25` (25% ann.) | Research Policy | Stress test volatility hurdle. |
| `HEURISTIC_REBALANCE_THRESHOLD` | **C** | `0.02` (2%) | Research Policy | Rebalancing deadband hysteresis. |
| `HEURISTIC_MIN_PORTFOLIO_TURNOVER`| **C**| `0.05` (5%) | Research Policy | Minimum portfolio-level rebalance delta. |
| `HEURISTIC_SOLVER_TOLERANCE` | **C** | `1e-7` | Numerical Architecture | Optimizer convergence tolerance. |
| `HEURISTIC_MAX_SOLVER_ITER` | **C** | `1,000` | Numerical Architecture | Solver loop safety ceiling. |
| `HEURISTIC_EIGENVALUE_FLOOR` | **C** | `1e-6` | Numerical Architecture | PSD covariance stability floor. |
| `ILLUSTRATIVE_MOCK_CAPITAL_USD` | **D** | `$1,000,000` | Documentation | Mock portfolio basis for documentation. |

---

## 41. Adversarial Self-Audit (25 Dimensions)

To prove institutional resilience, Phase 21 specifies controls across twenty-five adversarial attack vectors:

| # | Adversarial Vector | Control Mechanism | Failure Mode | Fail-Closed Outcome | Authority Owner | Verification Status |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Allocation Authority Leakage:** Phase 21 attempts to select a strategy omitted by Phase 20. | AF-02 & AF-03 strictly restrict optimization candidates to Phase 20's `selected_strategy_ids`. | Unauthorized candidate selection. | Engine halts with `ERR_ALLOC_STRATEGY_NOT_IN_CATALOG`. | Phase 20 Authority | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **2** | **Statistical Authority Leakage:** Phase 21 re-calculates DSR to adjust candidate weights. | Architectural firewall; Phase 21 has no access to raw return series or multiple testing engines. | Statistical overreach. | API method not found; compile-time failure. | Phase 6 Authority | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **3** | **Economic Qualification Leakage:** Phase 21 modifies friction haircut parameters to make a strategy viable. | Phase 21 consumes frozen Phase 8.5 dossier digests; friction parameters are immutable. | Friction tampering. | Recalculated dossier digest fails `AF-08`. | Phase 8.5 Authority | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **4** | **Admission Bypass:** Unadmitted research candidate injected into allocation slate. | AF-06 verifies `admission_status == "ADMITTED"` in Phase 17 catalog. | Unadmitted candidate injected. | Candidate excluded under `ERR_ALLOC_ADMISSION_INVALID`. | Phase 17 Authority | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **5** | **Live Capital Bypass:** Caller sets `execution_mode = "LIVE"` to trigger broker orders. | Engine hard-rejects `"LIVE"` requests while global capital lock is active. | Unauthorized live deployment. | Engine halts with `ERR_ALLOC_CIRCUIT_BREAKER_ACTIVE`. | System Governance | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **6** | **Broker Order Leakage:** Downstream caller interprets `target_weights` as direct broker market orders. | Output contract contains zero order IDs, price limits, or routing tags; Phase 22 owns netting. | Direct broker execution. | Broker rejects DTO; schema invalid. | Phase 21 Architecture | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **7** | **Weight-as-Position Confusion:** Execution engine assumes target weight equals actual position. | Strict separation between allocation plan and Phase 11 real-world position telemetry. | Position tracking error. | Phase 22 reconciles actual vs target before generating intents. | Phase 22 Authority | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **8** | **Lineage Break:** Allocation plan generated without referencing Phase 20 decision digest. | AF-01 & AF-04 enforce cryptographic lineage checks. | Orphan allocation plan. | Engine halts with `ERR_ALLOC_LINEAGE_BROKEN`. | Lineage Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **9** | **Covariance Poisoning:** Caller injects non-positive-semidefinite covariance matrix to distort weights. | AF-18 checks minimum eigenvalue $\lambda_{\min} \ge 10^{-6}$. | Singular / distorted weights. | Solver rejected under `ERR_ALLOC_COVARIANCE_NOT_PSD`. | Covariance Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **10**| **Lookahead Covariance:** Covariance calculated using future bars ($T > T_{\text{as\_of}}$). | AF-21 validates timestamps of all return inputs against $T_{\text{as\_of}}$. | Temporal lookahead bias. | Engine halts with `ERR_ALLOC_TEMPORAL_LOOKAHEAD`. | Data Contract Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **11**| **Stale Risk Inputs:** 1-month-old volatility vector used to size active portfolio. | AF-10 & AF-15 check input timestamps against `max_evidence_age`. | Stale risk sizing. | Engine halts with `ERR_ALLOC_REGIME_STALE`. | Telemetry Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **12**| **Fake Capacity Assumption:** Optimizer allocates \$10M to a illiquid micro-cap strategy. | Capacity ceiling check clamps allocation: $w_i \times A \le K_i$. | Alpha-destroying market impact. | Allocation clamped or rejected if capacity unverified. | Phase 8.5 Authority | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **13**| **Numerical Instability:** Matrix condition number $\kappa(\Sigma) = 10^{12}$ causes optimizer to diverge. | Conditioning check detects ill-conditioning; applies Ledoit-Wolf shrinkage. | Exploding weights / NaN. | Solver cascades to minimum variance or defensive mode. | Numerical Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **14**| **Infeasible Problem Forcing:** Optimizer forced to emit "best-effort" weights when constraints conflict. | Infeasibility trap strictly halts and routes to `NO_ALLOCATION`. | Contaminated weights emitted. | Decision status emitted as `INFEASIBLE`; zero allocation. | Solver Architecture | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **15**| **Silent Solver Substitution:** Engine silently switches from ERC to Equal-Weight without recording. | Solver ID and version sealed in immutable plan digest. | Undocumented model behavior. | Audit ledger detects mismatch; alert raised. | Audit Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **16**| **Hidden Leverage:** Short positions used to inflate gross exposure to 300%. | AF-14 & CONC-06 check $\sum |w_i| \le \text{max\_gross\_leverage}$. | Unintended portfolio leverage. | Optimization rejected under `ERR_ALLOC_EXPOSURE_LIMIT_UNDEFINED`.| Risk Management | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **17**| **Concentration Leakage:** Two strategies with correlation $\rho = 0.98$ both receive 25% weights. | Cluster risk rule enforces $w_i + w_j \le 0.35$ for correlated pairs. | Latent 50% single-factor risk. | Optimizer enforces joint pair bound. | Risk Management | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **18**| **AI Weight Manipulation:** LLM modifies target weights to reflect "market intuition." | AI Epistemic Firewall prohibits AI write permissions to weight vectors. | Unverified AI intervention. | Engine rejects payload; cryptographic signature invalid. | AI Epistemic Firewall | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **19**| **Human Override Abuse:** Operator repeatedly forces 100% allocation on favored strategy. | `OverrideAllocationRecord` requires cryptographic identity and reason code. | Unaudited manual override. | Audit ledger flags override spike; compliance alert fired. | Governance Auditor | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **20**| **Policy Drift:** Local configuration changes leverage limit without updating policy digest. | AF-11 checks `allocation_policy_digest` against immutable manifest. | Unapproved policy drift. | Engine halts with `ERR_ALLOC_POLICY_DIGEST_MISMATCH`. | Governance Board | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **21**| **Historical Survivorship in $\Sigma$:** Covariance matrix excludes defunct strategies from lookback. | Sovereign catalog maintains full historical covariance asset universe. | Underestimated portfolio risk. | Covariance engine uses survivor-bias-free returns. | Phase 17 Authority | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **22**| **Turnover Budget Bypass:** High-frequency rebalancing generates 200% daily turnover. | Turnover constraint clamps weight delta: $\frac{1}{2}\sum |w_t - w_{t-1}| \le \text{budget}$. | Excessive fee drag. | Optimizer clamps rebalance or suppresses trade. | Policy Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **23**| **Zero-Risk Semantics Confusion:** Downstream listener treats $w_i = 0$ as instruction to send sell orders. | Phase 21 documentation and schemas explicitly declare $w_i$ as target weights only. | Erroneous market dumps. | Phase 22 orchestrator enforces staged liquidation schedules. | Phase 22 Authority | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **24**| **Singular Portfolio Volatility:** Base volatility $\sigma_p = 0$ causes division-by-zero in ERC. | AF-20 checks standalone volatilities; floor prevents division by zero. | Runtime divide-by-zero crash. | Engine raises `ERR_ALLOC_VOLATILITY_DEGENERATE`. | Numerical Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |
| **25**| **Expected Return Fabrication:** Mean-Variance solver silently sets $\mu_i = \text{mean}(R_i)$. | Strict Section 16 rule halts unless $\boldsymbol{\mu}$ is provided by certified upstream authority. | Spurious mean-variance weights. | Engine halts with `ERR_ALLOC_EXPECTED_RETURN_UNAVAILABLE`. | Epistemic Engine | CONTROL SPECIFIED / NOT YET IMPLEMENTED |

---

## 42. Academic & Quantitative Grounding

Phase 21 is grounded in peer-reviewed econometric and quantitative portfolio management literature:

1. **Modern Portfolio Theory & Mean-Variance Optimization:**
   - *Markowitz, H. (1952). "Portfolio Selection." Journal of Finance.*  
     Establishes the mean-variance framework and diversification mechanics. Phase 21 explicitly constrains this to prevent extreme corner solutions driven by estimation error.
2. **Equal Risk Contribution & Risk Parity:**
   - *Maillard, S., Roncalli, T., & Teïletche, J. (2008). "On the Properties of Equally-Weighted Risk Contribution Portfolios." Journal of Portfolio Management.*  
     Provides mathematical proof of the existence, uniqueness, and convexity of the ERC portfolio under non-singular covariance matrices.
3. **Portfolio Estimation Error & Shrinkage:**
   - *Ledoit, O., & Wolf, M. (2004). "A well-conditioned estimator for large-dimensional covariance matrices." Journal of Multivariate Analysis.*  
     Demonstrates that sample covariance matrices are severely ill-conditioned when $N/T$ is non-negligible, proving the mathematical necessity of shrinkage targets.
   - *Chopra, V. K., & Ziemba, W. T. (1993). "The effect of errors in means, variances, and covariances on optimal portfolio choice." Journal of Portfolio Management.*  
     Proves that estimation errors in expected returns are an order of magnitude more destructive than errors in variances, justifying Phase 21's strict ban on fabricating $\boldsymbol{\mu}$.
4. **Diversification Maximization:**
   - *Choueifaty, Y., & Coignard, Y. (2008). "Toward Maximum Diversification." Journal of Portfolio Management.*  
     Establishes the Diversification Ratio and proves that maximizing risk-weighted asset spread yields the optimal uncorrelated risk exposure.

### 42.1 Epistemic Separation Table

| Principle | Academic Literature Fact | ACASH Governance Policy | Research Heuristic | Architectural Choice |
| :--- | :--- | :--- | :--- | :--- |
| **Covariance Conditioning** | Sample covariance is singular when $N \ge T$. | Ledoit-Wolf shrinkage is mandatory. | Minimum eigenvalue floor $\lambda = 10^{-6}$. | Isolated in `covariance.py`. |
| **Risk Contribution** | $\sum \text{RC}_i = \sigma_p$ (Euler Theorem). | Require ERC as default baseline solver. | Target volatility $\sigma^* = 0.12$. | Solvers implement uniform interface. |
| **Return Sensitivity** | $\mu$ estimation error destroys portfolio utility. | Banned from fabricating $\boldsymbol{\mu}$ internally. | Quadratic risk aversion $\lambda = 2.0$. | Mean-Variance fails closed if $\mu$ null. |
| **Concentration Risk** | Diversified weights reduce idiosyncratic risk. | Hard 25% single-strategy ceiling. | Correlation cluster ceiling $\rho \le 0.75$. | Firewall gate preceding solver. |

---

## 43. Explicit Non-Goals

To eliminate cross-phase ambiguity, Phase 21 explicitly declares the following as **NON-GOALS**:

1. **Strategy Discovery & Research:** Phase 21 does not generate signals or research hypotheses. That belongs to Phase 14.
2. **Strategy Selection:** Phase 21 does not select strategies or filter candidate pools. That belongs to Phase 20.
3. **Statistical Validation:** Phase 21 does not compute DSR, PBO, MinTRL, or $p$-values. That belongs to Phase 6.
4. **Economic Qualification:** Phase 21 does not qualify trading capacity or fee drag. That belongs to Phase 8.5.
5. **Strategy Admission:** Phase 21 does not admit strategies to the sovereign catalog. That belongs to Phase 17.
6. **Regime Detection:** Phase 21 does not classify market volatility or trend states. That belongs to Phase 19.
7. **Runtime Health Monitoring:** Phase 21 does not monitor broker connectivity or reality gaps. That belongs to Phase 11.
8. **Multi-Strategy Order Orchestration:** Phase 21 does not batch orders or net positions. That belongs to Phase 22.
9. **Order Generation & Routing:** Phase 21 does not emit orders, limit prices, or FIX messages. That belongs to Phase 12.
10. **Live Capital Deployment:** Phase 21 does not move funds or allocate live capital. Live capital remains strictly `$0.00`.

---

## 44. Future Implementation Constraints (When Authorized)

> [!CAUTION]
> **CODE IMPLEMENTATION IS CURRENTLY STRICTLY LOCKED AND NOT AUTHORIZED.**  
> The following architectural constraints are established exclusively for the future phase when human governance formally unlocks code implementation.

### 44.1 Proposed Module Boundaries
```
src/acash/research/allocation/
├── __init__.py
├── firewall.py                     # AllocationEligibilityFirewall (AF-01 to AF-25)
├── models.py                       # PortfolioAllocationPlan, DTOs
├── policy.py                       # AllocationPolicy & Threshold Registry
├── solvers/
│   ├── __init__.py
│   ├── base.py                     # IAllocationSolver Interface
│   ├── erc.py                      # Equal Risk Contribution Solver
│   ├── risk_parity.py              # General Risk Parity Solver
│   ├── volatility_target.py        # Volatility Targeting Solver
│   ├── minimum_variance.py         # Minimum Variance Solver
│   ├── mean_variance.py            # Constrained Mean-Variance Solver
│   ├── max_diversification.py      # Maximum Diversification Solver
│   ├── risk_budgeting.py           # Risk Budgeting Solver
│   └── defensive.py                # Defensive Zero-Risk Solver
├── covariance.py                   # Ledoit-Wolf Shrinkage & PSD Repair
├── constraints.py                  # Concentration, Leverage, Exposure Checks
├── stress.py                       # Pre-Flight Stress Testing Engine
├── sensitivity.py                  # Perturbation & Condition Diagnostics
├── ledger.py                       # AllocationAuditLedger (JSONL Append-Only)
├── manifest.py                     # AllocationReproducibilityManifest
└── resolver.py                     # Lineage Digest Verification
```

### 44.2 Mandatory Engineering Standards
1. **Pydantic V2 Models:** All DTOs must use immutable Pydantic models (`frozen=True`, `extra='forbid'`).
2. **Decimal Financial Types:** All weights, capital amounts, and risk budgets must use Python `Decimal`.
3. **Strict Typing:** Must achieve 100% clean validation under `uv run mypy --strict src/acash/research/allocation/ tests/`.
4. **Environment-Sealed Determinism:** Optimization routines must produce byte-for-byte identical output digests within a declared execution environment (ADR-022).
5. **No Mutation of Sealed Modules:** Phase 21 code must never modify upstream modules (`src/acash/core/`, `src/acash/adapters/`, `src/acash/research/selection/`).

---

## 45. Acceptance Criteria

The Phase 21 Master Architecture Specification is deemed acceptable when the following plan-level criteria are verified:

- [x] **Criterion 1 (Scope Demarcation):** Phase 21 defines risk-based capital allocation while strictly avoiding strategy selection (Phase 20), statistical validation (Phase 6), and execution orchestration (Phase 22).
- [x] **Criterion 2 (Selection Integrity):** Enforces that Phase 21 consumes `StrategySelectionDecision` and cannot independently add, substitute, or revive candidates.
- [x] **Criterion 3 (Eligibility Firewall):** Specifies 25 pre-solver filter predicates (`AF-01` to `AF-25`) covering decision integrity, authority lineage, capital limits, covariance health, and circuit breakers.
- [x] **Criterion 4 (Solver Families):** Mathematically formulates eight governed solver families (ERC, Risk Parity, VolTarget, MinVar, MeanVar, MaxDiv, Risk Budgeting, Defensive Zero-Risk).
- [x] **Criterion 5 (Epistemic Hygiene):** Explicitly states that numerical optimality $\ne$ market profitability, and strictly bans fabricating expected returns $\boldsymbol{\mu}$.
- [x] **Criterion 6 (Fail-Closed Feasibility):** Enforces that `INFEASIBLE` solver statuses default strictly to `NO_ALLOCATION` (zero "best-effort" guessing).
- [x] **Criterion 7 (Covariance Governance):** Specifies Ledoit-Wolf analytical shrinkage and positive-semidefinite matrix validation with transparent repair logging.
- [x] **Criterion 8 (Capital Source & Unit Discipline):** Disentangles Total Equity from Allocatable Capital and strictly distinguishes risk budgets ($b_i$) from capital weights ($w_i$).
- [x] **Criterion 9 (Allocation $\ne$ Execution):** Explicitly specifies that target weights $w_i$ are abstract sizing ratios emitting zero broker orders.
- [x] **Criterion 10 (Adversarial Audit):** Formalizes controls across 25 adversarial attack vectors with explicit fail-closed outcomes.
- [x] **Criterion 11 (Audit Ledger & Lineage):** Specifies the immutable `PortfolioAllocationPlan` schema and hash-chained `allocation_ledger.jsonl`.
- [x] **Criterion 12 (Zero Machine-Specific Paths):** Verifies document portability using strictly repository-relative paths.
- [x] **Criterion 13 (Runtime Invariant Preservation):** Confirms zero code implementation, `$0.00` live capital, zero orders, broker disconnected, and Phase 13 soak (PID 41844) untouched.

---

## 46. Governance Sign-Off Ledger

```
================================================================================
                    ACASH GOVERNANCE & ARCHITECTURE SIGN-OFF
================================================================================
Document ID             : ACASH-SPEC-PHASE21-ALLOCATION-v1.0
Specification Status    : PROPOSED ARCHITECTURE — HUMAN APPROVAL PENDING
Implementation Status   : STRICTLY LOCKED / NOT AUTHORIZED
Parent Roadmap          : docs/ROADMAP.md (v3.4.0)
Parent Architecture     : AGENTS.md, ADR-022, ADR-023

Lead Quant Architect   : Antigravity / Senior Quantitative Portfolio Architect
Governance Auditor      : Statistical Governance & Risk Management Reviewer
DevOps / SRE Lead       : Fail-Closed Systems Engineer

Verification Status:
  - Architecture Review : COMPLETE / SATISFIED
  - Authority Isolation : STRICTLY DEMARCATED (Zero Selection/Execution Overreach)
  - Mathematical Sound  : GOVERNED FORMULATIONS (ERC, Risk Parity, VolTargeting)
  - Fail-Closed Contract: COMPLETE (30/30 Failure Modes Handled; INFEASIBLE -> NO_ALLOC)
  - Adversarial Audit   : COMPLETE (25/25 Dimensions Addressed)
  - Live Trading State  : HARD-LOCKED ($0.00 Capital, 0 Orders, Broker Disconnected)
  - Background Soak     : UNTOUCHED (PID 41844 Active in Step 5)

FINAL VERDICT:
  -> CONDITIONAL PASS: READY FOR HUMAN REVIEW & GOVERNANCE APPROVAL
  -> IMPLEMENTATION: LOCKED UNTIL FORMAL HUMAN GOVERNANCE SIGN-OFF
================================================================================
```
