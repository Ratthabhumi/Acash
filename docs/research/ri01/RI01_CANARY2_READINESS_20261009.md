# RI01 Canary 2: Prepared, Empirical Acquisition Not Authorized

Software checkpoint: runtime `cf63f15800099967f4c45d3df66e87a66a012eac` (isolated worktree), canonical main `1362395e8463be13a8e75a5d9ef07da660f56ade`.
This is an additive readiness checkpoint for historical depth qualification on session `2018-06-01`.
It preserves the historical [R1 design](RI01_PROBE_R1_DESIGN.md) and Canary 1 evidence.
It does **not** ratify network access.

## Candidate and contract

The exact [unissued candidate](RI01_CANARY2_UNISSUED_AUTHORITY.json) deliberately has an invalid authority prefix (`UNISSUED_`) and unresolved UTC windows (`null`).
The executable parser rejects it fail-closed.
An operator must approve a unique issued identity (`AUTHORIZE_RI01_PROBE_R1_CANARY2_...`), exact runtime SHA, resolved external unique root, and bounded future UTC window separately.

This JSON contains only fields accepted by `RI01ProbeAuthority.from_dict()`.
Review metadata (feed, timeframe, adjustment, start/end, expected grid and
proposed validity) stays in this document; do not copy it into executable JSON
or widen the parser. The root placeholder and null times must remain unresolved
until the operator approves the complete packet.

Do not create or reuse an occupied evidence root. Do not reuse Canary 1 authority, evidence root, or receipt.

- **Scientific Question**: Can the same account obtain and qualify historical SPY 1-minute SIP bars from 2018-06-01?
- **Scope**: SPY, session `2018-06-01`, historical 1Min SIP bars, raw adjustment, NYSE RTH `[2018-06-01T13:30:00Z, 2018-06-01T20:00:00Z)`, 390 distinct grid positions, request budget 3.
- **Locks**: `read_only=True`, `no_outcomes=True`, `no_paper=True`, `no_live=True`, `capital_usd=0.00`, `no_real_orders=True`.
- **Exclusions**: No returns, PnL, Sharpe, signals, predictive tests, lookahead, sealed 2023+ holdout, automatic retry, or missing-bar imputation.
- **Contract Boundary**: Alpaca request end is inclusive (`2018-06-01T20:00:00+00:00`); qualification selects exclusive-close RTH grid `[13:30, 20:00)`. A returned 20:00 bar is retained in raw bytes but excluded from qualified RTH bars.

## Observed evidence taxonomy

| Observation | Retrieval evidence | Qualification / interpretation |
|---|---|---|
| 200, exhausted pages, exact 390 grid | RETRIEVED | QUALIFIED |
| 200, no bars | RETRIEVED | DATA_UNAVAILABLE |
| 200, incomplete/duplicate/off-grid or invalid bar | Contract failure | Inspect actual raw evidence and qualification where emitted; never call covered |
| 401 | AUTHENTICATION_FAILED | Credential rejection; no entitlement inference |
| Generic 403 | ACCESS_FORBIDDEN | Reason unconfirmed |
| 403/422 + allowlisted code 42210000 or 40010001 + exact SIP restriction message | ENTITLEMENT_DENIED | Confirmed recent SIP subscription restriction only |
| Generic 422 or other non-200 | HTTP_FAILED | No detailed reason inferred |
| Invalid response structure/JSON | MALFORMED_RESPONSE where handled | Not qualified |
| RequestError, including timeout/connect/read | TRANSPORT_FAILED | Invocation initiated, provider acceptance UNKNOWN, no response observed |
| Pagination still incomplete at budget | PARTIAL | Stop; no automatic retry or budget extension |

Some per-bar corruption exceptions occur after writing raw pages but before a
terminal manifest or qualification. A raw-page-only run is **INCOMPLETE_EVIDENCE**,
never success. Preserve it; do not rerun or increase the budget automatically.

## Operator runbook (review only; network command not executed)

1. Explicitly authorize **only** this Canary 2 scope and budget.
   Use a clean isolated checkout pinned to `cf63f15800099967f4c45d3df66e87a66a012eac`.
   Do not pull or restart Homelab.
2. Review the resolved external root for repository collision, uniqueness, and empty state.
   The operator resolves a fresh absolute path outside every checkout, including
   symlink/junction collision checks. No machine-specific path is issued here.
3. Operator issues a unique `AUTHORIZE_RI01_PROBE_R1_CANARY2_...` ID and explicit UTC validity window (e.g. 20-minute window).
4. Run scope-only dry run (no HTTP):
   ```powershell
   uv run python -m acash.research.ri01.probe --session 2018-06-01 --capability bars
   ```
5. **Do not execute the pinned CLI directly.** Its request counter is per client;
   it may invoke HTTP on reuse before discovering an immutable page collision.
   Before approval, copy the reviewed `scripts/ri01_canary_single_use.py` as raw
   bytes to external operator storage; compute its literal SHA-256 with the
   existing `content_sha256`. Record external driver path/hash and the stable
   external claims directory in the operator review packet. Run that copy from
   the clean pinned checkout, using its pinned installed `acash` package.
   The driver and its imported runtime identities must both match the packet.
   Only after separate human network approval, execute:
   ```powershell
   uv run python $env:ACASH_CANARY2_DRIVER --execute-approved --authority-file $env:ACASH_CANARY2_AUTHORITY_FILE --claims-dir $env:ACASH_RI01_CLAIMS_DIR --expected-driver-sha256 $env:ACASH_CANARY2_DRIVER_SHA256
   ```
   This command is **UNEXECUTED**.
6. Preserve raw bytes and audit manifest, qualification, token chain, and exact 390 RTH grid with `require_complete_rth_grid`.
   Compare raw page hashes with literal bytes. A canonical JSON digest and a
   literal formatted-file SHA-256 are different quantities; verify each using
   its corresponding representation. Keep receipts and raw SIP data private.
   Stop after this session. Do not escalate to Canary 3 without separate authorization.

Readiness verdict: **CANARY2_AWAITING_OPERATOR_AUTHORIZATION**; real 2018 SIP
feasibility **UNVERIFIED**, network authority **UNISSUED**, live requests in this
task **0**. The scope-only dry run does not check credentials, validate an issued
authority, reserve a root, or establish complete execution readiness. Those
operator-specific checks remain pending until a resolved packet exists.

## Offline publication checks â€” 2026-10-11

- Remote main confirmed at `1362395e8463be13a8e75a5d9ef07da660f56ade`;
  PR #12 and #13 are merged. Historical main CI run `37793131851` is successful
  across all five jobs. A new review PR requires its own matching CI evidence.
- Existing isolated empirical checkout is clean and pinned to
  `cf63f15800099967f4c45d3df66e87a66a012eac`; its actual scope-only dry run
  for `2018-06-01`/bars reports `NETWORK_REQUESTS = 0`.
- Targeted RI-01, Canary 2 and V3 synthetic tests: **128 passed**. MyPy:
  **588 files clean**, with a configuration note for unused `nautilus_trader.*`.
  This note is optional dependency configuration debt, not a Canary 2 failure.
- Full repository CI-prescribed hermetic tier on Python 3.12.13:
  **3298 passed, 20 skipped, 56 deselected, 12 warnings**. Command:
  `uv run pytest -q --tb=line -m "not non_hermetic and not native_mt5 and not sealed_data and not dashboard" --ignore=tests/unit/execution/mt5`.
  Skipped/excluded checks are not certified. Two warnings concern the Nautilus
  dependency's deprecated `Timestamp.utcnow`; ten concern existing tar restore
  extraction behavior. They are dependency compatibility debt and an existing
  backup extraction security/compatibility caveat respectively; neither was
  suppressed or repaired in this publication-only change. Host symlink tests
  cannot run where Windows refuses link creation; Linux CI supplies separate
  platform coverage, not proof of a future operator root on Windows.
- Canary 1 evidence rechecked locally without network or modification:
  `2021-06-01`, one page/one recorded operation, 391 raw bars, 390 exact RTH
  timestamps. Raw hashes, token chain, canonical manifest/qualification bindings
  and preserved disk-audit digests match. Raw OHLC/volume contract checks pass.
  Canonical manifest digest differs from literal formatted-file SHA-256.
  This establishes bounded **DATA_FEASIBILITY_PASS**, never strategy validation.
- Credentials are present in the current process; no values were displayed or
  exported. No authentication, entitlement, or future secret injection was
  tested against the provider. A future operator process must check its own
  injection without printing values.
- Actual future authority ID, fresh evidence root and UTC validity remain
  unresolved. No Canary 2 root was allocated, no issued authority created, and
  no empirical provider request performed. Windows symlink coverage and other
  skipped checks must be disclosed with the full suite/CI results.
- HYP_011 V3 remains an offline proposal with deployment/activation unissued.
  A finite, preregistered dispatch rehearsal cannot prove future 100% uptime;
  no universal 99.9% gate is imposed by this review. Existing V2 authority and
  Homelab runtime are untouched. PPDS remains synthetic/read-only; no real
  statement, tax workflow, depth entitlement or options dataset is certified.


## Single-operation correction — 2026-10-11

The external driver creates exclusive persistent claims for authority identity,
canonical authority digest and resolved evidence-root identity, then an immutable
root start receipt **before constructing the HTTP client**. Existing identity
claims block a changed window/root under the same ID; an occupied or previously
claimed root blocks a different authority. Exclusive creation has one winner in
concurrent attempts. A crash or a failure after any claim consumes the attempt;
there is no rollback/retry or automatic budget/window extension.

All operators must use the same reviewed persistent claims directory. Never
switch registries, remove claims/receipts, empty evidence roots or replace the
reviewed driver to retry. This is a local operator procedure, not tamper-proof
cross-machine enforcement: deletion, a new unreviewed registry, or bypassing the
driver breaks its trust boundary. Such actions require a new explicit decision.
Canonical authority JSON still contains only accepted RI01 fields; claims and
driver identity are separate private audit artifacts. Keep raw data/paths and
receipts out of public Git. A start receipt proves local reservation, not provider
receipt or data qualification. It remains consumed after corruption/transport
failure. A fresh operation needs a separately approved identity/root, never a
rerun of the consumed authority.

Mock tests cover reuse across newly constructed clients, changed root/window
under the same identity, a new identity with an occupied root, partial crash
claims, driver-hash mismatch and competing exclusive writers. No pinned
`src/` implementation, economics, seal or runtime hash was modified.
