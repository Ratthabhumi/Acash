# HYP_011 Prospective Shadow Observation Engine — Specification

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_PROSPECTIVE_SHADOW_ENGINE_PRE_DATA_READINESS]
[STATE: PROSPECTIVE_SHADOW_ENGINE_READY_WAITING_FOR_ACTIVATION_SESSION_COMPLETION]
[MARKET_DATA_ACCESSED: ZERO]
```

- **Readiness manifest:** `docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_ENGINE_READINESS.json`
- **Activation binding (unchanged):** 2026-09-28T13:30:00Z; missed [2026-09-25]; no backfill.

## 1. Modules

- `src/acash/research/hyp_011/shadow.py` — activation derivation (same-day
  correct), close_utc completion guard with explicit now_utc, missed-session
  derivation, append-only `ShadowState` with duplicate/out-of-order/early/
  future/recent-stress/quarantine guards, 504+2 minimums.
- `src/acash/research/hyp_011/shadow_ops.py` — single-session strategy
  processing (entitlement → payable settlement → open transaction → EOD
  valuation), independent SPY benchmark leg, SHA-chained append-only
  observation writer with tamper-evident state pins.
- `scripts/process_hyp_011_prospective_shadow.py` — single-session runner:
  dry-run default; live requires `--execute-network`, derives the unique next
  expected session, enforces idempotence (already-processed → no action, zero
  network), validates all guards pre-network. One session per invocation; no
  ranges, no catch-up.

## 2. Data Contract (Per Session, ACWI/AGG/SPY × Split/Raw)

Exactly one target session; no spill/duplicates; OHLCV valid; split/raw
aligned; every HTTP attempt counted; raw bytes hashed. Corporate actions:
frozen sponsors, causal availability only, ex-date entitlement from
prior-close holdings, payable-gated spendability, no double count, split
fail-closed. Rebalance: initial allocation at activation open (not counted as
annual); scheduled first-open-of-year thereafter (counted).

## 3. Locks

Zero network in this task. Observed sessions 0, rebalances 0. No interim
final gates (`NON_DECISIVE_PROSPECTIVE_SHADOW_MONITORING` only). Paper
NOT_AUTHORIZED, live LOCKED, capital $0.00, NO_REAL_ORDERS=true.
R1/R2/R3/activation artifacts unmutated.

## 4. Next Human Action

After activation-session canonical close:
`AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_0001` (process Sep-28 exactly once).
