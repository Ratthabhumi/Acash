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
At the New York open (09:30 America/New_York), overnight macro news, earnings, and accumulated institutional order imbalances are incorporated into price. Large institutional rebalancing and liquidity discovery create structured directional flows that may exhibit persistence into subsequent trading intervals.

## 4. Null Hypothesis
$H_0$: Information incorporated during the market opening interval contains zero incremental predictive power regarding subsequent intraday return distributions after conditioning on unconditional market return, prevailing volatility, and historical intraday seasonality.

## 5. Alternative Hypothesis
$H_1$: The sign and magnitude of the opening-interval return significantly predict the sign and magnitude of the late-session or closing-interval return, conditional on volume and volatility state variables.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Gao, Han, Li, and Zhou (2018, *Journal of Financial Economics*) establish that the first half-hour return of the US equity market significantly predicts the last half-hour return. This predictability is demonstrably stronger during high-volatility, high-volume, and macroeconomic announcement states.
- **Preprint / Preliminary**: Intraday cross-asset lead-lag effects between index futures and underlying cash equities during the open.
- **Source Claim Only**: Claims that a specific fixed 1-minute, 5-minute, or 15-minute bar close above a moving average guarantees a continuation with 1:2 R:R.

## 7. What Existing Evidence Does NOT Support
Existing academic literature does NOT support the claim that an arbitrary retail rule (e.g., 5-minute bar close above EMA 12 or 9:30 range breakout) yields consistent positive net alpha after accounting for execution friction, bid/ask spread crossing, and transaction fees.

## 8. Source Claims That Motivated This Intake
- `SR-01`: 9:30 high/low breakout and 1-minute FVG momentum claims.
- `SR-03`: Discretionary emphasis on market open volatility and 1-minute execution.
- `SR-04`: First 5-minute candle EMA12 momentum claim (claimed 982% return, 57% win rate).
- `SR-07`: Nasdaq Opening Range Breakout (09:30–09:45 NY opening range).
- `SR-19`: Reported high frequency of winning configurations during NY AM opening hours.

## 9. Data Requirements
- **Instrument**: US Equities (SPY, QQQ) and US Index Futures (CME: ES, NQ).
- **Frequency**: 1-minute and tick-level event bars.
- **Data Types**: Top-of-book (NBBO) quotes and trade prints.
- **Time Zone**: America/New_York (converted to UTC).
- **Vendor / Feed Semantics**: Consolidated Tape (SIP) for cash equities; CME MDP 3.0 direct feed for index futures.
- **Historical Coverage**: Minimum 10 years covering distinct volatility regimes (2014–2024).
- **Authority Requirements**: Authoritative exchange/SIP archives with microsecond timestamps.

## 10. Data Provenance Contract Required Before Empirical Work
Formal data provider verification, verification of DST alignment between cash and futures sessions, and immutable SHA-256 data lineage manifest.

## 11. Execution / Friction Requirements
- Executable bid/ask spread modeling at open (spread is widest between 09:30 and 09:35 ET).
- Broker clearing commissions and exchange transaction fees.
- Asymmetric slippage and market impact models.
- Strict resolution of bar-path ambiguity for opening bars.

## 12. Confounders
- Overnight index futures return drift (Asia/Europe sessions).
- Scheduled macroeconomic releases at 08:30 ET and 10:00 ET.
- Intraday U-shaped volume and volatility smiles.

## 13. Required Negative / Placebo Controls
- Time-of-day placebo: Evaluate identical breakout/momentum logic applied at random midday intervals (e.g., 11:30–12:00, 13:00–13:30 ET).
- Return-permuted control: Intraday bar series with shuffled opening returns.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: MEDIUM-HIGH.
- **Rationale**: ACASH previously researched intraday equity index strategies under HYP_007. Historical parameters and findings from HYP_007 must NOT be recycled or used to select opening window intervals.

## 15. Falsification Concept
The mechanism is falsified if conditional late-session returns show zero statistically significant deviation from the unconditional mean when conditioned on opening return sign/magnitude across multi-year out-of-sample data.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No exact lookback windows (1-min, 5-min, 15-min, 30-min), target multiples, or indicator thresholds are authorized at R0.

## 17. Metrics
Diagnostics include mean conditional return, t-statistic, Deflated Sharpe Ratio, and net realization after spread crossing.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
SATELLITE SHORTLIST A.

## 19. Open Questions
- What is the minimum effective observation window (e.g., 15m vs. 30m) that captures institutional flow without excessive noise?
- Does the effect persist in individual large-cap equities or is it strictly an index-level macro phenomenon?

## 20. Next Permitted Action
zero-outcome data feasibility audit.
