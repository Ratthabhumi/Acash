# RI-14 — FVG / SMC (Fair Value Gap / Smart Money Concepts)

## 1. Intake Status
- Intake status: NEGATIVE_CONTROL_CANDIDATE
- Candidate role: NEGATIVE_CONTROL_CANDIDATE / LOW PRIORITY
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
A mechanically defined three-candle price geometry wherein candle 1's high (low) does not overlap candle 3's low (high)—commonly labeled a "Fair Value Gap" (FVG)—is evaluated to determine whether it contains incremental predictive information regarding future price retests beyond an ordinary matched price displacement.

## 3. Economic / Microstructure Rationale
Retail discretionary discourse claims that an FVG represents an "unbalanced institutional footprint" where price moved so rapidly that liquidity was omitted, creating a "magnetic" attraction for price to revisit and "rebalance" the gap.

## 4. Null Hypothesis
$H_0$: Mechanically defined Fair Value Gaps exhibit zero incremental predictive power, retest frequency, or post-retest continuation edge compared to size-matched price displacements lacking the three-candle non-overlapping geometry.

## 5. Alternative Hypothesis
$H_1$: Prices revisit mechanically identified Fair Value Gaps with statistically significant excess frequency and exhibit directional bounces that survive transaction costs.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: NONE. SMC and FVG concepts originate entirely within unregulated retail trading social media.
- **Preprint / Preliminary**: Highly conflicting 2026 preprints. One study finds that while prices frequently touch FVG zones, tradeable strategies generate zero net alpha after spread and commission; it also identifies severe coarse-bar path bias in backtest claims. Another preprint claims positive gross returns over a small, unrobust sample.
- **Source Claim Only**: Widespread promotional claims that FVGs represent "bank algorithms" and offer effortless daily 1:2 R:R setups.

## 7. What Existing Evidence Does NOT Support
Scientific evidence does NOT support the claim that FVGs represent institutional balance sheets, bank footprints, or guaranteed support/resistance levels. The terminology "Smart Money Concepts" is marketing framing with zero institutional standing.

## 8. Source Claims That Motivated This Intake
- `SR-01`: 9:30 open breakout combined with 1-minute FVG momentum.

## 9. Data Requirements
- **Instrument**: CME Index Futures (NQ, ES) and US Equities.
- **Frequency**: 1-minute and tick-level bars.
- **Data Types**: High-precision OHLCV bars and NBBO quotes.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: Authoritative exchange tick feeds.
- **Historical Coverage**: Minimum 5 years.
- **Authority Requirements**: Authoritative exchange data.

## 10. Data Provenance Contract Required Before Empirical Work
Strict machine-deterministic geometric specification of the FVG condition before accessing any market data.

## 11. Execution / Friction Requirements
- Full spread crossing and slippage modeling.
- Resolution of intrabar bar-path ambiguity when price enters the gap.

## 12. Confounders
- Coarse-bar bias: testing FVG rules on 15m or 1h bars without evaluating intrabar tick sequencing leads to massive overestimation of fill rates.
- Unconditional price drift.

## 13. Required Negative / Placebo Controls
- Geometry placebo: A matched price displacement of identical magnitude and duration that does NOT possess the 3-candle non-overlapping condition.
- Random gap placement control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: HIGH.
- **Rationale**: Massive retail exposure and widespread post-hoc cherry-picking in online media.

## 15. Falsification Concept
Falsified if the conditional forward return following an FVG fill is statistically indistinguishable from a matched price displacement control, or if net returns are negative after transaction costs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No gap size thresholds, timeframe selections, or take-profit rules are authorized.

## 17. Metrics
Retest probability vs. placebo, net expectancy after friction, bar-path sensitivity.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
NEGATIVE_CONTROL_CANDIDATE / LOW PRIORITY.

## 19. Open Questions
- Is the FVG phenomenon entirely explained by standard bid/ask bounce and coarse-bar discretization?
- Does conditioning on order flow imbalance at the gap boundary eliminate any apparent edge?

## 20. Next Permitted Action
remain on hold.
