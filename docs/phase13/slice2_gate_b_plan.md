# Phase 13 Slice 2: Gate B Mandatory Human Authorization Plan (Rev 3)
## Preflight & Implementation Plan (Plan Only — Zero Execution)

> **Document:** `docs/phase13/slice2_gate_b_plan.md`  
> **Status:** PROPOSED — PENDING HUMAN AUDITOR APPROVAL (REV 3)  
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

## User Review Required (Rev 3 Audit Adjustments)

> [!CAUTION]
> **CRITICAL GOVERNANCE BOUNDARY: PLAN ONLY — ZERO EXECUTION**  
> This document establishes ONLY the preflight plan, schema contracts, and architectural test harness for Gate B. It **DOES NOT**:
> 1. Create or fund any live broker account.
> 2. Connect to any live broker for trading.
> 3. Transmit any `order_send` or order mutation.
> 4. Activate any `LiveAuthorization` (`status` remains strictly un-activated).
> 5. Sign any `AuthorizationApproval` or `HumanGORecord` with live keys.
> 6. Issue any "GO" decision.
> 7. Unlock Gate B or authorize Slice 3.

### Key Refinements in Rev 3 (Addressing Audit Blockers B10 & B11 + Refinements):
1. **[BLOCKER B10 RESOLVED] Per-Order `max_notional` is Machine-Enforced:**
   - In `admission.py:construct_order_intent()`, added explicit per-order notional ceiling check:
     $$\text{order\_notional} = \text{quantity} \times \text{contract\_size} \times \text{price} \le \text{authorization.max\_notional}$$
   - Any order exceeding `max_notional` fails closed immediately with `PreLiveRiskAdmissionError`.
   - Clear architectural distinction maintained:
     - **Per-Order Notional Ceiling:** ✅ **MACHINE-ENFORCED**
     - **Cumulative Portfolio Exposure Ceiling:** ❌ **NOT IMPLEMENTED / DEFERRED TO PHASE 14**
2. **[BLOCKER B11 RESOLVED] Cryptographically Non-Repudiable `HumanGORecord` Contract:**
   - Replaced prose description with formal immutable schema `HumanGORecord` in `schema.py`.
   - Binds 5 cryptographic digests: `authorization_digest`, `gate_a_evidence_digest`, `live_account_identity_digest`, `approver_public_key_id`, and `record_digest`.
   - Machine verification in `activate_live_authorization()` verifies Ed25519 digital signature, key validity in `TrustStore`, and all digest matches before emitting `ACTIVE`.
3. **[REFINEMENT 1 RESOLVED] Broker-Authoritative Snapshot Measurement Points for `STRICT_SERIAL_MODE`:**
   - Pre-dispatch measurement point explicitly anchored to `MT5BrokerRealitySnapshot` via authoritative 6-D reconciliation:
     $$\text{Reconciliation} \to \text{Broker Reality Snapshot} \to \text{Pre-Dispatch Assertion} \to \text{Admission} \to \text{Dispatch}$$
4. **[REFINEMENT 2 RESOLVED] Testable Discrete Invariants for Pending Orders:**
   - Replaced continuous "at all times" with discrete, measurable pre- and post-conditions:
     - **Pre-Condition (Before Every Dispatch):**
       `broker_snap.pending_orders == 0` $\land$ `coordinator.in_flight_orders == 0` $\land$ `broker_snap.open_positions == 0` (for entry) $\land$ `reserved_exposure == 0`.
     - **Post-Condition (After Dispatch):**
       Synchronous 6-D reconciliation to verify terminal state.
5. **[REFINEMENT 3 RESOLVED] `max_order_rate_per_minute` Accurately Classified:**
   - Formally designated as **GOVERNANCE-BOUND (P1 Debt — Throttle mechanism deferred to Phase 14; fully contained by STRICT_SERIAL_MODE)**.

---

## 1. Executive Summary & Progression Topology

The objective of Phase 13 Slice 2 is to build the formal, dual-layer authorization harness (**Machine Gate + Governance Gate**) required to evaluate Gate B. 

Gate B is the sole authoritative mechanism in ACASH capable of transitioning `LiveAuthorization.status` to `ACTIVE`. Under Rev 3, `ACTIVE` is impossible to reach without a mathematically verified, Ed25519-signed `HumanGORecord` bound to the exact live account and certified Gate A evidence digests.

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

## 2. Updated Authorization State Machine & Human GO Bridge (B10 & B11)

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
   APPROVED_PENDING_GO  ◄── [Machine Quorum Met; Orders Strictly BLOCKED]
         │
         │ [SOVEREIGN HUMAN GOVERNANCE GATE]
         │ G-1: Gate A Evidence Pack Verified (Digest Match)
         │ G-2: Live Broker Account Verified via Read-Only Preflight
         │ G-3: Human Issues Explicit Signed HumanGORecord (Ed25519)
         │ G-4: HumanGORecord Archived in Repository Ledger
         │
         │ activate_live_authorization(auth, go_record, trust_store)
         ▼
        ACTIVE          ◄── [Machine-enables admission.py per-order checks]
         │
         ├─ Suspended (Kill switch trip / anomaly)
         ├─ Expired (now_utc > expires_at)
         └─ Revoked (CertificateRevocationEvent)
```

> [!IMPORTANT]
> **State Machine Invariant:**  
> In `APPROVED_PENDING_GO`, `admission.py:construct_order_intent()` strictly raises `PreLiveRiskAdmissionError("AUTHORIZATION_PENDING_HUMAN_GO")`.  
> Transition to `ACTIVE` is guarded by `activate_live_authorization()`, which performs full cryptographic signature and digest verification over the `HumanGORecord`.

---

## 3. Cryptographic `HumanGORecord` Contract Specification (B11)

To eliminate the ambiguity of "written sign-off statements" and provide genuine non-repudiation, Slice 2 introduces the formal `HumanGORecord` domain model in `src/acash/execution/schema.py`:

```python
class HumanGORecord(BaseModel):
    """Cryptographically verifiable, non-repudiable sovereign authorization artifact.
    
    Proves that a designated human authority personally authorized live capital
    deployment for a specific strategy on a specific broker account with verified
    Gate A evidence.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    human_go_record_id: str = Field(description="Deterministic identifier (e.g. GO_P13_20260904_001).")
    authorization_id: str = Field(description="LiveAuthorization identifier being approved.")
    authorization_digest: str = Field(description="Exact SHA-256 digest of the LiveAuthorization artifact.")
    gate_a_evidence_digest: str = Field(description="Exact SHA-256 digest of certified Gate A evidence pack.")
    live_account_identity_digest: str = Field(description="Exact SHA-256 digest of verified live account identity.")
    decision: Literal["GO"] = Field(default="GO", description="Explicit sovereign authorization decision.")
    approver_identity: str = Field(description="Human authority name / organizational role.")
    approver_public_key_id: str = Field(description="Key ID in Ed25519TrustStore (Role: HUMAN_AUDITOR).")
    issued_at_utc: datetime = Field(description="Strict UTC timestamp of human decision.")
    expires_at_utc: datetime = Field(description="Mandatory expiration window for this GO decision.")
    signature_algorithm: Literal["Ed25519"] = Field(default="Ed25519")
    signature: str = Field(description="Base64-encoded Ed25519 digital signature over canonical payload.")
    record_digest: str = Field(description="Canonical SHA-256 digest of this record.")
    previous_record_digest: str = Field(default="0" * 64, description="Audit chain linking.")

    def compute_canonical_payload_bytes(self) -> bytes:
        payload = {
            "human_go_record_id": self.human_go_record_id,
            "authorization_id": self.authorization_id,
            "authorization_digest": self.authorization_digest,
            "gate_a_evidence_digest": self.gate_a_evidence_digest,
            "live_account_identity_digest": self.live_account_identity_digest,
            "decision": self.decision,
            "approver_identity": self.approver_identity,
            "approver_public_key_id": self.approver_public_key_id,
            "issued_at_utc": self.issued_at_utc.isoformat(),
            "expires_at_utc": self.expires_at_utc.isoformat(),
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
```

### Machine Verification Invariant in `activate_live_authorization()`:
$$\boxed{\text{Valid Ed25519 Sig} \land \text{Digest Matches Auth} \land \text{Digest Matches Gate A} \land \text{Digest Matches Live Account} \land \text{Decision == 'GO'} \land \text{Not Expired} \land \text{Key Active}}$$
If any single condition diverges, activation fails closed with `DataContractError`.

---

## 4. Per-Order `max_notional` Machine Enforcement Contract (B10)

To close Blocker B10, `construct_order_intent()` in `src/acash/execution/admission.py` is upgraded to machine-enforce per-order notional limits:

```python
# 1. Calculate per-order notional value in account currency
order_units = quantity * symbol_spec.contract_size
order_notional = order_units * price

# 2. Machine-Enforce per-order notional ceiling
if order_notional > authorization.max_notional:
    raise PreLiveRiskAdmissionError(
        f"Order notional {order_notional} exceeds authorized max_notional "
        f"({authorization.max_notional})."
    )
```

### Capital Boundary Architecture Matrix:
| Boundary Scope | Enforcement Mechanism | Status | Implementation Authority |
| :--- | :--- | :---: | :--- |
| **Per-Order Sizing (`quantity`)** | `quantity <= max_position_size` | ✅ **MACHINE-ENFORCED** | `admission.py:685` |
| **Per-Order Notional Ceiling** | `order_notional <= max_notional` | ✅ **MACHINE-ENFORCED** | Upgraded `admission.py` (B10) |
| **Cumulative Portfolio Notional** | $\sum \text{exposure} + \text{new} \le \text{max\_notional}$ | ❌ **NOT IMPLEMENTED** | Deferred to Phase 14 (P1 Debt) |
| **Temporary Slice 3 Containment** | `STRICT_SERIAL_MODE = TRUE` | ✅ **SAFETY-LOCKED** | Restricts active exposure to $\le 1$ order |

---

## 5. Parameter Ownership Matrix (Zero Operational Defaults)

| Parameter Name | Schema Type | Proposed Constraint | Enforcement State | Authority / Owner |
| :--- | :--- | :--- | :--- | :--- |
| `authorization_id` | `str` | `AUTH_P13_LIVE_001` | **Cryptographically Bound** | Machine / Unique |
| `certificate_id` | `str` | Linked Phase 6/8.5 Certificate | **Cryptographically Bound** | Statistical Authority |
| `strategy_id` | `str` | Target Live Strategy ID | **Machine-Enforced** per order | Strategy Authority |
| `max_notional` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Machine-Enforced Per-Order** (B10) | **Human Auditor** |
| `max_position_size` | `Decimal` | `Decimal("0.01")` (Micro-lot) | **Machine-Enforced Per-Order** (`admission.py:685`) | **Plan Rev3 §4.6** |
| `max_order_rate_per_minute` | `int` | `1` (Throttle limit) | **Governance-Bound (P1 Debt)** (Contained by serial mode) | **Human Auditor** |
| `max_daily_loss_notional` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Machine-Enforced by RiskEngine** (Binary Reject) | **Human Auditor** |
| `max_drawdown_pct` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Machine-Enforced by RiskEngine** (Binary Reject) | **Human Auditor** |
| `allowed_venues` | `Tuple[str]` | `("LIVE_MT5",)` | **Machine-Enforced Per-Order** (`admission.py:674`) | **Human Auditor** |
| `allowed_symbols` | `Tuple[str]` | `("EURUSD",)` | **Machine-Enforced Per-Order** (`admission.py:679`) | **Human Auditor** |
| `risk_policy_version` | `str` | `v1.0.0-p13` | **Cryptographically Bound** | Risk Policy Registry |
| `required_approvals` | `int` | **[TBD — REQUIRED GOVERNANCE INPUT]** | **Machine-Enforced** ($\ge 1$, zero default) | **Governance Policy** |
| `authorized_at` | `datetime` | UTC timestamp of issuance | **Cryptographically Bound** | Machine Clock |
| `expires_at` | `datetime` | Time-boxed window (e.g. +24h) | **Machine-Enforced Per-Order** (`admission.py:668`) | **Human Auditor** |
| `currency` | `str` | `MT5AccountReality.currency` | **Operational Convention** (Verified at M-2) | **Human Auditor** |

---

## 6. Measurable Invariants for `STRICT_SERIAL_MODE` & Pending Orders

To resolve Refinements 1 and 2, `STRICT_SERIAL_MODE` is formalized with **discrete broker-authoritative measurement points**:

### Measurement Point Architecture:
$$\text{Reconciliation Engine} \to \text{Broker Reality Snapshot} \to \text{Serial Mode Assertion} \to \text{Order Admission} \to \text{Dispatch}$$

```python
class StrictSerialExecutionLock:
    """Discrete broker-authoritative safety gate for Slice 3 deployment."""

    @staticmethod
    def assert_serial_preconditions(
        broker_snapshot: MT5BrokerRealitySnapshot,
        coordinator: ExecutionCoordinator,
    ) -> None:
        # 1. Measurable Invariant: Pending Orders == 0
        if len(broker_snapshot.orders) != 0:
            raise PreLiveRiskAdmissionError(
                f"STRICT_SERIAL_VIOLATION: Broker has {len(broker_snapshot.orders)} active pending orders. Expected 0."
            )
        # 2. Measurable Invariant: In-Flight Orders == 0
        if coordinator.in_flight_count != 0:
            raise PreLiveRiskAdmissionError(
                f"STRICT_SERIAL_VIOLATION: Coordinator has {coordinator.in_flight_count} in-flight orders. Expected 0."
            )
        # 3. Measurable Invariant: Open Positions == 0 for new entry
        if len(broker_snapshot.positions) != 0:
            raise PreLiveRiskAdmissionError(
                f"STRICT_SERIAL_VIOLATION: Broker has {len(broker_snapshot.positions)} open positions. Expected 0."
            )
```
- **Pre-Dispatch:** Must pass `assert_serial_preconditions()` using a freshly captured broker snapshot ($< 1000\text{ ms}$ old).
- **Post-Dispatch:** Requires immediate synchronous 6-D reconciliation cycle before clearing the serial lock.

---

## 7. M-2 Multi-Dimensional Valuation & Unit Contract

Item M-2 validates the four dimensions of currency and notional valuation:

1. **Account Currency:** `MT5AccountReality.currency == "USD"`.
2. **Monetary Unit:** Stated in 1.00 base units of account currency.
3. **Asset Valuation Basis:** EURUSD base currency is EUR, quote currency is USD.
4. **Notional Calculation Formula:**
   $$\text{Notional USD} = \text{Volume (lots)} \times \text{Contract Size} \times \text{Execution Price}$$
   $$\text{Example: } 0.01 \text{ lot} \times 100,000 \times 1.16282 = 1,162.82 \text{ USD}$$
   Human auditor verifies that `max_notional` $\ge 1,162.82\text{ USD}$ (e.g. $1,500.00 USD), otherwise the per-order machine check (B10) will reject 0.01 lot EURUSD orders.

---

## 8. Operational Demarcation: Read-Only Preflight vs Trading Session

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

## 9. Updated Automated Test Matrix (14 Tests)

The implementation of Slice 2 will include the following unit test suite (`tests/unit/execution/test_gate_b_authorization_lifecycle.py`):

1. `test_draft_creation_with_valid_parameters`: Verifies M-1 schema bounds.
2. `test_currency_and_valuation_basis_contract`: Verifies M-2 multi-dimensional checks.
3. `test_ed25519_quorum_signing_and_verification`: Verifies M-3 and M-4.
4. `test_authorization_digest_tamper_proofing`: Verifies M-5.
5. `test_kill_switch_quorum_loading`: Verifies M-7.
6. `test_active_cannot_occur_before_human_go`: Verifies that `APPROVED_PENDING_GO` blocks order construction.
7. `test_human_go_record_cryptographic_verification`: Verifies Ed25519 signature on `HumanGORecord`.
8. `test_active_transition_requires_all_five_matching_digests`: Verifies M-6 digest bindings.
9. `test_per_order_max_notional_machine_enforcement`: Verifies B10 rejection when $1162.82 > 500.
10. `test_required_approvals_cannot_default`: Verifies fail-closed when `required_approvals` is omitted.
11. `test_max_drawdown_pct_cannot_default`: Verifies fail-closed when `max_drawdown_pct` is omitted.
12. `test_strict_serial_mode_rejections`: Verifies discrete pre-dispatch snapshot checks (pending, in-flight, open).
13. `test_read_only_preflight_cannot_escalate_trading`: Verifies preflight rejects trade-enabled session.
14. `test_revocation_event_halts_issuance`: Verifies rollback and emergency revocation.

---

## 10. Exact Stop Gate

```text
================================================================================
                    PHASE 13 SLICE 2 EXACT STOP GATE
================================================================================
Upon completion of Slice 2 Implementation:
1. LiveAuthorization will exist in APPROVED_PENDING_GO.
2. HumanGORecord verification machinery will be fully operational.
3. Per-order max_notional machine gate will be fully operational.
4. Live Capital remains strictly $0.00.
5. Zero broker orders will be sent.
6. Master trading password will NOT be loaded.
7. All execution will STOP completely.
8. Progression to Slice 3 (First Live Order) requires explicit, independent
   Human Sign-Off.
================================================================================
```
