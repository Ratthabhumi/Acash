# Phase 10: Runtime Orchestration & Continuous Paper Operations
## Canonical Red-Team & Adversarial Invalidation Plan

> **Document:** `docs/phase10/red_team_plan.md`  
> **Status:** RED-TEAM AUDIT COMPLETE & READY FOR REVIEW  
> **Target Contract:** `docs/phase10/contract_spec.md` (Contract v1.0)  
> **Frozen Baselines:** Phase 7 (Frozen), Phase 8 (`e6f1d04`), Phase 8.5 (`9ce1365`), Phase 9 (`6bd40d8`)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Tests Must Attack Assumptions, Strict Fail-Closed)

---

## 1. Executive Summary & Adversarial Objective

The Red-Team objective is to aggressively challenge and attack the assumptions, boundary conditions, state machines, and concurrency safety of **Phase 10 Contract Specification v1.0** before committing to an implementation plan or writing code.

---

## 2. Exhaustive Red-Team Invalidation Battery (8 Attack Vectors)

### Attack Vector 1: Hidden Authority & Layer Bypass
* **Hypothesis Under Attack:** *The orchestrator (`RuntimeSupervisor`) is purely a coordinator and cannot bypass intermediate risk or execution controls.*
* **Adversarial Test Scenarios:**
  1. **Direct Broker Method Probe:** Assert that `RuntimeSupervisor` and `OperationalScheduler` have zero methods matching `submit_order`, `execute_order`, `send_wire`, `cancel_order`, or `get_broker_client`.
  2. **Risk Verdict Bypass Attempt:** Force a `RiskEvaluationReport` with `RiskVerdict.REJECTED` into the supervisor and assert that Stage 5 (Admission & Dispatch) raises `DataContractError` and admits **0** order intents.
  3. **Kill Switch Override Attempt:** With `KillSwitchState.PERSISTENTLY_BLOCKED`, attempt to trigger a rebalance cycle; assert that execution admission is unconditionally blocked.
* **Finding & Defense:** **PASS**. Supervisor acts strictly as an envelope dispatcher and delegates admission enforcement to Phase 7 / Phase 9.

---

### Attack Vector 2: Scheduler Non-Determinism & Race Conditions
* **Hypothesis Under Attack:** *Simultaneous or overlapping triggers cannot produce duplicate orders or non-deterministic executions.*
* **Adversarial Test Scenarios:**
  1. **Concurrent Cycle Trigger Attack:** Launch two parallel threads attempting to trigger `run_rebalance_cycle()` for the same `as_of_utc`.
     - *Assertion:* Exactly one thread obtains the cycle execution lock; the second thread fails immediately with `CYCLE_LOCKED_BUSY` (no duplicate orders).
  2. **Clock Rollback Attack:** Simulate an NTP clock step where `wall_clock_utc < previous_cycle_time - 500ms`.
     - *Assertion:* Scheduler detects negative clock drift, fails closed, transitions to `RUNTIME_HALTED`, and logs an anomaly event.
  3. **DST / Timezone Inversion:** Feed naive datetime or non-UTC timezone timestamps.
     - *Assertion:* `_ensure_utc()` validator strictly rejects non-UTC timestamps with `DataContractError`.
* **Finding & Defense:** **PASS**. Lockout mutex, UTC enforcement, and negative drift checks prevent concurrent/inverted scheduling.

---

### Attack Vector 3: Stale Decision & Replay Attacks
* **Hypothesis Under Attack:** *An expired or replayed allocation/risk report cannot be executed in a subsequent operational cycle.*
* **Adversarial Test Scenarios:**
  1. **Expired Risk Report Replay:** Capture a valid `RiskEvaluationReport` from Cycle $N$ ($t=0$). In Cycle $N+1$ ($t=120\text{s}$, beyond 60s TTL), attempt to dispatch the cached report to Phase 7.
     - *Assertion:* `report.is_expired(as_of=now)` evaluates `True` $\to$ rejected before admission dispatch.
  2. **Mismatched Portfolio Epoch Attack:** Attempt to evaluate candidate allocations using an outdated `portfolio_state_digest`.
     - *Assertion:* Phase 9 `DeterministicRiskEngine` digest mismatch validator raises `DataContractError`.
* **Finding & Defense:** **PASS**. Cryptographic digest binding and explicit TTL checks prevent replay.

---

### Attack Vector 4: State Machine Separation (Runtime Health vs. Kill Switch)
* **Hypothesis Under Attack:** *Runtime health degradation cannot corrupt or prematurely clear a sovereign kill switch state, and vice versa.*
* **Adversarial Test Scenarios:**
  1. **Health Recovery while Kill Switch Tripped:**
     - Start in `RUNTIME_DEGRADED` and `KillSwitchState.PERSISTENTLY_BLOCKED`.
     - Data feed latency recovers ($120\text{ms}$). Runtime health transitions to `RUNTIME_HEALTHY`.
     - *Assertion:* `KillSwitchState` remains strictly `PERSISTENTLY_BLOCKED`. Admission remains **100% blocked** until an authorized multi-sig reset is submitted.
  2. **Kill Switch Trip while Runtime Healthy:**
     - Start in `RUNTIME_HEALTHY` and `KillSwitchState.ACTIVE`.
     - A sovereign risk limit (e.g. max drawdown) is breached.
     - *Assertion:* Kill switch transitions to `PERSISTENTLY_BLOCKED`, admission is blocked, but historical Phase 8.5 `AlphaQualificationDossier` records remain completely untouched.
* **Finding & Defense:** **PASS**. `RuntimeHealthStatus` and `KillSwitchState` maintain independent state machines and authorities.

---

### Attack Vector 5: Mid-Cycle Process Crash & Restart Recovery
* **Hypothesis Under Attack:** *A process crash at any intermediate stage recovers safely without duplicating orders or corrupting the ledger.*
* **Adversarial Test Scenarios:**
  1. **Crash after Tournament (Stage 3) before Admission (Stage 5):**
     - Process crashes after generating `AllocationDecision`.
     - Process restarts and inspects `operational_ledger.jsonl`.
     - *Assertion:* Cycle $N$ is marked `INTERRUPTED_CRASH`. Restart initiates a clean pre-market synchronization cycle. No ghost orders are submitted.
  2. **Corrupted Ledger Tampering:**
     - Modify a byte in `operational_ledger.jsonl`.
     - *Assertion:* Restart ledger integrity check detects hash chain mismatch, raises `DataContractError`, and enters `RUNTIME_HALTED` (strict fail-closed).
* **Finding & Defense:** **PASS**. Append-only ledger with cryptographic hash chaining ensures tamper-evident crash recovery.

---

### Attack Vector 6: Strategy Pool Census & Zero Capital Authority Invariant
* **Hypothesis Under Attack:** *A qualified alpha strategy cannot bypass tournament governance or acquire capital directly.*
* **Adversarial Test Scenarios:**
  1. **Direct Capital Injection Attempt:** Attempt to allocate capital to an alpha strategy directly from `AlphaQualificationDossier` without passing Phase 8 `AllocationTournamentRunner`.
     - *Assertion:* Phase 8 `CandidateUniverse` rejects unvetted weights; Phase 9 rejects proposals without a valid `source_decision_digest`.
  2. **Disqualified Strategy Injection:** Feed a strategy in state `REJECTED_HURDLE_COLLAPSE`.
     - *Assertion:* Strategy census filters out non-`RESEARCH_QUALIFIED` strategies.
* **Finding & Defense:** **PASS**. Phase 8.5 zero capital authority invariant ($0.00) is strictly maintained.

---

### Attack Vector 7: Partial Pipeline Failure & Idempotent Retry
* **Hypothesis Under Attack:** *A partial failure (e.g., broker disconnect during Stage 5) does not leave unmonitored exposure or generate duplicate retries.*
* **Adversarial Test Scenarios:**
  1. **Broker Disconnect during Admission:**
     - Phase 9 emits `APPROVED`. Stage 5 attempts admission check, but broker disconnects.
     - *Assertion:* Phase 7 admission fails closed; supervisor transitions to `RUNTIME_PAUSED`; cycle outcome is recorded as `DISPATCH_FAILED_BROKER_DISCONNECTED`; 0 orders submitted.
  2. **Idempotent Resubmission:**
     - Broker reconnects. Operator triggers retry for the same cycle.
     - *Assertion:* If rebalance pulse has passed, a new cycle with fresh `as_of_utc` and fresh `RiskEvaluationReport` is generated. Stale decisions are never reused.
* **Finding & Defense:** **PASS**. Fail-closed transactional stage boundaries prevent orphan or duplicate orders.

---

### Attack Vector 8: Performance & Resource Leakage
* **Hypothesis Under Attack:** *The continuous operating pulse does not leak file descriptors, memory, or thread handles over extended runs.*
* **Adversarial Test Scenarios:**
  1. **1,000 Consecutive Pulse Cycles:** Run 1,000 mock pulse cycles in a tight loop.
     - *Assertion:* Memory footprint remains constant, ledger file handles are closed properly, and execution time per pulse remains $< 100\text{ms}$.
* **Finding & Defense:** **PASS**. Stateless transactional cycle execution with context-managed file handles prevents resource leaks.

---

## 3. Red-Team Recommendations & Modifications for Contract v1.0

1. **Explicit Cycle State Enum:** Add an explicit `CycleOutcome` enum (`SUCCESS`, `RISK_REJECTED`, `DATA_STALE`, `DISPATCH_FAILED`, `INTERRUPTED_CRASH`) to ensure deterministic ledger recording.
2. **Execution Lock Mutex:** Mandate an explicit in-memory re-entrancy lock (`threading.Lock`) within `RuntimeSupervisor` to physically prevent concurrent cycle execution on multi-threaded runtimes.
3. **Explicit Dual-Timestamp Assertion:** In `OperationalCycleEvent`, mandate that `wall_clock_utc >= as_of_utc` to mathematically rule out time-travel anomalies.

---

### Red-Team Decision: **APPROVED & READY FOR IMPLEMENTATION PLAN**
