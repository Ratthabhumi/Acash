# ACASH Research Re-Inception Gate: Architectural Specification & Governance Contract

> **Document ID:** `SPEC-RESEARCH-REINCEPTION-GATE-20260906-001`  
> **Timestamp:** `2026-09-06T23:25:00+00:00`  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed)  
> **Status:** `RATIFIED & IMPLEMENTED`  
> **Verdict:** `PASS`  

---

## 1. Executive Summary & Architecture Boundary

The **Research Re-Inception Gate** serves as the canonical, machine-enforced governance bridge between:
$$\mathbf{STANDING\ BY \longrightarrow RESEARCH\ INCEPTION \longrightarrow STEP\ R1}$$

### What the Gate Is
- **An R1 Pre-Registration Entry Control:** It enforces institutional standards of scientific rigor, anti-HARKing declarations, and quarantine boundaries before a candidate hypothesis can be sealed as Step R1.
- **A Declarative Validator:** It validates hypothesis metadata, search grid geometry, economic rationale, and declared data windows.

### What the Gate Is NOT (Explicit Non-Goals)
- **NOT an Alpha Evaluator:** It does not compute returns, Rank IC, or evaluate trading viability.
- **NOT a Data Acquisition Seam:** It performs **zero Parquet/CSV file reads** and accesses zero market data. (Dataset verification belongs strictly to Step R2).
- **NOT a Trading Authorization Gate:** It cannot authorize paper trading, live trading, or capital allocation.

---

## 2. Six Mandatory Governance Invariants

```text
                             STANDING BY
                                  │
                  [Research Inception Proposal]
                                  │
                                  ▼
                   RESEARCH RE-INCEPTION GATE
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    ▼                             ▼                             ▼
[1. Identity & Immutability]  [2. Anti-HARKing Cardinality]  [3. Quarantine Boundary]
 - New immutable ID            - planned_trials == |Grid|     - No unverified holdout access
 - No terminal resurrection    - Frozen degrees of freedom    - Valid GovernanceExceptionRecord
    │                             │                             │
    └─────────────────────────────┼─────────────────────────────┘
                                  │
    ┌─────────────────────────────┴─────────────────────────────┐
    ▼                                                           ▼
[4. Pre-Registration Completeness]              [5. Decoupled Readiness Invariant]
 - Rationale >= 20 chars                         - Hard-locked Capital: $0.00
 - Non-empty features                            - is_strategy_qualified: False
 - Horizons & Invalidation Criteria              - is_paper_authorized: False
 - Realistic Cost Model                          - is_live_authorized: False
                                  │
                                  ▼
                  INCEPTION AUTHORIZATION TOKEN
                                  │
                                  ▼
                     STEP R1 PRE-REGISTRATION
```

### Invariant 1: New Immutable Hypothesis Identity
- Must match pattern `^HYP_[A-Z0-9_]+$`.
- **Zero Resurrection:** Cannot reuse any ID from `TERMINAL_HYPOTHESIS_REGISTRY` (e.g. `HYP_TSMOM_EURUSD_001`). Falsified hypotheses are absorbing and permanent.
- **Zero In-Place Mutation:** Cannot overwrite or modify parameters of an existing sealed hypothesis on disk.

### Invariant 2: Anti-HARKing Search Cardinal Equality
- **The Cardinal Equality Rule:**
  $$\mathbf{planned\_trial\_count \equiv \prod_{param \in Grid} |values_{param}|}$$
- A proposal declaring $K=1$ while providing a grid of 20 parameter variations fails closed immediately (`ANTI_HARKING_CARDINALITY_MISMATCH`). Search degrees of freedom must be honestly and completely accounted for.

### Invariant 3: Declarative Data Contract & Quarantine Protection
- **Declarative Window Only:** `proposed_data_window` is declared as metadata `(start_utc, end_utc)`. The gate does not read data from disk.
- **Quarantine Boundary:** Overlapping with the `EURUSD_M5_HOLDOUT` (2026-08-18T04:40:00Z to 2026-09-04T21:00:00Z) is blocked fail-closed.
- **Governance Exception Verification:** Declaring a `governance_exception_id` alone is insufficient. The referenced `GovernanceExceptionRecord` must:
  1. Exist in the authoritative exception registry.
  2. Authorize the exact `candidate_hypothesis_id`, `target_symbol`, and `target_timeframe`.
  3. Possess a verified SHA-256 canonical digest matching its contents.

### Invariant 4: Pre-Registration Completeness
- `economic_rationale`: Must be a non-trivial structural theory ($\ge 20$ characters).
- `feature_dependencies`: At least 1 valid feature symbol.
- `target_horizons`: At least 1 positive integer; `primary_horizon` must be a member.
- `invalidation_criteria`: Finite, strictly positive hurdles (`min_in_sample_rank_ic > 0`, `min_hac_t_stat >= 1.50`).
- `cost_model`: Explicit, non-negative friction parameters.

### Invariant 5: Decoupled Readiness Invariant
- Emitted `InceptionAuthorizationToken` contains frozen, immutable governance attributes:
  - `capital_authority_usd = Decimal("0.00")`
  - `is_strategy_qualified = False`
  - `is_paper_authorized = False`
  - `is_live_authorized = False`
- There are **zero methods or upgrade mechanisms** on the token to unlock trading or capital.

---

## 3. Data Transfer Objects (DTOs) & Validator Specification

### 3.1 `ResearchInceptionProposal`
```python
class ResearchInceptionProposal(BaseModel):
    candidate_hypothesis_id: str
    candidate_hypothesis_version: str = "1.0.0"
    economic_rationale: str
    target_symbol: str
    target_timeframe: str
    feature_dependencies: List[str]
    parameter_search_grid: Dict[str, List[Any]]
    planned_trial_count: int
    target_horizons: List[int]
    primary_horizon: int
    expected_direction: ExpectedDirection
    invalidation_criteria: InvalidationCriteria
    cost_model: CostModelConfig
    proposed_dataset_id: str
    proposed_data_window: Tuple[str, str]
    proposed_split_policy: SplitPolicy
    governance_exception_id: Optional[str] = None
    author: str = "QuantitativeResearchAgent"
    proposed_at_utc: str
```

### 3.2 `InceptionAuthorizationToken`
```python
class InceptionAuthorizationToken(BaseModel):
    token_id: str
    authorized_hypothesis_id: str
    proposal_sha256: str
    decision: InceptionDecision = InceptionDecision.INCEPTION_AUTHORIZED
    authorized_at_utc: str
    capital_authority_usd: Decimal = Field(default=Decimal("0.00"), frozen=True)
    is_strategy_qualified: bool = Field(default=False, frozen=True)
    is_paper_authorized: bool = Field(default=False, frozen=True)
    is_live_authorized: bool = Field(default=False, frozen=True)
```

---

## 4. Canonical Enforcement Examples

### 4.1 Compliant Proposal (PASS)
- **Candidate ID:** `HYP_MR_EURUSD_001`
- **Search Grid:** `{"lookback": [3, 5, 8], "threshold": [1.0, 2.0]}` (6 combinations)
- **Planned Trials:** `6` (Cardinality match)
- **Data Window:** `2025-01-01T00:00:00Z` to `2025-06-30T23:59:00Z` (Zero overlap with 2026 holdout)
- **Verdict:** `INCEPTION_AUTHORIZED` $\to$ Token emitted with `$0.00` capital.

### 4.2 Rejected: Terminal Resurrection Attempt (FAIL CLOSED)
- **Candidate ID:** `HYP_TSMOM_EURUSD_001`
- **Result:** `BLOCKED_MUTATION_VIOLATION`: Reusing terminally falsified hypothesis ID is strictly forbidden.

### 4.3 Rejected: Anti-HARKing Cardinality Mismatch (FAIL CLOSED)
- **Search Grid:** 6 combinations
- **Planned Trials:** `1` (Under-reporting search degrees of freedom)
- **Result:** `ANTI_HARKING_CARDINALITY_MISMATCH`: Declared planned_trial_count (1) != grid cardinality (6).

### 4.4 Rejected: Unverified Quarantined Holdout Access (FAIL CLOSED)
- **Data Window:** Overlaps with `EURUSD_M5_HOLDOUT`
- **Governance Exception:** `None`
- **Result:** `BLOCKED_QUARANTINE_VIOLATION`: Quarantined data cannot be reused without verified exception.

---

## 5. Verification & Test Evidence

### 5.1 Test Execution Results
- **Targeted Unit Tests:** `tests/unit/research/test_research_reinception_gate.py`: **13/13 PASSED** in 2.79s.
- **Research Unit Test Suite:** `tests/unit/research/`: **107/107 PASSED** in 4.93s.
- **Full Repository Regression Suite:** `uv run pytest`: **1,519 passed, 1 skipped, 0 failed** in 40.75s.
- **Static Type Checker:** `uv run mypy`: **0 issues found** across all touched source files.

---

## 6. Evidence Classification Table

| Invariant / Property | Classification | Ground Truth Reference |
| :--- | :--- | :--- |
| **New Immutable ID Enforcement** | **VERIFIED** | Enforced by `ResearchReInceptionGate`; tested in unit tests |
| **Terminal Resurrection Blocking** | **VERIFIED** | Enforced against `TERMINAL_HYPOTHESIS_REGISTRY`; tested |
| **Anti-HARKing Cardinal Equality** | **VERIFIED** | Enforced by `proposal.grid_cardinality == planned_trial_count`; tested |
| **Declarative Data Contract (0 Parquet Reads)** | **VERIFIED** | Inspected `reinception.py`; 0 parquet/csv import or read calls |
| **Quarantine Exception Validation** | **VERIFIED** | Enforced by `GovernanceExceptionRecord` digest checking; tested |
| **Decoupled Readiness & Zero Capital ($0.00)** | **VERIFIED** | Hard-locked on `InceptionAuthorizationToken`; tested |
| **Phase 13 Step 8/9 Lock Preservation** | **VERIFIED** | Inception token has zero trading authority; tested |

---

## 7. Mandatory Non-Execution Affirmations

- **Zero market data accessed or read.**
- **Zero empirical research or backtests executed.**
- **Zero `HYP_..._002` created or registered.**
- **Zero quarantined M5 holdout bars exposed.**
- **Zero broker connections or orders submitted.**
- **Capital authority remains strictly `$0.00`.**
- **Phase 13 Step 8 and Step 9 remain strictly locked.**

---

## 8. Final Verdict

$$\boxed{\mathbf{VERDICT:\ PASS}}$$

The Research Re-Inception Gate is fully ratified, mathematically bounded, architecturally decoupled, and verified against all unit and regression tests. The ACASH repository remains safely in **`STANDING BY`**.
