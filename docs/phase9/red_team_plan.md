# Phase 9: Deterministic Risk Engine & Kill Switch
## Red-Team Attack Matrix & Invariant Test Battery

> **Document:** `docs/phase9/red_team_plan.md`  
> **Status:** AUDIT & RED-TEAM ADVERSARIAL MATRIX (PRE-IMPLEMENTATION)  
> **Baseline Commit:** `9ce1365` (Phase 8.5 Frozen Baseline, 772/772 tests passing, 0 MyPy errors)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Tests Must Attack Assumptions)

---

## 1. Executive Summary

This document defines the formal **Adversarial Red-Team Attack Plan** for Phase 9. Before any production code is written, this plan defines the degenerate inputs, race conditions, boundary violations, malicious digests, and catastrophic failures that the Phase 9 test battery must actively attack.

In accordance with `AGENTS.md` Principle 14:
$$\text{Happy Path} \longrightarrow \text{Boundary} \longrightarrow \text{Malformed} \longrightarrow \text{Contradictory} \longrightarrow \text{Adversarial} \longrightarrow \text{Permutation} \longrightarrow \text{Numerical Stability} \longrightarrow \text{Golden Reference}$$

---

## 2. Red-Team Attack Matrix by Category

### Category 1: Market Data & Telemetry Adversarial Attacks

| Test ID | Attack Scenario | Injected Vector / Malformed Input | Expected Fail-Closed Behavior |
| :--- | :--- | :--- | :--- |
| **RT-DATA-01** | Stale Market Data Breach | `data_age_ms = 1501` ($> 1500\text{ms}$ threshold) | `evaluate_kill_switch_triggers()` emits `STALE_MARKET_DATA`; `KillSwitchController` trips `TRIPPED`; all evaluations emit `KILL_SWITCH_BLOCKED`. |
| **RT-DATA-02** | Extreme Clock Skew | `system_time - broker_time = 501ms` ($> 500\text{ms}$) | `evaluate_kill_switch_triggers()` emits `CLOCK_SKEW_DETECTED`; new allocations rejected. |
| **RT-DATA-03** | Non-Finite Market Prices | `reference_prices["AAPL"] = float("nan")` / `Decimal("Infinity")` | `RiskStateBridge` raises `DataContractError`; zero silent default fallback. |
| **RT-DATA-04** | Timestamp Rollback / Inversion | $T_{\text{eval}} < T_{\text{portfolio\_state}}$ | `DeterministicRiskEngine` raises `DataContractError` (temporal monotonicity violation). |
| **RT-DATA-05** | Silent Broker Disconnect | `is_broker_connected = False` | Emits `BROKER_DISCONNECTED`; `HALT_NEW_ORDERS` + `FREEZE_AND_RECONCILE`. |

---

### Category 2: Risk Limits & Capital Boundary Attacks

| Test ID | Attack Scenario | Injected Vector / Malformed Input | Expected Fail-Closed Behavior |
| :--- | :--- | :--- | :--- |
| **RT-RISK-01** | Gross Leverage Exceeded | $\sum w_i = 1.05 > \text{MaxGrossLeverage} (1.0)$ under `BINARY_REJECT` | Emits `RiskVerdict.REJECTED`; `adjusted_weights = {}`, `cash_weight = Decimal("1.0")`. |
| **RT-RISK-02** | Single-Asset Concentration | $w_{\text{NVDA}} = 0.35 > \text{MaxConcentration} (0.25)$ | `EXACT_SCALE_DOWN` scales $\alpha = \frac{0.25}{0.35} \approx 0.714$; `BINARY_REJECT` rejects. |
| **RT-RISK-03** | Peak Drawdown Breach | `current_drawdown_pct = 15.1% >= 15.0%` | Emits `KillSwitchTriggerType.MAX_DRAWDOWN`; trips Kill Switch; `EMERGENCY_FLATTEN` initiated. |
| **RT-RISK-04** | Cumulative Daily Loss Breach | $\text{Realized P&L}_{\text{today}} = -\$10,001 < -\$10,000$ limit | Emits `KillSwitchTriggerType.MAX_DAILY_LOSS`; trips Kill Switch; working orders cancelled. |
| **RT-RISK-05** | Negative Position / Short Invariant | Candidate allocation contains $w_{\text{SPY}} = -0.10$ | `DeterministicRiskEngine` immediately raises `DataContractError` (strict long-only invariant). |
| **RT-RISK-06** | Zero/Negative Account Equity | `account_state.equity = Decimal("0.00")` / `Decimal("-500.00")` | Raises `DataContractError`; halts all trading operations. |
| **RT-RISK-07** | Extreme Floating-Point Rounding Drift | $\sum w_i = 0.9999999999999999$ | `RiskStateBridge` normalizes via exact finite Decimal arithmetic; preserves exact $\sum w_i + w_{\text{cash}} = 1.0$. |

---

### Category 3: Derisking Algorithm Adversarial Attacks

| Test ID | Attack Scenario | Injected Vector / Malformed Input | Expected Fail-Closed Behavior |
| :--- | :--- | :--- | :--- |
| **RT-DRSK-01** | Repeated Iterative Derisking | Pass already-derisked $\mathbf{w}'$ back into `DeriskEngine` | **Idempotent**: $\alpha = 1.0$, output weights $\mathbf{w}'' \equiv \mathbf{w}'$. |
| **RT-DRSK-02** | Zero Leverage Pathological Case | Input candidate has $\sum w_i = 0.0$ (100% Cash) | Scale factor $\alpha = 1.0$; outputs 100% Cash safely without division-by-zero. |
| **RT-DRSK-03** | Monotonic Risk Preservation | Derisking allocation under positive weights | Assert $\forall i, w_i' \le w_i$ and $w_{\text{cash}}' \ge w_{\text{cash}}$. No position is inflated. |
| **RT-DRSK-04** | Cash Buffer Encroachment Attack | Scaled risky weights leave $w_{\text{cash}} < \text{MinCashBuffer}$ | Scaling factor $\alpha$ capped by cash constraint: $\alpha \le \frac{1.0 - \text{MinCashBuffer}}{\sum w_i}$. |

---

### Category 4: Kill Switch State Machine & Quorum Attacks

| Test ID | Attack Scenario | Injected Vector / Malformed Input | Expected Fail-Closed Behavior |
| :--- | :--- | :--- | :--- |
| **RT-KILL-01** | Duplicate Trigger Flooding | 100 identical breach events submitted in parallel | Idempotent transition to `TRIPPED`; exactly 1 persistent event logged. |
| **RT-KILL-02** | Unauthorized Reset Attempt | Single operator signature where `required_approvals = 2` | `PreLiveRiskAdmissionError` (Quorum not met); state remains `PERSISTENTLY_BLOCKED`. |
| **RT-KILL-03** | Tampered Reset Digest | Signature valid but payload modified (e.g. altered timestamp) | Digest mismatch check fails; reset rejected; state remains blocked. |
| **RT-KILL-04** | Process Crash & Restart Recovery | Process abruptly terminated while in `TRIPPED` state | On reboot, `KillSwitchController` reloads ledger and initializes as `PERSISTENTLY_BLOCKED`. |
| **RT-KILL-05** | Concurrent Reset vs Trigger Race | Reset request submitted simultaneously with new breach trigger | Fail-closed: New breach trigger wins; state returns to `TRIPPED`. |

---

### Category 5: Emergency Flattening Boundary Attacks

| Test ID | Attack Scenario | Injected Vector / Malformed Input | Expected Fail-Closed Behavior |
| :--- | :--- | :--- | :--- |
| **RT-FLAT-01** | Direct Wire Transmission Attempt | Test attempts to call broker REST endpoint from Phase 9 | **Architectural Assertion**: Phase 9 module has 0 network/broker imports. |
| **RT-FLAT-02** | Partial Liquidation State | Broker fills half of position, remaining order open | `ExecutionCoordinator` tracks `filled_qty`; Phase 9 reconciles remaining delta without double-selling. |
| **RT-FLAT-03** | Unknown Broker Position State | `PortfolioState.positions` in conflict with broker snapshot | `CoordinatorIncident(RECONCILIATION_CONFLICT)` opens restriction; halts automated liquidations until human audit. |

---

### Category 6: Cryptographic Integrity & Tampering Attacks

| Test ID | Attack Scenario | Injected Vector / Malformed Input | Expected Fail-Closed Behavior |
| :--- | :--- | :--- | :--- |
| **RT-INT-01** | Altered Allocation Decision Digest | Modify `authorized_weights` after decision signed | `recompute_digest(decision) != decision.decision_digest` $\to$ `DataContractError`. |
| **RT-INT-02** | Replayed / Outdated Risk Evaluation | Submit RiskEvaluationReport with past epoch timestamp | Phase 7 admission detects expired authorization or stale evaluation. |
| **RT-INT-03** | Policy Version Mismatch | Evaluate candidate under `v1.0.0` policy against `v2.0.0` engine | Report digest reflects engine policy mismatch; rejected at admission boundary. |

---

## 3. Sovereign Authority Proof Assertions

The test battery must execute formal unit and integration assertions verifying the separation of concerns:

1. **Phase 8.5 Authority Proof:**
   $$\forall s \in \text{AlphaLifecycleState}, \quad \text{dossier.capital\_authority\_usd} \equiv \text{Decimal("0.00")}$$
2. **Phase 8 Authority Proof:**
   $$\text{AllocationDecision} \text{ produces target weights but CANNOT bypass Risk Engine or emit raw Orders.}$$
3. **Phase 9 Authority Proof:**
   $$\text{RiskVerdict.REJECTED} \implies \text{Zero OrderIntents constructed in Phase 7.}$$
   $$\text{KillSwitchState.TRIPPED} \implies \text{All Phase 7 Order Construction blocked immediately.}$$
4. **Phase 7 Authority Proof:**
   $$\text{Phase 7 is the SOLE module authorized to transition order states and interface with broker adapters.}$$

---

## 4. Open Mathematical & Policy Questions for Implementation

The following items are designated as `[OPEN QUESTION]` to be locked in the final implementation plan:

1. **Drawdown Reference Benchmark**:
   - High-water mark should track `PortfolioState.total_equity` peak since session inception or lifetime peak.
   - *Default Policy*: Inception-to-date peak equity.
2. **Intraday Loss Reset Boundary**:
   - Exact UTC rollover boundary (00:00:00 UTC) for resetting `realized_pnl_today`.
3. **Concentration Denominator**:
   - Single-asset concentration calculated as $\frac{\text{Market Value}_i}{\text{Total Equity}}$ or $\frac{w_i}{\sum w_i}$.
   - *Default Policy*: $\frac{\text{Market Value}_i}{\text{Total Equity}}$.
4. **Kill Switch Multi-Sig Quorum**:
   - Pinned to 2-of-3 Ed25519 signatures from authorized risk officer key IDs.

---

## 5. Anti-Duplication Inventory

| Target Functionality | Reused Existing Implementation | Do NOT Duplicate |
| :--- | :--- | :--- |
| **Double-Entry Accounting** | `PortfolioState.validate_accounting_invariants()` | Do NOT write secondary equity calculator. |
| **Market Data Age & Drift Detection** | `evaluate_kill_switch_triggers()` in `admission.py` | Do NOT write redundant trigger detection logic. |
| **Operational Restriction Locks** | `RiskRestrictionAuthority` in `operational_restriction.py` | Do NOT implement separate locking ledger. |
| **Cryptographic Hashing & Lineage** | `CanonicalConfigSerializer` in `core/serialization.py` | Do NOT use raw `json.dumps()` or uncanonical dicts. |
| **Order State Transitions** | `transition_order()` in `execution/state_machine.py` | Do NOT mutate order states inside Risk Engine. |

---

## 6. Verification Ledger

```markdown
### Verification Ledger
- Red-Team Matrix Status: COMPLETE (6 Categories, 25 Adversarial Attacks Defined)
- Invariant Testing Order: Happy Path -> Boundary -> Malformed -> Adversarial -> Golden Reference
- Anti-Duplication Verification: 5 Key Systems Reused
- Production Code Written: ZERO (Pure specification and red-team plan)
- Next Step: Present Contract Spec & Red-Team Plan for Approval -> Create Implementation Plan
```
