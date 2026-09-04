# Phase 13 Slice 2: Gate B Mandatory Human Authorization Plan (Rev 9)
## Preflight & Implementation Plan (Plan Only — Zero Execution)

> **Document:** `docs/phase13/slice2_gate_b_plan.md`  
> **Status:** PROPOSED — PENDING HUMAN AUDITOR APPROVAL (REV 9)  
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

## User Review Required (Rev 9 Audit Adjustments)

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

### Key Refinements in Rev 9 (Addressing Audit Findings B35–B37):

1. **[BLOCKER B35 RESOLVED] Atomic Activation Transaction & Crash-Recovery Protocol:**
   - Addressed the state-consistency gap where a mid-transaction crash could produce `ACTIVE` without a committed ledger record, or an advanced ledger head without an `ACTIVE` authorization.
   - **Transaction Invariant:**
     $$\text{LiveAuthorization.status} == \text{ACTIVE} \iff \text{Committed HumanGORecord} \iff \text{Advanced Ledger Head}$$
   - Defined an **Atomic Activation Unit-of-Work Protocol**:
     $$\text{BEGIN TRANSACTION} \to \text{Verify Invariants} \to \text{Stage Write-Ahead Journal} \to \text{Atomic Commit} \to \text{Complete}$$
   - If an unexpected crash occurs mid-flight, the system either rolls back cleanly on recovery or completes the journaled commit idempotently. Order admission strictly checks both states simultaneously; partial commits fail closed.
2. **[BLOCKER B36 RESOLVED] Strict Boundary Tests for Reconciliation Timeout:**
   - Established explicit tests for all boundaries of $0 < \text{timeout\_ms} \le 30000$:
     - Negative and zero values ($0, -1$) $\to$ fail closed.
     - Exact upper bound ($30000\text{ ms}$) $\to$ valid / accepted.
     - Above upper bound ($30001\text{ ms}$) $\to$ fail closed.
3. **[BLOCKER B37 RESOLVED] Formal Parameter Taxonomy (Disclosing Fixed Constants vs Zero-Default Inputs):**
   - Renamed and restructured Section 5 into **"Parameter Taxonomy & Governance Ownership Matrix"**.
   - Explicitly categorized parameters into four distinct classes:
     1. *Cryptographic Protocol Constants* (e.g. `signature_algorithm = "Ed25519"`).
     2. *Fixed Slice-3 Safety Policy Invariants* (e.g. `max_position_size = Decimal("0.01")` — non-configurable safety constraint, not a default).
     3. *Mandatory Human Governance Inputs (Strict Zero Defaults)* (e.g. `max_notional`, `max_slippage_points`, `max_quote_age_ms`, `decision`, `approver_role`).
     4. *Technical Debt / Governance Baseline* (e.g. `max_order_rate_per_minute = 1` — not machine-enforced; Phase 14 debt).
4. **[TEST EXPANSION] Comprehensive 45-Test Matrix:**
   - Expanded the automated test matrix to **45 discrete unit tests** incorporating transaction atomicity, crash recovery, and upper/lower SLA boundary checks.

---

## 1. Executive Summary & Progression Topology

The objective of Phase 13 Slice 2 is to build the formal, dual-layer authorization harness (**Machine Gate + Governance Gate**) required to evaluate Gate B. 

Gate B is the sole authoritative mechanism in ACASH capable of transitioning `LiveAuthorization.status` to `ACTIVE`. Under Rev 9, `ACTIVE` is impossible to reach without an atomic, transactional state commit binding the verified `LiveAuthorization`, the Ed25519-signed `HumanGORecord`, and the unbroken authoritative ledger head.

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
         │ G-3: Human Issues Explicit Signed HumanGORecord (Ed25519, Zero Defaults)
         │ G-4: HumanGORecord Verified Against Authoritative Ledger Head
         │
         │ execute_atomic_activation_transaction(auth, go_record, trust_store, ledger)
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
> Transition to `ACTIVE` is guarded by `execute_atomic_activation_transaction()`, enforcing strict atomic consistency between the authorization state and the ledger head.

---

## 3. Cryptographic `HumanGORecord` & Atomic Activation Protocol (B11, B13, B14, B15, B30, B31, B32, B35)

### 3.1 Domain Schema Specification
```python
class HumanGORecord(BaseModel):
    """Cryptographically verifiable, non-repudiable sovereign authorization artifact.
    
    Proves that a designated human authority personally authorized live capital
    deployment for a specific strategy on a specific broker account with verified
    Gate A evidence, explicit zero-default governance inputs, and unbroken audit lineage.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    human_go_record_id: str = Field(description="Deterministic identifier (e.g. GO_P13_20260904_001).")
    authorization_id: str = Field(description="LiveAuthorization identifier being approved.")
    authorization_digest: str = Field(description="Exact SHA-256 digest of the LiveAuthorization artifact.")
    gate_a_evidence_digest: str = Field(description="Exact SHA-256 digest of certified Gate A evidence pack.")
    live_account_identity_digest: str = Field(description="Exact SHA-256 digest of verified live account identity.")
    decision: Literal["GO"] = Field(description="Explicit sovereign authorization decision (REQUIRED; NO DEFAULT).")
    approver_identity: str = Field(description="Descriptive metadata: Human authority name / role.")
    approver_public_key_id: str = Field(description="Key ID in Ed25519TrustStore.")
    approver_role: ApproverRole = Field(description="Explicit governance role (REQUIRED; NO DEFAULT; MUST BE HUMAN_AUDITOR).")
    issued_at_utc: datetime = Field(description="Strict UTC timestamp of human decision.")
    expires_at_utc: datetime = Field(description="Mandatory expiration window for this GO decision.")
    previous_record_digest: str = Field(description="Tamper-evident audit chain linkage (REQUIRED; NO DEFAULT).")
    signature_algorithm: Literal["Ed25519"] = Field(default="Ed25519", description="Fixed cryptographic protocol constant.")
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
            "previous_record_digest": self.previous_record_digest,  # CRITICAL B13 & B30 BINDING
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
```

### 3.2 Atomic Activation Transaction Boundary (B35)
To eliminate state-divergence between `LiveAuthorization.status` and `AuthoritativeGOLedger`:

```python
class ActivationTransactionManager:
    """Coordinates atomic two-phase transition of LiveAuthorization and AuthoritativeGOLedger."""

    @staticmethod
    def execute_atomic_activation(
        auth: LiveAuthorization,
        go_record: HumanGORecord,
        trust_store: Ed25519TrustStore,
        ledger: AuthoritativeGOLedger,
    ) -> LiveAuthorization:
        # Phase 1: Pre-Commit Validation (Fail-Closed)
        ActivationValidator.assert_activation_preconditions(auth, go_record, trust_store, ledger)

        # Phase 2: Atomic Unit-of-Work Commit
        # Transaction Invariant: ACTIVE <=> Committed Record <=> Advanced Ledger Head
        try:
            with ledger.begin_transaction() as tx:
                # 1. Append record to persistent ledger
                tx.append_go_record(go_record)
                # 2. Advance authoritative ledger head
                tx.set_head_digest(go_record.record_digest)
                # 3. Transition authorization status to ACTIVE
                activated_auth = auth.model_copy(update={
                    "status": LiveAuthorizationStatus.ACTIVE,
                    "activated_at": datetime.now(timezone.utc),
                    "active_go_record_digest": go_record.record_digest,
                })
                tx.persist_activated_authorization(activated_auth)
                tx.commit()
            return activated_auth
        except Exception as exc:
            # Automatic rollback on any failure or crash
            ledger.rollback_pending_transaction()
            raise DataContractError(f"ACTIVATION_TRANSACTION_FAILED: {exc}") from exc
```

### 3.3 Admission Double-Verification Invariant (B35):
In `admission.py:construct_order_intent()`, the engine enforces:
$$\boxed{\begin{aligned}
&\text{auth.status} == \text{ACTIVE} \quad \land \\
&\text{ledger.contains}(\text{auth.active\_go\_record\_digest}) \quad \land \\
&\text{ledger.current\_head\_digest} == \text{auth.active\_go\_record\_digest}
\end{aligned}}$$
If any single condition diverges (indicating a partial commit or ledger desynchronization), admission strictly fails closed.

---

## 4. Pre-Admission Bounding, Quote Contract & Slippage Semantics (B12, B17, B21, B22, B23, B25, B26, B27, B36)

### 4.1 Formal `MT5QuoteSnapshot` Contract (B23, B25, B26)
To eliminate stale-price, non-UTC, and future-timestamped market quotes, admission requires a validated `MT5QuoteSnapshot`:

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

    def assert_valid_and_fresh(self, *, max_quote_age_ms: int) -> None:
        """Enforce strict quote freshness, UTC provenance, and sanity bounds.
        
        CRITICAL B25 & B26 INVARIANTS:
        - max_quote_age_ms is a required keyword argument (ZERO operational default).
        - timestamp_utc MUST be timezone-aware and set to UTC (offset == 0).
        - 0 <= quote_age_ms <= max_quote_age_ms (strictly rejects future timestamps).
        - ask >= bid > 0 (strictly rejects non-positive or inverted spread).
        """
        # 1. B25: Enforce positive freshness threshold
        if max_quote_age_ms is None or max_quote_age_ms <= 0:
            raise PreLiveRiskAdmissionError(
                "MANDATORY_PARAMETER_MISSING: max_quote_age_ms must be a positive int"
            )

        # 2. B26: Enforce timezone-aware UTC provenance
        if self.timestamp_utc.tzinfo is None or self.timestamp_utc.utcoffset() != timedelta(0):
            raise PreLiveRiskAdmissionError(
                f"INVALID_TIMESTAMP_PROVENANCE: Quote timestamp {self.timestamp_utc} must be explicit UTC-aware"
            )

        # 3. B26: Enforce non-negative and fresh quote age (rejects future timestamps)
        now_utc = datetime.now(timezone.utc)
        age_ms = (now_utc - self.timestamp_utc).total_seconds() * 1000.0
        if age_ms < 0:
            raise PreLiveRiskAdmissionError(
                f"FUTURE_TIMESTAMP_ANOMALY: Quote timestamp {self.timestamp_utc} is in the future "
                f"relative to local clock {now_utc} (age: {age_ms:.1f}ms)"
            )
        if age_ms > max_quote_age_ms:
            raise PreLiveRiskAdmissionError(
                f"STALE_QUOTE: Quote age {age_ms:.1f}ms exceeds maximum allowed {max_quote_age_ms}ms"
            )

        # 4. Spread sanity
        if self.ask < self.bid:
            raise PreLiveRiskAdmissionError(
                f"INVALID_QUOTE: Inverted market spread ask ({self.ask}) < bid ({self.bid})"
            )
```

### 4.2 Pre-Admission Bounding with `max_slippage_points` (B17, B22, B27)
In `construct_order_intent()`, ACASH prevents submitting orders whose conservative bounded executable risk exceeds authorized capital:

```python
# 1. Enforce explicit governance parameters (ZERO DEFAULTS)
if authorization.max_slippage_points is None or authorization.max_slippage_points <= 0:
    raise PreLiveRiskAdmissionError(
        "MANDATORY_PARAMETER_MISSING: authorization.max_slippage_points is undefined or non-positive."
    )
if authorization.max_quote_age_ms is None or authorization.max_quote_age_ms <= 0:
    raise PreLiveRiskAdmissionError(
        "MANDATORY_PARAMETER_MISSING: authorization.max_quote_age_ms is undefined or non-positive."
    )

# 2. Assert quote validity and freshness (B23, B25, B26)
quote.assert_valid_and_fresh(max_quote_age_ms=authorization.max_quote_age_ms)

# 3. Derive ACASH conservative worst-case executable price bound
slippage_buffer = Decimal(str(authorization.max_slippage_points)) * quote.point_size

if side == OrderSide.BUY:
    worst_case_price = quote.ask + slippage_buffer
else:
    worst_case_price = quote.bid - slippage_buffer

# 4. CRITICAL B27 INVARIANT: Enforce strictly positive worst-case price
if worst_case_price <= Decimal("0"):
    raise PreLiveRiskAdmissionError(
        f"INVALID_WORST_CASE_EXECUTION_PRICE: Computed worst-case price {worst_case_price} "
        f"is non-positive (Reference: {quote.ask if side == OrderSide.BUY else quote.bid}, "
        f"Buffer: {slippage_buffer})"
    )

# 5. Compute bounded executable notional in account currency
order_units = quantity * quote.contract_size
bounded_executable_notional = order_units * worst_case_price

# 6. Machine-Enforce capital ceiling (Preventive Control - B21)
if bounded_executable_notional > authorization.max_notional:
    raise PreLiveRiskAdmissionError(
        f"Bounded executable notional {bounded_executable_notional:.2f} exceeds "
        f"authorized max_notional {authorization.max_notional:.2f} "
        f"(Reference Price: {quote.ask if side == OrderSide.BUY else quote.bid}, "
        f"Worst-Case Price: {worst_case_price}, Assumed Slippage Buffer: {slippage_buffer})"
    )
```

### 4.3 Post-Fill Detective Anomaly Trap & SLA Timeout (B21, B29, B33, B34, B36)
ACASH does not control venue order matching engines during extreme market gaps. If an adverse venue gap causes the actual fill price to result in $\text{actual\_notional} > \text{max\_notional}$:
- The 6-D reconciliation engine detects the discrepancy immediately upon fill confirmation.
- The adapter transitions to `BLOCKED` with `MT5DiscrepancyKind.NOTIONAL_BREACH_ANOMALY`.
- **SLA Timeout (B29, B33, B36):** Strictly bounded by:
  $$0 < \text{post\_dispatch\_reconciliation\_timeout\_ms} \le 30000\text{ ms}$$
  If reconciliation cannot confirm terminal broker deal/position state within this timeout:
  - The state is classified as `UNKNOWN` (which $\ne$ `FAILED`).
  - **Strict No-Retry Invariant (B34):** Automated retries are strictly prohibited to prevent duplicate fills.
  - The adapter transitions to `BLOCKED` with `MT5DiscrepancyKind.INDETERMINATE_EXECUTION_TIMEOUT`. All subsequent dispatches are locked pending manual forensic audit.

---

## 5. Parameter Taxonomy & Governance Ownership Matrix (B37)

To eliminate ambiguity between configurable runtime inputs and immutable safety constraints, parameters are strictly categorized:

| Parameter Name | Schema Type | Value / Constraint | Classification | Authority / Owner |
| :--- | :--- | :--- | :--- | :--- |
| `signature_algorithm` | `Literal["Ed25519"]` | `"Ed25519"` | **Cryptographic Protocol Constant** | Protocol Spec |
| `max_position_size` | `Decimal` | `Decimal("0.01")` (Micro-lot) | **Slice-3 Fixed Policy Invariant** | Plan Rev3 §4.6 |
| `max_order_rate_per_minute` | `int` | `1` (Throttle limit) | **Technical Debt (Phase 14)** (Not Enforced) | Governance Policy |
| `authorization_id` | `str` | Unique ID (e.g. `AUTH_P13_LIVE_001`) | **Cryptographically Bound** | Machine Clock / Ledger |
| `certificate_id` | `str` | Linked Phase 6/8.5 Certificate | **Cryptographically Bound** | Statistical Authority |
| `strategy_id` | `str` | Target Live Strategy ID | **Machine-Enforced Per-Order** | Strategy Authority |
| `max_notional` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Mandatory Human Input (Zero Default)** | **Human Auditor** |
| `max_slippage_points` | `int` | **[TBD — REQUIRED HUMAN INPUT]** | **Mandatory Human Input (Zero Default)** | **Human Auditor / Policy** |
| `max_quote_age_ms` | `int` | **[TBD — REQUIRED HUMAN INPUT]** | **Mandatory Human Input (Zero Default)** | **Human Auditor / Policy** |
| `post_dispatch_reconciliation_timeout_ms` | `int` | **[TBD — REQUIRED GOVERNANCE INPUT]** | **Mandatory Human Input ($0 < \text{ms} \le 30000$)** | **Execution SLA Policy** |
| `max_daily_loss_notional` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Mandatory Human Input (Zero Default)** | **Human Auditor** |
| `max_drawdown_pct` | `Decimal` | **[TBD — REQUIRED HUMAN INPUT]** | **Mandatory Human Input (Zero Default)** | **Human Auditor** |
| `allowed_venues` | `Tuple[str]` | `("LIVE_MT5",)` | **Mandatory Human Input (Zero Default)** | **Human Auditor** |
| `allowed_symbols` | `Tuple[str]` | `("EURUSD",)` | **Mandatory Human Input (Zero Default)** | **Human Auditor** |
| `required_approvals` | `int` | **[TBD — REQUIRED GOVERNANCE INPUT]** | **Mandatory Governance Input ($\ge 1$)** | **Governance Policy** |
| `decision` | `Literal["GO"]` | `"GO"` | **Mandatory Human Input (Zero Default)** | **Human Auditor** |
| `approver_role` | `ApproverRole` | `ApproverRole.HUMAN_AUDITOR` | **Mandatory Human Input (Zero Default)** | **Human Auditor** |
| `authorized_at` | `datetime` | UTC timestamp of issuance | **Cryptographically Bound** | Machine Clock |
| `expires_at` | `datetime` | Time-boxed window (e.g. +24h) | **Mandatory Human Input (Zero Default)** | **Human Auditor** |
| `currency` | `str` | `MT5AccountReality.currency` | **Operational Convention** (Verified at M-2) | **Human Auditor** |

---

## 6. Serialized Execution Coordinator Critical Section & Anomaly Detection (B18, B24, B28, B29, B34)

### 6.1 Honest Concurrency Specification (B28):
ACASH order dispatch is serialized through a single `ExecutionCoordinator` critical section.
- **Runtime Property:** Exactly $\le 1$ active dispatcher inside the runtime process.
- **Fail-Closed Mutex:** If lock acquisition fails or times out, dispatch aborts immediately with `PreLiveRiskAdmissionError("DISPATCH_LOCK_ACQUISITION_FAILED")`.
- **External Venue Concurrency (B24 & B34):** ACASH cannot prevent external actions on the broker account. External mutations are handled via **pre-dispatch assertion rejection** and **post-dispatch reconciliation anomaly detection & containment**.

### 6.2 Exclusive Serial Dispatch Lock Lifecycle:

```
[DISPATCH INITIATION]
       │
       ▼
Acquire SerialDispatchLock (Exclusive Mutex with Timeout)
       │  (If acquisition fails: Fail closed, raise PreLiveRiskAdmissionError)
       ▼
Coordinated observation under ACASH serial lock:
  - Fresh Broker Reality Snapshot (< 100ms old)
  - Fresh MT5QuoteSnapshot (UTC-aware, age <= max_quote_age_ms, ask >= bid > 0)
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
  - worst_case_price > 0 (B27)
  - bounded_executable_notional <= max_notional
       │  (If rejected: Abort, release lock, raise PreLiveRiskAdmissionError)
       ▼
Atomic Dispatch: adapter.order_send(deviation=max_slippage_points)
       │
       ▼
Synchronous Post-Dispatch Reconciliation (with post_dispatch_reconciliation_timeout_ms SLA):
  - Verify deal execution matches intent
  - Detect concurrent external broker mutation (UNTRACKED_BROKER_POSITION)
  - Detect NOTIONAL_BREACH_ANOMALY if fill breached max_notional
  - If reconciliation SLA times out -> Transition to BLOCKED (INDETERMINATE_EXECUTION_TIMEOUT)
  - STRICTLY NO AUTOMATED RETRY of order_send (B34)
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

## 9. Comprehensive Automated Test Matrix (45 Tests)

The implementation of Slice 2 will include the following 45 unit tests in `tests/unit/execution/test_gate_b_authorization_lifecycle.py`:

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
15. `test_admission_rejects_stale_or_invalid_price_quote`: Verifies fail-closed when quote age exceeds `max_quote_age_ms`, spread is inverted, or prices non-positive (B23).
16. `test_quote_snapshot_rejects_naive_or_non_utc_timestamp`: Verifies fail-closed when quote timestamp is naive or non-UTC aware (B26).
17. `test_quote_snapshot_rejects_future_timestamp`: Verifies fail-closed when quote timestamp is in the future ($\text{age\_ms} < 0$) (B26).
18. `test_worst_case_notional_requires_explicit_max_slippage_points`: Verifies fail-closed when `max_slippage_points` is missing, None, or $\le 0$ (B17 zero-default check).
19. `test_worst_case_notional_requires_explicit_max_quote_age_ms`: Verifies fail-closed when `max_quote_age_ms` is missing, None, or $\le 0$ (B25 zero-default check).
20. `test_worst_case_price_rejects_zero_or_negative_price`: Verifies fail-closed when `worst_case_price <= 0` for both BUY and SELL (B27 boundary check).
21. `test_worst_case_notional_nominal_pass_worst_case_fail`: Verifies B12/B17 boundary: nominal price $\le$ `max_notional`, but Ask + slippage $>$ `max_notional` fails closed.
22. `test_worst_case_notional_pass_within_boundary`: Verifies B12/B17: worst-case price $\le$ `max_notional` passes admission.
23. `test_reconciliation_detects_post_fill_notional_breach`: Verifies B12/B21: fill price $>$ worst-case causing notional breach triggers `NOTIONAL_BREACH_ANOMALY` & adapter block.
24. `test_post_dispatch_reconciliation_timeout_blocks_adapter`: Verifies B29 SLA: reconciliation exceeding timeout transitions adapter to `BLOCKED` with `INDETERMINATE_EXECUTION_TIMEOUT`.
25. `test_strict_serial_mode_rejections`: Verifies discrete pre-dispatch snapshot checks (pending $\neq 0$, in-flight $\neq 0$, open $\neq 0$).
26. `test_strict_serial_lock_failure_and_external_mutation_containment`: Verifies dispatch lock acquisition failure fails closed, and external broker mutations are detected and blocked (B18, B24, B28).
27. `test_required_approvals_cannot_default`: Verifies fail-closed when `required_approvals` is omitted.
28. `test_max_drawdown_pct_cannot_default`: Verifies fail-closed when `max_drawdown_pct` is omitted.
29. `test_read_only_preflight_cannot_escalate_trading`: Verifies preflight rejects trade-enabled session.
30. `test_revocation_event_halts_issuance`: Verifies that a `CertificateRevocationEvent` immediately revokes authorization, transitions to `REVOKED`, and halts order admission (B20).
31. `test_human_go_rejects_chain_fork`: Verifies activation fails if `previous_record_digest` does not match authoritative ledger head (B30).
32. `test_human_go_rejects_stale_previous_digest`: Verifies activation fails if submitting an older previous digest against an updated ledger head (B30).
33. `test_first_human_go_requires_genesis_digest`: Verifies initial record requires exact genesis digest `"0"*64` (B30).
34. `test_go_ledger_head_updates_atomically`: Verifies that upon successful activation, ledger head advances to new record digest atomically (B30).
35. `test_human_go_requires_explicit_decision`: Verifies that omitting `decision` in input fails schema validation closed (B31).
36. `test_human_go_requires_explicit_approver_role`: Verifies that omitting `approver_role` in input fails schema validation closed (B32).
37. `test_human_go_rejects_record_role_mismatch`: Verifies activation fails if `go_record.approver_role != trust_store[key_id].role` (B32).
38. `test_reconciliation_timeout_requires_positive_value`: Verifies fail-closed when `post_dispatch_reconciliation_timeout_ms <= 0` or missing (B33/B36).
39. `test_reconciliation_timeout_rejects_above_maximum`: Verifies fail-closed when `post_dispatch_reconciliation_timeout_ms = 30001` (B36).
40. `test_reconciliation_timeout_accepts_maximum_boundary`: Verifies acceptance of exact maximum `post_dispatch_reconciliation_timeout_ms = 30000` (B36).
41. `test_reconciliation_timeout_does_not_retry_order`: Verifies that upon timeout, adapter enters `BLOCKED` with `UNKNOWN` state and strictly disallows automated retry of `order_send` (B34).
42. `test_activation_atomicity_rolls_back_status_and_ledger`: Verifies that if activation fails mid-flight, neither `ACTIVE` status nor ledger head advances (B35).
43. `test_activation_recovery_after_crash`: Verifies that restart/recovery detects partial write journal and restores consistent pre-activation state (B35).
44. `test_no_active_without_ledger_record`: Verifies that admission rejects orders if authorization is marked `ACTIVE` but record is missing from ledger (B35).
45. `test_no_ledger_head_advance_without_active`: Verifies that admission rejects orders if ledger head advanced but authorization status is not `ACTIVE` (B35).

---

## 10. Exact Stop Gate

```text
================================================================================
                    PHASE 13 SLICE 2 EXACT STOP GATE
================================================================================
Upon completion of Slice 2 Implementation:
1. LiveAuthorization will exist in APPROVED_PENDING_GO.
2. HumanGORecord non-repudiable verification machinery will be fully operational.
3. Authoritative ledger head continuity verification will be fully operational.
4. Atomic Activation Transaction Manager will guarantee state-ledger consistency.
5. Worst-case executable notional machine gate with explicit slippage will be operational.
6. MT5QuoteSnapshot contract with UTC and non-negative age validation operational.
7. Serial critical section with timeout and post-reconciliation SLA operational.
8. Live Capital remains strictly $0.00.
9. Zero broker orders will be sent.
10. Master trading password will NOT be loaded.
11. All execution will STOP completely.
12. Progression to Slice 3 (First Live Order) requires explicit, independent
    Human Sign-Off.
================================================================================
```
