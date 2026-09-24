# CORE-001 / HYP_011 Research Inception (PROPOSED — NOT PREREGISTERED)

[DOCUMENT ID: docs/phase14/CORE_001_HYP_011_RESEARCH_INCEPTION.md]

[AUTHORIZATION: AUTHORIZE_CORE_001_PARK_HYP_010_AND_PREREGISTER_HYP_011_R1]

[CANONICAL HEAD AT INCEPTION: c70db723415da58f5769167567029454af4325b7]

[STATE: PROPOSED_NOT_PREREGISTERED]

[IMPLEMENTATION-ONLY RECORD — NO LITERATURE RESEARCH, NO BACKTEST, NO PERFORMANCE]

## 1. Lineage

| Field | Value |
|---|---|
| CORE_ID | `CORE-001` |
| HYPOTHESIS_ID | `HYP_011` |
| STATE | `PROPOSED_NOT_PREREGISTERED` |
| WORKING TITLE | `Global 80/20 Strategic Allocation Core` |
| STRATEGY FAMILY | `STATIC_GLOBAL_EQUITY_BOND_STRATEGIC_ASSET_ALLOCATION` |
| SCIENTIFIC_PARENT | `null` |
| MECHANISM_ID | `null` |
| CANDIDATE_ORDINAL_WITHIN_CORE | `3` |

Predecessors: HYP_009 = `TERMINAL_NOT_SUPPORTED_CANDIDATE_NOT_PARENT`;
HYP_010 = `BLOCKED_NON_FALSIFIED_CANDIDATE_NOT_PARENT`. HYP_011 is not an
amendment/rescue of either and performs no VEU substitution. K = 1.

## 2. Research Selection Basis (Supplied Authority, Pre-Performance)

- **A. Long-run equity premium** (Dimson/Marsh/Staunton, UBS Global Investment
  Returns Yearbook 2026): equities the highest-performing major liquid asset
  class over long horizons, with material drawdown/volatility risk.
- **B. Global diversification** (Cambridge Judge, Global Investment Returns
  project): international diversification historically improved risk-adjusted
  outcomes for most countries; defensible prospectively, not guaranteed.
- **C. 80/20 allocation** (Vanguard diversification guidance): conventional
  "aggressive" strategic allocation; growth preserved with partial bond
  diversification. NOT claimed mathematically optimal; selected
  pre-performance as a conventional growth-oriented allocation.
- **D. Rebalancing** (Vanguard guidance/research): rebalancing controls risk,
  not maximizes return; annual calendar rebalancing is operationally simple.
  No threshold optimization (avoids extra parameters/monitoring complexity).

## 3. Asset Universe / Economic Role (Frozen)

- Targets: ACWI (0.80, GLOBAL_EQUITY_GROWTH_ASSET) + AGG (0.20,
  US_INVESTMENT_GRADE_BOND_DIVERSIFIER). No other holding; no SPY holding;
  residual operational cash from whole-share sizing only (0% return).
- No VEU/IVV/BIL/SHV/IAU/IYR/QQQ/VXUS/BND/TLT/GLD/sector ETFs. SPY is the
  primary gating benchmark ONLY.

## 4. No Signal / Rebalance / Constraints (Frozen)

- No momentum/MA/absolute/relative/vol/macro/valuation/ML/discretion signals;
  no lookback, warmup, ranking, or threshold. Sole state:
  `STATIC_TARGET_ALLOCATION_80_20`.
- ANNUAL rebalance only: initial allocation at first eligible canonical U.S.
  equity session open on/after partition start; scheduled rebalance at first
  eligible open of each new calendar year to 80/20. No monthly/quarterly/
  drift/tactical/performance-triggered rebalance.
- Long only, MAX_GROSS_LEVERAGE 1.0, no margin/short/options/futures/leveraged
  ETF/synthetic, whole shares only, no negative cash.

## 5. Whole-Share Rebalance Algorithm (Frozen)

At each execution OPEN: pretrade spendable value = spendable cash + share
values at raw opens (unpaid receivables count in equity but NOT in the trade
budget). Ideal targets T_ACWI = 0.80 × value, T_AGG = 0.20 × value. Integer
targets Q = floor(T / raw_open). Execute SELLS first, then BUYS. If adverse
fills/fees would drive spendable cash negative: iteratively decrement a
proposed BUY by one share, each time choosing the asset whose one-share
reduction minimizes increase in ABS(w_ACWI − 0.80) + ABS(w_AGG − 0.20);
tie-break decrements AGG first; continue until projected spendable cash ≥ 0.
No discretionary rounding, no borrowing.

## 6. Data / Corporate-Action / Cost Contracts (Frozen)

- Bars: ALPACA_HISTORICAL_STOCK_BARS, ACWI/AGG (+SPY benchmark), 1Day, SIP;
  raw for execution/valuation + split series for lineage qualification. No
  IEX/fallback/substitution/splicing; no vendor adjusted-close authority.
- Distributions: ACWI/AGG → BLACKROCK_ISHARES_OFFICIAL; SPY benchmark →
  STATE_STREET_SPDR_OFFICIAL. Ex-date + amount + payable (+record/type where
  provided) required; gaps → `BLOCKED_DIVIDEND_AUTHORITY_COVERAGE_GAP`; no
  D=0 inference, no unofficial sources, no inferred payable. Splits: bind
  official authority or `BLOCKED_SPLIT_EVENT_CONTRACT`.
- Source feasibility (pre-performance signal, NOT qualified coverage):
  iShares ACWI page (inception 2008-03-26, semi-annual, 39-record interface
  with record/ex/payable/total fields); iShares AGG page (inception
  2003-09-22, monthly, ~275-record interface, same fields). R2 must still
  prove exact 2016–2024 coverage fail-closed.
- Simulated starting AUM 100000.00 (real 0.00). Baseline 2bps/side, stress
  10bps/side + 2x canonical sell-side regulatory fees, commission 0,
  independent paths. Missing applicable fee authority → `BLOCKED_FEE_AUTHORITY`.
- Portfolio dividends: ex-date receivable in equity immediately, spendable
  only on payable date, no double count, missing payable →
  `BLOCKED_DIVIDEND_PAYMENT_DATE_CONTRACT`, terminal unpaid receivable in equity.

## 7. Benchmark / Partitions / Prospective (Frozen)

- Primary gating benchmark: SPY BUY AND HOLD (independent 100000.00, first
  performance-session open, whole shares, 2bps buy, same CA economics, no
  rebalance/liquidation). Total-return outperformance NOT required (G4 is
  drawdown-only). Secondary informational: ACWI BUY AND HOLD (non-binding).
- Historical exposed replication 2016-01-01..2024-12-31 (first execution at
  first eligible open on/after 2016-01-01; NOT researcher-blind).
- Recent stress 2025-01-01..2026-08-14 (NOT pristine, NON_DECISIVE, separate
  authorization, no rescue). Quarantine 2026-08-15..prospective-exclusive
  (ZERO ACCESS). Prospective: first eligible regular session open strictly
  after HYP_011 R1 commit (LOCKED at R1); final evaluation needs ≥504 sessions
  AND ≥2 annual rebalances (later of the two); same G1–G6; no interim tuning.

## 8. Gates / Verdicts (Frozen CORE-001 Philosophy)

G1 return > 0; G2 Sharpe ≥ 0.50 (252/ddof1/rf0, zero-variance fail-closed);
G3 MDD ≤ 0.35; G4 strategy MDD < SPY B&H MDD (identical partition, equivalent
CA economics); G5 10bps-stress return > 0; G6 no material contract failure.
Conjunction, no override. Historical:
`HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW` /
`HISTORICAL_REPLICATION_NOT_SUPPORTED_NO_PROSPECTIVE_AUTHORIZATION` /
`BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT`. Prospective:
`PROSPECTIVE_SUPPORT_FOR_HUMAN_REVIEW` /
`HYP_011_TERMINAL_NOT_SUPPORTED_PROSPECTIVELY` (pass never auto-authorizes trading).

## 9. Anti-Optimization / Continuity

K = 1. Post-R1 redesign forbidden (weights, universe, filters, frequency,
thresholds, gates, dates, rescue uses) — any redesign needs a NEW hypothesis.
CORE-001 objective (simple deployable long-only 1x low-turnover core) remains
open; HYP_009 candidate #1 terminal; HYP_010 candidate #2 parked non-falsified;
HYP_011 candidate #3, not an amendment.

## 10. Authority Boundary

Formal R1 registration NOT PERFORMED by this document. Zero market-data
requests, zero signals/P&L. Paper NOT_AUTHORIZED, live LOCKED.

## 11. Next Human Action

`REVIEW_CORE_001_HYP_011_R1_AND_AUTHORIZE_PROVIDER_AND_SPONSOR_QUALIFICATION`
(after R1 seal, not by this document).
