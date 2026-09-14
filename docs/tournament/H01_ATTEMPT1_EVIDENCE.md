# H01 Shadow Tournament — Attempt 1 Evidence

> [!CAUTION]
> **This document is EVIDENCE PRESERVATION, not a qualification certificate.**
> The run below is a **simulated infrastructure exercise** only. Zero real orders,
> zero real capital, zero research admission. It exercises
> Signal → Risk → Order → Simulated Fill → Portfolio → Journal → Replay.

> **Branch context:** authored on `feat/tournament-v2-risk-remediation-10slot`
> (base `main` `9a58ced5011e15c7bcf3975f0e83acf339fa53ce`).
> **Status:** H01 Attempt 1 CLOSED (24h continuity NOT ACHIEVED).

---

## 1. Run Identity

| Item | Value |
|---|---|
| Tournament ID | `SHADOW-20260914_073303_142fd6e0` |
| Runtime image | `acash:shadow-tournament-bb6d49c` |
| Runtime ACASH commit | `bb6d49c41fefef42c288ebdfce597572433423f9` |

## 2. Terminal Run State (FACT)

| Item | Value |
|---|---|
| Container start (UTC) | 2026-09-14T07:33:01Z |
| Container finish (UTC) | 2026-09-14T15:09:55Z |
| Approx runtime | 7h36m54s |
| Exit code | `EXIT=2` |
| 24h continuity target | **NOT ACHIEVED** |
| Final failure | `BinancePublicKlinesFeed.poll_next_bar` → `ReadTimeout` |
| Response | Fail-closed halt (no auto-reconnect, no auto-restart) |

**EVIDENCE:** The run did not reach its first nominal 24h checkpoint
(2026-09-15T07:33:03Z). It halted fail-closed on a feed ReadTimeout after
approximately 7h36m54s.

## 3. Artifact Inventory (EVIDENCE)

Path root: `/data/docker/acash/tournament/`

| Artifact | Size |
|---|---|
| Final journal (slot A, jsonl) | 156814 bytes |
| Snapshot ledger | 906 bytes |
| Sealed manifest (slot A, json) | 1772 bytes |

## 4. Journal Terminal Sequence (FACT)

| Seq | Event | Details |
|---|---|---|
| 146 | `RECONCILIATION_COMPLETED` | PASS — 146 events, 15 orders, 15 fills, 0 violations |
| 147 | `SESSION_STOPPED` | `reason=NORMAL_SHUTDOWN` (⚠ see D5) |

> [!NOTE]
> Actual root cause of terminal halt: feed `ReadTimeout` fail-closed.
> The journal recorded `SESSION_STOPPED reason=NORMAL_SHUTDOWN`, which **does
> not preserve the causal terminal reason**. This is shutdown-reason
> observability defect **D5** (see `./TOURNAMENT_V2_10SLOT_DESIGN.md`).

## 5. Slot A Evidence

### 5.1 Strategy (FACT)

| Item | Value |
|---|---|
| Strategy ID | `INFRA-TEST-MOMENTUM-SYNTHETIC-001` |
| Version | 1.0.0 |
| Class | `InfrastructureTestStrategy` |
| Governance | `INFRASTRUCTURE_TEST_STRATEGY_ONLY` |

### 5.2 Risk Configuration (FACT)

| Parameter | Value |
|---|---|
| `initial_cash` | 1000.00 |
| `max_position_units` | 10.0 |
| `max_notional` | 100000.0 |
| `max_daily_loss` | 100.0 |

### 5.3 Observed Accounting State (EVIDENCE)

| Metric | Value |
|---|---|
| Max abs position observed | 10.0 BTC |
| Final open position | LONG 9.0 BTC |
| Final cash | -699728.123 |
| Final avg entry | 77846.1644304 |
| Final realized PnL | -112.6371264 |
| Initial virtual NAV | 1000.0 |
| Max drawdown pct | 201.99 |
| Exposure pct | > 20000 |
| Risk utilization pct (vs 10.0 units) | 90.0 |

### 5.4 Kill-Switch Journal Sequence (FACT)

| Seq | Event | Key Fields |
|---|---|---|
| 144 | `KILL_SWITCH_TRIGGERED` | `trigger_reason=MAX_DAILY_LOSS`, `trigger_type=DAILY_LOSS_LIMIT` |
| 145 | `RISK_REJECTED` | `daily_realized_loss=112.6371264`, `max_daily_loss=100.0` |

**FACT:** After SEQ 144, no further `FILL_SIMULATED` or `POSITION_UPDATED`
events occurred in the journal snapshot. The kill switch DID stop subsequent
simulated execution. The 9.0 BTC simulated position remained open (see D3).

## 6. Defect Links

| Defect | Summary | Evidence |
|---|---|---|
| D1 | `max_notional` NOT enforced in `PaperSessionRunner._evaluate_risk()` | 9-10 BTC at ~$77-78k → ~$702k notional vs $100k limit; `exposurePct` ≈ 26,685% |
| D2 | Virtual insolvency / no margin boundary | `cash = -699,728.123`, max drawdown 201.99% |
| D3 | Kill switch does not flatten existing position | SEQ 144 halts decisions; 9.0 BTC stays open |
| D4 | Execution state not exposed (slot/supervisor/dashboard report RUNNING after kill switch) | overall/slot status stayed `RUNNING` after SEQ 144 |
| D5 | Terminal shutdown reason not preserved (`NORMAL_SHUTDOWN`) | SEQ 147 vs actual feed ReadTimeout cause |

## 7. Governance Boundaries (unchanged)

- HYP_003 NOT CREATED · R1 NOT STARTED · Backtesting LOCKED
- Paper NOT AUTHORIZED · Live LOCKED
- Canonical capital $0.00 · NO_REAL_ORDERS=true
- Auto reconnect DISABLED · Operator resume REQUIRED

**GOVERNANCE BOUNDARY:** No remediation decision in this document authorizes
H02, a new run, Paper, Live, or backtesting. All such decisions remain open
with the Human.

---

### Verification Ledger
- Implementation Status: DOCUMENTATION ONLY — no runtime code modified
- Contract Enforcement: N/A (doc-only)
- Mathematical Authority: N/A
- Local Test Suite: NOT RUN (doc-only)
- Type Checker (MyPy): NOT RUN (doc-only)
- Remote CI Status: NOT AVAILABLE
- Methodological Caveats:
  - All performance metrics are infrastructure-test accounting state only
  - Kill-switch stop confirmed; open simulated position is a design decision (D3)
  - max_notional enforcement gap confirmed (D1)
  - Shutdown reason `NORMAL_SHUTDOWN` does not preserve causality (D5)