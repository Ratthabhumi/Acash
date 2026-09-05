# B23.2 Host Application-Control Enforcement Validation Package

> **Package ID:** `ACASH-PKG-B23-2-HOST-VALIDATION-v1.0`  
> **Target Requirement:** Phase 13 / Gate B Governance Repair (Rev 10 Assertion B23.2)  
> **Substrate Target:** Designated Windows Governance / Enforcement Host  
> **Status:** Execution-Ready Package  

---

## 1. Purpose

This package provides the standalone, automated verification harness to physically prove **Assertion B23.2 (Host Application-Control Execution Enforcement)** on a designated Windows host configured with App Control for Business / Windows Defender Application Control (WDAC) or AppLocker in **Enforce Mode**.

It formally resolves the gap between:
- **B23.1 (PASS):** WinVerifyTrust object/PE cryptographic verification (user-mode API).
- **B23.2 (PENDING PHYSICAL PROOF):** Operating system kernel process-creation denial (`NtCreateUserProcess` / `NtCreateSection`).

---

## 2. Host Prerequisites

The target machine MUST be an authoritative **Designated Governance Host** satisfying:
1. **Operating System:** Windows 11 Enterprise / Pro / Server (with App Control / WDAC or AppLocker deployed).
2. **Policy Enforcement State:**
   - `Win32_DeviceGuard.UsermodeCodeIntegrityPolicyEnforcementStatus == 2` (**Enforced**).
   - *Note on Microsoft status values:*
     - `0` = Off / Disabled
     - `1` = Audit Mode (generates Event 3076, does NOT block execution)
     - `2` = Enforced Mode (generates Event 3077, BLOCKS execution)
3. **Event Logging:** `Microsoft-Windows-CodeIntegrity/Operational` channel enabled.

---

## 3. Package Contents

- `validate_b23_2_enforcement.ps1`: Automated 5-step PowerShell validation harness.
- Output artifact: `var/governance/b23_2_enforcement_evidence.json` (Structured cryptographic evidence dossier).

---

## 4. Execution Instructions

On the Designated Governance Host, open an elevated or standard PowerShell prompt and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\governance\b23_2_host_validation\validate_b23_2_enforcement.ps1
```

### Expected Execution Flow
1. **Step 1:** Verifies `UsermodeCodeIntegrityPolicyEnforcementStatus == 2`. If `0` or `1`, halts immediately with `ENVIRONMENT NOT SUFFICIENT`.
2. **Step 2:** Copies `acash-bootstrapper.exe` and mutates a byte to create an unauthorized test artifact.
3. **Step 3:** Attempts execution; asserts that the OS kernel denies process creation (Win32 Error `1260` `ERROR_ACCESS_DISABLED_BY_POLICY` or NTSTATUS `0xC0000428`).
4. **Step 4:** Extracts Code Integrity Event ID `3077` (Block event) from `Microsoft-Windows-CodeIntegrity/Operational`.
5. **Step 5:** Verifies correlation between artifact SHA-256, path, and timestamp; emits sealed JSON evidence to `var/governance/b23_2_enforcement_evidence.json`.

---

## 5. Evidence Dossier Schema

Upon successful execution, the resulting dossier contains:
```json
{
  "test_id": "B23.2",
  "test_name": "Host Application-Control Execution Enforcement",
  "verdict": "PASS",
  "host_telemetry": {
    "computer_name": "...",
    "kernel_mode_ci_status": 2,
    "user_mode_ci_status": 2,
    "policy_enforcement_mode": "ENFORCE (Value == 2)"
  },
  "execution_attempt": {
    "artifact_path": "...",
    "artifact_sha256": "...",
    "execution_timestamp_utc": "...",
    "process_blocked": true,
    "os_interception_details": "..."
  },
  "security_event": {
    "log_name": "Microsoft-Windows-CodeIntegrity/Operational",
    "event_id": 3077,
    "event_timestamp_utc": "...",
    "provider_name": "Microsoft-Windows-CodeIntegrity",
    "event_xml": "..."
  },
  "certified_at_utc": "..."
}
```

This dossier serves as the definitive physical evidence required to promote Assertion B23.2 from **NOT PROVEN** to **PASS**.
