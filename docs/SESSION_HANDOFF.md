# ACASH — Session Handoff
## Phase 13 Slice 1: Gate A Pre-Live Certification — Layer B Workstation Handoff

> **Document:** `docs/SESSION_HANDOFF.md`
> **Status:** PHASE 13 SLICE 1 IN PROGRESS — LAYER A PASSED (11/11); LAYER B HARNESS REFACTORED (`2f01841`); READY FOR LIVE MT5 DEMO REHEARSAL AT WORK
> **Current Head Commit:** `2f01841` (Enforce authentic 6-D recon, exact lineage, and broker-derived flat portfolio in Layer B harness)
> **Operating Environment:** Windows 10/11 x64, Python 3.14.3/3.14.6 (`.venv`), MetaTrader 5 Desktop Terminal (Demo Only)
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Implementation Correctness $\neq$ Mathematical Validity)
> **Date:** 2026-09-04

---

## 1. Immutable Frozen Baselines & Progression

- **Phase 7 (Live Execution Reality):** `FROZEN`
- **Phase 8 (Portfolio Allocation & Tournament):** `FROZEN` (`e6f1d04`)
- **Phase 8.5 (Alpha Research & Economic Evidence):** `FROZEN` (`9ce1365`)
- **Phase 9 (Deterministic Risk Engine & Kill Switch):** `FROZEN` (`6bd40d8`)
- **Phase 10 (Runtime Orchestration & Continuous Paper Operations):** `FROZEN` (`3955bf6`)
- **Phase 11 (Strategy Forward Drift & Execution Reality Attribution):** `FROZEN` (`092a2b1`)
- **Phase 12 (MT5 & Venue Execution Adapters):** `FROZEN` (`1e1d154`, Closeout Report: `docs/phase12/closeout_report.md`)
- **Phase 13 (Live Small Capital Deployment):**
  - **Slice 1 (Gate A Pre-Live Certification):** `IN PROGRESS`
    - Layer A (Automated Pytest Suite): `✅ 11/11 PASSED` (Audited & Approved)
    - Layer B (Operational Demo Terminal Rehearsal): `🟡 IN PROGRESS` (Harness refactored @ `2f01841`; Preflight passed; Pending execution of A-3, A-10, A-11)
  - **Gate A Certification Status:** `🔒 NOT CERTIFIED` (Pending Layer B evidence)
  - **Gate B Authorization Status:** `🚫 STRICTLY LOCKED`
  - **Live Capital Authority:** `🔒 $0.00` (Strict Frozen Invariant)
  - **Production Codebase (`src/`):** `🔒 STRICTLY FROZEN` (Zero edits permitted)

---

## 2. Phase 12 Slice 6 — Freeze & Exit Gate (Reference)

Phase 12 is officially closed and frozen at `1e1d154`. Full inventory is documented in `docs/phase12/closeout_report.md`.
Baseline regression: 1240 passed (1158 unit + 82 integration).

---

## 3. Frozen Contract Inventory (Critical Boundary)

| Contract | Frozen Invariant |
|----------|-----------------|
| State Machine Authority | `transition_order()` in `state_machine.py` — sole authority |
| Coordinator Authority | `ExecutionCoordinator` — sole shadow-state owner |
| Gate 6 Routing Key | `c.intent_id` exclusively; `c.execution_id` strictly FORBIDDEN |
| Dispatch Gate | `can_dispatch() == True` iff `READY AND is_reconciled` |
| UNKNOWN Semantics | Non-absorbing; blocks dispatch; resolved by RECON only |
| ACK ≠ FILLED | retcode 10009 → ACK; FILLED requires `MT5DealReality` evidence |
| BLOCKED State | Absorbing; requires operator intervention |
| Live Capital | $0.00; no live credential path exists in codebase |
| Admission Gate | All 5 conditions required (risk/calc/restriction/auth/venue) |

---

## 4. Deferred Backlog

| Item | Reason for Deferral | Priority |
|------|---------------------|----------|
| **TradingView Ingress Gateway** | Signal ingress concern, not execution authority. | Post-Gate B |
| **Phase-B Transactional Mutation** | Sequential apply is P1 debt acknowledged in Slice 5 Plan Rev5. | Post-Phase 13 |

---

## 5. Phase 13 Slice 1 Architecture & Gate A Two-Layer Model

Phase 13 Slice 1 establishes **Gate A: Pre-Live Certification** across two distinct layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      GATE A: TWO-LAYER MODEL                           │
├──────────────────────────────────┬─────────────────────────────────────┤
│  LAYER A: Automated Pytest       │  LAYER B: Operational Demo Terminal │
│  - MockMT5Transport & simulation │  - Real MetaTrader 5 Desktop GUI    │
│  - 11/11 tests passing           │  - Operator-assisted harness        │
│  - Cryptographic & logic gates   │  - Real MT5 Demo account (0) only   │
│  - Status: ✅ 11/11 PASSED        │  - Status: 🟡 IN PROGRESS           │
└──────────────────────────────────┴─────────────────────────────────────┘
```

---

## 6. Audit Verdict on Initial Harness (`4d367af`) & Remediation (`2f01841`)

The human auditor rejected commit `4d367af` for Layer B certification due to P0 integrity gaps:
1. **A-11 P0 Gap:** Previously did not execute real 6-D RECON post-manual close; did not prove `UNTRACKED_TRADE_DEAL` / `MISSING_POSITION`; did not prove adapter transitioned to `BLOCKED`; did not simulate process restart; created synthetic `flat_portfolio` in memory to bypass tracker.
2. **A-3 Gap:** Used placeholder `"0" * 64` digests instead of authentic SHA-256; `intent_id` lineage mismatched.
3. **Preflight Gap:** Checked `volume_min <= 0.01` instead of exact micro-lot contract (`volume_min == 0.01` and `volume_step == 0.01`).
4. **A-10 Gap:** Required authentic SHA-256 artifact hashing on recorded human SLA evidence.

### Remediation Implemented in Commit `2f01841`:
- **Production `src/` FROZEN:** Zero lines of code modified in `src/`.
- **Preflight:** Enforces `spec.volume_min == Decimal("0.01")` and `spec.volume_step == Decimal("0.01")`. Detects MT5 GUI Algo Trading button status. Written to `docs/phase13/layer_b_evidence_preflight.json` (SHA-256: `6e95c750...`).
- **A-3 Exact Lineage & Real RECON:** Computes authentic SHA-256 digests via `compute_payload_digest()`. Lineage matches dispatch `intent_id` (`INT_DEMO_A3_<timestamp>`) to broker deal. Runs real 6-D RECON.
- **A-10 SLA Timing:** Interactive `input()` records operator reaction time ($\le 900$s SLA) and hashes artifact with SHA-256.
- **A-11 Full E2E Recovery Lifecycle:**
  - **Zero automated close commands:** Prompt instructs human operator to close position via MT5 GUI.
  - **Real Post-Close 6-D RECON:** Detects `MISSING_POSITION` & `UNTRACKED_TRADE_DEAL`. Calls `adapter.mark_blocked()`; asserts `adapter.safety_state == BLOCKED` and `can_dispatch() == False`.
  - **Simulated Restart:** Instantiates `restarted_adapter`. Captures fresh broker reality, confirms 0 open positions. Synchronizes shadow deals, runs fresh 6-D RECON clean (`report_flat.is_clean == True`), confirms adapter reconciled (`can_dispatch() == True`).
  - **Broker-Derived Flat Portfolio:** Calls `derive_portfolio_from_broker(broker_snap_flat)` to derive `PortfolioState` directly from broker reality. Passes to `EmergencyFlattenTracker`, verifying `FLATTEN_COMPLETED`.
  - Hashed evidence written to `docs/phase13/layer_b_evidence_a11.json`.

---

## 7. Workstation Handoff Runbook: Step-by-Step Execution at Work

Follow these exact steps when resuming work on your work computer:

### Step 1: Environment & Repository Sync
```powershell
# 1. Pull latest commit from origin/main
git pull origin main

# 2. Verify HEAD is 2f01841 or later
git log -1 --oneline

# 3. Ensure virtual environment is up to date
uv sync

# 4. Ensure MetaTrader 5 Python library is present on Windows x64
uv pip install metatrader5==5.0.6162

# 5. Verify static types & regression test suite
uv run mypy scripts/phase13_layer_b_harness.py
uv run pytest tests/integration/test_phase13_slice1_gate_a.py
```

### Step 2: MetaTrader 5 Terminal Preparation
1. Launch the **MetaTrader 5 Desktop Terminal** on your work computer.
2. Login to your **Demo Account** (Account `trade_mode` must be `0`).
   - *Strict Fail-Closed:* Connecting a live account (`trade_mode == 2`) will immediately trigger an uncatchable fatal halt.
3. Ensure the symbol **`EURUSD`** is visible in Market Watch and supports 0.01 micro-lots (`volume_min=0.01`, `volume_step=0.01`).
4. **Enable Algo Trading:** Click the **"Algo Trading"** button on the MT5 top toolbar so that the icon turns green. (If disabled, MT5 rejects Python orders with retcode 10027).

---

### Step 3: Layer B Interactive Execution Sequence

Execute the rehearsal procedures in the following strict sequential order:

#### 3.1 Preflight Demarcation Audit
```powershell
uv run python scripts/phase13_layer_b_harness.py --mode preflight
```
- **Expected Outcome:** Terminal connected, Account trade_mode=0 (DEMO), EURUSD micro-lot spec verified.
- **Artifact Generated:** `docs/phase13/layer_b_evidence_preflight.json`.

#### 3.2 Procedure A-3: MT5 Demo Order & Real 6-D RECON
```powershell
uv run python scripts/phase13_layer_b_harness.py --mode a3
```
- **Operator Action:** The harness will display order details (BUY 0.01 EURUSD) and prompt:
  ```text
  Confirm order submission to Demo Terminal? (type 'YES' to proceed):
  ```
  Type `YES` and press ENTER.
- **Expected Outcome:** Retcode 10009 (`DONE`), Order & Deal tickets captured, authentic digests computed, 6-D RECON returns `CLEAN` (`is_clean == True`).
- **Artifact Generated:** `docs/phase13/layer_b_evidence_a3.json`.

#### 3.3 Procedure A-10: Degraded Warning & Human SLA Rehearsal
```powershell
uv run python scripts/phase13_layer_b_harness.py --mode a10
```
- **Operator Action:** The console displays a structured `STRATEGY_DEGRADED` warning alert with timestamp.
- Press **ENTER** immediately to acknowledge the alert.
- **Expected Outcome:** Measures elapsed time, confirms `elapsed_seconds <= 900.0` (SLA PASS).
- **Artifact Generated:** `docs/phase13/layer_b_evidence_a10.json`.

#### 3.4 Procedure A-11: Emergency Manual Close & 6-D Discrepancy Recovery
```powershell
uv run python scripts/phase13_layer_b_harness.py --mode a11
```
- **Workflow & Operator Actions:**
  1. Harness identifies (or opens) an open EURUSD 0.01 position and verifies baseline clean state.
  2. Trips Sovereign Kill Switch; verifies automated execution dispatch is blocked.
  3. **MANDATORY HUMAN OPERATOR ACTION:** The harness pauses and displays:
     ```text
     ------------------------------------------------------------
       🚨 MANDATORY OPERATOR ACTION REQUIRED
     ------------------------------------------------------------
     1. Switch to your MetaTrader 5 Desktop Terminal window.
     2. In the 'Trade' tab at the bottom, locate Position Ticket #<TICKET>.
     3. Right-click the position and click 'Close Position' (or click 'X').
     4. Confirm the position has disappeared from the Trade tab.
     ------------------------------------------------------------
     👉 Once you have MANUALLY closed the position in MT5 GUI, press ENTER...
     ```
  4. Switch to the MT5 window, manually close the position in GUI, return to console, and press **ENTER**.
  5. Harness executes real 6-D RECON post-close $\to$ detects `MISSING_POSITION` & `UNTRACKED_TRADE_DEAL` $\to$ verifies adapter transitions to `BLOCKED`.
  6. Simulates clean restart $\to$ confirms broker is flat $\to$ synchronizes shadow ledger $\to$ runs fresh 6-D RECON clean $\to$ adapter confirmed reconciled.
  7. Derives flat `PortfolioState` directly from broker reality $\to$ `EmergencyFlattenTracker` confirms `FLATTEN_COMPLETED`.
- **Artifact Generated:** `docs/phase13/layer_b_evidence_a11.json`.

---

### Step 4: Evidence Pack Compilation & Gate A Certification

Once all three evidence JSON files are generated:
1. Verify evidence files exist and inspect their contents:
   - `docs/phase13/layer_b_evidence_preflight.json`
   - `docs/phase13/layer_b_evidence_a3.json`
   - `docs/phase13/layer_b_evidence_a10.json`
   - `docs/phase13/layer_b_evidence_a11.json`
2. Update `docs/phase13/gate_a_evidence_pack.md` to transition Layer B items from `PENDING` to `PASS` with the authentic SHA-256 hashes.
3. Commit and push the evidence to `origin/main`:
   ```powershell
   git add docs/phase13/layer_b_evidence_*.json docs/phase13/gate_a_evidence_pack.md
   git commit -m "docs(phase13): record authentic Layer B rehearsal evidence for A-3, A-10, A-11"
   git push origin main
   ```
4. **STOP AND WAIT:** Present the complete evidence pack to the user/auditor for formal Gate A certification.
   - **DO NOT proceed to Gate B.**
   - **Live capital remains strictly $0.00 until explicit human authorization.**

---

## 8. Verification Ledger (Current Handoff State)

```markdown
### Verification Ledger
- Implementation Status: COMPLETE (Layer B Rehearsal Harness Refactored to Strict Fail-Closed Standard)
- Contract Enforcement: STRICT FAIL-CLOSED (Preflight contract equality, exact lineage, zero synthetic portfolios, authentic digests)
- Mathematical Authority: CANONICAL SPEC (MT5ReconciliationEngine 6-D spec, SHA-256 digest validation, EmergencyFlattenTracker)
- Local Test Suite: VERIFIED (11/11 Layer A passed, 1251 full suite passed, preflight live probe passed)
- Type Checker (MyPy): VERIFIED (264 source files in src/ + tests/ clean, harness clean)
- Production Codebase (src/): STRICTLY FROZEN (Zero edits)
- Gate A Status: 🟡 IN PROGRESS / NOT CERTIFIED (Harness ready, awaiting operator execution of A-3, A-10, A-11)
- Gate B Status: 🚫 STRICTLY LOCKED
- Live Capital Authority: 🔒 $0.00 (Strict Invariant)
```



