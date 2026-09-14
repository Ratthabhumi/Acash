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
- Mounting is **explicit opt-in only**:
  - API: `create_default_shadow_tournament(..., auto_mount_infrastructure_candidates=True)`
  - CLI: `--auto-mount-infra-candidates`
  - Default `False`. The flag mounts only INFRA_TEST candidates; zero alpha
    candidates are ever auto-mounted.

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