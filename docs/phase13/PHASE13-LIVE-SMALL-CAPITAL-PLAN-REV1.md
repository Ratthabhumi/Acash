# Phase 13 — Live Small Capital Deployment
# Plan Revision 1: Pre-Live Readiness & Small Capital Architecture

> **Document:** `docs/phase13/PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV1.md`
> **Status:** DRAFT — PENDING USER AUDIT & APPROVAL
> **Plan Revision:** Rev1
> **Date:** 2026-09-03
> **Frozen Execution Baseline:** `1e1d154` (Phase 12 — CLOSED & FROZEN)
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed)
> **TradingView:** OUT OF SCOPE — separate independent backlog item

---

## 0. Scope of This Document

This plan defines:
1. **What Phase 13 is** — and what it is not
2. **What ACASH must prove** before a human authorizes the first live capital
3. **Gate A: Pre-Live Certification** — what must be verified while still at $0.00
4. **Gate B: Human Authorization** — the explicit approval event that changes live capital from $0.00

> [!IMPORTANT]
> This Rev1 plan does NOT implement live trading.
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
│  A-1  Risk limits configured & verified             │
│  A-2  Kill switch operational (PERSISTENTLY_BLOCKED│
│       recovery verified)                           │
│  A-3  MT5 demo account full lifecycle evidence     │
│  A-4  6-D Reconciliation verified on demo          │
│  A-5  Monitoring / ForwardHealthState verified     │
│  A-6  Emergency flatten verified on demo           │
│  A-7  Failure / recovery procedure documented      │
│  A-8  Position sizing & capital limit confirmed    │
│  A-9  Daily loss limit & max exposure confirmed    │
│  A-10 Rollback / emergency stop tested on demo     │
└────────────────────────────────────────────────────┘
         │
         │  All A-* items: PASS
         ▼
┌────────────────────────────────────────────────────┐
│ GATE B — MANDATORY HUMAN AUTHORIZATION             │
│ (Hard Gate — no code can bypass this)              │
│                                                    │
│  B-1  Human reviews Gate A evidence                │
│  B-2  Human confirms live account & broker         │
│  B-3  Human sets explicit capital limit (USD)      │
│  B-4  Human signs AuthorizationApproval record     │
│  B-5  Kill switch Ed25519 quorum verified           │
│  B-6  Human issues explicit GO decision            │
└────────────────────────────────────────────────────┘
         │
         │  B-* items: ALL SIGNED
         ▼
    $0.00 → Small Capital (human-defined limit)
    First live order authorized
```

---

## 4. Capital Limit

### 4.1 Proposal (requires human confirmation at Gate B)

| Parameter | Proposed Constraint | Rationale |
|-----------|---------------------|-----------|
| Initial capital deployment | TBD by human (Gate B) | Cannot be set by agent |
| Maximum single position | Micro-lot (0.01 lot per instrument) | Minimum broker unit |
| Maximum concurrent open positions | 1 (initial; may be relaxed later) | Fail-safe for initial live run |
| Maximum total exposure (USD) | TBD by human (Gate B) | Cannot be set by agent |

> [!CAUTION]
> Capital limits in this plan are **proposals only**.
> The human must confirm exact USD amounts at Gate B.
> No agent may set or modify live capital limits unilaterally.

### 4.2 Capital Lock Invariant (From Phase 12 Frozen Contract)

```
CapitalAuthorityUSD ≡ 0.00
```

This invariant is **frozen from Phase 12** and remains in effect until Gate B explicit authorization. Any code change to this invariant requires both Gate A completion and Gate B human approval.

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
  └── Credentials stored via Windows DPAPI (separate from demo credentials)
  └── Identity Triad:
        Credential Owner ≡ Adapter Runtime ≡ Terminal Process Owner
```

> [!WARNING]
> Live credentials MUST be stored in a separate DPAPI vault entry from demo credentials.
> Cross-contamination (live credentials on demo adapter or vice versa) is a critical security failure.

### 5.3 Paper/Live Hard Separation

| Boundary | Enforcement |
|----------|-------------|
| Demo account | `MT5BrokerAdapter` initialized with demo credentials |
| Live account | `MT5BrokerAdapter` initialized with live credentials (Gate B only) |
| Mixed-account dispatch | **PROHIBITED** — each adapter instance is bound to exactly one account |
| Cross-account state queries | **PROHIBITED** — `(broker_id, account_id)` binding enforced |

---

## 6. Risk Limits

All limits are enforced by the **Phase 9 `DeterministicRiskEngine`** (frozen, `6bd40d8`) — no new risk engine is required.

### 6.1 Existing Risk Parameters (from `RiskPolicyConfig` — `src/acash/risk/risk_schema.py`)

| Parameter | Field | Default | Phase 13 Proposed Override |
|-----------|-------|---------|---------------------------|
| Max gross leverage | `max_gross_leverage` | `1.00` | ≤ `1.00` (no leverage, initial) |
| Max drawdown | `max_drawdown_limit_pct` | `15.00%` | TBD by human — propose `5.00%` initial |
| Max daily loss | `max_daily_loss_usd` | `10,000.00` | TBD by human — scaled to live capital |
| Min cash buffer | `min_cash_buffer` | configurable | TBD by human |

> [!IMPORTANT]
> Phase 13 risk parameters must be explicitly configured by the human at Gate B.
> Default values from `RiskPolicyConfig` are **not** appropriate for live small capital without review.

### 6.2 Risk Engine Authority Chain (Frozen)

```
DeterministicRiskEngine.evaluate()
  │
  ├─ Gross leverage boundary check
  ├─ Asset concentration check
  ├─ Mandatory cash floor check
  ├─ Peak-to-trough drawdown check  → MAX_DRAWDOWN_BREACHED → BINARY_REJECT
  └─ Cumulative daily loss check    → MAX_DAILY_LOSS_BREACHED → BINARY_REJECT
```

**`BINARY_REJECT`** immediately blocks all order admission — this is already implemented and frozen.

---

## 7. Kill Switch

### 7.1 Existing Implementation (`SovereignKillSwitchController` — `src/acash/risk/kill_switch.py`)

Already implemented in Phase 9 (`6bd40d8`). Phase 13 **consumes** this — does not rewrite.

```
Kill Switch Lifecycle:
  ARMED → TRIPPED → PERSISTENTLY_BLOCKED → (multi-sig quorum reset) → ARMED

Append-only disk persistence:
  - SHA-256 tamper-evident event chaining
  - Process restart recovery: TRIPPED / PERSISTENTLY_BLOCKED always recovered
  - Corrupted ledger → fail-closed

Multi-Sig Quorum Reset:
  - Ed25519TrustStore cryptographic signature verification
  - Requires non-empty root cause analysis
  - Distinct approver quorum enforcement
  - Replay protection
```

### 7.2 Gate A Kill Switch Verification

Before Gate B, kill switch must be verified on the live account environment:
- `ARMED` state confirmed on startup
- Trigger a test `TRIPPED` event → verify `PERSISTENTLY_BLOCKED` recovery on restart
- Verify that `PERSISTENTLY_BLOCKED` blocks ALL order dispatch
- Verify quorum reset mechanism functional

---

## 8. Position Sizing

### 8.1 MT5 Volume Contract (Frozen from Phase 12)

```python
# BrokerSymbolSpec fields (src/acash/execution/mt5/schemas.py)
volume_min  : Decimal  # e.g. 0.01 (minimum lot)
volume_step : Decimal  # e.g. 0.01 (step size)
volume_max  : Decimal  # e.g. 100.00 (maximum lot)
```

Phase 13 initial constraint:
$$\text{Phase 13 position size} \equiv \text{volume\_min} \quad (\text{0.01 lot per order, pending Gate B confirmation})$$

### 8.2 Sizing Enforcement

The existing `quantize_volume()` pipeline (Phase 12, frozen) already enforces:
- `VOLUME_BELOW_MINIMUM` → `DataContractError` (fail-closed)
- `VOLUME_ABOVE_MAXIMUM` → `DataContractError` (fail-closed)
- `VOLUME_STEP_MISMATCH` → `DataContractError` (fail-closed)

No new sizing code needed for Phase 13 initial scope.

---

## 9. Daily Loss Limit & Max Exposure

| Limit | Enforcement | Configuration |
|-------|-------------|---------------|
| Daily loss | `DeterministicRiskEngine` `max_daily_loss_usd` field | Must be set at Gate B — scaled to actual capital |
| Max exposure | `DeterministicRiskEngine` `max_gross_leverage` + `min_cash_buffer` | ≤ 1.00 (no leverage) |
| Drawdown | `DeterministicRiskEngine` `max_drawdown_limit_pct` | Human defines threshold at Gate B |

> Reaching any limit → `BINARY_REJECT` → no orders accepted → `EmergencyFlattenGenerator` if positions open

---

## 10. Reconciliation Requirement

### 10.1 6-D Reconciliation (Frozen Phase 12 Contract)

All 6 dimensions MUST pass before any dispatch is enabled:

```
Dimension 1: Balance
Dimension 2: Equity
Dimension 3: Margin
Dimension 4: Positions
Dimension 5: Resting Orders
Dimension 6: Historical Deals
```

**`can_dispatch() == True`** iff:
- `safety_state == READY`
- `is_reconciled == True`

Both conditions must hold simultaneously — this is enforced by the frozen Phase 12 contract.

### 10.2 Phase 13 Reconciliation Cadence

Gate A must verify:
- Reconciliation cycle runs correctly against live account on startup
- `UNKNOWN` state (connection loss) → reconciliation required before dispatch resumes
- `BLOCKED` state (CRITICAL discrepancy) → operator intervention required

---

## 11. Monitoring & Alerting

### 11.1 Existing Implementation (Phase 11 `ForwardHealthState`)

Phase 11 (`092a2b1`) already implements:
```
ForwardHealthState:
  HEALTHY → no action
  DEGRADED → DEGRADED_PROBATION recommendation (anti-whipsaw hysteresis)
  MONITORING_BLOCKED → telemetry failure → flag for operator

MonitoringEvidenceLedger:
  Append-only SHA-256 chained ledger
  Epoch recovery via reinitialize_stream() (no gap backfill)
```

### 11.2 Phase 13 Monitoring Requirements

Gate A must verify:
- `ForwardHealthState` transitions correctly on live account data
- `MONITORING_BLOCKED` does NOT falsely signal strategy decay (telemetry disruption ≠ negative evidence)
- `MonitoringEvidenceLedger` persists correctly across process restarts
- Human is alerted on `DEGRADED` recommendation (alerting mechanism TBD — out of scope for Rev1)

> [!NOTE]
> Phase 13 Rev1 does not define a real-time alerting UI.
> Operator must actively monitor logs and `MonitoringEvidenceLedger` until alerting is implemented.

---

## 12. Recovery Procedure

### 12.1 Connection Loss Recovery

```
Connection loss detected
    │
    ▼
In-flight orders → UNKNOWN
    │
    ▼
can_dispatch() == False (all dispatch blocked)
    │
    ▼
Wait for MT5 terminal reconnection
    │
    ▼
Run 6-D Reconciliation cycle
    │
    ├─ PASS → safety_state → READY → can_dispatch() → True → resume
    └─ FAIL → BLOCKED → operator intervention required
```

### 12.2 CRITICAL Discrepancy Recovery

```
UNTRACKED_TRADE_DEAL detected (external broker activity)
    │
    ▼
MT5ReconciliationError raised
    │
    ▼
Adapter → BLOCKED (absorbing)
    │
    ▼
ALL dispatch permanently blocked
    │
    ▼
Operator investigates discrepancy
    │
    ▼
Root cause identified and documented
    │
    ▼
Kill switch reset (Ed25519 quorum if tripped)
    │
    ▼
Manual position reconciliation if needed
    │
    ▼
Restart with fresh 6-D Reconciliation cycle
```

### 12.3 Process Crash Recovery

```
ACASH process crash during live operation
    │
    ▼
SovereignKillSwitchController reads persisted ledger
    │
    ├─ State was ARMED → restart in ARMED
    ├─ State was TRIPPED → restart in PERSISTENTLY_BLOCKED (fail-closed)
    └─ Ledger corrupted → startup halt (fail-closed)
         │
         ▼
6-D Reconciliation required before any dispatch
```

---

## 13. Rollback / Emergency Stop

### 13.1 Emergency Flatten (Phase 9 — Frozen)

`EmergencyFlattenGenerator` already implemented:
- Emits zero-target liquidation intents ($q_{\text{target}} \equiv 0.0$, $\Delta q_i = -q_i$ for all positions)
- `EmergencyFlattenTracker` evaluates completion strictly against Phase 7/12 broker reconciliation
- Completion criterion: all positions confirmed closed via 6-D RECON

### 13.2 Emergency Stop Sequence

```
Emergency detected (human or automated trigger)
    │
    ▼
SovereignKillSwitchController.trip()
    │
    ▼
KillSwitchState → TRIPPED → PERSISTENTLY_BLOCKED
    │
    ▼
EmergencyFlattenGenerator.generate_intents()
    │
    ▼
ExecutionCoordinator dispatches close orders via MT5BrokerAdapter
    │
    ▼
EmergencyFlattenTracker monitors closure via RECON evidence
    │
    ▼
All positions closed → flatten_status == COMPLETE
    │
    ▼
System stays PERSISTENTLY_BLOCKED until quorum reset
```

### 13.3 Human Emergency Stop

- Human can trip kill switch directly via `SovereignKillSwitchController.trip()`
- Human can manually submit close orders in MT5 terminal (external broker activity → BLOCKED → operator handles)
- MT5 terminal "Close All Positions" button remains available as last-resort hardware override

---

## 14. Mandatory Human Approval Gate (Gate B)

### 14.1 Authorization Structure (Phase 7 Schema — Frozen)

Phase 7 already defines `AuthorizationApproval` with `ApproverRole`. Gate B uses this schema:

```python
AuthorizationApproval:
  approver_id    : str          # Human identity
  approver_role  : ApproverRole # Role in approval hierarchy
  approval_digest: str          # SHA-256 of approved scope
  timestamp_utc  : datetime     # Strict UTC
  signature      : str          # Ed25519 signature
```

### 14.2 Gate B Checklist

The following MUST be completed by the human before ANY live capital is deployed:

```
GATE B — MANDATORY HUMAN AUTHORIZATION CHECKLIST

[ ] B-1  Reviewed all Gate A evidence and confirmed PASS
[ ] B-2  Confirmed live broker account identity and credentials
[ ] B-3  Confirmed live MT5 terminal path and version
[ ] B-4  Set explicit capital limit (USD amount — mandatory)
[ ] B-5  Set explicit max daily loss limit (USD — mandatory)
[ ] B-6  Set explicit max drawdown threshold (% — mandatory)
[ ] B-7  Set explicit max position size (lots — mandatory)
[ ] B-8  Confirmed kill switch Ed25519 quorum keys loaded
[ ] B-9  Confirmed monitoring ledger operational
[ ] B-10 Signed AuthorizationApproval record
[ ] B-11 Issued explicit GO decision (verbal or written)

UNTIL ALL B-* ITEMS ARE CHECKED: CapitalAuthorityUSD ≡ 0.00
```

---

## 15. Criteria for First Live Order

The following **conjunctive** conditions must ALL hold before the first live order is dispatched:

$$\boxed{P_{13} = \text{GateA\_PASS} \land \text{GateB\_SIGNED} \land \text{KillSwitch\_ARMED} \land \text{RECON\_PASS} \land \text{RiskEngine\_PASS} \land \text{Admission\_ACTIVE}}$$

| Condition | Verification |
|-----------|-------------|
| Gate A complete | All A-1 through A-10 items PASS |
| Gate B signed | All B-1 through B-11 items checked by human |
| Kill switch ARMED | `KillSwitchState.ARMED` confirmed on startup |
| RECON pass | 6-D Reconciliation cycle PASS on live account |
| Risk engine pass | `DeterministicRiskEngine.evaluate()` returns PASS for proposed allocation |
| Admission active | `AuthorizationStatus.ACTIVE` on live `ExecutionAuthorization` |
| `can_dispatch()` | Returns `True` (READY + is_reconciled) |

$$\text{HTTP-success} \neq P_{13} \quad \text{ACK} \neq P_{13} \quad \text{Unit tests} \neq P_{13}$$

---

## 16. Criteria to Remain at $0.00 (No-Go Conditions)

Phase 13 does NOT proceed to live capital if ANY of the following are true:

| Condition | No-Go Trigger |
|-----------|---------------|
| Gate A any item FAIL | Stay at $0.00, fix and re-verify |
| Gate B not complete | Stay at $0.00 (unconditional) |
| Kill switch not ARMED | Stay at $0.00 |
| RECON failing on demo account | Stay at $0.00, investigate |
| EmergencyFlatten not verified | Stay at $0.00 |
| `can_dispatch()` returning False | Stay at $0.00 |
| Human explicitly says NO | Stay at $0.00 (unconditional) |
| Any P1 architectural debt unresolved that creates live risk | Evaluate — may stay at $0.00 |

> [!CAUTION]
> There is no automated mechanism that transitions CapitalAuthorityUSD from $0.00.
> This is a human-only gate. If a human does not explicitly authorize, capital stays at $0.00 forever.

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
  TradingView Webhook
      ↓
  IP/Token Validation
      ↓
  Canonical event_id
      ↓
  Idempotency Check
      ↓
  TradingViewCandidateSignal (CapitalAuthorityUSD = 0.00)
      ↓
  Research → Validation → Tournament → Risk → Admission → Execution
```

---

## 18. Phase 13 Implementation Slices (Proposed — Pending Approval)

```
Phase 13
│
├─ Slice 1: Gate A — Pre-Live Certification
│    ├─ Risk limits configured for live account
│    ├─ Kill switch verified on live environment
│    ├─ MT5 demo full lifecycle evidence
│    ├─ Emergency flatten verified
│    └─ Recovery procedures documented
│
├─ Slice 2: Gate B — Human Authorization
│    ├─ Evidence package compiled for human review
│    ├─ Capital / risk limits confirmed by human
│    ├─ AuthorizationApproval signed
│    └─ GO/NO-GO decision
│
└─ Slice 3: First Live Order (only after Gate B)
     ├─ Single micro-lot live order
     ├─ Full lifecycle: SUBMITTED → ACK → RECON → FILLED
     ├─ Source code audit
     └─ Human confirmation of first live evidence
```

---

## 19. Verification Workflow for This Plan

Per `AGENTS.md` workflow:

```
1. Antigravity drafts Plan Rev1 (this document)
2. User audits against frozen baseline (1e1d154) and ROADMAP.md
3. ❌ Defects → Rev2 / Rev3 / ...
   ✅ Approved → Antigravity implements Slice 1
4. Tests → Full regression
5. Source Code Audit (user)
6. Gate A evidence compiled
7. Human Approval (Gate B)
8. $0.00 → Small Capital
9. First live order evidence
```

---

## Verification Ledger (Plan Rev1)

- **Plan Status:** DRAFT — NOT APPROVED
- **Implementation Status:** NOT STARTED
- **Production Code Changes:** ZERO (this is a planning document only)
- **Frozen Baseline Respected:** `1e1d154` — no Phase 12 contracts reopened
- **TradingView:** OUT OF SCOPE (confirmed)
- **Live Capital:** $0.00 (unchanged — Gate B not reached)
- **Mathematical Authority:** N/A (planning document)
- **Methodological Caveats:**
  - Capital limits in Section 4 and 6 are proposals — human must confirm at Gate B
  - Alerting mechanism (Section 11) is out of scope for Rev1 — operator must actively monitor
  - Phase-B transactional P1 debt (from Phase 12 closeout) remains acknowledged but does not block Phase 13 Gate A
