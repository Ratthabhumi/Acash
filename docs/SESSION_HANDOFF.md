# ACASH SESSION HANDOFF — V2 MERGED → D1-D5 RATIFIED → D4 PASS → D5 CLOSED (ACCEPTED WITH EXCEPTION)
## Canonical Current Session Handoff — 2026-09-17

> [!CAUTION]
> **VERIFY CURRENT REPOSITORY, RUNTIME, JOURNAL, AND GOVERNANCE STATE BEFORE ACTING.**
> This document is a navigation snapshot, not eternal source of truth.
> Always `git fetch origin`, verify full 40-char SHAs, and re-inspect
> container/journal state before any consequential action.

> **Document:** `docs/SESSION_HANDOFF.md`
> **This is the single canonical ACASH session handoff.**
> For the archived E3.6 historical checkpoint, see `E3.6-SESSION-HANDOFF.md`.
> **Date:** 2026-09-17 (UTC)
> **Status labels used:** FACT | EVIDENCE | INFERENCE | DEFECT | GOVERNANCE BOUNDARY | NEXT ACTION

---

## 0. Current Operator Checkpoint — 2026-09-17

> [!IMPORTANT]
> **D5 IS CLOSED (ACCEPTED WITH EXCEPTION). Read this checkpoint before acting.**

| Gate | State |
|---|---|
| D1 `CASH_CONSTRAINED_SPOT` | **RATIFIED + WIRED END-TO-END** (`4b2269d`) |
| D2 `HALT_AND_REQUIRE_OPERATOR_RESOLUTION` | **RATIFIED + WIRED END-TO-END** (`4b2269d`) |
| D3 `NAV_RELATIVE_PERCENT` 10% | **RATIFIED + WIRED END-TO-END** (`4b2269d`) — all slots incl. injected A |
| D4 10-slot capacity drill | **COMPLETE / PASS** (2026-09-16, `acash:shadow-v2-4b2269d`) |
| D5 3-slot 24h Shadow V2 | **CLOSED — ACCEPTED WITH EXCEPTION** (2026-09-17; finalization fix verified at `fd5a35d`) |
| Dashboard backend routing | **TEMPORARY workaround active; permanent fix deferred to next milestone** |
| Feed recovery (D5) | EXPLICIT OPT-IN, Shadow-only, bounded (5/2,5,10,20,30/2s/90s), restart policy `no` |

**FACT — Repository:** `origin/main = fd5a35d82bc5b7510ecf84590ed9d36f2041b025`
(verified 2026-09-17). Contains surgical finalization fix for RISK_HALTED runners.

**FACT — D5 Attempt 1 runtime:** container `acash-shadow-v2-d5-24h`, tournament
`SHADOW-20260916_000715_849306fb`, 3 INFRA_TEST slots A/B/C, `acashCommitSha =
4b2269d49cc36be94d4f7fb93a8b5e120a292cf6`, `noRealOrders=true`, capital $0.
Completed full 24h wall-clock container lifecycle; ~21h active execution before
all slots entered fail-closed RISK_HALTED on MAX_DAILY_LOSS. Missing snapshots/manifests
traced to shutdown lifecycle skip bug, which is now fixed and closure-verified.

**FACT — Homelab Closure Verification:** Image `acash:shadow-v2-fd5a35d`
(`sha256:5e78425de64e7d2ccb8e8bb63a4c8ee54e284eca1e1b3a44b505badafe4f565f`),
verified exactly 1 journal, 1 snapshot, 1 manifest (sealed, PASS/PASS), terminal reason
`RISK_KILL_SWITCH`.

**HUMAN DECISION:** No second 24h rerun required. D5 closed as ACCEPTED WITH EXCEPTION.

**GOVERNANCE BOUNDARY — unchanged:** HYP_003 NOT CREATED, R1 NOT STARTED,
Backtesting LOCKED, Paper NOT AUTHORIZED, Live LOCKED, capital $0.00,
`NO_REAL_ORDERS=true`, SHADOW-only.

**NEXT ACTION:** Address permanent dashboard backend routing fix; align with human
operator on next authorized milestone (D5 closure does NOT auto-unlock trading/research gates).

---

## 1. ACASH Repository — Current State

| Item | Value |
|---|---|
| Repository | `Ratthabhumi/Acash` |
| Active branch | **`main`** |
| Current main / HEAD = `origin/main` | **`fd5a35d82bc5b7510ecf84590ed9d36f2041b025`** (verify with `git rev-parse HEAD`) |
| Tip commit message | `fix(shadow): finalize risk-halted runners on shutdown` |
| Feature branch | `feat/tournament-v2-risk-remediation-10slot` — merged to `main` |
| Base before V2 merge | `9a58ced5011e15c7bcf3975f0e83acf339fa53ce` |

**FACT:** `origin/main == fd5a35d82bc5b7510ecf84590ed9d36f2041b025` as of 2026-09-17.
V2 remediation + V2 follow-up hardening + operator ratification + V2 CLI routing +
runtime-policy wiring + RISK_HALTED finalization fix were merged to `main` and pushed.

**MERGED COMMIT CHAIN (26 commits, base → tip, all full SHAs):**

| # | Commit | Scope |
|---|---|---|
| 1 | `ad6642fb5dd9f65c406194daacd3b31a0953f40d` | docs: H01 Attempt 1 evidence preserved, H01 closure recorded (EXIT=2, ReadTimeout) |
| 2 | `260d32b56668a6d99d1e120e2fa2096b4d4ca350` | fix(paper): enforce `MAX_NOTIONAL` + preserve terminal reason (Defects A & E) |
| 3 | `c4651ac82fba8e2a382dd01b3ab0248cc2a042e4` | feat(paper): funding + kill-switch position policies + granular execution states (Defects B, C & D) |
| 4 | `24d5607b380e033015365b60b9e71f29cc76d4af` | feat(paper): parameterize slot fanout for N-slot tournament (V2 10-slot readiness) |
| 5 | `b169d272d320217996f1dc6b7208a8677db26b65` | feat(paper): add 10-slot infrastructure candidate catalog with explicit auto-mount opt-in |
| 6 | `139ac62c18fa95621f5685d8a131650b0fff2d40` | feat(dashboard): align V2 10-slot contract, granular execution states, `SHADOW_RUNTIME` data source |
| 7 | `56160de912d9f49e7e56bad70a46d216b883f1dc` | test(paper): prove 10-slot layout state isolation (independent journals, hashes, portfolios) |
| 8 | `3787cd06fff7423b2e6f4e8efd93051c52d6d808` | docs(tournament): record V2 10-slot design + validation evidence |
| 9 | `706168ce3ce19ee85bbc281b484bf9ba0d4d6645` | feat(paper): journal event kinds + re-entrant lock integrity + feed-health recovery metrics |
| 10 | `48aeeec942218f42f7c3d956cecddc9f1724cbd1` | feat(paper): transient feed recovery + staged dynamic candidate admission + safe NAV sizing |
| 11 | `d86eca535bf06be105265496df36641897d1d75a` | test(paper): transient recovery, dynamic candidate admission, and safe sizing suites |
| 12 | `3aea870668be764b03b0c80bac079a79bdf0cd3c` | feat(dashboard): FEED_RECOVERING seat, cohort provenance, null-rank leaderboard |
| 13 | `df1bafa341dec0a38a1abcc9e2f7d8a467083511` | docs(tournament): record transient recovery, dynamic admission, and safe sizing design + evidence |
| 14 | `db908b57becc8ab3ea514416cc5f25e30faa22c4` | docs: refresh session handoff with V2 follow-up evidence (recovery / dynamic admission / sizing) |
| 15 | `536e84ebe49fde515c6a93c3929181e674e2313b` | fix(shadow): make feed recovery explicit opt-in and bounded |
| 16 | `045eb4aab81ce181bbafe64ca9eca70a1ffee284` | fix(shadow): strict recovery CLI validation and symmetric auto-mount |
| 17 | `7c01998310b972b8c2c9d020ee14d7874a137043` | test(shadow): cover bounded recovery and CLI flag contracts |
| 18 | `f95670793ae9540767ca3e84907112a7715f7739` | docs(tournament): record final recovery hardening evidence |
| 19 | `173cc81bbff3d19bbc5f608da90b52e770bbfba8` | fix(shadow): reject non-finite recovery timing values at CLI and config layers |
| 20 | `8db9bf5fa1ac6cb276f7ca38ea9c93afba566e03` | docs(tournament): record numeric hardening evidence in validation ledger |
| 21 | `243412d36592fc57a8801dade8579b6e2ff713a5` | docs: record V2 operator ratification D1-D5 |
| 22 | `a79e0c70d63bd8142bbcd3d4b626f4624d74be8a` | docs: refresh session handoff with V2 merge, D1-D5 ratification, and Homelab blocker |
| 23 | `938b4a46332e1fdfe8ea924689044fe05839ed14` | fix(shadow): route paper tournament command to V2 CLI |
| 24 | `4b2269d49cc36be94d4f7fb93a8b5e120a292cf6` | fix(shadow): wire ratified V2 runtime policies end to end |
| 25 | `fd5a35d82bc5b7510ecf84590ed9d36f2041b025` | fix(shadow): finalize risk-halted runners on shutdown |

> Verify the final SHA with `git rev-parse HEAD` — never trust a hard-coded tip.
> Tip commit `fd5a35d` fixes the RISK_HALTED shutdown lifecycle finalization defect,
> introduces PaperSessionRunner stop idempotency, and seals manifests for risk-halted slots.

**VERIFY, do not assume.** Run `git fetch origin` and `git rev-parse origin/main` at start of
every session.

---

## 2. Pi Personal Infrastructure — Current State

| Item | Value |
|---|---|
| Repository | `Ratthabhumi/Pi_Personal-Infrastructure` |
| Current main | `3ce27f09e742768633c23a5d0746a004bc3a1727` |
| Dashboard pin deployed | `acash-dashboard:ec86a85` |
| Shadow runtime (D4 / D5 Attempt 1) | `acash:shadow-v2-4b2269d` (replaces historical `acash:shadow-tournament-bb6d49c`) |
| Shadow runtime (D5 closure smoke) | `acash:shadow-v2-fd5a35d` (`sha256:5e78425de64e7d2ccb8e8bb63a4c8ee54e284eca1e1b3a44b505badafe4f565f`) |

**FACT:** The D4 capacity drill and the D5 24h Attempt 1 run both used the Homelab-hosted
image `acash:shadow-v2-4b2269d`. The subsequent short closure smoke verifying the RISK_HALTED
finalization fix used `acash:shadow-v2-fd5a35d`. The historical `bb6d49c` H01-era tag remains preserved.

**VERIFY** Pi main and deployed image tags at start of next session before any Pi action.

---

## 3. Immutable Governance Boundaries

> [!IMPORTANT]
> These boundaries are HARD LOCKS. No agent, audit, or session result changes them
> without explicit human authorization.

| Boundary | State |
|---|---|
| HYP_003 | NOT CREATED |
| R1 | NOT STARTED |
| Backtesting | LOCKED / NOT AUTHORIZED |
| Paper Trading | NOT AUTHORIZED |
| Live Trading | LOCKED |
| Canonical Capital | $0.00 |
| NO_REAL_ORDERS | true |
| Automatic Feed Reconnect | DISABLED (controlled Shadow recovery is EXPLICIT OPT-IN only — currently active for the D5 run) |
| Operator Resume | REQUIRED |
| Shadow Tournament | SIMULATED / INFRASTRUCTURE-TEST ONLY |
| Dashboard | READ ONLY |
| Public Internet Exposure | DISABLED |
| Automatic Code Sync | DISABLED |

**Do NOT:**
- Create HYP_003
- Authorize Paper or Live
- Unlock backtesting
- Introduce real capital or real broker execution
- Introduce auto-reconnect
- Restart H01 automatically

---

## 4. H01 Shadow Tournament — Current Runtime State

### 4.1 Tournament Identity

| Item | Value |
|---|---|
| Tournament ID | `SHADOW-20260914_073303_142fd6e0` |
| Runtime image | `acash:shadow-tournament-bb6d49c` |
| Runtime ACASH commit | `bb6d49c41fefef42c288ebdfce597572433423f9` |
| H01 start (UTC) | 2026-09-14 07:33:03 UTC |
| H01 start (Asia/Bangkok) | 2026-09-14 14:33:03 |
| First nominal 24h checkpoint (UTC) | 2026-09-15 07:33:03 UTC |
| First nominal 24h checkpoint (Asia/Bangkok) | 2026-09-15 14:33:03 |

### 4.2 Container Safety State (FACT — observed during session)

| Item | Observed Value |
|---|---|
| Container status | running |
| Health | healthy |
| RestartCount | 0 |
| Feed | HEALTHY |
| Canonical capital | $0 |
| realOrderCount | 0 |
| noRealOrders | true |
| NO_REAL_ORDERS env | true |
| Slot A | RUNNING |
| Slot B | UNASSIGNED |
| Slot C | UNASSIGNED |

> [!IMPORTANT]
> The above is the **mid-run observation**. See §4.4 for the **terminal** state:
> the container subsequently exited `EXIT=2` on a feed ReadTimeout after ~7h36m54s.

### 4.3 Revised H01 Status Classification

> [!CAUTION]
> Do NOT write "H01 GREEN". The correct classification is below.

| Dimension | Status |
|---|---|
| H01 infrastructure/feed continuity | **FAIL — 24h NOT ACHIEVED (EXIT=2 at ~7h36m54s)** |
| H01 dashboard/telemetry | **PASS** |
| H01 real-order safety | **PASS** |
| H01 execution-risk semantics | **FAIL — remediation required** |
| H01 execution-chain qualification | **NOT ACCEPTABLE AS FULL PASS UNTIL RISK DEFECTS ARE REMEDIATED** |
| H01 run lifecycle | **CLOSED** (no auto-restart; operator+human decision required for next run) |

**GOVERNANCE BOUNDARY:** This FAIL finding does NOT imply any real-money loss.
Everything remains simulated-only. Canonical real capital remains $0.

### 4.4 Terminal State — Attempt 1 (FACT)

| Item | Value |
|---|---|
| Container start (UTC) | 2026-09-14T07:33:01Z |
| Container finish (UTC) | 2026-09-14T15:09:55Z |
| Approx runtime | 7h36m54s |
| Exit code | `EXIT=2` |
| Final failure | `BinancePublicKlinesFeed.poll_next_bar` `ReadTimeout` → fail-closed halt |
| 24h continuity | NOT ACHIEVED |
| Final journal | 156814 bytes; SEQ 146 `RECONCILIATION_COMPLETED` PASS (146 events, 15 orders, 15 fills, 0 violations) |
| Terminal event | SEQ 147 `SESSION_STOPPED reason=NORMAL_SHUTDOWN` (⚠ causal reason NOT preserved — Defect E) |

**EVIDENCE PRESERVATION:** Full evidence archived at
[`docs/tournament/H01_ATTEMPT1_EVIDENCE.md`](tournament/H01_ATTEMPT1_EVIDENCE.md).
Artifacts on Host: `/data/docker/acash/tournament/`.

### 4.5 Tournament V2 Remediation — COMPLETED (EVIDENCE)

| Item | Value |
|---|---|
| Branch | `feat/tournament-v2-risk-remediation-10slot` — **MERGED to main** |
| Defects addressed | A (`MAX_NOTIONAL`), B (funding policy), C (kill-switch policy), D (execution states), E (terminal reason) |
| V2 readiness | N-slot fanout A..Z (1–26), 10-slot INFRA_TEST catalog, 10-slot isolation proven |
| V2 follow-up | transient feed recovery seat (FEED_RECOVERING), staged dynamic candidate admission (SIGHUP / candidate-add file), safe NAV-relative sizing (10% cap), journal re-entrant lock fix |
| Runtime-policy wiring (Fix 2) | `--portfolio-funding-policy`, `--kill-switch-position-policy` CLI flags; D1/D2/D3 threaded into every slot `PaperSessionConfig`; injected/slot-A sizing honors explicit NAV choice; per-slot `effectivePolicies` provenance in status |
| Local test suite | **2408 passed / 1 skipped** (full `uv run pytest tests/`) |
| MyPy | **424 source files clean** (`uv run mypy src/ tests/`) |
| Dashboard | `npm run typecheck` clean; node contract tests **27/27**; production build clean |
| Merge state | ff-only merged and pushed to `main` @ `4b2269d49cc36be94d4f7fb93a8b5e120a292cf6` |
| Deployment state | **DEPLOYED** to Homelab as `acash:shadow-v2-4b2269d` — D4 drill ran on it, D5 24h run is using it now (§4.7, §4.8) |
| Paper/Live | NOT AUTHORIZED |

**Design/validation records:** `docs/tournament/TOURNAMENT_V2_10SLOT_DESIGN.md` and
`docs/tournament/TOURNAMENT_V2_VALIDATION.md`.

### 4.6 V2 Follow-up Session Summary (EVIDENCE)

Controlled transient feed recovery (shadow only — **Automatic Feed Reconnect
DISABLED BY DEFAULT**; the runtime only ever recovers when the operator passes
`--enable-feed-recovery`), staged dynamic admission of INFRA_TEST candidates
with cohort provenance and null-rank single-member cohorts, and NAV-relative
sizing bounded to 10% of virtual equity. During a recovery episode the slot
emits **zero** new simulated orders/signals; a failed recovery halts with
`FEED_RECOVERY_FAILED` (causal reason preserved) and exit code 5.

**Final recovery hardening (YELLOW-item closure, 2026-09-15):**
- Recovery CLI default is **OFF** (`--enable-feed-recovery` is the single
  canonical positive opt-in; the inverted `--disable-feed-recovery` was removed).
- Backoff indexing corrected to a single authority
  `backoff_delay_seconds(attempt_no, backoff)` — attempt 1 sleeps the first
  backoff entry, journaled `backoff_seconds` equals the actual sleep, and the
  terminal attempt sleeps nothing.
- Bar-wait is bounded by a monotonic deadline `bar_wait_timeout_seconds`
  (default 90.0, `--recovery-bar-wait-timeout-seconds`) — a `BAR_WAIT_TIMEOUT`
  consumes that attempt's retry budget and applies backoff; never unbounded.
- Strict CLI validation (`max_attempts >= 1`, poll interval `>= 0`, bar-wait
  `> 0`, backoff `> 0`) replaces the silent `max(1, ...)` clamp.
- `--auto-mount-infra-candidates` is symmetric (`BooleanOptionalAction`,
  default `True` = default operational layout exercises the 3-slot INFRA_TEST
  layout); `--no-auto-mount-infra-candidates` runs slot-A-injected alone and
  must NOT silently create catalog candidates. Auto-mount is not alpha
  authorization.

- Strict float validators now also reject **non-finite** IEEE-754 values
  (`NaN`/`+Inf`/`-Inf`) at both the CLI layer (`_positive_float`,
  `_non_negative_float`, `_parse_backoff_seconds`) and the config layer
  (`FeedRecoveryConfig.__post_init__`, DataContractError), closing the
  non-finite timing hole that could poison `monotonic() + bar_wait_timeout`.

New/updated suites after hardening and Fix 2 (runtime-policy wiring):
`test_feed_recovery.py` (32), `test_dynamic_candidate_add.py` (15),
`test_safe_sizing.py` (19), `test_v2_cli_options.py` (42),
`tests/unit/paper/test_v2_runtime_policy_wiring.py` (6 collected as part of the
paper suite; full suite totals after Fix 2: **2408 passed / 1 skipped**).

**HUMAN DECISIONS D1–D5 = RATIFIED** (2026-09-15, updated 2026-09-16). See
`docs/tournament/V2_OPERATOR_RATIFICATION_20260915.md` and §11.
D1=CASH_CONSTRAINED_SPOT, D2=HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
D3=NAV_RELATIVE_PERCENT 10%, D4=10-slot capacity drill AUTHORIZED and now
**COMPLETE / PASS** (2026-09-16, see §4.7),
D5=3-slot 24h Shadow V2 AUTHORIZED **only after D4 PASS** — D5 is now
**RUNNING and NOT yet classified PASS** (see §4.8).

---

### 4.7 D4 Capacity Drill — COMPLETE / PASS (EVIDENCE, 2026-09-16)

**D4 = 10-slot V2 Homelab capacity drill, CLASSIFIED PASS.**

| Item | Value |
|---|---|
| Image tag | `acash:shadow-v2-4b2269d` |
| Image ID | `sha256:f0f62153faa3a7a5b7161a9d5ea28dd8712fd44a78356e92c372380c48398bae` |
| Exact ACASH commit | `4b2269d49cc36be94d4f7fb93a8b5e120a292cf6` |
| Slots | **10, concurrent — A through J, all `RUNNING` during the drill** |
| Slot A strategy | `INFRA-TEST-MOMENTUM-SYNTHETIC-001` |

**Effective policies observed on ALL slots during D4:**

| Policy field | Effective value |
|---|---|
| `portfolioFundingPolicy` | `CASH_CONSTRAINED_SPOT` (D1) |
| `killSwitchPositionPolicy` | `HALT_AND_REQUIRE_OPERATOR_RESOLUTION` (D2) |
| `signalSizingPolicy` | `NAV_RELATIVE_PERCENT` (D3) |
| `navSizingNotionalPct` | `10` (D3) |

**Safety state held throughout D4 (FACT):**

| Item | Value |
|---|---|
| `canonicalCapitalUsd` | `0.0` |
| `realOrderCount` | `0` |
| `noRealOrders` | `true` |
| `feedHealth` | `HEALTHY` |

**Terminal result (FACT — operator-recorded runtime evidence):**
- Ran through **T+900 seconds** and was **gracefully stopped**.
- Final container state: **ExitCode=0, RestartCount=0, OOM=false**.
- Final artifacts: **manifests=10, journals=10, snapshots=10**.

**GOVERNANCE BOUNDARY — What D4 PASS unlocks:**
- D4 PASS unlocked **previously ratified D5 only** (3-slot 24h Shadow V2 infra-test run).
- It did **NOT** authorize Paper, Live, backtesting, HYP_003, R1, broker
  connectivity, or any real capital.

---

### 4.8 D5 Shadow V2 Run — CLOSED (ACCEPTED WITH EXCEPTION)

> [!IMPORTANT]
> **D5 Attempt 1 is CLOSED as ACCEPTED WITH EXCEPTION.**
> Full 24h container/wall-clock lifecycle was achieved (~21h active execution before expected
> fail-closed RISK_HALTED on MAX_DAILY_LOSS). Missing snapshots/manifests were traced to a
> shutdown lifecycle finalization defect, which was surgically remediated in `fd5a35d` and
> closure-verified via a Homelab smoke test. Per Human Decision: no 24h rerun required.

| Item | Value |
|---|---|
| Classification | **ACCEPTED WITH EXCEPTION** (Human Decision 2026-09-17) |
| Container | `acash-shadow-v2-d5-24h` |
| Storage (Preserved) | `/data/docker/acash/shadow-v2-4b2269d-d5-24h` (DO NOT touch, move, or overwrite) |
| Attempt 1 Image | `acash:shadow-v2-4b2269d` (commit `4b2269d49cc36be94d4f7fb93a8b5e120a292cf6`) |
| Tournament ID | `SHADOW-20260916_000715_849306fb` |
| Tournament start (UTC) | `2026-09-16T00:07:16.204711+00:00` |
| 24h Wall-Clock completion | `2026-09-17T00:07:16Z` (gracefully stopped by watchdog `docker stop --timeout 20`) |
| Container terminal state | ExitCode=0, RestartCount=0, OOM=false |
| Active execution duration | Approximately 21h before all slots (A/B/C) entered RISK_HALTED on MAX_DAILY_LOSS |
| Safety boundaries | `canonicalCapitalUsd=0.0`, `realOrderCount=0`, `noRealOrders=true`, capital $0 |
| Active slots | Exactly 3 INFRA_TEST slots (A: fast/slow 3/5, B: 4/6, C: 5/7) |

**FACT — D5 Attempt 1 Evidence & Risk Semantics:**
- All three slots correctly halted on `MAX_DAILY_LOSS` fail-closed limit per ratified D2 policy (`HALT_AND_REQUIRE_OPERATOR_RESOLUTION`).
- This was expected fail-closed risk policy execution, NOT an infrastructure crash or feed instability.
- In Attempt 1, `status.json` correctly reflected `operatorResolutionRequired=true` and slots in `RISK_HALTED`.
- However, final manifests (0) and daily snapshots (0) were missing because `ShadowTournamentSupervisor.halt()` skipped slots not in `(RUNNING, FEED_RECOVERING)`, omitting `runner.stop()` for already-halted slots.

**FACT — Defect Remediation (`fd5a35d`):**
- Commit: `fd5a35d82bc5b7510ecf84590ed9d36f2041b025` (`fix(shadow): finalize risk-halted runners on shutdown`).
- Root cause: Supervisor shutdown loop checked presentation status rather than lifecycle status, skipping unfinalized runners.
- Fix: Loop checks `slot.runner is None or not slot.runner.is_started or slot.runner.is_finalized`. RISK_HALTED status and reason provenance are preserved; causal terminal reason `TerminalReason.RISK_KILL_SWITCH` is propagated. PaperSessionRunner `stop()` is made strictly idempotent.
- Local verification: Full repository suite **2418 passed, 1 skipped**; MyPy clean on **425 source files**.

**FACT — Homelab Closure Verification (`acash:shadow-v2-fd5a35d`):**
- Deployed Image: `acash:shadow-v2-fd5a35d` (Image ID: `sha256:5e78425de64e7d2ccb8e8bb63a4c8ee54e284eca1e1b3a44b505badafe4f565f`).
- Short Homelab closure smoke executed to test risk-halt finalization on Docker.
- Produced exact artifacts:
  - 1 journal (`.journal.jsonl`)
  - 1 snapshot (`.snapshots.jsonl`)
  - 1 sealed manifest (`.manifest.json`)
  - 1 `status.json`
- Manifest verification:
  - `final_reconciliation_status=PASS`
  - `journal_integrity_status=PASS`
  - `no_real_orders=true`, `simulated_fills_only=true`
  - `git_commit=fd5a35d82bc5b7510ecf84590ed9d36f2041b025`
- Journal verification:
  - Exactly one `SESSION_STOPPED` event with `reason=RISK_KILL_SWITCH`.
- The RISK_HALTED finalization defect is thus closure-verified on the Homelab Docker environment.

**CAVEAT — Smoke Harness Wrapper Observation:**
- The temporary Python smoke wrapper script exited non-zero because its internal assertion assumed a specific session-id filename format for the journal.
- The actual runtime artifacts were produced cleanly, validated independently, and verified with PASS reconciliation and PASS integrity.
- This was an assertion bug in the ephemeral test harness, NOT an ACASH runtime or finalization failure.

**HUMAN DECISION (2026-09-17):**
- No second 24-hour D5 rerun is required.
- D5 is formally closed as **ACCEPTED WITH EXCEPTION** (not an unqualified PASS).
- D5 Attempt 1 evidence directory (`/data/docker/acash/shadow-v2-4b2269d-d5-24h`) is permanently preserved as evidence.

**GOVERNANCE BOUNDARY:** D5 closure does NOT authorize HYP_003, R1, Paper, Live, backtesting, real capital, or broker connectivity. These remain strictly locked.

---

### 4.9 D5 Watchdog (FACT — Historical Execution)

| Item | Value |
|---|---|
| Watchdog script | `/tmp/acash-d5-watch.sh` |
| Execution | Monitored D5 container through full 24h wall-clock run; issued graceful `docker stop --timeout 20` at endpoint |
| Restarts | 0 (restart policy `no` enforced throughout) |

---

### 4.10 Dashboard Routing Observation (FACT — temporary, cleanup deferred)

| Item | Value |
|---|---|
| Dashboard URL (Tailscale/private) | `https://homelab.tail35e4b4.ts.net/acash/` |
| Initial symptom | Frontend reachable but Shadow API returned **HTTP 502** |
| Root cause | Backend hostname mismatch — dashboard Nginx expects `acash-shadow:9103` while the D5 container is named `acash-shadow-v2-d5-24h` |
| Verified working path | Direct: `http://acash-shadow-v2-d5-24h:9103/api/shadow/status` returned live Shadow runtime JSON |
| Workaround | Temporary Docker network alias restored the dashboard |

**FACT / GOVERNANCE BOUNDARY:** The dashboard routing fix is **temporary**.
The permanent cleanup (intended stable network alias or configurable backend
hostname) is **deferred until AFTER D5 completes**. Do **not** alter the D5
evidence run merely to clean up dashboard routing.

---

## 5. Slot A Strategy

| Item | Value |
|---|---|
| Strategy name | `INFRA-TEST-MOMENTUM-SYNTHETIC-001` |
| Version | 1.0.0 |
| Class | `InfrastructureTestStrategy` |
| Governance classification | `INFRASTRUCTURE_TEST_STRATEGY_ONLY` |

**Algorithm (FACT):**
- SMA fast = 3 bars, SMA slow = 5 bars
- SMA fast > SMA slow -> LONG signal
- SMA fast < SMA slow -> SHORT signal
- Target quantity = 1.0 BTC per non-flat signal

**This strategy is explicitly NOT:**
- HYP_003
- Alpha qualification
- ACASH research evidence
- Backtest authorization
- Paper authorization
- Live authorization

Its sole purpose is infrastructure exercise:
Signal -> Risk -> Order -> Simulated Fill -> Portfolio -> Journal -> Replay / Observability.

---

## 6. H01 Audit Evidence

### 6.1 Journal Location and Size

| Item | Value |
|---|---|
| Journal path | `/data/docker/acash/tournament/SHADOW-20260914_073303_142fd6e0_slot_a.journal.jsonl` |
| Observed size | 154847 bytes |
| Mode | 644 |

**EVIDENCE — Audit event counts (observed in journal snapshot):**

| Event type | Count |
|---|---|
| TOTAL_EVENTS | 146 |
| KILL_SWITCH_TRIGGERED | 1 |
| RISK_APPROVED | 15 |
| RISK_REJECTED | 4 |
| FILL_SIMULATED | 15 |
| POSITION_UPDATED | 15 |

Maximum observed absolute position: **10.0 BTC**
Current observed open position (dashboard/API): **LONG 9.0 BTC**

### 6.2 Runtime Metrics (EVIDENCE — observed during session)

| Metric | Observed Value |
|---|---|
| initialNavUsd | 1000.0 |
| currentNavUsd | 2631.967 |
| pnlUsd | 1631.967 |
| pnlPct | 163.1967 |
| realizedPnlUsd | -112.6371264 |
| unrealizedPnlUsd | 1744.6101264 |
| maxDrawdownPct | 201.99656384572788 |
| currentDrawdownPct | 50.42795039794688 |
| exposurePct | 26685.74833954985 |
| riskUtilizationPct | 90.0 |
| openPositionCount | 1 |
| simulatedOrderCount | 15 |
| simulatedFillCount | 15 |
| signalCount | 23 |

> [!IMPORTANT]
> **INFERENCE / INTERPRETATION BOUNDARY**
> Interpret ALL performance metrics above strictly as infrastructure-test accounting state.
> They are NOT strategy research evidence, NOT alpha qualification evidence,
> and NOT admissible for any research or trading authorization purpose.

---

## 7. Kill Switch Evidence (FACT — observed journal sequence)

**Critical sequence observed in journal:**

| Seq | Event | Key Fields |
|---|---|---|
| 136 | RISK_APPROVED | current_position=10.0, proposed_position=9.0, daily_realized_loss=81.545696, max_daily_loss=100.0 |
| 137 | ORDER_INTENT_CREATED | SHORT 1.0 BTC |
| 138 | FILL_SIMULATED | fill_price=77815.07300 |
| 139 | POSITION_UPDATED | 10.0 -> 9.0 BTC |
| 140 | PORTFOLIO_UPDATED | cash=-699728.123000, equity=887.3568736, position=9.0, realized_pnl=-112.6371264 |
| 141 | MARKET_BAR_RECEIVED | — |
| 142 | FEATURE_SNAPSHOT | — |
| 143 | SIGNAL_SHORT | — |
| 144 | KILL_SWITCH_TRIGGERED | trigger_reason=MAX_DAILY_LOSS, trigger_type=DAILY_LOSS_LIMIT |
| 145 | RISK_REJECTED | current_position=9.0, proposed_position=8.0, daily_realized_loss=112.6371264, max_daily_loss=100.0 |

**Kill switch violation:** `MAX_DAILY_LOSS: 112.6371264 >= 100.0`

**FACT:** No further `FILL_SIMULATED` or `POSITION_UPDATED` events occurred after sequence 144 in the
observed journal snapshot. The decision-loop kill switch DID stop subsequent simulated execution.

---

## 8. PASS Findings — Working Behavior to Preserve

> [!NOTE]
> Record these explicitly so future remediation work does NOT accidentally destroy working behavior.

**PASS (FACT — observed):**
- max-position gate DID reject proposed position of 11 BTC
- max-daily-loss kill switch DID trigger at correct threshold
- The triggering signal/order path was journaled
- The subsequent risk check was correctly rejected
- No `FILL_SIMULATED` or `POSITION_UPDATED` occurred after kill switch
- Journal remained readable; hash-chain infrastructure remains available
- Feed remained HEALTHY throughout
- Container remained running/healthy
- RestartCount remained 0
- Real orders remained zero
- Canonical real capital remained $0

---

## 9. Discovered Execution-Risk Defects

> [!CAUTION]
> These are confirmed defects requiring remediation. They do NOT imply real-money risk
> (canonical capital = $0, all simulated). They DO block H01 from qualifying as a full
> execution-infrastructure PASS.

### DEFECT 1 — MAX_NOTIONAL NOT ENFORCED

**Classification:** DEFECT — execution-risk model gap

**Context (FACT):** Tournament configuration includes:
```
initial_cash       = 1000.00
max_position_units = 10.0
max_notional       = 100000.0
max_daily_loss     = 100.0
```

**EVIDENCE:** The observed `PaperSessionRunner._evaluate_risk()` checks `max_position_units` and
`max_daily_loss` but does **NOT** enforce `config.max_notional`.

**Evidence of impact:**
- Runtime allowed 9-10 BTC position at approximately 77,000-78,000 BTC/USD price
- At 9 BTC x ~78,040 USD/BTC: notional approximately $702,360
- Configured `max_notional` = $100,000
- Observed `exposurePct` approximately 26,685%

This is not a dashboard display issue. It is an execution-risk model defect.
`max_notional` in the config has no enforcement path in the current risk evaluator.

---

### DEFECT 2 — VIRTUAL INSOLVENCY / LEVERAGE SEMANTICS

**Classification:** DEFECT — simulator boundary / margin semantics

**EVIDENCE:**
```
cash           = -699,728.123
initial NAV    = $1,000
maxDrawdownPct = 201.997%
```

**FACT:** The tournament drawdown computation operates on these accounting values correctly per its
current formula. The >200% drawdown is **not** merely a UI formatting defect — it reflects actual
accounting state in the virtual portfolio.

**Defect:** The simulator currently lacks a clear insolvency/margin/liquidation boundary. A real
brokerage account would have been liquidated long before these states were reachable. The virtual
portfolio permits cash/equity states that would be economically insolvent without margin semantics.

**INFERENCE:** The correct remediation design is not self-evident and requires explicit engineering
decision. Do not assume what the fix should be.

---

### DEFECT 3 — KILL SWITCH DOES NOT FLATTEN EXISTING POSITION

**Classification:** DEFECT — kill-switch safety / design decision required

**FACT:** The max-daily-loss kill switch (SEQ 144) blocks future decisions and orders. However, the
existing 9.0 BTC simulated position remains open indefinitely after kill switch activation.

**GOVERNANCE BOUNDARY:** Do NOT choose or implement a remediation design in this handoff.
This requires explicit human/engineering decision.

**Potential options for future decision (INFERENCE — not authorized):**
- Halt + preserve existing position as-is
- Halt + forced simulated liquidation at market
- Halt + explicit operator resolution required before position can be closed

---

### DEFECT 4 — SUPERVISOR / DASHBOARD STATE SEMANTICS

**Classification:** DEFECT — observability / execution-state propagation

**FACT:** After runner kill switch (SEQ 144):
- Tournament still reports `overallStatus = RUNNING`
- Slot A still reports `RUNNING`
- Feed remains `HEALTHY`

**Assessment (EVIDENCE + INFERENCE):** Feed/container health reporting is operationally correct —
the container is alive and the feed is connected. However, reporting `RUNNING` for Slot A after the
runner's kill switch is activated is misleading for execution state monitoring.

**Defect:** The system does not expose runner kill-switch state as a distinct slot/tournament execution
status (e.g., `KILL_SWITCH_ACTIVE`, `HALTED_LOSS_LIMIT`). The dashboard and supervisor API cannot
currently distinguish "slot running normally" from "slot halted by kill switch, position frozen".

---

## 10. Dashboard Work Completed This Session

### 10.1 Shadow UNASSIGNED Null-Metric Crash Fix

**Commit:** `78bb2e42c8221ab83e88d29dd0f0256528b59b72`

**Fix:** Production `TypeError` caused by null values for:
- `exposurePct`
- `riskUtilizationPct`
- `durationSeconds`

UNASSIGNED Slot B/C now render N/A as em dash instead of crashing.

### 10.2 ACASH Warm Neutral Standard Theme

**Commit:** `ec86a8596a8aa3d8a85c6e875d2e72adfc9c3ca2` — current ACASH main

**Dashboard validation run on Homelab (FACT — reported by prior session):**

| Check | Result |
|---|---|
| npm ci | PASS |
| tsc --noEmit | PASS |
| Tests | 24 / 24 PASS |
| Vite production build | PASS |
| Linux image build | PASS |
| Read-only nginx smoke test | PASS |
| healthz | PASS |

**Final dashboard image:** `acash-dashboard:ec86a85`
**Linux image ID:** `sha256:307e3aa864ea3cc70be2125b812f97e70cff68e206a292a5cbabd67856beae2f`
**Production dashboard state (observed):** running / healthy / RestartCount = 0

### 10.3 Routes Validated (FACT — observed during session)

| Route | Result |
|---|---|
| `https://acash.mew.lab/healthz` (LAN) | HTTP 200 healthy |
| `https://homelab.tail35e4b4.ts.net/acash/healthz` (Tailscale/Traefik) | HTTP 200 healthy |
| `https://homelab.tail35e4b4.ts.net/acash/api/shadow/status` | HTTP 200 |
| VictoriaMetrics job=acash-shadow | health=up, scrapeUrl=http://acash-shadow:9102/metrics |

> [!NOTE]
> **DNS caveat:** Direct DNS lookup for `homelab.tail35e4b4.ts.net` from the Homelab host failed
> during one curl test. The Traefik Tailscale Host route was validated successfully using
> `--resolve 127.0.0.1`. Do not conflate host DNS resolution with router/dashboard health.

---

## 11. Next Session — Recommended Order

> [!IMPORTANT]
> **Perform read-only verification FIRST before any action.**

**FACT — Current state to verify:** `origin/main ==
fd5a35d82bc5b7510ecf84590ed9d36f2041b025`; **D4 = COMPLETE / PASS**;
**D5 = CLOSED — ACCEPTED WITH EXCEPTION** (Human Decision 2026-09-17; no 24h rerun required;
finalization fix verified via Homelab closure smoke).

**NEXT ACTION — Step 1: Verify current state**
```bash
git fetch origin
git rev-parse origin/main  # must == fd5a35d82bc5b7510ecf84590ed9d36f2041b025
git status --short --branch
```

**NEXT ACTION — Step 2: D5 is closed — do NOT restart or rerun D5**
- D5 Attempt 1 completed its 24h wall-clock container lifecycle and is closed as
  **ACCEPTED WITH EXCEPTION** per Human Decision (§4.8).
- Do NOT restart the D5 container, do NOT initiate another 24h run, do NOT touch
  or overwrite `/data/docker/acash/shadow-v2-4b2269d-d5-24h`.

**NEXT ACTION — Step 3: D1–D5 Status Summary**

| Packet | Decision | Value | Status |
|---|---|---|---|
| D1 | Portfolio funding model | **RATIFIED = `CASH_CONSTRAINED_SPOT`** | Wired end-to-end (`4b2269d`) |
| D2 | Kill-switch position policy | **RATIFIED = `HALT_AND_REQUIRE_OPERATOR_RESOLUTION`** | Wired end-to-end (`4b2269d`) |
| D3 | Candidate sizing | **RATIFIED = `NAV_RELATIVE_PERCENT` / 10.0%** | Wired end-to-end (`4b2269d`); applies to ALL slots incl. injected A |
| D4 | V2 Homelab capacity drill | **RATIFIED = 10-slot / 15 min INFRA_TEST drill** | **COMPLETE / PASS (2026-09-16, §4.7)** |
| D5 | V2 runtime | **3-slot 24h Shadow V2** | **CLOSED — ACCEPTED WITH EXCEPTION (2026-09-17, §4.8)** |

Record: `docs/tournament/V2_OPERATOR_RATIFICATION_20260915.md`.

**NEXT ACTION — Step 4: Permanent dashboard backend-routing fix**
- Address the permanent dashboard backend-routing fix (§4.10) — configure stable network alias
  or configurable backend hostname (the temporary alias workaround covers interim).
- Re-verify dashboard/Tailscale/VictoriaMetrics health after the fix.

**NEXT ACTION — Step 5: Open Governance Milestone Alignment**
- Align with human operator on the next authorized governance milestone.
- **GOVERNANCE INVARIANT:** D5 closure does NOT grant trading authority, does NOT create HYP_003,
  does NOT start R1, and does NOT authorize Backtest, Paper, or Live. R1 and hypothesis creation
  remain separate, human-authorized governance steps.

**NEXT ACTION — Step 6: Do NOT**
- Create HYP_003, start R1, authorize Paper/Live, unlock backtesting
- Introduce real capital or broker credentials
- Start another D5 or overwrite H01 / D4 / D5 Attempt 1 failure/evidence directories
- Tag new images over preserved historical tags (`bb6d49c`, `4b2269d`)

---

## 12. Stop Conditions

Stop and report to the human before proceeding past these boundaries:

- Any request to restart H01, start H02, or start another D5 rerun
- Any request to create HYP_003, start R1, authorize Paper, authorize Live, or unlock Backtest
- Any request to introduce real capital or real broker credentials
- Any conflict between this handoff and actual repository/runtime state
- Any remediation implementation that touches more than the isolated defect

---

## 13. Verification Ledger

```
Implementation Status:    COMPLETE — V2 remediation + V2 follow-up + final recovery
                           hardening + numeric hardening + V2 CLI routing +
                           runtime-policy wiring + RISK_HALTED finalization fix
                           MERGED to main @ fd5a35d82bc5b7510ecf84590ed9d36f2041b025
                           (verify tip with `git rev-parse HEAD`)
                           D4 = COMPLETE / PASS; D5 = CLOSED (ACCEPTED WITH EXCEPTION)
Contract Enforcement:     STRICT FAIL-CLOSED (no max(1e-12,..) floors, no silent clamps)
Mathematical Authority:   CANONICAL SPEC (nominal sizing arithmetic & fail-closed lifecycle)
Local Test Suite:         VERIFIED — 2418 passed / 1 skipped (full `uv run pytest`)
Type Checker (MyPy):      VERIFIED — 425 source files clean (`uv run mypy src/ tests/`)
Dashboard:                VERIFIED (npm run typecheck clean; node contract tests 27/27; build clean)
Homelab Closure Smoke:    VERIFIED on acash:shadow-v2-fd5a35d (sha256:5e78425d...)
                           Exact artifacts: 1 journal, 1 snapshot, 1 manifest (PASS/PASS),
                           terminal reason RISK_KILL_SWITCH
Methodological Caveats:
  - D1–D3 RATIFIED & wired end-to-end (4b2269d): CASH_CONSTRAINED_SPOT,
    HALT_AND_REQUIRE_OPERATOR_RESOLUTION, NAV_RELATIVE_PERCENT 10% (incl. slot A)
  - D4 (10-slot capacity drill) COMPLETE / PASS 2026-09-16 on
    acash:shadow-v2-4b2269d (T+900s, graceful stop, ExitCode=0, RestartCount=0,
    OOM=false, 10 manifests/journals/snapshots) — operator-recorded evidence
  - D5 CLOSED as ACCEPTED WITH EXCEPTION (Human Decision 2026-09-17):
    24h container wall-clock achieved; ~21h active execution before expected
    fail-closed RISK_HALTED; finalization defect fixed at fd5a35d and closure-verified
    on Homelab; literal continuous 24h active execution not achieved; no 24h rerun required
  - Homelab smoke harness wrapper had ephemeral filename assertion error; actual
    runtime artifacts were fully produced and verified PASS
  - Dashboard backend routing workaround is TEMPORARY (nginx expects
    acash-shadow:9103); permanent fix scheduled next
  - Automatic Feed Reconnect DISABLED BY DEFAULT; controlled shadow recovery is
    EXPLICIT OPT-IN only (`--enable-feed-recovery`), bounded by attempts /
    backoff / bar-wait timeout; operator resume REQUIRED after terminal halt
```

---

## 14. NEXT SESSION QUICK START

```
ACASH QUICK START — 2026-09-17 Handoff
=======================================
1. git fetch origin; verify origin/main = fd5a35d82bc5b7510ecf84590ed9d36f2041b025;
   verify current tip with `git rev-parse HEAD` (hard-coded tips self-invalidate)
2. RISK_HALTED finalization fix committed and pushed to main at fd5a35d.
3. H01 Attempt 1: EXITED EXIT=2 (ReadTimeout ~7h36m54s); evidence preserved
4. D4 = COMPLETE / PASS (2026-09-16): 10 slots A-J, acash:shadow-v2-4b2269d
5. D5 = CLOSED — ACCEPTED WITH EXCEPTION (Human Decision 2026-09-17):
   24h container lifecycle achieved, ~21h active execution, fail-closed RISK_HALTED,
   finalization defect fixed and closure-verified at fd5a35d; no 24h rerun required.
6. VERIFICATION: 2418 passed / 1 skipped; mypy 425 clean; Homelab closure smoke verified
7. GOVERNANCE: HYP_003=NOT CREATED, R1=NOT STARTED, Paper=NOT AUTHORIZED, capital=$0, NO_REAL_ORDERS=true
8. D1-D5 RATIFIED & CLOSED:
   D1=CASH_CONSTRAINED_SPOT, D2=HALT_AND_REQUIRE_OPERATOR_RESOLUTION,
   D3=NAV_RELATIVE_PERCENT/10%, D4=dry-run COMPLETE/PASS, D5=ACCEPTED WITH EXCEPTION
9. DASHBOARD: routing workaround is TEMPORARY. Permanent fix scheduled next.
10. NEXT: address permanent dashboard backend-routing fix; open governance alignment
    on next authorized milestone (D5 closure does NOT auto-unlock trading/research).
11. DO NOT create HYP_003 / start R1 / authorize Paper/Live / unlock backtest /
    use real capital / reconnect broker / rerun D5 / touch EIMS_11-8-2026.md
```

### Verification Ledger
- Implementation Status: MERGED TO MAIN — D1-D5 RATIFIED & CLOSED (D4 PASS, D5 ACCEPTED WITH EXCEPTION)
- Contract Enforcement: STRICT FAIL-CLOSED
- Local Test Suite: VERIFIED (2418 passed / 1 skipped)
- Type Checker (MyPy): VERIFIED (425 source files clean)
- Homelab Access: OPERATIONAL (D4 PASS, D5 Attempt 1 preserved, closure smoke verified)
- Methodological Caveats: D5 CLOSED with exception (no 24h rerun); literal 24h active execution
  not achieved due to expected fail-closed risk halt; finalization defect fixed and verified.
