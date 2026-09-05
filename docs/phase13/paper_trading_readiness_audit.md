# ACASH Phase 13 — Paper Trading Readiness Audit & Implementation Contract
# 3-Month Continuous Forward Operation Specification (Revision 2)

> **Document ID:** `docs/phase13/paper_trading_readiness_audit.md`  
> **Version:** 2.0.0 (Implementation Contract Edition)  
> **Date:** 2026-09-05  
> **Status:** AUDIT PASSED — IMPLEMENTATION LOCKED AWAITING HUMAN GO  
> **Governance Authority:** Phase 13 Gate A (Certified), Gate B Rev 10 Step 2 (Conditional Pass), B23.2 (Not Proven / Deferred)  
> **Rule Enforcement:** Zero unverified claims; zero synthetic dossiers; zero code modifications prior to explicit approval.

---

## 1. Executive Summary & Governance Boundary

This document establishes the definitive, audited **Implementation Contract** required for ACASH to execute a reliable, continuous **3-month Paper Trading validation program** on the current Windows development host.

### 1.1 Governance Boundary (Immutable)
- **Phase 13 Gate A:** `CERTIFIED` (Formal Human Sign-off 2026-09-04; MT5 Demo `112040157` flat).
- **Phase 13 Gate B (Rev 10 Step 2):** `CONDITIONAL PASS` (B1–B22 PASS, B23.1 PASS, B23.2 NOT PROVEN / DEFERRED).
- **Assertion B23.2 (Host Kernel Enforcement):** `NOT PROVEN / DEFERRED` to future dedicated 24/7 cloud/VM infrastructure.
- **Step 3 Ceremony:** `STRICTLY BLOCKED / LOCKED`.
- **Step 4 Activation:** `STRICTLY BLOCKED / LOCKED`.
- **Slice 3 (First Live Order):** `STRICTLY BLOCKED / LOCKED`.
- **Live Capital Authority:** `$0.00` | **Live Orders Dispatched:** `0` | **Live Broker Connection:** `DISCONNECTED`.

### 1.2 Core Architectural Principles for Paper Trading
1. **Paper $\neq$ Backtest:** Paper trading is continuous forward operation consuming market data arriving in real time; replaying historical data is backtesting, never paper trading.
2. **Zero Synthetic Qualification:** We strictly forbid manufacturing a fake `AlphaQualificationDossier` merely to make upstream checks pass. Strategy qualification must be earned through the legitimate Phase 8.5 / Phase 17 mathematical contract.
3. **Core Gaps vs. Deployment Hardening:** Exactly **4 Core Architectural Gaps** are recognized. External process supervision (watchdogs, restart daemons) is classified as an OS-level deployment concern, keeping ACASH core pure and unbloated.
4. **Execution Realism:** The MetaQuotes MT5 Demo environment serves as the primary paper execution environment (leveraging existing frozen Phase 12 adapters and 6-D reconciliation), with an offline `SimulatedMarketMatcher` serving as a deterministic test double.

---

## 2. Repository Fact Audit (Verified Baseline at Commit `e733d53`)

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

## 3. The 4 Core Architectural Gaps (Detailed Seam Specifications)

In accordance with auditor guidance (Option A), exactly **4 Core Architectural Gaps** are established. All external process monitoring is decoupled into an operational deployment concern.

### Gap 1: Paper Execution Bridge & Order Dispatch Seam
- **Existing Foundation:** `RuntimeSupervisor` (Stage 5 admission hook), `ExecutionCoordinator` (shadow state authority), `MT5BrokerAdapter` (Phase 12), `MockBroker` (Phase 7).
- **Exact Missing Seam:** A deterministic adapter that takes the admitted `AllocationDecision` from Stage 5, evaluates the target delta ($\Delta q_i = q_{\text{target}, i} - q_{\text{current}, i}$), constructs canonical `OrderIntent` DTOs, dispatches them to the selected venue (`MT5BrokerAdapter` or `SimulatedMarketMatcher`), and passes raw events to `ExecutionCoordinator`.
- **Exact New Files:** `src/acash/runtime/paper_bridge.py`
- **Interfaces Reused:** `IExecutionEngine`, `to_coordinator_event()`, `transition_order()`, `AllocationDecision`, `OrderIntent`.
- **Tests Required:**
  - Net zero delta produces zero orders.
  - Vetoed allocation in Stage 4/5 produces zero orders.
  - Partial fill updates shadow state without double accumulation.
  - Rejected paper order routes to coordinator incident log without raising unhandled crash.
- **Failure Semantics:** Strict fail-closed. If venue is unreachable or returns timeout, order transitions to `UNKNOWN`, triggering reconciliation rather than assuming a fill.

### Gap 2: Forward Market Data Feeder (Real-Time Tick/Bar Pump)
- **Existing Foundation:** `IMarketDataProvider` (`src/acash/core/interfaces/market_data.py`), `NativeMT5Transport` (Phase 12), `ParquetStorageEngine` (Phase 2).
- **Exact Missing Seam:** A continuous background feed pump that polls or streams live market prices as they arrive in real time, updates the active `IMarketDataProvider` cache, and tracks `data_age_ms` to feed Stage 1 freshness checks.
- **Exact New Files:** `src/acash/runtime/feeder.py`
- **Interfaces Reused:** `IMarketDataProvider`, `Bar`, `MarketDataSnapshot`, `NativeMT5Transport.get_latest_tick()`.
- **Tests Required:**
  - Fresh tick updates provider and resets `data_age_ms`.
  - Feed drop exceeding `max_market_data_age_ms` (1500ms) causes Stage 1 to halt with `DATA_STALE`.
  - Clock jump or negative timestamp raises `DataContractError`.
- **Failure Semantics:** Strict fail-closed. Zero synthetic data imputation; missing data halts rebalance pulse.

### Gap 3: Portfolio State Rehydration & Crash Recovery Seam
- **Existing Foundation:** `OperationalLedger` (JSONL + SHA-256 chain verification), `SovereignKillSwitchController._recover_state_from_disk()`.
- **Exact Missing Seam:** A startup rehydration routine that reads the most recent valid `OperationalCycleEvent` from the sealed ledger, reconstitutes in-memory `PortfolioState` (cash balance, open positions, realized PnL), and cross-checks with the broker reality before the first new pulse runs.
- **Exact New Files:** `src/acash/runtime/rehydration.py`
- **Interfaces Reused:** `OperationalLedger`, `OperationalCycleEvent`, `PortfolioState`, `AccountState`, `RiskStateBridge`.
- **Tests Required:**
  - Corrupted ledger line halts rehydration fail-closed.
  - Clean restart restores exact position quantities, cash, and equity.
  - Reconciles recovered state against broker open positions; raises discrepancy incident if mismatched.
- **Failure Semantics:** If ledger digest is broken or broker positions disagree with recovered state, daemon enters `RUNTIME_HALTED` and refuses to dispatch orders.

### Gap 4: Legitimate Strategy Qualification & Paper Eligibility
- **Existing Foundation:**
  - Baseline Strategies: `MultiHorizonMomentumStrategy`, `SessionVwapMeanReversionStrategy`, `MicrostructureImbalanceStrategy` (`src/acash/research/strategies.py`).
  - Master Qualification Gate: `AlphaQualificationGate` (`src/acash/research/qualification.py`).
  - Lifecycle States: `AlphaLifecycleState.FORWARD_PAPER_MONITORED`, `RESEARCH_QUALIFIED` (`src/acash/research/alpha_schema.py`).
- **Exact Missing Seam:**
  - Zero strategies currently hold a legitimately sealed `AlphaQualificationDossier` file on disk.
  - We strictly **FORBID** fabricating a fake `baseline_momentum_dossier.json`.
  - Stage 2 of `RuntimeSupervisor` currently filters strictly for `lifecycle_state == AlphaLifecycleState.RESEARCH_QUALIFIED`. Under the canonical lifecycle state graph, an alpha entering forward paper testing holds state `FORWARD_PAPER_MONITORED`.
  - The seam requires either:
    1. Executing an authentic Phase 6 / 8.5 qualification run on historical data to earn `RESEARCH_QUALIFIED`, OR
    2. Extending `RuntimeSupervisor` Stage 2 census to legitimately admit dossiers in `FORWARD_PAPER_MONITORED` state for forward paper tracking (governed by Phase 11).
- **Exact New Files:** `src/acash/runtime/strategy_adapter.py` (wraps baseline strategy into allocation candidate).
- **Status:** **`BLOCKED (QUALIFICATION PENDING)`**.

---

## 4. Candidate Strategy & Paper Eligibility Audit

### 4.1 Strategy Candidate Identification
The primary candidate for the 3-month paper validation is:
- **Strategy ID:** `STRAT-MOM-MULTI-HORIZON-V1`
- **Class:** `MultiHorizonMomentumStrategy` (`src/acash/research/strategies.py`)
- **Mechanism:** Time-Series Momentum (TSMOM) evaluating multi-horizon return signs across lookback bars.
- **Style:** Systematic Trend-Following (Taker execution, zero maker-rebate reliance).
- **Target Instrument:** EURUSD / SPY (liquid baseline).

### 4.2 Current Qualification Status: BLOCKED
- **Audit Finding:** The strategy code exists and executes unit tests cleanly, but **no authentic Phase 6 ValidationReport, no sealed SearchTrialLedger, and no Phase 8.5 AlphaQualificationDossier exist on disk**.
- **Governance Constraint:** We refuse to synthesize artificial evidence. Prior to starting the 3-month paper trading run, the candidate strategy must execute the canonical qualification pipeline:
  $$\text{HypothesisSpec} \longrightarrow \text{SearchTrialLedger (Sealed)} \longrightarrow \text{ValidationReport (PASS)} \longrightarrow \text{AlphaQualificationGate} \longrightarrow \text{Dossier}$$
  Only when this pipeline succeeds with net positive trading alpha after friction may the strategy be admitted to paper trading.

---

## 5. Paper Trading Session Identity Specification

To guarantee that 3 months of forward paper execution data remains forensically auditable, unpolluted, and traceable, every paper run MUST be initialized with an immutable **Paper Trading Session Identity**:

```json
{
  "paper_run_id": "PAPER-RUN-20260905-001",
  "strategy_id": "STRAT-MOM-MULTI-HORIZON-V1",
  "strategy_version": "1.0.0",
  "start_time_utc": "2026-09-05T14:00:00Z",
  "end_time_utc": null,
  "config_digest": "4a7b9c... (SHA-256 of RuntimePolicyConfig)",
  "dossier_digest": "8f2e1a... (SHA-256 of AlphaQualificationDossier)",
  "data_source": "METAQUOTES_MT5_DEMO",
  "execution_mode": "MT5_DEMO_VENUE",
  "ledger_path": "var/paper/PAPER-RUN-20260905-001/operational_ledger.jsonl"
}
```

This identity is embedded in every `OperationalCycleEvent` and every `MonitoringEvidenceLedger` record, preventing data cross-contamination across restarts or strategy iterations.

---

## 6. Execution Environment Architecture: MT5 Demo Primary vs. Local Simulator

The Paper Execution Bridge supports two distinct execution backends behind a unified interface:

```text
                           PAPER EXECUTION BRIDGE
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
       PRIMARY EXECUTION VENUE                 DETERMINISTIC FALLBACK
          [MT5 Demo Account]                  [Simulated Market Matcher]
    ├── Real broker terminal connection      ├── 100% offline, zero network
    ├── MetaQuotes-Demo Server               ├── Spread + slippage + fee model
    ├── Authoritative 6-D Reconciliation     ├── Instant local execution
    └── Real broker fills & latency          └── Ideal for soak tests & unit tests
```

- **Primary Path (MT5 Demo):** Used for the 90-day forward validation program. Leverages existing `MT5BrokerAdapter` and `MT5AuthoritativeReconciler` verified under Gate A and Phase 12 (`1e1d154`).
- **Fallback Path (Local Simulator):** Used for unit tests, offline continuous integration, and initial recovery tests.

---

## 7. Mandatory Pre-90-Day Progressive Validation Sequence

A continuous 90-day forward run represents a significant operational commitment. The system MUST progress through a strict, multi-stage verification ladder before the 90-day run commences:

```
[1. Minimal Implementation]
        ↓
[2. Unit Tests (Pytest 100% clean)]
        ↓
[3. Integration Tests (Bridge + Rehydration + Feeder)]
        ↓
[4. Restart / Recovery Tests (FR-01 through FR-08)]
        ↓
[5. Short Soak Test (24–72 Hours Unattended)]
        ↓
[6. Soak Test Telemetry & Reconciliation Audit]
        ↓
[7. Paper Run Readiness Review]
        ↓
[8. EXPLICIT HUMAN GO AUTHORIZATION]
        ↓
[9. 90-Day Continuous Paper Trading Operation]
        ↓
[10. 3-Month Formal Econometric & Reality Gap Review]
```

Under no circumstances will a 90-day run be initiated immediately following unit test completion. The **24–72h Soak Test** is a mandatory prerequisite to prove memory stability, socket resilience, and scheduler punctuality.

---

## 8. Operational Hardening: External Process Supervision

In alignment with auditor guidance, process supervision is decoupled from the core Python codebase:

- **Classification:** Deployment & Infrastructure Concern (NOT ACASH Core).
- **Host OS Mechanism:** Windows Task Scheduler or Windows Service (NSSM).
- **Policy:** If `python -m acash.runtime.daemon` terminates unexpectedly, the Windows service manager automatically restarts the process after a 10-second backoff.
- **Contract Preservation:** The daemon startup routine immediately invokes `OperationalLedger.verify_ledger_integrity()` and `PortfolioStateRehydrator.rehydrate()`, ensuring that any crash-restart safely resumes without operator intervention.

---

## 9. Minimal Implementation File List (Scope for Human Approval)

When approved by human governance, implementation is strictly bounded to **4 new production files and 1 test file**:

| File Path | Component | Responsibility |
|---|---|---|
| `src/acash/runtime/paper_bridge.py` | `PaperExecutionBridge`<br>`SimulatedMarketMatcher` | Translates Stage 5 allocation into `OrderIntent`, routes to MT5 Demo or Local Matcher, and updates `ExecutionCoordinator`. |
| `src/acash/runtime/feeder.py` | `ForwardMarketDataFeeder` | Continuous market-data pump for live ticks/bars; updates `IMarketDataProvider` and tracks `data_age_ms`. |
| `src/acash/runtime/rehydration.py` | `PortfolioStateRehydrator` | Rebuilds `PortfolioState` from last `OperationalCycleEvent` on boot and cross-checks broker reality. |
| `src/acash/runtime/strategy_adapter.py` | `PaperStrategyAdapter` | Wraps baseline strategy into allocation candidate with `PaperTradingSessionIdentity`. |
| `tests/unit/runtime/test_paper_bridge.py` | Adversarial Test Suite | Tests all 4 seams, recovery paths, stale data drops, and order life cycles. |

*Zero modifications to frozen core contracts (Phases 1–12). Zero live broker wire access.*

---

## 10. Final Governance Status Ledger

```text
================================================================================
                    ACASH PHASE 13 GOVERNANCE STATUS LEDGER
================================================================================
Phase 13 Gate A (Pre-Live Certification):     PASS (CERTIFIED)
Phase 13 Gate B (Governance Repair Rev 10):    CONDITIONAL PASS (Step 2 Complete)
Assertion B1–B22 (Adversarial Suite):          PASS (22/22 Verified)
Assertion B23.1 (WinVerifyTrust):              PASS (Cryptographically Verified)
Assertion B23.2 (Host Kernel Enforcement):     NOT PROVEN / DEFERRED
Paper Trading Readiness Audit:                PASS (Contract Formalized)
Candidate Strategy Qualification:              BLOCKED (Qualification Run Pending)
Paper Runtime Implementation:                 LOCKED (Awaiting Explicit Human GO)
Step 3 Ceremony:                               BLOCKED (LOCKED)
Step 4 Activation:                             BLOCKED (LOCKED)
Slice 3 First Live Order:                      BLOCKED (LOCKED)
Live Capital Authority:                        $0.00 (ZERO)
Live Orders Dispatched:                        0
Live Broker Wire:                              DISCONNECTED
================================================================================
```

> **Mandatory Boundary Statement:**  
> `PASS` on Audit $\neq$ `IMPLEMENTATION APPROVAL`.  
> `PAPER READY` $\neq$ `LIVE READY`.  
> Implementation remains strictly halted awaiting explicit human approval.
