# Phase 13 — Live Small Capital Deployment
# Plan Revision 2: Pre-Live Readiness & Small Capital Architecture

> **Document:** `docs/phase13/PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV2.md`
> **Status:** DRAFT — PENDING USER AUDIT & APPROVAL
> **Plan Revision:** Rev2 (addresses Rev1 audit findings: P0-1, P0-2, P1-1, P1-2)
> **Date:** 2026-09-03
> **Frozen Execution Baseline:** `1e1d154` (Phase 12 — CLOSED & FROZEN)
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed)
> **TradingView:** OUT OF SCOPE — separate independent backlog item

---

## Rev2 Changelog (vs Rev1 Audit Findings)

| Finding | Rev1 Status | Rev2 Resolution |
|---------|-------------|-----------------|
| P0-1: Gate B machine enforcement undefined | ❌ | Section 4: `LiveAuthorization.max_notional` as machine-enforceable capital ceiling; `authorization_digest` semantics defined |
| P0-2: Signed authorization vs verbal GO conflated | ❌ | Section 14: Machine Gate vs Human Governance Gate explicitly separated |
| P1-1: Monitoring alerting TBD | ⚠️ | Section 11: Concrete DEGRADED response mechanism defined |
| P1-2: PERSISTENTLY_BLOCKED vs EmergencyFlatten semantics | ⚠️ | Section 7 + 13: Gap identified; architectural implication declared; close-only path documented |

> [!IMPORTANT]
> Rev2 does NOT add new subsystems, rewrite existing contracts, or add code.
> All resolutions are clarifications of existing frozen architecture, with explicit gaps named.

---

## 0. Scope of This Document

This plan defines:
1. **What Phase 13 is** — and what it is not
2. **What ACASH must prove** before a human authorizes the first live capital
3. **Gate A: Pre-Live Certification** — what must be verified while still at $0.00
4. **Gate B: Human Authorization** — the explicit approval event that changes live capital from $0.00

> [!IMPORTANT]
> This Rev2 plan does NOT implement live trading.
> Live capital remains at $0.00 until Gate B is explicitly signed off.
> No production code change is authorized from this document alone.

---

## 1. Phase 13 Objective

Deploy ACASH in a **real live broker account with a strictly bounded micro-capital allocation**, subject to all Phase 9 risk boundaries, Phase 12 execution lifecycle contracts, and Mandatory Human Approval.

**Phase 13 success criterion:**
$$\boxed{\text{First real live order lifecycle} \to \text{FILLED/RECONCILED} \land \text{All risk boundaries enforced} \land \text{Kill switch operational}}$$

**Phase 13 is explicitly NOT:**
- A TradingView integration phase
- A new execution architecture phase
- A strategy research phase
- A capital growth phase

---

## 2. Non-Goals (Explicit)

| Item | Status |
|------|--------|
| TradingView Ingress Gateway | ❌ OUT OF SCOPE (separate backlog) |
| New broker adapters | ❌ OUT OF SCOPE |
| New lifecycle states | ❌ OUT OF SCOPE |
| New state transition authority | ❌ OUT OF SCOPE |
| Capital growth / scaling | ❌ OUT OF SCOPE |
| Rewrite of RECON-6D | ❌ OUT OF SCOPE |
| Rewrite of ExecutionCoordinator | ❌ OUT OF SCOPE |
| New capital authority subsystem | ❌ OUT OF SCOPE (existing `LiveAuthorization` is sufficient) |
| Automated live trading without human approval | ❌ PERMANENTLY PROHIBITED |

---

## 3. Two-Gate Structure

```
Phase 12 FROZEN (1e1d154)
         │
         ▼
┌────────────────────────────────────────────────────┐
│ GATE A — PRE-LIVE CERTIFICATION                    │
│ (Still at $0.00 live capital)                      │
│                                                    │
│  A-1  Risk limits configured & verified            │
│  A-2  Kill switch operational (PERSISTENTLY_BLOCKED│
│       recovery verified)                           │
│  A-3  MT5 demo account full lifecycle evidence     │
│  A-4  6-D Reconciliation verified on demo          │
│  A-5  Monitoring / ForwardHealthState verified     │
│  A-6  Emergency flatten intent verified on demo    │
│  A-7  Emergency close-only path clarified (→ S7.3) │
│  A-8  Failure / recovery procedures documented     │
│  A-9  Position sizing confirmed                    │
│  A-10 Rollback / emergency stop tested on demo     │
│  A-11 DEGRADED alert mechanism verified (→ S11.2)  │
└────────────────────────────────────────────────────┘
         │
         │  All A-* items: PASS
         ▼
┌────────────────────────────────────────────────────┐
│ GATE B — MANDATORY HUMAN AUTHORIZATION             │
│                                                    │
│ [Machine Gate — cryptographically enforced]        │
│  B-1  LiveAuthorization constructed                │
│  B-2  Human-signed AuthorizationApproval quorum    │
│  B-3  authorization_digest verified                │
│  B-4  AuthorizationStatus → ACTIVE                 │
│                                                    │
│ [Human Governance Gate — organizational record]    │
│  B-5  Human reviews Gate A evidence                │
│  B-6  Human confirms live broker account           │
│  B-7  Human confirms capital limit (max_notional)  │
│  B-8  Human confirms all limit fields              │
│  B-9  Human issues explicit GO declaration         │
└────────────────────────────────────────────────────┘
         │
         │  Machine Gate: ACTIVE status enforced
         │  Governance Gate: GO on record
         ▼
    $0.00 → Small Capital (max_notional as enforced ceiling)
    First live order authorized
```

---

## 4. Capital Limit — Machine-Enforceable Ceiling

### 4.1 `LiveAuthorization.max_notional` — Verified Source

From `src/acash/execution/schema.py:278`:
```python
class LiveAuthorization(BaseModel):
    max_notional: Decimal = Field(description="Maximum total notional exposure.")
    max_position_size: Decimal = Field(...)
    max_daily_loss_notional: Decimal = Field(...)
    max_drawdown_pct: Decimal = Field(...)
    allowed_venues: Tuple[str, ...]
    allowed_symbols: Tuple[str, ...]
    authorization_digest: str  # SHA-256 over ALL above fields + approval_digests
```

`max_notional` is **bound in `authorization_digest`** via `compute_authorization_digest()` (`schema.py:349`). Any change to `max_notional` invalidates the digest. This is the machine-enforceable capital ceiling.

### 4.2 Machine Authorization Semantics for Gate B

Gate B is machine-enforced through the following chain (all frozen, verified in source):

```
Human signs AuthorizationApproval (Ed25519 signature)
     │
     ▼
Ed25519TrustStore.verify() (kill_switch.py / admission.py)
     │
     ▼
|verified approvals| >= required_approvals
     │
     ▼
compute_authorization_digest() → authorization_digest sealed
     │
     ▼
LiveAuthorization.status → ACTIVE
     │
     ▼
construct_order_intent() enforces at admission:
  ├─ status == ACTIVE         (admission.py:650)
  ├─ restriction_authority gate (admission.py:656)
  ├─ not expired              (admission.py:668)
  ├─ venue in allowed_venues  (admission.py:674)
  ├─ symbol in allowed_symbols (admission.py:679)
  ├─ quantity <= max_position_size (admission.py:685)
  ├─ risk_status == NORMAL    (admission.py:696)
  └─ calculation_status == NOMINAL (admission.py:691)
```

**If `status != ACTIVE`, `construct_order_intent()` raises `PreLiveRiskAdmissionError` (fail-closed).**
No order can be created without an ACTIVE `LiveAuthorization`.

### 4.3 Known Gap: Cumulative `max_notional` Enforcement

> [!WARNING]
> **Verified source gap (P1 debt, not P0 blocker):**
> `construct_order_intent()` enforces `quantity <= max_position_size` per-order,
> but does NOT enforce cumulative notional against `max_notional` at admission time.
> `max_notional` is validated as `>= max_position_size` at `LiveAuthorization` construction,
> but runtime cumulative exposure tracking against this ceiling is NOT implemented in the current admission gate.
>
> **Phase 13 mitigation:** `max_position_size` == `volume_min` (0.01 lot), max 1 concurrent position,
> `DeterministicRiskEngine.max_daily_loss_usd` as independent runtime ceiling.
> This combination makes inadvertent breach of `max_notional` unlikely at micro-lot scale.
> A future phase must implement explicit cumulative notional tracking in admission.

### 4.4 Capital Parameters (Human confirms at Gate B)

| Parameter | Field | Phase 13 Constraint | Who Sets |
|-----------|-------|---------------------|----------|
| Capital ceiling | `max_notional` | TBD — human confirms USD amount at Gate B | Human only |
| Per-order max size | `max_position_size` | `volume_min` (0.01 lot) | Human confirms |
| Daily loss halt | `max_daily_loss_notional` | TBD — scaled to live capital | Human only |
| Drawdown halt | `max_drawdown_pct` | TBD — propose ≤ 5% initial | Human confirms |
| Venue whitelist | `allowed_venues` | Live MT5 venue only | Human confirms |
| Symbol whitelist | `allowed_symbols` | Initial target symbols only | Human confirms |
| Expiry | `expires_at` | Mandatory — time-boxed authorization | Human confirms |

> [!CAUTION]
> No agent may construct or activate a `LiveAuthorization` unilaterally.
> Capital limits are set exclusively by the human at Gate B via the Ed25519 multi-sig quorum.

---

## 5. Broker / Account Boundary

### 5.1 Broker Adapter
- **Adapter:** `MT5BrokerAdapter` (Phase 12 — FROZEN, `1e1d154`)
- **Transport:** `NativeMT5Transport` (IPC to local MT5 terminal)
- **No new broker adapters** in Phase 13 initial scope

### 5.2 Account Separation

```
ACASH Live Account (Phase 13)
  └── Distinct from any paper/demo account
  └── Credentials: Windows DPAPI — separate vault entry from demo
  └── Identity Triad:
        Credential Owner ≡ Adapter Runtime ≡ Terminal Process Owner
  └── allowed_venues in LiveAuthorization includes ONLY live venue ID
  └── Demo venue ID MUST NOT appear in allowed_venues for live authorization
```

> [!WARNING]
> Live credentials MUST use a separate DPAPI vault entry from demo credentials.
> Demo venue ID must never appear in a live `LiveAuthorization.allowed_venues`.

### 5.3 Paper/Live Hard Separation

| Boundary | Enforcement |
|----------|-------------|
| Demo adapter | Initialized with demo credentials; `allowed_venues` = demo venue |
| Live adapter | Initialized with live credentials; `allowed_venues` = live venue |
| Venue cross-contamination | `construct_order_intent()` venue check blocks it fail-closed |
| Mixed-account dispatch | Impossible — each `MT5BrokerAdapter` instance binds one account |

---

## 6. Risk Limits

All limits enforced by **Phase 9 `DeterministicRiskEngine`** (frozen, `6bd40d8`) — no rewrite.

### 6.1 Existing Risk Parameters (`RiskPolicyConfig`)

| Parameter | Field | Phase 13 Constraint | Enforcement |
|-----------|-------|---------------------|-------------|
| Max gross leverage | `max_gross_leverage` | ≤ 1.00 (no leverage) | `DeterministicRiskEngine.evaluate()` → `BINARY_REJECT` |
| Max drawdown | `max_drawdown_limit_pct` | Human confirms at Gate B | → `MAX_DRAWDOWN_BREACHED` → `BINARY_REJECT` |
| Max daily loss | `max_daily_loss_usd` | Human confirms at Gate B | → `MAX_DAILY_LOSS_BREACHED` → `BINARY_REJECT` |

`BINARY_REJECT` → `RiskStatus != NORMAL` → `construct_order_intent()` raises `PreLiveRiskAdmissionError` (fail-closed).

### 6.2 Dual Capital Ceiling (Layered Defence)

```
Layer 1: LiveAuthorization.max_notional (admission gate — static ceiling)
Layer 2: LiveAuthorization.max_daily_loss_notional (daily dynamic halt)
Layer 3: RiskPolicyConfig.max_daily_loss_usd (DeterministicRiskEngine — independent)
Layer 4: RiskPolicyConfig.max_drawdown_limit_pct (equity-based halt)
Layer 5: can_dispatch() — RECON + READY gate (broker adapter)
```

These are independent layers. Breaching any single layer blocks execution.

---

## 7. Kill Switch — PERSISTENTLY_BLOCKED Semantics (P1-2 Resolved)

### 7.1 Existing Implementation (Phase 9 — frozen `6bd40d8`)

```
assert_admission_allowed()  [kill_switch.py:158]
  └─ if is_blocked → raise DataContractError("EXECUTION_ADMISSION_BLOCKED")

is_blocked == True when:
  KillSwitchState ∈ {TRIPPED, PERSISTENTLY_BLOCKED}

PERSISTENTLY_BLOCKED:
  - Survives process restart (disk-persisted ledger)
  - SHA-256 tamper-evident event chaining
  - Corrupted ledger → fail-closed to PERSISTENTLY_BLOCKED
  - Reset requires Ed25519 quorum + non-empty root cause
```

### 7.2 PERSISTENTLY_BLOCKED Blocks ALL Dispatch — Including Emergency Close

> [!WARNING]
> **Verified source finding:** `assert_admission_allowed()` blocks ALL order dispatch when `PERSISTENTLY_BLOCKED`.
> There is NO close-only exception in the current codebase.
>
> `EmergencyFlattenGenerator.generate_flatten_intent()` produces an `EmergencyFlattenIntent` record —
> this is an **intent artifact only**, NOT a dispatch primitive.
> The actual close orders must route through `ExecutionCoordinator` → `MT5BrokerAdapter`,
> which is blocked when kill switch is PERSISTENTLY_BLOCKED.

### 7.3 Emergency Close-Only Gap — Architectural Declaration

**Current state of architecture (FROZEN):**
```
KillSwitch.TRIPPED → PERSISTENTLY_BLOCKED
    │
    ├─ EmergencyFlattenGenerator.generate_flatten_intent() → EmergencyFlattenIntent
    │    (intent record only — does NOT dispatch)
    │
    └─ Dispatch path:
         ExecutionCoordinator
              ↓
         assert_admission_allowed() → DataContractError  ← BLOCKS CLOSE ORDER TOO
```

**Implication:** In Phase 13, if PERSISTENTLY_BLOCKED is triggered while a position is open, automated emergency close is currently blocked by the admission gate. The operator must manually close positions in the MT5 terminal.

> [!IMPORTANT]
> **Phase 13 Gate A must explicitly verify this behavior on demo:**
> - Trigger kill switch while a demo position is open
> - Confirm PERSISTENTLY_BLOCKED blocks automated close
> - Confirm manual MT5 terminal close triggers UNTRACKED_TRADE_DEAL → BLOCKED state
> - Confirm operator procedure: manual close → restart → fresh RECON
>
> **A future phase (not Phase 13) may implement a close-only emergency dispatch channel.**
> This requires an explicit architecture review and contract change.

### 7.4 Emergency Flatten Semantics (Corrected)

```
EmergencyFlattenGenerator.generate_flatten_intent()
    └─ Input: KillSwitchState ∈ {TRIPPED, PERSISTENTLY_BLOCKED}
    └─ Output: EmergencyFlattenIntent (intent record only)
    
EmergencyFlattenTracker.verify_flatten_completion()
    └─ Input: EmergencyFlattenIntent + current PortfolioState
    └─ Output: completion status (tracker only, no dispatch)

Phase 13 emergency close procedure:
    1. Kill switch trips → PERSISTENTLY_BLOCKED
    2. EmergencyFlattenGenerator produces intent record (forensic)
    3. Automated dispatch blocked (no close-only exception currently)
    4. Operator closes positions manually in MT5 terminal
    5. Manual close → UNTRACKED_TRADE_DEAL discrepancy detected
    6. Adapter → BLOCKED state
    7. Operator documents root cause
    8. Fresh process restart + 6-D RECON cycle
    9. Kill switch quorum reset (if applicable)
```

---

## 8. Position Sizing

### 8.1 MT5 Volume Contract (Frozen Phase 12)

```python
# BrokerSymbolSpec (src/acash/execution/mt5/schemas.py)
volume_min  : Decimal  # e.g. 0.01 lot
volume_step : Decimal
volume_max  : Decimal
```

Phase 13 initial constraint:
$$\text{max\_position\_size} \equiv \text{volume\_min} \quad (0.01\ \text{lot per order})$$

`max_position_size == volume_min` is encoded in the signed `LiveAuthorization` → bound in `authorization_digest`.

### 8.2 Sizing Enforcement (Frozen)

- `VOLUME_BELOW_MINIMUM` → `DataContractError` (fail-closed)
- `VOLUME_ABOVE_MAXIMUM` → `DataContractError` (fail-closed)
- `quantity > max_position_size` → `PreLiveRiskAdmissionError` at `construct_order_intent()` (fail-closed)

---

## 9. Daily Loss Limit & Max Exposure

| Limit | Field | Enforcement Point | Fail-Closed |
|-------|-------|-------------------|-------------|
| Daily loss | `LiveAuthorization.max_daily_loss_notional` | runtime tracking (future) | Yes |
| Daily loss | `RiskPolicyConfig.max_daily_loss_usd` | `DeterministicRiskEngine` | Yes → BINARY_REJECT |
| Max exposure | `LiveAuthorization.max_notional` | authorization ceiling | Yes (static) |
| Gross leverage | `RiskPolicyConfig.max_gross_leverage` | `DeterministicRiskEngine` | Yes → BINARY_REJECT |
| Drawdown | `LiveAuthorization.max_drawdown_pct` | runtime tracking (future) | Yes |
| Drawdown | `RiskPolicyConfig.max_drawdown_limit_pct` | `DeterministicRiskEngine` | Yes → BINARY_REJECT |

> Note: `LiveAuthorization` limit fields and `RiskPolicyConfig` limit fields are independent layers.
> Both must be configured with consistent values by the human at Gate B.

---

## 10. Reconciliation Requirement

### 10.1 6-D Reconciliation (Frozen Phase 12 Contract)

```
can_dispatch() == True iff:
  safety_state == READY    (adapter.py:197)
  AND is_reconciled == True (adapter.py:200)
```

All 6 dimensions pass before dispatch is enabled. `UNKNOWN` or `BLOCKED` → `can_dispatch() == False`.

### 10.2 Phase 13 Reconciliation Cadence (Gate A verification)

- Reconciliation cycle runs on startup against live account
- `UNKNOWN` (connection loss) → all dispatch blocked → RECON required before resume
- `BLOCKED` (CRITICAL discrepancy) → operator intervention
- `UNTRACKED_TRADE_DEAL` after manual MT5 close → triggers BLOCKED → documented in Section 7.4

---

## 11. Monitoring & Alerting (P1-1 Resolved)

### 11.1 Existing Implementation (Phase 11 — frozen `092a2b1`)

```
ForwardHealthState:
  HEALTHY           → no action
  INSUFFICIENT_EVIDENCE → no action (accumulating)
  DEGRADED          → DEGRADED_PROBATION recommendation
  MONITORING_BLOCKED → telemetry failure (NOT performance evidence)

MonitoringEvidenceLedger:
  Append-only SHA-256 chained ledger
  Epoch recovery via reinitialize_stream()
```

### 11.2 Concrete DEGRADED Alert Mechanism (Phase 13 Minimum)

Gate A must verify ALL of the following before Gate B:

**DEGRADED trigger:**
```
ForwardHealthStateMachine.advance()
  → ForwardHealthState.DEGRADED
  → ForwardGovernanceRecommendation.DEGRADED_PROBATION
```

**Minimum alert response chain for Phase 13 (no UI required):**
```
State → DEGRADED
     │
     ▼
MonitoringEvidenceLedger records evidence (forensic)
     │
     ▼
Runtime supervisor logs structured WARNING:
  {
    "level": "WARNING",
    "event": "STRATEGY_DEGRADED",
    "state": "DEGRADED",
    "recommendation": "DEGRADED_PROBATION",
    "timestamp_utc": "...",
    "strategy_id": "...",
    "trigger_metrics": {...}
  }
     │
     ▼
Operator must acknowledge within defined SLA
(Phase 13 SLA: operator actively monitors logs during trading hours)
     │
     ▼
If no acknowledgement / escalation:
  Operator manually trips kill switch
```

**MONITORING_BLOCKED response:**
```
MONITORING_BLOCKED ≠ DEGRADED
MONITORING_BLOCKED = telemetry disruption
  → logs structured ERROR
  → NOT treated as strategy decay evidence
  → operator investigates telemetry pipeline
```

> [!NOTE]
> Phase 13 does not implement a real-time alerting UI.
> The Gate A requirement is that structured WARNING logs are verified observable
> and the operator has a documented acknowledgement procedure.
> A future phase may implement push notifications or a dashboard.

---

## 12. Recovery Procedure

### 12.1 Connection Loss Recovery

```
Connection loss detected
    │
    ▼
In-flight orders → UNKNOWN lifecycle state
    │
    ▼
can_dispatch() == False (all dispatch blocked)
    │
    ▼
Wait for MT5 terminal reconnection
    │
    ▼
Run 6-D Reconciliation cycle
    ├─ PASS → safety_state → READY → can_dispatch() → True → resume
    └─ FAIL → BLOCKED → operator intervention required
```

### 12.2 CRITICAL Discrepancy Recovery

```
UNTRACKED_TRADE_DEAL detected
    │
    ▼
MT5ReconciliationError raised
    │
    ▼
Adapter → BLOCKED (absorbing state)
    │
    ▼
ALL dispatch blocked (including automated emergency close — see Section 7.3)
    │
    ▼
Operator investigates; root cause documented
    │
    ▼
Kill switch reset (Ed25519 quorum if PERSISTENTLY_BLOCKED)
    │
    ▼
Restart + fresh 6-D Reconciliation cycle
```

### 12.3 Process Crash Recovery

```
ACASH crash
    │
    ▼
SovereignKillSwitchController reads persisted ledger
    ├─ ARMED → restart in ARMED
    ├─ TRIPPED → restart in PERSISTENTLY_BLOCKED (fail-closed)
    └─ Corrupted ledger → startup halt (fail-closed)
         │
         ▼
6-D RECON required before any dispatch
```

---

## 13. Rollback / Emergency Stop (P1-2 Resolved)

### 13.1 Emergency Flatten — Corrected Semantics

`EmergencyFlattenGenerator` produces `EmergencyFlattenIntent` — an **intent record and forensic artifact**, NOT a dispatch primitive. It does not directly close positions.

### 13.2 Emergency Stop Sequence (Phase 13 Actual Behavior)

```
Emergency trigger (automated risk breach OR human operator)
     │
     ▼
SovereignKillSwitchController.trip()
     │
     ▼
KillSwitchState → TRIPPED → PERSISTENTLY_BLOCKED
     │
     ├─ assert_admission_allowed() → DataContractError for ALL orders
     │   (new orders AND close orders both blocked by admission gate)
     │
     └─ EmergencyFlattenGenerator.generate_flatten_intent()
          → EmergencyFlattenIntent record (forensic only)
     │
     ▼
Automated close: BLOCKED (no close-only exception in current architecture)
     │
     ▼
Operator takes over:
  Option A: Close positions in MT5 terminal manually
    → triggers UNTRACKED_TRADE_DEAL → Adapter BLOCKED
    → restart → fresh RECON to verify flat
  Option B: Coordinate with broker support for position close
     │
     ▼
EmergencyFlattenTracker.verify_flatten_completion()
  → verifies zero-position state via reconciled PortfolioState
     │
     ▼
System stays PERSISTENTLY_BLOCKED until quorum reset
```

### 13.3 Known Architecture Gap — Close-Only Emergency Channel

> [!WARNING]
> Phase 13 relies on **operator manual intervention** for emergency position closure.
> There is no automated close-only emergency dispatch channel in the current frozen architecture.
>
> This is a P1 architectural debt — NOT a Gate A blocker for Phase 13 micro-lot deployment,
> because micro-lot exposure loss is bounded by `max_daily_loss_notional` and `LiveAuthorization` limits.
> However, this gap MUST be resolved before any meaningful capital scaling.
>
> Resolution path: dedicated close-only execution channel that bypasses `assert_admission_allowed()`
> with its own sovereign authorization. Requires explicit architecture review.

---

## 14. Mandatory Human Approval Gate (Gate B) — Machine vs Governance Separation (P0-2 Resolved)

### 14.1 Machine Gate — Cryptographically Enforced

The machine gate is `LiveAuthorization.status == ACTIVE`. This requires:

```python
# Verified from source (schema.py, admission.py):

Step 1: construct_live_authorization(...) → LiveAuthorization(status=DRAFT)
   Params encoded: max_notional, max_position_size, max_daily_loss_notional,
                   max_drawdown_pct, allowed_venues, allowed_symbols,
                   expires_at, risk_policy_version, required_approvals

Step 2: Human signs AuthorizationApproval
   approval_digest = SHA-256(canonical payload including authorization_id)
   approval_signature = Ed25519.sign(approval_digest)

Step 3: transition to ACTIVE
   |verified approvals| >= required_approvals
   authorization_digest recomputed over all params + sorted approval_digests
   status → ACTIVE

Step 4: construct_order_intent() checks status == ACTIVE (admission.py:650)
   ← FAIL-CLOSED: PreLiveRiskAdmissionError if not ACTIVE
```

**The system cannot process any live order without a correctly signed, ACTIVE `LiveAuthorization`.**

### 14.2 Human Governance Gate — Organizational Record Only

The human governance gate is NOT machine-verifiable. It is a separate organizational requirement:

```
Human Governance Events (organizational record):
  [ ] Human reviews Gate A evidence
  [ ] Human confirms live broker account and credentials
  [ ] Human reviews and sets all LiveAuthorization parameters
  [ ] Human issues explicit GO decision (verbal or written)
  [ ] GO decision logged / archived

These events DO NOT directly enable machine execution.
The machine is enabled ONLY by the signed, ACTIVE LiveAuthorization.
The GO decision is a governance record, not a machine command.
```

> [!IMPORTANT]
> **The separation contract:**
> - Machine Gate: `LiveAuthorization.status == ACTIVE` (cryptographic, fail-closed)
> - Governance Gate: Human GO decision (organizational, non-machine-verifiable)
>
> The machine trusts the signed authorization artifact.
> The organization trusts the human GO record.
> Both must occur; they are parallel requirements, not sequential commands.

### 14.3 Gate B Checklist (Revised)

```
GATE B — MANDATORY HUMAN AUTHORIZATION

[MACHINE GATE — must complete before system accepts live orders]
[ ] M-1  LiveAuthorization constructed with Phase 13 parameters
[ ] M-2  Human reviews and confirms all LiveAuthorization fields:
         - max_notional (USD amount)
         - max_position_size (lots)
         - max_daily_loss_notional (USD)
         - max_drawdown_pct (%)
         - allowed_venues (live venue ID only)
         - allowed_symbols (target symbols)
         - expires_at (time-boxed)
         - required_approvals (≥ 1)
[ ] M-3  Each required approver signs AuthorizationApproval (Ed25519)
[ ] M-4  Quorum verified: |valid approvals| >= required_approvals
[ ] M-5  authorization_digest verified (canonical hash matches all params)
[ ] M-6  LiveAuthorization.status transitions to ACTIVE
[ ] M-7  Kill switch Ed25519 quorum keys confirmed loaded

[GOVERNANCE GATE — parallel organizational requirement]
[ ] G-1  Human reviews all Gate A evidence
[ ] G-2  Human confirms live broker account identity
[ ] G-3  Human issues explicit GO decision
[ ] G-4  GO decision archived as governance record

UNTIL M-6 (status = ACTIVE): no live order can be constructed
UNTIL G-3 (GO decision): no live order should be attempted (governance)
```

---

## 15. Criteria for First Live Order

The following **conjunctive** conditions must ALL hold:

$$\boxed{P_{13} = \text{GateA\_PASS} \land \text{GateB.M6\_ACTIVE} \land \text{GateB.G3\_GO} \land \text{KillSwitch\_ARMED} \land \text{RECON\_PASS} \land \text{RiskEngine\_PASS} \land \text{can\_dispatch()}}$$

| Condition | Source Enforcement |
|-----------|-------------------|
| Gate A complete | All A-1 through A-11 PASS |
| `LiveAuthorization.status == ACTIVE` | `admission.py:650` — fail-closed |
| Kill switch ARMED | `assert_admission_allowed()` — fail-closed |
| 6-D RECON pass | `can_dispatch() == True` — `adapter.py:197` |
| `RiskStatus == NORMAL` | `admission.py:696` — fail-closed |
| `CalculationStatus == NOMINAL` | `admission.py:691` — fail-closed |
| Human GO on record | Governance requirement (non-machine) |

$$\text{HTTP-success} \neq P_{13} \quad \text{ACK} \neq P_{13} \quad \text{Unit tests} \neq P_{13} \quad \text{"GO"} \neq P_{13}\ (\text{without ACTIVE})$$

---

## 16. Criteria to Remain at $0.00 (No-Go Conditions)

| Condition | No-Go Trigger | Machine or Governance |
|-----------|---------------|----------------------|
| Gate A any item FAIL | Stay at $0.00 | Governance |
| `LiveAuthorization.status != ACTIVE` | Stay at $0.00 | **Machine (fail-closed)** |
| Kill switch not ARMED | Stay at $0.00 | **Machine (fail-closed)** |
| RECON failing | Stay at $0.00 | **Machine (fail-closed)** |
| `RiskStatus != NORMAL` | Stay at $0.00 | **Machine (fail-closed)** |
| Emergency flatten gap not acknowledged | Stay at $0.00 | Governance (A-7) |
| DEGRADED alert procedure not verified | Stay at $0.00 | Governance (A-11) |
| Human explicitly says NO | Stay at $0.00 | Governance (unconditional) |

> [!CAUTION]
> Machine gates are fail-closed automatically.
> Governance gates require explicit human action.
> Both categories must be satisfied.

---

## 17. TradingView — Explicitly Out of Scope

```
❌ TradingView Ingress Gateway    — separate backlog
❌ TradingView webhook handling   — separate backlog
❌ TradingView signal parsing     — separate backlog
❌ TradingView authentication     — separate backlog

PROHIBITED PATH (forever):
  TradingView → MT5 → Broker   ← STRICTLY FORBIDDEN

PERMITTED PATH (when TradingView eventually implemented):
  TradingView Webhook → IP/Token Validation → Canonical event_id
      → Idempotency Check → TradingViewCandidateSignal (CapitalAuthorityUSD = 0.00)
      → Research → Validation → Tournament → Risk → Admission → Execution
```

---

## 18. Phase 13 Implementation Slices (Proposed — Pending Rev2 Approval)

```
Phase 13
│
├─ Slice 1: Gate A — Pre-Live Certification
│    ├─ Risk limits configured for live LiveAuthorization
│    ├─ Kill switch verified: PERSISTENTLY_BLOCKED test + recovery
│    ├─ MT5 demo full lifecycle evidence (SUBMITTED → ACK → RECON → FILLED)
│    ├─ Emergency flatten gap verified and operator procedure documented
│    ├─ DEGRADED structured WARNING log observable and acknowledged
│    └─ Recovery procedures documented and tested on demo
│
├─ Slice 2: Gate B — Human Authorization
│    ├─ LiveAuthorization constructed with Phase 13 parameters
│    ├─ Human reviews all fields; Ed25519 quorum signed
│    ├─ authorization_digest verified → status ACTIVE
│    ├─ Human issues GO (governance record)
│    └─ GO/NO-GO final decision
│
└─ Slice 3: First Live Order (only after Gate B Machine + Governance gates)
     ├─ Single micro-lot live order
     ├─ Full lifecycle: SUBMITTED → ACK → RECON → FILLED
     ├─ verify RiskEngine, KillSwitch, RECON all held throughout
     ├─ Source code audit
     └─ Human confirmation of first live evidence
```

---

## 19. Architectural Debt Summary (Phase 13 Scope)

| Debt Item | Severity | Scope | Resolution |
|-----------|----------|-------|------------|
| Cumulative `max_notional` not enforced per-order at admission | P1 | Phase 13 mitigated (micro-lot + Risk limits) | Future phase |
| No close-only emergency dispatch channel | P1 | Mitigated by operator procedure | Future phase (explicit arch review required) |
| No real-time alerting UI | P2 | Mitigated by structured log monitoring | Future phase |
| Phase-B transactional P1 debt (from Phase 12) | P1 | Does not affect Phase 13 | Future phase |

---

## Verification Ledger (Plan Rev2)

- **Plan Status:** DRAFT — NOT APPROVED
- **Implementation Status:** NOT STARTED
- **Production Code Changes:** ZERO (planning document only)
- **Frozen Baseline Respected:** `1e1d154` — no Phase 12 contracts reopened
- **TradingView:** OUT OF SCOPE (confirmed)
- **Live Capital:** $0.00 (unchanged — Gate B Machine Gate not reached)
- **Rev1 P0-1 (machine enforcement):** RESOLVED — `LiveAuthorization.max_notional` + `authorization_digest` defined; gap acknowledged
- **Rev1 P0-2 (signed vs GO conflated):** RESOLVED — Machine Gate (M-1 through M-7) vs Governance Gate (G-1 through G-4) explicitly separated
- **Rev1 P1-1 (monitoring alerting):** RESOLVED — structured WARNING log chain defined; SLA acknowledged
- **Rev1 P1-2 (PERSISTENTLY_BLOCKED vs flatten):** RESOLVED — gap verified in source; operator procedure documented; close-only channel declared as future debt
- **Methodological Caveats:**
  - `max_notional` cumulative tracking not implemented — mitigated by micro-lot scale
  - Emergency automated close not possible when PERSISTENTLY_BLOCKED — operator procedure required
  - Phase 13 monitoring requires active operator vigilance (no automated push alerts)
