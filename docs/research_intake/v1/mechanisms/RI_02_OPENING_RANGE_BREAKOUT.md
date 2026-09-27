# RI-02 — Opening Range Breakout (ORB)

## 1. Intake Status
- Intake status: PROMISING_UNVERIFIED
- Candidate role: SATELLITE ONLY
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
A breakout beyond an information-rich opening price range established during the initial market session may contain short-horizon continuation information driven by asymmetric liquidity exhaustion.

## 3. Economic / Microstructure Rationale
Initial trading ranges establish localized supply and demand bounds. A sustained violation of this range may reflect participant flow where aggressive market orders exhaust resting limit order book depth.

## 4. Null Hypothesis
$H_0$: Breakouts beyond the initial opening price range exhibit no higher directional continuation probability or positive expected return than random price thresholds constructed from matched-volatility intervals.

## 5. Alternative Hypothesis
$H_1$: Price expansion beyond the opening range exhibits statistically significant positive autocorrelation and directional drift over an intraday holding horizon, net of execution frictions.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Empirical literature on opening range breakout / TORB in index futures.
- **Preprint / Preliminary**: Studies demonstrating opening range breakout persistence in commodity and index futures.
- **Source Claim Only**: Fixed mechanical recipes claiming 49.0% win rate, 1.10 profit factor, 2x range target, and 0.25 ATR buffer.

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that an invariant retail rule (e.g., 09:30–09:45, 5-minute close breakout, ATR14, 0.25 ATR buffer, 2x range target, 1 trade/day, 15:55 flat, 1% risk) is scientific authority. It belongs strictly in source notes (`SR-07`).

## 8. Source Claims That Motivated This Intake
- `SR-01`: 9:30 high/low breakout with 1:2 RR.
- `SR-07`: Nasdaq Opening Range Breakout (Win 49.0%, PF 1.10, MDD 24.61%, 09:30–09:45 range, 0.25 ATR, 2x range target, 15:55 flat).
- `SR-10`: USDJPY Morning Range Breakout (03:00–06:00 broker time range).

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED (Index Futures or Currency Futures cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Executed trades, volume, and quote data.
- **Time Zone**: America/New_York (UTC storage).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative tick or bar archives with precise exchange timestamps.

## 10. Data Provenance Contract Required Before Empirical Work
Verification of continuous contract roll method and explicit capture of opening bid/ask spreads.

## 11. Execution / Friction Requirements
- Exchange execution and clearing fees.
- Realistic slippage modeling on stop-entry orders.
- Explicit resolution of intrabar bar-path ambiguity.

## 12. Confounders
- Opening range duration choice.
- Intraday mean-reverting chop regimes generating false breakouts.

## 13. Required Negative / Placebo Controls
- Matched time-of-day / volatility breakout control: Breakout logic applied to pseudo-ranges formed at non-opening intervals.
- Shuffled bar control: Permuted price sequences with identical opening volatility.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: HIGH.
- **Rationale**: ORB is widely snooped in retail and quantitative circles, presenting severe selection bias risk.

## 15. Falsification Concept
Falsified if out-of-sample forward returns following range breakouts do not exceed execution spread and commission costs across a multi-year evaluation period.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No opening duration (e.g. 15m), buffer (e.g. 0.25 ATR), or profit target (e.g. 2x range) is authorized.

## 17. Metrics
Expectancy per trade, Deflated Sharpe Ratio, maximum drawdown, and slippage decay curve.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
SATELLITE ONLY.

## 19. Open Questions
- Does conditioning on opening volume expansion separate genuine breakouts from liquidity sweeps?
- How does the futures roll cycle affect opening range geometry?

## 20. Next Permitted Action
remain on hold.
