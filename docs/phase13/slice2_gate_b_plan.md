# Phase 13 Slice 2: Gate B Mandatory Human Authorization Plan (Rev 16)
## Preflight & Implementation Plan (Plan Only — Zero Execution)

> **Document:** `docs/phase13/slice2_gate_b_plan.md`  
> **Status:** PROPOSED — PENDING HUMAN AUDITOR APPROVAL (REV 16)  
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

## User Review Required (Rev 16 Audit Adjustments)

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

### Key Refinements in Rev 16 (Addressing Audit Findings B69–B74):

1. **[BLOCKER B69 RESOLVED] Atomic Publication Protocol & Staged Snapshot Ordering:**
   - Locked down the exact write, publication, and barrier ordering to prevent partial-state observation:
     $$\text{Stage Mutations} \to \mathbf{fsync_1} \to \text{Verify Staged} \to \text{Write Marker} \to \mathbf{fsync_2} \to \mathbf{Publish\ Snapshot} \to \mathbf{fsync_3} \to \mathbf{CAS\ COMMITTING \to COMMITTED}$$
   - Publication of the complete immutable snapshot occurs *prior* to flipping the transaction state to `COMMITTED`. Because authoritative readers require `durable_tx_state == COMMITTED`, no reader can ever observe partial, fragmented, or half-published mutations.
2. **[BLOCKER B70 RESOLVED] `AuthoritativeAbortRecordBlock` Complete Snapshot Binding:**
   - Formalized `AuthoritativeAbortRecordBlock` schema binding:
     - `activation_transaction_id`
     - `pre_transaction_head_digest`
     - `authorization_id`
     - `approved_authorization_digest`
     - `expected_previous_state` (`COMMITTING`)
     - `terminal_state` (`ABORTED`)
     - `abort_reason_code`
     - `abort_timestamp_utc`
   - `is_provably_uncommitted()` strictly validates all binding fields against current memory and pre-transaction storage, preventing cross-transaction abort reuse.
3. **[BLOCKER B71 RESOLVED] Recovery Tier 2 Requires Durable Transaction State == `COMMITTED`:**
   - Tier 2 Recovery classification strictly requires:
     $$\text{durable\_tx\_state} == \text{COMMITTED} \land \text{CommitRecordBlock valid} \land \text{verify\_complete\_recovery\_manifest} == \text{True}$$
   - If marker and manifest are valid but `tx_state == COMMITTING` (crash during publication barrier), recovery enters a formal **Commit-Recovery Path** executing atomic CAS `COMMITTING` $\to$ `COMMITTED`. If CAS fails, system transitions to `QUARANTINE_LOCKED`.
4. **[BLOCKER B72 RESOLVED] Canonical Authority Hierarchy & Conflict Resolution:**
   - Explicitly defined the single-authority hierarchy across the 3 core primitives:
     1. **Layer 1 (Lifecycle State Authority):** `DurableTransactionState` (single source of truth for transaction state).
     2. **Layer 2 (Cryptographic Evidence Authority):** `AuthoritativeCommitRecordBlock` (immutable manifest proving snapshot completeness and digests).
     3. **Layer 3 (Committed Payload):** Persisted Entities (`HumanGORecord`, Head, `LiveAuthorization`).
   - Established complete Conflict Resolution Matrix for all state/marker permutations.
5. **[BLOCKER B73 RESOLVED] Authorization Digest Disambiguation:**
   - Disambiguated pre-activation and post-activation authorization digests:
     - `approved_authorization_digest`: SHA-256 of the approved draft `LiveAuthorization` in `APPROVED_PENDING_GO` (bound in `HumanGORecord`).
     - `activated_authorization_digest`: SHA-256 of the activated `LiveAuthorization` artifact in `ACTIVE` state (bound in `AuthoritativeCommitRecordBlock`).
   - Both digests are distinctly declared, hashed, and validated in manifests and admission.
6. **[B74 RESOLVED] Formal `ABORTED` Semantics (Zero Published Snapshot Invariant):**
   - Codified that `durable_tx_state == ABORTED` strictly proves that **no committed snapshot was ever published to the authoritative namespace**.
7. **[TEST EXPANSION] Comprehensive 86-Test Matrix:**
   - Expanded unit test matrix from 80 to **86 discrete unit tests** (Tests 81–86 added for B69–B74).

---

## 1. Executive Summary & Progression Topology

The objective of Phase 13 Slice 2 is to build the formal, dual-layer authorization harness (**Machine Gate + Governance Gate**) required to evaluate Gate B. 

`ACTIVE is reachable only through the authoritative activation transaction path.` Under Rev 14, `ACTIVE` is impossible to reach without an atomic Compare-And-Swap commit binding the verified `LiveAuthorization`, the Ed25519-signed `HumanGORecord`, and the unbroken authoritative ledger head under a unique, durably enforced `activation_transaction_id`:
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
         │   ├── CAS Check: expected_head == tx.current_head_digest (B38)
         │   ├── Stage WAL Journal: PREPARED -> COMMITTING with fsync (B50, B55)
         │   ├── Step 1-3: Persist & fsync_1 Mutation Data (Record, Head, Auth) (B59)
         │   ├── Step 4-6: Write & fsync_2 Commit Record Block Manifest (B59, B60)
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

## 3. Cryptographic Schema, Staging Isolation, Atomic Publication & Terminal CAS Contracts (B11, B13, B14, B15, B30, B31, B32, B35, B38, B39, B40, B43, B44, B48, B49, B50, B51, B52, B53, B54, B55, B56, B57, B58, B59, B60, B61, B62, B64, B65, B66, B67, B68, B69, B70, B71, B72, B73, B74)

### 3.1 Domain Schema Specification & Identity Scope (B51, B73)
```python
class HumanGORecord(BaseModel):
    """Cryptographically verifiable, non-repudiable sovereign authorization artifact.
    
    Proves that a designated human authority personally authorized live capital
    deployment for a specific strategy on a specific broker account with verified
    Gate A evidence, explicit zero-default governance inputs, and unbroken audit lineage.
    
    CRITICAL B51 SCOPE: activation_transaction_id is transactional storage metadata,
    NOT a human authorization claim. It is bound by durable storage invariants and
    ledger transaction headers, NOT by the HumanGORecord Ed25519 digital signature.

    CRITICAL B73 DISAMBIGUATION: approved_authorization_digest explicitly binds the
    SHA-256 digest of the pre-activation draft LiveAuthorization artifact (approved by
    machine quorum), distinct from the post-activation activated_authorization_digest.
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
            "previous_record_digest": self.previous_record_digest,  # CRITICAL B13 & B30 BINDING
        }
        return CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
```

### 3.2 Canonical Cryptographic Integrity Verification Helper (B45)
```python
def verify_human_go_record_integrity(
    record: HumanGORecord,
    trust_store: Ed25519TrustStore,
    ledger: AuthoritativeGOLedger,
) -> None:
    """Verify cryptographic integrity, trust anchor, and audit lineage of HumanGORecord.
    
    Fail-closed invariants:
    1. Recomputed SHA-256 over canonical payload MUST match record.record_digest.
    2. Ed25519 signature MUST be cryptographically valid for approver_public_key_id.
    3. Key in trust_store MUST exist, be active, NOT revoked, and have role HUMAN_AUDITOR.
    4. previous_record_digest MUST match ledger.current_head_digest (or genesis for first).
    """
    canonical_bytes = record.compute_canonical_payload_bytes()
    recomputed_digest = hashlib.sha256(canonical_bytes).hexdigest()
    if recomputed_digest != record.record_digest:
        raise DataContractError(
            f"RECORD_DIGEST_MISMATCH: Computed {recomputed_digest} != record {record.record_digest}"
        )

    if record.approver_public_key_id not in trust_store:
        raise DataContractError(f"KEY_NOT_IN_TRUST_STORE: {record.approver_public_key_id}")
    key_entry = trust_store[record.approver_public_key_id]
    if key_entry.is_revoked:
        raise DataContractError(f"APPROVER_KEY_REVOKED: {record.approver_public_key_id}")
    if not key_entry.is_active:
        raise DataContractError(f"APPROVER_KEY_INACTIVE: {record.approver_public_key_id}")
    if key_entry.role != ApproverRole.HUMAN_AUDITOR or record.approver_role != ApproverRole.HUMAN_AUDITOR:
        raise DataContractError("INVALID_APPROVER_ROLE: Human GO requires active HUMAN_AUDITOR")

    try:
        raw_sig = base64.b64decode(record.signature)
        key_entry.public_key.verify(raw_sig, canonical_bytes)
    except Exception as exc:
        raise DataContractError(f"CRYPTOGRAPHIC_SIGNATURE_INVALID: {exc}") from exc
```

### 3.3 Durable Transaction State Machine & Terminal-State CAS Invariant (B64, B67)
To eliminate any ambiguity between commit and abort states, the storage engine defines an explicit transactional lifecycle:

```python
class DurableTransactionState(str, Enum):
    """Storage-layer transactional lifecycle states."""
    PREPARED = "PREPARED"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"
    QUARANTINED = "QUARANTINED"
```

**CRITICAL B64 INVARIANT: Mutually Exclusive, Irreversible Terminal States**
- `COMMITTED` and `ABORTED` are strictly **mutually exclusive, durable, atomic, and irreversible terminal states**.
- $\text{COMMITTED} \nrightarrow \text{ABORTED}$ and $\text{ABORTED} \nrightarrow \text{COMMITTED}$.
- Transitions from `COMMITTING` are executed exclusively via an atomic Compare-And-Swap operation on persistent storage state:
  $$\text{compare\_and\_set\_tx\_state}(tx\_id, expected=\text{COMMITTING}, new \in \{\text{COMMITTED}, \text{ABORTED}\}) \to \text{bool}$$
- **CRITICAL B67 INVARIANT:** If the abort CAS fails (e.g. state was already `COMMITTED`, storage experienced a write race, or state is unreadable):
  $$\to \textbf{STRICTLY FORBID ROLLBACK}$$
  $$\to \textbf{Transition to QUARANTINE\_LOCKED}$$

### 3.4 Authoritative Abort Record Block Schema & Snapshot Binding Contract (B70, B74)
```python
class AuthoritativeAbortRecordBlock(BaseModel):
    """Cryptographically verifiable on-disk record of an authoritative transaction abort (B70).
    
    CRITICAL B70 BINDING CONTRACT:
    The abort record is bound directly to the exact pre-transaction snapshot, preventing
    cross-transaction abort substitution or unverified rollbacks.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    activation_transaction_id: UUID = Field(description="Unique transactional identity.")
    pre_transaction_head_digest: str = Field(description="Authoritative ledger head digest prior to transaction.")
    authorization_id: str = Field(description="LiveAuthorization identifier bound to this transaction.")
    approved_authorization_digest: str = Field(description="Exact SHA-256 of the approved draft LiveAuthorization artifact.")
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

### 3.5 Authoritative Commit Record Block Schema & Disambiguated Manifest (B60, B73)
```python
class AuthoritativeCommitRecordBlock(BaseModel):
    """Cryptographic manifest proving durable persistence of all transaction mutations (B60, B73).
    
    CRITICAL B73 DISAMBIGUATION:
    Manifest distinctly declares and verifies BOTH the approved_authorization_digest (pre-activation
    draft signed by HumanGORecord) AND the activated_authorization_digest (post-activation artifact).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    activation_transaction_id: UUID = Field(description="Unique transactional identity.")
    commit_timestamp_utc: datetime = Field(description="Strict UTC timestamp of durable commit.")
    ledger_record_digest: str = Field(description="SHA-256 of persisted HumanGORecord.")
    advanced_head_digest: str = Field(description="SHA-256 of new ledger head.")
    approved_authorization_digest: str = Field(description="SHA-256 of the approved pre-activation LiveAuthorization.")
    activated_authorization_digest: str = Field(description="SHA-256 of the activated LiveAuthorization artifact.")
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

### 3.6 Mutation Visibility & Staging Isolation Contract (B65)
**CRITICAL B65 INVARIANT: $\text{fsync} \neq \text{visibility}$**
Persisting mutation payloads prior to the commit marker must NOT make uncommitted mutations visible to authoritative readers. The storage architecture enforces strict **Staging Isolation + Versioned Visibility**:

1. **Isolated Transactional Staging Namespace:**
   All mutations are initially staged in an isolated transaction directory (`storage/staging/<tx_id>/`):
   - Staged `HumanGORecord` payload
   - Staged advanced head pointer
   - Staged activated `LiveAuthorization` payload
2. **Authoritative Reader Isolation:**
   Authoritative reader APIs (`AuthoritativeGOLedger.get_record()`, `AuthoritativeGOLedger.current_head_digest`, `LiveAuthorizationStore.get_authorization()`) query **ONLY** the committed root namespace (`storage/committed/`).
   $$\text{visible}(E) \iff \text{exists}(E \text{ in committed snapshot}) \land \text{durable\_tx\_state}(E.\text{tx\_id}) == \text{COMMITTED}$$

### 3.7 Atomic Snapshot Publication Protocol & Durability Barriers (B50, B55, B59, B60, B65, B69, B73)
> [!NOTE]
> **Durability Barrier Semantics:** `fsync` / `FlushFileBuffers` completion represents the storage backend's synchronous durability barrier under the operating system / filesystem fail-closed contract.

**CRITICAL B69 ORDERING: Publication BEFORE CAS**
To prevent any window where readers could observe partial committed files, the publication of the complete immutable snapshot occurs *prior* to flipping transaction state to `COMMITTED`:

$$\text{Stage Mutations} \to \mathbf{fsync_1} \to \text{Verify Staged} \to \text{Write Marker} \to \mathbf{fsync_2} \to \mathbf{Publish\ Snapshot} \to \mathbf{fsync_3} \to \mathbf{CAS\ COMMITTING \to COMMITTED}$$

```python
class StorageCommitContract:
    """Enforces strict multi-phase write ordering, staging isolation, atomic snapshot publication, and durability barriers (B50, B55, B59, B60, B65, B69, B73)."""

    @staticmethod
    def execute_durable_commit(
        tx: LedgerStorageTransaction,
        tx_id: UUID,
        go_record: HumanGORecord,
        approved_auth: LiveAuthorization,
        activated_auth: LiveAuthorization,
    ) -> AuthoritativeCommitRecordBlock:
        # -------------------------------------------------------------
        # PHASE 1: STAGED MUTATION DATA DURABILITY BARRIER (fsync_1)
        # -------------------------------------------------------------
        # Step 1: Write all mutation data payloads into isolated staging area (B65)
        tx.write_staged_mutation_data(tx_id, go_record, activated_auth)
        
        # Step 2: Synchronous durability barrier for staged data (fsync_1)
        tx.flush_staged_mutation_data_barrier(tx_id)
        
        # Step 3: Verify staged mutation data is readable and digests match
        if not tx.verify_staged_mutation_data_durable(tx_id, go_record.record_digest, activated_auth):
            raise DataContractError("STAGED_MUTATION_DATA_DURABILITY_VERIFICATION_FAILED")

        # -------------------------------------------------------------
        # PHASE 2: COMMIT MANIFEST DURABILITY BARRIER (fsync_2) (B60, B73)
        # -------------------------------------------------------------
        # Step 4: Construct cryptographic Commit Record Block manifest (B60, B73)
        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_record.record_digest,
            advanced_head_digest=go_record.record_digest,
            approved_authorization_digest=approved_auth.authorization_digest,
            activated_authorization_digest=activated_auth.authorization_digest,
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})

        # Step 5: Write immutable commit marker block to staging
        tx.write_commit_marker_block(final_commit_block)
        
        # Step 6: Synchronous durability barrier for commit marker (fsync_2)
        tx.flush_commit_marker_barrier(tx_id)
        
        # Step 7: Verify commit marker on disk
        if not tx.verify_commit_marker_durable(tx_id, manifest_digest):
            raise DataContractError("COMMIT_MARKER_DURABILITY_VERIFICATION_FAILED")

        # -------------------------------------------------------------
        # PHASE 3: ATOMIC SNAPSHOT PUBLICATION & INDEX fsync_3 (B69)
        # -------------------------------------------------------------
        # Step 8: Publish complete immutable snapshot atomically BEFORE CAS (B69)
        # Staged files become present in storage, but reader visibility is STILL BLOCKED
        # because durable_tx_state is still COMMITTING!
        tx.publish_staged_snapshot_atomically(tx_id)
        
        # Step 9: Synchronous durability barrier for publication index / directory (fsync_3)
        tx.flush_publication_barrier()

        # -------------------------------------------------------------
        # PHASE 4: ATOMIC CAS STATE TRANSITION TO COMMITTED (B64, B69)
        # -------------------------------------------------------------
        # Step 10: Atomic persistent CAS state transition to COMMITTED (B64)
        # This single atomic operation makes the entire published snapshot visible to readers!
        if not tx.compare_and_set_tx_state(tx_id, expected=DurableTransactionState.COMMITTING, new=DurableTransactionState.COMMITTED):
            raise DataContractError("COMMIT_CAS_TRANSITION_FAILED")

        return final_commit_block
```

### 3.8 Atomic Activation Transaction Manager (B38, B54, B56, B61, B64, B65, B67, B69, B70, B73)

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
        # Phase 1: Pre-Commit Validation
        verify_human_go_record_integrity(go_record, trust_store, ledger)
        ActivationValidator.assert_activation_preconditions(auth, go_record, trust_store)

        tx_id = uuid4()

        # Phase 2: Exclusive Critical Section (B38, B54)
        with ledger.exclusive_lock() as tx:
            # B54: Atomic Uniqueness Check & Reservation INSIDE Exclusive Lock
            if tx.has_transaction_id(tx_id):
                raise DataContractError(f"DUPLICATE_TRANSACTION_ID_REJECTED: {tx_id} already exists in storage")
            tx.reserve_transaction_id(tx_id)

            # B38 CAS Invariant: Verify head inside locked section
            if tx.current_head_digest != go_record.previous_record_digest:
                raise DataContractError(
                    f"STALE_LEDGER_HEAD_CONFLICT: Expected head {go_record.previous_record_digest}, "
                    f"but current head is {tx.current_head_digest}. Concurrent activation rejected."
                )

            # Initialize durable transaction state machine (B64)
            tx.set_tx_state_durable(tx_id, DurableTransactionState.PREPARED)

            # Stage Durable Write-Ahead Journal (fsync - B50)
            journal = tx.create_wal_journal(
                activation_transaction_id=tx_id,
                authorization_id=auth.authorization_id,
                go_record=go_record,
            )
            journal.write_state_durable(JournalState.PREPARED)

            try:
                # Transition transaction state to COMMITTING (B64)
                if not tx.compare_and_set_tx_state(tx_id, expected=DurableTransactionState.PREPARED, new=DurableTransactionState.COMMITTING):
                    raise DataContractError("STATE_TRANSITION_FAILED: Could not transition to COMMITTING")
                journal.write_state_durable(JournalState.COMMITTING)

                # Prepare in-memory active authorization (B73)
                activated_auth = auth.model_copy(update={
                    "status": LiveAuthorizationStatus.ACTIVE,
                    "activated_at": datetime.now(timezone.utc),
                    "active_go_record_digest": go_record.record_digest,
                    "activation_transaction_id": tx_id,
                })

                # Two-Phase Durability Execution with Publication Protocol (B59, B60, B65, B69, B73)
                StorageCommitContract.execute_durable_commit(tx, tx_id, go_record, auth, activated_auth)

                # Post-Commit Journal Finalization (B56, B61)
                try:
                    journal.write_state_durable(JournalState.COMMITTED)
                except Exception as journal_exc:
                    # B56 & B61: Storage commit is durable! STRICTLY FORBID ROLLBACK!
                    tx.log_post_commit_journal_anomaly(journal_exc)

                return activated_auth

            except Exception as exc:
                # Evaluate durable commit status on disk
                if tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTED:
                    # B56: Storage is already committed! STRICTLY NEVER ROLLBACK!
                    tx.log_post_commit_anomaly(exc)
                    return activated_auth

                # Attempt atomic CAS transition to ABORTED (B64, B67)
                cas_aborted = tx.compare_and_set_tx_state(
                    tx_id,
                    expected=DurableTransactionState.COMMITTING,
                    new=DurableTransactionState.ABORTED,
                )
                if not cas_aborted:
                    # B64 & B67: Abort CAS failed! State transition unproven!
                    # STRICTLY FORBID ROLLBACK -> Enter QUARANTINE_LOCKED
                    tx.transition_to_quarantine_locked(tx_id, exc)
                    journal.write_state_durable(JournalState.QUARANTINED)
                    raise DataContractError(
                        f"ACTIVATION_COMMIT_UNCERTAIN: Abort CAS failed. Transitioned to QUARANTINE_LOCKED. "
                        f"Automatic rollback strictly prohibited. Forensic audit required. Error: {exc}"
                    ) from exc

                # Write authoritative on-disk abort record bound to exact snapshot (B58, B70)
                try:
                    abort_block = AuthoritativeAbortRecordBlock(
                        activation_transaction_id=tx_id,
                        pre_transaction_head_digest=tx.get_pre_transaction_head_digest(),
                        authorization_id=auth.authorization_id,
                        approved_authorization_digest=auth.authorization_digest,
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

                # Determine if state is provably uncommitted or ambiguous (B58, B70, B74)
                if is_provably_uncommitted(tx, tx_id, auth):
                    tx.rollback_staging(tx_id)
                    raise DataContractError(f"ACTIVATION_PRE_COMMIT_ABORTED: {exc}") from exc
                else:
                    # B49, B58: Any ambiguity enters quarantine; NO AUTOMATIC ROLLBACK!
                    tx.transition_to_quarantine_locked(tx_id, exc)
                    journal.write_state_durable(JournalState.QUARANTINED)
                    raise DataContractError(
                        f"ACTIVATION_COMMIT_UNCERTAIN: System transitioned to QUARANTINE_LOCKED. "
                        f"Automatic rollback strictly prohibited. Forensic audit required. Error: {exc}"
                    ) from exc
```

### 3.9 Positive Proof of Pre-Commit State (`is_provably_uncommitted()`) (B58, B64, B70, B74)
Rollback is permitted if and only if **positive durable abort evidence** exists on disk:

```python
def is_provably_uncommitted(
    tx: LedgerStorageTransaction,
    tx_id: UUID,
    auth: LiveAuthorization,
) -> bool:
    """Assert POSITIVE persistent proof that storage entered terminal ABORTED state (B58, B64, B70, B74).
    
    CRITICAL INVARIANTS:
    1. Primary proof: Authoritative on-disk ABORT_RECORD bound to this exact tx_id,
       old head digest, authorization_id, and approved_authorization_digest (B70).
    2. Primary CAS proof: Storage engine confirms durable state == ABORTED and terminal (B64).
    3. Formal ABORTED proof: Engine guarantees NO committed snapshot of this tx was ever published (B74).
    4. Secondary consistency: Commit marker does NOT exist, head is unchanged, auth not ACTIVE.
    If ANY condition fails or I/O read error occurs -> returns False -> QUARANTINE_LOCKED (NO ROLLBACK).
    """
    try:
        # 1. PRIMARY POSITIVE PROOF: Authoritative abort record exists and is valid
        abort_record = tx.read_durable_abort_record(tx_id)
        if abort_record is None or not abort_record.is_valid():
            return False

        # B70: Assert exact snapshot binding fields
        if abort_record.activation_transaction_id != tx_id:
            return False
        if abort_record.pre_transaction_head_digest != tx.get_pre_transaction_head_digest():
            return False
        if abort_record.authorization_id != auth.authorization_id:
            return False
        if abort_record.approved_authorization_digest != auth.authorization_digest:
            return False
        if abort_record.terminal_state != DurableTransactionState.ABORTED:
            return False

        # 2. PRIMARY CAS PROOF: Storage engine confirms terminal state == ABORTED (B64)
        if tx.get_durable_tx_state(tx_id) != DurableTransactionState.ABORTED:
            return False
        if not tx.assert_abort_is_terminal(tx_id):
            return False

        # 3. FORMAL B74 PROOF: Guarantees no committed snapshot was published
        if tx.has_published_committed_snapshot(tx_id):
            tx.log_consistency_violation(f"Published snapshot exists for aborted tx {tx_id}")
            return False

        # 4. SECONDARY CONSISTENCY VALIDATION
        if tx.has_durable_commit_marker(tx_id):
            tx.log_consistency_violation(f"Commit marker present on aborted tx {tx_id}")
            return False
        if tx.get_durable_head_digest() != tx.get_pre_transaction_head_digest():
            tx.log_consistency_violation(f"Head digest advanced on aborted tx {tx_id}")
            return False
        if tx.get_authorization_status_on_disk(tx_id) == LiveAuthorizationStatus.ACTIVE:
            tx.log_consistency_violation(f"Authorization ACTIVE on aborted tx {tx_id}")
            return False

        return True
    except Exception:
        # Any I/O or decode error => Ambiguous => Quarantine (NO ROLLBACK)
        return False
```

### 3.10 Complete Recovery Manifest Deep Entity Verification (B66, B71, B73)

```python
def verify_complete_recovery_manifest(
    tx: LedgerStorageTransaction,
    tx_id: UUID,
    block: AuthoritativeCommitRecordBlock,
) -> bool:
    """Recompute and deeply verify actual on-disk entities against the CommitRecordBlock (B66, B73).
    
    CRITICAL B66 & B73 INVARIANTS:
    Commit marker presence alone is insufficient. Recovery MUST read, hash, and verify:
    1. Actual HumanGORecord bytes on disk -> SHA-256 == block.ledger_record_digest
    2. Actual Head digest on disk -> matches block.advanced_head_digest
    3. Actual LiveAuthorization bytes on disk -> SHA-256 == block.activated_authorization_digest
    4. Recomputed mutation_manifest_digest -> matches block.mutation_manifest_digest
    If ANY entity is corrupt, missing, or mismatched -> returns False (Triggers Quarantine).
    """
    try:
        # 1. Read actual HumanGORecord from disk and verify SHA-256
        actual_record_payload = tx.read_raw_ledger_record_bytes(block.ledger_record_digest)
        if actual_record_payload is None:
            return False
        if hashlib.sha256(actual_record_payload).hexdigest() != block.ledger_record_digest:
            return False

        # 2. Read actual Head from disk and verify digest
        if tx.get_durable_head_digest() != block.advanced_head_digest:
            return False

        # 3. Read actual LiveAuthorization from disk and verify activated_authorization_digest (B73)
        actual_auth_payload = tx.read_raw_authorization_bytes(block.activated_authorization_digest)
        if actual_auth_payload is None:
            return False
        if hashlib.sha256(actual_auth_payload).hexdigest() != block.activated_authorization_digest:
            return False

        # 4. Recompute mutation_manifest_digest from verified fields
        recomputed_manifest = block.compute_manifest_digest()
        if recomputed_manifest != block.mutation_manifest_digest:
            return False

        return True
    except Exception:
        return False
```

### 3.11 Canonical Authority Hierarchy & Conflict Resolution (B71, B72)

| Layer | Canonical Primitive | Authority Domain | Role & Invariants |
| :--- | :--- | :--- | :--- |
| **Layer 1** | `DurableTransactionState` | **Lifecycle State Authority** | Governs transactional lifecycle (`PREPARED`, `COMMITTING`, `COMMITTED`, `ABORTED`, `QUARANTINED`). |
| **Layer 2** | `AuthoritativeCommitRecordBlock` | **Cryptographic Evidence Authority** | Immutable manifest binding and proving snapshot completeness and entity digests. |
| **Layer 3** | Persisted Entities (`Record`, `Head`, `Auth`) | **Committed Payload** | The raw operational files on disk verified by the manifest. |

#### Conflict Resolution Matrix:
| `durable_tx_state` | Commit Marker | Manifest Verification | Resolution / Authoritative Action | Resulting Tier |
| :--- | :--- | :--- | :--- | :--- |
| `COMMITTED` | Valid | Valid | Idempotent recovery; preserve storage, rebuild journal | **Tier 2 (`COMMITTED`)** |
| `COMMITTING` | Valid | Valid | **Commit-Recovery Path (B71):** Execute CAS `COMMITTING` $\to$ `COMMITTED` | **Tier 2 (if CAS OK) / Tier 3 (if CAS fails)** |
| `COMMITTED` | Missing / Corrupted | Any | State corruption: state claims committed but evidence missing | **Tier 3 (`QUARANTINE_LOCKED`)** |
| `ABORTED` | Missing | Secondary checks pass | Proven aborted; discard staging mutations | **Tier 1 (`ABORTED`)** |
| `ABORTED` | Present | Any | Fatal contradiction: abort record with commit marker | **Tier 3 (`QUARANTINE_LOCKED`)** |
| `COMMITTING` | Missing | Missing / Partial | Pre-commit failure: execute abort CAS & verify abort record | **Tier 1 (if Abort OK) / Tier 3 (if Abort fails)** |

### 3.12 Three-Tier Recovery Decision Tree & Forensic Uncertainty States (B44, B49, B58, B61, B62, B66, B71)

```
                       [PENDING WAL JOURNAL FOUND]
                                    │
                     Is Journal State == COMMITTED?
                     ├── YES ──► Idempotent No-Op (Tuple: ACTIVE, Head=R, Record=R, COMMITTED)
                     └── NO
                          │
          Evaluate Durable Storage State on Disk:
          1. Does AuthoritativeCommitRecordBlock exist for tx_id?
          2. verify_complete_recovery_manifest(tx, tx_id, block) == True? (B66, B73)
                                    │
       ┌────────────────────────────┴────────────────────────────┐
    [YES]                                                       [NO]
       │                                                         │
Is durable_tx_state == COMMITTED? (B71)          Does Positive Durable Abort Record Exist?
  ├── YES ──► TIER 2: COMMITTED (Idempotent)    (is_provably_uncommitted() == True - B58, B64, B70, B74)
  └── NO (State is COMMITTING)                                   │
        │                                        ┌─────────────────┴─────────────────┐
        ▼                                       [YES]                               [NO]
  COMMIT-RECOVERY PATH (B71):                    │                                   │
  Attempt CAS: COMMITTING -> COMMITTED    TIER 1: PRE-COMMIT                 TIER 3: QUARANTINE (B62, B66, B71)
  ├── SUCCESS ──► TIER 2: COMMITTED       Durable abort proven!              State ambiguous/corrupted!
  └── FAILURE ──► TIER 3: QUARANTINE      Rollback staging mutations         STRICTLY NO ROLLBACK!
                                          Tuple: (APPROVED_PENDING_GO,       Set QUARANTINE_LOCKED
                                                  Head=OldHead,              Tuple: (QUARANTINED,
                                                  Record=Absent,                     Head=UNCERTAIN,
                                                  ABORTED)                           Record=UNCERTAIN,
                                                                                     QUARANTINED)
```

| Recovery Tier | Classification | Storage Evidence | Authoritative Action | Resulting 4-Tuple $\mathbf{\Sigma}_{\text{final}}$ |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Crash 1-3)** | **Pre-Commit Failure** | Authoritative on-disk `ABORT_RECORD` + CAS `ABORTED` confirmed (B58, B64, B70, B74) | Rollback staging, mark `ABORTED` | `(APPROVED_PENDING_GO, OldHead, Absent, ABORTED)` |
| **Tier 2 (Crash 4-5)** | **Provably Committed** | Valid `CommitRecordBlock`, CAS `COMMITTED`, AND all bound entities verified (B59, B60, B61, B66, B71, B73) | Rebuild journal to `COMMITTED`, preserve `ACTIVE` | `(ACTIVE, RecordDigest, Present, COMMITTED)` |
| **Tier 3 (Ambiguity)** | **Commit Uncertain** | No abort record OR entity digest mismatch OR state conflict (B62, B66, B67, B71, B72) | **QUARANTINE_LOCKED** (STRICTLY NO ROLLBACK) | `(QUARANTINED, UNCERTAIN, UNCERTAIN, QUARANTINED)` |

---

## 4. Pre-Admission Bounding, Quote Contract & Deep Admission Verification (B12, B17, B21, B22, B23, B25, B26, B27, B36, B41, B45)

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
        """Enforce strict quote freshness, UTC provenance, and sanity bounds.
        
        CRITICAL B25 & B26 INVARIANTS:
        - max_quote_age_ms is a required keyword argument (ZERO operational default).
        - timestamp_utc MUST be timezone-aware and set to UTC (offset == 0).
        - 0 <= quote_age_ms <= max_quote_age_ms (strictly rejects future timestamps).
        - ask >= bid > 0 (strictly rejects non-positive or inverted spread).
        """
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

### 4.2 Deep Admission Verification & Cryptographic Re-Verification (B41, B45)
```python
# 1. Verify Authorization Status
if authorization.status != LiveAuthorizationStatus.ACTIVE:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_INACTIVE")

# 2. Fetch Bound HumanGORecord from Persistent Ledger
bound_record = ledger.get_record(authorization.active_go_record_digest)
if bound_record is None:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Active GO record not found in ledger")

# 3. B45: Mandatory Full Cryptographic Re-Verification
verify_human_go_record_integrity(bound_record, trust_store, ledger)

# 4. Deep Field & Lineage Consistency Checks (B41, B48, B51)
if bound_record.record_digest != authorization.active_go_record_digest:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger record digest mismatch")
if bound_record.authorization_id != authorization.authorization_id:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger record authorization_id mismatch")
if bound_record.approved_authorization_digest != authorization.authorization_digest:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger record approved_authorization_digest mismatch")
if bound_record.decision != "GO":
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger record decision is not GO")
if ledger.current_head_digest != bound_record.record_digest:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_DESYNC: Ledger head advanced beyond active record")

# 5. Double Validity Window Check
now_utc = datetime.now(timezone.utc)
if not (bound_record.issued_at_utc <= now_utc < bound_record.expires_at_utc):
    raise PreLiveRiskAdmissionError("HUMAN_GO_EXPIRED")
if now_utc >= authorization.expires_at:
    raise PreLiveRiskAdmissionError("AUTHORIZATION_EXPIRED")
```

### 4.3 Pre-Admission Bounding with `max_slippage_points` (B17, B22, B27)
```python
# 1. Enforce explicit governance parameters (ZERO DEFAULTS)
if authorization.max_slippage_points is None or authorization.max_slippage_points <= 0:
    raise PreLiveRiskAdmissionError("MANDATORY_PARAMETER_MISSING: max_slippage_points undefined or non-positive")
if authorization.max_quote_age_ms is None or authorization.max_quote_age_ms <= 0:
    raise PreLiveRiskAdmissionError("MANDATORY_PARAMETER_MISSING: max_quote_age_ms undefined or non-positive")

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

### 4.4 Post-Fill Detective Anomaly Trap & SLA Timeout (B21, B29, B33, B34, B36)
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

| Parameter Name | Schema Type | Value / Constraint | Classification | Authority / Owner |
| :--- | :--- | :--- | :--- | :--- |
| `signature_algorithm` | `Literal["Ed25519"]` | `"Ed25519"` | **Cryptographic Protocol Constant** | Protocol Spec |
| `max_position_size` | `Decimal` | `Decimal("0.01")` (Micro-lot) | **Slice-3 Fixed Policy Invariant** | Plan Rev3 §4.6 |
| `max_order_rate_per_minute` | `int` | `1` (Throttle limit) | **Technical Debt (Phase 14)** (Not Enforced) | Governance Policy |
| `authorization_id` | `str` | Unique ID (e.g. `AUTH_P13_LIVE_001`) | **Cryptographically Bound** | Machine Clock / Ledger |
| `activation_transaction_id` | `UUID` | RFC 4122 UUID v4 | **Transactional Storage Metadata** (B51) | Transaction Engine |
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
  - Deep Ledger & Cryptographic Integrity Verification (B41, B45)
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

## 9. Comprehensive Automated Test Matrix (86 Tests)

The implementation of Slice 2 will include the following 86 unit tests in `tests/unit/execution/test_gate_b_authorization_lifecycle.py`:

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
43. `test_recovery_rejects_mismatched_transaction_identity`: Verifies recovery manager rejects storage mutations if `activation_transaction_id` diverges between journal and disk entities (B43).
44. `test_recovery_is_idempotent_by_transaction_id`: Verifies repeated recovery calls referencing the same `activation_transaction_id` produce identical safe outcomes (B43).
45. `test_duplicate_activation_transaction_id_rejected_durably`: Verifies that presenting an already-persisted `activation_transaction_id` strictly aborts fail-closed before any mutation (B48).
46. `test_concurrent_activation_cannot_fork_ledger`: Verifies CAS head check rejects competing activation with stale previous digest under concurrent writer attempts (B38).
47. `test_crash_before_record_append`: Asserts complete final 4-tuple `(APPROVED_PENDING_GO, OldHead, Absent, ABORTED)` on Crash 1 (B39, B47).
48. `test_crash_after_record_append`: Asserts complete final 4-tuple `(APPROVED_PENDING_GO, OldHead, Absent, ABORTED)` after rolling back uncommitted append on Crash 2 (B39, B47).
49. `test_crash_after_head_update`: Asserts complete final 4-tuple `(APPROVED_PENDING_GO, OldHead, Absent, ABORTED)` after rolling back uncommitted head advance on Crash 3 (B39, B47).
50. `test_crash_after_authorization_persist`: Asserts complete final 4-tuple `(ACTIVE, RecordDigest, Present, COMMITTED)` when all 7 durable criteria match on Crash 4 (B39, B44, B47, B52).
51. `test_recovery_of_committed_transaction_is_idempotent`: Asserts complete final 4-tuple `(ACTIVE, RecordDigest, Present, COMMITTED)` unchanged on repeated recovery (B39, B47).
52. `test_post_commit_exception_does_not_rollback_committed_state`: Verifies that an exception during post-commit finalization does NOT attempt to rollback durable ledger state (B40, B44).
53. `test_admission_validates_bound_ledger_record_content`: Verifies admission deeply validates bound ledger record digest, authorization_id, decision, role, and head alignment (B41).
54. `test_admission_validates_bound_ledger_record_cryptographic_integrity`: Verifies admission re-verifies SHA-256 canonical digest and Ed25519 signature before order intent construction (B45).
55. `test_admission_rejects_corrupted_record_payload`: Verifies admission fails closed if on-disk record payload was modified after activation (B45).
56. `test_admission_rejects_corrupted_record_signature`: Verifies admission fails closed if on-disk record signature was corrupted or tampered (B45).
57. `test_admission_rejects_revoked_key_at_execution_boundary`: Verifies admission fails closed if approver key was revoked between activation and order execution (B45).
58. `test_recovery_does_not_rollback_provably_committed_state_on_metadata_mismatch`: Verifies that recovery never executes rollback on storage that passed durable commit point (B49).
59. `test_recovery_quarantines_commit_uncertain_state`: Verifies that ambiguous post-commit states transition to `QUARANTINE_LOCKED` without rollback (B49).
60. `test_recovery_distinguishes_precommit_from_postcommit_failure`: Verifies that recovery distinguishes Tier 1 (rollback) from Tier 2 (finalize) and Tier 3 (quarantine) (B49).
61. `test_commit_contract_requires_durable_flush_before_success`: Verifies storage commit contract requires synchronous non-volatile flush before returning success (B50, B55).
62. `test_transaction_id_scope_is_explicit`: Verifies `activation_transaction_id` is excluded from canonical payload and Ed25519 signature computation (B51).
63. `test_recovery_evaluates_all_seven_durable_criteria`: Verifies that recovery strictly asserts all 7 discrete proof criteria before transition to `COMMITTED` (B52).
64. `test_concurrent_transaction_id_uniqueness_is_atomic`: Verifies duplicate transaction ID rejection occurs atomically inside exclusive transaction lock (B54).
65. `test_provably_uncommitted_requires_durable_abort_proof`: Verifies `is_provably_uncommitted` returns True ONLY when positive on-disk abort record is confirmed (B58).
66. `test_missing_record_is_not_sufficient_for_uncommitted_proof`: Verifies absence of record digest fails closed to False and quarantine without rollback (B58).
67. `test_corrupt_commit_marker_is_not_interpreted_as_absent`: Verifies unreadable or corrupt commit marker triggers quarantine rather than pre-commit rollback (B58, B62).
68. `test_read_error_cannot_produce_provably_uncommitted`: Verifies disk read errors during uncommitted evaluation fail closed to False (B58).
69. `test_commit_marker_ordering_mutation_data_fsync_before_marker_fsync`: Verifies `fsync_1` on mutation data strictly completes before commit marker block is written (B59).
70. `test_commit_marker_semantic_proof_binds_complete_mutation_manifest`: Verifies Commit Record Block binds and verifies unified SHA-256 manifest of record, head, and auth digests (B60).
71. `test_storage_commit_success_journal_fsync_failure_never_rolls_back`: Verifies that if storage commit barrier succeeds but subsequent journal sync fails, storage is never rolled back (B56).
72. `test_journal_partial_write_corruption_preserves_committed_storage`: Verifies that power loss during journal write preserves committed storage and rebuilds journal (B61).
73. `test_recovery_after_journal_finalization_failure_is_idempotent`: Verifies recovery manager detects durable storage commit marker and finalizes journal to `COMMITTED` after journal sync failure (B56, B61).
74. `test_tier3_uncertainty_state_models_ambiguous_record_and_head`: Verifies Tier 3 represents record and head as UNCERTAIN rather than fabricating clean states (B62).
75. `test_power_loss_before_marker_fsync_quarantines_or_aborts_cleanly`: Verifies power loss between `fsync_1` and `fsync_2` triggers quarantine/abort without corrupted state (B59, B62).
76. `test_no_alternate_path_can_activate_authorization`: Verifies that no constructor, helper, or direct assignment outside `execute_atomic_activation` can set `status = ACTIVE` (B57).
77. `test_abort_and_commit_terminal_states_are_mutually_exclusive`: Verifies that once a transaction enters `COMMITTED`, it cannot transition to `ABORTED`, and vice-versa (B64).
78. `test_uncommitted_mutations_are_invisible_to_authoritative_reads`: Verifies that staged mutations prior to commit marker `fsync_2` are completely invisible to ledger and authorization readers (B65).
79. `test_recovery_validates_actual_entities_against_commit_manifest`: Verifies recovery recomputes SHA-256 digests of actual on-disk record, head, and authorization files against `AuthoritativeCommitRecordBlock` and quarantines on any mismatch (B66).
80. `test_failed_abort_cas_causes_quarantine`: Verifies that if `compare_and_set_tx_state(expected=COMMITTING, new=ABORTED)` fails, the system enters `QUARANTINE_LOCKED` and strictly forbids rollback (B64, B67).
81. `test_publication_order_prevents_partial_authoritative_visibility`: Verifies staged snapshot is published before CAS to `COMMITTED`, preventing partial-state visibility (B69).
82. `test_recovery_requires_durable_committed_transaction_state`: Verifies Recovery Tier 2 strictly requires `durable_tx_state == COMMITTED` alongside valid marker and manifest (B71).
83. `test_abort_record_is_bound_to_exact_transaction_snapshot`: Verifies `is_provably_uncommitted` asserts all binding fields (`tx_id`, `pre_transaction_head_digest`, `authorization_id`, `approved_authorization_digest`) on `AuthoritativeAbortRecordBlock` (B70).
84. `test_commit_marker_and_tx_state_conflict_enters_quarantine`: Verifies conflicting states (e.g. `COMMITTED` with missing marker, or `ABORTED` with present marker) fail closed to `QUARANTINE_LOCKED` (B71, B72).
85. `test_approved_and_activated_authorization_digests_are_distinct`: Verifies `approved_authorization_digest` and `activated_authorization_digest` are distinct and independently validated (B73).
86. `test_aborted_transaction_cannot_have_published_committed_snapshot`: Verifies that `ABORTED` state strictly proves no committed snapshot was published to authoritative storage (B74).

---

## 10. Exact Stop Gate

```text
================================================================================
                    PHASE 13 SLICE 2 EXACT STOP GATE
================================================================================
Upon completion of Slice 2 Implementation:
1. LiveAuthorization will exist in APPROVED_PENDING_GO.
2. HumanGORecord non-repudiable verification machinery will be fully operational.
3. Authoritative ledger head continuity with CAS commit guard operational.
4. Atomic Activation Transaction Manager with durable terminal-state CAS (B64),
   staging isolation & atomic publication protocol (B65, B69), complete recovery
   manifest verification (B66, B71), bound abort records (B70), digest
   disambiguation (B73), and uncertainty states (B62) operational.
5. Deep admission verification with full cryptographic re-verification operational.
6. Worst-case executable notional machine gate with explicit slippage operational.
7. MT5QuoteSnapshot contract with UTC and non-negative age validation operational.
8. Serial critical section with timeout and post-reconciliation SLA operational.
9. Live Capital remains strictly $0.00.
10. Zero broker orders will be sent.
11. Master trading password will NOT be loaded.
12. All execution will STOP completely.
13. Progression to Slice 3 (First Live Order) requires explicit, independent
    Human Sign-Off.
================================================================================
```
