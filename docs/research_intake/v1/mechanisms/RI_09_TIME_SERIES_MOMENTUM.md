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
Return direction may persist at certain horizons.

## 3. Economic / Microstructure Rationale
Proposed explanations in the broader literature may include behavioral underreaction to fundamental news, delayed information diffusion, institutional fund flow inertia, and risk-management feedback mechanisms.

## 4. Null Hypothesis
$H_0$: Past excess returns over lookback horizons contain zero predictive information regarding future excess returns, and observed trend performance is entirely attributable to data snooping and random drift.

## 5. Alternative Hypothesis
$H_1$: Past excess returns significantly predict future directional returns across liquid financial contracts, generating positive risk-adjusted returns after accounting for transaction costs.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Moskowitz, Ooi, and Pedersen (2012, *Journal of Financial Economics*) document robust time-series momentum across global futures contracts over 1- to 12-month horizons.
- **Preprint / Preliminary**: Multi-horizon trend-following and dynamic volatility scaling models.
- **Source Claim Only**: Claims that specific arbitrary exponential moving averages (e.g., EMA 8/21, EMA 9/21/50, EMA 12) have supplied scientific privilege.

## 7. What Existing Evidence Does NOT Support
Important: exact EMA (8/21, 9/21/50, 12) has no supplied scientific privilege. Academic evidence does NOT support the claim that any specific proprietary combination of moving average parameters possesses structural superiority over other lookback windows.

## 8. Source Claims That Motivated This Intake
- `SR-03`: Personal preference for EMA 8 and 21.
- `SR-04`: Claimed 982% return using 5-minute EMA 12 momentum.
- `SR-06`: Ninja GEX checklist emphasizing daily and intraday EMA 9/21/50 stacks.
- `SR-08`: Nasdaq daily long bias (unconditional upward drift).
- `SR-14`: Trend following and momentum macro strategy families.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED (global futures cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Continuous rolled futures prices and consolidated volumes.
- **Canonical Market Time Zone**: NOT_YET_DETERMINED_BY_INSTRUMENT (UTC storage required).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED (20 years cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
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
Falsified if systematic momentum portfolios fail to achieve positive Sharpe ratios across out-of-sample data after realistic transaction costs and roll decay.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No specific moving average parameters (8, 9, 12, 21, 50) are authorized.

## 17. Metrics
Annualized Sharpe Ratio, Max Drawdown, Calmar Ratio, Deflated Sharpe Ratio.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
DO_NOT_RECYCLE into CORE-002. May remain in library as a scientific family reference.

## 19. Open Questions
- What is the decay rate of short-horizon intraday momentum compared to classic multi-month time-series momentum?
- How does trend performance behave during monetary policy transitions?

## 20. Next Permitted Action
literature preservation only.
