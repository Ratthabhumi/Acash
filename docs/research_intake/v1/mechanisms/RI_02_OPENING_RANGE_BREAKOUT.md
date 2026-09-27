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
A breakout beyond an information-rich opening price range established during the initial market session may indicate directional order flow continuation driven by asymmetric liquidity exhaustion.

## 3. Economic / Microstructure Rationale
Initial trading ranges establish localized supply and demand bounds. A sustained violation of this range may reflect institutional participant participation where aggressive market orders exhaust resting limit order book depth, forcing price discovery into new territory.

## 4. Null Hypothesis
$H_0$: Breakouts beyond the initial opening price range exhibit no higher directional continuation probability or positive expected return than random price thresholds constructed from matched-volatility intervals.

## 5. Alternative Hypothesis
$H_1$: Price expansion beyond the opening range exhibits statistically significant positive autocorrelation and directional drift over an intraday holding horizon, net of execution frictions.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Empirical literature on Time-of-Day Breakout (TORB) and intraday volatility expansion in index futures.
- **Preprint / Preliminary**: Studies demonstrating opening range breakout persistence in commodity and index futures.
- **Source Claim Only**: Fixed mechanical recipes claiming 49.0% win rate, 1.10 profit factor, 2x range target, and 0.25 ATR buffer.

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that an invariant 15-minute range (09:30–09:45) with fixed 2:1 profit targets is universally profitable across market regimes without rigorous dynamic volatility adjustment.

## 8. Source Claims That Motivated This Intake
- `SR-01`: 9:30 high/low breakout with 1:2 RR.
- `SR-07`: Nasdaq Opening Range Breakout (Win 49.0%, PF 1.10, MDD 24.61%, 09:30–09:45 range, 0.25 ATR buffer, 2x range target, 15:55 flat).
- `SR-10`: USDJPY Morning Range Breakout (03:00–06:00 broker time range).

## 9. Data Requirements
- **Instrument**: CME Index Futures (NQ, ES) and Currency Futures.
- **Frequency**: 1-minute and tick-level bars.
- **Data Types**: Executed trades, volume, and NBBO quotes.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: CME MDP 3.0 direct exchange market data.
- **Historical Coverage**: Minimum 10 years.
- **Authority Requirements**: Authoritative tick archives with precise exchange timestamps.

## 10. Data Provenance Contract Required Before Empirical Work
Verification of continuous contract roll method and explicit capture of wide opening bid/ask spreads.

## 11. Execution / Friction Requirements
- Exchange execution and clearing fees.
- Realistic slippage modeling on stop-entry orders (stop orders often fill worse than limit triggers during breakouts).
- Explicit resolution of intrabar high/low path ambiguity.

## 12. Confounders
- Opening range duration choice (5-minute vs. 15-minute vs. 30-minute).
- Intraday mean-reverting chop regimes that generate false breakout whipsaws.

## 13. Required Negative / Placebo Controls
- Matched-volatility breakout control: Breakout logic applied to pseudo-ranges formed at 11:00 or 13:00.
- Shuffled bar control: Permuted price sequences with identical opening volatility.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: HIGH.
- **Rationale**: ORB is one of the most widely snooped retail strategies in algorithmic trading. High risk of selection bias from public claims.

## 15. Falsification Concept
Falsified if out-of-sample forward returns following range breakouts do not exceed the execution spread and commission costs across a multi-year evaluation period.

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
- How does the roll cycle in index futures affect opening range geometry?

## 20. Next Permitted Action
remain on hold.
