# RI-01 Provider Probe R1 — Design (HARNESS BUILT, NEVER EXECUTED)

**Status**: `CODE_PREPARATION_ONLY`. The harness in
`src/acash/research/ri01/probe.py` (13 hermetic mock-transport tests) has
NEVER touched a live endpoint and MUST NOT run before ALL of:

1. HYP_011 Observation #1 forensic check complete (2026-10-06 session),
2. a future single explicit network authority with a bounded scope,
3. execution from an ISOLATED worktree — never `/home/mew/Acash` while
   HYP_011 V2 is armed (that checkout's runtime SHA is pinned by the live
   timer; any branch switch there would fail V2 preflight itself).

## 1. Frozen scope

- Symbol: SPY only (hardcoded; anything else is rejected pre-network).
- Sessions (allowlisted, already-consumed or pre-holdout ONLY):
  - `2018-06-01` — early-depth regular session (390 min)
  - `2021-06-01` — normal later in-sample regular session (390 min)
  - `2021-11-26` — historical half-day (210 min)
- Hard holdout guard: any session ≥ 2023-01-01 is rejected BEFORE any
  network, even with a valid authorization.
- Capabilities: `bars` (1Min SIP raw, paginated to exhaustion, full-grid
  validated), `trades` (narrow ±5-min windows around open/close, exchange +
  conditions preserved).

## 2. What execution records (and only that)

Per session×capability: raw response bytes + JSON envelope (endpoint,
parameters, retrieved_at_utc, content SHA-256, rate-limit headers,
authorization string). Coverage statistics are the only quantitative output.
No returns, no PnL, no Sharpe, no hit-rate, no thresholds, no signal — the
module contains no price-arithmetic code path by construction.

## 3. Stability / revision-vintage plan (future, scheduled)

The envelope's `retrieved_at_utc` + content digest make a later re-fetch
comparable via `compare_stability()`. Revision-vintage evidence that needs
real time separation is a FUTURE SCHEDULED collection (re-run the same
bounded scope ≥30 days later, diff digests) — it is NOT faked by immediate
re-fetch, and it is NOT part of R1 execution.

## 4. Execution gate (all required, in order)

1. Dry-run first: scope validation, `NETWORK_REQUESTS = 0`.
2. Live requires `--execute-network` PLUS `--authorization
   AUTHORIZE_RI01_PROBE_R1_*` (shape-checked; the real string comes from the
   future authority, not from this document).
3. Entitlement failures (401/403) fail closed with NOTHING recorded.
4. Missing data is `DATA_UNAVAILABLE`; grid mismatches fail the session.

## 5. Explicit non-goals for R1

- No preregistration, no outcome evaluation, no parameter choices.
- No Evidence Kernel extraction (reuse assessment stands as documented).
- No PPDS ingestion, no broker orders, no capital, no Homelab changes.
