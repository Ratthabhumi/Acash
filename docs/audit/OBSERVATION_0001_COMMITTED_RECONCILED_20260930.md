# Observation #0001 Result & Adjudication Record — COMMITTED_AND_RECONCILED

**Date Context**: 2026-09-30 / 2026-10-01
**Target Session**: 2026-09-30
**Classification Authority**: Four-way post-run protocol
(`docs/SESSION_HANDOFF.md` §12)

---

## 1. Classification (Immutable)

```text
HYP_011_OBSERVATION_0001 = COMMITTED_AND_RECONCILED
TARGET_SESSION           = 2026-09-30
OBSERVATION_ORDINAL      = 1
DISPATCH_ATTEMPT         = 2
S1_PROGRESS              = 1/20
```

## 2. Service Evidence (Operator-Recorded Runtime Telemetry)

```text
SERVICE_RESULT   = SUCCESS
NRESTARTS        = 0
NETWORK_REQUESTS = 6
```

`ExecMainCode=1` is NOT an error: for systemd it means the process reached
`exited`; the true exit status is `ExecMainStatus=0` with `Result=success`.

`NETWORK_REQUESTS_ISSUED = 6` matches the frozen contract exactly:
ACWI / AGG / SPY × split / raw = 6 provider requests, with no automatic
Observation #2 dispatch.

## 3. Cryptographic Evidence (Operator-Recomputed, Independent)

```text
OBSERVATION_SHA256 =
ab5d164b2d97c1f5adc3f66d02b01dc560595fb6a5b67c4d006f17d642bfb9ed
STATE_SHA256 =
37ac485f0634aee752d383a3bbb195269dc90275d00115a7ed785266fd42b772
```

## 4. Reconciliation Evidence

29/29 independent reconciliation checks: **PASS**.
No temporary files left behind (`TEMP_FILES = NONE`).

## 5. Governance Boundaries (Unchanged by This Record)

```text
REAL_CAPITAL_AUTHORITY   = $0.00
PAPER_TRADING_AUTHORITY  = false
LIVE_TRADING_AUTHORITY   = false
NO_REAL_ORDERS           = true
OBSERVATION_0002         = NOT_AUTHORIZED
```

This record advances the sample clock to S1=1/20. It does NOT authorize
Observation #2, does NOT merge any branch, does NOT deploy any runtime, and
does NOT set any Obs #2 timer. Continuation requires the F01/F02/F09/F10/F14
gates plus explicit human continuation authorization.

## 6. Lineage Note

No synthetic copies of the production observation are committed alongside
this record. Hashes and telemetry above are recorded as evidence only; raw
production artifacts remain on the homelab host, byte-immutable and
untouched by the repair branch.
