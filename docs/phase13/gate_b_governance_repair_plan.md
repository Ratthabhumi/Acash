# Phase 13: Gate B Governance Repair Plan (Formal Specification — Revision 6)

**Document ID:** `ACASH-DOC-P13-GATE-B-GOVERNANCE-REPAIR-PLAN-REV6`  
**Parent Incident Report:** `docs/phase13/gate_b_forensic_reconciliation_report.md` (Commit `affc5ce`)  
**Governing Specification Baseline:** `docs/phase13/slice2_gate_b_plan.md` (Rev 20 Frozen Baseline, Spec Commit `647ba75`)  
**Auditor Review Baseline:** Human Auditor Review of Rev 5 (Resolving Blockers R5-1, R5-2, and Finding R5-3)  
**Current System State:**  
- Transaction Persistence: `COMMITTED` (Incident transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` on physical NTFS)  
- Authorization Provenance: `INVALID` (Self-authorizing runtime runner loop)  
- Governance State: `QUARANTINED / NOT AUTHORIZED`  
- Trading Authority: `STRICTLY BLOCKED`  
- Live Capital Deployed: `$0.00`  
- Live Orders Transmitted: `0`  
- Broker Connection: `DISCONNECTED`  
**Document Status:** REVISION 6 — SUBMITTED FOR FORMAL AUDIT APPROVAL (ZERO EXECUTION / ZERO CODE MUTATION)

---

## 1. Executive Summary & Problem Remediation

During the Gate B activation attempt on 2026-09-05, the runner script committed transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` via a **circular self-authorizing loop**: the runner generated its own Ed25519 human governance keypair at runtime, wrote its own public key into a new trust store, fabricated a `HumanGORecord`, signed the record with its own private key, verified the signature against its own trust store, and hardcoded the confirmation token into evidence.

While the physical storage mechanics (two-phase commit, fsync barriers, CAS elevations, pointer transitions, NTFS DACL) executed correctly as software code, the **governance provenance is mathematically and organizationally invalid**.

In Revision 5, the architecture introduced out-of-band human authentication, static dependency closure audits, and Windows token privilege boundaries. However, audit review of Revision 5 identified that the root-of-root trust chain remained incomplete:
1. **Unsigned Release Manifest (Blocker R5-1):** The release manifest binding the commit SHA and root anchor was not cryptographically authenticated by an External Release Authority, leaving open the risk of self-consistent forged packages.
2. **Runtime Trust Root Selection (Blocker R5-2):** The runner lacked an immutable bootstrap anchor, creating the risk that the runner determines "who to trust" from local runtime files.
3. **Host Passphrase Insufficiency:** A passphrase entered on the host console is vulnerable to automated replay if compromised; only hardware-backed user presence provides true anti-automation guarantees.
4. **Mathematical Honesty on Dependency Analysis:** Static AST analyzers cannot prove dynamic runtime behavior of lazy imports; unsupported dynamic imports must be strictly prohibited rather than assumed safe.
5. **Real OS Integration Evidence (Finding R5-3):** OS privilege boundaries (B19/B20) must be proven on actual Win32 tokens and NTFS substrates, not merely mocked Python objects.

This Revision 6 Governance Repair Plan establishes a **complete, non-circular, cryptographically sealed trust hierarchy** from an External Release Authority down to the physical two-phase commit:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   CANONICAL ROOT-OF-ROOT TRUST BOOTSTRAP HIERARCHY                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. IMMUTABLE EXTERNAL RELEASE TRUST ANCHOR:                                            │
│    - External Release Authority Public Key: RELEASE_AUTHORITY_ROOT_PUBLIC_KEY          │
│    - Pinned immutably in compiled release verification bootstrap                       │
│                                │                                                       │
│                                ▼ verifies signature                                    │
│ 2. SIGNED RELEASE MANIFEST (release_manifest.json):                                    │
│    - Signed via Ed25519 by External Release Authority                                  │
│    - Binds: release_commit_sha, executable_tree_digest, sovereign_root_anchor_digest   │
│    - Asserts actual codebase tree SHA-256 == manifest.executable_tree_digest            │
│    - Asserts actual commit SHA == manifest.release_commit_sha                           │
│                                │                                                       │
│                                ▼ validates authentic anchor                            │
│ 3. PINNED SOVEREIGN ROOT ANCHOR (sovereign_root_anchor.json):                          │
│    - Validated against signed release_manifest.sovereign_root_anchor_digest            │
│    - Contains SOVEREIGN_ROOT_PUBLIC_KEY and BOOTSTRAP_AUTHORITY_PUBLIC_KEY             │
│                                │                                                       │
│             ┌──────────────────┴──────────────────┐                                    │
│             ▼ verifies signature                  ▼ verifies signature                 │
│ 4. TRUST ANCHOR MANIFEST:             5. GENESIS BOOTSTRAP MANIFEST:                   │
│    - Signed by Sovereign Root             - Signed by Bootstrap Authority              │
│    - Binds SHA-256 of trust_store.json    - Binds Genesis head & incident archive tree │
│             │                                     │                                    │
│             ▼ references digest                   ▼ validates fresh storage root       │
│ 6. SEALED TRUST STORE (trust_store.json) 7. FRESH GENESIS ROOT (var/gate_b/)           │
│    - Registered Approver Public Keys      - Head digest: "00000...00000"               │
│             │                                                                          │
│             ▼ verifies signature                                                       │
│ 8. AUTHENTICATED HUMAN GO RECORD (human_go_record.json):                               │
│    - Signed via Hardware-Backed User-Presence Ceremony (FIDO2 / YubiKey physical touch)│
│    - Bound to Gate A digest, account, limits, and fresh Genesis head                   │
│                                │                                                       │
│                                ▼ ingested & verified by                                │
│ 9. VERIFY-ONLY RUNNER (Process B):                                                     │
│    - Real Unprivileged Windows Token (No SeTakeOwnership, No SeRestore, No Admin)      │
│    - Static AST Dependency Closure: ZERO signing/keygen/trust-write symbols            │
│    - Single uninterrupted exclusive transactional lock (Stages 6–8) ──> 2PC Commit     │
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

## 3. Signed Release Manifest & Non-Circular Root-of-Root Trust Chain (Blockers R5-1 & R5-2 Resolution)

To guarantee that the Runner never determines "who to trust" from unverified local files, trust is anchored in an **Immutable External Release Trust Anchor** that validates a **Signed Release Manifest**.

### 3.1 `ReleaseManifest` Schema (Blocker R5-1 Resolution)
```python
class ReleaseManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int = Field(default=1, description="Schema version.")
    release_tag: str = Field(description="Audited release tag, e.g. v1.0.0-gate-b.")
    release_commit_sha: str = Field(description="Exact Git commit SHA of frozen release baseline.")
    executable_tree_digest: str = Field(
        description="Canonical SHA-256 tree digest of audited codebase source files."
    )
    sovereign_root_anchor_digest: str = Field(
        description="Exact SHA-256 digest of sovereign_root_anchor.json."
    )
    release_timestamp_utc: datetime = Field(description="UTC timestamp of release authorization.")
    release_authority_key_id: str = Field(
        description="Key ID of the External Release Authority."
    )
    release_authority_signature_ed25519: str = Field(
        description="Hex-encoded Ed25519 signature over canonical release manifest payload."
    )

    def compute_canonical_signed_bytes(self) -> bytes:
        """Compute canonical JSON bytes over manifest fields excluding the signature."""
        payload = {
            "manifest_version": self.manifest_version,
            "release_tag": self.release_tag,
            "release_commit_sha": self.release_commit_sha,
            "executable_tree_digest": self.executable_tree_digest,
            "sovereign_root_anchor_digest": self.sovereign_root_anchor_digest,
            "release_timestamp_utc": self.release_timestamp_utc.isoformat(),
            "release_authority_key_id": self.release_authority_key_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

### 3.2 Non-Circular Root-of-Root Bootstrap Chain (Blocker R5-2 Resolution)
The Runner's bootstrap sequence proceeds strictly downward through non-circular verification gates:

```text
Runner Startup (Stage 1 Pre-Flight)
   │
   ├─ 1. Locate release_manifest.json (Immutable build artifact)
   │
   ├─ 2. Extract release_authority_key_id; match against compiled RELEASE_AUTHORITY_ROOT_PUBLIC_KEY
   │     (If mismatch or unknown key -> Fail-Closed: RELEASE_AUTHORITY_UNKNOWN)
   │
   ├─ 3. Verify release_authority_signature_ed25519 over compute_canonical_signed_bytes()
   │     (If signature invalid -> Fail-Closed: RELEASE_MANIFEST_SIGNATURE_INVALID)
   │
   ├─ 4. Compute current repository tree hash; assert == manifest.executable_tree_digest
   │     (If codebase modified -> Fail-Closed: EXECUTABLE_INTEGRITY_COMPROMISED)
   │
   ├─ 5. Compute sha256(sovereign_root_anchor.json); assert == manifest.sovereign_root_anchor_digest
   │     (If root anchor modified -> Fail-Closed: SOVEREIGN_ROOT_ANCHOR_TAMPERED)
   │
   ├─ 6. Ingest authenticated sovereign_root_anchor.json
   │     Provides: SOVEREIGN_ROOT_PUBLIC_KEY and BOOTSTRAP_AUTHORITY_PUBLIC_KEY
   │
   ├─ 7. Ingest & verify genesis_bootstrap_manifest.json using BOOTSTRAP_AUTHORITY_PUBLIC_KEY
   │
   ├─ 8. Ingest & verify trust_anchor_manifest.json using SOVEREIGN_ROOT_PUBLIC_KEY
   │
   └─ 9. ONLY THEN load trust_store.json and accept HumanGORecord
```

> [!CRITICAL]
> **Zero Runtime Root Override:** The Runner strictly prohibits overriding or injecting the release authority key or root anchor via environment variables (`ACASH_ROOT_KEY_OVERRIDE`), CLI arguments, or mutable local configuration. Any override attempt triggers an immediate fatal exception.

---

## 4. Authoritative Genesis Bootstrap Manifest

To guarantee that the activation runner does not grant itself Genesis authority by calling `mkdir` or generating a Genesis head, Genesis initialization is established as an **external pre-run bootstrap ceremony** digitally signed by the Sovereign Bootstrap Authority.

### 4.1 `GenesisBootstrapManifest` Schema
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

### 4.2 Genesis Ceremony & Runner Verification Order
1. External bootstrap tool initializes pristine `var/gate_b/` directory skeleton.
2. Writes `var/gate_b/head.json` containing:
   $$\text{head\_digest} = \text{"0000000000000000000000000000000000000000000000000000000000000000"}$$
3. Signs manifest with `BOOTSTRAP_AUTHORITY_PRIVATE_KEY` and emits `var/gate_b/genesis_bootstrap_manifest.json`.
4. Flushes storage via Win32 `FlushFileBuffers`.
5. **Runner Verification Contract:** The Activation Runner verifies:
   a. Manifest exists and deserializes under frozen model.
   b. `bootstrap_signer_key_id` matches the authenticated `BOOTSTRAP_AUTHORITY_PUBLIC_KEY`.
   c. `bootstrap_signature_ed25519` is cryptographically valid over `compute_canonical_signed_bytes()`.
   d. `genesis_head_digest` matches `GENESIS_HEAD_DIGEST` ("00000...00000").
   e. `head.json` on disk matches `GENESIS_HEAD_DIGEST`.
   f. If any check fails $\to$ Raise `DataContractError: GENESIS_ENVIRONMENT_UNVERIFIED` (Fail-Closed).
   The Runner **CANNOT** create or re-initialize Genesis.

---

## 5. Cryptographic Trust-Store Provenance

### 5.1 `TrustAnchorManifest` Schema
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

### 5.2 Runner Cryptographic Ingestion Contract
Before reading any key entry or initializing `Ed25519TrustStore`:
1. Ingest `var/gate_b/trust_anchor_manifest.json`.
2. Extract `sovereign_signer_key_id` and match against the authenticated `SOVEREIGN_ROOT_PUBLIC_KEY`.
3. Cryptographically verify `sovereign_signature_ed25519` over `compute_canonical_signed_bytes()` using `SOVEREIGN_ROOT_PUBLIC_KEY`.
4. Compute `actual_trust_store_digest = sha256(read_bytes(var/gate_b/trust_store.json))`.
5. Assert `actual_trust_store_digest == manifest.trust_store_digest`.
6. Assert all required key IDs (`KEY_HUMAN_GOVERNANCE_AUDITOR_001`, `KEY_STORAGE_ENGINE_PROD_001`) exist in `manifest.trust_store_key_ids`.
7. If signature fails, digest mismatches, or required keys are missing $\to$ Raise `DataContractError: TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID` (Fail-Closed).
8. Only upon 100% cryptographic verification of the manifest does the runner load `trust_store.json`.

---

## 6. OS-Level Capability & Windows Token Privilege Boundary (Finding R5-3 Resolution)

Application-level absence of write methods is insufficient if OS access controls or process privileges permit modification. The repair enforces both filesystem DACLs and real Win32 process token restrictions:

### 6.1 Identity & Ownership Separation (DACL Layer)
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

### 6.2 Windows Token Privilege Boundary & Real Host Integration Evidence
A file-level Deny ACE is bypassed if the running process holds administrative privileges. To guarantee kernel enforcement:
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
4. **Mandatory Real Integration Evidence (Finding R5-3):** Adversarial Tests B19 and B20 MUST execute as real Windows integration tests on the host system against the physical NTFS filesystem and the actual Windows process token (via Win32 `OpenProcessToken`, `GetTokenInformation`, `SetFileSecurityW`, etc.) proving that the OS kernel denies takeover, permission modification, and elevation. Unit-test mock tokens are strictly insufficient for B19/B20 acceptance.

---

## 7. Process-Level Separation & Authenticated Human Authorization Ceremony

### 7.1 Process Separation: Mint Tool vs Activation Runner
To eliminate shared memory space or runtime object reuse between authorization creation and authorization consumption, the two roles are physically decoupled across OS processes:

```text
┌────────────────────────────────────────────────────────┐       ┌────────────────────────────────────────────────────────┐
│            PROCESS A: INTERACTIVE MINT TOOL            │       │               PROCESS B: VERIFY-ONLY RUNNER            │
│         (tools/governance/mint_human_go_record.py)     │       │               (src/acash/gate_b/runner.py)             │
├────────────────────────────────────────────────────────┤       ├────────────────────────────────────────────────────────┤
│ • Interactive TTY Execution ONLY (Anti-Pipe Hygiene)   │       │ • Automated pipeline execution                         │
│ • Asserts sys.stdin.isatty() == True                   │       │ • Unprivileged Windows Process Token (Real Win32 Token)│
│ • Hardware-Backed User-Presence Ceremony (MANDATORY)   │       │ • Static Dependency Closure: ZERO signing/keygen code  │
│ • Physical Touch on Hardware Key (FIDO2 / YubiKey)     │       │ • Ingests confirmation token via CLI argument          │
│ • Loads sovereign private key from secure hardware key │       │ • Strictly Verify-Only                                 │
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

### 7.2 Authenticated Human Authorization Ceremony: Hardware-Backed User Presence
Auditing established that interactive TTY checks (`isatty()`) only verify the absence of basic I/O redirection, and host-entered passphrases can be automated if the secret is accessible to local scripts.

Therefore, the ceremony establishes a strict hierarchy of authentication factors:
1. **Hardware-Backed User-Presence Factor (AUTHORITATIVE & MANDATORY):**
   The Sovereign Human Private Key is held in a physical hardware security module (FIDO2 / YubiKey CTAP2 / PKCS#11 hardware token). Signing a `HumanGORecord` strictly requires **physical user presence (physical touch / button press on the hardware authenticator)**. Physical presence cannot be simulated, synthesized, or automated by any local process, PTY, subshell, or remote script.
2. **Host-Entered Passphrase (INSUFFICIENT ALONE / SECONDARY ONLY):**
   A console passphrase may optionally serve as a secondary local decryption factor, but is explicitly **INSUFFICIENT** on its own to authorize the mint tool without the hardware-backed physical user-presence factor.
3. **Anti-Pipe Hygiene:** The tool enforces `sys.stdin.isatty()` as basic I/O hygiene, but never treats TTY presence as proof of human identity.
4. **Immediate Process Termination:** Once the single `human_go_record.json` artifact is signed and flushed, the process clears all in-memory key buffers and exits immediately with code 0.

### 7.3 Full Static Recursive Dependency Closure Audit (Mathematical Honesty Formulation)
Auditing established that inspecting runtime `sys.modules` does NOT prove capability isolation: modules loaded lazily, conditionally (`if condition: import ...`), or via untraversed code paths do not appear in `sys.modules`. Furthermore, static AST analysis cannot verify arbitrary dynamic runtime behaviors.

Therefore, the dependency boundary is governed by the following strict mathematical and architectural invariant:
> **Static Dependency Invariant:**  
> All statically resolvable imports are recursively analyzed across the entire dependency graph of the Runner. Unsupported dynamic, non-literal, or unresolvable import mechanisms are strictly prohibited rather than trusted.

1. **Static AST Analysis Algorithm:**
   - Parse the AST of `acash.gate_b.runner` and recursively resolve all `ast.Import` and `ast.ImportFrom` nodes across all reachable internal modules.
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
   The runner codebase strictly prohibits non-literal dynamic imports (`importlib.import_module(variable)`, `__import__(variable)`). Any unresolvable dynamic import detected in the runner closure triggers an immediate static audit failure.
4. **Complementary Runtime Verification:**
   The test suite verifies that `Ed25519Signer` and key generation symbols are absent from `acash.gate_b.runner.__dict__` and never instantiated during execution.

### 7.4 Capability Boundary Matrix
| Capability | Process A: Interactive Mint Tool | Process B: Verify-Only Runner |
| :--- | :---: | :---: |
| **Interactive TTY Required** | **MANDATORY (Anti-Pipe Hygiene)** | Not Required (Automated / Pipeline) |
| **Hardware-Backed User Presence** | **MANDATORY (Physical Touch / FIDO2)**| ⛔ **PROHIBITED (Zero Key Material)** |
| **Host Passphrase Alone** | **INSUFFICIENT (Secondary Only)** | ⛔ **PROHIBITED (Zero Key Material)** |
| **Load Sovereign Private Key**| **PERMITTED** (Unlocked via Hardware) | ⛔ **PROHIBITED (Zero Key Capability)** |
| **Sign `HumanGORecord`** | **PERMITTED** | ⛔ **PROHIBITED (Verify-Only)** |
| **Generate Keypairs (`generate_key_pair`)**| ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Write `trust_store.json`** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED** |
| **Import Storage Write APIs** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Post-Verification 2PC)** |
| **Advance Ledger Head** | ⛔ **STRICTLY PROHIBITED** | **PERMITTED (Stage 8 2PC Commit)** |
| **Broker Order Dispatch** | ⛔ **STRICTLY PROHIBITED** | ⛔ **STRICTLY PROHIBITED (Slice 3 Blocked)** |
| **OS Token Privilege** | Standard Operator Token | **Unprivileged Token (No Admin/Takeover)** |

---

## 8. Full Operational Context Binding in `HumanGORecord`

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

## 9. Adversarial Verification Plan (21 Hard Boundary Tests)

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
| **Test B14: Full Static Recursive AST Closure Audit** | Statically analyze full recursive import graph; ban unresolvable dynamic imports | Fails closed if ANY reachable module exports signing/keygen capability |
| **Test B15: Trust Anchor Sovereign Signature Check** | Mutate manifest or sign with untrusted sovereign root key | Fails closed: `TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID` |
| **Test B16: Genesis Bootstrap Signature Check** | Mutate genesis manifest or sign with untrusted bootstrap key | Fails closed: `GENESIS_ENVIRONMENT_UNVERIFIED` |
| **Test B17: Hardware User Presence & PTY Ban** | Run mint tool in PTY/headless or without hardware touch confirmation | Fails closed: `MINT_TOOL_REQUIRES_HARDWARE_USER_PRESENCE` |
| **Test B18: Sovereign Root Anchor Tampering Ban** | Mutate root anchor or digest mismatch against release manifest | Fails closed: `DataContractError: SOVEREIGN_ROOT_ANCHOR_TAMPERED` |
| **Test B19: Real Windows Token Privilege Audit**| Execute on actual Win32 token; verify unprivileged status and no elevation | Fails closed: `GovernanceSecurityError: RUNNER_PROCESS_TOKEN_PRIVILEGED` |
| **Test B20: Real NTFS Owner Takeover & DACL Ban**| Attempt Win32 takeover or DACL write on actual host NTFS substrate | Fails closed: `ERROR_ACCESS_DENIED` / `ERROR_PRIVILEGE_NOT_HELD` |
| **Test B21: Signed Release Manifest Verification**| Mutate release manifest or sign with untrusted release authority key | Fails closed: `DataContractError: RELEASE_MANIFEST_SIGNATURE_INVALID` |

---

## 10. Execution Phasing & Acceptance Criteria

The repair proceeds through four strictly gated steps. Advancing between steps requires explicit human auditor sign-off:

```text
Step 1: Formal Audit Approval of this Plan (Rev 6)
  │
  ▼
Step 2: Implement Tooling & Architectural Hardening (Zero Activation)
  ├─ tools/governance/mint_human_go_record.py (Process A: Hardware-Backed User Presence)
  ├─ src/acash/gate_b/runner.py (Process B: Verify-Only with Static Closure Isolation & Real Token Audit)
  ├─ tests/unit/gate_b/test_gate_b_governance_repair.py (21 Adversarial Tests)
  └─ Verification Criterion: ALL REPOSITORY TESTS PASS (Pre-repair baseline + new tests clean; MyPy clean)
  │
  ▼
Step 3: Governance Ceremonies & Storage Re-initialization
  ├─ Archive var/gate_b -> var/gate_b_incident_archive (Option 2)
  ├─ External Release Authority signs release_manifest.json (Commit SHA & Root Anchor Digest)
  ├─ Execute Genesis Bootstrap Ceremony -> Sovereign signs genesis_bootstrap_manifest.json
  ├─ Execute Trust Anchor Ceremony -> Sovereign signs trust_anchor_manifest.json & seals trust_store.json
  ├─ Execute Hardware-Backed Human Authorization Ceremony -> Auditor signs human_go_record.json
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
> "All repository tests pass; exact count reported from actual execution. No regression from pre-repair baseline. Static type checker (MyPy) reports 0 errors across all source files. Tests B19 and B20 verified against actual Win32 host tokens and physical NTFS filesystem."

---

## 11. Approval Sign-Off Block

```markdown
════════════════════════════════════════════════════════════════════════════════
    GATE B GOVERNANCE REPAIR PLAN (REV 6) — FORMAL AUDIT APPROVAL
════════════════════════════════════════════════════════════════════════════════

Governing Document:       docs/phase13/gate_b_governance_repair_plan.md (Rev 6)
Parent Incident Report:   docs/phase13/gate_b_forensic_reconciliation_report.md
Storage Resolution Mode:  OPTION 2: FORENSIC ARCHIVE & FRESH GENESIS ROOT
Incident Archive Path:    var/gate_b_incident_archive/ (Immutable NTFS Deny DACL)
Release Authority:        release_manifest.json (Ed25519 Signed by External Release Authority)
Root Anchor Governance:   Pinned via Signed Release Manifest (Zero Runtime Override)
Genesis Authority:        genesis_bootstrap_manifest.json (Ed25519 Sovereign Signed)
Trust Anchor Authority:   trust_anchor_manifest.json (Ed25519 Sovereign Signed)
OS Capability Contract:   Governance Owner, Non-Elevation, Anti-Replacement DACL
Windows Token Boundary:   Real Unprivileged Win32 Token (No SeTakeOwnership/SeRestore/Admin)
Static Closure Isolation: Static AST Dependency Graph: ZERO Signing/Keygen/Write Symbols
Human Authorization:      Hardware-Backed User Presence (FIDO2 / Physical Touch Required)
Live Capital Authority:   $0.00 (Zero Capital Deployed)
Broker Execution:         PROHIBITED (Slice 3 Strictly Blocked)

Auditor Decision:         [ PENDING REVIEW / APPROVED / REVISION REQUIRED ]

Human Governance Auditor: _______________________________________________

Date & Time (UTC):        _______________________________________________

Decision Token:           _______________________________________________
════════════════════════════════════════════════════════════════════════════════
```
