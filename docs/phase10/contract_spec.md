# Phase 10: Runtime Orchestration & Continuous Paper Operations
## Canonical Contract Specification v1.0

> **Document:** `docs/phase10/contract_spec.md`  
> **Status:** PROPOSED CONTRACT v1.0 (Awaiting Red-Team Review)  
> **Frozen Baselines:** Phase 7 (Frozen), Phase 8 (`e6f1d04`), Phase 8.5 (`9ce1365`), Phase 9 (`6bd40d8`)  
> **Current HEAD:** `d590074` (origin/main, 842 passing tests, 0 MyPy errors)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Authority, Strict Fail-Closed, Separation of Concerns)

---

## 1. Executive Summary & Core Mission

$$\boxed{\text{From Verified Components} \longrightarrow \text{Verified Operating System}}$$

Phase 10 engineers the **authoritative operating pulse, scheduling daemon, runtime supervisor, and operational event ledger** for ACASH. 

Its primary mission is to transform the standalone, mathematically verified decision and execution engines of Phases 7, 8, 8.5, and 9 into a unified, continuous, and autonomous operating system. It coordinates the lifecycle of live and paper trading operations without usurping or duplicating the authority of any underlying engine.

---

## 2. Five-Way Sovereign Authority Matrix

$$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Runtime\ Orchestration\ (10)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)}}$$

```
                                    ┌───────────────────────┐
                                    │ Operational Scheduler │
                                    │    (Cadence Pulse)    │
                                    └──────────┬────────────┘
                                               │
                                               ▼
                                    ┌───────────────────────┐
                                    │  Runtime Supervisor   │
                                    │    (Orchestrator)     │
                                    └──────────┬────────────┘
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               │                               │                               │
               ▼                               ▼                               ▼
    ┌──────────────────────┐        ┌──────────────────────┐        ┌──────────────────────┐
    │ Phase 8.5 (Research) │        │ Phase 8 (Allocation) │        │   Phase 9 (Risk)     │
    │ - Qualified Dossiers │───────>│ - Tournament Sizing  │───────>│ - Sovereign Veto     │
    │ - Strict $0 Capital  │        │ - Zero Wire Access   │        │ - Derisk / Kill Sw.  │
    └──────────────────────┘        └──────────────────────┘        └──────────┬───────────┘
                                                                               │
                                                                               ▼
                                                                    ┌──────────────────────┐
                                                                    │ Phase 7 (Execution)  │
                                                                    │ - Admission Check    │
                                                                    │ - Broker Wire / BMAP │
                                                                    │ - Reconciliation     │
                                                                    └──────────┬───────────┘
                                                                               │
                                                                               ▼
                                                                          Broker Wire
```

### Strict Non-Negotiable Invariants:
1. **Zero Execution Authority in Orchestrator:** Phase 10 coordinates the execution flow; it **never** calls broker APIs directly, opens network sockets, or constructs broker order envelopes.
2. **Zero Strategy / Optimization Logic in Orchestrator:** Phase 10 triggers tournament runs; it **never** invents alpha weights or overrides Phase 8 portfolio optimizers.
3. **Zero Risk Veto Override:** Phase 10 respects `RiskEvaluationReport` verdicts (`APPROVED`, `REDUCED`, `REJECTED`, `KILL_SWITCH_BLOCKED`); it **never** overrides Phase 9 risk decisions.
4. **Separation of Runtime Health vs. Research Evidence:**
   $$\boxed{\mathbf{Research\ Qualification\ (Historical\ Evidence)} \neq \mathbf{Runtime\ Health\ (Operating\ Status)}}$$
   A degraded runtime health status stops downstream execution without mutating or rewriting historical Phase 8.5 `AlphaQualificationDossier` records.
5. **Separation of Runtime Health vs. Risk Kill Switch:**
   $$\boxed{\mathbf{Runtime\ Health\ (Operational\ State)} \neq \mathbf{KillSwitchState\ (Risk\ Boundary)}}$$
   A telemetry delay degrades runtime health (`RUNTIME_DEGRADED`), but does not trip the sovereign `KillSwitchState.PERSISTENTLY_BLOCKED` unless an explicit risk condition is breached.

---

## 3. Operational Scheduling & Clock Semantics

### A. Operational Regimes (`RuntimeRegime`)
```python
class RuntimeRegime(str, Enum):
    PRE_MARKET = "PRE_MARKET"            # Health check, data sync, trust store loading
    MARKET_OPEN = "MARKET_OPEN"          # Continuous tick streaming, real-time heartbeat
    REBALANCE_PULSE = "REBALANCE_PULSE"  # Scheduled tournament, risk evaluation, admission dispatch
    POST_MARKET_CLOSE = "POST_MARKET_CLOSE" # EOD equity snapshot, ledger sealing, metric reset
    MAINTENANCE = "MAINTENANCE"          # Off-hours integrity validation, archival
```

### B. Dual-Clock Discipline: Simulation vs. Wall-Clock UTC
- **Wall-Clock UTC (`wall_clock_utc`):** The actual system timestamp from NTP-synchronized UTC clock used for telemetry, wire transit latency, and timeout evaluation.
- **Logical Evaluation Time (`as_of_utc`):** The explicit discrete timestamp attached to all portfolio, risk, and strategy calculations.
- **Rule:** Zero `datetime.now()` calls inside deterministic algorithms. Every calculation explicitly receives `as_of_utc`.

### C. Pulse Identification & Idempotency
- **Pulse Cycle Identity:** Each pulse cycle is identified by `cycle_id = f"CYCLE_{regime.value}_{int(as_of_utc.timestamp())}_{seq}"`.
- **Idempotency Hash:** Computed over `(cycle_id, as_of_utc, regime, portfolio_digest)`. Re-running the pulse with identical input produces the identical pulse digest.
- **Duplicate Pulse Defense:** If a pulse with identical `cycle_id` has already executed, the scheduler logs an idempotent skip without triggering duplicate orders.
- **Overlapping Cycle Prevention:** If a cycle execution is currently active, subsequent trigger attempts return immediately with `CYCLE_LOCKED_BUSY` (fail-closed, no concurrent overlapping cycles).
- **Clock Rollback Protection:** If `wall_clock_utc < previous_cycle_wall_clock_utc - max_clock_drift_ms`, the scheduler raises `DataContractError` and enters `RUNTIME_HALTED`.

---

## 4. Unified Runtime Supervisor & 5-Stage Pipeline

The `RuntimeSupervisor` executes the operational cycle across 5 discrete, transactional stages:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RUNTIME SUPERVISOR CYCLE FLOW                         │
│                                                                             │
│  [ Stage 1: Telemetry & Ingestion Check ]                                   │
│  └── Verify data freshness (data_age_ms <= max_market_data_age_ms)          │
│                                                                             │
│  [ Stage 2: Strategy Pool Census ]                                          │
│  └── Discover active Phase 8.5 RESEARCH_QUALIFIED dossiers                  │
│                                                                             │
│  [ Stage 3: Phase 8 Portfolio Tournament ]                                  │
│  └── Run out-of-sample allocation tournament -> CandidateRiskAllocation     │
│                                                                             │
│  [ Stage 4: Phase 9 Sovereign Risk Gate ]                                   │
│  └── Evaluate against leverage/concentration/cash -> RiskEvaluationReport   │
│                                                                             │
│  [ Stage 5: Phase 7 Execution Admission & Dispatch ]                        │
│  └── If APPROVED/REDUCED, pass admitted intent envelope to Phase 7          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Stage Transaction & Failure Rules:
1. **Strict Fail-Closed Progression:** If any stage fails, raises an exception, or emits a rejecting verdict (`REJECTED`, `KILL_SWITCH_BLOCKED`, `NOWHERE`), the pipeline terminates immediately for that cycle.
2. **Zero Silent Fallbacks:** A failed tournament does not silently fall back to previous weights; it produces 100% Cash (`NOWHERE`) under Phase 8 governance.
3. **Audit Trail Sealing:** Every stage records its output digest into the cycle execution manifest before advancing.

---

## 5. Runtime Health State Machine

```
               ┌──────────────────┐
               │ RUNTIME_HEALTHY  │
               └────────┬─────────┘
                        │ (Telemetry delay / transient warning)
                        ▼
               ┌──────────────────┐
               │ RUNTIME_DEGRADED │
               └────────┬─────────┘
                        │ (Socket loss / missing data / operator pause)
                        ▼
               ┌──────────────────┐
               │  RUNTIME_PAUSED  │
               └────────┬─────────┘
                        │ (Fatal unhandled error / integrity breach / clock skew)
                        ▼
               ┌──────────────────┐
               │  RUNTIME_HALTED  │
               └──────────────────┘
```

### State Semantics:
- **`RUNTIME_HEALTHY`:** All data feeds nominal, socket connections active, telemetry latency $< 1500\text{ms}$. Full rebalance and execution permitted.
- **`RUNTIME_DEGRADED`:** Data latency or transient telemetry warnings ($1500\text{ms} < \text{age} \le 5000\text{ms}$). Rebalance operations paused; active positions monitored.
- **`RUNTIME_PAUSED`:** Broker connection lost, operator paused, or pending maintenance. Zero new order admissions allowed.
- **`RUNTIME_HALTED`:** Fatal integrity failure, unhandled crash, or clock rollback. Requires operator intervention to resume.

---

## 6. Operational Event Ledger Schema

Append-only disk ledger (`data/runtime/operational_ledger.jsonl`) cryptographically linked via SHA-256 digests:

```python
class OperationalCycleEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cycle_id: str                          # Unique deterministic cycle ID
    sequence_number: int                   # Monotonically increasing sequence
    regime: RuntimeRegime                  # PRE_MARKET, MARKET_OPEN, REBALANCE_PULSE, etc.
    as_of_utc: datetime                    # Logical evaluation timestamp
    wall_clock_utc: datetime               # System NTP timestamp
    
    # Cross-Phase Lineage Bindings
    active_dossier_digests: tuple[str, ...] # Active Phase 8.5 Strategy Dossier hashes
    portfolio_state_digest: str            # Authoritative Phase 1/8 PortfolioState hash
    account_state_digest: str              # Authoritative Phase 1/8 AccountState hash
    allocation_decision_digest: str        # Phase 8 AllocationDecision hash (or empty)
    risk_report_digest: str                # Phase 9 RiskEvaluationReport hash (or empty)
    execution_manifest_digests: tuple[str, ...] # Phase 7 ExecutionManifest hashes (or empty)
    
    # Operational Status
    runtime_health: RuntimeHealthStatus    # HEALTHY, DEGRADED, PAUSED, HALTED
    kill_switch_state: KillSwitchState     # ACTIVE, TRIPPED, PERSISTENTLY_BLOCKED
    cycle_outcome: str                     # SUCCESS, RISK_REJECTED, DATA_STALE, ERROR
    error_message: Optional[str] = None
    
    # Cryptographic Hash Chaining
    previous_event_digest: str             # SHA-256 of preceding ledger record
    event_digest: str                      # Canonical SHA-256 digest of this record
```

---

## 7. Configurable Runtime Policies (`RuntimePolicyConfig`)

All operational policy values are explicit, bounded, and immutable:

```python
class RuntimePolicyConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rebalance_cron: str = "0 14 * * 1-5"          # 14:00 UTC (9:00 AM EST) Mon-Fri
    heartbeat_interval_seconds: int = 5            # Real-time telemetry heartbeat
    max_market_data_age_ms: int = 1500             # Telemetry degradation threshold
    max_clock_drift_ms: int = 500                  # Maximum allowed wall-clock drift
    cycle_timeout_seconds: int = 30                # Maximum execution time per pulse
    max_degraded_cycles_before_pause: int = 3      # Hysteresis threshold
    persistence_path: str = "data/runtime/operational_ledger.jsonl"
```

---

## 8. Anti-Duplication Inventory

Phase 10 strictly reuses existing infrastructure without duplicate implementations:
- **Lineage Serialization:** Uses `CanonicalConfigSerializer` (`src/acash/core/serialization.py`).
- **Cryptographic Trust Store:** Uses `Ed25519TrustStore` (`src/acash/execution/crypto.py`).
- **Accounting & Positions:** Uses `PortfolioState` and `AccountState` (`src/acash/core/domain/portfolio.py`).
- **Risk Gate:** Calls `DeterministicRiskEngine.evaluate_candidate_allocation()` (`src/acash/risk/risk_engine.py`).
- **Kill Switch:** Calls `SovereignKillSwitchController` (`src/acash/risk/kill_switch.py`).
- **Execution & Normalization:** Calls `ExecutionCoordinator` (`src/acash/execution/coordinator.py`).

---

## 9. Red-Team Invalidation Targets (To be Audited in `red_team_plan.md`)

The subsequent Red-Team review must attack:
1. **Hidden Authority Creation:** Verify that `RuntimeSupervisor` cannot directly emit orders or mutate risk reports.
2. **Scheduler Non-Determinism:** Attack race conditions, DST transitions, clock skew, and rapid trigger pulses.
3. **Replay & Duplicate Execution:** Attempt to re-run the same `cycle_id` to test order duplication prevention.
4. **Stale Decision Reuse:** Ensure an expired `RiskEvaluationReport` (TTL 60s) cannot be admitted in a subsequent cycle.
5. **Runtime Health vs. Kill Switch Confusion:** Verify that `RUNTIME_DEGRADED` does not corrupt `KillSwitchState.ACTIVE`, and that `PERSISTENTLY_BLOCKED` locks execution regardless of `RUNTIME_HEALTHY`.
6. **Process Crash Mid-Cycle:** Simulate process termination between Stage 3 (Tournament) and Stage 5 (Admission) to verify crash recovery and ledger reconciliation.

---

## 10. Acceptance Criteria & Status Classification

| Criteria | Verification Target | Classification |
| :--- | :--- | :---: |
| **Authority Separation** | Phase 10 has 0 broker wire methods, 0 alpha generation methods, 0 risk veto overrides | **LOCK** |
| **Scheduler Idempotency** | Duplicate pulses with identical `(cycle_id, as_of_utc)` produce identical digests & 0 duplicate orders | **LOCK** |
| **Dual-Clock Discipline** | `as_of_utc` strictly separated from `wall_clock_utc`; clock rollbacks fail closed | **LOCK** |
| **Health vs. Kill Switch** | State machines remain strictly separated; immutable Phase 8.5 dossiers never mutated | **LOCK** |
| **Append-Only Ledger** | SHA-256 hash chaining validated; corrupt records fail closed | **LOCK** |

---

### Classification: **PROPOSED CONTRACT v1.0 — READY FOR RED-TEAM REVIEW**
