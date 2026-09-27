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
Unusually high normalized volume combined with price displacement/breakout may contain incremental continuation information.

## 3. Economic / Microstructure Rationale
High volume during a price breakout reflects unusually elevated trading activity / participation sufficient to absorb resting liquidity at local extremes. When volume is abnormally elevated relative to historical baseline expectations, it reflects broader / more intense market participation rather than low-liquidity slippage.

## 4. Null Hypothesis
$H_0$: Conditioning price breakouts on abnormal volume spikes provides zero incremental predictive information or return persistence compared to unconditional price breakouts.

## 5. Alternative Hypothesis
$H_1$: Breakouts accompanied by statistically significant normalized volume spikes exhibit higher continuation rates and lower false-breakout frequency than breakouts occurring on average or below-average volume.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Volume/flow information has a scientific basis in market microstructure literature.
- **Preprint / Preliminary**: Empirical evaluations of abnormal volume filters on breakout strategies in futures.
- **Source Claim Only**: Specific social-media recipes claiming optimal parameters such as vol_mult = 2.5, vol_n = 50, k = 10, ATR14, 50% retracement limit entries, and skipping Wednesdays and Fridays.

## 7. What Existing Evidence Does NOT Support
The exact social-media recipe is NOT authority. The following belong only to `SR-12`:
vol_mult = 2.5, vol_n = 50, k = 10, long+short, 50% retracement limit, cancel after 10 bars, ATR14, 1 ATR stop, 1 ATR target, 12:00–16:00 ET, 15:59 flat, max 2/day, exclude Wed/Fri.
Trade volume does NOT identify participant identity (whale, institution, or retail).

## 8. Source Claims That Motivated This Intake
- `SR-06`: Ninja GEX checklist emphasizing volume 1.5x–3x average to validate breakouts.
- `SR-12`: Volume spike breakout strategy recipe (vol_mult = 2.5, vol_n = 50, k = 10, 50% retracement limit, ATR14 stop/target, 12:00–16:00 ET, skip Wed/Fri).
- `SR-19`: Discussion of volume spike systems exhibiting low win rates (7–14%) but high payoffs.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED.
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: High-precision trade volume and quote prices.
- **Time Zone**: America/New_York (UTC storage).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative exchange trade volume archives.

## 10. Data Provenance Contract Required Before Empirical Work
Data semantic warning: CFD tick volume != CME futures volume != SIP equity volume. Volume semantics must be strictly verified.

## 11. Execution / Friction Requirements
- Stop-limit order execution modeling.
- Limit order fill probability on retracement pullback rules.
- Intrabar bar-path ambiguity resolution.

## 12. Confounders
- Time-of-day U-shaped volume curve.
- Scheduled news releases creating non-tradeable flash spikes.

## 13. Required Negative / Placebo Controls
- Required control: matched price move without abnormal volume.
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
Post-breakout drift t-statistic, Deflated Sharpe Ratio, limit order execution rate.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Satellite later.

## 19. Open Questions
- How should volume be normalized: relative to rolling window, time-of-day expectation, or volatility state?
- Do retracement limit entries introduce severe survivorship bias by omitting runaway trends?

## 20. Next Permitted Action
remain on hold.
