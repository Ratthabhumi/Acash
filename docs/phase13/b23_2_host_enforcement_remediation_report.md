# ACASH Gate B Governance Repair: B23.2 Host Application-Control Enforcement Remediation Report

> **Document ID:** `ACASH-REPORT-GATEB-B23-REMEDIATION-v1.0`  
> **Related Documents:** [`docs/phase13/gate_b_step2_evidence_pack.md`](gate_b_step2_evidence_pack.md), [`docs/phase13/gate_b_activation_plan.md`](gate_b_activation_plan.md) (Rev 10 Baseline)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief)  
> **Directive:** Auditor Directive — B23.2 Remediation Only (2026-09-05)  
> **Status:** **MANDATORY HALT — B23.1 PASSED, B23.2 NOT PROVEN (ENVIRONMENT NOT SUFFICIENT)**  

---

## 1. Executive Summary & Governance Status

In accordance with the Auditor Directive concerning Phase 13 / Gate B Governance Repair (Rev 10 Step 2):
1. **Implementation State Preserved:** The current Step 2 code implementation, native x64 MSVC bootstrapper (`tools/governance/bin/acash-bootstrapper.exe`), launcher, Process A minting tool, and tests B1–B22 remain intact and verified.
2. **B23 Formally Decoupled:** B23 is split into two distinct, independent assertions:
   - **B23.1 — Authenticode Trust Verification:** **PASS** (Cryptographic verification via `WinVerifyTrust` strictly rejects unsigned and tampered binaries).
   - **B23.2 — Host Application-Control Execution Enforcement:** **NOT PROVEN (ENVIRONMENT NOT SUFFICIENT)** (The current development machine does not have an active User-Mode Code Integrity or AppLocker policy in Enforce mode).
3. **No False Equivalence:** ACASH explicitly recognizes that `WinVerifyTrust` is a user-mode API for object/PE trust verification; it is **NOT** by itself evidence of operating system kernel-level process-creation denial.
4. **Strict Operational Boundaries Maintained:**
   - **Step 3 Ceremony:** **STRICTLY BLOCKED**
   - **Step 4 Activation:** **STRICTLY BLOCKED**
   - **Gate B Activation:** **STRICTLY BLOCKED**
   - **Slice 3:** **STRICTLY BLOCKED**
   - **Live Capital:** **$0.00 (HARD-LOCKED)**
   - **Live Orders:** **0**
   - **Broker Connectivity:** **DISCONNECTED**
   - **Live Credentials:** **NONE INTRODUCED / ZERO ACCESS**

---

## 2. Technical Distinction: B23.1 vs B23.2

To uphold institutional epistemic discipline (`Implementation Correctness` $\ne$ `Contract Correctness` $\ne$ `Host Enforcement`), the two layers are separated:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│             B23.1: AUTHENTICODE OBJECT TRUST VERIFICATION                   │
│   • Evaluator: WinVerifyTrust API (wintrust.dll)                            │
│   • Mechanism: Parses PE header, validates PKCS#7 / Authenticode signature,│
│     and verifies PE hash against catalog/embedded signature.                │
│   • Purpose: Proves artifact integrity and cryptographic lineage.           │
│   • Scope: In-process programmatic verification.                            │
│   • Status: PASSED (Unsigned -> 0x800B0100; Tampered -> 0x800B0100/digest)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             B23.2: HOST APPLICATION-CONTROL EXECUTION ENFORCEMENT           │
│   • Evaluator: Host Application-Control Engine (WDAC CI.dll or AppLocker)   │
│   • Universal Policy Assertion: Host Application-Control policy rejected    │
│     execution (Never a blanket 'kernel block' without identifying engine)   │
│   • Mechanism Distinction:                                                  │
│     - WDAC: Kernel CI driver (ci.dll) blocks execution at section creation  │
│     - AppLocker: AppID.sys driver / AppIDSvc blocks execution on launch     │
│   • Purpose: Proves host policy prevents execution of unauthorized binaries.│
│   • Status: NOT PROVEN ON CURRENT HOST (ENVIRONMENT NOT SUFFICIENT)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> **GOVERNANCE INVARIANT:**  
> A passing `WinVerifyTrust` result proves only that the cryptographic verification logic correctly detects invalid signatures. It does **NOT** prove that the host Application-Control policy will intercept and refuse to execute an unauthorized executable when an operator or script invokes it.

---

## 3. Physical Telemetry of Current Development Host

Direct, non-destructive telemetry was gathered from the local development host:

### 3.1 DeviceGuard & Code Integrity Query
```powershell
Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard | Select-Object -Property *
```
**Telemetry Output:**
- `CodeIntegrityPolicyEnforcementStatus`: **`2`** (Kernel-mode HVCI/KMCI is active)
- `UsermodeCodeIntegrityPolicyEnforcementStatus`: **`0`** (**DISABLED / NOT ENFORCED**; Microsoft values: `0 = Off`, `1 = Audit`, `2 = Enforced`)
- `VirtualizationBasedSecurityStatus`: `2` (VBS running)
- `SecurityServicesRunning`: `{2}` (Credential Guard / HVCI)

### 3.2 AppLocker Service Status Query
```powershell
Get-Service AppIDSvc, AppID
```
**Telemetry Output:**
- `AppIDSvc` (Application Identity): **`Stopped`**
- `AppID` (AppID Driver): **`Stopped`**
- `Get-AppLockerPolicy`: Cmdlet not recognized on this host management surface.

### 3.3 Live Execution Trial
An execution attempt was performed using the newly compiled, unsigned native bootstrapper:
```powershell
tools\governance\bin\acash-bootstrapper.exe --help
```
**Observed Execution Result:**
- The process was created and executed by the Windows kernel loader.
- The process executed application initialization logic and exited with:
  ```text
  [CRITICAL BOOTSTRAP FAILURE] RELEASE_MANIFEST_MISSING: Release manifest not found: var\governance\release\acash_release_manifest.json
  ```
- **Forensic Finding:** The fact that the process executed and reached application-level error handling is **direct empirical proof** that the host OS did **not** block process creation at the kernel loader boundary.

### 3.4 Host Assessment Verdict
$$\boxed{\mathbf{CURRENT\ HOST\ VERDICT:\ ENVIRONMENT\ NOT\ SUFFICIENT\ FOR\ B23.2}}$$

The local development host does not enforce User-Mode Code Integrity (`UMCI = 0`) and does not run an active AppLocker service. Therefore, B23.2 cannot be legitimately proven on this workstation in its current state.

---

## 4. Architectural Separation: Dev Host vs Designated Governance Host

Attempting to enforce machine-wide Windows Defender Application Control (WDAC) or AppLocker policies on an active developer laptop risks rendering the developer environment unusable, disrupting compilation tools, IDEs, or Python runtimes, and conflates distinct operational roles.

ACASH adopts a clean engineering separation:

```text
┌────────────────────────────────────────┐       ┌────────────────────────────────────────┐
│            DEVELOPMENT HOST            │       │      DESIGNATED GOVERNANCE HOST        │
├────────────────────────────────────────┤       ├────────────────────────────────────────┤
│ • Native Compilation (MSVC x64)        │       │ • Authoritative Execution Substrate    │
│ • Python Virtualenv & Dependencies     │  ──►  │ • Deployed WDAC / App Control Policy   │
│ • Unit & Integration Tests (B1–B22)    │       │   in ENFORCE Mode (UMCI = 1)           │
│ • Authenticode Trust Check (B23.1)     │       │ • Authenticode-Signed Release Artifact │
│ • Git Repository Management            │       │ • Physical B23.2 Kernel Denial Proof   │
└────────────────────────────────────────┘       └────────────────────────────────────────┘
```

> **Invariant:** Development and unit testing are performed on the Development Host. Authoritative OS-level application-control enforcement (B23.2) is demonstrated on the **Designated Governance Host**.

---

## 5. Formal Host-Validation Procedure for B23.2

When validating B23.2 on the Designated Governance Host, the following 5-step verification protocol must be executed and recorded:

```text
Step 1: Verify Host Policy State (Enforce Mode)
               │
               ▼
Step 2: Attempt Execution of Unauthorized / Unsigned Artifact
               │
               ▼
Step 3: Verify Kernel Denies Process Creation (Error Code Captured)
               │
               ▼
Step 4: Capture Host Code Integrity / AppLocker Event Log
               │
               ▼
Step 5: Cryptographic Correlation (Hash, Path, Timestamp)
```

### Step 1: Verify Host Policy State
Confirm that User-Mode Code Integrity or AppLocker is active in **Enforce Mode** (`UsermodeCodeIntegrityPolicyEnforcementStatus == 2`):
```powershell
$ci = Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard
# UsermodeCodeIntegrityPolicyEnforcementStatus: 0 = Off, 1 = Audit, 2 = Enforced
if ($ci.UsermodeCodeIntegrityPolicyEnforcementStatus -ne 2) {
    throw "Host policy is NOT in Enforce mode (Current status: $($ci.UsermodeCodeIntegrityPolicyEnforcementStatus); Expected: 2 [Enforced])"
}
```
- **Required Assertion:** `UsermodeCodeIntegrityPolicyEnforcementStatus == 2` (Enforced Mode; note that `1` is Audit Mode only).

### Step 2: Attempt Execution of Unauthorized Artifact
Attempt to launch an unsigned, untrusted, or tampered executable artifact (`acash-bootstrapper.exe`):
```powershell
$targetExe = "C:\ACASH\governance\bin\unauthorized-bootstrapper.exe"
$process = Start-Process -FilePath $targetExe -ArgumentList "--help" -PassThru -ErrorAction SilentlyContinue
```

### Step 3: Verify Host Application-Control Policy Rejects Execution
Assert that process creation is rejected directly by the active policy engine:
- **Expected Return:** Process fails to launch (`$process` is `$null` or throws Win32 exception).
- **Expected Win32 / NTSTATUS Error Codes:**
  - `0xC0000428` (`STATUS_ACCESS_DISABLED_BY_POLICY_DEFAULT`)
  - `1260` (`ERROR_ACCESS_DISABLED_BY_POLICY`: *"This program is blocked by group policy."*)
  - Zero application bytes executed (zero stdout/stderr from application).

### Step 4: Capture Host Security Event Log
Query the security event log channel corresponding to the active policy engine:
- **For WDAC / App Control for Business:** Query `Microsoft-Windows-CodeIntegrity/Operational` for Event ID **`3077`** (Block event; note that `3076` is Audit Mode only).
- **For AppLocker:** Query `Microsoft-Windows-AppLocker/EXE and DLL` for Event ID **`8004`** (Block event; note that `8003` is Audit Mode only).

```powershell
# Query WDAC Operational Log for Block Event (Event ID 3077)
Get-WinEvent -FilterHashtable @{
    LogName = 'Microsoft-Windows-CodeIntegrity/Operational'
    Id = 3077
} -MaxEvents 1 | Format-List TimeCreated, Id, Message
```

### Step 5: Cryptographic Correlation
Verify that the blocked event directly corresponds to the target test artifact:
1. **File Path:** Matches the exact execution path of the test binary.
2. **SHA-256 Hash:** Matches the SHA-256 digest of the test binary.
3. **Timestamp:** Correlates with the execution attempt (within $\pm 2$ seconds).

---

### 5.1 Required 8-Part Evidence Dossier Specification

When executed on the Designated Governance Host, the validation harness generates an authoritative 8-part JSON dossier:

```text
var/governance/b23_2_dossier/
├── 01_policy_state.json        # Host policy engine, KMCI/UMCI status, AppIDSvc status
├── 02_policy_identity.json     # Active policy GUID, friendly name, version
├── 03_valid_artifact.json       # Signed release artifact hash, path, and Authenticode details
├── 04_tampered_artifact.json    # Test unauthorized artifact path, size, and SHA-256 digest
├── 05_execution_attempt.json    # Execution invocation parameters, timestamp, and OS error code
├── 06_block_event.json          # Raw XML and structured fields of Event 3077 (WDAC) or 8004 (AppLocker)
├── 07_hash_correlation.json     # Cryptographic proof matching artifact digest to event payload
└── 08_final_b23_2_verdict.json  # Master signed evaluation verdict
```

#### Canonical `08_final_b23_2_verdict.json` Schema:
```json
{
  "test_id": "B23.2",
  "verdict": "PASS",
  "policy_mode": "ENFORCED",
  "policy_engine": "WDAC",
  "policy_identity": "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}",
  "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "attempt_timestamp_utc": "2026-09-05T12:00:00.000000Z",
  "execution_result": "BLOCKED",
  "process_started": false,
  "os_error_code": 1260,
  "os_error_message": "This program is blocked by group policy.",
  "event_id": 3077,
  "event_log": "Microsoft-Windows-CodeIntegrity/Operational",
  "event_artifact_match": true,
  "certified_at_utc": "2026-09-05T12:00:02.000000Z"
}
```

---

## 6. Adversarial Assertion Results (24 Assertions: B1–B22, B23.1, B23.2)

The adversarial test suite has been updated to truthfully reflect this decoupled state:

```powershell
# Command:
uv run pytest tests/unit/gate_b/test_gate_b_governance_repair.py -v
```
**Assertion Breakdown:**
- **B1–B22 (22 Assertions):** **`22 PASSED`** (AST bans, DACL protections, key revocations, genesis manifests, token privilege checks).
- **B23.1 (1 Assertion):** **`1 PASSED`** (`test_b23_1_native_bootstrapper_authenticode_trust_verification` proves WinVerifyTrust fail-closed).
- **B23.2 (1 Assertion):** **`1 SKIPPED / NOT PROVEN`** (`test_b23_2_host_application_control_enforcement` skipped on dev host due to `UMCI == 0`).

**Summary:** **24 Assertions Total: 23 PASSED, 1 SKIPPED / NOT PROVEN (B23.2)**


---

## 7. Mandatory Halt & State Verification

```text
════════════════════════════════════════════════════════════════════════════════
                        MANDATORY GOVERNANCE HALT
════════════════════════════════════════════════════════════════════════════════
[STATUS] STEP 2 IMPLEMENTATION: COMPLETE
[ASSERTION B1–B22] ALL PASSED (22/22)
[ASSERTION B23.1] PASSED (WinVerifyTrust Fail-Closed)
[ASSERTION B23.2] NOT PROVEN (DEVELOPMENT ENVIRONMENT NOT SUFFICIENT)
[MANDATORY HALT] HALTED FOR DESIGNATED ENFORCEMENT HOST ASSIGNMENT
[STEP 3 CEREMONY] STRICTLY BLOCKED (Awaiting B23.2 Resolution & Signed Release)
[STEP 4 ACTIVATION] STRICTLY BLOCKED
[SLICE 3 FIRST LIVE ORDER] STRICTLY BLOCKED
[LIVE CAPITAL] $0.00 (HARD-LOCKED)
[LIVE ORDERS] 0
[BROKER CONNECTION] STRICTLY DISCONNECTED
[CREDENTIAL BOUNDARY] ZERO LIVE CREDENTIALS INTRODUCED
════════════════════════════════════════════════════════════════════════════════
```

---

## 8. Verification Ledger

```markdown
### Verification Ledger
- Implementation Status: COMPLETE (Step 2 Implementation Locked)
- B23.1 Status: VERIFIED (WinVerifyTrust Fail-Closed Authenticode Check Passed)
- B23.2 Status: NOT PROVEN (Deferred to Designated Governance Enforcement Host)
- Contract Enforcement: STRICT FAIL-CLOSED (Zero Unverified Claims)
- Local Test Suite: VERIFIED (23 passed, 1 skipped in 4.10s)
- Full Repository Suite: VERIFIED (1431 passed, baseline clean)
- Type Checker (MyPy): VERIFIED (295 files clean, zero errors)
- Live Capital Authority: STRICTLY HARD-LOCKED ($0.00 Live Capital; Live Orders = 0)
- Remote CI Status: Ready to push documentation update
- Methodological Invariant: Developer Host != Designated Governance Host; WinVerifyTrust != Kernel Process Denial.
```
