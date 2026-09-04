# Phase 13 Slice 2: Gate B Mandatory Human Authorization Plan (Rev 19)
## Preflight & Implementation Plan (Plan Only — Zero Execution)

> **Document:** `docs/phase13/slice2_gate_b_plan.md`  
> **Status:** PROPOSED — PENDING HUMAN AUDITOR APPROVAL (REV 19)  
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

## User Review Required (Rev 19 Audit Adjustments)

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

### Key Refinements in Rev 19 (Addressing Final Audit Findings B88–B91):

1. **[BLOCKER B88 RESOLVED] Durable Previous-Pointer Binding & CAS Failure Recovery:**
   - Formalized invariant $\mathbf{PREVIOUS\_POINTER\_BINDING}(tx)$:
     $$\mathbf{PREVIOUS\_POINTER\_BINDING}(tx) \implies \text{previous\_committed\_pointer is durably recorded, cryptographically bound, and authenticated}$$
   - Established `DurablePointerTransitionRecord` schema (`pointer_version`, `previous_tx_id`, `new_tx_id`, `commit_intent_digest`, `previous_pointer_digest`).
   - Defined strict CAS Failure Protocol: If persistent CAS `COMMITTING` $\to$ `COMMITTED` fails after pointer switch, the engine **NEVER silently rolls back the pointer**. Rollback to `previous_tx_id` is permitted ONLY if the transition record is durably authenticated against disk state; otherwise, the entire storage engine transitions immediately to **`QUARANTINE_LOCKED`**.
2. **[BLOCKER B89 RESOLVED] Concrete Storage Backend Durability Contract:**
   - Defined platform-specific storage backend specifications for Windows (NTFS/ReFS) and Linux (ext4/XFS):
     - Windows semantics: `FlushFileBuffers` via Python `os.fsync`; atomic pointer switch via `os.replace` (`MoveFileExW(..., MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)`).
     - Linux semantics: `fsync(fd)` / `fdatasync(fd)` on file descriptors; parent directory `fsync(dir_fd)` following promotion and rename; atomic pointer switch via POSIX `rename(2)`.
     - Canonical Definition of $\mathbf{DURABLE}(barrier)$: Synchronous non-volatile hardware barrier confirmed by the underlying operating system system call before returning execution to application space.
3. **[B90 RESOLVED] Formal Rationale for Conservative Quarantine Boundaries (Crash-03 & Crash-04):**
   - Formalized fail-closed rationale: A transaction that reaches snapshot directory promotion or directory barrier (`fsync_3`) but has NOT durably established the committed snapshot pointer needed for recovery **MUST NOT be auto-aborted**.
   - Because snapshot files are physically present on disk, automatic rollback risks destroying valid intended mutations or creating observer ambiguity. ACASH enforces an **intentional conservative quarantine policy** to preserve immutable forensic evidence whenever transaction provenance is incomplete.
4. **[B91 RESOLVED] Accurate Scope of Crash / Fault-Injection Testing:**
   - Clarified test suite terminology to **Fault-Injection Crash/Restart Tests**.
   - Explicitly codified Evidence Scope: *Validates process-crash, abnormal termination, and controlled restart semantics; does not constitute physical hardware power-loss or storage controller failure certification.*
5. **[RECOVERY HIERARCHY] Unidirectional Recovery Input Hierarchy (Zero Circularity):**
   - Established strict recovery precedence eliminating circular dependency:
     $$\text{1. tx\_state} \to \text{2. pointer (transition record)} \to \text{3. snapshots/<tx\_id>/} \to \text{4. manifest} \to \text{5. journal}$$
   - Journal is strictly reconstructible operational metadata, NEVER an independent authority over storage state.
6. **[TEST EXPANSION] Comprehensive 111-Assertion Verification Harness:**
   - Unit Test Matrix expanded to **100 Discrete Automated Unit Tests** (Tests 1–98, including 87a, 87b, 87c).
   - Crash Integration Matrix expanded to **11 Fault-Injection Crash Scenarios** (Crash-01 through Crash-11).

---

## 1. Executive Summary & Progression Topology

The objective of Phase 13 Slice 2 is to build the formal, dual-layer authorization harness (**Machine Gate + Governance Gate**) required to evaluate Gate B. 

`ACTIVE is reachable only through the authoritative activation transaction path.` Under Rev 19, `ACTIVE` is impossible to reach without an atomic Compare-And-Swap commit binding the verified `LiveAuthorization`, the Ed25519-signed `HumanGORecord`, and the unbroken authoritative ledger head under a unique, durably enforced `activation_transaction_id`:
$$\textbf{ACTIVE Authorization} \iff \textbf{Bound HumanGORecord Committed} \land \textbf{Ledger Current Head == Record Digest}$$

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
         │   ├── Acquire Exclusive Ledger Mutex
         │   ├── Generate & Durably Reserve activation_transaction_id (B54)
         │   ├── Assert AUTH_CHAIN_VALID(tx) Derivation Invariant (B79)
         │   ├── CAS Check: expected_head == tx.current_head_digest (B38)
         │   ├── Stage WAL Journal: PREPARED -> COMMITTING with fsync (B50, B55)
         │   ├── Phase 1: Stage Mutation Data (Record, Head, Auth) -> fsync_1 (B59, B65)
         │   ├── Phase 2: Write Commit Manifest Block -> fsync_2 (B60, B73)
         │   ├── Phase 3: Promote to Snapshot Dir & Mark Read-Only -> fsync_3 (B75, B83)
         │   ├── Phase 4: Pre-CAS Re-verification under Exclusive Lock (B75, B86)
         │   ├── Phase 5: Two-Phase Recoverable Commit (B82, B88):
         │   │   ├── Step 5a: Write Durable Pointer Transition Record & Flush (B88)
         │   │   ├── Step 5b: Atomic Pointer Switch (committed_pointer -> snapshots/<tx_id>)
         │   │   └── Step 5c: Persistent CAS State Transition (COMMITTING -> COMMITTED)
         │   └── Finalize Journal: COMMITTED with fsync (B44, B56, B61)
         ▼
        ACTIVE          ◄── [Machine-enables admission.py per-order checks]
         │
         ├─ Suspended (Kill switch trip / anomaly)
         ├─ Expired (now_utc >= min(auth.expires_at, go_record.expires_at_utc))
         ├─ Revoked (CertificateRevocationEvent)
         └─ Quarantined (QUARANTINE_LOCKED on post-commit ambiguity - B49, B58, B62)
```

> [!IMPORTANT]
> **State Machine Invariant (B57):**  
> In `APPROVED_PENDING_GO`, `admission.py:construct_order_intent()` strictly raises `PreLiveRiskAdmissionError("AUTHORIZATION_PENDING_HUMAN_GO")`.  
> In `QUARANTINE_LOCKED`, order intent construction strictly fails closed with `PreLiveRiskAdmissionError("SYSTEM_QUARANTINED_PENDING_FORENSIC_AUDIT")`.  
> `ACTIVE` cannot be instantiated or set through any constructor, updater, or mock outside `execute_atomic_activation_transaction()`.

---

## 3. Cryptographic Schema, Staging Isolation, Atomic Publication & Terminal CAS Contracts (B11, B13, B14, B15, B30, B31, B32, B35, B38, B39, B40, B43, B44, B48, B49, B50, B51, B52, B53, B54, B55, B56, B57, B58, B59, B60, B61, B62, B64, B65, B66, B67, B68, B69, B70, B71, B72, B73, B74, B75, B76, B77, B78, B79, B80, B81, B82, B83, B84, B85, B86, B87, B88, B89, B90, B91)

### 3.1 Domain Schema Specification & Identity Scope (B51, B73, B77)
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
    approved_authorization_digest: str = Field(description="Exact SHA-256 digest of the approved draft LiveAuthorization artifact.")
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
        """Derive canonical bytes for Ed25519 signature and SHA-256 digest."""
        payload = {
            "human_go_record_id": self.human_go_record_id,
            "authorization_id": self.authorization_id,
            "approved_authorization_digest": self.approved_authorization_digest,
            "gate_a_evidence_digest": self.gate_a_evidence_digest,
            "live_account_identity_digest": self.live_account_identity_digest,
            "decision": self.decision,
            "approver_identity": self.approver_identity,
            "approver_public_key_id": self.approver_public_key_id,
            "approver_role": self.approver_role.value,
            "issued_at_utc": self.issued_at_utc.isoformat(),
            "expires_at_utc": self.expires_at_utc.isoformat(),
            "previous_record_digest": self.previous_record_digest,
            "signature_algorithm": self.signature_algorithm,
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
```

### 3.2 LiveAuthorization Schema & Derivation Lineage Contract (B73, B77, B79)
```python
class LiveAuthorization(BaseModel):
    """Authoritative runtime strategy authorization artifact."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    authorization_id: str = Field(description="Deterministic strategy authorization ID.")
    status: LiveAuthorizationStatus = Field(default=LiveAuthorizationStatus.DRAFT)
    approved_authorization_digest: str = Field(description="Canonical SHA-256 of draft artifact when approved by machine quorum.")
    source_approved_digest: Optional[str] = Field(default=None, description="Cryptographic derivation link to human-approved draft digest (B79).")
    activated_authorization_digest: Optional[str] = Field(default=None, description="SHA-256 of active artifact post-activation (B73, B77).")
    active_go_record_digest: Optional[str] = Field(default=None, description="Bound HumanGORecord digest once active.")
    activation_transaction_id: Optional[UUID] = Field(default=None, description="Storage transaction ID under which activation committed.")
    strategy_id: str = Field(description="Bound strategy identity.")
    symbol: str = Field(description="Trading symbol.")
    account_id: str = Field(description="Target live broker account ID.")
    max_notional_usd: Decimal = Field(gt=Decimal("0"))
    max_drawdown_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("100"))
    max_slippage_points: int = Field(gt=0, description="Mandatory positive slippage allowance points.")
    max_quote_age_ms: int = Field(gt=0, description="Mandatory positive quote age SLA.")
    required_approvals: int = Field(gt=0)
    created_at: datetime = Field(description="UTC timestamp.")
    expires_at: datetime = Field(description="Mandatory UTC expiry.")

    @property
    def authorization_digest(self) -> str:
        """Backward-compatibility property alias pointing to canonical approved_authorization_digest."""
        return self.approved_authorization_digest
```

### 3.3 Durable Transaction State Machine & Terminal-State CAS Invariant (B64, B67)
```python
class DurableTransactionState(str, Enum):
    """Storage-layer transactional lifecycle states."""
    PREPARED = "PREPARED"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"
    QUARANTINED = "QUARANTINED"
```

### 3.4 Authoritative Abort Record Block Schema & Snapshot Binding Contract (B70, B74, B76, B77)
```python
class AuthoritativeAbortRecordBlock(BaseModel):
    """Cryptographically verifiable on-disk record of an authoritative transaction abort (B70, B76, B77)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    activation_transaction_id: UUID = Field(description="Unique transactional identity.")
    pre_transaction_head_digest: str = Field(description="Authoritative ledger head digest prior to transaction.")
    authorization_id: str = Field(description="LiveAuthorization identifier bound to this transaction.")
    approved_authorization_digest: str = Field(description="Exact canonical SHA-256 of the approved draft LiveAuthorization artifact.")
    expected_previous_state: DurableTransactionState = Field(description="State from which abort occurred (COMMITTING).")
    terminal_state: Literal[DurableTransactionState.ABORTED] = Field(default=DurableTransactionState.ABORTED)
    abort_reason_code: str = Field(description="Structured machine error code triggering abort.")
    abort_timestamp_utc: datetime = Field(description="Strict UTC timestamp of abort publication.")
    abort_record_digest: str = Field(description="SHA-256 canonical digest over abort record payload.")

    def compute_digest(self) -> str:
        payload = {
            "activation_transaction_id": str(self.activation_transaction_id),
            "pre_transaction_head_digest": self.pre_transaction_head_digest,
            "authorization_id": self.authorization_id,
            "approved_authorization_digest": self.approved_authorization_digest,
            "expected_previous_state": self.expected_previous_state.value,
            "terminal_state": self.terminal_state.value,
            "abort_reason_code": self.abort_reason_code,
            "abort_timestamp_utc": self.abort_timestamp_utc.isoformat(),
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()
```

### 3.5 Authoritative Commit Record Block Schema & Disambiguated Manifest (B60, B73, B77, B79)
```python
class AuthoritativeCommitRecordBlock(BaseModel):
    """Cryptographic manifest proving durable persistence of all transaction mutations (B60, B73, B77, B79)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    activation_transaction_id: UUID = Field(description="Unique transactional identity.")
    commit_timestamp_utc: datetime = Field(description="Strict UTC timestamp of durable commit.")
    ledger_record_digest: str = Field(description="SHA-256 of persisted HumanGORecord.")
    advanced_head_digest: str = Field(description="SHA-256 of new ledger head.")
    approved_authorization_digest: str = Field(description="Canonical SHA-256 of the approved draft LiveAuthorization.")
    activated_authorization_digest: str = Field(description="Canonical SHA-256 of the activated LiveAuthorization artifact.")
    mutation_manifest_digest: str = Field(description="SHA-256 over canonical manifest of above digests.")

    def compute_manifest_digest(self) -> str:
        payload = {
            "activation_transaction_id": str(self.activation_transaction_id),
            "commit_timestamp_utc": self.commit_timestamp_utc.isoformat(),
            "ledger_record_digest": self.ledger_record_digest,
            "advanced_head_digest": self.advanced_head_digest,
            "approved_authorization_digest": self.approved_authorization_digest,
            "activated_authorization_digest": self.activated_authorization_digest,
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()
```

### 3.6 Transaction-Addressed Versioned Snapshots & Storage Backend Specification (B65, B75, B83, B86, B88, B89)

```text
storage/
├── staging/
│   └── <tx_id>/                  <-- [Phase 1: Write & fsync_1]
├── snapshots/
│   └── <tx_id>/                  <-- [Phase 3: Atomic directory rename + READ-ONLY ACLs + fsync_3]
│       ├── record.json
│       ├── head.json
│       ├── authorization.json
│       └── commit_record_block.json
├── pointer/
│   ├── committed_pointer         <-- [Phase 5b: Atomic pointer switch pointing to snapshots/<tx_id>]
│   └── transition.json           <-- [Phase 5a: Durable previous-pointer binding record (B88)]
├── aborts/
│   └── <tx_id>.json              <-- [Authoritative abort records]
└── tx_state/
    └── <tx_id>.state             <-- [Persistent CAS state file]
```

**CRITICAL B89 SPECIFICATION: Concrete Storage Backend Durability Contract**
The ACASH storage engine formally specifies and binds its durability guarantees to the following platform backends:

1. **Target Platforms & Filesystems:**
   - **Primary Target (Windows):** Windows 10/11 / Windows Server on **NTFS / ReFS**.
   - **Secondary Target (Linux):** Linux Kernel $\ge 5.15$ on **ext4 / XFS** (POSIX compliant).
2. **Platform-Specific Primitive Mappings:**
   - **File Durability Barrier (`fsync`):**
     - *Windows:* Calls `FlushFileBuffers(HANDLE)` via Python's `os.fsync(fd)`. Guarantees non-volatile medium flush of file contents and file metadata.
     - *Linux:* Calls `fsync(fd)` / `fdatasync(fd)` ensuring dirty pages are committed to storage device.
   - **Directory Entry Durability:**
     - *Windows:* NTFS synchronously commits directory entry modifications upon parent directory flush or synchronous file creation.
     - *Linux:* Requires explicit `fsync(dir_fd)` on parent directory after file creation, unlink, or rename.
   - **Atomic Pointer & Directory Promotion (`os.replace`):**
     - *Windows:* Maps to `MoveFileExW(old, new, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)` providing atomic file/directory replacement on the same volume.
     - *Linux:* Maps to `rename(2)` / `renameat2(2)` atomic syscall.
3. **Canonical Definition of $\mathbf{DURABLE}(barrier)$:**
   $$\mathbf{DURABLE}(barrier) \implies \text{Synchronous non-volatile hardware commit confirmed by OS system call before returning execution.}$$

### 3.7 Durable Pointer Transition Record & 2-Phase Recoverable Commit (B82, B86, B88, B89)

```python
class DurablePointerTransitionRecord(BaseModel):
    """Cryptographically authenticated durable record of pointer state transition (B88).
    
    Prevents silent pointer rollback and binds the transition from previous_tx_id to new_tx_id.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    pointer_version: int = Field(description="Monotonically increasing pointer version.")
    previous_tx_id: Optional[UUID] = Field(description="Previous active transaction ID (None for genesis).")
    new_tx_id: UUID = Field(description="New transaction ID being published.")
    transition_timestamp_utc: datetime = Field(description="Strict UTC timestamp of transition.")
    commit_intent_digest: str = Field(description="SHA-256 of AuthoritativeCommitRecordBlock being published.")
    previous_pointer_digest: str = Field(description="SHA-256 of previous pointer state file for hash-chain continuity.")
```

**CRITICAL B88 INVARIANT: Durable Previous-Pointer Binding (PREVIOUS_POINTER_BINDING)**
$$\mathbf{PREVIOUS\_POINTER\_BINDING}(tx) \iff \text{previous\_tx\_id is durably recorded and bound prior to pointer switch}$$
- **Protocol on CAS Failure:**
  If Step 5c (CAS `COMMITTING` $\to$ `COMMITTED`) fails after Step 5b (pointer switch):
  1. The engine **STRICTLY FORBIDS silent or unauthenticated pointer rollback**.
  2. Rollback of `committed_pointer` to `previous_tx_id` is permitted **IF AND ONLY IF** the on-disk `DurablePointerTransitionRecord` is durably present, valid, and authenticates `previous_tx_id` against the durable ledger head.
  3. The uncommitted transaction `new_tx_id` transitions immediately to **`QUARANTINE_LOCKED`**.
  4. If transition record is missing, corrupted, or contradictory $\to$ **FREEZE SYSTEM IN QUARANTINE_LOCKED**.

```python
class StorageCommitContract:
    """Enforces 2-phase recoverable commit with durable previous-pointer binding (B75, B82, B86, B88, B89)."""

    @staticmethod
    def execute_durable_commit(
        tx: LedgerStorageTransaction,
        tx_id: UUID,
        go_record: HumanGORecord,
        approved_auth: LiveAuthorization,
        activated_auth: LiveAuthorization,
    ) -> AuthoritativeCommitRecordBlock:
        # Phase 1: Staged Mutation Data Durability Barrier (fsync_1)
        tx.write_staged_mutation_data(tx_id, go_record, activated_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)
        if not tx.verify_staged_mutation_data_durable(tx_id, go_record.record_digest, activated_auth):
            raise DataContractError("STAGED_MUTATION_DATA_DURABILITY_VERIFICATION_FAILED")

        # Phase 2: Commit Manifest Durability Barrier (fsync_2)
        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_record.record_digest,
            advanced_head_digest=go_record.record_digest,
            approved_authorization_digest=approved_auth.approved_authorization_digest,
            activated_authorization_digest=activated_auth.activated_authorization_digest,
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})

        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_id)
        if not tx.verify_commit_marker_durable(tx_id, manifest_digest):
            raise DataContractError("COMMIT_MARKER_DURABILITY_VERIFICATION_FAILED")

        # Phase 3: Promote to Snapshot Directory & fsync_3 (B75, B83)
        tx.promote_staging_to_snapshot_directory_atomically(tx_id)
        tx.mark_snapshot_directory_read_only(tx_id)
        tx.flush_snapshot_directory_barrier(tx_id)

        # Phase 4: Pre-CAS Manifest Re-verification under Exclusive Lock (B75, B86)
        if not tx.deep_verify_snapshot_manifest(tx_id, final_commit_block):
            raise DataContractError("POST_BARRIER_TAMPERING_DETECTED_PRE_CAS")

        # Phase 5: Two-Phase Recoverable Commit with Durable Pointer Transition (B82, B88)
        # Step 5a: Record and fsync durable pointer transition binding (B88)
        transition_record = DurablePointerTransitionRecord(
            pointer_version=tx.get_next_pointer_version(),
            previous_tx_id=tx.get_current_active_transaction_id(),
            new_tx_id=tx_id,
            transition_timestamp_utc=datetime.now(timezone.utc),
            commit_intent_digest=manifest_digest,
            previous_pointer_digest=tx.get_current_pointer_digest(),
        )
        tx.write_durable_pointer_transition_record(transition_record)
        tx.flush_pointer_transition_barrier()

        # Step 5b: Atomic pointer switch (committed_pointer -> snapshots/<tx_id>)
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        # Step 5c: Persistent CAS transition: COMMITTING -> COMMITTED
        cas_success = tx.compare_and_set_tx_state(
            tx_id,
            expected=DurableTransactionState.COMMITTING,
            new=DurableTransactionState.COMMITTED,
        )
        if not cas_success:
            # B88 CAS Failure Recovery: Do NOT silently rollback pointer!
            tx.handle_post_pointer_switch_cas_failure(tx_id, transition_record)
            raise DataContractError("COMMIT_CAS_TRANSITION_FAILED")

        return final_commit_block
```

### 3.8 Atomic Activation Transaction Manager (B38, B54, B56, B61, B64, B65, B67, B69, B70, B73, B75, B76, B77, B79, B82, B88)

```python
class ActivationTransactionManager:
    """Coordinates atomic CAS commit, durability barriers, and recovery for Gate B."""

    @staticmethod
    def execute_atomic_activation(
        auth: LiveAuthorization,
        go_record: HumanGORecord,
        trust_store: Ed25519TrustStore,
        ledger: AuthoritativeGOLedger,
    ) -> LiveAuthorization:
        verify_human_go_record_integrity(go_record, trust_store, ledger)
        ActivationValidator.assert_activation_preconditions(auth, go_record, trust_store)

        if go_record.approved_authorization_digest != auth.approved_authorization_digest:
            raise DataContractError(
                f"GO_RECORD_APPROVED_DIGEST_MISMATCH: GO approves {go_record.approved_authorization_digest} "
                f"but LiveAuthorization has {auth.approved_authorization_digest}"
            )

        tx_id = uuid4()

        with ledger.exclusive_lock() as tx:
            if tx.has_transaction_id(tx_id):
                raise DataContractError(f"DUPLICATE_TRANSACTION_ID_REJECTED: {tx_id} already exists in storage")
            tx.reserve_transaction_id(tx_id)

            if tx.current_head_digest != go_record.previous_record_digest:
                raise DataContractError(
                    f"STALE_LEDGER_HEAD_CONFLICT: Expected head {go_record.previous_record_digest}, "
                    f"but current head is {tx.current_head_digest}. Concurrent activation rejected."
                )

            tx.set_tx_state_durable(tx_id, DurableTransactionState.PREPARED)

            journal = tx.create_wal_journal(
                activation_transaction_id=tx_id,
                authorization_id=auth.authorization_id,
                go_record=go_record,
            )
            journal.write_state_durable(JournalState.PREPARED)

            try:
                if not tx.compare_and_set_tx_state(tx_id, expected=DurableTransactionState.PREPARED, new=DurableTransactionState.COMMITTING):
                    raise DataContractError("STATE_TRANSITION_FAILED: Could not transition to COMMITTING")
                journal.write_state_durable(JournalState.COMMITTING)

                activated_auth = auth.model_copy(update={
                    "status": LiveAuthorizationStatus.ACTIVE,
                    "activated_at": datetime.now(timezone.utc),
                    "active_go_record_digest": go_record.record_digest,
                    "activation_transaction_id": tx_id,
                    "source_approved_digest": auth.approved_authorization_digest,
                    "activated_authorization_digest": "",
                })
                activated_digest = hashlib.sha256(
                    CanonicalConfigSerializer.to_canonical_json(activated_auth.model_dump(exclude={"activated_authorization_digest"})).encode("utf-8")
                ).hexdigest()
                activated_auth = activated_auth.model_copy(update={"activated_authorization_digest": activated_digest})

                StorageCommitContract.execute_durable_commit(tx, tx_id, go_record, auth, activated_auth)

                try:
                    journal.write_state_durable(JournalState.COMMITTED)
                except Exception as journal_exc:
                    tx.log_post_commit_journal_anomaly(journal_exc)

                return activated_auth

            except Exception as exc:
                if tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTED:
                    tx.log_post_commit_anomaly(exc)
                    return activated_auth

                cas_aborted = tx.compare_and_set_tx_state(
                    tx_id,
                    expected=DurableTransactionState.COMMITTING,
                    new=DurableTransactionState.ABORTED,
                )
                if not cas_aborted:
                    tx.transition_to_quarantine_locked(tx_id, exc)
                    journal.write_state_durable(JournalState.QUARANTINED)
                    raise DataContractError(
                        f"ACTIVATION_COMMIT_UNCERTAIN: Abort CAS failed. Transitioned to QUARANTINE_LOCKED. "
                        f"Automatic rollback strictly prohibited. Forensic audit required. Error: {exc}"
                    ) from exc

                try:
                    abort_block = AuthoritativeAbortRecordBlock(
                        activation_transaction_id=tx_id,
                        pre_transaction_head_digest=tx.get_pre_transaction_head_digest(),
                        authorization_id=auth.authorization_id,
                        approved_authorization_digest=auth.approved_authorization_digest,
                        expected_previous_state=DurableTransactionState.COMMITTING,
                        terminal_state=DurableTransactionState.ABORTED,
                        abort_reason_code=type(exc).__name__,
                        abort_timestamp_utc=datetime.now(timezone.utc),
                        abort_record_digest="",
                    )
                    abort_digest = abort_block.compute_digest()
                    final_abort_block = abort_block.model_copy(update={"abort_record_digest": abort_digest})
                    tx.write_durable_abort_record(final_abort_block)
                    tx.flush_abort_record_barrier(tx_id)
                    journal.write_state_durable(JournalState.ABORTED)
                except Exception as abort_exc:
                    tx.log_abort_failure_anomaly(abort_exc)

                if is_provably_uncommitted(tx, tx_id):
                    tx.rollback_staging(tx_id)
                    raise DataContractError(f"ACTIVATION_PRE_COMMIT_ABORTED: {exc}") from exc
                else:
                    tx.transition_to_quarantine_locked(tx_id, exc)
                    journal.write_state_durable(JournalState.QUARANTINED)
                    raise DataContractError(
                        f"ACTIVATION_COMMIT_UNCERTAIN: System transitioned to QUARANTINE_LOCKED. "
                        f"Automatic rollback strictly prohibited. Forensic audit required. Error: {exc}"
                    ) from exc
```

### 3.9 Disk-Authoritative Proof of Pre-Commit State (`is_provably_uncommitted()`) (B76, B80)

```python
def is_provably_uncommitted(
    tx: LedgerStorageTransaction,
    tx_id: UUID,
    optional_in_memory_auth: Optional[LiveAuthorization] = None,
) -> bool:
    """Assert DISK-AUTHORITATIVE persistent proof that storage entered terminal ABORTED state (B76, B80)."""
    try:
        abort_record = tx.read_durable_abort_record(tx_id)
        if abort_record is None or not abort_record.is_valid():
            return False

        if abort_record.compute_digest() != abort_record.abort_record_digest:
            return False

        if abort_record.activation_transaction_id != tx_id:
            return False

        durable_pre_head = tx.get_pre_transaction_head_digest_from_disk(tx_id)
        if abort_record.pre_transaction_head_digest != durable_pre_head:
            return False

        durable_draft_digest = tx.read_durable_draft_authorization_digest(abort_record.authorization_id)
        if abort_record.approved_authorization_digest != durable_draft_digest:
            return False

        if abort_record.terminal_state != DurableTransactionState.ABORTED:
            return False

        if tx.get_durable_tx_state(tx_id) != DurableTransactionState.ABORTED:
            return False
        if not tx.assert_abort_is_terminal(tx_id):
            return False

        if tx.committed_pointer_references_transaction(tx_id):
            tx.log_consistency_violation(f"Committed pointer references aborted tx {tx_id}")
            return False

        if tx.has_snapshot_directory(tx_id) and tx.is_snapshot_marked_authoritative(tx_id):
            tx.log_consistency_violation(f"Authoritative snapshot exists for aborted tx {tx_id}")
            return False

        if tx.has_durable_commit_marker(tx_id):
            tx.log_consistency_violation(f"Commit marker present on aborted tx {tx_id}")
            return False
        if tx.get_durable_head_digest() != durable_pre_head:
            tx.log_consistency_violation(f"Head digest advanced on aborted tx {tx_id}")
            return False

        if optional_in_memory_auth is not None:
            if abort_record.authorization_id != optional_in_memory_auth.authorization_id:
                return False
            if abort_record.approved_authorization_digest != optional_in_memory_auth.approved_authorization_digest:
                return False

        return True
    except Exception:
        return False
```

### 3.10 Disambiguated Reader API Contracts (`ReadActiveCommittedSnapshot` vs `ReadCommittedSnapshot`) (B75, B81, B85)

```python
class SnapshotReaderService:
    """Disambiguated, consistent reader contracts over versioned snapshots (B81, B85)."""

    @staticmethod
    def read_active_committed_snapshot(storage: LedgerStorage) -> AuthoritativeSnapshotView:
        active_tx_id = storage.read_committed_snapshot_pointer_atomically()
        if active_tx_id is None:
            raise DataContractError("NO_ACTIVE_COMMITTED_SNAPSHOT_AVAILABLE")

        if storage.get_durable_tx_state(active_tx_id) != DurableTransactionState.COMMITTED:
            raise DataContractError(f"ACTIVE_SNAPSHOT_TX_NOT_COMMITTED: {active_tx_id}")

        commit_block = storage.read_commit_record_block_from_snapshot(active_tx_id)
        if not storage.deep_verify_snapshot_manifest(active_tx_id, commit_block):
            storage.transition_to_quarantine_locked(active_tx_id, Exception("CORRUPTED_ACTIVE_SNAPSHOT_DETECTED"))
            raise DataContractError("ACTIVE_SNAPSHOT_CORRUPTED_ENTERING_QUARANTINE")

        return AuthoritativeSnapshotView(
            transaction_id=active_tx_id,
            commit_record_block=commit_block,
            record=storage.read_record_from_snapshot(active_tx_id),
            head_digest=commit_block.advanced_head_digest,
            authorization=storage.read_authorization_from_snapshot(active_tx_id),
        )

    @staticmethod
    def read_committed_snapshot(storage: LedgerStorage, tx_id: UUID) -> AuthoritativeSnapshotView:
        if storage.get_durable_tx_state(tx_id) != DurableTransactionState.COMMITTED:
            raise DataContractError(f"CANNOT_READ_UNCOMMITTED_SNAPSHOT: {tx_id}")

        if not storage.has_snapshot_directory(tx_id):
            raise DataContractError(f"SNAPSHOT_DIRECTORY_MISSING: {tx_id}")

        commit_block = storage.read_commit_record_block_from_snapshot(tx_id)
        if not storage.deep_verify_snapshot_manifest(tx_id, commit_block):
            storage.transition_to_quarantine_locked(tx_id, Exception(f"CORRUPTED_SNAPSHOT_DETECTED: {tx_id}"))
            raise DataContractError("SNAPSHOT_CORRUPTED_ENTERING_QUARANTINE")

        return AuthoritativeSnapshotView(
            transaction_id=tx_id,
            commit_record_block=commit_block,
            record=storage.read_record_from_snapshot(tx_id),
            head_digest=commit_block.advanced_head_digest,
            authorization=storage.read_authorization_from_snapshot(tx_id),
        )
```

### 3.11 Canonical Authority Hierarchy & Unidirectional Recovery Precedence (B71, B72, B78, B82, B84, B88)

To eliminate any potential circular recovery dependencies, the storage engine defines a strict **Unidirectional Precedence Model**:

```text
┌────────────────────────────────────────────────────────┐
│ 1. tx_state (DurableTransactionState)                  │  <-- Single authority for lifecycle state
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. pointer (committed_pointer + transition.json)       │  <-- Primary active version authority (B88)
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. snapshots/<tx_id>/ (Immutable operational entities) │  <-- Committed payload
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. AuthoritativeCommitRecordBlock (Manifest)           │  <-- Cryptographic evidence authority
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. WAL Journal (reconstructible operational metadata)  │  <-- Rebuilt from storage; NEVER an authority
└────────────────────────────────────────────────────────┘
```

#### 18 Canonical Reachable Classes & Rejection Policy (B84):
Any input vector $\mathbf{v} \notin \text{CanonicalReachableClasses}$ is an **Unreachable / Contradictory Input Domain Vector** that fails closed immediately to **Tier 3 (`QUARANTINE_LOCKED`)**:

| Class | `TxState` | `CommitMarker` | `Manifest` | `AbortRecord` | `SnapshotPointer` | `CASResult` | Authoritative Recovery Action | Resulting Tier |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `PREPARED` | `ABSENT` | `N/A` | `ABSENT` | `ABSENT` | `N/A` | Pre-commit crash before marker; execute Abort CAS & write abort record | **Tier 1 (`ABORTED`)** |
| **2** | `PREPARED` | `VALID` | Any | Any | Any | `N/A` | State violation: marker written before `COMMITTING` state | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **3** | `PREPARED` | `CORRUPT` | Any | Any | Any | `N/A` | State violation: corrupt marker in `PREPARED` | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **4** | `COMMITTING` | `ABSENT` | `N/A` | `ABSENT` | `ABSENT` | `N/A` | Crash before marker written; execute Abort CAS & write bound abort record | **Tier 1 (`ABORTED`)** |
| **5** | `COMMITTING` | `CORRUPT` | Any | Any | Any | `N/A` | Corrupted commit marker on disk; indeterminate intent | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **6** | `COMMITTING` | `VALID` | `INVALID` | Any | Any | `N/A` | Marker valid but entity hash mismatch / corrupt entity | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **7** | `COMMITTING` | `VALID` | `VALID` | `ABSENT` | `ACTIVE` | `SUCCESS` | **Commit-Recovery Path (B82):** Recoverable commit intent; CAS succeeds; finalize journal | **Tier 2 (`COMMITTED`)** |
| **8** | `COMMITTING` | `VALID` | `VALID` | `ABSENT` | `ACTIVE` | `CAS_CONFLICT`| State conflict: CAS failed; restore authenticated previous pointer (B88) | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **9** | `COMMITTING` | `VALID` | `VALID` | `ABSENT` | `ACTIVE` | `STORAGE_IO`  | Storage I/O failure during CAS transition; quarantine | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **10**| `COMMITTING` | `VALID` | `VALID` | `ABSENT` | `ABSENT` | `N/A` | Crash before snapshot pointer switch (Crash-04); conservative quarantine (B90) | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **11**| `COMMITTED` | `VALID` | `VALID` | `ABSENT` | `ACTIVE` | `N/A` | Completely consistent committed transaction; idempotent no-op | **Tier 2 (`COMMITTED`)** |
| **12**| `COMMITTED` | `ABSENT` | Any | Any | Any | `N/A` | Fatal state corruption: state is `COMMITTED` but marker absent | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **13**| `COMMITTED` | `CORRUPT` | Any | Any | Any | `N/A` | Fatal state corruption: state is `COMMITTED` but marker corrupted | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **14**| `COMMITTED` | `VALID` | `INVALID` | Any | Any | `N/A` | Entity payload corrupted post-commit | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **15**| `ABORTED` | `ABSENT` | `N/A` | `VALID_BOUND`| `ABSENT` | `N/A` | Proven aborted; discard staging directory | **Tier 1 (`ABORTED`)** |
| **16**| `ABORTED` | Any | Any | Any | `ACTIVE` | `N/A` | Fatal contradiction: aborted state but pointer is active (B80) | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **17**| `ABORTED` | Any | Any | `CORRUPT` | Any | `N/A` | Aborted state but abort record corrupted | **Tier 3 (`QUARANTINE_LOCKED`)** |
| **18**| `QUARANTINED`| Any | Any | Any | Any | `N/A` | System quarantined; refuse all mutations, forensic audit required | **Tier 3 (`QUARANTINE_LOCKED`)** |

### 3.12 Three-Tier Recovery Decision Tree & Formal Rationale for Conservative Quarantine (B90)

**CRITICAL B90 RATIONALE: Conservative Quarantine Policy for Crash-03 & Crash-04**
- **Crash-03 (Promotion complete, fsync_3 interrupted):** Directory exists in `/snapshots/<tx_id>/`, but physical metadata commit is unproven.
- **Crash-04 (fsync_3 complete, pointer switch pending):** Snapshot is durable, but committed pointer switch was not reached.
- **Formal Invariant:** A transaction that reaches snapshot promotion but has NOT durably established the committed pointer needed for recovery **MUST NOT be auto-aborted**.
  Because physical entity mutations exist on disk, auto-rollback risks destroying legitimate state intent or creating partial-observer divergence. ACASH deliberately chooses **intentional conservative quarantine** over heuristic guessing, freezing the system to preserve all physical evidence for forensic audit.

```
                       [PENDING WAL JOURNAL FOUND]
                                    │
                     Is Journal State == COMMITTED?
                     ├── YES ──► Idempotent No-Op (Tuple: ACTIVE, Head=R, Record=R, COMMITTED)
                     └── NO
                          │
          Evaluate Durable Storage State on Disk:
          1. Does AuthoritativeCommitRecordBlock exist for tx_id?
          2. deep_verify_snapshot_manifest(tx, tx_id, block) == True? (B66, B75)
          3. Is snapshot pointer active and referencing tx_id? (B75, B82)
                                    │
       ┌────────────────────────────┴────────────────────────────┐
    [YES]                                                       [NO]
       │                                                         │
Is durable_tx_state == COMMITTED? (B71, B82)     Does Disk-Authoritative Abort Proof Pass?
  ├── YES ──► TIER 2: COMMITTED (Idempotent)    (is_provably_uncommitted() == True - B76, B80)
  └── NO (State is COMMITTING)                                   │
        │                                        ┌─────────────────┴─────────────────┐
        ▼                                       [YES]                               [NO]
  COMMIT-RECOVERY PATH (B71, B82):               │                                   │
  (Recoverable Commit Intent Recognized)  TIER 1: PRE-COMMIT                 TIER 3: QUARANTINE (B78, B84, B90)
  Attempt CAS: COMMITTING -> COMMITTED    Durable abort proven!              State ambiguous/corrupted!
  ├── SUCCESS ──► TIER 2: COMMITTED       Rollback staging mutations         STRICTLY NO ROLLBACK!
  └── FAILURE ──► TIER 3: QUARANTINE      Tuple: (APPROVED_PENDING_GO,       Set QUARANTINE_LOCKED
                  (Restore auth prev              Head=OldHead,              Tuple: (QUARANTINED,
                   pointer if valid - B88)        Record=Absent,                     Head=UNCERTAIN,
                                                  ABORTED)                           Record=UNCERTAIN,
                                                                                     QUARANTINED)
```

---

## 4. Pre-Admission Bounding, Quote Contract & Deep Admission Verification (B12, B17, B21, B22, B23, B25, B26, B27, B36, B41, B45, B77, B79, B85)

### 4.1 Formal `MT5QuoteSnapshot` Contract (B23, B25, B26)
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
        if max_quote_age_ms is None or max_quote_age_ms <= 0:
            raise PreLiveRiskAdmissionError("MANDATORY_PARAMETER_MISSING: max_quote_age_ms must be positive int")

        if self.timestamp_utc.tzinfo is None or self.timestamp_utc.utcoffset() != timedelta(0):
            raise PreLiveRiskAdmissionError(
                f"INVALID_TIMESTAMP_PROVENANCE: Quote timestamp {self.timestamp_utc} must be explicit UTC-aware"
            )

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

        if self.ask < self.bid:
            raise PreLiveRiskAdmissionError(
                f"INVALID_QUOTE: Inverted market spread ask ({self.ask}) < bid ({self.bid})"
            )
```

### 4.2 Deep Admission Verification & Cryptographic Re-Verification (B41, B45, B77, B79, B85)
```python
# 1. Fetch current active committed snapshot via disambiguated reader API (B85)
active_view = SnapshotReaderService.read_active_committed_snapshot(storage)
authorization = active_view.authorization

# 2. Verify Authorization Status
if authorization.status != LiveAuthorizationStatus.ACTIVE:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_INACTIVE")

# 3. Fetch Bound HumanGORecord from Persistent Ledger
bound_record = active_view.record
if bound_record is None:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Active GO record not found in snapshot")

# 4. Mandatory Full Cryptographic Re-Verification (B45)
verify_human_go_record_integrity(bound_record, trust_store, ledger)

# 5. Deep Field & Lineage Consistency Checks (B41, B48, B51, B77, B79)
if bound_record.record_digest != authorization.active_go_record_digest:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger record digest mismatch")
if bound_record.authorization_id != authorization.authorization_id:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger record authorization_id mismatch")

# B77 & B79: Canonical derivation check using approved_authorization_digest
if bound_record.approved_authorization_digest != authorization.approved_authorization_digest:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger record approved_authorization_digest mismatch")
if authorization.source_approved_digest != bound_record.approved_authorization_digest:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Active authorization source_approved_digest mismatch")

if bound_record.decision != "GO":
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger record decision is not GO")
if active_view.head_digest != bound_record.record_digest:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger head advanced beyond active record")

# 6. Double Validity Window Check
now_utc = datetime.now(timezone.utc)
if not (bound_record.issued_at_utc <= now_utc < bound_record.expires_at_utc):
    raise PreLiveRiskAdmissionError("HUMAN_GO_EXPIRED")
if now_utc >= authorization.expires_at:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_EXPIRED")
```

### 4.3 Pre-Admission Bounding with `max_slippage_points` (B17, B22, B27)
```python
if authorization.max_slippage_points is None or authorization.max_slippage_points <= 0:
    raise PreLiveRiskAdmissionError("MANDATORY_PARAMETER_MISSING: max_slippage_points undefined or non-positive")
if authorization.max_quote_age_ms is None or authorization.max_quote_age_ms <= 0:
    raise PreLiveRiskAdmissionError("MANDATORY_PARAMETER_MISSING: max_quote_age_ms undefined or non-positive")

quote.assert_valid_and_fresh(max_quote_age_ms=authorization.max_quote_age_ms)

slippage_buffer = Decimal(str(authorization.max_slippage_points)) * quote.point_size

if side == OrderSide.BUY:
    worst_case_price = quote.ask + slippage_buffer
else:
    worst_case_price = quote.bid - slippage_buffer

if worst_case_price <= Decimal("0"):
    raise PreLiveRiskAdmissionError(
        f"INVALID_WORST_CASE_EXECUTION_PRICE: Computed worst-case price {worst_case_price} "
        f"is non-positive (Reference: {quote.ask if side == OrderSide.BUY else quote.bid}, "
        f"Buffer: {slippage_buffer})"
    )

order_units = quantity * quote.contract_size
bounded_executable_notional = order_units * worst_case_price

if bounded_executable_notional > authorization.max_notional_usd:
    raise PreLiveRiskAdmissionError(
        f"WORST_CASE_NOTIONAL_BREACH: Bounded executable notional {bounded_executable_notional} "
        f"exceeds limit {authorization.max_notional_usd}"
    )
```

### 4.4 Reconciliation Breaches & Bounded Recovery SLA (B21, B29, B33, B34, B36)
```python
if actual_filled_notional > authorization.max_notional_usd:
    adapter.trip_circuit_breaker(
        reason=AdapterBlockReason.NOTIONAL_BREACH_ANOMALY,
        details=f"Fill notional {actual_filled_notional} exceeded authorized bound {authorization.max_notional_usd}"
    )
    raise ExecutionAnomalyError("CRITICAL_NOTIONAL_BREACH_POST_FILL")
```

---

## 5. Serial Critical Section & In-Flight Concurrency Control (B18, B24, B28)

```python
class StrictSerialExecutionGate:
    """Guarantees exactly zero concurrency during live execution."""

    @classmethod
    def assert_clean_execution_channel(cls, adapter: LiveMT5ExecutionAdapter) -> None:
        if adapter.has_pending_intent():
            raise PreLiveRiskAdmissionError("SERIAL_DISPATCH_VIOLATION: Pending order intent exists")
        if adapter.has_inflight_order():
            raise PreLiveRiskAdmissionError("SERIAL_DISPATCH_VIOLATION: In-flight order dispatch in progress")
        if adapter.has_open_position():
            raise PreLiveRiskAdmissionError("SERIAL_DISPATCH_VIOLATION: Open position already exists on account")

    @classmethod
    def assert_zero_external_mutations(cls, adapter: LiveMT5ExecutionAdapter) -> None:
        broker_orders = adapter.query_broker_orders_raw()
        broker_positions = adapter.query_broker_positions_raw()
        if len(broker_orders) > 0 or len(broker_positions) > 0:
            adapter.trip_circuit_breaker(
                reason=AdapterBlockReason.EXTERNAL_MUTATION_DETECTED,
                details=f"External orders={len(broker_orders)}, positions={len(broker_positions)}"
            )
            raise ExecutionAnomalyError("EXTERNAL_BROKER_MUTATION_DETECTED")
```

---

## 6. Kill-Switch, Revocation & Quarantine Protocols (B19, B20, B49, B58, B62)

1. **Active Key Revocation (B20):**
   When a `CertificateRevocationEvent` is ingested, any key marked `is_revoked = True` immediately causes all subsequent `LiveAuthorization` validations to fail closed.
2. **Circuit Breaker Trip (B19):**
   If drawdown breaches `max_drawdown_pct` or slippage exceeds `max_slippage_points`, the adapter transitions to `BLOCKED`.
3. **Forensic Quarantine Protocol (`QUARANTINE_LOCKED`) (B49, B58, B62, B88, B90):**
   If transaction commit or recovery encounters any ambiguity, missing entity, digest mismatch, pointer corruption, or CAS conflict, the storage engine transitions directly to `QUARANTINE_LOCKED`. Automatic rollback is strictly forbidden.

---

## 7. Machine Gate vs Sovereign Human Governance Gate Comparison Matrix

| Dimension | Machine Gate (M-1 to M-7) | Sovereign Human Governance Gate (G-1 to G-4) |
| :--- | :--- | :--- |
| **Authority** | Algorithmic Quorum ($N \ge 3$) | Designated Human Auditor |
| **Cryptographic Primitive** | Ed25519 Machine Signatures | Ed25519 Sovereign Signature over Canonical `HumanGORecord` |
| **Audit Continuity** | Artifact SHA-256 Digest | Unbroken Hash Chain (`previous_record_digest == current_head_digest`) |
| **Execution Prerequisite** | Valid Machine Quorum | Bound `HumanGORecord` Committed to Authoritative Ledger |
| **Default Policy** | Strict Fail-Closed | Zero Operational Defaults; Explicit Decision Parameter |
| **State Machine Bridge** | Advances to `APPROVED_PENDING_GO` | Executes CAS Commit Transition to `ACTIVE` |

---

## 8. Preflight Checklist (Implementation Gating)

- [ ] All 10 domain schema classes implemented with Pydantic `frozen=True, extra="forbid"`.
- [ ] `HumanGORecord` canonical serializer and Ed25519 verification implemented.
- [ ] `AuthoritativeGOLedger` head verification with CAS atomic append implemented.
- [ ] `StorageCommitContract` with 2-phase recoverable commit (B82) and durable pointer transition record (B88) implemented.
- [ ] Platform-specific storage backend durability contract implemented and validated (B89).
- [ ] `is_provably_uncommitted()` implemented with strictly disk-authoritative proof (zero RAM dependency).
- [ ] `SnapshotReaderService` with disambiguated reader APIs implemented (`ReadActiveCommittedSnapshot` vs `ReadCommittedSnapshot`).
- [ ] 18 Canonical Reachable Recovery Classes and unreachable domain rejection implemented.
- [ ] `MT5QuoteSnapshot` contract with explicit UTC-awareness and freshness implemented.
- [ ] All 100 automated unit tests passing locally.
- [ ] All 11 fault-injection crash scenarios verified on physical filesystem test runner.
- [ ] MyPy zero errors in `src/` and `tests/`.

---

## 9. Comprehensive Verification Harness (100 Unit Tests + 11 Crash Fault-Injection Scenarios)

### 9.1 Unit Test Suite (100 Discrete Automated Unit Tests)

1. `test_human_go_record_schema_immutability`: Verifies `HumanGORecord` is frozen and rejects extra fields.
2. `test_human_go_record_forbids_defaults`: Verifies omitting any mandatory field raises `ValidationError`.
3. `test_human_go_record_canonical_serialization_deterministic`: Verifies identical bytes across dict orderings.
4. `test_human_go_record_signature_verification_success`: Verifies valid Ed25519 signature verification.
5. `test_human_go_record_signature_verification_tamper_payload`: Verifies modifying payload invalidates signature.
6. `test_human_go_record_signature_verification_wrong_key`: Verifies verification fails if wrong key is used.
7. `test_human_go_record_cryptographic_verification`: Verifies valid Ed25519 signature over canonical payload passes.
8. `test_human_go_tamper_previous_digest_fails`: Verifies tampering `previous_record_digest` fails (B13).
9. `test_human_go_tamper_record_digest_fails`: Verifies tampering `record_digest` fails (B13).
10. `test_human_go_tamper_approver_key_id_fails`: Verifies tampering `approver_public_key_id` fails (B13/B14).
11. `test_human_go_rejects_non_auditor_role`: Verifies rejection if registered role $\neq$ `HUMAN_AUDITOR` (B14).
12. `test_human_go_rejects_unregistered_or_revoked_key`: Verifies rejection if key is unregistered/revoked (B14).
13. `test_human_go_expiry_subordination_at_activation`: Verifies rejection if `go_record.expires_at_utc > auth.expires_at` (B15).
14. `test_admission_rejects_expired_authorization_or_go`: Verifies double-window expiry check at admission (`now >= min(auth, go)`) (B15).
15. `test_admission_rejects_stale_or_invalid_price_quote`: Verifies fail-closed on stale quote, inverted spread, or non-positive price (B23).
16. `test_quote_snapshot_rejects_naive_or_non_utc_timestamp`: Verifies fail-closed on naive/non-UTC timestamp (B26).
17. `test_quote_snapshot_rejects_future_timestamp`: Verifies fail-closed on future timestamp ($\text{age\_ms} < 0$) (B26).
18. `test_worst_case_notional_requires_explicit_max_slippage_points`: Verifies fail-closed when `max_slippage_points` missing/None/$\le 0$ (B17).
19. `test_worst_case_notional_requires_explicit_max_quote_age_ms`: Verifies fail-closed when `max_quote_age_ms` missing/None/$\le 0$ (B25).
20. `test_worst_case_price_rejects_zero_or_negative_price`: Verifies fail-closed when worst-case price $\le 0$ (B27).
21. `test_worst_case_notional_nominal_pass_worst_case_fail`: Verifies nominal pass but worst-case fail fails closed (B12/B17).
22. `test_worst_case_notional_pass_within_boundary`: Verifies worst-case within boundary passes (B12/B17).
23. `test_reconciliation_detects_post_fill_notional_breach`: Verifies fill breach triggers `NOTIONAL_BREACH_ANOMALY` & adapter block (B21).
24. `test_post_dispatch_reconciliation_timeout_blocks_adapter`: Verifies SLA timeout blocks adapter with `INDETERMINATE_EXECUTION_TIMEOUT` (B29).
25. `test_strict_serial_mode_rejections`: Verifies discrete pre-dispatch snapshot checks (pending $\neq 0$, in-flight $\neq 0$, open $\neq 0$).
26. `test_strict_serial_lock_failure_and_external_mutation_containment`: Verifies dispatch lock failure and external broker mutation detection (B18, B24, B28).
27. `test_required_approvals_cannot_default`: Verifies fail-closed when `required_approvals` is omitted.
28. `test_max_drawdown_pct_cannot_default`: Verifies fail-closed when `max_drawdown_pct` is omitted.
29. `test_read_only_preflight_cannot_escalate_trading`: Verifies preflight rejects trade-enabled session.
30. `test_revocation_event_halts_issuance`: Verifies `CertificateRevocationEvent` immediately halts order admission (B20).
31. `test_human_go_rejects_chain_fork`: Verifies activation fails if `previous_record_digest` mismatches ledger head (B30).
32. `test_human_go_rejects_stale_previous_digest`: Verifies activation fails on submitting stale digest against advanced head (B30).
33. `test_first_human_go_requires_genesis_digest`: Verifies initial record requires exact genesis digest `"0"*64` (B30).
34. `test_go_ledger_head_updates_atomically`: Verifies ledger head advances to new record digest atomically on commit (B30).
35. `test_human_go_requires_explicit_decision`: Verifies omitting `decision` fails schema validation closed (B31).
36. `test_human_go_requires_explicit_approver_role`: Verifies omitting `approver_role` fails schema validation closed (B32).
37. `test_human_go_rejects_record_role_mismatch`: Verifies activation fails if `go_record.approver_role != trust_store[key_id].role` (B32).
38. `test_reconciliation_timeout_requires_positive_value`: Verifies fail-closed when timeout $\le 0$ or missing (B33/B36).
39. `test_reconciliation_timeout_rejects_above_maximum`: Verifies fail-closed when timeout $= 30001$ (B36).
40. `test_reconciliation_timeout_accepts_maximum_boundary`: Verifies acceptance of exact maximum timeout $= 30000$ (B36).
41. `test_reconciliation_timeout_does_not_retry_order`: Verifies adapter enters `BLOCKED` with `UNKNOWN` state and never retries order (B34).
42. `test_activation_atomicity_rolls_back_status_and_ledger`: Verifies mid-flight activation failure preserves uncommitted state (B35).
43. `test_recovery_rejects_mismatched_transaction_identity`: Verifies recovery rejects mutations if `activation_transaction_id` diverges (B43).
44. `test_recovery_is_idempotent_by_transaction_id`: Verifies repeated recovery calls produce identical safe outcomes (B43).
45. `test_duplicate_activation_transaction_id_rejected_durably`: Verifies duplicate `activation_transaction_id` aborts fail-closed (B48).
46. `test_concurrent_activation_cannot_fork_ledger`: Verifies CAS head check rejects competing activation under concurrent attempts (B38).
47. `test_crash_before_record_append`: Asserts complete final 4-tuple `(APPROVED_PENDING_GO, OldHead, Absent, ABORTED)` on Crash 1 (B39, B47).
48. `test_crash_after_record_append`: Asserts complete final 4-tuple `(APPROVED_PENDING_GO, OldHead, Absent, ABORTED)` on Crash 2 (B39, B47).
49. `test_crash_after_head_update`: Asserts complete final 4-tuple `(APPROVED_PENDING_GO, OldHead, Absent, ABORTED)` on Crash 3 (B39, B47).
50. `test_crash_after_authorization_persist`: Asserts complete final 4-tuple `(ACTIVE, RecordDigest, Present, COMMITTED)` on Crash 4 (B39, B44, B47, B52).
51. `test_recovery_of_committed_transaction_is_idempotent`: Asserts complete final 4-tuple unchanged on repeated recovery (B39, B47).
52. `test_post_commit_exception_does_not_rollback_committed_state`: Verifies post-commit failure does not rollback committed storage (B40, B44).
53. `test_admission_validates_bound_ledger_record_content`: Verifies admission deeply validates bound record content and head alignment (B41).
54. `test_admission_validates_bound_ledger_record_cryptographic_integrity`: Verifies admission re-verifies Ed25519 signature before order admission (B45).
55. `test_admission_rejects_corrupted_record_payload`: Verifies admission fails closed if record payload on disk was tampered (B45).
56. `test_admission_rejects_corrupted_record_signature`: Verifies admission fails closed if record signature on disk was tampered (B45).
57. `test_admission_rejects_revoked_key_at_execution_boundary`: Verifies admission fails closed if key was revoked post-activation (B45).
58. `test_recovery_does_not_rollback_provably_committed_state_on_metadata_mismatch`: Verifies recovery never rolls back durable commit (B49).
59. `test_recovery_quarantines_commit_uncertain_state`: Verifies ambiguous post-commit states enter `QUARANTINE_LOCKED` without rollback (B49).
60. `test_recovery_distinguishes_precommit_from_postcommit_failure`: Verifies recovery distinguishes Tier 1, Tier 2, and Tier 3 (B49).
61. `test_commit_contract_requires_durable_flush_before_success`: Verifies storage contract requires synchronous non-volatile flush (B50, B55).
62. `test_transaction_id_scope_is_explicit`: Verifies `activation_transaction_id` excluded from canonical human payload (B51).
63. `test_recovery_evaluates_all_seven_durable_criteria`: Verifies recovery strictly asserts all proof criteria before `COMMITTED` (B52).
64. `test_concurrent_transaction_id_uniqueness_is_atomic`: Verifies duplicate transaction ID rejection inside exclusive lock (B54).
65. `test_provably_uncommitted_requires_durable_abort_proof`: Verifies `is_provably_uncommitted` returns True ONLY on positive abort proof (B58).
66. `test_missing_record_is_not_sufficient_for_uncommitted_proof`: Verifies absence of record fails closed to False and quarantine (B58).
67. `test_corrupt_commit_marker_is_not_interpreted_as_absent`: Verifies unreadable commit marker triggers quarantine, not rollback (B58, B62).
68. `test_read_error_cannot_produce_provably_uncommitted`: Verifies disk read errors during uncommitted check fail closed to False (B58).
69. `test_commit_marker_ordering_mutation_data_fsync_before_marker_fsync`: Verifies `fsync_1` completes before marker is written (B59).
70. `test_commit_marker_semantic_proof_binds_complete_mutation_manifest`: Verifies Commit Record Block binds unified SHA-256 manifest (B60).
71. `test_storage_commit_success_journal_fsync_failure_never_rolls_back`: Verifies journal sync failure after storage commit never rolls back (B56).
72. `test_journal_partial_write_corruption_preserves_committed_storage`: Verifies partial journal write preserves committed storage (B61).
73. `test_recovery_after_journal_finalization_failure_is_idempotent`: Verifies recovery finalizes journal after post-commit failure (B56, B61).
74. `test_tier3_uncertainty_state_models_ambiguous_record_and_head`: Verifies Tier 3 models record and head as UNCERTAIN (B62).
75. `test_power_loss_before_marker_fsync_quarantines_or_aborts_cleanly`: Verifies power loss between `fsync_1` and `fsync_2` aborts cleanly (B59, B62).
76. `test_no_alternate_path_can_activate_authorization`: Verifies no constructor or helper outside activation manager can set `ACTIVE` (B57).
77. `test_abort_and_commit_terminal_states_are_mutually_exclusive`: Verifies `COMMITTED` and `ABORTED` are mutually exclusive and irreversible (B64).
78. `test_uncommitted_mutations_are_invisible_to_authoritative_reads`: Verifies staged mutations are invisible to authoritative readers (B65).
79. `test_recovery_validates_actual_entities_against_commit_manifest`: Verifies recovery recomputes entity SHA-256 against manifest (B66).
80. `test_failed_abort_cas_causes_quarantine`: Verifies failed abort CAS enters `QUARANTINE_LOCKED` and strictly forbids rollback (B64, B67).
81. `test_publication_order_prevents_partial_authoritative_visibility`: Verifies snapshot publication completes before CAS to `COMMITTED` (B69).
82. `test_recovery_requires_durable_committed_transaction_state`: Verifies Recovery Tier 2 strictly requires `durable_tx_state == COMMITTED` (B71).
83. `test_abort_record_is_bound_to_exact_transaction_snapshot`: Verifies `is_provably_uncommitted` asserts all binding fields on abort record (B70).
84. `test_commit_marker_and_tx_state_conflict_enters_quarantine`: Verifies conflicting states fail closed to `QUARANTINE_LOCKED` (B71, B72).
85. `test_approved_and_activated_authorization_digests_are_distinct`: Verifies distinct validation of both authorization digests (B73).
86. `test_aborted_transaction_cannot_have_published_committed_snapshot`: Verifies aborted transaction has zero published snapshots (B74).
87a. `test_published_snapshot_is_immutable_before_commit`: Verifies snapshot directory is marked read-only and write-once prior to CAS (B75, B83).
87b. `test_mutation_after_publication_barrier_is_rejected`: Verifies attempting to write into snapshot directory after `fsync_3` is rejected by ACLs (B75, B86).
87c. `test_manifest_still_matches_before_committed_transition`: Verifies pre-CAS deep re-verification catches any post-barrier tampering under exclusive lock (B75, B86).
88. `test_abort_proof_survives_full_process_restart`: Verifies `is_provably_uncommitted` derives full abort proof from disk records with zero RAM state (B76).
89. `test_canonical_approved_digest_field_is_used_everywhere`: Verifies `approved_authorization_digest` is used consistently across schemas, aborts, and admission (B77).
90. `test_canonical_recovery_classes_are_deterministic`: Verifies every class of the 18-class matrix yields exactly one deterministic recovery action (B78, B84).
91. `test_unreachable_recovery_vector_enters_quarantine`: Verifies any input vector outside the 18 canonical classes fails closed to `QUARANTINE_LOCKED` (B84).
92. `test_activated_authorization_must_derive_from_approved_authorization`: Verifies `AUTH_CHAIN_VALID(tx)` rejects active authorization with mismatched derivation (B79).
93. `test_aborted_with_any_published_entity_enters_quarantine`: Verifies `ABORTED` transaction possessing any published entity/pointer fails closed to `QUARANTINE_LOCKED` (B80).
94. `test_read_active_committed_snapshot_requires_committed_state`: Verifies `ReadActiveCommittedSnapshot` rejects snapshot if state is not `COMMITTED` (B82, B85).
95. `test_read_committed_snapshot_by_id_allows_historical_audit`: Verifies `ReadCommittedSnapshot(tx_id)` allows reading historical committed snapshot even if not active (B85).
96. `test_failed_commit_cas_preserves_authenticated_previous_pointer`: Verifies that if CAS fails after pointer switch, pointer is rolled back to authenticated previous_tx_id, or system freezes in quarantine (B88).
97. `test_pointer_transition_record_survives_restart`: Verifies `DurablePointerTransitionRecord` is completely readable and authenticated from disk after full host restart (B88).
98. `test_storage_backend_satisfies_declared_durability_contract`: Verifies that filesystem backend satisfies FlushFileBuffers/fsync durability barriers and atomic directory replace semantics (B89).
99. `test_commit_recovery_uses_state_pointer_snapshot_consistently`: Verifies recovery strictly adheres to unidirectional authority precedence (state -> pointer -> snapshot -> manifest -> journal) without circularity (B88).
100. `test_unrecoverable_prepublication_state_quarantines`: Verifies that Crash-03 and Crash-04 fail closed to quarantine preserving physical evidence (B90).

### 9.2 Fault-Injection Crash/Restart Integration Matrix (B87, B89, B90, B91)
> [!NOTE]
> **Evidence Scope (B91):**  
> This matrix validates process-crash, abnormal execution termination, and controlled process restart semantics on real physical filesystem mounts; it does **not** constitute physical hardware power-loss or storage controller failure certification.

| Crash ID | Fault Injection Point | Injected State at Crash | Recovery Action Expected | Expected Final 6-Tuple $\mathbf{\Sigma}$ `(state, pointer, snapshot, manifest, journal, auth)` |
| :---: | :--- | :--- | :--- | :--- |
| **Crash-01** | Post-`fsync_1` (Staged mutation data durable) | Staged files on disk; marker absent | Tier 1: Execute abort CAS, write abort record, discard staging | `(ABORTED, OldPointer, Discarded, N/A, ABORTED, APPROVED_PENDING_GO)` |
| **Crash-02** | Post-`fsync_2` (Commit marker block durable) | Staged files + marker on disk; promotion pending | Tier 1: Staging not promoted; pointer unchanged; abort cleanly | `(ABORTED, OldPointer, Discarded, N/A, ABORTED, APPROVED_PENDING_GO)` |
| **Crash-03** | Post-Promotion (Directory promoted to snapshots) | Directory promoted; `fsync_3` interrupted | Tier 3: Promotion unproven; conservative quarantine (B90) | `(QUARANTINED, OldPointer, UNCERTAIN, UNCERTAIN, QUARANTINED, QUARANTINED)` |
| **Crash-04** | Post-`fsync_3` (Snapshot directory durable) | Snapshot durable; pointer transition pending | Tier 3: Pointer transition absent; conservative quarantine (B90) | `(QUARANTINED, OldPointer, Valid, Valid, QUARANTINED, QUARANTINED)` |
| **Crash-05** | Post-Pointer Switch (Pointer switched to `<tx_id>`) | Pointer active; state is `COMMITTING` | **Commit-Recovery Path (B82):** Recoverable intent recognized; CAS `COMMITTED` | `(COMMITTED, NewPointer, Valid, Valid, COMMITTED, ACTIVE)` |
| **Crash-06** | Pre-CAS Transition (State still `COMMITTING`) | Pointer active; CAS not reached | **Commit-Recovery Path (B82):** CAS executed during recovery | `(COMMITTED, NewPointer, Valid, Valid, COMMITTED, ACTIVE)` |
| **Crash-07** | Post-CAS Transition (State `COMMITTED`) | Storage committed; journal finalization pending | Tier 2: Storage proven committed; journal finalized to `COMMITTED` | `(COMMITTED, NewPointer, Valid, Valid, COMMITTED, ACTIVE)` |
| **Crash-08** | Full Host Restart + Process Recovery | Total RAM wipe; disk-authoritative recovery | Assert complete reconstructibility from disk with zero RAM | Matches expected Tier 1, Tier 2, or Tier 3 outcome |
| **Crash-09** | Post-Pointer Switch CAS Failure (B88) | Pointer is `tx_new`; CAS fails (state conflict) | Rollback pointer to authenticated `previous_tx_id`; quarantine `tx_new` | `(QUARANTINED, OldPointer, Valid, Valid, QUARANTINED, QUARANTINED)` |
| **Crash-10** | Restart Following Post-Pointer CAS Failure (B88) | System restarted after CAS failure | Detect uncommitted pointer + authenticated transition record | `(QUARANTINED, OldPointer, Valid, Valid, QUARANTINED, QUARANTINED)` |
| **Crash-11** | Corrupted Previous-Pointer Transition Record (B88) | Pointer switch uncommitted; transition record corrupt | Freeze entire storage engine; strictly NO silent rollback | `(QUARANTINED, UNCERTAIN, UNCERTAIN, UNCERTAIN, QUARANTINED, QUARANTINED)` |

---

## 10. Exact Stop Gate

```text
================================================================================
                    PHASE 13 SLICE 2 EXACT STOP GATE (REV 19)
================================================================================
Upon completion of Slice 2 Implementation:
1. LiveAuthorization will exist in APPROVED_PENDING_GO.
2. HumanGORecord non-repudiable verification machinery will be fully operational.
3. Authoritative ledger head continuity with CAS commit guard operational.
4. Two-Phase Recoverable Commit Protocol with transaction-addressed snapshots,
   read-only ACLs, and atomic pointer switch (B75, B82, B83, B86) operational.
5. Durable Previous-Pointer Binding with authenticated CAS failure rollback (B88) operational.
6. Storage Backend Durability Contract (Windows NTFS/ReFS & Linux ext4/XFS) (B89) operational.
7. Conservative Quarantine Boundaries for incomplete provenance (B90) operational.
8. Disk-Authoritative Abort Proof with zero RAM dependency (B76) operational.
9. Canonical authorization digest naming with zero ambiguity (B77) operational.
10. 18 Canonical Reachable Recovery Classes with unreachable domain rejection (B78, B84) operational.
11. Cryptographic derivation chain AUTH_CHAIN_VALID(tx) (B79) operational.
12. Formal ABORTED semantic contract guarantee (B80) operational.
13. Disambiguated Reader APIs ReadActiveCommittedSnapshot & ReadCommittedSnapshot (B81, B85) operational.
14. Real filesystem fault-injection harness (Crash-01 through Crash-11) (B87, B91) operational.
15. Worst-case executable notional machine gate with explicit slippage operational.
16. MT5QuoteSnapshot contract with UTC and non-negative age validation operational.
17. Serial critical section with timeout and post-reconciliation SLA operational.
18. Live Capital remains strictly $0.00.
19. Zero broker orders will be sent.
20. Master trading password will NOT be loaded.
21. All execution will STOP completely.
22. Progression to Slice 3 (First Live Order) requires explicit, independent
    Human Sign-Off.
================================================================================
```
