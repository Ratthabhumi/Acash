# ACASH — Phase 7 Design Proposal & Evolution: Live Execution, Broker Mapping & Paper Validation

**Document:** `docs/phase7/phase_7_proposal.md`  
**Status:** **ACTIVE PHASE PROPOSAL & ARCHITECTURAL EVOLUTION SPECIFICATION**  
**Phase:** Phase 7: Live Execution & Broker Mapping  
**Date:** 2026-08-31  

---

> [!IMPORTANT]
> **Architectural Authority Notice:**  
> This document is a **high-level proposal, architectural narrative, and evolution history** of Phase 7 while it is an active development phase.  
> It is **NOT** a replacement for existing frozen canonical contracts. The canonical authorities remain:
> - [`./architecture.md`](./architecture.md) & [`./execution_state_machine.md`](./execution_state_machine.md) (State Machine & Transition Rules)
> - [`./broker_adapter_contract.md`](./broker_adapter_contract.md) & [`./broker_semantic_mapping.md`](./broker_semantic_mapping.md) (Vendor-Agnostic Translation)
> - [`./alpaca_bmap.md`](./alpaca_bmap.md) (Concrete Alpaca Broker Mapping)
> - [`./paper_exercise_r1.md`](./paper_exercise_r1.md) (R1 Order-Lifecycle Contract & P Evidence Checklist)
> - [`./live_authorization.md`](./live_authorization.md) & [`./reconciliation.md`](./reconciliation.md) (Admission & Reconciliation Invariants)

---

## 1. Phase 7 Objective & Scope

The objective of Phase 7 is to bridge the boundary between **Certified Statistical Research (Phase 6)** and **Real-World Broker Execution (Phase 7)** without introducing epistemic leakage, broker vendor lock-in, or uncontained financial risk.

```
┌────────────────────────────────────────────────────────┐
│      PHASE 6: STATISTICAL GOVERNANCE & VALIDATION      │
│  [ ValidationReport: PASS_TRADEABLE_ALPHA (Read-Only) ]│
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼ (One-Way Lineage Boundary)
┌────────────────────────────────────────────────────────┐
│      PHASE 7: SOVEREIGN EXECUTION & BROKER MAPPING     │
│                                                        │
│  1. Certificate Verification & Risk Admission Gate     │
│  2. Deterministic State Machine (transition_order)     │
│  3. Broker-Agnostic Translation (BrokerAdapter)        │
│  4. Concrete Paper Adapter (Alpaca BMAP)               │
│  5. 6-Dimension Dual-Clock State Reconciliation        │
│  6. Fail-Closed Kill Switch Engine                     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼ (Paper-First Verification)
┌────────────────────────────────────────────────────────┐
│    SANDBOX / PAPER VENUE ONLY (E != P Verification)    │
│            [ ZERO LIVE TRADING BY DEFAULT ]            │
└────────────────────────────────────────────────────────┘
```

### Core Tenets of Phase 7:
1. **The Authorization Invariant:**
   $$\boxed{\text{PASS\_TRADEABLE\_ALPHA} \neq \text{LIVE\_AUTHORIZATION}}$$
   Statistical significance proves only that an alpha model satisfied historical hurdles under the null hypothesis. It confers **zero authority** to risk capital until admitted through operational risk, capacity, drawdown, and kill-switch gates.
2. **Paper-First Empirical Validation:**
   Execution logic must be exhaustively proven in a live Paper environment ($P$) before any live broker routing is unlocked.
3. **No Live Trading by Default:**
   All transports, credentials, and routing configurations default strictly to sandbox/paper endpoints. Live execution paths are hard-locked behind mandatory dual-key operator authorization.

---

## 2. Phase 7 Architectural Principles & Decoupled State Dimensions

Phase 7 maintains strict separation across three orthogonal state dimensions to prevent state conflation:

```
                  ┌─────────────────────────────────────┐
                  │ 1. ORDER LIFECYCLE STATE            │
                  │ (PENDING_SUBMIT -> FILLED / UNKNOWN)│
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────┴──────────────────┐
                  │ 2. OPERATIONAL RESTRICTION STATE    │
                  │ (NORMAL -> RECONCILIATION_HALTED)   │
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────┴──────────────────┐
                  │ 3. EVIDENCE & PROVENANCE STATE      │
                  │ (D -> E -> E* -> P Evidence Lineage)│
                  └─────────────────────────────────────┘
```

### 2.1 State Authority vs. Evidence Authority
- **Single State Authority:** The `transition_order()` function in [`src/acash/execution/state_machine.py`](../../src/acash/execution/state_machine.py) is the **sole authoritative transition engine**. Neither broker adapters, transport layers, nor the Execution Coordinator may mutate or fabricate order states.
- **Evidence Authority:** State transitions require cryptographic lineage. Every terminal state must be backed by a verifiable `ExecutionManifest`, normalized `BrokerRawEvent`, or `ReconciliationReport`.

### 2.2 Operational Restriction Ownership & Separation of Concerns
- **`OperationalRestrictionEngine`:** Owns operational restrictions (`HALT_NEW_ORDERS`, `CANCEL_ALL_INFLIGHT`, `COOLDOWN`).
- **`ExecutionCoordinator != Risk Engine`:** The Coordinator orchestrates the event pipeline; it does **not** evaluate statistical alpha or invent risk policies.
- **`ExecutionCoordinator != Restriction Owner`:** The Coordinator enforces active restrictions emitted by the Risk Engine or Reconciliation Engine; it does **not** arbitrarily clear or override restrictions.

---

## 3. Step 8 Evolutionary Architecture

Phase 7 evolved through a disciplined sequence of sub-specifications and implementations (Step 8):

| Step | Subsystem | Responsibility | Canonical Reference |
| :--- | :--- | :--- | :--- |
| **Step 8A** | **Admission & Authorization** | Pre-execution capital capacity, certificate signature checks, and operational tokens. | [`./live_authorization.md`](./live_authorization.md) |
| **Step 8B** | **Execution State Machine** | Authoritative transition matrix, absorbing terminal states (`FILLED`, `CANCELLED`, `REJECTED`, `EXPIRED`), non-terminal `UNKNOWN` handling. | [`./execution_state_machine.md`](./execution_state_machine.md) |
| **Step 8C** | **Broker Event Normalizer** | Deterministic translation of raw broker payload streams into typed `BrokerEvent` tokens. | [`src/acash/execution/broker_events.py`](../../src/acash/execution/broker_events.py) |
| **Step 8D** | **Mock Broker Substrate** | Fully deterministic in-memory broker simulating race conditions, partial fills, clock skew, and network dropouts. | [`src/acash/execution/mock_broker.py`](../../src/acash/execution/mock_broker.py) |
| **Step 8E** | **Execution Coordinator & Reconciliation** | Orchestrates admission, dispatch, event ingestion, and dual-clock 6-dimension state reconciliation. | [`./reconciliation.md`](./reconciliation.md) • [`src/acash/execution/coordinator.py`](../../src/acash/execution/coordinator.py) |
| **Step 8F** | **Broker Adapter Contract** | Vendor-neutral adapter contract (`IBrokerAdapter`), timeout boundaries, clock skew tolerance ($\le 5.0\text{s}$), credential isolation. | [`./broker_adapter_contract.md`](./broker_adapter_contract.md) |
| **Step 8F-1**| **Broker Semantic Mapping (BMAP)** | 12-item vendor-agnostic mapping framework (Status, Fills, Cancels, Rejections, Replay, Disconnects). | [`./broker_semantic_mapping.md`](./broker_semantic_mapping.md) |
| **Step 8F-2**| **Alpaca Paper Transport** | `PaperHttpAlpacaTransport` enforcing `paper-api.alpaca.markets/v2` URL pinning and header authentication. | [`src/acash/execution/alpaca/transport.py`](../../src/acash/execution/alpaca/transport.py) |
| **Step 8F-3**| **Alpaca Paper Adapter** | Concrete `AlpacaPaperAdapter` implementing Alpaca BMAP translation. | [`src/acash/execution/alpaca/adapter.py`](../../src/acash/execution/alpaca/adapter.py) |
| **R0** | **Read-Only Connectivity Exercise** | Verification of credentialed account inspection, balance queries, and read-only reconciliation readiness. | [`src/acash/execution/alpaca/paper_exercise.py`](../../src/acash/execution/alpaca/paper_exercise.py) |
| **R1** | **Order Lifecycle Exercise** | Automated single-order lifecycle verification (`SUBMIT` $\to$ `ACK` $\to$ `FILL`/`CANCEL` $\to$ `RECONCILE`). | [`./paper_exercise_r1.md`](./paper_exercise_r1.md) • [`./r1_paper_run_runbook.md`](./r1_paper_run_runbook.md) |

---

## 4. Evidence Classification Model ($\text{Unit Tests} \neq E \neq P$)

To eliminate unverified claims, Phase 7 establishes three orthogonal dimensions of verification:

```
  [ Local Unit Tests ]    ──► 588 tests passing (Automated Invariants & Regression Safety)
             │
  [ D: Design-Conformant ]──► Architecture & Contract Spec matches schema
             │
             ▼
  [ E: Broker Semantic ]  ──► Independently verified against official vendor API docs / schemas
             │
             ▼
  [ E*: Partially Bounded]──► Verified with known edge-case caveats (e.g. BMAP-11 SSE replay)
             │
             ▼
  [ P: Empirically Proven]──► Executed & verified in live Paper environment with complete lineage
```

$$\boxed{\text{588 Unit Tests} \neq E \text{ (Broker Semantic Review)} \neq P \text{ (Empirical Paper Execution)}}$$

- **`Local Unit Tests`:** Continuous integration and regression suite proving internal code execution and contract invariants (588 tests).
- **`D` (Design):** The logic is specified and mathematically consistent on paper.
- **`E` (Broker Semantic Review):** The broker API behavior is verified against authoritative vendor documentation and synthetic contract tests (`BMAP 01–10 = E`, `BMAP 11 = E*`, `BMAP 12 = D`).
- **`E*` (Partially Bounded):** Bounded behavior where vendor API has documented limitations (e.g. Alpaca SSE replay gaps).
- **`P` (Paper Proven):** A real order was dispatched to the broker's sandbox/paper environment, transitioned through the live state machine, and reconciled against actual broker fills with complete cryptographic logs ($P = 0$).

> **Non-Negotiable Rule:** Unit test execution and items marked **`E`** CANNOT be promoted to **`P`** without real runtime execution logs and reconciliation certificates.

---

## 5. Alpaca Concrete Integration & BMAP Subordination

Phase 7 implements Alpaca Paper Trading as its first concrete broker target under strict subordination rules:

```text
Alpaca SSE (trade_updates) / REST (/v2/orders)
                    │
                    ▼
       [ AlpacaPaperAdapter ]              <-- Translator ONLY (Zero State Authority)
                    │
                    ▼
             BrokerRawEvent                <-- Canonical Ingestion Token
                    │
                    ▼
        normalize_broker_event()           <-- Step 8C Deterministic Normalizer
                    │
                    ▼
           transition_order()              <-- Step 8B Sole State Authority
```

### 5.1 Subordination Invariants:
1. **BMAP is Subordinate to ACASH:** ACASH canonical domain models will **never** be distorted to accommodate broker API quirks. The adapter is strictly a bidirectional translator.
2. **`HTTP 200/204 != Execution State`:**
   - A REST `POST /v2/orders` response (`200 OK`) is a `SubmissionReceipt`, **never** a `FILLED` state.
   - A REST `DELETE /v2/orders/{id}` response (`204 No Content`) is a `CancelRequestedReceipt`, **never** a `CANCELLED` state.
3. **BMAP-07 Strict Fail-Closed Cancellation:**
   - If a cancellation request fails or is rejected by Alpaca (`order_cancel_rejected`), the order remains **`SUBMITTED` / `IN_FLIGHT`** until terminal confirmation arrives via SSE `trade_updates` or REST snapshot reconciliation.
4. **Paper-Only Credential Boundary:**
   - The transport layer binds strictly to `ALPACA_PAPER` (`https://paper-api.alpaca.markets/v2`). Any credential payload indicating live production endpoints raises `DataContractError` immediately.

---

## 6. Paper Validation Framework & P Evidence Acceptance

### 6.1 R0 vs. R1 Scope
- **R0 (Read-Only Harness):** Exercises non-mutating endpoints (`GET /v2/account`, `GET /v2/positions`). Proves connectivity and credential validity only. It confers **zero P evidence** for order execution.
- **R1 (Order-Lifecycle Harness):** Exercises active order creation, tracking, terminal transition, and post-trade ledger reconciliation.

### 6.2 The P Evidence Acceptance Invariant
To flip any BMAP Conformance Matrix cell from **`D/E`** to **`P`**, the execution run must satisfy all four conditions simultaneously:

$$\boxed{P_{\text{accepted}} \iff \text{TerminalVerified} \land \text{EvidenceLineageComplete} \land \text{ReconciliationVerified} \land \text{NoDispute}}$$

1. **`TerminalVerified`:** Order reached an absorbing terminal state (`FILLED` or `CANCELLED`) authorized by `transition_order()`.
2. **`EvidenceLineageComplete`:** Full cryptographic lineage chain exists (`OrderIntent` $\to$ `ExecutionManifest` $\to$ `BrokerRawEvent` $\to$ `ReconciliationReport`).
3. **`ReconciliationVerified`:** Broker REST snapshot matches ACASH internal accounting within exact tolerance ($|\Delta_{\text{qty}}| = 0, |\Delta_{\text{price}}| \le 10^{-10}$).
4. **`NoDispute`:** Zero unhandled errors, zero clock-skew violations ($> 5.0\text{s}$), and zero state machine rejections.

---

## 7. Current Implementation Status (Actual Repository State)

As of git commit **[`61233ad`](https://github.com/Ratthabhumi/Acash/commit/61233ad)** on branch `main`:

| Subsystem Component | Implementation State | Verification Level | Test Suite |
| :--- | :--- | :--- | :--- |
| **Admission & Authorization Gate** | Complete (`admission.py`) | **Tested (Invariant)** | `tests/unit/execution/test_phase7_contracts.py` |
| **Execution State Machine** | Complete (`state_machine.py`) | **Tested (State Space)** | `tests/unit/execution/test_execution_state_machine.py` |
| **Broker Event Normalizer** | Complete (`broker_events.py`) | **Tested (Mapping)** | `tests/unit/execution/test_broker_event_normalizer.py` |
| **Mock Broker & Pipeline** | Complete (`mock_broker.py`) | **Tested (Substrate)** | `tests/unit/execution/test_execution_pipeline.py` |
| **Execution Coordinator** | Complete (`coordinator.py`) | **Tested (Reconciliation)** | `tests/unit/execution/test_execution_coordinator.py` |
| **Broker Adapter Contract** | Complete (`broker_adapter.py`) | **Tested (Interface)** | `tests/unit/execution/test_broker_adapter.py` |
| **Alpaca Paper Transport** | Complete (`transport.py`) | **Tested (Guard)** | `tests/unit/execution/test_alpaca_transport.py` |
| **Alpaca Paper Adapter** | Complete (`adapter.py`) | **BMAP E-Reviewed** | `tests/unit/execution/test_alpaca_paper_adapter_bmap.py` |
| **R0 Read-Only Harness** | Complete (`paper_exercise.py`) | **Tested (Read-Only)** | `tests/unit/execution/test_alpaca_paper_exercise.py` |
| **R1 Order Exercise Harness**| Complete (`order_exercise.py`) | **Tested (Lifecycle Wire)** | `tests/unit/execution/test_alpaca_order_exercise.py` |
| **R1 Defect Fixes** | Committed (`4a92348`, `8e92188`) | **Tested (Defect Guard)**| Connect-before-submit & Paper transport guard |
| **Local Credential Vault** | Complete (`scripts/`) | **Tested (DPAPI)** | `tests/unit/execution/test_paper_launcher.py` |
| **Empirical Paper Execution** | **NOT RUN** | **$P = 0$** | Pending authorized single paper run |
| **Live Production Trading** | **HARD LOCKED (OFF)** | **N/A** | Out of Phase 7 scope |

---

## 8. Current Blocker & Next Checkpoint

### 8.1 Active Operational Blocker:
1. **Operator Environment Credentials Visibility:**  
   Operator-exported Alpaca Paper credentials (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`) must be active in the execution shell environment before triggering preflight.
2. **Mandatory Human Preflight Authorization:**  
   The R1 Paper run is gated on a green, verified preflight check (`ALPACA_PAPER` endpoint, valid credentials, read-only session verified).

### 8.2 Approved Run Parameters (Single Isolated Paper Order):
- **Symbol:** `SPY`
- **Quantity:** `1` share (Market Order / Day)
- **Client Order ID:** `acash-r1-paper-20260831-001`
- **Safety Mode:** Paper Sandbox Mode (`https://paper-api.alpaca.markets/v2`)
- **Runbook Authority:** [`./r1_paper_run_runbook.md`](./r1_paper_run_runbook.md)

---

## 9. Canonical Phase 7 Documentation Index

All active Phase 7 specifications and runbooks are maintained within [`docs/phase7/`](./):

- **[`docs/phase7/CONTEXT_MAP.md`](./CONTEXT_MAP.md)**: Master Phase 7 navigation context map and core invariants.
- **[`docs/phase7/architecture.md`](./architecture.md)**: End-to-end execution dataflow, risk admission, and state boundaries.
- **[`docs/phase7/broker_adapter_contract.md`](./broker_adapter_contract.md)**: Sovereign vendor-neutral broker adapter contract.
- **[`docs/phase7/broker_semantic_mapping.md`](./broker_semantic_mapping.md)**: Vendor-agnostic 12-item semantic mapping framework.
- **[`docs/phase7/alpaca_bmap.md`](./alpaca_bmap.md)**: Concrete Alpaca Broker Semantic Mapping (BMAP).
- **[`docs/phase7/execution_state_machine.md`](./execution_state_machine.md)**: Authoritative order and fill state transition matrix.
- **[`docs/phase7/paper_exercise_r1.md`](./paper_exercise_r1.md)**: R1 order-lifecycle contract & P evidence checklist.
- **[`docs/phase7/r1_paper_run_runbook.md`](./r1_paper_run_runbook.md)**: Operator runbook for the R1 single paper order exercise.
- **[`docs/phase7/reconciliation.md`](./reconciliation.md)**: Dual-clock 6-dimension internal vs. broker state reconciliation.
- **[`docs/phase7/risk_state.md`](./risk_state.md)**: Dynamic risk monitoring, limit headroom, and state transitions.
- **[`docs/phase7/kill_switch.md`](./kill_switch.md)**: Automated fail-closed kill switch triggers and procedures.
- **[`docs/phase7/live_authorization.md`](./live_authorization.md)**: Pre-live risk admission and operational authorization tokens.
- **[`docs/phase7/certificate.md`](./certificate.md)**: Validation certificate ingestion and cryptographic verification.
- **[`docs/phase7/execution_manifest.md`](./execution_manifest.md)**: Execution manifest schema and execution drag attribution.
- **[`docs/phase7/order_lifecycle.md`](./order_lifecycle.md)**: High-level order intent and fill lifecycle overview.
