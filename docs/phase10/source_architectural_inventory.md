# Phase 10: Runtime Orchestration & Continuous Paper Operations
## Source & Architectural Inventory Audit

> **Document:** `docs/phase10/source_architectural_inventory.md`  
> **Status:** AUDIT COMPLETE  
> **Frozen Baselines:** Phase 7 (Frozen), Phase 8 (`e6f1d04`), Phase 8.5 (`9ce1365`), Phase 9 (`6bd40d8`)  
> **Current HEAD:** `d590074` (origin/main, 842 passing tests, 0 MyPy errors)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Authority, Strict Fail-Closed, Separation of Concerns)

---

## 1. Executive Summary & Audit Mission

$$\boxed{\text{From Verified Components} \longrightarrow \text{Verified Operating System}}$$

With Phases 7, 8, 8.5, and 9 frozen, ACASH possesses an exhaustive set of verified, mathematically disciplined decision and execution engines. However, these engines currently exist as isolated components. 

The objective of **Phase 10: Runtime Orchestration & Continuous Paper Operations** is to implement the **authoritative operating pulse** (the orchestration layer) that drives continuous, scheduled, and event-driven operational cycles across live/paper environments while strictly preserving all existing authority boundaries.

---

## 2. Comprehensive Inventory of Existing ACASH Components

| Component | Source Path | Phase / Authority | Reusable Capabilities in Phase 10 | Strict Boundary / Invariant to Preserve |
| :--- | :--- | :--- | :--- | :--- |
| **`PortfolioState` & `AccountState`** | `src/acash/core/domain/portfolio.py` | Phase 1 / Phase 8 | Authoritative accounting models, cash, equity, position maps | Must remain pure accounting data; never mutate historical states. |
| **`AlphaQualificationGate` & Dossier** | `src/acash/research/qualification.py` | Phase 8.5 (`9ce1365`) | Qualified strategy pool discovery (`RESEARCH_QUALIFIED`) | **Zero Capital Authority ($0.00)**. Historical qualification is immutable. |
| **`AllocationTournamentRunner`** | `src/acash/portfolio/tournament.py` | Phase 8 (`e6f1d04`) | Out-of-sample portfolio rebalance selection | **Zero Runtime Execution Authority**. Emits proposal only. |
| **`DeterministicRiskEngine`** | `src/acash/risk/risk_engine.py` | Phase 9 (`6bd40d8`) | Sovereign multi-tier risk veto, derisking (`EXACT_SCALE_DOWN`) | Risk approval $\neq$ Execution authorization. Emits `RiskEvaluationReport`. |
| **`SovereignKillSwitchController`** | `src/acash/risk/kill_switch.py` | Phase 9 (`6bd40d8`) | Sovereign trip, disk ledger persistence, multi-sig reset | Any trip blocks execution admission immediately. |
| **`EmergencyFlattenGenerator`** | `src/acash/risk/emergency.py` | Phase 9 (`6bd40d8`) | Deterministic zero-target intent generation ($\Delta q_i = -q_i$) | Intent emitted $\neq$ Orders transmitted $\neq$ Positions flattened. |
| **`RiskStateBridge`** | `src/acash/risk/bridge.py` | Phase 9 (`6bd40d8`) | Cross-phase type-safe state conversion | Loss-bounded conversions, preserves temporal identity & digests. |
| **`ExecutionCoordinator`** | `src/acash/execution/coordinator.py` | Phase 7 | Sole order lifecycle state authority & fill deduplication | Owns broker event processing, order transition, and fill accumulation. |
| **`AlpacaPaperAdapter` & Transport** | `src/acash/execution/alpaca/` | Phase 7 | Venue-pinned paper REST/SSE gateway & BMAP 01–12 | **Sole network/broker wire authority**. Zero strategy/risk logic inside transport. |
| **`CanonicalConfigSerializer`** | `src/acash/core/serialization.py` | Core Lineage | Deterministic JSON canonicalization & SHA-256 digests | Sole hashing authority. |

---

## 3. Identification of Critical Capability Gaps (What Phase 10 Must Build)

The audit reveals four essential architectural capabilities that must be engineered in Phase 10:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PHASE 10 RUNTIME CONTROL PLANE                        │
│                                                                             │
│  ┌───────────────────────┐   ┌────────────────────────┐   ┌──────────────┐  │
│  │ 1. Scheduled Cadence  │   │ 2. Runtime Supervisor  │   │ 3. Event Bus │  │
│  │    & Clock Daemon     │──>│    & Orchestrator      │<──│    & Pulse   │  │
│  │    (Market Hours,     │   │    (State Machine,     │   │    (Ticks,   │  │
│  │     Daily Rebalance)  │   │     Health Heartbeat)  │   │     Fills)   │  │
│  └───────────────────────┘   └───────────┬────────────┘   └──────────────┘  │
│                                          │                                  │
│                                          ▼                                  │
│                              ┌────────────────────────┐                     │
│                              │ 4. Operational Ledger  │                     │
│                              │    & Telemetry Store   │                     │
│                              │    (Structured Trace)  │                     │
│                              └────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 1: Scheduled Operational Cadence & Clock Daemon
- **Requirement:** A deterministic scheduler managing operational regimes:
  - `PRE_MARKET` (Health checks, data freshness validation, trust-store loading).
  - `MARKET_OPEN` (Continuous tick ingestion, heartbeat monitoring, anomaly trip detection).
  - `REBALANCE_PULSE` (Scheduled tournament execution, risk gate evaluation, admission dispatch).
  - `POST_MARKET_CLOSE` (End-of-day equity sealing, daily PnL reset, disk state synchronization).
- **Rule:** Strict separation of simulated backtest time vs. wall-clock UTC time.

### Gap 2: Unified Runtime Supervisor & Pipeline Orchestrator
- **Requirement:** A master orchestrator (`RuntimeSupervisor` / `OperationalPulse`) that connects:
  $$\text{Data Ingestion} \longrightarrow \text{Phase 8.5 Strategy Pool} \longrightarrow \text{Phase 8 Tournament} \longrightarrow \text{Phase 9 Risk Engine} \longrightarrow \text{Phase 7 Coordinator}$$
- **Rule:** The supervisor coordinates the flow of immutable envelopes; it does **not** bypass or mutate any intermediate gate.

### Gap 3: Operational Event Ledger & Telemetry Recording
- **Requirement:** An append-only disk ledger recording every operational pulse cycle:
  - Cycle ID, Timestamp, Market Regime.
  - Active Strategy Census & Dossier Digests.
  - Allocation Decision Digest.
  - Risk Report Digest & Verdict.
  - Order Intent Digests & Execution Outcomes.
  - Broker Reconciliation Snapshot.
- **Rule:** Binds full end-to-end cryptographic lineage for forward paper operations.

### Gap 4: Runtime Health Status & Degradation Model (Without Mutating Historical Evidence)
- **Requirement:** Implement runtime health status (`RUNTIME_HEALTHY`, `RUNTIME_DEGRADED`, `RUNTIME_PAUSED`, `RUNTIME_HALTED`).
- **Rule (Non-Negotiable):**
  $$\boxed{\text{Research Qualification (Historical Evidence)} \neq \text{Runtime Health (Operating Status)}}$$
  - Runtime degradation blocks downstream allocation/risk without rewriting or retrospectively falsifying Phase 8.5 historical dossiers.

---

## 4. Phase 10 Authority Boundaries & Anti-Patterns

### Strict Guardrails:
1. **Zero Execution Authority in Orchestrator:** The orchestrator dispatches envelopes; it never calls broker APIs directly or constructs raw broker payloads.
2. **Zero Strategy Logic in Scheduler:** Timing mechanisms trigger events; they never compute alphas or optimize weights.
3. **Fail-Closed Operational State:** Any unhandled exception, missing data feed, or broken socket transitions the supervisor immediately to `RUNTIME_PAUSED` or triggers Phase 9 `KillSwitchController.trip()`.
4. **No Rewriting of Frozen Contracts:** Phase 7, 8, 8.5, and 9 code remains immutable.

---

## 5. Next Steps for Phase 10

Following the canonical ACASH engineering process:
1. **Step 1:** Author **Phase 10 Contract Specification v1.0** (`docs/phase10/contract_spec.md`).
2. **Step 2:** Author **Phase 10 Red-Team & Adversarial Invalidation Plan** (`docs/phase10/red_team_plan.md`).
3. **Step 3:** Author **Phase 10 Implementation Plan** (`docs/phase10/implementation_plan.md`).
4. **Step 4:** Execute implementation slice-by-slice via strict TDD.
