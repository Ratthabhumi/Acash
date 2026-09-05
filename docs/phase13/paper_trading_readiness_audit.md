# ACASH Phase 13 — Paper Trading Readiness Audit & Gap Analysis
# 3-Month Continuous Forward Operation Feasibility Assessment

> **Document ID:** `docs/phase13/paper_trading_readiness_audit.md`  
> **Status:** AUDIT COMPLETE — IMPLEMENTATION LOCKED  
> **Governance Authority:** Phase 13 Gate A (Certified), Gate B Rev 10 Step 2 (Conditional Pass), B23.2 (Not Proven / Deferred)  
> **Objective:** Determine exact requirements for continuous 3-month Paper Trading validation on the current development host using existing ACASH architecture.  
> **Rule Enforcement:** Zero unverified claims; zero code changes in audit phase; zero live execution authority.

---

## 1. Executive Summary & Governance Boundary

This audit evaluates the codebase at commit `e733d53` to determine whether ACASH can execute a **continuous 3-month Paper Trading validation program** on the current Windows development host without requiring physical enterprise OS enforcement (`WDAC UMCI=2` / `B23.2`), without deploying live capital, and without premature implementation of future phases (Phases 14–28).

### 1.1 Active Governance Boundary (Immutable)
- **Phase 13 Gate A:** `CERTIFIED` (Formal Human Sign-off 2026-09-04; MT5 Demo `112040157` 100% flat).
- **Phase 13 Gate B (Rev 10 Step 2):** `CONDITIONAL PASS` (B1–B22 PASS, B23.1 PASS, B23.2 NOT PROVEN / DEFERRED).
- **Assertion B23.2:** `NOT PROVEN / DEFERRED` to future dedicated 24/7 cloud/VM infrastructure.
- **Step 3 Ceremony:** `STRICTLY BLOCKED / LOCKED`.
- **Step 4 Activation:** `STRICTLY BLOCKED / LOCKED`.
- **Slice 3 (First Live Order):** `STRICTLY BLOCKED / LOCKED`.
- **Live Capital:** `$0.00` | **Live Orders:** `0` | **Live Broker Connection:** `DISCONNECTED`.

### 1.2 Core Audit Finding
ACASH possesses **extensive, production-grade foundational components** across Phase 7 (Broker Abstraction & Alpaca Paper P-001), Phase 8 (Portfolio Tournament), Phase 9 (Sovereign Risk Engine & Kill Switch), Phase 10 (Runtime Supervisor, Scheduler & Operational Ledger), Phase 11 (Forward Tracking, Drift Detection & Realized Drag Attribution), and Phase 12 (MT5 Broker Adapter & 6-D Reconciliation).

However, **there is currently an architectural seam gap** between the upstream 5-stage supervisor (`RuntimeSupervisor`) and the downstream execution/fill simulator:
1. `RuntimeSupervisor` stops at Stage 5 (`admission_hook_fn`), outputting `admitted_for_execution=True/False` without an automated order-dispatch and fill-monitoring runner.
2. The system has two operational fill simulation options:
   - *Option 1 (Simulated Local Broker):* `MockBroker` exists and supports partial/full fills and cancellation races, but operates in-memory without background limit-order matching against incoming bars.
   - *Option 2 (Real Paper Broker):* `AlpacaPaperAdapter` (US Equities) and `MT5BrokerAdapter` (Demo MetaQuotes) exist and have passed order exercise tests, but lack an unattended 24/7 continuous event loop with automated reconnection and state recovery.
3. Persistent portfolio state rehydration across process restarts is incomplete (the `OperationalLedger` recovers historical cycle digests, but does not reconstruct active in-memory open positions upon boot).

---

## 2. Repository Fact Audit (Evidence-Grounded Inventory)

Every item below has been directly verified against active code at HEAD.

| Domain / Capability | Exact Source File | Exact Class / Function | Status | Proving Tests | Known Limitations |
|---|---|---|---|---|---|
| **A. Roadmap & Boundaries** | `docs/ROADMAP.md` | Lines 1–100, 220–350, 434–446 | `EXISTS_AND_VERIFIED` | N/A (Doc) | 3-month paper validation runbook not formally detailed. |
| **B. Runtime Orchestration** | `src/acash/runtime/supervisor.py`<br>`src/acash/runtime/daemon.py` | `RuntimeSupervisor`<br>`ContinuousPaperDaemon` | `EXISTS_AND_VERIFIED` | `tests/unit/runtime/test_supervisor.py`<br>`tests/unit/runtime/test_daemon.py` | Stops at Stage 5 admission hook; does not dispatch to execution coordinator. Daemon consumes generator, not async timer. |
| **C. Telemetry & Drift** | `src/acash/monitoring/metrics.py`<br>`src/acash/monitoring/attribution.py`<br>`src/acash/monitoring/state_machine.py` | `ForwardMetricsCalculator`<br>`ExecutionAttributionEngine`<br>`ForwardHealthStateMachine` | `EXISTS_AND_VERIFIED` | `tests/unit/monitoring/test_window_metrics.py`<br>`tests/unit/monitoring/test_execution_attribution.py`<br>`test_forward_state_machine.py` | Attribution v1 is aggressive/taker only (`MAKER` rejected). Offline estimator; requires continuous ingestion feed. |
| **D. Venue Execution Adapters** | `src/acash/execution/mt5/adapter.py`<br>`src/acash/execution/alpaca/adapter.py` | `MT5BrokerAdapter`<br>`AlpacaPaperAdapter` | `EXISTS_AND_VERIFIED` | `tests/unit/execution/test_mt5_adapter.py`<br>`tests/unit/execution/test_alpaca_adapter.py` | MT5 requires local running terminal; Alpaca requires internet + paper credentials. Both lack continuous unattended retry loops. |
| **E. Paper Execution Seam** | `src/acash/execution/alpaca/paper_exercise.py`<br>`src/acash/execution/alpaca/order_exercise.py` | `PaperReadOnlyEvidence`<br>`run_order_exercise_verification` | `EXISTS_BUT_INCOMPLETE` | `tests/unit/execution/test_alpaca_paper_exercise.py`<br>`test_alpaca_order_exercise.py` | Built for discrete test checkpoints (`P-001`); not a continuous 3-month daemon loop. |
| **F. Mock Execution Engine** | `src/acash/execution/mock.py` | `MockExecutionEngine` | `EXISTS_AND_VERIFIED` | `tests/unit/test_mock_adapters.py` | In-memory only. Fixed fee/slippage calculation. No partial fill or queue dynamics. |
| **G. Mock Broker (Simulator)** | `src/acash/execution/mock_broker.py` | `MockBroker`<br>`MockBrokerOrder` | `EXISTS_AND_VERIFIED` | `tests/unit/execution/test_mock_broker.py`<br>`test_cancellation_races.py` | In-memory only. Requires manual invocation (`apply_full_fill`, `apply_partial_fill`); no autonomous matching against price ticks. |
| **H. Execution Reconciliation** | `src/acash/execution/coordinator.py`<br>`src/acash/execution/mt5/reconciliation.py` | `ExecutionCoordinator`<br>`MT5AuthoritativeReconciler` | `EXISTS_AND_VERIFIED` | `tests/unit/execution/test_coordinator.py`<br>`tests/unit/execution/test_mt5_reconciliation.py` | `ExecutionCoordinator` is in-memory pure logic. `MT5AuthoritativeReconciler` is MT5-specific. |
| **I. Operational Ledger** | `src/acash/runtime/ledger.py` | `OperationalLedger`<br>`OperationalCycleEvent` | `EXISTS_AND_VERIFIED` | `tests/unit/runtime/test_ledger.py` | Thread-safe, append-only, SHA-256 chained JSONL. Replays on boot. Stores cycle summaries, not per-fill tick logs. |
| **J. Decision Ledger** | `src/acash/storage/mock.py`<br>`src/acash/monitoring/ledger.py` | `InMemoryDecisionLedger`<br>`MonitoringEvidenceLedger` | `EXISTS_BUT_INCOMPLETE` | `tests/unit/test_decision_ledger.py`<br>`tests/unit/monitoring/test_ingestion_and_ledger.py` | `InMemoryDecisionLedger` is in-memory only (lost on restart). `MonitoringEvidenceLedger` persists to `OperationalLedger` on disk. |
| **K. Strategy Interfaces** | `src/acash/research/strategies.py`<br>`src/acash/backtest/strategies/` | `MicrostructureImbalanceStrategy`<br>`SessionVwapMeanReversionStrategy`<br>`MultiHorizonMomentumStrategy`<br>`MicrostructureImbalanceActor` | `EXISTS_BUT_INCOMPLETE` | `tests/unit/research/test_strategies.py`<br>`tests/unit/backtest/test_backtest_strategies.py` | Research strategies produce mathematical signals (`Decimal`), not order intents. Backtest actors are tied to `BacktestRunner`. No pre-sealed Phase 8.5 `AlphaQualificationDossier` file on disk. |
| **L. Market-Data Ingestion** | `src/acash/data/pipeline.py`<br>`src/acash/data/mock.py` | `IngestionPipeline`<br>`MockMarketDataProvider` | `EXISTS_BUT_INCOMPLETE` | `tests/unit/data/test_pipeline.py` | Ingestion is Parquet batch-oriented. `MockMarketDataProvider` is in-memory. Missing a forward real-time streaming feed / tick pump. |
| **M. Restart / Recovery** | `src/acash/runtime/ledger.py`<br>`src/acash/risk/kill_switch.py` | `OperationalLedger._replay_and_verify_existing_ledger`<br>`SovereignKillSwitchController._recover_state_from_disk` | `EXISTS_BUT_INCOMPLETE` | `tests/unit/runtime/test_ledger.py`<br>`tests/unit/risk/test_kill_switch_persistence.py` | Recovers ledger chain and kill switch state (`PERSISTENTLY_BLOCKED`). Does NOT rehydrate active open portfolio positions or order state machine. |
| **N. Monitoring / Health** | `src/acash/runtime/schema.py`<br>`src/acash/monitoring/state_machine.py` | `RuntimeHealthStatus`<br>`ForwardHealthStateMachine` | `EXISTS_AND_VERIFIED` | `tests/unit/monitoring/test_forward_state_machine.py` | 5-state anti-whipsaw hysteresis state machine. Lacks OS-level process supervisor / heartbeat watchdog. |
| **O. Scheduling & Cadence** | `src/acash/runtime/scheduler.py` | `OperationalScheduler` | `EXISTS_AND_VERIFIED` | `tests/unit/runtime/test_scheduler.py` | Evaluates cadence and prevents concurrent cycles. Has no internal wall-clock sleep/wake background loop. |
| **P. Long-Running Tests** | `tests/unit/runtime/test_daemon.py` | `test_daemon_step_pulse_and_harness_loop` | `EXISTS_BUT_INCOMPLETE` | `tests/unit/runtime/test_daemon.py` | Tests 3 to 100 discrete sequential pulses in-memory. No multi-day forward endurance tests. |

---

## 3. Paper Trading Capability Matrix

Requirements evaluated against the strict classification standard:

| Requirement Category | Specific Capability | Classification | Justification / Grounding |
|---|---|---|---|
| **Pipeline Core** | 5-Stage Fail-Closed Supervisor | `EXISTS_AND_VERIFIED` | `RuntimeSupervisor` in `src/acash/runtime/supervisor.py` (tested in `test_supervisor.py`). |
| **Pipeline Core** | Concurrency Lock & Dual-Clock | `EXISTS_AND_VERIFIED` | `OperationalScheduler` enforces `as_of_utc != wall_clock_utc` and busy locks. |
| **Pipeline Core** | Execution Admission Bridge | `MISSING` | Seam connecting Stage 5 output to `OrderIntent` generation and dispatch. |
| **Execution Simulation** | In-Memory Exchange Reality | `EXISTS_AND_VERIFIED` | `MockBroker` simulates ACK, partial fill, full fill, reject, and cancel races. |
| **Execution Simulation** | Autonomous Tick-Matching Engine | `MISSING` | `MockBroker` cannot autonomously match resting orders against incoming bars/ticks. |
| **Execution Simulation** | Real Paper Broker Transport | `EXISTS_AND_VERIFIED` | `AlpacaPaperAdapter` and `MT5BrokerAdapter` verified on real paper/demo venues. |
| **Risk Enforcement** | Multi-Tier Boundary Checks | `EXISTS_AND_VERIFIED` | `DeterministicRiskEngine` checks gross leverage, concentration, cash floor, drawdown. |
| **Risk Enforcement** | Sovereign Kill Switch | `EXISTS_AND_VERIFIED` | `SovereignKillSwitchController` with disk persistence and quorum recovery. |
| **Risk Enforcement** | Monotonic Derisking | `EXISTS_AND_VERIFIED` | `DeriskEngine` implements `EXACT_SCALE_DOWN` and `BINARY_REJECT`. |
| **State & Persistence** | Operational Cycle Event Ledger | `EXISTS_AND_VERIFIED` | `OperationalLedger` with append-only JSONL and SHA-256 chain verification. |
| **State & Persistence** | Forensic Monitoring Ledger | `EXISTS_AND_VERIFIED` | `MonitoringEvidenceLedger` adapts `OperationalLedger` for drift/cost evidence. |
| **State & Persistence** | Portfolio State Rehydration | `MISSING` | Process restart reloads ledger hashes but does not rebuild in-memory positions. |
| **State & Persistence** | Decision Ledger Disk Persistence | `EXISTS_BUT_INCOMPLETE` | `InMemoryDecisionLedger` is memory-only; needs persistence adapter. |
| **Market Data** | Historical Parquet & Integrity | `EXISTS_AND_VERIFIED` | `IngestionPipeline` + `ParquetStorageEngine` + `DataIntegrityValidator`. |
| **Market Data** | Forward Market Data Feed Pump | `MISSING` | No live streaming/polling pump delivering fresh market snapshots to daemon. |
| **Strategy Layer** | Baseline Research Strategies | `EXISTS_AND_VERIFIED` | OBI Imbalance, Session VWAP, and Multi-Horizon Momentum implemented. |
| **Strategy Layer** | Strategy Execution Wrapper | `MISSING` | Adapter translating research signals into candidate allocation for Stage 2/3. |
| **Strategy Layer** | Research-Qualified Dossier File | `MISSING` | No pre-computed, canonical `.json` dossier stored on disk for baseline strategy. |
| **Attribution & Metrics** | 8 Econometric Estimators | `EXISTS_AND_VERIFIED` | `ForwardMetricsCalculator` computes return, vol, Sharpe, MDD, HWM, hit rate, TE, t-stat. |
| **Attribution & Metrics** | Execution Drag Decomposition | `EXISTS_AND_VERIFIED` | `ExecutionAttributionEngine` computes spread, timing, slippage, fee, and rebate drag. |
| **Attribution & Metrics** | Drift State Machine | `EXISTS_AND_VERIFIED` | `ForwardHealthStateMachine` with 5 states and anti-whipsaw hysteresis. |
| **Operations** | Long-Running Daemon Loop | `EXISTS_BUT_INCOMPLETE` | `ContinuousPaperDaemon` exists but requires external iterator driver. |
| **Operations** | Windows Process Watchdog | `MISSING` | No external script/service monitoring daemon process liveness and restarting. |

---

## 4. Reusable Existing Components (Zero Reinvention)

The following components MUST be reused as-is without rewriting or duplicating:

1. **`RuntimeSupervisor` (`src/acash/runtime/supervisor.py`):** The authoritative 5-stage orchestrator. Must remain the central pipeline authority.
2. **`OperationalScheduler` (`src/acash/runtime/scheduler.py`):** Authoritative cadence, dual-clock verification, and concurrency lock.
3. **`OperationalLedger` (`src/acash/runtime/ledger.py`):** Append-only disk ledger with SHA-256 chaining.
4. **`DeterministicRiskEngine` (`src/acash/risk/risk_engine.py`):** Sovereign risk boundaries and allocation evaluation.
5. **`SovereignKillSwitchController` (`src/acash/risk/kill_switch.py`):** Emergency trip, disk persistence, and quorum reset.
6. **`ExecutionCoordinator` (`src/acash/execution/coordinator.py`):** Shadow order state machine, event deduplication, and reconciliation.
7. **`ForwardMetricsCalculator` (`src/acash/monitoring/metrics.py`):** Pure Decimal econometric performance calculations.
8. **`ExecutionAttributionEngine` (`src/acash/monitoring/attribution.py`):** Spread, slippage, timing, and fee drag decomposition.
9. **`MonitoringEvidenceLedger` (`src/acash/monitoring/ledger.py`):** Forensic evidence adapter for Phase 10 ledger.
10. **`ForwardHealthStateMachine` (`src/acash/monitoring/state_machine.py`):** Health transitions and governance recommendations.
11. **`AllocationTournamentRunner` (`src/acash/portfolio/tournament.py`):** Out-of-sample portfolio tournament.
12. **`MockBroker` (`src/acash/execution/mock_broker.py`):** Reality simulator for simulated broker fills.

---

## 5. Missing-Component / Gap Analysis

To run a reliable, continuous 3-month paper trading validation, exactly **4 architectural gaps** must be addressed:

### Gap 1: Paper Execution Bridge & Autonomous Fill Matcher
- **Defect:** `RuntimeSupervisor` stops at Stage 5 (`admission_hook_fn`). It does not convert an admitted `AllocationDecision` / `RiskEvaluationReport` into concrete `OrderIntent` objects and dispatch them to `ExecutionCoordinator`. Furthermore, if running fully offline on the Dev Host without external broker connectivity, `MockBroker` requires manual function calls to fill orders.
- **Requirement:** A lightweight, deterministic `PaperExecutionBridge`:
  1. Takes Stage 5 admitted allocation.
  2. Generates `OrderIntent` (target delta quantity = target - current).
  3. Dispatches intent to `ExecutionCoordinator`.
  4. Feeds order to either:
     - *Local Mode:* An autonomous `SimulatedMarketMatcher` that executes simulated fills against the latest bar/quote with realistic spread and fee assumptions.
     - *Venue Mode:* `AlpacaPaperAdapter` or `MT5BrokerAdapter` (when paper/demo connection is available).

### Gap 2: Forward Market Data Feeder (Feed Pump)
- **Defect:** ACASH has batch ingestion (`IngestionPipeline`) and in-memory mock (`MockMarketDataProvider`), but lacks a forward tick/bar pump that feeds fresh market data at scheduled intervals.
- **Requirement:** A `ForwardMarketDataFeeder`:
  - In *Offline Simulation Mode:* Streams historical bars forward sequentially in real time (e.g. 1 bar per minute or accelerated 1 pulse per 5 seconds), updating `IMarketDataProvider` and tracking `data_age_ms`.
  - In *Online Demo Mode:* Polls MT5 Demo or Alpaca Paper market quotes at 1-minute cadence.

### Gap 3: State Rehydration on Startup (Crash/Restart Survival)
- **Defect:** If the daemon or host machine restarts, `OperationalLedger` audits the historical hash chain, but in-memory `PortfolioState` (cash, positions, equity) starts from default blank values.
- **Requirement:** A `PortfolioStateRehydrator`:
  - Inspects the last valid `OperationalCycleEvent` from `OperationalLedger`.
  - Reconstitutes the exact portfolio positions, cash balance, and active strategy state as of the last cycle before the shutdown.

### Gap 4: Canonical Baseline Strategy Qualification Dossier
- **Defect:** Stage 2 of `RuntimeSupervisor` (`Strategy Census`) strictly filters for `AlphaLifecycleState.RESEARCH_QUALIFIED`. If zero qualified dossiers are passed, the supervisor executes the governed 100% Cash fallback (`GOVERNANCE_FALLBACK`).
- **Requirement:** Seal a canonical, verifiable `AlphaQualificationDossier` file for at least one baseline strategy (e.g. `MultiHorizonMomentumStrategy` or `MicrostructureImbalanceStrategy`) grounded in Phase 8.5 schema, and store it on disk so the supervisor can load and trade it.

---

## 6. Proposed Paper Runtime Architecture

The proposed Paper Trading architecture strictly honors the Sovereign Separation of Concerns and has **ZERO live broker wire access**:

```text
                     FORWARD MARKET DATA FEEDER
               (Real Demo Feed or Historical Tick Pump)
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      CONTINUOUS PAPER DAEMON                           │
│                                                                        │
│   STAGE 1: Freshness Check (data_age_ms <= max_market_data_age_ms)    │
│                                │                                       │
│   STAGE 2: Strategy Census (Load RESEARCH_QUALIFIED Dossier)          │
│                                │                                       │
│   STAGE 3: Allocation Tournament (AllocationTournamentRunner)          │
│                                │                                       │
│   STAGE 4: Sovereign Risk Gate (DeterministicRiskEngine + Kill Switch) │
│                                │                                       │
│   STAGE 5: Execution Admission Verification                            │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │ Admitted Allocation
                                 ▼
                     PAPER EXECUTION BRIDGE
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       [Local Dev Mode]                  [Online Demo Mode]
    Simulated Market Matcher             MT5 Demo / Alpaca Paper
    (Spread + Slippage Model)            (Zero Real Capital)
                 │                               │
                 └───────────────┬───────────────┘
                                 │ Raw Broker Event
                                 ▼
                     EXECUTION COORDINATOR
           (transition_order() Sole State Authority)
                                 │
                                 ▼
                     6-DIMENSIONAL RECONCILIATION
                                 │
                                 ▼
                 FORENSIC PERSISTENCE & MONITORING
                 ├── OperationalLedger (JSONL + SHA-256)
                 ├── MonitoringEvidenceLedger (Drift & Drag)
                 └── ForwardMetricsCalculator (Rolling Econometrics)
```

---

## 7. 3-Month Validation Program Design

The 3-month paper validation program is structured into three progressive operational categories:

```
Month 1: SYSTEM STABILITY ──► Month 2: STRATEGY BEHAVIOR ──► Month 3: ROBUSTNESS
```

### Month 1 — System Stability & Operational Invariants
- **Primary Goal:** Prove runtime survival, data integrity, and crash recovery.
- **Validation Categories:**
  - *Process Uptime:* Measure uptime ratio, cycle dispatch punctuality, and scheduler lockouts.
  - *Restart & Recovery:* Execute planned process restarts; assert 100% fidelity of portfolio state rehydration and zero ledger hash corruption.
  - *Data Freshness Discipline:* Verify that stale market data (>1500ms or missed bar) cleanly triggers `CycleOutcome.DATA_STALE` and blocks order generation.
  - *Reconciliation Health:* Verify that 100% of paper fills reconcile cleanly across all 6 dimensions (Intent, Symbol, Volume, Price, State, Fill History) with zero unresolved incidents.
  - *Risk Gate Integrity:* Assert zero risk boundary breaches; verify sovereign kill switch trip/recovery semantics.

### Month 2 — Strategy Behavior & Realized Execution Drag
- **Primary Goal:** Evaluate strategy signal behavior and quantify reality gap in paper execution.
- **Validation Categories:**
  - *Expectancy & Sharpe:* Track rolling annualized return, volatility, and Sharpe ratio via `ForwardMetricsCalculator`.
  - *Realized Execution Drag:* Decompose execution frictions via `ExecutionAttributionEngine`:
    - Spread drag vs benchmark midpoint
    - Timing drag between decision and arrival
    - Slippage drag from arrival quote to fill price
    - Simulated broker commission drag
  - *Regime Tracking:* Monitor strategy performance across distinct market regimes (trending vs ranging, high-vol vs low-vol).
  - *Shadow Decisions:* Record rejected orders and derisked allocations for counterfactual evaluation.
  - *Drawdown Control:* Verify peak-to-trough drawdown behavior against theoretical backtest limits.

### Month 3 — Robustness & Degraded Environment Endurance
- **Primary Goal:** Prove resilience against market turbulence, anomalies, and infrastructure disruptions.
- **Validation Categories:**
  - *Volatility Spike Endurance:* Replay high-volatility sessions (e.g. CPI/NFP release or market flash events) through the paper harness; assert proper derisking.
  - *Data Interruption Handling:* Inject synthetic feed drops and delayed ticks; verify fail-closed transition to `RUNTIME_DEGRADED` / `MONITORING_BLOCKED` without spurious strategy demotions.
  - *Adversarial Cancellation Races:* Subject paper orders to simultaneous fill-and-cancel events; assert `ExecutionCoordinator` correctly handles late events and duplicates.
  - *Long-Term Drift Evaluation:* Evaluate `ForwardHealthStateMachine` over the cumulative 90-day window; check for structural alpha degradation.

---

## 8. Failure & Recovery Test Plan

To guarantee the system survives real-world development host disruptions, the following adversarial test scenarios must be executed and verified before launching the 3-month validation:

| Scenario ID | Disruption Type | Injection Method | Expected Fail-Closed Behavior |
|---|---|---|---|
| **FR-01** | Process Crash | `kill -9` / unhandled kill during active cycle | Next startup detects incomplete cycle, audits ledger chain, rehydrates state from last committed event, and resumes without duplicate cycle ID. |
| **FR-02** | Machine Reboot | Sudden host restart | Ledger integrity verified on boot via `verify_ledger_integrity()`; kill switch state verified; portfolio balance and positions reconstituted. |
| **FR-03** | Stale Data Feed | Disconnect feed or freeze clock for 5,000ms | Supervisor Stage 1 detects `data_age_ms > 1500ms`, emits `CycleOutcome.DATA_STALE`, and blocks order generation. |
| **FR-04** | Corrupted Ledger Line | Bit-flip a single byte in `operational_ledger.jsonl` | Daemon startup halts immediately with `DataContractError("Ledger Corrupted")`; refuses to operate on corrupted evidence chain. |
| **FR-05** | Duplicate Event Replay | Re-send previously committed `broker_event_id` | `ExecutionCoordinator` detects duplicate event identity, ignores fill re-application, and records `DUPLICATE_EVENT` incident. |
| **FR-06** | Late Fill After Cancel | Deliver fill event after order reached `CANCELLED` | `transition_order()` raises terminal absorbing error; coordinator records `LATE_EVENT` incident; fill quantity not credited. |
| **FR-07** | Kill Switch Trip | Invoke `kill_switch.trip()` mid-operation | Next cycle immediately rejected at Stage 4 (`CycleOutcome.RISK_REJECTED`); status report shows `is_kill_switch_blocked=True`. |
| **FR-08** | Clock Inversion | Inject negative time delta ($t_{\text{current}} < t_{\text{last}}$) | `OperationalScheduler` detects temporal inversion and raises `DataContractError`. |

---

## 9. Metrics Availability Matrix

Auditing all desired paper trading measurements against current implementation capability:

| Metric Category | Desired Metric | Implemented Class / Function | Status | Supported Units / Notes |
|---|---|---|---|---|
| **Performance** | PnL (Realized / Unrealized) | `PortfolioState.realized_pnl`, `unrealized_pnl` | `EXISTS_AND_VERIFIED` | Decimal USD |
| **Performance** | Drawdown (Rolling Window) | `ForwardMetricsCalculator.calculate_window_metrics` | `EXISTS_AND_VERIFIED` | Decimal percentage (peak-to-trough) |
| **Performance** | Drawdown (Inception HWM) | `ForwardMetricsCalculator.calculate_window_metrics` | `EXISTS_AND_VERIFIED` | Decimal percentage (HWM) |
| **Performance** | Expectancy | `StrategyRegimeObservation.expectancy_bps` | `EXISTS_AND_VERIFIED` | Basis points (bps) |
| **Performance** | Win Rate / Hit Rate | `ForwardMetricsCalculator._calculate_hit_rate` | `EXISTS_AND_VERIFIED` | Decimal fraction [0.0, 1.0] |
| **Performance** | Annualized Return | `ForwardMetricsCalculator._calculate_mean_return` | `EXISTS_AND_VERIFIED` | Decimal annualized return |
| **Performance** | Annualized Volatility | `ForwardMetricsCalculator._calculate_volatility` | `EXISTS_AND_VERIFIED` | Decimal sample standard deviation |
| **Performance** | Annualized Sharpe Ratio | `ForwardMetricsCalculator._calculate_sharpe_ratio` | `EXISTS_AND_VERIFIED` | Decimal Sharpe (fail-closed on zero var) |
| **Performance** | Tracking Error & t-Stat | `ForwardMetricsCalculator.calculate_window_metrics` | `EXISTS_AND_VERIFIED` | Decimal |
| **Performance** | Profit Factor | N/A | `MISSING` | Derivable from gross wins / gross losses. |
| **Performance** | Turnover | N/A | `MISSING` | Derivable from traded notional / equity. |
| **Execution** | Spread Drag | `ExecutionAttributionEngine.decompose_execution_drag` | `EXISTS_AND_VERIFIED` | Basis points (bps) |
| **Execution** | Timing Drag | `ExecutionAttributionEngine.decompose_execution_drag` | `EXISTS_AND_VERIFIED` | Basis points (bps) |
| **Execution** | Slippage Drag | `ExecutionAttributionEngine.decompose_execution_drag` | `EXISTS_AND_VERIFIED` | Basis points (bps) |
| **Execution** | Commission Fee Drag | `ExecutionAttributionEngine.decompose_execution_drag` | `EXISTS_AND_VERIFIED` | Basis points (bps) |
| **Execution** | Rebate Benefit | `ExecutionAttributionEngine.decompose_execution_drag` | `EXISTS_AND_VERIFIED` | Basis points (bps) |
| **Execution** | Gross & Net Realized Drag | `ExecutionAttributionEngine.decompose_execution_drag` | `EXISTS_AND_VERIFIED` | Basis points (bps) |
| **Execution** | Partial Fills | `MockBroker.apply_partial_fill`, `ExecutionCoordinator` | `EXISTS_AND_VERIFIED` | Decimal quantity |
| **Execution** | Missed Fills / Rejections | `MockBroker.reject`, `ExecutionCoordinator` | `EXISTS_AND_VERIFIED` | Count and incident record |
| **Risk** | Gross / Net Exposure | `PortfolioState.gross_exposure`, `net_exposure` | `EXISTS_AND_VERIFIED` | Decimal USD |
| **Risk** | Margin Utilization | `RiskEvaluationReport.metrics["margin_utilization"]` | `EXISTS_AND_VERIFIED` | Decimal percentage |
| **Risk** | Risk Breaches / Vetoes | `RiskEvaluationReport.verdict`, `rejection_reason` | `EXISTS_AND_VERIFIED` | Enum (`RiskVerdict.REJECTED`) |
| **Risk** | Derisking Adjustments | `DeriskEngine.calculate_derisk_adjustment` | `EXISTS_AND_VERIFIED` | Exact scale-down weights |
| **Research** | Strategy ID / Version | `StrategyDefinition.strategy_id`, `strategy_version` | `EXISTS_AND_VERIFIED` | String |
| **Research** | Market Regime Label | `RuntimeRegime`, `StrategyRegimeObservation` | `EXISTS_AND_VERIFIED` | Enum |
| **Research** | Accepted / Rejected Trades | `CycleExecutionSummary.admitted_for_execution` | `EXISTS_AND_VERIFIED` | Boolean + Ledger digest |
| **Research** | Shadow Decisions | `AllocationDecision.unselected_candidates` | `EXISTS_AND_VERIFIED` | Cryptographic digests |
| **Operational** | Uptime & Cycle Count | `DaemonStatusReport.total_cycles_executed` | `EXISTS_AND_VERIFIED` | Integer count |
| **Operational** | Data Stale Incidents | `CycleOutcome.DATA_STALE` | `EXISTS_AND_VERIFIED` | Count in ledger |
| **Operational** | Reconciliation Mismatches | `CoordinatorIncidentKind.RECONCILIATION_CONFLICT` | `EXISTS_AND_VERIFIED` | Forensic incident records |
| **Operational** | Ledger Event Count & Digest | `OperationalLedger.event_count`, `last_event_digest` | `EXISTS_AND_VERIFIED` | Monotonic int + SHA-256 string |

---

## 10. Explicit Blockers & Non-Blockers

### 10.1 Explicit Blockers (Must be resolved before starting 3-month paper trading)
1. **Paper Execution Bridge:** Missing adapter connecting `RuntimeSupervisor` Stage 5 to `ExecutionCoordinator` and order dispatch.
2. **Autonomous Fill Matching (for offline mode):** `MockBroker` does not match orders against incoming bars automatically.
3. **State Rehydration:** Need a startup routine to reload open portfolio positions from `OperationalLedger`.
4. **Qualified Strategy Dossier:** Need a serialized, verifiable `AlphaQualificationDossier` file on disk for a baseline strategy so Stage 2 census admits it.

### 10.2 Explicit Non-Blockers (DO NOT block paper trading)
1. **Assertion B23.2 (WDAC Enforce Mode):** Non-blocker. B23.2 is an enterprise production live-governance requirement for live capital. It has zero bearing on paper trading on the development host.
2. **Phase 13 Gate B Step 3 Ceremony / Step 4 Activation:** Non-blocker. These are live-capital release gates and remain strictly locked ($0.00 capital).
3. **Phase 14–28 Roadmap Items:** Non-blocker. Future phases (AI quant layer, L3 microstructure replay, strategy state machine) are not required for baseline paper validation.
4. **Hardware HSM / Key Ceremony:** Non-blocker. Paper trading does not sign live broker wires.
5. **Maker Attribution:** Non-blocker. Paper execution uses taker-style market/limit fills; maker attribution is explicitly deferred.

---

## 11. Minimal Required Implementation Scope (For Human Approval)

To make ACASH fully paper-trading ready on the development host, the minimal necessary changes are confined to **4 new lightweight files and 0 modifications to frozen core contracts**:

1. `src/acash/runtime/paper_bridge.py`:
   - `PaperExecutionBridge`: Connects Stage 5 admitted allocation to `ExecutionCoordinator`.
   - `SimulatedMarketMatcher`: Matches resting orders against incoming bars/ticks using spread and fee models.
2. `src/acash/runtime/feeder.py`:
   - `ForwardMarketDataFeeder`: Feeds market data bars/ticks at configured cadences (historical replay or demo feed).
3. `src/acash/runtime/rehydration.py`:
   - `PortfolioStateRehydrator`: Rebuilds in-memory `PortfolioState` from the latest `OperationalCycleEvent`.
4. `var/governance/dossiers/baseline_momentum_dossier.json`:
   - Sealed canonical `AlphaQualificationDossier` for `MultiHorizonMomentumStrategy` to satisfy Stage 2 census.
5. Accompanying adversarial unit tests in `tests/unit/runtime/test_paper_bridge.py`.

*All implementation will be executed strictly on the current development host. Zero live credentials, zero live capital.*

---

## 12. Final Governance Status Ledger

```text
================================================================================
                    ACASH PHASE 13 GOVERNANCE STATUS LEDGER
================================================================================
Phase 13 Gate A (Pre-Live Certification):     PASS (CERTIFIED)
Phase 13 Gate B (Governance Repair Rev 10):    CONDITIONAL PASS (Step 2 Complete)
Assertion B1–B22 (Adversarial Suite):          PASS (22/22 Verified)
Assertion B23.1 (WinVerifyTrust):              PASS (Cryptographically Verified)
Assertion B23.2 (Host Kernel Enforcement):     NOT PROVEN / DEFERRED
Paper Trading Readiness:                      EXISTS_BUT_INCOMPLETE (4 Gaps Identified)
Step 3 Ceremony:                               BLOCKED (LOCKED)
Step 4 Activation:                             BLOCKED (LOCKED)
Slice 3 First Live Order:                      BLOCKED (LOCKED)
Live Capital Authority:                        $0.00 (ZERO)
Live Orders Dispatched:                        0
Live Broker Wire:                              DISCONNECTED
================================================================================
```

> **Mandatory Boundary Statement:**  
> `PASS` on unit tests $\neq$ `LIVE AUTHORIZATION`.  
> `PAPER READY` $\neq$ `LIVE READY`.  
> Implementation remains on hold awaiting explicit human approval.
