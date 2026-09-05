# Phase 13: Gate B Governance Repair Plan (Formal Specification — Revision 9)

**Document ID:** `ACASH-DOC-P13-GATE-B-GOVERNANCE-REPAIR-PLAN-REV9`  
**Parent Incident Report:** `docs/phase13/gate_b_forensic_reconciliation_report.md` (Commit `affc5ce`)  
**Governing Specification Baseline:** `docs/phase13/slice2_gate_b_plan.md` (Rev 20 Frozen Baseline, Spec Commit `647ba75`)  
**Auditor Review Baseline:** Human Auditor Review of Rev 8 (Resolving Blockers R8-1, R8-2, and Finding R8-3)  
**Current System State:**  
- Transaction Persistence: `COMMITTED` (Incident transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` on physical NTFS)  
- Authorization Provenance: `INVALID` (Self-authorizing runtime runner loop)  
- Governance State: `QUARANTINED / NOT AUTHORIZED`  
- Trading Authority: `STRICTLY BLOCKED`  
- Live Capital Deployed: `$0.00`  
- Live Orders Transmitted: `0`  
- Broker Connection: `DISCONNECTED`  
**Document Status:** REVISION 9 — SUBMITTED FOR FORMAL AUDIT APPROVAL (ZERO EXECUTION / ZERO CODE MUTATION)

---

## 1. Executive Summary & Problem Remediation

During the Gate B activation attempt on 2026-09-05, the runner script committed transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` via a **circular self-authorizing loop**: the runner generated its own Ed25519 human governance keypair at runtime, wrote its own public key into a new trust store, fabricated a `HumanGORecord`, signed the record with its own private key, verified the signature against its own trust store, and hardcoded the confirmation token into evidence.

While the physical storage mechanics (two-phase commit, fsync barriers, CAS elevations, pointer transitions, NTFS DACL) executed correctly as software code, the **governance provenance is mathematically and organizationally invalid**.

In Revision 8, the architecture introduced release manifests binding the launcher, interpreter, and dependency tree. However, deep root-of-trust audit identified that **the Verifier's Paradox had merely shifted from the Runner to the Launcher**:
1. **Launcher Self-Attestation Paradox (Blocker R8-1):** `launch_runner.py` was tasked with reading its own SHA-256 and verifying its own integrity. If an attacker patches `launch_runner.py` to return `True`, self-attestation collapses. A verifier cannot derive its authority from the mutable software tree it is adjudicating.
2. **Mutable Root Anchor in Python Source (Blocker R8-2):** `RELEASE_AUTHORITY_ROOT_PUBLIC_KEY` resided in Python code, which could be patched alongside the launcher. The root anchor must be pinned outside the Python software stack.
3. **Ambiguous Runtime Environment Digest (Finding R8-3):** `runtime_dependencies_tree_digest` required a formal, deterministic canonical algorithm (`ACASH-RUNTIME-ENV-V1`) with explicit exclusion sets, path normalizations, and byte-level formulations.

This Revision 9 Governance Repair Plan resolves the Verifier's Paradox by introducing an **External OS-Enforced Trust Boundary & Native Signed Bootstrapper**:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   CANONICAL ROOT-OF-ROOT TRUST BOOTSTRAP HIERARCHY                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. TIER 0: OS-ENFORCED TRUST & CODE INTEGRITY POLICY (Blocker R8-1 Resolution):        │
│    - Windows Defender Application Control (WDAC) / Authenticode Code Signing Policy     │
│    - Only binaries signed by External Release Authority Authenticode Cert may execute  │
│                                │                                                       │
│                                ▼ OS verifies Authenticode signature before execution   │
│ 2. TIER 1: NATIVE SIGNED BOOTSTRAPPER (tools/governance/bin/acash-bootstrapper.exe):   │
│    - Standalone compiled native binary (ASLR, DEP, SafeSEH, read-only .rdata)          │
│    - RELEASE_AUTHORITY_ROOT_PUBLIC_KEY compiled immutably into PE read-only section    │
│    - Verifies release_manifest.json signature via embedded Root Key (Blocker R8-2)     │
│    - Asserts sha256(tools/governance/launch_runner.py) == manifest.launcher_sha256     │
│    - Asserts sha256(python.exe) == manifest.python_interpreter_sha256                  │
│    - Evaluates ACASH-RUNTIME-ENV-V1(.venv) == manifest.runtime_env_digest (R8-3)      │
│    - Evaluates ACASH-RELEASE-TREE-V1(codebase) == manifest.executable_tree_digest      │
│                                │                                                       │
│                                ▼ launches authenticated launcher                       │
│ 3. TIER 2: AUTHENTICATED PRE-EXECUTION LAUNCHER (tools/governance/launch_runner.py):   │
│    - Spawns Python in Strict Isolated Mode (-I -s -E, absolute canonical paths)        │
│    - Sanitizes sys.path: Zero CWD, zero user site-packages, zero PYTHONPATH injection  │
│                                │                                                       │
│                                ▼ spawns verify-only runner process                     │
│ 4. TIER 3: VERIFY-ONLY RUNNER (src/acash/gate_b/runner.py):                            │
│    - Real Unprivileged Windows Token (No SeTakeOwnership, No SeRestore, No Admin)      │
│    - Static AST Dependency Closure: ZERO signing/keygen/trust-write symbols            │
│    - Validates sovereign_root_anchor.json against manifest.sovereign_root_anchor_digest│
│                                │                                                       │
│             ┌──────────────────┴──────────────────┐                                    │
│             ▼ verifies signature                  ▼ verifies signature                 │
│ 5. TRUST ANCHOR MANIFEST:             6. GENESIS BOOTSTRAP MANIFEST:                   │
│    - Signed by Sovereign Root             - Signed by Bootstrap Authority              │
│    - Binds SHA-256 of trust_store.json    - Binds Genesis head & incident archive tree │
│             │                                     │                                    │
│             ▼ references digest                   ▼ validates fresh storage root       │
│ 7. SEALED TRUST STORE (trust_store.json) 8. FRESH GENESIS ROOT (var/gate_b/)           │
│    - Registered Approver Public Keys      - Head digest: "00000...00000"               │
│             │                                                                          │
│             ▼ verifies signature                                                       │
│ 9. AUTHENTICATED HUMAN GO RECORD (human_go_record.json):                               │
│    - Signed via YubiKey PIV Ed25519 (Slot 9c, PIN=Always, Touch=Always)                │
│    - Bound to Gate A digest, account, limits, and fresh Genesis head                   │
│                                │                                                       │
│                                ▼ executes under single continuous lock                 │
│ 10. 2PC GATE B ACTIVATION COMMIT (Stages 6–8 Single Exclusive Lock):                   │
│    - Advances ledger head from GENESIS_HEAD_DIGEST to Activation Transaction           │
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

## 3. Pre-Execution Verifier, Native Bootstrapper, & Canonical Environment Attestation (Blockers R8-1, R8-2, & R8-3 Resolution)

### 3.1 External OS Trust & Native Signed Bootstrapper (Blockers R8-1 & R8-2 Resolution)
To eliminate the Verifier's Paradox and remove the root anchor from Python source code:
1. **Tier 0 OS Application Control:** The host Windows operating system enforces execution integrity via Windows Defender Application Control (WDAC) or Authenticode Code Signing policies. Only native binaries signed with the **External Release Authority Authenticode Certificate** are permitted to execute.
2. **Tier 1 Native Signed Bootstrapper (`tools/governance/bin/acash-bootstrapper.exe`):**
   - Standalone native binary compiled from audited source with stack protection (`/GS`), Control Flow Guard (`/guard:cf`), ASLR (`/DYNAMICBASE`), and DEP (`/NXCOMPAT`).
   - Authenticode digitally signed by the External Release Authority.
   - **Immutable Root Anchor:** The `RELEASE_AUTHORITY_ROOT_PUBLIC_KEY` is compiled into the PE `.rdata` (read-only data) section of `acash-bootstrapper.exe`. It does NOT exist as a mutable Python variable.
   - **Administrative DACL:** The bootstrapper binary is owned by Administrator with explicit Deny Write ACEs for standard users.
3. **Bootstrapper Attestation Sequence:**
   When `acash-bootstrapper.exe` executes:
   a. Loads `release_manifest.json`.
   b. Verifies `release_authority_signature_ed25519` using its embedded read-only root public key.
   c. Reads raw bytes of `tools/governance/launch_runner.py`, computes SHA-256, and asserts `== manifest.launcher_artifact_sha256`.
   d. Reads raw bytes of `sys.executable` (`python.exe`), computes SHA-256, and asserts `== manifest.python_interpreter_sha256`.
   e. Computes `ACASH-RUNTIME-ENV-V1` across `.venv/Lib/site-packages` and asserts `== manifest.runtime_dependencies_tree_digest`.
   f. Computes `ACASH-RELEASE-TREE-V1` across codebase and asserts `== manifest.executable_tree_digest`.
   g. Only if all verifications succeed: invokes `python.exe -I -s -E tools/governance/launch_runner.py`.

### 3.2 Canonical Runtime Environment Digest Algorithm `ACASH-RUNTIME-ENV-V1` (Finding R8-3 Resolution)
To eliminate ambiguity in runtime environment attestation, `ACASH-RUNTIME-ENV-V1` specifies a deterministic, byte-for-byte canonical hashing standard:

#### 3.2.1 Base Directory & Strict Path Normalization
- Base directory: `.venv/Lib/site-packages/`
- Every file path is normalized to POSIX relative format (`/`) relative to `.venv/Lib/site-packages/` (e.g. `pydantic/main.py`).

#### 3.2.2 Strict Exclusion Set
The following paths within site-packages are **STRICTLY EXCLUDED**:
- `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd.tmp`
- `*.dist-info/RECORD` (install-time mutable hash records)
- `*.dist-info/INSTALLER`
- `*.dist-info/direct_url.json`
- Temporary files, `.pytest_cache/`, scratch files

#### 3.2.3 Strict Inclusion Set
All release-critical dependency artifacts:
- `.py`, `.pyd`, `.dll`, `.so`, `.json` data files
- `.dist-info/METADATA` and `.dist-info/entry_points.txt` belonging to dependencies locked in `uv.lock`

#### 3.2.4 Symlink & Encoding Handling
- Symlinks are resolved to canonical target paths; circular symlinks trigger immediate fail-closed abort.
- All file contents are read as raw binary bytes (`rb`) with zero line-ending normalization.

#### 3.2.5 Canonical Hashing Formulation
1. Discover all files matching Inclusion Set not matched by Exclusion Set.
2. For each file, compute leaf SHA-256:
   $$H_{\text{leaf}} = \text{hex}(\text{SHA256}(\text{raw\_bytes}))$$
3. Sort all entries lexicographically by `canonical_rel_path` in UTF-8 byte order.
4. Assemble canonical runtime environment payload:
   $$\text{RuntimePayload} = \text{"ACASH-RUNTIME-ENV-V1}\backslash 0\text{"} \parallel \sum_{i} \left( \text{canonical\_rel\_path}_i \parallel \text{"}\backslash 0\text{"} \parallel H_{\text{leaf}, i} \parallel \text{"}\backslash n\text{"} \right)$$
5. Compute final digest:
   $$\text{runtime\_dependencies\_tree\_digest} = \text{hex}(\text{SHA256}(\text{RuntimePayload}))$$

### 3.3 Python Runtime Isolation & Anti-Hijacking Contract
To guarantee that static AST analysis cannot be bypassed by runtime import/path hijacking:
1. **Isolated Mode Execution:** The launcher spawns the Python runner using strict isolated mode flags:
   ```bash
   python.exe -I -s -E src/acash/gate_b/runner.py --activation-transaction-id ...
   ```
   - `-I` (Isolated mode): Implies `-E` and `-s`. Python ignores all `PYTHON*` environment variables (`PYTHONPATH`, `PYTHONHOME`, `PYTHONUSERBASE`, etc.) and completely disables adding the current working directory (`""`) or script directory to `sys.path`.
   - `-s`: Disables importing user site-packages (`%APPDATA%\Python`).
   - `-E`: Completely ignores environment variables affecting Python runtime.
2. **Absolute Path Binding:**
   - The interpreter is invoked via an absolute, verified path resolved from repository root: `.venv/Scripts/python.exe`.
   - The runner entrypoint is invoked via canonical absolute path resolved from repository root: `src/acash/gate_b/runner.py`.
   - Working directory is explicitly bound to repository root.
3. **Runner Startup `sys.path` Sanitization:**
   At Stage 1 pre-flight, the Runner inspects `sys.path`:
   - Asserts that neither `""` nor `"."` exists in `sys.path`.
   - Asserts that every path entry in `sys.path` is an absolute canonical path within either the authenticated standard library or the authenticated `.venv/Lib/site-packages`.
   - If any unauthorized or relative directory is detected in `sys.path` $\to$ Halt immediately (`GovernanceSecurityError: UNTRUSTED_MODULE_SEARCH_PATH_DETECTED`).

### 3.4 Canonical Tree Digest Algorithm `ACASH-RELEASE-TREE-V1`
To guarantee deterministic, byte-for-byte identical hashing between the External Release Authority and local verifiers with zero circularity:

#### 3.4.1 Strict Exclusion Set
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

#### 3.4.2 Strict Inclusion Set
All release-critical production codebase and governance tooling files:
- `src/**` (all production engine modules)
- `tools/governance/**` (all sovereign governance tools, excluding binaries in `bin/`)
- `pyproject.toml`, `uv.lock` (frozen package dependencies)

#### 3.4.3 Canonical Tree Digest Formulation
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

### 3.5 `ReleaseManifest` Schema
```python
class ReleaseManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int = Field(default=1, description="Schema version.")
    release_tag: str = Field(description="Audited release tag, e.g. v1.0.0-gate-b.")
    release_commit_sha: str = Field(description="Exact Git commit SHA of frozen release baseline.")
    launcher_artifact_sha256: str = Field(
        description="Exact SHA-256 of tools/governance/launch_runner.py."
    )
    executable_tree_digest: str = Field(
        description="Canonical SHA-256 tree digest using ACASH-RELEASE-TREE-V1."
    )
    python_interpreter_sha256: str = Field(
        description="Exact SHA-256 of authoritative python.exe binary."
    )
    dependency_lock_digest: str = Field(
        description="Exact SHA-256 of uv.lock."
    )
    runtime_dependencies_tree_digest: str = Field(
        description="Deterministic SHA-256 tree digest using ACASH-RUNTIME-ENV-V1."
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
            "launcher_artifact_sha256": self.launcher_artifact_sha256,
            "executable_tree_digest": self.executable_tree_digest,
            "python_interpreter_sha256": self.python_interpreter_sha256,
            "dependency_lock_digest": self.dependency_lock_digest,
            "runtime_dependencies_tree_digest": self.runtime_dependencies_tree_digest,
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

## 6. OS-Level Capability & Windows Token Privilege Boundary

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
│ • Interactive TTY Execution ONLY (Anti-Pipe Hygiene)   │       │ • Launched via: acash-bootstrapper.exe & launcher.py   │
│ • Asserts sys.stdin.isatty() == True                   │       │ • Python Isolated Mode: -I -s -E                       │
│ • Hardware-Backed User Presence: YubiKey PIV Ed25519   │       │ • Unprivileged Windows Process Token (Real Win32 Token)│
│ • PIN Policy = Always, Touch Policy = Always           │       │ • Sanitized sys.path: No CWD, no injection             │
│ • Hardware Secure Element Generates Ed25519 Signature  │       │ • Static Dependency Closure: ZERO signing/keygen code  │
│ • Signs canonical HumanGORecord payload                │       │ • Ingests confirmation token via CLI argument          │
│ • Writes human_go_record.json artifact to disk         │       │ • Strictly Verify-Only                                 │
│ • LACKS ledger mutation APIs                           │       │ • Ingests pre-existing artifact file from disk         │
│ • LACKS trust-store write APIs                         │       │ • Ingests sealed trust store (Read-Only)               │
│ • PROCESS EXITS IMMEDIATELY                            │       │ • Executes 2PC commit under single continuous lock     │
└────────────────────────────────────────────────────────┘       └────────────────────────────────────────────────────────┘
                            │                                                                 ▲
                            │                    PERSISTED ARTIFACT ONLY                      │
                            └──────────────────── var/gate_b/governance/ ─────────────────────┘
                                                 human_go_record.json
```

### 7.2 Hardware-Backed User Presence: YubiKey PIV Ed25519 Protocol
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
3. **Anti-Automation Guarantee:** Software automation, PTY allocations, background scripts, or remote callers cannot simulate physical capacitive touch on the hardware key sensor. Absence of physical touch causes the hardware token to abort with `SW_SECURITY_STATUS_NOT_SATISFIED` or timeout.
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
| **Python Execution Mode** | Interactive Standard Python | **Python Isolated Mode (`-I -s -E`)** |

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

## 9. Adversarial Verification Plan (23 Hard Boundary Tests)

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
| **Test B22: Pre-Execution Full Artifact Attestation**| Mutate launcher, python.exe, dependencies, or inject PYTHONPATH/CWD | Fails closed: `PreExecutionIntegrityError` / launcher abort |
| **Test B23: Native Bootstrapper Authenticode & Root Tampering Ban**| Mutate native bootstrapper binary or embedded root key | Fails closed: OS Authenticode invalid / bootstrapper abort |

---

## 10. Execution Phasing & Acceptance Criteria

The repair proceeds through four strictly gated steps. Advancing between steps requires explicit human auditor sign-off:

```text
Step 1: Formal Audit Approval of this Plan (Rev 9)
  │
  ▼
Step 2: Implement Tooling & Architectural Hardening (Zero Activation)
  ├─ tools/governance/bin/acash-bootstrapper.exe (Native Authenticode Signed Bootstrapper: R8-1 & R8-2)
  ├─ tools/governance/launch_runner.py (Pre-Execution Attestation & Python Isolated Mode Launcher)
  ├─ tools/governance/mint_human_go_record.py (Process A: YubiKey PIV Ed25519 Hardware Touch)
  ├─ src/acash/gate_b/runner.py (Process B: Verify-Only with Static Closure, sys.path Sanitization & Token Audit)
  ├─ tests/unit/gate_b/test_gate_b_governance_repair.py (23 Adversarial Tests)
  └─ Verification Criterion: ALL REPOSITORY TESTS PASS (Pre-repair baseline + new tests clean; MyPy clean)
  │
  ▼
Step 3: Governance Ceremonies & Storage Re-initialization
  ├─ Archive var/gate_b -> var/gate_b_incident_archive (Option 2)
  ├─ External Release Authority signs release_manifest.json (Commit SHA, Launcher, Python, Dependencies, Codebase)
  ├─ Execute Genesis Bootstrap Ceremony -> Sovereign signs genesis_bootstrap_manifest.json
  ├─ Execute Trust Anchor Ceremony -> Sovereign signs trust_anchor_manifest.json & seals trust_store.json
  ├─ Execute Hardware-Backed Human Authorization Ceremony -> Auditor signs human_go_record.json via YubiKey PIV
  └─ Human Audit Review of Fresh Activation Pack on GitHub
  │
  ▼
Step 4: Fresh Authoritative Gate B Activation Execution
  ├─ acash-bootstrapper.exe verifies signed release_manifest.json, launcher, interpreter, and environment
  ├─ Spawns launch_runner.py -> launches Process B in Isolated Mode (-I)
  ├─ Process B (Verify-Only Runner) executes Stages 1–9 under single continuous lock
  ├─ Verify COMMITTED on fresh root
  └─ Immediate Halt: STOP AGAIN (Live capital = $0.00; Live orders = 0)
```

> [!NOTE]
> **Acceptance Criterion Language:**  
> "All repository tests pass; exact count reported from actual execution. No regression from pre-repair baseline. Static type checker (MyPy) reports 0 errors across all source files. Tests B19 and B20 verified against actual Win32 host tokens and physical NTFS filesystem. Test B22 verified by asserting pre-execution launcher abort under launcher tampering, interpreter tampering, dependency mutation, and PYTHONPATH injection. Test B23 verified by asserting native bootstrapper Authenticode/PE root rejection upon binary mutation."

---

## 11. Approval Sign-Off Block

```markdown
════════════════════════════════════════════════════════════════════════════════
    GATE B GOVERNANCE REPAIR PLAN (REV 9) — FORMAL AUDIT APPROVAL
════════════════════════════════════════════════════════════════════════════════

Governing Document:       docs/phase13/gate_b_governance_repair_plan.md (Rev 9)
Parent Incident Report:   docs/phase13/gate_b_forensic_reconciliation_report.md
Storage Resolution Mode:  OPTION 2: FORENSIC ARCHIVE & FRESH GENESIS ROOT
Incident Archive Path:    var/gate_b_incident_archive/ (Immutable NTFS Deny DACL)
Tier 0 OS Policy:         Windows Authenticode & WDAC Code Signing Enforcement
Tier 1 Bootstrapper:      acash-bootstrapper.exe (Authenticode Signed, PE .rdata Root Anchor)
Pre-Execution Launcher:   tools/governance/launch_runner.py (Attested by Release Manifest)
Runtime Environment:      Binds python.exe, uv.lock, and ACASH-RUNTIME-ENV-V1
Python Isolation:         Strict Isolated Mode (-I -s -E), Canonical Absolute Paths
Canonical Tree Digest:    ACASH-RELEASE-TREE-V1 (Strict Exclusion Set & Lexicographical Ordering)
Release Authority:        release_manifest.json (Ed25519 Signed by External Release Authority)
Root Anchor Governance:   PE .rdata Section of Native Bootstrapper (Zero Runtime Override)
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
