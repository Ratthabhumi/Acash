# Phase 10: Runtime Orchestration & Continuous Paper Operations
## Canonical Implementation Plan (Contract v1.0 Locked)

> **Document:** `docs/phase10/implementation_plan.md`  
> **Status:** COMPLETE & FROZEN (All 6 Slices Verified)  
> **Target Contract:** `docs/phase10/contract_spec.md` (Contract v1.0) & `docs/phase10/red_team_plan.md`  
> **Frozen Baselines:** Phase 7 (Frozen), Phase 8 (`e6f1d04`), Phase 8.5 (`9ce1365`), Phase 9 (`6bd40d8`)  
> **Phase 10 Tests:** 62 passed | Full Repo: 904 passed | MyPy: 0 errors  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Separation of Concerns)

---

## 1. Executive Summary & Core Architectural Invariants

$$\boxed{\text{From Verified Components} \longrightarrow \text{Verified Operating System}}$$

Phase 10 implements the **authoritative operating pulse, scheduling daemon, runtime supervisor, and operational event ledger** for ACASH. 

### Non-Negotiable Architectural Invariants:
1. **Five-Way Sovereign Separation:**
   $$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Runtime\ Orchestration\ (10)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)}}$$
2. **Zero Execution Authority in Orchestration Plane:**
   $$\boxed{\mathbf{RuntimeSupervisor} \nRightarrow \text{Direct Broker Wire / Socket Access}}$$
3. **Dual-Clock & Idempotency Discipline:**
   $$\boxed{\text{Logical Time } (as\_of\_utc) \neq \text{System Time } (wall\_clock\_utc) \quad \land \quad \text{Duplicate Pulse} \implies 0 \text{ Duplicate Orders}}$$
4. **Separation of Runtime Health vs. Historical Evidence:**
   $$\boxed{\mathbf{Research\ Qualification\ (Historical\ Evidence)} \neq \mathbf{Runtime\ Health\ (Operating\ Status)}}$$
5. **Separation of Runtime Health vs. Risk Kill Switch:**
   $$\boxed{\mathbf{Runtime\ Health\ (Operational\ State)} \neq \mathbf{KillSwitchState\ (Risk\ Boundary)}}$$

---

## 2. Inventory of Reused Existing Components (Zero Duplication)

| Existing Component | Source Location | Reused Role in Phase 10 | Invariant Preserved |
| :--- | :--- | :--- | :--- |
| **`PortfolioState` & `AccountState`** | `src/acash/core/domain/portfolio.py` | Double-entry accounting snapshots | Strict double-entry conservation |
| **`AlphaQualificationGate` & Dossier** | `src/acash/research/qualification.py` | Active strategy discovery (`RESEARCH_QUALIFIED`) | **Zero Capital Authority ($0.00)** |
| **`AllocationTournamentRunner`** | `src/acash/portfolio/tournament.py` | Out-of-sample portfolio rebalance selection | **Zero Runtime Execution Authority** |
| **`DeterministicRiskEngine`** | `src/acash/risk/risk_engine.py` | Sovereign risk evaluation & derisking | Sovereign risk veto |
| **`SovereignKillSwitchController`** | `src/acash/risk/kill_switch.py` | Sovereign kill-switch lifecycle & ledger | Immediate admission lockout |
| **`EmergencyFlattenGenerator`** | `src/acash/risk/emergency.py` | Zero-target liquidation intent generator | Intent $\neq$ Flatten completed |
| **`RiskStateBridge`** | `src/acash/risk/bridge.py` | Cross-phase type-safe state conversions | Loss-bounded state translation |
| **`ExecutionCoordinator`** | `src/acash/execution/coordinator.py` | Order lifecycle & fill accumulation | Sole order state authority |
| **`AlpacaPaperAdapter`** | `src/acash/execution/alpaca/` | Venue-pinned paper broker execution | **Sole broker wire authority** |
| **`CanonicalConfigSerializer`** | `src/acash/core/serialization.py` | Cryptographic SHA-256 digests | Sole hashing authority |

---

## 3. Implementation Slices & Execution Order

```
Slice 1: Operational Domain Contracts & Configuration (schema.py)
   │
   ▼
Slice 2: Operational Clock & Cadence Scheduler (scheduler.py)
   │
   ▼
Slice 3: Operational Event Ledger & Telemetry Store (ledger.py)
   │
   ▼
Slice 4: Runtime Supervisor & 5-Stage Orchestrator (supervisor.py)
   │
   ▼
Slice 5: Continuous Paper Trading Daemon & Live Harness (daemon.py)
   │
   ▼
Slice 6: Full Multi-Phase Integration Pipeline & Phase 10 Freeze
```

---

### Slice 1: Operational Domain Contracts & Configuration
- **Files:** `src/acash/runtime/schema.py`, `src/acash/runtime/__init__.py`
- **Tests:** `tests/unit/runtime/test_schema.py`
- **Tasks:**
  1. Define enums: `RuntimeRegime`, `RuntimeHealthStatus`, `CycleOutcome`.
  2. Implement `RuntimePolicyConfig` (frozen, explicit timeouts, thresholds).
  3. Implement `OperationalCycleEvent` with dual timestamps, cross-phase digests, and SHA-256 hash chaining.
  4. Write unit tests for immutability, finite Decimals, and valid serialization.

---

### Slice 2: Operational Clock & Cadence Scheduler
- **File:** `src/acash/runtime/scheduler.py`
- **Tests:** `tests/unit/runtime/test_scheduler.py`
- **Tasks:**
  1. Implement `OperationalScheduler` managing regime transitions (`PRE_MARKET` $\to$ `MARKET_OPEN` $\to$ `REBALANCE_PULSE` $\to$ `POST_MARKET_CLOSE`).
  2. Implement dual-clock separation (`as_of_utc` vs `wall_clock_utc`).
  3. Implement negative clock drift defense (clock rollback raises `DataContractError`).
  4. Implement pulse idempotency and duplicate pulse suppression.
  5. Write unit tests for clock drift, DST transitions, and rapid pulse deduplication.

---

### Slice 3: Operational Event Ledger & Telemetry Store
- **File:** `src/acash/runtime/ledger.py`
- **Tests:** `tests/unit/runtime/test_ledger.py`
- **Tasks:**
  1. Implement `OperationalLedger` managing append-only JSON Lines persistence (`data/runtime/operational_ledger.jsonl`).
  2. Implement SHA-256 hash chaining (`previous_event_digest` $\to$ `event_digest`).
  3. Implement crash recovery and corrupted ledger fail-closed defense.
  4. Write unit tests for disk persistence, tampering detection, and crash restart recovery.

---

### Slice 4: Runtime Supervisor & 5-Stage Orchestrator
- **File:** `src/acash/runtime/supervisor.py`
- **Tests:** `tests/unit/runtime/test_supervisor.py`
- **Tasks:**
  1. Implement `RuntimeSupervisor` orchestrating the 5-stage cycle:
     $$\text{Data Check} \longrightarrow \text{Strategy Census} \longrightarrow \text{Portfolio Tournament} \longrightarrow \text{Risk Gate} \longrightarrow \text{Execution Admission}$$
  2. Implement `RuntimeHealthStatus` state machine (`HEALTHY`, `DEGRADED`, `PAUSED`, `HALTED`).
  3. Enforce strict fail-closed stage boundaries (a failed stage terminates the cycle immediately).
  4. Enforce zero direct broker wire access on the supervisor.
  5. Write unit tests for health transitions, stage failures, risk rejections, and admission locks.

---

### Slice 5: Continuous Paper Trading Daemon & Live Harness
- **File:** `src/acash/runtime/daemon.py`
- **Tests:** `tests/unit/runtime/test_daemon.py`
- **Tasks:**
  1. Implement `ContinuousPaperDaemon` with event-driven pulse loop, telemetry heartbeat, and graceful POSIX/Windows signal handling (`SIGINT`, `SIGTERM`).
  2. Implement bridge to Phase 7 `AlpacaPaperAdapter` and `ExecutionCoordinator`.
  3. Write unit tests for daemon lifecycle, graceful shutdown, and heartbeat intervals.

---

### Slice 6: Full Multi-Phase Integration Pipeline & Phase 10 Freeze
- **Test File:** `tests/integration/test_phase10_runtime_pipeline.py`
- **Report:** `docs/phase10/freeze_report.md`
- **Tasks:**
  1. Write end-to-end integration tests connecting real Phase 8.5 $\to$ Phase 8 $\to$ Phase 9 $\to$ Phase 10 $\to$ Phase 7.
  2. Run full repository test suite (`uv run pytest -q`, expected $\ge 850$ passing).
  3. Run static type checker (`uv run mypy src/acash/runtime/ tests/unit/runtime/ tests/integration/test_phase10_runtime_pipeline.py`).
  4. Audit git status, create dedicated Phase 10 freeze commit, push to `origin main`, and verify `HEAD == origin/main`.
