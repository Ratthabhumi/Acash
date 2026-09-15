# ACASH Shadow Tournament — V2 10-Slot Design

> [!CAUTION]
> **This document is DESIGN RECORD ONLY — not a qualification certificate,
> not run authorization, not research admission.** It describes the
> configuration surface available in the simulator. Zero real orders, zero
> real capital, zero research admission until the Human authorizes otherwise.

> **Branch context:** `feat/tournament-v2-risk-remediation-10slot`
> (base `main` `9a58ced5011e15c7bcf3975f0e83acf339fa53ce`).
> **Scope:** Tournament V2 readiness (Defects A–E from H01 Attempt 1),
> N-slot fanout, execution-state observability.

---

## 1. Objectives (V2 Readiness)

| # | Objective | Defect closed |
|---|---|---|
| O1 | Enforce a portfolio risk boundary (no unchecked notional, no unbounded virtual debt) | D1, D2 |
| O2 | Kill switch is allowed to flatten or preserve the simulated position via policy | D3 |
| O3 | Expose granular per-slot and aggregate execution states (`RUNNING` / `RISK_HALTED` / `FEED_HALTED` / `STOPPED` / `UNASSIGNED`) end-to-end | D4 |
| O4 | Preserve the causal terminal reason on shutdown | D5 |
| O5 | Remove the fixed 3-slot hardcode: N-slot fanout A..Z (1..26) with a deterministic 10-slot infrastructure catalog | V2 |
| O6 | Align the dashboard contract with the V2 backend states | V2 |

## 2. N-Slot Fanout

- Slot coordinate generator: `slot_ids_for_count(num_slots)` yields `("A", ...)` up
  to 26 slots (`A..Z`). Out-of-contract values (`0`, `27+`) raise
  `DataContractError` (fail-closed, no silent clamp).
- Every `TournamentSlot.slot_id` is validated against `_SLOT_ID_PATTERN` (`^[A-Z]$`).
- `--num-slots` on the tournament CLI (default `3`, range `[1, 26]`) picks the
  fanout; the default layout of a fresh tournament is Slot A mounted + the rest
  honestly `UNASSIGNED` (no phantom runners, no fabricated state).
- Closed-position history and the status writers are fan-out aligned to the
  live slot set, so no stale slot records leak across resize.

## 3. 10-Slot Infrastructure Candidate Catalog

- `INFRASTRUCTURE_CANDIDATES_10SLOT` exposes exactly 10 deterministic,
  infrastructure-test-only candidates (`A..J`), each with a distinct
  `strategy_id` (`INFRA-TEST-MOMENTUM-SYNTHETIC-001..010`), distinct fast/slow
  windows and quantity, all labeled `INFRASTRUCTURE_TEST_STRATEGY_ONLY`.
- Slot A is bit-compatible with the historical canonical default
  (`INFRA-TEST-MOMENTUM-SYNTHETIC-001`; fast=3, slow=5, qty=1.0).
- Mounting is **explicit** (API opt-in, CLI symmetric):
  - API: `create_default_shadow_tournament(..., auto_mount_infrastructure_candidates=True)`
    (library default `False` — explicit opt-in).
  - CLI: `--auto-mount-infra-candidates` / `--no-auto-mount-infra-candidates`
    (default `True` = the default operational layout exercises the 3-slot
    INFRA_TEST layout; `--no-auto-mount-infra-candidates` runs slot-A-injected
    alone and must NOT silently create catalog candidates).
  - Infra auto-mount only ever mounts INFRA_TEST candidates; zero alpha
    candidates are ever auto-mounted, and auto-mount alone does NOT authorize
    or constitute runtime strategy trading.

## 4. Portfolio & Risk Policies (Defects D1/D2)

`PortfolioFundingPolicy` (config-sealed, single authority):

| Policy | Contract |
|---|---|
| `SIMULATED_LEVERAGED` (default) | Negative virtual cash permitted. H01-evidence-preserving: a kill switch is *not* an accounting error. Unbounded **notional** is still blocked by the `MAX_NOTIONAL` gate. |
| `CASH_CONSTRAINED_SPOT` | Reject simulated fills that would make virtual cash negative (fail-closed). |
| `EXPLICIT_BOUNDED_LEVERAGE` | Requires `max_debt_limit_usd >= 0`; simulated fills are rejected when debt would breach the limit. Any invalid/negative limit raises `DataContractError` (no `max(1e-12, …)` floors). |

`KillSwitchPositionPolicy` (Defect D3):

| Policy | Contract |
|---|---|
| `HALT_AND_PRESERVE_POSITION` (default) | Kill switch stops decisions; open simulated position stays intact (H01 behavior preserved). |
| `HALT_AND_FORCE_SIMULATED_FLATTEN` | On kill-switch trigger, attempt to flatten the open simulated position at mark. Missing/zero reference price → `DataContractError` (fail-closed, never silent no-op). |
| `HALT_AND_REQUIRE_OPERATOR_RESOLUTION` | Kill switch + `operatorResolutionRequired=True` surfaced in `TournamentSlot` and API JSON. |

Both policies are fields of the runner config and therefore enter
`compute_config_hash()` — identical inputs seal identical hashes, any policy
change rotates the hash (cryptographic lineage preserved).

## 5. Execution-State Observability (Defect D4)

`SlotExecutionState` (single authority, `src/acash/paper/tournament.py`):

- `RUNNING` — actively processing synchronized bars
- `RISK_HALTED` — kill switch active (`MAX_DAILY_LOSS`) on this slot
- `FEED_HALTED` — halted fail-closed (feed disconnect / staleness)
- `STOPPED` — operator/normal shutdown
- `UNASSIGNED` — no runner attached

Aggregate precedence: `RISK_HALTED > FEED_HALTED > STOPPED > RUNNING >
UNASSIGNED > NOT_STARTED`. Surfaced in: slot status, aggregate
`executionState`, `/api/shadow/status` JSON, Prometheus one-hot metrics, and
the dashboard contract. `_update_metrics` emits one-hot gauges
(e.g. `slot_status_onehot{slot="A",state="RISK_HALTED"} 1`) — measurement is
the state, not a cosmetic `RUNNING` proxy.

## 6. Data Source Labeling

Status JSON and dashboard report `dataSource: "SHADOW_RUNTIME"` — every
metric/leaderboard/equity point is explicitly tagged as simulated.

## 7. Dashboard Contract

- `SlotId = "A".."J"`, `SlotStatus` includes the five granular states above.
- `SimulatedPosition {symbol, side, quantity, entryPrice, currentPrice, unrealizedPnlUsd}`.
- `EquityPoint {timestampUtc, navUsd, pnlUsd}`.
- Leaderboard uses `strategyId`, `pnlUsd`, `winRatePct`, `simulatedFills`.
- `operatorResolutionRequired: boolean` on `StrategySlot`; `executionState` on
  global status.

## 8. Governance Boundaries (unchanged)

- HYP_003 NOT CREATED · R1 NOT STARTED · Backtesting LOCKED
- Paper NOT AUTHORIZED · Live LOCKED
- Canonical capital $0.00 · NO_REAL_ORDERS=true
- Auto reconnect DISABLED · Operator resume REQUIRED

**GOVERNANCE BOUNDARY:** nothing in this design authorizes H02, a new run,
paper, live, or backtesting. All such decisions remain with the Human.

## 9. V2 Follow-up — Transient Feed Recovery, Dynamic Admission, Safe Sizing

Two follow-up capability groups were added to the same branch and are recorded
here with their exact contracts. Both remain **shadow-only instruments**: they
do NOT unlock auto-reconnect, paper, live, or research admission.

### 9.1 Transient Feed Recovery (opt-in, shadow)

Motivation: H01 Attempt 1 ended `EXIT=2` because a transient feed `ReadTimeout`
halted the whole tournament fail-closed with no operator-understandable path.
This adds a *controlled, operator-visible* recovery seat for **transient**
`FeedConnectionError` only.

| Contract | Rule |
|---|---|
| Trigger | feed poll raises `FeedConnectionError` (transient). `FeedContractError` / staleness remain **immediate fail-closed halt** — no recovery path |
| Seat | slot enters `FEED_RECOVERING`; supervisor `feeds_health` becomes `RECOVERING` |
| During recovery | **zero** new simulated orders and **zero** new signals; portfolio, cash, journal, and closed-position history are preserved untouched |
| Reconnect boundary | on the next supervisor poll, `recovery.validate_reconnect_bar()` compares the live bar time against the authoritative `last_accepted_bar_utc`: equal-gap or pending bars are backfilled into an in-memory window; an older-than-boundary resume is rejected |
| Journaling | every episode runs under a single episode correlation id created by `enter_feed_recovery`; phases `FEED_RECOVERING` → `FEED_RECOVERY_ATTEMPTED` → `FEED_RECOVERY_SUCCEEDED` (or `FEED_RECOVERY_EXHAUSTED`), plus `SESSION_STOPPED reason=FEED_RECOVERY_FAILED` on exhaustion |
| Backoff | `FeedRecoveryConfig.backoff_seconds` is a `Tuple[float, ...]` (one delay per attempt). Single authority: `backoff_delay_seconds(n, backoff) = backoff[min(n-1, len-1)]` — attempt 1 failure sleeps the first entry, and the journaled `backoff_seconds` value is exactly the applied sleep. CLI default `2,5,10,20,30` (each > 0). The terminal attempt sleeps nothing |
| Bar-wait | after a successful reconnect the episode waits for its first bar under a **monotonic deadline** `bar_wait_timeout_seconds` (config default `90.0`, CLI `--recovery-bar-wait-timeout-seconds`, must be > 0). Every `None` poll consumes elapsed budget; a deadline expiry is `BAR_WAIT_TIMEOUT`, consumes that attempt's retry budget, and applies the configured backoff — never an unbounded wait, never a busy-loop |
| Exhaustion | after `max_attempts` failures the failure reason is **preserved** (never rewritten as `NORMAL_SHUTDOWN`) and the tournament halts fail-closed; operator resume is **required** — there is no automatic reconnect |
| Opt-in | CLI recovery default is **OFF**: **`--enable-feed-recovery`** is the single canonical positive switch (the inverted `--disable-feed-recovery` was removed). Default OFF means any transient `FeedConnectionError` immediately halts fail-closed (exit 2, operator resume required). When enabled, controlled shadow recovery applies only to transient `FeedConnectionError` inside the bounded attempts / backoff / bar-wait budget above. The supervisor API path remains available programmatically |

### 9.2 Dynamic Shadow Candidate Admission (SIGHUP / candidate-add file)

Motivation (D3-era design constraint reversed): allowed **staged** admission of
new INFRA_TEST shadow candidates without a full tournament restart, while frozen
slots and comparison integrity stay explicit.

| Contract | Rule |
|---|---|
| Stage | `stage_candidate_add(slot_id, strategy_id)` returns an explicit `ShadowCandidateStageResult` |
| Rejection matrix | `TOURNAMENT_NOT_RUNNING` · `INVALID_SLOT_ID` · `UNKNOWN_SLOT` · `SLOT_OCCUPIED` · `CANDIDATE_ADD_UNCONFIGURED` · `UNKNOWN_STRATEGY_ID` · `DUPLICATE_STRATEGY_ID` · `CAPACITY_EXCEEDED` — all fail-closed, none silent |
| Materialization | staged candidates are admitted on the **next** bar into a new runner + fresh config hash; cohort id is `"<strategy_id>:ADD:<YYYYMMDD_HHMMSS_ffffff>"` |
| Provenance | `observation_kind` `NONE` / `CONTINUOUS` / `LATE_JOIN`; `comparison_window_id`; `baseline_nav_usd = 1000.00` (slot NAV at admission) — all carried in the slot/API JSON |
| Leaderboard | each cohort's observation window feeds a per-slot comparison; **single-member cohorts report rank `null`** (no statistical comparison exists — never fabricated) |
| Operator surface | `last_operator_action_results` / `clear_operator_action_results`; CLI `--candidate-add-file` + `SIGHUP` triggers a staged restage from the file |

### 9.3 Safe NAV-Relative Sizing (shadow bound, no leverage surprise)

| Contract | Rule |
|---|---|
| Policy | `SignalSizingPolicy.INFRA_FIXED_QUANTITY` (default, bit-compatible with historical canonical qty=1.0) / `NAV_RELATIVE_PERCENT` |
| Formula | `qty = (equity × SAFE_V2_NAV_SIZING_PCT / 100) / price`, `SAFE_V2_NAV_SIZING_PCT = 10.0`, 8-dp `ROUND_DOWN`, `exec_signal(target_quantity=qty)` |
| Fail-closed | non-positive quantity, zero price, zero/negative equity → `DataContractError` / `SIZING` gate rejection; a dead sizing config is rejected at admission |
| Sealing | `SESSION_STARTED` payload carries `sizing` metadata **only when** sizing was actually applied (fixed policy → empty, H01-replay bit-compatible) |

### 9.4 Journal Integrity Fix Sourced While Wiring Recovery

`journal_system_event` re-acquired the journal lock while internal callers
(`enter_feed_recovery`, `_materialize_candidate_adds`, …) already held it —
a re-entrant deadlock on a plain `threading.Lock`. Split into the public
wrapper `journal_system_event()` (acquires the lock) and the internal
`_journal_system_event_unlocked()` (no lock); all internal call sites use the
unlocked variant. Also fixed UTF-8 mojibake (`—`/`·` corruption) that this
branch had previously introduced into tournament wording.

---

### Verification Ledger
- Implementation Status: DESIGN RECORD — reflects commits `c4651ac`,
  `24d5607`, `b169d27`, `139ac62`, `56160de` plus the V2 follow-up commit set
  (recovery / candidate admission / sizing)
- Contract Enforcement: STRICT FAIL-CLOSED (prescribed above)
- Mathematical Authority: N/A (config/observability design; sizing arithmetic is
  nominal, not statistical)
- Local Test Suite: SEE `./TOURNAMENT_V2_VALIDATION.md`
- Type Checker (MyPy): SEE `./TOURNAMENT_V2_VALIDATION.md`
- Remote CI Status: NOT AVAILABLE
- Methodological Caveats:
  - Recovery is a *shadow* seat, not auto-reconnect; `NO_REAL_ORDERS` and
    operator-resume boundaries are preserved
  - Candidate admission is INFRA_TEST-only; dynamic admission is *not* alpha
    qualification and carries no research admission
  - Sizing is nominal-share math verified by unit tests, not a statistical model

---

### Verification Ledger
- Implementation Status: DESIGN RECORD — reflects commits `c4651ac`,
  `24d5607`, `b169d27`, `139ac62`, `56160de`
- Contract Enforcement: STRICT FAIL-CLOSED (prescribed above)
- Mathematical Authority: N/A (config/observability design)
- Local Test Suite: SEE `./TOURNAMENT_V2_VALIDATION.md`
- Type Checker (MyPy): SEE `./TOURNAMENT_V2_VALIDATION.md`
- Remote CI Status: NOT AVAILABLE
- Methodological Caveats:
  - Policies are *available*, not *chosen*; the deployed defaults preserve
    H01 evidence semantics
  - 10-slot catalog is infrastructure-exercise only; zero alpha authority
  - D5 (terminal reason preservation) was verified via kill-switch reason
    propagation in `ShadowTournamentSupervisor`; live-container observability
    of `SESSION_STOPPED` causality remains operator-verified at deployment