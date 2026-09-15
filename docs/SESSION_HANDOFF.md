# ACASH SESSION HANDOFF — H01 Closure → Tournament V2 Risk Remediation → HUMAN DECISION PENDING
## Canonical Current Session Handoff — 2026-09-15

> [!CAUTION]
> **VERIFY CURRENT REPOSITORY, RUNTIME, JOURNAL, AND GOVERNANCE STATE BEFORE ACTING.**
> This document is a navigation snapshot, not eternal source of truth.
> Always `git fetch origin`, verify full 40-char SHAs, and re-inspect
> container/journal state before any consequential action.

> **Document:** `docs/SESSION_HANDOFF.md`
> **This is the single canonical ACASH session handoff.**
> For the archived E3.6 historical checkpoint, see `E3.6-SESSION-HANDOFF.md`.
> **Date:** 2026-09-15 (UTC)
> **Status labels used:** FACT | EVIDENCE | INFERENCE | DEFECT | GOVERNANCE BOUNDARY | NEXT ACTION

---

## 1. ACASH Repository — Current State

| Item | Value |
|---|---|
| Repository | `Ratthabhumi/Acash` |
| Active branch | `feat/tournament-v2-risk-remediation-10slot` |
| Branch base | `main @ 9a58ced5011e15c7bcf3975f0e83acf339fa53ce` (origin/main verified) |
| Base message | `docs: refresh canonical session handoff and archive E3.6 checkpoint` |
| Branch tip | `df1bafa` (12 commits ahead of main) — V2 follow-up implemented, pushed, NOT merged |
| Branch state | PUSHED to `origin/feat/tournament-v2-risk-remediation-10slot` — NOT merged |

**FACT:** `origin/main == 9a58ced5011e15c7bcf3975f0e83acf339fa53ce` re-verified on 2026-09-15
after the V2 work completed (see §4.5). Branch remains 12 commits ahead of main.

**ACTIVE BRANCH COMMITS (EVIDENCE — full SHAs):**

| # | Commit | Scope |
|---|---|---|
| 1 | `ad6642fb5dd9f65c406194daacd3b31a0953f40d` | docs: H01 Attempt 1 evidence preserved, H01 closure recorded (EXIT=2, ReadTimeout) |
| 2 | `260d32b56668a6d99d1e120e2fa2096b4d4ca350` | fix: enforce `MAX_NOTIONAL` + preserve terminal reason (Defects A & E) |
| 3 | `c4651ac82fba8e2a382dd01b3ab0248cc2a042e4` | feat: funding + kill-switch position policies + granular execution states (Defects B, C & D) |
| 4 | `24d5607b380e033015365b60b9e71f29cc76d4af` | feat: N-slot fanout A..Z (1–26), `--num-slots` CLI |
| 5 | `b169d272d320217996f1dc6b7208a8677db26b65` | feat: 10-slot infrastructure candidate catalog, auto-mount opt-in |
| 6 | `139ac62c18fa95621f5685d8a131650b0fff2d40` | feat: dashboard V2 contract, granular states, `SHADOW_RUNTIME` data source |
| 7 | `56160de912d9f49e7e56bad70a46d216b883f1dc` | test: 10-slot layout state isolation |
| 8 | `3787cd06fff7423b2e6f4e8efd93051c52d6d808` | docs: V2 10-slot design + validation evidence |
| 9 | `706168c` | feat(paper): journal event kinds + re-entrant lock integrity + feed-health recovery metrics |
| 10 | `48aeeec` | feat(paper): transient feed recovery + staged dynamic candidate admission + safe NAV sizing |
| 11 | `d86eca5` | test(paper): recovery, dynamic candidate admission, and safe sizing suites (69 tests) |
| 12 | `3aea870` | feat(dashboard): FEED_RECOVERING seat, cohort provenance, null-rank leaderboard |
| 13 | `df1bafa` | docs(tournament): record recovery / dynamic admission / safe sizing design + evidence |

> A follow-up docs commit (SESSION_HANDOFF refresh) completes the commit set.

**VERIFY, do not assume.** Run `git fetch origin` and `git rev-parse origin/main` at start of
every session.

---

## 2. Pi Personal Infrastructure — Current State

| Item | Value |
|---|---|
| Repository | `Ratthabhumi/Pi_Personal-Infrastructure` |
| Current main | `3ce27f09e742768633c23a5d0746a004bc3a1727` |
| Dashboard pin deployed | `acash-dashboard:ec86a85` |
| Shadow runtime pin | `acash:shadow-tournament-bb6d49c` |

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
| Automatic Feed Reconnect | DISABLED |
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
| Branch | `feat/tournament-v2-risk-remediation-10slot` @ `df1bafa` |
| Defects addressed | A (`MAX_NOTIONAL`), B (funding policy), C (kill-switch policy), D (execution states), E (terminal reason) |
| V2 readiness | N-slot fanout A..Z (1–26), 10-slot INFRA_TEST catalog, 10-slot isolation proven |
| V2 follow-up | transient feed recovery seat (FEED_RECOVERING), staged dynamic candidate admission (SIGHUP / candidate-add file), safe NAV-relative sizing (10% cap), journal re-entrant lock fix |
| Local test suite | **2353 passed / 12 skipped** (full `uv run pytest tests/`) |
| MyPy | **423 source files clean** (`uv run mypy src/ tests/`) |
| Dashboard | `npm run typecheck` clean; node contract tests **27/27**; production build clean |
| Deployment state | NOT deployed — no image built, no container restarted, no Pi change |
| Paper/Live | NOT AUTHORIZED |

**Design/validation records:** `docs/tournament/TOURNAMENT_V2_10SLOT_DESIGN.md` and
`docs/tournament/TOURNAMENT_V2_VALIDATION.md`.

### 4.6 V2 Follow-up Session Summary (EVIDENCE)

Controlled transient feed recovery (shadow only — auto-reconnect remains
structurally DISABLED, operator resume REQUIRED after exhaustion), staged
dynamic admission of INFRA_TEST candidates with cohort provenance and
null-rank single-member cohorts, and NAV-relative sizing bounded to 10% of
virtual equity. During a recovery episode the slot emits **zero** new simulated
orders/signals; a failed recovery halts with `FEED_RECOVERY_FAILED` (causal
reason preserved) and exit code 5. New suites: `test_feed_recovery.py` (18),
`test_dynamic_candidate_add.py` (15), `test_safe_sizing.py` (17),
`test_v2_cli_options.py` (19).

**PENDING HUMAN DECISION (D1–D5)** — the branch implements *policies*, it does **not** choose
them. See §11 step 3.

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

**NEXT ACTION — Step 1: Verify current state**
```bash
git fetch origin
git rev-parse origin/main  # must == 9a58ced5011e15c7bcf3975f0e83acf339fa53ce
git status --short --branch
```
Also re-verify: container status (H01 Attempt 1 = EXITED EXIT=2), journal path/size, feed health.

**NEXT ACTION — Step 2: V2 remediation is COMPLETE — verify evidence artifacts**
- Design: `docs/tournament/TOURNAMENT_V2_10SLOT_DESIGN.md`
- Validation: `docs/tournament/TOURNAMENT_V2_VALIDATION.md`
- Branch tip `df1bafa` pushed to origin (NOT merged)
- Full local evidence: 2353 passed / 12 skipped; mypy 423 files clean; dashboard 27/27

**NEXT ACTION — Step 3: Obtain HUMAN DECISIONS (D1–D5) before any deployment/run**

The V2 branch makes *policies available*; it does **not** choose them. The following
only become effective after explicit Human authorization:

| Packet | Decision | Options | Default (recommended) |
|---|---|---|---|
| D1 | Portfolio funding model | `SIMULATED_LEVERAGED` / `CASH_CONSTRAINED_SPOT` / `EXPLICIT_BOUNDED_LEVERAGE` | `SIMULATED_LEVERAGED` (H01-evidence preserving) |
| D2 | Kill-switch position policy | `HALT_AND_PRESERVE_POSITION` / `HALT_AND_FORCE_SIMULATED_FLATTEN` / `HALT_AND_REQUIRE_OPERATOR_RESOLUTION` | `HALT_AND_PRESERVE_POSITION` |
| D3 | Candidate sizing | Confirm Slot A bit-compatible with historical canonical default; catalog A..J is INFRA_TEST-only | Confirm |
| D4 | V2 Homelab resource limits | **TEST REQUIRED** — 10-slot mount is unit-proven; container-level resource-limit soak/drill NOT yet performed | Perform before any V2 run claim |
| D5 | V2 runtime authorization | No run authorized; design commit set does not unlock H02 / Paper / Live | NO RUN |

**NEXT ACTION — Step 4: Only after D1–D5 are authorized**

Deployment on Homelab (build image from branch tip, run `acash-shadow` with chosen
`--num-slots` and `--auto-mount-infra-candidates` per authorized layout), observe a V2
soak, then reconcile against journal/manifests. Do NOT auto-merge the branch.

**NEXT ACTION — Step 5: Do NOT**
- Merge `feat/tournament-v2-risk-remediation-10slot` to `main` without explicit instruction
- Create HYP_003, start R1, authorize Paper/Live, unlock backtesting
- Introduce real capital or broker credentials
- Restart H01 or start H02 without Human authorization
- Build/deploy images or touch Pi infrastructure without explicit request

---

## 12. Stop Conditions

Stop and report to the human before proceeding past these boundaries:

- Any request to restart H01, start H02, or start `acash-shadow` fresh
- Any request to create HYP_003, start R1, authorize Paper, authorize Live, or unlock Backtest
- Any request to introduce real capital or real broker credentials
- Any conflict between this handoff and actual repository/runtime state
- Any remediation implementation that touches more than the isolated defect

---

## 13. Verification Ledger

```
Implementation Status:    COMPLETE — V2 remediation + V2 follow-up delivered on
                           feat/tournament-v2-risk-remediation-10slot
                           (13 commits, tip df1bafa, pushed; NOT merged)
Contract Enforcement:     STRICT FAIL-CLOSED (no max(1e-12,..) floors, no silent clamps)
Mathematical Authority:   N/A (config/observability + nominal sizing arithmetic)
Local Test Suite:         VERIFIED (2353 passed / 12 skipped — full `uv run pytest tests/`)
Type Checker (MyPy):      VERIFIED (423 source files clean — `uv run mypy src/ tests/`)
Dashboard:                VERIFIED (npm run typecheck clean; node contract tests 27/27; build clean)
Remote CI Status:         NOT AVAILABLE
Methodological Caveats:
  - Policies are AVAILABLE, not CHOSEN; defaults preserve H01 evidence semantics (D1/D2 pending)
  - 10-slot catalog is INFRA_TEST only; zero alpha authority
  - No deployment, no image build, no container run on Pi from this branch
  - D4 (V2 Homelab resource limits) TEST REQUIRED before any V2 run claim
  - D5 (V2 runtime authorization) NOT granted by this branch
  - Transient feed recovery is a SHADOW seat only; auto-reconnect structurally DISABLED;
    exhaustion preserves causal reason and requires operator resume
```

---

## 14. NEXT SESSION QUICK START

```
ACASH QUICK START — 2026-09-15 Handoff
=======================================
1. git fetch origin; verify origin/main = 9a58ced5011e15c7bcf3975f0e83acf339fa53ce
2. Active work branch: feat/tournament-v2-risk-remediation-10slot
   (base = main @ 9a58ced; tip df1bafa; 13 commits; PUSHED, NOT merged)
3. H01 Attempt 1: EXITED EXIT=2 (ReadTimeout ~7h36m54s); evidence archived (docs/tournament/)
4. V2 REMEDIATION COMPLETE: A (MAX_NOTIONAL), B (funding), C (kill-switch), D (states), E (reason)
5. V2 READINESS: N-slot fanout A..Z, 10-slot INFRA_TEST catalog, --num-slots,
   --auto-mount-infra-candidates, dashboard V2 contract (SHADOW_RUNTIME)
6. V2 FOLLOW-UP COMPLETE: transient feed recovery (FEED_RECOVERING, opt-in, fail-closed),
   staged dynamic candidate admission (SIGHUP / --candidate-add-file), safe NAV sizing (10%),
   journal re-entrant lock fix
7. VERIFICATION: pytest 2353 passed / 12 skipped; mypy 423 files; dashboard 27/27 + build
8. GOVERNANCE: HYP_003=NOT CREATED, R1=NOT STARTED, Paper=NOT AUTHORIZED, capital=$0
9. PENDING: HUMAN DECISION PACKET D1 (funding) / D2 (kill-switch) / D3 (sizing) /
   D4 (Homelab resource-limit TEST REQUIRED) / D5 (NO runtime authorization granted)
10. DO NOT merge branch, DO NOT build/deploy images, DO NOT restart H01 / start H02
11. NO run of 24h continuity has been performed on this branch
```
