# Phase 13: Gate B Governance Repair Plan (Formal Specification — Revision 2)

**Document ID:** `ACASH-DOC-P13-GATE-B-GOVERNANCE-REPAIR-PLAN-REV2`  
**Parent Incident Report:** `docs/phase13/gate_b_forensic_reconciliation_report.md` (Commit `affc5ce`)  
**Governing Specification Baseline:** `docs/phase13/slice2_gate_b_plan.md` (Rev 20 Frozen Baseline, Spec Commit `647ba75`)  
**Auditor Review Baseline:** Human Auditor Review of Rev 1 (Incorporates 5 Mandatory Findings)  
**Current System State:**  
- Transaction Persistence: `COMMITTED` (Incident transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` on physical NTFS)  
- Authorization Provenance: `INVALID` (Self-authorizing runtime runner loop)  
- Governance State: `QUARANTINED / NOT AUTHORIZED`  
- Trading Authority: `STRICTLY BLOCKED`  
- Live Capital Deployed: `$0.00`  
- Live Orders Transmitted: `0`  
- Broker Connection: `DISCONNECTED`  
**Document Status:** REVISION 2 — SUBMITTED FOR FORMAL AUDIT APPROVAL (ZERO EXECUTION / ZERO CODE MUTATION)

---

## 1. Executive Summary & Core Architectural Resolution

During the Gate B activation attempt on 2026-09-05, the runner script committed transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` via a **circular self-authorizing loop**: the runner generated its own Ed25519 human governance keypair at runtime, wrote its own public key into a new trust store, fabricated a `HumanGORecord`, signed the record with its own private key, verified the signature against its own trust store, and hardcoded the confirmation token into evidence.

While the physical storage mechanics (two-phase commit, fsync barriers, CAS elevations, pointer transitions, NTFS DACL) executed correctly as software code, the **governance provenance is mathematically and organizationally invalid**.

This Revision 2 Governance Repair Plan establishes the non-negotiable architectural, cryptographic, and operational remediation:
1. **Mandatory Forensic Archive & Clean Genesis Root (Option 2):** Incident storage `var/gate_b` is preserved as an immutable archive (`var/gate_b_incident_archive/`). The `COMMITTED` transaction state is **never rewritten or falsified**. The fresh authoritative ledger root begins cleanly from `GENESIS_HEAD_DIGEST`.
2. **Sovereign Trust Anchor Pre-Existence:** The trust store must exist, be sealed, and be proven read-only **before** any execution process launches. The runner has **zero private-key capability** for human governance keys by architectural design.
3. **Strict Capability Boundary (Mint Tool $\neq$ Activation Runner):** The artifact creation tool (external) and the activation engine (runner) are isolated by enforceable boundary contracts. The runner is strictly **Verify-Only**.
4. **Full Operational Context Binding:** `HumanGORecord` cryptographically binds all risk, account, Gate A lineage, and target ledger head parameters before human signing.
5. **Capability Boundary Test Suite:** Adversarial tests attack every assumption and boundary condition, not merely function calls.

```text
┌────────────────────────────────────────────────────────────────────────┐
│               GOVERNANCE REPAIR ARCHITECTURE (REVISION 2)              │
├────────────────────────────────────────────────────────────────────────┤
│ 1. INCIDENT FORENSIC ARCHIVE (Mandatory Option 2):                     │
│    var/gate_b/ ──> var/gate_b_incident_archive/ (Immutable / Read-Only)│
│    (Tx 339ce2fd-... remains COMMITTED in archive; provenance INVALID)  │
├────────────────────────────────────────────────────────────────────────┤
│ 2. FRESH PRODUCTION LEDGER ROOT (var/gate_b/):                         │
│    - Current Ledger Head: GENESIS_HEAD_DIGEST (000000...000000)        │
│    - Linked via explicit non-authoritative incident lineage metadata   │
├────────────────────────────────────────────────────────────────────────┤
│ 3. SOVEREIGN TRUST ANCHOR CEREMONY (Offline Human Authority):          │
│    - Sovereign Human Private Key held exclusively offline / externally │
│    - Export public key ──> bootstrap var/gate_b/trust_store.json       │
│    - Apply Win32 NTFS Read-Only DACL (Runner cannot write/replace)     │
├────────────────────────────────────────────────────────────────────────┤
│ 4. MINT TOOL (tools/governance/mint_human_go_record.py):               │
│    - Outside execution runtime; operator-invoked                       │
│    - Binds context: Gate A digest, account, limits, GENESIS head       │
│    - Signs with Sovereign Private Key ──> outputs human_go_record.json │
│    - CANNOT activate; CANNOT write ledger; CANNOT mutate trust store   │
├────────────────────────────────────────────────────────────────────────┤
│ 5. ACTIVATION RUNNER (src/acash/gate_b/runner.py) (STRICT VERIFY-ONLY):│
│    - Ingests sealed trust store (Asserts immutable & pre-existing)     │
│    - Ingests pre-existing signed human_go_record.json artifact         │
│    - Verifies key provenance, Ed25519 signature, context bindings      │
│    - Zero keygen; zero human private keys; zero self-signing           │
│    - Enters single continuous lock (Stages 6–8) ──> 2PC Commit         │
│    - Immediate Halt: STOP AGAIN (Live capital remains $0.00)           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Mandatory Storage Resolution: Forensic Archive & Fresh Genesis (Option 2)

### 2.1 Rejection of In-Place State Mutation (Option 1 Rejection)
Option 1 (rewriting `COMMITTED` $\to$ `QUARANTINED` in place on transaction `339ce2fd-...`) is **CATEGORICALLY REJECTED**.
- **The Persistence vs Authority Invariant:** `Transaction persistence = COMMITTED` represents an immutable physical fact that the two-phase commit succeeded on NTFS disk. `Authorization provenance = INVALID` represents the governance verdict. Rewriting the durable CAS file to `QUARANTINED` conflates these distinct domains and corrupts the forensic record.

### 2.2 Execution Procedure for Option 2 (Forensic Archive)
Prior to any fresh activation attempt, the incident storage environment will be archived under strict provenance:
1. **Manifest Sealing:** An authoritative SHA-256 tree manifest of all files, directory structures, and NTFS DACLs in `var/gate_b/` will be generated and signed.
2. **Atomic Relocation:** `var/gate_b/` will be atomically moved to `var/gate_b_incident_archive/`.
3. **Immutable Quarantine ACL:** The entire `var/gate_b_incident_archive/` directory tree will be sealed under an NTFS Read-Only Deny DACL (`Everyone:(OI)(CI)(DENY)(DE,WD,AD,WEA,DC,WA)`), preventing any mutation or deletion.
4. **Lineage Cross-Reference:** The fresh environment will reference `incident_archive_sha256_manifest` in non-executable governance metadata (`docs/phase13/`), but `var/gate_b_incident_archive/` is **strictly excluded** from the authoritative execution ledger path.
5. **Fresh Genesis Root:** The fresh `var/gate_b/` directory will be initialized cleanly starting from `GENESIS_HEAD_DIGEST`:
   $$\text{Head Digest}_{\text{fresh}} = \text{0000000000000000000000000000000000000000000000000000000000000000}$$

---

## 3. Hardened Trust Anchor Architecture & Zero-Capability Contract

### 3.1 Strict Linear Bootstrap Sequence
The trust anchor bootstrap must strictly precede any execution process:
```text
Sovereign Human Key (Held externally)
        ↓
Public Key Exported (32-byte Ed25519 base64)
        ↓
Trust Store Bootstrap (var/gate_b/trust_store.json)
        ↓
Trust Store Sealed (Win32 Flush + NTFS Read-Only DACL)
        ↓
Activation Runner Starts (Verifies pre-existence & DACL)
```

### 3.2 The Runner Zero-Capability Contract
The activation runner codebase (`src/acash/gate_b/runner.py`) is governed by an architectural contract that eliminates human key capabilities by design:
1. **Never Mounted:** The human governance private key is never mounted, copied, or symlinked into the runner environment or container.
2. **Never Available via API:** The runner modules contain no imports, classes, functions, or parameters capable of accepting or processing a private key for human governance.
3. **Never Persisted in Runtime:** Runtime storage (`var/gate_b/`) contains strictly public key entries (`public_key_b64`). Private keys are prohibited under runtime paths.
4. **Never Generated:** `Ed25519Signer.generate_key_pair()` is strictly banned within all execution runner modules. The runner's cryptographic scope is strictly limited to signature verification (`trust_store.verify(...)`).

---

## 4. Enforceable Capability Boundary: Mint Tool vs Activation Runner

To guarantee that the artifact generator never becomes an accidental self-authorizing runner, the codebase enforces an absolute separation of capabilities:

| Capability / Permission | External Mint Tool (`tools/governance/mint_human_go_record.py`) | Production Activation Runner (`src/acash/gate_b/runner.py`) |
| :--- | :---: | :---: |
| **Sovereign Human Private Key** | **PERMITTED** (Operator-supplied via secure CLI prompt/path) | ⛔ **PROHIBITED (Zero Key Capability)** |
| **Sign `HumanGORecord`** | **PERMITTED** | ⛔ **PROHIBITED (Verify-Only)** |
| **Output Signed Artifact** | **PERMITTED** (`human_go_record.json`) | ⛔ **PROHIBITED** |
| **Ingest Sealed Trust Store** | Optional (pre-flight validation) | **MANDATORY (Strictly Read-Only)** |
| **Verify Ed25519 Signatures** | Optional | **MANDATORY (Precondition Gate)** |
| **Mutate / Replace Trust Store** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Write Ledger State (`tx_state`)** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Post-Verification 2PC)** |
| **Advance Ledger Head** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Stage 8 2PC Commit)** |
| **Mutate System Safety Mode** | ⛔ **STRICTLY PROHIBITED** | ⛔ **PROHIBITED (Recovery Engine Only)** |
| **Broker Order Transmission** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED (Slice 3 Blocked)** |

---

## 5. Explicit Context Binding in `HumanGORecord`

The canonical payload signed by the Human Auditor must be bound to the exact operational, financial, and temporal context of the pending transaction. Signing an unbound or partially bound record is rejected fail-closed.

### 5.1 Canonical Bound Fields
```python
class HumanGORecordPayload(BaseModel):
    go_record_id: str                      # e.g., "GO_REC_P13_SLICE2_REPAIR_001"
    authorization_id: str                  # Must match draft: "AUTH_P13_EURUSD_001"
    approved_authorization_digest: str     # SHA-256 of draft.compute_approved_canonical_bytes()
    source_approved_digest: str            # Gate A Certified Digest: 9dbc99aa7bffc593d0...
    previous_record_digest: str            # MUST BE GENESIS_HEAD_DIGEST for fresh root
    account_id: str                        # Target Account: "ACC_112040157"
    symbol: str                            # Target Symbol: "EURUSD"
    max_notional_usd: Decimal              # Hard limit: Decimal("500.00")
    record_timestamp_utc: datetime         # Strict UTC timestamp of decision
    expires_at_utc: datetime               # Authorization expiry (maximum 7 days)
    approver_public_key_id: str            # Must resolve to ACTIVE in sealed trust store
```

### 5.2 Fresh Root Head Binding Invariant
`previous_record_digest` **must reference the ledger head of the fresh authoritative root**:
$$\text{previous\_record\_digest} == \text{GENESIS\_HEAD\_DIGEST} == \text{"0000000000000000000000000000000000000000000000000000000000000000"}$$
If a `HumanGORecord` references the defective head from the incident environment (`81f4d44a...`), the activation runner rejects it fail-closed immediately (`DataContractError: STALE_INCIDENT_LEDGER_HEAD_REJECTED`).

---

## 6. Comprehensive Capability Boundary Verification Plan

The adversarial test suite (`tests/unit/gate_b/test_gate_b_governance_repair.py`) attacks the boundary contracts, proving that neither runner nor mint tool can breach their sandbox:

| Test Identifier | Adversarial Attack Scenario | Expected Fail-Closed Behavior |
| :--- | :--- | :--- |
| **Test B1: Runner Keygen Ban** | Introspect `src/acash/gate_b/runner.py` AST/bytecode for key generation routines | Fails code audit; runner has zero keypair generation functions |
| **Test B2: Runner Trust Store Overwrite** | Runner attempts to call `write_file_durable` on `trust_store.json` | Fails closed with `PermissionError` / `StorageDurabilityError` |
| **Test B3: Trust Store Created Post-Launch** | Trust store timestamp is newer than runner process start time | Fails closed: `DataContractError: TRUST_STORE_PROVENANCE_VIOLATION` |
| **Test B4: Unknown Approver Key** | `HumanGORecord` signed by valid Ed25519 key not in sealed trust store | Fails closed: `DomainValidationError: TrustStore unknown key_id` |
| **Test B5: Untrusted / Revoked Key** | Approver key status is `REVOKED` or expired at `record_timestamp_utc` | Fails closed: `DomainValidationError: key has been REVOKED` |
| **Test B6: Expired Authorization Record** | Runner launched when `current_time > expires_at_utc` | Fails closed: `PreLiveRiskAdmissionError: HUMAN_GO_EXPIRED` |
| **Test B7: Stale Ledger Head Continuity** | `previous_record_digest` matches incident head rather than Genesis head | Fails closed: `DataContractError: LEDGER_HEAD_CONTINUITY_BROKEN` |
| **Test B8: Post-Sign Artifact Mutation** | Mutate 1 character in `authorization.json` after `HumanGORecord` signed | Fails closed: `DataContractError: DRAFT_DIGEST_MISMATCH` |
| **Test B9: Missing Disk Artifact** | Pass in-memory synthetic dictionary to runner instead of file path | Fails closed: `DataContractError: ARTIFACT_FILE_REQUIRED` |
| **Test B10: Mint Tool Activation Ban** | Mint tool invoked with runner arguments or attempted storage writes | Fails closed; mint tool lacks storage commit transaction methods |
| **Test B11: Temporal Provenance Integrity** | $\text{Timestamp}_{\text{trust\_store}} \le \text{Timestamp}_{\text{go\_record}} \le \text{Timestamp}_{\text{runner}}$ | Validates strict chronological lineage of cryptographic artifacts |

---

## 7. Execution Phasing & Transition Gate

The repair proceeds through three strictly gated steps. Advancing between steps requires explicit human auditor sign-off:

```
Step 1: Formal Audit Approval of this Plan (Rev 2)
  │
  ▼
Step 2: Implement Tooling & Architectural Hardening (Zero Activation)
  ├─ tools/governance/mint_human_go_record.py
  ├─ src/acash/gate_b/runner.py (Verify-Only)
  ├─ tests/unit/gate_b/test_gate_b_governance_repair.py
  └─ Verify 1,408/1,408 regression + MyPy clean
  │
  ▼
Step 3: Governance Ceremony & Storage Re-initialization
  ├─ Archive var/gate_b -> var/gate_b_incident_archive (Option 2)
  ├─ Bootstrap sealed var/gate_b/trust_store.json (Phase A)
  ├─ External Human Auditor signs human_go_record.json (Phase B)
  └─ Human Audit Review of Fresh Activation Pack
  │
  ▼
Step 4: Fresh Authoritative Gate B Activation Execution (Phase C)
  ├─ Verify-Only Runner executes Stages 1–9 under single lock
  ├─ Verify COMMITTED on fresh root
  └─ Immediate Halt: STOP AGAIN (Live capital = $0.00)
```

---

## 8. Approval Sign-Off Block

```markdown
════════════════════════════════════════════════════════════════════════════════
    GATE B GOVERNANCE REPAIR PLAN (REV 2) — FORMAL AUDIT APPROVAL
════════════════════════════════════════════════════════════════════════════════

Governing Document:       docs/phase13/gate_b_governance_repair_plan.md (Rev 2)
Parent Incident Report:   docs/phase13/gate_b_forensic_reconciliation_report.md
Storage Resolution Mode:  OPTION 2: FORENSIC ARCHIVE & FRESH GENESIS ROOT
Incident Archive Path:    var/gate_b_incident_archive/ (Immutable NTFS DACL)
Fresh Authoritative Root: var/gate_b/ (Starting from GENESIS_HEAD_DIGEST)
Runner Capability Policy: STRICT VERIFY-ONLY (Zero Human Keygen / Zero Signing)
Mint Tool Policy:         EXTERNAL ARTIFACT MINTING ONLY (Zero Activation)
Live Capital Authority:   $0.00 (Zero Capital Deployed)
Broker Execution:         PROHIBITED (Slice 3 Strictly Blocked)

Auditor Decision:         [ PENDING REVIEW / APPROVED / REVISION REQUIRED ]

Human Governance Auditor: _______________________________________________

Date & Time (UTC):        _______________________________________________

Decision Token:           _______________________________________________
════════════════════════════════════════════════════════════════════════════════
```
