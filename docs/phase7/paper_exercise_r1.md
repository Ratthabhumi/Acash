# Phase 7 Paper Exercise — R1 Order-Lifecycle Contract & Evidence Checklist

> **Status: PROPOSED — DOCS-ONLY, NO ORDERS FIRED, NO HARNESS CODE.**
> This is the **R1 exercise contract** that defines how the Alpaca paper adapter is
> empirically pushed through a **live order lifecycle** (submit → ack → fill/cancel
> → reconciliation) and what evidence is required to flip a BMAP Conformance Matrix
> (§A, [`./alpaca_bmap.md`](./alpaca_bmap.md)) cell from **D** (design) to **P**
> (paper-exercised).
>
> It is grounded in the frozen canonical authority, not a re-invention of rules:
> - `./execution_state_machine.md` — the SOLE transition authority (`transition_order()`);
> - `./broker_adapter_contract.md` — the adapter is a translator, NOT a decision authority;
> - `./execution_manifest.md` — `ExecutionManifest` forensic lineage spec;
> - `./reconciliation.md` — 6-dimension reconciliation / `ReconciliationReport`;
> - `./alpaca_bmap.md` §1–§12 — the concrete Alpaca mapping this harness exercises.
>
> All code/schema references in §2/§4/§6 were verified against the concrete
> pipeline source during review: `transition_order()` (`./src/acash/execution/state_machine.py`),
> `normalize_broker_event()` + `ReconciliationEvidence` (`./src/acash/execution/broker_events.py`),
> `ExecutionCoordinator.apply()` + `CoordinatorEvent` (`./src/acash/execution/coordinator.py`),
> `BrokerRawEvent` (`./src/acash/execution/mock_broker.py`).
>
> This document DOES NOT authorize firing orders. It is the contract the R1
> harness (and its tests) must satisfy before a single paper order is submitted.

---

## 0. Why R1 Exists (and what it is NOT)

R0 (`./src/acash/execution/alpaca/paper_exercise.py`, committed `424070c`) proved
**read-only paper connectivity** only. It never mutates broker state, so it is
**NOT** evidence of the order-lifecycle pipeline. Per the locked rule
$$\boxed{\text{E} \neq \text{P}}$$

R0 does **not** count as P; it only proves a credentialed read-only session exists.
R1 is the first checkpoint that **exercises the full translation chain**:

```text
Alpaca SSE trade_updates / REST /v2/orders
        ↓
[Alpaca Adapter]              <- translator ONLY (8F-3)
        ↓
BrokerRawEvent (+ ReconciliationEvidence fields)
        ↓
normalize_broker_event()      <- Step 8C (deterministic)
        ↓
ExecutionCoordinator / transition_order()   <- Step 8B SOLE authority
```

## 0.1 R1 Non-Negotiable Invariants

These are carried forward from the locked framework. The R1 harness MUST satisfy
all of them; a violation is itself a FAILED R1 result, not something to paper over:

1. **`HTTP response != execution state`.** A `POST` ACK (`SubmissionReceipt`) is
   never `FILLED`; a cancel `DELETE 204` is never `CANCELLED`. Terminal state is
   established only by the adapter→normalizer→`transition_order()` chain (BMAP no-shortcut,
   `./broker_adapter_contract.md`, `./transport.py`).
2. **`P evidence != E evidence`.** E (docs/API re-verification) proves documented
   semantics. P (R1) proves runtime behavior against an account. Flipping a §A cell
   to P requires the R1 evidence artifact for that cell — never an E pointer.
3. **The harness MUST NOT skip `transition_order()`.** Every broker observation that
   claims a canonical state MUST pass through the adapter → normalizer →
   `transition_order()` pipeline. The harness MUST NOT set an `OrderLifecycleState`
   directly or fabricate a terminal state.
4. **The harness MUST NOT fabricate terminal states.** `UNKNOWN` may exit ONLY via
   `RECONCILE` carrying authoritative evidence (`./execution_state_machine.md` §2.3).
   `cancelled` without user-cancel provenance fail-closes to reconciliation (BMAP-07
   strict, `./adapter.py` `_map_canceled`). The harness drives these fail-closed paths
   and records the resulting incident/`UNKNOWN` — it NEVER guesses a state.
5. **Authority separation.** The harness and adapter never decide state. They feed
   observations into the pipeline; `transition_order()` is judged only by the
   evidence it produces.
6. **No credential material in evidence.** `ExecutionManifest`, `ReconciliationReport`,
   `PaperReadOnlyEvidence`, and any R1 artifact carry NO secrets (BMAP-10, C-1..C-5).
7. **Paper-only venue.** R1 binds to `ALPACA_PAPER` + paper keys via the existing
   `paper_credential_provider()` / `PaperHttpAlpacaTransport` guard. Live path stays ❌.

## 0.2 Scope Boundary

- R1 fires **paper** orders with a **separate throwaway client_order_id** on a
  **paper account** set up for the exercise; it causes no real money movement.
- R1 does NOT authorize live orders, live credentials, or a live venue.
- R1 exercises real REST/SSE against the paper env with operator-exported
  `ACASH_ALPACA_API_KEY_ID` / `ACASH_ALPACA_API_SECRET` in the running session.
  Unit tests use fake transports and never touch the network.

---

## 1. R1 Exercise Steps (the ordered lifecycle)

For each requirement below, the harness drives an `OrderIntent` through the R0
pattern extended to include write + reconciliation. Use a **dedicated, cancellable
paper order** (e.g. `LIMIT` resting order) so the lifecycle can be observed
deterministically at each stage rather than racing to an instantaneous market fill.

Abstract lifecycle (one or more orders per step, as needed to hit every row):

```text
OrderIntent
   ↓  (authorization gated)
BrokerSubmission (submit_order)
   ↓  HTTP PATTERN PAID / SubmissionReceipt        [HTTP success ≠ FILLED]
ACK / REJECT  (SSE accepted/new/pending_new → ACK → ACKNOWLEDGED)
   ↓
PARTIAL_FILL / FILL  (partial_fill → PARTIALLY_FILLED; fill → FILLED)  — paper random partials
   ↓  or
CANCEL_REQUEST → CANCEL_REQUESTED
   ├─ CANCEL_ACK  → CANCELLED        (reconciliation-resolved, BMAP-07)
   ├─ FILL        → FILLED           (fill-vs-cancel race: fill authoritative)
   ├─ CANCEL_REJECT → ACKNOWLEDGED   (cancel declined, order still working)
   └─ CONNECTION_LOST → UNKNOWN      (first-class; reconcile to exit)
   ↓
REST reconciliation → RealWorldState → RECONCILE → verified terminal
   ↓
ExecutionManifest + evidence lineage (intent_digest → execution_digest → fills)
```

The harness MAY run several order lifecycles to cover the branching table; a
single order cannot traverse both the fill and cancel branches. The R1 result is a
**suite of exercised order lifecycles**, each producing its own evidence lineage.

---

## 2. Required Evidence Per BMAP §A Cell (D → P)

Each §A cell flips to **P** only when its R1 evidence carries the exact raw broker
field/event/state named. Enumerate the artifact required per cell:

| §A | Requirement | R1 evidence artifact required to flip to P |
| :--- | :--- | :--- |
| 1 | Raw event → `BrokerEventKind` mapping | For each SSE event type exercised (`accepted/new/pending_new`, `partial_fill`, `fill`, `rejected`, `expired`, `order_cancel_rejected`), a `BrokerRawEvent` whose `event_kind` equals the canonical map (§1) and whose `source`/`broker_sequence`/`observed_at` are populated from the raw `AlpacaTradeEvent`. |
| 2 | Required/optional fields (`field_map`) | A `BrokerRawEvent` carrying `broker_order_id`, `event_kind`, `observed_at`, `source`, `broker_sequence`, `cancel_was_requested` | 2 | Required/optional fields (`field_map`) | A `BrokerRawEvent` carrying the required fields (`broker_order_id`, `event_kind`, `observed_at`, `source`, `broker_sequence`, `cancel_was_requested`) each derived from the raw Alpaca DTO per BMAP §2 Layer A; plus a persisted `ReconciliationEvidence` (6 canonical fields: `broker_order_id`, `observed_status`, `observed_at`, `source`, `broker_sequence`, `evidence_digest`) with `verify_digest()` passing (BMAP-02/11). |
| 3 | `broker_sequence` semantics (ULID, verbatim) | An `AlpacaTradeEvent.event_id` (ULID) carried **verbatim** as `broker_sequence` for the live SSE path — never timestamp-derived (BMAP-03/09). |
| 4 | Fallback ordering declared | A REST-snapshot observation whose `broker_sequence` is the strictly-increasing `LOCAL-FB-*` local counter, explicitly labelled `fallback`, never presented as genuine Alpaca sequence (BMAP-04). |
| 5 | Timeout / ambiguous → `UNKNOWN` | A simulated `POST`/cancel timeout (`CONNECTION_LOST`) that drives the order to `UNKNOWN`, NEVER `CANCELLED`/`REJECTED`; then a REST `RECONCILE` exiting `UNKNOWN` only with authoritative evidence (state-machine §2.3, §5.3). |
| 6 | Partial / full / overfill | A paper `partial_fill` → `PARTIALLY_FILLED` with cumulative `filled_qty` correctly accumulated (no double-accumulate); a `fill` → `FILLED` with `filled_qty = requested_qty`; and an injected overfill (`filled_qty > requested_qty`) asserting `AlpacaAdapterMappingError` (fail-closed, BMAP-06/M-2). |
| 7 | Cancel request/ack/reject (`CancelRequested ≠ Cancelled`; ambiguous cancel fail-closed) | A `DELETE 204` that changes NO state (still `CANCEL_REQUESTED`/working); a user-cancel resolved via REST snapshot evidence (BMAP-07); a `canceled` SSE event raising `AlpacaAdapterMappingError` (untreated); an `order_cancel_rejected` → `CANCEL_REJECTED` returning to `ACKNOWLEDGED` live (state-machine §2.4, table rows 16–20). |
| 8 | Duplicate / out-of-order (coordinator-adjudicated; SSE replay) | A replayed `event_id` (via `since_id`) whose dedup key `(execution_id, event_id)` is skipped without re-accumulation; a late event after terminal classified `INVALID`-style (fail-closed), not last-wins (BMAP-08, state-machine §2.5 terminal-absorbing). |
| 9 | Timestamp / clock-skew (UTC, broker report time) | `observed_at` captured from the event-keyed `at`/`executed_at`/`updated_at` (not blanket `timestamp`); `event_id` used for ordering only (BMAP-09). |
| 10 | Credential & secret boundary | Every R1 evidence/manifest/incident artifact contains ZERO credential material; the paper venue + paper keys are the ONLY credentials used; a non-paper provider fails closed (BMAP-10, `./credentials.py`, `./transport.py` level 1/1b/2). |
| 11 | Evidence provenance / digest (fail-closed on tamper) | A valid `evidence_digest` over the canonical evidence serialization; an injected digest tamper MUST fail closed (never silently accepted) (BMAP-11 E\*, ACASH-owned). |
| 12 | Conformance checklist (adversarial, §14) | Results for every case in `./alpaca_bmap.md` §12 that requires a live lifecycle, each with its raw evidence (cases 1–15 mapped in §3 below). |

---

## 3. Mapping BMAP §12 Checklist Cases → R1 Order Lifecycles

`./alpaca_bmap.md` §12 defines the pre-implementation adversarial cases. R1 executes
them in paper. Table: which R1 lifecycle(s) satisfy each case and the raw evidence milestone.

| §12 case | R1 lifecycle to drive | Raw evidence milestone (artifact that flips the case) |
| :--- | :--- | :--- |
| 1. submit → accepted/new → ACK → ACKNOWLEDGED | Full submit → ACK order | SSE `accepted`/`new` → `BrokerRawEvent(ACK)` → `transition_order` yields `ACKNOWLEDGED` |
| 2. partial_fill then fill → PARTIALLY_FILLED → FILLED, cumulative correct | Order allowed to partial then fully fill | Two `BrokerRawEvent`s (`PARTIAL_FILL`, `FILLED`) with `filled_qty` cumulative = requested; coordinator accumulates once each |
| 3. paper random partials (no double-accumulate) | Market order in paper | Multiple `partial_fill` events; cumulative = sum of per-fill qty; no re-accumulation |
| 4. POST timeout → CONNECTION_LOST → UNKNOWN, reconcile via REST | Simulated submit timeout | Adapter `CONNECTION_LOST` → `UNKNOWN`; then REST `RECONCILE` → verified terminal |
| 5. DELETE 204 → no immediate change; canceled user-trigger → CANCELLED | Cancel lifecycle | `DELETE 204` leaves state working (`CANCEL_REQUESTED`); `CANCELLED` only after reconciliation snapshot with `cancel_was_requested` (BMAP-07) |
| 6. ambiguous canceled → fail-closed → UNKNOWN/reconciliation | Canceled-without-provenance | SSE `canceled` raises `AlpacaAdapterMappingError`; routed to reconciliation; not guessed |
| 7. canceled with reason=CORPORATE_ACTION → not user cancel | CCC trigger (if paper reproduces) | Treated as non-user cancel → fail-closed/reconciliation, never `CANCELLED` from SSE |
| 8. order_cancel_rejected / TOO_LATE_TO_CANCEL → CANCEL_REJECTED, order live | Cancel rejected | `order_cancel_rejected` → `CANCEL_REJECTED` → `ACKNOWLEDGED` live |
| 9. reconnect SSE with since_id → recovery; redelivery → dedup | Reconnect mid-lifecycle | Replayed `event_id` deduped, no re-accumulation |
| 10. late event after terminal → LATE_EVENT, absorbing | Force terminal, deliver late event | Terminal-absorbing; late event classified fail-closed, historical state unchanged (state-machine §2.5) |
| 11. overfill (filled_qty > qty) → anomaly, NOT silent FILLED/clamp | Injected overfill | `AlpacaAdapterMappingError` (BMAP-06 fail-closed) |
| 12. trade_correct/bust → incident/reconciliation, not silent merge | Incidental (if paper reproduces) | Surfaces as incident/reconciliation input, not merged |
| 13. credential absent from every artifact | All R1 runs | Grep over all evidence/manifest/incident output: no API key/secret string |
| 14. REST snapshot (no SSE cursor) → declared fallback sequence | Reconciliation snapshot | `LOCAL-FB-*` sequence, labelled fallback, not genuine (BMAP-04) |
| 15. tampered evidence digest → fail-closed reject | Reconstruct+alter digest | Digest mismatch raises fail-closed (BMAP-11) |

---

## 4. Evidence Lineage (ExecutionManifest)

Every R1 order lifecycle MUST conclude by emitting an `ExecutionManifest` binding:

```text
intent_digest  →  execution_digest  →  fill events
(client_order_id / broker_order_id / side / qty / cumulative filled_qty / avg fill price)
```

The canonical execution record is the **ordered set of `CoordinatorEvent`s** that
`ExecutionCoordinator.apply()` actually consumed (each of which the coordinator
delegated to `transition_order()` as the sole authority). The exact chain an R1
observation follows — this is the ONLY path that yields a canonical state:

```text
BrokerRawEvent (adapter/8F-3, authority-free)
   ↓  normalize_broker_event()  (broker_events.py:161, Step 8C)
(ExecutionEvent, Optional[ReconciliationEvidence])
   ↓  packed into CoordinatorEvent(broker_event_id, broker_sequence,
        canonical_event, evidence, fill_qty, evidence_refs)
ExecutionCoordinator.apply()  (coordinator.py:168; dedups on (broker_event_id,
                                 broker_sequence), routes late events to incident)
   ↓  transition_order(state, event, evidence=...)  (state_machine.py:139, Step 8B SOLE authority)
verdict: new OrderLifecycleState (or preserving/rejecting terminal)
```

- `intent_digest`: SHA-256 of the originating `OrderIntent` (`./src/acash/execution/schema.py`).
- `execution_digest`: SHA-256 of the canonical execution record — the ordered set
  of `CoordinatorEvent`s successfully applied by `ExecutionCoordinator` for this
  order, serialized in `broker_sequence` order (including their `evidence` /
  `fill_qty` / `evidence_refs`, and the `ReconciliationEvidence.evidence_digest`
  where produced). This binds digest → evidence chain end-to-end.
- `broker_event_id` is the dedup identity (with `broker_sequence`) that makes the
  record idempotent; a re-delivered `(broker_event_id, broker_sequence)` is applied
  once, never re-accumulated.
- `closed_at`: set only when the order reached a verified terminal state (never a
  fabricated one; `UNKNOWN` left open with an incident).
- The manifest is frozen (`extra="forbid"`), carries `broker_order_id`,
  `filled_qty`, `average_fill_price`, and the terminal state fields per
  `./execution_manifest.md` §2.

A lifecycle that ends in `UNKNOWN` (unresolved reconciliation) MUST NOT conclude a
`closed_at`; it MUST record the `UNKNOWN` + incident and leave the manifest open
for later `RECONCILE` resolution.

## 4.1 Reconciliation Evidence

Each R1 lifecycle that passes through `UNKNOWN` uses the 6-dimension reconciliation
(`./reconciliation.md`) and emits a `ReconciliationReport` (`is_in_parity`, dimension
counts, `report_digest`). `UNKNOWN → {terminal}` under `RECONCILE` is allowed ONLY
with that authoritative report (state-machine §2.3).

---

## 5. Fail-Closed Assertions (must hold, or R1 FAILS)

These are the acceptance criteria for the R1 evidence. Assert ALL of them:

1. For every canonical terminal state claimed, there is a `transition_order()` call
   whose source/event/target row exists in `./execution_state_machine.md` §4.
2. No artifact shows a state that was not reached through the pipeline
   (grep the harness: no direct `OrderLifecycleState` assignment outside the engine,
   no fabricated `FILLED`/`CANCELLED`).
3. `UNKNOWN` is resolved only via `RECONCILE` + authoritative report; `UNKNOWN → CANCELLED`
   without evidence does not occur.
4. Every cancel: `DELETE 204` never produces `CANCELLED`; SSE `canceled` raises
   `AlpacaAdapterMappingError`; `CANCELLED` terminal only via REST snapshot with
   `cancel_was_requested=True`.
5. Every overfill raises fail-closed (never silent `FILLED`/clamp).
6. `broker_sequence` on the live SSE path is the verbatim ULID `event_id`; the REST
   snapshot path uses the labelled `LOCAL-FB-*` fallback — never the reverse.
7. No credential material anywhere (BMAP-10).
8. Harness never calls `submit_order`/`cancel_order` without going through the
   adapter/transport seam and never skips `transition_order()`.

---

## 6. Harness Design Requirements (R1 implementation, after this contract is approved)

The R1 harness extends the R0 pattern (`./src/acash/execution/alpaca/paper_exercise.py`),
with the same test discipline:

- **Injected transport**: `run_order_lifecycle(transport, ..., scenario)` accepts an
  `AlpacaTransport` so unit tests use fakes; production builds the paper transport
  from env (`paper_endpoint()` + `paper_credential_provider()`).
- **Write path routed through the adapter + coordinator**: the harness drives
  `AlpacaPaperAdapter` (adapter → transport `submit_order`/`cancel_order`), collects
  `BrokerRawEvent` observations per order, feeds them to `normalize_broker_event()`,
  packs the results into `CoordinatorEvent`s, and submits them to
  `ExecutionCoordinator.apply()` — which is the ONLY path to `transition_order()`.
  The harness NEVER calls `transition_order()` (or mutates an
  `OrderLifecycleState`) outside that chain.
- **Scenarios**: a finite set of named order-lifecycle scenarios mapping 1:1 to
  §3 (e.g. `FULL_FILL`, `PARTIAL_THEN_FILL`, `CANCEL_ACK`, `CANCEL_BEFORE_ACK_TIMEOUT`,
  `CANCEL_REJECT`, `FILL_RACE_CANCEL`, `RECONCILE_EXIT_UNKNOWN`).
- **Evidence DTOs**: frozen, `extra="forbid"`, no secrets; carry raw `broker_order_id`,
  canonical state reached, `broker_sequence`, `evidence_digest`, `observed_at`.
- **Tests (fake transports)**: AST structural guard (no direct state assignment /
  no `transition_order` bypass), per-scenario fake-transport runs asserting the
  exact canonical transitions, fail-closed paths (timeout, ambiguous cancel,
  overfill, custom cancel-provenance), digest tamper, no-secret sweeps.
- **Production P-run**: requires operator-exported
  `ACASH_ALPACA_API_KEY_ID` / `ACASH_ALPACA_API_SECRET` in the session; NOT part of the
  unit suite.

## 6.1 AST / structural guard (carried from R0)

The R1 conformance suite MUST assert by AST that the harness itself (the file under
test) never assigns an `OrderLifecycleState` or calls `transition_order()` directly —
state may only be observed from the pipeline output, never authored locally.

---

## 7. Execution Protocol (order of operations)

1. **This contract is reviewed and approved by the user.** (Current checkpoint —
   NOT yet approved, no orders fired, no harness code.)
2. R1 harness + unit tests are implemented against fake transports; targeted suite
   green; full `uv run pytest` green; `uv run mypy src/ tests/` clean (only the 5
   pre-existing `dgp_experiments.py` errors, out-of-scope).
3. A separate commit for the R1 harness + its tests, staged exactly, `.omc/` excluded,
   committed **only after user approval**.
4. **Real paper P-run** (operator-exported env creds, paper venue): run the
   order-lifecycle scenarios, collect the evidence artifacts, and flip the §A cells
   that are genuinely P — each gated by the §2 evidence. Update `./alpaca_bmap.md`
   §12.5 / §A accordingly with an honest, evidence-backed P record.

Live path stays ❌ throughout; R1 is paper-only.

---

## 8. Next Deliverable (gate)

Until this contract is approved:

- ❌ No `src/` change, no harness code.
- ❌ No order submitted or cancelled anywhere.
- ✅ Stop at the design doc and await review.

---

### Verification Ledger (this checkpoint)

- Implementation Status: **DOCS-ONLY** (no `src/` change; no harness; no account touched)
- Contract Enforcement: **NORMATIVE** (MUST / MUST NOT / REQUIRED per RFC-2119) — PROPOSED
- Mathematical Authority: **CANONICAL SPEC** (`execution_state_machine.md`,
  `broker_adapter_contract.md`, `execution_manifest.md`, `reconciliation.md`,
  `alpaca_bmap.md`)
- Local Test Suite: **N/A** for this checkpoint (no code change); prior full suite **554 passed**
- Type Checker (MyPy): **N/A** for this checkpoint; prior state clean (0 new; 5 pre-existing
  `dgp_experiments.py` errors out-of-scope)
- Remote CI Status: **NOT AVAILABLE** (not run for a docs-only change)
- Methodological Caveats: R1 contract is a proposal. It does NOT yet prove any
  §A cell is P; the evidence milestones in §2/§3 must be collected from a genuine
  paper run (operator-exported credentials, paper venue) before any cell flips from
  D. Paper behavior may differ from live (paper random partials, no live liquidity);
  R1 is paper-lifecycle evidence only, never a live-tradeability claim
  (AGENTS.md §1.5 Empirical Admission ≠ Future Tradeable Profitability).
