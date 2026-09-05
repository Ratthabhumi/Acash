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
- **B23.2 (PENDING PHYSICAL PROOF):** Host Application-Control policy rejected execution (`NtCreateUserProcess` / `NtCreateSection`).

---

## 2. Host Prerequisites

The target machine MUST be an authoritative **Designated Governance Host** satisfying:
1. **Operating System:** Windows 11 Enterprise / Pro / Server (with App Control / WDAC or AppLocker deployed).
2. **Policy Enforcement State:**
   - **App Control for Business (WDAC):** `Win32_DeviceGuard.UsermodeCodeIntegrityPolicyEnforcementStatus == 2` (**Enforced**).
   - **OR AppLocker:** `AppIDSvc` running with enforced EXE rules.
   - *Note on Microsoft status values for UMCI:*
     - `0` = Off / Disabled
     - `1` = Audit Mode (generates Event 3076, does NOT block execution)
     - `2` = Enforced Mode (generates Event 3077, BLOCKS execution)
3. **Event Logging:** `Microsoft-Windows-CodeIntegrity/Operational` (for WDAC) or `Microsoft-Windows-AppLocker/EXE and DLL` (for AppLocker) enabled.

---

## 3. Package Contents

- `validate_b23_2_enforcement.ps1`: Automated 5-step PowerShell validation harness.
- `template_08_final_b23_2_verdict.json`: Canonical baseline unexecuted verdict schema.
- Output directory: `var/governance/b23_2_dossier/` (8-part structured evidence dossier).

---

## 4. Execution Instructions

On the Designated Governance Host, open a PowerShell prompt and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\governance\b23_2_host_validation\validate_b23_2_enforcement.ps1
```

### Expected Execution Flow
1. **Step 1:** Inspects host policy state. If neither WDAC (UMCI == 2) nor AppLocker (Enforce rules) is active, halts immediately with `ENVIRONMENT NOT SUFFICIENT`.
2. **Step 2:** Copies `acash-bootstrapper.exe` and mutates a byte to create an unauthorized test artifact.
3. **Step 3:** Attempts execution; asserts that the host Application-Control policy rejected execution (Win32 Error `1260` `ERROR_ACCESS_DISABLED_BY_POLICY` or NTSTATUS `0xC0000428`).
4. **Step 4:** Extracts the applicable Block event (Event ID `3077` for WDAC or Event ID `8004` for AppLocker) and corroborating Event ID `3089` (Signature Information) via ActivityId correlation.
5. **Step 5:** Emits the complete 8-part cryptographic evidence dossier to `var/governance/b23_2_dossier/`.

---

## 5. Required 8-Part Evidence Dossier Structure

Upon execution on the Designated Governance Host, the package creates 8 discrete JSON evidence files in `var/governance/b23_2_dossier/`:

| File | Content Description |
|---|---|
| `01_policy_state.json` | Host policy engine, KMCI/UMCI status, and AppIDSvc status |
| `02_policy_identity.json` | Active policy GUID, friendly name, OS version |
| `03_valid_artifact.json` | Source valid binary path, size, and SHA-256 digest |
| `04_tampered_artifact.json` | Tampered test artifact path, mutation offset, and SHA-256 digest |
| `05_execution_attempt.json` | Execution parameters, invocation timestamp, and OS rejection error code |
| `06_block_event.json` | Raw XML and structured fields of Event 3077 (WDAC) or 8004 (AppLocker) + Event 3089 correlation |
| `07_hash_correlation.json` | Cryptographic correlation matching artifact SHA-256 and execution time window |
| `08_final_b23_2_verdict.json` | Master evaluation verdict (emitted as PASS only upon full execution) |

### Baseline Unexecuted Schema (`template_08_final_b23_2_verdict.json`):
To prevent automated parsers or auditors from mistakenly interpreting documentation examples as completed physical proof, the baseline unexecuted artifact explicitly records `NOT_PROVEN`:

```json
{
  "test_id": "B23.2",
  "status": "TEMPLATE_UNEXECUTED",
  "verdict": "NOT_PROVEN",
  "policy_mode": "UNKNOWN",
  "policy_engine": "UNKNOWN",
  "policy_identity": "UNASSIGNED",
  "artifact_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "attempt_timestamp_utc": null,
  "execution_result": "NOT_EXECUTED",
  "process_started": null,
  "os_error_code": null,
  "os_error_message": null,
  "event_id": null,
  "event_log": null,
  "event_artifact_match": false,
  "corroborating_event_3089_found": false,
  "certified_at_utc": null
}
```

### Authoritative Post-Execution Verdict Schema (Emitted on Designated Host):
Only when executed on the Designated Governance Host with active policy enforcement (`UMCI == 2` or AppLocker Enforced) does `validate_b23_2_enforcement.ps1` dynamically emit the verified verdict:

```json
{
  "test_id": "B23.2",
  "status": "AUTHORITATIVE_RESULT",
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
  "corroborating_event_3089_found": true,
  "certified_at_utc": "2026-09-05T12:00:02.000000Z"
}
```

This 8-part dossier serves as the definitive physical evidence required to promote Assertion B23.2 from **NOT PROVEN** to **PASS**.


