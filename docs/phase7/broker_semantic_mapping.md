# Phase 7 Step 8F: Real Broker Semantic Mapping Framework (Pre-Implementation)

> **Status: DRAFT — DOCS-ONLY CHECKPOINT.**
> This document is a **normative pre-implementation framework** for the Real Broker
> Adapter's *semantic mapping* step. It is **vendor-agnostic**: it does NOT select
> or commit to any broker vendor/protocol, does NOT contain any vendor REST/WS
> message schema, and does NOT authorize any live credentials or live order flow.
>
> Its purpose is to LOCK the **ACASH canonical semantics** — the single contract
> every future vendor adapter must conform to — NOT to lock any vendor's API. It
> FREEZES the *methodology* a vendor adapter MUST follow to translate broker reality
> onto the canonical `BrokerEventKind` + `ReconciliationEvidence` vocabulary, and
> defines the **Broker-specific Mapping specification (BMAP)** that each concrete
> vendor adapter MUST produce and audit BEFORE any implementation.
>
> It does NOT implement anything and does NOT change any execution code.
>
> ```text
> Broker-specific reality
>         ↓
> [Vendor Adapter]                 <- this framework: translation only
>         ↓
> Canonical BrokerEventKind
>         ↓
> ReconciliationEvidence
>         ↓
> normalize_broker_event()         (Step 8C, deterministic)
>         ↓
> Canonical ExecutionEvent
>         ↓
> transition_order()               (Step 8B — SOLE state authority)
> ```
>
> The central invariant, stated once and re-affirmed throughout:
>
> $$\boxed{ \text{Vendor-specific semantics} \longrightarrow \text{ACASH canonical semantics} }$$
>
> A broker MUST conform to the SAME canonical contract. A divergence is DECLARED
> and routed fail-closed — the canonical state machine is NEVER re-shaped to fit a
> vendor. This framework is **not** a mock-broker-contract reissue; it is the
> discipline that keeps the canonical boundary single-source and vendor-free.

---

## 1. Relationship to the Frozen Contracts (no contradiction)

This framework extends the **Broker Adapter Contract**
([`./broker_adapter_contract.md`](./broker_adapter_contract.md), rv `6fd4a78`) from
a single canonical target into a repeatable, per-vendor mapping discipline. It does
NOT replace or weaken it; where a vendor reality would tempt a mapping that
violates a frozen rule, the frozen rule WINS and the divergence is declared and
routed fail-closed. The sandbox/paper adapter (commit `5cee91d`) proves the
interface/contract works; it is NOT evidence that a real broker shares the same
semantics — that gap is exactly what each BMAP must close.

Frozen rules this framework concrete-ises (and MUST NOT contradict):

| Frozen source | Rule pinned here | Where re-stated |
| :--- | :--- | :--- |
| Contract §2.1 `M-2`/`M-2a` | Cumulative-fill triage: `q_cum<q_req→PARTIAL_FILL`, `=→FILLED`, `>→OVERFILL anomaly` (never silent FILLED/clamp) | §3 item 6 |
| Contract §2.2 | Vendor error → canonical classification; unresolvable → fail-closed | §3 item 5 |
| Contract §3 `T-2` | `CancelRequested ≠ Cancelled`; timeout/ambiguous → `UNKNOWN` → reconcile | §3 items 5, 7 |
| Contract §4 `I-1`/`I-3` | Event identity `(broker_event_id, broker_sequence)`; no self-reorder/last-wins | §3 items 3, 4, 8 |
| Contract §5 `S-1`/`S-3` | UTC timestamps; `broker_sequence` REQUIRED when trustworthy else declared fallback | §3 items 3, 4, 9 |
| Contract §6 `C-1`..`C-5` | Credential/secret boundary; no secrets cross canonical boundary | §3 item 10 |

---

## 2. The Broker-specific Mapping specification (BMAP)

Every real broker adapter SHALL be governed by a **BMAP** — a single, auditable,
vendor-specific mapping document. The BMAP is the binding evidence that the
adapter's semantics are correct and is the artifact that lets a sandbox/paper
adapter of a target broker be validated before any live capital.

A BMAP is vendor-agnostic in **structure**, vendor-specific in **content**:

```
BMAP ::= {
  vendor:            <name + version of broker API/protocol>,
  source_authority:  <which broker endpoint/stream is the source of truth>,
  item01: status_map     (raw broker event -> BrokerEventKind)        [§3.1]
  item02: field_map      (required / optional -> ReconciliationEvidence) [§3.2]
  item03: sequence_semantics                                             [§3.3]
  item04: fallback_ordering                                              [§3.4]
  item05: timeout / ambiguous policy                                     [§3.5]
  item06: partial / full / overfill triage                               [§3.6]
  item07: cancel request / ack / reject                                  [§3.7]
  item08: duplicate / out-of-order handling                              [§3.8]
  item09: timestamp / clock-skew policy                                  [§3.9]
  item10: credential & secret boundary                                   [§3.10]
  item11: evidence provenance / digest                                   [§3.11]
  item12: conformance test checklist                                     [§3.12]
  divergences:  List<vendor reality that would tempt a dangerous shortcut;
                how it is routed fail-closed>
  conformance:  Adapter Conformance Matrix (§4), all PASS with evidence.
}
```

### 2.1 Normative gate (SM-0)

**SM-0**: A vendor adapter MAY NOT be implemented unless its BMAP satisfies **all**
12 items in §3 with no conflict against the frozen rules. A BMAP that requires a
conflict, a safety-degrading fallback, or a "silent floor" MUST be escalated for
redesign — never accepted by documenting the shortcut. A divergence MUST be
declared and routed fail-closed; the canonical state machine is NEVER re-shaped to
fit the vendor.

---

## 3. The Twelve Normative Mapping Items (MUST for every future adapter)

Each item is normative (RFC-2119). A future BMAP MUST populate and evidence every
one of them.

### 3.1 Item 1 — Raw broker event → `BrokerEventKind` mapping (status_map)

- **SM-1** The vendor's native status enum MUST NOT cross the canonical boundary
  (contract §2.1 M-1). Only the mapped `BrokerEventKind` does.
- **SM-3** If a vendor reports multiple synonymous statuses (e.g. "partially
  filled" vs "partiallyFilled"), the BMAP MUST canonicalise to ONE canonical kind
  per logical outcome, stated explicitly (single mapping authority).
- Template (per vendor value): vendor status → canonical kind → trigger condition →
  conflict-with-frozen-rule (Y/N).

| Vendor status / event (verbatim) | Canonical `BrokerEventKind` | Trigger condition | Conflict with frozen rule? |
| :--- | :--- | :--- | :--- |
| `<vendor value>` | `ACK` | working / acknowledged | no |
| `<vendor value>` | `REJECT` | authoritative terminal reject | no |
| `<vendor value>` | `PARTIAL_FILL` | `q_cum < q_req`, residual working | no |
| `<vendor value>` | `FILLED` | `q_cum = q_req` | no |
| `<vendor value>` | `CANCEL_REJECTED` | cancel refused, order live | no |
| `<vendor value>` | `ORDER_CANCELLED` | cancelled; ambiguous without hint | only if hint resolves |
| `<vendor value>` | `EXPIRED` | per TimeInForce | no |
| `<vendor value>` | `CONNECTION_LOST` | socket drop / timeout / 5xx / ambiguous ack | no |
| *unclassifiable* | — | MUST raise (fail-closed) | — |

### 3.2 Item 2 — Required / optional fields (field_map)

- **SM-2b** The BMAP MUST declare, per payload, which fields are **required** vs
  **optional**, and map optional field absence to a defined default or a fail-closed
  rejection (never a silent magic value).
- Required lattice onto `ReconciliationEvidence`: `broker_order_id`, `observed_at`,
  `source`, `broker_sequence`, `cancel_was_requested` (contract §2 N-2). Missing a
  REQUIRED field → the adapter MUST NOT emit the event; it MUST fail closed.

| Canonical field | Required | Vendor source field (verbatim) | If vendor absent |
| :--- | :--- | :--- | :--- |
| `broker_order_id` | yes | `<field>` | — |
| `observed_at` | yes | `<field>` | labelled receipt time (SM-7) |
| `source` | yes | `<venue>` | — |
| `broker_sequence` | yes | `<field>` | declared fallback (item 4) |
| `cancel_was_requested` | yes | `<broker-side>` | — |
| `fill_qty` (fill events) | conditional | `<field>` | fail-closed (M-2a) |

### 3.3 Item 3 — `broker_sequence` semantics

- **SM-6** Event identity is `(broker_event_id, broker_sequence)` (contract §4
  I-1). The BMAP MUST specify which vendor field populates each, and its semantics
  (scoped to order / connection / stream; monotonic or not; unique or not). When a
  venue supplies a **trustworthy** sequence, the adapter MUST use it verbatim
  (contract §5 S-3). The BMAP MUST state the meaning explicitly, never leave it
  implicit.

### 3.4 Item 4 — Fallback ordering when sequence unavailable

- **SM-6b** When a venue does NOT supply a trustworthy sequence, the adapter MUST
  NOT fabricate one that *looks* genuinely broker-issued (contract §5 S-3). It MUST
  use a distinct, non-empty value derived from broker reality (e.g. its own
  strictly-increasing receipt counter), and MUST declare the fallback ordering
  semantics in the BMAP: definition, scope, monotonicity guarantee, and any
  guarantee the venue cannot provide (declared, never silently assumed). Never reuse
  a value for two distinct logical events within one order's stream.

### 3.5 Item 5 — Timeout / ambiguous → `UNKNOWN`

- **SM-4** A broker error SHALL NOT be assumed terminal unless it is an
  authoritative order rejection (contract §2.2).
- **SM-5** A timeout or ambiguous response MUST map to `CONNECTION_LOST` → `UNKNOWN`
  (contract §3 T-1/T-2/T-5), never to a terminal state on speculation. Any vendor
  error that maps to nothing MUST be surfaced loudly (incident + stop), never
  defaulted to benign (contract §2.1 M-4). Recovery requires reconciliation
  evidence (Step 8E), never adapter-side self-selection.

### 3.6 Item 6 — Partial / full / overfill semantics

- **SM-2** Fill triage is mandatory and vendor-checked regardless of the vendor's
  own label: `q_cum < q_req → PARTIAL_FILL`, `q_cum = q_req → FILLED`,
  `q_cum > q_req → OVERFILL anomaly` — never silent `FILLED`, never silent clamp
  (contract §2.1 M-2/M-2a). `fill_qty` is carried by the adapter; accumulation is
  done ONLY by the coordinator (contract §4 I-4).

### 3.7 Item 7 — Cancel request / ack / reject semantics

- **SM-8c** `CancelRequested ≠ Cancelled` (contract §3 T-2, state-machine §2.4). A
  cancel REQUEST is not a confirmation. A confirmed cancel requires a real
  `ORDER_CANCELLED`/`CANCEL_ACK` event (with broker-side cancel in flight) or
  authoritative reconciliation evidence. A cancel REJECT leaves the order live
  (`CANCEL_REJECTED`). Confusion must route fail-closed, never guessed.

### 3.8 Item 8 — Duplicate / out-of-order handling

- **SM-8** The adapter forwards events in **arrival order**; it MAY NOT reorder,
  suppress, or rewrite to "fix" sequence (contract §4 I-3). Duplicacy/ordering is
  adjudicated by the coordinator (`ExecutionCoordinator.apply`, I-2) — a re-delivered
  identity is skipped without re-accumulation; a late event after terminal is a
  LATE_EVENT incident (I-5, terminal-absorbing). The adapter MUST NOT drop
  duplicates itself (except transport-level bytes); it MUST deliver every distinct
  logical event.

### 3.9 Item 9 — Timestamp / clock-skew

- **SM-7** All timestamps entering the boundary MUST be UTC-aware (contract §5
  S-1). `observed_at` is the broker's report time unless the broker provides none,
  in which case it is the adapter's labelled receipt time (S-2); the BMAP MUST state
  which.
- **SM-9** The adapter MUST NOT assume wall-clock equality with the broker. On the
  admission clock-skew trigger (`CLOCK_SKEW_DETECTED`) it MUST stop new submissions
  and route working orders through the disconnect/reconciliation path (contract §5
  S-4). A broker timestamp far from local UTC MUST NOT be silently trusted for
  sequencing.

### 3.10 Item 10 — Credential & secret boundary

- Re-affirms contract §6 `C-1`..`C-5`: secrets injected at runtime only, never in
  code/logs/manifests/evidence/incidents; the canonical event path carries NO
  credential material; access scoped to venue `LiveAuthorization.allowed_venues`;
  fail-closed on any credential failure; live rotation without code change.

### 3.11 Item 11 — Evidence provenance / digest

- **SM-10** Every normalized event yields `ReconciliationEvidence` with
  `evidence_digest` provenance (Step 8C). The BMAP MUST state which broker fields
  feed the digest and confirm the adapter NEVER tampers with or fabricates
  digest-relevant fields. Any tamper / mismatch MUST fail closed (digest mismatch →
  incident / reject), never silently accepted. Adapter-side observation MUST be
  reproducible and attributable (`observed_at`, `source`, `broker_sequence`).

### 3.12 Item 12 — Conformance test checklist

- **SM-11** Each BMAP MUST carry a conformance test checklist mapping to §4,
  evidencing every requirement with executable/designed tests. The checklist MUST
  mirror §4 rows and MUST be run (or, pre-implementation, specified and reviewed)
  before the adapter is accepted. Tests MUST attack adversarial cases (boundary,
  overfill, timeout→UNKNOWN, duplicate, out-of-order, tampered digest, secret
  leakage) — not only happy paths (AGENTS.md §14).

---

## 4. Adapter Conformance Matrix (empty template)

This matrix is the **single acceptance ledger** for a BMAP. Rows are the normative
requirements in §3; columns are future vendor adapters. Every cell MUST be `✓`
(conformant + evidenced) before that adapter is considered for implementation, or
`✗` with an explicit, approved fail-closed divergence — NEVER a silent pass.

> TEMPLATE — no real vendor is selected or scored here. Each future BMAP fills one
> column.

| Requirement (normative item) | Adapter A | Adapter B | Adapter C |
| :--- | :---: | :---: | :---: |
| 1. Raw broker event → `BrokerEventKind` mapping | ☐ | ☐ | ☐ |
| 2. Required / optional fields (`field_map`) | ☐ | ☐ | ☐ |
| 3. `broker_sequence` semantics documented | ☐ | ☐ | ☐ |
| 4. Fallback ordering declared (no look-alike) | ☐ | ☐ | ☐ |
| 5. Timeout / ambiguous → `UNKNOWN` (never CANCELLED/REJECTED) | ☐ | ☐ | ☐ |
| 6. Partial / full / overfill (overfill fail-closed) | ☐ | ☐ | ☐ |
| 7. Cancel request / ack / reject (`CancelRequested ≠ Cancelled`) | ☐ | ☐ | ☐ |
| 8. Duplicate / out-of-order (coordinator-adjudicated, no last-wins) | ☐ | ☐ | ☐ |
| 9. Timestamp / clock-skew (UTC, broker report time) | ☐ | ☐ | ☐ |
| 10. Credential & secret boundary (no leakage) | ☐ | ☐ | ☐ |
| 11. Evidence provenance / digest (fail-closed on tamper) | ☐ | ☐ | ☐ |
| 12. Conformance test checklist (§3.12, adversarial §14) | ☐ | ☐ | ☐ |

Admission rule: a BMAP whose matrix has any unchecked `☐`, or an approved `✗`
without a declared fail-closed divergence, is **NOT conformant** and MUST NOT yield
an implementation.

---

## 5. Safety Boundary Re-affirmed (Real Broker / Live path stays OFF)

This framework does NOT enable live trading. Independently of any BMAP:

- **Live orders**: ❌ NOT authorized by this checkpoint.
- **Live credentials**: ❌ NOT introduced; injected only later under the venue's
  `LiveAuthorization.allowed_venues` (contract §6 C-3).
- **Real broker adapter code**: ❌ NOT implemented here.

Next executable road-map, unchanged by this checkpoint:

```text
5cee91d (sandbox/paper adapter)
   ↓
Vendor-Agnostic Semantic Contract     <- THIS checkpoint
   ↓
Freeze
   ↓
Select Target Broker
   ↓
Implement Adapter (guided by audited BMAP)
   ↓
Conformance Tests
   ↓
Sandbox/Paper (target broker)
   ↓
Live Readiness Review
```

---

## 6. Verification Ledger (this checkpoint)

- Implementation Status: **DOCS-ONLY** (no `src/` change; no real broker code touched)
- Contract Enforcement: **NORMATIVE** (MUST / MUST NOT / REQUIRED / INVALID per RFC-2119)
- Authority: **CANONICAL REFERENCE** to `broker_adapter_contract.md` (rv `6fd4a78`)
  + Step 8B/8C/8D/8E + admission/restriction lineage + `5cee91d`
- Local Test Suite: **N/A** (no code change); full repo previously **446 passed**
- Type Checker: **N/A** for this checkpoint (no code change); execution MyPy **0 errors**
- Methodological Caveats: Vendor-agnostic framework + empty conformance matrix only.
  It does NOT select a broker, contains NO vendor schemas, and provides NO retry/backoff
  policy (those belong to a concrete BMAP + adapter design step). The 5 pre-existing
  `dgp_experiments.py` MyPy errors remain **out-of-scope debt**, intentionally untouched.
