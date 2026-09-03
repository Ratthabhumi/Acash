# Phase 13 Slice 1: Gate A Pre-Live Certification Evidence Pack

**Document ID:** `ACASH-DOC-P13-GATE-A-EVIDENCE`  
**Governing Plan:** `docs/phase13/PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV3.md` (SHA-256: `8D871167AAA9FAC99261151850E8CC9E81688E8ED49BC3E350A7F79CF6E77391`)  
**Recovery Runbook:** `docs/phase13/recovery_runbook.md` (SHA-256: `D4C4A59A4F3A3897F6309B2E9E8C4E872B8E3624AEF6D91200FB795ED9197EDE`)  
**Test Suite:** `tests/integration/test_phase13_slice1_gate_a.py` (SHA-256: `EC2152E2C66DD82B23315B3B13D20213662579FED74C5A9A5044CBFF13D35EBA`)  
**Execution Timestamp:** 2026-09-03T14:24:58Z  
**Git Baseline Commit:** `ba25fcf0d66310b81b552b07610b49d001707f20`  

---

## 1. Executive Summary & Certification State

This Evidence Pack documents the formal verification of **Gate A (Pre-Live Certification)** for Phase 13 Slice 1.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        GATE A CERTIFICATION STATE                       │
├────────────────────────────┬───────────────────────────────────────────┤
│ Live Capital Authority     │ $0.00 (STRICT INVARIANT ENFORCED)         │
│ Layer A Contract Evidence  │ ✅ 11/11 PASSED (Automated Pytest Suite)  │
│ Full Regression Suite      │ ✅ 1251/1251 PASSED                       │
│ Type Safety (MyPy)         │ ✅ 264/264 Source Files Clean             │
│ Layer B Operational Demo   │ 📋 PROTOCOL DOCUMENTED & READY            │
│ Overall Gate A Verdict     │ 🟡 CONDITIONAL PASS (Pending Layer B Demo)│
│ Gate B Transition          │ ⛔ STRICTLY BLOCKED                       │
└────────────────────────────┴───────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Strict Capital Lock:** Live capital authority remains strictly `$0.00`. Under no circumstances does Gate A certification authorize live deployment, real funds allocation, or Gate B progression. Gate A certifies pre-live technical and operational readiness only.

---

## 2. Two-Layer Evidence Model

To prevent false confidence from synthetic mocks representing live terminal realities, ACASH enforces a strict **Two-Layer Evidence Model**:

### Layer A: Automated Contract Evidence
- **Substrate:** In-process Python runtime, `MockMT5Transport`, synthetic risk states, deterministic ledger persistence.
- **Scope:** Verifies mathematical invariants, fail-closed state machines, cryptographic bindings, and exception boundaries.
- **Authority:** Enforced via `uv run pytest tests/integration/test_phase13_slice1_gate_a.py -v`.
- **Status:** **COMPLETE & FULLY VERIFIED (11/11 tests passing)**.

### Layer B: Operational Demo Rehearsal Protocol
- **Substrate:** Actual MetaTrader 5 Terminal (Demo Account), live IPC pipe, Windows process boundary, human operator actions.
- **Scope:** Verifies live terminal order placement, broker fill receipt, manual MT5 position closure under kill switch trip, and real operator reaction SLA.
- **Authority:** Human operator execution log with UTC timestamps and MT5 deal tickets.
- **Status:** **REHEARSAL PROTOCOL PREPARED (Items A-3, A-10, A-11)**.

---

## 3. Gate A Checklist (A-1 through A-11) Evidence Matrix

| Item | Description | Layer | Test Function / Reference | Result | Verified Invariants |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **A-1** | RiskPolicyConfig micro-capital limits | **A** | `test_gate_a1_risk_policy_config_limits` | **PASS** | $50 daily loss limit trips binary reject/halt; 5% drawdown boundary enforced; normal allocation passes. |
| **A-2** | Kill switch persistence & restart recovery | **A** | `test_gate_a2_kill_switch_persistence_and_recovery` | **PASS** | `PERSISTENTLY_BLOCKED` written to JSONL ledger with SHA-256 chaining; recovers after process restart; fail-closed admission block. |
| **A-3** | MT5 Demo order lifecycle contract | **A** | `test_gate_a3_layer_a_demo_lifecycle_contract_evidence` | **PASS** | Progression `SUBMITTED` $\to$ `ACKNOWLEDGED` $\to$ `FILLED` verified via `ExecutionCoordinator` and normalized broker events. |
| **A-3 (Demo)** | MT5 Demo terminal operational lifecycle | **B** | Protocol: Section 4.1 | *Pending Live Rehearsal* | Submits 0.01 lot order to live MT5 demo terminal; verifies ticket assigned and position opened. |
| **A-4** | 6-D Reconciliation cycle & anomaly blocking | **A** | `test_gate_a4_6d_reconciliation_cycle_evidence` | **PASS** | Nominal 6-D cycle yields clean confirmation and unblocks adapter; untracked external deal trips `MT5TransportSafetyState.BLOCKED` and halts dispatch. |
| **A-5** | Forward health state transitions | **A** | `test_gate_a5_forward_health_state_transitions` | **PASS** | Sparse observations yield `INSUFFICIENT_EVIDENCE`; invalid telemetry immediately triggers `MONITORING_BLOCKED`; restoration resets to `INSUFFICIENT_EVIDENCE`. |
| **A-6** | Emergency flatten intent forensic record | **A** | `test_gate_a6_emergency_flatten_intent_forensic_record` | **PASS** | Kill switch trip generates immutable `EmergencyFlattenIntent` forensic artifact; zero direct broker wiring. |
| **A-7** | Recovery procedures contract | **A** | `test_gate_a7_recovery_procedures_contract` | **PASS** | Connection loss (`TRADE_SERVER_DISCONNECTED`) transitions adapter to `RECONCILIATION_REQUIRED`; dispatch blocked until 6-D recon re-verified. |
| **A-8** | LiveAuthorization parameter contract & digest | **A** | `test_gate_a8_live_authorization_parameter_contract` | **PASS** | Micro-capital limits ($500 notional, 0.01 lot, $50 daily loss) bound into SHA-256 digest; DRAFT status strictly rejected at admission gate. |
| **A-9** | Rollback & corrupted persistence fails closed | **A** | `test_gate_a9_rollback_corrupted_persistence_fails_closed` | **PASS** | Malformed JSONL ledger raises `DataContractError("PERSISTENCE_RECOVERY_FAILED")` on startup; blocks execution engine. |
| **A-10 (Auto)** | Structured DEGRADED WARNING logging | **A** | `test_gate_a10_automated_degraded_warning_and_sla_policy` | **PASS** | JSON structured WARNING payload with trigger metrics, recommendation code, and strategy ID verified. |
| **A-10 (SLA)** | Operator $\le 15$ min ACK SLA simulation | **A** | `test_gate_a10_automated_degraded_warning_and_sla_policy` | **PASS** | ACK at 10 min passes SLA; ACK at 18 min breaches SLA and mandates kill switch escalation. |
| **A-11 (Auto)** | Emergency manual close contract flow | **A** | `test_gate_a11_layer_a_emergency_manual_close_rehearsal` | **PASS** | Kill switch trips $\to$ manual broker close $\to$ RECON detects mismatch $\to$ synchronized flat restart $\to$ `EmergencyFlattenTracker` confirms `FLATTEN_COMPLETED`. |
| **A-11 (Demo)** | Emergency manual close terminal rehearsal | **B** | Protocol: Section 4.2 | *Pending Live Rehearsal* | Operator manually closes open position in MT5 terminal; verifies reconciler syncs flat portfolio. |

---

## 4. Layer B Operational Demo Rehearsal Protocols

### 4.1 Protocol A-3-Demo: MT5 Demo Order Placement Rehearsal
1. **Pre-condition:** MT5 Demo Terminal connected to demo broker account; shadow ledger initial state clean.
2. **Action:** Issue single `0.01` lot EURUSD BUY order through `MT5BrokerAdapter.submit_order()`.
3. **Verification Points:**
   - Broker returns `TRADE_RETCODE_DONE` (retcode 10009).
   - Order ticket and Deal ticket generated and recorded in shadow ledger.
   - Position appears in MT5 terminal Trade tab.
   - Subsequent 6-D reconciliation cycle confirms 0 discrepancies.
4. **Recording:** Log execution timestamp, order ticket, deal ticket, and confirmation digest in session handoff.

### 4.2 Protocol A-10-Operational: DEGRADED Alerting & Human SLA Rehearsal
1. **Trigger:** Inject artificial performance degradation into forward metrics stream.
2. **Log Emission:** Verify log line:
   ```json
   {"level": "WARNING", "event": "STRATEGY_DEGRADED", "state": "DEGRADED", "recommendation": "DEGRADED_PROBATION", "periods_degraded": 1}
   ```
3. **Human Action:** Operator logs receipt within 15 minutes.
4. **Log Format:**
   ```markdown
   - Degraded Alert UTC: YYYY-MM-DDTHH:MM:SSZ
   - Operator ACK UTC:   YYYY-MM-DDTHH:MM:SSZ
   - Elapsed Seconds:    XXX (< 900s)
   - Action Taken:       DOCUMENTED_INVESTIGATION
   ```

### 4.3 Protocol A-11-Demo: Emergency Manual Close Terminal Rehearsal
1. **Pre-condition:** Active 0.01 lot EURUSD demo position open.
2. **Step 1 (Trip):** Trip Sovereign Kill Switch via operator CLI:
   `c.trip(reason="DEMO_EMERGENCY_REHEARSAL")`
3. **Step 2 (Verify Invariant):** Attempt automated order dispatch $\to$ verify rejected with `EXECUTION_ADMISSION_BLOCKED`.
4. **Step 3 (Manual Action):** Operator opens MT5 GUI terminal, navigates to Trade tab, right-clicks open EURUSD position, selects "Close Position".
5. **Step 4 (Recon Detection):** Trigger 6-D reconciliation $\to$ adapter must detect `UNTRACKED_TRADE_DEAL` or `MISSING_POSITION` and transition to `BLOCKED`.
6. **Step 5 (Sync & Verify):** Perform clean shadow sync with broker closing deal; verify `EmergencyFlattenTracker` reports `FLATTEN_COMPLETED`.

---

## 5. Execution Provenance & Environment

```text
Host Operating System:    Windows (10.0.26100)
Python Runtime:           Python 3.14.3
Package Manager:          uv 0.11.2 (02036a8ba 2026-03-26 x86_64-pc-windows-msvc)
Pytest Version:           pytest 9.1.1, pluggy 1.6.0
MyPy Version:             mypy 2.3.1 (compiled: yes)

Target Test Suite:        tests/integration/test_phase13_slice1_gate_a.py
Pytest Result:            11 passed in 2.17s
Full Test Suite Result:   1251 passed, 3 warnings in 15.56s
MyPy Result:              Success: no issues found in 264 source files

Artifact SHA-256 Hashes:
- test_phase13_slice1_gate_a.py:  EC2152E2C66DD82B23315B3B13D20213662579FED74C5A9A5044CBFF13D35EBA
- recovery_runbook.md:            D4C4A59A4F3A3897F6309B2E9E8C4E872B8E3624AEF6D91200FB795ED9197EDE
- PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV3.md: 8D871167AAA9FAC99261151850E8CC9E81688E8ED49BC3E350A7F79CF6E77391
```

---

## 6. Methodological Caveats & Governance Invariants

1. **Layer A is Necessary but Not Sufficient for Live Deployment:** Passing unit/integration tests with `MockMT5Transport` certifies software contract correctness under tested assumptions. It does not certify that the Windows MT5 desktop terminal or broker liquidity bridges behave identically under live network latency or terminal crashes. Layer B execution is required before Gate B authorization.
2. **Cumulative Exposure Limit Status:** As documented in Plan Rev3 Section 6.2, cumulative exposure enforcement (`current_exposure + order_notional <= max_notional`) remains an audited P1 debt item that is NOT machine-enforced in runtime admission. Order-level `max_position_size` (0.01 lot) is machine-enforced.
3. **Fail-Closed Boundary Preservation:** All recovery mechanisms, persistence corruptions, and reconciliation discrepancies transition to absorbing `BLOCKED` states requiring manual human intervention and multi-signature quorum reset.
4. **STOP GATE:** Execution is halted at Gate A. No progression to Gate B or live deployment shall occur without explicit human audit and multi-sig authorization.
