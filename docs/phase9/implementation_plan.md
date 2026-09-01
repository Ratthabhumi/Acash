# Phase 9: Deterministic Risk Engine & Kill Switch
## Canonical Implementation Plan (Contract v1.1 Locked)

> **Document:** `docs/phase9/implementation_plan.md`  
> **Status:** APPROVED & LOCKED FOR EXECUTION  
> **Baseline Commit:** `9ce1365` (Phase 8.5 Frozen Baseline, 772/772 passing tests, 0 MyPy errors)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Authority, Strict Fail-Closed, Separation of Concerns)

---

## 1. Executive Summary & Core Architectural Invariants

Phase 9 implements the **Deterministic Risk Engine & Kill Switch** for the ACASH quantitative trading engine. It acts as the non-negotiable sovereign runtime control plane between Phase 8 (Portfolio Allocation & Rebalance Planning) and Phase 7 (Pre-Live Risk Admission & Execution Coordination).

### Non-Negotiable Architectural Invariants:
1. **Four-Way Sovereign Separation:**
   $$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)}}$$
2. **Sovereign Risk Veto:**
   $$\boxed{\mathbf{Risk\ Rejection} \implies \text{Execution Blocked (Fail-Closed, 0 Orders Allowed)}}$$
3. **Zero Direct Execution Authority in Phase 9:**
   $$\boxed{\mathbf{Risk\ Approval} \neq \text{Execution Authorization} \quad \land \quad \mathbf{Phase\ 9} \nRightarrow \text{Direct Broker Wire Access}}$$
4. **Emergency Intent Generation $\neq$ Flatten Completion:**
   $$\boxed{\mathbf{EmergencyFlattenIntent\ Emitted} \neq \mathbf{Positions\ Flattened}}$$
5. **Strict Fail-Closed Contract:**
   *Any missing data, non-nominal calculation status, non-finite arithmetic, clock skew, or unhandled exception immediately results in `RiskVerdict.REJECTED` or `KillSwitchState.TRIPPED`.*

---

## 2. Inventory of Reused Existing Components (Zero Duplication)

| Existing Component | Source Location | Reused Role in Phase 9 | Invariant Preserved |
| :--- | :--- | :--- | :--- |
| **`PortfolioState` & `AccountState`** | `src/acash/core/domain/portfolio.py` | Double-entry accounting state snapshots | Strict accounting conservation |
| **`TargetAllocation` & `RiskAssessment`** | `src/acash/core/domain/signal.py` | Base domain target and risk models | Domain contract integrity |
| **`IRiskEngine`** | `src/acash/core/interfaces/risk.py` | Canonical abstract risk interface | Interface authority |
| **`RebalancePlan` & `AllocationDecision`** | `src/acash/portfolio/planner.py`, `schema.py` | Candidate input proposals to be evaluated | Phase 8 $\to$ Phase 9 forward flow |
| **`evaluate_kill_switch_triggers()`** | `src/acash/execution/admission.py` | Telemetry anomaly trigger detection | Detection $\neq$ State machine |
| **`RiskRestrictionAuthority`** | `src/acash/execution/operational_restriction.py` | Phase 7 operational lock enforcement | Execution boundary isolation |
| **`Ed25519TrustStore`** | `src/acash/execution/crypto.py` | Multi-sig cryptographic quorum verification | Authorized deactivation |
| **`CanonicalConfigSerializer`** | `src/acash/core/serialization.py` | Cryptographic SHA-256 digests | Single serialization authority |

---

## 3. Implementation Slices & Execution Order

```
Slice 1: Domain Contracts & Configuration (risk_schema.py)
   │
   ▼
Slice 2: Deterministic Risk Engine & Derisking (risk_engine.py)
   │
   ▼
Slice 3: Sovereign Kill Switch Controller & Ledger (kill_switch.py)
   │
   ▼
Slice 4: Emergency Flattening Intent Generator (emergency.py)
   │
   ▼
Slice 5: Type-Safe Risk State Bridge (bridge.py)
   │
   ▼
Slice 6: Full Multi-Phase Integration Pipeline & Freeze Verification
```

---

### Slice 1: Domain Contracts & Configuration
- **File:** `src/acash/risk/risk_schema.py`
- **Tests:** `tests/unit/risk/test_risk_schema.py`
- **Tasks:**
  1. Implement `RiskVerdict`, `DeriskPolicy`, and `KillSwitchState` enums.
  2. Implement `RiskPolicyConfig` with frozen configuration, finite Decimal validators, and canonical digest calculation.
  3. Implement `RiskEvaluationReport`, `KillSwitchResetEvent`, and `EmergencyFlattenIntent` data contracts.
  4. Write unit tests for immutability (`frozen=True`, `extra="forbid"`), finite Decimals, and valid JSON serialization.

---

### Slice 2: Deterministic Risk Engine & Derisking
- **File:** `src/acash/risk/risk_engine.py`
- **Tests:** `tests/unit/risk/test_risk_engine.py`
- **Tasks:**
  1. Implement `DeterministicRiskEngine` realizing the `IRiskEngine` interface.
  2. Implement multi-tier exposure evaluations (gross leverage, asset concentration, mandatory cash buffer).
  3. Implement drawdown and daily loss boundary checks.
  4. Implement `DeriskEngine` realizing `EXACT_SCALE_DOWN` (monotonically proven uniform scale-down) and `BINARY_REJECT`.
  5. Write adversarial unit tests attacking limit breaches, negative positions, division-by-zero, and non-finite inputs.

---

### Slice 3: Sovereign Kill Switch Controller & Ledger
- **File:** `src/acash/risk/kill_switch.py`
- **Tests:** `tests/unit/risk/test_kill_switch.py`
- **Tasks:**
  1. Implement `KillSwitchController` managing `ACTIVE -> TRIPPED -> PERSISTENTLY_BLOCKED -> RESET` lifecycle.
  2. Implement local state persistence (`data/risk/kill_switch_state.json`) and crash recovery on startup.
  3. Implement multi-sig reset verification via `Ed25519TrustStore` with required approval quorum.
  4. Write unit tests for trigger flooding, unauthorized resets, tampered digests, and restart recovery.

---

### Slice 4: Emergency Flattening Intent Generator
- **File:** `src/acash/risk/emergency.py`
- **Tests:** `tests/unit/risk/test_emergency_flatten.py`
- **Tasks:**
  1. Implement `generate_emergency_flatten_intent()` translating active `PortfolioState.positions` into zero-target liquidation orders.
  2. Enforce separation of concerns: Phase 9 generates intent; Phase 7 admits, transmits, and reconciles.
  3. Implement flatten completion verification check (`is_flatten_completed(portfolio_state) -> bool`).
  4. Write adversarial tests verifying zero wire communication in Phase 9 and exact opposite-side delta calculations.

---

### Slice 5: Type-Safe Risk State Bridge
- **File:** `src/acash/risk/bridge.py`
- **Tests:** `tests/unit/risk/test_risk_bridge.py`
- **Tasks:**
  1. Implement `convert_target_allocation()`, `convert_portfolio_state()`, and `convert_risk_state()`.
  2. Enforce strict finite Decimal conversions and validate long-only bounds.
  3. Fail-closed immediately upon encountering NaN, Infinity, negative equity, or unmapped symbols.
  4. Write unit tests attacking malformed, missing, and non-finite data structures.

---

### Slice 6: Multi-Phase Integration Pipeline & Freeze Verification
- **File:** `src/acash/risk/__init__.py`
- **Tests:** `tests/integration/test_risk_engine_pipeline.py`
- **Tasks:**
  1. Implement end-to-end multi-phase integration pipeline:
     $$\text{Phase 8.5 Dossier} \to \text{Phase 8 Plan} \to \text{Phase 9 Risk Engine} \to \text{Phase 7 Admission} \to \text{Broker}$$
  2. Verify that rejected allocations produce 0 orders in Phase 7.
  3. Verify that tripped kill switches immediately halt order admission.
  4. Verify that full repository test suite (772+ tests) passes with 0 regressions and 0 MyPy errors.
  5. Declare Phase 9 Complete & Frozen.

---

## 4. Comprehensive Test Strategy & Acceptance Criteria

| Test Category | Target Module | Invariant / Failure Mode Attacked |
| :--- | :--- | :--- |
| **Contract Invariants** | `test_risk_schema.py` | Immutability, `extra="forbid"`, finite Decimals, valid digests. |
| **Exposure & Leverage Gates** | `test_risk_engine.py` | Gross leverage $> 1.0$, concentration $> 0.25$, cash buffer $< 0.05$. |
| **Derisking Sizing Math** | `test_risk_engine.py` | Monotonicity, no short creation, cash buffer preserved, idempotency. |
| **Kill Switch State Machine** | `test_kill_switch.py` | Immediate lockout, crash recovery, multi-sig reset quorum verification. |
| **Emergency Flattening Boundary** | `test_emergency_flatten.py` | Zero wire access in Phase 9, exact opposite-side liquidation deltas. |
| **Risk-State Bridge Precision** | `test_risk_bridge.py` | NaN/Inf rejection, exact Decimal casting, zero silent float drift. |
| **Full Multi-Phase Pipeline** | `test_risk_engine_pipeline.py` | Phase 8 $\to$ Phase 9 $\to$ Phase 7 end-to-end integration (772+ green). |

---

### Implementation Readiness Ledger
- Design Specification: **CONTRACT v1.1 (LOCKED)**
- Reused Components: **8 EXISTING ENGINES INTEGRATED (ZERO DUPLICATION)**
- New Modules: **`risk_schema.py`, `risk_engine.py`, `kill_switch.py`, `emergency.py`, `bridge.py`**
- Execution Authority in Phase 9: **EXPLICITLY ZERO (BROKER ACCESS PROHIBITED)**
- Next Step: **Begin TDD Implementation of Slice 1 upon User Approval.**
