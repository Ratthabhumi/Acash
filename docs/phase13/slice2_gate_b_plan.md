# Phase 13 Slice 2: Gate B Mandatory Human Authorization Plan (Rev 6)
## Preflight & Implementation Plan (Plan Only — Zero Execution)

> **Document:** `docs/phase13/slice2_gate_b_plan.md`  
> **Status:** PROPOSED — PENDING HUMAN AUDITOR APPROVAL (REV 6)  
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

## User Review Required (Rev 6 Audit Adjustments)

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

### Key Refinements in Rev 6 (Addressing Audit Findings B21–B24):

1. **[B21 RESOLVED] Accurate Separation of Preventive vs. Detective Capital Controls:**
   - **Terminological Discipline:** Removed all claims of "guaranteeing that actual broker execution does not breach `max_notional`". ACASH does not control venue order matching engines during extreme market gaps.
   - **Preventive Control (Pre-Admission):** Prevents the submission of any order whose *bounded executable risk* (derived from conservative worst-case price) exceeds `max_notional`.
   - **Detective & Containment Control (Post-Fill):** Detects any broker execution that fills outside the authorized capital bound during 6-D reconciliation, immediately transitions adapter to `BLOCKED`, raises `NOTIONAL_BREACH_ANOMALY`, and fail-closes all subsequent execution.
2. **[B22 RESOLVED] Explicit Semantics of `max_slippage_points`:**
   - Formally designated as: **ACASH Assumed Adverse Price Movement Bound** (and forwarded as broker request parameter `MqlTradeRequest.deviation` where supported).
   - Clarified that it constitutes an internal risk-bound ceiling for pre-admission bounding, **NOT** a venue-guaranteed fill ceiling during extreme market illiquidity.
3. **[B23 RESOLVED] Formal `MT5QuoteSnapshot` Contract & Freshness Bounds:**
   - Added a dedicated, immutable `MT5QuoteSnapshot` domain contract with strict mathematical assertions:
     - Strict UTC timestamp: `timestamp_utc`.
     - Quote freshness ceiling: $\text{quote\_age} \le \text{max\_quote\_age\_ms}$ (Default: $500\text{ ms}$, Zero magic floor).
     - Symbol alignment: `quote.symbol == intent.symbol`.
     - Positive and non-inverted spread: $\text{ask} \ge \text{bid} > 0$.
     - Positive units: $\text{point\_size} > 0 \land \text{contract\_size} > 0$.
   - **Transactional Observation Boundary:** Both `MT5BrokerRealitySnapshot` and `MT5QuoteSnapshot` are captured under the exclusive `SerialDispatchLock` immediately prior to admission.
4. **[B24 RESOLVED] Accurate Concurrency Boundary Framing:**
   - Reframed concurrency boundary:
     - **ACASH-Internal Races:** Eliminated via `ExecutionCoordinator` exclusive `SerialDispatchLock`.
     - **External Broker Mutations:** ACASH cannot prevent external actions on the broker account (e.g. manual MT5 terminal, EA); external mutations are handled via **pre-dispatch assertion rejection** and **immediate post-dispatch reconciliation anomaly detection & containment**.

---

## 1. Executive Summary & Progression Topology

The objective of Phase 13 Slice 2 is to build the formal, dual-layer authorization harness (**Machine Gate + Governance Gate**) required to evaluate Gate B. 

Gate B is the sole authoritative mechanism in ACASH capable of transitioning `LiveAuthorization.status` to `ACTIVE`. Under Rev 6, `ACTIVE` is impossible to reach without a mathematically verified, Ed25519-signed `HumanGORecord` bound to the exact live account, certified Gate A evidence, and tamper-evident audit chain digests.

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

## 2. Updated Authorization State Machine & Sovereign Human GO Bridge

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
         ├─ Expired (now_utc >= min(auth.expires_at, go_record.expires_at_utc))
         └─ Revoked (CertificateRevocationEvent)
```

> [!IMPORTANT]
> **State Machine Invariant:**  
> In `APPROVED_PENDING_GO`, `admission.py:construct_order_intent()` strictly raises `PreLiveRiskAdmissionError("AUTHORIZATION_PENDING_HUMAN_GO")`.  
> Transition to `ACTIVE` is guarded by `activate_live_authorization()`, which performs full cryptographic signature, chain linkage, and digest verification over the `HumanGORecord`.

---

## 3. Cryptographic `HumanGORecord` Contract Specification (B11, B13, B14, B15)

To provide genuine non-repudiation and prevent audit chain tampering, Slice 2 introduces the formal `HumanGORecord` domain model in `src/acash/execution/schema.py`:

```python
class HumanGORecord(BaseModel):
    """Cryptographically verifiable, non-repudiable sovereign authorization artifact.
    
    Proves that a designated human authority personally authorized live capital
    deployment for a specific strategy on a specific broker account with verified
    Gate A evidence and unbroken audit lineage.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    human_go_record_id: str = Field(description="Deterministic identifier (e.g. GO_P13_20260904_001).")
    authorization_id: str = Field(description="LiveAuthorization identifier being approved.")
    authorization_digest: str = Field(description="Exact SHA-256 digest of the LiveAuthorization artifact.")
    gate_a_evidence_digest: str = Field(description="Exact SHA-256 digest of certified Gate A evidence pack.")
    live_account_identity_digest: str = Field(description="Exact SHA-256 digest of verified live account identity.")
    decision: Literal["GO"] = Field(default="GO", description="Explicit sovereign authorization decision.")
    approver_identity: str = Field(description="Descriptive metadata: Human authority name / role.")
    approver_public_key_id: str = Field(description="Key ID in Ed25519TrustStore (must have role HUMAN_AUDITOR).")
    approver_role: ApproverRole = Field(default=ApproverRole.HUMAN_AUDITOR, description="Required role: HUMAN_AUDITOR.")
    issued_at_utc: datetime = Field(description="Strict UTC timestamp of human decision.")
    expires_at_utc: datetime = Field(description="Mandatory expiration window for this GO decision.")
    previous_record_digest: str = Field(default="0" * 64, description="Tamper-evident audit chain linkage.")
    signature_algorithm: Literal["Ed25519"] = Field(default="Ed25519")
    signature: str = Field(description="Base64-encoded Ed25519 digital signature over canonical payload.")
    record_digest: str = Field(description="Canonical SHA-256 digest over canonical payload bytes.")

    def compute_canonical_payload_bytes(self) -> bytes:
        """Derive canonical bytes for Ed25519 signature and SHA-256 digest.
        
        CRITICAL B13 INVARIANT: previous_record_digest IS EXPLICITLY BOUND
        to prevent chain tampering or splicing attacks.
        """
        payload = {
            "human_go_record_id": self.human_go_record_id,
            "authorization_id": self.authorization_id,
            "authorization_digest": self.authorization_digest,
            "gate_a_evidence_digest": self.gate_a_evidence_digest,
            "live_account_identity_digest": self.live_account_identity_digest,
            "decision": self.decision,
            "approver_identity": self.approver_identity,
            "approver_public_key_id": self.approver_public_key_id,
            "approver_role": self.approver_role.value,
            "issued_at_utc": self.issued_at_utc.isoformat(),
            "expires_at_utc": self.expires_at_utc.isoformat(),
            "previous_record_digest": self.previous_record_digest,  # CRITICAL B13 BINDING
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
```

### Derivation & Verification Order:
$$\begin{array}{rcll}
\text{canonical\_payload} &=& \text{compute\_canonical\_payload\_bytes}(\text{fields with } \text{previous\_record\_digest}) \\
\text{record\_digest} &=& \text{SHA-256}(\text{canonical\_payload}) \\
\text{signature} &=& \text{Ed25519.sign}(\text{private\_key}, \text{canonical\_payload})
\end{array}$$

### Machine Verification Invariant in `activate_live_authorization()`:
$$\boxed{\begin{aligned}
&\text{SHA-256}(\text{canonical\_payload}) == \text{record\_digest} \quad \land \\
&\text{Ed25519.verify}(\text{public\_key}, \text{canonical\_payload}, \text{signature}) \quad \land \\
&\text{trust\_store.get\_key}(\text{key\_id}).\text{role} == \text{HUMAN\_AUDITOR} \quad \land \\
&\text{trust\_store.get\_key}(\text{key\_id}).\text{is\_active} == \text{True} \quad \land \\
&\text{auth.authorization\_digest} == \text{go\_record.authorization\_digest} \quad \land \\
&\text{gate\_a\_evidence\_digest} == \text{go\_record.gate\_a\_evidence\_digest} \quad \land \\
&\text{live\_account\_identity\_digest} == \text{go\_record.live\_account\_identity\_digest} \quad \land \\
&\text{go\_record.decision} == \text{"GO"} \quad \land \\
&\text{go\_record.expires\_at\_utc} \le \text{auth.expires\_at} \quad \land \\
&\text{now\_utc} < \text{go\_record.expires\_at\_utc} \quad \land \\
&\text{now\_utc} < \text{auth.expires\_at}
\end{aligned}}$$

If any single condition fails, activation raises `DataContractError` immediately.

---

## 4. Pre-Admission Bounding, Quote Contract & Slippage Semantics (B12, B17, B21, B22, B23)

### 4.1 Formal `MT5QuoteSnapshot` Contract (B23)
To eliminate stale-price and unvalidated market quote gaps, admission requires a validated `MT5QuoteSnapshot`:

```python
class MT5QuoteSnapshot(BaseModel):
    """Authoritative market price observation bound to transaction window."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(description="Normalized symbol (e.g. EURUSD).")
    bid: Decimal = Field(gt=Decimal("0"), description="Live broker bid price.")
    ask: Decimal = Field(gt=Decimal("0"), description="Live broker ask price.")
    point_size: Decimal = Field(gt=Decimal("0"), description="Symbol tick/point dimension.")
    contract_size: Decimal = Field(gt=Decimal("0"), description="Units per standard lot.")
    timestamp_utc: datetime = Field(description="Strict UTC timestamp of quote observation.")

    def assert_valid_and_fresh(self, max_quote_age_ms: int = 500) -> None:
        """Enforce strict quote freshness and sanity bounds."""
        if self.ask < self.bid:
            raise PreLiveRiskAdmissionError(
                f"INVALID_QUOTE: Inverted market spread ask ({self.ask}) < bid ({self.bid})"
            )
        now_utc = datetime.now(timezone.utc)
        age_ms = (now_utc - self.timestamp_utc).total_seconds() * 1000.0
        if age_ms > max_quote_age_ms:
            raise PreLiveRiskAdmissionError(
                f"STALE_QUOTE: Quote age {age_ms:.1f}ms exceeds maximum allowed {max_quote_age_ms}ms"
            )
```

### 4.2 Pre-Admission Bounding with `max_slippage_points` (B17 & B22)
In `construct_order_intent()`, ACASH prevents submitting orders whose conservative bounded executable risk exceeds authorized capital:

```python
# 1. Enforce explicit governance-defined assumed adverse price movement (ZERO DEFAULT)
if authorization.max_slippage_points is None or authorization.max_slippage_points <= 0:
    raise PreLiveRiskAdmissionError(
        "MANDATORY_PARAMETER_MISSING: authorization.max_slippage_points is undefined or non-positive. "
        "Operational defaults (e.g. stops_level_points or magic numbers) are strictly prohibited."
    )

# 2. Assert quote validity and freshness (B23)
quote.assert_valid_and_fresh(max_quote_age_ms=500)

# 3. Derive ACASH conservative worst-case executable price bound
slippage_buffer = Decimal(str(authorization.max_slippage_points)) * quote.point_size

if side == OrderSide.BUY:
    worst_case_price = quote.ask + slippage_buffer
else:
    worst_case_price = quote.bid - slippage_buffer

# 4. Compute bounded executable notional in account currency
order_units = quantity * quote.contract_size
bounded_executable_notional = order_units * worst_case_price

# 5. Machine-Enforce capital ceiling (Preventive Control - B21)
if bounded_executable_notional > authorization.max_notional:
    raise PreLiveRiskAdmissionError(
        f"Bounded executable notional {bounded_executable_notional:.2f} exceeds "
        f"authorized max_notional {authorization.max_notional:.2f} "
        f"(Reference Price: {quote.ask if side == OrderSide.BUY else quote.bid}, "
        f"Worst-Case Price: {worst_case_price}, Assumed Slippage Buffer: {slippage_buffer})"
    )
```

### 4.3 Post-Fill Detective Anomaly Trap (B21)
ACASH does not control venue order matching engines during extreme market gaps. If an adverse venue gap causes the actual fill price to result in $\text{actual\_notional} > \text{max\_notional}$:
- The 6-D reconciliation engine detects the discrepancy immediately upon fill confirmation.
- The adapter transitions to `BLOCKED` with `MT5DiscrepancyKind.NOTIONAL_BREACH_ANOMALY`.
- All further order submissions and dispatches are fail-closed.

---

## 5. Parameter Ownership Matrix (Zero Operational Defaults)

| Parameter Name | Schema Type | Proposed Constraint | Enforcement State | Authority / Owner |
| :--- | :--- | :--- | :--- | :--- |
| `authorization_id` | `str` | `AUTH_P13_LIVE_001` | **Cryptographically Bound** | Machine / Unique |
| `certificate_id` | `str` | Linked Phase 6/8.5 Certificate | **Cryptographically Bound** | Statistical Authority |
| `strategy_id` | `str` | Target Live Strategy ID | **Machine-Enforced** per order | Strategy Authority |
| `max_notional` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Machine-Enforced (Bounded)** (B12, B21) | **Human Auditor** |
| `max_slippage_points` | `int` | **[TBD — REQUIRED HUMAN INPUT]** | **Machine-Enforced (Assumed Risk Bound)** (B17, B22) | **Human Auditor / Policy** |
| `max_position_size` | `Decimal` | `Decimal("0.01")` (Micro-lot) | **Machine-Enforced Per-Order** (`admission.py:685`) | **Plan Rev3 §4.6** |
| `max_order_rate_per_minute` | `int` | `1` (Throttle limit) | **NOT MACHINE-ENFORCED** (B19 Phase 14 Debt) | **Governance Policy** |
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

## 6. Closing ACASH-Internal Dispatch Race & Detecting External Broker Mutation (B18 & B24)

### 6.1 Architectural Demarcation of Concurrency Boundaries (B24):
- **ACASH-Internal Concurrency:** Completely serialized and race-free. Only a single `ExecutionCoordinator` holding an exclusive dispatch mutex executes admission and dispatch.
- **External Venue Concurrency:** ACASH cannot prevent external actions on the broker account (e.g. manual MT5 GUI, EA, other terminal). External mutations are handled via **pre-dispatch assertion rejection** and **immediate post-dispatch reconciliation anomaly detection & containment**.

### 6.2 Exclusive Serial Dispatch Lock Lifecycle:

```
[DISPATCH INITIATION]
       │
       ▼
Acquire SerialDispatchLock (Exclusive Mutex)
       │
       ▼
Capture Unified Transactional Observation under lock:
  - Fresh Broker Reality Snapshot (< 100ms old)
  - Fresh MT5QuoteSnapshot (< 500ms old, positive & non-inverted spread)
       │
       ▼
Assert Strict Serial Invariants:
  - broker_snapshot.orders == 0
  - broker_snapshot.positions == 0 (for entry)
  - coordinator.in_flight_count == 0
       │  (If any != 0: Abort, release lock, raise PreLiveRiskAdmissionError)
       ▼
Order Admission Evaluation:
  - Authorization ACTIVE and not expired
  - HumanGORecord valid and not expired
  - bounded_executable_notional <= max_notional
       │  (If rejected: Abort, release lock, raise PreLiveRiskAdmissionError)
       ▼
Atomic Dispatch: adapter.order_send(deviation=max_slippage_points)
       │
       ▼
Immediate Synchronous Post-Dispatch Reconciliation:
  - Verify deal execution matches intent
  - Detect concurrent external broker mutation (UNTRACKED_BROKER_POSITION)
  - Detect NOTIONAL_BREACH_ANOMALY if fill breached max_notional
       │  (If anomaly detected: Transition to BLOCKED, raise CRITICAL alert)
       ▼
Release SerialDispatchLock
       │
       ▼
[DISPATCH COMPLETE]
```

---

## 7. Dynamic Execution Notional Semantics (B16)

Item M-2 validates the dynamic execution valuation framework:

1. **Account Currency:** `MT5AccountReality.currency == "USD"`.
2. **Monetary Unit:** Stated in 1.00 base units of account currency.
3. **Asset Valuation Basis:** EURUSD base currency is EUR, quote currency is USD.
4. **Dynamic Valuation Contract:**
   $$\text{Bounded Executable Notional} = \text{Volume (lots)} \times \text{Contract Size} \times \text{Worst-Case Price}$$
5. **Illustrative Reference (Example Only — Not a Static Invariant):**
   - At Ask = $1.16282$ with `max_slippage_points = 20` (0.00020 buffer), worst-case price is $1.16302$, representing $\approx 1,163.02\text{ USD}$ notional for 0.01 lot EURUSD.
   - At Ask = $1.18000$, the same 0.01 lot order represents $\approx 1,180.20\text{ USD}$ notional.
   - The human auditor determines `max_notional` based on organizational risk capital (e.g. $1,500.00\text{ USD}$); the machine dynamically validates every single order against the live Ask/Bid and slippage bound at admission.

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

## 9. Comprehensive Automated Test Matrix (25 Tests)

The implementation of Slice 2 will include the following 25 unit tests in `tests/unit/execution/test_gate_b_authorization_lifecycle.py`:

1. `test_draft_creation_with_valid_parameters`: Verifies M-1 schema bounds.
2. `test_currency_and_valuation_basis_contract`: Verifies M-2 multi-dimensional checks (USD, currency match).
3. `test_ed25519_quorum_signing_and_verification`: Verifies M-3 and M-4 quorum logic.
4. `test_authorization_digest_tamper_proofing`: Verifies M-5 tamper check on authorization payload.
5. `test_kill_switch_quorum_loading`: Verifies M-7 kill switch armed assertion.
6. `test_active_cannot_occur_before_human_go`: Verifies `APPROVED_PENDING_GO` strictly blocks order construction.
7. `test_human_go_record_cryptographic_verification`: Verifies valid Ed25519 signature over canonical payload passes.
8. `test_human_go_tamper_previous_digest_fails`: Verifies that tampering `previous_record_digest` invalidates Ed25519 signature (B13).
9. `test_human_go_tamper_record_digest_fails`: Verifies that tampering `record_digest` fails verification (B13).
10. `test_human_go_tamper_approver_key_id_fails`: Verifies that tampering `approver_public_key_id` fails verification (B13/B14).
11. `test_human_go_rejects_non_auditor_role`: Verifies rejection if key exists but registered role $\neq$ `HUMAN_AUDITOR` (B14).
12. `test_human_go_rejects_unregistered_or_revoked_key`: Verifies rejection if key is not in TrustStore or is revoked (B14).
13. `test_human_go_expiry_subordination_at_activation`: Verifies rejection if `go_record.expires_at_utc > auth.expires_at` (B15).
14. `test_admission_rejects_expired_authorization_or_go`: Verifies double-window expiry check at admission (`now >= min(auth, go)`) (B15).
15. `test_admission_rejects_stale_or_invalid_price_quote`: Verifies fail-closed when quote age $> 500\text{ ms}$, spread is inverted, or prices non-positive (B23).
16. `test_worst_case_notional_requires_explicit_max_slippage_points`: Verifies fail-closed when `max_slippage_points` is missing, None, or $\le 0$ (B17 zero-default check).
17. `test_worst_case_notional_nominal_pass_worst_case_fail`: Verifies B12/B17 boundary: nominal price $\le$ `max_notional`, but Ask + slippage $>$ `max_notional` fails closed.
18. `test_worst_case_notional_pass_within_boundary`: Verifies B12/B17: worst-case price $\le$ `max_notional` passes admission.
19. `test_reconciliation_detects_post_fill_notional_breach`: Verifies B12/B21: fill price $>$ worst-case causing notional breach triggers `NOTIONAL_BREACH_ANOMALY` & adapter block.
20. `test_strict_serial_mode_rejections`: Verifies discrete pre-dispatch snapshot checks (pending $\neq 0$, in-flight $\neq 0$, open $\neq 0$).
21. `test_strict_serial_toctou_prevention_under_concurrent_mutation`: Verifies that internal concurrent dispatch attempts fail closed under `SerialDispatchLock` and external mutations are trapped (B18/B24).
22. `test_required_approvals_cannot_default`: Verifies fail-closed when `required_approvals` is omitted.
23. `test_max_drawdown_pct_cannot_default`: Verifies fail-closed when `max_drawdown_pct` is omitted.
24. `test_read_only_preflight_cannot_escalate_trading`: Verifies preflight rejects trade-enabled session.
25. `test_revocation_event_halts_issuance`: Verifies that a `CertificateRevocationEvent` immediately revokes authorization, transitions to `REVOKED`, and halts order admission (B20).

---

## 10. Exact Stop Gate

```text
================================================================================
                    PHASE 13 SLICE 2 EXACT STOP GATE
================================================================================
Upon completion of Slice 2 Implementation:
1. LiveAuthorization will exist in APPROVED_PENDING_GO.
2. HumanGORecord non-repudiable verification machinery will be fully operational.
3. Worst-case executable notional machine gate with explicit slippage will be operational.
4. MT5QuoteSnapshot contract & freshness validation will be fully operational.
5. SerialDispatchLock with internal race prevention & external anomaly trap operational.
6. Live Capital remains strictly $0.00.
7. Zero broker orders will be sent.
8. Master trading password will NOT be loaded.
9. All execution will STOP completely.
10. Progression to Slice 3 (First Live Order) requires explicit, independent
    Human Sign-Off.
================================================================================
```
