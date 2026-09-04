# Phase 13: Gate B Governance Repair Plan (Formal Specification — Revision 3)

**Document ID:** `ACASH-DOC-P13-GATE-B-GOVERNANCE-REPAIR-PLAN-REV3`  
**Parent Incident Report:** `docs/phase13/gate_b_forensic_reconciliation_report.md` (Commit `affc5ce`)  
**Governing Specification Baseline:** `docs/phase13/slice2_gate_b_plan.md` (Rev 20 Frozen Baseline, Spec Commit `647ba75`)  
**Auditor Review Baseline:** Human Auditor Review of Rev 2 (Resolving 5 Blockers)  
**Current System State:**  
- Transaction Persistence: `COMMITTED` (Incident transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` on physical NTFS)  
- Authorization Provenance: `INVALID` (Self-authorizing runtime runner loop)  
- Governance State: `QUARANTINED / NOT AUTHORIZED`  
- Trading Authority: `STRICTLY BLOCKED`  
- Live Capital Deployed: `$0.00`  
- Live Orders Transmitted: `0`  
- Broker Connection: `DISCONNECTED`  
**Document Status:** REVISION 3 — SUBMITTED FOR FORMAL AUDIT APPROVAL (ZERO EXECUTION / ZERO CODE MUTATION)

---

## 1. Executive Summary & Problem Remediation

During the Gate B activation attempt on 2026-09-05, the runner script committed transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` via a **circular self-authorizing loop**: the runner generated its own Ed25519 human governance keypair at runtime, wrote its own public key into a new trust store, fabricated a `HumanGORecord`, signed the record with its own private key, verified the signature against its own trust store, and hardcoded the confirmation token into evidence.

While the physical storage mechanics (two-phase commit, fsync barriers, CAS elevations, pointer transitions, NTFS DACL) executed correctly as software code, the **governance provenance is mathematically and organizationally invalid**.

This Revision 3 Governance Repair Plan permanently closes every loophole that permitted the incident:
1. **Cryptographic Trust-Store Provenance:** Replaces mutable filesystem timestamps with an immutable `TrustAnchorManifest` verified cryptographically via exact SHA-256 digest before any trust entry is loaded.
2. **OS-Level Capability Boundary:** Enforces kernel-level ownership separation, non-elevation, and anti-replacement policies preventing runner identity from mutating trust-store files.
3. **Strict Process Separation (Mint Tool $\neq$ Runner):** Enforces that the Mint Tool and the Activation Runner execute in separate OS processes. Zero private-key capability crosses process boundaries. The Mint Tool lacks ledger mutation APIs; the Runner lacks signing APIs.
4. **Authoritative Genesis Bootstrap Manifest:** The fresh ledger environment is created and sealed by an external Genesis bootstrap ceremony referencing the incident archive manifest. The runner verifies the Genesis root but cannot create or initialize Genesis authority itself.
5. **Mandatory Forensic Archive (Option 2):** The incident storage `var/gate_b/` is preserved as an immutable archive (`var/gate_b_incident_archive/`). The `COMMITTED` transaction state is never rewritten or falsified.
6. **Decoupled Test Acceptance Language:** Acceptance criteria require that all repository tests pass with exact counts reported dynamically from actual execution, rather than rigid hardcoded numbers.

```text
┌────────────────────────────────────────────────────────────────────────┐
│               GOVERNANCE REPAIR ARCHITECTURE (REVISION 3)              │
├────────────────────────────────────────────────────────────────────────┤
│ 1. INCIDENT FORENSIC ARCHIVE (Mandatory Option 2):                     │
│    var/gate_b/ ──> var/gate_b_incident_archive/ (Immutable / Read-Only)│
│    (Tx 339ce2fd-... remains COMMITTED in archive; provenance INVALID)  │
├────────────────────────────────────────────────────────────────────────┤
│ 2. EXTERNAL GENESIS BOOTSTRAP CEREMONY (Pre-Run Governance Authority): │
│    - Emits genesis_bootstrap_manifest.json (root_id, archive_digest)   │
│    - Initializes fresh root var/gate_b/ starting at GENESIS_HEAD_DIGEST│
│    - Runner VERIFIES Genesis environment; runner CANNOT initialize it  │
├────────────────────────────────────────────────────────────────────────┤
│ 3. SOVEREIGN TRUST ANCHOR CEREMONY (Offline Human Authority):          │
│    - Sovereign Human Private Key held offline / external to ACASH      │
│    - Export public key ──> bootstrap var/gate_b/trust_store.json       │
│    - Emits immutable trust_anchor_manifest.json (SHA-256 sealed)       │
│    - OS Boundary: Governance-owned, Runner has NO write/DACL/replace   │
├────────────────────────────────────────────────────────────────────────┤
│ 4. PROCESS A: MINT TOOL (tools/governance/mint_human_go_record.py):    │
│    - Runs in independent OS process; exits upon artifact generation    │
│    - Binds context: Gate A digest, account, limits, fresh Genesis head │
│    - Signs with Sovereign Private Key ──> outputs human_go_record.json │
│    - Lacks ledger mutation APIs; lacks trust-store mutation APIs       │
├────────────────────────────────────────────────────────────────────────┤
│ 5. PROCESS B: ACTIVATION RUNNER (src/acash/gate_b/runner.py):          │
│    - Separate OS process (Zero private keys; zero signing capability)  │
│    - Verifies genesis_bootstrap_manifest.json root integrity           │
│    - Verifies trust_anchor_manifest.json SHA-256 digest                │
│    - Ingests sealed trust store (Read-Only)                            │
│    - Ingests pre-existing signed human_go_record.json artifact         │
│    - Verifies key provenance, Ed25519 signature, context bindings      │
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
1. **Manifest Sealing:** An authoritative SHA-256 tree manifest of all files, directory structures, and NTFS DACLs in `var/gate_b/` will be generated and signed (`incident_archive_manifest_digest`).
2. **Atomic Relocation:** `var/gate_b/` will be atomically moved to `var/gate_b_incident_archive/`.
3. **Immutable Quarantine ACL:** The entire `var/gate_b_incident_archive/` directory tree will be sealed under an NTFS Read-Only Deny DACL (`Everyone:(OI)(CI)(DENY)(DE,WD,AD,WEA,DC,WA)`), preventing any mutation or deletion.
4. **Lineage Cross-Reference:** The fresh Genesis environment will bind `incident_archive_manifest_digest` in `genesis_bootstrap_manifest.json`, establishing non-executable historical lineage while strictly excluding the archive from the authoritative execution ledger path.

---

## 3. Authoritative Genesis Bootstrap Manifest (Blocker 4 Resolution)

To guarantee that the activation runner does not grant itself Genesis authority by calling `mkdir` or generating a Genesis head, Genesis initialization is established as an **external pre-run bootstrap ceremony**.

### 3.1 `GenesisBootstrapManifest` Schema
```python
class GenesisBootstrapManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int = Field(default=1, description="Schema version.")
    root_id: str = Field(description="Unique stable identifier of fresh storage root.")
    genesis_head_digest: str = Field(
        description="Canonical genesis head digest (must be GENESIS_HEAD_DIGEST)."
    )
    trust_store_digest: str = Field(description="Expected SHA-256 of trust_store.json.")
    trust_anchor_manifest_digest: str = Field(
        description="Expected SHA-256 of trust_anchor_manifest.json."
    )
    incident_archive_manifest_digest: str = Field(
        description="SHA-256 tree manifest of var/gate_b_incident_archive/."
    )
    bootstrap_timestamp_utc: datetime = Field(description="UTC timestamp of bootstrap ceremony.")
    ceremony_authority_id: str = Field(description="Identifier of bootstrapping authority.")
    bootstrap_manifest_digest: str = Field(description="SHA-256 of canonical manifest payload.")
```

### 3.2 Genesis Ceremony Execution Order
1. External bootstrap tool initializes pristine `var/gate_b/` directory skeleton.
2. Writes `var/gate_b/head.json` containing:
   $$\text{head\_digest} = \text{"0000000000000000000000000000000000000000000000000000000000000000"}$$
3. Emits `var/gate_b/genesis_bootstrap_manifest.json` and flushes via Win32 `FlushFileBuffers`.
4. **Runner Verification Contract:** The Activation Runner verifies `genesis_bootstrap_manifest.json` bit-for-bit against expected digests. If the manifest is missing, tampered, or if `head.json` diverges from Genesis, the runner halts immediately (`DataContractError: GENESIS_ENVIRONMENT_UNVERIFIED`). The runner **CANNOT** create or re-initialize Genesis.

---

## 4. Cryptographic Trust-Store Provenance (Blocker 1 Resolution)

Filesystem timestamps are mutable metadata and cannot authorize trust. Trust-anchor pre-existence must be verified **cryptographically**.

### 4.1 `TrustAnchorManifest` Schema
```python
class TrustAnchorManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int = Field(default=1, description="Schema version.")
    ceremony_id: str = Field(description="Identifier of sovereign key ceremony.")
    trust_store_digest: str = Field(description="Exact SHA-256 digest of canonical trust_store.json.")
    trust_store_key_ids: Tuple[str, ...] = Field(
        description="Explicit tuple of registered key IDs (e.g. KEY_HUMAN_GOVERNANCE_AUDITOR_001)."
    )
    ceremony_timestamp_utc: datetime = Field(description="UTC timestamp of key ceremony.")
    ceremony_manifest_digest: str = Field(description="SHA-256 digest over canonical manifest fields.")
```

### 4.2 Runner Cryptographic Ingestion Contract
Before reading any key entry or initializing `Ed25519TrustStore`:
1. Ingest `var/gate_b/trust_anchor_manifest.json`.
2. Compute `actual_trust_store_digest = sha256(read_bytes(var/gate_b/trust_store.json))`.
3. Assert `actual_trust_store_digest == manifest.trust_store_digest`.
4. Assert all required key IDs (`KEY_HUMAN_GOVERNANCE_AUDITOR_001`, `KEY_STORAGE_ENGINE_PROD_001`) exist in `manifest.trust_store_key_ids`.
5. If any digest mismatch or missing key $\to$ Raise `DataContractError: TRUST_STORE_CRYPTOGRAPHIC_PROVENANCE_MISMATCH` (Fail-Closed).
6. Filesystem timestamps (`mtime`, `ctime`) are recorded as non-authoritative diagnostic telemetry only.

---

## 5. OS-Level Capability Boundary (Blocker 2 Resolution)

Application-level absence of write methods is insufficient if process privileges allow filesystem modification. The repair enforces kernel-level OS access controls:

### 5.1 Identity & Ownership Separation
- **Owner Separation:** `trust_store.json`, `trust_anchor_manifest.json`, and `genesis_bootstrap_manifest.json` are owned by the Governance Principal (e.g. Administrator / Auditor), **never by the runner service identity**.
- **Kernel-Level Deny ACE:** Explicit Win32 Deny Access Control Entry (ACE) is applied to the runner identity:
  - Deny Write Data (`WD`)
  - Deny Append Data (`AD`)
  - Deny Write Attributes (`WA`)
  - Deny Write Extended Attributes (`WEA`)
  - Deny Delete (`DE`)
  - Deny Change Permissions (`WRITE_DAC`)
  - Deny Take Ownership (`WRITE_OWNER`)
- **Anti-Replacement Invariant:** Filesystem atomic replacements (`os.replace`, `MoveFileExW` with `MOVEFILE_REPLACE_EXISTING`) and unlinks (`os.remove`, `DeleteFileW`) fail closed at kernel level with `ERROR_ACCESS_DENIED`.

---

## 6. Process-Level Separation: Mint Tool vs Activation Runner (Blocker 3 Resolution)

To eliminate the possibility of a shared memory space or runtime object reuse between authorization creation and authorization consumption, the two roles are physically decoupled across OS processes:

```
┌────────────────────────────────────────┐       ┌────────────────────────────────────────┐
│      PROCESS A: MINT TOOL CLI          │       │      PROCESS B: ACTIVATION RUNNER      │
│  (tools/governance/mint_human_go.py)   │       │      (src/acash/gate_b/runner.py)      │
├────────────────────────────────────────┤       ├────────────────────────────────────────┤
│ • Interactive / Operator execution     │       │ • Automated pipeline execution         │
│ • Loads sovereign private key          │       │ • Zero private key capability          │
│ • Prompts for confirmation token       │       │ • Ingests token via CLI argument       │
│ • Signs canonical HumanGORecord payload│       │ • Strictly Verify-Only                 │
│ • Writes human_go_record.json to disk  │       │ • Ingests pre-existing artifact file   │
│ • LACKS ledger mutation APIs           │       │ • LACKS signing / keygen APIs          │
│ • LACKS trust-store write APIs         │       │ • Ingests sealed trust store (Read-Only│
│ • PROCESS EXITS IMMEDIATELY            │       │ • Executes 2PC under single lock       │
└────────────────────────────────────────┘       └────────────────────────────────────────┘
                    │                                                ▲
                    │           PERSISTED ARTIFACT ONLY              │
                    └─────────── var/gate_b/governance/ ─────────────┘
                                human_go_record.json
```

### 6.1 Capability Boundary Matrix
| Capability | Mint Tool Process | Activation Runner Process |
| :--- | :---: | :---: |
| **Load Sovereign Private Key** | **PERMITTED** (Signing Ceremony Only) | ⛔ **PROHIBITED (Zero Key Capability)** |
| **Sign `HumanGORecord`** | **PERMITTED** | ⛔ **PROHIBITED (Verify-Only)** |
| **Generate Keypairs (`generate_key_pair`)** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Write `trust_store.json`** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Import Storage Write APIs** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Post-Verification 2PC)** |
| **Advance Ledger Head** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Stage 8 2PC Commit)** |
| **Broker Order Dispatch** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED (Slice 3 Blocked)** |

---

## 7. Full Operational Context Binding in `HumanGORecord`

The canonical payload signed by the Human Auditor must bind all operational parameters to prevent replay, transposition, or stale head execution:

```python
class HumanGORecordPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    go_record_id: str                      # e.g., "GO_REC_P13_SLICE2_REPAIR_001"
    authorization_id: str                  # Bound draft: "AUTH_P13_EURUSD_001"
    approved_authorization_digest: str     # Exact SHA-256 of draft.compute_approved_canonical_bytes()
    source_approved_digest: str            # Gate A Certified Digest: 9dbc99aa7bffc593d0...
    previous_record_digest: str            # MUST BE GENESIS_HEAD_DIGEST ("00000...00000")
    account_id: str                        # Target Account: "ACC_112040157"
    symbol: str                            # Target Symbol: "EURUSD"
    max_notional_usd: Decimal              # Micro-capital exposure ceiling: Decimal("500.00")
    max_drawdown_pct: Decimal              # Drawdown ceiling: Decimal("5.00")
    record_timestamp_utc: datetime         # UTC decision timestamp
    expires_at_utc: datetime               # Expiration timestamp (maximum 7 days)
    approver_public_key_id: str            # Must match KEY_HUMAN_GOVERNANCE_AUDITOR_001
```

> [!CRITICAL]
> **Genesis Head Binding:** `previous_record_digest` MUST match `GENESIS_HEAD_DIGEST`. If the payload references the incident head (`81f4d44a...`), the runner halts immediately (`DataContractError: STALE_INCIDENT_LEDGER_HEAD_REJECTED`).

---

## 8. Adversarial Verification Plan (13 Hard Boundary Tests)

The adversarial test suite (`tests/unit/gate_b/test_gate_b_governance_repair.py`) attacks every capability boundary and assumption:

| Test Identifier | Adversarial Attack Scenario | Expected Fail-Closed Assertion |
| :--- | :--- | :--- |
| **Test B1: Runner Keygen AST Ban** | Inspect `src/acash/gate_b/runner.py` AST/bytecode for key generation calls | Code audit fails; zero keypair generation functions exist in module |
| **Test B2: Runner Trust Store Overwrite** | Runner attempts `write_file_durable` on `trust_store.json` | Fails closed with OS `PermissionError` / `StorageDurabilityError` |
| **Test B3: Trust Store DACL Modification** | Runner attempts `icacls` or `SetFileSecurityW` to grant write access | Fails closed with OS `ERROR_ACCESS_DENIED` |
| **Test B4: Trust Store Replacement Attack** | Runner creates `temp.json` and calls `os.replace` on `trust_store.json` | Fails closed with OS `PermissionError` |
| **Test B5: Cryptographic Trust Store Tampering** | Mutate 1 bit in `trust_store.json` without updating manifest | Fails closed: `TRUST_STORE_CRYPTOGRAPHIC_PROVENANCE_MISMATCH` |
| **Test B6: Unknown Approver Key** | `HumanGORecord` signed by key not in `trust_anchor_manifest.json` | Fails closed: `DomainValidationError: unknown key_id` |
| **Test B7: Revoked Approver Key** | Approver key status is `REVOKED` in sealed trust store | Fails closed: `DomainValidationError: key has been REVOKED` |
| **Test B8: Expired Authorization Record** | Runner executed when `current_time > expires_at_utc` | Fails closed: `PreLiveRiskAdmissionError: HUMAN_GO_EXPIRED` |
| **Test B9: Stale Ledger Head Continuity** | `previous_record_digest` references incident head (`81f4d44a...`) | Fails closed: `DataContractError: LEDGER_HEAD_CONTINUITY_BROKEN` |
| **Test B10: Post-Sign Draft Tampering** | Mutate 1 character in `authorization.json` after record signed | Fails closed: `DataContractError: DRAFT_DIGEST_MISMATCH` |
| **Test B11: Genesis Manifest Missing / Tampered** | Delete or tamper `genesis_bootstrap_manifest.json` in fresh root | Fails closed: `DataContractError: GENESIS_ENVIRONMENT_UNVERIFIED` |
| **Test B12: In-Memory Synthetic Record Bypass** | Pass mock dictionary or in-memory model to runner instead of file | Fails closed: `DataContractError: ARTIFACT_FILE_REQUIRED` |
| **Test B13: Mint Tool Execution Boundary** | Invoke mint tool with runner arguments or attempted ledger writes | Fails closed; mint tool lacks storage mutation classes |

---

## 9. Execution Phasing & Acceptance Criteria

The repair proceeds through three strictly gated steps. Advancing between steps requires explicit human auditor sign-off:

```
Step 1: Formal Audit Approval of this Plan (Rev 3)
  │
  ▼
Step 2: Implement Tooling & Architectural Hardening (Zero Activation)
  ├─ tools/governance/mint_human_go_record.py (Process A)
  ├─ src/acash/gate_b/runner.py (Process B Verify-Only)
  ├─ tests/unit/gate_b/test_gate_b_governance_repair.py (13 Adversarial Tests)
  └─ Verification Criterion: ALL REPOSITORY TESTS PASS (Pre-repair baseline + new tests clean; MyPy clean)
  │
  ▼
Step 3: Governance Ceremonies & Storage Re-initialization
  ├─ Archive var/gate_b -> var/gate_b_incident_archive (Option 2)
  ├─ Execute Genesis Bootstrap Ceremony -> emit genesis_bootstrap_manifest.json
  ├─ Execute Trust Anchor Ceremony -> emit sealed trust_store.json & trust_anchor_manifest.json
  ├─ Execute Process A (Mint Tool) -> Human Auditor signs human_go_record.json
  └─ Human Audit Review of Fresh Activation Pack
  │
  ▼
Step 4: Fresh Authoritative Gate B Activation Execution
  ├─ Process B (Verify-Only Runner) executes Stages 1–9 under single lock
  ├─ Verify COMMITTED on fresh root
  └─ Immediate Halt: STOP AGAIN (Live capital = $0.00)
```

> [!NOTE]
> **Acceptance Criterion Language (Blocker 5 Resolution):**  
> "All repository tests pass; exact count reported from actual execution. No regression from pre-repair baseline. Static type checker (MyPy) reports 0 errors across all source files."

---

## 10. Approval Sign-Off Block

```markdown
════════════════════════════════════════════════════════════════════════════════
    GATE B GOVERNANCE REPAIR PLAN (REV 3) — FORMAL AUDIT APPROVAL
════════════════════════════════════════════════════════════════════════════════

Governing Document:       docs/phase13/gate_b_governance_repair_plan.md (Rev 3)
Parent Incident Report:   docs/phase13/gate_b_forensic_reconciliation_report.md
Storage Resolution Mode:  OPTION 2: FORENSIC ARCHIVE & FRESH GENESIS ROOT
Incident Archive Path:    var/gate_b_incident_archive/ (Immutable NTFS Deny DACL)
Genesis Authority:        genesis_bootstrap_manifest.json (GENESIS_HEAD_DIGEST)
Trust Anchor Authority:   trust_anchor_manifest.json (Exact SHA-256 Verified)
OS Capability Contract:   Governance Owner, Non-Elevation, Anti-Replacement DACL
Process Separation:       Process A (Mint Tool) != Process B (Verify-Only Runner)
Live Capital Authority:   $0.00 (Zero Capital Deployed)
Broker Execution:         PROHIBITED (Slice 3 Strictly Blocked)

Auditor Decision:         [ PENDING REVIEW / APPROVED / REVISION REQUIRED ]

Human Governance Auditor: _______________________________________________

Date & Time (UTC):        _______________________________________________

Decision Token:           _______________________________________________
════════════════════════════════════════════════════════════════════════════════
```
