# Phase 13: Gate B Governance Repair Plan (Revision 1)

**Document ID:** `ACASH-DOC-P13-GATE-B-GOVERNANCE-REPAIR-PLAN-REV1`  
**Parent Incident Report:** `docs/phase13/gate_b_forensic_reconciliation_report.md` (Commit `affc5ce`)  
**Governing Specification Baseline:** `docs/phase13/slice2_gate_b_plan.md` (Rev 20 Frozen Baseline, Spec Commit `647ba75`)  
**Current System State:**  
- Transaction Persistence: `COMMITTED` (`339ce2fd-a215-4569-9bf4-84a6812175d1` on physical NTFS)  
- Authorization Provenance: `INVALID` (Self-authorizing runtime loop)  
- Governance State: `QUARANTINED / NOT AUTHORIZED`  
- Trading Authority: `STRICTLY BLOCKED`  
- Live Capital Deployed: `$0.00`  
- Live Orders Transmitted: `0`  
**Document Status:** DRAFT — SUBMITTED FOR FORMAL AUDIT REVIEW (ZERO EXECUTION)

---

## 1. Executive Summary & Problem Definition

During the Gate B activation procedure on 2026-09-05, the runner script executed a **closed-loop self-authorizing transaction**: it generated its own sovereign human Ed25519 keypair at runtime, inserted the public key into a freshly created trust store, synthesized a `HumanGORecord`, signed the record with its own in-memory private key, verified the signature against its own trust store, and committed the transaction.

While the two-phase commit storage mechanics (fsync barriers, Win32 flushes, pointer switch, directory promotion, NTFS DACL) executed correctly as software code, the **governance provenance is mathematically and organizationally invalid**.

This Governance Repair Plan defines the architectural remediation required to permanently eliminate the self-authorizing flaw, establish an independent sovereign trust-anchor ceremony, and guarantee that the activation runner operates strictly as a **Verify-Only Execution Engine**.

```text
┌────────────────────────────────────────────────────────────────────────┐
│             DEFECTIVE LOOP vs REPAIRED DECOUPLED ARCHITECTURE          │
├────────────────────────────────────────────────────────────────────────┤
│ ❌ DEFECTIVE LOOP (Incident 2026-09-05):                               │
│ Runner ──> generate_key() ──> write trust_store ──> sign ──> commit    │
│ (Self-authorizing; zero independent human evidence)                    │
├────────────────────────────────────────────────────────────────────────┤
│ ✅ REPAIRED DECOUPLED ARCHITECTURE (This Plan):                        │
│ 1. External Sovereign Key Ceremony (Offline / Hardware Key)            │
│                 │                                                      │
│                 ▼                                                      │
│ 2. Pre-Existing Immutable Trust Store (var/gate_b/trust_store.json)    │
│                 │                                                      │
│                 ▼                                                      │
│ 3. External HumanGORecord Minting & Signing (Independent Artifact)     │
│                 │                                                      │
│                 ▼                                                      │
│ 4. Activation Runner (STRICT VERIFY-ONLY):                             │
│    - Read pre-existing Trust Store (Fail-closed if writable)          │
│    - Read pre-existing HumanGORecord artifact                         │
│    - Verify signature & lineage (Zero keygen, zero self-signing)       │
│    - Execute 2PC Commit ONLY IF all external proofs hold              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Strict Governance Invariants (Non-Negotiable)

In strict accordance with `AGENTS.md` (Principles 1, 2, 3, 4, 5, 13), any repaired activation pathway must satisfy the following six hard invariants:

1. **Invariant 1: Pre-Existing Immutable Trust Anchor**  
   The `Ed25519TrustStore` must exist on physical disk **before** the activation runner is launched. The activation runner MUST NOT generate keys, add entries, or overwrite `trust_store.json`. If `trust_store.json` is missing or writable by the runner process, the transaction fails closed immediately (`DataContractError: TRUST_STORE_PROVENANCE_VIOLATION`).

2. **Invariant 2: Sovereign Key Separation**  
   The human governance private key (`app_priv`) must **never enter the activation runner process memory, environment, or repository**. The private key is held exclusively by the sovereign human auditor (offline/external ceremony).

3. **Invariant 3: Independent Pre-Approved `HumanGORecord` Artifact**  
   The `HumanGORecord` must be authored, signed, and serialized to disk by an external governance tool **prior** to running activation. The runner is strictly an ingestion consumer; it cannot synthesize, mutate, or sign a `HumanGORecord`.

4. **Invariant 4: Strict Verify-Only Runner Contract**  
   The runner codebase must contain **zero keypair generation routines**, **zero signing functions for human authority**, and **zero trust-store mutation code**. The runner's only cryptographic operation regarding human authority is `trust_store.verify(...)`.

5. **Invariant 5: Authenticated External Execution Token Binding**  
   Human execution authorization tokens (e.g., `P13-GATE-B-EXECUTION-GO-20260905`) must not be hardcoded as string literals in runner source code. The token must be supplied as an external explicit input parameter during invocation and validated against the signed authorization payload.

6. **Invariant 6: Forensic Lineage Preservation**  
   Existing physical artifacts from the incident (`339ce2fd-...`) in `var/gate_b` and git history (`0bd859c`, `affc5ce`) must remain preserved for complete auditability. They must not be silently wiped or deleted without formal quarantine recording.

---

## 3. Detailed Architecture of the Repaired Governance Model

The repair decouples the activation lifecycle into three distinct, non-overlapping phases:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 PHASE A: SOVEREIGN TRUST ANCHOR CEREMONY                │
├─────────────────────────────────────────────────────────────────────────┤
│ - Executed OFFLINE by Human Governance Authority                        │
│ - Generates KEY_HUMAN_GOVERNANCE_AUDITOR_001                            │
│ - Generates KEY_STORAGE_ENGINE_PROD_001                                 │
│ - Emits canonical, signed var/gate_b/trust_store.json                   │
│ - Sets NTFS Read-Only DACL on trust_store.json                          │
│ - Output: Permanent, immutable trust anchor on disk                     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                 PHASE B: EXTERNAL HUMAN GO MINTING CEREMONY             │
├─────────────────────────────────────────────────────────────────────────┤
│ - Executed OFFLINE by Human Governance Auditor                          │
│ - Ingests certified Gate A audit digest & draft LiveAuthorization       │
│ - Ingests current persistent ledger head                                │
│ - Constructs canonical HumanGORecord payload                            │
│ - Signs payload using sovereign private key (external to runner)        │
│ - Writes var/gate_b/governance/human_go_record.json                     │
│ - Output: Standalone, verifiable, pre-existing cryptographic artifact   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│              PHASE C: ACTIVATION RUNNER (STRICT VERIFY-ONLY)            │
├─────────────────────────────────────────────────────────────────────────┤
│ - Ingests external execution token via CLI parameter                    │
│ - Loads existing trust_store.json (Asserts immutable / read-only)       │
│ - Loads existing human_go_record.json artifact                          │
│ - Verifies approver key status == ACTIVE                                │
│ - Verifies Ed25519 signature against trust store                        │
│ - Verifies draft authorization digest matches record payload            │
│ - Verifies Gate A lineage & ledger head continuity CAS                  │
│ - Enters single continuous exclusive transactional lock (Stages 6–8)    │
│ - Executes 2-Phase Commit & atomic pointer transition                   │
│ - Halts immediately: STOP AGAIN                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Quarantined Storage State Resolution Strategy

The current NTFS storage root contains transaction `339ce2fd-a215-4569-9bf4-84a6812175d1` in `COMMITTED` state with `INVALID` authorization provenance.

Two governance-compliant options exist to resolve this quarantined state:

### Option 1: Formal On-Disk Quarantine Transition (Recommended)
1. Invoke `GateBRecoveryCoordinator.quarantine_transaction(tx_id="339ce2fd-...", reason="SELF_AUTHORIZING_RUNNER_LOOP")`.
2. Transition `tx_state` to `QUARANTINED` and `system_safety_mode` to `QUARANTINE_LOCKED`.
3. Append formal forensic entry to `journal/quarantine_log.json`.
4. The quarantine state proves on physical disk that the defective transaction was detected, halted, and safely frozen.
5. Initialize a fresh, repaired ledger root (`var/gate_b_v2` or cleanly archived ledger) for the fresh activation transaction.

### Option 2: Forensic Archive & Fresh Genesis Ledger
1. Move `var/gate_b` $\to$ `var/gate_b_incident_20260905_archive/` (retaining full NTFS ACLs and bitwise file integrity).
2. Record SHA-256 manifest of all archived files in the repair audit pack.
3. Initialize pristine `var/gate_b` with pre-authenticated `trust_store.json` (Phase A) starting cleanly from `GENESIS_HEAD_DIGEST`.

> [!IMPORTANT]
> **Auditor Decision Required:** Please confirm whether you prefer **Option 1 (On-disk quarantine lock)** or **Option 2 (Forensic archive & clean genesis root)** during audit review.

---

## 5. Required Codebase & Tooling Changes

To implement the repaired architecture, the following surgical changes will be made (pending your plan approval):

### 5.1 New External Tool: `tools/governance/mint_human_go_record.py`
A standalone, offline CLI utility for the Human Auditor:
- Accepts: Draft authorization path, current ledger root, approver key path.
- Computes canonical signed payload bytes.
- Signs payload using provided private key.
- Emits canonical `human_go_record.json`.
- Runs completely outside the execution runtime.

### 5.2 Refactored Activation Runner: `src/acash/gate_b/runner.py`
The production activation runner will be refactored to enforce:
```python
class GateBActivationRunner:
    def execute_activation(
        self,
        ledger_root: Path,
        draft_auth_path: Path,
        signed_go_record_path: Path,
        execution_token: str,
    ) -> GateBActivationReceipt:
        # 1. Assert trust_store.json exists and is NOT writable by current process
        # 2. Load trust store strictly read-only
        # 3. Load signed_go_record_path (assert pre-existing file)
        # 4. Verify approver key is in trust store and ACTIVE
        # 5. Verify Ed25519 signature over go_record payload
        # 6. Verify draft authorization digest matches record
        # 7. Verify Gate A evidence lineage
        # 8. Single continuous lock: CAS head check -> Reserve UUIDv4 -> 2PC Commit
        # 9. Verify COMMITTED -> STOP AGAIN
```
**Strict Prohibitions in Runner:**
- `Ed25519Signer.generate_key_pair()` $\to$ **BANNED** in runner module.
- `StoragePlatformUtils.write_file_durable(trust_store_path, ...)` $\to$ **BANNED** in runner module.
- Hardcoded confirmation token $\to$ **BANNED**; must be passed via CLI argument.

---

## 6. Adversarial Verification Plan

Before re-attempting Gate B activation, the repaired architecture must pass a dedicated adversarial test suite attacking the exact flaws identified in the incident:

1. **Test A1: Runner Rejects Self-Generated Key**  
   Assert that runner fails closed if trust store does not contain the signing key ID prior to launch.
2. **Test A2: Runner Rejects Runtime Trust Store Overwrite**  
   Assert that runner cannot modify, write, or replace `trust_store.json`.
3. **Test A3: Runner Fails Closed on Missing `human_go_record.json`**  
   Assert that runner raises `DataContractError` if no pre-existing signed artifact is provided.
4. **Test A4: Runner Rejects Forged / Tampered `HumanGORecord`**  
   Assert that runner raises `CryptographicVerificationError` if payload or signature is altered by 1 bit.
5. **Test A5: Runner Enforces Continuous Lock (Stages 6–8)**  
   Assert that lock release between Stage 6 and Stage 8 raises `DataContractError: TRANSACTION_LOCK_INTERRUPTED`.
6. **Test A6: Full Regression & MyPy Verification**  
   Run full regression suite (1,408+ tests) and MyPy (291 source files) to guarantee zero regressions.

---

## 7. Approval Sign-Off Block

```markdown
════════════════════════════════════════════════════════════════════════════════
    GATE B GOVERNANCE REPAIR PLAN (REV 1) — FORMAL AUDIT APPROVAL
════════════════════════════════════════════════════════════════════════════════

Governing Document:       docs/phase13/gate_b_governance_repair_plan.md (Rev 1)
Parent Incident:          docs/phase13/gate_b_forensic_reconciliation_report.md
Target Remediation Scope: Decoupled Sovereign Key, Immutable Trust Store,
                          Verify-Only Activation Runner
Storage Quarantine Mode:  [ OPTION 1: On-Disk Quarantine / OPTION 2: Forensic Archive ]
Live Capital Authority:   $0.00 (Zero Capital Deployed)
Broker Execution:         PROHIBITED (Slice 3 Strictly Blocked)

Auditor Decision:         [ PENDING REVIEW / APPROVED / REVISION REQUIRED ]

Human Governance Auditor: _______________________________________________

Date & Time (UTC):        _______________________________________________

Decision Token:           _______________________________________________
════════════════════════════════════════════════════════════════════════════════
```
