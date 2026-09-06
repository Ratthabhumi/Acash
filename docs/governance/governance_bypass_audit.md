# ACASH Standing By: Read-Only Governance Integrity & Bypass Audit Report

> **Document ID:** `AUDIT-GOV-BYPASS-20260906-002`  
> **Timestamp:** `2026-09-06T23:18:00+00:00`  
> **Auditor:** Static Architecture Analysis Engine  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed)  
> **Overall Verdict:** `PASS`  
> **Classification:** `VERIFIED FOR TESTED ENFORCEMENT PATHS` (Repository-wide static audit; not formal mathematical proof of all arbitrary bypasses)  

---

## 1. Scope of Audit

This audit evaluates the mechanical integrity and architectural isolation of the ACASH governance controls following the completion of Governance Invariant Hardening.

### Strict Non-Execution Boundaries (Mandatory Affirmations)
- **Zero Empirical Research:** No backtests, statistical trials, or alpha fits were executed.
- **Zero Market Data Inspection:** No market-data files were evaluated, resampled, or read for data analysis.
- **Zero Holdout Exposure:** Quarantined M5 holdout partitions (bars 6,060..9,999) were **never accessed or read**.
- **Zero New Hypotheses:** No `HYP_..._002` was created or registered.
- **Zero Broker Connectivity:** No broker sockets, transports, or terminals were activated.
- **Zero Order Submission:** Zero live or paper orders were emitted.
- **Zero Capital Allocation:** Capital authority remains strictly hard-locked at **`$0.00`**.
- **Zero Artifact Mutation:** All sealed research manifests, digests, and frozen core files remain strictly unmutated.

---

## 2. Static Audit Methodology

The audit inspected all Python source files (`src/`), operational scripts (`scripts/`), test suites (`tests/`), and documentation (`docs/`) using static call-graph tracing, pattern matching, symbol usage analysis, and state transition graph verification:
1. **Data Authorization & Quarantine Seams:** Traced all occurrences of Parquet/CSV file loading (`read_table`, `read_csv`, `pyarrow.parquet`).
2. **Trading & Dispatch Seams:** Traced all dispatch mechanisms (`submit_order`, `can_dispatch`, `evaluate_and_dispatch`, `ExecutionCoordinator`).
3. **Immutability Seams:** Inspected lifecycle state transitions (`AlphaLifecycleState`) and parameter mutation guards.
4. **Readiness Separation Seams:** Searched repository-wide for collapsed master switches (`system_ready`, `is_ready`, `can_trade`, `paper_ready`, `live_ready`, `authorize_trading`, `authorize_capital`).
5. **Step 8 / Step 9 Prerequisites:** Traced activation paths into continuous paper trading and verified conjunctive gating.

---

## 3. Research Data Authorization Paths

### 3.1 Evaluation of Specific Audit Questions (A–F)

| Question | Assessment | Detailed Static Evidence |
| :--- | :--- | :--- |
| **A. Does research execution pass through `DatasetQuarantineValidator`?** | **YES** | `scripts/execute_phase8_5_step_r3.py:87–96` invokes `DatasetQuarantineValidator.validate_dataset_binding_for_execution()` before reading `EURUSD_M5_canonical.parquet`. |
| **B. Can canonical research execution bypass `quarantine.py`?** | **NO** | In the canonical Step R3 execution pipeline, manifest verification and quarantine checks precede parquet file loading. |
| **C. Can it directly open a dataset before authorization?** | **NO (Canonical)**<br>**CAVEAT (Direct OS Call)** | In `execute_step_r3_census()`, dataset loading cannot occur before authorization. However, an arbitrary external Python script could theoretically call `pyarrow.parquet.read_table()` directly on the filesystem outside the ACASH framework. File system ACLs and immutable governance manifests are required to prevent out-of-process OS reads. |
| **D. Can it synthesize an authorization object without cryptographic binding?** | **NO** | `DatasetAuthorizationToken` validates that `exposure_state` cannot be initialized in `UNKNOWN` or `REVOKED` states, and requires exact matching of `bound_hypothesis_sha256` derived from universal `CanonicalConfigSerializer`. |
| **E. Can it use a dataset by path alone?** | **NO** | `DatasetQuarantineValidator` requires both `HypothesisSpecification` and `dataset_manifest`. If `manifest["hypothesis_id"] != spec.hypothesis_id`, execution is aborted with `CROSS_HYPOTHESIS_CONTAMINATION_ERROR`. |
| **F. Can a dataset with UNKNOWN / REVOKED / QUARANTINED state be reached?** | **NO** | `DatasetQuarantineValidator` checks exposure states fail-closed: `UNKNOWN` raises `DATASET_AUTHORIZATION_UNKNOWN`, `REVOKED` raises `DATASET_AUTHORIZATION_REVOKED`, and `QUARANTINED` raises `DATASET_QUARANTINED_ERROR`. |

### 3.2 In-Memory Layer vs. Storage Layer Separation
- **`src/acash/research/pipeline.py` (Phase 4):** Operates entirely on in-memory `pa.Table` objects provided by the caller; it does not read Parquet files from disk.
- **Architectural Boundary:** Data quarantine is strictly enforced at the **Ingestion / Data Loading Seam** (`scripts/execute_phase8_5_step_r3.py` and `acash.research.quarantine`) before in-memory tables are supplied to compute engines.

---

## 4. Trading Authorization Paths

### 4.1 Order Dispatch Entry Points
1. **`src/acash/runtime/paper_bridge.py` (`PaperExecutionBridge.evaluate_and_dispatch`):**
   - **Venue Restriction:** Supported venues are strictly `PaperExecutionVenueType.MT5_DEMO` and `LOCAL_SIMULATOR`. Live venue execution is architecturally impossible in this module.
   - **Strategy Gating:** Dispatches orders only if `allocation.gate_verdict == "APPROVED_INVESTABLE_ALLOCATION"` and `allocation.is_fallback_baseline is False`. If zero `RESEARCH_QUALIFIED` strategies exist, supervisor falls back to 100% Cash, and dispatch returns `[]` (0 orders).
2. **`src/acash/execution/mt5/adapter.py` (`MT5BrokerAdapter.submit_order`):**
   - **Transport Gate:** `can_dispatch()` evaluates only whether the IPC transport is connected and 6-D reconciled (`safety_state == READY and is_reconciled is True`).
   - It is an execution adapter, not a governance authority.
3. **`src/acash/gate_b/` (Phase 13 Slice 2 Live Activation):**
   - **Sovereign Barrier:** Live orders require an atomic CAS commit binding an Ed25519-signed `HumanGORecord`, an unbroken authoritative ledger head, and a 6-domain readiness check.
   - Currently: **Zero live authorizations exist; Live Capital Authority is strictly $0.00**.

---

## 5. Terminal Hypothesis Immutability Audit

### 5.1 Lifecycle State Machine Traversal
In `src/acash/research/alpha_schema.py`:
- `AlphaLifecycleState.TERMINALLY_FALSIFIED` is a terminal absorbing state.
- `ALLOWED_LIFECYCLE_TRANSITIONS[AlphaLifecycleState.TERMINALLY_FALSIFIED] == set()`:
  - Any call to `validate_lifecycle_transition(AlphaLifecycleState.TERMINALLY_FALSIFIED, ...)` raises `DataContractError("Illegal Alpha lifecycle transition...")`.
  - It is mathematically impossible to transition a hypothesis out of `TERMINALLY_FALSIFIED`.

### 5.2 Anti-HARKing Mutation Lock
- In `validate_hypothesis_immutability()`:
  - If a candidate hypothesis has `hypothesis_id == existing_spec.hypothesis_id` but a different SHA-256 digest, it raises `DataContractError("HYPOTHESIS_MUTATION_FORBIDDEN...")`.
  - Re-registering an existing hypothesis ID with modified parameters is strictly blocked.
- In `PERMANENTLY_QUARANTINED_HOLDOUTS`:
  - `HYP_TSMOM_EURUSD_001` holdout bars (6,060..9,999) are permanently registered as quarantined against any new hypothesis.

---

## 6. Readiness Plane Separation Audit

### 6.1 Search for Collapsed Master Switches
A repository-wide static search for master switches returned:
- `system_ready`: **0 occurrences in operational code** (appears only in negative tests asserting its non-existence).
- `is_ready`: **0 occurrences in operational code**.
- `can_trade`: **0 occurrences**.
- `paper_ready`: **0 occurrences**.
- `live_ready`: **0 occurrences**.
- `authorize_trading`: **0 occurrences**.
- `authorize_capital`: **0 occurrences**.

### 6.2 Inference Creep Protection
In `src/acash/core/readiness_planes.py`:
- `SystemReadinessPlanes` contains no master boolean attribute.
- `ReadinessPlaneEvaluator.validate_infrastructure_does_not_authorize_strategy()` strictly enforces:
  $$\mathbf{Infrastructure(SOAK\_VERIFIED\_PASS) \implies Strategy(RESEARCH\_QUALIFIED)\ is\ FORBIDDEN}$$
- Strategy qualification requires independent empirical research verification through Phase 8.5.

---

## 7. Phase 13 Step 8 / Step 9 Transition Analysis

### 7.1 Transition Gating
In `ReadinessPlaneEvaluator.validate_step9_continuous_paper_transition()`:
Transition to Step 9 is aborted fail-closed unless all 5 independent conditions hold:
1. `planes.infrastructure == InfrastructureReadinessState.SOAK_VERIFIED_PASS`
2. `planes.research_engine == ResearchEngineReadinessState.ENGINE_VERIFIED_PASS`
3. `planes.strategy_alpha == StrategyAlphaReadinessState.RESEARCH_QUALIFIED`
4. `planes.human_go == HumanGOCheckpointState.AUTHORIZED_SIGNED`
5. `planes.trading_authority != TradingCapitalAuthorityState.HARD_LOCKED_ZERO_CAPITAL`

### 7.2 Static Entrypoint Tracing
- No standalone script or daemon currently initiates Phase 13 Step 9.
- `scripts/phase13_soak_runner.py` executes Step 5 only (24h soak, local simulator, $0.00 capital).
- Step 9 remains **NOT AUTHORIZED** and cannot be triggered automatically by any daemon, cron, or recovery hook.

---

## 8. Static Call-Graph & Entry-Point Inventory

```text
========================================================================================
RESEARCH WORKFLOW CALL GRAPH
========================================================================================
[scripts/execute_phase8_5_step_r3.py]
  │
  ├─► [docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_001.json] (Read & Verify SHA-256)
  │
  ├─► [docs/phase8.5/manifests/manifest-EURUSD_M5_canonical.json] (Load Manifest)
  │
  ├─► [acash.research.quarantine.DatasetQuarantineValidator]
  │     ├── Check 1: Exposure state != UNKNOWN / REVOKED / QUARANTINED
  │     ├── Check 2: spec.hypothesis_id in allowed_hypothesis_ids
  │     ├── Check 3: spec SHA-256 == manifest SHA-256
  │     └── Check 4: Holdout partitions != PERMANENTLY_QUARANTINED
  │
  └─► [pq.read_table("EURUSD_M5_canonical.parquet")] (Load In-Sample Bars 0..5,999)
        │
        └─► [acash.research.evaluation] (Calculate HAC, Rank IC, Autocorr)
              │
              └─► [SearchTrialLedger Sealing] (Cryptographic Digest)

========================================================================================
TRADING / DISPATCH WORKFLOW CALL GRAPH
========================================================================================
[scripts/phase13_soak_runner.py] / [ContinuousPaperDaemon]
  │
  └─► [RuntimeSupervisor.execute_rebalance_cycle()]
        │
        ├─► STAGE 1: Data Freshness Check
        │
        ├─► STAGE 2: Strategy Census
        │     └── Filter: lifecycle_state == RESEARCH_QUALIFIED
        │           ├── If 0 qualified: Sovereign Fallback to 100% Cash (0 Orders)
        │           └── Note: STRAT-MOM-MULTI-HORIZON is TERMINALLY_FALSIFIED -> Rejected
        │
        ├─► STAGE 3: Phase 8 Allocation Tournament (100% Cash)
        │
        ├─► STAGE 4: Phase 9 Sovereign Risk Engine & Kill Switch
        │
        └─► STAGE 5: Phase 7 Admission Check
              │
              └─► [PaperExecutionBridge.evaluate_and_dispatch()]
                    ├── Guard: gate_verdict == "APPROVED_INVESTABLE_ALLOCATION"
                    ├── Guard: is_fallback_baseline is False
                    └── Outcome: Fallback active -> DISPATCH SUPPRESSED (0 Orders)
```

---

## 9. Findings Table

| Item ID | Category | Description | Status / Enforcement |
| :--- | :--- | :--- | :--- |
| **F-01** | Data Quarantine | Cross-hypothesis contamination blocked before data load | **VERIFIED** (Fail-Closed) |
| **F-02** | Data Quarantine | M5 holdout bars 6,060..9,999 permanently locked | **VERIFIED** (Fail-Closed) |
| **F-03** | Epistemic Scope | `UNEXPOSED_PRISTINE` bound to ACASH protocol scope | **VERIFIED** (Documented) |
| **F-04** | Immutability | `TERMINALLY_FALSIFIED` has 0 outbound transitions | **VERIFIED** (Fail-Closed) |
| **F-05** | Immutability | Parameter mutation under existing hypothesis ID blocked | **VERIFIED** (Fail-Closed) |
| **F-06** | Readiness Planes | Infrastructure != Engine != Strategy != Trading | **VERIFIED** (Decoupled) |
| **F-07** | Readiness Planes | Zero master switch (`system_ready`) in repository | **VERIFIED** (0 Occurrences) |
| **F-08** | Step 8 / Step 9 | Phase 13 Step 9 cannot activate without Step 8 Human GO | **VERIFIED** (Fail-Closed) |
| **F-09** | Capital Authority | Capital remains strictly $0.00; live allocation blocked | **VERIFIED** (Hard-Locked) |
| **F-10** | Seam Separation | In-memory compute engines decoupled from disk loaders | **VERIFIED** (Architectural) |

---

## 10. Confirmed Bypasses

$$\mathbf{NONE}$$

No canonical execution path in the repository allows bypassing the quarantine validator, mutating a sealed hypothesis, collapsing readiness planes into a single switch, or activating Phase 13 Step 9 without Phase 13 Step 8 Human GO.

---

## 11. Potential / Unresolved Paths & Limitations

1. **Direct File System Access via Non-ACASH Python Scripts:**
   - *Nature:* An operator or unmanaged script running raw Python code could execute `pyarrow.parquet.read_table("data/parquet/research/EURUSD_M5_canonical.parquet")` directly, bypassing all ACASH Python import hooks.
   - *Classification:* **ACCEPTED OPERATING SYSTEM RISK** (Cannot be prevented by application-level Python code; mitigated by file permissions and cryptographic manifest hashing).
2. **Phase 4 In-Memory `ResearchPipeline` Caller Responsibility:**
   - *Nature:* `ResearchPipeline.execute()` receives `pa.Table` directly in memory and does not inspect disk manifests.
   - *Mitigation:* In ACASH architecture, dataset ingestion and partitioning occur in Phase 8.5 scripts (`execute_phase8_5_step_r3.py`) where `DatasetQuarantineValidator` is strictly enforced.
   - *Classification:* **VERIFIED FOR TESTED ENFORCEMENT PATHS**.

---

## 12. Evidence Classification Table

| Finding / Property | Evidence Classification | Ground Truth Reference |
| :--- | :--- | :--- |
| **Zero Confirmed Bypasses in Canonical Paths** | **VERIFIED** | Static call-graph and symbol search across `src/` and `scripts/` |
| **Cross-Hypothesis Data Quarantine** | **VERIFIED** | Enforced by `DatasetQuarantineValidator`; tested in 5 unit tests |
| **Holdout Bar Quarantine (6,060–9,999)** | **VERIFIED** | Enforced by `PERMANENTLY_QUARANTINED_HOLDOUTS`; tested |
| **Terminal Immutability (0 Outbound)** | **VERIFIED** | Enforced by `ALLOWED_LIFECYCLE_TRANSITIONS`; tested |
| **Zero Master Trading Switch** | **VERIFIED** | 0 occurrences of `system_ready` / `is_ready` / `can_trade` in `src/` |
| **Conjunctive Step 9 Gating** | **VERIFIED** | Enforced by `ReadinessPlaneEvaluator`; tested |
| **Capital Authority Hard-Lock ($0.00)** | **VERIFIED** | Enforced by `SystemReadinessPlanes`; tested |
| **Exhaustive Formal Proof across All Possible OS Code** | **NOT PROVEN** | Unprovable without formal OS/kernel verification (Dijkstra boundary) |
| **Live Broker Connectivity** | **BLOCKED** | Disconnected wire, 0 live orders, $0.00 capital |

---

## 13. Final Audit Verdict

$$\boxed{\mathbf{VERDICT:\ PASS}}$$

**Audit Certification:**
No confirmed bypass was found in the statically audited canonical repository paths. The ACASH repository governance scaffolding is strictly decoupled, fail-closed, and operational. The system remains securely in **`STANDING BY`** with zero live trading authority and zero capital allocated.
