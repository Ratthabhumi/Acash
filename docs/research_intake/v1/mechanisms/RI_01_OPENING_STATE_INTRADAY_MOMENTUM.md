# RI-01 — Opening-State / Intraday Momentum

## 1. Intake Status
- Intake status: SUPPORTED_MECHANISM
- Candidate role: SATELLITE SHORTLIST A
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Information incorporated during the US market opening interval may contain incremental predictive information regarding later intraday returns, specifically the closing session return distribution.

## 3. Economic / Microstructure Rationale
At the market open (e.g. 09:30 local exchange time in US equity market examples), overnight macro news, earnings, and accumulated order imbalances are incorporated into price. Large rebalancing and liquidity discovery create structured directional flows that may exhibit persistence into subsequent trading intervals.

## 4. Null Hypothesis
$H_0$: Information incorporated during the market opening interval contains zero incremental predictive power regarding subsequent intraday return distributions after conditioning on unconditional market return, prevailing volatility, and historical intraday seasonality.

## 5. Alternative Hypothesis
$H_1$: The sign and magnitude of the opening-interval return significantly predict the sign and magnitude of the late-session or closing-interval return, conditional on volume and volatility state variables.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Gao, Han, Li, and Zhou (2018, *Journal of Financial Economics*) establish that the first half-hour return of the US equity market predicts the last half-hour return. This relation is stronger in higher volatility, volume, and macro-news states.
- **Preprint / Preliminary**: Literature on opening volume and volatility having a distinct intraday structure.
- **Source Claim Only**: Claims that a specific fixed 1-minute, 5-minute, or 15-minute bar close above a moving average guarantees a continuation with 1:2 RR.

## 7. What Existing Evidence Does NOT Support
Existing academic literature does NOT support the claim that an arbitrary retail rule (e.g., 5-minute bar close above EMA 12 or 9:30 range breakout) yields consistent positive net alpha after accounting for execution friction, spread crossing, and transaction fees.

## 8. Source Claims That Motivated This Intake
- `SR-01`: 9:30 high/low breakout and 1-minute FVG momentum claims.
- `SR-03`: Discretionary emphasis on market open volatility and 1-minute execution.
- `SR-04`: First 5-minute candle EMA12 momentum claim (claimed 982% return, 57% win rate, 1,448 trades).
- `SR-07`: Nasdaq Opening Range Breakout (09:30–09:45 NY opening range).
- `SR-19`: Reported high frequency of winning configurations during NY AM opening hours.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED (US Equities, ETFs, or Index Futures cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Price observations, volume, and quotes where execution semantics require them.
- **Canonical Market Time Zone**: NOT_YET_DETERMINED_BY_INSTRUMENT (UTC storage required).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED (subject to zero-outcome data feasibility audit).
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative exchange or consolidated tape archives.

## 10. Data Provenance Contract Required Before Empirical Work
Formal data provider verification, verification of DST alignment, and immutable lineage manifest.

## 11. Execution / Friction Requirements
- Executable bid/ask spread modeling at open.
- Broker clearing commissions and exchange transaction fees.
- Asymmetric slippage and market impact models.
- Resolution of same-bar ambiguity for opening bars.

## 12. Confounders
- Overnight index return drift.
- Scheduled macroeconomic releases (e.g., 08:30 ET, 10:00 ET).
- Intraday U-shaped volume and volatility curves.

## 13. Required Negative / Placebo Controls
- Time-of-day placebo: Evaluate identical logic applied at non-opening midday intervals (ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- Return-permuted control: Intraday bar series with shuffled opening returns.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: MEDIUM-HIGH.
- **Rationale**: ACASH previously researched intraday equity index strategies under HYP_007. Historical parameters and findings from HYP_007 must NOT be recycled or used to choose new parameters.

## 15. Falsification Concept
The mechanism is falsified if conditional late-session returns show zero statistically significant deviation from the unconditional mean when conditioned on opening return sign/magnitude across out-of-sample data.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No exact lookback windows (1-minute, 5-minute, 15-minute, 30-minute), targets, stops, FVG thresholds, ATR parameters, or news filters are authorized at R0; all remain UNSET.

## 17. Metrics
Diagnostics include mean conditional return, t-statistic, Deflated Sharpe Ratio, and net realization after friction.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
SATELLITE SHORTLIST A.

## 19. Open Questions
- What is the minimum effective observation window that captures opening flow without excessive noise?
- Does the effect persist in individual equities or is it primarily an index-level macro phenomenon?

## 20. Next Permitted Action
zero-outcome data feasibility audit.
