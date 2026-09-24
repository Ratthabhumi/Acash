# CORE-001 / HYP_010 Strategy Preregistration (FROZEN)

```text
PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_R1_SEAL
OPEN_BEFORE_R1_UNRESOLVED_COUNT = 0
HYP_010 = PROPOSED_NOT_PREREGISTERED
EMPIRICAL_EXECUTION = NOT_AUTHORIZED
```

- **Document ID:** `docs/research/CORE-001-HYP-010-strategy-preregistration.md`
- **Authorization:** `AUTHORIZE_CORE_001_HYP_010_R1_PREREGISTRATION`
- **CORE_ID:** `CORE-001` | **HYPOTHESIS_ID:** `HYP_010` | **Version:** `v1.0`
- **Working title:** ETF-Native Global Equity Dual Momentum Core
- **Trial count:** `K = 1` single specification. No search grid. No tuning.
- **Parent hypothesis:** None (de novo candidate #2; HYP_009 terminal, not amended).

All research decisions below were supplied by the external research authority
and frozen before any HYP_010 performance observation. Binding detail mirrors
`docs/phase14/CORE_001_HYP_010_RESEARCH_INCEPTION.md` §§4–10.

## 1. ETF Universe / Roles

SPY = US equity candidate; VEU = non-US equity candidate; AGG = defensive
holding; BIL = Treasury-bill hurdle, SIGNAL ONLY (never a v1 holding). Targets:
SPY/VEU/AGG only. No QQQ/VXUS/BND/SHY/TLT/GLD/sector ETFs. No substitution.

## 2. Signal Contract

Causal total-return levels per signal asset (SPY/VEU/BIL; AGG history qualified
for accounting though its momentum is unused): split-adjusted closes,
`G_i,t = (P_i,t + D_i,t)/P_i,t-1`, `TR_i,t = TR_i,t-1 * G_i,t`, ex-date
economics, no vendor adjusted-close authority, no fill/interpolation/inference.
Execution/valuation at raw market prices.

## 3. Momentum + Target Rule (K=1)

`M12_i(t) = TR_i(t)/TR_i(t-12) - 1` (exactly 12 calendar months earlier; no
multi-horizon composite, no skip-month, no MA, no vol adjust, no z-score).
ABSOLUTE: risk-on iff `SPY_M12 > BIL_M12`, else TARGET = AGG (equality → AGG).
RELATIVE (if risk-on): `SPY_M12 >= VEU_M12` → SPY else VEU (equality → SPY).

## 4. Position / Timing / Warmup / Partitions

100% target holding (whole shares, residual cash at 0), leverage ≤ 1.0, no
short/options/futures/leveraged-ETF/synthetic/weights/vol-targeting. Trade only
on target change. Decision after month-end close; execution next eligible open.
Warmup 13 month-ends (Jan-2016..Jan-2017); first decision Jan-2017 month-end.
Historical exposed replication (first execution → 2024-12-31, NOT
researcher-blind; Dec-2024 pending if execution in 2025). Recent stress
2025-01-01..2026-08-14 (NOT pristine, NON_DECISIVE, no rescue/authorization).
Quarantine 2026-08-15..prospective-exclusive (ZERO ACCESS). Prospective first
open strictly after R1 commit (LOCKED at R1); final evaluation needs ≥24
decisions AND ≥504 sessions (later of the two); same G1–G6; no interim tuning.

## 5. Costs / Dividends / Benchmark / Gates

Simulated starting AUM 100000.00 (real 0.00). Baseline 2bps/side, stress
10bps/side + 2x canonical sell-side regulatory fees, commission 0, whole
shares, no negative cash/leverage. Missing applicable fee authority →
`BLOCKED_FEE_AUTHORITY`. Portfolio dividends: ex-date receivable, spendable on
payable only, no double count, missing payable → `BLOCKED_DIVIDEND_PAYMENT_DATE_CONTRACT`.
Sponsor authorities: SPY/BIL → STATE STREET/SPDR; VEU → VANGUARD; AGG →
BLACKROCK/ISHARES (ex-date + amount + payable required; gaps →
`BLOCKED_DIVIDEND_AUTHORITY_COVERAGE_GAP`). Splits: bound authoritative event
or `BLOCKED_SPLIT_EVENT_CONTRACT`. Bars: ALPACA_HISTORICAL_STOCK_BARS,
SPY/VEU/AGG/BIL, 1Day, SIP, split for signal / raw for execution; no fallback.
Benchmark: independent SPY buy-and-hold 100000.00 (return outperformance NOT
required; G4 drawdown-only). Gates G1–G6 per §15 of the authorizing prompt,
conjunction, no override. Verdicts per §§16–18 (historical / recent-stress
context / prospective).

## 6. Anti-Optimization / Continuity

K = 1. Post-R1 redesign forbidden (horizon, universe, comparator, filters,
ties, thresholds, gates, dates, rescue uses) — any redesign needs a NEW
hypothesis. CORE-001 objective (simple deployable long-only 1x low-turnover
core) remains open; HYP_009 candidate #1 terminal; HYP_010 candidate #2, not an
amendment.
