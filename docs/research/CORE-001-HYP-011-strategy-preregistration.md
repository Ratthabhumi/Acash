# CORE-001 / HYP_011 Strategy Preregistration (FROZEN)

```text
PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_R1_SEAL
OPEN_BEFORE_R1_UNRESOLVED_COUNT = 0
HYP_011 = PROPOSED_NOT_PREREGISTERED
EMPIRICAL_EXECUTION = NOT_AUTHORIZED
```

- **Document ID:** `docs/research/CORE-001-HYP-011-strategy-preregistration.md`
- **Authorization:** `AUTHORIZE_CORE_001_PARK_HYP_010_AND_PREREGISTER_HYP_011_R1`
- **CORE_ID:** `CORE-001` | **HYPOTHESIS_ID:** `HYP_011` | **Version:** `v1.0`
- **Working title:** Global 80/20 Strategic Allocation Core
- **Trial count:** `K = 1` single specification. No search. No tuning.
- **Parent hypothesis:** None (de novo candidate #3; predecessors terminal/parked, not amended).

All decisions below are supplied by the external research authority, frozen
before any HYP_011 performance observation. Binding detail mirrors
`docs/phase14/CORE_001_HYP_011_RESEARCH_INCEPTION.md` §§3–9.

## 1. Holdings / Weights / Roles

ACWI 0.80 (GLOBAL_EQUITY_GROWTH_ASSET) + AGG 0.20
(US_INVESTMENT_GRADE_BOND_DIVERSIFIER). LONG ONLY, leverage ≤ 1.0, no
margin/short/options/futures/leveraged-ETF/synthetic. No signal of any kind;
sole state `STATIC_TARGET_ALLOCATION_80_20`. No SPY holding; residual
operational cash (0% return) from whole-share sizing only.

## 2. Rebalance (Annual, Deterministic Whole-Share Solver)

Initial allocation at first eligible canonical U.S. equity session open on or
after partition start; scheduled rebalance at first eligible open of each new
calendar year to 80/20. SELLS first, then BUYS at adverse fills
(buy ×1.0002 / sell ×0.9998 baseline; ×1.0010/×0.9990 stress + 2x canonical
sell-side regulatory fees; commission 0). Unpaid receivables count in equity,
excluded from trade budget. If fills/fees would drive spendable cash negative:
iteratively decrement a proposed BUY one share, each time minimizing increase
in ABS(w_ACWI − 0.80) + ABS(w_AGG − 0.20); tie-break AGG first; until
projected cash ≥ 0. No borrowing, no discretion.

## 3. Data / Corporate Actions / Costs

ALPACA_HISTORICAL_STOCK_BARS, ACWI/AGG (+SPY benchmark), 1Day, SIP; raw for
execution/valuation + split lineage qualification; no fallback/splicing/vendor
adjusted-close authority. Distributions: ACWI/AGG → BLACKROCK_ISHARES_OFFICIAL,
SPY → STATE_STREET_SPDR_OFFICIAL (ex-date + amount + payable required; gaps →
`BLOCKED_DIVIDEND_AUTHORITY_COVERAGE_GAP`; no D=0 inference; no inferred
payable). Splits: official authority or `BLOCKED_SPLIT_EVENT_CONTRACT`.
Simulated starting AUM 100000.00 (real 0.00). Portfolio dividends: ex-date
receivable in equity, spendable on payable only, no double count.

## 4. Benchmark / Partitions / Prospective / Gates

Primary gating benchmark SPY BUY AND HOLD (independent 100000.00, whole
shares, 2bps buy, same CA economics, no rebalance/liquidation; return
outperformance NOT required, G4 drawdown-only). Secondary informational ACWI
BUY AND HOLD (non-binding). Historical 2016-01-01..2024-12-31 (exposed
replication, not researcher-blind). Recent stress 2025-01-01..2026-08-14 (not
pristine, non-decisive, separate authorization, no rescue). Quarantine
2026-08-15..prospective-exclusive (zero access). Prospective first eligible
regular open strictly after HYP_011 R1 commit (locked at R1); final evaluation
needs ≥504 sessions AND ≥2 annual rebalances (later); same G1–G6; no tuning.
Gates G1–G6 per CORE-001 philosophy (return > 0, Sharpe ≥ 0.50 [252/ddof1/rf0,
zero-variance fail-closed], MDD ≤ 0.35, core MDD < SPY B&H MDD, 10bps-stress
return > 0, no material contract failure), conjunction, no override.
Historical verdicts: supported-for-prospective-shadow / not-supported-no-
prospective-authorization / blocked-invalid-contract. Prospective:
support-for-human-review / terminal-not-supported-prospectively (pass never
auto-authorizes trading).

## 5. Anti-Optimization / Continuity

K = 1. Post-R1 redesign forbidden (weights, universe, filters, frequency,
thresholds, gates, dates, rescue uses) — any redesign needs a NEW hypothesis.
CORE-001 objective remains open; HYP_009 #1 terminal; HYP_010 #2 parked
non-falsified; HYP_011 #3, not an amendment.
