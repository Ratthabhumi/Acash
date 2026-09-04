# Phase 13: Gate B Governance Repair Plan (Formal Specification — Revision 4)

**Document ID:** `ACASH-DOC-P13-GATE-B-GOVERNANCE-REPAIR-PLAN-REV4`  
**Parent Incident Report:** `docs/phase13/gate_b_forensic_reconciliation_report.md` (Commit `affc5ce`)  
**Governing Specification Baseline:** `docs/phase13/slice2_gate_b_plan.md` (Rev 20 Frozen Baseline, Spec Commit `647ba75`)  
**Auditor Review Baseline:** Human Auditor Review of Rev 3 (Resolving Blockers R3-1, R3-2, and Findings R3-3, R3-4)  
**Current System State:**  
- Transaction Persistence: `COMMITTED` (Incident transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` on physical NTFS)  
- Authorization Provenance: `INVALID` (Self-authorizing runtime runner loop)  
- Governance State: `QUARANTINED / NOT AUTHORIZED`  
- Trading Authority: `STRICTLY BLOCKED`  
- Live Capital Deployed: `$0.00`  
- Live Orders Transmitted: `0`  
- Broker Connection: `DISCONNECTED`  
**Document Status:** REVISION 4 — SUBMITTED FOR FORMAL AUDIT APPROVAL (ZERO EXECUTION / ZERO CODE MUTATION)

---

## 1. Executive Summary & Problem Remediation

During the Gate B activation attempt on 2026-09-05, the runner script committed transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` via a **circular self-authorizing loop**: the runner generated its own Ed25519 human governance keypair at runtime, wrote its own public key into a new trust store, fabricated a `HumanGORecord`, signed the record with its own private key, verified the signature against its own trust store, and hardcoded the confirmation token into evidence.

While the physical storage mechanics (two-phase commit, fsync barriers, CAS elevations, pointer transitions, NTFS DACL) executed correctly as software code, the **governance provenance is mathematically and organizationally invalid**.

In Revision 3, the architecture replaced filesystem timestamps with SHA-256 manifests and established process separation. However, audit review identified that **hash integrity is not sovereign authority**: an attacker or rogue script modifying both the payload and manifest can recompute SHA-256 hashes, satisfying integrity checks without possessing authentic sovereign authority.

This Revision 4 Governance Repair Plan establishes a true cryptographic root-of-trust, permanently closing every vulnerability:
1. **Cryptographic Authority via External Digital Signatures (Blocker R3-1 Resolution):** `TrustAnchorManifest` and `GenesisBootstrapManifest` are digitally signed (`Ed25519`) by external sovereign authorities. The Runner verifies external digital signatures against an immutable root-of-trust anchor before reading digests or loading keys. Hash integrity verifies corruption; digital signatures verify authentic sovereign authority.
2. **Cryptographic Binding for Genesis Authority (Blocker R3-2 Resolution):** `GenesisBootstrapManifest` eliminates arbitrary string identifiers (`ceremony_authority_id`) in favor of cryptographic binding (`bootstrap_signer_key_id`, `bootstrap_signature_ed25519`), verified against the external sovereign bootstrap root anchor.
3. **Transitive Capability Isolation (Finding R3-3 Resolution):** Enforces an explicit capability allowlist dependency graph. Automated audits verify that the Runner's entire **transitive import closure** possesses zero private key loading, key generation, signing, or trust-store mutation capabilities.
4. **Human-Presence Requirement in Mint Tool (Finding R3-4 Resolution):** Process A (Mint Tool) enforces interactive TTY presence and manual operator challenge-token entry, preventing automated scripts, pipelines, or background callers from silently driving the minting process.
5. **OS-Level Capability Boundary:** Enforces kernel-level ownership separation, non-elevation, and anti-replacement policies preventing runner identity from mutating trust-store files.
6. **Mandatory Forensic Archive (Option 2):** The incident storage `var/gate_b/` is preserved as an immutable archive (`var/gate_b_incident_archive/`). The `COMMITTED` transaction state is never rewritten or falsified.
7. **Decoupled Test Acceptance Language:** Acceptance criteria require that all repository tests pass with exact counts reported dynamically from actual execution, rather than rigid hardcoded numbers.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      GOVERNANCE REPAIR ARCHITECTURE (REVISION 4)                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. INCIDENT FORENSIC ARCHIVE (Mandatory Option 2):                                     │
│    var/gate_b/ ──> var/gate_b_incident_archive/ (Immutable NTFS Deny DACL)             │
│    (Tx 339ce2fd-... remains COMMITTED in archive; authorization provenance INVALID)    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. EXTERNAL GENESIS BOOTSTRAP AUTHORITY (Pre-Run Sovereign Ceremony):                   │
│    - External Bootstrap Authority signs genesis_bootstrap_manifest.json (Ed25519)     │
│    - Cryptographically binds: root_id, genesis_head_digest, archive_manifest_digest    │
│    - Initializes fresh root var/gate_b/ starting at GENESIS_HEAD_DIGEST                │
│    - Runner VERIFIES external signature; Runner CANNOT create or initialize Genesis   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. EXTERNAL SOVEREIGN TRUST ANCHOR CEREMONY (Offline Human Authority):                 │
│    - Sovereign Human Private Key held strictly offline / external to ACASH codebase    │
│    - Signs trust_anchor_manifest.json (Ed25519) referencing trust_store_digest         │
│    - Ingests sealed public keys into var/gate_b/trust_store.json                       │
│    - OS Boundary: Governance-owned, Runner identity has NO write/DACL/replace access   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. PROCESS A: INTERACTIVE MINT TOOL (tools/governance/mint_human_go_record.py):        │
│    - Requires interactive TTY human presence (asserts isatty; prompts operator)        │
│    - Binds full operational context: Gate A digest, account, limits, fresh Genesis     │
│    - Signs with Sovereign Approver Key ──> outputs human_go_record.json artifact       │
│    - Lacks ledger mutation APIs; lacks trust-store mutation APIs; exits immediately    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. PROCESS B: VERIFY-ONLY RUNNER (src/acash/gate_b/runner.py):                         │
│    - Separate OS process; Transitive dependency closure has ZERO signing/keygen       │
│    - Verifies external Ed25519 signature on genesis_bootstrap_manifest.json            │
│    - Verifies external Ed25519 signature on trust_anchor_manifest.json                 │
│    - Verifies exact SHA-256 digest of trust_store.json against signed manifest         │
│    - Verifies Ed25519 signature on pre-existing human_go_record.json artifact          │
│    - Enters single continuous transactional lock (Stages 6–8) ──> 2PC Commit           │
│    - Immediate Halt: STOP AGAIN (Live capital remains $0.00; Live orders = 0)          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Mandatory Storage Resolution: Forensic Archive & Fresh Genesis (Option 2)

### 2.1 Rejection of In-Place State Mutation (Option 1 Rejection)
Option 1 (rewriting `COMMITTED` $\to$ `QUARANTINED` in place on transaction `339ce2fd-...`) is **CATEGORICALLY REJECTED**.
- **The Persistence vs Authority Invariant:** `Transaction persistence = COMMITTED` represents an immutable physical fact that the two-phase commit succeeded on NTFS disk. `Authorization provenance = INVALID` represents the governance verdict. Rewriting the durable CAS file to `QUARANTINED` conflates these distinct domains and corrupts the forensic record.

### 2.2 Execution Procedure for Option 2 (Forensic Archive)
Prior to any fresh activation attempt, the incident storage environment will be archived under strict provenance:
1. **Manifest Sealing:** An authoritative SHA-256 tree manifest of all files, directory structures, and NTFS DACLs in `var/gate_b/` will be generated and recorded (`incident_archive_manifest_digest`).
2. **Atomic Relocation:** `var/gate_b/` will be atomically moved to `var/gate_b_incident_archive/`.
3. **Immutable Quarantine ACL:** The entire `var/gate_b_incident_archive/` directory tree will be sealed under an NTFS Read-Only Deny DACL (`Everyone:(OI)(CI)(DENY)(DE,WD,AD,WEA,DC,WA)`), preventing any mutation or deletion.
4. **Lineage Cross-Reference:** The fresh Genesis environment will bind `incident_archive_manifest_digest` in `genesis_bootstrap_manifest.json`, establishing non-executable historical lineage while strictly excluding the archive from the authoritative execution ledger path.

---

## 3. Authoritative Genesis Bootstrap Manifest (Blocker R3-2 Resolution)

To guarantee that the activation runner does not grant itself Genesis authority by calling `mkdir` or generating a Genesis head, Genesis initialization is established as an **external pre-run bootstrap ceremony** digitally signed by the Sovereign Bootstrap Authority.

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
    bootstrap_signer_key_id: str = Field(
        description="Cryptographic identifier of sovereign bootstrapping key."
    )
    bootstrap_signature_ed25519: str = Field(
        description="Hex-encoded Ed25519 signature over canonical payload bytes."
    )

    def compute_canonical_signed_bytes(self) -> bytes:
        """Compute canonical JSON bytes over manifest fields excluding the signature."""
        payload = {
            "manifest_version": self.manifest_version,
            "root_id": self.root_id,
            "genesis_head_digest": self.genesis_head_digest,
            "trust_store_digest": self.trust_store_digest,
            "trust_anchor_manifest_digest": self.trust_anchor_manifest_digest,
            "incident_archive_manifest_digest": self.incident_archive_manifest_digest,
            "bootstrap_timestamp_utc": self.bootstrap_timestamp_utc.isoformat(),
            "bootstrap_signer_key_id": self.bootstrap_signer_key_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

### 3.2 Genesis Ceremony & Runner Verification Order
1. External bootstrap tool initializes pristine `var/gate_b/` directory skeleton.
2. Writes `var/gate_b/head.json` containing:
   $$\text{head\_digest} = \text{"0000000000000000000000000000000000000000000000000000000000000000"}$$
3. Signs manifest with `SOVEREIGN_BOOTSTRAP_KEY` and emits `var/gate_b/genesis_bootstrap_manifest.json`.
4. Flushes storage via Win32 `FlushFileBuffers`.
5. **Runner Verification Contract:** The Activation Runner verifies:
   a. Manifest exists and deserializes under frozen model.
   b. `bootstrap_signer_key_id` matches the immutable sovereign root anchor.
   c. `bootstrap_signature_ed25519` is cryptographically valid over `compute_canonical_signed_bytes()`.
   d. `genesis_head_digest` matches `GENESIS_HEAD_DIGEST` ("00000...00000").
   e. `head.json` on disk matches `GENESIS_HEAD_DIGEST`.
   f. If any check fails $\to$ Raise `DataContractError: GENESIS_ENVIRONMENT_UNVERIFIED` (Fail-Closed).
   The Runner **CANNOT** create or re-initialize Genesis.

---

## 4. Cryptographic Trust-Store Provenance & Authority (Blocker R3-1 Resolution)

Filesystem timestamps are mutable metadata, and standalone hashes only verify file integrity without authenticating origin. Trust-anchor pre-existence and authority must be **verified cryptographically via external digital signature**.

```text
External Sovereign Authority (Offline)
                 │
                 ▼ signs via Sovereign Private Key
┌────────────────────────────────────────────────────────┐
│             TrustAnchorManifest (Signed)               │
├────────────────────────────────────────────────────────┤
│ manifest_version: 1                                    │
│ ceremony_id: "CEREMONY_SOVEREIGN_ROOT_20260905"        │
│ trust_store_digest: SHA256(trust_store.json)           │
│ trust_store_key_ids: ["KEY_HUMAN_GOVERNANCE_..."]      │
│ sovereign_signer_key_id: "KEY_EXTERNAL_SOVEREIGN_ROOT" │
│ sovereign_signature_ed25519: <Ed25519 Signature>       │
└────────────────────────────────────────────────────────┘
                 │
                 ▼ verifies signature against compiled Root Anchor
┌────────────────────────────────────────────────────────┐
│             Activation Runner (Verify-Only)            │
├────────────────────────────────────────────────────────┤
│ 1. Verify sovereign_signature_ed25519 (Authenticity)   │
│ 2. Compute SHA256(trust_store.json) (Integrity)        │
│ 3. Assert compute_digest == manifest.trust_store_digest│
│ 4. Assert key_ids in manifest.trust_store_key_ids      │
│ 5. ONLY THEN ingest trust_store.json                   │
└────────────────────────────────────────────────────────┘
```

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
    sovereign_signer_key_id: str = Field(
        description="Key ID of sovereign authority that authorized this trust store."
    )
    sovereign_signature_ed25519: str = Field(
        description="Hex-encoded Ed25519 signature over canonical manifest payload bytes."
    )

    def compute_canonical_signed_bytes(self) -> bytes:
        """Compute canonical JSON bytes over manifest fields excluding the signature."""
        payload = {
            "manifest_version": self.manifest_version,
            "ceremony_id": self.ceremony_id,
            "trust_store_digest": self.trust_store_digest,
            "trust_store_key_ids": list(self.trust_store_key_ids),
            "ceremony_timestamp_utc": self.ceremony_timestamp_utc.isoformat(),
            "sovereign_signer_key_id": self.sovereign_signer_key_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

### 4.2 Runner Cryptographic Ingestion Contract
Before reading any key entry or initializing `Ed25519TrustStore`:
1. Ingest `var/gate_b/trust_anchor_manifest.json`.
2. Extract `sovereign_signer_key_id` and match against the immutable external root anchor.
3. Cryptographically verify `sovereign_signature_ed25519` over `compute_canonical_signed_bytes()` using the sovereign root public key.
4. Compute `actual_trust_store_digest = sha256(read_bytes(var/gate_b/trust_store.json))`.
5. Assert `actual_trust_store_digest == manifest.trust_store_digest`.
6. Assert all required key IDs (`KEY_HUMAN_GOVERNANCE_AUDITOR_001`, `KEY_STORAGE_ENGINE_PROD_001`) exist in `manifest.trust_store_key_ids`.
7. If signature fails, digest mismatches, or required keys are missing $\to$ Raise `DataContractError: TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID` (Fail-Closed).
8. Only upon 100% cryptographic verification of the manifest does the runner load `trust_store.json`.

---

## 5. OS-Level Capability Boundary

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

## 6. Process-Level Separation & Human Presence

### 6.1 Process Separation: Mint Tool vs Activation Runner
To eliminate the possibility of a shared memory space or runtime object reuse between authorization creation and authorization consumption, the two roles are physically decoupled across OS processes:

```text
┌────────────────────────────────────────────────────────┐       ┌────────────────────────────────────────────────────────┐
│            PROCESS A: INTERACTIVE MINT TOOL            │       │               PROCESS B: VERIFY-ONLY RUNNER            │
│         (tools/governance/mint_human_go_record.py)     │       │               (src/acash/gate_b/runner.py)             │
├────────────────────────────────────────────────────────┤       ├────────────────────────────────────────────────────────┤
│ • Interactive TTY Execution ONLY (Human Presence)      │       │ • Automated pipeline execution                         │
│ • Asserts sys.stdin.isatty() == True                   │       │ • Zero private key capability in dependency closure    │
│ • Interactive Operator Challenge-Token prompt          │       │ • Ingests confirmation token via CLI argument          │
│ • Loads sovereign private key from secure external path│       │ • Strictly Verify-Only                                 │
│ • Signs canonical HumanGORecord payload                │       │ • Ingests pre-existing artifact file from disk         │
│ • Writes human_go_record.json artifact to disk         │       │ • LACKS signing / keygen APIs                          │
│ • LACKS ledger mutation APIs                           │       │ • Ingests sealed trust store (Read-Only)               │
│ • LACKS trust-store write APIs                         │       │ • Executes 2PC commit under single continuous lock     │
│ • PROCESS EXITS IMMEDIATELY                            │       │ • Immediate Halt: STOP AGAIN (Live capital = $0.00)    │
└────────────────────────────────────────────────────────┘       └────────────────────────────────────────────────────────┘
                            │                                                                 ▲
                            │                    PERSISTED ARTIFACT ONLY                      │
                            └──────────────────── var/gate_b/governance/ ─────────────────────┘
                                                 human_go_record.json
```

### 6.2 Human-Presence Requirement (Finding R3-4 Resolution)
To guarantee that the Mint Tool cannot be spawned silently or driven by an automated caller, CI runner, or background daemon:
1. **Interactive TTY Enforcement:** The Mint Tool explicitly checks:
   ```python
   if not (sys.stdin.isatty() and sys.stdout.isatty()):
       raise GovernanceSecurityError("MINT_TOOL_REQUIRES_INTERACTIVE_TTY_HUMAN_PRESENCE")
   ```
2. **Interactive Confirmation Challenge:** The operator must manually input the approved confirmation token (e.g. `P13-GATE-B-EXECUTION-GO-20260905`) interactively. The tool refuses automated piped stdin (`sys.stdin.read()` without TTY) and fails closed if piped.
3. **External Key Protection:** The sovereign private key is never stored in the repository, never committed to git, and never accessible via default environment variables. It must be provided via a secure offline path, hardware key, or operator-entered decryption passphrase during the interactive ceremony.
4. **Immediate Exit:** Once the single `human_go_record.json` artifact is written and flushed, Process A exits immediately with code 0.

### 6.3 Transitive Capability Isolation (Finding R3-3 Resolution)
The Runner's capability boundary is not merely syntactic (checking AST of `runner.py`). The Runner's **entire transitive dependency closure** must be free of key-generation, signing, or trust-mutation capabilities:
- **Capability Allowlist:** The runner and its imported modules may only import verification components (`Ed25519Verifier`, schema validation, storage read/commit utilities).
- **Prohibited Symbol Closure:** No module reachable in `sys.modules` from `acash.gate_b.runner` may export:
  - `Ed25519Signer`
  - `generate_key_pair`
  - `from_private_bytes`
  - Trust store write or modification functions
- This invariant is enforced at runtime and verified by automated static and runtime dependency closure tests (`Test B14`).

### 6.4 Capability Boundary Matrix
| Capability | Process A: Interactive Mint Tool | Process B: Verify-Only Runner |
| :--- | :---: | :---: |
| **Interactive TTY Required** | **MANDATORY (`isatty() == True`)** | Not Required (Automated / Pipeline) |
| **Load Sovereign Private Key** | **PERMITTED** (Operator Ceremony) | ⛔ **PROHIBITED (Zero Key Capability)** |
| **Sign `HumanGORecord`** | **PERMITTED** | ⛔ **PROHIBITED (Verify-Only)** |
| **Generate Keypairs (`generate_key_pair`)**| ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Write `trust_store.json`** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Import Storage Write APIs** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Post-Verification 2PC)** |
| **Advance Ledger Head** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Stage 8 2PC Commit)** |
| **Broker Order Dispatch** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED (Slice 3 Blocked)** |

---

## 7. Full Operational Context Binding in `HumanGORecord`

The canonical payload signed by the Human Auditor binds all operational parameters to prevent replay, transposition, or stale head execution:

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

## 8. Adversarial Verification Plan (17 Hard Boundary Tests)

The adversarial test suite (`tests/unit/gate_b/test_gate_b_governance_repair.py`) attacks every capability boundary, cryptographic signature, and environmental invariant:

| Test Identifier | Adversarial Attack Scenario | Expected Fail-Closed Assertion |
| :--- | :--- | :--- |
| **Test B1: Runner Direct AST Ban** | Inspect `src/acash/gate_b/runner.py` AST for keypair generation calls | Audit fails; zero key generation functions exist in runner module |
| **Test B2: Runner Trust Store Overwrite** | Runner attempts `write_file_durable` on `trust_store.json` | Fails closed with OS `PermissionError` / `StorageDurabilityError` |
| **Test B3: Trust Store DACL Modification** | Runner attempts `icacls` or `SetFileSecurityW` to grant write access | Fails closed with OS `ERROR_ACCESS_DENIED` |
| **Test B4: Trust Store Replacement Attack** | Runner creates `temp.json` and calls `os.replace` on `trust_store.json` | Fails closed with OS `PermissionError` |
| **Test B5: Trust Store Tampering (Integrity)** | Mutate 1 bit in `trust_store.json` without modifying manifest | Fails closed: `TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID` |
| **Test B6: Unknown Approver Key** | `HumanGORecord` signed by key not in `trust_anchor_manifest.json` | Fails closed: `DomainValidationError: unknown key_id` |
| **Test B7: Revoked Approver Key** | Approver key status is `REVOKED` in sealed trust store | Fails closed: `DomainValidationError: key has been REVOKED` |
| **Test B8: Expired Authorization Record** | Runner executed when `current_time > expires_at_utc` | Fails closed: `PreLiveRiskAdmissionError: HUMAN_GO_EXPIRED` |
| **Test B9: Stale Ledger Head Continuity** | `previous_record_digest` references incident head (`81f4d44a...`) | Fails closed: `DataContractError: LEDGER_HEAD_CONTINUITY_BROKEN` |
| **Test B10: Post-Sign Draft Tampering** | Mutate 1 character in `authorization.json` after record signed | Fails closed: `DataContractError: DRAFT_DIGEST_MISMATCH` |
| **Test B11: Genesis Manifest Missing / Tampered**| Delete or tamper `genesis_bootstrap_manifest.json` in fresh root | Fails closed: `DataContractError: GENESIS_ENVIRONMENT_UNVERIFIED` |
| **Test B12: In-Memory Synthetic Record Bypass**| Pass mock dictionary or in-memory model to runner instead of file | Fails closed: `DataContractError: ARTIFACT_FILE_REQUIRED` |
| **Test B13: Mint Tool Execution Boundary** | Invoke mint tool with runner arguments or attempted ledger writes | Fails closed; mint tool lacks storage mutation classes |
| **Test B14: Transitive Dependency Capability Audit** | Inspect entire recursive module closure of runner for signing/keygen | Fails closed if any module in closure exports `Ed25519Signer` or keygen |
| **Test B15: Trust Anchor Sovereign Signature Check** | Mutate manifest or sign with untrusted sovereign root key | Fails closed: `TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID` |
| **Test B16: Genesis Bootstrap Signature Check** | Mutate genesis manifest or sign with untrusted bootstrap key | Fails closed: `GENESIS_ENVIRONMENT_UNVERIFIED` |
| **Test B17: Mint Tool Human Presence Non-TTY Ban** | Run mint tool in non-TTY pipe / headless subshell | Fails closed: `MINT_TOOL_REQUIRES_INTERACTIVE_TTY_HUMAN_PRESENCE` |

---

## 9. Execution Phasing & Acceptance Criteria

The repair proceeds through three strictly gated steps. Advancing between steps requires explicit human auditor sign-off:

```text
Step 1: Formal Audit Approval of this Plan (Rev 4)
  │
  ▼
Step 2: Implement Tooling & Architectural Hardening (Zero Activation)
  ├─ tools/governance/mint_human_go_record.py (Process A with TTY Human Presence)
  ├─ src/acash/gate_b/runner.py (Process B Verify-Only with Transitive Boundary)
  ├─ tests/unit/gate_b/test_gate_b_governance_repair.py (17 Adversarial Tests)
  └─ Verification Criterion: ALL REPOSITORY TESTS PASS (Pre-repair baseline + new tests clean; MyPy clean)
  │
  ▼
Step 3: Governance Ceremonies & Storage Re-initialization
  ├─ Archive var/gate_b -> var/gate_b_incident_archive (Option 2)
  ├─ Execute Genesis Bootstrap Ceremony -> Sovereign signs genesis_bootstrap_manifest.json
  ├─ Execute Trust Anchor Ceremony -> Sovereign signs trust_anchor_manifest.json & seals trust_store.json
  ├─ Execute Process A (Interactive Mint Tool) -> Human Auditor signs human_go_record.json
  └─ Human Audit Review of Fresh Activation Pack on GitHub
  │
  ▼
Step 4: Fresh Authoritative Gate B Activation Execution
  ├─ Process B (Verify-Only Runner) executes Stages 1–9 under single continuous lock
  ├─ Verify COMMITTED on fresh root
  └─ Immediate Halt: STOP AGAIN (Live capital = $0.00; Live orders = 0)
```

> [!NOTE]
> **Acceptance Criterion Language:**  
> "All repository tests pass; exact count reported from actual execution. No regression from pre-repair baseline. Static type checker (MyPy) reports 0 errors across all source files."

---

## 10. Approval Sign-Off Block

```markdown
════════════════════════════════════════════════════════════════════════════════
    GATE B GOVERNANCE REPAIR PLAN (REV 4) — FORMAL AUDIT APPROVAL
════════════════════════════════════════════════════════════════════════════════

Governing Document:       docs/phase13/gate_b_governance_repair_plan.md (Rev 4)
Parent Incident Report:   docs/phase13/gate_b_forensic_reconciliation_report.md
Storage Resolution Mode:  OPTION 2: FORENSIC ARCHIVE & FRESH GENESIS ROOT
Incident Archive Path:    var/gate_b_incident_archive/ (Immutable NTFS Deny DACL)
Genesis Authority:        genesis_bootstrap_manifest.json (Ed25519 Sovereign Signed)
Trust Anchor Authority:   trust_anchor_manifest.json (Ed25519 Sovereign Signed)
OS Capability Contract:   Governance Owner, Non-Elevation, Anti-Replacement DACL
Transitive Isolation:     Runner Import Closure has ZERO Signing/Keygen Symbols
Human Presence:           Process A Requires Interactive TTY & Manual Token Entry
Live Capital Authority:   $0.00 (Zero Capital Deployed)
Broker Execution:         PROHIBITED (Slice 3 Strictly Blocked)

Auditor Decision:         [ PENDING REVIEW / APPROVED / REVISION REQUIRED ]

Human Governance Auditor: _______________________________________________

Date & Time (UTC):        _______________________________________________

Decision Token:           _______________________________________________
════════════════════════════════════════════════════════════════════════════════
```
