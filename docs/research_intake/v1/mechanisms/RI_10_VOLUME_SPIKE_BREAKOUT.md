# RI-10 — Volume-Spike Breakout

## 1. Intake Status
- Intake status: PROMISING_UNVERIFIED
- Candidate role: Satellite later
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Abnormally high normalized transaction volume accompanying a price displacement or breakout beyond recent local extrema may signal genuine institutional participation, increasing the probability of short-horizon trend continuation.

## 3. Economic / Microstructure Rationale
High volume during a price breakout reflects aggressive order flow sufficient to absorb resting liquidity at local extremes. When volume is abnormally elevated relative to historical time-of-day expectations, it indicates coordinated market participation rather than low-liquidity slippage.

## 4. Null Hypothesis
$H_0$: Conditioning price breakouts on abnormal volume spikes provides zero incremental predictive information or return persistence compared to unconditional price breakouts.

## 5. Alternative Hypothesis
$H_1$: Breakouts accompanied by statistically significant normalized volume spikes exhibit higher continuation rates and lower false-breakout frequency than breakouts occurring on average or below-average volume.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Literature on volume-return interactions (e.g., Blume, Easley, O'Hara on volume and price discovery; Lee and Swaminathan on volume and momentum).
- **Preprint / Preliminary**: Empirical evaluations of abnormal volume filters on breakout strategies in futures.
- **Source Claim Only**: Specific social-media recipes claiming optimal parameters such as $	ext{vol\_mult} = 2.5$, $	ext{vol\_n} = 50$, $k = 10$, ATR 14, 50% retracement limit entries, and skipping Wednesdays and Fridays.

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that an arbitrarily complex set of heuristic filters ($	ext{vol\_mult}=2.5$, 12:00–16:00 ET window, skipping Wed/Fri) represents a stationary law of market behavior. Such hyper-specific parameter sets are classic artifacts of historical overfitting.

## 8. Source Claims That Motivated This Intake
- `SR-06`: Ninja GEX checklist emphasizing volume 1.5x–3x average to validate breakouts.
- `SR-12`: Volume spike breakout strategy recipe ($	ext{vol\_mult}=2.5$, $	ext{vol\_n}=50$, $k=10$, 50% retracement limit, ATR14 stop/target, 12:00–16:00 ET, skip Wed/Fri).
- `SR-19`: Discussion of volume spike systems exhibiting low win rates (7–14%) but high payoffs.

## 9. Data Requirements
- **Instrument**: CME Index Futures (NQ, ES) and US Equities.
- **Frequency**: 1-minute and 5-minute bars.
- **Data Types**: High-precision trade volume and NBBO prices.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: CME MDP 3.0 / Consolidated Tape SIP.
- **Historical Coverage**: Minimum 10 years.
- **Authority Requirements**: Authoritative exchange trade volume archives.

## 10. Data Provenance Contract Required Before Empirical Work
Strict verification of volume semantics: CFD tick volume is explicitly banned; consolidated exchange volume is required.

## 11. Execution / Friction Requirements
- Stop-limit order execution modeling.
- Limit order fill probability on 50% retracement pullback rules.
- Intrabar bar-path ambiguity resolution.

## 12. Confounders
- Time-of-day U-shaped volume curve (a raw 2.5x volume at 13:00 is very different from 2.5x at 09:30).
- Scheduled news releases creating non-tradeable flash spikes.

## 13. Required Negative / Placebo Controls
- Volume-independent breakout control: Identical price breakout without the volume spike condition.
- Shuffled volume control: Randomly assigning volume values across bars.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: MEDIUM.
- **Rationale**: Public availability of complex overfitted parameter sets introduces severe selection bias.

## 15. Falsification Concept
Falsified if volume-filtered breakouts yield no statistically significant improvement in post-breakout excess return or Sharpe ratio compared to unfiltered breakouts across out-of-sample data.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No volume multipliers (e.g. 2.5), lookbacks (e.g. 50), or session filters are authorized at R0.

## 17. Metrics
Post-breakout drift $t$-statistic, Deflated Sharpe Ratio, limit order execution rate.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Satellite later.

## 19. Open Questions
- How should volume be normalized: relative to rolling window, time-of-day expectation, or volatility state?
- Do retracement limit entries introduce severe survivorship bias by omitting the strongest runaway trends?

## 20. Next Permitted Action
remain on hold.
