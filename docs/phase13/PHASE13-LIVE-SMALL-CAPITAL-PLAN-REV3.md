# Phase 13 — Live Small Capital Deployment
# Plan Revision 3: Pre-Live Readiness & Small Capital Architecture

> **Document:** `docs/phase13/PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV3.md`
> **Status:** DRAFT — PENDING USER AUDIT & APPROVAL
> **Plan Revision:** Rev3 (addresses Rev2 audit findings: P0 max_notional semantics, P1 SLA, P1 emergency close)
> **Date:** 2026-09-03
> **Frozen Execution Baseline:** `1e1d154` (Phase 12 — CLOSED & FROZEN)
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed)
> **TradingView:** OUT OF SCOPE — separate independent backlog item

---

## Rev3 Changelog (vs Rev2 Audit Findings — 8.3/10 NOT APPROVED)

| Finding | Rev2 Status | Rev3 Resolution |
|---------|-------------|-----------------|
| P0: `max_notional` overclaimed as "machine-enforceable capital ceiling" | ❌ | Corrected to "cryptographically authorized exposure ceiling"; cumulative runtime enforcement explicitly NOT IMPLEMENTED |
| P0: "max 1 concurrent position" claimed without source evidence | ❌ | Removed — no enforcement found in source; replaced with verified enforcement only |
| P0: "unlikely at micro-lot scale" accepted as safety argument | ❌ | Removed; Phase 13 capital safety guarantee stated with only what source actually enforces |
| P1: DEGRADED SLA "actively monitors logs" not measurable | ⚠️ | Concrete numeric SLA defined (≤ 15 min acknowledgement; ≤ 5 min trip on no-ack) |
| P1: Emergency close gap severity understated | ⚠️ | Hard Gate A end-to-end demo test criterion added as explicit A-11 requirement |
| P1: `max_notional` currency/unit undefined | ⚠️ | Currency denomination contract stated; MT5AccountReality.currency as authority |

> [!IMPORTANT]
> Rev3 does NOT add new subsystems, rewrite existing contracts, or add code.
> All resolutions are corrections to Rev2 terminology and addition of concrete operational controls.

---

## Verification Ledger Status

| Finding | Rev1 | Rev2 | Rev3 |
|---------|------|------|------|
| P0-2: Machine Gate vs Governance Gate | ❌ | ✅ RESOLVED | ✅ Preserved |
| P0-1: max_notional digest integrity (cryptographic seal) | ❌ | ✅ RESOLVED | ✅ Preserved |
| P0-new: cumulative max_notional NOT IMPLEMENTED | N/A | ❌ Overclaimed | ✅ Explicitly declared |
| P1-1: Monitoring SLA | ⚠️ | ⚠️ Partial | ✅ RESOLVED |
| P1-2: Emergency close semantics documented | ⚠️ | ✅ RESOLVED | ✅ Preserved |
| P1-2b: Emergency close Gate A end-to-end test | not stated | not required | ✅ ADDED (A-11) |
| max_notional currency unit | not stated | not stated | ✅ RESOLVED |

---

## 0. Scope of This Document

This plan defines:
1. **What Phase 13 is** — and what it is not
2. **What ACASH must prove** before a human authorizes the first live capital
3. **Gate A: Pre-Live Certification** — what must be verified while still at $0.00
4. **Gate B: Human Authorization** — the explicit approval event that changes live capital from $0.00

> [!IMPORTANT]
> This Rev3 plan does NOT implement live trading.
> Live capital remains at $0.00 until Gate B is explicitly signed off.
> No production code change is authorized from this document alone.

---

## 1. Phase 13 Objective

Deploy ACASH in a **real live broker account with a strictly bounded micro-capital allocation**, subject to all Phase 9 risk boundaries, Phase 12 execution lifecycle contracts, and Mandatory Human Approval.

**Phase 13 success criterion:**
$$\boxed{\text{First real live order lifecycle} \to \text{FILLED/RECONCILED} \land \text{All machine-enforced risk gates held} \land \text{Kill switch operational}}$$

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
| Cumulative notional runtime enforcer | ❌ OUT OF SCOPE (declared P1 debt — future phase) |
| Automated live trading without human approval | ❌ PERMANENTLY PROHIBITED |

---

## 3. Two-Gate Structure

```
Phase 12 FROZEN (1e1d154)
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ GATE A — PRE-LIVE CERTIFICATION (still at $0.00)     │
│                                                      │
│  A-1  RiskPolicyConfig configured with live limits   │
│  A-2  Kill switch PERSISTENTLY_BLOCKED recovery      │
│       verified on demo                               │
│  A-3  MT5 demo full lifecycle evidence               │
│       (SUBMITTED → ACK → RECON → FILLED)             │
│  A-4  6-D Reconciliation verified on demo            │
│  A-5  ForwardHealthStateMachine verified on demo     │
│  A-6  EmergencyFlattenIntent record verified on demo │
│  A-7  Recovery procedures documented and tested      │
│  A-8  LiveAuthorization parameters confirmed         │
│  A-9  Rollback: PERSISTENTLY_BLOCKED tested on demo  │
│  A-10 DEGRADED WARNING log observable; SLA rehearsed │
│  A-11 Emergency-close operator procedure demonstrated│
│       end-to-end on demo (position open → KS trip →  │
│       BLOCKED → manual MT5 close → UNTRACKED deal →  │
│       restart → RECON → flat confirmed)              │
└──────────────────────────────────────────────────────┘
         │  All A-* items: PASS
         ▼
┌──────────────────────────────────────────────────────┐
│ GATE B — MANDATORY HUMAN AUTHORIZATION               │
│                                                      │
│ [Machine Gate — cryptographically enforced]          │
│  M-1  LiveAuthorization constructed with Phase 13    │
│       parameters (all fields human-confirmed)        │
│  M-2  Each required approver signs Ed25519           │
│       AuthorizationApproval                          │
│  M-3  |verified approvals| >= required_approvals     │
│  M-4  authorization_digest verified                  │
│  M-5  LiveAuthorization.status → ACTIVE              │
│  M-6  Kill switch Ed25519 quorum keys confirmed      │
│                                                      │
│ [Governance Gate — organizational record]            │
│  G-1  Human reviews all Gate A evidence              │
│  G-2  Human confirms live broker account             │
│  G-3  Human issues explicit GO decision              │
│  G-4  GO archived as governance record               │
└──────────────────────────────────────────────────────┘
         │  Machine Gate (M-5): ACTIVE
         │  Governance Gate (G-3): GO on record
         ▼
    $0.00 → Small Capital (human-confirmed parameters)
    First live order authorized
```

---

## 4. Capital Limit — Correct Semantics (Rev3 Corrected)

### 4.1 Two Distinct Properties of `max_notional`

`LiveAuthorization.max_notional` (`src/acash/execution/schema.py:278`) has **two distinct properties that must not be conflated**:

| Property | What it is | What it is NOT |
|----------|-----------|----------------|
| **Cryptographic authorization seal** | `max_notional` is bound in `authorization_digest` — changing the value invalidates the digest and requires new Ed25519 quorum | A real-time runtime exposure counter |
| **Declared authorized ceiling** | The human's signed statement of the maximum notional they authorize | A machine-enforced limit checked per-order at dispatch time |

**Correct terminology (Rev3):**
```
max_notional = cryptographically authorized exposure ceiling

NOT:
max_notional = machine-enforced capital ceiling
```

### 4.2 Cumulative Exposure Enforcement — NOT IMPLEMENTED

> [!WARNING]
> **Verified from source (admission.py, schema.py):**
>
> `construct_order_intent()` enforces:
>   - `quantity <= max_position_size`  ← per-order check (machine-enforced)
>
> `construct_order_intent()` does NOT enforce:
>   - `current_total_exposure + new_order_notional <= max_notional`  ← NOT IMPLEMENTED
>
> **Cumulative notional tracking against `max_notional` is NOT implemented in the current admission gate.**
> This is P1 architectural debt. No runtime counter or portfolio exposure check against `max_notional` exists.

### 4.3 What Machine Enforcement Actually Exists (Verified Source)

The following are **machine-enforced** at `construct_order_intent()` (`admission.py:650–700`):

```
✅ status == ACTIVE              (admission.py:650)
✅ restriction gate cleared      (admission.py:656)
✅ not expired                   (admission.py:668)
✅ venue in allowed_venues       (admission.py:674)
✅ symbol in allowed_symbols     (admission.py:679)
✅ quantity <= max_position_size (admission.py:685)
✅ calculation_status == NOMINAL (admission.py:691)
✅ risk_status == NORMAL         (admission.py:696)
```

The following are **NOT machine-enforced** at admission:
```
❌ current_exposure + order_notional <= max_notional (no cumulative tracker)
❌ concurrent position count <= N                    (no max_concurrent field exists)
❌ daily notional flow <= max_daily_loss_notional    (no runtime counter at admission)
```

**Note on "max 1 concurrent position":** No such enforcement exists in source. This was a Rev2 documentation error. It is removed.

### 4.4 Phase 13 Actual Capital Safety Guarantee

Given the above, Phase 13 capital safety relies on the following **layered defence** — each layer is stated with its actual enforcement status:

| Layer | Mechanism | Machine-Enforced | Source |
|-------|-----------|-----------------|--------|
| 1 | `LiveAuthorization.status == ACTIVE` | ✅ Yes — fail-closed | `admission.py:650` |
| 2 | `quantity <= max_position_size` | ✅ Yes — per-order | `admission.py:685` |
| 3 | `venue` in `allowed_venues` | ✅ Yes — fail-closed | `admission.py:674` |
| 4 | `RiskStatus == NORMAL` (drawdown/daily-loss breach) | ✅ Yes — BINARY_REJECT | `risk_engine.py` |
| 5 | `can_dispatch()` READY + is_reconciled | ✅ Yes — broker gate | `adapter.py:197` |
| 6 | `max_notional` authorized ceiling | ✅ Cryptographically sealed | `schema.py:349` |
| 7 | `max_notional` cumulative enforcement | ❌ NOT IMPLEMENTED | P1 debt |
| 8 | Concurrent position count limit | ❌ NOT IMPLEMENTED | P1 debt |

> [!CAUTION]
> Phase 13 depends on Layers 1–6 for capital safety.
> Layers 7–8 are not implemented. This is an accepted P1 debt at micro-lot scale.
> No language claiming "capital boundary enforced" is used in this plan.
> The correct statement is: **Phase 13 has layered machine-enforced admission gates, with acknowledged gaps in cumulative exposure tracking.**

### 4.5 `max_notional` Currency / Unit Contract

> [!IMPORTANT]
> `LiveAuthorization.max_notional` is a unitless `Decimal` — the schema has no currency field.
> The denomination is NOT enforced by the schema; it is an **operational convention** that must be explicitly stated at Gate B.
>
> Currency authority: `MT5AccountReality.currency` (`schemas.py:330`) — the account deposit currency string (e.g. `'USD'`).
>
> **Gate B requirement:** Human must explicitly confirm that `max_notional` and all `Decimal` monetary fields in `LiveAuthorization` are denominated in the same currency as `MT5AccountReality.currency` for the target live account.
>
> Until this is confirmed, the denomination is operationally undefined.

### 4.6 Capital Parameters (Gate B — human confirmation required)

| Field | Type | Phase 13 Constraint | Enforcement |
|-------|------|---------------------|-------------|
| `max_notional` | Decimal (account currency) | TBD by human | Cryptographic seal; cumulative NOT enforced |
| `max_position_size` | Decimal (lots) | `volume_min` (0.01 lot) | Machine-enforced per-order |
| `max_daily_loss_notional` | Decimal (account currency) | TBD by human | Cryptographic seal; runtime NOT enforced |
| `max_drawdown_pct` | Decimal (%) | TBD — propose ≤ 5% | Cryptographic seal; `DeterministicRiskEngine` enforces independently |
| `allowed_venues` | Tuple[str] | Live MT5 venue ID only | Machine-enforced per-order |
| `allowed_symbols` | Tuple[str] | Target symbols only | Machine-enforced per-order |
| `expires_at` | datetime | Time-boxed; human sets | Machine-enforced per-order |

---

## 5. Broker / Account Boundary

### 5.1 Broker Adapter
- **Adapter:** `MT5BrokerAdapter` (Phase 12 — FROZEN, `1e1d154`)
- **Transport:** `NativeMT5Transport` (IPC to local MT5 terminal)
- **No new broker adapters** in Phase 13 initial scope

### 5.2 Account Separation

```
ACASH Live Account (Phase 13):
  - Distinct from any paper/demo account
  - Windows DPAPI: separate vault entry from demo credentials
  - Identity Triad: Credential Owner ≡ Adapter Runtime ≡ Terminal Process Owner
  - allowed_venues: live venue ID only (machine-enforced at admission)
  - Demo venue ID must NOT appear in live LiveAuthorization.allowed_venues
```

> [!WARNING]
> Live credentials MUST use a separate DPAPI vault entry from demo.
> Cross-contamination is prevented by `allowed_venues` venue check at `construct_order_intent()`.

### 5.3 Paper/Live Hard Separation

| Boundary | Machine Enforcement |
|----------|---------------------|
| Demo adapter | `allowed_venues` = demo venue; venue mismatch → `PreLiveRiskAdmissionError` |
| Live adapter | `allowed_venues` = live venue; demo venue rejected at admission |
| Mixed-account dispatch | Impossible via venue check — `admission.py:674` |

---

## 6. Risk Limits

All limits enforced by **Phase 9 `DeterministicRiskEngine`** (frozen, `6bd40d8`) — no rewrite.

### 6.1 Risk Parameters and Their Enforcement (Verified Source)

| Parameter | Field | Enforcement | Result |
|-----------|-------|-------------|--------|
| Max gross leverage | `max_gross_leverage` | `DeterministicRiskEngine.evaluate()` | `BINARY_REJECT` → `risk_status != NORMAL` → admission fail-closed |
| Max drawdown | `max_drawdown_limit_pct` | `DeterministicRiskEngine` | `MAX_DRAWDOWN_BREACHED` → `BINARY_REJECT` |
| Max daily loss | `max_daily_loss_usd` (USD explicit per `risk_schema.py:156`) | `DeterministicRiskEngine` | `MAX_DAILY_LOSS_BREACHED` → `BINARY_REJECT` |

> Note: `max_daily_loss_usd` in `RiskPolicyConfig` explicitly says "USD" in its description (`risk_schema.py:156`). This must match the account currency.

---

## 7. Kill Switch — Verified Semantics

### 7.1 Implementation (Phase 9 — frozen `6bd40d8`)

```python
# kill_switch.py:158
def assert_admission_allowed(self) -> None:
    """Sovereign admission gate. Raises DataContractError fail-closed if blocked."""
    if self.is_blocked:
        raise DataContractError(
            f"EXECUTION_ADMISSION_BLOCKED: Sovereign kill switch is active in state '{self._state.value}'."
        )

# is_blocked == True when:
#   KillSwitchState in {TRIPPED, PERSISTENTLY_BLOCKED}
```

### 7.2 PERSISTENTLY_BLOCKED — Verified Behavior

- Blocks ALL order dispatch (new AND close orders)
- Survives process restart (disk-persisted, SHA-256 event chaining)
- Corrupted ledger → fail-closed to PERSISTENTLY_BLOCKED
- Reset requires Ed25519 quorum + non-empty root cause

### 7.3 Gate A Verification Requirements

- `ARMED` state confirmed on startup
- Trigger test `TRIPPED` event → verify `PERSISTENTLY_BLOCKED` on restart
- Verify `assert_admission_allowed()` raises for all order attempts
- Verify quorum reset mechanism functional
- **A-11: End-to-end emergency-close operator procedure demonstrated (see Section 13.3)**

---

## 8. Position Sizing

### 8.1 MT5 Volume Contract (Frozen Phase 12)

```python
# BrokerSymbolSpec (schemas.py)
volume_min  : Decimal  # e.g. 0.01 lot
volume_step : Decimal
volume_max  : Decimal
```

Phase 13 constraint:
$$\texttt{max\_position\_size} \equiv \texttt{volume\_min} \quad (0.01\ \text{lot per order})$$

This is encoded in the signed `LiveAuthorization` → bound in `authorization_digest`. Machine-enforced per-order at `admission.py:685`.

**What is NOT enforced:** concurrent position count. No `max_concurrent_positions` field exists in source. This is not claimed as an enforcement mechanism.

---

## 9. Daily Loss Limit & Max Exposure

| Limit | Field | Enforcement | Currency |
|-------|-------|-------------|----------|
| Daily loss | `RiskPolicyConfig.max_daily_loss_usd` | `DeterministicRiskEngine` → BINARY_REJECT | Explicitly USD (`risk_schema.py:156`) |
| Daily loss (auth) | `LiveAuthorization.max_daily_loss_notional` | Cryptographic seal; runtime NOT enforced | Account currency (human confirms at Gate B) |
| Authorized ceiling | `LiveAuthorization.max_notional` | Cryptographic seal; cumulative NOT enforced | Account currency (human confirms at Gate B) |
| Per-order max size | `LiveAuthorization.max_position_size` | Machine-enforced per-order (`admission.py:685`) | Lots (instrument-native) |
| Leverage ceiling | `RiskPolicyConfig.max_gross_leverage` | `DeterministicRiskEngine` → BINARY_REJECT | Ratio (unitless) |

---

## 10. Reconciliation Requirement

```
can_dispatch() == True iff:
  safety_state == READY    (adapter.py:197)
  AND is_reconciled == True (adapter.py:200)
```

6-D Reconciliation dimensions must all pass before dispatch. This is machine-enforced by the frozen Phase 12 contract (`1e1d154`).

---

## 11. Monitoring & Alerting — Concrete SLA (P1-1 Resolved)

### 11.1 Existing Implementation (Phase 11 — frozen `092a2b1`)

```
ForwardHealthState: HEALTHY / INSUFFICIENT_EVIDENCE / DEGRADED / MONITORING_BLOCKED
ForwardGovernanceRecommendation: DEGRADED_PROBATION / MONITORING_BLOCKED_FLAG
MonitoringEvidenceLedger: append-only SHA-256 chained
```

### 11.2 Phase 13 DEGRADED Alert Mechanism and SLA

**DEGRADED trigger:**
```
ForwardHealthStateMachine.advance()
  → ForwardHealthState.DEGRADED
  → ForwardGovernanceRecommendation.DEGRADED_PROBATION
```

**Required structured WARNING log (machine-observable):**
```json
{
  "level": "WARNING",
  "event": "STRATEGY_DEGRADED",
  "state": "DEGRADED",
  "recommendation": "DEGRADED_PROBATION",
  "timestamp_utc": "<ISO-8601>",
  "strategy_id": "<id>",
  "periods_degraded": <int>,
  "trigger_metrics": { ... }
}
```

**Phase 13 SLA (concrete, measurable):**

| Event | Required Action | Time Limit |
|-------|-----------------|------------|
| WARNING emitted | Operator acknowledges (logs reviewed) | ≤ 15 minutes |
| No acknowledgement within 15 min | Operator manually trips kill switch | ≤ 5 minutes after SLA breach |
| Kill switch tripped | PERSISTENTLY_BLOCKED → no further orders | Immediate |
| MONITORING_BLOCKED emitted | Operator investigates telemetry pipeline | ≤ 15 minutes |

> [!IMPORTANT]
> These SLAs apply during defined **live trading hours** only.
> Before live trading hours begin, system must be in HEALTHY state.
> Operator must be reachable within the SLA window before any live order is permitted.

**Gate A verification (A-10):**
- Rehearse DEGRADED → WARNING log emission on demo
- Operator demonstrates reading and acknowledging the structured WARNING within SLA
- Rehearse manual kill switch trip triggered by missed acknowledgement

### 11.3 MONITORING_BLOCKED Semantics

```
MONITORING_BLOCKED ≠ DEGRADED
MONITORING_BLOCKED = telemetry pipeline disruption ONLY
  → logs structured ERROR (not WARNING)
  → NOT treated as strategy decay evidence
  → operator investigates telemetry
  → does NOT alone trigger kill switch
```

---

## 12. Recovery Procedure

### 12.1 Connection Loss Recovery

```
Connection loss → In-flight orders → UNKNOWN
can_dispatch() == False
Wait for MT5 reconnection
Run 6-D Reconciliation cycle
  ├─ PASS → READY → can_dispatch() → True → resume
  └─ FAIL → BLOCKED → operator intervention
```

### 12.2 CRITICAL Discrepancy Recovery

```
UNTRACKED_TRADE_DEAL detected
→ MT5ReconciliationError
→ Adapter BLOCKED (absorbing)
→ ALL dispatch blocked
→ Operator investigates; root cause documented
→ Kill switch reset if PERSISTENTLY_BLOCKED (Ed25519 quorum)
→ Restart + fresh 6-D Reconciliation cycle
```

### 12.3 Process Crash Recovery

```
Crash → KillSwitchController reads persisted ledger
  ├─ ARMED → restart ARMED
  ├─ TRIPPED → restart PERSISTENTLY_BLOCKED (fail-closed)
  └─ Corrupted → startup halt (fail-closed)
6-D RECON required before any dispatch
```

---

## 13. Rollback / Emergency Stop — Corrected Semantics

### 13.1 EmergencyFlattenIntent — Correct Role

`EmergencyFlattenGenerator.generate_flatten_intent()` → `EmergencyFlattenIntent` is a **forensic record and intent artifact only**. It does not dispatch orders.

### 13.2 Emergency Stop Automated Sequence

```
Emergency trigger (automated risk breach or human)
     │
     ▼
SovereignKillSwitchController.trip()
     │
     ▼
KillSwitchState → TRIPPED → PERSISTENTLY_BLOCKED
     │
     ├─ assert_admission_allowed() → DataContractError for ALL orders
     │   (new orders AND close orders — no close-only exception)
     │
     └─ EmergencyFlattenGenerator.generate_flatten_intent()
          → EmergencyFlattenIntent (forensic record only, no dispatch)
```

**Result:** Automated position closure is BLOCKED. Operator intervention is required.

### 13.3 Operator Emergency Close Procedure (Gate A-11 — End-to-End Demo Verification Required)

The following procedure MUST be demonstrated end-to-end on demo before Gate B:

```
Step 1: Position open on demo account
         │
Step 2: Kill switch trips → PERSISTENTLY_BLOCKED
         │
Step 3: Verify ALL automated dispatch blocked
         (assert_admission_allowed() raises)
         │
Step 4: Operator closes position in MT5 terminal (manual)
         │
Step 5: UNTRACKED_TRADE_DEAL discrepancy detected
         → Adapter → BLOCKED (absorbing)
         │
Step 6: All dispatch now doubly blocked:
         kill switch PERSISTENTLY_BLOCKED + adapter BLOCKED
         │
Step 7: Operator documents root cause
         │
Step 8: Process restart
         │
Step 9: 6-D Reconciliation cycle on restarted adapter
         → verify position is flat (zero quantity)
         │
Step 10: EmergencyFlattenTracker.verify_flatten_completion()
          → confirm zero-position state
         │
Step 11: Kill switch quorum reset (if appropriate)
         + new fresh reconciliation
```

> [!CAUTION]
> Gate A item A-11 requires this procedure to be demonstrated completely on demo.
> No live authorization (Gate B M-5) should proceed until A-11 is verified.
>
> **Maximum operator response SLA for live emergency:**
> Position detected open + kill switch PERSISTENTLY_BLOCKED → operator begins manual close procedure ≤ 15 minutes.

---

## 14. Mandatory Human Approval Gate (Gate B) — Machine vs Governance

### 14.1 Machine Gate (Cryptographically Enforced)

```
LiveAuthorization construction → DRAFT
     │
Human signs AuthorizationApproval (Ed25519)
     │ verify: Ed25519TrustStore
     │ verify: |valid approvals| >= required_approvals
     │
authorization_digest computed (SHA-256 over ALL params + approval_digests)
     │
status → ACTIVE
     │
construct_order_intent() [admission.py:650]:
  if status != ACTIVE → PreLiveRiskAdmissionError (fail-closed)
```

**The system cannot process any live order without a correctly signed, ACTIVE `LiveAuthorization`.**

### 14.2 Human Governance Gate (Organizational Record)

```
Governance Gate events (NOT machine-verifiable):
  G-1: Human reviews Gate A evidence
  G-2: Human confirms live broker account
  G-3: Human issues explicit GO decision
  G-4: GO archived as governance record

These events do NOT directly enable machine execution.
Machine execution is enabled ONLY by signed ACTIVE LiveAuthorization.
```

**Contract:** Machine trusts the signed authorization artifact. Organization trusts the governance record. Both must occur; neither replaces the other.

### 14.3 Gate B Checklist (Final)

```
GATE B — MANDATORY HUMAN AUTHORIZATION

[MACHINE GATE]
[ ] M-1  LiveAuthorization constructed with Phase 13 parameters
[ ] M-2  Human reviews and explicitly confirms all fields:
         - max_notional (account currency amount — see §4.5)
         - max_position_size = volume_min (0.01 lot)
         - max_daily_loss_notional (account currency amount)
         - max_drawdown_pct (%)
         - allowed_venues (live venue ID only)
         - allowed_symbols (target symbols)
         - expires_at (time-boxed)
         - required_approvals (≥ 1)
         - risk_policy_version (matches deployed RiskPolicyConfig)
         - MT5AccountReality.currency confirmed to match denomination of all Decimal fields
[ ] M-3  Each required approver signs AuthorizationApproval (Ed25519)
[ ] M-4  |verified approvals| >= required_approvals
[ ] M-5  authorization_digest verified against all params
[ ] M-6  LiveAuthorization.status → ACTIVE
[ ] M-7  Kill switch Ed25519 quorum keys confirmed loaded

[GOVERNANCE GATE]
[ ] G-1  Human reviews all Gate A evidence (A-1 through A-11)
[ ] G-2  Human confirms live broker account identity
[ ] G-3  Human issues explicit GO decision
[ ] G-4  GO decision archived as governance record

UNTIL M-6 (ACTIVE): no live order can be constructed — machine-enforced
UNTIL G-3 (GO): no live order should be attempted — governance requirement
```

---

## 15. Criteria for First Live Order

$$\boxed{P_{13} = \text{GateA\_PASS} \land \text{M6\_ACTIVE} \land \text{G3\_GO} \land \text{KS\_ARMED} \land \text{RECON\_PASS} \land \text{Risk\_NORMAL} \land \text{can\_dispatch()}}$$

| Condition | Enforcement Type | Source |
|-----------|-----------------|--------|
| Gate A (A-1 through A-11) complete | Governance | Human verification |
| `LiveAuthorization.status == ACTIVE` | Machine (fail-closed) | `admission.py:650` |
| `KillSwitchState == ARMED` | Machine (fail-closed) | `kill_switch.py:158` |
| 6-D RECON pass (`can_dispatch() == True`) | Machine (fail-closed) | `adapter.py:197` |
| `RiskStatus == NORMAL` | Machine (fail-closed) | `admission.py:696` |
| `CalculationStatus == NOMINAL` | Machine (fail-closed) | `admission.py:691` |
| Human GO on record | Governance | G-3 |

$$\text{HTTP-success} \neq P_{13} \quad \text{ACK} \neq P_{13} \quad \text{unit tests} \neq P_{13} \quad \text{verbal "GO" alone} \neq P_{13}$$

---

## 16. Criteria to Remain at $0.00 (No-Go Conditions)

| Condition | Type | Enforcement |
|-----------|------|-------------|
| Any Gate A item FAIL | Governance | Human |
| `LiveAuthorization.status != ACTIVE` | **Machine** | `admission.py:650` — fail-closed |
| `KillSwitchState != ARMED` | **Machine** | `kill_switch.py:158` — fail-closed |
| RECON failing | **Machine** | `can_dispatch()` — fail-closed |
| `RiskStatus != NORMAL` | **Machine** | `admission.py:696` — fail-closed |
| A-11 demo test not completed | Governance | Human |
| DEGRADED SLA procedure not rehearsed | Governance | Human |
| `max_notional` currency denomination not confirmed | Governance | Human (M-2) |
| Human explicitly says NO | Governance | Unconditional |

---

## 17. TradingView — Explicitly Out of Scope

```
❌ TradingView Ingress Gateway  — separate backlog
❌ All TradingView integration  — separate backlog

PROHIBITED PATH (forever):
  TradingView → MT5 → Broker  ← STRICTLY FORBIDDEN

PERMITTED FUTURE PATH (when implemented, separate backlog):
  TradingView Webhook → Validation → Canonical event_id
    → Idempotency → CandidateSignal (CapitalAuthorityUSD = 0.00)
    → Research → Validation → Tournament → Risk → Admission → Execution
```

---

## 18. Phase 13 Implementation Slices (Proposed — Pending Rev3 Approval)

```
Phase 13
│
├─ Slice 1: Gate A — Pre-Live Certification
│    ├─ A-1:  RiskPolicyConfig configured with live-appropriate limits
│    ├─ A-2:  Kill switch PERSISTENTLY_BLOCKED recovery verified on demo
│    ├─ A-3:  MT5 demo full lifecycle evidence
│    ├─ A-4:  6-D Reconciliation verified on demo
│    ├─ A-5:  ForwardHealthStateMachine verified on demo
│    ├─ A-6:  EmergencyFlattenIntent forensic record verified
│    ├─ A-7:  Recovery procedures documented
│    ├─ A-8:  LiveAuthorization parameters reviewed and confirmed
│    ├─ A-9:  Rollback tested end-to-end on demo
│    ├─ A-10: DEGRADED WARNING log and SLA rehearsed on demo
│    └─ A-11: Emergency-close operator procedure demonstrated end-to-end
│
├─ Slice 2: Gate B — Human Authorization
│    ├─ LiveAuthorization constructed (M-1)
│    ├─ Human confirms all fields + currency denomination (M-2)
│    ├─ Ed25519 quorum signed (M-3 through M-5)
│    ├─ status → ACTIVE (M-6)
│    └─ Human GO decision (G-3)
│
└─ Slice 3: First Live Order (only after Gate B Machine + Governance)
     ├─ Single micro-lot live order
     ├─ Full lifecycle: SUBMITTED → ACK → RECON → FILLED
     ├─ Verify all machine gates held throughout
     ├─ Source code audit
     └─ Human confirmation of first live evidence
```

---

## 19. Architectural Debt Summary

| Debt | Severity | Phase 13 Mitigation | Resolution |
|------|----------|---------------------|------------|
| Cumulative `max_notional` not enforced per-order | P1 | `max_position_size` per-order + `RiskEngine` daily/drawdown limits | Future phase explicit implementation |
| No concurrent position count enforcement | P1 | `max_position_size = volume_min` limits single-order exposure | Future phase: `max_concurrent_positions` field |
| No automated close-only emergency channel | P1 | Operator manual close procedure (A-11) | Future phase: explicit architecture review |
| No real-time alerting UI | P2 | Structured WARNING log + SLA (Section 11.2) | Future phase |
| Phase-B transactional P1 debt (Phase 12) | P1 | Does not affect Phase 13 | Future phase |

---

## Verification Ledger (Plan Rev3)

- **Plan Status:** DRAFT — NOT APPROVED
- **Implementation Status:** NOT STARTED
- **Production Code Changes:** ZERO (planning document only)
- **Frozen Baseline Respected:** `1e1d154` — no Phase 12 contracts reopened
- **TradingView:** OUT OF SCOPE (confirmed)
- **Live Capital:** $0.00 (unchanged — Gate B not reached)
- **P0-2 Machine vs Governance Gate:** ✅ RESOLVED (Rev2, preserved)
- **P0 max_notional digest integrity:** ✅ RESOLVED (Rev2, preserved)
- **P0 cumulative max_notional NOT IMPLEMENTED:** ✅ EXPLICITLY DECLARED (Rev3)
- **P0 "max 1 concurrent position" removed:** ✅ CORRECTED (Rev3)
- **P0 "unlikely at micro-lot scale" safety argument removed:** ✅ CORRECTED (Rev3)
- **P1-1 Monitoring SLA:** ✅ RESOLVED with numeric SLA (Rev3)
- **P1-2 Emergency close semantics:** ✅ RESOLVED (Rev2, preserved)
- **P1-2b Gate A end-to-end emergency close test (A-11):** ✅ ADDED (Rev3)
- **max_notional currency denomination:** ✅ RESOLVED (Rev3)
- **Methodological Caveats:**
  - Cumulative `max_notional` not enforced at runtime — declared P1 debt; mitigated by per-order `max_position_size` and `DeterministicRiskEngine` limits
  - Emergency close requires operator manual procedure — A-11 Gate A requirement
  - Phase 13 monitoring requires active operator vigilance within defined SLA windows
