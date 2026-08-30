# Phase 7 Step 8: Execution State Machine Contract

> **Status: DESIGN FOR APPROVAL — no implementation yet.**
> This document formalizes the order execution state machine contract that the
> Execution State Machine engine MUST implement. It is the single authoritative
> transition authority for a submitted `OrderIntent`. Approval of this contract is
> a prerequisite before any `mock`/`real` broker adapter is implemented.

---

## 1. Scope & Chain Invariant

The contract enforces the fail-closed end-to-end chain:

$$\boxed{ Authorization \rightarrow OrderIntent \rightarrow BrokerSubmission \rightarrow Ack/Reject \rightarrow Fill/Unknown }$$

States are governed by the existing `acash.execution.schema.OrderLifecycleState` enum:

```
INTENT, SUBMITTED, CANCEL_REQUESTED, ACKNOWLEDGED,
PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED, EXPIRED, UNKNOWN
```

This document defines **who may transition a state, under which source state, by
which event, and to which target state**, with strict fail-closed semantics and a
single canonical transition authority.

---

## 2. Core Design Invariants (Non-Negotiable)

1. **State-only mutation**: The only way a `OrderLifecycleState` changes is through
   the transition authority (the Execution State Machine engine). No path mutates
   an order's lifecycle state in-place outside the authority.
2. **First-class `UNKNOWN`**: `UNKNOWN` is a fully populated lifecycle state, NOT an
   error or an on-the-fly fallback. Any connectivity loss or verification timeout
   transitions the order to `UNKNOWN` — it is NEVER silently coerced to `CANCELLED`,
   `FILLED`, or any other state on ambiguous network conditions.
3. **`CANCEL_REQUESTED → UNKNOWN` on connectivity loss**:
   - `CANCEL_REQUESTED + BrokerConfirmation` → `CANCELLED` (legitimate).
   - `CANCEL_REQUESTED + ConnectionLost/Timeout` → `UNKNOWN` (fail-closed).
   - There is **NO** acceptable `CANCEL_REQUESTED → CANCELLED` shortcut that bypasses
     an authoritative broker confirmation.
4. **`UNKNOWN` blocks all further action until reconciliation**:
   - From `UNKNOWN`, the ONLY legal transitions are:
     - `UNKNOWN + ReconciliationVerify` → **symmetric reconciliation to the verified
       terminal state** (`FILLED`, `CANCELLED`, `REJECTED`, `EXPIRED`), OR
     - `UNKNOWN + ReconciliationDispute` → stays `UNKNOWN` + raises incident (loop).
   - While `UNKNOWN`, the strategy shadow-mode is `RESTRICTED`; no new order intents
     are admitted (per `risk_state` NORMAL/RESTRICTED invariant).
5. **Terminal states are absorbing**: `FILLED`, `CANCELLED`, `REJECTED`, `EXPIRED`
   are terminal. No event may transition OUT of a terminal state. This is enforced
   fail-closed (raise `PreLiveRiskAdmissionError` / a dedicated `ExecutionStateError`).
6. **Single canonical source of truth**: Every state in this machine is derived from
   a single authoritative transition table (Section 4). There is ONE transition
   function; no dual/parallel state machines may drift.

---

## 3. Events

An **event** is the atomic input that causes a state transition. Event names are
aligned to broker adapter semantics and reconciliation.

| Event | Meaning |
| :--- | :--- |
| `SUBMIT` | Order packet handed to broker transport (intent → submission). |
| `ACK` | Broker acknowledged working order. |
| `REJECT` | Broker rejected order (authoritative terminal rejection). |
| `PARTIAL_FILL` | Broker reported a partial fill. |
| `FILL` | Broker reported complete fill (cumulative = requested). |
| `CANCEL_REQUEST` | Local operator/strategy requests cancellation. |
| `CANCEL_ACK` | Broker confirms order removed from book (authoritative cancel). |
| `CANCEL_REJECT` | Broker declined the cancel request. |
| `EXPIRY` | Order expired per broker/`TimeInForce`. |
| `CONNECTION_LOST` | Gateway/transport connectivity lost or response timeout. |
| `RECONCILE` | Reconciliation engine has an authoritative broker status report. |

Note: `CONNECTION_LOST` is a **pseudo-event** — it does not originate from the broker;
it originates from connectivity monitoring, and it is the sole path that places an
order into `UNKNOWN`.

---

## 4. Authoritative Transition Table

Rows read: **Source State** × **Event** → **Target State**. Any (source, event) pair
NOT listed is **invalid** and MUST raise fail-closed (no silent no-op, no implicit
coercion).

| # | Source | Event | Target | Notes |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `INTENT` | `SUBMIT` | `SUBMITTED` | packet left socket, awaiting ack |
| 2 | `SUBMITTED` | `ACK` | `ACKNOWLEDGED` | working order |
| 3 | `SUBMITTED` | `REJECT` | `REJECTED` | terminal — authoritative reject |
| 4 | `SUBMITTED` | `CONNECTION_LOST` | `UNKNOWN` | ambiguous post-submit state |
| 5 | `ACKNOWLEDGED` | `PARTIAL_FILL` | `PARTIALLY_FILLED` | residual still working |
| 6 | `ACKNOWLEDGED` | `FILL` | `FILLED` | terminal |
| 7 | `ACKNOWLEDGED` | `CANCEL_REQUEST` | `CANCEL_REQUESTED` | operator-initiated |
| 8 | `ACKNOWLEDGED` | `REJECT` | `REJECTED` | terminal (broker deems order invalid) |
| 9 | `ACKNOWLEDGED` | `EXPIRY` | `EXPIRED` | terminal |
| 10 | `ACKNOWLEDGED` | `CONNECTION_LOST` | `UNKNOWN` | ambiguous working state |
| 11 | `PARTIALLY_FILLED` | `PARTIAL_FILL` | `PARTIALLY_FILLED` | cumulative still < requested |
| 12 | `PARTIALLY_FILLED` | `FILL` | `FILLED` | terminal — cumulative = requested |
| 13 | `PARTIALLY_FILLED` | `CANCEL_REQUEST` | `CANCEL_REQUESTED` | cancel residual |
| 14 | `PARTIALLY_FILLED` | `EXPIRY` | `EXPIRED` | terminal |
| 15 | `PARTIALLY_FILLED` | `CONNECTION_LOST` | `UNKNOWN` | ambiguous residual |
| 16 | `CANCEL_REQUESTED` | `CANCEL_ACK` | `CANCELLED` | terminal — legitimate cancel |
| 17 | `CANCEL_REQUESTED` | `CANCEL_REJECT` | `ACKNOWLEDGED` | cancel declined, order still working |
| 18 | `CANCEL_REQUESTED` | `FILL` | `FILLED` | terminal — fill raced cancel; fill is authoritative |
| 19 | `CANCEL_REQUESTED` | `CONNECTION_LOST` | `UNKNOWN` | **first-class**: cannot confirm cancel on lost connectivity |
| 20 | `CANCEL_REQUESTED` | `RECONCILE` | `UNKNOWN` | reconcile is never a blind `CANCELLED` assertion |
| 21 | `UNKNOWN` | `RECONCILE` | `FILLED` | reconciliation verified authoritative fill |
| 22 | `UNKNOWN` | `RECONCILE` | `CANCELLED` | reconciliation verified authoritative cancel |
| 23 | `UNKNOWN` | `RECONCILE` | `REJECTED` | reconciliation verified authoritative reject |
| 24 | `UNKNOWN` | `RECONCILE` | `EXPIRED` | reconciliation verified authoritative expiry |
| 25 | `UNKNOWN` | `CONNECTION_LOST` | `UNKNOWN` | remains unknown; incident raised |

---

## 5. Fail-Closed Semantics

### 5.1 Invalid Transitions
Any (source, event) pair not in Section 4 raises a fail-closed error. Examples that
MUST fail:
- `INTENT` + `FILL` (cannot be filled before submission)
- `SUBMITTED` + `CANCEL_REQUEST` (cannot cancel before ack — use broker cancel flow)
- `FILLED` + anything (terminal — absorbing)
- `CANCELLED` + anything (terminal — absorbing)
- `REJECTED` + anything (terminal — absorbing)
- `EXPIRED` + anything (terminal — absorbing)

### 5.2 Terminal Absorbing Rule
Once a state in `{FILLED, CANCELLED, REJECTED, EXPIRED}` is reached, NO event can
change the state. The transition authority raises fail-closed rather than mutate.

### 5.3 The `UNKNOWN` No-Shortcut Rule
From `CANCEL_REQUESTED`, the order MAY NOT be marked `CANCELLED` unless the broker
confirms (`CANCEL_ACK`) or reconciliation authoritatively verifies the cancel
(`RECONCILE` → `CANCELLED`). On `CONNECTION_LOST`, the order MUST go to `UNKNOWN`.
This prevents unfilled-position accounting drift and phantom cancel confirmation.

---

## 6. Reconciliation Coupling

`UNKNOWN` is never resolved by the executing state machine alone. It requires the
**Reconciliation Engine** (see `docs/phase7/reconciliation.md`) to supply an
authoritative broker status, delivered back as a `RECONCILE` event carrying the
verified terminal state. Until then the order remains `UNKNOWN` and the strategy
stays `RESTRICTED`.

---

## 7. Execution Deadline & Staleness Bound

A submission is declared `CONNECTION_LOST` when no `ACK`/`REJECT` is received within
the configured **acknowledgement deadline** (default e.g. `2000ms`, configurable).
A working order is likewise subject to the order-staleness watchdog. These deadlines
are explicit, configurable constants — never silent magic floors.

---

## 8. Adoption Impact (What Implementation MUST Provide)

1. A single `transition_order(state, event) -> OrderLifecycleState` authority
   implementing Section 4 exactly, raising fail-closed on any invalid pair.
2. A `BrokerSubmission`/`Ack`/`Reject` normalization layer that maps broker adapter
   responses to the canonical events in Section 3 (no direct broker enum leakage).
3. Integration of `CANCEL_REQUESTED` + `ConnectionLost` → `UNKNOWN` with the
   reconciliation trigger and `RESTRICTED` shadow-mode gate.
4. Adversarial test suite attacking: terminal absorbing, `UNKNOWN` no-shortcut,
   invalid (source,event) pairs, connectivity-lost during cancel, fill-vs-cancel race,
   and reconciliation-only resolution of `UNKNOWN`.

The mock broker adapter MAY be implemented against this contract next; the REAL
broker adapter MUST NOT begin until this contract + state machine engine + mock
adapter are verified.
