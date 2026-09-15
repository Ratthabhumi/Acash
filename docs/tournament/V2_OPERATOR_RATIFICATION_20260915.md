# V2 Operator Ratification — 2026-09-15

> **Document:** `docs/tournament/V2_OPERATOR_RATIFICATION_20260915.md`
> **Status:** FACT — HUMAN AUTHORIZATION RECORD
> **Date:** 2026-09-15 (UTC)

## Ratified Decisions

### D1 — Portfolio Funding Policy
**CASH_CONSTRAINED_SPOT**

Reject simulated fills that would make virtual cash negative (fail-closed). Historical fixed-quantity behavior remains only for regression/historical compatibility and is NOT the V2 operational sizing policy.

### D2 — Kill-Switch Open-Position Policy
**HALT_AND_REQUIRE_OPERATOR_RESOLUTION**

Kill switch + `operatorResolutionRequired=True` surfaced in `TournamentSlot` and API JSON. No forced fills. Evidence preserved on kill.

### D3 — V2 Infrastructure Sizing
**NAV_RELATIVE_PERCENT**
`nav_sizing_notional_pct = 10.0`

NAV-relative sizing 10% for V2 INFRA_TEST candidates. Fixed-quantity (qty=1.0) remains only for historical compatibility.

### D4 — Homelab Capacity Validation
**AUTHORIZED**

A bounded 10-slot INFRASTRUCTURE_TEST capacity drill is authorized solely to validate infrastructure capacity/isolation/resource behavior. It is NOT alpha evidence, NOT research qualification, NOT Paper, NOT Live.

### D5 — Conditional V2 Runtime
**AUTHORIZED ONLY IF D4 PASSES ALL GATES**

After a successful D4 capacity drill, start ONE new 24-hour Shadow V2 operational run with exactly 3 INFRASTRUCTURE_TEST candidates.

Runtime scope:
- BTCUSDT
- M1
- exactly 3 initially active INFRA_TEST slots
- same canonical finalized feed fanout
- NAV-relative sizing 10%
- CASH_CONSTRAINED_SPOT
- HALT_AND_REQUIRE_OPERATOR_RESOLUTION
- controlled transient feed recovery ENABLED
- recovery remains bounded/fail-closed
- canonical REAL capital = $0
- NO_REAL_ORDERS=true
- simulated orders/fills only

## Explicit Exclusions

This authorization DOES NOT authorize:
- HYP_003 creation
- R1 start
- Backtesting
- Paper Trading
- Live Trading
- real broker connectivity
- real capital
- strategy/alpha qualification

| Item | Status |
|---|---|
| HYP_003 | NOT CREATED |
| R1 | NOT STARTED |
| Backtesting | LOCKED |
| Paper Trading | NOT AUTHORIZED |
| Live Trading | LOCKED |
| Canonical capital | $0.00 |
| NO_REAL_ORDERS | true |

## Verification

- Source-level blockers: VERIFIED CLOSED (numeric hardening complete)
- Test suite: 2384 passed / 12 skipped
- MyPy: 423 source files clean
- Dashboard: 27/27 tests, typecheck clean, build clean
- GitHub branch: `feat/tournament-v2-risk-remediation-10slot` = `8db9bf5...`, ahead 21/behind 0

This document records human scope. It is not alpha qualification.
