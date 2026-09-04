# Phase 13 Slice 2: Gate B Mandatory Human Authorization Plan (Rev 2)
## Preflight & Implementation Plan (Plan Only — Zero Execution)

> **Document:** `docs/phase13/slice2_gate_b_plan.md`  
> **Status:** PROPOSED — PENDING HUMAN AUDITOR APPROVAL (REV 2)  
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Implementation Correctness $\neq$ Mathematical Validity)  
> **Governing Specifications:**
> - `docs/phase13/PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV3.md` (§3, §4, §14, §15, §16, §18)
> - `docs/phase13/consolidated_gate_a_audit.md` (Gate A CERTIFIED baseline)
> - `docs/SESSION_HANDOFF.md`
> **Current Baseline:**
> - Phase 13 Slice 1 (Gate A): `✅ CERTIFIED`
> - Gate B: `🔒 STRICTLY LOCKED`
> - Slice 3 (First Live Order): `⛔ BLOCKED`
> - Live Capital Authority: `💰 $0.00`
> - Broker Reality (Demo 112040157): `🟢 100% FLAT`
> - Phase 17: `✅ PARKED / FROZEN`

---

## User Review Required (Rev 2 Audit Adjustments)

> [!CAUTION]
> **CRITICAL GOVERNANCE BOUNDARY: PLAN ONLY — ZERO EXECUTION**  
> This document establishes ONLY the preflight plan and architectural contract for Gate B. It **DOES NOT**:
> 1. Create or fund any live broker account.
> 2. Connect to any live broker for trading.
> 3. Transmit any `order_send` or order mutation.
> 4. Activate any `LiveAuthorization` (`status` remains strictly un-activated).
> 5. Sign any `AuthorizationApproval` with live keys.
> 6. Issue any "GO" decision.
> 7. Unlock Gate B or authorize Slice 3.

### Key Refinements in Rev 2 (Addressing Audit Findings B3–B9):
1. **[BLOCKER B3 RESOLVED] Sovereign Human GO Precedes Machine ACTIVE:**
   - The sequence has been fundamentally inverted: `M-6 ACTIVE` can NEVER occur before `G-3 Human GO` and `G-4 GO Archival`.
   - Introduced intermediate lifecycle state: `APPROVED_PENDING_GO`.
   - `ACTIVE` transition requires BOTH complete cryptographic quorum AND a verified, digest-bound `HumanGORecord`.
2. **[B4 RESOLVED] No Operational Default for `required_approvals`:**
   - Removed `required_approvals = 1` default.
   - Formally designated as `[REQUIRED GOVERNANCE INPUT / TBD]` (schema invariant: $\ge 1$).
3. **[B5 RESOLVED] No Operational Default for `max_drawdown_pct`:**
   - Removed `5.0%` placeholder.
   - Formally designated as `[REQUIRED HUMAN INPUT / TBD]` (schema invariant: $(0, 100]$).
4. **[B6 RESOLVED] Formalized `STRICT_SERIAL_MODE = TRUE`:**
   - Established strict runtime constraints for Slice 3 to contain risk during un-enforced cumulative exposure:
     $$\text{In-Flight Orders} \le 1 \quad \land \quad \text{Open Positions} \le 1 \quad \land \quad \text{Pending Orders} = 0$$
   - Explicitly documented as a temporary containment control, NOT equivalent to cumulative exposure enforcement.
5. **[B7 RESOLVED] Capital Boundary Declared `PARTIALLY ENFORCED`:**
   - Per-order bound is machine-enforced; cumulative exposure remains acknowledged P1 debt deferred to Phase 14.
6. **[B8 RESOLVED] Multi-Dimensional Valuation & Unit Contract (M-2):**
   - M-2 validates account currency, monetary unit, valuation basis, and FX conversion formula.
7. **[B9 RESOLVED] Strict Separation of Read-Only Preflight vs Trade Permission:**
   - Live preflight is restricted to Read-Only inspection (Login, Server, Balance, Leverage, Currency).
   - Master trading password / trade execution permission is strictly quarantined to Slice 3 under explicit human control.

---

## 1. Executive Summary & Progression Topology

The objective of Phase 13 Slice 2 is to build the formal, dual-layer authorization harness (**Machine Gate + Governance Gate**) required to evaluate Gate B. 

Gate B is the sole authoritative mechanism in ACASH capable of transitioning `LiveAuthorization.status` to `ACTIVE`. Under Rev 2, `ACTIVE` is strictly unachievable without an immutable, cryptographically bound Human "GO" record on disk.

```
┌────────────────────────────────────────────────────────────────────────┐
│               PHASE 13 PROGRESSION & STOP GATE TOPOLOGY                │
├────────────────────────────────────────────────────────────────────────┤
│  Slice 1: Gate A — Pre-Live Rehearsal (Demo)        │  ✅ CERTIFIED     │
│  Slice 2: Gate B — Dual-Gate Authorization Setup    │  🔒 THIS PLAN     │
│  Slice 3: First Live Order (Micro-Lot 0.01)          │  ⛔ STRICTLY      │
│                                                      │     BLOCKED      │
└──────────────────────────────────────────────────────┴─────────────────┘
```

---

## 2. Updated Authorization State Machine (Resolving Blocker B3)

```
       DRAFT (M-1)
         │
         │ submit_for_approval()
         ▼
   PENDING_APPROVAL
         │
         │ Ed25519 Quorum Verified (M-3, M-4, M-5)
         │ Kill Switch ARMED (M-7)
         ▼
   APPROVED_PENDING_GO  ◄── [Machine Quorum Met; Orders Still BLOCKED]
         │
         │ G-1: Gate A Evidence Reviewed
         │ G-2: Live Broker Account Verified (Read-Only)
         │ G-3: Explicit Human GO Issued
         │ G-4: HumanGORecord Written & Archived
         ▼
        ACTIVE          ◄── [ONLY Here: admission.py construct_order_intent() enabled]
         │
         ├─ Suspended (Kill switch trip / anomaly)
         ├─ Expired (now_utc > expires_at)
         └─ Revoked (CertificateRevocationEvent)
```

> [!IMPORTANT]
> **State Machine Invariant:**  
> In `APPROVED_PENDING_GO`, all cryptographic signatures and digests are 100% valid, but `admission.py:650` strictly rejects order construction with `PreLiveRiskAdmissionError("AUTHORIZATION_PENDING_HUMAN_GO")`.  
> `ACTIVE` can ONLY be emitted by passing a valid `HumanGORecord` whose digest is bound into the activation transition.

---

## 3. Revised Machine Gate vs Governance Gate Sequence

The execution sequence is strictly ordered so that Machine Verification prepares the authorization, Human Governance authorizes the deployment, and Machine Activation executes last:

```
[MACHINE PREPARATION]
M-1: Construct LiveAuthorization [DRAFT]
M-2: Verify Live Account Parameters, Currency & Valuation Basis (Read-Only)
M-3: Collect Ed25519 AuthorizationApproval Signatures
M-4: Verify Quorum (|approvals| >= required_approvals)
M-5: Verify authorization_digest Integrity
M-7: Verify Sovereign Kill Switch ARMED & Quorum Keys Loaded
      ↓
State: APPROVED_PENDING_GO
      ↓
[SOVEREIGN GOVERNANCE GATE]
G-1: Human Reviews Gate A Certified Evidence Pack
G-2: Human Confirms Live Broker Identity & Ownership
G-3: Human Issues Explicit "GO" Decision (Non-Repudiable)
G-4: System Archives HumanGORecord with Digest Chaining
      ↓
[FINAL MACHINE ACTIVATION]
M-6: Transition LiveAuthorization to ACTIVE (Bound to HumanGORecord digest)
      ↓
STOP (Gate B Complete — Slice 3 Awaits Separate Human Authorization)
```

| Gate Step | Invariant & Contract Description | Enforcement Mechanism | Substrate |
| :---: | :--- | :--- | :--- |
| **M-1** | `LiveAuthorization` DRAFT artifact constructed with valid schema | Pydantic V2 immutable validation (`schema.py:252`) | In-Memory / JSON |
| **M-2** | Multi-dimensional verification of currency, unit, and valuation basis | Fail-closed comparison against live broker terminal | MT5 IPC (Read-Only) |
| **M-3** | Ed25519 digital signature generated for each approver | `Ed25519Signer` / KMS over canonical approval bytes | Ed25519 (RFC 8032) |
| **M-4** | Quorum check: `\|verified approvals\| >= required_approvals` | `_collect_verified_approvals()` (`admission.py:402`) | In-Memory TrustStore |
| **M-5** | `authorization_digest` covers all 15 params + sorted approvals | `compute_authorization_digest()` (`schema.py:349`) | SHA-256 Digest |
| **M-7** | Sovereign Kill Switch Ed25519 quorum keys loaded and ARMED | `SovereignKillSwitchController(trust_store=...)` | Risk Controller |
| **G-1** | Formal audit review of Gate A Evidence Pack | Verification of `docs/phase13/consolidated_gate_a_audit.md` | Human Auditor |
| **G-2** | Live broker account identity verification (Read-Only) | Written confirmation of login, server, owner, leverage | Human Auditor |
| **G-3** | Explicit human "GO" authorization command | Signed, non-repudiable written sign-off statement | Human Auditor |
| **G-4** | Archival of GO decision and digest binding | Committed immutable JSON/Markdown record in repository | Git Versioning |
| **M-6** | Status transition: `APPROVED_PENDING_GO -> ACTIVE` | `activate_live_authorization(auth, human_go_record)` | Domain State Machine |

---

## 4. Parameter Ownership Matrix (Rev 2 — Zero Operational Defaults)

| Parameter Name | Schema Type | Proposed Constraint | Enforcement State | Authority / Owner |
| :--- | :--- | :--- | :--- | :--- |
| `authorization_id` | `str` | `AUTH_P13_LIVE_001` | **Cryptographically Bound** | Machine / Unique |
| `certificate_id` | `str` | Linked Phase 6/8.5 Certificate | **Cryptographically Bound** | Statistical Authority |
| `strategy_id` | `str` | Target Live Strategy ID | **Machine-Enforced** per order | Strategy Authority |
| `max_notional` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Cryptographically Bound** (Cumulative NOT enforced) | **Human Auditor** |
| `max_position_size` | `Decimal` | `Decimal("0.01")` (Micro-lot) | **Machine-Enforced** per order (`admission.py:685`) | **Plan Rev3 §4.6** |
| `max_order_rate_per_minute` | `int` | `1` (Throttle: 1 order/min) | **Cryptographically Bound** | **Human Auditor** |
| `max_daily_loss_notional` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Cryptographically Bound** (RiskEngine enforces) | **Human Auditor** |
| `max_drawdown_pct` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Machine-Enforced** by RiskEngine (Binary Reject) | **Human Auditor** |
| `allowed_venues` | `Tuple[str]` | `("LIVE_MT5",)` | **Machine-Enforced** per order (`admission.py:674`) | **Human Auditor** |
| `allowed_symbols` | `Tuple[str]` | `("EURUSD",)` | **Machine-Enforced** per order (`admission.py:679`) | **Human Auditor** |
| `risk_policy_version` | `str` | `v1.0.0-p13` | **Cryptographically Bound** | Risk Policy Registry |
| `required_approvals` | `int` | **[TBD — REQUIRED GOVERNANCE INPUT]** | **Machine-Enforced** ($\ge 1$, no default) | **Governance Policy** |
| `authorized_at` | `datetime` | UTC timestamp of issuance | **Cryptographically Bound** | Machine System Clock |
| `expires_at` | `datetime` | Time-boxed window (e.g. +24h) | **Machine-Enforced** per order (`admission.py:668`) | **Human Auditor** |
| `currency` | `str` | `MT5AccountReality.currency` | **Operational Convention** (Verified at M-2) | **Human Auditor** |

---

## 5. Capital Boundary Assessment & Temporary Safety Locks

### 5.1 Capital Boundary Status: PARTIALLY ENFORCED
- **Per-Order Sizing:** ✅ **MACHINE-ENFORCED** (`quantity <= max_position_size` checked at `admission.py:685`).
- **Cumulative Exposure:** ❌ **NOT IMPLEMENTED** (`current_exposure + new_order_notional <= max_notional` is acknowledged P1 architectural debt deferred to Phase 14).
- **Declaration:** ACASH does **NOT** claim full capital boundary enforcement in Slice 2/3.

### 5.2 Formalization of `STRICT_SERIAL_MODE = TRUE`
To prevent the cumulative exposure gap from causing risk breach during Slice 3 live testing, ACASH formalizes `STRICT_SERIAL_MODE` as an explicit safety lock:

```python
class StrictSerialExecutionLock:
    """Temporary containment control for Slice 3 micro-capital deployment.
    
    Enforces:
    1. In-flight orders count == 0 before any dispatch.
    2. Open positions count == 0 before any new entry.
    3. Pending broker orders count == 0 at all times.
    4. Reserved exposure ambiguity == 0 (no concurrent allocations).
    Fails closed immediately if any condition is breached.
    """
```
- **Governance Status:** Temporary Slice 3 containment control; does NOT replace Phase 14 cumulative exposure engine.

---

## 6. M-2 Currency, Monetary Unit & Valuation Basis Contract

To eliminate currency and valuation ambiguity (Finding B8), Item M-2 requires explicit validation across four dimensions:

1. **Account Currency:** Must match `MT5AccountReality.currency` (e.g. `"USD"`).
2. **Monetary Unit:** Stated in base units of account currency (e.g. 1.0 = 1.00 USD).
3. **Asset Valuation Basis:** For EURUSD:
   $$\text{Base Currency} = \text{EUR}, \quad \text{Quote Currency} = \text{USD}$$
4. **Notional Calculation Formula:**
   $$\text{Notional USD} = \text{Volume (lots)} \times \text{Contract Size} \times \text{Execution Price}$$
   $$\text{Example: } 0.01 \text{ lot} \times 100,000 \times 1.16282 = 1,162.82 \text{ USD Notional}$$
   The human auditor must verify that `max_notional` accommodates the asset's contract notional in account currency.

---

## 7. Operational Demarcation: Read-Only Preflight vs Trading Session

To prevent unintended privilege escalation (Finding B9):

```
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│   SLICE 2: READ-ONLY PREFLIGHT       │     │   SLICE 3: TRADE-ENABLED SESSION     │
├──────────────────────────────────────┤     ├──────────────────────────────────────┤
│ - Connect using Investor Password    │     │ - Connect using Master Password      │
│ - Trade Permission: DISABLED (Read)  │     │ - Trade Permission: ENABLED (Trade)  │
│ - Queries: account_info, symbols     │     │ - Order Dispatch: Micro-lot 0.01     │
│ - Zero order_send possible           │     │ - Explicit Human Sign-Off Required   │
│ - Fails closed if trade_allowed=True │     │ - Strictly Serial Execution Lock     │
└──────────────────────────────────────┘     └──────────────────────────────────────┘
```
Slice 2 is strictly quarantined to Read-Only connectivity. Transition to trade-enabled connectivity cannot occur as an automated side-effect.

---

## 8. Failure, Revocation & Rollback Semantics

1. **Signature Mismatch:** `DomainValidationError` raised; status remains `DRAFT` / `PENDING_APPROVAL`.
2. **Digest Mismatch:** Any parameter tampering fails canonical SHA-256 verification.
3. **Missing Human GO:** If `HumanGORecord` is absent, corrupted, or does not match `authorization_id`, transition to `ACTIVE` raises `DataContractError`.
4. **Emergency Revocation:** `CertificateRevocationEvent` immediately transitions authorization to `REVOKED` (`admission.py` halts fail-closed).
5. **Kill Switch Veto:** If `SovereignKillSwitchController.state != ARMED`, order admission raises `DataContractError("EXECUTION_ADMISSION_BLOCKED")`.

---

## 9. Updated Automated Test Matrix

The implementation of Slice 2 will include the following unit test suite (`tests/unit/execution/test_gate_b_authorization_lifecycle.py`):

1. `test_draft_creation_with_valid_parameters`: Verifies M-1 schema.
2. `test_currency_and_valuation_basis_contract`: Verifies M-2 multi-dimensional checks.
3. `test_ed25519_quorum_signing_and_verification`: Verifies M-3 and M-4.
4. `test_authorization_digest_tamper_proofing`: Verifies M-5.
5. `test_kill_switch_quorum_loading`: Verifies M-7.
6. `test_active_cannot_occur_before_human_go`: Verifies that `APPROVED_PENDING_GO` cannot construct orders.
7. `test_active_transition_binds_human_go_digest`: Verifies M-6 requires valid `HumanGORecord`.
8. `test_required_approvals_cannot_default`: Verifies fail-closed when `required_approvals` is missing.
9. `test_max_drawdown_pct_cannot_default`: Verifies fail-closed when `max_drawdown_pct` is missing.
10. `test_strict_serial_mode_rejections`:
    - Rejects 2nd in-flight order.
    - Rejects 2nd open position.
    - Rejects unexpected pending order.
11. `test_read_only_preflight_cannot_escalate_trading`: Verifies preflight rejects trade-enabled session.
12. `test_revocation_event_halts_issuance`: Verifies rollback.

---

## 10. Exact Stop Gate

```text
================================================================================
                    PHASE 13 SLICE 2 EXACT STOP GATE
================================================================================
Upon completion of Slice 2 Implementation:
1. LiveAuthorization will exist in APPROVED_PENDING_GO (or ACTIVE only if GO signed).
2. Live Capital remains strictly $0.00.
3. Zero broker orders will be sent.
4. Master trading password will NOT be loaded.
5. All execution will STOP completely.
6. Progression to Slice 3 (First Live Order) requires explicit, independent
   Human Sign-Off.
================================================================================
```
