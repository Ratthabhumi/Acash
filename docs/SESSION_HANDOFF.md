# ACASH SESSION HANDOFF — H01 Shadow Tournament Risk Findings
## Canonical Current Session Handoff — 2026-09-14

> [!CAUTION]
> **VERIFY CURRENT REPOSITORY, RUNTIME, JOURNAL, AND GOVERNANCE STATE BEFORE ACTING.**
> This document is a navigation snapshot, not eternal source of truth.
> Always `git fetch origin`, verify full 40-char SHAs, and re-inspect
> container/journal state before any consequential action.

> **Document:** `docs/SESSION_HANDOFF.md`
> **This is the single canonical ACASH session handoff.**
> For the archived E3.6 historical checkpoint, see `E3.6-SESSION-HANDOFF.md`.
> **Date:** 2026-09-14 (UTC) / 2026-09-14 (Asia/Bangkok)
> **Status labels used:** FACT | EVIDENCE | INFERENCE | DEFECT | GOVERNANCE BOUNDARY | NEXT ACTION

---

## 1. ACASH Repository — Current State

| Item | Value |
|---|---|
| Repository | `Ratthabhumi/Acash` |
| Branch (main) | `main` |
| Current `origin/main` | `ec86a8596a8aa3d8a85c6e875d2e72adfc9c3ca2` |
| Commit message | `feat(dashboard): migrate UI to ACASH warm neutral standard theme` |
| Parent commit | `78bb2e42c8221ab83e88d29dd0f0256528b59b72` |
| Parent message | `fix(dashboard): null-guard UNASSIGNED slot metrics to prevent toFixed crash` |

**FACT:** `HEAD == origin/main == ec86a8596a8aa3d8a85c6e875d2e72adfc9c3ca2` verified by
`git fetch origin` + `git rev-parse` on 2026-09-14.

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

### 4.3 Revised H01 Status Classification

> [!CAUTION]
> Do NOT write "H01 GREEN". The correct classification is below.

| Dimension | Status |
|---|---|
| H01 infrastructure/feed continuity | **PASS / ongoing** |
| H01 dashboard/telemetry | **PASS** |
| H01 real-order safety | **PASS** |
| H01 execution-risk semantics | **FAIL — remediation required** |
| H01 execution-chain qualification | **NOT ACCEPTABLE AS FULL PASS UNTIL RISK DEFECTS ARE REMEDIATED** |

**GOVERNANCE BOUNDARY:** This FAIL finding does NOT imply any real-money loss.
Everything remains simulated-only. Canonical real capital remains $0.

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
git rev-parse origin/main  # must == ec86a8596a8aa3d8a85c6e875d2e72adfc9c3ca2
git status --short --branch
```
Also re-verify: container status, RestartCount, journal path/size, feed health.

**NEXT ACTION — Step 2: Preserve current H01 evidence**
- Do NOT restart H01 merely to clear or "reset" observed state
- Do NOT discard journal; it is the primary audit evidence for this run
- Preserve journal at `/data/docker/acash/tournament/SHADOW-20260914_073303_142fd6e0_slot_a.journal.jsonl`

**NEXT ACTION — Step 3: Remediation design (engineering review, NOT implementation)**

Address these defects in isolation, in this recommended order:

1. **Defect 1** — max_notional enforcement in `PaperSessionRunner._evaluate_risk()`
2. **Defect 2** — insolvency/margin semantics — define the virtual portfolio boundary policy
3. **Defect 3** — kill-switch position policy — decide: halt+preserve vs halt+liquidate vs halt+operator-gate
4. **Defect 4** — kill-switch execution-state propagation to supervisor/API/dashboard

**NEXT ACTION — Step 4: Tests before implementation**

Write adversarial tests for each defect BEFORE implementing the fix.
Priority order per AGENTS.md:
Boundary -> Malformed -> Contradictory -> Adversarial -> Numerical Stability -> Golden Reference.

**NEXT ACTION — Step 5: Scope isolation**

Keep execution-risk remediation strictly isolated from:
- H02 / research strategy work
- Any alpha qualification path
- Any research governance boundary

**NEXT ACTION — Step 6: Authorization before new run**

Only after remediation is reviewed and explicitly authorized should a new execution-infrastructure
run be considered. Do NOT auto-authorize H02 from this handoff.

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
Implementation Status:    DOCUMENTATION ONLY — no runtime code modified
Contract Enforcement:     N/A (doc-only commit)
Mathematical Authority:   N/A
Local Test Suite:         NOT RUN (doc-only; no code changed)
Type Checker (MyPy):      NOT RUN (doc-only; no code changed)
Remote CI Status:         NOT AVAILABLE
Methodological Caveats:
  - All performance metrics are infrastructure-test accounting state only
  - Kill-switch stop is confirmed but position remains open
  - max_notional enforcement gap is confirmed defect
  - Drawdown >200% reflects real accounting state, not display bug
  - Dashboard route validation used --resolve; direct DNS resolution failed once
```

---

## 14. NEXT SESSION QUICK START

```
ACASH QUICK START — 2026-09-14 Handoff
=======================================
1. git fetch origin; verify origin/main = ec86a8596a8aa3d8a85c6e875d2e72adfc9c3ca2
2. Verify container: acash-shadow running/healthy, RestartCount=0, feed=HEALTHY
3. Verify journal: SHADOW-20260914_073303_142fd6e0_slot_a.journal.jsonl exists, size ~154847
4. Governance: HYP_003=NOT CREATED, R1=NOT STARTED, Paper=NOT AUTHORIZED, capital=$0
5. H01 STATUS: feed/container PASS; execution-risk semantics FAIL (4 defects)
6. DO NOT restart H01 to clear state — preserve journal evidence
7. DO NOT treat H01 as full PASS — risk defects must be remediated first
8. Defect 1: max_notional not enforced in _evaluate_risk() — ~$702k notional at $100k limit
9. Defect 2: virtual insolvency semantics — cash=-$699k, drawdown >200%
10. Defect 3: kill switch halts decisions but 9 BTC position stays open (design decision needed)
```
