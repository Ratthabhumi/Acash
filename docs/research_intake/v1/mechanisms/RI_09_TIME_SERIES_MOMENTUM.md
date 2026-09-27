# RI-09 — Time-Series Momentum / Trend

## 1. Intake Status
- Intake status: SUPPORTED_MECHANISM
- Candidate role: DO_NOT_RECYCLE into CORE-002
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Asset returns exhibit positive autocorrelation over intermediate horizons (time-series momentum), whereby past positive excess returns predict future positive excess returns across diverse asset classes.

## 3. Economic / Microstructure Rationale
Time-series momentum is driven by behavioral underreaction to fundamental news, delayed information diffusion, institutional fund flow inertia, and risk-management feedback mechanisms (stop-loss cascades and trend-following mandates).

## 4. Null Hypothesis
$H_0$: Past excess returns over lookback horizons contain zero predictive information regarding future excess returns, and observed trend performance is entirely attributable to data snooping and random walk drift.

## 5. Alternative Hypothesis
$H_1$: Past excess returns significantly predict future directional returns across liquid financial contracts, generating positive risk-adjusted returns after accounting for transaction costs.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Moskowitz, Ooi, and Pedersen (2012, *Journal of Financial Economics*) document robust time-series momentum across dozens of global futures contracts over 1- to 12-month horizons.
- **Preprint / Preliminary**: Multi-horizon trend-following and dynamic volatility scaling models.
- **Source Claim Only**: Claims that specific arbitrary exponential moving average combinations (e.g., EMA 8/21, EMA 9/21/50, EMA 12) represent optimal trading signals.

## 7. What Existing Evidence Does NOT Support
Academic evidence does NOT support the claim that any specific proprietary combination of moving average parameters possesses structural superiority over other lookback windows. Exact parameterizations are heavily prone to sample-specific overfitting.

## 8. Source Claims That Motivated This Intake
- `SR-03`: Personal preference for EMA 8 and 21.
- `SR-04`: Claimed 982% return using 5-minute EMA 12 momentum.
- `SR-06`: Ninja GEX checklist emphasizing daily and intraday EMA 9/21/50 stacks.
- `SR-08`: Nasdaq daily long bias (unconditional upward drift).
- `SR-14`: Trend following and momentum macro strategy families.

## 9. Data Requirements
- **Instrument**: Global futures, equity indexes, and commodities.
- **Frequency**: Daily and intraday bars.
- **Data Types**: Continuous rolled futures prices and consolidated volumes.
- **Time Zone**: Canonical market exchange time (UTC).
- **Vendor / Feed Semantics**: Authoritative exchange continuous series.
- **Historical Coverage**: Minimum 20 years (covering multiple macroeconomic cycles).
- **Authority Requirements**: Authoritative long-term historical archives.

## 10. Data Provenance Contract Required Before Empirical Work
Rigorous specification of roll rules, contract stitching, and financing rates.

## 11. Execution / Friction Requirements
- Full contract roll transaction costs.
- Exchange clearing and execution fees.
- Capital financing costs.

## 12. Confounders
- Broad market beta drift (especially in equity indices).
- Trend-reversal regimes during macroeconomic turning points.

## 13. Required Negative / Placebo Controls
- Cross-sectionally permuted return series.
- Time-reversed historical series.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: VERY_HIGH.
- **Rationale**: ACASH previously conducted extensive research on momentum and trend allocation under HYP_009 and HYP_010. Investigating adjacent trend mechanisms poses severe multiple-testing contamination.

## 15. Falsification Concept
Falsified if systematic momentum portfolios fail to achieve positive Sharpe ratios across multi-decade out-of-sample data after realistic transaction costs and roll decay.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No specific moving average parameters (8, 9, 12, 21, 50) are authorized.

## 17. Metrics
Annualized Sharpe Ratio, Max Drawdown, Calmar Ratio, Deflated Sharpe Ratio.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
DO_NOT_RECYCLE. Preserved strictly as a scientific family benchmark and baseline control.

## 19. Open Questions
- What is the decay rate of short-horizon intraday momentum compared to classic multi-month time-series momentum?
- How does trend performance behave during monetary policy tightening regimes?

## 20. Next Permitted Action
literature preservation only.
