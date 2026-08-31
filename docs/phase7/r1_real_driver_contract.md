# R1-REAL Driver Contract — Broker-Observed Lifecycle & P Evidence Specification

> **Document:** `docs/phase7/r1_real_driver_contract.md`  
> **Status:** PROPOSED / ARCHITECTURAL SPECIFICATION  
> **Authority Contract:** `./broker_adapter_contract.md`, `./execution_state_machine.md`, `./alpaca_bmap.md`  
> **Empirical Basis:** Findings from `INCIDENT-20260831-R1-SYNTHETIC-FILL` (Commit `3dd9f25`)

---

## 0. Executive Summary & Empirical Motivation

On 2026-08-31, the ACASH execution subsystem executed its first live wire order against Alpaca Paper (`46865b08-8da2-4955-9486-ee7ce2ac9cde`). While the HTTP POST submission and subsequent HTTP DELETE cancellation were successfully confirmed by the broker, a critical architectural finding was identified:

$$\boxed{\text{Real Submission } \neq \text{ Real Broker Lifecycle } \neq \text{ Synthetic Event Pump}}$$

### The R1 Synthetic-Fill Flaw:
The initial R1 test harness (`run_order_exercise_verification`) executed a genuine wire submission (`POST /v2/orders`), but subsequently injected **synthetic in-memory trade events** (`harness.acknowledge()` and `harness.full_fill()`) into the `ExecutionCoordinator`. Because the real market was closed, the broker's actual state remained resting at `ACCEPTED` (`filled_qty = 0`), creating an irreconcilable **Reconciliation Parity Failure** between the internal shadow state (`FILLED/1`) and broker reality (`ACCEPTED/0`).

### The R1-REAL Principle:
To produce authentic, audit-grade **Paper Runtime Evidence ($P = 1$)**, the runtime driver must **observe and ingest real broker events exclusively**. Synthetic event generation is strictly confined to unit/conformance testing and is **hard-forbidden in the Paper/Live runtime path**.

---

## 1. Core Architectural Invariants (Non-Negotiable)

1. **Broker as Sole External Observation Authority:** The execution driver shall never fabricate, assume, or simulate trade events, acknowledgments, or fills during live/paper execution.
2. **ExecutionCoordinator as Sole Internal Transition Authority:** The driver is an observation pump only. All canonical state transitions remain strictly governed by `transition_order()` via `ExecutionCoordinator.apply()`.
3. **Zero Synthetic Injections in Runtime Path:** Methods such as `full_fill()`, `acknowledge()`, and `partial_fill()` that construct synthetic `AlpacaTradeEvent` instances are prohibited in the production `run_order_exercise_verification` workflow.
4. **Resting State Awareness:** Orders submitted outside market hours or limit orders resting on the book transition to `SUBMITTED` / `ACKNOWLEDGED` and remain in that state until genuine broker events arrive.
5. **Fail-Closed Timeout & Reconciliation:** If no terminal broker event is observed within the allocated timeout budget, the driver transitions to `CONNECTION_LOST` $\to$ `UNKNOWN` and invokes the 6-dimension Reconciliation Engine. It shall never optimistically declare terminal completion.
6. **Strict BMAP-07 Cancellation Provenance:** Cancellation confirmation must be derived from an authoritative REST snapshot with `cancel_requested_at` provenance, rejecting raw SSE `canceled` ambiguity.
7. **Authentic Economic Attribution:** `average_fill_price`, `realized_slippage_bps`, and execution timestamps must be extracted directly from the broker's actual fill reports (`filled_avg_price`), eliminating hardcoded or placeholder economics.

---

## 2. Dual Observation Architecture (SSE + REST Fallback)

The R1-REAL driver implements a resilient dual-channel observation model:

```text
                     [ ACASH Execution Driver ]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
    [ Channel A: SSE Stream ]        [ Channel B: REST Snapshot ]
    - Primary Observation Path       - Recovery & Reconciliation Path
    - Alpaca Trade Events SSE        - Polling on Interval / Timeout
    - ULID Event Ordering            - Authoritative State Recovery
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                    [ normalize_broker_event() ]
                                 ▼
                    [ ExecutionCoordinator ]
                                 ▼
                       [ transition_order() ]
```

### 2.1 Channel A: Primary SSE Event Stream
- **Source:** Alpaca Trade Events SSE (`/v2/events/trades`).
- **Ingestion:** Streams incoming `AlpacaTradeEvent` records asynchronously or via cursor replay (`since_id`).
- **Ordering:** `broker_sequence` is assigned the verbatim ULID `event_id` (BMAP-03).
- **Deduplication:** Repeated events are deduplicated via `(broker_event_id, broker_sequence)` in `ExecutionCoordinator`.

### 2.2 Channel B: Authoritative REST Snapshot Polling (Fallback & Recovery)
- **Source:** Alpaca REST API (`GET /v2/orders/{broker_order_id}`).
- **Trigger Conditions:**
  1. Stream disconnection, timeout, or silence exceeding $T_{\text{poll}}$ interval.
  2. Terminal verification check prior to final reconciliation report generation.
  3. Post-cancellation resolution per BMAP-07.
- **Ordering:** `broker_sequence` is assigned `LOCAL-FB-*` fallback sequence (BMAP-03/BMAP-08).

---

## 3. Order Lifecycle State Progression Matrix

```text
       ┌────────────────────────┐
       │   OrderIntent (INTENT)  │
       └───────────┬────────────┘
                   │  Real Wire POST /v2/orders
                   ▼
       ┌────────────────────────┐
       │       SUBMITTED        │
       └───────────┬────────────┘
                   │  Broker TradeEvent(ACCEPTED) / REST Status: 'accepted'|'new'
                   ▼
       ┌────────────────────────┐
       │      ACKNOWLEDGED      │ ◄────── Resting State (Market Closed / Limit Order)
       └─────┬────────────┬─────┘
             │            │
  Real Broker Fill        │ Real Broker Cancel / Expire
             │            │
             ▼            ▼
       ┌──────────┐ ┌───────────┐
       │  FILLED  │ │ CANCELLED │
       └────┬─────┘ └─────┬─────┘
            │             │
            └──────┬──────┘
                   ▼
       ┌────────────────────────┐
       │ 6-Dim Reconciliation   │
       │ (REST Snapshot Parity) │
       └───────────┬────────────┘
                   ▼
       ┌────────────────────────┐
       │ P Evidence Certificate │
       └────────────────────────┘
```

---

## 4. Timeout, Abort & Fail-Closed Boundaries

| Event / Failure Mode | Driver Behavior | Resulting State |
| :--- | :--- | :--- |
| **HTTP Submit Timeout (>10s)** | Transport raises `AlpacaTransportTimeoutError` | State transitions to `UNKNOWN`; invokes reconciliation |
| **Stream Silence in ACK State** | Polling initiates at 2.0s intervals up to timeout budget | Remains `ACKNOWLEDGED` if resting; updates if filled |
| **Market Closed at Submit** | Order remains resting on broker | Driver records `ACKNOWLEDGED`, pauses or awaits cancel |
| **Operator Stop / Abort** | Driver issues `DELETE /v2/orders/{id}` | Awaits REST snapshot verification $\to$ `CANCELLED` |
| **Overfill or Negative Price** | `normalize_broker_event()` catches contract violation | Raises `BrokerEventMappingError` fail-closed |

---

## 5. Conjunctive P Evidence Acceptance Standard

A Paper execution run achieves **$P = 1$ (Accepted)** if and only if all four conjuncts evaluate to `TRUE` simultaneously:

$$\boxed{P_{\text{accepted}} \iff \text{TerminalVerified} \land \text{EvidenceLineageComplete} \land \text{ReconciliationVerified} \land \text{NoDispute}}$$

### Conjunct Formal Specifications:

1. **`TerminalVerified`:**
   $$\text{TerminalVerified} \equiv (\text{final\_terminal} == \text{True}) \land (\text{final\_state} \in \{\text{FILLED}, \text{CANCELLED}\}) \land (\text{closed\_at} \neq \text{None})$$

2. **`EvidenceLineageComplete`:**
   $$\text{EvidenceLineageComplete} \equiv (\text{manifest} \neq \text{None}) \land (\text{len}(\text{execution\_digest}) == 64) \land (\text{reconciliation\_report} \neq \text{None}) \land (\text{len}(\text{report\_digest}) == 64) \land (\text{digests match recomputation})$$

3. **`ReconciliationVerified`:**
   $$\text{ReconciliationVerified} \equiv (\text{is\_in_parity} == \text{True}) \land (\text{internal state} \equiv \text{broker snapshot}) \land (\Delta_{\text{qty}} == 0)$$

4. **`NoDispute`:**
   $$\text{NoDispute} \equiv (\text{disputed} == \text{False}) \land (\forall o \in \text{outcomes}, \text{status}(o) == \text{APPLIED})$$

---

## 6. Implementation Strategy & Deliverables

1. **`R1RealOrderExerciseDriver` Class:**
   - Encapsulates `submit_and_observe_lifecycle()` without synthetic pumps.
   - Configurable polling/stream timeout (`timeout_seconds`, `poll_interval_seconds`).
   - Extracts real fill price, fee attribution, and broker execution IDs.
2. **Dedicated Unit & Regression Test Suite:**
   - Injected fake transport asserting that the driver handles async real-like event sequences, stream disconnections, resting timeouts, and snapshot reconciliations without emitting synthetic events.
3. **Execution Runbook Synchronization:**
   - Update `docs/phase7/r1_paper_run_runbook.md` to reference `R1RealOrderExerciseDriver`.
