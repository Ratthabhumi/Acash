# Phase 7 Step 8F: Real Broker Adapter Contract (Pre-Implementation)

> **Status: DRAFT — DOCS-ONLY CHECKPOINT.**
> This document is a **normative pre-implementation contract** for the Real Broker
> Adapter. It FREEZES the interface rules between a real broker and the existing
> canonical execution boundary BEFORE any broker-specific adapter code is written.
> It does NOT implement any broker adapter and does NOT change any execution code.
>
> It is binding on any `real` broker adapter implemented under `acash.execution`
> later. A real broker implementation MUST NOT begin until this contract is
> reviewed and locked, because the highest-risk remaining failure mode is not the
> internal state machine — it is the **adapter that translates broker reality
> (incorrectly) into canonical events**.
>
> Prerequisite idiom — all executable pieces referenced here already exist and are
> locked:
> - `src/acash/execution/state_machine.py` (Step 8B) — sole state-transition authority.
> - `src/acash/execution/broker_events.py` (Step 8C) — broker-agnostic normalizer.
> - `src/acash/execution/mock_broker.py` (Step 8D) — broker-side reality simulator.
> - `src/acash/execution/coordinator.py` (Step 8E) — shadow state + reconciliation seam.
> - `src/acash/execution/operational_restriction.py` + `admission.py` — restriction/admission boundary.

---

## 1. Scope & the Core Boundary Invariant

The adapter is a **translator, not a decision authority**. It sits between broker
reality and the canonical boundary:

```
Broker Raw State / Error / WebSocket / Rest Response
        │
        ▼
  Broker Adapter            <- THIS LAYER: translation only
        │  (must yield canonical BrokerEventKind + evidence fields)
        ▼
 broker_events.normalize_broker_event()   (Step 8C, deterministic)
        │  (yields ExecutionEvent + ReconciliationEvidence | None)
        ▼
        ExecutionCoordinator.apply()      (Step 8E, shadow state + dedup)
        │
        ▼
   transition_order()                     (Step 8B — SOLE state authority)
        │
        ▼
       State
```

$$\boxed{ BrokerAdapter \neq StateAuthority }$$

Normative (RFC-2119):
- **N-1**: An adapter MUST NOT compute, return, or mutate any `OrderLifecycleState`.
  It emits **broker reality** only (broker status / error / event) mapped onto the
  canonical `BrokerEventKind` vocabulary and the `ReconciliationEvidence` lineage.
  State transition is performed ONLY by `transition_order()` (Step 8B).
- **N-2**: An adapter MUST translate broker payloads onto the canonical
  `BrokerEventKind` vocabulary (ACK, REJECT, PARTIAL_FILL, FILLED,
  CANCEL_REJECTED, ORDER_CANCELLED, EXPIRED, CONNECTION_LOST) and the
  `ReconciliationEvidence` fields (broker_order_id, observed_status, observed_at,
  source, broker_sequence, evidence_digest) defined in `broker_events.py`. It MUST
  NOT introduce broker-enum leakage into the canonical boundary.
- **N-3**: An adapter MUST route all normalization through
  `normalize_broker_event()`; it MUST NOT hand-roll its own event mapping on the
  side (single canonical mapping authority; §2.6 of the state machine contract).
- **N-4**: `cancel_was_requested` MUST be sourced from **broker-side/client
  knowledge** (whether a cancel request is in flight with the broker), NEVER
  derived from internal shadow state. This mirrors the Step 8D mock-broker design.

---

## 2. Contract Area 1 — Broker → Canonical Event Mapping

### 2.1 Broker status → `BrokerEventKind` (adapter responsibility)
The adapter MUST map its vendor status/event onto these canonical kinds first; the
normalizer then maps kind → `ExecutionEvent`. The canonical target set is:

| Canonical kind | Meaning the adapter MUST guarantee | Resulting canonical event (via 8C) |
| :--- | :--- | :--- |
| `ACK` | Working order acknowledged by broker | `ACK` |
| `REJECT` | Order rejected (authoritative terminal reject) | `REJECT` |
| `PARTIAL_FILL` | Partial fill, residual still working | `PARTIAL_FILL` |
| `FILLED` | Complete fill (cumulative = requested) | `FILL` |
| `CANCEL_REJECTED` | Cancel request rejected; order remains live | `CANCEL_REJECT` |
| `ORDER_CANCELLED` | Broker reports order removed from book (ambiguous w/o hint) | `CANCEL_ACK` **if** `cancel_was_requested`, else reconciliation (fail-closed) |
| `EXPIRED` | Order expired per `TimeInForce` | `EXPIRY` |
| `CONNECTION_LOST` | Connectivity lost / ambiguous timeout | `CONNECTION_LOST` |

Normative:
- **M-1**: An adapter MUST NORMALIZE to the above `BrokerEventKind` set; the
  vendor's native status enum MUST NOT cross the boundary.
- **M-2** **Cumulative-fill triage** — the adapter MUST classify a broker fill
  report by cumulative filled quantity `q_cum` relative to requested `q_req`:
  - `q_cum < q_req` → `PARTIAL_FILL` (residual still working).
  - `q_cum = q_req` → `FILLED` (terminal).
  - `q_cum > q_req` → **OVERFILLED / protocol anomaly** — MUST NOT be silently
    classified as `FILLED`; the adapter MUST route this to an incident /
    reconciliation (fail-closed), not assert a normal terminal fill.
- **M-2a**: An adapter MUST report the per-fill `fill_qty` carried for
  `PARTIAL_FILL`/`FILL` accumulation by the coordinator (§4 I-4). It MUST NOT
  silently clamp an overfill down to the requested quantity.
- **M-3**: `ORDER_CANCELLED` without a broker-side cancel in flight is an ambiguous
  unexpected cancellation; the adapter MUST surface it as ambiguous and let the
  normalizer fail closed / route to reconciliation — it MUST NOT guess an order
  state.
- **M-4**: Unknown / unmatched vendor status MUST be surfaced as an error
  (fail-closed), NEVER silently mapped to a benign event.

### 2.2 Broker error → canonical classification
Vendor error codes MUST be classified into **one of**: authoritative rejection
(`Reject`-equivalent), cancel-related rejection (`CancelRejected`-equivalent),
connectivity/timeout (`ConnectionLost`-equivalent), or unresolvable (needs
admission/reconciliation). A broker error SHALL NOT be assumed terminal unless it
is an authoritative order rejection.

| Vendor error class | Adapter must map to | Route |
| :--- | :--- | :--- |
| Order-level invalid (auth, size, symbol) | `REJECT` | normalizer → `REJECT` |
| Cancel request refused; order live | `CANCEL_REJECTED` | normalizer → `CANCEL_REJECT` |
| Socket drop / read timeout / 5xx / ambiguous ack | `CONNECTION_LOST` | normalizer → `CONNECTION_LOST` → `UNKNOWN` |
| Anything the adapter cannot classify | raise (fail-closed) | reconciliation/incident, never silent |

---

## 3. Contract Area 2 — Timeout / Connection-Loss → UNKNOWN Semantics

This is the most safety-critical area. It re-affirms the state machine contract
(§2.2, §2.3, §2.4) at the adapter boundaory and forbids the classic adapter bug of
"assume timeout = cancelled".

$$\boxed{ timeout\;/\;ambiguous \longrightarrow UNKNOWN \longrightarrow RECONCILE }$$

$$\boxed{ timeout \not\longrightarrow CANCELLED }$$

Normative:
- **T-1**: On an **acknowledgement timeout** (no `ACK`/`REJECT` within the
  configured ack deadline) the adapter MUST emit `CONNECTION_LOST` →
  `UNKNOWN`. It MUST NOT emit a `CANCEL_ACK`/`FILL`/`REJECT` on speculation.
- **T-2**: On a **pending-cancel confirmation timeout** the adapter MUST emit
  `CONNECTION_LOST` → `UNKNOWN` (order becomes first-class `UNKNOWN`). It MUST NOT
  report the order as `CANCELLED` merely because a cancel was requested
  (`CancelRequested ≠ Cancelled`, contract §2.4).
- **T-3**: Any ambiguous broker response where the true outcome cannot be
  established MUST become `UNKNOWN` and REQUIRES reconciliation evidence to exit.
  Recovery is `COORDINATOR.reconcile(...)` with authoritative evidence
  (Step 8E), never adapter-side self-selection.
- **T-4**: Timeout/deadline values are explicit configurable constants per venue
  (never silent magic floors); the adapter MUST log and surface the bound used.
- **T-5**: The adapter MUST NOT convert a timeout into a terminal state directly;
  any terminal claim requires an authoritative broker status or reconciliation
  evidence.

---

## 4. Contract Area 3 — Idempotency, Duplicate & Out-of-Order Events

Re-delivery and reordering are expected in live brokers (at-least-once delivery,
restart replay, retries). The system MUST be idempotent and ordering-tolerant at
the coordinator seam, not by fabricating state authority.

- **I-1** **Event identity authority**: event identity is the
  `(broker_event_id, broker_sequence)` pair (Step 8E `CoordinatorEvent`). An
  adapter MUST populate both fields for every logical event. Where a venue
  supplies a trustworthy broker-provided identifier/sequence the adapter MUST use
  it verbatim; where it does not, the adapter MUST apply the declared fallback
  ordering semantics (§5 S-3) — never a silently fabricated look-alike — and
  MUST NOT reuse a value for two distinct logical events within the same scope.
- **I-2** **Idempotency lives in the coordinator** (`ExecutionCoordinator.apply`),
  where re-delivered `(broker_event_id, broker_sequence)` is detected and skipped
  (DUPLICATE_EVENT incident) without re-applying a transition or re-accumulating
  fill qty. The adapter MUST rely on this; it MUST NOT itself drop duplicates
  before the coordinator (it may de-dupe transport-level bytes, but MUST deliver
  every distinct logical event).
- **I-3** **Out-of-order events**: the state authority (`transition_order`)
  REJECTS any `(state, event)` pair not in the canonical table (fail-closed). An
  out-of-order event that reaches a wrong source state therefore raises
  `ExecutionStateError` and the coordinator records a LATE_EVENT/incident routed to
  reconciliation. The adapter MUST NOT attempt to reorder, suppress, or "fix" the
  sequence itself — it MUST forward reality in arrival order.
- **I-4** **Fill quantity**: fill qty MUST be carried by the adapter for
  `PARTIAL_FILL`/`FILL` and accumulated ONLY by the coordinator on non-duplicate
  events. The adapter MUST NOT adjust cumulative fill totals.
- **I-5** A duplicate delivered AFTER a terminal state shall be surfaced as a
  LATE_EVENT incident (terminal-absorbing, §2.5), never silently dropped.

---

## 5. Contract Area 4 — Broker Sequence / Timestamp / Clock-Skew Policy

- **S-1** All timestamps entering the canonical boundary MUST be UTC and
  timezone-aware; the adapter MUST normalize vendor local/naive timestamps to UTC
  `datetime` before calling the normalizer. Never a naive `datetime` here.
- **S-2** `observed_at` is the **broker's report time** for the event, not the
  adapter's local receipt time (unless the broker provides none and receipt is the
  best available, in which case the adapter MUST label it as receipt time).
  `observed_at` is threaded into `ReconciliationEvidence` and incident lineage
  (coordinator has no clock, Step 8E).
- **S-3** **Sequence**: `broker_sequence` is used for event identity (§4 I-1).
  - **REQUIRED when the venue/protocol supplies a trustworthy sequence** (an
    execution-report/sequence id scoped to the order, connection, or stream): the
    adapter MUST populate `broker_sequence` with it verbatim.
  - If the venue does **NOT** provide a trustworthy sequence, the adapter MUST NOT
    fabricate one that *looks* like a genuine broker sequence just to satisfy the
    contract. It MUST populate `broker_sequence` with a distinct, non-empty value
    derived from broker reality (e.g. its own strictly-increasing receipt counter)
    **AND MUST explicitly declare the fallback ordering semantics** (`fallback`
    ordering policy) for that venue — what the value means, its scope
    (per order / connection / stream), and whether it is monotonic. The adapter
    MUST NOT reuse a value for two distinct logical events within the same scope.
    Any sequencing guarantee that the venue cannot provide MUST be declared, not
    silently assumed.
- **S-4** **Clock-skew**: the adapter MUST NOT assume wall-clock equality between
  its host and the broker. If the system's clock-skew watchdog (admission
  `evaluate_kill_switch_triggers`, `CLOCK_SKEW_DETECTED`) fires, the adapter MUST
  stop new submissions and route affected working orders through the disconnect /
  reconciliation path as configured. The adapter MUST NOT silently trust a
  broker timestamp that is far from local UTC when that matters for sequencing.
- **S-5** Sequence ordering policy: `(broker_sequence)` is the ordering reference
  for a single order's event stream; the state authority remains the arbiter of
  what is legal to apply next (I-3).

---

## 6. Contract Area 5 — Credential & Secret Boundary

- **C-1** **No secrets in code or logs**: API/secret/private keys MUST be injected
  via environment / secret store / keystore at runtime, NEVER hard-coded, and NEVER
  logged, serialized into manifests, or included in `ReconciliationEvidence`,
  incidents, or event payloads.
- **C-2** **Secrets never cross the canonical boundary**: the adapter is the only
  component that touches broker credentials; the canonical event path
  (`BrokerEventKind`, `ReconciliationEvidence`, `ExecutionEvent`,
  `CoordinatorIncident`, `OrderIntent`) MUST NOT carry any credential material.
- **C-3** Credential access is scoped to the adapter/transport layer under the
  venue's `LiveAuthorization.allowed_venues`; the adapter MUST fail closed if a
  venue/symbol is not authorized by the relevant `LiveAuthorization`.
- **C-4** On any credential failure (expired, revoked, permission denied) the
  adapter MUST surface a connectivity/authorization incident and stop new
  submissions rather than silently retrying with degraded credentials.
- **C-5** Rotation / revocation: adapter MUST support live secret rotation without
  code change and MUST re-validate auth on reconnect.

---

## 7. What the Adapter MUST NOT Do (Negative Contract)

| Prohibited behavior | Consequence |
| :--- | :--- |
| Compute or set `OrderLifecycleState` directly | Contract violation (§1 N-1); must delegate to `transition_order()` |
| Map `timeout → CANCELLED` | Violates §3 T-2/T-5; must go `UNKNOWN` |
| Treat `cancel requested → cancelled` locally | Violates state-machine §2.4; requires `CANCEL_ACK`/evidence |
| Self-reorder / suppress / rewrite broker event sequence | Violates §4 I-3; forward arrival order |
| Guess an unexpected cancel outcome | Violates §2.1 M-3; fail closed → reconciliation |
| Let fill qty accumulate outside the coordinator | Violates §4 I-4 |
| Log or propagate credentials | Violates §6 |
| Bypass `normalize_broker_event()` with its own mapping | Violates §1 N-3 (dual canonical mapping) |
| Silently drop a late/duplicate/unclassifiable event | Violates §4 I-5 and fail-closed policy |

---

## 8. Adapter Surface (interface shape to be implemented later)

This is the **minimum seam** the future real adapter SHALL provide. It is
doc-scope now; no implementation.

```
submit_order(intent: OrderIntent)                 -> submission receipt / broker_order_id
cancel_order(broker_order_id, client_order_id)    -> cancel request sent (NOT confirmed)
on_event(ws/stream) / request_status(...)         -> yield canonical BrokerRawEvent observations
status snapshot                                   -> for reconciliation queries
credential lifecycle (inject/rotate/revoke)       -> §6
```

Anything the adapter observes is emitted as a canonical `BrokerRawEvent`-shaped
observation (like Step 8D) carrying `broker_order_id`, `event_kind`,
`observed_at`, `source`, `broker_sequence`, `cancel_was_requested`, then handed to
`normalize_broker_event()` → `ExecutionCoordinator.apply()`/`reconcile()`.

---

## 9. Verification Ledger (this checkpoint)

- Implementation Status: **DOCS-ONLY** (no `src/` change; no real broker code touched)
- Contract Enforcement: **NORMATIVE** (MUST / MUST NOT / REQUIRED / INVALID per RFC-2119)
- Authority: **CANONICAL REFERENCE** to Step 8B/8C/8D/8E + admission + restriction lineage
- Local Test Suite: **N/A** (no code change); full repo previously **420 passed**
- Type Checker: **N/A** for this checkpoint (no code change); execution MyPy **0 errors**
- Methodological Caveats: This contract locks the adapter ↔ canonical boundary and
  the 5 risk areas. It does NOT yet specify a chosen broker vendor/protocol, its
  REST/WS message schemas, or a specific retry backoff policy — those belong to the
  concrete adapter design step and MUST be re-audited against this contract before
  implementation. Production composition-root provenance for the restriction
  authority remains a **deployment invariant** (from the operational-boundary
  checkpoint), not code-provable.
