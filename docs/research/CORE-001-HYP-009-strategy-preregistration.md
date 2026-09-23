# CORE-001 / HYP_009 Strategy Preregistration (FROZEN)

```text
PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_R1_SEAL
OPEN_BEFORE_R1_UNRESOLVED_COUNT = 0
HYP_009 = PROPOSED_NOT_PREREGISTERED
EMPIRICAL_EXECUTION = NOT_AUTHORIZED
```

- **Document ID:** `docs/research/CORE-001-HYP-009-strategy-preregistration.md`
- **Authorization:** `AUTHORIZE_CORE_001_HYP_009_R1_PREREGISTRATION`
- **CORE_ID:** `CORE-001` | **HYPOTHESIS_ID:** `HYP_009` | **Version:** `v1.0`
- **Working title:** SPY Monthly 10-Month SMA Long/Cash Core
- **Strategy family:** `LONG_HORIZON_MOVING_AVERAGE_TREND_FILTER`
- **Trial count:** `K = 1` single specification. No search grid. No parameter tuning.
- **Parent hypothesis:** None (de novo core lineage; HYP_008 / MEC-0018 retired, not reused).

All research decisions below were supplied by the external research authority.
This document freezes them before any HYP_009 performance observation.

---

## 1. Strategy Specification (Binding, Unchanged from Inception)

- Instrument `SPY`, frequency `MONTHLY`, decision date
  `LAST_REGULAR_TRADING_SESSION_OF_EACH_CALENDAR_MONTH`.
- States `LONG` / `CASH` only. `LONG` iff month-end `signal_level > sma_10m`
  (arithmetic mean of current + prior 9 month-end levels); equality → `CASH`.
- No tolerance, no hysteresis, no confirmation, no stop-loss, no trailing stop,
  no secondary/volatility/liquidity/macro filter, no ML, no override.
- Sizing: LONG 100% SPY notional, CASH 0%. `MAX_GROSS_LEVERAGE = 1.0`.
  No margin/leveraged-ETF/synthetic/short exposure. `VOLATILITY_TARGETING = false`.
- Timing: signal observable only after month-end close t; earliest execution =
  `NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL` (Market-on-Open / OPG intent).
- Rebalance: trade only on state change. Turnover class `LOW`.
- Warm-up: 10 completed month-end observations; before that `NO_SIGNAL` (fail-closed).
- Calendar: canonical ACASH NYSE calendar incl. sealed unscheduled closures.
  Early-close session valid as month-end only if final eligible session of month.
- Missing data: fail-closed. No interpolation/forward-fill/synthetic/substitution.
- Cash: `CASH_RETURN = 0.0`. Benchmark: `SPY_BUY_AND_HOLD` (equivalent
  corporate-action economics). No beat-the-benchmark gate.

## 2. Total-Return Signal Construction (RESOLVED)

- Provider: `ALPACA_HISTORICAL_STOCK_BARS`, `/v2/stocks/SPY/bars`, `1Day`, `sip`.
- Signal-price adjustment: `split` only (NOT dividend, NOT all).
- Dividend authority: `STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS`.
- Daily factor `G_t = (P_t + D_t) / P_{t-1}` with split-adjusted closes `P`
  and ex-date cash distributions `D`; wealth index `TR_0 = 1.0`,
  `TR_t = TR_{t-1} * G_t`; month-end `signal_level` = `TR_t` on final eligible
  session; SMA over current + prior 9 month-ends. Ex-date economics only.
- Missing dividend lineage → FAIL CLOSED. Vendor dividend-adjusted close is NOT
  primary authority. Execution prices remain raw market prices.

## 3. Execution & Transaction-Cost Contract (RESOLVED)

- Historical baseline proxy: RAW next-session daily OPEN (`adjustment=raw`).
- Baseline slippage 2 bps/side: BUY `raw_open * 1.0002`, SELL `raw_open * 0.9998`.
- No spread subtraction beyond this. No intraday NBBO dependency.
- Commission baseline `0.00` (Alpaca self-directed API deployment).
- Regulatory fees: reuse canonical ACASH sell-side authority (SEC 31, FINRA TAF,
  CAT if applicable) by trade date. No short-borrow fee (never shorts).
- Stress: 10 bps/side (`* 1.0010` / `* 0.9990`), 2x regulatory fees, commission
  stays 0 unless broker authority changes. Identical signal/state path.

## 4. Sample Partitions (RESOLVED)

| Partition | Dates | Role / Classification |
|---|---|---|
| Research start | 2016-01-01 | provider/data-contract availability basis |
| Warm-up | 2016-01-01 .. 2016-10-31 | first 10 month-end observations; ZERO P&L/metrics |
| M1 | 2016-11-01 .. 2020-12-31 | `DESIGN_AND_IMPLEMENTATION_REPLICATION_SAMPLE`, `HISTORICAL_EXPOSED_REPLICATION` |
| M2 | 2021-01-01 .. 2024-12-31 | `LOCKED_HISTORICAL_OOS`, `LOCKED_HISTORICAL_OOS_NOT_PRISTINE_RESEARCHER_BLIND` |
| M3 | 2025-01-01 .. 2026-08-14 | `PUBLICLY_EXPOSED_RECENT_STRESS_SAMPLE`, `NOT_PRISTINE_OOS` |
| Quarantine | 2026-08-15 .. prospective-start-exclusive | `STRICT_ZERO_ACCESS_PRE_PROSPECTIVE_GAP` |
| Prospective | first NYSE regular-session open strictly after R1 commit timestamp | `PROSPECTIVE_ONLY`, `LOCKED_ZERO_ACCESS` at R1 |

- M2 firewall: no M2 market-data reads until R1 sealed + M1 dataset complete +
  M1 result sealed + explicit human authorization. No automatic M2 execution.
- M3: not permitted to rescue a failed M2; if M2 fails continuation gates, M3
  remains locked. No automatic M3 execution.
- HYP_009 builds its own daily dataset under its own lineage. HYP_007
  parquet/ledgers/results/M3 MUST NOT be read as HYP_009 evidence.
- Provider: no substitution, no splicing. Missing 2016-01-01 coverage under
  current entitlement → `BLOCKED_DATA_ENTITLEMENT`, return to human.

## 5. Acceptance Gates G1–G6 (FROZEN, NET OF BASELINE FRICTION)

- G1: `NET_TOTAL_RETURN > 0`
- G2: `NET_ANNUALIZED_SHARPE >= 0.50` (periods_per_year=252, ddof=1,
  risk_free_rate=0; zero variance → FAIL CLOSED)
- G3: `MAX_DRAWDOWN <= 0.35`
- G4: `CORE_MAX_DRAWDOWN < SPY_BUY_AND_HOLD_MAX_DRAWDOWN` (identical partitions,
  equivalent corporate-action economics)
- G5: `10_BPS_PER_SIDE_STRESS_NET_TOTAL_RETURN > 0`
- G6: `NO_MATERIAL_DATA_OR_EXECUTION_CONTRACT_FAILURE == TRUE`
- Conjunction: `G1 AND G2 AND G3 AND G4 AND G5 AND G6`. No override.
- M1: contract-invalid → `BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT`;
  all pass → `M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION`;
  else → `M1_NOT_SUPPORTED_NO_M2_AUTHORIZATION`.
- M2: identical frozen strategy+gates; all pass →
  `M2_SUPPORTED_FOR_RECENT_STRESS_CONSIDERATION`;
  else → `FAIL_CORE_EDGE_NOT_SUPPORTED` (no automatic M3).

## 6. Anti-Optimization Covenant

`K = 1`. No search grid. No parameter tuning. No gate relaxation after results.
No earlier-data addition after results without a new hypothesis. Sample dates
chosen on provider/data-contract availability, NOT observed performance.

## 7. Authority Boundary

R1 preregistration/governance only. ZERO Alpaca/SSGA requests, ZERO price
inspection, ZERO signals/P&L/Sharpe/MDD/benchmark/stress results in this task.
Paper `NOT_AUTHORIZED`, live `LOCKED`, capital `$0.00`, `NO_REAL_ORDERS=true`.
Next required step: `AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION`.
