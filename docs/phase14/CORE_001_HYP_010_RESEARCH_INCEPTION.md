# CORE-001 / HYP_010 Research Inception (PROPOSED — NOT PREREGISTERED)

[DOCUMENT ID: docs/phase14/CORE_001_HYP_010_RESEARCH_INCEPTION.md]

[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_010_R1_PREREGISTRATION]

[CANONICAL HEAD AT INCEPTION: cd3a3f65b0cff038eeb9e90733b0fb853bcc48bf]

[STATE: PROPOSED_NOT_PREREGISTERED]

[IMPLEMENTATION-ONLY RECORD — NO LITERATURE RESEARCH, NO BACKTEST, NO PERFORMANCE]

## 1. Lineage

| Field | Value |
|---|---|
| CORE_ID | `CORE-001` |
| HYPOTHESIS_ID | `HYP_010` |
| STATE | `PROPOSED_NOT_PREREGISTERED` |
| WORKING TITLE | `ETF-Native Global Equity Dual Momentum Core` |
| STRATEGY FAMILY | `ETF_NATIVE_RELATIVE_PLUS_ABSOLUTE_MOMENTUM_ASSET_ALLOCATION` |
| SCIENTIFIC_PARENT_HYPOTHESIS | `null` |
| PREDECESSOR_CANDIDATE_CONTEXT | `HYP_009` |
| MECHANISM_ID | `null` (none invented or reserved) |

HYP_009 relationship: `TERMINAL_PREDECESSOR_CANDIDATE_NOT_PARENT_NOT_AMENDED_NOT_RESCUED`.
HYP_009 is immutable terminal evidence. HYP_010 does not alter, rescue, retune,
rename, or reinterpret HYP_009. HYP_010 is candidate #2 under the still-open
CORE-001 research objective. HYP_008 remains retired and is not reused. K = 1.

## 2. Research Selection Record (Pre-Performance, External Authority)

The external research authority considered the following families BEFORE any
HYP_010 performance observation. This record contains NO HYP_010 backtest results.

- **A. 12-month SPY time-series momentum / absolute momentum — REJECTED.**
  Moving-average trend rules and TSMOM are scientifically too closely related
  to HYP_009 for a clean independent successor (disguised-rescue risk).
- **B. Volatility-managed SPY — REJECTED.** Published real-time evidence is
  mixed; implementations depend materially on scaling/calibration/leverage
  choices; unnecessary specification degrees of freedom for CORE-001.
- **C. Diversified long/short futures trend following — NOT SELECTED FOR
  CORE-001.** Strong literature, but shorting, derivatives, volatility scaling,
  and multi-market futures infrastructure fall outside the simple long-only 1x
  CORE-001 operational envelope (future CORE-002 territory).
- **D. ETF-native global equity dual momentum — SELECTED.** Relative momentum
  has broad multi-market evidence; absolute momentum has broad multi-asset
  evidence; combining relative + absolute momentum has direct published
  precedent; monthly cadence is operationally simple; long-only; max 1x;
  low expected turnover; no derivatives; no shorting; fully investable ETF
  implementation possible.

## 3. External Literature Authority (Recorded, Not Researched Here)

1. Moskowitz, Ooi, Pedersen. "Time Series Momentum." JFE 104(2), 2012,
   228–250. DOI: 10.1016/j.jfineco.2011.11.003 — time-series return
   continuation across equity index, currency, commodity, bond futures.
2. Asness, Moskowitz, Pedersen. "Value and Momentum Everywhere." JoF 68(3),
   2013, 929–985. DOI: 10.1111/jofi.12021 — momentum premia across diverse
   markets/assets.
3. Antonacci. "Risk Premia Harvesting Through Dual Momentum." JME 2(1), 2017,
   27–55. SSRN 2042750 — precedent for combining relative + absolute momentum.
4. Antonacci public Global Equities Momentum methodology — monthly evaluation,
   12-month lookback, U.S. equity absolute momentum vs Treasury-bill return,
   relative U.S. vs non-U.S. selection when risk-on, aggregate bonds defensive.
   HYP_010 is an ETF-native preregistered implementation derived from that
   architecture, NOT an exact index replication.
5. Marshall, Nguyen, Visaltanachoti. "Time series momentum and moving average
   trading rules." Quant. Finance 17(3), 2017, 405–421.
   DOI: 10.1080/14697688.2016.1205209 — supports NOT using SPY TSMOM as
   candidate #2 (TSMOM/MA-rule kinship).
6. Cederburg, O'Doherty, Wang, Yan. "On the performance of volatility-managed
   portfolios." JFE 138(1), 2020, 95–117. DOI: 10.1016/j.jfineco.2020.04.015 —
   supports rejecting volatility management (real-time benefits not systematic).

## 4. ETF Universe (Frozen)

- SPY = U.S. equity candidate. VEU = non-U.S. equity candidate.
- AGG = defensive/risk-off holding. BIL = Treasury-bill hurdle, SIGNAL ONLY.
- Target holdings: SPY / VEU / AGG only. BIL is never a v1 holding.
- No QQQ, VXUS, BND, SHY, TLT, GLD, sector ETFs. No provider substitution.

## 5. Decision Rule (Frozen K=1)

- Frequency MONTHLY; decision date LAST_ELIGIBLE_REGULAR_NYSE_SESSION_OF_MONTH
  (early close eligible if final session); observable only after close;
  execution NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL.
- `M12(asset,t) = TR(asset,t)/TR(asset,t-12) - 1` (causal TR from
  split-adjusted closes + official distributions; raw prices for execution).
- ABSOLUTE: `SPY_M12 > BIL_M12` → risk-on; `<=` → TARGET = AGG (equality → AGG).
- RELATIVE (if risk-on): `SPY_M12 >= VEU_M12` → SPY else VEU (equality → SPY).
- No tolerance/smoothing/second filter/vol target/stop/ML/override.
- 100% target holding (whole shares, residual cash at 0), MAX_GROSS_LEVERAGE 1.0.
- Trade ONLY on target-asset change (`NO_CHURN_HOLD_EXISTING`).

## 6. Warmup / Partitions / Prospective (Frozen)

- Data start 2016-01-01. Warmup: 13 month-ends (Jan-2016..Jan-2017). First
  eligible decision: Jan-2017 month-end; first execution next eligible open
  (calendar-derived, expected Feb-2017).
- Historical exposed replication: first execution → 2024-12-31,
  `HISTORICAL_EXPOSED_REPLICATION_NOT_RESEARCHER_BLIND` (no fake OOS wording).
- Recent stress 2025-01-01..2026-08-14: `PUBLICLY_EXPOSED_RECENT_STRESS_NOT_PRISTINE`,
  NON_DECISIVE, cannot rescue, cannot authorize paper/live.
- Quarantine 2026-08-15..prospective-exclusive: STRICT_ZERO_ACCESS.
- Prospective: first NYSE open strictly after HYP_010 R1 commit; LOCKED_ZERO_ACCESS
  at R1. Final prospective evaluation requires ≥24 completed monthly decisions
  AND ≥504 eligible sessions (whichever later); same G1–G6; no interim tuning.

## 7. Gates / Verdicts (Frozen, CORE-001 Philosophy Reused)

G1 return > 0; G2 Sharpe ≥ 0.50 (252/ddof1/rf0, zero-variance fail-closed);
G3 MDD ≤ 0.35; G4 strategy MDD < SPY B&H MDD (identical partition, equivalent
CA economics); G5 10bps-stress return > 0; G6 no material contract failure.
Conjunction G1–G6, no override.
Historical verdicts: `HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW` /
`HISTORICAL_REPLICATION_NOT_SUPPORTED_NO_PROSPECTIVE_AUTHORIZATION` /
`BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT`.
Prospective: `PROSPECTIVE_SUPPORT_FOR_HUMAN_REVIEW` /
`HYP_010_TERMINAL_NOT_SUPPORTED_PROSPECTIVELY` (pass never auto-authorizes trading).

## 8. Cost / Accounting / Benchmark (Frozen)

- Simulated starting AUM 100000.00 (real capital 0.00). Baseline 2bps/side,
  stress 10bps/side + 2x canonical sell-side regulatory fees, commission 0,
  whole shares, no negative cash/leverage. Missing applicable fee authority →
  `BLOCKED_FEE_AUTHORITY` (no invented zero).
- Portfolio dividend: ex-date receivable, spendable only on payable date, no
  double count, missing payable → `BLOCKED_DIVIDEND_PAYMENT_DATE_CONTRACT`.
- Benchmark: independent SPY buy-and-hold 100000.00, first performance-session
  open, 2bps buy, same CA economics, no rebalance/liquidation. Return
  outperformance NOT required; G4 is drawdown-only.

## 9. Authorities

- Sponsor dividend authorities: SPY → STATE STREET/SPDR; BIL → STATE
  STREET/SPDR; VEU → VANGUARD; AGG → BLACKROCK/ISHARES. Ex-date + amount +
  payable required; gaps → `BLOCKED_DIVIDEND_AUTHORITY_COVERAGE_GAP`.
- Bars: ALPACA_HISTORICAL_STOCK_BARS, SPY/VEU/AGG/BIL, 1Day, SIP,
  split for signal / raw for execution. No IEX/fallback/splicing.

## 10. Anti-Optimization / Continuity

K = 1. Post-R1 changes forbidden (horizon, universe, comparator, filters,
ties, thresholds, gates, dates, rescue uses). Any redesign needs a NEW
hypothesis. CORE-001 remains the objective for a simple deployable long-only
1x low-turnover core; HYP_009 was candidate #1 (terminal); HYP_010 is
candidate #2, NOT an amendment. Futures long/short trend needs a separate core.

## 11. Authority Boundary

Formal R1 registration: NOT PERFORMED by this document (proposed only).
No market-data requests, no signals/P&L, no stress access, no quarantine/
prospective access in this task. Paper NOT_AUTHORIZED, live LOCKED.

## 12. Next Human Action

`REVIEW_CORE_001_HYP_010_R1_AND_AUTHORIZE_PROVIDER_DATA_QUALIFICATION`
(after R1 seal, not by this document).
