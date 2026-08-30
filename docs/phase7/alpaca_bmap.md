# Phase 7 Step 8F: Concrete Broker Mapping Specification (BMAP) — Alpaca

> **Status: PROPOSED — DOCS-ONLY, AUDIT-PENDING CHECKPOINT.**
> This is the **concrete Broker-specific Mapping specification (BMAP) for Alpaca**,
> an instance of the vendor-agnostic framework in
> [`./broker_semantic_mapping.md`](./broker_semantic_mapping.md) (rv `7779111`),
> which in turn extends the Broker Adapter Contract
> ([`./broker_adapter_contract.md`](./broker_adapter_contract.md), rv `6fd4a78`).
>
> It is **PROPOSED**: it converts the vendor-agnostic 12 items into concrete
> Alpaca mappings based on Alpaca's documented API surface (Trade Events SSE
> `trade_updates`, Activity SSE, and REST `/v2/orders`). It is **audit-pending**: the
> Conformance Matrix (§A) marks each item DESIGN-CONFORMANT (D) but **no cell is
> EXECUTED (E/PASS) yet** — nothing has been run against a live or paper account.
>
> It does NOT implement an adapter, does NOT touch execution code, does NOT select
> live credentials, and does NOT authorize live orders. A broker-specific
> sandbox/paper adapter for Alpaca is NOT to be written until this BMAP is audited
> and locked, matching the framework gate (§2.1 SM-0).

---

## 0. Scope & Source of Truth

- **Vendor / protocol**: Alpaca Trading API (version noted in Conformance Matrix;
  endpoints subject to change — pin SDK version per best practice).
- **Source authority** (what is the source of truth for order state):
  - **Realtime**: Trade Events SSE stream `trade_updates` (`/v2/events/trades`) for
    order lifecycle events (`accepted`, `new`, `partial_fill`, `fill`, `canceled`,
    `expired`, `rejected`, `order_cancel_rejected`, `replaced`, …).
  - **Replay / recovery**: the same SSE supports replay via `since_id` (ULID
    cursor) and `since_ulid`/`until_ulid`; the broker is explicit that a consumer
    "can always re-open and request data after a particular event using
    `since_id`" to avoid missed events.
  - **Authoritative reconciliation snapshot**: REST `GET /v2/orders/{order_id}`,
    `GET /v2/orders` with `by_client_order_id`, `position_qty`, and account/positions
    queries. Used to exit `UNKNOWN` (reconciliation evidence) and to validate the
    SSE-derived state.
- **Paper environment**: first-class, separate base URL `paper-api.alpaca.markets`,
  distinct key pair, mirrors the live API surface. Paper intentionally injects
  random partial fills to exercise client fill handling — safely testable without
  live capital.

Pipeline (unchanged canonical boundary):

```text
Alpaca SSE trade_updates / REST /v2/orders
        ↓
[Alpaca Adapter]                  <- this BMAP: translation only
        ↓
Scan. BrokerEventKind + ReconciliationEvidence fields
        ↓
normalize_broker_event()          (Step 8C, deterministic)
        ↓
Canonical ExecutionEvent
        ↓
transition_order()                (Step 8B — SOLE state authority)
```

Central invariant restated:
$$\boxed{ \text{Alpaca-specific semantics} \longrightarrow \text{ACASH canonical semantics} }$$

---

## 1. Item 1 — Raw broker event → `BrokerEventKind` mapping

Alpaca `TradeUpdateEventType` → canonical. Vendor enum MUST NOT cross the boundary
(framework §3.1 SM-1).

| Alpaca `event` | Canonical `BrokerEventKind` | Notes / trigger | Frozen-rule conflict |
| :--- | :--- | :--- | :--- |
| `accepted` | `ACK` | received by Alpaca, not yet routed | no |
| `new` | `ACK` | received **and routed** to venue | no |
| `pending_new` | `ACK` | routed, not yet accepted for execution | no |
| `partial_fill` | `PARTIAL_FILL` | `order.filled_qty < qty` (residual working) | no (M-2) |
| `fill` | `FILLED` | `order.filled_qty = qty` | no (M-2) |
| `rejected` | `REJECT` | authoritative terminal reject | no |
| `canceled` | `ORDER_CANCELLED` | **ambiguous** — see §7 for `reason`/`cancel_requested_at` triage | only if hint resolves (M-3) |
| `expired` | `EXPIRED` | reached end of lifespan per TIF | no |
| `replaced` / `order_replace_rejected` | incident / reconciliation | not a local canonical terminal; treat as state-changing observation | requires explicit handling |
| `order_cancel_rejected` | `CANCEL_REJECTED` | cancel refused; confirmed live | no |
| `done_for_day`, `held`, `stopped`, `suspended`, `calculated`, `pending_cancel`, `pending_replace` | in-flight / non-terminal | MUST NOT be treated as terminal | fail-closed on misuse (M-4) |
| `trade_bust` / `trade_correct` | incident / reconciliation | correction of a prior fill; MUST NOT be silently merged | fail-closed (I-5/overfill lineage) |
| *unknown / unmatched transient status* | — | MUST raise (fail-closed) | — (M-4) |

Normative:
- **A-1** Only the mapped `BrokerEventKind` crosses the boundary; the Alpaca enum
  and `order.status` string never do.
- **A-2** `partial_fill`/`fill` classification MUST verify cumulative `filled_qty`
  against requested `qty` (M-2 triage), never trust the label alone.

---

## 2. Item 2 — Required / optional fields (`field_map`)

Alpaca order/event → canonical boundary. **The canonical models are fixed by
Step 8C/8E; this BMAP adapts TO them, never the reverse**
($\boxed{\text{Canonical Code} > \text{Vendor Mapping}}$). Three distinct layers
carry an Alpaca field to exactly one destination:

```text
Alpaca raw field
      ↓
┌──────────────────────────────┐
│ A. Normalizer input          │   normalize_broker_event(...) params
│     cancel_requested_at →    │
│     cancel_was_requested     │
│     event_kind               │
│     broker_order_id          │
│     observed_at              │
│     broker_sequence          │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ B. ReconciliationEvidence    │   persisted evidence schema
│     broker_order_id          │
│     observed_status          │
│     observed_at              │
│     source                   │
│     broker_sequence          │
│     evidence_digest          │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ C. CoordinatorEvent          │   event identity + application
│     broker_event_id          │
│     broker_sequence          │
│     canonical_event          │
│     fill_qty                 │
│     order_id                 │
│     observed_at              │
│     evidence_refs            │
└──────────────────────────────┘
```

### Layer A — inputs to `normalize_broker_event()` (broker-client-sourced hints)

These are the **parameters** to Step 8C. They are transport hints, NOT persisted
as evidence fields.

| Normalizer input | Required | Alpaca source (verbatim) | If Alpaca absent |
| :--- | :--- | :--- | :--- |
| `broker_order_id` | yes | `order.id` (UUID) | — |
| `event_kind` | yes | mapped from Alpaca `event` (see §1) | fail-closed (never guessed) |
| `observed_at` | yes | `timestamp` on the trade event; else `order.updated_at` (contract S-2 broker report time) | labelled receipt time |
| `source` | yes | `"ALPACA"` | — |
| `broker_sequence` | yes | `event_id` (ULID, v2) on SSE; see §3 | declared fallback (REST path, §4) |
| `cancel_was_requested` | conditional | `order.cancel_requested_at != null` (broker-side knowledge, NOT internal shadow state) | fail-closed ambiguity (§7) |

### Layer B — persisted `ReconciliationEvidence` schema (FIXED by Step 8C, not expanded)

The evidence schema is the canonical one in `broker_events.py` and is **NOT
modified to fit this BMAP** (canonical authority). Only these fields exist:

| Evidence field | Alpaca source | Notes |
| :--- | :--- | :--- |
| `broker_order_id` | `order.id` | authoritative broker order identifier |
| `observed_status` | mapped `BrokerEventKind` (§1) | canonical, never vendor enum |
| `observed_at` | broker report `timestamp` | UTC |
| `source` | `"ALPACA"` | venue |
| `broker_sequence` | `event_id` | broker sequence / replay id |
| `evidence_digest` | computed by normalizer | SHA-256 over canonical serialization |

The BMAP adds NO fields to this schema. Per-vendor extra identifiers
(`execution_id`, `client_order_id`, `cancel_requested_at`) do NOT live here — they
feed Layer A / Layer C instead.

### Layer C — `CoordinatorEvent` (identity + application)

| CoordinatorEvent field | Alpaca source / derivation | Notes |
| :--- | :--- | :--- |
| `broker_event_id` | `execution_id` (fill/partial) else `order.id:event` | dedup key (contract I-1) |
| `broker_sequence` | `event_id` | ordering reference (S-5) |
| `canonical_event` | normalizer output `ExecutionEvent` | |
| `fill_qty` | per-fill event `qty` (fill/partial only) | accumulated ONLY by coordinator (I-4) |
| `order_id` | local identity (ACASH) | optional |
| `observed_at` | broker report `timestamp` | UTC |
| `evidence_refs` | digested evidence lineage | tamper-evident |

### Required-lattice rule (framework §3.2)

A missing REQUIRED field in **Layer A** -> the adapter MUST NOT emit the event; it
MUST fail closed. Layer B is produced by the normalizer; Layer C is assembled by
the pump from Layer A/B + identity.

### Timestamp framing (current Alpaca semantics)

Do NOT treat any single timestamp as a universal canonical event time. Current
Alpaca docs distinguish four clock/identity notions:

```text
event_id      = ordering / replay identity (publication sequence; ULID, v2)
at            = business event time (when the activity occurred in the source system)
executed_at   = execution time where applicable (supersedes the legacy field for fills)
timestamp     = LEGACY / event-dependent field; do NOT treat as universal canonical time
```

- `timestamp` "has various different meanings depending on the value of `event`"
  (TradeUpdateEventV2 schema). In the Activity SSE it is renamed/superseded by
  `executed_at`. The adapter MUST NOT assume a single meaning for `timestamp`.
- Per-event mapping: `at` → business event time; `executed_at` (fill/partial) →
  execution time; `event_id` → ordering/replay identity (see §3, §8, §9).
- Any use of `timestamp` must be event-keyed and flagged as legacy/event-dependent.

---

## 3. Item 3 — `broker_sequence` semantics

**Terminology (v2, current docs):** the SSE `broker_sequence` source is the **v2
`event_id` (ULID)**, NOT the legacy v1 `event_ulid`. Current Alpaca docs (Activity
SSE + Trade Events SSE v2) define `event_id` as a ULID: "lexicographically
sortable, monotonically increasing event identifier... The time part encodes the
timestamp when event-streaming emitted the event (publication time). Use for
cursor-based replay." The legacy integer/`event_ulid` naming applies only to
deprecated `/v1`/legacy endpoints. This BMAP targets the v2 endpoint and uses
`event_id`.

- **REQUIRED (verbatim)**: The Trade Events SSE (v2) supplies a **trustworthy
  broker-issued sequence**: `event_id` (ULID) on every event, which is
  **lexicographically sortable and deterministic-replayable** (`since_id`).
  The adapter MUST populate `broker_sequence = event_id` **verbatim** (contract
  §5 S-3 REQUIRED; framework §3.3 SM-6), and MUST **NOT** derive it from any
  timestamp, wall clock, or `at` field — Alpaca defines `event_id` as the
  publication-issued sequence and requires it as the replay cursor.
- **Boxed invariant (publication ≠ business):**
  $$\boxed{\text{publication sequence} \neq \text{business timestamp}}$$
  `event_id` (publication time order) is independent of `at`/`timestamp`
  (business/execution timing). Backfill can publish a business-old event later
  (e.g. a `trade_correct` with `at` hours before its delivery), so
  lexicographic/sequence order MUST NOT be assumed equal to business-time order.
  This propagates into §9. See §8 for how these two axes are used distinctly:
  `event_id` for ordering/replay/dedup, `at`/`timestamp` for observed business
  timing only.
- Identity: `(broker_event_id, broker_sequence)` = `(execution_id or
  order.id:event, event_id)` — see §8.
- Semantics statement: ULID encodes publication time + stochastic component,
  monotonic per source, unique per event — satisfies I-1 (no reuse within an
  order's stream).

---

## 4. Item 4 — Fallback ordering when sequence unavailable

- The SSE path needs NO fallback (`event_id` REQUIRED, §3).
- **Declared fallback (REST-snapshot only)**: when state is reconstructed from REST
  `GET /v2/orders` (no SSE cursor), Alpaca provides `order.updated_at` but no
  monotonic per-event id on that snapshot path. The adapter MUST then use its own
  **strictly-increasing local receipt counter** as `broker_sequence`, declared as
  `fallback` semantics (framework §3.4 SM-6b): definition (per-connection receipt
  counter), scope (per order stream), monotonic (true), and MUST be labelled
  `fallback` — never presented as a genuine Alpaca sequence. This fallback applies
  ONLY to reconciliation snapshots, never to the live SSE path.

---

## 5. Item 5 — Timeout / ambiguous → `UNKNOWN`

- Re-affirms frozen contract §3 T-1/T-2/T-5 and framework §3.5.
- **Ack/submit timeout**: Alpaca guidance — if an order `POST` times out it "may
  have been sent to the market for execution"; the client MUST NOT resend or mark
  the order canceled on speculation. The adapter MUST emit `CONNECTION_LOST` →
  `UNKNOWN` and rely on reconciliation to establish reality.
- **Pending-cancel confirmation timeout**: a cancel `DELETE` returning 204/422 does
  not itself prove final state; confirmation arrives as a later `canceled`/event.
  Until confirmed, `CancelRequested ≠ Cancelled`; on timeout the adapter MUST emit
  `CONNECTION_LOST` → `UNKNOWN`, not `CANCELLED` (T-2).
- **Ambiguous `canceled`**: see §7 — must route fail-closed / `UNKNOWN` when the
  cancel origin is unclear.

---

## 6. Item 6 — Partial / full / overfill semantics

- **Triage (M-2, framework §3.6 SM-2)**: using cumulative `order.filled_qty` and
  requested `order.qty`:
  - `filled_qty < qty` → `partial_fill` → `PARTIAL_FILL`
  - `filled_qty = qty` → `fill` → `FILLED`
  - `filled_qty > qty` → **OVERFILL anomaly** → MUST NOT be silently
    `FILLED`/clamped; raise + route to reconciliation/incident (M-2/M-2a).
- Per-fill `qty` and `price` are carried by the adapter; cumulative accumulation is
  done ONLY by the coordinator (contract §4 I-4).
- Alpaca paper injects random partial fills — the natural, safe harness for testing
  this triage without live capital.

---

## 7. Item 7 — Cancel request / ack / reject semantics (CRITICAL NUANCE)

Alpaca `canceled` is **not** proof of a user cancel.

- The `canceled` event can be user-submitted **or** Alpaca-side (corporate-action
  sweeps, aged-GTC expiry, overnight lifecycle) **or** upstream-venue-initiated.
  A machine-readable cause is exposed via the top-level `reason` field on
  `canceled`/`order_cancel_rejected` (e.g. `CORPORATE_ACTION`,
  `TOO_LATE_TO_CANCEL`).
- **Adapter rule (A-3, fail-closed per framework §3.7 SM-8c / contract M-3):**
  - If `cancel_requested_at != null` (broker-side cancel in flight) AND
    `reason` indicates a user cancel → map to `ORDER_CANCELLED` →
    `CANCEL_ACK` (canonical), authority reconciles to `CANCELLED`.
  - If `canceled` arrives with `cancel_requested_at == null` or an unexpected
    `reason` → **unexpected cancellation** → MUST NOT guess a state; route to
    `UNKNOWN` / reconciliation (fail-closed), per contract M-3.
  - `order_cancel_rejected` → `CANCEL_REJECTED` → order remains live
    (`CANCEL_REQUESTED` stays until facts say otherwise).
  - Never treat a cancel `DELETE` 204 alone as cancelled (T-2).

---

## 8. Item 8 — Duplicate / out-of-order handling

- **Identity**: fill/partial_fill dedup uses `execution_id`; cross-event ordering
  and replay use `event_id` (ULID, sortable, v2). `(execution_id, event_id)` is the
  idempotency key the coordinator consumes.
- **Replay/reconnect**: SSE `since_id` (ULID, v2) supports deterministic replay —
  reconnect resumes from the last processed `event_id` cursor using `since_id`.
  Re-delivered identity is re-applied idempotently. This recovery mechanism is
  **NOT** a claim that the network layer never fails or that no event is ever
  missed; it is a well-defined recovery path. Per Current Alpaca guidance, a
  connection may be closed by client/network error, so the adapter reconnects with
  `since_id = last_processed_event_id` and then lets the coordinator deduplicate
  (`ref_id`/`execution_id`) any re-delivered events.
- **Duplicates**: re-delivered identity is skipped by `ExecutionCoordinator.apply`
  without re-accumulation (contract §4 I-2).
- **Out-of-order / late**: after a terminal state, a late event is a LATE_EVENT
  incident, terminal-absorbing, never silently dropped (contract §4 I-3/I-5). The
  adapter forwards arrival order; it does NOT reorder/suppress (I-3).
- **Trade corrections/busts**: `trade_correct` / `trade_bust` adjust a prior fill;
  they MUST be surfaced as incidents/reconciliation input, never silently merged
  into cumulative totals by the adapter (framework §8-trace I-5, overfill lineage).

---

## 9. Item 9 — Timestamp / clock-skew

- All timestamps UTC-aware (contract §5 S-1). Per §2 timestamp framing,
  `observed_at` (broker report time) is captured from the *event-keyed* field: the
  SSE `executed_at` / business `at` for fill-family events, or `order.updated_at`
  for snapshots — NOT a blanket `timestamp` (which is legacy/event-dependent).
  Never the adapter's local receipt unless the broker provides none (S-2,
  labelled).
- **Boxed invariant (ordering identity ≠ event time — from §3):**
  $$\boxed{\text{Ordering Identity} \neq \text{Event Time}}$$
  The `event_id` (ULID) gives **publication-order** sequencing; `at`/`timestamp`/
  `executed_at` give **business/execution** timing. A backfill can publish a
  business-old event later, so the two axes differ. The adapter MUST use `event_id`
  for ordering/dedup/replay and `at`/`timestamp` only for business-timing evidence;
  it MUST NOT reorder or sequence by timestamps, and MUST NOT derive a sequence
  from a timestamp.
- **Clock-skew** (S-4): adapter MUST NOT assume wall-clock equality. On the
  admission `CLOCK_SKEW_DETECTED` trigger, stop new submissions and route working
  orders through disconnect/reconciliation. A broker timestamp far from local UTC
  MUST NOT be trusted for sequencing when it matters (the ULID also embeds
  publication time — cross-check against broker `timestamp`, but never use it as
  the sequence).

---

## 10. Item 10 — Credential & secret boundary

- Re-affirms contract §6 C-1..C-5 / framework §3.10.
- Alpaca key pair (API key id + secret) injected at runtime via secret store /
  env, never in code, logs, events, evidence, manifests, or incidents.
- Paper uses **distinct keys + `paper-api.alpaca.markets`** base URL — sandbox/paper
  phase binds to the paper key set only; live keys never session-scoped to the
  paper adapter.
- Fail-closed on any credential/authorization failure (expired/revoked/denied):
  stop new submissions, surface incident, live rotation without code change.

---

## 11. Item 11 — Evidence provenance / digest

- `ReconciliationEvidence` is sourced from authoritative Alpaca fields:
  `order.id`, `client_order_id`, `order.status`, `order.filled_qty`,
  `order.filled_avg_price`, `timestamp`, `source="ALPACA"`,
  `broker_sequence=event_id`, `cancel_requested_at`. `evidence_digest` is
  computed by Step 8C normalizer over these canonical fields.
- The adapter MUST NOT tamper with or fabricate digest-relevant fields. Any digest
  mismatch / tamper MUST fail closed (incident/reject), never silently accepted
  (framework §3.11 SM-10).

---

## 12. Item 12 — Conformance test checklist (adversarial)

Pre-implementation designed cases (run in paper during the sandbox-adapter step;
nothing executed yet this checkpoint). Cases MUST include, per AGENTS.md §14
(assumption-attack, not just happy path):

1. submit → `accepted`/`new` → `ACK` → `ACKNOWLEDGED`
2. `partial_fill` then `fill` → `PARTIALLY_FILLED` → `FILLED`, cumulative correct
3. **Paper random partials**: submit market order in paper, verify `partial_fill`
   triage + fill accumulation survives across multiple partials (no double-accumulate)
4. Submit `POST` timeout (simulated) → `CONNECTION_LOST` → `UNKNOWN`, never
   `CANCELLED`/`REJECTED`; reconcile via REST to exit
5. Cancel `DELETE` 204 → no immediate state change; `canceled` user-triggered →
   `CANCELLED`
6. **Ambiguous `canceled`** (no `cancel_requested_at`, unexpected `reason`) →
   fail-closed → `UNKNOWN`/reconciliation, never guessed
7. `canceled` with `reason=CORPORATE_ACTION` → not treated as user cancel
8. `order_cancel_rejected` / `reason=TOO_LATE_TO_CANCEL` → `CANCEL_REJECTED`, order
   live
9. Reconnect SSE with `since_id` → recovery of events from cursor; **possible
   re-delivery** (back-dated cursor) → dedup REQUIRED, no re-accumulation
10. Out-of-order late event after terminal → LATE_EVENT, absorbing; not last-wins
11. Overfill scenario `filled_qty > qty` (simulated/injected) → anomaly, NOT silent
    `FILLED`/clamp
12. `trade_correct`/`trade_bust` → incident/reconciliation, not silent merge
13. Credential material absent from every event/evidence/error/log; no secret leak
14. REST snapshot (no SSE cursor) → declared `fallback` sequence, labelled, no
    look-alike genuine sequence
15. Tampered evidence digest → fail-closed reject

---

## 12.5. Evidence Re-verification Log (D / E / P)

Three-level evidence scheme (established for this audit):
- **D** = documented / design-conformant (what the freeze at `ddc7a73` locked)
- **E** = independently verified against **current** Alpaca API/docs (source direct)
- **P** = empirically exercised in a paper environment (not yet — no paper run)

$$\boxed{D \rightarrow E \neq E \rightarrow P}$$

This log records documentation/API verification only. **No item is P** (nothing has
run against an account). The Conformance Matrix (§A) stays **D** everywhere; E
here is the API/docs re-verification evidence record, not an override of the
admission matrix. Flipping §A cells D→E/P is a separate, later admission step with
its own gate.

Status recap: **BMAP-01..10 = E**, **BMAP-11 = E\*** (see note), **BMAP-12 = D**.
**P = 0** — the Alpaca adapter is NOT yet "verified", because no paper environment
has been exercised.

**Meaning of E for 01–11 (semantic precision):** E here means the Alpaca
**documented capability / semantic contract** is verified against current Alpaca
API/docs. It does **NOT** mean the ACASH mapping behavior is empirically proven or
that the adapter satisfies it — only that the broker's documented semantics match
the claim. `P` (paper-exercised) is the only status that proves runtime behavior;
**P = 0 here.**

**BMAP-11 = E\*** (asterisk): the source fields/identities used for evidence
lineage are verified against Alpaca docs (**E** part), but the **canonical digest
behavior is an ACASH-owned implementation responsibility** — it is NOT Alpaca
behavior and is NOT covered by this evidence; hence the `*`. The digest is enforced
by the ACASH normalizer, not by Alpaca.

| BMAP | Status | Evidence (current Alpaca source) |
| :-- | :--: | :-- |
| 01 | E | **documented event vocabulary**: Trade Events SSE v2 lifecycle list (`accepted/new/pending_new/fill/partial_fill/canceled/expired/replaced/rejected/done_for_day/held/stopped/suspended/pending_cancel/pending_replace/calculated/order_replace_rejected/order_cancel_rejected/trade_bust/trade_correct`) |
| 02 | E | **current field/schema verified**: TradeUpdateEventV2 + `Order` (`event_id` ulid, `event`, `at`, `execution_id` uuid, `qty`/`price` per fill, `previous_execution_id`; `order.id`, `client_order_id`, `filled_qty` cumulative, `cancel_requested_at`). `timestamp` is event-dependent legacy, superseded by `executed_at` (see §2 framing) |
| 03 | E | **`event_id` ULID semantics verified**: v2 `event_id` = ULID publication sequence (vs v1 integer + `event_ulid`); `at` = business event time; keep verbatim; NOT derive from timestamp |
| 04 | E | **cursor/replay capability verified**: `/v2/events/trades` `since`/`until` RFC3339, `since_id`/`until_id` ULID, `since`⊕`since_id`; no cursor → no historic; recon recom. back-date + expect **redelivery** → recovery capability, NOT exactly-once |
| 05 | E | **reconciliation endpoints verified** (order lookup, client-order-id lookup, position query via REST); NOTE: E means the endpoint capability is verified — the ACASH reconciliation *algorithm* is NOT covered by this evidence |
| 06 | E | **fill/partial semantics verified**: per-fill `qty` + `order.filled_qty` cumulative; paper random partials (NOT live-liquidity evidence) |
| 07 | E | **cancel lifecycle/API semantics verified**: `pending_cancel`/`canceled`/`order_cancel_rejected`; `reason` (`CORPORATE_ACTION`, `TOO_LATE_TO_CANCEL`); DELETE 204 = **request accepted ≠ confirmed CANCELLED**, 422 = non-cancellable |
| 08 | E | **reconnect + redelivery/idempotency semantics verified**: SSE reconnect with `since_id`; possible redelivery (back-dated recon cursor) → **idempotent replay REQUIRED**; NOT "exactly-once"/"no missed/no duplicate" |
| 09 | E | **time-field separation verified**: `event_id` (publication/ordering) ≠ `at` (business event time) ≠ `executed_at` (execution time); legacy `timestamp` superseded by `executed_at` in Activity SSE; backfill example proves the axes diverge |
| 10 | E | **credential/paper-live separation verified**: paper & live use distinct domains + keys; trading API uses key/secret auth |
| 11 | E\* | **source fields/identities verified** (`order.id`, `client_order_id`, `filled_qty`, `status`, `event_id`, `execution_id`, `cancel_requested_at`) → Layer B lineage; **canonical digest remains ACASH-owned** (E\* — see note above) |
| 12 | D | Conformance checklist not yet executed (no paper run → not P) |

---

## A. Adapter Conformance Matrix — Alpaca (PROPOSED, audit-pending)

> Cells are design-conformant (**D**) based on documented Alpaca semantics. **No
> cell is EXECUTED (E/PASS) — nothing has run against an account.** Cells flip to
> PASS only after the sandbox-adapter conformance suite (§12) executes in Alpaca
> paper. A single unchecked/`FAIL` cell blocks implementation.

| # | Requirement (normative item) | Alpaca (status) |
| :--- | :--- | :---: |
| 1 | Raw broker event → `BrokerEventKind` mapping | D |
| 2 | Required / optional fields (`field_map`) | D |
| 3 | `broker_sequence` semantics documented (ULID, verbatim) | D |
| 4 | Fallback ordering declared (no look-alike, REST path only) | D |
| 5 | Timeout / ambiguous → `UNKNOWN` (never CANCELLED/REJECTED) | D |
| 6 | Partial / full / overfill (overfill fail-closed) | D |
| 7 | Cancel request / ack / reject (`CancelRequested ≠ Cancelled`; ambiguous `canceled` → fail-closed) | D |
| 8 | Duplicate / out-of-order (coordinator-adjudicated; SSE `since_id` replay) | D |
| 9 | Timestamp / clock-skew (UTC, broker report time) | D |
| 10 | Credential & secret boundary (paper keys, no leak) | D |
| 11 | Evidence provenance / digest (fail-closed on tamper) | D |
| 12 | Conformance test checklist (adversarial, §14) | D |

Admission rule (framework §2.1 SM-0): this BMAP is PROPOSED; it is locked (the
matrix row 12/D becomes enforced) only after audit + paper execution.

---

## B. Safety Boundary Re-affirmed

- **Live orders / Live credentials**: ❌ NOT authorized by this checkpoint.
- **Broker-specific sandbox/paper adapter**: ❌ NOT implemented yet — gated behind
  audit of this BMAP + framework admission rule.
- **Real broker (live) integration**: ❌ remains OUT of scope until the full
  road-map is traversed.

Road-map position:

```text
7779111 (semantic framework)  -> THIS BMAP (PROPOSED) -> Freeze -> Sandbox/Paper Adapter -> Conformance -> Live Readiness
```

---

## C. Verification Ledger (this checkpoint)

- Implementation Status: **DOCS-ONLY** (no `src/` change; no adapter code; no live or paper account touched)
- Contract Enforcement: **NORMATIVE** (MUST / MUST NOT / REQUIRED per RFC-2119) — PROPOSED, audit-pending
- Authority: **CANONICAL REFERENCE** to `broker_semantic_mapping.md` (rv `7779111`)
  + `broker_adapter_contract.md` (rv `6fd4a78`) + Step 8B/8C/8D/8E + `5cee91d`
- Local Test Suite: **N/A** (no code change); full repo previously **446 passed**
- Type Checker: **N/A** for this checkpoint; execution MyPy **0 errors**
- Methodological Caveats: PROPOSED BMAP grounded in Alpaca documentation (SSE
  `trade_updates`, Activity SSE, REST `/v2/orders`, paper env). It is NOT yet
  empirically validated against a live/paper account; the Conformance Matrix is
  DESIGN (D), not EXECUTED (E). Alpaca API behavior (rate limits, event schema,
  deprecation) can change and MUST be re-verified at implementation time. The 5
  pre-existing `dgp_experiments.py` MyPy errors remain **out-of-scope debt**,
  intentionally untouched.
