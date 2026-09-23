# CORE-001 / HYP_009 Research Inception (PROPOSED — NOT PREREGISTERED)

[DOCUMENT ID: docs/phase14/CORE_001_HYP_009_RESEARCH_INCEPTION.md]

[AUTHORIZATION: AUTHORIZE_RETIRE_HYP_008_AND_OPEN_CORE_001_HYP_009_IMPLEMENTATION]

[CANONICAL HEAD AT INCEPTION: a231234 (parent 47e95def3ad98503f41ce4549986d53f65102cb5)]

[STATE: PROPOSED_NOT_PREREGISTERED]

[IMPLEMENTATION-ONLY RECORD — NO LITERATURE RESEARCH, NO STRATEGY COMPARISON, NO BACKTEST]

## 1. Lineage

| Field | Value |
|---|---|
| CORE_ID | `CORE-001` |
| HYPOTHESIS_ID | `HYP_009` |
| STATE | `PROPOSED_NOT_PREREGISTERED` |
| WORKING TITLE | `SPY Monthly 10-Month SMA Long/Cash Core` |
| STRATEGY FAMILY | `LONG_HORIZON_MOVING_AVERAGE_TREND_FILTER` |
| RESEARCH PRIORITY | `CORE_FIRST` |
| SELECTION STATUS | `SELECTED_PRE_PERFORMANCE_FROM_EXTERNAL_LITERATURE_AND_OPERATIONAL_SIMPLICITY` |

No alternative-family comparison is authorized. CORE-001 v1 is exactly the
supplied design in §2–§12. The following are explicitly NOT substituted:

- 12-month TSMOM; dual-horizon trend; volatility-managed trend; long/short
  trend; multi-asset trend.

HYP_009 does not reuse, rename, or continue the retired HYP_008 / MEC-0018
lineage. HYP_008 remains `RETIRED_BEFORE_PREREGISTRATION` (see
`docs/phase14/HYP_008_PRE_R1_RETIREMENT.md`).

## 2. Instrument and Frequency

- Instrument: `SPY`.
- Frequency: `MONTHLY`.
- Decision date: `LAST_REGULAR_TRADING_SESSION_OF_EACH_CALENDAR_MONTH`.

## 3. Direction States and Signal

Direction states: `LONG`, `CASH`. No `SHORT` state.

Signal: `LONG` iff current month-end signal level is strictly greater than the
arithmetic mean of the current and prior 9 month-end signal levels
(`10_MONTH_SIMPLE_MOVING_AVERAGE`).

- `signal_level > sma_10m` → `LONG`.
- Else → `CASH`.
- Equality (`signal_level == sma_10m`) → `CASH`.
- No tolerance band. No hysteresis. No confirmation indicator. No stop loss.
  No trailing stop. No secondary filter. No volatility filter. No liquidity
  filter. No macro filter. No machine learning. No discretionary override.

## 4. Position Sizing

- `LONG` state: 100% SPY notional exposure.
- `CASH` state: 0% SPY exposure.
- `MAX_GROSS_LEVERAGE`: `1.0`. No margin leverage. No leveraged ETF.
  No synthetic leverage. No short exposure.
- `VOLATILITY_TARGETING`: `false`. Volatility targeting, if ever researched,
  must be a separate future hypothesis or additive authorized research lineage.

## 5. Timing Contract

Signal may only be computed after the official final eligible regular-session
data for decision day t are complete and qualified. No trading at the same
close used to construct the signal.

- Month-end close t → signal observable only after close t → earliest
  execution = next eligible regular-session open t+1.
- Execution timing: `NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL`.
- No same-close execution. No look-ahead.

## 6. Signal Series vs Execution Series

- Signal role: `TOTAL_RETURN_OR_EQUIVALENT_CAUSALLY_RECONSTRUCTED_SERIES` —
  economically continuous SPY ownership, corporate-action safe.
- Preferred future implementation: deterministic causal total-return month-end
  signal levels from qualified SPY prices + authoritative split history +
  authoritative dividend history.
- Primary dividend authority (reuse where compatible):
  `STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS`.
- Execution prices remain `RAW MARKET PRICES`. Never conflate signal series
  with execution price series.

## 7. Cash Accounting

Scientific v1 baseline: `CASH_RETURN = 0.0` (conservative; avoids a second
return-generating asset and T-bill/risk-free regime contamination).

Do NOT add T-bill yield, SOFR, money-market return, or Treasury ETF return.
Those may only be future secondary context under separate authority.

## 8. Benchmark

Primary future benchmark: `SPY_BUY_AND_HOLD` with economically equivalent
corporate-action treatment. CORE-001 is NOT required to beat buy-and-hold
total return in every period. Future scientific emphasis: drawdown control,
risk-adjusted robustness, friction survival, regime persistence,
deployability, operational simplicity. No numerical gates are authorized.

## 9. Turnover, Warm-Up, Calendar, Missing Data

- Binary state system. Trade only on state change (`CASH -> LONG` or
  `LONG -> CASH`). No daily resizing, no rebalance band, no partial exposure,
  no scaling ladder, no volatility sizing. Expected turnover class: `LOW`.
- Warm-up minimum: `10` completed month-end signal observations. Before full
  warm-up: `NO SIGNAL`. Fail closed.
- Calendar authority: canonical NYSE calendar in repository, including
  already-sealed unscheduled closure corrections. A valid official early-close
  session may serve as month-end decision date if it is the final eligible
  NYSE trading session of that calendar month and complete under calendar
  authority. Holidays skip naturally. No synthetic session.
- Strict fail-closed on missing data. Forbidden: interpolation, forward-fill,
  synthetic month-end value, substitute provider without explicit
  authorization. Missing required signal input → `BLOCK / FAIL CLOSED`.

## 10. Out of Scope

CORE-001 / HYP_009 is `LONG/CASH ONLY`. No `SHORT` branch. A future long/short
core strategy must be a separate lineage (e.g. a future CORE-002/HYP-XXX),
which is NOT reserved or created here. No shorting infrastructure here.

## 11. Sample Architecture (Conceptual Lifecycle Only)

`DESIGN / IMPLEMENTATION VERIFICATION → LOCKED OOS → FRICTION / STRESS →
PROSPECTIVE SHADOW → HUMAN REVIEW → PAPER → SMALL REAL CAPITAL`.

Exact sample dates: `OPEN_BEFORE_R1`. Existing HYP_007 M3 is NOT automatically
HYP_009 OOS. HYP_007 M3 is NOT accessed.

## 12. OPEN_BEFORE_R1 Items

- `OPEN_BEFORE_R1_TOTAL_RETURN_SIGNAL_CONSTRUCTION`
- `OPEN_BEFORE_R1_EXECUTION_COST_MODEL`
- `OPEN_BEFORE_R1_SAMPLE_PARTITION_DATES`
- `OPEN_BEFORE_R1_LOCKED_OOS_BOUNDARY`
- `OPEN_BEFORE_R1_PROSPECTIVE_BOUNDARY`

Future R1 execution-cost contract must include next-session-open execution,
realistic commission, realistic spread/slippage, and fail-closed missing-cost
authority. Do not import HYP_007 intraday NBBO complexity. No arbitrary
friction values are assigned here.

## 13. Authority Boundary

- Formal R1 registration: NOT PERFORMED (proposed only).
- ResearchReInceptionGate: NOT INVOKED.
- Backtest: NOT AUTHORIZED, NOT EXECUTED.
- Historical signals / trades / P&L / Sharpe / MDD: ZERO (none computed).
- HYP_007 M3 accessed: `false`. Quarantine gap accessed: `false`.
- Paper: `NOT_AUTHORIZED`. Live: `LOCKED`.
- Capital: `$0.00`. `NO_REAL_ORDERS=true`.

## 14. Next Human Action

`REVIEW_CORE_001_HYP_009_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION`
