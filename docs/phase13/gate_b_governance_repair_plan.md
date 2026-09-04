# Phase 13: Gate B Governance Repair Plan (Formal Specification — Revision 7)

**Document ID:** `ACASH-DOC-P13-GATE-B-GOVERNANCE-REPAIR-PLAN-REV7`  
**Parent Incident Report:** `docs/phase13/gate_b_forensic_reconciliation_report.md` (Commit `affc5ce`)  
**Governing Specification Baseline:** `docs/phase13/slice2_gate_b_plan.md` (Rev 20 Frozen Baseline, Spec Commit `647ba75`)  
**Auditor Review Baseline:** Human Auditor Review of Rev 6 (Resolving Blockers R6-1, R6-2, and Finding R6-3)  
**Current System State:**  
- Transaction Persistence: `COMMITTED` (Incident transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` on physical NTFS)  
- Authorization Provenance: `INVALID` (Self-authorizing runtime runner loop)  
- Governance State: `QUARANTINED / NOT AUTHORIZED`  
- Trading Authority: `STRICTLY BLOCKED`  
- Live Capital Deployed: `$0.00`  
- Live Orders Transmitted: `0`  
- Broker Connection: `DISCONNECTED`  
**Document Status:** REVISION 7 — SUBMITTED FOR FORMAL AUDIT APPROVAL (ZERO EXECUTION / ZERO CODE MUTATION)

---

## 1. Executive Summary & Problem Remediation

During the Gate B activation attempt on 2026-09-05, the runner script committed transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` via a **circular self-authorizing loop**: the runner generated its own Ed25519 human governance keypair at runtime, wrote its own public key into a new trust store, fabricated a `HumanGORecord`, signed the record with its own private key, verified the signature against its own trust store, and hardcoded the confirmation token into evidence.

While the physical storage mechanics (two-phase commit, fsync barriers, CAS elevations, pointer transitions, NTFS DACL) executed correctly as software code, the **governance provenance is mathematically and organizationally invalid**.

In Revision 6, the architecture established a signed release manifest, non-circular bootstrap, and hardware user presence. However, deep root-of-trust audit identified three final gaps required for complete mathematical and cryptographic closure:
1. **Pre-Execution Verifier Authenticity (Blocker R6-1):** A signed manifest verifies files, but does not prevent an attacker from modifying the Runner executable itself to skip manifest checks. Trust must anchor in a pre-execution launch verifier outside the Runner.
2. **Deterministic Tree Digest Specification (Blocker R6-2):** `executable_tree_digest` lacked a formal byte-for-byte canonical algorithm, domain separation, and exclusion set, risking divergence between Release Authority hashing and Runner verification, as well as circular manifest hashing.
3. **Precise Hardware Signing Protocol (Finding R6-3):** Replaced generic "FIDO2" references with the exact cryptographic hardware protocol: **YubiKey PIV Ed25519 with PIN Policy = Always and Touch Policy = Always**.

This Revision 7 Governance Repair Plan establishes an **unbroken, pre-execution authenticated trust hierarchy**:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   CANONICAL ROOT-OF-ROOT TRUST BOOTSTRAP HIERARCHY                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. PRE-EXECUTION VERIFIER & LAUNCH BOUNDARY (Blocker R6-1 Resolution):                 │
│    - External Pre-Execution Launcher: tools/governance/launch_runner.py               │
│    - Verifies signed release_manifest.json via RELEASE_AUTHORITY_ROOT_PUBLIC_KEY       │
│    - Computes deterministic executable_tree_digest (Algorithm ACASH-RELEASE-TREE-V1)  │
│    - Asserts Runner executable integrity BEFORE spawning or executing Runner process   │
│                                │                                                       │
│                                ▼ spawns authenticated process                          │
│ 2. SIGNED RELEASE MANIFEST (release_manifest.json):                                    │
│    - Signed via Ed25519 by External Release Authority                                  │
│    - Cryptographically binds: commit SHA, tree digest, root anchor digest              │
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
│    - Signed via YubiKey PIV Ed25519 (Slot 9c, PIN=Always, Touch=Always)                │
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

## 3. Pre-Execution Verifier Authenticity & Canonical Release Manifest (Blockers R6-1 & R6-2 Resolution)

### 3.1 Pre-Execution Verifier & Launch Boundary (Blocker R6-1 Resolution)
To eliminate the vulnerability where an attacker modifies `runner.py` to bypass verification checks, verification is decoupled into a **Pre-Execution Bootstrap Launcher** (`tools/governance/launch_runner.py`):
1. **Out-of-Process Attestation:** Before invoking Python runtime on `acash.gate_b.runner`, the launcher:
   - Reads `release_manifest.json`.
   - Cryptographically verifies `release_authority_signature_ed25519` against `RELEASE_AUTHORITY_ROOT_PUBLIC_KEY`.
   - Computes the canonical `executable_tree_digest` across the codebase using algorithm `ACASH-RELEASE-TREE-V1`.
   - Asserts `computed_tree_digest == manifest.executable_tree_digest`.
   - Asserts `sha256(src/acash/gate_b/runner.py)` matches the recorded hash.
2. **Fail-Closed Pre-Execution Gate:** If any file in `src/` has been modified or patched, the launcher halts immediately (`PreExecutionIntegrityError: RUNNER_EXECUTABLE_AUTHENTICITY_FAILED`). The Runner process is never started.
3. **Adversarial Test B22:** Verifies that modifying a single byte in `runner.py` causes the pre-execution verifier to reject execution before Gate B Stage 1 begins.

### 3.2 Canonical Tree Digest Algorithm `ACASH-RELEASE-TREE-V1` (Blocker R6-2 Resolution)
To guarantee deterministic, byte-for-byte identical hashing between the External Release Authority and local verifiers with zero circularity:

#### 3.2.1 Domain Separation & Strict Exclusion Set
The following paths are **STRICTLY EXCLUDED** from `executable_tree_digest`:
- `release_manifest.json` (avoids circular manifest self-hashing)
- `*.sig`, `*.signature`, `*.sha256`
- `var/` (runtime storage, locks, journals, state databases)
- `var/gate_b_incident_archive/` (historical forensic archive)
- `.git/`, `.gitignore`, `.github/`
- `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.venv/`, `*.egg-info/`
- `docs/` (non-executable markdown artifacts)
- Temporary, scratch, or log files

#### 3.2.2 Strict Inclusion Set
All release-critical production codebase and governance tooling files:
- `src/**` (all production engine modules)
- `tools/governance/**` (all sovereign governance tools)
- `pyproject.toml`, `uv.lock` (frozen package dependencies)

#### 3.2.3 Canonical Tree Digest Formulation
1. Discover all files matching Inclusion Set that are not excluded.
2. Normalize every file path to POSIX relative format (`/`) relative to repository root (e.g. `src/acash/gate_b/runner.py`).
3. Read raw file bytes verbatim (`rb`).
4. Compute leaf SHA-256:
   $$H_{\text{leaf}} = \text{hex}(\text{SHA256}(\text{raw\_bytes}))$$
5. Sort all entries lexicographically by `canonical_rel_path` in UTF-8 byte order.
6. Assemble canonical tree payload:
   $$\text{TreePayload} = \text{"ACASH-RELEASE-TREE-V1}\backslash 0\text{"} \parallel \sum_{i} \left( \text{canonical\_rel\_path}_i \parallel \text{"}\backslash 0\text{"} \parallel H_{\text{leaf}, i} \parallel \text{"}\backslash n\text{"} \right)$$
7. Compute final digest:
   $$\text{executable\_tree\_digest} = \text{hex}(\text{SHA256}(\text{TreePayload}))$$

### 3.3 `ReleaseManifest` Schema
```python
class ReleaseManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int = Field(default=1, description="Schema version.")
    release_tag: str = Field(description="Audited release tag, e.g. v1.0.0-gate-b.")
    release_commit_sha: str = Field(description="Exact Git commit SHA of frozen release baseline.")
    executable_tree_digest: str = Field(
        description="Canonical SHA-256 tree digest using ACASH-RELEASE-TREE-V1."
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

---

## 4. Authoritative Genesis Bootstrap Manifest

Genesis initialization is established as an **external pre-run bootstrap ceremony** digitally signed by the Sovereign Bootstrap Authority.

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
2. Writes `var/gate_b/head.json` containing `head_digest = "00000...00000"`.
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
2. **Restricted Privilege Token:** The Runner process token MUST NOT hold:
   - `SeTakeOwnershipPrivilege` (Bans taking ownership of governance files)
   - `SeRestorePrivilege` (Bans DACL-bypass write operations)
   - `SeBackupPrivilege` (Bans DACL-bypass read operations)
   - `SeSecurityPrivilege` (Bans audit policy / SACL manipulation)
   - `SeDebugPrivilege` (Bans cross-process inspection or memory injection)
   - `SeTcbPrivilege` (Bans acting as part of the operating system)
3. **Pre-Flight Token Inspection (Stage 1 Invariant):** At startup, before performing any operation, the Runner inspects its Win32 process token via `GetTokenInformation(TokenPrivileges)` and `GetTokenInformation(TokenElevation)`:
   - If `TokenIsElevated == True` $\to$ Halt immediately (`GovernanceSecurityError: RUNNER_PROCESS_TOKEN_ELEVATED`).
   - If any restricted privilege is enabled or present in token $\to$ Halt immediately (`GovernanceSecurityError: RESTRICTED_TOKEN_PRIVILEGES_DETECTED`).
4. **Mandatory Real Integration Evidence:** Adversarial Tests B19 and B20 MUST execute as real Windows integration tests on the host system against the physical NTFS filesystem and the actual Windows process token (via Win32 `OpenProcessToken`, `GetTokenInformation`, `SetFileSecurityW`, etc.) proving that the OS kernel denies takeover, permission modification, and elevation. Unit-test mock tokens are strictly prohibited for B19/B20 acceptance.

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
│ • Hardware-Backed User Presence: YubiKey PIV Ed25519   │       │ • Static Dependency Closure: ZERO signing/keygen code  │
│ • PIN Policy = Always, Touch Policy = Always           │       │ • Ingests confirmation token via CLI argument          │
│ • Hardware Secure Element Generates Ed25519 Signature  │       │ • Strictly Verify-Only                                 │
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

### 7.2 Hardware-Backed User Presence: YubiKey PIV Ed25519 Protocol (Finding R6-3 Resolution)
Auditing established that generic "FIDO2" references are ambiguous for arbitrary artifact signing, and console passphrases can be automated by local scripts.

Therefore, the authoritative human ceremony enforces the exact cryptographic hardware protocol:
1. **Authoritative Signing Mechanism:** **YubiKey PIV (Personal Identity Verification) / PKCS#11 with Ed25519**:
   - **Key Slot:** Slot `9c` (Digital Signature) or Slot `9a` (Authentication)
   - **Algorithm:** `Ed25519` (supported in YubiKey 5 Series firmware $\ge$ 5.7)
   - **PIN Policy:** `Always` (requires user PIN on every signing operation)
   - **Touch Policy:** `Always` (requires physical capacitive touch on the hardware contact for every signing operation; hardware timeout fails closed if touch is not detected within 15 seconds)
2. **Signing Ceremony Protocol Execution:**
   - Mint Tool computes canonical payload bytes for `HumanGORecord`.
   - Prompts operator for YubiKey PIV PIN on interactive console.
   - Initiates PIV signing operation targeting Slot `9c`.
   - YubiKey hardware LED blinks, waiting for physical capacitance touch on the hardware sensor.
   - Auditor physically touches the YubiKey contact.
   - The YubiKey internal cryptographic coprocessor generates the Ed25519 signature and returns signature bytes. The private key never leaves the hardware secure element.
   - Process A formats `human_go_record.json`, writes to disk, flushes buffers, and exits immediately.
3. **Anti-Automation Resistance:** Software automation, PTY allocations, background scripts, or remote callers cannot simulate physical capacitive touch on the hardware key sensor. Absence of physical touch causes the hardware token to abort with `SW_SECURITY_STATUS_NOT_SATISFIED` or timeout.
4. **Host Passphrase Insufficiency:** A console passphrase alone is strictly secondary and explicitly **INSUFFICIENT** to authorize artifact generation without the hardware-backed physical user-presence factor.

### 7.3 Full Static Recursive Dependency Closure Audit
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
| **Hardware-Backed User Presence** | **MANDATORY (YubiKey PIV Touch=Always)**| ⛔ **PROHIBITED (Zero Key Material)** |
| **Host Passphrase Alone** | **INSUFFICIENT (Secondary Only)** | ⛔ **PROHIBITED (Zero Key Material)** |
| **Load Sovereign Private Key**| **PERMITTED** (Hardware Element Only) | ⛔ **PROHIBITED (Zero Key Capability)** |
| **Sign `HumanGORecord`** | **PERMITTED (Hardware Coprocessor)**| ⛔ **PROHIBITED (Verify-Only)** |
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

## 9. Adversarial Verification Plan (22 Hard Boundary Tests)

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
| **Test B22: Pre-Execution Runner Integrity Check**| Mutate 1 byte in `runner.py`; launcher verifies `ACASH-RELEASE-TREE-V1` | Fails closed: `PreExecutionIntegrityError: RUNNER_EXECUTABLE_AUTHENTICITY_FAILED` |

---

## 10. Execution Phasing & Acceptance Criteria

The repair proceeds through four strictly gated steps. Advancing between steps requires explicit human auditor sign-off:

```text
Step 1: Formal Audit Approval of this Plan (Rev 7)
  │
  ▼
Step 2: Implement Tooling & Architectural Hardening (Zero Activation)
  ├─ tools/governance/launch_runner.py (Pre-Execution Bootstrap Launcher: Blocker R6-1)
  ├─ tools/governance/mint_human_go_record.py (Process A: YubiKey PIV Ed25519 Hardware Touch)
  ├─ src/acash/gate_b/runner.py (Process B: Verify-Only with Static Closure Isolation & Real Token Audit)
  ├─ tests/unit/gate_b/test_gate_b_governance_repair.py (22 Adversarial Tests)
  └─ Verification Criterion: ALL REPOSITORY TESTS PASS (Pre-repair baseline + new tests clean; MyPy clean)
  │
  ▼
Step 3: Governance Ceremonies & Storage Re-initialization
  ├─ Archive var/gate_b -> var/gate_b_incident_archive (Option 2)
  ├─ External Release Authority signs release_manifest.json (Commit SHA & ACASH-RELEASE-TREE-V1)
  ├─ Execute Genesis Bootstrap Ceremony -> Sovereign signs genesis_bootstrap_manifest.json
  ├─ Execute Trust Anchor Ceremony -> Sovereign signs trust_anchor_manifest.json & seals trust_store.json
  ├─ Execute Hardware-Backed Human Authorization Ceremony -> Auditor signs human_go_record.json via YubiKey PIV
  └─ Human Audit Review of Fresh Activation Pack on GitHub
  │
  ▼
Step 4: Fresh Authoritative Gate B Activation Execution
  ├─ Pre-Execution Launcher verifies runner authenticity -> launches Process B
  ├─ Process B (Verify-Only Runner) executes Stages 1–9 under single continuous lock
  ├─ Verify COMMITTED on fresh root
  └─ Immediate Halt: STOP AGAIN (Live capital = $0.00; Live orders = 0)
```

> [!NOTE]
> **Acceptance Criterion Language:**  
> "All repository tests pass; exact count reported from actual execution. No regression from pre-repair baseline. Static type checker (MyPy) reports 0 errors across all source files. Tests B19 and B20 verified against actual Win32 host tokens and physical NTFS filesystem. Test B22 verified by mutating runner bytecode and asserting pre-execution launcher abort."

---

## 11. Approval Sign-Off Block

```markdown
════════════════════════════════════════════════════════════════════════════════
    GATE B GOVERNANCE REPAIR PLAN (REV 7) — FORMAL AUDIT APPROVAL
════════════════════════════════════════════════════════════════════════════════

Governing Document:       docs/phase13/gate_b_governance_repair_plan.md (Rev 7)
Parent Incident Report:   docs/phase13/gate_b_forensic_reconciliation_report.md
Storage Resolution Mode:  OPTION 2: FORENSIC ARCHIVE & FRESH GENESIS ROOT
Incident Archive Path:    var/gate_b_incident_archive/ (Immutable NTFS Deny DACL)
Pre-Execution Boundary:   tools/governance/launch_runner.py (Authenticates Runner Before Execution)
Canonical Tree Digest:    ACASH-RELEASE-TREE-V1 (Strict Exclusion Set & Lexicographical Ordering)
Release Authority:        release_manifest.json (Ed25519 Signed by External Release Authority)
Root Anchor Governance:   Pinned via Signed Release Manifest (Zero Runtime Override)
Genesis Authority:        genesis_bootstrap_manifest.json (Ed25519 Sovereign Signed)
Trust Anchor Authority:   trust_anchor_manifest.json (Ed25519 Sovereign Signed)
OS Capability Contract:   Governance Owner, Non-Elevation, Anti-Replacement DACL
Windows Token Boundary:   Real Unprivileged Win32 Token (No SeTakeOwnership/SeRestore/Admin)
Static Closure Isolation: Static AST Dependency Graph: ZERO Signing/Keygen/Write Symbols
Human Authorization:      YubiKey PIV Ed25519 (Slot 9c, PIN=Always, Touch=Always)
Live Capital Authority:   $0.00 (Zero Capital Deployed)
Broker Execution:         PROHIBITED (Slice 3 Strictly Blocked)

Auditor Decision:         [ PENDING REVIEW / APPROVED / REVISION REQUIRED ]

Human Governance Auditor: _______________________________________________

Date & Time (UTC):        _______________________________________________

Decision Token:           _______________________________________________
════════════════════════════════════════════════════════════════════════════════
```
