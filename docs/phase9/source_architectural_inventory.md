# Phase 9: Source & Architectural Inventory Audit
## Comprehensive Pre-Implementation Risk Engine & Kill Switch Audit

> **Document:** `docs/phase9/source_architectural_inventory.md`  
> **Status:** AUDITED & VERIFIED AGAINST BASELINE `9ce1365`  
> **Baseline Commit:** `9ce1365` (Phase 8.5 Frozen Baseline, 772/772 tests passing, 0 MyPy errors)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Authority, Strict Fail-Closed, Separation of Concerns)

---

## 1. Executive Summary

This inventory audit establishes the empirical baseline of the existing risk, governance, admission, and execution capabilities across the ACASH repository prior to drafting the formal **Phase 9: Deterministic Risk Engine & Kill Switch** contract.

The repository is currently at commit `9ce1365` (100% clean working tree, 772 passing unit/integration tests, 0 MyPy errors). Every statement in this audit has been verified directly against active source files and executed test suites.

### Key Audit Conclusions:
1. **Abstract Contract Exists, Real Implementation Missing**: `IRiskEngine` was established in Phase 1 (`src/acash/core/interfaces/risk.py`), but has **zero** concrete production implementations and **zero** mock adapters across the codebase.
2. **Dispersed Risk Fragments Across Phases**:
   - **Phase 8 Governance (`src/acash/portfolio/governance.py`)**: Owns static pre-allocation hurdle, DSR provenance, constraint feasibility, and cash sovereignty fallback.
   - **Phase 7 Admission (`src/acash/execution/admission.py`)**: Owns pre-live cryptographic ticket admission, operational restrictions (`RiskRestrictionAuthority`), and reactive kill-switch trigger detection (`evaluate_kill_switch_triggers`).
   - **Phase 1 Domain Models (`src/acash/core/domain/`)**: Owns double-entry `PortfolioState`, broker `AccountState`, `TargetAllocation`, and `RiskAssessment`.
3. **Core Missing Authority (Phase 9 Responsibility)**: A unified, deterministic **Runtime Risk Engine** that acts as the sovereign control plane between Phase 8 (Portfolio Rebalance Planning) and Phase 7 (Order Admission & Execution), capable of:
   - Evaluating planned rebalance deltas against hard portfolio leverage, asset concentration, and drawdown limits.
   - Deterministically **approving, reducing, or rejecting** allocations without probabilistic heuristics.
   - Dispatching structured, emergency position-flattening / order-cancellation commands upon kill-switch activation.

---

## 2. Evidence Classification System

Findings in this audit are strictly categorized according to the following evidentiary taxonomy:

- **`[VERIFIED FACT]`**: Concrete implementation or behavior verified by inspecting source code and passing test executions.
- **`[PROJECT CONTRACT]`**: Binding architectural invariant or non-negotiable rule defined in `AGENTS.md`, `DECISIONS.md`, or canonical domain schemas.
- **`[EXISTING CAPABILITY]`**: Fully functional, tested component active in the repository.
- **`[MISSING CAPABILITY]`**: Necessary capability that is absent from the codebase and must be built in Phase 9.
- **`[UNVERIFIED]`**: Ambiguous or partial implementation requiring explicit verification or remediation.
- **`[OPEN QUESTION]`**: Unresolved architectural, mathematical, or policy question requiring explicit decision before implementation.

---

## 3. Runtime Authority Chain & Integration Seams

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 8.5: Alpha Research & Evidence Validation                         │
│ - Authority: Empirical evidence admissibility only                      │
│ - Output: AlphaQualificationDossier (RESEARCH_QUALIFIED)                │
│ - Invariant: Capital Authority === $0.00, Live Order Authority === None │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Candidate Strategy Inputs
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 8: Portfolio Engine & Rebalance Planning                          │
│ - Authority: Capital allocation optimization & rebalance delta planning │
│ - Gate: PortfolioGovernanceGate (Hurdle, DSR, Long-only, 100% Cash)    │
│ - Output: AllocationDecision -> RebalancePlan (Target Qtys & Deltas)    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ RebalancePlan / Candidate Allocations
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 9: Deterministic Risk Engine & Kill Switch (SOVEREIGN CONTROL)   │
│ - Authority: Sovereign veto over all allocations; Real-time risk gate   │
│ - Evaluator: DeterministicRiskEngine (IRiskEngine)                      │
│ - Actions: APPROVED (100%) | REDUCED (Scaled down) | REJECTED (0% Cash) │
│ - Global Override: KillSwitchEvent (CANCEL_ORDERS, EMERGENCY_FLATTEN)  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Authorized Target / Safe Orders
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 7: Pre-Live Risk Admission & Execution Coordinator                │
│ - Authority: Cryptographic ticket verification, BMAP, state machine     │
│ - Admission: construct_order_intent() (Active Auth, RiskState, Limits)  │
│ - Coordinator: ExecutionCoordinator (Reconciliation, Idempotency, Dedup)│
│ - Driver: AlpacaPaperAdapter / MockBroker -> Paper Broker Venue         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detailed Boundary Analysis:

| Boundary | Upstream Output | Downstream Input | Sovereign Authority | Veto Capability | Failure Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **8.5 $\to$ 8** | `AlphaQualificationDossier` | `AllocationCandidate` | Phase 8 Allocator / Tournament | Rejects unqualified alphas from candidate pool | Candidate omitted from tournament; 100% Cash fallback if empty |
| **8 $\to$ 9** | `RebalancePlan` / `AllocationDecision` | Candidate Allocations to Risk Engine | **Phase 9 Risk Engine** | **Sovereign Veto over all allocations** | Scales down (`REDUCED`) or forces 100% Cash (`REJECTED`) |
| **9 $\to$ 7** | `RiskAssessment` / Approved Allocations | `OrderIntent` Construction | Phase 7 Admission Gate | Rejects if Auth inactive or RiskState non-nominal | `PreLiveRiskAdmissionError` raised (fail-closed, 0 orders sent) |
| **7 $\to$ Broker** | `OrderIntent` | Wire REST/WebSocket payload | Broker Adapter (`AlpacaPaperAdapter`) | Rejects if venue unmapped or connection dead | Order marked `REJECTED`, incident logged, 0 phantom fills |

---

## 4. Existing Source & Interface Inventory

### 4.1 Domain Models (`src/acash/core/domain/`)
- `PortfolioState` (`portfolio.py`) `[EXISTING CAPABILITY]`:
  - Enforces double-entry accounting: $\text{Total Equity} \equiv \text{Cash} + \sum \text{Market Value}$.
  - Enforces finite Decimals, gross exposure, net exposure, and unrealized/realized P&L consistency.
- `AccountState` (`portfolio.py`) `[EXISTING CAPABILITY]`:
  - Captures external broker account snapshot: `balance`, `equity`, `free_margin`, `margin_level_pct`, `leverage`, `is_live`, `timestamp_utc`.
- `TargetAllocation` (`signal.py`) `[EXISTING CAPABILITY]`:
  - Immutable mapping of symbols to target float weights, `cash_weight`, rationale, and timestamp.
- `RiskAssessment` (`signal.py`) `[EXISTING CAPABILITY]`:
  - Fields: `approved: bool`, `adjusted_weights: Mapping[str, float]`, `rejection_reason: Optional[str]`, `max_drawdown_pct: float`, `risk_utilization_pct: float`, `timestamp_utc: datetime`.

### 4.2 Interfaces (`src/acash/core/interfaces/`)
- `IRiskEngine` (`risk.py`) `[PROJECT CONTRACT]`:
  ```python
  class IRiskEngine(ABC):
      @abstractmethod
      def evaluate_allocation(
          self,
          target_allocation: TargetAllocation,
          portfolio_state: PortfolioState,
          account_state: Optional[AccountState],
          timestamp_utc: datetime,
      ) -> RiskAssessment:
          """Evaluate candidate target allocation against hard portfolio and drawdown constraints."""
          pass
  ```
  - **Status**: Pure ABC only. **No concrete implementation exists anywhere in the codebase.**

### 4.3 Phase 8 Portfolio Governance (`src/acash/portfolio/governance.py`)
- `PortfolioGovernanceGate` `[EXISTING CAPABILITY]`:
  - Checks pre-risk limits: `is_kill_switch_active`, `current_drawdown_pct >= max_drawdown_limit_pct`, `margin_headroom < margin_buffer_threshold`.
  - Enforces long-only bounds ($w_i \ge 0$), leverage ceiling ($\sum w_i \le \text{max\_gross\_leverage}$), and cash conservation ($\sum w_i + w_{\text{cash}} = 1.0$).
  - Evaluates hurdle rate and DSR sample sufficiency; defaults sovereignly to `CASH_SOVEREIGN_FALLBACK` upon failure.
- `RebalancePlanner` (`src/acash/portfolio/planner.py`) `[EXISTING CAPABILITY]`:
  - Translates `AllocationDecision` into `RebalancePlan` with target quantities, position deltas, and reference sizing notionals.

### 4.4 Phase 7 Execution Admission & Operational Restriction (`src/acash/execution/`)
- `construct_order_intent()` (`admission.py`) `[EXISTING CAPABILITY]`:
  - Enforces `LiveAuthorization.status == ACTIVE`, non-expired authorization, allowed venues, allowed symbols, and `quantity <= max_position_size`.
  - Checks `current_risk.calculation_status == CalculationStatus.NOMINAL` and `current_risk.risk_status == RiskStatus.NORMAL`.
  - Enforces active restrictions via `RiskRestrictionAuthority.gate_for_intent()`.
- `evaluate_kill_switch_triggers()` (`admission.py`) `[EXISTING CAPABILITY]`:
  - Evaluates reactive operational triggers:
    1. `BROKER_DISCONNECTED` $\to$ `HALT_NEW_ORDERS` + `FREEZE_AND_RECONCILE`.
    2. `STALE_MARKET_DATA` (data age $> 1500\text{ms}$) $\to$ `CANCEL_WORKING_ORDERS` + `FREEZE_AND_RECONCILE`.
    3. `CLOCK_SKEW_DETECTED` (drift $> 500\text{ms}$) $\to$ `CANCEL_WORKING_ORDERS` + `FREEZE_AND_RECONCILE`.
    4. `MAX_DAILY_LOSS` ($\text{loss} > \text{max\_daily\_loss\_notional}$) $\to$ `CANCEL_WORKING_ORDERS` + `CONTROLLED_DERISK`.
    5. `MAX_DRAWDOWN` ($\text{drawdown} \ge \text{max\_drawdown\_pct}$) $\to$ `CANCEL_WORKING_ORDERS` + `EMERGENCY_FLATTEN`.
- `RiskRestrictionAuthority` (`operational_restriction.py`) `[EXISTING CAPABILITY]`:
  - Thread-safe ledger managing open operational restrictions (e.g. `RECONCILIATION_CONFLICT`, `DATA_SOURCE_DEGRADED`).
  - Admission gate strictly consults restriction authority; admission only enforces, never clears.

---

## 5. Phase 9 Missing Capability Gap Analysis

| Risk Capability | Existing Repository State | Phase 9 Required Implementation | Classification |
| :--- | :--- | :--- | :--- |
| **Concrete Risk Engine** | `IRiskEngine` ABC defined in Phase 1; zero implementations. | `DeterministicRiskEngine` implementing `IRiskEngine` with hard parameter thresholds. | `[MISSING CAPABILITY]` |
| **Multi-Tier Leverage & Exposure Caps** | Checked statically in Phase 8 Governance; no real-time check against live order impact. | Live portfolio-level gross leverage and single-asset concentration limits. | `[MISSING CAPABILITY]` |
| **Dynamic Position Derisking / Reduction** | `RiskAssessment.adjusted_weights` defined, but no sizing scale-down math exists. | Proportional allocation scaling algorithm preserving cash buffer and long-only rules. | `[MISSING CAPABILITY]` |
| **Global Kill Switch Controller** | Reactive triggers defined in Phase 7; no central sovereign kill switch engine. | Sovereign `KillSwitchController` with idempotent activation, persistence, and deactivation quorum. | `[MISSING CAPABILITY]` |
| **Emergency Flattening Dispatcher** | Trigger outputs `EMERGENCY_FLATTEN` action string; no order generation logic exists. | Deterministic liquidation order plan generator converting open positions to closing market orders. | `[MISSING CAPABILITY]` |
| **Unified Risk State Bridge** | Phase 8 uses `RiskSnapshot`; Phase 7 uses `RiskState`; Phase 1 uses `PortfolioState`. | Canonical conversion and validation bridge linking domain states without data loss. | `[MISSING CAPABILITY]` |

---

## 6. Fail-Closed Analysis & Safety Invariants

| Failure Scenario | Existing System Response | Risk Engine Invariant for Phase 9 |
| :--- | :--- | :--- |
| **Missing Market Data / Snapshot** | Phase 7 rejects order intent (`CalculationStatus != NOMINAL`). | Phase 9 Risk Engine immediately emits `REJECTED` (100% Cash), halts evaluation. |
| **Stale Market Data ($> 1500\text{ms}$)** | Phase 7 trips kill-switch trigger (`STALE_MARKET_DATA`). | Phase 9 trips `KillSwitchEvent`, cancels working orders, blocks new allocations. |
| **Broker State Disconnected / Unknown** | Phase 7 blocks order admission; coordinator logs `UNKNOWN_RECONCILIATION`. | Phase 9 trips `KillSwitchEvent`, freezes positions, rejects all target adjustments. |
| **Mathematical / Division Exception** | Handled via Pydantic finite Decimal validators. | Fail-closed exception boundary: any arithmetic error immediately defaults to `REJECTED`. |
| **Position Reversal / Short Attempt** | Phase 8 planner rejects negative positions ($q < 0$). | Phase 9 rejects any allocation with negative weights (strict long-only invariant). |
| **Bypass Attempt via Direct Transmission** | Phase 7 admission requires `LiveAuthorization` + `RiskState` + `intent_digest`. | Zero order transmission authority in Phase 9; cannot bypass Phase 7 admission. |

---

## 7. Open Architectural, Mathematical & Policy Questions

1. **Precision & Typing Policy in Risk Engine**:
   - *Question*: Should Phase 9 `DeterministicRiskEngine` operate purely on `Decimal` weights/notionals, or maintain compatibility with Phase 1 `float`-based `TargetAllocation` / `RiskAssessment`?
   - *Audit Finding*: Phase 1 `TargetAllocation` uses `Mapping[str, float]`, while Phase 8 uses `Mapping[str, Decimal]`.
   - *Recommendation*: Phase 9 should accept both via strict canonical Decimal conversion internally, ensuring finite precision and zero IEEE-754 rounding drift.
2. **Derisking Sizing Policy (`REDUCED` Verdict)**:
   - *Question*: When a candidate target allocation breaches a gross leverage or risk budget limit, how should weights be scaled down?
   - *Option A*: Uniform proportional scale-down: $w_i' = w_i \cdot \frac{\text{MaxLeverage}}{\sum w_i}$, residual to cash.
   - *Option B*: Binary rejection (no partial sizing): If limit breached, 100% Cash.
   - *Recommendation*: Support both via configurable policy (`EXACT_SCALE_DOWN` vs `BINARY_REJECT`).
3. **Kill Switch Reset & Recovery Semantics**:
   - *Question*: How can a tripped kill switch be deactivated?
   - *Audit Finding*: Phase 7 `reactivate_authorization()` requires Ed25519 multi-sig quorum.
   - *Recommendation*: Phase 9 Kill Switch must require identical explicit operator/multi-sig cryptographic quorum to reset.

---

## 8. Proposed Phase 9 Scope & Implementation Roadmap

```
Slice 1: Risk Domain Contracts & Mathematical Specifications (risk_schema.py)
   ├── RiskPolicyConfig (Frozen Pydantic contract: leverage, drawdown, concentration limits)
   ├── RiskVerdict / RiskEvaluationDecision (APPROVED, REDUCED, REJECTED)
   └── KillSwitchState (ACTIVE, TRIPPED, RESET_PENDING, PERSISTED)
   │
   ▼
Slice 2: Deterministic Risk Evaluation Engine (risk_engine.py)
   ├── Implement IRiskEngine interface
   ├── Exposure & Leverage Gating (Gross, Net, Single-Asset Concentration)
   ├── Drawdown & Loss Gating (Historical peak equity vs current valuation)
   └── Proportional Derisking & Weight Adjustment Algorithm
   │
   ▼
Slice 3: Sovereign Kill Switch Controller & Trigger Engine (kill_switch.py)
   ├── Real-time telemetry monitoring (latency, drift, disconnect, loss breach)
   ├── Multi-tier action dispatch (HALT_NEW_ORDERS, CANCEL_WORKING, EMERGENCY_FLATTEN)
   └── Cryptographic Quorum Reset & Persistence Ledger
   │
   ▼
Slice 4: Emergency Flattening & Order Intent Generator (emergency.py)
   ├── Translate open positions into risk-reducing market liquidation intents
   └── Parity reconciliation against broker account state
   │
   ▼
Slice 5: End-to-End Multi-Phase Integration Test Battery
   └── Full regression across Phase 8 -> Phase 9 -> Phase 7 integration seams (772+ green)
```

---

## 9. Verification & Anti-Duplication Ledger

```markdown
### Verification Ledger
- Inventory Audit Status: COMPLETE
- Inspected Source Files: 12 files across core, execution, portfolio, research
- Reused Components: PortfolioState, AccountState, RiskRestrictionAuthority, evaluate_kill_switch_triggers, RebalancePlanner
- Missing Components Identified: DeterministicRiskEngine, Proportional Derisking, KillSwitchController, Emergency Flattening Generator
- Current Test Baseline: 772 passed, exit code 0 (commit 9ce1365)
- MyPy Static Analysis: 0 errors
- Next Step: Present Audit Findings -> Draft Phase 9 Contract Specification & Red-Team Attack Matrix
```
