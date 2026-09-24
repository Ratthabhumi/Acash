# Phase 14 HYP_009: R2 Runner Boundary Correction (Additive)

```text
[CORRECTION RECORD: HYP_009 R2 PROVIDER RUNNER BOUNDARY + REQUEST AUDIT]
[ARTIFACT_ID: HYP_009_R2_RUNNER_BOUNDARY_CORRECTION]
[STARTING_GIT_SHA: a60acce766dea2cb4a31cc6cdcc5da9311f4721d]
[HYPOTHESIS_ID: HYP_009]
[CORE_ID: CORE-001]
[SCIENTIFIC_STATUS: UNMODIFIED / INTACT]
[STATE: READY_FOR_LIVE_PROVIDER_QUALIFICATION_NOT_EXECUTED]
[NETWORK_REQUESTS_ISSUED: 0]
[LIVE_PROVIDER_QUALIFICATION_PERFORMED: false]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/HYP_009_R2_RUNNER_BOUNDARY_CORRECTION.md`
- **Associated Manifest:** `docs/phase14/manifests/HYP_009_R2_RUNNER_BOUNDARY_CORRECTION.json`
- **Supersedes nothing; preserves lineage:** the prior readiness record
  `docs/phase14/HYP_009_R2_PROVIDER_IMPLEMENTATION_READINESS.md` and its
  manifest remain untouched as historical lineage.
- **Human Authorization:**
  `AUTHORIZE_CORE_001_HYP_009_R2_PROVIDER_RUNNER_BOUNDARY_CORRECTION`
  (narrow implementation correction only; live qualification NOT authorized).

---

## 1. External Audit Findings (Verified)

### Finding 1 — Provider end-bound could exclude the Nov-4 daily bar (blocking)

The runner constructed `end_utc = 2016-11-04T00:00:00Z`. Alpaca defines
start/end as timestamp bounds, and its own 1Day examples timestamp daily bars
after 00:00 UTC for the session date (e.g. `2022-06-09T04:00:00Z`). An end
boundary at exactly midnight could therefore exclude the legitimate 2016-11-04
daily bar and produce a false `FAIL_SCOPE_MISMATCH` against a correct
provider. **Confirmed against the a60acce runner source before editing.**

### Finding 2 — Request counter under-reported failed attempts (audit truth)

The runner incremented `network_requests_issued` only after a fetch returned
successfully. An issued HTTP request answered with 401/403/500 raises before
the increment, leaving the counter at 0 despite a real provider attempt.
**Confirmed against the a60acce runner source before editing.**

---

## 2. Corrections (This Workflow, Additive)

### 2.1 Provider timestamp-boundary correction

- Scientific session-date window **unchanged:** `2016-11-01 .. 2016-11-04`
  inclusive. No expansion to 2016-11-05.
- New deterministic helper
  `inclusive_date_window_to_utc_bounds(start_date, end_date)` in
  `src/acash/data/qualification/hyp_009_daily_client.py` (exported from the
  qualification package): inclusive start date -> UTC start-of-day
  (`00:00:00Z`); inclusive end date -> UTC end-of-day (`23:59:59.999999Z`).
- Runner now builds provider bounds through the helper:
  `start_utc = 2016-11-01T00:00:00Z`,
  `end_utc = 2016-11-04T23:59:59.999999Z`.
- Response spill validation is **not loosened**: any returned session date
  outside `2016-11-01..2016-11-04` is still rejected (unit-proven: a Nov-7
  session row against the corrected bounds raises provider-spill).
- Frozen HYP_009 date contract (`2016-01-01..2020-12-31`) still enforced by
  `Hyp009PreNetworkGuard` at fetch time; the helper itself is a pure
  converter.

### 2.2 Actual HTTP-attempt counting correction

- `HYP009AlpacaClient` accepts an optional `http_attempt_listener` callback,
  invoked once per **actual** `client.get` transport execution — first
  attempts, 429 retries, and pagination pages each count. The hook carries no
  credentials and performs no logging.
- The runner wires an `HttpAttemptCounter` through the listener and reports
  its value at every exit path (dry-run, blocked, scope-mismatch, pass,
  contract-violation), so failed responses are counted truthfully.
- No retry/pagination behavior changed; counting is purely observational.

### 2.3 Unit proofs added

Bounds mapping (start-of-day / end-of-day / inverted-window rejection);
Nov-4 `04:00:00Z` bar admitted under corrected bounds; Nov-session spill
still rejected; probe session set exactly Nov 1,2,3,4 via split+raw
alignment; counter cases — pre-network rejection 0, single-page success 1,
HTTP 401/403/500 exactly 1 each, two probes 2, 429-retry 2, two-page
pagination 2.

---

## 3. Scope Discipline (§5)

Unchanged: SPY / 1Day / SIP / SPLIT / RAW / probe sessions Nov 1-4 /
authorized boundary 2016-01-01..2020-12-31 / CA-1 calendar authority /
response validation / alignment rule. No M1 acquisition, no strategy
calculations, no P&L, no M2/M3/quarantine/prospective access, no HYP_007
empirical reads, no HYP_003 scientific modification, no HYP_003 runner
execution.

---

## 4. State & Boundary Invariants

```text
M2_ACCESS_COUNT = 0
M3_ACCESS_COUNT = 0
QUARANTINE_ACCESS_COUNT = 0
PROSPECTIVE_ACCESS_COUNT = 0
HYP_007_EMPIRICAL_READ_COUNT = 0
HYP_003_SCIENTIFIC_FILES_MODIFIED = NO
HYP_003_RUNNER_EXECUTED = NO
NETWORK_REQUESTS_ISSUED = 0
LIVE_PROVIDER_QUALIFICATION_PERFORMED = false
PAPER_AUTHORIZED = false
LIVE_AUTHORIZED = false
CAPITAL_AUTHORITY_USD = 0.00
NO_REAL_ORDERS = true
```

Live provider qualification requires separate authorization:
`AUTHORIZE_CORE_001_HYP_009_R2_LIVE_PROVIDER_QUALIFICATION`.

---

## 5. Manifest Digests (Verification)

| Artifact | Digest |
| :--- | :--- |
| Manifest canonical payload (`canonical_payload_sha256`, repo convention) | `b1a2d429480a86a1031e26482434d93b2efa26d578f09d724dc36e52068a7c84` |
| Manifest file `docs/phase14/manifests/HYP_009_R2_RUNNER_BOUNDARY_CORRECTION.json` | `b654fe3359878ab60115b276eb01de3934279dba2d2e18c13a582d8fbfc0f3d3` |

Recompute with `CanonicalConfigSerializer.compute_sha256` over the manifest
payload (excluding the hash field) and `sha256sum` over the file bytes.
