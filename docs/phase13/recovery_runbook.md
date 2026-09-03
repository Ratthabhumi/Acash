# Phase 13: Operational Recovery Runbook

> **Document:** `docs/phase13/recovery_runbook.md`
> **Status:** OFFICIAL OPERATIONAL PROTOCOL — GATE A CERTIFICATION ARTIFACT
> **Scope:** Phase 13 Live Small Capital Deployment
> **Target System:** ACASH Execution & Risk Subsystems
> **Frozen Baseline Authority:** `1e1d154` (Phase 12 FROZEN)
> **Plan Authority:** `PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV3.md`

---

## 0. Executive Mandate & Fail-Closed Contract

In all operational states, ACASH adheres strictly to the **Fail-Closed Principle** per `AGENTS.md`:
1. Any ambiguous, undefined, or contradictory broker state MUST transition the system to an execution-inhibited state (`BLOCKED`, `UNKNOWN`, or `PERSISTENTLY_BLOCKED`).
2. Live dispatch is permitted **IFF** `can_dispatch() == True` (`safety_state == READY` $\land$ `is_reconciled == True`).
3. If automated systems fail, **the human operator is the terminal safety authority**.

---

## 1. Procedure 1: Connection Loss Recovery (MT5 Terminal / IPC Disconnect)

### 1.1 Trigger Condition
- IPC pipe to MT5 terminal terminates unexpectedly.
- Heartbeat probe exceeds timeout or socket read fails.
- In-flight orders transition to `OrderLifecycleState.UNKNOWN`.

### 1.2 Automated System State
- `MT5TransportSafetyState` transitions to `UNKNOWN` or `UNINITIALIZED`.
- `can_dispatch()` returns `False` immediately.
- Execution coordinator rejects all incoming order dispatch requests.

### 1.3 Step-by-Step Recovery Procedure
1. **Assess In-Flight State:**
   - Review coordinator in-flight registry for any orders in `OrderLifecycleState.UNKNOWN`.
   - Do NOT attempt to resubmit or cancel orders while disconnected.
2. **Restore MT5 Connection:**
   - Verify MT5 terminal process is running under the authorized Windows DPAPI credential context.
   - Trigger adapter reconnection (`adapter.reconnect()` or service restart).
3. **Mandatory 6-D Reconciliation Cycle:**
   - Once connection state returns to `CONNECTED`, trigger a full 6-D Reconciliation Cycle:
     $$\text{RECON-6D} = (\text{Balance}, \text{Equity}, \text{Margin}, \text{Positions}, \text{Resting Orders}, \text{Historical Deals})$$
4. **Resolution Gate:**
   - **PASS**: `is_reconciled` becomes `True`, safety state transitions to `READY`, `can_dispatch()` evaluates to `True`. Normal dispatch resumes.
   - **FAIL**: Discrepancy detected $\to$ transition to `BLOCKED` (Proceed to Procedure 2).

---

## 2. Procedure 2: CRITICAL Discrepancy Recovery (Untracked Deals / External Mutation)

### 2.1 Trigger Condition
- 6-D Reconciliation detects an external trade or deal not originating from ACASH (`UNTRACKED_TRADE_DEAL`).
- Volume mismatch between ACASH shadow position and MT5 terminal reality.
- Balance/margin discrepancy exceeding calibrated tolerance.

### 2.2 Automated System State
- `MT5ReconciliationError` is raised.
- `MT5BrokerAdapter` safety state transitions to `BLOCKED` (absorbing state).
- `can_dispatch()` returns `False` permanently. No automated order can be submitted.

### 2.3 Step-by-Step Recovery Procedure
1. **Halt and Isolate:**
   - Verify that all automated execution is blocked (`can_dispatch() == False`).
2. **Forensic Inspection:**
   - Extract MT5 deal ticket numbers from discrepancy report.
   - Inspect broker terminal logs to determine source of external deal (e.g., manual operator trade, mobile app login, broker swap/rollover adjustment).
3. **Position Realignment:**
   - Document the root cause in the forensic audit ledger.
   - If manual position adjustment is needed, perform necessary order directly in MT5 terminal.
4. **Resynchronization:**
   - Restart the ACASH execution coordinator service with explicit state resynchronization against the broker reality snapshot.
   - Execute a clean 6-D reconciliation cycle.
   - Confirm zero discrepancies before unlocking dispatch.

---

## 3. Procedure 3: Process Crash Recovery (Cold Restart & Ledger Replay)

### 3.1 Trigger Condition
- Hardware failure, OS reboot, unhandled exception, or unexpected termination of the ACASH process.

### 3.2 Automated Recovery Logic upon Process Restart
1. **Kill Switch Ledger Inspection:**
   - `SovereignKillSwitchController` loads the append-only SHA-256 disk ledger (`kill_switch_events.jsonl`).
   - If latest state was `ARMED` $\to$ Controller initializes in `ARMED`.
   - If latest state was `TRIPPED` or `PERSISTENTLY_BLOCKED` $\to$ Controller initializes in `PERSISTENTLY_BLOCKED` (Fail-Closed).
   - If disk ledger is corrupted, missing, or has invalid cryptographic hash chain $\to$ Controller halts startup and fails closed to `PERSISTENTLY_BLOCKED`.
2. **Broker State Sync:**
   - Broker adapter starts in `UNINITIALIZED` / `UNKNOWN`.
   - `can_dispatch()` is `False` until explicit connection and full 6-D reconciliation.

### 3.3 Operator Checklist
- [ ] Verify kill switch state via `controller.state`.
- [ ] If `PERSISTENTLY_BLOCKED`, perform root-cause analysis before quorum reset.
- [ ] Run 6-D reconciliation cycle to confirm portfolio synchronization.
- [ ] Confirm `can_dispatch() == True` before enabling trading loop.

---

## 4. Procedure 4: Emergency Manual Position Closure (Operator MT5 Override)

### 4.1 Trigger Condition
- Emergency market conditions, critical software failure, or kill switch trip where positions remain open.
- **Architectural Note:** In ACASH frozen architecture, `PERSISTENTLY_BLOCKED` blocks ALL dispatch, including automated close orders. The operator MUST execute manual closure in MT5.

### 4.2 Step-by-Step Manual Close Sequence
1. **Trip Kill Switch Immediately:**
   - Operator triggers `SovereignKillSwitchController.trip(reason="OPERATOR_MANUAL_EMERGENCY")`.
   - State becomes `PERSISTENTLY_BLOCKED`. Automated dispatch is 100% blocked.
2. **Open MT5 Terminal Directly:**
   - Access the dedicated Windows MT5 desktop terminal session.
   - Navigate to the **Trade** tab.
3. **Execute Close Order:**
   - Right-click open position(s) and select **Close Position** (or click the 'X' button).
   - Confirm position quantity reaches `0.00`.
4. **Discrepancy Recognition in ACASH:**
   - Next ACASH reconciliation cycle observes the manual close deal as `UNTRACKED_TRADE_DEAL`.
   - Broker adapter transitions to `BLOCKED`.
   - Dispatch is now doubly locked: `PERSISTENTLY_BLOCKED` + `BLOCKED`.
5. **Post-Close Verification:**
   - Execute process restart.
   - Perform 6-D reconciliation $\to$ verify position is flat (`0.0`).
   - Run `EmergencyFlattenTracker.verify_flatten_completion()` to confirm zero-position status.

---

## 5. Procedure 5: Sovereign Kill Switch Quorum Reset

### 5.1 Pre-Conditions for Reset
- Cause of kill switch trip has been identified, mitigated, and documented.
- All broker positions are confirmed closed or in an intended, verified state.
- 6-D reconciliation confirms zero unaccounted discrepancies.

### 5.2 Cryptographic Multi-Sig Reset Protocol
1. **Root Cause Analysis Documentation:**
   - Draft non-empty forensic root cause string `root_cause_analysis`.
2. **Quorum Signature Collection:**
   - Generate canonical reset payload:
     $$\text{payload} = \text{CanonicalJson}(\text{reset\_id}, \text{timestamp}, \text{root\_cause\_analysis}, \text{prev\_event\_id})$$
   - Required distinct approvers sign the payload using authorized Ed25519 private keys:
     $$\sigma_i = \text{Ed25519Sign}(K_{\text{priv}, i}, \text{SHA256}(\text{payload}))$$
3. **Execute Reset Transition:**
   - Call `SovereignKillSwitchController.reset_quorum(approvals, root_cause_analysis)`.
   - `Ed25519TrustStore` verifies each signature, public key identity, and quorum threshold.
   - State transitions: `PERSISTENTLY_BLOCKED` $\to$ `RESET_PENDING` $\to$ `ARMED`.
   - Reset event is cryptographically chained and appended to disk ledger.

---

## 6. Procedure 6: Operational Handling of `MONITORING_BLOCKED`

### 6.1 Classification Truth
`MONITORING_BLOCKED` is an **Operational Fail-Closed Procedure**, not an automated admission gate in `admission.py`.

### 6.2 Protocol
1. **Immediate Action on `MONITORING_BLOCKED` Alarm:**
   - Operator receives structured ERROR log (`event: MONITORING_BLOCKED`).
   - Operator MUST immediately pause or inhibit submission of new `OrderIntent` items.
   - Do NOT panic flatten existing open positions (broker-side TP/SL remains active).
2. **Investigation Window ($\le 15$ Minutes):**
   - Inspect data feed, feature engine, and telemetry pipelines.
   - Check if market data feed is stale, disconnected, or malformed.
3. **Escalation & Kill Switch Mandate ($> 30$ Minutes):**
   - If telemetry cannot be restored within **30 minutes** of the initial trigger:
     $$\text{Telemetry Outage} > 30\text{ min} \implies \text{MANDATORY MANUAL KILL SWITCH TRIP}$$
   - Operator invokes `controller.trip(reason="MONITORING_TELEMETRY_OUTAGE_EXCEEDED_30M")`.
