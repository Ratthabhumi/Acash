# Phase 7 Step 8: Execution State Machine Contract

> **Status: LOCKED + AMENDED (rv2).**
> This is the **single authoritative normative contract** for order execution
> state transitions. All normative requirements use MUST / MUST NOT / ONLY /
> REQUIRED / INVALID. The Execution State Machine engine MUST implement this
> contract exactly; it is the sole transition authority for a submitted
> `OrderIntent`. No `mock`/`real` broker adapter SHALL be implemented before the
> engine and its tests conform to this contract.
>
> Amendment history:
> - rv1 (`953246d`): base contract.
> - rv2: lock `UNKNOWN` reconciliation-only exit, cancel-sent != cancelled
>   semantics, and terminal-absorbing formal invariant as normative rules.

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

## 2. Core Normative Invariants (Non-Negotiable)

Normative keywords — MUST / MUST NOT / ONLY / REQUIRED / INVALID — are used
per RFC 2119. Every invariant below SHALL be enforced by the transition authority
and SHALL have a corresponding executable test (see Section 9).

### 2.1 State-Only Mutation (Single Authority)
- The order's `OrderLifecycleState` MUST be mutated ONLY through the transition
  authority function.
- No path MAY mutate the lifecycle state in-place outside the authority.

### 2.2 First-Class `UNKNOWN`
- `UNKNOWN` is a fully populated lifecycle state, NOT an error value and NOT an
  ad-hoc fallback.
- An order MUST enter `UNKNOWN` on any ambiguous connectivity/verification
  condition. It MUST NOT be silently coerced to `CANCELLED`, `FILLED`, or any
  other state under ambiguous conditions.

### 2.3 `UNKNOWN` Reconciliation Gate (Formal Invariant)
An order in `UNKNOWN` SHALL have no new orders admitted and SHALL be subject to
mandatory reconciliation:

$$\boxed{ UNKNOWN \Rightarrow \text{NO\_NEW\_ORDERS} \land \text{RECONCILIATION\_REQUIRED} }$$

An order MAY exit `UNKNOWN` ONLY via a `RECONCILE` event carrying authoritative
broker/reconciliation evidence:

$$\boxed{ UNKNOWN \xrightarrow{\text{RECONCILE}} \{\text{FILLED},\text{CANCELLED},\text{REJECTED},\text{EXPIRED},\text{UNKNOWN}\} }$$

- The `UNKNOWN → {FILLED,CANCELLED,REJECTED,EXPIRED}` transitions REQUIRE
  authoritative broker/reconciliation evidence.
- `UNKNOWN → UNKNOWN` is the reconciliation-dispute loop: no verified outcome;
  an incident SHALL be raised and the order MUST remain `UNKNOWN`.
- The engine MUST NOT transition `UNKNOWN → ACKNOWLEDGED`.
- The engine MUST NOT transition `UNKNOWN → CANCELLED` or `UNKNOWN → FILLED`
  without broker evidence.
- Guidance vs. normative: it is NEVER a decision made by "guessing" the outcome.

### 2.4 `CANCEL_REQUESTED` Semantics (Formal Invariant)
A cancel request is NOT a cancel confirmation:

$$\boxed{\text{CancelRequested} \neq \text{Cancelled}}$$

The complete `CANCEL_REQUESTED` fan-out is fixed as follows:

```
CANCEL_REQUESTED
 ├─ CANCEL_ACK      → CANCELLED
 ├─ CANCEL_REJECT   → ACKNOWLEDGED
 ├─ FILL            → FILLED
 └─ CONNECTION_LOST → UNKNOWN
```

- `CANCEL_ACK → CANCELLED` REQUIRES broker confirmation that the order was
  removed from the book.
- `CANCEL_REJECT → ACKNOWLEDGED` SHALL mean the broker confirmed the
  cancellation request was **rejected** and the underlying order **remains
  live/working**. It MUST NOT be interpreted locally as a generic cancellation
  failure that the engine re-specifies.
- `FILL → FILLED` handles the fill-vs-cancel race: a fill REQUESTED while a
  cancel is pending is authoritative — the order is filled.
- `CONNECTION_LOST → UNKNOWN` is REQUIRED whenever cancel confirmation cannot be
  established; `CANCEL_REQUESTED` MUST NOT shortcut to `CANCELLED` without an
  authoritative `CANCEL_ACK` or reconciliation evidence.

### 2.5 Terminal Absorbing States (Formal Invariant)
The terminal states `FILLED, CANCELLED, REJECTED, EXPIRED` are absorbing:

$$\boxed{ s \in \{\text{FILLED},\text{CANCELLED},\text{REJECTED},\text{EXPIRED}\} \Rightarrow \forall e,\; \delta(s,e)=\text{INVALID} }$$

- Any event delivered to a terminal state MUST be classified `INVALID`
  (fail-closed raise), NEVER a no-op permitting later mutation and NEVER a
  backward mutation of historical state.
- Late broker events arriving after a terminal state MUST NOT mutate the
  historical order state; they SHALL be routed to the reconciliation/incident
  path.
- Examples that MUST be `INVALID`: `FILLED → CANCELLED`, `FILLED → UNKNOWN`,
  `CANCELLED → FILLED`, `REJECTED → ACTIVE`, `EXPIRED → FILLED`.

### 2.6 Single Canonical Source of Truth
- Every state in this machine is derived from the single authoritative transition
  table (Section 4) through ONE transition function.
- There SHALL NOT be dual/parallel state machines that can drift.

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
| `CANCEL_REJECT` | Broker confirmed the cancellation request was rejected AND the underlying order remains live/working. |
| `EXPIRY` | Order expired per broker/`TimeInForce`. |
| `CONNECTION_LOST` | Gateway/transport connectivity lost or response timeout. |
| `RECONCILE` | Reconciliation engine delivers an authoritative broker status report (evidence-gated). |

Note: `CONNECTION_LOST` is a **pseudo-event** — it does not originate from the broker;
it originates from connectivity monitoring, and it is the sole path that places an
order into `UNKNOWN`.

Note: `RECONCILE` MUST NOT be treated as a blind assertion. Transitions `UNKNOWN →`
any terminal state under `RECONCILE` REQUIRE the reconciliation engine to produce
authoritative broker evidence for that exact outcome.

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
Formalized in §2.5. Once a state in `{FILLED, CANCELLED, REJECTED, EXPIRED}` is
reached, $\forall e,\ \delta(s,e)=\text{INVALID}$. The transition authority MUST
raise fail-closed (e.g. a dedicated `ExecutionStateError`) rather than mutate.

### 5.3 The `UNKNOWN` No-Shortcut Rule
Formalized in §2.4. From `CANCEL_REQUESTED`, the order MUST NOT be marked
`CANCELLED` unless the broker confirms (`CANCEL_ACK`) or reconciliation
authoritatively verifies the cancel (`RECONCILE` → `CANCELLED`, §2.3 evidence
rule). On `CONNECTION_LOST`, the order MUST go to `UNKNOWN`. This prevents
unfilled-position accounting drift and phantom cancel confirmation.

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

---

## 9. Executable Interpretation (Test-Case Mapping)

The following test cases are the mandatory executable interpretation of this
contract. Each maps 1:1 to a normative invariant above and MUST be present in the
Step 8B verification suite before the implementation may be considered conformant.

| Normative Invariant | Mandatory Test Case | Expected |
| :--- | :--- | :--- |
| §2.3 (UNKNOWN requires reconciliation) | `test_unknown_requires_reconciliation()` | `UNKNOWN` cannot be left except via `RECONCILE`; non-`RECONCILE` events are `INVALID` |
| §2.3 (no direct UNKNOWN→CANCELLED) | `test_unknown_cannot_transition_to_cancelled_directly()` | `UNKNOWN` + `CANCEL_ACK` is `INVALID` (no broker evidence path) |
| §2.3 (no UNKNOWN→ACKNOWLEDGED) | `test_unknown_cannot_transition_to_acknowledged()` | `INVALID` |
| §2.3 (UNKNOWN→UNKNOWN dispute loop) | `test_unknown_reconcile_dispute_remains_unknown()` | stays `UNKNOWN` + incident raised |
| §2.3 (evidence-gated recovery) | `test_unknown_reconcile_to_verified_terminal()` | `RECONCILE` → each of `FILLED/CANCELLED/REJECTED/EXPIRED` with evidence |
| §2.4 (CancelRequested ≠ Cancelled) | `test_cancel_requested_is_not_cancelled()` | `CANCEL_REQUESTED` status distinct from `CANCELLED`; no implicit coercion |
| §2.4 (CANCEL_ACK validation) | `test_cancel_ack_transitions_to_cancelled()` | only with authoritative `CANCEL_ACK` |
| §2.4 (CANCEL_REJECT semantics) | `test_cancel_reject_returns_to_acknowledged_live()` | `CANCEL_REJECT` → `ACKNOWLEDGED`, underlying order live |
| §2.4 (fill-vs-cancel race) | `test_late_fill_after_cancel_requested_becomes_filled()` | `CANCEL_REQUESTED` + `FILL` → `FILLED` |
| §2.4 (connection loss during cancel) | `test_connection_loss_during_cancel_becomes_unknown()` | `CANCEL_REQUESTED` + `CONNECTION_LOST` → `UNKNOWN` |
| §2.5 (terminal absorbing) | `test_terminal_states_are_absorbing()` | $\forall e,\ \delta(s,e)=\text{INVALID}$ for each terminal state |
| §2.5 (late event after terminal) | `test_late_event_after_terminal_raises_invalid_not_mutation()` | late event raises fail-closed; historical state unchanged |

FAIL-CLOSED rule: a test asserting a transition is `INVALID` MUST assert the
transition authority raised a fail-closed error (the engine MUST NOT silently
return the prior state as if nothing happened — that is an implicit coercion and
is itself a contract violation).
