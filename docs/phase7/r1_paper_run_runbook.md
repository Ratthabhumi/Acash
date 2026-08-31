# R1 Paper Exercise — Runbook (DRAFT — NOT AUTHORIZED)

Status: **DRAFT / NOT AUTHORIZED**. This runbook defines *how* the first real
Paper order would be exercised — it does **NOT** grant authorization to run.
`P = 0` until an actual Paper runtime run completes and produces P evidence.

This document is a **precondition and plan only**. It must be reviewed and
explicitly approved by the operator (order parameters + kill/stop go-ahead)
before any command in it is executed.

References are repository-relative. Authority contract:
`./paper_exercise_r1.md`; broker adapter contract under `./`; harness source
`src/acash/execution/alpaca/order_exercise.py`.

---

## 0. Evidence semantics (E vs P)

- **E** = API / documentation / semantics verification (the 578-test suite, the
  R0/R1 harnesses against fake transports). E **never** proves P.
- **P** = actual Paper runtime observation — a real directive accepted by the
  Paper venue and a verified broker reality returned. `P = 0` today.

This runbook produces exactly **one** P record: the `LifecycleEvidence` returned
by a real `run_order_exercise_verification()` call, plus the broker-side reality
the run induces (order id, status, fills).

---

## 1. Exact command

Run from the repository root (`C:\Users\MewMew\Desktop\Co-op\Acash`).

```powershell
# Session: credentials must be exported into the SAME process environment.
$env:ACASH_ALPACA_API_KEY_ID = "<PAPER account key id>"
$env:ACASH_ALPACA_API_SECRET = "<PAPER account secret>"

uv run python -c "
from acash.execution.alpaca.order_exercise import run_order_exercise_verification
from decimal import Decimal

ev = run_order_exercise_verification(
    client_order_id='<COID>',   # operator-supplied, explicit
    symbol='<SYMBOL>',          # operator-supplied, explicit
    quantity=Decimal('<QTY>'),  # operator-supplied, explicit
)
print(ev)
print('P_OBSERVED', {
    'client_order_id': ev.client_order_id,
    'broker_order_id': ev.broker_order_id,
    'final_state': ev.final_state,
    'final_terminal': ev.final_terminal,
    'filled_qty': str(ev.filled_qty),
    'disputed': ev.disputed,
    'manifest_digest': ev.manifest and ev.manifest.execution_digest,
    'reconciliation_digest': ev.reconciliation_report and ev.reconciliation_report.report_digest,
    'is_in_parity': ev.reconciliation_report and ev.reconciliation_report.is_in_parity,
})
"
```

`run_order_exercise_verification()` internally builds
`PaperHttpAlpacaTransport(provider=paper_credential_provider(), endpoint=paper_endpoint())`
and drives the explicit nominal flow: **submit → acknowledge → full_fill**. All
state flows only through `ExecutionCoordinator`.

---

## 2. Pre-run environment checks (operational authorization)

Before running, ALL must hold — checked against the *effective runtime*, not
`.env.example`:

1. **Credential venue is Paper.** Confirm the exported
   `ACASH_ALPACA_API_KEY_ID` belongs to a **Paper** account (never a live key).
   `paper_credential_provider()` pins venue `ALPACA_PAPER`;
   `PaperHttpAlpacaTransport` L1b `assert_paper_venue()` rejects a live-scoped
   provider; `connect()` L2 `_assert_venue_match()` re-asserts credential vs
   endpoint venue **before** any HTTP client is built.
2. **Endpoint is Paper.** `paper_endpoint()` derives
   `https://paper-api.alpaca.markets/v2` (constant; no env host override).
3. **No live credential/host in effective config.** The committed entry
   (`order_exercise.py`, `run_order_exercise_verification`) references only
   `paper_credential_provider`, `paper_endpoint`, `PaperHttpAlpacaTransport`.
   Grep before run: no `LIVE_API_HOST`, `api.alpaca.markets` (live), or live key
   prefix in the invocation path.
4. **Order parameters explicitly approved** — symbol / quantity /
   client_order_id are caller-supplied and MUST be the operator-confirmed values
   (Section 7). `quantity` must be a positive, integer/step multiple accepted by
   Paper for the symbol.
5. **Paper account buyable** — the symbol must be tradeable in the Paper account
   and `quantity` within its buying power. Failures surface as `AlpacaTransportError`
   (fail-closed), never a fabricated terminal state.
6. **Runtime timeout equality (Section 4)** — assert the effective transport
   timeout matches the actual HTTP client timeout:

```powershell
uv run python -c "
from acash.execution.alpaca.transport import PaperHttpAlpacaTransport, HttpAlpacaTransport
from acash.execution.alpaca.credentials import paper_credential_provider
from acash.execution.alpaca.venue import paper_endpoint
import inspect

# Default chain: harness passes no timeout -> PaperHttpAlpacaTransport(10.0)
# -> HttpAlpacaTransport(10.0) -> httpx.Client(timeout=10.0).
assert HttpAlpacaTransport.__init__.__defaults__[0] == 10.0
t = PaperHttpAlpacaTransport(provider=paper_credential_provider(), endpoint=paper_endpoint())
print('EFFECTIVE_TRANSPORT_TIMEOUT', t._timeout)
assert t._timeout == 10.0
print('TIMEOUT_EQUALITY_OK :', True)
"
```

---

## 3. Expected Paper-domain observables

Nominal successful run:

- `client_order_id` echoed by the venue on the created order.
- `broker_order_id` = the venue-assigned order UUID (captured in
  `LifecycleEvidence.broker_order_id` and `ExecutionManifest.broker_order_id`).
- `final_state == "FILLED"`, `final_terminal is True`, `filled_qty == quantity`.
- `disputed is False`; `reconciliation_report.is_in_parity is True`.
- `ExecutionManifest.closed_at` set (verified terminal), `execution_digest` a
  64-hex sha256.
- `states_reached` includes `SUBMITTED, ACKNOWLEDGED, PARTIALLY_FILLED, FILLED`
  (the exact tuple depends on venue fill pacing; at minimum it must end at a
  verified `FILLED`).

These observables feed the **conjunctive P acceptance rule** (Section 8) —
`FILLED` alone is not P; it is only the terminal-state conjunct.

Any of these indicates a discrepancy to be treated per Section 6 —
never coerced to a terminal or "green" outcome:

- `disputed is True`, `final_state == "UNKNOWN"`, `closed_at is None`,
  `is_in_parity is False`, duplicate/late-event incidents, or a
  reconcile-token that does not match broker reality.

---

## 4. Timeout / abort behavior

**Effective timeout is the code default, verified from source** (not a runbook
preference). The committed chain is:

- `run_order_exercise_verification()` builds
  `PaperHttpAlpacaTransport(provider=…, endpoint=…)` with **no** `timeout`
  argument → the default applies.
- `PaperHttpAlpacaTransport.__init__(timeout: float = 10.0)` (`transport.py:513-531`)
  forwards `timeout=timeout` to `HttpAlpacaTransport`.
- `HttpAlpacaTransport.__init__(timeout: float = 10.0)` stores it as
  `self._timeout` (`transport.py:329-333`).
- `connect()` passes `timeout=self._timeout` to `httpx.Client(...)`
  (`transport.py:367-375`) → **actual HTTP client timeout = 10.0s**.

∴ `runbook timeout == effective transport timeout == actual HTTP client timeout
== 10.0s` by the default chain. A pre-run check (Section 2.6) asserts this
equality programmatically.

Timeout semantics (not just operational preference):

$$ \text{timeout} \rightarrow \text{CONNECTION\_LOST} \rightarrow \text{UNKNOWN} $$

- A timeout raises `AlpacaTransportTimeoutError` (fail-closed **ambiguity**, not
  a terminal guess); harness `connect()`/`submit` will propagate it and the order
  is treated as UNKNOWN — never CANCELLED/REJECTED/FILLED by assumption.
- Harness errors (`OrderExerciseError`) are reserved for ordering/usage mistakes.
- No silent retry, no silent floor, no fabricated parity.

---

## 5. How to identify the created order

- Primary: `broker_order_id` from the returned `LifecycleEvidence`.
- Cross-check in the Alpaca Paper UI / API: locate the order by
  `client_order_id` (unique on Paper), confirm venue = Paper, status = `filled`,
  symbol + qty match.
- The Paper account position screen must reflect `quantity` of `<SYMBOL>` after
  fill (if it was not already held).

---

## 6. How to reconcile afterward

Use a read-only follow-up (paper venue only):

```powershell
uv run python -c "
from acash.execution.alpaca.transport import PaperHttpAlpacaTransport
from acash.execution.alpaca.credentials import paper_credential_provider
from acash.execution.alpaca.venue import paper_endpoint

t = PaperHttpAlpacaTransport(provider=paper_credential_provider(), endpoint=paper_endpoint())
t.connect()
o = t.query_order('<BROKER_ORDER_ID>')
print('VENUE', t.endpoint.venue.value)
print('STATUS', o.status)
print('FILLED_QTY', o.filled_qty)
"
```

Reconciliation rule (from `state_machine.py` §2.3): an UNKNOWN shadow exits
toward a terminal **only** via `reconcile(...)` with an evidence token that names
the verified broker outcome. If the shadow is already terminal and broker reality
contradicts it, the coordinator records a `RECONCILIATION_CONFLICT` incident and
marks the execution disputed (no self-selection, never a regression). P is
recorded **only** when `LifecycleEvidence` shows a verified terminal + parity.

---

## 7. Order parameters (OPERATOR MUST CONFIRM — NOT SET BY ANTIGRAVITY)

These are caller-supplied to `run_order_exercise_verification` and are **not**
chosen by Antigravity, per security discipline:

| Field | Value | Confirmed by operator |
|-------|-------|-----------------------|
| `symbol` | `<SYMBOL>` | ☐ |
| `quantity` | `<QTY>` | ☐ |
| `client_order_id` | `<COID>` | ☐ |

Placeholder values (`<...>`) are NOT runnable. No wire activity occurs until the
operator fills these in AND grants go-ahead.

---

## 8. What exactly gets recorded as **P**

The single P artifact is the `LifecycleEvidence` returned by a **real** Paper
run (Section 1), plus the broker-side reality confirmed in Section 5/6. P is
**NOT** `final_state == "FILLED"` alone. Acceptance is the **conjunctive** rule:

$$ \boxed{P = \underbrace{\text{Terminal Verified}}_{\text{final\_state terminal} \land \text{closed\_at set}} \land \underbrace{\text{Evidence Lineage Complete}}_{\text{manifest + report digests present}} \land \underbrace{\text{Reconciliation Verified}}_{\text{is\_in\_parity}} \land \underbrace{\text{No Dispute}}_{\text{disputed == False}} } $$

Operationally, every conjunct must hold:

1. **Terminal Verified** — `final_terminal is True` and `ExecutionManifest.closed_at`
   is set (a terminal state is never asserted bare; it carries lineage).
2. **Evidence Lineage Complete** — `ExecutionManifest.execution_digest` and
   `ReconciliationReport.report_digest` are present (64-hex sha256), and the
   intent/manifest/report are bound.
3. **Reconciliation Verified** — `ReconciliationReport.is_in_parity is True`
   (single-order parity between internal shadow and broker reality).
4. **No Dispute** — `disputed is False`; no `RECONCILIATION_CONFLICT` /
   `UNKNOWN_RECONCILIATION` / late-event / duplicate anomalies against the
   terminal outcome.

If ANY conjunct is false (e.g. `FILLED` but `disputed is True`, or `FILLED` but
`is_in_parity is False`, or `closed_at is None`), the run is **NOT P** regardless
of the `final_state` string.

The accepted P record is:

- `P_OBSERVED` payload above (client_order_id, broker_order_id, final_state,
  final_terminal, filled_qty, disputed, manifest digest, reconciliation digest,
  is_in_parity).
- The `LifecycleEvidence` object itself (no secret material by construction:
  `credentials` env vars are redacted; `manifest`/`report` carry only hashes and
  the nominal intent — see the "NOT admission proof" caveat on
  `build_nominal_intent`).

Counter-evidence is NOT P:
- Unit/integration tests (E only).
- Fake-transport harness runs (E only).
- A run that ends UNKNOWN/disputed/aborted (that is a recorded E/incident, not P
  of a filled Paper lifecycle).
- Any run that fails even one conjunct above — `FILLED` with a dispute, a parity
  failure, or missing lineage is an incident, not P.

---

## 9. Emergency / abort procedure

Do **not** run until this section is approved.

1. **Immediate stop**: terminate the Python run (Ctrl-C / kill the process).
   The harness is fail-closed — no retry on interruption; the order is left
   UNKNOWN and must be resolved, not assumed.
2. **Identify the order** (Section 5). If a `broker_order_id` was already
   returned, find it in the Paper account by `client_order_id`.
3. **Stop the Paper order** (only if it is still working / not terminal):
   issue a cancel to Paper via the read-only/paper transport:
   `t.cancel_order('<BROKER_ORDER_ID>')` — a REQUEST, never a confirmation; then
   observe broker reality (canceled / filled / rejected) and reconcile
   accordingly. If already FILLED or non-cancellable, record truth and reconcile.
4. **Record the incident**: preserve the exception, any partial `LifecycleEvidence`,
   and the broker reality; mark this run as NOT-P (no fabricated parity).
5. **Do not re-submit** the same order blindly; confirm the abort reason first.

---

## 10. Authorization gate (this is NOT a run)

Execution of this runbook requires explicit operator sign-off on:
- the exact `symbol` / `quantity` / `client_order_id` (Section 7);
- the kill/stop procedure (Section 9);
- confirmation that the exported credentials are Paper-scoped (Section 2.1).

Until signed off, `run_order_exercise_verification()` must not be called and the
runbook is a **draft only**. `P` remains **0**.
