# ACASH Shadow Tournament — V2 10-Slot Validation

> [!CAUTION]
> **This document is TEST EVIDENCE RECORD ONLY — it is not a qualification
> certificate, not run authorization, and not research admission.**

> **Branch context:** `feat/tournament-v2-risk-remediation-10slot`
> (base `main` `9a58ced5011e15c7bcf3975f0e83acf339fa53ce`).
> **Status:** local suite verified at the design commit set below.

---

## 1. Test Inventory (unit + integration, paper/tournament scope)

| Test file | Coverage | Status |
|---|---|---|
| `tests/unit/paper/test_risk_remediation_v2.py` | Defects A & E — `MAX_NOTIONAL` gate, `TerminalReason` preservation | 9 passed |
| `tests/unit/paper/test_tournament.py` | N-slot fanout `A..Z` (1..26), slot validation, 10-slot layout, auto-mount, catalog, **10-slot state isolation** (distinct journals / hashes / portfolios, no cross-slot sharing) | 17 passed |
| `tests/unit/paper/test_v2_policy_seams.py` | Funding policies, negative-debt contract error, kill-switch preserve / flatten / operator-policy, payload fields, `RISK_HALTED`/`FEED_HALTED`/`STOPPED` aggregate states, one-hot metrics | 14 passed |
| `tests/integration/test_shadow_tournament_runtime.py` | HTTP API endpoints exercised under `num_slots=3`, `auto_mount_infra_candidates=False` namespaces | 4 passed |
| **Total (paper scope)** | | **229 passed** |

Mypy (strict, `src/acash/paper/`): **Success — no issues in 24 source files**.

Dashboard contract (TypeScript): `npm run typecheck` clean; shadow contract
node tests 25/25 (`dashboard/test/shadow_contract.test.mjs`).

## 2. What the Tests Prove

1. **D1 fix:** `MAX_NOTIONAL` gate rejects simulated orders whose notional
   would exceed the configured limit; rejection reason and trigger type are
   journaled (fail-closed, no soft cap).
2. **D5 fix:** terminal reason is propagated and preserved through the
   supervisor halt path (no silent `NORMAL_SHUTDOWN` rewrite of a causal halt).
3. **D2 contract:** `EXPLICIT_BOUNDED_LEVERAGE` rejects non-negative-required
   debt limits with `DataContractError`; `CASH_CONSTRAINED_SPOT` rejects
   negative-cash fills. No `max(1e-12, …)` floors anywhere.
4. **D3 contract:** `HALT_AND_FORCE_SIMULATED_FLATTEN` flattens at mark and
   fails closed on a missing mark; `HALT_AND_REQUIRE_OPERATOR_RESOLUTION`
   surfaces `operatorResolutionRequired` in slot + API JSON.
5. **D4 fix:** slot status transitions `RUNNING → RISK_HALTED` on kill-switch
   trigger and `→ FEED_HALTED` on feed failure; aggregate state precedence
   verified; one-hot metric gauges carry the true state.
6. **V2 fanout:** `slot_ids_for_count` is deterministic, tie-symmetric, and
   contract-bounded (`DataContractError` outside `[1, 26]`); 10-slot layout
   mounts only Slot A by default with the rest `UNASSIGNED`; the infrastructure
   catalog holds 10 distinct INFRA_TEST candidates; auto-mount is opt-in only.
7. **V2 isolation:** in a fully auto-mounted 10-slot layout, all 10 slots own
   distinct journal files, distinct session IDs, distinct config hashes, and
   distinct (non-shared) portfolio objects; one bar is delivered to every slot;
   manifests are sealed per slot with distinct config hashes after halt.

## 3. Evidence Trail (commits)

| Commit | Change |
|---|---|
| `260d32b` | fix(paper): enforce `MAX_NOTIONAL` + preserve terminal reason (D1, D5) |
| `c4651ac` | feat(paper): funding + kill-switch position policies and granular execution states (D2, D3, D4) |
| `24d5607` | feat(paper): parameterize slot fanout for N-slot tournament (A..Z, 1..26) |
| `b169d27` | feat(paper): 10-slot infrastructure candidate catalog with explicit auto-mount opt-in |
| `139ac62` | feat(dashboard): align V2 10-slot contract, granular execution states, `SHADOW_RUNTIME` data source |
| `56160de` | test(paper): prove 10-slot layout state isolation |

## 4. Explicit Non-Claims (what this does NOT prove)

- No strategy alpha, no statistical qualification, no backtesting result.
- No run of 24h continuity has been performed on this branch (H01 Attempt 1
  remains the last run; it did NOT achieve 24h).
- No production deployment, no live feed soak, no operator-recovery drill
  on the V2 layout. D4/D5 observability is verified at the Python/unit level;
  container-level behavior remains operator-verified at deployment.
- Paper/Live remain NOT AUTHORIZED; canonical capital stays $0.00.

---

## 5. V2 Follow-up Evidence — Recovery / Dynamic Admission / Safe Sizing

Second validation pass on the same branch after the follow-up feature set
(transient feed recovery, staged dynamic candidate admission, NAV-relative
sizing). Records replace the §1 scope snapshot for the newest suites; the
earlier suites remain continuously green.

### 5.1 Test inventory (additions)

| Test file | Coverage | Status |
|---|---|---|
| `tests/unit/paper/test_feed_recovery.py` | Episode lifecycle, reconnect boundary validation, zero orders/signals during recovery, portfolio preservation, journal ordering under one episode correlation id, operator stop during recovery, resume boundary, **exact backoff schedule (journal == actual sleep, no terminal sleep), deterministic bounded bar-wait timeout (fake clock), wall-clock-bounded wait, operator stop mid-wait, FeedContractError bypass, config validation** | 29 passed |
| `tests/unit/paper/test_dynamic_candidate_add.py` | Stage/materialize semantics, rejection matrix, batch cohort identity, catalog instance freshness, adversarial double-stage, fail-closed null-builder materialize | 15 passed |
| `tests/unit/paper/test_safe_sizing.py` | FIXED vs NAV sizing spread, config hashing, dead-config rejection, SESSION_STARTED sizing seal, CLI policy override | 17 passed |
| `tests/unit/paper/test_v2_cli_options.py` | CLI flag parsing and validation boundaries, **recovery default OFF / positive opt-in flag / removed inverted flag, strict max-attempts & bar-wait & poll-interval validators, auto-mount BooleanOptional default True / explicit True / --no-auto-mount False** | 32 passed |

### 5.2 Full-repository evidence (this branch tip)

| Check | Result |
|---|---|
| `uv run pytest tests/` | **2377 passed / 12 skipped** (0 failures) |
| `uv run mypy src/ tests/` | **Success — no issues in 423 source files** |
| `git diff --check` | clean |
| Dashboard `npm run typecheck` | clean |
| Dashboard node contract tests | **27 / 27 passed** (incl. FEED_RECOVERING seat, provenance, null-rank) |
| Dashboard `npm run build` | clean (tsc + vite production build) |

### 5.3 What the follow-up tests prove

1. **Recovery is a strict seat, not a reconnect.** During an episode the
   journal receives no new EXECUTION or SIGNAL events, portfolio cash/position
   and closed-position history are byte-identical before/after, and all episode
   phases share the single correlation id minted by `enter_feed_recovery`.
2. **Recovery fails closed.** Budget exhaustion preserves the causal reason
   (`FEED_RECOVERY_FAILED`), halts the tournament, and requires operator resume;
   an older-than-boundary reconnect bar is rejected, and a fresh runner refuses
   to join mid-window (drops the bar, halts feed-seam first).
3. **Dynamic admission is staged and explicit.** Unconfigured slots,
   occupied slots, unknown/duplicate strategies, unknown slot ids, and
   capacity-exceeded states are all rejected with named results; admission
   happens only on the next bar; late-join cohorts carry rank `null` on the
   leaderboard (single-member — no fabricated comparison).
4. **Sizing is safe and sealed.** NAV-relative sizing produces a bounded
   fraction of current equity with 8-dp `ROUND_DOWN`, fixed policy remains
   bit-compatible with the canonical qty=1.0, dead sizing configs are rejected,
   and non-positive derived quantity is rejected by the SIZING gate (never
   silently clamped).
5. **Journal lock integrity.** The re-entrant lock split (`journal_system_event`
   wrapper / `_journal_system_event_unlocked`) is exercised by the recovery and
   candidate-admission paths with no deadlock across the suite.

### 5.4 Final Recovery Hardening Evidence (YELLOW-item closure)

Third validation pass: closes the five audited YELLOW items from the V2 branch
review. Each item is recorded with its confirmed root cause, the remediation,
and the test evidence. **No runtime, deployment, or live/long-run execution was
performed in this pass.**

| YELLOW item | Confirmed root cause | Remediation | Test evidence |
|---|---|---|---|
| #1 recovery default OFF | CLI enabled recovery by default via the inverted `--disable-feed-recovery` (default `False` → `recovery_enabled = True`) | Single canonical positive switch `--enable-feed-recovery` (default `False`); the inverted flag was removed; default OFF now immediately halts fail-closed (exit 2, operator resume) | `test_recovery_off_by_default`, `test_enable_feed_recovery_flag`, `test_disable_feed_recovery_removed` |
| #2 backoff off-by-one | Driver slept `backoff[min(attempts_used, len-1)]` *after* incrementing → attempt 1 failure slept the 2nd entry (5s instead of 2s) | Single authority `backoff_delay_seconds(attempt_no, backoff) = backoff[min(attempt_no-1, len-1)]`; journaled `backoff_seconds` is literally the value slept; terminal attempt sleeps nothing | `test_backoff_schedule_exact_no_terminal_sleep`, `test_backoff_journaled_equals_actual_sleep`, `test_backoff_short_schedule_clamps_to_last_entry`, `test_backoff_delay_seconds_single_authority` |
| #3 unbounded bar-wait | Connected-recovery poll loop (`bar is None → sleep → poll…`) had no deadline | `bar_wait_timeout_seconds` default `90.0` (> 0) with an injectable monotonic deadline; every `None` consumes elapsed budget; `BAR_WAIT_TIMEOUT` consumes the attempt's retry budget + configured backoff; operator stop still interrupts mid-wait | `test_bar_wait_timeout_consumes_attempt_then_recovers`, `test_bar_wait_timeout_all_attempts_exhausted`, `test_bar_wait_timeout_budget_wallclock_bounded`, `test_operator_stop_during_bar_wait`, `test_bar_wait_timeout_non_positive_rejected` |
| #4 silent CLI clamp | `FeedRecoveryConfig(max_attempts=max(1, int(...)))` silently raised 0/negative operator input to 1 | Strict argparse types: `_positive_int` (max attempts >= 1), `_non_negative_float` (poll interval >= 0), `_positive_float` (bar-wait > 0), `_parse_backoff_seconds` (backoff > 0); any violation is a parse-time `SystemExit` — never a silent correction | `test_max_recovery_attempts_zero_rejected`, `test_max_recovery_attempts_negative_rejected`, `test_bar_wait_timeout_zero_rejected`, `test_poll_interval_negative_rejected`, `test_poll_interval_zero_allowed`, plus backoff rejection suite |
| #5 auto-mount symmetry | `--auto-mount-infra-candidates` was `store_true` default `True` — impossible to disable | `argparse.BooleanOptionalAction` default `True` (`--auto-mount-infra-candidates` / `--no-auto-mount-infra-candidates`); default operational layout exercises 3 INFRA_TEST candidates; auto-mount is explicitly *not* alpha authorization; when disabled, `infra_mount_count` cannot silently create candidates | `test_auto_mount_default_true`, `test_auto_mount_explicit_true`, `test_no_auto_mount_flag_disables` |

**Final recovery semantics recorded after this pass**

- **Automatic Feed Reconnect: DISABLED BY DEFAULT** — any transient feed
  connection failure immediately halts fail-closed (exit code 2) with operator
  resume required.
- **Controlled Shadow Feed Recovery: AVAILABLE / EXPLICIT OPT-IN**
  (`--enable-feed-recovery`), and only ever handles transient
  `FeedConnectionError` inside a bounded attempts / backoff / bar-wait budget;
  `FeedContractError` and staleness still bypass recovery and halt immediately.
- **Operator Resume: REQUIRED** after terminal recovery failure (`BUDGET_EXHAUSTED`
  → `FEED_RECOVERING` halt, exit 5) or an ordinary fail-closed halt.

---

### Verification Ledger
- Implementation Status: COMPLETE (design commit set + V2 follow-up commit set + final recovery hardening)
- Contract Enforcement: STRICT FAIL-CLOSED
- Mathematical Authority: N/A (config/observability changes; accounting contract tests)
- Local Test Suite: VERIFIED (2377 passed / 12 skipped — full `uv run pytest tests/`)
- Type Checker (MyPy): VERIFIED (423 source files clean, `uv run mypy src/ tests/`)
- Remote CI Status: NOT AVAILABLE
- Methodological Caveats:
  - Dashboard evidence (`npm run typecheck`, node contract tests, production
    build) is a separate toolchain; counts reported from local run
  - Recovery/candidate/sizing behavior is verified at the Python/unit level;
    container-level operator-recovery drill remains operator-verified at
    deployment
  - The 12 skipped tests and 3 pydantic serializer warnings (pre-existing
    `mt5_reconciliation` invalid-enum fixtures) are unrelated to this branch's
    scope and classified as accepted risk
  - This hardening pass performed NO runtime, deployment, image build, or
    long-run execution; Homelab validation remains a separate human step