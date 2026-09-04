# Phase 13: Gate B Governance Repair Plan (Formal Specification — Revision 5)

**Document ID:** `ACASH-DOC-P13-GATE-B-GOVERNANCE-REPAIR-PLAN-REV5`  
**Parent Incident Report:** `docs/phase13/gate_b_forensic_reconciliation_report.md` (Commit `affc5ce`)  
**Governing Specification Baseline:** `docs/phase13/slice2_gate_b_plan.md` (Rev 20 Frozen Baseline, Spec Commit `647ba75`)  
**Auditor Review Baseline:** Human Auditor Review of Rev 4 (Resolving Blockers R4-1, R4-2, and Findings R4-3, R4-4)  
**Current System State:**  
- Transaction Persistence: `COMMITTED` (Incident transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` on physical NTFS)  
- Authorization Provenance: `INVALID` (Self-authorizing runtime runner loop)  
- Governance State: `QUARANTINED / NOT AUTHORIZED`  
- Trading Authority: `STRICTLY BLOCKED`  
- Live Capital Deployed: `$0.00`  
- Live Orders Transmitted: `0`  
- Broker Connection: `DISCONNECTED`  
**Document Status:** REVISION 5 — SUBMITTED FOR FORMAL AUDIT APPROVAL (ZERO EXECUTION / ZERO CODE MUTATION)

---

## 1. Executive Summary & Problem Remediation

During the Gate B activation attempt on 2026-09-05, the runner script committed transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` via a **circular self-authorizing loop**: the runner generated its own Ed25519 human governance keypair at runtime, wrote its own public key into a new trust store, fabricated a `HumanGORecord`, signed the record with its own private key, verified the signature against its own trust store, and hardcoded the confirmation token into evidence.

While the physical storage mechanics (two-phase commit, fsync barriers, CAS elevations, pointer transitions, NTFS DACL) executed correctly as software code, the **governance provenance is mathematically and organizationally invalid**.

In Revision 4, the architecture introduced Ed25519 digital signatures on manifests, process separation, and dynamic test counting. However, audit review of Revision 4 identified four critical boundaries that remained underspecified:
1. **TTY Presence $\neq$ Human Presence:** A pseudo-terminal (PTY / ConPTY) or automated subshell can satisfy `isatty() == True` and supply tokens programmatically.
2. **`sys.modules` $\neq$ Full Dependency Closure:** Runtime module inspection only audits loaded modules in a specific execution path; lazy, conditional, or dynamic imports are invisible to `sys.modules`.
3. **Sovereign Root-of-Root Governance:** The provenance, pinning, and change-control gates governing the compiled Root Anchor itself were not formally specified.
4. **Deny ACE $\neq$ Privilege Isolation:** File-level Deny ACEs can be bypassed if the runner process token holds Windows administrative privileges (`SeTakeOwnershipPrivilege`, `SeRestorePrivilege`).

This Revision 5 Governance Repair Plan formally resolves all four gaps:
- **Authenticated Human Authorization Ceremony (Blocker R4-1 Resolution):** Replaces TTY presence with an external out-of-band authenticated ceremony. TTY is retained strictly as anti-pipe hygiene, not proof of human identity. Key unlocking requires an external human factor (hardware token / out-of-band passphrase) unavailable to automated host runners.
- **Full Static Recursive Dependency Closure Audit (Blocker R4-2 Resolution):** Replaces runtime `sys.modules` checks with a static AST recursive import closure audit analyzing direct, transitive, lazy, and dynamic imports. Enforces an absolute capability ban on private key loading, key generation, signing, and trust-store mutation in the runner's dependency graph.
- **Sovereign Root-of-Root Governance Specification (Finding R4-3 Resolution):** Defines the formal provenance of the Sovereign Root Anchor, pinned to the audited executable release identity (`commit_sha`, reproducible build manifest), rejecting any runtime injection or tampering.
- **Windows Process Token Privilege Boundary (Finding R4-4 Resolution):** Formally restricts the Runner process identity to an unprivileged standard token, verifying that `SeTakeOwnershipPrivilege`, `SeRestorePrivilege`, and elevation tokens are absent before Stage 1 execution.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      GOVERNANCE REPAIR ARCHITECTURE (REVISION 5)                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. INCIDENT FORENSIC ARCHIVE (Mandatory Option 2):                                     │
│    var/gate_b/ ──> var/gate_b_incident_archive/ (Immutable NTFS Deny DACL)             │
│    (Tx 339ce2fd-... remains COMMITTED in archive; authorization provenance INVALID)    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. PINNED SOVEREIGN ROOT ANCHOR (Root-of-Root Governance):                             │
│    - Generated in offline hardware ceremony; pinned to audited release commit SHA      │
│    - Runner verifies pinned anchor against release manifest; rejects runtime mutation │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. EXTERNAL SOVEREIGN CEREMONIES (Signed Manifest Roots):                              │
│    - External Bootstrap Authority signs genesis_bootstrap_manifest.json (Ed25519)     │
│    - Sovereign Authority signs trust_anchor_manifest.json (Ed25519)                    │
│    - Ingests sealed public keys into var/gate_b/trust_store.json                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. PROCESS A: AUTHENTICATED HUMAN AUTHORIZATION CEREMONY (Interactive Mint Tool):      │
│    - Anti-pipe TTY check (hygiene only; NOT treated as human proof)                    │
│    - Requires out-of-band human authentication factor (external passphrase / token)    │
│    - Signs canonical HumanGORecord payload with Sovereign Approver Key                 │
│    - Lacks ledger mutation APIs; lacks trust-store mutation APIs; exits immediately    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. PROCESS B: VERIFY-ONLY RUNNER (Zero-Capability Dependency Closure):                 │
│    - Unprivileged Windows Process Token (No SeTakeOwnership, No SeRestore, No Admin)   │
│    - Static AST Dependency Closure Audit verifies ZERO signing/keygen/trust-write code │
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

## 3. Authoritative Genesis Bootstrap Manifest

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

## 4. Cryptographic Trust-Store Provenance & Sovereign Root-of-Root Governance

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
2. Extract `sovereign_signer_key_id` and match against the pinned Sovereign Root Anchor.
3. Cryptographically verify `sovereign_signature_ed25519` over `compute_canonical_signed_bytes()` using the pinned Sovereign Root Public Key.
4. Compute `actual_trust_store_digest = sha256(read_bytes(var/gate_b/trust_store.json))`.
5. Assert `actual_trust_store_digest == manifest.trust_store_digest`.
6. Assert all required key IDs (`KEY_HUMAN_GOVERNANCE_AUDITOR_001`, `KEY_STORAGE_ENGINE_PROD_001`) exist in `manifest.trust_store_key_ids`.
7. If signature fails, digest mismatches, or required keys are missing $\to$ Raise `DataContractError: TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID` (Fail-Closed).
8. Only upon 100% cryptographic verification of the manifest does the runner load `trust_store.json`.

### 4.3 Sovereign Root-of-Root Governance Specification (Finding R4-3 Resolution)
To guarantee that the Root Anchor itself cannot be replaced, altered, or injected during runtime:
1. **Provenance:** The Sovereign Root Keypair is generated during an offline, air-gapped Sovereign Key Generation Ceremony. The private key never exists on any network-connected host or runner filesystem.
2. **Release Identity Pinning:** The public key of the Sovereign Root Anchor is cryptographically bound to the **Audited Executable Release Identity**:
   $$\text{RootPin} = \left(\text{root\_key\_id}, \text{root\_pubkey\_hex}, \text{release\_commit\_sha}, \text{release\_manifest\_digest}\right)$$
   The release identity is frozen in immutable compiled code (`acash.governance.root_anchor`) and signed in the Git release tag.
3. **Change-Control Policy:** Altering the pinned Root Anchor requires:
   - Formal Multi-Party Key Ceremony documented in a signed ceremony ledger.
   - Re-audit of the entire repository governance chain.
   - New signed release commit tag.
4. **Runtime Immutability:** The Runner strictly prohibits loading or overriding the Root Anchor from:
   - Environment variables (`ACASH_ROOT_KEY_OVERRIDE`, etc. $\to$ Hard Exception).
   - Dynamic command-line flags.
   - Local filesystem or mutable configuration files.
   If the pinned root anchor diverges from the compiled release manifest, the Runner immediately raises `DataContractError: SOVEREIGN_ROOT_ANCHOR_TAMPERED` (Fail-Closed).

---

## 5. OS-Level Capability & Token Privilege Boundary (Finding R4-4 Resolution)

Application-level absence of write methods is insufficient if OS access controls or process privileges permit modification. The repair enforces both filesystem DACLs and process token restrictions:

### 5.1 Identity & Ownership Separation (DACL Layer)
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

### 5.2 Windows Token Privilege Boundary (Finding R4-4 Resolution)
A file-level Deny ACE is bypassed if the running process holds administrative privileges (e.g. `SeTakeOwnershipPrivilege` allows taking ownership despite Deny ACEs; `SeRestorePrivilege` allows bypassing DACL write checks). To guarantee that the kernel boundary cannot be defeated:
1. **Unprivileged Service Identity:** The Runner MUST execute under a dedicated unprivileged standard user token (`acash_runner_svc`), NOT `Administrator`, NOT member of `BUILTIN\Administrators`, and NOT `NT AUTHORITY\SYSTEM`.
2. **Restricted Privilege Token:** The Runner process token MUST NOT hold any of the following Windows privileges:
   - `SeTakeOwnershipPrivilege` (Bans taking ownership of governance files)
   - `SeRestorePrivilege` (Bans DACL-bypass write operations)
   - `SeBackupPrivilege` (Bans DACL-bypass read operations)
   - `SeSecurityPrivilege` (Bans audit policy / SACL manipulation)
   - `SeDebugPrivilege` (Bans cross-process inspection or memory injection)
   - `SeTcbPrivilege` (Bans acting as part of the operating system)
3. **Pre-Flight Token Inspection (Stage 1 Invariant):** At startup, before performing any operation, the Runner inspects its Win32 process token via `GetTokenInformation(TokenPrivileges)` and `GetTokenInformation(TokenElevation)`:
   - If `TokenIsElevated == True` $\to$ Halt immediately (`GovernanceSecurityError: RUNNER_PROCESS_TOKEN_ELEVATED`).
   - If any restricted privilege is enabled or present in token $\to$ Halt immediately (`GovernanceSecurityError: RESTRICTED_TOKEN_PRIVILEGES_DETECTED`).
   - Asserts that attempting `TakeOwnership` or `WRITE_DAC` returns `ERROR_ACCESS_DENIED` or `ERROR_PRIVILEGE_NOT_HELD`.

---

## 6. Process-Level Separation & Authenticated Human Authorization Ceremony

### 6.1 Process Separation: Mint Tool vs Activation Runner
To eliminate shared memory space or runtime object reuse between authorization creation and authorization consumption, the two roles are physically decoupled across OS processes:

```text
┌────────────────────────────────────────────────────────┐       ┌────────────────────────────────────────────────────────┐
│            PROCESS A: INTERACTIVE MINT TOOL            │       │               PROCESS B: VERIFY-ONLY RUNNER            │
│         (tools/governance/mint_human_go_record.py)     │       │               (src/acash/gate_b/runner.py)             │
├────────────────────────────────────────────────────────┤       ├────────────────────────────────────────────────────────┤
│ • Interactive TTY Execution ONLY (Anti-Pipe Hygiene)   │       │ • Automated pipeline execution                         │
│ • Asserts sys.stdin.isatty() == True                   │       │ • Unprivileged Windows Process Token                   │
│ • Authenticated Human Authorization Ceremony           │       │ • Static Dependency Closure: ZERO signing/keygen code  │
│ • External Human Factor (Hardware / Out-of-Band Pass)  │       │ • Ingests confirmation token via CLI argument          │
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

### 6.2 Authenticated Human Authorization Ceremony (Blocker R4-1 Resolution)
Auditing established that interactive TTY checks (`isatty()`) only verify the absence of basic I/O redirection; automated tools can easily allocate a pseudo-terminal (PTY / ConPTY) to satisfy `isatty()`.

Therefore, **TTY presence is classified strictly as anti-pipe hygiene, NOT proof of human presence or authorization**.

True human authorization is established via an **Authenticated Human Authorization Ceremony**:
1. **Out-of-Band Human Authentication Factor:** The Sovereign Human Private Key is encrypted at rest and can ONLY be decrypted via an out-of-band factor held exclusively by the Human Governance Auditor:
   - Hardware token PIN (e.g. FIDO2 / YubiKey physical touch), OR
   - High-entropy cryptographic passphrase entered interactively by the human auditor at the console during the ceremony.
2. **Zero Automated Availability:** The key material cannot be decrypted by any automated script, background process, or CI runner because the unlocking secret does NOT reside anywhere in environment variables, configuration files, or the host filesystem.
3. **Anti-Automation Resistance:** The Mint Tool enforces a challenge-response interaction where the auditor must confirm the Gate A digest, target account, and limits before signature emission. An automated process allocating a PTY cannot bypass the requirement for the external physical/passphrase secret.
4. **Immediate Process Termination:** Once the single `human_go_record.json` artifact is signed and flushed, the process clears all in-memory key buffers and exits immediately with code 0.

### 6.3 Static Recursive Dependency Closure Audit (Blocker R4-2 Resolution)
Auditing established that inspecting runtime `sys.modules` does NOT prove capability isolation: modules loaded lazily, conditionally (`if condition: import ...`), or via untraversed code paths do not appear in `sys.modules`.

Therefore, runtime `sys.modules` inspection is replaced by an **Authoritative Static Recursive AST Dependency Closure Audit**:
1. **Static AST Analysis Algorithm:**
   - Parse the AST of `acash.gate_b.runner` and extract all `ast.Import`, `ast.ImportFrom`, and calls to dynamic import functions (`importlib.import_module`, `__import__`).
   - Transitively resolve and parse every internal codebase module reachable from the runner's root import graph.
   - Build the complete static directed dependency graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$.
2. **Prohibited Capability Ban:**
   No node in $\mathcal{G}$ reachable from `acash.gate_b.runner` may contain, import, or re-export:
   - `Ed25519Signer`
   - `generate_key_pair`
   - `from_private_bytes`
   - Private key loading utilities or file decrypters
   - Trust-store write or modification utilities
   - File deletion or replacement APIs targeting trust-store paths
3. **Dynamic Import Prohibition:**
   The runner codebase strictly prohibits non-literal dynamic imports (`importlib.import_module(variable)`) that could obscure the static dependency graph. Any dynamic import detected in the runner closure triggers an immediate static audit failure.
4. **Complementary Runtime Verification:**
   In addition to the static AST audit, the test suite verifies that `Ed25519Signer` and key generation symbols are absent from `acash.gate_b.runner.__dict__` and never instantiated during execution.

### 6.4 Capability Boundary Matrix
| Capability | Process A: Interactive Mint Tool | Process B: Verify-Only Runner |
| :--- | :---: | :---: |
| **Interactive TTY Required** | **MANDATORY (Anti-Pipe Hygiene)** | Not Required (Automated / Pipeline) |
| **Out-of-Band Human Factor** | **MANDATORY (Passphrase / Hardware PIN)** | ⛔ **PROHIBITED (Zero Key Material)** |
| **Load Sovereign Private Key**| **PERMITTED** (Decrypted by Human Factor) | ⛔ **PROHIBITED (Zero Key Capability)** |
| **Sign `HumanGORecord`** | **PERMITTED** | ⛔ **PROHIBITED (Verify-Only)** |
| **Generate Keypairs (`generate_key_pair`)**| ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Write `trust_store.json`** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Import Storage Write APIs** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Post-Verification 2PC)** |
| **Advance Ledger Head** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Stage 8 2PC Commit)** |
| **Broker Order Dispatch** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED (Slice 3 Blocked)** |
| **OS Token Privilege** | Standard Operator Token | **Unprivileged Token (No Admin/Takeover)** |

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

## 8. Adversarial Verification Plan (20 Hard Boundary Tests)

The adversarial test suite (`tests/unit/gate_b/test_gate_b_governance_repair.py`) attacks every capability boundary, cryptographic signature, static dependency path, and OS privilege invariant:

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
| **Test B14: Full Static Recursive AST Closure Audit** | Parse full recursive import graph of runner; inspect all dependencies | Fails closed if ANY reachable module exports signing/keygen capability |
| **Test B15: Trust Anchor Sovereign Signature Check** | Mutate manifest or sign with untrusted sovereign root key | Fails closed: `TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID` |
| **Test B16: Genesis Bootstrap Signature Check** | Mutate genesis manifest or sign with untrusted bootstrap key | Fails closed: `GENESIS_ENVIRONMENT_UNVERIFIED` |
| **Test B17: Anti-Pipe & PTY Automation Ban** | Run mint tool in non-TTY pipe or automated pseudo-console without human factor | Fails closed: `MINT_TOOL_REQUIRES_AUTHENTICATED_HUMAN_CEREMONY` |
| **Test B18: Sovereign Root Anchor Tampering Ban** | Mutate compiled root anchor or inject environment override | Fails closed: `DataContractError: SOVEREIGN_ROOT_ANCHOR_TAMPERED` |
| **Test B19: Runner Windows Process Token Audit**| Run runner under elevated token or with restricted privileges present | Fails closed: `GovernanceSecurityError: RUNNER_PROCESS_TOKEN_PRIVILEGED` |
| **Test B20: File Owner Takeover & Privilege Escalation** | Attempt to take ownership of trust store or modify security descriptor | Fails closed: `ERROR_ACCESS_DENIED` / `ERROR_PRIVILEGE_NOT_HELD` |

---

## 9. Execution Phasing & Acceptance Criteria

The repair proceeds through four strictly gated steps. Advancing between steps requires explicit human auditor sign-off:

```text
Step 1: Formal Audit Approval of this Plan (Rev 5)
  │
  ▼
Step 2: Implement Tooling & Architectural Hardening (Zero Activation)
  ├─ tools/governance/mint_human_go_record.py (Process A: Authenticated Human Ceremony)
  ├─ src/acash/gate_b/runner.py (Process B: Verify-Only with Static Closure Isolation & Token Audit)
  ├─ tests/unit/gate_b/test_gate_b_governance_repair.py (20 Adversarial Tests)
  └─ Verification Criterion: ALL REPOSITORY TESTS PASS (Pre-repair baseline + new tests clean; MyPy clean)
  │
  ▼
Step 3: Governance Ceremonies & Storage Re-initialization
  ├─ Archive var/gate_b -> var/gate_b_incident_archive (Option 2)
  ├─ Execute Genesis Bootstrap Ceremony -> Sovereign signs genesis_bootstrap_manifest.json
  ├─ Execute Trust Anchor Ceremony -> Sovereign signs trust_anchor_manifest.json & seals trust_store.json
  ├─ Execute Authenticated Human Authorization Ceremony -> Auditor signs human_go_record.json
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
    GATE B GOVERNANCE REPAIR PLAN (REV 5) — FORMAL AUDIT APPROVAL
════════════════════════════════════════════════════════════════════════════════

Governing Document:       docs/phase13/gate_b_governance_repair_plan.md (Rev 5)
Parent Incident Report:   docs/phase13/gate_b_forensic_reconciliation_report.md
Storage Resolution Mode:  OPTION 2: FORENSIC ARCHIVE & FRESH GENESIS ROOT
Incident Archive Path:    var/gate_b_incident_archive/ (Immutable NTFS Deny DACL)
Root Anchor Governance:   Pinned to Audited Release Identity (Zero Runtime Override)
Genesis Authority:        genesis_bootstrap_manifest.json (Ed25519 Sovereign Signed)
Trust Anchor Authority:   trust_anchor_manifest.json (Ed25519 Sovereign Signed)
OS Capability Contract:   Governance Owner, Non-Elevation, Anti-Replacement DACL
Windows Token Boundary:   Unprivileged Runner Token (No SeTakeOwnership/SeRestore/Admin)
Static Closure Isolation: Static AST Dependency Graph: ZERO Signing/Keygen/Write Symbols
Human Authorization:      Authenticated Ceremony with Out-of-Band Human Factor
Live Capital Authority:   $0.00 (Zero Capital Deployed)
Broker Execution:         PROHIBITED (Slice 3 Strictly Blocked)

Auditor Decision:         [ PENDING REVIEW / APPROVED / REVISION REQUIRED ]

Human Governance Auditor: _______________________________________________

Date & Time (UTC):        _______________________________________________

Decision Token:           _______________________________________________
════════════════════════════════════════════════════════════════════════════════
```
